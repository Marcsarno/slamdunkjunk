extends SceneTree
## Headless test runner:  godot --headless --script res://tests/run_tests.gd
## Exits 1 if anything fails.

var failures := 0
var passes := 0
var current := ""


func _init() -> void:
	for t in [
		"test_start_state", "test_shoot_spends_ammo", "test_out_of_ammo_disables_shoot",
		"test_shotgun_cannot_reach_long", "test_stalk_and_spook_cost", "test_aim_then_bonus_consumed",
		"test_brace_softens_charge", "test_unbraced_charge_hurts", "test_spray_cancels_maul",
		"test_spook_100_means_escape", "test_right_and_wrong_calls", "test_fox_wary_of_second_call",
		"test_rifle_overkill_on_rabbit", "test_clean_shotgun_kill_can_grade_a",
		"test_defeat_when_stamina_runs_out", "test_downwind_stops_passive_spook",
		"test_hit_chance_responds_to_nerve", "test_enraged_bear_never_flees_from_spook",
		"test_bear_can_grade_a", "test_walk_frames_alternate", "test_buy_and_sell", "test_requests_flow",
		"test_defeat_penalty", "test_save_round_trip", "test_area_files",
	]:
		current = t
		call(t)
	print("\n%d passed, %d failed" % [passes, failures])
	quit(1 if failures else 0)


func check(cond: bool, what: String) -> void:
	if cond:
		passes += 1
	else:
		failures += 1
		print("FAIL  %s: %s" % [current, what])


func loadout(extra := {}) -> Dictionary:
	var lo := {"weapon": "rifle", "weapons": ["rifle", "shotgun"], "ammo": {"rifle_ammo": 10, "shells": 10},
		"calls": ["grunt"], "upgrades": [], "items": {"scent": 1, "spray": 1},
		"uses": {"aim": 3, "call": 3}, "stamina": 100}
	lo.merge(extra, true)
	return lo


func battle(species: String, opts := {}, extra := {}) -> BattleRules:
	var b := BattleRules.new()
	var o := {"seed": 1}
	o.merge(opts, true)
	b.start(species, loadout(extra), o)
	return b


# ---------------------------------------------------------------- rules ----
func test_start_state() -> void:
	var b := battle("whitetail_buck", {"range": BattleRules.LONG, "spook_bonus": 10})
	var buck: Dictionary = GameData.ANIMALS["whitetail_buck"]
	check(b.vit == buck["vit"] and b.vit_max == buck["vit"], "buck starts at full vitality")
	check(b.spook == buck["spook"] + 10, "base spook + bonus 10")
	check(b.range_i == BattleRules.LONG, "starts at the given range")
	check(b.nerve == GameData.START_NERVE - 10, "dangerous game costs 10 nerve")


func test_shoot_spends_ammo() -> void:
	var b := battle("whitetail_doe")
	b.act("shoot")
	check(b.loadout["ammo"]["rifle_ammo"] == 9, "one round spent")
	check(b.shots == 1, "shot counted")


func test_out_of_ammo_disables_shoot() -> void:
	var b := battle("whitetail_doe", {}, {"ammo": {"rifle_ammo": 0, "shells": 0}})
	check(not b.actions()[0]["on"], "shoot is disabled with no ammo")


func test_shotgun_cannot_reach_long() -> void:
	var b := battle("wild_turkey", {"range": BattleRules.LONG}, {"weapon": "shotgun"})
	check(not b.actions()[0]["on"], "shotgun shoot disabled at long range")
	check(b.hit_chance() == 0, "zero hit chance at long")


func test_stalk_and_spook_cost() -> void:
	var b := battle("whitetail_doe", {"range": BattleRules.LONG, "downwind": true})
	var s0 := b.spook
	b.events = []
	b._stalk()
	check(b.range_i == BattleRules.MID, "stalk closes one range")
	check(b.spook == s0 + 12, "stalk adds 12 spook")
	var t := battle("wild_turkey", {"range": BattleRules.LONG}, {"upgrades": ["boots"]})
	var t0 := t.spook
	t._stalk()
	check(t.spook == t0 + 16, "boots halve it, turkey eagle eye adds 10")


func test_aim_then_bonus_consumed() -> void:
	var b := battle("whitetail_doe", {"range": BattleRules.MID})
	var before := b.hit_chance()
	b._aim()
	check(b.hit_chance() > before, "aim raises hit chance")
	check(b.loadout["uses"]["aim"] == 2, "aim use spent")
	b._shoot()
	check(b.aim_acc == 0 and b.aim_vital == 0, "aim bonus consumed by the shot")


