"""Autumn overworld: terrain, trees, brush, props, and a composed sample map.

Tiles are 16x16. Trees are taller sprites anchored at their trunk base.
"""
import math
import random
from raster import Canvas, hexc, _seg_dist
import palette as P
import hunter
import animals

T = 16


# ------------------------------------------------------------- foliage ----
def canopy(c, cx, cy, r, base, shade, light, rng, lumps=7):
    """A leafy blob: a ring of lumps with shading from the top-left."""
    pts = []
    for i in range(lumps):
        a = i / lumps * math.tau + rng.uniform(-0.3, 0.3)
        pts.append((cx + math.cos(a) * r * 0.62, cy + math.sin(a) * r * 0.5,
                    r * rng.uniform(0.42, 0.55)))
    for x, y, rr in pts:
        c.ellipse(x + 1, y + 1.5, rr, rr * 0.9, shade)
    c.ellipse(cx, cy + 1, r * 0.8, r * 0.62, shade)
    for x, y, rr in pts:
        c.ellipse(x, y, rr, rr * 0.9, base)
    c.ellipse(cx - 0.5, cy - 0.5, r * 0.62, r * 0.5, base)
    for x, y, rr in pts:
        if y < cy + 1 and x < cx + r * 0.3:
            c.ellipse(x - rr * 0.25, y - rr * 0.3, rr * 0.45, rr * 0.35, light)
    # loose leaf flecks
    for _ in range(int(r * 2)):
        a = rng.uniform(0, math.tau)
        d = rng.uniform(0, r * 0.75)
        c.set(cx + math.cos(a) * d, cy + math.sin(a) * d * 0.8, rng.choice([light, shade]))


def tree(kind, seed=0):
    rng = random.Random(seed)
    if kind == 'pine':
        c = Canvas(28, 46)
        c.rect(12, 36, 4, 9, P.TRUNK)
        c.rect(14, 36, 2, 9, P.TRUNK_SH)
        for i, (y, w) in enumerate([(4, 4), (10, 7), (17, 10), (24, 12), (31, 13)]):
            c.poly([(14, y - 4), (14 - w, y + 8), (14 + w, y + 8)], P.PINE_2)
            c.poly([(14, y - 4), (14 - w + 1, y + 7), (14 + w - 3, y + 7)], P.PINE_1)
            c.poly([(14, y - 3), (14 - w + 3, y + 5), (13, y + 5)], P.PINE_3)
        c.outline(P.OUTLINE)
        return c
    pal = {
        'oak': (P.OAK_1, P.OAK_2, P.OAK_3),
        'maple': (P.MAPLE_1, P.MAPLE_2, P.MAPLE_3),
        'birch': (P.BIRCH_1, P.BIRCH_2, P.BIRCH_3),
    }[kind]
    c = Canvas(34, 46)
    if kind == 'birch':
        c.rect(15, 22, 4, 23, P.BIRCH_BARK)
        for y in range(24, 44, 4):
            c.rect(15 + rng.randint(0, 2), y, 2, 1, P.BIRCH_MARK)
        c.line(17, 30, 23, 24, P.BIRCH_BARK, 1.5)
    else:
        c.poly([(13, 45), (21, 45), (19, 26), (15, 26)], P.TRUNK)
        c.poly([(18, 45), (21, 45), (19, 26), (17.5, 26)], P.TRUNK_SH)
        c.line(16, 32, 11, 25, P.TRUNK, 1.6)
        c.line(19, 30, 24, 24, P.TRUNK, 1.6)
        c.rect(12, 44, 2, 1, P.TRUNK)
        c.rect(21, 44, 2, 1, P.TRUNK_SH)
    canopy(c, 17, 15, 14, *pal, rng, lumps=8)
    c.outline(P.OUTLINE)
    return c


