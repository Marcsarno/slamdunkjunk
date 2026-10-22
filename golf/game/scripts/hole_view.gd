class_name HoleView
extends Node3D
## Everything you see on a hole: the Blender terrain/props, painted billboard cards, sky,
## fog and lights, the pin, lantern lights. Gameplay data lives in Terrain / props.json.

const CARD_DIR := "res://assets/cards/"
const LANTERN_LIGHTS := 6

var dir: String
var terrain: Terrain
var props: Dictionary
var lantern_lights: Array[OmniLight3D] = []
var _light_timer := 0.0
var camera: Camera3D


func build(hole_dir: String, t: Terrain) -> void:
	dir = hole_dir
	terrain = t
	props = JSON.parse_string(FileAccess.get_file_as_string(dir.path_join("props.json")))
	_environment()
	var scene: Node3D = load(dir.path_join("hole.glb")).instantiate()
	add_child(scene)
	_apply_materials(scene)
	_cards()
	_backdrop()
	_pin()
	for i in LANTERN_LIGHTS:
		var l := OmniLight3D.new()
		l.light_color = Color(1.0, 0.55, 0.2)
		l.light_energy = 2.2
		l.omni_range = 7.0
		l.omni_attenuation = 1.4
		l.shadow_enabled = false
		add_child(l)
		lantern_lights.append(l)


func _environment() -> void:
	var env := Environment.new()
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.07, 0.03, 0.15)
	sky_mat.sky_horizon_color = Color(0.42, 0.2, 0.36)
	sky_mat.sky_curve = 0.12
	sky_mat.ground_horizon_color = Color(0.2, 0.12, 0.22)
	sky_mat.ground_bottom_color = Color(0.05, 0.03, 0.08)
	sky_mat.sun_angle_max = 0.0
	var sky := Sky.new()
	sky.sky_material = sky_mat
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.42, 0.36, 0.6)
	env.ambient_light_energy = 0.75
	env.fog_enabled = true
	env.fog_light_color = Color(0.32, 0.2, 0.42)
	env.fog_density = 0.0045
	env.fog_sky_affect = 0.25
	env.glow_enabled = true
	env.glow_intensity = 0.9
	env.glow_bloom = 0.08
	env.glow_hdr_threshold = 0.9
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure = 1.05
	var dbg := OS.get_cmdline_user_args()
	if "--nofog" in dbg:
		env.fog_enabled = false
	if "--noglow" in dbg:
		env.glow_enabled = false
	if "--flatsky" in dbg:
		env.background_mode = Environment.BG_COLOR
		env.background_color = Color(0.1, 0.05, 0.2)
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	var moon := DirectionalLight3D.new()
	moon.light_color = Color(0.74, 0.7, 1.0)
	moon.light_energy = 1.1
	moon.shadow_enabled = true
	moon.directional_shadow_max_distance = 80.0
	moon.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL
	moon.rotation = Vector3(deg_to_rad(-38), deg_to_rad(150), 0)
	add_child(moon)


func _vc_material(rough: float) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.vertex_color_use_as_albedo = true
	m.roughness = rough
	return m


func _apply_materials(root: Node) -> void:
	var albedo: Texture2D = load(dir.path_join("albedo.png"))
	var terrain_mat := StandardMaterial3D.new()
	terrain_mat.albedo_texture = albedo
	terrain_mat.roughness = 1.0
	terrain_mat.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	var glow := StandardMaterial3D.new()
	glow.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	glow.albedo_color = Color(1.0, 0.78, 0.35)
	glow.emission_enabled = true
	glow.emission = Color(1.0, 0.55, 0.15)
	glow.emission_energy_multiplier = 3.0
	var water := StandardMaterial3D.new()
	water.albedo_color = Color(0.04, 0.07, 0.11, 0.92)
	water.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	water.metallic = 0.7
	water.roughness = 0.06
	water.emission_enabled = true
	water.emission = Color(0.12, 0.06, 0.2)
	var cache := {}
	for node in root.find_children("*", "MeshInstance3D", true, false):
		var mi := node as MeshInstance3D
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		for i in mi.mesh.get_surface_count():
			var src := mi.mesh.surface_get_material(i)
			var name := src.resource_name if src else ""
			var m: Material
			if name == "terrain":
				m = terrain_mat
				mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			elif name == "glow":
				m = glow
			elif name == "water":
				m = water
				mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			elif name.ends_with("_vc"):
				if not cache.has(name):
					cache[name] = _vc_material(0.9 if name != "pumpkin_vc" else 0.55)
				m = cache[name]
				if name == "skirt_vc":
					mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			else:
				continue
			mi.set_surface_override_material(i, m)


func _card_material(tex: Texture2D, fog := true) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_texture = tex
	m.billboard_mode = BaseMaterial3D.BILLBOARD_FIXED_Y
	m.billboard_keep_scale = true
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
	m.alpha_scissor_threshold = 0.45
	m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	m.albedo_color = Color(0.78, 0.72, 0.86)       # moonlit: painted art sits a touch darker/cooler
	m.disable_fog = not fog
	return m