func test_brace_softens_charge() -> void:
	var b := battle("whitetail_buck", {"range": BattleRules.CLOSE})
	b.telegraph = "charge"
	b.act("brace")
	check(b.stamina == 95, "braced charge does 5 damage (got %d)" % b.stamina)
	check(b.counter_bonus == 25, "brace sets up a point-blank counter")


func test_unbraced_charge_hurts() -> void:
	var b := battle("whitetail_buck", {"range": BattleRules.CLOSE})
	var n0 := b.nerve
	b.telegraph = "charge"
	b.act("wait")
	check(b.stamina == 80, "unbraced charge does 20 damage")
	check(b.nerve < n0, "and shakes nerve")


func test_spray_cancels_maul() -> void:
	var b := battle("black_bear", {"range": BattleRules.CLOSE})
	b.telegraph = "maul"
	b.act("spray")
	check(b.stamina == 100, "no damage after spray")
	check(b.loadout["items"]["spray"] == 0, "spray used up")
	check(b.telegraph == "" or b.outcome == "fled", "maul cancelled")


func test_spook_100_means_escape() -> void:
	var b := battle("whitetail_doe")
	b.spook = 99
	b.downwind = false
	b.telegraph = ""
	b.stunned = true          # animal skips its move, passive spook pushes it over
	b.act("brace")
	check(b.outcome == "fled", "animal bolts at 100 spook")


func test_right_and_wrong_calls() -> void:
	var b := battle("whitetail_doe", {"range": BattleRules.LONG})
	var s0 := b.spook
	b._call()
	check(b.range_i == BattleRules.MID, "grunt pulls a doe closer")
	check(b.spook == s0 - 5, "right call calms")
	var t := battle("wild_turkey", {"range": BattleRules.LONG})
	var t0 := t.spook
	t._call()
	check(t.spook == t0 + 20, "grunt tube on a turkey spooks it")
	var u := battle("wild_turkey", {"range": BattleRules.LONG}, {"calls": ["grunt", "box"]})
	u._call()
	check(u.range_i == BattleRules.CLOSE, "box call brings a gobbler two ranges")


func test_fox_wary_of_second_call() -> void:
	var b := battle("red_fox", {"range": BattleRules.LONG}, {"calls": ["predator"]})
	b._call()
	var s1 := b.spook
	b._call()
	check(b.spook == s1 + 20, "second call spooks a fox")


func test_rifle_overkill_on_rabbit() -> void:
	var graded := 0
	for seed in 60:
		var b := battle("cottontail", {"seed": seed, "range": BattleRules.MID})
		b.act("shoot")
		if b.outcome == "harvest":
			graded += 1
			check(b.result["grade"] != "A", "rifle on a rabbit can't grade A")
			check(b.result["notes"].size() == 1, "overkill note")
	check(graded > 20, "rifle kills rabbits in one shot often")


func test_clean_shotgun_kill_can_grade_a() -> void:
	var got_a := false
	for seed in 300:
		var b := battle("cottontail", {"seed": seed, "range": BattleRules.CLOSE}, {"weapon": "shotgun"})
		b.act("shoot")
		if b.outcome == "harvest" and b.result["grade"] == "A":
			got_a = true
			break
	check(got_a, "a single vital shotgun hit grades A")


func test_defeat_when_stamina_runs_out() -> void:
	var b := battle("black_bear", {"range": BattleRules.CLOSE}, {"stamina": 10})
	b.telegraph = "maul"
	b.act("wait")
	check(b.outcome == "defeat", "maul at 10 stamina knocks Chris out")
	check(b.loadout["stamina"] == 0, "stamina written back")


func test_downwind_stops_passive_spook() -> void:
	var b := battle("whitetail_buck", {"downwind": true, "range": BattleRules.LONG})
	b.spook = 30
	b._end_round()
	check(b.spook == 30, "no keen-nose spook when downwind")
	var c := battle("whitetail_buck", {"downwind": false, "range": BattleRules.LONG})
	c.spook = 30
	c._end_round()
	check(c.spook == 30 + GameData.ANIMALS["whitetail_buck"]["keen"], "keen nose adds spook when upwind")


func test_hit_chance_responds_to_nerve() -> void:
	var b := battle("whitetail_doe", {"range": BattleRules.MID})
	b.nerve = 100
	var hi := b.hit_chance()
	b.nerve = 0
	var lo := b.hit_chance()
	check(hi - lo >= 30, "nerve swings accuracy a lot (%d vs %d)" % [hi, lo])


func test_enraged_bear_never_flees_from_spook() -> void:
	var b := battle("black_bear")
	b.vit = 20
	var s0 := b.spook
	b._add_spook(50)
	check(b.spook == s0, "enraged bear ignores spook")


