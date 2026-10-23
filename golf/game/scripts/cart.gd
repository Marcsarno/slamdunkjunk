class_name Cart
extends Node3D
## The caddie's golf cart, parked beside him: a camera-facing sprite drawn from 8 sides, showing each
## frame the side of the cart the camera is on, so it turns like a solid thing as the view moves.
## Its lantern throws a little warm light on the grass. Its front points along this node's -z.

const DIR := "res://assets/cast/"
## cart_0..7: the camera in front, front-left, left, back-left, back, back-right, right, front-right
const VIEWS := 8

var mesh := MeshInstance3D.new()
var mat := StandardMaterial3D.new()
var light := OmniLight3D.new()
var _quads: Array = []
var _view := -1


func _ready() -> void:
	var meta: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(DIR + "cart.json"))
	var mpp: float = meta.m_per_px
	for i in VIEWS:
		var tex: Texture2D = load(DIR + "cart_%d.png" % i)
		var q := QuadMesh.new()
		q.size = Vector2(tex.get_width(), tex.get_height()) * mpp
		q.center_offset = Vector3(0, q.size.y * 0.5, 0)
		_quads.append([q, tex])
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_FIXED_Y
	mat.billboard_keep_scale = true
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_DEPTH_PRE_PASS     # the lantern glows stay soft
	mat.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	mat.albedo_color = Color(0.95, 0.92, 1.0)
	mesh.material_override = mat
	mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mesh)
	light.light_color = Color(1.0, 0.6, 0.25)
	light.light_energy = 0.9
	light.omni_range = 4.0
	light.shadow_enabled = false
	light.position = Vector3(0, 1.8, 0)
	add_child(light)


func _process(_delta: float) -> void:
	var cam := get_viewport().get_camera_3d()
	if cam == null:
		return
	# where the camera is, round the cart: 0 straight ahead of it, counting toward its left
	var to_cam := cam.global_position - global_position
	var fwd := -global_basis.z
	var left := -global_basis.x
	var ang := atan2(to_cam.dot(left), to_cam.dot(fwd))
	var v := posmod(roundi(ang / (TAU / VIEWS)), VIEWS)
	if v != _view:
		_view = v
		mesh.mesh = _quads[v][0]
		mat.albedo_texture = _quads[v][1]
