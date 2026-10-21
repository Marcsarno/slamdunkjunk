"""v2 proof scene: one 480x270 screen of Maple Hollow."""
import math
import random
import sys

import numpy as np

from px import Px, ramp, value_noise, band, falling_leaf, hx
import flora

W, H = 480, 270


def seg_dist(px_, py_, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = np.clip(((px_ - ax) * dx + (py_ - ay) * dy) / L, 0, 1)
    return np.hypot(px_ - (ax + t * dx), py_ - (ay + t * dy))


def ground(seed=3):
    """Flat mid-green with gentle broad variation, then small grass marks laid
    on a jittered grid. Texture comes from marks, not from noise."""
    rng = random.Random(seed)
    p = Px(W, H)
    big = value_noise(W, H, 110, seed + 1, octaves=2)
    idx = band(big, [0.38, 0.64], dither=0.02) + 2       # ramp 2..4, broad areas only
    for i in (2, 3, 4):
        p.a[idx == i] = ramp('grass', i)
    for gy in range(0, H, 5):
        for gx in range(0, W, 6):
            x = gx + rng.randint(0, 3) + (3 if (gy // 5) % 2 else 0)
            y = gy + rng.randint(0, 2)
            if not (0 <= x < W - 2 and 1 <= y < H):
                continue
            base = int(idx[y, x])
            if rng.random() < 0.45:
                continue
            dark = ramp('grass', max(1, base - 1))
            lite = ramp('grass', min(5, base + 1))
            p.set(x, y, dark)
            p.set(x + 2, y, dark)
            p.set(x + 1, y - 1, lite)
    return p


def path_mask(pts, width, seed):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32) + 0.5
    d = np.full((H, W), 1e9, dtype=np.float32)
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        d = np.minimum(d, seg_dist(xx, yy, ax, ay, bx, by))
    wob = (value_noise(W, H, 10, seed) - 0.5) * 5
    return d < width / 2 + wob


def paint_path(p, mask, seed):
    rng = random.Random(seed)
    n = value_noise(W, H, 22, seed + 5)
    idx = band(n, [0.3, 0.7], dither=0.015) + 2   # ramp 2..4, mostly 3
    for i in (2, 3, 4):
        p.a[mask & (idx == i)] = ramp('path', i)
    up = np.zeros_like(mask)
    up[1:] = mask[1:] & ~mask[:-1]                 # top edge: grass shades the dip
    up2 = np.zeros_like(mask)
    up2[2:] = mask[2:] & ~mask[:-2] & ~up[2:]
    down = np.zeros_like(mask)
    down[:-1] = mask[:-1] & ~mask[1:]
    p.a[up] = ramp('path', 1)
    p.a[up2] = ramp('path', 2)
    p.a[down] = ramp('path', 5)
    ys, xs = np.nonzero(mask & ~up & ~up2 & ~down)
    for _ in range(len(xs) // 90):
        k = rng.randrange(len(xs))
        x, y = xs[k], ys[k]
        p.set(x, y, ramp('path', 5))
        p.set(x, y + 1, ramp('path', 2))


def pond(p, cx, cy, rx, ry, seed):
    rng = random.Random(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32) + 0.5
    ang = np.arctan2(yy - cy, xx - cx)
    wob = 1 + 0.07 * np.sin(ang * 3 + 1) + 0.05 * np.sin(ang * 7)
    d = np.hypot((xx - cx) / rx, (yy - cy) / ry) / wob
    shore = d < 1.0
    water = d < 0.93
    p.a[shore & ~water] = ramp('path', 1)
    depth = np.clip(1 - d, 0, 1)
    idx = band(1 - depth * 1.6 + (yy - cy) / ry * 0.15, [0.25, 0.55, 0.8])  # 0 deep .. 3 shallow
    cols = [ramp('water', 1), ramp('water', 2), ramp('water', 3), ramp('water', 4)]
    for i in range(4):
        p.a[water & (idx == i)] = cols[i]
    # bank shadow along the top of the water
    top = water & (yy < cy - ry * 0.55) & (d > 0.74)
    p.a[top] = ramp('water', 1)
    # reflected sky glints
    for _ in range(22):
        x = rng.uniform(cx - rx * 0.6, cx + rx * 0.6)
        y = rng.uniform(cy - ry * 0.3, cy + ry * 0.6)
        if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 < 0.55:
            L = rng.randint(2, 6)
            for k in range(L):
                p.set(x + k, y, ramp('water', 5 if k else 4))
    return shore


def scatter_leaves(p, cx, base, radius, ramp_name, rng, count):
    for _ in range(count):
        a = rng.uniform(0, math.tau)
        d = radius * math.sqrt(rng.random())
        x = cx + math.cos(a) * d * 1.3
        y = base + math.sin(a) * d * 0.55
        falling_leaf(p, x, y, ramp_name, rng)


def cast_shadow(p, cx, base, rx, ry, dx=7):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32) + 0.5
    m = ((xx - (cx + dx)) / rx) ** 2 + ((yy - (base - 1)) / ry) ** 2 <= 1
    p.darken(m)


def grade(p):
    a = p.a[:, :, :3].astype(np.float32)
    # warm late-afternoon light, cooler shadows
    lum = a.mean(axis=2, keepdims=True) / 255
    warm = np.array([1.06, 1.0, 0.9])
    cool = np.array([0.94, 0.97, 1.06])
    a = a * (warm * lum + cool * (1 - lum))
    yy, xx = np.mgrid[0:H, 0:W]
    vig = 1 - 0.22 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.5
    a = a * np.clip(vig, 0.6, 1)[:, :, None]
    # soft light shafts from the top-left
    shaft = np.zeros((H, W))
    for off in (80, 190, 260):
        d = np.abs((xx - yy * 0.9) - off)
        shaft += np.clip(1 - d / 34, 0, 1) ** 2 * 0.045 * (1 - yy / H)
    a = a + shaft[:, :, None] * np.array([255, 220, 150])
    p.a[:, :, :3] = np.clip(a, 0, 255).astype(np.uint8)


def compose(chars=None, seed=3):
    rng = random.Random(seed)
    p = ground(seed)
    pm = path_mask([(-10, 150), (90, 168), (190, 150), (300, 190), (420, 214), (500, 222)], 24, seed)
    paint_path(p, pm, seed)
    shore = pond(p, 382, 64, 66, 34, seed)

    props = []   # (base_y, x, y, sprite)
    trees = [('oak', 34, 112, 1), ('maple', 98, 92, 2), ('pine', 156, 84, 4), ('birch', 204, 108, 3),
             ('maple', 238, 248, 5), ('oak', 60, 244, 6), ('pine', 14, 210, 7), ('birch', 150, 240, 8),
             ('oak', 466, 158, 9), ('pine', 300, 100, 10), ('maple', 446, 246, 11)]
    # dense tree lines framing the clearing, top and bottom
    for i in range(16):
        x = -10 + i * 33 + rng.randint(-6, 6)
        trees.append((rng.choice(['oak', 'maple', 'pine', 'pine', 'birch']), x, 40 + rng.randint(-8, 8), 40 + i))
    for i in range(16):
        x = -14 + i * 32 + rng.randint(-6, 6)
        trees.append((rng.choice(['oak', 'maple', 'pine', 'oak', 'birch']), x, 286 + rng.randint(-4, 6), 70 + i))
    blocked = pm | shore
    for kind, x, base, s in trees:
        spr, sh = flora.pine(s) if kind == 'pine' else flora.broadleaf(kind, s)
        ox = int(x - spr.w / 2)
        oy = int(base - spr.h + 2)
        cast_shadow(p, x, base, sh[2], sh[3] + 2)
        if kind != 'pine':
            scatter_leaves(p, x, base, sh[2] * 1.1, {'oak': 'orange', 'maple': 'red', 'birch': 'gold'}[kind], rng, 45)
        props.append((base, ox, oy, spr))
    for name, x, base, s in [('red', 230, 120, 1), ('gold', 424, 196, 2), ('orange', 120, 196, 3), ('red', 420, 112, 4)]:
        spr, sh = flora.bush(name, s)
        cast_shadow(p, x, base, sh[2], sh[3], dx=4)
        props.append((base, int(x - spr.w / 2), base - spr.h + 2, spr))
    spr, sh = flora.rock(2)
    cast_shadow(p, 258, 214, 8, 3, dx=3)
    props.append((214, 250, 204, spr))
    for x, y in [(318, 70), (326, 84), (440, 92), (448, 40)]:
        r = flora.reeds(rng)
        props.append((y + 20, x, y, r))
    # tufts: sparse, never on the path or water
    for _ in range(140):
        x, y = rng.randrange(W - 6), rng.randrange(8, H - 5)
        if blocked[min(H - 1, y + 4), x] or blocked[y, x]:
            continue
        p.blit(flora.tuft(rng), x, y)
    for c in chars or []:
        base, x, y, spr = c
        cast_shadow(p, x + spr.w / 2 - 2, base, spr.w * 0.32, 2.6, dx=2)
        props.append(c)
    for base, x, y, spr in sorted(props, key=lambda t: t[0]):
        p.blit(spr, x, y)
    # falling leaves in the air
    for _ in range(14):
        falling_leaf(p, rng.randrange(W), rng.randrange(H), rng.choice(['orange', 'red', 'gold']), rng)
    grade(p)
    return p


def with_characters(frame=0):
    import chris
    import buck
    c = chris.walk('right')[frame]
    b = buck.deer(frame, 1)
    chars = [(166, 112, 166 - c.h + 1, c), (150, 318, 150 - b.h + 2, b)]
    return compose(chars)


if __name__ == '__main__':
    sys.path.insert(0, '..')
    with_characters().image(2).save(sys.argv[1])
