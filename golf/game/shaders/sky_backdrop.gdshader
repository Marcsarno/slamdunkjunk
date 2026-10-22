// Sky for a hole. Two looks mixed by `paint_mix`:
//   0 = plain night (the Blender-render look): a gradient from horizon glow to a dark zenith
//   1 = the hole's painted backdrop (moon painted out by prep_backdrops.py), wrapped around the
//       course by mirroring it past its edges, and hazed toward the fog color by `haze`.
// Either way the moon is a separate sprite drawn once, in the direction the moonlight comes from.
shader_type sky;

uniform sampler2D backdrop : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D moon_tex : source_color, filter_linear, repeat_disable;
uniform float paint_mix = 1.0;
uniform float haze = 0.0;
uniform float span_deg = 90.0;
uniform float aspect = 1.5;
uniform float horizon_v = 0.8;
uniform float yaw_deg = 0.0;
uniform vec3 moon_dir = vec3(0.0, 0.6, -0.8);
uniform float moon_half = 0.08;
uniform float moon_scale = 1.0;
uniform vec3 top_color : source_color = vec3(0.12, 0.08, 0.25);
uniform vec3 horizon_color : source_color = vec3(0.45, 0.32, 0.55);
uniform vec3 ground_color : source_color = vec3(0.35, 0.3, 0.45);
uniform float energy = 1.0;

void sky() {
	vec3 d = normalize(EYEDIR);
	float az = degrees(atan(d.x, -d.z)) - yaw_deg;
	float el = degrees(asin(clamp(d.y, -1.0, 1.0)));

	vec3 night = mix(horizon_color, top_color, pow(clamp(el / 55.0, 0.0, 1.0), 0.6));
	night = mix(night, ground_color, smoothstep(0.0, -3.0, el));

	vec3 c = night;
	if (paint_mix > 0.0) {
		float t = az / span_deg + 0.5;
		float m = mod(t, 2.0);
		float u = m < 1.0 ? m : 2.0 - m;
		float v = horizon_v - el / (span_deg / aspect);
		vec3 p = textureLod(backdrop, vec2(u, clamp(v, 0.003, 0.997)), 0.0).rgb;
		p = mix(p, top_color, smoothstep(0.03, -0.2, v));
		p = mix(p, ground_color, smoothstep(0.997, 1.15, v));
		p = mix(p, horizon_color, haze * (1.0 - smoothstep(0.0, 40.0, el)));
		c = mix(night, p, paint_mix);
	}

	vec3 md = normalize(moon_dir);
	float facing = dot(d, md);
	if (facing > 0.2) {
		vec3 right = normalize(cross(md, vec3(0.0, 1.0, 0.0)));
		vec3 up = cross(right, md);
		vec2 q = vec2(dot(d, right), dot(d, up)) / facing;
		vec2 muv = q / (2.0 * moon_half * moon_scale) + 0.5;
		muv.y = 1.0 - muv.y;
		if (muv.x > 0.0 && muv.x < 1.0 && muv.y > 0.0 && muv.y < 1.0) {
			vec4 mc = texture(moon_tex, muv);
			c = mix(c, mc.rgb, mc.a);
		}
	}
	COLOR = c * energy;
}
