"""v2 battle screen: layered backdrop with atmospheric depth, big buck,
over-the-shoulder Chris, and the HUD drawn at screen resolution."""
import math
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from px import Px, ramp, value_noise, band, clump_canopy, hx, RAMP, OUT
import buck
from buck import Draw

W, H = 480, 270
SKY_TOP, SKY_BOT = np.array([228, 196, 150]), np.array([246, 228, 190])


def haze(p, mask, amount, color=(238, 214, 178)):
    a = p.a[:, :, :3].astype(np.float32)
    a[mask] = a[mask] * (1 - amount) + np.array(color) * amount
    p.a[:, :, :3] = a.astype(np.uint8)


def tree_line(rng, y_base, height, count, scale, hz, seed):
    layer = Px(W, H)
    for i in range(count):
        x = i * (W / count) + rng.uniform(-8, 8)
        kind = rng.choice(['orange', 'red', 'gold', 'pine', 'orange'])
        cy = y_base - height * rng.uniform(0.45, 0.65)
        rx = 13 * scale * rng.uniform(0.85, 1.15)
        ry = height * 0.5
        if kind == 'pine':
            import flora
            spr, _ = flora.pine(seed + i)
            sc = max(1, int(round(height * 1.5 / spr.h * 2))) / 2
            im = spr.image()
            im = im.resize((max(1, int(spr.w * sc)), max(1, int(spr.h * sc))), Image.NEAREST)
            sp = Px(im.width, im.height)
            sp.a = np.array(im)
            layer.blit(sp, int(x - sp.w / 2), int(y_base - sp.h + 2))
        else:
            clump_canopy(layer, x, cy, rx, ry, kind, seed + i * 13, n=int(rx * ry / 10))
    m = layer.a[:, :, 3] > 0
    haze(layer, m, hz)
    return layer


def backdrop(seed=5):
    rng = random.Random(seed)
    p = Px(W, H)
    t = np.linspace(0, 1, 110)[:, None]
    p.a[:110, :, :3] = (SKY_TOP * (1 - t) + SKY_BOT * t)[:, None, :].astype(np.uint8)
    p.a[:, :, 3] = 255
    # far ridge
    for x in range(W):
        top = int(62 + 10 * math.sin(x * 0.013 + 1) + 4 * math.sin(x * 0.05))
        p.a[top:110, x, :3] = (176, 160, 156)
    p.blit(tree_line(rng, 98, 22, 26, 0.7, 0.58, seed), 0, 0)
    # meadow with perspective: marks grow and spread toward the bottom
    gy0 = 96
    big = value_noise(W, H, 90, seed)
    idx = band(big, [0.3, 0.78], dither=0.02) + 2
    for i in (2, 3, 4):
        m = (idx == i)
        m[:gy0] = False
        p.a[m] = ramp('grass', i)
    p.blit(tree_line(rng, 112, 34, 15, 1.0, 0.3, seed + 50), 0, 0)
    for y in range(116, H, 1):
        persp = (y - 110) / (H - 110)
        step = int(4 + persp * 9)
        if y % max(2, int(2 + persp * 4)):
            continue
        for x in range(rng.randrange(step), W, step):
            if rng.random() < 0.5:
                continue
            base = int(idx[y, x])
            L = 1 + int(persp * 3)
            for k in range(L):
                p.set(x, y - k, ramp('grass', max(1, base - 1) if k == 0 else min(5, base + 1)))
            p.set(x + 2, y, ramp('grass', max(1, base - 1)))
    # trampled platforms
    for cx, cy, rx, ry in ((344, 132, 78, 13), (100, 196, 118, 18)):
        yy, xx = np.mgrid[0:H, 0:W]
        d = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
        p.a[(d <= 1) & (d > 0.82)] = ramp('grass', 2)
        inner = d <= 0.82
        n = band(value_noise(W, H, 12, seed + 9), [0.45], dither=0.03)
        p.a[inner & (n == 0)] = ramp('path', 4)
        p.a[inner & (n == 1)] = ramp('path', 3)
        for _ in range(int(rx * 0.8)):
            a = rng.uniform(0, math.tau)
            r = math.sqrt(rng.random()) * 0.9
            x, y = cx + math.cos(a) * rx * r, cy + math.sin(a) * ry * r
            c = rng.choice(['orange', 'red', 'gold'])
            p.set(x, y, ramp(c, 4))
            p.set(x + 1, y, ramp(c, 2))
    return p


