extends Node3D
## Game flow for one hole: intro flyover -> aim -> slingshot pull -> swing cut -> ball chase
## -> result -> next shot ... -> holed. Course coords (x right, y down-range, z up) are used
## for all gameplay; Terrain.to_world() converts for anything drawn.
##
## Aiming works like the phone golf games: each shot starts with a target on the best landing spot
## (where the roll ends at the pin, when it's in reach); drag it anywhere in the club's range. Pulling
## back to the gauge's mark lands on the target (no wind); past it is extra power at a risk. The pull
## is a slingshot (hud.gd Sling): pulling down and to the right sends the shot left, and down-left
## sends it right, and the view stays up on the course while it's drawn so the landing can be watched
## swinging round as it moves. No shot is exact: it lands somewhere in a
## margin of error that grows with its length (the white circle on the ground). The wind is the
## aiming game: a mint ring shows where it carries the shot.

enum Phase { INTRO, AIM, PULL, SWING, FLIGHT, RESULT, HOLED }

const YD := 1.0936
const PULL_ZONE := 0.62         # touches starting below this share of the screen height pull back to
                                # swing; above it they drag the target
## The pull: drawing the band PULL_TRAVEL_MAX of the screen's height down (sideways only aims) is
## the club's full power (less when the finger starts too near the bottom: what's left above
## PULL_BOTTOM, but never under PULL_TRAVEL_MIN). The target is a mark partway along it. A putt's full
## pull is PUTT_HEADROOM times the putt, so the hole sits halfway along and a firm putt can run past.
const PULL_BOTTOM := 0.975
const PULL_TRAVEL_MIN := 0.12
const PULL_TRAVEL_MAX := 0.21
const PUTT_HEADROOM := 2.0
const PUTT_PAST := 0.3          # putts are aimed this far (m) past the hole, so the mark's pace drops
const MAGNET := 0.03            # within this (share of the pull) of the mark, the pull settles exactly on it
const RISKY_POWER := 0.9        # past this share of a club's power the swing gets loose: a wider margin
const EASE := 20.0              # power follows the finger at this rate (1/s), smoothing touch jitter
const MIN_PULL := 0.06
const SPREAD_NEAR := 0.045      # how far off a shot may land, as a share of its length: short shots ...
const SPREAD_FAR := 0.10        # ... up to this for a full drive of SPREAD_AT meters
const SPREAD_AT := 220.0
const SPREAD_LONG := 0.75       # the margin is shorter along the line than across it
## Slingshot aim: how far the finger has slid sideways (not the band's angle, which also changes as
## the pull grows) turns the shot the other way, evenly, up to SLING_AIM_MAX at SLING_SPAN of the
## screen's width; putts turn less, for fine lines. A soft dead zone in the middle lets a slightly
## crooked pull go straight without a step where the aim starts to move.
const SLING_SPAN := 0.4
const SLING_AIM_MAX := deg_to_rad(18.0)
const PUTT_TURN := 0.5            # putts: the line turns this share of the pull's angle (fine, not twitchy)
const PUTT_TURN_MAX := deg_to_rad(40.0)
const SLING_DEAD := 0.06        # share of SLING_SPAN
const SIDE_EASE := 12.0         # the aim follows the finger at this rate (1/s): smooth, not laggy
const DRAG_TURN := 0.9          # dragging the target: radians of aim per screen width across ...
const DRAG_REACH := 1.4         # ... and club ranges of distance per screen height up or down
const HINT := "Drag up top to move the target"
const FLIGHT_SPEED := 1.25      # flight plays a bit faster than real time
## The opening: one camera move (_intro_shots), dark at first: on the lantern and her bag by the tee
## while the lightning cracks and the lantern catches, rising behind the tee, then on down the hole
## lighting it as it goes (HoleView.light_front) to the flag; then a dip to black and up behind her.
const TEE_TIME := 4.6          # on the lantern and bag, rising behind the tee
const FLY_TIME := 5.0          # down the hole to the flag
const FLY_BACK := 0.5          # the dip to black and up behind her
const LIGHT_LEAD := 75.0       # the lights come on this far down the hole ahead of the camera ...
const LIGHT_SPEED := 130.0     # ... the front moving no faster than this (m/s), so they catch one by one
const AIM_BACK := 3.1           # aim camera: meters behind the ball ...
const AIM_HEIGHT := 1.65        # ... and above it; fixed so she is the same size every shot
const AIM_FOV := 60.0
const ORBIT_TIME := 0.42        # the sweep round from behind her to her side as she swings
const CHASE_BACK := 5.0         # the camera after the ball in the air: this far behind it ...
const CHASE_SIDE := 1.8         # ... to the side ...
const CHASE_UP := 1.8           # ... and above
const PUTT_BALL_Y := 0.74        # the putting stroke's view, from behind her: the ball this far down
const AIM_BALL_Y := 0.8         # the aiming view tips down until the ball sits this far down the screen
const CLUB_FACE := 0.13         # m from the middle of a driver or iron head in her sprite to its face
const BALL_LOOK_GROUND := 0.018  # the ball's drawn width as a share of its distance from the camera ...
const BALL_LOOK_AIR := 0.11     # ... and in the air, where its face is the show
const STREAKS_PER_S := 40.0     # wind streaks round the ball in flight ...
const STREAK_LIFE := 0.28       # ... and how long each lasts (s)
const SWING_HOLD := 0.45        # seconds the swing view holds after contact, for her follow-through

var terrain: Terrain
var obstacles: ObstacleGrid
var view := HoleView.new()
var fx := Fx.new()
var divots := Node3D.new()
var intro_fx := IntroFx.new()
var bag: Node3D                       # her golf bag (3D), stood beside her for every shot            # the turf her irons have taken this hole (cleared with the hole)
var golfer := Golfer.new()
var lantern := HeroLantern.new()
var hud := Hud.new()
var cam := Camera3D.new()
var ball_mesh := Sprite3D.new()          # the ball she plays: Marc's design picked in the clubhouse, its face in the air ...
var ball_plain := MeshInstance3D.new()    # ... and plain in its colour on the ground, turning as it rolls
var _ball_spin := Basis()
var _ball_last := Vector3.INF
var _ball_face_tex: Texture2D             # its scared face
var wind_fx := MeshInstance3D.new()       # streaks of air rushing past it in flight
var wind_mesh := ImmediateMesh.new()
var _streaks: Array = []                  # [angle round the ball, distance out, length, age]
var _wind_dir := Vector3.ZERO
var _streak_due := 0.0
var trail := MeshInstance3D.new()
var trail_mesh := ImmediateMesh.new()
var ring := MeshInstance3D.new()           # where the wind carries a perfect full shot: flat, mint
var dots := MultiMeshInstance3D.new()      # the flight arc and the roll after it
var putt_grid := PuttGrid.new()             # on the green: the slope grid and the straight aim line
var target_ring := MeshInstance3D.new()    # the target, flat on the ground
var spread_ring := MeshInstance3D.new()    # the margin of error round where this pull lands
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
var max_power := 1.0            # the power of a full pull, set when the pull starts (the club's own; a putt's headroom)
var pull := 0.0                 # 0 .. 1 of max_power; the target sits at mark_pull()
var _pull_len := 300.0          # finger travel (px) for a full pull, from where this pull started
var _max_carry := 0.0           # how far a full pull goes, for the gauge's scale
var pull_goal := 0.0            # where the finger says the pull should be; pull eases toward it
var pull_start := Vector2.ZERO
var spread_test := Vector2.INF  # a test can fix where in the margin a shot lands (x across, y along, -1..1)
var _shot_offset := Vector2.ZERO
var _aim_at_pull := Vector2(0, 1)   # slingshot aim while pulling: the aim and target distance when the
var _dist_at_pull := 0.0            # pull began, and how far the band says to turn from them (eased)
var _side_goal := 0.0
var _side := 0.0
var target_dragging := false
var _drag_from := Vector2.ZERO  # target dragging: where the finger went down, and the target then
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
	var id: String = Round.current().id
	if not Holes.hole_ready(id):
		set_process(false)            # nothing runs until the hole is built
		set_process_unhandled_input(false)
		# on the web the holes arrive in the background (scripts/holes.gd): if this one isn't here yet
		# (or what every hole needs, "core"), wait for it
		var note := "Loading..."
		var wait := _waiting_note(note)
		var bar := _waiting_bar(wait)
		var t0 := Time.get_ticks_msec()
		var show := func():
			var waiting: Array = Holes.needs(id).filter(func(p: String): return not Holes.is_ready(p))
			var f := Holes.progress(waiting[0] if not waiting.is_empty() else id)
			if f >= 0.0:
				bar.value = f
				wait.text = note + "\n%d%%" % roundi(f * 100.0)
			else:
				# size unknown: creep along (most holes take a few seconds), with what's arrived if known
				bar.value = 0.92 * (1.0 - exp(-float(Time.get_ticks_msec() - t0) / 5000.0))
				var mb := Holes.downloaded(waiting[0] if not waiting.is_empty() else id) / 1048576.0
				wait.text = note + ("\n%.1f MB" % mb if mb > 0.05 else "")
		var ticker := Timer.new()
		ticker.wait_time = 0.2
		ticker.timeout.connect(show)
		add_child(ticker)
		ticker.start()
		var ok: bool = await Holes.fetch(id)
		ticker.queue_free()
		if not ok:
			wait.text = "The fog won't lift (no connection?).\nBack to the clubhouse..."
			await get_tree().create_timer(2.5).timeout
			get_tree().set_meta("front_menu", true)
			get_tree().change_scene_to_file("res://scenes/front.tscn")
			return
		wait.get_parent().get_parent().queue_free()
		set_process(true)
		set_process_unhandled_input(true)
	terrain = Terrain.load_hole(Round.dir())
	tree_exiting.connect(func():
		Quality.watching = false
		Holes.hold = false)
	view.build(Round.dir(), terrain)
	add_child(view)
	obstacles = ObstacleGrid.new(view.props.obstacles)
	add_child(fx)
	add_child(divots)
	view.ambience.lightning.connect(func(k: float):
		# the thunder (a real recording) a second or two after the flash, louder the brighter it was
		Sfx.play_after(randf_range(0.9, 2.0), "thunder", lerpf(-14.0, -4.0, k), randf_range(0.85, 1.0)))
	par = int(terrain.meta.par)
	add_child(golfer)
	add_child(lantern)
	_make_bag()
	add_child(intro_fx)
	cam.keep_aspect = Camera3D.KEEP_WIDTH
	cam.near = 0.05
	cam.far = 2500.0
	add_child(cam)
	view.camera = cam
	_make_ball_visuals()
	add_child(hud)
	var wg := HoleView._col(view.theme.get("water_glow"), Color(0.35, 0.55, 1.0))
	if wg.v < 0.05:
		wg = Color(0.35, 0.55, 1.0)
	hud.aim_map.setup(terrain, Color(0.16 + 0.6 * wg.r, 0.16 + 0.6 * wg.g, 0.16 + 0.6 * wg.b))
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
	await _prewarm()
	# while this hole is played, the rest of the round arrives one at a time: the next hole, then the
	# other songs, then the holes after it, in order
	var later: Array = []
	for i in range(Round.index + 1, Round.HOLES.size()):
		later.append(Round.HOLES[i].id)
	later.insert(mini(1, later.size()), "music")
	Holes.queue(later)
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--capture="):
			add_child(load("res://tests/capture.gd").new())
		elif a.begins_with("--capture-hole="):
			add_child(load("res://tests/capture_hole.gd").new())
		elif a.begins_with("--look-out="):
			add_child(load("res://tests/look_at.gd").new())
		elif a.begins_with("--overhead="):
			add_child(load("res://tests/overhead.gd").new())
		elif a == "--intro-path":
			add_child(load("res://tests/intro_path.gd").new())
		elif a == "--knock-probe":
			add_child(load("res://tests/knock_probe.gd").new())
		elif a.begins_with("--light-set="):
			add_child(load("res://tests/light_set.gd").new())


