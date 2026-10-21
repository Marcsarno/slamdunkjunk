class_name Hud
extends CanvasLayer
## Overworld readout: money, unsold haul, wind, sneaking.

var money := Label.new()
var haul := Label.new()
var wind := Label.new()
var wind_icon := TextureRect.new()
var sneak := Label.new()
var banner := Label.new()
var show_wind := false


func _ready() -> void:
	layer = 5
	var top := PanelContainer.new()
	top.theme = Art.theme()
	top.position = Vector2(4, 4)
	top.add_theme_stylebox_override("panel", Art.box(Color(0.96, 0.92, 0.84, 0.92), Art.EDGE, 1, 3, 3))
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	top.add_child(row)
	for l in [money, haul, wind]:
		l.add_theme_font_size_override("font_size", 11)
		l.add_theme_color_override("font_color", Art.INK)
		row.add_child(l)
	wind_icon.stretch_mode = TextureRect.STRETCH_KEEP_CENTERED
	wind_icon.custom_minimum_size = Vector2(11, 11)
	row.add_child(wind_icon)
	add_child(top)
	sneak.text = "SNEAKING"
	sneak.add_theme_font_override("font", Art.title_font())
	sneak.add_theme_font_size_override("font_size", 8)
	sneak.add_theme_color_override("font_color", Art.PANEL)
	sneak.add_theme_color_override("font_outline_color", Art.INK)
	sneak.add_theme_constant_override("outline_size", 3)
	sneak.position = Vector2(8, 26)
	sneak.visible = false
	add_child(sneak)
	banner.add_theme_font_override("font", Art.title_font())
	banner.add_theme_font_size_override("font_size", 16)
	banner.add_theme_color_override("font_color", Art.PANEL)
	banner.add_theme_color_override("font_outline_color", Art.INK)
	banner.add_theme_constant_override("outline_size", 5)
	banner.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	banner.size = Vector2(480, 24)
	banner.position = Vector2(0, 60)
	banner.modulate.a = 0.0
	add_child(banner)
	Game.changed.connect(refresh)
	refresh()


func refresh() -> void:
	money.text = "$%d" % Game.money
	var n := Game.inventory.size()
	haul.text = "HAUL %d ($%d)" % [n, Game.inventory_value()] if n else "HAUL 0"
	wind.text = "WIND"
	wind.visible = show_wind
	wind_icon.visible = show_wind
	wind_icon.texture = Art.arrow(Game.wind)


func set_sneaking(on: bool) -> void:
	sneak.visible = on


func announce(text: String) -> void:
	banner.text = text
	var tw := create_tween()
	tw.tween_property(banner, "modulate:a", 1.0, 0.3)
	tw.tween_interval(1.4)
	tw.tween_property(banner, "modulate:a", 0.0, 0.5)
