"""Chris, v2: hand-placed pixels, 16x27 frames, selective outline.

Head and torso are pixel grids. Arms and legs are parts placed per frame
from a pose table, so left/right footfalls alternate by construction.
"""
import numpy as np

from px import Px, hx, OUT

FW, FH = 16, 27

PAL = {
    'h': '#4a3123', 'l': '#76513a', 'H': '#33221b',            # hair mid / light / dark
    'S': '#f1c39b', 's': '#d79a70', 'k': '#a8694b',            # skin light / mid / shadow
    'e': '#241a1e', 'b': '#a87458',                            # eyes, stubble
    'V': '#ec641d', 'F': '#ff9a45', 'v': '#ad4116',            # blaze vest mid / light / dark
    'C': '#625c3a', 'K': '#867d4f', 'c': '#403d28', 'G': '#4f6035',  # camo
    'P': '#5c5240', 'p': '#38322a', 'Q': '#7a6c50',            # pants mid / dark / near-leg light
    'D': '#55402f', 'B': '#2e221b',                            # boots light / dark
    'M': '#3a3d44', 'm': '#6b7380', 'W': '#8a5a34',            # rifle metal / light, stock
}

FRONT_HEAD = [
    "................",
    ".....hhhhhh.....",
    "....hhllhhhh....",
    "...hhllhhhhhH...",
    "...hhhhhhhhhH...",
    "...HhsSSSSShH...",
    "...HsSSSSSSsH...",
    "...ksSeSSeSsk...",
    "...ksSeSSeSsk...",
    "...ksSSSsSSsk...",
    "....bSSSSSSb....",
    ".....bbssbb.....",
]
FRONT_BODY = [
    "....KFVCCVvK....",
    "....FVCGCCVv....",
    "....FVCCKCVv....",
    "....VVGCCGVv....",
    "....VVCKCCVv....",
    "....vvCCGCvv....",
    "....cccccccc....",
    "....PPPPPPpp....",
]
BACK_HEAD = [
    "................",
    ".....hhhhhh.....",
    "....hhllhhhh....",
    "...hhllhhhhhH...",
    "...hhhlhhhhhH...",
    "...hhhhhhhhhH...",
    "...hhhhhhhhhH...",
    "...khhhhhhhHk...",
    "...khhhhhhHHk...",
    "...sHhhhhhHHs...",
    "....sHHHHHHs....",
    ".....ssssss.....",
]
BACK_BODY = [
    "....FVVVVVMv....",
    "....FVVVVMVv....",
    "....VVVVMVVv....",
    "....VVVWVVVv....",
    "....VVWWVVvv....",
    "....vWWvvvvv....",
    "....cccccccc....",
    "....PPPPPPpp....",
]
SIDE_HEAD = [   # facing right
    "................",
    ".....hhhhh......",
    "....hllhhhh.....",
    "...hhllhhhhh....",
    "...hhhhhhhhhh...",
    "...HhhhhsSSSS...",
    "...HhhhsSSSSS...",
    "...HhkksSSeSS...",
    "...HhkksSSeSSS..",
    "....hhssSSSSs...",
    ".....bbsSSSb....",
    "......bbbbb.....",
]
SIDE_BODY = [
    "......VVVVv.....",
    ".....MVVVVv.....",
    ".....MFVVVv.....",
    ".....WFVVVv.....",
    ".....WVVVVv.....",
    "......vvvvv.....",
    "......cccccc....",
    "......PPPPpp....",
]
SIDE_BARREL = [(5, 9), (5, 10), (4, 7), (4, 8), (5, 11)]

# 'L'/'R' = Chris's own left/right leg forward; None = passing
CYCLE = ['L', None, 'R', None]


def _boot(p, x, y, w, near=True):
    for i in range(w):
        p.set(x + i, y, PAL['D'] if near else PAL['B'])
        p.set(x + i, y + 1, PAL['B'])


def selout(p):
    """Outline, then soften it on the lit (top-left) side: those outline pixels
    take a dark version of the colour they border instead of near-black."""
    alpha = p.a[:, :, 3] > 0
    src = p.a.copy()
    p.outline(OUT)
    h, w = alpha.shape
    for y in range(h):
        for x in range(w):
            if alpha[y, x] or p.a[y, x, 3] == 0:
                continue
            # neighbour below or to the right means this outline pixel is on the lit side
            for dx, dy in ((1, 0), (0, 1)):
                xx, yy = x + dx, y + dy
                if 0 <= xx < w and 0 <= yy < h and alpha[yy, xx] and y < h * 0.45:
                    c = src[yy, xx, :3].astype(np.float32) * 0.42
                    p.a[y, x, :3] = c.astype(np.uint8)
                    break


