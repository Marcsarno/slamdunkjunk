# Art requests for ChatGPT — Graveyard Shift: Midnight Golf

Ordered by priority. **Batch 1 blocks the playable hole; the rest can come in any order.**

## How to ask (applies to every request)

- **Attach references every time:** `iron.png` (the pixie-cut swing sheet) for anything with Brittany; the
  Haunted Harvest / Spiderwood paintings for anything environmental. Say "match this exact art style".
- **One image per pose.** Sheets with many poses come back with drifting scale and proportions.
- **Background:** ask for a transparent PNG. If it comes back with a fake checkerboard or a gradient, ask
  instead for *"a flat solid pure green #00FF00 background, no shadow, no ground"*. I remove it cleanly.
- **Nothing extra in frame:** no ground, no cast shadow, no tee, no ball, no text, no border.
- Square images (1024×1024) are fine. I handle trimming, scaling and alignment.

---

## Batch 1 — Brittany for the aim view and reactions (highest priority)

Use the **pixie-cut** Brittany only. Paste this style line at the start of each prompt:

> *Same character and exact art style as the attached sprite sheet: Brittany, short messy auburn pixie cut
> with a small jack-o'-lantern hair clip, pink t-shirt with sunglasses hooked on the collar, dark purple
> apron tied at the waist with a pumpkin patch, olive shorts, heavily tattooed arms and legs, chunky cream
> sneakers. Right-handed golfer. Full body, head to toe, feet fully visible. Transparent background.*

1. **Aim pose, from behind.** *"…seen from behind and slightly to her right (back three-quarter view), in
   golf address stance holding an iron, club head resting on the grass in front of her, looking down at the
   ball, as if the camera stands just behind her looking down the fairway."*
2. **Aim pose, breathing.** Same as #1, *"shoulders very slightly raised, otherwise identical."* (Two-frame
   idle so she isn't frozen while you aim.)
3. **Watching the shot, from behind.** *"…seen from behind (back three-quarter view), holding her finish
   pose with the club wrapped behind her shoulders, weight on her front foot, back heel up, looking far down
   the fairway."* (Plays while the camera follows the ball.)
4. **Putting address, from behind.** *"…back three-quarter view, bent over a putter, putter head on the
   green, looking down at the ball."*
5. **Putting stroke back** and **6. putting stroke through**: same view as #4, *"putter swung a short
   distance back"* / *"putter swung a short distance forward past where the ball was"*.
7. **Driver downswing, front view.** Attach `driver.png`: *"…front view exactly like this sheet, downswing
   frame: club shaft level at hip height, pointing to her right, hips starting to turn."* (Fills the one
   gap in the driver swing.)
8. **Groan.** *"…front view, holding the club in one hand, other hand over her face, slumped, a bad shot."*
9. **Startled.** *"…front view, jumping back, both hands up, wide eyes, club still in one hand, as if a
   skeleton just burst out of the ground next to her."*

> Optional, best quality: a full **back three-quarter iron swing**, eight separate images (address,
> takeaway, half back, top, downswing, contact, release, finish) using the same view as #1. With these
> I can show the whole swing from behind instead of cutting to the side view.

---

## Batch 2 — Seamless ground textures (makes the 3D match the paintings)

This fixes the "3D didn't match the art" problem. Every 3D surface gets painted with these.

Prompt template:

> *Seamless tileable texture, top-down, flat even lighting, no shadows, no objects, no perspective,
> painterly hand-painted style matching the attached painting, square 1024×1024: [SURFACE].*

| # | [SURFACE] |
|---|---|
| 10 | lush fairway grass, soft painted brush strokes, warm green |
| 11 | longer darker rough grass with a few fallen orange and red autumn leaves |
| 12 | very smooth fine putting-green grass |
| 13 | pale golden bunker sand with soft ripples |
| 14 | dark loose grave dirt with small pebbles |
| 15 | weathered grey-lavender gravestone with lichen and moss patches |
| 16 | old dark wood planks (for barn, bridge and fence) |
| 17 | twisted tree bark, dark purple-brown |
| 18 | dry stone wall stones, rounded grey-purple, stacked |
| 19 | mossy dark cliff rock face (for Spiderwood) |

---

## Batch 3 — Skies and horizon layers (one set per hole theme)

The camera swings around, so backdrops wrap all the way around the hole. That is what keeps the 2D
background working when the camera moves to the side.

20. **Sky panorama**, one per theme: *"Wide seamless panoramic night sky, 4096×1024, left and right edges
    tile perfectly, no ground and no horizon objects, [THEME SKY]. Painterly, matching the attached
    painting."*
    - Haunted Harvest: *deep purple to burnt-orange sunset, big glowing full moon, soft clouds*
    - Spiderwood: *violet night, misty, full moon behind thin clouds*
    - (I'll ask for the other themes once the concept art for them arrives.)
21. **Horizon silhouette strips**, transparent, wide 4096×1024, tileable left-right, flat bottom edge:
    - *rolling distant purple hills with tiny lit cottage windows*
    - *distant gothic castle and spires on a hill* (one image, not tiled)
    - *dark pine forest treeline*
    - *bare spooky tree line with twisted branches*

---

## Batch 4 — Scatter cutouts (fill the course so it looks lush, like the paintings)

Each as its own transparent image, front view, no ground:

22. grass tuft · 23. tall dry grass clump · 24. fern · 25. cornstalk clump (3–4 stalks) ·
26. cattail reeds clump · 27. pile of orange and red autumn leaves · 28. small mushroom cluster (glowing teal) ·
29. birch tree (white bark, orange leaves; for Spiderwood) · 30. twisted bare dead tree ·
31. apple tree with red apples (Haunted Harvest) · 32. hay bale stack · 33. bat, wings up / 34. bat,
wings down (two frames for a flapping loop) · 35. crow sitting on a post.

---

## I'll make these myself (no need to request)

Glow halos and light pools, fog wisps, fireflies, ball trail, sand and water splashes, the aim arrow and
landing marker, and every 3D prop: tombstones, lanterns, fences, walls, windmill, barn, bridge, skeletons.
