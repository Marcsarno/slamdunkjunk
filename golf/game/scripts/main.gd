extends Node3D
## Game flow for one hole: intro flyover -> aim -> slingshot pull -> swing cut -> ball chase
## -> result -> next shot ... -> holed. Course coords (x right, y down-range, z up) are used
## for all gameplay; Terrain.to_world() converts for anything drawn.
##
## Aiming works like the phone golf games: each shot starts with a target on the best landing spot
## (where the roll ends at the pin, when it's in reach); drag it anywhere in the club's range. Pulling
## back to the gauge's mark lands on the target (no wind); past it is extra power at a risk. While
## pulling, a needle sweeps: let go in its middle for a perfect strike, off it and the shot starts off
## line and bends. The wind is the aiming game: a faint ring shows where it carries a perfect shot.

enum Phase { INTRO, AIM, PULL, SWING, FLIGHT, RESULT, HOLED }

const YD := 1.0936
const PULL_ZONE := 0.62         # touches starting below this share of the screen height pull back to
                                # swing; above it they drag the target
const PULL_FULL := 0.26         # pull distance (share of screen height) to the target mark: a full shot
const OVERPOWER := 1.1          # pulling past the mark adds up to this much power, and speeds the needle
const MAGNET := 0.04            # within this of the mark, the pull settles exactly on it
const EASE := 20.0              # power follows the finger at this rate (1/s), smoothing touch jitter
const MIN_PULL := 0.06
const PERFECT := 0.12           # half-width of the needle's perfect middle (the needle runs -1..1)
const MISS_AIM := 0.035         # radians a shot starts off line with the needle at its end ...
const MISS_CURVE := 0.0004      # ... and the side spin it gets (BallSim curve), less toward the middle
const NEEDLE_PERIOD := {"driver": 1.0, "iron": 1.2, "wedge": 1.4}   # seconds per sweep and back
const HINT := "Drag the target · pull down from the bottom to swing"
const FLIGHT_SPEED := 1.25      # flight plays a bit faster than real time
const INTRO_TIME := 5.0
const AIM_BACK := 3.7           # aim camera: meters behind the ball ...
const AIM_HEIGHT := 2.0         # ... and above it; fixed so she is the same size every shot
const SWING_HOLD := 0.75        # seconds the swing view holds after contact, for her follow-through

var terrain: Terrain
var obstacles: ObstacleGrid
var view := HoleView.new()
var fx := Fx.new()
var golfer := Golfer.new()
var hud := Hud.new()
var cam := Camera3D.new()
var ball_mesh := MeshInstance3D.new()
var trail := MeshInstance3D.new()
var trail_mesh := ImmediateMesh.new()
var ring := MeshInstance3D.new()           # where the wind carries a perfect full shot: flat, mint
var dots := MultiMeshInstance3D.new()      # the flight arc and the roll after it
var target_ring := MeshInstance3D.new()    # the target, flat on the ground
var target_label := Label3D.new()

var phase := Phase.INTRO
var sim: BallSim
var ball := Vector3.ZERO
var last_ball := Vector3.ZERO
var aim := Vector2(0, 1)
var club: Dictionary
var strokes := 0
var par := 4
var wind := Vector2.ZERO
var target := Vector2.ZERO      # course xy where the shot is planned to land: the target marker
var full_power := 1.0           # club power (as Clubs.launch_velocity takes it) that carries to the target
var pull := 0.0                 # 0 .. OVERPOWER: 1 is the target mark
var pull_goal := 0.0            # where the finger says the pull should be; pull eases toward it
var pull_start := Vector2.ZERO
var needle := 0.0               # accuracy needle while pulling, -1..1 (0: perfect)
var needle_test := INF          # a test can fix the needle at this value on release
var _needle_t := 0.0
var _shot_needle := 0.0
var target_dragging := false
var _drag_hit0 := Vector2.ZERO  # target dragging: the ground under the finger at press, and the target then
var _target0 := Vector2.ZERO
var _power_scale := 1.0         # last solved power against distance / club carry, for estimates mid-drag
var preview := {}               # this pull's flight, no wind
var _preview_key := ""
var _target_key := ""
var _wind_land := Vector3.INF   # where the wind carries a full, perfect shot
var _carry_m := 0.0             # the preview shot's carry, and where it stops after rolling (< 0: not yet
var _finish_m := -1.0           # worked out; that waits until the finger holds still, to spare the phone)
var _finish_warn := ""
var cam_pos := Vector3.ZERO
var cam_target := Vector3.ZERO
var cam_fov := 64.0
var phase_t := 0.0
var trail_pts: Array[Vector3] = []
var flight_dir := Vector2(0, 1)
var _landed_fx := false         # the first landing's puff and thud have been shown


