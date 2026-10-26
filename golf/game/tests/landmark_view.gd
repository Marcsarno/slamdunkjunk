extends SceneTree
## A landmark on its own in the game's renderer, with its real materials (the patterned surfaces, the
## lit windows), under a moonlit night like the course's, from the front, the side and three-quarters.
## Export it first (tools/export_landmark.py <kind> game/tests/preview/<kind>.glb), import, then:
##   xvfb-run godot --path golf/game --rendering-driver opengl3 --resolution 900x1100 \
##     -s res://tests/landmark_view.gd -- --kind=chapel --out=<prefix>

var kind := "chapel"
var out := ""
var cam: Camera3D
var views := [["front", -90.0], ["side", 0.0], ["three_quarter", -45.0]]
var step := 0
var frames := 0
var centre := Vector3.ZERO
var size := 10.0


func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--kind="):
			kind = a.trim_prefix("--kind=")
		elif a.begins_with("--out="):
			out = a.trim_prefix("--out=")
	var world := Node3D.new()
	root.add_child(world)
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.1, 0.07, 0.2)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.32, 0.3, 0.5)
	env.ambient_light_energy = 0.9
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	var we := WorldEnvironment.new()
	we.environment = env
	world.add_child(we)
	var moon := DirectionalLight3D.new()
	moon.light_color = Color(0.62, 0.66, 1.0)
	moon.light_energy = 0.9
	moon.shadow_enabled = true
	moon.rotation_degrees = Vector3(-38, -150, 0)
	world.add_child(moon)
	var rim := DirectionalLight3D.new()                 # warm rim light from behind, as the concepts have
	rim.light_color = Color(1.0, 0.6, 0.3)
	rim.light_energy = 0.45
	rim.rotation_degrees = Vector3(-25, 20, 0)
	world.add_child(rim)
	var ground := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(120, 120)
	ground.mesh = pm
	var gm := StandardMaterial3D.new()
	gm.albedo_color = Color(0.1, 0.16, 0.07)
	ground.material_override = gm
	world.add_child(ground)
	var scene: Node3D = load("res://tests/preview/%s.glb" % kind).instantiate()
	world.add_child(scene)
	var mats := {
		"LandmarkSurface": _surface(),
		"LandmarkBody": _surface(),
		"LandmarkGlow": _unshaded(Color(1.0, 0.72, 0.32)),
		"LandmarkStained": _unshaded(Color(0.95, 0.2, 0.34)),
	}
	for node in scene.find_children("*", "MeshInstance3D", true, false):
		var mi := node as MeshInstance3D
		for i in mi.mesh.get_surface_count():
			var src := mi.mesh.surface_get_material(i)
			var n := src.resource_name if src else ""
			if mats.has(n):
				mi.set_surface_override_material(i, mats[n])
	_scene = scene
	_world = world
	cam = Camera3D.new()
	cam.fov = 40
	world.add_child(cam)


var _scene: Node3D
var _world: Node3D
var _ready_done := false


## Once the scene is in the tree: frame the model, light its front, aim the first view.
func _setup() -> void:
	var box := AABB()
	var first := true
	for node in _scene.find_children("*", "MeshInstance3D", true, false):
		var mi := node as MeshInstance3D
		var b := mi.global_transform * mi.get_aabb()
		box = b if first else box.merge(b)
		first = false
	centre = box.get_center()
	size = maxf(box.size.x, maxf(box.size.y, box.size.z))
	for x in [-8.0, 8.0]:                              # lanterns either side of the front
		var l := OmniLight3D.new()
		l.light_color = Color(1.0, 0.6, 0.25)
		l.light_energy = 2.0
		l.omni_range = 14.0
		_world.add_child(l)
		l.global_position = Vector3(centre.x + x, 1.5, box.end.z + 5.0)
	_place()


func _surface() -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = load("res://shaders/landmark.gdshader")
	m.set_shader_parameter("tex_stone", load("res://assets/textures/stone.png"))
	m.set_shader_parameter("tex_wood", load("res://assets/textures/wood.png"))
	return m


func _unshaded(c: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = c
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	return m


func _place() -> void:
	# glTF turns the model's -y front (Blender) into +z in Godot: the front view looks from +z
	var a := deg_to_rad(float(views[step][1]))
	var dist := size * 2.0
	var dir := Vector3(cos(a), 0.0, -sin(a))
	cam.position = centre + dir * dist + Vector3(0, size * 0.18, 0)
	cam.look_at(centre - Vector3(0, size * 0.04, 0))


func _process(_delta: float) -> bool:
	if not _ready_done:
		_ready_done = true
		_setup()
		return false
	frames += 1
	if frames < 8:
		return false
	var img := root.get_viewport().get_texture().get_image()
	img.save_png("%s_%s.png" % [out, views[step][0]])
	print("saved ", views[step][0])
	step += 1
	frames = 0
	if step >= views.size():
		return true
	_place()
	return false
