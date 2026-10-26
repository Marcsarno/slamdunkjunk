"""3D stand-ins for four of the painted light pictures, built from parts the game already has: the carved
jack-o'-lantern (props.jack, as on the tees and the house porch), the chapel's candles and the
headstones. Each is the size its picture is shown at on the course, and takes the same arguments as a
landmark (tools/landmarks.py), so tools/export_landmark.py can export one on its own for a preview.

  classic_jack        light_classic_jack         one big carved pumpkin with a curled stem (1.5 m)
  pumpkin_pile        pumpkin_pile               three carved pumpkins in a heap on fallen leaves (1.35 m)
  pumpkin_path_lights light_pumpkin_path_lights  three carved pumpkins on iron stakes (1.9 m)
  grave_candles       light_grave_candles        a headstone with melted candles round it (1.45 m)
"""
import math

import bpy  # noqa: F401,I001  (bpy must load before bmesh)
import bmesh
import landmarks
import props
from landmarks import GLOW, IRON, LEAVES, Parts
from mathutils import Vector

WAX = (0.93, 0.84, 0.62)
STEM = (0.3, 0.22, 0.1)


def _jack(col, name, x, y, z, r, turn, pos, rot_z, scale):
    """A carved jack placed in the prop's own frame (x, y, z) and turned with it."""
    c, s = math.cos(rot_z), math.sin(rot_z)
    wx, wy = pos[0] + (x * c - y * s) * scale, pos[1] + (x * s + y * c) * scale
    return props.jack(col, name, (wx, wy, pos[2] + z * scale), r=r * scale, rot_z=rot_z + turn)


def _tube(p, a, b, r0, r1, color, sides=6):
    """A tapered tube from a to b in the body mesh."""
    vs = props.tube(p.body, a, b, r0, r1, sides)
    p._paint(p.body, p.lay, list({f for v in vs for f in v.link_faces}), color, 0.04)


def _curl(p, base, r, turn=1.0, segs=8):
    """A pumpkin stem: a thick stub that rises, leans over and curls at its tip."""
    pts = []
    for k in range(segs + 1):
        t = k / segs
        a = t * 2.2 * math.pi * 0.75
        rad = r * 0.28 * (1.0 - 0.55 * t)
        pts.append(Vector((base[0] + turn * (math.sin(a) * rad + t * r * 0.12), base[1], base[2] + r * 0.22 * t
                           + (1 - math.cos(a)) * rad * 0.6)))
    for k in range(segs):
        _tube(p, pts[k], pts[k + 1], r * 0.11 * (1 - 0.7 * k / segs), r * 0.11 * (1 - 0.7 * (k + 1) / segs), STEM)


def _leaves(p, n, rmin, rmax, seed_turn=0.0):
    """Fallen leaves round a prop's foot, red, orange and gold."""
    cols = (LEAVES, (0.75, 0.33, 0.06), (0.8, 0.55, 0.12))
    for k in range(n):
        a = k * 2.4 + seed_turn
        rr = rmin + (rmax - rmin) * ((k * 0.618) % 1.0)
        p.box((math.cos(a) * rr, math.sin(a) * rr * 0.85, 0.015), (0.2, 0.15, 0.02), cols[k % 3], jitter=0.15, kind="leaf")


def _flame(p, base, r, h):
    """A candle flame: a small glowing cone."""
    ret = bmesh.ops.create_cone(p.glow, cap_ends=True, segments=6, radius1=r, radius2=0.0, depth=h)
    bmesh.ops.translate(p.glow, vec=Vector(base) + Vector((0, 0, h / 2)), verts=ret["verts"])
    p._paint(p.glow, p.glay, list({f for v in ret["verts"] for f in v.link_faces}), GLOW, 0.0)


def classic_jack(col, name, pos, rot_z=0.0, scale=1.0):
    r = 0.78
    _jack(col, f"{name}_Jack", 0, 0, 0, r, 0.0, pos, rot_z, scale)
    p = Parts(seed=41, surfaces=True)
    _curl(p, (0.06, 0.03, r * 0.8 * 1.62), r * 1.4)
    _leaves(p, 9, r * 0.95, r * 1.35)
    return p.finish(col, name, pos, rot_z, scale)


