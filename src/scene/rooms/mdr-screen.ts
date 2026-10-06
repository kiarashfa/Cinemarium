// The Macrodata Refinement screen: a field of numbers drifting on a dark CRT, a few of them "scary"
// (they swell and tremble), the file's name and progress above, the five bins below.
import { rng } from '../materials';

const FILES = ['Cold Harbor', 'Siena', 'Tumwater', 'Dranesville'];

export function mdrScreen(q: number) {
  const W = 512, H = 384, canvas = document.createElement('canvas'); canvas.width = W; canvas.height = H;
  const g = canvas.getContext('2d')!, seed = 17 + q * 101, cols = 13, rows = 8;
  const digits = Array.from({ length: cols * rows }, (_, i) => Math.floor(rng(seed + i)() * 10));
  const scary = new Set(Array.from({ length: 5 }, (_, i) => Math.floor(rng(seed * 7 + i)() * cols * rows)));
  const progress = [0.18, 0.47, 0.31, 0.62][q % 4];
  function draw(t: number) {
    const r = rng(seed + Math.floor(t * 0.5));
    g.fillStyle = '#04121a'; g.fillRect(0, 0, W, H);
    const glow = g.createRadialGradient(W / 2, H / 2, 40, W / 2, H / 2, W * 0.7);
    glow.addColorStop(0, 'rgba(60,140,170,0.16)'); glow.addColorStop(1, 'rgba(0,0,0,0.35)'); g.fillStyle = glow; g.fillRect(0, 0, W, H);
    // header: the file and how far along it is
    g.fillStyle = '#9fe0f5'; g.fillRect(16, 14, W - 32, 34);
    g.fillStyle = '#04121a'; g.font = '600 20px "Manrope", ui-sans-serif, sans-serif'; g.textBaseline = 'middle';
    g.fillText(FILES[q % 4], 30, 32);
    const pct = Math.min(99, Math.floor((progress + t * 0.0004) * 100)); g.textAlign = 'right'; g.fillText(`${pct}% Complete`, W - 30, 32); g.textAlign = 'left';
    g.strokeStyle = 'rgba(159,224,245,.55)'; g.lineWidth = 1.5; g.beginPath(); g.moveTo(16, 60); g.lineTo(W - 16, 60); g.stroke();
    // the numbers
    g.textAlign = 'center';
    for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) {
      const k = j * cols + i, isScary = scary.has(k), x = 36 + i * 36.5, y = 92 + j * 30;
      const dx = Math.sin(t * 0.6 + k * 1.7) * 2.2, dy = Math.cos(t * 0.5 + k * 2.3) * 1.6;
      if (r() < 0.004) digits[k] = Math.floor(r() * 10);
      const swell = isScary ? 1 + 0.35 * (0.5 + 0.5 * Math.sin(t * 2.1 + k)) : 1;
      g.font = `${Math.round(20 * swell)}px "IBM Plex Mono", ui-monospace, monospace`;
      g.fillStyle = isScary ? '#e8fbff' : 'rgba(150,220,240,0.86)';
      g.fillText(String(digits[k]), x + dx + (isScary ? Math.sin(t * 9 + k) * 1.2 : 0), y + dy);
    }
    g.textAlign = 'left';
    // the bins
    g.beginPath(); g.moveTo(16, H - 70); g.lineTo(W - 16, H - 70); g.stroke();
    for (let b = 0; b < 5; b++) {
      const bx = 22 + b * 96;
      g.strokeStyle = 'rgba(159,224,245,.7)'; g.strokeRect(bx, H - 58, 84, 22);
      g.fillStyle = '#9fe0f5'; g.font = '15px "IBM Plex Mono", ui-monospace, monospace'; g.textBaseline = 'middle'; g.fillText(`0${b + 1}`, bx + 32, H - 47);
      const fill = ((progress * 3.1 + b * 0.17) % 1) * 84; g.fillStyle = 'rgba(159,224,245,.85)'; g.fillRect(bx, H - 30, fill, 6);
      g.strokeRect(bx, H - 30, 84, 6);
    }
    // scanlines
    g.fillStyle = 'rgba(0,0,0,0.18)'; for (let y = 0; y < H; y += 3) g.fillRect(0, y, W, 1);
  }
  draw(0);
  return { canvas, draw };
}
