"""Low-poly, vertex-colored Halloween props built with bmesh (shared by the hole builder).

Every builder takes a world position (x, y, z) in course coords (z up) and returns the new object.
Materials are named by role (stone_vc, pumpkin_vc, glow, ...) so Godot can swap in its own
shaders by name; vertex colors live in the "Col" attribute.
"""
import math
import random

import bpy  # noqa: I001  (bpy must load before bmesh)
import bmesh
from mathutils import Matrix, Vector, noise

_mats = {}


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def vcol_layer(bm):
    return bm.loops.layers.color.get("Col") or bm.loops.layers.color.new("Col")


def paint(bm, fn):
    lay = vcol_layer(bm)
    for f in bm.faces:
        for l in f.loops:
            l[lay] = (*fn(l.vert.co, f.normal), 1.0)


def material(name, rough=0.85, emit=None, strength=0.0):
    if name in _mats:
        return _mats[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    attr = nt.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "Col"
    nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*emit, 1)
        bsdf.inputs["Emission Strength"].default_value = strength
    _mats[name] = m
    return m


def link(name, bm, mats, collection):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    return ob


def tube(bm, p0, p1, r0, r1, sides=8):
    p0, p1 = Vector(p0), Vector(p1)
    axis = p1 - p0
    rot = axis.to_track_quat("Z", "Y").to_matrix().to_4x4()
    ret = bmesh.ops.create_cone(bm, cap_ends=True, segments=sides, radius1=r0, radius2=r1, depth=axis.length)
    bmesh.ops.transform(bm, matrix=Matrix.Translation((p0 + p1) / 2) @ rot, verts=ret["verts"])
    return ret["verts"]


def ball(bm, p, r, seg=8):
    ret = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(4, seg // 2), radius=r)
    bmesh.ops.translate(bm, vec=Vector(p), verts=ret["verts"])
    return ret["verts"]


# ---------- stones ----------------------------------------------------------------------------
STONE, STONE_DK, MOSS = (0.42, 0.40, 0.46), (0.20, 0.19, 0.24), (0.24, 0.33, 0.12)


def _stone_colors(h):
    def fn(co, n):
        t = max(0.0, min(1.0, co.z / max(h, 0.01)))
        c = lerp(STONE_DK, STONE, 0.35 + 0.65 * t)
        if n.z > 0.6 and co.z > h * 0.6:
            c = lerp(c, MOSS, 0.55)
        if t < 0.12:
            c = lerp(c, MOSS, 0.5)
        v = 0.9 + 0.2 * noise.noise(co * 3.0)
        return tuple(k * v for k in c)
    return fn


def _finish_stone(bm, name, pos, rot_z, tilt, h, col):
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.035, segments=2, affect="EDGES", clamp_overlap=True)
    for v in bm.verts:
        v.co += Vector((noise.noise(v.co * 4.0), noise.noise(v.co * 4.0 + Vector((3, 1, 2))), 0)) * 0.018
    bm.normal_update()
    paint(bm, _stone_colors(h))
    ob = link(name, bm, [material("stone_vc", 0.9)], col)
    ob.location = (pos[0], pos[1], pos[2] - 0.08)
    ob.rotation_euler = (tilt[0], tilt[1], rot_z)
    return ob


def headstone(col, name, pos, w=0.7, h=1.0, d=0.16, rot_z=0.0, tilt=(0, 0)):
    bm = bmesh.new()
    pts = [(-w / 2, 0), (w / 2, 0)]
    for k in range(9):
        a = math.pi * k / 8
        pts.append((w / 2 * math.cos(a), h - w / 2 + w / 2 * math.sin(a)))
    face = bm.faces.new([bm.verts.new((x, -d / 2, z)) for x, z in pts])
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, vec=(0, d, 0), verts=[e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)])
    bm.normal_update()
    front = min(bm.faces, key=lambda f: f.calc_center_median().y)
    bmesh.ops.inset_region(bm, faces=[front], thickness=w * 0.14, depth=-0.025)
    return _finish_stone(bm, name, pos, rot_z, tilt, h, col)


def _slab(bm, pts, d, z0, inset=None):
    """An extruded stone slab from a profile [(x, z), ...] (front at -y), sitting at z0, with its front
    panel set back into a frame. Returns the panel's y (where carvings go)."""
    face = bm.faces.new([bm.verts.new((x, -d / 2, z + z0)) for x, z in pts])
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, vec=(0, d, 0), verts=[e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # the slab's own front (not the plinth's, which stands further out)
    front = next(f for f in bm.faces if f.normal.y < -0.9 and abs(f.calc_center_median().y + d / 2) < 1e-4
                 and f.calc_center_median().z > z0 + 0.05)
    if inset is None:
        return front.calc_center_median().y         # a plain face
    bmesh.ops.inset_region(bm, faces=[front], thickness=inset, depth=0.0)       # the frame round it ...
    bmesh.ops.inset_region(bm, faces=[front], thickness=0.004, depth=0.0)       # ... and a sharp step down
    for v in front.verts:
        v.co.y += 0.02                              # the panel set back behind its frame
    return front.calc_center_median().y


def _plinth(bm, w, d, h):
    r = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(w, d, h), verts=r["verts"])
    bmesh.ops.translate(bm, vec=(0, 0, h / 2), verts=r["verts"])
    # a little narrower at the top, as the concept's
    for v in r["verts"]:
        if v.co.z > h * 0.9:
            v.co.x *= 0.96
            v.co.y *= 0.92


def _carving(bm, polys, y):
    """Flat carved shapes laid on the panel at `y` (a hair proud of it, so they never flicker), marked
    (face layer "carved") to be painted dark as cut stone."""
    carved = bm.faces.layers.int.get("carved") or bm.faces.layers.int.new("carved")
    for poly in polys:
        f = bm.faces.new([bm.verts.new((x, y - 0.003, z)) for x, z in poly])
        f.normal_update()
        if f.normal.y > 0:
            f.normal_flip()
        f[carved] = 1


def _letters(text, size, center_z, resolution=1):
    """Polygons of `text` in Blender's own font, centred, as [(x, z), ...] lists (a few per letter)."""
    cu = bpy.data.curves.new("txt", "FONT")
    cu.body = text
    cu.size = size
    cu.align_x = "CENTER"
    cu.resolution_u = resolution
    ob = bpy.data.objects.new("txt", cu)
    bpy.context.scene.collection.objects.link(ob)
    deps = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(deps).to_mesh()
    polys = [[(me.vertices[i].co.x, me.vertices[i].co.y + center_z - size * 0.35) for i in p.vertices] for p in me.polygons]
    ob.evaluated_get(deps).to_mesh_clear()
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    return polys


