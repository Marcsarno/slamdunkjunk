"""The Blender night look (from the style test the user liked): world gradient with stars, cool
moonlight from behind the camera, warm rim light, shadowless point lights in every lantern,
AgX Punchy, bloom and depth haze in the compositor. Shared by every preview render.
"""
import math

import bpy

SKY_TOP = (0.035, 0.02, 0.075)
SKY_HORIZON = (0.30, 0.16, 0.34)
HAZE = (0.20, 0.12, 0.30)


def world(scene):
    w = bpy.data.worlds.new("Night")
    scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (*SKY_HORIZON, 1)
    ramp.color_ramp.elements[1].position = 0.45
    ramp.color_ramp.elements[1].color = (*SKY_TOP, 1)
    nt.links.new(sep.outputs["Z"], ramp.inputs[0])
    # stars: sparse bright cells above the horizon
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 260.0
    nt.links.new(tc.outputs["Generated"], vor.inputs["Vector"])
    thr = nt.nodes.new("ShaderNodeMath")
    thr.operation = "LESS_THAN"
    thr.inputs[1].default_value = 0.035
    nt.links.new(vor.outputs["Distance"], thr.inputs[0])
    up = nt.nodes.new("ShaderNodeMath")
    up.operation = "GREATER_THAN"
    up.inputs[1].default_value = 0.12
    nt.links.new(sep.outputs["Z"], up.inputs[0])
    star = nt.nodes.new("ShaderNodeMath")
    star.operation = "MULTIPLY"
    nt.links.new(thr.outputs[0], star.inputs[0])
    nt.links.new(up.outputs[0], star.inputs[1])
    add = nt.nodes.new("ShaderNodeMix")
    add.data_type = "RGBA"
    add.blend_type = "ADD"
    add.inputs["B"].default_value = (0.9, 0.85, 1.0, 1)
    nt.links.new(star.outputs[0], add.inputs["Factor"])
    nt.links.new(ramp.outputs["Color"], add.inputs["A"])
    nt.links.new(add.outputs["Result"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    scene.view_layers[0].use_pass_mist = True
    scene.view_layers[0].use_pass_z = True
    w.mist_settings.start = 15.0
    w.mist_settings.depth = 260.0
    w.mist_settings.falloff = "QUADRATIC"


def lights(scene, moon_azimuth=200.0, moon_elev=36.0, lanterns=(), lantern_energy=140.0):
    col = scene.collection
    sun = bpy.data.lights.new("Moonlight", "SUN")
    sun.energy = 3.4
    sun.color = (0.70, 0.68, 1.0)
    sun.angle = math.radians(3)
    so = bpy.data.objects.new("Moonlight", sun)
    # azimuth measured like the game: 0 = straight down-range (+y), light travels from that bearing
    so.rotation_euler = (math.radians(90 - moon_elev), 0, math.radians(moon_azimuth + 180))
    col.objects.link(so)
    rim = bpy.data.lights.new("Rim", "SUN")
    rim.energy = 1.1
    rim.color = (1.0, 0.55, 0.35)
    ro = bpy.data.objects.new("Rim", rim)
    ro.rotation_euler = (math.radians(70), 0, math.radians(moon_azimuth))
    col.objects.link(ro)
    for i, p in enumerate(lanterns):
        ld = bpy.data.lights.new(f"Lantern_{i}", "POINT")
        ld.energy = lantern_energy
        ld.color = (1.0, 0.5, 0.15)
        ld.shadow_soft_size = 0.2
        ld.use_shadow = False
        lo = bpy.data.objects.new(f"Lantern_{i}", ld)
        lo.location = p
        col.objects.link(lo)


def compositor(scene, haze=HAZE, haze_amount=0.65):
    tree = bpy.data.node_groups.new("Comp", "CompositorNodeTree")
    scene.compositing_node_group = tree
    tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = tree.nodes.new("CompositorNodeRLayers")
    out = tree.nodes.new("NodeGroupOutput")
    # haze only on geometry nearer than 1 km: the sky gradient (and the far moon) stay clean
    near = tree.nodes.new("ShaderNodeMath")
    near.operation = "LESS_THAN"
    near.inputs[1].default_value = 1000.0
    tree.links.new(rl.outputs["Depth"], near.inputs[0])
    mul0 = tree.nodes.new("ShaderNodeMath")
    mul0.operation = "MULTIPLY"
    tree.links.new(rl.outputs["Mist"], mul0.inputs[0])
    tree.links.new(near.outputs[0], mul0.inputs[1])
    mul = tree.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = haze_amount
    tree.links.new(mul0.outputs[0], mul.inputs[0])
    mix = tree.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["B"].default_value = (*haze, 1)
    tree.links.new(mul.outputs[0], mix.inputs["Factor"])
    tree.links.new(rl.outputs["Image"], mix.inputs["A"])
    gl = tree.nodes.new("CompositorNodeGlare")
    for k, v in (("Type", "Bloom"), ("Quality", "High")):
        if k in gl.inputs:
            gl.inputs[k].default_value = v
    for k, v in (("Threshold", 0.8), ("Strength", 0.6), ("Size", 0.6)):
        if k in gl.inputs:
            gl.inputs[k].default_value = v
    tree.links.new(mix.outputs["Result"], gl.inputs["Image"])
    tree.links.new(gl.outputs["Image"], out.inputs[0])


def render_settings(scene, samples=24):
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = samples
    scene.eevee.use_shadows = True
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Punchy"


def setup(scene, lanterns=(), moon_azimuth=200.0, samples=24):
    world(scene)
    lights(scene, moon_azimuth=moon_azimuth, lanterns=lanterns)
    compositor(scene)
    render_settings(scene, samples)
