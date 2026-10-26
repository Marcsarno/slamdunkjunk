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
STAINED = (0.95, 0.18, 0.32)     # a chapel's rose window: red-violet glass lit from inside


class Parts:
    """One bmesh for the painted body and one for the glowing bits, built up part by part."""

    def __init__(self, seed=1):
        self.body = bmesh.new()
        self.glow = bmesh.new()
        self.rng = random.Random(seed)
        self.lay = props.vcol_layer(self.body)
        self.glay = props.vcol_layer(self.glow)
        self.stain = bmesh.new()
        self.slay = props.vcol_layer(self.stain)

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

    def cone(self, base, r, h, color, segments=12, turn=0.0):
        ret = bmesh.ops.create_cone(self.body, cap_ends=True, segments=segments, radius1=r, radius2=0.0, depth=h)
        if turn:
            bmesh.ops.rotate(self.body, cent=Vector((0, 0, 0)), matrix=Matrix.Rotation(turn, 3, "Z"), verts=ret["verts"])
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
                                (self.glow, props.material("LandmarkGlow", 0.6, emit=GLOW, strength=3.0), "_Glow"),
                                (self.stain, props.material("LandmarkStained", 0.6, emit=STAINED, strength=2.5), "_Stained")):
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


SIDING = (0.3, 0.33, 0.28)        # weathered grey-green boards
SLATE = (0.2, 0.24, 0.29)
DOOR = (0.28, 0.16, 0.1)
CHIMNEY = (0.36, 0.22, 0.18)


def _prism_x(p, profile, x0, x1, color, caps_color=None):
    """A shape extruded along x from x0 to x1; profile: [(y, z), ...]."""
    bm = p.body
    a = [bm.verts.new((x0, y, z)) for y, z in profile]
    b = [bm.verts.new((x1, y, z)) for y, z in profile]
    n = len(profile)
    sides = [bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i])) for i in range(n)]
    caps = [bm.faces.new(list(reversed(a))), bm.faces.new(b)]
    p._paint(bm, p.lay, sides, color)
    p._paint(bm, p.lay, caps, caps_color or color)


def mansion(col, name, pos, rot_z=0.0, scale=1.0):
    """The vampire's house (concept B): two storeys of grey-green boards on a stone footing under a slate
    gable roof with a dormer, an eight-sided tower with a spire on its left, a porch with a little gable
    over the door, a brick chimney, and lit windows on both floors. ~19 m wide; the front faces -y."""
    p = Parts(seed=707)
    W, D, H = 14.0, 10.0, 7.0
    hw, hd = W / 2, D / 2
    base = 0.8
    p.box((0, 0, base / 2), (W + 0.4, D + 0.4, base), STONE)
    p.box((0, 0, base + H / 2), (W, D, H), SIDING, jitter=0.08)
    p.box((0, 0, base + H / 2), (W + 0.12, D + 0.12, 0.25), TRIM)                # the band between floors
    top = base + H
    _prism_x(p, [(-hd - 0.6, top - 0.1), (hd + 0.6, top - 0.1), (0, top + 4.6)], -hw - 0.5, hw + 0.5, SLATE, SIDING)
    _prism_x(p, [(-hd + 0.05, top), (hd - 0.05, top), (0, top + 4.3)], -hw + 0.02, hw - 0.02, SIDING)
    # a dormer on the front slope
    p.box((2.5, -hd + 1.6, top + 1.6), (1.8, 1.6, 1.6), SIDING)
    _prism_x(p, [(-hd + 0.7, top + 2.4), (-hd + 2.5, top + 2.4), (-hd + 1.6, top + 3.3)], 1.4, 3.6, SLATE)
    _window(p, 2.5, -hd + 0.8, top + 1.0, 0.8, 1.0, -1)
    # chimney
    p.box((4.8, 1.5, top + 3.0), (1.1, 1.1, 5.0), CHIMNEY)
    # the tower: eight-sided, three storeys, a tall slate spire
    tx, ty, tr = -hw - 1.4, -hd + 2.6, 2.7
    p.cylinder((tx, ty, 0), tr + 0.2, base, STONE, segments=8)
    p.cylinder((tx, ty, base), tr, 11.5, SIDING, segments=8)
    p.cone((tx, ty, base + 11.5), tr + 0.5, 6.0, SLATE, segments=8)
    p.cylinder((tx, ty, base + 17.3), 0.08, 1.2, IRON, segments=4)
    for z in (base + 1.4, base + 4.8, base + 8.2):
        _window(p, tx, ty - tr * 0.92, z, 0.8, 1.6, -1)
    # porch: a deck, two posts, a roof and a little gable over the door
    px, pw, pd = 1.2, 4.2, 2.4
    p.box((px, -hd - pd / 2, base * 0.6), (pw, pd, 0.25), STONE)
    for sx in (-1, 1):
        p.box((px + sx * (pw / 2 - 0.25), -hd - pd + 0.25, base + 1.4), (0.25, 0.25, 2.8), TRIM)
    p.box((px, -hd - pd / 2, base + 2.9), (pw + 0.3, pd + 0.3, 0.2), SLATE)
    _prism_x(p, [(-hd - pd - 0.1, base + 3.0), (-hd + 0.1, base + 3.0), (-hd - pd / 2, base + 4.3)],
             px - pw / 2 - 0.1, px + pw / 2 + 0.1, SLATE, TRIM)
    p.box((px, -hd - 0.06, base + 1.15), (1.2, 0.12, 2.3), DOOR)
    p.box((px, -hd - 0.4, base + 2.6), (0.25, 0.25, 0.25), GLOW, glow=True)       # porch lamp
    # windows: ground floor either side of the porch, upstairs across the front, and down the sides
    for x in (-4.6, -2.0, 4.4):
        _window(p, x, -hd, base + 1.2, 1.1, 1.6, -1)
    for x in (-4.6, -1.6, 1.6, 4.6):
        _window(p, x, -hd, base + H / 2 + 1.0, 1.0, 1.5, -1)
    for sx in (-1, 1):
        for y in (-2.0, 2.0):
            for z in (base + 1.2, base + H / 2 + 1.0):
                _window(p, sx * hw, y, z, 1.0, 1.5, "x+" if sx > 0 else "x-")
    obs = p.finish(col, name, pos, rot_z, scale)
    return obs, [(hw + 4.5) * scale, (hd + 3.0) * scale]


