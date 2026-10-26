"""Revised hole plan, checked against the game's clubs and real-course sizes: each hole's concept, as built
now, and the proposal (irregular hazards at real sizes, the band where a good drive finishes, the risky
carries), with a side view of its ground from tee to green and the measured facts.
usage: python3 -I plan_holes2.py <golf dir> <out dir>"""
import json
import math
import os
import random
import sys

from PIL import Image, ImageDraw

sys_argv = list(sys.argv)
sys.argv = ["x"]
import plan_holes as P  # noqa: E402
import check_plan as C  # noqa: E402,F401  (club helpers)
GOLF, OUT = (sys_argv[1], sys_argv[2]) if len(sys_argv) > 2 else (None, None)
P.GOLF = GOLF

YD = 1.0936
PX = 470
SS = 2
DRIVE_CARRY, DRIVE_END = 205.0, 228.0
font = P.font


def organic(c, r, rot, seed, lobes=0.16, n=72):
    """An irregular outline round an ellipse: a couple of soft lobes and coves, never a clean oval."""
    rnd = random.Random(seed)
    a2, p2 = rnd.uniform(0.5, 1.0) * lobes, rnd.uniform(0, math.tau)
    a3, p3 = rnd.uniform(0.4, 0.9) * lobes, rnd.uniform(0, math.tau)
    a5, p5 = rnd.uniform(0.2, 0.5) * lobes, rnd.uniform(0, math.tau)
    rx, ry = r
    out = []
    for k in range(n):
        t = math.tau * k / n
        f = 1 + a2 * math.cos(2 * t + p2) + a3 * math.cos(3 * t + p3) + a5 * math.cos(5 * t + p5)
        x, y = rx * math.cos(t) * f, ry * math.sin(t) * f
        out.append((c[0] + x * math.cos(rot) - y * math.sin(rot), c[1] + x * math.sin(rot) + y * math.cos(rot)))
    return out


def bunker_parts(b, seed):
    """A bunker as real ones are drawn: a main body with a finger or two of sand off it."""
    rnd = random.Random(seed)
    parts = [organic(b["center"], b["radius"], b.get("rotation", 0.0), seed, 0.12)]
    rx, ry = b["radius"]
    rot = b.get("rotation", 0.0)
    for k in range(rnd.choice([1, 2])):
        s = rnd.choice([-1, 1]) * rnd.uniform(0.45, 0.75)
        cx = b["center"][0] + math.cos(rot) * rx * s
        cy = b["center"][1] + math.sin(rot) * rx * s
        off = rnd.choice([-1, 1]) * ry * 0.6
        cx += -math.sin(rot) * off
        cy += math.cos(rot) * off
        parts.append(organic([cx, cy], [rx * 0.42, ry * 0.75], rot + rnd.uniform(-0.6, 0.6), seed + 9 + k, 0.1))
    return parts


def g(c, r, rot=0.0, **kw):
    return dict({"center": c, "radius": r, "rotation": rot}, **kw)


POND, PURPLE, BLOOD, MARSH, WEB, CORN, PATCH, GRAVE, HEDGE, RAVINE = P.POND, P.PURPLE, P.BLOOD, P.MARSH, P.WEB, P.CORN, \
    P.PATCH, P.GRAVE, P.HEDGE, P.RAVINE

