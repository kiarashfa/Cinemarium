// The Rotunda: a circular video club after the round wine cellar of the Cité du Vin in Bordeaux. One ring of racks
// makes the wall, floor to ceiling, every cell holding DVD and VHS cases in runs with air between them, lit by the
// strip under the shelf above; brass rods between the columns of cells; curved light-oak display counters around the
// subject; four concrete columns; a dark satin floor; and a stack of luminous rings hanging over the centre.
// It is kept dark, as the cellar is: the racks are a quiet texture, the rings and the counters carry the light.
// Two finishes: noir (dark-stained racks, as in Bordeaux; the Case) and oak (honey oak, brass, a gallery).
import * as THREE from 'three/webgpu';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { canvasTexture, noise, rng } from './materials';
import { capture, dim, keySpot, polishedFloor, type Subject } from './ambient-kit';

export type Finish = 'noir' | 'oak';
const ROWS = 16;                   // shelf rows in the media texture
const CELL = 0.62, SHELF = 0.3;    // a rack cell: 62 cm of arc, 30 cm between shelves

// a collector's palette: black, ivory and gilt, deep burgundy, navy and green; a little silver
const SPINES = [[12, 12, 13], [16, 15, 15], [20, 18, 17], [10, 10, 11], [226, 216, 194], [214, 202, 178], [104, 18, 24], [74, 14, 20],
  [20, 30, 58], [26, 40, 70], [22, 44, 34], [150, 118, 62], [182, 182, 186], [60, 44, 34]];

function drawSpine(c: CanvasRenderingContext2D, x: number, y: number, bw: number, bh: number, r: () => number, vhs: boolean) {
  const p = SPINES[Math.floor(r() * SPINES.length)], v = 0.82 + r() * 0.3;
  const col = (k: number) => `rgb(${(p[0] * v * k) | 0},${(p[1] * v * k) | 0},${(p[2] * v * k) | 0})`;
  const g = c.createLinearGradient(x, 0, x + bw, 0); g.addColorStop(0, col(0.6)); g.addColorStop(0.4, col(1.08)); g.addColorStop(1, col(0.62));
  c.fillStyle = g; c.fillRect(x, y, bw - 0.8, bh);
  const light = p[0] + p[1] + p[2] > 360;
  c.fillStyle = light ? 'rgba(20,18,16,.75)' : r() < 0.6 ? 'rgba(214,176,96,.9)' : 'rgba(240,236,228,.75)';
  c.fillRect(x + bw * 0.32, y + bh * (0.18 + r() * 0.12), Math.max(1, bw * 0.36), bh * (0.3 + r() * 0.35));   // the title, along the spine
  c.fillRect(x + bw * 0.2, y + bh * 0.04, bw * 0.6, Math.max(1.5, bw * 0.5));                                  // a studio mark
  if (r() < 0.5) { c.fillStyle = 'rgba(214,176,96,.85)'; c.fillRect(x + bw * 0.25, y + bh * 0.9, bw * 0.5, 2); }   // the collector's number
  if (vhs) { c.fillStyle = 'rgba(255,255,255,.1)'; c.fillRect(x, y, 1, bh); }                                // a clamshell's rim
}

/** A cover, face out: invented art (a field, a figure or a band, a title block), never a real film's. */
function drawCover(c: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: () => number) {
  const hue = r() < 0.5 ? 20 + r() * 30 : r() * 360, dark = r() < 0.8;                 // mostly dark, warm, muted art
  const g = c.createLinearGradient(x, y, x, y + h);
  g.addColorStop(0, `hsl(${hue},${15 + r() * 30}%,${dark ? 6 + r() * 12 : 35 + r() * 25}%)`);
  g.addColorStop(1, `hsl(${(hue + 20 + r() * 40) % 360},${10 + r() * 25}%,${dark ? 2 + r() * 6 : 20 + r() * 20}%)`);
  c.fillStyle = g; c.fillRect(x, y, w, h);
  c.fillStyle = `hsla(${(hue + 160 + r() * 40) % 360},${25 + r() * 25}%,${45 + r() * 30}%,${0.45 + r() * 0.35})`;
  if (r() < 0.5) { c.beginPath(); c.arc(x + w * (0.3 + r() * 0.4), y + h * (0.35 + r() * 0.3), w * (0.15 + r() * 0.25), 0, 6.283); c.fill(); }
  else c.fillRect(x + w * 0.1, y + h * (0.25 + r() * 0.3), w * 0.8, h * (0.08 + r() * 0.2));
  c.fillStyle = r() < 0.5 ? 'rgba(214,180,104,.9)' : `rgba(250,244,230,${0.75 + r() * 0.2})`; c.fillRect(x + w * 0.12, y + h * (r() < 0.5 ? 0.08 : 0.76), w * 0.76, h * 0.07);
  c.fillStyle = 'rgba(255,255,255,.35)'; for (let k = 0; k < 3; k++) c.fillRect(x + w * 0.15, y + h * (0.9 + k * 0.025), w * 0.7, 1);
  c.fillStyle = 'rgba(255,255,255,.08)'; c.fillRect(x, y, w * 0.12, h);                                     // the sleeve's sheen
  c.strokeStyle = 'rgba(0,0,0,.6)'; c.lineWidth = 1; c.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
}

