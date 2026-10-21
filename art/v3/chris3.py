"""Chris, v3: detailed 48x84 sprite built from a jointed figure.

Every body part is drawn as a shaded volume (lit top-left) with its own
texture mapped to the part, so camo and fabric move with the limb instead of
swimming. Each part gets its own dark outline, which is what separates an arm
from the torso at this size. Legs and arms come from per-frame joint tables,
and leg pixels are tagged so the leg check can verify the stride.
"""
import math
import sys

import numpy as np

sys.path.insert(0, '../v2')
from px import Px, hx, BAYER4, value_noise  # noqa: E402

FW, FH = 48, 84
GROUND = 81
LIGHT = np.array([-0.6, -0.8])
LINE = '#17110e'

SKIN = ['#5a3324', '#844c33', '#b06f4c', '#d39470', '#ebb791', '#f6d3b0']
HAIR = ['#1d130d', '#2f2018', '#45301f', '#5e422b', '#78573a', '#8f6a48']
CAMO = ['#2a2219', '#3e3123', '#56442f', '#705b3d', '#8b744f', '#a68e64', '#bea77c']
CAMO_G = ['#1f2418', '#2d3522', '#3f4a2d', '#536139', '#677646', '#7d8b55', '#93a066']
BLAZE = ['#561d0b', '#933311', '#cc4f19', '#ee6f28', '#ff944a', '#ffb877']
PANTS = ['#1f2117', '#2e3122', '#41452d', '#575c3a', '#6e7349', '#868a58']
PATCH = ['#5e4d34', '#7d6848', '#a08a5e', '#bfa877']
BOOT = ['#1b120c', '#2f1e13', '#47301e', '#62432a', '#7f5a39', '#9a7350']
SOLE = ['#141010', '#2a2420']
METAL = ['#111215', '#202228', '#33363e', '#4f5562', '#717a89']
WOOD = ['#2e1b10', '#4a2d18', '#6b4223', '#8c5a30', '#ab7444']
STRAP = ['#1c1410', '#2e2118', '#433022']

_NOISE = {}


def noise(seed, cell=3):
    key = (seed, cell)
    if key not in _NOISE:
        _NOISE[key] = value_noise(96, 96, cell, seed, octaves=2)
    return _NOISE[key]


def camo_offset(u, v, seed):
    """Camo pattern in part-local coordinates. Returns (ramp or None, tone offset)."""
    a = noise(seed, 3)[int(v) % 96, int(u) % 96]
    b = noise(seed + 7, 3)[int(v + 31) % 96, int(u + 17) % 96]
    c = noise(seed + 13, 2)[int(v + 7) % 96, int(u + 53) % 96]
    if a > 0.66:
        return None, -3                  # dark bark blotch
    if b > 0.71:
        return CAMO_G, -1                # green leaf blotch
    if c > 0.68:
        return None, 1                   # tan highlight fleck
    return None, 0


class Fig:
    def __init__(self):
        self.p = Px(FW, FH)
        self.tag = np.zeros((FH, FW), dtype=object)

    # one part on its own layer: draw, outline, merge
    def part(self, draw_fn, tag=None, outline=True):
        layer = Px(FW, FH)
        draw_fn(layer)
        if outline:
            layer.outline(LINE)
        m = layer.a[:, :, 3] > 0
        self.p.a[m] = layer.a[m]
        if tag:
            self.tag[m] = tag

    @staticmethod
    def tone(ramp, lam, x, y, off=0, bias=0.0, contrast=0.45):
        if isinstance(off, tuple):
            ramp = off[0] or ramp
            off = off[1]
        dith = 0.0 if ramp is SKIN else (BAYER4[y % 4, x % 4] - 0.5) * 0.12   # never dither faces
        v = 0.55 + lam * contrast + bias + dith
        i = int(round(v * (len(ramp) - 1))) + off
        return ramp[max(0, min(len(ramp) - 1, i))]