# Course metres: tee at the origin, y down the range, x to the right.
# Greenside bunkers ~20-26 yd x 8-10 yd, fairway bunkers ~30-38 yd x 12 yd (real sizes).
PLAN = {
    1: {"par": 4, "turn": "right (concept flipped)",
        "path": [[0, 0], [0, 90], [3, 175], [14, 214], [46, 244], [84, 258], [104, 262]],
        "widths": [26, 32, 40, 40, 34, 28, 24], "fairway_start": 40,
        "green": g([106, 263], [12, 10], 0.4),
        "bunkers": [g([-11, 211], [6, 16], 0.15), g([90, 276], [10, 4], 0.35), g([121, 249], [9, 4], -0.9)],
        "hazards": [g([54, 172], [26, 16], 0.2, color=POND, label="pond"),
                    g([-48, 112], [14, 26], 0.1, color=PATCH, label="pumpkin patch")],
        "pads": [{"center": [66, 216], "radius": [17, 12], "rotation": 0.5}],
        "risk": [[0, 0], [66, 216], [106, 263]],
        "elev": [[0, 8.0], [80, 6.0], [200, 2.5], [270, 4.0], [320, 5.0]],
        "note": "Elevated tee looking down to the pond in the corner; the drive finishes right at the corner. "
                "Cutting it carries the pond to a small landing past it."},
    2: {"par": 3, "turn": "none (tee to green)",
        "path": [[0, 0], [18, 132]], "widths": [24, 24], "fairway_start": 112,
        "green": g([18, 133], [15, 9], -0.25),
        "bunkers": [g([39, 127], [10, 4], 1.2), g([2, 146], [11, 4], -0.25)],
        "hazards": [g([8, 90], [26, 17], -0.3, color=PURPLE, label="witch's pool")],
        "pads": [{"center": [42, 108], "radius": [12, 9], "rotation": 0.5}],
        "risk": [[0, 0], [18, 133]], "safe": [[0, 0], [42, 108], [24, 128]],
        "elev": [[0, 11.0], [40, 9.0], [85, 3.2], [118, 4.0], [133, 4.4]], "green_raise": 1.2,
        "note": "Downhill into the hollow (plays about 8 yd shorter): carry the pool to a wide, shallow green; "
                "the apron right is the bail-out."},
    3: {"par": 5, "turn": "left (a long sweep round the graveyard)",
        "path": [[0, 0], [100, 4], [198, 26], [250, 78], [276, 150], [284, 230], [282, 280]],
        "widths": [24, 34, 40, 38, 40, 32, 24], "fairway_start": 38,
        "green": g([282, 282], [13, 10], 1.4),
        "bunkers": [g([211, 7], [16, 6], 0.25), g([301, 187], [6, 16], 0.05), g([266, 292], [4, 10], 0.1),
                    g([298, 270], [4, 9], -0.2)],
        "hazards": [g([124, 96], [54, 34], 0.55, color=GRAVE, label="graveyard")],
        "pads": [{"center": [150, 160], "radius": [18, 14], "rotation": 0.6}],
        "features": [{"pos": [322, 300], "label": "chapel"}],
        "risk": [[0, 0], [150, 160], [282, 282]],
        "elev": [[0, 2.0], [215, 5.0], [330, 9.0], [487, 14.0]],
        "note": "A long sweep left round the graveyard, climbing to the chapel: three shots. The brave drive "
                "flies the graveyard to a pad; from there a perfect 3 wood can reach in two."},
    4: {"par": 4, "turn": "right",
        "path": [[0, 0], [-2, 80], [-2, 170], [12, 212], [52, 232], [112, 238], [150, 240]],
        "widths": [24, 32, 40, 40, 34, 28, 24], "fairway_start": 36,
        "green": g([152, 241], [12, 10], 0.2),
        "bunkers": [g([-16, 200], [6, 16], 0.15), g([134, 228], [10, 4], 0.35), g([168, 254], [9, 4], -0.6)],
        "hazards": [g([66, 122], [42, 52], 0.35, color=WEB, label="the web")],
        "risk": [[0, 0], [104, 226], [152, 241]],
        "elev": [[0, 3.0], [200, 7.0], [357, 10.5]],
        "note": "The L from the concept with the corner where a drive finishes; flying the web's corner is a "
                "full carry."},
    5: {"par": 5, "turn": "right, then a little left (S)",
        "path": [[0, 0], [12, 100], [40, 196], [95, 246], [132, 306], [142, 372], [160, 418]],
        "widths": [24, 34, 42, 38, 42, 32, 24], "fairway_start": 40,
        "green": g([162, 420], [12, 10], -0.3),
        "bunkers": [g([144, 411], [10, 4], 0.9), g([180, 433], [9, 4], -0.4), g([44, 232], [6, 16], -0.8),
                    g([158, 331], [6, 15], 0.1)],
        "hazards": [g([88, 330], [22, 46], -0.3, color=CORN, label="corn maze")],
        "features": [{"pos": [186, 458], "label": "barn"}],
        "elev": [[0, 8.0], [100, 6.2], [200, 4.6], [270, 3.2], [360, 4.0], [462, 6.5]],
        "note": "Three shots down the long diagonal through the farm: a bend at the drive, then the corn "
                "maze all down the left of the second shot and the barn behind the green."},
    6: {"par": 3, "turn": "none (tee to green)",
        "path": [[0, 0], [-18, 158]], "widths": [24, 24], "fairway_start": 146, "green_raise": 1.0,
        "green": g([-18, 159], [10, 14], 0.1),
        "bunkers": [g([-36, 170], [10, 4], 0.6), g([2, 172], [9, 4], -0.5)],
        "hazards": [{"line": [[-120, 70], [-80, 104], [-40, 118], [-8, 124], [6, 129]], "width": 18,
                     "color": MARSH, "label": "marsh"}],
        "pads": [{"center": [12, 160], "radius": [10, 8], "rotation": 0.2}],
        "risk": [[0, 0], [-18, 159]], "safe": [[0, 0], [30, 126], [12, 158]],
        "elev": [[0, 7.0], [60, 4.0], [110, 2.2], [158, 2.6]],
        "note": "Downhill over the marsh, which crosses in front of the green from the left (hole 2's water is "
                "on the right); a long iron to a bail-out apron right."},
    7: {"par": 4, "turn": "left",
        "path": [[0, 0], [5, 80], [10, 160], [-6, 220], [-52, 262], [-100, 278]],
        "widths": [24, 32, 40, 38, 30, 24], "fairway_start": 34,
        "green": g([-102, 280], [13, 10], 0.4),
        "bunkers": [g([-86, 296], [10, 4], -0.4), g([-120, 264], [9, 4], 0.9), g([24, 195], [6, 16], -0.2)],
        "hazards": [g([-38, 180], [18, 26], 0.35, color=BLOOD, label="blood pond"),
                    g([80, 170], [24, 80], 0.0, color=HEDGE, label="hedge maze")],
        "features": [{"pos": [-120, 324], "label": "mansion"}],
        "risk": [[0, 0], [-30, 226], [-102, 280]],
        "elev": [[0, 3.0], [160, 4.0], [260, 6.5], [335, 9.0]],
        "note": "Uphill dogleg left to the mansion; the blood pond fills the corner, so cutting it is a near-"
                "full carry; the hedge maze lines the right."},
    8: {"par": 4, "turn": "straight, split fairway",
        "path": [[0, 0], [8, 90], [22, 175], [34, 240], [40, 300], [36, 382]],
        "widths": [24, 34, 42, 34, 32, 24], "fairway_start": 36,
        "extra_fairways": [[[[6, 110], [-26, 190], [-30, 270], [20, 372]], [28, 30, 28, 24]]],
        "green": g([36, 384], [11, 15], -0.1),
        "bunkers": [g([18, 392], [4, 10], 0.1), g([54, 376], [4, 10], -0.2), g([49, 202], [6, 15], 0.1)],
        "hazards": [{"line": [[-150, 322], [-60, 296], [0, 280], [60, 262], [160, 232]], "width": 22,
                     "color": RAVINE, "label": "ravine"}],
        "features": [{"pos": [-92, 326], "label": "Horseman"}],
        "risk": [[0, 0], [-24, 190], [-28, 270], [36, 384]],
        "elev": [[0, 9.0], [200, 6.7], [245, 6.1], [262, 5.2], [278, 3.5], [300, 6.0], [388, 10.0]], "fairway_gap": [258, 304],
        "note": "The long par 4. The ravine crosses beyond a drive's reach (~300 yd), so you lay up and carry it "
                "with a long iron to the biggest green; the left fairway is narrower, past the Horseman."},
    9: {"par": 4, "turn": "hard left (horseshoe)",
        "path": [[0, 0], [45, 65], [88, 128], [104, 182], [86, 226], [46, 246], [8, 242]],
        "widths": [24, 32, 40, 38, 32, 28, 24], "fairway_start": 34,
        "green": g([6, 243], [13, 10], 0.1),
        "bunkers": [g([-10, 232], [9, 4], 0.9), g([18, 258], [10, 4], -0.2), g([119, 152], [6, 16], 0.2)],
        "hazards": [g([28, 158], [24, 44], -0.2, color=PATCH, label="pumpkin patch")],
        "pads": [{"center": [16, 212], "radius": [12, 9], "rotation": 0.1}],
        "features": [{"pos": [-4, 284], "label": "home"}],
        "risk": [[0, 0], [16, 212], [6, 243]],
        "elev": [[0, 12.0], [120, 8.0], [210, 5.0], [342, 7.5]],
        "note": "From a high tee the safe drive goes right round the patch, then a short iron back left to "
                "the green by the house. The brave drive flies the patch to a landing just short of the green."},
}


