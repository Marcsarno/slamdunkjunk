"""Build one hole for the game: terrain fields + Blender scene -> glTF + props list.

usage: python3 build_hole.py <hole.json> <out_dir> [--preview]

Outputs in <out_dir>:
  heights.bin, surface.bin, splat.png, detail.png, terrain.json   (from hole_gen)
  hole.glb      terrain mesh (same 1 m lattice as heights.bin), water, 3D props
  props.json    lanterns (for lights), obstacles (ball collisions), cards (painted billboards)
  golf/build/<hole>/hole.blend, albedo.png, preview.png   inspection files (not shipped)
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

BUILD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build", os.path.basename(os.path.normpath(OUT)))
hole, meta = hole_gen.build(SPEC, OUT, BUILD)
spec = hole.spec
random.seed(spec.get("seed", 1))
rng = np.random.default_rng(spec.get("seed", 1))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
# Hole: unique geometry -> hole.glb. Library: one mesh per vegetation/prop variant -> library.glb.
# Instances: linked copies of library meshes, only for Blender preview renders (the game draws
# them with MultiMesh from props.json).
col = bpy.data.collections.new("Hole")
LIB = bpy.data.collections.new("Library")
INST = bpy.data.collections.new("Instances")
for c in (col, LIB, INST):
    scene.collection.children.link(c)


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
tm.use_nodes = True
_tex = tm.node_tree.nodes.new("ShaderNodeTexImage")
_tex.image = bpy.data.images.load(os.path.abspath(os.path.join(OUT, "ground.jpg")))
tm.node_tree.links.new(_tex.outputs["Color"], tm.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
tm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
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
props.paint(bm, lambda co, n: (0.10, 0.16, 0.07))
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
    wm = bpy.data.materials.get("water") or bpy.data.materials.new("water")
    wm.use_nodes = True
    _b = wm.node_tree.nodes["Principled BSDF"]
    _b.inputs["Base Color"].default_value = (0.01, 0.015, 0.03, 1)
    _b.inputs["Roughness"].default_value = 0.06
    props.link(f"Water_{k}", bm, [wm], col)

# ---------- props --------------------------------------------------------------------------
lanterns, obstacles, cards = [], [], []
taken = []


def free(x, y, r):
    return all((x - a) ** 2 + (y - b) ** 2 > (r + c) ** 2 for a, b, c in taken)


def face_tee(x, y):
    """rot_z that turns a prop's front (-Y) toward the tee, where the player looks from."""
    tx, ty = spec["tee"]["center"]
    return math.atan2(tx - x, -(ty - y))


# jack-o'-lanterns lining the fairway, alternating sides
side = 1
spacing = spec.get("lantern_spacing", 26)
for s in np.repeat(np.arange(spec["fairway_start"] * 0.6, hole.length - 16, spacing), 2):
    p, d = path_point(s)
    nrm = np.array([d[1], -d[0]]) * side
    off = hole.half_width(s) + 2.2 + random.uniform(0, 1.5)
    x, y = p + nrm * off
    if surf_at(x, y) in (hole_gen.ROUGH, hole_gen.DEEP) and free(x, y, 1.0):
        r = random.uniform(0.32, 0.42)
        props.jack(col, f"Jack_{len(lanterns)}", (x, y, h_at(x, y)), r=r,
                   rot_z=face_tee(x, y) + random.uniform(-0.35, 0.35))
        lanterns.append([round(x, 2), round(y, 2), round(h_at(x, y) + r * 0.7, 2)])
        obstacles.append({"type": "sphere", "pos": [x, y, h_at(x, y) + r * 0.6], "r": r})
        taken.append((x, y, 1.0))
    side = -side

