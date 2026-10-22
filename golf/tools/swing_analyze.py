"""Segment golfer sprite sheets into frames and measure registration drift."""
import sys, json, os
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

A = sys.argv[1]
OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)
SHEETS = {
    "driver": "reviewed/driver.png", "iron": "reviewed/iron.png", "putter": "reviewed/putter.png",
    "dir_driver": "hybrid/brittany_directions.png", "dir_iron": "hybrid/brittany_irons.png",
    "dir_putt": "hybrid/brittany_putts.png",
}

def segment(im):
    a = np.array(im)[..., 3] > 128
    m = ndimage.binary_dilation(a, iterations=6)
    lab, n = ndimage.label(m)
    boxes = []
    for sl in ndimage.find_objects(lab):
        h = sl[0].stop - sl[0].start; w = sl[1].stop - sl[1].start
        if h * w > 8000:
            boxes.append((sl[1].start, sl[0].start, sl[1].stop, sl[0].stop))
    # sort into rows, then columns
    boxes.sort(key=lambda b: (b[1] + b[3]) / 2)
    rows, cur = [], []
    for b in boxes:
        if cur and (b[1] + b[3]) / 2 - (cur[-1][1] + cur[-1][3]) / 2 > 80:
            rows.append(cur); cur = []
        cur.append(b)
    if cur: rows.append(cur)
    return [b for r in rows for b in sorted(r, key=lambda b: b[0])]

def measure(rgba):
    arr = np.array(rgba).astype(int)
    a = arr[..., 3] > 128
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    shoe = a & (r > 200) & (g > 195) & (b > 180)          # cream sneakers
    hair = a & (r > 140) & (g > 50) & (g < 130) & (b < 80) & (r - g > 60)
    ys, xs = np.nonzero(shoe)
    sole = ys.max() if len(ys) else np.nonzero(a)[0].max()
    shoe_cx = xs.mean() if len(xs) else a.shape[1] / 2
    hy = np.nonzero(hair)[0]
    head = hy.min() if len(hy) else np.nonzero(a)[0].min()
    return dict(sole=int(sole), shoe_cx=float(shoe_cx), head=int(head), height=int(sole - head))

report = {}
for name, rel in SHEETS.items():
    im = Image.open(os.path.join(A, rel)).convert("RGBA")
    frames = []
    for i, bx in enumerate(segment(im)):
        crop = im.crop(bx)
        m = measure(crop)
        m.update(index=i, box=bx)
        frames.append((crop, m))
    report[name] = [m for _, m in frames]
    # aligned filmstrip: sole baseline + shoe center, uniform cell
    H = max(m["sole"] for _, m in frames) + 20
    left = max(m["shoe_cx"] for _, m in frames) + 10
    right = max(c.width - m["shoe_cx"] for c, m in frames) + 10
    cw = int(left + right)
    per = 6 if len(frames) > 8 else len(frames)
    rows = (len(frames) + per - 1) // per
    strip = Image.new("RGBA", (cw * per, (H + 30) * rows), (40, 28, 56, 255))
    d = ImageDraw.Draw(strip)
    base_h = np.median([m["height"] for _, m in frames])
    for k, (c, m) in enumerate(frames):
        ox = (k % per) * cw; oy = (k // per) * (H + 30)
        px = int(ox + left - m["shoe_cx"]); py = int(oy + (H - 20) - m["sole"])
        strip.alpha_composite(c, (px, py))
        d.line([(ox, oy + H - 20), (ox + cw, oy + H - 20)], fill=(255, 80, 80, 255))
        d.line([(ox + left, oy), (ox + left, oy + H)], fill=(80, 200, 255, 120))
        d.line([(ox, oy + H - 20 - base_h), (ox + cw, oy + H - 20 - base_h)], fill=(120, 255, 120, 160))
        d.text((ox + 6, oy + H + 2), f"#{k} h={m['height']}", fill=(255, 255, 255, 255))
    strip.convert("RGB").save(os.path.join(OUT, f"{name}_strip.png"))
json.dump(report, open(os.path.join(OUT, "measure.json"), "w"), indent=1)
for n, fs in report.items():
    print(n, len(fs), "frames; heights", [f["height"] for f in fs])
