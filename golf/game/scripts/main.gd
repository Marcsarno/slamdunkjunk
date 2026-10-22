extends Node3D
## Game flow for one hole: intro flyover -> aim -> slingshot pull -> swing cut -> ball chase
## -> result -> next shot ... -> holed. Course coords (x right, y down-range, z up) are used
## for all gameplay; Terrain.to_world() converts for anything drawn.

enum Phase { INTRO, AIM, PULL, SWING, FLIGHT, RESULT, HOLED }

const HOLE_DIR := "res://assets/holes/h01"
const YD := 1.0936
const AIM_ZONE := 0.30          # top share of the screen: drag sideways to turn
const PULL_FULL := 0.28         # pull distance (share of screen height) for 100% power
const FINE_AIM := 0.45          # radians of aim per screen-width of sideways pull
const MIN_PULL := 0.06
const FLIGHT_SPEED := 1.25      # flight plays a bit faster than real time
const INTRO_TIME := 5.0
const AIM_BACK := 4.4           # aim camera: meters behind the ball ...
const AIM_HEIGHT := 2.0         # ... and above it; fixed so she is the same size every shot

var terrain: Terrain
var obstacles: ObstacleGrid
var view := HoleView.new()
var golfer := Golfer.new()
var hud := Hud.new()
var cam := Camera3D.new()
var ball_mesh := MeshInstance3D.new()
var trail := MeshInstance3D.new()
var trail_mesh := ImmediateMesh.new()
var ring := MeshInstance3D.new()
var dots := MultiMeshInstance3D.new()

var phase := Phase.INTRO
var sim: BallSim
var ball := Vector3.ZERO
var last_ball := Vector3.ZERO
var aim := Vector2(0, 1)
var club: Dictionary
var strokes := 0
var par := 4
var wind := Vector2.ZERO
var pull := 0.0
var pull_start := Vector2.ZERO
var aim_at_pull := Vector2.ZERO
var aim_dragging := false
var preview := {}
var _preview_key := ""
var cam_pos := Vector3.ZERO
var cam_target := Vector3.ZERO
var cam_fov := 64.0
var phase_t := 0.0
var trail_pts: Array[Vector3] = []
var flight_dir := Vector2(0, 1)


func _ready() -> void:
	randomize()
	terrain = Terrain.load_hole(HOLE_DIR)
	view.build(HOLE_DIR, terrain)
	add_child(view)
	obstacles = ObstacleGrid.new(view.props.obstacles)
	par = int(terrain.meta.par)
	add_child(golfer)
	cam.keep_aspect = Camera3D.KEEP_WIDTH
	cam.near = 0.05
	cam.far = 2500.0
	add_child(cam)
	view.camera = cam
	_make_ball_visuals()
	add_child(hud)
	hud.club_pressed.connect(_cycle_club)
	hud.next_pressed.connect(_start_hole)
	var w: Dictionary = terrain.meta.wind
	wind = Vector2.from_angle(randf() * TAU) * randf_range(float(w.min), float(w.max))
	_start_hole()
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--capture="):
			add_child(load("res://tests/capture.gd").new())


# ---------------------------------------------------------------- hole / shot flow
func _start_hole() -> void:
	hud.hide_card()
	strokes = 0
	ball = terrain.tee() + Vector3(0, 0, BallSim.RADIUS)
	last_ball = ball
	hud.set_hole(int(terrain.meta.number), terrain.meta.name, par)
	trail_pts.clear()
	_setup_shot()
	phase = Phase.INTRO
	phase_t = 0.0
	hud.hint.text = "Tap to skip"
	hud.flash("Hole %d · Par %d\n%d yds" % [terrain.meta.number, par, roundi(_to_pin() * YD)], INTRO_TIME)


func _to_pin() -> float:
	var p := terrain.pin()
	return Vector2(p.x - ball.x, p.y - ball.y).length()


func _on_green() -> bool:
	var s := terrain.surface_at(ball.x, ball.y)
	return s == Terrain.Surface.GREEN or (s == Terrain.Surface.FRINGE and _to_pin() < 12.0)


