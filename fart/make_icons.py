"""Draws the app icons (a whoopee cushion with a gas puff) into icons/. Run: python3 make_icons.py"""
from pathlib import Path

from PIL import Image, ImageDraw

MUSTARD = (243, 195, 58)
INK = (42, 21, 48)
RUBBER = (224, 54, 90)
RUBBER_DARK = (158, 28, 60)
CREAM = (255, 244, 216)
GAS = (155, 197, 61)

OUT = Path(__file__).parent / "icons"


def draw(size, art_scale):
    """art_scale is how much of the square the drawing fills (maskable icons need a wide safe margin)."""
    s = 4  # supersample, then shrink for smooth edges
    big = size * s
    img = Image.new("RGB", (big, big), MUSTARD)
    d = ImageDraw.Draw(img)
    u = big * art_scale / 240  # drawing units: the cushion is laid out on a 240-wide grid
    ox = (big - 240 * u) / 2
    oy = (big - 230 * u) / 2 + 10 * u

    def p(x, y):
        return (ox + x * u, oy + y * u)

    line = max(2, round(6 * u))
    # gas puffs, behind and below the nozzle
    for cx, cy, r in [(68, 214, 20), (104, 222, 15), (176, 214, 20), (140, 224, 13)]:
        d.ellipse([p(cx - r, cy - r), p(cx + r, cy + r)], fill=GAS, outline=INK, width=max(2, round(4 * u)))
    # nozzle
    d.polygon([p(100, 150), p(140, 150), p(150, 192), p(120, 198), p(90, 192)], fill=RUBBER, outline=INK)
    d.line([p(100, 150), p(90, 192), p(120, 198), p(150, 192), p(140, 150)], fill=INK, width=line, joint="curve")
    # body
    d.ellipse([p(12, 8), p(228, 168)], fill=RUBBER, outline=INK, width=line)
    d.ellipse([p(34, 28), p(206, 148)], outline=RUBBER_DARK, width=max(2, round(3 * u)))
    # shine
    d.ellipse([p(46, 36), p(104, 58)], fill=CREAM)
    return img.resize((size, size), Image.LANCZOS)


def main():
    OUT.mkdir(exist_ok=True)
    draw(192, 0.86).save(OUT / "icon-192.png")
    draw(512, 0.86).save(OUT / "icon-512.png")
    draw(512, 0.62).save(OUT / "icon-maskable-512.png")
    draw(180, 0.78).save(OUT / "apple-touch-icon.png")


if __name__ == "__main__":
    main()
