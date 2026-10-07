// The surroundings. Each builds a real room around a subject (the tower, or the case on its plinth) and lights it;
// `?ambient=` picks one on either page, so one ambient can be judged for both layouts.
//   atelier      a dark gallery: polished black stone, tall softboxes, a key light in a little haze (the Tower)
//   travertine   a light stone hall with arched niches, sun through a mullioned window (the Case)
//   stage        a theatre stage before a red velvet curtain, under warm spotlights
//   library      a tall old library at night: walnut shelves on two tiers, a gallery, warm pendant globes
//   reading      library and atelier in one: the walnut stacks round a polished black floor, softboxes set into
//                the shelving, a key light in haze
//   rotunda      a circular video club after the Cité du Vin's round cellar: rings of racks of DVD and VHS cases,
//   rotunda-oak  a stack of luminous rings over the centre (noir: dark racks; oak: honey oak, brass and a gallery)
import * as THREE from 'three/webgpu';
import { EXRLoader } from 'three/addons/loaders/EXRLoader.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { canvasTexture, noise, rng } from './materials';
import { QUERY } from './stage';
import { asset, beam, beamBetween, capture, diffuser, dim, keySpot, polishedFloor, shadowy, type Subject } from './ambient-kit';
import { rotunda } from './rotunda';

export type { Subject };
export interface Ambient {
  id: AmbientId; group: THREE.Group; exposure: number; theme: 'dark' | 'light';
  /** a sunlit hall: dark lacquer reads warmer, and a room's own light needs a lift to hold its own */
  daylight?: boolean; roomPower?: number;
  update(t: number): void;
}

// ---------- Atelier ----------
export async function atelier(scene: THREE.Scene, renderer: THREE.WebGPURenderer, s: Subject): Promise<Ambient> {
  const g = new THREE.Group(), top = s.centre.y + s.height / 2;
  scene.background = new THREE.Color(0x060607); scene.fog = new THREE.FogExp2(0x060607, 0.03);
  // polished black stone: dark veined stone with a faint mirror of the room in it
  g.add(polishedFloor(new THREE.CircleGeometry(30, 96)));
  // a dark plaster wall with tall recessed softboxes, an overhead softbox above the subject
  const plaster = canvasTexture(512, 512, (c, w, h) => { c.fillStyle = '#16151a'; c.fillRect(0, 0, w, h); noise(c, w, h, 12, 7); }, { repeat: [10, 4] });
  const wall = new THREE.Mesh(new THREE.PlaneGeometry(44, 18), new THREE.MeshStandardMaterial({ map: plaster, roughness: 0.95 })); wall.position.set(0, 9, -7.3); g.add(wall);
  const bh = Math.min(7.2, Math.max(5.2, top + 1.2)), by = 0.8 + bh / 2;
  const glow = diffuser();
  for (const [x, k] of [[-4.4, 1], [4.4, 1], [-8.4, 0.55], [8.4, 0.55]]) {
    const box = new THREE.Mesh(new THREE.PlaneGeometry(0.6, bh), new THREE.MeshBasicMaterial({ map: glow, color: new THREE.Color(1, 0.93, 0.84).multiplyScalar(1.25 * k) }));
    box.position.set(x, by, -7.23); g.add(box);   // in front of its frame: coplanar faces z-fight on real GPUs
    const frame = new THREE.Mesh(new THREE.BoxGeometry(0.76, bh + 0.2, 0.1), new THREE.MeshStandardMaterial({ color: 0x0b0b0c, roughness: 0.5 })); frame.position.set(x, by, -7.34); g.add(frame);
    const rl = new THREE.RectAreaLight(0xffeedd, 4 * k, 0.6, bh); rl.position.set(x, by, -7.1); rl.lookAt(x * 0.2, s.centre.y, 0); g.add(rl);
  }
  const oy = top + 2.6, over = new THREE.Mesh(new THREE.PlaneGeometry(3.2, 1.5), new THREE.MeshBasicMaterial({ color: new THREE.Color(1, 0.96, 0.9).multiplyScalar(1.6) }));
  over.rotation.x = Math.PI / 2; over.position.set(0, oy, s.centre.z - 0.1); g.add(over);
  const down = new THREE.RectAreaLight(0xfff4e8, 5, 3.2, 1.5); down.position.set(0, oy - 0.02, s.centre.z - 0.1); down.lookAt(0, 0, s.centre.z - 0.1); g.add(down);
  const from = new THREE.Vector3(0.9, top + 4.5, s.centre.z + 2.2), spot = keySpot(0xfff1e0, from, s, 120);
  g.add(spot, spot.target, new THREE.HemisphereLight(0x2a2620, 0x050505, 0.4));
  g.add(beamBetween(0xffe6c8, from, new THREE.Vector3(s.centre.x, s.height > 3 ? top : 0, s.centre.z), 0.25, s.width * 0.9, 0.03));   // a tall subject: the beam ends on its roof
  scene.add(g);
  capture(scene, renderer, s.centre, 0.9);
  return { id: 'atelier', group: g, exposure: 0.9, theme: 'dark', update() {} };
}

