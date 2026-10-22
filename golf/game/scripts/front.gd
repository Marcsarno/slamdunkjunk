extends Control
## The way in: the splash (title art and its PLAY button) and the clubhouse menu, whose blackboard is
## written in chalk. Each picture is laid out in its own pixels (941 x 1672) on a stage scaled to fill
## the screen: the splash centred, the clubhouse kept to its right edge so the whole board stays in view
## on tall phones (the window and golf bag on the left are what gets trimmed).

const ART := Vector2(941, 1672)
const PLAY_RECT := Rect2(150, 1385, 650, 185)     # the PLAY button in the splash art
const BOARD := Rect2(396, 246, 494, 890)          # inside the board's frame, clear of her hand
const CHALK := Color(0.96, 0.95, 0.9)
const CHALK_DIM := Color(0.96, 0.95, 0.9, 0.58)
const CHALK_ORANGE := Color(1.0, 0.72, 0.38)
const HOLES := [
	["Pumpkin Patch", 4], ["Witch's Hollow", 0], ["Forgotten Cemetery", 0], ["Spiderwood", 0],
	["Haunted Harvest", 0], ["Ghostlight Marsh", 0], ["Vampire's Garden", 0], ["Headless Trail", 0],
	["Midnight Homecoming", 0],
]   # par 0: not built yet
const HELP := [
	"Drag the sky to turn your aim.",
	"Pull down anywhere below it to set the power.",
	"Let go to swing.",
	"Tap the club box to change clubs.",
	"Watch the wind arrow up top.",
]

var splash := Control.new()
var clubhouse := Control.new()
var play_art := TextureRect.new()
var list := Control.new()
var help := Control.new()
var title := Label.new()
var fade := ColorRect.new()
var chalk: ShaderMaterial
var head_font: Font = Chalk.head_font()
var hand_font: Font = Chalk.hand_font()
var _t := 0.0
var _busy := false


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--capture=") or a.begins_with("--capture-hole="):
			get_tree().change_scene_to_file.call_deferred("res://scenes/main.tscn")
			return
	set_anchors_preset(Control.PRESET_FULL_RECT)
	Music.set_in_play(false)
	Music.start()
	chalk = Chalk.material()

	_build_splash()
	_build_clubhouse()
	fade.color = Color(0.03, 0.01, 0.05, 1.0)
	fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(fade)
	get_viewport().size_changed.connect(_fit)
	_fit()
	var to_menu: bool = get_tree().has_meta("front_menu") and get_tree().get_meta("front_menu")
	get_tree().set_meta("front_menu", false)
	splash.visible = not to_menu
	clubhouse.visible = to_menu
	create_tween().tween_property(fade, "color:a", 0.0, 0.35)


func _process(delta: float) -> void:
	_t += delta
	play_art.scale = Vector2.ONE * (1.0 + 0.025 * sin(_t * 3.0)) if not _busy else play_art.scale


func _fit() -> void:
	var vp := get_viewport_rect().size
	var s := maxf(vp.x / ART.x, vp.y / ART.y)
	for st in [splash, clubhouse]:
		st.scale = Vector2(s, s)
		st.position.y = (vp.y - ART.y * s) * 0.5
	splash.position.x = (vp.x - ART.x * s) * 0.5
	clubhouse.position.x = vp.x - ART.x * s


# ---------------------------------------------------------------- splash
func _build_splash() -> void:
	splash.size = ART
	add_child(splash)
	var bg := TextureRect.new()
	bg.texture = load("res://assets/ui/splash.png")
	bg.size = ART
	bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	splash.add_child(bg)
	play_art.texture = load("res://assets/ui/splash_play.png")
	play_art.position = PLAY_RECT.position
	play_art.size = PLAY_RECT.size
	play_art.pivot_offset = PLAY_RECT.size * 0.5
	play_art.mouse_filter = Control.MOUSE_FILTER_IGNORE
	splash.add_child(play_art)
	var hit := _invisible_button(PLAY_RECT.grow(20))
	hit.pressed.connect(_on_play)
	splash.add_child(hit)


