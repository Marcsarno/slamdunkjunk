"""Whitetail, v2: drawn from anatomy, not ovals.

Unit coordinates (ground at y=29, facing left, ~32 units long). Scale s=1 is
the overworld sprite; s=3 is the battle sprite. Each part is shaded as its
own volume lit from the top-left, then the whole thing gets a selective
outline. Legs bend at real joints (the hind leg's hock points backward).
"""
import math

import numpy as np

from px import Px, hx, OUT
from raster import _inside

DEER = ['#3a2219', '#5a3523', '#7f4e30', '#a46a40', '#c28855', '#d9a875']
GHOST = ['#8c8792', '#aea9ad', '#cbc6c3', '#e2ddd6', '#f2eee7', '#ffffff']
WHITE = '#efe7d8'
WHITE_SH = '#c9bda8'
ANT = ['#7d6a4e', '#b39f78', '#ddcca2', '#f0e4c0']
HOOF = '#231a17'
LIGHT = np.array([-0.62, -0.78])

# frame -> {leg: (swing, lift)}; negative swing = reaching forward (left)
GAIT = [
    {'FL': (-2.2, 0), 'BR': (-2.2, 0), 'FR': (2.0, 0), 'BL': (2.0, 0)},
    {'FL': (0, 0), 'BR': (0, 0), 'FR': (-0.6, 1.6), 'BL': (-0.6, 1.6)},
    {'FL': (2.0, 0), 'BR': (2.0, 0), 'FR': (-2.2, 0), 'BL': (-2.2, 0)},
    {'FL': (-0.6, 1.6), 'BR': (-0.6, 1.6), 'FR': (0, 0), 'BL': (0, 0)},
]


class Draw:
    def __init__(self, s, pad_top=10, pal=DEER):
        self.s = s
        self.pal = pal
        self.ox, self.oy = 2 * s, pad_top * s
        self.p = Px(int(36 * s) + 4, int((29 + pad_top) * s) + 4)
        self.tags = np.zeros((self.p.h, self.p.w), dtype=object)

    def P(self, x, y):
        return self.ox + x * self.s, self.oy + y * self.s

    def shade(self, nx, ny, bias=0.0, x=0, y=0):
        lam = nx * LIGHT[0] + ny * LIGHT[1]            # top-left lit
        v = 0.55 + lam * 0.45 + bias
        if self.s >= 2:                                # ordered dither softens bands at battle size
            from px import BAYER4
            v += (BAYER4[y % 4, x % 4] - 0.5) * 0.16
        i = int(round(v * (len(self.pal) - 1)))
        return self.pal[max(0, min(len(self.pal) - 1, i))]

    def volume(self, pts, center, radii, bias=0.0, tag=None):
        """Fill a polygon, shading each pixel as if on an ellipsoid."""
        P = [self.P(x, y) for x, y in pts]
        cx, cy = self.P(*center)
        rx, ry = radii[0] * self.s, radii[1] * self.s
        xs = [q[0] for q in P]
        ys = [q[1] for q in P]
        for y in range(int(min(ys)) - 1, int(max(ys)) + 2):
            for x in range(int(min(xs)) - 1, int(max(xs)) + 2):
                if _inside(x + 0.5, y + 0.5, P):
                    nx = (x + 0.5 - cx) / rx
                    ny = (y + 0.5 - cy) / ry
                    self.p.set(x, y, self.shade(nx, ny, bias, x, y))
                    if tag:
                        self._tag(x, y, tag)

    def ellipse(self, c, r, bias=0.0, tag=None):
        cx, cy = self.P(*c)
        rx, ry = r[0] * self.s, r[1] * self.s
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                nx, ny = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
                if nx * nx + ny * ny <= 1:
                    self.p.set(x, y, self.shade(nx, ny, bias, x, y))
                    if tag:
                        self._tag(x, y, tag)

    def limb(self, a, b, w0, w1, bias=0.0, tag=None, col=None):
        """Tapered limb segment, lit on its left edge."""
        ax, ay = self.P(*a)
        bx, by = self.P(*b)
        w0, w1 = w0 * self.s, w1 * self.s
        L = math.hypot(bx - ax, by - ay) or 1
        ux, uy = (bx - ax) / L, (by - ay) / L
        for y in range(int(min(ay, by) - w0) - 1, int(max(ay, by) + w0) + 2):
            for x in range(int(min(ax, bx) - w0) - 1, int(max(ax, bx) + w0) + 2):
                px_, py_ = x + 0.5 - ax, y + 0.5 - ay
                t = max(0.0, min(1.0, (px_ * ux + py_ * uy) / L))
                qx, qy = ax + ux * t * L, ay + uy * t * L
                d = math.hypot(x + 0.5 - qx, y + 0.5 - qy)
                hw = (w0 + (w1 - w0) * t) / 2
                if d <= hw:
                    side = ((x + 0.5 - qx) * -uy + (y + 0.5 - qy) * ux) / max(hw, 0.5)
                    c = col or self.shade(side * 0.9, 0.1, bias, x, y)
                    self.p.set(x, y, c)
                    if tag:
                        self._tag(x, y, tag)

    def _tag(self, x, y, tag):
        if 0 <= x < self.p.w and 0 <= y < self.p.h:
            self.tags[y, x] = tag

    def px(self, x, y, c, size=1.0):
        X, Y = self.P(x, y)
        n = max(1, int(round(size * self.s)))
        for j in range(n):
            for i in range(n):
                self.p.set(X + i, Y + j, c)

    def line(self, a, b, w, c):
        self.limb(a, b, w, w, col=c)


