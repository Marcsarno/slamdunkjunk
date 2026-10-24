"""Model Brittany's golf bag (Marc's mock-up, art_src/bag/bag_mockup.png): a plum stand bag with orange
piping, a black base, a front pocket with a jack-o'-lantern on it, a padded handle, the two stand legs
kicked out behind, and three clubs showing (driver, iron, putter). Low-poly, vertex-coloured; it stands
beside her on every shot so the camera's swing round her reads as a real 3D scene.

usage: python3 -I make_bag.py <out.glb> [--preview <png>]     (bpy as a module, headless)

Blender: z up, the pocket toward -y, the base at the origin (glTF: the pocket toward +z). About 1.25 m
to the top of the driver.
"""
import math
import sys

import bpy  # noqa: I001  (bpy must load before bmesh)
import bmesh
from mathutils import Matrix, Vector

args = sys.argv[1:]
OUT = [a for a in args if not a.startswith("--")][0]
PREVIEW = args[args.index("--preview") + 1] if "--preview" in args else None

PLUM = (0.46, 0.2, 0.4)          # bright enough to read as plum by moonlight
PLUM_DARK = (0.32, 0.13, 0.28)
ORANGE = (0.95, 0.42, 0.08)
BLACK = (0.035, 0.035, 0.04)
STEEL = (0.55, 0.56, 0.6)
GUNMETAL = (0.16, 0.16, 0.18)
COPPER = (0.55, 0.3, 0.16)

LEAN = math.radians(14.0)        # the bag tips back onto its legs
H = 0.86                         # base to the top of the collar

bpy.ops.wm.read_factory_settings(use_empty=True)
col = bpy.context.scene.collection
bm = bmesh.new()
lay = bm.loops.layers.color.new("Col")


def paint(faces, c):
    for f in faces:
        for lp in f.loops:
            lp[lay] = (*c, 1.0)


def faces_of(verts):
    return list({f for v in verts for f in v.link_faces})


def place(verts, m):
    bmesh.ops.transform(bm, matrix=m, verts=verts)


def tube(z0, z1, r0, r1, c, seg=14, sx=1.0, m=Matrix()):
    """A tapered tube (capped) from z0 to z1, squashed front-to-back by sx."""
    ret = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r0, radius2=r1, depth=z1 - z0)
    v = ret["verts"]
    place(v, Matrix.Translation((0, 0, (z0 + z1) / 2)))
    place(v, Matrix.Diagonal((1.0, sx, 1.0, 1.0)))
    place(v, m)
    paint(faces_of(v), c)
    return v


def box(center, size, c, m=Matrix()):
    ret = bmesh.ops.create_cube(bm, size=1.0)
    v = ret["verts"]
    place(v, Matrix.Diagonal((*size, 1.0)))
    place(v, Matrix.Translation(center))
    place(v, m)
    paint(faces_of(v), c)
    return v


def rod(a, b, r, c, seg=6):
    """A thin cylinder from point a to point b."""
    a, b = Vector(a), Vector(b)
    d = b - a
    ret = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=d.length)
    v = ret["verts"]
    rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
    place(v, Matrix.Translation((a + b) / 2) @ rot)
    paint(faces_of(v), c)


lean = Matrix.Rotation(LEAN, 4, "X")       # top back toward +y

# the bag itself: base, body, collar with its piping
tube(0.0, 0.09, 0.15, 0.155, BLACK, sx=0.85, m=lean)
tube(0.09, 0.115, 0.152, 0.152, ORANGE, sx=0.85, m=lean)
tube(0.115, H - 0.1, 0.14, 0.15, PLUM, sx=0.85, m=lean)
tube(H - 0.1, H - 0.085, 0.158, 0.158, ORANGE, sx=0.85, m=lean)
tube(H - 0.085, H - 0.01, 0.155, 0.155, PLUM_DARK, sx=0.85, m=lean)
tube(H - 0.01, H + 0.004, 0.16, 0.16, ORANGE, sx=0.85, m=lean)              # the rim's piping
tube(H - 0.06, H + 0.008, 0.138, 0.138, BLACK, seg=14, sx=0.85, m=lean)      # the dark mouth inside it
# piping down the front either side of the pocket, and rivets on the collar
for x in (-0.09, 0.09):
    box((x, -0.112, 0.43), (0.012, 0.012, 0.6), ORANGE, m=lean)
for x in (-0.11, 0.0, 0.11):
    box((x, -0.128, H - 0.05), (0.018, 0.012, 0.018), COPPER, m=lean)
# the front pocket: a padded block with orange piping round its edge
pk_z0, pk_z1 = 0.17, 0.52
box((0.0, -0.14, (pk_z0 + pk_z1) / 2), (0.15, 0.06, pk_z1 - pk_z0), PLUM, m=lean)
for z in (pk_z0, pk_z1):
    box((0.0, -0.172, z), (0.16, 0.012, 0.012), ORANGE, m=lean)
for x in (-0.078, 0.078):
    box((x, -0.172, (pk_z0 + pk_z1) / 2), (0.012, 0.012, pk_z1 - pk_z0), ORANGE, m=lean)
