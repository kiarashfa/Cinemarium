// KMH's two screens. The big TV: game seven on the broadcast, kept to Howard's clock (the pregame while he settles,
// the tip, the fourth quarter running down, the last basket and the final), a court seen from the side line with its
// players moving, the score bug along the bottom. The camera monitor: four grey views of the store.
import { rng } from '../materials';
import type { Cast } from './performers';

interface Game { who: string; act: string; tip: number; win: number; end: number; pregame: number }
interface Live { game?: Game; [k: string]: unknown }

export function gemsScreen(q: number) {
  return q === 1 ? monitor() : tv();
}

// ---------------------------------------------------------------- the game
const HOME_C = '#e8eee9', AWAY_C = '#c8203a', GREEN = '#1f7a45';

function tv() {
  const W = 640, H = 368, canvas = document.createElement('canvas'); canvas.width = W; canvas.height = H;
  const g = canvas.getContext('2d')!;
  let cast: Cast | null = null, game: Game | null = null;
  const r = rng(7);
  const players = Array.from({ length: 10 }, (_, i) => ({ home: i < 5, x: 0.2 + r() * 0.6, y: 0.25 + r() * 0.55, ph: r() * 6.28, sp: 0.6 + r() * 0.8 }));

  function clock(): { phase: 'pre' | 'tip' | 'game' | 'final'; u: number; t: number } {
    const cur = cast && game ? cast.current(game.who) : null;
    if (!cur || !game || cur.getClip().name !== game.act || cur.getEffectiveWeight() < 0.3) return { phase: 'final', u: 1, t: 0 };
    const t = cur.time;
    if (t < game.pregame) return { phase: 'final', u: 1, t };                              // the post-game, still on from before
    if (t < game.tip - 3) return { phase: 'pre', u: (t - game.pregame) / (game.tip - 3 - game.pregame), t };
    if (t < game.tip + 1.5) return { phase: 'tip', u: (t - (game.tip - 3)) / 4.5, t };
    if (t < game.win) return { phase: 'game', u: (t - game.tip) / (game.win - game.tip), t };
    return { phase: 'final', u: 1, t };
  }

  function court(t: number, zoom: number) {
    // the floor from the side line: parquet in perspective, the green key and the centre circle, the crowd above
    g.fillStyle = '#1b2a22'; g.fillRect(0, 0, W, H);
    for (let row = 0; row < 7; row++) {                                                      // the crowd: rows of heads
      for (let i = 0; i < 48; i++) {
        const rr = rng(row * 101 + i); g.fillStyle = rr() < 0.55 ? '#2f8a50' : rr() < 0.5 ? '#d8dcd2' : '#55453a';
        g.fillRect(i * 14 + (row % 2) * 7, 12 + row * 12 + Math.sin(t * 3 + i) * (rr() < 0.1 ? 1.5 : 0), 9, 9);
      }
    }
    const top = 104, bot = H - 54;
    g.fillStyle = '#c99a5e'; g.beginPath(); g.moveTo(-80 * zoom, bot); g.lineTo(W + 80 * zoom, bot); g.lineTo(W - 30, top); g.lineTo(30, top); g.closePath(); g.fill();
    g.strokeStyle = 'rgba(120,80,40,0.25)'; g.lineWidth = 1;
    for (let k = 0; k < 18; k++) { const x = (k / 18) * W; g.beginPath(); g.moveTo(x, top); g.lineTo(W / 2 + (x - W / 2) * 1.35, bot); g.stroke(); }
    g.fillStyle = GREEN;                                                                     // the keys at either end
    g.beginPath(); g.moveTo(30, top); g.lineTo(140, top); g.lineTo(110, bot); g.lineTo(-60, bot); g.closePath(); g.fill();
    g.beginPath(); g.moveTo(W - 30, top); g.lineTo(W - 140, top); g.lineTo(W - 110, bot); g.lineTo(W + 60, bot); g.closePath(); g.fill();
    g.strokeStyle = 'rgba(255,255,255,0.85)'; g.lineWidth = 2;
    g.beginPath(); g.moveTo(W / 2, top); g.lineTo(W / 2, bot); g.stroke();
    g.beginPath(); g.ellipse(W / 2, (top + bot) / 2, 54, 20, 0, 0, 6.283); g.stroke();
    return { top, bot };
  }

  function figure(x: number, y: number, s: number, home: boolean, t: number, ph: number) {
    const leg = Math.sin(t * 7 + ph) * 3 * s;
    g.fillStyle = '#3a2418'; g.fillRect(x - 2 * s, y - 9 * s, 2 * s, 9 * s + leg); g.fillRect(x + 1 * s, y - 9 * s, 2 * s, 9 * s - leg);
    g.fillStyle = home ? HOME_C : AWAY_C; g.fillRect(x - 4 * s, y - 22 * s, 8 * s, 13 * s);
    g.fillStyle = home ? GREEN : '#1d3c8f'; g.fillRect(x - 3 * s, y - 13 * s, 6 * s, 3 * s);
    g.fillStyle = '#4a2c1e'; g.beginPath(); g.arc(x, y - 25 * s, 3.2 * s, 0, 6.283); g.fill();
  }

  function bug(home: number, away: number, period: string, time: string) {
    g.fillStyle = 'rgba(10,14,22,0.92)'; g.fillRect(40, H - 44, W - 80, 30);
    g.fillStyle = AWAY_C; g.fillRect(40, H - 44, 8, 30); g.fillStyle = GREEN; g.fillRect(196, H - 44, 8, 30);
    g.font = '700 19px "Manrope Variable", ui-sans-serif, sans-serif'; g.textBaseline = 'middle'; g.fillStyle = '#fff';
    g.fillText('PHI', 58, H - 29); g.fillText(String(away), 120, H - 29); g.fillText('BOS', 214, H - 29); g.fillText(String(home), 276, H - 29);
    g.fillStyle = '#f2c84b'; g.fillText(period, 340, H - 29); g.fillStyle = '#fff'; g.fillText(time, 392, H - 29);
    g.font = '600 13px "Manrope Variable", ui-sans-serif, sans-serif'; g.fillStyle = '#b9c2cc'; g.fillText('EAST SEMIS · GAME 7', 470, H - 29);
  }

  function draw(t: number) {
    const c = clock();
    if (c.phase === 'pre') {                                                                 // the studio before the game
      g.fillStyle = '#0d1b3a'; g.fillRect(0, 0, W, H);
      const gr = g.createLinearGradient(0, 0, W, H); gr.addColorStop(0, 'rgba(40,120,255,0.35)'); gr.addColorStop(1, 'rgba(0,0,0,0.2)'); g.fillStyle = gr; g.fillRect(0, 0, W, H);
      g.fillStyle = '#16305c'; g.fillRect(0, H * 0.58, W, H * 0.42);
      for (let k = 0; k < 3; k++) { const x = 150 + k * 170; figure(x, H * 0.74, 3.2, k !== 1, t * 0.15, k); g.fillStyle = '#1a1a22'; g.fillRect(x - 13, H * 0.74 - 70, 26, 44); }
      g.font = '800 34px "Manrope Variable", ui-sans-serif, sans-serif'; g.fillStyle = '#fff'; g.textBaseline = 'middle'; g.textAlign = 'center';
      g.fillText('GAME 7', W / 2, 70); g.font = '600 18px "Manrope Variable", ui-sans-serif, sans-serif'; g.fillStyle = '#9fc3ff'; g.fillText('PHILADELPHIA  AT  BOSTON', W / 2, 106); g.textAlign = 'left';
      bug(0, 0, 'PRE', 'GAME');
      return;
    }
    if (c.phase === 'final' && c.t > 0) {                                                   // the final: the winners on the floor, the interview
      court(t, 1);
      g.fillStyle = 'rgba(0,0,0,0.35)'; g.fillRect(0, 0, W, H);
      const rr = rng(Math.floor(t * 2));
      for (let k = 0; k < 6; k++) figure(180 + k * 52 + Math.sin(t * 4 + k) * 6, 270 + (k % 2) * 10 - Math.abs(Math.sin(t * 6 + k)) * 12 * (rr() < 0.7 ? 1 : 0), 3.0, true, t, k);
      g.font = '800 30px "Manrope Variable", ui-sans-serif, sans-serif'; g.fillStyle = '#fff'; g.textBaseline = 'middle'; g.textAlign = 'center';
      g.fillText('CELTICS ADVANCE', W / 2, 64); g.textAlign = 'left';
      bug(85, 75, 'FINAL', '');
      return;
    }
    if (c.phase === 'final') { court(t, 1); bug(85, 75, 'FINAL', ''); return; }
    const { top, bot } = court(t, 1);
    if (c.phase === 'tip') {                                                                 // the jump ball at centre court
      const mid = (top + bot) / 2; const up = Math.max(0, Math.sin(Math.min(1, c.u * 1.6) * Math.PI)) * 70;
      for (let k = 0; k < 10; k++) { const a = (k / 10) * 6.283; figure(W / 2 + Math.cos(a) * (k < 2 ? 14 : 90), mid + 24 + Math.sin(a) * (k < 2 ? 6 : 34), 2.2, k % 2 === 0, t * 0.4, k); }
      g.fillStyle = '#e0762b'; g.beginPath(); g.arc(W / 2, mid - 40 - up, 5, 0, 6.283); g.fill();
      bug(0, 0, '1ST', '12:00');
      return;
    }
    // the game: the players flowing up and down the floor, the ball with one of them
    const flow = Math.sin(t * 0.32) * 0.28;
    let best = -1, bx = W / 2, by = (top + bot) / 2;
    players.forEach(p => {
      const x = (0.5 + flow + Math.sin(t * p.sp * 0.6 + p.ph) * 0.18 + (p.x - 0.5) * 0.7) * W;
      const yy = top + 18 + (p.y + Math.sin(t * p.sp * 0.4 + p.ph * 2) * 0.08) * (bot - top - 30);
      figure(x, yy, 1.8 + (yy - top) / (bot - top) * 0.8, p.home, t, p.ph);
      if (p.home && Math.sin(t * 0.5 + p.ph) > best) { best = Math.sin(t * 0.5 + p.ph); bx = x; by = yy; }
    });
    g.fillStyle = '#e0762b'; g.beginPath(); g.arc(bx + 6, by - 16 + Math.abs(Math.sin(t * 9)) * 8, 3.5, 0, 6.283); g.fill();
    const home = Math.round(57 + 28 * c.u), away = Math.round(54 + 21 * c.u);
    const left = Math.max(0, (1 - c.u) * 10.5 * 60), mm = Math.floor(left / 60), ss = Math.floor(left % 60);
    bug(home, away, '4TH', `${mm}:${String(ss).padStart(2, '0')}`);
    g.font = '600 13px "Manrope Variable", ui-sans-serif, sans-serif'; g.fillStyle = 'rgba(10,14,22,0.85)'; g.fillRect(W - 186, 16, 150, 24);
    g.fillStyle = '#fff'; g.textBaseline = 'middle'; g.fillText(`GARNETT  ${16 + Math.round(10 * c.u)} PTS+REB`, W - 178, 28);
  }
  draw(0);
  return {
    canvas, draw, gain: 1.4, every: 1 / 15,
    bind(c: Cast, live: Live | undefined) { cast = c; game = (live?.game as Game) ?? null; },
  };
}

