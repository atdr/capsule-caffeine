import pytest

from capsule_caffeine.http import PageError, extract_embedded_json
from capsule_caffeine.scrape import (
    DOMAIN,
    parse_caffeine,
    range_categories,
    scrape_line,
    tidy_name,
)

from .conftest import category, component_page


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
        # No caffeine anchor: other mg figures on the page are not caffeine.
        (["Net weight 50g", "Approx. 60 mg"], (None, None)),
        (["Vitamin B12 0.6mg<br>Sodium 5mg"], (None, None)),
        (["Serving 2 - 5mg"], (None, None)),
        (["Sodium 2 - 5mg per serving"], (None, None)),
        # Real sg Odacio and Bianco Doppio: a range alone in its section, no title.
        (["Net Weight (for 10 capsules):", "108g", "130 - 200mg per cup"], (165, (130, 200))),
        (["Made in Switzerland", "81mg - 130mg"], (106, (81, 130))),
        (["Decaffeinated coffee with 3mg of sodium"], (None, None)),
        (["Vitamin B6 1.4mg", "Per serving of caffeine is 80mg/40ml"], (80, None)),
        (["Sodium 5mg", "CAFFEINE", "7mg - 80mg"], (44, (7, 80))),
        # The real sg Caramello sections, with the figure after the CAFFEINE title.
        (
            [
                "10 capsules of caramel flavoured roast and ground coffee for the "
                "Nespresso system. Packaged in a protective atmosphere.",
                "INGREDIENTS & ALLERGENS",
                "Roast and ground coffee with natural caramel flavouring only",
                "NET WEIGHT (FOR 10 CAPSULES)",
                "47g",
                "MADE IN SWITZERLAND BY NESTLÉ NESPRESSO S.A.",
                "CAFFEINE",
                "7mg - 80mg",
            ],
            (44, (7, 80)),
        ),
        # The real tw Altissio Decaffeinato sections: "4g" is a typo for 4 mg.
        (
            [
                "10 capsules of roast and ground coffee for the Nespresso Vertuo "
                "system.<br>INGREDIENTS: Roast and ground coffee only.",
                "NET WEIGHT",
                "70g (7g*10 capsule)<br>Per serving of caffeine is 4g/40ml",
                "Producer",
                "MADE IN SWITZERLAND BY NESTLÉ NESPRESSO S.A.",
            ],
            (4, None),
        ),
        # A gram figure is read as mg only when it is a single digit per serving.
        (["Per serving of caffeine is 40g/40ml"], (None, None)),
        (["Per serving of caffeine is 4000g/40ml"], (None, None)),
        (["Per serving of caffeine is 4g"], (None, None)),
        (["NET WEIGHT 7g/40ml"], (None, None)),
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


def test_range_categories_skip_unnamed_badges():
    espresso = category("sg", "capsule-range-espresso", "Espresso")
    badge = category("sg", "capsule-range-label-limited-edition", None)
    assert range_categories([espresso, badge]) == [espresso]
