class_name GameData
## Static game data: weapons, animals, shop stock and requests.
## Every number here is a starting guess; tests/balance_sim.gd checks them.

const RANGE_NAMES := ["CLOSE", "MID", "LONG"]

const WEAPONS := {
	"rifle": {
		"name": ".308 Rifle", "short": "RIFLE",
		"acc": [80, 90, 85],          # close, mid, long
		"power": 40, "noise": 35,
		"hide_mod": {"light": 1.0, "medium": 1.0, "heavy": 0.85},
		"overkill": ["light"],        # too much gun: meat grade drops
		"ammo": "rifle_ammo",
	},
	"shotgun": {
		"name": "12-Gauge", "short": "SHOTGUN",
		"acc": [95, 70, 0],
		"power": 30, "noise": 30,
		"hide_mod": {"light": 1.0, "medium": 0.75, "heavy": 0.5},
		"overkill": [],
		"ammo": "shells",
	},
}

## behavior: picks moves in battle_rules.gd
## keen: Spook added every turn (halved by scent, zero when downwind)
## notice: tiles at which it spots a walking hunter on the map
const ANIMALS := {
	"cottontail": {
		"name": "Cottontail", "rarity": "Common", "hide": "light",
		"vit": 26, "spook": 20, "keen": 3, "evasion": 15, "notice": 3,
		"call": "", "danger": false, "speed": 0.30,
		"drops": [["meat", "Rabbit meat", 8], ["pelt", "Rabbit pelt", 6]],
		"xp": 5,
	},
	"wild_turkey": {
		"name": "Wild Turkey", "rarity": "Uncommon", "hide": "light",
		"vit": 46, "spook": 35, "keen": 5, "evasion": 25, "notice": 5,
		"call": "box", "danger": false, "speed": 0.38,
		"drops": [["meat", "Turkey meat", 40], ["fan", "Tail fan", 25]],
		"xp": 12,
	},
	"whitetail_doe": {
		"name": "Whitetail Doe", "rarity": "Common", "hide": "medium",
		"vit": 60, "spook": 20, "keen": 3, "evasion": 5, "notice": 5,
		"call": "grunt", "danger": false, "speed": 0.34,
		"drops": [["meat", "Venison", 90], ["pelt", "Deer hide", 25]],
		"xp": 12,
	},
	"red_fox": {
		"name": "Red Fox", "rarity": "Uncommon", "hide": "medium",
		"vit": 45, "spook": 30, "keen": 4, "evasion": 15, "notice": 4,
		"call": "predator", "danger": false, "speed": 0.30,
		"drops": [["pelt", "Fox pelt", 70]],
		"xp": 15,
	},
	"whitetail_buck": {
		"name": "Whitetail Buck", "rarity": "Rare", "hide": "medium",
		"vit": 90, "spook": 30, "keen": 9, "evasion": 10, "notice": 6,
		"call": "grunt", "danger": true, "speed": 0.34,
		"drops": [["meat", "Venison", 110], ["antlers", "Antlers", 0]],
		"xp": 30,
	},
	"black_bear": {
		"name": "Black Bear", "rarity": "Rare", "hide": "heavy",
		"vit": 150, "spook": 10, "keen": 2, "evasion": 0, "notice": 4,
		"call": "predator", "danger": true, "speed": 0.42,
		"drops": [["meat", "Bear meat", 150], ["pelt", "Bear hide", 300]],
		"xp": 40,
	},
}

## Overworld spawn weights in Maple Hollow.
const SPAWN_WEIGHTS := {
	"cottontail": 30, "whitetail_doe": 22, "wild_turkey": 18,
	"red_fox": 14, "whitetail_buck": 10, "black_bear": 6,
}

const CALLS := {
	"grunt": "Grunt Tube", "box": "Box Call", "predator": "Predator Call",
}

const GRADE_MULT := {"A": 1.5, "B": 1.0, "C": 0.6}

## Outfitter stock. kind: weapon / ammo / call / consumable / upgrade
const SHOP := [
	{"id": "rifle_ammo", "name": "Rifle ammo x10", "price": 15, "kind": "ammo", "qty": 10,
		"desc": "Ten .308 rounds."},
	{"id": "shotgun", "name": "12-Gauge Shotgun", "price": 120, "kind": "weapon",
		"desc": "Deadly up close and on birds. Comes with 10 shells. A rifle ruins small-game meat; this doesn't."},
	{"id": "shells", "name": "Shotgun shells x10", "price": 12, "kind": "ammo", "qty": 10,
		"desc": "Ten 12-gauge shells.", "needs": "shotgun"},
	{"id": "box", "name": "Box Call", "price": 40, "kind": "call",
		"desc": "Turkey yelps. A gobbler struts two ranges closer."},
	{"id": "predator", "name": "Predator Call", "price": 60, "kind": "call",
		"desc": "Dying-rabbit squeal. Pulls in foxes... and anything else that's hungry."},
	{"id": "scent", "name": "Cover Scent x2", "price": 20, "kind": "consumable", "qty": 2,
		"desc": "In battle: Spook gains are halved for 3 turns."},
	{"id": "spray", "name": "Bear Spray", "price": 35, "kind": "consumable", "qty": 1,
		"desc": "Cancels a charge and stuns the animal for a turn."},
	{"id": "scope", "name": "Variable Scope", "price": 150, "kind": "upgrade",
		"desc": "Rifle accuracy +15% at Long range, +10% at Mid."},
	{"id": "boots", "name": "Quiet Boots", "price": 90, "kind": "upgrade",
		"desc": "Animals notice you later on the map, and Stalk adds half the Spook."},
]

## Game Warden requests. Count harvests of a species after accepting.
const REQUESTS := [
	{"id": "rabbits", "title": "Rabbit Stew", "species": "cottontail", "count": 2, "reward": 40,
		"text": "The diner's out of rabbit. Bring in two cottontails."},
	{"id": "turkey", "title": "Thanksgiving Bird", "species": "wild_turkey", "count": 1, "reward": 60,
		"text": "Folks want a wild turkey for the harvest supper. Gobblers answer a box call."},
	{"id": "bear", "title": "Berry Thicket Bear", "species": "black_bear", "count": 1, "reward": 200,
		"text": "A black bear's raiding the berry thicket up north-east of the pond. Take bear spray.",
		"after": "turkey"},
]

const START_MONEY := 50
const MAX_STAMINA := 100
const START_NERVE := 70
const ABILITY_USES := {"aim": 3, "call": 3}
