// Night pond: dark water that picks up the sky toward the horizon (fresnel), with slow ripples
// catching the moon. Cheap enough for phones: no screen reads.
shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx;

uniform vec3 deep_color : source_color = vec3(0.05, 0.06, 0.13);
uniform vec3 sky_color : source_color = vec3(0.45, 0.35, 0.6);
// > 0: a brew glowing up from below in slow drifting patches (a witch's swamp); black = plain pond
uniform vec3 glow : source_color = vec3(0.0);

void fragment() {
	vec3 wp = (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float t = TIME * 0.4;
	vec2 rip = vec2(sin(wp.x * 0.9 + t) + sin(wp.z * 1.3 - t * 1.3), cos(wp.z * 0.8 + t * 0.7) + sin(wp.x * 1.7 + t));
	NORMAL = normalize(NORMAL + (VIEW_MATRIX * vec4(rip.x * 0.04, 0.0, rip.y * 0.04, 0.0)).xyz);
	float fres = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);
	ALBEDO = deep_color;
	EMISSION = mix(deep_color * 0.2, sky_color * 0.3, fres);
	float t2 = TIME * 0.15;
	float patch = sin(wp.x * 0.21 + t2) * sin(wp.z * 0.17 - t2 * 1.3) + 0.6 * sin((wp.x + wp.z) * 0.33 + t2 * 2.1);
	EMISSION += glow * (0.35 + 0.65 * smoothstep(-0.2, 1.2, patch)) * (1.0 - fres * 0.7);
	ROUGHNESS = 0.45;
	METALLIC = 0.0;
	SPECULAR = 0.1;
}
