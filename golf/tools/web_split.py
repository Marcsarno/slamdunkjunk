"""Split the web build so the game shows its title after only a small first download, and the rest
arrives in stages while the player looks at the title and the clubhouse.

usage: python3 -I golf/tools/web_split.py golf/build/split.json

Stages (scripts/holes.gd fetches the packs; scripts/front.gd and main.gd ask for them):
  main     the first download: the engine's data, the scripts, the title and clubhouse pictures, the
           balls, fonts and sound effects (everything not listed under exclude)
  core     loaded behind the title (its bar is under PLAY, which waits for it): her swing frames, the
           bag and lanterns, the first song
  course   the art every hole uses, behind the clubhouse
  h01..h09 each hole's own folder (tools/pack_holes.gd adds it) and its art not in core (a picture a
           few holes share is in each of their packs, so a hole picked from the clubhouse has all it
           needs); hole 1 loads behind the clubhouse after course
  music    songs 2 and 3

Writes, from tools/hole_art.json (the art each hole opens) and assets/golfer/golfer.json, what the
main export leaves out ("exclude") and what each pack carries ("packs"). Her old swing frames (the
video ones replaced them) and art in the per-hole folders that no hole uses go nowhere (the files stay
in the project).
"""
import glob
import json
import os
import sys

out = sys.argv[1]
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
game = os.path.join(root, 'game')
art = json.load(open(os.path.join(root, 'tools', 'hole_art.json')))
holes = art['holes']
everywhere = set.intersection(*(set(v) for v in holes.values()))

per_hole = set()
for folder in art['folders']:
    for imp in glob.glob(os.path.join(game, folder, '**', '*.import'), recursive=True):
        per_hole.add(os.path.relpath(imp, game)[:-len('.import')])


def imported(folder):
    """The imported files (their sources) under a folder of the game."""
    return sorted(os.path.relpath(imp, game)[:-len('.import')]
                  for imp in glob.glob(os.path.join(game, folder, '**', '*.import'), recursive=True))


songs = ['assets/music/brittanys_graveyard_shift.mp3', 'assets/music/bad_luck_on_the_back_nine.mp3',
         'assets/music/stay_off_the_grass.mp3']

# her frames: the club sprites (driver, iron, putter) shown through golfer.gd's face_set/back_set,
# which take the "video" set when there is one, plus the celebration
sets = json.load(open(os.path.join(game, 'assets', 'golfer', 'golfer.json')))
style = 'video'
used_sets = {'video_celebrate'}
for sprite in ('driver', 'iron', 'putter'):
    face, back = '%s_%s' % (style, sprite), '%s_back_%s' % (style, sprite)
    used_sets.add(face if face in sets else sprite)
    used_sets.add(back if back in sets else 'back_' + sprite)
used_frames = {f['file'] for s in used_sets for f in sets[s]['frames'].values()}
frames = imported('assets/golfer')
old_frames = [f for f in frames if os.path.basename(f) not in used_frames]

core = [f for f in frames if f not in old_frames] + imported('assets/props') + songs[:1]
course = sorted(everywhere)
packs = {'core': core, 'course': course, 'music': songs[1:]}
for h, v in holes.items():
    packs[h] = sorted(set(v) - everywhere)
exclude = sorted(per_hole | set(frames) | set(imported('assets/props')) | set(songs)) + ['assets/holes/h01/*']

json.dump({'exclude': exclude, 'packs': packs}, open(out, 'w'), indent=1)
print('web_split: %d files left out of the first download; packs %s' % (
    len(exclude), {k: len(v) for k, v in packs.items()}))
