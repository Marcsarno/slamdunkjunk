class_name BattleScene
extends Control
## The encounter screen. Draws the backdrop, the animal and Chris, the two
## status panels and the action buttons, and plays out BattleRules events.

signal finished(outcome: String, rules: BattleRules)

const FOE_AT := Vector2(340, 131)

var rules := BattleRules.new()
var foe := Sprite2D.new()
var chris := Sprite2D.new()
var flash := ColorRect.new()
var msg := Label.new()
var grid := GridContainer.new()
var foe_name := Label.new()
var foe_rarity := Label.new()
var vit_bar := Art.bar(Art.HP, 120, 6)
var spook_bar := Art.bar(Art.SPOOK, 120, 6)
var stam_bar := Art.bar(Art.HP, 124, 6)
var nerve_bar := Art.bar(Art.NERVE, 124, 6)
var range_lbl := Label.new()
var foe_status := Label.new()
var me_status := Label.new()
var busy := false
var in_bag := false
var skip := false
var bob := 0.0
var sfx := AudioStreamPlayer.new()


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	theme = Art.theme()
	var bg := TextureRect.new()
	bg.texture = load("res://assets/battle/backdrop_hollow.png")
	add_child(bg)

	foe.centered = false
	foe.hframes = 4
	add_child(foe)
	chris.texture = load("res://assets/battle/chris_back.png")
	chris.centered = false
	chris.position = Vector2(26, 194 - chris.texture.get_height())
	add_child(chris)

	# animal panel
	var fp := _panel(Vector2(8, 8), Vector2(186, 0))
	var v := VBoxContainer.new()
	fp.add_child(v)
	var top := HBoxContainer.new()
	foe_name.add_theme_font_size_override("font_size", 12)
	foe_name.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	foe_rarity.add_theme_font_size_override("font_size", 9)
	foe_rarity.add_theme_color_override("font_color", Art.MUTED)
	top.add_child(foe_name)
	top.add_child(foe_rarity)
	v.add_child(top)
	v.add_child(_bar_row("VITAL", vit_bar))
	v.add_child(_bar_row("SPOOK", spook_bar))
	foe_status.add_theme_font_size_override("font_size", 9)
	foe_status.add_theme_color_override("font_color", Art.SPOOK)
	v.add_child(foe_status)

	# Chris panel
	var mp := _panel(Vector2(282, 128), Vector2(190, 0))
	var mv := VBoxContainer.new()
	mp.add_child(mv)
	var mtop := HBoxContainer.new()
	var nm := Art.label("CHRIS", 12)
	nm.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	range_lbl.add_theme_font_size_override("font_size", 10)
	range_lbl.add_theme_color_override("font_color", Art.BLAZE)
	mtop.add_child(nm)
	mtop.add_child(range_lbl)
	mv.add_child(mtop)
	mv.add_child(_bar_row("STAMINA", stam_bar))
	mv.add_child(_bar_row("NERVE", nerve_bar))
	me_status.add_theme_font_size_override("font_size", 9)
	me_status.add_theme_color_override("font_color", Art.NERVE)
	mv.add_child(me_status)

	# bottom panel
	var bottom := Panel.new()
	bottom.position = Vector2(0, 194)
	bottom.size = Vector2(480, 76)
	bottom.add_theme_stylebox_override("panel", Art.box(Art.PANEL, Art.EDGE, 3, 0, 0))
	add_child(bottom)
	msg.position = Vector2(10, 200)
	msg.size = Vector2(176, 64)
	msg.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	msg.add_theme_font_size_override("font_size", 11)
	add_child(msg)
	var sep := ColorRect.new()
	sep.color = Art.EDGE
	sep.position = Vector2(192, 194)
	sep.size = Vector2(3, 76)
	add_child(sep)
	grid.columns = 4
	grid.position = Vector2(199, 199)
	grid.add_theme_constant_override("h_separation", 3)
	grid.add_theme_constant_override("v_separation", 3)
	add_child(grid)

	flash.set_anchors_preset(Control.PRESET_FULL_RECT)
	flash.color = Color(1, 1, 1, 0)
	flash.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(flash)
	add_child(sfx)