# Trees: the dominant kind sets the hole's look (about 6 in 10, standing in groves), a second kind
# about 1 in 4, accents for the rest; the far woods follow the same mix with a conifer behind.
TREES = {
    1: ("tree_scarlet_maple", "tree_copper_oak", ["lantern_tree", "haunted_tree", "tree_golden_aspen"]),
    2: ("tree_witchwood_purple", "tree_bent_willow", ["haunted_tree", "tree_hollow_sentinel", "tree_raven_perch"]),
    3: ("tree_silver_snag", "tree_ancient_yew", ["tree_raven_perch", "tree_hollow_sentinel", "dead_tree"]),
    4: ("tree_dark_blue_spruce", "tree_moonlit_pine", ["tree_ghost_birch", "dead_tree", "tree_hollow_sentinel"]),
    5: ("tree_harvest_pear", "apple_tree", ["tree_copper_oak", "maple_orange", "tree_golden_aspen"]),
    6: ("tree_twisted_cypress", "tree_bent_willow", ["dead_tree", "tree_raven_perch", "tree_ghost_birch"]),
    7: ("tree_crooked_plum", "tree_formal_yew", ["tree_ancient_yew", "tree_hollow_sentinel", "tree_scarlet_maple"]),
    8: ("tree_lightning_oak", "tree_windbent_fir", ["dead_tree", "tree_raven_perch", "tree_silver_snag"]),
    9: ("tree_golden_aspen", "maple_orange", ["lantern_tree", "birch", "tree_copper_oak"]),
}
# Undergrowth under each hole's trees and along its rough (the new ground plants); one landmark tree.
UNDER = {1: ["ground_brambles", "ground_ferns"], 2: ["ground_heather", "ground_ferns"], 3: ["ground_ferns", "ground_brambles"],
         4: ["ground_ferns"], 5: ["ground_brambles", "ground_heather"], 6: ["ground_marsh_reeds", "ground_ferns"],
         7: ["ground_brambles"], 8: ["ground_ferns", "ground_brambles"], 9: ["ground_heather", "ground_brambles"]}