def front(step, back=False):
    p = Px(FW, FH)
    head = BACK_HEAD if back else FRONT_HEAD
    body = BACK_BODY if back else FRONT_BODY
    # legs: from the front, Chris's left leg is on the viewer's right
    cols = {'R': 4, 'L': 9} if not back else {'L': 4, 'R': 9}
    for side in ('L', 'R'):
        x = cols[side]
        if step is None:
            foot = 23
        elif not back:
            foot = 24 if step == side else 22
        else:
            foot = 22 if step == side else 24
        for y in range(20, foot):
            p.set(x, y, PAL['P'] if x < 7 else PAL['p'])
            p.set(x + 1, y, PAL['P'] if x < 7 else PAL['P'])
            p.set(x + 2, y, PAL['p'])
        bx = x - 1 if x < 7 else x
        _boot(p, bx, foot, 4)
    p.ascii(head, PAL, 0, 0)
    p.ascii(body, PAL, 0, 12)
    # arms swing opposite the legs
    arms = {'R': 2, 'L': 12} if not back else {'L': 2, 'R': 12}
    for side in ('L', 'R'):
        x = arms[side]
        swing = 0
        if step is not None:
            swing = 1 if step != side else -1
            if back:
                swing = -swing
        length = 5 + swing
        lit = x < 7
        for y in range(13, 13 + length):
            p.set(x, y, PAL['K'] if lit else PAL['C'])
            p.set(x + 1, y, PAL['C'] if lit else PAL['c'])
        hand = PAL['S'] if not back else PAL['s']
        p.set(x, 13 + length, hand)
        p.set(x + 1, 13 + length, PAL['s'] if not back else PAL['k'])
    selout(p)
    return p


SIDE_POSE = {
    'L': {'L': (3, 0), 'R': (-4, 0)},            # dx forward (to the right)
    'pass_L': {'L': (0, 0), 'R': (1, 2)},        # right leg swinging through
    'R': {'L': (-4, 0), 'R': (3, 0)},
    'pass_R': {'L': (1, 2), 'R': (0, 0)},
}
SIDE_CYCLE = ['L', 'pass_L', 'R', 'pass_R']


def _line(p, x0, y0, x1, y1, c, wdt=2):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for i in range(n + 1):
        t = i / max(1, n)
        x = round(x0 + (x1 - x0) * t)
        y = round(y0 + (y1 - y0) * t)
        for k in range(wdt):
            p.set(x + k, y, c)


def side(step):
    """Facing right. The near side is Chris's right."""
    p = Px(FW, FH)
    pose = SIDE_POSE[step]
    hip = (8, 19)

    def leg(which, near):
        dx, lift = pose[which]
        col = PAL['Q'] if near else PAL['p']
        fx, fy = hip[0] + dx, 24 - lift
        if lift:
            kx, ky = hip[0] + 1, 22
            _line(p, hip[0], hip[1], kx, ky, col)
            _line(p, kx, ky, fx, fy, col)
        else:
            _line(p, hip[0], hip[1], fx, fy, col)
        bx = fx                       # toe points right
        for i in range(4):
            p.set(bx + i - 1, fy, PAL['D'] if near else PAL['B'])
            p.set(bx + i - 1, fy + 1, PAL['B'])

    def arm(which, near):
        dx = 0
        if step == 'L':
            dx = -3 if which == 'L' else 3
        elif step == 'R':
            dx = 3 if which == 'L' else -3
        col = PAL['C'] if near else PAL['c']
        hx_, hy = 8 + dx, 18 - abs(dx) // 2
        _line(p, 8, 13, hx_, hy, col)
        if near:
            _line(p, 8, 13, 8, 14, PAL['K'], 1)
        p.set(hx_, hy + 1, PAL['S'] if near else PAL['s'])
        p.set(hx_ + 1, hy + 1, PAL['s'] if near else PAL['k'])

    leg('L', near=False)
    arm('L', near=False)
    p.ascii(SIDE_HEAD, PAL, 0, 0)
    p.ascii(SIDE_BODY, PAL, 0, 12)
    for x, y in SIDE_BARREL:
        p.set(x, y, PAL['M'])
    leg('R', near=True)
    arm('R', near=True)
    selout(p)
    return p


def walk(direction):
    if direction == 'down':
        return [front(s) for s in CYCLE]
    if direction == 'up':
        return [front(s, back=True) for s in CYCLE]
    if direction == 'right':
        return [side(s) for s in SIDE_CYCLE]
    # left is the mirror; mirroring swaps which leg is near, so start from the
    # frame where the (now-near) left leg leads
    return [side(s).flipped() for s in ['R', 'pass_R', 'L', 'pass_L']]