func _ready() -> void:
	randomize()
	terrain = Terrain.load_hole(Round.dir())
	view.build(Round.dir(), terrain)
	add_child(view)
	obstacles = ObstacleGrid.new(view.props.obstacles)
	add_child(fx)
	view.ambience.lightning.connect(func(k: float):
		Sfx.play_after(randf_range(0.4, 1.8), "thunder", lerpf(-12.0, -3.0, k), randf_range(0.85, 1.1)))
	par = int(terrain.meta.par)
	add_child(golfer)
	cam.keep_aspect = Camera3D.KEEP_WIDTH
	cam.near = 0.05
	cam.far = 2500.0
	add_child(cam)
	view.camera = cam
	_make_ball_visuals()
	add_child(hud)
	Music.set_in_play(true)
	Music.start()
	hud.club_pressed.connect(_cycle_club)
	hud.next_pressed.connect(_on_next)
	hud.menu_pressed.connect(func():
		get_tree().set_meta("front_menu", true)   # straight back to the clubhouse board, no splash
		get_tree().change_scene_to_file("res://scenes/front.tscn"))
	var w: Dictionary = terrain.meta.wind
	wind = Vector2.from_angle(randf() * TAU) * randf_range(float(w.min), float(w.max))
	_start_hole()
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--capture="):
			add_child(load("res://tests/capture.gd").new())
		elif a.begins_with("--capture-hole="):
			add_child(load("res://tests/capture_hole.gd").new())


# ---------------------------------------------------------------- hole / shot flow
## The card's first button: on to the next hole of the round, or this one again after the last.
func _on_next() -> void:
	if Round.has_next() or Round.scores.size() > 1:
		# on to the next hole, or after a round of several holes a new one from hole 1
		if Round.has_next():
			Round.advance()
		else:
			Round.start(0)
		hud.fade_out_then(func(): get_tree().change_scene_to_file("res://scenes/main.tscn"))
	else:
		_start_hole()


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
	hud.flash("Hole %d · Par %d\n%s" % [terrain.meta.number, par, _dist_text(_to_pin(), false)], INTRO_TIME)


func _to_pin() -> float:
	var p := terrain.pin()
	return Vector2(p.x - ball.x, p.y - ball.y).length()


func _on_green() -> bool:
	var s := terrain.surface_at(ball.x, ball.y)
	return s == Terrain.Surface.GREEN or (s == Terrain.Surface.FRINGE and _to_pin() < 12.0)


func _setup_shot() -> void:
	club = Clubs.pick(_to_pin(), _on_green())
	pull = 0.0
	pull_goal = 0.0
	target_dragging = false
	_set_target(_default_target())
	hud.set_stroke(strokes + 1, par)
	hud.set_distance(_dist_text(_to_pin(), club.id == "putter"))
	hud.set_club(club.label, club.carry_m * YD)
	hud.hide_gauge()
	hud.hint.text = HINT if strokes == 0 else ""
	ball_mesh.visible = true
	_preview_key = ""
	trail_pts.clear()
	phase = Phase.AIM
	_target_cam()
	cam_pos = _want_pos
	cam_target = _want_target
	cam_fov = _want_fov
	hud.fade_in()


## A distance as a golfer says it: feet on the green, yards elsewhere.
func _dist_text(m: float, feet: bool) -> String:
	if feet:
		var ft := maxi(1, roundi(m * 3.281))
		return "%d ft" % ft
	var yd := maxi(1, roundi(m * YD))
	return "1 yd" if yd == 1 else "%d yds" % yd


## Where a shot should land to start with: for a putt, the hole; with the pin in reach, the spot the
## roll carries on from to finish at the pin; otherwise a full club out along the fairway's centre line.
func _default_target() -> Vector2:
	var b := Vector2(ball.x, ball.y)
	var pin2 := Vector2(terrain.pin().x, terrain.pin().y)
	if club.id == "putter":
		return pin2
	var reach: float = club.carry_m
	if b.distance_to(pin2) <= reach:
		return _landing_to_stop_at(pin2)
	var best := (pin2 - b).normalized() * reach
	var best_err := INF
	var start_i := 0
	var closest := INF
	var path: Array = terrain.meta.path
	for i in path.size():
		var d := Vector2(path[i][0], path[i][1]).distance_to(b)
		if d < closest:
			closest = d
			start_i = i
	for i in range(start_i, path.size()):
		var v := Vector2(path[i][0], path[i][1]) - b
		var err := absf(v.length() - reach * 0.97)
		if err < best_err:
			best_err = err
			best = v
	return b + best


