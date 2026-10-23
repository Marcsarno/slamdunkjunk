"""Lighten Marc's pumpkin lanterns for a phone: python3 -I prep_lanterns.py <src.glb> <out.glb> [rind_ratio]

The lanterns come as ~16k-triangle models in ~20 parts (art_src/lanterns): almost all of it the
pumpkin's shell (~10k) and its glowing inside (~5k), the wood and iron a few hundred. Here the shell
is decimated (its carved openings kept), the inside more so (it's only seen through the face), the
little iron bolts and collars a little, and
every part joined into one object, so a lantern is ~3k triangles and a handful of draw calls (one per
material). Materials and their textures pass through untouched.
"""
import sys

import bpy

SRC, OUT = sys.argv[1], sys.argv[2]
RIND = float(sys.argv[3]) if len(sys.argv) > 3 else 0.18
INSIDE = 0.06

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
for ob in meshes:
    small_iron = any(k in ob.name for k in ("Bolt", "Collar", "Crown", "Clamp", "Strap", "bolt"))
    ratio = RIND if "Rind" in ob.name else (INSIDE if "Interior" in ob.name else (0.35 if small_iron else 1.0))
    if ratio < 1.0:
        dec = ob.modifiers.new("Lighter", "DECIMATE")
        dec.decimate_type = "COLLAPSE"
        dec.ratio = ratio
        dec.use_collapse_triangulate = True
        with bpy.context.temp_override(object=ob, active_object=ob):
            bpy.ops.object.modifier_apply(modifier=dec.name)
# one object: parts keep their places (applied transforms), the root stays at ground level
for ob in meshes:
    ob.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
with bpy.context.temp_override(active_object=meshes[0], selected_editable_objects=meshes, selected_objects=meshes):
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.join()
lantern = meshes[0]
lantern.name = "Lantern"
deps = bpy.context.evaluated_depsgraph_get()
me = lantern.evaluated_get(deps).to_mesh()
me.calc_loop_triangles()
print("triangles", len(me.loop_triangles), "materials", [m.name for m in lantern.data.materials])
for ob in list(bpy.context.scene.objects):
    if ob is not lantern:
        bpy.data.objects.remove(ob)
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_yup=True)
