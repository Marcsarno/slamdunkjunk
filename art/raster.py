"""Tiny indexed-pixel canvas for procedural pixel art.

Everything is drawn at native sprite resolution (no downscaling), so every
pixel lands on the grid. Shapes are filled by testing pixel centers.
"""
import math
from PIL import Image


def hexc(h):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = [[None] * w for _ in range(h)]
        # Optional tag layer: lets tests ask "which part owns this pixel?"
        self.tag = [[None] * w for _ in range(h)]

    # ---- primitives -----------------------------------------------------
    def set(self, x, y, c, tag=None):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h and c is not None:
            self.px[y][x] = hexc(c) if isinstance(c, str) else c
            self.tag[y][x] = tag

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[y][x]
        return None

    def rect(self, x, y, w, h, c, tag=None):
        for yy in range(int(y), int(y + h)):
            for xx in range(int(x), int(x + w)):
                self.set(xx, yy, c, tag)

    def ellipse(self, cx, cy, rx, ry, c, tag=None, shade=None, light=None):
        """Filled ellipse. With shade/light, does simple top-left lighting."""
        for y in range(int(cy - ry - 1), int(cy + ry + 2)):
            for x in range(int(cx - rx - 1), int(cx + rx + 2)):
                nx = (x + 0.5 - cx) / rx
                ny = (y + 0.5 - cy) / ry
                d = nx * nx + ny * ny
                if d <= 1.0:
                    col = c
                    if shade and (ny > 0.38 or (nx > 0.55 and ny > 0.0)):
                        col = shade
                    elif light and ny < -0.45 and nx < 0.2:
                        col = light
                    self.set(x, y, col, tag)

    def poly(self, pts, c, tag=None):
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        for y in range(int(min(ys)) - 1, int(max(ys)) + 2):
            for x in range(int(min(xs)) - 1, int(max(xs)) + 2):
                if _inside(x + 0.5, y + 0.5, pts):
                    self.set(x, y, c, tag)

    def line(self, x0, y0, x1, y1, c, width=1.0, tag=None):
        r = width / 2.0
        for y in range(int(min(y0, y1) - r - 1), int(max(y0, y1) + r + 2)):
            for x in range(int(min(x0, x1) - r - 1), int(max(x0, x1) + r + 2)):
                if _seg_dist(x + 0.5, y + 0.5, x0, y0, x1, y1) <= r:
                    self.set(x, y, c, tag)

    def ascii(self, rows, pal, ox=0, oy=0, tag=None, tags=None):
        """Blit an ASCII grid. '.' is transparent. `tags` maps char->tag."""
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch == '.' or ch == ' ':
                    continue
                t = tags.get(ch, tag) if tags else tag
                self.set(ox + i, oy + j, pal[ch], t)

    # ---- post passes ----------------------------------------------------
    def outline(self, c, diagonal=False, tag='outline'):
        col = hexc(c)
        add = []
        nbrs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        if diagonal:
            nbrs += [(1, 1), (-1, 1), (1, -1), (-1, -1)]
        for y in range(self.h):
            for x in range(self.w):
                if self.px[y][x] is not None:
                    continue
                for dx, dy in nbrs:
                    p = self.get(x + dx, y + dy)
                    if p is not None:
                        add.append((x, y))
                        break
        for x, y in add:
            self.px[y][x] = col
            self.tag[y][x] = tag

    def flipped(self):
        out = Canvas(self.w, self.h)
        for y in range(self.h):
            out.px[y] = list(reversed(self.px[y]))
            out.tag[y] = list(reversed(self.tag[y]))
        return out

    def paste(self, other, ox, oy):
        for y in range(other.h):
            for x in range(other.w):
                p = other.px[y][x]
                if p is not None:
                    tx, ty = ox + x, oy + y
                    if 0 <= tx < self.w and 0 <= ty < self.h:
                        self.px[ty][tx] = p
                        self.tag[ty][tx] = other.tag[y][x]

    def recolor_tags(self, mapping):
        """Debug view: paint every pixel whose tag is in mapping."""
        out = Canvas(self.w, self.h)
        for y in range(self.h):
            for x in range(self.w):
                p = self.px[y][x]
                t = self.tag[y][x]
                if p is None:
                    continue
                if t in mapping:
                    out.px[y][x] = hexc(mapping[t])
                else:
                    g = int(0.3 * p[0] + 0.59 * p[1] + 0.11 * p[2])
                    g = 90 + g // 3
                    out.px[y][x] = (g, g, g, 255)
                out.tag[y][x] = t
        return out

    def image(self, scale=1):
        im = Image.new('RGBA', (self.w, self.h), (0, 0, 0, 0))
        data = [p if p is not None else (0, 0, 0, 0) for row in self.px for p in row]
        im.putdata(data)
        if scale != 1:
            im = im.resize((self.w * scale, self.h * scale), Image.NEAREST)
        return im


def _inside(x, y, pts):
    n = len(pts)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y):
            xint = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < xint:
                inside = not inside
        j = i
    return inside


def _seg_dist(px, py, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - x0) * dx + (py - y0) * dy) / L))
    qx, qy = x0 + t * dx, y0 + t * dy
    return math.hypot(px - qx, py - qy)


def sheet(frames, scale=1, pad=0, bg=None):
    """Lay canvases out left to right into one PIL image."""
    w = sum(f.w for f in frames) + pad * (len(frames) - 1)
    h = max(f.h for f in frames)
    im = Image.new('RGBA', (w * scale, h * scale), bg or (0, 0, 0, 0))
    x = 0
    for f in frames:
        im.alpha_composite(f.image(scale), (x * scale, (h - f.h) * scale))
        x += f.w + pad
    return im
