"""Copy the painted tree cutouts (GOLF-TREE-NN_Name.png) and undergrowth (GOLF-GROUND-NN_Name.png)
into the game's billboard cards.

usage: python3 -I prep_trees.py <dir of GOLF-TREE-*.png / GOLF-GROUND-*.png> <golf/game/assets>

Each is trimmed to its alpha bounds, capped at MAX_H pixels tall, and saved as
cards/tree_<name>.png (GOLF-TREE-04_Copper_Oak.png -> tree_copper_oak.png). The hole builder places
them by that name (see TREE_HEIGHT in build_hole.py and each hole's trees_near / trees_far).
Undergrowth goes the same way to cards/ground_<name>.png, smaller (GOLF-GROUND-02_Brambles_v2.png ->
ground_brambles.png).
"""
import glob
import os
import re
import sys

from PIL import Image

MAX_H = 640      # they are never more than about a third of the screen tall
MAX_H_GROUND = 384   # knee-high plants: never big on screen

src, dst = sys.argv[1], sys.argv[2]
for path in sorted(glob.glob(os.path.join(src, "GOLF-TREE-*.png")) + glob.glob(os.path.join(src, "GOLF-GROUND-*.png"))):
    m = re.match(r"GOLF-(TREE|GROUND)-\d+_(.+?)(_v\d+)?\.png", os.path.basename(path))
    name = ("tree_" if m.group(1) == "TREE" else "ground_") + m.group(2).lower()
    cap = MAX_H if m.group(1) == "TREE" else MAX_H_GROUND
    im = Image.open(path).convert("RGBA")
    im = im.crop(im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox())
    if im.height > cap:
        im = im.resize((round(im.width * cap / im.height), cap), Image.LANCZOS)
    im.save(os.path.join(dst, "cards", name + ".png"), optimize=True)
    print(name, im.size)