/** 16 shelf rows of cases in one 2048² texture (a 30 cm row is 128 px): DVD spines, VHS clamshells, covers face out. */
function mediaTexture(seed: number) {
  const t = canvasTexture(2048, 2048, (c, w, h) => {
    const r = rng(seed), rh = h / ROWS;
    c.fillStyle = '#060504'; c.fillRect(0, 0, w, h);
    for (let row = 0; row < ROWS; row++) {
      const base = (row + 1) * rh - 3, mood = r(); let x = 0;
      while (x < w) {
        const k = r(), vhs = mood < 0.25 ? true : mood > 0.8 ? false : r() < 0.3;
        if (k < 0.07) {                                   // a cover face out, with room round it
          const cw = 46 + r() * 12, ch = rh * 0.7; x += 12; drawCover(c, x, base - ch, cw, ch, r); x += cw + 16 + r() * 26; continue;
        }
        if (k < 0.13) {                                   // a short stack lying flat
          const th = vhs ? 10.5 : 6, n = 2 + Math.floor(r() * 4); x += 8;
          for (let q = 0; q < n; q++) { c.save(); c.translate(x + 81, base - q * th); c.rotate(Math.PI / 2); drawSpine(c, 0, 0, th, 81, r, vhs); c.restore(); }
          x += 81 + 18 + r() * 30; continue;
        }
        const n = 6 + Math.floor(r() * (vhs ? 9 : 20));    // a run of cases, then empty shelf
        for (let q = 0; q < n && x < w; q++) {
          const bw = vhs ? 10 + r() * 2 : 5.4 + r() * 1.2, bh = rh * (vhs ? 0.7 : 0.63) * (0.98 + r() * 0.03);
          drawSpine(c, x, base - bh, bw, bh, r, vhs); x += bw + 0.4;
        }
        x += 20 + r() * 64;
      }
      // the strip under the shelf above lights the top of the row; the foot of the row falls into shade
      const y0 = row * rh, gl = c.createLinearGradient(0, y0, 0, y0 + rh);
      gl.addColorStop(0, 'rgba(255,205,140,.3)'); gl.addColorStop(0.3, 'rgba(255,205,140,0)'); gl.addColorStop(0.5, 'rgba(0,0,0,.25)'); gl.addColorStop(1, 'rgba(0,0,0,.72)');
      c.fillStyle = gl; c.fillRect(0, y0, w, rh);
    }
  });
  t.anisotropy = 8; return t;
}

/** Covers lying face up on a counter's slanted top: two rows, 2 m of counter per tile. */
function coversTexture(seed: number) {
  const t = canvasTexture(2048, 512, (c, w, h) => {
    const r = rng(seed); c.fillStyle = '#d9c3a0'; c.fillRect(0, 0, w, h); noise(c, w, h, 8, seed);
    for (const [y0, ch] of [[40, 200], [272, 200]]) {
      let x = 14;
      while (x < w - 120) { const cw = 104 + r() * 8; drawCover(c, x, y0, cw, ch, r); c.fillStyle = 'rgba(0,0,0,.25)'; c.fillRect(x + 3, y0 + ch, cw - 2, 5); x += cw + 10 + r() * 6; }
    }
  }, { repeat: [1, 1] });
  t.anisotropy = 8; return t;
}

