# Graveyard Shift: Midnight Golf: where things stand

Notes to pick the work up from (last updated 2026-10-23, evening). Code lives on the
`claude/hunting-game-pitch` branch of `Marcsarno/slamdunkjunk`, under `golf/`.

## Where it's played

- **Vercel (public):** https://midnight-golf-wheat.vercel.app (`#fps` on the end shows frame rate and 3D
  scale). Project `midnight-golf` (team `marcsarno`, id `prj_Kx6ClNpKm1RppDyK6dlbOPKP4No0`), root
  directory `golf/dist/web`, no build step. Its production branch is `main`, so pushes to this branch only
  make (protected) previews: **deploy production by hand**  (2026-10-23: automatic deploys on push are now turned off, see the rules below) after rebuilding `golf/dist/web` (Vercel MCP
  `create_deployment`, `gitSource` github Marcsarno/slamdunkjunk, ref `claude/hunting-game-pitch`, the
  commit sha, `target: production`).
- **Claude artifact (private preview):** https://claude.ai/artifact/TAgqet24mAUsE5tgyED6Qs, published from
  `golf/build/web_host/index.html` (+ its files). One publish caps at 64 MB: send the `hole_*.pck.wasm`
  packs in one publish and the `index.*` files in a second.
- The separate Vercel project `graveyard-shift-golf` and repo `Marcsarno/graveyard-shift-golf` are a
  different version from another chat: leave them alone. The old `slamdunkjunk` Vercel project fails on
  every push to this branch (it expects a Vite app); harmless.

## Build, test, ship

```
# a hole (headless Blender via the bpy module): layout JSON -> terrain, glb, props
python3 golf/tools/build_hole.py golf/courses/holes/h04_spiderwood.json golf/game/assets/holes/h04
python3 -I golf/tools/make_holes_4_9.py golf/courses/holes      # holes 4-9 layouts are written by this
# Godot
godot --headless --path golf/game --import
godot --headless --path golf/game -s res://tests/test_physics.gd           # must say ALL PASSED
godot --headless --path golf/game -s res://tests/probe_landing.gd          # bounce/roll per club
xvfb-run -a -s "-screen 0 720x1560x24" godot --path golf/game --rendering-driver opengl3 --resolution 720x1560 \
  -- --hole=h01 --capture-hole=<dir>      # bot plays the hole, screenshot per stage (--burst, --side-test, --drag-test)
#   --capture=<dir> --introonly | --intro-frames | --stills ;  --quality=0.75 fixes the 3D scale
# web: one script exports twice (textures for phones, ETC2, and for desktops, S3TC), packs holes 2-9
# and hosts it in golf/dist/web (Vercel: every push to this branch now deploys to production) and
# golf/build/web_host (serve it and open local.html to test)
bash golf/tools/build_web.sh
# local phone-sized touch test: serve golf/build on 8770, then the Playwright scripts in the scratchpad
```

Textures drawn in 3D (golfer, cards, sky, textures, balls, flags, props) import VRAM-compressed
(`compress/mode=2`, mipmaps on): they stay compressed in graphics memory (hole 1 went from ~226 MB to
~107 MB, `tests/mem_probe.gd --list`). The page fetches the game data in the format the device reads
(phones ETC2, other desktops S3TC; `web_pack.py`). Menu art (`assets/ui`) stays `compress/mode=1`
(lossy, 0.85) and the hole maps lossless. Run `--import` after changing an `.import` file.

## Standing rules from Marc

- Commit by name (never `git add -A` outside `golf/dist`), push this branch; commit `golf/dist/` only as
  a clean build from committed sources. Don't touch `fart/` or `Marcsarno/yola-zombie`. Run Blender
  headless only. Never enter passwords. Look at real frames before claiming something looks right.
- When told "just answer", answer only.
- **No preview builds, ever.** Pushes don't deploy (`golf/dist/web/vercel.json` and the repo root
  `vercel.json` turn git deployments off for this branch; `build_web.sh` rewrites the first). Production
  is deployed by hand, only when Marc asks; otherwise he plays the Claude artifact. Batch commits and
  push a few times a session.

## The game today

- Nine holes, par 36, Round autoload (`scripts/round.gd`). Hole 1 ships in the first download; holes 2-9
  are separate packs the `Holes` autoload fetches as the round reaches them (next one prefetched).
- Black night sky on every hole (`shaders/night_sky.gdshader`): painted star, cloud and moon layers; the
  moon is round in screen space. Painted backdrops are no longer used (left out of the export).
