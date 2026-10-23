"""Hole layout -> terrain fields shared by Blender (render mesh) and Godot (ball physics).

A hole is described once in golf/courses/holes/<id>.json (course coords, meters: x right, y
down-range, z up). This module evaluates that description on regular grids:

  heights   float32 [ny, nx] at PHYS_CELL spacing -- also the render-mesh vertex lattice, so the
            ball rests exactly on what is drawn
  surface   uint8   [ny, nx] at SURF_CELL spacing -- surface ids below
  albedo    RGB image painted from the surface + height fields (prototype look)

usage: python3 -I hole_gen.py <hole.json> <out_dir>
Writes heights.bin, surface.bin, albedo.png and terrain.json (grid metadata) into <out_dir>.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import cKDTree

PHYS_CELL = 1.0
SURF_CELL = 0.5
ALBEDO_PX_PER_M = 10.0
SPLAT_PX_PER_M = 4.0
MARGIN = 8.0
MAX_TEXTURE = 4096

OOB, ROUGH, FAIRWAY, GREEN, SAND, WATER, TEE, FRINGE, DEEP, PATH = range(10)
SURFACE_NAMES = ["oob", "rough", "fairway", "green", "sand", "water", "tee", "fringe", "deep_rough", "cart_path"]


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def catmull_rom(points, step=1.0):
    p = np.asarray(points, float)
    p = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
    out = []
    for i in range(1, len(p) - 2):
        seg = np.linalg.norm(p[i + 1] - p[i])
        n = max(2, int(seg / step))
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p[i]) + (-p[i - 1] + p[i + 1]) * t
                              + (2 * p[i - 1] - 5 * p[i] + 4 * p[i + 1] - p[i + 2]) * t2
                              + (-p[i - 1] + 3 * p[i] - 3 * p[i + 1] + p[i + 2]) * t3))
    out.append(p[-2])
    return np.array(out)


class Noise:
    """Cheap smooth 2D noise: a sum of randomly oriented sine waves (deterministic per seed)."""

    def __init__(self, seed, waves=12, wavelength=(18.0, 70.0)):
        rng = np.random.default_rng(seed)
        ang = rng.uniform(0, math.tau, waves)
        k = math.tau / rng.uniform(*wavelength, waves)
        self.kx, self.ky = np.cos(ang) * k, np.sin(ang) * k
        self.ph = rng.uniform(0, math.tau, waves)
        self.norm = 1.0 / math.sqrt(waves / 2)

    def __call__(self, x, y):
        v = np.zeros_like(x)
        for kx, ky, ph in zip(self.kx, self.ky, self.ph):
            v += np.sin(x * kx + y * ky + ph)
        return v * self.norm


def ellipse_r(x, y, e):
    """Normalized elliptical radius (1.0 on the rim) for {'center','radius','rotation'}."""
    cx, cy = e["center"]
    rx, ry = e["radius"]
    c, s = math.cos(e.get("rotation", 0.0)), math.sin(e.get("rotation", 0.0))
    dx, dy = x - cx, y - cy
    u = (dx * c + dy * s) / rx
    v = (-dx * s + dy * c) / ry
    return np.sqrt(u * u + v * v), np.arctan2(v, u)


def kidney_r(x, y, e):
    """Bunker shape: an ellipse with a soft notch, so bunkers don't read as perfect ovals."""
    r, th = ellipse_r(x, y, e)
    return r / (1.0 - 0.18 * np.exp(-((np.angle(np.exp(1j * (th - 1.2)))) / 0.5) ** 2))


