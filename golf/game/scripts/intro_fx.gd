class_name IntroFx
extends Node3D
## The opening's lightning: as the camera hangs high over the hole a jagged bolt cracks across the sky,
## with the ambience's flash of light over the course (and its thunder, which main plays after a
## flash). begin() hangs the bolt in the sky ahead of the camera; it's gone when stop() is called.

const STRIKES := [[0.6, 1.0]]     # [seconds into the opening, strength]

var ambience: Ambience
var _bolts: Array = []          # {node, mat, at, strength, fired}
var _t := 0.0
var _running := false
var _rng := RandomNumberGenerator.new()


## Hang the bolt in the sky ahead of a camera at `from` (world coords) looking toward `look`.
func begin(from: Vector3, look: Vector3, _time: float) -> void:
	stop()
	_rng.seed = hash(from)
	_running = true
	_t = 0.0
	var fwd := (look - from).normalized()
	var right := fwd.cross(Vector3.UP).normalized()
	# in the sky over the horizon, whichever way the camera tips: level ahead, high above it
	var ahead := Vector3(fwd.x, 0.0, fwd.z).normalized()
	for s in STRIKES.size():
		var side := 1.0 if s % 2 == 0 else -1.0
		var at := from + ahead * 420.0 + right * side * _rng.randf_range(90.0, 160.0) + Vector3(0, 60.0, 0)
		_bolts.append(_bolt(at, right, Vector3.UP, 170.0 * float(STRIKES[s][1])))
		_bolts[-1]["at"] = float(STRIKES[s][0])
		_bolts[-1]["strength"] = float(STRIKES[s][1])
		_bolts[-1]["fired"] = false


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
	for b in _bolts:
		b.node.queue_free()
	_bolts.clear()


func _process(delta: float) -> void:
	if not _running:
		return
	_t += delta
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
