// Room registry. Each loader builds a room at real size inside MODULE; `loadRoom` measures it, refuses it if it
// would poke through the glass, then shrinks it to SCALE. No other scaling exists.
// Loaders import their code on demand, so the club downloads a room, and what draws it, only when its case is entered;
// `release` frees the rooms no longer shown.
import type * as THREE from 'three/webgpu';
import { measureRoom, shrink } from '../module';
import { QUERY } from '../stage';
import type { Room, RoomLoader } from './types';
import type { Screen } from './baked';

type Study = 'severanceStudy' | 'lostStudy' | 'matrixStudy';
const study = (name: Study): RoomLoader => () => import('./study').then(m => m[name]());

/** A baked room when its files exist, otherwise the study model (so a missing bake never breaks a page). */
const baked = (id: string, fallback: Study, screen?: () => Promise<Screen>): RoomLoader => async () => {
  try {
    if (QUERY.has('study')) throw new Error('study requested');
    const [{ bakedRoom }, s] = await Promise.all([import('./baked'), screen?.()]);
    return await bakedRoom(id, s);
  } catch (err) {
    console.warn(`room ${id}: using the study model (${(err as Error).message ?? err})`);
    return study(fallback)();
  }
};

export const ROOMS: Record<string, RoomLoader> = {
  'severance': baked('severance', 'severanceStudy', () => import('./mdr-screen').then(m => m.mdrScreen)),
  'lost': study('lostStudy'),
  'the-matrix': study('matrixStudy'),
};

const cache = new Map<string, Promise<Room>>();

export function loadRoom(id: string): Promise<Room> {
  if (!cache.has(id)) {
    const loader = ROOMS[id];
    if (!loader) return Promise.reject(new Error(`No room "${id}"`));
    cache.set(id, loader().then(room => {
      const fit = measureRoom(room.group);
      if (!fit.ok) throw new Error(`Room "${id}" does not fit the module: ${fit.problems.join('; ')}`);
      room.group.userData.fit = fit;
      shrink(room.group);
      return room;
    }));
  }
  return cache.get(id)!;
}

/** Frees every loaded room but the ones kept (geometry, materials, textures), so memory holds one or two rooms. */
export function release(keep: string[]) {
  for (const [id, p] of cache) {
    if (keep.includes(id)) continue;
    cache.delete(id);
    p.then(room => {
      room.group.removeFromParent();
      room.group.traverse(o => {
        const m = o as THREE.Mesh; if (!m.isMesh) return;
        m.geometry.dispose();
        for (const mat of ([] as THREE.Material[]).concat(m.material)) {
          for (const v of Object.values(mat)) if ((v as THREE.Texture)?.isTexture) (v as THREE.Texture).dispose();
          mat.dispose();
        }
      });
      room.dispose?.();
    }, () => {});
  }
}

/** Puts a room on the case's stage, replacing whatever stood there. */
export function mount(stage: THREE.Group, room: Room) {
  for (const c of [...stage.children]) if (c.userData.isRoom) stage.remove(c);
  room.group.userData.isRoom = true;
  stage.add(room.group);
}

export type { Room };