class Hole:
    def __init__(self, spec):
        self.spec = spec
        self.path = catmull_rom(spec["path"], 0.5)
        seg = np.linalg.norm(np.diff(self.path, axis=0), axis=1)
        self.path_s = np.concatenate([[0], np.cumsum(seg)])
        self.length = float(self.path_s[-1])
        self.tree = cKDTree(self.path)
        tan = np.gradient(self.path, axis=0)
        self.tangent = tan / np.linalg.norm(tan, axis=1, keepdims=True)
        ctrl = np.asarray(spec["path"], float)
        _, ctrl_idx = self.tree.query(ctrl)
        self.width_s = self.path_s[ctrl_idx]
        self.widths = np.asarray(spec["fairway_width"], float)
        # broad rolls only: wavelengths of 70-200 m keep fairway grades to a few percent
        self.noise = Noise(spec.get("seed", 1), wavelength=(70.0, 200.0))
        self.noise_fine = Noise(spec.get("seed", 1) + 7, wavelength=(5.0, 14.0))   # paint only, never height
        self.edge_noise = Noise(spec.get("seed", 1) + 3, wavelength=(9.0, 30.0))
        # ponds sit just below the local ground so their banks stay ~3:1 instead of cliffs
        for w in spec.get("water", []):
            w["level"] = None
        lo = self.path.min(axis=0)
        hi = self.path.max(axis=0)
        reach = max(self.widths) / 2 + spec["rough_width"] + spec["deep_rough_width"] + MARGIN
        self.x0, self.y0 = math.floor(lo[0] - reach), math.floor(lo[1] - reach)
        self.x1, self.y1 = math.ceil(hi[0] + reach), math.ceil(hi[1] + reach)
        for w in spec.get("water", []):
            c = np.array([[w["center"][0]]], float), np.array([[w["center"][1]]], float)
            w["level"] = round(float(self.base_height(*c)[0, 0]) + w.get("level_offset", -0.6), 3)
        self.cart = self._cart_path()

    def _cart_path(self):
        """The cart path: from beside the tee box down one side of the hole in the rough, a few metres
        off the fairway, to beside the green. spec "cart_path": {"side": 1 (right of the line) or -1,
        "offset": metres beyond the fairway edge, "width": metres, "switch": [[metres along, side], ...]
        (it crosses over there)}. Returns the centreline as dense points, or None."""
        cp = self.spec.get("cart_path")
        if not cp:
            return None
        switches = sorted(cp.get("switch", []))
        tee_hw = self.spec["tee"]["size"][0] / 2
        pts = []
        for s in np.arange(0.0, self.length, 1.0):
            side = float(cp.get("side", 1))
            for s0, sd in switches:                       # crossings ease over ~40 m
                side = side + (sd - side) * smoothstep(s0 - 20.0, s0 + 20.0, s)
            i = int(np.clip(np.searchsorted(self.path_s, s), 0, len(self.path) - 1))
            t = self.tangent[i]
            n = np.array([t[1], -t[0]])                   # right of the line of play
            off = self.half_width(s) + cp.get("offset", 6.0)
            off = tee_hw + 3.0 + (off - tee_hw - 3.0) * smoothstep(0.0, self.spec["fairway_start"], s)
            near_green = max(self.spec["green"]["radius"]) + 3.0          # it finishes beside the green
            off = off + (near_green - off) * smoothstep(self.length - 45.0, self.length - 5.0, s)
            pts.append(self.path[i] + n * side * off)
        pts = np.array(pts)
        pts = ndimage.gaussian_filter1d(pts, 6.0, axis=0, mode="nearest")
        # dense, even spacing for the distance lookups
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        acc = np.concatenate([[0], np.cumsum(seg)])
        even = np.arange(0.0, acc[-1], 0.5)
        dense = np.stack([np.interp(even, acc, pts[:, 0]), np.interp(even, acc, pts[:, 1])], axis=1)
        self.cart_tree = cKDTree(dense)
        self.cart_width = cp.get("width", 2.6)
        return dense

    def cart_distance(self, x, y):
        d, _ = self.cart_tree.query(np.stack([np.ravel(x), np.ravel(y)], axis=1))
        return d.reshape(np.shape(x))

    # --- geometry helpers -------------------------------------------------------------------
    def path_query(self, x, y):
        d, idx = self.tree.query(np.stack([x.ravel(), y.ravel()], axis=1))
        return d.reshape(x.shape), self.path_s[idx].reshape(x.shape)

    def lateral(self, x, y):
        """Signed offset from the centerline (+ = right of the line of play), and distance along it."""
        _, idx = self.tree.query(np.stack([x.ravel(), y.ravel()], axis=1))
        p = self.path[idx]
        t = self.tangent[idx]
        off = np.stack([x.ravel(), y.ravel()], axis=1) - p
        lat = off[:, 0] * t[:, 1] - off[:, 1] * t[:, 0]
        return lat.reshape(x.shape), self.path_s[idx].reshape(x.shape)

    def half_width(self, s):
        return np.interp(s, self.width_s, self.widths) / 2

    def fairway_edge(self, x, y, d, s):
        """Signed distance to the fairway edge (negative inside), with an organic wobble."""
        e = d - self.half_width(s) - 1.6 * self.edge_noise(x, y)
        start = self.spec["fairway_start"]
        e = np.where(s < start, np.maximum(e, (start - s)), e)
        tail = self.length + 6.0
        e = np.where(s > tail, np.maximum(e, s - tail), e)
        # a forced carry: no fairway over [from, to] metres along the hole (over a pond, say)
        c = self.spec.get("carry")
        if c:
            e = np.where((s > c[0]) & (s < c[1]), np.maximum(e, np.minimum(s - c[0], c[1] - s)), e)
        return e

    # --- fields -----------------------------------------------------------------------------
    BASE_CELL = 2.0
    BASE_SMOOTH = 6.0     # meters (gaussian sigma): removes seams where the nearest centerline point jumps

    def base_height(self, x, y):
        """Smoothed landform, sampled bilinearly from a cached grid."""
        if not hasattr(self, "_base"):
            pad = 20.0
            xs = np.arange(self.x0 - pad, self.x1 + pad + 1e-6, self.BASE_CELL)
            ys = np.arange(self.y0 - pad, self.y1 + pad + 1e-6, self.BASE_CELL)
            bx, by = np.meshgrid(xs, ys)
            raw = self._raw_base_height(bx, by)
            self._base = ndimage.gaussian_filter(raw, self.BASE_SMOOTH / self.BASE_CELL, mode="nearest")
            self._base_origin = (xs[0], ys[0])
        fx = (np.asarray(x, float) - self._base_origin[0]) / self.BASE_CELL
        fy = (np.asarray(y, float) - self._base_origin[1]) / self.BASE_CELL
        return ndimage.map_coordinates(self._base, [fy.ravel(), fx.ravel()], order=1, mode="nearest").reshape(np.shape(x))

    def _raw_base_height(self, x, y):
        """Landform before features: tee-to-green fall, cross tilt, broad rolls, framing banks."""
        sp, el = self.spec, self.spec["elevation"]
        lat, s = self.lateral(x, y)
        d = np.abs(lat)
        if "profile" in el:
            # an elevation profile along the line of play, [[metres from the tee, height], ...] (a ridge,
            # a shelf, a climb), in place of the even tee-to-green fall
            prof = np.array(el["profile"], float)
            h = np.interp(s, prof[:, 0], prof[:, 1])
        else:
            t = smoothstep(0.0, 1.0, s / self.length)
            h = el["tee"] + (el["green"] - el["tee"]) * t
        h += el.get("cross_tilt", 0.012) * lat                      # 1-2% fall across for drainage
        play = self.half_width(s) + sp["rough_width"] * 0.5
        rolls = el.get("roll_height", 0.45)
        h += rolls * self.noise(x, y) * (1.0 + 0.8 * smoothstep(play * 0.5, play * 1.5, d))
        # framing banks beyond the rough: smoothstep rise, steepest grade = 1.5 * H / width
        bank_h = el.get("bank_height", 3.0)
        bank_w = max(bank_h * 10.0, 20.0)                          # keeps banks under ~15%
        h += bank_h * smoothstep(play, play + bank_w, d)
        for m in el.get("mounds", []):
            hm = min(m["height"], 0.11 * m["radius"])               # gaussian max grade ~1.36 h/R -> <15%
            r2 = ((x - m["center"][0]) ** 2 + (y - m["center"][1]) ** 2) / m["radius"] ** 2
            h += hm * np.exp(-2.5 * r2)
        return h

    def height(self, x, y):
        sp, el = self.spec, self.spec["elevation"]
        h = self.base_height(x, y)
        # tee: level pad raised ~0.45 m, 3:1 sides, a hair of fall toward the front for drainage
        tx, ty = sp["tee"]["center"]
        hw, hl = sp["tee"]["size"][0] / 2, sp["tee"]["size"][1] / 2
        q = np.maximum(np.abs(x - tx) - hw, np.abs(y - ty) - hl)
        pad = float(self.base_height(np.array([[tx]], float), np.array([[ty]], float))[0, 0]) + 0.45
        pad_surface = pad - 0.005 * (y - ty)
        h = h + (pad_surface - h) * (1 - smoothstep(0.0, 2.2, q))
        # green: tilted plane (1.5-3%), pushed up slightly, falling off at <=17.5% into the surrounds
        g = sp["green"]
        gx, gy = g["center"]
        gr, _ = ellipse_r(x, y, g)
        slope = np.array(g["slope"], float)
        mag = np.linalg.norm(slope)
        if mag > 0:
            slope = slope / mag * np.clip(mag, 0.015, 0.028)
        center_h = float(self.base_height(np.array([[gx]], float), np.array([[gy]], float))[0, 0]) + 0.35
        plane = center_h + slope[0] * (x - gx) + slope[1] * (y - gy)
        r_min = min(g["radius"])
        falloff = 6.0 / r_min                                          # ~6 m apron/falloff
        h = h + (plane - h) * (1 - smoothstep(1.0, 1.0 + falloff, gr))
        # bunkers: flat sand floor, faces ~35-40%, lip raised on the side facing the tee
        for b in sp["bunkers"]:
            br = kidney_r(x, y, b)
            depth = b.get("depth", 0.45)
            bmin = min(b["radius"])
            edge_w = min(0.6, 1.5 * depth / (0.38 * bmin))              # radius fraction for the face
            h = h - depth * (1 - smoothstep(1.0 - edge_w, 1.0, br))
            toward_tee = np.clip(((ty - b["center"][1]) * (y - b["center"][1])
                                  + (tx - b["center"][0]) * (x - b["center"][0])) /
                                 (np.hypot(ty - b["center"][1], tx - b["center"][0]) * bmin + 1e-6), 0, 1)
            h = h + 0.25 * (1 - toward_tee) * np.exp(-((br - 1.12) / 0.14) ** 2)
        # water: banks fall away under the waterline. An "island" pond leaves the green and a collar
        # round it standing (an island green: the green's ground stays as built above)
        for w in sp.get("water", []):
            wr, _ = ellipse_r(x, y, w)
            floor = w["level"] - 0.7
            sink = 1 - smoothstep(0.8, 1.5, wr)
            if w.get("island"):
                sink = sink * smoothstep(1.4, 2.2, gr)
            h = h + (floor - h) * sink
        return h

    def surface(self, x, y, h):
        sp = self.spec
        d, s = self.path_query(x, y)
        edge = self.fairway_edge(x, y, d, s)
        out = np.full(x.shape, OOB, np.uint8)
        hw = self.half_width(s)
        deep_lim = hw + sp["rough_width"] + sp["deep_rough_width"] + 2.0 * self.edge_noise(y, x)
        out[d < deep_lim] = DEEP
        out[d < hw + sp["rough_width"] + 1.5 * self.edge_noise(x + 50, y)] = ROUGH
        out[edge < 0] = FAIRWAY
        # rough islands: a patch of rough inside the fairway (the fairway splits round it)
        for r in sp.get("rough_islands", []):
            ir, _ = ellipse_r(x, y, r)
            out[(ir < 1.0) & (out == FAIRWAY)] = ROUGH
        if self.cart is not None:
            out[self.cart_distance(x, y) < self.cart_width / 2] = PATH
        tx, ty = sp["tee"]["center"]
        out[(np.abs(x - tx) <= sp["tee"]["size"][0] / 2) & (np.abs(y - ty) <= sp["tee"]["size"][1] / 2)] = TEE
        gr, _ = ellipse_r(x, y, sp["green"])
        out[(gr < 1.22) & (out != OOB)] = FRINGE
        out[gr < 1.0] = GREEN
        for b in sp["bunkers"]:
            out[kidney_r(x, y, b) < 1.0] = SAND
        for w in sp.get("water", []):
            wr, _ = ellipse_r(x, y, w)
            wet = (h < w["level"]) & (wr < 1.4)
            if w.get("island"):
                wet &= gr > 1.4
            out[wet] = WATER
        return out


