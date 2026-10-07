// The Swan's live faces. The terminal: its prompt, and the numbers as Desmond types them. The counter: 108 minutes in
// split-flap digits, counting down a second at a time, flipping back to 108:00 when he presses Enter (left alone it
// would reach zero and turn to the hieroglyphs). The mainframes: panels of blinking lamps, tape reels turning in bursts.
import { rng } from '../materials';
import type { Cast } from './performers';

interface Terminal { who: string; act: string; text: string; start: number; step: number; enter: number }
interface Live { terminal?: Terminal; [k: string]: unknown }

const FULL = 108 * 60;
/** shared by the terminal (which hears Enter) and the counter (which resets on it) */
const swan = {
  base: FULL - 15 - Math.floor(Math.random() * 240),     // the counter when the room opens: a few minutes into its run
  t0: 0, resets: 0,
};
const remaining = (t: number) => Math.max(0, swan.base - Math.floor(t - swan.t0));
if (typeof location !== 'undefined' && /[?&]debug/.test(location.search)) (window as any).__swan = { swan, remaining };

export function swanScreen(q: number) {
  if (q === 0) return terminal();
  if (q === 1) return counter();
  if (q >= 20) return reels(q);
  return lamps(q);
}

// ---------------------------------------------------------------- the terminal
function terminal() {
  const W = 512, H = 384, canvas = document.createElement('canvas'); canvas.width = W; canvas.height = H;
  const g = canvas.getContext('2d')!;
  let cast: Cast | null = null, spec: Terminal | null = null, lastAt = -1, done = false, lastLine = '', shownKey = '';
  const green = (a: number) => `rgba(110,255,140,${a})`;
  function draw(t: number) {
    let typed = '', entering = false;
    const cur = cast && spec ? cast.current(spec.who) : null;
    if (cur && spec && cur.getClip().name === spec.act && cur.getEffectiveWeight() > 0.3) {
      const at = cur.time;
      if (at < lastAt) done = false;                                  // the act began again
      lastAt = at;
      const n = Math.max(0, Math.min(spec.text.length, Math.floor((at - spec.start) / spec.step) + 1));
      typed = spec.text.slice(0, n);
      if (at >= spec.enter && !done) { done = true; lastLine = spec.text; swan.base = FULL; swan.t0 = t; swan.resets++; }
      entering = !done;
      if (done) typed = '';
    } else { lastAt = -1; done = false; }
    const blink = Math.floor(t * 2.2) % 2 === 0 || entering, key = `${lastLine}|${typed}|${blink}`;
    if (key === shownKey) return false;                                // nothing new on the screen: no upload
    shownKey = key;
    g.fillStyle = '#020604'; g.fillRect(0, 0, W, H);
    const glow = g.createRadialGradient(W / 2, H / 2, 30, W / 2, H / 2, W * 0.75);
    glow.addColorStop(0, 'rgba(40,120,60,0.18)'); glow.addColorStop(1, 'rgba(0,0,0,0.5)'); g.fillStyle = glow; g.fillRect(0, 0, W, H);
    g.font = '600 34px "IBM Plex Mono", ui-monospace, monospace'; g.textBaseline = 'top';
    g.shadowColor = green(0.8); g.shadowBlur = 10;
    let y = 30;
    if (lastLine) { g.fillStyle = green(0.45); g.fillText('>: ' + lastLine, 26, y); y += 48; }
    g.fillStyle = green(0.95); const line = '>: ' + typed; g.fillText(line, 26, y);
    if (blink) { const w = g.measureText(line).width; g.fillRect(30 + w, y + 2, 18, 32); }
    g.shadowBlur = 0;
    g.fillStyle = 'rgba(0,0,0,0.22)'; for (let r = 0; r < H; r += 3) g.fillRect(0, r, W, 1);   // scanlines
    return true;
  }
  draw(0);
  return { canvas, draw, gain: 1.5, bind(c: Cast, live?: Live) { cast = c; spec = live?.terminal ?? null; } };
}

// ---------------------------------------------------------------- the counter
// The face, as built: five windows across it (three for the minutes, a gap, two for the seconds), in metres from its
// centre; the canvas spans the face.
const FACE_W = 0.99, FACE_H = 0.31, TILE = 0.118, GAP = 0.012, SEP = 0.05, OPEN = 0.25;
const GLYPHS = ['\u{13080}', '\u{13399}', '\u{1309D}', '\u{1314B}', '\u{131CB}'];   // what it shows at zero

