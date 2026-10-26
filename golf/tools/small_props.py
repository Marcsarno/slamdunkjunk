"""3D stand-ins for painted light pictures, built in Blender (headless) from simple parts. Each is the size
its picture is shown at on the course, and takes the same arguments as a landmark (tools/landmarks.py), so
tools/export_landmark.py can export one on its own for a preview.

  classic_jack        light_classic_jack         one big carved pumpkin, an angry grin, a curled stem (1.5 m)
  pumpkin_pile        pumpkin_pile               three carved pumpkins heaped on fallen leaves (1.35 m)
  grave_candles       light_grave_candles        a cracked headstone with melted candles round it (1.45 m)
  pumpkin_path_lights light_pumpkin_path_lights  three carved pumpkins on iron stakes (1.9 m; not chosen)

The pumpkins here are finer than the tee markers' (props.jack): smooth-shaded, with deep creases between
round lobes, each with its own carved face, a lit carved edge round every cut, and a gnarled stem that
curls over. Shells use the game's pumpkin material (pumpkin_vc: lit by the moon, with the candle's glow),
the cuts its glow material; stems, leaves, wax and stone the landmarks' patterned material.
"""
import math

import bpy  # noqa: F401,I001  (bpy must load before bmesh)
import bmesh
import landmarks
import props
from landmarks import GLOW, IRON, SURFACE, Parts
from mathutils import Matrix, Vector

STEM_DK, STEM_LT = (0.4, 0.28, 0.13), (0.58, 0.45, 0.24)
LEAF_COLS = ((0.62, 0.3, 0.06), (0.68, 0.44, 0.08), (0.64, 0.54, 0.16), (0.58, 0.24, 0.05))
WAX_LO, WAX_HI = (0.62, 0.56, 0.42), (0.8, 0.78, 0.6)      # the patterned material brightens these ×1.6
HEADSTONE = (0.54, 0.52, 0.6)
CRACK = (0.16, 0.14, 0.2)
MOSS = (0.24, 0.3, 0.12)
FLESH = (1.0, 0.72, 0.3)                                    # the carved edge, lit from inside
P_LOBE, P_CREASE, P_BASE, P_TOP = (0.88, 0.38, 0.07), (0.24, 0.06, 0.02), (0.4, 0.11, 0.03), (0.5, 0.26, 0.07)
SQ = 0.78                                                   # pumpkins are squat
LOBES = 10


# ---------- carved faces: polygons in the front's own (u across, v up) units, about -0.6..0.6 --------
def _mirror(poly):
    return [(-u, v) for u, v in reversed(poly)]


def _grin(w, top, depth, upper_teeth=(), lower_teeth=(), tooth=0.09, tip=0.06):
    """A wide carved mouth from -w to w: its upper edge sags to top - depth/3 at the middle, its lower
    edge to top - depth; square teeth hang from the upper edge and stand on the lower."""
    n = 14
    up, lo = [], []
    for k in range(n + 1):
        u = -w + 2 * w * k / n
        t = 1 - (u / w) ** 2
        up.append((u, top + tip * (1 - t) - depth * 0.33 * t))
        lo.append((u, top + tip * (1 - t) - depth * t ** 0.7))

    def notch(edge, teeth, sign):
        out = []
        for u, v in edge:
            for c in teeth:
                if abs(u - c) < 1e-6:
                    break
            else:
                out.append((u, v))
                continue
            hw = tooth * 0.55
            out += [(u - hw, v), (u - hw, v + sign * tooth), (u + hw, v + sign * tooth), (u + hw, v)]
        return out
    # teeth sit on sample points: snap the asked-for places to the nearest
    snap = lambda cs: [min((p[0] for p in up), key=lambda u: abs(u - c)) for c in cs]  # noqa: E731
    upper = notch(up, snap(upper_teeth), -1)
    lower = notch(lo, snap(lower_teeth), +1)
    return upper + list(reversed(lower))


def _dome_eye(cx, cy, rx, ry, flat_up=False, n=8):
    """A half-round eye: round on top and flat below (a happy jack), or flat on top (flat_up)."""
    pts = [(cx + rx * math.cos(math.pi * k / n), cy + (-1 if flat_up else 1) * ry * math.sin(math.pi * k / n))
           for k in range(n + 1)]
    return pts if not flat_up else list(reversed(pts))


