"""Style test: a small midnight-graveyard patch mixing modeled 3D props with painted 2D cards.

Run:  python3 graveyard_test.py <cutouts_dir> <out_dir>
Everything is vertex-colored low-poly geometry so it exports to glTF for Godot unchanged.
"""
import sys, math, random, os
import bpy, bmesh
from mathutils import Vector, Matrix, noise

CUT, OUT = sys.argv[-2], sys.argv[-1]
os.makedirs(OUT, exist_ok=True)
random.seed(7)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection


# ---------- helpers ----------
def new_obj(name, bm, mats):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    for m in mats:
        me.materials.append(m)
    col.objects.link(ob)
    return ob


def vcol_layer(bm):
    return bm.loops.layers.color.get("Col") or bm.loops.layers.color.new("Col")


def paint(bm, fn):
    """fn(world_pos, normal, face) -> (r,g,b)"""
    lay = vcol_layer(bm)
    for f in bm.faces:
        for l in f.loops:
            c = fn(l.vert.co, f.normal, f)
            l[lay] = (*c, 1.0)


def vc_material(name, rough=0.85, emit=None, emit_strength=0.0):
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
        bsdf.inputs["Emission Strength"].default_value = emit_strength
    return m


def card_material(name, path, light_mix=0.55):
    """Painted cutout: lit by the scene but keeps most of its painted value."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = light_mix
    bsdf.inputs["Roughness"].default_value = 1.0
    m.surface_render_method = "DITHERED"
    return m, tex.image.size


def card(name, path, height, loc, face_to=None, light_mix=0.55):
    mat, (w, h) = card_material(name + "_mat", path, light_mix)
    width = height * w / h
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in [(-width / 2, 0, 0), (width / 2, 0, 0), (width / 2, 0, height), (-width / 2, 0, height)]]
    f = bm.faces.new(vs)
    uv = bm.loops.layers.uv.new()
    for l, c in zip(f.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        l[uv].uv = c
    ob = new_obj(name, bm, [mat])
    ob.location = loc
    if face_to is not None:
        d = Vector(face_to) - Vector(loc)
        ob.rotation_euler = (0, 0, math.atan2(d.y, d.x) - math.pi / 2 + math.pi)
    return ob


def tube(bm, p0, p1, r0, r1, sides=8):
    """Tapered cylinder between two points, capped with a small dome."""
    p0, p1 = Vector(p0), Vector(p1)
    axis = (p1 - p0)
    q = axis.to_track_quat("Z", "Y")
    rot = q.to_matrix().to_4x4()
    ret = bmesh.ops.create_cone(bm, cap_ends=True, segments=sides, radius1=r0, radius2=r1, depth=axis.length)
    m = Matrix.Translation((p0 + p1) / 2) @ rot
    bmesh.ops.transform(bm, matrix=m, verts=ret["verts"])
    return ret["verts"]


def ball(bm, p, r, seg=8):
    ret = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(4, seg // 2), radius=r)
    bmesh.ops.translate(bm, vec=Vector(p), verts=ret["verts"])
    return ret["verts"]


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


# ---------- ground ----------
def fairway_x(y):
    return 0.9 * math.sin(y * 0.18)


def height(x, y):
    h = 0.35 * noise.noise(Vector((x * 0.12, y * 0.12, 0.3)))
    h += 0.08 * noise.noise(Vector((x * 0.6, y * 0.6, 1.7)))
    side = abs(x - fairway_x(y))
    h += max(0.0, side - 3.2) ** 1.3 * 0.12        # rough banks rise toward the edges
    return h


bm = bmesh.new()
NX, NY, W, L = 66, 100, 22.0, 40.0
grid = []
for j in range(NY + 1):
    row = []
    for i in range(NX + 1):
        x = -W / 2 + W * i / NX
        y = -6 + L * j / NY
        row.append(bm.verts.new((x, y, height(x, y))))
    grid.append(row)
for j in range(NY):
    for i in range(NX):
        bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
bm.normal_update()

FAIR = (0.36, 0.56, 0.17)
FAIR2 = (0.26, 0.43, 0.12)
ROUGH = (0.17, 0.28, 0.10)
DIRT = (0.36, 0.25, 0.17)


def ground_col(co, n, f):
    side = abs(co.x - fairway_x(co.y))
    stripe = FAIR if int((co.y + 6) / 2.2) % 2 == 0 else FAIR2
    t = min(1.0, max(0.0, (side - 2.4) / 0.6))
    c = lerp(stripe, ROUGH, t)
    v = 0.85 + 0.25 * noise.noise(Vector((co.x * 0.4, co.y * 0.4, 5))) + 0.12 * noise.noise(Vector((co.x * 2.5, co.y * 2.5, 9)))
    c = tuple(k * v for k in c)
    # tee box: slightly brighter, crisp square
    if abs(co.x) < 1.6 and -1.2 < co.y < 1.6:
        c = (0.36, 0.56, 0.18)
    return c


paint(bm, ground_col)
ground = new_obj("Ground", bm, [vc_material("ground_vc", 0.95)])

STONE = (0.42, 0.40, 0.46)
STONE_DK = (0.20, 0.19, 0.24)
MOSS = (0.24, 0.33, 0.12)


def stone_col(base_z, h):
    def fn(co, n, f):
        t = max(0.0, min(1.0, (co.z - base_z) / max(h, 0.01)))
        c = lerp(STONE_DK, STONE, 0.35 + 0.65 * t)
        if n.z > 0.6 and co.z - base_z > h * 0.6:
            c = lerp(c, MOSS, 0.55)
        if t < 0.12:
            c = lerp(c, MOSS, 0.5)
        v = 0.9 + 0.2 * noise.noise(co * 3.0)
        return tuple(k * v for k in c)
    return fn


stone_mat = vc_material("stone_vc", 0.9)


def finish_stone(bm, name, loc, rot_z, tilt, h):
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.035, segments=2, affect="EDGES", clamp_overlap=True)
    # small chips / wobble so nothing reads as a perfect CAD block
    for v in bm.verts:
        v.co += Vector((noise.noise(v.co * 4.0), noise.noise(v.co * 4.0 + Vector((3, 1, 2))), 0)) * 0.018
    bm.normal_update()
    paint(bm, stone_col(0.0, h))
    ob = new_obj(name, bm, [stone_mat])
    ob.location = (loc[0], loc[1], height(loc[0], loc[1]) - 0.08)
    ob.rotation_euler = (tilt[0], tilt[1], rot_z)
    return ob


def headstone(name, loc, w=0.7, h=1.0, d=0.16, rot_z=0.0, tilt=(0, 0)):
    bm = bmesh.new()
    pts = [(-w / 2, 0), (w / 2, 0)]
    arc_c = h - w / 2
    for k in range(9):
        a = math.pi * k / 8
        pts.append((w / 2 * math.cos(a), arc_c + w / 2 * math.sin(a)))
    verts = [bm.verts.new((x, -d / 2, z)) for x, z in pts]
    face = bm.faces.new(verts)
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, vec=(0, d, 0), verts=[e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)])
    bm.normal_update()
    # recessed engraving panel on the front face
    front = min(bm.faces, key=lambda f: f.calc_center_median().y)
    bmesh.ops.inset_region(bm, faces=[front], thickness=w * 0.14, depth=-0.025)
    ob = finish_stone(bm, name, loc, rot_z, tilt, h)
    # carved "RIP": real text converted to a thin dark mesh sitting in the recess
    cu = bpy.data.curves.new(name + "_rip", "FONT")
    cu.body = "R.I.P."
    cu.size = w * 0.26
    cu.align_x = "CENTER"
    cu.extrude = 0.004
    tob = bpy.data.objects.new(name + "_rip", cu)
    col.objects.link(tob)
    bpy.context.view_layer.update()
    tme = bpy.data.meshes.new_from_object(tob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(tob)
    tm = bmesh.new()
    tm.from_mesh(tme)
    bmesh.ops.rotate(tm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "X"), verts=tm.verts)
    bmesh.ops.translate(tm, vec=(0, -d / 2 + 0.024, h * 0.55), verts=tm.verts)
    paint(tm, lambda co, n, f: (0.10, 0.09, 0.12))
    rip = new_obj(name + "_RIP", tm, [stone_mat])
    rip.parent = ob
    return ob


def cross_stone(name, loc, h=1.3, rot_z=0.0, tilt=(0, 0)):
    bm = bmesh.new()
    for sx, sy, sz, z in [(0.18, 0.15, h, h / 2), (0.75, 0.15, 0.18, h * 0.7), (0.5, 0.34, 0.2, 0.1)]:
        r = bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=r["verts"])
        bmesh.ops.translate(bm, vec=(0, 0, z), verts=r["verts"])
    return finish_stone(bm, name, loc, rot_z, tilt, h)


def obelisk(name, loc, h=2.2, rot_z=0.0):
    bm = bmesh.new()
    r = bmesh.ops.create_cone(bm, cap_ends=True, segments=4, radius1=0.32, radius2=0.22, depth=h)
    bmesh.ops.translate(bm, vec=(0, 0, h / 2 + 0.25), verts=r["verts"])
    r2 = bmesh.ops.create_cone(bm, cap_ends=True, segments=4, radius1=0.24, radius2=0.0, depth=0.4)
    bmesh.ops.translate(bm, vec=(0, 0, h + 0.45), verts=r2["verts"])
    r3 = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(0.85, 0.85, 0.3), verts=r3["verts"])
    bmesh.ops.translate(bm, vec=(0, 0, 0.12), verts=r3["verts"])
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 4, 3, "Z"), verts=r["verts"] + r2["verts"])
    return finish_stone(bm, name, loc, rot_z, (0, 0), h + 0.6)


# ---------- jack-o'-lantern ----------
PUMP = (0.95, 0.42, 0.06)
PUMP_DK = (0.55, 0.18, 0.03)
STEM = (0.30, 0.22, 0.10)
glow_mat = vc_material("glow", 0.5, emit=(1.0, 0.55, 0.12), emit_strength=14.0)
pumpkin_mat = vc_material("pumpkin_vc", 0.6)


FACE_SHAPES = [
    [(-0.58, 0.10), (-0.14, 0.10), (-0.38, 0.52)],                     # left eye
    [(0.14, 0.10), (0.58, 0.10), (0.38, 0.52)],                        # right eye
    [(-0.10, -0.06), (0.10, -0.06), (0.0, 0.13)],                      # nose
    [(-0.66, -0.12), (-0.40, -0.22), (-0.30, -0.12), (-0.16, -0.24), (0.0, -0.14),
     (0.16, -0.24), (0.30, -0.12), (0.40, -0.22), (0.66, -0.12),
     (0.42, -0.42), (0.24, -0.34), (0.10, -0.50), (-0.06, -0.38), (-0.24, -0.50), (-0.42, -0.40)],  # grin
]


def rib(phi, amp):
    return 1.0 + amp * math.cos(phi * 8)


def jack(name, loc, r=0.38, rot_z=0.0, light=True):
    RIB, SQ = 0.11, 0.8
    bm = bmesh.new()
    ret = bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=18, radius=r)
    for v in ret["verts"]:
        phi = math.atan2(v.co.y, v.co.x)
        k = rib(phi, RIB)
        v.co.x *= k
        v.co.y *= k
        v.co.z *= SQ
        if v.co.z > r * SQ * 0.82:
            v.co.z -= (v.co.z - r * SQ * 0.82) * 0.75      # sunken crown around the stem
    bm.normal_update()
    lay = vcol_layer(bm)
    for f in bm.faces:
        for l in f.loops:
            phi = math.atan2(l.vert.co.y, l.vert.co.x)
            groove = 0.5 + 0.5 * math.cos(phi * 8)
            c = lerp(PUMP_DK, PUMP, 0.25 + 0.75 * groove)
            c = lerp(PUMP_DK, c, min(1, 0.35 + (l.vert.co.z + r) / (1.6 * r)))
            l[lay] = (*c, 1)
    sv = tube(bm, (0, 0, r * SQ * 0.6), (0.07, 0.04, r * 1.05), 0.065, 0.035, 6)
    for f in bm.faces:
        if all(v in sv for v in f.verts):
            for l in f.loops:
                l[lay] = (*STEM, 1)
    # carved face: flat shapes, densified, then wrapped onto the front of the shell (emissive)
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
        k = rib(math.atan2(y, x), RIB)
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
    bm.normal_update()
    ob = new_obj(name, bm, [pumpkin_mat, glow_mat])
    ob.location = (loc[0], loc[1], height(loc[0], loc[1]) + r * SQ * 0.85)
    ob.rotation_euler = (0, 0, rot_z)
    if light:
        ld = bpy.data.lights.new(name + "_light", "POINT")
        ld.energy = 140
        ld.color = (1.0, 0.5, 0.15)
        ld.shadow_soft_size = 0.2
        ld.use_shadow = False          # sits inside the shell: lights the ground, not the pumpkin skin
        lo = bpy.data.objects.new(name + "_light", ld)
        lo.location = ob.location + Vector((0, 0, -r * 0.2))
        col.objects.link(lo)
    return ob


# ---------- skeleton arm clawing out of a fresh grave ----------
BONE = (0.86, 0.82, 0.70)
BONE_DK = (0.45, 0.40, 0.32)


def skeleton_arm(name, loc):
    bm = bmesh.new()
    parts = []
    elbow = Vector((0, 0.05, -0.05))
    wrist = Vector((0.10, -0.10, 0.42))
    parts += tube(bm, elbow, wrist, 0.05, 0.04, 7)
    parts += tube(bm, elbow + Vector((0.05, 0.02, 0)), wrist + Vector((0.04, 0.03, -0.02)), 0.035, 0.03, 6)
    parts += ball(bm, wrist + Vector((0.02, 0, 0.02)), 0.06, 8)
    # fingers: splayed, curled like it's grabbing at the air
    knuckle_base = wrist + Vector((0.02, -0.02, 0.1))
    for k, spread in enumerate([-0.11, -0.04, 0.03, 0.10]):
        base = knuckle_base + Vector((spread, 0, 0.02 - abs(spread) * 0.3))
        parts += tube(bm, wrist + Vector((spread * 0.4, 0, 0.03)), base, 0.018, 0.016, 5)
        p = base
        dirv = Vector((spread * 1.5, -0.25, 1.0)).normalized()
        seg = [0.11, 0.08, 0.06]
        for s in range(3):
            parts += ball(bm, p, 0.022, 6)
            dirv = (Matrix.Rotation(-0.55, 3, "X") @ dirv).normalized()
            q = p + dirv * seg[s]
            parts += tube(bm, p, q, 0.017, 0.013, 5)
            p = q
    # thumb
    t0 = wrist + Vector((-0.1, -0.03, 0.05))
    parts += tube(bm, wrist, t0, 0.02, 0.018, 5)
    parts += tube(bm, t0, t0 + Vector((-0.05, -0.08, 0.09)), 0.017, 0.012, 5)
    bm.normal_update()
    lay = vcol_layer(bm)
    for f in bm.faces:
        for l in f.loops:
            t = max(0, min(1, (l.vert.co.z + 0.1) / 0.9))
            l[lay] = (*lerp(BONE_DK, BONE, 0.4 + 0.6 * t), 1)
    ob = new_obj(name, bm, [vc_material("bone_vc", 0.7)])
    ob.location = (loc[0], loc[1], height(loc[0], loc[1]) + 0.18)
    ob.rotation_euler = (0.15, -0.2, 0.4)
    ob.scale = (1.5, 1.5, 1.5)
    # dirt mound with clods
    bm = bmesh.new()
    ret = bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=10, radius=1.0)
    for v in ret["verts"]:
        # rounded-rectangle grave mound, ~0.9 x 1.9 m, heaped in the middle
        x, y = v.co.x, v.co.y
        sq = max(abs(x), abs(y)) + 1e-6
        rr = math.hypot(x, y)
        boxy = rr / sq if sq > 0 else 1
        v.co.x = x * 0.45 * (0.6 + 0.4 * boxy)
        v.co.y = y * 0.95 * (0.6 + 0.4 * boxy)
        v.co.z = max(v.co.z, 0) ** 0.7 * 0.32
        v.co += Vector((0, 0, 0.05 * noise.noise(v.co * 4)))
    for k in range(7):
        a = k / 7 * math.tau + random.random()
        rr = 0.6 + random.random() * 0.4
        ball(bm, (math.cos(a) * rr * 0.55, math.sin(a) * rr * 1.1, 0.05), 0.05 + random.random() * 0.05, 5)
    bm.normal_update()
    paint(bm, lambda co, n, f: tuple(k * (0.8 + 0.4 * noise.noise(co * 5)) for k in DIRT))
    for f in bm.faces:
        f.smooth = True
    mound = new_obj(name + "_mound", bm, [vc_material("dirt_vc", 1.0)])
    mound.location = (loc[0], loc[1], height(loc[0], loc[1]) - 0.04)
    mound.rotation_euler = (0, 0, 0.4)
    return ob


# ---------- wrought-iron fence ----------
def fence(name, p0, p1, posts=9):
    bm = bmesh.new()
    p0, p1 = Vector(p0), Vector(p1)
    for k in range(posts):
        t = k / (posts - 1)
        p = p0.lerp(p1, t)
        z = height(p.x, p.y)
        hh = 1.25 if k % 4 else 1.45
        tube(bm, (p.x, p.y, z - 0.1), (p.x, p.y, z + hh), 0.025, 0.025, 5)
        r = bmesh.ops.create_cone(bm, cap_ends=True, segments=4, radius1=0.06, radius2=0.0, depth=0.16)
        bmesh.ops.translate(bm, vec=(p.x, p.y, z + hh + 0.08), verts=r["verts"])
    for zz in (0.25, 1.05):
        a = Vector((p0.x, p0.y, height(p0.x, p0.y) + zz))
        b = Vector((p1.x, p1.y, height(p1.x, p1.y) + zz))
        tube(bm, a, b, 0.022, 0.022, 4)
    bm.normal_update()
    paint(bm, lambda co, n, f: (0.08, 0.07, 0.10))
    return new_obj(name, bm, [vc_material("iron_vc", 0.45)])


# ---------- scene layout ----------
headstone("Grave_A", (-2.9, 3.6), rot_z=0.15, tilt=(0.05, -0.08))
headstone("Grave_B", (-4.2, 5.0), w=0.6, h=0.85, rot_z=-0.1, tilt=(0.0, 0.12))
cross_stone("Grave_C", (-3.0, 6.8), rot_z=0.25, tilt=(-0.06, 0.04))
headstone("Grave_D", (-5.0, 8.0), w=0.8, h=1.15, rot_z=0.05, tilt=(0.1, 0.0))
obelisk("Grave_E", (-3.8, 10.6), rot_z=0.3)
headstone("Grave_F", (4.6, 13.5), w=0.65, h=0.9, rot_z=-0.3, tilt=(0.0, -0.1))
cross_stone("Grave_G", (5.6, 15.0), h=1.1, rot_z=-0.2, tilt=(0.08, 0.1))
headstone("Grave_H", (3.4, 2.4), w=0.55, h=0.8, rot_z=-0.4, tilt=(-0.1, 0.06))
skeleton_arm("SkeletonArm", (2.3, 4.6))
fence("Fence", (-5.9, 2.0), (-5.5, 12.0), posts=12)

for k, y in enumerate([1.8, 5.5, 9.5, 14.0, 19.0, 25.0]):
    side = -1 if k % 2 == 0 else 1
    x = fairway_x(y) + side * 2.6
    jack(f"Jack_{k}", (x, y), r=0.36 + 0.05 * (k % 2), rot_z=math.atan2(-x, -1.0) * 0.6, light=(k < 5))

# painted 2D cards: trees, scarecrow, backdrop layers and the golfer
CAM = (0.4, -3.4, 1.55)
card("Tree_L1", f"{CUT}/haunted_tree.png", 4.2, (-7.5, 15.5, height(-7.5, 15.5) - 0.1), face_to=CAM)
card("Tree_R1", f"{CUT}/maple_red.png", 5.5, (7.4, 9.5, height(7.4, 9.5) - 0.1), face_to=CAM)
card("Tree_R2", f"{CUT}/maple_orange.png", 6.0, (8.5, 20.0, height(8.5, 20.0) - 0.1), face_to=CAM)
card("Tree_L2", f"{CUT}/lantern_tree.png", 5.0, (-8.6, 24.0, height(-8.6, 24.0) - 0.1), face_to=CAM)
card("Scarecrow", f"{CUT}/scarecrow.png", 2.0, (4.4, 19.0, height(4.4, 19.0) - 0.05), face_to=CAM)
card("Pines_far", f"{CUT}/pines_distant.png", 14.0, (-6.0, 46.0, -1.0), face_to=CAM, light_mix=0.35)
card("Pines_far2", f"{CUT}/pines_distant.png", 12.0, (9.0, 44.0, -1.0), face_to=CAM, light_mix=0.35)
card("Moon", f"{CUT}/moon.png", 13.0, (8.0, 70.0, 9.0), face_to=CAM, light_mix=1.4)
golfer = card("Golfer", f"{CUT}/brittany_back_address.png", 1.6, (-0.45, 0.2, height(-0.35, 0.3) - 0.02), face_to=CAM, light_mix=0.7)

# ball on the tee
bm = bmesh.new()
ball(bm, (0, 0, 0), 0.05, 12)
paint(bm, lambda co, n, f: (0.95, 0.95, 0.92))
b = new_obj("Ball", bm, [vc_material("ball_vc", 0.3)])
b.location = (0.25, 0.75, height(0.25, 0.75) + 0.07)

# ---------- lighting / world ----------
world = bpy.data.worlds.new("Night")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.05, 0.025, 0.09, 1)
bg.inputs["Strength"].default_value = 1.0
# distance haze is done in the compositor from the mist pass (world volumes are too costly)
scene.view_layers[0].use_pass_mist = True
world.mist_settings.start = 6.0
world.mist_settings.depth = 60.0
world.mist_settings.falloff = "QUADRATIC"

sun = bpy.data.lights.new("Moonlight", "SUN")
sun.energy = 3.2
sun.color = (0.70, 0.68, 1.0)
sun.angle = math.radians(3)
so = bpy.data.objects.new("Moonlight", sun)
so.rotation_euler = (math.radians(42), 0, math.radians(160))
col.objects.link(so)
fill = bpy.data.lights.new("Rim", "SUN")
fill.energy = 1.2
fill.color = (1.0, 0.55, 0.35)
fo = bpy.data.objects.new("Rim", fill)
fo.rotation_euler = (math.radians(70), 0, math.radians(20))
col.objects.link(fo)

cam = bpy.data.cameras.new("Cam")
cam.lens = 22
co = bpy.data.objects.new("Cam", cam)
co.location = CAM
target = Vector((0.0, 12.0, 0.9))
co.rotation_euler = (target - Vector(CAM)).to_track_quat("-Z", "Y").to_euler()
col.objects.link(co)
scene.camera = co

r = scene.render
r.engine = "BLENDER_EEVEE"
r.resolution_x, r.resolution_y = 1080, 1920
r.resolution_percentage = int(os.environ.get("PCT", "50"))
scene.eevee.taa_render_samples = int(os.environ.get("SAMPLES", "16"))
scene.eevee.use_shadows = True
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Punchy"
# bloom so the lanterns actually glow
try:
    tree = bpy.data.node_groups.new("Comp", "CompositorNodeTree")
    scene.compositing_node_group = tree
    tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = tree.nodes.new("CompositorNodeRLayers")
    gl = tree.nodes.new("CompositorNodeGlare")
    out = tree.nodes.new("NodeGroupOutput")
    for k, v in (("Type", "Bloom"), ("Quality", "High")):
        if k in gl.inputs:
            gl.inputs[k].default_value = v
    if hasattr(gl, "glare_type"):
        gl.glare_type = "BLOOM"
    for k, v in (("Threshold", 0.8), ("Strength", 0.6), ("Size", 0.6)):
        if k in gl.inputs:
            gl.inputs[k].default_value = v
    mul = tree.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = 0.6
    tree.links.new(rl.outputs["Mist"], mul.inputs[0])
    mix = tree.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["B"].default_value = (0.20, 0.12, 0.30, 1)
    tree.links.new(mul.outputs[0], mix.inputs["Factor"])
    tree.links.new(rl.outputs["Image"], mix.inputs["A"])
    tree.links.new(mix.outputs["Result"], gl.inputs["Image"])
    tree.links.new(gl.outputs["Image"], out.inputs[0])
    print("BLOOM ok")
except Exception as e:
    print("BLOOM skipped:", e)

r.filepath = os.path.join(OUT, "graveyard_test.png")
bpy.ops.render.render(write_still=True)
# close-up of the modeled props, to judge the 3D work on its own
co.location = (-0.2, 0.6, 1.1)
co.data.lens = 30
co.rotation_euler = (Vector((-2.2, 6.0, 0.6)) - co.location).to_track_quat("-Z", "Y").to_euler()
r.filepath = os.path.join(OUT, "graveyard_closeup.png")
bpy.ops.render.render(write_still=True)
co.location = (0.6, 1.6, 1.0)
co.rotation_euler = (Vector((2.3, 4.6, 0.7)) - co.location).to_track_quat("-Z", "Y").to_euler()
r.filepath = os.path.join(OUT, "graveyard_closeup2.png")
bpy.ops.render.render(write_still=True)

# ---------- budget report + glTF export of the 3D props ----------
deps = bpy.context.evaluated_depsgraph_get()
tot = 0
for ob in scene.objects:
    if ob.type == "MESH":
        me = ob.evaluated_get(deps).to_mesh()
        me.calc_loop_triangles()
        n = len(me.loop_triangles)
        tot += n
        print(f"TRIS {ob.name:14s} {n}")
print("TRIS TOTAL", tot)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "graveyard_test.glb"), export_format="GLB", export_lights=False)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "graveyard_test.blend"))
