class_name HoleView
extends Node3D
## Everything you see on a hole: the Blender terrain/props, painted billboard cards, the painted
## sky backdrop and moon, fog and lights, the pin, lantern lights, bats. The look comes from the
## hole's "theme" (courses/holes/<id>.json -> terrain.json); gameplay data lives in Terrain.

const CARD_DIR := "res://assets/cards/"
const TEX_DIR := "res://assets/textures/"
const BACKDROP_DIR := "res://assets/backdrops/"
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
	_horizon_rings()
	_pin()
	_make_bats()
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


func _environment() -> void:
	var bd: Dictionary = theme.get("backdrop", {})
	var style := _sky_style()
	var fog_col := _col(theme.get("fog"), Color(0.30, 0.21, 0.40))
	var top_col := _col(theme.get("sky_top"), Color(0.07, 0.04, 0.14))
	var horizon_col := _col(theme.get("sky_horizon"), Color(0.40, 0.28, 0.50))
	var moon_dir := Vector3(-0.3, 0.55, -0.78).normalized()
	var moon_col := _col(theme.get("moon_light"), Color(0.72, 0.7, 1.0))
	var mat := ShaderMaterial.new()
	mat.shader = load("res://shaders/sky_backdrop.gdshader")
	mat.set_shader_parameter("paint_mix", 1.0 if style == "painted" else 0.0)
	mat.set_shader_parameter("haze", float(theme.get("backdrop_haze", 0.45)))
	if not bd.is_empty():
		var all_meta: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(BACKDROP_DIR + "meta.json"))
		var v: String = bd.get("variant", "a")
		var info: Dictionary = all_meta[bd.hole][v]
		var folder: String = BACKDROP_DIR + bd.hole + "/"
		mat.set_shader_parameter("backdrop", load(folder + v + ".jpg"))
		var span: float = bd.get("span", 90.0)
		var aspect: float = float(info.size[0]) / float(info.size[1])
		var horizon_v: float = bd.get("horizon_v", 0.8)
		var yaw: float = bd.get("yaw", 0.0)
		mat.set_shader_parameter("span_deg", span)
		mat.set_shader_parameter("aspect", aspect)
		mat.set_shader_parameter("horizon_v", horizon_v)
		mat.set_shader_parameter("yaw_deg", yaw)
		if info.has("moon"):
			var mi: Dictionary = info.moon
			mat.set_shader_parameter("moon_tex", load(folder + v + "_moon.png"))
			var box: Array = mi.sprite_box_uv
			var cu := (float(box[0]) + float(box[2])) * 0.5
			var cv := (float(box[1]) + float(box[3])) * 0.5
			var az := deg_to_rad((cu - 0.5) * span + yaw)
			var el := deg_to_rad((horizon_v - cv) * span / aspect)
			var half_deg := (float(box[2]) - float(box[0])) * span * 0.5
			if style != "painted":
				# plain night sky: a clean moon from the hole's element sheet, low enough to be in view
				az = deg_to_rad(float(theme.get("moon_azimuth", -14.0)))
				el = deg_to_rad(float(theme.get("moon_elevation", 24.0)))
				if ResourceLoader.exists(folder + "moon_clean.png"):   # (exported builds hold the imported image, not the .png)
					mat.set_shader_parameter("moon_tex", load(folder + "moon_clean.png"))
					mat.set_shader_parameter("moon_glow", 1.0)
					half_deg = 8.0
			moon_dir = Vector3(sin(az) * cos(el), sin(el), -cos(az) * cos(el))
			mat.set_shader_parameter("moon_half", tan(deg_to_rad(half_deg)))
			mat.set_shader_parameter("moon_scale", float(theme.get("moon_scale", 1.0)))
			mat.set_shader_parameter("moon_dir", moon_dir)
	mat.set_shader_parameter("top_color", top_col)
	mat.set_shader_parameter("horizon_color", horizon_col)
	mat.set_shader_parameter("ground_color", fog_col)
	var sky := Sky.new()
	sky.radiance_size = Sky.RADIANCE_SIZE_32
	sky.sky_material = mat
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	# night lighting (matched by eye to the Blender style render): low cool ambient, moonlight
	# with long shadows, a warm rim from the other side, and lantern glow carrying the scene
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.46, 0.40, 0.66)
	env.ambient_light_energy = float(theme.get("ambient", 0.22))
	env.fog_enabled = true
	env.fog_light_color = fog_col
	env.fog_density = float(theme.get("fog_density", 0.0045))
	env.fog_sky_affect = 0.0
	env.glow_enabled = true
	env.glow_intensity = 1.1
	env.glow_strength = 1.1
	env.glow_bloom = 0.0
	env.glow_hdr_threshold = 1.0
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure = float(theme.get("exposure", 0.9))
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	moon_light.light_color = moon_col
	moon_light.light_energy = float(theme.get("moon_energy", 0.75))
	moon_light.shadow_enabled = true
	moon_light.directional_shadow_max_distance = 80.0
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
	var rim := DirectionalLight3D.new()
	rim.light_color = Color(1.0, 0.56, 0.36)
	rim.light_energy = float(theme.get("rim_energy", 0.32))
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
	m.set_shader_parameter("origin", Vector2(terrain.meta.origin[0], terrain.meta.origin[1]))
	m.set_shader_parameter("extent", Vector2(terrain.meta.extent[0], terrain.meta.extent[1]))
	m.set_shader_parameter("texture_strength", float(theme.get("texture_strength", 0.35)))
	m.set_shader_parameter("brightness", float(theme.get("ground_brightness", 1.0)))
	var none: Array[Vector4] = []
	none.resize(POOLS)
	m.set_shader_parameter("pools", none)
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


