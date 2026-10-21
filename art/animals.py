"""Animals, drawn from shapes so one definition renders at any scale.

Overworld sprites use scale 1. Battle sprites reuse the same definition at a
larger scale, which keeps both views on-model. All animals face left.

Quadrupeds walk with a diagonal gait: front-left moves with back-right, and
front-right with back-left. Leg pixels are tagged FL, FR, BL, BR (the
animal's own left/right; facing left, its left side is toward the camera).
"""
from raster import Canvas
import palette as P

# frame -> {leg: (dx, lift)}; negative dx = forward (the animal faces left)
QUAD_GAIT = [
    {'FL': (-2, 0), 'BR': (-2, 0), 'FR': (2, 0), 'BL': (2, 0)},
    {'FL': (0, 0), 'BR': (0, 0), 'FR': (-0.5, 1.5), 'BL': (-0.5, 1.5)},
    {'FL': (2, 0), 'BR': (2, 0), 'FR': (-2, 0), 'BL': (-2, 0)},
    {'FL': (-0.5, 1.5), 'BR': (-0.5, 1.5), 'FR': (0, 0), 'BL': (0, 0)},
]
QUAD_EXPECTED = [{'FL', 'BR'}, None, {'FR', 'BL'}, None]


def _outline(c, s):
    c.outline(P.OUTLINE)
    if s >= 2:                      # battle-size sprites get a 2px line
        c.outline(P.OUTLINE)


class Pen:
    """Draws onto a canvas in a scaled coordinate space."""

    def __init__(self, c, s, ox=0, oy=0):
        self.c, self.s, self.ox, self.oy = c, s, ox, oy

    def _p(self, x, y):
        return self.ox + x * self.s, self.oy + y * self.s

    def ell(self, x, y, rx, ry, col, shade=None, light=None, tag=None):
        X, Y = self._p(x, y)
        self.c.ellipse(X, Y, rx * self.s, ry * self.s, col, tag, shade, light)

    def poly(self, pts, col, tag=None):
        self.c.poly([self._p(x, y) for x, y in pts], col, tag)

    def line(self, x0, y0, x1, y1, col, w=1.0, tag=None, minw=1.0):
        X0, Y0 = self._p(x0, y0)
        X1, Y1 = self._p(x1, y1)
        self.c.line(X0, Y0, X1, Y1, col, max(minw, w * self.s), tag)

    def dot(self, x, y, col, size=1, tag=None):
        X, Y = self._p(x, y)
        n = max(1, int(round(size * self.s)))
        self.c.rect(int(X), int(Y), n, n, col, tag)


def _leg(pen, hip, ground, dx, lift, col, hoof, w, tag, hind=False):
    """Planted hooves always end on `ground`, even while the body bobs."""
    hx, hy = hip
    length = ground - hy
    fx, fy = hx + dx, ground - lift
    if hind:
        # hock bends backward
        kx, ky = hx + 1.6 + dx * 0.4, hy + length * 0.55 - lift * 0.5
        pen.line(hx, hy, kx, ky, col, w * 1.25, tag)
        pen.line(kx, ky, fx, fy, col, w * 0.85, tag)
    else:
        kx, ky = hx + dx * 0.5 - lift * 0.6, hy + length * 0.5 - lift * 0.4
        pen.line(hx, hy, kx, ky, col, w * 1.15, tag)
        pen.line(kx, ky, fx, fy, col, w * 0.85, tag)
    pen.line(fx - 0.2, fy - 0.3, fx + 0.6, fy - 0.3, hoof, max(w * 0.8, 0.9), tag)


