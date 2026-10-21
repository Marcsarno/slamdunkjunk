class_name Overworld
extends Node2D
## One area of the map, built from assets/areas/<name>.json.
## Handles collisions, doors, exits, animal spawning, noticing and encounters.

signal encounter(animal: Wildlife, opts: Dictionary)
signal door(id: String)
signal exit_area(to: String, tile: Vector2i, face: String)
signal say(text: String)
signal refill_at_truck

const MAX_ANIMALS := 6
const ENGAGE := 2                  # tiles: an encounter starts this close

var area := ""
var map: Dictionary = {}
var w := 0
var h := 0
var blocked: Array = []
var brush: Array = []
var paused := false
var world := Node2D.new()
var player := Player.new()
var animals: Array = []
var respawn := 8.0
var truck_tiles: Array = []
var sign_tiles: Array = []


func build(p_area: String, start: Vector2i, face: String) -> void:
	area = p_area
	var f := FileAccess.open("res://assets/areas/%s.json" % area, FileAccess.READ)
	map = JSON.parse_string(f.get_as_text())
	w = map["w"]
	h = map["h"]
	blocked = map["blocked"]
	brush = map["brush"]

	var ground := Sprite2D.new()
	ground.texture = load("res://assets/areas/" + map["ground"])
	ground.centered = false
	add_child(ground)

	world.y_sort_enabled = true
	add_child(world)
	for p in map["props"]:
		var s := Sprite2D.new()
		s.texture = load("res://assets/props/%s.png" % p["sprite"])
		s.centered = false
		s.position = Vector2(p["x"], p["base_y"])
		s.offset = Vector2(0, p["y"] - p["base_y"])
		world.add_child(s)
		if p["sprite"] == "truck":
			for dx in 3:
				truck_tiles.append(Vector2i(int(p["x"] + 4) / 16 + dx, int(p["base_y"]) / 16 - 1))
		if p["sprite"] == "signpost":
			sign_tiles.append(Vector2i(int(p["x"] + 10) / 16, int(p["base_y"]) / 16 - 1))

	player.can_walk = can_walk
	world.add_child(player)
	player.place(start, face)
	player.stepped.connect(_on_player_step)
	player.bumped.connect(_on_bump)
	player.set_in_grass(is_brush(start))

	var cam := Camera2D.new()
	cam.limit_left = 0
	cam.limit_top = 0
	cam.limit_right = w * 16
	cam.limit_bottom = h * 16
	cam.position_smoothing_enabled = false
	player.add_child(cam)
	cam.offset = Vector2(0, -8)

	if area == "hollow":
		for i in MAX_ANIMALS:
			spawn_one(10)


func _process(delta: float) -> void:
	if paused or area != "hollow":
		return
	respawn -= delta
	if respawn <= 0.0:
		respawn = 12.0
		if animals.size() < MAX_ANIMALS:
			spawn_one(11)


func set_paused(p: bool) -> void:
	paused = p
	player.frozen = p


# ----------------------------------------------------------- collision ----
func inside(t: Vector2i) -> bool:
	return t.x >= 0 and t.y >= 0 and t.x < w and t.y < h


func is_blocked(t: Vector2i) -> bool:
	return not inside(t) or blocked[t.y][t.x] == "1"


func is_brush(t: Vector2i) -> bool:
	return inside(t) and brush[t.y][t.x] == "1"


func animal_at(t: Vector2i) -> Wildlife:
	for a in animals:
		if a.tile == t:
			return a
	return null


func can_walk(t: Vector2i) -> bool:
	return not is_blocked(t) and animal_at(t) == null


func animal_can_walk(t: Vector2i, who: Wildlife) -> bool:
	if is_blocked(t) or t == player.tile:
		return false
	for e in map["exits"]:
		if Vector2i(e["x"], e["y"]) == t:
			return false
	for a in animals:
		if a != who and a.tile == t:
			return false
	return true


# ------------------------------------------------------------- spawning ----
func spawn_one(min_dist: int) -> void:
	var weights: Dictionary = GameData.SPAWN_WEIGHTS
	var total := 0
	for sp in weights:
		total += weights[sp]
	var roll := randi_range(1, total)
	var species := ""
	for sp in weights:
		roll -= weights[sp]
		if roll <= 0:
			species = sp
			break
	# keep the map to one bear at a time
	if species == "black_bear":
		for a in animals:
			if a.species == "black_bear":
				species = "cottontail"
	var zone: Array = map["zones"][species]
	for attempt in 40:
		var r: Array = zone.pick_random()
		var t := Vector2i(randi_range(r[0], r[2]), randi_range(r[1], r[3]))
		if is_blocked(t) or animal_at(t) != null:
			continue
		if absi(t.x - player.tile.x) + absi(t.y - player.tile.y) < min_dist:
			continue
		var a := Wildlife.new()
		a.setup(species, t, zone, self)
		world.add_child(a)
		animals.append(a)
		a.stepped.connect(_on_animal_step)
		return


func remove_animal(a: Wildlife) -> void:
	animals.erase(a)
	a.queue_free()


# --------------------------------------------------------------- senses ----
## Is Chris downwind of this animal (scent blowing away from it)?
func player_downwind_of(a: Wildlife) -> bool:
	var rel: Vector2i = player.tile - a.tile
	return rel.x * Game.wind.x + rel.y * Game.wind.y > 0


func notice_radius(a: Wildlife) -> float:
	var r: float = a.data()["notice"]
	if player.sneaking:
		r *= 0.5
	if "boots" in Game.upgrades:
		r *= 0.8
	if is_brush(player.tile):
		r *= 0.7
	var rel: Vector2i = a.tile - player.tile
	var dot := rel.x * Game.wind.x + rel.y * Game.wind.y
	if dot > 0:
		r *= 1.5      # the wind carries Chris's scent straight to it
	elif dot < 0:
		r *= 0.75
	return r


func _sense(a: Wildlife) -> void:
	if a.alert:
		return
	var d := Vector2(a.tile - player.tile).length()
	if d <= notice_radius(a):
		a.notice()


func _check_encounter() -> void:
	for a in animals:
		var d: int = absi(a.tile.x - player.tile.x) + absi(a.tile.y - player.tile.y)
		if d <= ENGAGE:
			var opts := {"downwind": player_downwind_of(a)}
			if a.alert:
				opts["range"] = BattleRules.LONG
				opts["spook_bonus"] = 30
			elif player.sneaking:
				opts["range"] = BattleRules.CLOSE if d <= 1 else BattleRules.MID
				opts["spook_bonus"] = -10 - (5 if is_brush(player.tile) else 0)
			else:
				opts["range"] = BattleRules.MID
				opts["spook_bonus"] = 0
			encounter.emit(a, opts)
			return


func _on_player_step(t: Vector2i) -> void:
	player.set_in_grass(is_brush(t))
	for e in map["exits"]:
		if Vector2i(e["x"], e["y"]) == t:
			exit_area.emit(e["to"], Vector2i(e["tx"], e["ty"]), e["face"])
			return
	for a in animals:
		_sense(a)
	_check_encounter()


func _on_animal_step(a: Wildlife) -> void:
	if paused:
		return
	_sense(a)
	_check_encounter()


func _on_bump(t: Vector2i) -> void:
	for d in map["doors"]:
		if Vector2i(d["x"], d["y"]) == t:
			door.emit(d["id"])
			return
	if t in truck_tiles:
		refill_at_truck.emit()
		return
	if t in sign_tiles:
		say.emit("MAPLE HOLLOW ->  Hunters: check the wind before you stalk.")
