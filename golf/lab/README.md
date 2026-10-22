# Swing Lab

One page for building and checking Brittany's golf swing: her rig beside the reference rig playing the
same clip, the club held from her lead hand, and the numbers that matter, worst frame first.

Open it: `python3 -m http.server 8765` in this folder, then http://127.0.0.1:8765/ (three.js loads from
cdn.jsdelivr.net). The published copy is a claude.ai artifact.

## What it does
- **Retarget, live:** each of her bones takes the reference bone's world-space change from its rest
  pose (BVH frame 0 is the added T-pose; FBX uses the bind pose), after lining the two rigs up on their
  limb lines at rest (hips and chest also on their side lines). Hip travel is scaled by leg length.
- **CMU wrists:** in the CMU conversion `<Side>Hand` is only forearm twist and `<Side>FingerBase` is the
  palm, so her ForeArm takes `<Side>Hand` and her Hand takes `<Side>FingerBase`. Torso, collarbones,
  head and feet take the reference's change on her own rest (copying CMU's lines shrugged her shoulders).
- **Posture:** her arms are shorter and her torso longer than the mocap golfer's, so she bends more at
  the hips (pelvis, spine and collarbones tip about her hip joints; arms keep their hang), with shoulders
  rolled forward a little and arms swung forward; full to impact, easing to a share by the finish.
- **Grip, club first:** the club is placed as golf and the face-on video have it at address (sole flat at
  the club's lie, face square, hands 4 cm ahead; the club gets longer if she can't reach the ball), and its
  shaft is turned to the video's at the top (level, at the target), impact (back on the ball) and finish
  (down her back). Both hands hold it in a fixed grip (handle diagonal across the fingers, thumbs down the
  shaft, back of the lead hand and the trail palm to the target). The lead hand's correction is keyed at
  those four frames and eased between, so it still moves with the mocap between them.
- **The arm adapts:** the lead wrist is held at the video's angle for the phase, its forearm points where
  that wrist puts it, and the elbow (a hinge, forearm roll within 75 deg) is found so the hand lands nearest
  the mocap's. The trail hand is pinned on the grip; its elbow swing is searched for a natural trail wrist.
  If the trail arm can't reach, the hands move toward the trail shoulder (96% reach at most). Twist lives
  in the forearms, never the wrists.
- **Club at the ten positions:** the lead hand's correction is keyed at all ten and eased between them:
  square at address and impact, level and along the target line at P2 / P6 (head away) and P8 (at the
  target), level at the target at the top, up on the club's plane at P3 / P5 / P9 leaning as the video
  shows, down her back at the finish.
- **Hands placed together** (switch, off by default; the solve takes ~20 s): the club's grip may move off
  the mocap's hand path so both arms hold it with natural wrists, clear of her body and each other.
  Fewer arm-against-arm frames and no hand pops, but the lead wrist leaves its range more often; her trail
  arm still meets her chest in about a third of the frames either way (the mocap's hand path is not hers).
- **Collision:** her torso, chest, pelvis and thigh skin (skinned on the CPU each frame) against arm and
  hand capsules sized from her own arm vertices along their length; arm against arm. Red points mark skin
  inside an arm.
- **Video reference:** your swing videos, only to check her 3D animation against (never game art). Each
  club has its video in `assets/video/<club>/` exactly as you made it (`ref.mp4`, plus a VP9 `ref.webm`
  for browsers without H.264) and a few numbers (`video.json`: keys, where her feet are, her height at
  address). No frames are exported. The lab seeks the video to the frame matching the clip (synced at the
  ten swing positions: address, P2 club level back, P3 lead arm level, top, P5 lead arm level down, P6 club
  level down, impact, P8 club level through, P9 hands up level with the shoulders, finish; read off the
  video by eye one frame at a time, and found on her own arms in the clip by the same angles) and shows
  the view that matches the camera: face-on, or from behind her
  where the video shows both sides. Beside her, or traced over her (the outline is drawn on the fly from
  the video's plain background).
- **Views:** face-on, from behind, down the line, from the target, above, four close upper-body views, and four hand
  close-ups (support side, below, above, 3/4);
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
- `tools/shoot.mjs` (Playwright): screenshots and key-frame / hand / video sheets through `window.lab`.
- `tools/video_ref.py`: adds a swing video as a club's reference (copies the video, measures the keys and
  her feet; see its header for the commands used).
