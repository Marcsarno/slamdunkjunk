class_name HoleView
extends Node3D
## Everything you see on a hole: the Blender terrain/props, painted billboard cards, the painted
## sky backdrop and moon, fog and lights, the pin, lantern lights, bats, and the Ambience (mist,
## wisps, leaves, ghosts, lightning). The look comes from the
## hole's "theme" (courses/holes/<id>.json -> terrain.json); gameplay data lives in Terrain.

const CARD_DIR := "res://assets/cards/"
const TEX_DIR := "res://assets/textures/"
const BACKDROP_DIR := "res://assets/backdrops/"
const SKY_DIR := "res://assets/sky/"
const LANTERN_LIGHTS := 6
const TERRAIN_LAYER := 2
const POOLS := 16

var dir: String
var terrain: Terrain
var props: Dictionary
var theme: Dictionary
var lantern_lights: Array[OmniLight3D] = []
var camera: Camera3D
var env := Environment.new()
var moon_light := DirectionalLight3D.new()
var _light_timer := 0.0
var _bats: Array = []
var _bat_tex: Array[Texture2D] = []
var _bat_t := 0.0
var _terrain_mat: ShaderMaterial
var ambience := Ambience.new()
var _fog_base := 0.0045
var _sky_mat: ShaderMaterial
var _moon_dir := Vector3(0, 0.5, -1)
var _key_dir := Vector3(0, 0.5, 0.87)     # toward the key light (the ground's hill shading follows it)
var _light_points: Array = []      # [course position, color, pool size, pool strength]: the lanterns and the light props
var _halos: Array = []             # the light props' glows: [halo node, its size, phase], breathing
var _floaters: Array = []          # light props that hover (ghosts, the skull): [node, base y, phase]
var _posts: Array = []             # the post lanterns (tee markers, by the green): [world pos, [their lit materials], halo]
var _lamp_mats: Array[ShaderMaterial] = []    # the lantern faces and pumpkin shells, lit by the front in their shader
# The opening lights the course as the camera goes: a front moves down the hole from the tee, and
# every light behind it is on (each catching over LIGHT_RAMP metres with a flicker), every light past
# it still dark. INF: all on (the rest of the game).
const LIGHT_RAMP := 10.0
var _front_from := Vector3.ZERO    # world coords: where the front is measured from (the tee)...
var _front_dir := Vector3.FORWARD  # ... and the way it goes (level, down the hole)
var _front_d := INF                # how far down the hole it has come, metres


func build(hole_dir: String, t: Terrain) -> void:
	dir = hole_dir
	terrain = t
	theme = t.meta.get("theme", {})
	props = JSON.parse_string(FileAccess.get_file_as_string(dir.path_join("props.json")))
	_environment()
	var scene: Node3D = load(dir.path_join("hole.glb")).instantiate()
	add_child(scene)
	_apply_materials(scene)
	_cards()
	_glow_props()
	_horizon_rings()
	_pin()
	_green_lanterns()
	_tee_markers()
	_webs()
	_make_bats()
	add_child(ambience)
	ambience.build(terrain, props, theme, env)
	for i in LANTERN_LIGHTS:
		var l := OmniLight3D.new()
		l.light_color = Color(1.0, 0.55, 0.2)
		l.light_energy = 2.6
		l.omni_range = 6.5
		l.omni_attenuation = 1.6
		l.shadow_enabled = false
		l.light_cull_mask = ~TERRAIN_LAYER
		add_child(l)
		lantern_lights.append(l)


static func _col(a: Variant, fallback: Color) -> Color:
	if a is Array and a.size() >= 3:
		return Color(a[0], a[1], a[2])
	return fallback


# ---------------------------------------------------------------- sky, fog, light
func _sky_style() -> String:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--sky="):
			return arg.trim_prefix("--sky=")
	return theme.get("sky_style", "night")


## The night's lighting (on top of each hole's theme): how the fill, moon, rim and exposure run
## against the themes' first numbers (a shade darker: Marc wants the night a little darker than the
## first look), the haze the distance fades into (HAZE_MIX 0: plain night fog), and the sky's
## horizon band. All cheap: no extra lights, passes or shadows.
const AMBIENT_COLOR := Color(0.5, 0.53, 0.82)
const AMBIENT_LIFT := 0.7
const MOON_LIFT := 0.75
const MOON_COOL := Color(0.75, 0.82, 1.0)
const RIM_LIFT := 1.0
const EXPOSURE_LIFT := 0.84
const HAZE := Color(0.36, 0.38, 0.58)     # moonlit mist: the colour far things fade toward
const HAZE_MIX := 0.0
const FOG_THIN := 1.0
const HORIZON_LIFT := 1.0


