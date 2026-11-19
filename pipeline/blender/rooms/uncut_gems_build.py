# Uncut Gems: assemble Howard's showroom (the oak photo wall, the pink cases, the counter, the vestibule), its people
# (Howard, Arno, Phil, Nico) and the room's rig (the vestibule's inner door, Howard's phone); then preview, bake and
# export.
import math, os, random
import bpy
from mathutils import Vector, Matrix, Quaternion
import cine, people, stages
from stages import camera
import rooms.uncut_gems as R

ROOM = 'uncut-gems'
OUT = os.path.join(cine.OUT, ROOM)
WEB = os.path.join(cine.ROOT, 'public', 'rooms', ROOM)
PEOPLE_TEX = os.path.join(cine.OUT, 'people')
ARGS = {}
SEATED = []
MATS = {}
RIG = {'lights': []}


def build(args):
    ARGS.clear(); ARGS.update(args)
    sc = cine.reset(int(args.get('samples', 256)))
    M = R.mats(); MATS.update(M)
    static, phantom, crowd = cine.coll('static'), cine.coll('phantom'), cine.coll('people')
    rnd = random.Random(2012)
    seated = [] if args.get('nocast') else cast(crowd, args)
    SEATED[:] = seated
    R.shell(M, static, phantom)
    R.vestibule(M, static)
    recesses = R.cases(M, static, rnd)
    R.counter(M, static, rnd)
    R.photo_wall(M, static, rnd)
    R.armchair(M, static)
    heads = R.tracks(M, static)
    R.models(M, static)
    RIG['lights'] = R.lights(heads, recesses)
    if args.get('nocast'): _static_rig(M, static)
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
            'close': camera('cam_close', (0.4, -7.4, 2.7), (0.2, 0.6, 1.0), 40),
            'master': camera('cam_master', (-0.2, -3.4, 1.6), (0.0, 2.4, 1.2), 64),        # from the front, into the room
            'vest': camera('cam_vest', (0.4, -1.2, 1.5), (3.6, 2.0, 1.1), 50),             # the vestibule from the counter's end
            'cases': camera('cam_cases', (-0.6, -1.6, 1.5), (-4.5, 0.4, 1.3), 56),         # the pink cases, the counter
            'tv': camera('cam_tv', (1.2, -1.0, 1.6), (-3.5, 3.0, 1.7), 46),               # the photo wall and the TV
            'counter': camera('cam_counter', (0.8, -2.6, 1.7), (-2.3, -0.4, 0.95), 40),
            'inside': camera('cam_inside', (2.2, -0.6, 1.5), (3.7, 2.2, 0.9), 46),          # into the vestibule through its door
            'top': camera('cam_top', (0.0, 0.0, 14.0), (0.0, 0.1, 0.0), 38),
            'f_howard': camera('cam_f_howard', (0.3, -0.32, 1.66), (-0.55, -0.55, 1.62), 30),
            'f_arno': camera('cam_f_arno', (-0.3, -0.5, 1.64), (0.55, -0.25, 1.62), 30),
            'f_phil': camera('cam_f_phil', (0.33, -0.56, 1.72), (1.05, -1.1, 1.72), 30),
            'f_nico': camera('cam_f_nico', (0.47, -0.01, 1.66), (1.3, 0.35, 1.64), 30),
            'right': camera('cam_right', (12.0, -6.0, 6.0), (0.5, 0.2, 0.8), 34)}
    return sc, M, objs, list(phantom.objects), seated, cams


def _static_rig(M, col):
    """Without the cast: the rig's parts where they rest (to judge the set)."""
    try: import rooms.uncut_gems_rig as RG
    except ImportError: return
    arm, mesh = RG.make_rig(M, col)
    mesh.parent = None


