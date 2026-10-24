extends Node
## Scripted play-through that saves screenshots, for checking the look without a phone.
## Run: xvfb-run godot --path golf/game --rendering-driver opengl3 -- --capture=<dir> [--introonly | --intro-frames]

var main: Node
const INTRO_AT := [0.4, 1.0, 1.5, 1.9, 2.2, 2.6, 3.2, 4.0, 5.0, 6.2, 7.4, 8.4, 9.3]   # --intro-frames: when to snap (s into the opening)
var out_dir := ""
var t := 0.0
var step := 0
var shots_taken := 0


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--capture="):
			out_dir = a.trim_prefix("--capture=")
	DirAccess.make_dir_recursive_absolute(out_dir)
	main = get_parent()


func snap(name: String) -> void:
	var img := get_viewport().get_texture().get_image()
	img.save_png(out_dir.path_join("%02d_%s.png" % [shots_taken, name]))
	shots_taken += 1
	print("captured %s phase=%d cam=%s target=%s golfer=%s aim=%s" % [name, main.phase, main.cam.global_position, main.cam_target, main.golfer.position, main.aim])


func _process(delta: float) -> void:
	t += delta
	if "--intro-frames" in OS.get_cmdline_user_args():
		# the opening shot, a frame every so often through it
		if step < INTRO_AT.size() and main.phase == main.Phase.INTRO and main.phase_t >= INTRO_AT[step]:
			snap("intro_%.1f" % main.phase_t)
			step += 1
		elif step >= INTRO_AT.size() and main.phase != main.Phase.INTRO:
			t = 0.0
			step = -100
		elif step == -100 and t > 0.6:
			snap("after_intro")                 # where the opening hands over to the aim
			get_tree().quit()
		return
	match step:
		0:
			if t > 1.5:
				snap("intro")
				step += 1
				if "--introonly" in OS.get_cmdline_user_args():
					get_tree().quit()
		1:
			if t > 2.0:
				main._press(Vector2(360, 900))       # skip the intro
				step += 1
		2:
			if t > 3.0:
				snap("aim")
				if "--stills" in OS.get_cmdline_user_args():
					get_tree().quit()
					return
				main._press(Vector2(360, 800))       # start a pull
				step += 1
		3:
			if t > 3.3:
				main._drag(Vector2(330, 800 + 1280 * 0.28 * 0.92), Vector2(0, 50))
				step += 1
		4:
			if t > 3.8:
				snap("pull")
				main._release()
				step += 1
		5:
			if t > 3.95:
				snap("swing")
				step += 1
		6:
			if t > 4.6:
				snap("launch")
				step += 1
		7:
			if t > 6.0:
				snap("flight_mid")
				step += 1
		8:
			if t > 8.0:
				snap("flight_late")
				step += 1
		9:
			if main.phase == main.Phase.RESULT or t > 16.0:
				snap("result")
				step += 1
		10:
			if main.phase == main.Phase.AIM:
				t = 0.0
				step += 1
		11:
			if t > 0.8:
				snap("second_shot")
				get_tree().quit()
