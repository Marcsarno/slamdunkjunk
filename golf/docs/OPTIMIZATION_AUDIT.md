# Download audit (October 2026)

Every file in every phone-format download was opened and measured (compressed, as sent). Nothing was
changed by this audit. Measured on the build after the pumpkins were stored once (commit 3b4abaa).

## Where the bytes are today (phone, whole round)

| Download | When | Size | What's in it |
|---|---|---|---|
| Engine (index.wasm) | first | 9.2 MB | Godot itself |
| index.pck | first | 3.3 MB | title, clubhouse, fonts, ball pictures (1.7 MB), scripts |
| core | behind the title, PLAY waits | 10.9 MB | her frames 6.1, song 1 3.0, bag/lanterns 1.7 |
| course | behind the clubhouse | 7.7 MB | ground textures 4.3, sky 2.7, shared plants |
| h01..h09 | before each hole | 54.4 MB | hole model ~28, pictures ~23, height maps ~3 |
| music | later | 6.4 MB | songs 2 and 3 |
| **Total** | | **~92 MB** | |

## Findings

| # | What | Saving (est.) | Visual change | Risk |
|---|---|---|---|---|
| A | 40 pictures shared by several holes are saved inside each of those holes' downloads (dead tree x4, lantern ghost x7, moons x4-5, ferns x6 ...) | **13.6 MB** (measured) | none | low: download logic only |
| B | Every hole model carries a shadow copy and far-detail copies of the **ground**; the game never lets the ground cast shadows and the camera is always inside it | **~10-14 MB** (hole 1: 3.1 -> 1.2 MB with no extras at all) | none expected | low; must confirm by screenshots + frame time. The per-object import setting didn't take on the first try |
| C | Her frames are stored in the graphics-chip format, which compresses poorly | 6.1 -> ~2.8 MB (PLAY waits on this) | slight softening at edges possible | low-medium; a little more graphics memory (small frames) |
| D | Ball pictures are 512 px; shown at most ~280 px | 1.6 -> ~0.2 MB in the **first** download | none | very low |
| E | Hedge texture (1 MB) downloaded before hole 1; only hole 7 has hedges. Lantern models carry 3 identical copies of 2 textures | ~1 MB earlier, 0.3 MB total | none | very low |
| F | Gravestones, fences, bridges: every copy is its own model (same trick as the pumpkins) | ~2.5 + 1.5 + 1 MB (rough, from raw files) | stones become a handful of shapes | low-medium |
| G | Song 1 is 192 kbps (the others 128) and PLAY waits for it | 3.0 -> 2.0 MB | slight audio quality, Marc's call | low |
| H | Ground textures (4.3 MB before hole 1) and tree pictures (8.9 MB): a smaller download format (Basis Universal) that stays chip-compressed | unknown, needs a test | possible slight blur | medium (memory/speed on phones) |
| I | Build the ground on the phone from the height map it already downloads | ~8 MB | none | medium-high: slower hole load on the phone |
| J | Engine: Brotli or a trimmed engine | unknown | none | high effort |

Not worth doing: WebP for ground textures and trees (4.3 -> 0.8 MB looks great, but takes four times the
graphics memory and is slower to draw on phones). Tangents (6 KB). Library/ground.jpg: already excluded.

## Why these were missed

- Earlier optimization measured each download's total and moved files between stages; nobody opened the
  downloads to look for repeats or for what's inside the models.
- The hole-pack rule copies shared pictures into each hole on purpose (so any hole can be picked first);
  its cost was never measured.
- The pumpkins were merged per 40 m to cut draw calls: tuned for drawing speed, not for bytes.
- Import defaults (far-detail and shadow copies) were left on for every object, including the ground,
  although the game itself turns ground shadows off; the two were never cross-checked.
- Sizes were judged by kind of file ("pictures are heavy, 3D is light") instead of measured.

Fix: a byte-level audit (this one) should run with every web build, printing the biggest items and any
repeats, so the next one shows up the day it happens.

## Proposed order

1. No visible change, biggest: A, B, D, E. About 25-30 MB off the round; first download -1.4 MB,
   before hole 1 about -1.3 MB.
2. Small visual risk, judged by eye: C, G, F (with the 3D classic jack, candles and pile).
3. Experiments: H, I, J.

Each step separately, each checked with same-spot screenshots, the bot playing all nine holes, the physics
tests, a frame-time run and the size report; deployed only when Marc asks. Phases 1 and 2 together: about
92 -> 55-60 MB (estimate).
