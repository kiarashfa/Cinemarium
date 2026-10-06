// The case for the one-at-a-time layout: a lacquer plinth with a brass band, a bronze rim, frameless
// glass and an engraved plate. Its inner size is CASE, the same box every tower floor has.
import * as THREE from 'three/webgpu';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { CASE, GLASS } from './module';
import { glass, glassEdge, lacquer, brass, bronze, plateMaterial } from './materials';

export function box(parent: THREE.Object3D, w: number, h: number, d: number, mat: THREE.Material, x: number, y: number, z: number, r = 0) {
  const m = new THREE.Mesh(r ? new RoundedBoxGeometry(w, h, d, 3, r) : new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x, y, z); m.castShadow = m.receiveShadow = true; parent.add(m); return m;
}

/** Glass walls (and optionally a lid) around an inner box of CASE footprint, from y0 to y0 + height. */
export function glassBox(parent: THREE.Object3D, y0: number, height: number, lid: boolean, mat: THREE.Material = glass) {
  const W = CASE.w, D = CASE.d, t = GLASS.pane, yc = y0 + height / 2;
  const pane = (w: number, h: number, d: number, x: number, y: number, z: number) => {
    const m = box(parent, w, h, d, mat, x, y, z); m.castShadow = false; m.receiveShadow = false; m.renderOrder = 2; return m;
  };
  pane(W + 2 * t, height, t, 0, yc, D / 2 + t / 2); pane(W + 2 * t, height, t, 0, yc, -D / 2 - t / 2);
  pane(t, height, D, W / 2 + t / 2, yc, 0); pane(t, height, D, -W / 2 - t / 2, yc, 0);
  const top = y0 + height;
  if (lid) pane(W + 2 * t, t, D + 2 * t, 0, top + t / 2, 0);
  // only the edges of thick glass catch the light
  const e = 0.0045, edge = (w: number, h: number, d: number, x: number, y: number, z: number) => { const m = box(parent, w, h, d, glassEdge, x, y, z); m.castShadow = false; };
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) edge(e, height, e, sx * (W / 2 + t / 2), yc, sz * (D / 2 + t / 2));
  if (lid) {
    const yl = top + t / 2;
    for (const sz of [-1, 1]) edge(W + 2 * t, e, e, 0, yl, sz * (D / 2 + t / 2));
    for (const sx of [-1, 1]) edge(e, e, D + 2 * t, sx * (W / 2 + t / 2), yl, 0);
  }
}

export interface Vitrine { group: THREE.Group; stage: THREE.Group; top: number; setLabel(text: string): void }

export function buildCase({ base = 0.95, label = '' } = {}): Vitrine {
  const g = new THREE.Group(), W = CASE.w, D = CASE.d;
  box(g, W + 0.14, base, D + 0.14, lacquer, 0, base / 2, 0, 0.012);
  box(g, W + 0.15, 0.012, D + 0.15, brass, 0, base - 0.03, 0);
  const rim = 0.025; box(g, W + 0.04, rim, D + 0.04, bronze, 0, base + rim / 2, 0);
  const y0 = base + rim, stage = new THREE.Group(); stage.position.y = y0; g.add(stage);
  glassBox(g, y0, CASE.h, true);
  const plate = new THREE.Mesh(new THREE.PlaneGeometry(0.62, 0.087), plateMaterial(label));
  plate.position.set(0, base * 0.62, D / 2 + 0.0705); g.add(plate);
  return {
    group: g, stage, top: y0 + CASE.h,
    setLabel(text) { const old = plate.material; plate.material = plateMaterial(text); old.map?.dispose(); old.dispose(); },
  };
}
