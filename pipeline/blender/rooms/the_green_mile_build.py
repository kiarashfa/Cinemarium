# The Green Mile: assemble E Block (the Mile, the six cells, the desk end, the restraint room's door), its people
# (Paul, Brutal, Dean, Harry, Percy, John Coffey, Delacroix, Bitterbuck) and the block's own rig (the entry door,
# Coffey's cell door, his chains, Percy's baton, the mouse); then preview, bake and export.
import math, os, random
import bpy
from mathutils import Vector, Matrix, Quaternion
import cine, people, stages
from stages import camera
import rooms.the_green_mile as R

ROOM = 'the-green-mile'
OUT = os.path.join(cine.OUT, ROOM)
WEB = os.path.join(cine.ROOT, 'public', 'rooms', ROOM)
PEOPLE_TEX = os.path.join(cine.OUT, 'people')
ARGS = {}
SEATED = []
MATS = {}
RIG = {'lights': []}
S = R.SCALE


def P(x, y, z=0.0):
    return Vector((x, y, z)) * S


def build(args):
    ARGS.clear(); ARGS.update(args)
    sc = cine.reset(int(args.get('samples', 256)))
    M = R.mats(); MATS.update(M)
    static, phantom, crowd = cine.coll('static'), cine.coll('phantom'), cine.coll('people')
    seated = [] if args.get('nocast') else cast(crowd, args)
    SEATED[:] = seated
    rnd = random.Random(1935)
    R.shell(M, static, phantom)
    R.cells(M, static, rnd)
    lamp = R.desk_end(M, static, rnd)
    R.doors(M, static)
    R.windows(M, static)
    bulbs = R.pendants(M, static)
    RIG['lights'] = R.lights(bulbs, lamp)
    if args.get('nocast'): _static_rig(M, static)
    objs = [o for o in static.objects if o.type == 'MESH']; phantoms = [o for o in phantom.objects if o.type == 'MESH']
    bpy.context.view_layer.update()
    cine.bake_ready(objs + phantoms)
    for o in objs + phantoms:
        if not o.data.uv_layers: cine.world_uv(o, 1.0)
        elif 'UVMap' not in o.data.uv_layers: o.data.uv_layers[0].name = 'UVMap'
    R.shrink(objs + phantoms, RIG['lights'])
    cine.bake_ready(objs + phantoms)
    R.section(objs, M)
    objs = _merge(objs)
    for o in phantoms: cine.phantom(o)
    cine.check_module(objs)
    cams = {'case': camera('cam_case', (1.2, -17.5, 7.6), (0.0, 0.4, 0.7), 30),
            'close': camera('cam_close', (0.4, -7.4, 2.9), (0.2, 0.5, 0.8), 40),
            'mile': camera('cam_mile', (3.9, -0.7, 1.15), (-3.6, -0.3, 0.75), 50),       # down the Mile to the desk (the film's master)
            'back': camera('cam_back', (-3.0, -1.2, 1.2), (4.5, 0.2, 0.7), 50),          # from the desk to the restraint room
            'cells': camera('cam_cells', (0.0, -2.6, 1.0), (0.4, 2.2, 0.85), 56),        # the cell fronts
            'desk': camera('cam_desk', (-1.4, -1.0, 1.15), (-3.4, -1.8, 0.6), 54),
            'coffey': camera('cam_coffey', (2.6, -0.6, 1.2), (4.3, 2.3, 0.6), 50),
            'top': camera('cam_top', (0.0, 0.0, 14.0), (0.0, 0.1, 0.0), 38),
            'right': camera('cam_right', (12.0, -6.0, 6.0), (0.5, 0.2, 0.8), 34),
            'f_brutal': camera('cam_f_brutal', (-2.7, -0.95, 1.35), (-3.32, -0.47, 1.25), 34),
            'f_dean': camera('cam_f_dean', (-2.2, -2.0, 1.2), (-3.3, -1.84, 0.95), 34),
            'f_paul': camera('cam_f_paul', (2.8, 0.2, 1.3), (4.05, 0.99, 1.2), 34),
            'f_coffey': camera('cam_f_coffey', (-3.83, 0.0, 1.38), (-4.215, 0.09, 1.38), 46),
            'f_paul2': camera('cam_f_paul2', (3.75, 0.85, 1.42), (4.09, 0.99, 1.4), 40),
            'f_del': camera('cam_f_del', (1.2, -0.3, 1.2), (1.23, 1.8, 1.05), 34)}
    return sc, M, objs, list(phantom.objects), seated, cams


def _static_rig(M, col):
    """Without the cast: the rig's parts where they rest (to judge the set)."""
    try: import rooms.the_green_mile_rig as RG
    except ImportError: return
    arm, mesh = RG.make_rig(M, col)
    mesh.parent = None


KEEP = ('left_wall', 'back_wall', 'end_', 'pass_', 'part_', 'kerb', 'floor', 'subfloor')


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
# Brutal at the entry door, watching the yard through its grille; Dean at the desk; Paul by the open end cell (his
# hands behind his back); Delacroix and Bitterbuck at their bars; behind the end wall, out of sight, Percy and Harry
# with John Coffey in chains. Brutal's `scene` cues everyone's and the room's rig: the door; Percy in first ("Dead man
# walking!"), leading Coffey by his chain, Harry at his side, Brutal and Dean behind; Paul waits in the cell; the head
# shake; Percy's baton; Coffey in; Percy sent off, Del's fingers on the way; Harry takes the irons and the cuffs off;
# Paul's talk, the light, the handshake; Coffey sits; the door shut and locked. Back at the desk the guards watch the
# mouse come up the Mile and take Brutal's crumb, and go back under the restraint room's door. Then Paul and Brutal
# take Coffey out to the yard, Harry with the chains; the door shuts; Paul walks back down to the end cell.
# Costumes after Karyn Wagner (people_textures.the_green_mile); Paul's head is a scan of a wax figure of Tom Hanks,
# Coffey's a head made from a still of Michael Clarke Duncan.
PAUL_HEAD = os.path.join(cine.OUT, 'people', 'paul', 'paul_head.glb')      # rooms/pulp_fiction_heads.py
COFFEY_HEAD = os.path.join(cine.OUT, 'people', 'coffey', 'coffey_head.glb')


def _tex(who, prefix, *names):
    return {f'{prefix}_{n}.tga': f'{who}/{prefix}_{n}.png' for n in names}


CAST = [
    dict(who='brutal', avatar='Business_Male_05', shape=(('broad', 1.0),), height=1.93, cap=True, tex=_tex('brutal', 'm016', 'head_color', 'body_color', 'body_normal')),
    dict(who='paul', avatar='Business_Male_01', shape=(('lean', 0.5),), height=1.83, cap=True,
         head=dict(glb=PAUL_HEAD, front='-y', eyes=((-0.035, -0.172, 0.150), (0.029, -0.172, 0.152)), cut=0.02, fan_cut=0.005),
         tex=_tex('paul', 'm005', 'body_color', 'body_normal')),
    dict(who='dean', avatar='Business_Male_01', shape=(('lean', 1.1),), height=1.80, cap=True, tex=_tex('dean', 'm005', 'head_color', 'body_color', 'body_normal')),
    dict(who='harry', avatar='Business_Male_04', shape=(('lean', 0.7),), height=1.78, cap=True, tex=_tex('harry', 'm015', 'head_color', 'body_color', 'body_normal')),
    dict(who='percy', avatar='Business_Male_03', shape=(('lean', 1.4),), height=1.78, cap=True, tex=_tex('percy', 'm020', 'head_color', 'body_color', 'body_normal')),
    dict(who='coffey', avatar='Male_Adult_06', shape=(('heavy', 1.1), ('athletic', 1.0)), height=1.96,
         head=dict(glb=COFFEY_HEAD, front='-y', eyes=((-0.127, -0.272, 0.149), (0.104, -0.271, 0.144)), cut=0.0, fan_cut=-0.07),   # eyes drawn in 15%: his big head
         tex=_tex('coffey', 'm011', 'head_color', 'body_color', 'body_normal')),
    dict(who='del', avatar='Male_Adult_14', shape=(('lean', 1.6),), height=1.70, tex=_tex('del', 'm012', 'head_color', 'body_color', 'body_normal')),
    dict(who='chief', avatar='Male_Adult_07', shape=(), height=1.80, tex=_tex('chief', 'm013', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
]
K = {c['who']: S * c['height'] / 1.78 for c in CAST}
SPINE = ('Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2')
ARMS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('Clavicle', 'UpperArm', 'Forearm', 'Hand'))
LEGS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('Thigh', 'Calf', 'Foot'))
FINGERS = tuple(f'Bip01 {s} Finger{f}{j}' for s in 'LR' for f in '01234' for j in ('', '1', '2'))
ALL = ('Bip01 Pelvis',) + SPINE + ARMS + LEGS + ('Bip01 Neck', 'Bip01 Head')

# where they are (true metres) and which way they face
CELL_A = R.END_X + R.COFFEY_CELL * R.PITCH + R.PIER / 2           # Coffey's cell front starts here (its door's hinge side)
HOME = {'brutal': ((-4.3, -0.62), (-1.0, 0.0)), 'dean': (tuple(R.DESK_CHAIR), (1.0, 0.0)), 'paul': ((5.45, 1.32), (-1.0, -0.05)),
        'percy': ((-5.5, -0.62), (1.0, 0.0)), 'coffey': ((-5.62, 0.12), (1.0, 0.0)), 'harry': ((-5.58, 0.85), (1.0, 0.0)),
        'del': ((R.cell_mid(R.DEL_CELL), 2.42), (0.0, -1.0)), 'chief': ((R.cell_mid(R.CHIEF_CELL), 2.42), (0.0, -1.0))}
BASES = {'dean': 'm_sit_chair_breathe_01', 'del': 'm_idle_nervous_01'}
WORK = {w: ('wait', 6, 12) for w in HOME} | {'room': ('rest', 6, 12)}
FIRST = {'brutal': 'scene'}
CUE = {'brutal': {'scene': {w: 'scene' for w in list(HOME) + ['room'] if w != 'brutal'}}}
OPEN = {}
SPOT = dict(c1=(4.97, 1.22), c_in=(5.45, 2.45), seat=(5.08, 3.0), sit_from=(5.42, 3.0), p_in=(5.65, 3.55), percy_at=(4.45, 0.55), percy_jab=(4.72, 0.62),
            harry_at=(4.2, 1.48), unchain=(5.05, 1.92), harry_out=(4.0, 1.05), brutal_at=(3.6, 0.55), dean_at=(3.85, -0.05), del_strike=(R.cell_mid(R.DEL_CELL), 1.42),
            brutal_aside=(-4.0, 0.62), close=(4.3, 1.05), paul_out=(4.75, 0.72), paul_desk=(-2.5, -1.15), brutal_desk=(-2.3, -2.85), harry_desk=(-3.0, -3.45),
            open_at=(5.15, 1.35), paul_cell=(4.65, 0.95), harry_door=(-4.35, -0.25), brutal_wait=(-3.6, -1.25), paul_wait=(-3.3, 0.75),
            del_seat=(R.cell_x(R.DEL_CELL)[0] + 0.5, 3.15), del_kneel=(R.cell_mid(R.DEL_CELL), 2.62))
HS = (5.62, 3.02, 1.05)                                           # where Paul's and Coffey's hands meet
PENDANT = (4.9, R.LAMP_Y, R.BULB_Z)                               # the light Paul points at
CHAIN_DESK = (-3.42, -2.95, R.DESK_H + 0.008)
DEL_BARS = 1.28                                                   # the height Del and the Chief hold the bars at
TL = dict(door_open=(3.0, 4.4), door_shut=(10.5, 11.5), percy_go=4.2, coffey_go=5.0, harry_go=6.6, dean_up=6.5, dean_go=9.0, brutal_go=9.6,
          arrive=23.0, paul_in=(17.5, 21.5), del_grin=(15.5, 19.5), talk1=(23.0, 26.5), shake=(25.0, 27.2), beckon=(27.0, 28.6), jab=29.3,
          enter=(30.0, 33.0), turn1=(33.0, 35.0), order=(30.0, 34.2), percy_leave=34.5, percy_at_del=40.5, smash=(41.0, 41.6), yell=(42.0, 44.6),
          percy_door=50.0, door2=(50.3, 51.2), percy_out=53.5, door2_shut=(53.6, 54.6), harry_move=(35.0, 37.0), crouch=(37.0, 38.5), ankles=(38.5, 41.5),
          rise=(41.5, 43.0), wrists=(43.5, 47.0), harry_back=(47.0, 49.5), turn2=(48.0, 50.0), talk2=(50.5, 58.5), ctalk=(59.0, 63.5), point=(64.0, 66.5),
          hand=(67.5, 71.0), to_bunk=(71.5, 73.0), turn3=(73.0, 74.2), sit=(74.2, 76.6), paul_go_out=(74.6, 78.4), brutal_to_close=(74.0, 77.6),
          close=(78.0, 79.5), lock=(79.6, 80.8), head_down=(79.5, 85.0), to_desk=81.0, at_desk=91.5, dean_sit=(91.5, 94.0), put=(92.0, 93.2),
          mouse_out=97.0, mouse_desk=118.0, mouse_sit=(118.0, 120.5), crumb=(119.0, 125.0), mouse_back=125.5, mouse_gone=131.8,
          laugh1=(106.0, 109.0), laugh2=(130.0, 133.0), yard=134.0, pick=(136.0, 137.5), at_cell=143.0, unlock=(144.0, 144.8), open=(144.8, 146.0),
          stand=(145.5, 148.0), out_go=148.0, harry_open=(162.0, 163.2), door3=(162.3, 163.2), harry_through=163.2, coffey_home=167.0,
          door3_shut=(167.0, 168.0), chains_back=167.5, brutal_home=(168.4, 170.5), paul_back=166.0, paul_home=175.5,
          del_hit=41.5, del_kneel=(42.0, 44.5), del_up=(58.0, 60.0), del_sit=(62.0, 64.5), del_rise=(160.0, 162.5), del_bars=166.5,
          end=178.0)