func _on_play() -> void:
	if _busy:
		return
	_busy = true
	var tw := create_tween()
	tw.tween_property(play_art, "scale", Vector2.ONE * 0.94, 0.08)
	tw.tween_property(play_art, "scale", Vector2.ONE * 1.02, 0.12)
	tw.tween_property(fade, "color:a", 1.0, 0.25)
	tw.tween_callback(func():
		splash.visible = false
		clubhouse.visible = true
		_busy = false)
	tw.tween_property(fade, "color:a", 0.0, 0.3)


# ---------------------------------------------------------------- clubhouse menu, in chalk
func _build_clubhouse() -> void:
	clubhouse.size = ART
	add_child(clubhouse)
	var bg := TextureRect.new()
	bg.texture = load("res://assets/ui/clubhouse.png")
	bg.size = ART
	bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	clubhouse.add_child(bg)
	# old chalk, wiped but never quite gone
	var dust := ColorRect.new()
	dust.color = Color(0.9, 0.88, 0.92, 1.0)
	dust.position = BOARD.position - Vector2(26, 26)
	dust.size = BOARD.size + Vector2(48, 44)
	dust.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var dm := chalk.duplicate()
	dm.set_shader_parameter("dust", 0.09)
	dust.material = dm
	clubhouse.add_child(dust)

	title = _chalk_label("Tonight's Course", head_font, 62, CHALK)
	title.position = Vector2(BOARD.position.x, BOARD.position.y)
	title.size = Vector2(BOARD.size.x, 80)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	clubhouse.add_child(title)
	clubhouse.add_child(_chalk_line(BOARD.position.y + 86, 0.16, 0.84))

	list.size = ART
	list.mouse_filter = Control.MOUSE_FILTER_IGNORE
	clubhouse.add_child(list)
	var y := BOARD.position.y + 118.0
	for i in HOLES.size():
		var hole: Array = HOLES[i]
		var ready_hole: bool = int(hole[1]) > 0
		var row := _invisible_button(Rect2(BOARD.position.x, y, BOARD.size.x, 64))
		list.add_child(row)
		var name := _chalk_label("%d.  %s" % [i + 1, hole[0]], hand_font, 40 if ready_hole else 36, CHALK if ready_hole else CHALK_DIM)
		name.position = Vector2(BOARD.position.x + 14, y + 4)
		name.size = Vector2(BOARD.size.x - 120, 58)
		list.add_child(name)
		var right := _chalk_label("par %d" % hole[1] if ready_hole else "soon", hand_font, 34, CHALK_ORANGE if ready_hole else CHALK_DIM)
		right.position = Vector2(BOARD.end.x - 118, y + 8)
		right.size = Vector2(104, 52)
		right.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		list.add_child(right)
		if ready_hole:
			row.pressed.connect(_play_hole.bind(row, name))
		else:
			row.pressed.connect(_soon.bind(name, right))
		y += 72.0
	list.add_child(_chalk_line(y + 6, 0.08, 0.92))
	var half := BOARD.size.x * 0.5
	var how := _invisible_button(Rect2(BOARD.position.x, y + 22, half, 64))
	list.add_child(how)
	var how_l := _chalk_label("How to play ?", hand_font, 36, CHALK)
	how_l.position = Vector2(BOARD.position.x, y + 26)
	how_l.size = Vector2(half, 58)
	how_l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	list.add_child(how_l)
	how.pressed.connect(_show_help.bind(true))
	var mus := _invisible_button(Rect2(BOARD.position.x + half, y + 22, half, 64))
	list.add_child(mus)
	var mus_l := _chalk_label(_music_text(), hand_font, 36, CHALK)
	mus_l.position = Vector2(BOARD.position.x + half, y + 26)
	mus_l.size = Vector2(half, 58)
	mus_l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	list.add_child(mus_l)
	mus.pressed.connect(func():
		Music.toggle()
		mus_l.text = _music_text())

	help.size = ART
	help.visible = false
	help.mouse_filter = Control.MOUSE_FILTER_IGNORE
	clubhouse.add_child(help)
	var tips := VBoxContainer.new()
	tips.position = Vector2(BOARD.position.x + 14, BOARD.position.y + 130)
	tips.size = Vector2(BOARD.size.x - 28, 0)
	tips.add_theme_constant_override("separation", 34)
	tips.mouse_filter = Control.MOUSE_FILTER_IGNORE
	help.add_child(tips)
	for line in HELP:
		var l := _chalk_label(line, hand_font, 38, CHALK)
		l.custom_minimum_size.x = BOARD.size.x - 28
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		tips.add_child(l)
	var back := _invisible_button(Rect2(BOARD.position.x, BOARD.end.y - 90, BOARD.size.x, 70))
	help.add_child(back)
	var back_l := _chalk_label("<  back to the course", hand_font, 38, CHALK_ORANGE)
	back_l.position = Vector2(BOARD.position.x, BOARD.end.y - 84)
	back_l.size = Vector2(BOARD.size.x, 58)
	back_l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	help.add_child(back_l)
	back.pressed.connect(_show_help.bind(false))


