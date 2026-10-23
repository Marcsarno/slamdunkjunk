extends Node
## A still of a hole from a set spot, looking at another (course metres), after the hole has loaded:
## for checking a landmark or a view without playing to it.
##   xvfb-run godot --path golf/game --rendering-driver opengl3 --resolution 720x1560 \
##     -- --hole=h05 --look-from=60,330,6 --look-at=62,392,4 --look-out=<file.png>
var main: Node
var from := Vector3.ZERO
var at := Vector3.ZERO
var out := ""
var t := 0.0


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--look-from="):
			from = _v(a.trim_prefix("--look-from="))
		elif a.begins_with("--look-at="):
			at = _v(a.trim_prefix("--look-at="))
		elif a.begins_with("--look-out="):
			out = a.trim_prefix("--look-out=")
	main = get_parent()


func _v(s: String) -> Vector3:
	var p := s.split(",")
	return Vector3(float(p[0]), float(p[1]), float(p[2]))


func _process(delta: float) -> void:
	t += delta
	if main.phase == main.Phase.INTRO and t > 1.0:
		main._press(Vector2(360, 900))
	if main.phase == main.Phase.AIM and t > 3.0 and out != "":
		var f := out
		out = ""
		main.set_process(false)
		var tr: Terrain = main.terrain
		var w0 := Terrain.to_world(from + Vector3(0, 0, tr.height(from.x, from.y)))
		var w1 := Terrain.to_world(at + Vector3(0, 0, tr.height(at.x, at.y)))
		main.cam.global_position = w0
		main.cam.look_at(w1)
		main.cam.fov = 60.0
		main.golfer.visible = false
		for k in 4:
			await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(f)
		print("saved ", f)
		get_tree().quit()
