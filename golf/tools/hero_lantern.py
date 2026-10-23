"""Model the giant jack-o'-lantern that sits by every tee (the opening shot of each hole swings round it).

usage: python3 -I hero_lantern.py <out.glb> [--preview <png>] [--ratio <share of the body's triangles kept>]

A ribbed pumpkin about a meter across with a real shell (solidify), a face carved through it with
booleans (triangle eyes and nose, a toothy grin), the lid's cut line, a twisted stem with a curling
vine, two leaves at its foot, and a candle inside. Materials are named by role so Godot swaps in its
own (hero_skin, hero_flesh, hero_cut, hero_stem, hero_leaf, hero_wax, hero_flame); colors are vertex
colors in "Col". Blender: z up, the face toward -y, the base at the origin (glTF: face toward +z).
"""
import math
import random
import sys

import bpy  # noqa: I001  (bpy must load before bmesh)
import bmesh
from mathutils import Vector, noise

R = 0.5            # radius across the lobes, meters
SQUASH = 0.78      # height / width
LOBES = 10
SHELL = 0.045
LID_POLAR = 0.62   # the lid's cut line: how far down from the top (radians from the pole)

random.seed(4)
args = [a for a in sys.argv[1:] if not a.startswith("--")]
OUT = args[0]
PREVIEW = sys.argv[sys.argv.index("--preview") + 1] if "--preview" in sys.argv else None
DECIMATE = float(sys.argv[sys.argv.index("--ratio") + 1]) if "--ratio" in sys.argv else 0.22   # share of the body's triangles kept

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection


def material(name, color):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    attr = nt.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "Col"
    nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    m.diffuse_color = (*color, 1)
    return m


M_SKIN = material("hero_skin", (0.95, 0.45, 0.08))
M_FLESH = material("hero_flesh", (1.0, 0.75, 0.3))
M_CUT = material("hero_cut", (1.0, 0.82, 0.45))
M_STEM = material("hero_stem", (0.35, 0.3, 0.12))
M_LEAF = material("hero_leaf", (0.2, 0.35, 0.1))
M_WAX = material("hero_wax", (0.95, 0.9, 0.78))
M_FLAME = material("hero_flame", (1.0, 0.8, 0.3))


def obj(name, bm, mats):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    return ob


def paint(bm, fn):
    lay = bm.loops.layers.color.get("Col") or bm.loops.layers.color.new("Col")
    for f in bm.faces:
        for lp in f.loops:
            lp[lay] = (*fn(lp.vert.co, f), 1.0)


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def lid_line(phi):
    """Polar angle of the lid's zigzag cut at azimuth phi."""
    tri = abs(((phi * 9 / math.pi) % 2) - 1)          # a zigzag, 9 teeth round
    return LID_POLAR + 0.05 * (tri - 0.5)


# ---- the body: a sphere pushed into lobes, squashed, dimpled top and bottom, a little uneven ----
bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, u_segments=128, v_segments=96, radius=R)
for v in bm.verts:
    p = v.co.copy()
    phi = math.atan2(p.y, p.x)
    polar = math.acos(max(-1.0, min(1.0, p.z / R)))
    lobe = abs(math.cos(phi * LOBES / 2)) ** 0.45               # rounded lobes, pinched grooves
    rr = 0.9 + 0.1 * lobe
    rr *= 1.0 + 0.035 * noise.noise(p * 3.0)                    # not quite symmetric
    s = math.sin(polar)
    z = p.z * SQUASH
    # dimples: the top sinks round the stem, the bottom sits flat
    z -= 0.16 * R * math.exp(-(s / 0.28) ** 2) * (1 if p.z > 0 else -0.6)
    z = max(z, -R * SQUASH * 0.9)
    # the lid's cut: a narrow groove along the zigzag line
    d = abs(polar - lid_line(phi))
    groove = math.exp(-(d / 0.012) ** 2)
    k = rr * (1.0 - 0.025 * groove)
    v.co = Vector((p.x * k, p.y * k, z * (1.0 - 0.02 * groove)))