function counter() {
  const W = 1024, H = Math.round(W * FACE_H / FACE_W), canvas = document.createElement('canvas'); canvas.width = W; canvas.height = H;
  const g = canvas.getContext('2d')!, px = W / FACE_W;
  const xs: number[] = []; { let x = -(5 * TILE + 3 * GAP + SEP) / 2; for (let i = 0; i < 5; i++) { xs.push(x); x += TILE + (i === 2 ? SEP : GAP); } }
  const shown = digits(remaining(0)), from = [...shown], flipAt = shown.map(() => -9);
  const FLIP = 0.16;
  function digits(s: number) { const m = Math.floor(s / 60), sec = s % 60; return [...String(m).padStart(3, '0'), ...String(sec).padStart(2, '0')]; }

  function half(x: number, y: number, w: number, h: number, ch: string, top: boolean, zero: boolean, k: number) {
    // one half of a card: the card, its character, cut at the hinge
    g.save(); g.beginPath(); g.rect(x, top ? y : y + h / 2, w, h / 2); g.clip();
    const red = zero && k >= 3;
    const grad = g.createLinearGradient(0, y, 0, y + h);
    grad.addColorStop(0, red ? '#7a1712' : '#1d1d1c'); grad.addColorStop(0.5, red ? '#5e100c' : '#121212'); grad.addColorStop(1, red ? '#741511' : '#1a1a19');
    g.fillStyle = grad; g.fillRect(x, y, w, h);
    g.fillStyle = zero ? (red ? '#1a0806' : '#d33a2a') : '#ece9df';
    g.font = zero ? `${Math.round(h * 0.62)}px "Segoe UI Historic", "Noto Sans Egyptian Hieroglyphs", serif` : `700 ${Math.round(h * 0.86)}px "Helvetica Neue", "Arial Narrow", Arial, sans-serif`;
    g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillText(ch, x + w / 2, y + h * (zero ? 0.52 : 0.54));
    g.restore();
  }
  function card(i: number, t: number, zero: boolean) {
    const x = W / 2 + xs[i] * px, w = TILE * px, y = H / 2 - (OPEN / 2) * px, h = OPEN * px;
    const now = shown[i], was = from[i], p = Math.min(1, Math.max(0, (t - flipAt[i]) / FLIP));
    if (t < flipAt[i]) { half(x, y, w, h, was, true, zero, i); half(x, y, w, h, was, false, zero, i); }
    else if (p >= 1) { half(x, y, w, h, now, true, zero, i); half(x, y, w, h, now, false, zero, i); }
    else {
      half(x, y, w, h, now, true, zero, i); half(x, y, w, h, was, false, zero, i);
      // the falling flap: the old top folding down to the hinge, then the new bottom unfolding from it
      const mid = y + h / 2; g.save();
      if (p < 0.5) { g.translate(0, mid); g.scale(1, 1 - 2 * p); g.translate(0, -mid); half(x, y, w, h, was, true, zero, i); }
      else { g.translate(0, mid); g.scale(1, 2 * p - 1); g.translate(0, -mid); half(x, y, w, h, now, false, zero, i); }
      g.restore();
      g.fillStyle = `rgba(0,0,0,${0.35 * Math.sin(p * Math.PI)})`; g.fillRect(x, y, w, h);   // the flap's shadow
    }
    g.fillStyle = '#050505'; g.fillRect(x, y + h / 2 - 2, w, 4);                            // the hinge
    g.fillStyle = 'rgba(255,255,255,0.06)'; g.fillRect(x, y + h / 2 + 2, w, 2);
  }
  let lastKey = '';
  function draw(t: number) {
    const left = remaining(t), zero = left === 0;
    const want = zero ? GLYPHS : digits(left);
    for (let i = 0; i < 5; i++) if (want[i] !== shown[i]) {
      if (t - flipAt[i] < FLIP) continue;                                // one flip at a time per card
      from[i] = shown[i]; shown[i] = want[i]; flipAt[i] = t + (swan.resets && t - swan.t0 < 1 ? i * 0.07 : 0);
    }
    const flipping = flipAt.some(f => t - f < FLIP + 0.02 && t - f > -1), key = shown.join('') + flipping;
    if (!flipping && key === lastKey) return false;                       // nothing moved: no upload
    lastKey = key;
    g.fillStyle = '#0b0b0b'; g.fillRect(0, 0, W, H);
    for (let i = 0; i < 5; i++) card(i, t, zero);
    return true;
  }
  draw(0);
  return { canvas, draw, gain: 0.8, every: 1 / 30 };
}

