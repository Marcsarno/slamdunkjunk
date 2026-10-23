extends SceneTree
## What the ball does after it lands, club by club, on a flat fairway and green (for tuning):
##   godot --headless --path golf/game --script res://tests/probe_landing.gd

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
	for surf_name in ["FAIRWAY", "GREEN", "ROUGH"]:
		var t := flat(Terrain.Surface[surf_name])
		print("== landing on %s" % surf_name)
		for club in Clubs.ALL:
			if club.id == "putter":
				continue
			for pw in [1.0, 0.5]:
				var s := BallSim.new(t, null, Vector3(0, 9999, 0), Vector2.ZERO)
				s.launch(Vector3(0, 0, BallSim.RADIUS), Clubs.launch_velocity(club, pw, Vector2(0, 1)), club.lift)
				var landed_t := -1.0
				var land_v := Vector3.ZERO
				var last_b := 0
				var hops := []
				var peak := 0.0
				var hop_start := 0.0
				var roll_start := Vector3.INF
				var prev_state := s.state
				var prev_vel := s.vel
				while not s.is_done():
					prev_vel = s.vel
					s._step(BallSim.DT)
					if s.bounces > 0 and landed_t < 0.0:
						landed_t = s.time
						land_v = prev_vel
						hop_start = s.pos.y
					if s.bounces > last_b and last_b > 0:
						hops.append("%.2fm high/%.1fm long" % [peak, s.pos.y - hop_start])
						hop_start = s.pos.y
						peak = 0.0
					last_b = s.bounces
					if landed_t > 0.0 and s.state == BallSim.State.FLYING:
						peak = maxf(peak, s.pos.z)
					if s.state == BallSim.State.ROLLING and roll_start == Vector3.INF:
						if peak > 0.0:
							hops.append("%.2fm high/%.1fm long" % [peak, s.pos.y - hop_start])
						roll_start = s.pos
				var desc := rad_to_deg(atan2(-land_v.z, Vector2(land_v.x, land_v.y).length()))
				print("  %-6s %3d%%  carry %5.1f  lands at %4.1f m/s, %2.0f deg | hops %s | roll from %5.1f to %5.1f (%4.1f m) | %.1f s after landing" % [
					club.id, int(pw * 100), s.first_land.y, land_v.length(), desc, hops, roll_start.y, s.pos.y,
					s.pos.y - roll_start.y, s.time - landed_t])
	var g := flat(Terrain.Surface.GREEN)
	var putter := Clubs.by_id("putter")
	print("== putts")
	for pw in [0.05, 0.1, 0.25, 0.5, 1.0]:
		var r := BallSim.simulate(g, null, Vector3(0, 9999, 0), Vector2.ZERO, Vector3(0, 0, 0), Clubs.launch_velocity(putter, pw, Vector2(0, 1)), 0.0)
		print("  power %.2f: rolls %.1f m in %.1f s" % [pw, r.end.y, r.time])
	quit()
