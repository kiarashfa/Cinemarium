// Screenshot a page at desktop and/or phone size on the real GPU, and print console errors.
// Start the dev server first (npm run dev). Usage:
//   node tools/shots/shot.mjs <path> <out-name> [both|d|m] [frames=30]
//   e.g. node tools/shots/shot.mjs "/Cinemarium/?still" tower both
// Writes shots/<out-name>-d.png and -m.png. Env: BASE (default http://127.0.0.1:4321), CHROME (path to chrome.exe).
import { chromium } from 'playwright-core';
import { mkdirSync } from 'node:fs';

const [, , rel = '/Cinemarium/', name = 'shot', mode = 'both', frames = '30'] = process.argv;
const BASE = process.env.BASE || 'http://127.0.0.1:4321';
const exe = process.env.CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
mkdirSync('shots', { recursive: true });
const browser = await chromium.launch({
  executablePath: exe, headless: true,
  args: ['--enable-gpu', '--use-angle=d3d11', '--enable-unsafe-webgpu', '--force_high_performance_gpu', '--ignore-gpu-blocklist', '--enable-features=Vulkan'],
});
const sizes = { d: [1440, 900, +(process.env.DPR || 1)], m: [390, 844, 3] };
for (const tag of mode === 'both' ? ['d', 'm'] : [mode]) {
  const [w, h, dpr] = sizes[tag];
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: dpr, isMobile: tag === 'm', hasTouch: tag === 'm' });
  const page = await ctx.newPage(), log = [];
  page.on('console', m => { if (['error', 'warning'].includes(m.type())) log.push(`${m.type()}: ${m.text().slice(0, 300)}`); });
  page.on('pageerror', e => log.push('pageerror: ' + e.message));
  page.on('requestfailed', r => log.push('reqfail: ' + r.url().slice(0, 120) + ' ' + r.failure()?.errorText));
  const t0 = Date.now();
  await page.goto(BASE + rel, { waitUntil: 'load', timeout: 120000 });
  await page.waitForFunction(n => window.__ready && window.__frames >= n, +frames, { timeout: 240000 }).catch(() => log.push('timeout waiting for frames'));
  const info = await page.evaluate(() => ({ frames: window.__frames, backend: window.__backend }));
  await page.screenshot({ path: `shots/${name}-${tag}.png` });
  console.log(`${tag} ${w}x${h} backend=${info.backend} frames=${info.frames} ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  for (const l of log.slice(0, 15)) console.log('  ' + l);
  await ctx.close();
}
await browser.close();
