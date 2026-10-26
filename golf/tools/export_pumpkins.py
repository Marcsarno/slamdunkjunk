"""The pumpkins every hole shares, stored once: a carved jack-o'-lantern and a plain pumpkin, each 1 m in
radius and standing on the ground at its origin, front (the carved face) toward -y. The game places
copies of them where a hole's props.json lists "pumpkins" (the lanterns along the fairway and the patches),
so a hole's own model no longer carries hundreds of pumpkins of its own.

usage: python3 export_pumpkins.py <out.glb>     (game/assets/props/pumpkins.glb)
"""
import os
import sys

import bpy  # noqa: I001
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import props  # noqa: E402

OUT = sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
col = bpy.context.scene.collection
for name, carved in (("PumpkinCarved", True), ("PumpkinPlain", False)):
    ob = props.jack(col, name, (0, 0, 0), r=1.0, carved=carved, shade=1.0)
    ob.data.transform(Matrix.Translation(ob.location))       # its foot at the origin, so a copy stands on its spot
    ob.location = (0, 0, 0)
for me in bpy.data.meshes:
    if "Col" in me.color_attributes:
        me.color_attributes.active_color_name = "Col"
        me.color_attributes.render_color_index = me.color_attributes.find("Col")
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_lights=False, export_cameras=False,
                          export_image_format="NONE", export_vertex_color="ACTIVE", export_all_vertex_colors=False)