func _setup_shot() -> void:
	club = Clubs.pick(_to_pin(), _on_green())
	aim = _default_aim()
	pull = 0.0
	_place_golfer_back()
	hud.set_stroke(strokes + 1, par)
	hud.set_distance(_to_pin() * YD)
	hud.set_club(club.label, club.carry_m * YD)
	hud.set_power(0, 0)
	hud.hint.text = "Pull down to swing · drag the sky to turn" if strokes == 0 else ""
	ball_mesh.visible = true
	_preview_key = ""
	trail_pts.clear()
	phase = Phase.AIM
	_aim_cam()
	cam_pos = _want_pos
	cam_target = _want_target
	cam_fov = _want_fov
	hud.fade_in()


func _default_aim() -> Vector2:
	var pin := terrain.pin()
	var to_pin := Vector2(pin.x - ball.x, pin.y - ball.y)
	var reach: float = club.carry_m * 0.95
	if club.id == "putter" or to_pin.length() <= reach * 1.1:
		return to_pin.normalized()
	# otherwise aim at the point on the fairway centerline about one club-length away
	var best := to_pin
	var best_err := INF
	var start_i := 0
	var closest := INF
	var path: Array = terrain.meta.path
	for i in path.size():
		var d := Vector2(path[i][0] - ball.x, path[i][1] - ball.y).length()
		if d < closest:
			closest = d
			start_i = i
	for i in range(start_i, path.size()):
		var v := Vector2(path[i][0] - ball.x, path[i][1] - ball.y)
		var err := absf(v.length() - reach)
		if err < best_err:
			best_err = err
			best = v
	return best.normalized()


func _cycle_club() -> void:
	if phase != Phase.AIM:
		return
	var ids := ["driver", "iron", "wedge", "putter"]
	club = Clubs.by_id(ids[(ids.find(club.id) + 1) % ids.size()])
	hud.set_club(club.label, club.carry_m * YD)
	_place_golfer_back()
	_preview_key = ""


func _right() -> Vector2:
	return Vector2(aim.y, -aim.x)


func _sprite_set(view_name: String) -> String:
	var s: String = club.sprite
	return ("back_" + s) if view_name == "back" else s


func _place_golfer_back() -> void:
	var set_name := _sprite_set("back")
	var off := golfer.club_offset(set_name)
	var g2 := Vector2(ball.x, ball.y) - _right() * off.x - aim * 0.12
	golfer.position = Terrain.to_world(Vector3(g2.x, g2.y, terrain.height(g2.x, g2.y)))
	golfer.address(set_name)


func _place_golfer_face() -> void:
	var set_name := _sprite_set("face")
	var off := golfer.club_offset(set_name)
	var g2 := Vector2(ball.x, ball.y) - aim * off.x - _right() * 0.45
	golfer.position = Terrain.to_world(Vector3(g2.x, g2.y, terrain.height(g2.x, g2.y)))


func _shoot() -> void:
	strokes += 1
	last_ball = ball
	hud.hint.text = ""
	hud.set_power(0, 0)
	_show_preview(false)
	phase = Phase.SWING
	phase_t = 0.0
	if golfer.contact.is_connected(_on_contact):
		golfer.contact.disconnect(_on_contact)
	golfer.contact.connect(_on_contact, CONNECT_ONE_SHOT)
	if club.id == "putter":
		golfer.play_downswing(_sprite_set("back"))
	else:
		_place_golfer_face()
		golfer.play_downswing(_sprite_set("face"))
		_cut_to_swing_cam()


func _on_contact() -> void:
	sim = BallSim.new(terrain, obstacles, terrain.pin(), wind)
	sim.launch(ball, Clubs.launch_velocity(club, pull, aim), club.lift)
	trail_pts.clear()
	flight_dir = aim
	phase = Phase.FLIGHT
	phase_t = 0.0


