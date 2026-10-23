"""Cut Brittany's swing out of rendered videos into game frames (a stand-in until the 3D avatar
arrives). Two videos, one per camera view:

  --view face   front-on, for the swing cut: the downswing from the top to the finish
  --view back   from behind, for aiming: address, and the backswing the pull scrubs through

usage: python3 -I prep_video_swing.py <video> <out_dir> --view face|back [--sheet <jpg>]

Each video is a fixed camera on a flat white backdrop, so every frame is cut on one canvas and
shares one foot anchor: she moves in the frames exactly as in the video, without sliding. Writes
<prefix>_NN.png (trimmed RGBA, each with its own size and anchor) and puts that view's sets for the
driver and iron into <out_dir>/golfer.json; the other sets there are left as they are.
Golfer.SPRITE_STYLE picks these sets ("video") or the drawn ones ("").

Per frame:
  - the background is flood-filled in from the frame edges (near-white, near-grey pixels), so white
    inside her outline (sneaker highlights) stays;
  - the video's ball and tee are taken out (the game draws its own ball);
  - where the club runs out of the picture, the shaft is carried on in a straight line to its full
    length and a club head (cut from the address frame) is put on the end.
"""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image
from scipy import ndimage

# Per video (frame numbers 1-based, as ffmpeg numbers them; club positions in video pixels at
# address: where the shaft meets her hands, where it meets the head, and the box the head sits in)
VIEWS = {
    "face": dict(
        address=1,
        top=53,             # the downswing starts at the top (49-52 are a pause up there)
        last=86,
        hold_from=76,       # from here she holds the finish: every other frame is enough
        hands0=(228.0, 340.0), hosel0=(203.0, 628.0), head_box=(176, 618, 216, 667),
        prefix="video_swing", set_prefix="video_"),
    "back": dict(
        address=1,
        top=81,             # address to the top of the backswing (then she holds it a long while)
        step=1,             # every frame: the pull scrubs through them, as smooth as the video
        hands0=(252.0, 358.0), hosel0=(372.0, 562.0), head_box=(364, 552, 432, 606),
        prefix="video_back", set_prefix="video_back_"),
}
PAD = 260                   # canvas margin around the video, for a club carried past its edge
FPS = 24.0
CLUB_DEPTH = 0.75           # a club carried past the picture's edge is drawn this share of its
                            # address length (swinging, it's foreshortened)
BALL_AHEAD_M = 0.15         # the video's ball sits about this far in front of her feet (by its
                            # height below her soles, against her height)


def read_frames(video):
    tmp = tempfile.mkdtemp()
    subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-map", "0:v:0", f"{tmp}/f%03d.png"], check=True)
    return {int(f[1:4]): np.asarray(Image.open(f"{tmp}/{f}").convert("RGB")).astype(np.int16)
            for f in sorted(os.listdir(tmp))}


FLOOR_Y = 560              # below this the backdrop's floor carries her soft shadow


def foreground(a):
    """Everything that isn't backdrop: near-white, near-grey pixels joined to the frame's edge
    (on the floor, the light grey of her shadow too), and pockets of pure backdrop her arms, legs
    or club close off. White on her (sneakers, highlights) is warmer than the backdrop and stays."""
    light = a.mean(2)
    chroma = a.max(2) - a.min(2)
    floor = np.zeros(light.shape, bool)
    floor[FLOOR_Y:] = True
    cand = ((light >= 244) & (chroma <= 10)) | (floor & (light >= 200) & (chroma <= 7))
    lab, n = ndimage.label(cand)
    edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    bg = np.isin(lab, edge[edge > 0])
    sizes = ndimage.sum(cand, lab, range(1, n + 1))
    mean_chroma = ndimage.mean(chroma, lab, range(1, n + 1))
    pockets = [i + 1 for i in range(n) if sizes[i] >= 120 and mean_chroma[i] <= 3.6]   # white on her: 4+
    # a pocket between her arms picks up a tint from her skin, like the white on her sneakers; but
    # it's above the floor and ringed by skin and shirt, where white on her is ringed by cream
    # sneaker or grey metal
    coloured = chroma > 30
    for i in range(n):
        if i + 1 in pockets or sizes[i] < 120 or mean_chroma[i] > 8:
            continue
        m = lab == i + 1
        if m[FLOOR_Y:].any() or light[m].mean() < 249:
            continue
        ring = ndimage.binary_dilation(m, iterations=4) & ~m   # past the soft edge
        if coloured[ring].mean() > 0.6:
            pockets.append(i + 1)
    return ~(bg | np.isin(lab, pockets))


