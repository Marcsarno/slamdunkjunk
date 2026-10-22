// Sky from a painted 3:1 panorama strip. The strip is repeated `repeats` times around the
// horizon so its pixels stay square (a round moon stays round); with 2 repeats the two moons
// are 180 degrees apart and never on screen together. Above the strip fades to its top color,
// below the horizon to the ground color.
shader_type sky;

uniform sampler2D sky_tex : source_color, filter_linear, repeat_enable;
uniform float repeats = 2.0;
uniform float yaw = 0.0;            // texture u that faces world -Z (down the hole)
uniform float horizon_v = 0.85;     // texture v that sits on the horizon
uniform float deg_span = 60.0;      // degrees of elevation covered by the full strip height
uniform vec3 top_color : source_color = vec3(0.2, 0.1, 0.3);
uniform vec3 ground_color : source_color = vec3(0.08, 0.05, 0.1);
uniform float energy = 1.0;

void sky() {
	vec3 d = normalize(EYEDIR);
	float az = atan(d.x, -d.z) / (2.0 * PI);
	float el = degrees(asin(clamp(d.y, -1.0, 1.0)));
	float u = fract(az * repeats + yaw);
	float v = horizon_v - el / deg_span;
	vec3 c = texture(sky_tex, vec2(u, clamp(v, 0.002, 0.998))).rgb;
	c = mix(c, top_color, smoothstep(0.04, -0.12, v));
	c = mix(c, ground_color, smoothstep(0.0, -6.0, el));
	COLOR = c * energy;
}