def pumpkin_pile(col, name, pos, rot_z=0.0, scale=1.0):
    # the big one at the back sits up on the others, as in the picture
    _jack(col, f"{name}_JackBig", 0.15, 0.3, 0.26, 0.5, 0.1, pos, rot_z, scale)
    _jack(col, f"{name}_JackL", -0.45, -0.12, 0.0, 0.36, -0.25, pos, rot_z, scale)
    _jack(col, f"{name}_JackR", 0.55, -0.2, 0.0, 0.28, 0.3, pos, rot_z, scale)
    p = Parts(seed=42, surfaces=True)
    p.box((0.15, 0.32, 0.13), (0.5, 0.3, 0.26), (0.25, 0.16, 0.08), jitter=0.0)       # what the big one rests on, behind the others
    for x, y, z, r, t in ((0.15, 0.3, 0.26, 0.5, 1), (-0.45, -0.12, 0.0, 0.36, -1), (0.55, -0.2, 0.0, 0.28, 1)):
        _curl(p, (x + 0.03, y, z + r * 0.8 * 1.62), r * 1.3, turn=t)
    _leaves(p, 16, 0.5, 1.0)
    return p.finish(col, name, pos, rot_z, scale)


def pumpkin_path_lights(col, name, pos, rot_z=0.0, scale=1.0):
    p = Parts(seed=43, surfaces=True)
    for x, h, r, turn in ((-0.75, 1.0, 0.26, 0.25), (0.0, 1.35, 0.32, 0.0), (0.75, 0.95, 0.24, -0.3)):
        _tube(p, (x, 0, 0), (x, 0, h), 0.03, 0.025, IRON)                             # the iron stake
        _tube(p, (x, 0, h - 0.12), (x, 0, h), 0.03, r * 0.55, IRON)                    # the cup it holds the pumpkin in
        vine = [Vector((x + 0.045 * math.cos(t * 0.9), 0.045 * math.sin(t * 0.9), 0.08 + t * (h - 0.25) / 14))
                for t in range(15)]                                                  # a vine wound up it
        for a, b in zip(vine, vine[1:]):
            _tube(p, a, b, 0.016, 0.014, (0.24, 0.2, 0.1), sides=4)
        _jack(col, f"{name}_Jack{x:+.1f}", x, 0, h - 0.04, r, turn, pos, rot_z, scale)
        _curl(p, (x + 0.02, 0.0, h - 0.04 + r * 0.8 * 1.62), r * 1.3, turn=1 if x <= 0 else -1)
    return p.finish(col, name, pos, rot_z, scale)


def grave_candles(col, name, pos, rot_z=0.0, scale=1.0):
    p = Parts(seed=44, surfaces=True)
    w, h = 0.8, 1.15                                                                 # the headstone, a rounded top
    prof = [(-w / 2, 0.0), (w / 2, 0.0)] + [(w / 2 * math.cos(a), h - w / 2 + w / 2 * math.sin(a) * 0.8)
                                            for a in (k * math.pi / 8 for k in range(9))]
    p.prism(prof, 0.18, 0.38, landmarks.CHAPEL_STONE)
    p.box((0, 0.28, 0.05), (1.0, 0.45, 0.1), landmarks.QUOIN)                          # its footing
    p.box((0, 0.17, 0.62), (0.07, 0.02, 0.42), landmarks.QUOIN, jitter=0.0)              # a cross cut in its face
    p.box((0, 0.17, 0.7), (0.26, 0.02, 0.07), landmarks.QUOIN, jitter=0.0)
    # fat candles of different heights round its foot, tallest at the sides, melted wax down them
    for x, y, h, r in ((-0.6, -0.05, 0.72, 0.13), (-0.36, -0.32, 0.46, 0.12), (-0.08, -0.5, 0.26, 0.11),
                       (0.22, -0.4, 0.36, 0.11), (0.52, -0.15, 0.6, 0.13), (0.7, 0.2, 0.34, 0.1)):
        p.cylinder((x, y, 0.0), r * 1.5, 0.03, WAX, segments=10)                     # the pool of wax
        p.cylinder((x, y, 0.0), r, h, WAX, segments=10)
        p.cylinder((x, y, h - 0.05), r * 1.12, 0.05, WAX, segments=10)                # the melted lip
        for k in range(5):                                                           # drips down its side
            a = k * 1.3 + x * 7
            ln = h * (0.25 + 0.5 * ((k * 0.618 + x) % 1.0))
            _tube(p, (x + math.cos(a) * r * 1.02, y + math.sin(a) * r * 1.02, h - 0.03),
                  (x + math.cos(a) * r * 1.02, y + math.sin(a) * r * 1.02, h - 0.03 - ln), 0.03, 0.022, WAX, sides=5)
        _tube(p, (x, y, h - 0.03), (x, y, h + 0.04), 0.008, 0.008, (0.1, 0.08, 0.06), sides=4)  # the wick
        _flame(p, (x, y, h + 0.03), 0.04, 0.15)                                       # its flame
    return p.finish(col, name, pos, rot_z, scale)