// ---------------------------------------------------------------- the mainframes
function lamps(q: number) {
  const W = 232, H = 248, canvas = document.createElement('canvas'); canvas.width = W; canvas.height = H;
  const g = canvas.getContext('2d')!, r = rng(301 + q * 17), cols = 9, rows = 9;
  const colour = Array.from({ length: rows }, () => ['#ff3b2a', '#ffb02e', '#f4f1e2', '#55ff7a'][Math.floor(r() * 4)]);
  const on = Array.from({ length: rows * cols }, () => r() < 0.4);
  const kind = Array.from({ length: rows }, () => (r() < 0.35 ? 'count' : r() < 0.6 ? 'scan' : 'twinkle'));
  let tick = 0;
  function draw(t: number) {
    tick++;
    g.fillStyle = '#1b201d'; g.fillRect(0, 0, W, H);
    g.fillStyle = '#101311'; for (let j = 0; j < rows; j++) g.fillRect(8, 14 + j * 26, W - 16, 20);
    for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) {
      const k = j * cols + i;
      if (kind[j] === 'count') on[k] = ((Math.floor(t * (1.5 + j * 0.4)) + j * 37) >> (cols - 1 - i) & 1) === 1;
      else if (kind[j] === 'scan') on[k] = i === Math.floor(t * 3 + j) % cols || on[k] && r() < 0.15;
      else if (r() < 0.06) on[k] = !on[k];
      const x = 20 + i * 24, y = 24 + j * 26;
      if (on[k]) {
        const gl = g.createRadialGradient(x, y, 0, x, y, 11); gl.addColorStop(0, colour[j]); gl.addColorStop(0.45, colour[j] + 'aa'); gl.addColorStop(1, colour[j] + '00');
        g.fillStyle = gl; g.fillRect(x - 11, y - 11, 22, 22);
      } else { g.fillStyle = '#2b2f2c'; g.beginPath(); g.arc(x, y, 5, 0, Math.PI * 2); g.fill(); }
    }
    return true;
  }
  draw(0);
  return { canvas, draw, gain: 1.1, every: 0.25 };
}

function reels(q: number) {
  const W = 256, H = 256, canvas = document.createElement('canvas'); canvas.width = W; canvas.height = H;
  const g = canvas.getContext('2d')!, r = rng(907 + q * 31);
  let fill = 0.3 + r() * 0.4, angle = r() * 6, last = 0;
  const phase = r() * 10;
  function reel(cx: number, cy: number, pack: number, a: number) {
    g.fillStyle = '#3a2a1e'; g.beginPath(); g.arc(cx, cy, 22 + pack * 52, 0, Math.PI * 2); g.fill();            // the tape on it
    g.strokeStyle = 'rgba(210,214,208,0.85)'; g.lineWidth = 3; g.beginPath(); g.arc(cx, cy, 78, 0, Math.PI * 2); g.stroke();   // the flange's rim
    g.fillStyle = 'rgba(200,204,198,0.35)';
    for (let k = 0; k < 3; k++) {                                                                               // its three windows
      g.beginPath(); g.moveTo(cx, cy); g.arc(cx, cy, 74, a + k * 2.094 + 0.35, a + k * 2.094 + 1.75); g.closePath(); g.fill();
    }
    g.fillStyle = '#c9ccc6'; g.beginPath(); g.arc(cx, cy, 20, 0, Math.PI * 2); g.fill();
    g.fillStyle = '#2a2d2b'; g.beginPath(); g.arc(cx, cy, 7, 0, Math.PI * 2); g.fill();
  }
  function draw(t: number) {
    const dt = Math.min(0.5, t - last); last = t;
    const burst = Math.max(0, Math.sin(t * 0.7 + phase) * 1.4 + Math.sin(t * 2.3 + phase * 2) * 0.6 - 0.3);   // tape drives run in starts and stops
    angle += dt * burst * 4.5; fill = 0.15 + 0.7 * (0.5 + 0.5 * Math.sin(t * 0.004 + phase));
    g.fillStyle = '#0b0d0c'; g.fillRect(0, 0, W, H);
    reel(64, 70, fill, angle); reel(192, 70, 1 - fill, angle * 0.9);
    g.strokeStyle = '#3a2a1e'; g.lineWidth = 2;
    g.beginPath(); g.moveTo(64 - 22 - fill * 52, 70); g.lineTo(40, 200); g.lineTo(216, 200); g.lineTo(192 + 22 + (1 - fill) * 52, 70); g.stroke();
    g.fillStyle = '#9a9d98'; for (const x of [40, 128, 216]) { g.beginPath(); g.arc(x, 200, 9, 0, Math.PI * 2); g.fill(); }
    g.fillStyle = 'rgba(255,255,255,0.05)'; g.fillRect(0, 0, W, H * 0.45);                                   // the glass
    return true;
  }
  draw(0);
  return { canvas, draw, gain: 0.6, every: 0.1 };
}
