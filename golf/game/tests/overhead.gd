extends Node
## A still of the whole hole from straight above (map-like: north up, the play area framed), to set
## beside the layout concepts:
##   xvfb-run godot --path golf/game --rendering-driver opengl3 --resolution 1000x1000 \
##     -- --hole=h05 --overhead=<dir>
var main: Node
var out := ""
var t := 0.0
var done := false


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--overhead="):
			out = a.trim_prefix("--overhead=")
	DirAccess.make_dir_recursive_absolute(out)
	main = get_parent()


func _process(delta: float) -> void:
	t += delta
	if main.phase == main.Phase.INTRO and t > 1.0:
		main._press(Vector2(360, 900))
	if done or main.phase != main.Phase.AIM or t < 3.5:
		return
	done = true
	main.set_process(false)
	main.hud.visible = false
	var tr: Terrain = main.terrain
	# the play area: the line of play, the tee and the pin, with room round them
	var lo := Vector2(INF, INF)
	var hi := Vector2(-INF, -INF)
	for p: Array in tr.meta.path:
		lo = lo.min(Vector2(p[0], p[1]))
		hi = hi.max(Vector2(p[0], p[1]))
	for q: Vector3 in [tr.tee(), tr.pin()]:
		lo = lo.min(Vector2(q.x, q.y))
		hi = hi.max(Vector2(q.x, q.y))
	var mid := (lo + hi) * 0.5
	var span := maxf(hi.x - lo.x, hi.y - lo.y) + 70.0
	var top := Terrain.to_world(Vector3(mid.x, mid.y, tr.height(mid.x, mid.y) + 400.0))
	main.view.moon_light.shadow_enabled = false
	main.cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	main.cam.size = span
	main.cam.far = 2000.0
	main.cam.look_at_from_position(top, top + Vector3.DOWN, Terrain.to_world(Vector3(0, 1, 0)) - Terrain.to_world(Vector3.ZERO))
	for i in 6:
		await RenderingServer.frame_post_draw
	main.get_viewport().get_texture().get_image().save_png(out.path_join("%s.png" % Round.current().id))
	get_tree().quit()
