# Twin Peaks: assemble the Red Room (drapes, the zigzag floor, the chairs, the Venus, the lamps) and its people (the
# agent, Laura, the man from another place, the giant); then preview, bake and export.
import math, os
import bpy
from mathutils import Vector, Matrix
import cine, people, stages
from stages import camera
import rooms.twin_peaks as R

ROOM = 'twin-peaks'
OUT = os.path.join(cine.OUT, ROOM)
WEB = os.path.join(cine.ROOT, 'public', 'rooms', ROOM)
PEOPLE_TEX = os.path.join(cine.OUT, 'people')
SKF = os.path.join(cine.CACHE, 'sketchfab')
ARGS = {}
SEATED = []
MATS = {}
RIG = {'lights': []}


def build(args):
    ARGS.clear(); ARGS.update(args)
    sc = cine.reset(int(args.get('samples', 256)))
    M = R.mats(); MATS.update(M)
    static, phantom, crowd = cine.coll('static'), cine.coll('phantom'), cine.coll('people')
    seated = [] if args.get('nocast') else cast(crowd, args)
    SEATED[:] = seated
    R.shell(M, static, phantom)
    R.drapes(M, static)
    R.chairs(M, static)
    R.venus(M, static)
    for k, p in enumerate(R.TORCH): R.torchiere(f'torchiere{k}', M, static, p)
    R.side_table(M, static)
    RIG['lights'] = R.lights()
    objs = [o for o in static.objects if o.type == 'MESH']; phantoms = [o for o in phantom.objects if o.type == 'MESH']
    bpy.context.view_layer.update()
    cine.bake_ready(objs + phantoms)
    for o in objs + phantoms:
        if not o.data.uv_layers: cine.world_uv(o, 1.0)
        elif 'UVMap' not in o.data.uv_layers: o.data.uv_layers[0].name = 'UVMap'
    R.section(objs, M)
    objs = _merge(objs)
    for o in phantoms: cine.phantom(o)
    cine.check_module(objs)
    cams = {'case': camera('cam_case', (0.6, -17.0, 7.4), (0.2, 0.4, 0.9), 30),
            'close': camera('cam_close', (0.4, -7.4, 2.7), (0.0, 1.0, 1.0), 40),
            'master': camera('cam_master', (-0.4, -3.2, 1.5), (-0.2, 2.4, 1.0), 60),       # the dream's master: the three and the Venus
            'pair': camera('cam_pair', (0.7, -0.6, 1.3), (0.7, 2.6, 1.0), 50),
            'dale': camera('cam_dale', (-0.6, 0.4, 1.4), (-2.6, 1.4, 1.1), 46),
            'slit': camera('cam_slit', (1.2, 0.6, 1.6), (3.6, 3.1, 1.3), 50),
            'top': camera('cam_top', (0.0, 0.0, 14.0), (0.0, 0.1, 0.0), 38),
            'f_dale': camera('cam_f_dale', (-1.6, 1.1, 1.2), (-2.55, 1.32, 1.15), 30),
            'f_laura': camera('cam_f_laura', (1.4, 1.3, 1.15), (1.4, 2.4, 1.1), 30),
            'f_arm': camera('cam_f_arm', (-0.05, 1.5, 0.95), (-0.05, 2.4, 0.9), 34),
            'f_giant': camera('cam_f_giant', (0.2, -0.9, 2.0), (2.3, 2.4, 2.0), 30),
            'right': camera('cam_right', (12.0, -6.0, 6.0), (0.5, 0.2, 0.8), 34)}
    return sc, M, objs, list(phantom.objects), seated, cams


KEEP = ('left_', 'back_', 'kerb', 'floor', 'subfloor', 'drape_', 'venus')


def _merge(objs):
    """Join the many small pieces, one object per atlas and material: fewer meshes to draw."""
    groups = {}
    for o in objs:
        if o.get('role') or len(o.material_slots) != 1 or o.name.startswith(KEEP): continue
        groups.setdefault((o.get('lm', ''), o.material_slots[0].material.name), []).append(o)
    out = [o for o in objs if not any(o in g for g in groups.values())]
    for (lm, mat), g in groups.items():
        if len(g) == 1: out += g; continue
        bpy.ops.object.select_all(action='DESELECT')
        for o in g: o.select_set(True)
        bpy.context.view_layer.objects.active = g[0]
        bpy.ops.object.join()
        j = bpy.context.view_layer.objects.active; j.name = f'{lm}_{mat}' if lm else mat
        if lm: j['lm'] = lm
        out.append(j)
    cine.log(f'merged {len(objs)} meshes into {len(out)}')
    return out


def preview(sc, cams, which, samples, path, size=(1440, 900)):
    """A Cycles render from one camera; pose=who:act:frame poses one person first; seq=who:act:s1;s2;... renders the
    act at those seconds with everyone it cues posed alongside."""
    if ARGS.get('seq'):
        who, act, ts = str(ARGS['seq']).split(':')
        for t in ts.split(';'):
            for c, arm, mesh in SEATED:
                if act in c['acts'] and (c['who'] == who or act == 'scene'):
                    people.pose_at(arm, c['acts'][act], int(c['acts'][act].frame_range[0]) + int(float(t) * people.FPS))
            stages.render(sc, cams[which], samples, path.replace('.png', f'_{act}_{float(t):05.1f}.png'), (960, 600), float(ARGS.get('exposure', 0.0)))
        return
    for spec in filter(None, str(ARGS.get('pose', '')).split(',')):
        who, act, f = spec.split(':')
        for c, arm, mesh in SEATED:
            if c['who'] == who and act in c['acts']: people.pose_at(arm, c['acts'][act], int(c['acts'][act].frame_range[0]) + int(f))
    stages.render(sc, cams[which], samples, path, size, float(ARGS.get('exposure', 0.0)))