# pumpkin patches near the tee: a few carved lanterns plus plain pumpkins, all facing the player
for k, pc in enumerate(spec.get("pumpkin_clusters", [])):
    cx, cy = pc["center"]
    for i in range(pc.get("carved", 2) + pc.get("plain", 3)):
        for _ in range(40):
            a, rr = random.uniform(0, math.tau), random.uniform(0.3, pc.get("radius", 1.6))
            x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr
            if free(x, y, 0.45) and surf_at(x, y) not in (hole_gen.FAIRWAY, hole_gen.GREEN, hole_gen.TEE, hole_gen.SAND):
                break
        else:
            continue
        carved = i < pc.get("carved", 2)
        r = random.uniform(0.3, 0.45) if carved else random.uniform(0.18, 0.32)
        props.jack(col, f"Patch_{k}_{i}", (x, y, h_at(x, y)), r=r,
                   rot_z=face_tee(x, y) + random.uniform(-0.5, 0.5), carved=carved)
        if carved:
            lanterns.append([round(x, 2), round(y, 2), round(h_at(x, y) + r * 0.7, 2)])
        obstacles.append({"type": "sphere", "pos": [x, y, h_at(x, y) + r * 0.6], "r": r})
        taken.append((x, y, 0.45))

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
theme = spec.get("theme", {})
tree_cfg = dict(spec.get("trees", {}))
tree_cfg.update({k: v for k, v in (("near", theme.get("trees_near")), ("far", theme.get("trees_far"))) if v})


def in_cornfield(x, y):
    cf = theme.get("cornfield")
    if not cf:
        return False
    lat, s_ = hole.lateral(np.array([[x]]), np.array([[y]]))
    lat, s_ = float(lat[0, 0]), float(s_[0, 0])
    sgn = 1 if cf.get("side", "right") == "right" else -1
    start = hole.half_width(s_) + spec["rough_width"] + cf.get("gap", 4.0) - 3.0
    return hole.length * cf["from"] - 4 < s_ < hole.length * cf["to"] + 4 and start < lat * sgn < start + cf.get("depth", 26.0) + 4


TREE_HEIGHT = {"pine_blue": (9.0, 13.0), "haunted_tree": (5.5, 7.5), "lantern_tree": (5.5, 7.5),
               "dead_tree": (6.0, 8.5), "birch": (8.0, 11.0), "apple_tree": (5.5, 7.5),
               # the painted tree set (tools/prep_trees.py)
               "tree_copper_oak": (7.0, 9.5), "tree_scarlet_maple": (7.0, 9.5), "tree_golden_aspen": (8.0, 11.0),
               "tree_crooked_plum": (5.5, 7.5), "tree_harvest_pear": (6.0, 8.0), "tree_hollow_sentinel": (7.0, 9.0),
               "tree_bent_willow": (5.0, 6.5), "tree_lightning_oak": (7.0, 9.0), "tree_silver_snag": (7.0, 9.5),
               "tree_raven_perch": (4.5, 6.0), "tree_moonlit_pine": (10.0, 14.0), "tree_twisted_cypress": (8.0, 10.5),
               "tree_ancient_yew": (5.0, 6.5), "tree_windbent_fir": (8.0, 10.0), "tree_ghost_birch": (8.0, 11.0)}
# trees much wider than tall: their canopy (the ball's soft obstacle) spreads wider for their height
TREE_SPREAD = {"tree_bent_willow": 0.5, "tree_ancient_yew": 0.5, "tree_raven_perch": 0.45, "tree_windbent_fir": 0.35,
               "tree_lightning_oak": 0.35}
sp = spec.get("trees_spacing", tree_cfg.get("spacing", 8.5))
for yy in np.arange(y0 + 4, y1 - 4, sp):
    for xx in np.arange(x0 + 4, x1 - 4, sp):
        x = float(xx + rng.uniform(-sp * 0.4, sp * 0.4))
        y = float(yy + rng.uniform(-sp * 0.4, sp * 0.4))
        d, s = hole.path_query(np.array([[x]]), np.array([[y]]))
        d, s = float(d[0, 0]), float(s[0, 0])
        if s < 6 and d < 25:
            continue                       # keep the view from the tee open
        edge = hole.half_width(s) + spec["rough_width"]
        if d < edge - 4 or not free(x, y, 2.5) or in_cornfield(x, y):
            continue
        su = surf_at(x, y)
        if su == hole_gen.WATER:
            continue
        near_zone = d < edge + spec["deep_rough_width"]
        if rng.random() > (0.75 if near_zone else 0.4):
            continue
        pool = tree_cfg.get("near" if near_zone else "far", ["maple_orange"])
        img = pool[int(rng.integers(0, len(pool)))]
        height = float(rng.uniform(*TREE_HEIGHT.get(img, (7.0, 10.0))))
        z = h_at(x, y)
        cards.append({"image": img, "pos": [round(x, 2), round(y, 2), round(z - 0.15, 2)], "height": round(height, 2),
                      "shadow": True})
        if near_zone:
            obstacles.append({"type": "cylinder", "pos": [x, y, z], "r": 0.45, "h": height * 0.45})
            obstacles.append({"type": "sphere", "pos": [x, y, z + height * 0.62], "r": height * TREE_SPREAD.get(img, 0.28),
                              "soft": True})
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

