class_name Hud
extends CanvasLayer
## On-screen text and buttons. Built in code; styled in the game's purple/orange palette.

signal club_pressed
signal next_pressed
signal menu_pressed

const ORANGE := Color(1.0, 0.62, 0.18)
const CREAM := Color(1.0, 0.94, 0.84)
const PURPLE := Color(0.16, 0.08, 0.24, 0.82)

var title := Label.new()
var stroke := Label.new()
var dist := Label.new()
var wind := Label.new()
var wind_arrow := WindArrow.new()
var power := Label.new()
var message := Label.new()
var hint := Label.new()
var club := Button.new()
var card := PanelContainer.new()
var card_title: Label
var card_text: Label
var next := Button.new()
var _msg_time := 0.0
var fade := ColorRect.new()
var _fade_t := 0.0
var fps := Label.new()
var _fps_t := 0.0
var _fps_worst := 0.0


func _panel_style(radius := 18) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = PURPLE
	sb.set_corner_radius_all(radius)
	sb.border_color = Color(1.0, 0.55, 0.15, 0.7)
	sb.set_border_width_all(2)
	sb.content_margin_left = 18
	sb.content_margin_right = 18
	sb.content_margin_top = 10
	sb.content_margin_bottom = 10
	return sb


## The wind arrow, drawn (web builds have no system font to fall back on for an arrow glyph).
class WindArrow extends Control:
	func _draw() -> void:
		var c := Vector2(11, 15)
		var ink := Color(0.06, 0.02, 0.1)
		var col := Color(0.6, 1.0, 0.8)
		var head := PackedVector2Array([c + Vector2(0, -13), c + Vector2(9, -2), c + Vector2(-9, -2)])
		var outline_head := PackedVector2Array([c + Vector2(0, -16), c + Vector2(12, -0.5), c + Vector2(-12, -0.5)])
		draw_line(c + Vector2(0, -3), c + Vector2(0, 13), ink, 8.0)
		draw_colored_polygon(outline_head, ink)
		draw_line(c + Vector2(0, -3), c + Vector2(0, 12), col, 4.0)
		draw_colored_polygon(head, col)


func _label(l: Label, size: int, color := CREAM) -> Label:
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_outline_color", Color(0.06, 0.02, 0.1))
	l.add_theme_constant_override("outline_size", 6)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


func _ready() -> void:
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)

	var top := PanelContainer.new()
	top.add_theme_stylebox_override("panel", _panel_style())
	top.set_anchors_preset(Control.PRESET_TOP_WIDE)
	top.offset_left = 16
	top.offset_right = -16
	top.offset_top = 16
	top.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(top)
	var row := HBoxContainer.new()
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	top.add_child(row)
	var left := VBoxContainer.new()
	left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	left.mouse_filter = Control.MOUSE_FILTER_IGNORE
	row.add_child(left)
	left.add_child(_label(title, 30, ORANGE))
	left.add_child(_label(stroke, 24))
	var right := VBoxContainer.new()
	right.mouse_filter = Control.MOUSE_FILTER_IGNORE
	row.add_child(right)
	dist.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	right.add_child(_label(dist, 30))
	var wrow := HBoxContainer.new()
	wrow.alignment = BoxContainer.ALIGNMENT_END
	wrow.mouse_filter = Control.MOUSE_FILTER_IGNORE
	right.add_child(wrow)
	wind_arrow.custom_minimum_size = Vector2(22, 30)
	wind_arrow.pivot_offset = Vector2(11, 15)
	wind_arrow.mouse_filter = Control.MOUSE_FILTER_IGNORE
	wrow.add_child(wind_arrow)
	wrow.add_child(_label(wind, 24, Color(0.6, 1.0, 0.8)))

	power.set_anchors_preset(Control.PRESET_CENTER)
	power.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	power.position = Vector2(-200, 120)
	power.size = Vector2(400, 120)
	root.add_child(_label(power, 44, ORANGE))

	# just above the horizon, clear of the moon (which sits a fifth to a third of the way down)
	message.anchor_left = 0.5
	message.anchor_right = 0.5
	message.anchor_top = 0.37
	message.anchor_bottom = 0.37
	message.offset_left = -330
	message.offset_right = 330
	message.offset_top = -70
	message.offset_bottom = 70
	message.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	message.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	message.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	root.add_child(_label(message, 46, CREAM))

	hint.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.position = Vector2(-340, -250)
	hint.size = Vector2(680, 90)
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	root.add_child(_label(hint, 26, Color(1, 1, 1, 0.85)))

	var vig := ColorRect.new()
	vig.set_anchors_preset(Control.PRESET_FULL_RECT)
	vig.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var vm := ShaderMaterial.new()
	vm.shader = load("res://shaders/vignette.gdshader")
	vig.material = vm
	root.add_child(vig)
	root.move_child(vig, 0)

	# frame rate in the corner when the web page is opened with #fps (for checking on a phone)
	if OS.has_feature("web") and str(JavaScriptBridge.eval("location.hash", true)) == "#fps":
		fps.position = Vector2(16, 150)
		root.add_child(_label(fps, 24, Color(0.6, 1.0, 0.8)))

	fade.color = Color(0.05, 0.02, 0.08, 0.0)
	fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(fade)

	club.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	club.position = Vector2(-250, -140)
	club.size = Vector2(220, 100)
	club.add_theme_font_size_override("font_size", 28)
	club.add_theme_stylebox_override("normal", _panel_style(24))
	club.add_theme_stylebox_override("hover", _panel_style(24))
	club.add_theme_stylebox_override("pressed", _panel_style(24))
	club.add_theme_color_override("font_color", ORANGE)
	club.pressed.connect(func(): club_pressed.emit())
	root.add_child(club)

	# the score card: a small blackboard in a wooden frame, written in chalk like the clubhouse menu
	var board := StyleBoxFlat.new()
	board.bg_color = Color(0.12, 0.07, 0.13, 0.97)
	board.border_color = Color(0.42, 0.22, 0.1)
	board.set_border_width_all(12)
	board.set_corner_radius_all(10)
	board.shadow_color = Color(0, 0, 0, 0.45)
	board.shadow_size = 18
	board.content_margin_left = 34
	board.content_margin_right = 34
	board.content_margin_top = 30
	board.content_margin_bottom = 34
	card.add_theme_stylebox_override("panel", board)
	card.set_anchors_preset(Control.PRESET_CENTER)
	card.position = Vector2(-290, -230)
	card.size = Vector2(580, 460)
	card.visible = false
	root.add_child(card)
	var cv := VBoxContainer.new()
	cv.alignment = BoxContainer.ALIGNMENT_CENTER
	cv.add_theme_constant_override("separation", 22)
	card.add_child(cv)
	card_title = Chalk.label("", Chalk.head_font(), 76)
	card_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	cv.add_child(card_title)
	card_text = Chalk.label("", Chalk.hand_font(), 40, Chalk.DIM)
	card_text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	cv.add_child(card_text)
	_chalk_button(next, "Play again", Chalk.ORANGE)
	next.pressed.connect(func(): next_pressed.emit())
	cv.add_child(next)
	var menu := Button.new()
	_chalk_button(menu, "Clubhouse", Chalk.WHITE)
	menu.pressed.connect(func(): menu_pressed.emit())
	cv.add_child(menu)


