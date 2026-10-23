class_name Balls
## Marc's Halloween golf balls: the one picked on the clubhouse bar (front.gd) is the ball she plays,
## its face going from calm to scared as the pull grows and staying scared in the air. Art:
## res://assets/balls/<ball>/{still,launch}.png, 512 px squares with the ball ART_FILL of the
## height (tools/prep_balls.py cuts them from the sheets).

const BALLS := ["pumpkin", "ghost", "skull", "mummy", "vampire", "frank", "bat"]
const NAMES := {"pumpkin": "Jack", "ghost": "Boo", "skull": "Bones", "mummy": "Wraps", "vampire": "The Count",
	"frank": "Frankie", "bat": "Batty"}
## Each ball's colour, for the plain ball seen rolling on the ground (its face only shows in the air).
const COLORS := {"pumpkin": Color(0.98, 0.46, 0.08), "ghost": Color(0.93, 0.92, 0.98), "skull": Color(0.9, 0.88, 0.84),
	"mummy": Color(0.86, 0.8, 0.64), "vampire": Color(0.86, 0.82, 0.95), "frank": Color(0.55, 0.78, 0.38),
	"bat": Color(0.42, 0.26, 0.55)}
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


## The plain ball's skin: its colour with darker stripes pole to pole (a spinning ball shows them turning).
static func plain_texture(ball: String) -> ImageTexture:
	var c: Color = COLORS.get(ball, Color(0.95, 0.95, 0.92))
	var dark := c.darkened(0.35)
	var w := 64
	var h := 32
	var img := Image.create(w, h, false, Image.FORMAT_RGB8)
	for x in w:
		var stripe := absf(sin(x / float(w) * TAU * 3.0)) > 0.93
		for y in h:
			img.set_pixel(x, y, dark if stripe else c)
	img.generate_mipmaps()
	return ImageTexture.create_from_image(img)