var _intro_id := 0              # the current opening, so a restarted one's title timer is the only one shown


## The opening flyover is drawn softer and without the moon's shadows (from up there they barely
## show, and redrawing the shadow map every frame costs a phone); the aiming view gets both back.
func _flyover(on: bool) -> void:
	Quality.flyover(on)
	view.moon_light.shadow_enabled = not on


## Every material, texture and effect is drawn once behind a dark title card before the hole is
## shown: a phone's browser builds each shader (and uploads each texture) the first time it's
## drawn, and doing that during the flyover is what made the opening stutter.
func _prewarm() -> void:
	set_process(false)
	set_process_unhandled_input(false)
	var card := _waiting_note("Loading...")
	var cover := card.get_parent().get_parent() as CanvasLayer
	cover.layer = 100
	golfer.preload_frames()
	# the whole hole from straight above
	var span := Vector2(terrain.nx, terrain.ny) * terrain.cell
	var mid := terrain.origin + span * 0.5
	var top := Terrain.to_world(Vector3(mid.x, mid.y, terrain.height(mid.x, mid.y) + 400.0))
	view.moon_light.shadow_enabled = false          # the flyover's look first, then the aiming view's
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = maxf(span.x, span.y)
	cam.look_at_from_position(top, top + Vector3.DOWN, Terrain.to_world(Vector3(0, 1, 0)) - Terrain.to_world(Vector3.ZERO))
	await _drawn(2)
	cam.projection = Camera3D.PROJECTION_PERSPECTIVE
	# the opening's framed shots
	var start := 0.0
	for sh in _intro_shots():
		phase_t = start + 0.1
		start += float(sh.time)
		_intro_cam()
		_apply_cam(0.0)
		await _drawn(1)
	intro_fx.stop()
	phase_t = 0.0
	# the aiming view with its markers, a ball trail, and every landing effect (out of sight underground)
	view.moon_light.shadow_enabled = true
	await _drawn(1)
	phase = Phase.AIM
	_aim_cam()
	cam_pos = _want_pos
	cam_target = _want_target
	cam_fov = _want_fov
	_apply_cam(0.0)
	_update_preview()
	var under := Terrain.to_world(ball) + Vector3(0, -4, 0)
	for surf in [Terrain.Surface.FAIRWAY, Terrain.Surface.SAND, Terrain.Surface.WATER, Terrain.Surface.PATH, Terrain.Surface.GREEN]:
		fx.land(under, surf)
	fx.holed(under, Color(1.0, 0.6, 0.25))
	fx.divot(under, Vector3.UP, Vector3.FORWARD, 1.0, under + Vector3.FORWARD * 2.0, Vector3.UP, divots)
	fx.sand_blast(under, Vector3.FORWARD)
	for i in 8:
		trail_pts.append(under + Vector3(i, 0, 0))
	_streaks.append([0.0, 1.0, 2.0, 0.1])
	_wind_dir = Vector3.FORWARD
	_update_ball_visual()
	ball_mesh.visible = true                   # its face too, though it only shows in the air
	ball_mesh.modulate.a = 0.5
	await _drawn(2)
	trail_pts.clear()
	_streaks.clear()
	# the first shot, rehearsed: the pull (its gauge and map, her backswing), then round at her side
	# through the swing, and the putting read, so none of it is drawn (or a sound loaded) for the
	# first time when it's played for real
	Sfx.preload_all()
	phase = Phase.PULL
	pull = 0.6
	_update_preview()
	_show_gauge()
	_show_aim_map(false)
	golfer.set_pull(_sprite_set("back"), pull)
	await _drawn(1)
	_place_golfer_face()
	var face_set := _sprite_set("face")
	var sc := _swing_cam()
	cam_pos = sc[0]
	cam_target = sc[1]
	cam_fov = sc[2]
	_apply_cam(0.0)
	var down: Array = golfer.sets[face_set].down
	for f in [down[0], down[down.size() / 2], down[down.size() - 1]]:
		golfer.show_frame(face_set, int(f))
		await _drawn(1)
	var b2 := Vector2(ball.x, ball.y)
	putt_grid.build(terrain, b2, b2 + aim * 4.0)
	putt_grid.set_line(b2, aim, 4.0)
	await _drawn(1)
	putt_grid.visible = false
	pull = 0.0
	phase = Phase.AIM                        # out of the rehearsal's pull, so the shot set-up puts her at address
	hud.hide_gauge()
	hud.hide_aim_map()
	_show_preview(false)
	# then the opening for real
	_start_hole()
	cover.queue_free()
	hud.fade_in()
	set_process(true)
	set_process_unhandled_input(true)


func _drawn(frames: int) -> void:
	for i in frames:
		await RenderingServer.frame_post_draw


## A pumpkin-orange progress bar under a waiting note.
func _waiting_bar(note: Label) -> ProgressBar:
	var bar := ProgressBar.new()
	bar.show_percentage = false
	bar.max_value = 1.0
	bar.set_anchors_preset(Control.PRESET_CENTER)
	bar.size = Vector2(440, 18)
	bar.position = Vector2(-220, 110)
	var bg := StyleBoxFlat.new()
	bg.bg_color = Color(0.09, 0.05, 0.14)
	bg.border_color = Color(1.0, 0.62, 0.24)
	bg.set_border_width_all(2)
	bg.set_corner_radius_all(9)
	var fill := StyleBoxFlat.new()
	fill.bg_color = Color(1.0, 0.55, 0.15)
	fill.set_corner_radius_all(9)
	bar.add_theme_stylebox_override("background", bg)
	bar.add_theme_stylebox_override("fill", fill)
	note.get_parent().add_child(bar)
	return bar


## A line of text on a dark screen while a hole is fetched.
func _waiting_note(text: String) -> Label:
	var layer := CanvasLayer.new()
	add_child(layer)
	var bg := ColorRect.new()
	bg.color = Color(0.09, 0.05, 0.14)          # the loading screen's dark purple
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	layer.add_child(bg)
	var l := Label.new()
	l.text = text
	l.set_anchors_preset(Control.PRESET_FULL_RECT)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.add_theme_font_override("font", Chalk.hand_font())
	l.add_theme_font_size_override("font_size", 34)
	l.add_theme_color_override("font_color", Color(1.0, 0.9, 0.78, 0.7))     # light, quiet
	bg.add_child(l)
	return l


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
	for d in divots.get_children():
		d.queue_free()
	strokes = 0
	ball = terrain.tee() + Vector3(0, 0, BallSim.RADIUS)
	last_ball = ball
	hud.set_hole(int(terrain.meta.number), terrain.meta.name, par)
	trail_pts.clear()
	_setup_shot()
	phase = Phase.INTRO
	phase_t = 0.0
	_shot = -1
	hud.hide_aim_map()
	_flyover(true)
	hud.hint.text = "Tap to skip"
	_place_lantern()
	_front = -12.0
	view.lights_from(Terrain.to_world(terrain.tee()),
		Terrain.to_world(Vector3(_hole_dir().x, _hole_dir().y, 0.0)) - Terrain.to_world(Vector3.ZERO))
	# the hole's name over the dark tee, as the lantern catches
	var title := "Hole %d · Par %d\n%s" % [terrain.meta.number, par, _dist_text(_to_pin(), false)]
	_intro_id += 1
	var this_intro := _intro_id
	get_tree().create_timer(0.5).timeout.connect(func():
		if phase == Phase.INTRO and _intro_id == this_intro:
			hud.flash(title, TEE_TIME - 1.1))


func _to_pin() -> float:
	var p := terrain.pin()
	return Vector2(p.x - ball.x, p.y - ball.y).length()


func _on_green() -> bool:
	var s := terrain.surface_at(ball.x, ball.y)
	return s == Terrain.Surface.GREEN or (s == Terrain.Surface.FRINGE and _to_pin() < 12.0)


func _setup_shot() -> void:
	_lie = 1.0
	_celebrating = false
	club = _pick_club()
	_lie = _lie_at(ball)
	if club.id == "putter":
		putt_grid.build(terrain, Vector2(ball.x, ball.y), Vector2(terrain.pin().x, terrain.pin().y))
	else:
		putt_grid.visible = false
	pull = 0.0
	pull_goal = 0.0
	target_dragging = false
	_set_target(_default_target())
	_place_bag()
	view.face_flag(Terrain.to_world(ball))     # under the fade, so it's already round when the shot comes up
	hud.set_stroke(strokes + 1, par)
	hud.set_distance(_dist_text(_to_pin(), club.id == "putter"))
	hud.set_club(club.label, club.carry_m * YD)
	hud.hide_gauge()
	hud.hint.text = HINT if strokes == 0 else ""
	if _lie < 0.9:
		var patch := terrain.patch_at(ball.x, ball.y)
		var where := "A spider web" if terrain.in_web(ball.x, ball.y) else ("The corn" if terrain.in_corn(ball.x, ball.y) \
			else (String(PATCH_NAMES[patch]) if patch != "" else String(Terrain.SURFACE_LABELS[terrain.surface_at(ball.x, ball.y)])))
		hud.hint.text = "%s: it'll fly %d%% shorter" % [where, roundi((1.0 - _lie) * 100.0)]
	var sh := _slope_hint()
	if sh != "":
		hud.hint.text = sh if hud.hint.text == "" or strokes == 0 else hud.hint.text + "\n" + sh
	ball_mesh.visible = true
	_preview_key = ""
	trail_pts.clear()
	phase = Phase.AIM
	_aim_cam()
	cam_pos = _want_pos
	cam_target = _want_target
	cam_fov = _want_fov
	hud.fade_in()


