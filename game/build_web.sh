#!/usr/bin/env bash
# Export the web build to game/build/web (single-threaded: runs on any static host, incl. iOS Safari).
set -euo pipefail
cd "$(dirname "$0")"
godot --headless --import >/dev/null 2>&1 || true
mkdir -p build/web
godot --headless --export-release "Web" build/web/index.html 2>&1 | grep -E "ERROR|SCRIPT ERROR" && exit 1 || true
echo "exported: $(du -sh build/web | cut -f1)"
