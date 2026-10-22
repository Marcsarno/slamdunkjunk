"""Build one hole for the game: terrain fields + Blender scene -> glTF + props list.

usage: python3 build_hole.py <hole.json> <out_dir> [--preview]

Outputs in <out_dir>:
  heights.bin, surface.bin, albedo.png, terrain.json   (from hole_gen)
  hole.glb      terrain mesh (same 1 m lattice as heights.bin), water, 3D props
  props.json    lanterns (for lights), obstacles (ball collisions), cards (painted billboards)
  hole.blend    the Blender scene, for inspection
  preview.png   (with --preview) a quick overhead render
"""
import json
import math
import os
import random
import sys

import bpy  # noqa: I001  (bpy must load before bmesh)
import bmesh
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hole_gen  # noqa: E402
import props  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
SPEC, OUT = args[0], args[1]
PREVIEW = "--preview" in sys.argv

hole, meta = hole_gen.build(SPEC, OUT)
spec = hole.spec
random.seed(spec.get("seed", 1))
rng = np.random.default_rng(spec.get("seed", 1))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection


def h_at(x, y):
    return float(hole.height(np.array([[x]], float), np.array([[y]], float))[0, 0])


def surf_at(x, y):
    return int(hole.surface(np.array([[x]], float), np.array([[y]], float),
                            np.array([[h_at(x, y)]]))[0, 0])


def path_point(s):
    i = int(np.clip(np.searchsorted(hole.path_s, s), 1, len(hole.path) - 1))
    a, b = hole.path[i - 1], hole.path[i]
    t = (s - hole.path_s[i - 1]) / max(1e-6, hole.path_s[i] - hole.path_s[i - 1])
    p = a + (b - a) * t
    d = (b - a) / max(1e-6, np.linalg.norm(b - a))
    return p, d


# ---------- terrain mesh: exactly the heights.bin lattice -----------------------------------
heights = np.fromfile(os.path.join(OUT, "heights.bin"), np.float32).reshape(meta["phys"]["ny"], meta["phys"]["nx"])
surface = np.fromfile(os.path.join(OUT, "surface.bin"), np.uint8).reshape(meta["surf"]["ny"], meta["surf"]["nx"])
ny, nx = heights.shape
cell = meta["phys"]["cell"]
x0, y0 = meta["origin"]
x1, y1 = meta["extent"]

# keep quads within reach of anything playable; the far field is a coarse skirt
playable = surface != hole_gen.OOB
step = int(round(cell / meta["surf"]["cell"]))
near = playable[::step, ::step][:ny, :nx]
from scipy import ndimage  # noqa: E402
near = ndimage.binary_dilation(near, iterations=6)

bm = bmesh.new()
uv = bm.loops.layers.uv.new("UVMap")
vmap = {}


def vert(i, j):
    k = (i, j)
    if k not in vmap:
        vmap[k] = bm.verts.new((x0 + i * cell, y0 + j * cell, float(heights[j, i])))
    return vmap[k]


def add_tri(a, b, c):
    f = bm.faces.new((vert(*a), vert(*b), vert(*c)))
    for loop, (i, j) in zip(f.loops, (a, b, c)):
        loop[uv].uv = ((i * cell) / (x1 - x0), (j * cell) / (y1 - y0))


for j in range(ny - 1):
    for i in range(nx - 1):
        if not (near[j, i] or near[j, i + 1] or near[j + 1, i] or near[j + 1, i + 1]):
            continue
        # fixed diagonal (i,j)-(i+1,j+1): the physics sampler in Godot splits cells the same way
        add_tri((i, j), (i + 1, j), (i + 1, j + 1))
        add_tri((i, j), (i + 1, j + 1), (i, j + 1))
terrain_tris = len(bm.faces)
for f in bm.faces:
    f.smooth = True
tm = bpy.data.materials.new("terrain")
terrain = props.link("Terrain", bm, [tm], col)

# coarse skirt under and around the lattice, out to the horizon ring
bm = bmesh.new()
S, pad = 6.0, 120.0
xs = np.arange(x0 - pad, x1 + pad + 1, S)
ys = np.arange(y0 - pad, y1 + pad + 1, S)
gx, gy = np.meshgrid(xs, ys)
inside = (gx >= x0) & (gx <= x1) & (gy >= y0) & (gy <= y1)
gz = np.where(inside, hole.height(gx, gy), 0.0)
outside_h = hole.height(np.clip(gx, x0, x1), np.clip(gy, y0, y1))
gz = np.where(inside, gz, outside_h + 0.04 * np.minimum(np.hypot(gx - np.clip(gx, x0, x1), gy - np.clip(gy, y0, y1)), 60))
gz -= np.where(inside, 0.8, 0.12)   # tucked well under the lattice so it never pokes through
verts = [[bm.verts.new((float(gx[j, i]), float(gy[j, i]), float(gz[j, i]))) for i in range(gx.shape[1])]
         for j in range(gx.shape[0])]
