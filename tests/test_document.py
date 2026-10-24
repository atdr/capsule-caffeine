from capsule_caffeine.document import market_document
from capsule_caffeine.merge import MergedPod, disagrees, merge_markets, pod_key
from capsule_caffeine.scrape import Pod, Range, scrape_market
from capsule_caffeine.validate import problems, schema_problems

NOW = "2026-10-24T12:00:00Z"


def pod(name, caffeine_mg=60, caffeine_range_mg=None):
    return Pod(
        name, "1", caffeine_mg, f"https://x/{name}.png", f"https://x/{name}", caffeine_range_mg
    )


def test_disagreement_respects_ranges():
    chosen = MergedPod("Lungo", 75, "", "")
    assert not disagrees(chosen, pod("Lungo", 44, (7, 80)))
    assert disagrees(chosen, pod("Lungo", 210, (120, 300)))
    assert disagrees(chosen, pod("Lungo", 80))


def test_market_document_keeps_market_ranges(original_tw):
    doc = market_document("tw", scrape_market(original_tw, "tw", ["Original"]), NOW)

    assert schema_problems(doc) == []
    assert doc["source"]["locales"] == ["tw"]
    # Special Offer is a promotion, and Ristretto is listed under Espresso too.
    assert set(doc["lines"]["Original"]) == {"Espresso"}
    assert doc["lines"]["Original"]["Espresso"]["Ristretto"]["caffeine_mg"] == 120


def test_market_document_drops_only_promotions_that_repeat_other_ranges():
    range_map = {"Original": {"offer": None, "autumn": None, "espresso": "Espresso"}}
    market = {
        "Original": [
            Range("espresso", "Espresso", [pod("Ristretto")]),
            Range("offer", "Special Offer", [pod("Ristretto")]),
            Range("autumn", "Autumn Selection", [pod("Ristretto"), pod("Maple")]),
            # Only in promotions: neither may vanish.
            Range("offer", "Special Offer", [pod("Pecan")]),
            Range("autumn", "Autumn Selection", [pod("Pecan")]),
        ]
    }

    lines = market_document("tw", market, NOW, range_map)["lines"]["Original"]

    assert {r: list(p) for r, p in lines.items()} == {
        "Espresso": ["Ristretto"],
        "Autumn Selection": ["Ristretto", "Maple", "Pecan"],
        "Special Offer": ["Pecan"],
    }


def test_pod_key_ignores_case_marks_and_box_size():
    assert pod_key("Starbucks® Blonde Espresso Roast 50 Capsules Box") == pod_key(
        "STARBUCKS BLONDE ESPRESSO ROAST"
    )
    assert pod_key("Coffee+ Ginseng") != pod_key("Coffee Ginseng")


def test_merge_markets():
    range_map = {"Pro": {"classic-b2b": "Classics", "new-b2b": None, "classics-b2b": "Classics"}}
    markets = {
        "tw": {
            "Pro": [
                Range("classic-b2b", "Classic", [pod("Ristretto 50 Capsule Box", 95)]),
                Range("new-b2b", "New", [pod("Amaretti", 1)]),
            ]
        },
        "sg": {
            "Pro": [
                Range(
                    "classics-b2b",
                    "Classics",
                    [pod("Ristretto", 90, (60, 120)), pod("Lungo", None)],
                ),
                Range("odd-b2b", "Odd One", [pod("Lungo", 70, (40, 100))]),
            ]
        },
    }

    doc = merge_markets(markets, NOW, range_map)
    pro = doc["lines"]["Pro"]

    assert schema_problems(doc) == []
    assert doc["source"] == {
        "site": "nespresso.com",
        "language": "en",
        "locales": ["tw", "sg"],
        "merged": True,
    }
    # Matched across markets by name; the first market's name and caffeine win.
    assert pro["Classics"]["Ristretto 50 Capsule Box"]["caffeine_mg"] == 95
    assert pro["Classics"]["Ristretto 50 Capsule Box"]["available_in"] == ["tw", "sg"]
    # A later market fills a missing value; an unmapped range keeps its own name.
    assert pro["Classics"]["Ristretto 50 Capsule Box"].get("caffeine_range_mg") is None
    assert pro["Classics"]["Lungo"]["caffeine_mg"] == 70
    assert pro["Classics"]["Lungo"]["caffeine_range_mg"] == [40, 100]
    assert pro["Odd One"]["Lungo"]["available_in"] == ["sg"]
    # Promotions are dropped, so a pod found only there goes under Limited Edition.
    assert set(pro) == {"Classics", "Odd One", "Limited Edition"}
    assert pro["Limited Edition"]["Amaretti"]["caffeine_mg"] == 1


def test_problems_flags_thin_or_caffeine_free_data():
    lines = {"Original": {"Espresso": {f"Pod {i}": {} for i in range(3)}}}
    doc = {
        "schema": 2,
        "generated_at": NOW,
        "scraper": "2.0.0",
        "source": {"site": "nespresso.com", "language": "en", "locales": ["tw"]},
        "lines": lines,
    }
    for name in lines["Original"]["Espresso"]:
        lines["Original"]["Espresso"][name] = {
            "caffeine_mg": None,
            "image_url": "https://x/i.png",
            "page_url": "https://x/p",
        }

    assert problems(doc) == [
        "Original: only 3 pods, expected at least 10",
        "3 of 3 pods have no caffeine value",
    ]
    doc["schema"] = 1
    assert problems(doc) == ["schema: 2 was expected"]
