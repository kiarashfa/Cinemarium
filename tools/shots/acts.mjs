// Watch who does what for a while: samples the cast's current acts every two seconds (needs the dev server).
// Usage: node tools/shots/acts.mjs "/Cinemarium/severance/" 60
import { chromium } from 'playwright-core';
const [, , rel = '/Cinemarium/severance/', secs = '60'] = process.argv;
const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true,
  args: ['--enable-gpu', '--use-angle=d3d11', '--enable-unsafe-webgpu', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
page.on('pageerror', e => console.log('pageerror', e.message));
await page.goto('http://127.0.0.1:4321' + rel + (rel.includes('?') ? '&' : '?') + 'debug', { waitUntil: 'load' });
await page.waitForFunction(() => window.__ready && window.__cast, null, { timeout: 120000 });
let last = '';
for (let s = 0; s <= +secs; s += 2) {
  const st = JSON.stringify(await page.evaluate(() => window.__cast.state()));
  if (st !== last) { console.log(String(s).padStart(3), st); last = st; }
  await page.waitForTimeout(2000);
}
await browser.close();
