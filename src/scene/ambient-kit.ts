// The pieces every ambient is made of: haze in a beam, a key spot sized to the subject, polished stone with a faint
// mirror, the room's own reflections captured once.
import * as THREE from 'three/webgpu';
import { abs, dot, float, normalView, positionViewDirection, pow, reflector, uniform, uv, vec4, color as tslColor } from 'three/tsl';
import { canvasTexture, noise, rng } from './materials';
import { QUALITY, QUERY } from './stage';

/** What an ambient frames: its centre, height and width (metres). */
export interface Subject { centre: THREE.Vector3; height: number; width: number }

export const asset = (p: string) => `${import.meta.env.BASE_URL}${p}`;
export const shadowy = (o: THREE.Object3D) => { o.traverse(c => { if ((c as THREE.Mesh).isMesh) c.castShadow = c.receiveShadow = true; }); return o; };

/** A soft additive light cone: haze in a beam. Brightest at its top, where the light is. */
export function beam(hex: number, rTop: number, rBottom: number, height: number, intensity: number) {
  const m = new THREE.MeshBasicNodeMaterial({ transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, fog: false });
  const I = uniform(intensity), edge = pow(abs(dot(normalView, positionViewDirection)), 1.6), fall = pow(uv().y, 1.4);
  m.colorNode = vec4(tslColor(hex).mul(I).mul(edge).mul(fall), 1);
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(rTop, rBottom, height, 48, 1, true), m); mesh.renderOrder = 10;
  return mesh;
}
/** A beam from a light at `from` to the pool it makes at `to`. */
export function beamBetween(hex: number, from: THREE.Vector3, to: THREE.Vector3, rTop: number, rBottom: number, intensity: number) {
  const d = new THREE.Vector3().subVectors(from, to), b = beam(hex, rTop, rBottom, d.length(), intensity);
  b.position.addVectors(from, to).multiplyScalar(0.5); b.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.normalize());
  return b;
}
/** A warm key spot from `from` that covers the subject with a soft edge; casts the shadow. */
export function keySpot(hex: number, from: THREE.Vector3, s: Subject, candela: number, cover = 0.75) {
  const dist = from.distanceTo(s.centre), half = Math.max(s.height, s.width) * cover;
  const spot = new THREE.SpotLight(hex, candela * (dist / 5) ** 1.6, dist * 2.5, Math.min(1.0, Math.atan(half / dist) * 1.35), 0.7, 1.6);
  spot.position.copy(from); spot.target.position.copy(s.centre); spot.castShadow = true;
  spot.shadow.mapSize.set(2048, 2048); spot.shadow.bias = -0.0004; spot.shadow.radius = 6;
  return spot;
}
/** The room's own reflections: everything built so far, seen once from the subject. */
export function capture(scene: THREE.Scene, renderer: THREE.WebGPURenderer, at: THREE.Vector3, intensity: number) {
  const rt = new THREE.CubeRenderTarget(256, { type: THREE.HalfFloatType, generateMipmaps: true, minFilter: THREE.LinearMipmapLinearFilter });
  const cam = new THREE.CubeCamera(0.05, 200, rt); cam.position.copy(at); scene.add(cam);
  cam.update(renderer, scene); scene.remove(cam);
  scene.environment = rt.texture; scene.environmentIntensity = intensity;
}
/** Polished dark stone (or resin): faint veins, a clear coat, and on desktops a faint mirror of the room in it,
 * strongest at a glancing angle. Keep `mirror` low: a strong one turns the floor into a second room below. */
export function polishedFloor(geometry: THREE.BufferGeometry, { base = '#0d0d0f', vein = '150,150,160', mirror = 0.35, repeat = 7, coat = 1, coatRough = 0.12, map = null as THREE.Texture | null } = {}) {
  const t = map ?? canvasTexture(1024, 1024, (c, w, h) => {
    c.fillStyle = base; c.fillRect(0, 0, w, h); const r = rng(4);
    for (let k = 0; k < 60; k++) {
      c.strokeStyle = `rgba(${vein},${0.02 + r() * 0.04})`; c.lineWidth = 0.6 + r() * 1.5; c.beginPath();
      let x = r() * w, y = r() * h; c.moveTo(x, y); for (let q = 0; q < 8; q++) { x += (r() - 0.4) * 160; y += (r() - 0.5) * 90; c.lineTo(x, y); } c.stroke();
    }
    noise(c, w, h, 10, 2);
  }, { repeat: [repeat, repeat] });
  const mat = new THREE.MeshPhysicalNodeMaterial({ map: t, roughness: 0.35, clearcoat: coat, clearcoatRoughness: coatRough });
  const floor = new THREE.Mesh(geometry, mat); floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true;
  if (QUALITY === 'high' && !QUERY.has('nomirror')) {
    const m = reflector({ resolutionScale: 0.5, bounces: false }), cos = abs(dot(normalView, positionViewDirection));
    const fresnel = float(0.04).add(pow(float(1).sub(cos), 5).mul(0.6));       // a dark floor is a mirror only at a glance
    mat.emissiveNode = m.rgb.mul(fresnel.mul(mirror)); floor.add(m.target);
  }
  return floor;
}
/** Scale an ambient's light: its lamps and everything that glows (unlit materials), once each. */
export function dim(root: THREE.Object3D, k: number) {
  const seen = new Set<THREE.Material>();
  root.traverse(o => {
    if ((o as THREE.Light).isLight) (o as THREE.Light).intensity *= k;
    const m = (o as THREE.Mesh).material as THREE.MeshBasicMaterial | undefined;
    if (m && !seen.has(m) && m.isMeshBasicMaterial && !m.transparent) { seen.add(m); m.color.multiplyScalar(k); }
  });
}
/** A softbox's diffuser: brightest in the middle, falling off toward its frame, with a faint weave. */
export function diffuser() {
  return canvasTexture(64, 512, (c, w, h) => {
    const img = c.createImageData(w, h), r = rng(5);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const u = Math.abs(x / (w - 1) - 0.5) * 2, v = Math.abs(y / (h - 1) - 0.5) * 2;
      const f = (1 - 0.32 * u ** 2.2) * (1 - 0.22 * v ** 3) * (0.985 + r() * 0.03), o = (y * w + x) * 4;
      img.data[o] = img.data[o + 1] = img.data[o + 2] = 255 * f; img.data[o + 3] = 255;
    }
    c.putImageData(img, 0, 0);
  });
}