# ---------------------------------------------------------------- the cast
# The loop (one clock, TL): the three sit, the man from another place talking with his hands; he gets up, dances
# (knees bent, shuffling, snapping his fingers) across the front of the drapes and back, and sits; the giant comes
# in through the slit in the drapes, stops before them, says what he has to say to the agent and goes out the way he
# came; Laura gets up, goes round to the agent, bends and whispers in his ear, a hand on his shoulder, and goes back to
# her chair. Costumes after Patricia Norris (people_textures.twin_peaks).
def _tex(who, prefix, *names):
    return {f'{prefix}_{n}.tga': f'{who}/{prefix}_{n}.png' for n in names}


HEAD = {w: os.path.join(cine.OUT, 'people', w, f'{w}_head.glb') for w in ('dale', 'laura', 'arm', 'giant')}
HEAD_FIT = {                                      # who -> swap_head settings (eyes measured on each head by raycast)
    'dale': dict(front='-y', eyes=((-0.100, -0.153, 1.563), (0.076, -0.153, 1.563)), cut=0.0, fan_cut=-0.12, keep_r=(0.3, 0.3)),
    'laura': dict(front='-y', eyes=((-0.224, -0.3545, 0.214), (0.05, -0.3545, 0.245)), cut=0.02, fan_cut=0.02, scalp=(200, 160, 100)),
    'arm': dict(front='-y', eyes=((-0.141, -0.314, -0.031), (0.147, -0.322, -0.027)), cut=-0.04, fan_cut=-0.12, keep_r=(0.075, 0.06), scalp=(24, 20, 18)),
    'giant': dict(front='-y', eyes=((-0.163, -0.291, 0.043), (0.099, -0.305, 0.013)), cut=0.0, fan_cut=-0.12, keep_r=(0.3, 0.3)),
}
CAST = [
    dict(who='dale', avatar='Business_Male_01', shape=('lean', 0.4), height=1.78, tex=_tex('dale', 'm005', 'body_color')),
    dict(who='laura', avatar='Female_Adult_15', shape=None, height=1.70,
         shell=dict(colour=(210, 172, 108), hem=-0.1, thick=0.016, gap=0.007, fall=0.018, front=34.0, temple=14.0, nape=-26.0, curl=1.0, width=0.038),
         skirt=dict(image='laura/gown.png', hem=0.01, top=0.06, ease=0.02, flare=0.2, folds=16, depth=0.012),
         tex=_tex('laura', 'f018', 'head_color', 'body_color', 'body_normal')),
    dict(who='arm', avatar='Male_Adult_06', shape=None, height=1.09, proportion={'Thigh': 0.45, 'Calf': 0.5, 'UpperArm': 0.66, 'Forearm': 0.72},
         big_head=(1.24, 0.05), tex=_tex('arm', 'm011', 'head_color', 'body_color', 'body_normal')),
    dict(who='giant', avatar='Male_Adult_12', shape=('lean', 0.8), height=2.13, tex=_tex('giant', 'm007', 'head_color', 'body_color', 'body_normal')),
]
for c in CAST:
    if c['who'] in HEAD_FIT and os.path.exists(HEAD[c['who']]): c['head'] = dict(glb=HEAD[c['who']], **HEAD_FIT[c['who']])
K = {c['who']: c['height'] / 1.78 for c in CAST}
SPINE = ('Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2')
ARMS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('Clavicle', 'UpperArm', 'Forearm', 'Hand'))
LEGS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('Thigh', 'Calf', 'Foot'))
FINGERS = tuple(f'Bip01 {s} Finger{f}{j}' for s in 'LR' for f in '01234' for j in ('', '1', '2'))
ALL = ('Bip01 Pelvis',) + SPINE + ARMS + LEGS + ('Bip01 Neck', 'Bip01 Head')


def _seat(who):
    p, f = R.CHAIRS[who]; return (p.x - f.x * 0.06, p.y - f.y * 0.06), (f.x, f.y)


# where they are (true metres) and which way they face: the three seated; the giant waits in the corridor behind the
# drapes (out of sight), facing along it toward the slit
HOME = {'dale': _seat('dale'), 'laura': _seat('laura'), 'arm': _seat('arm'), 'giant': ((3.98, 3.36), (-1.0, -0.2))}
BASES = {'dale': 'm_sit_chair_breathe_01', 'laura': 'f_sit_chair_breathe_01', 'arm': 'm_sit_chair_idle_relaxed_01', 'giant': 'm_idle_breathe_01'}
SITTERS = ('dale', 'laura', 'arm')
WORK = {w: ('wait', 6, 12) for w in HOME}
FIRST = {'arm': 'scene'}
CUE = {'arm': {'scene': {w: 'scene' for w in HOME if w != 'arm'}}}
TL = dict(arm_talk=(1.0, 6.0), arm_up=(6.4, 8.8), dance=(8.8, 25.6), arm_down=(26.4, 29.4), arm_talk2=(30.4, 34.0),
          g_in=(35.0, 44.5), g_talk=(44.5, 55.5), g_bow=(54.0, 55.5), g_out=(55.5, 64.5),
          l_up=(66.0, 68.6), l_to=(68.6, 73.6), whisper=(73.6, 81.0), l_back=(81.0, 86.0), l_down=(86.0, 89.0),
          l_touch=(14.0, 18.0), end=96.0)
# the dance's route before the chairs: out from his chair, across to the right under Laura's torchiere, back
ARM_F = Vector((*HOME['arm'][1], 0)).normalized()
DANCE = [(HOME['arm'][0][0], HOME['arm'][0][1] - 0.62), (0.7, 1.62), (1.7, 1.52), (2.25, 1.75), (1.6, 1.42), (0.6, 1.5),
         (HOME['arm'][0][0], HOME['arm'][0][1] - 0.62)]
