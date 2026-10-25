"""The Nespresso Log Shortcut, built as an unsigned .shortcut file.

Shortcuts only imports signed files, so sign the output on a Mac logged into iCloud:
`shortcuts sign --mode anyone --input unsigned.shortcut --output "Nespresso Log.shortcut"`.

The format is undocumented; this follows the files the Shortcuts app itself exports.
UUIDs are derived from names, so an unchanged Shortcut builds to identical bytes.
"""

import json
import plistlib
import uuid
from importlib import resources

DATA_URL = "https://atdr.github.io/capsule-caffeine/{}/capsules.json"
REPO_URL = "https://github.com/atdr/capsule-caffeine"
SCHEMA_VERSION = 2
OBJ = "￼"  # Shortcuts' placeholder for a variable inside text
NAMESPACE = uuid.UUID("5c0b3b4e-6f1c-4c55-9d43-7a0e2f2d8a61")
ISO_DATE = {
    "Type": "WFDateFormatVariableAggrandizement",
    "WFDateFormatStyle": "ISO 8601",
    "WFISO8601IncludeTime": True,
}


def uid(name: str) -> str:
    return str(uuid.uuid5(NAMESPACE, name)).upper()


def attachment(value: dict) -> dict:
    return {"Value": value, "WFSerializationType": "WFTextTokenAttachment"}


def as_number(token: dict) -> dict:
    """Type a variable as a number, so number conditions like "is not 2" apply."""
    token["Value"]["Aggrandizements"] = [
        {"Type": "WFCoercionVariableAggrandizement", "CoercionItemClass": "WFNumberContentItem"}
    ]
    return token


def named(name: str) -> dict:
    """A Set Variable variable, for outputs the editor won't rename (Ask for Input)."""
    return {"Type": "Variable", "VariableName": name}


def text(string: str, *values: dict) -> dict:
    """Text with variables; each OBJ in `string` takes the next value, in order."""
    attachments, at = {}, 0
    for value in values:
        at = string.index(OBJ, at)
        # Positions count UTF-16 code units, as in NSString.
        attachments[f"{{{len(string[:at].encode('utf-16-le')) // 2}, 1}}"] = value
        at += 1
    return {
        "Value": {"string": string, "attachmentsByRange": attachments},
        "WFSerializationType": "WFTextTokenString",
    }


class Out:
    """A named action output; the name is what the editor shows on its pill."""

    def __init__(self, name: str):
        self.name, self.uuid = name, uid(f"output {name}")

    def ref(self) -> dict:
        return {"OutputName": self.name, "OutputUUID": self.uuid, "Type": "ActionOutput"}

    def var(self) -> dict:
        return attachment(self.ref())


def action(identifier: str, **params) -> dict:
    return {
        "WFWorkflowActionIdentifier": f"is.workflow.actions.{identifier}",
        "WFWorkflowActionParameters": params,
    }


def output(identifier: str, out: Out, **params) -> dict:
    return action(identifier, UUID=out.uuid, CustomOutputName=out.name, **params)


def if_(group: str, condition: int, value: dict, **params) -> dict:
    return action(
        "conditional",
        GroupingIdentifier=uid(f"if {group}"),
        WFControlFlowMode=0,
        WFCondition=condition,
        WFInput={"Type": "Variable", "Variable": value},
        **params,
    )


def otherwise(group: str) -> dict:
    return action("conditional", GroupingIdentifier=uid(f"if {group}"), WFControlFlowMode=1)


def end_if(group: str) -> dict:
    return action(
        "conditional",
        GroupingIdentifier=uid(f"if {group}"),
        WFControlFlowMode=2,
        UUID=uid(f"end if {group}"),
    )


def get(key: str, source: Out, out: Out) -> dict:
    return output("getvalueforkey", out, WFDictionaryKey=key, WFInput=source.var())


def choose(source: Out, prompt: str, names: Out, chosen: Out, value: Out) -> list[dict]:
    """Choose from List on a dictionary shows its values, so pick from its keys instead."""
    return [
        output("getvalueforkey", names, WFGetDictionaryValueType="All Keys", WFInput=source.var()),
        output("choosefromlist", chosen, WFChooseFromListActionPrompt=prompt, WFInput=names.var()),
        output(
            "getvalueforkey",
            value,
            WFGetDictionaryValueType="Value",
            WFDictionaryKey=text(OBJ, chosen.ref()),
            WFInput=source.var(),
        ),
    ]


HAS_ANY_VALUE, IS_NOT = 100, 5