def grid(h, cell):
    xs = np.arange(h.x0, h.x1 + 1e-6, cell)
    ys = np.arange(h.y0, h.y1 + 1e-6, cell)
    return np.meshgrid(xs, ys)


PALETTE = {
    OOB: (34, 46, 30), ROUGH: (58, 92, 38), FAIRWAY: (104, 152, 52), GREEN: (122, 176, 62),
    SAND: (214, 186, 132), WATER: (24, 44, 58), TEE: (112, 160, 56), FRINGE: (90, 138, 48),
    DEEP: (42, 66, 32), PATH: (112, 104, 94),
}


def paint_albedo(hole, out_path):
    """Prototype ground paint: flat surface colors + mowing stripes, edges and leaf litter."""
    span = max(hole.x1 - hole.x0, hole.y1 - hole.y0)
    cell = 1.0 / min(ALBEDO_PX_PER_M, (MAX_TEXTURE - 1) / span)
    gx, gy = grid(hole, cell)
    hh = hole.height(gx, gy)
    surf = hole.surface(gx, gy, hh)
    rgb = np.zeros(gx.shape + (3,), np.float32)
    for k, c in PALETTE.items():
        rgb[surf == k] = c
    lat, s = hole.lateral(gx, gy)
    stripe = (np.floor(lat / 6.0) % 2 == 0)                       # mowed in lanes along the line of play
    fw = np.isin(surf, [FAIRWAY, TEE])
    rgb[fw & stripe] *= 1.06
    rgb[fw & ~stripe] *= 0.94
    gm = surf == GREEN
    gstripe = np.floor((gx * 0.8 + gy * 0.6) / 1.8) % 2 == 0
    rgb[gm & gstripe] *= 1.04
    rgb[gm & ~gstripe] *= 0.96
    # painted outlines where surfaces meet (the concept art has crisp, darker borders)
    edge = np.zeros(surf.shape, bool)
    for axis in (0, 1):
        dif = np.diff(surf.astype(int), axis=axis) != 0
        if axis == 0:
            edge[1:, :] |= dif
            edge[:-1, :] |= dif
        else:
            edge[:, 1:] |= dif
            edge[:, :-1] |= dif
    rgb[edge & (surf != SAND)] *= 0.72
    rgb[edge & (surf == SAND)] = (150, 112, 72)
    # value noise + fallen leaves in the rough
    rng = np.random.default_rng(hole.spec.get("seed", 1))
    n = hole.noise_fine(gx * 3.1, gy * 3.1)
    rgb *= (0.92 + 0.08 * n)[..., None]
    leafy = np.isin(surf, [ROUGH, DEEP])
    leaves = leafy & (rng.random(surf.shape) < 0.012)
    cols = np.array([(196, 86, 24), (170, 40, 30), (214, 150, 40)], np.float32)
    rgb[leaves] = cols[rng.integers(0, 3, leaves.sum())]
    sandy = surf == SAND
    rgb[sandy] *= (0.95 + 0.05 * (rng.random(sandy.sum()) > 0.5))[:, None]
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)[::-1])   # row 0 = far (max y)
    img.save(out_path)
    return img.size


