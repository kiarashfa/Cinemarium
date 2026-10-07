// The club: one Rotunda, built once, and four places in it. Home stands just inside the entrance and takes in the
// whole room; the case holds one title's room (every title has its own address); the board stands across the room;
// About is at the exit. Moving between places is a walk round the case, and the address follows without a reload.
// A room is loaded only when its case is entered: changing title sinks the room into the plinth and lifts the next.
import * as THREE from 'three/webgpu';
import { createStage, startLoop, STILL, REDUCED, QUERY } from './stage';
import { buildRotunda, BOARD, DOOR, RADIUS } from './rotunda';
import { buildCase } from './case';
import { CASE, STAGE_LIFT } from './module';
import { loadRoom, mount, release, type Room } from './rooms';
import { sorted, honourable, label, subtitle, KIND_NAME, type Kind, type Sort, type Title } from '../data/titles';
import { parse, path, head, titleOf, type Route } from '../data/routes';

const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const $$ = <T extends HTMLElement = HTMLElement>(sel: string) => [...document.querySelectorAll<T>(sel)];
const SORTS: Sort[] = ['rank', 'year', 'imdb'];
const wrap = (a: number) => Math.atan2(Math.sin(a), Math.cos(a));
const HOME = 0.62;   // home's angle round the room: off the entrance, in the gap between two counters

/** Where the camera stands (angle round the centre, distance, height), what it looks at, its lens and focus. */
interface Shot { th: number; R: number; y: number; look: THREE.Vector3; fov: number; focus: THREE.Vector3; range: number }
/** The same place as the camera holds it: its heading (yaw, pitch) instead of a point to look at. */
interface Pose { th: number; R: number; y: number; yaw: number; pitch: number; fov: number; focus: THREE.Vector3; range: number }
const shotOf = (): Shot => ({ th: 0, R: 0, y: 0, look: new THREE.Vector3(), fov: 46, focus: new THREE.Vector3(), range: 1 });
/** The direction to the left of a camera looking outward along angle a (toward the centre: pass a + π). */
const leftOf = (a: number, out: THREE.Vector3, k: number) => out.set(Math.cos(a) * k, 0, -Math.sin(a) * k);
function poseOf(s: Shot, out?: Pose): Pose {
  const x = Math.sin(s.th) * s.R, z = Math.cos(s.th) * s.R, dx = s.look.x - x, dy = s.look.y - s.y, dz = s.look.z - z;
  const p = out ?? { th: 0, R: 0, y: 0, yaw: 0, pitch: 0, fov: 46, focus: new THREE.Vector3(), range: 1 };
  Object.assign(p, { th: s.th, R: s.R, y: s.y, yaw: Math.atan2(dx, dz), pitch: Math.atan2(dy, Math.hypot(dx, dz)), fov: s.fov, range: s.range });
  p.focus.copy(s.focus); return p;
}

