"""v2 trees, bushes and ground details."""
import math
import random

import numpy as np

from px import Px, ramp, clump_canopy, RAMP


def broadleaf(kind, seed=0, w=56, h=72):
    """Oak / maple / birch. Trunk first, then clump canopy, then branch hints."""
    rng = random.Random(seed)
    p = Px(w, h)
    leaf = {'oak': 'orange', 'maple': 'red', 'birch': 'gold'}[kind]
    cx = w / 2
    base = h - 2
    # trunk
    if kind == 'birch':
        tw = 4
        for y in range(30, base + 1):
            for x in range(int(cx - tw / 2), int(cx + tw / 2)):
                i = 3 if x < cx - 0.5 else 2
                if x == int(cx + tw / 2) - 1:
                    i = 1
                p.set(x, y, ramp('birch', i))
        for y in range(34, base, 3):
            x = int(cx - 2 + rng.randint(0, 2))
            p.set(x, y, ramp('birch', 0))
            p.set(x + 1, y, ramp('birch', 0))
    else:
        for y in range(36, base + 1):
            spread = 0 if y < base - 4 else (base - 4 - y) * -0.8   # root flare
            x0 = cx - 4 - spread
            x1 = cx + 4 + spread
            for x in range(int(x0), int(math.ceil(x1))):
                t = (x - x0) / max(1, (x1 - x0))
                i = 3 if t < 0.3 else (2 if t < 0.7 else 1)
                if (y * 7 + x * 3) % 11 == 0:
                    i = max(0, i - 1)                                     # bark grooves
                p.set(x, y, ramp('bark', i))
        # a branch reaching into the canopy
        for k in range(8):
            p.set(int(cx + 3 + k * 0.9), int(30 - k * 0.8), ramp('bark', 2))
            p.set(int(cx - 3 - k * 0.8), int(31 - k * 0.7), ramp('bark', 2))
    ry = 23 if kind != 'birch' else 20
    rx = 26 if kind == 'oak' else (23 if kind == 'maple' else 17)
    clump_canopy(p, cx, 29, rx, ry, leaf, seed * 31 + 7)
    # a few dark gaps where you can see into the tree, with trunk behind
    for _ in range(3):
        gx = int(cx + rng.uniform(-rx * 0.4, rx * 0.4))
        gy = int(27 + rng.uniform(2, ry * 0.5))
        p.set(gx, gy, ramp(leaf, 0))
        p.set(gx + 1, gy, ramp(leaf, 0))
    return p, (cx, base, rx * 0.9, 7)


def pine(seed=0, w=40, h=76):
    rng = random.Random(seed)
    p = Px(w, h)
    cx = w / 2
    base = h - 2
    for y in range(base - 10, base + 1):
        for x in range(int(cx - 2), int(cx + 2)):
            p.set(x, y, ramp('bark', 2 if x < cx else 1))
    tiers = 6
    for t in range(tiers):
        top = 4 + t * 10
        bot = top + 17
        half = 6 + t * 2.6
        for y in range(top, min(bot, base - 6)):
            f = (y - top) / (bot - top)
            hw = half * f + 1
            for x in range(int(cx - hw - 1), int(cx + hw + 2)):
                dx = (x + 0.5 - cx) / max(1, hw)
                if abs(dx) > 1:
                    continue
                # drooping, saw-toothed lower edge
                if y > bot - 4 and ((x + t) % 3 == 0) and f > 0.85:
                    continue
                lam = -dx * 0.7 + (0.4 - f) * 0.8
                i = 2 + int(round(lam * 1.6))
                if y >= bot - 2:
                    i -= 1
                p.set(x, y, ramp('pine', max(0, min(5, i))))
    return p, (cx, base, 13, 5)


def bush(ramp_name, seed=0):
    p = Px(26, 18)
    clump_canopy(p, 13, 10, 12, 7.5, ramp_name, seed, n=12)
    return p, (13, 16, 11, 3)


def tuft(rng, ramp_name='grass'):
    """3-5 blade grass tuft, 5x4."""
    p = Px(6, 5)
    for i, x in enumerate((1, 2, 3, 4)):
        hgt = rng.randint(2, 4)
        for k in range(hgt):
            c = ramp(ramp_name, 4 if k == hgt - 1 else 3)
            p.set(x + (1 if k == hgt - 1 and x > 2 else 0) - (1 if k == hgt - 1 and x < 2 else 0), 4 - k, c)
    return p


def reeds(rng):
    p = Px(12, 20)
    for i in range(5):
        x = 1 + i * 2 + rng.randint(0, 1)
        hgt = rng.randint(10, 17)
        for k in range(hgt):
            p.set(x + (1 if k > hgt * 0.7 and i % 2 else 0), 19 - k, ramp('grass', 3 if k < hgt - 2 else 4))
        if i % 2 == 0:
            for k in range(3):
                p.set(x, 19 - hgt + k - 1, ramp('bark', 2 + (k == 0)))
    return p


def rock(seed=0):
    p = Px(16, 11)
    rng = random.Random(seed)
    for y in range(11):
        for x in range(16):
            nx, ny = (x + 0.5 - 8) / 7.5, (y + 0.5 - 7) / 5
            if nx * nx + ny * ny <= 1 and y >= 1:
                lam = nx * -0.6 + ny * -0.8
                i = 2 + int(round(lam * 1.5))
                p.set(x, y, ramp('stone', max(0, min(4, i))))
    # moss on top
    for x in range(4, 10):
        if rng.random() < 0.7:
            p.set(x, 2 + rng.randint(0, 1), ramp('grass', 3))
    return p, (8, 10, 8, 2.5)