// ---------- Travertine ----------
export async function travertine(scene: THREE.Scene, _renderer: THREE.WebGPURenderer, s: Subject): Promise<Ambient> {
  const g = new THREE.Group();
  const hdr = await new EXRLoader().loadAsync(asset('env/apartment.exr')); hdr.mapping = THREE.EquirectangularReflectionMapping;
  scene.environment = hdr; scene.environmentIntensity = 0.55;
  scene.background = new THREE.Color(0xe9dfd0); scene.fog = new THREE.Fog(0xe9dfd0, 14, 40);
  const trav = (rep: [number, number], seed: number) => canvasTexture(1024, 1024, (c, w, h) => {
    const r = rng(seed); c.fillStyle = '#ddd0bb'; c.fillRect(0, 0, w, h);
    for (let y = 0; y < h; y += 2) { const t = Math.sin(y * 0.02 + Math.sin(y * 0.003) * 4) * 0.5 + 0.5; c.fillStyle = `rgba(${150 + t * 40},${125 + t * 30},${95 + t * 20},${0.05 + r() * 0.05})`; c.fillRect(0, y, w, 2); }
    for (let k = 0; k < 700; k++) { c.fillStyle = `rgba(120,100,70,${0.15 + r() * 0.25})`; c.beginPath(); c.ellipse(r() * w, r() * h, 1 + r() * 5, 0.6 + r() * 1.4, 0, 0, 6.28); c.fill(); }
    noise(c, w, h, 10, seed);
  }, { repeat: rep });
  const tiles = canvasTexture(1024, 1024, (c, w, h) => {
    const base = trav([1, 1], 11).image as HTMLCanvasElement;
    for (let i = 0; i < 2; i++) for (let j = 0; j < 2; j++) c.drawImage(base, i * w / 2, j * h / 2, w / 2, h / 2);
    c.strokeStyle = 'rgba(120,100,75,.35)'; c.lineWidth = 3;
    for (let k = 0; k <= 2; k++) { c.beginPath(); c.moveTo(k * w / 2, 0); c.lineTo(k * w / 2, h); c.stroke(); c.beginPath(); c.moveTo(0, k * h / 2); c.lineTo(w, k * h / 2); c.stroke(); }
  }, { repeat: [8, 8] });
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(30, 30), new THREE.MeshPhysicalMaterial({ map: tiles, roughness: 0.5, clearcoat: 0.25, clearcoatRoughness: 0.3 }));
  floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; g.add(floor);
  const wallMat = new THREE.MeshStandardMaterial({ map: trav([3, 1], 12), roughness: 0.85 });
  // back wall with three arched niches; tall enough for the tower as well as the case
  const W = 16, H = Math.max(7, s.centre.y + s.height / 2 + 2), back = new THREE.Shape(); back.moveTo(-W / 2, 0); back.lineTo(W / 2, 0); back.lineTo(W / 2, H); back.lineTo(-W / 2, H); back.lineTo(-W / 2, 0);
  for (const x of [-4, 0, 4]) {
    const a = new THREE.Path(), w = 1.7, h = 3.4;
    a.moveTo(x - w / 2, 0.9); a.lineTo(x - w / 2, 0.9 + h); a.absarc(x, 0.9 + h, w / 2, Math.PI, 0, true); a.lineTo(x + w / 2, 0.9); a.lineTo(x - w / 2, 0.9); back.holes.push(a);
    const niche = new THREE.Mesh(new THREE.BoxGeometry(w, h + w / 2, 0.02), wallMat); niche.position.set(x, 0.9 + (h + w / 2) / 2, -6.6); g.add(niche);
    const sill = new THREE.Mesh(new THREE.BoxGeometry(w + 0.2, 0.1, 0.7), wallMat); sill.position.set(x, 0.85, -6.25); g.add(shadowy(sill));
  }
  const bw = new THREE.Mesh(new THREE.ExtrudeGeometry(back, { depth: 0.6, bevelEnabled: false, curveSegments: 32 }), wallMat); bw.position.z = -6.6; g.add(shadowy(bw));
  // left wall with a tall mullioned window; the sun comes through it
  const L = new THREE.Shape(); L.moveTo(-10, 0); L.lineTo(10, 0); L.lineTo(10, H); L.lineTo(-10, H); L.lineTo(-10, 0);
  const win = new THREE.Path(), wx = -1.2, ww = 2.4, wy = 0.8, wh = 4.2;
  win.moveTo(wx - ww / 2, wy); win.lineTo(wx + ww / 2, wy); win.lineTo(wx + ww / 2, wy + wh); win.absarc(wx, wy + wh, ww / 2, 0, Math.PI, false); win.lineTo(wx - ww / 2, wy); L.holes.push(win);
  const lw = new THREE.Mesh(new THREE.ExtrudeGeometry(L, { depth: 0.5, bevelEnabled: false, curveSegments: 32 }), wallMat); lw.rotation.y = Math.PI / 2; lw.position.set(-6, 0, 0); g.add(shadowy(lw));
  const mull = new THREE.MeshStandardMaterial({ color: 0x2b2620, roughness: 0.6, metalness: 0.3 });
  for (const [x, y, w, h] of [[0, wy + wh / 2 + 0.3, 0.05, wh + 1.1], [0, wy + 1.4, ww, 0.05], [0, wy + 2.8, ww, 0.05], [0, wy + 4.0, ww, 0.05]]) {
    const b = new THREE.Mesh(new THREE.BoxGeometry(0.06, h, w), mull); b.position.set(-5.75, y, -(wx + x)); g.add(shadowy(b));
  }
  const sun = new THREE.DirectionalLight(0xffe2b8, 5.5); sun.position.set(-16, 9.5, 2.5); sun.target.position.set(0, 0, -0.6); sun.castShadow = true; sun.shadow.mapSize.set(4096, 4096);
  Object.assign(sun.shadow.camera, { left: -9, right: 9, top: 9, bottom: -9, near: 1, far: 40 }); sun.shadow.bias = -0.0003; sun.shadow.normalBias = 0.02; g.add(sun, sun.target);
  g.add(new THREE.HemisphereLight(0xfff4e6, 0xc9b79c, 0.9));
  const bounce = new THREE.PointLight(0xffd9a8, 6, 12, 1.5); bounce.position.set(1.5, 0.6, 1.5); g.add(bounce);
  const shaft = beam(0xfff0d6, 0.9, 1.3, 13, 0.045); shaft.position.set(-3, 4.2, -0.8); shaft.rotation.set(0, 0, -1.03); g.add(shaft);
  scene.add(g);
  return { id: 'travertine', group: g, exposure: 0.9, theme: 'light', daylight: true, roomPower: 1.15, update() {} };
}