func _shot_done() -> void:
	phase = Phase.RESULT
	phase_t = 0.0
	var carried := Vector2(sim.pos.x - last_ball.x, sim.pos.y - last_ball.y).length() * YD
	match sim.state:
		BallSim.State.HOLED:
			phase = Phase.HOLED
			ball = sim.pos
			hud.flash(_score_name(strokes - par), 3.0)
			return
		BallSim.State.WATER:
			strokes += 1
			ball = last_ball
			hud.flash("Splash! +1 stroke")
		BallSim.State.OOB:
			strokes += 1
			ball = last_ball
			hud.flash("Out of bounds! +1 stroke")
		_:
			ball = sim.pos
			hud.flash("%s · %d yds" % [Terrain.SURFACE_LABELS[terrain.surface_at(ball.x, ball.y)], roundi(carried)])


func _score_name(diff: int) -> String:
	if strokes == 1:
		return "HOLE IN ONE!"
	match diff:
		-3: return "Albatross!"
		-2: return "Eagle!"
		-1: return "Birdie!"
		0: return "Par"
		1: return "Bogey"
		2: return "Double bogey"
	return "+%d" % diff


# ---------------------------------------------------------------- input
func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.button_index == MOUSE_BUTTON_LEFT:
		if e.pressed:
			_press(e.position)
		else:
			_release()
	elif e is InputEventMouseMotion and (e.button_mask & MOUSE_BUTTON_MASK_LEFT):
		_drag(e.position, e.relative)


func _press(p: Vector2) -> void:
	var vp := get_viewport().get_visible_rect().size
	match phase:
		Phase.INTRO:
			_end_intro()
		Phase.AIM:
			if p.y < vp.y * AIM_ZONE:
				aim_dragging = true
			else:
				phase = Phase.PULL
				pull_start = p
				aim_at_pull = aim
				pull = 0.0
				hud.hint.text = ""


func _drag(p: Vector2, rel: Vector2) -> void:
	var vp := get_viewport().get_visible_rect().size
	if aim_dragging:
		aim = aim.rotated(-rel.x / vp.x * 2.2).normalized()
		_place_golfer_back()
	elif phase == Phase.PULL:
		var d := p - pull_start
		pull = clampf(d.y / (vp.y * PULL_FULL), 0.0, 1.0)
		aim = aim_at_pull.rotated(d.x / vp.x * FINE_AIM).normalized()
		_place_golfer_back()
		golfer.set_pull(_sprite_set("back"), pull)


func _release() -> void:
	if aim_dragging:
		aim_dragging = false
		return
	if phase == Phase.PULL:
		if pull < MIN_PULL:
			phase = Phase.AIM
			pull = 0.0
			golfer.address(_sprite_set("back"))
			hud.set_power(0, 0)
		else:
			_shoot()


# ---------------------------------------------------------------- per frame
func _process(delta: float) -> void:
	phase_t += delta
	match phase:
		Phase.INTRO:
			_intro_cam()
			if phase_t >= INTRO_TIME:
				_end_intro()
		Phase.AIM, Phase.PULL:
			_aim_cam()
			_update_preview()
		Phase.SWING:
			pass
		Phase.FLIGHT:
			var was_flying := sim.state == BallSim.State.FLYING
			sim.advance(delta * (FLIGHT_SPEED if was_flying else 1.0))
			if sim.state == BallSim.State.FLYING or sim.state == BallSim.State.ROLLING:
				var hv := Vector2(sim.vel.x, sim.vel.y)
				if hv.length() > 1.0:
					flight_dir = flight_dir.lerp(hv.normalized(), 0.2).normalized()
			_chase_cam(delta)
			if sim.is_done():
				_shot_done()
		Phase.RESULT:
			_chase_cam(delta)
			if phase_t > 1.8:
				_setup_shot()
		Phase.HOLED:
			_chase_cam(delta)
			if phase_t > 2.4 and not hud.card.visible:
				hud.show_card("%s\n\n%d strokes · par %d" % [_score_name(strokes - par), strokes, par])
	_update_ball_visual()
	_update_wind_hud()
	_apply_cam(delta)


func _end_intro() -> void:
	phase = Phase.AIM
	hud.flash("", 0.01)
	hud.hint.text = "Pull down to swing · drag the sky to turn"
	_aim_cam()
	cam_pos = _aim_cam_pos()
	cam_target = _aim_cam_target()


