class_name BattleRules
extends RefCounted
## Turn-based encounter rules. No graphics: the battle scene, the tests and
## the balance simulator all drive this same class.
##
## Each round: Chris acts, then the animal acts, then passive Spook builds.
## The animal escapes at 100 Spook. Dangerous animals telegraph big attacks
## a turn ahead, which is what Brace and Bear Spray answer.

const CLOSE := 0
const MID := 1
const LONG := 2

var rng := RandomNumberGenerator.new()
var species := ""
var a: Dictionary = {}          # GameData.ANIMALS entry
var loadout: Dictionary = {}    # shared with Game state; ammo/uses/items are spent from it

var vit := 0
var vit_max := 0
var spook := 0
var range_i := MID
var stamina := 100
var nerve := 70
var downwind := false

var aim_acc := 0
var aim_vital := 0
var counter_bonus := 0
var evasion_bonus := 0
var evasion_turns := 0
var scent_turns := 0
var roosted := 0
var telegraph := ""             # "", "charge" (buck) or "maul" (bear)
var stunned := false
var bracing := false
var wounded := false
var calls_heard := 0
var shots := 0
var hits := 0
var last_vital := false
var kill_weapon := ""
var turn := 0

var outcome := ""               # "", harvest, fled, retreat, defeat
var result: Dictionary = {}
var events: Array = []          # [{text, fx}] produced by the last act()


func start(p_species: String, p_loadout: Dictionary, opts: Dictionary = {}) -> void:
	species = p_species
	a = GameData.ANIMALS[species]
	loadout = p_loadout
	if opts.has("seed"):
		rng.seed = opts["seed"]
	else:
		rng.randomize()
	vit_max = a["vit"]
	vit = vit_max
	range_i = opts.get("range", MID)
	spook = clampi(a["spook"] + opts.get("spook_bonus", 0), 0, 95)
	downwind = opts.get("downwind", false)
	stamina = loadout.get("stamina", GameData.MAX_STAMINA)
	nerve = GameData.START_NERVE
	if a["danger"]:
		nerve -= 10   # big animals rattle you
	outcome = ""
	result = {}
	events = []


# ------------------------------------------------------------- actions ----
func weapon_id() -> String:
	return loadout.get("weapon", "rifle")


func ammo_left() -> int:
	return loadout["ammo"].get(GameData.WEAPONS[weapon_id()]["ammo"], 0)


func weapon_acc(r: int) -> int:
	var w: Dictionary = GameData.WEAPONS[weapon_id()]
	var acc: int = w["acc"][r]
	if weapon_id() == "rifle" and "scope" in loadout.get("upgrades", []):
		acc += [0, 10, 15][r]
	return acc


func hit_chance() -> int:
	if weapon_acc(range_i) <= 0:
		return 0
	var c: float = weapon_acc(range_i) * (0.6 + 0.4 * nerve / 100.0) + aim_acc + counter_bonus \
		- a["evasion"] - evasion_bonus
	return clampi(int(round(c)), 5, 97)


func matching_call() -> String:
	var owned: Array = loadout.get("calls", [])
	if a["call"] != "" and a["call"] in owned:
		return a["call"]
	return owned[0] if owned.size() > 0 else ""


## Buttons for the UI: id, label, detail line, enabled.
func actions() -> Array:
	var uses: Dictionary = loadout["uses"]
	var items: Dictionary = loadout["items"]
	var w: Dictionary = GameData.WEAPONS[weapon_id()]
	var call := matching_call()
	var list := [
		{"id": "shoot", "label": "SHOOT", "sub": "%d%% · %d left" % [hit_chance(), ammo_left()],
			"on": ammo_left() > 0 and weapon_acc(range_i) > 0},
		{"id": "aim", "label": "AIM", "sub": "%d/%d" % [uses["aim"], GameData.ABILITY_USES["aim"]],
			"on": uses["aim"] > 0},
		{"id": "stalk", "label": "STALK", "sub": "closer", "on": range_i > CLOSE},
		{"id": "call", "label": "CALL", "sub": (GameData.CALLS[call].to_upper() if call != "" else "NO CALL"),
			"on": call != "" and uses["call"] > 0},
		{"id": "wait", "label": "FREEZE", "sub": "calm it", "on": true},
		{"id": "brace", "label": "BRACE", "sub": "vs charge", "on": true},
		{"id": "bag", "label": "BAG", "sub": "items", "on": true},
		{"id": "run", "label": "BACK OFF", "sub": "leave", "on": true},
	]
	if w["acc"][range_i] <= 0:
		list[0]["sub"] = "out of range"
	return list


