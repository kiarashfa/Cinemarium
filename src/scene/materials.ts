// Shared look-dev: the case's glass, lacquer, brass and bronze, and small canvas-texture helpers.
import * as THREE from 'three/webgpu';

/** A canvas texture drawn once. Colour textures are sRGB; data textures (normals, roughness) are not. */
export function canvasTexture(w: number, h: number, draw: (g: CanvasRenderingContext2D, w: number, h: number) => void,
  { repeat = [1, 1] as [number, number], srgb = true } = {}) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  draw(c.getContext('2d')!, w, h);
  const t = new THREE.CanvasTexture(c);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(...repeat); t.anisotropy = 8;
  return t;
}

/** A seeded random generator (mulberry32), so procedural textures are the same on every load. */
export function rng(seed: number) {
  let s = seed >>> 0;
  return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

export function noise(g: CanvasRenderingContext2D, w: number, h: number, amp: number, seed = 1) {
  const r = rng(seed), d = g.getImageData(0, 0, w, h);
  for (let i = 0; i < d.data.length; i += 4) { const n = (r() - .5) * amp; d.data[i] += n; d.data[i + 1] += n; d.data[i + 2] += n; }
  g.putImageData(d, 0, 0);
}

// Museum glass: low-iron, anti-reflective (about 1% reflectance instead of plain glass's 4%), rendered with
// transmission, never opacity (opacity adds a white veil). Plain-glass reflections of a bright hall veil the room.
export const glass = new THREE.MeshPhysicalMaterial({
  color: 0xffffff, roughness: 0.01, metalness: 0, transmission: 1, thickness: 0.006, ior: 1.52,
  specularIntensity: 0.22, envMapIntensity: 0.7,
});
// Frameless museum glass: only the thick edges catch the light, in a faint green.
export const glassEdge = new THREE.MeshPhysicalMaterial({
  color: 0x9fd2bf, roughness: 0.08, transparent: true, opacity: 0.6, envMapIntensity: 2.2, emissive: 0x14221c,
});
export const lacquer = new THREE.MeshPhysicalMaterial({ color: 0x0b0b0c, roughness: 0.3, clearcoat: 1, clearcoatRoughness: 0.07 });
export const brass = new THREE.MeshPhysicalMaterial({ color: 0xcfa968, metalness: 1, roughness: 0.26 });
export const bronze = new THREE.MeshPhysicalMaterial({ color: 0x2a221b, metalness: 1, roughness: 0.32 });

/** An engraved brass plate: the title in spaced capitals. */
export function plateMaterial(text: string) {
  const map = canvasTexture(1024, 144, (g, w, h) => {
    const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, '#e8cb92'); gr.addColorStop(1, '#a7834a');
    g.fillStyle = gr; g.fillRect(0, 0, w, h); noise(g, w, h, 10, 3);
    g.fillStyle = '#2b1d0d'; g.font = '56px "Bodoni Moda", Didot, Georgia, serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillText(text.toUpperCase().split('').join(' '), w / 2, h / 2 + 3);
  }, { repeat: [1, 1] });
  map.wrapS = map.wrapT = THREE.ClampToEdgeWrapping;
  return new THREE.MeshPhysicalMaterial({ map, metalness: 0.75, roughness: 0.34 });
}