def pieces(mask):
    lab, n = ndimage.label(mask, structure=np.ones((3, 3)))
    return lab, ndimage.sum(mask, lab, range(1, n + 1)), ndimage.find_objects(lab)


def ball_shape(fg):
    """The ball on its tee at address: the second-largest piece (she is the largest), a little grown."""
    lab, sizes, _ = pieces(fg)
    ball = lab == np.argsort(-sizes)[1] + 1
    return ndimage.binary_dilation(ball, iterations=3)


def her(a, a0, ball, ball_there):
    """Her and her club: no specks, no shadow on the floor, and no ball or tee while they're there."""
    fg = foreground(a)
    if ball_there:
        # the ball as it stood at address, except where something has moved over it (the club head
        # coming through)
        over = np.abs(a - a0).max(2) > 40
        if (over & ball).sum() < 0.3 * ball.sum():
            over[:] = False                      # the club isn't there: the ball goes entirely
        fg &= ~(ball & ~over)
    # her shadow on the floor is light and tinted like her sneakers: drop light floor pixels outside
    # her silhouette, keep the ones her outline encloses (sneaker panels inside their darker seams)
    light = (a.mean(2) >= 215) & ((a.max(2) - a.min(2)) <= 18)
    light[:FLOOR_Y] = False
    fg &= ndimage.binary_fill_holes(fg & ~light) | ~light
    lab, sizes, _ = pieces(fg)
    drop = [i + 1 for i in range(len(sizes)) if sizes[i] < 40]
    if ball_there:
        # the ball drifts a pixel or two near impact: any loose bit left around its spot goes too
        zone = ndimage.binary_dilation(ball, iterations=12)
        drop += [i + 1 for i in range(len(sizes)) if not (lab == i + 1)[~zone].any()]
    return fg & ~np.isin(lab, drop)


def neutral(a):
    return (a.max(2) - a.min(2)) <= 30


def club_head(a0, keep0, cfg):
    """The club head cut from the address frame, as RGBA, and the hosel's place in that image."""
    x0, y0, x1, y1 = cfg["head_box"]
    hx, hy = cfg["hosel0"]
    rgba = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
    rgba[..., :3] = a0[y0:y1, x0:x1]
    m = keep0[y0:y1, x0:x1].copy()
    m[: int(hy) - y0 - 2] = False                # just the head: no shaft above the hosel
    rgba[..., 3] = m * 255
    return Image.fromarray(rgba), (hx - x0, hy - y0)


def exit_point(keep):
    """Where the club runs off the picture, if it does: (x, y) on the edge."""
    h, w = keep.shape
    for line, at in ((keep[0], lambda v: (v, 0)), (keep[-1], lambda v: (v, h - 1)),
                     (keep[:, 0], lambda v: (0, v)), (keep[:, -1], lambda v: (w - 1, v))):
        if line.any():
            return np.array(at(float(np.nonzero(line)[0].mean())))
    return None


def shaft_colour(a0, keep0, cfg):
    """The shaft's colour at address: the median of the grey pixels within a few pixels of its middle
    stretch, between hands and head."""
    (hx, hy), (sx, sy) = cfg["hands0"], cfg["hosel0"]
    p0, d = np.array([hx, hy]), np.array([sx - hx, sy - hy])
    length = np.linalg.norm(d)
    d = d / length
    ys, xs = np.nonzero(keep0 & neutral(a0))
    rel = np.stack([xs, ys], 1) - p0
    along = rel @ d
    off = np.abs(rel @ np.array([-d[1], d[0]]))
    band = (along > 0.25 * length) & (along < 0.85 * length) & (off < 4)
    return tuple(int(v) for v in np.median(a0[ys[band], xs[band]], 0)) + (255,)