bm.normal_update()

DARK, MID, LIGHT, TOP = (0.42, 0.12, 0.02), (0.93, 0.38, 0.05), (1.0, 0.55, 0.12), (0.85, 0.55, 0.12)


def skin(co, f):
    phi = math.atan2(co.y, co.x)
    lobe = abs(math.cos(phi * LOBES / 2))
    c = mix(DARK, MID, 0.15 + 1.3 * lobe)
    c = mix(c, LIGHT, (lobe - 0.75) * 2.5)
    h = co.z / (R * SQUASH)
    c = mix(c, TOP, (h - 0.55) * 2.0)                             # sun-faded shoulders
    c = mix(c, DARK, (-h - 0.35) * 1.2)                           # darker underneath
    c = mix(c, (0.75, 0.35, 0.06), 0.25 * (noise.noise(co * 9.0) + 0.3))   # blotches
    polar = math.acos(max(-1.0, min(1.0, co.z / max(co.length, 1e-6))))
    if abs(polar - lid_line(phi)) < 0.022:
        c = (0.2, 0.06, 0.01)
    return c


paint(bm, skin)
body = obj("Pumpkin", bm, [M_SKIN, M_FLESH, M_CUT])
body.location.z = R * SQUASH * 0.9

# the shell: thickness inward, the inside and the cut edges get their own materials
sol = body.modifiers.new("Shell", "SOLIDIFY")
sol.thickness = SHELL
sol.offset = -1.0
sol.use_rim = True
sol.material_offset = 1
sol.material_offset_rim = 2
bpy.context.view_layer.objects.active = body
bpy.ops.object.modifier_apply(modifier="Shell")

# ---- the face: cutters pushed straight through the front of the shell ----
FACE = [
    [(-0.62, 0.12), (-0.16, 0.08), (-0.42, 0.55)],                           # eyes
    [(0.16, 0.08), (0.62, 0.12), (0.42, 0.55)],
    [(-0.13, -0.08), (0.13, -0.08), (0.0, 0.15)],                            # nose
    [(-0.7, -0.14), (-0.5, -0.2), (-0.44, -0.1), (-0.3, -0.22), (-0.2, -0.12),  # grin, teeth up and down
     (-0.08, -0.25), (0.08, -0.25), (0.2, -0.12), (0.3, -0.22), (0.44, -0.1), (0.5, -0.2), (0.7, -0.14),
     (0.55, -0.38), (0.36, -0.5), (0.26, -0.38), (0.12, -0.55), (-0.02, -0.42), (-0.16, -0.55),
     (-0.28, -0.4), (-0.4, -0.52), (-0.56, -0.38)],
]
centre_z = body.location.z
for i, shape in enumerate(FACE):
    cb = bmesh.new()
    front = [cb.verts.new((u * R * 0.95, -R * 1.4, centre_z + v * R * SQUASH)) for u, v in shape]
    back = [cb.verts.new((u * R * 0.95, -R * 0.2, centre_z + v * R * SQUASH)) for u, v in shape]
    n = len(shape)
    cb.faces.new(front)
    cb.faces.new(list(reversed(back)))
    for j in range(n):
        cb.faces.new([front[j], front[(j + 1) % n], back[(j + 1) % n], back[j]])
    bmesh.ops.recalc_face_normals(cb, faces=cb.faces)
    paint(cb, lambda co, f: (1.0, 0.8, 0.42))
    cutter = obj(f"Cut_{i}", cb, [M_CUT])
    b = body.modifiers.new(f"Carve_{i}", "BOOLEAN")
    b.operation = "DIFFERENCE"
    b.solver = "EXACT"
    b.material_mode = "TRANSFER"
    b.object = cutter
    bpy.ops.object.modifier_apply(modifier=b.name)
    bpy.data.objects.remove(cutter)

