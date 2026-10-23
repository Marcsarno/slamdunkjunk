"""Check a hole layout in 2D before building it: python3 -I plan_check.py <layout.json> <out.png>

Draws the layout's surfaces as the game will build them (hole_gen's own surface model), then the
plan's lines of play as shots: "plan": {"safe": [[x, y], ...], "risk": [[x, y], ...]} in the
layout, each a list of where the shots land, starting at the tee. Every shot is labelled with its
length in yards and the club the game would pick for it, and every landing gets the game's margin of
error drawn round it (scripts/main.gd _spread: 4.5% of a short shot up to 10% of a 220 m one, across;
three quarters of that along), so a pad too small for its shot shows at a glance.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hole_gen as hg  # noqa: E402

K = 2.0                    # px per metre
YD = 1.0936
COLORS = {hg.OOB: (24, 38, 30), hg.ROUGH: (52, 88, 50), hg.FAIRWAY: (118, 166, 72), hg.GREEN: (156, 204, 98),
          hg.SAND: (228, 210, 160), hg.TEE: (138, 186, 84), hg.FRINGE: (104, 150, 66), hg.DEEP: (36, 62, 40),
          hg.PATH: (184, 172, 152)}
CLUBS = [("Driver", 205), ("3 Wood", 185), ("5 Iron", 165), ("7 Iron", 145), ("9 Iron", 125), ("P Wedge", 105),
         ("S Wedge", 82), ("L Wedge", 58), ("Chip", 32)]
FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../game/assets/fonts/CaveatBrush-Regular.ttf")


def club_for(m, last):
    if last:
        return "Putt"
    pick = CLUBS[0][0] if m > CLUBS[0][1] else None
    for name, carry in reversed(CLUBS):
        if carry * 0.9 >= m:
            pick = name
            break
    return pick or "too long!"


def spread(m):
    share = 0.045 + (0.10 - 0.045) * min(1.0, m / 220.0)
    return m * share


def main():
    spec = json.load(open(sys.argv[1]))
    h = hg.Hole(spec)
    xs = np.arange(h.x0, h.x1, 1.0 / K)
    ys = np.arange(h.y0, h.y1, 1.0 / K)
    gx, gy = np.meshgrid(xs, ys)
    surf = h.surface(gx, gy, h.height(gx, gy))
    rgb = np.zeros(surf.shape + (3,), np.uint8)
    for k, c in COLORS.items():
        rgb[surf == k] = c
    rgb[surf == hg.WATER] = (60, 110, 200)
    for w in spec.get("webs", []):                     # spider webs: the ball stops dead in them
        r, _ = hg.ellipse_r(gx, gy, w)
        rgb[r < 1.0] = (rgb[r < 1.0] * 0.4 + np.array([170, 140, 220]) * 0.6).astype(np.uint8)
    for w in spec.get("cornfields", []):                # cornfields: lost in the corn
        r, _ = hg.ellipse_r(gx, gy, w)
        rgb[r < 1.0] = (rgb[r < 1.0] * 0.3 + np.array([200, 160, 60]) * 0.7).astype(np.uint8)
    img = Image.fromarray(rgb[::-1])
    dr = ImageDraw.Draw(img)
    top = ys[-1]

    def P(x, y):
        return ((x - h.x0) * K, (top - y) * K)

    font = ImageFont.truetype(FONT, 22)
    for g in spec.get("graveyards", []):
        cx, cy = P(*g["center"])
        r = g["radius"] * K
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(200, 200, 210), width=2)
    pin = spec["pin"]
    for name, col in (("safe", (255, 255, 255)), ("risk", (255, 220, 60))):
        pts = spec.get("plan", {}).get(name)
        if not pts:
            continue
        pts = [spec["tee"]["center"]] + pts
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            m = math.dist(a, b)
            last = math.dist(b, pin) < 1.0 and math.dist(a, pin) < 25
            dr.line([P(*a), P(*b)], fill=col, width=3)
            if not last and math.dist(b, pin) > 1.0:
                rr = spread(m) * K
                bx, by = P(*b)
                dr.ellipse([bx - rr, by - rr, bx + rr, by + rr], outline=col, width=2)
            mx, my = P((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            dr.text((mx + 8, my - 12), "%d yd %s" % (round(m * YD), club_for(m, last)), font=font, fill=col,
                    stroke_width=3, stroke_fill=(10, 6, 14))
    tx, ty = P(*spec["tee"]["center"])
    dr.rectangle([tx - 6, ty - 6, tx + 6, ty + 6], fill=(255, 255, 255))
    px, py = P(*pin)
    dr.polygon([(px, py - 24), (px + 14, py - 19), (px, py - 14)], fill=(235, 60, 50))
    dr.line([px, py, px, py - 24], fill=(255, 255, 255), width=2)
    dr.text((10, 8), "%s  par %d  ·  %d yd" % (spec["name"], spec["par"], round(h.length * YD)), font=font,
            fill=(255, 190, 110), stroke_width=3, stroke_fill=(10, 6, 14))
    img.save(sys.argv[2])
    print(sys.argv[2], img.size, "length %.0f m" % h.length)


if __name__ == "__main__":
    main()
