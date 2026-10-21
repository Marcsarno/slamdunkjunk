"""Battle screen art: 240x160 backdrop, hunter back-sprite, enemy placement.

The HUD (names, bars, menu) is drawn by the page/game on top of this.
"""
import math
import random
from raster import Canvas, hexc
import palette as P
import animals
from world import canopy


class _Scaled:
    """Draw with coordinates designed at 1x onto a bigger canvas."""

    def __init__(self, c, s):
        self.c, self.s = c, s

    def line(self, x0, y0, x1, y1, col, w=1.0):
        s = self.s
        self.c.line(x0 * s, y0 * s, x1 * s, y1 * s, col, w * s)

    def ellipse(self, cx, cy, rx, ry, col, shade=None, light=None):
        s = self.s
        self.c.ellipse(cx * s, cy * s, rx * s, ry * s, col, None, shade, light)

    def rect(self, x, y, w, h, col):
        s = self.s
        self.c.rect(round(x * s), round(y * s), max(1, round(w * s)), max(1, round(h * s)), col)


def hunter_back(s=1.0):
    """Chris from behind, rifle shouldered and aimed up-right."""
    c = Canvas(int(64 * s), int(52 * s))
    d = _Scaled(c, s)
    d.line(30, 30, 62, 9, P.GUNMETAL, 2.4)
    d.line(30, 29, 61, 8.5, P.GUN_LT, 0.8)
    d.line(24, 35, 34, 27, P.STOCK, 4.2)
    d.line(25, 36, 33, 29, P.STOCK_SH, 1.6)
    d.line(38, 21, 50, 13, P.GUNMETAL, 4.2)          # scope
    d.line(38, 20, 49, 12.5, P.GUN_LT, 1.0)
    d.rect(37, 21, 3, 3, P.GUNMETAL)
    d.ellipse(24, 46, 21, 16, P.BLAZE, P.BLAZE_SH)
    d.ellipse(24, 46, 11, 14, P.BLAZE_SH)
    d.ellipse(24, 45, 10, 14, P.BLAZE)
    d.rect(22, 34, 4, 18, P.BLAZE_SH)                # vest seam
    d.ellipse(6, 44, 6, 9, P.CAMO, P.CAMO_DK, P.CAMO_LT)
    d.line(38, 38, 42, 25, P.CAMO, 7)
    d.line(39, 36, 42, 26, P.CAMO_LT, 2)
    d.ellipse(42, 24, 3, 2.6, P.SKIN, P.SKIN_SH)       # trigger hand
    rng = random.Random(3)
    for _ in range(int(26 * s * s)):
        x, y = rng.randint(1, c.w - 2), rng.randint(int(32 * s), c.h - 1)
        if c.get(x, y) == hexc(P.CAMO):
            c.rect(x, y, 2, 1, rng.choice([P.CAMO_DK, P.CAMO_GR, P.CAMO_LT]))
    d.ellipse(24, 30, 6, 4, P.SKIN_SH)                 # neck
    d.ellipse(24, 20, 10, 11, P.HAIR, P.HAIR_SH)
    d.ellipse(14.5, 22, 2.2, 3.2, P.SKIN, P.SKIN_SH)   # ear
    d.ellipse(21, 14, 5, 3.5, '#7d5a3c')               # hair highlight
    c.outline(P.OUTLINE)
    c.outline(P.OUTLINE)
    return c


def backdrop(W=240, H=160, foe=(176, 92, 46, 10), me=(62, 150, 58, 12)):
    c = Canvas(W, H)
    rng = random.Random(11)
    top, bot = hexc('#f2d7a6'), hexc('#cfe0d9')
    for y in range(H):
        t = min(1, y / 70)
        col = tuple(int(top[i] * (1 - t) + bot[i] * t) for i in range(3)) + (255,)
        for x in range(W):
            c.px[y][x] = col
    # distant ridge
    for x in range(W):
        h = 44 + math.sin(x * 0.03) * 6 + math.sin(x * 0.11) * 2
        for y in range(int(h), 70):
            c.px[y][x] = hexc('#b9a98c')
    # treeline
    cols = [(P.OAK_1, P.OAK_2, P.OAK_3), (P.MAPLE_1, P.MAPLE_2, P.MAPLE_3),
            (P.BIRCH_1, P.BIRCH_2, P.BIRCH_3), (P.PINE_1, P.PINE_2, P.PINE_3)]
    for i in range(W // 16 + 1):
        x = i * 16 + rng.randint(-4, 4)
        canopy(c, x, 58 + rng.randint(-3, 3), rng.randint(9, 13), *rng.choice(cols), rng, lumps=6)
    # meadow
    for y in range(66, H):
        for x in range(W):
            n = math.sin(x * 0.07 + y * 0.3) + math.sin(x * 0.019 - y * 0.05)
            c.px[y][x] = hexc(P.GRASS_3 if n > 0.9 else (P.GRASS_1 if n > -0.7 else P.GRASS_2))
    for _ in range(W * H // 70):
        x, y = rng.randrange(W), rng.randrange(66, H)
        c.set(x, y, rng.choice([P.OAK_1, P.MAPLE_1, P.BIRCH_1, P.GRASS_DRY]))
    # platforms (trampled grass where each side stands)
    for cx, cy, rx, ry in (foe, me):
        c.ellipse(cx, cy + 1, rx, ry, P.GRASS_2)
        c.ellipse(cx, cy, rx - 2, ry - 2, P.GRASS_DRY)
        c.ellipse(cx - 6, cy - 2, rx - 14, ry - 5, '#d6bc6a')
        for _ in range(40):
            a = rng.uniform(0, math.tau)
            d = rng.uniform(0.2, 0.95)
            c.set(cx + math.cos(a) * rx * d, cy + math.sin(a) * ry * d, rng.choice([P.OAK_2, P.GRASS_2, P.MAPLE_1]))
    return c


def scene(enemy='whitetail_buck', frame=0):
    c = backdrop()
    spr = {
        'whitetail_buck': lambda: animals.deer(frame, s=2, antlers=3),
        'ghost_buck': lambda: animals.deer(frame, s=2, antlers=3, ghost=True),
        'black_bear': lambda: animals.bear(frame, s=2),
        'red_fox': lambda: animals.fox(frame, s=2.2),
        'wild_turkey': lambda: animals.turkey(frame, s=2.2, strut=True),
    }[enemy]()
    c.paste(spr, 176 - spr.w // 2, 94 - spr.h)
    hb = hunter_back()
    c.paste(hb, 30, 160 - hb.h)
    return c