def bush(kind, seed=0):
    rng = random.Random(seed)
    c = Canvas(20, 16)
    pal = {
        'sumac': (P.MAPLE_1, P.MAPLE_2, P.MAPLE_3),
        'hazel': (P.BIRCH_1, P.BIRCH_2, P.BIRCH_3),
        'green': (P.PINE_3, P.PINE_1, '#7fa673'),
        'oak': (P.OAK_1, P.OAK_2, P.OAK_3),
    }[kind]
    canopy(c, 10, 9, 8, *pal, rng, lumps=6)
    if kind == 'green':
        for _ in range(4):
            c.set(rng.randint(5, 15), rng.randint(5, 12), '#c4432d')  # berries
    c.outline(P.OUTLINE)
    return c


def tall_grass(seed=0):
    """Brush patch where animals hide; rustles when something is inside."""
    rng = random.Random(seed)
    c = Canvas(16, 16)
    for i in range(9):
        x = 1 + i * 1.7 + rng.uniform(-0.4, 0.4)
        h = rng.uniform(7, 12)
        col = rng.choice([P.GRASS_DRY, '#d6bc6a', P.GRASS_3, '#b59a4c'])
        c.line(x, 15, x + rng.uniform(-1.5, 1.5), 15 - h, col, 1.2)
    c.outline(P.OUTLINE)
    return c


def rock(seed=0):
    c = Canvas(16, 12)
    c.ellipse(8, 7, 6.5, 4.5, P.STONE_1, P.STONE_2, P.STONE_3)
    c.set(5, 5, P.STONE_3)
    c.outline(P.OUTLINE)
    return c


def stump():
    c = Canvas(14, 12)
    c.rect(3, 4, 8, 6, P.TRUNK)
    c.rect(8, 4, 3, 6, P.TRUNK_SH)
    c.ellipse(7, 4, 4, 1.8, P.PATH_3)
    c.ellipse(7, 4, 2, 0.9, P.PATH_2)
    c.rect(2, 9, 2, 1, P.TRUNK)
    c.rect(10, 9, 2, 1, P.TRUNK_SH)
    c.outline(P.OUTLINE)
    return c


def log():
    c = Canvas(30, 10)
    c.rect(3, 2, 24, 6, P.TRUNK)
    c.rect(3, 6, 24, 2, P.TRUNK_SH)
    for x in range(5, 25, 5):
        c.rect(x, 3, 2, 1, P.TRUNK_SH)
    c.ellipse(3, 5, 2, 3, P.PATH_3)
    c.set(3, 5, P.PATH_2)
    c.ellipse(16, 2, 3, 1, '#7a8a3a')   # moss
    c.outline(P.OUTLINE)
    return c


def tree_stand():
    """Ladder stand: the save point / fast-travel spot in the woods."""
    c = Canvas(22, 40)
    for x in (5, 15):
        c.rect(x, 10, 2, 29, P.GUNMETAL)
    for y in range(14, 38, 4):
        c.rect(6, y, 10, 1, P.GUN_LT)
    c.rect(2, 6, 18, 5, P.CAMO_DK)
    c.rect(2, 6, 18, 2, P.CAMO)
    c.rect(4, 0, 2, 7, P.GUNMETAL)
    c.rect(16, 0, 2, 7, P.GUNMETAL)
    c.rect(4, 0, 14, 2, P.GUN_LT)
    c.outline(P.OUTLINE)
    return c


