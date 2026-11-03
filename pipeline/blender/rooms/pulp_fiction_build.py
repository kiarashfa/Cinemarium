# Pulp Fiction: assemble apartment 49 (the living room, the kitchen behind the bar, the hallway with the lift, the
# bathroom), its people (Jules, Vincent, Brett, Roger, Marvin, the man in the bathroom) and the room's own rig (the
# doors, the table, the burger, the cup, the briefcase, the flashes); then preview, bake and export.
import math, os, random
import bpy
from mathutils import Vector, Matrix, Quaternion
import cine, people, stages
from stages import camera
import rooms.pulp_fiction as R

ROOM = 'pulp-fiction'
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
    rnd = random.Random(1994)
    seated = [] if args.get('nocast') else cast(crowd, args)
    SEATED[:] = seated
    R.shell(M, static, phantom)
    R.doorways(M, static)
    R.windows(M, static)
    R.living(M, static, rnd)
    R.brett_chair(M, static)
    R.bar(M, static)
    chand = R.kitchen(M, static, rnd)
    hall = R.hallway(M, static)
    bulb = R.bathroom(M, static)
    RIG['lights'] = R.lights(chand, hall, bulb)
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
    cams = {'case': camera('cam_case', (1.0, -17.0, 7.4), (-0.2, 0.3, 0.8), 30),
            'close': camera('cam_close', (-0.6, -7.6, 2.8), (-0.6, 0.3, 0.9), 40),
            'master': camera('cam_master', (-0.6, -3.4, 1.55), (-1.6, 1.6, 1.1), 50),          # the film's master: the door wall
            'reverse': camera('cam_reverse', (-3.6, 1.6, 1.6), (1.2, -0.4, 1.0), 50),         # toward the bar and the kitchen
            'kitchen': camera('cam_kitchen', (-0.2, -2.0, 1.6), (3.6, 0.6, 1.1), 48),
            'hall': camera('cam_hall', (0.2, 3.0, 1.6), (-4.4, 2.9, 1.1), 56),
            'bath': camera('cam_bath', (0.7, 2.4, 1.7), (3.6, 3.3, 0.8), 56),
            'top': camera('cam_top', (0.0, 0.0, 14.0), (0.0, 0.1, 0.0), 38),
            'act': camera('cam_act', (-0.3, -6.8, 3.9), (-0.6, 0.5, 0.9), 52),
            'table': camera('cam_table', (-0.9, -2.2, 1.7), (-1.4, 0.6, 1.0), 44),
            'side': camera('cam_side', (-1.0, 2.0, 1.7), (-0.9, -0.2, 1.0), 48),
            'bar': camera('cam_bar', (0.2, -1.2, 1.7), (2.3, 0.6, 1.1), 44),
            'right': camera('cam_right', (12.0, -6.0, 6.0), (0.5, 0.2, 0.8), 34)}
    return sc, M, objs, list(phantom.objects), seated, cams


def _static_rig(M, col):
    """Without the cast: the rig's parts where they rest (to judge the set)."""
    try: import rooms.pulp_fiction_rig as RG
    except ImportError: return
    arm, mesh = RG.make_rig(M, col)
    mesh.parent = None


KEEP = ('left_', 'back_wall', 'part_', 'kerb', 'floor', 'subfloor')


def _merge(objs):
    """Join the many small pieces, one object per atlas and material: fewer meshes to draw."""
    groups = {}
    for o in objs:
        if o.get('role') or o.get('backdrop') or len(o.material_slots) != 1 or o.name.startswith(KEEP): continue
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
# Jules and Vincent wait in the lift; Brett at the dinette in his mustard chair, Roger on the sofa, Marvin against the
# wall by the front door, the man in the bathroom behind its door with his revolver. Costumes after Betsy Heimann
# (people_textures.pulp_fiction); Jules's and Vincent's heads are sculpts. Jules's `scene` cues everyone's and the
# room's rig: the lift opens, they come along the hall, Marvin lets them in, Roger starts up and is waved down; Jules
# takes Brett's burger and his Sprite while Vincent smokes in the kitchen, takes the case from the bar's cupboard and
# opens it (the glow); Brett stands to explain, Jules shoots Roger, tips the table away, presses Brett, Ezekiel, the
# two fire together; the man bursts out of the bathroom firing, misses with all six, runs back in; they look at the
# holes in the wall and leave by the lift, Vincent closing the door. Then Brett and Roger are themselves again.
JULES_HEAD = os.path.join(cine.OUT, 'people', 'jules', 'jules_head.glb')      # rooms/pulp_fiction_heads.py
VINCENT_HEAD = os.path.join(cine.OUT, 'people', 'vincent', 'vincent_head.glb')


def _tex(who, prefix, *names):
    return {f'{prefix}_{n}.tga': f'{who}/{prefix}_{n}.png' for n in names}


CAST = [
    dict(who='jules', avatar='Business_Male_01', shape=('athletic', 0.5), height=1.88,
         head=dict(glb=JULES_HEAD, front='-y', eyes=((-0.1066, -0.2434, 0.1229), (0.1693, -0.2155, 0.1443)), cut=0.02, fan_cut=-0.02),
         tex=_tex('jules', 'm005', 'body_color')),
    dict(who='vincent', avatar='Business_Male_01', shape=('heavy', 0.25), height=1.84,
         head=dict(glb=VINCENT_HEAD, front='-y', eyes=((-0.0667, -0.2469, 0.647), (0.0957, -0.2357, 0.657)), cut=0.02, fan_cut=-0.02),
         tex=_tex('vincent', 'm005', 'body_color')),
    dict(who='brett', avatar='Business_Male_06', shape=('heavy', 0.2), height=1.71, tex=_tex('brett', 'm025', 'head_color', 'body_color', 'body_normal')),
    dict(who='roger', avatar='Male_Adult_16', shape=('lean', 1.0), height=1.78,
         shell=dict(colour=(176, 140, 86), hem=-0.1, thick=0.006, gap=0.005, fall=0.012, front=42.0, temple=10.0, nape=-26.0, width=0.03, swept_cards=True),
         tex=_tex('roger', 'm019', 'head_color', 'body_color', 'body_normal')),
    dict(who='marvin', avatar='Male_Adult_12', shape=('lean', 0.8), height=1.76, tex=_tex('marvin', 'm007', 'body_color', 'body_normal')),
    dict(who='fourth', avatar='Male_Adult_07', shape=('lean', 1.2), height=1.75, tex=_tex('fourth', 'm013', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
]
K = {c['who']: c['height'] / 1.78 for c in CAST}
SPINE = ('Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2')
ARMS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('Clavicle', 'UpperArm', 'Forearm', 'Hand'))
LEGS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('Thigh', 'Calf', 'Foot'))
FINGERS = tuple(f'Bip01 {s} Finger{f}{j}' for s in 'LR' for f in '01234' for j in ('', '1', '2'))
ALL = ('Bip01 Pelvis',) + SPINE + ARMS + LEGS + ('Bip01 Neck', 'Bip01 Head')

# where they are (true metres) and which way they face
# (in the lift facing its doors: their bind poses' arms run along y, so they stand where those stay inside the module)
HOME = {'jules': ((-3.86, 2.46), (1.0, 0.0)), 'vincent': ((-4.2, 2.86), (1.0, 0.0)), 'brett': (tuple(R.BRETT_CHAIR), (-1.0, 0.0)),
        'roger': ((-0.85, -3.12), (0.0, 1.0)), 'marvin': ((-3.78, 1.74), (0.25, -1.0)), 'fourth': ((1.86, 2.62), (-1.0, -0.1))}
BASES = {'jules': 'm_idle_breathe_01', 'vincent': 'm_idle_breathe_01', 'brett': 'm_sit_chair_breathe_01', 'roger': 'm_idle_breathe_01',
         'marvin': 'm_idle_breathe_01', 'fourth': 'm_idle_nervous_01'}
WORK = {'jules': ('wait', 6, 12), 'vincent': ('wait', 6, 12), 'brett': ('sit', 6, 12), 'roger': ('lie', 6, 12), 'marvin': ('stand', 6, 12),
        'fourth': ('hide', 6, 12), 'room': ('rest', 6, 12)}
FIRST = {'jules': 'scene'}
CUE = {'jules': {'scene': {w: 'scene' for w in ('vincent', 'brett', 'roger', 'marvin', 'fourth', 'room')}}}
SEAT_TOP = 0.49                                      # Brett's chair: the seat's top
LIE_P = Vector((-0.86, -3.12, 0.53))                 # Roger's pelvis, lying on his back along the sofa, his head to +x
SPOTS = dict(j_door=(-2.8, 2.6), v_door=(-2.22, 2.86), j_table=(-2.3, 0.4), v_bar=(2.62, 0.5), m_door=(-3.05, 1.56), j_brett=(-1.22, 0.42),
             v_by=(-1.42, -0.22), j_wall=(-4.0, -1.18), v_wall=(-3.96, -1.72), f_fire=(0.94, 1.36), j_hall=(-3.3, 2.78), v_hall=(-2.8, 2.56))