## The landing spot short of `spot` that the roll (no wind) carries on from to finish there.
func _landing_to_stop_at(spot: Vector2) -> Vector2:
	var b := Vector2(ball.x, ball.y)
	var d := b.distance_to(spot)
	var dir := (spot - b).normalized()
	var land := d
	for i in 3:
		var r := BallSim.simulate(terrain, obstacles, terrain.pin(), Vector2.ZERO, ball,
			Clubs.launch_velocity(club, _power_for(land, dir), dir), club.lift)
		if r.state == BallSim.State.HOLED:
			break
		var f := Vector2(r.end.x, r.end.y).distance_to(b)
		if absf(f - d) < 0.5:
			break
		land = clampf(land - (f - d), d * 0.6, d)
	return b + dir * land


## How far a club's swing at power `p` carries along `dir` with no wind (a putt: how far it rolls).
## INF when a putt drops: it would have rolled at least as far as it needed to.
func _carry(p: float, dir: Vector2) -> float:
	var r := BallSim.simulate(terrain, obstacles, terrain.pin(), Vector2.ZERO, ball,
		Clubs.launch_velocity(club, p, dir), club.lift, 0.0, true)
	if r.state == BallSim.State.HOLED:
		return INF
	var land: Vector3 = r.first_land if r.first_land != Vector3.INF else r.end
	return Vector2(land.x - ball.x, land.y - ball.y).length()


## The power that carries `d` meters along `dir` with no wind. Carry is close to proportional to
## power (Clubs), so a few proportional corrections settle it whatever the slope.
func _power_for(d: float, dir: Vector2) -> float:
	var p := clampf(d / club.carry_m, 0.005, 1.2)
	for i in 5:
		var c := _carry(p, dir)
		if c == INF or c < 0.05:
			break
		var np := clampf(p * d / c, 0.005, 1.2)
		if absf(np - p) < 0.002:
			p = np
			break
		p = np
	return p


## Put the target at `t` (kept within the club's reach) and face it. `exact` solves the power that
## carries there; mid-drag an estimate from the last solve keeps the finger's frame cheap.
func _set_target(t: Vector2, exact := true) -> void:
	var b := Vector2(ball.x, ball.y)
	var v := t - b
	var reach: float = club.carry_m
	if v.length() > reach:
		v = v.normalized() * reach
	var shortest := 0.05 if club.id == "putter" else 0.5
	if v.length() < shortest:
		v = (v.normalized() if v.length() > 0.001 else aim) * shortest
	target = b + v
	aim = v.normalized()
	_place_golfer_back()
	if exact:
		full_power = _power_for(v.length(), aim)
		if full_power > 1.0:
			# uphill or blocked: a full swing doesn't get there, so the target comes back to where it does
			full_power = 1.0
			var reach_now := _carry(1.0, aim)
			if reach_now != INF:
				target = b + aim * reach_now
		_power_scale = full_power / maxf(v.length() / club.carry_m, 0.001)
	else:
		full_power = clampf(v.length() / club.carry_m * _power_scale, 0.02, 1.0)
	_preview_key = ""
	_target_key = ""
	_wind_land = Vector3.INF


func _cycle_club() -> void:
	if phase != Phase.AIM:
		return
	var ids := ["driver", "iron", "wedge", "putter"]
	club = Clubs.by_id(ids[(ids.find(club.id) + 1) % ids.size()])
	hud.set_club(club.label, club.carry_m * YD)
	hud.set_distance(_dist_text(_to_pin(), club.id == "putter"))
	_set_target(_default_target())


func _right() -> Vector2:
	return Vector2(aim.y, -aim.x)


func _sprite_set(view_name: String) -> String:
	var s: String = club.sprite
	return golfer.back_set(s) if view_name == "back" else golfer.face_set(s)


func _place_golfer_back() -> void:
	var set_name := _sprite_set("back")
	var off := golfer.club_offset(set_name)
	var g2 := Vector2(ball.x, ball.y) - _right() * off.x - aim * 0.12
	golfer.position = Terrain.to_world(Vector3(g2.x, g2.y, terrain.height(g2.x, g2.y)))
	golfer.address(set_name)


func _place_golfer_face() -> void:
	var set_name := _sprite_set("face")
	var off := golfer.club_offset(set_name)
	var g2 := Vector2(ball.x, ball.y) - aim * off.x - _right() * golfer.ball_ahead(set_name)
	golfer.position = Terrain.to_world(Vector3(g2.x, g2.y, terrain.height(g2.x, g2.y)))


