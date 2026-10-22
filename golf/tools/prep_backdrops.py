"""Turn the per-hole background paintings into game backdrops.

usage: python3 -I prep_backdrops.py <dir with midnight-golf-background-art-holes-*> <golf/game/assets/backdrops>

For each hole and each painting (a, b):
  <slug>/<v>.jpg        the painting with its moon painted out (the sky shader mirrors it to wrap
                        360 degrees, so a baked-in moon would appear more than once)
  <slug>/<v>_moon.png   the moon and its halo as a separate RGBA sprite, drawn once by the shader
  meta.json             moon position/size, fog and sky colors sampled from the painting
  <slug>/el_NN.png      the 15 elements from the atlas, trimmed, in catalog order
"""
import glob
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage

SRC, DST = sys.argv[1], sys.argv[2]


def find_moon(rgb):
    """Moon disc or crescent: seed at the brightest compact blob in the upper sky, then grow it at
    a threshold halfway between that blob and the surrounding sky so the whole shape is caught."""
    h, w, _ = rgb.shape
    lum = rgb.mean(axis=2)
    upper = np.zeros_like(lum, bool)
    upper[: int(h * 0.42)] = True
    seed = ndimage.binary_opening((lum > np.percentile(lum[upper], 99.4)) & upper, iterations=2)
    lab, n = ndimage.label(seed)
    best, best_score = None, 0
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        bh, bw = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if bh < 10 or bw < 10:
            continue
        score = (lab[sl] == i).sum() * (min(bh, bw) / max(bh, bw)) ** 2
        if score > best_score:
            best, best_score = i, score
    if not best:
        return None
    moon_l = lum[lab == best].mean()
    sky_l = np.median(lum[upper])
    grown = ndimage.binary_fill_holes(ndimage.binary_opening(lum > (moon_l + sky_l) * 0.5, iterations=1))
    glab, _ = ndimage.label(grown)
    ids = np.unique(glab[lab == best])
    ids = ids[ids > 0]
    region = np.isin(glab, ids)
    ys, xs = np.nonzero(region)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    bh, bw = y1 - y0 + 1, x1 - x0 + 1
    full = min(bh, bw) / max(bh, bw) > 0.8 and region.sum() / (np.pi * (max(bh, bw) / 2) ** 2) > 0.65
    return (x0 + x1) / 2, (y0 + y1) / 2, max(bh, bw) / 2, full


def remove_moon(rgb, moon):
    cx, cy, r, full = moon
    h, w, _ = rgb.shape
    yy, xx = np.mgrid[0:h, 0:w]
    dist = np.hypot(xx - cx, yy - cy)
    R = r * 1.5                                    # disc + inner halo
    feather = r * 0.45
    ring = (dist > R) & (dist < R + feather * 1.5)
    rf = rgb.astype(np.float32)
    best, best_err = None, np.inf
    for dx in np.arange(-6.0, 6.01, 0.25) * r:
        for dy in (-0.6 * r, -0.3 * r, 0.0, 0.3 * r, 0.6 * r):
            if abs(dx) < 3.2 * r:
                continue
            sx, sy = int(round(cx + dx)), int(round(cy + dy))
            if sx - R - 2 * feather < 0 or sx + R + 2 * feather >= w or sy - R - 2 * feather < 0 or sy + R + 2 * feather >= h:
                continue
            shifted = np.roll(np.roll(rf, -int(round(dy)), axis=0), -int(round(dx)), axis=1)
            err = np.mean((shifted[ring] - rf[ring]) ** 2)
            # avoid copying another bright object (or the moon's own glow) into the hole
            src_disc = shifted[dist < R]
            err += 4.0 * max(0.0, src_disc.mean() - rf[ring].mean()) ** 2
            if err < best_err:
                best, best_err = (int(round(dx)), int(round(dy))), err
    if best is None:
        best = (int(4 * r), 0)
    src = np.roll(np.roll(rf, -best[1], axis=0), -best[0], axis=1)
    k = np.clip((R + feather - dist) / feather, 0, 1)[..., None]
    clean = (rf * (1 - k) + src * k).astype(np.uint8)
    # the moon sprite = what the painting has over the cleaned sky, with alpha from the difference
    pad = int(r * 2.6)
    x0, y0, x1, y1 = int(max(0, cx - pad)), int(max(0, cy - pad)), int(min(w, cx + pad)), int(min(h, cy + pad))
    orig = rgb[y0:y1, x0:x1].astype(np.float32)
    base = clean[y0:y1, x0:x1].astype(np.float32)
    diff = np.clip((orig - base).max(axis=2), 0, None)
    alpha = np.clip(diff / max(1.0, np.percentile(diff, 99.5)), 0, 1)
    disc = dist[y0:y1, x0:x1] < r * 1.02
    if full:
        alpha = np.where(disc, 1.0, alpha)
    # un-premultiply so blending over a different sky gives back the painted moon
    col = np.where(alpha[..., None] > 0.02, (orig - base * (1 - alpha[..., None])) / np.maximum(alpha[..., None], 0.02), orig)
    sprite = np.dstack([np.clip(col, 0, 255), alpha * 255]).astype(np.uint8)
    return clean, sprite, (x0, y0, x1, y1)