// ---------------------------------------------------------------- the camera monitor
function monitor() {
  const W = 320, H = 224, canvas = document.createElement('canvas'); canvas.width = W; canvas.height = H;
  const g = canvas.getContext('2d')!;
  let last = -1;
  function draw(t: number) {
    const s = Math.floor(t);
    if (s === last) return false;
    last = s;
    g.fillStyle = '#0b0f12'; g.fillRect(0, 0, W, H);
    for (let k = 0; k < 4; k++) {
      const x = (k % 2) * W / 2, y = Math.floor(k / 2) * H / 2, r = rng(k * 31 + 5);
      const gr = g.createLinearGradient(x, y, x, y + H / 2); gr.addColorStop(0, '#9fb3bf'); gr.addColorStop(1, '#3d4a52'); g.fillStyle = gr; g.fillRect(x + 2, y + 2, W / 2 - 4, H / 2 - 4);
      g.fillStyle = 'rgba(30,40,46,0.7)';
      for (let j = 0; j < 4; j++) g.fillRect(x + 10 + r() * (W / 2 - 60), y + 30 + r() * 40, 20 + r() * 40, 10 + r() * 30);
      g.fillStyle = '#e8f0f2'; g.font = '10px ui-monospace, monospace'; g.textBaseline = 'top'; g.fillText(`CAM 0${k + 1}`, x + 6, y + 6);
      const d = new Date(); g.fillText(`${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`, x + W / 2 - 60, y + H / 2 - 16);
    }
    g.fillStyle = 'rgba(0,0,0,0.2)'; for (let y = 0; y < H; y += 3) g.fillRect(0, y, W, 1);
    return true;
  }
  draw(0);
  return { canvas, draw, gain: 1.0, every: 0.5 };
}