def finish_club(img, a, keep, cfg, head, head_hosel, col):
    """Carry a club that runs off the picture on to its full length and put the head on the end.
    img is the padded RGBA canvas; a and keep are the video frame and her mask."""
    e = exit_point(keep)
    if e is None:
        return img, None
    # the club: the run of grey pixels (shaft, grip) joined to the edge where it leaves; small gaps
    # in the pale, blurred shaft are bridged
    shaft = keep & neutral(a)
    body = keep & ~neutral(a)
    lab, _ = ndimage.label(ndimage.binary_dilation(shaft, iterations=1), structure=np.ones((3, 3)))
    h, w = keep.shape
    ex, ey = int(round(e[0])), int(round(e[1]))
    at_edge = lab[max(ey - 2, 0):ey + 3, max(ex - 40, 0):ex + 41] if ey in (0, h - 1) else \
        lab[max(ey - 40, 0):ey + 41, max(ex - 2, 0):ex + 3]
    ids = np.unique(at_edge[at_edge > 0])
    club = np.isin(lab, ids) & shaft
    ys, xs = np.nonzero(club)
    if len(xs) < 20:
        return img, None
    pts = np.stack([xs, ys], 1).astype(float)
    centre = np.array([np.nonzero(body)[1].mean(), np.nonzero(body)[0].mean()])
    # its visible tip: the club pixel on the picture's border furthest from her
    border = (xs <= 1) | (xs >= w - 2) | (ys <= 1) | (ys >= h - 2)
    if not border.any():
        return img, None
    tips = pts[border]
    e = tips[np.argmax(np.linalg.norm(tips - centre, axis=1))]
    # her hands: where the club meets her, nearest the tip
    touch = club & ndimage.binary_dilation(body, iterations=3)
    if not touch.any():
        raise SystemExit("couldn't find her hands on the club")
    ty, tx = np.nonzero(touch)
    tp = np.stack([tx, ty], 1).astype(float)
    hands = tp[np.argmin(np.linalg.norm(tp - e, axis=1))]
    d = (e - hands) / np.linalg.norm(e - hands)
    near = np.linalg.norm(pts - e, axis=1) < 40
    # the club carried on is drawn shorter than at address: swinging, it points partly toward or away
    # from the camera, so it looks shorter than it is. Never shorter than what the video shows.
    (hx, hy), (sx, sy) = cfg["hands0"], cfg["hosel0"]
    shaft_len = CLUB_DEPTH * np.hypot(sx - hx, sy - hy)
    hosel = hands + d * max(shaft_len, np.linalg.norm(e - hands))
    # one straight shaft from her hands to the head: the video's blurred, broken shaft past her hands
    # is cleared and the line drawn over the whole length
    stray = (pts - hands) @ d > 6
    arr = np.array(img)
    arr[ys[stray] + PAD, xs[stray] + PAD, 3] = 0
    img = Image.fromarray(arr)
    from PIL import ImageDraw
    p0 = hands + d * 6 + PAD
    p1 = hosel + PAD
    ImageDraw.Draw(img).line([tuple(p0), tuple(p1)], fill=col, width=4)
    # head: turned so its hosel's shaft lines up with this shaft
    d0 = np.array([sx - hx, sy - hy])
    turn = np.degrees(np.arctan2(d0[1], d0[0]) - np.arctan2(d[1], d[0]))
    big = Image.new("RGBA", (head.width * 3, head.height * 3))
    off = (head.width, head.height)
    big.paste(head, off)
    pivot = (off[0] + head_hosel[0], off[1] + head_hosel[1])
    rot = big.rotate(turn, resample=Image.BICUBIC, center=pivot)
    img.alpha_composite(rot, (int(round(p1[0] - pivot[0])), int(round(p1[1] - pivot[1]))))
    return img, (hands, hosel)


def defringe(a, keep):
    """Her outline's pixels are blended with the white backdrop, a pale halo on the dark course:
    give each edge pixel the colour just inside her outline, where it's lighter than that. The thin
    shaft has no inside to borrow from and is left as it is."""
    inner = ndimage.binary_erosion(keep, iterations=2)
    if not inner.any():
        return a
    dist, (iy, ix) = ndimage.distance_transform_edt(~inner, return_indices=True)
    src = a[iy, ix]
    edge = keep & ~inner & (dist <= 3) & (a.mean(2) > src.mean(2) + 8)
    out = a.copy()
    out[edge] = src[edge]
    return out


def ball_leaves(frames, ball, top):
    """The first frame after the top where the ball's spot is mostly backdrop again."""
    for n in sorted(frames):
        if n > top and foreground(frames[n])[ball].mean() < 0.15:
            return n
    raise SystemExit("couldn't find the frame the ball leaves")


