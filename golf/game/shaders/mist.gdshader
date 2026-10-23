// A bank of low mist: a soft, wide card that turns about the vertical to face the camera, its edge
// broken up by two layers of drifting noise so it breathes. It thins out close to the camera (so
// flying through it never whites out the view) and far away (where the fog takes over).
// One MultiMesh holds every bank; INSTANCE_CUSTOM.x gives each its own phase.
shader_type spatial;
render_mode unshaded, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;   // its own colour, not the fog's

uniform sampler2D noise : repeat_enable, filter_linear;
uniform vec3 color : source_color = vec3(0.6, 0.55, 0.75);
uniform float alpha = 0.3;

varying float phase;
varying float cam_d;

void vertex() {
	vec3 center = MODEL_MATRIX[3].xyz;
	vec3 right = normalize(vec3(INV_VIEW_MATRIX[0].x, 0.0, INV_VIEW_MATRIX[0].z));
	float sx = length(MODEL_MATRIX[0].xyz);
	float sy = length(MODEL_MATRIX[1].xyz);
	vec3 wp = center + right * VERTEX.x * sx + vec3(0.0, VERTEX.y * sy, 0.0);
	phase = INSTANCE_CUSTOM.x;
	cam_d = length(CAMERA_POSITION_WORLD - wp);
	POSITION = PROJECTION_MATRIX * VIEW_MATRIX * vec4(wp, 1.0);
}

void fragment() {
	vec2 c = UV - vec2(0.5, 0.6);
	float body = smoothstep(0.5, 0.08, length(c * vec2(1.0, 1.7)));
	float n1 = texture(noise, UV * vec2(1.1, 0.6) + vec2(TIME * 0.011 + phase, TIME * 0.003)).r;
	float n2 = texture(noise, UV * vec2(0.55, 0.4) - vec2(TIME * 0.006, phase * 0.7)).r;
	float a = body * smoothstep(0.32, 0.78, n1 * 0.55 + n2 * 0.55);
	float fade = smoothstep(6.0, 32.0, cam_d) * (1.0 - smoothstep(320.0, 520.0, cam_d));
	ALBEDO = color;
	ALPHA = a * alpha * fade * (0.75 + 0.25 * sin(TIME * 0.27 + phase * 6.2831));
}
