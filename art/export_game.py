"""Export every asset the Godot game loads into game/assets/.

Usage: python3 export_game.py [game_dir]
Fails (non-zero) if the leg check or an area reachability check fails.
"""
import os
import subprocess
import sys

from PIL import Image

import animals
import areas
import battle
import hunter
from raster import sheet

BATTLE_SCALE = {'cottontail': 3.0, 'wild_turkey': 2.6, 'whitetail_doe': 2.5, 'red_fox': 2.6,
                'whitetail_buck': 2.5, 'black_bear': 2.5, 'ghost_buck': 2.5}


def battle_frames(name):
    s = BATTLE_SCALE[name]
    fn = {
        'cottontail': lambda f: animals.rabbit(f, s),
        'wild_turkey': lambda f: animals.turkey(f, s, strut=True),
        'whitetail_doe': lambda f: animals.deer(f, s),
        'red_fox': lambda f: animals.fox(f, s),
        'whitetail_buck': lambda f: animals.deer(f, s, antlers=3),
        'black_bear': lambda f: animals.bear(f, s),
        'ghost_buck': lambda f: animals.deer(f, s, antlers=3, ghost=True),
    }[name]
    return [fn(f) for f in range(4)]


def main(game_dir):
    here = os.path.dirname(os.path.abspath(__file__))
    A = os.path.join(game_dir, 'assets')
    dirs = {k: os.path.join(A, k) for k in ('chars', 'animals', 'battle', 'props', 'areas')}
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)

    report = subprocess.run([sys.executable, 'verify.py'], capture_output=True, text=True, cwd=here)
    print(report.stdout.strip())
    if report.returncode:
        sys.exit('Leg check failed: not exporting.')

    for d in ('down', 'up', 'left', 'right'):
        sheet(hunter.walk(d)).save(os.path.join(dirs['chars'], f'chris_{d}.png'))
    battle.hunter_back(1.8).image().save(os.path.join(dirs['battle'], 'chris_back.png'))

    for name in animals.ROSTER:
        sheet(animals.walk(name)).save(os.path.join(dirs['animals'], f'{name}.png'))
        sheet(battle_frames(name)).save(os.path.join(dirs['battle'], f'{name}.png'))

    battle.backdrop(480, 270, foe=(340, 128, 78, 14), me=(110, 196, 96, 16)).image().save(
        os.path.join(dirs['battle'], 'backdrop_hollow.png'))

    for name, c in areas.prop_sprites().items():
        c.image().save(os.path.join(dirs['props'], f'{name}.png'))

    for build in (areas.town, areas.hollow):
        a = build()
        problems = areas.check(a)
        if problems:
            sys.exit('\n'.join(problems))
        a.export(dirs['areas'])
        print(f'area {a.name}: {a.w}x{a.h} tiles, {len(a.props)} props')

    # app icon: Chris's face, scaled up
    face = hunter.walk('down')[0].image().crop((2, 0, 14, 12)).resize((120, 120), Image.NEAREST)
    icon = Image.new('RGBA', (128, 128), (226, 96, 15, 255))
    icon.alpha_composite(face, (4, 8))
    icon.save(os.path.join(game_dir, 'icon.png'))
    print('exported to', A)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'game'))
