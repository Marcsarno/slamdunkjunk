"""Cut Brittany's putting stroke out of rendered videos into game frames, with a shorter backswing
than the video's (a putt's backswing barely leaves the ball).

usage: python3 -I prep_video_putt.py <video> <out_dir> --view back|face [--sheet <jpg>]

  --view back   from her side, the angle the game shows while putting (video_back_putter)
  --view face   front-on (video_putter)

The stroke is shortened without a jump: the backswing is played only until the putter head has
gone BACK_SHARE of the video's backswing, then the frames pick up again on the way down where the
head passes that same spot, and the follow-through stops when it has gone as far past the ball
(then holds). The club never leaves the picture in what's kept, so nothing is redrawn. The video's
ball (hidden behind the putter at address, rolling away after the strike) is taken out of every
frame: the game draws its own. Cutting out (backdrop, shadow, outline) is prep_video_swing.py's.
"""
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prep_video_swing as pvs  # noqa: E402

# per video: the address frame, which way the backswing takes the head (-1: toward smaller x in
# the picture), and how much of it to keep
VIEWS = {
    "back": dict(address=1, back_dir=-1, prefix="video_back_putt", set_name="video_back_putter", view="back"),
    "face": dict(address=1, back_dir=-1, prefix="video_putt", set_name="video_putter", view="face"),
}
BACK_SHARE = 0.4
FOLLOW_SHARE = 1.2           # the follow-through goes this many times the kept backswing past the ball
FPS = 24.0


def lowest_x(club):
    """The putter head's place across the picture: the middle of the club's lowest pixels."""
    ys, xs = np.nonzero(club)
    if len(xs) < 15:
        return None
    low = ys >= ys.max() - 18
    return float(xs[low].mean())


def head_x(a, bg0):
    """Where the putter head is, from the grey club pixels below her hips over places that are
    backdrop at address; None while the club hasn't left its address spot."""
    l, c = a.mean(2), a.max(2) - a.min(2)
    club = (c <= 22) & (l < 205) & (l > 30) & bg0
    club[:300] = False
    return lowest_x(club)


def her_putt(a, bg0=None):
    """Her and her putter: no backdrop, no shadow, no specks, no ball. With bg0 (the address frame's
    backdrop), anything ball-white on the ground where the backdrop was goes too: the ball, even
    touching the putter head."""
    fg = pvs.foreground(a)
    if bg0 is not None:
        whiteish = (a.mean(2) > 205) & ((a.max(2) - a.min(2)) < 30)
        cand = fg & bg0 & whiteish & (np.arange(a.shape[0])[:, None] > 540)
        lab, n = ndimage.label(cand)
        ball = np.zeros(cand.shape, bool)
        for i, sl in enumerate(ndimage.find_objects(lab)):
            h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
            if 4 <= h <= 22 and 4 <= w <= 22 and max(h, w) <= 1.8 * min(h, w):   # round: not the thin shaft
                ball |= lab == i + 1
        fg &= ~(ndimage.binary_dilation(ball, iterations=2) & bg0)
    light = (a.mean(2) >= 215) & ((a.max(2) - a.min(2)) <= 18)
    light[:pvs.FLOOR_Y] = False
    fg &= ndimage.binary_fill_holes(fg & ~light) | ~light
    lab, sizes, _ = pvs.pieces(fg)
    lum = ndimage.mean(a.mean(2), lab, range(1, len(sizes) + 1))
    # specks, and the ball: a small, bright piece on its own
    drop = [i + 1 for i in range(len(sizes)) if sizes[i] < 40 or (sizes[i] < 700 and lum[i] > 190)]
    return fg & ~np.isin(lab, drop)