def pillar(col, name, pos, rot_z=0.0, scale=1.0):
    """A stone gate pillar with a cap and a slab on top for a gargoyle to sit on (3.2 m tall)."""
    p = Parts(seed=17)
    p.box((0, 0, 0.2), (1.5, 1.5, 0.4), STONE)
    p.box((0, 0, 1.75), (1.1, 1.1, 2.7), STONE, jitter=0.1)
    p.box((0, 0, 3.2), (1.45, 1.45, 0.3), STONE)
    obs = p.finish(col, name, pos, rot_z, scale)
    return obs, [0.75 * scale, 0.75 * scale]


def hedge(col, name, points, height_at, height=2.4, width=1.3):
    """A clipped hedge wall along a polyline, a box per stretch standing on the ground. Returns the
    boxes ([cx, cy, cz, length, width, height, rot]) for the ball to bounce off."""
    bm = bmesh.new()
    lay = props.vcol_layer(bm)
    rng = random.Random(len(points))
    boxes = []
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy)
        steps = max(1, int(ln / 6.0))                  # short boxes follow the ground's rise and fall
        for k in range(steps):
            a = k / steps
            b = (k + 1) / steps
            ax, ay = x0 + dx * a, y0 + dy * a
            bx, by = x0 + dx * b, y0 + dy * b
            cx, cy = (ax + bx) / 2, (ay + by) / 2
            z0 = min(height_at(ax, ay), height_at(bx, by)) - 0.3
            seg = ln / steps + width * 0.5
            ret = bmesh.ops.create_cube(bm, size=1.0)
            bmesh.ops.scale(bm, vec=Vector((seg, width, height + 0.3)), verts=ret["verts"])
            bmesh.ops.rotate(bm, cent=Vector((0, 0, 0)), matrix=Matrix.Rotation(math.atan2(dy, dx), 3, "Z"), verts=ret["verts"])
            bmesh.ops.translate(bm, vec=Vector((cx, cy, z0 + (height + 0.3) / 2)), verts=ret["verts"])
            for f in {f for v in ret["verts"] for f in v.link_faces}:
                shade = 0.85 + rng.uniform(-0.08, 0.08) + (0.12 if f.normal.z > 0.5 else 0.0)
                for lp in f.loops:
                    lp[lay] = (0.16 * shade, 0.3 * shade, 0.14 * shade, 1.0)
            boxes.append([cx, cy, z0 + 0.3, seg, width, height, math.atan2(dy, dx)])
    bm.normal_update()
    props.link(name, bm, [props.material("hedge_vc", 0.9)], col)
    return boxes


CHAPEL_STONE = (0.44, 0.43, 0.52)   # lavender-grey stone in the moonlight (concept: the Forgotten Chapel)
QUOIN = (0.3, 0.3, 0.37)
CHAPEL_ROOF = (0.36, 0.2, 0.52)     # purple slate
SLATE_LINE = (0.24, 0.13, 0.34)
OAK = (0.36, 0.21, 0.1)
LEAVES = (0.55, 0.16, 0.06)