# ---------------------------------------------------------------- camera
var _want_pos := Vector3.ZERO
var _want_target := Vector3.ZERO
var _want_fov := 64.0
var _cam_rate := 8.0


func _aim_cam_pos() -> Vector3:
	var a := Vector3(aim.x, aim.y, 0)
	if club.id == "putter":
		return Terrain.to_world(ball - a * 3.0 + Vector3(0, 0, 1.3))
	return Terrain.to_world(ball - a * (AIM_BACK - pull * 0.8) + Vector3(0, 0, AIM_HEIGHT - pull * 0.3))


func _aim_cam_target() -> Vector3:
	var a := Vector3(aim.x, aim.y, 0)
	if club.id == "putter":
		var t := ball + a * 5.0
		return Terrain.to_world(Vector3(t.x, t.y, terrain.height(t.x, t.y)))
	var t2 := ball + a * 40.0
	return Terrain.to_world(Vector3(t2.x, t2.y, terrain.height(t2.x, t2.y) + 2.5))


func _aim_cam() -> void:
	_want_pos = _aim_cam_pos()
	_want_target = _aim_cam_target()
	_want_fov = 66.0
	_cam_rate = 9.0


func _cut_to_swing_cam() -> void:
	var g := Terrain.to_course(golfer.position)
	var a := Vector3(aim.x, aim.y, 0)
	var r := Vector3(_right().x, _right().y, 0)
	_want_pos = Terrain.to_world(g + r * 3.6 + a * 0.5 + Vector3(0, 0, 1.0))
	_want_target = Terrain.to_world(g + a * 0.55 + Vector3(0, 0, 0.8))
	_want_fov = 52.0
	cam_pos = _want_pos
	cam_target = _want_target
	cam_fov = _want_fov
	_cam_rate = 20.0


func _chase_cam(_delta: float) -> void:
	if sim == null:
		return
	var b := sim.pos
	var dir := Vector3(flight_dir.x, flight_dir.y, 0)
	var side := Vector3(flight_dir.y, -flight_dir.x, 0)
	var p: Vector3
	if sim.state == BallSim.State.FLYING:
		# swing out to the side mid-flight so the course slides past in depth, then tuck back in
		var air := clampf(sim.time / 4.5, 0.0, 1.0)
		var lateral := 9.0 * sin(air * PI)
		p = b - dir * 12.0 + side * lateral + Vector3(0, 0, 4.0 + 3.0 * sin(air * PI))
		_cam_rate = 3.2 if sim.time > 0.4 else 1.6
		_want_fov = 60.0
	else:
		p = b - dir * 6.5 + Vector3(0, 0, 2.6)
		_cam_rate = 2.5
	p.z = maxf(p.z, terrain.height(p.x, p.y) + 1.5)
	_want_pos = Terrain.to_world(p)
	_want_target = Terrain.to_world(b + sim.vel * 0.12 + Vector3(0, 0, 0.3))


func _intro_cam() -> void:
	var path: Array = terrain.meta.path
	var u := clampf(phase_t / INTRO_TIME, 0.0, 1.0)
	u = u * u * (3.0 - 2.0 * u)
	var f := u * (path.size() - 1)
	var i := mini(int(f), path.size() - 2)
	var k := f - i
	var p2 := Vector2(path[i][0], path[i][1]).lerp(Vector2(path[i + 1][0], path[i + 1][1]), k)
	var j := mini(i + 4, path.size() - 1)
	var ahead := Vector2(path[j][0], path[j][1])
	if j == path.size() - 1:
		ahead = Vector2(terrain.pin().x, terrain.pin().y)
	var h := terrain.height(p2.x, p2.y)
	cam_pos = Terrain.to_world(Vector3(p2.x, p2.y, h + 26.0 - 8.0 * u))
	cam_target = Terrain.to_world(Vector3(ahead.x, ahead.y, terrain.height(ahead.x, ahead.y)))
	cam_fov = 62.0
	_want_pos = cam_pos
	_want_target = cam_target
	_want_fov = cam_fov