func _environment() -> void:
	var bd: Dictionary = theme.get("backdrop", {})
	var style := _sky_style()
	var fog_col := _col(theme.get("fog"), Color(0.09, 0.09, 0.18))
	var top_col := _col(theme.get("sky_top"), Color(0.004, 0.006, 0.022))
	var horizon_col := _col(theme.get("sky_horizon"), Color(0.035, 0.045, 0.11))
	var moon_col := _col(theme.get("moon_light"), Color(0.72, 0.7, 1.0))
	var mat := ShaderMaterial.new()
	mat.shader = load("res://shaders/night_sky.gdshader")
	# the moon hangs where the theme says (degrees round from straight down the hole, and up)
	var az := deg_to_rad(float(theme.get("moon_azimuth", -14.0)))
	var el := deg_to_rad(float(theme.get("moon_elevation", 13.0)))
	var moon_dir := Vector3(sin(az) * cos(el), sin(el), -cos(az) * cos(el))
	if not bd.is_empty() and style == "painted":
		# the hole's painting, kept only as a skyline under the night sky
		var all_meta: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(BACKDROP_DIR + "meta.json"))
		var v: String = bd.get("variant", "a")
		var info: Dictionary = all_meta[bd.hole][v]
		mat.set_shader_parameter("backdrop", load(BACKDROP_DIR + bd.hole + "/" + v + ".jpg"))
		mat.set_shader_parameter("paint_mix", 1.0)
		mat.set_shader_parameter("span_deg", float(bd.get("span", 90.0)))
		mat.set_shader_parameter("aspect", float(info.size[0]) / float(info.size[1]))
		mat.set_shader_parameter("horizon_v", float(bd.get("horizon_v", 0.8)))
		mat.set_shader_parameter("yaw_deg", float(bd.get("yaw", 0.0)))
		mat.set_shader_parameter("paint_top_deg", float(theme.get("skyline_top", 14.0)))
		mat.set_shader_parameter("paint_dark", float(theme.get("skyline_dark", 0.5)))
	# the painted layers: stars, clouds and the moon (the theme picks the white moon or the harvest moon)
	for layer in ["stars_1", "stars_2", "stars_3", "clouds_bank", "clouds_puffs", "clouds_wisps"]:
		mat.set_shader_parameter(layer, load(SKY_DIR + layer + ".png"))
	var noise := FastNoiseLite.new()
	noise.frequency = 0.05
	var twinkle := NoiseTexture2D.new()
	twinkle.width = 128
	twinkle.height = 128
	twinkle.seamless = true
	twinkle.noise = noise
	mat.set_shader_parameter("twinkle_noise", twinkle)
	mat.set_shader_parameter("cloud_amount", float(theme.get("clouds", 0.6)))
	mat.set_shader_parameter("cloud_tint", _col(theme.get("cloud_tint"), Color(0.55, 0.55, 0.68)))
	mat.set_shader_parameter("star_amount", float(theme.get("stars", 1.0)))
	mat.set_shader_parameter("moon_dir", moon_dir)
	var moon_kind: String = theme.get("moon", "white")
	mat.set_shader_parameter("moon_tex", load(SKY_DIR + "moon_" + moon_kind + ".png"))
	mat.set_shader_parameter("moon_glow", Color(1.0, 0.62, 0.22) if moon_kind == "harvest" else Color(0.85, 0.88, 1.0))
	mat.set_shader_parameter("moon_radius", float(theme.get("moon_size", 0.034)))
	mat.set_shader_parameter("top_color", top_col)
	# a brighter band of night sky at the horizon, so the tree lines stand out against it
	mat.set_shader_parameter("horizon_color", horizon_col * HORIZON_LIFT)
	mat.set_shader_parameter("ground_color", fog_col)
	_sky_mat = mat
	_moon_dir = moon_dir
	var sky := Sky.new()
	sky.radiance_size = Sky.RADIANCE_SIZE_32
	sky.sky_material = mat
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	# night lighting, made to read: a cool moonlit fill so nothing the moon misses goes black, the
	# moon as key with long shadows, a warm rim from the other side, lantern glow, and the distance
	# fading into a pale moonlit haze (not into black), so the far trees and fairways show as layers
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = AMBIENT_COLOR
	env.ambient_light_energy = float(theme.get("ambient", 0.22)) * AMBIENT_LIFT
	env.fog_enabled = true
	env.fog_light_color = fog_col.lerp(HAZE, HAZE_MIX)
	env.fog_density = float(theme.get("fog_density", 0.0045)) * FOG_THIN
	_fog_base = env.fog_density
	env.fog_sky_affect = 0.0
	env.glow_enabled = true
	env.glow_intensity = 1.1
	env.glow_strength = 1.1
	env.glow_bloom = 0.0
	env.glow_hdr_threshold = 1.0
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure = float(theme.get("exposure", 0.9)) * EXPOSURE_LIFT
	# a touch more contrast and colour, so the oranges and purples carry at night
	env.adjustment_enabled = true
	env.adjustment_brightness = Quality.brightness_factor()     # the clubhouse's Brightness option
	env.adjustment_contrast = 1.0
	env.adjustment_saturation = 1.0
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	moon_light.light_color = moon_col.lerp(MOON_COOL, 0.3)
	moon_light.light_energy = float(theme.get("moon_energy", 0.75)) * MOON_LIFT
	moon_light.shadow_enabled = true
	moon_light.directional_shadow_max_distance = 40.0     # shadows round her and the tee; at night farther ones barely show
	moon_light.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL
	moon_light.shadow_blur = 1.5
	add_child(moon_light)
	# Art-directed key light: the moon hangs ahead in the sky, but the light falls from behind the
	# player's shoulder so everything facing the camera is lit (as in the Blender render).
	var key := moon_dir
	if theme.has("light_azimuth"):
		var la := deg_to_rad(float(theme.light_azimuth))
		var le := deg_to_rad(float(theme.get("light_elevation", 38.0)))
		key = Vector3(sin(la) * cos(le), sin(le), -cos(la) * cos(le))
	moon_light.look_at_from_position(key * 100.0, Vector3.ZERO, Vector3.UP)
	moon_dir = key
	_key_dir = key
	var rim := DirectionalLight3D.new()
	rim.light_color = Color(1.0, 0.56, 0.36)
	rim.light_energy = float(theme.get("rim_energy", 0.32)) * RIM_LIFT
	rim.shadow_enabled = false
	add_child(rim)
	var back := Vector3(-moon_dir.x, 0.35, -moon_dir.z).normalized()
	rim.look_at_from_position(back * 100.0, Vector3.ZERO, Vector3.UP)


# ---------------------------------------------------------------- materials
func _texture(name: String) -> Texture2D:
	return load(TEX_DIR + name + ".png")


