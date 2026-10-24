"""Checks a document must pass before it is published."""

import json
from importlib import resources

from jsonschema import Draft202012Validator

# Well below the counts seen in October 2026; a drop under these means a broken page.
MIN_PODS = {"Original": 10, "Vertuo": 10, "Pro": 3}
MAX_MISSING_CAFFEINE = 0.5


def load_schema() -> dict:
    return json.loads(resources.files(__package__).joinpath("capsules.schema.json").read_text())


def schema_problems(document: dict) -> list[str]:
    return [
        f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}"
        for e in Draft202012Validator(load_schema()).iter_errors(document)
    ]


def problems(document: dict) -> list[str]:
    """Everything wrong with `document`; empty when it is fit to publish."""
    found = schema_problems(document)
    if found:
        return found

    total = missing = 0
    for line, ranges in document["lines"].items():
        pods = {name: pod for range_pods in ranges.values() for name, pod in range_pods.items()}
        min_pods = MIN_PODS.get(line, 1)
        if len(pods) < min_pods:
            found.append(f"{line}: only {len(pods)} pods, expected at least {min_pods}")
        total += len(pods)
        missing += sum(1 for pod in pods.values() if pod["caffeine_mg"] is None)
    if total and missing / total > MAX_MISSING_CAFFEINE:
        found.append(f"{missing} of {total} pods have no caffeine value")
    return found