# ---------- ground cover and set dressing (no collision: the surface type decides the lie) -----
def card(img, x, y, height, shadow=False, sink=0.05):
    cards.append({"image": img, "pos": [round(float(x), 2), round(float(y), 2), round(h_at(x, y) - sink, 2)],
                  "height": round(float(height), 2), "shadow": shadow})


def scatter(img, spacing, prob, hrange, zone, shadow=False):
    """zone(x, y, d, s, surface) -> bool"""
    n = 0
    for yy in np.arange(y0 + 2, y1 - 2, spacing):
        for xx in np.arange(x0 + 2, x1 - 2, spacing):
            if rng.random() > prob:
                continue
            x = float(xx + rng.uniform(-spacing * 0.45, spacing * 0.45))
            y = float(yy + rng.uniform(-spacing * 0.45, spacing * 0.45))
            d, s = hole.path_query(np.array([[x]]), np.array([[y]]))
            d, s = float(d[0, 0]), float(s[0, 0])
            su = surf_at(x, y)
            if su in (hole_gen.FAIRWAY, hole_gen.GREEN, hole_gen.SAND, hole_gen.WATER, hole_gen.TEE, hole_gen.FRINGE):
                continue
            if not zone(x, y, d, s, su) or not free(x, y, 0.4):
                continue
            card(img, x, y, rng.uniform(*hrange), shadow)
            n += 1
    return n


rough_w = spec["rough_width"]
counts = {}
counts["grass_tuft"] = scatter("grass_tuft", 3.4, 0.18, (0.3, 0.5),
                               lambda x, y, d, s, su: su == hole_gen.ROUGH and d < hole.half_width(s) + rough_w * 0.8)
counts["tall_grass"] = scatter("tall_grass", 3.2, 0.5, (0.9, 1.4), lambda x, y, d, s, su: su == hole_gen.DEEP)
counts["leaf_pile"] = scatter("leaf_pile", 6.0, 0.35, (0.3, 0.5), lambda x, y, d, s, su: su in (hole_gen.ROUGH, hole_gen.DEEP))
counts["fern"] = scatter("fern", 7.0, 0.35, (0.6, 0.95), lambda x, y, d, s, su: su in (hole_gen.DEEP, hole_gen.OOB) and d < hole.half_width(s) + rough_w + spec["deep_rough_width"] + 10)
# glowing mushrooms in the graveyards and a crow keeping watch
for g in spec.get("graveyards", []):
    for _ in range(5):
        a, rr = random.uniform(0, math.tau), g["radius"] * random.uniform(0.3, 1.2)
        x, y = g["center"][0] + math.cos(a) * rr, g["center"][1] + math.sin(a) * rr
        if free(x, y, 0.5) and surf_at(x, y) in (hole_gen.ROUGH, hole_gen.DEEP, hole_gen.OOB):
            card("mushrooms", x, y, random.uniform(0.45, 0.75))
    if g.get("fence"):
        a = math.pi * 1.3
        x, y = g["center"][0] + math.cos(a) * (g["radius"] + 3.2), g["center"][1] + math.sin(a) * (g["radius"] + 3.2)
        card("crow_post", x, y, 1.6, shadow=True)
        taken.append((x, y, 0.6))
# cattails around the ponds
for w in spec.get("water", []):
    cx, cy = w["center"]
    rx, ry = w["radius"]
    rot = w.get("rotation", 0.0)
    for a in np.arange(0, math.tau, 0.09):
        if rng.random() > 0.55:
            continue
        k = rng.uniform(1.0, 1.18)
        u, v = math.cos(a) * rx * k, math.sin(a) * ry * k
        x = cx + u * math.cos(rot) - v * math.sin(rot)
        y = cy + u * math.sin(rot) + v * math.cos(rot)
        if surf_at(x, y) not in (hole_gen.FAIRWAY, hole_gen.TEE):
            card("cattails", x, y, rng.uniform(1.2, 1.8), sink=0.1)
