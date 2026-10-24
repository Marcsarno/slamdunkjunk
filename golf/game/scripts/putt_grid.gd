class_name PuttGrid
extends Node3D
## The putting read, the way the console golf games show it: a grid laid over the green whose beads
## run downhill (faster the steeper it falls), and a
## straight white line from the ball along the aim, as long as the putt. The beads tell you which way
## it will break (and the colour how hard: white to ~2.5%, yellow, red past ~4.5%); the line only shows
## where it's struck.

const STEP := 0.5             # m between the grid mesh's vertices (the lines themselves are 1 m apart)
const LIFT := 0.014           # m above the turf
const MAX_HALF := 22.0        # m: the grid covers at most this far either side of its middle
const LINE_WIDTH := 0.022     # m, half the aim line's width at the ball

var grid := MeshInstance3D.new()
var line := MeshInstance3D.new()
var _line_mesh := ImmediateMesh.new()
var _terrain: Terrain
var _ring := MeshInstance3D.new()          # where the putt stops
var _cup_glow := MeshInstance3D.new()      # the cup, lit when the putt would drop


func _ready() -> void:
	var sh := Shader.new()
	sh.code = """
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, fog_disabled, shadows_disabled;
varying vec3 wpos;
void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}
void fragment() {
	vec2 p = wpos.xz;
	// grid lines every metre, about the same few pixels wide near and far
	vec2 q = abs(fract(p + 0.5) - 0.5);
	float d = min(q.x, q.y);
	float w = max(0.012, fwidth(p.x) * 0.9);
	float gl = 1.0 - smoothstep(w * 0.5, w * 1.6, d);
	// a bead in each square, sliding downhill across it and fading in and out as it goes
	float s = COLOR.b;                                   // slope, 0 flat .. 1 at 8%
	vec2 down = normalize(COLOR.rg * 2.0 - 1.0 + vec2(0.0001));
	float t = fract(TIME * (0.2 + 1.6 * s));
	vec2 c = fract(p) - 0.5;
	float r = 0.055;
	float bead = (1.0 - smoothstep(r * 0.55, r, length(c - down * (t - 0.5) * 0.9))) * sin(t * 3.14159);
	bead *= smoothstep(0.06, 0.15, s);                    // dead flat: no beads, just the grid
	// white on an ordinary green (to ~2.5%), yellow where it falls faster, red where it's steep (4.5%+)
	vec3 col = mix(vec3(0.85, 0.94, 1.0), vec3(1.0, 0.84, 0.28), smoothstep(0.28, 0.4, s));
	col = mix(col, vec3(1.0, 0.34, 0.22), smoothstep(0.52, 0.66, s));
	ALBEDO = col;
	ALPHA = clamp(gl * 0.2 + bead * 0.9, 0.0, 1.0) * COLOR.a;
}
"""
	var gm := ShaderMaterial.new()
	gm.shader = sh
	grid.material_override = gm
	grid.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(grid)
	var lm := StandardMaterial3D.new()
	lm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	lm.vertex_color_use_as_albedo = true
	lm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	lm.no_depth_test = false
	lm.disable_fog = true
	lm.cull_mode = BaseMaterial3D.CULL_DISABLED
	# the stop ring and the cup's glow: flat discs drawn as rings by a little shader
	var rsh := Shader.new()
	rsh.code = """
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, fog_disabled, shadows_disabled;
uniform vec3 col : source_color = vec3(1.0);
uniform float fill = 0.0;
void fragment() {
	float r = length(UV - 0.5) * 2.0;
	float ring = smoothstep(0.72, 0.8, r) * (1.0 - smoothstep(0.9, 1.0, r));
	float pulse = 0.75 + 0.25 * sin(TIME * 5.0);
	ALBEDO = col;
	ALPHA = (ring + fill * (1.0 - smoothstep(0.0, 0.8, r)) * 0.6) * pulse;
}
"""
	for spec: Array in [[_ring, 0.34, Color(1.0, 1.0, 1.0), 0.0], [_cup_glow, 0.55, Color(0.4, 1.0, 0.6), 1.0]]:
		var mi: MeshInstance3D = spec[0]
		var pm := PlaneMesh.new()
		pm.size = Vector2.ONE * float(spec[1])
		mi.mesh = pm
		var mm := ShaderMaterial.new()
		mm.shader = rsh
		mm.set_shader_parameter("col", spec[2])
		mm.set_shader_parameter("fill", spec[3])
		mi.material_override = mm
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mi.visible = false
		add_child(mi)
	line.mesh = _line_mesh
	line.material_override = lm
	line.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(line)
	visible = false


