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
	["Pumpkin Patch", 4], ["Witch's Hollow", 3], ["Forgotten Cemetery", 5], ["Spiderwood", 4],
	["Haunted Harvest", 5], ["Ghostlight Marsh", 3], ["Vampire's Garden", 4], ["Headless Trail", 4],
	["Midnight Homecoming", 4],
]   # par 0: not built yet (the built ones are Round.HOLES, in the same order)
const HELP := [
	"Drag the top of the screen to move the gold ring: across to aim, up for longer.",
	"Pull down from the bottom like a slingshot, to the gauge's mark.",
	"Pull to the right to send it left, to the left to send it right.",
	"The white circle: where it may land.",
	"Wind blows a shot to the mint ring: aim off.",
	"On the green the beads run downhill: aim above the hole.",
]
## The slingshot balls, in a turntable on the bar: the one you play with sits big in the middle with
## its neighbours either side; tap one (or swipe) to turn it.
const BALL_MID := Vector2(668, 1326)      # the middle ball's foot, on the bar
const BALL_STEP := 150.0                  # from one ball to the next
const BALL_BIG := 138.0                   # the middle ball's height ...
const BALL_SMALL := 82.0                  # ... and its neighbours'
const BALL_GLOW := {"pumpkin": Color(1.0, 0.55, 0.15), "ghost": Color(0.62, 0.55, 1.0), "skull": Color(0.62, 0.55, 1.0),
	"mummy": Color(1.0, 0.8, 0.45), "vampire": Color(0.85, 0.2, 0.35), "frank": Color(0.45, 1.0, 0.45),
	"bat": Color(0.75, 0.35, 1.0)}

var splash := Control.new()
var clubhouse := Control.new()
var play_art := TextureRect.new()
var fade := ColorRect.new()
var chalk: ShaderMaterial
var head_font: Font = Chalk.head_font()
var hand_font: Font = Chalk.hand_font()
var _t := 0.0
var _busy := false
var _ball_pics: Array[TextureRect] = []   # in Balls.BALLS order
var _ball_glow := TextureRect.new()
var _ball_name := Label.new()
var _ball_i := maxi(0, Balls.BALLS.find(Balls.chosen()))
var _spin := float(_ball_i)                 # where the turntable is, easing toward _ball_i
var _press_x := 0.0


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
	_turn_balls(delta)


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
		_show_page("main")
		_busy = false)
	tw.tween_property(fade, "color:a", 0.0, 0.3)


# ---------------------------------------------------------------- clubhouse menu, in chalk
## The board shows one page at a time: the main page (Play Now, Pick a Hole, Pick your Ball, Options,
## How to Play) and one for each of those. Going to another page, a felt eraser sweeps the board (and
## leaves a smudge of dust), then the new page is chalked on line by line.
var _pages := {}                 # name -> Control
var _items := {}                 # name -> Array of chalk CanvasItems, in the order they're written
var _page := ""
var _dust: ColorRect
var _eraser := Control.new()
var _ball_ring: Line2D
var _board_balls: Array[TextureRect] = []
var _board_ball_name: Label


