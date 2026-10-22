"""Pack Godot's web export for a host that caps each file (15 MB) and serves files as they are.

usage: python3 -I golf/tools/web_pack.py golf/build/web golf/build/web_host

The engine (index.wasm, ~38 MB) is shipped gzipped (~9 MB) and the game data (index.pck) in parts under
the cap. The page's own loader is untouched: a small fetch shim, run before index.js, answers Godot's
requests for index.wasm and index.pck by joining the parts and un-gzipping in the browser
(DecompressionStream), so the engine gets the same bytes it would have fetched.
Export first:  godot --headless --path golf/game --export-release "Web" ../build/web/index.html
"""
import gzip
import json
import re
import os
import shutil
import sys

PART = 12 * 1024 * 1024

src, out = sys.argv[1], sys.argv[2]
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
    'index.pck': {'parts': parts('index.pck', pck), 'gzip': False, 'type': 'application/octet-stream'},
}
for f in os.listdir(src):
    if f not in ('index.html', 'index.wasm', 'index.pck'):
        shutil.copy(os.path.join(src, f), out)

# On-screen checks while it loads, and any error in plain words instead of a blank screen (the host's
# viewer can refuse things a normal web server allows, and a phone shows no console).
checks = """<div id="diag" style="position:fixed;left:8px;right:8px;bottom:8px;z-index:9;font:13px/1.4 system-ui,sans-serif;color:#f3e6ff;background:rgba(23,13,36,.92);border:1px solid #6b4a8a;border-radius:8px;padding:8px 10px;white-space:pre-wrap;pointer-events:none"></div>
<script>
(function () {
  const box = document.getElementById('diag');
  const line = (t) => { box.textContent += (box.textContent ? '\\n' : '') + t; };
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
  fetch('index.pck.1.wasm', { method: 'HEAD' }).then((r) => line('Game files reachable: ' + (r.ok ? 'yes' : 'NO (' + r.status + ')')),
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
  const realFetch = window.fetch.bind(window);
  function joined(urls) {
    return new ReadableStream({
      async start(ctrl) {
        try {
          for (const u of urls) {
            const r = await realFetch(u);
            if (!r.ok) throw new Error(u + ': ' + r.status);
            const rd = r.body.getReader();
            for (;;) { const { done, value } = await rd.read(); if (done) break; ctrl.enqueue(value); }
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

html = open(os.path.join(src, 'index.html'), encoding='utf-8').read()
marker = '<script src="index.js"></script>'
assert marker in html
html = html.replace(marker, checks + shim + '\t\t' + marker)
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
