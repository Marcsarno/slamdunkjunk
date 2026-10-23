// Will-o'-the-wisps: glowing motes that wander and flicker over the rough. Each is a camera-facing
// dot in one MultiMesh, moved entirely here (no per-frame work on the CPU). INSTANCE_CUSTOM.x is the
// wisp's phase, .y how fast it flickers. They stay a few pixels across however far away they are.
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform vec3 color : source_color = vec3(1.0, 0.6, 0.25);
uniform float energy = 4.0;

varying float flicker;

void vertex() {
	float ph = INSTANCE_CUSTOM.x * 6.2831;
	vec3 center = MODEL_MATRIX[3].xyz;
	center += vec3(sin(TIME * 0.37 + ph) * 1.8, sin(TIME * 0.9 + ph * 1.7) * 0.5, cos(TIME * 0.29 + ph * 0.8) * 1.8);
	float s = length(MODEL_MATRIX[0].xyz);
	s *= max(1.0, length(CAMERA_POSITION_WORLD - center) * 0.045);
	vec3 wp = center + (INV_VIEW_MATRIX[0].xyz * VERTEX.x + INV_VIEW_MATRIX[1].xyz * VERTEX.y) * s;
	flicker = 0.55 + 0.45 * sin(TIME * (1.8 + INSTANCE_CUSTOM.y * 3.5) + ph);
	POSITION = PROJECTION_MATRIX * VIEW_MATRIX * vec4(wp, 1.0);
}

void fragment() {
	float r = length(UV - 0.5) * 2.0;
	float core = smoothstep(0.32, 0.0, r);
	float halo = smoothstep(1.0, 0.0, r);
	ALBEDO = color * (core * energy + halo * halo * 0.5) * flicker;
}
