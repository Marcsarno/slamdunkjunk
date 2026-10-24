// Ground of a hole. Base color is a calm per-surface palette (the look of the Blender render);
// the painted tiling textures add grain on top at `texture_strength`. The splat map from
// hole_gen.py picks the surface (R fairway, G green, B sand, A deep-rough/out-of-bounds
// darkening, leftover = rough); the detail map carries mowing lanes and edge outlines.
// Jack-o'-lantern light pools are added here for the nearest lanterns (cheaper than real lights).
// A large, slow noise (`blotch`) breaks up the big flat areas: drifts of fallen leaves and darker and
// lighter patches in the rough, a gentle unevenness in the fairway; greens and sand stay clean.
// Greens get their own finish: fine grass up close, mowing stripes across the approach (or a checker)
// that flip light and dark with the view like real cut grass, a darker collar round the edge, a dew
// sheen and a few glints in the moonlight, and a worn ring of turf round the cup.
// Course coords: x = world x, y = -world z.
shader_type spatial;
render_mode diffuse_lambert;

uniform sampler2D splat : filter_linear, repeat_disable;
uniform sampler2D detail : filter_linear, repeat_disable;
uniform sampler2D path_mask : hint_default_black, filter_linear, repeat_disable;   // the cart path
uniform sampler2D tex_path : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform vec3 col_path : source_color = vec3(0.33, 0.31, 0.28);
uniform sampler2D tex_rough : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D tex_fairway : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D tex_green : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D tex_sand : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D tex_cliff : source_color, filter_linear_mipmap_anisotropic, repeat_enable;   // steep rock faces
uniform float tile_cliff = 6.0;
uniform sampler2D blotch : filter_linear_mipmap, repeat_enable;
uniform vec3 leaf_color : source_color = vec3(0.42, 0.2, 0.07);
uniform float leaf_amount = 0.55;
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
uniform vec2 pin_xy = vec2(0.0);           // the cup, course coords
uniform vec2 green_dir = vec2(0.0, 1.0);   // the way the hole comes in to the green (course coords)
uniform float green_checker = 0.0;         // 1: a checkerboard cut instead of stripes
uniform float stripe_width = 2.4;          // m
uniform vec3 shade_dir = vec3(0.0, 0.5, 0.87);   // toward the key light (world)
uniform float slope_shade = 0.6;           // hill shading: how much the ground's shape is drawn out

const int MAX_POOLS = 16;
uniform vec4 pools[MAX_POOLS];          // xyz world position, w strength (0 = unused)
uniform vec3 pool_color : source_color = vec3(1.0, 0.55, 0.2);
uniform float pool_radius = 1.5;
uniform float pool_range = 9.0;

