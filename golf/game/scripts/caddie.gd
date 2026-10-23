class_name Caddie
extends TextureRect
## Bones, the skeleton caddie, in the bottom-left corner: he presents each hole, leans on his club
## while you aim, points down the line as you pull, cheers a perfect strike or a good score, checks
## the rule book after a penalty, and keeps the score card. Each change of pose pops a little.

const DIR := "res://assets/cast/skelly_"
const HEIGHT := 190.0

var _rest := "lean"
var _back_in := 0.0          # seconds until he goes back to resting (0: stays)
var _idle_t := 0.0
var _textures := {}
var _pose := ""


func _ready() -> void:
	expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	anchor_left = 0.0
	anchor_right = 0.0
	anchor_top = 1.0
	anchor_bottom = 1.0
	_size_for(HEIGHT)
	say(_rest)


func _size_for(h: float) -> void:
	offset_left = 10
	offset_right = 10 + h * 0.8
	offset_bottom = -12
	offset_top = -12 - h
	pivot_offset = Vector2(h * 0.4, h)       # bottom centre: he bounces from his feet


func _tex(pose: String) -> Texture2D:
	if not _textures.has(pose):
		_textures[pose] = load(DIR + pose + ".png")
	return _textures[pose]


## Strike a pose; after `hold` seconds (if over 0) he goes back to resting.
func say(pose: String, hold := 0.0) -> void:
	_back_in = hold
	if pose == _pose:
		return
	_pose = pose
	texture = _tex(pose)
	_size_for(HEIGHT * (1.25 if pose == "card" else 1.0))
	scale = Vector2(1.12, 0.86)
	var tw := create_tween()
	tw.tween_property(self, "scale", Vector2.ONE, 0.35).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)


## What he does when nothing's happening.
func rest() -> void:
	say(_rest)


func _process(delta: float) -> void:
	# a slow sway, so he's never quite still
	rotation = sin(Time.get_ticks_msec() * 0.0017) * 0.025
	if _back_in > 0.0:
		_back_in -= delta
		if _back_in <= 0.0:
			say(_rest)
	if _pose == _rest or _pose == "idle":
		_idle_t += delta
		if _idle_t > 7.0:
			_idle_t = 0.0
			say("idle" if _pose == _rest else _rest)