func set_hole(number: int, name: String, par: int) -> void:
	title.text = "Hole %d · %s" % [number, name]
	stroke.text = "Par %d" % par


func set_stroke(n: int, par: int) -> void:
	stroke.text = "Par %d · Stroke %d" % [par, n]


func set_distance(text: String) -> void:
	dist.text = text


## `screen_angle`: wind direction relative to the camera (0 = blowing straight away from you).
func set_wind(speed_mps: float, screen_angle: float) -> void:
	wind.text = " %d mph" % roundi(speed_mps * 2.237) if speed_mps > 0.0 else ""
	wind_arrow.rotation = screen_angle
	wind_arrow.visible = speed_mps > 0.3


func set_club(label: String, yards: float) -> void:
	club.text = "%s\n%d yds" % [label, roundi(yards)]


func set_power(p: float, distance := "") -> void:
	power.text = "" if p <= 0.0 else "%d%%\n~%s" % [roundi(p * 100), distance]


func flash(text: String, seconds := 2.2) -> void:
	message.text = text
	_msg_time = seconds


## True where a touch belongs to a button (the club box, the score card), not to aiming or swinging.
func blocks(p: Vector2) -> bool:
	return (club.is_visible_in_tree() and club.get_global_rect().has_point(p)) \
		or (card.is_visible_in_tree() and card.get_global_rect().has_point(p))


func show_card(title_text: String, detail: String, next_text := "Play again") -> void:
	card_title.text = title_text
	card_text.text = detail
	next.text = next_text
	card.visible = true
	card.modulate.a = 0.0
	card.scale = Vector2.ONE * 0.92
	card.pivot_offset = card.size * 0.5
	var tw := create_tween().set_parallel()
	tw.tween_property(card, "modulate:a", 1.0, 0.3)
	tw.tween_property(card, "scale", Vector2.ONE, 0.35).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)


## A button written in chalk inside a chalk-drawn box.
func _chalk_button(b: Button, text: String, color: Color) -> void:
	b.text = text
	b.focus_mode = Control.FOCUS_NONE
	b.add_theme_font_override("font", Chalk.hand_font())
	b.add_theme_font_size_override("font_size", 40)
	for c in ["font_color", "font_hover_color", "font_pressed_color"]:
		b.add_theme_color_override(c, color)
	var box := StyleBoxFlat.new()
	box.bg_color = Color(1, 1, 1, 0.0)
	box.border_color = Color(color, 0.7)
	box.set_border_width_all(3)
	box.set_corner_radius_all(14)
	box.content_margin_top = 8
	box.content_margin_bottom = 8
	var down := box.duplicate()
	down.bg_color = Color(color, 0.12)
	for s in ["normal", "hover", "focus"]:
		b.add_theme_stylebox_override(s, box)
	b.add_theme_stylebox_override("pressed", down)
	b.material = Chalk.material()


func hide_card() -> void:
	card.visible = false


## Cover the cut to a new shot with a short fade from dark.
## Fade the screen to dark, then run `then` (a scene change).
func fade_out_then(then: Callable) -> void:
	_fade_t = 0.0
	var tw := create_tween()
	tw.tween_property(fade, "color:a", 1.0, 0.3)
	tw.tween_callback(then)


func fade_in(seconds := 0.35) -> void:
	_fade_t = seconds
	fade.color.a = 1.0


func _process(delta: float) -> void:
	if fps.is_inside_tree():
		_fps_worst = maxf(_fps_worst, delta)
		_fps_t += delta
		if _fps_t >= 1.0:
			fps.text = "%d fps · slowest frame %d ms" % [Engine.get_frames_per_second(), roundi(_fps_worst * 1000.0)]
			_fps_t = 0.0
			_fps_worst = 0.0
	if _fade_t > 0.0:
		_fade_t -= delta
		fade.color.a = clampf(_fade_t / 0.35, 0.0, 1.0)
	if _msg_time > 0.0:
		_msg_time -= delta
		message.modulate.a = clampf(_msg_time * 2.0, 0.0, 1.0)
		if _msg_time <= 0.0:
			message.text = ""
