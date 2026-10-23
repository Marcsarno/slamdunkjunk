# Graveyard Shift: Midnight Golf: where things stand

Notes to pick the work up from (last updated 2026-10-23). Code lives on the
`claude/hunting-game-pitch` branch of `Marcsarno/slamdunkjunk`, under `golf/`.

## Where it's played

- **Vercel (public):** https://midnight-golf-wheat.vercel.app (`#fps` on the end shows frame rate and 3D
  scale). Project `midnight-golf` (team `marcsarno`, id `prj_Kx6ClNpKm1RppDyK6dlbOPKP4No0`), root
  directory `golf/dist/web`, no build step. Its production branch is `main`, so pushes to this branch only
  make (protected) previews: **deploy production by hand** after rebuilding `golf/dist/web` (Vercel MCP
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
# web
mkdir -p golf/build/web && godot --headless --path golf/game --export-release "Web" ../build/web/index.html
godot --headless --path golf/game -s res://tools/pack_holes.gd -- --out=../build/web h02 h03 h04 h05 h06 h07 h08 h09
python3 -I golf/tools/web_pack.py golf/build/web golf/build/web_host          # the artifact / local test
python3 -I golf/tools/web_pack.py golf/build/web golf/dist/web && rm golf/dist/web/local.html   # Vercel
# local phone-sized touch test: serve golf/build on 8770, then the Playwright scripts in the scratchpad
```

New PNGs import as lossless: set `compress/mode=1` and `lossy_quality=0.85` in their `.import` files (the
project's convention), then `--import` again.

## Standing rules from Marc

- Commit by name (never `git add -A` outside `golf/dist`), push this branch; commit `golf/dist/` only as
  a clean build from committed sources. Don't touch `fart/` or `Marcsarno/yola-zombie`. Run Blender
  headless only. Never enter passwords. Look at real frames before claiming something looks right.
- When told "just answer", answer only.

## The game today

- Nine holes, par 36, Round autoload (`scripts/round.gd`). Hole 1 ships in the first download; holes 2-9
  are separate packs the `Holes` autoload fetches as the round reaches them (next one prefetched).
- Black night sky on every hole (`shaders/night_sky.gdshader`): painted star, cloud and moon layers; the
  moon is round in screen space. Painted backdrops are no longer used (left out of the export).
- Cast: the golfer (video-cut sprites: driver/iron swings, and putting from `tools/prep_video_putt.py` with
  a 40% backswing), the skeleton caddie, the cat and the golf cart (8 views) beside her; a modelled
  jack-o'-lantern by every tee that the opening camera swings round.
- Courses: winding layouts, cart paths (a real, bouncy surface) with plank bridges at water, painted trees
  (04-18) and glowing light props (01-15) per hole theme.
- Aiming: target auto-placed (lays up short of trouble), drag to move it. **Slingshot:** a Halloween ball
  button (`hud.gd` `Sling`, an on-screen control, not the golf ball) rests low in the middle; pull it
  back. The band's length is the power (a full stretch, 21% of the screen height, is the club's full
  power; the target is a mark part way, with a click), its tilt aims the other way (down-right sends it
  left, `SLING_AIM` 0.35 of the tilt past a 4 degree dead zone). Its face goes still -> launch -> panic
  (past 90%). The view stays up on the course while pulling (no zoom down; the corner map is off,
  `AIM_MAP`), cuts to her swing on release. Putts: a full pull is 2x the putt. Past 90% power the
  margin of error widens. Marc's seven balls (pumpkin, ghost, skull, mummy, vampire, frank, bat; still +
  launch faces; no panic face yet, it falls back to launch) are cut from `art_src/balls/balls_sheet*.png`
  by `tools/prep_balls.py` (usage in its docstring) into `assets/balls/<name>/<pose>.png`; picked on a
  turntable on the clubhouse bar (`front.gd`, names in `Sling.NAMES`, remembered in `user://settings.cfg`).
  Putts: the default target is read for break (`_read_putt`: a foot past, moved across the slope until
  the roll runs over the cup). The caddie, cat and cart appear on the tee only.
- Chalkboard fonts: Fredericka the Great (headings) and Caveat Brush (writing), `scripts/chalk.gd`.
  `--ball-size=0.13` tries sizes (default 0.15 of the screen width).
- Landings: turf bounce by descent angle and spin (drive skips and runs ~9%, iron rolls a few metres,
  wedge stops; tuned in `scripts/ball_sim.gd` SURF table).
- Performance: `Quality` autoload draws 3D at 75% on the web (HUD sharp), adapts 85/75/65/55% to the
  frame rate; shadows 40 m on a 1024 map; shot preview recomputed 10x a second while pulling.

## What's next (in Marc's order of interest)

1. **Marc's phone numbers** from `#fps` (tee, pulling, flight; phone model). Then, if needed, the rest of
   the performance list: hide small props/ground cover past ~60-80 m and coarser far terrain (do it in
   `build_hole.py`, automatic per rebuild), VRAM-compressed textures (cuts ~170 MB of GPU memory; make it
   the import default; check download size), bake the three star strips into one, thinner mist up close.
2. **Feel tuning after Marc plays:** pull travel, putt headroom (2x), driver run-out, wedge bite.
3. **The course plan** https://claude.ai/artifact/N3nVG9bieHCtFRGLxT2xFT (source in `golf/docs/plan/`:
   `proposal.py` holds the nine build-ready specs, `python3 -I build_page.py` redraws the page): keep holes 1-2; redesign 3 (split fairway), 4 (drivable par 4 ~280 yd), 5 (cape
   par 4), 6 (135-yd wedge, peninsula), 7 (hedge maze + moat), 8 (ridge high/low road), 9 (par 5 reachable
   in two). Waiting on Marc's go-ahead. Landmarks to model in Blender: windmill, castle drawbridge,
   covered bridge, village square; spider webs and hedge blocks best as painted art from Marc.
4. Fun extras from the plan: tombstone kicks, ball rattling over bridges, drifting wisps, the Horseman,
   homecoming lanterns.
5. Voice (Kokoro TTS for the caddie's call-outs) is **skipped for now**; needs `huggingface.co` allowed in
   the environment's network settings if it comes back.
6. On hold: the 3D swing, waiting for Marc's Unity-rigged character.