HAIR = ['#24170f', '#3a271c', '#523726', '#6d4c35', '#876247']
SKIN = ['#6e402d', '#a1634a', '#d4976e', '#efc19a', '#f8dbbb']
BLAZE = ['#5e220e', '#a33d14', '#df5e1a', '#fa8a35', '#ffb76d']
CAMO = ['#25261a', '#393a26', '#545335', '#727049', '#948d62']
METAL = ['#16171b', '#26292f', '#3c414b', '#5f6774', '#8992a0']
WOOD = ['#3a2214', '#59371e', '#7f512c', '#a06c3b', '#bd8a52']


def chris_back(s=4):
    d = Draw(s, pad_top=0)
    d.p = Px(int(36 * s) + 4, int(30 * s) + 4)
    d.tags = np.zeros((d.p.h, d.p.w), dtype=object)
    # rifle shouldered, pointing up-right toward the animal
    d.pal = WOOD
    d.limb((13.5, 21.0), (19.0, 17.2), 3.0, 2.4)
    d.pal = METAL
    d.limb((18.0, 17.6), (35.0, 6.4), 1.1, 0.9)
    d.limb((21.0, 14.6), (28.2, 9.8), 2.0, 2.0)
    d.limb((21.4, 14.0), (28.0, 9.4), 0.5, 0.5, col=METAL[4])
    d.ellipse((28.4, 9.8), (1.1, 1.1))
    # back and shoulders: blaze vest over camo
    d.pal = CAMO
    d.ellipse((3.6, 25.0), (3.6, 6.0))                         # near arm, hanging
    d.pal = BLAZE
    d.volume([(2.6, 31), (3.4, 22.4), (7.2, 18.6), (17.4, 18.4), (21.4, 21.2), (22.2, 31)],
             (12, 22), (11, 9))
    d.line((12.0, 19.0), (12.2, 31.0), 0.7, BLAZE[1])           # vest seam
    d.line((7.4, 19.4), (16.2, 25.6), 1.0, '#3a2a20')           # rifle sling
    # raised trigger arm
    d.pal = CAMO
    d.limb((19.8, 20.0), (24.6, 23.0), 4.4, 3.8)
    d.limb((24.4, 22.8), (20.4, 17.6), 3.6, 3.0)
    d.pal = SKIN
    d.ellipse((20.2, 17.2), (1.6, 1.3))
    # head from behind
    d.pal = SKIN
    d.ellipse((12.0, 17.4), (3.4, 2.2), bias=-0.25)             # neck
    d.ellipse((6.9, 12.8), (1.1, 1.8))                          # ears
    d.ellipse((17.2, 12.8), (1.1, 1.8), bias=-0.15)
    d.pal = HAIR
    d.ellipse((12.0, 11.0), (5.2, 5.8))
    for i in range(5):                                          # short hair texture
        d.line((9.0 + i * 1.4, 7.2 + (i % 2) * 0.6), (9.4 + i * 1.4, 9.4), 0.45, HAIR[3])
    from chris import selout
    selout(d.p)
    d.p.outline(OUT)
    return d.p


