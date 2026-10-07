// A baked room: static geometry lit by Cycles light maps (direct and bounce light, baked in Blender), and the
// living parts on top: motion-captured people lit by the room's own light, screens, a clock, a walker, and where a
// room has them, weather at the windows (rain on the glass, lightning baked as a second light the web flashes).
// Built by pipeline/blender; files in public/rooms/<id>/.
import * as THREE from 'three/webgpu';
import { color, float, lights, texture, uv, vec3, vec4 } from 'three/tsl';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { EXRLoader } from 'three/addons/loaders/EXRLoader.js';
import type { Room } from './types';
import { RENDERER, QUERY } from '../stage';
import { perform, type Cast, type PersonMeta } from './performers';
import { lightning, rainGlass } from './weather';

const gltf = new GLTFLoader(), exr = new EXRLoader(), image = new THREE.TextureLoader();

// Light maps already hold the bounce light, so the environment may only add reflections, not diffuse light.
const EnvironmentNode = (THREE as any).EnvironmentNode as { new(env: unknown): { setup(b: unknown): void } };
class ReflectionsOnly extends EnvironmentNode {
  setup(builder: any) {
    const ctx = builder.context, keep = ctx.iblIrradiance;
    ctx.iblIrradiance = vec3(0).toVar();
    super.setup(builder);
    ctx.iblIrradiance = keep;
  }
}
class RoomMaterial extends THREE.MeshPhysicalNodeMaterial {
  setupEnvironment(builder: any): any {
    const env = super.setupEnvironment(builder) as any;
    return env ? new ReflectionsOnly(env.envNode) : null;
  }
  /** Keep screen-space AO (the carpet: it gives the walking people their contact shadows). */
  keepAO = false;
  /** The light map holds the square root of the light (more of its 8 bits for the shadows): square it back. */
  lightMapSquared = false;
  setupLightMap(builder: any): any {
    if (!this.lightMapSquared || !this.lightMap) return super.setupLightMap(builder);
    const t = texture(this.lightMap, uv(1)).rgb;
    return new (THREE as any).IrradianceNode(t.mul(t).mul(this.lightMapIntensity));
  }
  // the light map already carries its occlusion; screen-space AO would darken the same corners twice
  setupMaterialLightings(builder: any) {
    const all = super.setupMaterialLightings(builder) as any[];
    return this.keepAO ? all : all.filter(n => !(n instanceof (THREE as any).AONode));
  }
}

const COPY = ['color', 'map', 'roughness', 'roughnessMap', 'metalness', 'metalnessMap', 'normalMap', 'normalScale', 'emissive', 'emissiveMap',
  'emissiveIntensity', 'aoMap', 'aoMapIntensity', 'alphaMap', 'alphaTest', 'transparent', 'opacity', 'side', 'vertexColors',
  'clearcoat', 'clearcoatRoughness', 'clearcoatMap', 'clearcoatRoughnessMap', 'clearcoatNormalMap', 'sheen', 'sheenColor', 'sheenRoughness',
  'specularIntensity', 'specularColor', 'ior', 'transmission', 'thickness', 'name'] as const;

function roomMaterial(src: THREE.MeshStandardMaterial, extra: Partial<RoomMaterial> = {}) {
  const m = new RoomMaterial();
  for (const k of COPY) { const v = (src as any)[k]; if (v === undefined) continue; const cur = (m as any)[k]; if (cur?.copy && v?.isColor || v?.isVector2) cur.copy(v); else (m as any)[k] = v; }
  return Object.assign(m, extra);
}

const asset = (id: string, f: string) => `${import.meta.env.BASE_URL}rooms/${id}/${f}`;

interface Emitter { x: number; y: number; z: number; r: number; L: number; color: [number, number, number] }
interface Window_ { x: number; y: number; z: number; w: number; h: number; L: number; color: [number, number, number]; /** turn about the vertical (default: facing x) */ ry?: number }
type Vec3 = [number, number, number];
interface Meta {
  wallHeight: number; lightmaps: Record<string, string>; lightMapIntensity: number; lightmapScale?: Record<string, number>;
  /** 'sqrt': light maps store sqrt(E / scale) (older files: E / scale) */
  lightmapEncoding?: 'sqrt';
  /** a second set of light maps, lightning alone: the web adds it in flashes */
  flashmaps?: Record<string, string>; flashScale?: Record<string, number>;
  /** how to light the people as the bake lit the room (Severance's older files list its troffers instead) */
  /** `at`: where to capture from; several points: each surface and person takes the nearest (a room of two lights) */
  capture?: { ceiling: Vec3; walls: Vec3; emitters: Emitter[]; windows: Window_[]; at?: Vec3 | Vec3[] };
  troffers?: { x: number; y: number; z: number; w: number; d: number; watts: number }[];
  live?: { flash?: { from: Vec3; color: Vec3 }; pills?: { who: string; act: string }; held?: Held[]; [k: string]: unknown };
  people: PersonMeta[];
}