// ---------- Stage ----------
export async function stage(scene: THREE.Scene, renderer: THREE.WebGPURenderer, s: Subject): Promise<Ambient> {
  const g = new THREE.Group(), top = s.centre.y + s.height / 2, back = -5.6;
  scene.background = new THREE.Color(0x030202); scene.fog = new THREE.FogExp2(0x050303, 0.03);
  // the stage floor: dark stained boards, worn and waxed
  const boards = canvasTexture(1024, 1024, (c, w, h) => {
    const r = rng(21), n = 8; c.fillStyle = '#1b130e'; c.fillRect(0, 0, w, h);
    for (let i = 0; i < n; i++) {
      const y0 = i * h / n, tone = 22 + r() * 16;
      c.fillStyle = `rgb(${tone + 12},${tone * 0.66},${tone * 0.45})`; c.fillRect(0, y0, w, h / n);
      for (let k = 0; k < 90; k++) { c.strokeStyle = `rgba(0,0,0,${0.08 + r() * 0.12})`; c.lineWidth = 0.5 + r() * 1.5; const yy = y0 + r() * h / n; c.beginPath(); c.moveTo(0, yy); c.bezierCurveTo(w * 0.3, yy + (r() - 0.5) * 6, w * 0.6, yy + (r() - 0.5) * 6, w, yy + (r() - 0.5) * 4); c.stroke(); }
      c.fillStyle = 'rgba(0,0,0,.75)'; c.fillRect(0, y0, w, 2);
      const cut = r() * w; c.fillRect(cut, y0, 2, h / n);       // butt joints, staggered
    }
    for (let k = 0; k < 260; k++) { c.fillStyle = `rgba(255,240,220,${0.015 + r() * 0.02})`; c.fillRect(r() * w, r() * h, 2 + r() * 40, 1); }   // scuffs
    noise(c, w, h, 8, 22);
  }, { repeat: [12, 12] });
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(30, 30), new THREE.MeshPhysicalMaterial({ map: boards, roughness: 0.48, clearcoat: 0.35, clearcoatRoughness: 0.3 }));
  floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; g.add(floor);
  // the house curtain: red velvet in deep folds, pooling a little on the boards; a valance of swags above
  const velvet = new THREE.MeshPhysicalMaterial({ color: 0x4a070b, roughness: 0.78, sheen: 1, sheenColor: new THREE.Color(1, 0.32, 0.3), sheenRoughness: 0.32 });
  const cw = 28, ch = Math.max(12, top + 4), curtain = new THREE.PlaneGeometry(cw, ch, 560, 12), cp = curtain.attributes.position;
  for (let i = 0; i < cp.count; i++) {
    const x = cp.getX(i), y = cp.getY(i) + ch / 2, pool = 1 + 0.8 * Math.max(0, 1 - y / 0.35);
    cp.setZ(i, (0.17 * Math.sin(x * 2 * Math.PI / 0.62 + 0.7 * Math.sin(x * 0.83)) + 0.05 * Math.sin(x * 2 * Math.PI / 0.23 + 1.3)) * pool + (y < 0.35 ? (0.35 - y) * 0.5 : 0));
  }
  curtain.computeVertexNormals();
  const drape = new THREE.Mesh(curtain, velvet); drape.position.set(0, ch / 2, back); drape.receiveShadow = true; g.add(drape);
  const vh = 2.4, val = new THREE.PlaneGeometry(cw, vh, 560, 24), vp = val.attributes.position;
  for (let i = 0; i < vp.count; i++) {
    const x = vp.getX(i), y = vp.getY(i), sw = Math.abs(Math.sin(x * Math.PI / 2.8)), sag = (1 - sw) * 0.0 + sw * 0.55;
    vp.setY(i, y - (y < 0 ? sag * (1 - (y + vh / 2) / vh) * 0.9 : 0));
    vp.setZ(i, 0.1 * Math.sin(x * 2 * Math.PI / 0.4) * (0.5 + 0.5 * (1 - (y + vh / 2) / vh)) + 0.35 + 0.25 * sw);
  }
  val.computeVertexNormals();
  const valance = new THREE.Mesh(val, velvet); valance.position.set(0, ch - vh / 2, back); g.add(valance);
  // black masking legs at the sides, a dark proscenium beyond
  const black = new THREE.MeshPhysicalMaterial({ color: 0x080707, roughness: 0.9, sheen: 0.6, sheenColor: new THREE.Color(0.2, 0.2, 0.22) });
  for (const sx of [-1, 1]) {
    const leg = new THREE.PlaneGeometry(3, ch, 60, 1), lp = leg.attributes.position;
    for (let i = 0; i < lp.count; i++) lp.setZ(i, 0.12 * Math.sin(lp.getX(i) * 2 * Math.PI / 0.7));
    leg.computeVertexNormals(); const m = new THREE.Mesh(leg, black); m.position.set(sx * 10.5, ch / 2, back + 2.2); m.rotation.y = -sx * 0.25; g.add(m);
  }
  // light: two warm front-of-house spots on the subject, footlight washes glowing up the curtain, a cool backlight
  const foh = [new THREE.Vector3(-6.5, top + 7, s.centre.z + 10), new THREE.Vector3(5.5, top + 7.5, s.centre.z + 9)];
  foh.forEach((p, k) => {
    const sp = keySpot(0xffd6a0, p, s, k ? 70 : 95, 0.9); sp.castShadow = k === 0; g.add(sp, sp.target);
    g.add(beamBetween(0xffd9b0, p, new THREE.Vector3(s.centre.x, 0, s.centre.z), 0.2, Math.max(s.width * 1.2, s.height * 0.5), 0.018));
  });
  for (const x of [-7, 0, 7]) {
    const wash = new THREE.SpotLight(0xff8a50, 60, 16, 0.75, 0.9, 1.4); wash.position.set(x, 0.15, back + 1.4); wash.target.position.set(x, 7, back); g.add(wash, wash.target);
  }
  const rim = new THREE.SpotLight(0xb8ccff, 40 * ((top + 6) / 5) ** 1.6, 40, 0.5, 0.8, 1.6); rim.position.set(0, top + 6, back + 1.2); rim.target.position.copy(s.centre); g.add(rim, rim.target);
  g.add(new THREE.HemisphereLight(0x1d0f0b, 0x000000, 0.22));
  scene.add(g);
  capture(scene, renderer, s.centre, 0.8);
  return { id: 'stage', group: g, exposure: 0.95, theme: 'dark', update() {} };
}

