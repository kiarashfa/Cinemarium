// Study models: white card maquettes of each title's room at its true wall height, each with a 1.75 m
// scale figure. They stand in until a title's realistic room is built, and they prove the module:
// MDR's 2.36 m ceiling, the Swan's 2.7 m and the hotel room's full 3 m all sit under the same glass.
import * as THREE from 'three/webgpu';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { MODULE } from '../module';
import { canvasTexture, noise } from '../materials';
import type { Room } from './types';

const card = (hex: number, seed: number) => new THREE.MeshStandardMaterial({
  color: hex, roughness: 0.92,
  map: canvasTexture(256, 256, (g, w, h) => { g.fillStyle = '#ffffff'; g.fillRect(0, 0, w, h); noise(g, w, h, 14, seed); }, { repeat: [4, 4] }),
});

function kit(parent: THREE.Object3D, mat: THREE.Material) {
  return (w: number, h: number, d: number, x: number, y: number, z: number, { ry = 0, r = 0.006, m = mat } = {}) => {
    const mesh = new THREE.Mesh(r ? new RoundedBoxGeometry(w, h, d, 2, Math.min(r, w / 2, h / 2, d / 2)) : new THREE.BoxGeometry(w, h, d), m);
    mesh.position.set(x, y + h / 2, z); mesh.rotation.y = ry; mesh.castShadow = mesh.receiveShadow = true; parent.add(mesh); return mesh;
  };
}

/** An architect's scale figure, 1.75 m: shoulders, head, legs. */
function figure(parent: THREE.Object3D, x: number, z: number, ry: number, mat: THREE.Material) {
  const f = new THREE.Group(); f.position.set(x, 0, z); f.rotation.y = ry; parent.add(f);
  const add = (geo: THREE.BufferGeometry, y: number, sx = 1, sz = 1) => { const m = new THREE.Mesh(geo, mat); m.position.y = y; m.scale.set(sx, 1, sz); m.castShadow = m.receiveShadow = true; f.add(m); };
  for (const s of [-1, 1]) { const leg = new THREE.Mesh(new THREE.CapsuleGeometry(0.075, 0.72, 6, 12), mat); leg.position.set(s * 0.1, 0.44, 0); leg.castShadow = true; f.add(leg); }
  add(new THREE.CapsuleGeometry(0.17, 0.42, 8, 16), 1.16, 1.15, 0.62);
  add(new THREE.SphereGeometry(0.11, 24, 16), 1.64, 0.9, 1);
  return f;
}

/** The shell: floor, full-height back and left walls, a low kerb on the front and right (the cut-away). */
function shell(g: THREE.Group, wallH: number, floorHex: number, wallHex: number) {
  const W = MODULE.W, D = MODULE.D, t = 0.12, box = kit(g, card(wallHex, 3));
  box(W, 0.04, D, 0, -0.04, 0, { m: card(floorHex, 5), r: 0 });
  box(W, wallH, t, 0, 0, -D / 2 + t / 2); box(t, wallH, D - t, -W / 2 + t / 2, 0, t / 2);
  box(W, 0.22, t, 0, 0, D / 2 - t / 2); box(t, 0.22, D - 2 * t, W / 2 - t / 2, 0, 0);
  return box;
}

// kept soft: the card is white and the club's own key light falls on it too
function light(g: THREE.Group, wallH: number) {
  const panel = new THREE.RectAreaLight(0xfff6ea, 1.1, 7, 5.4); panel.position.set(0, wallH + 0.4, 0.2); panel.lookAt(0, 0, 0.2); g.add(panel);
  const key = new THREE.SpotLight(0xfff1e0, 50, 16, 0.7, 1, 2); key.position.set(-2.4, 7, 3.4); key.target.position.set(0.3, 0, -0.4);
  key.castShadow = true; key.shadow.mapSize.set(2048, 2048); key.shadow.bias = -0.0002; key.shadow.normalBias = 0.03; key.shadow.radius = 6;
  g.add(key, key.target, new THREE.HemisphereLight(0xffffff, 0xd8d4cc, 0.18));
}

