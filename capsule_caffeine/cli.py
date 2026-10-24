"""Command line entry point: `capsule-caffeine scrape`."""

import argparse
import json
import logging
import sys

from .http import make_session
from .scrape import scrape


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="capsule-caffeine")
    commands = parser.add_subparsers(dest="command", required=True)

    scrape_cmd = commands.add_parser("scrape", help="scrape capsule data to JSON")
    scrape_cmd.add_argument("--locale", default="tw", help="nespresso.com market (default: tw)")
    scrape_cmd.add_argument("--line", default="original", help="capsule line (default: original)")
    scrape_cmd.add_argument("-o", "--output", default="-", help="output file (default: stdout)")
    scrape_cmd.add_argument("-v", "--verbose", action="store_true", help="log progress")

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    data = scrape(make_session(), locale=args.locale, line=args.line)
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output == "-":
        sys.stdout.write(text)
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