func _show_help(on: bool) -> void:
	var tw := create_tween()
	var out: Control = list if on else help
	var into: Control = help if on else list
	tw.tween_property(out, "modulate:a", 0.0, 0.15)
	tw.parallel().tween_property(title, "modulate:a", 0.0, 0.15)
	tw.tween_callback(func():
		title.text = "How to Play" if on else "Tonight's Course"
		out.visible = false
		into.modulate.a = 0.0
		into.visible = true)
	tw.tween_property(into, "modulate:a", 1.0, 0.2)
	tw.parallel().tween_property(title, "modulate:a", 1.0, 0.2)


## A hole that isn't built yet: its "soon" lights up orange for a moment and the name wiggles.
func _soon(label: Label, tag: Label) -> void:
	tag.add_theme_color_override("font_color", CHALK_ORANGE)
	create_tween().tween_callback(func(): tag.add_theme_color_override("font_color", CHALK_DIM)).set_delay(1.2)
	var tw := create_tween()
	tw.tween_property(label, "position:x", label.position.x + 8, 0.05)
	tw.tween_property(label, "position:x", label.position.x - 6, 0.07)
	tw.tween_property(label, "position:x", label.position.x, 0.05)


func _play_hole(_row: Button, label: Label) -> void:
	if _busy:
		return
	_busy = true
	label.add_theme_color_override("font_color", CHALK_ORANGE)
	var tw := create_tween()
	tw.tween_interval(0.15)
	tw.tween_property(fade, "color:a", 1.0, 0.3)
	tw.tween_callback(func(): get_tree().change_scene_to_file("res://scenes/main.tscn"))


func _music_text() -> String:
	return "Music: on" if Music.on else "Music: off"


# ---------------------------------------------------------------- helpers
func _chalk_label(text: String, font: Font, size: int, color: Color) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_override("font", font)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.material = chalk
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


## A hand-drawn chalk rule across the board at art height y, from share a to b of its width.
func _chalk_line(y: float, a: float, b: float) -> Line2D:
	var line := Line2D.new()
	line.width = 4.0
	line.default_color = Color(CHALK, 0.8)
	line.begin_cap_mode = Line2D.LINE_CAP_ROUND
	line.end_cap_mode = Line2D.LINE_CAP_ROUND
	line.material = chalk
	var n := 12
	for i in n + 1:
		var u := lerpf(a, b, float(i) / n)
		line.add_point(Vector2(BOARD.position.x + BOARD.size.x * u, y + 2.0 * sin(u * 9.0 + y) + 1.2 * sin(u * 23.0)))
	return line


func _invisible_button(r: Rect2) -> Button:
	var b := Button.new()
	b.flat = true
	b.focus_mode = Control.FOCUS_NONE
	b.position = r.position
	b.size = r.size
	for s in ["normal", "hover", "pressed", "focus", "disabled", "hover_pressed"]:
		b.add_theme_stylebox_override(s, StyleBoxEmpty.new())
	return b