func _build_clubhouse() -> void:
	clubhouse.size = ART
	add_child(clubhouse)
	var bg := TextureRect.new()
	bg.texture = load("res://assets/ui/clubhouse.png")
	bg.size = ART
	bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	clubhouse.add_child(bg)
	# old chalk, wiped but never quite gone
	_dust = ColorRect.new()
	_dust.color = Color(0.9, 0.88, 0.92, 1.0)
	_dust.position = BOARD.position - Vector2(26, 26)
	_dust.size = BOARD.size + Vector2(48, 44)
	_dust.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var dm := chalk.duplicate()
	dm.set_shader_parameter("dust", 0.09)
	_dust.material = dm
	clubhouse.add_child(_dust)

	var x0 := BOARD.position.x
	var w := BOARD.size.x
	var top := BOARD.position.y
	# the main page
	var m := _new_page("main")
	_write(m, "The Clubhouse", head_font, 60, CHALK, Rect2(x0, top + 6, w, 80))
	_rule(m, top + 92, 0.16, 0.84)
	_write(m, "Play Now", head_font, 80, CHALK_ORANGE, Rect2(x0, top + 140, w, 104))
	_write(m, "nine holes, from the first tee", hand_font, 30, CHALK_DIM, Rect2(x0, top + 244, w, 44))
	_tap(m, Rect2(x0, top + 132, w, 160), _play_round)
	_rule(m, top + 318, 0.3, 0.7)
	var y := top + 360.0
	for row: Array in [["Pick a Hole", "holes"], ["Pick your Ball", "balls"], ["Options", "options"], ["How to Play", "help"]]:
		_write(m, row[0], hand_font, 50, CHALK, Rect2(x0, y, w, 70))
		_tap(m, Rect2(x0, y - 4, w, 78), _go.bind(row[1]))
		y += 96.0

	# pick a hole
	var hp := _new_page("holes")
	_write(hp, "Pick a Hole", head_font, 60, CHALK, Rect2(x0, top + 6, w, 80))
	_rule(hp, top + 92, 0.16, 0.84)
	y = top + 116.0
	for i in HOLES.size():
		var hole: Array = HOLES[i]
		var built: bool = i < Round.HOLES.size()
		var name := _write(hp, "%d.  %s" % [i + 1, hole[0]], hand_font, 40 if built else 36, CHALK if built else CHALK_DIM,
			Rect2(x0 + 14, y + 4, w - 120, 58), HORIZONTAL_ALIGNMENT_LEFT)
		var right := _write(hp, "par %d" % hole[1] if built else "soon", hand_font, 34, CHALK_ORANGE if built else CHALK_DIM,
			Rect2(BOARD.end.x - 118, y + 8, 104, 52), HORIZONTAL_ALIGNMENT_RIGHT)
		if built:
			_tap(hp, Rect2(x0, y, w, 64), _play_hole.bind(i, name))
		else:
			_tap(hp, Rect2(x0, y, w, 64), _soon.bind(name, right))
		y += 70.0
	_back(hp)

	# pick your ball: the seven on the board, the one you play with ringed in chalk
	var bp := _new_page("balls")
	_write(bp, "Pick your Ball", head_font, 60, CHALK, Rect2(x0, top + 6, w, 80))
	_rule(bp, top + 92, 0.16, 0.84)
	var cx := x0 + w * 0.5
	for k in Balls.BALLS.size():
		var row := 0 if k < 4 else 1
		var col := k if k < 4 else k - 4
		var c := Vector2(cx + (col - (1.5 if row == 0 else 1.0)) * 116.0, top + 230 + row * 150)
		var pic := TextureRect.new()
		pic.texture = load("res://assets/balls/%s/still.png" % Balls.BALLS[k])
		pic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		pic.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
		pic.size = Vector2.ONE * 104.0
		pic.position = c - pic.size * 0.5
		pic.mouse_filter = Control.MOUSE_FILTER_IGNORE
		bp.add_child(pic)
		_items["balls"].append(pic)
		_board_balls.append(pic)
		_tap(bp, Rect2(c - Vector2(58, 64), Vector2(116, 128)), func(): _pick_ball(k))
	_ball_ring = _rule(bp, 0.0, 0.0, 0.0)
	_board_ball_name = _write(bp, "", head_font, 58, CHALK_ORANGE, Rect2(x0, top + 470, w, 80))
	_write(bp, "or turn them on the bar", hand_font, 30, CHALK_DIM, Rect2(x0, top + 560, w, 44))
	_back(bp)

	# options
	var op := _new_page("options")
	_write(op, "Options", head_font, 60, CHALK, Rect2(x0, top + 6, w, 80))
	_rule(op, top + 92, 0.16, 0.84)
	y = top + 150.0
	for opt: String in ["music", "sounds", "vibration", "graphics"]:
		var l := _write(op, _option_text(opt), hand_font, 48, CHALK, Rect2(x0, y, w, 70))
		_tap(op, Rect2(x0, y - 4, w, 78), _toggle_option.bind(opt, l))
		y += 100.0
	_write(op, "graphics: auto picks what runs smoothly", hand_font, 28, CHALK_DIM, Rect2(x0, y + 10, w, 44))
	_back(op)

	# how to play
	var help_p := _new_page("help")
	_write(help_p, "How to Play", head_font, 60, CHALK, Rect2(x0, top + 6, w, 80))
	_rule(help_p, top + 92, 0.16, 0.84)
	y = top + 124.0
	for line: String in HELP:
		var tip := _write(help_p, line, hand_font, 36, CHALK, Rect2(x0 + 14, y, w - 28, 50), HORIZONTAL_ALIGNMENT_LEFT, true)
		y += maxf(tip.get_combined_minimum_size().y, 50.0) + 30.0
	_back(help_p)

	_build_eraser()
	_show_page("main")
	_board_ball_ring()

	# the slingshot balls' turntable on the bar
	_ball_glow.texture = _glow_texture()
	_ball_glow.size = Vector2.ONE * BALL_BIG * 1.9
	_ball_glow.position = BALL_MID - Vector2(0, BALL_BIG * 0.5) - _ball_glow.size * 0.5
	_ball_glow.mouse_filter = Control.MOUSE_FILTER_IGNORE
	clubhouse.add_child(_ball_glow)
	for n: String in Balls.BALLS:
		var pic := TextureRect.new()
		pic.texture = load("res://assets/balls/%s/still.png" % n)
		pic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		pic.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
		pic.mouse_filter = Control.MOUSE_FILTER_IGNORE
		clubhouse.add_child(pic)
		_ball_pics.append(pic)
	var touch := Control.new()      # taps and swipes on the bar
	touch.position = Vector2(BALL_MID.x - BALL_STEP * 1.6, BALL_MID.y - BALL_BIG - 20)
	touch.size = Vector2(BALL_STEP * 3.2, BALL_BIG + 130)
	touch.gui_input.connect(_bar_input.bind(touch))
	clubhouse.add_child(touch)
	_ball_name = _chalk_label("", hand_font, 40, CHALK_ORANGE)
	_ball_name.material = null
	_ball_name.add_theme_color_override("font_outline_color", Color(0.08, 0.03, 0.1))
	_ball_name.add_theme_constant_override("outline_size", 10)
	_ball_name.position = Vector2(BALL_MID.x - 220, 1372)
	_ball_name.size = Vector2(440, 60)
	_ball_name.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_ball_name.mouse_filter = Control.MOUSE_FILTER_IGNORE
	clubhouse.add_child(_ball_name)
	_name_ball()
	_turn_balls(0.0)


