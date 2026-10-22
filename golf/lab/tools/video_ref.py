"""Add a swing video to the Swing Lab as a reference (to check her 3D animation against; never game art).

usage: python3 -I video_ref.py <video> <out dir, e.g. golf/lab/assets/video/driver>
       --keys address,top,impact,finish | address,p2,p3,top,p5,p6,impact,p8,p9,finish
       [--views face|face,behind] [--note text] [--json-only]

The video itself is the reference: it is copied (remuxed to .mp4, frames untouched) to <out>/ref.mp4, with
a VP9 copy (ref.webm) for browsers without H.264, and the lab seeks it to the frame that matches the clip. No frames are exported. video.json holds what the
lab needs to stand each view beside her (or trace its outline over her) at her size:
  views         one per picture in the frame, left to right: "face" (face-on, target to the right of the
                picture) and, for a side-by-side video, "behind" (from behind her back)
  per view:     x0, x1   the view's columns in the frame
                feet_x, sole_y   the middle of her shoes and the sole line at address (pinned to her feet)
                height_px        her height at address, hair to sole (scaled to her own height at address)
  bg            the background colour (the lab's outline separates her from it)
  keys          the swing positions in video frames, picked by eye one frame at a time (face-on): address,
                P2 club level going back, P3 lead arm level, top, P5 lead arm level coming down, P6 club
                level coming down, impact, P8 club level through, P9 trail arm level, finish (a putt: the
                four main ones)
--json-only rewrites video.json alone (the copies are already there).
Made so far:
  driver  Seedance two-angle driver video: --keys 0,39,57,90,111.5,115.5,120,123,126.5,186 --views face,behind
  iron    Seedance two-angle iron video:   --keys 0,43,60,96,117,122,128.5,136.5,143,190 --views face,behind
  putter  face-on putt video:              --keys 94,118,131,144
"""
import argparse
import json
import os
import subprocess
import tempfile

import numpy as np
from PIL import Image
from scipy import ndimage

ap = argparse.ArgumentParser()
ap.add_argument('video'); ap.add_argument('out')
ap.add_argument('--keys', required=True)
ap.add_argument('--views', default='face')
ap.add_argument('--note', default='')
ap.add_argument('--json-only', action='store_true')
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)

probe = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                   'stream=width,height,r_frame_rate,nb_frames', '-of', 'json', args.video],
                                  capture_output=True, text=True, check=True).stdout)['streams'][0]
n, d = probe['r_frame_rate'].split('/')
fps = round(float(n) / float(d), 3)
W, H = int(probe['width']), int(probe['height'])
vals = [float(x) for x in args.keys.split(',')]
names10 = ['address', 'p2', 'p3', 'top', 'p5', 'p6', 'impact', 'p8', 'p9', 'finish']
keys = dict(zip(names10 if len(vals) == 10 else ['address', 'top', 'impact', 'finish'], vals))
assert len(vals) in (4, 10) and vals == sorted(vals), 'keys: 4 or 10 frames, in swing order'

# the address frame, to measure where she stands (read only, nothing written)
with tempfile.TemporaryDirectory() as tmp:
    png = os.path.join(tmp, 'a.png')
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', args.video, '-vf', f"select=eq(n\\,{int(keys['address'])})",
                    '-vframes', '1', png], check=True)
    a = np.asarray(Image.open(png).convert('RGB')).astype(np.float32)

names = args.views.split(',')
c = 12
corners = np.concatenate([a[:c, :c].reshape(-1, 3), a[:c, -c:].reshape(-1, 3), a[-c:, :c].reshape(-1, 3), a[-c:, -c:].reshape(-1, 3)])
bg = np.median(corners, axis=0)
views = {}
for i, name in enumerate(names):
    x0, x1 = W * i // len(names), W * (i + 1) // len(names)
    part = a[:, x0:x1]
    fg = np.abs(part - bg).max(axis=2) > 40
    lab, k = ndimage.label(fg)
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, k + 1))
    her = lab == (1 + int(np.argmax(sizes)))
    ys = np.nonzero(her.any(axis=1))[0]
    # her shoes: the light (cream) part of her outline in the bottom fifth; the dark club head is left out
    shoe = her & (part.mean(axis=2) > 175)
    shoe[: int(H * 0.8)] = False
    sy, sx = np.nonzero(shoe)
    sole = int(np.percentile(sy, 99)) if len(sy) else int(ys.max())
    cols = np.unique(sx)
    runs = [r for r in np.split(cols, np.nonzero(np.diff(cols) > 4)[0] + 1) if len(r) > 6] if len(cols) else []
    feet = ((runs[0][0] + runs[0][-1]) / 2 + (runs[-1][0] + runs[-1][-1]) / 2) / 2 if runs else her.shape[1] / 2
    views[name] = {'x0': x0, 'x1': x1, 'feet_x': float(feet), 'sole_y': sole, 'height_px': int(sole - ys.min()),
                   'touches_top': bool(ys.min() <= 1)}

if not args.json_only:
    out_mp4 = os.path.join(args.out, 'ref.mp4')
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', args.video, '-map', '0:v:0', '-c', 'copy', '-movflags', '+faststart', out_mp4], check=True)
    # a VP9 copy for browsers without H.264 (open-source Chromium); the lab plays the .mp4 where it can
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', args.video, '-map', '0:v:0', '-c:v', 'libvpx-vp9', '-crf', '20', '-b:v', '0',
                    '-row-mt', '1', '-g', '12', os.path.join(args.out, 'ref.webm')], check=True)
meta = {'fps': fps, 'size': [W, H], 'frames': int(probe.get('nb_frames', 0) or 0), 'keys': keys, 'views': views,
        'bg': [round(float(x)) for x in bg], 'note': args.note}
json.dump(meta, open(os.path.join(args.out, 'video.json'), 'w'), indent=1)
print(json.dumps(meta))
