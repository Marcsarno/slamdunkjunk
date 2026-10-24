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
		Terrain.Surface.PATH:
			_particles(at, 16, 0.8, Vector2(0.12, 0.3), Vector2(0.8, 1.8), 60.0, Vector3(0, -2.0, 0),
				[Color(0.62, 0.58, 0.52, 0.7), Color(0.5, 0.47, 0.42, 0.0)])
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


static var _divot_shader: Shader


## Turf torn out by the club: dark earth with a ragged edge of broken grass (`sod` > 0.5: the
## piece itself, grass side up, with earth showing round its torn rim).
static func _divot_material(sod: bool) -> ShaderMaterial:
	if _divot_shader == null:
		_divot_shader = Shader.new()
		_divot_shader.code = """
shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_opaque;     // matched to the night turf by eye, not lit
uniform float sod = 0.0;
uniform float seed = 0.0;
float h(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7)) + seed) * 43758.5453); }
float n(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(h(i), h(i + vec2(1, 0)), f.x), mix(h(i + vec2(0, 1)), h(i + vec2(1, 1)), f.x), f.y);
}
void fragment() {
	vec2 q = (UV - 0.5) * 2.0;
	// a rounded, slightly tapered oval with a ragged rim
	float r = length(vec2(q.x * (1.0 + 0.25 * q.y), q.y));
	float rag = n(UV * vec2(9.0, 22.0)) * 0.22 + n(UV * 40.0) * 0.1;
	if (r > 1.0 - rag) { discard; }
	float rim = smoothstep(0.55, 0.95 - rag, r);
	float grit = n(UV * 60.0);
	vec3 earth = mix(vec3(0.24, 0.15, 0.08), vec3(0.4, 0.27, 0.15), grit);
	vec3 torn = mix(vec3(0.45, 0.5, 0.2), vec3(0.62, 0.6, 0.3), n(UV * vec2(8.0, 50.0)));   // pale broken blades
	vec3 grass = mix(vec3(0.3, 0.46, 0.12), vec3(0.4, 0.56, 0.16), n(UV * vec2(8.0, 50.0)));
	// the scar: darker earth in the deep middle, paler where it shallows, torn grass round the rim
	ALBEDO = sod > 0.5 ? mix(grass, earth, rim * 0.8) : mix(earth * (0.7 + 0.35 * r), torn, rim * step(0.45, n(UV * 30.0)));
}
"""
	var m := ShaderMaterial.new()
	m.shader = _divot_shader
	m.set_shader_parameter("sod", 1.0 if sod else 0.0)
	m.set_shader_parameter("seed", randf() * 100.0)
	return m


static func _flat(size: Vector2, sod: bool) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = size
	mi.mesh = pm
	mi.material_override = _divot_material(sod)
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return mi


## A basis lying on the ground (`n` up) with its length along `dir`.
static func _lying(n: Vector3, dir: Vector3) -> Basis:
	var fwd := (dir - n * dir.dot(n)).normalized()
	var side := n.cross(fwd).normalized()
	return Basis(side, n, -fwd).orthonormalized()


## An iron or wedge strikes down through the turf: the scar of earth starts just past the ball and
## stays (under `keep`, cleared with the hole); the sod is flung on ahead, tumbling, and lies where
## `sod_at` says; soil and grass spray forward. `size` 1 is a full short iron's divot.
func divot(at: Vector3, n: Vector3, dir: Vector3, size: float, sod_at: Vector3, sod_n: Vector3, keep: Node3D) -> void:
	var dims := Vector2(0.13, 0.3) * size        # a touch bigger than life so it reads from her camera
	var scar := _flat(dims, false)
	keep.add_child(scar)
	scar.global_transform = Transform3D(_lying(n, dir), at + dir * (0.03 + dims.y * 0.5) + n * 0.006)
	var piece := _flat(dims * Vector2(0.95, 0.85), true)
	keep.add_child(piece)
	var start := at + dir * dims.y * 0.6 + n * 0.03
	var rest := Transform3D(_lying(sod_n, dir).rotated(sod_n, randf_range(-0.6, 0.6)), sod_at + sod_n * 0.012)
	var flight := 0.55 + 0.15 * size
	var spin := Vector3(randf_range(5.0, 9.0), randf_range(-3.0, 3.0), randf_range(-2.0, 2.0))
	var up := (rest.origin.y - start.y + 4.9 * flight * flight) / flight      # rises, falls onto its spot
	var tw := create_tween()
	tw.tween_method(func(t: float) -> void:
		var s := t * flight
		var p := start.lerp(rest.origin, t)
		p.y = start.y + up * s - 4.9 * s * s
		var b := rest.basis
		if t < 1.0:
			b = rest.basis * Basis.from_euler(spin * (1.0 - t) * 2.2)
		piece.global_transform = Transform3D(b, p), 0.0, 1.0, flight)
	# soil and grass sprayed on ahead
	var p := _particles(at + dir * 0.1, int(18 * size) + 6, 0.9, Vector2(0.03, 0.08), Vector2(1.5, 3.5), 18.0,
		Vector3(0, -9.8, 0), [Color(0.3, 0.2, 0.1, 1.0), Color(0.35, 0.5, 0.18, 1.0), Color(0.3, 0.22, 0.12, 0.0)])
	p.direction = (dir + Vector3.UP * 0.9).normalized()


## Splashed out of a bunker: the club takes sand, not the ball, and it bursts up and forward.
func sand_blast(at: Vector3, dir: Vector3) -> void:
	var p := _particles(at + dir * 0.05, 70, 1.3, Vector2(0.06, 0.18), Vector2(1.5, 4.5), 30.0, Vector3(0, -6.0, 0),
		[Color(0.88, 0.77, 0.58, 1.0), Color(0.82, 0.7, 0.52, 0.0)])
	p.direction = (dir + Vector3.UP * 1.3).normalized()
	_particles(at, 14, 1.8, Vector2(0.4, 0.8), Vector2(0.3, 1.0), 70.0, Vector3(0, -0.3, 0),
		[Color(0.86, 0.76, 0.6, 0.45), Color(0.8, 0.7, 0.55, 0.0)])
