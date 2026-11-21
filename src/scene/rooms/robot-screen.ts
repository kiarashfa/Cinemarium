// The arcade's live screen: the terminal on the hackers' long table, running the encryption on the night of the hack.
// While Tyrell types, its lines come up one by one (the source of entropy, the keys, then every folder of the system
// encrypted in turn); while he is away from the keys the run goes on by itself; then it sits finished, the cursor
// blinking. The desktop behind it is the pale cyan of the night.
import type { Cast } from './performers';

interface Live { [k: string]: unknown }

const LINES = [
  'root@fsociety:~# ./fsociety.sh', 'Executing FunSociety', 'Loading Source of Entropy', '####################  COMPLETE', '',
  'Generating Keys', '####################  COMPLETE', '', 'Locating target files.', 'Beginning crypto operations',
  'Encrypting /bin', 'Encrypting /boot', 'Encrypting /dev', 'Encrypting /etc', 'Encrypting /home', 'Encrypting /lib',
  'Encrypting /opt', 'Encrypting /root', 'Encrypting /sbin', 'Encrypting /srv', 'Encrypting /usr', 'Encrypting /var',
  'Encryption complete.',
];
const WHO = 'tyrell', ACT = 'scene', PER_LINE = 3.2;

export function robotScreen(q: number) {
  const W = 1024, H = 640, canvas = document.createElement('canvas'); canvas.width = W; canvas.height = H;
  const g = canvas.getContext('2d')!;
  let cast: Cast | null = null, shownKey = '';
  function draw(t: number) {
    // how far the run has got: by Tyrell's act when he is in it, else finished
    const cur = cast?.current(WHO);
    const at = cur && cur.getClip().name === ACT && cur.getEffectiveWeight() > 0.3 ? cur.time : Infinity;
    const n = Math.min(LINES.length, Math.floor(at / PER_LINE) + 1);
    const blink = Math.floor(t * 2) % 2 === 0, key = `${n}|${blink}|${q}`;
    if (key === shownKey) return false;
    shownKey = key;
    const sky = g.createLinearGradient(0, 0, 0, H); sky.addColorStop(0, '#6fcfd6'); sky.addColorStop(1, '#8be0e4');
    g.fillStyle = sky; g.fillRect(0, 0, W, H);
    g.fillStyle = 'rgba(240,244,246,0.9)'; for (let j = 0; j < 6; j++) g.fillRect(20, 30 + j * 80, 50, 50);   // the desktop's icons
    g.fillStyle = '#2e3238'; g.fillRect(150, 60, 610, 500); g.fillStyle = '#c8ccd2'; g.fillRect(150, 60, 610, 24);
    g.font = '22px ui-monospace, Consolas, monospace'; g.textBaseline = 'top'; g.fillStyle = '#dee2de';
    const first = Math.max(0, n - 15);
    let y = 96;
    for (let i = first; i < n; i++) { g.fillText(LINES[i], 166, y); y += 30; }
    if (blink) g.fillRect(166, y + 2, 12, 22);
    return true;
  }
  draw(0);
  return { canvas, draw, gain: 1.4, every: 0.25, bind(c: Cast, _live?: Live) { cast = c; } };
}