## Turn the turntable toward the picked ball: each ball's place, size and fade from how far round it is.
func _turn_balls(delta: float) -> void:
	var n := Balls.BALLS.size()
	if n == 0 or _ball_pics.is_empty():
		return
	var to := float(_ball_i)
	var gap := wrapf(to - _spin, -n * 0.5, n * 0.5)
	_spin = to if absf(gap) < 0.002 else _spin + gap * (1.0 - exp(-delta * 12.0))
	for k in n:
		var pic := _ball_pics[k]
		var o := wrapf(k - _spin, -n * 0.5, n * 0.5)
		var near := clampf(1.0 - absf(o), 0.0, 1.0)
		var h := lerpf(BALL_SMALL, BALL_BIG, near)
		var bob := sin(_t * 2.6) * 5.0 - 5.0 if absf(o) < 0.05 else 0.0
		pic.size = Vector2.ONE * h / Balls.ART_FILL
		pic.position = Vector2(BALL_MID.x + o * BALL_STEP, BALL_MID.y - h * 0.5 + bob) - pic.size * 0.5
		var fade := clampf(1.9 - absf(o), 0.0, 1.0)
		var dim := lerpf(0.8, 1.0, near)
		pic.modulate = Color(dim, dim * 0.95, dim * 1.02, fade)
		pic.z_index = 1 if absf(o) < 0.5 else 0
	var g: Color = BALL_GLOW.get(Balls.BALLS[_ball_i], Color(1.0, 0.6, 0.3))
	_ball_glow.self_modulate = Color(g, 0.7 + 0.2 * sin(_t * 2.6))


func _name_ball() -> void:
	_ball_name.text = "<   %s   >" % Balls.NAMES.get(Balls.BALLS[_ball_i], "")


## A swipe turns it by one; a tap on a ball to either side brings that one round.
func _bar_input(e: InputEvent, touch: Control) -> void:
	if not (e is InputEventMouseButton and e.button_index == MOUSE_BUTTON_LEFT):
		return
	if e.pressed:
		_press_x = e.position.x
		return
	var dx: float = e.position.x - _press_x
	var mid := touch.size.x * 0.5
	if absf(dx) > 30.0:
		_pick_ball(_ball_i - int(signf(dx)))
	elif e.position.x < mid - BALL_BIG * 0.5:
		_pick_ball(_ball_i - 1)
	elif e.position.x > mid + BALL_BIG * 0.5:
		_pick_ball(_ball_i + 1)