## Items usable from the BAG submenu.
func bag_actions() -> Array:
	var items: Dictionary = loadout["items"]
	var list := []
	list.append({"id": "scent", "label": "COVER SCENT", "sub": "x%d" % items.get("scent", 0),
		"on": items.get("scent", 0) > 0 and scent_turns == 0})
	list.append({"id": "spray", "label": "BEAR SPRAY", "sub": "x%d" % items.get("spray", 0),
		"on": items.get("spray", 0) > 0})
	var other := "shotgun" if weapon_id() == "rifle" else "rifle"
	list.append({"id": "switch", "label": "SWITCH GUN", "sub": GameData.WEAPONS[other]["short"],
		"on": other in loadout.get("weapons", [])})
	return list


func act(id: String) -> Array:
	events = []
	if outcome != "":
		return events
	turn += 1
	bracing = false
	match id:
		"shoot": _shoot()
		"aim": _aim()
		"stalk": _stalk()
		"call": _call()
		"wait": _wait()
		"brace": _brace()
		"scent": _scent()
		"spray": _spray()
		"switch": _switch()
		"run": _run()
		_: push_error("unknown action " + id)
	if outcome == "":
		_animal_turn()
	if outcome == "":
		_end_round()
	loadout["stamina"] = stamina
	return events


func _say(text: String, fx := "") -> void:
	events.append({"text": text, "fx": fx})


func _name() -> String:
	return a["name"].to_upper()


func _add_spook(n: int) -> void:
	if n > 0:
		if scent_turns > 0:
			n = int(n / 2.0)
		if species == "black_bear":
			n = int(n / 2.0)
			if vit < vit_max * 0.4:
				n = 0     # an enraged bear won't run
	spook = clampi(spook + n, 0, 100)


func _shoot() -> void:
	var w: Dictionary = GameData.WEAPONS[weapon_id()]
	loadout["ammo"][w["ammo"]] -= 1
	shots += 1
	var chance := hit_chance()
	var vital_chance := 20 + aim_vital + (10 if range_i == CLOSE else 0)
	aim_acc = 0
	aim_vital = 0
	counter_bonus = 0
	if rng.randi_range(1, 100) > chance:
		_say("Chris fires the %s... and misses!" % w["short"].to_lower(), "miss")
		_add_spook(w["noise"])
		return
	var vital := rng.randi_range(1, 100) <= vital_chance
	var dmg := int(round(w["power"] * w["hide_mod"][a["hide"]] * (2.0 if vital else 1.0) * rng.randf_range(0.9, 1.1)))
	vit = maxi(0, vit - dmg)
	hits += 1
	last_vital = vital
	if vital:
		_say("A vital hit!", "vital")
	else:
		_say("Hit!", "hit")
	if vit <= 0:
		kill_weapon = weapon_id()
		_harvest()
		return
	wounded = true
	_add_spook(20)
	_say("The %s is wounded." % a["name"].to_lower())


func _aim() -> void:
	loadout["uses"]["aim"] -= 1
	aim_acc = 20
	aim_vital = 25
	nerve = mini(100, nerve + 15)
	_say("Chris settles the crosshairs and breathes out slow.", "aim")


func _stalk() -> void:
	range_i -= 1
	var cost := 12
	if "boots" in loadout.get("upgrades", []):
		cost = 6
	if species == "wild_turkey":
		cost += 10   # eagle eye
	_add_spook(cost)
	_say("Chris creeps closer. %s range." % GameData.RANGE_NAMES[range_i].capitalize(), "stalk")


func _call() -> void:
	var call := matching_call()
	loadout["uses"]["call"] -= 1
	var label: String = GameData.CALLS[call]
	if call != a["call"]:
		_say("The %s doesn't fool it." % label.to_lower(), "call")
		_add_spook(20)
		return
	calls_heard += 1
	if species == "red_fox" and calls_heard > 1:
		_say("The fox isn't fooled twice.", "call")
		_add_spook(20)
		return
	var steps := 2 if species == "wild_turkey" else 1
	var before := range_i
	range_i = maxi(CLOSE, range_i - steps)
	_add_spook(-5)
	if species == "wild_turkey":
		_say("Chris works the box call. The gobbler struts in, fanned out!", "call")
	elif species == "black_bear":
		_say("The squeal sounds like an easy meal. The bear comes looking.", "call")
	else:
		_say("The %s answers the %s and steps closer." % [a["name"].to_lower(), label.to_lower()], "call")
	if before == CLOSE:
		_say("It's already close.")


func _wait() -> void:
	_add_spook(-20)
	nerve = mini(100, nerve + 5)
	_say("Chris freezes. Not a muscle moves.", "wait")
	if range_i < LONG and rng.randf() < 0.25:
		range_i += 1
		_say("The %s wanders a little farther off." % a["name"].to_lower())