def capsule(layer, a, b, r0, r1, ramp, tex=None, seed=0, bias=0.0, uv0=(0, 0)):
    """Tapered limb from a to b. Shaded as a cylinder; texture in limb coords."""
    ax, ay = a
    bx, by = b
    L = math.hypot(bx - ax, by - ay) or 1.0
    ux, uy = (bx - ax) / L, (by - ay) / L
    px_, py_ = -uy, ux                                   # across the limb
    rmax = max(r0, r1)
    for y in range(int(min(ay, by) - rmax) - 1, int(max(ay, by) + rmax) + 2):
        for x in range(int(min(ax, bx) - rmax) - 1, int(max(ax, bx) + rmax) + 2):
            dx, dy = x + 0.5 - ax, y + 0.5 - ay
            t = max(0.0, min(1.0, (dx * ux + dy * uy) / L))
            qx, qy = ax + ux * t * L, ay + uy * t * L
            d = math.hypot(x + 0.5 - qx, y + 0.5 - qy)
            r = r0 + (r1 - r0) * t
            if d > r:
                continue
            side = ((x + 0.5 - qx) * px_ + (y + 0.5 - qy) * py_) / max(r, 0.5)
            n = np.array([px_, py_]) * side
            lam = float(-(n @ LIGHT)) * -1 if False else float(n @ LIGHT)
            off = tex(uv0[0] + t * L, uv0[1] + side * r, seed) if tex else 0
            layer.set(x, y, Fig.tone(ramp, lam + 0.15, x, y, off, bias))


def blob(layer, cx, cy, rx, ry, ramp, tex=None, seed=0, bias=0.0, contrast=0.45):
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            nx, ny = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
            if nx * nx + ny * ny > 1:
                continue
            lam = nx * LIGHT[0] + ny * LIGHT[1]
            off = tex(x - cx + 40, y - cy + 40, seed) if tex else 0
            layer.set(x, y, Fig.tone(ramp, lam, x, y, off, bias, contrast))


def poly(layer, pts, center, radii, ramp, tex=None, seed=0, bias=0.0, contrast=0.45):
    from raster import _inside
    xs = [q[0] for q in pts]
    ys = [q[1] for q in pts]
    cx, cy = center
    for y in range(int(min(ys)) - 1, int(max(ys)) + 2):
        for x in range(int(min(xs)) - 1, int(max(xs)) + 2):
            if not _inside(x + 0.5, y + 0.5, pts):
                continue
            nx, ny = (x + 0.5 - cx) / radii[0], (y + 0.5 - cy) / radii[1]
            lam = max(-1.2, min(1.2, nx * LIGHT[0] + ny * LIGHT[1]))
            off = tex(x - cx + 40, y - cy + 40, seed) if tex else 0
            layer.set(x, y, Fig.tone(ramp, lam, x, y, off, bias, contrast))


# ------------------------------------------------------------------ legs ----
def leg(fig, hip, knee, ankle, toe_dir, near, tag, patch=False, heel_up=0.0):
    bias = 0.0 if near else -0.22

    def draw(l):
        capsule(l, hip, knee, 4.4, 3.7, PANTS, bias=bias)
        capsule(l, knee, ankle, 3.6, 3.0, PANTS, bias=bias)
        if patch:                                   # the worn knee patch Chris always has
            blob(l, knee[0] + toe_dir * 0.6, knee[1] + 0.8, 2.4, 2.2, PATCH, bias=bias + 0.1, contrast=0.3)
        # boot: ankle cuff, foot pointing toe_dir, heel lifted if pushing off
        ax, ay = ankle
        capsule(l, (ax, ay - 1), (ax + toe_dir * 0.5, ay + 1.5 - heel_up), 3.4, 3.4, BOOT, bias=bias)
        tip = (ax + toe_dir * 5.2, ay + 2.6 - heel_up * 0.2)
        capsule(l, (ax - toe_dir * 1.2, ay + 2.4 - heel_up), tip, 2.4, 2.1, BOOT, bias=bias + 0.05)
        for i in range(-2, 7):
            x = int(round(ax + toe_dir * i * 0.85))
            y = int(round(ay + 4.4 - heel_up * (1 - i / 7) if heel_up else ay + 4.4))
            l.set(x, y, SOLE[0])
    fig.part(draw, tag)