/** A live screen: a canvas drawn every `every` seconds (0.12 by default; `draw` returns false when nothing changed),
 * `q` tells the screens of one room apart; `gain` its brightness; `bind` hands it the cast (a terminal that types as
 * someone types) and the room's live settings. */
export type Screen = (q: number) => { canvas: HTMLCanvasElement; draw(t: number): boolean | void; gain?: number; every?: number; bind?(cast: Cast, live: Meta['live']): void };
/** A prop carried in a hand during an act, between two moments of it (a mug picked up for a sip), at rest otherwise. */
interface Held { who: string; act: string; prop: string; hand: 'L' | 'R'; grab: number; release: number }

const loadMap = (id: string, f: string, scale: number) => (f.endsWith('.exr') ? exr : image).loadAsync(asset(id, f)).then(t => {
  // light maps: 8-bit sRGB WebP of E / scale for the web (EXR masters also work); UVs follow glTF, so no flip
  t.channel = 1; t.flipY = false; t.anisotropy = 4;
  t.colorSpace = f.endsWith('.exr') ? THREE.LinearSRGBColorSpace : THREE.SRGBColorSpace; t.needsUpdate = true;
  return { t, scale };
});

export async function bakedRoom(id: string, screen?: Screen): Promise<Room> {
  const meta: Meta = await (await fetch(asset(id, 'room.json'))).json();
  const groups = Object.keys(meta.lightmaps), flashGroups = Object.keys(meta.flashmaps ?? {});
  const [scene, maps, flashes] = await Promise.all([
    gltf.loadAsync(asset(id, 'room.glb')).then(g => g.scene),
    Promise.all(groups.map(g => loadMap(id, meta.lightmaps[g], meta.lightMapIntensity * (meta.lightmapScale?.[g] ?? 1)))),
    Promise.all(flashGroups.map(g => loadMap(id, meta.flashmaps![g], meta.flashScale?.[g] ?? 1))),
  ]);
  const atlas = Object.fromEntries(groups.map((g, i) => [g, maps[i]]));
  const flashAtlas = Object.fromEntries(flashGroups.map((g, i) => [g, flashes[i]]));
  const storm = flashGroups.length ? lightning() : null;

  const group = new THREE.Group(); group.add(scene);
  const none = lights([]), cache = new Map<string, THREE.Material>(), screens: { s: ReturnType<Screen>; tex: THREE.CanvasTexture; last: number }[] = [];
  const centres = new Map<string, THREE.Vector3>(), mugs: THREE.Mesh[] = [];
  let sectionFace: THREE.MeshBasicNodeMaterial | null = null;
  const hands: { pivot: THREE.Mesh; kind: string }[] = [];
  const lace: THREE.MeshBasicNodeMaterial[] = [];
  let clockCentre: THREE.Vector3 | null = null, glassView: THREE.MeshBasicNodeMaterial | null = null;
  scene.traverse(o => {
    const m = o as THREE.Mesh; if (!m.isMesh) return;
    m.castShadow = false; m.receiveShadow = false;
    // a mesh with several materials loads as a group of meshes, one per material, and its extras stay on the group
    const ud = (m.userData.lm || m.userData.role ? m.userData : m.parent?.userData ?? {}) as { lm?: string; role?: string; q?: number; who?: string };
    const src = m.material as THREE.MeshStandardMaterial;
    if (ud.role === 'screen' && screen) {
      const s = screen(ud.q ?? 0), tex = new THREE.CanvasTexture(s.canvas); tex.colorSpace = THREE.SRGBColorSpace;
      tex.flipY = false;               // glTF UVs run top-down (the exporter flips v), as the canvas does
      tex.generateMipmaps = false; tex.minFilter = THREE.LinearFilter;   // redrawn often: no mipmaps to rebuild on each upload
      const mat = new THREE.MeshBasicNodeMaterial({ map: tex, toneMapped: true }); mat.color.setScalar(s.gain ?? 1.6);
      m.material = mat; screens.push({ s, tex, last: -1 }); return;
    }
    if (ud.role === 'mug') { m.userData.who = ud.who; mugs.push(m); return; }   // lit like the people, once the room is captured
    // where the module's top cuts through walls and concrete: a flat dark cut face, as on an architect's model, which
    // neither the club's lights nor its reflections may lighten
    if (src?.name === 'section') { m.material = sectionFace ??= new THREE.MeshBasicNodeMaterial({ color: 0x141312 }); return; }
    if (ud.role === 'window') { m.material = glassView ??= rainGlass(storm?.flash ?? float(0) as any); return; }
    if (ud.role === 'lace') {        // lit from behind by the night (and the lightning), cut out by its own pattern
      const mat = new THREE.MeshBasicNodeMaterial({ map: src.map, alphaTest: 0.35, side: THREE.DoubleSide, transparent: false });
      const lt = texture(src.map!);              // keep the pattern's alpha: a colour node with no alpha would make it a solid sheet
      mat.colorNode = vec4(lt.rgb.mul(vec3(0.34, 0.42, 0.4).add(vec3(0.75, 0.85, 1.0).mul(storm ? storm.flash : float(0)))), lt.a);
      m.material = mat; lace.push(mat); return;
    }
    if (ud.role === 'glass' || ud.role === 'water') {
      // inside the case's glass a transparent object would vanish: an opaque glass that only reflects
      m.material = new THREE.MeshPhysicalNodeMaterial({ color: ud.role === 'glass' ? 0x8e9b98 : 0x5c6b68, roughness: 0.04, metalness: 0.1, clearcoat: 1, envMapIntensity: 1.6 });
      (m.material as THREE.MeshPhysicalNodeMaterial).lightsNode = none; return;
    }
    if (ud.lm && atlas[ud.lm]) {
      const centre = m.geometry.boundingSphere ?? (m.geometry.computeBoundingSphere(), m.geometry.boundingSphere!);
      const key = src.uuid + ud.lm + ':' + nearest(meta, centre.center);
      if (!cache.has(key)) {
        centres.set(key, centre.center.clone());
        const mat = roomMaterial(src, { lightMap: atlas[ud.lm].t, lightMapIntensity: atlas[ud.lm].scale, envMapIntensity: 0.55, lightMapSquared: meta.lightmapEncoding === 'sqrt' });
        // smoked polycarbonate chair mats are satin, not mirrors (a mirror picks up every ceiling panel)
        if (/chair_mat/.test(src.name)) { mat.roughness = 0.42; mat.envMapIntensity = 0.3; }
        // the partitions' bottle green: no sheen (it greys the fabric under top light), a deeper tint
        if (/partition/.test(src.name)) { mat.sheen = 0; mat.color.setRGB(0.8, 0.95, 0.84); }
        // an old mirror is tarnished: a dim reflection (a bright one turns the bulbs in the capture into a white glow)
        if (/mirror/.test(src.name)) mat.envMapIntensity = 0.14;
        // the walking people's contact shadows come from screen-space AO on the carpet (live depth, so every step)
        if (/carpet/.test(src.name)) mat.keepAO = true;
        // lightning: its own light map, added as light reflected by the surface's colour, as strong as the strike
        const fl = flashAtlas[ud.lm];
        if (fl && storm) {
          const albedo = src.map ? texture(src.map, uv()).rgb.mul(color(src.color)) : color(src.color);
          const own = src.emissiveMap ? texture(src.emissiveMap, uv()).rgb.mul(color(src.emissive)).mul(src.emissiveIntensity) : color(src.emissive).mul(src.emissiveIntensity);
          const ft = texture(fl.t, uv(1)).rgb, flashLight = meta.lightmapEncoding === 'sqrt' ? ft.mul(ft) : ft;
          mat.emissiveNode = (own as any).add((albedo as any).mul(flashLight).mul(fl.scale).mul(storm.flash));
        }
        cache.set(key, mat);
      }
      m.material = cache.get(key)!; (m.material as RoomMaterial).lightsNode = none;
    }
    if (m.name === 'wall_clock') { m.geometry.computeBoundingBox(); clockCentre = m.geometry.boundingBox!.getCenter(new THREE.Vector3()); }
    if (ud.role?.startsWith('clock_')) hands.push({ pivot: m, kind: ud.role.slice(6) });
  });
  // clock hands turn about the clock's centre (their geometry is in room coordinates)
  const clock = hands.map(({ pivot: mesh, kind }) => {
    const c = clockCentre ?? new THREE.Vector3(), p = new THREE.Group(); p.position.copy(c);
    mesh.geometry = mesh.geometry.clone(); mesh.geometry.translate(-c.x, -c.y, -c.z); mesh.position.set(0, 0, 0);
    // the hand as modelled points somewhere (a display time): find its tip, measured clockwise from twelve
    const pos = mesh.geometry.attributes.position; let tip = 0, tx = 0, ty = 1;
    for (let i = 0; i < pos.count; i++) { const x = pos.getX(i), y = pos.getY(i), r = x * x + y * y; if (r > tip) { tip = r; tx = x; ty = y; } }
    mesh.parent!.add(p); p.add(mesh); return { pivot: p, kind, rest: Math.atan2(tx, ty) };
  });

  // the room's own light, captured once: surfaces reflect it and the people are lit by it; lightning reaches the
  // people as a cold light from the windows, only while it flashes
  const captures = capturePoints(meta).map(at => captureRoom(group, meta, at));
  const envAt = (p: THREE.Vector3) => captures[nearest(meta, p)]?.texture ?? null;
  for (const [key, m] of cache) { const e = envAt(centres.get(key) ?? new THREE.Vector3()); if (e) (m as RoomMaterial).envMap = e; }
  let peopleLights = none, strike: THREE.DirectionalLight | null = null;
  if (storm && meta.live?.flash) {
    const f = meta.live.flash; strike = new THREE.DirectionalLight(new THREE.Color(...f.color), 0);
    strike.position.set(f.from[0] * 10, f.from[1] * 10, f.from[2] * 10); group.add(strike, strike.target);
    peopleLights = lights([strike]);
  }
  const bodies = await Promise.all(meta.people.map(async p => {
    const g = await gltf.loadAsync(asset(id, `people/${p.file}`));
    const body = g.scene;
    body.updateMatrixWorld(true);
    const pelvis = body.getObjectByName('Bip01_Pelvis'), env = envAt(pelvis ? pelvis.getWorldPosition(new THREE.Vector3()) : new THREE.Vector3());
    body.traverse(o => {
      const m = o as THREE.SkinnedMesh; if (!m.isMesh) return;
      m.frustumCulled = false;
      const src = m.material as THREE.MeshStandardMaterial;
      const mat = new THREE.MeshPhysicalNodeMaterial();
      for (const k of COPY) { const v = (src as any)[k]; if (v === undefined) continue; const cur = (mat as any)[k]; if (cur?.copy && (v?.isColor || v?.isVector2)) cur.copy(v); else (mat as any)[k] = v; }
      if (env) { mat.envMap = env; mat.envMapIntensity = 1; }
      mat.lightsNode = peopleLights;
      if (src.map && (src.transparent || src.alphaTest > 0 || /opacity|hair/i.test(src.name))) { mat.alphaTest = 0.45; mat.transparent = false; mat.side = THREE.DoubleSide; }
      m.material = mat;
    });
    group.add(body);
    return { body, clips: g.animations, meta: p };
  }));
  // each person's acts, crossfaded at random by weight; a walker on his rounds
  const cast = perform(bodies);
  if (QUERY.has('debug')) (window as any).__cast = cast;
  const pl = meta.live?.pills, pills = pl ? pillsFor(group, bodies.find(b => b.meta.who === pl.who)?.body, pl.who, pl.act, cast) : null;
  for (const m of mugs) {
    const src = m.material as THREE.MeshStandardMaterial, mat = new THREE.MeshPhysicalNodeMaterial();
    for (const k of COPY) { const v = (src as any)[k]; if (v === undefined) continue; const cur = (mat as any)[k]; if (cur?.copy && (v?.isColor || v?.isVector2)) cur.copy(v); else (mat as any)[k] = v; }
    const c = (m.geometry.computeBoundingSphere(), m.geometry.boundingSphere!.center), e = envAt(c);
    if (e) { mat.envMap = e; mat.envMapIntensity = 1; }
    mat.lightsNode = peopleLights; m.material = mat;
  }
  const held = (meta.live?.held ?? []).flatMap(h => {
    const body = bodies.find(b => b.meta.who === h.who)?.body, parts = mugs.filter(m => m.name.startsWith(h.prop));
    return body && parts.length ? [carried(group, body, parts, h, cast)] : [];
  });
  for (const sc of screens) sc.s.bind?.(cast, meta.live);

  return {
    group,
    update(t, dt) {
      cast.update(t, dt);
      if (storm) {
        if (QUERY.has('flash')) storm.flash.value = +(QUERY.get('flash') || 1); else storm.update(t);   // ?flash=1: hold a strike (screenshots)
        if (strike) strike.intensity = storm.flash.value * 2.6;
      }
      pills?.update();
      for (const h of held) h.update();
      for (const sc of screens) if (t - sc.last >= (sc.s.every ?? 0.12)) { sc.last = t; if (sc.s.draw(t) !== false) sc.tex.needsUpdate = true; }
      const now = new Date(), sec = now.getSeconds() + now.getMilliseconds() / 1000, min = now.getMinutes() + sec / 60, hr = (now.getHours() % 12) + min / 60;
      for (const h of clock) h.pivot.rotation.z = -((h.kind === 'h' ? hr / 12 : h.kind === 'm' ? min / 60 : Math.floor(sec) / 60) * Math.PI * 2 - h.rest);
    },
    dispose() { for (const c of captures) c?.dispose(); },
  };
}

