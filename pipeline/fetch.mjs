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
      const src = map === 'Diffuse' && !files.Diffuse ? files.coll1 : files[map];   // some textures name their colour map coll1
      const f = src?.[res]?.png ?? src?.[res]?.jpg; if (f) await get(f.url, join(out, `${map}.${f.url.split('.').pop()}`));
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
  async 'the-matrix'() {
    // Morpheus (Male_Adult_12, cached for Severance), Neo, Trinity
    for (const a of ['Adults/Male_Adult_12', 'Professions/Business_Male_02', 'Adults/Female_Adult_04']) await avatar(a);
    const S = 'all_animations_max_motextr_static';
    // in the wingback chairs: a breathing base and idles; standing talk, its arms layered over the seated base
    for (const c of ['breathe_01', 'idle_neutral_01', 'idle_neutral_02', 'idle_relaxed_01', 'gestic_thoughtful', 'gestic_shrug_01', 'idle_touch_face',
      'idle_scratch_head', 'idle_look_around', 'idle_nervous_01', 'idle_waiting_01', 'idle_roll_head']) await clip(S, `m_sit_chair_${c}`);
    for (const c of ['neutral_01', 'neutral_02', 'neutral_03', 'relaxed_01', 'relaxed_02', 'cool']) await clip(S, `m_gestic_talk_${c}`);
    // Trinity, standing by the window
    for (const c of ['f_idle_breathe_01', 'f_idle_neutral_01', 'f_idle_neutral_02', 'f_idle_neutral_03', 'f_idle_look_around_01', 'f_idle_move_01',
      'f_idle_waiting_01', 'f_idle_roll_head_01', 'f_gestic_listen_self-assured_01', 'f_gestic_listen_neutral_01']) await clip(S, c);
    for (const t of ['decrepit_wallpaper', 'damaged_plaster', 'leather_red_03', 'old_wood_floor', 'floral_jacquard', 'white_plaster_02',
      'ceiling_interior']) await polyhaven(t, '2k', 'tex');
    for (const m of ['mantel_clock_01', 'ornate_mirror_01']) await polyhaven(m, '1k', 'gltf');
  },
  async lost() {
    // Desmond, Jack, Locke, Ben, Kate
    for (const a of ['Professions/Sports_Male_03', 'Adults/Male_Adult_08', 'Adults/Male_Adult_14', 'Adults/Male_Adult_02', 'Adults/Female_Adult_07']) await avatar(a);
    const S = 'all_animations_max_motextr_static';
    // Desmond at the keyboard: the seated table set (cached for Severance)
    for (const c of ['breathe_01', 'idle_neutral_01', 'idle_look_around', 'idle_scratch_head', 'idle_touch_face', 'idle_roll_head', 'idle_waiting_01',
      'gestic_thoughtful', 'idle_touch_hair']) await clip(S, `m_sit_table_${c}`);
    // Jack and Locke standing behind him
    for (const c of ['m_idle_breathe_01', 'm_idle_breathe_02', 'm_idle_breathe_03', 'm_idle_neutral_01', 'm_idle_neutral_02', 'm_idle_neutral_03',
      'm_idle_look_around_01', 'm_idle_waiting_01', 'm_gestic_listen_neutral_01', 'm_gestic_talk_neutral_01', 'm_idle_stretch_arms_01']) await clip(S, c);
    // Ben and Kate in the booth: seated bases, coffee, talk
    for (const c of ['m_drink_drinking', 'm_drink_idle', 'm_gestic_talk_relaxed_01', 'm_gestic_talk_relaxed_02']) await clip(S, c);
    for (const c of ['f_drink_drinking', 'f_drink_idle', 'f_gestic_talk_neutral_01', 'f_gestic_talk_relaxed_01', 'f_gestic_talk_relaxed_02']) await clip(S, c);
    for (const c of ['breathe_01', 'idle_neutral_01', 'idle_touch_face', 'idle_touch_hair', 'idle_look_around', 'gestic_thoughtful']) await clip(S, `f_sit_table_${c}`);
    for (const t of ['worn_tile_floor', 'brushed_concrete', 'concrete_wall_008', 'leather_red_02', 'wood_table_worn', 'smooth_concrete_floor']) await polyhaven(t, '2k', 'tex');
    await polyhaven('desk_lamp_arm_01', '1k', 'gltf');
  },
  async seinfeld() {
    // Jerry (Male_Adult_08, cached for LOST), George, Kramer, Elaine
    for (const a of ['Adults/Male_Adult_08', 'Adults/Male_Adult_13', 'Adults/Male_Adult_06', 'Professions/Business_Female_03']) await avatar(a);
    const S = 'all_animations_max_motextr_static';
    // Jerry mid-room, George behind the counter, Kramer in the doorway: standing idles, talk and listen
    for (const c of ['m_idle_breathe_01', 'm_idle_breathe_02', 'm_idle_neutral_01', 'm_idle_neutral_02', 'm_idle_look_around_01', 'm_gestic_listen_neutral_01',
      'm_gestic_talk_neutral_01', 'm_gestic_talk_neutral_02', 'm_gestic_talk_relaxed_01', 'm_gestic_shrug_01', 'm_gestic_shrug_02', 'm_gestic_talk_nervous_01',
      'm_gestic_talk_excited_01', 'm_gestic_listen_excited_01', 'm_idle_shake_arms_01', 'm_gestic_laugh_loud', 'm_gestic_laugh_low', 'm_idle_nervous_01',
      'm_gestic_listen_accept_01', 'm_gestic_listen_deny_01', 'm_idle_neutral_04']) await clip(S, c);
    // Elaine perched on the couch's arm: the seated-chair set, and standing talk to layer over it
    for (const c of ['breathe_01', 'idle_neutral_01', 'gestic_shrug_01', 'idle_touch_hair', 'gestic_thoughtful', 'idle_look_around', 'idle_waiting_01']) await clip(S, `f_sit_chair_${c}`);
    for (const c of ['f_gestic_talk_excited_01', 'f_gestic_talk_neutral_01', 'f_gestic_listen_neutral_01', 'f_gestic_laugh_low', 'f_gestic_talk_self-assured_01']) await clip(S, c);
    for (const t of ['laminate_floor_02', 'cotton_jersey', 'painted_plaster_wall', 'white_plaster_02']) await polyhaven(t, '2k', 'tex');
    for (const m of ['bananas', 'food_apple_01', 'food_pears_asian_01', 'wooden_cutting_board', 'potted_plant_02', 'desk_lamp_arm_01', 'mantel_clock_01']) await polyhaven(m, '1k', 'gltf');
  },
  async 'the-sopranos'() {
    // Tony (Male_Adult_14, cached for LOST), Melfi
    for (const a of ['Adults/Male_Adult_14', 'Professions/Business_Female_02']) await avatar(a);
    const S = 'all_animations_max_motextr_static', XY = 'all_animations_max_motextr_xy', XYZ = 'all_animations_max_motextr_xyz';
    // in the two armchairs: breathing bases, idles, talk to layer over them
    for (const c of ['breathe_01', 'idle_neutral_01', 'idle_relaxed_01', 'gestic_thoughtful', 'gestic_shrug_01', 'idle_touch_face', 'idle_scratch_head',
      'idle_look_around', 'idle_nervous_01', 'idle_waiting_01']) await clip(S, `m_sit_chair_${c}`);
    for (const c of ['breathe_01', 'idle_neutral_01', 'idle_neutral_02', 'gestic_thoughtful', 'idle_touch_hair', 'idle_touch_face', 'idle_look_around',
      'idle_relaxed_01']) await clip(S, `f_sit_chair_${c}`);
    for (const c of ['m_gestic_talk_relaxed_01', 'm_gestic_talk_neutral_01', 'm_gestic_talk_nervous_01', 'm_gestic_talk_excited_01', 'm_idle_angry_01',
      'm_idle_angry_02', 'm_idle_breathe_01', 'm_idle_look_around_01', 'f_gestic_talk_neutral_01', 'f_gestic_listen_neutral_01']) await clip(S, c);
    // the walk-out: up from the chair, the outburst, out of the door and back, down into the chair again
    for (const c of ['m_sit_stand_up_chair_01', 'm_sit_down_chair_01', 'm_gestic_talk_angry_01', 'm_gestic_talk_angry_02']) await clip(XYZ, c);
    for (const c of ['m_walk_fast_01', 'm_walk_neutral_02', 'm_walk_slow_01']) await clip(XY, c);
    for (const t of ['sapele_veneer', 'rosewood_veneer1', 'velour_velvet', 'brown_leather', 'waffle_pique_cotton', 'poly_wool_herringbone',
      'rough_linen', 'white_plaster_02']) await polyhaven(t, '2k', 'tex');
    for (const m of ['hanging_picture_frame_01', 'desk_lamp_arm_01', 'office_notepads', 'binder_notebook']) await polyhaven(m, '1k', 'gltf');
    for (const t of ['Carpet012', 'Carpet013']) await ambientcg(t);
  },
};

const room = process.argv[2];
if (!ROOMS[room]) { console.error('usage: node pipeline/fetch.mjs <' + Object.keys(ROOMS).join('|') + '>'); process.exit(1); }
await ROOMS[room]();
writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
console.log('ok', Object.keys(manifest).length, 'entries in', manifestPath);
