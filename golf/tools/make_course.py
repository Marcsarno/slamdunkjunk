"""Write the nine hole layouts (courses/holes/h0N_*.json) from the course plan (plan_holes2.PLAN), so the
plan sheets and the built holes come from one source. Replaces make_holes_4_9.py and the hand-edited
holes 1-3 (Marc's redesign of 26 Oct: wider landing areas, real par 3s, varied bends, real-size hazards,
a dominant tree per hole).

usage: python3 -I make_course.py <golf/courses/holes>

Each hole keeps what the old layout carried that isn't the course's shape: its name, seed, theme (sky,
fog, lights, water colours), wind, lantern and tree spacing, tee pumpkins, cart path settings. The plan
is drawn with the tee at the origin and y down the range; every hole is turned so its tee shot runs up
+y as the builder and the game expect (the tee box, its drainage, the tee pumpkins and hole 7's gate
pillars all assume it). Hole 1 is the concept mirrored, so its moon and key light are mirrored too.
"""
import contextlib
import copy
import io
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(HERE)
_argv = sys.argv
sys.argv = ["x"]
with contextlib.redirect_stdout(io.StringIO()):
    import plan_holes2 as Q       # noqa: E402  (the plan: PLAN, TREES, UNDER, LANDMARK)
sys.argv = _argv

OUT = sys.argv[1]
WATERY = {Q.POND, Q.PURPLE, Q.BLOOD}
TEE_PUMPKINS = [{"center": [4.9, 3.4], "carved": 2, "plain": 1, "radius": 1.1},
                {"center": [-5.2, 6.2], "carved": 1, "plain": 2, "radius": 1.0}]
FILES = {1: "h01_pumpkin_patch", 2: "h02_witchs_hollow", 3: "h03_forgotten_cemetery", 4: "h04_spiderwood",
         5: "h05_haunted_harvest", 6: "h06_ghostlight_marsh", 7: "h07_vampires_garden", 8: "h08_headless_trail",
         9: "h09_midnight_homecoming"}
# lobes ([a2, phase2, a3, phase3, a5, phase5]) for each irregular area, by its index in the hole: the
# rim swells and tucks in 10-20%, never a clean oval
LOBES = [[0.12, 0.6, 0.09, 2.1, 0.04, 0.3], [0.1, 2.4, 0.11, 0.9, 0.05, 1.7], [0.14, 1.3, 0.07, 2.8, 0.04, 0.8],
         [0.09, 3.0, 0.1, 1.6, 0.05, 2.4]]


def ravine(points, half_width=5.0, depth=4.2):
    """A rocky ravine (or a marsh channel, shallow) along a polyline: one narrow water piece per segment
    (as make_holes_4_9.ravine)."""
    out = []
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy)
        out.append({"center": [round((x0 + x1) / 2, 2), round((y0 + y1) / 2, 2)],
                    "radius": [round(ln / 2 + 4.0, 2), half_width],
                    "rotation": round(math.atan2(dy, dx), 4), "level_offset": -depth})
    return out


def ell(c, r, rot=0.0, **kw):
    return dict({"center": list(c), "radius": list(r), "rotation": rot}, **kw)


def grown(e, by, **kw):
    """The same area grown by `by` metres all round (a zone round a hazard, say)."""
    return dict(ell(e["center"], [e["radius"][0] + by, e["radius"][1] + by], e.get("rotation", 0.0)), **kw)


def ring(e, out=3.0, n=14):
    """Fence posts round an area, a few metres outside it."""
    pts = []
    for k in range(n):
        a = math.tau * k / n
        u, v = math.cos(a) * (e["radius"][0] + out), math.sin(a) * (e["radius"][1] + out)
        r = e.get("rotation", 0.0)
        pts.append([round(e["center"][0] + u * math.cos(r) - v * math.sin(r), 1),
                    round(e["center"][1] + u * math.sin(r) + v * math.cos(r), 1)])
    return pts + [pts[0]]


