// The room module and the one model scale.
//
// Every room, for every title, is built inside MODULE at real size (metres, people 1.75 m tall)
// and shown at SCALE in every layout. The case and the tower floor are derived from these numbers
// only, so every case and every floor is identical, and the glass always clears the tallest room.
// Pick the numbers once; never scale a room on its own (that is how cases and floors drift apart in size).
import * as THREE from 'three/webgpu';

/** The box every room is built in, in real metres. Origin at the centre of the floor; x right, y up, z toward the viewer. */
export const MODULE = { W: 9.6, D: 7.6, H: 3.0 } as const;

/** One model scale for every room, case and floor. At 1:6 a person is 0.29 m tall. */
export const SCALE = 1 / 6;

/** Glass, in model metres: the gap around the room, the headroom above it, and the pane thickness. */
export const GLASS = { side: 0.008, head: 0.035, pane: 0.006 } as const;

/** Inner size of the glass, in model metres. The room stands on a stage at the bottom of this box. */
export const CASE = {
  w: MODULE.W * SCALE + 2 * GLASS.side,
  d: MODULE.D * SCALE + 2 * GLASS.side,
  h: MODULE.H * SCALE + GLASS.head,
} as const;

/** A tower floor: a lacquer slab, then exactly one case height of room and glass. */
export const FLOOR = { slab: 0.04, h: 0.04 + CASE.h } as const;

/** Lift the room 1.5 mm off its stage so the two floors never z-fight. */
export const STAGE_LIFT = 0.0015;

export interface FitReport {
  ok: boolean;
  /** Measured extent in real metres: [width, depth, height]. */
  size: [number, number, number];
  problems: string[];
}

const _box = new THREE.Box3();

/**
 * Measures a room (its group must be at the origin, unscaled, in real metres) against the module.
 * Skinned people are measured in their current pose.
 */
export function measureRoom(group: THREE.Object3D): FitReport {
  const keep = { p: group.position.clone(), q: group.quaternion.clone(), s: group.scale.clone(), parent: group.parent };
  group.removeFromParent();
  group.position.set(0, 0, 0); group.quaternion.identity(); group.scale.setScalar(1);
  group.updateMatrixWorld(true);
  _box.makeEmpty();
  group.traverse(o => {
    if (o.userData.ignoreFit) return;
    const m = o as THREE.Mesh;
    if (m.isMesh && m.visible) _box.expandByObject(m, false);
  });
  group.position.copy(keep.p); group.quaternion.copy(keep.q); group.scale.copy(keep.s);
  keep.parent?.add(group);

  const tol = 0.005, problems: string[] = [];
  if (_box.isEmpty()) return { ok: true, size: [0, 0, 0], problems };
  const { min, max } = _box;
  if (min.x < -MODULE.W / 2 - tol || max.x > MODULE.W / 2 + tol) problems.push(`width ${(max.x - min.x).toFixed(2)} m exceeds ${MODULE.W} m`);
  if (min.z < -MODULE.D / 2 - tol || max.z > MODULE.D / 2 + tol) problems.push(`depth ${(max.z - min.z).toFixed(2)} m exceeds ${MODULE.D} m`);
  if (max.y > MODULE.H + tol) problems.push(`height ${max.y.toFixed(2)} m exceeds ${MODULE.H} m: the glass would be shorter than the room`);
  if (min.y < -0.05 - tol) problems.push(`something hangs ${(-min.y).toFixed(2)} m below the floor`);
  return { ok: problems.length === 0, size: [max.x - min.x, max.z - min.z, max.y], problems };
}

/** Shrinks a measured room into model scale and brings its realtime lights back to physical sense. */
export function shrink(group: THREE.Object3D) {
  group.scale.setScalar(SCALE);
  group.position.y = STAGE_LIFT;
  rescaleLights(group, SCALE);
}

// three.js lights are physical: point and spot intensities are in candela and fall off with distance squared,
// so a room shrunk by s brings every lamp s times closer and s^2 times brighter. Undo that, and shrink
// what does not follow the parent's scale (area-light size, shadow cameras).
export function rescaleLights(root: THREE.Object3D, s: number) {
  root.traverse(o => {
    const l = o as THREE.PointLight & THREE.SpotLight;
    if (l.isPointLight || l.isSpotLight) {
      l.intensity *= s * s; l.distance *= s;
      if (l.shadow) { const c = l.shadow.camera as THREE.PerspectiveCamera; c.near *= s; c.far *= s; l.shadow.normalBias *= s; }
    }
    const a = o as THREE.RectAreaLight;
    if (a.isRectAreaLight) { a.width *= s; a.height *= s; }
  });
}