def _arch(p, x, y, z, w, h, facing, frame=QUOIN, glow=True, tracery=False):
    """A pointed-arch opening on a wall: a lit pane (or a dark recess, glow=False) with a stone frame,
    and with tracery=True a stone mullion and transom across the glass.
    facing -1 / +1: on a wall at y (front / back); 'x-' / 'x+': on a side wall at x."""
    tip = w * 0.75
    d = 0.06
    if facing in (-1, 1):
        yy = y + facing * d
        pts = [(x - w / 2, yy, z), (x + w / 2, yy, z), (x + w / 2, yy, z + h), (x, yy, z + h + tip), (x - w / 2, yy, z + h)]
        p.box((x, y, z + (h + tip) / 2), (w + 0.4, 0.1, h + tip + 0.3), frame)
        if tracery:
            p.box((x, yy + facing * 0.04, z + (h + tip * 0.7) / 2), (0.09, 0.06, h + tip * 0.7), frame)
            p.box((x, yy + facing * 0.04, z + h * 0.62), (w, 0.06, 0.09), frame)
    else:
        sx = 1 if facing == "x+" else -1
        xx = x + sx * d
        pts = [(xx, y - w / 2, z), (xx, y + w / 2, z), (xx, y + w / 2, z + h), (xx, y, z + h + tip), (xx, y - w / 2, z + h)]
        p.box((x, y, z + (h + tip) / 2), (0.1, w + 0.4, h + tip + 0.3), frame)
        if tracery:
            p.box((xx + sx * 0.04, y, z + (h + tip * 0.7) / 2), (0.06, 0.09, h + tip * 0.7), frame)
            p.box((xx + sx * 0.04, y, z + h * 0.62), (0.06, w, 0.09), frame)
    if glow:
        p.quad(pts, GLOW, glow=True)
    else:
        p.quad(pts, (0.04, 0.03, 0.05))


def _slope_strip(p, eave, ridge, ya, yb, u, du, color, lift=0.03):
    """A strip across a roof slope from eave (x, z) toward ridge (x, z), from u to u + du of the way up,
    standing `lift` off it (a course of slates, a missing patch)."""
    (xe, ze), (xr, zr) = eave, ridge
    nx, nz = (zr - ze), -(xr - xe)                       # outward normal of the slope (in x, z)
    ln = (nx * nx + nz * nz) ** 0.5
    if nz < 0:
        nx, nz = -nx, -nz
    nx, nz = nx / ln * lift, nz / ln * lift
    a = (xe + (xr - xe) * u + nx, ze + (zr - ze) * u + nz)
    b = (xe + (xr - xe) * (u + du) + nx, ze + (zr - ze) * (u + du) + nz)
    corners = [(a[0], ya, a[1]), (a[0], yb, a[1]), (b[0], yb, b[1]), (b[0], ya, b[1])]
    p.quad(corners if xe > xr else corners[::-1], color)


def _gable_y(p, x0, x1, y0, y1, z, rise, color, caps_color=None):
    """A gable roof whose ridge runs along y, eaves at x0 and x1."""
    return p.prism([(x0, z), (x1, z), ((x0 + x1) / 2, z + rise)], y0, y1, color, caps_color)