def actions() -> list[dict]:
    market, data, schema = Out("market"), Out("capsule data"), Out("schema")
    machines, machine_names, machine = Out("machines"), Out("machine names"), Out("machine")
    ranges, range_names, range_ = Out("ranges"), Out("range names"), Out("range")
    pods, pod_names, pod, pod_details = (
        Out("pods"),
        Out("pod names"),
        Out("pod"),
        Out("pod details"),
    )
    count_answer, caffeine = Out("pod count answer"), Out("caffeine per pod")
    image, total = Out("pod image"), Out("total caffeine")
    shortcut_input = attachment({"Type": "ExtensionInput"})

    return [
        action(
            "comment",
            WFCommentActionText=(
                "Run with a date as input to log a capsule after the fact; otherwise it logs now."
            ),
        ),
        if_("date", HAS_ANY_VALUE, shortcut_input),
        action(
            "setvariable",
            WFVariableName="date_time",
            WFInput=attachment(
                {
                    "Type": "ExtensionInput",
                    "Aggrandizements": [
                        {
                            "Type": "WFCoercionVariableAggrandizement",
                            "CoercionItemClass": "WFDateContentItem",
                        },
                        ISO_DATE,
                    ],
                }
            ),
        ),
        otherwise("date"),
        action(
            "setvariable",
            WFVariableName="date_time",
            WFInput=attachment({"Type": "CurrentDate", "Aggrandizements": [ISO_DATE]}),
        ),
        end_if("date"),
        action(
            "comment",
            WFCommentActionText=(
                f"Logs Nespresso pod caffeine to Health. Data: {DATA_URL.format('<market>')} "
                "(refreshed weekly from nespresso.com). Markets: tw, sg, or merged (experimental)."
            ),
        ),
        output("gettext", market, WFTextActionText="tw"),
        output("downloadurl", data, WFURL=text(DATA_URL.format(OBJ), market.ref())),
        get("schema", data, schema),
        # A newer schema means this copy is out of date: stop rather than log wrong numbers.
        if_("schema", IS_NOT, as_number(schema.var()), WFNumberValue=str(SCHEMA_VERSION)),
        action(
            "alert",
            WFAlertActionTitle="Please update this Shortcut",
            WFAlertActionMessage="The capsule data has moved to a newer format.",
            WFAlertActionCancelButtonShown=False,
        ),
        action("openurl", WFInput=text(REPO_URL)),
        action("exit"),
        end_if("schema"),
        get("lines", data, machines),
        *choose(machines, "Machine", machine_names, machine, ranges),
        *choose(ranges, "Range", range_names, range_, pods),
        *choose(pods, "Pod", pod_names, pod, pod_details),
        output(
            "ask",
            count_answer,
            WFInputType="Number",
            WFAskActionPrompt="How many pods?",
            WFAskActionDefaultAnswerNumber="1",
        ),
        action("setvariable", WFVariableName="pod count", WFInput=count_answer.var()),
        get("caffeine_mg", pod_details, caffeine),
        get("image_url", pod_details, image),
        if_("caffeine", HAS_ANY_VALUE, caffeine.var()),
        output(
            "math",
            total,
            WFMathOperation="×",
            WFInput=as_number(caffeine.var()),
            WFMathOperand=attachment(named("pod count")),
        ),
        action(
            "health.quantity.log",
            UUID=uid("action log caffeine"),
            WFQuantitySampleType="Caffeine",
            WFQuantitySampleQuantity={
                "Value": {"Magnitude": total.ref(), "Unit": "mg"},
                "WFSerializationType": "WFQuantityFieldValue",
            },
            WFQuantitySampleDate=text(OBJ, named("date_time")),
        ),
        action(
            "notification",
            WFInput=image.var(),
            WFNotificationActionTitle=text(OBJ, pod.ref()),
            WFNotificationActionBody=text(
                f"{OBJ} mg caffeine ☕️ ({OBJ} × {OBJ} mg)",
                total.ref(),
                named("pod count"),
                caffeine.ref(),
            ),
        ),
        otherwise("caffeine"),
        action(
            "notification",
            WFInput=image.var(),
            WFNotificationActionTitle=text(OBJ, pod.ref()),
            WFNotificationActionBody=(
                "Nespresso doesn't list caffeine for this pod, so nothing was logged."
            ),
        ),
        end_if("caffeine"),
    ]


def build() -> dict:
    steps = actions()
    market_index = next(
        i for i, step in enumerate(steps) if step["WFWorkflowActionIdentifier"].endswith("gettext")
    )
    return {
        "WFWorkflowActions": steps,
        "WFWorkflowClientVersion": "1505.1",
        "WFWorkflowIcon": {
            "WFWorkflowIconGlyphNumber": 59789,
            "WFWorkflowIconStartColor": -1448498689,
        },
        "WFWorkflowImportQuestions": [
            {
                "ActionIndex": market_index,
                "Category": "Parameter",
                "DefaultValue": "tw",
                "ParameterKey": "WFTextActionText",
                "Text": "Which market? tw (Taiwan), sg (Singapore) or merged (both, experimental)",
            }
        ],
        "WFWorkflowInputContentItemClasses": ["WFDateContentItem"],
        "WFWorkflowHasShortcutInputVariables": True,
        "WFWorkflowHasOutputFallback": False,
        "WFWorkflowOutputContentItemClasses": [],
        "WFQuickActionSurfaces": [],
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowTypes": ["WatchKit"],
    }


