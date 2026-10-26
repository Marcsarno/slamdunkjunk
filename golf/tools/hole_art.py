"""Turn the files each hole opened (tools/hole_art.sh) into tools/hole_art.json: for each hole, the
source files of the art it uses from the folders that differ hole to hole (trees, skies, ground
textures, hazards, flags), found through their imports.

usage: python3 -I golf/tools/hole_art.py <dir of h01.txt ... h09.txt> golf/tools/hole_art.json
"""
import glob
import json
import os
import re
import sys

FOLDERS = ('assets/cards/', 'assets/sky/', 'assets/textures/', 'assets/hazards/', 'assets/flags/')

opened_dir, out = sys.argv[1], sys.argv[2]
game = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'game')
opened = {os.path.basename(f)[:-4]: set(open(f).read().split()) for f in sorted(glob.glob(opened_dir + '/h0*.txt'))}
if len(opened) != 9 or any(len(v) < 100 for v in opened.values()):
    sys.exit('hole_art: a hole run failed (%s)' % {k: len(v) for k, v in opened.items()})
holes = {h: [] for h in sorted(opened)}
for folder in FOLDERS:
    for imp in sorted(glob.glob(os.path.join(game, folder, '**', '*.import'), recursive=True)):
        src = os.path.relpath(imp, game)[:-len('.import')]
        dests = [d[len('res://'):] for d in re.findall(r'"(res://\.godot/imported/[^"]+)"', open(imp).read())]
        for h, files in opened.items():
            if src in files or any(d in files for d in dests):
                holes[h].append(src)
json.dump({'folders': FOLDERS, 'holes': holes}, open(out, 'w'), indent=1)
print('hole_art: %s' % {h: len(v) for h, v in holes.items()})
