shader_type canvas_item;
// Chalk on a blackboard. A stroke's coverage is broken up by a fine grain (where the chalk skipped the
// board's surface), in screen space so every letter carries the same texture; lightly, so the letters
// stay whole and easy to read.
// dust > 0 instead draws a faint smudge of old, wiped chalk (for a ColorRect over the board).
// write_x / erase_x (in the item's own units, along its x) animate it: a line is written up to write_x, left to right, its
// edge a little ragged like a stick of chalk; the eraser has wiped everything left of erase_x.

uniform sampler2D grain : repeat_enable, filter_linear;
uniform float grain_px = 2.5;      // grain size on screen, in pixels
uniform float strength = 0.55;     // 0 = clean strokes, 1 = full chalk
uniform float dust = 0.0;          // > 0: draw a wiped-chalk smudge at this opacity
uniform float write_x = 100000.0;
uniform float erase_x = -100000.0;
varying float lx;

void vertex() {
	lx = VERTEX.x;
}

void fragment() {
	vec2 p = FRAGCOORD.xy / grain_px;
	float fine = texture(grain, p / 256.0).r;
	if (dust > 0.0) {
		float cloud = texture(grain, FRAGCOORD.xy / 1400.0 + 0.11).r;
		float sweep = texture(grain, vec2(FRAGCOORD.x / 2200.0, FRAGCOORD.y / 500.0) + 0.53).r;
		float a = smoothstep(0.45, 0.8, cloud * 0.6 + sweep * 0.55) * (0.6 + 0.4 * fine);
		COLOR = vec4(COLOR.rgb, COLOR.a * a * dust);
	} else {
		float keep = smoothstep(0.2, 0.55, fine);
		COLOR.a *= mix(1.0, keep, strength);
		COLOR.rgb *= mix(1.0, 0.9 + 0.1 * keep, strength);
		float rag = texture(grain, FRAGCOORD.xy / 90.0).r * 18.0;
		COLOR.a *= 1.0 - smoothstep(write_x - 10.0, write_x, lx - rag);
		COLOR.a *= smoothstep(erase_x - 30.0, erase_x, lx + rag * 1.5);
	}
}
