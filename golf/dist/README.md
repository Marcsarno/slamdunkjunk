# golf/dist/web

The built web game, as served by the Vercel project `midnight-golf` (root directory `golf/dist/web`,
no build step). Rebuild it only from committed sources:

    godot --headless --path golf/game --export-release "Web" ../build/web/index.html
    godot --headless --path golf/game -s res://tools/pack_holes.gd -- --out=../build/web h02 h03 h04 h05 h06 h07 h08 h09
    python3 -I golf/tools/web_pack.py golf/build/web golf/dist/web && rm golf/dist/web/local.html