/** Where the room is captured from (one point, or several), in room coordinates. */
function capturePoints(meta: Meta): (Vec3 | undefined)[] {
  const at = meta.capture?.at;
  return !at ? [undefined] : Array.isArray(at[0]) ? (at as Vec3[]) : [at as Vec3];
}

/** Which capture a point belongs to: the nearest capture point. */
function nearest(meta: Meta, p: THREE.Vector3) {
  const pts = capturePoints(meta); let best = 0, d = Infinity;
  pts.forEach((a, i) => { if (!a) return; const e = p.distanceToSquared(new THREE.Vector3(...a)); if (e < d) { d = e; best = i; } });
  return best;
}

/** A prop someone picks up: from `grab` to `release` seconds into their act it follows their hand (held as it was when
 * the hand closed on it); otherwise it stands where it was set down. */
function carried(group: THREE.Group, body: THREE.Object3D, parts: THREE.Mesh[], h: Held, cast: Cast) {
  const prop = new THREE.Group(), box = new THREE.Box3();
  for (const m of parts) box.expandByObject(m);
  box.getCenter(prop.position); group.add(prop); prop.updateMatrixWorld(true);
  for (const m of parts) prop.attach(m);
  const rest = prop.matrix.clone(), hand = body.getObjectByName(THREE.PropertyBinding.sanitizeNodeName(`Bip01 ${h.hand} Hand`));
  const offset = new THREE.Matrix4(), world = new THREE.Matrix4(), inv = new THREE.Matrix4();
  let holding = false;
  return {
    update() {
      const cur = cast.current(h.who);
      const on = !!hand && !!cur && cur.getClip().name === h.act && cur.time >= h.grab && cur.time <= h.release && cur.getEffectiveWeight() > 0.5;
      if (on) {
        hand!.updateWorldMatrix(true, false); prop.updateWorldMatrix(true, false);
        if (!holding) { offset.copy(hand!.matrixWorld).invert().multiply(prop.matrixWorld); holding = true; }
        world.multiplyMatrices(hand!.matrixWorld, offset);
        inv.copy(group.matrixWorld).invert(); world.premultiply(inv);
        world.decompose(prop.position, prop.quaternion, prop.scale);
      } else if (holding) {
        holding = false; rest.decompose(prop.position, prop.quaternion, prop.scale);
      }
    },
  };
}

