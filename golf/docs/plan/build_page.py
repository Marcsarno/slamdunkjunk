import base64, io, math, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage
sys.path.insert(0, "/home/user/slamdunkjunk/golf/tools")
import hole_gen as hg
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from proposal import proposal

K = 2.0  # px per metre
YD = 1.0936
BASE = {hg.OOB: (24, 38, 30), hg.DEEP: (36, 62, 40), hg.ROUGH: (52, 88, 50), hg.FAIRWAY: (118, 166, 72),
        hg.TEE: (138, 186, 84), hg.FRINGE: (104, 150, 66), hg.GREEN: (156, 204, 98), hg.SAND: (228, 210, 160),
        hg.PATH: (184, 172, 152)}


def water_rgb(theme):
    g = theme.get("water_glow", [0.35, 0.55, 1.0])
    if max(g) < 0.05:
        g = [0.35, 0.55, 1.0]
    return tuple(int(40 + 150 * c) for c in g)


def render(spec):
    h = hg.Hole(spec)
    cell = 1.0 / K
    gx, gy = hg.grid(h, cell)
    surf = h.surface(gx, gy, h.height(gx, gy))
    rgb = np.zeros(surf.shape + (3,), np.float32)
    for k, c in BASE.items():
        rgb[surf == k] = c
    rgb[surf == hg.WATER] = water_rgb(spec.get("theme", {}))
    lat, s = h.lateral(gx, gy)
    fw = np.isin(surf, [hg.FAIRWAY])
    lanes = np.where(np.floor(lat / 6.0) % 2 == 0, 1.06, 0.94)
    rgb[fw] *= lanes[fw][:, None]
    # woods: speckle the out-of-bounds so it reads as trees
    rng = np.random.default_rng(3)
    woods = surf == hg.OOB
    spots = ndimage.gaussian_filter(rng.random(surf.shape), 1.2)
    rgb[woods] *= (0.75 + 0.6 * (spots[woods] > 0.52))[:, None]
    edge = ndimage.binary_dilation(hg.surface_edges(surf), iterations=1) & (surf != hg.OOB)
    rgb[edge] *= 0.78
    img = Image.fromarray(np.clip(rgb[::-1], 0, 255).astype(np.uint8))
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    # bridges: runs of the cart path over water
    bridges = []
    if h.cart is not None:
        wet = h.surface(h.cart[:, 0:1], h.cart[:, 1:2], h.height(h.cart[:, 0:1], h.cart[:, 1:2]))[:, 0] == hg.WATER
        i = 0
        while i < len(wet):
            if wet[i]:
                j = i
                while j + 1 < len(wet) and (wet[j + 1] or wet[j + 1:j + 8].any()):
                    j += 1
                bridges.append(h.cart[max(0, i - 6):min(len(wet), j + 7)])
                i = j + 1
            else:
                i += 1
    return h, img.size, base64.b64encode(buf.getvalue()).decode(), bridges


