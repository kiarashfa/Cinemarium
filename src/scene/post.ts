// The finish: ground-truth AO feeding the ambient light, temporal AA, depth of field focused on the room
// (the tilt-shift miniature read), a little bloom for screens and lamps, vignette and grain.
// Glass lives on its own layer and is left out of the depth/normal pre-pass, so focus and AO look
// through it at the room instead of stopping at the pane.
import * as THREE from 'three/webgpu';
import {
  builtinAOContext, float, length, mrt, normalView, packNormalToRGB, pass, sample, screenUV, smoothstep, uniform,
  unpackRGBToNormal, vec4, velocity,
} from 'three/tsl';
import { ao } from 'three/addons/tsl/display/GTAONode.js';
import { traa } from 'three/addons/tsl/display/TRAANode.js';
import { dof } from 'three/addons/tsl/display/DepthOfFieldNode.js';
import { bloom } from 'three/addons/tsl/display/BloomNode.js';
import { film } from 'three/addons/tsl/display/FilmNode.js';

/** Layer for glass: rendered in the beauty pass, skipped in the pre-pass. */
export const GLASS_LAYER = 2;

export interface PostOptions { quality: 'high' | 'low'; aoRadius?: number; bloom?: [number, number, number] }

export function createPost(renderer: THREE.WebGPURenderer, scene: THREE.Scene, camera: THREE.PerspectiveCamera, opts: PostOptions) {
  camera.layers.enable(GLASS_LAYER);
  const pipeline = new THREE.RenderPipeline(renderer);
  const high = opts.quality === 'high';

  const solid = new THREE.Layers(); solid.set(0);
  const pre = pass(scene, camera); pre.transparent = false; pre.setLayers(solid);
  pre.setMRT(mrt({ output: packNormalToRGB(normalView), velocity }));
  pre.getTexture('output').type = THREE.UnsignedByteType;
  const preNormal = sample(uv => unpackRGBToNormal(pre.getTextureNode().sample(uv)));
  const preDepth = pre.getTextureNode('depth'), preVelocity = pre.getTextureNode('velocity');

  const beauty = pass(scene, camera);
  let aoNode: ReturnType<typeof ao> | null = null;
  if (high) {
    aoNode = ao(preDepth, preNormal, camera);
    aoNode.resolutionScale = 0.5; aoNode.radius.value = opts.aoRadius ?? 0.05; aoNode.distanceExponent.value = 1.4; aoNode.thickness.value = 0.03; aoNode.samples.value = 16;
    beauty.contextNode = builtinAOContext(aoNode.getTextureNode().sample(screenUV).r);
  }
  const resolved = high ? traa(beauty, preDepth, preVelocity, camera) : beauty;

  const focus = { distance: uniform(3), range: uniform(0.35), bokeh: uniform(high ? 1.7 : 1.2) };
  const Q = new URLSearchParams(location.search);   // ?nodof ?nobloom: switches for judging the finish
  const focused = Q.has('nodof') ? resolved : dof(resolved, pre.getViewZNode(), focus.distance, focus.range, focus.bokeh);
  const [bs, br, bt] = opts.bloom ?? [0.18, 0.4, 1.1];
  const lit = Q.has('nobloom') ? focused : focused.add(bloom(focused, bs, br, bt));
  // a light vignette and grain, as a lens and a sensor would leave them
  const d = length(screenUV.sub(0.5)), vig = float(1).sub(smoothstep(0.35, 0.95, d).mul(0.28));
  pipeline.outputNode = film(vec4(lit.rgb.mul(vig), 1), float(high ? 0.06 : 0.04));

  return {
    pipeline, focus,
    render() { pipeline.render(); },
    dispose() { aoNode?.dispose(); pipeline.dispose(); },
  };
}

/** Marks every mesh using a glass material as glass for the pre-pass split. */
export function tagGlass(root: THREE.Object3D, isGlass: (m: THREE.Material) => boolean) {
  root.traverse(o => { const m = o as THREE.Mesh; if (m.isMesh && isGlass(m.material as THREE.Material)) m.layers.set(GLASS_LAYER); });
}