func _pick_ball(i: int) -> void:
	var n := Balls.BALLS.size()
	var k := posmod(i, n)
	if k == _ball_i:
		return
	_ball_i = k
	Balls.choose(Balls.BALLS[k])
	Sfx.play("click", -4.0)
	_name_ball()
	_board_ball_ring()


## A soft round glow, white, to tint.
func _glow_texture() -> ImageTexture:
	var n := 128
	var img := Image.create(n, n, false, Image.FORMAT_RGBA8)
	for y in n:
		for x in n:
			var d := Vector2(x - n * 0.5 + 0.5, y - n * 0.5 + 0.5).length() / (n * 0.5)
			img.set_pixel(x, y, Color(1, 1, 1, pow(clampf(1.0 - d, 0.0, 1.0), 2.0) * 0.8))
	return ImageTexture.create_from_image(img)


## Change the board's page: wipe it, then chalk the new one on.
func _go(name: String) -> void:
	if _busy or name == _page:
		return
	_busy = true
	Sfx.play("click", -8.0)
	await _erase_board()
	_show_page(name)
	_busy = false


func _show_page(name: String) -> void:
	for n: String in _pages:
		_pages[n].visible = n == name
	_page = name
	_write_on(name)


## The felt eraser's sweep, side to side down the board while working across it; each line goes as it
## passes, and a cloud of dust is left behind that settles back.
func _erase_board() -> void:
	Sfx.play("erase", -6.0, randf_range(0.95, 1.05))
	_eraser.visible = true
	var items: Array = _items.get(_page, [])
	var span := Vector2(BOARD.position.x - 70.0, BOARD.end.x + 70.0)
	var sweep := func(u: float) -> void:
		var x := lerpf(span.x, span.y, u)
		_eraser.position = Vector2(x - 60.0, BOARD.position.y + BOARD.size.y * (0.48 + 0.36 * sin(u * TAU * 2.5)) - 24.0)
		for it: CanvasItem in items:
			if it is TextureRect:
				var tr := it as TextureRect
				tr.modulate.a = minf(tr.modulate.a, clampf((tr.position.x + tr.size.x - (x - 40.0)) / tr.size.x, 0.0, 1.0))
			elif it.material:
				(it.material as ShaderMaterial).set_shader_parameter("erase_x", x - _item_x(it) - 20.0)
		(_dust.material as ShaderMaterial).set_shader_parameter("dust", lerpf(0.09, 0.17, u))
	var tw := create_tween()
	tw.tween_method(sweep, 0.0, 1.0, 0.5)
	await tw.finished
	_eraser.visible = false
	var settle := create_tween()
	settle.tween_method(func(v: float): (_dust.material as ShaderMaterial).set_shader_parameter("dust", v), 0.17, 0.09, 1.6)


## Chalk a page on: each line written left to right in turn (overlapping a little), with the scratch of
## the chalk; the balls appear as their turn comes.
func _write_on(name: String) -> void:
	var items: Array = _items.get(name, [])
	var at := 0.0
	var k := 0
	for it: CanvasItem in items:
		if it is TextureRect:
			it.modulate.a = 0.0
			create_tween().tween_property(it, "modulate:a", 1.0, 0.18).set_delay(at)
			at += 0.05
			continue
		var mat := it.material as ShaderMaterial
		var ext: Vector2 = it.get_meta("ext", Vector2(0, 400))
		mat.set_shader_parameter("erase_x", -100000.0)
		mat.set_shader_parameter("write_x", ext.x - 20.0)
		var dur := clampf((ext.y - ext.x) / 1500.0, 0.08, 0.38)
		var tw := create_tween()
		tw.tween_interval(at)
		if k % 2 == 0:
			tw.tween_callback(func(): Sfx.play("chalk", -9.0, randf_range(0.9, 1.15)))
		tw.tween_method(func(v: float): mat.set_shader_parameter("write_x", v), ext.x - 20.0, ext.y + 30.0, dur)
		at += dur * 0.35 + 0.025
		k += 1


