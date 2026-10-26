"""Draw each hole as it is now (from courses/holes/*.json) and as proposed, as course maps in one style,
beside its concept. usage: python3 -I plan_holes.py <golf dir> <out dir>"""
import json
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

GOLF, OUT = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else (None, None)
YD = 1.0936
SS = 2                      # supersampling
PX = 470                    # map size


def font(sz):
    for f in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"]:
        try:
            return ImageFont.truetype(f, sz)
        except Exception:
            pass
    return ImageFont.load_default()


def densify(path, widths, step=2.0):
    out = []
    for i in range(len(path) - 1):
        (x0, y0), (x1, y1) = path[i], path[i + 1]
        w0, w1 = widths[i], widths[i + 1]
        n = max(1, int(math.dist(path[i], path[i + 1]) / step))
        for k in range(n):
            t = k / n
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, w0 + (w1 - w0) * t))
    out.append((path[-1][0], path[-1][1], widths[-1]))
    return out


def length(path):
    return sum(math.dist(path[i], path[i + 1]) for i in range(len(path) - 1))


def ellipse_pts(c, r, rot, n=48):
    rx, ry = (r, r) if not isinstance(r, (list, tuple)) else r
    return [(c[0] + rx * math.cos(a) * math.cos(rot) - ry * math.sin(a) * math.sin(rot),
             c[1] + rx * math.cos(a) * math.sin(rot) + ry * math.sin(a) * math.cos(rot))
            for a in [2 * math.pi * k / n for k in range(n)]]