## The club for this shot: the shortest whose full swing reaches the pin with a little in hand
## (Clubs.PICK_SHARE of its power), worked out over the real ground, so a downhill par 3 gets a
## shorter club than its flat yardage says and an uphill one a longer. Starting a couple of clubs
## short of the flat-ground pick keeps it to a few test flights.
func _pick_club() -> Dictionary:
	if _on_green():
		return Clubs.by_id("putter")
	var d := _to_pin()
	if d > Clubs.ALL[0].carry_m:
		return Clubs.ALL[0]             # out of reach: the driver, no need to test
	var dir := Vector2(terrain.pin().x - ball.x, terrain.pin().y - ball.y).normalized()
	var start := mini(Clubs.ALL.find(Clubs.pick(d, false)) + 2, Clubs.ALL.size() - 2)
	for i in range(start, -1, -1):
		club = Clubs.ALL[i]
		_lie = _lie_at(ball)
		if _power_for(d, dir) <= Clubs.PICK_SHARE:
			return club
	return Clubs.ALL[0]


## A distance as a golfer says it: feet on the green, yards elsewhere.
func _dist_text(m: float, feet: bool) -> String:
	if feet:
		var ft := maxi(1, roundi(m * 3.281))
		return "%d ft" % ft
	var yd := maxi(1, roundi(m * YD))
	return "1 yd" if yd == 1 else "%d yds" % yd


## Where a shot should land to start with: for a putt, a foot past the hole (struck to die right at
## the cup, a putt stops on the lip; firm enough to finish a foot by, it drops); with the pin in reach, the spot the
## roll carries on from to finish at the pin; otherwise a full club out along the fairway's centre line.
func _default_target() -> Vector2:
	var b := Vector2(ball.x, ball.y)
	var pin2 := Vector2(terrain.pin().x, terrain.pin().y)
	if club.id == "putter":
		return _read_putt(pin2)
	var reach: float = club.carry_m
	if b.distance_to(pin2) <= reach:
		var land := _landing_to_stop_at(pin2)
		if par == 3 and strokes == 0:
			# a par 3's tee shot is aimed at the green: a club that runs out (a wood into the wind)
			# would land short of it, over the water, so the mark goes forward onto the green
			var dir := (pin2 - b).normalized()
			while land.distance_to(pin2) > 1.0 and terrain.surface_at(land.x, land.y) != Terrain.Surface.GREEN \
					and (land - b).dot(dir) < (pin2 - b).dot(dir):
				land += dir
		return land
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
		var err := absf(v.length() - reach * Clubs.PICK_SHARE)
		if err < best_err:
			best_err = err
			best = v
	return _safe_layup(b + best)


## A putt's line, read the way a caddie reads a green: a foot past the hole, then moved across the
## slope until the roll at that pace runs over the cup (the white dots show it bending in).
func _read_putt(pin2: Vector2) -> Vector2:
	var b := Vector2(ball.x, ball.y)
	var t := pin2 + (pin2 - b).normalized() * PUTT_PAST
	for i in 5:
		var dir := (t - b).normalized()
		var r := BallSim.simulate(terrain, obstacles, terrain.pin(), Vector2.ZERO, ball,
			_launch(_power_for(b.distance_to(t), dir), dir), club.lift, 0.02)
		if r.state == BallSim.State.HOLED:
			break
		# where the roll passed the hole: its nearest point to the cup, and how far across the line
		var near := b
		for q in r.points:
			if Vector2(q.x, q.y).distance_to(pin2) < near.distance_to(pin2):
				near = Vector2(q.x, q.y)
		var right := Vector2(dir.y, -dir.x)
		var miss := (pin2 - near).dot(right)
		if absf(miss) < 0.01:
			break
		t += right * miss * b.distance_to(t) / maxf(b.distance_to(near), 0.1)
	return t


## Start the aim somewhere the shot finishes safely: if a shot to `t` would roll into water, out of
## bounds or a bunker, or its margin of error reaches water or out of bounds, the target comes back
## down the line 8 m at a time (as a good caddie would say: lay up short of the creek).
func _safe_layup(t: Vector2) -> Vector2:
	var b := Vector2(ball.x, ball.y)
	var dir := (t - b).normalized()
	var d := b.distance_to(t)
	var right := Vector2(dir.y, -dir.x)
	for k in 10:
		var r := BallSim.simulate(terrain, obstacles, terrain.pin(), Vector2.ZERO, ball,
			_launch(_power_for(d, dir), dir), club.lift)
		var e := Vector2(r.end.x, r.end.y)
		var m := _spread(d)
		var ok: bool = r.state != BallSim.State.WATER and r.state != BallSim.State.OOB \
			and terrain.surface_at(e.x, e.y) != Terrain.Surface.SAND and not terrain.in_web(e.x, e.y) \
			and not terrain.in_corn(e.x, e.y) and terrain.patch_at(e.x, e.y) == ""
		for q in [e + dir * m * SPREAD_LONG, e + right * m * 0.8, e - right * m * 0.8]:
			var sq := terrain.surface_at(q.x, q.y)
			ok = ok and sq != Terrain.Surface.WATER and sq != Terrain.Surface.OOB
		if ok or d < club.carry_m * 0.45:
			break
		d -= 8.0
	return b + dir * d


## The landing spot short of `spot` that the roll (no wind) carries on from to finish there.
func _landing_to_stop_at(spot: Vector2) -> Vector2:
	var b := Vector2(ball.x, ball.y)
	var d := b.distance_to(spot)
	var dir := (spot - b).normalized()
	var land := d
	for i in 5:
		var r := BallSim.simulate(terrain, obstacles, terrain.pin(), Vector2.ZERO, ball,
			_launch(_power_for(land, dir), dir), club.lift)
		if r.state == BallSim.State.HOLED:
			break
		var f := Vector2(r.end.x, r.end.y).distance_to(b)
		if absf(f - d) < 0.5:
			break
		# down to a third of the way (onto a green running away it's landed short and run up on), or a
		# little past for one that spins back
		land = clampf(land - (f - d), d * 0.35, d * 1.25)
	return b + dir * land


## How far a club's swing at power `p` carries along `dir` with no wind (a putt: how far it rolls).
## INF when a putt drops: it would have rolled at least as far as it needed to.
## How well the ball sits: the share of a club's power a full swing gets out of the lie (rough grabs
## the club, deep rough and the corn more, a bunker takes some, a spider web holds it fast).
const LIE := {Terrain.Surface.ROUGH: 0.92, Terrain.Surface.DEEP: 0.78, Terrain.Surface.SAND: 0.85}
const LIE_WEB := 0.6
const LIE_CORN := 0.65
const LIE_PATCH := 0.65                      # among the headstones or the pumpkins: like the corn
const PATCH_NAMES := {"graves": "The graves", "pumpkins": "The pumpkin patch"}
const PATCH_LOST := {"graves": "Lost in the graves!", "pumpkins": "Lost in the pumpkins!"}
var _lie := 1.0


func _lie_at(b: Vector3) -> float:
	if club.get("id", "") == "putter":
		return 1.0
	if terrain.in_web(b.x, b.y):
		return LIE_WEB
	if terrain.in_corn(b.x, b.y):
		return LIE_CORN
	if terrain.patch_at(b.x, b.y) != "":
		return LIE_PATCH
	var surf := terrain.surface_at(b.x, b.y)
	var f: float = LIE.get(surf, 1.0)
	if surf == Terrain.Surface.SAND and club.get("kind", "") == "wedge":
		f = 0.95                               # a wedge splashes it out
	return f


## A shot's launch from where the ball lies (every shot and every preview goes through here): the
## lie's loss of distance, and on sloping ground the slope's pull (_slope_lie).
func _launch(p: float, dir: Vector2) -> Vector3:
	var s := _slope_lie(dir)
	return Clubs.launch_velocity(club, p * _lie * s.y, dir.rotated(s.x))


const SLOPE_FREE := 0.02          # slopes gentler than this (2%) play as flat
const SLOPE_TURN := deg_to_rad(0.4)   # per percent of slope across the line, ball above/below her feet
const SLOPE_TURN_MAX := deg_to_rad(5.0)
const SLOPE_LENGTH := 0.9         # per unit of slope along the line: uphill shorter, downhill longer

## An uneven lie, for a shot along `dir`: x = how far it turns (radians, + = left), y = the power's
## factor. She's right-handed, standing left of the line with the ball to her right, so ground rising
## toward the ball (it sits above her feet) pulls it left, falling away pushes it right; an uphill lie
## adds loft and comes up short, a downhill one flies lower and runs on. Putts and the tee play level.
func _slope_lie(dir: Vector2) -> Vector2:
	if club.get("id", "") == "putter" or terrain == null:
		return Vector2(0.0, 1.0)
	var surf := terrain.surface_at(ball.x, ball.y)
	if surf == Terrain.Surface.TEE or surf == Terrain.Surface.GREEN:
		return Vector2(0.0, 1.0)
	var g := _grade(Vector2(ball.x, ball.y))
	var right := Vector2(dir.y, -dir.x)
	var across := _past(g.dot(right))
	var along := _past(g.dot(dir))
	return Vector2(clampf(across * 100.0 * SLOPE_TURN, -SLOPE_TURN_MAX, SLOPE_TURN_MAX),
		clampf(1.0 - along * SLOPE_LENGTH, 0.9, 1.08))


## The ground's rise per metre at `p` (course coords), over a metre or so either way.
func _grade(p: Vector2) -> Vector2:
	return Vector2(terrain.height(p.x + 0.8, p.y) - terrain.height(p.x - 0.8, p.y),
		terrain.height(p.x, p.y + 0.8) - terrain.height(p.x, p.y - 0.8)) / 1.6


func _past(v: float) -> float:
	return signf(v) * maxf(absf(v) - SLOPE_FREE, 0.0)


## What the slope under the ball will do to a shot along the target line, for the hint ("" if nothing).
func _slope_hint() -> String:
	if club.get("id", "") == "putter":
		return ""
	var s := _slope_lie(aim)
	var bits: Array[String] = []
	if absf(s.x) > deg_to_rad(0.6):
		bits.append("Ball above your feet: it'll pull left" if s.x > 0.0 else "Ball below your feet: it'll push right")
	if s.y < 0.985:
		bits.append("Uphill lie: plays shorter")
	elif s.y > 1.015:
		bits.append("Downhill lie: flies lower, runs on")
	return " · ".join(bits)


func _carry(p: float, dir: Vector2) -> float:
	var r := BallSim.simulate(terrain, obstacles, terrain.pin(), Vector2.ZERO, ball,
		_launch(p, dir), club.lift, 0.0, true)
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
	_place_golfer_back(phase != Phase.PULL)       # mid-pull she keeps her backswing
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
	club = Clubs.next(club)
	_lie = _lie_at(ball)
	if club.id == "putter":
		putt_grid.build(terrain, Vector2(ball.x, ball.y), Vector2(terrain.pin().x, terrain.pin().y))
	else:
		putt_grid.visible = false
	hud.set_club(club.label, club.carry_m * YD)
	hud.set_distance(_dist_text(_to_pin(), club.id == "putter"))
	_set_target(_default_target())


