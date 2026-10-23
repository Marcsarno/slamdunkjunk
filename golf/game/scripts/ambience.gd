class_name Ambience
extends Node3D
## What makes a hole feel alive at night, laid over the built scene: banks of mist drifting along the
## hole, will-o'-the-wisps flickering in the rough, leaves falling around the camera, little sheet
## ghosts haunting the graveyards, and now and then a flash of lightning. All cheap enough for phones:
## mist and wisps move in their shaders, the leaves are one particle system, the ghosts a handful.
##
## Per-hole settings come from the theme (all optional): "mist" (bank count), "mist_alpha",
## "wisp_color", "wisps" (count), "ghosts" (count), "lightning" (average seconds between flashes;
## 0 for none), "leaf_colors".

signal lightning(strength: float)        # a flash just lit the sky (for the thunder that follows)

var terrain: Terrain
var props: Dictionary
var theme: Dictionary
var env: Environment
var camera: Camera3D

var _leaves := CPUParticles3D.new()
var _ghosts: Array = []
var _ghost_t := 0.0
var _flash_light := DirectionalLight3D.new()
var _flash_t := -1.0
var _next_flash := 0.0
var _flash_strength := 1.0
var _base_bg := 1.0
var _base_ambient := 0.2
var _rng := RandomNumberGenerator.new()


func build(t: Terrain, hole_props: Dictionary, hole_theme: Dictionary, environment: Environment) -> void:
	terrain = t
	props = hole_props
	theme = hole_theme
	env = environment
	_rng.seed = hash(str(t.meta.get("id", "hole")))      # the same layout every visit
	_mist()
	_wisps()
	_make_leaves()
	_make_ghosts()
	_flash_light.light_color = Color(0.75, 0.82, 1.0)
	_flash_light.light_energy = 0.0
	_flash_light.shadow_enabled = false
	add_child(_flash_light)
	_flash_light.look_at_from_position(Vector3(10, 100, 30), Vector3.ZERO, Vector3.UP)
	_base_bg = env.background_energy_multiplier
	_base_ambient = env.ambient_light_energy
	_next_flash = _gap() * 0.5


static func _col(a: Variant, fallback: Color) -> Color:
	if a is Array and a.size() >= 3:
		return Color(a[0], a[1], a[2])
	return fallback


## Points along the hole's centre line, about every `step` meters, with the line's direction there.
func _along_path(step: float) -> Array:
	var out := []
	var path: Array = terrain.meta.path
	var carry := 0.0
	for i in range(1, path.size()):
		var a := Vector2(path[i - 1][0], path[i - 1][1])
		var b := Vector2(path[i][0], path[i][1])
		var seg := a.distance_to(b)
		var d := carry
		while d < seg:
			out.append([a.lerp(b, d / seg), (b - a).normalized()])
			d += step
		carry = d - seg
	return out


func _ground(x: float, y: float, up: float) -> Vector3:
	return Terrain.to_world(Vector3(x, y, terrain.height(x, y) + up))