FACES = {
    # the picture's classic jack: big slanted eyes, a small nose, a wide toothy grin
    "angry": [[(-0.56, 0.08), (-0.12, 0.12), (-0.4, 0.48)], _mirror([(-0.56, 0.08), (-0.12, 0.12), (-0.4, 0.48)]),
              [(-0.08, -0.04), (0.08, -0.04), (0.0, 0.12)],
              _grin(0.66, -0.1, 0.42, upper_teeth=(-0.24, 0.24), lower_teeth=(-0.42, 0.0, 0.42))],
    # the pile's big one: round happy eyes, a little nose, a broad smile with two teeth
    "happy": [_dome_eye(-0.26, 0.12, 0.15, 0.17), _dome_eye(0.26, 0.12, 0.15, 0.17),
              [(-0.06, -0.02), (0.06, -0.02), (0.0, 0.09)],
              _grin(0.52, -0.12, 0.34, upper_teeth=(-0.15, 0.15), tooth=0.08)],
    # the pile's left one: triangle eyes, a grin with one tooth down
    "grin": [[(-0.42, 0.06), (-0.12, 0.06), (-0.27, 0.32)], _mirror([(-0.42, 0.06), (-0.12, 0.06), (-0.27, 0.32)]),
             [(-0.05, -0.04), (0.05, -0.04), (0.0, 0.06)],
             _grin(0.5, -0.12, 0.32, upper_teeth=(0.0,), tooth=0.08)],
    # the pile's small one: round eyes, a plain smile
    "sweet": [_dome_eye(-0.24, 0.1, 0.14, 0.15), _dome_eye(0.24, 0.1, 0.14, 0.15),
              _grin(0.46, -0.12, 0.26)],
}


# ---------- the pumpkin --------------------------------------------------------------------------
def _lobe(phi):
    """1 on a lobe's crown, 0 in the crease between two."""
    return abs(math.cos(LOBES * phi / 2)) ** 0.35


def _surface(x, y, z):
    """The pumpkin's shell through a unit-sphere direction: lobed, squat, dimpled where the stem is."""
    phi = math.atan2(y, x)
    k = 1.0 - 0.2 * (1.0 - _lobe(phi))
    z2 = z * SQ
    if z > 0.72:                                           # the dimple round the stem
        z2 -= (z - 0.72) * SQ * 0.9
    if z < -0.8:                                           # it sits on a flattish bottom
        z2 += (-0.8 - z) * SQ * 0.6
    return Vector((x * k, y * k, z2))


class Pumpkins:
    """Carved pumpkins for one prop, all in one mesh: the shells and carved edges (pumpkin_vc) and the
    cuts (glow)."""

    def __init__(self):
        self.bm = bmesh.new()
        self.lay = props.vcol_layer(self.bm)

    def add(self, center, r, turn, face):
        bm, lay = self.bm, self.lay
        m = Matrix.Translation(Vector(center)) @ Matrix.Rotation(turn, 4, "Z") @ Matrix.Scale(r, 4)
        ret = bmesh.ops.create_uvsphere(bm, u_segments=50, v_segments=16, radius=1.0)
        for v in ret["verts"]:
            d = v.co.normalized()
            v.co = _surface(d.x, d.y, d.z)
        faces = list({f for v in ret["verts"] for f in v.link_faces})
        for f in faces:
            f.smooth = True
            f.material_index = 0
            for lp in f.loops:
                c = lp.vert.co
                lobe = _lobe(math.atan2(c.y, c.x))
                col = props.lerp(P_CREASE, P_LOBE, lobe ** 1.4)
                h = c.z / SQ
                col = props.lerp(P_BASE, col, min(1.0, 0.45 + 0.75 * (h + 1) / 1.4))       # darker below
                if h > 0.6:
                    col = props.lerp(col, P_TOP, (h - 0.6) / 0.4 * 0.7)                    # browner at the top
                lp[lay] = (*col, 1)
        bmesh.ops.transform(bm, matrix=m, verts=ret["verts"])
        for shape in FACES[face]:
            self._cut(shape, m, 1.22, 1.004, FLESH, 0)      # the carved edge, a rim of lit flesh
            self._cut(shape, m, 1.0, 1.009, (1, 0.75, 0.3), 1)
        return Vector(center) + Vector((0, 0, r * SQ * 0.74))   # where its stem starts

    def _cut(self, shape, m, grow, lift, color, mat):
        tmp = bmesh.new()
        cu = sum(u for u, _ in shape) / len(shape)
        cv = sum(v for _, v in shape) / len(shape)
        f = tmp.faces.new([tmp.verts.new((cu + (u - cu) * grow, cv + (v - cv) * grow, 0)) for u, v in shape])
        bmesh.ops.triangulate(tmp, faces=[f])
        bmesh.ops.subdivide_edges(tmp, edges=list(tmp.edges), cuts=1, use_grid_fill=True)
        bmesh.ops.triangulate(tmp, faces=list(tmp.faces))
        new = {}
        for v in tmp.verts:
            x, zs = v.co.x * 0.82, v.co.y * 0.95
            y = -math.sqrt(max(0.0, 1 - x * x - zs * zs))
            new[v] = self.bm.verts.new(m @ (_surface(x, y, zs) * lift))
        for g in tmp.faces:
            try:
                nf = self.bm.faces.new([new[v] for v in g.verts])
            except ValueError:
                continue
            nf.material_index = mat
            nf.smooth = False
            for lp in nf.loops:
                lp[self.lay] = (*color, 1)
        tmp.free()

    def finish(self, col, name, pos, rot_z, scale):
        bm = self.bm
        bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(pos)) @ Matrix.Rotation(rot_z, 4, "Z")
                            @ Matrix.Scale(scale, 4), verts=bm.verts)
        bm.normal_update()
        return props.link(name + "_Pumpkins", bm, [props.material("pumpkin_vc", 0.6),
                                                   props.material("glow", 0.5, emit=(1.0, 0.55, 0.12), strength=14.0)], col)


