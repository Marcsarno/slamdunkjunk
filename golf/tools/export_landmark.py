"""Export one landmark (tools/landmarks.py) on its own as a .glb, the way build_hole.py exports a hole
(vertex colours as the active colour), for previewing it in the game (game/tests/landmark_view.gd).

usage: python3 export_landmark.py <chapel|house|barn|mansion|a builder in small_props.py> <out.glb>
"""
import os
import sys

import bpy  # noqa: I001

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import landmarks  # noqa: E402
import small_props  # noqa: E402

KIND, OUT = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
getattr(landmarks if hasattr(landmarks, KIND) else small_props, KIND)(bpy.context.scene.collection, KIND, (0, 0, 0), 0.0, 1.0)
for me in bpy.data.meshes:
    if "Col" in me.color_attributes:
        me.color_attributes.active_color_name = "Col"
        me.color_attributes.render_color_index = me.color_attributes.find("Col")
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_lights=False, export_cameras=False,
                          export_image_format="NONE", export_vertex_color="ACTIVE", export_all_vertex_colors=False)
