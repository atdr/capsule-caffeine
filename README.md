# Capsule Caffeine

Python web scraper to gather data on the caffeine content of Nespresso pod coffee.

## Shortcut

[Nespresso Log](https://www.icloud.com/shortcuts/4d98f10396bc459382d860e7677df1ce) (also on [RoutineHub](https://routinehub.co/shortcut/8103/)) logs a pod's caffeine to the Health app. Pick the machine, range and pod, say how many pods, and it logs the total with a notification showing the pod. When you add it, it asks for a market: `tw` (Taiwan), `sg` (Singapore) or `merged` (both, experimental). It reads the [published data](#data), so it picks up new pods without updating. Run it with a date as input to log a pod after the fact.

Pods that Nespresso publishes no caffeine figure for are not logged. If the data ever moves to a new format, the Shortcut asks you to update it rather than logging wrong numbers.

The original Shortcuts ([single pod](https://www.icloud.com/shortcuts/4f33796a6ad24dd3aa20773b33eba3a2), [multiple pods](https://www.icloud.com/shortcuts/dd5f8b82081341c0bc7250667eca1da0)) read data pinned to the `v1.1` and `v1.0` tags. They keep working, but their data is no longer updated.

## Running the scraper

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv run capsule-caffeine -v scrape          # all markets and lines, into dist/
uv run capsule-caffeine scrape --locale tw --line Vertuo
uv run capsule-caffeine diff old-dist/ dist/   # release notes; exit 1 when changed
uv run capsule-caffeine site dist/ -o site/    # static site for GitHub Pages
```

A run writes one `dist/<market>/capsules.json` per market, keeping that market's own ranges. The defaults are `tw` and `sg`, the English-language markets that publish caffeine content. `au`, `hk`, `my` and `nz` run the same site but give no caffeine values; `uk`, `us`, `ca` and `ie` run a different site. With several markets it also writes `dist/merged/capsules.json`. That file is experimental: pods are matched by name across markets, and ranges are renamed through [`ranges.json`](capsule_caffeine/ranges.json). New range slugs show up as warnings and need adding there.

Every file follows [schema 2](capsule_caffeine/capsules.schema.json):

```json
{
  "schema": 2,
  "generated_at": "2026-10-24T12:00:00Z",
  "scraper": "2.0.0",
  "source": { "site": "nespresso.com", "language": "en", "locales": ["tw"] },
  "lines": {
    "Vertuo": {
      "Espresso": {
        "Double Espresso Dolce": {
          "id": "7034.80",
          "caffeine_mg": 133,
          "image_url": "https://www.nespresso.com/ecom/medias/…/320.png",
          "page_url": "https://www.nespresso.com/tw/en/order/capsules/vertuo/…"
        }
      }
    }
  }
}
```

`caffeine_mg` is `null` when the product page gives no value. Where a page gives a range (sg does, for example "120 – 300mg per cup"), `caffeine_range_mg` holds `[low, high]` and `caffeine_mg` is its midpoint. In the merged file, tw's single figure is preferred. A file that fails the checks (schema, a minimum number of pods per line, at most half missing caffeine) makes the run exit with an error.

`site` copies each `capsules.json` next to a plain table of names and caffeine figures linking to the Nespresso product pages, with no images or product descriptions.

Scraped data is a build output and is not committed to this repository. Tests run offline against hand-made pages: `uv run pytest`.

See this Gist for [a sample of the JSON](https://gist.github.com/atdr/5212cdd48e77021c0786561fb2063c86) found on the Nespresso site if you're interested in extending the scraper.

## Data

A [weekly workflow](.github/workflows/data.yml) scrapes with the latest code release and, when the data has changed, publishes it to GitHub Pages:

- `https://atdr.github.io/capsule-caffeine/<market>/capsules.json` (`tw`, `sg`, `merged`) always holds the latest data, with a readable table at `https://atdr.github.io/capsule-caffeine/<market>/`.
- Each change is also kept as a `data-YYYY-MM-DD` release with the files attached as `<market>-capsules.json`, for anyone who wants to pin a version. These are never marked as the latest release.

A new code release rebuilds the site. Pages has to be set to deploy from GitHub Actions once: `gh api -X POST repos/atdr/capsule-caffeine/pages -f build_type=workflow`.

## Releases

The scraper is versioned by [release-please](https://github.com/googleapis/release-please) from conventional commit messages, which also write `CHANGELOG.md`. Don't edit either by hand. Data is not versioned with the code.

## Thanks

To everyone who kept this going in their forks: [DEEJCUK](https://github.com/DEEJCUK/capsule-caffeine) for Vertuo support and a sturdier standalone scraper, which inspired this one; [edspc](https://github.com/edspc/capsule-caffeine) and [yuejunfeng0909](https://github.com/yuejunfeng0909/capsule-caffeine) for data refreshes and Singapore support; and [wiebecommajonas](https://github.com/wiebecommajonas) and [indiamai](https://github.com/indiamai) for their contributions here.

## License

The code in this repository (the scraper) is released under the [MIT License](LICENSE).

Data produced by the scraper is not covered by that license. It holds product information scraped from the Nespresso website, which this project does not own and cannot license. Nespresso is a trademark of Société des Produits Nestlé S.A.; this project is not affiliated with or endorsed by Nestlé.
