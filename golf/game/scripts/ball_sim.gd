class_name BallSim
extends RefCounted
## Golf ball physics in course coordinates (x right, y down-range, z up, meters).
##
## Flight: gravity, quadratic air drag relative to the wind, and backspin lift that decays.
## Ground: a turf bounce (below), then a roll with per-surface resistance plus the slope pulling it
## downhill. Obstacles (tombstones,
## lanterns, trunks, canopies) come from props.json. The same code drives the aim preview.

enum State { FLYING, ROLLING, STOPPED, HOLED, WATER, OOB }

const G := 9.81
const RADIUS := 0.0214
const DRAG := 0.0045
const SPIN_DECAY := 0.15
const CUP_RADIUS := 0.054
const CUP_DRAWN := 1.8            # the cup is drawn this many times its real radius (so it reads) ...
const CUP_CATCH := CUP_RADIUS * CUP_DRAWN   # ... and the ball drops anywhere in the hole as drawn
const CUP_CAPTURE_SPEED := 1.8     # dead centre it drops this quick (the drawn hole is bigger than a real one)
const DT := 1.0 / 120.0
const ROLL_START_SPEED := 1.3     # bounces softer than this settle into a roll
const MAX_TIME := 25.0

# The turf bounce. A ball coming in steep plugs into the turf and loses more of its speed both ways;
# a low skip keeps its speed and runs on. Each impact keeps, of the speed along the ground,
#   keep * (1 - 0.6 sin(descent)),  less the backspin's bite (spin * grip, first landing mostly),
# and bounces back up at  restitution * cos^2(descent)  of its speed into the ground. Gentle hops
# (slow into the ground) lose little along it, so a drive skips, then runs out.
# surface id -> [restitution, keep along the ground, rolling resistance (m/s^2), backspin grip (m/s)]
const SURF := {
	Terrain.Surface.OOB: [0.15, 0.30, 6.0, 1.0],
	Terrain.Surface.ROUGH: [0.18, 0.24, 4.0, 1.2],
	Terrain.Surface.FAIRWAY: [0.27, 0.40, 1.45, 2.8],
	Terrain.Surface.GREEN: [0.22, 0.36, 0.62, 6.0],
	Terrain.Surface.SAND: [0.05, 0.08, 9.0, 0.5],
	Terrain.Surface.WATER: [0.0, 0.0, 99.0, 0.0],
	Terrain.Surface.TEE: [0.27, 0.40, 1.45, 2.8],
	Terrain.Surface.FRINGE: [0.24, 0.36, 1.2, 4.0],
	Terrain.Surface.DEEP: [0.12, 0.18, 6.0, 1.0],
	Terrain.Surface.PATH: [0.55, 0.80, 1.4, 0.5],        # paving: a big kick and a long run
}
const PLUG_SPEED := 12.0         # m/s into the ground at which a landing takes its full loss
# backspin checks the ball for a moment after it lands
const CHECK_TIME := 0.35
const CHECK_BRAKE := 2.5         # extra m/s^2 at full spin
# the turf's drag eases off as the ball slows (to ROLL_TAIL of it at a crawl, from ROLL_TAIL_SPEED
# down), so a roll dies away over its last metre instead of stopping dead
# On a green, a spinning iron or wedge doesn't die where it lands: it hops on, the spin grabs, and it
# draws back (up to SPIN_BACK_MAX m/s for a full wedge coming in steep, a chip barely checks), braked
# by BITE m/s^2 until it's running back at that speed; then it rolls out as usual.
const SPIN_BACK_MAX := 1.5
const BITE := 9.0
const ROLL_TAIL := 0.3
const ROLL_TAIL_SPEED := 1.0     # m/s
const STOP_SPEED := 0.025        # m/s: slower than this, where the slope can't move it, it's still

var terrain: Terrain
var obstacles: ObstacleGrid
var pin := Vector3.ZERO
var wind := Vector2.ZERO

var pos := Vector3.ZERO
var vel := Vector3.ZERO
var lift := 0.0
var state := State.STOPPED
var time := 0.0
var bounces := 0
var first_land := Vector3.INF
var apex := 0.0
var hit_obstacle := false
var hits: Array = []              # {shape, speed} per knock off a prop, for whoever plays the sounds
var caught := false               # came down in a spider web
var skid := 0.0
var spin := 0.0                  # 0 (a driver's low spin) .. 1 (a wedge's); bites at the first landing
var spin_back := 0.0             # m/s it's still to draw back on the green (0: no spin left to bite)
var _bite_dir := Vector3.ZERO    # the way it was going when it landed


func _init(t: Terrain, obs: ObstacleGrid, pin_pos: Vector3, wind_v: Vector2 = Vector2.ZERO) -> void:
	terrain = t
	obstacles = obs
	pin = pin_pos
	wind = wind_v