func _shoot() -> void:
	strokes += 1
	last_ball = ball
	hud.hint.text = ""
	hud.hide_gauge()
	# the strike: where the needle stood when she let go (putts have no needle)
	_shot_needle = 0.0 if club.id == "putter" else (needle_test if needle_test != INF else needle)
	if absf(_shot_needle) <= PERFECT:
		_shot_needle = 0.0
		if club.id != "putter":
			hud.flash("Perfect!", 1.0)
			Sfx.play("perfect", -6.0)
	if club.id != "putter":
		Sfx.play_after(0.08, "swing", -4.0, randf_range(0.95, 1.05))
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
	# off the needle's middle the shot starts off line and bends the same way (+: right)
	var miss := signf(_shot_needle) * (absf(_shot_needle) - PERFECT) / (1.0 - PERFECT) if _shot_needle != 0.0 else 0.0
	var dir := aim.rotated(-miss * MISS_AIM)
	sim.launch(ball, Clubs.launch_velocity(club, full_power * pull, dir), club.lift, miss * MISS_CURVE)
	var hit: String = {"driver": "hit_driver", "putter": "putt"}.get(club.id, "hit_iron")
	Sfx.play(hit, lerpf(-14.0, 0.0, clampf(full_power * pull, 0.0, 1.0)) if club.id == "putter" else -1.0)
	_landed_fx = false
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
			Sfx.play("cup")
			Sfx.play_after(0.3, "holed", -3.0)
			fx.holed(Terrain.to_world(terrain.pin()), HoleView._col(view.theme.get("wisp_color"), Color(1.0, 0.6, 0.25)))
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
			if club.id == "putter":
				hud.flash("%s to go" % _dist_text(_to_pin(), true))
			else:
				hud.flash("%s · %s" % [Terrain.SURFACE_LABELS[terrain.surface_at(ball.x, ball.y)], _dist_text(carried / YD, false)])


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
## One finger at a time, read as touches (a mouse arrives as touches too: emulate_touch_from_mouse).
## Phones give each finger any id, so the first finger down is followed, whatever its index. Buttons
## get their taps as mouse clicks (emulate_mouse_from_touch); a touch that lands on one is theirs.
var _finger := -1


func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventScreenTouch:
		if e.pressed and _finger == -1 and not hud.blocks(e.position):
			_finger = e.index
			_press(e.position)
		elif not e.pressed and e.index == _finger:
			_finger = -1
			_release()
	elif e is InputEventScreenDrag and e.index == _finger:
		_drag(e.position, e.relative)


func _press(p: Vector2) -> void:
	var vp := get_viewport().get_visible_rect().size
	match phase:
		Phase.INTRO:
			_end_intro()
		Phase.AIM:
			if p.y > vp.y * PULL_ZONE:
				phase = Phase.PULL
				pull_start = p
				pull_goal = 0.0
				_needle_t = randf() * 10.0      # the needle starts anywhere in its sweep
				hud.hint.text = ""
			else:
				var hit: Variant = _ground_at(p)
				if hit != null:
					target_dragging = true
					_drag_hit0 = hit
					_target0 = target


func _drag(p: Vector2, _rel: Vector2) -> void:
	var vp := get_viewport().get_visible_rect().size
	if target_dragging:
		var hit: Variant = _ground_at(p)
		if hit != null:
			_set_target(_target0 + (hit - _drag_hit0), false)
	elif phase == Phase.PULL:
		var g := clampf((p - pull_start).y / (vp.y * PULL_FULL), 0.0, OVERPOWER)
		if absf(g - 1.0) < MAGNET:
			if absf(pull_goal - 1.0) >= MAGNET:
				Input.vibrate_handheld(18)      # a click onto the mark
				Sfx.play("click", -6.0)
			g = 1.0
		pull_goal = g


## The ground point (course xy) under a screen point, by walking the camera ray down to the terrain.
func _ground_at(p: Vector2) -> Variant:
	var o := cam.project_ray_origin(p)
	var n := cam.project_ray_normal(p)
	if n.y > -0.005:
		return null
	var t := 0.0
	var step := 1.0
	for i in 800:
		var c := Terrain.to_course(o + n * (t + step))
		if c.z <= terrain.height(c.x, c.y):
			var lo := t
			var hi := t + step
			for k in 14:
				var mid := (lo + hi) * 0.5
				var m := Terrain.to_course(o + n * mid)
				if m.z <= terrain.height(m.x, m.y):
					hi = mid
				else:
					lo = mid
			var g := Terrain.to_course(o + n * hi)
			return Vector2(g.x, g.y)
		t += step
		step = maxf(1.0, t * 0.02)
		if t > 3000.0:
			break
	return null


## Power follows the finger smoothly (touch reports arrive unevenly), and her backswing with it.
func _ease_toward_finger(delta: float) -> void:
	if pull == pull_goal:
		return
	pull = lerpf(pull, pull_goal, 1.0 - exp(-delta * EASE))
	if absf(pull - pull_goal) < 0.002:
		pull = pull_goal
	if phase == Phase.PULL:
		golfer.set_pull(_sprite_set("back"), minf(pull, 1.0))


