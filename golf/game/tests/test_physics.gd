extends SceneTree
## Headless physics checks:  godot --headless --path golf/game --script res://tests/test_physics.gd

var failures := 0


func check(cond: bool, msg: String) -> void:
	print(("  ok   " if cond else "  FAIL ") + msg)
	if not cond:
		failures += 1


func flat(surface: int, slope := Vector2.ZERO) -> Terrain:
	var t := Terrain.new()
	t.origin = Vector2(-200, -50)
	t.cell = 1.0
	t.nx = 401
	t.ny = 451
	t.heights.resize(t.nx * t.ny)
	for j in t.ny:
		for i in t.nx:
			t.heights[j * t.nx + i] = (t.origin.x + i) * slope.x + (t.origin.y + j) * slope.y
	t.surf_cell = 1.0
	t.snx = t.nx
	t.sny = t.ny
	t.surface.resize(t.snx * t.sny)
	t.surface.fill(surface)
	t.meta = {}
	return t


func _init() -> void:
	var fair := flat(Terrain.Surface.FAIRWAY)
	var far_pin := Vector3(0, 9999, 0)
	print("club carries (flat fairway, no wind):")
	for club in Clubs.ALL:
		if club.id == "putter":
			continue
		var v := Clubs.launch_velocity(club, 1.0, Vector2(0, 1))
		var r := BallSim.simulate(fair, null, far_pin, Vector2.ZERO, Vector3(0, 0, BallSim.RADIUS), v, club.lift)
		var carry: float = r.first_land.y
		var total: float = r.end.y
		print("    %-7s carry %5.1f m  total %5.1f m  apex %4.1f m  time %4.1f s" % [club.id, carry, total, r.apex, r.time])
		check(absf(carry - club.carry_m) < club.carry_m * 0.05, "%s full carry near %d m" % [club.id, club.carry_m])
		check(total - carry > 1.0 and total - carry < carry * 0.15, "%s rolls out %.0f m" % [club.id, total - carry])
		var half := BallSim.simulate(fair, null, far_pin, Vector2.ZERO, Vector3(0, 0, BallSim.RADIUS),
			Clubs.launch_velocity(club, 0.5, Vector2(0, 1)), club.lift)
		var ratio: float = half.first_land.y / carry
		check(ratio > 0.42 and ratio < 0.68, "%s half pull carries %.0f%% of full" % [club.id, ratio * 100])

	print("putting:")
	var green := flat(Terrain.Surface.GREEN)
	var putter := Clubs.by_id("putter")
	var p := BallSim.simulate(green, null, far_pin, Vector2.ZERO, Vector3(0, 0, 0), Clubs.launch_velocity(putter, 1.0, Vector2(0, 1)), 0.0)
	print("    full putt rolls %.1f m" % p.end.y)
	check(p.state == BallSim.State.STOPPED and absf(p.end.y - putter.carry_m) < 3.0, "full putt ~%d m and stops" % putter.carry_m)
	var holed := BallSim.simulate(green, null, Vector3(0, 6, 0), Vector2.ZERO, Vector3(0, 0, 0),
		Clubs.launch_velocity(putter, 0.33, Vector2(0, 1)), 0.0)
	check(holed.state == BallSim.State.HOLED, "firm-enough putt at the cup drops (state %d, end %s)" % [holed.state, holed.end])
	var slope_g := flat(Terrain.Surface.GREEN, Vector2(0.03, 0.0))
	var s := BallSim.simulate(slope_g, null, far_pin, Vector2.ZERO, Vector3(0, 0, slope_g.height(0, 0)),
		Clubs.launch_velocity(putter, 0.5, Vector2(0, 1)), 0.0)
	check(s.end.x < -0.5, "putt across a 3%% slope breaks downhill (x = %.2f)" % s.end.x)

	print("wind:")
	var iron := Clubs.by_id("iron")
	var headwind := BallSim.simulate(fair, null, far_pin, Vector2(0, -6), Vector3(0, 0, BallSim.RADIUS),
		Clubs.launch_velocity(iron, 1.0, Vector2(0, 1)), iron.lift)
	var cross := BallSim.simulate(fair, null, far_pin, Vector2(6, 0), Vector3(0, 0, BallSim.RADIUS),
		Clubs.launch_velocity(iron, 1.0, Vector2(0, 1)), iron.lift)
	print("    6 m/s headwind carry %.0f m, crosswind drift %.1f m" % [headwind.first_land.y, cross.first_land.x])
	check(headwind.first_land.y < iron.carry_m * 0.93, "headwind shortens the shot")
	check(cross.first_land.x > 4.0, "crosswind pushes the ball sideways")

	print("obstacles:")
	var grid := ObstacleGrid.new([{"type": "box", "pos": [0, 20, 0], "size": [0.8, 0.2, 1.2], "rot": 0.0}])
	var bounce := BallSim.simulate(fair, grid, far_pin, Vector2.ZERO, Vector3(0, 0, 0.3),
		Vector3(0, 12, 0.5), 0.0)
	check(bounce.end.y < 20.0, "ball driven into a tombstone bounces back (end y %.1f)" % bounce.end.y)

	print("hole 1 data:")
	var t := Terrain.load_hole("res://assets/holes/h01")
	var pr: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/holes/h01/props.json"))
	var obs := ObstacleGrid.new(pr.obstacles)
	var tee := t.tee()
	check(t.surface_at(tee.x, tee.y) == Terrain.Surface.TEE, "tee sits on the tee box")
	var pin := t.pin()
	check(t.surface_at(pin.x, pin.y) == Terrain.Surface.GREEN, "pin sits on the green")
	var drv := Clubs.by_id("driver")
	var drive := BallSim.simulate(t, obs, pin, Vector2.ZERO, tee + Vector3(0, 0, BallSim.RADIUS),
		Clubs.launch_velocity(drv, 1.0, Vector2(0.0, 1.0)), drv.lift)
	print("    straight drive ends at %s on %s" % [drive.end, Terrain.SURFACE_LABELS[t.surface_at(drive.end.x, drive.end.y)]])
	check(drive.state == BallSim.State.STOPPED, "drive comes to rest")
	check(not (t.surface_at(drive.end.x, drive.end.y) in [Terrain.Surface.OOB, Terrain.Surface.WATER]), "drive finishes in play")

	print("\n%s" % ("ALL PASSED" if failures == 0 else "%d FAILED" % failures))
	quit(1 if failures else 0)
