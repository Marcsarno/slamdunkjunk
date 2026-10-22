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


def jack(col, name, pos, r=0.38, rot_z=0.0, carved=True):
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
    shade = random.uniform(0.85, 1.1)
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
