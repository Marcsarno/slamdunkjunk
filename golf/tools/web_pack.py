"""Pack Godot's web export for a host that caps each file (15 MB) and serves files as they are.

usage: python3 -I golf/tools/web_pack.py golf/build/web golf/build/web_host [golf/build/web_desktop]

(tools/build_web.sh runs the whole thing.) Textures are compressed for the graphics chip, and phones
and desktops read different formats (ETC2 / S3TC), so the game data is exported twice: build/web with
the phone format and, given a third directory, its index.pck with the desktop one. The page picks the
one this device's WebGL reads, so each device downloads one.

The engine (index.wasm, ~38 MB) is shipped gzipped (~9 MB) and the game data (index.pck) in parts under
the cap. The page's own loader is untouched: a small fetch shim, run before index.js, answers Godot's
requests for index.wasm and index.pck by joining the parts and un-gzipping in the browser
(DecompressionStream), so the engine gets the same bytes it would have fetched.
Export first:  godot --headless --path golf/game --export-release "Web" ../build/web/index.html
and pack the holes left out of it (all but the first):
  godot --headless --path golf/game -s res://tools/pack_holes.gd -- --out=../build/web h02 h03 ... h09
"""
import gzip
import json
import re
import os
import shutil
import sys

PART = 12 * 1024 * 1024

src, out = sys.argv[1], sys.argv[2]
desktop = sys.argv[3] if len(sys.argv) > 3 else None
shutil.rmtree(out, ignore_errors=True)
os.makedirs(out)


def parts(name, data):
    names = []
    for i in range(0, len(data), PART):
        n = f'{name}.{i // PART}.wasm'   # served as .wasm (a type the host serves); the shim reads raw bytes
        open(os.path.join(out, n), 'wb').write(data[i:i + PART])
        names.append(n)
    return names


wasm = open(os.path.join(src, 'index.wasm'), 'rb').read()
pck = open(os.path.join(src, 'index.pck'), 'rb').read()
plan = {
    'index.wasm': {'parts': parts('index.wasm.gz', gzip.compress(wasm, 9)), 'gzip': True, 'type': 'application/wasm'},
    'index.pck': {'parts': parts('index.pck.etc2.gz', gzip.compress(pck, 6)), 'gzip': True, 'type': 'application/octet-stream'},
}
for k, v in plan.items():
    v['bytes'] = sum(os.path.getsize(os.path.join(out, n)) for n in v['parts'])
if desktop:
    dpck = open(os.path.join(desktop, 'index.pck'), 'rb').read()
    plan['index.pck@desktop'] = {'parts': parts('index.pck.s3tc.gz', gzip.compress(dpck, 6)), 'gzip': True,
                                 'type': 'application/octet-stream'}
    plan['index.pck@desktop']['bytes'] = sum(os.path.getsize(os.path.join(out, n))
                                             for n in plan['index.pck@desktop']['parts'])
for f in os.listdir(src):
    if f.startswith('hole_') and f.endswith('.pck'):
        # a hole's own pack (tools/pack_holes.gd), fetched by the game when the round reaches it;
        # hosted as .wasm like the parts above
        shutil.copy(os.path.join(src, f), os.path.join(out, f + '.wasm'))
    elif f not in ('index.html', 'index.wasm', 'index.pck'):
        shutil.copy(os.path.join(src, f), out)