def cabin(sign=True):
    """Trading Post: the town-hub building where pelts and meat are sold."""
    c = Canvas(64, 52)
    # roof
    c.poly([(0, 22), (32, 2), (64, 22)], '#7a3b2a')
    c.poly([(4, 21), (32, 5), (60, 21)], '#9a4a33')
    for y in range(8, 22, 3):
        c.line(32 - (y - 2) * 1.5, y, 32 + (y - 2) * 1.5, y, '#7a3b2a', 0.8)
    # log walls
    c.rect(4, 22, 56, 28, P.TRUNK)
    for y in range(22, 50, 4):
        c.rect(4, y + 3, 56, 1, P.TRUNK_SH)
        c.ellipse(4, y + 1.5, 1.6, 1.6, P.PATH_3)
        c.ellipse(59, y + 1.5, 1.6, 1.6, P.PATH_3)
    # door + windows
    c.rect(27, 34, 10, 16, '#4a2d1d')
    c.rect(28, 35, 8, 15, '#6b4128')
    c.set(34, 42, P.BIRCH_1)
    for wx in (10, 44):
        c.rect(wx, 30, 10, 8, '#f3cf6a')
        c.rect(wx + 4, 30, 2, 8, P.TRUNK_SH)
        c.rect(wx, 33, 10, 1, P.TRUNK_SH)
    # sign
    if sign:
        c.rect(18, 23, 28, 7, P.PATH_3)
        c.rect(18, 29, 28, 1, P.PATH_2)
        for i, x in enumerate(range(21, 44, 3)):
            c.rect(x, 25, 2, 3, P.TRUNK_SH)
    # antlers over the door
    c.line(28, 32, 25, 29, P.ANTLER, 1)
    c.line(36, 32, 39, 29, P.ANTLER, 1)
    c.outline(P.OUTLINE)
    return c


