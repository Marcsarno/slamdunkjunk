// Ground of a hole: painted tiling textures chosen per surface by the splat map that
// hole_gen.py writes (R fairway, G green, B sand, A deep-rough/out-of-bounds darkening,
// leftover = rough), times a detail map carrying mowing lanes and painted edge outlines.
// Course coords: x = world x, y = -world z.
shader_type spatial;
render_mode diffuse_lambert;

uniform sampler2D splat : filter_linear, repeat_disable;
uniform sampler2D detail : filter_linear, repeat_disable;
uniform sampler2D tex_rough : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D tex_fairway : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D tex_green : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D tex_sand : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform vec2 origin = vec2(0.0);
uniform vec2 extent = vec2(100.0);
uniform float tile_grass = 7.0;     // meters per texture repeat
uniform float tile_green = 4.5;
uniform float tile_sand = 3.5;
uniform vec3 dark_tint : source_color = vec3(0.42, 0.42, 0.40);
uniform float brightness = 1.0;
uniform vec3 grass_tint : source_color = vec3(1.0);   // pulls the painted grass toward the hole's palette

varying vec2 cxy;

void vertex() {
	vec3 w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	cxy = vec2(w.x, -w.z);
}

// two scales blended so the repeat isn't obvious from far away
vec3 tex2(sampler2D t, vec2 p, float tile) {
	vec3 a = texture(t, p / tile).rgb;
	vec3 b = texture(t, p / (tile * 3.7) + vec2(0.37, 0.71)).rgb;
	return mix(a, b, 0.35);
}

void fragment() {
	vec2 uv = (cxy - origin) / (extent - origin);
	uv.y = 1.0 - uv.y;
	vec4 w = texture(splat, uv);
	float det = texture(detail, uv).r * 2.0;
	vec3 c = tex2(tex_rough, cxy, tile_grass);
	c = mix(c, tex2(tex_fairway, cxy.yx, tile_grass), clamp(w.r, 0.0, 1.0));
	c = mix(c, tex2(tex_green, cxy, tile_green), clamp(w.g, 0.0, 1.0));
	c *= grass_tint;
	c = mix(c, tex2(tex_sand, cxy, tile_sand), clamp(w.b, 0.0, 1.0));
	c *= mix(vec3(1.0), dark_tint, clamp(w.a, 0.0, 1.0));
	ALBEDO = c * det * brightness;
	ROUGHNESS = 0.95;
	SPECULAR = 0.15;
}
