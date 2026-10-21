extends Node
## Top-level flow: title -> town <-> Maple Hollow, encounters, shops, menus.
##
## Debug starts (for automated play-tests), via URL query on web or
## `-- debug=...` on the command line:
##   debug=hollow | debug=town | debug=battle&species=black_bear | debug=shop&id=outfitter

const AREA_NAMES := {"town": "PINECREST", "hollow": "MAPLE HOLLOW"}

var ui := CanvasLayer.new()
var top := CanvasLayer.new()
var fade := ColorRect.new()
var hud := Hud.new()
var touch := TouchControls.new()
var ow: Overworld = null
var mode := "title"
var title: Control = null


func _ready() -> void:
	ui.layer = 10
	add_child(ui)
	add_child(hud)
	add_child(touch)
	top.layer = 30
	add_child(top)
	fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	fade.color = Color(Art.NIGHT, 0.0)
	fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	top.add_child(fade)
	hud.visible = false
	touch.set_shown(false)
	var dbg := _debug_args()
	if dbg.has("debug"):
		await _debug_start(dbg)
	else:
		_show_title()


# ---------------------------------------------------------------- title ----
func _show_title() -> void:
	mode = "title"
	title = Control.new()
	title.set_anchors_preset(Control.PRESET_FULL_RECT)
	title.theme = Art.theme()
	ui.add_child(title)
	var bg := TextureRect.new()
	bg.texture = load("res://assets/battle/backdrop_hollow.png")
	title.add_child(bg)
	var buck := Sprite2D.new()
	buck.texture = load("res://assets/battle/whitetail_buck.png")
	buck.hframes = 4
	buck.frame = 1
	buck.centered = false
	buck.position = Vector2(300, 131 - buck.texture.get_height())
	title.add_child(buck)
	var me := Sprite2D.new()
	me.texture = load("res://assets/battle/chris_back.png")
	me.centered = false
	me.position = Vector2(26, 270 - me.texture.get_height())
	title.add_child(me)
	var t := Label.new()
	t.text = "HOLLOW RIDGE"
	t.add_theme_font_override("font", Art.title_font())
	t.add_theme_font_size_override("font_size", 32)
	t.add_theme_color_override("font_color", Art.BLAZE)
	t.add_theme_color_override("font_outline_color", Art.INK)
	t.add_theme_constant_override("outline_size", 8)
	t.position = Vector2(20, 10)
	title.add_child(t)
	var sub := Label.new()
	sub.text = "CHRIS'S FIRST SEASON"
	sub.add_theme_font_override("font", Art.title_font())
	sub.add_theme_font_size_override("font_size", 8)
	sub.add_theme_color_override("font_color", Art.PANEL)
	sub.add_theme_color_override("font_outline_color", Art.INK)
	sub.add_theme_constant_override("outline_size", 4)
	sub.position = Vector2(24, 50)
	title.add_child(sub)
	var box := VBoxContainer.new()
	box.position = Vector2(330, 170)
	box.custom_minimum_size = Vector2(130, 0)
	box.add_theme_constant_override("separation", 4)
	title.add_child(box)
	if Game.has_save():
		var cont := Button.new()
		cont.text = "CONTINUE"
		cont.custom_minimum_size = Vector2(0, 26)
		cont.pressed.connect(_continue)
		box.add_child(cont)
	var ng := Button.new()
	ng.text = "NEW GAME"
	ng.custom_minimum_size = Vector2(0, 26)
	ng.pressed.connect(_new_game)
	box.add_child(ng)
	var help := Art.label("Move: arrows/WASD   A: Z/Enter   Sneak: hold X   Pack: Esc", 9, Art.PANEL)
	help.add_theme_color_override("font_outline_color", Art.INK)
	help.add_theme_constant_override("outline_size", 3)
	help.position = Vector2(8, 256)
	title.add_child(help)
	await get_tree().process_frame
	box.get_child(0).grab_focus()


func _close_title() -> void:
	if title:
		title.queue_free()
		title = null


func _new_game() -> void:
	_close_title()
	Game.new_game()
	await enter_area("town", Vector2i(22, 5), "down")
	await _say("Opening day in Pinecrest. Chris has $50, a .308 rifle, ten rounds and a grunt tube.")
	await _say("Hunt Maple Hollow to the east. Sell meat and hides at the Trading Post, gear up at the Outfitter, and check the Game Warden for paid requests.")
	await _say("Animals spot you from farther away when the wind carries your scent to them. Hold SNEAK to creep up quietly.")


func _continue() -> void:
	_close_title()
	Game.load_game()
	await enter_area(Game.area, Game.pos, Game.face)