func _right() -> Vector2:
	return Vector2(aim.y, -aim.x)


func _sprite_set(view_name: String) -> String:
	var s: String = club.sprite
	return golfer.back_set(s) if view_name == "back" else golfer.face_set(s)


func _place_golfer_back(pose := true) -> void:
	var set_name := _sprite_set("back")
	var off := golfer.club_offset(set_name)
	# her club's face on the ball (the sprite's club point is the middle of the head; full swings'
	# heads are long, so she stands a little further along)
	var face: float = 0.0 if club.id == "putter" else CLUB_FACE
	var g2 := Vector2(ball.x, ball.y) - _right() * (off.x + face) - aim * 0.12
	golfer.position = Terrain.to_world(Vector3(g2.x, g2.y, terrain.height(g2.x, g2.y)))
	if pose:
		golfer.address(set_name)


## The giant jack-o'-lantern sits off the left of the tee (clear of the camera's sweep round to her
## right side as she swings), its face turned back across the tee box.
var _lantern_face := Vector2.ZERO


func _place_lantern() -> void:
	var l2 := Vector2(ball.x, ball.y) - _right() * 4.4 + aim * 0.2     # back a little from the tee markers
	_lantern_face = (_right() + aim * 0.4).normalized()
	var w := Terrain.to_world(Vector3(l2.x, l2.y, terrain.height(l2.x, l2.y) - 0.04))
	lantern.position = w
	var f := Terrain.to_world(Vector3(_lantern_face.x, _lantern_face.y, 0)) - Terrain.to_world(Vector3.ZERO)
	lantern.look_at(w - f, Vector3.UP)      # its face (local +z) toward the tee


## How far off a shot of `d` meters may land (the circle's half-width): a few percent on short shots,
## more the longer it is, and more again with power past the mark. Putts are exact.
func _spread(d: float) -> float:
	if club.id == "putter":
		return 0.0
	var share := lerpf(SPREAD_NEAR, SPREAD_FAR, clampf(d / SPREAD_AT, 0.0, 1.0))
	var power := max_power * pull if phase == Phase.PULL or phase == Phase.SWING else 0.0
	return d * share * (1.0 + 4.0 * maxf(0.0, power - RISKY_POWER))


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
	hud.hide_aim_map()
	# where in its margin this one lands: anywhere in it, more often toward the middle (putts are exact)
	_shot_offset = Vector2.ZERO
	if club.id != "putter":
		_shot_offset = spread_test if spread_test != Vector2.INF else Vector2.from_angle(randf() * TAU) * randf()
		if _shot_offset.length() < 0.2:
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
		# down behind her for the stroke (the view stayed up on the green while the putt was drawn)
		_aim_cam()
		cam_pos = _want_pos
		cam_target = _want_target
		cam_fov = _want_fov
		golfer.play_downswing(_sprite_set("back"))
	else:
		_start_orbit()


func _on_contact() -> void:
	sim = BallSim.new(terrain, obstacles, terrain.pin(), wind)
	# aim at the spot in the margin it's to land on: across by the circle's width, along by its length
	var b := Vector2(ball.x, ball.y)
	var power := max_power * pull
	var d := _carry(power, aim)
	if d == INF:
		d = Vector2(target.x, target.y).distance_to(b)        # a putt that drops
	var r := _spread(d)
	var land := b + aim * d + _right() * _shot_offset.x * r + aim * _shot_offset.y * r * SPREAD_LONG
	var dir := (land - b).normalized()
	var stretch := land.distance_to(b) / maxf(d, 0.01)
	sim.launch(ball, _launch(power * stretch, dir), club.lift)
	_take_turf(dir, power)
	var hit: String = {"wood": "hit_driver", "putter": "putt"}.get(club.kind, "hit_iron")
	Sfx.play(hit, lerpf(-14.0, 0.0, clampf(power, 0.0, 1.0)) if club.id == "putter" else -1.0)
	_landed_fx = false
	trail_pts.clear()
	_time_scale = 1.0 if club.id == "putter" else FLIGHT_SPEED
	flight_dir = aim
	phase = Phase.FLIGHT
	phase_t = 0.0


const BAG_LAYER := 1 << 15      # render layer only the bag is on: its own warm light lights nothing else
const BAG_LIGHT := 1.6          # that light's strength
var _bag_light: OmniLight3D
const BAG_MODEL := "res://assets/props/bag/bag.glb"     # Marc's Pumpkin Golf Stand Bag (art_src/bag/final)


func _make_bag() -> void:
	if not ResourceLoader.exists(BAG_MODEL):
		return
	bag = (load(BAG_MODEL) as PackedScene).instantiate()
	# Marc's materials as they come, kept matte (the engine skips the file's specular setting), with a
	# rim so its outline catches the moonlight; and a small warm light of its own, as if from a lantern
	# nearby, that lights only the bag (its own layer), so the dark plum reads at night
	for node in bag.find_children("*", "MeshInstance3D", true, false):
		var mi := node as MeshInstance3D
		mi.layers = 1 | BAG_LAYER
		for i in mi.mesh.get_surface_count():
			var m := mi.mesh.surface_get_material(i) as StandardMaterial3D
			if m:
				m = m.duplicate()
				if m.metallic < 0.5:
					m.metallic_specular = 0.15
				m.rim_enabled = true
				m.rim = 0.55
				m.rim_tint = 0.35
				mi.set_surface_override_material(i, m)
	var warm := OmniLight3D.new()
	warm.light_color = Color(1.0, 0.62, 0.3)
	warm.light_energy = BAG_LIGHT
	warm.omni_range = 2.4
	warm.omni_attenuation = 1.2
	warm.shadow_enabled = false
	warm.light_cull_mask = BAG_LAYER
	warm.position = Vector3(0.55, 0.95, 0.85)      # up and out in front of the pocket, to one side
	bag.add_child(warm)
	_bag_light = warm
	add_child(bag)


## The bag set down just off her left side, pocket turned toward the camera behind her;
## never on the green (it's carried off to the nearest grass beside her).
func _place_bag() -> void:
	if bag == null:
		return
	var b := Vector2(ball.x, ball.y)
	var side := -_right()
	var at := b + side * 1.6 + aim * 1.9      # ahead on her left, in the frame behind her
	for k in 20:
		var su := terrain.surface_at(at.x, at.y)
		if su != Terrain.Surface.GREEN and su != Terrain.Surface.WATER and su != Terrain.Surface.SAND:
			break
		at += side * 1.2
	var w := Terrain.to_world(Vector3(at.x, at.y, terrain.height(at.x, at.y) - 0.02))
	var face := (-aim + side * 0.6).normalized()          # the pocket (local +z) back toward the camera
	var f := Terrain.to_world(Vector3(face.x, face.y, 0)) - Terrain.to_world(Vector3.ZERO)
	bag.global_transform = Transform3D(Basis.looking_at(-f, Vector3.UP), w)


## What the club takes at the strike: irons, wedges and chips off the turf dig a divot just past the
## ball (bigger the more lofted and the harder she swings), a bunker shot blasts sand; woods sweep it
## clean and putts touch nothing.
func _take_turf(dir: Vector2, power: float) -> void:
	if not club.kind in ["iron", "wedge", "chip"]:
		return
	var surf := terrain.surface_at(ball.x, ball.y)
	var at := Terrain.to_world(Vector3(ball.x, ball.y, terrain.height(ball.x, ball.y)))
	var d3 := Terrain.to_world(Vector3(dir.x, dir.y, 0.0)).normalized()
	if surf == Terrain.Surface.SAND:
		fx.sand_blast(at, d3)
		return
	if not surf in [Terrain.Surface.FAIRWAY, Terrain.Surface.ROUGH, Terrain.Surface.DEEP, Terrain.Surface.TEE, Terrain.Surface.FRINGE]:
		return
	var size: float = {"iron": 1.0, "wedge": 1.2, "chip": 0.6}[club.kind] * lerpf(0.6, 1.0, clampf(power, 0.0, 1.0))
	var n := Terrain.to_world(terrain.normal(ball.x, ball.y))
	var land := Vector2(ball.x, ball.y) + dir * randf_range(1.6, 3.0) * size
	var land_n := Terrain.to_world(terrain.normal(land.x, land.y))
	fx.divot(at, n, d3, size, Terrain.to_world(Vector3(land.x, land.y, terrain.height(land.x, land.y))), land_n, divots)


const CELEBRATE_SET := "video_celebrate"
const CELEBRATE_AT := 1.1        # s after the ball drops: the cut to her celebrating
var _celebrating := false
var _time_scale := 1.0           # how fast the shot plays: flight a bit quick, eased to real time on the ground


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
			hud.flash("Into the ravine! +1 stroke" if view.theme.get("ravine", false) else "Splash! +1 stroke")
		BallSim.State.OOB:
			strokes += 1
			ball = last_ball
			hud.flash("Out of bounds! +1 stroke")
		_:
			ball = sim.pos
			if sim.caught:
				hud.flash("Caught in the web! · %s" % _dist_text(carried / YD, false))
				Sfx.play("land_sand", -6.0, 0.7)
			elif terrain.in_corn(ball.x, ball.y):
				hud.flash("Lost in the corn! · %s" % _dist_text(carried / YD, false))
			elif terrain.patch_at(ball.x, ball.y) != "" and club.id != "putter":
				hud.flash("%s · %s" % [PATCH_LOST[terrain.patch_at(ball.x, ball.y)], _dist_text(carried / YD, false)])
			elif club.id == "putter":
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


var _knock_at := -1.0


## The ball off a prop this frame: a knock off a trunk, a clack off a stone, a thud off a pumpkin,
## a rustle through leaves; louder the harder it hit, and only one every so often (a ball dropping
## through a canopy touches it step after step).
func _prop_knocks() -> void:
	if sim.hits.is_empty():
		return
	var h: Dictionary = sim.hits[0]
	for k in sim.hits:
		if float(k.speed) > float(h.speed):
			h = k
	sim.hits.clear()
	var now := Time.get_ticks_msec() / 1000.0
	if float(h.speed) < 1.5 or now - _knock_at < 0.15:
		return
	_knock_at = now
	var s: Dictionary = h.shape
	var name := "hit_soft"
	match s.type:
		"cylinder": name = "hit_wood"
		"box": name = "hit_stone"
		"sphere": name = "hit_leaves" if s.get("soft", false) else "hit_soft"
	var k := clampf(float(h.speed) / 30.0, 0.0, 1.0)
	Sfx.play(name, lerpf(-16.0, -2.0, k), randf_range(0.9, 1.1))

