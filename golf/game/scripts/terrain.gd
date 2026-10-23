class_name Terrain
extends RefCounted
## Height and surface lookups for one hole, read from the files build_hole.py writes.
##
## Everything here works in course coordinates (meters): x right, y down-range, z up.
## Godot world space is x right, y up, z toward the tee, so world = (x, z, -y).

enum Surface { OOB, ROUGH, FAIRWAY, GREEN, SAND, WATER, TEE, FRINGE, DEEP, PATH }

const SURFACE_LABELS := ["Out of bounds", "Rough", "Fairway", "Green", "Bunker", "Water", "Tee",
	"Fringe", "Deep rough", "Cart path"]

var meta: Dictionary
var origin := Vector2.ZERO
var cell := 1.0
var nx := 0
var ny := 0
var heights := PackedFloat32Array()
var surf_cell := 0.5
var snx := 0
var sny := 0
var surface := PackedByteArray()


static func load_hole(dir: String) -> Terrain:
	var t := Terrain.new()
	t.meta = JSON.parse_string(FileAccess.get_file_as_string(dir.path_join("terrain.json")))
	t.origin = Vector2(t.meta.origin[0], t.meta.origin[1])
	t.cell = t.meta.phys.cell
	t.nx = int(t.meta.phys.nx)
	t.ny = int(t.meta.phys.ny)
	t.heights = FileAccess.get_file_as_bytes(dir.path_join(t.meta.phys.file)).to_float32_array()
	t.surf_cell = t.meta.surf.cell
	t.snx = int(t.meta.surf.nx)
	t.sny = int(t.meta.surf.ny)
	t.surface = FileAccess.get_file_as_bytes(dir.path_join(t.meta.surf.file))
	assert(t.heights.size() == t.nx * t.ny, "heights.bin size mismatch")
	assert(t.surface.size() == t.snx * t.sny, "surface.bin size mismatch")
	return t


static func to_world(c: Vector3) -> Vector3:
	return Vector3(c.x, c.z, -c.y)


static func to_course(w: Vector3) -> Vector3:
	return Vector3(w.x, -w.z, w.y)


func _h(i: int, j: int) -> float:
	return heights[clampi(j, 0, ny - 1) * nx + clampi(i, 0, nx - 1)]


## Ground height, interpolated on the same triangles the render mesh uses
## (each cell is split along its (i, j)-(i+1, j+1) diagonal).
func height(x: float, y: float) -> float:
	var fx := (x - origin.x) / cell
	var fy := (y - origin.y) / cell
	var i := floori(fx)
	var j := floori(fy)
	var u := fx - i
	var v := fy - j
	var h00 := _h(i, j)
	var h11 := _h(i + 1, j + 1)
	if u >= v:
		return h00 + (_h(i + 1, j) - h00) * u + (h11 - _h(i + 1, j)) * v
	return h00 + (h11 - _h(i, j + 1)) * u + (_h(i, j + 1) - h00) * v


## Upward unit normal of the ground at (x, y), in course coordinates.
func normal(x: float, y: float) -> Vector3:
	var e := cell * 0.5
	var dx := (height(x + e, y) - height(x - e, y)) / (2.0 * e)
	var dy := (height(x, y + e) - height(x, y - e)) / (2.0 * e)
	return Vector3(-dx, -dy, 1.0).normalized()


## Inside one of the hole's giant spider webs (the layout's "webs": ellipses, course coords)?
func in_web(x: float, y: float) -> bool:
	for w: Dictionary in meta.get("webs", []):
		var c := Vector2(w.center[0], w.center[1])
		var r := Vector2(w.radius[0], w.radius[1])
		var d := Vector2(x, y) - c
		var rot := float(w.get("rotation", 0.0))
		var u := (d.x * cos(rot) + d.y * sin(rot)) / r.x
		var v := (-d.x * sin(rot) + d.y * cos(rot)) / r.y
		if u * u + v * v < 1.0:
			return true
	return false


func surface_at(x: float, y: float) -> int:
	var i := int(round((x - origin.x) / surf_cell))
	var j := int(round((y - origin.y) / surf_cell))
	if i < 0 or j < 0 or i >= snx or j >= sny:
		return Surface.OOB
	return surface[j * snx + i]


func tee() -> Vector3:
	return Vector3(meta.tee[0], meta.tee[1], meta.tee[2])


func pin() -> Vector3:
	return Vector3(meta.pin[0], meta.pin[1], meta.pin[2])