/** The red pill and the blue: in the open palms of the one who offers them, only while he holds them out. */
function pillsFor(group: THREE.Group, body: THREE.Object3D | undefined, who: string, act: string, cast: ReturnType<typeof perform>) {
  if (!body) return null;
  const bone = (n: string) => body.getObjectByName(THREE.PropertyBinding.sanitizeNodeName(n));
  const sides = (['R', 'L'] as const).map((s, k) => {
    const hand = bone(`Bip01 ${s} Hand`), finger = bone(`Bip01 ${s} Finger2`);
    const mesh = new THREE.Mesh(new THREE.CapsuleGeometry(0.0042, 0.008, 4, 10),
      new THREE.MeshPhysicalNodeMaterial({ color: k ? 0x1f48c8 : 0xc4161c, emissive: k ? 0x0a1840 : 0x400608, roughness: 0.2, clearcoat: 1 }));
    mesh.rotation.z = Math.PI / 2; mesh.visible = false; group.add(mesh);
    return { hand, finger, mesh };
  });
  const a = new THREE.Vector3(), b = new THREE.Vector3();
  return {
    update() {
      const cur = cast.current(who);
      const on = !!cur && cur.getClip().name === act && cur.time > 1.7 && cur.time < cur.getClip().duration - 1.7 && cur.getEffectiveWeight() > 0.5;
      for (const s of sides) {
        s.mesh.visible = on && !!s.hand && !!s.finger;
        if (!s.mesh.visible) continue;
        s.hand!.getWorldPosition(a); s.finger!.getWorldPosition(b); group.worldToLocal(a); group.worldToLocal(b);
        s.mesh.position.lerpVectors(a, b, 0.55).y += 0.012;     // in the cup of the palm
      }
    },
  };
}