varying vec3 wpos;
varying vec3 wnorm;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnorm = (MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz;
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
	// the painted outlines round greens, bunkers and fairways (detail below ~0.88; the mowing lanes are
	// 0.9-1.1) read as an inked edge from afar but as a wide dark band underfoot: lift them up close
	float cam_d = length(CAMERA_POSITION_WORLD - wpos);
	det = mix(max(det, 0.9), det, smoothstep(10.0, 45.0, cam_d));

	det = mix(det, 1.0, smoothstep(0.55, 0.9, w.g) * step(0.94, det));    // the shader cuts the green's own lanes
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
	// --- the green's finish ---
	float on_green = smoothstep(0.55, 0.9, w.g);
	// the collar: the fringe's ring (green weight ~0.25 there), a shade darker and coarser
	float collar = smoothstep(0.12, 0.22, w.g) * (1.0 - smoothstep(0.32, 0.55, w.g)) * w.r;
	c *= 1.0 - 0.14 * collar;
	c *= mix(1.0, g_fair, 0.25 * collar);
	if (w.g > 0.05) {
		// fine grass up close (two tiny tilings), so the putting view has short blades, not a blur
		float near = 1.0 - smoothstep(4.0, 16.0, cam_d);
		vec2 r1 = mat2(vec2(0.8, 0.6), vec2(-0.6, 0.8)) * cxy;
		float fine = lum(texture(tex_green, cxy / 0.45).rgb) * 0.5 + lum(texture(tex_green, r1 / 0.28).rgb) * 0.5;
		c *= mix(1.0, fine / 0.38, 0.32 * near * on_green);
		// mowing stripes across the way in (or a checker): grass laid toward you reads light, away
		// dark, so they swap as the view turns round
		vec2 gd = normalize(green_dir);
		vec2 gr = vec2(gd.y, -gd.x);
		vec2 rel = cxy - pin_xy;
		float sa = sin(3.14159 * dot(rel, gd) / stripe_width);
		float band = sa;
		if (green_checker > 0.5) {
			band = sa * sin(3.14159 * dot(rel, gr) / stripe_width);
		}
		band = clamp(band * 4.0, -1.0, 1.0);
		vec3 vd = normalize(wpos - CAMERA_POSITION_WORLD);
		float facing = dot(normalize(vec2(vd.x, -vd.z) + vec2(0.0001)), gd);
		// side-on the stripes fade out rather than flipping light/dark in a hard line down the view
		c *= 1.0 + 0.07 * band * clamp(facing * 2.5, -1.0, 1.0) * on_green;
		// a worn, slightly paler ring of turf round the cup
		float dc = distance(cxy, pin_xy);
		c *= mix(vec3(1.0), vec3(1.07, 1.05, 0.9), (1.0 - smoothstep(0.12, 0.6, dc)) * on_green);
	}
	// big patches: two scales of noise, ~70 m and ~18 m across
	float big = texture(blotch, cxy / 70.0).r;
	float small = texture(blotch, cxy / 18.0 + vec2(0.31, 0.77)).r;
	float rough_w = clamp(1.0 - w.r - w.g - w.b, 0.0, 1.0);
	float patchy = (big - 0.5) * 0.5 + (small - 0.5) * 0.3;
	c *= 1.0 + patchy * (rough_w * 0.9 + w.r * 0.35);
	// fallen leaves drift in the rough, thickest where the small noise peaks inside the big one
	float leaves = smoothstep(0.55, 0.72, small * 0.6 + big * 0.5) * rough_w * leaf_amount;
	c = mix(c, leaf_color * (0.8 + 0.4 * small) * mix(1.0, grain, 0.6), leaves);
	c *= mix(vec3(1.0), dark_tint, w.a);
	// steep ground (a ravine's walls, a pond's banks) is bare rock, mapped onto the face it's on
	vec3 nw = normalize(wnorm);
	float steep = (1.0 - smoothstep(0.6, 0.78, nw.y)) * (1.0 - w.g) * (1.0 - w.b);
	if (steep > 0.01) {
		vec2 face_uv = abs(nw.x) > abs(nw.z) ? wpos.zy : wpos.xy;
		vec3 rock = texture(tex_cliff, face_uv / tile_cliff).rgb * 0.75;
		c = mix(c, rock, steep);
	}
	// the cart path: worn paving, a little lighter down the middle where the carts run
	float pm = texture(path_mask, uv).r;
	if (pm > 0.0) {
		vec3 pave = col_path * (0.75 + 0.5 * lum(tex2(tex_path, cxy, 2.2)) / 0.45);
		pave *= 0.92 + 0.16 * smoothstep(0.55, 1.0, pm) + (big - 0.5) * 0.2;
		c = mix(c, pave, smoothstep(0.15, 0.6, pm));
	}
	// hill shading, as on a relief map: the ground's tilt exaggerated five times against the key
	// light, so a 3-5% swell reads at night (faces toward the light a touch brighter, the backs of
	// rises darker) where plain moonlight would leave it flat
	vec3 ne = normalize(vec3(nw.x * 5.0, nw.y, nw.z * 5.0));
	vec3 sd = normalize(shade_dir);
	c *= 1.0 + clamp((dot(ne, sd) - sd.y) * slope_shade, -0.28, 0.22);
	c *= det * brightness;
	ALBEDO = c;
	// dew on the green: a soft sheen toward the moon, brighter at a glancing look
	float dew = smoothstep(0.55, 0.9, w.g);
	ROUGHNESS = mix(0.95, 0.72, dew);
	SPECULAR = mix(0.12, 0.2, dew);
	float fres = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 4.0);
	vec3 dew_glow = vec3(0.55, 0.65, 1.0) * fres * 0.05 * dew;
	// and a few drops catching the light up close, twinkling
	vec2 cell = floor(cxy * 16.0);
	float h = fract(sin(dot(cell, vec2(127.1, 311.7))) * 43758.5453);
	float tw = step(0.992, h) * smoothstep(0.75, 1.0, sin(TIME * 2.3 + h * 60.0));
	vec2 inr = fract(cxy * 16.0) - 0.5;
	tw *= 1.0 - smoothstep(0.05, 0.18, length(inr));
	dew_glow += vec3(0.8, 0.9, 1.0) * tw * 0.6 * dew * (1.0 - smoothstep(3.0, 14.0, cam_d));

	float pool = 0.0;
	for (int i = 0; i < MAX_POOLS; i++) {
		vec4 p = pools[i];
		if (p.w <= 0.0) { continue; }
		float d = distance(wpos, p.xyz);
		float r = d / pool_radius;
		pool += p.w / (1.0 + r * r) * smoothstep(pool_range, pool_range * 0.3, d);
	}
	EMISSION = c * pool_color * pool + dew_glow;
}
