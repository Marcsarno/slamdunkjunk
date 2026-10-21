class_name PackMenu
extends Control
## Pause menu: gear, haul, Field Journal, save.

signal closed


static func open(parent: Node) -> PackMenu:
	var m := PackMenu.new()
	parent.add_child(m)
	return m


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	theme = Art.theme()
	mouse_filter = Control.MOUSE_FILTER_STOP
	var dim := ColorRect.new()
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	dim.color = Color(0.1, 0.08, 0.05, 0.6)
	add_child(dim)
	var p := PanelContainer.new()
	p.position = Vector2(16, 10)
	p.custom_minimum_size = Vector2(448, 250)
	p.add_theme_stylebox_override("panel", Art.box(Art.PANEL, Art.EDGE, 3, 4, 8))
	add_child(p)
	var cols := HBoxContainer.new()
	cols.add_theme_constant_override("separation", 14)
	p.add_child(cols)

	var left := VBoxContainer.new()
	left.custom_minimum_size = Vector2(180, 0)
	cols.add_child(left)
	left.add_child(_title("PACK"))
	left.add_child(Art.label("$%d    Stamina %d" % [Game.money, Game.stamina], 11))
	var guns := []
	for wid in Game.weapons:
		guns.append(GameData.WEAPONS[wid]["name"] + (" *" if wid == Game.weapon else ""))
	left.add_child(_wrap(", ".join(guns)))
	left.add_child(_wrap("Ammo: %d rifle, %d shells" % [Game.ammo["rifle_ammo"], Game.ammo["shells"]]))
	var calls := []
	for c in Game.calls:
		calls.append(GameData.CALLS[c])
	left.add_child(_wrap("Calls: " + ", ".join(calls)))
	left.add_child(_wrap("Scent x%d   Bear spray x%d" % [Game.items.get("scent", 0), Game.items.get("spray", 0)]))
	left.add_child(_wrap("Aim %d/3   Call %d/3 (refill at the truck)" % [Game.uses["aim"], Game.uses["call"]]))
	if Game.upgrades.size():
		left.add_child(_wrap("Upgrades: " + ", ".join(Game.upgrades.map(func(u): return {"scope": "Scope", "boots": "Quiet Boots"}[u]))))
	left.add_child(_wrap("Haul: %d items, worth $%d" % [Game.inventory.size(), Game.inventory_value()]))
	var save := Button.new()
	save.text = "SAVE GAME"
	save.custom_minimum_size = Vector2(0, 22)
	var saved := Art.label("", 9, Art.HP)
	save.pressed.connect(func():
		Game.save_game()
		saved.text = "Saved.")
	left.add_child(save)
	left.add_child(saved)
	var close := Button.new()
	close.text = "CLOSE"
	close.custom_minimum_size = Vector2(0, 22)
	close.pressed.connect(_close)
	left.add_child(close)

	var right := VBoxContainer.new()
	cols.add_child(right)
	right.add_child(_title("FIELD JOURNAL"))
	var g := GridContainer.new()
	g.columns = 4
	g.add_theme_constant_override("h_separation", 10)
	for h in ["ANIMAL", "SEEN", "TAGGED", "BEST"]:
		g.add_child(Art.label(h, 9, Art.MUTED))
	for sp in GameData.ANIMALS:
		var a: Dictionary = GameData.ANIMALS[sp]
		var j: Dictionary = Game.journal.get(sp, {})
		var known := j.size() > 0
		g.add_child(Art.label(a["name"] if known else "???", 10))
		g.add_child(Art.label(str(j.get("seen", 0)), 10))
		g.add_child(Art.label(str(j.get("harvested", 0)), 10))
		var best: String = j.get("best_grade", "")
		if j.get("best_score", 0) > 0:
			best += " %din" % j["best_score"]
		g.add_child(Art.label(best if best != "" else "-", 10))
	right.add_child(g)
	right.add_child(_wrap("Rarer game: the buck near the ladder stand, the bear in the berry thicket.", 9, 230))
	await get_tree().process_frame
	close.grab_focus()


func _title(t: String) -> Label:
	var l := Label.new()
	l.text = t
	l.add_theme_font_override("font", Art.title_font())
	l.add_theme_font_size_override("font_size", 8)
	l.add_theme_color_override("font_color", Art.BLAZE)
	return l


func _wrap(t: String, size := 10, w := 180) -> Label:
	var l := Art.label(t, size)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size = Vector2(w, 0)
	return l


func _close() -> void:
	closed.emit()
	queue_free()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("menu"):
		_close()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("action"):
		var f := get_viewport().gui_get_focus_owner()
		if f is Button:
			f.pressed.emit()
			get_viewport().set_input_as_handled()