for j in range(gx.shape[0] - 1):
    for i in range(gx.shape[1] - 1):
        bm.faces.new((verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]))
for f in bm.faces:
    f.smooth = True
props.paint(bm, lambda co, n: (0.13, 0.17, 0.11))
props.link("Skirt", bm, [props.material("skirt_vc", 1.0)], col)

# ---------- water --------------------------------------------------------------------------
for k, w in enumerate(spec.get("water", [])):
    bm = bmesh.new()
    c = Vector((w["center"][0], w["center"][1], w["level"]))
    rx, ry = w["radius"][0] * 1.5, w["radius"][1] * 1.5
    rot = w.get("rotation", 0.0)
    ring = []
    for a in np.linspace(0, math.tau, 40, endpoint=False):
        u, v = math.cos(a) * rx, math.sin(a) * ry
        ring.append(bm.verts.new(c + Vector((u * math.cos(rot) - v * math.sin(rot), u * math.sin(rot) + v * math.cos(rot), 0))))
    bm.faces.new(ring)
    wm = bpy.data.materials.new("water")
    props.link(f"Water_{k}", bm, [wm], col)

# ---------- props --------------------------------------------------------------------------
lanterns, obstacles, cards = [], [], []
taken = []


def free(x, y, r):
    return all((x - a) ** 2 + (y - b) ** 2 > (r + c) ** 2 for a, b, c in taken)


# jack-o'-lanterns lining the fairway, alternating sides
side = 1
spacing = spec.get("lantern_spacing", 26)
for s in np.arange(spec["fairway_start"] * 0.6, hole.length - 16, spacing):
    p, d = path_point(s)
    nrm = np.array([d[1], -d[0]]) * side
    off = hole.half_width(s) + 2.2 + random.uniform(0, 1.5)
    x, y = p + nrm * off
    if surf_at(x, y) in (hole_gen.ROUGH, hole_gen.DEEP) and free(x, y, 1.0):
        r = random.uniform(0.32, 0.42)
        props.jack(col, f"Jack_{len(lanterns)}", (x, y, h_at(x, y)), r=r,
                   rot_z=math.atan2(-d[0], d[1]) + math.pi + random.uniform(-0.4, 0.4) - side * 0.5)
        lanterns.append([round(x, 2), round(y, 2), round(h_at(x, y) + r * 0.7, 2)])
        obstacles.append({"type": "sphere", "pos": [x, y, h_at(x, y) + r * 0.6], "r": r})
        taken.append((x, y, 1.0))
    side = -side

# graveyards: tombstones (ball bounces off them), skeleton arms, optional fence
for g, gy_ in enumerate(spec.get("graveyards", [])):
    cx, cy = gy_["center"]
    R = gy_["radius"]
    placed = 0
    tries = 0
    while placed < gy_["count"] and tries < 400:
        tries += 1
        a, rr = random.uniform(0, math.tau), R * math.sqrt(random.random())
        x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr
        if surf_at(x, y) in (hole_gen.FAIRWAY, hole_gen.GREEN, hole_gen.SAND, hole_gen.WATER, hole_gen.TEE) or not free(x, y, 1.1):
            continue
        z = h_at(x, y)
        kind = random.random()
        face = math.atan2(-(cx - 0), -(cy - 0)) + random.uniform(-0.35, 0.35)   # roughly toward the tee
        name = f"Grave_{g}_{placed}"
        tilt = (random.uniform(-0.1, 0.1), random.uniform(-0.12, 0.12))
        if kind < 0.55:
            w, hh = random.uniform(0.55, 0.85), random.uniform(0.8, 1.2)
            props.headstone(col, name, (x, y, z), w=w, h=hh, rot_z=face, tilt=tilt)
            obstacles.append({"type": "box", "pos": [x, y, z], "size": [w, 0.18, hh], "rot": face})
        elif kind < 0.85:
            props.cross_stone(col, name, (x, y, z), h=random.uniform(1.0, 1.4), rot_z=face, tilt=tilt)
            obstacles.append({"type": "box", "pos": [x, y, z], "size": [0.6, 0.3, 1.3], "rot": face})
        else:
            props.obelisk(col, name, (x, y, z), h=random.uniform(1.8, 2.6), rot_z=face)
            obstacles.append({"type": "box", "pos": [x, y, z], "size": [0.85, 0.85, 2.8], "rot": face})
        taken.append((x, y, 1.1))
        placed += 1
    for k in range(2):
        for _ in range(60):
            a, rr = random.uniform(0, math.tau), R * random.uniform(0.3, 1.0)
            x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr
            if free(x, y, 1.4) and surf_at(x, y) in (hole_gen.ROUGH, hole_gen.DEEP):
                props.skeleton_arm(col, f"Arm_{g}_{k}", (x, y, h_at(x, y)), rot_z=random.uniform(0, math.tau))
                taken.append((x, y, 1.4))
                break
    if gy_.get("fence"):
        pts = []
        for a in np.linspace(math.pi * 0.35, math.pi * 1.25, 9):
            x, y = cx + math.cos(a) * (R + 2.5), cy + math.sin(a) * (R + 2.5)
            pts.append((x, y))
        props.fence(col, f"Fence_{g}", pts, h_at, post_gap=1.1)