G_IN = [HOME['giant'][0], (3.45, 3.22), (3.05, 3.08), (2.72, 2.86), (2.5, 2.25), (1.6, 1.2), (0.4, 0.62), (-0.35, 0.55)]
G_SPOT = (-0.35, 0.55)
G_FACE = (-0.8, 0.6)
DALE_SEAT = Vector((*HOME['dale'][0], 0.0)); DALE_F = Vector((*HOME['dale'][1], 0)).normalized()
DALE_R = Vector((DALE_F.y, -DALE_F.x, 0))                 # the agent's right (toward the room's front)
L_SPOT = tuple((DALE_SEAT + DALE_F * 0.5 + DALE_R * 0.42).xy)
L_FACE = tuple((-(DALE_F * 0.45 + DALE_R * 0.75)).normalized().xy)
L_ROUTE = [(HOME['laura'][0][0], HOME['laura'][0][1] - 0.6), (0.7, 1.3), (-0.6, 0.85), (-1.5, 0.6), L_SPOT]
REC = {}                                          # who -> {frame: {'head', 'sR', 'sL'}}


def _all(arm, fingers=False):
    return (next(b.name for b in arm.data.bones if b.parent is None),) + ALL + (FINGERS if fingers else ())


def _smooth(x):
    x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)


def _win(t, a, b, rise=0.5, fall=0.5):
    return _smooth((t - a) / rise) * (1 - _smooth((t - b) / fall))


def _live(arm):
    pb = arm.pose.bones['Bip01 Pelvis']; M = people._world(arm, pb)
    f = M.to_3x3() @ Vector(arm['pel_fwd']); f.z = 0; f.normalize()
    up = Vector((0, 0, 1)); return M.translation.copy(), f, f.cross(up).normalized(), up


def _P(arm, bone):
    return people._world(arm, arm.pose.bones[bone]).translation.copy()


def _look(arm, at, w, limit=1.3, twist=0.0):
    """Head and neck turned toward `at` by w; `twist` shares the turn with the spine."""
    if w <= 0: return
    H = _P(arm, 'Bip01 Head'); pel, f, right, up = _live(arm)
    d = (Vector(at) - H).normalized()
    yaw = math.atan2(d.dot(-right), d.dot(f)); pitch = math.asin(max(-1, min(1, d.z)))
    if twist:
        for b_ in SPINE: people.bend(arm, b_, up, yaw * twist / 3 * w)
        yaw *= (1 - twist)
    yaw = max(-limit, min(limit, yaw)); pitch = max(-0.8, min(0.6, pitch))
    people.bend(arm, 'Bip01 Neck', up, yaw * 0.35 * w); people.bend(arm, 'Bip01 Head', up, yaw * 0.65 * w)
    people.bend(arm, 'Bip01 Neck', right, pitch * 0.3 * w); people.bend(arm, 'Bip01 Head', right, pitch * 0.7 * w)


def _hand_to(arm, side, tgt, w, pole, palm=None, pw=0.8):
    if w <= 0: return
    H0 = _P(arm, f'Bip01 {side} Hand'); g = H0.lerp(Vector(tgt), min(w, 1.0))
    people.ik2(arm, side, g, Vector(pole))
    if palm is not None: people.palm_to(arm, side, Vector(palm).normalized(), pw * min(w, 1.0))


def _record(who, arm, f):
    REC.setdefault(who, {})[f] = {'head': _P(arm, 'Bip01 Head'), 'sR': _P(arm, 'Bip01 R UpperArm'), 'sL': _P(arm, 'Bip01 L UpperArm')}


def _rec(who, f, key='head'):
    r = REC.get(who, {})
    if not r: (x, y), _ = HOME[who]; return Vector((x, y, 1.1 if who in SITTERS else 1.9))
    return (r.get(f) or r[min(r, key=lambda g: abs(g - f))])[key]


class Seq:
    """A scene's segments, built in order: add() a clip for a fixed time, pad() one until a moment on the clock,
    walk_to() a walk that arrives at a moment (the clip played faster or slower to match)."""
    def __init__(self): self.segs = []
    def t(self): return sum(s['dur'] for s in self.segs)
    def add(self, tag, **kw): kw['tag'] = tag; self.segs.append(kw)
    def pad(self, tag, until, **kw): kw['dur'] = max(0.4, until - self.t()); self.add(tag, **kw)
    def walk_to(self, arm, tag, walk, vs, pts, until, blend=0.6):
        route = people.path([Vector(p) for p in pts]); dur = max(0.5, until - self.t()); v = route[1] / dur
        self.add(tag, src=walk[0], f0=walk[1][0], dur=dur, rate=v / vs, at=people.walk_along(arm, walk[0], walk[1][0], v, route), blend=blend)
    def clip(self, arm, tag, c, p, h, dur, end=False, blend=0.6):
        """A clip at a place, fitted to `dur` seconds (played faster or slower)."""
        f0, f1 = c[1]; own = (f1 - f0) / people.FPS
        self.add(tag, src=c[0], f0=f0, dur=dur, rate=own / dur, at=_at(arm, c[0], f1 if end else f0, p, h), blend=blend)
    def log(self, who):
        t = 0.0
        for s in self.segs: s['t0'] = t; t += s['dur']
        cine.log(f'{who} scene: ' + ', '.join(f"{s['tag']} {s['t0']:.1f}" for s in self.segs) + f' end {t:.1f}')
        return t


def _at(arm, src, f, p, h):
    hh, pp = people.heading(arm, src, f); return people.carry(pp, hh, Vector((p[0], p[1], 0)), Vector((h[0], h[1], 0)).normalized())


