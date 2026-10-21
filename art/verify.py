"""Leg check: reads the rendered pixels of every walk cycle and confirms the
legs alternate (left forward, pass, right forward, pass) and that arms swing
opposite to the legs. Exits non-zero on any failure.

It measures pixels, not the pose tables, so a drawing bug that leaves the
same leg in front in every frame fails the check.
"""
import sys
import hunter
import animals


def _pixels(c, tag):
    return [(x, y) for y in range(c.h) for x in range(c.w) if c.tag[y][x] == tag]


def _reach(c, tag, direction, foot_only=False):
    """How far a limb reaches in the walking direction (bigger = more forward).

    With foot_only, only the bottom two rows of the limb count: that is where
    the hoof or boot lands, which is what makes a step read as a step.
    """
    pts = _pixels(c, tag)
    if not pts:
        return None
    if foot_only and direction in ('left', 'right'):
        low = max(y for _, y in pts)
        pts = [(x, y) for x, y in pts if y >= low - 1]
    if direction == 'down':
        return max(y for _, y in pts)
    if direction == 'up':
        return -max(y for _, y in pts)
    if direction == 'left':
        return -min(x for x, _ in pts)
    if direction == 'right':
        return max(x for x, _ in pts)


def forward_leg(c, direction, a='leg_L', b='leg_R', margin=2):
    foot = not a.startswith('arm')
    ra, rb = _reach(c, a, direction, foot), _reach(c, b, direction, foot)
    if ra is None or rb is None:      # one limb fully hidden behind the body
        return None
    if ra - rb >= margin:
        return 'L'
    if rb - ra >= margin:
        return 'R'
    return None


def check_hunter():
    results = []
    ok = True
    for d in ('down', 'up', 'left', 'right'):
        frames = hunter.walk(d)
        got = [forward_leg(f, d) for f in frames]
        arms = [forward_leg(f, 'down' if d == 'up' else d, 'arm_L', 'arm_R', 1) for f in frames]
        if d == 'up':
            # from behind, a forward-swinging arm looks shorter
            arms = [{'L': 'R', 'R': 'L'}.get(a) for a in arms]
        legs_ok = got == hunter.EXPECTED
        arms_ok = all(
            (g is None and a is None) or (g is not None and a is not None and a != g)
            for g, a in zip(got, arms))
        ok &= legs_ok and arms_ok
        results.append((f'hunter {d}', got, arms, legs_ok and arms_ok))
    return ok, results


def _foot(c, tag):
    pts = _pixels(c, tag)
    low = max(y for _, y in pts)
    return min(x for x, y in pts if y >= low - 1), low


def check_quads():
    """Quadrupeds use a diagonal gait. Each leg is compared with itself
    across frames (near and far legs hang from slightly different hips):

      frame 0: FL and BR planted forward, FR and BL back
      frame 1: FR and BL lifted, swinging through
      frame 2: FR and BL planted forward, FL and BR back
      frame 3: FL and BR lifted, swinging through
    """
    ok = True
    results = []
    legs = ('FL', 'FR', 'BL', 'BR')
    for name in ('whitetail_doe', 'whitetail_buck', 'red_fox', 'black_bear', 'ghost_buck'):
        frames = animals.walk(name)
        foot = [{l: _foot(f, l) for l in legs} for f in frames]
        got = []
        # contact frames: which legs are further forward than in the other contact frame
        for a, b in ((0, 2), (2, 0)):
            fwd = {l for l in legs if foot[b][l][0] - foot[a][l][0] >= 2}
            got.append(fwd)
        # passing frames: which legs are off the ground
        lifted = []
        for f in (1, 3):
            ground = max(y for _, y in foot[f].values())
            lifted.append({l for l in legs if foot[f][l][1] <= ground - 1})
        seq = [got[0], lifted[0], got[1], lifted[1]]
        want = [{'FL', 'BR'}, {'FR', 'BL'}, {'FR', 'BL'}, {'FL', 'BR'}]
        good = seq == want
        ok &= good
        labels = [fmt(seq[0]) + ' fwd', fmt(seq[1]) + ' lifted',
                  fmt(seq[2]) + ' fwd', fmt(seq[3]) + ' lifted']
        results.append((name, labels, None, good))
    frames = animals.walk('wild_turkey')
    got = [forward_leg(f, 'left') for f in frames]
    good = got == animals.TURKEY_EXPECTED
    ok &= good
    results.append(('wild_turkey', got, None, good))
    return ok, results


def fmt(x):
    if isinstance(x, set):
        return '+'.join(sorted(x))
    return '-' if x is None else str(x)


def main():
    ok1, r1 = check_hunter()
    ok2, r2 = check_quads()
    for name, legs, arms, good in r1 + r2:
        line = f"{'PASS' if good else 'FAIL'}  {name:16s} legs: {' | '.join(fmt(g) for g in legs)}"
        if arms:
            line += f"   arms fwd: {' | '.join(fmt(a) for a in arms)}"
        print(line)
    if not (ok1 and ok2):
        sys.exit(1)
    print('All walk cycles alternate correctly.')


if __name__ == '__main__':
    main()