def patch_pumpkins(e, step=9.0):
    """Pumpkin clusters across a patch, in loose rows."""
    out, k = [], 0
    rx, ry = e["radius"]
    r = e.get("rotation", 0.0)
    v = -ry + step * 0.6
    while v < ry:
        u = -rx + step * 0.6 + (step * 0.5 if k % 2 else 0)
        while u < rx:
            if (u / rx) ** 2 + (v / ry) ** 2 < 0.8:
                out.append({"center": [round(e["center"][0] + u * math.cos(r) - v * math.sin(r), 1),
                                       round(e["center"][1] + u * math.sin(r) + v * math.cos(r), 1)],
                            "carved": 1 + (k + int(u)) % 2, "plain": 2, "radius": 2.2})
            u += step
        v += step * 0.85
        k += 1
    return out


def maze(x0, x1, y0, y1):
    """Hedge-maze walls in a rectangle: the outer wall with a way in, and staggered inner walls."""
    w = [{"points": [[x0, y0], [x0, y0 + (y1 - y0) * 0.45]]}, {"points": [[x0, y0 + (y1 - y0) * 0.55], [x0, y1]]},
         {"points": [[x0, y1], [x1, y1]]}, {"points": [[x1, y1], [x1, y0]]},
         {"points": [[x1, y0], [x0 + (x1 - x0) * 0.6, y0]]}, {"points": [[x0 + (x1 - x0) * 0.4, y0], [x0, y0]]}]
    n = 5
    for k in range(1, n):
        y = y0 + (y1 - y0) * k / n
        if k % 2:
            w.append({"points": [[x0, y], [x0 + (x1 - x0) * 0.72, y]]})
        else:
            w.append({"points": [[x0 + (x1 - x0) * 0.28, y], [x1, y]]})
    return [{"points": [[round(a, 1), round(b, 1)] for a, b in h["points"]]} for h in w]


def pads_along(line, widths, skip=None):
    """A second fairway (a split hole's other route) as a chain of landing pads along a polyline."""
    out = []
    for (a, b), w in zip(zip(line, line[1:]), widths):
        L = math.dist(a, b)
        out.append(ell([(a[0] + b[0]) / 2, (a[1] + b[1]) / 2], [L / 2 + 6.0, w / 2], math.atan2(b[1] - a[1], b[0] - a[0])))
    return out