// ---------- Library ----------
const ROWS = 16;
/** Book spines: one tall texture of 16 shelf rows; every bay shows a different stretch of it. */
function bookTexture() {
  const t = canvasTexture(2048, 2048, (c, w, h) => {
    const r = rng(41), rh = h / ROWS;
    const pal = [[92, 22, 20], [36, 52, 34], [28, 36, 62], [120, 84, 46], [22, 20, 18], [140, 112, 62], [70, 30, 24], [54, 60, 44], [104, 96, 80], [40, 28, 22]];
    c.fillStyle = '#0a0705'; c.fillRect(0, 0, w, h);
    for (let row = 0; row < ROWS; row++) {
      let x = 0; const y1 = (row + 1) * rh;
      while (x < w) {
        const bw = 10 + r() * 26, bh = rh * (0.62 + r() * 0.33), p = pal[Math.floor(r() * pal.length)], v = 0.7 + r() * 0.5;
        if (r() < 0.04) { x += 8 + r() * 30; continue; }          // a gap where a book is out
        const lean = r() < 0.03 ? 0.08 : 0;
        c.save(); c.translate(x, y1); c.rotate(lean);
        const grd = c.createLinearGradient(0, 0, bw, 0); const col = (k: number) => `rgb(${p[0] * v * k},${p[1] * v * k},${p[2] * v * k})`;
        grd.addColorStop(0, col(0.55)); grd.addColorStop(0.35, col(1.05)); grd.addColorStop(1, col(0.6));
        c.fillStyle = grd; c.fillRect(0, -bh, bw - 1.5, bh);
        if (r() < 0.6) { c.fillStyle = `rgba(200,160,80,${0.35 + r() * 0.3})`; const by = -bh * (0.78 + r() * 0.1); c.fillRect(1, by, bw - 3.5, 2); c.fillRect(1, by - 6, bw - 3.5, 1.2); }
        if (r() < 0.4) { c.fillStyle = 'rgba(210,175,100,.45)'; c.fillRect(bw * 0.3, -bh * 0.55, bw * 0.35, bh * 0.18); }
        c.restore(); x += bw;
      }
      c.fillStyle = 'rgba(0,0,0,.6)'; c.fillRect(0, row * rh, w, rh * 0.06);   // the shelf above casts a shadow
    }
  });
  t.wrapS = t.wrapT = THREE.RepeatWrapping; return t;
}

const walnut = () => new THREE.MeshPhysicalMaterial({ color: 0x3a2214, roughness: 0.5, clearcoat: 0.4, clearcoatRoughness: 0.35 });
const brassMat = () => new THREE.MeshPhysicalMaterial({ color: 0xb08a4c, metalness: 1, roughness: 0.32 });

/** Walnut bookcases on two tiers along the four walls of a square room (half-width `half`), a gallery walkway with a
 * brass rail at the second tier, a dark coffered ceiling. `open(wall, bay, bays)` leaves a bay empty (a light slot). */
function stacks(g: THREE.Group, cz: number, half: number, tier: number, H: number, open: (wall: number, bay: number, bays: number) => boolean = () => false, upper = 4.08) {
  const books = bookTexture(), wood = walnut(), brass = brassMat();
  const frames: THREE.BufferGeometry[] = [], spines: THREE.BufferGeometry[] = [], r = rng(51);
  const bay = 1.1, shelf = 0.36, depth = 0.42, L = 2 * half - 1.2, n = Math.floor(L / bay);
  for (let wall = 0; wall < 4; wall++) {
    // one run of bookcases along each wall, its back to the wall, its books facing the room
    const place = (geo: THREE.BufferGeometry) => { geo.translate(0, 0, -half + depth + 0.02); geo.rotateY(wall * Math.PI / 2); geo.translate(0, 0, cz); return geo; };
    for (const [y0, y1] of [[0, tier - 0.2], [tier + 0.12, tier + 0.12 + upper]]) {
      const rows = Math.floor((y1 - y0 - 0.2) / shelf);
      for (let b = 0; b < n; b++) {
        const x0 = -L / 2 + b * bay;
        frames.push(place(new THREE.BoxGeometry(0.05, y1 - y0, depth).translate(x0, (y0 + y1) / 2, -depth / 2)));
        if (b === n - 1) frames.push(place(new THREE.BoxGeometry(0.05, y1 - y0, depth).translate(x0 + bay, (y0 + y1) / 2, -depth / 2)));
        if (open(wall, b, n)) continue;
        const back = new THREE.PlaneGeometry(bay - 0.05, rows * shelf);
        const u0 = r(), v0 = Math.floor(r() * (ROWS - rows)) / ROWS, uv = back.attributes.uv;
        for (let i = 0; i < uv.count; i++) uv.setXY(i, u0 + uv.getX(i) * 0.5, v0 + uv.getY(i) * rows / ROWS);
        back.translate(x0 + bay / 2, y0 + 0.2 + rows * shelf / 2, -depth + 0.06); spines.push(place(back));
        for (let k = 0; k <= rows; k++) frames.push(place(new THREE.BoxGeometry(bay, 0.03, depth).translate(x0 + bay / 2, y0 + 0.2 + k * shelf - 0.015, -depth / 2)));
      }
      frames.push(place(new THREE.BoxGeometry(L, 0.14, depth + 0.08).translate(0, y1 + 0.07, -depth / 2)));
      frames.push(place(new THREE.BoxGeometry(L, 0.2, depth + 0.04).translate(0, y0 + 0.1, -depth / 2 + 0.02)));
    }
  }
  g.add(new THREE.Mesh(mergeGeometries(frames), wood), new THREE.Mesh(mergeGeometries(spines), new THREE.MeshStandardMaterial({ map: books, roughness: 0.75 })));
  // the gallery: a walkway at the second tier with a brass rail
  const gal: THREE.BufferGeometry[] = [], rails: THREE.BufferGeometry[] = [];
  for (let k = 0; k < 4; k++) {
    const put = (geo: THREE.BufferGeometry, list: THREE.BufferGeometry[]) => { geo.rotateY(k * Math.PI / 2); geo.translate(0, 0, cz); list.push(geo); };
    put(new THREE.BoxGeometry(L, 0.14, 1.0).translate(0, tier + 0.05, half - 0.95), gal);
    const rail = new THREE.CylinderGeometry(0.025, 0.025, L, 8); rail.rotateZ(Math.PI / 2); rail.translate(0, tier + 1.05, half - 1.42); put(rail, rails);
    for (let x = -L / 2; x <= L / 2; x += 0.55) put(new THREE.CylinderGeometry(0.012, 0.012, 0.95, 6).translate(x, tier + 0.6, half - 1.42), rails);
  }
  g.add(new THREE.Mesh(mergeGeometries(gal), wood), new THREE.Mesh(mergeGeometries(rails), brass));
  // a dark coffered ceiling
  const ceil = new THREE.Mesh(new THREE.PlaneGeometry(2 * half, 2 * half), new THREE.MeshStandardMaterial({ color: 0x1a110b, roughness: 0.8 })); ceil.rotation.x = Math.PI / 2; ceil.position.set(0, H, cz); g.add(ceil);
  const beams: THREE.BufferGeometry[] = [];
  for (let k = -4; k <= 4; k++) { beams.push(new THREE.BoxGeometry(2 * half, 0.4, 0.3).translate(0, H - 0.2, cz + k * 2.4)); beams.push(new THREE.BoxGeometry(0.3, 0.4, 2 * half).translate(k * 2.4, H - 0.2, cz)); }
  g.add(new THREE.Mesh(mergeGeometries(beams), wood));
  return { brass };
}