TL = dict(lift_open=(0.3, 1.4), j_out=1.4, v_out=1.9, knock=(4.6, 5.6), m_go=5.0, door_open=(6.6, 7.8), j_in=8.2, v_in=8.9,
          roger_up=(8.6, 9.6), wave=(10.8, 12.4), roger_down=(12.0, 13.2), talk1=12.4, v_light=(18.4, 20.4),
          burger_grab=24.0, bite=(25.0, 26.6), offer=(29.0, 31.2), burger_put=34.0, cup_point=(35.6, 36.8), cup_grab=37.6, sip=(38.6, 41.4), cup_put=42.6,
          gulls=(44.0, 46.2), nod=(46.4, 47.2), v_crouch=45.6, cupdoor=(47.6, 48.2), case_grab=48.7, v_rise=49.4, cupdoor_close=(51.0, 51.6),
          case_put=52.8, lid_open=(53.6, 54.4), happy=(55.0, 60.0), lid_close=(59.8, 60.4),
          b_up=61.0, b_talk=63.0, draw=(66.4, 67.4), roger_shots=(67.8, 68.3, 68.8), b_sit=69.2, tip=(71.8, 72.4, 73.2), j_step=73.6,
          lean=(78.0, 91.0), cheek=(83.0, 87.6), shoulder=89.0, ezekiel=92.0, v_take=94.0, v_back=94.6, v_draw=(100.6, 101.4),
          j_shots=(104.5, 104.9, 105.3, 105.8, 106.2), v_shots=(104.7, 105.1, 105.6, 106.0), dead=106.6, m_head=106.0,
          f_burst=107.6, f_shots=(109.8, 110.2, 110.6, 111.0, 111.4, 111.8), f_stare=(112.0, 113.4), f_flee=113.4, f_door_close=(114.9, 115.4),
          look_each=(116.4, 118.0), to_wall=118.2, holes=(120.6, 125.0), tuck=(124.4, 125.0), leave=125.0, v_close=(128.9, 129.8),
          lift_open2=(129.6, 130.6), lift_close=(133.6, 134.8), end=137.0)
HANDS = {}                                           # who -> {frame: grip frame (world) of each hand} in the scene (for the rig)
HEADS = {}                                           # who -> {frame: head position}


def _all(arm, fingers=False):
    return (next(b.name for b in arm.data.bones if b.parent is None),) + ALL + (FINGERS if fingers else ())


def _smooth(x):
    x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)


def _win(t, a, b, rise=0.5, fall=0.5):
    """1 between a and b, eased in and out over rise and fall seconds."""
    return _smooth((t - a) / rise) * (1 - _smooth((t - b) / fall))


def _pulse(t, times, rise=0.04, fall=0.25):
    """A sharp kick at each of `times` (a shot's recoil, a body hit), fading."""
    return max([0.0] + [_smooth((t - s) / rise) * (1 - _smooth((t - s - rise) / fall)) for s in times])


def _live(arm):
    """The body frame now: the pelvis, and the facing it carries (stored in the pelvis's own axes when placed)."""
    pb = arm.pose.bones['Bip01 Pelvis']; M = people._world(arm, pb)
    f = M.to_3x3() @ Vector(arm['pel_fwd']); f.z = 0; f.normalize()
    up = Vector((0, 0, 1)); return M.translation.copy(), f, f.cross(up).normalized(), up


def _P(arm, bone):
    return people._world(arm, arm.pose.bones[bone]).translation.copy()


def _look(arm, at, w):
    """Turn the head (and a little the neck) toward a point, by the fraction w."""
    if w <= 0: return
    H = _P(arm, 'Bip01 Head'); pel, f, right, up = _live(arm)
    d = (Vector(at) - H).normalized()
    yaw = math.atan2(d.dot(-right), d.dot(f)); pitch = math.asin(max(-1, min(1, d.z)))
    yaw = max(-1.3, min(1.3, yaw)); pitch = max(-0.8, min(0.6, pitch))
    people.bend(arm, 'Bip01 Neck', up, yaw * 0.35 * w); people.bend(arm, 'Bip01 Head', up, yaw * 0.65 * w)
    people.bend(arm, 'Bip01 Neck', right, pitch * 0.3 * w); people.bend(arm, 'Bip01 Head', right, pitch * 0.7 * w)


def _hand_to(arm, side, tgt, w, pole, palm=None, pw=0.8):
    """A hand toward a point by w (IK from where the clip has it), its elbow toward `pole`, its palm facing `palm`."""
    if w <= 0: return
    H0 = _P(arm, f'Bip01 {side} Hand'); g = H0.lerp(Vector(tgt), min(w, 1.0))
    people.ik2(arm, side, g, Vector(pole))
    if palm is not None: people.palm_to(arm, side, Vector(palm).normalized(), pw * min(w, 1.0))


def _grip(arm, side):
    """A hand's grip frame (world): x along the forearm out through the fist, y toward the palm's side (the grip),
    z up the thumb's side; at the middle of the fist."""
    H = _P(arm, f'Bip01 {side} Hand'); F = _P(arm, f'Bip01 {side} Forearm')
    x = (H - F).normalized(); n = people._palm(arm, side)
    y = (n - x * n.dot(x)).normalized()
    if side == 'L': y = -y
    z = x.cross(y)
    c = H + x * 0.07 + (n - x * n.dot(x)).normalized() * 0.015
    return Matrix.Translation(c) @ Matrix(((x.x, y.x, z.x, 0), (x.y, y.y, z.y, 0), (x.z, y.z, z.z, 0), (0, 0, 0, 1)))


def _chest(arm, bone='Bip01 Spine2', depth=0.12, dx=0.0, dz=0.0):
    """A frame on the front of the chest (or a shoulder): its -y out of the body (a stain's face), z up the spine."""
    S2 = _P(arm, bone); u = (_P(arm, 'Bip01 Neck') - _P(arm, 'Bip01 Spine1')).normalized()
    s = (_P(arm, 'Bip01 R Clavicle') - _P(arm, 'Bip01 L Clavicle')).normalized()
    fwd = u.cross(s).normalized(); s = fwd.cross(u).normalized()
    c = S2 + fwd * depth + s * dx + u * dz
    X, Y, Z = -s, -fwd, u
    return Matrix.Translation(c) @ Matrix(((X.x, Y.x, Z.x, 0), (X.y, Y.y, Z.y, 0), (X.z, Y.z, Z.z, 0), (0, 0, 0, 1)))


def _mouth(arm):
    """Where the lips are and the head's axes (for a bite, a sip, a cigarette)."""
    u = (_P(arm, 'Bip01 Head') - _P(arm, 'Bip01 Neck')).normalized()
    s = (_P(arm, 'Bip01 REye') - _P(arm, 'Bip01 LEye')).normalized()
    fwd = u.cross(s).normalized()
    lip = (_P(arm, 'Bip01 MUpperLip') + _P(arm, 'Bip01 MBottomLip')) / 2
    return lip, fwd, s, u


def make_person(c, col):
    """One of them, standing at the origin facing -y: the avatar, its build, its head (the sculpts), its hair, its
    height."""
    tex = {k: os.path.join(PEOPLE_TEX, v) for k, v in c.get('tex', {}).items() if os.path.exists(os.path.join(PEOPLE_TEX, v))}
    arm, mesh = people.load_avatar(c['avatar'], textures=tex, collection=col)
    arm.animation_data_clear()
    mesh['person'] = c['who']; arm['person'] = c['who']
    if c.get('shape'): people.reshape(arm, mesh, *c['shape'])
    if c.get('head'):
        h = c['head']
        people.swap_head(arm, mesh, h['glb'], None, h['front'], h['eyes'], cut=h.get('cut', 0.0), fan_cut=h.get('fan_cut', -0.03))
        _bust_collar(arm, mesh, c['who'])
    if c.get('shell') or c.get('head'): people.remove_hair_cards(mesh)
    bpy.context.view_layer.update()
    top = max((mesh.matrix_world @ v.co).z for v in mesh.data.vertices)
    J = people._joints(arm)
    if c.get('shell'):
        h = dict(c['shell']); h['hem'] = J['Bip01 Neck'].z + h['hem']
        people.hair_shell(arm, mesh, **h)
    for ca in list(mesh.data.color_attributes): mesh.data.color_attributes.remove(ca)
    s = c['height'] / top
    arm.scale = arm.scale * s; arm.location = (arm.location.x, arm.location.y, arm.location.z * s)
    bpy.context.view_layer.update()
    return arm, mesh


def _bust_collar(arm, mesh, who):
    """The sculpt's bust below the jaw (a shirt collar and a suit's lapels, both men's): the faces there that are not
    skin (white, grey or black: unsaturated) go; the body's own collar and tie are round the neck instead. The hair
    hanging behind is kept (Vincent's)."""
    import bmesh
    import numpy as np
    J = people._joints(arm); jaw = J.get('Bip01 MJaw', J['Bip01 Head']).z - 0.02; back = J['Bip01 Head'].y + 0.02
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
        if q.z > jaw or q.y > back: continue
        u = sum((l[uv].uv for l in f.loops), Vector((0, 0))) / len(f.loops)
        c = px[int(min(max(u.y, 0), 0.999) * h), int(min(max(u.x, 0), 0.999) * w)]
        if (c.max() - c.min()) / (c.max() + 1e-6) < 0.22 or c.max() < 0.06: dead.append(f)
    bmesh.ops.delete(bm, geom=dead, context='FACES'); bm.to_mesh(mesh.data); bm.free(); mesh.data.update()
    cine.log(who, 'bust collar cut', len(dead), 'faces')


S_ = 1.0


def cast(col, args):
    """Load, dress, shape and place them, and bake their acts (cached: retargets and IK take minutes); the room's rig
    made fresh after (it follows their hands)."""
    full = bool(args.get('full'))
    spec = {'cast': CAST, 'bases': BASES, 'work': WORK, 'cue': CUE, 'tl': TL, 'home': HOME, 'spots': SPOTS, 'lie': list(LIE_P), 'seat': SEAT_TOP,
            'full': full, 'v': 3}
    for c in CAST:
        c['work'] = WORK[c['who']]; c['idles'] = {'scene': (None, 1.0 if c['who'] == 'jules' else 0.0)}; c['cue'] = CUE.get(c['who'], {})
        c['roam'] = ('scene',)
    seated = stages.cast_cache(OUT, CAST, spec, lambda: _make_cast(col, full), col)
    seated += _room_rig(seated, col)
    for c, arm, mesh in seated:
        people.pose_at(arm, c['acts'][c['work'][0]], int(c['acts'][c['work'][0]].frame_range[0]) + 10)
    return seated