func _terrain_material() -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = load("res://shaders/terrain.gdshader")
	m.set_shader_parameter("splat", load(dir.path_join(terrain.meta.splat.file)))
	m.set_shader_parameter("detail", load(dir.path_join(terrain.meta.splat.detail)))
	m.set_shader_parameter("tex_rough", _texture("rough"))
	m.set_shader_parameter("tex_fairway", _texture("fairway"))
	m.set_shader_parameter("tex_green", _texture("green"))
	m.set_shader_parameter("tex_sand", _texture("sand"))
	m.set_shader_parameter("tex_cliff", _texture("ravine"))
	if terrain.meta.splat.has("path"):
		m.set_shader_parameter("path_mask", load(dir.path_join(terrain.meta.splat.path)))
		m.set_shader_parameter("tex_path", _texture("stone"))
	m.set_shader_parameter("origin", Vector2(terrain.meta.origin[0], terrain.meta.origin[1]))
	m.set_shader_parameter("extent", Vector2(terrain.meta.extent[0], terrain.meta.extent[1]))
	m.set_shader_parameter("texture_strength", float(theme.get("texture_strength", 0.35)))
	m.set_shader_parameter("brightness", float(theme.get("ground_brightness", 1.0)))
	m.set_shader_parameter("shade_dir", _key_dir)
	m.set_shader_parameter("slope_shade", float(theme.get("slope_shade", 0.6)))
	# the green's cut: stripes across the way in (or a checker, if the theme says), centred on the cup
	var path: Array = terrain.meta.path
	var gin := Vector2(path[-1][0], path[-1][1]) - Vector2(path[-2][0], path[-2][1])
	m.set_shader_parameter("pin_xy", Vector2(terrain.pin().x, terrain.pin().y))
	m.set_shader_parameter("green_dir", gin.normalized() if gin.length() > 0.01 else Vector2(0, 1))
	var cut := str(theme.get("green_cut", "checker" if str(Round.current().get("id", "")) in CHECKER_GREENS else "stripes"))
	m.set_shader_parameter("green_checker", 1.0 if cut == "checker" else 0.0)
	var noise := FastNoiseLite.new()
	noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	noise.frequency = 0.02
	noise.fractal_octaves = 3
	var blotch := NoiseTexture2D.new()
	blotch.width = 256
	blotch.height = 256
	blotch.seamless = true
	blotch.generate_mipmaps = true
	blotch.noise = noise
	m.set_shader_parameter("blotch", blotch)
	m.set_shader_parameter("leaf_color", _col(theme.get("leaf_ground"), Color(0.3, 0.14, 0.05)))
	m.set_shader_parameter("leaf_amount", float(theme.get("leaf_amount", 0.3)))
	var none: Array[Vector4] = []
	none.resize(POOLS)
	m.set_shader_parameter("pools", none)
	m.set_shader_parameter("pool_cols", none)
	return m


## Vertex colors carry the modeled shading (moss, dark bases); a painted texture adds the grain.
func _textured_vc(tex_name: String, scale: float, boost: float, rough: float) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.vertex_color_use_as_albedo = true
	m.albedo_color = Color(boost, boost, boost)
	m.roughness = rough
	if tex_name != "":
		m.albedo_texture = _texture(tex_name)
		m.uv1_triplanar = true
		m.uv1_world_triplanar = true
		m.uv1_scale = Vector3.ONE * scale
		m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	return m


## The chapel's and the house's surfaces (stone, slate, clapboard, brick), drawn by the shader over the
## stone and wood textures every hole loads (shaders/landmark.gdshader).
func _landmark_material() -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = load("res://shaders/landmark.gdshader")
	m.set_shader_parameter("tex_stone", _texture("stone"))
	m.set_shader_parameter("tex_wood", _texture("wood"))
	return m


## Pumpkin shells glow faintly from the candle inside, which keeps them orange under blue moonlight.
func _pumpkin_material() -> ShaderMaterial:
	return _lamp_material(LAMP_SHELL)


## The lit things built into the hole share a material each, so they're lit by the front in their
## shader: a carved face is its warm colour (unshaded) when lit, near black when not; a pumpkin shell
## is lit by the moon like anything else, with the candle's faint glow when lit.
const LAMP_FACE := """
shader_type spatial;
render_mode unshaded, cull_%s;
#include "res://shaders/lamp_front.gdshaderinc"
void fragment() {
	ALBEDO = mix(vec3(0.05, 0.03, 0.02), vec3(1.0, 0.78, 0.35), lamp_on(v_world, TIME));
}
"""
## A chapel's stained glass: red-violet when its light is on.
const LAMP_STAINED := """
shader_type spatial;
render_mode unshaded, cull_%s;
#include "res://shaders/lamp_front.gdshaderinc"
void fragment() {
	ALBEDO = mix(vec3(0.04, 0.02, 0.03), vec3(0.95, 0.2, 0.34), lamp_on(v_world, TIME));
}
"""
## A chapel's leaded lancets: warm glass in a diamond lattice of lead, in the model's own metres.
const LAMP_LEADED := """
shader_type spatial;
render_mode unshaded, cull_%s;
#include "res://shaders/lamp_front.gdshaderinc"
#include "res://shaders/leaded.gdshaderinc"
void fragment() {
	ALBEDO = mix(vec3(0.05, 0.03, 0.02), vec3(1.0, 0.78, 0.35) * leaded(v_local, v_local_n), lamp_on(v_world, TIME));
}
"""
const LAMP_SHELL := """
shader_type spatial;
render_mode cull_%s;
#include "res://shaders/lamp_front.gdshaderinc"
void fragment() {
	ALBEDO = COLOR.rgb;
	ROUGHNESS = 0.5;
	// the candle's glow through the shell, dimmer in the dark creases between lobes
	EMISSION = vec3(1.0, 0.42, 0.08) * 0.45 * (0.3 + 0.7 * smoothstep(0.08, 0.55, COLOR.r)) * lamp_on(v_world, TIME);
}
"""


func _lamp_material(code: String, two_sided := false) -> ShaderMaterial:
	var sh := Shader.new()
	sh.code = code % ("disabled" if two_sided else "back")
	var m := ShaderMaterial.new()
	m.shader = sh
	_lamp_mats.append(m)
	_set_front_params(m)
	return m


func _set_front_params(m: ShaderMaterial) -> void:
	m.set_shader_parameter("front_from", _front_from)
	m.set_shader_parameter("front_dir", _front_dir)
	m.set_shader_parameter("front_d", 1.0e6 if _front_d == INF else _front_d)
	m.set_shader_parameter("ramp", LIGHT_RAMP)


## Start the opening's lighting: everything dark from `from` (world coords, the tee) on down `dir`.
func lights_from(from: Vector3, dir: Vector3) -> void:
	_front_from = from
	_front_dir = Vector3(dir.x, 0.0, dir.z).normalized()
	light_front(-LIGHT_RAMP * 2.0)


## Move the front: lights up to `d` metres down the hole are on. INF turns every light on.
func light_front(d: float) -> void:
	_front_d = d
	for m in _lamp_mats:
		_set_front_params(m)
	_light_timer = 0.0               # the lights and pools follow it this frame, not in a quarter second
	_apply_front()