# ---------------------------------------------------------------- areas ----
func enter_area(area: String, tile: Vector2i, face: String) -> void:
	mode = "busy"
	await _fade_to(1.0)
	if ow:
		ow.queue_free()
		ow = null
	if area == "hollow" and Game.area != "hollow":
		Game.reroll_wind()
	Game.area = area
	Game.pos = tile
	Game.face = face
	ow = Overworld.new()
	add_child(ow)
	move_child(ow, 0)
	ow.build(area, tile, face)
	ow.encounter.connect(_on_encounter)
	ow.door.connect(_on_door)
	ow.exit_area.connect(func(to, t, f): enter_area(to, t, f))
	ow.say.connect(_pause_say)
	ow.refill_at_truck.connect(_on_truck)
	hud.show_wind = area == "hollow"
	hud.visible = true
	hud.refresh()
	touch.set_shown(true)
	Game.save_game()
	await _fade_to(0.0)
	hud.announce(AREA_NAMES[area])
	mode = "play"


func _process(_d: float) -> void:
	if mode != "play" or ow == null:
		return
	hud.set_sneaking(ow.player.sneaking)
	Game.pos = ow.player.tile
	Game.face = ow.player.facing


func _unhandled_input(event: InputEvent) -> void:
	if mode == "play" and event.is_action_pressed("menu"):
		get_viewport().set_input_as_handled()
		mode = "menu"
		ow.set_paused(true)
		touch.set_shown(false)
		var m := PackMenu.open(ui)
		await m.closed
		_resume()


func _resume() -> void:
	ow.set_paused(false)
	touch.set_shown(true)
	hud.refresh()
	mode = "play"


func _pause_say(text: String) -> void:
	if ow:
		ow.set_paused(true)
	mode = "busy"
	await _say(text)
	_resume()


func _say(text: String) -> void:
	var was := mode
	touch.set_shown(false)
	var d := DialogBox.open(ui, text)
	await d.closed
	if was == "play":
		touch.set_shown(true)


# ------------------------------------------------------------ encounters ----
func _on_encounter(animal: Wildlife, opts: Dictionary) -> void:
	if mode != "play":
		return
	mode = "battle"
	ow.set_paused(true)
	touch.set_shown(false)
	await _battle_transition()
	hud.visible = false
	ow.visible = false
	var b := BattleScene.new()
	ui.add_child(b)
	await _fade_to(0.0, 0.15)
	b.begin(animal.species, opts)
	var outcome: String = await b.finished
	await _fade_to(1.0, 0.25)
	b.queue_free()
	ow.visible = true
	hud.visible = true
	hud.refresh()
	match outcome:
		"harvest", "fled":
			ow.remove_animal(animal)
		"retreat":
			animal.notice(false)
		"defeat":
			var r := Game.defeated()
			await _fade_to(1.0)
			await _say("Chris comes to on the cabin cot, bruised. The doctor's bill: $%d. %s" % [r["bill"],
				"Unsold meat spoiled." if r["lost"] else ""])
			await enter_area("town", Vector2i(22, 5), "down")
			return
	await _fade_to(0.0, 0.25)
	_resume()


func _battle_transition() -> void:
	for i in 3:
		fade.color = Color(1, 1, 1, 0.8)
		await get_tree().create_timer(0.06).timeout
		fade.color = Color(1, 1, 1, 0.0)
		await get_tree().create_timer(0.06).timeout
	await _fade_to(1.0, 0.2)


func _on_door(id: String) -> void:
	if mode != "play":
		return
	mode = "shop"
	ow.set_paused(true)
	touch.set_shown(false)
	var s := ShopPanel.open(ui, id)
	await s.closed
	_resume()


func _on_truck() -> void:
	if mode != "play":
		return
	Game.refill()
	_pause_say("Chris restocks from the truck. Aim and Call uses refilled.")


func _fade_to(alpha: float, t := 0.3) -> void:
	var c := Art.NIGHT
	c.a = alpha
	var tw := create_tween()
	tw.tween_property(fade, "color", c, t)
	await tw.finished


# ---------------------------------------------------------------- debug ----
func _debug_args() -> Dictionary:
	var out := {}
	var parts := []
	if OS.has_feature("web"):
		var q = JavaScriptBridge.eval("window.location.search", true)
		if typeof(q) == TYPE_STRING and q.length() > 1:
			parts = q.substr(1).split("&")
	else:
		parts = OS.get_cmdline_user_args()
	for p in parts:
		var kv: PackedStringArray = p.split("=")
		if kv.size() == 2:
			out[kv[0]] = kv[1]
	return out


func _debug_start(d: Dictionary) -> void:
	Game.new_game()
	Game.money = int(d.get("money", Game.money))
	match d["debug"]:
		"town":
			await enter_area("town", Vector2i(22, 5), "down")
		"hollow":
			await enter_area("hollow", Vector2i(1, 15), "right")
		"battle":
			await enter_area("hollow", Vector2i(1, 15), "right")
			var a := Wildlife.new()
			a.setup(d.get("species", "whitetail_buck"), Vector2i(3, 15), [[3, 15, 3, 15]], ow)
			ow.world.add_child(a)
			ow.animals.append(a)
			_on_encounter(a, {"range": int(d.get("range", 1)), "downwind": true})
		"shop":
			await enter_area("town", Vector2i(22, 5), "down")
			_on_door(d.get("id", "outfitter"))
		_:
			_show_title()
