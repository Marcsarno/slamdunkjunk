"""v2 pixel toolkit: numpy canvas, hue-shifted ramps, lit clumps, dithering.

Rules this follows (the things v1 got wrong):
  * shadows shift toward purple/blue, highlights toward warm yellow
  * no single-pixel noise on big surfaces; texture comes in clusters
  * one light direction (top-left) for everything, plus cast shadows
  * outlines on characters only; world props use their own dark ramp
"""
import math
import random

import numpy as np
from PIL import Image


def hx(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)] + [255], dtype=np.uint8)


# Ramps run dark -> light.
RAMP = {
    'grass': ['#2a3628', '#3b4a2e', '#556535', '#6e7b3e', '#8e9149', '#b4aa5e'],
    'orange': ['#3d1d24', '#6e2b27', '#a5432a', '#d26a2f', '#ec9a45', '#f7cc72'],
    'red': ['#2e1424', '#561c2b', '#8b2a2e', '#be3f33', '#e06a45', '#f39c64'],
    'gold': ['#3e2a1e', '#6e4c22', '#a5782a', '#d3a838', '#efcf5a', '#fbeaa0'],
    'pine': ['#14211f', '#1e3230', '#2b4a3e', '#3c654a', '#5a8458', '#86a66a'],
    'bark': ['#1c1418', '#33241f', '#4f362a', '#6d4c37', '#8f6a4b'],
    'birch': ['#2a2326', '#7d7570', '#b8b0a2', '#ddd5c4', '#f4eedf'],
    'path': ['#4a3a33', '#6e5544', '#937356', '#b5946c', '#d2b78c', '#e6d3ab'],
    'water': ['#1b2638', '#233a52', '#2c5468', '#3a7380', '#5b9a9b', '#a6d0c4'],
    'stone': ['#2c2a33', '#4b4850', '#6d6a6c', '#918c85', '#b8b1a2'],
}
OUT = '#1d1519'


def ramp(name, i):
    r = RAMP[name]
    return hx(r[max(0, min(len(r) - 1, i))])


BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0


class Px:
    def __init__(self, w, h, fill=None):
        self.w, self.h = w, h
        self.a = np.zeros((h, w, 4), dtype=np.uint8)
        if fill is not None:
            self.a[:, :] = hx(fill) if isinstance(fill, str) else fill

    def set(self, x, y, c):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            self.a[y, x] = hx(c) if isinstance(c, str) else c

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.a[y, x]
        return None

    def blit(self, other, ox, oy):
        ox, oy = int(ox), int(oy)
        x0, y0 = max(0, ox), max(0, oy)
        x1, y1 = min(self.w, ox + other.w), min(self.h, oy + other.h)
        if x0 >= x1 or y0 >= y1:
            return
        src = other.a[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
        m = src[:, :, 3] > 0
        dst = self.a[y0:y1, x0:x1]
        dst[m] = src[m]

    def darken(self, mask, amount=0.72, tint=(0.92, 0.95, 1.12)):
        """Multiply-darken where mask is True, nudged toward blue (cast shadow)."""
        sub = self.a[:, :, :3].astype(np.float32)
        f = np.array(tint, dtype=np.float32) * amount
        sub[mask] = np.clip(sub[mask] * f, 0, 255)
        self.a[:, :, :3] = sub.astype(np.uint8)

    def ascii(self, rows, pal, ox=0, oy=0, flip=False):
        for j, row in enumerate(rows):
            if flip:
                row = row[::-1]
            for i, ch in enumerate(row):
                if ch in '. ':
                    continue
                self.set(ox + i, oy + j, pal[ch])

    def outline(self, color=OUT):
        alpha = self.a[:, :, 3] > 0
        grown = alpha.copy()
        grown[1:] |= alpha[:-1]
        grown[:-1] |= alpha[1:]
        grown[:, 1:] |= alpha[:, :-1]
        grown[:, :-1] |= alpha[:, 1:]
        edge = grown & ~alpha
        self.a[edge] = hx(color)

    def flipped(self):
        p = Px(self.w, self.h)
        p.a = self.a[:, ::-1].copy()
        return p

    def image(self, scale=1):
        im = Image.fromarray(self.a, 'RGBA')
        if scale != 1:
            im = im.resize((self.w * scale, self.h * scale), Image.NEAREST)
        return im


def value_noise(w, h, cell, seed, octaves=3):
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), dtype=np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        c = max(2, cell >> o)
        gw, gh = w // c + 3, h // c + 3
        g = rng.random((gh, gw)).astype(np.float32)
        ys = np.arange(h) / c
        xs = np.arange(w) / c
        y0 = ys.astype(int)
        x0 = xs.astype(int)
        fy = (ys - y0)[:, None]
        fx = (xs - x0)[None, :]
        fy = fy * fy * (3 - 2 * fy)
        fx = fx * fx * (3 - 2 * fx)
        a = g[y0][:, x0]
        b = g[y0][:, x0 + 1]
        cc = g[y0 + 1][:, x0]
        d = g[y0 + 1][:, x0 + 1]
        out += amp * ((a * (1 - fx) + b * fx) * (1 - fy) + (cc * (1 - fx) + d * fx) * fy)
        total += amp
        amp *= 0.5
    return out / total


