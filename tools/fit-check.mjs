// Checks every room in public/rooms/*/room.glb against the module (9.6 x 7.6 x 3.0 m) without three.js:
// it reads each mesh's POSITION accessor bounds and the node transforms, and fails if anything pokes out.
// It also prints what each file carries (UV sets, extras, animations) so a broken export shows up early, and checks
// that every act of every person begins where the first act begins (same spot, same heading): the site crossfades
// acts in place, so an act baked elsewhere makes a person jump.
// Usage: node tools/fit-check.mjs [room-id]
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const MODULE = { W: 9.6, D: 7.6, H: 3.0 }, TOL = 0.005;
const rooms = join(process.cwd(), 'public', 'rooms');
const only = process.argv[2];

function glb(path) {
  const b = readFileSync(path), n = b.readUInt32LE(12), json = JSON.parse(b.toString('utf8', 20, 20 + n));
  json.bin = b.subarray(28 + n, 28 + n + b.readUInt32LE(20 + n));
  return json;
}
/** The first value an animation sampler outputs (a float VEC3 or VEC4). */
function first(g, accessor) {
  const a = g.accessors[accessor], v = g.bufferViews[a.bufferView], k = a.type === 'VEC4' ? 4 : 3, o = (v.byteOffset ?? 0) + (a.byteOffset ?? 0);
  return Array.from({ length: k }, (_, i) => g.bin.readFloatLE(o + 4 * i));
}
const rotate = ([x, y, z, w], [vx, vy, vz]) => {   // quaternion times vector
  const tx = 2 * (y * vz - z * vy), ty = 2 * (z * vx - x * vz), tz = 2 * (x * vy - y * vx);
  return [vx + w * tx + y * tz - z * ty, vy + w * ty + z * tx - x * tz, vz + w * tz + x * ty - y * tx];
};
/** Problems with a person's acts: each must start within 5 cm and 15 degrees of the first act's start. */
function actsInPlace(p) {
  const joints = new Set(p.skins?.[0]?.joints ?? []), parentOf = new Map();
  p.nodes.forEach((n, i) => (n.children ?? []).forEach(c => parentOf.set(c, i)));
  const top = [...joints].find(j => !joints.has(parentOf.get(j)));          // the skeleton's top joint (the hips)
  if (top === undefined) return [];
  const up = p.nodes[parentOf.get(top)] ?? {}, s = up.scale?.[0] ?? 1, q = up.rotation ?? [0, 0, 0, 1];
  const starts = (p.animations ?? []).map(a => {
    const at = path => a.channels.find(c => c.target.node === top && c.target.path === path);
    const t = at('translation'), r = at('rotation');
    return { name: a.name, pos: t ? rotate(q, first(p, a.samplers[t.sampler].output)).map(v => v * s) : null, rot: r ? first(p, a.samplers[r.sampler].output) : null };
  });
  const ref = starts[0], out = [];
  for (const x of starts.slice(1)) {
    const d = x.pos && ref.pos ? Math.hypot(x.pos[0] - ref.pos[0], x.pos[2] - ref.pos[2]) : 0;
    const dot = x.rot && ref.rot ? Math.abs(x.rot.reduce((sum, v, i) => sum + v * ref.rot[i], 0)) : 1;
    const ang = 2 * Math.acos(Math.min(1, dot)) * 180 / Math.PI;
    if (d > 0.05 || ang > 15) out.push(`${x.name} starts ${(d * 100).toFixed(0)} cm and ${ang.toFixed(0)}° from ${ref.name}`);
  }
  return out;
}
const mul = (a, b) => { const o = new Array(16).fill(0); for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) for (let k = 0; k < 4; k++) o[j * 4 + i] += a[k * 4 + i] * b[j * 4 + k]; return o; };
function local(n) {
  if (n.matrix) return n.matrix;
  const [x, y, z, w] = n.rotation ?? [0, 0, 0, 1], [sx, sy, sz] = n.scale ?? [1, 1, 1], [tx, ty, tz] = n.translation ?? [0, 0, 0];
  return [(1 - 2 * (y * y + z * z)) * sx, 2 * (x * y + z * w) * sx, 2 * (x * z - y * w) * sx, 0,
    2 * (x * y - z * w) * sy, (1 - 2 * (x * x + z * z)) * sy, 2 * (y * z + x * w) * sy, 0,
    2 * (x * z + y * w) * sz, 2 * (y * z - x * w) * sz, (1 - 2 * (x * x + y * y)) * sz, 0, tx, ty, tz, 1];
}
const apply = (m, [x, y, z]) => [m[0] * x + m[4] * y + m[8] * z + m[12], m[1] * x + m[5] * y + m[9] * z + m[13], m[2] * x + m[6] * y + m[10] * z + m[14]];

let failed = false;
for (const id of readdirSync(rooms)) {
  if (only && id !== only) continue;
  const path = join(rooms, id, 'room.glb'); if (!existsSync(path)) continue;
  const g = glb(path), lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity], uv1 = new Set(), out = [];
  const walk = (i, parent) => {
    const n = g.nodes[i], m = mul(parent, local(n));
    if (n.mesh !== undefined) for (const p of g.meshes[n.mesh].primitives) {
      const a = g.accessors[p.attributes.POSITION]; if (p.attributes.TEXCOORD_1 !== undefined) uv1.add(n.name);
      for (const c of [[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0], [0, 0, 1], [1, 0, 1], [0, 1, 1], [1, 1, 1]]) {
        const v = apply(m, c.map((k, d) => (k ? a.max : a.min)[d]));
        v.forEach((x, d) => { lo[d] = Math.min(lo[d], x); hi[d] = Math.max(hi[d], x); });
        if (v[1] > MODULE.H + TOL || v[1] < -0.05 - TOL || Math.abs(v[0]) > MODULE.W / 2 + TOL || Math.abs(v[2]) > MODULE.D / 2 + TOL) out.push(n.name);
      }
    }
    for (const c of n.children ?? []) walk(c, m);
  };
  for (const r of g.scenes[g.scene ?? 0].nodes) walk(r, [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
  const ok = out.length === 0;
  failed ||= !ok;
  console.log(`${ok ? 'fits' : 'DOES NOT FIT'}  ${id}: x[${lo[0].toFixed(2)}, ${hi[0].toFixed(2)}] y[${lo[1].toFixed(2)}, ${hi[1].toFixed(2)}] z[${lo[2].toFixed(2)}, ${hi[2].toFixed(2)}] m`
    + `  · ${g.meshes.length} meshes, ${uv1.size} with a light-map UV set, ${g.materials?.length ?? 0} materials`);
  if (!ok) console.log('   outside:', [...new Set(out)].slice(0, 12).join(', '));
  const people = join(rooms, id, 'people');
  if (existsSync(people)) for (const f of readdirSync(people)) {
    const p = glb(join(people, f)), off = actsInPlace(p);
    console.log(`   person ${f}: ${p.skins?.length ?? 0} skin, ${p.skins?.[0]?.joints.length ?? 0} joints, clips ${(p.animations ?? []).map(a => a.name).join(', ')}`);
    if (off.length) { failed = true; console.log(`   ACTS OUT OF PLACE in ${f}: ${off.join('; ')}`); }
  }
}
process.exit(failed ? 1 : 0);