KEEP = ('left_', 'back_', 'kerb', 'floor', 'subfloor', 'oak_back', 'oak_left', 'oak_front', 'mint_', 'vest_header')


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
    act at those seconds with everyone it cues (and the rig) posed alongside."""
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
# The loop closes with the film's own lock-in. Released, the four stand in the showroom; Arno wants out ("Buzz us
# out"), heads for the vestibule with Phil and Nico; Howard buzzes the inner door, they go in, it shuts behind them,
# and he never buzzes the outer one. Phil tries the building's door, bangs the glass; Arno shouts at the door; Howard
# says he is sorry, phones (Dinah), and sits down on his stool at the counter for the game. The tip, a rebound, he is
# up, at the TV, a hand flat on it; at the glass he taunts Arno; back on the stool; up again, pacing. In the
# vestibule they give up and sit on the floor. The last shot: he wins, runs to the glass and bangs on it ("Arno! I
# did it!"), buzzes them out; they come out to him. Costumes after Miyako Bellizzi (people_textures.uncut_gems).
def _tex(who, prefix, *names):
    return {f'{prefix}_{n}.tga': f'{who}/{prefix}_{n}.png' for n in names}


HEAD = {w: os.path.join(cine.OUT, 'people', w, f'{w}_head.glb') for w in ('howard', 'arno', 'phil', 'nico')}
HEAD_FIT = {                                      # who -> swap_head settings (eyes measured on each sculpt by raycast)
    'howard': dict(front='-y', eyes=((-0.04, -0.23, 0.055), (0.142, -0.23, 0.055)), cut=0.0, fan_cut=-0.12, keep_r=(0.3, 0.3), scalp=(20, 16, 14)),
    'arno': dict(front='-y', eyes=((-0.128, -0.256, 0.077), (0.062, -0.256, 0.074)), cut=0.0, fan_cut=-0.12, keep_r=(0.3, 0.3), scalp=(20, 18, 16)),
    'phil': dict(front='-y', eyes=((-0.0789, -0.245, 0.0118), (0.0899, -0.245, 0.0092)), cut=0.0, fan_cut=-0.12, keep_r=(0.3, 0.3), scalp=(128, 118, 100)),
}
CAST = [
    dict(who='howard', avatar='Male_Adult_06', shape=(('heavy', 0.35),), height=1.77, tex=_tex('howard', 'm011', 'head_color', 'body_color', 'body_normal')),
    dict(who='arno', avatar='Male_Adult_08', shape=(('lean', 1.0),), height=1.76, tex=_tex('arno', 'm014', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
    dict(who='phil', avatar='Business_Male_06', shape=(('lean', 0.8),), height=1.88, tex=_tex('phil', 'm025', 'head_color', 'body_color', 'body_normal')),
    dict(who='nico', avatar='Male_Adult_14', shape=(('heavy', 0.8), ('broad', 0.6)), height=1.80, tex=_tex('nico', 'm012', 'head_color', 'body_color', 'body_normal')),
]
for c in CAST:
    if c['who'] in HEAD_FIT and os.path.exists(HEAD[c['who']]): c['head'] = dict(glb=HEAD[c['who']], **HEAD_FIT[c['who']])
K = {c['who']: c['height'] / 1.78 for c in CAST}
SPINE = ('Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2')
ARMS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('Clavicle', 'UpperArm', 'Forearm', 'Hand'))
LEGS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('Thigh', 'Calf', 'Foot'))
FINGERS = tuple(f'Bip01 {s} Finger{f}{j}' for s in 'LR' for f in '01234' for j in ('', '1', '2'))
ALL = ('Bip01 Pelvis',) + SPINE + ARMS + LEGS + ('Bip01 Neck', 'Bip01 Head')

# where they are (true metres) and which way they face: home is the showroom, after the release (the loop's start)
HOME = {'howard': ((-0.55, -0.55), (1.0, 0.28)), 'arno': ((0.55, -0.25), (-1.0, -0.28)),
        'phil': ((1.05, -1.1), (-0.8, 0.6)), 'nico': ((1.3, 0.35), (-0.92, -0.4))}
BASES = {}
WORK = {w: ('wait', 6, 12) for w in HOME} | {'room': ('rest', 6, 12)}
FIRST = {'howard': 'scene'}
CUE = {'howard': {'scene': {w: 'scene' for w in list(HOME) + ['room'] if w != 'howard'}}}
STOOL = R.STOOLS[0]; STOOL_F = (-0.85, 0.53)
SPOT = dict(buzz=(-1.55, -0.30), call=(-1.35, -1.75), tv=(-2.95, 2.15), glass=(2.12, 1.45), taunt=(2.15, 1.05), pace=(-0.85, 0.35),
            lean=(-1.55, 0.95), a_door=(3.98, 0.12), a_in=(3.22, 1.12), a_sit=(2.92, 1.58), a_glass=(2.82, 1.45),
            p_wait=(3.6, -0.5), p1=(3.92, 2.12), p_od=(3.95, 3.18), p_glass=(3.98, 0.98), p_sit=(4.15, 2.3), p_push=(3.32, 1.0),
            n_wait=(4.25, -0.6), n1=(3.7, 2.92), n_sit=(3.68, 3.22))
TV_C = R.TV.copy()
DOOR_OPEN = -math.radians(95)
TL = dict(arno_go=3.4, phil_go=4.4, nico_go=5.0, howard_go=4.0, buzz=7.0, pull=7.1, door_open=(7.4, 8.4), arno_in=8.7, phil_in=10.4, nico_in=11.3,
          door_shut=(13.4, 14.4), sorry=(14.6, 19.2), grab=19.8, call=(23.6, 33.0), put=35.4, sit=(36.2, 38.6), tip=42.0, up1=(46.0, 48.4),
          cheer1=(48.4, 51.2), at_tv=55.0, touch=(57.2, 60.4), at_glass=66.0, taunt=(66.0, 75.5), sit2=(80.4, 82.8), shoot=(87.5, 89.5),
          up2=(92.0, 94.4), lean=(99.6, 104.0), win=104.0, cheer2=(104.0, 108.6), bang=(112.6, 116.6), buzz2=121.0, door2=(122.4, 123.4),
          phil_out=123.4, arno_out=124.4, nico_out=125.4, door2_shut=(128.8, 129.8), home=128.6,
          p_try=(15.2, 18.2), p_bang=(21.0, 27.0), a_shout=(13.2, 24.5), n_shout=(19.5, 26.5), a_sit=(36.0, 38.6), n_sit=(30.0, 32.6), p_sit=(64.0, 66.6),
          rise=(105.0, 107.6), end=140.0)
DOOR_KEYS = [(0.0, 0.0), (TL['door_open'][0], 0.0), (TL['door_open'][1], DOOR_OPEN), (TL['door_shut'][0], DOOR_OPEN), (TL['door_shut'][1], 0.0),
             (TL['door2'][0], 0.0), (TL['door2'][1], DOOR_OPEN), (TL['door2_shut'][0], DOOR_OPEN), (TL['door2_shut'][1], 0.0), (TL['end'], 0.0)]
REC = {}                                          # who -> {frame: {'head', 'gL', 'gR'}}


def _all(arm, fingers=False):
    return (next(b.name for b in arm.data.bones if b.parent is None),) + ALL + (FINGERS if fingers else ())


def _smooth(x):
    x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)


def _win(t, a, b, rise=0.5, fall=0.5):
    """1 between a and b, eased in and out over rise and fall seconds."""
    return _smooth((t - a) / rise) * (1 - _smooth((t - b) / fall))


def _pulse(t, times, rise=0.05, fall=0.3):
    return max([0.0] + [_smooth((t - s) / rise) * (1 - _smooth((t - s - rise) / fall)) for s in times])


def door_angle(t):
    k = max((i for i, (g, _) in enumerate(DOOR_KEYS) if g <= t), default=0)
    if k + 1 >= len(DOOR_KEYS): return DOOR_KEYS[-1][1]
    (t0, a0), (t1, a1) = DOOR_KEYS[k], DOOR_KEYS[k + 1]
    return a0 + (a1 - a0) * _smooth((t - t0) / max(t1 - t0, 1e-3))


def door_handle(t, side=-1):
    """Where the inner door's bar handle is at t (side -1: the showroom's side, +1 the vestibule's)."""
    w = R.VDOOR[1] - R.VDOOR[0] - 0.01; a = door_angle(t)
    loc = Vector((w - 0.2, side * 0.07, 1.05))
    return Vector((R.VDOOR[0] + 0.005, R.MY0, 0)) + Matrix.Rotation(a, 3, 'Z') @ loc


def _live(arm):
    pb = arm.pose.bones['Bip01 Pelvis']; M = people._world(arm, pb)
    f = M.to_3x3() @ Vector(arm['pel_fwd']); f.z = 0; f.normalize()
    up = Vector((0, 0, 1)); return M.translation.copy(), f, f.cross(up).normalized(), up


def _P(arm, bone):
    return people._world(arm, arm.pose.bones[bone]).translation.copy()


def _look(arm, at, w, limit=1.3, twist=0.0):
    """Head and neck turned toward `at` by w; `twist` shares the turn with the spine (a turn too wide for the neck)."""
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


def _grip(arm, side):
    """A hand's grip frame (world): x along the forearm out through the fist, y toward the palm, z up the thumb."""
    H = _P(arm, f'Bip01 {side} Hand'); F = _P(arm, f'Bip01 {side} Forearm')
    x = (H - F).normalized(); n = people._palm(arm, side)
    y = (n - x * n.dot(x)).normalized()
    if side == 'L': y = -y
    z = x.cross(y)
    c = H + x * 0.07 + (n - x * n.dot(x)).normalized() * 0.015
    return Matrix.Translation(c) @ Matrix(((x.x, y.x, z.x, 0), (x.y, y.y, z.y, 0), (x.z, y.z, z.z, 0), (0, 0, 0, 1)))


def _record(who, arm, f):
    REC.setdefault(who, {})[f] = {'head': _P(arm, 'Bip01 Head'), 'gL': _grip(arm, 'L'), 'gR': _grip(arm, 'R')}


def _rec(who, f, key='head'):
    r = REC.get(who, {})
    if not r: (x, y), _ = HOME[who]; return Vector((x, y, 1.62))
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
    def clip(self, arm, tag, c, p, h, until=None, dur=None, end=False, blend=0.6):
        """A clip at a place: for `dur` seconds (its own length by default) or until a moment; its speed fitted."""
        f0, f1 = c[1]; own = (f1 - f0) / people.FPS
        d = (until - self.t()) if until is not None else (dur or own)
        d = max(0.4, d)
        self.add(tag, src=c[0], f0=f0, dur=d, rate=own / d if dur is None and until is None else 1.0, at=_at(arm, c[0], f1 if end else f0, p, h), blend=blend)
    def log(self, who):
        t = 0.0
        for s in self.segs: s['t0'] = t; t += s['dur']
        cine.log(f'{who} scene: ' + ', '.join(f"{s['tag']} {s['t0']:.1f}" for s in self.segs) + f' end {t:.1f}')
        return t


def _at(arm, src, f, p, h):
    hh, pp = people.heading(arm, src, f); return people.carry(pp, hh, Vector((p[0], p[1], 0)), Vector((h[0], h[1], 0)).normalized())


def _clips(arm, who, names):
    out = {}
    for k, (clip, kw) in names.items(): out[k] = people.retarget(arm, clip, action_name=f'{who}_src_{k}', **kw)
    return out