- Cast: the golfer alone (video-cut sprites: driver/iron swings, and putting from `tools/prep_video_putt.py`
  with a 40% backswing; fitted to their drawn size by `tools/shrink_golfer.py`), and Marc's hanging-pumpkin
  lantern (wooden post, braced arm) by every tee that the opening camera swings round (`hero_lantern.gd`,
  `assets/props/lanterns/arm.glb`). A pair of his post-top pumpkin lanterns stands behind every green
  (`hole_view._green_lanterns`). His lantern models (`art_src/lanterns`, ~16k tris each) are lightened to
  ~3k by `tools/prep_lanterns.py` (decimated shell and inside, joined into one object); the bridge-mount
  one is prepared (`lanterns/bridge.glb`) but not placed. (The skeleton caddie, cat and cart were
  removed: "failed experiment".)
- Courses: winding layouts, cart paths (a real, bouncy surface) with plank bridges at water, painted trees
  (04-18) and glowing light props (01-15) per hole theme. Graveyards use Marc's three headstones
  (`props.py` `headstone_rip`, `headstone_moon`, `headstone_broken`, ~130-250 tris each) with crosses and
  obelisks; the builder merges small props (stones, pumpkins) into one mesh per 40 m of ground.
- **All nine holes are rebuilt from Marc's concepts** (`art_src/concepts/`, `art_src/redesign/`), each with a
  safe and a risky route (layouts: `courses/holes/h01..h03`, h04-h09 written by `tools/make_holes_4_9.py`):
  1 pond (carry its corner to a pad), 2 purple pool and giant cauldron, 3 walled graveyard loop, 4 giant
  spider web inside an L, 5 fenced cornfield and Marc's barn and silo, 6 ghost-lit marsh, 7 hedge maze,
  blood-red pond, the vampire's house and gargoyles on the tee's gate pillars, 8 rocky ravine and the
  Headless Horseman statue, 9 fenced pumpkin patch.
  Layout keys beyond the fairway: `pads`, `zones` (open rough, no trees), `fences`, `hedges` (walls the ball
  bounces off), `webs` / `web_art` (ball stops dead, 40% short next shot), `cornfields` (corn, fence, hay;
  35% short), `features` (a painted prop by `image`, or a 3D landmark by `model` from `tools/landmarks.py`:
  barn, mansion, pillar; `face` turns its front to a point, `lift` raises a painted one), and
  `make_holes_4_9.ravine()` for a ravine (deep narrow water; theme `ravine` changes the message). The hole's
  ground grows to take in all of these. Lies cost power (`main.LIE`: rough 8%, deep 22%, bunker 15%).
  Check a layout in 2D first: `python3 -I tools/plan_check.py <layout.json> <out.png>` (webs, corn, hedges
  drawn). `tests/look_at.gd` (`--look-from=x,y,h --look-at=x,y,h --look-out=f.png`) takes a still of any spot.
  Landmarks still to make: the chapel (3) and the clubhouse (9).
- Clubs (`scripts/clubs.gd`): Driver 205 m, 3 Wood 185, 5/7/9 Iron 165/145/125, P/S/L Wedge 105/82/58,
  Chip 32 (skips and runs), Putter. Auto-picked: the shortest club whose full swing covers the shot
  with 10% in hand (`PICK_SHARE`), so most shots want 80-90% of a full pull. The club button steps down
  the bag. `tests/tune_clubs.gd` finds each club's launch speed for its carry.
- Aiming: close behind her (`AIM_BACK` 3.1 m, `AIM_HEIGHT` 1.65, ball 80% down the screen), with the
  map top left showing the target, margin and landing (off on the green). The target is auto-placed
  (lays up short of trouble); dragging the upper screen swings it across (`DRAG_TURN`) and longer or
  shorter (`DRAG_REACH`). Pull down from the lower screen: how far down is the power (21% of the screen
  height is the club's full power; the target is a mark part way, with a click); sliding sideways aims
  the other way, slingshot style (`SLING_SPAN` 40% of the width = `SLING_AIM_MAX` 18 degrees, putts 8,
  soft dead zone, eased). On release the camera sweeps round from behind her to her side
  (`_start_orbit`, `ORBIT_TIME`) and she swings. Putts: a full pull is 2x the putt; the default target
  is read for break (`_read_putt`).
- The ball she plays is Marc's design picked on the clubhouse turntable (`scripts/balls.gd`: pumpkin,
  ghost, skull, mummy, vampire, frank, bat; still + launch faces cut by `tools/prep_balls.py`): a
  billboard drawn bigger than life (`BALL_LOOK_GROUND`/`BALL_LOOK_AIR` of its camera distance), calm
  at address, scared as the pull grows and in flight, where the chase camera follows close
  (`CHASE_*`) and thin wind streaks slide past its face (`_update_wind`).