const still: Room['update'] = () => {};

// Severance: the MDR floor. Low ceiling, the four-desk island in the middle of the carpet.
export async function severanceStudy(): Promise<Room> {
  const g = new THREE.Group(), H = 2.36, box = shell(g, H, 0xd7dfd6, 0xf4f3ef), white = card(0xfbfbf8, 9);
  for (let q = 0; q < 4; q++) {
    const a = q * Math.PI / 2, c = Math.cos(a), s = Math.sin(a), at = (x: number, z: number) => [x * c + z * s, -x * s + z * c] as const;
    const [dx, dz] = at(0.82, 0.82); box(1.5, 0.04, 1.5, dx, 0.72, dz, { ry: a, m: white });
    const [tx, tz] = at(0.82, 0.55); box(0.42, 0.38, 0.36, tx, 0.76, tz, { ry: a, m: white });
    const [cx, cz] = at(0.82, 1.85); box(0.5, 0.47, 0.5, cx, 0, cz, { ry: a, m: white });
  }
  box(3.1, 1.28, 0.05, 0, 0, 0, { r: 0 }); box(0.05, 1.28, 3.1, 0, 0, 0, { r: 0 });
  box(1.0, 2.1, 0.06, 3.0, 0, -MODULE.D / 2 + 0.15);
  figure(g, -2.6, 1.2, 0.5, white);
  light(g, H);
  return { group: g, update: still };
}

// LOST: the Swan. The computer under the countdown clock, a couch, the record player.
export async function lostStudy(): Promise<Room> {
  const g = new THREE.Group(), H = 2.7, box = shell(g, H, 0xd9d4ca, 0xf2efe8), white = card(0xfbfaf6, 11), D = MODULE.D;
  box(1.8, 0.05, 0.8, 0.3, 0.7, -D / 2 + 0.6); for (const x of [-0.55, 1.15]) box(0.05, 0.7, 0.7, x, 0, -D / 2 + 0.6, { m: white });
  box(0.44, 0.36, 0.36, 0.1, 0.75, -D / 2 + 0.5, { m: white }); box(1.0, 0.3, 0.16, 0.3, 1.75, -D / 2 + 0.2, { m: white });
  box(2.0, 0.42, 0.9, 1.9, 0, 0.9, { ry: -0.4, m: white }); box(2.0, 0.5, 0.22, 1.75, 0.42, 0.55, { ry: -0.4, m: white });
  box(1.2, 0.6, 0.5, -2.6, 0, -D / 2 + 0.4, { m: white }); box(0.35, 1.8, 1.6, -MODULE.W / 2 + 0.35, 0, -1.0, { m: white });
  figure(g, -0.8, 0.6, 0.3, white);
  light(g, H);
  return { group: g, update: still };
}

// The Matrix: two club chairs, an old television and a side table, in a 3 m white room (the module's full height).
export async function matrixStudy(): Promise<Room> {
  const g = new THREE.Group(), H = MODULE.H, box = shell(g, H, 0xe2e1dd, 0xf6f6f3), white = card(0xfcfcfa, 13);
  for (const [x, ry] of [[-1.0, 0.55], [1.0, -0.55]] as const) { box(0.92, 0.42, 0.86, x, 0, 0.2, { ry, m: white }); box(0.92, 0.5, 0.24, x - Math.sin(ry) * 0.32, 0.42, 0.2 - Math.cos(ry) * 0.32, { ry, m: white }); }
  box(0.9, 0.62, 0.5, 0, 0.27, -1.25, { m: white }); box(0.44, 0.55, 0.44, 0, 0, 0.45, { m: white, r: 0.2 });
  figure(g, 2.4, -0.6, -0.4, white);
  light(g, H);
  return { group: g, update: still };
}
