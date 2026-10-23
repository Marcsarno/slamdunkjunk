extends Node
## Plays a hole to the bottom of the cup and saves a screenshot at each stage of every shot (aim, pull,
## swing, flight, landing, result; the putts; the card), for checking the whole course's look.
## Each shot keeps the game's target, moved upwind by the drift the wind's ring shows, pulls to the
## mark and strikes it perfectly, as a good player would.
## Run: xvfb-run godot --path golf/game --rendering-driver opengl3 --resolution 720x1560 -- [--hole=h02] [--round] --capture-hole=<dir>

var main: Node
var out_dir := ""
var n := 0
var shot := 0
var t := 0.0
var stage := "wait_aim"
var landed := false
var aim_t := 0.0
var round := false     # --round: press Next hole on each card and play on to the last hole
var burst := false     # --burst: a screenshot every frame through each swing, not just one
var pull_steps := false   # --pull-steps: on the first shot, screenshots at a quarter, half, ... of the pull
var drag_test := false    # --drag-test: first shot, drag the target aside with a finger, land at the margin's edge
var side_test := false    # --side-test: first shot, slide the pulling finger a fifth of the screen right (aims left)


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--capture-hole="):
			out_dir = a.trim_prefix("--capture-hole=")
		if a == "--round":
			round = true
		if a == "--burst":
			burst = true
		if a == "--pull-steps":
			pull_steps = true
		if a == "--drag-test":
			drag_test = true
		if a == "--side-test":
			side_test = true
	DirAccess.make_dir_recursive_absolute(out_dir)
	main = get_parent()


func _touch(p: Vector2, down: bool) -> InputEventScreenTouch:
	var e := InputEventScreenTouch.new()
	e.index = 0
	e.position = p
	e.pressed = down
	return e


func _drag_ev(p: Vector2) -> InputEventScreenDrag:
	var e := InputEventScreenDrag.new()
	e.index = 0
	e.position = p
	return e