def _finish_concept_stone(bm, name, pos, rot_z, tilt, h, col):
    carved = bm.faces.layers.int["carved"]
    bmesh.ops.bevel(bm, geom=[e for e in bm.edges if not any(f[carved] for f in e.link_faces) and e.calc_face_angle(0) > 0.6],
                    offset=0.03, segments=1, affect="EDGES", clamp_overlap=True)
    for v in bm.verts:
        if not any(f[carved] for f in v.link_faces):
            v.co += Vector((noise.noise(v.co * 4.0), noise.noise(v.co * 4.0 + Vector((3, 1, 2))), 0)) * 0.012
    bm.normal_update()
    paint(bm, _stone_colors(h))
    lay = bm.loops.layers.color["Col"]
    for f in bm.faces:
        if f[carved]:
            for lp in f.loops:
                lp[lay] = (0.16, 0.14, 0.2, 1.0)
    ob = link(name, bm, [material("stone_vc", 0.9)], col)
    ob.location = (pos[0], pos[1], pos[2] - 0.06)
    ob.rotation_euler = (tilt[0], tilt[1], rot_z)
    return ob


def headstone_rip(col, name, pos, scale=1.0, rot_z=0.0, tilt=(0, 0)):
    """Marc's tall arched headstone: stepped shoulders, a recessed arched panel with RIP cut in it, on
    a wider plinth. About 300 triangles."""
    bm = bmesh.new()
    w, h, d, base = 0.62 * scale, 1.18 * scale, 0.17 * scale, 0.24 * scale
    _plinth(bm, w + 0.16 * scale, d + 0.2 * scale, base)
    hs = h - 0.36 * scale                       # the shoulders
    r = w / 2 - 0.05 * scale
    pts = [(-w / 2, 0), (w / 2, 0), (w / 2, hs), (w / 2 - 0.05 * scale, hs)]
    for k in range(1, 8):
        a = math.pi * k / 8
        pts.append((r * math.cos(a), hs + r * math.sin(a) * 0.95))
    pts += [(-w / 2 + 0.05 * scale, hs), (-w / 2, hs)]
    panel = _slab(bm, pts, d, base - 0.02 * scale, 0.07 * scale)
    _carving(bm, _letters("RIP", 0.15 * scale, base + h * 0.6), panel)
    return _finish_concept_stone(bm, name, pos, rot_z, tilt, base + h, col)


def headstone_moon(col, name, pos, scale=1.0, rot_z=0.0, tilt=(0, 0)):
    """Marc's wide headstone: a low arch over shoulders, a recessed panel with a crescent moon cut in
    it, on a plinth. About 250 triangles."""
    bm = bmesh.new()
    w, h, d, base = 1.0 * scale, 0.8 * scale, 0.2 * scale, 0.2 * scale
    _plinth(bm, w + 0.12 * scale, d + 0.16 * scale, base)
    hs = h - 0.24 * scale
    pts = [(-w / 2, 0), (w / 2, 0), (w / 2, hs), (w / 2 - 0.08 * scale, hs + 0.03 * scale)]
    for k in range(1, 8):
        t = k / 8
        x = (w / 2 - 0.08 * scale) * (1 - 2 * t)
        pts.append((x, hs + 0.03 * scale + (h - hs - 0.03 * scale) * math.sqrt(max(0.0, 1 - (2 * t - 1) ** 2))))
    pts += [(-w / 2 + 0.08 * scale, hs + 0.03 * scale), (-w / 2, hs)]
    panel = _slab(bm, pts, d, base - 0.02 * scale, 0.08 * scale)
    # the crescent: an outer circle's arc and an offset inner one, as one flat polygon
    cz, cx, ro = base + h * 0.6, 0.0, 0.08 * scale
    # a strip of quads from tip to tip (one concave polygon would triangulate across the hollow)
    n = 9
    strip = []
    for k in range(n + 1):
        t = k / n
        a_out = math.radians(55 + 250 * t)
        a_in = math.radians(75 + 210 * t)
        po = (cx + ro * math.cos(a_out), cz + ro * math.sin(a_out))
        pi_ = (cx + 0.04 * scale + ro * 0.8 * math.cos(a_in), cz + 0.025 * scale + ro * 0.8 * math.sin(a_in))
        strip.append((po, pi_))
    quads = [[strip[k][0], strip[k + 1][0], strip[k + 1][1], strip[k][1]] for k in range(n)]
    _carving(bm, quads, panel)
    return _finish_concept_stone(bm, name, pos, rot_z, tilt, base + h, col)


def headstone_broken(col, name, pos, scale=1.0, rot_z=0.0, tilt=(0, 0)):
    """Marc's tall plain slab with its top corner broken off and a crack running down from the break,
    on a plinth. About 150 triangles."""
    bm = bmesh.new()
    w, h, d, base = 0.6 * scale, 1.45 * scale, 0.2 * scale, 0.26 * scale
    _plinth(bm, w + 0.22 * scale, d + 0.24 * scale, base)
    pts = [(-w / 2, 0), (w / 2, 0), (w / 2, h - 0.32 * scale),          # the broken corner: a jagged step down
           (w / 2 - 0.07 * scale, h - 0.24 * scale), (w / 2 - 0.1 * scale, h - 0.16 * scale),
           (w / 2 - 0.18 * scale, h - 0.09 * scale), (w / 2 - 0.2 * scale, h), (-w / 2, h)]
    panel = _slab(bm, pts, d, base - 0.02 * scale, None)
    # the crack, from the break down and across the face
    crack = [(w / 2 - 0.12 * scale, h - 0.12 * scale), (w / 2 - 0.16 * scale, h - 0.24 * scale),
             (w / 2 - 0.11 * scale, h - 0.36 * scale), (w / 2 - 0.02 * scale, h - 0.5 * scale)]
    quads = []
    for (ax, az), (bx, bz) in zip(crack[:-1], crack[1:]):
        t = 0.008 * scale
        quads.append([(ax - t, az + base), (bx - t, bz + base), (bx + t, bz + base), (ax + t, az + base)])
    _carving(bm, quads, panel)
    return _finish_concept_stone(bm, name, pos, rot_z, tilt, base + h, col)


def cross_stone(col, name, pos, h=1.3, rot_z=0.0, tilt=(0, 0)):
    bm = bmesh.new()
    for sx, sy, sz, z in [(0.18, 0.15, h, h / 2), (0.75, 0.15, 0.18, h * 0.7), (0.5, 0.34, 0.2, 0.1)]:
        r = bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=r["verts"])
        bmesh.ops.translate(bm, vec=(0, 0, z), verts=r["verts"])
    return _finish_stone(bm, name, pos, rot_z, tilt, h, col)


def obelisk(col, name, pos, h=2.2, rot_z=0.0):
    bm = bmesh.new()
    r = bmesh.ops.create_cone(bm, cap_ends=True, segments=4, radius1=0.32, radius2=0.22, depth=h)
    bmesh.ops.translate(bm, vec=(0, 0, h / 2 + 0.25), verts=r["verts"])
    r2 = bmesh.ops.create_cone(bm, cap_ends=True, segments=4, radius1=0.24, radius2=0.0, depth=0.4)
    bmesh.ops.translate(bm, vec=(0, 0, h + 0.45), verts=r2["verts"])
    r3 = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(0.85, 0.85, 0.3), verts=r3["verts"])
    bmesh.ops.translate(bm, vec=(0, 0, 0.12), verts=r3["verts"])
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 4, 3, "Z"), verts=r["verts"] + r2["verts"])
    return _finish_stone(bm, name, pos, rot_z, (0, 0), h + 0.6, col)


