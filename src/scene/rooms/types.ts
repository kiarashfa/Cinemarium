import type * as THREE from 'three/webgpu';

/** A room at real size, inside MODULE: origin at the centre of its floor, back wall at -z, left wall at -x. */
export interface Room {
  group: THREE.Group;
  /** Advance people, screens and clocks. t: seconds since start; dt: seconds since last frame. */
  update(t: number, dt: number): void;
  /** Free what the room holds beyond its meshes (render targets). */
  dispose?(): void;
}

export type RoomLoader = () => Promise<Room>;