def band(values, edges, dither=0.035):
    """Quantize a 0..1 field into len(edges)+1 bands with ordered dithering
    only right at the boundaries (no noise inside flat areas)."""
    h, w = values.shape
    bay = np.tile(BAYER4, (h // 4 + 1, w // 4 + 1))[:h, :w]
    v = values + (bay - 0.5) * dither * 2
    out = np.zeros_like(values, dtype=np.int32)
    for e in edges:
        out += (v > e)
    return out


# ------------------------------------------------------------- foliage ----
LIGHT = (-0.62, -0.78)


def clump_canopy(p, cx, cy, rx, ry, ramp_name, seed, n=None, jag=0.22, base_shift=0):
    """Canopy built from many lit leaf clumps, back to front.

    Each clump is shaded on its own (top-left lit), and the whole canopy darkens
    toward the bottom, so it reads as a volume made of leaves rather than a blob.
    Returns a boolean mask of canopy pixels.
    """
    rng = random.Random(seed)
    n = n or int((rx * ry) / 14)
    clumps = []
    for _ in range(n):
        a = rng.uniform(0, math.tau)
        d = math.sqrt(rng.random())
        x = cx + math.cos(a) * rx * 0.78 * d
        y = cy + math.sin(a) * ry * 0.74 * d
        r = rng.uniform(4.2, 6.8)
        clumps.append((y, x, r, rng.random() * 10))
    clumps.sort()
    mask = np.zeros((p.h, p.w), dtype=bool)
    L = len(RAMP[ramp_name])
    for y, x, r, ph in clumps:
        for yy in range(int(y - r - 2), int(y + r + 2)):
            for xx in range(int(x - r - 2), int(x + r + 2)):
                if not (0 <= xx < p.w and 0 <= yy < p.h):
                    continue
                dx, dy = xx + 0.5 - x, yy + 0.5 - y
                ang = math.atan2(dy, dx)
                rr = r * (1 + jag * math.sin(ang * 5 + ph) * 0.5 + jag * 0.35 * math.sin(ang * 9 + ph * 2))
                dist = math.hypot(dx, dy)
                if dist > rr:
                    continue
                nx, ny = dx / rr, dy / rr
                local = nx * LIGHT[0] + ny * LIGHT[1]          # this clump's own lighting
                gx, gy = (xx + 0.5 - cx) / rx, (yy + 0.5 - cy) / ry
                glob = gx * LIGHT[0] + gy * LIGHT[1]           # the canopy as one volume
                v = 0.5 + glob * 0.42 + local * 0.16
                if dist > rr - 1.2 and glob < 0.15:
                    v -= 0.16                                     # crevices only on the shadow side
                idx = int(round(v * (L - 1))) + base_shift
                idx = max(0, min(L - 1, idx))
                p.a[yy, xx] = ramp(ramp_name, idx)
                mask[yy, xx] = True
    # silhouette: darkest ramp along the bottom/right edge, mid along the top/left
    edge_dark = ramp(ramp_name, 0)
    for yy in range(p.h):
        for xx in range(p.w):
            if not mask[yy, xx]:
                continue
            below = yy + 1 >= p.h or not mask[yy + 1, xx]
            right = xx + 1 >= p.w or not mask[yy, xx + 1]
            if below or (right and yy > cy - ry * 0.3):
                p.a[yy, xx] = edge_dark if yy > cy else ramp(ramp_name, 1)
    return mask


def falling_leaf(p, x, y, ramp_name, rng):
    c1 = ramp(ramp_name, 4)
    c2 = ramp(ramp_name, 2)
    if rng.random() < 0.5:
        p.set(x, y, c1)
        p.set(x + 1, y, c2)
    else:
        p.set(x, y, c1)
        p.set(x, y + 1, c2)
