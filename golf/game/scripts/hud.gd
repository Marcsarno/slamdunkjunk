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
var gauge := Gauge.new()
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


## The power gauge shown while pulling, in yards (feet for putts): filled to where this pull carries,
## with the target marked. Pulling to the mark lands on the target (it turns mint there); past it is
## extra power at a risk (red); a fainter stretch shows the roll once the finger holds still.
class Gauge extends Control:
	const TRACK_W := 22.0
	const TOP := 34.0
	const BOTTOM := 26.0
	var value := 0.0      # this pull's carry, in the gauge's units
	var finish := -1.0    # where it stops after rolling; < 0 while not worked out yet
	var mark := 1.0       # the target's distance: a full (100%) pull
	var top_value := 1.0  # the top of the scale: the most power a pull can add
	var unit := "yds"
	var warning := ""     # e.g. "into the water": where the preview shot ends up, if it's trouble

	func show_shot(v: float, finish_v: float, mark_v: float, top: float, unit_name: String, warn := "") -> void:
		value = v
		finish = finish_v
		mark = mark_v
		top_value = maxf(top, 1.0)
		unit = unit_name
		warning = warn
		visible = true
		queue_redraw()

	func _y(v: float) -> float:
		return lerpf(size.y - BOTTOM, TOP, clampf(v / top_value, 0.0, 1.0))

	func _draw() -> void:
		var font := get_theme_default_font()
		var ink := Color(0.06, 0.02, 0.1)
		var cream := Color(1, 0.94, 0.84)
		var tx := size.x - TRACK_W - 40.0   # room on the right for the target mark
		var y0 := size.y - BOTTOM
		var my := _y(mark)
		# the track, red-tinted above the mark where power is risky
		draw_rect(Rect2(tx - 6, TOP - 6, TRACK_W + 12, y0 - TOP + 12), Color(0.16, 0.08, 0.24, 0.78))
		draw_rect(Rect2(tx, TOP, TRACK_W, y0 - TOP), Color(0.05, 0.02, 0.09, 0.9))
		draw_rect(Rect2(tx, TOP, TRACK_W, my - TOP), Color(0.55, 0.08, 0.12, 0.55))
		var fy := _y(value)
		# a tick every 10/25/50 units (whichever gives a handful), labelled on the left except behind the tag
		var step := 50.0
		for st in [5.0, 10.0, 25.0, 50.0]:
			if top_value / st <= 8.0:
				step = st
				break
		var v := step
		while v < top_value:
			var ty := _y(v)
			draw_line(Vector2(tx - 10, ty), Vector2(tx + TRACK_W, ty), Color(cream, 0.55), 2.0)
			if absf(ty - fy) > 40.0 and absf(ty - my) > 16.0:
				var t := "%d" % roundi(v)
				var tw := font.get_string_size(t, HORIZONTAL_ALIGNMENT_LEFT, -1, 22).x
				draw_string_outline(font, Vector2(tx - 16 - tw, ty + 8), t, HORIZONTAL_ALIGNMENT_LEFT, -1, 22, 6, ink)
				draw_string(font, Vector2(tx - 16 - tw, ty + 8), t, HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Color(cream, 0.8))
			v += step
		# the fill: orange short of the mark, mint on it, red past it
		var on_mark := absf(value - mark) <= maxf(mark * 0.015, 0.3)
		var fill := Color(0.45, 1.0, 0.7) if on_mark else (Color(1.0, 0.32, 0.28) if value > mark else Color(1.0, 0.62, 0.18))
		draw_rect(Rect2(tx, fy, TRACK_W, y0 - fy), Color(fill, 0.9))
		if finish > value:
			var ry := _y(finish)
			draw_rect(Rect2(tx, ry, TRACK_W, fy - ry), Color(fill, 0.38))
		# the target mark: a line across the track and a ring beside it
		var px := tx + TRACK_W
		draw_line(Vector2(tx - 6, my), Vector2(px + 6, my), ink, 8.0)
		draw_line(Vector2(tx - 4, my), Vector2(px + 4, my), Color.WHITE, 4.0)
		var c := Vector2(px + 20, my)
		draw_arc(c, 11, 0, TAU, 24, ink, 7.0)
		draw_arc(c, 11, 0, TAU, 24, Color(1.0, 0.8, 0.4), 3.5)
		draw_circle(c, 3.5, Color(1.0, 0.8, 0.4))
		# this pull's distance, in a tag at the top of the fill
		var big := "%d" % roundi(value)
		var bw := font.get_string_size(big, HORIZONTAL_ALIGNMENT_LEFT, -1, 46).x
		var uw := font.get_string_size(unit, HORIZONTAL_ALIGNMENT_LEFT, -1, 22).x
		var note := warning
		if note == "":
			note = "on target" if on_mark else ("too far!" if value > mark else "")
			if finish > value + 0.5:
				note = ("on target · " if on_mark else "") + "rolls to %d" % roundi(finish)
		var rw := font.get_string_size(note, HORIZONTAL_ALIGNMENT_LEFT, -1, 20).x
		var tag_w := maxf(bw + uw + 30, rw + 24)
		var tag := Rect2(tx - 28 - tag_w, fy - 30, tag_w, 56 + (24 if note != "" else 0))
		var sb := StyleBoxFlat.new()
		sb.bg_color = Color(0.16, 0.08, 0.24, 0.92)
		sb.border_color = fill
		sb.set_border_width_all(3)
		sb.set_corner_radius_all(12)
		draw_style_box(sb, tag)
		draw_line(Vector2(tag.end.x, fy), Vector2(tx + TRACK_W, fy), cream, 4.0)
		draw_string(font, Vector2(tag.position.x + 12, fy + 16), big, HORIZONTAL_ALIGNMENT_LEFT, -1, 46, cream)
		draw_string(font, Vector2(tag.position.x + 18 + bw, fy + 15), unit, HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Color(cream, 0.8))
		if note != "":
			var note_col := Color(1.0, 0.45, 0.4) if (warning != "" or value > mark and not on_mark) else Color(cream, 0.8)
			draw_string(font, Vector2(tag.position.x + 12, fy + 41), note, HORIZONTAL_ALIGNMENT_LEFT, -1, 20, note_col)


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

	# down the right edge, between the top bar and the club box
	gauge.anchor_left = 1.0
	gauge.anchor_right = 1.0
	gauge.anchor_top = 0.27
	gauge.anchor_bottom = 0.78
	gauge.offset_left = -250
	gauge.offset_right = -8
	gauge.mouse_filter = Control.MOUSE_FILTER_IGNORE
	gauge.visible = false
	root.add_child(gauge)


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
	hint.position = Vector2(-340, -300)
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


func hide_gauge() -> void:
	gauge.visible = false


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
