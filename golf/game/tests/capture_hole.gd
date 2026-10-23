extends Node
## Plays a hole to the bottom of the cup and saves a screenshot at each stage of every shot (aim, pull,
## swing, flight, landing, result; the putts; the card), for checking the whole course's look.
## Each shot aims at the pin and picks the power whose simulated finish is nearest it (driver off the
## tee aims down the fairway's middle instead, as a player would).
## Run: xvfb-run godot --path golf/game --rendering-driver opengl3 --resolution 720x1560 -- [--hole=h02] [--round] --capture-hole=<dir>

var main: Node
var out_dir := ""
var n := 0
var shot := 0
var t := 0.0
var stage := "wait_aim"
var landed := false
var round := false     # --round: press Next hole on each card and play on to the last hole
var burst := false     # --burst: a screenshot every frame through each swing, not just one
var pull_steps := false   # --pull-steps: on the first shot, screenshots at a quarter, half, ... of the pull


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
	DirAccess.make_dir_recursive_absolute(out_dir)
	main = get_parent()


func snap(name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png(out_dir.path_join("%s_%02d_s%d_%s.png" % [Round.current().id, n, shot + 1, name]))
	n += 1
	print("captured s%d %s phase=%d strokes=%d club=%s ball scale %.2f cam-ball %.1f m" % [shot + 1, name, main.phase, main.strokes, main.club.get("id", ""), main.ball_mesh.scale.x, main.cam.global_position.distance_to(main.ball_mesh.global_position)])


## The pull (0..1) whose simulated finish lands nearest `target`, along `aim`.
func best_pull(target: Vector3) -> float:
	var best := 0.5
	var best_d := INF
	for i in 41:
		var p := 0.07 + 0.93 * i / 40.0   # a person can pull as little as MIN_PULL
		var r := BallSim.simulate(main.terrain, main.obstacles, main.terrain.pin(), main.wind, main.ball,
			Clubs.launch_velocity(main.club, p, main.aim), main.club.lift)
		var d := Vector2(r.end.x - target.x, r.end.y - target.y).length()
		if r.state == BallSim.State.WATER or r.state == BallSim.State.OOB:
			d += 1000.0
		if d < best_d:
			best_d = d
			best = p
	return best


func _process(delta: float) -> void:
	t += delta
	match stage:
		"wait_aim":
			if main.phase == main.Phase.INTRO and t > 1.0:
				main._press(Vector2(360, 900))
			if main.phase == main.Phase.AIM and t > 1.2:
				var pin: Vector3 = main.terrain.pin()
				var to_pin := Vector2(pin.x - main.ball.x, pin.y - main.ball.y)
				var target := pin
				if main.club.id == "driver":
					# a full drive down the middle: ~22 path samples (~220 m) on from where the ball lies
					var path: Array = main.terrain.meta.path
					var here := Vector2(main.ball.x, main.ball.y)
					var near := 0
					for i in path.size():
						if Vector2(path[i][0], path[i][1]).distance_to(here) < Vector2(path[near][0], path[near][1]).distance_to(here):
							near = i
					var k: int = mini(near + 22, path.size() - 1)
					var far := Vector2(path[k][0], path[k][1])
					to_pin = far - Vector2(main.ball.x, main.ball.y)
					target = Vector3(far.x, far.y, 0)
				main.aim = to_pin.normalized()
				main.aim_goal = main.aim
				main._place_golfer_back()
				main._aim_cam()
				await snap("aim")
				var p := best_pull(target)
				main._press(Vector2(360, 1000))
				main._drag(Vector2(360, 1000 + p * main.get_viewport().get_visible_rect().size.y * main.PULL_FULL), Vector2.ZERO)
				main.aim = to_pin.normalized()
				main.aim_goal = main.aim
				main.pull = p
				main.pull_goal = p
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
				await snap("landing")
				stage = "done"
			elif main.phase == main.Phase.RESULT or main.phase == main.Phase.HOLED:
				stage = "done"
		"done":
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
