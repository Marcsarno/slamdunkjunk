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
from scipy.spatial import cKDTree

PHYS_CELL = 1.0
SURF_CELL = 0.5
ALBEDO_PX_PER_M = 10.0
MARGIN = 8.0
MAX_TEXTURE = 4096

OOB, ROUGH, FAIRWAY, GREEN, SAND, WATER, TEE, FRINGE, DEEP = range(9)
SURFACE_NAMES = ["oob", "rough", "fairway", "green", "sand", "water", "tee", "fringe", "deep_rough"]


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
        ctrl = np.asarray(spec["path"], float)
        _, ctrl_idx = self.tree.query(ctrl)
        self.width_s = self.path_s[ctrl_idx]
        self.widths = np.asarray(spec["fairway_width"], float)
        self.noise = Noise(spec.get("seed", 1))
        self.noise_fine = Noise(spec.get("seed", 1) + 7, wavelength=(5.0, 14.0))
        self.edge_noise = Noise(spec.get("seed", 1) + 3, wavelength=(9.0, 30.0))
        lo = self.path.min(axis=0)
        hi = self.path.max(axis=0)
        reach = max(self.widths) / 2 + spec["rough_width"] + spec["deep_rough_width"] + MARGIN
        self.x0, self.y0 = math.floor(lo[0] - reach), math.floor(lo[1] - reach)
        self.x1, self.y1 = math.ceil(hi[0] + reach), math.ceil(hi[1] + reach)

    # --- geometry helpers -------------------------------------------------------------------
    def path_query(self, x, y):
        d, idx = self.tree.query(np.stack([x.ravel(), y.ravel()], axis=1))
        return d.reshape(x.shape), self.path_s[idx].reshape(x.shape)

    def half_width(self, s):
        return np.interp(s, self.width_s, self.widths) / 2

    def fairway_edge(self, x, y, d, s):
        """Signed distance to the fairway edge (negative inside), with an organic wobble."""
        e = d - self.half_width(s) - 1.6 * self.edge_noise(x, y)
        start = self.spec["fairway_start"]
        e = np.where(s < start, np.maximum(e, (start - s)), e)
        tail = self.length + 6.0
        return np.where(s > tail, np.maximum(e, s - tail), e)

    # --- fields -----------------------------------------------------------------------------
    def height(self, x, y):
        sp, el = self.spec, self.spec["elevation"]
        d, s = self.path_query(x, y)
        t = smoothstep(0.0, 1.0, s / self.length)
        h = el["tee"] + (el["green"] - el["tee"]) * t
        play = self.half_width(s) + sp["rough_width"] * 0.5
        h += el["undulation"] * self.noise(x, y) * (0.6 + 0.4 * smoothstep(0, play, d))
        h += 0.12 * self.noise_fine(x, y)
        h += np.minimum(el["bank_slope"] * np.maximum(0.0, d - play) ** 1.25, 9.0)
        for m in el.get("mounds", []):
            r2 = ((x - m["center"][0]) ** 2 + (y - m["center"][1]) ** 2) / m["radius"] ** 2
            h += m["height"] * np.exp(-2.5 * r2)
        # tee box: flat pad
        tx, ty = sp["tee"]["center"]
        hw, hl = sp["tee"]["size"][0] / 2, sp["tee"]["size"][1] / 2
        q = np.maximum(np.abs(x - tx) - hw, np.abs(y - ty) - hl)
        tee_h = el["tee"] + 0.25
        h = h + (tee_h - h) * (1 - smoothstep(0.0, 4.0, q))
        # green: tilted plane, blended into the surrounds
        g = sp["green"]
        gr, _ = ellipse_r(x, y, g)
        plane = el["green"] + 0.3 + g["slope"][0] * (x - g["center"][0]) + g["slope"][1] * (y - g["center"][1])
        h = h + (plane - h) * (1 - smoothstep(1.0, 1.7, gr))
        # bunkers: bowl with a raised lip
        for b in sp["bunkers"]:
            br = kidney_r(x, y, b)
            bowl = b["depth"] * (1 - np.clip(br, 0, 1) ** 3)
            lip = 0.18 * np.exp(-((br - 1.05) / 0.12) ** 2)
            h = h - bowl + lip
        # water: shoreline falls away under the waterline
        for w in sp.get("water", []):
            wr, _ = ellipse_r(x, y, w)
            floor = w["level"] - 0.9
            h = h + (floor - h) * (1 - smoothstep(0.85, 1.25, wr))
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
        tx, ty = sp["tee"]["center"]
        out[(np.abs(x - tx) <= sp["tee"]["size"][0] / 2) & (np.abs(y - ty) <= sp["tee"]["size"][1] / 2)] = TEE
        gr, _ = ellipse_r(x, y, sp["green"])
        out[(gr < 1.22) & (out != OOB)] = FRINGE
        out[gr < 1.0] = GREEN
        for b in sp["bunkers"]:
            out[kidney_r(x, y, b) < 1.0] = SAND
        for w in sp.get("water", []):
            wr, _ = ellipse_r(x, y, w)
            out[(h < w["level"]) & (wr < 1.4)] = WATER
        return out


