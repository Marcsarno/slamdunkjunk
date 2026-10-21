"""The hunter: 16x24 overworld sprite, 4 directions x 4-frame walk cycle.

The head and torso are hand-placed pixels. Arms and legs are separate parts
placed from a pose table, so which leg is forward in each frame is data that
the leg check (verify.py) can test. Pixels are tagged leg_L / leg_R / arm_L /
arm_R, where L and R are the hunter's own left and right.
"""
from raster import Canvas
import palette as P

W, H = 16, 24

PAL = {
    'H': P.HAIR, 'h': P.HAIR_SH, 'S': P.SKIN, 's': P.SKIN_SH, 'B': P.STUBBLE,
    'E': P.EYE, 'C': P.CAMO, 'c': P.CAMO_DK, 'k': P.CAMO_LT, 'g': P.CAMO_GR,
    'V': P.BLAZE, 'v': P.BLAZE_SH, 'G': P.GUNMETAL, 'l': P.GUN_LT,
    'W': P.STOCK, 'w': P.STOCK_SH, 'O': P.OUTLINE,
}

DOWN = [
    "................",
    "....HHHHHHHH....",
    "...HHHHHHHHHH...",
    "...HHhHHHHhHH...",
    "...hSSSSSSSSh...",
    "...SSESSSSESS...",
    "...SSESSSSESS...",
    "...sSSSSSSSSs...",
    "....BSSssSSB....",
    ".....BBBBBB.....",
    "....VVkCCgVV....",
    "....VVCgCkVV....",
    "....VVCCkCVV....",
    "....VVgCCCVV....",
    "....VVCkCgVV....",
    "....vvCCcCvv....",
    "....cccWWccc....",
]

UP = [
    "................",
    "....HHHHHHHH....",
    "...HHHHHHHHHH...",
    "...HHHHHHHHHH...",
    "...HHHHHHHHHH...",
    "...HHHHHHHHHH...",
    "...sHHHHHHHHs...",
    "...ShHHHHHHhS...",
    "....hhhhhhhh....",
    ".....SSSSSS.....",
    "....VVVVVVlV....",
    "....VVVVVGVV....",
    "....VvVVGVVV....",
    "....VVVwVVvV....",
    "....VVWWVVVV....",
    "....vWWvvvvv....",
    "....cccccccc....",
]

# Facing left. Rifle slung on the back (right side of the sprite).
LEFT = [
    "................",
    ".....HHHHHH.....",
    "....HHHHHHHH....",
    "....HHHHHHHHH...",
    "....SSHHHHHHH...",
    "....SESSHsHHH...",
    "...SSSSSSsHHh...",
    "....SSSSSSHh....",
    "....BBSSSs......",
    ".....BBBB.......",
    ".....VVVVVv.....",
    ".....VVVVvvG....",
    ".....VVVVvvG....",
    ".....VVVVvwW....",
    ".....VVVVvWW....",
    ".....vvvvv......",
    ".....cccccc.....",
]
# barrel poking up behind the shoulder in the side view
LEFT_BARREL = [(11, 8), (12, 7), (12, 6), (12, 5)]
UP_BARREL = [(11, 9), (12, 8), (12, 7)]


def _boot(c, x, y, w, tag):
    c.rect(x, y, w, 1, P.BOOT_LT, tag)
    c.rect(x, y + 1, w, 1, P.BOOT, tag)


# ---- front / back -------------------------------------------------------
# step: 'L' = hunter's left leg forward, 'R' = right leg forward, None = passing
CYCLE = ['L', None, 'R', None]


def _front_back(step, facing):
    c = Canvas(W, H)
    body = DOWN if facing == 'down' else UP
    # Screen columns of each leg. Facing the camera, the hunter's left leg
    # is on the viewer's right. From behind, it is on the viewer's left.
    if facing == 'down':
        cols = {'R': 4, 'L': 9}
        arm_cols = {'R': 2, 'L': 12}
    else:
        cols = {'L': 4, 'R': 9}
        arm_cols = {'L': 2, 'R': 12}

    for side in ('L', 'R'):
        x = cols[side]
        tag = 'leg_' + side
        if step is None:
            foot = 20                         # both planted
        elif facing == 'down':
            foot = 21 if step == side else 19  # front leg reaches lower
        else:
            foot = 19 if step == side else 21  # walking away: front leg higher
        c.rect(x, 17, 3, foot - 17, P.PANTS, tag)
        c.rect(x + (2 if x < 7 else 0), 17, 1, foot - 17, P.PANTS_SH, tag)
        c.rect(7, 17, 2, 1, P.PANTS_SH)        # crotch
        _boot(c, x, foot, 3, tag)

    c.ascii(body, PAL)
    if facing == 'up':
        for x, y in UP_BARREL:
            c.set(x, y, P.GUNMETAL)

    # Arms swing opposite the legs: left leg forward -> right arm forward.
    for side in ('L', 'R'):
        x = arm_cols[side]
        tag = 'arm_' + side
        swing = 0
        if step is not None:
            fwd = (step != side)
            swing = 1 if fwd else -1
            if facing == 'up':
                swing = -swing
        length = 5 + swing
        c.rect(x, 10, 2, length, P.CAMO, tag)
        c.rect(x + (1 if x < 7 else 0), 10, 1, length, P.CAMO_DK, tag)
        c.rect(x, 10 + length, 2, 1, P.SKIN if facing == 'down' else P.SKIN_SH, tag)

    c.outline(P.OUTLINE)
    return c


