// Downloads the source assets a room needs into pipeline/cache/ (git-ignored) and records where each
// came from and under which licence in pipeline/cache/MANIFEST.json. Re-running skips what is there.
// Usage: node pipeline/fetch.mjs severance
import { mkdirSync, existsSync, writeFileSync, readFileSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const CACHE = fileURLToPath(new URL('./cache/', import.meta.url));
const RB = 'https://raw.githubusercontent.com/microsoft/Microsoft-Rocketbox/master/Assets';
const manifestPath = join(CACHE, 'MANIFEST.json');
const manifest = existsSync(manifestPath) ? JSON.parse(readFileSync(manifestPath, 'utf8')) : {};

async function get(url, out) {
  if (existsSync(out) && statSync(out).size > 0) return false;
  mkdirSync(dirname(out), { recursive: true });
  const r = await fetch(url); if (!r.ok) throw new Error(`${r.status} ${url}`);
  writeFileSync(out, Buffer.from(await r.arrayBuffer())); return true;
}
const note = (key, source, licence, files) => { manifest[key] = { source, licence, files, fetched: new Date().toISOString().slice(0, 10) }; };

// ---------- Microsoft Rocketbox (MIT) ----------
async function avatar(path) {
  const name = path.split('/').pop(), tree = JSON.parse(readFileSync(join(CACHE, 'rocketbox', 'tree.json'), 'utf8')).tree;
  const files = tree.filter(e => e.type === 'blob' && e.path.startsWith(`Assets/Avatars/${path}/`) && !/_facial\.fbx$|\.png$|\.mat$|\.shader$|\.meta$/i.test(e.path));
  for (const f of files) await get(`${RB}/${f.path.slice(7)}`, join(CACHE, 'rocketbox', 'avatars', name, f.path.split('/').slice(-2).join('/')));
  note(`rocketbox/${name}`, `https://github.com/microsoft/Microsoft-Rocketbox/tree/master/Assets/Avatars/${path}`, 'MIT', files.length);
}
async function clip(folder, name) {
  await get(`${RB}/Animations/${folder}/${encodeURIComponent(name)}.max.fbx`, join(CACHE, 'rocketbox', 'animations', `${name.replace(/ /g, '_')}.fbx`));
  note(`rocketbox-anim/${name}`, `https://github.com/microsoft/Microsoft-Rocketbox/tree/master/Assets/Animations/${folder}`, 'MIT', 1);
}

// ---------- Poly Haven (CC0) ----------
async function polyhaven(id, res = '1k', kind = 'gltf') {
  const files = await (await fetch(`https://api.polyhaven.com/files/${id}`)).json(), out = join(CACHE, 'polyhaven', id);
  if (kind === 'gltf') {
    const g = files.gltf[res].gltf; await get(g.url, join(out, g.url.split('/').pop()));
    for (const [rel, f] of Object.entries(g.include ?? {})) await get(f.url, join(out, rel));
  } else {
    for (const map of ['Diffuse', 'nor_gl', 'Rough', 'AO', 'Displacement', 'arm']) {
      const f = files[map]?.[res]?.png ?? files[map]?.[res]?.jpg; if (f) await get(f.url, join(out, `${map}.${f.url.split('.').pop()}`));
    }
  }
  note(`polyhaven/${id}`, `https://polyhaven.com/a/${id}`, 'CC0', kind);
}

// ---------- ambientCG (CC0) ----------
async function ambientcg(id, res = '2K-JPG') {
  const out = join(CACHE, 'ambientcg', id), zip = join(out, `${id}_${res}.zip`);
  if (await get(`https://ambientcg.com/get?file=${id}_${res}.zip`, zip)) execFileSync(process.platform === 'win32' ? 'C:/Windows/System32/tar.exe' : 'tar', ['-xf', zip, '-C', out]);
  note(`ambientcg/${id}`, `https://ambientcg.com/view?id=${id}`, 'CC0', res);
}

const ROOMS = {
  async severance() {
    mkdirSync(join(CACHE, 'rocketbox'), { recursive: true });
    if (!existsSync(join(CACHE, 'rocketbox', 'tree.json'))) await get('https://api.github.com/repos/microsoft/Microsoft-Rocketbox/git/trees/master?recursive=1', join(CACHE, 'rocketbox', 'tree.json'));
    for (const a of ['Professions/Business_Male_01', 'Professions/Business_Male_05', 'Adults/Male_Adult_12', 'Adults/Female_Adult_15', 'Adults/Male_Adult_03']) await avatar(a);
    const S = 'all_animations_max_motextr_static', XY = 'all_animations_max_motextr_xy';
    // seated at a desk: one breathing base for the work loop, and idles to break it up
    const seated = ['breathe_01', 'idle_neutral_01', 'idle_neutral_02', 'idle_look_around', 'idle_scratch_head', 'idle_touch_face', 'idle_roll_head',
      'idle_yawn', 'idle_relaxed_01', 'idle_dust', 'idle_waiting_01', 'gestic_thoughtful', 'gestic_shrug_01'];
    for (const c of seated) await clip(S, `m_sit_table_${c}`);
    for (const c of [...seated.filter(c => c !== 'idle_dust'), 'idle_touch_hair', 'idle_stretch arms']) await clip(S, `f_sit_table_${c}`);
    // standing, for the supervisor on his rounds
    for (const c of ['m_idle_neutral_01', 'm_idle_neutral_02', 'm_idle_breathe_01', 'm_idle_look_around_01', 'm_idle_waiting_01', 'm_gestic_listen_neutral_01', 'm_gestic_talk_neutral_01']) await clip(S, c);
    for (const c of ['m_walk_cool_01', 'm_walk_neutral_02']) await clip(XY, c);
    for (const t of ['rough_linen', 'poly_wool_herringbone', 'jersey_melange', 'white_plaster_02', 'ceiling_interior']) await polyhaven(t, '2k', 'tex');
    for (const m of ['wall_clock', 'office_notepads', 'stationery_supplies', 'vintage_stapler', 'binder_notebook', 'fire_alarm']) await polyhaven(m, '1k', 'gltf');
    for (const t of ['Carpet012', 'Carpet013']) await ambientcg(t);
  },
};

const room = process.argv[2];
if (!ROOMS[room]) { console.error('usage: node pipeline/fetch.mjs <' + Object.keys(ROOMS).join('|') + '>'); process.exit(1); }
await ROOMS[room]();
writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
console.log('ok', Object.keys(manifest).length, 'entries in', manifestPath);