func _release() -> void:
	if target_dragging:
		target_dragging = false
		_set_target(target)             # solve the power exactly where it was left
		return
	if phase == Phase.PULL:
		if pull_goal < MIN_PULL:
			# let go without pulling: no shot
			phase = Phase.AIM
			pull = 0.0
			pull_goal = 0.0
			golfer.address(_sprite_set("back"))
			hud.hide_gauge()
		else:
			pull = pull_goal   # the shot is what the finger said, even if the ease hadn't caught up
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
			_ease_toward_finger(delta)
			if phase == Phase.PULL:
				_aim_cam()
				_sweep_needle(delta)
			elif not target_dragging:     # the view holds still under a dragging finger
				_target_cam()
			_update_preview()
		Phase.SWING:
			pass
		Phase.FLIGHT:
			var was_flying := sim.state == BallSim.State.FLYING
			# a ball trickling up to the cup goes into slow motion: will it drop?
			var to_cup := Vector2(sim.pos.x - terrain.pin().x, sim.pos.y - terrain.pin().y).length()
			var slow := 0.45 if sim.state == BallSim.State.ROLLING and to_cup < 2.2 and sim.vel.length() > 0.15 else 1.0
			sim.advance(delta * (FLIGHT_SPEED if was_flying else slow))
			if not _landed_fx and sim.first_land != Vector3.INF:
				_landed_fx = true
				var surf := terrain.surface_at(sim.first_land.x, sim.first_land.y)
				var tint := HoleView._col(view.theme.get("water_glow"), Color(0.55, 0.75, 1.0)).lerp(Color(0.6, 0.8, 1.0), 0.3)
				fx.land(Terrain.to_world(sim.first_land), surf, tint)
				match surf:
					Terrain.Surface.WATER: Sfx.play("splash", -2.0)
					Terrain.Surface.SAND: Sfx.play("land_sand", -3.0)
					_: Sfx.play("land_grass", -4.0, randf_range(0.9, 1.1))
			if sim.state == BallSim.State.FLYING or sim.state == BallSim.State.ROLLING:
				var hv := Vector2(sim.vel.x, sim.vel.y)
				if hv.length() > 1.0:
					flight_dir = flight_dir.lerp(hv.normalized(), 0.2).normalized()
			# full swings: stay on her through the follow-through, then go after the ball
			if club.id == "putter" or phase_t > SWING_HOLD:
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
				Round.record(strokes)
				var detail := "%d strokes on a par %d" % [strokes, par]
				if Round.scores.size() > 1:
					detail += "\nRound: %s after %d" % [Round.to_par_text(), Round.scores.size()]
				hud.show_card(_score_name(strokes - par), detail, "Next hole" if Round.has_next() else ("New round" if Round.scores.size() > 1 else "Play again"))
	_apply_cam(delta)
	_update_ball_visual()   # after the camera moves: the ball's size is set from its distance to the camera
	_update_wind_hud()
	# while the camera follows the ball she steps out of shot if it comes right up beside her (after a
	# putt the camera settles where she stands)
	var following := (phase == Phase.FLIGHT and phase_t > SWING_HOLD) or phase == Phase.RESULT or phase == Phase.HOLED
	golfer.visible = not (following and cam.global_position.distance_to(golfer.global_position) < 3.0)


func _end_intro() -> void:
	phase = Phase.AIM
	hud.flash("", 0.01)
	hud.hint.text = HINT
	_target_cam()


## The accuracy needle sweeps while she's pulled back: faster for longer clubs, and faster still with
## power past the mark.
func _sweep_needle(delta: float) -> void:
	if club.id == "putter" or pull < MIN_PULL:
		hud.accuracy.visible = false
		return
	var over := maxf(0.0, pull - 1.0) / (OVERPOWER - 1.0)
	_needle_t += delta * (1.0 + 1.5 * over)
	needle = sin(_needle_t * TAU / float(NEEDLE_PERIOD.get(club.id, 1.2)))
	hud.accuracy.show_needle(needle, PERFECT)


# ---------------------------------------------------------------- camera
var _want_pos := Vector3.ZERO
var _want_target := Vector3.ZERO
var _want_fov := 64.0
var _cam_rate := 8.0


func _aim_cam_pos() -> Vector3:
	var a := Vector3(aim.x, aim.y, 0)
	if club.id == "putter":
		return Terrain.to_world(ball - a * 3.0 + Vector3(0, 0, 1.3))
	return Terrain.to_world(ball - a * AIM_BACK + Vector3(0, 0, AIM_HEIGHT))   # held still while pulling, so the landing marker can be read


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
	_cam_rate = 5.0


