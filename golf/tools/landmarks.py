"""Low-poly landmarks from Marc's concept sheets (art_src/redesign/02_Landmark_Concept_Sheets), built in
headless Blender (bpy) for build_hole.py. Simple shapes, painted in vertex colours like props.py, with
the windows and lamps on a separate glowing material so they read at night from across the hole.

Each builder takes the collection, a name, the ground position (course coords: x right, y down-range,
z up), a turn about z (0: the front faces down-range, -y... i.e. back toward the tee) and a scale, and
returns the objects it made plus a footprint [half_x, half_y] for the ball's collision box.
"""
import math
import random

import bmesh
from mathutils import Matrix, Vector

import props

WOOD_RED = (0.42, 0.11, 0.09)
TRIM = (0.82, 0.78, 0.7)
STONE = (0.36, 0.35, 0.38)
ROOF = (0.22, 0.27, 0.31)
SILO = (0.62, 0.58, 0.5)
IRON = (0.3, 0.3, 0.32)
GLOW = (1.0, 0.68, 0.28)


class Parts:
    """One bmesh for the painted body and one for the glowing bits, built up part by part."""

    def __init__(self, seed=1):
        self.body = bmesh.new()
        self.glow = bmesh.new()
        self.rng = random.Random(seed)
        self.lay = props.vcol_layer(self.body)
        self.glay = props.vcol_layer(self.glow)

    def _paint(self, bm, lay, faces, color, jitter=0.06):
        for f in faces:
            k = 1.0 + self.rng.uniform(-jitter, jitter)
            c = tuple(min(1.0, v * k) for v in color)
            for lp in f.loops:
                lp[lay] = (*c, 1.0)

    def box(self, center, size, color, glow=False, jitter=0.06):
        bm = self.glow if glow else self.body
        ret = bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=Vector(size), verts=ret["verts"])
        bmesh.ops.translate(bm, vec=Vector(center), verts=ret["verts"])
        faces = list({f for v in ret["verts"] for f in v.link_faces})
        self._paint(bm, self.glay if glow else self.lay, faces, color, jitter)

    def prism(self, profile, y0, y1, color, caps_color=None):
        """A shape extruded along y from y0 to y1; profile: [(x, z), ...] counter-clockwise seen from -y."""
        bm = self.body
        a = [bm.verts.new((x, y0, z)) for x, z in profile]
        b = [bm.verts.new((x, y1, z)) for x, z in profile]
        n = len(profile)
        sides = [bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i])) for i in range(n)]
        caps = [bm.faces.new(list(reversed(a))), bm.faces.new(b)]
        self._paint(bm, self.lay, sides, color)
        self._paint(bm, self.lay, caps, caps_color or color)
        return sides, caps

    def cylinder(self, base, r, h, color, segments=12, glow=False):
        bm = self.glow if glow else self.body
        ret = bmesh.ops.create_cone(bm, cap_ends=True, segments=segments, radius1=r, radius2=r, depth=h)
        bmesh.ops.translate(bm, vec=Vector(base) + Vector((0, 0, h / 2)), verts=ret["verts"])
        faces = list({f for v in ret["verts"] for f in v.link_faces})
        self._paint(bm, self.glay if glow else self.lay, faces, color)

    def cone(self, base, r, h, color, segments=12):
        ret = bmesh.ops.create_cone(self.body, cap_ends=True, segments=segments, radius1=r, radius2=0.0, depth=h)
        bmesh.ops.translate(self.body, vec=Vector(base) + Vector((0, 0, h / 2)), verts=ret["verts"])
        faces = list({f for v in ret["verts"] for f in v.link_faces})
        self._paint(self.body, self.lay, faces, color)

    def quad(self, corners, color, glow=False):
        bm = self.glow if glow else self.body
        f = bm.faces.new([bm.verts.new(c) for c in corners])
        self._paint(bm, self.glay if glow else self.lay, [f], color, 0.0)

    def finish(self, col, name, pos, rot_z, scale):
        m = Matrix.Translation(Vector(pos)) @ Matrix.Rotation(rot_z, 4, "Z") @ Matrix.Scale(scale, 4)
        obs = []
        for bm, mat, suffix in ((self.body, props.material("LandmarkBody", 0.85), ""),
                                (self.glow, props.material("LandmarkGlow", 0.6, emit=GLOW, strength=3.0), "_Glow")):
            if not bm.faces:
                bm.free()
                continue
            bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            obs.append(props.link(name + suffix, bm, [mat], col))
        return obs