# On-screen checks while it loads, and any error in plain words instead of a blank screen (the host's
# viewer can refuse things a normal web server allows, and a phone shows no console).
checks = """<div id="diag" style="position:fixed;left:8px;right:8px;bottom:8px;z-index:9;font:13px/1.4 system-ui,sans-serif;color:#f3e6ff;background:rgba(23,13,36,.92);border:1px solid #6b4a8a;border-radius:8px;padding:8px 10px;white-space:pre-wrap;pointer-events:none"></div>
<script>
(function () {
  const box = document.getElementById('diag');
  // the checks stay out of sight unless one fails (then the box shows, with what went wrong)
  box.style.display = 'none';
  const line = (t) => {
    box.textContent += (box.textContent ? '\\n' : '') + t;
    if (/NO|BLOCKED|rror|failed/.test(t)) box.style.display = 'block';
  };
  window.__diag = line;
  window.addEventListener('error', (e) => line('Error: ' + (e.message || e.type) + (e.filename ? ' (' + e.filename.split('/').pop() + ':' + e.lineno + ')' : '')));
  window.addEventListener('unhandledrejection', (e) => line('Error: ' + (e.reason && e.reason.message || e.reason)));
  line('Checking this browser...');
  try {
    const gl = document.createElement('canvas').getContext('webgl2');
    line('WebGL 2: ' + (gl ? 'yes' : 'NO (the game needs it)'));
  } catch (e) { line('WebGL 2: error ' + e.message); }
  line('Unzip (DecompressionStream): ' + (typeof DecompressionStream === 'function' ? 'yes' : 'NO'));
  if (typeof WebAssembly !== 'object') line('WebAssembly: NO (the game engine needs it)');
  else WebAssembly.instantiate(new Uint8Array([0, 97, 115, 109, 1, 0, 0, 0]))
    .then(() => line('WebAssembly: yes'), (e) => line('WebAssembly: BLOCKED - ' + e.message));
  fetch('index.pck.etc2.gz.0.wasm', { method: 'HEAD' }).then((r) => line('Game files reachable: ' + (r.ok ? 'yes' : 'NO (' + r.status + ')')),
    (e) => line('Game files reachable: NO - ' + e.message));
}());
</script>
"""

shim = """<script>
// Phones report 3x pixel density; drawing the 3D scene at that every frame costs more than it shows.
// Godot sizes its canvas from devicePixelRatio, so it sees at most 2.
(function () {
  const real = window.devicePixelRatio || 1;
  try { Object.defineProperty(window, 'devicePixelRatio', { get: () => Math.min(2, real), configurable: true }); } catch (e) {}
}());
// Godot asks for index.wasm and index.pck; they are hosted gzipped / in parts (see golf/tools/web_pack.py)
(function () {
  const PLAN = %s;
  // the game data with textures in the format this device's graphics chip reads: phones (and Macs with
  // Apple chips) ETC2, other desktops S3TC
  let etc2 = true;
  try {
    const gl = document.createElement('canvas').getContext('webgl2');
    etc2 = !gl || !!gl.getExtension('WEBGL_compressed_texture_etc');
  } catch (e) {}
  if (!etc2 && PLAN['index.pck@desktop']) PLAN['index.pck'] = PLAN['index.pck@desktop'];
  const realFetch = window.fetch.bind(window);
  // what's been downloaded, for the loading bar (window.__loaded of window.__total bytes)
  window.__loaded = 0;
  window.__total = PLAN['index.wasm'].bytes + PLAN['index.pck'].bytes;
  function joined(urls) {
    return new ReadableStream({
      async start(ctrl) {
        try {
          for (const u of urls) {
            const r = await realFetch(u);
            if (!r.ok) throw new Error(u + ': ' + r.status);
            const rd = r.body.getReader();
            for (;;) {
              const { done, value } = await rd.read();
              if (done) break;
              window.__loaded += value.length;
              ctrl.enqueue(value);
            }
          }
          ctrl.close();
        } catch (e) { ctrl.error(e); }
      },
    });
  }
  window.fetch = function (input, init) {
    const url = typeof input === 'string' ? input : (input && input.url) || '';
    const name = url.split('?')[0].split('#')[0].split('/').pop();
    const p = PLAN[name];
    if (!p) return realFetch(input, init);
    let body = joined(p.parts);
    if (p.gzip) body = body.pipeThrough(new DecompressionStream('gzip'));
    return Promise.resolve(new Response(body, { status: 200, headers: { 'Content-Type': p.type } }));
  };
}());
</script>
""" % json.dumps(plan)

