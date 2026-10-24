"""Building schema v2 documents (`capsules.json`) from scraped markets."""

from importlib.metadata import version

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


def market_document(locale: str, market: dict[str, list[Range]], generated_at: str) -> dict:
    """One market, keeping its own range names. A pod may sit in several ranges."""
    lines = {}
    for line, ranges in market.items():
        line_ranges: dict[str, dict] = {}
        for range_ in ranges:
            pods = line_ranges.setdefault(range_.name, {})
            for pod in range_.pods:
                pods.setdefault(pod.name, pod_entry(pod))
        lines[line] = line_ranges
    return document(lines, [locale], generated_at)
