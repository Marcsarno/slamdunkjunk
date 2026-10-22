"""Make the Swing Lab's copy of the character: skinned mesh + skeleton only, lighter textures, hands that close.

usage: python3 slim_character.py <character.glb> <out.glb>
Drops unskinned stray meshes and all actions, scales the base color to 2048, the normal map to
1024 and metallic-roughness to 512, and writes JPEG textures. The skeleton is untouched.

Hands: her four fingers are one block (a mitten; the gaps are painted) skinned almost entirely to the
hand bone, so her finger joints moved nothing. The block is re-weighted along the rig's own middle-finger
joints (knuckle, middle, last), and the thumb along its own joints, each blended over +-6 mm across the
joint (the mesh has an edge loop at each), so the block curls into a fist and the thumb wraps.
"""
import sys

import bpy
from mathutils import Vector

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


def reweight_chain(mesh, arm, joints, verts, blend=0.006, tip=0.03):
    """Weights along a chain of joints: each vertex is placed along the polyline joints[0..] (extended past
    the last joint by `tip`); before the first joint it belongs to the parent (joints[0] is the parent bone
    name, the rest are the chain's bones in order)."""
    names = joints
    heads = [arm.matrix_world @ arm.data.bones[n].head_local for n in names[1:]]
    end = arm.matrix_world @ arm.data.bones[names[-1]].tail_local
    pts = heads + [end + (end - heads[-1]).normalized() * tip]
    # distance along the chain of each joint
    acc = [0.0]
    for a, b in zip(pts[:-1], pts[1:]):
        acc.append(acc[-1] + (b - a).length)
    groups = {n: mesh.vertex_groups.get(n) or mesh.vertex_groups.new(name=n) for n in names}
    mw = mesh.matrix_world
    for v in verts:
        co = mw @ v.co
        # nearest point on the polyline -> distance along it (before the first joint: negative)
        best = None
        for i, (a, b) in enumerate(zip(pts[:-1], pts[1:])):
            ab = b - a
            t = (co - a).dot(ab) / ab.length_squared
            tc = max(0.0, min(1.0, t)) if i else min(1.0, t)
            d = (co - (a + ab * tc)).length
            if best is None or d < best[0]:
                best = (d, acc[i] + tc * ab.length)
        s_ = best[1]
        # piecewise-linear weights with a +-blend ramp at each joint
        w = {}
        bounds = acc[:len(names) - 1]          # where each chain bone starts
        for k, n in enumerate(names):
            lo = -1e9 if k == 0 else bounds[k - 1]
            hi = bounds[k] if k < len(bounds) else 1e9
            up = 1.0 if k == 0 else min(1.0, max(0.0, (s_ - (lo - blend)) / (2 * blend)))
            down = 1.0 if hi >= 1e9 else min(1.0, max(0.0, ((hi + blend) - s_) / (2 * blend)))
            w[n] = up * down
        tot = sum(w.values()) or 1.0
        for n in names:
            groups[n].remove([v.index])
            if w[n] / tot > 1e-3:
                groups[n].add([v.index], w[n] / tot, "REPLACE")


mesh = next(o for o in bpy.data.objects if o.type == "MESH")
arm.data.pose_position = "REST"
vgname = {g.index: g.name for g in mesh.vertex_groups}
for side in ("Left", "Right"):
    pre = f"mixamorig:{side}Hand"
    thumb_names = [pre + f"Thumb{i}" for i in (1, 2, 3)]
    mid_names = [pre + f"Middle{i}" for i in (1, 2, 3)]
    thumb_v, block_v = [], []
    for v in mesh.data.vertices:
        ws = {vgname[g.group]: g.weight for g in v.groups}
        if sum(ws.get(n, 0) for n in thumb_names + [pre + "Thumb4"]) > 0.15:
            thumb_v.append(v)
        elif max(ws, key=ws.get, default="") in [pre] + mid_names + [pre + "Middle4"]:
            block_v.append(v)
    # the finger block: only from just before the knuckles on (the palm stays on the hand)
    k1 = arm.matrix_world @ arm.data.bones[mid_names[0]].head_local
    k4 = arm.matrix_world @ arm.data.bones[pre + "Middle4"].head_local
    axis = (k4 - k1).normalized()
    block_v = [v for v in block_v if ((mesh.matrix_world @ v.co) - k1).dot(axis) > -0.015]
    reweight_chain(mesh, arm, [pre] + mid_names, block_v)
    reweight_chain(mesh, arm, [pre] + thumb_names, thumb_v, tip=0.02)
    print(side, "hand: finger block", len(block_v), "verts, thumb", len(thumb_v), "verts re-weighted")

for img in bpy.data.images:
    n = img.name.lower()
    size = 512 if "metal" in n or "rough" in n else 1024 if "normal" in n else 2048
    if img.size[0] > size:
        img.scale(size, size)
    print("image", img.name, tuple(img.size))
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_animations=False,
                          export_image_format="JPEG", export_jpeg_quality=88,
                          export_cameras=False, export_lights=False)
