extends Node
## Prints the opening's camera path (course coords) through time, with how fast it moves and turns,
## so a jerk shows as a jump in speed or turn rate:
##   xvfb-run godot --path golf/game --rendering-driver opengl3 -- --hole=h01 --intro-path
var main: Node


func _ready() -> void:
	main = get_parent()
	await get_tree().process_frame
	var shots: Array = main._intro_shots()
	var pin: Vector3 = main.terrain.pin()
	print("path pin=", pin, " tee=", main.terrain.tee(), " length=", main._hole_length(), " path_end=", main.terrain.meta.path[-1])
	var prev_p := Vector3.INF
	var prev_yaw := 0.0
	var start := 0.0
	var dt := 0.1
	for sh: Dictionary in shots:
		var n := int(round(float(sh.time) / dt))
		for k in n:
			var u := float(k) / n
			var pose: Array = main._shot_pose(sh, main._ease(u, str(sh.get("ease", "linear"))))
			var p: Vector3 = pose[0]
			var l: Vector3 = pose[1]
			var yaw := rad_to_deg(atan2(l.x - p.x, l.y - p.y))
			var pitch := rad_to_deg(atan2(l.z - p.z, Vector2(l.x - p.x, l.y - p.y).length()))
			var spd := 0.0 if prev_p == Vector3.INF else p.distance_to(prev_p) / dt
			var turn := 0.0 if prev_p == Vector3.INF else wrapf(yaw - prev_yaw, -180.0, 180.0) / dt
			print("path t=%.1f pos=(%.0f,%.0f,%.1f) h=%.1f speed=%.0f yaw=%.0f turn=%.0f pitch=%.0f to_pin=%.0f" % [start + u * float(sh.time),
				p.x, p.y, p.z, p.z - main.terrain.height(p.x, p.y), spd, yaw, turn, pitch, Vector2(pin.x - p.x, pin.y - p.y).length()])
			prev_p = p
			prev_yaw = yaw
		start += float(sh.time)
	get_tree().quit()