# Keys every action may carry, and the legacy single-condition If keys, which Shortcuts
# still reads and migrates to its newer WFConditions form.
COMMON_KEYS = {"UUID", "GroupingIdentifier", "WFControlFlowMode", "CustomOutputName"}
LEGACY_IF_KEYS = {"WFInput", "WFCondition", "WFConditionalActionString", "WFNumberValue"}


def known_actions() -> dict:
    """Parameter keys and choices for the actions used here, from Apple's own definitions."""
    data = resources.files(__package__).joinpath("shortcut_actions.json").read_text("utf-8")
    return {k: v for k, v in json.loads(data).items() if not k.startswith("_")}


def problems(shortcut: dict) -> list[str]:
    """Structural mistakes the Shortcuts editor would only show on a device."""
    found = []
    steps = shortcut["WFWorkflowActions"]
    outputs: set[str] = set()
    variables: set[str] = set()
    open_blocks: list[dict] = []  # innermost last: {"group": id, "otherwise": seen yet}

    def references(value):
        if isinstance(value, dict):
            if value.get("Type") == "ActionOutput":
                yield "output", value["OutputUUID"]
            elif value.get("Type") == "Variable" and "VariableName" in value:
                yield "variable", value["VariableName"]
            for child in value.values():
                yield from references(child)
        elif isinstance(value, list):
            for child in value:
                yield from references(child)

    for index, step in enumerate(steps):
        params = step["WFWorkflowActionParameters"]
        # A reference must point at an earlier action's output or a variable set before it.
        for kind, target in references(params):
            known = outputs if kind == "output" else variables
            if target not in known:
                found.append(f"action {index}: {kind} {target} is not defined before it")
        if step["WFWorkflowActionIdentifier"].endswith("conditional"):
            group, mode = params["GroupingIdentifier"], params["WFControlFlowMode"]
            if mode == 0:
                open_blocks.append({"group": group, "otherwise": False})
            elif not open_blocks or open_blocks[-1]["group"] != group:
                found.append(f"action {index}: Otherwise or End If without its If")
            elif mode == 1 and open_blocks[-1]["otherwise"]:
                found.append(f"action {index}: a second Otherwise in one If")
            elif mode == 1:
                open_blocks[-1]["otherwise"] = True
            else:
                open_blocks.pop()
        if "UUID" in params:
            outputs.add(params["UUID"])
        if "WFVariableName" in params:
            variables.add(params["WFVariableName"])
    if open_blocks:
        found.append(f"{len(open_blocks)} If without End If")

    # An id names one thing: one action's output, or one If block. A block's id is
    # claimed by its If; its Otherwise and End If share it.
    owners: dict[str, str] = {}
    for index, step in enumerate(steps):
        params = step["WFWorkflowActionParameters"]
        claims = [(params.get("UUID"), f"action {index}")]
        if params.get("WFControlFlowMode") == 0:
            claims.append((params.get("GroupingIdentifier"), f"the If at action {index}"))
        for id_, owner in claims:
            if id_ and owners.setdefault(id_, owner) != owner:
                found.append(f"id {id_} is used by {owners[id_]} and {owner}")

    # Shortcuts silently ignores a misspelt key, so check them against the definitions.
    catalog = known_actions()
    for index, step in enumerate(steps):
        name = step["WFWorkflowActionIdentifier"].removeprefix("is.workflow.actions.")
        params = step["WFWorkflowActionParameters"]
        if name not in catalog:
            found.append(f"action {index}: {name} is not in shortcut_actions.json")
            continue
        allowed = set(catalog[name]["keys"]) | COMMON_KEYS
        if name == "conditional":
            allowed |= LEGACY_IF_KEYS
        for key in sorted(set(params) - allowed):
            found.append(f"action {index}: {name} has no parameter {key}")
        for key, choices in catalog[name].get("choices", {}).items():
            if isinstance(params.get(key), str) and params[key] not in choices:
                found.append(
                    f"action {index}: {name}.{key} {params[key]!r} is not one of {choices}"
                )

    for question in shortcut.get("WFWorkflowImportQuestions", []):
        target = steps[question["ActionIndex"]]["WFWorkflowActionParameters"]
        if question["ParameterKey"] not in target:
            found.append(f"import question {question['Text']!r} points at the wrong action")
    return found


def to_bytes(shortcut: dict) -> bytes:
    return plistlib.dumps(shortcut, fmt=plistlib.FMT_BINARY)