- Pin flags: Marc's four painted flags (`assets/flags`, cut by `tools/prep_flags.py`), one per hole
  (`hole_view.FLAGS`).
- Putting: a grid over the green whose beads run downhill (white to ~2.5%, yellow, red past ~4.5%) and a
  straight aim line as long as the putt (`scripts/putt_grid.gd`), as PGA 2K / EA PGA show it. The cup
  judges a putt once as it comes over the rim: slow enough for its line drops, else it hops the hole
  and rolls on a little slower (`ball_sim._check_cup`).
- Greens (`shaders/terrain.gdshader`, uniforms set in `hole_view._terrain_material`): fine grass tiled in
  up close, mowing stripes across the way in (a checker on `hole_view.CHECKER_GREENS`) that swap light
  and dark with the view, a darker collar, a soft dew gloss and a few glints, a worn ring round the cup;
  the cup has a white liner rim.
- The opening (`main._intro_cam`): two framed shots, the hole's own centrepiece (`main.CINEMA`, per hole:
  the camera glides from `from` to `to` looking at `look`, heights above the ground) and a low push in on
  the flag from the approach, with a dip to black between, then a curve up over the hole, round behind
  her and down into the aim view. Tap skips. `tests/capture.gd --intro-frames` snaps it and the hand-over.
- Rolls die away gently: the turf's drag eases to 30% at a crawl (`ball_sim.ROLL_TAIL`). No slow motion
  near the cup (Marc took it out); flight plays at 1.25x, easing to real time on landing (`main._time_scale`).
- The clubhouse board (`scripts/front.gd`) is pages: main (Play Now = the round from hole 1, Pick a Hole,
  Pick your Ball, Options, How to Play) and one for each. Changing page, a felt eraser sweeps the board
  (each line wiped as it passes, a cloud of dust left that settles) and the new page is chalked on line by
  line (the chalk shader's `write_x` / `erase_x`, in each item's own units), with chalk and eraser sounds
  (`make_sfx.py`). Options: Music, Sounds (`Sfx.on`), Vibration (`Sfx.buzz`), Graphics auto / sharp /
  smooth (`Quality.set_mode`), all remembered in `user://settings.cfg`.
- Chalkboard fonts: Fredericka the Great (headings) and Caveat Brush (writing), `scripts/chalk.gd`.
  `--ball-size=0.13` tries sizes (default 0.15 of the screen width).
- Landings: turf bounce by descent angle and spin (drive skips and runs ~9%, iron rolls a few metres,
  wedge stops; tuned in `scripts/ball_sim.gd` SURF table).
- Performance: `Quality` autoload draws 3D at 75% on the web (HUD sharp), adapts 85/75/65/55% to the
  frame rate (never during the opening flyover; the step a phone settles on is remembered); shadows 40 m
  on a 1024 map; shot preview recomputed 10x a second while pulling. Before each hole `main._prewarm()`
  draws everything once behind a title card (the whole hole from above, the lantern, the aiming view,
  every landing effect underground, a trail, a rehearsed first shot: pull, side view, swing frames, the
  putting grid) and loads every sound and loads all her frames, so no shader compiles and no
  texture loads mid-flyover or mid-swing. Props under 2.5 m aren't drawn past 90 m (`hole_view.gd`).

## What's next (in Marc's order of interest)

1. **Performance**: Marc says the lantern cut "really, really helped"; the flyover was the last choppy
   spot (now drawn at 60% with no shadows). Left if needed: VRAM-compressed textures (check download
   size), bake the three star strips into one, thinner mist up close, cheaper shadows on phones.
2. **Feel tuning after Marc plays:** pull travel, putt headroom (2x), driver run-out, wedge bite.
3. **The rest of Marc's revised holes** (concept sheets in `art_src/concepts/`; 3, 6, 9 done): 2 and 1
   next, then 4, 5, 8, then 7, as above. Landmarks from the concepts still to make: the clubhouse behind
   9's green, the chapel on 3, the barn on 5, the mansion on 7, the Horseman statue and bridge on 8.
   (The older plan page https://claude.ai/artifact/N3nVG9bieHCtFRGLxT2xFT, source `golf/docs/plan/`, is
   superseded by Marc's concepts.)
4. Fun extras from the plan: tombstone kicks, ball rattling over bridges, drifting wisps, the Horseman,
   homecoming lanterns.
5. Voice (Kokoro TTS for the caddie's call-outs) is **skipped for now**; needs `huggingface.co` allowed in
   the environment's network settings if it comes back.
6. On hold: the 3D swing, waiting for Marc's Unity-rigged character.
