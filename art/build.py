"""Export every sprite to PNG spritesheets (4 frames, left to right) and run
the leg check. Usage: python3 build.py <out_dir>
"""
import os
import subprocess
import sys
from raster import sheet
import animals
import battle
import hunter
import world

LEG_COLORS = {'leg_L': '#ff3d9a', 'leg_R': '#25c4e8',
              'arm_L': '#ffa3cf', 'arm_R': '#9be6f7'}
QUAD_COLORS = {'FL': '#ff3d9a', 'BL': '#ffa3cf', 'FR': '#25c4e8', 'BR': '#9be6f7'}


def main(out):
    os.makedirs(out, exist_ok=True)
    save = lambda im, name: im.save(os.path.join(out, name + '.png'))

    for d in ('down', 'up', 'left', 'right'):
        frames = hunter.walk(d)
        save(sheet(frames), f'hunter_{d}')
        save(sheet([f.recolor_tags(LEG_COLORS) for f in frames]), f'legcheck_hunter_{d}')

    for name in animals.ROSTER:
        frames = animals.walk(name)
        save(sheet(frames), name)
        if name not in ('cottontail', 'wild_turkey'):
            save(sheet([f.recolor_tags(QUAD_COLORS) for f in frames]), f'legcheck_{name}')
    save(sheet([f.recolor_tags(LEG_COLORS) for f in animals.walk('wild_turkey')]), 'legcheck_wild_turkey')

    for enemy in ('whitetail_buck', 'black_bear', 'wild_turkey', 'red_fox', 'ghost_buck'):
        fn = {
            'whitetail_buck': lambda f: animals.deer(f, s=2, antlers=3),
            'ghost_buck': lambda f: animals.deer(f, s=2, antlers=3, ghost=True),
            'black_bear': lambda f: animals.bear(f, s=2),
            'red_fox': lambda f: animals.fox(f, s=2.2),
            'wild_turkey': lambda f: animals.turkey(f, s=2.2, strut=True),
        }[enemy]
        save(sheet([fn(f) for f in range(4)]), f'battle_{enemy}')
    save(battle.backdrop().image(), 'battle_backdrop')
    save(battle.hunter_back().image(), 'hunter_back')

    save(sheet([world.overworld(f) for f in range(4)]), 'overworld')

    report = subprocess.run([sys.executable, 'verify.py'], capture_output=True, text=True,
                            cwd=os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(out, 'legcheck.txt'), 'w') as f:
        f.write(report.stdout)
    print(report.stdout)
    if report.returncode:
        sys.exit('Leg check failed; sprites not approved.')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'out')
