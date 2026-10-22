"""Render every 3D prop/vegetation variant in a row under the game's night lighting (look check).

usage: python3 render_lineup.py <out.png>
"""
import math
import os
import sys

import bpy  # noqa: I001
import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import props  # noqa: E402
import night_look  # noqa: E402

OUT = sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection

rows = [
    ["maple_orange", "maple_red", "apple_tree", "birch", "pine_blue", "dead_tree", "lantern_tree"],
    ["scarecrow", "crow_post", "hay_bales", "corn", "cattails", "bush_heather", "tall_grass", "grass_tuft",
     "leaf_pile", "mushrooms", "pumpkin_pile"],
]
spacing = [7.5, 1.9]
for r, names in enumerate(rows):
    x = -(len(names) - 1) * spacing[r] / 2
    y = r * -7.0
    for name in names:
        fn, _ = props.VARIANTS[name]
        bm, mats, h = fn(3)
        ob = props.link(name, bm, mats, col)
        ob.location = (x, y, 0)
        x += spacing[r]
props.jack(col, "Jack", (6.5, -9.0, 0), r=0.4, rot_z=0.0)
props.jack(col, "Jack2", (-6.5, -9.0, 0), r=0.34, rot_z=0.2)
props.headstone(col, "Stone", (4.5, -10.0, 0), rot_z=0.1)
props.cross_stone(col, "Cross", (-4.5, -10.0, 0), rot_z=-0.1)

bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=60)
props.paint(bm, lambda co, n: (0.16, 0.26, 0.09))
props.link("Ground", bm, [props.material("ground_vc", 1.0)], col)

night_look.setup(scene, lanterns=[(6.5, -9.0, 0.35), (-6.5, -9.0, 0.3), (0, -2, 6)])
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
cam.location = (0, -21, 4.2)
cam.rotation_euler = (math.radians(82), 0, 0)
cam.data.lens = 20
col.objects.link(cam)
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