# What each hole adds to the plan: its water, open zones, props, landmarks, cart path side, pin.
def extras(i, p):
    hz = {h.get("label"): h for h in p["hazards"]}
    e = {"water": [], "zones": [], "pads": [ell(q["center"], q["radius"], q.get("rotation", 0.0)) for q in p.get("pads", [])],
         # (a par 3's bail-out pad stands in a little open ground of its own, level, no bank or woods)
         "graveyards": [], "pumpkin_clusters": copy.deepcopy(TEE_PUMPKINS), "fences": [], "features": [],
         "patches": [], "webs": [], "web_art": [], "cornfields": [], "hedges": []}

    if p["par"] == 3:
        e["zones"] += [grown(q, 13, surface="rough") for q in e["pads"]]

    def water(h, k, **kw):
        w = ell(h["center"], h["radius"], h["rotation"], level_offset=-0.6, lobes=LOBES[k % 4], **kw)
        e["water"].append(w)
        e["zones"].append(grown(h, 8, surface="rough", lobes=LOBES[k % 4]))

    if i == 1:
        water(hz["pond"], 0)
        pt = ell(hz["pumpkin patch"]["center"], hz["pumpkin patch"]["radius"], hz["pumpkin patch"]["rotation"])
        e["zones"].append(grown(pt, 4, surface="deep_rough"))
        e["patches"].append(dict(pt, kind="pumpkins"))
        e["fences"].append({"points": ring(pt)})
        e["pumpkin_clusters"] += patch_pumpkins(pt)
        e["graveyards"] += [{"center": [-34, 24], "radius": 6, "count": 7, "fence": True},
                            {"center": [150, 236], "radius": 7, "count": 8, "fence": True}]
        e["cart"] = {"side": -1, "offset": 6.0}
        e["pin"] = [-3, 2]
    elif i == 2:
        water(hz["witch's pool"], 1)
        e["zones"].append(ell([10, 58], [24, 46], 0.1, surface="deep_rough"))          # the carry
        e["features"].append({"image": "light_witchs_cauldron", "pos": [-34, 98], "scale": 3.6})
        e["pumpkin_clusters"].append({"center": [-30, 112], "carved": 2, "plain": 2})
        e["graveyards"].append({"center": [-40, 40], "radius": 5, "count": 5, "fence": False})
        e["cart"] = {"side": 1, "offset": 6.0}
        e["pin"] = [3, -1]
    elif i == 3:
        gy = hz["graveyard"]
        ga = ell(gy["center"], gy["radius"], gy["rotation"])
        e["zones"].append(grown(ga, 6, surface="deep_rough", lobes=LOBES[2]))
        e["patches"].append(dict(ga, kind="graves"))
        ax, ay = math.cos(gy["rotation"]), math.sin(gy["rotation"])
        for s in (-1, 1):                     # two walled plots fill the long graveyard
            e["graveyards"].append({"center": [round(gy["center"][0] + s * ax * 24, 1), round(gy["center"][1] + s * ay * 24, 1)],
                                    "radius": 28, "count": 44, "fence": True})
        e["graveyards"].append({"center": [318, 312], "radius": 8, "count": 9, "fence": True})   # by the chapel's spot
        e["features"].append({"image": "light_grave_candles", "pos": [312, 300], "scale": 2.0})
        e["pumpkin_clusters"].append({"center": [150, 132], "carved": 2, "plain": 1})
        e["cart"] = {"side": 1, "offset": 6.0}
        e["pin"] = [-2, 3]
    elif i == 4:
        wb = hz["the web"]
        main = ell(wb["center"], wb["radius"], wb["rotation"])
        e["webs"] = [main, ell([44, 52], [12, 12], -0.4), ell([104, 150], [18, 13], 0.6)]
        e["web_art"] = [grown(main, 6), ell([44, 52], [15, 15], 2.1), ell([104, 150], [22, 17], -1.2)]
        e["zones"].append(grown(main, 8, surface="deep_rough"))
        e["graveyards"].append({"center": [-46, 120], "radius": 6, "count": 6, "fence": False})
        e["cart"] = {"side": -1, "offset": 6.0}
        e["pin"] = [3, 1]
    elif i == 5:
        cm = hz["corn maze"]
        e["cornfields"] = [ell(cm["center"], cm["radius"], cm["rotation"], gap=4.2)]
        e["zones"].append(grown(cm, 8, surface="deep_rough"))
        e["features"].append({"model": "barn", "pos": [186, 458], "face": [162, 420], "clear": 18})
        e["pumpkin_clusters"] += [{"center": [-14, 40], "carved": 2, "plain": 3}, {"center": [70, 224], "carved": 1, "plain": 3},
                                  {"center": [176, 380], "carved": 2, "plain": 2}, {"center": [112, 296], "carved": 1, "plain": 3}]
        e["graveyards"].append({"center": [-40, 150], "radius": 6, "count": 6, "fence": True})
        e["cart"] = {"side": 1, "offset": 7.0}
        e["pin"] = [2, 3]
    elif i == 6:
        mh = hz["marsh"]
        e["water"] += ravine(mh["line"], half_width=mh["width"] / 2, depth=0.6)
        e["zones"] += [ell([-6, 70], [26, 58], -0.1, surface="deep_rough"),            # the carry
                       ell([-50, 110], [56, 22], 0.4, surface="rough", lobes=LOBES[3])]  # the marsh's banks
        e["graveyards"].append({"center": [-60, 40], "radius": 5, "count": 5, "fence": False})
        e["cart"] = {"side": 1, "offset": 6.0}
        e["pin"] = [1, 4]
    elif i == 7:
        water(hz["blood pond"], 2)
        e["hedges"] = maze(58, 104, 92, 250)
        e["features"] += [{"model": "mansion", "pos": [-124, 330], "face": [-102, 280], "clear": 20},
                          {"model": "pillar", "pos": [-10, 7], "clear": 2}, {"model": "pillar", "pos": [10, 7], "clear": 2},
                          {"image": "statue_gargoyle", "pos": [-10, 7], "scale": 1.3, "lift": 3.35, "clear": 2},
                          {"image": "statue_gargoyle", "pos": [10, 7], "scale": 1.3, "lift": 3.35, "clear": 2}]
        e["graveyards"].append({"center": [-150, 240], "radius": 6, "count": 7, "fence": True})
        e["cart"] = {"side": 1, "offset": 6.0}
        e["pin"] = [-3, 2]
    elif i == 8:
        rv = hz["ravine"]
        e["water"] += ravine(rv["line"], half_width=5.0, depth=4.2)
        e["carry"] = list(p["fairway_gap"])
        # the left route: a narrower fairway past the Horseman, broken by the ravine like the main one
        line, widths = p["extra_fairways"][0]
        e["pads"] += pads_along([[6, 110], [-26, 190], [-30, 254]], widths[:2]) + pads_along([[-20, 316], [20, 372]], widths[2:3])
        e["features"].append({"image": "statue_horseman", "pos": [-66, 318], "scale": 1.4, "clear": 9})
        e["zones"].append(ell([-6, 330], [100, 26], -0.25, surface="rough"))           # the far bank
        # the ground between the two routes stays open (no framing bank rising between them)
        e["zones"].append(ell([-10, 190], [92, 34], math.pi / 2 + 0.05, surface="rough"))
        e["zones"] += [grown(q, 10, surface="rough") for q in e["pads"]]
        e["graveyards"].append({"center": [86, 330], "radius": 6, "count": 6, "fence": False})
        e["cart"] = {"side": -1, "offset": 6.0}
        e["pin"] = [-2, 4]
    elif i == 9:
        pp = hz["pumpkin patch"]
        pt = ell(pp["center"], pp["radius"], pp["rotation"])
        e["zones"].append(grown(pt, 6, surface="deep_rough"))
        e["patches"].append(dict(pt, kind="pumpkins"))
        e["fences"].append({"points": ring(pt, 3.0, 18)})
        e["pumpkin_clusters"] += patch_pumpkins(pt)
        e["features"].append({"tree": Q.LANDMARK[9], "pos": [-22, 268], "height": 10.0})
        e["graveyards"].append({"center": [-70, 230], "radius": 7, "count": 8, "fence": True})
        e["cart"] = {"side": 1, "offset": 6.0}
        e["pin"] = [2, -3]
    return e