## Lay the grid over the green round the ball and the pin (course coordinates).
func build(t: Terrain, ball: Vector2, pin: Vector2) -> void:
	_terrain = t
	var mid := (ball + pin) * 0.5
	var half := clampf(ball.distance_to(pin) * 0.5 + 5.0, 7.0, MAX_HALF)
	var n := int(ceil(half * 2.0 / STEP)) + 1
	var x0 := snappedf(mid.x - half, 1.0)
	var y0 := snappedf(mid.y - half, 1.0)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for j in n:
		for i in n:
			var x := x0 + i * STEP
			var y := y0 + j * STEP
			var nr := t.normal(x, y)
			var fall := Vector2(nr.x, nr.y)              # downhill, in course coordinates
			var slope := fall.length() / maxf(nr.z, 0.01)
			var down := fall.normalized() if fall.length() > 0.00001 else Vector2(1, 0)
			var surf := t.surface_at(x, y)
			var on := 1.0 if surf == Terrain.Surface.GREEN or surf == Terrain.Surface.FRINGE else 0.0
			# fade toward the edge of the patch
			var edge := minf(minf(i, n - 1 - i), minf(j, n - 1 - j)) * STEP
			on *= clampf(edge / 2.0, 0.0, 1.0)
			# downhill as a world direction (course y runs to world -z)
			st.set_color(Color(down.x * 0.5 + 0.5, -down.y * 0.5 + 0.5, clampf(slope / 0.08, 0.0, 1.0), on))
			st.add_vertex(Terrain.to_world(Vector3(x, y, t.height(x, y) + LIFT)))
	for j in n - 1:
		for i in n - 1:
			var a := j * n + i
			# split each square the same way the terrain mesh does, so the grid lies on it
			st.add_index(a)
			st.add_index(a + n + 1)
			st.add_index(a + 1)
			st.add_index(a)
			st.add_index(a + n)
			st.add_index(a + n + 1)
	grid.mesh = st.commit()
	visible = true


## The putt's roll as it will go (`pts`: course positions along it, the last where it stops): a line
## draped on the turf following the break, a ring where it stops, and the cup lit when it would drop.
func set_path(pts: Array, holed: bool, pin: Vector3) -> void:
	_line_mesh.clear_surfaces()
	_ring.visible = false
	_cup_glow.visible = holed
	if holed:
		_cup_glow.position = Terrain.to_world(pin) + Vector3(0, 0.03, 0)
	if _terrain == null or pts.size() < 2:
		return
	# resample every ~0.15 m so the line is smooth whatever the record rate
	var dense: Array[Vector2] = []
	for i in pts.size() - 1:
		var a2 := Vector2(pts[i].x, pts[i].y)
		var b2 := Vector2(pts[i + 1].x, pts[i + 1].y)
		var n := maxi(1, int(a2.distance_to(b2) / 0.15))
		for k in n:
			dense.append(a2.lerp(b2, float(k) / n))
	dense.append(Vector2(pts[-1].x, pts[-1].y))
	if dense.size() < 2:
		return
	var col := Color(0.55, 1.0, 0.7) if holed else Color(1.0, 1.0, 1.0)
	_line_mesh.surface_begin(Mesh.PRIMITIVE_TRIANGLE_STRIP)
	for i in dense.size():
		var c := dense[i]
		var dir := (dense[mini(i + 1, dense.size() - 1)] - dense[maxi(i - 1, 0)]).normalized()
		var right := Vector2(dir.y, -dir.x)
		var f := float(i) / (dense.size() - 1)
		var w := LINE_WIDTH * lerpf(1.1, 0.8, f)
		for sgn: float in [1.0, -1.0]:
			var p := c + right * w * sgn
			_line_mesh.surface_set_color(Color(col, lerpf(0.95, 0.7, f)))
			_line_mesh.surface_add_vertex(Terrain.to_world(Vector3(p.x, p.y, _terrain.height(p.x, p.y) + LIFT + 0.004)))
	_line_mesh.surface_end()
	if not holed:
		var e := dense[-1]
		_ring.position = Terrain.to_world(Vector3(e.x, e.y, _terrain.height(e.x, e.y) + LIFT + 0.02))
		_ring.visible = true


## The straight aim line, from the ball along `dir` for `length` metres, draped on the turf.
func set_line(ball: Vector2, dir: Vector2, length: float) -> void:
	_line_mesh.clear_surfaces()
	if _terrain == null or length < 0.05:
		return
	var right := Vector2(dir.y, -dir.x)
	var steps := clampi(int(length / 0.2), 2, 200)
	_line_mesh.surface_begin(Mesh.PRIMITIVE_TRIANGLE_STRIP)
	for k in steps + 1:
		var f := float(k) / steps
		var c := ball + dir * (0.12 + (length - 0.12) * f)
		var w := LINE_WIDTH * lerpf(1.0, 0.6, f)
		var a := lerpf(0.9, 0.55, f)
		for sgn: float in [1.0, -1.0]:
			var p := c + right * w * sgn
			_line_mesh.surface_set_color(Color(1.0, 1.0, 1.0, a))
			_line_mesh.surface_add_vertex(Terrain.to_world(Vector3(p.x, p.y, _terrain.height(p.x, p.y) + LIFT + 0.004)))
	_line_mesh.surface_end()
