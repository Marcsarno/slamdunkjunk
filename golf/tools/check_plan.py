"""Measure the proposed holes against the game's clubs and real-course norms."""
import math
import sys

sys.argv = ["x"]
import plan_holes as P   # noqa: E402

YD = 1.0936
DRIVE_CARRY, DRIVE_TOTAL = 205.0, 228.0      # metres: the game's driver, flat, no wind (carry + ~11% roll)
CLUBS = [("Driver", 205), ("3 Wood", 185), ("5 Iron", 165), ("7 Iron", 145), ("9 Iron", 125), ("P Wedge", 105),
         ("S Wedge", 82), ("L Wedge", 58)]


def club_for(m):
    for name, c in reversed(CLUBS):
        if c >= m * 0.97:
            return name
    return "beyond driver"


def along(path, s):
    for i in range(len(path) - 1):
        L = math.dist(path[i], path[i + 1])
        if s <= L:
            t = s / L
            return [path[i][0] + (path[i + 1][0] - path[i][0]) * t, path[i][1] + (path[i + 1][1] - path[i][1]) * t], i, t
        s -= L
    return path[-1], len(path) - 2, 1.0


def width_at(path, widths, s):
    _, i, t = along(path, s)
    return widths[i] + (widths[i + 1] - widths[i]) * t


def corner(path):
    """Distance along the path to the middle of the first bend (heading change over 25 degrees)."""
    hd = [math.atan2(path[i + 1][1] - path[i][1], path[i + 1][0] - path[i][0]) for i in range(len(path) - 1)]
    s, acc = 0.0, 0.0
    for i in range(1, len(hd)):
        s += math.dist(path[i - 1], path[i])
        d = (hd[i] - hd[i - 1] + math.pi) % (2 * math.pi) - math.pi
        acc += d
        if abs(acc) > math.radians(25):
            return s
    return None


def ellipse_exit(a, b, h):
    """Along segment a->b, the distance from a where it leaves the hazard ellipse (None if it never enters)."""
    cx, cy = h["center"]
    rx, ry = h["radius"]
    rot = h.get("rotation", 0.0)
    L = math.dist(a, b)
    last = None
    for k in range(int(L) + 1):
        x = a[0] + (b[0] - a[0]) * k / L
        y = a[1] + (b[1] - a[1]) * k / L
        dx, dy = x - cx, y - cy
        u = (dx * math.cos(rot) + dy * math.sin(rot)) / rx
        v = (-dx * math.sin(rot) + dy * math.cos(rot)) / ry
        if u * u + v * v <= 1.0:
            last = k
    return last


for i in range(1, 10):
    p = P.scaled(P.PROPOSED[i])
    path, widths = p["path"], p["widths"]
    L = P.length(path)
    g = p["green"]
    garea = math.pi * g["radius"][0] * g["radius"][1]
    print("\n%d %s  par %d  %d yd" % (i, P.NAMES[i], p["par"], L * YD))
    print("   green %.0f x %.0f yd, %.0f sq ft" % (2 * g["radius"][0] * YD, 2 * g["radius"][1] * YD, garea * 10.764))
    if p["par"] == 3:
        print("   tee shot %d yd: %s" % (L * YD, club_for(L)))
    else:
        c = corner(path)
        print("   bend at %s yd from the tee (a drive lands %d-%d yd)" % (int(c * YD) if c else "none",
              DRIVE_CARRY * YD, DRIVE_TOTAL * YD))
        print("   fairway at the drive's landing (200-230 m): %d-%d yd wide" % (
            width_at(path, widths, 200) * YD, width_at(path, widths, min(230, L - 1)) * YD))
        left = L - DRIVE_TOTAL
        if p["par"] == 4:
            print("   approach after a good drive: %d yd (%s)" % (left * YD, club_for(left)))
        else:
            print("   after drive + 3 wood: %d yd (%s); going for it in two needs %d yd" % (
                (left - 200) * YD, club_for(left - 200), left * YD))
    for h in p.get("hazards", []):
        if "center" not in h:
            continue
        rx, ry = h["radius"]
        print("   %s: %.0f x %.0f yd" % (h.get("label", "hazard"), 2 * rx * YD, 2 * ry * YD), end="")
        if p.get("risk"):
            a, b = p["risk"][0], p["risk"][1]
            e = ellipse_exit(a, b, h)
            if e is not None:
                print(";  risky line carries it at %d yd from the tee" % (e * YD), end="")
        print()
    for b in p.get("bunkers", []):
        rx, ry = b["radius"]
        print("   bunker %.0f x %.0f yd (%d m2)" % (2 * rx * YD, 2 * ry * YD, math.pi * rx * ry))
