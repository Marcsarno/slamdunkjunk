"""Leg check for the v3 Chris, read from the tagged pixels of every frame.

Contact frames (0, 2): the leading leg must be L then R.
  side views: the leading foot is the one farther in the walking direction
  front view: the leading foot is lower on screen (closer to the camera)
  back view:  the leading foot is higher on screen (farther from the camera)
Passing frames (1, 3): the lifted foot must be the leg that was behind in
the previous contact frame (it is swinging through), so R then L.
"""
import sys
sys.path.insert(0, '../v2'); sys.path.insert(0, '..')
import numpy as np
import chris3


def foot(f, tag):
    ys, xs = np.nonzero(f.tag == tag)
    low = ys.max()
    sel = ys >= low - 4
    return xs[sel].min(), xs[sel].max(), low


def leading(f, d):
    L, R = foot(f, 'leg_L'), foot(f, 'leg_R')
    if d == 'right':
        a, b = L[1], R[1]
    elif d == 'left':
        a, b = -L[0], -R[0]
    elif d == 'down':
        a, b = L[2], R[2]
    else:
        a, b = -L[2], -R[2]
    return 'L' if a - b >= 2 else ('R' if b - a >= 2 else '?')


def lifted(f):
    L, R = foot(f, 'leg_L'), foot(f, 'leg_R')
    return 'L' if R[2] - L[2] >= 2 else ('R' if L[2] - R[2] >= 2 else '?')


def main():
    ok = True
    for d in ('down', 'right', 'up', 'left'):
        fr = chris3.walk(d)
        got = [leading(fr[0], d), lifted(fr[1]), leading(fr[2], d), lifted(fr[3])]
        good = got == ['L', 'R', 'R', 'L']
        ok &= good
        print(('PASS' if good else 'FAIL'), d.ljust(5),
              'lead %s | lift %s | lead %s | lift %s' % tuple(got))
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
