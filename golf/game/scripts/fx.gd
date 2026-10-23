class_name Fx
extends Node3D
## One-off effects where the ball comes down: grass flicked up, a puff of sand, a splash with a ring
## spreading on the water, and spirits rising out of the cup when it drops. Each is a short burst of
## CPU particles (works on every renderer) that frees itself when done.

static var _dot: ImageTexture
static var _ring: ImageTexture


static func _dot_texture() -> ImageTexture:
	if _dot == null:
		var n := 32
		var img := Image.create(n, n, false, Image.FORMAT_RGBA8)
		for y in n:
			for x in n:
				var d := Vector2(x - n * 0.5 + 0.5, y - n * 0.5 + 0.5).length() / (n * 0.5)
				img.set_pixel(x, y, Color(1, 1, 1, clampf(1.0 - d, 0.0, 1.0) ** 1.5))
		_dot = ImageTexture.create_from_image(img)
	return _dot


static func _ring_texture() -> ImageTexture:
	if _ring == null:
		var n := 128
		var img := Image.create(n, n, false, Image.FORMAT_RGBA8)
		for y in n:
			for x in n:
				var d := Vector2(x - n * 0.5 + 0.5, y - n * 0.5 + 0.5).length() / (n * 0.5)
				img.set_pixel(x, y, Color(1, 1, 1, clampf(1.0 - absf(d - 0.85) / 0.1, 0.0, 1.0)))
		_ring = ImageTexture.create_from_image(img)
	return _ring


func _particles(at: Vector3, amount: int, life: float, size: Vector2, speed: Vector2, spread: float,
		gravity: Vector3, colors: Array, glow := false) -> CPUParticles3D:
	var p := CPUParticles3D.new()
	var q := QuadMesh.new()
	q.size = Vector2.ONE
	p.mesh = q
	var m := StandardMaterial3D.new()
	m.albedo_texture = _dot_texture()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	m.vertex_color_use_as_albedo = true
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	if glow:
		m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	m.disable_fog = glow
	p.material_override = m
	p.one_shot = true
	p.explosiveness = 0.92
	p.amount = amount
	p.lifetime = life
	p.local_coords = false
	p.direction = Vector3.UP
	p.spread = spread
	p.initial_velocity_min = speed.x
	p.initial_velocity_max = speed.y
	p.gravity = gravity
	p.damping_min = 0.5
	p.damping_max = 1.5
	p.scale_amount_min = size.x
	p.scale_amount_max = size.y
	var grad := Gradient.new()
	var cs := PackedColorArray()
	var offs := PackedFloat32Array()
	for i in colors.size():
		cs.append(colors[i])
		offs.append(float(i) / maxf(1, colors.size() - 1))
	grad.colors = cs
	grad.offsets = offs
	p.color_ramp = grad
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(p)
	p.global_position = at
	p.emitting = true
	get_tree().create_timer(life + 0.5).timeout.connect(p.queue_free)
	return p


## Where a full shot comes down, by what it lands on.
func land(at: Vector3, surface: int, water_tint := Color(0.6, 0.8, 1.0)) -> void:
	match surface:
		Terrain.Surface.SAND:
			_particles(at, 50, 1.4, Vector2(0.3, 0.7), Vector2(1.2, 3.2), 70.0, Vector3(0, -3.0, 0),
				[Color(0.86, 0.74, 0.55, 0.9), Color(0.8, 0.68, 0.5, 0.0)])
		Terrain.Surface.WATER:
			splash(at, water_tint)
		Terrain.Surface.GREEN, Terrain.Surface.FRINGE:
			_particles(at, 14, 0.7, Vector2(0.08, 0.16), Vector2(1.0, 2.2), 50.0, Vector3(0, -6.0, 0),
				[Color(0.5, 0.8, 0.35, 1.0), Color(0.4, 0.7, 0.3, 0.0)])
		_:
			_particles(at, 28, 1.0, Vector2(0.1, 0.25), Vector2(1.5, 3.8), 55.0, Vector3(0, -7.0, 0),
				[Color(0.45, 0.65, 0.25, 1.0), Color(0.5, 0.35, 0.18, 0.0)])


func splash(at: Vector3, tint: Color) -> void:
	_particles(at, 60, 1.1, Vector2(0.08, 0.2), Vector2(3.0, 6.5), 22.0, Vector3(0, -9.8, 0),
		[Color(0.95, 0.98, 1.0, 1.0), Color(tint, 0.0)])
	_particles(at, 18, 1.6, Vector2(0.4, 0.9), Vector2(0.5, 1.4), 80.0, Vector3(0, -0.5, 0),
		[Color(tint, 0.55), Color(tint, 0.0)], true)
	# a ring spreading out on the water
	var ring := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2.ONE
	ring.mesh = plane
	var m := StandardMaterial3D.new()
	m.albedo_texture = _ring_texture()
	m.albedo_color = Color(tint.lerp(Color.WHITE, 0.5), 0.9)
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	ring.material_override = m
	ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(ring)
	ring.global_position = at + Vector3(0, 0.05, 0)
	ring.scale = Vector3.ONE * 0.3
	var tw := create_tween().set_parallel()
	tw.tween_property(ring, "scale", Vector3(5, 1, 5), 1.6).set_ease(Tween.EASE_OUT).set_trans(Tween.TRANS_CUBIC)
	tw.tween_property(m, "albedo_color:a", 0.0, 1.6)
	tw.chain().tween_callback(ring.queue_free)


## The ball drops: spirits swirl up out of the cup, glowing.
func holed(at: Vector3, tint: Color) -> void:
	var p := _particles(at, 40, 2.4, Vector2(0.12, 0.3), Vector2(0.8, 2.4), 28.0, Vector3(0, 0.6, 0),
		[Color(tint.lerp(Color.WHITE, 0.3), 1.0), Color(tint, 0.8), Color(tint, 0.0)], true)
	p.explosiveness = 0.55
	p.tangential_accel_min = 2.0
	p.tangential_accel_max = 4.0
	p.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
	p.emission_sphere_radius = 0.15