def _place(c, arm, at, f, base_name):
    """Set a person at a place facing their way; the base clip retargeted there and slid so its pelvis is over it."""
    who = c['who']; f = Vector((*f, 0)).normalized()
    people.face(arm, f); arm.location = (at[0], at[1], arm.location.z); bpy.context.view_layer.update()
    arm['fwd'] = list(f)
    base, frames, _ = people.retarget(arm, base_name, cycles=2, action_name=f'{who}_base')
    people.pose_at(arm, base, frames[0])
    pel = people._world(arm, arm.pose.bones['Bip01 Pelvis']).translation
    arm.location.x += at[0] - pel.x; arm.location.y += at[1] - pel.y
    bpy.context.view_layer.update()
    people.pose_at(arm, base, frames[0])
    arm['pel_fwd'] = list(people._world(arm, arm.pose.bones['Bip01 Pelvis']).to_3x3().inverted() @ f)
    return base, frames


def _make_cast(col, full):
    seated, made = [], {}
    for c in CAST:
        arm, mesh = make_person(c, col)
        at, f = HOME[c['who']]
        base, frames = _place(c, arm, at, f, BASES[c['who']])
        made[c['who']] = dict(c=c, arm=arm, mesh=mesh, base=base, frames=frames, k=K[c['who']])
        seated.append((c, arm, mesh))
    acts = {k: {} for k in made}
    for m in made.values(): m['mesh'].hide_viewport = True
    # the passive first (their heads and hands are looked at), then Vincent, then Jules (who leads)
    for who, fn in (('roger', _roger_acts), ('brett', _brett_acts), ('marvin', _marvin_acts), ('fourth', _fourth_acts), ('vincent', _vincent_acts), ('jules', _jules_acts)):
        for w2, m2 in made.items(): m2['arm'].hide_viewport = w2 != who          # the others out of the depsgraph: every IK step re-evaluates it
        fn(made[who], acts[who], full)
    for m2 in made.values(): m2['arm'].hide_viewport = False
    for who, m in made.items():
        m['c']['acts'] = acts[who]
        if m['base'] not in acts[who].values(): bpy.data.actions.remove(m['base'])
        m['mesh'].hide_viewport = False
        people.pose_at(m['arm'], acts[who][m['c']['work'][0]], int(m['frames'][0]) + 10)
    return seated


def _at(arm, src, f, p, h):
    hh, pp = people.heading(arm, src, f); return people.carry(pp, hh, Vector((p[0], p[1], 0)), Vector((h[0], h[1], 0)).normalized())


def _record(who, arm, f):
    HEADS.setdefault(who, {})[f] = _P(arm, 'Bip01 Head')


def _head_of(who, f):
    """Where someone's head is at frame f of the scene (recorded), or roughly at home."""
    h = HEADS.get(who, {})
    if h: return h.get(f) or h[min(h, key=lambda g: abs(g - f))]
    (x, y), _ = HOME[who]; return Vector((x, y, {'brett': 1.15, 'roger': 0.62}.get(who, 1.62)))


class Seq:
    """A scene's segments, built in order: add() a clip for a fixed time, pad() one until a moment on the clock."""
    def __init__(self): self.segs = []
    def t(self): return sum(s['dur'] for s in self.segs)
    def add(self, tag, **kw): kw['tag'] = tag; self.segs.append(kw)
    def pad(self, tag, until, **kw): kw['dur'] = max(0.4, until - self.t()); self.add(tag, **kw)
    def walk(self, arm, tag, src, f0, vs, pts, blend=0.6):
        r = people.path(pts); self.add(tag, src=src, f0=f0, dur=r[1] / vs, at=people.walk_along(arm, src, f0, vs, r), blend=blend)
    def log(self, who):
        t = 0.0
        for s in self.segs: s['t0'] = t; t += s['dur']
        cine.log(f'{who} scene: ' + ', '.join(f"{s['tag']} {s['t0']:.1f}" for s in self.segs) + f' end {t:.1f}')
        return t


def _clips(arm, who, names):
    """Retarget the clips a scene uses: {key: (action, frames, speed)}; `names` {key: (clip, kw)}."""
    out = {}
    for k, (clip, kw) in names.items(): out[k] = people.retarget(arm, clip, action_name=f'{who}_src_{k}', **kw)
    return out


def _gun_arm(arm, side, tgt, w, kick=0.0):
    """An arm out, the pistol pointed at `tgt`, the elbow a little bent; the recoil kicks the hand up and back."""
    if w <= 0: return
    people.point_at(arm, side, tgt + Vector((0, 0, 0.18 * kick)), w=w, reach=0.5, jab=-0.06 * kick, shape='gun', drop=0.18, out=0.12)
    people.hand_shape(arm, side, 'fist', 0.85 * w)


# ---------------------------------------------------------------- Roger, on the sofa
def _lie_pose(arm, m, w=1.0):
    """Lying on his back along the sofa, his head on its pillows at the +x end: the standing body (facing +y) turned so
    its up runs along +x and its face looks up, its pelvis on LIE_P; the head propped, the hands on the belly."""
    if w <= 0: return
    root = next(pb for pb in arm.pose.bones if pb.parent is None)
    pel = _P(arm, 'Bip01 Pelvis')
    R3 = Matrix(((0, 0, 1), (1, 0, 0), (0, 1, 0)))                            # up -> +x, facing (+y) -> up, right (+x) -> +y
    Rq = Quaternion().slerp(R3.to_quaternion(), w)
    T = Matrix.Translation(pel.lerp(LIE_P, w)) @ Rq.to_matrix().to_4x4() @ Matrix.Translation(-pel)
    root.matrix = arm.matrix_world.inverted() @ T @ people._world(arm, root)
    bpy.context.view_layer.update()
    if w > 0.9:
        people.bend(arm, 'Bip01 Neck', Vector((0, 1, 0)), -0.35); people.bend(arm, 'Bip01 Head', Vector((0, 1, 0)), -0.25)
        for b_ in SPINE: people.bend(arm, b_, Vector((0, 1, 0)), -0.06)
        belly = _P(arm, 'Bip01 Spine1') + Vector((0, 0, 0.13 * m['k']))
        for side, sd in (('L', -1), ('R', 1)):
            g = belly + Vector((0.02, sd * 0.08, 0))
            _hand_to(arm, side, g, 0.8, g + Vector((-0.2, sd * 0.3, 0.1)), palm=Vector((0, 0, -1)), pw=0.6)


def _roger_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS
    door = Vector((-2.8, 2.0, 1.4))
    def lie(f, t):
        _lie_pose(arm, m)
        _look(arm, Vector((-1.4, 0.4, 1.1)), 0.35)
        _record('roger', arm, f)
    acts['lie'] = people.custom_act(arm, base, frames, 'roger_lie', lie, _all(arm))
    if not full: return
    n = int(round(TL['end'] * FPS))
    longb, lf, _ = people.retarget(arm, BASES['roger'], cycles=60, limit=n + 10, action_name='roger_src_long')
    T = TL; hit = T['roger_shots']

    def scene(f, t):
        _lie_pose(arm, m)
        up = _win(t, T['roger_up'][0], T['roger_down'][0], 0.6, 1.0)          # starts up when they come in, waved down
        for b_, a in zip(SPINE, (0.28, 0.22, 0.16)): people.bend(arm, b_, Vector((0, 1, 0)), -a * up)
        dead = _smooth((t - hit[-1]) / 0.6)
        if t < hit[0]:
            tgt = door if t < 14 else _head_of('jules', f)
            if T['nod'][0] < t < T['nod'][1]: people.bend(arm, 'Bip01 Head', Vector((0, 1, 0)), 0.25 * math.sin(math.pi * (t - T['nod'][0]) / 0.4))
            _look(arm, tgt, 0.6)
        jolt = _pulse(t, hit, 0.03, 0.2)
        for b_ in SPINE: people.bend(arm, b_, Vector((0, 1, 0)), 0.12 * jolt)
        if dead > 0:                                                            # his head rolls toward the room, an arm falls off the edge
            people.bend(arm, 'Bip01 Head', Vector((1, 0, 0)), 0.5 * dead); people.bend(arm, 'Bip01 Neck', Vector((0, 1, 0)), 0.2 * dead)
            hand = _P(arm, 'Bip01 L UpperArm') + Vector((-0.05, 0.25, -0.38))
            _hand_to(arm, 'L', hand, dead, hand + Vector((0.3, 0.2, 0.2)))
        _record('roger', arm, f)
    acts['scene'] = people.custom_act(arm, longb, (lf[0], lf[0] + n), 'roger_scene', scene, _all(arm))
    bpy.data.actions.remove(longb)