func _panel(at: Vector2, min_size: Vector2) -> PanelContainer:
	var p := PanelContainer.new()
	p.position = at
	p.custom_minimum_size = min_size
	p.add_theme_stylebox_override("panel", Art.box(Art.PANEL, Art.EDGE, 2, 4, 5))
	add_child(p)
	return p


func _bar_row(text: String, bar: ProgressBar) -> HBoxContainer:
	var row := HBoxContainer.new()
	var l := Art.label(text, 9, Art.MUTED)
	l.custom_minimum_size = Vector2(50, 0)
	row.add_child(l)
	bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	row.add_child(bar)
	return row


# ---------------------------------------------------------------- flow ----
func begin(species: String, opts: Dictionary) -> void:
	rules.start(species, Game.loadout(), opts)
	Game.mark_seen(species)
	var tex: Texture2D = load("res://assets/battle/%s.png" % species)
	foe.texture = tex
	foe.frame = 1
	foe.position = FOE_AT - Vector2(tex.get_width() / 8.0, tex.get_height())
	foe_name.text = rules.a["name"].to_upper()
	foe_rarity.text = rules.a["rarity"].to_upper()
	refresh()
	_buttons(false)
	busy = true
	var intro := "A %s! " % rules.a["name"].to_upper()
	if opts.get("range", 1) == BattleRules.LONG:
		intro += "It already spotted Chris."
	elif opts.get("range", 1) == BattleRules.CLOSE:
		intro += "Chris slipped in close without a sound."
	else:
		intro += "It hasn't noticed Chris yet."
	intro += " The wind is %s." % ("in Chris's favor" if rules.downwind else "carrying Chris's scent to it")
	await _type(intro)
	busy = false
	_buttons(true)


func refresh() -> void:
	vit_bar.value = 100.0 * rules.vit / rules.vit_max
	spook_bar.value = rules.spook
	stam_bar.value = rules.stamina
	nerve_bar.value = rules.nerve
	range_lbl.text = GameData.RANGE_NAMES[rules.range_i] + " RANGE"
	var fs := []
	if rules.telegraph != "":
		fs.append("ABOUT TO ATTACK!")
	if rules.evasion_bonus > 0:
		fs.append("EVADING")
	if rules.roosted > 0:
		fs.append("ROOSTED")
	if rules.wounded:
		fs.append("WOUNDED")
	foe_status.text = "  ".join(fs)
	var ms := []
	if rules.aim_acc > 0:
		ms.append("AIMED")
	if rules.counter_bonus > 0:
		ms.append("COUNTER")
	if rules.scent_turns > 0:
		ms.append("SCENT %d" % rules.scent_turns)
	ms.append(GameData.WEAPONS[rules.weapon_id()]["short"])
	me_status.text = "  ".join(ms)


func _buttons(enabled: bool) -> void:
	for c in grid.get_children():
		grid.remove_child(c)
		c.queue_free()
	var list := rules.bag_actions() if in_bag else rules.actions()
	if in_bag:
		list.append({"id": "back", "label": "BACK", "sub": "", "on": true})
	var first: Button = null
	for a in list:
		var b := Button.new()
		b.custom_minimum_size = Vector2(66, 32)
		b.text = a["label"] + ("\n" + a["sub"] if a["sub"] != "" else "")
		b.add_theme_font_size_override("font_size", 9)
		b.disabled = not (enabled and a["on"])
		b.focus_mode = Control.FOCUS_ALL
		b.pressed.connect(_on_action.bind(a["id"]))
		grid.add_child(b)
		if first == null and not b.disabled:
			first = b
	if first and enabled:
		first.grab_focus()