def slice_elements(path, out_dir):
    im = Image.open(path).convert("RGBA")
    a = np.array(im)
    a[..., 3] = np.where(a[..., 3] < 20, 0, a[..., 3])
    cw, ch = im.width / 5, im.height / 3
    n = 0
    for r in range(3):
        for c in range(5):
            cell = a[int(r * ch):int((r + 1) * ch), int(c * cw):int((c + 1) * cw)]
            m = cell[..., 3] > 40
            if not m.any():
                continue
            lab, k = ndimage.label(ndimage.binary_dilation(m, iterations=4))
            sizes = ndimage.sum(m, lab, range(1, k + 1))
            keep = np.isin(lab, 1 + np.nonzero(sizes > sizes.max() * 0.05)[0])
            cell = cell.copy()
            cell[..., 3] = np.where(keep, cell[..., 3], 0)
            piece = Image.fromarray(cell)
            piece = piece.crop(piece.getchannel("A").getbbox())
            n += 1
            piece.save(os.path.join(out_dir, f"el_{n:02d}.png"), optimize=True)
    return n


meta = {}
for hole_dir in sorted(glob.glob(os.path.join(SRC, "midnight-golf-background-art-holes-*", "0*-*"))):
    slug = os.path.basename(hole_dir)
    out = os.path.join(DST, slug)
    os.makedirs(out, exist_ok=True)
    entry = {}
    for v in ("a", "b"):
        rgb = np.array(Image.open(os.path.join(hole_dir, f"background-{v}.png")).convert("RGB"))
        h, w, _ = rgb.shape
        moon = find_moon(rgb.astype(np.float32))
        info = {"size": [w, h]}
        if moon:
            clean, sprite, box = remove_moon(rgb, moon)
            Image.fromarray(sprite, "RGBA").save(os.path.join(out, f"{v}_moon.png"), optimize=True)
            info["moon"] = {"uv": [round(moon[0] / w, 4), round(moon[1] / h, 4)], "radius_px": round(moon[2], 1),
                            "full": bool(moon[3]),
                            "sprite_box_uv": [round(box[0] / w, 4), round(box[1] / h, 4), round(box[2] / w, 4), round(box[3] / h, 4)]}
        else:
            clean = rgb
        Image.fromarray(clean).save(os.path.join(out, f"{v}.jpg"), quality=90)
        info["top_color"] = [round(float(c) / 255, 3) for c in rgb[: int(h * 0.04)].reshape(-1, 3).mean(axis=0)]
        info["fog_color"] = [round(float(c) / 255, 3) for c in rgb[int(h * 0.94):].reshape(-1, 3).mean(axis=0)]
        entry[v] = info
    entry["elements"] = slice_elements(os.path.join(hole_dir, "elements.png"), out)
    meta[slug] = entry
    print(slug, {v: entry[v].get("moon", {}).get("uv") for v in ("a", "b")}, "elements", entry["elements"])
json.dump(meta, open(os.path.join(DST, "meta.json"), "w"), indent=1)
