// Frame time of a page after it settles, on the real GPU (GPU=low: the integrated one). Usage:
//   node tools/shots/fps.mjs "/Cinemarium/lost/" [settle seconds=25] [measure seconds=6]
import { chromium } from 'playwright-core';
const [, , rel = '/Cinemarium/', settle = '25', measure = '6'] = process.argv;
const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true,
  args: ['--enable-gpu', '--use-angle=d3d11', '--enable-unsafe-webgpu', '--ignore-gpu-blocklist', process.env.GPU === 'low' ? '--force_low_power_gpu' : '--force_high_performance_gpu'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: +(process.env.DPR || 1) });
page.on('pageerror', e => console.log('pageerror', e.message));
await page.goto('http://127.0.0.1:4321' + rel, { waitUntil: 'load' });
await page.waitForFunction(() => window.__ready, null, { timeout: 120000 });
await page.waitForTimeout(+settle * 1000);
const r = await page.evaluate(s => new Promise(done => {
  const ts = []; const t0 = performance.now();
  const f = t => { ts.push(t); if (t - t0 < s * 1000) requestAnimationFrame(f); else done(ts); };
  requestAnimationFrame(f);
}), +measure);
const d = r.slice(1).map((t, i) => t - r[i]).sort((a, b) => a - b);
const q = await page.evaluate(() => window.__quality);
console.log(rel, 'rung', q.rung, 'median', d[d.length >> 1].toFixed(1), 'ms', 'p90', d[Math.floor(d.length * 0.9)].toFixed(1), 'ms', 'fps', (1000 * d.length / (r.at(-1) - r[0])).toFixed(1));
await browser.close();