func _on_action(id: String) -> void:
	if busy:
		return
	if id == "bag":
		in_bag = true
		_buttons(true)
		return
	if id == "back":
		in_bag = false
		_buttons(true)
		return
	in_bag = false
	busy = true
	_buttons(false)
	var events := rules.act(id)
	for e in events:
		await _fx(e["fx"])
		await _type(e["text"])
		refresh()
	refresh()
	if rules.outcome != "":
		await _finish()
		return
	busy = false
	_buttons(true)


func _type(text: String) -> void:
	msg.text = text
	msg.visible_ratio = 0.0
	skip = false
	var t := 0.0
	var dur := clampf(text.length() * 0.016, 0.1, 0.9)
	while t < dur and not skip:
		await get_tree().process_frame
		t += get_process_delta_time()
		msg.visible_ratio = t / dur
	msg.visible_ratio = 1.0
	skip = false
	var hold := 0.0
	while hold < 0.85 and not skip:
		await get_tree().process_frame
		hold += get_process_delta_time()
	skip = false


func _gui_input(event: InputEvent) -> void:
	if busy and event is InputEventMouseButton and event.pressed:
		skip = true


func _unhandled_input(event: InputEvent) -> void:
	if busy and (event.is_action_pressed("action") or event.is_action_pressed("ui_accept")):
		skip = true
		get_viewport().set_input_as_handled()
	elif not busy and event.is_action_pressed("action"):
		var f := get_viewport().gui_get_focus_owner()
		if f is Button and not f.disabled:
			f.pressed.emit()
			get_viewport().set_input_as_handled()


func _process(delta: float) -> void:
	bob += delta
	if foe.texture and rules.outcome == "":
		foe.offset.y = -1.0 if int(bob * 2.0) % 2 == 0 else 0.0


# ----------------------------------------------------------------- fx ----
func _fx(kind: String) -> void:
	match kind:
		"hit", "vital", "miss":
			_gunshot()
			flash.color = Color(1, 0.95, 0.8, 0.7)
			var tw := create_tween()
			tw.tween_property(flash, "color:a", 0.0, 0.12)
			await tw.finished
			if kind != "miss":
				foe.modulate = Color(3, 3, 3)
				await _shake(foe, 4 if kind == "vital" else 2, 0.25)
				foe.modulate = Color.WHITE
				_popup("VITAL!" if kind == "vital" else "HIT", Art.SPOOK)
			else:
				_popup("MISS", Art.MUTED)
		"telegraph":
			for i in 3:
				foe.modulate = Color(1.6, 0.6, 0.5)
				await get_tree().create_timer(0.08).timeout
				foe.modulate = Color.WHITE
				await get_tree().create_timer(0.08).timeout
		"hurt", "stumble":
			flash.color = Color(0.8, 0.1, 0.05, 0.45)
			var tw2 := create_tween()
			tw2.tween_property(flash, "color:a", 0.0, 0.3)
			await _shake(self, 4, 0.3)
		"braced", "bluff":
			await _shake(self, 2, 0.2)
		"flee":
			foe.flip_h = true
			var tw3 := create_tween()
			tw3.tween_property(foe, "position:x", 520.0, 0.7)
			for i in 6:
				foe.frame = i % 4
				await get_tree().create_timer(0.11).timeout
			await tw3.finished
		"harvest":
			var tw4 := create_tween()
			tw4.tween_property(foe, "modulate", Color(0.55, 0.5, 0.45, 0.9), 0.5)
			await tw4.finished
		"aim":
			_popup("+AIM", Art.NERVE)
		"spray":
			flash.color = Color(1, 0.6, 0.2, 0.5)
			var tw5 := create_tween()
			tw5.tween_property(flash, "color:a", 0.0, 0.5)


func _shake(node: CanvasItem, amount: int, dur: float) -> void:
	var start: Vector2 = node.position
	var t := 0.0
	while t < dur:
		node.position = start + Vector2(randi_range(-amount, amount), randi_range(-amount, amount))
		await get_tree().create_timer(0.03).timeout
		t += 0.03
	node.position = start


