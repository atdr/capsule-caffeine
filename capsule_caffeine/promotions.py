"""The curated range map (`ranges.json`) and the promotions it marks.

It maps each market's range slug to a shared name, or to null for promotions and
assortments (Special Offer, Coffee of the Month), which say nothing about a pod.
"""

import json
from importlib import resources

LIMITED = "Limited Edition"


def load_range_map() -> dict[str, dict[str, str | None]]:
    return json.loads(resources.files(__package__).joinpath("ranges.json").read_text())


def is_promotion(line: str, slug: str, range_map: dict) -> bool:
    line_map = range_map.get(line, {})
    return slug in line_map and line_map[slug] is None
