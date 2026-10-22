"""Copy delivered 2D art into the game with clean names and sensible sizes.

usage: python3 -I prep_art.py <dir containing the extracted batch folders> <golf/game/assets>

Cutouts are trimmed to their alpha bounds and capped in size (small foliage needs far fewer
pixels than a tree). Tiling textures, skies and horizon strips are copied as-is.
"""
import os
import sys

from PIL import Image

SRC, DST = sys.argv[1], sys.argv[2]

CARDS = {  # source (relative) -> (game name, max height px)
    "Batch_4_foliage/22_grass_tuft.png": ("grass_tuft", 256),
    "Batch_4_foliage/23_tall_dry_grass.png": ("tall_grass", 384),
    "Batch_4_foliage/24_fern.png": ("fern", 320),
    "Batch_4_foliage/25_cornstalk_clump.png": ("corn", 512),
    "Batch_4_foliage/26_cattail_reeds.png": ("cattails", 512),
    "Batch_4_foliage/27_orange_red_leaf_pile.png": ("leaf_pile", 256),
    "Batch_4_foliage/28_teal_mushroom_cluster.png": ("mushrooms", 320),
    "Batch_4_foliage/32_hay_bale_stack.png": ("hay_bales", 384),
    "Batch_4_trees/29_white_birch_orange_leaves.png": ("birch", 1024),
    "Batch_4_trees/30_twisted_dead_tree.png": ("dead_tree", 1024),
    "Batch_4_trees/31_apple_tree.png": ("apple_tree", 1024),
    "Batch_4_creatures/33_bat_wings_up.png": ("bat_up", 256),
    "Batch_4_creatures/34_bat_wings_down.png": ("bat_down", 256),
    "Batch_4_creatures/35_crow_on_post.png": ("crow_post", 512),
}
TEXTURES = {
    "Batch2_Textures_A/10_fairway_grass.png": "fairway",
    "Batch2_Textures_A/11_rough_grass.png": "rough",
    "Batch2_Textures_A/12_putting_green.png": "green",
    "Batch2_Textures_A/13_bunker_sand.png": "sand",
    "Batch2_Textures_A/14_grave_dirt.png": "dirt",
    "Batch2_Textures_B/15_gravestone_stone.png": "stone",
    "Batch2_Textures_B/16_old_wood_planks.png": "wood",
    "Batch2_Textures_B/17_twisted_tree_bark.png": "bark",
    "Batch2_Textures_B/18_dry_stone_wall.png": "stone_wall",
    "Batch2_Textures_B/19_cliff_rock.png": "cliff",
}
SKY = {
    "Batch_3_Skies_Horizons_Native/Batch_3/01_Harvest_Sky.png": "sky_harvest",
    "Batch_3_Skies_Horizons_Native/Batch_3/02_Spiderwood_Sky.png": "sky_spiderwood",
    "Batch_3_Skies_Horizons_Native/Batch_3/03_Rolling_Hills_Cottages.png": "horizon_hills",
    "Batch_3_Skies_Horizons_Native/Batch_3/04_Gothic_Castle_NonTiling.png": "horizon_castle",
    "Batch_3_Skies_Horizons_Native/Batch_3/05_Dark_Pine_Treeline.png": "horizon_pines",
    "Batch_3_Skies_Horizons_Native/Batch_3/06_Twisted_Bare_Treeline.png": "horizon_bare_trees",
}

for sub in ("cards", "textures", "sky"):
    os.makedirs(os.path.join(DST, sub), exist_ok=True)

for rel, (name, max_h) in CARDS.items():
    im = Image.open(os.path.join(SRC, rel)).convert("RGBA")
    a = im.getchannel("A").point(lambda v: 0 if v < 24 else v)
    im.putalpha(a)
    im = im.crop(a.getbbox())
    if im.height > max_h:
        im = im.resize((round(im.width * max_h / im.height), max_h), Image.LANCZOS)
    im.save(os.path.join(DST, "cards", name + ".png"), optimize=True)
    print(f"card    {name:12s} {im.size}")

for rel, name in TEXTURES.items():
    im = Image.open(os.path.join(SRC, rel)).convert("RGB")
    im.save(os.path.join(DST, "textures", name + ".png"), optimize=True)
    print(f"texture {name:12s} {im.size}")

import json  # noqa: E402

import numpy as np  # noqa: E402
from scipy import ndimage  # noqa: E402

sky_meta = {}
for rel, name in SKY.items():
    im = Image.open(os.path.join(SRC, rel))
    im.save(os.path.join(DST, "sky", name + ".png"), optimize=True)
    entry = {"size": list(im.size)}
    if name.startswith("sky_"):
        # the moon is the largest bright, low-saturation disc: find it so the moonlight matches
        a = np.asarray(im.convert("RGB"), np.float32)
        lum = a.mean(axis=2)
        sat = a.max(axis=2) - a.min(axis=2)
        upper = np.arange(a.shape[0])[:, None] < a.shape[0] * 0.7      # the horizon glow is bright too
        mask = ndimage.binary_opening((lum > np.percentile(lum[upper[:, 0]], 98.5)) & (sat < 170) & upper, iterations=2)
        lab, n = ndimage.label(mask)
        if n:
            sizes = ndimage.sum(mask, lab, range(1, n + 1))
            cy, cx = ndimage.center_of_mass(mask, lab, 1 + int(np.argmax(sizes)))
            entry["moon_uv"] = [round(cx / im.width, 4), round(cy / im.height, 4)]
        entry["top_color"] = [round(float(v) / 255, 3) for v in a[:8].reshape(-1, 3).mean(axis=0)]
        entry["horizon_color"] = [round(float(v) / 255, 3) for v in a[-8:].reshape(-1, 3).mean(axis=0)]
    sky_meta[name] = entry
    print(f"sky     {name:18s} {im.size} {im.mode} {entry.get('moon_uv', '')}")
json.dump(sky_meta, open(os.path.join(DST, "sky", "sky.json"), "w"), indent=1)
