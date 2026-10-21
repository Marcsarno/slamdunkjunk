class_name ShopPanel
extends Control
## Town building screens: trading_post, outfitter, warden, cabin.

signal closed

const TITLES := {
	"trading_post": "TRADING POST", "outfitter": "OUTFITTER",
	"warden": "GAME WARDEN", "cabin": "CHRIS'S CABIN",
}

var kind := ""
var body := VBoxContainer.new()
var money := Label.new()
var status := Label.new()
var desc := Label.new()


static func open(parent: Node, p_kind: String) -> ShopPanel:
	var s := ShopPanel.new()
	s.kind = p_kind
	parent.add_child(s)
	return s


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	theme = Art.theme()
	mouse_filter = Control.MOUSE_FILTER_STOP
	var dim := ColorRect.new()
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	dim.color = Color(0.1, 0.08, 0.05, 0.6)
	add_child(dim)
	var p := PanelContainer.new()
	p.position = Vector2(24, 12)
	p.custom_minimum_size = Vector2(432, 246)
	p.add_theme_stylebox_override("panel", Art.box(Art.PANEL, Art.EDGE, 3, 4, 8))
	add_child(p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 5)
	p.add_child(v)
	var head := HBoxContainer.new()
	var t := Label.new()
	t.text = TITLES[kind]
	t.add_theme_font_override("font", Art.title_font())
	t.add_theme_font_size_override("font_size", 16)
	t.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(t)
	money.add_theme_font_size_override("font_size", 12)
	head.add_child(money)
	v.add_child(head)
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.add_theme_constant_override("separation", 3)
	v.add_child(body)
	status.add_theme_font_size_override("font_size", 10)
	status.add_theme_color_override("font_color", Art.BLAZE)
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	status.custom_minimum_size = Vector2(416, 0)
	v.add_child(status)
	var leave := Button.new()
	leave.text = "LEAVE"
	leave.custom_minimum_size = Vector2(0, 22)
	leave.pressed.connect(_close)
	v.add_child(leave)
	rebuild()


func _close() -> void:
	Game.save_game()
	closed.emit()
	queue_free()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("menu"):
		_close()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("action"):
		var f := get_viewport().gui_get_focus_owner()
		if f is Button and not f.disabled:
			f.pressed.emit()
			get_viewport().set_input_as_handled()


func rebuild() -> void:
	money.text = "$%d" % Game.money
	for c in body.get_children():
		body.remove_child(c)
		c.queue_free()
	match kind:
		"trading_post": _trading_post()
		"outfitter": _outfitter()
		"warden": _warden()
		"cabin": _cabin()
	await get_tree().process_frame
	for c in _all_buttons(self):
		if not c.disabled:
			c.grab_focus()
			break


func _all_buttons(n: Node) -> Array:
	var out := []
	for c in n.get_children():
		if c is Button:
			out.append(c)
		out.append_array(_all_buttons(c))
	return out


func _line(text: String, size := 11, color := Art.INK) -> Label:
	var l := Art.label(text, size, color)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size = Vector2(416, 0)
	body.add_child(l)
	return l


# ------------------------------------------------------------ shops ----
func _trading_post() -> void:
	if Game.inventory.is_empty():
		_line("\"Nothing to sell? Meat, hides and antlers. Bring 'em in.\"", 11, Art.MUTED)
		_line("Clean kills grade A and pay 1.5x. Messy ones grade C and pay 0.6x.", 10, Art.MUTED)
		return
	var grid := GridContainer.new()
	grid.columns = 3
	grid.add_theme_constant_override("h_separation", 14)
	for d in Game.inventory:
		grid.add_child(Art.label(d["name"], 11))
		grid.add_child(Art.label("grade " + d["grade"], 10, Art.MUTED))
		grid.add_child(Art.label("$%d" % d["value"], 11))
	var sc := ScrollContainer.new()
	sc.custom_minimum_size = Vector2(416, 120)
	sc.add_child(grid)
	body.add_child(sc)
	var sell := Button.new()
	sell.text = "SELL ALL FOR $%d" % Game.inventory_value()
	sell.custom_minimum_size = Vector2(0, 24)
	sell.pressed.connect(func():
		var got := Game.sell_all()
		status.text = "Sold for $%d. Spend it at the Outfitter next door." % got
		rebuild())
	body.add_child(sell)