# ---------- jack-o'-lantern ---------------------------------------------------------------------
PUMP, PUMP_DK, STEM = (0.95, 0.42, 0.06), (0.55, 0.18, 0.03), (0.30, 0.22, 0.10)
FACE_SHAPES = [
    [(-0.58, 0.10), (-0.14, 0.10), (-0.38, 0.52)],
    [(0.14, 0.10), (0.58, 0.10), (0.38, 0.52)],
    [(-0.10, -0.06), (0.10, -0.06), (0.0, 0.13)],
    [(-0.66, -0.12), (-0.40, -0.22), (-0.30, -0.12), (-0.16, -0.24), (0.0, -0.14),
     (0.16, -0.24), (0.30, -0.12), (0.40, -0.22), (0.66, -0.12),
     (0.42, -0.42), (0.24, -0.34), (0.10, -0.50), (-0.06, -0.38), (-0.24, -0.50), (-0.42, -0.40)],
]


def _rib(phi, amp):
    return 1.0 + amp * math.cos(phi * 8)


def jack(col, name, pos, r=0.38, rot_z=0.0, carved=True, shade=None):
    RIB, SQ = 0.11, 0.8
    bm = bmesh.new()
    ret = bmesh.ops.create_uvsphere(bm, u_segments=24 if not carved else 32, v_segments=14, radius=r)
    for v in ret["verts"]:
        k = _rib(math.atan2(v.co.y, v.co.x), RIB)
        v.co.x *= k
        v.co.y *= k
        v.co.z *= SQ
        if v.co.z > r * SQ * 0.82:
            v.co.z -= (v.co.z - r * SQ * 0.82) * 0.75
    bm.normal_update()
    lay = vcol_layer(bm)
    shade = random.uniform(0.85, 1.1) if shade is None else shade
    for f in bm.faces:
        for l in f.loops:
            groove = 0.5 + 0.5 * math.cos(math.atan2(l.vert.co.y, l.vert.co.x) * 8)
            c = lerp(PUMP_DK, PUMP, 0.25 + 0.75 * groove)
            c = lerp(PUMP_DK, c, min(1, 0.35 + (l.vert.co.z + r) / (1.6 * r)))
            l[lay] = (*(min(1, k * shade) for k in c), 1)
    sv = tube(bm, (0, 0, r * SQ * 0.6), (0.07, 0.04, r * 1.05), 0.065, 0.035, 6)
    for f in bm.faces:
        if all(v in sv for v in f.verts):
            for l in f.loops:
                l[lay] = (*STEM, 1)
    mats = [material("pumpkin_vc", 0.6)]
    if carved:
        fm = bmesh.new()
        for shape in FACE_SHAPES:
            f = fm.faces.new([fm.verts.new((u, v, 0)) for u, v in shape])
            bmesh.ops.triangulate(fm, faces=[f])
        bmesh.ops.subdivide_edges(fm, edges=list(fm.edges), cuts=2, use_grid_fill=True)
        bmesh.ops.triangulate(fm, faces=list(fm.faces))
        for v in fm.verts:
            x = v.co.x * r * 0.82
            z = v.co.y * r * SQ * 0.95
            y = -r * math.sqrt(max(0.0, 1 - (x / r) ** 2 - (z / (r * SQ)) ** 2))
            k = _rib(math.atan2(y, x), RIB)
            v.co = Vector((x * k, y * k, z)) * 1.006
        fl = vcol_layer(fm)
        for g in fm.faces:
            g.material_index = 1
            for l in g.loops:
                l[fl] = (1.0, 0.75, 0.3, 1)
        tmp = bpy.data.meshes.new("tmpface")
        fm.to_mesh(tmp)
        fm.free()
        bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
        mats.append(material("glow", 0.5, emit=(1.0, 0.55, 0.12), strength=14.0))
    bm.normal_update()
    ob = link(name, bm, mats, col)
    ob.location = (pos[0], pos[1], pos[2] + r * SQ * 0.85)
    ob.rotation_euler = (0, 0, rot_z)
    return ob


# ---------- fence ------------------------------------------------------------------------------
def fence(col, name, points, height_at, post_gap=1.0):
    """Wrought-iron fence along a polyline of (x, y); height_at(x, y) gives ground z."""
    bm = bmesh.new()
    for (ax, ay), (bx, by) in zip(points[:-1], points[1:]):
        seg = math.hypot(bx - ax, by - ay)
        n = max(1, int(seg / post_gap))
        for k in range(n + 1):
            t = k / n
            x, y = ax + (bx - ax) * t, ay + (by - ay) * t
            z = height_at(x, y)
            hh = 1.45 if k % 4 == 0 else 1.25
            tube(bm, (x, y, z - 0.1), (x, y, z + hh), 0.025, 0.025, 5)
            r = bmesh.ops.create_cone(bm, cap_ends=True, segments=4, radius1=0.06, radius2=0.0, depth=0.16)
            bmesh.ops.translate(bm, vec=(x, y, z + hh + 0.08), verts=r["verts"])
        for zz in (0.25, 1.05):
            tube(bm, (ax, ay, height_at(ax, ay) + zz), (bx, by, height_at(bx, by) + zz), 0.022, 0.022, 4)
    bm.normal_update()
    paint(bm, lambda co, n: (0.08, 0.07, 0.10))
    return link(name, bm, [material("iron_vc", 0.45)], col)


# ---------- wooden bridge ----------------------------------------------------------------------
WOOD, WOOD_DK, WOOD_LT = (0.36, 0.24, 0.15), (0.20, 0.13, 0.09), (0.48, 0.34, 0.22)


