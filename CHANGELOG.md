# Changelog

## [2.0.1](https://github.com/atdr/capsule-caffeine/compare/v2.0.0...v2.0.1) (2026-10-24)


### Bug Fixes

* **data:** drop promotions that only repeat other ranges ([#13](https://github.com/atdr/capsule-caffeine/issues/13)) ([9206679](https://github.com/atdr/capsule-caffeine/commit/92066794df90499a99e3bd966b147a5f37b7d3b6))


### Documentation

* link the v2 Shortcut and mark the v1 ones as legacy ([#15](https://github.com/atdr/capsule-caffeine/issues/15)) ([f848d29](https://github.com/atdr/capsule-caffeine/commit/f848d293d0c93959f2162f6a8c219641b5c9db5e))

## [2.0.0](https://github.com/atdr/capsule-caffeine/compare/v1.1.0...v2.0.0) (2026-10-24)


### ⚠ BREAKING CHANGES

* **scraper:** the output is schema 2 (lines > ranges > pods, one file per market) instead of the v1 ranges > pods file.

### Features

* **scraper:** schema v2 with Vertuo, Pro and per-market files ([#7](https://github.com/atdr/capsule-caffeine/issues/7)) ([e93f14b](https://github.com/atdr/capsule-caffeine/commit/e93f14b966487c0e2c10ab24aa23b47afb78c93e))
* **site:** build a static site from capsules.json ([#8](https://github.com/atdr/capsule-caffeine/issues/8)) ([c474ea1](https://github.com/atdr/capsule-caffeine/commit/c474ea1904463c5779ff5b9665b1147b6354e8ba))