def chapel(col, name, pos, rot_z=0.0, scale=1.0):
    """The Forgotten Chapel (Marc's concept, art_src/landmarks/chapel_concept.png): a small stone chapel,
    a steep purple slate roof with slates missing, darker quoin buttresses down its sides, a square bell
    tower on the front with an open belfry, a bell and a slate spire with an iron cross; a red rose
    window over the pointed door (ajar, candlelit), tall lit lancet windows, a broken wall and stones
    at its foot. ~8 m wide, 15 m long, 17 m to the cross; the front faces -y."""
    p = Parts(seed=303)
    W, L, H = 8.0, 13.0, 5.6
    hw = W / 2
    y0, y1 = -L / 2, L / 2
    p.box((0, 0, 0.25), (W + 0.6, L + 0.6, 0.5), QUOIN)                           # footing
    p.box((0, 0, 0.5 + H / 2), (W, L, H), CHAPEL_STONE, jitter=0.1)
    top = 0.5 + H
    _gable_y(p, -hw - 0.5, hw + 0.5, y0 - 0.3, y1 + 0.4, top - 0.1, 5.2, CHAPEL_ROOF, CHAPEL_STONE)
    _gable_y(p, -hw + 0.05, hw - 0.05, y0 + 0.02, y1 - 0.02, top, 4.9, CHAPEL_STONE)  # the gable walls under it
    # missing slates: dark gaps on both slopes
    k = 5.2 / (hw + 0.5)
    for sx, yy, u in ((1, -1.5, 0.45), (1, 2.8, 0.7), (-1, 0.6, 0.35), (-1, 4.2, 0.6)):
        xa, xb = sx * (hw + 0.5) * (1 - u), sx * (hw + 0.5) * (1 - u - 0.14)
        za, zb = top - 0.08 + (hw + 0.5 - abs(xa)) * k, top - 0.08 + (hw + 0.5 - abs(xb)) * k
        n = 0.03 * sx
        p.quad([(xa + n, yy - 0.5, za + 0.03), (xa + n, yy + 0.5, za + 0.03), (xb + n, yy + 0.5, zb + 0.03),
                (xb + n, yy - 0.5, zb + 0.03)][:: sx], (0.05, 0.03, 0.06))
    for sx in (-1, 1):
        eave, ridge = (sx * (hw + 0.5), top - 0.1), (0.0, top - 0.1 + 5.2)
        for u in (0.1, 0.27, 0.44, 0.61, 0.78):
            _slope_strip(p, eave, ridge, y0 - 0.25, y1 + 0.35, u, 0.035, SLATE_LINE, 0.02)
    p.box((0, y1 + 0.2, top + 5.4), (0.1, 0.1, 0.9), IRON)                              # the back gable's cross
    p.box((0, y1 + 0.2, top + 5.6), (0.5, 0.1, 0.1), IRON)
    # stone blocks standing a little proud on the walls, lighter and darker, round the windows
    for sx in (-1, 1):
        for k in range(16):
            yy = p.rng.uniform(y0 + 0.6, y1 - 0.6)
            zz = p.rng.uniform(0.8, top - 0.5)
            if min(abs(yy - c) for c in (-4.2, 0.2, 4.6)) < 1.0 and 1.2 < zz < 4.6:
                continue
            shade = p.rng.choice((0.85, 1.12))
            p.box((sx * (hw + 0.02), yy, zz), (0.06, p.rng.uniform(0.6, 1.1), 0.36),
                  tuple(c * shade for c in CHAPEL_STONE))
    # buttresses: darker stone piers between the windows and at the corners
    for yy in (y0 + 0.3, -2.0, 2.4, y1 - 0.3):
        for sx in (-1, 1):
            p.box((sx * (hw + 0.25), yy, 0.5 + H * 0.45), (0.7, 0.9, H * 0.9), QUOIN, jitter=0.1)
    # tall lit lancets down each side, between the buttresses
    for yy in (-4.2, 0.2, 4.6):
        for sx in (-1, 1):
            _arch(p, sx * hw, yy, 1.6, 1.0, 2.2, "x+" if sx > 0 else "x-", tracery=True)
    # the tower on the front: square, a belfry with open arches, a bell, a slate spire and a cross
    T, ty, th = 4.0, y0 - 1.6, 11.0
    p.box((0, ty, 0.25), (T + 0.6, T + 0.6, 0.5), QUOIN)
    p.box((0, ty, 0.5 + 6.3 / 2), (T, T, 6.3), CHAPEL_STONE, jitter=0.1)
    for sx in (-1, 1):                                                             # corner quoins
        for sy in (-1, 1):
            p.box((sx * (T / 2 - 0.15), ty + sy * (T / 2 - 0.15), 0.5 + 6.3 / 2), (0.42, 0.42, 6.35), QUOIN)
    bz = 0.5 + 6.3
    p.box((0, ty, bz + 0.15), (T + 0.4, T + 0.4, 0.3), QUOIN)                       # the ledge under the belfry
    for sx in (-1, 1):                                                             # belfry corner piers
        for sy in (-1, 1):
            p.box((sx * (T / 2 - 0.45), ty + sy * (T / 2 - 0.45), bz + 1.75), (0.9, 0.9, 3.2), CHAPEL_STONE)
    p.box((0, ty, bz + 3.5), (T + 0.2, T + 0.2, 0.5), CHAPEL_STONE)                 # the belfry's lintel
    p.box((0, ty, bz + 3.82), (T + 0.5, T + 0.5, 0.18), QUOIN)
    zt = bz + 3.25                                                                  # the openings' heads
    o = T / 2 - 0.9
    for side in (-1, 1):                                                             # front and back faces
        for sx in (-1, 1):
            p.prism([(sx * o, zt - 1.2), (sx * o, zt), (0.0, zt)][:: -sx], ty + side * (T / 2) - 0.25,
                    ty + side * (T / 2) + 0.25, CHAPEL_STONE)
    for side in (-1, 1):                                                             # the two sides
        for sy in (-1, 1):
            _prism_x(p, [(ty + sy * o, zt - 1.2), (ty + sy * o, zt), (ty, zt)][:: sy], side * (T / 2) - 0.25,
                     side * (T / 2) + 0.25, CHAPEL_STONE)
    p.box((0, ty, bz + 0.45), (T - 1.6, T - 1.6, 0.3), QUOIN)                          # the belfry floor
    p.cylinder((0, ty, bz + 1.3), 0.58, 1.05, IRON, segments=8)                      # the bell
    p.cone((0, ty, bz + 2.35), 0.4, 0.4, IRON, segments=8)
    p.box((0, ty, bz + 2.85), (0.1, 0.1, 0.5), IRON)
    p.box((0, ty, bz + 3.05), (T - 1.4, 0.16, 0.16), OAK)                             # the beam it hangs from
    sz = bz + 3.9
    q = math.pi / 4
    p.cone((0, ty, sz - 0.1), (T + 1.0) / math.sqrt(2), 1.3, CHAPEL_ROOF, segments=4, turn=q)  # the flared skirt
    p.cone((0, ty, sz + 0.4), (T - 0.6) / math.sqrt(2), 6.2, CHAPEL_ROOF, segments=4, turn=q)  # the spire
    p.box((0, ty, sz + 7.1), (0.14, 0.14, 1.7), IRON)                                # the cross
    p.box((0, ty, sz + 7.5), (0.9, 0.14, 0.14), IRON)
    # the front: a pointed door ajar in candlelight, the rose window above it
    fy = ty - T / 2
    p.box((0, fy - 0.05, 1.7), (2.0, 0.12, 2.5), QUOIN)                              # door surround
    _arch(p, 0, fy - 0.08, 0.5, 1.5, 1.7, -1)                                        # the open doorway's light
    p.box((-0.55, fy - 0.35, 1.55), (0.12, 0.7, 2.1), OAK)                           # the door, swung half open
    rz = 4.5
    bm = p.stain
    ret = bmesh.ops.create_circle(bm, cap_ends=True, segments=16, radius=0.95)
    bmesh.ops.rotate(bm, cent=Vector((0, 0, 0)), matrix=Matrix.Rotation(math.pi / 2, 3, "X"), verts=ret["verts"])
    bmesh.ops.translate(bm, vec=Vector((0, fy - 0.16, rz)), verts=ret["verts"])
    p._paint(bm, p.slay, list({f for v in ret["verts"] for f in v.link_faces}), STAINED, 0.0)
    p.box((0, fy - 0.06, rz), (2.4, 0.1, 2.4), QUOIN)                                # its frame
    for ang in (0.0, math.pi / 4, math.pi / 2, 3 * math.pi / 4):     # its tracery: four spokes
        ret = bmesh.ops.create_cube(p.body, size=1.0)
        bmesh.ops.scale(p.body, vec=Vector((0.08, 0.04, 1.9)), verts=ret["verts"])
        bmesh.ops.rotate(p.body, cent=Vector((0, 0, 0)), matrix=Matrix.Rotation(ang, 3, "Y"), verts=ret["verts"])
        bmesh.ops.translate(p.body, vec=Vector((0, fy - 0.2, rz)), verts=ret["verts"])
        p._paint(p.body, p.lay, list({f for v in ret["verts"] for f in v.link_faces}), (0.12, 0.05, 0.1), 0.0)
    for sx in (-1, 1):
        _arch(p, sx * (hw - 1.1), y0, 1.6, 0.7, 1.9, -1)
    # red ivy: clumps grown up the tower's left corner, over the door, and up the nave's corners
    ivy = (LEAVES, (0.66, 0.24, 0.07), (0.45, 0.1, 0.07))
    for k in range(26):
        z = 0.5 + (k / 26) ** 0.8 * 8.4
        x = -T / 2 + 0.2 + p.rng.uniform(-0.45, 0.35) * (1.0 - z / 12)
        sz = p.rng.uniform(0.35, 0.75) * (1.0 - z / 14)
        p.box((x, fy - 0.12, z), (sz * 1.2, 0.12, sz), p.rng.choice(ivy), jitter=0.2)
        if k % 3 == 0:                                                               # round the corner, onto the side
            p.box((-T / 2 - 0.08, fy + 0.35 + p.rng.uniform(0, 0.6), z), (0.12, sz, sz), p.rng.choice(ivy), jitter=0.2)
    for k in range(7):
        p.box((-0.9 + 0.3 * k, fy - 0.15, 3.0 + 0.35 * math.sin(k * 0.9)), (0.4, 0.1, 0.35), p.rng.choice(ivy), jitter=0.2)
    for sx, yy in ((1, y0 + 0.2), (-1, y1 - 0.2), (1, 2.4)):
        for k in range(9):
            z = 0.6 + k * 0.5
            p.box((sx * (hw + 0.62), yy + p.rng.uniform(-0.4, 0.4), z), (0.1, p.rng.uniform(0.4, 0.8), 0.45),
                  p.rng.choice(ivy), jitter=0.2)
    # leaves drifted along the walls' feet
    for sx in (-1, 1):
        for k in range(10):
            p.box((sx * (hw + 0.8 + p.rng.uniform(0, 0.6)), p.rng.uniform(y0, y1), 0.08),
                  (p.rng.uniform(0.6, 1.1), p.rng.uniform(0.5, 0.9), 0.16), p.rng.choice(ivy), jitter=0.25)
    # low broken stone walls along both sides, with gaps
    for sx in (-1, 1):
        for ya, yb, h in ((y0 - 1.0, y0 + 3.5, 0.75), (y0 + 5.0, y0 + 8.6, 0.6), (y0 + 9.6, y1 + 0.6, 0.8)):
            p.box((sx * (hw + 2.2), (ya + yb) / 2, h / 2), (0.7, yb - ya, h), QUOIN, jitter=0.12)
    # steps and candles at the door
    p.box((0, fy - 0.7, 0.12), (2.6, 1.2, 0.24), QUOIN)
    p.box((0, fy - 1.3, 0.06), (3.0, 0.8, 0.12), QUOIN)
    for cx, cy in ((-0.9, fy - 0.6), (-0.65, fy - 0.85), (0.8, fy - 0.7), (1.0, fy - 0.45)):
        p.box((cx, cy, 0.38), (0.09, 0.09, 0.28), (0.9, 0.85, 0.75))
        p.box((cx, cy, 0.56), (0.07, 0.07, 0.09), GLOW, glow=True)
    # the broken wall and a few stones at its foot, and fallen leaves
    for x, y, w, h in ((-5.6, y0 - 1.0, 2.6, 0.8), (-6.2, -1.5, 0.6, 0.6), (5.9, y0 + 0.5, 0.6, 0.9),
                       (6.0, 3.0, 0.6, 0.5), (3.2, y0 - 2.6, 1.8, 0.6), (-3.4, y0 - 2.8, 1.2, 0.5)):
        p.box((x, y, h / 2), (w if w > 1 else 0.6, w if w <= 1 else 0.6, h), QUOIN, jitter=0.12)
    for k, (x, y) in enumerate(((-2.6, fy - 1.6), (2.4, fy - 1.9), (-5.0, 2.0), (5.2, -3.6), (-5.4, 5.2))):
        if k % 2 == 0:                                                               # a slab with a rounded top
            p.box((x, y, 0.5), (0.75, 0.22, 1.0), CHAPEL_STONE, jitter=0.1)
            p.box((x, y, 1.06), (0.58, 0.22, 0.13), CHAPEL_STONE)                       # its rounded shoulders
            p.box((x, y, 1.15), (0.34, 0.22, 0.08), CHAPEL_STONE)
            p.box((x, y - 0.13, 0.75), (0.07, 0.04, 0.5), QUOIN)                          # its carved cross
            p.box((x, y - 0.13, 0.85), (0.32, 0.04, 0.07), QUOIN)
        else:                                                                        # a stone cross
            p.box((x, y, 0.65), (0.22, 0.22, 1.3), CHAPEL_STONE, jitter=0.1)
            p.box((x, y, 1.0), (0.75, 0.22, 0.22), CHAPEL_STONE)
    for k in range(18):
        a = k * 2.4
        r = 4.6 + (k % 4) * 0.9
        p.box((math.cos(a) * r, math.sin(a) * r * 1.4, 0.06), (0.9, 0.7, 0.12), LEAVES, jitter=0.25)
    obs = p.finish(col, name, pos, rot_z, scale)
    return obs, [(hw + 1.0) * scale, (L / 2 + T + 0.5) * scale]