# ---------------------------------------------------------------- mist
func _mist() -> void:
	var count := int(theme.get("mist", 26))
	if count <= 0:
		return
	var spots := []
	# banks either side of the hole, some drifting across it further out, and over any water
	for p in _along_path(22.0):
		var c: Vector2 = p[0]
		var side := Vector2(p[1].y, -p[1].x)
		for s in [-1.0, 1.0]:
			spots.append(c + side * s * _rng.randf_range(24.0, 55.0) + p[1] * _rng.randf_range(-8.0, 8.0))
		if _rng.randf() < 0.35:
			spots.append(c + side * _rng.randf_range(-12.0, 12.0))
	for w in terrain.meta.get("water", []):
		for k in 5:
			var a := _rng.randf() * TAU
			spots.append(Vector2(w.center[0], w.center[1]) + Vector2(cos(a) * w.radius[0], sin(a) * w.radius[1]) * _rng.randf_range(0.5, 1.0))
	# thin the list to the bank count, evenly
	var picked := []
	var stride := maxf(1.0, float(spots.size()) / count)
	var f := 0.0
	while int(f) < spots.size() and picked.size() < count:
		picked.append(spots[int(f)])
		f += stride
	var q := QuadMesh.new()
	q.size = Vector2.ONE
	q.center_offset = Vector3(0, 0.5, 0)
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_custom_data = true
	mm.mesh = q
	mm.instance_count = picked.size()
	for i in picked.size():
		var p: Vector2 = picked[i]
		var w := _rng.randf_range(26.0, 48.0)
		var h := _rng.randf_range(5.0, 9.0)
		mm.set_instance_transform(i, Transform3D(Basis().scaled(Vector3(w, h, w)), _ground(p.x, p.y, -1.5)))
		mm.set_instance_custom_data(i, Color(_rng.randf(), 0, 0, 0))
	var noise := FastNoiseLite.new()
	noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	noise.frequency = 0.012
	noise.fractal_octaves = 4
	var tex := NoiseTexture2D.new()
	tex.width = 256
	tex.height = 256
	tex.seamless = true
	tex.noise = noise
	var m := ShaderMaterial.new()
	m.shader = load("res://shaders/mist.gdshader")
	m.set_shader_parameter("noise", tex)
	var fog := env.fog_light_color
	m.set_shader_parameter("color", _col(theme.get("mist_color"), fog.lerp(Color(0.86, 0.86, 0.96), 0.65)))
	m.set_shader_parameter("alpha", float(theme.get("mist_alpha", 0.45)))
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	mmi.material_override = m
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mmi)


# ---------------------------------------------------------------- wisps
func _wisps() -> void:
	var count := int(theme.get("wisps", 60))
	var trees := []
	for c in props.get("cards", []):
		if c.image in ["dead_tree", "haunted_tree", "maple_red", "maple_orange", "pine_blue", "birch", "lantern_tree", "apple_tree"]:
			trees.append(c)
	if trees.is_empty() or count <= 0:
		return
	var q := QuadMesh.new()
	q.size = Vector2.ONE
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_custom_data = true
	mm.mesh = q
	mm.instance_count = count
	for i in count:
		var c: Dictionary = trees[_rng.randi() % trees.size()]
		var x: float = c.pos[0] + _rng.randf_range(-6.0, 6.0)
		var y: float = c.pos[1] + _rng.randf_range(-6.0, 6.0)
		var s := _rng.randf_range(0.4, 0.7)
		mm.set_instance_transform(i, Transform3D(Basis().scaled(Vector3.ONE * s), _ground(x, y, _rng.randf_range(0.6, 3.2))))
		mm.set_instance_custom_data(i, Color(_rng.randf(), _rng.randf(), 0, 0))
	var m := ShaderMaterial.new()
	m.shader = load("res://shaders/wisp.gdshader")
	m.set_shader_parameter("color", _col(theme.get("wisp_color"), Color(1.0, 0.6, 0.25)))
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	mmi.material_override = m
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mmi)


# ---------------------------------------------------------------- leaves
## A leaf, drawn: a pointed oval with a darker midrib, in white (tinted per particle).
static func _leaf_texture() -> ImageTexture:
	var w := 32
	var img := Image.create(w, w, false, Image.FORMAT_RGBA8)
	for y in w:
		for x in w:
			var u := (x + 0.5) / w * 2.0 - 1.0
			var v := (y + 0.5) / w * 2.0 - 1.0
			var half := 0.55 * (1.0 - v * v) * (1.0 - 0.25 * v)       # wide near the stem, a pointed tip
			var inside := absf(u) < half and absf(v) < 0.95
			var a := 0.0
			if inside:
				a = clampf((half - absf(u)) * 8.0, 0.0, 1.0)
			var rib := 0.75 if absf(u) < 0.06 else 1.0
			img.set_pixel(x, y, Color(rib, rib, rib, a))
	return ImageTexture.create_from_image(img)