/** Warm glass globes on brass rods from the ceiling, each a light. */
function globes(g: THREE.Group, at: [number, number][], y: number, H: number, cz: number, brass: THREE.Material, candela = 26) {
  const glow = new THREE.MeshBasicMaterial({ color: new THREE.Color(1, 0.78, 0.5).multiplyScalar(2.2) });
  for (const [x, z] of at) {
    const globe = new THREE.Mesh(new THREE.SphereGeometry(0.26, 24, 16), glow); globe.position.set(x, y, cz + z); g.add(globe);
    const rod = new THREE.Mesh(new THREE.CylinderGeometry(0.01, 0.01, H - y - 0.26, 6), brass); rod.position.set(x, (H + y + 0.26) / 2, cz + z); g.add(rod);
    const pl = new THREE.PointLight(0xffc68a, candela, 22, 2); pl.position.copy(globe.position); g.add(pl);
  }
}

export async function library(scene: THREE.Scene, renderer: THREE.WebGPURenderer, s: Subject): Promise<Ambient> {
  const g = new THREE.Group(), cz = s.centre.z, half = 11, tier = 4.6, H = 13.5;
  scene.background = new THREE.Color(0x0b0806); scene.fog = new THREE.FogExp2(0x0d0906, 0.022);
  // oak parquet in herringbone, waxed
  const parquet = canvasTexture(1024, 1024, (c, w, h) => {
    const r = rng(31); c.fillStyle = '#3a2516'; c.fillRect(0, 0, w, h);
    const L = 128, Wd = 32;
    for (let row = -2; row < h / Wd + 4; row++) for (let col = -2; col < w / L + 3; col++) for (const dir of [1, -1]) {
      c.save(); c.translate(col * L + (dir > 0 ? 0 : L / 2), row * Wd * 2 + (dir > 0 ? 0 : Wd)); c.rotate(dir * Math.PI / 4);
      const t = 46 + r() * 30; c.fillStyle = `rgb(${t + 40},${t + 14},${t - 8})`; c.fillRect(0, 0, L * 0.7, Wd * 0.7);
      c.strokeStyle = 'rgba(20,10,4,.55)'; c.lineWidth = 1.2; c.strokeRect(0, 0, L * 0.7, Wd * 0.7);
      for (let k = 0; k < 5; k++) { c.strokeStyle = `rgba(30,15,5,${0.1 + r() * 0.15})`; c.beginPath(); const yy = r() * Wd * 0.7; c.moveTo(0, yy); c.lineTo(L * 0.7, yy + (r() - 0.5) * 3); c.stroke(); }
      c.restore();
    }
    noise(c, w, h, 8, 32);
  }, { repeat: [14, 14] });
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(2 * half, 2 * half), new THREE.MeshPhysicalMaterial({ map: parquet, roughness: 0.42, clearcoat: 0.45, clearcoatRoughness: 0.2 }));
  floor.rotation.x = -Math.PI / 2; floor.position.z = cz; floor.receiveShadow = true; g.add(floor);
  const { brass } = stacks(g, cz, half, tier, H);
  globes(g, [[-5, -5], [5, -5], [-5, 5], [5, 5], [0, -8], [0, 8]], Math.max(8, s.centre.y + s.height / 2 + 2.6), H, cz, brass);
  const from = new THREE.Vector3(1.5, s.centre.y + s.height / 2 + 5, cz + 3), spot = keySpot(0xffe2bc, from, s, 70);
  g.add(spot, spot.target, new THREE.HemisphereLight(0x2a1c12, 0x0a0604, 0.35));
  const moon = new THREE.DirectionalLight(0x9fb4e8, 0.5); moon.position.set(-8, 12, -4); g.add(moon);
  scene.add(g);
  capture(scene, renderer, s.centre, 0.85);
  return { id: 'library', group: g, exposure: 1.0, theme: 'dark', update() {} };
}

