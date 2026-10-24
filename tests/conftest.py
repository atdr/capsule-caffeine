"""Hand-made stand-ins for nespresso.com pages. Pods and numbers are invented."""

import json

import pytest

from capsule_caffeine.scrape import DOMAIN


def component_page(component_id: str, payload: dict) -> str:
    """A page shaped like Nespresso's: a mount <div> followed by a data <script>."""
    return (
        f'<html><body><div id="{component_id}-1234"></div>'
        f"<script>window.component = {json.dumps(payload)};</script></body></html>"
    )


def listing_page(categories: list[dict], products: list[dict]) -> str:
    data = {"categories": categories, "products": products}
    return component_page("respProductListPLPCapsule", {"configuration": {"eCommerceData": data}})


def product_page(name: str, ingredients: list[str], image: str = "/img/large.png") -> str:
    product = {
        "name": name,
        "ingredients": [{"text": t} for t in ingredients],
        "image": {"url": image},
    }
    return component_page(
        "respProductDetailPDPCapsule", {"configuration": {"eCommerceData": {"product": product}}}
    )


def category(locale: str, slug: str, name: str, parent: str = "capsule-range") -> dict:
    prefix = f"nesclub2.{locale}.b2c/cat/"
    return {"id": prefix + slug, "name": name, "superCategories": [prefix + parent]}


def product(locale, url, ranges, *, unit_quantity=1, image="/img/small.png", pid="1000.80"):
    prefix = f"nesclub2.{locale}.b2c/cat/"
    return {
        "internationalId": pid,
        "url": url,
        "type": "capsule",
        "unitQuantity": unit_quantity,
        "ranges": [prefix + r for r in ranges],
        "image": {"url": image} if image else None,
    }


class FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        pass


class FakeSession:
    """Serves pages from a {url: html} dict and records every request."""

    def __init__(self, pages: dict[str, str]):
        self.pages = pages
        self.requests: list[str] = []

    def get(self, url, timeout=None):
        self.requests.append(url)
        return FakeResponse(self.pages[url])


@pytest.fixture
def original_tw() -> FakeSession:
    """tw Original: one real range, one promo, one empty range, plus a bundle."""
    categories = [
        category("tw", "capsule-range-espressos", "Espresso"),
        category("tw", "capsule-range-recommends-2", "SPECIAL OFFER"),
        category("tw", "capsule-range-assortment", "Assortment"),
        category("tw", "capsule-aromatic-intense", "Intense", parent="capsule-aromatic"),
    ]
    products = [
        product("tw", "/p/ristretto", ["capsule-range-espressos", "capsule-range-recommends-2"]),
        product("tw", "/p/arpeggio", ["capsule-range-espressos"], image=None, pid="1001.80"),
        product("tw", "/p/sleeve", ["capsule-range-assortment"], unit_quantity=50),
    ]
    return FakeSession(
        {
            f"{DOMAIN}/tw/en/order/capsules/original": listing_page(categories, products),
            f"{DOMAIN}/p/ristretto": product_page(
                "Ristretto", ["Net weight", "Per serving of caffeine is 120mg/25ml"]
            ),
            f"{DOMAIN}/p/arpeggio": product_page("ARPEGGIO", ["Approx. 60 mg per cup"]),
        }
    )
