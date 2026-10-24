import json

from capsule_caffeine.cli import main
from capsule_caffeine.document import market_document
from capsule_caffeine.scrape import scrape_market

NOW = "2026-10-24T12:00:00Z"


def test_site_builds_from_a_build(original_tw, tmp_path):
    build = tmp_path / "dist"
    (build / "tw").mkdir(parents=True)
    doc = market_document("tw", scrape_market(original_tw, "tw", ["Original"]), NOW)
    doc["lines"]["Original"]["Espresso"]["Arpeggio"]["caffeine_range_mg"] = [7, 80.5]
    (build / "tw" / "capsules.json").write_text(json.dumps(doc), encoding="utf-8")

    assert main(["site", str(build), "-o", str(tmp_path / "site")]) == 0

    site = tmp_path / "site"
    assert json.loads((site / "tw" / "capsules.json").read_text()) == doc
    assert json.loads((site / "capsules.schema.json").read_text())["title"].endswith("schema 2")
    assert 'href="tw/"' in (site / "index.html").read_text()
    html = (site / "tw" / "index.html").read_text()
    assert "<caption>Original</caption>" in html
    assert '>Ristretto</a></td><td class="mg">120 mg</td>' in html
    assert "(7 to 80.5)" in html
    assert "not affiliated" in html
    assert "<img" not in html


def test_site_needs_a_build(tmp_path):
    assert main(["site", str(tmp_path), "-o", str(tmp_path / "site")]) == 1
    assert main(["site", str(tmp_path / "missing"), "-o", str(tmp_path / "site")]) == 1


def test_site_rebuild_drops_markets_no_longer_built(original_tw, tmp_path):
    build, site = tmp_path / "dist", tmp_path / "site"
    doc = market_document("tw", scrape_market(original_tw, "tw", ["Original"]), NOW)
    for market in ("tw", "sg"):
        (build / market).mkdir(parents=True)
        (build / market / "capsules.json").write_text(json.dumps(doc), encoding="utf-8")
    (site / "notes").mkdir(parents=True)
    (site / "notes" / "keep.txt").write_text("not ours")
    assert main(["site", str(build), "-o", str(site)]) == 0

    (build / "sg" / "capsules.json").unlink()
    assert main(["site", str(build), "-o", str(site)]) == 0

    assert sorted(p.name for p in site.iterdir()) == [
        "capsules.schema.json",
        "index.html",
        "notes",
        "tw",
    ]
    # Building into the input directory leaves its files in place.
    assert main(["site", str(build), "-o", str(build)]) == 0
    assert json.loads((build / "tw" / "capsules.json").read_text()) == doc