GRADE_LIMITS = {  # percent; from golf architecture guidance (pin areas <=3%, surrounds <=17.5%)
    "green": 3.0, "tee": 2.0, "fairway": 6.0, "fringe": 17.5, "rough": 17.5, "deep_rough": 20.0, "sand": 45.0,
}


def slope_report(hole, px, py, heights, spec):
    gy_, gx_ = np.gradient(heights.astype(np.float64), PHYS_CELL)
    pct = np.hypot(gx_, gy_) * 100
    surf = hole.surface(px, py, heights)
    print("grade report (percent)    p50    p95    max   limit")
    worst = []
    for k, name in enumerate(SURFACE_NAMES):
        m = ndimage.binary_erosion(surf == k, iterations=1)   # interior cells only
        if name in ("oob", "water") or not m.any():
            continue
        p50, p95, mx = np.percentile(pct[m], 50), np.percentile(pct[m], 95), pct[m].max()
        lim = GRADE_LIMITS.get(name)
        flag = "" if lim is None or p95 <= lim else "  <-- over"
        if flag:
            worst.append(name)
        print(f"  {name:12s}          {p50:5.1f}  {p95:5.1f}  {mx:5.1f}  {lim}{flag}")
    pin = spec["pin"]
    near = np.hypot(px - pin[0], py - pin[1]) < 3.0
    print(f"  pin area (3 m)        max {pct[near].max():.1f}%  (limit 3.0)")
    return worst