def svg_for(p, n):
    spec = p["spec"]
    h, (w, ht), png, bridges = render(spec)
    x0, y1 = h.x0, h.y1
    def P(x, y):
        return ((x - x0) * K, (y1 - y) * K)
    def path_d(pts):
        return " ".join(("M" if i == 0 else "L") + "%.1f %.1f" % P(*q) for i, q in enumerate(pts))
    u = max(w / 250.0, ht / 640.0)          # viewBox units per screen pixel, so marks read the same size on every map
    parts = [f'<svg class="map" viewBox="0 0 {w} {ht}" style="--u:{u:.3f}" role="img" aria-label="Plan of hole {n}, {spec["name"]}">',
             f'<image href="data:image/png;base64,{png}" width="{w}" height="{ht}"/>']
    for b in bridges:
        parts.append(f'<path d="{path_d(b[::3])}" class="bridge"/>')
    parts.append(f'<path d="{path_d(p["safe"])}" class="safe" marker-end="url(#arr-safe)"/>')
    if p.get("hero"):
        parts.append(f'<path d="{path_d(p["hero"])}" class="hero" marker-end="url(#arr-hero)"/>')
    tx, ty = P(*spec["tee"]["center"])
    t = 6 * u
    parts.append(f'<rect x="{tx - t:.1f}" y="{ty - t:.1f}" width="{2 * t:.1f}" height="{2 * t:.1f}" rx="{u:.1f}" class="tee"/>')
    px, py = P(*spec["pin"])
    fh = 22 * u
    parts.append(f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{px:.1f}" y2="{py - fh:.1f}" class="pole"/>'
                 f'<path d="M{px:.1f} {py - fh:.1f} l{11 * u:.1f} {4 * u:.1f} l{-11 * u:.1f} {4 * u:.1f}z" class="flag"/>')
    for x, y, label in p["notes"]:
        lx, ly = P(x, y)
        lx = min(max(lx, 6), w - 6)
        anchor = "start" if lx < w * 0.55 else "end"
        parts.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="{3 * u:.1f}" class="pin-dot"/>'
                     f'<text x="{lx + (7 * u if anchor == "start" else -7 * u):.1f}" y="{ly + 4 * u:.1f}" text-anchor="{anchor}" class="note">{label}</text>')
    # scale bar: 50 yards
    bar = 50 / YD * K
    parts.append(f'<g class="scale"><line x1="{8 * u:.1f}" y1="{ht - 10 * u:.1f}" x2="{8 * u + bar:.1f}" y2="{ht - 10 * u:.1f}"/>'
                 f'<text x="{8 * u:.1f}" y="{ht - 15 * u:.1f}">50 yd</text></g>')
    parts.append("</svg>")
    yards = round((h.length) * YD / 5) * 5
    return "".join(parts), yards, h


def main():
    P = proposal()
    cards, rows, bars = [], [], []
    total_par, total_yd = 0, 0
    maxyd = 0
    built = []
    for i, p in enumerate(P):
        svg, yards, h = svg_for(p, i + 1)
        built.append((p, svg, yards))
        maxyd = max(maxyd, yards)
    for i, (p, svg, yards) in enumerate(built):
        n = i + 1
        total_par += p["par"]; total_yd += yards
        name = p["spec"]["name"]
        status = '<span class="chip chip-new">Redesign</span>' if p["changed"] else '<span class="chip">Keep</span>'
        cards.append(f'''
<article class="hole" id="hole-{n}">
  <div class="map-wrap">{svg}</div>
  <div class="hole-text">
    <p class="eyebrow">Hole {n} · Par {p["par"]} · {yards} yd {status}</p>
    <h3>{name}: <span>{p["title"]}</span></h3>
    <p class="question">{p["question"]}</p>
    <dl>
      <div><dt>Shape</dt><dd>{p["shape"]}</dd></div>
      <div><dt>Ground</dt><dd>{p["elevation"]}</dd></div>
      <div><dt>Hazard</dt><dd>{p["hazard"]}</dd></div>
      <div><dt>Green</dt><dd>{p["green"]}</dd></div>
      <div><dt>Landmark</dt><dd>{p["landmark"]}</dd></div>
    </dl>
    <p class="today"><strong>Compared with today:</strong> {p["today"]}</p>
  </div>
</article>''')
        rows.append(f'<tr><td class="num">{n}</td><td>{name}</td><td class="num">{p["par"]}</td><td class="num">{yards}</td>'
                    f'<td>{p["shape"]}</td><td>{p["hazard"]}</td><td>{p["green"]}</td></tr>')
        bw = yards / maxyd * 100
        bars.append(f'<div class="bar-row"><span class="bar-n">{n}</span><div class="bar par{p["par"]}" style="width:{bw:.1f}%">'
                    f'<span>{yards} yd</span></div><span class="bar-par">par {p["par"]}</span></div>')
    html = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "template.html")).read()
    html = html.replace("{{CARDS}}", "".join(cards)).replace("{{ROWS}}", "".join(rows)).replace("{{BARS}}", "".join(bars))
    html = html.replace("{{TOTAL_PAR}}", str(total_par)).replace("{{TOTAL_YD}}", f"{total_yd:,}")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "midnight_nine.html")
    open(out, "w").write(html)
    print(out, len(html) // 1024, "KB", total_par, total_yd)


main()
