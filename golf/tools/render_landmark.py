"""Render one landmark (tools/landmarks.py) on its own under the game's night lighting, from the front, the
side and three-quarters (the views of Marc's concept sheets), to set beside the concept.

usage: python3 render_landmark.py <chapel|house|barn|mansion> <out_prefix>
writes <out_prefix>_front.png, _side.png, _three_quarter.png
"""
import math
import os
import sys

import bpy  # noqa: I001
import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import props  # noqa: E402
import landmarks  # noqa: E402
import night_look  # noqa: E402

KIND, OUT = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection

obs, (hx, hy) = getattr(landmarks, KIND)(col, KIND, (0, 0, 0), 0.0, 1.0)
lo = Vector((1e9, 1e9, 1e9))
hi = -lo
for ob in obs:
    for v in ob.data.vertices:
        w = ob.matrix_world @ v.co
        lo = Vector(map(min, lo, w))
        hi = Vector(map(max, hi, w))
centre = (lo + hi) / 2
size = max(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z)
tris = sum(len(p.vertices) - 2 for ob in obs for p in ob.data.polygons)
print(f"{KIND}: {hi.x - lo.x:.1f} x {hi.y - lo.y:.1f} m, {hi.z - lo.z:.1f} m tall, {tris} triangles")

bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=80)
props.paint(bm, lambda co, n: (0.12, 0.2, 0.08))
props.link("Ground", bm, [props.material("ground_vc", 1.0)], col)

# lanterns either side of the front, as the course's light props would stand
night_look.setup(scene, lanterns=[(-hx - 3, lo.y - 4, 1.5), (hx + 3, lo.y - 4, 1.5)])
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
cam.data.lens = 50
col.objects.link(cam)
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = 900, 1100
for view, ang in (("front", -90.0), ("side", 0.0), ("three_quarter", -45.0)):
    a = math.radians(ang)
    dist = size * 2.1
    cam.location = centre + Vector((math.cos(a) * dist, math.sin(a) * dist, size * 0.22))
    d = (centre + Vector((0, 0, -size * 0.05))) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = f"{OUT}_{view}.png"
    bpy.ops.render.render(write_still=True)
