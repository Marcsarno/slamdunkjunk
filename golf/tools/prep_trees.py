"""Copy the painted tree cutouts (GOLF-TREE-NN_Name.png) into the game's billboard cards.

usage: python3 -I prep_trees.py <dir of GOLF-TREE-*.png> <golf/game/assets>

Each is trimmed to its alpha bounds, capped at MAX_H pixels tall, and saved as
cards/tree_<name>.png (GOLF-TREE-04_Copper_Oak.png -> tree_copper_oak.png). The hole builder places
them by that name (see TREE_HEIGHT in build_hole.py and each hole's trees_near / trees_far).
"""
import glob
import os
import re
import sys

from PIL import Image

MAX_H = 640      # they are never more than about a third of the screen tall

src, dst = sys.argv[1], sys.argv[2]
for path in sorted(glob.glob(os.path.join(src, "GOLF-TREE-*.png"))):
    m = re.match(r"GOLF-TREE-\d+_(.+)\.png", os.path.basename(path))
    name = "tree_" + m.group(1).lower()
    im = Image.open(path).convert("RGBA")
    im = im.crop(im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox())
    if im.height > MAX_H:
        im = im.resize((round(im.width * MAX_H / im.height), MAX_H), Image.LANCZOS)
    im.save(os.path.join(dst, "cards", name + ".png"), optimize=True)
    print(name, im.size)