def surface_edges(surf):
    edge = np.zeros(surf.shape, bool)
    for axis in (0, 1):
        dif = np.diff(surf.astype(int), axis=axis) != 0
        if axis == 0:
            edge[1:, :] |= dif
            edge[:-1, :] |= dif
        else:
            edge[:, 1:] |= dif
            edge[:, :-1] |= dif
    return edge


def paint_splat(hole, out_dir):
    """Texture weights for the Godot terrain shader, plus a brightness overlay.

    splat.png  R fairway (incl. tee), G green, B sand, A darkening (deep rough / out of bounds);
               rough is whatever weight is left over.
    detail.png grayscale, 128 = neutral: mowing lanes, collar ring, painted outlines at edges.
    Row 0 is the far end of the hole (max y), like an image of the hole seen from above.
    """
    cell = 1.0 / SPLAT_PX_PER_M
    gx, gy = grid(hole, cell)
    surf = hole.surface(gx, gy, hole.height(gx, gy))
    w = np.zeros(gx.shape + (4,), np.float32)
    w[..., 0] = np.isin(surf, [FAIRWAY, TEE]) + 0.75 * (surf == FRINGE)
    w[..., 1] = (surf == GREEN) + 0.25 * (surf == FRINGE)
    w[..., 2] = surf == SAND
    w[..., 3] = 0.45 * (surf == DEEP) + 0.75 * (surf == OOB) + 0.6 * (surf == WATER)
    for c in range(4):
        w[..., c] = ndimage.gaussian_filter(w[..., c], 0.6)
    # path.png: where the cart path is (the shader lays paving there)
    pm = ndimage.gaussian_filter((surf == PATH).astype(np.float32), 0.5)
    Image.fromarray(np.clip(pm[::-1] * 255, 0, 255).astype(np.uint8), "L").save(os.path.join(out_dir, "path.png"))
    lat, s = hole.lateral(gx, gy)
    det = np.full(gx.shape, 1.0, np.float32)
    lanes = np.where(np.floor(lat / 6.0) % 2 == 0, 1.07, 0.93)
    det = np.where(np.isin(surf, [FAIRWAY, TEE]), lanes, det)
    gl = np.where(np.floor((gx * 0.8 + gy * 0.6) / 1.8) % 2 == 0, 1.05, 0.95)
    det = np.where(surf == GREEN, gl, det)
    det = np.where(surf == FRINGE, 0.9, det)
    edge = ndimage.binary_dilation(surface_edges(surf), iterations=1)
    det = np.where(edge & (surf != WATER), det * 0.72, det)
    det = ndimage.gaussian_filter(det, 0.7)
    Image.fromarray(np.clip(w[::-1] * 255, 0, 255).astype(np.uint8), "RGBA").save(os.path.join(out_dir, "splat.png"))
    Image.fromarray(np.clip(det[::-1] * 128, 0, 255).astype(np.uint8), "L").save(os.path.join(out_dir, "detail.png"))
    return [int(gx.shape[1]), int(gx.shape[0])]


