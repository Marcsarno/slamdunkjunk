extends Node
## The lighting check: four fixed views of a hole, the same every run, so a change to the night's
## lighting can be judged frame against frame: the aim view, high over the tee looking down the hole,
## mid-fairway toward the green, and across the green.
##   xvfb-run godot --path golf/game --rendering-driver opengl3 --resolution 720x1560 \
##     -- --hole=h03 --light-set=<dir>
var main: Node
var out := ""
var t := 0.0
var done := false


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--light-set="):
			out = a.trim_prefix("--light-set=")
	DirAccess.make_dir_recursive_absolute(out)
	main = get_parent()


func _snap(name: String) -> void:
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	main.get_viewport().get_texture().get_image().save_png(out.path_join("%s_%s.png" % [Round.current().id, name]))


func _view(from: Vector3, at: Vector3, fov: float) -> void:
	main.cam.global_position = Terrain.to_world(from)
	main.cam.look_at(Terrain.to_world(at), Vector3.UP)
	main.cam.fov = fov
	await get_tree().create_timer(0.4).timeout


func _process(delta: float) -> void:
	t += delta
	if main.phase == main.Phase.INTRO and t > 1.0:
		main._press(Vector2(360, 900))
	if done or main.phase != main.Phase.AIM or t < 3.5:
		return
	done = true
	await _snap("1_aim")
	main.set_process(false)
	var tr: Terrain = main.terrain
	var tee := tr.tee()
	var mid: Vector3 = main._along_hole(0.55)
	var far: Vector3 = main._along_hole(0.8)
	var pin := tr.pin()
	var d := Vector2(mid.x - tee.x, mid.y - tee.y).normalized()
	await _view(Vector3(tee.x - d.x * 30.0, tee.y - d.y * 30.0, tee.z + 42.0), mid, 56.0)
	await _snap("2_high")
	var m2 := main._along_hole(0.6) as Vector3
	await _view(m2 + Vector3(0, 0, 4.0), Vector3(pin.x, pin.y, pin.z + 2.0), 60.0)
	await _snap("3_fairway")
	var g := Vector2(pin.x, pin.y) - Vector2(far.x - pin.x, far.y - pin.y).normalized() * -1.0
	var side := Vector2(pin.x - far.x, pin.y - far.y).normalized()
	var p := Vector2(pin.x, pin.y) - side * 14.0 + Vector2(side.y, -side.x) * 6.0
	await _view(Vector3(p.x, p.y, tr.height(p.x, p.y) + 2.2), pin + Vector3(0, 0, 0.5), 58.0)
	await _snap("4_green")
	get_tree().quit()