# the shell's inside and the cut faces: warm flesh colors
me = body.data
cl = me.color_attributes["Col"]
for poly in me.polygons:
    if poly.material_index in (1, 2):
        c = (1.0, 0.72, 0.28) if poly.material_index == 1 else (1.0, 0.85, 0.5)
        for li in poly.loop_indices:
            cl.data[li].color = (*c, 1.0)

# fewer triangles where the shell is smooth (the lobes), keeping them where it bends (the carved face,
# the lid's groove): the full sphere was ~50k triangles for a meter-wide prop, a lot for a phone
if DECIMATE < 1.0:
    dec = body.modifiers.new("Lighter", "DECIMATE")
    dec.decimate_type = "COLLAPSE"
    dec.ratio = DECIMATE
    dec.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=dec.name)

# ---- the stem: a twisted, ridged, tapering stalk leaning over, flared where it meets the pumpkin ----
top_z = body.location.z + R * SQUASH - 0.16 * R
bm = bmesh.new()
ring_n, rings = 12, 14
prev = None
first = None
for k in range(rings + 1):
    t = k / rings
    rad = 0.06 * (1.0 - 0.35 * t) * (1.0 + 1.2 * max(0.0, 0.2 - t) / 0.2)     # flared foot
    cx, cy, cz = 0.07 * t * t, 0.025 * t * t, top_z - 0.03 + 0.2 * t
    ring = []
    for j in range(ring_n):
        a = j / ring_n * math.tau + t * 0.8
        ridge = 1.0 + 0.12 * math.cos(a * 6)
        ring.append(bm.verts.new((cx + math.cos(a) * rad * ridge, cy + math.sin(a) * rad * ridge, cz)))
    if prev:
        for j in range(ring_n):
            bm.faces.new([prev[j], prev[(j + 1) % ring_n], ring[(j + 1) % ring_n], ring[j]])
    else:
        first = ring
    prev = ring
bm.faces.new(list(reversed(first)))
bm.faces.new(prev)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
paint(bm, lambda co, f: mix((0.25, 0.3, 0.1), (0.55, 0.48, 0.28), (co.z - top_z) / 0.2 + 0.1 * noise.noise(co * 40)))
obj("Stem", bm, [M_STEM])

# a vine curling off the stem
curve = bpy.data.curves.new("Vine", "CURVE")
curve.dimensions = "3D"
curve.bevel_depth = 0.008
curve.bevel_resolution = 2
sp = curve.splines.new("POLY")
pts = []
for k in range(60):
    t = k / 59
    a = t * math.tau * 2.3
    rad = 0.04 + 0.14 * (1 - t)
    pts.append((0.02 + math.cos(a) * rad * 0.9 - 0.1 * t, -0.04 + math.sin(a) * rad, top_z + 0.04 + 0.12 * t + 0.03 * math.sin(a)))
sp.points.add(len(pts) - 1)
for p, q in zip(sp.points, pts):
    p.co = (*q, 1.0)
vine = bpy.data.objects.new("Vine", curve)
col.objects.link(vine)
bpy.context.view_layer.objects.active = vine
vine.select_set(True)
bpy.ops.object.convert(target="MESH")
vine = bpy.context.view_layer.objects.active
vbm = bmesh.new()
vbm.from_mesh(vine.data)
paint(vbm, lambda co, f: (0.25, 0.38, 0.1))
vbm.to_mesh(vine.data)
vbm.free()
vine.data.materials.clear()
vine.data.materials.append(M_STEM)