## Pumpkin shells glow faintly from the candle inside, which keeps them orange under blue moonlight.
func _pumpkin_material() -> StandardMaterial3D:
	var m := _textured_vc("", 1.0, 1.0, 0.5)
	m.emission_enabled = true
	m.emission = Color(1.0, 0.42, 0.08)
	m.emission_energy_multiplier = 0.35
	return m


func _apply_materials(root: Node) -> void:
	var terrain_mat := _terrain_material()
	_terrain_mat = terrain_mat
	var glow := StandardMaterial3D.new()
	glow.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	glow.albedo_color = Color(1.0, 0.78, 0.35)
	glow.emission_enabled = true
	glow.emission = Color(1.0, 0.55, 0.15)
	glow.emission_energy_multiplier = 4.5
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
	}
	for node in root.find_children("*", "MeshInstance3D", true, false):
		var mi := node as MeshInstance3D
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
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
		mm.mesh = q
		mm.instance_count = list.size()
		for i in list.size():
			var c: Dictionary = list[i]
			var p := Terrain.to_world(Vector3(c.pos[0], c.pos[1], c.pos[2]))
			var s := float(c.height)
			var flip := -1.0 if (i * 7919) % 2 == 1 else 1.0     # mirror half of them for variety
			mm.set_instance_transform(i, Transform3D(Basis().scaled(Vector3(s * flip, s, s)), p))
		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.material_override = _card_material(tex, tint)
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if list[0].get("shadow", false) \
			else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(mmi)


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
	# a pennant like the one on the title art: orange-red, a gentle wave, pointing with the breeze
	var flag := MeshInstance3D.new()
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var cols := 8
	for i in cols:
		var u0 := float(i) / cols
		var u1 := float(i + 1) / cols
		# a triangle 0.8 m long, 0.5 m tall at the pole, tapering to a point
		var a0 := Vector3(u0 * 0.8, 0.25 * (1.0 - u0), 0)
		var b0 := Vector3(u0 * 0.8, -0.25 * (1.0 - u0), 0)
		var a1 := Vector3(u1 * 0.8, 0.25 * (1.0 - u1), 0)
		var b1 := Vector3(u1 * 0.8, -0.25 * (1.0 - u1), 0)
		for v in [a0, b0, a1, a1, b0, b1]:
			st.set_uv(Vector2(v.x / 0.8, 0.5 - v.y * 2.0))
			st.add_vertex(v)
	st.generate_normals()
	flag.mesh = st.commit()
	var fsh := Shader.new()
	fsh.code = """
shader_type spatial;
render_mode cull_disabled;
uniform vec3 color : source_color = vec3(0.95, 0.32, 0.16);
void vertex() {
	// the cloth ripples more toward the free end
	float u = UV.x;
	VERTEX.z += sin(u * 7.0 - TIME * 4.2) * 0.09 * u;
	VERTEX.y += sin(u * 5.0 - TIME * 3.1) * 0.02 * u;
}
void fragment() {
	ALBEDO = color * (0.85 + 0.15 * UV.x);
	EMISSION = color * 0.35;
	ROUGHNESS = 0.8;
}
"""
	var fm := ShaderMaterial.new()
	fm.shader = fsh
	flag.material_override = fm
	flag.position = p + Vector3(0.02, 2.02, 0)
	add_child(flag)
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


func _process(delta: float) -> void:
	_bat_t += delta
	for b in _bats:
		var a: float = b.phase + _bat_t * b.speed
		var c: Vector3 = b.center
		var p := c + Vector3(cos(a) * b.r, sin(a) * b.r * 0.7, sin(_bat_t * 1.7 + b.phase) * b.bob)
		b.node.position = Terrain.to_world(p)
		b.mat.albedo_texture = _bat_tex[int((_bat_t + b.flap) * 9.0) % 2]
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
	if _terrain_mat:
		var pools: Array[Vector4] = []
		for i in POOLS:
			if i < near.size():
				var w := Terrain.to_world(Vector3(near[i][0], near[i][1], near[i][2]))
				pools.append(Vector4(w.x, w.y, w.z, 2.2))
			else:
				pools.append(Vector4.ZERO)
		_terrain_mat.set_shader_parameter("pools", pools)
