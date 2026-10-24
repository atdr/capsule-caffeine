import json

from capsule_caffeine.cli import main
from capsule_caffeine.diff import compare, summary


def doc(lines, generated_at="2026-10-24T12:00:00Z"):
    return {"schema": 2, "generated_at": generated_at, "scraper": "2.0.0", "lines": lines}


def pod(mg, image="https://x/a.png"):
    return {"caffeine_mg": mg, "image_url": image, "page_url": "https://x/a"}


OLD = doc({"Original": {"Espresso": {"Ristretto": pod(120), "Roma": pod(70)}}})
NEW = doc(
    {
        "Original": {
            "Espresso": {"Ristretto": pod(115)},
            "Lungo": {"Roma": pod(70)},
            "Limited Edition": {"Maple": pod(None)},
        }
    },
    generated_at="2026-10-31T12:00:00Z",
)


def test_unchanged_apart_from_build_time():
    assert not compare(OLD, {**OLD, "generated_at": "later", "scraper": "2.1.0"})


def test_compare_lists_changes():
    changes = compare(OLD, NEW)

    assert changes.added == ["Original / Maple (no value)"]
    assert changes.removed == []
    assert changes.caffeine == ["Original / Ristretto: 120 mg → 115 mg"]
    assert changes.moved == ["Original / Roma: Espresso → Lungo"]
    assert not changes.other


def test_image_only_change_still_counts():
    newer = json.loads(json.dumps(OLD))
    newer["lines"]["Original"]["Espresso"]["Roma"]["image_url"] = "https://x/b.png"
    changes = compare(OLD, newer)
    assert changes and changes.other
    assert summary({"tw": changes}) == "### tw\n\nImages or links changed."


def test_diff_command_over_build_directories(tmp_path, capsys):
    for root, data in (("old", OLD), ("new", NEW)):
        (tmp_path / root / "tw").mkdir(parents=True)
        (tmp_path / root / "tw" / "capsules.json").write_text(json.dumps(data))
    (tmp_path / "new" / "sg").mkdir()
    (tmp_path / "new" / "sg" / "capsules.json").write_text(json.dumps(OLD))

    assert main(["diff", str(tmp_path / "old"), str(tmp_path / "new")]) == 1
    out = capsys.readouterr().out
    assert "### sg\n\n**Added**\n- Original / Ristretto (120 mg)\n- Original / Roma (70 mg)" in out
    assert "### tw" in out

    assert main(["diff", str(tmp_path / "old"), str(tmp_path / "old")]) == 0
    assert capsys.readouterr().out == "No changes.\n"