func _apply_cam(delta: float) -> void:
	var k := 1.0 - exp(-_cam_rate * delta)
	cam_pos = cam_pos.lerp(_want_pos, k)
	cam_target = cam_target.lerp(_want_target, minf(1.0, k * 1.6))
	cam_fov = lerpf(cam_fov, _want_fov, k)
	cam.fov = cam_fov
	if cam_pos.distance_to(cam_target) > 0.01:
		cam.look_at_from_position(cam_pos, cam_target, Vector3.UP)


# ---------------------------------------------------------------- ball, trail, preview
func _make_ball_visuals() -> void:
	var sm := SphereMesh.new()
	sm.radius = BallSim.RADIUS
	sm.height = BallSim.RADIUS * 2.0
	sm.radial_segments = 16
	sm.rings = 8
	ball_mesh.mesh = sm
	var bm := StandardMaterial3D.new()
	bm.albedo_color = Color(0.95, 0.95, 0.92)
	bm.emission_enabled = true
	bm.emission = Color(0.6, 0.65, 0.7)
	bm.emission_energy_multiplier = 0.4
	ball_mesh.material_override = bm
	add_child(ball_mesh)

	trail.mesh = trail_mesh
	var tm := StandardMaterial3D.new()
	tm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	tm.vertex_color_use_as_albedo = true
	tm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	tm.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	tm.cull_mode = BaseMaterial3D.CULL_DISABLED
	trail.material_override = tm
	trail.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(trail)

	var q := QuadMesh.new()
	q.size = Vector2(0.075, 0.075)
	ring.mesh = q
	var rm := StandardMaterial3D.new()
	rm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	rm.albedo_texture = _marker_texture()
	rm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	rm.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	rm.fixed_size = true
	rm.no_depth_test = true
	rm.disable_fog = true
	rm.render_priority = 10
	ring.material_override = rm
	ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(ring)

	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	var dm := SphereMesh.new()
	dm.radius = 1.0
	dm.height = 2.0
	dm.radial_segments = 8
	dm.rings = 4
	mm.mesh = dm
	mm.instance_count = 40
	mm.visible_instance_count = 0
	dots.multimesh = mm
	var dmat := StandardMaterial3D.new()
	dmat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	dmat.albedo_color = Color(1.0, 0.85, 0.5)
	dmat.disable_fog = true
	dots.material_override = dmat
	dots.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(dots)
	_show_preview(false)


func _marker_texture() -> ImageTexture:
	var n := 128
	var img := Image.create(n, n, false, Image.FORMAT_RGBA8)
	for y in n:
		for x in n:
			var d := Vector2(x - n * 0.5 + 0.5, y - n * 0.5 + 0.5).length() / (n * 0.5)
			var ring_a := clampf(1.0 - absf(d - 0.78) / 0.11, 0.0, 1.0)
			var dot_a := clampf(1.0 - d / 0.16, 0.0, 1.0)
			var glow := clampf(1.0 - d, 0.0, 1.0) * 0.25
			var a := maxf(maxf(ring_a, dot_a), glow)
			img.set_pixel(x, y, Color(1.0, 0.82 - 0.2 * ring_a, 0.45 - 0.2 * ring_a, a))
	return ImageTexture.create_from_image(img)


func _update_ball_visual() -> void:
	var b := sim.pos if (phase == Phase.FLIGHT or phase == Phase.RESULT or phase == Phase.HOLED) and sim else ball
	var w := Terrain.to_world(b)
	ball_mesh.position = w
	var d := cam.global_position.distance_to(w)
	ball_mesh.scale = Vector3.ONE * maxf(1.0, d * 0.0045 / BallSim.RADIUS)
	ball_mesh.visible = phase != Phase.HOLED
	# trail
	if phase == Phase.FLIGHT and sim.state == BallSim.State.FLYING:
		trail_pts.append(w)
		if trail_pts.size() > 90:
			trail_pts.remove_at(0)
	elif trail_pts.size() > 0:
		trail_pts.remove_at(0)
		if trail_pts.size() > 0:
			trail_pts.remove_at(0)
	trail_mesh.clear_surfaces()
	if trail_pts.size() < 2:
		return
	trail_mesh.surface_begin(Mesh.PRIMITIVE_TRIANGLE_STRIP)
	var cp := cam.global_position
	for i in trail_pts.size():
		var p := trail_pts[i]
		var t := (trail_pts[mini(i + 1, trail_pts.size() - 1)] - trail_pts[maxi(i - 1, 0)]).normalized()
		var side := t.cross(cp - p).normalized()
		var f := float(i) / (trail_pts.size() - 1)
		var width := cp.distance_to(p) * 0.0022 * (0.3 + 0.7 * f)
		var c := Color(1.0, 0.7 + 0.25 * f, 0.4, f * 0.55)
		trail_mesh.surface_set_color(c)
		trail_mesh.surface_add_vertex(p + side * width)
		trail_mesh.surface_set_color(c)
		trail_mesh.surface_add_vertex(p - side * width)
	trail_mesh.surface_end()


