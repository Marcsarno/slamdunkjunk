class_name Balls
## Marc's Halloween golf balls: the one picked on the clubhouse bar (front.gd) is the ball she plays,
## its face going from calm to scared as the pull grows and staying scared in the air. Art:
## res://assets/balls/<ball>/{still,launch}.png, 512 px squares with the ball ART_FILL of the
## height (tools/prep_balls.py cuts them from the sheets).

const BALLS := ["pumpkin", "ghost", "skull", "mummy", "vampire", "frank", "bat"]
const NAMES := {"pumpkin": "Jack", "ghost": "Boo", "skull": "Bones", "mummy": "Wraps", "vampire": "The Count",
	"frank": "Frankie", "bat": "Batty"}
const ART_FILL := 0.8
const SETTINGS := "user://settings.cfg"


## The ball picked in the clubhouse (remembered between visits).
static func chosen() -> String:
	var cfg := ConfigFile.new()
	var b := "pumpkin"
	if cfg.load(SETTINGS) == OK:
		b = str(cfg.get_value("play", "ball", b))
	return b if b in BALLS else "pumpkin"


static func choose(b: String) -> void:
	var cfg := ConfigFile.new()
	cfg.load(SETTINGS)
	cfg.set_value("play", "ball", b)
	cfg.save(SETTINGS)


## A ball's face: "still" or "launch" (scared).
static func texture(ball: String, pose: String) -> Texture2D:
	var path := "res://assets/balls/%s/%s.png" % [ball, pose]
	return load(path) if ResourceLoader.exists(path) else null
