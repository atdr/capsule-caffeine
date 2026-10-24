"""Command line entry point: `capsule-caffeine scrape` and `capsule-caffeine diff`."""

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from .diff import compare, summary
from .document import market_document
from .http import make_session
from .merge import merge_markets
from .scrape import LINES, LOCALES, scrape_market
from .validate import problems

FILENAME = "capsules.json"
MERGED = "merged"

log = logging.getLogger("capsule_caffeine")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")


def read_json(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def scrape(args: argparse.Namespace) -> int:
    """Write <out>/<locale>/capsules.json per market, plus <out>/merged/ for several."""
    locales = args.locale or list(LOCALES)
    lines = args.line or list(LINES)
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    session = make_session()

    markets = {}
    failed = False
    for locale in locales:
        markets[locale] = scrape_market(session, locale, lines, args.delay)
        doc = market_document(locale, markets[locale], generated_at)
        for problem in problems(doc):
            log.error("%s: %s", locale, problem)
            failed = True
        write_json(args.out / locale / FILENAME, doc)

    if len(markets) > 1:
        merged = merge_markets(markets, generated_at)
        # The merged file is experimental, so its problems never block a publish.
        for problem in problems(merged):
            log.warning("%s: %s", MERGED, problem)
        write_json(args.out / MERGED / FILENAME, merged)
    return 1 if failed else 0


def builds(root: Path) -> dict[str, Path]:
    """{name: capsules.json path} for a single file or a directory of builds."""
    if root.is_dir():
        return {p.parent.name: p for p in sorted(root.glob(f"*/{FILENAME}"))}
    return {root.name: root}


def diff(args: argparse.Namespace) -> int:
    """Print release notes; exit 1 when anything changed, like diff(1)."""
    old, new = builds(args.old), builds(args.new)
    changes = {}
    for name in sorted(old.keys() | new.keys()):
        old_doc = read_json(old[name]) if name in old else None
        # A market missing from the new build counts as all its pods removed.
        new_doc = read_json(new[name]) if name in new else {"lines": {}}
        changes[name] = compare(old_doc, new_doc)
    sys.stdout.write(summary(changes) + "\n")
    return 1 if any(changes.values()) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="capsule-caffeine")
    parser.add_argument("-v", "--verbose", action="store_true", help="log progress")
    commands = parser.add_subparsers(dest="command", required=True)

    scrape_cmd = commands.add_parser("scrape", help="scrape capsule data")
    scrape_cmd.add_argument(
        "--locale",
        action="append",
        help=f"nespresso.com market, repeatable (default: {' '.join(LOCALES)})",
    )
    scrape_cmd.add_argument(
        "--line",
        action="append",
        choices=list(LINES),
        help="capsule line, repeatable (default: all)",
    )
    scrape_cmd.add_argument(
        "-o", "--out", type=Path, default=Path("dist"), help="output directory (default: dist)"
    )
    scrape_cmd.add_argument(
        "--delay", type=float, default=0.3, help="seconds between product pages (default: 0.3)"
    )
    scrape_cmd.set_defaults(run=scrape)

    diff_cmd = commands.add_parser("diff", help="compare two builds (files or directories)")
    diff_cmd.add_argument("old", type=Path)
    diff_cmd.add_argument("new", type=Path)
    diff_cmd.set_defaults(run=diff)

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
