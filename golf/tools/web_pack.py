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

shim = """<script>
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
html = html.replace(marker, shim + '\t\t' + marker)
# the host wraps the page in its own document: keep Godot's title, style and body content only
title = re.search(r'<title>.*?</title>', html, re.S).group(0)
style = re.search(r'<style>.*?</style>', html, re.S).group(0)
body = re.search(r'<body>(.*)</body>', html, re.S).group(1)
html = (title + '\n<style>:root { color-scheme: dark; background: #170d24; } html, body { height: 100%; }</style>\n'
        + style + '\n' + body)
open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(html)
for f in sorted(os.listdir(out)):
    print(f'{os.path.getsize(os.path.join(out, f)):>10}  {f}')
