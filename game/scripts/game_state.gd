extends Node
## Autoload "Game": everything that persists between scenes and in the save.

const SAVE_PATH := "user://save.json"
const SAVE_VERSION := 1

var money := 0
var stamina := 0
var inventory: Array = []        # harvested drops waiting to be sold
var weapons: Array = []
var weapon := "rifle"
var ammo: Dictionary = {}
var calls: Array = []
var upgrades: Array = []
var items: Dictionary = {}
var uses: Dictionary = {}
var journal: Dictionary = {}     # species -> {seen, harvested, best_grade, best_score}
var requests: Dictionary = {}    # id -> {state: open/active/done, progress}
var area := "town"
var pos := Vector2i(22, 5)
var face := "down"
var earned := 0                  # lifetime sales, for the title screen
var wind := Vector2i.RIGHT       # direction the wind blows toward

signal changed


func _ready() -> void:
	_setup_input()
	new_game()


func _setup_input() -> void:
	var binds := {
		"move_up": [KEY_UP, KEY_W], "move_down": [KEY_DOWN, KEY_S],
		"move_left": [KEY_LEFT, KEY_A], "move_right": [KEY_RIGHT, KEY_D],
		"action": [KEY_Z, KEY_ENTER, KEY_SPACE, KEY_E],
		"sneak": [KEY_X, KEY_SHIFT],
		"menu": [KEY_ESCAPE, KEY_C, KEY_TAB],
	}
	for act in binds:
		if not InputMap.has_action(act):
			InputMap.add_action(act)
		for k in binds[act]:
			var ev := InputEventKey.new()
			ev.physical_keycode = k
			InputMap.action_add_event(act, ev)


func new_game() -> void:
	money = GameData.START_MONEY
	stamina = GameData.MAX_STAMINA
	inventory = []
	weapons = ["rifle"]
	weapon = "rifle"
	ammo = {"rifle_ammo": 10, "shells": 0}
	calls = ["grunt"]
	upgrades = []
	items = {"scent": 1, "spray": 0}
	uses = GameData.ABILITY_USES.duplicate()
	journal = {}
	requests = {}
	for r in GameData.REQUESTS:
		requests[r["id"]] = {"state": "open", "progress": 0}
	area = "town"
	pos = Vector2i(22, 5)
	face = "down"
	earned = 0
	reroll_wind()


func reroll_wind() -> void:
	wind = [Vector2i.UP, Vector2i.DOWN, Vector2i.LEFT, Vector2i.RIGHT].pick_random()


## The dictionary BattleRules spends from. Sub-dictionaries are shared, so
## ammo and uses spent in battle come straight off the real totals.
func loadout() -> Dictionary:
	return {"weapon": weapon, "weapons": weapons, "ammo": ammo, "calls": calls,
		"upgrades": upgrades, "items": items, "uses": uses, "stamina": stamina}


func after_battle(lo: Dictionary) -> void:
	stamina = lo["stamina"]
	weapon = lo["weapon"]
	changed.emit()


func mark_seen(species: String) -> void:
	var j: Dictionary = journal.get(species, {"seen": 0, "harvested": 0, "best_grade": "", "best_score": 0})
	j["seen"] += 1
	journal[species] = j


## Bank the drops, update the journal and requests. Returns request titles completed.
func add_harvest(species: String, result: Dictionary) -> Array:
	for d in result["drops"]:
		inventory.append(d)
	var j: Dictionary = journal.get(species, {"seen": 1, "harvested": 0, "best_grade": "", "best_score": 0})
	j["harvested"] += 1
	if j["best_grade"] == "" or result["grade"] < j["best_grade"]:
		j["best_grade"] = result["grade"]
	j["best_score"] = maxi(j["best_score"], result.get("score", 0))
	journal[species] = j
	var done := []
	for r in GameData.REQUESTS:
		var st: Dictionary = requests[r["id"]]
		if st["state"] == "active" and r["species"] == species:
			st["progress"] += 1
			if st["progress"] >= r["count"]:
				st["state"] = "ready"
				done.append(r["title"])
	changed.emit()
	return done


func inventory_value() -> int:
	var t := 0
	for d in inventory:
		t += d["value"]
	return t


func sell_all() -> int:
	var total := inventory_value()
	money += total
	earned += total
	inventory = []
	changed.emit()
	return total


func owns(id: String) -> bool:
	return id in weapons or id in calls or id in upgrades


