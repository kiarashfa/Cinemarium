// The Tower: one glass building standing in still water at dusk, ten storeys, one title per floor,
// No. 1 at the top. The switch re-dresses the whole building: each floor's lights go out, its room
// changes from series to film (or back), and the lights come on again, floor by floor.
import * as THREE from 'three/webgpu';
import { createStage, startLoop, STILL, REDUCED, QUERY } from '../stage';
import { dusk } from '../ambients';
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
  const amb = await dusk(scene, renderer); renderer.toneMappingExposure = amb.exposure;
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
    $('floors').innerHTML = tower.floors.map(f => {
      const t = titleAt(list, f.index), n = STOREYS - f.index;
      return `<button data-i="${f.index}" class="${f.index === cur ? 'on' : ''}${t ? '' : ' empty'}"><span class="n">${String(n).padStart(2, '0')}</span><span class="t">${t ? t.title : '—'}</span></button>`;
    }).join('');
    for (const b of document.querySelectorAll<HTMLButtonElement>('[data-kind]')) b.setAttribute('aria-pressed', String(b.dataset.kind === kind));
  }
  function caption() {
    const t = slot[cur].title ?? titleAt(sorted(kind, by), cur), n = STOREYS - cur, cap = $('cap');
    cap.classList.add('out');
    setTimeout(() => {
      $('k').textContent = `${KIND_NAME[kind]} · Floor ${n}`;
      $('nm').textContent = t ? label(t) : 'To come';
      $('sc').textContent = t ? t.scene : 'A room still being built.';
      const a = $<HTMLAnchorElement>('open');
      if (t) { a.href = `${import.meta.env.BASE_URL}${KIND_PATH[t.kind]}/${t.slug}/`; a.hidden = false; } else a.hidden = true;
      cap.classList.remove('out');
    }, STILL ? 0 : 280);
    for (const b of $('floors').querySelectorAll('button')) b.classList.toggle('on', +b.dataset.i! === cur);
  }
  function go(i: number) { const n = Math.max(0, Math.min(STOREYS - 1, i)); if (n === cur) return; cur = n; caption(); }
  $('floors').addEventListener('click', e => { const b = (e.target as HTMLElement).closest('button'); if (b) go(+b.dataset.i!); });
  for (const b of document.querySelectorAll<HTMLButtonElement>('[data-kind]')) b.addEventListener('click', async () => {
    const k = b.dataset.kind as Kind; if (k === kind) return; kind = k; panel(); caption();
    history.replaceState(null, '', `?kind=${KIND_PATH[kind]}`);
    await dress(sorted(kind, by), { animate: true }); caption();
  });
  addEventListener('keydown', e => { if (e.key === 'ArrowUp') go(cur + 1); if (e.key === 'ArrowDown') go(cur - 1); });
  let lock = 0;
  addEventListener('wheel', e => { if (Math.abs(e.deltaY) < 12 || performance.now() < lock) return; lock = performance.now() + 650; go(cur + (e.deltaY < 0 ? 1 : -1)); }, { passive: true });
  let sy: number | null = null;
  canvas.addEventListener('pointerdown', e => sy = e.clientY);
  addEventListener('pointerup', e => { if (sy !== null && Math.abs(e.clientY - sy) > 40) go(cur + (e.clientY > sy ? 1 : -1)); sy = null; });
  let mx = 0; addEventListener('pointermove', e => { mx = e.clientX / innerWidth - 0.5; });

  await dress(sorted(kind, by), { animate: false });
  panel(); caption();

  let camY = tower.floors[cur].y0 + CASE.h / 2;
  const look = new THREE.Vector3();
  startLoop(stage, { fov: p => p ? 46 : 30, aoRadius: 0.05, bloom: [0.2, 0.45, 1.15] }, (t, dt, post) => {
    for (const s of slot) s.room?.update(t, dt || 1e-4);
    const f = tower.floors[cur], tgt = f.y0 + CASE.h * 0.45;
    camY += (tgt - camY) * (STILL || REDUCED ? 1 : 1 - Math.exp(-dt * 2.6));
    const portrait = innerWidth < innerHeight;
    camera.position.set((portrait ? 0.9 : 1.7) + mx * 0.4, camY + (portrait ? 0.75 : 0.6), portrait ? 4.2 : 4.5);
    look.set(portrait ? 0.32 : -0.55, camY - (portrait ? 0.12 : 0.05), -0.3); camera.lookAt(look);   // portrait: the tower sits left of the floor list
    post.focus.distance.value = camera.position.distanceTo(new THREE.Vector3(0, camY, -0.3));
    post.focus.range.value = FLOOR.h * 0.9;
  });
  window.__ready = true;
  $('loading').classList.add('done');
}
