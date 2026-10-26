"""Run plan v2 through the hole builder's own ground (hole_gen.Hole) and measure what a golfer
meets: plays-like for each shot (1 m of rise ~ 1 m more), the slope where drives land, the green
against the water beside it, pond banks, fairway grades against the builder's limits."""
import io, contextlib, math, sys, copy
import numpy as np
sys.path.append(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import hole_gen as HG


def ravine(points, half_width=5.0, depth=4.2):
    """As make_holes_4_9.ravine: one narrow water piece per segment of the line."""
    out = []
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        dx, dy = x1 - x0, y1 - y0
        ln = (dx * dx + dy * dy) ** 0.5
        out.append({"center": [round((x0 + x1) / 2, 2), round((y0 + y1) / 2, 2)], "radius": [round(ln / 2 + 4.0, 2), half_width],
                    "rotation": round(math.atan2(dy, dx), 4), "level_offset": -depth})
    return out
with contextlib.redirect_stdout(io.StringIO()):
    import plan_holes2 as Q
    import check_plan as C
P, PLAN, YD = Q.P, Q.PLAN, Q.YD
WATERY = {Q.POND, Q.PURPLE, Q.BLOOD}


def spec_for(i, p):
    water, zones = [], []
    for h in p["hazards"]:
        if "line" in h:
            water += ravine(h["line"], half_width=h["width"] / 2 * (0.45 if h["color"] == Q.RAVINE else 1.0),
                            depth=4.2 if h["color"] == Q.RAVINE else 0.6)
            continue
        zones.append({"center": h["center"], "radius": [r + 6 for r in h["radius"]], "rotation": h["rotation"], "surface": "deep_rough"})
        if tuple(h["color"]) in WATERY:
            water.append({"center": h["center"], "radius": h["radius"], "rotation": h["rotation"], "level_offset": -0.6})
    return {"id": "p%d" % i, "name": "x", "number": i, "par": p["par"], "seed": 100 + i,
            "path": p["path"], "fairway_width": p["widths"], "fairway_start": p["fairway_start"],
            "rough_width": 13, "deep_rough_width": 14, "tee": {"center": p["path"][0], "size": [8, 10]},
            "green": dict(p["green"], slope=[0.012, 0.016], **({"raise": p["green_raise"]} if "green_raise" in p else {})), "pin": p["green"]["center"],
            "bunkers": [dict(b, depth=0.5) for b in p["bunkers"]], "water": water, "zones": zones,
            "pads": [dict(q) for q in p.get("pads", [])],
            "elevation": {"profile": p["elev"], "cross_tilt": 0.008, "roll_height": 0.35, "bank_height": 2.5,
                          "undulation": 0.3}}


def H(hole, x, y):
    return float(hole.height(np.array([[x]], float), np.array([[y]], float))[0, 0])


def B(hole, x, y):
    return float(hole.base_height(np.array([[x]], float), np.array([[y]], float))[0, 0])


def play(d, rise):
    return "%d yd plays %d" % (d * YD, (d + rise) * YD)


for i, p in PLAN.items():
    sp = spec_for(i, copy.deepcopy(p))
    with contextlib.redirect_stdout(io.StringIO()):
        hole = HG.Hole(sp)
    tee = p["path"][0]
    g = p["green"]["center"]
    zt, zg = H(hole, *tee), H(hole, *g)
    out = ["\n%d %s par %d: tee %.1f m, green %.1f m" % (i, P.NAMES[i], p["par"], zt, zg)]
    if p["par"] == 3:
        d = math.dist(tee, g)
        out.append("   tee shot %s (%s)" % (play(d, zg - zt), C.club_for(d + zg - zt)))
    else:
        land = C.along(p["path"], Q.DRIVE_CARRY)[0]
        stop = C.along(p["path"], Q.DRIVE_END)[0]
        zl, zs = H(hole, *land), H(hole, *stop)
        out.append("   drive lands %.1f m (%+.1f m from the tee: carries %+d yd)" % (zl, zl - zt, -(zl - zt) * YD))
        # slope of the landing area along the line and across it (stance)
        a = C.along(p["path"], Q.DRIVE_CARRY - 10)[0]
        b = C.along(p["path"], Q.DRIVE_END + 10)[0]
        along = (H(hole, *b) - H(hole, *a)) / math.dist(a, b) * 100
        t = np.subtract(b, a) / math.dist(a, b)
        n = np.array([-t[1], t[0]])
        c = np.add(stop, n * 8)
        e = np.subtract(stop, n * 8)
        across = (H(hole, *c) - H(hole, *e)) / 16 * 100
        out.append("   landing area: %+.1f%% along (runs %s), %.1f%% across" % (along, "on" if along < 0 else "up, stops sooner", abs(across)))
        d = math.dist(stop, g)
        out.append("   approach %s (%s)" % (play(d, zg - zs), C.club_for(d + zg - zs)))
        for pad in p.get("pads", []):
            zp = H(hole, *pad["center"])
            dp = math.dist(tee, pad["center"])
            out.append("   brave drive to the pad: %s; then %s" % (play(dp, zp - zt), play(math.dist(pad["center"], g), zg - zp)))
    for w in sp["water"]:
        if w["level"] is None:
            continue
        a_ = np.linspace(0, math.tau, 48, endpoint=False)
        rx, ry = w["radius"]
        ca, sa = math.cos(w["rotation"]), math.sin(w["rotation"])
        ex = w["center"][0] + 1.15 * (rx * np.cos(a_) * ca - ry * np.sin(a_) * sa)
        ey = w["center"][1] + 1.15 * (rx * np.cos(a_) * sa + ry * np.sin(a_) * ca)
        rim = hole.base_height(ex[None, :], ey[None, :])[0]
        dg = math.dist(w["center"], g) - max(w["radius"])
        out.append("   water at %.1f m: bank %.1f-%.1f m above it%s" % (w["level"], rim.min() - w["level"], rim.max() - w["level"],
                   ("; green %.1f m above the water" % (zg - w["level"])) if dg < 30 else ""))
    # fairway grades on the built ground (1 m grid), against the builder's limit (p95 <= 9%)
    xs = np.arange(hole.x0, hole.x1, 1.0)
    ys = np.arange(hole.y0, hole.y1, 1.0)
    X, Y = np.meshgrid(xs, ys)
    Z = hole.height(X, Y)
    gy_, gx_ = np.gradient(Z, 1.0)
    pct = np.hypot(gx_, gy_) * 100
    lat, s = hole.lateral(X, Y)
    fw = (np.abs(lat) < hole.half_width(s) - 1) & (s > p["fairway_start"]) & (np.hypot(X - g[0], Y - g[1]) > max(p['green']['radius']) + 10) & \
         (np.hypot(X - tee[0], Y - tee[1]) > 15)
    if "fairway_gap" in p:
        fw &= ~((s > p["fairway_gap"][0]) & (s < p["fairway_gap"][1]))
    out.append("   fairway grade p50 %.1f%%  p95 %.1f%%  max %.1f%%  (limit p95 9%%)" % (
        np.percentile(pct[fw], 50), np.percentile(pct[fw], 95), pct[fw].max()))
    print("\n".join(out))
