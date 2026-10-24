"""Cut Brittany's celebration (a front-on fist pump, putter in hand) out of Marc's video into game frames.

usage: python3 -I prep_celebrate.py <video> <golfer_assets_dir> [--sheet <png>]

  python3 -I tools/prep_celebrate.py art_src/celebrate/putt_fist_pump.mp4 game/assets/golfer

Every STEP-th frame is cut from the white backdrop (prep_video_swing.foreground, with this video's
floor line), defringed, scaled so she stands BODY_PX tall like the other sets, and written as
celebrate_NN.png. golfer.json gets a "video_celebrate" set (view face) whose "down" plays them in
order (the game plays it as a one-off, like a downswing with no contact).
"""
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prep_video_swing as pvs  # noqa: E402

STEP = 2                 # every other frame of the 24 fps video: 12 a second
BODY_PX = 420            # her height in the frames, about the other sets'
SET = "video_celebrate"


def main():
    video, out = sys.argv[1], sys.argv[2]
    sheet = sys.argv[sys.argv.index("--sheet") + 1] if "--sheet" in sys.argv else None
    frames = pvs.read_frames(video)
    nums = sorted(frames)[::STEP]
    h = frames[nums[0]].shape[0]
    pvs.FLOOR_Y = int(h * 0.86)          # her soles sit near the bottom of this video
    cut = {}
    for n in nums:
        a = frames[n]
        keep = pvs.foreground(a)
        light = (a.mean(2) >= 215) & ((a.max(2) - a.min(2)) <= 18)
        light[:pvs.FLOOR_Y] = False
        keep &= ndimage.binary_fill_holes(keep & ~light) | ~light       # no floor shadow
        lab, k = ndimage.label(keep, structure=np.ones((3, 3)))
        if k:
            sizes = ndimage.sum(keep, lab, range(1, k + 1))
            keep &= np.isin(lab, [i + 1 for i in range(k) if sizes[i] >= 60])
        rgba = np.dstack([pvs.defringe(a, keep).clip(0, 255).astype(np.uint8), (keep * 255).astype(np.uint8)])
        cut[n] = rgba
    # one scale and one foot anchor for all: the soles at the first frame
    k0 = cut[nums[0]][..., 3] > 0
    rows = np.nonzero(k0.any(1))[0]
    top, sole = rows.min(), rows.max()
    scale = BODY_PX / float(sole - top)
    cols = np.nonzero(k0[sole - 25:sole + 1].any(0))[0]
    anchor = ((cols.min() + cols.max()) / 2.0, float(sole))
    meta = {}
    for n in nums:
        img = Image.fromarray(cut[n])
        img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
        x0, y0, x1, y1 = img.getbbox()
        img = img.crop((x0, y0, x1, y1))
        name = "celebrate_%02d.png" % n
        img.save(os.path.join(out, name), optimize=True)
        meta[str(n)] = {"file": name, "size": [img.width, img.height],
                        "anchor": [round(anchor[0] * scale - x0, 1), round(anchor[1] * scale - y0, 1)],
                        "height": BODY_PX, "club_head": None}
    path = os.path.join(out, "golfer.json")
    sets = json.load(open(path))
    step_ms = round(1000.0 * STEP / 24.0)
    down_ms = [step_ms] * len(nums)
    down_ms[-1] = 900
    sets[SET] = {"view": "face", "body_px": BODY_PX, "frames": meta, "back": [nums[0]], "down": nums,
                 "contact": -1, "down_ms": down_ms}
    with open(path, "w") as f:
        json.dump(sets, f, indent=1)
    print("wrote %d frames, %.1f s" % (len(nums), sum(down_ms) / 1000.0))
    if sheet:
        w = 120
        ims = [Image.open(os.path.join(out, meta[str(n)]["file"])) for n in nums[::3]]
        c = Image.new("RGB", (w * len(ims), int(w * 2.2)), (40, 120, 40))
        for i, im in enumerate(ims):
            im = im.resize((w, int(im.height * w / im.width)))
            c.paste(im, (i * w, 0), im)
        c.save(sheet)


if __name__ == "__main__":
    main()
