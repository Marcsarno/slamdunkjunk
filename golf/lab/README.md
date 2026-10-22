# Swing Lab

One page for building and checking Brittany's golf swing: her rig beside the reference rig playing the
same clip, the club held from her lead hand, and the numbers that matter, worst frame first.

Open it: `python3 -m http.server 8765` in this folder, then http://127.0.0.1:8765/ (three.js loads from
cdn.jsdelivr.net). The published copy is a claude.ai artifact.

## What it does
- **Retarget, live:** each of her bones takes the reference bone's world-space change from its rest
  pose (BVH frame 0 is the added T-pose; FBX uses the bind pose), after lining the two rigs up on their
  limb lines at rest (hips and chest also on their side lines). Hip travel is scaled by leg length.
- **Club:** the lead fist holds the grip end. Fist centre = circle through the curled middle-finger
  joints. The club's line comes from the reference's two hands (default) or from her own two fists.
  The face turns with the back of the lead hand.
- **Trail hand:** onto its spot on the club (below the lead fist by the reference's hand spacing,
  scaled by arm length), two-bone arm in the source's elbow plane, the hand keeps its retargeted turn.
- **Views:** face-on, down the line, above, and four hand close-ups (support side, below, above, 3/4);
  the reference camera mirrors hers relative to each golfer. Close-ups clip anything nearer than 16 cm.
- **Numbers:** trail fist to its grip spot in the club frame (along / face / toe), grip axis vs shaft,
  wrists in the forearm's frame against human limits, arm straightness and reach, clubhead height,
  foot slide (address to impact); a whole-clip scan lists the worst frames.

## Clips
`assets/clips.json`. Now: CMU subject 64 (real mocap, see assets/mocap/README.md), a stand-in until the
Mixamo golf clips arrive: put X Bot FBX files in `assets/mixamo/` and add entries with `"kind": "fbx"`
(FBX loading is written but untested).

## Tools
- `tools/slim_character.py` (Blender, headless): the lab's copy of the character, skin and skeleton only,
  lighter textures. `assets/brittany.glb.b64.txt` is the same file as base64 for hosts that don't serve
  .glb (`base64 -w0 assets/brittany.glb > assets/brittany.glb.b64.txt`).
- `tools/shoot.mjs` (Playwright): screenshots and key-frame / hand sheets through `window.lab`.