## Rub out one line and chalk it again (an option changing its value).
func _rewrite(l: Label, text: String) -> void:
	var mat := l.material as ShaderMaterial
	var ext: Vector2 = l.get_meta("ext")
	var tw := create_tween()
	tw.tween_method(func(v: float): mat.set_shader_parameter("erase_x", v), ext.x - 30.0, ext.y + 40.0, 0.18)
	tw.tween_callback(func():
		l.text = text
		_measure(l)
		var e: Vector2 = l.get_meta("ext")
		mat.set_shader_parameter("erase_x", -100000.0)
		mat.set_shader_parameter("write_x", e.x - 20.0)
		Sfx.play("chalk", -9.0, randf_range(0.95, 1.1)))
	tw.tween_method(func(v: float): mat.set_shader_parameter("write_x", v), ext.x - 20.0, ext.y + 60.0, 0.3)


func _build_eraser() -> void:
	# a wooden-backed felt board eraser
	_eraser.size = Vector2(120, 48)
	_eraser.pivot_offset = _eraser.size * 0.5
	_eraser.rotation = -0.12
	_eraser.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var wood := Panel.new()
	var ws := StyleBoxFlat.new()
	ws.bg_color = Color(0.55, 0.34, 0.18)
	ws.set_corner_radius_all(10)
	ws.border_color = Color(0.36, 0.2, 0.1)
	ws.set_border_width_all(2)
	wood.add_theme_stylebox_override("panel", ws)
	wood.size = Vector2(120, 30)
	wood.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_eraser.add_child(wood)
	var felt := Panel.new()
	var fs := StyleBoxFlat.new()
	fs.bg_color = Color(0.72, 0.7, 0.68)
	fs.corner_radius_bottom_left = 6
	fs.corner_radius_bottom_right = 6
	felt.add_theme_stylebox_override("panel", fs)
	felt.position = Vector2(3, 28)
	felt.size = Vector2(114, 18)
	felt.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_eraser.add_child(felt)
	_eraser.visible = false
	_eraser.z_index = 5
	clubhouse.add_child(_eraser)


## The chalk ring round the ball you play with on the Pick your Ball page, and its name under them.
func _board_ball_ring() -> void:
	if _ball_ring == null or _board_balls.is_empty():
		return
	var pic := _board_balls[_ball_i]
	var c := pic.position + pic.size * 0.5
	_ball_ring.clear_points()
	var n := 28
	for i in n + 2:
		var a := TAU * float(i) / n - 0.4
		var r := 62.0 + 3.0 * sin(i * 1.7)
		_ball_ring.add_point(c + Vector2(cos(a) * r, sin(a) * r * 0.95))
	var ext := Vector2(c.x - 70.0, c.x + 70.0)
	_ball_ring.set_meta("ext", ext)
	var rm := _ball_ring.material as ShaderMaterial
	rm.set_shader_parameter("erase_x", -100000.0)
	if _page == "balls":
		# drawn round the new one with a quick stroke of chalk
		create_tween().tween_method(func(v: float): rm.set_shader_parameter("write_x", v), ext.x - 20.0, ext.y + 30.0, 0.22)
	for k in _board_balls.size():
		_board_balls[k].self_modulate = Color(1, 1, 1) if k == _ball_i else Color(0.78, 0.76, 0.82)
	if _board_ball_name:
		var t := Balls.NAMES.get(Balls.BALLS[_ball_i], "") as String
		if _board_ball_name.text == "":
			_board_ball_name.text = t
			_measure(_board_ball_name)
		elif _board_ball_name.text != t and _page == "balls":
			_rewrite(_board_ball_name, t)
		else:
			_board_ball_name.text = t
			_measure(_board_ball_name)


func _play_round() -> void:
	if _busy:
		return
	_busy = true
	Round.start(0)
	var tw := create_tween()
	tw.tween_interval(0.12)
	tw.tween_property(fade, "color:a", 1.0, 0.3)
	tw.tween_callback(func(): get_tree().change_scene_to_file("res://scenes/main.tscn"))


func _option_text(opt: String) -> String:
	match opt:
		"music": return "Music: " + ("on" if Music.on else "off")
		"sounds": return "Sounds: " + ("on" if Sfx.on else "off")
		"vibration": return "Vibration: " + ("on" if Sfx.buzz_on else "off")
		"graphics": return "Graphics: " + Quality.mode
	return opt