# a cornfield along one side of the hole (theme), with hay bales at its edge
cf = theme.get("cornfield")
if cf:
    sgn = 1 if cf.get("side", "right") == "right" else -1
    n_corn = 0
    for s_ in np.arange(hole.length * cf["from"], hole.length * cf["to"], 1.7):
        p, d = path_point(s_)
        nrm = np.array([d[1], -d[0]]) * sgn
        start = hole.half_width(s_) + rough_w + cf.get("gap", 4.0)
        for row in np.arange(start, start + cf.get("depth", 26.0), 2.3):
            x, y = p + nrm * (row + rng.uniform(-0.4, 0.4)) + d * rng.uniform(-0.5, 0.5)
            if surf_at(x, y) in (hole_gen.WATER, hole_gen.FAIRWAY, hole_gen.GREEN) or not free(x, y, 0.3):
                continue
            card("corn", x, y, rng.uniform(2.0, 2.6), shadow=False, sink=0.1)
            n_corn += 1
    counts["corn"] = n_corn
    for k in range(3):
        s_ = hole.length * (cf["from"] + (cf["to"] - cf["from"]) * (0.2 + 0.3 * k))
        p, d = path_point(s_)
        x, y = p + np.array([d[1], -d[0]]) * sgn * (hole.half_width(s_) + rough_w + cf.get("gap", 4.0) - 2.0)
        if free(x, y, 1.5):
            card("hay_bales", x, y, 1.3, shadow=True)
            obstacles.append({"type": "box", "pos": [x, y, h_at(x, y)], "size": [2.4, 1.2, 1.3],
                              "rot": math.atan2(d[1], d[0])})
            taken.append((x, y, 1.5))
print("ground cover:", counts)

# ---------- 3D library + instances (replaces the painted cards) ------------------------------
import zlib  # noqa: E402
from collections import defaultdict  # noqa: E402

FIXED_SCALE = {"leaf_pile", "mushrooms", "pumpkin_pile", "hay_bales", "scarecrow", "crow_post", "cattails"}
FACE_PLAYER = {"scarecrow", "crow_post"}
variants = {}
for img in sorted({c["image"] for c in cards}):
    if img not in props.VARIANTS:
        print("no 3D model for", img)
        continue
    fn, n = props.VARIANTS[img]
    variants[img] = []
    for k in range(n):
        bm, mats, h = fn(zlib.crc32(img.encode()) % 1000 + 37 * k)
        ob = props.link(f"{img}_{k}", bm, mats, LIB)
        ob.location = (0, 0, -1000)
        variants[img].append((ob, h))
instances = defaultdict(list)
for c in cards:
    vs = variants.get(c["image"])
    if not vs:
        continue
    ob, h = vs[int(rng.integers(len(vs)))]
    x, y, z = c["pos"]
    if c["image"] in FIXED_SCALE:
        sc = float(rng.uniform(0.85, 1.15))
    else:
        sc = c["height"] / h
    rot = face_tee(x, y) if c["image"] in FACE_PLAYER else float(rng.uniform(0, math.tau))
    instances[ob.name].append([round(x, 2), round(y, 2), round(z, 2), round(rot, 3), round(sc, 3)])
    inst = bpy.data.objects.new(ob.name + "_i", ob.data)
    inst.location = (x, y, z)
    inst.rotation_euler = (0, 0, rot)
    inst.scale = (sc, sc, sc)
    INST.objects.link(inst)


