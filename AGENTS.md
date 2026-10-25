# capsule-caffeine

<!-- Stable instructions only. TODOs, status and changelogs do not belong here:
they change too often and cost context on every session. The backlog is GitHub
Issues; the record of what happened is git history and CHANGELOG.md. -->

Scrapes the caffeine content of Nespresso capsules from nespresso.com, publishes
it weekly as JSON on GitHub Pages, and builds the Nespresso Log Shortcut that
reads it and logs caffeine to Apple Health. An application, not a library: it is
not published to PyPI, and its own scheduled run is what uses its dependencies.

## Commands

```bash
uv sync --locked                     # install from uv.lock, dev tools included
uv run --locked ruff check .         # lint
uv run --locked ruff format --check .
uv run --locked pytest -q            # offline: tests use hand-made pages
uv run --locked pytest -q --cov      # coverage, scoped in pyproject.toml

uv run capsule-caffeine -v scrape            # all default markets, into dist/
uv run capsule-caffeine diff old-dist/ dist/ # exit 1 when the data changed
uv run capsule-caffeine site dist/ -o site/  # the static Pages site
uv run capsule-caffeine shortcut -o out.shortcut
```

CI runs the lint and test commands through atdr/github-boilerplate's
`python-ci.yml`, which installs from `uv.lock` the same way.

## Architecture

- `scrape.py` reads one market's capsule ranges and caffeine figures, through
  `http.py`, which fetches pages and the JSON embedded in them.
- `document.py` builds schema 2 `capsules.json` documents
  (`capsules.schema.json`); `validate.py` holds the checks one must pass before
  it is published.
- `promotions.py` reads `ranges.json`, the curated range map. `merge.py` is the
  experimental cross-market merge.
- `diff.py` compares two builds, both to decide whether to publish and to write
  the release notes.
- `site.py` builds the static site; `shortcut.py` builds the unsigned Shortcut,
  and `scripts/sign-shortcut.sh` signs it on a Mac logged into iCloud.

**Workflows:**

- `data.yml` runs every Monday. It checks out the **latest code release**, not
  `main`, scrapes, compares with the live site, and deploys and snapshots only
  when the data changed (or when forced).
- `release-please.yml` maintains the release PR. When a release is cut it
  dispatches `data.yml` with `force` (a release made with `GITHUB_TOKEN` starts
  no `release` workflow) and attaches the unsigned Shortcut to the release.

## Conventions

- **Git workflow:** GitHub Flow. Every change lands on a `<type>/<description>`
  branch and merges by squash PR. Never commit directly to `main`.
- **Commits and PR titles:** Conventional Commits, `<type>(<scope>): <summary>`,
  with types `feat fix perf refactor test docs chore ci`. The PR title becomes
  the commit on `main`, which release-please reads.
- **Releases:** automated by release-please. Never bump the version or edit
  CHANGELOG.md by hand. `release-please-config.json` also bumps the package's
  own version inside `uv.lock`.
- **Dependencies** are pinned in `uv.lock`. Dependabot's `uv` entry bumps them;
  a runtime bump is `fix`, so it cuts a release and reaches the next scrape,
  while a dev tool bump is `chore` and does not.
- **Workflows:** each file's `name:` is its filename stem, and every job sets
  `timeout-minutes`. See atdr/github-boilerplate's STANDARDS.md.

## Gotchas

- **A merged change does not reach the data until it is released.** `data.yml`
  builds from the newest `v*` tag, so a fix on `main` waits for its release PR.
- **Data releases are not code releases.** `data.yml` publishes dated
  `data-YYYY-MM-DD` releases with `--latest=false`, so "latest" always stays the
  newest code release. Never make a data release the latest one.
- Scraped data is a build output and is never committed (`dist/` and `site/` are
  ignored).
- New range slugs from the site appear as warnings and need adding to
  `ranges.json`.