def bridge(col, name, deck, floor_at, width=2.8, lanterns=True):
    """A plank bridge (a cart path over water): deck = [(x, y, z), ...] along its centreline (z = the
    deck's top), floor_at(x, y) = the ground or water bed below for the piles. Planks across, two
    stringers, posts with a top rail and a mid rail each side, piles down to the bed, and a little
    lantern on the first and last posts. Returns (object, lantern positions)."""
    bm = bmesh.new()
    pts = [Vector(p) for p in deck]
    lens = [0.0]
    for a, b in zip(pts[:-1], pts[1:]):
        lens.append(lens[-1] + (b - a).length)
    total = lens[-1]

    def at(d):
        for i in range(1, len(pts)):
            if lens[i] >= d or i == len(pts) - 1:
                t = (d - lens[i - 1]) / max(1e-6, lens[i] - lens[i - 1])
                p = pts[i - 1].lerp(pts[i], min(max(t, 0.0), 1.0))
                tan = (pts[i] - pts[i - 1]).normalized()
                return p, tan
        return pts[-1], (pts[-1] - pts[-2]).normalized()

    plank_faces, rail_faces, post_faces = [], [], []
    hw = width / 2
    n = max(2, int(total / 0.34))
    for k in range(n + 1):
        d = total * k / n
        p, tan = at(d)
        side = Vector((tan.y, -tan.x, 0)).normalized()
        jag = 0.06 * math.sin(k * 2.3)                    # uneven plank ends
        a = p - side * (hw + jag) - Vector((0, 0, 0.04))
        b = p + side * (hw - jag) - Vector((0, 0, 0.04))
        ret = bmesh.ops.create_cube(bm, size=1.0)
        v = ret["verts"]
        L = (b - a).length
        bmesh.ops.scale(bm, vec=(L, 0.3, 0.08), verts=v)
        rot = Vector((tan.y, -tan.x, 0)).to_track_quat("X", "Z").to_matrix().to_4x4()
        bmesh.ops.transform(bm, matrix=Matrix.Translation((a + b) / 2) @ rot, verts=v)
        plank_faces += list({f for vv in v for f in vv.link_faces})
    # stringers under the deck
    for sd in (-0.8, 0.8):
        for d0, d1 in zip(lens[:-1], lens[1:]):
            p0, t0 = at(d0)
            p1, _ = at(d1)
            off = Vector((t0.y, -t0.x, 0)).normalized() * hw * sd
            rail_faces += [f for vv in tube(bm, p0 + off - Vector((0, 0, 0.18)), p1 + off - Vector((0, 0, 0.18)), 0.09, 0.09, 6)
                           for f in vv.link_faces]
    # posts, rails and piles
    posts = max(2, int(total / 1.8) + 1)
    tops = {-1: [], 1: []}
    for k in range(posts):
        d = total * k / (posts - 1)
        p, tan = at(d)
        side = Vector((tan.y, -tan.x, 0)).normalized()
        for sd in (-1, 1):
            q = p + side * (hw + 0.05) * sd
            top = q + Vector((0, 0, 1.0))
            post_faces += [f for vv in tube(bm, q - Vector((0, 0, 0.2)), top, 0.07, 0.06, 6) for f in vv.link_faces]
            bed = floor_at(q.x, q.y)
            if bed < q.z - 0.5:
                post_faces += [f for vv in tube(bm, Vector((q.x, q.y, bed - 0.3)), q - Vector((0, 0, 0.15)), 0.11, 0.1, 6)
                               for f in vv.link_faces]
            tops[sd].append(top)
    for sd in (-1, 1):
        for a, b in zip(tops[sd][:-1], tops[sd][1:]):
            for dz in (0.0, -0.45):
                rail_faces += [f for vv in tube(bm, a + Vector((0, 0, dz)), b + Vector((0, 0, dz)), 0.045, 0.045, 5)
                               for f in vv.link_faces]
    bm.normal_update()
    lay = vcol_layer(bm)
    rail_set, post_set = set(rail_faces), set(post_faces)
    for f in bm.faces:
        tone = WOOD_LT if f in rail_set else (WOOD_DK if f in post_set else WOOD)
        k = 0.85 + 0.3 * noise.noise(f.calc_center_median() * 3.1)
        for lp in f.loops:
            lp[lay] = (*(min(1.0, c * k) for c in tone), 1.0)
    obj = link(name, bm, [material("wood_vc", 0.8)], col)
    lamp_pts = []
    if lanterns:
        for sd, i in ((1, 0), (-1, -1)):
            t = tops[sd][i]
            lamp_pts.append((t.x, t.y, t.z + 0.12))
            jack(col, f"{name}_Lamp{i}", (t.x, t.y, t.z - 0.02), r=0.16, rot_z=random.uniform(0, math.tau))
    return obj, lamp_pts


# ---------- skeleton arm out of a grave ---------------------------------------------------------
BONE, BONE_DK, DIRT = (0.86, 0.82, 0.70), (0.45, 0.40, 0.32), (0.36, 0.25, 0.17)


def skeleton_arm(col, name, pos, rot_z=0.4):
    bm = bmesh.new()
    elbow, wrist = Vector((0, 0.05, -0.05)), Vector((0.10, -0.10, 0.42))
    tube(bm, elbow, wrist, 0.05, 0.04, 7)
    tube(bm, elbow + Vector((0.05, 0.02, 0)), wrist + Vector((0.04, 0.03, -0.02)), 0.035, 0.03, 6)
    ball(bm, wrist + Vector((0.02, 0, 0.02)), 0.06, 8)
    knuckle = wrist + Vector((0.02, -0.02, 0.1))
    for spread in (-0.11, -0.04, 0.03, 0.10):
        base = knuckle + Vector((spread, 0, 0.02 - abs(spread) * 0.3))
        tube(bm, wrist + Vector((spread * 0.4, 0, 0.03)), base, 0.018, 0.016, 5)
        p, dirv = base, Vector((spread * 1.5, -0.25, 1.0)).normalized()
        for seg in (0.11, 0.08, 0.06):
            ball(bm, p, 0.022, 6)
            dirv = (Matrix.Rotation(-0.55, 3, "X") @ dirv).normalized()
            q = p + dirv * seg
            tube(bm, p, q, 0.017, 0.013, 5)
            p = q
    t0 = wrist + Vector((-0.1, -0.03, 0.05))
    tube(bm, wrist, t0, 0.02, 0.018, 5)
    tube(bm, t0, t0 + Vector((-0.05, -0.08, 0.09)), 0.017, 0.012, 5)
    bm.normal_update()
    paint(bm, lambda co, n: lerp(BONE_DK, BONE, 0.4 + 0.6 * max(0, min(1, (co.z + 0.1) / 0.9))))
    arm = link(name, bm, [material("bone_vc", 0.7)], col)
    arm.location = (pos[0], pos[1], pos[2] + 0.18)
    arm.rotation_euler = (0.15, -0.2, rot_z)
    arm.scale = (1.5, 1.5, 1.5)

    bm = bmesh.new()
    ret = bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=10, radius=1.0)
    for v in ret["verts"]:
        x, y = v.co.x, v.co.y
        sq = max(abs(x), abs(y)) + 1e-6
        boxy = math.hypot(x, y) / sq
        v.co.x = x * 0.45 * (0.6 + 0.4 * boxy)
        v.co.y = y * 0.95 * (0.6 + 0.4 * boxy)
        v.co.z = max(v.co.z, 0) ** 0.7 * 0.32
        v.co += Vector((0, 0, 0.05 * noise.noise(v.co * 4)))
    for k in range(7):
        a = k / 7 * math.tau + random.random()
        rr = 0.6 + random.random() * 0.4
        ball(bm, (math.cos(a) * rr * 0.55, math.sin(a) * rr * 1.1, 0.05), 0.05 + random.random() * 0.05, 5)
    for f in bm.faces:
        f.smooth = True
    bm.normal_update()
    paint(bm, lambda co, n: tuple(k * (0.8 + 0.4 * noise.noise(co * 5)) for k in DIRT))
    mound = link(name + "_mound", bm, [material("dirt_vc", 1.0)], col)
    mound.location = (pos[0], pos[1], pos[2] - 0.04)
    mound.rotation_euler = (0, 0, rot_z)
    return arm


# =================================================================================================
# Vegetation and set dressing, fully 3D (replaces the painted cards). Each builder returns a bmesh
# at the origin, z up, base on z=0, plus its material list; build_hole instances them.
# Colors are vertex colors with baked-in fake AO (darker underneath and inside), so they read with
# depth under Godot's cheap lighting too.
# =================================================================================================

