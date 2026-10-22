shader_type canvas_item;
// Chalk on a blackboard. A stroke's coverage is broken up by a fine grain (where the chalk skipped the
// board's surface) and a coarser streak, both in screen space so every letter carries the same texture.
// dust > 0 instead draws a faint smudge of old, wiped chalk (for a ColorRect over the board).

uniform sampler2D grain : repeat_enable, filter_linear;
uniform float grain_px = 2.5;      // grain size on screen, in pixels
uniform float strength = 1.0;      // 0 = clean strokes, 1 = full chalk
uniform float dust = 0.0;          // > 0: draw a wiped-chalk smudge at this opacity

void fragment() {
	vec2 p = FRAGCOORD.xy / grain_px;
	float fine = texture(grain, p / 256.0).r;
	float streak = texture(grain, vec2(p.x / 900.0, p.y / 2600.0) + 0.37).r;
	if (dust > 0.0) {
		float cloud = texture(grain, FRAGCOORD.xy / 1400.0 + 0.11).r;
		float sweep = texture(grain, vec2(FRAGCOORD.x / 2200.0, FRAGCOORD.y / 500.0) + 0.53).r;
		float a = smoothstep(0.45, 0.8, cloud * 0.6 + sweep * 0.55) * (0.6 + 0.4 * fine);
		COLOR = vec4(COLOR.rgb, COLOR.a * a * dust);
	} else {
		float keep = smoothstep(0.16, 0.56, fine * 0.85 + streak * 0.22);
		COLOR.a *= mix(1.0, keep, strength);
		COLOR.rgb *= mix(1.0, 0.9 + 0.1 * keep, strength);
	}
}