## Returns "" on success, or the reason it failed.
func buy(entry: Dictionary) -> String:
	if entry.has("needs") and not owns(entry["needs"]):
		return "You need the %s first." % entry["needs"]
	var kind: String = entry["kind"]
	if kind in ["weapon", "call", "upgrade"] and owns(entry["id"]):
		return "Already owned."
	if money < entry["price"]:
		return "Not enough money."
	money -= entry["price"]
	match kind:
		"weapon":
			weapons.append(entry["id"])
			ammo["shells"] += 10
		"ammo":
			ammo[entry["id"]] += entry["qty"]
		"call":
			calls.append(entry["id"])
		"upgrade":
			upgrades.append(entry["id"])
		"consumable":
			items[entry["id"]] = items.get(entry["id"], 0) + entry["qty"]
	changed.emit()
	return ""


func request_available(r: Dictionary) -> bool:
	if r.has("after"):
		return requests[r["after"]]["state"] == "done"
	return true


func accept_request(id: String) -> void:
	requests[id]["state"] = "active"
	requests[id]["progress"] = 0
	changed.emit()


func turn_in_request(id: String) -> int:
	for r in GameData.REQUESTS:
		if r["id"] == id and requests[id]["state"] == "ready":
			requests[id]["state"] = "done"
			money += r["reward"]
			changed.emit()
			return r["reward"]
	return 0


func refill() -> void:
	uses = GameData.ABILITY_USES.duplicate()
	changed.emit()


func rest() -> void:
	stamina = GameData.MAX_STAMINA
	refill()


## Knocked out in the field: meat spoils, the doctor bills $25.
func defeated() -> Dictionary:
	var lost := 0
	var keep := []
	for d in inventory:
		if d["kind"] == "meat":
			lost += 1
		else:
			keep.append(d)
	inventory = keep
	var bill := mini(money, 25)
	money -= bill
	stamina = GameData.MAX_STAMINA / 2
	area = "town"
	pos = Vector2i(22, 5)
	face = "down"
	changed.emit()
	return {"lost": lost, "bill": bill}


# ---------------------------------------------------------------- save ----
func to_dict() -> Dictionary:
	return {
		"version": SAVE_VERSION, "money": money, "stamina": stamina, "inventory": inventory,
		"weapons": weapons, "weapon": weapon, "ammo": ammo, "calls": calls,
		"upgrades": upgrades, "items": items, "uses": uses, "journal": journal,
		"requests": requests, "area": area, "pos": [pos.x, pos.y], "face": face, "earned": earned,
	}


func from_dict(d: Dictionary) -> void:
	new_game()
	money = int(d.get("money", money))
	stamina = int(d.get("stamina", stamina))
	inventory = d.get("inventory", [])
	for item in inventory:
		item["value"] = int(item["value"])
	weapons = d.get("weapons", weapons)
	weapon = d.get("weapon", weapon)
	for k in d.get("ammo", {}):
		ammo[k] = int(d["ammo"][k])
	calls = d.get("calls", calls)
	upgrades = d.get("upgrades", upgrades)
	for k in d.get("items", {}):
		items[k] = int(d["items"][k])
	for k in d.get("uses", {}):
		uses[k] = int(d["uses"][k])
	journal = {}
	var jd: Dictionary = d.get("journal", {})
	for sp in jd:
		var e: Dictionary = jd[sp]
		journal[sp] = {"seen": int(e["seen"]), "harvested": int(e["harvested"]),
			"best_grade": e["best_grade"], "best_score": int(e["best_score"])}
	var rq: Dictionary = d.get("requests", {})
	for id in rq:
		if requests.has(id):
			requests[id] = {"state": rq[id]["state"], "progress": int(rq[id]["progress"])}
	area = d.get("area", area)
	var p: Array = d.get("pos", [pos.x, pos.y])
	pos = Vector2i(int(p[0]), int(p[1]))
	face = d.get("face", face)
	earned = int(d.get("earned", 0))


func save_game() -> void:
	var f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if f == null:
		push_error("Could not save: %s" % FileAccess.get_open_error())
		return
	f.store_string(JSON.stringify(to_dict()))
	f.close()


func has_save() -> bool:
	return FileAccess.file_exists(SAVE_PATH)


func load_game() -> bool:
	if not has_save():
		return false
	var f := FileAccess.open(SAVE_PATH, FileAccess.READ)
	var parsed = JSON.parse_string(f.get_as_text())
	f.close()
	if typeof(parsed) != TYPE_DICTIONARY:
		return false
	from_dict(parsed)
	changed.emit()
	return true


func delete_save() -> void:
	if has_save():
		DirAccess.remove_absolute(SAVE_PATH)