## How far a light at world `w` has come on, 0 (dark) .. 1, with a candle's flicker while it catches.
func lit(w: Vector3) -> float:
	if _front_d == INF:
		return 1.0
	var on := clampf((_front_d - (w - _front_from).dot(_front_dir)) / LIGHT_RAMP, 0.0, 1.0)
	if on > 0.0 and on < 1.0:
		on *= 0.7 + 0.3 * sin(_bat_t * 31.0 + w.x * 1.7 + w.z * 2.3)
	return on


func _apply_front() -> void:
	for p in _posts:
		var on := lit(p[0])
		for m: StandardMaterial3D in p[1]:
			m.emission_energy_multiplier = HeroLantern.LANTERN_GLOW * on
		p[2].visible = on > 0.0
		p[2].material_override.set_shader_parameter("strength", on)
	for g in _cup_glows:
		g.visible = lit(g.global_position) > 0.5


## A soft additive glow (always facing the camera) at `at` in its parent's space, `size` m across: the
## light hanging round a lantern's face, so it reads as light, not just a bright colour. It sits a little
## toward the camera from its point, so the thing it lights doesn't hide it, and keeps its parent's scale.
static var _halo_shader: Shader


static func glow_halo(at: Vector3, size: float, col: Color, pull := 0.35) -> MeshInstance3D:
	if _halo_shader == null:
		_halo_shader = Shader.new()
		_halo_shader.code = """
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, fog_disabled, shadows_disabled;
uniform vec4 col : source_color = vec4(1.0, 0.55, 0.18, 0.5);
uniform float strength = 1.0;
uniform float pull = 0.35;
void vertex() {
	float s = length(MODEL_MATRIX[0].xyz);
	MODELVIEW_MATRIX = VIEW_MATRIX * mat4(INV_VIEW_MATRIX[0] * s, INV_VIEW_MATRIX[1] * s, INV_VIEW_MATRIX[2] * s, MODEL_MATRIX[3]);
	VERTEX.z += pull / max(s, 0.01);
}
void fragment() {
	float r = length(UV - 0.5) * 2.0;
	ALBEDO = col.rgb * col.a * strength * pow(clamp(1.0 - r, 0.0, 1.0), 1.7);
}
"""
	var q := QuadMesh.new()
	q.size = Vector2.ONE * size
	var m := ShaderMaterial.new()
	m.shader = _halo_shader
	m.set_shader_parameter("col", col)
	m.set_shader_parameter("pull", pull)
	var mi := MeshInstance3D.new()
	mi.mesh = q
	mi.material_override = m
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.position = at
	return mi


const SMALL_PROP := 2.5          # meters: props smaller than this ...
const SMALL_PROP_RANGE := 90.0   # ... aren't drawn past this far from the camera


func _apply_materials(root: Node) -> void:
	var terrain_mat := _terrain_material()
	_terrain_mat = terrain_mat
	var glow := _lamp_material(LAMP_FACE)       # the carved faces and lit windows, dark till the front reaches them
	var water := ShaderMaterial.new()
	water.shader = load("res://shaders/water.gdshader")
	water.set_shader_parameter("sky_color", env.fog_light_color)
	water.set_shader_parameter("deep_color", _col(theme.get("water_deep"), Color(0.025, 0.035, 0.08)))
	water.set_shader_parameter("glow", _col(theme.get("water_glow"), Color(0, 0, 0)))
	var by_name := {
		"terrain": terrain_mat,
		"skirt_vc": terrain_mat,
		"glow": glow,
		"water": water,
		"stone_vc": _textured_vc("stone", 0.9, 2.1, 0.9),
		"dirt_vc": _textured_vc("dirt", 0.8, 2.4, 1.0),
		"pumpkin_vc": _pumpkin_material(),
		"bone_vc": _textured_vc("", 1.0, 1.0, 0.7),
		"iron_vc": _textured_vc("", 1.0, 1.0, 0.45),
		"wood_vc": _textured_vc("wood", 0.7, 1.6, 0.85),
		"LandmarkBody": _textured_vc("wood", 0.5, 2.0, 0.95),
		"hedge_vc": _textured_vc("hedge", 0.45, 2.2, 0.95),
		"LandmarkGlow": _lamp_material(LAMP_FACE, true),
		"LandmarkSurface": _landmark_material(),
		"LandmarkStained": _lamp_material(LAMP_STAINED, true),
		"LandmarkLeaded": _lamp_material(LAMP_LEADED, true),
	}
	for node in root.find_children("*", "MeshInstance3D", true, false):
		var mi := node as MeshInstance3D
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		# small props (tombstones, pumpkins, fences) stop being drawn where they'd be a few pixels: a
		# phone draws fewer things each frame, and the builder needs no change
		var e := mi.get_aabb().size
		if maxf(e.x, maxf(e.y, e.z)) < SMALL_PROP:
			mi.visibility_range_end = SMALL_PROP_RANGE
		for i in mi.mesh.get_surface_count():
			var src := mi.mesh.surface_get_material(i)
			var name := src.resource_name if src else ""
			if not by_name.has(name):
				continue
			if name in ["terrain", "skirt_vc", "water"]:
				mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			if name in ["terrain", "skirt_vc"]:
				mi.layers = TERRAIN_LAYER
			mi.set_surface_override_material(i, by_name[name])


# ---------------------------------------------------------------- painted cards
func _card_material(tex: Texture2D, tint: Color, fog := true) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_texture = tex
	m.billboard_mode = BaseMaterial3D.BILLBOARD_FIXED_Y
	m.billboard_keep_scale = true
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
	m.alpha_scissor_threshold = 0.45
	m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	m.albedo_color = tint
	m.disable_fog = not fog
	return m


## One MultiMesh per image (and shadow setting): thousands of plants in ~20 draw calls.
func _cards() -> void:
	var tint := _col(theme.get("card_tint"), Color(0.8, 0.74, 0.86))
	var groups := {}
	for c in props.cards:
		var key := "%s|%s" % [c.image, c.get("shadow", false)]
		if not groups.has(key):
			groups[key] = []
		groups[key].append(c)
	for key in groups:
		var list: Array = groups[key]
		var tex: Texture2D = load(CARD_DIR + list[0].image + ".png")
		var aspect := float(tex.get_width()) / float(tex.get_height())
		var q := QuadMesh.new()
		q.size = Vector2(aspect, 1.0)
		q.center_offset = Vector3(0, 0.5, 0)
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_colors = true
		mm.mesh = q
		mm.instance_count = list.size()
		for i in list.size():
			var c: Dictionary = list[i]
			var p := Terrain.to_world(Vector3(c.pos[0], c.pos[1], c.pos[2]))
			var s := float(c.height)
			var flip := -1.0 if (i * 7919) % 2 == 1 else 1.0     # mirror half of them for variety
			mm.set_instance_transform(i, Transform3D(Basis().scaled(Vector3(s * flip, s, s)), p))
			mm.set_instance_color(i, Color.WHITE * _woods_shade(float(c.pos[0]), float(c.pos[1])))
		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		var cm := _card_material(tex, tint)
		cm.vertex_color_use_as_albedo = true
		mmi.material_override = cm
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if list[0].get("shadow", false) \
			else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(mmi)