func _press(p: Vector2) -> void:
	var vp := get_viewport().get_visible_rect().size
	match phase:
		Phase.INTRO:
			_end_intro()
		Phase.AIM:
			if p.y > vp.y * PULL_ZONE:
				hud.show_pull_tip(false)
				phase = Phase.PULL
				pull_start = p
				pull_goal = 0.0
				max_power = _full_pull_power()
				_pull_len = clampf(vp.y * PULL_BOTTOM - p.y, vp.y * PULL_TRAVEL_MIN, vp.y * PULL_TRAVEL_MAX)
				var mc := _carry(max_power, aim)
				_max_carry = mc if mc != INF else Vector2(target.x - ball.x, target.y - ball.y).length() * PUTT_HEADROOM
				_aim_at_pull = aim
				_dist_at_pull = Vector2(target.x - ball.x, target.y - ball.y).length()
				_side_goal = 0.0
				_side = 0.0
				hud.hint.text = ""
				_pull_quarter = 0
				Sfx.buzz(10)
			else:
				target_dragging = true
				_drag_from = p
				_target0 = target


func _drag(p: Vector2, _rel: Vector2) -> void:
	if target_dragging:
		# from behind her the target is far off, so a drag moves it by how far the finger goes: across
		# swings it left or right, up pushes it longer, down brings it shorter
		var vp := get_viewport().get_visible_rect().size
		var b := Vector2(ball.x, ball.y)
		var v0 := _target0 - b
		var d := (p - _drag_from) / vp
		var reach: float = club.carry_m * (PUTT_HEADROOM if club.id == "putter" else 1.0)
		var dist := clampf(v0.length() - d.y * reach * DRAG_REACH, 0.5, reach)
		_set_target(b + v0.normalized().rotated(-d.x * DRAG_TURN) * dist, false)
	elif phase == Phase.PULL:
		# the band, from where the finger went down: how far down it is drawn is the power, its tilt the aim
		var v := p - pull_start
		var putt: bool = club.id == "putter"
		# full swings: how far down is the power, sideways only aims; putts: a true slingshot, the
		# length of the pull is the pace and the ball goes straight away from the finger
		var g := clampf((v.length() if putt else v.y) / _pull_len, 0.0, 1.0)
		var m := mark_pull()
		if absf(g - m) < MAGNET:
			if absf(pull_goal - m) >= MAGNET:
				Sfx.buzz(18)      # a click onto the mark
				Sfx.play("click", -6.0)
			g = m
		pull_goal = g
		if putt:
			# the angle of the pull, eased in close to the start so a short pull can't swing it wildly
			var ang := atan2(v.x, maxf(v.y, 1.0))
			_side_goal = clampf(ang * PUTT_TURN * smoothstep(12.0, 60.0, v.length()), -PUTT_TURN_MAX, PUTT_TURN_MAX)
		else:
			var u := clampf(v.x / (get_viewport().get_visible_rect().size.x * SLING_SPAN), -1.0, 1.0)
			u *= smoothstep(0.0, 2.0 * SLING_DEAD, absf(u))
			_side_goal = u * SLING_AIM_MAX


## The power of a full pull: the club's full power, or for a putt PUTT_HEADROOM times this putt.
func _full_pull_power() -> float:
	if club.id == "putter":
		return clampf(maxf(full_power * PUTT_HEADROOM, full_power + 0.06), 0.02, 1.0)
	return 1.0


## Where on the pull (0 .. 1) the target is.
func mark_pull() -> float:
	return clampf(full_power / maxf(max_power, 0.0001), 0.0, 1.0)


## Power and the sideways aim follow the finger smoothly (touch reports arrive unevenly), and her
## backswing with them.
func _ease_toward_finger(delta: float) -> void:
	if pull == pull_goal and _side == _side_goal:
		return
	var k := 1.0 - exp(-delta * EASE)
	pull = lerpf(pull, pull_goal, k)
	if absf(pull - pull_goal) < 0.002:
		pull = pull_goal
	if _side != _side_goal:
		_side = lerpf(_side, _side_goal, 1.0 - exp(-delta * SIDE_EASE))
		if absf(_side - _side_goal) < 0.0005:
			_side = _side_goal
		_set_target(Vector2(ball.x, ball.y) + _aim_at_pull.rotated(_side) * _dist_at_pull, false)
	if phase == Phase.PULL:
		golfer.set_pull(_sprite_set("back"), pull)
		_pull_feel()


## As the pull grows the phone taps each quarter of the way.
var _pull_quarter := 0


func _pull_feel() -> void:
	var q := int(pull * 4.0 + 0.001)
	if q > _pull_quarter:
		Sfx.buzz(6)
	_pull_quarter = q


func _release() -> void:
	if target_dragging:
		target_dragging = false
		_set_target(target)             # solve the power exactly where it was left
		return
	if phase == Phase.PULL:
		if pull_goal < MIN_PULL:
			# let go without pulling: no shot, and the aim goes back to where it was
			phase = Phase.AIM
			pull = 0.0
			pull_goal = 0.0
			_side = 0.0
			_side_goal = 0.0
			_set_target(Vector2(ball.x, ball.y) + _aim_at_pull * _dist_at_pull)
			hud.hide_gauge()
			golfer.address(_sprite_set("back"))
		else:
			pull = pull_goal   # the shot is what the finger said, even if the ease hadn't caught up
			if _side != 0.0 or _side_goal != 0.0:
				_side = _side_goal
				_set_target(Vector2(ball.x, ball.y) + _aim_at_pull.rotated(_side) * _dist_at_pull)
			Sfx.play("twang", lerpf(-12.0, -4.0, pull), lerpf(1.15, 0.9, pull))
			Sfx.buzz(25)
			_shoot()


# ---------------------------------------------------------------- per frame
func _process(delta: float) -> void:
	phase_t += delta
	# a finished background download is unpacked only while she stands lining up a shot, never through
	# the opening, the pull, the swing or the ball's flight (scripts/holes.gd)
	Holes.hold = phase in [Phase.INTRO, Phase.PULL, Phase.SWING, Phase.FLIGHT] or _celebrating
	match phase:
		Phase.INTRO:
			_intro_cam()
			if phase_t >= _intro_length():
				_end_intro()
		Phase.AIM, Phase.PULL:
			_ease_toward_finger(delta)
			_aim_cam()
			_update_preview()
		Phase.SWING:
			_orbit(delta)
		Phase.FLIGHT:
			var was_flying := sim.state == BallSim.State.FLYING
			_time_scale = move_toward(_time_scale, FLIGHT_SPEED if was_flying else 1.0, delta * 2.0)
			sim.advance(delta * _time_scale)
			_prop_knocks()
			if not _landed_fx and sim.first_land != Vector3.INF:
				_landed_fx = true
				var surf := terrain.surface_at(sim.first_land.x, sim.first_land.y)
				var tint := HoleView._col(view.theme.get("water_glow"), Color(0.55, 0.75, 1.0)).lerp(Color(0.6, 0.8, 1.0), 0.3)
				fx.land(Terrain.to_world(sim.first_land), surf, tint)
				match surf:
					Terrain.Surface.WATER: Sfx.play("splash", -2.0)
					Terrain.Surface.SAND: Sfx.play("land_sand", -3.0)
					Terrain.Surface.PATH: Sfx.play("land_grass", -3.0, 1.5)       # a harder tap off the paving
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
			# the ball drops, then a cut to her, front-on, celebrating (Marc's fist pump), then the card
			if phase_t > CELEBRATE_AT and not _celebrating and golfer.sets.has(CELEBRATE_SET):
				_celebrating = true
				golfer.play_downswing(CELEBRATE_SET)       # where she stood for the stroke
				# in front of her, the flag behind her
				var g := golfer.global_position
				var away := g - Terrain.to_world(terrain.pin())
				away.y = 0.0
				away = away.normalized() if away.length() > 0.5 else Vector3.BACK
				_want_pos = g + away * 2.7 + Vector3(0, 1.05, 0)
				_want_target = g + Vector3(0, 0.95, 0)
				_want_fov = 50.0
				cam_pos = _want_pos
				cam_target = _want_target
				cam_fov = _want_fov
				hud.fade_in(0.3)
				Sfx.play("holed", -6.0)
			if not _celebrating:
				_chase_cam(delta)
			var card_at := CELEBRATE_AT + 3.6 if _celebrating else 2.4
			if phase_t > card_at and not hud.card.visible:
				Round.record(strokes)
				var detail := "%d strokes on a par %d" % [strokes, par]
				if Round.scores.size() > 1:
					detail += "\nRound: %s after %d" % [Round.to_par_text(), Round.scores.size()]
				hud.show_card(_score_name(strokes - par), detail, "Next hole" if Round.has_next() else ("New round" if Round.scores.size() > 1 else "Play again"))
	# the pull prompt, while lining up a hole's first shot
	hud.show_pull_tip(phase == Phase.AIM and strokes == 0 and not target_dragging)
	_apply_cam(delta)
	_update_ball_visual()   # after the camera moves: the ball's size is set from its distance to the camera
	_update_wind_hud()
	# while the camera follows the ball she steps out of shot if it comes right up beside her (after a
	# putt the camera settles where she stands)
	var following := (phase == Phase.FLIGHT and phase_t > SWING_HOLD) or phase == Phase.RESULT \
		or (phase == Phase.HOLED and not _celebrating)
	golfer.visible = not (following and cam.global_position.distance_to(golfer.global_position) < 3.0)


func _end_intro() -> void:
	intro_fx.stop()
	view.light_front(INF)            # every light on, whenever the opening ends (or is skipped)
	lantern.on = 1.0
	if _bag_light:
		_bag_light.light_energy = BAG_LIGHT
	phase = Phase.AIM
	_flyover(false)
	Quality.watching = true          # the scene's sharpness adapts from here on, never mid-flyover
	hud.flash("", 0.01)
	hud.hint.text = HINT
	_aim_cam()


# ---------------------------------------------------------------- camera
var _want_pos := Vector3.ZERO
var _want_target := Vector3.ZERO
var _want_fov := 64.0
var _cam_rate := 8.0


## Aiming and pulling: close behind her, so she fills the frame (the map in the corner shows where the
## shot comes down). While pulling the view holds the line the pull began on, so the sideways aim
## visibly swings the shot's line across the screen.
func _aim_cam_dir() -> Vector3:
	var d := _aim_at_pull if phase == Phase.PULL else aim
	return Vector3(d.x, d.y, 0)


func _aim_cam_pos() -> Vector3:
	var a := _aim_cam_dir()
	if club.id == "putter":
		return Terrain.to_world(ball - a * 3.6 + Vector3(0, 0, 3.3))     # up behind the ball, the green laid out
	return Terrain.to_world(ball - a * AIM_BACK + Vector3(0, 0, AIM_HEIGHT))


func _aim_cam_target() -> Vector3:
	var a := _aim_cam_dir()
	return _look_with_ball_at(Terrain.to_course(_aim_cam_pos()), a, PUTT_BALL_Y if club.id == "putter" else AIM_BALL_Y,
		_aim_fov())


func _aim_fov() -> float:
	return 66.0 if club.id == "putter" else AIM_FOV


