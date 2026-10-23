extends Node
## The round in play (an autoload, so it lasts across scene changes): the holes built so far in order,
## which one is up, and the strokes taken on each hole finished. Start at hole 1 for a full round;
## starting anywhere else plays on from there.

const HOLES := [
	{"id": "h01", "name": "Pumpkin Patch", "par": 4},
	{"id": "h02", "name": "Witch's Hollow", "par": 3},
	{"id": "h03", "name": "Forgotten Cemetery", "par": 5},
	{"id": "h04", "name": "Spiderwood", "par": 4},
	{"id": "h05", "name": "Haunted Harvest", "par": 5},
	{"id": "h06", "name": "Ghostlight Marsh", "par": 3},
	{"id": "h07", "name": "Vampire's Garden", "par": 4},
	{"id": "h08", "name": "Headless Trail", "par": 4},
	{"id": "h09", "name": "Midnight Homecoming", "par": 4},
]

var index := 0
var scores := {}          # hole index -> strokes, for the holes finished this round


func _ready() -> void:
	# --hole=h02 starts the round there (once per launch, so Next hole still moves on)
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--hole="):
			select_id(a.trim_prefix("--hole="))


func start(i: int) -> void:
	index = clampi(i, 0, HOLES.size() - 1)
	scores = {}


func select_id(id: String) -> void:
	for i in HOLES.size():
		if HOLES[i].id == id:
			start(i)


func current() -> Dictionary:
	return HOLES[index]


func dir() -> String:
	return "res://assets/holes/%s" % HOLES[index].id


func has_next() -> bool:
	return index + 1 < HOLES.size()


func advance() -> void:
	index = mini(index + 1, HOLES.size() - 1)


func record(strokes: int) -> void:
	scores[index] = strokes


## Strokes against par over the holes finished, as golfers say it: "E", "+2", "-1".
func to_par_text() -> String:
	var d := 0
	for i in scores:
		d += int(scores[i]) - int(HOLES[i].par)
	return "E" if d == 0 else ("+%d" % d if d > 0 else "%d" % d)