## Aiming: up behind the ball, high enough to see the ball at the bottom and the target well up the
## screen, so where the shot is going reads at a glance.
func _target_cam() -> void:
	var d := maxf(Vector2(target.x - ball.x, target.y - ball.y).length(), 5.0)
	var a := Vector3(aim.x, aim.y, 0)
	var t3 := Vector3(target.x, target.y, terrain.height(target.x, target.y))
	var p := ball - a * (0.24 * d + 6.0) + Vector3(0, 0, 0.2 * d + 4.0)
	p.z = maxf(p.z, terrain.height(p.x, p.y) + 3.0)
	_want_pos = Terrain.to_world(p)
	_want_target = Terrain.to_world(ball.lerp(t3, 0.85))
	_want_fov = 50.0
	_cam_rate = 4.0


func _cut_to_swing_cam() -> void:
	var g := Terrain.to_course(golfer.position)
	var a := Vector3(aim.x, aim.y, 0)
	var r := Vector3(_right().x, _right().y, 0)
	var lead := golfer.swing_cam_lead(golfer.current_set)
	_want_pos = Terrain.to_world(g + r * 3.0 + a * (lead - 0.1) + Vector3(0, 0, 0.95))
	_want_target = Terrain.to_world(g + a * lead + Vector3(0, 0, 0.8))
	_want_fov = 52.0
	cam_pos = _want_pos
	cam_target = _want_target
	cam_fov = _want_fov
	_cam_rate = 20.0


func _chase_cam(_delta: float) -> void:
	if sim == null:
		return
	var b := sim.draw_pos()
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


## A point on the hole's centre line at a fractional index, on a smooth (Catmull-Rom) curve through the
## path points, so the flyover glides instead of turning at each point.
func _path_at(f: float) -> Vector2:
	var path: Array = terrain.meta.path
	var n := path.size()
	f = clampf(f, 0.0, n - 1.0)
	var i := mini(int(f), n - 2)
	var t := f - i
	var p := func(k: int) -> Vector2: return Vector2(path[clampi(k, 0, n - 1)][0], path[clampi(k, 0, n - 1)][1])
	var p0: Vector2 = p.call(i - 1)
	var p1: Vector2 = p.call(i)
	var p2: Vector2 = p.call(i + 1)
	var p3: Vector2 = p.call(i + 2)
	var t2 := t * t
	var t3 := t2 * t
	return 0.5 * (2.0 * p1 + (p2 - p0) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2 + (3.0 * p1 - p0 - 3.0 * p2 + p3) * t3)


## The ground height under the centre line, averaged over a stretch so the camera rides over the
## mounds instead of bobbing with them.
func _path_height(f: float) -> float:
	var h := 0.0
	for k in 5:
		var q := _path_at(f + (k - 2) * 0.75)
		h += terrain.height(q.x, q.y)
	return h / 5.0


func _intro_cam() -> void:
	var n: int = terrain.meta.path.size()
	var u := clampf(phase_t / INTRO_TIME, 0.0, 1.0)
	u = u * u * (3.0 - 2.0 * u)
	var f := u * (n - 1)
	var p2 := _path_at(f)
	# looking four points ahead, sliding toward the pin over the last stretch
	var fa := f + 4.0
	var ahead := _path_at(fa)
	var pin2 := Vector2(terrain.pin().x, terrain.pin().y)
	ahead = ahead.lerp(pin2, clampf(fa - (n - 1.0) + 1.0, 0.0, 1.0))
	var h := _path_height(f)
	cam_pos = Terrain.to_world(Vector3(p2.x, p2.y, h + 26.0 - 8.0 * u))
	cam_target = Terrain.to_world(Vector3(ahead.x, ahead.y, _path_height(minf(fa, n - 1.0))))
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

	var wplane := PlaneMesh.new()
	wplane.size = Vector2.ONE
	ring.mesh = wplane
	var rm := StandardMaterial3D.new()
	rm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	rm.albedo_texture = _target_texture()
	rm.albedo_color = Color(0.5, 1.0, 0.8, 0.9)     # mint: the wind's ring, apart from the gold target
	rm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	rm.no_depth_test = true
	rm.disable_fog = true
	rm.render_priority = 8
	rm.cull_mode = BaseMaterial3D.CULL_DISABLED
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
	mm.instance_count = 64
	mm.visible_instance_count = 0
	dots.multimesh = mm
	var dmat := StandardMaterial3D.new()
	dmat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	dmat.albedo_color = Color(1.0, 0.85, 0.5)
	dmat.disable_fog = true
	dots.material_override = dmat
	dots.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(dots)

	var plane := PlaneMesh.new()
	plane.size = Vector2.ONE
	target_ring.mesh = plane
	var tmat := StandardMaterial3D.new()
	tmat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	tmat.albedo_texture = _target_texture()
	tmat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	tmat.no_depth_test = true
	tmat.disable_fog = true
	tmat.render_priority = 9
	tmat.cull_mode = BaseMaterial3D.CULL_DISABLED
	target_ring.material_override = tmat
	target_ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(target_ring)
	target_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	target_label.no_depth_test = true
	target_label.fixed_size = true
	target_label.pixel_size = 0.0011
	target_label.font_size = 44
	target_label.outline_size = 14
	target_label.modulate = Color(1.0, 0.9, 0.7)
	target_label.outline_modulate = Color(0.08, 0.03, 0.12)
	target_label.render_priority = 11
	target_label.outline_render_priority = 10
	add_child(target_label)
	_show_preview(false)


