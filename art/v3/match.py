"""Style-match test against the reference Chris sheet (ref/).

The reference is ~42x80 px per character, naturalistic colours, 5-8 tones
per material, small-cluster surface texture (camo, fur), a dark 1px outline,
and a soft rim of light on the top-left. This draws a buck, a tree and
ground at that same pixel density so they can stand next to him.
"""
import math
import random
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, '../v2')
sys.path.insert(0, '..')
from px import Px, value_noise, BAYER4, hx, clump_canopy, RAMP, ramp  # noqa: E402
import buck as B  # noqa: E402

OUTLINE = '#1a1411'
FUR = ['#2b1a13', '#3e2619', '#563420', '#6f4529', '#8a5833', '#a46d40', '#bb8352', '#cf9c68', '#dfb683']
FUR_W = ['#8f8576', '#b5ab98', '#d5ccba', '#ece5d6']


class TexDraw(B.Draw):
    """Draw with more tones and a fur/grain texture mixed into the shading."""

    def __init__(self, s, pal, seed=1):
        super().__init__(s, pal=pal)
        self.tex = value_noise(self.p.w, self.p.h, 2, seed, octaves=1)
        self.streak = value_noise(self.p.w, self.p.h, 6, seed + 3, octaves=1)

    def shade(self, nx, ny, bias=0.0, x=0, y=0):
        lam = nx * B.LIGHT[0] + ny * B.LIGHT[1]
        v = 0.5 + lam * 0.55 + bias
        if 0 <= y < self.p.h and 0 <= x < self.p.w:
            v += (self.tex[y, x] - 0.5) * 0.42            # fur clusters
            v += (self.streak[y, x] - 0.5) * 0.12
        v += (BAYER4[y % 4, x % 4] - 0.5) * 0.08
        i = int(round(v * (len(self.pal) - 1)))
        return self.pal[max(0, min(len(self.pal) - 1, i))]


def textured_buck(frame=0, s=2.4, seed=1):
    # Reuse the anatomy from v2 but render with the textured, higher-tone drawer.
    orig = B.Draw
    B.Draw = lambda s_, pad_top=10, pal=None: TexDraw(s_, FUR, seed)
    try:
        p = B.deer(frame, s)
    finally:
        B.Draw = orig
    # replace v2's selective outline with the reference's uniform dark line
    a = p.a
    dark = (a[:, :, 3] > 0) & (a[:, :, :3].astype(int).sum(2) < 75)
    return p


def tree(seed=4, kind='orange'):
    """Broadleaf at reference density: ~3x the v2 tree, more clumps, textured."""
    rng = random.Random(seed)
    p = Px(150, 190)
    cx, base = 75, 186
    bark = ['#1e1512', '#2f211a', '#452f22', '#5e412e', '#7a573d', '#94704f']
    tex = value_noise(150, 190, 2, seed, octaves=2)
    for y in range(92, base + 1):
        flare = max(0, (y - (base - 12)) * 0.9)
        x0, x1 = cx - 8 - flare, cx + 8 + flare
        for x in range(int(x0), int(math.ceil(x1))):
            t = (x - x0) / (x1 - x0)
            v = 0.75 - t * 0.6 + (tex[y, x] - 0.5) * 0.35
            if (x * 5 + y // 3) % 9 == 0:
                v -= 0.25                                     # vertical bark furrows
            p.set(x, y, bark[max(0, min(5, int(v * 5.5)))])
    for k, (dx, dy) in enumerate([(26, -36), (-24, -30), (6, -48)]):
        for i in range(22):
            t = i / 21
            p.set(int(cx + dx * t), int(100 + dy * t), bark[3 if dx < 0 else 2])
            p.set(int(cx + dx * t) + 1, int(100 + dy * t), bark[2])
    # canopy: many small clumps for a leafy edge
    clump_canopy(p, cx, 72, 64, 56, kind, seed, n=260, jag=0.3)
    # leaf-sized texture: break flat areas into 2px leaf clusters
    leaf = RAMP[kind]
    t2 = value_noise(150, 190, 2, seed + 11, octaves=1)
    for y in range(p.h):
        for x in range(p.w):
            if p.a[y, x, 3] and y < 132 and t2[y, x] > 0.72:
                c = p.a[y, x, :3].astype(int)
                for i, hcol in enumerate(leaf):
                    if (hx(hcol)[:3].astype(int) == c).all():
                        p.set(x, y, leaf[min(len(leaf) - 1, i + 1)])
                        break
    return p, (cx, base)


def ground(w, h, seed=2):
    p = Px(w, h)
    base = value_noise(w, h, 60, seed, octaves=2)
    fine = value_noise(w, h, 3, seed + 1, octaves=2)
    G = ['#2f3b26', '#3d4b2c', '#4c5b32', '#5d6c39', '#6f7c40', '#848d49', '#9c9d54']
    v = base * 0.55 + fine * 0.45
    yy, xx = np.mgrid[0:h, 0:w]
    v = v + (BAYER4[yy % 4, xx % 4] - 0.5) * 0.06
    idx = np.clip((v * 7.5 - 1.2).astype(int), 0, 6)
    for i in range(7):
        p.a[idx == i] = hx(G[i])
    rng = random.Random(seed)
    leaf = ['#c25a2a', '#e8893a', '#be3f33', '#d3a838', '#8e3b2a']
    for _ in range(w * h // 420):
        x, y = rng.randrange(w - 2), rng.randrange(h - 1)
        c = rng.choice(leaf)
        p.set(x, y, c)
        p.set(x + 1, y, c)
        p.set(x, y + 1, '#2f2418')
    return p


def outline(p, col=OUTLINE):
    p.outline(col)


def compose(frame=0):
    W, H = 480, 270
    scene = ground(W, H)
    ref = Image.open('ref/chris_sheet_native.png')
    # right-facing row; cells are 80x108
    cell = ref.crop((frame * 80, 108 + 18, frame * 80 + 80, 216))
    chris = Px(cell.width, cell.height)
    chris.a = np.array(cell)
    t, (tx, tb) = tree()
    t2, _ = tree(9, 'red')
    t3, _ = tree(12, 'gold')
    b = textured_buck(frame)
    outline(b)
    for spr, sx, base in [(t2, 300, 150), (t3, -30, 140)]:
        yy, xx = np.mgrid[0:H, 0:W]
        scene.darken(((xx - (sx + 95)) / 60) ** 2 + ((yy - base) / 12) ** 2 <= 1, 0.7)
        outline(spr)
        scene.blit(spr, sx, base - spr.h + 4)
    yy, xx = np.mgrid[0:H, 0:W]
    scene.darken(((xx - 300) / 34) ** 2 + ((yy - 226) / 6) ** 2 <= 1, 0.72)
    scene.darken(((xx - 128) / 18) ** 2 + ((yy - 238) / 4) ** 2 <= 1, 0.72)
    scene.blit(b, 300 - b.w // 2, 230 - b.h)
    scene.blit(chris, 128 - 40, 240 - chris.h + 2)
    return scene


if __name__ == '__main__':
    compose().image(2).save(sys.argv[1])
