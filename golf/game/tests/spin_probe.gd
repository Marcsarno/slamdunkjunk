extends SceneTree
## Each club's full swing onto a flat green: where it first lands, how far on it gets, and where it
## finishes (after any spin back). Run: godot --headless --script tests/spin_probe.gd


func flat(surface: int) -> Terrain:
	var t := Terrain.new()
	t.origin = Vector2(-200, -50)
	t.cell = 1.0
	t.nx = 401
	t.ny = 451
	t.heights.resize(t.nx * t.ny)
	t.heights.fill(0.0)
	t.surf_cell = 1.0
	t.snx = t.nx
	t.sny = t.ny
	t.surface.resize(t.snx * t.sny)
	t.surface.fill(surface)
	t.meta = {}
	return t


func _init() -> void:
	var g := flat(Terrain.Surface.GREEN)
	for c in Clubs.ALL:
		if c.id == "putter":
			continue
		for p in [1.0, 0.5]:
			var s := BallSim.new(g, null, Vector3(0, 900, 0))
			s.launch(Vector3(0, 0, BallSim.RADIUS), Clubs.launch_velocity(c, p, Vector2(0, 1)), c.lift)
			var furthest := 0.0
			var back0 := 0.0
			var t := 0.0
			while not s.is_done() and t < 25.0:
				s.advance(BallSim.DT)
				t += BallSim.DT
				if s.first_land != Vector3.INF:
					furthest = maxf(furthest, s.pos.y)
					if back0 == 0.0 and s.spin_back > 0.0:
						back0 = s.spin_back
			print("%-7s power %.1f: lands %.1f m, gets to %.1f m, finishes %.1f m  (spins back %.1f m, at %.2f m/s)" % [c.id, p,
				s.first_land.y, furthest, s.pos.y, furthest - s.pos.y, back0])
	quit()
