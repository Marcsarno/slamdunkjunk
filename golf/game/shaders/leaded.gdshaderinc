// Leaded glass: a diamond lattice of lead across a window (the chapel's lancets), in the model's own
// metres on the window's plane. Returns how much light comes through: 1 on the glass, dim on the lead.
float leaded(vec3 p, vec3 n) {
	float u = abs(n.x) > abs(n.z) ? p.z : p.x;
	float a = fract((u + p.y) * 2.4);
	float b = fract((u - p.y) * 2.4);
	float lead = max(1.0 - smoothstep(0.0, 0.06, min(a, 1.0 - a)), 1.0 - smoothstep(0.0, 0.06, min(b, 1.0 - b)));
	return mix(1.0, 0.28, lead);
}