func _make_leaves() -> void:
	var colors: Array = theme.get("leaf_colors", [[0.95, 0.45, 0.12], [0.85, 0.22, 0.1], [0.95, 0.7, 0.2]])
	var q := QuadMesh.new()
	q.size = Vector2(0.16, 0.16)
	_leaves.mesh = q
	var m := StandardMaterial3D.new()
	m.albedo_texture = _leaf_texture()
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
	m.alpha_scissor_threshold = 0.4
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	m.vertex_color_use_as_albedo = true
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	_leaves.material_override = m
	_leaves.amount = 46
	_leaves.lifetime = 9.0
	_leaves.preprocess = 9.0
	_leaves.local_coords = false
	_leaves.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	_leaves.emission_box_extents = Vector3(16, 5, 16)
	_leaves.direction = Vector3(1, -0.3, 0)
	_leaves.spread = 180.0
	_leaves.initial_velocity_min = 0.2
	_leaves.initial_velocity_max = 0.8
	_leaves.gravity = Vector3(0.25, -0.55, 0.1)
	_leaves.angular_velocity_min = -160.0
	_leaves.angular_velocity_max = 160.0
	_leaves.angle_min = 0.0
	_leaves.angle_max = 360.0
	_leaves.scale_amount_min = 0.7
	_leaves.scale_amount_max = 1.5
	var grad := Gradient.new()
	grad.offsets = PackedFloat32Array([0.0, 0.5, 1.0])
	var cs := PackedColorArray()
	for k in 3:
		var c: Array = colors[k % colors.size()]
		cs.append(Color(c[0], c[1], c[2]))
	grad.colors = cs
	_leaves.color_initial_ramp = grad
	_leaves.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_leaves)


# ---------------------------------------------------------------- ghosts
## A little sheet ghost, drawn: a round head and body with a wavy hem, hollow eyes and an "o" mouth.
static func _ghost_texture() -> ImageTexture:
	var w := 96
	var h := 128
	var img := Image.create(w, h, false, Image.FORMAT_RGBA8)
	for y in h:
		for x in w:
			var u := (x + 0.5) / w * 2.0 - 1.0          # -1..1 across
			var v := (y + 0.5) / h                       # 0 top .. 1 bottom
			var body := 0.0
			var head_r := 0.78
			var cy := 0.36
			var dy := (v - cy) * (float(h) / w) * 2.0
			if v < cy:
				body = 1.0 if u * u + dy * dy < head_r * head_r else 0.0
			else:
				var hem := 0.9 + 0.06 * sin(u * 9.0)            # wavy bottom edge
				var widen := head_r + (v - cy) * 0.25
				body = 1.0 if absf(u) < widen and v < hem else 0.0
			# soft edge
			var a := body
			var eye := (Vector2(u + 0.3, (v - 0.33) * 1.6).length() < 0.14) or (Vector2(u - 0.3, (v - 0.33) * 1.6).length() < 0.14)
			var mouth := Vector2(u, (v - 0.52) * 1.4).length() < 0.11
			var col := Color(0.92, 0.97, 1.0, a * (0.92 - 0.25 * smoothstep(0.55, 0.92, v)))
			if body > 0.0 and (eye or mouth):
				col = Color(0.06, 0.04, 0.12, a)
			img.set_pixel(x, y, col)
	return ImageTexture.create_from_image(img)


