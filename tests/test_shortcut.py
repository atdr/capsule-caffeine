import plistlib

from capsule_caffeine import shortcut
from capsule_caffeine.cli import main


def identifiers(built):
    return [a["WFWorkflowActionIdentifier"].rsplit(".", 1)[-1] for a in built["WFWorkflowActions"]]


def test_shortcut_is_well_formed_and_reproducible():
    built = shortcut.build()
    assert shortcut.problems(built) == []
    assert shortcut.to_bytes(built) == shortcut.to_bytes(shortcut.build())
    question = built["WFWorkflowImportQuestions"][0]
    assert identifiers(built)[question["ActionIndex"]] == "gettext"


def test_shortcut_reads_the_published_data():
    steps = shortcut.build()["WFWorkflowActions"]
    download = next(a for a in steps if a["WFWorkflowActionIdentifier"].endswith("downloadurl"))
    url = download["WFWorkflowActionParameters"]["WFURL"]["Value"]["string"]
    assert url == f"https://atdr.github.io/capsule-caffeine/{shortcut.OBJ}/capsules.json"


def test_problems_catch_broken_references_and_blocks():
    built = shortcut.build()
    steps = built["WFWorkflowActions"]
    # Drop the Ask action: later steps then use an output that no longer exists.
    del steps[identifiers(built).index("ask")]
    # And an End If.
    del steps[len(steps) - 1]

    found = shortcut.problems(built)
    assert any("is not defined before it" in p for p in found)
    assert found[-1] == "1 If without End If"


def test_shortcut_command_writes_a_plist(tmp_path):
    out = tmp_path / "log.shortcut"
    assert main(["shortcut", "-o", str(out)]) == 0
    assert plistlib.loads(out.read_bytes()) == shortcut.build()


def test_problems_catch_an_id_used_twice():
    built = shortcut.build()
    steps = built["WFWorkflowActions"]
    first_if = next(
        i for i, a in enumerate(steps) if a["WFWorkflowActionIdentifier"].endswith("conditional")
    )
    market = next(a for a in steps if a["WFWorkflowActionIdentifier"].endswith("gettext"))
    steps[first_if]["WFWorkflowActionParameters"]["GroupingIdentifier"] = market[
        "WFWorkflowActionParameters"
    ]["UUID"]

    assert any("is used by" in p for p in shortcut.problems(built))


def test_problems_catch_misspelt_keys_and_bad_choices():
    built = shortcut.build()
    steps = built["WFWorkflowActions"]
    alert = next(a for a in steps if a["WFWorkflowActionIdentifier"].endswith("alert"))
    alert["WFWorkflowActionParameters"]["WFAlertActionShowCancelButton"] = False
    math = next(a for a in steps if a["WFWorkflowActionIdentifier"].endswith("math"))
    math["WFWorkflowActionParameters"]["WFMathOperation"] = "*"

    found = shortcut.problems(built)
    assert any("alert has no parameter WFAlertActionShowCancelButton" in p for p in found)
    assert any("WFMathOperation '*' is not one of" in p for p in found)


def conditionals(steps):
    return [a for a in steps if a["WFWorkflowActionIdentifier"].endswith("conditional")]


def test_problems_catch_a_second_otherwise():
    built = shortcut.build()
    steps = built["WFWorkflowActions"]
    otherwise = next(
        i
        for i, a in enumerate(steps)
        if a["WFWorkflowActionParameters"].get("WFControlFlowMode") == 1
    )
    steps.insert(otherwise, steps[otherwise])

    assert any("a second Otherwise in one If" in p for p in shortcut.problems(built))


def test_problems_catch_two_if_blocks_sharing_an_id():
    built = shortcut.build()
    blocks = conditionals(built["WFWorkflowActions"])
    first = blocks[0]["WFWorkflowActionParameters"]["GroupingIdentifier"]
    # Give the next complete If block (the schema check) the first block's id.
    for block in blocks[3:5]:
        block["WFWorkflowActionParameters"]["GroupingIdentifier"] = first

    assert any("is used by the If at action" in p for p in shortcut.problems(built))


def test_problems_catch_a_bad_input_type():
    built = shortcut.build()
    ask = next(
        a for a in built["WFWorkflowActions"] if a["WFWorkflowActionIdentifier"].endswith("ask")
    )
    ask["WFWorkflowActionParameters"]["WFInputType"] = "Nubmer"

    assert any("WFInputType 'Nubmer' is not one of" in p for p in shortcut.problems(built))
