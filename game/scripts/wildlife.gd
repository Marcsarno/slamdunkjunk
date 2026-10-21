class_name Wildlife
extends Node2D
## An animal roaming the map. Wanders its zone tile by tile; once it notices
## Chris it shows "!" and flees (a bear stands its ground instead).

signal stepped(animal: Wildlife)

var species := ""
var tile := Vector2i.ZERO
var zone: Array = []               # [[x0,y0,x1,y1], ...]
var alert := false
var flee_steps := 0
var moving := false
var steps := 0
var calm_timer := 0.0
var think := 0.0
var overworld: Node                # gives can_walk() and player tile

var sprite := Sprite2D.new()
var bubble := Label.new()


func setup(p_species: String, p_tile: Vector2i, p_zone: Array, ow: Node) -> void:
	species = p_species
	tile = p_tile
	zone = p_zone
	overworld = ow
	position = Vector2(tile.x * 16 + 8, tile.y * 16 + 16)


func _ready() -> void:
	var tex: Texture2D = load("res://assets/animals/%s.png" % species)
	var sh := Sprite2D.new()
	var fw := tex.get_width() / 4
	sh.texture = Art.shadow(maxi(8, int(fw * 0.6)), 4)
	sh.position = Vector2(0, -2)
	add_child(sh)
	sprite.texture = tex
	sprite.hframes = 4
	sprite.centered = false
	sprite.offset = Vector2(-fw / 2.0, -tex.get_height() + 1)
	add_child(sprite)
	bubble.text = "!"
	bubble.add_theme_font_override("font", Art.title_font())
	bubble.add_theme_font_size_override("font_size", 16)
	bubble.add_theme_color_override("font_color", Art.BLAZE)
	bubble.add_theme_color_override("font_outline_color", Art.INK)
	bubble.add_theme_constant_override("outline_size", 4)
	bubble.position = Vector2(-4, -tex.get_height() - 16)
	bubble.visible = false
	add_child(bubble)
	think = randf_range(0.2, 1.5)


func data() -> Dictionary:
	return GameData.ANIMALS[species]


func notice(by_player := true) -> void:
	if alert:
		return
	alert = true
	bubble.visible = true
	calm_timer = 6.0
	flee_steps = 0 if species == "black_bear" else 7
	if by_player:
		var tw := create_tween()
		tw.tween_property(bubble, "position:y", bubble.position.y - 4, 0.12)
		tw.tween_property(bubble, "position:y", bubble.position.y, 0.12)


func in_zone(t: Vector2i) -> bool:
	for r in zone:
		if t.x >= r[0] and t.x <= r[2] and t.y >= r[1] and t.y <= r[3]:
			return true
	return false


func _process(delta: float) -> void:
	if moving or overworld.paused:
		return
	if alert:
		calm_timer -= delta
		if calm_timer <= 0.0:
			alert = false
			bubble.visible = false
	think -= delta
	if think > 0.0:
		return
	var options := [Vector2i.UP, Vector2i.DOWN, Vector2i.LEFT, Vector2i.RIGHT]
	if flee_steps > 0:
		flee_steps -= 1
		var away: Vector2i = tile - overworld.player.tile
		options.sort_custom(func(x, y): return Vector2(x).dot(Vector2(away)) > Vector2(y).dot(Vector2(away)))
		for d in options:
			if overworld.animal_can_walk(tile + d, self):
				_step(d, data()["speed"] * 0.55)
				return
		think = 0.3
		return
	if randf() < 0.45:
		think = randf_range(0.8, 2.5)     # browse / look around
		return
	options.shuffle()
	for d in options:
		var t: Vector2i = tile + d
		if overworld.animal_can_walk(t, self) and (in_zone(t) or not in_zone(tile)):
			_step(d, data()["speed"])
			return
	think = 0.6


func _step(d: Vector2i, t: float) -> void:
	moving = true
	if d.x != 0:
		sprite.flip_h = d.x > 0          # sheets face left
	var frames := Player.frames_for_step(steps)
	steps += 1
	sprite.frame = frames[0]
	var target := tile + d
	tile = target                         # claim the tile now so nothing walks into it
	var tw := create_tween()
	tw.tween_property(self, "position", Vector2(target.x * 16 + 8, target.y * 16 + 16), t)
	tw.parallel().tween_callback(func(): sprite.frame = frames[1]).set_delay(t * 0.5)
	await tw.finished
	moving = false
	think = randf_range(0.0, 0.25) if flee_steps > 0 else randf_range(0.1, 0.9)
	stepped.emit(self)