def _clips(arm, who, names):
    return {k: people.retarget(arm, clip, action_name=f'{who}_src_{k}', **kw) for k, (clip, kw) in names.items()}


def _long(arm, who, clip, key, inplace=False):
    """A clip retargeted for the whole scene's length (an idle that never runs out)."""
    n = int(round(TL['end'] * people.FPS)) + 90
    return people.retarget(arm, clip, cycles=80, limit=n, inplace=inplace, action_name=f'{who}_src_{key}')


def _idle(Q, tag, until, idle, p, h, blend=0.7, arm=None):
    """An idle segment at a place until a moment, its clip taken from where the clock is."""
    f0 = idle[1][0] + int(Q.t() * people.FPS)
    Q.pad(tag, until, src=idle[0], f0=f0, at=_at(arm, idle[0], f0, p, h), blend=blend)


def _drift(arm, src, f0, pts, until, Q, face=None):
    """A carrier for a clip danced in place while it travels along a route by `until`, facing `face` throughout (or
    along the route)."""
    route = people.path([Vector(p) for p in pts]); at, L = route; dur = max(0.5, until - Q.t()); v = L / dur
    hw, pw = people.heading(arm, src, f0)
    def M(lt):
        p, tg = at(lt * v)
        return people.carry(pw, hw, p, Vector((*face, 0)).normalized() if face else tg)
    return M, dur


# ---------------------------------------------------------------- making them
def _big_head(arm, mesh, s, drop=0.0):
    """A head `s` times its size about the neck's top (an adult's head on a small man's body), set `drop` metres lower
    on the neck (his is short): the vertices by their weights to the head and what hangs from it, the head's own bones
    with them."""
    heads = {b.name for b in arm.data.bones if b.name == 'Bip01 Head' or (b.parent and any(p.name == 'Bip01 Head' for p in b.parent_recursive))}
    heads |= {b.name for b in arm.data.bones if b.parent and b.parent.name == 'Bip01 Head'}
    H = arm.matrix_world @ arm.data.bones['Bip01 Head'].head_local
    me = mesh.data; M = mesh.matrix_world; Mi = M.inverted(); names = [g.name for g in mesh.vertex_groups]
    for v in me.vertices:
        w = sum(g.weight for g in v.groups if names[g.group] in heads)
        if w <= 0: continue
        p = M @ v.co; w = min(w, 1.0); v.co = Mi @ (H + (p - H) * (1 + (s - 1) * w) - Vector((0, 0, drop * w)))
    bpy.context.view_layer.objects.active = arm; arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    A = arm.matrix_world; Ai = A.inverted()
    dz = Vector((0, 0, drop))
    for eb in arm.data.edit_bones:
        if eb.name in heads and eb.name != 'Bip01 Head':
            eb.head = Ai @ (H + (A @ eb.head - H) * s - dz); eb.tail = Ai @ (H + (A @ eb.tail - H) * s - dz)
        elif eb.name == 'Bip01 Head':
            eb.head = Ai @ (A @ eb.head - dz); eb.tail = Ai @ (A @ eb.tail - dz)
    bpy.ops.object.mode_set(mode='OBJECT')
    people._fresh_normals(mesh)
    cine.log('big head', mesh.get('person'), s)