# ---- side ---------------------------------------------------------------
# Hip x for side view; positive dx = backward (toward the sprite's right).
SIDE_LEGS = {
    # step: {leg: (foot_dx, lift)}
    'L': {'L': (-3, 0), 'R': (3, 0)},   # left (near) leg forward
    'pass_after_L': {'L': (0, 0), 'R': (1, 2)},   # right leg swinging through
    'R': {'L': (3, 0), 'R': (-3, 0)},
    'pass_after_R': {'L': (1, 2), 'R': (0, 0)},
}
SIDE_CYCLE = ['L', 'pass_after_L', 'R', 'pass_after_R']


def _side_left(step):
    c = Canvas(W, H)
    hip_x, hip_y = 7.5, 16.5
    pose = SIDE_LEGS[step]

    def leg(side, near):
        dx, lift = pose[side]
        tag = 'leg_' + side
        col = P.PANTS if near else P.PANTS_SH
        fx, fy = hip_x + dx, 20.5 - lift
        if lift:
            # bent knee while swinging through
            c.line(hip_x, hip_y, hip_x - 1, 18.5, col, 2.2, tag)
            c.line(hip_x - 1, 18.5, fx, fy, col, 2.0, tag)  # shin
        else:
            c.line(hip_x, hip_y, fx, fy, col, 2.2, tag)
        bx = int(round(fx - 2))
        by = int(round(fy)) - 0
        boot_col = P.BOOT_LT if near else P.BOOT
        c.rect(bx, by, 3, 1, boot_col, tag)
        c.rect(bx, by + 1, 3, 1, P.BOOT, tag)

    def arm(side, near):
        # left leg forward -> left arm back
        dx = 0
        if step == 'L':
            dx = 3 if side == 'L' else -3
        elif step == 'R':
            dx = -3 if side == 'L' else 3
        tag = 'arm_' + side
        col = P.CAMO if near else P.CAMO_DK
        hx = 7.5 + dx
        hy = 15.2 - abs(dx) * 0.4
        c.line(7.5, 10.8, hx, hy, col, 2.0, tag)
        if near:
            c.line(7.5, 11.2, hx, hy, P.CAMO_GR, 0.9, tag)   # sleeve crease
        c.rect(int(hx) - (1 if dx < 0 else 0), int(hy) + 1, 2 if dx else 1, 1,
               P.SKIN if near else P.SKIN_SH, tag)

    # Facing left, the hunter's left side faces the camera.
    leg('R', near=False)
    arm('R', near=False)
    c.ascii(LEFT, PAL)
    for x, y in LEFT_BARREL:
        c.set(x, y, P.GUNMETAL)
    leg('L', near=True)
    arm('L', near=True)
    c.outline(P.OUTLINE)
    return c


def _swap_tags(c):
    sw = {'leg_L': 'leg_R', 'leg_R': 'leg_L', 'arm_L': 'arm_R', 'arm_R': 'arm_L'}
    for y in range(c.h):
        for x in range(c.w):
            t = c.tag[y][x]
            if t in sw:
                c.tag[y][x] = sw[t]
    return c


def walk(direction):
    """Return the 4 walk frames for 'down', 'up', 'left' or 'right'."""
    if direction in ('down', 'up'):
        return [_front_back(s, direction) for s in CYCLE]
    if direction == 'left':
        return [_side_left(s) for s in SIDE_CYCLE]
    # Facing right is the mirror image. Mirroring turns the near (left) leg
    # into the near right leg, so the tags swap sides too. The cycle order
    # stays left-forward first by starting from the 'R' frame.
    order = ['R', 'pass_after_R', 'L', 'pass_after_L']
    return [_swap_tags(_side_left(s).flipped()) for s in order]


# Which leg is forward in each frame, as designed. verify.py checks the
# rendered pixels against this.
EXPECTED = ['L', None, 'R', None]
