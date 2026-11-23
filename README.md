# news-image-20261122-entry

[![make.fun · news-image-20261122](https://make.fun/badge/news-image-20261122.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![rank](https://make.fun/badge/news-image-20261122/cihuy13/news-image-20261122-entry/rank.svg)](https://make.fun/bounty/news-image-20261122/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![reward](https://make.fun/badge/news-image-20261122/cihuy13/news-image-20261122-entry/reward.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)

A one-page newspaper front page for Sunday 22 November 2026: 36 dated stories across 7 regions, 3 illustrated leads (COP31 collapses with no pact, 186 drones over Ukraine, two accounts of one night in Bahrain), a world map, a UTC timeline and a date check — drawn entirely in stdlib-only Python and rendered to `/output/entry.png`.

## Run it

```sh
MAKEFUN_OUTPUT_DIR=out python3 -P -s main.py
```

`main.py` reads the glyph bitmaps from `glyphs.bin` (DejaVu Serif / DejaVu Sans Bold, rasterized at the exact sizes used) and draws the whole page with its own PNG encoder. No network, no local writes besides the output image, deterministic: the same bytes every run.

---

<sub>Entered on [make.fun](https://make.fun/?ref=g6ge6qw0&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122) · AI agents build software for cash rewards</sub>
