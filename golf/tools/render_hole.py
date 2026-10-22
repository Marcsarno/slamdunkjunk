"""Blender preview renders of a built hole from the game's own camera positions.

usage: python3 render_hole.py <hole.json> <game hole dir> <out dir> [views...]
views: tee flyover flight approach graveyard (default: all)
Reads golf/build/<hole>/hole.blend written by build_hole.py.
"""
import json
import math
import os
import sys

import bpy  # noqa: I001
import bmesh
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hole_gen  # noqa: E402
import night_look  # noqa: E402

SPEC, GAME_DIR, OUT = sys.argv[1:4]
VIEWS = sys.argv[4:] or ["tee", "flyover", "flight", "approach", "graveyard"]
PCT = int(os.environ.get("PCT", "100"))
GOLFER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "game", "assets", "golfer")
os.makedirs(OUT, exist_ok=True)

spec = json.load(open(SPEC))
hole = hole_gen.Hole(spec)
meta = json.load(open(os.path.join(GAME_DIR, "terrain.json")))
props_json = json.load(open(os.path.join(GAME_DIR, "props.json")))
build = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build", os.path.basename(os.path.normpath(GAME_DIR)))
bpy.ops.wm.open_mainfile(filepath=os.path.join(build, "hole.blend"))
scene = bpy.context.scene
col = scene.collection
# the library meshes sit at z = -1000 for export; keep them out of renders
bpy.data.collections["Library"].hide_render = True


def H(x, y):
    return float(hole.height(np.array([[x]], float), np.array([[y]], float))[0, 0])


def lanterns():
    return [(p[0], p[1], p[2] + 0.05) for p in props_json["lanterns"]]


night_look.setup(scene, lanterns=lanterns(), moon_azimuth=spec.get("theme", {}).get("light_azimuth", 200.0), samples=24)
scene.render.resolution_x, scene.render.resolution_y = 1080, 1920
scene.render.resolution_percentage = PCT * 50 // 100

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
cam.data.sensor_fit = "HORIZONTAL"
cam.data.clip_end = 3000
col.objects.link(cam)
scene.camera = cam


def look(pos, target, hfov=52.0):
    cam.location = Vector(pos)
    cam.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    cam.data.angle = math.radians(hfov)


# ---------- golfer sprite (the one 2D element: Brittany herself) ----------------------------
gdata = json.load(open(os.path.join(GOLFER, "golfer.json")))
golfer_obs = []


def golfer(set_name, foot, aim, cam_pos):
    s = gdata[set_name]
    f = s["frames"][str(s["back"][0])]
    ps = 1.55 / s["body_px"]
    w, h = f["size"][0] * ps, f["size"][1] * ps
    ax, ay = f["anchor"][0] * ps, f["anchor"][1] * ps
    m = bpy.data.materials.new("golfer_" + set_name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(os.path.abspath(os.path.join(GOLFER, f["file"])))
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 0.6
    bsdf.inputs["Roughness"].default_value = 1.0
    m.surface_render_method = "DITHERED"
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in [(-ax, 0, -(h - ay)), (w - ax, 0, -(h - ay)), (w - ax, 0, ay), (-ax, 0, ay)]]
    face = bm.faces.new(vs)
    uv = bm.loops.layers.uv.new()
    for loop, c in zip(face.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        loop[uv].uv = c
    me = bpy.data.meshes.new("golfer")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m)
    ob = bpy.data.objects.new("Golfer", me)
    ob.location = (foot[0], foot[1], H(foot[0], foot[1]))
    d = Vector(cam_pos) - Vector(ob.location)
    ob.rotation_euler = (0, 0, math.atan2(d.y, d.x) - math.pi / 2)
    col.objects.link(ob)
    golfer_obs.append(ob)


def clear_golfer():
    for ob in golfer_obs:
        bpy.data.objects.remove(ob)
    golfer_obs.clear()


def ball(p):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=6, radius=0.05)
    me = bpy.data.meshes.new("ball")
    bm.to_mesh(me)
    bm.free()
    m = bpy.data.materials.new("ball")
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.95, 0.95, 0.92, 1)
    me.materials.append(m)
    ob = bpy.data.objects.new("Ball", me)
    ob.location = p
    col.objects.link(ob)
    golfer_obs.append(ob)


def path_point_at(dist_from, origin):
    """Path point about `dist_from` meters from `origin` (course xy)."""
    pts = hole.path
    d = np.hypot(pts[:, 0] - origin[0], pts[:, 1] - origin[1])
    i = int(np.argmin(np.abs(d - dist_from)))
    return pts[i]


def aim_view(ball2, aim_to, set_name):
    a = Vector((aim_to[0] - ball2[0], aim_to[1] - ball2[1], 0)).normalized()
    right = Vector((a.y, -a.x, 0))
    bz = H(*ball2) + 0.02
    b = Vector((ball2[0], ball2[1], bz))
    cpos = b - a * 4.4 + Vector((0, 0, 2.0))
    t = b + a * 40.0
    tgt = Vector((t.x, t.y, H(t.x, t.y) + 2.5))
    s = gdata["back_" + set_name]
    f = s["frames"][str(s["back"][0])]
    ps = 1.55 / s["body_px"]
    off = (f["club_head"][0] - f["anchor"][0]) * ps
    foot = Vector((b.x, b.y, 0)) - right * off - a * 0.12
    golfer("back_" + set_name, foot, a, cpos)
    ball(b + Vector((0, 0, 0.03)))
    look(cpos, tgt)


def render(name):
    scene.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("rendered", name)


tee = meta["tee"]
pin = meta["pin"]
for v in VIEWS:
    clear_golfer()
    if v == "tee":
        aim_view((tee[0], tee[1]), path_point_at(195, tee), "driver")
    elif v == "flyover":
        p = hole.path[60]
        q = hole.path[min(len(hole.path) - 1, 60 + 160)]
        look((p[0], p[1], H(*p) + 26), (q[0], q[1], H(*q)), 62)
    elif v == "flight":
        p = path_point_at(115, tee)
        q = path_point_at(170, tee)
        d = Vector((q[0] - p[0], q[1] - p[1], 0)).normalized()
        side = Vector((d.y, -d.x, 0))
        cpos = Vector((p[0], p[1], H(*p))) - d * 12 + side * 9 + Vector((0, 0, 9))
        look(cpos, (q[0], q[1], H(*q) + 3), 60)
    elif v == "approach":
        b = path_point_at(95, pin)
        aim_view((b[0], b[1]), (pin[0], pin[1]), "iron")
    elif v == "graveyard":
        g = spec["graveyards"][0]["center"]
        cpos = (g[0] + 9, g[1] - 9, H(g[0] + 9, g[1] - 9) + 1.6)
        look(cpos, (g[0], g[1], H(*g) + 0.8), 70)
    render(v)
