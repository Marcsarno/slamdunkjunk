"""Inline the spritesheets and leg-check report into pitch/index.html."""
import base64
import html
import json
import os

here = os.path.dirname(os.path.abspath(__file__))
sprites = os.path.join(here, 'sprites')
data = {}
for f in sorted(os.listdir(sprites)):
    if f.endswith('.png'):
        with open(os.path.join(sprites, f), 'rb') as fh:
            data[f[:-4]] = 'data:image/png;base64,' + base64.b64encode(fh.read()).decode()

with open(os.path.join(sprites, 'legcheck.txt')) as fh:
    report = html.escape(fh.read().strip())
report = report.replace('PASS', '<span class="ok">PASS</span>')

with open(os.path.join(here, 'template.html')) as fh:
    page = fh.read()
page = page.replace('/*SPRITES*/{}', json.dumps(data))
page = page.replace('/*LEGCHECK*/', report)
with open(os.path.join(here, 'index.html'), 'w') as fh:
    fh.write(page)
print(f'index.html: {len(page) // 1024} KB, {len(data)} sprites')
