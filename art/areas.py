"""Area layouts for the game: Pinecrest (town) and Maple Hollow.

Each area is generated from a seed plus hand-placed features, then exported
as a painted ground PNG and a JSON file the game reads:

  blocked   rows of '0'/'1', one char per 16px tile
  brush     rows of '0'/'1': tall grass Chris can hide in
  props     sprites to y-sort (trees, bushes, buildings), with base_y
  exits     edge tiles that lead to another area
  doors     building doors (bumping one opens that shop)
  zones     spawn rectangles per species
"""
import json
import math
import os
import random

from raster import Canvas, hexc, _seg_dist
import palette as P
import world

T = 16


class Area:
    def __init__(self, name, w, h, seed):
        self.name, self.w, self.h = name, w, h
        self.rng = random.Random(seed)
        self.path = [[False] * w for _ in range(h)]
        self.water = [[False] * w for _ in range(h)]
        self.blocked = [[False] * w for _ in range(h)]
        self.brush = [[False] * w for _ in range(h)]
        self.reserved = [[False] * w for _ in range(h)]   # keep clear of random props
        self.props = []
        self.exits = []
        self.doors = []
        self.zones = {}
        self.start = None

    # ---- layout helpers ------------------------------------------------
    def inside(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def free(self, x, y):
        return (self.inside(x, y) and not self.blocked[y][x] and not self.path[y][x]
                and not self.water[y][x] and not self.reserved[y][x] and not self.brush[y][x])

    def path_line(self, pts, width=2):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            n = max(abs(x1 - x0), abs(y1 - y0))
            for i in range(n + 1):
                x = round(x0 + (x1 - x0) * i / max(n, 1))
                y = round(y0 + (y1 - y0) * i / max(n, 1))
                for dx in range(width):
                    for dy in range(width):
                        if self.inside(x + dx, y + dy):
                            self.path[y + dy][x + dx] = True

    def ellipse_cells(self, cx, cy, rx, ry):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if self.inside(x, y) and ((x + .5 - cx) / rx) ** 2 + ((y + .5 - cy) / ry) ** 2 <= 1:
                    yield x, y

    def pond(self, cx, cy, rx, ry):
        for x, y in self.ellipse_cells(cx, cy, rx, ry):
            self.water[y][x] = True
            self.blocked[y][x] = True

    def brush_patch(self, cx, cy, rx, ry):
        for x, y in self.ellipse_cells(cx, cy, rx, ry):
            if not self.path[y][x] and not self.water[y][x] and not self.blocked[y][x]:
                self.brush[y][x] = True

    def reserve(self, x0, y0, x1, y1):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if self.inside(x, y):
                    self.reserved[y][x] = True

    def prop(self, sprite, canvas, tx, ty, block=True, foot=(0, 0, 1, 1)):
        """Place a sprite whose base sits on the bottom of tile (tx, ty), centred
        on the footprint. `foot` is (dx, dy, w, h) in tiles relative to (tx, ty)."""
        fx, fy, fw, fh = foot
        cx = (tx + fx + fw / 2) * T
        base = (ty + 1) * T
        x = int(round(cx - canvas.w / 2))
        y = base - canvas.h
        self.props.append({'sprite': sprite, 'x': x, 'y': y, 'base_y': base})
        if block:
            for yy in range(ty + fy, ty + fy + fh):
                for xx in range(tx + fx, tx + fx + fw):
                    if self.inside(xx, yy):
                        self.blocked[yy][xx] = True

    # ---- export --------------------------------------------------------
    def render_ground(self):
        W, H = self.w * T, self.h * T
        c = world.ground(W, H, [], 0, [], seed=self.rng.randint(0, 999))
        rng = self.rng

        def mask_from(cells, r):
            centers = [((x + .5) * T, (y + .5) * T) for y in range(self.h) for x in range(self.w) if cells[y][x]]
            grid = {}
            for cx, cy in centers:
                grid.setdefault((int(cx // T), int(cy // T)), []).append((cx, cy))
            m = [[False] * W for _ in range(H)]
            for py in range(H):
                for px in range(W):
                    tx, ty = px // T, py // T
                    wob = math.sin(px * .23 + py * .11) * 1.3 + math.sin(py * .19 - px * .07)
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            for cx, cy in grid.get((tx + dx, ty + dy), ()):
                                if (px + .5 - cx) ** 2 + (py + .5 - cy) ** 2 <= (r + wob) ** 2:
                                    m[py][px] = True
                                    break
                            if m[py][px]:
                                break
                        if m[py][px]:
                            break
            return m

        def paint(m, base, edge, speck):
            for y in range(H):
                for x in range(W):
                    if not m[y][x]:
                        continue
                    e = any(not (0 <= y + dy < H and 0 <= x + dx < W and m[y + dy][x + dx])
                            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                    col = edge if e else base
                    if not e and rng.random() < .06:
                        col = speck
                    c.px[y][x] = hexc(col)

        paint(mask_from(self.path, 11.0), P.PATH_1, P.PATH_2, P.PATH_3)
        wm = mask_from(self.water, 10.5)
        paint(wm, P.WATER_1, P.WATER_2, P.WATER_3)
        for _ in range(W * H // 400):
            x, y = rng.randrange(W - 6), rng.randrange(H)
            if all(wm[y][x + i] for i in range(-2, 7) if 0 <= x + i < W):
                c.rect(x, y, 4, 1, P.WATER_3)
        # flattened grass under brush so tall grass reads as a patch
        for y in range(self.h):
            for x in range(self.w):
                if self.brush[y][x]:
                    for py in range(y * T, y * T + T):
                        for px in range(x * T, x * T + T):
                            if (px + py) % 3 == 0:
                                c.px[py][px] = hexc(P.GRASS_2)
        return c

    def export(self, out_dir):
        os.makedirs(out_dir, exist_ok=True)
        self.render_ground().image().save(os.path.join(out_dir, f'{self.name}_ground.png'))
        rows = lambda g: [''.join('1' if v else '0' for v in r) for r in g]
        data = {
            'name': self.name, 'w': self.w, 'h': self.h, 'tile': T,
            'ground': f'{self.name}_ground.png',
            'blocked': rows(self.blocked), 'brush': rows(self.brush),
            'props': sorted(self.props, key=lambda p: p['base_y']),
            'exits': self.exits, 'doors': self.doors, 'zones': self.zones,
            'start': self.start,
        }
        with open(os.path.join(out_dir, f'{self.name}.json'), 'w') as f:
            json.dump(data, f, separators=(',', ':'))
        return data


# Sprites used as props; build.py exports each under this name.
TREE_KINDS = ['oak', 'maple', 'birch', 'pine']
TREE_VARIANTS = 3
BUSH_KINDS = ['sumac', 'hazel', 'green', 'oak']


def prop_sprites():
    s = {}
    for k in TREE_KINDS:
        for v in range(TREE_VARIANTS):
            s[f'tree_{k}_{v}'] = world.tree(k, seed=v * 17 + len(k))
    for i, k in enumerate(BUSH_KINDS):
        s[f'bush_{k}'] = world.bush(k, seed=i + 3)
    s['rock'] = world.rock()
    s['stump'] = world.stump()
    s['log'] = world.log()
    s['tree_stand'] = world.tree_stand()
    s['cattails'] = world.cattails(seed=2)
    s['tall_grass'] = world.tall_grass(seed=4)
    for b in BUILDINGS:
        s['bld_' + b] = building(b)
    s['signpost'] = signpost()
    s['truck'] = truck()
    return s


def _forest_border(a, thickness=2, gaps=()):
    rng = a.rng
    for y in range(a.h):
        for x in range(a.w):
            edge = min(x, y, a.w - 1 - x, a.h - 1 - y)
            if edge < thickness and (x, y) not in gaps and not a.path[y][x]:
                a.blocked[y][x] = True
                if (x + y) % 2 == 0 or edge == 0:
                    k = rng.choice(TREE_KINDS + ['pine'])
                    a.prop(f'tree_{k}_{rng.randrange(TREE_VARIANTS)}', world.tree(k), x, y, block=True)


def _scatter(a, count, kinds, min_path_gap=2, block=True):
    rng = a.rng
    placed = 0
    tries = 0
    while placed < count and tries < count * 40:
        tries += 1
        x, y = rng.randrange(2, a.w - 2), rng.randrange(2, a.h - 2)
        if not a.free(x, y):
            continue
        near = False
        for dy in range(-min_path_gap, min_path_gap + 1):
            for dx in range(-min_path_gap, min_path_gap + 1):
                if a.inside(x + dx, y + dy) and (a.path[y + dy][x + dx] or a.water[y + dy][x + dx]):
                    near = True
        # keep trees from touching each other so there is always a way through
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if a.inside(x + dx, y + dy) and a.blocked[y + dy][x + dx]:
                    near = True
        if near:
            continue
        kind = rng.choice(kinds)
        if kind in TREE_KINDS:
            name = f'tree_{kind}_{rng.randrange(TREE_VARIANTS)}'
        elif kind in BUSH_KINDS:
            name = f'bush_{kind}'
        else:
            name = kind
        a.prop(name, _sprite_size(name), x, y, block=block)
        placed += 1


_SIZES = {}


def _sprite_size(name):
    if not _SIZES:
        for k, v in prop_sprites().items():
            _SIZES[k] = v
    return _SIZES[name]


# ------------------------------------------------------------------ town ----
BUILDINGS = {
    'trading_post': ('#7a3b2a', '#9a4a33', 'Trading Post'),
    'outfitter': ('#3d5a44', '#4f7357', 'Outfitter'),
    'warden': ('#3b4a63', '#4d5f7d', 'Game Warden'),
    'cabin': ('#5a4a3a', '#76624c', "Chris's Cabin"),
}


def building(kind):
    """80x60 log building. Footprint 5x3 tiles, door in the middle column."""
    roof, roof_lt, _ = BUILDINGS[kind]
    c = Canvas(80, 60)
    c.poly([(0, 26), (40, 4), (80, 26)], roof)
    c.poly([(5, 25), (40, 7), (75, 25)], roof_lt)
    for y in range(10, 26, 3):
        half = (y - 4) * 1.75
        c.line(40 - half, y, 40 + half, y, roof, 0.8)
    c.rect(4, 26, 72, 34, P.TRUNK)
    for y in range(26, 60, 4):
        c.rect(4, y + 3, 72, 1, P.TRUNK_SH)
        c.ellipse(4, y + 1.5, 1.6, 1.6, P.PATH_3)
        c.ellipse(75, y + 1.5, 1.6, 1.6, P.PATH_3)
    # door (tile column 2: x 32..48)
    c.rect(34, 42, 12, 18, '#4a2d1d')
    c.rect(35, 43, 10, 17, '#6b4128')
    c.set(43, 51, P.BIRCH_1)
    for wx in (10, 56):
        c.rect(wx, 36, 12, 9, '#f3cf6a')
        c.rect(wx + 5, 36, 2, 9, P.TRUNK_SH)
        c.rect(wx, 40, 12, 1, P.TRUNK_SH)
    # sign board with an icon for the shop
    c.rect(28, 27, 24, 12, P.PATH_3)
    c.rect(28, 38, 24, 1, P.PATH_2)
    ic = {'trading_post': _icon_pelt, 'outfitter': _icon_rifle,
          'warden': _icon_badge, 'cabin': _icon_house}[kind]
    ic(c, 40, 33)
    c.outline(P.OUTLINE)
    return c


def _icon_pelt(c, x, y):
    c.ellipse(x, y, 5, 3.4, P.DEER)
    for dx, dy in ((-5, -3), (5, -3), (-5, 3), (5, 3)):
        c.rect(x + dx - (1 if dx < 0 else 0), y + dy - (1 if dy < 0 else 0), 2, 2, P.DEER_SH)


def _icon_rifle(c, x, y):
    c.line(x - 8, y + 2, x + 8, y - 2, P.GUNMETAL, 1.4)
    c.line(x - 8, y + 2, x - 3, y + 1, P.STOCK, 2.4)
    c.rect(x, y - 3, 4, 1, P.GUNMETAL)


def _icon_badge(c, x, y):
    c.poly([(x, y - 5), (x + 2, y - 1), (x + 5, y - 1), (x + 2.5, y + 1.5), (x + 3.5, y + 5),
            (x, y + 3), (x - 3.5, y + 5), (x - 2.5, y + 1.5), (x - 5, y - 1), (x - 2, y - 1)], P.BIRCH_1)


def _icon_house(c, x, y):
    c.poly([(x - 5, y), (x, y - 5), (x + 5, y)], P.MAPLE_1)
    c.rect(x - 4, y, 8, 5, P.CREAM)


def signpost():
    c = Canvas(20, 22)
    c.rect(9, 8, 2, 14, P.TRUNK)
    c.poly([(2, 3), (15, 3), (19, 7), (15, 11), (2, 11)], P.PATH_3)
    c.rect(4, 6, 9, 1, P.TRUNK_SH)
    c.rect(4, 8, 7, 1, P.TRUNK_SH)
    c.outline(P.OUTLINE)
    return c


def truck():
    """Chris's pickup: the 'refill abilities' spot at the trailhead."""
    c = Canvas(44, 26)
    c.rect(2, 10, 40, 10, '#8b2f24')
    c.rect(2, 10, 40, 3, '#a8402f')
    c.poly([(22, 10), (26, 2), (38, 2), (40, 10)], '#8b2f24')
    c.poly([(27, 4), (37, 4), (38, 9), (25, 9)], '#9fc4d8')
    c.rect(2, 8, 18, 2, '#6d241c')
    for wx in (10, 33):
        c.ellipse(wx, 20, 4, 4, '#26201c')
        c.ellipse(wx, 20, 1.6, 1.6, STONE)
    c.rect(41, 13, 2, 3, '#f3cf6a')
    c.outline(P.OUTLINE)
    return c


STONE = P.STONE_3


def town():
    a = Area('town', 30, 18, seed=21)
    a.path_line([(0, 10), (29, 10)])
    a.exits.append({'x': 29, 'y': 10, 'to': 'hollow', 'tx': 1, 'ty': 15, 'face': 'right'})
    a.exits.append({'x': 29, 'y': 11, 'to': 'hollow', 'tx': 1, 'ty': 16, 'face': 'right'})
    spots = {'trading_post': (2, 4), 'outfitter': (8, 4), 'warden': (14, 4), 'cabin': (20, 4)}
    for kind, (bx, by) in spots.items():
        a.prop('bld_' + kind, building(kind), bx, by, foot=(0, -2, 5, 3))
        a.path_line([(bx + 2, by + 1), (bx + 2, 9)], width=1)
        a.doors.append({'x': bx + 2, 'y': by, 'id': kind, 'ax': bx + 2, 'ay': by + 1})
        a.reserve(bx - 1, by - 3, bx + 5, by + 1)
    a.prop('truck', truck(), 24, 13, foot=(0, 0, 3, 1))
    a.reserve(23, 12, 28, 14)
    a.prop('signpost', signpost(), 27, 8, foot=(0, 0, 1, 1))
    a.reserve(26, 6, 29, 9)
    gaps = {(29, 10), (29, 11)}
    _forest_border(a, 2, gaps)
    for x, y, k in [(8, 13, 'maple'), (14, 14, 'oak'), (4, 14, 'birch'), (17, 13, 'oak'),
                    (20, 15, 'maple'), (11, 15, 'pine')]:
        if a.free(x, y):
            a.prop(f'tree_{k}_{x % TREE_VARIANTS}', world.tree(k), x, y)
    for x, y, k in [(7, 7, 'sumac'), (13, 7, 'hazel'), (25, 6, 'oak'), (11, 13, 'green'), (6, 13, 'sumac')]:
        if a.free(x, y):
            a.prop('bush_' + k, world.bush(k), x, y)
    a.start = {'x': 22, 'y': 5, 'face': 'down'}   # on the cabin step
    return a


# ------------------------------------------------------------ the hollow --
def hollow():
    a = Area('hollow', 48, 32, seed=5)
    a.path_line([(0, 15), (8, 15), (14, 12), (22, 13), (29, 18), (37, 20), (40, 19)])
    a.exits.append({'x': 0, 'y': 15, 'to': 'town', 'tx': 28, 'ty': 10, 'face': 'left'})
    a.exits.append({'x': 0, 'y': 16, 'to': 'town', 'tx': 28, 'ty': 11, 'face': 'left'})
    a.pond(32.5, 7.5, 5.2, 3.2)
    for x, y in [(27, 6), (28, 9), (37, 6), (36, 9), (30, 4)]:
        if a.inside(x, y) and not a.water[y][x] and not a.blocked[y][x]:
            a.prop('cattails', world.cattails(), x, y, block=False)
    for cx, cy, rx, ry in [(12, 22, 4.5, 2.4), (24.5, 8.5, 3.2, 2.2), (20, 25.5, 5.5, 2.2),
                           (39, 12.5, 3.4, 2.2), (42.5, 26, 3.4, 2.8), (7, 6, 3, 2)]:
        a.brush_patch(cx, cy, rx, ry)
    # tree stand overlooking the field
    a.prop('tree_stand', world.tree_stand(), 41, 17)
    a.reserve(38, 16, 44, 22)
    # berry thicket in the north-east where the bear feeds
    for x, y in [(41, 4), (43, 5), (40, 7), (44, 8), (42, 9)]:
        a.prop('bush_green', world.bush('green'), x, y)
    a.reserve(38, 3, 45, 10)
    a.prop('log', world.log(), 15, 18, foot=(0, 0, 2, 1))
    for x, y in [(9, 26), (33, 14), (19, 5)]:
        if a.free(x, y):
            a.prop('rock', world.rock(), x, y)
    for x, y in [(27, 26), (13, 9)]:
        if a.free(x, y):
            a.prop('stump', world.stump(), x, y)
    # oak flat for turkeys: a loose grid of oaks
    for x, y in [(26, 22), (30, 23), (34, 22), (28, 27), (33, 27)]:
        if a.free(x, y):
            a.prop(f'tree_oak_{(x + y) % TREE_VARIANTS}', world.tree('oak'), x, y)
    a.reserve(25, 21, 35, 28)
    gaps = {(0, 15), (0, 16)}
    _forest_border(a, 2, gaps)
    _scatter(a, 70, ['oak', 'maple', 'birch', 'pine', 'maple', 'oak'])
    _scatter(a, 22, BUSH_KINDS)
    for y in range(a.h):
        for x in range(a.w):
            if a.brush[y][x]:
                a.prop('tall_grass', world.tall_grass(), x, y, block=False)
    a.zones = {
        'cottontail': [[9, 20, 15, 24], [16, 24, 25, 27], [5, 5, 9, 7]],
        'wild_turkey': [[25, 21, 35, 28]],
        'whitetail_doe': [[14, 4, 24, 10], [36, 22, 45, 28]],
        'red_fox': [[4, 4, 12, 10], [9, 18, 16, 25]],
        'whitetail_buck': [[36, 10, 45, 16]],
        'black_bear': [[38, 3, 45, 10]],
    }
    a.start = {'x': 1, 'y': 15, 'face': 'right'}
    return a


def check(a):
    """Every zone, exit and door approach must be reachable from the start."""
    from collections import deque
    sx, sy = a.start['x'], a.start['y']
    seen = {(sx, sy)}
    q = deque([(sx, sy)])
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if a.inside(nx, ny) and (nx, ny) not in seen and not a.blocked[ny][nx]:
                seen.add((nx, ny))
                q.append((nx, ny))
    problems = []
    for e in a.exits:
        if (e['x'], e['y']) not in seen:
            problems.append(f"{a.name}: exit {e} unreachable")
    for d in a.doors:
        if (d['ax'], d['ay']) not in seen:
            problems.append(f"{a.name}: door {d['id']} approach unreachable")
    for sp, rects in a.zones.items():
        cells = [(x, y) for x0, y0, x1, y1 in rects for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]
        ok = [c for c in cells if c in seen]
        if len(ok) < 3:
            problems.append(f"{a.name}: zone {sp} has only {len(ok)} reachable tiles")
    return problems