func _aim_cam() -> void:
	_want_pos = _aim_cam_pos()
	_want_target = _aim_cam_target()
	_want_fov = _aim_fov()
	_cam_rate = 6.0


## A point to look at from `p` (course) straight along `a`, tipped down just enough to put the ball
## `ball_y` of the way down the screen with a view `fov` degrees wide (its height follows the aspect).
func _look_with_ball_at(p: Vector3, a: Vector3, ball_y: float, fov: float) -> Vector3:
	var vp := get_viewport().get_visible_rect().size
	var tan_v := tan(deg_to_rad(fov) * 0.5) * vp.y / maxf(vp.x, 1.0)
	var to_b := ball - p
	var pitch := atan2(-to_b.z, Vector2(to_b.x, to_b.y).length()) - atan(2.0 * (ball_y - 0.5) * tan_v)
	return Terrain.to_world(p + (a * cos(pitch) - Vector3(0, 0, sin(pitch))) * 30.0)


## The side-on view of her swing: beside her, level with her hips, looking a little ahead of her.
func _swing_cam() -> Array:
	var g := Terrain.to_course(golfer.position)
	var a := Vector3(aim.x, aim.y, 0)
	var r := Vector3(_right().x, _right().y, 0)
	var lead := golfer.swing_cam_lead(golfer.current_set)
	return [Terrain.to_world(g + r * 3.0 + a * (lead - 0.1) + Vector3(0, 0, 0.95)),
		Terrain.to_world(g + a * lead + Vector3(0, 0, 0.8)), 52.0]


## Let go on a full swing: the camera sweeps round from behind her to her side (she turns to face it
## half way round), then she swings. No cut, so the eye follows her round.
var _orbit_t := -1.0
var _orbit_from: Array = []
var _orbit_to: Array = []
var _orbit_turned := false


func _start_orbit() -> void:
	var back_pos := golfer.position
	var back_set := golfer.current_set
	_place_golfer_face()
	golfer.address(_sprite_set("face"))
	_orbit_to = _swing_cam()
	golfer.position = back_pos                  # she stays as she is until half way round
	golfer.set_pull(back_set, pull)
	_orbit_from = [cam_pos, cam_target, cam_fov]
	_orbit_turned = false
	_orbit_t = 0.0


func _orbit(delta: float) -> void:
	if _orbit_t < 0.0:
		return
	_orbit_t += delta
	var u := smoothstep(0.0, 1.0, clampf(_orbit_t / ORBIT_TIME, 0.0, 1.0))
	if u > 0.5 and not _orbit_turned:
		_orbit_turned = true
		_place_golfer_face()
		golfer.address(_sprite_set("face"))
	# round her: the angle and the distance from her eased, not a straight line through her
	var pivot := golfer.global_position
	var v0: Vector3 = _orbit_from[0] - pivot
	var v1: Vector3 = _orbit_to[0] - pivot
	var a0 := atan2(v0.x, v0.z)
	var a1 := a0 + angle_difference(a0, atan2(v1.x, v1.z))
	var ang := lerpf(a0, a1, u)
	var flat := lerpf(Vector2(v0.x, v0.z).length(), Vector2(v1.x, v1.z).length(), u)
	cam_pos = pivot + Vector3(sin(ang) * flat, lerpf(v0.y, v1.y, u), cos(ang) * flat)
	cam_target = (_orbit_from[1] as Vector3).lerp(_orbit_to[1], u)
	cam_fov = lerpf(_orbit_from[2], _orbit_to[2], u)
	_want_pos = cam_pos
	_want_target = cam_target
	_want_fov = cam_fov
	if _orbit_t >= ORBIT_TIME:
		_orbit_t = -1.0
		golfer.play_downswing(_sprite_set("face"))


func _chase_cam(_delta: float) -> void:
	if sim == null:
		return
	var b := sim.draw_pos()
	var dir := Vector3(flight_dir.x, flight_dir.y, 0)
	var side := Vector3(flight_dir.y, -flight_dir.x, 0)
	var p: Vector3
	if sim.state == BallSim.State.FLYING:
		# close behind the ball and a little to the side, so its scared face is in the picture all the
		# way; easing after it, so the camera falls behind as it leaves her and closes in as it slows
		# toward the top of its flight
		p = b - dir * CHASE_BACK + side * CHASE_SIDE + Vector3(0, 0, CHASE_UP)
		p.z = maxf(p.z, terrain.height(p.x, p.y) + 3.5)      # over the lanterns and headstones by the tee
		_cam_rate = lerpf(2.0, 5.5, clampf(sim.time / 1.2, 0.0, 1.0))
		_want_fov = 58.0
	else:
		p = b - dir * 6.5 + Vector3(0, 0, 2.6)
		_cam_rate = 2.5
	p.z = maxf(p.z, terrain.height(p.x, p.y) + 1.5)
	_want_pos = Terrain.to_world(p)
	_want_target = Terrain.to_world(b + sim.vel * (0.06 if sim.state == BallSim.State.FLYING else 0.12) + Vector3(0, 0, 0.3))


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


## Each hole opens on the lantern and her bag in the dark, rises behind the tee and flies on down the
## hole to the flag, the lights catching ahead of it.
var _shot := -1                  # which of the opening's shots is showing (a dip to black between them)
var _front := 0.0                # how far down the hole the lights have come on (HoleView.light_front)


func _intro_cam() -> void:
	var shots := _intro_shots()
	var i := 0
	var start := 0.0
	while i < shots.size() and phase_t >= start + float(shots[i].time):
		start += float(shots[i].time)
		i += 1
	if i != _shot:
		_shot = i
		if i == shots.size():
			hud.fade_in(0.35)                 # the dip to black, and up behind her
		if i == 0:
			var s0: Dictionary = shots[0]
			var p0: Array = _shot_pose(s0, 0.0)
			intro_fx.ambience = view.ambience
			intro_fx.begin(Terrain.to_world(p0[0]), Terrain.to_world(p0[1]), float(s0.time))
	if i < shots.size():
		var sh: Dictionary = shots[i]
		var u := clampf((phase_t - start) / float(sh.time), 0.0, 1.0)
		var pose: Array = _shot_pose(sh, _ease(u, str(sh.get("ease", "linear"))))
		cam_pos = Terrain.to_world(pose[0])
		cam_target = Terrain.to_world(pose[1])
		cam_fov = pose[2]
	else:
		_aim_cam()
		cam_pos = _want_pos
		cam_target = _want_target
		cam_fov = _want_fov
	_want_pos = cam_pos
	_want_target = cam_target
	_want_fov = cam_fov
	_intro_lights()


## The lights in the opening: all dark, then the lantern by the tee catches (and her bag in its glow)
## and the markers, then everything down the hole as the camera comes to it, a little ahead of it.
func _intro_lights() -> void:
	var goal := lerpf(-12.0, 14.0, smoothstep(1.6, 3.0, phase_t))
	if phase_t > TEE_TIME:
		var c := Terrain.to_course(cam_pos)
		var t := terrain.tee()
		goal = maxf(goal, Vector2(c.x - t.x, c.y - t.y).dot(_hole_dir()) + LIGHT_LEAD)
	_front = minf(goal, _front + LIGHT_SPEED * get_process_delta_time()) if phase_t > TEE_TIME else goal
	view.light_front(_front)
	# the lantern catches as the camera holds on it: a sputter, then the candle takes
	var catch := clampf((phase_t - 0.7) / 0.6, 0.0, 1.0)
	lantern.on = catch if catch >= 1.0 else catch * (0.6 + 0.4 * sin(phase_t * 37.0))
	if _bag_light:
		_bag_light.light_energy = BAG_LIGHT * lantern.on       # her bag is lit by the lantern beside it


## Straight down the hole, tee to pin (course coords, level).
func _hole_dir() -> Vector2:
	var t := terrain.tee()
	var p := terrain.pin()
	return Vector2(p.x - t.x, p.y - t.y).normalized()


## How a shot's time runs: "in" starts slow, "out" settles, "inout" both, "late" holds still first,
## "linear" holds its speed.
func _ease(u: float, how: String) -> float:
	match how:
		"in": return u * u * (1.5 - 0.5 * u)
		"out": return 1.0 - (1.0 - u) * (1.0 - u)
		"inout": return u * u * (3.0 - 2.0 * u)
		"late": return smoothstep(0.3, 1.0, u)          # held still a while, then eased in and out
	return u


## Where the camera is, what it looks at and its field of view, `u` (0..1) through a shot (course coords).
func _shot_pose(sh: Dictionary, u: float) -> Array:
	if str(sh.get("kind", "line")) == "fly":
		# along one smoothed line from the rise's end down the hole to the flag, at an even pace (the
		# shot's ease sets it going and brings it to rest), looking on along the same line ahead and
		# at the flag at the end
		var line: Array = sh.line
		var total: float = line[-1][1]
		var at := u * total
		var pos := _on_line(line, at)
		var look := _on_line(line, at + FLY_LOOK) + Vector3(0, 0, -4.0)
		look = look.lerp(sh.pin, smoothstep(total - FLY_LOOK * 1.5, total, at))
		look = look.lerp(sh.look_from, 1.0 - smoothstep(0.0, 0.2, u))   # handed on from the rise
		return [pos, look, lerpf(56.0, 46.0, u)]
	if str(sh.get("kind", "line")) == "rise":
		# through its keys on one rounded line at an even pace, the look turning one way only, through
		# the middle key's look, at a pace kept to the camera's (so it never swings faster than it moves)
		var line: Array = sh.line
		var at: float = u * float(line[-1][1])
		var dirs: Array = sh.dirs
		var x: float = at / float(line[-1][1])
		var xb: float = sh.xb                    # how far along the line its middle key is
		var y0 := atan2(dirs[0].x, dirs[0].y)
		var turn := wrapf(atan2(dirs[2].x, dirs[2].y) - y0, -PI, PI)
		var gb := clampf(wrapf(atan2(dirs[1].x, dirs[1].y) - y0, -PI, PI) / turn, 0.05, 0.95) if absf(turn) > 0.01 else 0.5
		var yaw := y0 + turn * _monotone(x, xb, gb)
		var pitch := lerpf(asin(dirs[0].z), asin(dirs[1].z), smoothstep(0.0, xb, x)) if x < xb \
			else lerpf(asin(dirs[1].z), asin(dirs[2].z), smoothstep(xb, 1.0, x))
		var p0 := _on_line(line, at)
		var dir := Vector3(sin(yaw) * cos(pitch), cos(yaw) * cos(pitch), sin(pitch))
		return [p0, p0 + dir * 20.0, lerpf(float(sh.fov), float(sh.fov_to), u)]
	# a straight move, turning steadily (not swinging) from one look to the other
	var p: Vector3 = (sh.from as Vector3).lerp(sh.to, u)
	var d0: Vector3 = ((sh.look as Vector3) - (sh.from as Vector3)).normalized()
	var d1: Vector3 = ((sh.look_to as Vector3) - (sh.to as Vector3)).normalized()
	var dir := d0.slerp(d1, u) if d0.dot(d1) > -0.99 else d0.lerp(d1, u).normalized()
	return [p, p + dir * 20.0, lerpf(float(sh.fov), float(sh.fov_to), u)]


