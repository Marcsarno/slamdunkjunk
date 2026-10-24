class_name HeroLantern
extends Node3D
## The lantern by the tee (Marc's hanging-pumpkin lantern: an old painted-wood post with a braced arm,
## a carved pumpkin hanging from it, lit from inside; tools/prep_lanterns.py lightens his model to
## ~3.6k triangles in one piece). A flickering candle light inside throws warm light round it. Each
## hole's opening shot swings round the pumpkin.

const MODEL := "res://assets/props/lanterns/arm.glb"
const PUMPKIN := Vector3(0.94, 1.5, 0.0)    # the hanging pumpkin's middle, from the post's foot (its face toward +z)
const RADIUS := 0.44

var light := OmniLight3D.new()
var _t := randf() * 10.0


const LANTERN_GLOW := 7.0      # the carved face's glow: well over the bloom threshold, so it blazes


func _ready() -> void:
	var scene: Node3D = load(MODEL).instantiate()
	add_child(scene)
	for node in scene.find_children("*", "MeshInstance3D", true, false):
		var mi := node as MeshInstance3D
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		for i in mi.mesh.get_surface_count():
			var m := mi.mesh.surface_get_material(i) as StandardMaterial3D
			if m and m.emission_enabled:
				m = m.duplicate()
				m.emission_energy_multiplier = LANTERN_GLOW   # the candle inside blazes through the carving
				mi.set_surface_override_material(i, m)
	add_child(HoleView.glow_halo(PUMPKIN, 1.6, Color(1.0, 0.55, 0.18, 0.55), 0.62))
	light.light_color = Color(1.0, 0.55, 0.18)
	light.light_energy = 1.4
	light.omni_range = 5.5
	light.omni_attenuation = 1.6
	light.shadow_enabled = false
	light.position = PUMPKIN + Vector3(0, -0.05, 0.35)    # just in front of the face, so it lights the ground there
	add_child(light)


## The pumpkin's middle in the world (where the opening camera looks and swings round).
func pumpkin_world() -> Vector3:
	return to_global(PUMPKIN)


func _process(delta: float) -> void:
	_t += delta
	var f := 0.85 + 0.1 * sin(_t * 13.0) + 0.06 * sin(_t * 23.0 + 1.3) + 0.05 * sin(_t * 5.1)
	light.light_energy = 1.4 * f