func launch(from: Vector3, velocity: Vector3, lift_coef: float) -> void:
	pos = from
	_prev_pos = from
	_acc = 0.0
	vel = velocity
	lift = lift_coef
	# the club's spin, from its lift: driver ~0.1, iron ~0.55, wedge 1, putter 0
	spin = clampf((lift_coef - 0.0015) / 0.0009, 0.0, 1.0)
	skid = 0.0
	spin_back = 0.0
	time = 0.0
	bounces = 0
	first_land = Vector3.INF
	apex = from.z
	hit_obstacle = false
	hits.clear()
	caught = false
	_over_cup = false
	state = State.FLYING if velocity.z > 0.01 else State.ROLLING


func ground_z(x: float, y: float) -> float:
	return terrain.height(x, y) + RADIUS


func is_done() -> bool:
	return state >= State.STOPPED


## Advance by `dt` seconds using fixed internal substeps. Time left over (less than one step) carries
## to the next frame, so the ball moves evenly whatever the frame rate; draw_pos() blends the last two
## steps by that leftover for a smooth picture.
var _acc := 0.0
var _prev_pos := Vector3.ZERO


func advance(dt: float) -> void:
	_acc += dt
	while _acc >= DT:
		if is_done():
			_acc = 0.0
			return
		_prev_pos = pos
		_step(DT)
		_acc -= DT


func draw_pos() -> Vector3:
	if is_done():
		return pos
	return _prev_pos.lerp(pos, clampf(_acc / DT, 0.0, 1.0))


func _step(dt: float) -> void:
	time += dt
	if time > MAX_TIME:
		state = State.STOPPED
		return
	if state == State.FLYING:
		_fly(dt)
	elif state == State.ROLLING:
		_roll(dt)


func _fly(dt: float) -> void:
	var air := vel - Vector3(wind.x, wind.y, 0.0)
	var s := air.length()
	var acc := Vector3(0, 0, -G) - air * (DRAG * s)
	# lift: perpendicular to travel, in the vertical plane that contains it
	var h := Vector2(vel.x, vel.y)
	if h.length() > 0.01 and lift > 0.0:
		var hd := h.normalized()
		var up_perp := Vector3(-hd.x * vel.z, -hd.y * vel.z, h.length())
		acc += up_perp * (lift * s)
		lift *= 1.0 - SPIN_DECAY * dt
	vel += acc * dt
	var prev := pos
	pos += vel * dt
	apex = maxf(apex, pos.z)
	_collide_obstacles(prev)
	var gz := ground_z(pos.x, pos.y)
	if pos.z <= gz:
		pos.z = gz
		_land()


func _land() -> void:
	var surf := terrain.surface_at(pos.x, pos.y)
	if first_land == Vector3.INF:
		first_land = pos
	if surf == Terrain.Surface.WATER:
		state = State.WATER
		return
	if surf == Terrain.Surface.OOB:
		state = State.OOB
		return
	if terrain.in_web(pos.x, pos.y):
		# caught in a giant spider web: it stops dead where it comes down
		caught = true
		vel = Vector3.ZERO
		state = State.STOPPED
		return
	bounces += 1
	var p: Array = SURF[surf]
	var n := terrain.normal(pos.x, pos.y)
	var vn := -vel.dot(n)                    # speed into the ground
	if vn <= 0.0:
		return
	var vt_vec := vel + n * vn
	var vt := vt_vec.length()
	var sin_d := clampf(vn / maxf(vel.length(), 0.001), 0.0, 1.0)
	var plug := clampf(vn / PLUG_SPEED, 0.0, 1.0)
	var keep := 1.0 - (1.0 - float(p[1]) * (1.0 - 0.6 * sin_d)) * plug
	var along := vt * keep - spin * float(p[3]) * plug
	var dir := vt_vec / vt if vt > 0.0001 else Vector3.ZERO
	var green := surf == Terrain.Surface.GREEN or surf == Terrain.Surface.FRINGE
	if bounces == 1 and spin > 0.4 and green:
		# the green takes it: a hop on, then the spin bites (in _roll) and draws it back
		along = vt * keep
		spin_back = SPIN_BACK_MAX * (spin - 0.4) / 0.6 * pow(clampf(vn / 14.0, 0.0, 1.0), 2.0)
		_bite_dir = Vector3(dir.x, dir.y, 0.0).normalized()
	along = maxf(along, 0.0)
	var out_n: float = vn * float(p[0]) * (1.0 - sin_d * sin_d)
	if bounces == 1 and spin > 0.3 and spin_back <= 0.0:
		skid = CHECK_TIME
	spin *= 0.2                              # the turf takes most of the spin at the first landing
	vel = dir * along + n * out_n
	if out_n < ROLL_START_SPEED:
		vel = dir * along
		state = State.ROLLING


