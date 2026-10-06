// Room registry. Each loader builds a room at real size inside MODULE; `mountRoom` measures it,
// refuses it if it would poke through the glass, then shrinks it to SCALE. No other scaling exists.
import type * as THREE from 'three/webgpu';
import { measureRoom, shrink } from '../module';
import type { Room, RoomLoader } from './types';
import { severanceStudy, lostStudy, matrixStudy } from './study';
import { bakedRoom } from './baked';
import { mdrScreen } from './mdr-screen';

/** A baked room when its files exist, otherwise the study model (so a missing bake never breaks a page). */
const baked = (id: string, study: RoomLoader, screen?: Parameters<typeof bakedRoom>[1]): RoomLoader => () =>
  (new URLSearchParams(location.search).has('study') ? Promise.reject(new Error('study requested')) : bakedRoom(id, screen))
    .catch(err => { console.warn(`room ${id}: using the study model (${err.message ?? err})`); return study(); });

export const ROOMS: Record<string, RoomLoader> = {
  'severance': baked('severance', severanceStudy, mdrScreen),
  'lost': lostStudy,
  'the-matrix': matrixStudy,
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

/** Puts a room on a stage (a case or a tower floor), replacing whatever stood there. */
export function mount(stage: THREE.Group, room: Room) {
  for (const c of [...stage.children]) if (c.userData.isRoom) stage.remove(c);
  room.group.userData.isRoom = true;
  stage.add(room.group);
}

export type { Room };