LEAF_PALETTES = {
    "maple_orange": [(0.98, 0.50, 0.08), (0.90, 0.34, 0.05), (1.00, 0.66, 0.16), (0.80, 0.24, 0.05)],
    "maple_red": [(0.80, 0.13, 0.07), (0.92, 0.25, 0.08), (0.62, 0.08, 0.09), (0.98, 0.38, 0.10)],
    "apple": [(0.86, 0.46, 0.08), (0.62, 0.52, 0.10), (0.95, 0.60, 0.12), (0.70, 0.30, 0.06)],
    "birch": [(1.00, 0.70, 0.14), (0.96, 0.56, 0.08), (1.00, 0.80, 0.30), (0.88, 0.45, 0.06)],
    "bush": [(0.20, 0.30, 0.10), (0.30, 0.38, 0.12), (0.45, 0.30, 0.10), (0.24, 0.24, 0.12)],
}
BARK, BARK_LT = (0.20, 0.12, 0.14), (0.42, 0.27, 0.22)
BIRCH_BARK, BIRCH_MARK = (0.90, 0.88, 0.84), (0.10, 0.08, 0.09)
PINE = [(0.12, 0.24, 0.24), (0.16, 0.30, 0.27), (0.10, 0.19, 0.22)]


def _sweep(bm, pts, radii, sides=6, cap=True):
    """Tube through `pts` with per-point radius; returns the new faces."""
    rings = []
    for i, p in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        tan = (b - a).normalized()
        q = tan.to_track_quat("Z", "Y")
        ring = []
        for k in range(sides):
            ang = math.tau * k / sides
            ring.append(bm.verts.new(p + q @ Vector((math.cos(ang) * radii[i], math.sin(ang) * radii[i], 0))))
        rings.append(ring)
    faces = []
    for r0, r1 in zip(rings[:-1], rings[1:]):
        for k in range(sides):
            faces.append(bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k])))
    if cap:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
        faces.append(bm.faces.new(rings[-1]))
    return faces


def _wander(rng, start, direction, length, segs, wobble, up_bias=0.0):
    pts = [Vector(start)]
    d = Vector(direction).normalized()
    for _ in range(segs):
        d = (d + Vector((rng.uniform(-wobble, wobble), rng.uniform(-wobble, wobble),
                         rng.uniform(-wobble * 0.4, wobble * 0.4) + up_bias))).normalized()
        pts.append(pts[-1] + d * (length / segs))
    return pts


def _color_faces(bm, faces, fn):
    lay = vcol_layer(bm)
    for f in faces:
        for l in f.loops:
            l[lay] = (*fn(l.vert.co, f.normal), 1.0)


def _blob(bm, center, radius, rng, squash=0.8, subdiv=2):
    ret = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    seed = Vector((rng.uniform(0, 50), rng.uniform(0, 50), rng.uniform(0, 50)))
    for v in ret["verts"]:
        n = v.co.normalized()
        bump = 1.0 + 0.22 * noise.noise(n * 2.2 + seed) + 0.08 * noise.noise(n * 5.0 + seed)
        v.co = Vector((n.x * radius * bump, n.y * radius * bump, n.z * radius * bump * squash)) + Vector(center)
    return list({f for v in ret["verts"] for f in v.link_faces})


def _trunk_and_branches(bm, rng, height, radius, n_branches, wobble=0.25, spread=0.9, bark=(BARK, BARK_LT),
                        sides=7, lean=0.15):
    """Twisty trunk plus branches; returns (faces, branch tips)."""
    trunk = _wander(rng, (0, 0, -0.15), (rng.uniform(-lean, lean), rng.uniform(-lean, lean), 1.0), height, 7, wobble * 0.5)
    radii = [radius * (1.25 if i == 0 else 1.0 - 0.6 * i / 7) for i in range(len(trunk))]
    faces = _sweep(bm, trunk, radii, sides)
    tips = [trunk[-1]]
    for b in range(n_branches):
        i = rng.randint(3, 6)
        ang = math.tau * b / n_branches + rng.uniform(-0.4, 0.4)
        d = Vector((math.cos(ang) * spread, math.sin(ang) * spread, rng.uniform(0.6, 1.1)))
        br = _wander(rng, trunk[i], d, height * rng.uniform(0.35, 0.55), 4, wobble, 0.15)
        r0 = radii[i] * 0.55
        faces += _sweep(bm, br, [r0 * (1 - 0.7 * k / 4) for k in range(len(br))], max(4, sides - 2))
        tips.append(br[-1])
    dark, light = bark
    seed = rng.uniform(0, 100)

    def col(co, n):
        ridge = 0.5 + 0.5 * math.sin(co.z * 9.0 + math.atan2(co.y, co.x) * 3.0 + seed)
        c = lerp(dark, light, 0.25 + 0.45 * ridge)
        return lerp((0.08, 0.05, 0.07), c, min(1.0, 0.45 + co.z / max(height, 0.1)))
    _color_faces(bm, faces, col)
    return faces, tips


def _canopy(bm, rng, tips, palette, size, count, center_z, squash=0.75):
    """Leaf mass as many small clumps on an ellipsoid shell, each clump its own shade:
    lit tops, dark undersides and interior, like the painted trees."""
    tip_c = Vector((sum(t.x for t in tips) / len(tips), sum(t.y for t in tips) / len(tips),
                    max(t.z for t in tips)))
    center = Vector((tip_c.x, tip_c.y, tip_c.z - size * 0.15))
    rx, rz = size * 1.35, size * 1.0
    faces = []
    clumps = []
    n = count * 2
    for i in range(n):
        # fibonacci sphere for even coverage, jittered; fewer clumps underneath
        z = 1 - 2 * (i + 0.5) / n
        if z < -0.55 and rng.random() < 0.6:
            continue
        r_ = math.sqrt(max(0.0, 1 - z * z))
        th = i * 2.399963 + rng.uniform(-0.3, 0.3)
        d = Vector((math.cos(th) * r_, math.sin(th) * r_, z))
        c = center + Vector((d.x * rx, d.y * rx, d.z * rz)) * rng.uniform(0.62, 0.9)
        rad = size * rng.uniform(0.42, 0.62)
        fs = _blob(bm, c, rad, rng, squash, 2)
        clumps.append((fs, c, rad, palette[rng.randrange(len(palette))], rng.uniform(0.85, 1.12)))
    # a solid core so gaps between clumps read as deep shadow, not sky
    core = _blob(bm, center, size * 1.0, rng, 0.85, 2)
    clumps.append((core, center, size, palette[0], 0.45))
    lay = vcol_layer(bm)
    top = center.z + rz
    bottom = center.z - rz
    for fs, c, rad, base, bright in clumps:
        for f in fs:
            for l in f.loops:
                co = l.vert.co
                h = max(0.0, min(1.0, (co.z - bottom) / (top - bottom)))
                outward = (co - center).length / max(rx, rz)
                local = max(0.0, (co - c).normalized().z) if (co - c).length > 1e-6 else 0
                shade = bright * (0.32 + 0.38 * h + 0.3 * min(outward, 1.0) + 0.22 * local)
                warm = 0.06 * noise.noise(co * 3.1)
                l[lay] = (min(1.0, base[0] * shade + warm), min(1.0, base[1] * shade), min(1.0, base[2] * shade), 1.0)
            f.smooth = True
            faces.append(f)
    return faces


