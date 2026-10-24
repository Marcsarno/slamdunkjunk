class_name IntroFx
extends Node3D
## The opening's high shot over the hole: lightning cracks across the sky (a jagged bolt with the
## ambience's flash of light) and the night's spirits drift past the lens: a flock of bats, lantern
## ghosts, captured spirits and marsh wisps, and little sheet ghosts, all 2D cards facing the camera.
## begin() lays them out along the camera's move; they fade in and out on their own clock and are
## gone when stop() is called (the shot ends, or the opening is skipped).

const CARD_DIR := "res://assets/cards/"
const SPIRITS := ["light_lantern_ghost", "light_captured_spirit", "light_marsh_wisp", "light_skull_lantern"]
const STRIKES := [[0.7, 1.0], [2.5, 0.7]]     # [seconds into the shot, strength]

var ambience: Ambience
var _items: Array = []          # {node, mat, from, vel, t0, t1, flap}
var _bolts: Array = []          # {node, mat, at}
var _t := 0.0
var _running := false
var _bat_tex: Array = []
var _rng := RandomNumberGenerator.new()


func _card(tex: Texture2D, size: float, glow: bool) -> Array:
	var q := QuadMesh.new()
	var asp := float(tex.get_width()) / maxf(1.0, float(tex.get_height()))
	q.size = Vector2(size * asp, size)
	var mi := MeshInstance3D.new()
	mi.mesh = q
	var m := StandardMaterial3D.new()
	m.albedo_texture = tex
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	m.disable_fog = glow
	m.albedo_color = Color(1, 1, 1, 0)
	mi.material_override = m
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mi)
	return [mi, m]


## Lay the spirits out ahead of a camera moving from `from` to `to` (world coords) looking at `look`,
## over `time` seconds.
func begin(from: Vector3, to: Vector3, look: Vector3, time: float) -> void:
	stop()
	_rng.seed = hash(from)
	_running = true
	_t = 0.0
	var fwd := (look - from).normalized()
	var right := fwd.cross(Vector3.UP).normalized()
	var up := right.cross(fwd).normalized()
	# lantern ghosts, spirits and wisps drifting across, one after another
	for k in 6:
		var f := (k + 0.5) / 6.0
		var name: String = SPIRITS[k % SPIRITS.size()]
		if not ResourceLoader.exists(CARD_DIR + name + ".png"):
			continue
		var cam := from.lerp(to, f)
		var side := -1.0 if k % 2 == 0 else 1.0
		var p := cam + fwd * _rng.randf_range(16.0, 30.0) + right * side * _rng.randf_range(4.0, 11.0) + up * _rng.randf_range(-5.0, 3.0)
		var c := _card(load(CARD_DIR + name + ".png"), _rng.randf_range(2.6, 3.8), true)
		_items.append({"node": c[0], "mat": c[1], "from": p, "vel": -right * side * _rng.randf_range(2.5, 4.5) + Vector3(0, 0.6, 0),
			"t0": f * time - 1.3, "t1": f * time + 1.5, "flap": false})
	# sheet ghosts closer in, quick
	var gtex := Ambience._ghost_texture()
	for k in 3:
		var f := 0.25 + 0.3 * k
		var cam := from.lerp(to, f)
		var side := 1.0 if k % 2 == 0 else -1.0
		var p := cam + fwd * _rng.randf_range(10.0, 16.0) + right * side * 6.0 + up * _rng.randf_range(-3.0, 1.0)
		var c := _card(gtex, 1.6, true)
		_items.append({"node": c[0], "mat": c[1], "from": p, "vel": -right * side * 5.0 + Vector3(0, 1.0, 0),
			"t0": f * time - 0.9, "t1": f * time + 1.4, "flap": false})
	# a flock of bats sweeping through the frame
	if _bat_tex.is_empty() and ResourceLoader.exists(CARD_DIR + "bat_up.png"):
		_bat_tex = [load(CARD_DIR + "bat_up.png"), load(CARD_DIR + "bat_down.png")]
	if not _bat_tex.is_empty():
		var lead := from.lerp(to, 0.35) + fwd * 18.0 - right * 16.0 + up * 2.0
		for k in 9:
			var c := _card(_bat_tex[0], _rng.randf_range(1.0, 1.5), false)
			(c[1] as StandardMaterial3D).albedo_color = Color(0.75, 0.65, 0.8, 0)
			var off := right * _rng.randf_range(-3.0, 3.0) + up * _rng.randf_range(-1.5, 1.5) + fwd * _rng.randf_range(-3.0, 3.0)
			_items.append({"node": c[0], "mat": c[1], "from": lead + off, "vel": right * _rng.randf_range(10.0, 12.0) + up * 1.2,
				"t0": 0.6 + _rng.randf_range(0.0, 0.4), "t1": 3.6, "flap": true, "phase": _rng.randf() * 6.0})
	# the lightning: a bolt far off in the sky either side of the line, each with its flash
	# (in the sky over the horizon, whichever way the camera tips: level ahead, high above it)
	var ahead := Vector3(fwd.x, 0.0, fwd.z).normalized()
	for s in STRIKES.size():
		var side := 1.0 if s == 0 else -1.0
		var at := from + ahead * 420.0 + right * side * _rng.randf_range(90.0, 160.0) + Vector3(0, 60.0, 0)
		_bolts.append(_bolt(at, right, Vector3.UP, 170.0 * float(STRIKES[s][1])))
		_bolts[-1]["at"] = float(STRIKES[s][0])
		_bolts[-1]["strength"] = float(STRIKES[s][1])
		_bolts[-1]["fired"] = false