def main():
    video, out = sys.argv[1], sys.argv[2]
    view = sys.argv[sys.argv.index("--view") + 1]
    sheet = sys.argv[sys.argv.index("--sheet") + 1] if "--sheet" in sys.argv else None
    cfg = VIEWS[view]
    frames = pvs.read_frames(video)
    a0 = frames[cfg["address"]]
    bg0 = (a0.mean(2) >= 240) & ((a0.max(2) - a0.min(2)) <= 12)
    d = cfg["back_dir"]
    # the club at address: grey club pixels below her hips that are backdrop once the club has swung
    # away (her tattooed legs stay put, the club doesn't)
    l0, c0 = a0.mean(2), a0.max(2) - a0.min(2)
    gone_bg = np.zeros(bg0.shape, bool)
    for n in sorted(frames)[len(frames) // 6: len(frames) // 2: 3]:
        f = frames[n]
        gone_bg |= (f.mean(2) >= 240) & ((f.max(2) - f.min(2)) <= 12)
    head0 = (c0 <= 22) & (l0 < 205) & (l0 > 30) & gone_bg
    head0[:300] = False
    x0h = lowest_x(head0)
    ns = sorted(frames)
    xh = {n: head_x(frames[n], bg0) for n in ns}
    # how far back the head is (and, negative, how far through), from where it sat at address
    back_by = {n: (d * (xh[n] - x0h) if xh[n] is not None else 0.0) for n in ns}
    through = {n: -back_by[n] for n in ns}
    # the top: the frame furthest back in the first two thirds of the video
    top = max(ns[: int(len(ns) * 0.67)], key=lambda n: back_by[n])
    reach = back_by[top]
    keep_to = reach * BACK_SHARE
    start = cfg["address"]
    moving = []
    for n in ns:
        if n <= start or back_by[n] <= 2.0:
            continue
        if back_by[n] > keep_to:
            break                                  # the rest of the backswing is left out
        moving.append(n)
    back = [start] + moving
    resume = next(n for n in ns if n > top and back_by[n] <= keep_to)
    contact = next(n for n in ns if n > resume and back_by[n] <= 2.0)
    finish = next((n for n in ns if n > contact and through[n] >= keep_to * FOLLOW_SHARE), ns[-1])
    down = [n for n in ns if resume <= n <= finish]
    x_addr = x0h
    print(f"head at x {x_addr:.0f}; top at frame {top}, {reach:.0f} px back; keep {keep_to:.0f} px: backswing "
          f"frames {back[1]}-{back[-1]}; downswing from frame {resume}, strike at {contact}, finish {finish}")

    used = sorted(set(back) | set(down))
    # outside her at address (her outline, not just white pixels: her sneakers' highlights are as
    # white as the backdrop)
    off_her = ~ndimage.binary_dilation(her_putt(a0), iterations=2)
    cut = {}
    for n in used:
        a = frames[n]
        keep = her_putt(a, off_her)
        rgba = np.zeros(a.shape[:2] + (4,), np.uint8)
        rgba[..., :3] = pvs.defringe(a, keep)
        rgba[..., 3] = keep * 255
        cut[n] = rgba
    if sheet:
        pvs.contact_sheet(cut, used, sheet)

    keep0 = her_putt(a0)
    shoes = keep0 & ~pvs.neutral(a0)
    sole = np.nonzero(shoes.any(1))[0].max()
    top_px = np.nonzero(keep0.any(1))[0].min()
    feet = np.nonzero(shoes[sole - 30:sole + 1].any(0))[0]
    anchor = ((feet.min() + feet.max()) / 2.0, float(sole))
    # the putter head at address, where the game puts its ball: the lowest of the club's pixels there
    club = (x0h, float(sole))
    body_px = int(sole - top_px)
    print("anchor", anchor, "putter head", club, "body", body_px, "px")

    frames_meta = {}
    for n in used:
        img = Image.fromarray(cut[n])
        x0, y0, x1, y1 = img.getbbox()
        img = img.crop((x0, y0, x1, y1))
        name = "%s_%02d.png" % (cfg["prefix"], n)
        img.save(os.path.join(out, name), optimize=True)
        frames_meta[str(n)] = {"file": name, "size": [img.width, img.height],
                               "anchor": [round(anchor[0] - x0, 1), round(anchor[1] - y0, 1)],
                               "height": body_px,
                               "club_head": [round(club[0] - x0, 1), round(club[1] - y0, 1)]}
    step = round(1000.0 / FPS)
    down_ms = [step] * len(down)
    down_ms[-1] = 600
    sets = {"view": cfg["view"], "body_px": body_px, "frames": frames_meta, "back": back, "down": down,
            "contact": down.index(contact), "down_ms": down_ms}
    if cfg["view"] == "face":
        sets.update({"ball_ahead_m": 0.0, "swing_cam_lead_m": 0.0})
    path = os.path.join(out, "golfer.json")
    meta = json.load(open(path)) if os.path.exists(path) else {}
    meta[cfg["set_name"]] = sets
    with open(path, "w") as f:
        json.dump(meta, f, indent=1)
    print("wrote %d frames: backswing %d, stroke %d (strike %d ms in)" % (len(used), len(back), len(down),
                                                                       sum(down_ms[:down.index(contact)])))


if __name__ == "__main__":
    main()