# ---------- small parts ----------------------------------------------------------------------------
def _tube(p, a, b, r0, r1, color, sides=6, kind="plain"):
    """A tapered tube from a to b in the body mesh."""
    vs = props.tube(p.body, a, b, r0, r1, sides)
    p._paint(p.body, p.lay, list({f for v in vs for f in v.link_faces}), color, 0.04, kind=kind)


def _ball(p, c, r, color, seg=8, kind="plain", squash=1.0):
    vs = props.ball(p.body, c, r, seg)
    for v in vs:
        v.co.z = c[2] + (v.co.z - c[2]) * squash
    p._paint(p.body, p.lay, list({f for v in vs for f in v.link_faces}), color, 0.03, kind=kind)


def _stem(p, base, r, turn=1.0, lean=0.0):
    """A gnarled stem: a thick, ridged, twisting stub out of the dimple, then a thin tendril that loops
    over and curls at its tip, as in the pictures."""
    def put(x, z):
        return Vector((base[0] + x * math.cos(lean), base[1] + x * math.sin(lean), base[2] + z))
    stub = [put(turn * r * 0.05 * math.sin(t * 2.2), r * 0.42 * t) for t in (k / 4 for k in range(5))]
    for k in range(4):                                                       # the stub, twisting as it tapers
        r0, r1 = r * (0.13 - 0.016 * k) * (1.15 if k == 0 else 1.0), r * (0.13 - 0.016 * (k + 1))
        vs = props.tube(p.body, stub[k], stub[k + 1], r0, r1, 6)
        bmesh.ops.rotate(p.body, cent=stub[k], matrix=Matrix.Rotation(k * 0.35, 3, "Z"), verts=vs)
        p._paint(p.body, p.lay, list({f for v in vs for f in v.link_faces}), props.lerp(STEM_DK, STEM_LT, 0.3 + k / 5),
                 0.05, kind="plain")
    top = stub[-1]
    segs = 14
    prev = top
    for k in range(1, segs + 1):                                             # the tendril: out, over and round
        t = k / segs
        a = t * 1.7 * math.pi
        cr = r * 0.22 * (1 - 0.55 * t)
        x = turn * (r * 0.06 * t + math.sin(a) * cr)
        z = r * 0.12 * t + (1 - math.cos(a)) * cr * 0.8
        pt = top + (put(x, z) - put(0, 0))
        _tube(p, prev, pt, r * 0.065 * (1 - 0.65 * (t - 1 / segs)), r * 0.065 * (1 - 0.65 * t), STEM_LT, sides=5)
        prev = pt


