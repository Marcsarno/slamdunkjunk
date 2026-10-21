class_name TouchControls
extends CanvasLayer
## On-screen d-pad and buttons. Only drawn on touch screens; each button
## presses the same input action as the keyboard, so the game sees no
## difference. Multi-touch works: steer with one thumb, sneak with the other.

var pad := Node2D.new()


func _ready() -> void:
	layer = 20
	add_child(pad)
	var c := Vector2(54, 212)
	_button("move_up", "up", c + Vector2(-15, -44), 30)
	_button("move_down", "down", c + Vector2(-15, 14), 30)
	_button("move_left", "left", c + Vector2(-44, -15), 30)
	_button("move_right", "right", c + Vector2(14, -15), 30)
	_button("action", "A", Vector2(424, 196), 38, "A")
	_button("sneak", "B", Vector2(382, 222), 32, "SNEAK")
	_button("menu", "M", Vector2(446, 6), 28, "PACK")


func _button(action: String, glyph: String, at: Vector2, size: int, text := "") -> void:
	var b := TouchScreenButton.new()
	b.texture_normal = Art.touch_button(size, glyph)
	b.texture_pressed = Art.touch_button(size, glyph, true)
	b.action = action
	b.position = at
	b.visibility_mode = TouchScreenButton.VISIBILITY_TOUCHSCREEN_ONLY
	var shape := CircleShape2D.new()
	shape.radius = size / 2.0 + 4
	b.shape = shape
	b.shape_centered = true
	pad.add_child(b)
	if text != "":
		var l := Label.new()
		l.text = text
		l.add_theme_font_override("font", Art.title_font())
		l.add_theme_font_size_override("font_size", 8)
		l.add_theme_color_override("font_color", Art.INK)
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		l.size = Vector2(size, size)
		l.mouse_filter = Control.MOUSE_FILTER_IGNORE
		b.add_child(l)


func set_shown(on: bool) -> void:
	pad.visible = on and (DisplayServer.is_touchscreen_available() or OS.has_feature("force_touch"))
