"""Copy the painted light props (GOLF-LIGHT-NN_Name.png) into the game, and find where each one's light is.

usage: python3 -I prep_lights.py <dir of GOLF-LIGHT-*.png> <golf/game/assets>

Each is trimmed to its alpha bounds (ignoring the generator's faint sub-10 alpha specks), capped at
MAX_H pixels tall and saved as cards/light_<name>.png. Its light source is found as the brightest
part of the picture (the flame, the glowing eyes, the spirit): cards/lights.json records, per prop,
that spot (x from the centre as a share of the width, y up from the bottom as a share of the height)
and its color (from the saturated glow round it), so the game hangs a glow and a colored light there.
"""
import glob
import json
import os
import re
import sys

import numpy as np
from PIL import Image

MAX_H = 512

src, dst = sys.argv[1], sys.argv[2]
meta = {}
for path in sorted(glob.glob(os.path.join(src, "GOLF-LIGHT-*.png"))):
    m = re.match(r"GOLF-LIGHT-\d+_(.+)\.png", os.path.basename(path))
    name = "light_" + m.group(1).lower().replace("'", "")
    im = Image.open(path).convert("RGBA")
    a = np.array(im)[..., 3]
    ys, xs = np.where(a > 10)
    im = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    if im.height > MAX_H:
        im = im.resize((round(im.width * MAX_H / im.height), MAX_H), Image.LANCZOS)
    im.save(os.path.join(dst, "cards", name + ".png"), optimize=True)
    px = np.array(im).astype(float) / 255.0
    rgb, al = px[..., :3], px[..., 3]
    # brightness that favors saturated glows over white highlights a little
    lum = (rgb.max(axis=2) * 0.7 + rgb.mean(axis=2) * 0.3) * (al > 0.6)
    cut = np.quantile(lum[al > 0.6], 0.985)
    gy, gx = np.where(lum >= cut)
    w = lum[gy, gx]
    cx, cy = float((gx * w).sum() / w.sum()), float((gy * w).sum() / w.sum())
    # the glow's color: from the bright, saturated pixels round that spot (its core is near white)
    yy, xx = np.mgrid[0:im.height, 0:im.width]
    near = (np.hypot(xx - cx, yy - cy) < 0.18 * im.height) & (al > 0.6)
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    k = near & (lum > np.quantile(lum[near], 0.7))
    wk = (sat * lum)[k] ** 2
    col = (rgb[k] * wk[:, None]).sum(0) / wk.sum()
    col = col / max(col.max(), 1e-6)
    meta[name] = {"glow": [round(cx / im.width - 0.5, 3), round(1.0 - cy / im.height, 3)],
                  "color": [round(float(c), 3) for c in col], "aspect": round(im.width / im.height, 3)}
    print(name, im.size, meta[name])
with open(os.path.join(dst, "cards", "lights.json"), "w") as f:
    json.dump(meta, f, indent=1)
