extends SceneTree
## Smoothness under uneven frame times (as phones give):  godot --headless --path golf/game --script res://tests/test_smooth.gd
## Plays the intro flyover and one full drive frame by frame with dt jittering 14-19 ms, and reports
## how evenly the camera turns and the ball moves: the largest frame-to-frame change in the camera's
## turn rate (deg/s) and in the ball's speed on screen (m/s), lower is smoother.

func _initialize() -> void:
	var main: Node = load("res://scenes/main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	main.set_process(false)
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	var dts := []
	for i in 2000:
		dts.append(rng.randf_range(0.014, 0.019))
	# intro
	var prev_dir := Vector3.ZERO
	var prev_rate := -1.0
	var worst_turn := 0.0
	var i := 0
	while main.phase == 0 and i < 600:
		var dt: float = dts[i]
		main._process(dt)
		if main.phase != 0:
			break   # the cut to the aim view is meant to be a cut
		var d: Vector3 = -main.cam.global_transform.basis.z
		if prev_dir != Vector3.ZERO:
			var rate := rad_to_deg(prev_dir.angle_to(d)) / dt
			if prev_rate >= 0.0 and i > 3:
				worst_turn = maxf(worst_turn, absf(rate - prev_rate))
			prev_rate = rate
		prev_dir = d
		i += 1
	print("intro: %d frames, worst change in camera turn rate %.1f deg/s" % [i, worst_turn])
	# one drive
	main._press(Vector2(360, 900))
	main._drag(Vector2(360, 1250), Vector2.ZERO)
	main._release()
	main.golfer.set_process(false)
	for k in 200:   # the swing frames play on their own; step them until the club meets the ball
		if main.phase == 4:
			break
		main.golfer._process(1.0 / 60.0)
	var prev_p := Vector3.INF
	var prev_v := -1.0
	var worst_ball := 0.0
	var worst_at := ""
	var n := 0
	while main.phase == 4 and n < 1200:
		var dt: float = dts[n]
		main._process(dt)
		if main.sim and main.sim.state == 0:
			var p: Vector3 = main.ball_mesh.position
			if prev_p != Vector3.INF:
				var v := p.distance_to(prev_p) / dt
				if prev_v >= 0.0 and n > 5:
					if absf(v - prev_v) > worst_ball:
						worst_at = "frame %d, t %.2f s, speed %.1f -> %.1f, z %.1f" % [n, main.sim.time, prev_v, v, main.sim.pos.z]
					worst_ball = maxf(worst_ball, absf(v - prev_v))
				prev_v = v
			prev_p = p
		n += 1
	print("drive: %d frames, worst frame-to-frame change in ball speed %.1f m/s (%s)" % [n, worst_ball, worst_at])
	quit()
