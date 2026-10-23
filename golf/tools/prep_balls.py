"""Cut the slingshot balls (hud.gd Sling) out of the artist's sheet.

usage: python3 -I prep_balls.py <game_assets_dir> <sheet.png>=<ball>,<ball>,... [more sheets]

  python3 -I tools/prep_balls.py game/assets art_src/balls/balls_sheet.png=pumpkin,ghost,skull \
      art_src/balls/balls_sheet_2.png=mummy,vampire,frank,bat

Each sheet is a transparent PNG, one ball per row (top to bottom, as named) and one pose per column
(POSES below). Each
ball is found by its own outline (alpha), and both of its poses are scaled alike and centred on the
same spot, so swapping poses doesn't make it jump. Writes <assets>/balls/<ball>/<pose>.png: 512 px
squares with the ball ART_FILL of the height (hud.gd's Sling.ART_FILL).
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

POSES = ["still", "launch"]
SIZE = 512
ART_FILL = 0.8
FAINT = 6          # alpha below this (the faint glow the art was painted in) goes


def main():
    out = sys.argv[1]
    for arg in sys.argv[2:]:
        sheet, names = arg.split("=")
        cut_sheet(sheet, names.split(","), out)


def cut_sheet(sheet, balls, out):
    im = np.asarray(Image.open(sheet).convert("RGBA")).copy()
    im[..., 3][im[..., 3] < FAINT] = 0
    h, w = im.shape[:2]
    rows, cols = len(balls), len(POSES)
    for r, ball in enumerate(balls):
        cuts = []
        for c, pose in enumerate(POSES):
            cell = im[r * h // rows:(r + 1) * h // rows, c * w // cols:(c + 1) * w // cols]
            solid = cell[..., 3] > 128
            lab, n = ndimage.label(solid)
            biggest = 1 + int(np.argmax(ndimage.sum(solid, lab, range(1, n + 1))))
            ys, xs = np.nonzero(ndimage.binary_dilation(lab == biggest, iterations=6) & (cell[..., 3] > 0))
            cuts.append((pose, cell[ys.min():ys.max() + 1, xs.min():xs.max() + 1]))
        # by height, so the round of every ball comes out the same size whatever sticks out of its
        # sides (ears, bolts, wings), as long as those still fit the square
        tall = max(a.shape[0] for _, a in cuts)
        wide = max(a.shape[1] for _, a in cuts)
        scale = min(SIZE * ART_FILL / tall, SIZE * 0.97 / wide)
        os.makedirs(os.path.join(out, "balls", ball), exist_ok=True)
        for pose, a in cuts:
            img = Image.fromarray(a)
            img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
            canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
            canvas.paste(img, ((SIZE - img.width) // 2, (SIZE - img.height) // 2))
            path = os.path.join(out, "balls", ball, pose + ".png")
            canvas.save(path, optimize=True)
            print(path, img.size)


if __name__ == "__main__":
    main()