def _maple(p, x, y, size, ang, color, z=0.0, tilt=(0.0, 0.0)):
    """A fallen maple leaf: five pointed lobes, one face up (lying on the ground, or tipped against
    something)."""
    pts = []
    for i in range(10):
        a = ang + i * 2 * math.pi / 10
        pts.append(((size if i % 2 == 0 else size * 0.45) * math.cos(a), (size if i % 2 == 0 else size * 0.45) * math.sin(a)))
    rot = Matrix.Rotation(tilt[0], 3, "X") @ Matrix.Rotation(tilt[1], 3, "Y")
    bm = p.body
    c = bm.verts.new(Vector((x, y, z + 0.01)))
    ring = [bm.verts.new(Vector((x, y, z + 0.01)) + rot @ Vector((u, v, 0))) for u, v in pts]
    faces = [bm.faces.new((c, ring[i], ring[(i + 1) % 10])) for i in range(10)]
    if (rot @ Vector((0, 0, 1))).z < 0.3:                                     # tipped up: seen from both sides
        back = [bm.verts.new(v.co - rot @ Vector((0, 0, 0.004))) for v in ring]
        cb = bm.verts.new(c.co - rot @ Vector((0, 0, 0.004)))
        faces += [bm.faces.new((cb, back[(i + 1) % 10], back[i])) for i in range(10)]
    p._paint(bm, p.lay, faces, color, 0.12, kind="plain")


def _leaf_bed(p, n, rmin, rmax, seed=0.0, sx=1.0, sy=0.85):
    for k in range(n):
        a = k * 2.399 + seed
        rr = rmin + (rmax - rmin) * ((k * 0.618 + seed) % 1.0)
        _maple(p, math.cos(a) * rr * sx, math.sin(a) * rr * sy, 0.14 + 0.07 * ((k * 0.37) % 1.0), a * 1.7,
               LEAF_COLS[k % 4], z=0.005 * (k % 3), tilt=(0.15 * math.sin(k), 0.15 * math.cos(k)))


def _leaf_mound(p, center, rx, ry, h):
    """A low heap of leaves (the patterned material draws the leaves on it)."""
    vs = props.ball(p.body, center, 1.0, 12)
    for v in vs:
        d = v.co - Vector(center)
        v.co = Vector(center) + Vector((d.x * rx, d.y * ry, max(0.0, d.z) * h))
    p._paint(p.body, p.lay, list({f for v in vs for f in v.link_faces}), (0.5, 0.24, 0.07), 0.1, kind="leaf")


def _flame(p, base, r, h):
    """A candle flame: a teardrop, round below and drawn up to a point."""
    bm = p.glow
    ret = bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=5, radius=1.0)
    for v in ret["verts"]:
        z = v.co.z
        k = (1 - max(0.0, z)) ** 1.3 if z > 0 else 1.0
        v.co = Vector((base[0] + v.co.x * r * k, base[1] + v.co.y * r * k,
                       base[2] + r + (z * h if z > 0 else z * r)))
    p._paint(bm, p.glay, list({f for v in ret["verts"] for f in v.link_faces}), GLOW, 0.0)


# ---------- the props ------------------------------------------------------------------------------
def classic_jack(col, name, pos, rot_z=0.0, scale=1.0):
    r = 0.8
    pk = Pumpkins()
    top = pk.add((0, 0, r * SQ * 0.92), r, 0.0, "angry")
    p = Parts(seed=41, surfaces=True)
    _stem(p, top, r * 1.35, turn=1.0, lean=0.3)
    _leaf_bed(p, 11, r * 0.95, r * 1.5, seed=0.4)
    _maple(p, -r * 0.7, -r * 0.55, 0.15, 1.0, LEAF_COLS[1], z=0.12, tilt=(0.9, 0.3))    # one tipped against it
    return [pk.finish(col, name, pos, rot_z, scale)] + p.finish(col, name, pos, rot_z, scale)