## Beyond the rough is the darkest part of the night: trees and plants out in the deep rough and the
## woods are drawn darker than those by the fairway (so the light props glow against them).
const WOODS_SHADE := {Terrain.Surface.DEEP: 0.78, Terrain.Surface.OOB: 0.6}


func _woods_shade(x: float, y: float) -> float:
	var k: float = WOODS_SHADE.get(terrain.surface_at(x, y), 1.0)
	return k


## The painted light props along the rough (placed by build_hole.py, their light found by prep_lights.py):
## each stands in the world like a card, with a soft halo of its own color where its light is, and
## joins the lanterns for the pooled lights. The ghosts and the skull hover and bob.
func _glow_props() -> void:
	for p in props.lanterns:
		_light_points.append([Vector3(p[0], p[1], p[2]), Color(1.0, 0.55, 0.2), 1.0, 2.2])
	var list: Array = props.get("glows", [])
	if list.is_empty():
		return
	var meta: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(CARD_DIR + "lights.json"))
	var halo_tex := Fx._dot_texture()
	var mats := {}
	for g in list:
		var m: Dictionary = meta[g.image]
		var h := float(g.height)
		var lift := float(g.get("lift", 0.0))
		if not mats.has(g.image):
			var tex: Texture2D = load(CARD_DIR + g.image + ".png")
			var q := QuadMesh.new()
			q.size = Vector2(h * float(m.aspect), h)
			q.center_offset = Vector3(0, h * 0.5, 0)
			var mat := _card_material(tex, Color(1, 1, 1))
			mat.disable_fog = true             # lights read through the night haze
			var col := Color(m.color[0], m.color[1], m.color[2])
			var hm := StandardMaterial3D.new()
			hm.albedo_texture = halo_tex
			hm.albedo_color = Color(col, 0.8)
			hm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
			hm.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
			hm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
			hm.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
			hm.disable_fog = true
			var hq := QuadMesh.new()
			var hs := clampf(h * 2.0, 2.4, 6.0)      # a wide soft glow, so it reads as light, not a sticker
			hq.size = Vector2(hs, hs)
			mats[g.image] = [q, mat, hq, hm, col]
		var parts: Array = mats[g.image]
		var node := Node3D.new()
		add_child(node)
		node.position = Terrain.to_world(Vector3(g.pos[0], g.pos[1], g.pos[2] + lift))
		var body := MeshInstance3D.new()
		body.mesh = parts[0]
		body.material_override = parts[1]
		body.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		node.add_child(body)
		var halo := MeshInstance3D.new()
		halo.mesh = parts[2]
		halo.material_override = parts[3]
		halo.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		halo.position = Vector3(0, h * float(m.glow[1]), 0)
		node.add_child(halo)
		_halos.append([halo, randf() * TAU])
		# its light on the ground round it, in its own colour, as wide as it is tall
		_light_points.append([Vector3(g.pos[0], g.pos[1], g.pos[2] + lift + h * float(m.glow[1])), parts[4],
			clampf(h * 0.8, 1.4, 3.5), 5.0])
		if lift > 0.0 and not g.get("still", false):          # ghosts and the skull hover; a gargoyle sits
			_floaters.append([node, node.position.y, randf() * TAU])


## Optional painted tree-line rings between the course edge and the sky backdrop.
func _horizon_rings() -> void:
	var center := Vector3((terrain.meta.origin[0] + terrain.meta.extent[0]) * 0.5,
		(terrain.meta.origin[1] + terrain.meta.extent[1]) * 0.5, 0)
	for ring in theme.get("rings", []):
		var tex: Texture2D = load("res://assets/sky/" + ring.image + ".png")
		var segs := 64
		var r: float = ring.radius
		var h: float = ring.height
		var base: float = ring.get("base", -8.0)
		var repeats: float = ring.get("repeats", 6.0)
		var st := SurfaceTool.new()
		st.begin(Mesh.PRIMITIVE_TRIANGLES)
		for i in segs:
			var a0 := TAU * i / segs
			var a1 := TAU * (i + 1) / segs
			var u0 := repeats * i / segs
			var u1 := repeats * (i + 1) / segs
			var p0 := Terrain.to_world(center + Vector3(cos(a0) * r, sin(a0) * r, base))
			var p1 := Terrain.to_world(center + Vector3(cos(a1) * r, sin(a1) * r, base))
			var up := Vector3(0, h, 0)
			for vtx in [[p0, Vector2(u0, 1)], [p1, Vector2(u1, 1)], [p1 + up, Vector2(u1, 0)],
					[p0, Vector2(u0, 1)], [p1 + up, Vector2(u1, 0)], [p0 + up, Vector2(u0, 0)]]:
				st.set_uv(vtx[1])
				st.add_vertex(vtx[0])
		var mesh := MeshInstance3D.new()
		mesh.mesh = st.commit()
		var m := StandardMaterial3D.new()
		m.albedo_texture = tex
		m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
		m.alpha_scissor_threshold = 0.4
		m.cull_mode = BaseMaterial3D.CULL_DISABLED
		m.disable_fog = true
		m.albedo_color = Color.WHITE.lerp(env.fog_light_color, float(ring.get("haze", 0.4)))
		m.texture_repeat = true
		mesh.material_override = m
		mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(mesh)


# ---------------------------------------------------------------- pin
## A pair of Marc's post-top pumpkin lanterns behind each green, one at each back corner, faces turned
## back down the hole (background dressing: their glow is all emissive, no lights).
const GREEN_LANTERN := "res://assets/props/lanterns/post.glb"


