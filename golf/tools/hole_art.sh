#!/usr/bin/env bash
# Which art each hole really opens: plays each hole's set-up (tests/light_set.gd) under strace and keeps
# the trees, skies, ground textures, hazards and flags it reads, so the web build can ship hole 1's in
# the first download and each later hole's in its own (tools/web_split.py). Writes tools/hole_art.json.
# Needs xvfb-run and strace; build_web.sh reruns it when a hole's files are newer than that file.
#   bash golf/tools/hole_art.sh
set -euo pipefail
cd "$(dirname "$0")/.."
T=$(mktemp -d)
run() {
	(cd game && timeout 400 xvfb-run -a -s "-screen 0 720x1560x24" strace -f -qq -e trace=openat -o "$T/$1.raw" \
		godot --path . --rendering-driver opengl3 --resolution 720x1560 -- --hole=$1 --light-set="$T/shots" >/dev/null 2>&1) || true
	grep -o '"[^"]*/golf/game/[^"]*"' "$T/$1.raw" | grep -v ENOENT | tr -d '"' | sed 's|.*/golf/game/||' | sort -u > "$T/$1.txt"
	rm -f "$T/$1.raw"
}
for set in "h01 h02 h03" "h04 h05 h06" "h07 h08 h09"; do
	for h in $set; do run $h & done
	wait
done
python3 -I tools/hole_art.py "$T" tools/hole_art.json
rm -rf "$T"