# --------------------------------------------------------------- player ----
func test_bear_can_grade_a() -> void:
	var b := battle("black_bear")
	b.shots = 3
	b.hits = 3
	b.last_vital = true
	b.kill_weapon = "rifle"
	b._harvest()
	check(b.result["grade"] == "A", "three clean hits ending vital grade A on a bear")


func test_walk_frames_alternate() -> void:
	# Each tile step plays half the cycle; the foot alternates every step.
	var seq := []
	for step in 6:
		seq.append_array(Player.frames_for_step(step))
	check(seq == [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3], "frames run L,pass,R,pass in order: %s" % [seq])


# ---------------------------------------------------------------- state ----
func fresh_game() -> Node:
	var g = load("res://scripts/game_state.gd").new()
	g.new_game()
	return g


func test_buy_and_sell() -> void:
	var g := fresh_game()
	var shotgun := {}
	for e in GameData.SHOP:
		if e["id"] == "shotgun":
			shotgun = e
	check(g.buy(shotgun) == "Not enough money.", "can't afford shotgun at start")
	g.inventory = [{"kind": "meat", "name": "Venison", "species": "whitetail_doe", "grade": "A", "value": 135},
		{"kind": "pelt", "name": "Deer hide", "species": "whitetail_doe", "grade": "A", "value": 38}]
	check(g.sell_all() == 173, "sell all totals drops")
	check(g.inventory.is_empty(), "inventory cleared")
	check(g.buy(shotgun) == "", "can buy after selling")
	check("shotgun" in g.weapons and g.ammo["shells"] == 10, "shotgun comes with shells")
	check(g.buy(shotgun) == "Already owned.", "no double-buying")
	g.free()


func test_requests_flow() -> void:
	var g := fresh_game()
	var bear: Dictionary = GameData.REQUESTS[2]
	check(not g.request_available(bear), "bear request locked until turkey done")
	g.accept_request("rabbits")
	var res := {"grade": "B", "drops": [], "score": 0}
	g.add_harvest("cottontail", res)
	check(g.requests["rabbits"]["state"] == "active", "one rabbit isn't enough")
	var done: Array = g.add_harvest("cottontail", res)
	check(done == ["Rabbit Stew"], "second rabbit completes it")
	var m0: int = g.money
	check(g.turn_in_request("rabbits") == 40 and g.money == m0 + 40, "reward paid")
	check(g.journal["cottontail"]["harvested"] == 2, "journal counts harvests")
	g.free()


func test_defeat_penalty() -> void:
	var g := fresh_game()
	g.money = 100
	g.inventory = [{"kind": "meat", "value": 50}, {"kind": "pelt", "value": 20}]
	var r: Dictionary = g.defeated()
	check(r["lost"] == 1 and g.inventory.size() == 1, "meat spoils, pelts stay")
	check(g.money == 75, "doctor's bill")
	check(g.area == "town", "wakes up in town")
	g.free()


func test_save_round_trip() -> void:
	var g := fresh_game()
	g.money = 321
	g.upgrades = ["scope"]
	g.inventory = [{"kind": "pelt", "name": "Fox pelt", "species": "red_fox", "grade": "A", "value": 105}]
	g.accept_request("turkey")
	g.mark_seen("red_fox")
	g.pos = Vector2i(7, 9)
	g.area = "hollow"
	var text := JSON.stringify(g.to_dict())
	var h := fresh_game()
	h.from_dict(JSON.parse_string(text))
	check(h.money == 321 and h.upgrades == ["scope"], "money and upgrades survive")
	check(h.inventory.size() == 1 and h.inventory[0]["value"] == 105, "inventory survives")
	check(h.requests["turkey"]["state"] == "active", "requests survive")
	check(h.pos == Vector2i(7, 9) and h.area == "hollow", "position survives")
	check(typeof(h.ammo["rifle_ammo"]) == TYPE_INT, "numbers come back as ints")
	g.free()
	h.free()


func test_area_files() -> void:
	var maps := {}
	for name in ["town", "hollow"]:
		var f := FileAccess.open("res://assets/areas/%s.json" % name, FileAccess.READ)
		check(f != null, "%s.json exists" % name)
		if f == null:
			return
		maps[name] = JSON.parse_string(f.get_as_text())
	for name in maps:
		var m: Dictionary = maps[name]
		check(m["blocked"].size() == m["h"] and m["blocked"][0].length() == m["w"], "%s grid size" % name)
		var s: Dictionary = m["start"]
		check(m["blocked"][s["y"]][s["x"]] == "0", "%s start tile is walkable" % name)
		for e in m["exits"]:
			var to: Dictionary = maps[e["to"]]
			check(to["blocked"][e["ty"]][e["tx"]] == "0", "%s exit lands on a walkable tile" % name)
		for sp in m["zones"]:
			check(GameData.ANIMALS.has(sp), "zone species %s exists" % sp)
