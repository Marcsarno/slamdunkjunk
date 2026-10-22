// Sky + distant scenery from one painted backdrop (moon painted out by prep_backdrops.py).
// The painting covers `span_deg` of the horizon centered on `yaw_deg`; beyond that it is
// mirrored back and forth so the edges always meet seamlessly. The moon is a separate sprite
// drawn once, in the direction the moonlight comes from.
shader_type sky;

uniform sampler2D backdrop : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D moon_tex : source_color, filter_linear, repeat_disable;
uniform float span_deg = 90.0;
uniform float aspect = 1.5;           // painting width / height
uniform float horizon_v = 0.8;        // painting v that sits on the horizon
uniform float yaw_deg = 0.0;          // world bearing of the painting's center (0 = -Z)
uniform vec3 moon_dir = vec3(0.0, 0.6, -0.8);
uniform float moon_half = 0.08;       // half-size of the moon sprite in tangent units
uniform vec3 top_color : source_color = vec3(0.12, 0.08, 0.25);
uniform vec3 ground_color : source_color = vec3(0.35, 0.3, 0.45);
uniform float energy = 1.0;

void sky() {
	vec3 d = normalize(EYEDIR);
	float az = degrees(atan(d.x, -d.z)) - yaw_deg;
	float el = degrees(asin(clamp(d.y, -1.0, 1.0)));
	float t = az / span_deg + 0.5;
	float m = mod(t, 2.0);
	float u = m < 1.0 ? m : 2.0 - m;
	float v = horizon_v - el / (span_deg / aspect);
	vec3 c = textureLod(backdrop, vec2(u, clamp(v, 0.003, 0.997)), 0.0).rgb;
	c = mix(c, top_color, smoothstep(0.03, -0.2, v));
	c = mix(c, ground_color, smoothstep(0.997, 1.15, v));

	vec3 md = normalize(moon_dir);
	float facing = dot(d, md);
	if (facing > 0.2) {
		vec3 right = normalize(cross(md, vec3(0.0, 1.0, 0.0)));
		vec3 up = cross(right, md);
		vec2 p = vec2(dot(d, right), dot(d, up)) / facing;
		vec2 muv = p / (2.0 * moon_half) + 0.5;
		muv.y = 1.0 - muv.y;
		if (muv.x > 0.0 && muv.x < 1.0 && muv.y > 0.0 && muv.y < 1.0) {
			vec4 mc = texture(moon_tex, muv);
			c = mix(c, mc.rgb, mc.a);
		}
	}
	COLOR = c * energy;
}
