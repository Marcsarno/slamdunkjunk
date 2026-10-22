class_name Hud
extends CanvasLayer
## On-screen text and buttons. Built in code; styled in the game's purple/orange palette.

signal club_pressed
signal next_pressed

const ORANGE := Color(1.0, 0.62, 0.18)
const CREAM := Color(1.0, 0.94, 0.84)
const PURPLE := Color(0.16, 0.08, 0.24, 0.82)

var title := Label.new()
var stroke := Label.new()
var dist := Label.new()
var wind := Label.new()
var wind_arrow := Label.new()
var power := Label.new()
var message := Label.new()
var hint := Label.new()
var club := Button.new()
var card := PanelContainer.new()
var card_text := Label.new()
var next := Button.new()
var _msg_time := 0.0
var fade := ColorRect.new()
var _fade_t := 0.0


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
	wind_arrow.text = "↑"
	wind_arrow.pivot_offset = Vector2(10, 18)
	wrow.add_child(_label(wind_arrow, 30, Color(0.6, 1.0, 0.8)))
	wrow.add_child(_label(wind, 24, Color(0.6, 1.0, 0.8)))

	power.set_anchors_preset(Control.PRESET_CENTER)
	power.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	power.position = Vector2(-200, 120)
	power.size = Vector2(400, 120)
	root.add_child(_label(power, 44, ORANGE))

	message.set_anchors_preset(Control.PRESET_CENTER_TOP)
	message.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	message.position = Vector2(-330, 250)
	message.size = Vector2(660, 140)
	message.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	root.add_child(_label(message, 46, CREAM))

	hint.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.position = Vector2(-340, -250)
	hint.size = Vector2(680, 90)
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	root.add_child(_label(hint, 26, Color(1, 1, 1, 0.85)))

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

	card.add_theme_stylebox_override("panel", _panel_style(28))
	card.set_anchors_preset(Control.PRESET_CENTER)
	card.position = Vector2(-280, -220)
	card.size = Vector2(560, 440)
	card.visible = false
	root.add_child(card)
	var cv := VBoxContainer.new()
	cv.alignment = BoxContainer.ALIGNMENT_CENTER
	cv.add_theme_constant_override("separation", 24)
	card.add_child(cv)
	card_text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	cv.add_child(_label(card_text, 38))
	next.text = "Play again"
	next.add_theme_font_size_override("font_size", 34)
	next.add_theme_stylebox_override("normal", _panel_style(24))
	next.add_theme_color_override("font_color", ORANGE)
	next.pressed.connect(func(): next_pressed.emit())
	cv.add_child(next)


func set_hole(number: int, name: String, par: int) -> void:
	title.text = "Hole %d · %s" % [number, name]
	stroke.text = "Par %d" % par


func set_stroke(n: int, par: int) -> void:
	stroke.text = "Par %d · Stroke %d" % [par, n]


func set_distance(yards: float) -> void:
	dist.text = "%d yds" % roundi(yards)


## `screen_angle`: wind direction relative to the camera (0 = blowing straight away from you).
func set_wind(speed_mps: float, screen_angle: float) -> void:
	wind.text = " %d mph" % roundi(speed_mps * 2.237)
	wind_arrow.rotation = screen_angle
	wind_arrow.visible = speed_mps > 0.3


func set_club(label: String, yards: float) -> void:
	club.text = "%s\n%d yds" % [label, roundi(yards)]


func set_power(p: float, yards: float) -> void:
	power.text = "" if p <= 0.0 else "%d%%\n~%d yds" % [roundi(p * 100), roundi(yards)]


func flash(text: String, seconds := 2.2) -> void:
	message.text = text
	_msg_time = seconds


func show_card(text: String) -> void:
	card_text.text = text
	card.visible = true


func hide_card() -> void:
	card.visible = false


## Cover the cut to a new shot with a short fade from dark.
func fade_in(seconds := 0.35) -> void:
	_fade_t = seconds
	fade.color.a = 1.0


func _process(delta: float) -> void:
	if _fade_t > 0.0:
		_fade_t -= delta
		fade.color.a = clampf(_fade_t / 0.35, 0.0, 1.0)
	if _msg_time > 0.0:
		_msg_time -= delta
		message.modulate.a = clampf(_msg_time * 2.0, 0.0, 1.0)
		if _msg_time <= 0.0:
			message.text = ""