box((0.06, -0.176, 0.48), (0.01, 0.006, 0.05), BLACK, m=lean)                 # the zip pull
# the jack-o'-lantern on the pocket: an orange face with dark eyes and a grin, and a stem
jx, jy, jz = 0.0, -0.1735, 0.33
ret = bmesh.ops.create_circle(bm, cap_ends=True, segments=16, radius=0.05)
pv = ret["verts"]
place(pv, Matrix.Translation((jx, jy, jz)) @ Matrix.Rotation(math.radians(90), 4, "X") @ Matrix.Diagonal((1.12, 0.92, 1.0, 1.0)))
place(pv, lean)
paint(faces_of(pv), ORANGE)
box((jx, jy - 0.001, jz + 0.052), (0.012, 0.004, 0.02), (0.3, 0.32, 0.1), m=lean)
for ex in (-0.02, 0.02):                                                       # triangle eyes
    tri = [bm.verts.new(p) for p in ((jx + ex - 0.012, jy - 0.002, jz + 0.006), (jx + ex + 0.012, jy - 0.002, jz + 0.006),
                                        (jx + ex, jy - 0.002, jz + 0.026))]
    place(tri, lean)
    paint([bm.faces.new(tri)], (0.12, 0.04, 0.06))
for k in range(5):                                                             # the grin's teeth gaps
    mx = jx - 0.028 + k * 0.014
    box((mx, jy - 0.002, jz - 0.018 + (0.004 if k % 2 else 0.0)), (0.011, 0.002, 0.009), (0.12, 0.04, 0.06), m=lean)
# the handle: a padded black arc on the side
hc = Vector((0.155, 0.0, 0.68))
prev = None
for k in range(7):
    a = math.pi * k / 6
    p = hc + Vector((0.07 * math.sin(a) * 0.7, 0.0, 0.11 * math.cos(a)))
    if prev is not None:
        q0, q1 = lean @ prev, lean @ p
        rod(q0, q1, 0.018, BLACK)
    prev = p
# the clubs, up out of the mouth
top = lean @ Vector((0.0, 0.0, H))
for (ox, oy), length, head in (((-0.05, 0.02), 0.42, "driver"), ((0.01, -0.02), 0.36, "iron"), ((0.06, 0.03), 0.31, "putter")):
    base = lean @ Vector((ox, oy, H - 0.05))
    tip = base + Vector((ox * 1.6, 0.03, length))
    rod(base, tip, 0.008, STEEL)
    rod(base, base + Vector((0, 0, 0.08)), 0.014, BLACK)                       # the grip end sticks just out
    if head == "driver":
        ret = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=0.06)
        v = ret["verts"]
        place(v, Matrix.Translation(tip + Vector((-0.02, 0.0, 0.0))) @ Matrix.Diagonal((1.25, 0.95, 0.55, 1.0)))
        paint(faces_of(v), GUNMETAL)
        box(tip + Vector((-0.02, -0.0, 0.034)), (0.1, 0.02, 0.006), ORANGE)
    elif head == "iron":
        box(tip + Vector((0.035, 0.0, 0.01)), (0.085, 0.012, 0.05), STEEL)
    else:
        box(tip + Vector((0.045, 0.0, 0.0)), (0.1, 0.022, 0.024), GUNMETAL)
# the stand legs: from under the collar out behind to the ground, with rubber feet
for side in (-1, 1):
    a = lean @ Vector((side * 0.11, 0.1, H - 0.14))
    foot = Vector((side * 0.2, 0.52, 0.0))
    rod(a, foot, 0.009, GUNMETAL)
    rod(foot + Vector((0, 0, 0.0)), foot + Vector((0, 0, 0.045)), 0.017, BLACK)

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new("Bag")
bm.to_mesh(me)
bm.free()
ob = bpy.data.objects.new("Bag", me)
col.objects.link(ob)
mat = bpy.data.materials.new("bag")
mat.use_nodes = True
nt = mat.node_tree
attr = nt.nodes.new("ShaderNodeVertexColor")
attr.layer_name = "Col"
nt.links.new(attr.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
nt.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.75
me.materials.append(mat)
for p in me.polygons:
    p.use_smooth = False
ob.select_set(True)
# only "Col" goes out, as COLOR_0 (anything else would come first and read as white)
for ca in [c for c in me.color_attributes if c.name != "Col"]:
    me.color_attributes.remove(ca)
me.color_attributes.active_color = me.color_attributes["Col"]
me.color_attributes.render_color_index = me.color_attributes.active_color_index
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True, export_apply=True,
                          export_vertex_color="ACTIVE", export_yup=True)
print("wrote", OUT, "faces", len(me.polygons))

if PREVIEW:
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 600, 800
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    col.objects.link(cam)
    cam.location = (1.1, -1.9, 1.0)
    cam.rotation_euler = (math.radians(78), 0, math.radians(30))
    sc.camera = cam
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(20))
    col.objects.link(sun)
    world = bpy.data.worlds.new("W")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.85, 0.83, 0.8, 1)
    sc.world = world
    sc.render.filepath = PREVIEW
    bpy.ops.render.render(write_still=True)
