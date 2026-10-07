// The case: a lacquer plinth with a brass band, a bronze rim, frameless glass with a lid, and an engraved plate.
// Its inner size is CASE, so every title's room stands in the same box.
import * as THREE from 'three/webgpu';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { CASE, GLASS } from './module';
import { glass, glassEdge, lacquer, brass, bronze, plateMaterial } from './materials';

function box(parent: THREE.Object3D, w: number, h: number, d: number, mat: THREE.Material, x: number, y: number, z: number, r = 0) {
  const m = new THREE.Mesh(r ? new RoundedBoxGeometry(w, h, d, 3, r) : new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x, y, z); m.castShadow = m.receiveShadow = true; parent.add(m); return m;
}

/** Glass walls and a lid around an inner box of CASE size, from y0 up. */
function glassBox(parent: THREE.Object3D, y0: number) {
  const W = CASE.w, D = CASE.d, H = CASE.h, t = GLASS.pane, yc = y0 + H / 2, top = y0 + H;
  const pane = (w: number, h: number, d: number, x: number, y: number, z: number) => {
    const m = box(parent, w, h, d, glass, x, y, z); m.castShadow = false; m.receiveShadow = false; m.renderOrder = 2;
  };
  pane(W + 2 * t, H, t, 0, yc, D / 2 + t / 2); pane(W + 2 * t, H, t, 0, yc, -D / 2 - t / 2);
  pane(t, H, D, W / 2 + t / 2, yc, 0); pane(t, H, D, -W / 2 - t / 2, yc, 0);
  pane(W + 2 * t, t, D + 2 * t, 0, top + t / 2, 0);
  // only the edges of thick glass catch the light
  const e = 0.0045, edge = (w: number, h: number, d: number, x: number, y: number, z: number) => { box(parent, w, h, d, glassEdge, x, y, z).castShadow = false; };
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) edge(e, H, e, sx * (W / 2 + t / 2), yc, sz * (D / 2 + t / 2));
  const yl = top + t / 2;
  for (const sz of [-1, 1]) edge(W + 2 * t, e, e, 0, yl, sz * (D / 2 + t / 2));
  for (const sx of [-1, 1]) edge(e, e, D + 2 * t, sx * (W / 2 + t / 2), yl, 0);
}

export interface Vitrine { group: THREE.Group; stage: THREE.Group; top: number; setLabel(text: string): void }

export function buildCase({ base = 0.95, label = '' } = {}): Vitrine {
  const g = new THREE.Group(), W = CASE.w, D = CASE.d;
  box(g, W + 0.14, base, D + 0.14, lacquer, 0, base / 2, 0, 0.012);
  box(g, W + 0.15, 0.012, D + 0.15, brass, 0, base - 0.03, 0);
  const rim = 0.025; box(g, W + 0.04, rim, D + 0.04, bronze, 0, base + rim / 2, 0);
  const y0 = base + rim, stage = new THREE.Group(); stage.position.y = y0; g.add(stage);
  glassBox(g, y0);
  const plate = new THREE.Mesh(new THREE.PlaneGeometry(0.62, 0.087), plateMaterial(label));
  plate.position.set(0, base * 0.62, D / 2 + 0.0705); g.add(plate);
  return {
    group: g, stage, top: y0 + CASE.h,
    setLabel(text) { const old = plate.material; plate.material = plateMaterial(text); old.map?.dispose(); old.dispose(); },
  };
}