## The giant spider webs (the layout's "web_art"): Marc's web drawing stretched over each one, draped on
## the ground and glowing faintly lavender in the moonlight.
func _webs() -> void:
	var arts: Array = terrain.meta.get("web_art", [])
	if arts.is_empty():
		return
	var sh := Shader.new()
	sh.code = """
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled;
uniform sampler2D web : source_color, filter_linear_mipmap, repeat_disable;
uniform vec3 tint : source_color = vec3(0.86, 0.8, 1.0);
void fragment() {
	float a = texture(web, UV).a;
	// a slow shimmer along the strands, as if dew or moonlight runs over them
	float shimmer = 0.85 + 0.15 * sin(TIME * 1.3 + (UV.x + UV.y) * 18.0);
	ALBEDO = tint * shimmer;
	ALPHA = a * 0.8;
}
"""
	var mat := ShaderMaterial.new()
	mat.shader = sh
	mat.set_shader_parameter("web", load("res://assets/hazards/web.png"))
	for w: Dictionary in arts:
		var c := Vector2(w.center[0], w.center[1])
		var r := Vector2(w.radius[0], w.radius[1])
		var rot := float(w.get("rotation", 0.0))
		var ax := Vector2(cos(rot), sin(rot))
		var ay := Vector2(-sin(rot), cos(rot))
		var n := clampi(int(maxf(r.x, r.y) / 1.5), 16, 72)     # a vertex every ~1.5 m, so it lies on the ground
		var st := SurfaceTool.new()
		st.begin(Mesh.PRIMITIVE_TRIANGLES)
		for j in n + 1:
			for i in n + 1:
				var u := float(i) / n
				var v := float(j) / n
				var p := c + ax * (u - 0.5) * 2.0 * r.x + ay * (v - 0.5) * 2.0 * r.y
				st.set_uv(Vector2(u, 1.0 - v))
				st.add_vertex(Terrain.to_world(Vector3(p.x, p.y, terrain.height(p.x, p.y) + 0.12)))
		for j in n:
			for i in n:
				var a := j * (n + 1) + i
				for k: int in [a, a + 1, a + n + 2, a, a + n + 2, a + n + 1]:
					st.add_index(k)
		var mi := MeshInstance3D.new()
		mi.mesh = st.commit()
		mi.material_override = mat
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(mi)


func _green_lanterns() -> void:
	if not ResourceLoader.exists(GREEN_LANTERN):
		return
	var g: Dictionary = terrain.meta.green
	var c := Vector2(g.center[0], g.center[1])
	var path: Array = terrain.meta.path
	var a := Vector2(path[path.size() - 2][0], path[path.size() - 2][1])
	var dir := (c - a).normalized()                     # the way the hole comes into the green
	var across := Vector2(dir.y, -dir.x)
	var r := maxf(float(g.radius[0]), float(g.radius[1]))
	var scene: PackedScene = load(GREEN_LANTERN)
	for side: float in [-1.0, 1.0]:
		var q := c + dir * (r + 5.0) + across * side * r * 0.9
		for tries in 4:                                   # out of any water or sand behind the green
			var su := terrain.surface_at(q.x, q.y)
			if su != Terrain.Surface.WATER and su != Terrain.Surface.SAND and su != Terrain.Surface.GREEN:
				break
			q += dir * 3.0
		_lantern_post(scene, q, -dir, 1.0)


## Your pumpkin post lanterns, shrunk, as the tee's markers: one either side a couple of metres ahead
## of the ball, facing her, so the first look down each hole is framed by them.
const TEE_MARKER_SCALE := 0.45


func _tee_markers() -> void:
	if not ResourceLoader.exists(GREEN_LANTERN):
		return
	var path: Array = terrain.meta.path
	var t := Vector2(terrain.tee().x, terrain.tee().y)
	var dir := (Vector2(path[1][0], path[1][1]) - Vector2(path[0][0], path[0][1])).normalized()
	var across := Vector2(dir.y, -dir.x)
	var scene: PackedScene = load(GREEN_LANTERN)
	for side: float in [-1.0, 1.0]:
		_lantern_post(scene, t + dir * 2.6 + across * side * 2.7, -dir, TEE_MARKER_SCALE)


## One post lantern standing at `at` (course coords), its face (local +z) toward `face`, lit up.
func _lantern_post(scene: PackedScene, at: Vector2, face: Vector2, size: float) -> void:
	var post: Node3D = scene.instantiate()
	add_child(post)
	post.position = Terrain.to_world(Vector3(at.x, at.y, terrain.height(at.x, at.y) - 0.03))
	var f := Terrain.to_world(Vector3(face.x, face.y, 0)) - Terrain.to_world(Vector3.ZERO)
	# built before the view is in the tree, so no look_at
	post.basis = Basis.looking_at(-f, Vector3.UP).scaled(Vector3.ONE * size)
	for node in post.find_children("*", "MeshInstance3D", true, false):
		var mi := node as MeshInstance3D
		var mats: Array[StandardMaterial3D] = []
		for i in mi.mesh.get_surface_count():
			var m := mi.mesh.surface_get_material(i) as StandardMaterial3D
			if m and m.emission_enabled:
				m = m.duplicate()
				m.emission_energy_multiplier = HeroLantern.LANTERN_GLOW
				mi.set_surface_override_material(i, m)
				mats.append(m)
		if not mats.is_empty():
			# a soft warm glow hanging round the lit pumpkin
			var t := Transform3D.IDENTITY             # the glowing part's place within the lantern
			var n: Node = mi
			while n != post and n is Node3D:
				t = (n as Node3D).transform * t
				n = n.get_parent()
			var halo := glow_halo(t * mi.get_aabb().get_center(), 1.3, Color(1.0, 0.55, 0.18, 0.5))
			post.add_child(halo)
			_posts.append([post.transform * halo.position, mats, halo])


const FLAG_SIZE := Vector2(0.8, 0.5)
const CUP_DRAWN := BallSim.CUP_DRAWN   # the cup is drawn this many times its real radius (so it reads)
const FLAG_TURN := deg_to_rad(20.0)   # the flag faces the player but this much off square, so it looks solid
var _flag_pivot: Node3D
var _cup_glows: Array = []
## Greens cut in a checker rather than stripes (a layout's theme can say with "green_cut").
const CHECKER_GREENS := ["h03", "h06", "h09"]
## Which of Marc's flags flies on each hole (a layout's theme can name its own with "flag").
const FLAGS := {"h01": "pumpkin", "h02": "moon", "h03": "skull", "h04": "ghost", "h05": "pumpkin",
	"h06": "ghost", "h07": "moon", "h08": "skull", "h09": "pumpkin"}


