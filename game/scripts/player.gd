class_name Player
extends Node2D
## Chris on the map. Moves one tile per step, Pokémon-style.
##
## The sprite sheets hold 4 frames per direction: 0 left foot forward,
## 1 passing, 2 right foot forward, 3 passing. Each tile step plays half the
## cycle, and the half alternates every step, so the feet always go
## left, right, left, right no matter how many tiles Chris walks.

signal stepped(tile: Vector2i)
signal bumped(tile: Vector2i)

const WALK_TIME := 0.20
const SNEAK_TIME := 0.36
const DIRS := {"up": Vector2i.UP, "down": Vector2i.DOWN, "left": Vector2i.LEFT, "right": Vector2i.RIGHT}

var tile := Vector2i.ZERO
var facing := "down"
var moving := false
var sneaking := false
var steps := 0
var frozen := false
var can_walk: Callable           # func(Vector2i) -> bool, set by the overworld

var sprite := Sprite2D.new()
var shadow := Sprite2D.new()
var grass := Sprite2D.new()       # tall grass drawn over the legs
var textures := {}


static func frames_for_step(step: int) -> Array:
	return [0, 1] if step % 2 == 0 else [2, 3]


func _ready() -> void:
	for d in DIRS:
		textures[d] = load("res://assets/chars/chris_%s.png" % d)
	shadow.texture = Art.shadow(12, 4)
	shadow.position = Vector2(0, -2)
	add_child(shadow)
	sprite.hframes = 4
	sprite.centered = false
	sprite.offset = Vector2(-8, -24)
	add_child(sprite)
	var tg: Texture2D = load("res://assets/props/tall_grass.png")
	grass.texture = tg
	grass.centered = false
	grass.region_enabled = true
	grass.region_rect = Rect2(0, tg.get_height() - 8, tg.get_width(), 8)
	grass.offset = Vector2(-8, -8)
	grass.visible = false
	add_child(grass)
	_face(facing)
	sprite.frame = 1


func place(t: Vector2i, f: String) -> void:
	tile = t
	position = Vector2(t.x * 16 + 8, t.y * 16 + 16)
	_face(f)


func _face(f: String) -> void:
	facing = f
	sprite.texture = textures[f]


func set_in_grass(on: bool) -> void:
	grass.visible = on


func held_direction() -> String:
	if Input.is_action_pressed("move_up"):
		return "up"
	if Input.is_action_pressed("move_down"):
		return "down"
	if Input.is_action_pressed("move_left"):
		return "left"
	if Input.is_action_pressed("move_right"):
		return "right"
	return ""


func _process(_delta: float) -> void:
	sneaking = Input.is_action_pressed("sneak")
	if moving or frozen:
		return
	var d := held_direction()
	if d == "":
		return
	try_step(d)


func try_step(d: String) -> void:
	_face(d)
	var target: Vector2i = tile + DIRS[d]
	if not can_walk.call(target):
		sprite.frame = 1
		bumped.emit(target)
		return
	moving = true
	var frames := frames_for_step(steps)
	steps += 1
	var t := SNEAK_TIME if sneaking else WALK_TIME
	sprite.frame = frames[0]
	var tw := create_tween()
	tw.tween_property(self, "position", Vector2(target.x * 16 + 8, target.y * 16 + 16), t)
	tw.parallel().tween_callback(func(): sprite.frame = frames[1]).set_delay(t * 0.5)
	await tw.finished
	tile = target
	moving = false
	stepped.emit(tile)
	if held_direction() == "":
		sprite.frame = 1