# ---------------------------------------------------------------- deer ----
def deer(frame=0, s=1.0, antlers=0, ghost=False):
    pal = dict(base=P.DEER, sh=P.DEER_SH, lt=P.DEER_LT, belly=P.CREAM)
    if ghost:
        pal = dict(base=P.GHOST, sh=P.GHOST_SH, lt=P.GHOST_LT, belly=P.GHOST_LT)
    W, H = int(32 * s) + 2, int(37 * s) + 2
    c = Canvas(W, H)
    pen = Pen(c, s, 1, 1 + 9 * s)   # headroom for antlers
    gait = QUAD_GAIT[frame]
    bob = 0.5 if frame in (1, 3) else 0
    fh, bh = (11.5, 14 - bob), (21.5, 13.5 - bob)
    far = pal['sh']
    _leg(pen, fh, 25.5, gait['FR'][0], gait['FR'][1], far, P.HOOF, 1.6, 'FR')
    _leg(pen, (bh[0] + 0.5, bh[1]), 25.5, gait['BR'][0], gait['BR'][1], far, P.HOOF, 1.6, 'BR', hind=True)
    # body
    pen.ell(17, 12 - bob, 8.2, 4.6, pal['base'], pal['sh'], pal['lt'])
    pen.ell(17.5, 14.6 - bob, 6.0, 1.6, pal['belly'])
    pen.ell(22.5, 11 - bob, 3.6, 4.0, pal['base'], pal['sh'], pal['lt'])
    # tail
    pen.ell(26.2, 9.4 - bob, 1.3, 1.9, P.WHITE if not ghost else P.GHOST_LT)
    pen.dot(26.0, 8.0 - bob, pal['sh'])
    # neck + head
    pen.poly([(9, 11 - bob), (13.5, 9 - bob), (8.5, 3.2 - bob), (5.5, 4.5 - bob)], pal['base'])
    pen.poly([(9.5, 12 - bob), (12.5, 11 - bob), (8, 5 - bob), (6.6, 6 - bob)], pal['lt'])
    pen.ell(5.4, 4.6 - bob, 2.8, 2.1, pal['base'], None, pal['lt'])
    pen.poly([(4, 4 - bob), (0.6, 5.6 - bob), (1, 7 - bob), (4.6, 6.6 - bob)], pal['base'])
    pen.dot(0.8, 5.4 - bob, P.NOSE)
    pen.line(2.2, 6.6 - bob, 4.2, 6.6 - bob, P.WHITE, 0.8)
    pen.dot(4.2, 3.6 - bob, P.NOSE if not ghost else P.GHOST_EYE)
    # ears
    pen.poly([(6.5, 3 - bob), (9.8, 0.4 - bob), (10.2, 2 - bob), (7.6, 4 - bob)], pal['base'])
    pen.dot(8.6, 1.8 - bob, pal['sh'])
    if antlers:
        a = P.ANTLER if not ghost else P.GHOST_LT
        b = P.ANTLER_SH
        y0 = 2.4 - bob
        # far beam first, darker, offset back
        pen.line(7.6, y0, 9.0, y0 - 3.6, b, 1.0)
        pen.line(9.0, y0 - 3.6, 6.6, y0 - 6.2, b, 1.0)
        pen.line(8.6, y0 - 4.4, 9.8, y0 - 7.6, b, 0.9)
        # near beam: sweeps back, up, then forward over the face
        pen.line(6.6, y0, 7.6, y0 - 3.4, a, 1.1)
        pen.line(7.6, y0 - 3.4, 5.6, y0 - 5.6, a, 1.1)
        pen.line(5.6, y0 - 5.6, 2.6, y0 - 5.8, a, 1.0)
        pen.line(7.0, y0 - 4.2, 7.6, y0 - 8.0, a, 0.9)
        if antlers >= 2:
            pen.line(5.2, y0 - 5.6, 5.0, y0 - 8.6, a, 0.9)
        if antlers >= 3:
            pen.line(3.4, y0 - 5.8, 2.8, y0 - 8.0, a, 0.9)
    # near legs last
    _leg(pen, (fh[0] + 1, fh[1]), 25.5, gait['FL'][0], gait['FL'][1], pal['base'], P.HOOF, 1.6, 'FL')
    _leg(pen, (bh[0] + 1.5, bh[1]), 25.5, gait['BL'][0], gait['BL'][1], pal['base'], P.HOOF, 1.6, 'BL', hind=True)
    _outline(c, s)
    return c