export async function startClub(canvas: HTMLCanvasElement) {
  const stage = await createStage(canvas, { fov: 46, far: 80 });
  const { renderer, scene, camera } = stage;
  // the room first: its reflections are captured from the case's place before the case stands there
  const club = buildRotunda(scene, renderer, { centre: new THREE.Vector3(0, 1.25, 0), height: 1.6, width: CASE.w + 0.14 },
    { mirror: stage.rung.mirror && !QUERY.has('nomirror') });
  renderer.toneMappingExposure = 0.95;
  const vit = buildCase({ label: 'Cinemarium' });
  scene.add(vit.group);
  if (QUERY.has('noglass')) vit.group.traverse(o => { const m = o as THREE.Mesh; if (m.isMesh && ((m.material as THREE.MeshPhysicalMaterial).transmission > 0 || (m.material as THREE.Material).transparent)) m.visible = false; });
  const middle = new THREE.Vector3(0, vit.top - CASE.h / 2, 0);

  // ---------- state ----------
  let route: Route = parse(location.pathname);
  let kind: Kind = QUERY.get('kind') === 'films' ? 'film' : 'series';
  let by: Sort = SORTS.includes(QUERY.get('sort') as Sort) ? QUERY.get('sort') as Sort : 'rank';
  let zoom = QUERY.has('zoom') ? 1 : 0;                      // in the case: 0 at the case, 1 close
  let wanted: Title | null = null, cur: Title | null = null, shown: Room | null = null, shownId = '';
  let phase: 'idle' | 'sinking' | 'loading' | 'rising' = 'idle', lift = -1;
  let loop: ReturnType<typeof startLoop> | null = null;

  // ---------- the case's room ----------
  function want(t: Title) {
    wanted = t;
    if (phase === 'idle' && t !== cur) shown ? phase = 'sinking' : bring();
  }
  function bring() {
    const t = cur = wanted!; vit.setLabel(t.title);
    if (!t.room) {                     // not built yet: the case stays empty
      for (const ch of [...vit.stage.children]) vit.stage.remove(ch);
      shown = null; shownId = ''; phase = 'idle'; hint(); return;
    }
    phase = 'loading'; hint();
    const id = t.room;
    loadRoom(id).then(r => {
      if (r !== shown) { mount(vit.stage, r); release([id, shownId]); shown = r; shownId = id; lift = -1; }
      phase = 'rising'; loop?.settle(); hint();
    }, err => { console.error(err); phase = 'idle'; hint(); });
  }
  function liftStep(dt: number) {
    const step = STILL || REDUCED ? 1 : dt / 0.9;
    if (phase === 'sinking') { lift = Math.max(-1, lift - step); if (lift === -1) bring(); }
    else if (phase === 'rising') { lift = Math.min(0, lift + step); if (lift === 0) { phase = 'idle'; if (wanted && wanted !== cur) phase = 'sinking'; } }
    if (shown) shown.group.position.y = STAGE_LIFT - (1 - Math.cos(lift * Math.PI / 2)) * 0.75;
  }

  // ---------- panels ----------
  const listOf = () => sorted(kind, by);
  /** The title "Step up to the case" leads to: the one already in the case if it is of this list, else its best
   * ranked with a room (or its first, while none is built). */
  const caseTitle = () => (wanted?.kind === kind ? wanted : listOf().filter(x => x.room).sort((a, b) => a.rank - b.rank)[0] ?? listOf()[0]) ?? null;
  function controls() {
    for (const b of $$('[data-kind]')) b.setAttribute('aria-pressed', String(b.dataset.kind === kind));
    for (const b of $$('[data-sort]')) b.setAttribute('aria-pressed', String(b.dataset.sort === by));
    const list = listOf(), t = caseTitle();
    $('pills').innerHTML = list.map(x => `<button data-slug="${x.slug}" class="${x === wanted ? 'on' : ''}">${x.title}</button>`).join('');
    $('bk').textContent = KIND_NAME[kind];
    $('list').innerHTML = Array.from({ length: 10 }, (_, i) => list[i]).map((x, i) => {
      const n = `<span class="n">${String(i + 1).padStart(2, '0')}</span>`;
      return x ? `<li class="${x.room ? '' : 'unbuilt'}">${n}<a href="${path({ view: 'case', slug: x.slug })}">${x.title} <em>${x.year}</em></a></li>` : `<li class="empty">${n}<span>To come</span></li>`;
    }).join('');
    const also = honourable(kind); $('also').textContent = also.length ? `Honourable mentions: ${also.map(x => x.title).join(' · ')}` : '';
    const enter = $<HTMLAnchorElement>('enter');
    if (t) { enter.href = path({ view: 'case', slug: t.slug }); enter.hidden = false; } else enter.hidden = true;
    $<HTMLAnchorElement>('to-board').href = path({ view: 'board' }) + query('board');
  }
  function caption() {
    const t = wanted; if (!t) return;
    const cap = $('cap'), list = listOf(); cap.classList.add('out');
    setTimeout(() => {
      $('k').textContent = `${KIND_NAME[t.kind]} · ${list.indexOf(t) + 1} of ${list.length}`;
      $('nm').textContent = label(t); $('sc').textContent = subtitle(t);
      $('rt').innerHTML = t.imdb.rating ? `IMDb <b>${t.imdb.rating.toFixed(1)}</b>` : '';
      cap.classList.remove('out');
    }, STILL ? 0 : 280);
    for (const b of $$('#pills button')) b.classList.toggle('on', b.dataset.slug === t.slug);
  }
  function hint() {
    const v = route.view;
    $('hint').textContent = v === 'case' ? (phase === 'loading' ? 'Bringing up the room…' : cur && !cur.room ? 'This room is being built' : zoom ? 'Drag to walk around · scroll back to step away' : 'Drag to walk around the case · scroll to lean in')
      : v === 'board' ? 'Choose a title to open its case' : 'Click the case to step up to it';
    $('zoom').textContent = zoom ? 'Step back' : 'Look closer';
  }

  // ---------- the router ----------
  /** The query an address keeps: the switches in use (still, debug, q…) plus the list and order where they matter. */
  function query(view: Route['view']) {
    const q = new URLSearchParams(location.search);
    for (const k of ['kind', 'sort', 'zoom', 'th']) q.delete(k);
    if (kind === 'film' && view !== 'case') q.set('kind', 'films');
    if (by !== 'rank' && view !== 'about') q.set('sort', by);
    const s = q.toString(); return s ? `?${s}` : '';
  }
  function go(r: Route, push = true) {
    if (r.view === 'case') {
      const t = titleOf(r.slug); if (!t) return go({ view: 'home' }, push);
      if (route.view !== 'case') { zoom = 0; orbit = 0.55; }
      kind = t.kind; want(t);
    }
    const moving = r.view !== route.view;
    route = r; document.body.dataset.view = r.view;
    if (moving) walk();
    const h = head(r); document.title = h.title; document.querySelector('meta[name=description]')?.setAttribute('content', h.description);
    for (const a of $$('[data-nav]')) a.dataset.nav === r.view ? a.setAttribute('aria-current', 'page') : a.removeAttribute('aria-current');
    const url = path(r) + query(r.view);
    if (push && url !== location.pathname + location.search) history.pushState(null, '', url); else history.replaceState(null, '', url);
    controls(); caption(); hint();
  }
  addEventListener('popstate', () => {
    const q = new URLSearchParams(location.search);
    kind = q.get('kind') === 'films' ? 'film' : 'series'; by = SORTS.includes(q.get('sort') as Sort) ? q.get('sort') as Sort : 'rank';
    go(parse(location.pathname), false);
  });
  // links inside the club move through it rather than reload it
  document.addEventListener('click', e => {
    const a = (e.target as HTMLElement).closest('a');
    if (!a || a.target || e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0 || a.origin !== location.origin) return;
    if (!a.pathname.startsWith(import.meta.env.BASE_URL)) return;
    e.preventDefault(); go(parse(a.pathname));
  });
  // the lists and their order
  for (const b of $$('[data-kind]')) b.addEventListener('click', () => {
    const k = b.dataset.kind as Kind; if (k === kind) return; kind = k;
    if (route.view === 'case') { const t = listOf()[0]; if (t) return go({ view: 'case', slug: t.slug }); }
    controls(); history.replaceState(null, '', path(route) + query(route.view));
  });
  for (const b of $$('[data-sort]')) b.addEventListener('click', () => {
    const s = b.dataset.sort as Sort; if (s === by) return; by = s;
    controls(); caption(); history.replaceState(null, '', path(route) + query(route.view));
  });
  const step = (d: number) => { const list = listOf(), i = wanted ? list.indexOf(wanted) : -1; if (list.length) go({ view: 'case', slug: list[(i + d + list.length) % list.length].slug }); };
  $('pills').addEventListener('click', e => { const b = (e.target as HTMLElement).closest('button'); if (b) go({ view: 'case', slug: b.dataset.slug! }); });
  $('prev').addEventListener('click', () => step(-1)); $('next').addEventListener('click', () => step(1));
  // stepping up to the case starts loading its room while the pointer is still on the way
  for (const ev of ['pointerenter', 'focus']) $('enter').addEventListener(ev, () => { const t = caseTitle(); if (t?.room) loadRoom(t.room).catch(() => {}); });

  // ---------- moving about: click, wheel, keys, drag ----------
  const enterCase = () => { const t = caseTitle(); if (t) go({ view: 'case', slug: t.slug }); };
  const setZoom = (z: number) => {
    if (route.view !== 'case') return;
    if (z < 0) return go({ view: 'home' });
    const z1 = Math.min(1, z); if (z1 === zoom) return;
    zoom = z1; walk(); hint();
  };
  $('zoom').addEventListener('click', () => setZoom(zoom ? 0 : 1));
  let wheelLock = 0;
  addEventListener('wheel', e => {
    if (Math.abs(e.deltaY) < 8 || performance.now() < wheelLock || (e.target as HTMLElement).closest('.list,.pills')) return;
    wheelLock = performance.now() + 650;
    const inward = e.deltaY < 0;
    if (route.view === 'home') { if (inward) enterCase(); }
    else if (route.view === 'case') setZoom(zoom + (inward ? 1 : -1));
    else if (!inward) go({ view: 'home' });
  }, { passive: true });
  addEventListener('keydown', e => {
    if (e.key === 'Escape' && route.view !== 'home') go({ view: 'home' });
    if (route.view !== 'case') return;
    if (e.key === 'ArrowRight') step(1); if (e.key === 'ArrowLeft') step(-1);
    if (e.key === '+' || e.key === '=') setZoom(zoom + 1); if (e.key === '-') setZoom(zoom - 1);
  });
  // drag to walk round the case; a click (no drag) at home steps up to it; idle, the walk drifts slowly
  let orbit = +(QUERY.get('th') ?? 0.55), orbitV = 0, drag: number | null = null, moved = 0, idle = 0, mx = 0, sway = 0;
  canvas.addEventListener('pointerdown', e => { drag = e.clientX; moved = 0; idle = 0; canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener('pointermove', e => {
    mx = e.clientX / innerWidth - 0.5;
    if (drag === null) return; const d = e.clientX - drag; moved += Math.abs(d); drag = e.clientX;
    if (route.view === 'case') { orbitV = d * -0.006; orbit += orbitV; }
  });
  canvas.addEventListener('pointerup', () => { if (drag !== null && moved < 6 && route.view === 'home') enterCase(); drag = null; });

  // ---------- the camera's places, and the walks between them ----------
  const target = shotOf(), tmp = new THREE.Vector3();
  function aim(out: Shot, portrait: boolean) {
    const v = route.view, P = portrait;
    if (v === 'case') {
      // at the case, or close enough to read the room as a miniature; the case sits right of the caption
      const z = zoom, L = (a: number, b: number) => z ? b : a, off = P ? 0 : L(0.45, 0.12);
      out.th = orbit; out.R = P ? L(5.7, 2.9) : L(3.55, 1.7); out.y = P ? L(3.1, 2.0) : L(2.3, 1.62); out.fov = P ? 46 : 32;
      out.look.set(0, P ? L(0.95, 1.06) : L(1.08, 1.06), 0).add(leftOf(orbit + Math.PI, tmp, off));
      out.focus.copy(middle); out.range = L(1.15, 0.75);
    } else if (v === 'board' || v === 'about') {
      // standing just inside a counter, eyes over it, facing the wall: the board across from the entrance, or the
      // doors; the counter stays below the frame (in portrait the camera looks lower: the wall sits above the panel)
      const a = v === 'board' ? BOARD : DOOR, about = v === 'about', d = RADIUS + (about ? 0.9 : 0);
      out.th = a + (about ? 0.05 : 0); out.R = 4.0; out.y = 2.0; out.fov = P ? 64 : 50;
      out.focus.set(Math.sin(a) * d, about ? 1.6 : 2.4, Math.cos(a) * d); out.range = about ? 1.6 : 2.4;
      out.look.copy(out.focus).add(leftOf(a, tmp, P ? 0 : 1.9)); out.look.y = P ? (about ? 0.7 : 1.2) : about ? 1.75 : 2.4;
    } else {
      // home: a few steps in from the entrance, between two counters: the whole room, the case right of the welcome
      out.th = HOME + sway * 0.05; out.R = P ? 7.2 : 6.6; out.y = P ? 3.6 : 2.7; out.fov = P ? 64 : 54;
      out.look.set(0, P ? 1.0 : 1.9, 0).add(leftOf(out.th + Math.PI, tmp, P ? 0 : 1.0));
      out.focus.copy(middle); out.range = 2.6;
    }
    return out;
  }
  // a walk blends the pose it starts from into the place it goes to (which may move meanwhile: a drag, the sway);
  // once there, the camera holds the place exactly
  const portrait = () => innerWidth < innerHeight;
  const cam = poseOf(aim(target, portrait())), from = poseOf(target), to = poseOf(target);
  let walked = 1, walkFor = 1.6;
  function walk(seconds?: number) {
    Object.assign(from, cam, { focus: from.focus.copy(cam.focus) });
    poseOf(aim(target, portrait()), to);
    walked = 0; walkFor = seconds ?? Math.min(2.8, 1.2 + 0.4 * Math.abs(wrap(to.th - from.th)) + 0.08 * Math.abs(to.R - from.R));
  }
  if (route.view === 'home' && !STILL && !REDUCED) {   // the visit begins in the doorway and walks in
    Object.assign(cam, { th: DOOR, R: RADIUS + 1.0, y: 1.7, yaw: Math.PI, pitch: -0.02, fov: 54 }); walk(2.8);
  }

  go(route, false);
  loop = startLoop(stage, { fov: p => p ? 66 : 50, aoRadius: 0.05, bloom: [0.14, 0.4, 1.05], onRung: r => club.setMirror(r.mirror && !QUERY.has('nomirror')) }, (t, dt, post) => {
    idle += dt;
    if (drag === null) { orbitV *= 0.92; orbit += orbitV + (route.view === 'case' && idle > 4 && !REDUCED && !STILL ? dt * 0.05 : 0); }
    sway += (mx - sway) * Math.min(1, dt * 2);
    liftStep(dt);
    shown?.update(t, dt || 1e-4);
    poseOf(aim(target, portrait()), to);
    walked = STILL || REDUCED ? 1 : Math.min(1, walked + dt / walkFor);
    const e = walked * walked * (3 - 2 * walked), mix = (a: number, b: number) => a + (b - a) * e;
    cam.th = from.th + wrap(to.th - from.th) * e; cam.yaw = from.yaw + wrap(to.yaw - from.yaw) * e;
    cam.R = mix(from.R, to.R); cam.y = mix(from.y, to.y); cam.pitch = mix(from.pitch, to.pitch); cam.fov = mix(from.fov, to.fov); cam.range = mix(from.range, to.range);
    cam.focus.lerpVectors(from.focus, to.focus, e);
    camera.position.set(Math.sin(cam.th) * cam.R, cam.y, Math.cos(cam.th) * cam.R);
    tmp.set(Math.sin(cam.yaw) * Math.cos(cam.pitch), Math.sin(cam.pitch), Math.cos(cam.yaw) * Math.cos(cam.pitch)).add(camera.position); camera.lookAt(tmp);
    if (Math.abs(camera.fov - cam.fov) > 0.01) { camera.fov = cam.fov; camera.updateProjectionMatrix(); }
    post.focus.distance.value = camera.position.distanceTo(cam.focus); post.focus.range.value = cam.range;
    if (!window.__ready && phase === 'idle' && walked === 1 && (route.view !== 'case' || shown)) window.__ready = true;
  });
  $('loading').classList.add('done');
}