func _flag_name() -> String:
	return str(theme.get("flag", FLAGS.get(str(Round.current().get("id", "")), "pumpkin")))


func _pin() -> void:
	var p := Terrain.to_world(terrain.pin())
	# the cup: a white liner showing as a rim round the dark hole, like a real one
	# (drawn about twice real size, as golf games do, so it reads from the tee of a putt; the ball
	# still drops by the real cup)
	var liner := MeshInstance3D.new()
	var lm := CylinderMesh.new()
	lm.top_radius = BallSim.CUP_RADIUS * CUP_DRAWN * 1.28
	lm.bottom_radius = lm.top_radius
	lm.height = 0.02
	liner.mesh = lm
	var white_rim := StandardMaterial3D.new()
	white_rim.albedo_color = Color(0.92, 0.92, 0.88)
	white_rim.emission_enabled = true
	white_rim.emission = Color(0.6, 0.6, 0.58)
	liner.material_override = white_rim
	liner.position = p + Vector3(0, 0.004, 0)
	add_child(liner)
	var cup := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = BallSim.CUP_RADIUS * CUP_DRAWN
	cm.bottom_radius = cm.top_radius
	cm.height = 0.02
	cup.mesh = cm
	var dark := StandardMaterial3D.new()
	dark.albedo_color = Color(0.02, 0.02, 0.02)
	cup.material_override = dark
	cup.position = p + Vector3(0, 0.007, 0)
	add_child(cup)
	# a faint glow rising out of the cup (as if something's down there), and a soft ring of light on
	# the grass round it: it finds the eye from across the green without looking like a target
	var cup_glow := glow_halo(p + Vector3(0, 0.22, 0), 0.9, Color(1.0, 0.82, 0.5, 0.42), 0.0)
	add_child(cup_glow)
	var ring := MeshInstance3D.new()
	var rp := PlaneMesh.new()
	rp.size = Vector2.ONE * 0.9
	ring.mesh = rp
	var rmat := StandardMaterial3D.new()
	rmat.albedo_texture = Fx._dot_texture()
	rmat.albedo_color = Color(1.0, 0.85, 0.55, 0.32)
	rmat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	rmat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	rmat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	rmat.disable_fog = true
	ring.material_override = rmat
	ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	ring.position = p + Vector3(0, 0.012, 0)
	add_child(ring)
	_cup_glows = [cup_glow, ring]
	# the pole and flag turn together (see _process): the flag eases round to face whoever is looking
	_flag_pivot = Node3D.new()
	_flag_pivot.position = p
	add_child(_flag_pivot)
	var pole := MeshInstance3D.new()
	var pm := CylinderMesh.new()
	pm.top_radius = 0.02
	pm.bottom_radius = 0.02
	pm.height = 2.3
	pole.mesh = pm
	var white := StandardMaterial3D.new()
	white.albedo_color = Color(0.9, 0.88, 0.85)
	pole.material_override = white
	pole.position = Vector3(0, 1.15, 0)
	_flag_pivot.add_child(pole)
	# Marc's painted flag for the hole (a jack-o'-lantern, ghost, skull or moon and bat), a gentle wave
	var flag := MeshInstance3D.new()
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var cols := 10
	var rows := 2
	for i in cols:
		for j in rows:
			var u0 := float(i) / cols
			var u1 := float(i + 1) / cols
			var v0 := float(j) / rows
			var v1 := float(j + 1) / rows
			# 0.8 m long, 0.5 m tall; the swallowtail is in the texture's alpha
			for uv: Vector2 in [Vector2(u0, v0), Vector2(u0, v1), Vector2(u1, v0), Vector2(u1, v0), Vector2(u0, v1), Vector2(u1, v1)]:
				st.set_uv(uv)
				st.add_vertex(Vector3(uv.x * FLAG_SIZE.x, (0.5 - uv.y) * FLAG_SIZE.y, 0))
	st.generate_normals()
	flag.mesh = st.commit()
	var fsh := Shader.new()
	fsh.code = """
shader_type spatial;
render_mode cull_disabled;
uniform sampler2D cloth : source_color, filter_linear_mipmap;
void vertex() {
	// the cloth ripples more toward the free end
	float u = UV.x;
	VERTEX.z += sin(u * 7.0 - TIME * 4.2) * 0.09 * u;
	VERTEX.y += sin(u * 5.0 - TIME * 3.1) * 0.02 * u;
}
void fragment() {
	vec4 c = texture(cloth, UV);
	ALPHA = c.a;
	ALPHA_SCISSOR_THRESHOLD = 0.5;
	// the folds catch the light as they turn (both faces show the painting, the back one mirrored)
	float fold = 0.82 + 0.18 * sin(UV.x * 7.0 - TIME * 4.2 + 1.2);
	ALBEDO = c.rgb * fold;
	EMISSION = c.rgb * 0.3;
	ROUGHNESS = 0.85;
}
"""
	var fm := ShaderMaterial.new()
	fm.shader = fsh
	fm.set_shader_parameter("cloth", load("res://assets/flags/%s.png" % _flag_name()))
	flag.material_override = fm
	flag.position = Vector3(0.02, 2.3 - FLAG_SIZE.y * 0.5 - 0.02, 0)
	_flag_pivot.add_child(flag)
	# a slim beam to find the pin from far away: bright at the foot, gone by the top, and fading out
	# as you get close (on the green it would only stand in the way)
	var beam := MeshInstance3D.new()
	var bm := CylinderMesh.new()
	bm.top_radius = 0.35
	bm.bottom_radius = 0.12
	bm.height = 40.0
	bm.cap_top = false
	bm.cap_bottom = false
	beam.mesh = bm
	var bsh := Shader.new()
	bsh.code = """
shader_type spatial;
render_mode unshaded, blend_add, cull_disabled, depth_draw_never, fog_disabled;
varying float h;
void vertex() {
	h = VERTEX.y / 40.0 + 0.5;
}
void fragment() {
	float near = smoothstep(14.0, 45.0, length(CAMERA_POSITION_WORLD - NODE_POSITION_WORLD));
	float a = 0.16 * pow(1.0 - h, 1.6) * near;
	ALBEDO = vec3(0.55, 1.0, 0.78) * a;
}
"""
	var bmat := ShaderMaterial.new()
	bmat.shader = bsh
	beam.material_override = bmat
	beam.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	beam.position = p + Vector3(0, 20.0, 0)
	add_child(beam)


