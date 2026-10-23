"""Cut the pin flags out of the artist's sheet (four painted pennants on a glowing backdrop).

usage: python3 -I prep_flags.py <sheet.png> <out_dir>

  python3 -I tools/prep_flags.py art_src/flags/flag_sheet.png game/assets/flags

The sheet is 2 x 2 flags, left to right then top to bottom, as NAMES. Each is cut from its quarter by
GrabCut (the backdrop is a soft gradient, the flag has a stitched hem), then straightened to a
rectangle: the hoist (left, by the pole) is the cut's left edge and every column is stretched from
the flag's top edge to its bottom edge there, so the painted wave flattens out and the game's own
wave can take over. The swallowtail notch stays in the alpha. Writes <out>/<name>.png, 512 x 320.
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage

NAMES = ["pumpkin", "ghost", "skull", "moon"]
OUT_W, OUT_H = 512, 320


def cut(quarter):
    h, w = quarter.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    rect = (int(w * 0.02), int(h * 0.06), int(w * 0.96), int(h * 0.9))
    bg = np.zeros((1, 65), np.float64)
    fg = np.zeros((1, 65), np.float64)
    cv2.grabCut(cv2.cvtColor(quarter, cv2.COLOR_RGB2BGR), mask, rect, bg, fg, 8, cv2.GC_INIT_WITH_RECT)
    m = (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)
    # the biggest piece, holes filled, edges smoothed a touch
    lab, n = ndimage.label(m)
    if n > 1:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        m = lab == (1 + int(np.argmax(sizes)))
    m = ndimage.binary_fill_holes(m)
    m = ndimage.binary_opening(m, iterations=2)
    return m


def straighten(rgb, m):
    """Columns from the hoist to the tips, each stretched from its top edge to its bottom edge."""
    cols = np.where(m.any(axis=0))[0]
    x0, x1 = cols[0], cols[-1]
    # the notch eats into the fly end: take the top and bottom edges from the outer hull of each column
    tops = np.array([np.argmax(m[:, x]) for x in range(x0, x1 + 1)], float)
    bots = np.array([m.shape[0] - 1 - np.argmax(m[::-1, x]) for x in range(x0, x1 + 1)], float)
    tops = ndimage.uniform_filter1d(tops, 9)
    bots = ndimage.uniform_filter1d(bots, 9)
    rgba = np.dstack([rgb, (m * 255).astype(np.uint8)])
    out = np.zeros((OUT_H, OUT_W, 4), np.uint8)
    xs = np.linspace(0, x1 - x0, OUT_W)
    for i, fx in enumerate(xs):
        k = int(round(fx))
        x = x0 + k
        ys = np.linspace(tops[k], bots[k], OUT_H)
        col = np.stack([ndimage.map_coordinates(rgba[:, x, c].astype(float), [ys], order=1) for c in range(4)], -1)
        out[:, i] = np.clip(col, 0, 255).astype(np.uint8)
    # bleed the cloth's colour into the clear pixels, so filtering doesn't draw a dark fringe
    a = out[..., 3] > 127
    idx = ndimage.distance_transform_edt(~a, return_distances=False, return_indices=True)
    out[..., :3] = out[..., :3][idx[0], idx[1]]
    out[..., 3] = np.where(a, 255, 0)
    return out


def main():
    sheet, out_dir = sys.argv[1], sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    im = np.asarray(Image.open(sheet).convert("RGB"))
    h, w = im.shape[:2]
    for i, name in enumerate(NAMES):
        r, c = divmod(i, 2)
        q = np.ascontiguousarray(im[r * h // 2:(r + 1) * h // 2, c * w // 2:(c + 1) * w // 2])
        m = cut(q)
        Image.fromarray(straighten(q, m)).save(os.path.join(out_dir, name + ".png"))
        Image.fromarray((m * 255).astype(np.uint8)).save(os.path.join(out_dir, name + "_mask.png"))
        print(name, "cut", int(m.sum()), "px")


if __name__ == "__main__":
    main()