## One MultiMesh per painted image: hundreds of trees in ~10 draw calls.
func _cards() -> void:
	var groups := {}
	for c in props.cards:
		if not groups.has(c.image):
			groups[c.image] = []
		groups[c.image].append(c)
	for img in groups:
		var tex: Texture2D = load(CARD_DIR + img + ".png")
		var aspect := float(tex.get_width()) / float(tex.get_height())
		var q := QuadMesh.new()
		q.size = Vector2(aspect, 1.0)
		q.center_offset = Vector3(0, 0.5, 0)
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = q
		mm.instance_count = groups[img].size()
		for i in groups[img].size():
			var c: Dictionary = groups[img][i]
			var p := Terrain.to_world(Vector3(c.pos[0], c.pos[1], c.pos[2]))
			mm.set_instance_transform(i, Transform3D(Basis().scaled(Vector3.ONE * float(c.height)), p))
		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.material_override = _card_material(tex)
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		add_child(mmi)


## Moon and a ring of far forest so the horizon works from any camera angle.
func _backdrop() -> void:
	var center := Vector3((terrain.meta.origin[0] + terrain.meta.extent[0]) * 0.5,
		(terrain.meta.origin[1] + terrain.meta.extent[1]) * 0.5, 0)
	var pines: Texture2D = load(CARD_DIR + "pines_distant.png")
	var aspect := float(pines.get_width()) / float(pines.get_height())
	var q := QuadMesh.new()
	q.size = Vector2(aspect, 1.0)
	q.center_offset = Vector3(0, 0.5, 0)
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = q
	var n := 64
	mm.instance_count = n
	var radius: float = maxf(terrain.meta.extent[1] - terrain.meta.origin[1], 260.0) * 0.75
	for i in n:
		var a := TAU * i / n + randf() * 0.05
		var r := radius * (1.0 + 0.12 * sin(i * 2.7))
		var c := center + Vector3(cos(a) * r, sin(a) * r, -6.0)
		var hgt := 34.0 + 10.0 * sin(i * 1.7)
		mm.set_instance_transform(i, Transform3D(Basis().scaled(Vector3.ONE * hgt), Terrain.to_world(c)))
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	var m := _card_material(pines)
	m.albedo_color = Color(0.55, 0.45, 0.7)
	mmi.material_override = m
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mmi)

	var moon_tex: Texture2D = load(CARD_DIR + "moon.png")
	var moon := MeshInstance3D.new()
	var mq := QuadMesh.new()
	mq.size = Vector2(float(moon_tex.get_width()) / moon_tex.get_height(), 1.0) * 120.0
	moon.mesh = mq
	var mm2 := _card_material(moon_tex, false)
	mm2.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	mm2.albedo_color = Color(1.4, 1.3, 1.2)
	moon.material_override = mm2
	moon.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var pin := terrain.pin()
	moon.position = Terrain.to_world(Vector3(pin.x + 260, pin.y + 700, 190))
	add_child(moon)


func _pin() -> void:
	var p := Terrain.to_world(terrain.pin())
	var cup := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = BallSim.CUP_RADIUS * 1.6
	cm.bottom_radius = cm.top_radius
	cm.height = 0.02
	cup.mesh = cm
	var dark := StandardMaterial3D.new()
	dark.albedo_color = Color(0.02, 0.02, 0.02)
	cup.material_override = dark
	cup.position = p + Vector3(0, 0.005, 0)
	add_child(cup)
	var pole := MeshInstance3D.new()
	var pm := CylinderMesh.new()
	pm.top_radius = 0.02
	pm.bottom_radius = 0.02
	pm.height = 2.3
	pole.mesh = pm
	var white := StandardMaterial3D.new()
	white.albedo_color = Color(0.9, 0.88, 0.85)
	pole.material_override = white
	pole.position = p + Vector3(0, 1.15, 0)
	add_child(pole)
	var flag := MeshInstance3D.new()
	var fq := QuadMesh.new()
	fq.size = Vector2(0.75, 0.5)
	flag.mesh = fq
	var fm := StandardMaterial3D.new()
	fm.albedo_color = Color(1.0, 0.35, 0.1)
	fm.emission_enabled = true
	fm.emission = Color(1.0, 0.3, 0.05)
	fm.emission_energy_multiplier = 1.5
	fm.cull_mode = BaseMaterial3D.CULL_DISABLED
	flag.material_override = fm
	flag.position = p + Vector3(0.38, 2.05, 0)
	add_child(flag)
	# a faint ghost-light column so the pin is findable from the tee
	var beam := MeshInstance3D.new()
	var bm := CylinderMesh.new()
	bm.top_radius = 0.6
	bm.bottom_radius = 0.25
	bm.height = 40.0
	bm.cap_top = false
	bm.cap_bottom = false
	beam.mesh = bm
	var bmat := StandardMaterial3D.new()
	bmat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	bmat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	bmat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	bmat.albedo_color = Color(0.5, 1.0, 0.75, 0.08)
	bmat.cull_mode = BaseMaterial3D.CULL_DISABLED
	bmat.disable_fog = true
	beam.material_override = bmat
	beam.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	beam.position = p + Vector3(0, 20.0, 0)
	add_child(beam)


func _process(delta: float) -> void:
	_light_timer -= delta
	if _light_timer > 0.0 or camera == null:
		return
	_light_timer = 0.25
	var cam := camera.global_position
	var near: Array = props.lanterns.duplicate()
	near.sort_custom(func(a, b):
		return Terrain.to_world(Vector3(a[0], a[1], a[2])).distance_squared_to(cam) \
			< Terrain.to_world(Vector3(b[0], b[1], b[2])).distance_squared_to(cam))
	for i in lantern_lights.size():
		var l := lantern_lights[i]
		l.visible = i < near.size()
		if l.visible:
			var p: Array = near[i]
			l.position = Terrain.to_world(Vector3(p[0], p[1], p[2] + 0.35))
