extends Node
## Throws the ball at the nearest prop of each kind and prints which sound played:
##   godot --headless --path golf/game -- --hole=h07 --knock-probe
var main: Node
var done := false


func _ready() -> void:
	main = get_parent()


var t := 0.0


func _process(dt: float) -> void:
	t += dt
	if main.phase == main.Phase.INTRO and t > 1.0:
		main._press(Vector2(360, 900))
	if done or main.phase != main.Phase.AIM:
		return
	done = true
	var ball: Vector3 = main.ball
	main.sim = BallSim.new(main.terrain, main.obstacles, main.terrain.pin(), Vector2.ZERO)
	for want in [["cylinder", false], ["box", false], ["sphere", false], ["sphere", true]]:
		var best := {}
		var bd := INF
		for s: Dictionary in main.obstacles.shapes:
			if s.type == want[0] and bool(s.get("soft", false)) == want[1]:
				var d := Vector2(s.pos.x - ball.x, s.pos.y - ball.y).length()
				if d < bd:
					bd = d
					best = s
		if best.is_empty():
			print("knock ", want, " none on this hole")
			continue
		var c: Vector3 = best.pos
		var z := c.z + (float(best.h) * 0.5 if best.type == "cylinder" else (float(best.size[2]) * 0.5 if best.type == "box" else 0.0))
		var at := Vector3(c.x, c.y, z)
		var from := at + Vector3(-6.0, 0.0, 0.0)
		main.sim.launch(from, Vector3(14.0, 0.0, 0.05), 0.0)
		main._knock_at = -1.0
		var heard := "nothing"
		var before: int = Sfx._next
		for i in 120:
			main.sim.advance(1.0 / 60.0)
			main._prop_knocks()
			if Sfx._next != before:
				var p: AudioStreamPlayer = Sfx._players[(Sfx._next + Sfx._players.size() - 1) % Sfx._players.size()]
				heard = "%s at %.1f dB" % [p.stream.resource_path.get_file(), p.volume_db]
				break
		print("knock ", want, " -> ", heard)
	get_tree().quit()
