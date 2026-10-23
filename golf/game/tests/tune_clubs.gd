extends SceneTree
## Finds each club's launch speed for its carry (flat fairway, no wind), for tuning scripts/clubs.gd:
##   godot --headless --path golf/game --script res://tests/tune_clubs.gd
## Prints, per club in Clubs.ALL, the speed that carries carry_m with its launch angle and lift, and
## how far the shot then runs out.

func _init() -> void:
	var fair := Terrain.new()       # flat fairway, as in test_physics.gd
	fair.origin = Vector2(-200, -50)
	fair.cell = 1.0
	fair.nx = 401
	fair.ny = 451
	fair.heights.resize(fair.nx * fair.ny)
	fair.heights.fill(0.0)
	fair.surf_cell = 1.0
	fair.snx = fair.nx
	fair.sny = fair.ny
	fair.surface.resize(fair.snx * fair.sny)
	fair.surface.fill(Terrain.Surface.FAIRWAY)
	fair.meta = {}
	var far_pin := Vector3(0, 9999, 0)
	for club in Clubs.ALL:
		if club.id == "putter":
			continue
		var lo := 5.0
		var hi := 120.0
		var r: Dictionary
		for i in 30:
			var mid := (lo + hi) * 0.5
			var c: Dictionary = club.duplicate()
			c.speed = mid
			r = BallSim.simulate(fair, null, far_pin, Vector2.ZERO, Vector3(0, 0, BallSim.RADIUS),
				Clubs.launch_velocity(c, 1.0, Vector2(0, 1)), c.lift)
			if r.first_land.y < club.carry_m:
				lo = mid
			else:
				hi = mid
		print("%-7s carry %5.1f  speed %5.1f  (now %5.1f)  runs to %5.1f (%2.0f%%)  apex %4.1f" % [club.id, r.first_land.y,
			(lo + hi) * 0.5, club.speed, r.end.y, (r.end.y - r.first_land.y) / r.first_land.y * 100.0, r.apex])
	quit()
