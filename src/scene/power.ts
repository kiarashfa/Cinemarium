// A room's "power": every realtime light, emissive surface and baked light map in it, scaled together.
// The tower uses it to switch a floor's lights off, change the room, and switch them on again.
import type * as THREE from 'three/webgpu';

export type Power = ReturnType<typeof makePower>;

/** The room's power control, made once so its base intensities are captured while fully lit. */
export function powerOf(root: THREE.Object3D): Power {
  return (root.userData.power ??= makePower(root)) as Power;
}

function makePower(root: THREE.Object3D) {
  const lights: [THREE.Light, number][] = [], mats: [THREE.MeshStandardMaterial, number, number][] = [];
  const seen = new Set<THREE.Material>();
  root.traverse(o => {
    const l = o as THREE.Light; if (l.isLight) lights.push([l, l.intensity]);
    const m = (o as THREE.Mesh).material as THREE.MeshStandardMaterial | undefined;
    if (m && !Array.isArray(m) && !seen.has(m) && 'emissiveIntensity' in m) { seen.add(m); mats.push([m, m.emissiveIntensity, m.lightMapIntensity ?? 1]); }
  });
  let current = 1;
  return {
    get value() { return current; },
    set(p: number) {
      if (p === current) return; current = p;
      for (const [l, i] of lights) l.intensity = i * p;
      for (const [m, e, lm] of mats) { m.emissiveIntensity = e * p; if (m.lightMap) m.lightMapIntensity = lm * (0.04 + 0.96 * p); }
    },
    /** Call after a light's base intensity changes on purpose (an alarm, a flicker). */
    rebase(l: THREE.Light, base: number) { const e = lights.find(x => x[0] === l); if (e) e[1] = base; },
  };
}
