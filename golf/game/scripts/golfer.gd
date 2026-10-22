class_name Golfer
extends Node3D
## Brittany as a camera-facing sprite standing in the 3D world.
##
## Two views: "back" (seen from behind while aiming) and "face" (front-on, used for the swing
## cut). Frames come from assets/golfer/golfer.json; every frame is a quad whose foot anchor
## sits on this node's origin, so she never slides or changes size between frames.

signal contact
signal swing_finished

const HEIGHT_M := 1.55          # sole to top of hair in the address pose
const DIR := "res://assets/golfer/"

var sets: Dictionary
var current_set := ""
var mesh := MeshInstance3D.new()
var mat := StandardMaterial3D.new()
var _quads := {}                 # "set/frame" -> [QuadMesh, Texture2D]
var _down: Array = []
var _down_ms: Array = []
var _down_i := -1
var _down_t := 0.0
var _contact_i := -1


func _ready() -> void:
	sets = JSON.parse_string(FileAccess.get_file_as_string(DIR + "golfer.json"))
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_FIXED_Y
	mat.billboard_keep_scale = true
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
	mat.alpha_scissor_threshold = 0.5
	mat.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	mat.albedo_color = Color(0.93, 0.9, 1.0)
	mesh.material_override = mat
	mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	add_child(mesh)


func _quad(set_name: String, frame: int) -> Array:
	var key := "%s/%d" % [set_name, frame]
	if _quads.has(key):
		return _quads[key]
	var s: Dictionary = sets[set_name]
	var f: Dictionary = s.frames[str(frame)]
	var ps: float = HEIGHT_M / float(s.body_px)
	var w: float = f.size[0] * ps
	var h: float = f.size[1] * ps
	var q := QuadMesh.new()
	q.size = Vector2(w, h)
	q.center_offset = Vector3(w * 0.5 - f.anchor[0] * ps, f.anchor[1] * ps - h * 0.5, 0)
	var tex: Texture2D = load(DIR + f.file)
	_quads[key] = [q, tex]
	return _quads[key]


func show_frame(set_name: String, frame: int) -> void:
	var qt := _quad(set_name, frame)
	mesh.mesh = qt[0]
	mat.albedo_texture = qt[1]
	current_set = set_name


## Club head at address, relative to the foot anchor, in meters along the sprite's right/up.
func club_offset(set_name: String) -> Vector2:
	var s: Dictionary = sets[set_name]
	var f: Dictionary = s.frames[str(int(s.back[0]))]
	var ps: float = HEIGHT_M / float(s.body_px)
	if f.club_head == null:
		return Vector2(0.5, 0)
	return Vector2((f.club_head[0] - f.anchor[0]) * ps, (f.anchor[1] - f.club_head[1]) * ps)


## Backswing that follows the slingshot pull (0 = address, 1 = top).
func set_pull(set_name: String, pull: float) -> void:
	var back: Array = sets[set_name].back
	var i := clampi(int(round(pull * (back.size() - 1))), 0, back.size() - 1)
	show_frame(set_name, int(back[i]))
	_down_i = -1


func address(set_name: String) -> void:
	show_frame(set_name, int(sets[set_name].back[0]))
	_down_i = -1


func play_downswing(set_name: String) -> void:
	var s: Dictionary = sets[set_name]
	current_set = set_name
	_down = s.down
	_down_ms = s.down_ms
	_contact_i = int(s.contact)
	_down_i = 0
	_down_t = 0.0
	show_frame(set_name, int(_down[0]))
	if _contact_i == 0:
		contact.emit()


func _process(delta: float) -> void:
	if _down_i < 0:
		return
	_down_t += delta * 1000.0
	if _down_t < float(_down_ms[_down_i]):
		return
	_down_t = 0.0
	_down_i += 1
	if _down_i >= _down.size():
		_down_i = -1
		swing_finished.emit()
		return
	show_frame(current_set, int(_down[_down_i]))
	if _down_i == _contact_i:
		contact.emit()