HOUSE_SIDING = (0.86, 0.8, 0.67)     # warm cream clapboard (concept: the Homecoming House)
CLAP_LINE = (0.62, 0.57, 0.5)
POT = (0.5, 0.24, 0.13)
HOUSE_ROOF = (0.3, 0.2, 0.4)         # dusky plum shingles
SHUTTER = (0.1, 0.22, 0.2)
RED_DOOR = (0.55, 0.07, 0.06)
BRICK = (0.48, 0.2, 0.13)
PUMPKIN = (0.85, 0.36, 0.06)
BLACK = (0.04, 0.035, 0.05)


def _shuttered(p, x, y, z, w, h, facing):
    """A lit window with white glazing bars and dark green shutters either side."""
    _window(p, x, y, z, w, h, facing)
    if facing in (-1, 1):
        for sx in (-1, 1):
            p.box((x + sx * (w / 2 + 0.32), y + facing * 0.06, z + h / 2), (0.42, 0.08, h + 0.1), SHUTTER)
        p.box((x, y + facing * 0.1, z + h / 2), (0.06, 0.04, h), TRIM)
        p.box((x, y + facing * 0.1, z + h * 0.52), (w, 0.04, 0.06), TRIM)
    else:
        sx = 1 if facing == "x+" else -1
        for sy in (-1, 1):
            p.box((x + sx * 0.06, y + sy * (w / 2 + 0.32), z + h / 2), (0.08, 0.42, h + 0.1), SHUTTER)
        p.box((x + sx * 0.1, y, z + h / 2), (0.04, 0.06, h), TRIM)
        p.box((x + sx * 0.1, y, z + h * 0.52), (0.04, w, 0.06), TRIM)


