// The Tower: one glass building in a reading room, ten storeys, one title per floor, No. 1 at the top.
// The visit opens on the whole tower in its room; a click (or the wheel) rides up to a floor, where the wheel moves
// between floors and "Look closer" leans in. The switch re-dresses the whole building: each floor's lights go out, its room
// changes from series to film (or back), and the lights come on again, floor by floor.
import * as THREE from 'three/webgpu';
import { createStage, startLoop, STILL, REDUCED, QUERY } from '../stage';
import { buildAmbient } from '../ambients';
import { buildTower } from '../tower';
import { CASE, FLOOR } from '../module';
import { loadRoom, mount, type Room } from '../rooms';
import { powerOf, type Power } from '../power';
import { sorted, label, KIND_NAME, KIND_PATH, type Kind, type Sort, type Title } from '../../data/titles';

const STOREYS = 10;
const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;

export async function startTower(canvas: HTMLCanvasElement) {
  const stage = await createStage(canvas, { fov: 30, far: 900 });
  const { renderer, scene, camera } = stage;
  const height = 0.55 + STOREYS * FLOOR.h + FLOOR.slab;
  const amb = await buildAmbient('reading', scene, renderer, { centre: new THREE.Vector3(0, height / 2, -0.3), height, width: CASE.w + 0.3 });
  renderer.toneMappingExposure = amb.exposure;
  const tower = buildTower(STOREYS); tower.group.position.z = -0.3; scene.add(tower.group);

  let kind: Kind = QUERY.get('kind') === 'films' ? 'film' : 'series';
  let by: Sort = (QUERY.get('sort') as Sort) || 'rank';
  // floor i (0 = lowest) holds the title ranked STOREYS - i
  const slot = Array.from({ length: STOREYS }, () => ({} as { title?: Title; room?: Room; power?: Power }));
  const titleAt = (list: Title[], floor: number) => list[STOREYS - 1 - floor];

  async function dress(list: Title[], { animate }: { animate: boolean }) {
    const jobs = tower.floors.map(async f => {
      const s = slot[f.index], next = titleAt(list, f.index);
      if (s.title?.slug === next?.slug) return;
      const delay = animate ? f.index * 70 : 0;
      if (animate && s.power) await fade(s.power, 0, 420, delay);
      for (const c of [...f.stage.children]) f.stage.remove(c);
      f.vacant.visible = true;
      s.title = next; s.room = undefined; s.power = undefined;
      if (!next) return;
      const room = await loadRoom(next.room).catch(err => { console.error(err); return null; });
      if (!room || s.title !== next) return;
      mount(f.stage, room); f.vacant.visible = false; s.room = room; s.power = powerOf(room.group);
      if (animate) { s.power.set(0); await fade(s.power, 1, 700, delay * 0.6); } else s.power.set(1);
    });
    await Promise.all(jobs);
  }
  function fade(p: Power, to: number, ms: number, delay: number) {
    if (STILL || REDUCED) { p.set(to); return Promise.resolve(); }
    const from = p.value;
    return new Promise<void>(res => setTimeout(() => {
      const t0 = performance.now();
      const step = () => { const k = Math.min(1, (performance.now() - t0) / ms); p.set(from + (to - from) * (k * k * (3 - 2 * k))); k < 1 ? requestAnimationFrame(step) : res(); };
      step();
    }, delay));
  }

  // the lift panel, the caption and the switch
  // ?floor=N picks a storey by its number (1 = the top); the visit starts at No. 1
  let cur = STOREYS - Math.max(1, Math.min(STOREYS, parseInt(QUERY.get('floor') ?? '1') || 1));
  function panel() {
    const list = sorted(kind, by);
    $('floors').innerHTML = [...tower.floors].reverse().map(f => {   // like a lift panel: the top floor (No. 1) first
      const t = titleAt(list, f.index), n = STOREYS - f.index;
      return `<button data-i="${f.index}" class="${f.index === cur ? 'on' : ''}${t ? '' : ' empty'}"><span class="n">${String(n).padStart(2, '0')}</span><span class="t">${t ? t.title : '—'}</span></button>`;
    }).join('');
    for (const b of document.querySelectorAll<HTMLButtonElement>('[data-kind]')) b.setAttribute('aria-pressed', String(b.dataset.kind === kind));
    for (const b of document.querySelectorAll<HTMLButtonElement>('[data-sort]')) b.setAttribute('aria-pressed', String(b.dataset.sort === by));
  }
  const url = () => history.replaceState(null, '', `?kind=${KIND_PATH[kind]}${by === 'rank' ? '' : `&sort=${by}`}${QUERY.has('ambient') ? `&ambient=${QUERY.get('ambient')}` : ''}`);
  function caption() {
    const t = slot[cur].title ?? titleAt(sorted(kind, by), cur), n = STOREYS - cur, cap = $('cap');
    cap.classList.add('out');
    setTimeout(() => {
      $('k').textContent = `${KIND_NAME[kind]} · Floor ${n}`;
      $('nm').textContent = t ? label(t) : 'To come';
      $('sc').textContent = t ? t.scene : 'A room still being built.';
      $('rt').innerHTML = t?.imdb.rating ? `IMDb <b>${t.imdb.rating.toFixed(1)}</b>` : '';
      const a = $<HTMLAnchorElement>('open');
      if (t) { a.href = `${import.meta.env.BASE_URL}${KIND_PATH[t.kind]}/${t.slug}/`; a.hidden = false; } else a.hidden = true;
      cap.classList.remove('out');
    }, STILL ? 0 : 280);
    for (const b of $('floors').querySelectorAll('button')) b.classList.toggle('on', +b.dataset.i! === cur);
  }
  function go(i: number) { const n = Math.max(0, Math.min(STOREYS - 1, i)); if (view === 0) setView(1); if (n === cur) return; cur = n; caption(); }
  // three distances: 0 the whole tower in its room, 1 a floor, 2 close to that floor. ?view=tower|floor|close;
  // ?floor=N starts at that floor.
  const VIEWS = ['tower', 'floor', 'close'], vq = QUERY.get('view') ?? (QUERY.has('floor') ? 'floor' : 'tower');
  let view = Math.max(0, VIEWS.indexOf(vq)), vk = view;
  const vb = $<HTMLButtonElement>('view'), hint = $('hint');
  function setView(v: number) {
    view = Math.max(0, Math.min(2, v));
    vb.textContent = ['Step in', 'Look closer', 'Whole tower'][view];
    hint.textContent = view ? 'Scroll to ride between floors' : 'Click the tower to step in';
  }
  vb.addEventListener('click', () => setView((view + 1) % 3)); setView(view);
  addEventListener('keydown', e => { if (e.key === 'Escape') setView(0); });
  $('floors').addEventListener('click', e => { const b = (e.target as HTMLElement).closest('button'); if (b) go(+b.dataset.i!); });
  for (const b of document.querySelectorAll<HTMLButtonElement>('[data-kind]')) b.addEventListener('click', async () => {
    const k = b.dataset.kind as Kind; if (k === kind) return; kind = k; panel(); caption(); url();
    await dress(sorted(kind, by), { animate: true }); caption();
  });
  for (const b of document.querySelectorAll<HTMLButtonElement>('[data-sort]')) b.addEventListener('click', async () => {
    const s = b.dataset.sort as Sort; if (s === by) return; by = s; panel(); caption(); url();
    await dress(sorted(kind, by), { animate: true }); caption();
  });
  addEventListener('keydown', e => { if (e.key === 'ArrowUp') go(cur + 1); if (e.key === 'ArrowDown') go(cur - 1); });
  let lock = 0;
  addEventListener('wheel', e => {
    if (Math.abs(e.deltaY) < 12 || performance.now() < lock) return; lock = performance.now() + 650;
    if (view === 0) setView(1); else go(cur + (e.deltaY < 0 ? 1 : -1));
  }, { passive: true });
  let sy: number | null = null;
  canvas.addEventListener('pointerdown', e => sy = e.clientY);
  addEventListener('pointerup', e => {
    if (sy === null) return;
    if (Math.abs(e.clientY - sy) > 40) go(cur + (e.clientY > sy ? 1 : -1)); else if (view === 0 && e.target === canvas) setView(1);
    sy = null;
  });
  let mx = 0; addEventListener('pointermove', e => { mx = e.clientX / innerWidth - 0.5; });

  await dress(sorted(kind, by), { animate: false });
  panel(); caption();

  let camY = tower.floors[cur].y0 + CASE.h / 2;
  const look = new THREE.Vector3();
  const P = [new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3()], K = [new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3()];
  const pick = (v: THREE.Vector3[], k: number, out: THREE.Vector3) => k <= 1 ? out.lerpVectors(v[0], v[1], k) : out.lerpVectors(v[1], v[2], k - 1);
  const mix = (v: [number, number, number], k: number) => k <= 1 ? v[0] + (v[1] - v[0]) * k : v[1] + (v[2] - v[1]) * (k - 1);
  startLoop(stage, { fov: p => p ? 46 : 30, aoRadius: 0.05, bloom: [0.2, 0.45, 1.15] }, (t, dt, post) => {
    for (const s of slot) s.room?.update(t, dt || 1e-4);
    const f = tower.floors[cur], tgt = f.y0 + CASE.h * 0.45, ease = STILL || REDUCED ? 1 : 1 - Math.exp(-dt * 2.4);
    camY += (tgt - camY) * ease; vk += (view - vk) * ease;
    const portrait = innerWidth < innerHeight;   // portrait: the tower sits left of the floor list
    // the whole tower from above its roofline, so every lit room is seen from above, like the case
    P[0].set((portrait ? 4.2 : 5.6) + mx * 0.3, portrait ? 7.4 : 6.9, portrait ? 6.6 : 5.4); K[0].set(portrait ? 0.4 : -0.2, height / 2 + 0.55, -0.3);
    P[1].set((portrait ? 0.9 : 1.7) + mx * 0.4, camY + (portrait ? 0.75 : 0.6), portrait ? 4.2 : 4.5); K[1].set(portrait ? 0.32 : -0.55, camY - (portrait ? 0.12 : 0.05), -0.3);
    P[2].set((portrait ? 0.55 : 0.95) + mx * 0.2, camY + (portrait ? 0.45 : 0.3), portrait ? 2.3 : 2.35); K[2].set(portrait ? 0.16 : -0.3, camY - 0.07, -0.3);
    pick(P, vk, camera.position); camera.lookAt(pick(K, vk, look));
    const fov = mix(portrait ? [66, 46, 46] : [50, 30, 30], vk);
    if (Math.abs(camera.fov - fov) > 0.01) { camera.fov = fov; camera.updateProjectionMatrix(); }
    post.focus.distance.value = camera.position.distanceTo(new THREE.Vector3(0, mix([height / 2, camY, camY], vk), -0.3));
    post.focus.range.value = mix([4.5, FLOOR.h * 1.35, 0.5], vk);
  });
  window.__ready = true;
  $('loading').classList.add('done');
}