def arm(fig, shoulder, elbow, hand, near, tag, back_view=False):
    bias = 0.0 if near else -0.22

    def draw(l):
        capsule(l, shoulder, elbow, 4.0, 3.5, CAMO, camo_offset, 11 if near else 13, bias)
        capsule(l, elbow, hand, 3.4, 3.0, CAMO, camo_offset, 17 if near else 19, bias, uv0=(9, 0))
        blob(l, hand[0], hand[1] + 0.5, 2.3, 2.3, SKIN, bias=bias - (0.2 if back_view else 0))
    fig.part(draw, tag)


# ----------------------------------------------------------------- views ----
STEP_SIDE = {
    # leg -> (knee, ankle, heel_up) relative to hip; arm -> (elbow, hand) rel. to shoulder
    'contact': {'front': ((5, 13), (9, 27), 0.0), 'back': ((-4, 13), (-9, 26), 2.5),
                'arm_front': ((4, 10), (8, 17)), 'arm_back': ((-4, 10), (-7, 17)), 'bob': 1},
    'pass': {'front': ((5, 9), (-1, 21), 1.5), 'back': ((0, 14), (0, 28), 0.0),
             'arm_front': ((1, 11), (2, 19)), 'arm_back': ((-1, 11), (-1, 19)), 'bob': 0},
}


def side_right(phase, lead):
    """Facing right. lead: which of Chris's legs is in front ('L' or 'R').
    Facing right, Chris's right side is toward the camera (near)."""
    f = Fig()
    pose = STEP_SIDE[phase]
    bob = pose['bob']
    hip = (23, 50 + bob)
    sh = (23, 31 + bob)
    near_leg = 'R'
    near_leads = (lead == near_leg)
    # which pose slot does each leg use?
    slot = {near_leg: 'front' if near_leads else 'back', 'L': 'back' if near_leads else 'front'}
    # arms swing opposite the legs: the near arm goes forward when the near leg is back
    arm_slot = {'near': 'arm_back' if near_leads else 'arm_front', 'far': 'arm_front' if near_leads else 'arm_back'}

    def L(rel, base):
        return (base[0] + rel[0], base[1] + rel[1])

    # far arm, far leg (behind)
    e, h = pose[arm_slot['far']]
    arm(f, (sh[0] + 1, sh[1] + 1), L(e, sh), L(h, sh), False, 'arm_L')
    k, a, hu = pose[slot['L']]
    leg(f, (hip[0] + 1, hip[1]), L(k, hip), L(a, hip), 1, False, 'leg_L', patch=False, heel_up=hu)
    # rifle on the back, barrel up behind the head
    def rifle(l):
        capsule(l, (11.5, 54 + bob), (14.0, 40 + bob), 2.4, 2.0, WOOD)
        capsule(l, (13.6, 42 + bob), (15.6, 6 + bob), 1.2, 1.0, METAL)
        capsule(l, (12.6, 33 + bob), (13.8, 21 + bob), 1.9, 1.9, METAL)
        capsule(l, (13.0, 22 + bob), (13.4, 20 + bob), 2.3, 2.3, METAL)
    f.part(rifle)
    # torso: puffy jacket, slight forward lean, hood bunched at the back
    def torso(l):
        pts = [(15, 34 + bob), (18, 27 + bob), (28, 26.5 + bob), (32, 33 + bob), (32.5, 44 + bob),
               (30.5, 53 + bob), (16.5, 53 + bob), (14, 45 + bob)]
        poly(l, pts, (23, 38 + bob), (9, 14), CAMO, camo_offset, 3)
        blob(l, 18.5, 30 + bob, 4.2, 3.0, CAMO, camo_offset, 5, bias=-0.05)       # hood
        for y in (37, 44):                                                      # quilting
            for x in range(18, 30):
                if l.get(x, y + bob) is not None and l.get(x, y + bob)[3] and x % 2:
                    c = l.get(x, y + bob)[:3].astype(int)
                    l.set(x, y + bob, tuple((c * 0.8).astype(int)) + (255,))
        # blaze strap over the shoulder
        capsule(l, (21, 28 + bob), (27.5, 41 + bob), 2.3, 2.1, BLAZE)
        capsule(l, (20.5, 29 + bob), (19.5, 37 + bob), 2.0, 1.8, BLAZE, bias=-0.1)
        # belt
        for x in range(17, 30):
            l.set(x, 51 + bob, STRAP[1])
    f.part(torso)
    # near leg
    k, a, hu = pose[slot[near_leg]]
    leg(f, hip, L(k, hip), L(a, hip), 1, True, 'leg_R', patch=True, heel_up=hu)
    # head
    def head(l):
        hx_, hy = 25, 16 + bob
        blob(l, hx_ - 0.5, hy + 8.5, 3.4, 3.2, SKIN, bias=-0.15)                  # neck
        blob(l, hx_, hy, 7.0, 8.3, SKIN, contrast=0.4)
        blob(l, hx_ + 3.4, hy + 4.4, 4.0, 3.6, SKIN, bias=0.05, contrast=0.35)    # jaw and chin
        for y in range(int(hy - 9), int(hy + 5)):
            for x in range(int(hx_ - 8), int(hx_ + 7)):
                nx, ny = (x + 0.5 - hx_) / 7.1, (y + 0.5 - hy) / 8.4
                if nx * nx + ny * ny > 1:
                    continue
                if y < hy - 4.2 + max(0, (hx_ - x) * 0.6) - (2 if x > hx_ + 2 else 0) or x < hx_ - 4:
                    lam = nx * LIGHT[0] + ny * LIGHT[1]
                    l.set(x, y, Fig.tone(HAIR, lam, x, y, 0, 0.05))
    f.part(head)
    hx_, hy = 25, 16 + bob
    face = [
        (7, -1, SKIN[3]), (7, 0, SKIN[3]), (8, 0, SKIN[3]), (8, 1, SKIN[2]), (7, 1, SKIN[2]),   # nose
        (3, -3, HAIR[1]), (4, -3, HAIR[1]), (5, -3, HAIR[2]), (6, -3, HAIR[2]),                 # brow
        (4, -1, '#e9ddd0'), (5, -1, '#1a1210'), (5, 0, '#2a1e18'),                             # eye
        (5, 5, '#8a4c3a'), (6, 5, '#8a4c3a'),                                                  # mouth
        (-1, 0, SKIN[2]), (-1, 1, SKIN[1]), (-2, 1, SKIN[2]), (-1, 2, SKIN[1]), (-2, 0, SKIN[3]),  # ear
    ]
    for dx, dy, c in face:
        f.p.set(hx_ + dx, hy + dy, c)
    for dy in (6, 7):
        for dx in range(1, 7):
            if (dx + dy) % 2 == 0:
                f.p.set(hx_ + dx, hy + dy, '#9a6a52')
    # near arm last
    e, h = pose[arm_slot['near']]
    arm(f, sh, L(e, sh), L(h, sh), True, 'arm_R')
    return f