// ---------- Reading room: a grand library hall ----------
// After the George Peabody Library (tiers of black and gilt cast-iron galleries round a tall atrium) and the Royal
// Portuguese Reading Room (dark carved wood, a chandelier), with the atelier's polished floor and key light in haze.
export async function reading(scene: THREE.Scene, renderer: THREE.WebGPURenderer, s: Subject): Promise<Ambient> {
  const g = new THREE.Group(), cz = s.centre.z, half = 8.8, TIER = 3.6, TIERS = 4, H = 18, top = s.centre.y + s.height / 2;
  const deck = 1.15, depth = 0.42, bay = 1.1, shelf = 0.36, L = 2 * half - 0.2, n = Math.floor(L / bay), x0w = -n * bay / 2;
  scene.background = new THREE.Color(0x070605); scene.fog = new THREE.FogExp2(0x080605, 0.016);
  // a marble floor in black and warm grey squares, polished to a faint sheen
  const marble = canvasTexture(1024, 1024, (c, w, h) => {
    const r = rng(61);
    for (let i = 0; i < 2; i++) for (let j = 0; j < 2; j++) {
      c.fillStyle = (i + j) % 2 ? '#2a2622' : '#0b0a0a'; c.fillRect(i * w / 2, j * h / 2, w / 2, h / 2);
    }
    for (let k = 0; k < 90; k++) {
      c.strokeStyle = `rgba(200,190,175,${0.03 + r() * 0.05})`; c.lineWidth = 0.5 + r() * 1.2; c.beginPath();
      let x = r() * w, y = r() * h; c.moveTo(x, y); for (let q = 0; q < 7; q++) { x += (r() - 0.45) * 120; y += (r() - 0.5) * 80; c.lineTo(x, y); } c.stroke();
    }
    c.strokeStyle = 'rgba(0,0,0,.6)'; c.lineWidth = 2; for (let k = 0; k <= 2; k++) { c.beginPath(); c.moveTo(k * w / 2, 0); c.lineTo(k * w / 2, h); c.stroke(); c.beginPath(); c.moveTo(0, k * h / 2); c.lineTo(w, k * h / 2); c.stroke(); }
    noise(c, w, h, 8, 62);
  }, { repeat: [11, 11] });
  const floor = polishedFloor(new THREE.PlaneGeometry(2 * half, 2 * half), { map: marble, mirror: 0.3, coat: 0.6, coatRough: 0.2 }); floor.position.z = cz; g.add(floor);

  const books = bookTexture(), wood = walnut(), brass = brassMat();
  const iron = new THREE.MeshPhysicalMaterial({ color: 0x121212, metalness: 0.6, roughness: 0.45 });
  const gilt = new THREE.MeshPhysicalMaterial({ color: 0xc9a050, metalness: 1, roughness: 0.28 });
  const oak = new THREE.MeshPhysicalMaterial({ color: 0x7a5232, roughness: 0.55, clearcoat: 0.3 });
  const parts = { wood: [] as THREE.BufferGeometry[], books: [] as THREE.BufferGeometry[], iron: [] as THREE.BufferGeometry[], gilt: [] as THREE.BufferGeometry[], oak: [] as THREE.BufferGeometry[] };
  const r = rng(51);
  // everything is built for the back wall (z = -half, facing +z) and turned to the other three
  for (let wall = 0; wall < 4; wall++) {
    const put = (list: THREE.BufferGeometry[], geo: THREE.BufferGeometry) => { geo.rotateY(wall * Math.PI / 2); geo.translate(0, 0, cz); list.push(geo); };
    const zf = -half + depth;   // the face of the bookcases
    for (let t = 0; t < TIERS; t++) {
      const y0 = t * TIER + (t ? 0.16 : 0), y1 = (t + 1) * TIER - 0.2, rows = Math.floor((y1 - y0 - 0.22) / shelf);
      for (let b = 0; b < n; b++) {
        const x = x0w + b * bay;
        put(parts.wood, new THREE.BoxGeometry(0.06, y1 - y0, depth).translate(x, (y0 + y1) / 2, zf - depth / 2));
        if (b === n - 1) put(parts.wood, new THREE.BoxGeometry(0.06, y1 - y0, depth).translate(x + bay, (y0 + y1) / 2, zf - depth / 2));
        const back = new THREE.PlaneGeometry(bay - 0.06, rows * shelf), uv = back.attributes.uv;
        const u0 = r(), v0 = Math.floor(r() * (ROWS - rows)) / ROWS;
        for (let i = 0; i < uv.count; i++) uv.setXY(i, u0 + uv.getX(i) * 0.5, v0 + uv.getY(i) * rows / ROWS);
        back.translate(x + bay / 2, y0 + 0.2 + rows * shelf / 2, zf - depth + 0.06); put(parts.books, back);
        for (let k = 0; k <= rows; k++) put(parts.wood, new THREE.BoxGeometry(bay, 0.03, depth).translate(x + bay / 2, y0 + 0.2 + k * shelf - 0.015, zf - depth / 2));
      }
      put(parts.wood, new THREE.BoxGeometry(L, 0.16, depth + 0.1).translate(0, y1 + 0.08, zf - depth / 2 + 0.05));      // cornice
      put(parts.wood, new THREE.BoxGeometry(L, 0.2, depth + 0.04).translate(0, y0 + 0.1, zf - depth / 2 + 0.02));        // plinth
      put(parts.gilt, new THREE.BoxGeometry(L, 0.012, 0.012).translate(0, y1 + 0.17, zf + 0.06));                        // a gilt line on the cornice
      put(parts.gilt, new THREE.CylinderGeometry(0.012, 0.012, L, 8).rotateZ(Math.PI / 2).translate(0, y1 - 0.12, zf + 0.09));   // the ladder rail
      if (t === 0) continue;
      // the gallery of this tier: a deck, its fascia with a gilt band, an iron balustrade with a gilded handrail
      // decks run corner to corner (the side walls' a hair lower, so the corners do not flicker); the balustrade runs
      // along the deck edge from one inner corner to the other
      const yd = t * TIER - (wall % 2) * 0.003, ze = zf + deck, Ld = -2 * zf, Lr = -2 * ze;
      put(parts.wood, new THREE.BoxGeometry(Ld, 0.14, deck).translate(0, yd + 0.07, zf + deck / 2));
      put(parts.iron, new THREE.BoxGeometry(Lr, 0.34, 0.05).translate(0, yd - 0.1, ze));
      put(parts.gilt, new THREE.BoxGeometry(Lr, 0.03, 0.06).translate(0, yd - 0.02, ze + 0.005));
      put(parts.gilt, new THREE.BoxGeometry(Lr, 0.045, 0.07).translate(0, yd + 1.02, ze));
      put(parts.iron, new THREE.BoxGeometry(Lr, 0.03, 0.03).translate(0, yd + 0.18, ze));
      for (let x = -Lr / 2; x <= Lr / 2; x += 0.14) put(parts.iron, new THREE.BoxGeometry(0.016, 0.82, 0.016).translate(x, yd + 0.6, ze));
      // brackets under the deck
      for (let b = 1; b < n; b += 2) put(parts.iron, new THREE.BoxGeometry(0.05, 0.05, deck).translate(x0w + b * bay, yd - 0.28, zf + deck / 2));
    }
    // slender iron columns at the gallery edge, with gilt rings at every deck
    for (let x = -L / 2 + deck + 1.6; x < L / 2 - deck - 1; x += 3.3) {
      put(parts.iron, new THREE.CylinderGeometry(0.065, 0.08, (TIERS - 1) * TIER + 1.0, 16).translate(x, ((TIERS - 1) * TIER + 1.0) / 2, zf + deck - 0.02));
      for (let t = 1; t < TIERS; t++) put(parts.gilt, new THREE.CylinderGeometry(0.1, 0.1, 0.06, 16).translate(x, t * TIER - 0.32, zf + deck - 0.02));
    }
    // a frieze between the top tier and the ceiling
    put(parts.wood, new THREE.BoxGeometry(2 * half, H - TIERS * TIER, 0.1).translate(0, TIERS * TIER + (H - TIERS * TIER) / 2, -half + 0.05));
    put(parts.gilt, new THREE.BoxGeometry(2 * half, 0.04, 0.04).translate(0, TIERS * TIER + 0.6, -half + 0.12));
  }
  // rolling library ladders: two on the floor, one on the first gallery, hooked on the brass rails
  const ladder = (wall: number, x: number, y0: number, h: number) => {
    const zf = -half + depth, lean = 0.62, put = (geo: THREE.BufferGeometry, list: THREE.BufferGeometry[]) => {
      geo.rotateX(-Math.atan2(lean, h)); geo.translate(x, y0, zf + lean + 0.06); geo.rotateY(wall * Math.PI / 2); geo.translate(0, 0, cz); list.push(geo);
    };
    for (const sx of [-0.24, 0.24]) put(new THREE.BoxGeometry(0.05, h, 0.07).translate(sx, h / 2, 0), parts.oak);
    for (let k = 1; k * 0.3 < h - 0.1; k++) put(new THREE.CylinderGeometry(0.016, 0.016, 0.48, 8).rotateZ(Math.PI / 2).translate(0, k * 0.3, 0), parts.oak);
    for (const sx of [-0.24, 0.24]) put(new THREE.CylinderGeometry(0.035, 0.035, 0.03, 12).rotateZ(Math.PI / 2).translate(sx, 0.035, 0), parts.gilt);
  };
  ladder(0, -2.1, 0, 3.35); ladder(1, 3.4, 0, 3.35); ladder(3, -1.2, TIER, 3.3);
  // long reading tables on the floor with green banker's lamps
  const lampLight = new THREE.MeshBasicMaterial({ color: new THREE.Color(0.2, 0.62, 0.32).multiplyScalar(1.6) });
  for (const sx of [-1, 1]) {
    const tx = sx * 5.2;
    parts.oak.push(new THREE.BoxGeometry(1.1, 0.06, 4.2).translate(tx, 0.76, cz));
    for (const dx of [-0.42, 0.42]) for (const dz of [-1.9, 1.9]) parts.oak.push(new THREE.BoxGeometry(0.08, 0.73, 0.08).translate(tx + dx, 0.365, cz + dz));
    for (const dz of [-1.3, 0, 1.3]) {
      const shade = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.12, 0.09, 20, 1, true), lampLight); shade.position.set(tx, 1.18, cz + dz); g.add(shade);
      parts.gilt.push(new THREE.CylinderGeometry(0.012, 0.012, 0.36, 8).translate(tx, 0.97, cz + dz));
      parts.gilt.push(new THREE.CylinderGeometry(0.08, 0.09, 0.025, 20).translate(tx, 0.8, cz + dz));
    }
    const pl = new THREE.PointLight(0xffd6a0, 7, 7, 2); pl.position.set(tx, 1.05, cz); g.add(pl);
  }
  const add = (list: THREE.BufferGeometry[], m: THREE.Material) => g.add(new THREE.Mesh(mergeGeometries(list.map(x => x.index ? x.toNonIndexed() : x)), m));
  add(parts.wood, wood); add(parts.iron, iron); add(parts.gilt, gilt); add(parts.oak, oak);
  g.add(new THREE.Mesh(mergeGeometries(parts.books), new THREE.MeshStandardMaterial({ map: books, roughness: 0.75 })));
  // the ceiling: dark coffers round a laylight of glass panes, lit from above
  const ceil = new THREE.Mesh(new THREE.PlaneGeometry(2 * half, 2 * half), new THREE.MeshStandardMaterial({ color: 0x150e09, roughness: 0.85 })); ceil.rotation.x = Math.PI / 2; ceil.position.set(0, H, cz); g.add(ceil);
  const lay = 7.2, glassPane = canvasTexture(512, 512, (c, w, h) => {
    const gr = c.createRadialGradient(w / 2, h / 2, 10, w / 2, h / 2, w * 0.7); gr.addColorStop(0, '#fff3dc'); gr.addColorStop(1, '#c9b08a'); c.fillStyle = gr; c.fillRect(0, 0, w, h);
    c.strokeStyle = '#1a1410'; c.lineWidth = 7; for (let k = 0; k <= 8; k++) { c.beginPath(); c.moveTo(k * w / 8, 0); c.lineTo(k * w / 8, h); c.stroke(); c.beginPath(); c.moveTo(0, k * h / 8); c.lineTo(w, k * h / 8); c.stroke(); }
  });
  const laylight = new THREE.Mesh(new THREE.PlaneGeometry(lay, lay), new THREE.MeshBasicMaterial({ map: glassPane, color: new THREE.Color(1, 0.95, 0.86).multiplyScalar(0.75) }));
  laylight.rotation.x = Math.PI / 2; laylight.position.set(0, H - 0.02, cz); g.add(laylight);
  const sky = new THREE.RectAreaLight(0xfff0d8, 2.2, lay, lay); sky.position.set(0, H - 0.05, cz); sky.lookAt(0, 0, cz); g.add(sky);
  const beams: THREE.BufferGeometry[] = [];
  for (let k = -3; k <= 3; k++) {
    if (Math.abs(k) <= 1) continue;
    beams.push(new THREE.BoxGeometry(2 * half, 0.45, 0.3).translate(0, H - 0.22, cz + k * 2.4), new THREE.BoxGeometry(0.3, 0.45, 2 * half).translate(k * 2.4, H - 0.22, cz));
  }
  for (const k of [-1, 1]) beams.push(new THREE.BoxGeometry(lay + 0.6, 0.5, 0.3).translate(0, H - 0.25, cz + k * (lay / 2 + 0.15)), new THREE.BoxGeometry(0.3, 0.5, lay + 0.6).translate(k * (lay / 2 + 0.15), H - 0.25, cz));
  g.add(new THREE.Mesh(mergeGeometries(beams), wood));
  // a brass chandelier over the tower: two hoops of candle bulbs on a chain from the laylight
  const cy = Math.max(top + 3.2, 9.5), bulb = new THREE.MeshBasicMaterial({ color: new THREE.Color(1, 0.8, 0.52).multiplyScalar(2.4) });
  const chand: THREE.BufferGeometry[] = [], bulbs: THREE.BufferGeometry[] = [];
  for (const [rad, dy, count] of [[1.35, 0, 18], [0.85, 0.55, 12]] as const) {
    chand.push(new THREE.TorusGeometry(rad, 0.03, 10, 96).rotateX(Math.PI / 2).translate(0, cy + dy, cz));
    for (let q = 0; q < count; q++) {
      const a = q * Math.PI * 2 / count, x = Math.sin(a) * rad, z = cz + Math.cos(a) * rad;
      chand.push(new THREE.CylinderGeometry(0.028, 0.035, 0.14, 10).translate(x, cy + dy + 0.08, z));
      bulbs.push(new THREE.SphereGeometry(0.032, 10, 8).scale(1, 1.6, 1).translate(x, cy + dy + 0.2, z));
    }
    for (let q = 0; q < 6; q++) {
      const a = q * Math.PI / 3, len = Math.hypot(rad, 1.4);
      const arm = new THREE.CylinderGeometry(0.008, 0.008, len, 6); arm.rotateZ(-Math.atan2(rad, 1.4)); arm.translate(rad / 2, cy + dy + 0.7, 0); arm.rotateY(a); arm.translate(0, 0, cz); chand.push(arm);
    }
  }
  chand.push(new THREE.CylinderGeometry(0.012, 0.012, H - cy - 1.4, 6).translate(0, (H + cy + 1.4) / 2, cz), new THREE.SphereGeometry(0.12, 16, 12).translate(0, cy + 1.4, cz));
  g.add(new THREE.Mesh(mergeGeometries(chand.map(x => x.index ? x.toNonIndexed() : x)), gilt), new THREE.Mesh(mergeGeometries(bulbs), bulb));
  for (let q = 0; q < 4; q++) { const a = q * Math.PI / 2, pl = new THREE.PointLight(0xffcf96, 14, 16, 2); pl.position.set(Math.sin(a) * 1.1, cy + 0.15, cz + Math.cos(a) * 1.1); g.add(pl); }
  // the atelier in it: a key light on the subject, in a little haze
  const from = new THREE.Vector3(0.9, Math.min(top + 5, H - 1), cz + 2.2), spot = keySpot(0xfff1e0, from, s, 100);
  g.add(spot, spot.target, new THREE.HemisphereLight(0x2e2218, 0x060504, 0.34));
  g.add(beamBetween(0xffe6c8, from, new THREE.Vector3(s.centre.x, s.height > 3 ? top : 0, cz), 0.25, s.width * 0.9, 0.024));
  dim(g, 1.1);
  scene.add(g);
  capture(scene, renderer, s.centre, 0.9);
  return { id: 'reading', group: g, exposure: 0.95, theme: 'dark', update() {} };
}