def house(col, name, pos, rot_z=0.0, scale=1.0):
    """The Homecoming House (Marc's concept, art_src/landmarks/homecoming_house_concept.png): a cream
    clapboard cape with a steep plum roof, two dormers, a brick chimney, a black-cat weathervane, a
    porch across the front (white posts and rails, a string of lights, a lamp, a red door with a wreath,
    a jack-o'-lantern on each side of the steps, a rocking chair) and green-shuttered lit windows.
    ~12 m wide, 9 m deep, 10 m to the ridge; the front faces -y."""
    p = Parts(seed=909)
    W, D, H = 11.0, 7.5, 3.6
    hw, hd = W / 2, D / 2
    base = 0.7
    p.box((0, 0, base / 2), (W + 0.2, D + 0.2, base), TRIM)                           # the white skirt
    p.box((0, 0, base + H / 2), (W, D, H), HOUSE_SIDING, jitter=0.05)
    top = base + H
    # the main roof: ridge across (along x), gable ends on the sides, steep
    _prism_x(p, [(-hd - 0.6, top - 0.15), (hd + 0.6, top - 0.15), (0, top + 4.6)], -hw - 0.35, hw + 0.35,
             HOUSE_ROOF, HOUSE_SIDING)
    _prism_x(p, [(-hd + 0.05, top), (hd - 0.05, top), (0, top + 4.35)], -hw + 0.02, hw - 0.02, HOUSE_SIDING)
    # clapboard lines on all four walls
    for k in range(1, 8):
        z = base + k * H / 8
        p.box((0, -hd - 0.025, z), (W, 0.03, 0.05), CLAP_LINE, jitter=0.0)
        p.box((0, hd + 0.025, z), (W, 0.03, 0.05), CLAP_LINE, jitter=0.0)
        for sx in (-1, 1):
            p.box((sx * (hw + 0.025), 0, z), (0.03, D, 0.05), CLAP_LINE, jitter=0.0)
    # white trim: rake boards up both gable ends, fascia along the eaves
    for sx in (-1, 1):
        x = sx * (hw + 0.37)
        for ye in (-hd - 0.6, hd + 0.6):
            _prism_x(p, [(ye, top - 0.15), (0.0, top + 4.6), (0.0, top + 4.25), (ye, top - 0.5)][:: 1 if ye < 0 else -1],
                     x - 0.06, x + 0.06, TRIM)
    for ye in (-hd - 0.62, hd + 0.62):
        p.box((0, ye, top - 0.3), (W + 0.8, 0.1, 0.3), TRIM)
    # two dormers on the front slope
    for dx in (-2.6, 2.6):
        p.box((dx, -hd + 1.5, top + 1.25), (2.0, 2.0, 1.9), HOUSE_SIDING)
        p.prism([(dx - 1.3, top + 2.1), (dx + 1.3, top + 2.1), (dx, top + 3.3)], -hd + 0.25, -hd + 2.9, HOUSE_ROOF, TRIM)
        _shuttered(p, dx, -hd + 0.5, top + 0.65, 0.85, 1.1, -1)
    # the chimney on the right, through the back slope, and the weathervane with its cat on the ridge
    p.box((3.4, 0.9, top + 3.6), (1.2, 1.2, 4.6), BRICK, jitter=0.08)
    p.box((3.4, 0.9, top + 5.95), (1.4, 1.4, 0.2), (0.62, 0.6, 0.58))
    vx = -1.6
    p.box((vx, 0, top + 4.95), (0.07, 0.07, 1.3), BLACK)
    p.box((vx, 0, top + 5.25), (1.4, 0.05, 0.05), BLACK)                              # the arrow
    p.box((vx, 0, top + 5.05), (0.05, 0.9, 0.05), BLACK)
    p.box((vx + 0.1, 0, top + 5.62), (0.62, 0.16, 0.3), BLACK)                       # the cat: body, head, ears, tail
    p.box((vx + 0.45, 0, top + 5.88), (0.24, 0.16, 0.22), BLACK)
    p.box((vx + 0.4, 0, top + 6.03), (0.06, 0.1, 0.1), BLACK)
    p.box((vx + 0.52, 0, top + 6.03), (0.06, 0.1, 0.1), BLACK)
    p.box((vx - 0.3, 0, top + 5.95), (0.06, 0.06, 0.55), BLACK)
    p.box((vx + 0.49, -0.09, top + 5.9), (0.12, 0.02, 0.05), GLOW, glow=True)        # yellow eyes
    # a lower wing on the back left (concept side view)
    p.box((-hw + 1.6, hd + 1.4, base + 1.5), (3.2, 2.8, 3.0), HOUSE_SIDING)
    _prism_x(p, [(hd - 0.1, base + 2.9), (hd + 3.1, base + 2.9), (hd + 1.5, base + 4.2)], -hw - 0.1, -hw + 3.3, HOUSE_ROOF, HOUSE_SIDING)
    # the porch across the front: deck, steps, posts, rails, a shed roof, lights
    PD = 2.6
    py = -hd - PD / 2
    p.box((0, py, base - 0.1), (W + 0.4, PD, 0.2), TRIM)
    for k, (h, dy) in enumerate(((0.45, 0.55), (0.22, 1.05))):
        p.box((0, -hd - PD - dy + 0.3, h / 2), (2.4, 0.5, h), TRIM)
    for x in (-hw - 0.05, -hw / 2 - 0.3, -1.4, 1.4, hw / 2 + 0.3, hw + 0.05):
        p.box((x, -hd - PD + 0.15, base + 1.45), (0.22, 0.22, 2.9), TRIM)
    for x0, x1 in ((-hw - 0.05, -1.4), (1.4, hw + 0.05)):                             # rails and balusters
        p.box(((x0 + x1) / 2, -hd - PD + 0.15, base + 0.9), (x1 - x0, 0.12, 0.1), TRIM)
        p.box(((x0 + x1) / 2, -hd - PD + 0.15, base + 0.1), (x1 - x0, 0.12, 0.08), TRIM)
        n = int((x1 - x0) / 0.3)
        for i in range(1, n):
            p.box((x0 + (x1 - x0) * i / n, -hd - PD + 0.15, base + 0.5), (0.05, 0.05, 0.8), TRIM)
    eave = base + 3.0
    _prism_x(p, [(-hd - PD - 0.4, eave), (-hd + 0.02, top - 0.6), (-hd + 0.02, top - 0.4), (-hd - PD - 0.4, eave + 0.2)],
             -hw - 0.4, hw + 0.4, HOUSE_ROOF, HOUSE_ROOF)
    p.box((0, -hd - PD + 0.15, eave - 0.12), (W + 0.6, 0.22, 0.25), TRIM)             # the porch beam
    for i in range(23):                                                              # the string of lights
        x = -hw + i * W / 22
        sag = 0.12 * math.sin(math.pi * ((i * 2) % 22) / 22)
        p.box((x, -hd - PD + 0.02, eave - 0.32 - sag), (0.1, 0.1, 0.1), GLOW, glow=True)
    # the front: a red door with a wreath and a lamp, big lit windows either side
    p.box((0, -hd - 0.06, base + 1.1), (1.1, 0.12, 2.2), RED_DOOR)
    for k in range(8):                                                               # the wreath: a ring of leaves
        a = k * math.pi / 4
        p.box((0.27 * math.cos(a), -hd - 0.17, base + 1.6 + 0.27 * math.sin(a)), (0.2, 0.08, 0.2), LEAVES, jitter=0.2)
    p.box((0.95, -hd - 0.15, base + 2.35), (0.22, 0.22, 0.32), GLOW, glow=True)       # porch lamp
    for x in (-3.4, 3.4):
        _shuttered(p, x, -hd, base + 0.7, 1.6, 1.7, -1)
    # the sides: a window on each floor, in the gable
    for sx in (-1, 1):
        _shuttered(p, sx * hw, 0, base + 0.8, 1.0, 1.5, "x+" if sx > 0 else "x-")
        _shuttered(p, sx * (hw + 0.37), 0, top + 0.7, 0.9, 1.3, "x+" if sx > 0 else "x-")
    # jack-o'-lanterns on the steps and the porch, a rocking chair, hanging baskets of autumn flowers
    for x, y in ((-1.5, -hd - PD - 0.5), (1.5, -hd - PD - 0.5)):
        p.cylinder((x, y, 0.0), 0.36, 0.55, PUMPKIN, segments=8)
        p.box((x, y - 0.33, 0.3), (0.32, 0.06, 0.18), GLOW, glow=True)              # the carved face
        p.box((x, y, 0.62), (0.08, 0.08, 0.14), (0.25, 0.35, 0.1))
    for x in (-2.3, 2.3):                                                             # pots of orange mums by the steps
        p.cylinder((x, -hd - PD - 0.35, 0.0), 0.28, 0.4, POT, segments=8)
        p.box((x, -hd - PD - 0.35, 0.55), (0.6, 0.6, 0.35), (0.85, 0.42, 0.08), jitter=0.2)
    p.box((3.6, -hd - 1.2, base + 0.45), (0.7, 0.7, 0.12), OAK)                         # rocking chair
    p.box((3.6, -hd - 0.9, base + 0.95), (0.7, 0.1, 1.0), OAK)
    for x in (-hw + 0.4, hw - 0.4):
        p.box((x, -hd - PD + 0.5, eave - 0.8), (0.55, 0.55, 0.45), LEAVES, jitter=0.2)
    obs = p.finish(col, name, pos, rot_z, scale)
    return obs, [(hw + 0.6) * scale, (hd + PD + 1.2) * scale]
