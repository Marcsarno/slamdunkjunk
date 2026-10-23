extends Node
## How sharply the 3D scene is drawn (an autoload, so it holds across holes). The HUD is always drawn
## at the screen's full resolution; only the 3D world is drawn smaller and scaled up, which at phone
## size costs little to the eye and a lot less work for the phone.
##
## On the web it adapts: it starts at a middle step and watches the frame rate while a hole is
## played. Running slow for a couple of seconds steps the scene down; running smooth for a good while
## steps it back up (slowly, so it doesn't flip back and forth). It never changes during a hole's
## opening flyover (main turns watching on after it), and the step a phone settles on is remembered
## for its next visit, so it starts where it runs smoothly. Desktop and the tests draw at full
## size with anti-aliasing. --quality=<scale> (0.5 .. 1) fixes the scale anywhere, for checking how a
## step looks.

const STEPS := [1.0, 0.85, 0.75, 0.65, 0.55]   # share of the screen's resolution the 3D scene is drawn at
const START := 2                               # the web starts at 0.75
const SLOW_MS := 22.0                          # averaging slower than this (about 45 fps) steps down ...
const SLOW_FOR := 2.0                          # ... after this many seconds
const FAST_MS := 17.5                          # averaging faster than this (about 57 fps) steps up ...
const FAST_FOR := 12.0                         # ... after this many seconds
const FAST_FOR_AFTER_DROP := 40.0              # ... or this long once it has had to step down
const SETTINGS := "user://settings.cfg"

var step := START
var adaptive := false
var watching := false          # main turns this on while a hole is being played (not on the menu or loading)
var _avg_ms := 16.7
var _slow_t := 0.0
var _fast_t := 0.0
var _dropped := false


func _ready() -> void:
	adaptive = OS.has_feature("web")
	if not adaptive:
		step = 0
	else:
		var cfg := ConfigFile.new()
		if cfg.load(SETTINGS) == OK:
			step = clampi(int(cfg.get_value("video", "step", START)), 1, STEPS.size() - 1)
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--quality="):
			adaptive = false
			step = -1
			_apply_scale(clampf(float(a.trim_prefix("--quality=")), 0.5, 1.0))
			return
	_apply()


func scale() -> float:
	return get_viewport().scaling_3d_scale


func _apply() -> void:
	_apply_scale(STEPS[step])


## The opening flyover sweeps the whole hole at speed: drawn at FLYOVER_SCALE (motion hides the
## softness) it stays smooth on a phone; then back to the step the frame rate chose.
const FLYOVER_SCALE := 0.6


func flyover(on: bool) -> void:
	if step < 0:
		return                      # fixed with --quality
	_apply_scale(minf(STEPS[step], FLYOVER_SCALE) if on and adaptive else STEPS[step])


func _remember() -> void:
	var cfg := ConfigFile.new()
	cfg.load(SETTINGS)
	cfg.set_value("video", "step", step)
	cfg.save(SETTINGS)


func _apply_scale(s: float) -> void:
	var vp := get_viewport()
	vp.scaling_3d_mode = Viewport.SCALING_3D_MODE_BILINEAR
	vp.scaling_3d_scale = s
	# anti-aliasing only at full size: scaled up, the edges are already soft, and it would double the work
	vp.msaa_3d = Viewport.MSAA_2X if s >= 0.999 else Viewport.MSAA_DISABLED


func _process(delta: float) -> void:
	if not adaptive or not watching:
		_slow_t = 0.0
		_fast_t = 0.0
		return
	var ms := minf(delta * 1000.0, 100.0)       # one long hitch (a hole loading) doesn't swing the average far
	_avg_ms = lerpf(_avg_ms, ms, 0.05)
	if _avg_ms > SLOW_MS:
		_slow_t += delta
		_fast_t = 0.0
		if _slow_t > SLOW_FOR and step < STEPS.size() - 1:
			step += 1
			_dropped = true
			_slow_t = 0.0
			_avg_ms = 16.7
			_apply()
			_remember()
	elif _avg_ms < FAST_MS:
		_fast_t += delta
		_slow_t = 0.0
		if _fast_t > (FAST_FOR_AFTER_DROP if _dropped else FAST_FOR) and step > 1:   # the web tops out at 0.85
			step -= 1
			_fast_t = 0.0
			_apply()
			_remember()
	else:
		_slow_t = maxf(0.0, _slow_t - delta)
		_fast_t = maxf(0.0, _fast_t - delta)
