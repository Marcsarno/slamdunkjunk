"""Prepare the night-sky layers and the cast (the skeleton caddie and the black cat) for the game.

usage: python3 -I prep_night_art.py <src_dir> <game_assets_dir>

<src_dir> holds the artist's transparent PNGs under these names:
  moon_harvest.png moon_white.png          full moons (cropped here to the disc, centred, square)
  stars_1.png stars_2.png stars_3.png      star strips: sparse bright, medium, dense faint
  clouds_wisps.png clouds_puffs.png clouds_bank.png
  skelly_card.png skelly_bow.png cat_ball.png cat_walk.png    single poses
  cast_sheet.png                           4x4: two rows of skeleton poses, two rows of cat poses (the
                                           figures overrun the grid, so each is cut out by its outline)

Writes <assets>/sky/{moon_*,stars_*,clouds_*}.png and <assets>/cast/*.png (each trimmed to its figure).
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

SHEET_NAMES = [
    ["skelly_idle", "skelly_wave", "skelly_tip", "skelly_club"],
    ["skelly_point", "skelly_read", "skelly_cheer", "skelly_lean"],
    ["cat_sit", "cat_happy", "cat_walk2", "cat_pounce"],
    ["cat_crouch", "cat_groom", "cat_sleep", "cat_stretch"],
]


def moon(src, out, size=512):
    im = Image.open(src).convert("RGBA")
    a = np.array(im)[..., 3]
    ys, xs = np.where(a >= 250)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    r = ((xs.max() - xs.min()) + (ys.max() - ys.min())) / 4
    box = (int(round(cx - r)), int(round(cy - r)), int(round(cx + r)), int(round(cy + r)))
    im.crop(box).resize((size, size), Image.LANCZOS).save(out)


def trim(im, pad=6):
    a = np.array(im)[..., 3]
    ys, xs = np.where(a > 8)
    return im.crop((max(0, xs.min() - pad), max(0, ys.min() - pad),
                    min(im.width, xs.max() + 1 + pad), min(im.height, ys.max() + 1 + pad)))


def fit(im, h):
    return im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS) if im.height > h else im


def main():
    src, assets = sys.argv[1], sys.argv[2]
    sky = os.path.join(assets, "sky")
    cast = os.path.join(assets, "cast")
    os.makedirs(cast, exist_ok=True)
    for name in ("moon_harvest", "moon_white"):
        moon(os.path.join(src, name + ".png"), os.path.join(sky, name + ".png"))
    for name in ("stars_1", "stars_2", "stars_3", "clouds_wisps", "clouds_puffs", "clouds_bank"):
        im = Image.open(os.path.join(src, name + ".png")).convert("RGBA")
        im.resize((2048, round(im.height * 2048 / im.width)), Image.LANCZOS).save(os.path.join(sky, name + ".png"))
    for name in ("skelly_card", "skelly_bow", "cat_ball", "cat_walk"):
        fit(trim(Image.open(os.path.join(src, name + ".png")).convert("RGBA")), 512).save(os.path.join(cast, name + ".png"))
    sheet = Image.open(os.path.join(src, "cast_sheet.png")).convert("RGBA")
    px = np.array(sheet)
    solid = ndimage.binary_dilation(px[..., 3] > 8, iterations=4)     # whiskers and loose bits join their figure
    labels, n = ndimage.label(solid)
    sizes = ndimage.sum(solid, labels, range(1, n + 1))
    keep = sorted(np.argsort(sizes)[::-1][:16] + 1)
    figs = []
    for k in keep:
        ys, xs = np.where(labels == k)
        figs.append((ys.mean(), xs.mean(), k, xs.min(), xs.max(), ys.min(), ys.max()))
    ch = sheet.height / 4
    figs.sort(key=lambda f: (int(f[0] // ch), f[1]))
    for i, (_, _, k, x0, x1, y0, y1) in enumerate(figs):
        only = px.copy()
        only[..., 3] = np.where(labels == k, only[..., 3], 0)          # nothing of the neighbours
        fig = Image.fromarray(only).crop((max(0, x0 - 6), max(0, y0 - 6), x1 + 7, y1 + 7))
        fig.save(os.path.join(cast, SHEET_NAMES[i // 4][i % 4] + ".png"))
    print("wrote", sorted(os.listdir(sky)), sorted(os.listdir(cast)))


if __name__ == "__main__":
    main()