def _window(p, x, y, z, w, h, facing):
    """A lit window on a wall at y (facing -1: the front, +1: the back) or, facing 'x', on a side wall at x."""
    d = 0.05                     # the pane stands just proud of its frame, which is flush with the wall
    if facing in (-1, 1):
        yy = y + facing * d
        p.quad([(x - w / 2, yy, z), (x + w / 2, yy, z), (x + w / 2, yy, z + h), (x - w / 2, yy, z + h)], GLOW, glow=True)
        p.box((x, y, z + h / 2), (w + 0.2, 0.06, h + 0.2), TRIM)
    else:
        sx = 1 if facing == "x+" else -1
        xx = x + sx * d
        p.quad([(xx, y - w / 2, z), (xx, y + w / 2, z), (xx, y + w / 2, z + h), (xx, y - w / 2, z + h)], GLOW, glow=True)
        p.box((x, y, z + h / 2), (0.06, w + 0.2, h + 0.2), TRIM)


def barn(col, name, pos, rot_z=0.0, scale=1.0):
    """Barn and silo (concept A): a red board barn on a stone footing with a gambrel roof and a cupola,
    white X-braced doors under a lamp, lit windows, and a tall wooden silo with iron bands and a cone
    roof beside it. ~10 m wide, 14 m deep; the front (doors) faces -y."""
    p = Parts(seed=505)
    W, D, H = 10.0, 14.0, 4.6
    hw, hd = W / 2, D / 2
    p.box((0, 0, 0.3), (W + 0.3, D + 0.3, 0.6), STONE)                       # footing
    p.box((0, 0, 0.6 + H / 2), (W, D, H), WOOD_RED, jitter=0.1)             # walls
    # the gambrel roof over the walls, its gable ends walled in red
    roof = [(-hw - 0.5, 0.6 + H - 0.1), (hw + 0.5, 0.6 + H - 0.1), (hw - 0.9, 0.6 + H + 2.4),
            (0, 0.6 + H + 4.1), (-hw + 0.9, 0.6 + H + 2.4)]
    sides, caps = p.prism(roof, -hd - 0.4, hd + 0.4, ROOF, caps_color=WOOD_RED)
    gable = [(-hw, 0.6 + H), (hw, 0.6 + H), (hw - 1.0, 0.6 + H + 2.3), (0, 0.6 + H + 3.85), (-hw + 1.0, 0.6 + H + 2.3)]
    p.prism(gable, -hd - 0.02, hd + 0.02, WOOD_RED)
    # cupola on the ridge
    top = 0.6 + H + 4.1
    p.box((0, 0, top + 0.5), (1.2, 1.2, 1.2), WOOD_RED)
    p.prism([(-0.95, top + 1.1), (0.95, top + 1.1), (0, top + 1.9)], -0.95, 0.95, ROOF)
    # big doors: white frame, red panels, an X across each
    dz = 0.6
    for sx in (-1, 1):
        cx = sx * 1.45
        p.box((cx, -hd - 0.05, dz + 1.7), (2.8, 0.1, 3.4), TRIM)
        p.box((cx, -hd - 0.1, dz + 1.7), (2.4, 0.06, 3.0), WOOD_RED)
        for k in (-1, 1):
            ang = k * math.atan2(3.0, 2.4)
            bar = bmesh.ops.create_cube(p.body, size=1.0)
            bmesh.ops.scale(p.body, vec=Vector((3.84, 0.06, 0.22)), verts=bar["verts"])
            bmesh.ops.rotate(p.body, cent=Vector((0, 0, 0)), matrix=Matrix.Rotation(ang, 3, "Y"), verts=bar["verts"])
            bmesh.ops.translate(p.body, vec=Vector((cx, -hd - 0.15, dz + 1.7)), verts=bar["verts"])
            p._paint(p.body, p.lay, list({f for v in bar["verts"] for f in v.link_faces}), TRIM)
    # the lamp over the doors, and the windows
    p.box((0, -hd - 0.35, dz + 3.75), (0.35, 0.35, 0.35), GLOW, glow=True)
    p.box((0, -hd - 0.15, dz + 3.95), (0.7, 0.3, 0.12), IRON)
    _window(p, 0, -hd - 0.4, 0.6 + H + 0.8, 1.5, 1.4, -1)                     # hay-loft window, on the roof's end
    for sx in (-1, 1):
        _window(p, sx * 3.85, -hd, dz + 1.6, 0.8, 0.9, -1)
        for wy in (-3.5, 1.0, 5.0):
            _window(p, sx * hw, wy, dz + 1.6, 0.9, 0.9, "x+" if sx > 0 else "x-")
    # the silo, close by the barn's right side
    sx, sy, r, sh = hw + 2.6, 2.0, 2.1, 12.5
    p.cylinder((sx, sy, 0), r + 0.2, 0.6, STONE)
    p.cylinder((sx, sy, 0.6), r, sh, SILO)
    for bz in (2.5, 5.5, 8.5, 11.5):
        p.cylinder((sx, sy, bz), r + 0.06, 0.18, IRON)
    p.cone((sx, sy, 0.6 + sh), r + 0.35, 2.6, ROOF)
    _window(p, sx, sy - r, 0.6 + sh - 2.2, 0.5, 0.9, -1)
    obs = p.finish(col, name, pos, rot_z, scale)
    return obs, [(hw + 5.0) * scale, (hd + 0.5) * scale]