# ---- two leaves at its foot: five-lobed, curling up at the edges ----
def leaf(name, at, angle, size):
    lb = bmesh.new()
    n = 40
    centre = lb.verts.new((0, 0, 0))
    rim = []
    for j in range(n):
        a = j / n * math.tau
        rr = size * (0.6 + 0.4 * abs(math.cos(a * 2.5)) ** 0.7)
        rim.append(lb.verts.new((math.cos(a) * rr, math.sin(a) * rr, 0)))
    for j in range(n):
        lb.faces.new([centre, rim[j], rim[(j + 1) % n]])
    bmesh.ops.subdivide_edges(lb, edges=list(lb.edges), cuts=2, use_grid_fill=True)
    for v in lb.verts:
        d = v.co.length / size
        v.co.z = 0.35 * size * d * d + 0.02 * noise.noise(v.co * 12)
        x, y = v.co.x, v.co.y
        v.co.x = at[0] + x * math.cos(angle) - y * math.sin(angle)
        v.co.y = at[1] + x * math.sin(angle) + y * math.cos(angle)
        v.co.z += 0.01
    lb.normal_update()
    paint(lb, lambda co, f: mix((0.3, 0.5, 0.14), (0.5, 0.68, 0.22), 0.5 + 0.5 * noise.noise(co * 18)))
    obj(name, lb, [M_LEAF])


leaf("Leaf_0", (-0.48, -0.28), 0.6, 0.26)
leaf("Leaf_1", (0.52, -0.08), 2.4, 0.22)

# ---- a candle inside, with its flame ----
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.07, radius2=0.065, depth=0.2)
bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0.05, body.location.z - R * SQUASH * 0.9 + SHELL + 0.12))
paint(bm, lambda co, f: (0.95, 0.9, 0.78))
obj("Candle", bm, [M_WAX])
bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.035)
for v in bm.verts:
    v.co.z *= 2.0 if v.co.z > 0 else 1.0
bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0.05, body.location.z - R * SQUASH * 0.9 + SHELL + 0.26))
paint(bm, lambda co, f: (1.0, 0.85, 0.4))
obj("Flame", bm, [M_FLAME])

# smooth shading, with the carved edges and the lid groove kept crisp
for ob in col.objects:
    if ob.type == "MESH":
        for poly in ob.data.polygons:
            poly.use_smooth = True
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(50))
        ob.select_set(False)
for ob in col.objects:
    ob.select_set(True)
    if ob.type == "MESH":
        # only "Col" goes out, as COLOR_0 (anything else would come first and read as white)
        for ca in [c for c in ob.data.color_attributes if c.name != "Col"]:
            ob.data.color_attributes.remove(ca)
        ob.data.color_attributes.active_color = ob.data.color_attributes["Col"]
        ob.data.color_attributes.render_color_index = ob.data.color_attributes.active_color_index
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True, export_apply=True,
                          export_vertex_color="ACTIVE", export_yup=True)
tris = sum(len(o.data.polygons) for o in col.objects if o.type == "MESH")
print("wrote", OUT, "faces", tris)

if PREVIEW:
    for m, (base, emit) in {M_SKIN: (None, 0), M_FLESH: ((1, 0.6, 0.15), 3), M_CUT: ((1, 0.7, 0.3), 2),
                           M_FLAME: ((1, 0.8, 0.3), 20)}.items():
        if emit:
            bsdf = m.node_tree.nodes["Principled BSDF"]
            bsdf.inputs["Emission Color"].default_value = (*base, 1)
            bsdf.inputs["Emission Strength"].default_value = emit
    light = bpy.data.lights.new("Candle", "POINT")
    light.energy = 60
    light.color = (1, 0.6, 0.2)
    lo = bpy.data.objects.new("CandleLight", light)
    lo.location = (0, 0.05, body.location.z - 0.05)
    col.objects.link(lo)
    moon = bpy.data.lights.new("Moon", "SUN")
    moon.energy = 1.5
    moon.color = (0.6, 0.65, 1.0)
    mo = bpy.data.objects.new("Moon", moon)
    mo.rotation_euler = (0.9, 0.2, -0.6)
    col.objects.link(mo)
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    cam.location = (0.9, -2.2, 0.95)
    col.objects.link(cam)
    d = Vector((0, 0, 0.42)) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    scene.world = bpy.data.worlds.new("W")
    scene.world.color = (0.01, 0.01, 0.03)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 48
    scene.cycles.device = "CPU"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.filepath = PREVIEW
    bpy.ops.render.render(write_still=True)
    print("preview", PREVIEW)
