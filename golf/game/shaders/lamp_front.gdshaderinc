// The opening's light front (HoleView.light_front): lights up to front_d metres down the hole from
// front_from are on, catching over `ramp` metres with a candle's flicker; past it they're dark.
uniform vec3 front_from;
uniform vec3 front_dir;
uniform float front_d = 1.0e6;
uniform float ramp = 10.0;
varying vec3 v_world;

void vertex() {
	v_world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

float lamp_on(vec3 w, float t) {
	float on = clamp((front_d - dot(w - front_from, front_dir)) / ramp, 0.0, 1.0);
	if (on > 0.0 && on < 1.0) {
		vec3 c = floor(w);
		on *= 0.7 + 0.3 * sin(t * 31.0 + c.x * 1.7 + c.z * 2.3);
	}
	return on;
}