## The target: a bold ring with a softer inner ring and a centre dot, gold.
func _target_texture() -> ImageTexture:
	var n := 256
	var img := Image.create(n, n, false, Image.FORMAT_RGBA8)
	for y in n:
		for x in n:
			var d := Vector2(x - n * 0.5 + 0.5, y - n * 0.5 + 0.5).length() / (n * 0.5)
			var outer := clampf(1.0 - absf(d - 0.84) / 0.1, 0.0, 1.0)
			var inner := clampf(1.0 - absf(d - 0.48) / 0.07, 0.0, 1.0) * 0.8
			var dot := clampf(1.0 - d / 0.12, 0.0, 1.0)
			var fill := 0.22 if d < 0.84 else 0.0
			var a := maxf(maxf(outer, inner), maxf(dot, fill))
			img.set_pixel(x, y, Color(1.0, 0.8, 0.35, a))
	return ImageTexture.create_from_image(img)


func _update_ball_visual() -> void:
	var b := sim.draw_pos() if (phase == Phase.FLIGHT or phase == Phase.RESULT or phase == Phase.HOLED) and sim else ball
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
	var cp := cam.global_position   # (a ribbon about 4 px wide at the ball on a phone, tapering behind)
	for i in trail_pts.size():
		var p := trail_pts[i]
		var t := (trail_pts[mini(i + 1, trail_pts.size() - 1)] - trail_pts[maxi(i - 1, 0)]).normalized()
		var side := t.cross(cp - p).normalized()
		var f := float(i) / (trail_pts.size() - 1)
		var width := cp.distance_to(p) * 0.0034 * (0.25 + 0.75 * f)
		var c := Color(1.0, 0.72 + 0.23 * f, 0.42, f * f * 0.75)
		trail_mesh.surface_set_color(c)
		trail_mesh.surface_add_vertex(p + side * width)
		trail_mesh.surface_set_color(c)
		trail_mesh.surface_add_vertex(p - side * width)
	trail_mesh.surface_end()


func _show_preview(on: bool) -> void:
	var full: bool = club.get("id", "") != "putter"
	ring.visible = on and full and _wind_land != Vector3.INF
	target_ring.visible = on
	target_label.visible = on
	dots.multimesh.visible_instance_count = dots.multimesh.visible_instance_count if on else 0


## The shot preview, all without wind: the arc of this pull's flight (a full pull while aiming), the
## roll after it once things hold still, the target ring with its distance, and a faint ring where the
## wind would carry a perfect full shot.
func _update_preview() -> void:
	var putt: bool = club.id == "putter"
	var p := full_power * (pull if phase == Phase.PULL else 1.0)
	var key := "%.4f|%.3f|%.3f|%s" % [p, target.x, target.y, club.id]
	var still := key == _preview_key
	_preview_key = key
	if not still:
		preview = BallSim.simulate(terrain, obstacles, terrain.pin(), Vector2.ZERO, ball,
			Clubs.launch_velocity(club, p, aim), club.lift, 0.05, not putt)
		var land: Vector3 = preview.first_land if preview.first_land != Vector3.INF else preview.end
		_carry_m = Vector2(land.x - ball.x, land.y - ball.y).length()
		_finish_m = _carry_m if putt else -1.0
		_finish_warn = _trouble(preview.state) if putt else ""
		_roll_pts = []
	elif _finish_m < 0.0 and not target_dragging:
		# held still: run it to the finish for the roll (a putt's preview already did)
		var whole := BallSim.simulate(terrain, obstacles, terrain.pin(), Vector2.ZERO, ball,
			Clubs.launch_velocity(club, p, aim), club.lift, 0.05)
		_finish_m = Vector2(whole.end.x - ball.x, whole.end.y - ball.y).length()
		_finish_warn = _trouble(whole.state)
		_roll_pts = []
		var pts: Array = whole.points
		var landed := false
		for q in pts:
			if not landed and whole.first_land != Vector3.INF and Vector2(q.x - ball.x, q.y - ball.y).length() >= _carry_m - 0.5:
				landed = true
			if landed:
				_roll_pts.append(q)
		_roll_pts.append(whole.end)
	# the wind's ring: where a perfect full pull lands in this wind (worked out when the target settles)
	var tkey := "%.3f|%.3f|%s|%.4f" % [target.x, target.y, club.id, full_power]
	if tkey != _target_key and not target_dragging:
		_target_key = tkey
		_wind_land = Vector3.INF
		if not putt and wind.length() > 0.5:
			var w := BallSim.simulate(terrain, obstacles, terrain.pin(), wind, ball,
				Clubs.launch_velocity(club, full_power, aim), club.lift, 0.0, true)
			_wind_land = w.first_land if w.first_land != Vector3.INF else w.end
	_draw_preview(putt)
	if phase == Phase.PULL:
		_show_gauge()
	else:
		hud.hide_gauge()