# ----------------------------------------------------------------- fox ----
def fox(frame=0, s=1.0):
    W, H = int(30 * s) + 2, int(18 * s) + 2
    c = Canvas(W, H)
    pen = Pen(c, s, 1, 1)
    g = QUAD_GAIT[frame]
    bob = 0.4 if frame in (1, 3) else 0
    fh, bh = (8.5, 10 - bob), (16.5, 9.5 - bob)
    _leg(pen, fh, 16.5, g['FR'][0] * 0.8, g['FR'][1] * 0.8, P.FOX_SOCK, P.FOX_SOCK, 1.3, 'FR')
    _leg(pen, bh, 16.5, g['BR'][0] * 0.8, g['BR'][1] * 0.8, P.FOX_SOCK, P.FOX_SOCK, 1.3, 'BR', hind=True)
    # tail
    pen.poly([(18, 7.5 - bob), (25, 5 - bob), (29, 8 - bob), (27, 10.5 - bob), (20, 10 - bob)], P.FOX)
    pen.poly([(22, 9.5 - bob), (25, 5.5 - bob), (27.5, 8.5 - bob), (26, 10.2 - bob)], P.FOX_SH)
    pen.ell(28, 8.6 - bob, 1.6, 1.4, P.WHITE)
    # body
    pen.ell(12.5, 8 - bob, 6.6, 3.2, P.FOX, P.FOX_SH, P.FOX_LT)
    pen.ell(11.5, 10 - bob, 4.2, 1.1, P.CREAM)
    # head
    pen.ell(5, 5.5 - bob, 2.8, 2.4, P.FOX, None, P.FOX_LT)
    pen.poly([(3.2, 5 - bob), (-0.2, 7 - bob), (3.6, 7.6 - bob)], P.FOX)
    pen.poly([(1.4, 7 - bob), (-0.2, 7 - bob), (3.6, 7.8 - bob), (4.6, 7.2 - bob)], P.WHITE)
    pen.dot(-0.2, 6.4 - bob, P.NOSE)
    pen.dot(4.0, 4.6 - bob, P.NOSE)
    pen.poly([(4.4, 3.6 - bob), (5.4, 0.2 - bob), (7, 3.6 - bob)], P.FOX)
    pen.dot(5.4, 2.0 - bob, P.FOX_SOCK)
    pen.poly([(6.6, 3.8 - bob), (7.8, 0.8 - bob), (8.4, 4.4 - bob)], P.FOX_SH)
    _leg(pen, (fh[0] + 1, fh[1]), 16.5, g['FL'][0] * 0.8, g['FL'][1] * 0.8, P.FOX_SOCK, P.FOX_SOCK, 1.3, 'FL')
    _leg(pen, (bh[0] + 1.2, bh[1]), 16.5, g['BL'][0] * 0.8, g['BL'][1] * 0.8, P.FOX_SOCK, P.FOX_SOCK, 1.3, 'BL', hind=True)
    _outline(c, s)
    return c


# ---------------------------------------------------------------- bear ----
def bear(frame=0, s=1.0):
    W, H = int(34 * s) + 2, int(24 * s) + 2
    c = Canvas(W, H)
    pen = Pen(c, s, 1, 1)
    g = QUAD_GAIT[frame]
    bob = 0.5 if frame in (1, 3) else 0
    fh, bh = (10.5, 13 - bob), (24, 13 - bob)
    _leg(pen, fh, 22.5, g['FR'][0] * 1.2, g['FR'][1], P.BEAR_SH, P.BEAR_SH, 3.0, 'FR')
    _leg(pen, bh, 22.5, g['BR'][0] * 1.2, g['BR'][1], P.BEAR_SH, P.BEAR_SH, 3.2, 'BR')
    pen.ell(18, 9.5 - bob, 11, 6.2, P.BEAR, P.BEAR_SH, P.BEAR_LT)
    pen.ell(13, 6.4 - bob, 4.6, 3.6, P.BEAR, None, P.BEAR_LT)     # shoulder hump
    pen.ell(6.2, 10 - bob, 4.4, 3.8, P.BEAR, P.BEAR_SH, P.BEAR_LT)
    pen.ell(2.8, 11.4 - bob, 2.6, 1.9, P.BEAR_MUZ)
    pen.dot(0.6, 10.6 - bob, P.NOSE, 1.2)
    pen.dot(5.2, 9.0 - bob, P.NOSE)
    pen.ell(7.6, 6.4 - bob, 1.5, 1.5, P.BEAR)
    pen.dot(7.4, 6.3 - bob, P.BEAR_MUZ)
    _leg(pen, (fh[0] + 1.5, fh[1] + 0.5), 22.5, g['FL'][0] * 1.2, g['FL'][1], P.BEAR_LT, P.BEAR_SH, 3.0, 'FL')
    _leg(pen, (bh[0] + 1.5, bh[1] + 0.5), 22.5, g['BL'][0] * 1.2, g['BL'][1], P.BEAR_LT, P.BEAR_SH, 3.2, 'BL')
    _outline(c, s)
    return c


# -------------------------------------------------------------- turkey ----
# Biped: left and right legs alternate like the hunter's side view.
TURKEY_GAIT = [
    {'L': (-2, 0), 'R': (2, 0)},
    {'L': (0, 0), 'R': (0.5, 1.5)},
    {'L': (2, 0), 'R': (-2, 0)},
    {'L': (0.5, 1.5), 'R': (0, 0)},
]
TURKEY_EXPECTED = ['L', None, 'R', None]