func _brace() -> void:
	bracing = true
	_say("Chris plants both feet and gets ready.", "brace")


func _scent() -> void:
	loadout["items"]["scent"] -= 1
	scent_turns = 4
	_add_spook(-10)
	_say("Chris dabs on cover scent. The wind won't give Chris away now.", "scent")


func _spray() -> void:
	loadout["items"]["spray"] -= 1
	if telegraph != "":
		_say("A blast of bear spray! The attack falls apart.", "spray")
		telegraph = ""
		stunned = true
	else:
		_say("A cloud of bear spray drifts across the clearing.", "spray")
	if species == "black_bear" and rng.randf() < 0.4:
		_say("The bear crashes off into the brush.", "flee")
		outcome = "fled"
		return
	_add_spook(25)
	stunned = true


func _switch() -> void:
	var other := "shotgun" if weapon_id() == "rifle" else "rifle"
	loadout["weapon"] = other
	_say("Chris swaps to the %s." % GameData.WEAPONS[other]["name"], "switch")


func _run() -> void:
	if telegraph != "" and range_i == CLOSE and rng.randf() < 0.5:
		_say("Chris tries to back away, but it's too close!", "stumble")
		return
	_say("Chris backs off quietly and lets it go.", "run")
	outcome = "retreat"


# --------------------------------------------------------- animal turn ----
func _animal_turn() -> void:
	var n: String = a["name"].to_lower()
	if stunned:
		stunned = false
		_say("The %s shakes its head, stunned." % n)
		return
	if telegraph != "":
		_resolve_attack()
		return
	var r := rng.randf()
	var hurt := wounded and vit < vit_max * 0.35
	match species:
		"cottontail":
			if hurt and r < 0.6:
				_flee("The cottontail dives into a burrow.")
			elif r < 0.35:
				_evade(30, 2, "The cottontail zigzags!")
			elif r < 0.55:
				if range_i == LONG:
					_evade(50, 1, "The cottontail freezes, nearly invisible.")
				else:
					_add_spook(-5)
					_say("The cottontail freezes.")
			elif r < 0.75 and range_i < LONG:
				range_i += 1
				_say("The cottontail hops away a little.")
			else:
				_add_spook(-5)
				_say("The cottontail nibbles clover.")
		"wild_turkey":
			if spook >= 55 and roosted == 0 and r < 0.5:
				roosted = 2
				range_i = mini(LONG, range_i + 1)
				_evade(25, 2, "The turkey flies up into a tree!")
			elif spook >= 40:
				_add_spook(15)
				_say("Putt! Putt! The turkey is getting nervous.")
			elif hurt and r < 0.5:
				_flee("The turkey runs off into the timber.")
			else:
				_add_spook(-5)
				_say("The turkey scratches for acorns.")
		"whitetail_doe":
			if spook >= 70 and r < 0.5:
				if range_i == LONG:
					_flee("The doe bounds away, white tail flagging.")
				else:
					range_i += 1
					_say("The doe bounds a few steps farther away.")
			elif hurt and r < 0.5:
				_flee("The doe runs off, wounded. The trail goes cold.")
			elif spook >= 50:
				_add_spook(12)
				_say("The doe snorts and stamps a hoof.")
			elif r < 0.35:
				_evade(20, 2, "The doe flicks her tail and turns broadside... then quarters away.")
			else:
				_add_spook(-8)
				_say("The doe lowers her head to browse.")
		"red_fox":
			if hurt and r < 0.5:
				_flee("The fox vanishes into the brush.")
			elif r < 0.3:
				_evade(40, 1, "The fox slips behind the brush.")
			elif r < 0.5:
				range_i = rng.randi_range(CLOSE, LONG)
				_say("The fox doubles back. %s range." % GameData.RANGE_NAMES[range_i].capitalize())
			else:
				_add_spook(-5)
				_say("The fox pounces on a mouse in the leaves.")
		"whitetail_buck":
			if spook >= 70:
				if r < 0.5:
					_flee("Snort-wheeze! The buck explodes out of there.")
				else:
					_add_spook(12)
					_say("The buck snort-wheezes, hair standing up.")
			elif hurt and r < 0.45:
				_flee("The buck crashes off, wounded. The trail goes cold.")
			elif range_i <= MID and r < 0.3:
				telegraph = "charge"
				_say("The buck lowers its antlers and paws the ground!", "telegraph")
			elif r < 0.55:
				nerve = maxi(0, nerve - 10)
				_say("The buck stares right at Chris. Buck fever: Nerve drops.")
			else:
				_add_spook(-5)
				_say("The buck works a scrape, distracted.")
		"black_bear":
			var enraged := vit < vit_max * 0.4
			if wounded and range_i > CLOSE and r < 0.6:
				range_i = CLOSE
				telegraph = "maul"
				_say("The wounded bear comes straight at Chris!", "telegraph")
			elif range_i == CLOSE and r < 0.2 and not enraged:
				stamina = maxi(0, stamina - 8)
				_say("The bear swats at Chris! A glancing blow.", "hurt")
				if stamina <= 0:
					_say("Chris goes down hard...", "defeat")
					outcome = "defeat"
			elif range_i == CLOSE and (enraged or r < 0.75):
				telegraph = "maul"
				_say("The bear rears up on its hind legs!", "telegraph")
			elif r < 0.35:
				range_i = maxi(CLOSE, range_i - 1)
				nerve = maxi(0, nerve - 25)
				_say("The bear huffs and bluff-charges! Nerve shaken.", "bluff")
			elif r < 0.55:
				nerve = maxi(0, nerve - 10)
				_say("The bear pops its jaw at Chris.")
			else:
				_add_spook(-5)
				_say("The bear rakes berries off a bush.")


