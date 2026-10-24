"""Experimental: merging several markets into one document.

Product ids differ between markets and so do range slugs and names, so pods are
matched by normalised name and ranges are renamed through `ranges.json`, which maps
each market's range slug to a shared name (null for promotions and assortments).
"""

import logging
import re
from dataclasses import dataclass, field

from .document import document
from .promotions import LIMITED, load_range_map
from .scrape import Pod, Range

BOX_SUFFIX = re.compile(r"\b\d+\s*capsules?\s*box\b")
NON_WORD = re.compile(r"[^\w+]+")

log = logging.getLogger(__name__)


def pod_key(name: str) -> str:
    """`Starbucks® Blonde Espresso Roast 50 Capsules Box` -> `starbucks blonde espresso roast`."""
    name = BOX_SUFFIX.sub("", name.casefold())
    return " ".join(NON_WORD.sub(" ", name).split())


@dataclass
class MergedPod:
    name: str
    caffeine_mg: int | None
    image_url: str
    page_url: str
    caffeine_range_mg: tuple[float, float] | None = None
    ranges: list[str] = field(default_factory=list)
    available_in: list[str] = field(default_factory=list)


def canonical_range(line: str, range_: Range, locale: str, range_map: dict) -> str | None:
    line_map = range_map.get(line, {})
    if range_.slug in line_map:
        return line_map[range_.slug]
    log.warning("Unmapped %s range %s (%r) in %s", line, range_.slug, range_.name, locale)
    return range_.name


def disagrees(entry: MergedPod, pod: Pod) -> bool:
    """A later market's figure contradicts the one already chosen."""
    if pod.caffeine_mg is None or entry.caffeine_mg is None:
        return False
    if pod.caffeine_range_mg:
        low, high = pod.caffeine_range_mg
        return not low <= entry.caffeine_mg <= high
    return pod.caffeine_mg != entry.caffeine_mg


def merge_markets(
    markets: dict[str, dict[str, list[Range]]], generated_at: str, range_map: dict | None = None
) -> dict:
    """Merge {locale: {line: [Range]}}; earlier locales win names, links and caffeine."""
    range_map = load_range_map() if range_map is None else range_map
    merged: dict[str, dict[str, MergedPod]] = {}
    for locale, market in markets.items():
        for line, ranges in market.items():
            line_pods = merged.setdefault(line, {})
            for range_ in ranges:
                shared_range = canonical_range(line, range_, locale, range_map)
                for pod in range_.pods:
                    key = pod_key(pod.name)
                    if key not in line_pods:
                        line_pods[key] = MergedPod(
                            pod.name,
                            pod.caffeine_mg,
                            pod.image_url,
                            pod.page_url,
                            pod.caffeine_range_mg,
                        )
                    entry = line_pods[key]
                    if locale not in entry.available_in:
                        entry.available_in.append(locale)
                    if shared_range and shared_range not in entry.ranges:
                        entry.ranges.append(shared_range)
                    if entry.caffeine_mg is None:
                        entry.caffeine_mg = pod.caffeine_mg
                        entry.caffeine_range_mg = pod.caffeine_range_mg
                    elif disagrees(entry, pod):
                        log.warning(
                            "%s %s: %s in %s, %s mg earlier",
                            line,
                            entry.name,
                            "–".join(map(str, pod.caffeine_range_mg or [pod.caffeine_mg])) + " mg",
                            locale,
                            entry.caffeine_mg,
                        )

    lines: dict[str, dict] = {}
    for line, line_pods in merged.items():
        line_ranges: dict[str, dict] = {}
        for entry in line_pods.values():
            # Pods listed only under promotions still need a home.
            for range_name in entry.ranges or [LIMITED]:
                pod_entry = {
                    "caffeine_mg": entry.caffeine_mg,
                    "image_url": entry.image_url,
                    "page_url": entry.page_url,
                    "available_in": entry.available_in,
                }
                if entry.caffeine_range_mg:
                    pod_entry["caffeine_range_mg"] = list(entry.caffeine_range_mg)
                line_ranges.setdefault(range_name, {})[entry.name] = pod_entry
        lines[line] = line_ranges
    return document(lines, list(markets), generated_at, merged=True)