LANDMARK = {9: "tree_homecoming_swing_oak"}
CARDS = None
_COL = {}


def tree_colour(name):
    """The average colour of a tree card's crown (its top two thirds), for the map."""
    if name not in _COL:
        im = Image.open(os.path.join(CARDS, name + ".png")).convert("RGBA")
        im = im.crop((0, 0, im.width, im.height * 2 // 3)).resize((40, 40))
        px = [p[:3] for p in im.get_flattened_data() if p[3] > 200]
        _COL[name] = tuple(int(sum(c[k] for c in px) / len(px) * 0.8) for k in range(3))
    return _COL[name]


def now_trees(i):
    th = json.load(open(os.path.join(GOLF, "courses", "holes", P.FILES[i])))["theme"]
    return th["trees_near"]


def grove_pick(i, x, y, rnd):
    """Which tree stands at (x, y) on the proposed hole: groves (about 25 m across) of one kind."""
    dom, sec, acc = TREES[i]
    gx, gy = math.floor(x / 25.0), math.floor(y / 25.0)
    r = random.Random(gx * 7919 + gy * 104729 + i).random()
    kind = dom if r < 0.6 else (sec if r < 0.85 else acc[int(r * 1000) % len(acc)])
    return kind if rnd.random() < 0.85 else dom


def carry_over(line, hazard):
    """How far along the risky line (from its start) you must fly to clear the hazard."""
    best, first = None, None
    s0 = 0.0
    for a, b in zip(line, line[1:]):
        L = math.dist(a, b)
        for k in range(int(L) + 1):
            x = a[0] + (b[0] - a[0]) * k / L
            y = a[1] + (b[1] - a[1]) * k / L
            if "center" in hazard:
                cx, cy = hazard["center"]
                rx, ry = hazard["radius"]
                rot = hazard.get("rotation", 0)
                dx, dy = x - cx, y - cy
                u = (dx * math.cos(rot) + dy * math.sin(rot)) / rx
                v = (-dx * math.sin(rot) + dy * math.cos(rot)) / ry
                inside = u * u + v * v <= 1
            else:
                inside = any(_seg_dist((x, y), p, q) <= hazard["width"] / 2 for p, q in zip(hazard["line"], hazard["line"][1:]))
            if inside:
                best = s0 + k
                first = first if first is not None else s0 + k
            elif best is not None:
                return first, best
        s0 += L
    return (first, best) if best is not None else None


def _seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
    return math.dist(p, (ax + dx * t, ay + dy * t))


def facts(p):
    L = P.length(p["path"])
    out = ["par %d, %d yd" % (p["par"], L * YD)]
    if p["par"] == 3:
        out.append("%s off the tee" % C.club_for(L))
    else:
        c = C.corner(p["path"])
        if c:
            out.append("bend at %d yd" % (c * YD))
        out.append("drive ends ~%d yd" % (DRIVE_END * YD))
        left = L - DRIVE_END
        if p["par"] == 4:
            out.append("then %d yd (%s)" % (left * YD, C.club_for(left)))
        else:
            out.append("then %d yd: two more shots" % (left * YD))
    for h in p.get("hazards", []):
        if p.get("risk"):
            cv = carry_over(p["risk"], h)
            if cv:
                out.append("%s on the risky line %d-%d yd" % (h.get("label", "hazard"), cv[0] * YD, cv[1] * YD))
    if p["par"] > 3:
        out.append("tee to green direct %d yd" % (math.dist(p["path"][0], p["green"]["center"]) * YD))
    return ", ".join(out)


def draw(spec, title, proposal, hole=None):
    pts = list(spec["path"])
    for h in spec.get("hazards", []):
        pts += P.ellipse_pts(h["center"], h["radius"], h.get("rotation", 0)) if "center" in h else h["line"]
    for f in spec.get("features", []):
        pts.append(f["pos"])
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    span = max(max(xs) - min(xs), max(ys) - min(ys)) + 90
    S = PX * SS
    k = S / span

    def Pt(x, y):
        return ((x - cx) * k + S / 2, S / 2 - (y - cy) * k)

    img = Image.new("RGB", (S, S), (22, 12, 32))
    d = ImageDraw.Draw(img, "RGBA")
    rnd = random.Random(hash(title) & 0xffff)
    pool = now_trees(hole) if hole and not proposal else None
    for _ in range(int(S * S / 700)):
        x, y = rnd.uniform(0, S), rnd.uniform(0, S)
        r = rnd.uniform(5, 12) * SS
        if hole is None:
            col = rnd.choice([(48, 26, 70), (60, 30, 82), (40, 22, 58), (90, 40, 30), (70, 34, 52)])
        else:
            wx, wy = (x - S / 2) / k + cx, (S / 2 - y) / k + cy
            col = tree_colour(grove_pick(hole, wx, wy, rnd) if proposal else rnd.choice(pool))
        d.ellipse([x - r, y - r, x + r, y + r], fill=col)
    rough = spec.get("rough", 13)
    fairways = [(spec["path"], spec["widths"], spec.get("fairway_start", 34), True)] + \
        [(fp, fw, 0, False) for fp, fw in spec.get("extra_fairways", [])]
    for path, widths, start, main in fairways:
        dist, prev = 0.0, None
        for x, y, w in P.densify(path, widths):
            if prev:
                dist += math.dist(prev, (x, y))
            prev = (x, y)
            if main and proposal and spec["par"] == 3 and 14 < dist < start - 12:
                continue
            r = (w / 2 + rough) * k
            X, Y = Pt(x, y)
            d.ellipse([X - r, Y - r, X + r, Y + r], fill=(46, 72, 34))
    for path, widths, start, main in fairways:
        dist, prev = 0.0, None
        for x, y, w in P.densify(path, widths):
            if prev:
                dist += math.dist(prev, (x, y))
            prev = (x, y)
            if main and dist < start:
                continue
            # an organic fairway edge
            w2 = w * (1 + 0.07 * math.sin(dist / 23.0 + len(title)) + 0.04 * math.sin(dist / 9.0))
            r = w2 / 2 * k
            X, Y = Pt(x, y)
            d.ellipse([X - r, Y - r, X + r, Y + r], fill=(88, 146, 56))
    for n, pad in enumerate(spec.get("pads", [])):
        if proposal:
            d.polygon([Pt(*q) for q in organic(pad["center"], [pad["radius"][0] + 9, pad["radius"][1] + 9],
                                                pad.get("rotation", 0), n + 77)], fill=(46, 72, 34))
        d.polygon([Pt(*q) for q in organic(pad["center"], pad["radius"], pad.get("rotation", 0), n + 77)] if proposal
                  else [Pt(*q) for q in P.ellipse_pts(pad["center"], pad["radius"], pad.get("rotation", 0))], fill=(88, 146, 56))
    for n, h in enumerate(spec.get("hazards", [])):
        col = tuple(h["color"])
        if "line" in h:
            line = [Pt(*q) for q in h["line"]]
            wpx = int(h.get("width", 10) * k)
            for j in range(len(line) - 1):           # a stream that swells and narrows
                a, b = line[j], line[j + 1]
                for t in range(0, 21):
                    u = t / 20
                    X = a[0] + (b[0] - a[0]) * u
                    Y = a[1] + (b[1] - a[1]) * u
                    rr = wpx / 2 * (0.75 + 0.35 * math.sin(j * 2.1 + u * 3.0)) if proposal else wpx / 2
                    d.ellipse([X - rr, Y - rr, X + rr, Y + rr], fill=col)
        else:
            shape = organic(h["center"], h["radius"], h.get("rotation", 0), n * 31 + len(title), 0.18) if proposal \
                else P.ellipse_pts(h["center"], h["radius"], h.get("rotation", 0))
            d.polygon([Pt(*q) for q in shape], fill=col)
    gr = spec["green"]
    d.polygon([Pt(*q) for q in organic(gr["center"], [gr["radius"][0] + 3, gr["radius"][1] + 3], gr.get("rotation", 0), 5, 0.1)], fill=(100, 165, 66))
    d.polygon([Pt(*q) for q in organic(gr["center"], gr["radius"], gr.get("rotation", 0), 5, 0.1)], fill=(132, 205, 90))
    for n, b in enumerate(spec.get("bunkers", [])):
        parts = bunker_parts(b, n * 13 + len(title)) if proposal else [P.ellipse_pts(b["center"], b["radius"], b.get("rotation", 0))]
        for part in parts:
            d.polygon([Pt(*q) for q in part], fill=(226, 205, 150))
    tx, ty = spec["path"][0]
    if proposal and spec["par"] > 3:
        # where a good drive finishes: 224-249 yd from the tee
        X, Y = Pt(tx, ty)
        for rad in (DRIVE_CARRY, DRIVE_END):
            R = rad * k
            d.ellipse([X - R, Y - R, X + R, Y + R], outline=(255, 255, 255, 120), width=SS * 2)
    X, Y = Pt(tx, ty)
    d.rectangle([X - 5 * k, Y - 6 * k, X + 5 * k, Y + 6 * k], fill=(150, 210, 120), outline=(255, 255, 255), width=SS * 2)
    pin = spec.get("pin", gr["center"])
    X, Y = Pt(*pin)
    d.line([X, Y, X, Y - 26 * SS], fill=(240, 240, 240), width=SS * 2)
    d.polygon([(X, Y - 26 * SS), (X + 14 * SS, Y - 21 * SS), (X, Y - 16 * SS)], fill=(230, 40, 40))

    def dashed(line, col, dash, gap, w):
        for a, b in zip(line, line[1:]):
            A, B = Pt(*a), Pt(*b)
            L = math.dist(A, B)
            t = 0.0
            while t < L:
                t1 = min(L, t + dash)
                d.line([A[0] + (B[0] - A[0]) * t / L, A[1] + (B[1] - A[1]) * t / L,
                        A[0] + (B[0] - A[0]) * t1 / L, A[1] + (B[1] - A[1]) * t1 / L], fill=col, width=w)
                t = t1 + gap
    dashed(spec.get("safe", spec["path"]), (255, 255, 255), 14 * SS, 9 * SS, 3 * SS)
    if spec.get("risk"):
        dashed(spec["risk"], (255, 222, 60), 5 * SS, 6 * SS, 3 * SS)
    F = font(13 * SS)
    for h in spec.get("hazards", []) + spec.get("features", []):
        if h.get("label"):
            c = h.get("pos") or h.get("center") or h["line"][len(h["line"]) // 2]
            X, Y = Pt(*c)
            tw = d.textlength(h["label"], font=F)
            d.text((X - tw / 2 + SS, Y - 7 * SS + SS), h["label"], fill=(0, 0, 0), font=F)
            d.text((X - tw / 2, Y - 7 * SS), h["label"], fill=(255, 245, 230), font=F)
    L = 100 / YD * k
    d.line([20 * SS, S - 20 * SS, 20 * SS + L, S - 20 * SS], fill=(255, 255, 255), width=SS * 2)
    d.text((20 * SS, S - 40 * SS), "100 yd", fill=(255, 255, 255), font=font(12 * SS))
    return img.resize((PX, PX), Image.LANCZOS)


def profile(p, w, h):
    """The ground from tee to green, side on: height (m) against yards along the hole."""
    img = Image.new("RGB", (w, h), (30, 18, 44))
    d = ImageDraw.Draw(img)
    L = P.length(p["path"])
    el = p["elev"]
    lo = min(e[1] for e in el) - 2
    hi = max(e[1] for e in el) + 2
    lo, hi = min(lo, 0), max(hi, lo + 14)

    def XY(s, z):
        return (36 + (w - 50) * s / L, h - 18 - (h - 34) * (z - lo) / (hi - lo))
    pts = [XY(s, z) for s, z in el]
    d.polygon(pts + [XY(el[-1][0], lo), XY(0, lo)], fill=(52, 82, 40))
    d.line(pts, fill=(140, 210, 90), width=3)
    f = font(12)
    d.text((4, 2), "ground, tee to green (exaggerated)", fill=(200, 190, 220), font=f)
    d.text((4, pts[0][1] - 16), "tee %dm" % el[0][1], fill=(255, 235, 200), font=f)
    d.text((w - 76, pts[-1][1] - 16), "green %dm" % el[-1][1], fill=(255, 235, 200), font=f)
    grade = (el[-1][1] - el[0][1]) / L * 100
    d.text((w // 2 - 60, h - 16), "%d yd, %s %.1f%% overall" % (L * YD, "up" if grade > 0 else "down", abs(grade)),
           fill=(200, 190, 220), font=f)
    return img


def main():
    global CARDS
    CARDS = os.path.join(GOLF, "game", "assets", "cards")
    P.main.__globals__["GOLF"] = GOLF
    A = Image.open(os.path.join(GOLF, "art_src/redesign/08_Course_Layout_Concepts/Revised_Holes_2_4_6_9_Concepts_v1.png")).convert("RGB")
    B = Image.open(os.path.join(GOLF, "art_src/redesign/08_Course_Layout_Concepts/Revised_Holes_1_3_5_7_Concepts_v1.png")).convert("RGB")
    H8 = Image.open(os.path.join(GOLF, "art_src/concepts/hole_8.png")).convert("RGB")
    TL, TR, BL, BR = (22, 62, 620, 596), (636, 62, 1234, 596), (22, 612, 620, 1166), (636, 612, 1234, 1166)
    concept = {1: B.crop(TL), 3: B.crop(TR), 5: B.crop(BL), 7: B.crop(BR), 2: A.crop(TL), 4: A.crop(TR), 6: A.crop(BL),
               9: A.crop(BR), 8: H8.crop((20, 20, 1234, 1165))}
    os.makedirs(OUT, exist_ok=True)
    rows = {}
    for i in range(1, 10):
        now = P.current(P.FILES[i])
        p = PLAN[i]
        img_now = draw(now, "now%d" % i, False, i)
        img_new = draw(p, "new%d" % i, True, i)
        gap, head, prof_h, foot = 14, 46, 110, 146
        row = Image.new("RGB", (3 * PX + 4 * gap, PX + head + prof_h + foot), (23, 13, 36))
        d = ImageDraw.Draw(row)
        con = concept[i].resize((PX, int(PX * concept[i].height / concept[i].width))).crop((0, 0, PX, PX))
        row.paste(con, (gap, head))
        row.paste(img_now, (2 * gap + PX, head))
        row.paste(img_new, (3 * gap + 2 * PX, head))
        row.paste(profile(p, PX, prof_h - 8), (3 * gap + 2 * PX, head + PX + 6))
        d.text((gap, 10), "%d  %s" % (i, P.NAMES[i]), fill=(255, 196, 120), font=font(26))
        d.text((gap, head + PX + 8), "concept", fill=(205, 195, 225), font=font(17))
        d.text((2 * gap + PX, head + PX + 8), "now: par %d, %d yd" % (now["par"], P.length(now["path"]) * YD),
               fill=(205, 195, 225), font=font(17))
        dom, sec, acc = TREES[i]
        x = gap
        d.text((x, head + PX + 34), "proposed trees:", fill=(205, 195, 225), font=font(15))
        x += 132
        items = [(dom, 74, "mostly"), (sec, 58, "some")] + [(a, 44, "") for a in acc]
        items += [(u, 34, "under:" if n == 0 else "") for n, u in enumerate(UNDER[i])]
        if i in LANDMARK:
            items.append((LANDMARK[i], 60, "by the house:"))
        base = head + PX + prof_h
        for n, (name, h, tag) in enumerate(items):
            if tag == "under:":                      # undergrowth (and the landmark) on a line of their own
                x, base = gap + 132, base + 46
            im = Image.open(os.path.join(CARDS, name + ".png")).convert("RGBA")
            im.thumbnail((h, h))
            row.paste(im, (x, base - im.height - 2), im)
            label = name.replace("tree_", "").replace("ground_", "").replace("_", " ")
            f = font(13 if n < 2 else 11)
            d.text((x + im.width + 4, base - 34), (tag + " " if tag else "") + label,
                   fill=(255, 225, 170) if n < 2 else (190, 180, 210), font=f)
            x += im.width + 8 + int(d.textlength((tag + " " if tag else "") + label, font=f))
        y = head + PX + prof_h + 50
        for text, col, f in [("proposed: " + facts(p) + "; bends " + p["turn"], (255, 230, 160), font(16)),
                             (p["note"], (225, 215, 240), font(15))]:
            line = ""
            for w_ in text.split():
                if d.textlength(line + " " + w_, font=f) > 3 * PX + 2 * gap:
                    d.text((gap, y), line, fill=col, font=f)
                    line, y = w_, y + 19
                else:
                    line = (line + " " + w_).strip()
            d.text((gap, y), line, fill=col, font=f)
            y += 24
        rows[i] = row
    for group in [(1, 2, 3), (4, 5, 6), (7, 8, 9)]:
        h = sum(rows[i].height for i in group)
        sheet = Image.new("RGB", (rows[1].width, h + 40), (23, 13, 36))
        ImageDraw.Draw(sheet).text((14, 8), "Concept  |  as built now  |  proposed v2   (white dashes: safe line; yellow dots: "
                                   "risky line; white rings: where a good drive finishes, 224-249 yd)",
                                   fill=(255, 214, 160), font=font(18))
        y = 40
        for i in group:
            sheet.paste(rows[i], (0, y))
            y += rows[i].height
        sheet.save(os.path.join(OUT, "plan_v2_holes_%d-%d.png" % (group[0], group[-1])))
    for i in range(1, 10):
        print(i, facts(PLAN[i]))


if __name__ == "__main__":
    main()


def clashes():
    """Hazards that reach into the fairway or the green (sampled outline against the fairway's centre line)."""
    for i, p in PLAN.items():
        for h in p.get("hazards", []) + [dict(b, label="bunker") for b in p.get("bunkers", [])]:
            if "center" not in h:
                continue
            worst = 1e9
            for q in P.ellipse_pts(h["center"], h["radius"], h.get("rotation", 0)):
                for x, y, w in P.densify(p["path"], p["widths"], 4):
                    worst = min(worst, math.dist(q, (x, y)) - w / 2)
            if h.get("label") != "bunker" and worst < 2:
                print("  hole %d: %s reaches %.0f m into the fairway" % (i, h["label"], -worst))
            if h.get("label") == "bunker" and worst < -8:
                print("  hole %d: bunker at %s sits %.0f m inside the fairway" % (i, h["center"], -worst))


if __name__ == "__main__":
    clashes()
