// Ground of a hole. Base color is a calm per-surface palette (the look of the Blender render);
// the painted tiling textures add grain on top at `texture_strength`. The splat map from
// hole_gen.py picks the surface (R fairway, G green, B sand, A deep-rough/out-of-bounds
// darkening, leftover = rough); the detail map carries mowing lanes and edge outlines.
// Jack-o'-lantern light pools are added here for the nearest lanterns (cheaper than real lights).
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
uniform float tile_grass = 7.0;
uniform float tile_green = 4.5;
uniform float tile_sand = 3.5;
uniform vec3 col_rough : source_color = vec3(0.15, 0.25, 0.09);
uniform vec3 col_fairway : source_color = vec3(0.29, 0.47, 0.13);
uniform vec3 col_green : source_color = vec3(0.33, 0.53, 0.15);
uniform vec3 col_sand : source_color = vec3(0.72, 0.60, 0.42);
uniform vec3 dark_tint : source_color = vec3(0.45, 0.45, 0.42);
uniform float texture_strength = 0.35;
uniform float brightness = 1.0;

const int MAX_POOLS = 16;
uniform vec4 pools[MAX_POOLS];          // xyz world position, w strength (0 = unused)
uniform vec3 pool_color : source_color = vec3(1.0, 0.55, 0.2);
uniform float pool_radius = 1.5;
uniform float pool_range = 9.0;

varying vec3 wpos;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

vec3 tex2(sampler2D t, vec2 p, float tile) {
	vec3 a = texture(t, p / tile).rgb;
	vec3 b = texture(t, p / (tile * 3.7) + vec2(0.37, 0.71)).rgb;
	return mix(a, b, 0.35);
}

float lum(vec3 c) { return dot(c, vec3(0.3, 0.55, 0.15)); }

void fragment() {
	vec2 cxy = vec2(wpos.x, -wpos.z);
	vec2 uv = (cxy - origin) / (extent - origin);
	uv.y = 1.0 - uv.y;
	vec4 w = clamp(texture(splat, uv), 0.0, 1.0);
	float det = texture(detail, uv).r * 2.0;

	vec3 base_col = mix(col_rough, col_fairway, w.r);
	base_col = mix(base_col, col_green, w.g);
	base_col = mix(base_col, col_sand, w.b);
	// grain: brightness variation of the painted textures, normalized around 1
	float g_rough = lum(tex2(tex_rough, cxy, tile_grass)) / 0.16;
	float g_fair = lum(tex2(tex_fairway, cxy.yx, tile_grass)) / 0.32;
	float g_green = lum(tex2(tex_green, cxy, tile_green)) / 0.38;
	float g_sand = lum(tex2(tex_sand, cxy, tile_sand)) / 0.62;
	float grain = mix(g_rough, g_fair, w.r);
	grain = mix(grain, g_green, w.g);
	grain = mix(grain, g_sand, w.b);
	vec3 c = base_col * mix(1.0, grain, texture_strength);
	c *= mix(vec3(1.0), dark_tint, w.a);
	c *= det * brightness;
	ALBEDO = c;
	ROUGHNESS = 0.95;
	SPECULAR = 0.12;

	float pool = 0.0;
	for (int i = 0; i < MAX_POOLS; i++) {
		vec4 p = pools[i];
		if (p.w <= 0.0) { continue; }
		float d = distance(wpos, p.xyz);
		float r = d / pool_radius;
		pool += p.w / (1.0 + r * r) * smoothstep(pool_range, pool_range * 0.3, d);
	}
	EMISSION = c * pool_color * pool;
}
