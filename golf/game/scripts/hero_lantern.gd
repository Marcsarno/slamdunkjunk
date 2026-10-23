class_name HeroLantern
extends Node3D
## The giant jack-o'-lantern by the tee (modeled by tools/hero_lantern.py): a carved shell lit from
## inside by a flickering candle that throws warm light on the ground round it. Each hole's opening
## shot swings round it.

const RADIUS := 0.5             # as modeled: about a meter across
const CENTRE_Y := 0.35

var light := OmniLight3D.new()
var _t := randf() * 10.0


func _ready() -> void:
	var scene: Node3D = load("res://assets/props/hero_lantern.glb").instantiate()
	add_child(scene)
	var skin := _vc(0.5)
	skin.emission_enabled = true
	skin.emission = Color(1.0, 0.4, 0.08)
	skin.emission_energy_multiplier = 0.22     # the candle shows faintly through the shell
	skin.rim_enabled = true
	skin.rim = 0.35
	skin.rim_tint = 0.6
	var flesh := _vc(0.8)
	flesh.emission_enabled = true
	flesh.emission = Color(1.0, 0.55, 0.15)
	flesh.emission_energy_multiplier = 2.4
	var cut := _vc(0.8)
	cut.emission_enabled = true
	cut.emission = Color(1.0, 0.7, 0.32)
	cut.emission_energy_multiplier = 1.5
	var wax := _vc(0.6)
	wax.emission_enabled = true
	wax.emission = Color(1.0, 0.75, 0.4)
	wax.emission_energy_multiplier = 0.6
	var flame := StandardMaterial3D.new()
	flame.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	flame.albedo_color = Color(1.0, 0.85, 0.45)
	flame.emission_enabled = true
	flame.emission = Color(1.0, 0.7, 0.25)
	flame.emission_energy_multiplier = 6.0
	var by_name := {"hero_skin": skin, "hero_flesh": flesh, "hero_cut": cut, "hero_stem": _vc(0.85),
		"hero_leaf": _vc(0.75), "hero_wax": wax, "hero_flame": flame}
	for node in scene.find_children("*", "MeshInstance3D", true, false):
		var mi := node as MeshInstance3D
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		for i in mi.mesh.get_surface_count():
			var src := mi.mesh.surface_get_material(i)
			if src and by_name.has(src.resource_name):
				mi.set_surface_override_material(i, by_name[src.resource_name])
	light.light_color = Color(1.0, 0.55, 0.18)
	light.light_energy = 1.4
	light.omni_range = 5.0
	light.omni_attenuation = 1.8
	light.shadow_enabled = false
	light.position = Vector3(0, CENTRE_Y + 0.1, 0.35)    # just in front of the face, so it lights the ground there
	add_child(light)


func _vc(rough: float) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.vertex_color_use_as_albedo = true
	m.vertex_color_is_srgb = true
	m.roughness = rough
	return m


func _process(delta: float) -> void:
	_t += delta
	var f := 0.85 + 0.1 * sin(_t * 13.0) + 0.06 * sin(_t * 23.0 + 1.3) + 0.05 * sin(_t * 5.1)
	light.light_energy = 1.4 * f
