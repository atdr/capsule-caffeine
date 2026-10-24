"""Building schema v2 documents (`capsules.json`) from scraped markets."""

from importlib.metadata import version

from .promotions import LIMITED, is_promotion, load_range_map
from .scrape import Pod, Range

SCHEMA_VERSION = 2


def pod_entry(pod: Pod) -> dict:
    entry = {
        "id": pod.id,
        "caffeine_mg": pod.caffeine_mg,
        "image_url": pod.image_url,
        "page_url": pod.page_url,
    }
    if pod.caffeine_range_mg:
        entry["caffeine_range_mg"] = list(pod.caffeine_range_mg)
    return entry


def document(lines: dict[str, dict], locales: list[str], generated_at: str, **source) -> dict:
    return {
        "schema": SCHEMA_VERSION,
        "generated_at": generated_at,
        "scraper": version("capsule-caffeine"),
        "source": {"site": "nespresso.com", "language": "en", "locales": locales, **source},
        "lines": lines,
    }


def market_document(
    locale: str, market: dict[str, list[Range]], generated_at: str, range_map: dict | None = None
) -> dict:
    """One market, keeping its own range names. A pod may sit in several ranges.

    Promotions are left out; a pod listed only under one goes to Limited Edition.
    """
    range_map = load_range_map() if range_map is None else range_map
    lines = {}
    for line, ranges in market.items():
        line_ranges: dict[str, dict] = {}
        promoted: dict[str, Pod] = {}
        for range_ in ranges:
            if is_promotion(line, range_.slug, range_map):
                promoted.update((pod.name, pod) for pod in range_.pods)
                continue
            pods = line_ranges.setdefault(range_.name, {})
            for pod in range_.pods:
                pods.setdefault(pod.name, pod_entry(pod))
        listed = {name for pods in line_ranges.values() for name in pods}
        for name, pod in promoted.items():
            if name not in listed:
                line_ranges.setdefault(LIMITED, {})[name] = pod_entry(pod)
        lines[line] = line_ranges
    return document(lines, [locale], generated_at)
