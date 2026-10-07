// Renderer, camera, the frame loop, and the quality ladder: the club starts on a rung that suits the GPU and steps
// down (fewer pixels, then fewer effects) whenever frames run slow, so it keeps its pace on integrated graphics too.
// The rung reached is remembered per GPU for the next visit.
import * as THREE from 'three/webgpu';
import { RectAreaLightTexturesLib } from 'three/addons/lights/RectAreaLightTexturesLib.js';
import { createPost, tagGlass, type Post, type Tier } from './post';
import { glass, glassEdge } from './materials';

export const QUERY = new URLSearchParams(location.search);
/** `?still` freezes time for screenshots; `?q=high|medium|low` pins the quality. */
export const STILL = QUERY.has('still');
export const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
const PHONE = matchMedia('(pointer: coarse)').matches || innerWidth < 760;

/** A rung of the ladder: the post tier, pixels per CSS pixel (capped by the screen's own), the floor's mirror. */
export interface Rung { tier: Tier; ratio: number; mirror: boolean }
const LADDER: Rung[] = [
  { tier: 'high', ratio: 1.5, mirror: true },
  { tier: 'high', ratio: 1.25, mirror: true },
  { tier: 'medium', ratio: 1.25, mirror: false },
  { tier: 'medium', ratio: 1, mirror: false },
  { tier: 'low', ratio: 1, mirror: false },
  { tier: 'low', ratio: 0.75, mirror: false },
];
const PINNED: Record<string, number> = { high: 0, medium: 2, low: 4 };
const BUDGET = 1000 / 45;   // ms a frame may take on average before the next rung down
const KEY = 'cinemarium.rung:';

declare global { interface Window { __frames: number; __ready: boolean; __backend: string; __quality: { gpu: string; rung: number; ms: number } } }

/** The page's renderer, for loaders that render something once (a room's own reflections). */
export let RENDERER: THREE.WebGPURenderer | null = null;

export async function createStage(canvas: HTMLCanvasElement, { fov = 30, near = 0.05, far = 900 } = {}) {
  THREE.RectAreaLightNode.setLTC(RectAreaLightTexturesLib.init());
  const renderer = new THREE.WebGPURenderer({ canvas, antialias: false, powerPreference: 'high-performance', forceWebGL: QUERY.has('webgl') });
  await renderer.init(); RENDERER = renderer;
  renderer.toneMapping = THREE.AgXToneMapping;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFShadowMap;
  const backend = renderer.backend as unknown as { isWebGPUBackend?: boolean; device?: { adapterInfo?: GPUAdapterInfo }; gl?: WebGL2RenderingContext };
  window.__backend = backend.isWebGPUBackend ? 'webgpu' : 'webgl2';
  const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(fov, 1, near, far);
  const gpu = gpuName(backend), first = firstRung(gpu);
  return { renderer, scene, camera, gpu, rung: LADDER[first.at], first };
}
export type Stage = Awaited<ReturnType<typeof createStage>>;

function gpuName(b: { device?: { adapterInfo?: GPUAdapterInfo }; gl?: WebGL2RenderingContext }) {
  const info = b.device?.adapterInfo;
  if (info) return [info.vendor, info.architecture, info.description, (info as { isFallbackAdapter?: boolean }).isFallbackAdapter ? 'fallback' : ''].filter(Boolean).join(' ');
  const ext = b.gl?.getExtension('WEBGL_debug_renderer_info');
  return ext ? String(b.gl!.getParameter(ext.UNMASKED_RENDERER_WEBGL)) : '';
}

/** Where to start: pinned by ?q=, else the rung this GPU reached last time, else a guess from its name. */
function firstRung(gpu: string) {
  const q = QUERY.get('q') ?? '';
  if (q in PINNED) return { at: PINNED[q], pinned: true };
  try { const s = localStorage.getItem(KEY + gpu); if (s !== null && LADDER[+s]) return { at: +s, pinned: false }; } catch { /* no storage */ }
  const at = /swiftshader|llvmpipe|basic render|fallback/i.test(gpu) ? 5 : PHONE ? 3
    : /nvidia|geforce|quadro|amd|radeon|\bati\b/i.test(gpu) ? 0 : /apple/i.test(gpu) ? 1 : 2;
  return { at, pinned: false };
}

export interface LoopOptions {
  aoRadius?: number; bloom?: [number, number, number];
  fov: (portrait: boolean) => number;
  /** Told whenever the rung changes (the floor's mirror follows it). */
  onRung?: (r: Rung) => void;
}

export function startLoop(stage: Stage, opts: LoopOptions, tick: (t: number, dt: number, post: Post) => void) {
  const { renderer, scene, camera, gpu } = stage;
  tagGlass(scene, m => m === glass || m === glassEdge || (m as THREE.MeshPhysicalMaterial).transmission > 0);
  let at = stage.first.at, post: Post | null = null;
  if (QUERY.has('debug')) Object.assign(window, { __scene: scene, __camera: camera, __renderer: renderer });
  const resize = () => {
    const w = innerWidth, h = innerHeight; renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.fov = opts.fov(w < h); camera.updateProjectionMatrix();
  };
  const apply = () => {
    const r = LADDER[at];
    renderer.setPixelRatio(Math.min(devicePixelRatio, r.ratio)); resize();
    post?.dispose(); post = createPost(renderer, scene, camera, { tier: r.tier, aoRadius: opts.aoRadius, bloom: opts.bloom });
    opts.onRung?.(r); window.__quality = { gpu, rung: at, ms: 0 };
  };
  addEventListener('resize', resize); apply();

  // the governor: average the frame time over a stretch; too slow, and the next rung down is taken
  let settle = 90, sum = 0, n = 0;
  const govern = (ms: number) => {
    if (stage.first.pinned || STILL || at === LADDER.length - 1) return;
    if (settle > 0) { settle--; return; }
    if (ms > 200) return;                     // a hitch (shaders compiling, the tab coming back), not the pace
    sum += ms; if (++n < 120) return;
    const avg = sum / n; sum = n = 0; window.__quality.ms = Math.round(avg * 10) / 10;
    if (avg <= BUDGET) return;
    at++; apply(); settle = 90;
    try { localStorage.setItem(KEY + gpu, String(at)); } catch { /* no storage */ }
  };

  let last = performance.now(), t = 3;
  window.__frames = 0;
  renderer.setAnimationLoop(now => {
    const ms = now - last; last = now;
    const dt = STILL ? 0 : Math.min(0.05, ms / 1000); t += dt;
    tick(t, dt, post!);
    post!.render();
    window.__frames++;
    govern(ms);
  });
  /** Pause the governor for a moment: something heavy (a room) just arrived. */
  return { settle() { settle = Math.max(settle, 90); sum = n = 0; } };
}