var _roll_pts: Array = []


func _draw_preview(putt: bool) -> void:
	var mm := dots.multimesh
	var cp := cam.global_position
	var count := 0
	var pts: Array = preview.get("points", [])
	if putt:
		# putts: the first stretch of the roll, so the break shows but the finish doesn't
		var show_n := int(pts.size() * 0.4)
		var step := maxi(1, int(ceil(float(show_n) / 40.0)))
		for i in range(0, show_n, step):
			var w := Terrain.to_world(pts[i]) + Vector3(0, 0.02, 0)
			mm.set_instance_transform(count, Transform3D(Basis().scaled(Vector3.ONE * clampf(cp.distance_to(w) * 0.004, 0.012, 0.05)), w))
			count += 1
	else:
		# the flight: dots along the arc, about a dot per 4 m, sized to stay the same on screen
		var air: Array = []
		for q in pts:
			if q.z > terrain.height(q.x, q.y) + 0.05:
				air.append(q)
		var every := maxi(1, int(round(air.size() / 46.0)))
		for i in range(every, air.size(), every):
			if count >= 52:
				break
			var w := Terrain.to_world(air[i])
			mm.set_instance_transform(count, Transform3D(Basis().scaled(Vector3.ONE * cp.distance_to(w) * 0.0042), w))
			count += 1
		# the roll after it: smaller dots along the ground
		var rstep := maxi(1, int(round(_roll_pts.size() / 10.0)))
		for i in range(0, _roll_pts.size(), rstep):
			if count >= mm.instance_count:
				break
			var w := Terrain.to_world(_roll_pts[i]) + Vector3(0, 0.05, 0)
			mm.set_instance_transform(count, Transform3D(Basis().scaled(Vector3.ONE * cp.distance_to(w) * 0.0026), w))
			count += 1
	mm.visible_instance_count = count
	# the target ring, flat on the ground and sized to read from the camera, with its distance
	var tw := Terrain.to_world(Vector3(target.x, target.y, terrain.height(target.x, target.y) + 0.12))
	var size := clampf(cp.distance_to(tw) * (0.12 if not putt else 0.07), 0.35, 30.0)
	var pulse := 1.0 + 0.06 * sin(Time.get_ticks_msec() * 0.006)
	target_ring.global_transform = Transform3D(Basis().scaled(Vector3(size * pulse, 1.0, size * pulse)), tw)
	target_ring.visible = true
	var dist := Vector2(target.x - ball.x, target.y - ball.y).length()
	target_label.text = _dist_text(dist, putt)
	target_label.global_position = tw + Vector3(0, size * 0.6 + 0.5, 0)
	target_label.visible = true
	ring.visible = _wind_land != Vector3.INF and Vector2(_wind_land.x - target.x, _wind_land.y - target.y).length() > 1.0
	if ring.visible:
		var ww := Terrain.to_world(_wind_land) + Vector3(0, 0.1, 0)
		ring.global_transform = Transform3D(Basis().scaled(Vector3(size * 0.7, 1.0, size * 0.7)), ww)


func _show_gauge() -> void:
	var putt: bool = club.id == "putter"
	var per_m := 3.281 if putt else YD
	var mark := Vector2(target.x - ball.x, target.y - ball.y).length() * per_m
	hud.gauge.show_shot(_carry_m * per_m, _finish_m * per_m if _finish_m >= 0.0 else -1.0,
		mark, mark * OVERPOWER, "ft" if putt else "yds", _finish_warn)


func _trouble(state: int) -> String:
	if state == BallSim.State.WATER:
		return "into the water!"
	if state == BallSim.State.OOB:
		return "out of bounds!"
	return ""


func _update_wind_hud() -> void:
	var cam_fwd := -cam.global_basis.z
	var fwd2 := Vector2(cam_fwd.x, -cam_fwd.z)
	if fwd2.length() < 0.01:
		return
	var rel := fwd2.normalized().angle_to(wind.normalized()) if wind.length() > 0.01 else 0.0
	hud.set_wind(0.0 if club.get("id", "") == "putter" else wind.length(), -rel)   # a rolling putt doesn't feel the wind