def main():
    video, out = sys.argv[1], sys.argv[2]
    view = sys.argv[sys.argv.index("--view") + 1]
    sheet = sys.argv[sys.argv.index("--sheet") + 1] if "--sheet" in sys.argv else None
    cfg = VIEWS[view]
    frames = read_frames(video)
    address, top = cfg["address"], cfg["top"]
    a0 = frames[address]
    ball = ball_shape(foreground(a0))
    ys, xs = np.nonzero(ball)
    if view == "face":
        gone = ball_leaves(frames, ball, top)
        used = sorted({address, *range(top, cfg["hold_from"]), *range(cfg["hold_from"], cfg["last"] + 1, 2)})
    else:
        gone = top + 1                            # the backswing never reaches the ball
        used = sorted({*range(address, top, cfg["step"]), top})
    print("ball and tee at x %d-%d, y %d-%d; gone from frame %d" % (xs.min(), xs.max(), ys.min(), ys.max(), gone))

    keep0 = her(a0, a0, ball, ball_there=True)
    head = club_head(a0, keep0, cfg)
    col = shaft_colour(a0, keep0, cfg)       # one colour for every carried-on shaft, so it doesn't flicker
    print("shaft colour", col)
    cut = {}
    for n in used:
        a = frames[n]
        keep = her(a, a0, ball, ball_there=n < gone)
        h, w = keep.shape
        rgba = np.zeros((h + 2 * PAD, w + 2 * PAD, 4), np.uint8)
        rgba[PAD:PAD + h, PAD:PAD + w, :3] = defringe(a, keep)
        rgba[PAD:PAD + h, PAD:PAD + w, 3] = keep * 255
        img, club = finish_club(Image.fromarray(rgba), a, keep, cfg, *head, col)
        if club:
            print("frame %d: club carried on past the edge (hands %s, head %s)" % (n, club[0].round(), club[1].round()))
        cut[n] = np.asarray(img)
    if sheet:
        contact_sheet(cut, used, sheet)

    # one foot anchor for every frame: the floor midway between her soles at address (the lowest
    # sneaker-coloured pixels; the club head can reach lower, being nearer the camera). The club head
    # at address is where the video's ball sits, so the game's ball lines up with her impact.
    keep0 = her(a0, a0, ball, ball_there=True)
    shoes = keep0 & ~neutral(a0)
    sole = np.nonzero(shoes.any(1))[0].max()
    top_px = np.nonzero(keep0.any(1))[0].min()
    feet = np.nonzero(shoes[sole - 30:sole + 1].any(0))[0]
    anchor = ((feet.min() + feet.max()) / 2.0, float(sole))
    club = (float(xs.mean()), float(sole))
    body_px = int(sole - top_px)
    print("anchor", anchor, "club head", club, "body", body_px, "px")

    frames_meta = {}
    for n in used:
        img = Image.fromarray(cut[n])
        x0, y0, x1, y1 = img.getbbox()
        img = img.crop((x0, y0, x1, y1))
        name = "%s_%02d.png" % (cfg["prefix"], n)
        img.save(os.path.join(out, name), optimize=True)
        frames_meta[str(n)] = {"file": name, "size": [img.width, img.height],
                               "anchor": [round(anchor[0] + PAD - x0, 1), round(anchor[1] + PAD - y0, 1)],
                               "height": body_px,
                               "club_head": [round(club[0] + PAD - x0, 1), round(club[1] + PAD - y0, 1)]}
    path = os.path.join(out, "golfer.json")
    meta = json.load(open(path)) if os.path.exists(path) else {}
    if view == "face":
        down = [n for n in used if n >= top]
        contact = down.index(gone - 1)            # the last frame with the ball still on the tee
        step = round(1000.0 / FPS)
        down_ms = [step if n < cfg["hold_from"] else 2 * step for n in down]
        down_ms[-1] = 600
        sets = {"view": "face", "body_px": body_px, "frames": frames_meta, "back": [address], "down": down,
                "contact": contact, "down_ms": down_ms, "ball_ahead_m": BALL_AHEAD_M, "swing_cam_lead_m": 0.0}
        print("contact at frame %d, %d ms after the top" % (gone - 1, sum(down_ms[:contact])))
    else:
        # address first, then the backswing the pull scrubs through; the swing itself is the face set's
        sets = {"view": "back", "body_px": body_px, "frames": frames_meta, "back": used, "down": [top],
                "contact": 0, "down_ms": [100]}
    for club_name in ("driver", "iron"):
        meta[cfg["set_prefix"] + club_name] = sets
    with open(path, "w") as f:
        json.dump(meta, f, indent=1)
    print("wrote %d frames" % len(used))


def contact_sheet(cut, used, path, cols=10, w=180):
    from PIL import ImageDraw
    tiles = []
    for n in used:
        im = Image.fromarray(cut[n])
        im = im.crop((PAD - 200, PAD - 200, im.width - PAD + 200, im.height - PAD + 20))
        bg = Image.new("RGBA", im.size, (40, 70, 40, 255))
        bg.alpha_composite(im)
        tiles.append(bg.convert("RGB").resize((w, int(im.height * w / im.width))))
    th = tiles[0].height + 16
    s = Image.new("RGB", (cols * w, th * ((len(tiles) + cols - 1) // cols)), (15, 15, 15))
    d = ImageDraw.Draw(s)
    for i, (n, t) in enumerate(zip(used, tiles)):
        x, y = (i % cols) * w, (i // cols) * th
        s.paste(t, (x, y + 16))
        d.text((x + 4, y + 2), str(n), fill="white")
    s.save(path, quality=86)


if __name__ == "__main__":
    main()
