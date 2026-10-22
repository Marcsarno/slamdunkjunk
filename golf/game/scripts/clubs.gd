class_name Clubs
extends RefCounted
## Club table: the one place shot distances are tuned.
##
## carry_m is the full-power carry on flat ground with no wind. tests/test_physics.gd checks
## the simulation still produces these numbers, so holes can be designed around them.
## Pull strength maps to launch speed through sqrt(), which keeps carry roughly linear in pull:
## half a pull is about half the distance.

const ALL := [
	{"id": "driver", "label": "Driver", "carry_m": 205.0, "speed": 78.0, "launch_deg": 13.0,
		"lift": 0.0016, "sprite": "driver"},
	{"id": "iron", "label": "Iron", "carry_m": 150.0, "speed": 53.6, "launch_deg": 21.0,
		"lift": 0.0020, "sprite": "iron"},
	{"id": "wedge", "label": "Wedge", "carry_m": 88.0, "speed": 34.0, "launch_deg": 34.0,
		"lift": 0.0024, "sprite": "iron"},
	{"id": "putter", "label": "Putter", "carry_m": 22.0, "speed": 5.4, "launch_deg": 0.0,
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


## Longest club whose full carry doesn't fly well past the target.
static func pick(distance: float, on_green: bool) -> Dictionary:
	if on_green:
		return by_id("putter")
	for c in ALL:
		if c.id != "putter" and c.carry_m <= distance * 1.12:
			return c
	return by_id("wedge")