// ---------- Rotunda: the circular video club ----------
const noirRotunda = async (scene: THREE.Scene, renderer: THREE.WebGPURenderer, s: Subject): Promise<Ambient> =>
  ({ id: 'rotunda', group: await rotunda(scene, renderer, s, 'noir'), exposure: 0.95, theme: 'dark', update() {} });
const oakRotunda = async (scene: THREE.Scene, renderer: THREE.WebGPURenderer, s: Subject): Promise<Ambient> =>
  ({ id: 'rotunda-oak', group: await rotunda(scene, renderer, s, 'oak'), exposure: 1.0, theme: 'dark', update() {} });

const BUILDERS = { atelier, travertine, stage, library, reading, rotunda: noirRotunda, 'rotunda-oak': oakRotunda } as const;
export type AmbientId = keyof typeof BUILDERS;
export const AMBIENT_IDS = Object.keys(BUILDERS) as AmbientId[];

/** The page's ambient: its own by default, or `?ambient=<id>` to try another. */
export function buildAmbient(fallback: AmbientId, scene: THREE.Scene, renderer: THREE.WebGPURenderer, s: Subject) {
  const q = QUERY.get('ambient') as AmbientId | null, id = q && q in BUILDERS ? q : fallback;
  return BUILDERS[id](scene, renderer, s).then(a => { document.documentElement.dataset.theme = a.theme; return a; });
}