def draw(spec, title):
    """spec: path, widths, fairway_start, rough, green, tee, bunkers, hazards [{shape: ellipse|line, color,
    label}], features [{pos,label}], safe, risk, extra_fairways [[path, widths]], fairway (bool)"""
    pts = list(spec["path"])
    for h in spec.get("hazards", []):
        pts += ellipse_pts(h["center"], h["radius"], h.get("rotation", 0)) if "center" in h else h["line"]
    for f in spec.get("features", []):
        pts.append(f["pos"])
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    span = max(max(xs) - min(xs), max(ys) - min(ys)) + 90
    S = PX * SS
    k = S / span

    def P(x, y):
        return ((x - cx) * k + S / 2, S / 2 - (y - cy) * k)

    img = Image.new("RGB", (S, S), (22, 12, 32))
    d = ImageDraw.Draw(img)
    rnd = random.Random(hash(title) & 0xffff)
    for _ in range(int(S * S / 900)):          # the woods
        x, y = rnd.uniform(0, S), rnd.uniform(0, S)
        r = rnd.uniform(5, 14) * SS
        c = rnd.choice([(48, 26, 70), (60, 30, 82), (40, 22, 58), (90, 40, 30), (70, 34, 52)])
        d.ellipse([x - r, y - r, x + r, y + r], fill=c)
    rough = spec.get("rough", 13)
    fairways = [(spec["path"], spec["widths"], spec.get("fairway_start", 34))] + \
        [(p, w, 0) for p, w in spec.get("extra_fairways", [])]
    for path, widths, start in fairways:      # rough, then fairway
        for x, y, w in densify(path, widths):
            r = (w / 2 + rough) * k
            X, Y = P(x, y)
            d.ellipse([X - r, Y - r, X + r, Y + r], fill=(46, 72, 34))
    tx, ty = spec["path"][0]
    for path, widths, start in fairways:
        if not spec.get("fairway", True):
            continue
        dist = 0.0
        prev = None
        for x, y, w in densify(path, widths):
            if prev:
                dist += math.dist(prev, (x, y))
            prev = (x, y)
            if dist < start and path is spec["path"]:
                continue
            r = w / 2 * k
            X, Y = P(x, y)
            d.ellipse([X - r, Y - r, X + r, Y + r], fill=(88, 146, 56))
    for pad in spec.get("pads", []):
        d.polygon([P(*q) for q in ellipse_pts(pad["center"], pad["radius"], pad.get("rotation", 0))], fill=(88, 146, 56))
    for h in spec.get("hazards", []):
        col = tuple(h["color"])
        if "line" in h:
            d.line([P(*q) for q in h["line"]], fill=col, width=int(h.get("width", 10) * k), joint="curve")
        else:
            d.polygon([P(*q) for q in ellipse_pts(h["center"], h["radius"], h.get("rotation", 0))], fill=col)
    g = spec["green"]
    d.polygon([P(*q) for q in ellipse_pts(g["center"], [g["radius"][0] + 3, g["radius"][1] + 3], g.get("rotation", 0))], fill=(100, 165, 66))
    d.polygon([P(*q) for q in ellipse_pts(g["center"], g["radius"], g.get("rotation", 0))], fill=(132, 205, 90))
    for b in spec.get("bunkers", []):
        d.polygon([P(*q) for q in ellipse_pts(b["center"], b["radius"], b.get("rotation", 0))], fill=(226, 205, 150))
    X, Y = P(tx, ty)
    d.rectangle([X - 5 * k, Y - 6 * k, X + 5 * k, Y + 6 * k], fill=(150, 210, 120), outline=(255, 255, 255), width=SS * 2)
    pin = spec.get("pin", g["center"])
    X, Y = P(*pin)
    d.line([X, Y, X, Y - 26 * SS], fill=(240, 240, 240), width=SS * 2)
    d.polygon([(X, Y - 26 * SS), (X + 14 * SS, Y - 21 * SS), (X, Y - 16 * SS)], fill=(230, 40, 40))

    def dashed(line, col, dash, gap, w):
        for a, b in zip(line, line[1:]):
            A, B = P(*a), P(*b)
            L = math.dist(A, B)
            t = 0.0
            while t < L:
                t1 = min(L, t + dash)
                d.line([A[0] + (B[0] - A[0]) * t / L, A[1] + (B[1] - A[1]) * t / L,
                        A[0] + (B[0] - A[0]) * t1 / L, A[1] + (B[1] - A[1]) * t1 / L], fill=col, width=w)
                t = t1 + gap
    if spec.get("safe"):
        dashed(spec["safe"], (255, 255, 255), 14 * SS, 9 * SS, 3 * SS)
    if spec.get("risk"):
        dashed(spec["risk"], (255, 222, 60), 5 * SS, 6 * SS, 3 * SS)
    F = font(13 * SS)
    for h in spec.get("hazards", []) + spec.get("features", []):
        if h.get("label"):
            c = h.get("pos") or h.get("center") or h["line"][len(h["line"]) // 2]
            X, Y = P(*c)
            tw = d.textlength(h["label"], font=F)
            d.text((X - tw / 2 + SS, Y - 7 * SS + SS), h["label"], fill=(0, 0, 0), font=F)
            d.text((X - tw / 2, Y - 7 * SS), h["label"], fill=(255, 245, 230), font=F)
    # scale: 100 yards
    L = 100 / YD * k
    d.line([20 * SS, S - 20 * SS, 20 * SS + L, S - 20 * SS], fill=(255, 255, 255), width=SS * 2)
    d.text((20 * SS, S - 40 * SS), "100 yd", fill=(255, 255, 255), font=font(12 * SS))
    return img.resize((PX, PX), Image.LANCZOS)


def current(fname):
    d = json.load(open(os.path.join(GOLF, "courses", "holes", fname)))
    hz = []
    for w in d.get("water", []):
        hz.append({"center": w["center"], "radius": w["radius"], "rotation": w.get("rotation", 0), "color": (60, 110, 200)})
    for w in d.get("webs", []):
        hz.append({"center": w["center"], "radius": w["radius"], "rotation": w.get("rotation", 0), "color": (150, 120, 190)})
    for c in d.get("cornfields", []):
        hz.append({"center": c["center"], "radius": c["radius"], "rotation": c.get("rotation", 0), "color": (176, 128, 50)})
    for gy in d.get("graveyards", []):
        if gy["count"] > 20:
            hz.append({"center": gy["center"], "radius": gy["radius"], "color": (85, 80, 100), "label": "graveyard"})
    return {"path": d["path"], "widths": d["fairway_width"], "fairway_start": d.get("fairway_start", 34),
            "rough": d.get("rough_width", 13), "green": d["green"], "pin": d.get("pin", d["green"]["center"]),
            "bunkers": d.get("bunkers", []), "hazards": hz, "pads": d.get("pads", []),
            "features": [{"pos": f["pos"], "label": f.get("model") or f.get("image", "").replace("statue_", "").replace("light_", "")}
                         for f in d.get("features", []) if f.get("model") not in ("pillar",)],
            "safe": d["path"], "par": d["par"], "name": d["name"]}


def g(c, r, rot=0.0):
    return {"center": c, "radius": r, "rotation": rot}


def stream(points, half=6):
    return {"line": points, "width": half * 2, "color": (70, 200, 220)}


POND, PURPLE, BLOOD, MARSH, WEB, CORN, PATCH, GRAVE, HEDGE, RAVINE = (
    (60, 110, 200), (150, 60, 190), (170, 20, 40), (70, 200, 220), (150, 120, 190), (176, 128, 50),
    (200, 110, 30), (85, 80, 100), (24, 60, 30), (60, 45, 70))

PROPOSED = {
    1: {"par": 4, "turn": "right (mirrored concept)",
        "path": [[0, 0], [0, 60], [2, 130], [10, 195], [45, 248], [100, 282], [140, 296]],
        "widths": [26, 36, 46, 48, 40, 30, 26], "fairway_start": 40,
        "green": {"center": [142, 298], "radius": [14, 11], "rotation": 0.5},
        "bunkers": [g([126, 312], [5, 3], 0.4), g([158, 286], [4, 3], -0.6), g([-18, 210], [4, 8], 0.1)],
        "hazards": [dict(g([72, 200], [30, 22], 0.4), color=POND, label="pond"),
                    dict(g([60, 85], [26, 38], 0.2), color=PATCH, label="pumpkin patch")],
        "risk": [[0, 0], [62, 180], [142, 298]], "scale": 0.84,
        "note": "Dogleg RIGHT round the pond (concept flipped). Wide landing at the corner (48 yd); the pond "
                "sits in the corner, so cutting it is the risky line."},
    2: {"par": 3, "turn": "none: tee to green",
        "path": [[0, 0], [18, 132]], "widths": [26, 26], "fairway_start": 108, "fairway": True,
        "green": {"center": [18, 132], "radius": [15, 10], "rotation": -0.25},
        "bunkers": [g([36, 126], [4, 3], 0.6), g([4, 146], [6, 3], -0.3)],
        "hazards": [dict(g([8, 88], [24, 17], -0.3), color=PURPLE, label="witch's pool")],
        "features": [{"pos": [52, 92], "label": "cauldron"}],
        "risk": [[0, 0], [18, 132]], "safe": [[0, 0], [38, 110], [24, 128]],
        "pads": [{"center": [40, 110], "radius": [11, 9], "rotation": 0.4}],
        "note": "A real par 3: no fairway, just a carry over the witch's pool to a wide shallow green; a "
                "short apron to the right is the bail-out."},
    3: {"par": 5, "turn": "left (loop round the graveyard)",
        "path": [[0, 0], [70, -6], [140, 4], [188, 42], [204, 112], [192, 182], [150, 226], [92, 242], [42, 236]],
        "widths": [24, 38, 48, 40, 34, 44, 46, 32, 26], "fairway_start": 38,
        "green": {"center": [40, 236], "radius": [14, 11], "rotation": 0.2},
        "bunkers": [g([150, -14], [4, 7], 0.2), g([218, 150], [4, 8], 0.1), g([30, 250], [5, 3], 0.4), g([54, 222], [4, 3], -0.3)],
        "hazards": [dict(g([100, 112], [52, 58]), color=GRAVE, label="graveyard")],
        "risk": [[0, 0], [22, 150], [40, 236]], "pads": [{"center": [22, 150], "radius": [17, 14], "rotation": 0.2}],
        "scale": 0.82,
        "note": "Keeps the loop, at the concept's length; landing areas widened to 48 yd at each corner, and the risky "
                "route up the left (a layup area past the graveyard) from the concept is built in."},
    4: {"par": 4, "turn": "right",
        "path": [[0, 0], [-2, 70], [-2, 150], [12, 196], [52, 216], [112, 222], [160, 226]],
        "widths": [24, 36, 46, 46, 38, 30, 26], "fairway_start": 36,
        "green": {"center": [160, 226], "radius": [13, 10], "rotation": 0.2},
        "bunkers": [g([142, 212], [5, 3], 0.4), g([176, 238], [4, 3], -0.5), g([-22, 172], [4, 8], 0.2)],
        "hazards": [dict(g([66, 116], [44, 56], 0.35), color=WEB, label="the web")],
        "risk": [[0, 0], [104, 206], [160, 226]],
        "note": "Same L as the concept, with a wide corner to land in."},
    5: {"par": 5, "turn": "right, then a little left (S)",
        "path": [[0, 0], [18, 90], [55, 168], [105, 228], [138, 296], [142, 368], [168, 436]],
        "widths": [24, 38, 48, 40, 46, 34, 26], "fairway_start": 40,
        "green": {"center": [168, 436], "radius": [14, 11], "rotation": -0.3},
        "bunkers": [g([150, 430], [5, 3], 0.6), g([184, 448], [4, 3], -0.4), g([126, 220], [4, 8], -0.6)],
        "hazards": [dict(g([52, 300], [40, 62], -0.3), color=CORN, label="corn maze")],
        "features": [{"pos": [190, 476], "label": "barn"}],
        "risk": [[0, 0], [18, 90], [55, 168], [96, 340], [168, 436]],
        "note": "The long diagonal from the concept, bending right; the corn maze sits beside the second "
                "landing area so going for it in two flies the corn."},
    6: {"par": 3, "turn": "none: tee to green",
        "path": [[0, 0], [-18, 158]], "widths": [26, 26], "fairway_start": 132,
        "green": {"center": [-18, 158], "radius": [14, 11], "rotation": 0.3},
        "bunkers": [g([-34, 166], [4, 3], 0.4), g([0, 170], [4, 3], -0.4)],
        "hazards": [stream([[-110, 40], [-70, 82], [-36, 104], [-2, 112], [30, 130], [64, 170]], 8) | {"label": "marsh"}],
        "risk": [[0, 0], [-18, 158]], "safe": [[0, 0], [28, 92], [8, 140]],
        "note": "A real par 3 over the ghostlight marsh, which winds across in front of the green "
                "(left this time, so it isn't hole 2 again)."},
    7: {"par": 4, "turn": "left",
        "path": [[0, 0], [5, 80], [10, 160], [-6, 220], [-52, 262], [-100, 278]],
        "widths": [24, 36, 46, 42, 32, 26], "fairway_start": 34,
        "green": {"center": [-102, 280], "radius": [14, 11], "rotation": 0.4},
        "bunkers": [g([-86, 294], [5, 3], -0.4), g([-118, 266], [4, 3], 0.6), g([28, 190], [4, 8], -0.2)],
        "hazards": [dict(g([-58, 176], [28, 42], 0.3), color=BLOOD, label="blood pond"),
                    dict(g([78, 170], [26, 80]), color=HEDGE, label="hedge maze")],
        "features": [{"pos": [-120, 324], "label": "mansion"}],
        "risk": [[0, 0], [-58, 182], [-102, 280]],
        "note": "Dogleg LEFT round the blood pond, which is now in the corner (in play), with the hedge "
                "maze lining the right."},
    8: {"par": 4, "turn": "straight, split fairway",
        "path": [[0, 0], [8, 90], [24, 170], [44, 240], [44, 310], [28, 372]],
        "widths": [24, 36, 44, 36, 34, 26], "fairway_start": 36,
        "extra_fairways": [[[[6, 110], [-28, 190], [-26, 280], [20, 360]], [30, 30, 30, 26]]],
        "green": {"center": [28, 374], "radius": [13, 10], "rotation": -0.2},
        "bunkers": [g([12, 384], [5, 3], 0.4), g([44, 360], [4, 3], -0.5), g([-8, 300], [4, 7], 0.1)],
        "hazards": [{"line": [[-140, 262], [-60, 238], [0, 222], [60, 206], [150, 184]], "width": 12,
                     "color": RAVINE, "label": "ravine"}],
        "features": [{"pos": [-90, 300], "label": "Horseman"}],
        "risk": [[0, 0], [-24, 190], [-20, 290], [28, 374]],
        "note": "Two fairways after the drive: the safe right one, and a shorter left one over the narrow "
                "end of the ravine past the Horseman."},
    9: {"par": 4, "turn": "left (horseshoe)",
        "path": [[0, 0], [52, -8], [112, 12], [152, 70], [158, 148], [130, 208], [76, 236], [24, 230]],
        "widths": [24, 34, 46, 40, 36, 42, 32, 26], "fairway_start": 36,
        "green": {"center": [22, 230], "radius": [14, 11], "rotation": 0.1},
        "bunkers": [g([8, 220], [4, 3], 0.5), g([36, 244], [5, 3], -0.3), g([176, 110], [4, 8], 0.1)],
        "hazards": [dict(g([72, 112], [44, 54]), color=PATCH, label="pumpkin patch")],
        "features": [{"pos": [10, 276], "label": "home"}],
        "risk": [[0, 0], [64, 130], [22, 230]], "scale": 0.73,
        "note": "The horseshoe round the pumpkin patch from the concept; the brave line flies the patch."},
}

NAMES = {1: "Pumpkin Patch", 2: "Witch's Hollow", 3: "Forgotten Cemetery", 4: "Spiderwood", 5: "Haunted Harvest",
         6: "Ghostlight Marsh", 7: "Vampire's Garden", 8: "Headless Trail", 9: "Midnight Homecoming"}
FILES = {1: "h01_pumpkin_patch.json", 2: "h02_witchs_hollow.json", 3: "h03_forgotten_cemetery.json",
         4: "h04_spiderwood.json", 5: "h05_haunted_harvest.json", 6: "h06_ghostlight_marsh.json",
         7: "h07_vampires_garden.json", 8: "h08_headless_trail.json", 9: "h09_midnight_homecoming.json"}

def scaled(p):
    k = p.get("scale", 1.0)
    if k == 1.0:
        return p
    q = dict(p)
    S2 = lambda pts: [[x * k, y * k] for x, y in pts]
    q["path"] = S2(p["path"])
    for key in ("risk", "safe"):
        if key in p:
            q[key] = S2(p[key])
    q["green"] = dict(p["green"], center=[p["green"]["center"][0] * k, p["green"]["center"][1] * k])
    q["bunkers"] = [dict(b, center=[b["center"][0] * k, b["center"][1] * k]) for b in p.get("bunkers", [])]
    q["pads"] = [dict(b, center=[b["center"][0] * k, b["center"][1] * k]) for b in p.get("pads", [])]
    q["hazards"] = [dict(h, center=[h["center"][0] * k, h["center"][1] * k], radius=[h["radius"][0] * k, h["radius"][1] * k])
                    if "center" in h else dict(h, line=S2(h["line"])) for h in p.get("hazards", [])]
    q["features"] = [dict(f, pos=[f["pos"][0] * k, f["pos"][1] * k]) for f in p.get("features", [])]
    return q



def main():
    global CONCEPT
    A = Image.open(os.path.join(GOLF, "art_src/redesign/08_Course_Layout_Concepts/Revised_Holes_2_4_6_9_Concepts_v1.png")).convert("RGB")
    B = Image.open(os.path.join(GOLF, "art_src/redesign/08_Course_Layout_Concepts/Revised_Holes_1_3_5_7_Concepts_v1.png")).convert("RGB")
    H8 = Image.open(os.path.join(GOLF, "art_src/concepts/hole_8.png")).convert("RGB")
    TL, TR, BL, BR = (22, 62, 620, 596), (636, 62, 1234, 596), (22, 612, 620, 1166), (636, 612, 1234, 1166)
    CONCEPT = {1: B.crop(TL), 3: B.crop(TR), 5: B.crop(BL), 7: B.crop(BR), 2: A.crop(TL), 4: A.crop(TR), 6: A.crop(BL),
               9: A.crop(BR), 8: H8.crop((20, 20, 1234, 1165))}

    os.makedirs(OUT, exist_ok=True)
    rows = {}
    for i in range(1, 10):
        now = current(FILES[i])
        p = scaled(PROPOSED[i])
        prop = dict(p)
        prop.setdefault("safe", p["path"])
        img_now = draw(now, "now%d" % i)
        img_new = draw(prop, "new%d" % i)
        gap, head, foot = 14, 46, 64
        row = Image.new("RGB", (3 * PX + 4 * gap, PX + head + foot), (23, 13, 36))
        d = ImageDraw.Draw(row)
        con = CONCEPT[i].resize((PX, int(PX * CONCEPT[i].height / CONCEPT[i].width))).crop((0, 0, PX, PX))
        row.paste(con, (gap, head))
        row.paste(img_now, (2 * gap + PX, head))
        row.paste(img_new, (3 * gap + 2 * PX, head))
        nl, pl = length(now["path"]) * YD, length(p["path"]) * YD
        d.text((gap, 10), "%d  %s" % (i, NAMES[i]), fill=(255, 196, 120), font=font(26))
        d.text((gap, head + PX + 6), "concept", fill=(205, 195, 225), font=font(17))
        d.text((2 * gap + PX, head + PX + 6), "now: par %d, %d yd" % (now["par"], nl), fill=(205, 195, 225), font=font(17))
        d.text((3 * gap + 2 * PX, head + PX + 6), "proposed: par %d, %d yd, bends %s" % (p["par"], pl, p["turn"]),
               fill=(255, 230, 160), font=font(17))
        words, line, y = p["note"].split(), "", head + PX + 30
        for w in words:
            if d.textlength(line + " " + w, font=font(15)) > 3 * PX:
                d.text((gap, y), line, fill=(225, 215, 240), font=font(15))
                line, y = w, y + 18
            else:
                line = (line + " " + w).strip()
        d.text((gap, y), line, fill=(225, 215, 240), font=font(15))
        rows[i] = row
    for n, group in enumerate([(1, 2, 3), (4, 5, 6), (7, 8, 9)]):
        h = sum(rows[i].height for i in group)
        sheet = Image.new("RGB", (rows[1].width, h + 40), (23, 13, 36))
        ImageDraw.Draw(sheet).text((14, 8), "Concept  |  as built now  |  proposed      (white dashes: safe line, yellow dots: risky line)",
                                   fill=(255, 214, 160), font=font(20))
        y = 40
        for i in group:
            sheet.paste(rows[i], (0, y))
            y += rows[i].height
        sheet.save(os.path.join(OUT, "plan_holes_%d-%d.png" % (group[0], group[-1])))
    print("ok")


if __name__ == "__main__":
    main()
