extends SceneTree
## Memory at the menu and on a hole (graphics memory: textures and mesh buffers; and the engine's own
## heap), for checking a build stays inside what a phone's browser allows:
##   xvfb-run godot --path golf/game --rendering-driver opengl3 --resolution 780x1690 --script res://tests/mem_probe.gd -- [--hole=h03]
var t := 0.0
var stage := 0
var main: Node
var front: Node
var peak := 0.0


func _initialize() -> void:
	front = load("res://scenes/front.tscn").instantiate()
	root.add_child(front)


func _report(what: String) -> void:
	var P := Performance
	var mb := func(v: float) -> String: return "%.0f MB" % (v / 1048576.0)
	print("%-22s video %s (textures %s, buffers %s) | engine heap %s, peak %s" % [what,
		mb.call(P.get_monitor(P.RENDER_VIDEO_MEM_USED)), mb.call(P.get_monitor(P.RENDER_TEXTURE_MEM_USED)),
		mb.call(P.get_monitor(P.RENDER_BUFFER_MEM_USED)), mb.call(OS.get_static_memory_usage()),
		mb.call(OS.get_static_memory_peak_usage())])


func _process(d: float) -> bool:
	t += d
	match stage:
		0:
			if t > 3.0:
				_report("menu")
				front.queue_free()
				main = load("res://scenes/main.tscn").instantiate()
				root.add_child(main)
				stage = 1
				t = 0.0
		1:
			if t > 14.0:
				_report("hole, aiming")
				stage = 2
				t = 0.0
		2:
			if t > 6.0:
				_report("hole, 20 s in")
				quit()
	return false
