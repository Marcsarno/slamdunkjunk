// Drive the Swing Lab headless and save pictures.
// usage: node tools/shoot.mjs <url> <outdir> [page|sheet|hands|video]
//   page   a screenshot of the whole lab (desktop and phone width)
//   sheet  address / top / impact / finish x face-on, down the line, above (Brittany | reference)
//   hands  the four hand close-ups at the key frames and the worst trail-hand frame, worst first
//   video  face-on at the key frames: video | Brittany | reference, and the video's outline traced over her
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';

// Playwright from the global install (PLAYWRIGHT=/path/to/node_modules/playwright) or a local one
const { chromium } = createRequire(import.meta.url)(process.env.PLAYWRIGHT || 'playwright');
const [url, out, mode = 'page'] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch({
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
});
const page = await browser.newPage({ viewport: { width: 1280, height: 820 } });
// Where the CDN can't be reached (sandboxed machines), THREE_DIR points at a local copy of the same
// three@0.160.0 package and its files are served in place of cdn.jsdelivr.net.
if (process.env.THREE_DIR) {
  await page.route(/^https:\/\/cdn\.jsdelivr\.net\/npm\/three@0\.160\.0\//, async (route) => {
    const rel = route.request().url().replace(/^https:\/\/cdn\.jsdelivr\.net\/npm\/three@0\.160\.0\//, '');
    const file = path.join(process.env.THREE_DIR, rel);
    if (!fs.existsSync(file)) return route.fulfill({ status: 404, body: 'missing ' + rel });
    await route.fulfill({ status: 200, body: fs.readFileSync(file), headers: { 'content-type': 'application/javascript', 'access-control-allow-origin': '*' } });
  });
}
const logs = [];
page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') logs.push(`${m.type()}: ${m.text()}`); });
page.on('pageerror', (e) => logs.push('pageerror: ' + e.message));
await page.goto(url);
await page.waitForFunction(() => window.lab && window.lab.ready === true, null, { timeout: 180000 }).catch(() => {});
const ready = await page.evaluate(() => !!(window.lab && window.lab.ready));
console.log('ready', ready);
if (logs.length) console.log(logs.slice(0, 20).join('\n'));
// CLUB=driver|iron|putter: that club, grip solved at address, before any pictures
if (process.env.CLUB) {
  await page.evaluate((k) => window.lab.setClub(k), process.env.CLUB);
  console.log('solve', JSON.stringify(await page.evaluate(() => window.lab.solve())));
}
const save = async (name, dataUrl) => fs.writeFileSync(path.join(out, name), Buffer.from(dataUrl.split(',')[1], 'base64'));

if (mode === 'page') {
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(out, 'lab_desktop.png') });
  await page.setViewportSize({ width: 400, height: 860 });
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(out, 'lab_phone.png') });
}
if (mode === 'sheet' || mode === 'hands') {
  const keys = await page.evaluate(() => window.lab.keys());
  const scan = await page.evaluate(() => { const s = window.lab.scan(); return s && { trail: s.trail.f, leadWrist: s.leadWrist.f, trailWrist: s.trailWrist.f }; });
  console.log('keys', JSON.stringify(keys), 'worst', JSON.stringify(scan));
  const views = mode === 'sheet' ? ['face', 'dtl', 'above'] : ['hands: support side', 'hands: below', 'hands: above', 'hands: 3/4'];
  const frames = mode === 'sheet' ? Object.entries(keys).filter(([k]) => k !== 'finish' || true)
    : [['worst trail hand', scan.trail], ...Object.entries(keys).filter(([k]) => k !== 'finish')];
  for (const [label, f] of frames) {
    for (const v of views) {
      const url2 = await page.evaluate(([f2, v2]) => window.lab.shot(f2, v2, 520, 600), [f, v]);
      const nums = await page.evaluate(() => window.lab.measure());
      const name = `${mode}_${label.replace(/\W+/g, '_')}_${v.replace(/\W+/g, '_')}.png`;
      await save(name, url2);
      console.log(name, `trail ${Math.hypot(nums.trailAlong, nums.trailFace, nums.trailToe).toFixed(0)}mm`,
        `wrists L ${nums.leadFlex.toFixed(0)}/${nums.leadDev.toFixed(0)} T ${nums.trailFlex.toFixed(0)}/${nums.trailDev.toFixed(0)}`,
        `head ${nums.headY.toFixed(1)}cm`);
    }
  }
}
if (mode === 'video') {
  const keys = await page.evaluate(() => window.lab.keys());
  console.log('keys', JSON.stringify(keys));
  for (const [label, f] of Object.entries(keys)) {
    await page.evaluate(() => window.lab.setVideo({ mode: 'beside', scale: 100, dx: 0, dy: 0, nudge: 0 }));
    await save(`video_${label}_beside.png`, await page.evaluate((f2) => window.lab.shot(f2, 'face', 960, 620), f));
    const vf = await page.evaluate(() => window.lab.videoFrame());
    await page.evaluate(() => { window.lab.set('split', false); return window.lab.setVideo({ mode: 'over', line: true, opacity: 100 }); });
    await save(`video_${label}_over.png`, await page.evaluate((f2) => window.lab.shot(f2, 'face', 420, 620), f));
    await page.evaluate(() => { window.lab.set('split', true); return window.lab.setVideo({ mode: 'off' }); });
    const nums = await page.evaluate(() => window.lab.measure());
    console.log(label, 'clip frame', f, 'video frame', vf, `sole ${nums.soleY.toFixed(1)}cm`, `shaft ${nums.shaftDown.toFixed(0)}° below level`,
      `hands ahead ${nums.handsAhead.toFixed(1)}cm`, `trail fist ${Math.hypot(nums.trailAlong, nums.trailFace, nums.trailToe).toFixed(0)}mm`,
      `wrists L ${nums.leadFlex.toFixed(0)}/${nums.leadDev.toFixed(0)} T ${nums.trailFlex.toFixed(0)}/${nums.trailDev.toFixed(0)}`);
  }
}
await browser.close();