func _make_ghosts() -> void:
	var count := int(theme.get("ghosts", 2))
	if count <= 0:
		return
	# haunt where the tombstones are thickest: count them on a 16 m grid
	var cells := {}
	for o in props.get("obstacles", []):
		if o.type != "box":
			continue
		var k := Vector2i(int(floor(o.pos[0] / 16.0)), int(floor(o.pos[1] / 16.0)))
		cells[k] = cells.get(k, 0) + 1
	var spots := []
	var keys := cells.keys()
	keys.sort_custom(func(a, b): return cells[a] > cells[b])
	for k in keys:
		spots.append(Vector2((k.x + 0.5) * 16.0, (k.y + 0.5) * 16.0))
	if spots.is_empty():
		for p in _along_path(40.0):
			spots.append(p[0] + Vector2(p[1].y, -p[1].x) * 30.0 * (1 if _rng.randf() < 0.5 else -1))
	var tex := _ghost_texture()
	for i in count:
		var c: Vector2 = spots[i % spots.size()]
		var q := QuadMesh.new()
		q.size = Vector2(1.35, 1.8) * _rng.randf_range(0.85, 1.15)
		var mi := MeshInstance3D.new()
		mi.mesh = q
		var m := StandardMaterial3D.new()
		m.albedo_texture = tex
		m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		m.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
		m.depth_draw_mode = BaseMaterial3D.DEPTH_DRAW_DISABLED
		m.albedo_color = Color(1.25, 1.35, 1.5, 0.0)      # over 1: a faint glow in the bloom
		mi.material_override = m
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(mi)
		_ghosts.append({"node": mi, "mat": m, "center": c, "r": _rng.randf_range(2.5, 7.0),
			"speed": _rng.randf_range(0.18, 0.35) * (1 if _rng.randf() < 0.5 else -1),
			"phase": _rng.randf() * TAU, "cycle": _rng.randf_range(9.0, 15.0), "lift": _rng.randf_range(1.2, 2.4)})


# ---------------------------------------------------------------- lightning
func _gap() -> float:
	var every := float(theme.get("lightning", 0.0))
	return INF if every <= 0.0 else _rng.randf_range(every * 0.5, every * 1.5)


func _process(delta: float) -> void:
	if camera:
		# leaves fall in front of wherever the camera looks, a little above the ground there
		var fwd := -camera.global_basis.z
		var c := camera.global_position + Vector3(fwd.x, 0, fwd.z).normalized() * 12.0
		var cc := Terrain.to_course(c)
		_leaves.global_position = Terrain.to_world(Vector3(cc.x, cc.y, terrain.height(cc.x, cc.y) + 5.0))
	_ghost_t += delta
	for g in _ghosts:
		var a: float = g.phase + _ghost_t * g.speed
		var c: Vector2 = g.center
		var p := c + Vector2(cos(a), sin(a)) * float(g.r)
		var h := terrain.height(p.x, p.y) + float(g.lift) + 0.35 * sin(_ghost_t * 1.3 + g.phase)
		g.node.position = Terrain.to_world(Vector3(p.x, p.y, h))
		# fade in, linger, fade away, stay gone a while: a ghost is never quite there for long
		var u := fmod(_ghost_t + g.phase * 3.0, float(g.cycle)) / float(g.cycle)
		var vis := smoothstep(0.0, 0.12, u) * (1.0 - smoothstep(0.7, 0.82, u))
		g.mat.albedo_color.a = 0.8 * vis
	_next_flash -= delta
	if _next_flash <= 0.0:
		_next_flash = _gap()
		_flash_t = 0.0
		_flash_strength = _rng.randf_range(0.6, 1.0)
		lightning.emit(_flash_strength)
	if _flash_t >= 0.0:
		_flash_t += delta
		# two quick strokes, then a fading after-glow
		var k := 0.0
		if _flash_t < 0.08:
			k = 1.0
		elif _flash_t < 0.16:
			k = 0.25
		elif _flash_t < 0.24:
			k = 0.9
		elif _flash_t < 0.9:
			k = 0.9 * (1.0 - (_flash_t - 0.24) / 0.66)
		else:
			_flash_t = -1.0
		k *= _flash_strength
		_flash_light.light_energy = 2.2 * k
		env.background_energy_multiplier = _base_bg * (1.0 + 1.6 * k)
		env.ambient_light_energy = _base_ambient * (1.0 + 2.5 * k)
