"""Comparing two builds, for deciding whether to publish and for release notes."""

from dataclasses import dataclass, field

IGNORED_KEYS = ("generated_at", "scraper")


@dataclass
class Changes:
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    caffeine: list[str] = field(default_factory=list)
    moved: list[str] = field(default_factory=list)
    other: bool = False

    def __bool__(self) -> bool:
        return bool(self.added or self.removed or self.caffeine or self.moved or self.other)


def _pods(document: dict) -> dict[tuple[str, str], tuple[set[str], int | None]]:
    """{(line, pod name): (ranges, caffeine_mg)}"""
    pods: dict[tuple[str, str], tuple[set[str], int | None]] = {}
    for line, ranges in document["lines"].items():
        for range_name, range_pods in ranges.items():
            for name, pod in range_pods.items():
                pods.setdefault((line, name), (set(), pod["caffeine_mg"]))[0].add(range_name)
    return pods


def _content(document: dict | None) -> dict | None:
    if document is None:
        return None
    return {k: v for k, v in document.items() if k not in IGNORED_KEYS}


def compare(old: dict | None, new: dict) -> Changes:
    """What changed from `old` (None when there was no previous build) to `new`."""
    changes = Changes()
    if _content(old) == _content(new):
        return changes
    old_pods = _pods(old) if old else {}
    new_pods = _pods(new)
    for key in sorted(new_pods.keys() - old_pods.keys()):
        changes.added.append(_label(key, new_pods[key][1]))
    for key in sorted(old_pods.keys() - new_pods.keys()):
        changes.removed.append(_label(key, old_pods[key][1]))
    for key in sorted(old_pods.keys() & new_pods.keys()):
        (old_ranges, old_mg), (new_ranges, new_mg) = old_pods[key], new_pods[key]
        if old_mg != new_mg:
            changes.caffeine.append(f"{key[0]} / {key[1]}: {_mg(old_mg)} → {_mg(new_mg)}")
        if old_ranges != new_ranges:
            changes.moved.append(
                f"{key[0]} / {key[1]}: {', '.join(sorted(old_ranges))} → "
                f"{', '.join(sorted(new_ranges))}"
            )
    changes.other = not (changes.added or changes.removed or changes.caffeine or changes.moved)
    return changes


def _mg(value: int | None) -> str:
    return "no value" if value is None else f"{value} mg"


def _label(key: tuple[str, str], caffeine_mg: int | None) -> str:
    return f"{key[0]} / {key[1]} ({_mg(caffeine_mg)})"


def summary(changes_by_name: dict[str, Changes]) -> str:
    """Markdown release notes for the files that changed."""
    sections = []
    for name, changes in changes_by_name.items():
        if not changes:
            continue
        parts = [f"### {name}"]
        for title, items in (
            ("Added", changes.added),
            ("Removed", changes.removed),
            ("Caffeine changed", changes.caffeine),
            ("Moved between ranges", changes.moved),
        ):
            if items:
                parts.append(f"**{title}**\n" + "\n".join(f"- {item}" for item in items))
        if changes.other:
            parts.append("Images or links changed.")
        sections.append("\n\n".join(parts))
    return "\n\n".join(sections) if sections else "No changes."