GROUND = {  # calm night-course palette (sRGB), tuned on the Blender style test
    OOB: (0.11, 0.18, 0.08), ROUGH: (0.19, 0.31, 0.11), DEEP: (0.14, 0.23, 0.09),
    FAIRWAY: (0.37, 0.58, 0.18), TEE: (0.38, 0.60, 0.19), FRINGE: (0.30, 0.50, 0.15),
    GREEN: (0.42, 0.65, 0.21), SAND: (0.84, 0.72, 0.50), WATER: (0.06, 0.08, 0.08),
    PATH: (0.45, 0.42, 0.38),
}
GROUND_PX_PER_M = 5.0


def paint_ground(hole, out_path):
    """Ground color for both Blender and Godot: calm surface colors, soft mowing lanes, darker
    painted outlines where surfaces meet, broad value variation. No tiling textures."""
    span = max(hole.x1 - hole.x0, hole.y1 - hole.y0)
    cell = 1.0 / min(GROUND_PX_PER_M, 2047.0 / span)
    gx, gy = grid(hole, cell)
    hh = hole.height(gx, gy)
    surf = hole.surface(gx, gy, hh)
    rgb = np.zeros(gx.shape + (3,), np.float32)
    for k, c in GROUND.items():
        rgb[surf == k] = c
    for c in range(3):
        rgb[..., c] = ndimage.gaussian_filter(rgb[..., c], 0.8)
    lat, s = hole.lateral(gx, gy)
    lanes = np.where(np.floor(lat / 5.0) % 2 == 0, 1.07, 0.93)
    fw = np.isin(surf, [FAIRWAY, TEE])
    rgb[fw] *= lanes[fw][:, None]
    gm = surf == GREEN
    gl = np.where(np.floor((gx * 0.8 + gy * 0.6) / 1.6) % 2 == 0, 1.04, 0.96)
    rgb[gm] *= gl[gm][:, None]
    edge = ndimage.binary_dilation(surface_edges(surf), iterations=1) & (surf != WATER)
    shade = np.where(edge, 0.8, 1.0)
    shade = ndimage.gaussian_filter(shade, 0.8)
    broad = 0.88 + 0.12 * hole.noise(gx * 1.7, gy * 1.7) + 0.06 * hole.noise_fine(gx, gy)
    rgb *= (shade * broad)[..., None]
    img = Image.fromarray(np.clip(rgb[::-1] * 255, 0, 255).astype(np.uint8))
    img.save(out_path, quality=90)
    return list(img.size)


