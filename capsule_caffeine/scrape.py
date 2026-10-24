"""Scraping capsule ranges and their caffeine content from nespresso.com."""

import logging
import re

import requests

from .http import fetch_embedded_json

DOMAIN = "https://www.nespresso.com"
LISTING_SELECTOR = "div[id^=respProductListPLPCapsule]+script"
PRODUCT_SELECTOR = "div[id^=respProductDetailPDPCapsule]+script"
CAFFEINE_RE = re.compile(r"(\d+)\s?mg")
EXCLUDED_RANGES = ("capsule-range-limited-edition-b2c", "capsule-range-assortment")

log = logging.getLogger(__name__)


def capsule_ranges(categories: list[dict], locale: str) -> list[dict]:
    prefix = f"nesclub2.{locale}.b2c/cat/"
    excluded = {prefix + name for name in EXCLUDED_RANGES}
    return [
        c
        for c in categories
        if prefix + "capsule-range" in c.get("superCategories", []) and c["id"] not in excluded
    ]


def pods_in_range(products: list[dict], range_id: str) -> list[dict]:
    """Single capsules in a range, leaving out sleeves and bundles."""
    return [
        p
        for p in products
        if range_id in p.get("ranges", [])
        and p.get("type") == "capsule"
        and p.get("unitQuantity") == 1
    ]


def parse_caffeine(product: dict) -> int | None:
    """Caffeine in mg, read from the product's ingredients text."""
    text = " ".join(i.get("text", "") for i in product.get("ingredients", []))
    match = CAFFEINE_RE.search(text)
    return int(match.group(1)) if match else None


def scrape(session: requests.Session, locale: str = "tw", line: str = "original") -> dict:
    """Return {range name: {pod name: {caffeine_mg, image_url}}}."""
    listing_url = f"{DOMAIN}/{locale}/en/order/capsules/{line}"
    listing = fetch_embedded_json(session, listing_url, LISTING_SELECTOR)
    data = listing["configuration"]["eCommerceData"]

    result = {}
    for range_ in capsule_ranges(data["categories"], locale):
        log.info("Range: %s", range_["name"])
        pods = {}
        for item in pods_in_range(data["products"], range_["id"]):
            page = fetch_embedded_json(session, DOMAIN + item["url"], PRODUCT_SELECTOR)
            product = page["configuration"]["eCommerceData"]["product"]
            caffeine_mg = parse_caffeine(product)
            if caffeine_mg is None:
                log.warning("No caffeine value for %s", product["name"])
            log.info("  %s: %s mg", product["name"], caffeine_mg)
            pods[product["name"]] = {
                "caffeine_mg": caffeine_mg,
                "image_url": DOMAIN + product["image"]["url"],
            }
        result[range_["name"]] = pods
    return result
