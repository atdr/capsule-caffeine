"""Command line entry point: `capsule-caffeine scrape`, `diff`, `site` and `shortcut`."""

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from . import shortcut as nespresso_log
from .diff import compare, summary
from .document import market_document
from .http import make_session
from .merge import merge_markets
from .scrape import LINES, LOCALES, scrape_market
from .site import build_site
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
    # One key for any single file, so `diff old.json new.json` compares the two.
    return {FILENAME: root} if root.exists() else {}


def diff(args: argparse.Namespace) -> int:
    """Print release notes; exit 1 when anything changed and 2 on trouble, like diff(1)."""
    if not args.new.exists():
        log.error("%s does not exist", args.new)
        return 2
    old, new = builds(args.old), builds(args.new)
    changes = {}
    try:
        for name in sorted(old.keys() | new.keys()):
            old_doc = read_json(old[name]) if name in old else None
            # A market missing from the new build counts as all its pods removed.
            new_doc = read_json(new[name]) if name in new else {"lines": {}}
            changes[name] = compare(old_doc, new_doc)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        # Status 1 must mean "changed", so a broken file can't pass for an update.
        log.error("cannot compare %s: %r", name, error)
        return 2
    sys.stdout.write(summary(changes) + "\n")
    return 1 if any(changes.values()) else 0


def site(args: argparse.Namespace) -> int:
    """Build the static site for GitHub Pages from a build."""
    found = builds(args.build)
    if not found:
        log.error("no %s found in %s", FILENAME, args.build)
        return 1
    build_site(found, args.out)
    return 0


def shortcut(args: argparse.Namespace) -> int:
    """Build the unsigned Nespresso Log Shortcut; exit 1 if its structure is broken."""
    built = nespresso_log.build()
    for problem in nespresso_log.problems(built):
        log.error("%s", problem)
    if nespresso_log.problems(built):
        return 1
    args.out.write_bytes(nespresso_log.to_bytes(built))
    return 0


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

    site_cmd = commands.add_parser("site", help="build the static site from a build")
    site_cmd.add_argument(
        "build",
        type=Path,
        help="a build directory (default: dist)",
        nargs="?",
        default=Path("dist"),
    )
    site_cmd.add_argument(
        "-o", "--out", type=Path, default=Path("site"), help="output directory (default: site)"
    )
    site_cmd.set_defaults(run=site)

    shortcut_cmd = commands.add_parser("shortcut", help="build the unsigned Nespresso Log Shortcut")
    shortcut_cmd.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path("Nespresso Log (unsigned).shortcut"),
        help="output file (default: Nespresso Log (unsigned).shortcut)",
    )
    shortcut_cmd.set_defaults(run=shortcut)

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