def pumpkin_pile(col, name, pos, rot_z=0.0, scale=1.0):
    """As in the picture: a big one up at the back on a heap of leaves, a middling one in front on the
    left and a small one on the right, all looking out, leaves all round and tucked between them."""
    pk = Pumpkins()
    p = Parts(seed=42, surfaces=True)
    _leaf_mound(p, (0.08, 0.34, 0.0), 0.45, 0.3, 0.26)
    for (x, y, r, turn, face, sturn, lean) in ((0.08, 0.3, 0.5, 0.05, "happy", -1.0, -0.4),
                                               (-0.4, -0.18, 0.36, -0.3, "grin", 1.0, 0.5),
                                               (0.5, -0.24, 0.27, 0.35, "sweet", -1.0, 0.2)):
        z = r * SQ * 0.92 + (0.22 if r == 0.5 else 0.0)
        top = pk.add((x, y, z), r, turn, face)
        _stem(p, top, r * 1.3, turn=sturn, lean=lean)
    _leaf_bed(p, 20, 0.45, 1.05, seed=0.2, sx=1.1, sy=0.8)
    for x, y, z, a, tilt in ((0.06, -0.38, 0.06, 0.4, (1.1, 0.2)), (-0.75, 0.05, 0.1, 2.0, (0.4, -1.0)),
                             (0.82, -0.05, 0.08, 1.2, (0.3, 1.0)), (-0.2, 0.45, 0.42, 0.9, (0.6, 0.4)),
                             (0.5, 0.42, 0.3, 2.6, (0.7, -0.5))):           # leaves tipped up between them
        _maple(p, x, y, 0.14, a, LEAF_COLS[int(a * 3) % 4], z=z, tilt=tilt)
    return [pk.finish(col, name, pos, rot_z, scale)] + p.finish(col, name, pos, rot_z, scale)


def pumpkin_path_lights(col, name, pos, rot_z=0.0, scale=1.0):
    pk = Pumpkins()
    p = Parts(seed=43, surfaces=True)
    for x, h, r, turn in ((-0.75, 1.0, 0.26, 0.25), (0.0, 1.35, 0.32, 0.0), (0.75, 0.95, 0.24, -0.3)):
        _tube(p, (x, 0, 0), (x, 0, h), 0.03, 0.025, IRON)                             # the iron stake
        _tube(p, (x, 0, h - 0.12), (x, 0, h), 0.03, r * 0.55, IRON)                    # the cup it holds the pumpkin in
        top = pk.add((x, 0, h + r * SQ * 0.8), r, turn, "angry")
        _stem(p, top, r * 1.3, turn=1 if x <= 0 else -1)
    return [pk.finish(col, name, pos, rot_z, scale)] + p.finish(col, name, pos, rot_z, scale)


def _smooth_paint(p, faces, color_at):
    for f in faces:
        f.smooth = True
        for lp in f.loops:
            lp[p.lay] = (*color_at(lp.vert.co), SURFACE["plain"])


def _candle(p, x, y, h, r, seed):
    """A fat church candle burnt down unevenly: turned in one piece with a rounded, lumpy melted rim
    round a hollow top, wax run down its sides in drips ending in beads, a pool of wax at its foot, the
    wick and its flame. Paler toward the flame."""
    bm = p.body
    prof = [(0.0, 0.0), (r * 1.55, 0.0), (r * 1.4, 0.02), (r * 1.05, 0.035), (r, 0.08), (r, h * 0.5), (r * 0.99, h - 0.07),
            (r * 1.06, h - 0.03), (r * 1.03, h + 0.005), (r * 0.82, h + 0.012), (r * 0.62, h - 0.025), (0.0, h - 0.035)]
    n = 16
    rings = []
    for i in range(n):
        a = 2 * math.pi * i / n
        wob = 1 + 0.035 * math.sin(3 * a + seed) + 0.02 * math.sin(5 * a + 2 * seed)
        ring = []
        for j, (rr, z) in enumerate(prof):
            if j >= 6:                                                           # the rim burns down unevenly
                z += 0.035 * math.sin(2 * a + seed) + 0.015 * math.sin(4 * a + seed * 3)
            ring.append(bm.verts.new((x + math.cos(a) * rr * wob, y + math.sin(a) * rr * wob, z)))
        rings.append(ring)
    faces = []
    for i in range(n):
        A, B = rings[i], rings[(i + 1) % n]
        for j in range(len(prof) - 1):
            try:
                faces.append(bm.faces.new((A[j], B[j], B[j + 1], A[j + 1])))
            except ValueError:
                pass
    bmesh.ops.remove_doubles(bm, verts=[v for ring in rings for v in ring], dist=1e-5)
    faces = [f for f in faces if f.is_valid]
    _smooth_paint(p, faces, lambda co: props.lerp(WAX_LO, WAX_HI, max(0.0, min(1.0, co.z / h)) ** 0.7))
    for k in range(7):                                                          # drips, each ending in a bead
        a = k * 0.9 + seed * 3
        ln = h * (0.2 + 0.55 * ((k * 0.618 + seed) % 1.0))
        wr = r * (0.13 + 0.09 * ((k * 0.37 + seed) % 1.0))
        z0 = h - 0.02 + 0.035 * math.sin(2 * a + seed)
        c0 = Vector((x + math.cos(a) * r * 1.02, y + math.sin(a) * r * 1.02, z0))
        c1 = c0 - Vector((0, 0, ln))
        vs = props.tube(bm, c0, c1, wr, wr * 0.75, 6) + props.ball(bm, c1, wr * 1.15, 6)
        _smooth_paint(p, list({f for v in vs for f in v.link_faces}),
                      lambda co: props.lerp(WAX_LO, WAX_HI, max(0.0, min(1.0, co.z / h)) ** 0.6))
    _tube(p, (x, y, h - 0.03), (x + 0.008, y, h + 0.05), 0.009, 0.007, (0.08, 0.06, 0.05), sides=4)  # the wick
    _flame(p, (x + 0.008, y, h + 0.035), r * 0.36, r * 1.8)