func _roll(dt: float) -> void:
	var surf := terrain.surface_at(pos.x, pos.y)
	if surf == Terrain.Surface.WATER:
		state = State.WATER
		return
	if surf == Terrain.Surface.OOB:
		state = State.OOB
		return
	if terrain.in_web(pos.x, pos.y):
		caught = true                          # rolled into a web: stuck fast
		vel = Vector3.ZERO
		state = State.STOPPED
		return
	var resist: float = SURF[surf][2]
	if skid > 0.0:
		skid -= dt
		resist += CHECK_BRAKE * clampf(spin * 5.0, 0.0, 1.0)
	var n := terrain.normal(pos.x, pos.y)
	var slope := Vector3(0, 0, -G) - n * (-G * n.z)       # gravity along the ground
	var speed := vel.length()
	if spin_back > 0.0:
		# the spin grabbing: braked hard along the way it came in, through a stop, until it's running
		# back at spin_back; the slope still pulls
		var back := vel.dot(_bite_dir)
		vel += (slope - _bite_dir * BITE) * dt
		if vel.dot(_bite_dir) <= -spin_back or terrain.surface_at(pos.x, pos.y) != Terrain.Surface.GREEN and back < 0.0:
			spin_back = 0.0
		vel -= n * vel.dot(n)
		var prev0 := pos
		pos += vel * dt
		pos.z = ground_z(pos.x, pos.y)
		_collide_obstacles(prev0)
		_check_cup()
		return
	var holds := slope.length() < resist * 0.9               # the slope can't start it rolling again
	if speed < STOP_SPEED and holds:
		vel = Vector3.ZERO
		state = State.STOPPED
		_check_cup()                             # come to rest on the drawn rim: it drops
		return
	var dir := vel / speed if speed > 0.0001 else Vector3.ZERO
	var drag := resist * lerpf(ROLL_TAIL, 1.0, clampf(speed / ROLL_TAIL_SPEED, 0.0, 1.0))
	if holds:
		# still more than the slope's pull along its way, so it can't creep on downhill for ever
		drag = maxf(drag, minf(resist, slope.dot(dir) + 0.1 * resist))
	vel += (slope - dir * drag) * dt
	# friction must not reverse the ball within one step
	if speed > 0.0001 and vel.dot(dir) < 0.0 and holds:
		vel = Vector3.ZERO
	vel -= n * vel.dot(n)
	var prev := pos
	pos += vel * dt
	pos.z = ground_z(pos.x, pos.y)
	_collide_obstacles(prev)
	_check_cup()


func _check_cup() -> void:
	var d := Vector2(pos.x - pin.x, pos.y - pin.y)
	var speed := vel.length()
	# hanging on the rim as drawn when it stops: it drops (what you see is what counts)
	if speed < 0.08 and d.length() < CUP_CATCH + RADIUS * 0.6:
		_drop()
		return
	if d.length() > CUP_CATCH:
		_over_cup = false
		return
	if _over_cup:
		# rolling on across the hole: once slow enough anywhere over it, it falls in
		if speed < CUP_CAPTURE_SPEED * 0.4:
			_drop()
		return
	_over_cup = true
	var dir := Vector2(vel.x, vel.y).normalized() if speed > 0.0001 else Vector2.ZERO
	# how far off the cup's centre its line passes: dead centre it drops up to CUP_CAPTURE_SPEED,
	# nearer the rim it needs to be slower (it has less hole to fall into)
	var off := clampf(absf(dir.cross(-d)) / CUP_CATCH, 0.0, 1.0)
	if speed < CUP_CAPTURE_SPEED * sqrt(1.0 - off * off * 0.85):
		_drop()
		return
	# too quick: it hops the hole and rolls on, a little slower, a rim catch turning it aside
	var side := signf(dir.cross(-d))
	var turn := side * off * off * 0.5           # radians, up to ~30 degrees off the rim
	var h := Vector2(vel.x, vel.y).rotated(turn) * lerpf(0.85, 0.7, off)
	vel = Vector3(h.x, h.y, vel.z)


var _over_cup := false


func _drop() -> void:
	state = State.HOLED
	pos = Vector3(pin.x, pin.y, pin.z - 0.05)
	vel = Vector3.ZERO


func _collide_obstacles(prev: Vector3) -> void:
	if obstacles == null:
		return
	var hit := obstacles.collide(pos, vel, RADIUS)
	if hit.is_empty():
		return
	hit_obstacle = true
	hits.append({"shape": hit.shape, "speed": vel.length()})
	pos = hit.pos
	vel = hit.vel
	if state == State.ROLLING and vel.length() < 0.05:
		state = State.STOPPED


## Run a full shot without touching this instance's live state. Returns a summary used by
## the aim preview and the tests.
static func simulate(t: Terrain, obs: ObstacleGrid, pin_pos: Vector3, wind_v: Vector2, from: Vector3,
		velocity: Vector3, lift_coef: float, record_every: float = 0.0, max_flight_only := false) -> Dictionary:
	var s := BallSim.new(t, obs, pin_pos, wind_v)
	s.launch(from, velocity, lift_coef)
	var pts: Array[Vector3] = []
	var next_rec := 0.0
	while not s.is_done():
		s._step(DT)
		if record_every > 0.0 and s.time >= next_rec:
			pts.append(s.pos)
			next_rec += record_every
		if max_flight_only and s.first_land != Vector3.INF:
			break
	return {"end": s.pos, "state": s.state, "first_land": s.first_land, "apex": s.apex, "time": s.time,
		"points": pts}