def tree(kind, seed):
    """Returns (bmesh, materials, height). Heights are nominal; build_hole scales instances."""
    rng = random.Random(seed)
    bm = bmesh.new()
    bark_mat, leaf_mat = material("bark_vc", 0.9), material("leaf_vc", 0.8)
    if kind in ("maple_orange", "maple_red", "apple", "birch"):
        h = rng.uniform(4.0, 5.0)
        birch = kind == "birch"
        tf, tips = _trunk_and_branches(bm, rng, h, 0.22 if not birch else 0.16, rng.randint(3, 5),
                                       spread=0.8 if not birch else 0.45,
                                       bark=((BIRCH_MARK, BIRCH_BARK) if birch else (BARK, BARK_LT)))
        if birch:
            lay = vcol_layer(bm)
            for f in tf:
                for l in f.loops:
                    m = noise.noise(l.vert.co * Vector((6, 6, 2.5)) + Vector((seed, 0, 0)))
                    l[lay] = (*(BIRCH_MARK if m > 0.35 else BIRCH_BARK), 1)
        size = 1.6 if not birch else 1.15
        cf = _canopy(bm, rng, tips, LEAF_PALETTES[kind], size, rng.randint(8, 10) if not birch else 7, h * 0.85)
        for f in tf:
            f.material_index = 0
        for f in cf:
            f.material_index = 1
        mats = [bark_mat, leaf_mat]
        if kind == "apple":
            ap = []
            for _ in range(22):
                tip = tips[rng.randrange(len(tips))]
                p = Vector(tip) + Vector((rng.uniform(-1.3, 1.3), rng.uniform(-1.3, 1.3), rng.uniform(-1.0, 0.4)))
                ret = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.11)
                bmesh.ops.translate(bm, vec=p, verts=ret["verts"])
                ap += list({f for v in ret["verts"] for f in v.link_faces})
            _color_faces(bm, ap, lambda co, n: (0.78, 0.06, 0.05))
            for f in ap:
                f.material_index = 1
        top = h + size * 1.2
    elif kind == "pine":
        h = rng.uniform(6.0, 8.0)
        tf, _ = _trunk_and_branches(bm, rng, h * 0.35, 0.18, 0, lean=0.03)
        cones = []
        layers = 5
        for i in range(layers):
            t = i / layers
            r = (1.0 - t * 0.78) * h * 0.26
            z0 = h * (0.18 + 0.16 * i)
            ret = bmesh.ops.create_cone(bm, cap_ends=True, segments=9, radius1=r, radius2=0.0, depth=h * 0.34)
            for v in ret["verts"]:
                if v.co.z < 0 and v.co.length > 0.01:
                    v.co.z -= rng.uniform(0.0, 0.35) * r * 0.5          # ragged skirt
                v.co.x += rng.uniform(-0.05, 0.05) * r
            bmesh.ops.translate(bm, vec=(0, 0, z0 + h * 0.17), verts=ret["verts"])
            cones += list({f for v in ret["verts"] for f in v.link_faces})
        _color_faces(bm, cones, lambda co, n: tuple(c * (0.6 + 0.7 * (co.z / h) + 0.35 * max(n.z, 0)) for c in PINE[int(abs(co.x * 3 + co.y * 7)) % 3]))
        for f in tf:
            f.material_index = 0
        for f in cones:
            f.material_index = 1
        mats = [bark_mat, material("pine_vc", 0.9)]
        top = h
    else:  # dead / haunted / lantern: bare twisted trees
        h = rng.uniform(4.2, 5.5)
        tf, tips = _trunk_and_branches(bm, rng, h, 0.28, rng.randint(4, 6), wobble=0.55, spread=1.1,
                                       bark=((0.14, 0.08, 0.11), (0.36, 0.20, 0.20)), lean=0.25)
        # second tier of twigs
        for tip in list(tips[1:]):
            for _ in range(2):
                tw = _wander(rng, tip, (rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.2, 1.0)), rng.uniform(0.8, 1.6), 3, 0.7)
                f2 = _sweep(bm, tw, [0.05, 0.035, 0.02, 0.01], 4)
                _color_faces(bm, f2, lambda co, n: (0.16, 0.09, 0.12))
                tips.append(tw[-1])
        mats = [bark_mat]
        if kind == "lantern":
            glow = []
            for tip in rng.sample(tips[1:], min(5, len(tips) - 1)):
                p = Vector(tip) - Vector((0, 0, 0.45))
                f3 = _sweep(bm, [Vector(tip), p], [0.008, 0.008], 3, cap=False)
                _color_faces(bm, f3, lambda co, n: (0.05, 0.05, 0.05))
                ret = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.16)
                for v in ret["verts"]:
                    v.co.z *= 1.25
                bmesh.ops.translate(bm, vec=p - Vector((0, 0, 0.18)), verts=ret["verts"])
                glow += list({f for v in ret["verts"] for f in v.link_faces})
            _color_faces(bm, glow, lambda co, n: (1.0, 0.7, 0.3))
            for f in glow:
                f.material_index = 1
            mats.append(material("glow", 0.5, emit=(1.0, 0.55, 0.12), strength=14.0))
        top = h + 1.0
    bm.normal_update()
    return bm, mats, top


def far_pine(seed):
    """Silhouette pine for distant hills: two stacked 6-sided cones (~24 triangles)."""
    rng = random.Random(seed)
    bm = bmesh.new()
    h = rng.uniform(6.0, 8.0)
    for z0, r, dh in ((0.6, h * 0.24, h * 0.6), (h * 0.42, h * 0.16, h * 0.58)):
        ret = bmesh.ops.create_cone(bm, cap_ends=False, segments=6, radius1=r, radius2=0.0, depth=dh)
        bmesh.ops.translate(bm, vec=(0, 0, z0 + dh / 2), verts=ret["verts"])
    props_c = PINE[seed % 3]
    _color_faces(bm, list(bm.faces), lambda co, n: tuple(c * (0.5 + 0.5 * co.z / h) for c in props_c))
    bm.normal_update()
    return bm, [material("pine_vc", 0.9)], h


