// Soft dark corners and a touch of purple at the edges, like the Blender render.
shader_type canvas_item;

uniform float strength = 0.55;
uniform vec3 tint : source_color = vec3(0.06, 0.02, 0.1);

void fragment() {
	vec2 p = UV - 0.5;
	p.x *= 0.82;
	float v = smoothstep(0.32, 0.78, length(p));
	COLOR = vec4(tint, v * strength);
}