def _long(arm, who, clip, key, inplace=False):
    """A clip retargeted for the whole scene's length (an idle that never runs out)."""
    n = int(round(TL['end'] * people.FPS)) + 90
    return people.retarget(arm, clip, cycles=80, limit=n, inplace=inplace, action_name=f'{who}_src_{key}')


def _idle(Q, tag, until, idle, p, h, blend=0.7, arm=None):
    """An idle segment at a place until a moment, its clip taken from where the clock is (a long idle never runs out)."""
    f0 = idle[1][0] + int(Q.t() * people.FPS)
    Q.pad(tag, until, src=idle[0], f0=f0, at=_at(arm, idle[0], f0, p, h), blend=blend)


def make_person(c, col):
    """One of them, standing at the origin facing -y: the avatar, its build, its head (the sculpts), its height."""
    tex = {k: os.path.join(PEOPLE_TEX, v) for k, v in c.get('tex', {}).items() if os.path.exists(os.path.join(PEOPLE_TEX, v))}
    arm, mesh = people.load_avatar(c['avatar'], textures=tex, collection=col)
    arm.animation_data_clear()
    mesh['person'] = c['who']; arm['person'] = c['who']
    for sh in c.get('shape', ()): people.reshape(arm, mesh, *sh)
    bpy.context.view_layer.update()
    top = max((mesh.matrix_world @ v.co).z for v in mesh.data.vertices)
    if c.get('head'):
        h = c['head']
        people.swap_head(arm, mesh, h['glb'], None, h['front'], h['eyes'], cut=h['cut'], fan_cut=h['fan_cut'], tone=h.get('tone'), neck_skin=h.get('neck_skin', False), scalp=h.get('scalp'))
        from rooms.rear_window_build import _bust_cut
        _bust_cut(arm, mesh, c['who'], h['keep_r'])
        people.remove_hair_cards(mesh)
    for ca in list(mesh.data.color_attributes): mesh.data.color_attributes.remove(ca)
    s = c['height'] / top
    arm.scale = arm.scale * s; arm.location = (arm.location.x, arm.location.y, arm.location.z * s)
    bpy.context.view_layer.update()
    return arm, mesh


def cast(col, args):
    """Load, dress, shape and place them, and bake their acts (cached: retargets and IK take minutes); the room's rig
    made fresh after (it follows Howard's hand and the door's clock)."""
    full = bool(args.get('full'))
    spec = {'cast': CAST, 'bases': BASES, 'work': WORK, 'cue': CUE, 'tl': TL, 'home': HOME, 'spots': SPOT, 'stool': [list(STOOL), STOOL_F], 'full': full, 'v': 3}
    for c in CAST:
        c['work'] = WORK[c['who']]; c['idles'] = {'scene': (None, 1.0 if c['who'] == 'howard' else 0.0)}; c['cue'] = CUE.get(c['who'], {})
        c['roam'] = ('scene',)
    seated = stages.cast_cache(OUT, CAST, spec, lambda: _make_cast(col, full), col)
    seated += _room_rig(seated, col)
    for c, arm, mesh in seated:
        people.pose_at(arm, c['acts'][c['work'][0]], int(c['acts'][c['work'][0]].frame_range[0]) + 10)
    return seated


def _place(c, arm):
    who = c['who']; (x, y), f = HOME[who]; f = Vector((*f, 0)).normalized()
    people.face(arm, f); arm.location = (x, y, arm.location.z); bpy.context.view_layer.update()
    arm['fwd'] = list(f)
    base, frames, _ = people.retarget(arm, BASES.get(who, 'm_idle_breathe_01'), cycles=2, action_name=f'{who}_base')
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
    for who, fn in (('howard', _howard_acts), ('arno', _arno_acts), ('phil', _phil_acts), ('nico', _nico_acts)):
        for w2, m2 in made.items(): m2['arm'].hide_viewport = w2 != who          # the others out of the depsgraph
        fn(made[who], acts[who], full)
    for m2 in made.values(): m2['arm'].hide_viewport = False
    for who, m in made.items():
        m['c']['acts'] = acts[who]
        if m['base'] not in acts[who].values(): bpy.data.actions.remove(m['base'])
        m['mesh'].hide_viewport = False
        people.pose_at(m['arm'], acts[who][m['c']['work'][0]], int(m['frames'][0]) + 10)
    return seated


# ---------------------------------------------------------------- shared poses
def _floor(arm, k, w, cross=0.0):
    """Sitting on the floor (from a chair clip's pose): the pelvis lowered to the floor, the knees drawn up, the feet
    planted before them, the forearms over the knees, the back a little rounded."""
    if w <= 0: return
    pel, fwd, right, up = _live(arm)
    people.shift_root(arm, (0, 0, (0.13 * k - pel.z) * w))
    pel, fwd, right, up = _live(arm)
    for b_, a in zip(SPINE, (0.08, 0.08, 0.06)): people.bend(arm, b_, right, -a * w)
    for side, sd in (('L', -1), ('R', 1)):
        A0 = _P(arm, f'Bip01 {side} Foot')
        tgt = pel + fwd * 0.44 * k + right * sd * (0.15 - 0.06 * cross) * k
        tgt.z = 0.085 * k
        hip = _P(arm, f'Bip01 {side} Thigh')
        people.ik_leg(arm, side, A0.lerp(tgt, w), hip + fwd * 0.3 + up * 0.7 + right * sd * 0.15, keep_foot=False)
    for side, sd in (('L', -1), ('R', 1)):
        kn = _P(arm, f'Bip01 {side} Calf')
        g = kn + fwd * 0.12 * k + up * 0.03 * k - right * sd * 0.04 * k
        _hand_to(arm, side, g, w, g - up * 0.4 + right * sd * 0.3 - fwd * 0.15, palm=-up * 0.6 - right * sd * 0.4, pw=0.5)
        people.hand_shape(arm, side, 'fist', 0.25 * w)


def _seated_lift(arm, k):
    """How far a chair clip's pelvis must rise to sit on the stool (its seat higher than the clip's 0.52)."""
    return (R.STOOL_SEAT + 0.085 * k) - _P(arm, 'Bip01 Pelvis').z


# ---------------------------------------------------------------- Howard
TV_LOOK = TV_C + Vector((0, 0, -0.05))