def turkey(frame=0, s=1.0, strut=False):
    W, H = int(24 * s) + 2, int(24 * s) + 2
    c = Canvas(W, H)
    pen = Pen(c, s, 1, 1)
    g = TURKEY_GAIT[frame]
    bob = 0.5 if frame in (1, 3) else 0
    hip = (11.5, 15.5 - bob)

    def leg(side, col):
        dx, lift = g[side]
        fx, fy = hip[0] + dx, 22 - lift
        pen.line(hip[0], hip[1], fx, fy, col, 1.0, 'leg_' + side)
        pen.line(fx - 1.5, fy, fx + 0.5, fy, col, 0.9, 'leg_' + side)

    leg('R', '#a8574a')
    if strut:
        pen.ell(16, 8, 7.5, 7.5, P.TURKEY, P.TURKEY_SH)
        for i, a in enumerate(range(-80, 81, 20)):
            import math
            r = math.radians(a)
            pen.line(16, 9, 16 + 7.4 * math.sin(r), 9 - 7.4 * math.cos(r), P.TURKEY_BAND if i % 2 else P.TURKEY_SH, 0.9)
        pen.ell(16, 9, 5.4, 5.4, P.TURKEY, P.TURKEY_SH)
    else:
        pen.poly([(14, 11 - bob), (21, 9 - bob), (22.5, 13 - bob), (16, 15 - bob)], P.TURKEY_SH)
        pen.line(17, 12.5 - bob, 22, 11 - bob, P.TURKEY_BAND, 0.8)
    pen.ell(11.5, 12 - bob, 5.4, 4.4, P.TURKEY, P.TURKEY_SH, P.TURKEY_IRI)
    pen.line(9, 13 - bob, 14, 13 - bob, P.TURKEY_IRI, 0.8)
    pen.line(8.5, 15 - bob, 7.5, 18 - bob, '#3a2d22', 0.9)   # beard
    pen.line(7.6, 11 - bob, 5.2, 5 - bob, P.TURKEY_HEAD, 1.6)
    pen.ell(4.8, 4.2 - bob, 1.8, 1.6, P.TURKEY_HEAD)
    pen.line(3.2, 5 - bob, 4.0, 8.2 - bob, P.WATTLE, 1.2)
    pen.dot(2.2, 4.0 - bob, '#d9b25a')
    pen.dot(4.6, 3.6 - bob, P.NOSE)
    leg('L', '#c46a58')
    _outline(c, s)
    return c


# -------------------------------------------------------------- rabbit ----
def rabbit(frame=0, s=1.0):
    W, H = int(14 * s) + 2, int(12 * s) + 2
    c = Canvas(W, H)
    pen = Pen(c, s, 1, 1)
    hop = [0, 1.5, 2.5, 1.0][frame]
    pen.ell(7.5, 8 - hop, 4.4, 3.0, P.RABBIT, P.RABBIT_SH, P.RABBIT_LT)
    pen.ell(11.8, 7.2 - hop, 1.4, 1.4, P.WHITE)
    pen.ell(9, 10.4 - hop * 0.6, 2.6, 1.0, P.RABBIT_SH)
    pen.ell(3.6, 6 - hop, 2.4, 2.1, P.RABBIT, None, P.RABBIT_LT)
    pen.poly([(4, 4.6 - hop), (5.2, 0.2 - hop), (6.2, 0.6 - hop), (5.4, 5 - hop)], P.RABBIT)
    pen.dot(5.3, 1.4 - hop, '#d8a497')
    pen.dot(2.6, 5.4 - hop, P.NOSE)
    pen.dot(1.4, 6.6 - hop, '#c98c86')
    pen.line(4.5, 10 - hop * 0.3, 3.6, 11 - hop * 0.2, P.RABBIT, 1.0)
    _outline(c, s)
    return c


def walk(name, s=1.0):
    fn = {
        'whitetail_doe': lambda f: deer(f, s),
        'whitetail_buck': lambda f: deer(f, s, antlers=3),
        'ghost_buck': lambda f: deer(f, s, antlers=3, ghost=True),
        'red_fox': lambda f: fox(f, s),
        'black_bear': lambda f: bear(f, s),
        'wild_turkey': lambda f: turkey(f, s),
        'cottontail': lambda f: rabbit(f, s),
    }[name]
    return [fn(f) for f in range(4)]


ROSTER = ['cottontail', 'wild_turkey', 'whitetail_doe', 'red_fox',
          'whitetail_buck', 'black_bear', 'ghost_buck']