def grave_candles(col, name, pos, rot_z=0.0, scale=1.0):
    p = Parts(seed=44, surfaces=True)
    # an old headstone, its top rounded and chipped on one shoulder, cracked, moss at its foot
    w, h = 0.78, 1.12
    prof = [(-w / 2, 0.0), (w / 2, 0.0)]
    for k in range(13):
        a = k * math.pi / 12
        u, v = w / 2 * math.cos(a), h - w / 2 + w / 2 * math.sin(a) * 0.75
        if 2 <= k <= 3:                                                          # the chip
            u, v = u * 0.93, v - 0.06
        prof.append((u + 0.01 * math.sin(k * 3.1), v + 0.012 * math.cos(k * 2.3)))
    sides, caps = p.prism(prof, 0.16, 0.36, HEADSTONE)
    edges = list({e for f in sides + caps for e in f.edges})
    ret = bmesh.ops.bevel(p.body, geom=edges, offset=0.03, segments=2, affect="EDGES", profile=0.5, clamp_overlap=True)
    del ret
    p._paint(p.body, p.lay, list(p.body.faces), HEADSTONE, 0.04, kind="rock")    # (it is the first thing built)
    p.box((0, 0.26, 0.05), (0.98, 0.42, 0.1), landmarks.QUOIN)                  # its footing
    for (x0, z0), (x1, z1) in (((0.12, 1.02), (0.02, 0.78)), ((0.02, 0.78), (0.1, 0.6)), ((0.1, 0.6), (0.0, 0.42)),
                               ((-0.28, 0.66), (-0.16, 0.5)), ((-0.16, 0.5), (-0.22, 0.36))):    # cracks
        _tube(p, (x0, 0.157, z0), (x1, 0.157, z1), 0.008, 0.006, CRACK, sides=4)
    for k in range(7):                                                           # moss at its foot
        _ball(p, (-0.36 + k * 0.12, 0.15, 0.1 + 0.03 * (k % 2)), 0.06 + 0.02 * (k % 3), MOSS, seg=6,
              kind="leaf", squash=0.6)
    # fat candles of different heights round its foot, tallest at the sides, as in the picture
    for k, (x, y, hh, r) in enumerate(((-0.58, -0.06, 0.66, 0.15), (-0.33, -0.36, 0.42, 0.15),
                                       (-0.04, -0.52, 0.24, 0.13), (0.26, -0.4, 0.36, 0.14),
                                       (0.55, -0.12, 0.56, 0.15), (0.74, 0.22, 0.3, 0.12))):
        _candle(p, x, y, hh, r, seed=k * 1.7)
    # the wax has run together into one puddle in front of the stone
    vs = props.ball(p.body, (0.08, -0.25, 0.0), 1.0, 12)
    for v in vs:
        v.co = Vector((0.08 + (v.co.x - 0.08) * 0.85, -0.25 + (v.co.y + 0.25) * 0.4, max(0.0, v.co.z) * 0.02))
    p._paint(p.body, p.lay, list({f for v in vs for f in v.link_faces}), WAX_LO, 0.05, kind="plain")
    return p.finish(col, name, pos, rot_z, scale)
