// People who keep living: each person's file holds several acts (motion-capture clips baked in Blender, each a
// seamless loop). A seated refiner mostly works and now and then breaks off into an idle; the walker does his
// rounds and stops to watch. The next act is picked at random, by weight, and the change is a crossfade, so
// nothing restarts and nothing repeats on a fixed beat.
import * as THREE from 'three/webgpu';
import { rng } from '../materials';

export interface Act { name: string; loop?: boolean; w?: number; min?: number; max?: number }
export interface Stop { face: [number, number]; dwell: [number, number] }
export interface PersonMeta {
  who: string; file: string; acts: Act[];
  walker?: boolean; speed?: number; route?: { at: [number, number]; stop: Stop | null }[];
}

const FADE = 0.9;

/** The acts of one body, and crossfades between them. */
class Performer {
  readonly mixer: THREE.AnimationMixer;
  readonly actions = new Map<string, THREE.AnimationAction>();
  current: THREE.AnimationAction | null = null;
  constructor(root: THREE.Object3D, clips: THREE.AnimationClip[]) {
    this.mixer = new THREE.AnimationMixer(root);
    for (const c of clips) this.actions.set(c.name, this.mixer.clipAction(c));
  }
  has(name: string) { return this.actions.has(name); }
  duration(name: string) { return this.actions.get(name)!.getClip().duration; }
  play(name: string, loop: boolean, offset = 0, fade = FADE) {
    const next = this.actions.get(name)!;
    if (next === this.current) return;
    next.reset(); next.setLoop(loop ? THREE.LoopRepeat : THREE.LoopOnce, Infinity); next.clampWhenFinished = !loop;
    next.time = offset; next.setEffectiveWeight(1); next.play();
    if (this.current && fade > 0) this.current.crossFadeTo(next, fade, false); else this.current?.stop();
    this.current = next;
  }
  weight(name: string) { return this.actions.get(name)!.getEffectiveWeight(); }
}

function pick(acts: Act[], r: () => number) {
  const total = acts.reduce((s, a) => s + (a.w ?? 1), 0); let x = r() * total;
  for (const a of acts) { x -= a.w ?? 1; if (x <= 0) return a; }
  return acts[acts.length - 1];
}

/** Work, then an idle, then work again for a while: never the same idle twice in a row. */
function seated(p: Performer, acts: Act[], r: () => number) {
  const work = acts.find(a => a.loop) ?? acts[0], idles = acts.filter(a => a !== work && p.has(a.name));
  let until = -1, onWork = false, last = '';
  return (t: number) => {
    if (t < until) return;
    if (!onWork || !idles.length) {
      const first = until < 0;
      p.play(work.name, true, r() * p.duration(work.name), first ? 0 : FADE);
      const lo = work.min ?? 15, hi = work.max ?? 40;   // the first stretch is short, so the room comes alive soon
      onWork = true; until = t + (first ? lo * 0.3 + r() * (hi - lo) * 0.35 : lo + r() * (hi - lo));
    } else {
      const a = pick(idles.filter(i => i.name !== last), r);
      p.play(a.name, false); last = a.name; onWork = false;
      until = t + Math.max(1.5, p.duration(a.name) - FADE);
    }
  };
}

/** The supervisor's rounds: walk the route at the clip's own pace (slowing with the crossfade, so the feet do not
 * slide), stop where a stop is set, face the refiner there, stand a while (one idle or two), walk on. */
function rounds(p: Performer, body: THREE.Object3D, meta: PersonMeta, r: () => number) {
  const route = (meta.route ?? []).map(w => ({ at: new THREE.Vector2(w.at[0], -w.at[1]), stop: w.stop }));
  const idles = meta.acts.filter(a => !a.loop && p.has(a.name)), speed = meta.speed || 1;
  const pos = route[route.length - 1].at.clone(), dir = new THREE.Vector2();
  let i = 0, state: 'walk' | 'slowing' | 'stand' = 'walk', until = 0, last = '', heading = 0, face: THREE.Vector2 | null = null;
  p.play('walk', true, 0, 0);
  { const a = route[0].at; heading = Math.atan2(a.x - pos.x, a.y - pos.y); }
  const turn = (want: number, dt: number) => { let d = want - heading; d = Math.atan2(Math.sin(d), Math.cos(d)); heading += d * (1 - Math.exp(-dt * 3.5)); };
  return (t: number, dt: number) => {
    const w = route[i];
    if (state !== 'stand') {
      dir.subVectors(w.at, pos); const d = dir.length();
      if (w.stop && state === 'walk' && d <= speed * FADE * 0.5 + 0.02) {         // ease to a halt on the spot
        const a = pick(idles, r); p.play(a.name, false); last = a.name; state = 'slowing';
      }
      const v = speed * p.weight('walk'), step = Math.min(d, v * dt);
      if (d > 1e-4) { pos.addScaledVector(dir, step / d); if (d > 0.05) turn(Math.atan2(dir.x, dir.y), dt); }
      if (d - step < 0.01 || (state === 'slowing' && p.weight('walk') < 0.02)) {   // there (or as near as the fade took him)
        if (w.stop) {
          state = 'stand'; face = new THREE.Vector2(w.stop.face[0], -w.stop.face[1]);
          until = t + w.stop.dwell[0] + r() * (w.stop.dwell[1] - w.stop.dwell[0]);
          if (state === 'stand' && p.current === p.actions.get('walk')) { const a = pick(idles, r); p.play(a.name, false); last = a.name; }
        } else i = (i + 1) % route.length;
      }
    } else {
      if (face) turn(Math.atan2(face.x - pos.x, face.y - pos.y), dt);
      const cur = p.current!, left = cur.getClip().duration - cur.time;
      if (t >= until) { i = (i + 1) % route.length; state = 'walk'; p.play('walk', true, 0); face = null; }
      else if (left < FADE && cur.loop === THREE.LoopOnce) {                      // a short idle ran out: another one
        const a = pick(idles.filter(x => x.name !== last), r); p.play(a.name, false); last = a.name;
      }
    }
    body.position.set(pos.x, 0, pos.y); body.rotation.y = heading;
  };
}

export interface Cast {
  update(t: number, dt: number): void;
  /** who is doing what (for ?debug) */ state(): Record<string, string>;
  /** play one act now, no fade (for ?debug: checking every act in place) */ play(who: string, act: string): void;
  /** the act a person is in now (props that belong to an act follow it: pills in an open hand) */ current(who: string): THREE.AnimationAction | null;
}

export function perform(people: { body: THREE.Object3D; clips: THREE.AnimationClip[]; meta: PersonMeta }[]): Cast {
  const runs = people.map(({ body, clips, meta }, k) => {
    const p = new Performer(body, clips), r = rng(17 + k * 101);
    const step = meta.walker ? rounds(p, body, meta, r) : seated(p, meta.acts, r);
    return { p, step };
  });
  return {
    update(t, dt) {
      for (const { p, step } of runs) { step(t, dt); p.mixer.update(dt); }
    },
    state() { return Object.fromEntries(runs.map(({ p }, k) => [people[k].meta.who, p.current?.getClip().name ?? '-'])); },
    play(who, act) { const k = people.findIndex(x => x.meta.who === who); if (k >= 0 && runs[k].p.has(act)) runs[k].p.play(act, true, 0, 0); },
    current(who) { const k = people.findIndex(x => x.meta.who === who); return k >= 0 ? runs[k].p.current : null; },
  };
}
