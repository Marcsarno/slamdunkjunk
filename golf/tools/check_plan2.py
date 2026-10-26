"""Second check of plan v2: landing widths, green depth against the approach, where the bunkers sit
round the green, fairway bunkers against the drive, slope where the ball lands, pads, totals."""
import io, math, sys, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    import plan_holes2 as Q
    import check_plan as C
P, PLAN, YD = Q.P, Q.PLAN, Q.YD


def point_at(path, s):
    return C.along(path, s)[0]


def elev(el, s):
    for (s0, z0), (s1, z1) in zip(el, el[1:]):
        if s <= s1:
            return z0 + (z1 - z0) * (s - s0) / (s1 - s0)
    return el[-1][1]


def green_depth(g, ang):
    """Depth of the green ellipse along heading ang (m)."""
    rx, ry = g["radius"]
    r = g.get("rotation", 0)
    a = ang - r
    return 2 / math.sqrt((math.cos(a) / rx) ** 2 + (math.sin(a) / ry) ** 2)


tot = 0
for i, p in PLAN.items():
    path, L = p["path"], P.length(p["path"])
    tot += L * YD
    g = p["green"]
    print("\n%d %s par %d %d yd" % (i, P.NAMES[i], p["par"], L * YD))
    if p["par"] == 3:
        frm = path[0]
        app = L
    else:
        frm = point_at(path, Q.DRIVE_END)
        app = L - Q.DRIVE_END
        w = [C.width_at(path, p["widths"], s) * YD for s in (190, 210, 230, 250)]
        print("   fairway width 190/210/230/250 m out: %s yd" % "/".join("%d" % x for x in w))
        sl = [(elev(p["elev"], s + 15) - elev(p["elev"], s - 15)) / 30 * 100 for s in (205, 228)]
        print("   ground in the landing area: %+.1f%% / %+.1f%%" % tuple(sl))
    ang = math.atan2(g["center"][1] - frm[1], g["center"][0] - frm[0])
    dep = green_depth(g, ang) * YD
    wid = green_depth(g, ang + math.pi / 2) * YD
    print("   approach %d yd (%s): green %d yd deep x %d yd wide along that line, %.0f sq ft" % (
        app * YD, C.club_for(app), dep, wid, math.pi * g["radius"][0] * g["radius"][1] * 10.764))
    for b in p["bunkers"]:
        bx, by = b["center"]
        d_g = math.dist(b["center"], g["center"])
        if d_g < 35:
            rel = math.degrees((math.atan2(by - g["center"][1], bx - g["center"][0]) - ang + math.pi) % (2 * math.pi) - math.pi)
            side = "behind" if abs(rel) < 45 else ("front" if abs(rel) > 135 else ("left" if rel > 0 else "right"))
            print("   greenside bunker %s of the green (%d deg)  %dx%d yd" % (side, rel, 2 * b["radius"][0] * YD, 2 * b["radius"][1] * YD))
        else:
            # distance from tee along the hole and lateral offset
            best = min(((math.dist(b["center"], (x, y)), k) for k, (x, y, w_) in enumerate(P.densify(path, p["widths"], 1.0))))
            s = best[1] * 1.0
            print("   fairway bunker %d yd from the tee, %d m off the centre line" % (math.dist(path[0], b["center"]) * YD, best[0]))
    for pad in p.get("pads", []):
        print("   pad %dx%d yd at %d yd from the tee, %d yd to the green" % (
            2 * pad["radius"][0] * YD, 2 * pad["radius"][1] * YD, math.dist(path[0], pad["center"]) * YD,
            math.dist(pad["center"], g["center"]) * YD))
print("\ntotal %d yd, par %d" % (tot, sum(p["par"] for p in PLAN.values())))
