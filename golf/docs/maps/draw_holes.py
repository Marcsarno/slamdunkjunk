"""Simple top-down maps of the nine built holes, from what the game loads (surface.bin, terrain.json,
props.json), all at one scale: python3 -I draw_holes.py <golf/game/assets/holes> <out.png>"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

PX_PER_M = 1.15
COLORS = {0: (24, 38, 30), 1: (52, 88, 50), 2: (118, 166, 72), 3: (156, 204, 98), 4: (228, 210, 160),
          6: (138, 186, 84), 7: (104, 150, 66), 8: (36, 62, 40), 9: (184, 172, 152)}
FONT = "/home/user/slamdunkjunk/golf/game/assets/fonts/CaveatBrush-Regular.ttf"
YD = 1.0936


def hole_map(d):
    t = json.load(open(os.path.join(d, "terrain.json")))
    sf = t["surf"]
    surf = np.frombuffer(open(os.path.join(d, sf["file"]), "rb").read(), np.uint8).reshape(sf["ny"], sf["nx"])
    g = t["theme"].get("water_glow", [0.35, 0.55, 1.0])
    water = tuple(int(40 + 150 * c) for c in (g if max(g) > 0.05 else [0.35, 0.55, 1.0]))
    rgb = np.zeros(surf.shape + (3,), np.uint8)
    for k, c in COLORS.items():
        rgb[surf == k] = c
    rgb[surf == 5] = water
    img = Image.fromarray(rgb[::-1])           # up-range is up
    k = PX_PER_M * sf["cell"]
    img = img.resize((round(img.width * k), round(img.height * k)), Image.NEAREST)
    ox, oy = t["origin"]
    top = oy + sf["ny"] * sf["cell"]

    def P(x, y):
        return ((x - ox) * PX_PER_M, (top - y) * PX_PER_M)

    dr = ImageDraw.Draw(img)
    props = json.load(open(os.path.join(d, "props.json")))
    for o in props["obstacles"]:            # trunks, tombstones, rocks: what a ball can hit
        x, y = P(o["pos"][0], o["pos"][1])
        r = max(1.2, o.get("r", 0.5) * PX_PER_M)
        dr.ellipse([x - r, y - r, x + r, y + r], fill=(14, 10, 18))
    cp = t.get("cart_path") or []
    path = [P(q[0], q[1]) for q in t["path"]]
    for i in range(0, len(path) - 1, 2):
        dr.line([path[i], path[i + 1]], fill=(255, 245, 220), width=2)
    tx, ty = P(*t["tee"][:2])
    dr.rectangle([tx - 5, ty - 5, tx + 5, ty + 5], fill=(255, 255, 255), outline=(20, 10, 20))
    px, py = P(*t["pin"][:2])
    dr.line([px, py, px, py - 22], fill=(255, 255, 255), width=2)
    dr.polygon([(px, py - 22), (px + 12, py - 18), (px, py - 14)], fill=(235, 60, 50))
    return img, t


def main():
    root, out = sys.argv[1], sys.argv[2]
    maps = [hole_map(os.path.join(root, "h%02d" % n)) for n in range(1, 10)]
    cw = max(m[0].width for m in maps) + 30
    ch = max(m[0].height for m in maps) + 90
    sheet = Image.new("RGB", (cw * 3, ch * 3), (22, 14, 30))
    dr = ImageDraw.Draw(sheet)
    big = ImageFont.truetype(FONT, 30)
    small = ImageFont.truetype(FONT, 22)
    for i, (img, t) in enumerate(maps):
        x0, y0 = (i % 3) * cw, (i // 3) * ch
        sheet.paste(img, (x0 + (cw - img.width) // 2, y0 + 80 + (ch - 90 - img.height)))
        dr.text((x0 + 16, y0 + 10), "%d. %s" % (t["number"], t["name"]), font=big, fill=(255, 190, 110))
        dr.text((x0 + 16, y0 + 46), "Par %d  ·  %d yd" % (t["par"], round(t["length"] * YD / 5) * 5), font=small,
                fill=(240, 232, 220))
    sheet.save(out, optimize=True)
    print(out, sheet.size)


if __name__ == "__main__":
    main()
