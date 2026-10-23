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
var aim_map := AimMap.new()
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


## While pulling, the view behind her can't show where the shot comes down, so a small map of the
## hole shows it from above: turned so the aim points up, the ball at the bottom, the target, the
## margin of error and where this pull lands, moving as the pull grows and the aim swings.
class AimMap extends Control:
	var tex: ImageTexture
	var origin := Vector2.ZERO      # course xy of the texture's first pixel
	var m_per_px := 1.0
	var ball := Vector2.ZERO
	var aim := Vector2(0, 1)        # up the map: the line the pull began on, so sliding the aim swings the shot across it
	var shot_dir := Vector2(0, 1)   # where this shot is going
	var land := Vector2.ZERO
	var target := Vector2.ZERO
	var spread := Vector2.ZERO      # half-widths of the margin: across, along
	var span := 200.0               # metres from the ball to the top of the map
	var fill := Color(1.0, 0.62, 0.18)
	var label := ""

	const COLORS := {0: Color8(24, 38, 30), 1: Color8(52, 88, 50), 2: Color8(118, 166, 72), 3: Color8(156, 204, 98),
		4: Color8(228, 210, 160), 6: Color8(138, 186, 84), 7: Color8(104, 150, 66), 8: Color8(36, 62, 40),
		9: Color8(184, 172, 152)}

	## The hole's surfaces as a picture, one pixel per metre.
	func setup(t: Terrain, water: Color) -> void:
		var step := maxi(1, roundi(1.0 / t.surf_cell))
		var w := int(t.snx / step)
		var h := int(t.sny / step)
		var data := PackedByteArray()
		data.resize(w * h * 3)
		var k := 0
		for j in h:
			var row := j * step * t.snx
			for i in w:
				var s := t.surface[row + i * step]
				var c: Color = water if s == 5 else COLORS.get(s, Color8(24, 38, 30))
				data[k] = c.r8
				data[k + 1] = c.g8
				data[k + 2] = c.b8
				k += 3
		tex = ImageTexture.create_from_image(Image.create_from_data(w, h, false, Image.FORMAT_RGB8, data))
		origin = t.origin
		m_per_px = t.surf_cell * step

	func _to_panel(q: Vector2, s: float) -> Vector2:
		var rel := q - ball
		var right := Vector2(aim.y, -aim.x)
		return Vector2(size.x * 0.5 + rel.dot(right) * s, size.y * 0.9 - rel.dot(aim) * s)

	func _draw() -> void:
		if tex == null:
			return
		var s := size.y * 0.8 / maxf(span, 5.0)
		var right := Vector2(aim.y, -aim.x)
		# texture pixel -> course -> panel, as one transform
		var xa := Vector2(right.x, -aim.x) * s * m_per_px
		var ya := Vector2(right.y, -aim.y) * s * m_per_px
		var o := _to_panel(origin, s)
		draw_rect(Rect2(Vector2.ZERO, size), COLORS[0])        # beyond the hole: woods
		draw_set_transform_matrix(Transform2D(xa, ya, o))
		draw_texture(tex, Vector2.ZERO)
		draw_set_transform_matrix(Transform2D.IDENTITY)
		var ink := Color(0.06, 0.02, 0.1)
		var cream := Color(1, 0.94, 0.84)
		var b := _to_panel(ball, s)
		var l := _to_panel(land, s)
		var t := _to_panel(target, s)
		# the line of the shot, dashed
		var d := (l - b)
		var n := int(d.length() / 14.0)
		for i in n:
			if i % 2 == 0:
				draw_line(b + d * (float(i) / n), b + d * (float(i + 1) / n), Color(cream, 0.8), 3.0)
		# the margin of error round where it lands
		if spread.x > 0.2:
			var pts := PackedVector2Array()
			var sr := Vector2(shot_dir.y, -shot_dir.x)
			for i in 33:
				var a := TAU * i / 32.0
				pts.append(_to_panel(land + sr * cos(a) * spread.x + shot_dir * sin(a) * spread.y, s))
			draw_polyline(pts, ink, 5.0, true)
			draw_polyline(pts, Color(1, 1, 1, 0.9), 2.5, true)
		# the target ring, the landing spot, the ball
		draw_arc(t, 9.0, 0, TAU, 24, ink, 6.0)
		draw_arc(t, 9.0, 0, TAU, 24, Color(1.0, 0.8, 0.35), 3.0)
		draw_circle(l, 8.0, ink)
		draw_circle(l, 6.0, fill)
		draw_circle(b, 5.0, ink)
		draw_circle(b, 3.5, Color.WHITE)
		if label != "":
			var font := get_theme_default_font()
			var lp := l + Vector2(12, 8)
			draw_string_outline(font, lp, label, HORIZONTAL_ALIGNMENT_LEFT, -1, 24, 6, ink)
			draw_string(font, lp, label, HORIZONTAL_ALIGNMENT_LEFT, -1, 24, cream)


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

	# the aim map, top left under the bar, in a framed window that clips it
	var frame := PanelContainer.new()
	var fs := _panel_style(16)
	fs.content_margin_left = 4
	fs.content_margin_right = 4
	fs.content_margin_top = 4
	fs.content_margin_bottom = 4
	frame.add_theme_stylebox_override("panel", fs)
	frame.anchor_left = 0.0
	frame.anchor_right = 0.4
	frame.anchor_top = 0.115
	frame.anchor_bottom = 0.45
	frame.offset_left = 16
	frame.mouse_filter = Control.MOUSE_FILTER_IGNORE
	frame.clip_contents = true
	frame.visible = false
	aim_map.mouse_filter = Control.MOUSE_FILTER_IGNORE
	aim_map.clip_contents = true
	frame.add_child(aim_map)
	root.add_child(frame)


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
	aim_map.get_parent().visible = false


func show_aim_map() -> void:
	aim_map.get_parent().visible = true
	aim_map.queue_redraw()


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
			fps.text = "%d fps · slowest frame %d ms · 3D at %d%%" % [Engine.get_frames_per_second(),
				roundi(_fps_worst * 1000.0), roundi(Quality.scale() * 100.0)]
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
