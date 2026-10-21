extends SceneTree
## Balance simulator:  godot --headless --script res://tests/balance_sim.gd
##
## Plays N encounters per animal with three scripted styles and two gear
## levels, then prints harvest / escape / knocked-out rates, average turns
## and how often each action showed up in winning hunts.

const N := 2000
const SPECIES := ["cottontail", "whitetail_doe", "wild_turkey", "red_fox", "whitetail_buck", "black_bear"]

## Targets from the pitch, for the best style with starter gear.
const TARGET := {"Common": [0.75, 1.0], "Uncommon": [0.55, 0.75], "Rare": [0.25, 0.55]}


func _init() -> void:
	var problems := []
	for gear in ["starter", "upgraded"]:
		print("\n=== %s gear ===" % gear)
		print("%-15s %-8s %6s %6s %6s %6s %6s %5s %6s" % ["animal", "style", "win", "fled", "KO", "back", "turns", "A%", "$/hunt"])
		for sp in SPECIES:
			var best := 0.0
			for style in ["rusher", "stalker", "caller"]:
				var r := run(sp, style, gear)
				best = maxf(best, r["win"])
				print("%-15s %-8s %5.0f%% %5.0f%% %5.0f%% %5.0f%% %6.1f %4.0f%% %6.0f" % [sp, style,
					r["win"] * 100, r["fled"] * 100, r["defeat"] * 100, r["retreat"] * 100,
					r["turns"], r["a_rate"] * 100, r["money"]])
			if gear == "starter":
				var band: Array = TARGET[GameData.ANIMALS[sp]["rarity"]]
				if best < band[0] or best > band[1]:
					problems.append("%s best win %.0f%% outside %.0f-%.0f%%" % [sp, best * 100, band[0] * 100, band[1] * 100])
		print("\naction share in winning hunts (%s, all styles):" % gear)
		var share := action_share(gear)
		var keys := share.keys()
		keys.sort_custom(func(x, y): return share[x] > share[y])
		for k in keys:
			if k == "shoot":
				continue
			print("  %-7s %4.0f%%" % [k, share[k] * 100])
	print("")
	if problems.is_empty():
		print("All animals inside their target bands.")
	else:
		for p in problems:
			print("OUT OF BAND: " + p)
	quit(0)


func gear_loadout(gear: String) -> Dictionary:
	if gear == "starter":
		return {"weapon": "rifle", "weapons": ["rifle"], "ammo": {"rifle_ammo": 10, "shells": 0},
			"calls": ["grunt"], "upgrades": [], "items": {"scent": 1, "spray": 0},
			"uses": {"aim": 3, "call": 3}, "stamina": 100}
	return {"weapon": "rifle", "weapons": ["rifle", "shotgun"], "ammo": {"rifle_ammo": 10, "shells": 10},
		"calls": ["grunt", "box", "predator"], "upgrades": ["scope", "boots"], "items": {"scent": 2, "spray": 1},
		"uses": {"aim": 3, "call": 3}, "stamina": 100}


var _used_wins := {}


func run(sp: String, style: String, gear: String) -> Dictionary:
	var tally := {"harvest": 0, "fled": 0, "defeat": 0, "retreat": 0}
	var turns := 0
	var a_count := 0
	var money := 0
	for i in N:
		var lo := gear_loadout(gear)
		# small birds and rabbits: upgraded hunters carry the shotgun
		if gear == "upgraded" and GameData.ANIMALS[sp]["hide"] == "light":
			lo["weapon"] = "shotgun"
		var b := BattleRules.new()
		var start_range: int = [BattleRules.MID, BattleRules.LONG, BattleRules.MID][i % 3]
		b.start(sp, lo, {"seed": i * 7919 + 13, "range": start_range, "downwind": i % 2 == 0})
		var used := {}
		var guard := 0
		while b.outcome == "" and guard < 40:
			var act := choose(b, style)
			used[act] = true
			b.act(act)
			guard += 1
		if b.outcome == "":
			b.outcome = "retreat"
		tally[b.outcome] += 1
		turns += b.turn
		if b.outcome == "harvest":
			if b.result["grade"] == "A":
				a_count += 1
			for d in b.result["drops"]:
				money += d["value"]
			var key := gear
			if not _used_wins.has(key):
				_used_wins[key] = {"_wins": 0}
			_used_wins[key]["_wins"] += 1
			for k in used:
				_used_wins[key][k] = _used_wins[key].get(k, 0) + 1
	return {"win": tally["harvest"] / float(N), "fled": tally["fled"] / float(N),
		"defeat": tally["defeat"] / float(N), "retreat": tally["retreat"] / float(N),
		"turns": turns / float(N), "a_rate": a_count / maxf(1.0, tally["harvest"]), "money": money / float(N)}


func action_share(gear: String) -> Dictionary:
	var d: Dictionary = _used_wins.get(gear, {"_wins": 1})
	var out := {}
	for k in d:
		if k != "_wins":
			out[k] = d[k] / float(d["_wins"])
	return out


func on(b: BattleRules, id: String) -> bool:
	for x in b.actions() + b.bag_actions():
		if x["id"] == id:
			return x["on"]
	return false


func choose(b: BattleRules, style: String) -> String:
	# careful styles answer a telegraphed attack; the rusher just keeps shooting
	if b.telegraph != "" and style != "rusher":
		if on(b, "spray") and b.species == "black_bear":
			return "spray"
		return "brace"
	if b.stamina <= 25 and b.a["danger"]:
		return "run"
	match style:
		"rusher":
			if on(b, "shoot"):
				return "shoot"
			if on(b, "stalk"):
				return "stalk"
			return "wait"
		"stalker":
			if b.spook >= 65:
				return "wait"
			if b.range_i == BattleRules.LONG and on(b, "stalk"):
				return "stalk"
			if b.aim_acc == 0 and on(b, "aim") and b.spook < 55:
				return "aim"
			if on(b, "shoot"):
				return "shoot"
			return "wait"
		"caller":
			if b.downwind == false and on(b, "scent") and b.scent_turns == 0 and b.turn == 0:
				return "scent"
			if b.range_i > BattleRules.CLOSE and on(b, "call") and b.matching_call() == b.a["call"] and b.calls_heard == 0:
				return "call"
			if b.spook >= 70:
				return "wait"
			if b.aim_acc == 0 and on(b, "aim"):
				return "aim"
			if on(b, "shoot"):
				return "shoot"
			if on(b, "stalk"):
				return "stalk"
			return "wait"
	return "wait"