/** Cells on a ring of radius R between angles a0 and a1: quads facing the centre, each a different stretch of shelf. */
function cellRing(R: number, a0: number, a1: number, cols: number, y0: number, rows: number, r: () => number) {
  const pos: number[] = [], uvs: number[] = [], idx: number[] = [], da = (a1 - a0) / cols, uw = CELL * 427 / 2048, gap = 0.012 / R;
  for (let col = 0; col < cols; col++) for (let k = 0; k < rows; k++) {
    const b0 = a0 + col * da + gap, b1 = a0 + (col + 1) * da - gap, ya = y0 + k * SHELF + 0.02, yb = y0 + (k + 1) * SHELF - 0.004;
    const u0 = r() * (1 - uw), row = Math.floor(r() * ROWS), v0 = 1 - (row + 1) / ROWS, v1 = 1 - row / ROWS, n = pos.length / 3;
    // seen from the centre, growing angles run to the left: the texture runs the other way, so nothing reads mirrored
    for (const [a, y, u, v] of [[b0, ya, u0 + uw, v0], [b1, ya, u0, v0], [b1, yb, u0, v1], [b0, yb, u0 + uw, v1]]) { pos.push(Math.sin(a) * R, y, Math.cos(a) * R); uvs.push(u, v); }
    idx.push(n, n + 2, n + 1, n, n + 3, n + 2);
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2)); g.setIndex(idx);
  g.computeVertexNormals(); return g;
}
const lathe = (profile: number[][], a0 = 0, span = Math.PI * 2, seg = 180) => new THREE.LatheGeometry(profile.map(([x, y]) => new THREE.Vector2(x, y)), seg, a0, span);
const at = (geo: THREE.BufferGeometry, a: number, y: number, R: number) => { geo.translate(0, y, R); geo.rotateY(a); return geo; };

/** A ring of racks: cells, shelves, uprights, brass rods, LED strips, back and cornice, between angles a0..a0+span. */
function rackRing(R: number, depth: number, y0: number, rows: number, a0: number, span: number, r: () => number, out: { wood: THREE.BufferGeometry[]; brass: THREE.BufferGeometry[]; led: THREE.BufferGeometry[]; media: THREE.BufferGeometry[] }, cornice = true) {
  const cols = Math.max(1, Math.round(span * R / CELL)), top = y0 + rows * SHELF, full = span >= Math.PI * 2 - 1e-6;
  out.media.push(cellRing(R + 0.12, a0, a0 + span, cols, y0, rows, r));
  for (let k = 0; k <= rows; k++) {
    const y = y0 + k * SHELF;
    out.wood.push(lathe([[R, y - 0.022], [R + depth, y - 0.022], [R + depth, y], [R, y], [R, y - 0.022]], a0, span));
    if (k > 0) out.led.push(lathe([[R - 0.003, y - 0.036], [R - 0.003, y - 0.024]], a0, span));
  }
  for (let col = 0; col <= cols - (full ? 1 : 0); col++) {
    const a = a0 + col * span / cols;
    out.wood.push(at(new THREE.BoxGeometry(0.024, top - y0 + 0.02, depth), a, (y0 + top) / 2, R + depth / 2));
    out.brass.push(at(new THREE.CylinderGeometry(0.006, 0.006, top - y0, 6), a, (y0 + top) / 2, R - 0.022));
  }
  out.wood.push(lathe([[R + depth, 0], [R + depth, top + 0.2]], a0, span));                                   // the back
  out.wood.push(lathe([[R - 0.03, 0], [R - 0.03, y0], [R + depth, y0], [R + depth, 0]], a0, span));             // the plinth
  if (cornice) out.wood.push(lathe([[R - 0.05, top], [R + depth, top], [R + depth, top + 0.2], [R - 0.05, top + 0.2], [R - 0.05, top]], a0, span));
}