# the loading screen's picture: the title art, small enough to arrive first
from PIL import Image  # noqa: E402
art = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'game', 'assets', 'ui', 'splash.png'))
bg = Image.new('RGB', art.size, (23, 13, 36))
bg.paste(art, mask=art.split()[-1] if art.mode == 'RGBA' else None)
# cut off above the art's PLAY button (it isn't one yet), fading into the page's dark purple
cut = 1350
bg = bg.crop((0, 0, art.width, cut))
fade = Image.linear_gradient('L').resize((art.width, 160))          # 0 at top -> 255 at bottom
dark = Image.new('RGB', (art.width, 160), (23, 13, 36))
bg.paste(dark, (0, cut - 160), fade)
bg.resize((art.width * 2 // 3, cut * 2 // 3), Image.LANCZOS).save(os.path.join(out, 'loading.jpg'), quality=78)

html = open(os.path.join(src, 'index.html'), encoding='utf-8').read()
marker = '<script src="index.js"></script>'
assert marker in html
loader = """<div id="loader" style="position:absolute;inset:0;z-index:0;background:#170d24 url(loading.jpg) top center/min(100%,560px) auto no-repeat">
  <div style="position:absolute;left:12%;right:12%;bottom:9%;font:600 16px/1.3 system-ui,sans-serif;color:#ffe0b8;text-align:center;text-shadow:0 1px 3px #000">
    <div id="loader-text">Lighting the jack-o'-lanterns...</div>
    <div style="margin-top:10px;height:14px;border-radius:8px;background:rgba(23,13,36,.85);border:2px solid #ff9e3d;overflow:hidden">
      <div id="loader-bar" style="height:100%;width:2%;background:linear-gradient(90deg,#ff7a1a,#ffc46b);box-shadow:0 0 12px #ff9e3d;transition:width .25s"></div>
    </div>
  </div>
</div>
<script>
(function () {
  const bar = document.getElementById('loader-bar'), text = document.getElementById('loader-text');
  const lines = ["Lighting the jack-o'-lanterns...", 'Raking the bunkers...', 'Waking the ghosts...', 'Mowing the greens by moonlight...'];
  let k = 0, t = 0;
  const tick = () => {
    if (!document.getElementById('loader')) return;
    const f = window.__total ? Math.min(1, window.__loaded / window.__total) : 0;
    bar.style.width = Math.max(2, Math.round(f * 92 + (f >= 1 ? 6 : 0))) + '%';
    if (++t % 12 === 0) k = (k + 1) % lines.length;
    text.textContent = (f >= 1 ? 'Teeing up...' : lines[k]) + '  ' + Math.round(f * 100) + '%';
    setTimeout(tick, 250);
  };
  tick();
}());
</script>
"""
html = html.replace(marker, checks + shim + '\t\t' + marker)
# the loading screen sits in Godot's status overlay (shown at once, gone when the game starts) in place of
# its plain progress bar
html = html.replace('<div id="status-notice"></div>', '<div id="status-notice"></div>\n' + loader, 1)
assert 'id="loader"' in html
html = html.replace("#status {\n\tbackground-color: #170d24;", "#status {\n\tbackground-color: #170d24;\n\tz-index: 3;", 1)
html = html.replace("\tvisibility: hidden;\n}", "\tvisibility: visible;\n}", 1)
html = html.replace("#status-progress {\n\tbottom: 10%;", "#status-progress {\n\tvisibility: hidden;\n\tbottom: 10%;", 1)
# the checks box goes once the game is running; a failure notice from Godot's loader is echoed into it
html = html.replace("setStatusMode('hidden');\n\t\t}, displayFailureNotice);",
                    "setStatusMode('hidden'); document.getElementById('diag').remove();\n\t\t}, (e) => { window.__diag('Engine failed: ' + (e && e.message || e)); displayFailureNotice(e); });")
assert "document.getElementById('diag').remove()" in html
# local.html: the full document as Godot made it (its own viewport meta), for testing on this machine
open(os.path.join(out, 'local.html'), 'w', encoding='utf-8').write(html)
# the host wraps the page in its own document (with its own viewport meta): keep Godot's title, style and
# body content only
title = re.search(r'<title>.*?</title>', html, re.S).group(0)
style = re.search(r'<style>.*?</style>', html, re.S).group(0)
body = re.search(r'<body>(.*)</body>', html, re.S).group(1)
html = (title + '\n<style>:root { color-scheme: dark; background: #170d24; } html, body { height: 100%; }</style>\n'
        + style + '\n' + body)
open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(html)
for f in sorted(os.listdir(out)):
    print(f'{os.path.getsize(os.path.join(out, f)):>10}  {f}')
