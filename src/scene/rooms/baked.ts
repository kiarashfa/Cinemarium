// A baked room: static geometry lit by Cycles light maps (direct and bounce light, baked in Blender), and the
// living parts on top: motion-captured people lit by the room's own lights, screens, a clock, a walker.
// Built by pipeline/blender (see docs/pipeline.md); files in public/rooms/<id>/.
import * as THREE from 'three/webgpu';
import { lights, vec3 } from 'three/tsl';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { EXRLoader } from 'three/addons/loaders/EXRLoader.js';
import type { Room } from './types';
import { RENDERER } from '../stage';

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
  setupEnvironment(builder: any) {
    const env = super.setupEnvironment(builder) as any;
    return env ? new ReflectionsOnly(env.envNode) : null;
  }
  /** Keep screen-space AO (the carpet: it gives the walking people their contact shadows). */
  keepAO = false;
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

interface Meta {
  wallHeight: number; lightmaps: Record<string, string>; lightMapIntensity: number; lightmapScale?: Record<string, number>;
  troffers: { x: number; y: number; z: number; w: number; d: number; watts: number }[];
  people: { who: string; file: string; clip: string; walk?: boolean }[];
  walk: [number, number][];
}

export async function bakedRoom(id: string, screen?: (q: number) => { canvas: HTMLCanvasElement; draw(t: number): void }): Promise<Room> {
  const meta: Meta = await (await fetch(asset(id, 'room.json'))).json();
  const [scene, ...maps] = await Promise.all([
    gltf.loadAsync(asset(id, 'room.glb')).then(g => g.scene),
    ...Object.values(meta.lightmaps).map(f => (f.endsWith('.exr') ? exr : image).loadAsync(asset(id, f))),
  ]);
  // light maps: 8-bit sRGB WebP of E / scale for the web (EXR masters also work); UVs follow glTF, so no flip
  const atlas: Record<string, THREE.Texture> = {}, intensity: Record<string, number> = {};
  Object.entries(meta.lightmaps).forEach(([k, f], i) => {
    const t = maps[i] as THREE.Texture; t.channel = 1; t.flipY = false; t.anisotropy = 4;
    t.colorSpace = f.endsWith('.exr') ? THREE.LinearSRGBColorSpace : THREE.SRGBColorSpace; t.needsUpdate = true;
    atlas[k] = t; intensity[k] = meta.lightMapIntensity * (meta.lightmapScale?.[k] ?? 1);
  });

  const group = new THREE.Group(); group.add(scene);
  const none = lights([]), cache = new Map<string, THREE.Material>(), screens: { mat: THREE.MeshBasicNodeMaterial; draw(t: number): void; tex: THREE.CanvasTexture }[] = [];
  const hands: { pivot: THREE.Object3D; kind: string }[] = [];
  let clockCentre: THREE.Vector3 | null = null;
  scene.traverse(o => {
    const m = o as THREE.Mesh; if (!m.isMesh) return;
    m.castShadow = false; m.receiveShadow = false;
    const ud = m.userData as { lm?: string; role?: string; q?: number };
    if (ud.role === 'screen' && screen) {
      const s = screen(ud.q ?? 0), tex = new THREE.CanvasTexture(s.canvas); tex.colorSpace = THREE.SRGBColorSpace;
      const mat = new THREE.MeshBasicNodeMaterial({ map: tex, toneMapped: true }); mat.color.setScalar(1.6);
      m.material = mat; screens.push({ mat, draw: s.draw, tex }); return;
    }
    const src = m.material as THREE.MeshStandardMaterial;
    if (ud.lm && atlas[ud.lm]) {
      const key = src.uuid + ud.lm;
      if (!cache.has(key)) {
        const mat = roomMaterial(src, { lightMap: atlas[ud.lm], lightMapIntensity: intensity[ud.lm], envMapIntensity: 0.55 });
        // smoked polycarbonate chair mats are satin, not mirrors (a mirror picks up every ceiling panel)
        if (/chair_mat/.test(src.name)) { mat.roughness = 0.42; mat.envMapIntensity = 0.3; }
        // the partitions' bottle green: no sheen (it greys the fabric under top light), a deeper tint
        if (/partition/.test(src.name)) { mat.sheen = 0; mat.color.setRGB(0.8, 0.95, 0.84); }
        // the walking people's contact shadows come from screen-space AO on the carpet (live depth, so every step)
        if (/carpet/.test(src.name)) mat.keepAO = true;
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

  // the room's own light, captured once: the desks reflect it and the people are lit by it
  const env = captureRoom(group, meta);
  if (env) for (const m of cache.values()) { (m as RoomMaterial).envMap = env; }
  const mixers: THREE.AnimationMixer[] = [];
  let walker: { body: THREE.Object3D; mixer: THREE.AnimationMixer } | null = null;
  await Promise.all(meta.people.map(async (p, i) => {
    const g = await gltf.loadAsync(asset(id, `people/${p.file}`));
    const body = g.scene;
    body.traverse(o => {
      const m = o as THREE.SkinnedMesh; if (!m.isMesh) return;
      m.frustumCulled = false;
      const src = m.material as THREE.MeshStandardMaterial;
      const mat = new THREE.MeshPhysicalNodeMaterial();
      for (const k of COPY) { const v = (src as any)[k]; if (v === undefined) continue; const cur = (mat as any)[k]; if (cur?.copy && (v?.isColor || v?.isVector2)) cur.copy(v); else (mat as any)[k] = v; }
      if (env) { mat.envMap = env; mat.envMapIntensity = 1; }
      mat.lightsNode = none;
      if (src.map && (src.transparent || src.alphaTest > 0 || /opacity|hair/i.test(src.name))) { mat.alphaTest = 0.45; mat.transparent = false; mat.side = THREE.DoubleSide; }
      m.material = mat;
    });
    const mixer = new THREE.AnimationMixer(body), clip = g.animations.find(a => a.name === p.clip) ?? g.animations[0];
    if (clip) { const a = mixer.clipAction(clip); a.play(); a.time = (i * 2.3) % clip.duration; }
    mixers.push(mixer); group.add(body);
    if (p.walk) walker = { body, mixer };
  }));

  // Milchick's rounds: along the path at walking pace, turning smoothly into each leg
  const path = meta.walk.map(([x, y]) => new THREE.Vector2(x, -y));
  const legs = path.map((a, i) => a.distanceTo(path[(i + 1) % path.length])), loop = legs.reduce((s, l) => s + l, 0);
  const pos = new THREE.Vector2();
  function walk(t: number) {
    if (!walker) return;
    let s = (t * 1.0) % loop, i = 0; while (s > legs[i]) { s -= legs[i]; i++; }
    const a = path[i], b = path[(i + 1) % path.length]; pos.lerpVectors(a, b, s / legs[i]);
    const w = walker as { body: THREE.Object3D };
    w.body.position.set(pos.x, 0, pos.y);
    const want = Math.atan2(b.x - a.x, b.y - a.y); let d = want - w.body.rotation.y; d = Math.atan2(Math.sin(d), Math.cos(d)); w.body.rotation.y += d * 0.1;

  }

  let last = -1;
  return {
    group,
    update(t, dt) {
      for (const m of mixers) m.update(dt);
      walk(t);
      if (t - last > 0.12) { last = t; for (const s of screens) { s.draw(t); s.tex.needsUpdate = true; } }
      const now = new Date(), sec = now.getSeconds() + now.getMilliseconds() / 1000, min = now.getMinutes() + sec / 60, hr = (now.getHours() % 12) + min / 60;
      for (const h of clock) h.pivot.rotation.z = -((h.kind === 'h' ? hr / 12 : h.kind === 'm' ? min / 60 : Math.floor(sec) / 60) * Math.PI * 2 - h.rest);
    },
  };
}

/** Renders the baked room from its middle into a cube map, with the ceiling it was baked under. */
function captureRoom(group: THREE.Group, meta: Meta) {
  if (!RENDERER) return null;
  const H = meta.wallHeight, scene = new THREE.Scene(), parent = group.parent;
  scene.add(group);
  const extra = new THREE.Group(); scene.add(extra);
  const basic = (c: number | THREE.Color) => new THREE.MeshBasicNodeMaterial({ color: c, side: THREE.DoubleSide });
  const ceiling = new THREE.Mesh(new THREE.PlaneGeometry(9.6, 7.6), basic(new THREE.Color(0.42, 0.43, 0.43))); ceiling.rotation.x = Math.PI / 2; ceiling.position.y = H; extra.add(ceiling);
  for (const t of meta.troffers) {
    const L = t.watts / (Math.PI * t.w * t.d);
    const p = new THREE.Mesh(new THREE.PlaneGeometry(t.w, t.d), basic(new THREE.Color(0.97, 0.985, 1).multiplyScalar(L))); p.rotation.x = Math.PI / 2; p.position.set(t.x, H - 0.004, t.z); extra.add(p);
  }
  // the walls the cut-away removed, so reflections see a room rather than a void
  const wall = basic(new THREE.Color(0.5, 0.52, 0.5));
  const front = new THREE.Mesh(new THREE.PlaneGeometry(9.6, H), wall); front.position.set(0, H / 2, 3.74); extra.add(front);
  const right = new THREE.Mesh(new THREE.PlaneGeometry(7.6, H), wall); right.rotation.y = Math.PI / 2; right.position.set(4.74, H / 2, 0); extra.add(right);
  const rt = new THREE.CubeRenderTarget(256, { type: THREE.HalfFloatType, generateMipmaps: true });
  const cam = new THREE.CubeCamera(0.05, 30, rt); cam.position.set(0.15, 1.25, -0.55); scene.add(cam);
  cam.update(RENDERER, scene);
  scene.remove(group); parent?.add(group);
  extra.traverse(o => { const m = o as THREE.Mesh; if (m.isMesh) { m.geometry.dispose(); (m.material as THREE.Material).dispose(); } });
  return rt.texture;
}
