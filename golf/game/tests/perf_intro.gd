extends SceneTree
## Draw calls and the game's own frame work (scripts, physics: not the GPU) through the opening flyover
## and the first aiming view, for checking what a hole costs:
##   xvfb-run godot --path golf/game --rendering-driver opengl3 --resolution 720x1560 --script res://tests/perf_intro.gd -- --hole=h01
var t := 0.0
var main: Node
var marks := [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
var k := 0
var worst := 0.0
var sum := 0.0
var n := 0
func _initialize() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	root.add_child(main)
func _process(d: float) -> bool:
	t += d
	var ms := Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0
	worst = maxf(worst, ms)
	sum += ms
	n += 1
	if k < marks.size() and t > marks[k]:
		_report("t %.0fs phase %d" % [marks[k], main.phase])
		k += 1
	elif k == marks.size() and t > 9.5:
		_report("aim")
		quit()
	return false
func _report(what: String) -> void:
	var R := RenderingServer
	print("%s: draw calls %d, primitives %d k, script/process avg %.1f ms, worst %.1f ms" % [what,
		R.get_rendering_info(R.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
		R.get_rendering_info(R.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME) / 1000, sum / maxi(n, 1), worst])
	worst = 0.0
	sum = 0.0
	n = 0