def grid(h, cell):
    xs = np.arange(h.x0, h.x1 + 1e-6, cell)
    ys = np.arange(h.y0, h.y1 + 1e-6, cell)
    return np.meshgrid(xs, ys)


PALETTE = {
    OOB: (34, 46, 30), ROUGH: (58, 92, 38), FAIRWAY: (104, 152, 52), GREEN: (122, 176, 62),
    SAND: (214, 186, 132), WATER: (24, 44, 58), TEE: (112, 160, 56), FRINGE: (90, 138, 48),
    DEEP: (42, 66, 32),
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
    d, s = hole.path_query(gx, gy)
    stripe = (np.floor(s / 7.0) % 2 == 0)
    fw = surf == FAIRWAY
    rgb[fw & stripe] *= 1.10
    rgb[fw & ~stripe] *= 0.90
    gr, gth = ellipse_r(gx, gy, hole.spec["green"])
    gm = surf == GREEN
    rgb[gm] *= (1.0 + 0.06 * np.sign(np.sin(gr[gm] * 14.0)))[:, None]
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


def build(spec_path, out_dir):
    spec = json.load(open(spec_path))
    os.makedirs(out_dir, exist_ok=True)
    hole = Hole(spec)
    px, py = grid(hole, PHYS_CELL)
    heights = hole.height(px, py).astype(np.float32)
    sx, sy = grid(hole, SURF_CELL)
    surface = hole.surface(sx, sy, hole.height(sx, sy))
    heights.tofile(os.path.join(out_dir, "heights.bin"))
    surface.tofile(os.path.join(out_dir, "surface.bin"))
    albedo_size = paint_albedo(hole, os.path.join(out_dir, "albedo.png"))
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
        "albedo": {"file": "albedo.png", "size": list(albedo_size)},
        "tee": [0.0, 0.0, tee_h], "pin": [pin[0], pin[1], pin_h],
        "green": gp, "length": round(hole.length, 1),
        "path": [[round(float(a), 2), round(float(b), 2)] for a, b in hole.path[::20]],
        "water": spec.get("water", []), "wind": spec.get("wind", {"min": 0, "max": 0}),
    }
    json.dump(meta, open(os.path.join(out_dir, "terrain.json"), "w"), indent=1)
    counts = {SURFACE_NAMES[k]: int((surface == k).sum()) for k in range(len(SURFACE_NAMES))}
    print(f"{spec['id']}: length {hole.length:.0f} m, grid {px.shape[1]}x{px.shape[0]}, "
          f"h {heights.min():.1f}..{heights.max():.1f} m, albedo {albedo_size}")
    print("surface cells:", counts)
    return hole, meta


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