def compose(frame=0):
    p = backdrop()
    b = buck.deer(frame, 3)
    # soft contact shadow under the buck
    yy, xx = np.mgrid[0:H, 0:W]
    p.darken(((xx - 346) / 40) ** 2 + ((yy - 133) / 6) ** 2 <= 1, 0.72)
    p.blit(b, 344 - b.w // 2, 136 - b.h)
    c = chris_back(4)
    p.blit(c, 18, 202 - c.h)
    return p


def hud(img, scale=2):
    """Draw panels and text at screen resolution, like the game does."""
    W2, H2 = img.size
    d = ImageDraw.Draw(img)
    font = lambda n: ImageFont.truetype('/home/user/slamdunkjunk/game/assets/fonts/PixelifySans.ttf', n * scale)
    INK, PANEL, EDGE, MUTED = (42, 28, 22), (246, 236, 214), (107, 74, 48), (123, 93, 64)

    def panel(x, y, w, h, r=4):
        d.rounded_rectangle([x * scale + 3, y * scale + 3, (x + w) * scale + 3, (y + h) * scale + 3], r * scale, fill=(42, 28, 22, 90))
        d.rounded_rectangle([x * scale, y * scale, (x + w) * scale, (y + h) * scale], r * scale, fill=PANEL, outline=EDGE, width=2 * scale)

    def bar(x, y, w, frac, col):
        d.rounded_rectangle([x * scale, y * scale, (x + w) * scale, (y + 6) * scale], 3 * scale, fill=(74, 59, 48))
        d.rounded_rectangle([(x + 1) * scale, (y + 1) * scale, (x + 1 + (w - 2) * frac) * scale, (y + 5) * scale], 2 * scale, fill=col)

    panel(8, 8, 188, 46)
    d.text((16 * scale, 12 * scale), 'WHITETAIL BUCK', font=font(12), fill=INK)
    d.text((158 * scale, 14 * scale), '8 PT', font=font(10), fill=MUTED)
    d.text((16 * scale, 28 * scale), 'VITAL', font=font(9), fill=MUTED)
    bar(62, 29, 126, 1.0, (95, 174, 74))
    d.text((16 * scale, 39 * scale), 'SPOOK', font=font(9), fill=MUTED)
    bar(62, 40, 126, 0.32, (224, 102, 42))
    panel(286, 168, 186, 0) if False else None
    # bottom bar
    d.rectangle([0, 196 * scale, W2, H2], fill=PANEL)
    d.rectangle([0, 196 * scale, W2, 199 * scale], fill=EDGE)
    d.text((12 * scale, 205 * scale), 'A WHITETAIL BUCK steps out\nof the oaks. The wind is in\nyour favor.', font=font(11), fill=INK, spacing=4 * scale)
    d.rectangle([192 * scale, 196 * scale, 195 * scale, H2], fill=EDGE)
    labels = [('SHOOT', '88% · 10 left'), ('AIM', '3/3'), ('STALK', 'closer'), ('CALL', 'grunt tube'),
              ('FREEZE', 'calm it'), ('BRACE', 'vs charge'), ('BAG', 'items'), ('BACK OFF', 'leave')]
    for i, (a, sub) in enumerate(labels):
        x = 200 + (i % 4) * 69
        y = 202 + (i // 4) * 34
        focus = i == 0
        d.rounded_rectangle([x * scale, y * scale, (x + 66) * scale, (y + 31) * scale], 3 * scale,
                            fill=PANEL, outline=(255, 116, 23) if focus else EDGE, width=2 * scale)
        tw = d.textlength(a, font=font(10))
        d.text(((x + 33) * scale - tw / 2, (y + 4) * scale), a, font=font(10), fill=INK)
        sw = d.textlength(sub, font=font(8))
        d.text(((x + 33) * scale - sw / 2, (y + 17) * scale), sub, font=font(8), fill=MUTED)
    # Chris panel
    x, y = 290, 144
    d.rounded_rectangle([x * scale + 3, y * scale + 3, (x + 182) * scale + 3, (y + 48) * scale + 3], 4 * scale, fill=(42, 28, 22, 90))
    d.rounded_rectangle([x * scale, y * scale, (x + 182) * scale, (y + 48) * scale], 4 * scale, fill=PANEL, outline=EDGE, width=2 * scale)
    d.text(((x + 8) * scale, (y + 4) * scale), 'CHRIS', font=font(12), fill=INK)
    d.text(((x + 120) * scale, (y + 6) * scale), 'MID RANGE', font=font(9), fill=(255, 116, 23))
    d.text(((x + 8) * scale, (y + 21) * scale), 'STAMINA', font=font(9), fill=MUTED)
    bar(x + 56, y + 22, 118, 0.92, (95, 174, 74))
    d.text(((x + 8) * scale, (y + 33) * scale), 'NERVE', font=font(9), fill=MUTED)
    bar(x + 56, y + 34, 118, 0.6, (79, 138, 201))
    return img


if __name__ == '__main__':
    sys.path.insert(0, '..')
    img = compose().image(2).convert('RGB')
    hud(img).save(sys.argv[1])
