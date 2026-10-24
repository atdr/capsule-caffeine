"""A static site from a build: each market's capsules.json plus a plain HTML table.

The pages show facts only (names, caffeine, a link to the product page), so no
images, descriptions or Nespresso branding are copied onto them.
"""

import json
import shutil
from html import escape
from importlib.resources import files
from pathlib import Path

INDEX = "index.html"
SCHEMA = "capsules.schema.json"
REPO = "https://github.com/atdr/capsule-caffeine"

STYLE = """
:root { color-scheme: light dark; --fg: #1d1d1f; --bg: #fff; --muted: #6e6e73; --rule: #d2d2d7; }
@media (prefers-color-scheme: dark) {
  :root { --fg: #f5f5f7; --bg: #1c1c1e; --muted: #a1a1a6; --rule: #3a3a3c; }
}
body { font: 16px/1.5 system-ui, sans-serif; color: var(--fg); background: var(--bg);
  max-width: 48rem; margin: 0 auto; padding: 1rem; }
a { color: inherit; }
table { width: 100%; border-collapse: collapse; margin-bottom: 2rem; }
th, td { text-align: left; padding: 0.25rem 0.5rem 0.25rem 0;
  border-bottom: 1px solid var(--rule); }
td.mg { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
caption { text-align: left; font-weight: 600; padding: 0.5rem 0; }
footer, .muted { color: var(--muted); font-size: 0.875rem; }
"""

DISCLAIMER = (
    "Caffeine figures are scraped from nespresso.com and may be wrong or out of date; "
    "check the product page before relying on them. Nespresso is a trademark of "
    "Société des Produits Nestlé S.A. This project is not affiliated with or endorsed by Nestlé, "
    "and the data is not covered by the project's MIT License."
)


def page(title: str, body: str) -> str:
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escape(title)}</title>\n<style>{STYLE}</style>\n</head>\n<body>\n{body}"
        f"<footer><p>{escape(DISCLAIMER)}</p>"
        f'<p>Built by <a href="{REPO}">capsule-caffeine</a>.</p></footer>\n</body>\n</html>\n'
    )


def caffeine(pod: dict) -> str:
    if pod["caffeine_mg"] is None:
        return "unknown"
    if low_high := pod.get("caffeine_range_mg"):
        low, high = (f"{v:g}" for v in low_high)
        return f"{pod['caffeine_mg']} mg ({low} to {high})"
    return f"{pod['caffeine_mg']} mg"


def market_page(name: str, document: dict) -> str:
    sections = []
    for line, ranges in sorted(document["lines"].items()):
        rows = "".join(
            f'<tr><td>{escape(range_name)}</td><td><a href="{escape(pod["page_url"])}">'
            f'{escape(pod_name)}</a></td><td class="mg">{escape(caffeine(pod))}</td></tr>\n'
            for range_name, pods in sorted(ranges.items())
            for pod_name, pod in sorted(pods.items())
        )
        sections.append(
            f"<table>\n<caption>{escape(line)}</caption>\n"
            '<tr><th>Range</th><th>Pod</th><th class="mg">Caffeine per pod</th></tr>\n'
            f"{rows}</table>\n"
        )
    locales = ", ".join(document["source"]["locales"])
    merged = " (experimental merge)" if document["source"].get("merged") else ""
    body = (
        f"<h1>Capsule caffeine: {escape(name)}</h1>\n"
        f'<p class="muted">From nespresso.com ({escape(locales)}){merged}, '
        f"{escape(document['generated_at'])}. "
        '<a href="capsules.json">capsules.json</a></p>\n' + "".join(sections)
    )
    return page(f"Capsule caffeine: {name}", body)


def home_page(markets: dict[str, dict]) -> str:
    items = "".join(
        f'<li><a href="{escape(name)}/">{escape(name)}</a>, {escape(doc["generated_at"])}'
        f' (<a href="{escape(name)}/capsules.json">json</a>)</li>\n'
        for name, doc in sorted(markets.items())
    )
    body = (
        "<h1>Capsule caffeine</h1>\n"
        "<p>Caffeine per Nespresso pod, by market, refreshed from nespresso.com.</p>\n"
        f"<ul>\n{items}</ul>\n"
        f'<p class="muted">Files follow <a href="{SCHEMA}">schema 2</a>.</p>\n'
    )
    return page("Capsule caffeine", body)


def build_site(builds: dict[str, Path], out: Path) -> None:
    """Write <out>/<name>/{capsules.json,index.html} per build, plus a home page and the schema."""
    markets = {}
    for name, path in builds.items():
        markets[name] = json.loads(path.read_text(encoding="utf-8"))
        (out / name).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, out / name / path.name)
        (out / name / INDEX).write_text(market_page(name, markets[name]), encoding="utf-8")
    (out / SCHEMA).write_text(
        files("capsule_caffeine").joinpath(SCHEMA).read_text(encoding="utf-8"), encoding="utf-8"
    )
    (out / INDEX).write_text(home_page(markets), encoding="utf-8")