/** Renders the baked room from where its people are into a cube map, with what the cut-away hides: the ceiling, the
 * missing walls and the light sources (bulbs, windows; or Severance's ceiling troffers). */
function captureRoom(group: THREE.Group, meta: Meta, at?: Vec3) {
  if (!RENDERER) return null;
  const H = meta.wallHeight, scene = new THREE.Scene(), parent = group.parent, c = meta.capture;
  scene.add(group);
  const extra = new THREE.Group(); scene.add(extra);
  const basic = (col: number | THREE.Color) => new THREE.MeshBasicNodeMaterial({ color: col, side: THREE.DoubleSide });
  const ceiling = new THREE.Mesh(new THREE.PlaneGeometry(9.6, 7.6), basic(c ? new THREE.Color(...c.ceiling) : new THREE.Color(0.42, 0.43, 0.43)));
  ceiling.rotation.x = Math.PI / 2; ceiling.position.y = H; extra.add(ceiling);
  for (const t of meta.troffers ?? []) {
    const L = t.watts / (Math.PI * t.w * t.d);
    const p = new THREE.Mesh(new THREE.PlaneGeometry(t.w, t.d), basic(new THREE.Color(0.97, 0.985, 1).multiplyScalar(L))); p.rotation.x = Math.PI / 2; p.position.set(t.x, H - 0.004, t.z); extra.add(p);
  }
  for (const e of c?.emitters ?? []) {
    const s = new THREE.Mesh(new THREE.SphereGeometry(e.r, 12, 8), basic(new THREE.Color(...e.color).multiplyScalar(e.L))); s.position.set(e.x, e.y, e.z); extra.add(s);
  }
  for (const w of c?.windows ?? []) {
    const p = new THREE.Mesh(new THREE.PlaneGeometry(w.w, w.h), basic(new THREE.Color(...w.color).multiplyScalar(w.L))); p.rotation.y = w.ry ?? Math.PI / 2; p.position.set(w.x, w.y, w.z); extra.add(p);
  }
  // the walls the cut-away removed, so reflections see a room rather than a void
  const wall = basic(c ? new THREE.Color(...c.walls) : new THREE.Color(0.5, 0.52, 0.5));
  const front = new THREE.Mesh(new THREE.PlaneGeometry(9.6, H), wall); front.position.set(0, H / 2, 3.74); extra.add(front);
  const right = new THREE.Mesh(new THREE.PlaneGeometry(7.6, H), wall); right.rotation.y = Math.PI / 2; right.position.set(4.74, H / 2, 0); extra.add(right);
  const rt = new THREE.CubeRenderTarget(256, { type: THREE.HalfFloatType, generateMipmaps: true });
  const cam = new THREE.CubeCamera(0.05, 30, rt); cam.position.set(...(at ?? [0.15, 1.25, -0.55])); scene.add(cam);
  cam.update(RENDERER, scene);
  scene.remove(group); parent?.add(group);
  extra.traverse(o => { const m = o as THREE.Mesh; if (m.isMesh) { m.geometry.dispose(); (m.material as THREE.Material).dispose(); } });
  return rt;
}