# painted cards (billboards in Godot): trees near the rough edge, forest beyond
tree_cfg = spec.get("trees", {})
sp = tree_cfg.get("spacing", 8.5)
for yy in np.arange(y0 + 4, y1 - 4, sp):
    for xx in np.arange(x0 + 4, x1 - 4, sp):
        x = float(xx + rng.uniform(-sp * 0.4, sp * 0.4))
        y = float(yy + rng.uniform(-sp * 0.4, sp * 0.4))
        d, s = hole.path_query(np.array([[x]]), np.array([[y]]))
        d, s = float(d[0, 0]), float(s[0, 0])
        if s < 6 and d < 25:
            continue                       # keep the view from the tee open
        edge = hole.half_width(s) + spec["rough_width"]
        if d < edge - 4 or not free(x, y, 2.5):
            continue
        su = surf_at(x, y)
        if su == hole_gen.WATER:
            continue
        near_zone = d < edge + spec["deep_rough_width"]
        if rng.random() > (0.55 if near_zone else 0.35):
            continue
        pool = tree_cfg.get("near" if near_zone else "far", ["maple_orange"])
        img = pool[int(rng.integers(0, len(pool)))]
        height = float(rng.uniform(7.0, 10.0) if img != "pine_blue" else rng.uniform(9.0, 13.0))
        if img in ("haunted_tree", "lantern_tree"):
            height *= 0.75
        z = h_at(x, y)
        cards.append({"image": img, "pos": [round(x, 2), round(y, 2), round(z - 0.15, 2)], "height": round(height, 2)})
        if near_zone:
            obstacles.append({"type": "cylinder", "pos": [x, y, z], "r": 0.45, "h": height * 0.45})
            obstacles.append({"type": "sphere", "pos": [x, y, z + height * 0.62], "r": height * 0.28, "soft": True})
        taken.append((x, y, 2.5))

# a few set-dressing cards on the play edges
for name, at, ht in (("scarecrow", 0.45, 2.3), ("pumpkin_pile", 0.2, 1.4), ("pumpkin_pile", 0.7, 1.3), ("bush_heather", 0.55, 1.6)):
    s = hole.length * at
    p, d = path_point(s)
    for sgn in (1, -1):
        x, y = p + np.array([d[1], -d[0]]) * sgn * (hole.half_width(s) + 6.0)
        if free(x, y, 1.5) and surf_at(x, y) in (hole_gen.ROUGH, hole_gen.DEEP):
            cards.append({"image": name, "pos": [round(float(x), 2), round(float(y), 2), round(h_at(x, y) - 0.05, 2)], "height": ht})
            taken.append((x, y, 1.5))
            break

for o in obstacles:
    o["pos"] = [round(float(v), 3) for v in o["pos"]]
json.dump({"lanterns": lanterns, "obstacles": obstacles, "cards": cards},
          open(os.path.join(OUT, "props.json"), "w"), indent=1)

# ---------- export -------------------------------------------------------------------------
deps = bpy.context.evaluated_depsgraph_get()
tris = 0
for ob in scene.objects:
    if ob.type == "MESH":
        me = ob.evaluated_get(deps).to_mesh()
        me.calc_loop_triangles()
        tris += len(me.loop_triangles)
print(f"terrain tris {terrain_tris}, total tris {tris}, lanterns {len(lanterns)}, "
      f"obstacles {len(obstacles)}, cards {len(cards)}")
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "hole.glb"), export_format="GLB",
                          export_lights=False, export_cameras=False, export_image_format="NONE")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "hole.blend"))

if PREVIEW:
    img = bpy.data.images.load(os.path.abspath(os.path.join(OUT, "albedo.png")))
    tm.use_nodes = True
    tex = tm.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tm.node_tree.links.new(tex.outputs["Color"], tm.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 3
    sun.rotation_euler = (0.7, 0.2, 0.5)
    col.objects.link(sun)
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    cam.location = (meta["tee"][0] + 5, -40, 60)
    tgt = Vector((-25, 170, 0))
    cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 24
    col.objects.link(cam)
    scene.camera = cam
    w = bpy.data.worlds.new("w")
    scene.world = w
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = 540, 960
    scene.eevee.taa_render_samples = 8
    scene.render.filepath = os.path.join(OUT, "preview.png")
    bpy.ops.render.render(write_still=True)