REC = {}                                                          # who -> {frame: {'head', 'gL', 'gR', 'wL', 'wR', 'aL', 'aR', ...}}
HANDS = {c['who'] for c in CAST}


def _all(arm, fingers=False):
    return (next(b.name for b in arm.data.bones if b.parent is None),) + ALL + (FINGERS if fingers else ())


def _smooth(x):
    x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)


def _win(t, a, b, rise=0.5, fall=0.5):
    """1 between a and b, eased in and out over rise and fall seconds."""
    return _smooth((t - a) / rise) * (1 - _smooth((t - b) / fall))


def _pulse(t, times, rise=0.04, fall=0.25):
    return max([0.0] + [_smooth((t - s) / rise) * (1 - _smooth((t - s - rise) / fall)) for s in times])


def _live(arm):
    pb = arm.pose.bones['Bip01 Pelvis']; M = people._world(arm, pb)
    f = M.to_3x3() @ Vector(arm['pel_fwd']); f.z = 0; f.normalize()
    up = Vector((0, 0, 1)); return M.translation.copy(), f, f.cross(up).normalized(), up


def _P(arm, bone):
    return people._world(arm, arm.pose.bones[bone]).translation.copy()


def _look(arm, at, w):
    if w <= 0: return
    H = _P(arm, 'Bip01 Head'); pel, f, right, up = _live(arm)
    d = (Vector(at) - H).normalized()
    yaw = math.atan2(d.dot(-right), d.dot(f)); pitch = math.asin(max(-1, min(1, d.z)))
    yaw = max(-1.3, min(1.3, yaw)); pitch = max(-0.8, min(0.6, pitch))
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
    """Where someone's head, hands, wrists and ankles are at frame f of the scene (for looks, other hands, the rig)."""
    d = {'head': _P(arm, 'Bip01 Head'), 'gL': _grip(arm, 'L'), 'gR': _grip(arm, 'R')}
    for s in 'LR':
        d[f'w{s}'] = (_P(arm, f'Bip01 {s} Hand'), (_P(arm, f'Bip01 {s} Hand') - _P(arm, f'Bip01 {s} Forearm')).normalized())
        d[f'a{s}'] = (_P(arm, f'Bip01 {s} Foot'), (_P(arm, f'Bip01 {s} Foot') - _P(arm, f'Bip01 {s} Calf')).normalized())
    REC.setdefault(who, {})[f] = d


def _rec(who, f, key='head'):
    r = REC.get(who, {})
    if not r: (x, y), _ = HOME[who]; return P(x, y, 1.62)
    return (r.get(f) or r[min(r, key=lambda g: abs(g - f))])[key]


class Seq:
    """A scene's segments, built in order: add() a clip for a fixed time, pad() one until a moment on the clock,
    walk_to() a walk that arrives at a moment (the clip played faster or slower to match)."""
    def __init__(self): self.segs = []
    def t(self): return sum(s['dur'] for s in self.segs)
    def add(self, tag, **kw): kw['tag'] = tag; self.segs.append(kw)
    def pad(self, tag, until, **kw): kw['dur'] = max(0.4, until - self.t()); self.add(tag, **kw)
    def walk_to(self, arm, tag, walk, vs, pts, until, blend=0.6):
        route = people.path([P(*p) for p in pts]); dur = max(0.5, until - self.t()); v = route[1] / dur
        self.add(tag, src=walk[0], f0=walk[1][0], dur=dur, rate=v / vs, at=people.walk_along(arm, walk[0], walk[1][0], v, route), blend=blend)
    def log(self, who):
        t = 0.0
        for s in self.segs: s['t0'] = t; t += s['dur']
        cine.log(f'{who} scene: ' + ', '.join(f"{s['tag']} {s['t0']:.1f}" for s in self.segs) + f' end {t:.1f}')
        return t


def _at(arm, src, f, p, h):
    hh, pp = people.heading(arm, src, f); return people.carry(pp, hh, P(*p), Vector((h[0], h[1], 0)).normalized())


def _clips(arm, who, names):
    out = {}
    for k, (clip, kw) in names.items(): out[k] = people.retarget(arm, clip, action_name=f'{who}_src_{k}', **kw)
    return out


def _idle(S_, tag, until, idle, p, h, blend=0.7):
    """An idle segment at a place until a moment, its clip taken from where the clock is (a long idle never runs out)."""
    f0 = idle[1][0] + int(S_.t() * people.FPS)
    S_.pad(tag, until, src=idle[0], f0=f0, at=_at_cache(idle, f0, p, h), blend=blend)


_ARM = {}


def _at_cache(clip, f0, p, h):
    return _at(_ARM['arm'], clip[0], f0, p, h)


def make_person(c, col):
    """One of them, standing at the origin facing -y: the avatar, its build, its head (the sculpts), its cap, its
    height."""
    tex = {k: os.path.join(PEOPLE_TEX, v) for k, v in c.get('tex', {}).items() if os.path.exists(os.path.join(PEOPLE_TEX, v))}
    arm, mesh = people.load_avatar(c['avatar'], textures=tex, collection=col)
    arm.animation_data_clear()
    mesh['person'] = c['who']; arm['person'] = c['who']
    for sh in c.get('shape', ()): people.reshape(arm, mesh, *sh)
    if c.get('head'):
        h = c['head']
        people.swap_head(arm, mesh, h['glb'], None, h['front'], h['eyes'], cut=h.get('cut', 0.0), fan_cut=h.get('fan_cut', -0.03))
        _bust_collar(arm, mesh, c['who'])
    if c.get('head') or c.get('cap'): people.remove_hair_cards(mesh)
    if c.get('cap'): _guard_cap(arm, mesh)
    for ca in list(mesh.data.color_attributes): mesh.data.color_attributes.remove(ca)
    bpy.context.view_layer.update()
    s = c['height'] / _crown(arm, mesh)
    arm.scale = arm.scale * s; arm.location = (arm.location.x, arm.location.y, arm.location.z * s)
    bpy.context.view_layer.update()
    return arm, mesh


def _crown(arm, mesh):
    """The top of the head itself (not the cap's crown): the highest vertex skinned mostly to the head, cap left out."""
    capm = {i for i, sl in enumerate(mesh.material_slots) if sl.material and sl.material.name.startswith('gm_cap')}
    hz = 0.0
    for poly in mesh.data.polygons:
        if poly.material_index in capm: continue
        for i in poly.vertices: hz = max(hz, (mesh.matrix_world @ mesh.data.vertices[i].co).z)
    return hz


