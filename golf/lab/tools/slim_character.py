"""Make the Swing Lab's copy of the character: skinned mesh + skeleton only, lighter textures.

usage: python3 slim_character.py <character.glb> <out.glb>
Drops unskinned stray meshes and all actions, scales the base color to 2048, the normal map to
1024 and metallic-roughness to 512, and writes JPEG textures. The skeleton and skin are untouched.
"""
import sys

import bpy

SRC, OUT = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
for o in list(bpy.data.objects):
    if o.type == "MESH" and not any(m.type == "ARMATURE" for m in o.modifiers) and o.parent != arm:
        print("dropping", o.name)
        bpy.data.objects.remove(o)
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)
if arm.animation_data:
    arm.animation_data_clear()
for img in bpy.data.images:
    n = img.name.lower()
    size = 512 if "metal" in n or "rough" in n else 1024 if "normal" in n else 2048
    if img.size[0] > size:
        img.scale(size, size)
    print("image", img.name, tuple(img.size))
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_animations=False,
                          export_image_format="JPEG", export_jpeg_quality=88,
                          export_cameras=False, export_lights=False)