# ------------------------------------------------------------- terrain ----
def ground(W, H, path_pts, path_w, pond, seed=1):
    """Paint grass, a dirt path and a pond straight onto a canvas, pixel by pixel."""
    rng = random.Random(seed)
    c = Canvas(W, H)
    g = [hexc(P.GRASS_1), hexc(P.GRASS_2), hexc(P.GRASS_3)]
    for y in range(H):
        for x in range(W):
            n = (math.sin(x * 0.21 + y * 0.13) + math.sin(x * 0.05 - y * 0.17) * 1.4)
            col = g[0] if n > -0.6 else g[1]
            if n > 1.2:
                col = g[2]
            c.px[y][x] = col
    # fallen leaves
    leaf = [P.OAK_1, P.MAPLE_1, P.BIRCH_1, P.OAK_3, P.MAPLE_3, P.GRASS_DRY]
    for _ in range(W * H // 22):
        x, y = rng.randrange(W), rng.randrange(H)
        c.set(x, y, rng.choice(leaf))
        if rng.random() < 0.3:
            c.set(x + 1, y, rng.choice(leaf))
    # grass tufts
    for _ in range(W * H // 120):
        x, y = rng.randrange(W), rng.randrange(H)
        c.set(x, y, P.GRASS_2)
        c.set(x + 2, y, P.GRASS_2)
        c.set(x + 1, y - 1, P.GRASS_3)

    def region(inside, base, edge, speck):
        mask = [[inside(x + 0.5, y + 0.5) for x in range(W)] for y in range(H)]
        for y in range(H):
            for x in range(W):
                if not mask[y][x]:
                    continue
                edge_px = any(not (0 <= y + dy < H and 0 <= x + dx < W and mask[y + dy][x + dx])
                              for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                col = edge if edge_px else base
                if not edge_px and rng.random() < 0.06:
                    col = speck
                c.px[y][x] = hexc(col)
        return mask

    def near_path(x, y):
        wob = math.sin(x * 0.09) * 1.5 + math.sin(y * 0.11) * 1.2
        return any(_seg_dist(x, y, *a, *b) < path_w / 2 + wob
                   for a, b in zip(path_pts, path_pts[1:]))

    def in_pond(x, y):
        return any(((x - ex) / rx) ** 2 + ((y - ey) / ry) ** 2 <= 1 for ex, ey, rx, ry in pond)

    region(near_path, P.PATH_1, P.PATH_2, P.PATH_3)
    water = region(in_pond, P.WATER_1, P.WATER_2, P.WATER_3)
    for _ in range(40):
        x, y = rng.randrange(W - 4), rng.randrange(H)
        if all(water[y][x + i] for i in range(-1, 6) if 0 <= x + i < W):
            c.rect(x, y, 4, 1, P.WATER_3)
    return c


def cattails(seed=0):
    rng = random.Random(seed)
    c = Canvas(14, 18)
    for i in range(4):
        x = 2 + i * 3 + rng.uniform(-0.5, 0.5)
        h = rng.uniform(11, 16)
        c.line(x, 17, x, 17 - h, P.PINE_3, 0.9)
        c.rect(int(x), int(17 - h), 2, 3, P.TRUNK)
    c.outline(P.OUTLINE)
    return c


def shadow(c, cx, cy, rx, ry):
    """Darken ground under a sprite."""
    for y in range(int(cy - ry), int(cy + ry) + 1):
        for x in range(int(cx - rx), int(cx + rx) + 1):
            if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1:
                p = c.get(x, y)
                if p:
                    c.px[y][x] = (int(p[0] * 0.72), int(p[1] * 0.72), int(p[2] * 0.75), 255)


# ---------------------------------------------------------- the sample ----
def overworld(frame=0):
    """A 320x208 slice of Maple Hollow: the Trading Post at the trailhead,
    a pond, mixed hardwoods, and game moving through the brush."""
    W, H = 320, 208
    path = [(48, 56), (54, 80), (90, 100), (130, 112), (170, 132), (220, 140), (270, 150), (330, 154)]
    pond = [(252, 30, 30, 15), (236, 40, 16, 10), (270, 44, 14, 8)]
    c = ground(W, H, path, 15, pond, seed=7)

    sprites = []   # (base_y, x, y, canvas): sorted so lower things draw in front

    def put(spr, x, y, sh=True):
        if sh:
            shadow(c, x + spr.w / 2, y + spr.h - 1, spr.w * 0.38, 2.6)
        sprites.append((y + spr.h, x, y, spr))

    put(cabin(), 16, 4)
    trees = [
        ('pine', 0, -18), ('maple', 92, -14), ('oak', 120, -20), ('birch', 186, 40),
        ('pine', 290, -12), ('oak', 268, 10), ('maple', 300, 44), ('birch', 196, -18),
        ('oak', -8, 80), ('maple', 18, 120), ('pine', -4, 150), ('birch', 60, 150),
        ('oak', 100, 168), ('maple', 150, 160), ('pine', 240, 150), ('oak', 286, 130),
        ('birch', 300, 166), ('maple', 228, 64),
    ]
    for i, (k, x, y) in enumerate(trees):
        put(tree(k, seed=i), x, y)
    bushes = [('sumac', 80, 36), ('hazel', 160, 64), ('green', 50, 100), ('oak', 262, 112),
              ('sumac', 206, 120), ('hazel', 124, 140), ('green', 36, 190), ('sumac', 280, 196),
              ('oak', 184, 190), ('hazel', 300, 86)]
    for i, (k, x, y) in enumerate(bushes):
        put(bush(k, seed=i + 40), x, y)
    for i, (x, y) in enumerate([(176, 104), (192, 104), (176, 118), (208, 98), (90, 120),
                                 (106, 120), (90, 134), (60, 118), (138, 150), (154, 150)]):
        put(tall_grass(seed=i), x, y, sh=False)
    put(rock(), 64, 74)
    put(rock(), 214, 180)
    put(stump(), 152, 128)
    put(log(), 40, 170)
    put(tree_stand(), 290, 58)
    for i, (x, y) in enumerate([(220, 22), (228, 40), (276, 36)]):
        put(cattails(seed=i), x, y, sh=False)

    # characters
    h = hunter.walk('right')[frame]
    put(h, 96, 86)
    put(animals.deer(frame, antlers=3), 190, 66)
    put(animals.turkey((frame + 1) % 4), 132, 92)
    put(animals.rabbit(frame), 64, 142)
    put(animals.fox((frame + 2) % 4), 222, 160)

    for _, x, y, spr in sorted(sprites, key=lambda s: s[0]):
        c.paste(spr, int(x), int(y))

    # rustle mark over the brush patch where something is hiding
    if frame % 2 == 0:
        for x, y in [(96, 116), (98, 115), (100, 116), (110, 114), (112, 113), (114, 114)]:
            c.set(x, y, P.WHITE)
    return c
