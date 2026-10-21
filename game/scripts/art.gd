class_name Art
## Shared look: palette, fonts, the UI theme and small generated textures.

const INK := Color("2a1c16")
const PANEL := Color("f6ecd6")
const PANEL_DK := Color("e9d8b4")
const EDGE := Color("6b4a30")
const BLAZE := Color("ff7417")
const HP := Color("5fae4a")
const SPOOK := Color("e0662a")
const NERVE := Color("4f8ac9")
const MUTED := Color("7b5d40")
const GOLD := Color("e8c547")
const NIGHT := Color("23271d")

static var _font: FontFile
static var _title_font: FontFile
static var _theme: Theme
static var _cache := {}


static func font() -> FontFile:
	if _font == null:
		_font = _load_font("res://assets/fonts/PixelifySans.ttf")
	return _font


static func title_font() -> FontFile:
	if _title_font == null:
		_title_font = _load_font("res://assets/fonts/Silkscreen-Regular.ttf")
	return _title_font


static func _load_font(path: String) -> FontFile:
	# Fonts are imported resources; the raw .ttf is not in the exported pack.
	# Text renders at screen resolution (stretch mode canvas_items), so keep
	# normal smoothing; the pixel art itself still scales with nearest filtering.
	var f: FontFile = load(path)
	f.hinting = TextServer.HINTING_LIGHT
	return f


static func box(bg := PANEL, edge := EDGE, border := 2, radius := 3, pad := 4) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg
	s.border_color = edge
	s.set_border_width_all(border)
	s.set_corner_radius_all(radius)
	s.set_content_margin_all(pad)
	s.anti_aliasing = false
	return s


static func theme() -> Theme:
	if _theme:
		return _theme
	var t := Theme.new()
	t.default_font = font()
	t.default_font_size = 11
	t.set_color("font_color", "Label", INK)
	t.set_stylebox("panel", "PanelContainer", box())
	t.set_stylebox("panel", "Panel", box())
	for state in ["normal", "hover", "pressed", "focus", "disabled"]:
		var bg := PANEL
		var edge := EDGE
		match state:
			"hover": bg = PANEL_DK
			"pressed": bg = Color("e2c38f")
			"focus": edge = BLAZE
			"disabled": bg = Color("d8ccb3")
		var s := box(bg, edge, 2, 3, 3)
		if state == "focus":
			s.draw_center = false
		t.set_stylebox(state, "Button", s)
	t.set_color("font_color", "Button", INK)
	t.set_color("font_hover_color", "Button", INK)
	t.set_color("font_pressed_color", "Button", INK)
	t.set_color("font_focus_color", "Button", INK)
	t.set_color("font_disabled_color", "Button", Color("9a8a70"))
	t.set_font_size("font_size", "Button", 11)
	var bar_bg := box(Color("4a3b30"), Color("4a3b30"), 0, 2, 0)
	t.set_stylebox("background", "ProgressBar", bar_bg)
	t.set_constant("separation", "VBoxContainer", 2)
	t.set_constant("separation", "HBoxContainer", 4)
	_theme = t
	return t


static func label(text: String, size := 11, color := INK) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	return l


static func bar(color: Color, w := 100, h := 6) -> ProgressBar:
	var b := ProgressBar.new()
	b.custom_minimum_size = Vector2(w, h)
	b.show_percentage = false
	b.max_value = 100
	b.add_theme_stylebox_override("fill", box(color, color, 0, 2, 0))
	return b


## Soft oval shadow under characters.
static func shadow(w: int, h: int) -> ImageTexture:
	var key := "shadow%dx%d" % [w, h]
	if _cache.has(key):
		return _cache[key]
	var img := Image.create(w, h, false, Image.FORMAT_RGBA8)
	for y in h:
		for x in w:
			var nx := (x + 0.5 - w / 2.0) / (w / 2.0)
			var ny := (y + 0.5 - h / 2.0) / (h / 2.0)
			if nx * nx + ny * ny <= 1.0:
				img.set_pixel(x, y, Color(0.1, 0.08, 0.05, 0.35))
	var tex := ImageTexture.create_from_image(img)
	_cache[key] = tex
	return tex


## Pixel-art circle button face for the touch controls, with an arrow or letter.
static func touch_button(size: int, glyph: String, pressed := false) -> ImageTexture:
	var key := "tb%d%s%s" % [size, glyph, pressed]
	if _cache.has(key):
		return _cache[key]
	var img := Image.create(size, size, false, Image.FORMAT_RGBA8)
	var r := size / 2.0
	var fill := Color(0.96, 0.92, 0.84, 0.55 if not pressed else 0.85)
	var edge := Color(0.16, 0.11, 0.09, 0.7)
	for y in size:
		for x in size:
			var d := Vector2(x + 0.5 - r, y + 0.5 - r).length()
			if d <= r - 1.5:
				img.set_pixel(x, y, fill)
			elif d <= r:
				img.set_pixel(x, y, edge)
	var c := edge
	var m := int(r)
	var s := int(size * 0.18)
	match glyph:
		"up", "down", "left", "right":
			for i in s:
				for j in range(-i, i + 1):
					var p := Vector2i(j, i - s / 2)
					match glyph:
						"down": p = Vector2i(j, s / 2 - i)
						"left": p = Vector2i(i - s / 2, j)
						"right": p = Vector2i(s / 2 - i, j)
					img.set_pixel(m + p.x, m + p.y, c)
	var tex := ImageTexture.create_from_image(img)
	_cache[key] = tex
	return tex


## Small arrow pointing where the wind blows (where Chris's scent goes).
static func arrow(dir: Vector2i) -> ImageTexture:
	var key := "arrow%s" % dir
	if _cache.has(key):
		return _cache[key]
	var img := Image.create(11, 11, false, Image.FORMAT_RGBA8)
	var pts := []
	for i in 9:
		pts.append(Vector2i(1 + i, 5))          # shaft, pointing right
	for i in 4:
		pts.append(Vector2i(9 - i, 5 - i))
		pts.append(Vector2i(9 - i, 5 + i))
	for p in pts:
		var q: Vector2i = p
		match dir:
			Vector2i.LEFT: q = Vector2i(10 - p.x, p.y)
			Vector2i.UP: q = Vector2i(p.y, 10 - p.x)
			Vector2i.DOWN: q = Vector2i(p.y, p.x)
		img.set_pixel(q.x, q.y, BLAZE.darkened(0.2))
	var tex := ImageTexture.create_from_image(img)
	_cache[key] = tex
	return tex
