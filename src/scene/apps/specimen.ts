// The Case: one glass case on its plinth in the Rotunda, a circular video club. The visit opens on the whole room;
// a click (or the wheel) steps up to the case, the wheel again leans in until the room reads as a miniature.
// Choosing another title sinks the room into the plinth and lifts the next one up, like a museum lift. Drag to walk
// around it.
import * as THREE from 'three/webgpu';
import { createStage, startLoop, STILL, REDUCED, QUERY } from '../stage';
import { buildAmbient } from '../ambients';
import { buildCase } from '../case';
import { CASE } from '../module';
import { lacquer } from '../materials';
import { loadRoom, mount, type Room } from '../rooms';
import { powerOf } from '../power';
import { sorted, label, KIND_NAME, KIND_PATH, type Title } from '../../data/titles';

const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;

export async function startSpecimen(canvas: HTMLCanvasElement, first: Title) {
  const stage = await createStage(canvas, { fov: 32, far: 80 });
  const { renderer, scene, camera } = stage;
  const amb = await buildAmbient('rotunda', scene, renderer, { centre: new THREE.Vector3(0, 1.25, -0.4), height: 1.6, width: CASE.w + 0.14 });
  renderer.toneMappingExposure = amb.exposure;

  const vit = buildCase({ label: first.title });
  if (amb.daylight) {   // in daylight the black lacquer reads warmer as a dark bronze-brown
    const day = lacquer.clone(); day.color.setHex(0x2a2520);
    vit.group.traverse(o => { const m = o as THREE.Mesh; if (m.isMesh && m.material === lacquer) m.material = day; });
  }
  vit.group.position.set(0, 0, -0.4); scene.add(vit.group);
  if (QUERY.has('noglass')) vit.group.traverse(o => { const m = o as THREE.Mesh; if (m.isMesh && ((m.material as THREE.MeshPhysicalMaterial).transmission > 0 || (m.material as THREE.Material).transparent)) m.visible = false; });

  const list = sorted(first.kind);
  let cur = Math.max(0, list.findIndex(t => t.slug === first.slug)), want = cur;
  let shown: Room | null = null, lift = 0, liftDir = 0, swapping = false;
  // in a sunlit hall the room's own light reads a touch dim: lift it a little (lights, screens, light maps)
  const show = (r: Room) => { mount(vit.stage, r); powerOf(r.group).set(amb.roomPower ?? 1); };
  shown = await loadRoom(list[cur].room); show(shown);

  $('pills').innerHTML = list.map((t, i) => `<button data-i="${i}">${t.title}</button>`).join('');
  $('pills').addEventListener('click', e => { const b = (e.target as HTMLElement).closest('button'); if (b) go(+b.dataset.i!); });
  function caption() {
    const t = list[cur], cap = $('cap'); cap.classList.add('out');
    setTimeout(() => {
      $('k').textContent = `${KIND_NAME[t.kind]} · ${cur + 1} of ${list.length}`;
      $('nm').textContent = label(t); $('sc').textContent = t.scene; document.title = `${label(t)} · Cinemarium`;
      $('rt').innerHTML = t.imdb.rating ? `IMDb <b>${t.imdb.rating.toFixed(1)}</b>` : '';
      cap.classList.remove('out');
    }, STILL ? 0 : 280);
    for (const b of $('pills').querySelectorAll('button')) b.classList.toggle('on', +b.dataset.i! === cur);
  }
  function go(i: number) {
    const n = (i + list.length) % list.length; if (n === want) return; want = n;
    history.replaceState(null, '', `${import.meta.env.BASE_URL}${KIND_PATH[list[n].kind]}/${list[n].slug}/${location.search}`);
    if (liftDir === 0) liftDir = -1;
  }
  addEventListener('keydown', e => { if (e.key === 'ArrowRight') go(want + 1); if (e.key === 'ArrowLeft') go(want - 1); });
  caption();

  // three distances: 0 the whole room, 1 the case, 2 close enough to read the room as a miniature.
  // ?view=room|case|close (or ?zoom for close) picks one to start with.
  const VIEWS = ['room', 'case', 'close'], q = QUERY.has('zoom') ? 'close' : QUERY.get('view') ?? 'room';
  let zoom = Math.max(0, VIEWS.indexOf(q)), zk = zoom, wheelLock = 0;
  const zb = $<HTMLButtonElement>('zoom'), hint = $('hint');
  const setZoom = (z: number) => {
    zoom = Math.max(0, Math.min(2, z));
    zb.textContent = ['Step closer', 'Look closer', 'Step back'][zoom]; zb.setAttribute('aria-pressed', String(zoom === 2));
    hint.textContent = zoom ? 'Drag to walk around the case' : 'Click to approach · drag to walk around';
  };
  zb.addEventListener('click', () => setZoom(zoom === 2 ? 1 : zoom + 1)); setZoom(zoom);
  addEventListener('wheel', e => {
    if (Math.abs(e.deltaY) < 8 || performance.now() < wheelLock) return;
    wheelLock = performance.now() + 600; setZoom(zoom + (e.deltaY < 0 ? 1 : -1));
  }, { passive: true });
  addEventListener('keydown', e => { if (e.key === 'Escape') setZoom(0); if (e.key === '+' || e.key === '=') setZoom(zoom + 1); if (e.key === '-') setZoom(zoom - 1); });
  // orbit by drag, a slow drift when idle
  let th = +(QUERY.get('th') ?? 0.55), thV = 0, drag: number | null = null, idle = 0;
  let moved = 0;
  canvas.addEventListener('pointerdown', e => { drag = e.clientX; moved = 0; idle = 0; canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener('pointermove', e => { if (drag === null) return; thV = (e.clientX - drag) * -0.006; th += thV; moved += Math.abs(e.clientX - drag); drag = e.clientX; });
  canvas.addEventListener('pointerup', () => { if (drag !== null && moved < 6 && zoom === 0) setZoom(1); drag = null; });   // a click, not a drag

  const look = new THREE.Vector3(), centre = new THREE.Vector3(0, vit.top - CASE.h / 2, -0.4);
  startLoop(stage, { fov: p => p ? 46 : 32, aoRadius: 0.05, bloom: [0.14, 0.4, 1.05] }, (t, dt, post) => {
    idle += dt;
    if (drag === null) { thV *= 0.92; th += thV + (idle > 4 && !REDUCED && !STILL ? dt * 0.05 : 0); }
    if (liftDir && !swapping) {
      lift += liftDir * dt / 0.9;
      if (lift <= -1) {
        lift = -1; swapping = true; cur = want; caption(); vit.setLabel(list[cur].title);
        loadRoom(list[cur].room).then(r => { shown = r; show(r); liftDir = 1; swapping = false; });
      }
      if (lift >= 0 && liftDir === 1) { lift = 0; liftDir = 0; if (want !== cur) liftDir = -1; }
    }
    if (shown) { shown.group.position.y = 0.0015 + (lift < 0 ? -(1 - Math.cos(-lift * Math.PI / 2)) : 0) * 0.75; shown.update(t, dt || 1e-4); }
    zk += (zoom - zk) * (STILL || REDUCED ? 1 : 1 - Math.exp(-dt * 2.2));
    // each value at the three distances (room, case, close), blended along zk
    const portrait = innerWidth < innerHeight, L = (v: [number, number, number]) => zk <= 1 ? v[0] + (v[1] - v[0]) * zk : v[1] + (v[2] - v[1]) * (zk - 1);
    const R = L(portrait ? [7.0, 5.7, 2.9] : [6.0, 3.55, 1.7]), off = portrait ? 0 : L([0, 0.45, 0.12]);
    camera.position.set(Math.sin(th) * R, L(portrait ? [2.9, 3.1, 2.0] : [2.6, 2.3, 1.62]), Math.cos(th) * R - 0.4);
    look.set(-Math.cos(th) * off, L(portrait ? [1.8, 0.95, 1.06] : [1.95, 1.08, 1.06]), -0.4 + Math.sin(th) * off); camera.lookAt(look);
    const fov = L(portrait ? [64, 46, 46] : [46, 32, 32]);
    if (Math.abs(camera.fov - fov) > 0.01) { camera.fov = fov; camera.updateProjectionMatrix(); }
    post.focus.distance.value = camera.position.distanceTo(centre);
    post.focus.range.value = L([2.6, 1.15, 0.75]);
  });
  window.__ready = true;
  $('loading').classList.add('done');
}
