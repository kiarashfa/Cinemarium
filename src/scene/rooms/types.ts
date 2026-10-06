import type * as THREE from 'three/webgpu';

/** A room at real size, inside MODULE: origin at the centre of its floor, back wall at -z, left wall at -x. */
export interface Room {
  group: THREE.Group;
  /** Advance people, screens and clocks. t: seconds since start; dt: seconds since last frame. */
  update(t: number, dt: number): void;
  /** 0..1: how lit the room is (used when a tower floor switches between series and films). */
  setPower?(p: number): void;
  dispose?(): void;
}

export type RoomLoader = () => Promise<Room>;
