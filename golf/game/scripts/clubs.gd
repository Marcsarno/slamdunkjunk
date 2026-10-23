class_name Clubs
extends RefCounted
## Club table: the one place shot distances are tuned.
##
## carry_m is the full-power carry on flat ground with no wind. tests/test_physics.gd checks
## the simulation still produces these numbers, so holes can be designed around them.
## Pull strength maps to launch speed through sqrt(), which keeps carry roughly linear in pull:
## half a pull is about half the distance.

## A full bag, so the club picked for a shot always needs most of a full pull (finer control than one
## iron covering everything up to 160 yards). kind: how the shot runs out (woods run, irons roll a
## little, wedges stop, a chip skips and runs) and which swing she makes.
const ALL := [
	{"id": "driver", "label": "Driver", "kind": "wood", "carry_m": 205.0, "speed": 78.1, "launch_deg": 13.0,
		"lift": 0.0016, "sprite": "driver"},
	{"id": "wood3", "label": "3 Wood", "kind": "wood", "carry_m": 185.0, "speed": 69.2, "launch_deg": 15.0,
		"lift": 0.0017, "sprite": "driver"},
	{"id": "iron5", "label": "5 Iron", "kind": "iron", "carry_m": 165.0, "speed": 59.9, "launch_deg": 18.0,
		"lift": 0.0019, "sprite": "iron"},
	{"id": "iron7", "label": "7 Iron", "kind": "iron", "carry_m": 145.0, "speed": 52.4, "launch_deg": 21.0,
		"lift": 0.0020, "sprite": "iron"},
	{"id": "iron9", "label": "9 Iron", "kind": "iron", "carry_m": 125.0, "speed": 45.0, "launch_deg": 26.0,
		"lift": 0.0021, "sprite": "iron"},
	{"id": "pwedge", "label": "P Wedge", "kind": "wedge", "carry_m": 105.0, "speed": 38.9, "launch_deg": 30.0,
		"lift": 0.0022, "sprite": "iron"},
	{"id": "swedge", "label": "S Wedge", "kind": "wedge", "carry_m": 82.0, "speed": 32.5, "launch_deg": 34.0,
		"lift": 0.0024, "sprite": "iron"},
	{"id": "lwedge", "label": "L Wedge", "kind": "wedge", "carry_m": 58.0, "speed": 26.0, "launch_deg": 40.0,
		"lift": 0.0026, "sprite": "iron"},
	{"id": "chip", "label": "Chip", "kind": "chip", "carry_m": 32.0, "speed": 19.6, "launch_deg": 30.0,
		"lift": 0.0024, "sprite": "iron"},
	{"id": "putter", "label": "Putter", "kind": "putter", "carry_m": 22.0, "speed": 5.4, "launch_deg": 0.0,
		"lift": 0.0, "sprite": "putter"},
]

const POWER_EXPONENT := 0.5


static func by_id(id: String) -> Dictionary:
	for c in ALL:
		if c.id == id:
			return c
	return ALL[0]


static func launch_velocity(club: Dictionary, power: float, aim: Vector2) -> Vector3:
	var speed: float = club.speed * pow(clampf(power, 0.0, 1.0), POWER_EXPONENT)
	var a := deg_to_rad(club.launch_deg)
	var d := aim.normalized()
	return Vector3(d.x * cos(a), d.y * cos(a), sin(a)) * speed


## The club for a shot of `distance`: the shortest whose full swing covers it with a little in hand
## (PICK_SHARE), so the shot needs most of a full pull but stays short of the risky top of it; the
## driver when none does. On the green, the putter.
const PICK_SHARE := 0.9


static func pick(distance: float, on_green: bool) -> Dictionary:
	if on_green:
		return by_id("putter")
	for i in range(ALL.size() - 2, -1, -1):        # shortest first, the putter left out
		if ALL[i].carry_m * PICK_SHARE >= distance:
			return ALL[i]
	return ALL[0]


## The next club down the bag (back round to the driver after the putter), for the club button.
static func next(club: Dictionary) -> Dictionary:
	for i in ALL.size():
		if ALL[i].id == club.id:
			return ALL[(i + 1) % ALL.size()]
	return ALL[0]