def build(spec_path, out_dir, preview_dir=None):
    spec = json.load(open(spec_path))
    os.makedirs(out_dir, exist_ok=True)
    hole = Hole(spec)
    px, py = grid(hole, PHYS_CELL)
    heights = hole.height(px, py).astype(np.float32)
    sx, sy = grid(hole, SURF_CELL)
    surface = hole.surface(sx, sy, hole.height(sx, sy))
    heights.tofile(os.path.join(out_dir, "heights.bin"))
    slope_report(hole, px, py, heights, spec)
    surface.tofile(os.path.join(out_dir, "surface.bin"))
    splat_size = paint_splat(hole, out_dir)
    ground_size = paint_ground(hole, os.path.join(out_dir, "ground.jpg"))
    if preview_dir:
        os.makedirs(preview_dir, exist_ok=True)
        paint_albedo(hole, os.path.join(preview_dir, "albedo.png"))
    gp = spec["green"]
    pin = spec["pin"]
    pin_h = float(hole.height(np.array([[pin[0]]], float), np.array([[pin[1]]], float))[0, 0])
    tee_h = float(hole.height(np.array([[0.0]]), np.array([[0.0]]))[0, 0])
    meta = {
        "id": spec["id"], "name": spec["name"], "number": spec["number"], "par": spec["par"],
        "origin": [hole.x0, hole.y0], "extent": [hole.x1, hole.y1],
        "phys": {"cell": PHYS_CELL, "nx": int(px.shape[1]), "ny": int(px.shape[0]), "file": "heights.bin"},
        "surf": {"cell": SURF_CELL, "nx": int(sx.shape[1]), "ny": int(sx.shape[0]), "file": "surface.bin",
                 "names": SURFACE_NAMES},
        "splat": {"file": "splat.png", "detail": "detail.png", "path": "path.png", "size": splat_size},
        "ground": {"file": "ground.jpg", "size": ground_size},
        "theme": spec.get("theme", {}),
        "tee": [0.0, 0.0, tee_h], "pin": [pin[0], pin[1], pin_h],
        "green": gp, "length": round(hole.length, 1),
        "path": [[round(float(a), 2), round(float(b), 2)] for a, b in hole.path[::20]],
        "water": spec.get("water", []), "wind": spec.get("wind", {"min": 0, "max": 0}),
    }
    if hole.cart is not None:
        meta["cart_path"] = [[round(float(a), 2), round(float(b), 2)] for a, b in hole.cart[::4]]
    json.dump(meta, open(os.path.join(out_dir, "terrain.json"), "w"), indent=1)
    counts = {SURFACE_NAMES[k]: int((surface == k).sum()) for k in range(len(SURFACE_NAMES))}
    print(f"{spec['id']}: length {hole.length:.0f} m, grid {px.shape[1]}x{px.shape[0]}, "
          f"h {heights.min():.1f}..{heights.max():.1f} m, splat {splat_size}")
    print("surface cells:", counts)
    return hole, meta


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