def _howard_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS; T = TL
    arno_at = Vector((HOME['arno'][0][0], HOME['arno'][0][1], 1.6))
    def wait(f, t): _look(arm, arno_at, 0.6)
    acts['wait'] = people.custom_act(arm, base, frames, 'howard_wait', wait, _all(arm))
    if not full: return
    C = _clips(arm, 'howard', {'walk': ('m_walk_neutral_01', dict(inplace=True, cycles=14)), 'fast': ('m_walk_fast_01', dict(inplace=True, cycles=8)),
                                'down': ('m_sit_down_chair_01', {}), 'up': ('m_sit_stand_up_chair_01', {}), 'cheer1': ('m_cheer_02', {}), 'cheer2': ('m_cheer_04', {}),
                                'clap': ('m_claphands_01', {}), 'knock': ('m_knock_door', dict(cycles=2)), 'phone': ('m_cell_phone_talk_01', dict(cycles=3))})
    idle = _long(arm, 'howard', 'm_idle_neutral_01', 'idle'); nerv = _long(arm, 'howard', 'm_idle_nervous_01', 'nerv')
    talk = _long(arm, 'howard', 'm_gestic_talk_excited_01', 'talk', inplace=True); angry = _long(arm, 'howard', 'm_gestic_talk_angry_01', 'angry', inplace=True)
    seat = _long(arm, 'howard', 'm_sit_chair_idle_nervous_01', 'seat')
    walk, vs = (C['walk'][0], C['walk'][1]), C['walk'][2]; fast, vf = (C['fast'][0], C['fast'][1]), C['fast'][2]
    # which hand the phone clip holds the phone in (the one up at the head)
    ph = C['phone']; people.pose_at(arm, ph[0], (ph[1][0] + ph[1][1]) // 2)
    H = _P(arm, 'Bip01 Head'); side = min('LR', key=lambda s: (_P(arm, f'Bip01 {s} Hand') - H).length); arm['phone_hand'] = side
    cine.log('howard holds the phone in his', side, 'hand')
    home, hf = HOME['howard']; vest = Vector((3.4, 1.8, 1.4)); I = Matrix.Identity(4)
    Q = Seq()
    Q.pad('talk0', T['howard_go'], src=talk[0], f0=talk[1][0], at=_at(arm, talk[0], talk[1][0], home, hf))
    Q.walk_to(arm, 'w_buzz', walk, vs, [home, (-1.0, -0.42), SPOT['buzz']], T['buzz'] - 0.5)
    _idle(Q, 'buzz', T['sorry'][0], idle, SPOT['buzz'], (-1.0, 0.0), arm=arm)
    Q.pad('sorry', T['grab'] - 0.6, src=talk[0], f0=talk[1][0] + 200, at=_at(arm, talk[0], talk[1][0] + 200, SPOT['buzz'], (0.85, 0.53)))
    _idle(Q, 'grab', T['grab'] + 0.8, idle, SPOT['buzz'], (-1.0, 0.0), arm=arm)
    Q.walk_to(arm, 'w_call', walk, vs, [SPOT['buzz'], (-1.25, -0.9), SPOT['call']], T['call'][0])
    Q.clip(arm, 'call', C['phone'], SPOT['call'], (0.3, -0.95), until=T['call'][1])
    Q.walk_to(arm, 'w_back', walk, vs, [SPOT['call'], (-1.3, -0.9), SPOT['buzz']], T['put'] - 0.8)
    _idle(Q, 'put', T['sit'][0], idle, SPOT['buzz'], (-1.0, 0.0), arm=arm)
    dn = C['down']; Q.clip(arm, 'sit', dn, (STOOL.x, STOOL.y), STOOL_F, dur=T['sit'][1] - T['sit'][0], end=True, blend=0.6)
    Q.segs[-1]['rate'] = (dn[1][1] - dn[1][0]) / FPS / (T['sit'][1] - T['sit'][0])
    sf = lambda: seat[1][0] + int(Q.t() * FPS)
    f0 = sf(); Q.pad('seated1', T['up1'][0], src=seat[0], f0=f0, at=_at(arm, seat[0], f0, (STOOL.x, STOOL.y), STOOL_F))
    up = C['up']; Q.clip(arm, 'up1', up, (STOOL.x, STOOL.y), STOOL_F, dur=T['up1'][1] - T['up1'][0]); Q.segs[-1]['rate'] = (up[1][1] - up[1][0]) / FPS / (T['up1'][1] - T['up1'][0])
    Q.clip(arm, 'cheer1', C['cheer1'], (STOOL.x - 0.1, STOOL.y + 0.25), (-0.55, 0.83), until=T['cheer1'][1])
    Q.walk_to(arm, 'w_tv', walk, vs, [(STOOL.x - 0.1, STOOL.y + 0.25), (-1.45, 1.0), (-1.75, 1.95), SPOT['tv']], T['at_tv'])
    _idle(Q, 'tv', T['touch'][1] + 1.2, angry, SPOT['tv'], (-0.52, 0.85), arm=arm)
    Q.walk_to(arm, 'w_glass', walk, vs, [SPOT['tv'], (-1.8, 1.9), (-0.2, 1.4), (1.2, 1.1), SPOT['taunt']], T['at_glass'])
    Q.pad('taunt', T['taunt'][1], src=talk[0], f0=talk[1][0] + 600, at=_at(arm, talk[0], talk[1][0] + 600, SPOT['taunt'], (1.0, 0.15)))
    Q.walk_to(arm, 'w_stool', walk, vs, [SPOT['taunt'], (0.8, 0.4), (-0.6, -0.1), (STOOL.x + 0.5, STOOL.y - 0.25)], T['sit2'][0] - 1.2)
    _idle(Q, 'turn2', T['sit2'][0], idle, (STOOL.x + 0.5, STOOL.y - 0.25), (-0.85, 0.53), arm=arm)
    Q.clip(arm, 'sit2', dn, (STOOL.x, STOOL.y), STOOL_F, dur=T['sit2'][1] - T['sit2'][0], end=True); Q.segs[-1]['rate'] = (dn[1][1] - dn[1][0]) / FPS / (T['sit2'][1] - T['sit2'][0])
    f0 = sf(); Q.pad('seated2', T['up2'][0], src=seat[0], f0=f0, at=_at(arm, seat[0], f0, (STOOL.x, STOOL.y), STOOL_F))
    Q.clip(arm, 'up2', up, (STOOL.x, STOOL.y), STOOL_F, dur=T['up2'][1] - T['up2'][0]); Q.segs[-1]['rate'] = (up[1][1] - up[1][0]) / FPS / (T['up2'][1] - T['up2'][0])
    Q.walk_to(arm, 'w_pace', walk, vs, [(STOOL.x - 0.1, STOOL.y + 0.3), (-0.9, -0.3), SPOT['pace']], T['up2'][1] + 2.4)
    Q.pad('push', T['lean'][0] - 1.6, src=angry[0], f0=angry[1][0] + 300, at=_at(arm, angry[0], angry[1][0] + 300, SPOT['pace'], (-0.7, 0.72)))
    Q.walk_to(arm, 'w_lean', walk, vs, [SPOT['pace'], SPOT['lean']], T['lean'][0])
    _idle(Q, 'lean', T['win'], nerv, SPOT['lean'], (-1.0, 0.25), arm=arm)
    Q.clip(arm, 'cheer2', C['cheer2'], SPOT['lean'], (-0.7, 0.72), until=T['cheer2'][1])
    Q.walk_to(arm, 'w_bang', fast, vf, [SPOT['lean'], (-0.4, 1.35), (1.2, 1.45), SPOT['glass']], T['bang'][0])
    Q.clip(arm, 'bang', C['knock'], SPOT['glass'], (1.0, 0.0), until=T['bang'][1])
    Q.walk_to(arm, 'w_buzz2', walk, vs, [SPOT['glass'], (0.6, 0.9), (-0.9, -0.1), SPOT['buzz']], T['buzz2'] - 0.4)
    _idle(Q, 'buzz2', T['door2'][1] + 0.4, idle, SPOT['buzz'], (-1.0, 0.0), arm=arm)
    Q.walk_to(arm, 'w_home', walk, vs, [SPOT['buzz'], (-1.0, -0.62), home], T['home'])
    Q.pad('greet', T['end'] - 1.6, src=talk[0], f0=talk[1][0] + 900, at=_at(arm, talk[0], talk[1][0] + 900, home, hf))
    Q.pad('end', T['end'], src=base, f0=frames[0], at=I, blend=1.2)
    Q.log('howard')
    people.pose_at(arm, seat[0], seat[1][0]); lift = {'z': _seated_lift(arm, k)}
    phand = arm['phone_hand']; other = 'L' if phand == 'R' else 'R'
    rim = {'L': Vector((-1.9, -0.72, R.COUNTER_H + 0.03)), 'R': Vector((-1.93, -0.44, R.COUNTER_H + 0.03))}

    def overlay(tt, i, lt):
        tag = Q.segs[i]['tag']; f = int(round(tt * FPS)); dur = Q.segs[i]['dur']
        sw = {'sit': _smooth((lt - 0.6) / 1.4), 'seated1': 1.0, 'seated2': 1.0, 'sit2': _smooth((lt - 0.6) / 1.4),
              'up1': 1 - _smooth(lt / 1.2), 'up2': 1 - _smooth(lt / 1.2)}.get(tag, 0.0)
        if sw > 0: people.shift_root(arm, (0, 0, lift['z'] * sw))
        pel, fwd, right, up_ = _live(arm)
        head = _P(arm, 'Bip01 Head')
        # the phone: picked up at the counter, at his ear through the call and the walks, put back
        if T['grab'] - 0.8 <= tt <= T['put'] + 0.6 and tag != 'call':
            ear = head + right * (0.09 if phand == 'R' else -0.09) * k - up_ * 0.03 * k + fwd * 0.02 * k
            if tt < T['grab']: g, w = R.PHONE + Vector((0, 0, 0.02)), _smooth((tt - (T['grab'] - 0.8)) / 0.7)
            elif tt < T['grab'] + 1.2: g, w = (R.PHONE + Vector((0, 0, 0.02))).lerp(ear, _smooth((tt - T['grab']) / 1.2)), 1.0
            elif tt < T['put'] - 1.0: g, w = ear, 1.0
            elif tt < T['put']: g, w = ear.lerp(R.PHONE + Vector((0, 0, 0.02)), _smooth((tt - (T['put'] - 1.0)) / 1.0)), 1.0
            else: g, w = R.PHONE + Vector((0, 0, 0.02)), 1 - _smooth((tt - T['put']) / 0.6)
            sd = 1 if phand == 'R' else -1
            _hand_to(arm, phand, g, w, pel + right * sd * 0.5 - up_ * 0.3 - fwd * 0.1, palm=-right * sd if g == ear else -up_, pw=0.6)
            people.hand_shape(arm, phand, 'fist', 0.4 * w)
            _look(arm, R.PHONE if tt < T['grab'] + 0.3 or tt > T['put'] - 0.6 else vest, 0.5)
        # the buzzer, twice
        for tb in (T['buzz'], T['buzz2']):
            wb = _win(tt, tb - 0.6, tb + 0.3, 0.5, 0.5)
            if wb > 0:
                _hand_to(arm, 'R', R.BUZZER + Vector((0, 0, 0.03)), wb, R.BUZZER + right * 0.4 - up_ * 0.3, palm=-up_, pw=0.6)
                people.hand_shape(arm, 'R', 'point', wb); _look(arm, vest if tb == T['buzz'] else Vector((3.0, 1.6, 1.5)), 0.6 * wb)
        if tag in ('talk0', 'greet', 'end'):
            _look(arm, _rec('arno', f) if REC.get('arno') else arno_at, 0.7)
        elif tag in ('buzz', 'sorry', 'buzz2', 'w_home'):
            _look(arm, vest, 0.7, twist=0.3)
        elif tag in ('seated1', 'seated2', 'sit', 'sit2'):
            w = sw
            # forearms on the counter's rim, or the hands clasped before his mouth (praying for the tip)
            clasp = _win(tt, T['sit'][1] + 0.5, T['tip'] - 0.3, 0.8, 0.5) + _win(tt, T['sit2'][1] + 4.0, T['shoot'][0] - 0.2, 0.8, 0.4)
            for side_ in 'LR':
                sd = -1 if side_ == 'L' else 1
                g = rim[side_].lerp(head + fwd * 0.2 * k - up_ * 0.12 * k + right * sd * 0.01, min(1.0, clasp))
                _hand_to(arm, side_, g, w, g - up_ * 0.4 + right * sd * 0.35 + fwd * 0.05, palm=(-up_).lerp(-right * sd, min(1.0, clasp)), pw=0.6)
            clapw = _pulse(tt, [T['tip'] + 0.2 * j for j in range(4)], 0.08, 0.12)
            if clapw > 0:                                                        # the tip won: claps, hands meeting before his chest
                for side_ in 'LR':
                    sd = -1 if side_ == 'L' else 1
                    g = pel + fwd * 0.38 * k + up_ * 0.42 * k + right * sd * 0.12 * (1 - clapw) * k
                    _hand_to(arm, side_, g, clapw, g - up_ * 0.3 + right * sd * 0.3, palm=-right * sd, pw=0.7)
            sh = _win(tt, *T['shoot'], 0.3, 0.6)                                  # "Shoot! Shoot!": his right arm at the TV
            if sh > 0: people.point_at(arm, 'R', TV_LOOK, sh, jab=0.05 * math.sin(tt * 12), shape='point')
            _look(arm, TV_LOOK, 0.85 * w, twist=0.25)
        elif tag in ('up1', 'cheer1', 'w_tv', 'w_pace', 'push', 'cheer2', 'lean'):
            _look(arm, TV_LOOK, 0.7, twist=0.2)
            if tag == 'lean':                                                    # both hands on the counter's end, leaning in
                w = _smooth(lt / 0.8)
                for side_ in 'LR':
                    sd = -1 if side_ == 'L' else 1
                    g = Vector((-1.88, 0.95 + sd * 0.2, R.COUNTER_H + 0.02))
                    _hand_to(arm, side_, g, w, g - up_ * 0.3 + right * sd * 0.4 + fwd * 0.1, palm=-up_, pw=0.6)
                for b_, a in zip(SPINE, (0.1, 0.1, 0.06)): people.bend(arm, b_, right, -a * w)
            if tag == 'push':
                people.point_at(arm, 'R', TV_LOOK, _win(lt, 0.6, dur - 0.6, 0.4, 0.4), jab=0.04 * math.sin(tt * 7))
        elif tag == 'tv':
            # pointing at the screen, then a hand flat on it ("the man's feeling the gem")
            wp = _win(tt, T['at_tv'] + 0.4, T['touch'][0] - 0.3, 0.4, 0.4)
            if wp > 0: people.point_at(arm, 'R', TV_LOOK, wp, jab=0.05 * math.sin(tt * 9))
            wt = _win(tt, *T['touch'], 0.6, 0.6)
            if wt > 0:
                g = TV_C + R.TV_F * 0.03 + Vector((0.05, 0, -0.1))
                _hand_to(arm, 'R', g, wt, g - up_ * 0.4 + right * 0.4 - fwd * 0.2, palm=-R.TV_F, pw=0.8)
            _look(arm, TV_LOOK, 0.8)
        elif tag in ('w_glass', 'taunt'):
            a_at = _rec('arno', f) if REC.get('arno') else Vector((SPOT['a_sit'][0], SPOT['a_sit'][1], 0.8))
            _look(arm, a_at, 0.75)
            if tag == 'taunt':
                wp = _win(lt, 2.0, 5.0, 0.4, 0.5) + _win(lt, 7.0, 8.8, 0.3, 0.4)
                if wp > 0: people.point_at(arm, 'R', a_at, min(1.0, wp), jab=0.04 * math.sin(tt * 8))
        elif tag in ('cheer2', 'w_bang'):
            _look(arm, vest, 0.5)
        elif tag == 'bang':
            _look(arm, Vector((SPOT['a_glass'][0], SPOT['a_glass'][1], 1.45)), 0.8)
        elif tag in ('w_stool', 'turn2'):
            _look(arm, TV_LOOK, 0.5)
        _record('howard', arm, f)
    acts['scene'] = people.sequence(arm, base, 'howard_scene', Q.segs, overlay=overlay)
    for a, _, _ in C.values(): bpy.data.actions.remove(a)
    for a in (idle, nerv, talk, angry, seat): bpy.data.actions.remove(a[0])


# ---------------------------------------------------------------- the three in the vestibule
def _howard_at(f):
    return _rec('howard', f)


def _vest_common(arm, who, k, Q, tt, i, lt, sit_tags, rise_tags, sit_end=None):
    """The floor sitting (in and out), the shared looks."""
    tag = Q.segs[i]['tag']; f = int(round(tt * people.FPS))
    if tag in sit_tags:
        w = _smooth((lt - 0.4) / 1.4) if tag == sit_tags[0] else 1.0
        _floor(arm, k, w, cross=0.3 if who == 'nico' else 0.0)
    elif tag in rise_tags:
        _floor(arm, k, 1 - _smooth(lt / 1.2))


def _arno_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS; T = TL
    def wait(f, t): _look(arm, Vector((HOME['howard'][0][0], HOME['howard'][0][1], 1.6)), 0.6)
    acts['wait'] = people.custom_act(arm, base, frames, 'arno_wait', wait, _all(arm))
    if not full: return
    C = _clips(arm, 'arno', {'walk': ('m_walk_neutral_01', dict(inplace=True, cycles=12)), 'cin': ('m_crouch_in', {}), 'cout': ('m_crouch_out', {})})
    idle = _long(arm, 'arno', 'm_idle_angry_01', 'idle'); talk = _long(arm, 'arno', 'm_gestic_talk_angry_01', 'talk', inplace=True)
    exc = _long(arm, 'arno', 'm_gestic_talk_excited_01', 'exc', inplace=True); sitc = _long(arm, 'arno', 'm_sit_chair_idle_look_around', 'sit')
    walk, vs = (C['walk'][0], C['walk'][1]), C['walk'][2]
    home, hf = HOME['arno']; I = Matrix.Identity(4); S_ = SPOT
    Q = Seq()
    Q.pad('talk0', T['arno_go'], src=talk[0], f0=talk[1][0], at=_at(arm, talk[0], talk[1][0], home, hf))
    Q.walk_to(arm, 'w_door', walk, vs, [home, (2.0, -0.3), (3.4, -0.25), S_['a_door']], T['pull'] - 0.5)
    _idle(Q, 'pull', T['arno_in'], idle, S_['a_door'], (-0.55, 0.83), arm=arm)
    Q.walk_to(arm, 'w_in', walk, vs, [S_['a_door'], (3.4, 0.25), (3.3, 0.8), S_['a_in']], T['a_shout'][0])
    Q.pad('shout', T['a_shout'][1], src=talk[0], f0=talk[1][0] + 300, at=_at(arm, talk[0], talk[1][0] + 300, S_['a_in'], (-0.3, -0.95)))
    _idle(Q, 'stew', T['a_sit'][0] - 1.4, idle, S_['a_in'], (-0.5, -0.87), arm=arm)
    Q.walk_to(arm, 'w_sit', walk, vs, [S_['a_in'], S_['a_sit']], T['a_sit'][0])
    ci = C['cin']; Q.clip(arm, 'fold', ci, S_['a_sit'], (-0.5, -0.87), dur=T['a_sit'][1] - T['a_sit'][0], blend=0.4)
    Q.segs[-1]['rate'] = (ci[1][1] - ci[1][0]) / FPS / (T['a_sit'][1] - T['a_sit'][0]) * 0.75
    f0 = sitc[1][0] + int(Q.t() * FPS)
    Q.pad('floor', T['rise'][0], src=sitc[0], f0=f0, at=_at(arm, sitc[0], f0, S_['a_sit'], (-0.5, -0.87)), blend=0.8)
    co = C['cout']; Q.clip(arm, 'rise', co, S_['a_sit'], (-0.5, -0.87), dur=T['rise'][1] - T['rise'][0], blend=0.8)
    Q.segs[-1]['rate'] = (co[1][1] - co[1][0]) / FPS / (T['rise'][1] - T['rise'][0])
    Q.walk_to(arm, 'w_glass', walk, vs, [S_['a_sit'], (2.95, 1.45), S_['a_glass']], T['bang'][0] - 0.6)
    Q.pad('glass', T['arno_out'], src=exc[0], f0=exc[1][0], at=_at(arm, exc[0], exc[1][0], S_['a_glass'], (-1.0, 0.0)))
    Q.walk_to(arm, 'w_out', walk, vs, [S_['a_glass'], (3.2, 1.1), (3.28, 0.5), (2.6, -0.15), (1.5, -0.3), home], T['home'] + 0.6)
    Q.pad('greet', T['end'] - 1.6, src=exc[0], f0=exc[1][0] + 400, at=_at(arm, exc[0], exc[1][0] + 400, home, hf))
    Q.pad('end', T['end'], src=base, f0=frames[0], at=I, blend=1.2)
    Q.log('arno')

    def overlay(tt, i, lt):
        tag = Q.segs[i]['tag']; f = int(round(tt * FPS))
        _vest_common(arm, 'arno', k, Q, tt, i, lt, ('floor',), ('rise',))
        pel, fwd, right, up_ = _live(arm)
        if tag == 'pull':                                                        # his right hand on the door's bar as it swings out
            w = _win(tt, T['pull'], T['door_open'][0] + 0.45, 0.4, 0.5)
            g = door_handle(min(tt, T['door_open'][0] + 0.45), -1)
            _hand_to(arm, 'R', g, w, g - up_ * 0.4 + right * 0.4 - fwd * 0.2, palm=-right, pw=0.6)
            people.hand_shape(arm, 'R', 'fist', 0.6 * w)
            _look(arm, _howard_at(f), 0.5 * (1 - w))
        elif tag in ('talk0', 'greet', 'end', 'shout', 'stew', 'glass', 'w_out'):
            _look(arm, _howard_at(f), 0.75)
            if tag == 'shout':                                                   # a fist on the glass, now and then
                wb = _pulse(tt, (16.0, 18.4, 21.2), 0.1, 0.5)
                if wb > 0:
                    g = Vector((pel.x - 0.05, R.MY0 + 0.04, 1.35))
                    _hand_to(arm, 'R', g, wb, g - up_ * 0.4 + right * 0.4, palm=-fwd, pw=0.5); people.hand_shape(arm, 'R', 'fist', wb)
            if tag == 'glass':                                                  # a hand flat on the glass to Howard's
                wg = _win(tt, T['bang'][0] + 0.2, T['bang'][1] + 1.0, 0.5, 0.6)
                g = Vector((R.MX0 + 0.04, pel.y + 0.05, 1.45))
                _hand_to(arm, 'L', g, wg, g - up_ * 0.4 - right * 0.4, palm=Vector((-1, 0, 0)), pw=0.6)
        elif tag == 'floor':
            hw = _howard_at(f)
            _look(arm, hw if T['taunt'][0] < tt < T['taunt'][1] + 2 or tt > T['win'] - 0.5 else Vector((2.5, -0.5, 1.1)) if (tt % 17) < 9 else TV_LOOK, 0.6)
        _record('arno', arm, f)
    acts['scene'] = people.sequence(arm, base, 'arno_scene', Q.segs, overlay=overlay)
    for a, _, _ in C.values(): bpy.data.actions.remove(a)
    for a in (idle, talk, exc, sitc): bpy.data.actions.remove(a[0])


def _phil_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS; T = TL
    def wait(f, t): _look(arm, Vector((HOME['howard'][0][0], HOME['howard'][0][1], 1.6)), 0.5)
    acts['wait'] = people.custom_act(arm, base, frames, 'phil_wait', wait, _all(arm))
    if not full: return
    C = _clips(arm, 'phil', {'walk': ('m_walk_neutral_01', dict(inplace=True, cycles=12)), 'cin': ('m_crouch_in', {}), 'cout': ('m_crouch_out', {}),
                              'try': ('m_try_door_inwards', {}), 'knock': ('m_knock_door', dict(cycles=3))})
    idle = _long(arm, 'phil', 'm_idle_angry_02', 'idle'); talk = _long(arm, 'phil', 'm_gestic_talk_angry_01', 'talk', inplace=True)
    sitc = _long(arm, 'phil', 'm_sit_chair_breathe_01', 'sit'); calm = _long(arm, 'phil', 'm_idle_neutral_02', 'calm')
    walk, vs = (C['walk'][0], C['walk'][1]), C['walk'][2]
    home, hf = HOME['phil']; I = Matrix.Identity(4); S_ = SPOT; pf = (-0.55, -0.83)
    Q = Seq()
    _idle(Q, 'stand0', T['phil_go'], calm, home, hf, arm=arm)
    Q.walk_to(arm, 'w_wait', walk, vs, [home, (2.3, -0.75), S_['p_wait']], T['phil_go'] + 3.6)
    _idle(Q, 'wait', T['phil_in'], idle, S_['p_wait'], (-0.3, 0.95), arm=arm)
    Q.walk_to(arm, 'w_in', walk, vs, [S_['p_wait'], (3.55, 0.3), (3.62, 0.9), (3.85, 1.6), S_['p_od']], T['p_try'][0])
    Q.clip(arm, 'try', C['try'], S_['p_od'], (0.0, 1.0), until=T['p_try'][1])
    Q.walk_to(arm, 'w_glass', walk, vs, [S_['p_od'], (3.95, 2.0), S_['p_glass']], T['p_bang'][0])
    Q.clip(arm, 'bang', C['knock'], S_['p_glass'], (0.0, -1.0), until=T['p_bang'][1])
    Q.walk_to(arm, 'w_p1', walk, vs, [S_['p_glass'], (3.85, 1.6), S_['p1']], T['p_bang'][1] + 2.6)
    _idle(Q, 'stand', T['p_sit'][0] - 1.0, idle, S_['p1'], pf, arm=arm)
    Q.walk_to(arm, 'w_sit', walk, vs, [S_['p1'], S_['p_sit']], T['p_sit'][0])
    ci = C['cin']; Q.clip(arm, 'fold', ci, S_['p_sit'], pf, dur=T['p_sit'][1] - T['p_sit'][0], blend=0.4)
    Q.segs[-1]['rate'] = (ci[1][1] - ci[1][0]) / FPS / (T['p_sit'][1] - T['p_sit'][0]) * 0.75
    f0 = sitc[1][0] + int(Q.t() * FPS)
    Q.pad('floor', T['rise'][0] + 0.4, src=sitc[0], f0=f0, at=_at(arm, sitc[0], f0, S_['p_sit'], pf), blend=0.8)
    co = C['cout']; Q.clip(arm, 'rise', co, S_['p_sit'], pf, dur=T['rise'][1] - T['rise'][0], blend=0.8)
    Q.segs[-1]['rate'] = (co[1][1] - co[1][0]) / FPS / (T['rise'][1] - T['rise'][0])
    _idle(Q, 'up', T['buzz2'] - 2.0, calm, S_['p_sit'], pf, arm=arm)
    Q.walk_to(arm, 'w_push', walk, vs, [S_['p_sit'], (3.6, 1.6), S_['p_push']], T['buzz2'] + 0.2)
    _idle(Q, 'push', T['phil_out'], idle, S_['p_push'], (0.0, -1.0), arm=arm)
    Q.walk_to(arm, 'w_out', walk, vs, [S_['p_push'], (3.38, 0.3), (2.6, -0.6), (1.8, -1.0), home], T['home'])
    Q.pad('talk', T['end'] - 4.0, src=talk[0], f0=talk[1][0] + 500, at=_at(arm, talk[0], talk[1][0] + 500, home, hf))
    _idle(Q, 'stand1', T['end'] - 1.4, calm, home, hf, arm=arm)
    Q.pad('end', T['end'], src=base, f0=frames[0], at=I, blend=1.0)
    Q.log('phil')

    def overlay(tt, i, lt):
        tag = Q.segs[i]['tag']; f = int(round(tt * FPS))
        _vest_common(arm, 'phil', k, Q, tt, i, lt, ('floor',), ('rise',))
        pel, fwd, right, up_ = _live(arm)
        if tag == 'push':
            w = _win(tt, T['door2'][0] - 0.3, T['door2'][0] + 0.35, 0.3, 0.5)
            g = door_handle(min(tt, T['door2'][0] + 0.35), 1)
            _hand_to(arm, 'R', g, w, g - up_ * 0.4 + right * 0.4 - fwd * 0.2, palm=fwd, pw=0.6)
        elif tag == 'bang':
            g = Vector((pel.x, R.MY0 + 0.05, 1.5))
            wb = _smooth((lt - 0.3) / 0.6)
            _hand_to(arm, 'R', g + Vector((0, 0.05 * abs(math.sin(tt * 5.5)), 0)), wb, g - up_ * 0.4 + right * 0.4, palm=Vector((0, -1, 0)), pw=0.6)
            people.hand_shape(arm, 'R', 'fist', wb)
            _look(arm, _howard_at(f), 0.6)
        elif tag in ('floor', 'stand', 'up', 'wait', 'talk', 'stand1', 'end', 'stand0', 'w_out'):
            _look(arm, TV_LOOK if tag == 'floor' and (tt % 13) < 7 else _howard_at(f), 0.6)
        _record('phil', arm, f)
    acts['scene'] = people.sequence(arm, base, 'phil_scene', Q.segs, overlay=overlay)
    for a, _, _ in C.values(): bpy.data.actions.remove(a)
    for a in (idle, talk, sitc, calm): bpy.data.actions.remove(a[0])


def _nico_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS; T = TL
    def wait(f, t): _look(arm, Vector((HOME['howard'][0][0], HOME['howard'][0][1], 1.6)), 0.5)
    acts['wait'] = people.custom_act(arm, base, frames, 'nico_wait', wait, _all(arm))
    if not full: return
    C = _clips(arm, 'nico', {'walk': ('m_walk_neutral_01', dict(inplace=True, cycles=12)), 'cin': ('m_crouch_in', {}), 'cout': ('m_crouch_out', {})})
    idle = _long(arm, 'nico', 'm_idle_angry_01', 'idle'); talk = _long(arm, 'nico', 'm_gestic_talk_angry_02', 'talk', inplace=True)
    sitc = _long(arm, 'nico', 'm_sit_chair_breathe_01', 'sit'); calm = _long(arm, 'nico', 'm_idle_breathe_01', 'calm')
    walk, vs = (C['walk'][0], C['walk'][1]), C['walk'][2]
    home, hf = HOME['nico']; I = Matrix.Identity(4); S_ = SPOT; nf = (0.0, -1.0)
    Q = Seq()
    _idle(Q, 'stand0', T['nico_go'], calm, home, hf, arm=arm)
    Q.walk_to(arm, 'w_wait', walk, vs, [home, (2.6, -0.1), (3.6, -0.5), S_['n_wait']], T['nico_go'] + 3.8)
    _idle(Q, 'wait', T['nico_in'], idle, S_['n_wait'], (-0.4, 0.9), arm=arm)
    Q.walk_to(arm, 'w_in', walk, vs, [S_['n_wait'], (3.5, 0.3), (3.45, 0.9), (3.6, 1.8), S_['n1']], T['nico_in'] + 2.6)
    _idle(Q, 'stand', T['n_shout'][0], idle, S_['n1'], nf, arm=arm)
    Q.pad('shout', T['n_shout'][1], src=talk[0], f0=talk[1][0] + 200, at=_at(arm, talk[0], talk[1][0] + 200, S_['n1'], (-0.4, -0.92)))
    _idle(Q, 'stand2', T['n_sit'][0] - 0.8, idle, S_['n1'], nf, arm=arm)
    Q.walk_to(arm, 'w_sit', walk, vs, [S_['n1'], S_['n_sit']], T['n_sit'][0])
    ci = C['cin']; Q.clip(arm, 'fold', ci, S_['n_sit'], nf, dur=T['n_sit'][1] - T['n_sit'][0], blend=0.4)
    Q.segs[-1]['rate'] = (ci[1][1] - ci[1][0]) / FPS / (T['n_sit'][1] - T['n_sit'][0]) * 0.75
    f0 = sitc[1][0] + int(Q.t() * FPS)
    Q.pad('floor', T['rise'][0] + 0.8, src=sitc[0], f0=f0, at=_at(arm, sitc[0], f0, S_['n_sit'], nf), blend=0.8)
    co = C['cout']; Q.clip(arm, 'rise', co, S_['n_sit'], nf, dur=T['rise'][1] - T['rise'][0], blend=0.8)
    Q.segs[-1]['rate'] = (co[1][1] - co[1][0]) / FPS / (T['rise'][1] - T['rise'][0])
    _idle(Q, 'up', T['nico_out'], calm, S_['n_sit'], nf, arm=arm)
    Q.walk_to(arm, 'w_out', walk, vs, [S_['n_sit'], (3.55, 1.6), (3.42, 0.9), (3.42, 0.3), (2.6, -0.2), home], T['home'] + 1.8)
    _idle(Q, 'stand1', T['end'] - 1.4, calm, home, hf, arm=arm)
    Q.pad('end', T['end'], src=base, f0=frames[0], at=I, blend=1.0)
    Q.log('nico')

    def overlay(tt, i, lt):
        tag = Q.segs[i]['tag']; f = int(round(tt * FPS))
        _vest_common(arm, 'nico', k, Q, tt, i, lt, ('floor',), ('rise',))
        if tag in ('floor',): _look(arm, _howard_at(f) if (tt % 19) < 11 else TV_LOOK, 0.5)
        elif tag not in ('w_in', 'w_wait', 'w_sit', 'w_out', 'fold', 'rise'): _look(arm, _howard_at(f), 0.6)
        _record('nico', arm, f)
    acts['scene'] = people.sequence(arm, base, 'nico_scene', Q.segs, overlay=overlay)
    for a, _, _ in C.values(): bpy.data.actions.remove(a)
    for a in (idle, talk, sitc, calm): bpy.data.actions.remove(a[0])


# ---------------------------------------------------------------- the room's rig
def _room_rig(seated, col):
    """The rig and its acts: at rest (the door shut, the phone on the counter), and the scene (the door swung by the
    clock, the phone in Howard's hand through his call)."""
    import rooms.uncut_gems_rig as RG
    arm, mesh = RG.make_rig(MATS, col)
    c = dict(who='room', work=WORK['room'], idles={'scene': (None, 0.0)}, cue={}, roam=())
    by = {cc['who']: (cc, a) for cc, a, me in seated}
    FPS = people.FPS; F = lambda s: int(round(s * FPS))
    acts = {'rest': RG.rest_act(arm, 'room_rest')}
    if 'scene' in by['howard'][0]['acts']:
        n = int(round(TL['end'] * FPS))
        ha = by['howard'][1]; act = by['howard'][0]['acts']['scene']; f0 = int(act.frame_range[0]); side = ha.get('phone_hand', 'R')
        hands = {}
        for f in range(F(TL['grab']) - 2, F(TL['put']) + 3):
            people.pose_at(ha, act, f0 + f); hands[f] = _grip(ha, side)
        L = RG.Track(arm, n)
        RG.door_keys(L, [(F(t), a) for t, a in DOOR_KEYS])
        RG.carry(L, 'phone', F(TL['grab']), F(TL['put']), hands, settle=0.3)
        acts['scene'] = L.key('room_scene')
    c['acts'] = acts
    return [(c, arm, mesh)]


# ---------------------------------------------------------------- bake and export
def bake(sc, objs, phantoms, seated, args):
    """The showroom's light baked into atlases (the people and the rig out of it); then room.glb, the people, the rig
    and room.json."""
    os.makedirs(WEB, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    for c, arm, mesh in seated: mesh.hide_render = True
    export, atlases = stages.bake(objs, R.RH, OUT, int(args.get('size', 2048)), int(args.get('samples', 320)))
    for c, arm, mesh in seated: mesh.hide_render = False
    cine.export_glb(export, os.path.join(WEB, 'room.glb'))
    meta = stages.room_meta(R.RH, atlases); meta.update(_capture_meta())
    meta['people'] = _export_people(seated)
    meta['live'] = _live_meta()
    stages.write_meta(WEB, meta)


def _live_meta():
    """What the web's screens follow: the game on the TV keeps Howard's clock (the tip, the win)."""
    return {'game': {'who': 'howard', 'act': 'scene', 'tip': TL['tip'], 'win': TL['win'], 'end': TL['end'], 'pregame': TL['sit'][0]}}


def _export_people(seated):
    out = os.path.join(WEB, 'people'); os.makedirs(out, exist_ok=True); metas = []
    for c, arm, mesh in seated:
        pelvis = 'room_root' if c['who'] == 'room' else 'Bip01 Pelvis'
        people.export_person(arm, mesh, c['acts'], os.path.join(out, f"{c['who']}.glb"), roam=c.get('roam', ()), pelvis=pelvis)
        metas.append(person_meta(c))
    return metas


def _capture_meta():
    """How to light the people as the bake lit the room (three.js: y up, z = -Blender y): the ceiling's LED panels and
    the cone lights as emitters; captured mid-showroom, by the cases and in the vestibule (its cold green)."""
    em = []
    for l in RIG['lights']:
        if l.type != 'LIGHT' or not (l.name.startswith('ceiling') or l.name.startswith('cone') or l.name.startswith('vest_panel')): continue
        r = 0.06 if l.data.type == 'SPOT' else 0.25; e = l.data.energy
        em.append({'x': round(l.location.x, 3), 'y': round(l.location.z, 3), 'z': round(-l.location.y, 3), 'r': r,
                   'L': round(e / (4 * math.pi * r ** 2) / 60, 2), 'color': [round(v, 3) for v in l.data.color]})
    at = [[round(v, 3) for v in (p.x, p.z, -p.y)] for p in (Vector((-0.6, -0.4, 1.2)), Vector((-3.2, 0.0, 1.2)), Vector((3.6, 2.0, 1.2)), Vector((-2.5, 2.3, 1.2)))]
    return {'capture': {'ceiling': [0.7, 0.7, 0.72], 'walls': [0.5, 0.36, 0.24], 'emitters': em, 'windows': [], 'at': at}}


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
    stages.update_meta(WEB, people=_export_people(seated), live=_live_meta(), **_capture_meta())
    for c, arm, mesh in seated: people.pose_at(arm, c['acts'][c['work'][0]], int(c['acts'][c['work'][0]].frame_range[0]) + 30)
    for which in str(args.get('cams', 'case,close')).split(','):
        preview(sc, cams, which, int(args.get('samples', 64)), os.path.join(OUT, f'people_{which}.png'), size=(1200, 800))