def turn(pt, A):
    c, s = math.cos(A), math.sin(A)
    return [round(pt[0] * c - pt[1] * s, 2), round(pt[0] * s + pt[1] * c, 2)]


def turned(obj, A):
    """Every point and heading in a layout piece turned by A about the tee."""
    if isinstance(obj, list):
        if len(obj) == 2 and all(isinstance(v, (int, float)) for v in obj):
            return turn(obj, A)
        return [turned(v, A) for v in obj]
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in ("center", "pos", "face"):
                out[k] = turn(v, A)
            elif k == "slope":                   # a gradient: turned, kept fine (a green tilts ~1.7%)
                c, sn = math.cos(A), math.sin(A)
                out[k] = [round(v[0] * c - v[1] * sn, 5), round(v[0] * sn + v[1] * c, 5)]
            elif k == "rotation":
                out[k] = round(v + A, 4)
            elif k in ("points", "safe", "risk"):
                out[k] = [turn(q, A) for q in v]
            elif isinstance(v, (list, dict)) and k not in ("radius", "lobes", "carry", "profile"):
                out[k] = turned(v, A)
            else:
                out[k] = v
        return out
    return obj


def layout(i):
    p = Q.PLAN[i]
    old = json.load(open(os.path.join(OUT, FILES[i] + ".json")))
    e = extras(i, p)
    g = p["green"]
    last = (p["path"][-1][0] - p["path"][-2][0], p["path"][-1][1] - p["path"][-2][1])
    L = math.hypot(*last)
    t = (last[0] / L, last[1] / L)
    n = (-t[1], t[0])
    side = 1 if i % 2 else -1
    # the green tilts up away from the approach (back to front, ~1.7%), a little across
    slope = [round(t[0] * 0.016 + n[0] * 0.006 * side, 4), round(t[1] * 0.016 + n[1] * 0.006 * side, 4)]
    green = {"center": g["center"], "radius": g["radius"], "rotation": g["rotation"], "slope": slope}
    if "green_raise" in p:
        green["raise"] = p["green_raise"]
    pin = [g["center"][0] + e["pin"][0], g["center"][1] + e["pin"][1]]
    theme = copy.deepcopy(old["theme"])
    dom, sec, acc = Q.TREES[i]
    theme["trees"] = {"dominant": dom, "secondary": sec, "accents": acc,
                      "far": ["pine_blue", "tree_dark_blue_spruce"] if i == 4 else [sec, "tree_moonlit_pine"]}
    theme["under"] = Q.UNDER[i]
    theme["shore"] = {1: ["cattails", "ground_marsh_reeds"], 2: ["ground_marsh_reeds", "cattails"],
                      6: ["ground_marsh_reeds"], 7: ["cattails"], 8: ["ground_ferns"]}.get(i, ["cattails"])
    if i == 1 and not theme.get("mirrored"):  # the concept mirrored: the light comes from the mirrored side
        for k in ("moon_azimuth", "light_azimuth"):
            if k in theme:
                theme[k] = -theme[k]
        theme["mirrored"] = True
    elev = dict(old["elevation"])
    for k in ("tee", "green"):
        elev.pop(k, None)
    elev["profile"] = p["elev"]
    elev["mounds"] = []                       # set below, out of play
    spec = {
        "id": old["id"], "name": old["name"], "number": i, "par": p["par"], "seed": old["seed"],
        "note": p["note"],
        "path": p["path"], "fairway_start": p["fairway_start"], "fairway_width": p["widths"],
        "rough_width": 13, "deep_rough_width": 14, "tee": {"center": [0, 0], "size": old["tee"]["size"]},
        "green": green, "pin": pin, "bunkers_real": True,
        "bunkers": [ell(b["center"], b["radius"], b.get("rotation", 0.0), depth=0.5, lobes=LOBES[(k + i) % 4][:4])
                    for k, b in enumerate(p["bunkers"])],
        "water": e["water"], "zones": e["zones"], "pads": e["pads"], "elevation": elev, "wind": old["wind"],
        "graveyards": e["graveyards"], "lantern_spacing": old["lantern_spacing"],
        "trees_spacing": 6.5 if i == 4 else old["trees_spacing"], "theme": theme,
        "pumpkin_clusters": e["pumpkin_clusters"], "cart_path": e["cart"],
        "plan": {"safe": p.get("safe", p["path"]), "risk": p.get("risk", [])},
    }
    for k in ("fences", "features", "patches", "webs", "web_art", "cornfields", "hedges"):
        if e[k]:
            spec[k] = e[k]
    if "carry" in e:
        spec["carry"] = e["carry"]
    # turn the hole so its tee shot runs up +y
    a0 = math.atan2(p["path"][1][1] - p["path"][0][1], p["path"][1][0] - p["path"][0][0])
    A = math.pi / 2 - a0
    if abs(A) > 1e-6:
        for k in ("path", "green", "pin", "bunkers", "water", "zones", "pads", "graveyards", "pumpkin_clusters",
                  "fences", "features", "patches", "webs", "web_art", "cornfields", "hedges", "plan"):
            if k in spec:
                spec[k] = turned(spec[k], A)
        spec["path"] = [turn(q, A) for q in p["path"]]
    spec["path"] = [[round(a, 1), round(b, 1)] for a, b in spec["path"]]
    spec["elevation"]["mounds"] = mounds(spec)
    return spec


