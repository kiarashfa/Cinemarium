// The tower: a basalt footing, then ten identical floors under one skin of glass.
// A floor is a lacquer slab plus exactly CASE.h of room and air, so every storey is the same height
// and the slab above always clears the tallest room.
import * as THREE from 'three/webgpu';
import { CASE, FLOOR, GLASS } from './module';
import { box, glassBox } from './case';
import { lacquer, brass, glass } from './materials';

// a facade, not a vitrine: ordinary architectural glass that mirrors the room around it
const facade = glass.clone(); facade.specularIntensity = 1; facade.envMapIntensity = 0.5;
// an unlit storey: dark matte back and side, so an empty floor reads as an office with the lights off
const unlit = new THREE.MeshStandardMaterial({ color: 0x15140f, roughness: 0.92 });

export interface Floor { index: number; stage: THREE.Group; y0: number; vacant: THREE.Group }
export interface Tower { group: THREE.Group; floors: Floor[]; base: number; top: number }

export function buildTower(storeys = 10): Tower {
  const g = new THREE.Group(), W = CASE.w, D = CASE.d, t = GLASS.pane, base = 0.55;
  const basalt = new THREE.MeshPhysicalMaterial({ color: 0x1b1b1d, roughness: 0.6, clearcoat: 0.3 });
  box(g, W + 0.3, base + 0.3, D + 0.3, basalt, 0, (base + 0.3) / 2 - 0.3, 0, 0.02);
  box(g, W + 0.31, 0.012, D + 0.31, brass, 0, base - 0.01, 0);
  const slab = (y: number) => {
    box(g, W + 2 * t, FLOOR.slab, D + 2 * t, lacquer, 0, y + FLOOR.slab / 2, 0);
    box(g, W + 2 * t + 0.004, 0.006, D + 2 * t + 0.004, brass, 0, y + FLOOR.slab - 0.003, 0);
  };
  const floors: Floor[] = [];
  let y = base;
  for (let i = 0; i < storeys; i++) {
    slab(y);
    const stage = new THREE.Group(); stage.position.y = y + FLOOR.slab; g.add(stage);
    const vacant = new THREE.Group(); vacant.position.y = y + FLOOR.slab; g.add(vacant);
    box(vacant, W, CASE.h, 0.01, unlit, 0, CASE.h / 2, -D / 2 + 0.005); box(vacant, 0.01, CASE.h, D, unlit, -W / 2 + 0.005, CASE.h / 2, 0);
    box(vacant, W, 0.004, D, unlit, 0, 0.002, 0);
    floors.push({ index: i, stage, y0: y + FLOOR.slab, vacant });
    glassBox(g, y + FLOOR.slab, CASE.h, false, facade);
    y += FLOOR.h;
  }
  slab(y);
  return { group: g, floors, base, top: y + FLOOR.slab };
}
