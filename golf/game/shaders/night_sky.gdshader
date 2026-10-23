// The night sky, in layers, back to front:
//   1. a deep, nearly black gradient (a little lighter just above the horizon)
//   2. stars: small, crisp, twinkling, thinning toward the horizon
//   3. clouds: dark drifting banks that hide the stars behind them, their edges lit by the moon
//   4. optionally the hole's painting, only as a skyline (hills, castles) darkened into the night and
//      fading out above `paint_top_deg`, so its painted sky never shows
//   5. the moon, measured on the screen: every pixel's direction and the moon's are projected with
//      the camera's own orientation and field of view (set every frame by HoleView), and the disc is
//      round in those screen units, so it's always a perfect solid circle, in front of the clouds
// The moon layer is skipped when Godot renders the sky into a cubemap (it has no screen there).
shader_type sky;

uniform vec3 top_color : source_color = vec3(0.004, 0.006, 0.022);
uniform vec3 horizon_color : source_color = vec3(0.035, 0.045, 0.11);
uniform vec3 ground_color : source_color = vec3(0.02, 0.02, 0.04);
uniform float energy = 1.0;

uniform float star_amount = 1.0;

uniform sampler2D cloud_noise : repeat_enable, filter_linear;
uniform float cloud_amount = 0.45;
uniform vec3 cloud_color : source_color = vec3(0.045, 0.05, 0.085);
uniform vec3 cloud_lit : source_color = vec3(0.42, 0.45, 0.58);
uniform vec2 cloud_wind = vec2(0.0035, 0.0012);

uniform sampler2D backdrop : source_color, filter_linear_mipmap, repeat_enable;
uniform float paint_mix = 0.0;
uniform float span_deg = 90.0;
uniform float aspect = 1.5;
uniform float horizon_v = 0.8;
uniform float yaw_deg = 0.0;
uniform float paint_top_deg = 14.0;
uniform float paint_dark = 0.5;

uniform vec3 moon_dir = vec3(-0.3, 0.55, -0.78);
uniform float moon_radius = 0.034;             // share of the screen's height
uniform float screen_aspect = 0.46;            // width / height
uniform vec3 cam_right = vec3(1.0, 0.0, 0.0);
uniform vec3 cam_up = vec3(0.0, 1.0, 0.0);
uniform vec3 cam_fwd = vec3(0.0, 0.0, -1.0);
uniform vec2 tan_half = vec2(0.6, 1.3);        // tan of half the field of view, across and up
uniform vec3 moon_color : source_color = vec3(1.0, 0.97, 0.9);
uniform float moon_energy = 1.2;

float hash13(vec3 p) {
	p = fract(p * 0.1031);
	p += dot(p, p.zyx + 31.32);
	return fract((p.x + p.y) * p.z);
}

// About one cell in sixty holds a star, at a jittered spot, some brighter than others.
float stars(vec3 d, float t) {
	vec3 p = d * 170.0;
	vec3 cell = floor(p);
	float h = hash13(cell);
	if (h < 0.982) {
		return 0.0;
	}
	vec3 j = vec3(hash13(cell + 1.7), hash13(cell + 3.1), hash13(cell + 5.3)) - 0.5;
	float r = length(p - (cell + 0.5 + j * 0.6));
	float bright = 0.45 + 0.55 * pow((h - 0.982) / 0.018, 2.0);
	float twinkle = 0.7 + 0.3 * sin(t * (1.3 + 3.0 * j.x) + h * 60.0);
	return smoothstep(0.46, 0.0, r) * bright * twinkle;
}

void sky() {
	vec3 d = EYEDIR;
	float el = degrees(asin(clamp(d.y, -1.0, 1.0)));

	// 1. deep night
	vec3 c = mix(horizon_color, top_color, pow(clamp(el / 40.0, 0.0, 1.0), 0.55));
	c = mix(c, ground_color, smoothstep(0.0, -4.0, el));

	// 2. stars
	c += vec3(0.85, 0.9, 1.0) * stars(d, TIME) * star_amount * smoothstep(3.0, 18.0, el) * 2.2;

	// 3. clouds: noise on a plane above, drifting; thin to nothing near the horizon
	if (el > 0.0 && cloud_amount > 0.0) {
		vec2 uv = d.xz / max(d.y, 0.06) * 0.16;
		float n = texture(cloud_noise, uv + TIME * cloud_wind).r * 0.65
			+ texture(cloud_noise, uv * 2.3 - TIME * cloud_wind * 1.7 + vec2(0.37, 0.61)).r * 0.35;
		float dens = smoothstep(0.48, 0.74, n) * cloud_amount * smoothstep(1.0, 12.0, el);
		float rim = smoothstep(0.46, 0.56, n) * (1.0 - smoothstep(0.56, 0.7, n));
		float toward_moon = pow(max(dot(d, normalize(moon_dir)), 0.0), 6.0);
		vec3 cc = mix(cloud_color, cloud_lit, clamp(toward_moon * 0.9 + rim * (0.25 + 0.75 * toward_moon), 0.0, 1.0));
		c = mix(c, cc, dens);
	}

	// 4. the painting, as a dark skyline only
	if (paint_mix > 0.0) {
		float az = degrees(atan(d.x, -d.z)) - yaw_deg;
		float t = az / span_deg + 0.5;
		float m = mod(t, 2.0);
		float u = m < 1.0 ? m : 2.0 - m;
		float v = horizon_v - el / (span_deg / aspect);
		vec3 p = textureLod(backdrop, vec2(u, clamp(v, 0.003, 0.997)), 0.0).rgb * paint_dark;
		float a = paint_mix * (1.0 - smoothstep(paint_top_deg * 0.45, paint_top_deg, el));
		a *= 1.0 - smoothstep(0.997, 1.15, v);
		c = mix(c, p, a);
	}

	// 5. the moon: a round disc on the screen, softly shaded, with a faint halo
	vec3 md = normalize(moon_dir);
	if (dot(d, cam_fwd) > 0.0 && dot(md, cam_fwd) > 0.0) {
		vec2 sd = vec2(dot(d, cam_right), dot(d, cam_up)) / (dot(d, cam_fwd) * tan_half);
		vec2 sm = vec2(dot(md, cam_right), dot(md, cam_up)) / (dot(md, cam_fwd) * tan_half);
		vec2 q = (sd - sm) * vec2(0.5 * screen_aspect, 0.5) / moon_radius;
		float r = length(q);
		// a soft glow round it, lighting the clouds and sky nearby
		float halo = (exp(-max(r - 1.0, 0.0) * 3.0) * 0.16 + exp(-max(r - 1.0, 0.0) * 0.6) * 0.05) * step(1.0, r);
		c += moon_color * halo;
		if (r < 1.03) {
			float mare = texture(cloud_noise, q * 0.18 + vec2(0.21, 0.83)).r;
			float shade = (1.0 - 0.18 * r * r) * (0.8 + 0.2 * smoothstep(0.35, 0.7, mare));
			vec3 disc = moon_color * shade * moon_energy;
			c = mix(c, disc, smoothstep(1.03, 0.97, r));
		}
	}

	COLOR = c * energy;
}