export async function rotunda(scene: THREE.Scene, renderer: THREE.WebGPURenderer, s: Subject, finish: Finish) {
  const g = new THREE.Group(), cz = s.centre.z, top = s.centre.y + s.height / 2, oak = finish === 'oak';
  const R = 9, depth = 0.42, H = Math.max(8.6, top + 3), r = rng(oak ? 77 : 71);
  scene.background = new THREE.Color(0x040302); scene.fog = new THREE.FogExp2(0x050403, 0.024);
  const rackWood = new THREE.MeshPhysicalMaterial(oak ? { color: 0x8a5c33, roughness: 0.5, clearcoat: 0.35, clearcoatRoughness: 0.35 } : { color: 0x1b1310, roughness: 0.45, clearcoat: 0.5, clearcoatRoughness: 0.3 });
  const counterWood = new THREE.MeshPhysicalMaterial({ color: oak ? 0xa6764a : 0xb88c5c, roughness: 0.55, clearcoat: 0.25, clearcoatRoughness: 0.4 });
  const brass = new THREE.MeshPhysicalMaterial({ color: oak ? 0xc39a56 : 0xa98348, metalness: 1, roughness: 0.3 });
  const led = new THREE.MeshBasicMaterial({ color: new THREE.Color(1, 0.78, 0.5).multiplyScalar(oak ? 0.7 : 0.55), side: THREE.DoubleSide });
  const media = new THREE.MeshBasicMaterial({ map: mediaTexture(oak ? 13 : 11), color: new THREE.Color(1, 0.92, 0.82).multiplyScalar(oak ? 0.42 : 0.32), side: THREE.DoubleSide });
  const parts = { wood: [] as THREE.BufferGeometry[], brass: [] as THREE.BufferGeometry[], led: [] as THREE.BufferGeometry[], media: [] as THREE.BufferGeometry[] };
  // the wall: racks from the floor to the ceiling, all the way round
  rackRing(R, depth, 0.2, Math.floor((H - 0.7) / SHELF), 0, Math.PI * 2, r, parts);
  const counters: THREE.BufferGeometry[] = [], slants: THREE.BufferGeometry[] = [];
  // curved display counters around the subject: DVDs on two shelves in front, covers on the slanted top
  const Rc = 4.4, span = 0.9;
  for (let k = 0; k < 4; k++) {
    const a0 = k * Math.PI / 2 - span / 2 + Math.PI / 4 * (oak ? 1 : 0);
    // the body: a kick plate, two open shelves set back, a lip, the slanted display, the back
    const body = [[Rc, 0], [Rc, 0.12], [Rc + 0.22, 0.12], [Rc + 0.22, 0.8], [Rc, 0.8], [Rc, 0.86], [Rc + 0.6, 1.07], [Rc + 0.68, 1.07], [Rc + 0.68, 0], [Rc, 0]];
    counters.push(lathe(body, a0, span, 72));
    for (const a of [a0, a0 + span]) {   // end panels
      const sh = new THREE.Shape(body.map(([x, y]) => new THREE.Vector2(x, y))), cap = new THREE.ShapeGeometry(sh); cap.rotateY(a - Math.PI / 2); counters.push(cap);
    }
    slants.push(lathe([[Rc + 0.03, 0.875], [Rc + 0.58, 1.068]], a0 + 0.012, span - 0.024, 72));
    parts.media.push(cellRing(Rc + 0.2, a0 + 0.02, a0 + span - 0.02, Math.round(span * Rc / CELL), 0.12, 2, r));
    for (const y of [0.42]) counters.push(lathe([[Rc - 0.004, y], [Rc + 0.22, y], [Rc + 0.22, y + 0.025], [Rc - 0.004, y + 0.025], [Rc - 0.004, y]], a0, span, 72));
    parts.led.push(lathe([[Rc - 0.006, 0.83], [Rc - 0.006, 0.85]], a0, span, 72));
  }
  if (oak) {   // a gallery round the wall, with a brass rail
    const gy = 4.3;
    parts.wood.push(lathe([[R - 1.25, gy], [R, gy], [R, gy + 0.16], [R - 1.25, gy + 0.16], [R - 1.25, gy]]));
    parts.brass.push(lathe([[R - 1.22, gy + 1.02], [R - 1.2, gy + 1.04], [R - 1.18, gy + 1.02], [R - 1.2, gy + 1.0], [R - 1.22, gy + 1.02]], 0, Math.PI * 2, 240));
    const n = Math.round(2 * Math.PI * (R - 1.2) / 0.5);
    for (let k = 0; k < n; k++) parts.brass.push(at(new THREE.CylinderGeometry(0.008, 0.008, 0.86, 6), k * 2 * Math.PI / n, gy + 0.59, R - 1.2));
    parts.led.push(lathe([[R - 1.255, gy + 0.01], [R - 1.255, gy + 0.03]]));
  }
  const place = (geo: THREE.BufferGeometry) => geo.translate(0, 0, cz);
  const add = (list: THREE.BufferGeometry[], m: THREE.Material) => { const mesh = new THREE.Mesh(place(mergeGeometries(list.map(x => x.index ? x.toNonIndexed() : x))), m); g.add(mesh); return mesh; };
  add(parts.wood, rackWood); add(parts.brass, brass); add(parts.led, led); add(parts.media, media);
  add(counters, counterWood);
  const cov = coversTexture(oak ? 23 : 21); cov.repeat.set(span * (Rc + 0.3) / 2, 1);
  add(slants, new THREE.MeshBasicMaterial({ map: cov, color: new THREE.Color(1, 0.95, 0.88).multiplyScalar(0.95), side: THREE.DoubleSide }));
  // the floor, polished; the ceiling, dark; three concrete columns
  // dark polished concrete, satin: it holds the glow of the rings and the counters, not a copy of the racks
  const floor = polishedFloor(new THREE.CircleGeometry(R + 0.5, 160), { base: oak ? '#1c1713' : '#161412', vein: '150,140,128', mirror: 0.12, coat: 0.35, coatRough: 0.38 });
  floor.position.z = cz; g.add(floor);
  const ceil = new THREE.Mesh(new THREE.CircleGeometry(R + depth + 0.3, 160), new THREE.MeshStandardMaterial({ color: 0x0b0a09, roughness: 0.9 }));
  ceil.rotation.x = Math.PI / 2; ceil.position.set(0, H, cz); g.add(ceil);
  // four columns of fair-faced concrete, standing out from the racks between the counters
  const formwork = canvasTexture(256, 1024, (c, w, h) => {
    c.fillStyle = '#8f8c87'; c.fillRect(0, 0, w, h); noise(c, w, h, 14, 9);
    c.fillStyle = 'rgba(40,38,36,.18)'; for (let y = 0; y < h; y += 170) c.fillRect(0, y, w, 2);     // pour joints
    const r2 = rng(9); for (let k = 0; k < 260; k++) { c.fillStyle = `rgba(30,28,26,${0.1 + r2() * 0.2})`; c.beginPath(); c.arc(r2() * w, r2() * h, 0.6 + r2() * 1.6, 0, 6.283); c.fill(); }   // air holes
  }, { repeat: [2, 2] });
  const concrete = new THREE.MeshStandardMaterial({ map: formwork, roughness: 0.82 });
  for (let k = 0; k < 4; k++) {
    const a = Math.PI / 4 + k * Math.PI / 2, col = new THREE.Mesh(new THREE.CylinderGeometry(0.26, 0.26, H, 48), concrete);
    col.position.set(Math.sin(a) * 7.2, H / 2, cz + Math.cos(a) * 7.2); col.castShadow = col.receiveShadow = true; g.add(col);
  }
  // the chandelier: luminous bands stacked and gently tilted, the lowest but one spoked like a wheel
  const ringLight = new THREE.MeshBasicMaterial({ color: new THREE.Color(1, 0.86, 0.62).multiplyScalar(2.3), side: THREE.DoubleSide });
  const housing = new THREE.MeshPhysicalMaterial({ color: 0x1a1714, metalness: 0.8, roughness: 0.35 });
  const wires: THREE.BufferGeometry[] = [], base = s.height > 3 ? top + 0.95 : 3.0;
  const RINGS = [[2.6, 1.7, 0.12, 0.4], [2.45, 1.35, -0.07, 1.9], [2.2, 0.85, 0.05, 0.9], [2.35, 0.4, -0.035, 2.6], [2.0, 0, 0.025, 1.2]];
  RINGS.forEach(([rad, dy, tilt, dir], k) => {
    const ring = new THREE.Group(); ring.position.set(0, base + dy, cz); ring.rotation.set(tilt * Math.cos(dir), 0, tilt * Math.sin(dir)); g.add(ring);
    ring.add(new THREE.Mesh(new THREE.CylinderGeometry(rad, rad, 0.085, 180, 1, true), ringLight));          // an LED band, lit all round
    if (k === 3) for (let q = 0; q < 16; q++) {
      const sp = new THREE.CylinderGeometry(0.004, 0.004, rad, 4); sp.rotateZ(Math.PI / 2); sp.translate(rad / 2, 0, 0); sp.rotateY(q * Math.PI / 8);
      ring.add(new THREE.Mesh(sp, housing));
    }
    for (let q = 0; q < 4; q++) {
      const a = q * Math.PI / 2 + k * 0.4, x = Math.sin(a) * rad, z = Math.cos(a) * rad, y = base + dy, len = H - y;
      const wire = new THREE.CylinderGeometry(0.003, 0.003, len, 4); wire.translate(x, y + len / 2, cz + z); wires.push(wire);
    }
  });
  g.add(new THREE.Mesh(mergeGeometries(wires), housing));
  for (let q = 0; q < 8; q++) {
    const a = q * Math.PI / 4, pl = new THREE.PointLight(0xffd8a0, oak ? 11 : 9, 20, 2); pl.position.set(Math.sin(a) * 2.1, base, cz + Math.cos(a) * 2.1); g.add(pl);
  }
  const key = keySpot(0xffe6c4, new THREE.Vector3(0.3, base + 0.6, cz + 0.4), s, oak ? 55 : 45, 0.8);
  g.add(key, key.target, new THREE.HemisphereLight(0x2a1d12, 0x050403, oak ? 0.26 : 0.18));
  dim(g, 0.8);   // a cellar's light: a fifth darker than first drafted
  scene.add(g);
  capture(scene, renderer, s.centre, 0.7);
  return g;
}
