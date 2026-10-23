extends SceneTree
## Draw calls through the opening flyover and the first aiming view, for checking what a hole costs:
##   xvfb-run godot --path golf/game --rendering-driver opengl3 --resolution 720x1560 --script res://tests/perf_intro.gd -- --hole=h01
var t := 0.0
var main: Node
var marks := [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.3]
var k := 0
func _initialize() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	root.add_child(main)
func _process(d: float) -> bool:
	t += d
	if k < marks.size() and t > marks[k]:
		_report("intro %.1fs" % marks[k])
		k += 1
	elif k == marks.size() and t > 8.5:
		_report("aim")
		quit()
	return false
func _report(what: String) -> void:
	var R := RenderingServer
	print("%s: draw calls %d, objects %d, primitives %d k" % [what,
		R.get_rendering_info(R.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME), R.get_rendering_info(R.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME),
		R.get_rendering_info(R.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME) / 1000])
