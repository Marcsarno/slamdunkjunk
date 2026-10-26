"""Split the web build so the game shows its title after only a small first download, and the rest
arrives in stages while the player looks at the title and the clubhouse.

usage: python3 -I golf/tools/web_split.py golf/build/split.json

Stages (scripts/holes.gd fetches the packs; scripts/front.gd and main.gd ask for them):
  main     the first download: the engine's data, the scripts, the title and clubhouse pictures, the
           balls, fonts and sound effects (everything not listed under exclude)
  core     loaded behind the title (its bar is under PLAY, which waits for it): her swing frames, the
           bag and lanterns, the first song
  course   the art every hole uses, behind the clubhouse
  h01..h09 each hole's own folder (tools/pack_holes.gd adds it) and the art only that hole uses;
           hole 1 loads behind the clubhouse after course
  art_<n>  art a few holes share (not all), one pack per set of holes using it, named by their
           numbers (art_3468: holes 3, 4, 6 and 8): fetched once, before the first of them, so no
           picture downloads twice (game/assets/pack_deps.json tells scripts/holes.gd which a hole needs)
  music    songs 2 and 3

Writes, from tools/hole_art.json (the art each hole opens) and assets/golfer/golfer.json, what the
main export leaves out ("exclude"), what each pack carries ("packs") and the art packs each hole needs
("deps", also written to game/assets/pack_deps.json). Her old swing frames (the
video ones replaced them) and art in the per-hole folders that no hole uses go nowhere (the files stay
in the project).
"""
import collections
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

# the arm and bridge lanterns share the post lantern's timber and rind (lanterns/lantern_*.tres): the
# copies of those textures Godot pulls out of their models are never opened, so they're left out
unused_props = {'assets/props/lanterns/%s_%s.png' % (m, t) for m in ('arm', 'bridge') for t in ('wood', 'pumpkin')}
core = [f for f in frames if f not in old_frames] + \
    [f for f in imported('assets/props') if f not in unused_props] + songs[:1]
course = sorted(everywhere)
packs = {'core': core, 'course': course, 'music': songs[1:]}
users = collections.defaultdict(set)          # a picture -> the holes that open it (not all of them)
for h, v in holes.items():
    for f in set(v) - everywhere:
        users[f].add(h)
groups = collections.defaultdict(list)        # a set of holes -> the pictures exactly they share
for f, hs in users.items():
    if len(hs) > 1:
        groups[tuple(sorted(hs))].append(f)
deps = {h: [] for h in sorted(holes)}
for hs, files in sorted(groups.items()):
    gid = 'art_' + ''.join(str(int(h[1:])) for h in hs)
    packs[gid] = sorted(files)
    for h in hs:
        deps[h].append(gid)
for h, v in holes.items():
    packs[h] = sorted(f for f in set(v) - everywhere if len(users[f]) == 1)
exclude = sorted(per_hole | set(frames) | set(imported('assets/props')) | set(songs)) + ['assets/holes/h01/*']

json.dump({'exclude': exclude, 'packs': packs, 'deps': deps}, open(out, 'w'), indent=1)
json.dump(deps, open(os.path.join(game, 'assets', 'pack_deps.json'), 'w'), indent=1, sort_keys=True)
print('web_split: %d files left out of the first download; packs %s' % (
    len(exclude), {k: len(v) for k, v in packs.items()}))