def grass_clump(seed, tall=False):
    rng = random.Random(seed)
    bm = bmesh.new()
    faces = []
    n = rng.randint(7, 11) if not tall else rng.randint(9, 14)
    for _ in range(n):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(0.0, 0.14)
        base = Vector((math.cos(a) * r, math.sin(a) * r, -0.03))
        hgt = rng.uniform(0.28, 0.5) if not tall else rng.uniform(0.7, 1.2)
        lean = Vector((math.cos(a), math.sin(a), 0)) * rng.uniform(0.08, 0.3) * hgt
        w = 0.035 if not tall else 0.03
        side = Vector((-math.sin(a), math.cos(a), 0)) * w
        v0, v1 = bm.verts.new(base - side), bm.verts.new(base + side)
        mid = base + lean * 0.4 + Vector((0, 0, hgt * 0.55))
        v2, v3 = bm.verts.new(mid + side * 0.7), bm.verts.new(mid - side * 0.7)
        v4 = bm.verts.new(base + lean + Vector((0, 0, hgt)))
        faces += [bm.faces.new((v0, v1, v2, v3)), bm.faces.new((v3, v2, v4))]
    lo, hi = ((0.06, 0.12, 0.04), (0.42, 0.55, 0.16)) if not tall else ((0.30, 0.20, 0.07), (0.92, 0.70, 0.30))
    top = 0.5 if not tall else 1.2
    _color_faces(bm, faces, lambda co, n: lerp(lo, hi, max(0.0, min(1.0, co.z / top))))
    bm.normal_update()
    return bm, [material("grass_vc", 0.9)], top


def leaf_pile(seed):
    rng = random.Random(seed)
    bm = bmesh.new()
    faces = []
    pal = LEAF_PALETTES["maple_orange"] + LEAF_PALETTES["maple_red"]
    for _ in range(26):
        a, r = rng.uniform(0, math.tau), rng.uniform(0, 0.45) ** 0.8
        c = Vector((math.cos(a) * r, math.sin(a) * r, (0.45 - r) * 0.35 + rng.uniform(0, 0.04)))
        rot = rng.uniform(0, math.tau)
        pts = [c + Vector((math.cos(rot + k * math.tau / 5) * s, math.sin(rot + k * math.tau / 5) * s, rng.uniform(-0.02, 0.02)))
               for k, s in enumerate([0.09, 0.05, 0.08, 0.05, 0.09])]
        faces.append(bm.faces.new([bm.verts.new(p) for p in pts]))
    lay = vcol_layer(bm)
    for f in faces:
        col = pal[rng.randrange(len(pal))]
        for l in f.loops:
            l[lay] = (*(v * (0.7 + 0.6 * l.vert.co.z / 0.2) for v in col), 1)
    bm.normal_update()
    return bm, [material("leaf_vc", 0.8)], 0.2


def bush(seed):
    rng = random.Random(seed)
    bm = bmesh.new()
    faces = []
    for _ in range(rng.randint(3, 5)):
        c = Vector((rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), rng.uniform(0.25, 0.45)))
        faces += _blob(bm, c, rng.uniform(0.35, 0.55), rng, 0.7, 1)
    seed_v = Vector((seed, 0, 0))
    pal = LEAF_PALETTES["bush"]
    _color_faces(bm, faces, lambda co, n: tuple(v * (0.45 + 0.9 * co.z) for v in pal[int((noise.noise(co * 2 + seed_v) * 0.5 + 0.5) * 3.99)]))
    for f in faces:
        f.smooth = True
    bm.normal_update()
    return bm, [material("leaf_vc", 0.8)], 1.0


def corn_stalk(seed):
    rng = random.Random(seed)
    bm = bmesh.new()
    h = rng.uniform(2.0, 2.5)
    stem = _wander(rng, (0, 0, -0.05), (0, 0, 1), h, 3, 0.05)
    sf = _sweep(bm, stem, [0.03, 0.026, 0.02, 0.012], 4)
    _color_faces(bm, sf, lambda co, n: lerp((0.35, 0.28, 0.08), (0.75, 0.62, 0.22), co.z / h))
    lf = []
    for i in range(6):
        z = h * (0.2 + 0.12 * i)
        a = i * 2.4 + rng.uniform(-0.3, 0.3)
        d = Vector((math.cos(a), math.sin(a), 0))
        side = Vector((-d.y, d.x, 0)) * 0.035
        p0 = Vector((0, 0, z))
        p1 = p0 + d * 0.35 + Vector((0, 0, 0.18))
        p2 = p0 + d * 0.7 + Vector((0, 0, -0.05))
        vs = [bm.verts.new(p0 - side), bm.verts.new(p0 + side), bm.verts.new(p1 + side), bm.verts.new(p1 - side), bm.verts.new(p2)]
        lf += [bm.faces.new(vs[:4]), bm.faces.new((vs[3], vs[2], vs[4]))]
    _color_faces(bm, lf, lambda co, n: lerp((0.45, 0.33, 0.08), (0.88, 0.68, 0.25), co.z / h))
    ears = []
    for k in range(rng.randint(1, 2)):
        ret = bmesh.ops.create_cone(bm, cap_ends=True, segments=5, radius1=0.05, radius2=0.025, depth=0.26)
        bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(0.5, 3, "X"), verts=ret["verts"])
        bmesh.ops.translate(bm, vec=(0.05, 0.08 * (1 if k else -1), h * (0.5 + 0.12 * k)), verts=ret["verts"])
        ears += list({f for v in ret["verts"] for f in v.link_faces})
    _color_faces(bm, ears, lambda co, n: (0.95, 0.72, 0.18))
    bm.normal_update()
    return bm, [material("corn_vc", 0.85)], h


def cattails(seed):
    rng = random.Random(seed)
    bm = bmesh.new()
    for _ in range(rng.randint(4, 7)):
        base = Vector((rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), -0.05))
        h = rng.uniform(1.1, 1.7)
        stem = _wander(rng, base, (rng.uniform(-0.1, 0.1), rng.uniform(-0.1, 0.1), 1), h, 2, 0.05)
        sf = _sweep(bm, stem, [0.012, 0.01, 0.008], 3)
        _color_faces(bm, sf, lambda co, n: (0.32, 0.40, 0.12))
        top = stem[-1] - Vector((0, 0, 0.18))
        ret = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.035, radius2=0.035, depth=0.22)
        bmesh.ops.translate(bm, vec=top, verts=ret["verts"])
        _color_faces(bm, list({f for v in ret["verts"] for f in v.link_faces}), lambda co, n: (0.32, 0.15, 0.07))
    gm, _, _ = grass_clump(seed + 1)
    tmp = bpy.data.meshes.new("tmp_grass")
    gm.to_mesh(tmp)
    gm.free()
    bm.from_mesh(tmp)
    bpy.data.meshes.remove(tmp)
    bm.normal_update()
    return bm, [material("grass_vc", 0.9)], 1.7


def mushrooms(seed):
    rng = random.Random(seed)
    bm = bmesh.new()
    caps = []
    for i in range(rng.randint(3, 5)):
        base = Vector((rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), -0.02))
        h = rng.uniform(0.12, 0.4)
        sf = _sweep(bm, [base, base + Vector((rng.uniform(-0.03, 0.03), 0, h))], [0.03, 0.025], 5)
        _color_faces(bm, sf, lambda co, n: (0.55, 0.45, 0.62))
        ret = bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=4, radius=h * 0.45 + 0.05)
        for v in ret["verts"]:
            v.co.z = max(v.co.z, 0) * 0.55
        bmesh.ops.translate(bm, vec=base + Vector((0, 0, h)), verts=ret["verts"])
        caps += list({f for v in ret["verts"] for f in v.link_faces})
    _color_faces(bm, caps, lambda co, n: (0.25, 0.95, 0.9))
    for f in caps:
        f.material_index = 1
    bm.normal_update()
    return bm, [material("stem_vc", 0.8), material("mushroom_glow", 0.4, emit=(0.2, 1.0, 0.9), strength=3.0)], 0.5


