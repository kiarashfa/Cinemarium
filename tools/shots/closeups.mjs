// Desktop close-up (1920x1080) of every built room's case, one PNG each: shots/closeup-<slug>.png.
// Start the dev server first (npm run dev). Usage: node tools/shots/closeups.mjs [slug ...]
// The page's text and controls are hidden so only the case shows; UI=1 keeps them.
// Env: BASE (default http://127.0.0.1:4321), CHROME (path to chrome.exe), WAIT (seconds to let the room settle, default 8), UI=1.
import { chromium } from 'playwright-core';
import { mkdirSync, readFileSync } from 'node:fs';

const BASE = process.env.BASE || 'http://127.0.0.1:4321';
const exe = process.env.CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const wait = +(process.env.WAIT || 8);

// Built rooms = titles that name a room in src/data/titles.ts.
const built = [...readFileSync('src/data/titles.ts', 'utf8').matchAll(/slug: '([^']+)'.*?room: '([^']+)'/g)].map(m => m[1]);
const slugs = process.argv.length > 2 ? process.argv.slice(2) : built;

mkdirSync('shots', { recursive: true });
const browser = await chromium.launch({
  executablePath: exe, headless: true,
  args: ['--enable-gpu', '--use-angle=d3d11', '--enable-unsafe-webgpu', '--force_high_performance_gpu', '--ignore-gpu-blocklist', '--enable-features=Vulkan'],
});
const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
for (const slug of slugs) {
  const page = await ctx.newPage(), log = [];
  page.on('pageerror', e => log.push('pageerror: ' + e.message));
  const t0 = Date.now();
  await page.goto(`${BASE}/Cinemarium/${slug}/?zoom&q=high`, { waitUntil: 'load', timeout: 120000 });
  await page.waitForFunction(() => window.__ready && window.__frames >= 60, null, { timeout: 240000 }).catch(() => log.push('timeout waiting for the room'));
  if (!process.env.UI) await page.addStyleTag({ content: 'body > *:not(#gl) { visibility: hidden !important; }' });
  await page.waitForTimeout(wait * 1000);
  const out = `shots/closeup-${slug}.png`;
  await page.screenshot({ path: out });
  const q = await page.evaluate(() => window.__quality);
  console.log(`${slug}: ${out} (${((Date.now() - t0) / 1000).toFixed(1)}s, rung ${q?.rung}, ${q?.ms?.toFixed?.(1)} ms)`, log.join(' | '));
  await page.close();
}
await browser.close();