func _outfitter() -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	body.add_child(row)
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(236, 168)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	row.add_child(scroll)
	var list := VBoxContainer.new()
	list.add_theme_constant_override("separation", 2)
	scroll.add_child(list)
	desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	desc.custom_minimum_size = Vector2(176, 0)
	desc.size_flags_vertical = Control.SIZE_EXPAND_FILL
	desc.add_theme_font_size_override("font_size", 10)
	row.add_child(desc)
	for e in GameData.SHOP:
		var b := Button.new()
		var owned: bool = e["kind"] in ["weapon", "call", "upgrade"] and Game.owns(e["id"])
		b.text = "%s  %s" % [e["name"], "OWNED" if owned else "$%d" % e["price"]]
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.custom_minimum_size = Vector2(228, 17)
		b.add_theme_font_size_override("font_size", 10)
		for st in ["normal", "hover", "pressed", "focus", "disabled"]:
			var sb: StyleBoxFlat = Art.theme().get_stylebox(st, "Button").duplicate()
			sb.content_margin_top = 1
			sb.content_margin_bottom = 1
			b.add_theme_stylebox_override(st, sb)
		b.disabled = owned
		b.focus_entered.connect(func(): desc.text = _describe(e))
		b.mouse_entered.connect(func(): desc.text = _describe(e))
		b.pressed.connect(func():
			var err := Game.buy(e)
			status.text = err if err != "" else "Bought: %s." % e["name"]
			money.text = "$%d" % Game.money
			if err == "" and e["kind"] in ["weapon", "call", "upgrade"]:
				b.text = "%s  OWNED" % e["name"]
				b.disabled = true
			desc.text = _describe(e))
		list.add_child(b)
	desc.text = _describe(GameData.SHOP[0])


func _describe(e: Dictionary) -> String:
	var have := ""
	match e["id"]:
		"rifle_ammo": have = "You have %d rounds." % Game.ammo["rifle_ammo"]
		"shells": have = "You have %d shells." % Game.ammo["shells"]
		"scent": have = "You have %d." % Game.items.get("scent", 0)
		"spray": have = "You have %d." % Game.items.get("spray", 0)
	return "%s\n\n%s" % [e["desc"], have]


func _warden() -> void:
	for r in GameData.REQUESTS:
		var st: Dictionary = Game.requests[r["id"]]
		if not Game.request_available(r):
			continue
		var row := HBoxContainer.new()
		var v := VBoxContainer.new()
		v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		v.add_child(Art.label("%s  ($%d)" % [r["title"], r["reward"]], 11))
		var t := Art.label(r["text"], 9, Art.MUTED)
		t.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		t.custom_minimum_size = Vector2(320, 0)
		v.add_child(t)
		row.add_child(v)
		var b := Button.new()
		b.custom_minimum_size = Vector2(86, 22)
		b.add_theme_font_size_override("font_size", 10)
		match st["state"]:
			"open":
				b.text = "ACCEPT"
				b.pressed.connect(func():
					Game.accept_request(r["id"])
					status.text = "Accepted: %s." % r["title"]
					rebuild())
			"active":
				b.text = "%d / %d" % [st["progress"], r["count"]]
				b.disabled = true
			"ready":
				b.text = "TURN IN"
				b.pressed.connect(func():
					var pay := Game.turn_in_request(r["id"])
					status.text = "\"Good work.\" The Warden pays $%d." % pay
					rebuild())
			"done":
				b.text = "DONE"
				b.disabled = true
		row.add_child(b)
		body.add_child(row)
	var seen := 0
	var got := 0
	for sp in Game.journal:
		seen += 1
		if Game.journal[sp]["harvested"] > 0:
			got += 1
	_line("Field Journal: %d of %d Maple Hollow species seen, %d harvested. (Open your PACK to read it.)" % [seen, GameData.ANIMALS.size(), got], 9, Art.MUTED)


func _cabin() -> void:
	_line("A woodstove, a cot, and a wall waiting for trophies.", 11, Art.MUTED)
	_line("Stamina %d / %d" % [Game.stamina, GameData.MAX_STAMINA], 11)
	var b := Button.new()
	b.text = "REST AND SAVE"
	b.custom_minimum_size = Vector2(0, 24)
	b.pressed.connect(func():
		Game.rest()
		Game.save_game()
		status.text = "Chris sleeps until dawn. Stamina and abilities restored. Game saved."
		rebuild())
	body.add_child(b)
