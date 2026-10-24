"""Scraping capsule ranges and their caffeine content for one nespresso.com market."""

import logging
import re
import time
from dataclasses import dataclass, field

import requests

from .http import fetch_embedded_json

DOMAIN = "https://www.nespresso.com"
LISTING_SELECTOR = "div[id^=respProductListPLPCapsule]+script"
PRODUCT_SELECTOR = "div[id^=respProductDetailPDPCapsule]+script"
LINES = {
    "Original": "/{locale}/en/order/capsules/original",
    "Vertuo": "/{locale}/en/order/capsules/vertuo",
    "Pro": "/pro/{locale}/en/order/capsules/pro",
}
# English-language markets that publish caffeine content, in priority order. au, hk, my
# and nz run the same site but give no caffeine values; uk, us, ca and ie run another site.
LOCALES = ("tw", "sg")
NUMBER = r"(\d+(?:\.\d+)?)"
# sg gives a range: "120 – 300mg per cup", "7mg - 80mg".
CAFFEINE_RANGE = re.compile(rf"{NUMBER}\s?(?:mg)?\s*[-–—]\s*{NUMBER}\s?mg", re.IGNORECASE)
# tw says "Per serving of caffeine is 133mg/80ml"; older pages just "60 mg".
CAFFEINE_PATTERNS = (
    re.compile(rf"caff\w*\D{{0,20}}?{NUMBER}\s?mg", re.IGNORECASE),
    re.compile(rf"{NUMBER}\s?mg", re.IGNORECASE),
)
# Product page images are 2000px; the image server resizes them on request.
FALLBACK_IMAGE_WIDTH = 200
ZERO_WIDTH = re.compile(r"[\u200b-\u200d\ufeff]")
PARENTHESISED = re.compile(r"\([^)]*\)")

log = logging.getLogger(__name__)


@dataclass
class Pod:
    name: str
    id: str
    caffeine_mg: int | None
    image_url: str
    page_url: str
    caffeine_range_mg: tuple[float, float] | None = None


@dataclass
class Range:
    slug: str
    name: str
    pods: list[Pod] = field(default_factory=list)


def tidy_name(name: str) -> str:
    """Strip invisible characters and spacing; turn SHOUTED NAMES into title case.

    Parenthesised sizes such as "(25ml - 80ml)" are left alone.
    """
    words = ZERO_WIDTH.sub("", name).split()
    outside_brackets = PARENTHESISED.sub("", " ".join(words))
    if any(c.isalpha() for c in outside_brackets) and outside_brackets.isupper():
        words = [w.capitalize() if w.isupper() else w for w in words]
    return " ".join(words)


def range_categories(categories: list[dict]) -> list[dict]:
    """Named categories that are capsule ranges (children of `.../cat/capsule-range`).

    Unnamed ones, such as sg's limited edition label, are badges rather than ranges.
    """
    return [
        c
        for c in categories
        if c.get("name")
        and any(s.endswith("/cat/capsule-range") for s in c.get("superCategories") or [])
    ]


def range_slug(category_id: str) -> str:
    """`nesclub2.tw.b2c/cat/capsule-range-espressos` -> `capsule-range-espressos`."""
    return category_id.rsplit("/cat/", 1)[-1]


def pods_in_range(products: list[dict], range_id: str) -> list[dict]:
    """Single capsules in a range, leaving out sleeves and bundles."""
    return [
        p
        for p in products
        if range_id in p.get("ranges", [])
        and p.get("type") == "capsule"
        and p.get("unitQuantity") == 1
    ]


def _round(value: float) -> int:
    return int(value + 0.5)


def _number(text: str) -> float:
    value = float(text)
    return int(value) if value.is_integer() else value


def parse_caffeine(product: dict) -> tuple[int | None, tuple[float, float] | None]:
    """(caffeine in mg, (low, high) when the page gives a range) from the ingredients text.

    For a range the single value is its midpoint.
    """
    text = " ".join(i.get("text", "") for i in product.get("ingredients", []))
    if match := CAFFEINE_RANGE.search(text):
        low, high = sorted((_number(match.group(1)), _number(match.group(2))))
        return _round((low + high) / 2), (low, high)
    for pattern in CAFFEINE_PATTERNS:
        if match := pattern.search(text):
            return _round(float(match.group(1))), None
    return None, None


def image_url(item: dict, product: dict) -> str:
    """The small listing image (320px), else the product image resized."""
    if url := (item.get("image") or {}).get("url"):
        return DOMAIN + url
    return f"{DOMAIN}{product['image']['url']}?imwidth={FALLBACK_IMAGE_WIDTH}"


def scrape_pod(session: requests.Session, item: dict) -> Pod:
    page_url = DOMAIN + item["url"]
    page = fetch_embedded_json(session, page_url, PRODUCT_SELECTOR)
    product = page["configuration"]["eCommerceData"]["product"]
    caffeine_mg, caffeine_range_mg = parse_caffeine(product)
    pod = Pod(
        name=tidy_name(product["name"]),
        id=item["internationalId"],
        caffeine_mg=caffeine_mg,
        image_url=image_url(item, product),
        page_url=page_url,
        caffeine_range_mg=caffeine_range_mg,
    )
    if pod.caffeine_mg is None:
        log.warning("No caffeine value for %s (%s)", pod.name, page_url)
    log.info("  %s: %s mg", pod.name, pod.caffeine_mg)
    return pod


def scrape_line(
    session: requests.Session, locale: str, line: str, delay_s: float = 0.0
) -> list[Range]:
    listing_url = DOMAIN + LINES[line].format(locale=locale)
    data = fetch_embedded_json(session, listing_url, LISTING_SELECTOR)["configuration"][
        "eCommerceData"
    ]
    # A pod listed in several ranges is fetched once.
    pods_by_url: dict[str, Pod] = {}
    ranges = []
    for category in range_categories(data["categories"]):
        range_ = Range(range_slug(category["id"]), tidy_name(category["name"]))
        log.info("%s %s: %s", locale, line, range_.name)
        for item in pods_in_range(data["products"], category["id"]):
            if item["url"] not in pods_by_url:
                pods_by_url[item["url"]] = scrape_pod(session, item)
                time.sleep(delay_s)
            range_.pods.append(pods_by_url[item["url"]])
        if range_.pods:
            ranges.append(range_)
    return ranges


def scrape_market(
    session: requests.Session, locale: str, lines=tuple(LINES), delay_s: float = 0.0
) -> dict[str, list[Range]]:
    """Return {line: [Range]} for one market."""
    return {line: scrape_line(session, locale, line, delay_s) for line in lines}