def _front_leg(d, shoulder, swing, lift, near, tag):
    bias = 0.0 if near else -0.28
    sx, sy = shoulder
    elbow = (sx + swing * 0.15, sy + 4.2)
    knee = (sx + swing * 0.55 - lift * 0.5, sy + 8.4 - lift * 0.7)
    fet = (sx + swing - lift * 0.2, 27.6 - lift)
    hoof = (fet[0] - 0.4, 28.9 - lift)
    d.limb((sx, sy), elbow, 3.4, 2.6, bias, tag)
    d.limb(elbow, knee, 2.4, 1.9, bias, tag)
    d.limb(knee, fet, 1.6, 1.5, bias, tag)
    d.limb(fet, hoof, 1.6, 1.6, tag=tag, col=HOOF)


def _hind_leg(d, hip, swing, lift, near, tag):
    bias = 0.0 if near else -0.28
    hx_, hy = hip
    stifle = (hx_ - 1.2 + swing * 0.2, hy + 6.0)
    hock = (hx_ + 1.4 + swing * 0.5, hy + 10.4 - lift * 0.6)
    fet = (hx_ + 0.6 + swing, 27.6 - lift)
    hoof = (fet[0] - 0.4, 28.9 - lift)
    d.limb((hx_, hy), stifle, 4.6, 3.0, bias, tag)
    d.limb(stifle, hock, 2.6, 1.8, bias, tag)
    d.limb(hock, fet, 1.6, 1.5, bias, tag)
    d.limb(fet, hoof, 1.6, 1.6, tag=tag, col=HOOF)