# ---------- distant scenery: rolling hills ring with pine silhouettes, and the moon ----------
def scenery():
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r_in = max(x1 - x0, y1 - y0) * 0.5 + 40.0
    r_out = r_in + 520.0
    bm = bmesh.new()
    rings, segs = 14, 96
    verts = []
    hn = hole_gen.Noise(spec.get("seed", 1) + 11, waves=10, wavelength=(120.0, 420.0))
    for j in range(rings):
        t = j / (rings - 1)
        r = r_in + (r_out - r_in) * t ** 1.3
        row = []
        for i in range(segs):
            a = math.tau * i / segs
            x, y = cx + math.cos(a) * r, cy + math.sin(a) * r
            base = float(hole.base_height(np.array([[np.clip(x, x0, x1)]]), np.array([[np.clip(y, y0, y1)]]))[0, 0]) if t == 0 else 0.0
            hgt = (base - 1.0) * (1 - t) + (8.0 + 38.0 * t + 26.0 * float(hn(np.array([x]), np.array([y]))[0])) * min(1.0, t * 3.0)
            row.append(bm.verts.new((x, y, hgt)))
        verts.append(row)
    for j in range(rings - 1):
        for i in range(segs):
            bm.faces.new((verts[j][i], verts[j][(i + 1) % segs], verts[j + 1][(i + 1) % segs], verts[j + 1][i]))
    for f in bm.faces:
        f.smooth = True
    props.paint(bm, lambda co, n: props.lerp((0.10, 0.15, 0.08), (0.12, 0.10, 0.16), min(1.0, max(0.0, co.z / 50.0))))
    props.link("Hills", bm, [props.material("hills_vc", 1.0)], col)
    # pine silhouettes on the near hills: one merged mesh (it is far away, one draw call)
    bm = bmesh.new()
    pine_bm, _, ph = props.far_pine(5)
    me = bpy.data.meshes.new("tmp_pine")
    pine_bm.to_mesh(me)
    pine_bm.free()
    count = 0
    for k in range(900):
        a = rng.uniform(0, math.tau)
        t = rng.uniform(0.02, 0.35) ** 1.2
        r = r_in + (r_out - r_in) * t
        x, y = cx + math.cos(a) * r, cy + math.sin(a) * r
        if np.hypot(x - meta["tee"][0], y - meta["tee"][1]) < r_in * 0.5:
            continue
        hgt = (8.0 + 38.0 * t + 26.0 * float(hn(np.array([x]), np.array([y]))[0])) * min(1.0, t * 3.0) - 0.5
        sc = rng.uniform(1.4, 2.6)
        m = Matrix.Translation((x, y, hgt)) @ Matrix.Rotation(rng.uniform(0, 6.28), 4, "Z") @ Matrix.Scale(sc, 4)
        before = len(bm.verts)
        bm.from_mesh(me)
        bm.verts.ensure_lookup_table()
        bmesh.ops.transform(bm, matrix=m, verts=bm.verts[before:])
        count += 1
    bpy.data.meshes.remove(me)
    props.link("FarPines", bm, [props.material("pine_vc", 0.9)], col)
    # moon: emissive cratered sphere far away, in the theme's direction from the tee looking down-range
    th = spec.get("theme", {})
    az = math.radians(th.get("moon_azimuth", -14.0))
    el = math.radians(th.get("moon_elevation", 24.0))
    dist = 1400.0
    d = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
    bm = bmesh.new()
    ret = bmesh.ops.create_icosphere(bm, subdivisions=4, radius=60.0)
    for f in bm.faces:
        f.smooth = True
    props.paint(bm, lambda co, n: tuple(v * (0.75 + 0.25 * noise.noise(co * 0.05)) for v in (1.0, 0.7, 0.3)))
    moon = props.link("Moon", bm, [props.material("moon_glow", 1.0, emit=(1.0, 0.62, 0.22), strength=1.6)], col)
    moon.location = Vector((meta["tee"][0], meta["tee"][1], 0)) + d * dist
    print(f"scenery: hills ring {r_in:.0f}-{r_out:.0f} m, {count} far pines")
    return moon.location


from mathutils import Matrix, noise  # noqa: E402
# 3D hills, far pines and a 3D moon: the all-3D experiment (2026-10-22). Off unless the theme asks,
# because the game's painted sky draws its own moon and horizon.
moon_pos = scenery() if spec.get("theme", {}).get("scenery_3d") else None

for o in obstacles:
    o["pos"] = [round(float(v), 3) for v in o["pos"]]
out_props = {"lanterns": lanterns, "obstacles": obstacles, "cards": cards, "instances": instances}
if moon_pos is not None:
    out_props["moon"] = [round(v, 1) for v in moon_pos]
json.dump(out_props,
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
      f"obstacles {len(obstacles)}, instances {sum(len(v) for v in instances.values())}")
for me in bpy.data.meshes:
    if "Col" in me.color_attributes:
        me.color_attributes.active_color_name = "Col"
        me.color_attributes.render_color_index = me.color_attributes.find("Col")


def export(collection, path):
    bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children[collection]
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_active_collection=True,
                              export_lights=False, export_cameras=False, export_image_format="NONE",
                              export_vertex_color="ACTIVE", export_all_vertex_colors=False)


export("Hole", os.path.join(OUT, "hole.glb"))
if instances:
    export("Library", os.path.join(OUT, "library.glb"))
os.makedirs(BUILD, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BUILD, "hole.blend"))