## 0 .. 1 as `x` goes 0 .. 1, through (xb, gb), never turning back, still at both ends (a Hermite
## curve each side of the middle, its slope there kept low enough that it can't overshoot).
func _monotone(x: float, xb: float, gb: float) -> float:
	var m := minf(minf(3.0 * gb / xb, 3.0 * (1.0 - gb) / (1.0 - xb)), 1.2)
	if x < xb:
		var t := x / xb
		return _hermite(t, 0.0, gb, 0.0, m * xb)
	var t2 := (x - xb) / (1.0 - xb)
	return _hermite(t2, gb, 1.0, m * (1.0 - xb), 0.0)


func _hermite(t: float, p0: float, p1: float, m0: float, m1: float) -> float:
	var t2 := t * t
	var t3 := t2 * t
	return (2.0 * t3 - 3.0 * t2 + 1.0) * p0 + (t3 - 2.0 * t2 + t) * m0 + (-2.0 * t3 + 3.0 * t2) * p1 + (t3 - t2) * m1


const FLY_LOOK := 60.0           # m: the fly looks this far on ahead along its line


## The point `at` metres along a line of [point, metres from its start] (held at its ends).
func _on_line(line: Array, at: float) -> Vector3:
	if at <= 0.0:
		return line[0][0]
	for i in range(1, line.size()):
		if at <= float(line[i][1]):
			var a: float = line[i - 1][1]
			return (line[i - 1][0] as Vector3).lerp(line[i][0], (at - a) / maxf(float(line[i][1]) - a, 0.001))
	return line[-1][0]


## The fly's line: from `from` (where the rise ends, high behind the tee) down the line of play,
## coming down from tree-top height, to `end` before the flag; the corners rounded off (Chaikin) so
## it turns smoothly, never above or into the ground.
func _fly_line(from: Vector3, end: Vector3) -> Array:
	var pts: Array[Vector3] = [from]
	var n := 14
	for k in range(1, n):
		var f := lerpf(0.06, 0.94, float(k) / n)
		var g := _along_hole(f)
		pts.append(Vector3(g.x, g.y, g.z + lerpf(from.z - terrain.tee().z, 4.0, smoothstep(0.35, 1.0, f))))
	pts.append(end)
	return _rounded(pts, 2.2)


## A line through `pts` with its corners rounded off (Chaikin), as [point, metres from its start],
## kept `clear` metres over the ground.
func _rounded(pts: Array[Vector3], clear: float) -> Array:
	for it in 3:
		var sm: Array[Vector3] = [pts[0]]
		for k in pts.size() - 1:
			sm.append(pts[k].lerp(pts[k + 1], 0.25))
			sm.append(pts[k].lerp(pts[k + 1], 0.75))
		sm.append(pts[-1])
		pts = sm
	var line: Array = []
	var dist := 0.0
	for k in pts.size():
		var q := pts[k]
		q.z = maxf(q.z, terrain.height(q.x, q.y) + clear)
		if k > 0:
			dist += q.distance_to(line[-1][0])
		line.append([q, dist])
	return line


var _fly_cache := {}             # the fly's line for the hole being played (it's the same every frame)


## The opening, one camera move: close on the lantern by the tee in the dark (the lightning cracks,
## the lantern catches), pulling back past her bag and up behind the tee, turning one way to look down
## the hole; then on down the line of play, lower as it goes, in to the flag. Course coordinates.
func _intro_shots() -> Array:
	var rise := _tee_shot()
	var pin := terrain.pin()
	var path: Array = terrain.meta.path
	var way := (Vector2(pin.x, pin.y) - Vector2(path[-2][0], path[-2][1])).normalized()   # the way in to the green
	var e := Vector2(pin.x, pin.y) - way * 11.0
	var end := Vector3(e.x, e.y, maxf(pin.z, terrain.height(e.x, e.y)) + 2.6)
	var key := "%s %s" % [rise.to, end]
	if not _fly_cache.has(key):
		_fly_cache = {key: _fly_line(rise.to, end)}
	var fly := {"kind": "fly", "time": FLY_TIME, "ease": "inout", "line": _fly_cache[key], "pin": pin + Vector3(0, 0, 0.9),
		"look_from": rise.to + ((rise.look_to as Vector3) - (rise.to as Vector3)).normalized() * FLY_LOOK}
	return [rise, fly]


## The opening's first look: close on the lantern's carved face as it catches, easing back until
## she, her bag and the lantern are all in the frame, then up behind the tee, turning one way to look
## down the hole.
func _tee_shot() -> Dictionary:
	var t := terrain.tee()
	var d := _hole_dir()
	var r := Vector2(d.y, -d.x)            # to the right, looking down the hole
	var pumpkin := Terrain.to_course(lantern.pumpkin_world())
	var p2 := Vector2(pumpkin.x, pumpkin.y)
	var bag3 := Terrain.to_course(bag.global_position) if bag else t
	var both := (pumpkin + bag3 + Vector3(0, 0, 0.7)) * 0.5        # between the lantern and the top of the bag
	var a := p2 + _lantern_face * 2.3
	var b := Vector2(both.x, both.y) + (_lantern_face - d).normalized() * 6.5
	var e := Vector2(t.x, t.y) - d * 16.0 - r * 2.0
	var keys: Array[Vector3] = [Vector3(a.x, a.y, pumpkin.z + 0.15),
		Vector3(b.x, b.y, terrain.height(b.x, b.y) + 3.8), Vector3(e.x, e.y, t.z + 16.0)]
	var line := _rounded(keys, 0.6)
	var look_to := _along_hole(0.3) + Vector3(0, 0, 1.0)
	# held on the pumpkin while it catches ("late"), back to take in all three, then away
	return {"kind": "rise", "line": line, "to": keys[2], "xb": keys[0].distance_to(keys[1]) / (keys[0].distance_to(keys[1]) + keys[1].distance_to(keys[2])),
		"dirs": [(pumpkin - keys[0]).normalized(), (both - keys[1]).normalized(), (look_to - keys[2]).normalized()],
		"look_to": look_to, "fov": 46.0, "fov_to": 56.0, "time": TEE_TIME, "ease": "late"}


## How long the line of play is, tee to pin (metres).
func _hole_length() -> float:
	var path: Array = terrain.meta.path
	var total := 0.0
	for i in path.size() - 1:
		total += Vector2(path[i][0], path[i][1]).distance_to(Vector2(path[i + 1][0], path[i + 1][1]))
	return total


## The point `share` of the way along the line of play, on the ground.
func _along_hole(share: float) -> Vector3:
	var path: Array = terrain.meta.path
	var total := 0.0
	for i in path.size() - 1:
		total += Vector2(path[i][0], path[i][1]).distance_to(Vector2(path[i + 1][0], path[i + 1][1]))
	var want := total * share
	for i in path.size() - 1:
		var p0 := Vector2(path[i][0], path[i][1])
		var p1 := Vector2(path[i + 1][0], path[i + 1][1])
		var l := p0.distance_to(p1)
		if want <= l:
			var p := p0.lerp(p1, want / maxf(l, 0.001))
			return Vector3(p.x, p.y, terrain.height(p.x, p.y))
		want -= l
	var e := Vector2(path[-1][0], path[-1][1])
	return Vector3(e.x, e.y, terrain.height(e.x, e.y))


## How long the opening runs: its shots, then the swoop back to her.
func _intro_length() -> float:
	var total := FLY_BACK
	for sh in _intro_shots():
		total += float(sh.time)
	return total


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
	var name := Balls.chosen()
	_ball_face_tex = Balls.texture(name, "launch")
	ball_mesh.texture = _ball_face_tex
	ball_mesh.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	ball_mesh.shaded = false
	ball_mesh.double_sided = true
	ball_mesh.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	ball_mesh.alpha_cut = SpriteBase3D.ALPHA_CUT_DISABLED
	ball_mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(ball_mesh)
	var sm := SphereMesh.new()
	sm.radius = 0.5
	sm.height = 1.0
	sm.radial_segments = 16
	sm.rings = 8
	ball_plain.mesh = sm
	var pm := StandardMaterial3D.new()
	pm.albedo_texture = Balls.plain_texture(name)
	pm.emission_enabled = true                  # lit a little from within, so it reads at night
	pm.emission_texture = pm.albedo_texture
	pm.emission_energy_multiplier = 0.35
	pm.roughness = 0.6
	pm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_DEPTH_PRE_PASS
	ball_plain.material_override = pm
	ball_plain.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(ball_plain)
	wind_fx.mesh = wind_mesh
	var wm := StandardMaterial3D.new()
	wm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	wm.vertex_color_use_as_albedo = true
	wm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	wm.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	wm.cull_mode = BaseMaterial3D.CULL_DISABLED
	wm.disable_fog = true
	wind_fx.material_override = wm
	wind_fx.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(wind_fx)

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
	add_child(putt_grid)

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
	var splane := PlaneMesh.new()
	splane.size = Vector2.ONE
	spread_ring.mesh = splane
	var smat := StandardMaterial3D.new()
	smat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	smat.albedo_texture = _spread_texture()
	smat.albedo_color = Color(0.92, 0.95, 1.0, 0.95)
	smat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	smat.no_depth_test = true
	smat.disable_fog = true
	smat.render_priority = 7
	smat.cull_mode = BaseMaterial3D.CULL_DISABLED
	spread_ring.material_override = smat
	spread_ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(spread_ring)
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