# ---------------------------------------------------------------- Brett, at the dinette
def _brett_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS
    people.pose_at(arm, base, frames[0])
    m['drop'] = (SEAT_TOP + 0.09 * k) - _P(arm, 'Bip01 Pelvis').z
    cine.log(f"brett seated: dropped {m['drop']:+.3f}")
    burger = Vector((-1.12, 0.42, R.TABLE_H + 0.05))

    def sit(f, t):
        people.shift_root(arm, (0, 0, m['drop']))
        e = _win(t % 14.0, 5.0, 7.2, 0.8, 0.8)                               # a bite now and then
        lip, fwd, s, u = _mouth(arm)
        pel, fw, right, up = _live(arm)
        _hand_to(arm, 'R', burger.lerp(lip + fwd * 0.05 - u * 0.03, _smooth((t % 14.0 - 5.6) / 0.6) * (1 - _smooth((t % 14.0 - 6.6) / 0.5))), e, pel + right * 0.4 - up * 0.2)
        _look(arm, Vector((-2.3, 0.4, 1.4)), 0.2)
        _record('brett', arm, f)
    acts['sit'] = people.custom_act(arm, base, frames, 'brett_sit', sit, _all(arm))
    if not full: return
    C = _clips(arm, 'brett', {'sit': ('m_sit_chair_idle_nervous_01', dict(cycles=12)), 'up': ('m_sit_stand_up_chair_01', {}), 'down': ('m_sit_down_chair_01', {}),
                              'talk': ('m_gestic_talk_nervous_01', dict(cycles=2)), 'idle': ('m_idle_nervous_01', dict(cycles=3))})
    at0, f0 = Vector(HOME['brett'][0]), Vector(HOME['brett'][1])
    T = TL; S = Seq(); I = Matrix.Identity(4)
    S.pad('sit', T['b_up'], src=base, f0=frames[0], at=I)
    up = C['up']; S.add('up', src=up[0], f0=up[1][0], dur=(up[1][1] - up[1][0]) / FPS, at=_at(arm, up[0], up[1][0], at0, f0), blend=0.6)
    stand = at0 + f0 * 0.3
    S.pad('talk', T['b_sit'], src=C['talk'][0], f0=C['talk'][1][0], at=_at(arm, C['talk'][0], C['talk'][1][0], stand, f0), blend=0.7)
    dn = C['down']; S.add('down', src=dn[0], f0=dn[1][0], dur=(dn[1][1] - dn[1][0]) / FPS * 0.8, rate=1.25, at=_at(arm, dn[0], dn[1][1], at0, f0), blend=0.4)
    S.pad('terror', T['end'], src=C['sit'][0], f0=C['sit'][1][0], at=_at(arm, C['sit'][0], C['sit'][1][0], at0, f0), blend=0.5)
    S.log('brett')
    hits = T['j_shots'] + T['v_shots']

    def overlay(tt, i, lt):
        tag = S.segs[i]['tag']; f = int(round(tt * FPS))
        seatw = {'sit': 1.0, 'terror': 1.0, 'up': 1 - _smooth(lt / 1.0), 'down': _smooth((lt - 0.4) / 1.0)}.get(tag, 0.0)
        people.shift_root(arm, (0, 0, m['drop'] * seatw))
        pel, fwd, right, up_ = _live(arm)
        jules = _head_of('jules', f)
        if tag == 'sit':
            _look(arm, jules if T['j_in'] + 1.5 < tt else Vector((-2.8, 2.0, 1.5)), 0.6)
            if T['burger_grab'] - 0.8 < tt < T['burger_put'] + 1: _look(arm, jules - Vector((0, 0, 0.25)), 0.4)
        elif tag == 'talk':
            _look(arm, jules, 0.7)
            fl = _pulse(tt, T['roger_shots'], 0.05, 0.4)
            for b_ in SPINE: people.bend(arm, b_, right, 0.15 * fl)
            if tt > T['roger_shots'][0]: _look(arm, _head_of('roger', f), 0.5)
        elif tag == 'terror':
            dead = _smooth((tt - T['dead']) / 0.7)
            shield = _win(tt, T['tip'][1], T['dead'] - 0.2, 0.5, 0.3)          # his hands up before his face
            hd = _P(arm, 'Bip01 Head')
            for side, sd in (('L', -1), ('R', 1)):
                g = hd + fwd * 0.22 * k + right * sd * 0.12 * k - up_ * (0.06 + 0.05 * math.sin(tt * 9 + sd)) * k
                _hand_to(arm, side, g, shield * (0.4 if (side == 'R' and tt > T['shoulder']) else 1.0), g - up_ * 0.4 + right * sd * 0.3, palm=fwd, pw=0.6)
            if tt > T['shoulder']:                                             # his right hand to the wound
                sh = _P(arm, 'Bip01 R UpperArm') + fwd * 0.05 * k
                _hand_to(arm, 'R', sh, (1 - dead) * _smooth((tt - T['shoulder'] - 0.2) / 0.4), sh + right * 0.3 - up_ * 0.3)
            if T['cheek'][0] < tt < T['cheek'][1]:                              # the barrel at his cheek: his head pressed away
                people.bend(arm, 'Bip01 Head', fwd.cross(up_), 0.25 * _win(tt, T['cheek'][0], T['cheek'][1], 0.3, 0.3))
            jolt = _pulse(tt, (T['shoulder'],) + hits, 0.03, 0.22)
            shake = 0.025 * math.sin(tt * 37) * _win(tt, T['shoulder'], T['dead'], 0.3, 0.2)
            for b_ in SPINE: people.bend(arm, b_, right, 0.14 * jolt + shake)
            if dead > 0:                                                       # slumped back, the head fallen to one side
                for b_, a in zip(SPINE, (0.1, 0.12, 0.1)): people.bend(arm, b_, right, a * dead)
                people.bend(arm, 'Bip01 Neck', right, 0.3 * dead); people.bend(arm, 'Bip01 Head', fwd, 0.35 * dead)
                for side, sd in (('L', -1), ('R', 1)):
                    g = pel + right * sd * 0.26 * k - up_ * 0.12 + fwd * 0.08
                    _hand_to(arm, side, g, dead, g + right * sd * 0.3)
            else:
                _look(arm, jules, 0.8)
        _record('brett', arm, f)
    acts['scene'] = people.sequence(arm, base, 'brett_scene', S.segs, overlay=overlay)
    for a, _, _ in C.values(): bpy.data.actions.remove(a)


# ---------------------------------------------------------------- Marvin, by the front door
def _marvin_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS

    def stand(f, t):
        pel, fwd, right, up = _live(arm)
        for b_, a in zip(SPINE, (0.04, 0.04, 0.03)): people.bend(arm, b_, right, -a)       # leaning back on the wall
        _look(arm, Vector((-1.2, 0.0 + 0.6 * math.sin(t * 0.21), 1.1)), 0.4)
        _record('marvin', arm, f)
    acts['stand'] = people.custom_act(arm, base, frames, 'marvin_stand', stand, _all(arm))
    if not full: return
    C = _clips(arm, 'marvin', {'walk': ('m_walk_slow_01', dict(inplace=True, cycles=4)), 'idle': ('m_idle_nervous_01', dict(cycles=12)),
                               'idle2': ('m_idle_neutral_01', dict(cycles=4))})
    walk, wf, vs = C['walk']; idle, idf, _ = C['idle']
    home, hf = Vector(HOME['marvin'][0]), Vector(HOME['marvin'][1]); dp = Vector(SPOTS['m_door'])
    T = TL; S = Seq(); I = Matrix.Identity(4)
    S.pad('wait', T['m_go'], src=base, f0=frames[0], at=I)
    S.walk(arm, 'to_door', walk, wf[0], vs, [home, Vector((-3.45, 1.58)), dp])
    S.pad('open', T['door_open'][1] + 0.3, src=C['idle2'][0], f0=C['idle2'][1][0], at=_at(arm, C['idle2'][0], C['idle2'][1][0], dp, (0.2, 1.0)), blend=0.5)
    S.walk(arm, 'back', walk, wf[0] + 20, vs * 0.8, [dp, Vector((-3.5, 1.6)), home + Vector((0.02, -0.1))])
    S.pad('stand', T['end'], src=idle, f0=idf[0], at=_at(arm, idle, idf[0], home, hf), blend=0.8)
    S.log('marvin')
    knob = Vector((R.ENTRY[0] + 0.07, R.PART[0] - 0.03, 0.97))

    def overlay(tt, i, lt):
        tag = S.segs[i]['tag']; f = int(round(tt * FPS))
        pel, fwd, right, up = _live(arm)
        if tag == 'open':
            a = math.radians(70) * _smooth((tt - T['door_open'][0]) / (T['door_open'][1] - T['door_open'][0]))
            hinge = Vector((R.ENTRY[1] - 0.01, (R.PART[0] + R.PART[1]) / 2, 0.97))
            kn = hinge + Matrix.Rotation(a, 3, 'Z') @ (knob - hinge)
            w = _win(tt, T['door_open'][0] - 0.5, T['door_open'][0] + 0.7, 0.4, 0.4)
            _hand_to(arm, 'R', kn, w, kn - up * 0.4 + right * 0.3, palm=-fwd, pw=0.5)
            _look(arm, kn, 0.6)
        elif tag == 'stand':
            head = _win(tt, T['m_head'], T['end'] + 5, 0.6, 0.5)
            fl = _pulse(tt, T['roger_shots'] + T['j_shots'] + T['f_shots'], 0.05, 0.35)
            for b_ in SPINE: people.bend(arm, b_, right, 0.12 * fl)
            if head > 0:                                                       # his hands on his head
                hd = _P(arm, 'Bip01 Head')
                for side, sd in (('L', -1), ('R', 1)):
                    g = hd + up * 0.1 * k + right * sd * 0.08 * k
                    _hand_to(arm, side, g, head, g + right * sd * 0.4 + fwd * 0.2, palm=-up, pw=0.6)
            tgt = _head_of('jules', f) if tt < T['f_burst'] else Vector(SPOTS['f_fire'] + (1.5,)) if tt < T['f_flee'] + 1 else _head_of('jules', f)
            _look(arm, tgt, 0.6)
        _record('marvin', arm, f)
    acts['scene'] = people.sequence(arm, base, 'marvin_scene', S.segs, overlay=overlay)
    for a, _, _ in C.values(): bpy.data.actions.remove(a)


# ---------------------------------------------------------------- the man in the bathroom
def _fourth_hold(arm, k, w=1.0):
    """Waiting with the revolver held up in both hands by his chest, its barrel to the ceiling."""
    if w <= 0: return
    pel, fwd, right, up = _live(arm)
    c = _P(arm, 'Bip01 Spine2') + fwd * 0.22 * k + up * 0.02
    _hand_to(arm, 'R', c, w, c - up * 0.3 + right * 0.3, palm=-right, pw=0.6)
    _hand_to(arm, 'L', c - up * 0.03 + right * 0.03, w, c - up * 0.3 - right * 0.3, palm=right, pw=0.6)
    people.hand_shape(arm, 'R', 'fist', 0.9 * w); people.hand_shape(arm, 'L', 'fist', 0.7 * w)