func _show_preview(on: bool) -> void:
	ring.visible = on and club.get("id", "") != "putter"
	dots.multimesh.visible_instance_count = dots.multimesh.visible_instance_count if on else 0


func _update_preview() -> void:
	var p := pull if phase == Phase.PULL else 1.0
	var key := "%.3f|%.4f|%.4f|%s" % [p, aim.x, aim.y, club.id]
	if key == _preview_key:
		_place_ring()
		return
	_preview_key = key
	var putt: bool = club.id == "putter"
	var r := BallSim.simulate(terrain, obstacles, terrain.pin(), Vector2.ZERO, ball,
		Clubs.launch_velocity(club, p, aim), club.lift, 0.06, not putt)
	preview = r
	var pts: Array = r.points
	var mm := dots.multimesh
	var count := 0
	if putt:
		# putts: the first stretch of the actual roll, so the break shows but the finish doesn't
		var show_n := int(pts.size() * 0.4)
		var step := maxi(1, int(ceil(float(show_n) / mm.instance_count)))
		for i in range(0, show_n, step):
			if count >= mm.instance_count:
				break
			mm.set_instance_transform(count, Transform3D(Basis().scaled(Vector3.ONE * 0.025), Terrain.to_world(pts[i]) + Vector3(0, 0.02, 0)))
			count += 1
	elif r.first_land != Vector3.INF:
		# full shots: dashes along the ground under the flight path, ball to landing spot
		var land: Vector3 = r.first_land
		var span := Vector2(land.x - ball.x, land.y - ball.y)
		var n_dash := mini(mm.instance_count, maxi(4, int(span.length() / 6.0)))
		for i in range(1, n_dash):
			var t := float(i) / n_dash
			var p2 := Vector2(ball.x, ball.y) + span * t
			var g := Vector3(p2.x, p2.y, terrain.height(p2.x, p2.y) + 0.08)
			var s := 0.05 + span.length() * t * 0.004
			mm.set_instance_transform(count, Transform3D(Basis().scaled(Vector3(s, s * 0.35, s)), Terrain.to_world(g)))
			count += 1
	var n := count
	mm.visible_instance_count = count
	ring.visible = not putt and r.first_land != Vector3.INF
	var dist_m: float = Vector2(r.end.x - ball.x, r.end.y - ball.y).length() if putt \
		else Vector2(r.first_land.x - ball.x, r.first_land.y - ball.y).length()
	if phase == Phase.PULL:
		hud.set_power(pull, dist_m * YD)
	_place_ring()
	if n == 0:
		pass


func _place_ring() -> void:
	if not ring.visible or preview.is_empty():
		return
	var fl: Vector3 = preview.first_land
	ring.position = Terrain.to_world(fl) + Vector3(0, 0.4, 0)
	var m := ring.material_override as StandardMaterial3D
	m.albedo_color = Color(1, 1, 1, 1.0) if phase == Phase.PULL else Color(1, 1, 1, 0.55)


func _update_wind_hud() -> void:
	var cam_fwd := -cam.global_basis.z
	var fwd2 := Vector2(cam_fwd.x, -cam_fwd.z)
	if fwd2.length() < 0.01:
		return
	var rel := fwd2.normalized().angle_to(wind.normalized()) if wind.length() > 0.01 else 0.0
	hud.set_wind(wind.length(), -rel)