## The margin of error: a soft white rim round a faint fill.
func _spread_texture() -> ImageTexture:
	var n := 256
	var img := Image.create(n, n, false, Image.FORMAT_RGBA8)
	for y in n:
		for x in n:
			var d := Vector2(x - n * 0.5 + 0.5, y - n * 0.5 + 0.5).length() / (n * 0.5)
			var rim := clampf(1.0 - absf(d - 0.92) / 0.08, 0.0, 1.0)
			var fill := 0.2 if d < 0.92 else 0.0
			img.set_pixel(x, y, Color(1, 1, 1, maxf(rim, fill)))
	return ImageTexture.create_from_image(img)


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
	var d := cam.global_position.distance_to(w)
	# drawn bigger than a real ball, and bigger the farther away, so its face always reads: a little
	# at her feet, more in the air where the camera chases it
	var flying := phase == Phase.FLIGHT and sim != null and sim.state == BallSim.State.FLYING
	var rolling_fast := phase == Phase.FLIGHT and sim != null and sim.vel.length() > 3.0
	# it grows as it climbs and shrinks back as it comes down, so it's ball size again as it lands;
	# up high its scared face fades in, and low it's the plain ball in its colour, seen rolling
	var up := b.z - terrain.height(b.x, b.y) if flying else 0.0
	_ball_look = lerpf(BALL_LOOK_GROUND, BALL_LOOK_AIR, smoothstep(0.3, BALL_GROW_HEIGHT, up))
	var size := maxf(2.0 * BallSim.RADIUS, d * _ball_look)       # the ball's drawn width, in metres
	var face := smoothstep(FACE_FROM, FACE_FULL, up)
	if _ball_face_tex:
		ball_mesh.pixel_size = size / (_ball_face_tex.get_height() * Balls.ART_FILL)
	var at := w + (Vector3.ZERO if flying else Vector3(0, size * 0.5, 0))   # sitting on the grass
	ball_mesh.position = at
	ball_mesh.modulate.a = face
	ball_mesh.visible = phase != Phase.HOLED and face > 0.01
	# the plain ball turns over as it goes (about the level axis across its path), at its drawn size
	if _ball_last != Vector3.INF:
		var moved := at - _ball_last
		var flat := Vector3(moved.x, 0, moved.z)
		if flat.length() > 0.0001 and flat.length() < 20.0:
			var axis := flat.normalized().cross(Vector3.DOWN)
			_ball_spin = Basis(axis, -flat.length() / maxf(size * 0.5, 0.01)) * _ball_spin
			_ball_spin = _ball_spin.orthonormalized()
	_ball_last = at
	ball_plain.transform = Transform3D(_ball_spin.scaled(Vector3.ONE * size), at)
	(ball_plain.material_override as StandardMaterial3D).albedo_color.a = 1.0 - face
	ball_plain.visible = phase != Phase.HOLED and face < 0.99
	_update_wind(w, size, flying)
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


var _ball_look := BALL_LOOK_GROUND
const BALL_GROW_HEIGHT := 9.0   # m above the ground where the ball is drawn at its biggest
const FACE_FROM := 2.5          # m up where its face starts to show ...
const FACE_FULL := 6.0          # ... and where it's all face


## Air rushing past the ball in flight: thin pale streaks round it that slide back past its face and
## fade (they travel with the ball, so none is left hanging where the camera flies through).
func _update_wind(w: Vector3, size: float, flying: bool) -> void:
	var dt := get_process_delta_time()
	if sim != null and flying:
		_wind_dir = (Terrain.to_world(sim.vel) - Terrain.to_world(Vector3.ZERO)).normalized()
		_streak_due += dt * STREAKS_PER_S
		while _streak_due >= 1.0:
			_streak_due -= 1.0
			var a := randf() * TAU
			# [angle round the ball, distance out (ball widths), length (ball widths), age]
			_streaks.append([a, randf_range(0.55, 1.1), randf_range(1.5, 3.0), 0.0])
	for st in _streaks:
		st[3] += dt
	_streaks = _streaks.filter(func(st): return st[3] < STREAK_LIFE)
	wind_mesh.clear_surfaces()
	if _streaks.is_empty() or _wind_dir == Vector3.ZERO:
		return
	var dir := _wind_dir
	var across := dir.cross(Vector3.UP).normalized()
	var up := across.cross(dir).normalized()
	var cp := cam.global_position
	wind_mesh.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
	for st in _streaks:
		var k: float = st[3] / STREAK_LIFE
		var off := (across * cos(st[0]) + up * sin(st[0])) * size * float(st[1])
		var head := w + off + dir * size * (1.2 - 7.0 * k)          # starts ahead of the ball, slides back past it
		var tail := head - dir * size * float(st[2])
		var side := dir.cross(cp - head).normalized() * size * 0.022
		var c := Color(0.88, 0.94, 1.0, 0.7 * sin(k * PI))
		var c_tail := Color(c, 0.0)
		for v in [[head + side, c], [head - side, c], [tail, c_tail]]:
			wind_mesh.surface_set_color(v[1])
			wind_mesh.surface_add_vertex(v[0])
	wind_mesh.surface_end()


func _show_preview(on: bool) -> void:
	var full: bool = club.get("id", "") != "putter"
	ring.visible = on and full and _wind_land != Vector3.INF
	target_ring.visible = on
	target_label.visible = on
	spread_ring.visible = on and full
	dots.multimesh.visible_instance_count = dots.multimesh.visible_instance_count if on else 0
	if not on:
		putt_grid.visible = false


## The shot preview, all without wind: the arc of this pull's flight (a full pull while aiming), the
## roll after it once things hold still, the target ring with its distance, and a faint ring where the
## wind would carry a perfect full shot.
func _update_preview() -> void:
	var putt: bool = club.id == "putter"
	var p := max_power * pull if phase == Phase.PULL else full_power
	var key := "%.4f|%.3f|%.3f|%s" % [p, target.x, target.y, club.id]
	var still := key == _preview_key
	# while the pull or the aim is moving, the flight is worked out at most ten times a second (each
	# run is a whole flight; the gauge and map keep up, the phone doesn't stall)
	if not still and phase == Phase.PULL and Time.get_ticks_msec() - _preview_ms < PREVIEW_EVERY_MS:
		_draw_preview(putt)
		_show_gauge()
		_show_aim_map(putt)
		return
	_preview_key = key
	if not still:
		_preview_ms = Time.get_ticks_msec()
		preview = BallSim.simulate(terrain, obstacles, terrain.pin(), Vector2.ZERO, ball,
			_launch(p, aim), club.lift, 0.05, not putt)
		var land: Vector3 = preview.first_land if preview.first_land != Vector3.INF else preview.end
		_carry_m = Vector2(land.x - ball.x, land.y - ball.y).length()
		_finish_m = _carry_m if putt else -1.0
		_finish_warn = _trouble(preview.state) if putt else ""
		_roll_pts = []
	elif _finish_m < 0.0 and not target_dragging:
		# held still: run it to the finish for the roll (a putt's preview already did)
		var whole := BallSim.simulate(terrain, obstacles, terrain.pin(), Vector2.ZERO, ball,
			_launch(p, aim), club.lift, 0.05)
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
				_launch(full_power, aim), club.lift, 0.0, true)
			_wind_land = w.first_land if w.first_land != Vector3.INF else w.end
	_draw_preview(putt)
	_show_aim_map(putt)
	if phase == Phase.PULL:
		_show_gauge()
	else:
		hud.hide_gauge()


var _roll_pts: Array = []
const PREVIEW_EVERY_MS := 100
var _preview_ms := 0


func _draw_preview(putt: bool) -> void:
	var mm := dots.multimesh
	var cp := cam.global_position
	var count := 0
	var pts: Array = preview.get("points", [])
	if putt:
		# putts: a straight line along the aim, as long as this pull rolls (the target's distance
		# while aiming); the grid's beads show which way it will break
		var roll: Array = (preview.get("points", []) as Array).duplicate()
		if not roll.is_empty():
			roll.append(preview.end)
		putt_grid.set_path(roll, preview.get("state", -1) == BallSim.State.HOLED, terrain.pin())
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
	# smaller on full shots, so the margin-of-error circle round it reads
	var size := clampf(cp.distance_to(tw) * (0.055 if not putt else 0.07), 0.35, 30.0)
	var pulse := 1.0 + 0.06 * sin(Time.get_ticks_msec() * 0.006)
	target_ring.global_transform = Transform3D(Basis().scaled(Vector3(size * pulse, 1.0, size * pulse)), tw)
	target_ring.visible = true
	var dist := Vector2(target.x - ball.x, target.y - ball.y).length()
	target_label.text = _dist_text(dist, putt)
	# up or down to it: what it plays like (a metre of rise is about a metre more to carry)
	var rise := terrain.height(target.x, target.y) - terrain.height(ball.x, ball.y)
	if not putt and absf(rise) >= 1.5:
		target_label.text += "\nplays %s %s" % [_dist_text(dist + rise, false).trim_suffix(" yds"), "uphill" if rise > 0.0 else "downhill"]
	# the margin of error, round where this pull comes down: wide across the line, shorter along it
	var r := _spread(_carry_m)
	spread_ring.visible = not putt and r > 0.3
	if spread_ring.visible:
		var b2 := Vector2(ball.x, ball.y)
		var c := b2 + aim * _carry_m
		var cw := Terrain.to_world(Vector3(c.x, c.y, terrain.height(c.x, c.y) + 0.1))
		var across := Terrain.to_world(Vector3(_right().x, _right().y, 0)) - Terrain.to_world(Vector3.ZERO)
		var along := Terrain.to_world(Vector3(aim.x, aim.y, 0)) - Terrain.to_world(Vector3.ZERO)
		spread_ring.global_transform = Transform3D(Basis(across * 2.0 * r, Vector3.UP, along * 2.0 * r * SPREAD_LONG), cw)
	target_label.global_position = tw + Vector3(0, size * 0.6 + 0.5, 0)
	target_label.visible = true
	ring.visible = _wind_land != Vector3.INF and Vector2(_wind_land.x - target.x, _wind_land.y - target.y).length() > 1.0
	if ring.visible:
		var ww := Terrain.to_world(_wind_land) + Vector3(0, 0.1, 0)
		ring.global_transform = Transform3D(Basis().scaled(Vector3(size * 0.7, 1.0, size * 0.7)), ww)


## The map in the corner while aiming and pulling: where the shot lands, against the target and the
## course (aiming: where the target's pull lands; pulling: where this pull does).
func _show_aim_map(putt: bool) -> void:
	if putt:
		hud.hide_aim_map()          # on the green the hole is in view, and the map would be all green
		return
	var m := hud.aim_map
	var b2 := Vector2(ball.x, ball.y)
	var dist := b2.distance_to(target)
	var pulling := phase == Phase.PULL
	m.ball = b2
	m.aim = _aim_at_pull if pulling else aim
	m.shot_dir = aim
	m.target = target
	m.land = b2 + aim * minf(_carry_m, maxf(_max_carry if pulling else dist, dist) * 1.2)
	var r := _spread(_carry_m)
	m.spread = Vector2(r, r * SPREAD_LONG)
	m.span = maxf(maxf(_max_carry if pulling else dist * 1.15, dist) * 1.08, 10.0 if putt else 40.0)
	var on_mark := not pulling or absf(pull - mark_pull()) < 0.005
	m.fill = Color(0.45, 1.0, 0.7) if on_mark else (Color(1.0, 0.32, 0.28) if pull > mark_pull() else Color(1.0, 0.62, 0.18))
	m.label = _dist_text(_carry_m if pulling else dist, putt)
	hud.show_aim_map()


func _show_gauge() -> void:
	var putt: bool = club.id == "putter"
	var per_m := 3.281 if putt else YD
	var mark := Vector2(target.x - ball.x, target.y - ball.y).length() * per_m
	hud.gauge.show_shot(_carry_m * per_m, _finish_m * per_m if _finish_m >= 0.0 else -1.0,
		mark, maxf(_max_carry, mark) * per_m, "ft" if putt else "yds", _finish_warn)


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
