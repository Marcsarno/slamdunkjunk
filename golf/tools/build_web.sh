#!/usr/bin/env bash
# The web build, start to finish: export (textures in the phone format), export again for desktops
# (only its game data is kept), pack holes 2-9, then host it in golf/dist/web (Vercel) and
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
trap 'set_formats false true' EXIT
set_formats true false
(cd $G && godot --headless --export-release "Web" ../build/web_desktop/index.html 2>&1 | grep -E "^(ERROR|SCRIPT)" | grep -v leaked || true)
set_formats false true
(cd $G && godot --headless --export-release "Web" ../build/web/index.html 2>&1 | grep -E "^(ERROR|SCRIPT)" | grep -v leaked || true)
(cd $G && godot --headless -s res://tools/pack_holes.gd -- --out=../build/web h02 h03 h04 h05 h06 h07 h08 h09 | tail -1)
python3 -I tools/web_pack.py build/web build/web_host build/web_desktop | tail -1
python3 -I tools/web_pack.py build/web dist/web build/web_desktop > /dev/null
rm -f dist/web/local.html
du -sh dist/web
