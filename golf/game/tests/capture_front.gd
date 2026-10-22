extends SceneTree
## Screenshots of the splash and the clubhouse menu, for checking the look without a phone.
## Run: xvfb-run godot --path golf/game --rendering-driver opengl3 --resolution 1080x2340 --script res://tests/capture_front.gd -- --out=<dir>

var out := ""


func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out = a.trim_prefix("--out=")
	var front: Control = load("res://scenes/front.tscn").instantiate()
	root.add_child(front)
	await _wait(1.2)
	await _save("front_1_splash")
	front._on_play()
	await _wait(1.3)
	await _save("front_2_menu")
	front._soon(front.list.get_child(4), front.list.get_child(5))
	await _wait(0.3)
	await _save("front_3_soon")
	front._show_help(true)
	await _wait(0.8)
	await _save("front_4_help")
	quit()


func _wait(s: float) -> void:
	await create_timer(s).timeout


func _save(name: String) -> void:
	await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png(out.path_join(name + ".png"))
	print("saved ", name)
