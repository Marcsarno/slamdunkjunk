// The chapel's and the house's surfaces, drawn on the phone instead of shipped as pictures: the
// vertex colour's alpha says what a face is made of (tools/landmarks.py SURFACE) and this draws it,
// in the model's own metres so the pattern holds still: stone blocks with mortar, slates in staggered
// courses, overlapping clapboards, brick, wood planks. The grain comes from the stone and wood textures
// every hole already loads. Each block, slate or board gets its own shade, and the walls darken toward
// the ground.
shader_type spatial;
render_mode cull_back;

uniform sampler2D tex_stone : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D tex_wood : source_color, filter_linear_mipmap, repeat_enable;
uniform float boost = 1.6;

varying vec3 v_pos;
varying vec3 v_nrm;

void vertex() {
	v_pos = VERTEX;
	v_nrm = NORMAL;
}

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

// how far from a cell's edge (metres), for mortar lines and shadow lines
float edge(float f, float size) {
	return min(f, 1.0 - f) * size;
}

void fragment() {
	vec3 n = normalize(v_nrm);
	// the face's own coordinates: along it (u) and up it (v); on a near-flat top, plan coordinates
	float u;
	float v = v_pos.y;
	if (abs(n.y) > 0.85) {
		u = v_pos.x;
		v = v_pos.z;
	} else {
		vec2 t = normalize(vec2(-n.z, n.x));
		u = dot(v_pos.xz, t);
	}
	float k = COLOR.a;
	vec3 base = COLOR.rgb;
	float shade = 1.0;
	float grain = 1.0;
	if (k > 0.85) {                                   // stone: blocks in courses, mortar between
		float rh = 0.5, bl = 1.05;
		float r = floor(v / rh);
		float off = (mod(r, 2.0) * 0.5 + hash(vec2(r, 3.1)) * 0.25) * bl;
		float c = floor((u + off) / bl);
		float fu = fract((u + off) / bl), fv = fract(v / rh);
		float m = min(edge(fu, bl), edge(fv, rh));
		shade = 0.86 + 0.24 * hash(vec2(c, r));
		shade *= mix(0.66, 1.0, smoothstep(0.02, 0.05, m));                    // mortar
		shade *= 1.0 + 0.08 * smoothstep(0.75, 0.95, fv) - 0.1 * (1.0 - smoothstep(0.05, 0.2, fv));
		grain = mix(1.0, dot(texture(tex_stone, vec2(u, v) * 0.3).rgb, vec3(0.333)) * 2.2, 0.6);
		shade *= mix(0.7, 1.0, smoothstep(0.0, 1.6, v_pos.y));                  // damp near the ground
	} else if (k > 0.75) {                            // slate: staggered courses, a dark line under each
		float rh = 0.3, tw = 0.36;
		float r = floor(v / rh);
		float off = mod(r, 2.0) * 0.5 * tw;
		float c = floor((u + off) / tw);
		float fu = fract((u + off) / tw), fv = fract(v / rh);
		shade = 0.78 + 0.34 * hash(vec2(c, r + 7.0));
		shade *= mix(0.58, 1.0, smoothstep(0.0, 0.16, fv));
		shade *= mix(0.6, 1.0, smoothstep(0.012, 0.03, edge(fu, tw)));
		grain = mix(1.0, dot(texture(tex_stone, vec2(u, v) * 0.6).rgb, vec3(0.333)) * 2.2, 0.35);
	} else if (k > 0.65) {                            // clapboard: each board's lower edge overlaps the next
		float bh = 0.22;
		float r = floor(v / bh);
		float fv = fract(v / bh);
		shade = 0.92 + 0.12 * hash(vec2(r, 1.7));
		shade *= mix(0.62, 1.0, smoothstep(0.0, 0.18, fv)) * (0.94 + 0.08 * fv);
		grain = mix(1.0, dot(texture(tex_wood, vec2(v * 0.4, u * 0.15)).rgb, vec3(0.333)) * 3.0, 0.15);
		shade *= mix(0.82, 1.0, smoothstep(0.0, 1.0, v_pos.y));
	} else if (k > 0.55) {                            // brick: running bond
		float rh = 0.085, bl = 0.24;
		float r = floor(v / rh);
		float off = mod(r, 2.0) * 0.5 * bl;
		float c = floor((u + off) / bl);
		float fu = fract((u + off) / bl), fv = fract(v / rh);
		shade = 0.78 + 0.34 * hash(vec2(c, r + 11.0));
		shade *= mix(0.62, 1.0, smoothstep(0.008, 0.016, min(edge(fu, bl), edge(fv, rh))));
	} else if (k > 0.45) {                            // wood planks
		grain = dot(texture(tex_wood, vec2(u, v) * 0.5).rgb, vec3(0.333)) * 3.0;
	}
	ALBEDO = base * boost * shade * grain;
	ROUGHNESS = k > 0.75 && k < 0.85 ? 0.7 : 0.92;
}
