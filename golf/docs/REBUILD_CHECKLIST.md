# Nine-hole rebuild: checklist (plan v2)

What the rebuild must keep or redo, from the project's history (commits, HANDOFF.md, Marc's notes) and
from running plan v2 through the builder's own ground (`tools/check_plan_ground.py`). Tick each before
showing Marc.

## Builder changes needed first
- [ ] **Turn every layout so the tee shot runs up +y.** The tee box, its drainage, the tee pumpkins
      (`TEE_PUMPKINS`) and hole 7's gate pillars all assume it. Plan v2's hole 3 starts along +x and hole
      9 on a diagonal: rotate those layouts as a whole.
- [ ] **Bunkers at plan size.** `realistic_bunkers` caps greenside bunkers at 4.5-6.5 x 2.6-3.6 m and
      would shrink plan v2's (~20 x 9 m). Raise the caps, keep the greenside lip and depth, keep the
      cart-path slide (`bunkers_as_drawn` would lose both).
- [ ] **Irregular shapes** for water, zones, pads and bunkers (lobed outlines, not ellipses); the hole-6
      marsh as a line of water pieces like the ravine.
- [ ] **Fairway gaps** (`fairway_gap`: hole 8 at the ravine) and second fairways (`extra_fairways`: hole
      8's left route), `green_raise` (holes 2 and 6).
- [ ] **Trees in groves**: dominant ~6 in 10, second ~1 in 4, accents; far woods to match; undergrowth
      (`ground_*`); one landmark tree (swing oak, hole 9). `TREE_HEIGHT` / `TREE_SPREAD` entries for the
      four new trees. Trees ~15 m back from the fairway in the landing area; a gap along each brave line.
- [ ] **Graveyard and pumpkin patch play like the corn** (about 35% shorter, "Lost in the graves!").

## Layout and ground
- [ ] Every hazard off the fairway sits inside a `zone` (or `pad`), or it lands on the 2.5-3 m framing
      bank beyond the rough and the woods grow through it.
- [ ] Ponds sit under their lowest rim; no bank reaches into a green; greens at least ~2 m above water
      beside them (checked: holes 2 and 6 need `green_raise`).
- [ ] Builder grade report: no "<-- over"; pin area <= 3%; fairway p95 <= 9% (plan checked: 7-8.4%).
      No "accordion" ground (Marc, 22 Oct).
- [ ] Landing areas <= ~4% (plan checked: hole 8 3.8%, hole 5 3.1%, rest under 2%).
- [ ] The safe path runs through the safe landing (auto-target walks the path, then steps back from
      water, sand and out of bounds).
- [ ] Holes 4-9 are written by `make_holes_4_9.py` (its `PROFILES` override inline profiles); holes 1-3
      by hand: keep one source per hole.

## Greens, bunkers, cart path
- [ ] Lobed greens, tilt 1.5-2.8%, false front toward the approach, pin on GREEN.
- [ ] Cart path: bridges wherever it crosses the new water; greenside bunkers slide off it; light props
      it displaces (hole 1 went 12 -> 7) put back.
- [ ] `CHECKER_GREENS` and `FLAGS` keyed by hole id still right; mowing stripes follow the last leg.

## Trees, cards, props
- [ ] Trees 7 m and other scenery 1 m off the green's edge (the old tree-card-on-hole-2's-green bug).
- [ ] View from the tee open; nothing floating or sunk (look at frames).
- [ ] Features keep their clear radius; barn and mansion face the green; gargoyle stays on its pillar;
      headstones face the tee.
- [ ] Woods beyond the rough stay the darkest ground.
- [ ] Triangle count per hole no worse than today (hole 5 ~480k is the ceiling).

## Lights, lanterns, flags
- [ ] Green lanterns behind each green (out of water, sand, green); tee markers along the first leg; bag
      never on green, water or sand.
- [ ] Mirrored holes (hole 1): negate `moon_azimuth` and `light_azimuth` so the light stays behind her.
- [ ] Flag faces her once per shot; cup drawn 1.8x.

## Camera, opening
- [ ] Opening on bending holes: the rise aims down the straight tee-to-pin line and the light front moves
      along it, and the flight is a fixed 5 s however long the path. Check holes 3 and 9 (the big bends)
      with `tests/intro_path.gd`: no left-right swings (Marc), lights in order.
- [ ] Flyover ends short of the pin with the flag in view (not behind the false front).

## Web build
- [ ] Rerun `tools/hole_art.sh` -> `hole_art.json` -> `web_split.py`; each hole pack has its art.
- [ ] Every file under 15 MB (`web_pack.py` asserts); packs 4.7-9.9 MB today, hole 5 the biggest.
- [ ] Commit `dist` only from a clean build; no preview deploys; production only when Marc asks.

## Tests before showing Marc
- [ ] `test_physics.gd` ALL PASSED (it drives straight up hole 1 from the tee).
- [ ] Bot round per hole, safe and risky lines; `tests/overhead.gd` against the concepts; `light_set`;
      `mem_probe`; frames from the tee, the landing area and the green on every hole.