def _bust_collar(arm, mesh, who):
    """The sculpt's bust below the jaw (a shirt, a jacket: unsaturated or pale) cut away; the body's collar is round
    the neck instead."""
    import bmesh
    import numpy as np
    J = people._joints(arm); jaw = J.get('Bip01 MJaw', J['Bip01 Head']).z - 0.02
    k = next((i for i, sl in enumerate(mesh.material_slots) if sl.material and f'{who}_head' in sl.material.name), None)
    if k is None: cine.log('no sculpt material on', who); return
    p = next(n for n in mesh.material_slots[k].material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    im = next(l.from_node.image for l in p.inputs['Base Color'].links if getattr(l.from_node, 'image', None))
    w, h = im.size; px = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(px); px = px.reshape(h, w, 4)[..., :3]
    bm = bmesh.new(); bm.from_mesh(mesh.data); W_ = mesh.matrix_world; uv = bm.loops.layers.uv.active
    dead = []
    for f in bm.faces:
        if f.material_index != k: continue
        q = W_ @ f.calc_center_median()
        if q.z > jaw: continue
        u = sum((l[uv].uv for l in f.loops), Vector((0, 0))) / len(f.loops)
        c = px[int(min(max(u.y, 0), 0.999) * h), int(min(max(u.x, 0), 0.999) * w)]
        r = math.hypot(q.x - J['Bip01 Neck'].x, q.y - J['Bip01 Neck'].y)
        if who == 'coffey':                                           # dark skin in shadow reads unsaturated: cut his bust by distance alone
            dy = q.y - (J['Bip01 Neck'].y - 0.02); rr = math.hypot(q.x - J['Bip01 Neck'].x, dy)
            if q.z < jaw - 0.02 and rr > (0.14 if dy < 0 else 0.088): dead.append(f)
        elif (c.max() - c.min()) / (c.max() + 1e-6) < 0.3 or c.max() > 0.55 or (who == 'paul' and c.max() < 0.26) or (r > 0.115 and q.z < jaw - 0.03): dead.append(f)
    bmesh.ops.delete(bm, geom=dead, context='FACES'); bm.to_mesh(mesh.data); bm.free(); mesh.data.update()
    cine.log(who, 'bust collar cut', len(dead), 'faces')


def _guard_cap(arm, mesh):
    """The guards' peaked cap: a navy crown flaring over a band, a glossy black visor and chin strap, the gilt badge."""
    import bmesh
    cloth = cine.material('gm_cap_navy', (0.011, 0.012, 0.019), rough=0.75, sheen=0.15, sheen_tint=(0.12, 0.12, 0.18))
    gloss = cine.material('gm_cap_visor', (0.01, 0.01, 0.012), rough=0.12, coat=1.0, coat_rough=0.05)
    gold = cine.material('gm_cap_badge', (0.75, 0.56, 0.24), rough=0.3, metal=1.0)
    c, em, J = people._head_frame(arm)
    zb = em.z + 0.045
    base = Vector((c.x, c.y + 0.004, zb))
    seg = 44; bm = bmesh.new(); rings = []
    prof = ((0.094, 0.0), (0.096, 0.035), (0.1, 0.045), (0.128, 0.075), (0.132, 0.09), (0.124, 0.1), (0.07, 0.108), (0.0, 0.11))
    for r, dz in prof:
        ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg; ca, sa = math.cos(a), math.sin(a)
            ry = r * (1.12 if r < 0.11 else 1.08)
            z = dz + (0.012 * (r > 0.11) * (-sa))                               # the crown sits higher at the front
            ring.append(bm.verts.new(base + Vector((ca * r, sa * ry, z))))
        rings.append(ring)
    for A, B in zip(rings, rings[1:]):
        for i in range(seg): bm.faces.new((A[i], A[(i + 1) % seg], B[(i + 1) % seg], B[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces: f.smooth = True
    people._join_to_head(mesh, bm, 'cap_crown', [cloth])
    bm = bmesh.new()                                                          # the band (glossy) round the crown's foot
    lo = [bm.verts.new(base + Vector((math.cos(2 * math.pi * i / seg) * 0.0955, math.sin(2 * math.pi * i / seg) * 0.107, 0.004))) for i in range(seg)]
    hi = [bm.verts.new(base + Vector((math.cos(2 * math.pi * i / seg) * 0.097, math.sin(2 * math.pi * i / seg) * 0.109, 0.03))) for i in range(seg)]
    for i in range(seg): bm.faces.new((lo[i], lo[(i + 1) % seg], hi[(i + 1) % seg], hi[i]))
    # the visor: a half-moon from the band's front, out and down
    vis = []
    for i in range(19):
        a = math.pi + math.pi * i / 18                                        # the front half (-y)
        ca, sa = math.cos(a), math.sin(a)
        inner = base + Vector((ca * 0.094, sa * 0.105, 0.002))
        outer = base + Vector((ca * 0.1, sa * 0.105 - 0.062 * (-sa), -0.022 * (-sa)))
        vis.append((bm.verts.new(inner), bm.verts.new(outer)))
    for (a0, b0), (a1, b1) in zip(vis, vis[1:]): bm.faces.new((a0, a1, b1, b0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    people._join_to_head(mesh, bm, 'cap_visor', [gloss])
    bm = bmesh.new()                                                          # the badge over the band, on the front
    bc = base + Vector((0, -0.118, 0.06)); w, hh = 0.022, 0.03
    vs = [bm.verts.new(bc + Vector((x * w, -0.004 * (1 - abs(x)), z * hh))) for x, z in ((-1, 0.6), (1, 0.6), (0.8, -0.4), (0, -1), (-0.8, -0.4))]
    bm.faces.new(vs)
    people._join_to_head(mesh, bm, 'cap_badge', [gold])


S_ = 1.0


def cast(col, args):
    """Load, dress, shape and place them, and bake their acts (cached: retargets and IK take minutes); the room's rig
    made fresh after (it follows their hands)."""
    full = bool(args.get('full'))
    spec = {'cast': CAST, 'bases': BASES, 'work': WORK, 'cue': CUE, 'tl': TL, 'home': HOME, 'spots': SPOT, 'hs': HS, 'full': full, 'v': 2}
    for c in CAST:
        c['work'] = WORK[c['who']]; c['idles'] = {'scene': (None, 1.0 if c['who'] == 'brutal' else 0.0)}; c['cue'] = CUE.get(c['who'], {})
        c['roam'] = ('scene',)
    seated = stages.cast_cache(OUT, CAST, spec, lambda: _make_cast(col, full), col)
    seated += _room_rig(seated, col)
    for c, arm, mesh in seated:
        people.pose_at(arm, c['acts'][c['work'][0]], int(c['acts'][c['work'][0]].frame_range[0]) + 10)
    return seated


def _place(c, arm):
    """Shrink a person with the room and set them at home facing their way; the base clip retargeted there and slid
    so its pelvis is over the place (a sitter's onto the seat)."""
    who = c['who']; (x, y), f = HOME[who]; f = Vector((*f, 0)).normalized()
    arm.scale = arm.scale * S; arm.location = arm.location * S
    bpy.context.view_layer.update()
    people.face(arm, f); arm.location = (x * S, y * S, arm.location.z); bpy.context.view_layer.update()
    arm['fwd'] = list(f)
    base, frames, _ = people.retarget(arm, BASES.get(who, 'm_idle_breathe_01'), cycles=2, action_name=f'{who}_base')
    people.pose_at(arm, base, frames[0])
    pel = _P(arm, 'Bip01 Pelvis'); want = P(x, y) + (f * 0.03 * S if who == 'dean' else Vector())
    arm.location.x += want.x - pel.x; arm.location.y += want.y - pel.y
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
    order = (('coffey', _coffey_acts), ('percy', _percy_acts), ('harry', _harry_acts), ('paul', _paul_acts), ('brutal', _brutal_acts),
             ('dean', _dean_acts), ('del', _del_acts), ('chief', _chief_acts))
    for who, fn in order:
        for w2, m2 in made.items(): m2['arm'].hide_viewport = w2 != who          # the others out of the depsgraph
        _ARM['arm'] = made[who]['arm']
        fn(made[who], acts[who], full)
    for m2 in made.values(): m2['arm'].hide_viewport = False
    _ARM['arm'] = made['percy']['arm']; _baton(made['percy'], acts['percy'])
    for who, m in made.items():
        m['c']['acts'] = acts[who]
        if m['base'] not in acts[who].values(): bpy.data.actions.remove(m['base'])
        m['mesh'].hide_viewport = False
        people.pose_at(m['arm'], acts[who][m['c']['work'][0]], int(m['frames'][0]) + 10)
    return seated


def _long(arm, who, clip, key):
    """A clip retargeted for the whole scene's length (an idle that never runs out)."""
    n = int(round(TL['end'] * people.FPS)) + 90
    return people.retarget(arm, clip, cycles=80, limit=n, action_name=f'{who}_src_{key}')


def _behind_back(arm, k, w=1.0):
    """Hands clasped behind the back (Paul's way of standing)."""
    if w <= 0: return
    pel, fwd, right, up = _live(arm)
    c = pel - fwd * 0.13 * k + up * 0.03 * k
    for side, sd in (('L', -1), ('R', 1)):
        g = c + right * sd * 0.05 * k
        _hand_to(arm, side, g, w, g - fwd * 0.3 + right * sd * 0.35 - up * 0.1, palm=-fwd, pw=0.5)


# ---------------------------------------------------------------- John Coffey
def _cuffed(arm, k, w=1.0, out=0.0):
    """His hands cuffed together before his belly (held out a little by `out`, for the key)."""
    if w <= 0: return
    pel, fwd, right, up = _live(arm)
    c = pel + fwd * (0.24 + 0.2 * out) * k + up * (0.02 + 0.22 * out) * k
    for side, sd in (('L', -1), ('R', 1)):
        g = c + right * sd * 0.065 * k
        _hand_to(arm, side, g, w, g - up * 0.4 + right * sd * 0.35 - fwd * 0.1, palm=-right * sd, pw=0.7)
        people.hand_shape(arm, side, 'fist', 0.45 * w)


def _coffey_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS; T = TL
    def wait(f, t):
        _cuffed(arm, k); _look(arm, P(-4.75, -0.55, 1.7), 0.3)
    acts['wait'] = people.custom_act(arm, base, frames, 'coffey_wait', wait, _all(arm, fingers=True))
    if not full: return
    C = _clips(arm, 'coffey', {'walk': ('m_walk_slow_01', dict(inplace=True, cycles=24)), 'turn': ('m_turn_left_180', {}), 'turnr': ('m_turn_right_90', {}),
                               'down': ('m_sit_down_chair_01', {}), 'up': ('m_sit_stand_up_chair_01', {}), 'talk': ('m_gestic_talk_neutral_01', dict(cycles=2))})
    idle = _long(arm, 'coffey', 'm_idle_breathe_02', 'idle'); sit = _long(arm, 'coffey', 'm_sit_chair_breathe_01', 'sit')
    walk, vs = (C['walk'][0], C['walk'][1]), C['walk'][2]
    home, hf = HOME['coffey']
    Q = Seq(); I = Matrix.Identity(4)
    Q.pad('home', T['coffey_go'], src=base, f0=frames[0], at=I)
    path_in = [home, (-5.3, -0.35), (-4.75, -0.55), (-4.0, -0.3), (-2.6, 0.25), (0.0, 0.6), (2.6, 0.75), (4.1, 0.95), SPOT['c1']]
    Q.walk_to(arm, 'in', walk, vs, path_in, T['arrive'])
    _idle(Q, 'stand', T['enter'][0], idle, SPOT['c1'], (0, 1), blend=1.0)
    Q.walk_to(arm, 'enter', walk, vs, [SPOT['c1'], (4.98, 1.95), (5.3, 2.3), SPOT['c_in']], T['enter'][1])
    tn = C['turn']; Q.add('turn1', src=tn[0], f0=tn[1][0], dur=T['turn1'][1] - T['turn1'][0], rate=(tn[1][1] - tn[1][0]) / FPS / (T['turn1'][1] - T['turn1'][0]),
                          at=_at(arm, tn[0], tn[1][0], SPOT['c_in'], (0, 1)), blend=0.6)
    _idle(Q, 'key', T['turn2'][0], idle, SPOT['c_in'], (0, -1), blend=0.6)
    Q.add('turn2', src=tn[0], f0=tn[1][0], dur=T['turn2'][1] - T['turn2'][0], rate=(tn[1][1] - tn[1][0]) / FPS / (T['turn2'][1] - T['turn2'][0]),
          at=_at(arm, tn[0], tn[1][0], SPOT['c_in'], (0, -1)), blend=0.6)
    _idle(Q, 'listen', T['ctalk'][0], idle, SPOT['c_in'], (0, 1), blend=0.6)
    tk = C['talk']; Q.pad('ask', T['ctalk'][1], src=tk[0], f0=tk[1][0], at=_at(arm, tk[0], tk[1][0], SPOT['c_in'], (0, 1)), blend=0.8)
    _idle(Q, 'shake', T['to_bunk'][0], idle, SPOT['c_in'], (0, 1), blend=0.8)
    Q.walk_to(arm, 'to_bunk', walk, vs, [SPOT['c_in'], (5.45, 2.75), SPOT['sit_from']], T['to_bunk'][1])
    tr = C['turnr']; Q.add('turn3', src=tr[0], f0=tr[1][0], dur=T['turn3'][1] - T['turn3'][0], rate=(tr[1][1] - tr[1][0]) / FPS / (T['turn3'][1] - T['turn3'][0]),
                           at=_at(arm, tr[0], tr[1][0], SPOT['sit_from'], (0, 1)), blend=0.5)
    dn = C['down']; Q.add('sit', src=dn[0], f0=dn[1][0], dur=T['sit'][1] - T['sit'][0], rate=(dn[1][1] - dn[1][0]) / FPS / (T['sit'][1] - T['sit'][0]),
                          at=_at(arm, dn[0], dn[1][1], SPOT['seat'], (1, 0)), blend=0.5)
    sf0 = sit[1][0] + int(Q.t() * FPS)
    Q.pad('seated', T['stand'][0], src=sit[0], f0=sf0, at=_at(arm, sit[0], sf0, SPOT['seat'], (1, 0)), blend=0.6)
    up = C['up']; Q.add('up', src=up[0], f0=up[1][0], dur=T['stand'][1] - T['stand'][0], rate=(up[1][1] - up[1][0]) / FPS / (T['stand'][1] - T['stand'][0]),
                        at=_at(arm, up[0], up[1][0], SPOT['seat'], (1, 0)), blend=0.6)
    path_out = [(5.4, 3.0), (5.5, 2.5), (5.0, 1.9), SPOT['c1'], (4.1, 0.9), (2.6, 0.7), (0.0, 0.55), (-2.6, 0.2), (-4.0, -0.3), (-4.75, -0.55), (-5.3, -0.3), (-5.72, 0.05)]
    Q.walk_to(arm, 'out', walk, vs, path_out, T['coffey_home'])
    Q.add('turn4', src=tn[0], f0=tn[1][0], dur=2.0, rate=(tn[1][1] - tn[1][0]) / FPS / 2.0, at=_at(arm, tn[0], tn[1][0], home, (-1, 0)), blend=0.6)
    Q.pad('home2', T['end'], src=base, f0=frames[0] + 20, at=I, blend=1.0)
    Q.log('coffey')
    # the seat's height: the chair clip's pelvis lowered or raised onto the bunk (its mattress at 0.575)
    people.pose_at(arm, sit[0], sit[1][0])
    drop = {'z': (0.575 * S + 0.09 * k * 1.78 / 1.75) - _P(arm, 'Bip01 Pelvis').z}
    cine.log(f"coffey on the bunk: raised {drop['z'] / S:+.3f} (true m)")

    def overlay(tt, i, lt):
        tag = Q.segs[i]['tag']; f = int(round(tt * FPS))
        if tag in ('sit', 'seated', 'up'):
            dz = drop['z']
            w = {'seated': 1.0, 'sit': _smooth((lt - 1.2) / 1.0), 'up': 1 - _smooth(lt / 1.0)}[tag]
            people.shift_root(arm, (0, 0, dz * w))
        pel, fwd, right, up_ = _live(arm)
        chained = tt < T['wrists'][1] - 0.2 or tt > T['chains_back']
        out = _win(tt, T['wrists'][0] - 0.3, T['wrists'][1], 0.5, 0.6) if tt < T['chains_back'] else 0.0
        if chained or out > 0: _cuffed(arm, k, 1.0, out)
        x = pel.x / S
        duck = _smooth(1 - abs(x - (-4.75)) / 0.55)                            # under the low doorway
        if duck > 0:
            for b_, a in zip(SPINE, (0.12, 0.14, 0.12)): people.bend(arm, b_, right, -a * duck)
            people.bend(arm, 'Bip01 Head', right, -0.25 * duck)
        if tag == 'stand':
            sh = _win(tt, *T['shake'], 0.3, 0.3)
            if sh > 0: people.bend(arm, 'Bip01 Head', up_, 0.22 * math.sin((tt - T['shake'][0]) * 7.5) * sh)
            fl = _pulse(tt, (T['jab'],), 0.05, 0.4)
            for b_ in SPINE: people.bend(arm, b_, right, 0.07 * fl)
            _look(arm, P(5.6, 3.2, 1.75) if tt < T['jab'] else P(4.6, 0.6, 1.6), 0.5)
        elif tag in ('home', 'in'):
            _look(arm, pel + fwd * 2.0 + Vector((0, 0, 1.1 * S)) - up_ * 0.15, 0.3)
        elif tag == 'key':
            _look(arm, P(5.05, 1.9, 0.9 if tt < T['rise'][1] else 1.35), 0.5)
        elif tag in ('listen', 'ask', 'shake'):
            _look(arm, P(5.65, 3.55, 1.72), 0.6)
            if tag == 'listen' and T['point'][0] < tt < T['point'][1] + 0.5: _look(arm, P(*PENDANT), 0.6)
            hw = _win(tt, *T['hand'], 0.7, 0.7)
            if hw > 0:
                pump = Vector((0, 0, 0.03 * math.sin((tt - T['hand'][0]) * 6) * _win(tt, T['hand'][0] + 0.9, T['hand'][1] - 0.6, 0.3, 0.3)))
                g = P(*HS) + pump
                _hand_to(arm, 'R', g, hw, g - up_ * 0.4 + right * 0.35 - fwd * 0.2, palm=-right, pw=0.7)
                people.hand_shape(arm, 'R', 'fist', 0.4 * hw)
        elif tag in ('seated', 'sit'):
            for side, sd in (('L', -1), ('R', 1)):                             # hands clasped between his knees
                g = pel + fwd * 0.34 * k - up_ * 0.06 * k + right * sd * 0.02 * k
                _hand_to(arm, side, g, 1.0 if tag == 'seated' else _smooth((lt - 1.4) / 0.8), g - up_ * 0.3 + right * sd * 0.4, palm=-right * sd, pw=0.6)
            hd = _win(tt, *T['head_down'], 0.8, 1.2)
            mouse = _mouse_at(tt)
            if mouse and T['mouse_out'] < tt < T['mouse_gone']: _look(arm, P(mouse[0], mouse[1], 0.05), 0.6)
            elif tt < T['to_desk'] + 6: _look(arm, P(4.8, 1.0, 1.7), 0.4 * (1 - hd))
            for b_ in SPINE: people.bend(arm, b_, right, -0.08)
            if hd > 0: people.bend(arm, 'Bip01 Head', right, -0.35 * hd)
        elif tag == 'out':
            _look(arm, pel + fwd * 2.0 + Vector((0, 0, 1.2 * S)), 0.3)
        _record('coffey', arm, f)
    acts['scene'] = people.sequence(arm, base, 'coffey_scene', Q.segs, overlay=overlay)
    for a, _, _ in C.values(): bpy.data.actions.remove(a)
    for a in (idle, sit): bpy.data.actions.remove(a[0])


# ---------------------------------------------------------------- the mouse's way (true metres)
MOUSE_KEYS = [(97.0, (5.9, -0.64)), (98.5, (5.2, -0.2)), (99.7, (5.2, -0.2)), (101.2, (4.2, 0.9)), (102.6, (4.2, 0.9)), (104.4, (2.9, 1.0)),
              (105.6, (2.9, 1.0)), (107.4, (1.6, 1.05)), (108.8, (1.6, 1.05)), (110.6, (0.2, 1.0)), (111.6, (0.2, 1.0)), (113.4, (-1.3, 0.6)),
              (114.4, (-1.3, 0.6)), (116.3, (-2.2, -0.8)), (118.0, (-2.6, -2.05)), (121.0, (-2.56, -2.18)), (125.5, (-2.56, -2.18)),
              (127.0, (-2.0, -1.2)), (129.0, (1.0, -0.6)), (131.3, (4.5, -0.6)), (131.8, (5.95, -0.64))]


def _mouse_at(t):
    """Where the mouse is at second t of the scene: (x, y, heading, moving), or None while it is out of sight."""
    if t < MOUSE_KEYS[0][0] or t > MOUSE_KEYS[-1][0]: return None
    for (t0, a), (t1, b) in zip(MOUSE_KEYS, MOUSE_KEYS[1:]):
        if t0 <= t <= t1:
            u = (t - t0) / max(t1 - t0, 1e-6); u = u * u * (3 - 2 * u)
            d = Vector(b) - Vector(a); mv = d.length > 1e-4
            return (a[0] + d.x * u, a[1] + d.y * u, math.atan2(d.y, d.x) if mv else None, mv)
    return None


# ---------------------------------------------------------------- Percy
def _percy_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS; T = TL
    def wait(f, t):
        pel, fwd, right, up = _live(arm); g = pel + right * 0.22 * k - up * 0.02 * k + fwd * 0.05 * k
        _hand_to(arm, 'R', g, 1.0, g + right * 0.3 - fwd * 0.2, palm=-right, pw=0.6); people.hand_shape(arm, 'R', 'fist', 0.85)
        _look(arm, P(-4.75, -0.55, 1.5), 0.3)
    acts['wait'] = people.custom_act(arm, base, frames, 'percy_wait', wait, _all(arm, fingers=True))
    m['wait_fn'] = wait
    if not full: return
    C = _clips(arm, 'percy', {'walk': ('m_walk_cool_01', dict(inplace=True, cycles=16)), 'turn': ('m_turn_left_180', {}), 'talk': ('m_gestic_talk_cool', dict(cycles=4))})
    idle = _long(arm, 'percy', 'm_idle_nervous_01', 'idle')
    walk, vs = (C['walk'][0], C['walk'][1]), C['walk'][2]
    home, hf = HOME['percy']
    Q = Seq(); I = Matrix.Identity(4)
    Q.pad('home', T['percy_go'], src=base, f0=frames[0], at=I)
    Q.walk_to(arm, 'lead', walk, vs, [home, (-4.75, -0.6), (-3.7, -0.6), (-2.2, -0.25), (0.4, 0.05), (2.9, 0.25), (4.1, 0.45), SPOT['percy_at']], T['arrive'] - 0.4)
    _idle(Q, 'stand', 27.5, idle, SPOT['percy_at'], (0.6, 0.8), blend=0.8)
    Q.walk_to(arm, 'closer', walk, vs, [SPOT['percy_at'], SPOT['percy_jab']], 28.5)
    _idle(Q, 'jab', T['percy_leave'], idle, SPOT['percy_jab'], (0.45, 0.9), blend=0.6)
    Q.walk_to(arm, 'leave', walk, vs, [SPOT['percy_jab'], (4.2, 0.4), (2.6, 0.9), SPOT['del_strike']], T['percy_at_del'])
    _idle(Q, 'strike', T['yell'][0] + 0.3, idle, SPOT['del_strike'], (0, 1), blend=0.6)
    Q.walk_to(arm, 'to_door', walk, vs, [SPOT['del_strike'], (0.6, 0.9), (-2.0, -0.1), (-3.8, -0.55), (-4.3, -0.55)], T['percy_door'])
    _idle(Q, 'door', T['door2'][1], idle, (-4.3, -0.55), (-1, 0), blend=0.5)
    Q.walk_to(arm, 'out', walk, vs, [(-4.3, -0.55), (-4.85, -0.5), (-5.45, -0.42), (-5.72, -0.62)], T['percy_out'])
    tn = C['turn']; Q.add('turn', src=tn[0], f0=tn[1][0], dur=2.0, rate=(tn[1][1] - tn[1][0]) / FPS / 2.0, at=_at(arm, tn[0], tn[1][0], home, (-1, 0)), blend=0.6)
    Q.pad('home2', T['end'], src=base, f0=frames[0] + 20, at=I, blend=1.0)
    Q.log('percy')
    cuffs = lambda f: (_rec('coffey', f, 'wL')[0] + _rec('coffey', f, 'wR')[0]) / 2
    handle = lambda a: (Vector(ENTRY_H) + Matrix.Rotation(a, 3, 'Z') @ Vector((0, 0.86 * S, 0)))

    def overlay(tt, i, lt):
        tag = Q.segs[i]['tag']; f = int(round(tt * FPS))
        pel, fwd, right, up = _live(arm)
        held = pel + right * 0.22 * k - up * 0.02 * k + fwd * 0.05 * k                # the baton held low by his right side
        if tag in ('home', 'home2', 'turn'):
            wait(f, tt)
        if tag == 'lead':
            # the left hand on the chain back to Coffey's cuffs; the baton up and waved as he hollers
            if tt > T['coffey_go'] + 0.4:
                cf = cuffs(f); sh = _P(arm, 'Bip01 L UpperArm'); g = sh + (cf - sh).normalized() * 0.42 * k
                _hand_to(arm, 'L', g, _smooth((tt - T['coffey_go'] - 0.4) / 0.6), g - up * 0.3 - right * 0.3, palm=right, pw=0.4)
                people.hand_shape(arm, 'L', 'fist', 0.8)
            holler = max(0.0, math.sin((tt - T['percy_go']) * 2 * math.pi / 3.2)) ** 0.6 * _win(tt, T['percy_go'] + 0.6, T['arrive'] - 1.0, 0.4, 0.6)
            g = held.lerp(pel + right * 0.26 * k + up * 0.75 * k + fwd * 0.12 * k, holler)
            _hand_to(arm, 'R', g, 1.0, g + right * 0.4 - fwd * 0.2, palm=-right, pw=0.5); people.hand_shape(arm, 'R', 'fist', 0.85)
            people.bend(arm, 'Bip01 Head', right, 0.12 * holler)
            _look(arm, pel + fwd * 2.0 + Vector((0, 0, 1.0 * S)), 0.3)
        elif tag in ('stand', 'closer', 'jab'):
            slap = _win(tt, 24.0, 28.8, 0.6, 0.6) * (0.5 + 0.5 * math.sin(tt * 7))
            jab = _win(tt, T['jab'] - 0.35, T['jab'] + 0.15, 0.2, 0.4)
            back = Vector(_rec('coffey', f, 'head')); back = Vector((back.x, back.y - 0.18 * S, 1.05 * S))
            g = held.lerp(pel + fwd * 0.3 * k + up * 0.25 * k + right * 0.1 * k, max(slap * 0.8, 0.0))
            g = g.lerp(back, jab * 0.9)
            _hand_to(arm, 'R', g, 1.0, g + right * 0.35 - up * 0.3, palm=-right, pw=0.5); people.hand_shape(arm, 'R', 'fist', 0.85)
            if slap > 0.05:
                gl = pel + fwd * 0.3 * k + up * 0.22 * k - right * 0.04 * k
                _hand_to(arm, 'L', gl, _win(tt, 24.0, 28.8, 0.6, 0.6), gl - up * 0.3 - right * 0.3, palm=up, pw=0.5)
            _look(arm, P(5.65, 3.55, 1.7) if T['order'][0] < tt < T['order'][1] else _rec('coffey', f), 0.6)
        elif tag in ('leave', 'to_door'):
            _hand_to(arm, 'R', held, 1.0, held + right * 0.3 - fwd * 0.2, palm=-right, pw=0.5); people.hand_shape(arm, 'R', 'fist', 0.85)
            if tag == 'leave' and tt > T['percy_at_del'] - 2.0: _look(arm, P(SPOT['del_strike'][0], 2.4, 1.5), 0.6)
        elif tag == 'strike':
            bars = P(SPOT['del_strike'][0], 2.0, DEL_BARS)
            raise_ = _win(tt, T['smash'][0] - 0.6, T['smash'][0], 0.4, 0.15)
            hit = _win(tt, T['smash'][0], T['smash'][1], 0.12, 0.4)
            g = held.lerp(pel + right * 0.15 * k + up * 0.85 * k + fwd * 0.05 * k, raise_).lerp(bars - Vector((0, 0.32 * S, 0)), hit)
            _hand_to(arm, 'R', g, 1.0, g + right * 0.35 - up * 0.3, palm=-right, pw=0.5); people.hand_shape(arm, 'R', 'fist', 0.85)
            for b_ in SPINE: people.bend(arm, b_, right, -0.1 * hit)
            _look(arm, bars, 0.7)
        elif tag == 'door':
            a = math.radians(95) * _smooth((tt - T['door2'][0]) / (T['door2'][1] - T['door2'][0]))
            g = handle(a); w = _win(tt, T['door2'][0] - 0.5, T['door2'][0] + 0.6, 0.3, 0.3)
            _hand_to(arm, 'L', g, w, g - up * 0.3 - right * 0.3)
            _hand_to(arm, 'R', held, 1.0, held + right * 0.3 - fwd * 0.2, palm=-right, pw=0.5); people.hand_shape(arm, 'R', 'fist', 0.85)
        elif tag == 'out':
            _hand_to(arm, 'R', held, 1.0, held + right * 0.3 - fwd * 0.2, palm=-right, pw=0.5); people.hand_shape(arm, 'R', 'fist', 0.85)
        _record('percy', arm, f)
    acts['scene'] = people.sequence(arm, base, 'percy_scene', Q.segs, overlay=overlay)
    for a, _, _ in C.values(): bpy.data.actions.remove(a)
    bpy.data.actions.remove(idle[0])


ENTRY_H = tuple(P(R.END_X - 0.05, R.ENTRY[0] + 0.02, 1.02))      # the entry door's hinge at its handle's height (the handle swings about it)


def _baton(m, acts):
    """Percy's hickory baton, made in his right fist as his waiting pose holds it and skinned to that hand."""
    import bmesh
    arm, mesh, k = m['arm'], m['mesh'], m['k']
    people.pose_at(arm, acts['wait'], int(acts['wait'].frame_range[0]))
    G = _grip(arm, 'R')
    wood = cine.material('gm_baton_hickory', (0.34, 0.2, 0.1), rough=0.35, coat=0.6, coat_rough=0.2)
    bm = bmesh.new(); seg = 10; L0, L1 = -0.1, 0.5                                # along the grip's z (out of the thumb's side)
    rings = []
    for z, r in ((L0, 0.014), (L0 + 0.01, 0.017), (0.04, 0.016), (0.2, 0.017), (L1 - 0.02, 0.019), (L1, 0.012)):
        rings.append([bm.verts.new(G @ (Vector((math.cos(2 * math.pi * i / seg) * r, math.sin(2 * math.pi * i / seg) * r, z)) * S)) for i in range(seg)])
    for A, B in zip(rings, rings[1:]):
        for i in range(seg): bm.faces.new((A[i], A[(i + 1) % seg], B[(i + 1) % seg], B[i]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    A = arm.matrix_world; pb = arm.pose.bones['Bip01 R Hand']
    bm.transform(mesh.matrix_world.inverted() @ A @ pb.bone.matrix_local @ pb.matrix.inverted() @ A.inverted())
    me = bpy.data.meshes.new('baton'); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new('baton', me); [c.objects.link(ob) for c in mesh.users_collection]; me.materials.append(wood)
    ob.matrix_world = mesh.matrix_world.copy()
    vg = ob.vertex_groups.new(name='Bip01 R Hand'); vg.add(list(range(len(me.vertices))), 1.0, 'REPLACE')
    hidden = mesh.hide_viewport; mesh.hide_viewport = False; people._joined(mesh, ob); mesh.hide_viewport = hidden
    cine.log('baton in percy hand')


# ---------------------------------------------------------------- Harry
def _carry(arm, k, wl, wr):
    """The chains carried at his sides (the irons in his left hand, the cuffs in his right)."""
    pel, fwd, right, up = _live(arm)
    for side, sd, w in (('L', -1, wl), ('R', 1, wr)):
        if w <= 0: continue
        g = pel + right * sd * 0.24 * k - up * 0.04 * k + fwd * 0.06 * k
        _hand_to(arm, side, g, w, g + right * sd * 0.3 - fwd * 0.2, palm=-right * sd, pw=0.5)
        people.hand_shape(arm, side, 'fist', 0.85 * w)


def _harry_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS; T = TL
    def wait(f, t):
        _carry(arm, k, 0.0, 0.0); _look(arm, P(-4.75, -0.55, 1.5), 0.25)
    acts['wait'] = people.custom_act(arm, base, frames, 'harry_wait', wait, _all(arm, fingers=True))
    if not full: return
    C = _clips(arm, 'harry', {'walk': ('m_walk_neutral_01', dict(inplace=True, cycles=18)), 'cin': ('m_crouch_in', {}), 'cid': ('m_crouch_idle', dict(cycles=2)),
                              'cout': ('m_crouch_out', {}), 'turnr': ('m_turn_right_90', {})})
    idle = _long(arm, 'harry', 'm_idle_breathe_01', 'idle')
    walk, vs = (C['walk'][0], C['walk'][1]), C['walk'][2]
    home, hf = HOME['harry']
    Q = Seq(); I = Matrix.Identity(4)
    Q.pad('home', T['harry_go'], src=base, f0=frames[0], at=I)
    Q.walk_to(arm, 'in', walk, vs, [home, (-5.35, 0.0), (-4.75, -0.45), (-3.9, 0.3), (-2.4, 0.95), (0.0, 1.2), (2.6, 1.3), (3.95, 1.42), SPOT['harry_at']], T['arrive'] + 0.2)
    _idle(Q, 'stand', T['harry_move'][0], idle, SPOT['harry_at'], (0.8, -0.2), blend=0.8)
    Q.walk_to(arm, 'move', walk, vs, [SPOT['harry_at'], (4.25, 1.1), (4.75, 1.1), SPOT['unchain']], T['harry_move'][1])
    ci = C['cin']; Q.add('crouch', src=ci[0], f0=ci[1][0], dur=T['crouch'][1] - T['crouch'][0], rate=(ci[1][1] - ci[1][0]) / FPS / (T['crouch'][1] - T['crouch'][0]),
                         at=_at(arm, ci[0], ci[1][0], SPOT['unchain'], (0.55, 0.83)), blend=0.5)
    Q.pad('ankles', T['rise'][0], src=C['cid'][0], f0=C['cid'][1][0], at=_at(arm, C['cid'][0], C['cid'][1][0], SPOT['unchain'], (0.55, 0.83)), blend=0.4)
    co = C['cout']; Q.add('rise', src=co[0], f0=co[1][0], dur=T['rise'][1] - T['rise'][0], rate=(co[1][1] - co[1][0]) / FPS / (T['rise'][1] - T['rise'][0]),
                          at=_at(arm, co[0], co[1][0], SPOT['unchain'], (0.55, 0.83)), blend=0.4)
    _idle(Q, 'wrists', T['harry_back'][0], idle, SPOT['unchain'], (0.55, 0.83), blend=0.6)
    Q.walk_to(arm, 'back', walk, vs, [SPOT['unchain'], (4.75, 1.0), SPOT['harry_out']], T['harry_back'][1])
    _idle(Q, 'watch', T['to_desk'] + 0.6, idle, SPOT['harry_out'], (0.8, 0.6), blend=0.8)
    Q.walk_to(arm, 'to_desk', walk, vs, [SPOT['harry_out'], (2.6, 0.2), (0.0, -0.4), (-2.2, -1.6), SPOT['harry_desk']], T['at_desk'])
    _idle(Q, 'desk', T['pick'][1] + 0.4, idle, SPOT['harry_desk'], (1, 0.45), blend=0.8)
    Q.walk_to(arm, 'to_door', walk, vs, [SPOT['harry_desk'], (-2.4, -2.4), (-2.6, -0.6), (-3.8, -0.15), SPOT['harry_door']], 158.0)
    _idle(Q, 'door', T['harry_through'], idle, SPOT['harry_door'], (-1, -0.2), blend=0.8)
    Q.walk_to(arm, 'through', walk, vs, [SPOT['harry_door'], (-4.8, -0.45), (-5.35, 0.1), home], 165.5)
    tr = C['turnr']; Q.add('turn', src=tr[0], f0=tr[1][0], dur=1.5, rate=(tr[1][1] - tr[1][0]) / FPS / 1.5, at=_at(arm, tr[0], tr[1][0], home, (0, 1)), blend=0.5)
    Q.pad('home2', T['end'], src=base, f0=frames[0] + 20, at=I, blend=1.0)
    Q.log('harry')
    handle = lambda a: (Vector(ENTRY_H) + Matrix.Rotation(a, 3, 'Z') @ Vector((0, 0.86 * S, 0)))

    def overlay(tt, i, lt):
        tag = Q.segs[i]['tag']; f = int(round(tt * FPS))
        pel, fwd, right, up = _live(arm)
        irons = T['rise'][0] - 0.1 < tt < T['put'][0] + 0.6 or T['pick'][0] + 0.6 < tt < T['chains_back']
        cuffs = T['wrists'][1] - 0.2 < tt < T['put'][0] + 0.6 or T['pick'][0] + 0.6 < tt < T['chains_back']
        if tag == 'ankles':
            for side in 'LR':
                a = _rec('coffey', f, f'a{side}')[0]
                g = a + Vector((0, 0, 0.05 * S)) - fwd * 0.04 * S
                _hand_to(arm, side, g, _smooth((lt - 0.2) / 0.6), g + up * 0.3 + right * (0.3 if side == 'R' else -0.3), palm=fwd, pw=0.5)
            _look(arm, _rec('coffey', f, 'aL')[0], 0.7)
        elif tag == 'wrists':
            w = _win(tt, T['wrists'][0], T['wrists'][1] - 0.3, 0.5, 0.4)
            for side, cs in (('L', 'wL'), ('R', 'wR')):
                g = _rec('coffey', f, cs)[0] - fwd * 0.03 * S
                _hand_to(arm, side, g, w, g - up * 0.35 + right * (0.35 if side == 'R' else -0.35), palm=fwd, pw=0.5)
            _carry(arm, k, 1.0 - w, 0.0)
            _look(arm, _rec('coffey', f, 'wL')[0], 0.6)
        elif tag == 'desk' and T['put'][0] - 0.6 < tt < T['put'][1] + 0.6 or tag == 'desk' and T['pick'][0] - 0.6 < tt < T['pick'][1]:
            put = _win(tt, T['put'][0] - 0.5, T['put'][1], 0.4, 0.4) + _win(tt, T['pick'][0] - 0.5, T['pick'][1] - 0.1, 0.4, 0.4)
            for side, sd in (('L', -1), ('R', 1)):
                g = P(*CHAIN_DESK) + Vector((0, sd * 0.1 * S, 0.06 * S))
                _hand_to(arm, side, g, put, g + up * 0.3 + right * sd * 0.3 - fwd * 0.1, palm=-up, pw=0.5)
            for b_ in SPINE: people.bend(arm, b_, right, -0.1 * put)
            _look(arm, P(*CHAIN_DESK), 0.7 * put)
        elif tag == 'door':
            a = math.radians(95) * _smooth((tt - T['door3'][0]) / (T['door3'][1] - T['door3'][0]))
            g = handle(a); w = _win(tt, T['harry_open'][0], T['door3'][0] + 0.6, 0.4, 0.3)
            _hand_to(arm, 'R', g, w, g - up * 0.3 + right * 0.3)
            _carry(arm, k, 1.0, 1.0 - w)
        else:
            _carry(arm, k, 1.0 if irons else 0.0, 1.0 if cuffs else 0.0)
        mouse = _mouse_at(tt)
        if tag == 'desk':
            if mouse: _look(arm, P(mouse[0], mouse[1], 0.05), 0.6)
            elif T['laugh1'][0] < tt < T['laugh1'][1]: _look(arm, _rec('coffey', f), 0.3)
        elif tag in ('stand', 'watch'):
            _look(arm, _rec('coffey', f), 0.5)
        _record('harry', arm, f)
    acts['scene'] = people.sequence(arm, base, 'harry_scene', Q.segs, overlay=overlay)
    for a, _, _ in C.values(): bpy.data.actions.remove(a)
    bpy.data.actions.remove(idle[0])


# ---------------------------------------------------------------- Paul
def _paul_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS; T = TL
    def wait(f, t):
        _behind_back(arm, k); _look(arm, P(-2.0, -0.4 + 0.5 * math.sin(t * 0.25), 1.6), 0.3)
    acts['wait'] = people.custom_act(arm, base, frames, 'paul_wait', wait, _all(arm, fingers=True))
    if not full: return
    C = _clips(arm, 'paul', {'walk': ('m_walk_neutral_01', dict(inplace=True, cycles=20)), 'talk': ('m_gestic_talk_neutral_02', dict(cycles=4)),
                             'listen': ('m_gestic_listen_neutral_01', dict(cycles=4)), 'angry': ('m_gestic_talk_angry_01', {}), 'laugh': ('m_gestic_laugh_low', dict(cycles=2)),
                             'turn': ('m_turn_left_180', {})})
    idle = _long(arm, 'paul', 'm_idle_breathe_01', 'idle')
    walk, vs = (C['walk'][0], C['walk'][1]), C['walk'][2]
    home, hf = HOME['paul']; pin = SPOT['p_in']; fin = (-0.15, -1.0)
    Q = Seq(); I = Matrix.Identity(4)
    Q.pad('home', T['paul_in'][0], src=base, f0=frames[0], at=I)
    Q.walk_to(arm, 'in', walk, vs, [home, (5.05, 1.75), (5.15, 2.4), (5.62, 3.0), pin], T['paul_in'][1])
    _idle(Q, 'wait_in', T['talk1'][0], idle, pin, fin, blend=0.8)
    tk = C['talk']; Q.pad('talk1', T['beckon'][1], src=tk[0], f0=tk[1][0], at=_at(arm, tk[0], tk[1][0], pin, fin), blend=0.8)
    _idle(Q, 'stand1', T['order'][0], idle, pin, fin, blend=0.7)
    Q.pad('order', T['order'][1], src=tk[0], f0=tk[1][0] + 200, at=_at(arm, tk[0], tk[1][0] + 200, pin, fin), blend=0.8)
    _idle(Q, 'stand2', T['yell'][0], idle, pin, fin, blend=0.7)
    ag = C['angry']; Q.pad('yell', T['yell'][1], src=ag[0], f0=ag[1][0] + 60, at=_at(arm, ag[0], ag[1][0] + 60, pin, fin), blend=0.5)
    _idle(Q, 'watch', T['talk2'][0], idle, pin, fin, blend=0.8)
    Q.pad('talk2', T['talk2'][1], src=tk[0], f0=tk[1][0] + 60, at=_at(arm, tk[0], tk[1][0] + 60, pin, fin), blend=0.8)
    li = C['listen']; Q.pad('listen', T['point'][0], src=li[0], f0=li[1][0], at=_at(arm, li[0], li[1][0], pin, fin), blend=0.8)
    _idle(Q, 'point', T['paul_go_out'][0], idle, pin, fin, blend=0.7)
    Q.walk_to(arm, 'out', walk, vs, [pin, (5.75, 3.1), (5.72, 2.6), (5.05, 1.9), (4.95, 1.25), SPOT['paul_out']], T['paul_go_out'][1])
    _idle(Q, 'close', T['to_desk'] + 0.4, idle, SPOT['paul_out'], (-0.3, 0.95), blend=0.8)
    Q.walk_to(arm, 'to_desk', walk, vs, [SPOT['paul_out'], (3.0, 0.3), (0.0, -0.1), (-1.8, -0.7), SPOT['paul_desk']], T['at_desk'])
    _idle(Q, 'desk', T['laugh1'][0], idle, SPOT['paul_desk'], (1, -0.1), blend=0.8)
    la = C['laugh']; Q.pad('laugh1', T['laugh1'][1], src=la[0], f0=la[1][0], at=_at(arm, la[0], la[1][0], SPOT['paul_desk'], (1, -0.1)), blend=0.7)
    _idle(Q, 'desk2', T['laugh2'][0], idle, SPOT['paul_desk'], (1, -0.1), blend=0.8)
    Q.pad('laugh2', T['laugh2'][1], src=la[0], f0=la[1][0] + 40, at=_at(arm, la[0], la[1][0] + 40, SPOT['paul_desk'], (1, -0.1)), blend=0.7)
    _idle(Q, 'desk3', T['yard'], idle, SPOT['paul_desk'], (1, -0.1), blend=0.8)
    Q.walk_to(arm, 'to_cell', walk, vs, [SPOT['paul_desk'], (-1.0, -0.3), (2.0, 0.3), SPOT['paul_cell']], T['at_cell'])
    _idle(Q, 'cell', T['out_go'] + 0.8, idle, SPOT['paul_cell'], (0.3, 0.95), blend=0.8)
    Q.walk_to(arm, 'escort', walk, vs, [SPOT['paul_cell'], (3.9, 1.35), (2.6, 1.3), (0.0, 1.15), (-2.4, 0.95), SPOT['paul_wait']], 162.0)
    _idle(Q, 'see_off', T['paul_back'], idle, SPOT['paul_wait'], (-0.9, -0.4), blend=0.8)
    Q.walk_to(arm, 'back', walk, vs, [SPOT['paul_wait'], (-2.0, 0.9), (0.5, 1.0), (3.4, 1.0), (4.9, 1.1), home], T['paul_home'])
    tn = C['turn']; Q.add('turn', src=tn[0], f0=tn[1][0], dur=1.8, rate=(tn[1][1] - tn[1][0]) / FPS / 1.8, at=_at(arm, tn[0], tn[1][0], home, (1.0, 0.25)), blend=0.5)
    Q.pad('home2', T['end'], src=base, f0=frames[0] + 20, at=I, blend=0.6)
    Q.log('paul')

    def overlay(tt, i, lt):
        tag = Q.segs[i]['tag']; f = int(round(tt * FPS))
        pel, fwd, right, up = _live(arm)
        if tag == 'home': _behind_back(arm, k); _look(arm, P(-2.0, -0.3, 1.6), 0.3)
        elif tag == 'home2': _behind_back(arm, k, _smooth((lt - 0.8) / 1.2)); _look(arm, P(-2.0, -0.3, 1.6), 0.3)
        elif tag in ('wait_in', 'talk1', 'stand1', 'watch', 'talk2', 'listen', 'point'):
            _look(arm, _rec('coffey', f), 0.7)
            bk = _win(tt, *T['beckon'], 0.4, 0.4)
            if bk > 0:
                g = pel + fwd * 0.35 * k + up * 0.25 * k - right * 0.2 * k + fwd * 0.08 * k * math.sin((tt - T['beckon'][0]) * 9)
                _hand_to(arm, 'L', g, bk, g - up * 0.3 - right * 0.3, palm=-fwd, pw=0.6)
            if tag == 'watch' and tt < T['wrists'][1]: _look(arm, _rec('coffey', f, 'aL' if tt < T['rise'][1] else 'wL')[0], 0.5)
            pt = _win(tt, *T['point'], 0.4, 0.5)
            if pt > 0: people.point_at(arm, 'R', P(*PENDANT), w=pt, reach=0.5); _look(arm, P(*PENDANT), 0.6 * pt)
            hw = _win(tt, *T['hand'], 0.7, 0.7)
            if hw > 0:
                pump = Vector((0, 0, 0.03 * math.sin((tt - T['hand'][0]) * 6) * _win(tt, T['hand'][0] + 0.9, T['hand'][1] - 0.6, 0.3, 0.3)))
                g = P(*HS) + pump
                _hand_to(arm, 'R', g, hw, g - up * 0.4 + right * 0.35 - fwd * 0.2, palm=right, pw=0.7)
                people.hand_shape(arm, 'R', 'fist', 0.4 * hw)
        elif tag in ('order', 'stand2', 'yell'):
            _look(arm, _rec('percy', f), 0.75)
        elif tag == 'close':
            _look(arm, _rec('coffey', f), 0.5)
        elif tag in ('desk', 'laugh1', 'desk2', 'laugh2', 'desk3'):
            mouse = _mouse_at(tt)
            if mouse: _look(arm, P(mouse[0], mouse[1], 0.05), 0.65)
            else: _look(arm, P(1.0, 0.4, 1.0), 0.3)
        elif tag == 'cell':
            _look(arm, _rec('coffey', f), 0.6)
        elif tag == 'see_off':
            _look(arm, _rec('coffey', f), 0.5)
        _record('paul', arm, f)
    acts['scene'] = people.sequence(arm, base, 'paul_scene', Q.segs, overlay=overlay)
    for a, _, _ in C.values(): bpy.data.actions.remove(a)
    bpy.data.actions.remove(idle[0])


# ---------------------------------------------------------------- Brutal
CELL_HINGE_T = (CELL_A + 0.01, R.CELL_Y + 0.07)                    # the cell door's hinge (true metres)


def _cell_free_end(a):
    """The cell door's free end (its lock side) at angle a (0 shut, -pi/2 open into the Mile), at hand height."""
    v = Matrix.Rotation(a, 3, 'Z') @ Vector((0.76, 0, 0))
    return P(CELL_HINGE_T[0] + v.x, CELL_HINGE_T[1] + v.y, 1.08)


def _brutal_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS; T = TL
    grille = P(R.END_X - 0.05, sum(R.ENTRY) / 2 + 0.05, 1.5)
    def peer(arm=arm):
        pel, fwd, right, up = _live(arm)
        for b_, a in zip(SPINE, (0.03, 0.04, 0.03)): people.bend(arm, b_, right, -a)
        g = P(R.END_X - 0.03, -0.25, 1.32)
        _hand_to(arm, 'L', g, 1.0, g - up * 0.3 - right * 0.3, palm=fwd, pw=0.6)
        _look(arm, grille, 0.8)
    def wait(f, t): peer()
    acts['wait'] = people.custom_act(arm, base, frames, 'brutal_wait', wait, _all(arm, fingers=True))
    if not full: return
    C = _clips(arm, 'brutal', {'walk': ('m_walk_neutral_01', dict(inplace=True, cycles=20)), 'laugh': ('m_gestic_laugh_loud', dict(cycles=2)),
                               'cin': ('m_crouch_in', {}), 'cid': ('m_crouch_idle', dict(cycles=3)), 'cout': ('m_crouch_out', {}), 'turn': ('m_turn_left_180', {})})
    idle = _long(arm, 'brutal', 'm_idle_breathe_01', 'idle')
    walk, vs = (C['walk'][0], C['walk'][1]), C['walk'][2]
    home, hf = HOME['brutal']
    Q = Seq(); I = Matrix.Identity(4)
    Q.pad('home', T['door_open'][1], src=base, f0=frames[0], at=I)
    Q.walk_to(arm, 'aside', walk, vs, [home, (-4.2, 0.0), SPOT['brutal_aside']], 6.0)
    _idle(Q, 'watch', T['brutal_go'], idle, SPOT['brutal_aside'], (-0.8, -0.6), blend=0.8)
    Q.walk_to(arm, 'follow', walk, vs, [SPOT['brutal_aside'], (-3.4, 0.1), (-2.0, 0.2), (0.4, 0.4), (2.6, 0.5), SPOT['brutal_at']], 24.5)
    _idle(Q, 'stand', T['brutal_to_close'][0], idle, SPOT['brutal_at'], (0.85, 0.5), blend=0.8)
    Q.walk_to(arm, 'to_close', walk, vs, [SPOT['brutal_at'], (4.0, 0.8), SPOT['close']], T['brutal_to_close'][1])
    _idle(Q, 'close', T['to_desk'] + 0.8, idle, SPOT['close'], (0.6, 0.8), blend=0.6)
    Q.walk_to(arm, 'to_desk', walk, vs, [SPOT['close'], (3.0, 0.0), (0.0, -0.8), (-1.6, -2.2), SPOT['brutal_desk']], T['at_desk'] + 0.5)
    _idle(Q, 'desk', T['laugh1'][0] + 0.5, idle, SPOT['brutal_desk'], (1, 0.3), blend=0.8)
    la = C['laugh']; Q.pad('laugh1', T['laugh1'][1] + 0.5, src=la[0], f0=la[1][0], at=_at(arm, la[0], la[1][0], SPOT['brutal_desk'], (1, 0.3)), blend=0.7)
    _idle(Q, 'desk2', T['crumb'][0], idle, SPOT['brutal_desk'], (-0.3, 1.0), blend=1.0)
    ci = C['cin']; Q.add('crouch', src=ci[0], f0=ci[1][0], dur=1.5, rate=(ci[1][1] - ci[1][0]) / FPS / 1.5, at=_at(arm, ci[0], ci[1][0], SPOT['brutal_desk'], (-0.3, 1.0)), blend=0.5)
    Q.pad('crumb', T['crumb'][1], src=C['cid'][0], f0=C['cid'][1][0], at=_at(arm, C['cid'][0], C['cid'][1][0], SPOT['brutal_desk'], (-0.3, 1.0)), blend=0.4)
    co = C['cout']; Q.add('rise', src=co[0], f0=co[1][0], dur=1.5, rate=(co[1][1] - co[1][0]) / FPS / 1.5, at=_at(arm, co[0], co[1][0], SPOT['brutal_desk'], (-0.3, 1.0)), blend=0.4)
    _idle(Q, 'desk3', T['laugh2'][0], idle, SPOT['brutal_desk'], (1, 0.3), blend=0.9)
    Q.pad('laugh2', T['laugh2'][1], src=la[0], f0=la[1][0] + 40, at=_at(arm, la[0], la[1][0] + 40, SPOT['brutal_desk'], (1, 0.3)), blend=0.7)
    _idle(Q, 'desk4', T['yard'] + 0.5, idle, SPOT['brutal_desk'], (1, 0.3), blend=0.8)
    Q.walk_to(arm, 'to_cell', walk, vs, [SPOT['brutal_desk'], (-1.0, -0.9), (2.4, 0.2), (4.6, 0.85), SPOT['open_at']], T['at_cell'] + 0.5)
    _idle(Q, 'open', T['open'][1] + 0.5, idle, SPOT['open_at'], (-0.2, 1.0), blend=0.7)
    Q.walk_to(arm, 'aside2', walk, vs, [SPOT['open_at'], (5.55, 0.85)], 147.6)
    _idle(Q, 'wait_out', T['out_go'] + 1.4, idle, (5.55, 0.85), (-0.6, 0.8), blend=0.6)
    Q.walk_to(arm, 'escort', walk, vs, [(5.55, 0.85), (4.4, 0.3), (2.6, 0.2), (0.0, 0.0), (-2.2, -0.6), SPOT['brutal_wait']], 162.5)
    _idle(Q, 'see_off', T['brutal_home'][0], idle, SPOT['brutal_wait'], (-0.8, 0.6), blend=0.8)
    Q.walk_to(arm, 'home', walk, vs, [SPOT['brutal_wait'], (-4.0, -0.9), home], T['brutal_home'][1])
    Q.pad('home2', T['end'], src=base, f0=frames[0] + 20, at=I, blend=1.0)
    Q.log('brutal')
    handle = lambda a: (Vector(ENTRY_H) + Matrix.Rotation(a, 3, 'Z') @ Vector((0, 0.86 * S, 0)))

    def overlay(tt, i, lt):
        tag = Q.segs[i]['tag']; f = int(round(tt * FPS))
        pel, fwd, right, up = _live(arm)
        if tag == 'home':
            peer()
            a = math.radians(95) * _smooth((tt - T['door_open'][0]) / (T['door_open'][1] - T['door_open'][0]))
            push = _win(tt, T['door_open'][0] - 0.6, T['door_open'][0] + 0.8, 0.4, 0.4)
            g = handle(a); _hand_to(arm, 'R', g, push, g - up * 0.3 + right * 0.3)
        elif tag == 'home2':
            w = _smooth((lt - 0.5) / 1.0)
            if w > 0: peer()
        elif tag in ('watch', 'follow', 'stand'):
            _look(arm, _rec('coffey', f), 0.6)
        elif tag == 'close':
            cl = _win(tt, T['close'][0] - 0.4, T['close'][1], 0.4, 0.3)
            a = -math.pi / 2 * (1 - _smooth((tt - T['close'][0]) / (T['close'][1] - T['close'][0])))
            g = _cell_free_end(a)
            if cl > 0: _hand_to(arm, 'R', g, cl, g - up * 0.3 + right * 0.3, palm=fwd, pw=0.5)
            lk = _win(tt, *T['lock'], 0.3, 0.3)
            if lk > 0:
                g = P(CELL_A + 0.72, R.CELL_Y + 0.0, 1.08); _hand_to(arm, 'R', g, lk, g - up * 0.3 + right * 0.3); people.hand_shape(arm, 'R', 'fist', 0.6 * lk)
            _look(arm, g if (cl > 0 or lk > 0) else _rec('coffey', f), 0.6)
        elif tag in ('desk', 'laugh1', 'desk2', 'desk3', 'laugh2', 'desk4', 'crouch', 'crumb', 'rise'):
            mouse = _mouse_at(tt)
            if mouse: _look(arm, P(mouse[0], mouse[1], 0.05), 0.7)
            if tag == 'crumb':
                g = P(-2.52, -2.32, 0.1); w = _win(tt, T['crumb'][0] + 1.4, T['crumb'][1] - 0.3, 0.6, 0.6)
                _hand_to(arm, 'R', g, w, g + up * 0.3 + right * 0.3, palm=-up, pw=0.5)
        elif tag == 'open':
            ul = _win(tt, *T['unlock'], 0.3, 0.2)
            g = P(CELL_A + 0.72, R.CELL_Y + 0.0, 1.08)
            if ul > 0: _hand_to(arm, 'R', g, ul, g - up * 0.3 + right * 0.3); people.hand_shape(arm, 'R', 'fist', 0.6 * ul)
            op = _win(tt, T['open'][0] - 0.1, T['open'][1], 0.2, 0.4)
            a = -math.pi / 2 * _smooth((tt - T['open'][0]) / (T['open'][1] - T['open'][0]))
            ge = _cell_free_end(a)
            if op > 0: _hand_to(arm, 'R', ge, op, ge - up * 0.3 + right * 0.3, palm=-fwd, pw=0.5)
            _look(arm, g, 0.6)
        elif tag in ('wait_out', 'escort', 'see_off'):
            _look(arm, _rec('coffey', f), 0.5)
        _record('brutal', arm, f)
    acts['scene'] = people.sequence(arm, base, 'brutal_scene', Q.segs, overlay=overlay)
    for a, _, _ in C.values(): bpy.data.actions.remove(a)
    bpy.data.actions.remove(idle[0])


# ---------------------------------------------------------------- Dean
def _dean_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS; T = TL
    people.pose_at(arm, base, frames[0])
    m['drop'] = (R.CHAIR_SEAT * S + 0.09 * k * 1.78 / 1.75) - _P(arm, 'Bip01 Pelvis').z
    cine.log(f"dean seated: dropped {m['drop'] / S:+.3f} (true m)")
    paper = P(R.DESK.x - 0.05, R.DESK.y + 0.05, R.DESK_H + 0.02)
    def writing(t, w=1.0):
        pel, fwd, right, up = _live(arm)
        g = paper + Vector((0.03 * math.sin(t * 5.3), 0.04 * math.sin(t * 1.7), 0)) * S
        _hand_to(arm, 'R', g, w, g - up * 0.3 + right * 0.4 - fwd * 0.2, palm=-up, pw=0.6)
        gl = paper + Vector((0.0, 0.22, 0.0)) * S
        _hand_to(arm, 'L', gl, w, gl - up * 0.3 - right * 0.4 - fwd * 0.2, palm=-up, pw=0.6)
        for b_ in SPINE: people.bend(arm, b_, right, -0.08 * w)
    def sit(f, t):
        people.shift_root(arm, (0, 0, m['drop'])); writing(t); _look(arm, paper, 0.5)
    acts['wait'] = people.custom_act(arm, base, frames, 'dean_wait', sit, _all(arm, fingers=True))
    if not full: return
    C = _clips(arm, 'dean', {'walk': ('m_walk_neutral_01', dict(inplace=True, cycles=12)), 'up': ('m_sit_stand_up_chair_01', {}), 'down': ('m_sit_down_chair_01', {})})
    idle = _long(arm, 'dean', 'm_idle_breathe_01', 'idle'); seat_l = _long(arm, 'dean', 'm_sit_chair_breathe_01', 'sit')
    walk, vs = (C['walk'][0], C['walk'][1]), C['walk'][2]
    home, hf = HOME['dean']
    Q = Seq(); I = Matrix.Identity(4)
    Q.pad('sit', T['dean_up'], src=base, f0=frames[0], at=I)
    up = C['up']; Q.add('up', src=up[0], f0=up[1][0], dur=(up[1][1] - up[1][0]) / FPS, at=_at(arm, up[0], up[1][0], home, hf), blend=0.6)
    Q.walk_to(arm, 'follow', walk, vs, [(-4.1, -2.45), (-4.2, -1.45), (-3.5, -0.9), (-2.0, -0.35), (0.6, -0.1), (2.8, -0.1), SPOT['dean_at']], 25.0)
    _idle(Q, 'stand', T['to_desk'] + 1.2, idle, SPOT['dean_at'], (0.6, 0.8), blend=0.8)
    Q.walk_to(arm, 'back', walk, vs, [SPOT['dean_at'], (2.0, -0.6), (-1.0, -0.9), (-3.4, -1.0), (-4.2, -1.45), (-4.12, -2.3)], T['dean_sit'][0])
    dn = C['down']; Q.add('down', src=dn[0], f0=dn[1][0], dur=T['dean_sit'][1] - T['dean_sit'][0], rate=(dn[1][1] - dn[1][0]) / FPS / (T['dean_sit'][1] - T['dean_sit'][0]),
                          at=_at(arm, dn[0], dn[1][1], home, hf), blend=0.5)
    sf0 = seat_l[1][0] + int(Q.t() * FPS)
    Q.pad('seated', T['end'] - 1.5, src=seat_l[0], f0=sf0, at=_at(arm, seat_l[0], sf0, home, hf), blend=0.6)
    Q.pad('sit2', T['end'], src=base, f0=frames[0], at=I, blend=1.2)
    Q.log('dean')

    def overlay(tt, i, lt):
        tag = Q.segs[i]['tag']; f = int(round(tt * FPS))
        w = {'sit': 1.0, 'seated': 1.0, 'sit2': 1.0, 'up': 1 - _smooth(lt / 1.2), 'down': _smooth((lt - 1.0) / 1.2)}.get(tag, 0.0)
        if w > 0: people.shift_root(arm, (0, 0, m['drop'] * w))
        if tag == 'sit':
            writing(tt, 1 - _smooth((tt - (T['dean_up'] - 1.0)) / 1.0)); _look(arm, paper if tt < 2.5 else P(-4.75, -0.55, 1.6), 0.6)
        elif tag in ('seated', 'sit2'):
            mouse = _mouse_at(tt)
            wr = 1.0 if not (T['mouse_out'] - 1 < tt < T['mouse_gone'] + 3) else 0.0
            if tag == 'seated': wr = min(wr, _smooth((lt - 0.5) / 1.0))
            writing(tt, wr)
            if mouse: _look(arm, P(mouse[0], mouse[1], 0.05), 0.7)
            elif T['yard'] + 10 < tt < T['coffey_home']: _look(arm, _rec('coffey', f), 0.5)
            else: _look(arm, paper, 0.5)
        elif tag in ('stand', 'follow'):
            _look(arm, _rec('coffey', f), 0.5)
        _record('dean', arm, f)
    acts['scene'] = people.sequence(arm, base, 'dean_scene', Q.segs, overlay=overlay)
    for a, _, _ in C.values(): bpy.data.actions.remove(a)
    for a in (idle, seat_l): bpy.data.actions.remove(a[0])


# ---------------------------------------------------------------- Delacroix and Bitterbuck, at their bars
def _bars(arm, k, x, w=1.0, lean=0.0):
    """Both hands round the bars of the cell front before him, at DEL_BARS; leaning in by `lean`."""
    if w <= 0: return
    pel, fwd, right, up = _live(arm)
    for b_, a in zip(SPINE, (0.05, 0.06, 0.05)): people.bend(arm, b_, right, -a * lean)
    for side, sd in (('L', -1), ('R', 1)):
        g = P(x, R.CELL_Y + 0.11, DEL_BARS) + right * sd * 0.19 * k / 0.75
        _hand_to(arm, side, g, w, g - up * 0.35 + right * sd * 0.3 - fwd * 0.15, palm=fwd, pw=0.6)
        people.hand_shape(arm, side, 'fist', 0.8 * w)


def _del_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS; T = TL
    x0 = HOME['del'][0][0]
    def wait(f, t): _bars(arm, k, x0); _look(arm, P(0.0, 0.2, 1.4), 0.3)
    acts['wait'] = people.custom_act(arm, base, frames, 'del_wait', wait, _all(arm, fingers=True))
    if not full: return
    C = _clips(arm, 'del', {'walk': ('m_walk_slow_01', dict(inplace=True, cycles=6)), 'cin': ('m_crouch_in', {}), 'cout': ('m_crouch_out', {}),
                            'down': ('m_sit_down_chair_01', {}), 'up': ('m_sit_stand_up_chair_01', {})})
    idle = _long(arm, 'del', 'm_idle_nervous_01', 'idle'); crouch = _long(arm, 'del', 'm_crouch_idle', 'crouch'); seat_l = _long(arm, 'del', 'm_sit_chair_idle_nervous_01', 'sit')
    walk, vs = (C['walk'][0], C['walk'][1]), C['walk'][2]
    home, hf = HOME['del']; kneel = SPOT['del_kneel']; seat = SPOT['del_seat']
    Q = Seq(); I = Matrix.Identity(4)
    Q.pad('bars', T['del_hit'], src=base, f0=frames[0], at=I)
    ci = C['cin']; Q.add('fold', src=ci[0], f0=ci[1][0], dur=T['del_kneel'][1] - T['del_kneel'][0] + 0.5, rate=(ci[1][1] - ci[1][0]) / FPS / (T['del_kneel'][1] - T['del_kneel'][0] + 0.5),
                         at=_at(arm, ci[0], ci[1][0], kneel, (0, -1)), blend=0.35)
    cf0 = crouch[1][0] + int(Q.t() * FPS)
    Q.pad('weep', T['del_up'][0], src=crouch[0], f0=cf0, at=_at(arm, crouch[0], cf0, kneel, (0, -1)), blend=0.5)
    co = C['cout']; Q.add('rise', src=co[0], f0=co[1][0], dur=T['del_up'][1] - T['del_up'][0], rate=(co[1][1] - co[1][0]) / FPS / (T['del_up'][1] - T['del_up'][0]),
                          at=_at(arm, co[0], co[1][0], kneel, (0, -1)), blend=0.5)
    Q.walk_to(arm, 'to_bunk', walk, vs, [kneel, (x0, 3.0), (seat[0] + 0.32, seat[1] + 0.05)], T['del_sit'][0])
    dn = C['down']; Q.add('sit', src=dn[0], f0=dn[1][0], dur=T['del_sit'][1] - T['del_sit'][0], rate=(dn[1][1] - dn[1][0]) / FPS / (T['del_sit'][1] - T['del_sit'][0]),
                          at=_at(arm, dn[0], dn[1][1], seat, (1, 0)), blend=0.5)
    sf0 = seat_l[1][0] + int(Q.t() * FPS)
    Q.pad('seated', T['del_rise'][0], src=seat_l[0], f0=sf0, at=_at(arm, seat_l[0], sf0, seat, (1, 0)), blend=0.6)
    up = C['up']; Q.add('up', src=up[0], f0=up[1][0], dur=T['del_rise'][1] - T['del_rise'][0], rate=(up[1][1] - up[1][0]) / FPS / (T['del_rise'][1] - T['del_rise'][0]),
                        at=_at(arm, up[0], up[1][0], seat, (1, 0)), blend=0.5)
    Q.walk_to(arm, 'to_bars', walk, vs, [(seat[0] + 0.3, seat[1]), (x0 + 0.1, 2.9), home], T['del_bars'])
    Q.pad('bars2', T['end'], src=base, f0=frames[0] + 20, at=I, blend=1.0)
    Q.log('del')
    people.pose_at(arm, seat_l[0], seat_l[1][0])
    drop = {'z': (0.575 * S + 0.09 * k * 1.78 / 1.75) - _P(arm, 'Bip01 Pelvis').z}

    def overlay(tt, i, lt):
        tag = Q.segs[i]['tag']; f = int(round(tt * FPS))
        if tag in ('sit', 'seated', 'up'):
            dz = drop['z']; w = {'seated': 1.0, 'sit': _smooth((lt - 1.0) / 1.0), 'up': 1 - _smooth(lt / 1.0)}[tag]
            people.shift_root(arm, (0, 0, dz * w))
        pel, fwd, right, up_ = _live(arm)
        if tag == 'bars':
            grin = _win(tt, *T['del_grin'], 0.6, 0.8)
            _bars(arm, k, x0, 1.0, lean=0.6 + 0.6 * grin)
            if grin > 0: people.bend(arm, 'Bip01 Head', fwd, 0.18 * grin)
            near = _rec('coffey', f) if T['coffey_go'] < tt < T['arrive'] + 2 else (_rec('percy', f) if tt > T['percy_leave'] else P(4.9, 1.2, 1.6))
            _look(arm, near, 0.7)
        elif tag == 'bars2':
            _bars(arm, k, x0, _smooth((lt - 0.4) / 1.0)); _look(arm, P(0.0, 0.2, 1.4), 0.3)
        elif tag in ('fold', 'weep', 'rise'):
            # the hurt hand (his left) held to his chest, cradled in the right; rocking
            c = _P(arm, 'Bip01 Spine2') + fwd * 0.18 * k - up_ * 0.06 * k
            w = 1.0 if tag == 'weep' else (_smooth(lt / 0.5) if tag == 'fold' else 1 - _smooth((lt - 1.0) / 0.8))
            _hand_to(arm, 'L', c - right * 0.02 * k, w, c - up_ * 0.3 - right * 0.3, palm=-fwd, pw=0.5)
            _hand_to(arm, 'R', c + right * 0.05 * k + up_ * 0.02 * k, w, c - up_ * 0.3 + right * 0.3, palm=-right, pw=0.5)
            if tag == 'weep':
                for b_ in SPINE: people.bend(arm, b_, right, -0.12 - 0.06 * math.sin(tt * 3.2))
                people.bend(arm, 'Bip01 Head', right, -0.2)
            jolt = _pulse(tt, (T['del_hit'],), 0.04, 0.4)
            for b_ in SPINE: people.bend(arm, b_, right, 0.15 * jolt)
        elif tag in ('seated', 'sit', 'up'):
            mouse = _mouse_at(tt)
            for side, sd in (('L', -1), ('R', 1)):
                g = pel + fwd * 0.3 * k + up_ * 0.12 * k + right * sd * 0.03 * k
                _hand_to(arm, side, g, 1.0 if tag == 'seated' else 0.5, g - up_ * 0.3 + right * sd * 0.3, palm=-right * sd, pw=0.5)
            if mouse: _look(arm, P(mouse[0], mouse[1], 0.05), 0.8)
            else: _look(arm, P(2.5, 0.5, 1.4), 0.4)
        _record('del', arm, f)
    acts['scene'] = people.sequence(arm, base, 'del_scene', Q.segs, overlay=overlay)
    for a, _, _ in C.values(): bpy.data.actions.remove(a)
    for a in (idle, crouch, seat_l): bpy.data.actions.remove(a[0])


def _chief_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS; T = TL
    x0 = HOME['chief'][0][0]
    def wait(f, t): _bars(arm, k, x0, lean=0.3); _look(arm, P(1.0, 0.0, 1.4), 0.3)
    acts['wait'] = people.custom_act(arm, base, frames, 'chief_wait', wait, _all(arm, fingers=True))
    if not full: return
    n = int(round(T['end'] * FPS))
    longb, lf, _ = people.retarget(arm, 'm_idle_breathe_01', cycles=80, limit=n + 10, action_name='chief_src_long')

    def scene(f, t):
        _bars(arm, k, x0, lean=0.3)
        mouse = _mouse_at(t)
        if mouse: tgt = P(mouse[0], mouse[1], 0.05)
        elif T['coffey_go'] < t < T['arrive'] + 3 or T['out_go'] < t < T['coffey_home']: tgt = _rec('coffey', f)
        elif T['percy_leave'] < t < T['percy_door']: tgt = _rec('percy', f)
        else: tgt = P(3.0, 0.6, 1.5)
        _look(arm, tgt, 0.75)
        _record('chief', arm, f)
    acts['scene'] = people.custom_act(arm, longb, (lf[0], lf[0] + n), 'chief_scene', scene, _all(arm, fingers=True))
    bpy.data.actions.remove(longb)


# ---------------------------------------------------------------- the room's rig
def _room_rig(seated, col):
    """The rig and its acts: at rest (the entry door shut, the cell's open, the chains on Coffey behind the end wall,
    the mouse away), and the scene (the doors, the chains, the lead, the mouse)."""
    import rooms.the_green_mile_rig as RG
    arm, mesh = RG.make_rig(MATS, col)
    c = dict(who='room', work=WORK['room'], idles={'scene': (None, 0.0)}, cue={}, roam=())
    by = {cc['who']: (cc, a) for cc, a, me in seated}
    FPS = people.FPS; F = lambda s: int(round(s * FPS))

    def put_chains(L, f, d):
        """The cuffs and irons on Coffey's wrists and ankles (his recorded joints at frame f)."""
        for part, key in (('cuff_l', 'wL'), ('cuff_r', 'wR'), ('ank_l', 'aL'), ('ank_r', 'aR')):
            p, ax = d[key]
            q = Vector((1, 0, 0)).rotation_difference(ax)
            off = ax * (-0.035 if part.startswith('cuff') else 0.02) * S
            pos = p + off + (Vector((0, 0, -0.03 * S)) if part.startswith('ank') else Vector())
            L.set(part, f, pos, q, 1.0)

    def coffey_frame(a, f):
        people.pose_at(a, by['coffey'][0]['acts']['scene' if 'scene' in by['coffey'][0]['acts'] else 'wait'], f)
    # at rest: the chains on him as he waits behind the end wall
    ca = by['coffey'][1]; wa = by['coffey'][0]['acts']['wait']
    people.pose_at(ca, wa, int(wa.frame_range[0]))
    rest0 = {s: ((_P(ca, f'Bip01 {s[1]} Hand'), (_P(ca, f'Bip01 {s[1]} Hand') - _P(ca, f'Bip01 {s[1]} Forearm')).normalized()) if s[0] == 'w' else
                 (_P(ca, f'Bip01 {s[1]} Foot'), (_P(ca, f'Bip01 {s[1]} Foot') - _P(ca, f'Bip01 {s[1]} Calf')).normalized())) for s in ('wL', 'wR', 'aL', 'aR')}
    Lr = RG.Track(arm, int(4.0 * FPS))
    for f in range(Lr.n + 1):
        put_chains(Lr, f, rest0); Lr.set('celldoor', f, Lr.rest[Lr._k('celldoor')], Quaternion(Vector((0, 0, 1)), RG.CELL_OPEN))
    acts = {'rest': Lr.key('room_rest')}
    if 'scene' in by['coffey'][0]['acts']:
        n = int(round(TL['end'] * FPS)); T = TL
        sc = lambda who: by[who][0]['acts']['scene']
        def frames_of(who, fn):
            out = {}; a = by[who][1]; act = sc(who); f0 = int(act.frame_range[0])
            for f in range(f0, int(act.frame_range[1]) + 1):
                people.pose_at(a, act, f); out[f - f0] = fn(a)
            return out
        cof = frames_of('coffey', lambda a: {s: ((_P(a, f'Bip01 {s[1]} Hand'), (_P(a, f'Bip01 {s[1]} Hand') - _P(a, f'Bip01 {s[1]} Forearm')).normalized()) if s[0] == 'w' else
                                                 (_P(a, f'Bip01 {s[1]} Foot'), (_P(a, f'Bip01 {s[1]} Foot') - _P(a, f'Bip01 {s[1]} Calf')).normalized())) for s in ('wL', 'wR', 'aL', 'aR')})
        har = frames_of('harry', lambda a: (_grip(a, 'L'), _grip(a, 'R')))
        per = frames_of('percy', lambda a: _grip(a, 'L'))
        L = RG.Track(arm, n)
        # the entry door
        ek = [(0, 0.0), (F(T['door_open'][0]), 0.0), (F(T['door_open'][1]), math.radians(95)), (F(T['door_shut'][0]), math.radians(95)), (F(T['door_shut'][1]), 0.0),
              (F(T['door2'][0]), 0.0), (F(T['door2'][1]), math.radians(95)), (F(T['door2_shut'][0]), math.radians(95)), (F(T['door2_shut'][1]), 0.0),
              (F(T['door3'][0]), 0.0), (F(T['door3'][1]), math.radians(95)), (F(T['door3_shut'][0]), math.radians(95)), (F(T['door3_shut'][1]), 0.0)]
        dk = [(0, RG.CELL_OPEN), (F(T['close'][0]), RG.CELL_OPEN), (F(T['close'][1]), 0.0), (F(T['open'][0]), 0.0), (F(T['open'][1]), RG.CELL_OPEN)]
        for f in range(n + 1):
            L.set('entry', f, L.rest[L._k('entry')], Quaternion(Vector((0, 0, 1)), RG.door_angle(ek, f)))
            L.set('celldoor', f, L.rest[L._k('celldoor')], Quaternion(Vector((0, 0, 1)), RG.door_angle(dk, f)))
        # the chains: on Coffey; the irons then the cuffs in Harry's hands; on the desk; back in his hands; on Coffey again
        desk = P(*CHAIN_DESK)
        for f in range(n + 1):
            t = f / FPS; d = cof.get(f) or cof[min(cof, key=lambda g: abs(g - f))]
            gl, gr = har.get(f, har[max(har)])
            on_ank = t < T['rise'][0] or t > T['chains_back']
            on_cuf = t < T['wrists'][1] - 0.3 or t > T['chains_back']
            on_desk = T['put'][1] - 0.4 <= t <= T['pick'][0] + 0.6
            if on_ank or on_cuf: put_chains(L, f, d)
            for part, on, hand, sd in (('ank_l', on_ank, gl, -1), ('ank_r', on_ank, gl, 1), ('cuff_l', on_cuf, gr, -1), ('cuff_r', on_cuf, gr, 1)):
                if on: continue
                if on_desk:
                    off = Vector((0.0, sd * (0.1 if part.startswith('ank') else 0.06) + (-0.12 if part.startswith('ank') else 0.12), 0.01)) * S
                    L.set(part, f, desk + off, Quaternion(Vector((0, 1, 0)), math.pi / 2), 1.0)
                else:                                                   # hanging from the fist: the two ends close together
                    p = hand.to_translation() + Vector((0, 0, -0.06 * S)) + Vector((sd * 0.03 * S, 0, 0))
                    L.set(part, f, p, Quaternion(Vector((0, 1, 0)), math.pi / 2), 1.0)
        # the lead: from the middle of his cuffs to Percy's left fist, while Percy leads him in
        for f in range(n + 1):
            t = f / FPS
            if T['coffey_go'] + 0.6 < t < T['jab'] - 0.4:
                d = cof.get(f) or cof[min(cof, key=lambda g: abs(g - f))]
                a = (d['wL'][0] + d['wR'][0]) / 2; b = per[f].to_translation() if f in per else per[max(per)].to_translation()
                L.set('lead_a', f, a, Quaternion(), 1.0); L.set('lead_b', f, b, Quaternion(), 1.0)
        # the mouse
        for f in range(n + 1):
            t = f / FPS; mo = _mouse_at(t)
            if not mo: continue
            x, y, head, moving = mo
            if head is None:
                head = -math.pi / 2 if T['mouse_sit'][0] <= t <= T['mouse_back'] else math.pi / 2       # at a stop it looks into the cells
                if T['mouse_sit'][0] <= t <= T['mouse_back']: head = math.atan2(-2.85 + 2.05, -2.3 + 2.6)
            bob = 0.004 * abs(math.sin(t * 2 * math.pi * 7)) if moving else 0.0
            situp = _win(t, T['mouse_sit'][0], T['mouse_back'] - 0.4, 0.4, 0.3)
            nib = 0.15 * math.sin(t * 14) * _win(t, T['crumb'][0] + 2.0, T['mouse_back'] - 0.6, 0.3, 0.3)
            q = Quaternion(Vector((0, 0, 1)), head) @ Quaternion(Vector((0, 1, 0)), -math.radians(55) * situp - nib)
            L.set('mouse', f, P(x, y, bob), q, 1.0 if t > T['mouse_out'] + 0.05 and t < T['mouse_gone'] - 0.05 else 0.0)
        acts['scene'] = L.key('room_scene')
    c['acts'] = acts
    return [(c, arm, mesh)]


# ---------------------------------------------------------------- bake and export
def bake(sc, objs, phantoms, seated, args):
    """The block's light baked into atlases (the people and the rig out of it); then room.glb, the people, the rig and
    room.json."""
    os.makedirs(WEB, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    for c, arm, mesh in seated: mesh.hide_render = True
    export, atlases = stages.bake(objs, R.RH * S, OUT, int(args.get('size', 2048)), int(args.get('samples', 320)))
    for c, arm, mesh in seated: mesh.hide_render = False
    cine.export_glb(export, os.path.join(WEB, 'room.glb'))
    meta = stages.room_meta(R.RH * S, atlases); meta.update(_capture_meta())
    meta['people'] = _export_people(seated)
    stages.write_meta(WEB, meta)


def _export_people(seated):
    out = os.path.join(WEB, 'people'); os.makedirs(out, exist_ok=True); metas = []
    for c, arm, mesh in seated:
        pelvis = 'room_root' if c['who'] == 'room' else 'Bip01 Pelvis'
        people.export_person(arm, mesh, c['acts'], os.path.join(out, f"{c['who']}.glb"), roam=c.get('roam', ()), pelvis=pelvis)
        metas.append(person_meta(c))
    return metas


def _capture_meta():
    """How to light the people as the bake lit the room (three.js: y up, z = -Blender y; module metres): the
    pendants' bulbs and the desk lamp as small bright spheres; captured by the desk, mid-Mile and at Coffey's cell."""
    bulbs = []
    for l in RIG['lights']:
        if l.type != 'LIGHT' or l.data.type != 'POINT': continue
        r = 0.03; e = l.data.energy
        bulbs.append({'x': round(l.location.x, 3), 'y': round(l.location.z, 3), 'z': round(-l.location.y, 3), 'r': r,
                      'L': round(e / (4 * math.pi * r ** 2) / 60, 2), 'color': [round(v, 3) for v in l.data.color]})
    at = [[round(v, 3) for v in (p.x, p.z, -p.y)] for p in (P(-3.0, -1.6, 1.2), P(0.6, 0.2, 1.2), P(4.2, 0.9, 1.2), P(R.cell_mid(R.COFFEY_CELL), 3.2, 1.0))]
    return {'capture': {'ceiling': [0.62, 0.58, 0.5], 'walls': [0.52, 0.46, 0.36], 'emitters': bulbs, 'windows': [], 'at': at}}


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
