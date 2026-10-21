// Drive the web build in headless Chromium.
//   node play.js <url> <outdir> '<json steps>'
// Steps: ["wait", ms] ["shot", name] ["key", code] ["hold", code, ms]
//        ["tap", x, y] (game coords, 480x270) ["reload"]
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
(async () => {
  const [url, out, stepsJson, touch] = process.argv.slice(2);
  const steps = JSON.parse(stepsJson);
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'] });
  const ctx = await browser.newContext({ viewport: { width: 960, height: 540 }, hasTouch: touch === 'touch', isMobile: false });
  const page = await ctx.newPage();
  const errors = [];
  page.on('console', m => { const t = m.text(); if (/ERROR|SCRIPT|error/i.test(t)) errors.push(t); });
  page.on('pageerror', e => errors.push(String(e)));
  await page.goto(url);
  await page.waitForFunction(() => document.querySelector('canvas') && document.querySelector('#status') && getComputedStyle(document.querySelector('#status')).visibility === 'hidden', null, { timeout: 60000 }).catch(() => {});
  const scale = 2;
  for (const s of steps) {
    const [op, a, b] = s;
    if (op === 'wait') await page.waitForTimeout(a);
    else if (op === 'shot') await page.screenshot({ path: `${out}/${a}.png` });
    else if (op === 'key') { await page.keyboard.down(a); await page.waitForTimeout(90); await page.keyboard.up(a); await page.waitForTimeout(120); }
    else if (op === 'hold') { await page.keyboard.down(a); await page.waitForTimeout(b); await page.keyboard.up(a); }
    else if (op === 'tap') { if (touch === 'touch') await page.touchscreen.tap(a * scale, b * scale); else await page.mouse.click(a * scale, b * scale); await page.waitForTimeout(150); }
    else if (op === 'reload') { await page.reload(); await page.waitForTimeout(6000); }
  }
  console.log(errors.length ? 'ERRORS:\n' + errors.join('\n') : 'no console errors');
  await browser.close();
})();
