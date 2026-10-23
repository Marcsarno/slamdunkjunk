class_name Pal
extends Node3D
## One of the golfer's companions standing beside her on the course (the skeleton caddie, his cat):
## a camera-facing sprite like the golfer, its feet on this node's origin, that strikes a pose when
## something happens and drifts between its idle poses when nothing does. Each change of pose hops.

const DIR := "res://assets/cast/"

var prefix: String
var heights: Dictionary         # pose -> how tall it stands, meters (the art is drawn at varying sizes)
var idle: Array                 # poses it drifts between
var rest_pose: String

var mesh := MeshInstance3D.new()
var mat := StandardMaterial3D.new()
var _quads := {}
var _pose := ""
var _back_in := 0.0             # seconds until it goes back to resting (0: stays)
var _idle_in := 6.0


func _init(file_prefix: String, pose_heights: Dictionary, idle_poses: Array, rest: String) -> void:
	prefix = file_prefix
	heights = pose_heights
	idle = idle_poses
	rest_pose = rest


func _ready() -> void:
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_FIXED_Y
	mat.billboard_keep_scale = true
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
	mat.alpha_scissor_threshold = 0.5
	mat.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	mat.albedo_color = Color(0.97, 0.94, 1.0)     # moonlit, like the golfer
	mesh.material_override = mat
	mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	add_child(mesh)
	if _pose == "":
		pose(rest_pose)


func current() -> String:
	return _pose


## Strike a pose; after `hold` seconds (if over 0) it goes back to resting.
func pose(name: String, hold := 0.0) -> void:
	_back_in = hold
	_idle_in = randf_range(5.0, 9.0)
	if name == _pose:
		return
	_pose = name
	if not _quads.has(name):
		var tex: Texture2D = load(DIR + prefix + name + ".png")
		var h: float = heights[name]
		var q := QuadMesh.new()
		q.size = Vector2(h * tex.get_width() / tex.get_height(), h)
		q.center_offset = Vector3(0, h * 0.5, 0)
		_quads[name] = [q, tex]
	mesh.mesh = _quads[name][0]
	mat.albedo_texture = _quads[name][1]
	if is_inside_tree():
		var tw := create_tween()
		tw.tween_property(mesh, "position:y", 0.07, 0.09).set_ease(Tween.EASE_OUT)
		tw.tween_property(mesh, "position:y", 0.0, 0.14).set_ease(Tween.EASE_IN)


func rest() -> void:
	pose(rest_pose)


func _process(delta: float) -> void:
	if _back_in > 0.0:
		_back_in -= delta
		if _back_in <= 0.0:
			rest()
	elif _pose in idle:
		_idle_in -= delta
		if _idle_in <= 0.0:
			var others := idle.filter(func(p): return p != _pose)
			pose(others[randi() % others.size()])