def deer(frame=0, s=1, antlers=True, ghost=False):
    d = Draw(s, pal=GHOST if ghost else DEER)
    g = GAIT[frame]
    bob = -0.4 if frame in (1, 3) else 0.0
    sh = (12.6, 14.6 + bob)
    hip = (26.6, 13.6 + bob)
    # far legs first, darker
    _front_leg(d, (sh[0] + 0.8, sh[1]), g['FR'][0], g['FR'][1], False, 'FR')
    _hind_leg(d, (hip[0] + 0.8, hip[1]), g['BR'][0], g['BR'][1], False, 'BR')
    # torso
    body = [(10.2, 12.0), (13.5, 9.6 + bob), (19, 10.2 + bob), (24.5, 10.0 + bob), (29.2, 9.8 + bob),
            (31.4, 11.6 + bob), (31.0, 15.0 + bob), (29.4, 18.2 + bob), (25.5, 19.4 + bob),
            (19.5, 18.8 + bob), (14.5, 19.6 + bob), (11.0, 18.4 + bob), (9.4, 15.4 + bob)]
    d.volume(body, (20, 13.4 + bob), (12, 6.2), tag='body')
    d.ellipse((27.0, 13.4 + bob), (4.4, 5.4), bias=0.05)                 # haunch
    d.ellipse((13.2, 13.8 + bob), (3.6, 4.4), bias=0.05)                 # shoulder
    # white belly line and tail
    d.line((14, 19.0 + bob), (25.5, 19.0 + bob), 0.9, WHITE_SH)
    d.limb((31.2, 10.9 + bob), (33.4, 13.6 + bob), 2.2, 1.6, col=WHITE)
    d.line((31.6, 10.4 + bob), (33.0, 12.4 + bob), 0.8, d.pal[2])
    # neck
    neck = [(13.8, 10.2 + bob), (11.2, 5.0 + bob), (8.2, 4.4 + bob), (7.2, 6.8 + bob),
            (8.6, 12.0 + bob), (9.6, 16.0 + bob)]
    d.volume(neck, (10.6, 9.0 + bob), (3.4, 6.4), bias=0.04)
    d.limb((8.8, 8.6 + bob), (9.6, 12.0 + bob), 1.6, 1.2, col=WHITE)    # throat patch
    # head
    head = [(9.8, 3.2 + bob), (7.2, 2.6 + bob), (4.4, 3.8 + bob), (1.4, 5.9 + bob), (1.0, 7.4 + bob),
            (3.0, 8.3 + bob), (6.2, 7.7 + bob), (9.0, 6.9 + bob), (10.2, 5.0 + bob)]
    d.volume(head, (6.4, 4.8 + bob), (4.6, 3.0), bias=0.06)
    d.line((2.4, 7.7 + bob), (4.6, 7.8 + bob), 0.9, WHITE)              # muzzle band
    d.px(0.9, 6.1 + bob, HOOF, 1.1)                                     # nose
    d.px(5.6, 4.6 + bob, '#d0453a' if ghost else HOOF, 1.0)             # eye
    d.px(5.2, 4.2 + bob, WHITE, 0.6)                                    # eye ring
    ear = [(8.6, 3.0 + bob), (11.6, 0.6 + bob), (12.8, 1.4 + bob), (10.4, 4.2 + bob)]
    d.volume(ear, (10.6, 2.2 + bob), (2.0, 1.6), bias=0.1)
    d.line((9.8, 2.6 + bob), (11.6, 1.4 + bob), 0.7, d.pal[1])
    if antlers:
        y = 2.4 + bob
        far = ANT[0]
        # far beam peeks out behind, darker
        for a, b in [((8.8, y), (10.0, y - 3.0)), ((10.0, y - 3.0), (8.8, y - 5.8)),
                     ((8.8, y - 5.8), (6.0, y - 7.0)), ((9.4, y - 4.6), (9.8, y - 8.2))]:
            d.line(a, b, 0.85, far)
        # near main beam: up and back off the skull, then sweeping forward over the face
        main = [(7.6, y + 0.2), (8.8, y - 2.8), (7.8, y - 5.4), (5.2, y - 6.7), (2.4, y - 6.3), (0.9, y - 5.0)]
        for a, b in zip(main, main[1:]):
            d.line(a, b, 1.15, ANT[2])
            d.line((a[0] + 0.3, a[1] + 0.35), (b[0] + 0.3, b[1] + 0.35), 0.5, ANT[1])
        tines = [((8.1, y - 1.4), (7.1, y - 3.6)),            # brow tine
                 ((7.6, y - 5.6), (7.9, y - 9.6)),
                 ((5.2, y - 6.7), (4.9, y - 10.4)),
                 ((2.8, y - 6.4), (2.2, y - 8.9))]
        for a, b in tines:
            d.line(a, b, 0.95, ANT[3])
            d.line((a[0] + 0.3, a[1]), (b[0] + 0.3, b[1] + 0.4), 0.45, ANT[1])
        d.line((7.0, y + 0.4), (8.4, y), 1.3, ANT[0])                  # burr
    # near legs last
    _front_leg(d, sh, g['FL'][0], g['FL'][1], True, 'FL')
    _hind_leg(d, hip, g['BL'][0], g['BL'][1], True, 'BL')
    from chris import selout
    selout(d.p)
    if s >= 2:
        d.p.outline(OUT)
    d.p.tags = d.tags
    return d.p


def walk(s=1, antlers=True, ghost=False):
    return [deer(f, s, antlers, ghost) for f in range(4)]