def _fourth_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS
    door = Vector(((R.BATHDOOR[0] + R.BATHDOOR[1]) / 2, R.PART[1], 1.5))

    def hide(f, t):
        _fourth_hold(arm, k); _look(arm, door, 0.6)
        HANDS.setdefault('fourth', {})
        _record('fourth', arm, f)
    acts['hide'] = people.custom_act(arm, base, frames, 'fourth_hide', hide, _all(arm, fingers=True))
    if not full: return
    C = _clips(arm, 'fourth', {'run': ('m_run_fast_01', dict(inplace=True, cycles=6)), 'idle': ('m_idle_nervous_01', dict(cycles=12))})
    run, rf, vr = C['run']; idle, idf, _ = C['idle']
    home, hf = Vector(HOME['fourth'][0]), Vector(HOME['fourth'][1]); fire = Vector(SPOTS['f_fire'])
    aim_dir = (Vector(SPOTS['j_brett']) + Vector(SPOTS['v_by'])) / 2 - fire
    T = TL; S = Seq(); I = Matrix.Identity(4)
    S.pad('hide', T['f_burst'], src=base, f0=frames[0], at=I)
    S.walk(arm, 'burst', run, rf[0], vr * 0.75, [home, Vector((1.2, 2.55)), Vector((1.1, 1.95)), fire], blend=0.3)
    S.pad('fire', T['f_flee'], src=idle, f0=idf[0], at=_at(arm, idle, idf[0], fire, aim_dir.normalized()), blend=0.35)
    S.walk(arm, 'flee', run, rf[0] + 10, vr * 0.85, [fire, Vector((1.12, 1.95)), Vector((1.25, 2.5)), home], blend=0.3)
    S.pad('back', T['end'], src=base, f0=frames[0] + 20, at=I, blend=0.5)
    S.log('fourth')
    tgt = (Vector(SPOTS['j_brett']) + Vector(SPOTS['v_by'])) / 2; tgt = Vector((tgt.x, tgt.y, 1.3))

    def overlay(tt, i, lt):
        tag = S.segs[i]['tag']; f = int(round(tt * FPS))
        if tag in ('hide', 'back'):
            _fourth_hold(arm, k, 1.0 if tag == 'hide' else _smooth((lt - 0.4) / 0.8)); _look(arm, door, 0.6)
        elif tag == 'burst':
            _fourth_hold(arm, k, 0.5)
        elif tag == 'fire':
            aimw = _win(tt, T['f_shots'][0] - 0.8, T['f_stare'][0], 0.4, 0.8)
            kick = _pulse(tt, T['f_shots'], 0.03, 0.18)
            _gun_arm(arm, 'R', tgt, max(aimw, 0.6), kick)
            hr = _P(arm, 'Bip01 R Hand'); pel, fwd, right, up = _live(arm)
            _hand_to(arm, 'L', hr - right * 0.05 - up * 0.04, max(aimw, 0.5), hr - up * 0.4 - right * 0.4, palm=right, pw=0.5)
            people.hand_shape(arm, 'L', 'fist', 0.7)
            _look(arm, tgt + Vector((0, 0, 0.3)), 0.7)
            if tt > T['f_stare'][0]: people.bend(arm, 'Bip01 Head', right, 0.15 * _smooth((tt - T['f_stare'][0]) / 0.5))
        elif tag == 'flee':
            _fourth_hold(arm, k, 0.6)
        _record('fourth', arm, f)
    acts['scene'] = people.sequence(arm, base, 'fourth_scene', S.segs, overlay=overlay)
    for a, _, _ in C.values(): bpy.data.actions.remove(a)