func snap(name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png(out_dir.path_join("%s_%02d_s%d_%s.png" % [Round.current().id, n, shot + 1, name]))
	n += 1
	print("captured s%d %s phase=%d strokes=%d club=%s ball scale %.2f cam-ball %.1f m" % [shot + 1, name, main.phase, main.strokes, main.club.get("id", ""), main.ball_mesh.scale.x, main.cam.global_position.distance_to(main.ball_mesh.global_position)])


func _process(delta: float) -> void:
	t += delta
	match stage:
		"wait_aim":
			if main.phase == main.Phase.INTRO and t > 1.0:
				main._press(Vector2(360, 900))
			if main.phase != main.Phase.AIM:
				aim_t = 0.0
			aim_t += delta
			if main.phase == main.Phase.AIM and aim_t > 0.6:     # the shot's preview has had a few frames
				# aim like a player: the game's target, moved upwind by as far as the wind's ring sits off it
				var b2 := Vector2(main.ball.x, main.ball.y)
				var pin2 := Vector2(main.terrain.pin().x, main.terrain.pin().y)
				print("aim s%d: pin %.1f m, target %.1f m, power %.3f, wind %s, wind lands %.1f m from target" % [shot + 1, b2.distance_to(pin2), b2.distance_to(main.target), main.full_power, main.wind, Vector2(main._wind_land.x, main._wind_land.y).distance_to(main.target) if main._wind_land != Vector3.INF else -1.0])
				if main._wind_land != Vector3.INF:
					var drift := Vector2(main._wind_land.x - main.target.x, main._wind_land.y - main.target.y)
					main._set_target(main.target - drift)
					print("   moved upwind: target %.1f m, power %.3f" % [b2.distance_to(main.target), main.full_power])
				t = 0.0
				stage = "settle"
		"settle":
			if t > 0.9 and not (drag_test and shot == 0):
				stage = "settling"
				await snap("aim")
				var vp := main.get_viewport().get_visible_rect().size
				main._press(Vector2(360, vp.y * 0.8))
				main._drag(Vector2(360, vp.y * 0.8 + main._pull_len * main.mark_pull()), Vector2.ZERO)
				main.spread_test = Vector2.ZERO      # dead centre of its margin
				t = 0.0
				stage = "pull"
			elif t > 0.9:
				# a finger on the target, dragged a fifth of the screen to the right
				stage = "dragging"
				var tw: Vector3 = Terrain.to_world(Vector3(main.target.x, main.target.y, main.terrain.height(main.target.x, main.target.y)))
				var sp: Vector2 = main.cam.unproject_position(tw)
				var before: Vector2 = main.target
				main._unhandled_input(_touch(sp, true))
				for k in 10:
					main._unhandled_input(_drag_ev(sp + Vector2(14.4 * (k + 1), 0)))
					await get_tree().process_frame
				await snap("drag")
				main._unhandled_input(_touch(sp + Vector2(144, 0), false))
				var after_sp: Vector2 = main.cam.unproject_position(Terrain.to_world(Vector3(main.target.x, main.target.y, main.terrain.height(main.target.x, main.target.y))))
				print("drag test: target moved %.1f m; finger at %s, target drawn at %s" % [before.distance_to(main.target), sp + Vector2(144, 0), after_sp])
				t = 0.0
				stage = "settle_after_drag"
		"settle_after_drag":
			if t > 1.0:
				stage = "settling"
				await snap("aim")
				var vp := main.get_viewport().get_visible_rect().size
				main._press(Vector2(360, vp.y * 0.8))
				main._drag(Vector2(360, vp.y * 0.8 + main._pull_len * main.mark_pull()), Vector2.ZERO)
				main.spread_test = Vector2(0.95, 0.0)   # at the right edge of its margin
				drag_test = false
				t = 0.0
				stage = "pull"
		"pull":
			if t > 0.4:
				if pull_steps and shot == 0:
					pull_steps = false
					stage = "steps"
					var goal: float = main.pull_goal
					for p in [0.0, 0.25, 0.5, 0.75, 1.0]:
						main.pull_goal = p
						await get_tree().create_timer(0.35).timeout
						await snap("pull%d" % roundi(p * 100))
					main.pull_goal = goal
					main.pull = goal
					stage = "pull"
				await snap("pull")
				if side_test and shot == 0:
					side_test = false
					stage = "side"
					var vp := main.get_viewport().get_visible_rect().size
					var aim0: Vector2 = main.aim
					for k in 10:
						main._drag(Vector2(360 + 14.4 * (k + 1), vp.y * 0.8 + main._pull_len * main.mark_pull()), Vector2.ZERO)
						await get_tree().process_frame
					await get_tree().create_timer(0.5).timeout
					await snap("side")
					# a slingshot: the finger slid right, so the shot should have turned left
					var r0 := Vector2(aim0.y, -aim0.x)
					print("side test: aim turned %.2f degrees to the %s" % [rad_to_deg(absf(aim0.angle_to(main.aim))),
						"left (right for a slingshot)" if main.aim.dot(r0) < 0.0 else "right (WRONG for a slingshot)"])
					stage = "pull"
				main._release()
				t = 0.0
				stage = "swing"
		"swing":
			if burst and t < 1.1:
				stage = "burst"
				await snap("swing")
				stage = "swing"
			elif t > (1.1 if burst else 0.2):
				if not burst:
					await snap("swing")
				t = 0.0
				landed = false
				stage = "fly"
		"fly":
			if main.phase == main.Phase.FLIGHT and main.sim:
				if main.sim.state == BallSim.State.FLYING and t > 1.6 and not landed and stage == "fly":
					await snap("flight")
					stage = "land"
				elif main.sim.state == BallSim.State.ROLLING and main.club.id == "putter" and t > 0.8:
					await snap("roll")
					stage = "done"
			if main.phase == main.Phase.RESULT or main.phase == main.Phase.HOLED:
				stage = "done"
		"land":
			if main.sim and main.sim.state != BallSim.State.FLYING:
				stage = "landed"
				await snap("landing")
				t = 0.0
				stage = "after_landing"
			elif main.phase == main.Phase.RESULT or main.phase == main.Phase.HOLED:
				stage = "done"
		"after_landing":
			if t > 0.35:
				stage = "done"
				await snap("landing_fx")
		"done":
			if main.phase == main.Phase.RESULT and main.sim:
				print("   shot s%d: landed %.1f m, finished %.1f m out (from %s)" % [shot + 1, Vector2(main.sim.first_land.x - main.last_ball.x, main.sim.first_land.y - main.last_ball.y).length() if main.sim.first_land != Vector3.INF else -1.0, Vector2(main.sim.pos.x - main.last_ball.x, main.sim.pos.y - main.last_ball.y).length(), main.last_ball])
			if main.phase == main.Phase.RESULT:
				await snap("result")
				shot += 1
				t = 0.0
				stage = "wait_aim"
				if shot > 9:
					get_tree().quit()
			elif main.phase == main.Phase.HOLED:
				t = 0.0
				stage = "holed"
		"holed":
			if t > 3.2:
				stage = "next"
				await snap("card")
				if round and Round.has_next():
					main._on_next()
				else:
					get_tree().quit()
