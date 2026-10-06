// The two surroundings: Dusk (the tower in still water under a low sun) and Travertine
// (a sunlit stone hall for the one-at-a-time case). Ported from the GlassRoom mocks to WebGPU.
import * as THREE from 'three/webgpu';
import { abs, dot, normalView, positionViewDirection, pow, uniform, uv, vec4, color as tslColor } from 'three/tsl';
import { SkyMesh } from 'three/addons/objects/SkyMesh.js';
import { WaterMesh } from 'three/addons/objects/WaterMesh.js';
import { EXRLoader } from 'three/addons/loaders/EXRLoader.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { canvasTexture, noise, rng } from './materials';

export interface Ambient { group: THREE.Group; exposure: number; update(t: number): void }

const asset = (p: string) => `${import.meta.env.BASE_URL}${p}`;
const shadowy = (o: THREE.Object3D) => { o.traverse(c => { if ((c as THREE.Mesh).isMesh) c.castShadow = c.receiveShadow = true; }); return o; };

// A soft additive light cone: haze in a sunbeam.
function beam(hex: number, rTop: number, rBottom: number, height: number, intensity: number) {
  const m = new THREE.MeshBasicNodeMaterial({ transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide });
  const I = uniform(intensity), edge = pow(abs(dot(normalView, positionViewDirection)), 1.6), fall = pow(uv().y, 1.4);
  m.colorNode = vec4(tslColor(hex).mul(I).mul(edge).mul(fall), 1);
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(rTop, rBottom, height, 48, 1, true), m); mesh.renderOrder = 10;
  return mesh;
}

// ---------- Dusk ----------
export async function dusk(scene: THREE.Scene, renderer: THREE.WebGPURenderer): Promise<Ambient> {
  const g = new THREE.Group();
  const sun = new THREE.Vector3().setFromSphericalCoords(1, THREE.MathUtils.degToRad(90 - 3.2), THREE.MathUtils.degToRad(238));
  const sky = new SkyMesh(); sky.scale.setScalar(450);
  sky.turbidity.value = 3.5; sky.rayleigh.value = 1.6; sky.mieCoefficient.value = 0.004; sky.mieDirectionalG.value = 0.9;
  sky.cloudCoverage.value = 0.18; sky.cloudDensity.value = 0.3; sky.cloudSpeed.value = 0.000004; sky.sunPosition.value.copy(sun);
  g.add(sky);
  // the environment is the same sky, captured once
  const envScene = new THREE.Scene(), sky2 = new SkyMesh(); sky2.scale.setScalar(450);
  for (const k of ['turbidity', 'rayleigh', 'mieCoefficient', 'mieDirectionalG', 'cloudCoverage', 'cloudDensity'] as const) sky2[k].value = sky[k].value;
  sky2.sunPosition.value.copy(sun); sky2.cloudSpeed.value = 0; envScene.add(sky2);
  const cubeRT = new THREE.CubeRenderTarget(256, { type: THREE.HalfFloatType });
  new THREE.CubeCamera(0.1, 1000, cubeRT).update(renderer, envScene);
  scene.environment = cubeRT.texture; scene.environmentIntensity = 0.7; scene.background = null;

  const normals = canvasTexture(512, 512, (c, w, h) => {
    const img = c.createImageData(w, h), r = rng(3), waves = Array.from({ length: 24 }, () => [r() * 6.28, 2 + r() * 14, r() * 6.28, 0.3 + r() * 0.7]);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      let nx = 0, ny = 0;
      for (const [ang, f, ph, a] of waves) { const k = (x * Math.cos(ang) + y * Math.sin(ang)) / w * f * 6.28 + ph, d = Math.cos(k) * a; nx += d * Math.cos(ang); ny += d * Math.sin(ang); }
      const o = (y * w + x) * 4; img.data[o] = 128 + nx * 9; img.data[o + 1] = 128 + ny * 9; img.data[o + 2] = 255; img.data[o + 3] = 255;
    }
    c.putImageData(img, 0, 0);
  }, { srgb: false });
  const water = new WaterMesh(new THREE.PlaneGeometry(400, 400), {
    waterNormals: normals, sunDirection: sun.clone().normalize(), sunColor: 0xffc58a, waterColor: 0x02080d, distortionScale: 1.1, size: 3.2,
  });
  water.rotation.x = -Math.PI / 2; g.add(water);

  const key = new THREE.DirectionalLight(0xffb070, 3.2); key.position.copy(sun).multiplyScalar(30); key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048); Object.assign(key.shadow.camera, { left: -4, right: 4, top: 8, bottom: -1, near: 1, far: 80 }); key.shadow.bias = -0.0005;
  g.add(key, new THREE.HemisphereLight(0x6a7fa8, 0x05070a, 0.45));
  const rim = new THREE.DirectionalLight(0x8fb0ff, 0.8); rim.position.set(3, 4, 6); g.add(rim);
  scene.add(g);
  return { group: g, exposure: 0.62, update() {} };
}

// ---------- Travertine ----------
export async function travertine(scene: THREE.Scene): Promise<Ambient> {
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
  // back wall with three arched niches
  const W = 16, H = 7, back = new THREE.Shape(); back.moveTo(-W / 2, 0); back.lineTo(W / 2, 0); back.lineTo(W / 2, H); back.lineTo(-W / 2, H); back.lineTo(-W / 2, 0);
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
  return { group: g, exposure: 0.9, update() {} };
}

export { RoundedBoxGeometry };