func _evade(amount: int, turns: int, text: String) -> void:
	evasion_bonus = amount
	evasion_turns = turns
	_say(text, "evade")


func _flee(text: String) -> void:
	_say(text, "flee")
	outcome = "fled"


func _resolve_attack() -> void:
	var kind := telegraph
	telegraph = ""
	var dmg := 20 if kind == "charge" else 30
	var nerve_hit := 20 if kind == "charge" else 15
	if kind == "maul" and vit < vit_max * 0.4:
		dmg = int(dmg * 1.5)
	if bracing and kind == "charge":
		dmg = int(dmg * 0.25)
		counter_bonus = 25
		_say("Chris braces and sidesteps! Only grazed. Next shot is point-blank.", "braced")
	elif bracing:
		dmg = int(dmg * 0.5)
		nerve = maxi(0, nerve - 10)
		_say("Chris braces behind a tree. The swipe still lands, but softened.", "braced")
	else:
		nerve = maxi(0, nerve - nerve_hit)
		_say("The %s %s! Chris takes a hit." % [a["name"].to_lower(), "charges" if kind == "charge" else "swipes"], "hurt")
	stamina = maxi(0, stamina - dmg)
	range_i = CLOSE
	if stamina <= 0:
		_say("Chris goes down hard...", "defeat")
		outcome = "defeat"


func _end_round() -> void:
	var gain: int = a["keen"]
	if downwind:
		gain = 0
	if range_i == CLOSE:
		gain += 4
	_add_spook(gain)
	if evasion_turns > 0:
		evasion_turns -= 1
		if evasion_turns == 0:
			evasion_bonus = 0
	if scent_turns > 0:
		scent_turns -= 1
	if roosted > 0:
		roosted -= 1
	if spook >= 100:
		if wounded:
			_flee("The %s bolts, wounded. The trail goes cold." % a["name"].to_lower())
		else:
			_flee("The %s has had enough. It's gone." % a["name"].to_lower())


# ------------------------------------------------------------- harvest ----
func _harvest() -> void:
	outcome = "harvest"
	# A: no misses, finished with a vital hit, in two shots (three for heavy hides).
	var misses := shots - hits
	var max_clean := 3 if a["hide"] == "heavy" else 2
	var grade := "C"
	if misses == 0 and shots <= max_clean and last_vital:
		grade = "A"
	elif hits <= 3 and misses <= 1:
		grade = "B"
	var notes := []
	var meat_mult := 1.0
	if a["hide"] in GameData.WEAPONS[kill_weapon]["overkill"]:
		meat_mult = 0.5
		notes.append("Too much gun: half the meat is ruined.")
		grade = {"A": "B", "B": "C", "C": "C"}[grade]
	var mult: float = GameData.GRADE_MULT[grade]
	var drops := []
	var score := 0
	for d in a["drops"]:
		var kind: String = d[0]
		var value: float = d[2]
		var label: String = d[1]
		if kind == "antlers":
			var points := rng.randi_range(4, 10)
			score = 60 + points * 9 + rng.randi_range(0, 20)
			value = score * 2
			label = "%d-point antlers (%d in)" % [points, score]
		if kind == "meat":
			value *= meat_mult
		drops.append({"kind": kind, "name": label, "species": species, "grade": grade,
			"value": int(round(value * mult))})
	result = {"grade": grade, "drops": drops, "notes": notes, "score": score}
	_say("Harvested! %s, grade %s." % [a["name"], grade], "harvest")
