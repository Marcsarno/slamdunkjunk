extends SceneTree
## Screenshots of the splash and the clubhouse board's pages (and an eraser sweep mid-way), for
## checking the look without a phone.
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
	await _wait(0.75)
	await _save("front_2a_writing")
	await _wait(1.5)
	await _save("front_2_menu")
	front._go("holes")
	await _wait(0.25)
	await _save("front_3a_erasing")
	await _wait(2.4)
	await _save("front_3_holes")
	front._go("main")
	await _wait(2.6)
	front._go("balls")
	await _wait(2.4)
	front._pick_ball(front._ball_i + 1)
	await _wait(0.8)
	await _save("front_4_balls")
	front._pick_ball(front._ball_i - 1)
	front._go("main")
	await _wait(2.6)
	front._go("options")
	await _wait(2.4)
	await _save("front_5_options")
	front._go("main")
	await _wait(2.6)
	front._go("help")
	await _wait(2.6)
	await _save("front_6_help")
	quit()


func _wait(s: float) -> void:
	await create_timer(s).timeout


func _save(name: String) -> void:
	await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png(out.path_join(name + ".png"))
	print("saved ", name)
