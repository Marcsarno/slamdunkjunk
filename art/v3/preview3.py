import sys
sys.path.insert(0, '../v2'); sys.path.insert(0, '..')
from px import Px
import chris3
rows = [chris3.walk(d) for d in ('down', 'right', 'up', 'left')]
bg = Px(4 * 52, 4 * 86, '#1f2a20')
for r, frames in enumerate(rows):
    for i, f in enumerate(frames):
        bg.blit(f.p, i * 52 + 2, r * 86 + 1)
bg.image(int(sys.argv[2]) if len(sys.argv) > 2 else 3).save(sys.argv[1])