func _toggle_option(opt: String, l: Label) -> void:
	match opt:
		"music": Music.toggle()
		"sounds": Sfx.set_sounds(not Sfx.on)
		"vibration":
			Sfx.set_buzz(not Sfx.buzz_on)
			Sfx.buzz(30)
		"graphics":
			var order := ["auto", "sharp", "smooth"]
			Quality.set_mode(order[(order.find(Quality.mode) + 1) % order.size()])
	Sfx.play("click", -6.0)
	_rewrite(l, _option_text(opt))


## A hole that isn't built yet: its "soon" lights up orange for a moment and the name wiggles.
func _soon(label: Label, tag: Label) -> void:
	tag.add_theme_color_override("font_color", CHALK_ORANGE)
	create_tween().tween_callback(func(): tag.add_theme_color_override("font_color", CHALK_DIM)).set_delay(1.2)
	var tw := create_tween()
	tw.tween_property(label, "position:x", label.position.x + 8, 0.05)
	tw.tween_property(label, "position:x", label.position.x - 6, 0.07)
	tw.tween_property(label, "position:x", label.position.x, 0.05)


func _play_hole(i: int, label: Label) -> void:
	if _busy:
		return
	_busy = true
	Round.start(i)
	label.add_theme_color_override("font_color", CHALK_ORANGE)
	var tw := create_tween()
	tw.tween_interval(0.15)
	tw.tween_property(fade, "color:a", 1.0, 0.3)
	tw.tween_callback(func(): get_tree().change_scene_to_file("res://scenes/main.tscn"))


# ---------------------------------------------------------------- helpers
func _new_page(name: String) -> Control:
	var p := Control.new()
	p.size = ART
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	p.visible = false
	clubhouse.add_child(p)
	_pages[name] = p
	_items[name] = []
	return p


## A line of chalk on a page, in its own copy of the chalk material (so it can be written and wiped on
## its own), remembered in the page's writing order.
func _write(page: Control, text: String, font: Font, size: int, color: Color, r: Rect2,
		align := HORIZONTAL_ALIGNMENT_CENTER, wrap := false) -> Label:
	var l := _chalk_label(text, font, size, color)
	l.material = chalk.duplicate()
	if wrap:
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		l.custom_minimum_size.x = r.size.x
	l.position = r.position
	l.size = r.size
	l.horizontal_alignment = align
	page.add_child(l)
	_measure(l)
	_items[_pages.find_key(page)].append(l)
	return l


## Where a label's words run along its x (its own units), for the chalk to be written along them.
func _measure(l: Label) -> void:
	var font: Font = l.get_theme_font("font")
	var fs := l.get_theme_font_size("font_size")
	var tw := minf(font.get_string_size(l.text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x, l.size.x)
	var x0 := 0.0
	if l.horizontal_alignment == HORIZONTAL_ALIGNMENT_CENTER:
		x0 = (l.size.x - tw) * 0.5
	elif l.horizontal_alignment == HORIZONTAL_ALIGNMENT_RIGHT:
		x0 = l.size.x - tw
	if l.autowrap_mode != TextServer.AUTOWRAP_OFF:
		x0 = 0.0
		tw = l.size.x
	l.set_meta("ext", Vector2(x0, x0 + tw))


## Where an item's own x starts on the board (a label's left edge; a line's points are board coords).
func _item_x(it: CanvasItem) -> float:
	return (it as Control).position.x if it is Control else 0.0


func _rule(page: Control, y: float, a: float, b: float) -> Line2D:
	var line := _chalk_line(y, a, b)
	line.material = chalk.duplicate()
	line.set_meta("ext", Vector2(BOARD.position.x + BOARD.size.x * a, BOARD.position.x + BOARD.size.x * b))
	page.add_child(line)
	_items[_pages.find_key(page)].append(line)
	return line


func _tap(page: Control, r: Rect2, f: Callable) -> void:
	var b := _invisible_button(r)
	b.pressed.connect(f)
	page.add_child(b)


func _back(page: Control) -> void:
	_write(page, "<  back", hand_font, 40, CHALK_ORANGE, Rect2(BOARD.position.x, BOARD.end.y - 84, BOARD.size.x, 58))
	_tap(page, Rect2(BOARD.position.x, BOARD.end.y - 92, BOARD.size.x, 72), _go.bind("main"))


func _chalk_label(text: String, font: Font, size: int, color: Color) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_override("font", font)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	Chalk.dust(l, color)
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