def front(phase, lead, back=False):
    """Facing the camera (down) or away (up)."""
    f = Fig()
    bob = 1 if phase == 'contact' else 0
    hips = {'R': (20.5, 50 + bob), 'L': (27.5, 50 + bob)}         # viewer-left is Chris's right
    if back:
        hips = {'L': (20.5, 50 + bob), 'R': (27.5, 50 + bob)}
    for side in ('R', 'L'):
        hx_, hy = hips[side]
        if phase == 'contact':
            fwd = (side == lead)
        else:
            fwd = None
        # from the front, the forward foot sits lower (closer); the back foot is higher with heel up
        if fwd is None:
            swing = (side == lead)                   # passing: `lead` is the leg swinging through
            knee, ankle, hu = (hx_, hy + 13 - (3 if swing else 0)), (hx_, GROUND - 5 - (5 if swing else 0)), (1.5 if swing else 0)
        elif fwd != back:
            knee, ankle, hu = (hx_, hy + 14), (hx_, GROUND - 4), 0
        else:
            knee, ankle, hu = (hx_, hy + 12), (hx_, GROUND - 8), 2.0
        def draw(l, hx_=hx_, hy=hy, knee=knee, ankle=ankle, hu=hu, side=side):
            light_side = hx_ < 24
            bias = 0.0 if light_side else -0.12
            out = -1 if light_side else 1
            k2 = (knee[0] + out * 0.6, knee[1])
            capsule(l, (hx_, hy), k2, 4.6, 3.8, PANTS, bias=bias)
            capsule(l, k2, (ankle[0], ankle[1] - 2), 3.6, 3.1, PANTS, bias=bias)
            if side == 'R':
                blob(l, k2[0], k2[1] + 1, 2.4, 2.1, PATCH, bias=bias + 0.1, contrast=0.3)
            ax, ay = ankle
            # boot: shaft, then a wider foot with a lighter toe cap, laces and a sole
            capsule(l, (ax, ay - 3), (ax, ay + 1), 3.3, 3.5, BOOT, bias=bias)
            for y in range(int(ay), int(ay + 4)):
                for x in range(int(ax - 4), int(ax + 5)):
                    nx = (x + 0.5 - ax) / 4.5
                    ny = (y - ay - 1.5) / 2.5
                    if nx * nx * 0.9 + max(0, ny) ** 2 <= 1:
                        l.set(x, y, Fig.tone(BOOT, nx * LIGHT[0] + ny * LIGHT[1] + 0.1, x, y, 0, bias))
            for x in range(int(ax - 2), int(ax + 3)):
                l.set(x, int(ay + 2), BOOT[4] if x < ax + 1 else BOOT[3])          # toe cap
            for y in range(int(ay - 3), int(ay)):
                l.set(int(ax), y, BOOT[0])                                          # laces
                if y % 2 == 0:
                    l.set(int(ax) - 1, y, BOOT[4])
            for x in range(int(ax - 4), int(ax + 5)):
                l.set(x, int(ay + 4), SOLE[0])
        f.part(draw, 'leg_' + side)
    # rifle barrel over the shoulder (Chris's right shoulder)
    def rifle(l):
        if back:
            capsule(l, (31, 50 + bob), (27, 31 + bob), 2.0, 1.8, WOOD)
            capsule(l, (27.5, 34 + bob), (24, 12 + bob), 1.1, 0.9, METAL)
            capsule(l, (27.0, 30 + bob), (25.2, 22 + bob), 1.7, 1.7, METAL)
        else:
            capsule(l, (17.5, 30 + bob), (15.5, 10 + bob), 1.1, 0.9, METAL)
    f.part(rifle)

    def torso(l):
        pts = [(12.5, 32 + bob), (16, 26.5 + bob), (32, 26.5 + bob), (35.5, 32 + bob), (35, 45 + bob),
               (32.5, 53 + bob), (15.5, 53 + bob), (13, 45 + bob)]
        poly(l, pts, (24, 34 + bob), (13, 19), CAMO, camo_offset, 21 if back else 23, contrast=0.38)
        for x in range(15, 33):                                                    # jacket hem
            l.set(x, 52 + bob, CAMO[1])
        if back:
            blob(l, 24, 30 + bob, 6, 3.4, CAMO, camo_offset, 25, bias=-0.04)       # hood
        else:
            for y in range(29, 51):                                                # zipper
                l.set(24, y + bob, CAMO[1])
        for x0 in (18.0, 30.0):                                                    # blaze vest straps
            for y in range(int(27 + bob), int(44 + bob)):
                for x in range(int(x0 - 1.5), int(x0 + 2.5)):
                    nx = (x + 0.5 - x0) / 2.0
                    l.set(x, y, Fig.tone(BLAZE, nx * LIGHT[0] - 0.2 + (0.25 if x0 < 24 else -0.1), x, y))
        for x in range(17, 31):
            l.set(x, 51 + bob, STRAP[1])
        if back:
            capsule(l, (29, 50 + bob), (21, 29 + bob), 0.7, 0.7, STRAP)            # sling
        else:
            capsule(l, (18, 29 + bob), (29, 47 + bob), 0.7, 0.7, STRAP)
    f.part(torso)

    def head(l):
        hx_, hy = 24, 16 + bob
        blob(l, hx_, hy + 8.5, 3.8, 2.8, SKIN, bias=-0.2)                          # neck
        er = 1.2 if back else 1.6
        blob(l, hx_ - 7.2, hy + 1.5, er, 2.4, SKIN, bias=0.0)                       # ears
        blob(l, hx_ + 7.2, hy + 1.5, er, 2.4, SKIN, bias=-0.15)
        blob(l, hx_, hy, 7.2, 8.3, SKIN if not back else HAIR, contrast=0.4)
        blob(l, hx_, hy + 4.6, 5.4, 3.8, SKIN if not back else HAIR, bias=0.0, contrast=0.35)  # jaw
        for y in range(int(hy - 9), int(hy + 9)):
            for x in range(int(hx_ - 8), int(hx_ + 8)):
                nx, ny = (x + 0.5 - hx_) / 7.3, (y + 0.5 - hy) / 8.4
                if nx * nx + ny * ny > 1:
                    continue
                hairline = hy - 4.2 + abs(nx) * 3.0
                if back:
                    if y < hy + 5:
                        l.set(x, y, Fig.tone(HAIR, nx * LIGHT[0] + ny * LIGHT[1], x, y))
                elif y < hairline:
                    l.set(x, y, Fig.tone(HAIR, nx * LIGHT[0] + ny * LIGHT[1], x, y, 0, 0.05))
    f.part(head)
    if not back:
        hx_, hy = 24, 16 + bob
        feats = []
        for dx in (-5, -4, -3, 2, 3, 4):
            feats.append((dx, -2, HAIR[1]))                                       # brows
        feats += [(-4, 0, '#f3e7da'), (-3, 0, '#1a1210'), (-4, 1, '#3a2a22'), (-3, 1, '#1a1210'),
                  (3, 0, '#1a1210'), (4, 0, '#e2d6c8'), (3, 1, '#1a1210'), (4, 1, '#3a2a22'),
                  (0, 1, SKIN[3]), (0, 2, SKIN[3]), (0, 3, SKIN[2]), (1, 3, SKIN[1]), (-1, 3, SKIN[2]),
                  (-2, 5, SKIN[1]), (-1, 5, '#8a4c3a'), (0, 5, '#8a4c3a'), (1, 5, '#8a4c3a'), (2, 5, SKIN[1])]
        for dx, dy, c in feats:
            f.p.set(hx_ + dx, hy + dy, c)
        for dy in (6, 7):
            for dx in range(-4, 5):
                if (dx + dy) % 2 == 0:
                    f.p.set(hx_ + dx, hy + dy, '#9a6a52')                          # stubble
    # arms at the sides, swinging opposite the legs
    for side, sx in (('R', 11.5), ('L', 36.5)) if not back else (('L', 11.5), ('R', 36.5)):
        lit = sx < 24
        if phase == 'contact':
            arm_fwd = (side != lead)
        else:
            arm_fwd = None
        drop = 0 if arm_fwd is None else (2 if arm_fwd != back else -2)
        out = -1 if lit else 1
        sh = (sx + (2.5 if lit else -2.5), 30 + bob)
        el = (sx + out * 0.5, 41 + bob + drop * 0.4)
        hd = (sx + out * 0.2, 49 + bob + drop)
        arm(f, sh, el, hd, lit, 'arm_' + side, back_view=back)
    return f


# In contact frames `lead` is the leg planted in front; in passing frames it is
# the leg swinging forward (the one that was behind), so the order is L, R, R, L.
CYCLE = [('contact', 'L'), ('pass', 'R'), ('contact', 'R'), ('pass', 'L')]
EXPECTED = ['L', None, 'R', None]


def walk(direction):
    if direction == 'right':
        return [side_right(ph, ld) for ph, ld in CYCLE]
    if direction == 'left':
        out = []
        for ph, ld in CYCLE:
            # mirror a right-facing frame whose *other* leg leads, then swap tags
            f = side_right(ph, 'R' if ld == 'L' else 'L')
            f.p = f.p.flipped()
            f.tag = f.tag[:, ::-1].copy()
            sw = {'leg_L': 'leg_R', 'leg_R': 'leg_L', 'arm_L': 'arm_R', 'arm_R': 'arm_L'}
            f.tag = np.vectorize(lambda t: sw.get(t, t), otypes=[object])(f.tag)
            out.append(f)
        return out
    return [front(ph, ld, back=(direction == 'up')) for ph, ld in CYCLE]