# ---------------------------------------------------------------- bats
func _make_bats() -> void:
	if not ResourceLoader.exists(CARD_DIR + "bat_up.png"):
		return
	_bat_tex = [load(CARD_DIR + "bat_up.png"), load(CARD_DIR + "bat_down.png")]
	var tee := terrain.tee()
	var pin := terrain.pin()
	var centers := [tee + Vector3(-6, 55, 16), pin + Vector3(8, -20, 18)]
	for k in 7:
		var q := QuadMesh.new()
		q.size = Vector2(1.5, 1.0) * randf_range(0.7, 1.0)
		var mi := MeshInstance3D.new()
		mi.mesh = q
		var m := _card_material(_bat_tex[0], Color(0.75, 0.65, 0.8))
		m.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
		mi.material_override = m
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(mi)
		_bats.append({"node": mi, "mat": m, "center": centers[k % 2], "r": randf_range(6, 14),
			"speed": randf_range(0.5, 0.9) * (1 if k % 3 else -1), "phase": randf() * TAU,
			"bob": randf_range(1, 3), "flap": randf() * 0.2})


## Turn the flag to face where the player stands (world coords), a touch off square; it stays put
## after that, whatever the camera does, until the next shot is set up.
func face_flag(from: Vector3) -> void:
	if _flag_pivot:
		var d := from - _flag_pivot.global_position
		_flag_pivot.rotation.y = atan2(d.x, d.z) + FLAG_TURN


func _process(delta: float) -> void:
	ambience.camera = camera
	if camera:
		# the fog thins as the camera rises, so the high aiming view looks out over a clear night,
		# not a pale haze (from up there it looks through far more of it)
		var c := Terrain.to_course(camera.global_position)
		var up := smoothstep(8.0, 45.0, c.z - terrain.height(c.x, c.y))
		env.fog_density = _fog_base * lerpf(1.0, 0.3, up)
		ambience.set_height_fade(1.0 - 0.7 * up)
		# the sky measures the moon on the screen with the camera's own view, so it's always round
		var vp := camera.get_viewport().get_visible_rect().size
		var b := camera.global_basis
		_sky_mat.set_shader_parameter("cam_right", b.x)
		_sky_mat.set_shader_parameter("cam_up", b.y)
		_sky_mat.set_shader_parameter("cam_fwd", -b.z)
		var tx := tan(deg_to_rad(camera.fov) * 0.5)
		var aspect := vp.x / vp.y
		# keep_aspect: the camera's fov is across the screen (KEEP_WIDTH) or up it (KEEP_HEIGHT)
		var t := Vector2(tx, tx / aspect) if camera.keep_aspect == Camera3D.KEEP_WIDTH else Vector2(tx * aspect, tx)
		_sky_mat.set_shader_parameter("tan_half", t)
		_sky_mat.set_shader_parameter("screen_aspect", vp.x / vp.y)
	_bat_t += delta
	for f in _floaters:
		f[0].position.y = f[1] + sin(_bat_t * 1.4 + f[2]) * 0.12
	var breathe := 0.85 + 0.15 * sin(_bat_t * 1.3)
	for g in _cup_glows:
		if g.material_override is ShaderMaterial:
			g.material_override.set_shader_parameter("strength", breathe)
		else:
			g.material_override.albedo_color.a = 0.32 * breathe
	for hl in _halos:
		# the glow breathes, slow and a little uneven, like a flame or a spirit (and in the opening,
		# grows in as the light catches)
		var k: float = 1.0 + 0.08 * sin(_bat_t * 1.7 + hl[1]) + 0.04 * sin(_bat_t * 4.3 + hl[1] * 2.0)
		hl[0].scale = Vector3.ONE * maxf(k * lit(hl[0].global_position), 0.001)
	if _front_d != INF:
		_apply_front()
	for b in _bats:
		var a: float = b.phase + _bat_t * b.speed
		var c: Vector3 = b.center
		var p := c + Vector3(cos(a) * b.r, sin(a) * b.r * 0.7, sin(_bat_t * 1.7 + b.phase) * b.bob)
		b.node.position = Terrain.to_world(p)
		b.mat.albedo_texture = _bat_tex[int((_bat_t + b.flap) * 9.0) % 2]
	_light_timer -= delta
	if _light_timer > 0.0 or camera == null:
		return
	_light_timer = 0.25 if _front_d == INF else 0.0
	var cam := camera.global_position
	# the nearest lanterns and light props get the real lights, each in its own color
	var near: Array = _light_points.duplicate()
	near.sort_custom(func(a, b):
		return Terrain.to_world(a[0]).distance_squared_to(cam) < Terrain.to_world(b[0]).distance_squared_to(cam))
	var on := []
	for p in near:
		on.append(lit(Terrain.to_world(p[0])))
	for i in lantern_lights.size():
		var l := lantern_lights[i]
		l.visible = i < near.size() and on[i] > 0.0
		if l.visible:
			l.position = Terrain.to_world(near[i][0] + Vector3(0, 0, 0.35))
			l.light_color = near[i][1]
			l.light_energy = 2.6 * on[i]
	if _terrain_mat:
		# the nearest lights (lanterns and light props together) pool on the ground, each its colour
		var pools: Array[Vector4] = []
		var cols: Array[Vector4] = []
		for i in POOLS:
			if i < near.size():
				var w := Terrain.to_world(near[i][0])
				var col: Color = near[i][1]
				pools.append(Vector4(w.x, w.y, w.z, float(near[i][3]) * on[i]))
				cols.append(Vector4(col.r, col.g, col.b, float(near[i][2])))
			else:
				pools.append(Vector4.ZERO)
				cols.append(Vector4.ZERO)
		_terrain_mat.set_shader_parameter("pools", pools)
		_terrain_mat.set_shader_parameter("pool_cols", cols)
