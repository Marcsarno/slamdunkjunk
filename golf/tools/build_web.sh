#!/usr/bin/env bash
# The web build, start to finish: export (textures in the phone format), export again for desktops
# (only its game data is kept), pack holes 2-9 and the later songs (each with its own art, in both
# texture formats), then host it in golf/dist/web (Vercel) and
# golf/build/web_host (local testing: serve it and open local.html).
#   bash golf/tools/build_web.sh
set -euo pipefail
cd "$(dirname "$0")/.."
G=game
PRESET=$G/export_presets.cfg
rm -rf build/web build/web_desktop && mkdir -p build/web build/web_desktop
set_formats() {   # desktop mobile
	sed -i "s/^vram_texture_compression\/for_desktop=.*/vram_texture_compression\/for_desktop=$1/; s/^vram_texture_compression\/for_mobile=.*/vram_texture_compression\/for_mobile=$2/" $PRESET
}
# the first download is what the clubhouse and hole 1 need: the art each hole opens (tools/hole_art.json,
# remade when a hole's files are newer) decides what's left out of it and carried by each later hole's
# pack instead (tools/web_split.py); the preset gets those left out for these exports only
if [ -n "$(find $G/assets/holes -newer tools/hole_art.json -name '*.json' -print -quit)" ]; then
	bash tools/hole_art.sh
fi
python3 -I tools/ground_import.py
python3 -I tools/web_split.py build/split.json
cp $PRESET build/export_presets.cfg.orig
trap 'cp build/export_presets.cfg.orig $PRESET' EXIT
LEAVE=$(python3 -I -c "import json; print(', '.join(json.load(open('build/split.json'))['exclude']))")
sed -i "s|^exclude_filter=\"\(.*\)\"|exclude_filter=\"\1, $LEAVE\"|" $PRESET
set_formats true false
(cd $G && godot --headless --export-release "Web" ../build/web_desktop/index.html 2>&1 | grep -E "^(ERROR|SCRIPT)" | grep -v leaked || true)
set_formats false true
(cd $G && godot --headless --export-release "Web" ../build/web/index.html 2>&1 | grep -E "^(ERROR|SCRIPT)" | grep -v leaked || true)
for fmt in etc2 s3tc; do
	(cd $G && godot --headless -s res://tools/pack_holes.gd -- --out=../build/web --format=$fmt --split=../build/split.json \
		core course h01 h02 h03 h04 h05 h06 h07 h08 h09 music)
done
python3 -I tools/web_pack.py build/web build/web_host build/web_desktop | tail -1
python3 -I tools/web_pack.py build/web dist/web build/web_desktop > /dev/null
rm -f dist/web/local.html
# pushes never deploy on their own (each would use one of Vercel's daily deployments): production is
# deployed by hand when Marc asks
printf '{\n  "git": {\n    "deploymentEnabled": false\n  }\n}\n' > dist/web/vercel.json
du -sh dist/web