## A jagged lightning bolt hanging from the clouds at `at`, `length` m long, with a fork or two.
func _bolt(at: Vector3, right: Vector3, up: Vector3, length: float) -> Dictionary:
	var im := ImmediateMesh.new()
	var mi := MeshInstance3D.new()
	mi.mesh = im
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	m.disable_fog = true
	m.no_depth_test = true
	m.albedo_color = Color(0.8, 0.85, 1.0, 0.0)
	mi.material_override = m
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mi)
	var top := at + up * (length * 0.75)
	var lines: Array = [_jag(top, -up, right, length, 14, 3.2)]
	for k in 2:
		var from_i := 4 + k * 4
		var p0: Vector3 = lines[0][from_i]
		var d := (-up + right * (0.8 if k == 0 else -0.7)).normalized()
		lines.append(_jag(p0, d, right, length * 0.35, 6, 1.8))
	im.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
	for line: Array in lines:
		var w: float = line[-1]
		for i in line.size() - 2:
			var a: Vector3 = line[i]
			var b: Vector3 = line[i + 1]
			for tri in [[a - right * w, a + right * w, b + right * w], [a - right * w, b + right * w, b - right * w]]:
				for v: Vector3 in tri:
					im.surface_add_vertex(v)
	im.surface_end()
	mi.visible = false
	return {"node": mi, "mat": m}


func _jag(start: Vector3, dir: Vector3, right: Vector3, length: float, steps: int, width: float) -> Array:
	var pts: Array = [start]
	var p := start
	for i in steps:
		p += dir * (length / steps) + right * _rng.randf_range(-1.0, 1.0) * length / steps * 0.7
		pts.append(p)
	pts.append(width)
	return pts


func stop() -> void:
	_running = false
	for it in _items:
		it.node.queue_free()
	for b in _bolts:
		b.node.queue_free()
	_items.clear()
	_bolts.clear()


func _process(delta: float) -> void:
	if not _running:
		return
	_t += delta
	for it in _items:
		var u := (_t - float(it.t0)) / (float(it.t1) - float(it.t0))
		it.node.visible = u > 0.0 and u < 1.0
		if not it.node.visible:
			continue
		var age := _t - float(it.t0)
		var p: Vector3 = it.from + it.vel * age
		p.y += 0.4 * sin(_t * 2.0 + float(it.get("phase", 0.0)))
		it.node.position = p
		var a := smoothstep(0.0, 0.2, u) * (1.0 - smoothstep(0.75, 1.0, u))
		it.mat.albedo_color.a = a * (0.9 if not it.flap else 1.0)
		if it.flap:
			it.mat.albedo_texture = _bat_tex[int(_t * 9.0 + float(it.phase)) % 2]
	for b in _bolts:
		var dt := _t - float(b.at)
		if dt >= 0.0 and not b.fired:
			b.fired = true
			if ambience:
				ambience.strike(float(b.strength))
		# on with the flash's two strokes, then gone
		var on := (dt >= 0.0 and dt < 0.09) or (dt >= 0.16 and dt < 0.3)
		b.node.visible = on
		b.mat.albedo_color.a = (1.0 if dt < 0.09 else 0.7) * float(b.strength) if on else 0.0
