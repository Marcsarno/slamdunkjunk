class_name Cat
extends Node3D
## Midnight, the clubhouse cat, sitting beside the tee box: she turns up holding a golf ball, then
## sits, washes, naps and stretches while you play, and crouches to pounce when the club comes down.
## A camera-facing sprite like the golfer, with its feet on this node's origin.

const DIR := "res://assets/cast/cat_"
## How tall each pose stands, in meters (she's drawn at different sizes from pose to pose); a
## storybook cat, bigger than life so she reads on a phone.
const HEIGHTS := {
	"ball": 0.8, "sit": 0.8, "happy": 0.8, "groom": 0.74, "crouch": 0.58, "pounce": 0.67,
	"sleep": 0.45, "stretch": 0.64, "walk": 0.77, "walk2": 0.72,
}
const IDLE := ["sit", "sit", "groom", "happy", "sleep", "stretch"]

var mesh := MeshInstance3D.new()
var mat := StandardMaterial3D.new()
var _quads := {}
var _pose := ""
var _next := 3.0


func _ready() -> void:
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_FIXED_Y
	mat.billboard_keep_scale = true
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
	mat.alpha_scissor_threshold = 0.5
	mat.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	mat.albedo_color = Color(1.0, 0.97, 1.0)
	mesh.material_override = mat
	mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	add_child(mesh)
	pose("ball")
	_next = 5.0


func pose(name: String, hold := -1.0) -> void:
	_next = hold if hold > 0.0 else randf_range(4.0, 8.0)
	if name == _pose:
		return
	_pose = name
	if not _quads.has(name):
		var tex: Texture2D = load(DIR + name + ".png")
		var h: float = HEIGHTS[name]
		var w := h * tex.get_width() / tex.get_height()
		var q := QuadMesh.new()
		q.size = Vector2(w, h)
		q.center_offset = Vector3(0, h * 0.5, 0)
		_quads[name] = [q, tex]
	mesh.mesh = _quads[name][0]
	mat.albedo_texture = _quads[name][1]


## The club's coming down: she crouches, then pounces after the ball.
func watch_swing() -> void:
	pose("crouch", 0.7)
	get_tree().create_timer(0.7).timeout.connect(func(): pose("pounce", 2.5))


func _process(delta: float) -> void:
	_next -= delta
	if _next <= 0.0:
		var choices := IDLE.filter(func(p): return p != _pose)
		pose(choices[randi() % choices.size()])
