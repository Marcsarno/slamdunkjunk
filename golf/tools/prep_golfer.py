"""Cut Brittany's swing sheets into clean, foot-anchored frames for the game.

usage: python3 -I prep_golfer.py <characters_assets_dir> <out_dir>

<characters_assets_dir> is the `assets` folder of GraveyardShiftGolf_01_Characters_and_Animations.
Writes one trimmed PNG per frame plus golfer.json describing every set:
  anchor   foot point (px from the frame's top-left) that sits on the ground
  body_px  address-pose height (sole to top of hair) used to scale the set to world size
  back     frames scrubbed while the player pulls back the slingshot
  down     frames played after release; `contact` indexes into `down`
"""
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)

# Face-on sets: frames are referenced by reading order on the sheet.
FACE_SETS = {
    "driver": dict(sheet="reviewed/driver.png", back=[0, 1, 3, 4], down=[1, 5, 6, 7], contact=1,
                   down_ms=[60, 110, 150, 600]),
    "iron": dict(sheet="reviewed/iron.png", back=[0, 2, 3, 4], down=[5, 6, 8, 9, 10, 11], contact=2,
                 down_ms=[50, 50, 110, 90, 120, 600]),
    "putter": dict(sheet="reviewed/putter.png", back=[0, 2], down=[0, 3], contact=0,
                   down_ms=[80, 600]),
}
# Back three-quarter placeholders (row 0 of the 4x4 direction sheets: seen from behind-right,
# club toward the target). Columns: address, top, contact, finish.
BACK_SETS = {
    "back_driver": "hybrid/brittany_directions.png",
    "back_iron": "hybrid/brittany_irons.png",
    "back_putter": "hybrid/brittany_putts.png",
}


def clean(img):
    a = np.array(img.convert("RGBA"))
    a[..., 3] = np.where(a[..., 3] < 24, 0, a[..., 3])
    return Image.fromarray(a)


def segment(im):
    a = np.array(im)[..., 3] > 128
    lab, _ = ndimage.label(ndimage.binary_dilation(a, iterations=6))
    boxes = [(s[1].start, s[0].start, s[1].stop, s[0].stop) for s in ndimage.find_objects(lab)
             if (s[0].stop - s[0].start) * (s[1].stop - s[1].start) > 8000]
    boxes.sort(key=lambda b: (b[1] + b[3]) / 2)
    rows, cur = [], []
    for b in boxes:
        if cur and (b[1] + b[3]) / 2 - (cur[-1][1] + cur[-1][3]) / 2 > 80:
            rows.append(cur)
            cur = []
        cur.append(b)
    rows.append(cur)
    return [b for r in rows for b in sorted(r, key=lambda b: b[0])]


def largest_island(img):
    a = np.array(img)
    lab, n = ndimage.label(ndimage.binary_dilation(a[..., 3] > 128, iterations=3))
    if n > 1:
        sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
        keep = lab == (1 + int(np.argmax(sizes)))
        a[..., 3] = np.where(keep, a[..., 3], 0)
    out = Image.fromarray(a)
    return out.crop(out.getbbox())


def measure(img):
    arr = np.array(img).astype(int)
    a = arr[..., 3] > 128
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    shoe = a & (r > 200) & (g > 195) & (b > 180)
    hair = a & (r > 140) & (g > 50) & (g < 130) & (b < 80) & (r - g > 60)
    ys, xs = np.nonzero(shoe)
    sole = int(ys.max()) if len(ys) else int(np.nonzero(a)[0].max())
    cx = float(xs.mean()) if len(xs) else a.shape[1] / 2
    hy = np.nonzero(hair)[0]
    head = int(hy.min()) if len(hy) else int(np.nonzero(a)[0].min())
    return sole, cx, sole - head


def club_head(img, sole):
    """Lowest club pixels (not shoe/skin): where the ball sits at address."""
    arr = np.array(img).astype(int)
    a = arr[..., 3] > 128
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    shoe = (r > 200) & (g > 195) & (b > 180)
    sat = np.max(arr[..., :3], axis=2) - np.min(arr[..., :3], axis=2)
    club = a & ~shoe & (sat < 40)
    band = np.zeros_like(club)
    band[max(0, sole - int(img.height * 0.12)):, :] = True
    ys, xs = np.nonzero(club & band)
    if not len(xs):
        return None
    far = xs > np.percentile(xs, 70) if xs.mean() > img.width / 2 else xs < np.percentile(xs, 30)
    return [round(float(xs[far].mean()), 1), round(float(ys[far].max()), 1)]


def save(img, name):
    sole, cx, height = measure(img)
    img.save(os.path.join(OUT, name + ".png"))
    return dict(file=name + ".png", size=list(img.size), anchor=[round(cx, 1), sole], height=height,
                club_head=club_head(img, sole))


data = {}
for set_name, spec in FACE_SETS.items():
    sheet = clean(Image.open(os.path.join(SRC, spec["sheet"])))
    boxes = segment(sheet)
    frames = {}
    for idx in sorted(set(spec["back"] + spec["down"])):
        frames[idx] = save(sheet.crop(boxes[idx]), f"{set_name}_{idx:02d}")
    data[set_name] = dict(
        view="face",
        body_px=frames[spec["back"][0]]["height"],
        frames={str(k): v for k, v in frames.items()},
        back=spec["back"], down=spec["down"], contact=spec["contact"], down_ms=spec["down_ms"],
    )

for set_name, rel in BACK_SETS.items():
    sheet = clean(Image.open(os.path.join(SRC, rel)))
    cw, ch = sheet.width / 4, sheet.height / 4
    frames = {}
    for col in range(4):
        # widen the cell so club heads that cross the grid line are kept; the largest island wins
        cell = sheet.crop((max(0, int(col * cw) - 70), 0, min(sheet.width, int((col + 1) * cw) + 70), int(ch)))
        frames[col] = save(largest_island(cell), f"{set_name}_{col:02d}")
    data[set_name] = dict(view="back", body_px=frames[0]["height"],
                          frames={str(k): v for k, v in frames.items()},
                          back=[0, 1], down=[2, 3], contact=0, down_ms=[120, 600])

with open(os.path.join(OUT, "golfer.json"), "w") as f:
    json.dump(data, f, indent=1)
for k, v in data.items():
    print(k, v["view"], "body_px", v["body_px"], "frames", len(v["frames"]))