def _cloth(who, image):
    m = bpy.data.materials.new(f'{who}_cloth'); nt = m.node_tree; p = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.join(PEOPLE_TEX, image), check_existing=True)
    nt.links.new(t.outputs['Color'], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.7; p.inputs['Specular IOR Level'].default_value = 0.35
    p.inputs['Sheen Weight'].default_value = 0.5; p.inputs['Sheen Tint'].default_value = (0.3, 0.28, 0.3, 1)
    return m


def make_person(c, col):
    """One of them, standing at the origin facing -y: the avatar, its build, its proportions, its head, hair and
    gown, its height."""
    tex = {k: os.path.join(PEOPLE_TEX, v) for k, v in c.get('tex', {}).items() if os.path.exists(os.path.join(PEOPLE_TEX, v))}
    arm, mesh = people.load_avatar(c['avatar'], textures=tex, collection=col)
    arm.animation_data_clear()
    mesh['person'] = c['who']; arm['person'] = c['who']
    if c.get('shape'): people.reshape(arm, mesh, *c['shape'])
    if c.get('proportion'): people.reproportion(arm, mesh, c['proportion'])
    if c.get('big_head'): _big_head(arm, mesh, *c['big_head'])
    if c.get('head'):
        h = c['head']
        people.swap_head(arm, mesh, h['glb'], None, h['front'], h['eyes'], cut=h.get('cut', 0.0), fan_cut=h.get('fan_cut', -0.03), tone=h.get('tone'),
                         neck_skin=h.get('neck_skin', False), scalp=h.get('scalp'))
        if h.get('keep_r'):                                             # a made neck: the sculpt's bust cut round it
            from rooms.rear_window_build import _bust_cut
            _bust_cut(arm, mesh, c['who'], h['keep_r'])
    if c.get('shell') or c.get('head'): people.remove_hair_cards(mesh)
    bpy.context.view_layer.update()
    top = max((mesh.matrix_world @ v.co).z for v in mesh.data.vertices)
    J = people._joints(arm)
    if c.get('shell'):
        h = dict(c['shell']); h['hem'] = J['Bip01 Neck'].z + h['hem']
        people.hair_shell(arm, mesh, **h)
    if c.get('skirt'):
        h = dict(c['skirt']); h['hem'] = h['hem'] * top / c['height']
        people.skirt(arm, mesh, _cloth(c['who'], h.pop('image')), **h)
    for ca in list(mesh.data.color_attributes): mesh.data.color_attributes.remove(ca)
    s = c['height'] / top
    arm.scale = arm.scale * s; arm.location = (arm.location.x, arm.location.y, arm.location.z * s)
    bpy.context.view_layer.update()
    return arm, mesh


def cast(col, args):
    """Load, dress, shape and place them, and bake their acts (cached: retargets and IK take minutes)."""
    full = bool(args.get('full'))
    spec = {'cast': CAST, 'bases': BASES, 'work': WORK, 'cue': CUE, 'tl': TL, 'home': HOME, 'dance': DANCE, 'g_in': G_IN, 'chairs': {k: [list(p), list(f)] for k, (p, f) in R.CHAIRS.items()},
            'seat_h': R.SEAT_H, 'full': full, 'v': 5}
    for c in CAST:
        c['work'] = WORK[c['who']]; c['idles'] = {'scene': (None, 1.0 if c['who'] == 'arm' else 0.0)}; c['cue'] = CUE.get(c['who'], {})
        c['roam'] = ('scene',)
    seated = stages.cast_cache(OUT, CAST, spec, lambda: _make_cast(col, full), col)
    for c, arm, mesh in seated:
        people.pose_at(arm, c['acts'][c['work'][0]], int(c['acts'][c['work'][0]].frame_range[0]) + 10)
    return seated


def _place(c, arm):
    who = c['who']; (x, y), f = HOME[who]; f = Vector((*f, 0)).normalized()
    people.face(arm, f); arm.location = (x, y, arm.location.z); bpy.context.view_layer.update()
    arm['fwd'] = list(f)
    base, frames, _ = people.retarget(arm, BASES[who], cycles=2, action_name=f'{who}_base')
    people.pose_at(arm, base, frames[0])
    pel = _P(arm, 'Bip01 Pelvis')
    arm.location.x += x - pel.x; arm.location.y += y - pel.y
    bpy.context.view_layer.update()
    people.pose_at(arm, base, frames[0])
    arm['pel_fwd'] = list(people._world(arm, arm.pose.bones['Bip01 Pelvis']).to_3x3().inverted() @ f)
    return base, frames


def _make_cast(col, full):
    seated, made = [], {}
    for c in CAST:
        arm, mesh = make_person(c, col)
        base, frames = _place(c, arm)
        made[c['who']] = dict(c=c, arm=arm, mesh=mesh, base=base, frames=frames, k=K[c['who']])
        seated.append((c, arm, mesh))
    acts = {k: {} for k in made}
    for m in made.values(): m['mesh'].hide_viewport = True
    for who, fn in (('arm', _arm_acts), ('giant', _giant_acts), ('dale', _dale_acts), ('laura', _laura_acts)):
        for w2, m2 in made.items(): m2['arm'].hide_viewport = w2 != who
        fn(made[who], acts[who], full)
    for m2 in made.values(): m2['arm'].hide_viewport = False
    for who, m in made.items():
        m['c']['acts'] = acts[who]
        if m['base'] not in acts[who].values(): bpy.data.actions.remove(m['base'])
        m['mesh'].hide_viewport = False
        people.pose_at(m['arm'], acts[who][m['c']['work'][0]], int(m['frames'][0]) + 10)
    return seated


# ---------------------------------------------------------------- shared
def _lift(arm, k):
    """How far a chair clip's pelvis must move to sit on these cushions (lower than the clip's 0.52 m seat)."""
    return (R.SEAT_H + 0.085 * k) - _P(arm, 'Bip01 Pelvis').z


def _seated_w(tag, lt, sit_tags, down_tags, up_tags):
    if tag in sit_tags: return 1.0
    if tag in down_tags: return _smooth((lt - 0.6) / 1.4)
    if tag in up_tags: return 1 - _smooth(lt / 1.2)
    return 0.0


def _seat_parts(arm, who, k, Q):
    """The sitter's clips: the base (seated), getting up and sitting down."""
    sx = 'f' if who == 'laura' else 'm'
    C = _clips(arm, who, {'down': (f'{sx}_sit_down_chair_01', {}), 'up': (f'{sx}_sit_stand_up_chair_01', {})})
    return C


def _wait(arm, base, frames, who, k, look):
    """Between scenes: seated as the base has them, on these cushions, a look."""
    pose = {}
    def step(f, t):
        if 'z' not in pose: pose['z'] = _lift(arm, k)
        people.shift_root(arm, (0, 0, pose['z']))
        _look(arm, look(f), 0.55)
    return people.custom_act(arm, base, frames, f'{who}_wait', step, _all(arm))


# ---------------------------------------------------------------- the man from another place
def _arm_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS; T = TL; who = 'arm'
    dale_head = DALE_SEAT + Vector((0, 0, 1.15))
    people.pose_at(arm, base, frames[0]); lift = {'z': _lift(arm, k)}
    acts['wait'] = _wait(arm, base, frames, who, k, lambda f: dale_head)
    if not full: return
    C = _seat_parts(arm, who, k, None)
    C.update(_clips(arm, who, {'dance': ('m_dancing_cool', dict(inplace=True, cycles=6))}))
    shrug = _long(arm, who, 'm_sit_chair_gestic_shrug_01', 'shrug'); relax = _long(arm, who, 'm_sit_chair_idle_relaxed_01', 'relax')
    seat, sf_ = HOME[who]
    Q = Seq()
    Q.pad('start', 0.6, src=base, f0=frames[0], at=Matrix.Identity(4))
    _idle(Q, 'talk', T['arm_up'][0], shrug, seat, sf_, arm=arm)
    Q.clip(arm, 'up', C['up'], seat, sf_, T['arm_up'][1] - T['arm_up'][0])
    d = C['dance']; M_, dur = _drift(arm, d[0], d[1][0], DANCE, T['dance'][1], Q, face=(0.15, -1.0))
    Q.add('dance', src=d[0], f0=d[1][0], dur=dur, rate=1.0, at=M_, blend=0.8)
    Q.clip(arm, 'down', C['down'], seat, sf_, T['arm_down'][1] - Q.t(), end=True)
    f0 = relax[1][0] + int(Q.t() * FPS); Q.pad('seated', T['arm_talk2'][0], src=relax[0], f0=f0, at=_at(arm, relax[0], f0, seat, sf_))
    _idle(Q, 'talk2', T['arm_talk2'][1], shrug, seat, sf_, arm=arm)
    f0 = relax[1][0] + int(Q.t() * FPS); Q.pad('seated2', T['end'] - 1.4, src=relax[0], f0=f0, at=_at(arm, relax[0], f0, seat, sf_))
    Q.pad('end', T['end'], src=base, f0=frames[0], at=Matrix.Identity(4), blend=1.2)
    Q.log(who)
    sit_tags = ('start', 'talk', 'seated', 'talk2', 'seated2', 'end')

    def overlay(tt, i, lt):
        tag = Q.segs[i]['tag']; f = int(round(tt * FPS))
        sw = _seated_w(tag, lt, sit_tags, ('down',), ('up',))
        if sw > 0: people.shift_root(arm, (0, 0, lift['z'] * sw))
        pel, fwd, right, up_ = _live(arm)
        if tag == 'dance':                                                  # the snaps: fingers closed, flicked, in time
            for side in 'LR':
                people.hand_shape(arm, side, 'fist', 0.35 + 0.35 * max(0.0, math.sin(tt * math.pi * 2.0 + (0 if side == 'L' else math.pi))))
            _look(arm, dale_head if (tt % 6) < 3.5 else Vector((pel.x, pel.y - 2.0, 1.0)), 0.5)
        elif tag in ('talk', 'talk2'):
            _look(arm, dale_head, 0.7)
        elif tag in ('seated', 'seated2', 'end', 'start'):
            g = _rec('giant', f)
            at_ = g if T['g_in'][0] + 1.5 < tt < T['g_out'][1] - 1.0 else (_rec('laura', f) if T['l_up'][0] < tt < T['l_down'][1] else dale_head)
            _look(arm, at_, 0.6)
        _record(who, arm, f)
    acts['scene'] = people.sequence(arm, base, f'{who}_scene', Q.segs, overlay=overlay)
    for a, _, _ in C.values(): bpy.data.actions.remove(a)
    for a in (shrug, relax): bpy.data.actions.remove(a[0])


# ---------------------------------------------------------------- the giant
def _giant_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS; T = TL; who = 'giant'
    home, hf = HOME[who]
    def wait(f, t): pass
    acts['wait'] = people.custom_act(arm, base, frames, f'{who}_wait', wait, _all(arm))
    if not full: return
    C = _clips(arm, who, {'walk': ('m_walk_slow_01', dict(inplace=True, cycles=10))})
    idle = _long(arm, who, 'm_idle_breathe_01', 'idle'); talk = _long(arm, who, 'm_gestic_talk_neutral_02', 'talk', inplace=True)
    walk, vs = (C['walk'][0], C['walk'][1]), C['walk'][2]
    dale_head = DALE_SEAT + Vector((0, 0, 1.15))
    Q = Seq()
    _idle(Q, 'hidden', T['g_in'][0], idle, home, hf, arm=arm)
    Q.walk_to(arm, 'w_in', walk, vs, G_IN, T['g_in'][1])
    Q.pad('talk', T['g_bow'][0], src=talk[0], f0=talk[1][0], at=_at(arm, talk[0], talk[1][0], G_SPOT, G_FACE))
    _idle(Q, 'bow', T['g_bow'][1], idle, G_SPOT, G_FACE, arm=arm)
    Q.walk_to(arm, 'w_out', walk, vs, list(reversed(G_IN)), T['g_out'][1])
    _idle(Q, 'hidden2', T['end'] - 1.2, idle, home, hf, arm=arm)
    Q.pad('end', T['end'], src=base, f0=frames[0], at=Matrix.Identity(4), blend=1.0)
    Q.log(who)

    def overlay(tt, i, lt):
        tag = Q.segs[i]['tag']; f = int(round(tt * FPS))
        pel, fwd, right, up_ = _live(arm)
        if tag == 'talk':                                                   # to the agent, then to the two in their chairs
            pair = Vector((0.68, 2.42, 1.0))
            _look(arm, dale_head if (lt % 7) < 4.5 else pair, 0.8, twist=0.3)
        elif tag == 'bow':                                                  # a slow bow from the waist to the agent
            w = _win(lt, 0.0, Q.segs[i]['dur'] - 0.2, 0.5, 0.5)
            for b_, a in zip(SPINE, (0.14, 0.12, 0.1)): people.bend(arm, b_, right, -a * w)
            _look(arm, dale_head, 0.5)
        elif tag == 'w_in' and lt > Q.segs[i]['dur'] - 3.0:
            _look(arm, dale_head, 0.5 * _smooth((lt - (Q.segs[i]['dur'] - 3.0)) / 1.5))
        _record(who, arm, f)
    acts['scene'] = people.sequence(arm, base, f'{who}_scene', Q.segs, overlay=overlay)
    for a, _, _ in C.values(): bpy.data.actions.remove(a)
    for a in (idle, talk): bpy.data.actions.remove(a[0])


# ---------------------------------------------------------------- the agent
def _laura_at(t):
    """Where Laura's head is at t (her route, before her acts are made): for the agent's eyes."""
    T = TL
    if T['l_to'][0] <= t <= T['l_to'][1] or T['l_back'][0] <= t <= T['l_back'][1]:
        a, b = (T['l_to'] if t <= T['l_to'][1] else T['l_back'])
        u = (t - a) / (b - a); pts = L_ROUTE if t <= T['l_to'][1] else list(reversed(L_ROUTE))
        at, L = people.path([Vector(p) for p in pts]); p, _ = at(u * L); return p + Vector((0, 0, 1.6))
    if T['l_to'][1] < t < T['l_back'][0]: return Vector((*L_SPOT, 1.35))
    (x, y), _ = HOME['laura']; return Vector((x, y, 1.1))


def _dale_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS; T = TL; who = 'dale'
    arm_head = Vector((*HOME['arm'][0], 0.85))
    people.pose_at(arm, base, frames[0]); lift = {'z': _lift(arm, k)}
    acts['wait'] = _wait(arm, base, frames, who, k, lambda f: arm_head)
    if not full: return
    seat_c = _long(arm, who, 'm_sit_chair_breathe_01', 'seat'); still = _long(arm, who, 'm_sit_chair_idle_neutral_01', 'still')
    seat, sf_ = HOME[who]
    Q = Seq()
    Q.pad('start', 0.6, src=base, f0=frames[0], at=Matrix.Identity(4))
    f0 = seat_c[1][0] + int(Q.t() * FPS); Q.pad('seated', T['whisper'][0] - 1.0, src=seat_c[0], f0=f0, at=_at(arm, seat_c[0], f0, seat, sf_))
    f0 = still[1][0] + int(Q.t() * FPS); Q.pad('listen', T['whisper'][1] + 1.0, src=still[0], f0=f0, at=_at(arm, still[0], f0, seat, sf_), blend=1.0)
    f0 = seat_c[1][0] + int(Q.t() * FPS); Q.pad('seated2', T['end'] - 1.4, src=seat_c[0], f0=f0, at=_at(arm, seat_c[0], f0, seat, sf_), blend=1.0)
    Q.pad('end', T['end'], src=base, f0=frames[0], at=Matrix.Identity(4), blend=1.2)
    Q.log(who)

    def overlay(tt, i, lt):
        tag = Q.segs[i]['tag']; f = int(round(tt * FPS))
        people.shift_root(arm, (0, 0, lift['z']))
        pel, fwd, right, up_ = _live(arm)
        if T['dance'][0] - 1.0 < tt < T['arm_down'][1]: at_, w = _rec('arm', f), 0.7
        elif T['g_in'][0] + 2.0 < tt < T['g_out'][1] - 2.5: at_, w = _rec('giant', f), 0.75
        elif T['l_up'][0] < tt < T['whisper'][0] + 0.5 or T['l_back'][0] < tt < T['l_down'][1]: at_, w = _laura_at(tt), 0.6
        elif T['whisper'][0] + 0.5 <= tt <= T['l_back'][0]: at_, w = _P(arm, 'Bip01 Head') + fwd * 2.0 + right * 0.5, 0.4     # listening, eyes ahead
        else: at_, w = arm_head, 0.6
        _look(arm, at_, w, twist=0.2)
        _record(who, arm, f)
    acts['scene'] = people.sequence(arm, base, f'{who}_scene', Q.segs, overlay=overlay)
    for a in (seat_c, still): bpy.data.actions.remove(a[0])


# ---------------------------------------------------------------- Laura
def _laura_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS; T = TL; who = 'laura'
    dale_head = DALE_SEAT + Vector((0, 0, 1.15))
    people.pose_at(arm, base, frames[0]); lift = {'z': _lift(arm, k)}
    acts['wait'] = _wait(arm, base, frames, who, k, lambda f: dale_head)
    if not full: return
    C = _seat_parts(arm, who, k, None)
    C.update(_clips(arm, who, {'walk': ('f_walk_slow_01', dict(inplace=True, cycles=8))}))
    seat_c = _long(arm, who, 'f_sit_chair_breathe_01', 'seat'); touch = _long(arm, who, 'f_sit_chair_idle_touch_face', 'touch')
    idle = _long(arm, who, 'f_idle_breathe_01', 'idle')
    walk, vs = (C['walk'][0], C['walk'][1]), C['walk'][2]
    seat, sf_ = HOME[who]
    Q = Seq()
    Q.pad('start', 0.6, src=base, f0=frames[0], at=Matrix.Identity(4))
    f0 = seat_c[1][0] + int(Q.t() * FPS); Q.pad('seated', T['l_touch'][0], src=seat_c[0], f0=f0, at=_at(arm, seat_c[0], f0, seat, sf_))
    _idle(Q, 'touch', T['l_touch'][1], touch, seat, sf_, arm=arm)
    f0 = seat_c[1][0] + int(Q.t() * FPS); Q.pad('seated1', T['l_up'][0], src=seat_c[0], f0=f0, at=_at(arm, seat_c[0], f0, seat, sf_))
    Q.clip(arm, 'up', C['up'], seat, sf_, T['l_up'][1] - T['l_up'][0])
    Q.walk_to(arm, 'w_to', walk, vs, L_ROUTE, T['l_to'][1])
    _idle(Q, 'whisper', T['whisper'][1], idle, L_SPOT, L_FACE, arm=arm)
    Q.walk_to(arm, 'w_back', walk, vs, list(reversed(L_ROUTE)), T['l_back'][1])
    Q.clip(arm, 'down', C['down'], seat, sf_, T['l_down'][1] - Q.t(), end=True)
    f0 = seat_c[1][0] + int(Q.t() * FPS); Q.pad('seated2', T['end'] - 1.4, src=seat_c[0], f0=f0, at=_at(arm, seat_c[0], f0, seat, sf_))
    Q.pad('end', T['end'], src=base, f0=frames[0], at=Matrix.Identity(4), blend=1.2)
    Q.log(who)
    sit_tags = ('start', 'seated', 'touch', 'seated1', 'seated2', 'end')

    def overlay(tt, i, lt):
        tag = Q.segs[i]['tag']; f = int(round(tt * FPS))
        sw = _seated_w(tag, lt, sit_tags, ('down',), ('up',))
        if sw > 0: people.shift_root(arm, (0, 0, lift['z'] * sw))
        pel, fwd, right, up_ = _live(arm)
        if tag == 'whisper':
            # she bends to his right ear: the back curving forward, her head beside his, her left hand on his
            # right shoulder, then straightens
            dur = Q.segs[i]['dur']; w = _win(lt, 0.4, dur - 1.0, 1.4, 1.2)
            ear = _rec('dale', f) + DALE_R * 0.11 * K['dale'] + Vector((0, 0, 0.02))
            for b_, a in zip(SPINE, (0.22, 0.2, 0.16)): people.bend(arm, b_, right, -a * w)
            pel, fwd, right, up_ = _live(arm)
            _look(arm, ear, 0.9 * w + 0.3)
            sh = _rec('dale', f, 'sR') + Vector((0, 0, 0.04))
            side = min('LR', key=lambda s_: (_P(arm, f'Bip01 {s_} Hand') - sh).length); sd = -1 if side == 'L' else 1
            _hand_to(arm, side, sh, w, sh - up_ * 0.4 + right * sd * 0.3 - fwd * 0.2, palm=-up_, pw=0.6)
        elif tag in ('seated', 'seated1', 'seated2', 'start', 'end', 'touch'):
            at_ = _rec('arm', f) if T['dance'][0] - 0.5 < tt < T['arm_down'][1] else _rec('giant', f) if T['g_in'][0] + 2.0 < tt < T['g_out'][1] - 2.5 else dale_head
            _look(arm, at_, 0.55)
        elif tag in ('w_to',):
            _look(arm, dale_head, 0.5 * _smooth(lt / 1.5))
        _record(who, arm, f)
    acts['scene'] = people.sequence(arm, base, f'{who}_scene', Q.segs, overlay=overlay)
    for a, _, _ in C.values(): bpy.data.actions.remove(a)
    for a in (seat_c, touch, idle): bpy.data.actions.remove(a[0])


# ---------------------------------------------------------------- bake and export
def bake(sc, objs, phantoms, seated, args):
    """The room's light baked into atlases (the people out of it); then room.glb, the people and room.json."""
    os.makedirs(WEB, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    for c, arm, mesh in seated: mesh.hide_render = True
    export, atlases = stages.bake(objs, R.RH, OUT, int(args.get('size', 2048)), int(args.get('samples', 320)))
    for c, arm, mesh in seated: mesh.hide_render = False
    cine.export_glb(export, os.path.join(WEB, 'room.glb'))
    meta = stages.room_meta(R.RH, atlases); meta.update(_capture_meta())
    meta['people'] = _export_people(seated)
    stages.write_meta(WEB, meta)


def _export_people(seated):
    out = os.path.join(WEB, 'people'); os.makedirs(out, exist_ok=True); metas = []
    for c, arm, mesh in seated:
        people.export_person(arm, mesh, c['acts'], os.path.join(out, f"{c['who']}.glb"), roam=c.get('roam', ()))
        metas.append(person_meta(c))
    return metas


def _capture_meta():
    """How to light the people as the bake lit the room (three.js: y up, z = -Blender y): the spots over the drapes
    and the soft key as emitters; the drapes' red all round; captured among the chairs and before the slit."""
    em = []
    for l in RIG['lights']:
        if l.type != 'LIGHT': continue
        r = 0.25 if l.data.type == 'SPOT' else 0.8; e = l.data.energy
        em.append({'x': round(l.location.x, 3), 'y': round(l.location.z, 3), 'z': round(-l.location.y, 3), 'r': r,
                   'L': round(e / (4 * math.pi * r ** 2) / 60, 2), 'color': [round(v, 3) for v in l.data.color]})
    at = [[round(v, 3) for v in (p.x, p.z, -p.y)] for p in (Vector((0.5, 1.6, 1.2)), Vector((-2.4, 1.2, 1.2)), Vector((2.6, 2.4, 1.4)))]
    return {'capture': {'ceiling': [0.05, 0.035, 0.03], 'walls': [0.42, 0.06, 0.05], 'emitters': em, 'windows': [], 'at': at}}


def person_meta(c):
    work, lo, hi = c['work']
    acts = [{'name': work, 'loop': True, 'min': lo, 'max': hi}]
    for k, (clip, w) in c['idles'].items():
        if k not in c['acts']: continue
        a = {'name': k, 'w': w}
        if k in c.get('cue', {}): a['cue'] = c['cue'][k]
        if FIRST.get(c['who']) == k: a['first'] = True; a['at'] = 0.0
        acts.append(a)
    for k in c['acts']:
        if k != work and not any(a['name'] == k for a in acts): acts.append({'name': k, 'w': 0})
    return {'who': c['who'], 'file': f"{c['who']}.glb", 'acts': acts}


def people_stage(sc, cams, seated, args):
    stages.update_meta(WEB, people=_export_people(seated), **_capture_meta())
    for c, arm, mesh in seated: people.pose_at(arm, c['acts'][c['work'][0]], int(c['acts'][c['work'][0]].frame_range[0]) + 30)
    for which in str(args.get('cams', 'case,close')).split(','):
        preview(sc, cams, which, int(args.get('samples', 64)), os.path.join(OUT, f'people_{which}.png'), size=(1200, 800))