def mounds(spec):
    """A few broad mounds for relief, well out of play (beyond the rough, off every zone and water)."""
    path = spec["path"]
    out = []
    total = sum(math.dist(a, b) for a, b in zip(path, path[1:]))
    for k, (frac, side) in enumerate(((0.3, 1), (0.55, -1), (0.85, 1))):
        s, acc = frac * total, 0.0
        for a, b in zip(path, path[1:]):
            L = math.dist(a, b)
            if acc + L >= s:
                u = (s - acc) / L
                x, y = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
                nx, ny = (b[1] - a[1]) / L, -(b[0] - a[0]) / L
                c = [round(x + nx * side * 62, 1), round(y + ny * side * 62, 1)]
                clear = all(math.dist(c, z["center"]) > max(z["radius"]) + 26 for z in
                            spec["zones"] + spec["water"] + spec.get("pads", []) + spec.get("cornfields", []))
                if clear and math.dist(c, spec["green"]["center"]) > 50:
                    out.append({"center": c, "radius": 22, "height": 2.2})
                break
            acc += L
    return out


for i in range(1, 10):
    spec = layout(i)
    path = os.path.join(OUT, FILES[i] + ".json")
    json.dump(spec, open(path, "w"), indent=1)
    print("wrote", path, "par", spec["par"], "first leg", spec["path"][:2])
