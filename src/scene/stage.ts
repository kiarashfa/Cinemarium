// Renderer, camera and the frame loop shared by both layouts.
import * as THREE from 'three/webgpu';
import { RectAreaLightTexturesLib } from 'three/addons/lights/RectAreaLightTexturesLib.js';
import { createPost, tagGlass } from './post';
import { glass, glassEdge } from './materials';

export const QUERY = new URLSearchParams(location.search);
/** `?still` freezes time for screenshots; `?q=low` forces the phone tier. */
export const STILL = QUERY.has('still');
export const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
export const QUALITY: 'high' | 'low' = (QUERY.get('q') as 'high' | 'low') ?? (matchMedia('(pointer: coarse)').matches || innerWidth < 760 ? 'low' : 'high');

declare global { interface Window { __frames: number; __ready: boolean; __backend: string } }

/** The page's renderer, for loaders that render something once (a room's own reflections). */
export let RENDERER: THREE.WebGPURenderer | null = null;

export async function createStage(canvas: HTMLCanvasElement, { fov = 30, near = 0.05, far = 900 } = {}) {
  THREE.RectAreaLightNode.setLTC(RectAreaLightTexturesLib.init());
  const renderer = new THREE.WebGPURenderer({ canvas, antialias: false, powerPreference: 'high-performance', forceWebGL: QUERY.has('webgl') });
  await renderer.init(); RENDERER = renderer;
  renderer.setPixelRatio(Math.min(devicePixelRatio, QUALITY === 'high' ? 1.5 : 1.25));
  renderer.toneMapping = THREE.AgXToneMapping;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFShadowMap;
  window.__backend = (renderer.backend as unknown as { isWebGPUBackend?: boolean }).isWebGPUBackend ? 'webgpu' : 'webgl2';
  const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(fov, 1, near, far);
  return { renderer, scene, camera };
}

export function startLoop(
  { renderer, scene, camera }: { renderer: THREE.WebGPURenderer; scene: THREE.Scene; camera: THREE.PerspectiveCamera },
  { aoRadius, bloom, fov }: { aoRadius?: number; bloom?: [number, number, number]; fov: (portrait: boolean) => number },
  tick: (t: number, dt: number, post: ReturnType<typeof createPost>) => void,
) {
  tagGlass(scene, m => m === glass || m === glassEdge || (m as THREE.MeshPhysicalMaterial).transmission > 0);
  const post = createPost(renderer, scene, camera, { quality: QUALITY, aoRadius, bloom });
  if (QUERY.has('debug')) Object.assign(window, { __scene: scene, __camera: camera, __renderer: renderer });
  const resize = () => {
    const w = innerWidth, h = innerHeight; renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.fov = fov(w < h); camera.updateProjectionMatrix();
  };
  addEventListener('resize', resize); resize();
  let last = performance.now(), t = 3;
  window.__frames = 0;
  renderer.setAnimationLoop(now => {
    const dt = STILL ? 0 : Math.min(0.05, (now - last) / 1000); last = now; t += dt;
    tick(t, dt, post);
    post.render();
    window.__frames++;
  });
  return post;
}
