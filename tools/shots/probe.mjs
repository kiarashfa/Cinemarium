// Load a page with ?debug on the real GPU, wait for frames, then run a JS expression against window.__scene.
// The expression may await (it runs inside an async function). Usage: node tools/shots/probe.mjs "/Cinemarium/severance/?still" "<js expression using s = scene>"
import { chromium } from 'playwright-core';
const [, , rel, expr] = process.argv;
const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true,
  args: ['--enable-gpu', '--use-angle=d3d11', '--enable-unsafe-webgpu', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.on('console', m => { if (m.type() === 'error') console.log('console error:', m.text().slice(0, 300)); });
await page.goto('http://127.0.0.1:4321' + rel + (rel.includes('?') ? '&' : '?') + 'debug', { waitUntil: 'load' });
await page.waitForFunction(() => window.__ready && window.__frames > 20, null, { timeout: 120000 });
console.log(await page.evaluate(new Function(`const s = window.__scene; return (async () => JSON.stringify(await (async () => { ${expr} })(), null, 1))();`)));   // the expression may be async
if (process.env.SHOT) { await page.waitForTimeout(1500); await page.screenshot({ path: process.env.SHOT }); console.log('shot', process.env.SHOT); }
await browser.close();
