GRAVEYARD SHIFT: MIDNIGHT GOLF — FOLIAGE EXPANSION
8 separate transparent PNG sprites, October 26, 2026.
These are new art assets, not yet integrated into the game.

TREE ASSETS
GOLF-TREE-19_Formal_Yew.png
  Clipped conical yew/cypress for Vampire's Garden beside the hedge maze.
GOLF-TREE-20_Dark_Blue_Spruce.png
  Tall, dense dark-blue spruce for an enclosing tree wall in Spiderwood.
GOLF-TREE-21_Witchwood_Purple.png
  Charcoal-black gnarled trunk and purple canopy for Witch's Hollow.
GOLF-TREE-22_Homecoming_Swing_Oak.png
  Gnarled oak with a two-rope wooden swing, a landmark beside the Homecoming house.

UNDERGROWTH ASSETS
GOLF-GROUND-01_Ferns.png
  Layered curling fern clump for woodland understory.
GOLF-GROUND-02_Brambles_v2.png
  Thorny bramble patch for the rough beneath each hole's trees.
GOLF-GROUND-03_Marsh_Reeds.png
  Reeds and cattails for marsh-hole shorelines.
GOLF-GROUND-04_Heather.png
  Purple flowering heather for low rough and Witch's Hollow accents.

ART DIRECTION
Built-in image generation using the existing golf trees as style references.
Painterly, angular, detailed Halloween fantasy; violet/indigo shadows,
warm amber rim light, and cool teal highlights. Upright, nearly frontal,
subtly elevated three-quarter 2.5D billboard views. Complete silhouettes,
actual alpha transparency, no ground plate or cast ground shadow.

2.5D IMPLEMENTATION NOTES
- Preserve the PNG alpha channel; do not flatten onto a background.
- Anchor each sprite at its base center; calibrate scale by world height,
  not by matching raw pixel sizes across images.
- Depth-sort by the ground-contact position, not by image center.
- Use separate simple collision shapes when needed. Decorative leaves,
  roots, and transparent pixels should not automatically become collision.
- Keep the camera consistent with the illustrated view. These are single-view
  sprites, not fully rotatable 3D models or multi-angle sprite sets.
- Test over both light and dark terrain. Transparent pixels may carry hidden
  RGB data, which is normal; the engine must honor alpha.
- Reuse undergrowth with modest scale variation. Avoid mirroring when it
  would reverse the painted lighting direction noticeably.

PACKAGING
Two independent ZIPs, each below 9 MB. Extract both into the same folder.
Each PNG appears once across the two ZIPs. README and undergrowth prompts
are included in Part 1. PNGs are unmodified selected generated originals.
