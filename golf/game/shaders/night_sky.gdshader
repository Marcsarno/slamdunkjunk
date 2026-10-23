// The night sky, in layers, back to front:
//   1. a deep, nearly black gradient (a little lighter just above the horizon)
//   2. stars: three painted strips (sparse bright, medium, dense faint), each wrapped round the sky and
//      twinkling a little
//   3. clouds: three painted layers drifting at their own speeds (a low bank on the horizon, puffy
//      clouds, high wisps), hiding the stars behind them, brighter toward the moon
//   4. optionally the hole's painting, only as a skyline (hills, castles) darkened into the night and
//      fading out above `paint_top_deg`, so its painted sky never shows
//   5. the moon, measured on the screen: every pixel's direction and the moon's are projected with
//      the camera's own orientation and field of view (set every frame by HoleView), and the disc is
//      round in those screen units, so it's always a perfect solid circle, in front of the clouds
// The strips are laid on the sky by azimuth and elevation, the azimuth squeezed by cos(elevation) so
// what's painted round stays round, and folded back and forth so they meet themselves with no seam.
shader_type sky;

uniform vec3 top_color : source_color = vec3(0.004, 0.006, 0.022);
uniform vec3 horizon_color : source_color = vec3(0.035, 0.045, 0.11);
uniform vec3 ground_color : source_color = vec3(0.02, 0.02, 0.04);
uniform float energy = 1.0;

uniform sampler2D stars_1 : source_color, filter_linear;
uniform sampler2D stars_2 : source_color, filter_linear;
uniform sampler2D stars_3 : source_color, filter_linear;
uniform float star_amount = 1.0;
uniform sampler2D twinkle_noise : repeat_enable, filter_linear;

uniform sampler2D clouds_bank : source_color, filter_linear;
uniform sampler2D clouds_puffs : source_color, filter_linear;
uniform sampler2D clouds_wisps : source_color, filter_linear;
uniform float cloud_amount = 0.6;
uniform float cloud_drift = 1.0;               // how fast they drift (1: the puffs cross 160 degrees in 10 minutes)
uniform vec3 cloud_tint : source_color = vec3(0.55, 0.55, 0.68);

uniform sampler2D backdrop : source_color, filter_linear_mipmap, repeat_enable;
uniform float paint_mix = 0.0;
uniform float span_deg = 90.0;
uniform float aspect = 1.5;
uniform float horizon_v = 0.8;
uniform float yaw_deg = 0.0;
uniform float paint_top_deg = 14.0;
uniform float paint_dark = 0.5;

uniform vec3 moon_dir = vec3(-0.3, 0.55, -0.78);
uniform sampler2D moon_tex : source_color, filter_linear_mipmap;
uniform vec3 moon_glow : source_color = vec3(0.85, 0.88, 1.0);
uniform float moon_radius = 0.034;             // share of the screen's height
uniform float screen_aspect = 0.46;            // width / height
uniform vec3 cam_right = vec3(1.0, 0.0, 0.0);
uniform vec3 cam_up = vec3(0.0, 1.0, 0.0);
uniform vec3 cam_fwd = vec3(0.0, 0.0, -1.0);
uniform vec2 tan_half = vec2(0.6, 1.3);        // tan of half the field of view, across and up
uniform float moon_energy = 1.05;

// A strip spanning `span` degrees across (so span / 3 high: the paintings are 3:1) with its bottom
// edge at elevation `el0`, slid sideways by `shift` (a share of its width). `stack` folds it upward
// too, so it fills the sky (the stars); otherwise it's one band (the clouds).
vec4 strip(sampler2D tex, float az, float el, float span, float el0, float shift, bool stack) {
	float u = az * cos(radians(el)) / span + shift;
	float v = (el - el0) / (span / 3.0);
	if (v < 0.0 || (v > 1.0 && !stack)) {
		return vec4(0.0);
	}
	float m = mod(u, 2.0);
	float n = mod(v, 2.0);
	return texture(tex, vec2(m < 1.0 ? m : 2.0 - m, 1.0 - (n < 1.0 ? n : 2.0 - n)));
}