def hay_bales(seed):
    rng = random.Random(seed)
    bm = bmesh.new()
    faces = []
    for (x, y, z) in ((-0.65, 0, 0.25), (0.65, 0, 0.25), (0.0, 0.05, 0.75)):
        r = bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(1.2, 0.6, 0.5), verts=r["verts"])
        bmesh.ops.translate(bm, vec=(x, y, z), verts=r["verts"])
        bmesh.ops.rotate(bm, cent=(x, y, z), matrix=Matrix.Rotation(rng.uniform(-0.15, 0.15), 3, "Z"), verts=r["verts"])
        faces += list({f for v in r["verts"] for f in v.link_faces})
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.06, segments=1, affect="EDGES", clamp_overlap=True)
    bm.normal_update()
    _color_faces(bm, list(bm.faces), lambda co, n: tuple(c * (0.75 + 0.25 * noise.noise(co * 9)) * (0.6 + 0.4 * co.z) for c in (0.95, 0.72, 0.30)))
    return bm, [material("straw_vc", 0.95)], 1.0


def scarecrow(seed):
    rng = random.Random(seed)
    bm = bmesh.new()
    wood = []
    wood += _sweep(bm, [Vector((0, 0, -0.2)), Vector((0, 0, 2.0))], [0.06, 0.05], 5)
    wood += _sweep(bm, [Vector((-0.8, 0, 1.45)), Vector((0.8, 0, 1.5))], [0.04, 0.04], 5)
    _color_faces(bm, wood, lambda co, n: (0.30, 0.20, 0.13))
    shirt = []
    r = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(0.55, 0.28, 0.6), verts=r["verts"])
    bmesh.ops.translate(bm, vec=(0, 0, 1.25), verts=r["verts"])
    for v in r["verts"]:
        if v.co.z < 1.0:
            v.co.x *= 0.8
    shirt += list({f for v in r["verts"] for f in v.link_faces})
    for sx in (-1, 1):
        shirt += _sweep(bm, [Vector((0.2 * sx, 0, 1.47)), Vector((0.75 * sx, 0, 1.47))], [0.11, 0.09], 6)
    _color_faces(bm, shirt, lambda co, n: (0.48, 0.16, 0.20) if int(co.z * 8 + co.x * 8) % 2 else (0.36, 0.10, 0.16))
    straw = []
    for sx in (-1, 1):
        for _ in range(5):
            p = Vector((0.82 * sx, rng.uniform(-0.05, 0.05), 1.47))
            straw += _sweep(bm, [p, p + Vector((0.12 * sx, rng.uniform(-0.08, 0.08), rng.uniform(-0.15, 0.05)))], [0.012, 0.004], 3, cap=False)
    _color_faces(bm, straw, lambda co, n: (0.95, 0.75, 0.32))
    hat = []
    ret = bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.42, radius2=0.42, depth=0.03)
    bmesh.ops.translate(bm, vec=(0, 0, 2.02), verts=ret["verts"])
    hat += list({f for v in ret["verts"] for f in v.link_faces})
    ret = bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.2, radius2=0.04, depth=0.4)
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(0.25, 3, "Y"), verts=ret["verts"])
    bmesh.ops.translate(bm, vec=(0.04, 0, 2.2), verts=ret["verts"])
    hat += list({f for v in ret["verts"] for f in v.link_faces})
    _color_faces(bm, hat, lambda co, n: (0.32, 0.26, 0.14))
    for f in bm.faces:
        f.material_index = 0
    mats = [material("cloth_vc", 0.95)]
    bm.normal_update()
    return bm, mats, 2.4


def crow_post(seed):
    rng = random.Random(seed)
    bm = bmesh.new()
    post = _sweep(bm, [Vector((0, 0, -0.2)), Vector((0, 0, 1.3))], [0.09, 0.08], 6)
    _color_faces(bm, post, lambda co, n: (0.30, 0.20, 0.14))
    bird = []
    bird += _blob(bm, (0, 0, 1.48), 0.13, rng, 1.0, 1)
    bird += _blob(bm, (0.0, -0.1, 1.62), 0.08, rng, 1.0, 1)
    ret = bmesh.ops.create_cone(bm, cap_ends=True, segments=4, radius1=0.025, radius2=0.0, depth=0.1)
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "X"), verts=ret["verts"])
    bmesh.ops.translate(bm, vec=(0, -0.21, 1.61), verts=ret["verts"])
    beak = list({f for v in ret["verts"] for f in v.link_faces})
    tail = _sweep(bm, [Vector((0, 0.1, 1.45)), Vector((0, 0.32, 1.35))], [0.06, 0.02], 4)
    _color_faces(bm, bird + tail, lambda co, n: (0.06, 0.05, 0.09))
    _color_faces(bm, beak, lambda co, n: (0.85, 0.6, 0.1))
    for f in bird:
        f.smooth = True
    bm.normal_update()
    return bm, [material("crow_vc", 0.5)], 1.75


def pumpkin_pile(seed):
    bm = bmesh.new()
    rng = random.Random(seed)
    for _ in range(5):
        r = rng.uniform(0.15, 0.3)
        sub = bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=r)
        c = Vector((rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5), r * 0.7))
        for v in sub["verts"]:
            k = _rib(math.atan2(v.co.y, v.co.x), 0.1)
            v.co = Vector((v.co.x * k, v.co.y * k, v.co.z * 0.78)) + c
        fs = list({f for v in sub["verts"] for f in v.link_faces})
        _color_faces(bm, fs, lambda co, n: lerp(PUMP_DK, PUMP, 0.4 + 0.6 * max(0.0, n.z)))
        for f in fs:
            f.smooth = True
    bm.normal_update()
    return bm, [material("pumpkin_vc", 0.6)], 0.6


# image name of the old painted card -> 3D builder and how many variants to make
VARIANTS = {
    "maple_orange": (lambda s: tree("maple_orange", s), 3),
    "maple_red": (lambda s: tree("maple_red", s), 3),
    "apple_tree": (lambda s: tree("apple", s), 3),
    "birch": (lambda s: tree("birch", s), 2),
    "pine_blue": (lambda s: tree("pine", s), 3),
    "dead_tree": (lambda s: tree("dead", s), 2),
    "haunted_tree": (lambda s: tree("dead", s + 50), 2),
    "lantern_tree": (lambda s: tree("lantern", s), 2),
    "grass_tuft": (lambda s: grass_clump(s), 3),
    "tall_grass": (lambda s: grass_clump(s, tall=True), 3),
    "leaf_pile": (leaf_pile, 2),
    "fern": (bush, 2),
    "bush_heather": (bush, 2),
    "corn": (corn_stalk, 3),
    "cattails": (cattails, 2),
    "mushrooms": (mushrooms, 2),
    "hay_bales": (hay_bales, 1),
    "scarecrow": (scarecrow, 1),
    "crow_post": (crow_post, 1),
    "pumpkin_pile": (pumpkin_pile, 2),
}