# ---------------------------------------------------------------- Vincent
def _vincent_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS

    def wait(f, t):
        _look(arm, Vector((-3.0, 2.9 + 0.3 * math.sin(t * 0.3), 1.6)), 0.3)
    acts['wait'] = people.custom_act(arm, base, frames, 'vincent_wait', wait, _all(arm))
    if not full: return
    C = _clips(arm, 'vincent', {'walk': ('m_walk_neutral_01', dict(inplace=True, cycles=10)), 'idle': ('m_idle_neutral_01', dict(cycles=24)),
                                'idle2': ('m_idle_breathe_01', dict(cycles=10)), 'cin': ('m_crouch_in', {}), 'cid': ('m_crouch_idle', dict(cycles=2)),
                                'cout': ('m_crouch_out', {}), 'turn': ('m_turn_left_180', {})})
    walk, wf, vs = C['walk']; idle, idf, _ = C['idle']; idle2, i2f, _ = C['idle2']
    home, hf = Vector(HOME['vincent'][0]), Vector(HOME['vincent'][1])
    vd, bar, by, wall, hall = (Vector(SPOTS[s]) for s in ('v_door', 'v_bar', 'v_by', 'v_wall', 'v_hall'))
    T = TL; S = Seq(); I = Matrix.Identity(4)
    S.pad('lift', T['v_out'], src=base, f0=frames[0], at=I)
    S.walk(arm, 'out', walk, wf[0], vs, [home, Vector((-3.3, 3.08)), vd])
    S.pad('hall', T['v_in'], src=idle2, f0=i2f[0], at=_at(arm, idle2, i2f[0], vd, (-0.5, -1.0)), blend=0.6)
    S.walk(arm, 'in', walk, wf[0] + 12, vs, [vd, Vector((-2.8, 2.3)), Vector((-2.85, 1.55)), Vector((-2.9, 0.5)), Vector((-2.6, -0.66)), Vector((-1.0, -1.0)),
                                              Vector((0.7, -1.08)), Vector((1.95, -1.2)), Vector((2.62, -0.62)), bar])
    S.pad('smoke', T['v_crouch'], src=idle, f0=idf[0], at=_at(arm, idle, idf[0], bar, (-1.0, 0.0)), blend=0.7)
    ci = C['cin']; S.add('crouch', src=ci[0], f0=ci[1][0], dur=(ci[1][1] - ci[1][0]) / FPS / 1.8, rate=1.8, at=_at(arm, ci[0], ci[1][0], bar, (-1.0, 0.0)), blend=0.5)
    S.pad('down', T['v_rise'], src=C['cid'][0], f0=C['cid'][1][0], at=_at(arm, C['cid'][0], C['cid'][1][0], bar, (-1.0, 0.0)), blend=0.4)
    co = C['cout']; S.add('rise', src=co[0], f0=co[1][0], dur=(co[1][1] - co[1][0]) / FPS / 1.8, rate=1.8, at=_at(arm, co[0], co[1][0], bar, (-1.0, 0.0)), blend=0.4)
    S.pad('case', T['v_take'] + 0.6, src=idle, f0=idf[0] + 90, at=_at(arm, idle, idf[0] + 90, bar, (-1.0, 0.0)), blend=0.6)
    S.walk(arm, 'back', walk, wf[0] + 24, vs, [bar, Vector((2.62, -0.62)), Vector((1.95, -1.2)), Vector((0.7, -1.08)), Vector((-0.6, -0.8)), by])
    S.pad('by', T['to_wall'], src=idle2, f0=i2f[0] + 30, at=_at(arm, idle2, i2f[0] + 30, by, (1.0, 0.25)), blend=0.6)
    S.walk(arm, 'to_wall', walk, wf[0] + 6, vs * 0.85, [by, Vector((-2.4, -0.9)), wall])
    S.pad('holes', T['leave'] + 0.4, src=idle2, f0=i2f[0] + 60, at=_at(arm, idle2, i2f[0] + 60, wall, (-1.0, 0.1)), blend=0.6)
    S.walk(arm, 'leave', walk, wf[0] + 18, vs, [wall, Vector((-3.55, -0.2)), Vector((-3.05, 1.2)), Vector((-2.82, 2.05)), hall])
    S.pad('close', T['v_close'][1] + 0.2, src=idle2, f0=i2f[0] + 90, at=_at(arm, idle2, i2f[0] + 90, hall, (0.0, -1.0)), blend=0.5)
    S.walk(arm, 'to_lift', walk, wf[0] + 30, vs * 0.9, [hall, Vector((-3.2, 3.0)), Vector((-3.75, 3.2)), home + Vector((0.12, 0.0))])
    S.pad('home', T['end'], src=base, f0=frames[0] + 30, at=I, blend=1.0)
    S.log('vincent')
    lip = lambda: _mouth(arm)
    cup_in = R.BAR[1] + 0.02
    case_at = Vector((R.BAR[0] + 0.22, (R.CUPBOARD[0] + R.CUPBOARD[1]) / 2, R.BAR_TOP + 0.05))
    kn = Vector((R.BAR[1] + 0.03, R.CUPBOARD[0] + 0.05, 0.72))
    jules = lambda f: _head_of('jules', f); brett = lambda f: _head_of('brett', f)
    shots = T['v_shots']

    def overlay(tt, i, lt):
        tag = S.segs[i]['tag']; f = int(round(tt * FPS))
        pel, fwd, right, up = _live(arm)
        if tag in ('smoke', 'case', 'by', 'holes', 'close') or tag in ('crouch', 'down', 'rise'):
            puff = _win((tt - 20.0) % 9.0, 0.0, 1.4, 0.5, 0.5) if tt > T['v_light'][1] and tag == 'smoke' else 0.0
            light = _win(tt, T['v_light'][0], T['v_light'][1], 0.5, 0.5)
            if tag == 'smoke' and max(puff, light) > 0:                             # the cigarette to his lips, lit, a drag
                l0, lf_, ls, lu = lip()
                g = l0 + lf_ * 0.06 - lu * 0.02
                _hand_to(arm, 'R', g, max(puff, light), g - lu * 0.3 + ls * 0.2, palm=-lf_, pw=0.5)
                if light > 0: _hand_to(arm, 'L', g + lf_ * 0.03 + ls * 0.03, light, g - lu * 0.3 - ls * 0.2, palm=ls, pw=0.4)
        if tag == 'smoke':
            if T['offer'][0] < tt < T['offer'][1]: people.bend(arm, 'Bip01 Head', up, 0.12 * math.sin((tt - T['offer'][0]) * 6) * _win(tt, *T['offer'], 0.3, 0.3))
            _look(arm, brett(f) if (tt // 6) % 3 == 1 else jules(f), 0.55)
        elif tag in ('crouch', 'down', 'rise'):
            dw = _win(tt, T['cupdoor'][0] - 0.4, T['cupdoor'][1] + 0.2, 0.3, 0.3)
            _hand_to(arm, 'L', kn + Vector((0.06, 0.0, 0)), dw, kn + up * 0.3 - right * 0.3)
            reach = _win(tt, T['case_grab'] - 0.6, T['case_grab'] + 0.1, 0.4, 0.1)
            inside = Vector((cup_in + 0.05, (R.CUPBOARD[0] + R.CUPBOARD[1]) / 2, 0.24))
            if tt < T['case_grab'] + 0.1: _hand_to(arm, 'R', inside, reach, inside + up * 0.4 + right * 0.3)
            else: _hand_to(arm, 'R', pel + fwd * 0.3 * k + up * 0.1 * k, 1.0, pel + right * 0.4)
            _look(arm, inside, 0.7)
        elif tag == 'case':
            put = _smooth((tt - (T['case_put'] - 0.8)) / 0.8)
            held = pel + fwd * 0.32 * k + up * 0.15 * k
            hand_case = held.lerp(case_at + Vector((0.16, -0.08, 0.02)), put)
            if tt < T['case_put'] + 0.1: _hand_to(arm, 'R', hand_case, 1.0, hand_case - up * 0.3 + right * 0.3)
            opn = _win(tt, T['lid_open'][0] - 0.4, T['lid_open'][1] + 0.1, 0.3, 0.3)       # the locks, the lid up
            cls = _win(tt, T['lid_close'][0] - 0.3, T['lid_close'][1], 0.2, 0.3)
            for side, sd in (('L', -1), ('R', 1)):
                g = case_at + Vector((0.18, sd * 0.14, 0.08))
                _hand_to(arm, side, g, max(opn, cls) if tt > T['case_put'] + 0.1 or side == 'L' else 0.0, g - up * 0.3 + right * sd * 0.3, palm=-up, pw=0.5)
            stare = _win(tt, T['lid_open'][1], T['lid_close'][0], 0.4, 0.4)
            for b_ in SPINE: people.bend(arm, b_, right, -0.06 * stare)
            take = _smooth((tt - (T['v_take'] - 0.5)) / 0.5)
            if take > 0:
                h = case_at + Vector((0.2, 0.0, 0.06))
                _hand_to(arm, 'L', h, take, h - up * 0.3 - right * 0.3)
            _look(arm, case_at + Vector((0, 0, 0.1)) if stare > 0.2 else (jules(f) if tt < T['b_up'] else brett(f)), 0.75)
        elif tag in ('back', 'by', 'to_wall', 'holes', 'leave', 'close', 'to_lift'):
            # the case hangs from his left hand
            g = pel - right * 0.22 * k - up * 0.08 * k + fwd * 0.02
            _hand_to(arm, 'L', g, 0.85, g - right * 0.3 + up * 0.2)
            people.hand_shape(arm, 'L', 'fist', 0.8)
        if tag == 'by':
            draw = _smooth((tt - T['v_draw'][0]) / (T['v_draw'][1] - T['v_draw'][0]))
            aim = _win(tt, T['j_shots'][0] - 0.7, T['dead'] + 0.4, 0.5, 0.6)
            kick = _pulse(tt, shots, 0.03, 0.18)
            b = brett(f)
            if aim > 0: _gun_arm(arm, 'R', b - Vector((0, 0, 0.1)), aim, kick)
            elif draw > 0:
                g = pel + fwd * 0.25 * k + right * 0.22 * k
                _hand_to(arm, 'R', g, draw, g - up * 0.3 + right * 0.3, palm=-right, pw=0.5); people.hand_shape(arm, 'R', 'fist', 0.85 * draw)
            fl = _pulse(tt, T['f_shots'], 0.04, 0.4)
            for b_ in SPINE: people.bend(arm, b_, right, 0.08 * fl)
            if T['f_burst'] < tt < T['look_each'][0]: _look(arm, Vector(SPOTS['f_fire'] + (1.5,)), 0.8)
            elif tt > T['look_each'][0]: _look(arm, jules(f), 0.8)
            else: _look(arm, b, 0.7)
        elif tag == 'holes':
            for b_ in SPINE: people.bend(arm, b_, right, -0.12 * _win(tt, T['holes'][0], T['holes'][1], 0.6, 0.6))
            _look(arm, Vector((R.LEFT, -1.5, 1.55)), 0.8)
        elif tag == 'close':
            ck = Vector((R.ENTRY[0] + 0.07, R.PART[1] + 0.03, 0.97))
            hinge = Vector((R.ENTRY[1] - 0.01, (R.PART[0] + R.PART[1]) / 2, 0.97))
            a = math.radians(80) * (1 - _smooth((tt - T['v_close'][0]) / (T['v_close'][1] - T['v_close'][0])))
            kn2 = hinge + Matrix.Rotation(a, 3, 'Z') @ (Vector((R.ENTRY[0] + 0.07, (R.PART[0] + R.PART[1]) / 2 + 0.05, 0.97)) - hinge)
            _hand_to(arm, 'R', kn2, _win(tt, T['v_close'][0] - 0.4, T['v_close'][1], 0.3, 0.3), kn2 - up * 0.4 + right * 0.3)
        _record('vincent', arm, f)
    acts['scene'] = people.sequence(arm, base, 'vincent_scene', S.segs, overlay=overlay)
    for a, _, _ in C.values(): bpy.data.actions.remove(a)


# ---------------------------------------------------------------- Jules
def _jules_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS

    def wait(f, t):
        _look(arm, Vector((-3.0, 2.6 + 0.3 * math.sin(t * 0.27), 1.65)), 0.3)
    acts['wait'] = people.custom_act(arm, base, frames, 'jules_wait', wait, _all(arm))
    if not full: return
    C = _clips(arm, 'jules', {'walk': ('m_walk_cool_01', dict(inplace=True, cycles=10)), 'idle': ('m_idle_neutral_01', dict(cycles=24)),
                              'idle2': ('m_idle_breathe_01', dict(cycles=10)), 'talk': ('m_gestic_talk_cool', dict(cycles=4)),
                              'talk2': ('m_gestic_talk_neutral_02', dict(cycles=3)), 'angry': ('m_gestic_talk_angry_02', dict(cycles=3)),
                              'turn': ('m_turn_left_180', {})})
    walk, wf, vs = C['walk']; idle, idf, _ = C['idle']; idle2, i2f, _ = C['idle2']
    home, hf = Vector(HOME['jules'][0]), Vector(HOME['jules'][1])
    jd, jt, jb, jw, jh = (Vector(SPOTS[s]) for s in ('j_door', 'j_table', 'j_brett', 'j_wall', 'j_hall'))
    T = TL; S = Seq(); I = Matrix.Identity(4); E = (1.0, 0.0)
    at = lambda src, f0, p, h: _at(arm, src, f0, p, h)
    S.pad('lift', T['j_out'], src=base, f0=frames[0], at=I)
    S.walk(arm, 'out', walk, wf[0], vs, [home, Vector((-3.4, 2.88)), jd])
    S.pad('door', T['j_in'], src=idle2, f0=i2f[0], at=at(idle2, i2f[0], jd, (0.0, -1.0)), blend=0.6)
    S.walk(arm, 'in', walk, wf[0] + 10, vs, [jd, Vector((-2.8, 1.85)), Vector((-2.62, 1.0)), jt])
    S.pad('wave', T['talk1'], src=idle, f0=idf[0], at=at(idle, idf[0], jt, E), blend=0.7)
    S.pad('talk1', T['burger_grab'] - 1.0, src=C['talk'][0], f0=C['talk'][1][0], at=at(C['talk'][0], C['talk'][1][0], jt, E), blend=0.8)
    S.pad('burger', T['cup_point'][0], src=idle, f0=idf[0] + 60, at=at(idle, idf[0] + 60, jt, E), blend=0.7)
    S.pad('cup', T['gulls'][0], src=idle, f0=idf[0] + 120, at=at(idle, idf[0] + 120, jt, E), blend=0.6)
    S.pad('gulls', T['gulls'][1] + 0.6, src=idle, f0=idf[0] + 200, at=at(idle, idf[0] + 200, jt, E), blend=0.6)
    S.pad('happy', T['b_up'], src=C['talk2'][0], f0=C['talk2'][1][0], at=at(C['talk2'][0], C['talk2'][1][0], jt, E), blend=0.8)
    S.pad('listen', T['tip'][0] - 0.4, src=idle, f0=idf[0] + 260, at=at(idle, idf[0] + 260, jt, E), blend=0.7)
    S.pad('tip', T['j_step'], src=idle2, f0=i2f[0] + 40, at=at(idle2, i2f[0] + 40, jt, E), blend=0.5)
    S.walk(arm, 'step', walk, wf[0] + 20, vs * 0.8, [jt, Vector((-1.7, 0.42)), jb])
    ag, agf, _ = C['angry']
    t2, t2f, _ = C['talk2']; tc, tcf, _ = C['talk']                       # talk clips that stay where they are (the angry ones walk)
    S.pad('press', T['ezekiel'], src=t2, f0=t2f[0] + 300, at=at(t2, t2f[0] + 300, jb, E), blend=0.7)
    S.pad('ezekiel', T['j_shots'][0] - 0.8, src=tc, f0=tcf[0] + 400, at=at(tc, tcf[0] + 400, jb + Vector((-0.12, 0.05)), E), blend=0.9)
    S.pad('volley', T['to_wall'], src=idle2, f0=i2f[0] + 80, at=at(idle2, i2f[0] + 80, jb + Vector((-0.12, 0.05)), E), blend=0.6)
    S.walk(arm, 'to_wall', walk, wf[0] + 6, vs * 0.85, [jb + Vector((-0.12, 0.05)), Vector((-2.2, -0.2)), jw])
    S.pad('holes', T['leave'], src=idle2, f0=i2f[0] + 120, at=at(idle2, i2f[0] + 120, jw, (-1.0, -0.1)), blend=0.6)
    S.walk(arm, 'leave', walk, wf[0] + 14, vs, [jw, Vector((-3.4, 0.2)), Vector((-2.92, 1.3)), Vector((-2.8, 2.1)), Vector((-2.85, 2.6)), jh])
    S.pad('wait_lift', T['lift_open2'][1], src=idle2, f0=i2f[0] + 160, at=at(idle2, i2f[0] + 160, jh, (-1.0, 0.0)), blend=0.6)
    S.walk(arm, 'into', walk, wf[0] + 22, vs * 0.85, [jh, Vector((-3.7, 2.74)), home + Vector((0.1, 0.0))])
    S.pad('home', T['end'], src=base, f0=frames[0] + 40, at=I, blend=1.0)
    S.log('jules')
    burger = Vector((-1.12, 0.42, R.TABLE_H + 0.05)); cup = Vector((-1.2, 0.12, R.TABLE_H + 0.06)); burger_down = Vector((-1.72, 0.3, R.TABLE_H + 0.05))
    vin = lambda f: _head_of('vincent', f); brett = lambda f: _head_of('brett', f); roger = lambda f: _head_of('roger', f)
    edge = Vector((R.TABLE.x - 0.4, R.TABLE.y, R.TABLE_H))

    def held(pel, fwd, right, up):
        return pel + fwd * 0.3 * k + right * 0.12 * k + up * 0.22 * k

    def overlay(tt, i, lt):
        tag = S.segs[i]['tag']; f = int(round(tt * FPS))
        pel, fwd, right, up = _live(arm)
        lip, lf, ls, lu = _mouth(arm)
        if tag == 'door':
            kw = _win(tt, T['knock'][0], T['knock'][1], 0.25, 0.25)
            g = Vector((-2.92, R.PART[1] + 0.08, 1.35 + 0.025 * math.sin((tt - T['knock'][0]) * 18)))
            _hand_to(arm, 'R', g, kw, g - up * 0.3 + right * 0.3); people.hand_shape(arm, 'R', 'fist', kw)
            _look(arm, Vector((-2.8, 2.0, 1.6)), 0.4)
        elif tag == 'wave':                                                     # "keep chillin'": a hand patting the air at Roger
            w = _win(tt, T['wave'][0], T['wave'][1], 0.4, 0.5)
            g = pel + fwd * 0.25 * k - right * 0.3 * k + up * (0.12 + 0.06 * math.sin((tt - T['wave'][0]) * 7)) * k
            _hand_to(arm, 'L', g, w, g - up * 0.3 - right * 0.3, palm=-up, pw=0.7)
            _look(arm, roger(f), 0.85)
        elif tag in ('talk1', 'happy', 'listen'):
            tgt = brett(f)
            if tag == 'happy' and T['happy'][0] < tt < T['happy'][1]: tgt = vin(f)
            _look(arm, tgt, 0.75)
        elif tag == 'burger':
            reach = _smooth((tt - (T['burger_grab'] - 0.8)) / 0.8)
            put = _smooth((tt - (T['burger_put'] - 0.8)) / 0.8)
            bite = _win(tt, T['bite'][0], T['bite'][1], 0.5, 0.5)
            offer = _win(tt, T['offer'][0], T['offer'][1], 0.5, 0.6)
            h = held(pel, fwd, right, up)
            g = burger.lerp(h, _smooth((tt - T['burger_grab']) / 0.7)) if tt < T['burger_put'] - 0.8 else h.lerp(burger_down, put)
            g = g.lerp(lip + lf * 0.05 - lu * 0.03, bite)
            vh = vin(f); g = g.lerp(h + (vh - h).normalized() * 0.25, offer)
            w = reach * (1 - _smooth((tt - T['burger_put']) / 0.5))
            _hand_to(arm, 'R', g, w, g - up * 0.4 + right * 0.35, palm=up if bite < 0.5 else -lf, pw=0.5)
            people.hand_shape(arm, 'R', 'fist', 0.5 * w)
            chew = 0.04 * math.sin(tt * 11) * _win(tt, T['bite'][1], T['bite'][1] + 6, 0.2, 0.5)
            people.bend(arm, 'Bip01 Head', right, chew)
            _look(arm, vh if offer > 0.3 else (burger if tt < T['burger_grab'] + 0.4 else brett(f)), 0.7)
        elif tag == 'cup':
            pt = _win(tt, *T['cup_point'], 0.3, 0.3)
            people.point_at(arm, 'R', cup, w=pt, reach=0.45)
            reach = _smooth((tt - (T['cup_grab'] - 0.7)) / 0.7) * (1 - _smooth((tt - T['cup_put']) / 0.5))
            sip = _win(tt, T['sip'][0], T['sip'][1], 0.6, 0.6)
            h = held(pel, fwd, right, up)
            g = cup.lerp(h, _smooth((tt - T['cup_grab']) / 0.7)) if tt < T['cup_put'] - 0.7 else h.lerp(cup, _smooth((tt - (T['cup_put'] - 0.7)) / 0.7))
            g = g.lerp(lip + lf * 0.05 - lu * 0.2, sip)
            if pt <= 0.05: _hand_to(arm, 'R', g, reach, g - up * 0.4 + right * 0.35, palm=-right, pw=0.5)
            people.bend(arm, 'Bip01 Head', right, 0.12 * sip)
            _look(arm, cup if tt < T['cup_grab'] + 0.3 else brett(f), 0.6)
        elif tag == 'gulls':
            pt = _win(tt, *T['gulls'], 0.4, 0.4)
            people.point_at(arm, 'R', roger(f), w=pt, reach=0.5, jab=0.04 * math.sin(tt * 5))
            _look(arm, roger(f), 0.85)
        elif tag == 'tip':
            grab = _win(tt, T['tip'][0], T['tip'][2], 0.4, 0.4)
            push = _smooth((tt - T['tip'][1]) / 0.5)
            for side, sd in (('L', -1), ('R', 1)):
                g = edge + Vector((0.05, sd * 0.25, 0.02)) + Vector((0.12, -0.3, 0.3)) * push
                _hand_to(arm, side, g, grab, g - up * 0.4 + right * sd * 0.4, palm=-up + fwd, pw=0.5)
            for b_ in SPINE: people.bend(arm, b_, right, -0.15 * grab)
            _look(arm, edge, 0.7)
        if tt > T['draw'][0] and tag in ('listen', 'tip', 'step', 'press', 'ezekiel', 'volley', 'to_wall', 'holes'):
            # the pistol from his waistband: at Roger, then on Brett; held low between; tucked away when they leave
            draw = _smooth((tt - T['draw'][0]) / (T['draw'][1] - T['draw'][0])) * (1 - _smooth((tt - T['tuck'][0]) / 0.6))
            aim_r = _win(tt, T['draw'][1], T['roger_shots'][-1] + 0.4, 0.3, 0.6)
            cheek = _win(tt, *T['cheek'], 0.5, 0.5)
            aim_b = max(_win(tt, T['shoulder'] - 1.0, T['shoulder'] + 0.6, 0.5, 0.6), _win(tt, T['j_shots'][0] - 0.7, T['dead'] + 0.4, 0.5, 0.6))
            kick = _pulse(tt, T['roger_shots'] + (T['shoulder'],) + T['j_shots'], 0.03, 0.18)
            if tag == 'tip': pass
            elif aim_r > 0: _gun_arm(arm, 'R', roger(f), aim_r, kick)
            elif cheek > 0:
                b = brett(f); g = b + fwd * -0.16 * k + up * -0.02
                _hand_to(arm, 'R', g, cheek, g - up * 0.4 + right * 0.3, palm=-right, pw=0.5); people.hand_shape(arm, 'R', 'fist', 0.85)
            elif aim_b > 0: _gun_arm(arm, 'R', brett(f) - Vector((0, 0, 0.08)), aim_b, kick)
            elif draw > 0:
                g = pel + fwd * 0.22 * k + right * 0.22 * k - up * 0.05 * k
                _hand_to(arm, 'R', g, draw, g - up * 0.3 + right * 0.3, palm=-right, pw=0.5); people.hand_shape(arm, 'R', 'fist', 0.85 * draw)
        if tag in ('press', 'ezekiel'):
            lean = _win(tt, *T['lean'], 1.0, 1.0)
            for b_, a in zip(SPINE, (0.08, 0.1, 0.1)): people.bend(arm, b_, right, -a * lean)
            _look(arm, brett(f), 0.9)
        elif tag == 'volley':
            if T['f_burst'] < tt < T['look_each'][0]: _look(arm, Vector(SPOTS['f_fire'] + (1.5,)), 0.85)
            elif tt > T['look_each'][0]: _look(arm, vin(f), 0.85)
            else: _look(arm, brett(f), 0.8)
            fl = _pulse(tt, T['f_shots'], 0.04, 0.4)
            for b_ in SPINE: people.bend(arm, b_, right, 0.08 * fl)
        elif tag == 'holes':
            for b_ in SPINE: people.bend(arm, b_, right, -0.12 * _win(tt, T['holes'][0], T['holes'][1], 0.6, 0.6))
            pt = _win(tt, T['holes'][0] + 1.4, T['holes'][0] + 3.0, 0.4, 0.4)
            people.point_at(arm, 'L', Vector((R.LEFT, -1.4, 1.7)), w=pt, reach=0.45)
            _look(arm, Vector((R.LEFT, -1.4, 1.6)), 0.85)
        _record('jules', arm, f)
    acts['scene'] = people.sequence(arm, base, 'jules_scene', S.segs, overlay=overlay)
    for a, _, _ in C.values(): bpy.data.actions.remove(a)


# ---------------------------------------------------------------- the room's rig
def _frames_of(arm, act, fn):
    """fn(arm) at every frame of an act (frame 0 = its start)."""
    out = {}; f0 = int(act.frame_range[0])
    for f in range(f0, int(act.frame_range[1]) + 1):
        people.pose_at(arm, act, f); out[f - f0] = fn(arm)
    return out


def _room_rig(seated, col):
    """The room's rig and its acts: at rest, and the scene (the doors, the case, the table, the food, the guns, the
    flashes, the stains, the holes)."""
    import rooms.pulp_fiction_rig as RG
    arm, mesh = RG.make_rig(MATS, col)
    c = dict(who='room', work=WORK['room'], idles={'scene': (None, 0.0)}, cue={}, roam=())
    acts = {'rest': RG.rest_act(arm, 'room_rest')}
    FPS = people.FPS; F = lambda s: int(round(s * FPS))
    by = {cc['who']: (cc, a) for cc, a, me in seated}
    if 'scene' in by['jules'][0]['acts']:
        n = int(round(TL['end'] * FPS)); T = TL
        sc = lambda who: by[who][0]['acts']['scene']
        grips = {who: _frames_of(by[who][1], sc(who), lambda a: (_grip(a, 'L'), _grip(a, 'R'))) for who in ('jules', 'vincent', 'fourth')}
        jr = {f: g[1] for f, g in grips['jules'].items()}; vr = {f: g[1] for f, g in grips['vincent'].items()}; vl = {f: g[0] for f, g in grips['vincent'].items()}
        fr = {f: g[1] for f, g in grips['fourth'].items()}
        L = RG.Track(arm, n)
        # the lift, the front door, the bathroom door, the cupboard
        RG.slide(L, 'lift_l', F(T['lift_open'][0]), F(T['lift_open'][1]), Vector(), Vector((0, -0.38, 0)))
        RG.slide(L, 'lift_r', F(T['lift_open'][0]), F(T['lift_open'][1]), Vector(), Vector((0, 0.38, 0)))
        for part, s in (('lift_l', -1), ('lift_r', 1)):
            RG.slide(L, part, F(T['lift_open'][1]) + 30, F(T['lift_open'][1]) + 60, Vector((0, s * 0.38, 0)), Vector())
            RG.slide(L, part, F(T['lift_open2'][0]), F(T['lift_open2'][1]), Vector(), Vector((0, s * 0.38, 0)))
            RG.slide(L, part, F(T['lift_close'][0]), F(T['lift_close'][1]), Vector((0, s * 0.38, 0)), Vector())
        RG.swing(L, 'entry', F(T['door_open'][0]), F(T['door_open'][1]), 0.0, math.radians(70))
        RG.swing(L, 'entry', F(T['door_open'][1]), F(T['door_open'][1] + 0.8), math.radians(70), math.radians(88))
        RG.swing(L, 'entry', F(T['v_close'][0]), F(T['v_close'][1]), math.radians(88), 0.0)
        RG.swing(L, 'bathdoor', F(T['f_burst']), F(T['f_burst'] + 0.3), 0.0, math.radians(-105))
        RG.swing(L, 'bathdoor', F(T['f_door_close'][0]), F(T['f_door_close'][1]), math.radians(-105), 0.0)
        RG.swing(L, 'cupdoor', F(T['cupdoor'][0]), F(T['cupdoor'][1]), 0.0, math.radians(-100))
        RG.swing(L, 'cupdoor', F(T['cupdoor_close'][0]), F(T['cupdoor_close'][1]), math.radians(-100), 0.0)
        # the burger and the cup in Jules's hand, back on the table; the table tipped over, everything off it
        RG.carry(L, 'burger', F(T['burger_grab']), F(T['burger_put']), jr, home=(Vector((-1.72, 0.3, R.TABLE_H + 0.035)), Quaternion()))
        RG.carry(L, 'cup', F(T['cup_grab']), F(T['cup_put']), jr)
        # pushed away from Jules, it goes over onto its top's rim toward the south-west, its legs up (the rim kept on the floor)
        rest = L.rest['room_table']; d = Vector((-0.55, -0.83, 0)).normalized(); piv = rest + d * 0.31
        ax = Vector((0, 0, 1)).cross(d).normalized()
        rim = [rest + Vector((math.cos(a) * R.TABLE_R, math.sin(a) * R.TABLE_R, R.TABLE_H)) for a in [i * math.pi / 12 for i in range(24)]]
        for f in range(F(T['tip'][1]), n + 1):
            u = RG.ease((f - F(T['tip'][1])) / F(0.6)); q = Quaternion(ax, math.radians(96) * u)
            lift = max(0.0, -min((piv + q @ (p - piv)).z for p in rim))
            L.set('table', f, piv + q @ (rest - piv) + Vector((0, 0, lift)), q)
        lands = {'burger': (-1.9, -0.8), 'wrap0': (-1.2, -0.95), 'wrap1': (-1.75, -0.55), 'bag': (-1.45, -1.1), 'cup': (-0.95, -0.7), 'fries': (-1.35, -0.75)}
        rnd = random.Random(4)
        for j, (part, (x, y)) in enumerate(lands.items()):
            z = 0.06 if part == 'bag' else (0.05 if part == 'cup' else 0.02)
            rot = Quaternion(Vector((0, 0, 1)), rnd.uniform(-2, 2)) @ (Quaternion(Vector((1, 0, 0)), math.pi / 2) if part in ('bag', 'cup') else Quaternion())
            RG.fall(L, part, F(T['tip'][1] + 0.1) + j, Vector((x, y, z)), rot)
        # the case: out of the cupboard in Vincent's right hand, onto the counter, its lid up and down; in his left after
        top = (Vector((R.BAR[0] + 0.22, (R.CUPBOARD[0] + R.CUPBOARD[1]) / 2, R.BAR_TOP + 0.002)), Quaternion())
        RG.carry(L, 'case', F(T['case_grab']), F(T['case_put']), vr, settle=0.3, home=top)
        hang = Matrix(((0, 1, 0, 0), (0, 0, 1, 0), (1, 0, 0, 0), (0, 0, 0, 1)))                # in the hand's grip frame: the handle up
        hang = Matrix.Translation((0.0, -0.02, -0.03)) @ hang @ Matrix.Translation(-Vector((RG.CASE_D / 2 + 0.03, 0, RG.CASE_H / 2)))   # the handle in his fist
        RG.follow(L, 'case', F(T['v_take']), n, vl, hang)
        for f in range(n + 1):                                                  # the lid rides on the case, swung on its hinge
            p, q, s = L.get('case', f)
            ang = -math.radians(108) * (_smooth((f / FPS - T['lid_open'][0]) / (T['lid_open'][1] - T['lid_open'][0])) - _smooth((f / FPS - T['lid_close'][0]) / (T['lid_close'][1] - T['lid_close'][0])))
            L.set('lid', f, p + q @ RG.LID_HINGE, q @ Quaternion(Vector((0, 1, 0)), ang), s)
        # the guns: in the hand from the draw, away when tucked; the flashes at each shot
        gun = {'jules': (jr, F(T['draw'][0] + 0.3), F(T['tuck'][1])), 'vincent': (vr, F(T['v_draw'][0] + 0.3), F(T['tuck'][1] + 0.4)), 'fourth': (fr, 0, n)}
        for who, (hm, f0, f1) in gun.items():
            RG.follow(L, f'gun_{who}', f0, f1, hm, Matrix.Translation((0.0, 0.0, -0.01)))
        muzzle = {'jules': 0.17, 'vincent': 0.18, 'fourth': 0.26}
        for who, shots in (('jules', T['roger_shots'] + (T['shoulder'],) + T['j_shots']), ('vincent', T['v_shots']), ('fourth', T['f_shots'])):
            hm = gun[who][0]
            for s in shots:
                RG.follow(L, f'flash_{who}', F(s), F(s) + 2, hm, Matrix.Translation((muzzle[who], 0.0, 0.05)))
                for f in (F(s) + 3,): L.set(f'flash_{who}', f, RG.HIDE, Quaternion(), 0.0)
        # the stains: on Roger's chest at each of his shots, on Brett's shoulder, then his chest
        rch = {j: _frames_of(by['roger'][1], sc('roger'), lambda a, j=j: _chest(a, depth=0.115 * K['roger'], dx=(-0.04, 0.05, 0.0)[j], dz=(0.02, -0.03, -0.09)[j])) for j in range(3)}
        for j, s in enumerate(T['roger_shots']):
            RG.follow(L, f'stain_roger{j}', F(s) + 1, n, rch[j], Matrix.Scale(1.0, 4))
        bsh = _frames_of(by['brett'][1], sc('brett'), lambda a: _chest(a, 'Bip01 R UpperArm', depth=0.08, dz=-0.02))
        RG.follow(L, 'stain_brett0', F(T['shoulder']) + 1, n, bsh)
        for j in range(1, 4):
            bc = _frames_of(by['brett'][1], sc('brett'), lambda a, j=j: _chest(a, depth=0.14 * K['brett'], dx=(-0.05, 0.04, 0.0)[j - 1], dz=(0.0, -0.05, 0.05)[j - 1]))
            RG.follow(L, f'stain_brett{j}', F(T['j_shots'][j]) + 1, n, bc)
        # the six holes in the wall where the man's shots went
        for j, s in enumerate(T['f_shots']):
            RG.show(L, f'hole{j}', F(s) + 2)
        acts['scene'] = L.key('room_scene')
    c['acts'] = acts
    return [(c, arm, mesh)]


# ---------------------------------------------------------------- bake and export
def bake(sc, objs, phantoms, seated, args):
    """The room's light baked into atlases (the people and the rig out of it); then room.glb, the people, the rig and
    room.json."""
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
        pelvis = 'room_root' if c['who'] == 'room' else 'Bip01 Pelvis'
        people.export_person(arm, mesh, c['acts'], os.path.join(out, f"{c['who']}.glb"), roam=c.get('roam', ()), pelvis=pelvis)
        metas.append(person_meta(c))
    return metas


def _capture_meta():
    """How to light the people as the bake lit the room (three.js: y up, z = -Blender y): the bulbs as small bright
    spheres, the windows; captured in the living room, the kitchen and the hallway."""
    bulbs = []
    for l in RIG['lights']:
        if l.type != 'LIGHT' or l.data.type != 'POINT': continue
        r = 0.04; e = l.data.energy
        bulbs.append({'x': round(l.location.x, 3), 'y': round(l.location.z, 3), 'z': round(-l.location.y, 3), 'r': r,
                      'L': round(e / (4 * math.pi * r ** 2) / 60, 2), 'color': [round(v, 3) for v in l.data.color]})
    at = [[round(v, 3) for v in (p.x, p.z, -p.y)] for p in (Vector((-1.6, 0.0, 1.1)), Vector((3.0, 0.2, 1.2)), Vector((-2.4, 2.9, 1.3)), Vector((2.2, 2.9, 1.2)))]
    return {'capture': {'ceiling': [0.34, 0.33, 0.3], 'walls': [0.3, 0.32, 0.29], 'emitters': bulbs, 'windows': [], 'at': at}}


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
