"""Split the web build so the first download is only what the clubhouse and hole 1 need.

usage: python3 -I golf/tools/web_split.py golf/build/split.json

Writes, from tools/hole_art.json (the art each hole opens) and assets/golfer/golfer.json:
  exclude  the files left out of the game's main download: art from the per-hole folders that hole 1
           doesn't use, songs 2 and 3, and her old swing frames (the video ones replaced them)
  packs    what each later download carries besides the hole's own folder: every piece of that
           hole's art not already in the main download (a picture two holes share is in both packs,
           so a hole picked straight from the clubhouse has all it needs); "music" is songs 2 and 3
Art in those folders that no hole uses is left out of everything (the files stay in the project).
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
main = set(holes['h01'])

per_hole = set()
for folder in art['folders']:
    for imp in glob.glob(os.path.join(game, folder, '**', '*.import'), recursive=True):
        per_hole.add(os.path.relpath(imp, game)[:-len('.import')])
exclude = sorted(per_hole - main)
packs = {h: sorted(set(v) - main) for h, v in holes.items() if h != 'h01'}

# songs 2 and 3 come after the game starts (scripts/music.gd plays whichever have arrived)
songs = ['assets/music/bad_luck_on_the_back_nine.mp3', 'assets/music/stay_off_the_grass.mp3']
exclude += songs
packs['music'] = songs

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
for png in sorted(glob.glob(os.path.join(game, 'assets', 'golfer', '*.png'))):
    if os.path.basename(png) not in used_frames:
        exclude.append(os.path.relpath(png, game))

json.dump({'exclude': exclude, 'packs': packs}, open(out, 'w'), indent=1)
print('web_split: %d files left out of the first download; packs %s' % (
    len(exclude), {k: len(v) for k, v in packs.items()}))
