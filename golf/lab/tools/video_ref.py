"""Cut the face-on swing video into the Swing Lab's video reference (look and spacing only, never game art).

usage: python3 -I video_ref.py <video> <out dir, e.g. golf/lab/assets/video>

The video is a white-background, fixed-camera, face-on swing of Brittany. Each frame from just before
the takeaway to the finish is keyed to a transparent cut-out (background = near-white paper connected to
the border, plus the grey floor shadow) and saved as v_###.webp. video.json records what the lab needs
to stand the picture beside or over her at her own size:
  tpose_px      her height in pixels in the opening T-pose (scales the picture to her model's height)
  feet_x, sole_y  the middle of her shoes and the sole line at address (pinned to her feet and the ground)
  keys          address / top / impact / finish, found from the video itself:
                impact = the ball vanishes (half a frame before the first frame without it),
                top = the stillest frame between takeaway and impact,
                address = the last still frame before the takeaway, finish = the first still frame after.
The video's own impact is not drawn (the club jumps from behind her to past the ball between two
frames), so impact in the video is a timing mark, not a pose to copy.
"""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image
from scipy import ndimage

VIDEO, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)


def cut(rgb):
    a = rgb.astype(np.float32)
    lum = a.mean(axis=2)
    sat = a.max(axis=2) - a.min(axis=2)
    paper = (a.min(axis=2) >= 246) & (sat <= 6)             # the white page
    shadow = (lum > 150) & (sat <= 7)                        # the soft grey floor shadow (neutral grey) ...
    shadow[: int(a.shape[0] * 0.86)] = False                 # ... which is only ever on the floor (the steel shaft is grey too)
    # background = paper connected to the border, grown into neutral grey shadow touching it
    lab, _ = ndimage.label(paper)
    edge_ids = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    bg = np.isin(lab, edge_ids[edge_ids > 0])
    lab2, _ = ndimage.label(paper | shadow)
    touch = np.unique(lab2[bg])
    bg |= np.isin(lab2, touch[touch > 0]) & shadow
    # pockets of pure paper enclosed by her arms and the club are background too
    plab, pn = ndimage.label(paper & ~bg)
    if pn:
        psz = ndimage.sum(np.ones_like(plab), plab, range(1, pn + 1))
        bg |= np.isin(plab, 1 + np.nonzero(psz > 120)[0])
    fg = ~bg
    # keep her and the club (8-connected, so a 1 px shaft stays attached); drop specks and the ball
    flab, n = ndimage.label(fg, structure=np.ones((3, 3)))
    if n:
        sizes = ndimage.sum(np.ones_like(flab), flab, range(1, n + 1))
        keep = np.isin(flab, 1 + np.nonzero(sizes >= 60)[0])
        for i, sl in enumerate(ndimage.find_objects(flab), start=1):
            hh, ww = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
            if sizes[i - 1] < sizes.max() * 0.05 and 0.6 < hh / max(ww, 1) < 1.6 and max(hh, ww) < 40:
                keep[flab == i] = False
        fg = keep
    # soft edge: un-mix from white in a 2 px band around the cut
    band = ndimage.binary_dilation(fg, iterations=2) & ~ndimage.binary_erosion(fg, iterations=1)
    mix = np.clip((255.0 - a.min(axis=2)) / 255.0 * 1.6, 0, 1)
    alpha = np.where(band, mix, fg.astype(np.float32))
    safe = np.maximum(alpha, 1e-3)[..., None]
    col = np.clip((a - (1 - alpha[..., None]) * 255.0) / safe, 0, 255)
    col = np.where(alpha[..., None] > 0.02, col, 0)
    return np.dstack([col, alpha * 255]).astype(np.uint8), fg


def has_ball(rgb, fg):
    # the ball: a small round grey-rimmed blob low in the frame that is not part of her
    a = rgb.astype(np.float32)
    lum = a.mean(axis=2)
    sat = a.max(axis=2) - a.min(axis=2)
    rim = (lum < 225) & (lum > 120) & (sat < 25) & ~fg
    rim[: int(a.shape[0] * 0.80)] = False
    for sl in ndimage.find_objects(ndimage.label(rim)[0]):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if 8 <= h <= 30 and 8 <= w <= 30 and 0.6 < h / w < 1.6:
            return True
    return False


def shoes(fg, sole):
    # the two outer runs of her outline just above the sole line (the club head can sit between them)
    cols = np.nonzero(fg[sole - 28: sole].any(axis=0))[0]
    runs = [r for r in np.split(cols, np.nonzero(np.diff(cols) > 6)[0] + 1) if len(r) > 10]
    return (runs[0][0] + runs[0][-1]) / 2, (runs[-1][0] + runs[-1][-1]) / 2


with tempfile.TemporaryDirectory() as tmp:
    subprocess.run(["ffmpeg", "-loglevel", "error", "-i", VIDEO, os.path.join(tmp, "f_%04d.png")], check=True)
    files = sorted(f for f in os.listdir(tmp) if f.endswith(".png"))
    fps = 24
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                            "-of", "csv=p=0", VIDEO], capture_output=True, text=True).stdout.strip()
    if "/" in probe:
        n, d = probe.split("/")
        fps = round(float(n) / float(d), 3)
    cuts, motion, ball = [], [], []
    prev = None
    for f in files:
        rgb = np.asarray(Image.open(os.path.join(tmp, f)).convert("RGB"))
        rgba, fg = cut(rgb)
        al = rgba[..., 3].astype(np.float32) / 255
        motion.append(0.0 if prev is None else float(np.abs(al - prev).mean() * 1000))
        prev = al
        ball.append(has_ball(rgb, fg))
        cuts.append((rgba, fg))

h, w = cuts[0][1].shape
n = len(cuts)
# impact: the end of the longest stretch with the ball in view (at address the club head hides it)
runs, start = [], None
for i in range(n + 1):
    if i < n and ball[i]:
        start = i if start is None else start
    elif start is not None:
        runs.append((i - start, start, i))
        start = None
gone = max(runs)[2]
impact = gone - 0.5
top = min(range(gone - 20, gone - 3), key=lambda i: motion[i])
address = top
while address > 0 and motion[address] > 3:
    address -= 1
finish = next((i for i in range(gone + 5, n) if motion[i] < 10), n - 1)
first, last = max(0, address - 4), min(n - 1, finish + 2)

# scale from the opening T-pose: hair to sole
fg0 = cuts[0][1]
ys0 = np.nonzero(fg0.any(axis=1))[0]
sole = int(np.median([np.nonzero(cuts[i][1][:, int(x)])[0].max()
                      for i in (address,) for x in shoes(cuts[i][1], int(h * 0.93))]))
feet = shoes(cuts[address][1], sole)

for i in range(first, last + 1):
    Image.fromarray(cuts[i][0], "RGBA").save(os.path.join(OUT, f"v_{i:03d}.webp"), quality=80, alpha_quality=80, method=6)
meta = {
    "fps": fps, "size": [int(w), int(h)], "first": first, "last": last,
    "keys": {"address": address, "top": top, "impact": impact, "finish": finish},
    "tpose_px": int(ys0.max() - ys0.min()), "feet_x": float(sum(feet) / 2), "stance_px": float(feet[1] - feet[0]),
    "sole_y": sole,
    "note": "Face-on, camera fixed. Target to the right of the picture. The video skips its impact pose.",
}
json.dump(meta, open(os.path.join(OUT, "video.json"), "w"), indent=1)
print(json.dumps(meta))
print("motion around the swing:", " ".join(f"{i}:{motion[i]:.0f}" for i in range(first, last + 1)))
