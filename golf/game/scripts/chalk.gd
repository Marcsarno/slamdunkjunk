class_name Chalk
## Chalk on a blackboard, shared by the clubhouse menu and the score card: one material (the chalk
## shader with its grain) and the two chalk fonts: Fredericka the Great for headings (a hand-chalked
## sign letter) and Caveat Brush for the writing (a fat stick of chalk, easy to read small).

const WHITE := Color(0.96, 0.95, 0.9)
const DIM := Color(0.96, 0.95, 0.9, 0.58)
const ORANGE := Color(1.0, 0.72, 0.38)

static var _mat: ShaderMaterial


static func material() -> ShaderMaterial:
	if _mat == null:
		var noise := FastNoiseLite.new()
		noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
		noise.frequency = 0.09
		noise.fractal_octaves = 3
		var grain := NoiseTexture2D.new()
		grain.width = 256
		grain.height = 256
		grain.seamless = true
		grain.noise = noise
		_mat = ShaderMaterial.new()
		_mat.shader = load("res://shaders/chalk.gdshader")
		_mat.set_shader_parameter("grain", grain)
	return _mat


static func head_font() -> Font:
	return load("res://assets/fonts/FrederickatheGreat-Regular.ttf")


static func hand_font() -> Font:
	return load("res://assets/fonts/CaveatBrush-Regular.ttf")


## A label written in chalk.
static func label(text: String, font: Font, size: int, color := WHITE) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_override("font", font)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	dust(l, color)
	l.material = material()
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


## The faint cloud of dust round chalk letters (a soft outline in the chalk's colour).
static func dust(c: Control, color: Color) -> void:
	c.add_theme_color_override("font_outline_color", Color(color, 0.1))
	c.add_theme_constant_override("outline_size", 7)
