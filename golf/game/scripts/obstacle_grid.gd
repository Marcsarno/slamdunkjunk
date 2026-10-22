class_name ObstacleGrid
extends RefCounted
## Ball-vs-prop collisions (course coords). Shapes come from props.json:
##   sphere   {pos, r, soft?}     lanterns; "soft" = tree canopy the ball crashes through
##   cylinder {pos, r, h}         tree trunks
##   box      {pos, size, rot}    tombstones (size = width, depth, height; rot about z)
## A uniform 2D hash keeps lookups cheap enough for the per-frame aim preview.

const CELL := 8.0
const BOUNCE := 0.45
const SOFT_DAMP := 0.35

var shapes: Array = []
var buckets := {}


func _init(list: Array) -> void:
	for o in list:
		var s: Dictionary = o.duplicate()
		s.pos = Vector3(o.pos[0], o.pos[1], o.pos[2])
		var reach := 1.0
		match s.type:
			"sphere", "cylinder":
				reach = s.r
			"box":
				reach = Vector2(s.size[0], s.size[1]).length() * 0.5
		var idx := shapes.size()
		shapes.append(s)
		var lo := _key_of(s.pos.x - reach, s.pos.y - reach)
		var hi := _key_of(s.pos.x + reach, s.pos.y + reach)
		for i in range(lo.x, hi.x + 1):
			for j in range(lo.y, hi.y + 1):
				var k := Vector2i(i, j)
				if not buckets.has(k):
					buckets[k] = []
				buckets[k].append(idx)


func _key_of(x: float, y: float) -> Vector2i:
	return Vector2i(floori(x / CELL), floori(y / CELL))


## Returns {} when nothing is hit, else {pos, vel, shape}.
func collide(p: Vector3, v: Vector3, r: float) -> Dictionary:
	var k := _key_of(p.x, p.y)
	if not buckets.has(k):
		return {}
	for idx in buckets[k]:
		var s: Dictionary = shapes[idx]
		var res := {}
		match s.type:
			"sphere":
				res = _sphere(s, p, v, r)
			"cylinder":
				res = _cylinder(s, p, v, r)
			"box":
				res = _box(s, p, v, r)
		if not res.is_empty():
			return res
	return {}


func _reflect(v: Vector3, n: Vector3, e: float) -> Vector3:
	var vn := v.dot(n)
	if vn >= 0.0:
		return v
	return (v - n * vn) * 0.8 - n * vn * e


func _sphere(s: Dictionary, p: Vector3, v: Vector3, r: float) -> Dictionary:
	var c: Vector3 = s.pos
	var sr: float = s.r
	var d := p - c
	var dist := d.length()
	if dist >= sr + r:
		return {}
	if s.get("soft", false):
		# leaves: the ball loses most of its speed and drops; don't push it out
		if v.length() < 3.0:
			return {}
		return {"pos": p, "vel": v * SOFT_DAMP + Vector3(0, 0, -1.0), "shape": s}
	var n := d / maxf(dist, 0.0001)
	return {"pos": c + n * (sr + r), "vel": _reflect(v, n, BOUNCE), "shape": s}


func _cylinder(s: Dictionary, p: Vector3, v: Vector3, r: float) -> Dictionary:
	var c: Vector3 = s.pos
	var sr: float = s.r
	var sh: float = s.h
	if p.z < c.z or p.z > c.z + sh:
		return {}
	var d := Vector2(p.x - c.x, p.y - c.y)
	var dist := d.length()
	if dist >= sr + r:
		return {}
	var n2 := d / maxf(dist, 0.0001)
	var n := Vector3(n2.x, n2.y, 0)
	var out := Vector3(c.x + n2.x * (sr + r), c.y + n2.y * (sr + r), p.z)
	return {"pos": out, "vel": _reflect(v, n, BOUNCE), "shape": s}


func _box(s: Dictionary, p: Vector3, v: Vector3, r: float) -> Dictionary:
	var rot: float = s.rot
	var origin: Vector3 = s.pos
	var c := cos(rot)
	var sn := sin(rot)
	var rel := p - origin
	var lx := rel.x * c + rel.y * sn
	var ly := -rel.x * sn + rel.y * c
	var hx: float = s.size[0] * 0.5
	var hy: float = s.size[1] * 0.5
	var hz: float = s.size[2]
	var q := Vector3(clampf(lx, -hx, hx), clampf(ly, -hy, hy), clampf(rel.z, 0.0, hz))
	var dl := Vector3(lx, ly, rel.z) - q
	var dist := dl.length()
	if dist >= r:
		return {}
	var nl := dl / dist if dist > 0.0001 else Vector3(0, -1, 0)
	var n := Vector3(nl.x * c - nl.y * sn, nl.x * sn + nl.y * c, nl.z)
	var ql := q + nl * r
	var out := origin + Vector3(ql.x * c - ql.y * sn, ql.x * sn + ql.y * c, ql.z)
	return {"pos": out, "vel": _reflect(v, n, BOUNCE), "shape": s}
