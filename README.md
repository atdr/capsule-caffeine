# Capsule Caffeine

Python web scraper to gather data on the caffeine content of Nespresso pod coffee.

## Shortcuts

I made a corresponding Shortcut (links: [iCloud](https://www.icloud.com/shortcuts/4f33796a6ad24dd3aa20773b33eba3a2), [RoutineHub](https://routinehub.co/shortcut/8103/)) to log caffeine directly into the iPhone Health app. In addition, there is an alternative shortcut that allows logging of multiple pods at once, if you are very into your caffeine (link: [iCloud](https://www.icloud.com/shortcuts/dd5f8b82081341c0bc7250667eca1da0)).

These Shortcuts read data pinned to the `v1.1` and `v1.0` tags. They keep working, but their data is no longer updated. A new Shortcut with automatically refreshed data is on the way.

## Running the scraper

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv run capsule-caffeine scrape -v -o capsules.json
```

Options: `--locale` picks the nespresso.com market (default `tw`), `--line` the capsule line (default `original`). Without `-o` the JSON goes to stdout.

Scraped data is a build output and is not committed to this repository.

See this Gist for [a sample of the JSON](https://gist.github.com/atdr/5212cdd48e77021c0786561fb2063c86) found on the Nespresso site if you're interested in extending the scraper.

## Thanks

To everyone who kept this going in their forks: [DEEJCUK](https://github.com/DEEJCUK/capsule-caffeine) for Vertuo support and a sturdier standalone scraper, which inspired this one; [edspc](https://github.com/edspc/capsule-caffeine) and [yuejunfeng0909](https://github.com/yuejunfeng0909/capsule-caffeine) for data refreshes and Singapore support; and [wiebecommajonas](https://github.com/wiebecommajonas) and [indiamai](https://github.com/indiamai) for their contributions here.

## License

The code in this repository (the scraper) is released under the [MIT License](LICENSE).

Data produced by the scraper is not covered by that license. It holds product information scraped from the Nespresso website, which this project does not own and cannot license. Nespresso is a trademark of Société des Produits Nestlé S.A.; this project is not affiliated with or endorsed by Nestlé.