func _popup(text: String, color: Color) -> void:
	var l := Label.new()
	l.text = text
	l.add_theme_font_override("font", Art.title_font())
	l.add_theme_font_size_override("font_size", 16)
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_outline_color", Art.INK)
	l.add_theme_constant_override("outline_size", 4)
	l.position = FOE_AT + Vector2(-30, -110)
	add_child(l)
	var tw := create_tween()
	tw.tween_property(l, "position:y", l.position.y - 14, 0.6)
	tw.parallel().tween_property(l, "modulate:a", 0.0, 0.6).set_delay(0.3)
	tw.tween_callback(l.queue_free)


## A short noise burst with a fast decay. Generated, so no audio files.
func _gunshot() -> void:
	var rate := 22050
	var n := int(rate * 0.35)
	var data := PackedByteArray()
	data.resize(n * 2)
	var lp := 0.0
	for i in n:
		var t := float(i) / n
		var env := exp(-t * 9.0)
		lp = lp * 0.55 + randf_range(-1.0, 1.0) * 0.45
		var s := int(clampf(lp * env * 1.6, -1.0, 1.0) * 32000)
		data.encode_s16(i * 2, s)
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_16_BITS
	wav.mix_rate = rate
	wav.data = data
	sfx.stream = wav
	sfx.volume_db = -6.0
	sfx.play()


# -------------------------------------------------------------- result ----
func _finish() -> void:
	busy = true
	_buttons(false)
	Game.after_battle(rules.loadout)
	if rules.outcome == "harvest":
		var done := Game.add_harvest(rules.species, rules.result)
		await _result_panel(done)
	finished.emit(rules.outcome, rules)


func _result_panel(done: Array) -> void:
	var dim := ColorRect.new()
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	dim.color = Color(0.1, 0.08, 0.05, 0.55)
	add_child(dim)
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", Art.box(Art.PANEL, Art.EDGE, 3, 4, 10))
	p.position = Vector2(110, 24)
	p.custom_minimum_size = Vector2(260, 0)
	add_child(p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 4)
	p.add_child(v)
	var head := HBoxContainer.new()
	var t := Label.new()
	t.text = "TAGGED: " + rules.a["name"].to_upper()
	t.add_theme_font_override("font", Art.title_font())
	t.add_theme_font_size_override("font_size", 8)
	t.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	head.add_child(t)
	var g := Label.new()
	g.text = "GRADE " + rules.result["grade"]
	g.add_theme_font_override("font", Art.title_font())
	g.add_theme_font_size_override("font_size", 16)
	g.add_theme_color_override("font_color", {"A": Art.HP, "B": Art.GOLD, "C": Art.SPOOK}[rules.result["grade"]])
	head.add_child(g)
	v.add_child(head)
	var shots := Art.label("%d shot%s, %d hit%s" % [rules.shots, "" if rules.shots == 1 else "s",
		rules.hits, "" if rules.hits == 1 else "s"], 10, Art.MUTED)
	v.add_child(shots)
	for d in rules.result["drops"]:
		var row := HBoxContainer.new()
		var n := Art.label(d["name"], 11)
		n.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(n)
		row.add_child(Art.label("$%d" % d["value"], 11))
		v.add_child(row)
	for note in rules.result["notes"]:
		var l := Art.label(note, 10, Art.SPOOK)
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		l.custom_minimum_size = Vector2(240, 0)
		v.add_child(l)
	if rules.result["grade"] != "A":
		var tip := Art.label("Tip: a clean kill (no misses, finished with a vital hit) grades A and sells for 1.5x.", 9, Art.MUTED)
		tip.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		tip.custom_minimum_size = Vector2(240, 0)
		v.add_child(tip)
	for title in done:
		v.add_child(Art.label("Request complete: %s. See the Warden." % title, 10, Art.NERVE))
	v.add_child(Art.label("Sell your haul at the Trading Post in Pinecrest.", 9, Art.MUTED))
	var ok := Button.new()
	ok.text = "CONTINUE"
	ok.custom_minimum_size = Vector2(0, 24)
	v.add_child(ok)
	ok.grab_focus()
	busy = false
	await ok.pressed
	busy = true