void sky() {
	vec3 d = EYEDIR;
	float el = degrees(asin(clamp(d.y, -1.0, 1.0)));
	float az = degrees(atan(d.x, -d.z));

	// 1. deep night
	vec3 c = mix(horizon_color, top_color, pow(clamp(el / 40.0, 0.0, 1.0), 0.55));
	c = mix(c, ground_color, smoothstep(0.0, -4.0, el));

	if (el > -2.0) {
		// 2. stars
		vec4 s1 = strip(stars_1, az, el, 120.0, 4.0, 0.13, true);
		vec4 s2 = strip(stars_2, az, el, 100.0, 1.0, 0.57, true);
		vec4 s3 = strip(stars_3, az, el, 85.0, 2.0, 0.31, true);
		float tw = 0.65 + 0.7 * texture(twinkle_noise, vec2(az, el) * 0.11 + TIME * vec2(0.05, 0.08)).r;
		vec3 st = s1.rgb * s1.a * 1.3 * tw + s2.rgb * s2.a * (1.6 - 0.6 * tw) + s3.rgb * s3.a;
		c += st * star_amount * smoothstep(2.0, 10.0, el);

		// 3. clouds, far to near, each over what's behind it
		float t = TIME * cloud_drift / 600.0;
		float toward_moon = pow(max(dot(d, normalize(moon_dir)), 0.0), 8.0);
		vec3 lit = cloud_tint * (1.0 + 0.9 * toward_moon);
		vec4 k1 = strip(clouds_bank, az, el, 80.0, -3.0, 0.21 + t * 0.6, false);
		c = mix(c, k1.rgb * lit * 0.85, k1.a * cloud_amount);
		vec4 k2 = strip(clouds_puffs, az, el, 95.0, 9.0, 0.66 + t, false);
		c = mix(c, k2.rgb * lit, k2.a * cloud_amount);
		vec4 k3 = strip(clouds_wisps, az, el, 85.0, 16.0, 0.08 + t * 1.6, false);
		c = mix(c, k3.rgb * lit * 1.1, k3.a * cloud_amount * 0.8);
	}

	// 4. the painting, as a dark skyline only
	if (paint_mix > 0.0) {
		float t = (az - yaw_deg) / span_deg + 0.5;
		float m = mod(t, 2.0);
		float u = m < 1.0 ? m : 2.0 - m;
		float v = horizon_v - el / (span_deg / aspect);
		vec3 p = textureLod(backdrop, vec2(u, clamp(v, 0.003, 0.997)), 0.0).rgb * paint_dark;
		float a = paint_mix * (1.0 - smoothstep(paint_top_deg * 0.45, paint_top_deg, el));
		a *= 1.0 - smoothstep(0.997, 1.15, v);
		c = mix(c, p, a);
	}

	// 5. the moon: a round disc on the screen with a soft glow round it
	vec3 md = normalize(moon_dir);
	if (dot(d, cam_fwd) > 0.0 && dot(md, cam_fwd) > 0.0) {
		vec2 sd = vec2(dot(d, cam_right), dot(d, cam_up)) / (dot(d, cam_fwd) * tan_half);
		vec2 sm = vec2(dot(md, cam_right), dot(md, cam_up)) / (dot(md, cam_fwd) * tan_half);
		vec2 q = (sd - sm) * vec2(0.5 * screen_aspect, 0.5) / moon_radius;
		float r = length(q);
		float halo = (exp(-max(r - 1.0, 0.0) * 3.0) * 0.2 + exp(-max(r - 1.0, 0.0) * 0.6) * 0.06) * step(1.0, r);
		c += moon_glow * halo;
		if (r < 1.03) {
			vec3 disc = texture(moon_tex, vec2(0.5 + q.x * 0.5, 0.5 - q.y * 0.5) * 0.985 + 0.0075).rgb * moon_energy;
			c = mix(c, disc, smoothstep(1.02, 0.97, r));
		}
	}

	COLOR = c * energy;
}
