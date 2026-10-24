import pytest

from capsule_caffeine.http import PageError, extract_embedded_json
from capsule_caffeine.scrape import DOMAIN, parse_caffeine, scrape_line, tidy_name

from .conftest import component_page


def test_extract_embedded_json_reads_the_script_after_the_div():
    html = component_page("respThing", {"a": {"b": 1}})
    assert extract_embedded_json(html, "div[id^=respThing]+script") == {"a": {"b": 1}}


def test_extract_embedded_json_raises_when_the_component_is_missing():
    with pytest.raises(PageError):
        extract_embedded_json("<html></html>", "div[id^=respThing]+script")


@pytest.mark.parametrize(
    ("texts", "expected"),
    [
        (["125g (10 Capsules)<br>Per serving of Caffine is 140mg/230ml"], (140, None)),
        (["Net weight 50g", "Approx. 60 mg"], (60, None)),
        (["NET WEIGHT", "100g", "CAFFEINE", "120 – 300mg per cup"], (210, (120, 300))),
        (["CAFFEINE", "7mg - 80mg"], (44, (7, 80))),
        (["CAFFEINE", "125 - 312.5mg per cup"], (219, (125, 312.5))),
        (["Roast and ground coffee only", "300g"], (None, None)),
    ],
)
def test_parse_caffeine(texts, expected):
    assert parse_caffeine({"ingredients": [{"text": t} for t in texts]}) == expected


def test_tidy_name():
    assert tidy_name("  The Original Collection\u200b ") == "The Original Collection"
    assert tidy_name("ISPIRAZIONE ITALIANA") == "Ispirazione Italiana"
    assert tidy_name("Starbucks® by Nespresso") == "Starbucks® by Nespresso"
    assert tidy_name("ESPRESSOS (25ml - 80ml)") == "Espressos (25ml - 80ml)"
    assert tidy_name("NESPRESSO | BLUE BOTTLE COFFEE") == "Nespresso | Blue Bottle Coffee"
    assert tidy_name("COFFEE+") == "Coffee+"


def test_scrape_line(original_tw):
    ranges = scrape_line(original_tw, "tw", "Original")

    assert [(r.slug, r.name) for r in ranges] == [
        ("capsule-range-espressos", "Espresso"),
        ("capsule-range-recommends-2", "Special Offer"),
    ]
    ristretto, arpeggio = ranges[0].pods
    assert ristretto.caffeine_mg == 120
    assert ristretto.image_url == f"{DOMAIN}/img/small.png"
    assert arpeggio.name == "Arpeggio"
    assert arpeggio.image_url == f"{DOMAIN}/img/large.png?imwidth=200"
    assert ranges[1].pods == [ristretto]
    # Ristretto sits in two ranges but its page is fetched once; the sleeve never.
    assert sorted(original_tw.requests) == [
        f"{DOMAIN}/p/arpeggio",
        f"{DOMAIN}/p/ristretto",
        f"{DOMAIN}/tw/en/order/capsules/original",
    ]
