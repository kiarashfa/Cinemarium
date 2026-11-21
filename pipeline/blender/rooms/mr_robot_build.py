# Mr. Robot: assemble the arcade (the lanes, the counter, the tables, the machines, the signs) and its people (Elliot,
# Mr. Robot, Tyrell); then preview, bake and export.
import math, os
import bpy
from mathutils import Vector, Matrix
import cine, people, stages
from stages import camera
import rooms.mr_robot as R

ROOM = 'mr-robot'
OUT = os.path.join(cine.OUT, ROOM)
WEB = os.path.join(cine.ROOT, 'public', 'rooms', ROOM)
PEOPLE_TEX = os.path.join(cine.OUT, 'people')
ARGS = {}
SEATED = []
MATS = {}
RIG = {'lights': [], 'gun': []}


def build(args):
    ARGS.clear(); ARGS.update(args)
    sc = cine.reset(int(args.get('samples', 256)))
    M = R.mats(); MATS.update(M)
    static, phantom, crowd = cine.coll('static'), cine.coll('phantom'), cine.coll('people')
    seated = [] if args.get('nocast') else cast(crowd, args)
    SEATED[:] = seated
    R.shell(M, static, phantom)
    R.lanes(M, static)
    R.concession(M, static)
    R.popcorn(M, static)
    R.tables(M, static)
    R.chair(M, static)
    R.right_side(M, static)
    R.clutter(M, static)
    RIG['gun'] = R.gun(M, static)
    RIG['lights'] = R.lights()
    objs = [o for o in static.objects if o.type == 'MESH']; phantoms = [o for o in phantom.objects if o.type == 'MESH']
    bpy.context.view_layer.update()
    cine.bake_ready(objs + phantoms)
    for o in objs + phantoms:
        if not o.data.uv_layers: cine.world_uv(o, 1.0)
        elif 'UVMap' not in o.data.uv_layers: o.data.uv_layers[0].name = 'UVMap'
    R.section(objs, M)
    _place_gun(seated)
    objs = _merge(objs)
    for o in phantoms: cine.phantom(o)
    cine.check_module(objs)
    cams = {'case': camera('cam_case', (0.6, -17.0, 7.4), (0.2, 0.4, 0.9), 30),
            'close': camera('cam_close', (0.4, -7.4, 2.7), (0.0, 0.6, 1.0), 40),
            'master': camera('cam_master', (-0.6, -3.3, 1.6), (-1.4, 0.4, 1.0), 62),      # the night's master: the table, the counter, the lanes
            'gun': camera('cam_gun', (-0.2, -3.0, 1.5), (-1.3, -0.4, 1.2), 46),
            'lanes': camera('cam_lanes', (-1.0, -1.8, 1.7), (-0.6, 3.2, 1.4), 60),
            'right': camera('cam_right', (0.2, -2.6, 1.6), (4.2, 0.6, 1.3), 60),
            'counter': camera('cam_counter', (-1.2, 0.6, 1.6), (-4.2, -1.6, 1.2), 60),
            'top': camera('cam_top', (0.0, 0.0, 14.0), (0.0, 0.1, 0.0), 38),
            'f_tyrell': camera('cam_f_tyrell', (-1.2, -1.0, 1.3), (-2.2, -0.92, 1.15), 34),
            'f_robot': camera('cam_f_robot', (0.2, -0.8, 1.6), (-1.2, -0.7, 1.5), 34),
            'f_elliot': camera('cam_f_elliot', (-1.0, -1.4, 1.6), (-1.9, 0.2, 1.5), 34),
            'side': camera('cam_side', (12.0, -6.0, 6.0), (0.5, 0.2, 0.8), 34),
            'h_tyrell': camera('cam_h_tyrell', (-2.8, -1.5, 1.3), (-2.2, -0.92, 1.18), 30),
            'h_robot': camera('cam_h_robot', (-1.25, -0.5, 1.62), (-0.35, 0.02, 1.6), 30),
            'h_elliot': camera('cam_h_elliot', (-2.15, -0.6, 1.62), (-1.88, 0.22, 1.62), 30)}
    return sc, M, objs, list(phantom.objects), seated, cams


KEEP = ('left_', 'back_', 'kerb', 'floor', 'subfloor', 'coney_wall', 'gun_')


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
            _pose_gun(float(t))
            stages.render(sc, cams[which], samples, path.replace('.png', f'_{act}_{float(t):05.1f}.png'), (960, 600), float(ARGS.get('exposure', 0.0)))
        return
    for spec in filter(None, str(ARGS.get('pose', '')).split(',')):
        who, act, f = spec.split(':')
        for c, arm, mesh in SEATED:
            if c['who'] == who and act in c['acts']: people.pose_at(arm, c['acts'][act], int(c['acts'][act].frame_range[0]) + int(f))
    stages.render(sc, cams[which], samples, path, size, float(ARGS.get('exposure', 0.0)))


# ---------------------------------------------------------------- the cast
# The loop (one clock, TL): Tyrell at the long table running the hack, Elliot standing at its end talking to him, Mr.
# Robot by the lanes watching. Mr. Robot goes to the popcorn machine, digs the pistol out of the kettle, comes up
# behind Tyrell and puts it to the back of his head; Tyrell gets up and turns; Mr. Robot steps away and aims at him
# arm's length; Tyrell comes a step toward him; the trigger: it jams. Tyrell talks (an act of God, they are meant to
# work together), steps in and sets the barrel to his own forehead (pull it again); Mr. Robot lowers it; Tyrell
# embraces him. Mr. Robot puts the gun back in the popcorn and returns to the lanes; Tyrell sits back down to the
# keys; Elliot, who watched it all from the lanes, comes back to the table. Costumes: people_textures.mr_robot.
from rooms.twin_peaks_build import Seq, _at, _clips, _idle, _look, _hand_to, _smooth, _win, _live, _P, SPINE, FINGERS, ALL


def _tex(who, prefix, *names):
    return {f'{prefix}_{n}.tga': f'{who}/{prefix}_{n}.png' for n in names}


HEAD = {w: os.path.join(cine.OUT, 'people', w, f'{w}_head.glb') for w in ('elliot', 'robot', 'tyrell')}
HEAD_FIT = {                                      # who -> swap_head settings (eyes measured on each head by raycast)
    'elliot': dict(front='-y', eyes=((-0.11, -0.25, 0.11), (0.073, -0.25, 0.11)), cut=0.0, fan_cut=-0.12, keep_r=(0.3, 0.3)),
    'robot': dict(front='-y', eyes=((-0.113, -0.30, -0.013), (0.113, -0.30, -0.007)), cut=0.0, fan_cut=-0.12, keep_r=(0.3, 0.3)),   # behind his lenses
    'tyrell': dict(front='-y', eyes=((-0.107, -0.323, -0.037), (0.117, -0.323, -0.033)), cut=0.0, fan_cut=-0.12, keep_r=(0.3, 0.3)),
}
CAST = [
    dict(who='elliot', avatar='Male_Adult_20', shape=('lean', 0.6), height=1.75, tex=_tex('elliot', 'm027', 'body_color', 'body_normal')),
    dict(who='robot', avatar='Male_Adult_06', shape=None, height=1.74, cap=True, tex=_tex('robot', 'm011', 'body_color', 'body_normal')),
    dict(who='tyrell', avatar='Business_Male_01', shape=('lean', 0.5), height=1.84, tex=_tex('tyrell', 'm005', 'body_color', 'body_normal')),
]
for c in CAST:
    if c['who'] in HEAD_FIT and os.path.exists(HEAD[c['who']]): c['head'] = dict(glb=HEAD[c['who']], **HEAD_FIT[c['who']])
K = {c['who']: c['height'] / 1.78 for c in CAST}

SEAT, SEAT_F = R.CHAIR
R0 = ((-0.35, 0.02), (-1.0, -0.55))               # Mr. Robot's place by the lanes, watching
E0 = ((-1.88, 0.22), (-0.35, -1.0))               # Elliot at the table's end, talking to Tyrell
E1 = ((-1.05, 0.06), (-0.3, -1.0))                # where Elliot stands back to watch
P_STAND = (-2.05, -2.2)                           # behind the popcorn machine (it faces the front: its door is here)
P_FACE = (0.0, -1.0)
B_SPOT = ((SEAT.x + 0.58, SEAT.y), (-1.0, 0.0))   # behind Tyrell's chair
R_SPOT = ((-1.25, -1.62), (-1.0, 0.0))            # where he aims from
T_SPOT = ((-2.4, -1.6), (1.0, 0.0))               # Tyrell, clear of the chair, facing him
T2 = ((-1.76, -1.62), (1.0, 0.0))                 # Tyrell with the barrel at his forehead
T_HUG = ((-1.56, -1.62), (1.0, 0.0))
UP_END = (-2.52, -0.92)                           # where he stands after rising from the chair
HOME = {'tyrell': ((SEAT.x + 0.04, SEAT.y), (SEAT_F.x, SEAT_F.y)), 'elliot': E0, 'robot': R0}
BASES = {'tyrell': 'm_sit_chair_breathe_01', 'elliot': 'm_idle_neutral_01', 'robot': 'm_idle_breathe_01'}
WORK = {'tyrell': ('wait', 6, 12), 'elliot': ('wait', 6, 12), 'robot': ('wait', 6, 12)}
FIRST = {'robot': 'scene'}
CUE = {'robot': {'scene': {'tyrell': 'scene', 'elliot': 'scene'}}}
TL = dict(r_go=(14.0, 19.5), reach=(19.5, 23.5), grab=21.3, r_behind=(23.5, 28.5), head=(28.5, 33.0), t_up=(32.0, 35.0), r_away=(33.4, 36.8),
          t_turn=(35.0, 36.3), t_step=(36.3, 37.9), t_turnb=(37.9, 39.1), aim=37.4, click=40.6, look_gun=(41.2, 43.2), talk=(43.2, 70.0),
          t_in=(70.0, 72.4), forehead=(72.4, 80.0), lower=(80.0, 82.4), hug=(82.6, 88.0), r_back=(88.2, 95.0), put=(95.0, 98.0), release=96.6,
          r_home=(98.0, 105.5), t_back=(88.4, 95.0), t_turn2=(95.0, 96.4), t_sit=(96.4, 99.6), e_back=(15.0, 17.6), e_home=(100.0, 103.2), end=112.0)
ROUTE_GO = [R0[0], (-0.85, -1.75), (-1.55, -2.2), P_STAND]
ROUTE_BEHIND = [P_STAND, (-1.45, -1.75), (-1.42, -1.2), B_SPOT[0]]
ROUTE_AWAY = [B_SPOT[0], (-1.3, -1.1), (-0.95, -1.4), (-1.05, -1.66), R_SPOT[0]]
ROUTE_BACK = [R_SPOT[0], (-1.4, -2.05), (-1.75, -2.3), P_STAND]
ROUTE_HOME = [P_STAND, (-1.45, -2.0), (-0.85, -1.4), R0[0]]
ROUTE_T_BACK = [T_HUG[0], (-2.0, -1.78), (-2.45, -1.45), (UP_END[0], UP_END[1] - 0.18)]
REC = {}                                          # who -> {frame: {'head', 'hand', ...}}
GUN = {'who': 'robot', 'act': 'scene', 'prop': 'gun_', 'hand': 'R', 'grab': TL['grab'], 'release': TL['release']}   # the pistol, carried
SITTERS = ('tyrell',)


def _record(who, arm, f, **extra):
    d = {'head': _P(arm, 'Bip01 Head'), 'sR': _P(arm, 'Bip01 R UpperArm'), 'sL': _P(arm, 'Bip01 L UpperArm'), 'chest': _P(arm, 'Bip01 Spine2'),
         'hand': people._world(arm, arm.pose.bones['Bip01 R Hand']).copy()}
    d.update(extra); REC.setdefault(who, {})[f] = d


def _rec(who, f, key='head'):
    r = REC.get(who, {})
    if not r: (x, y), _ = HOME[who]; return Vector((x, y, 1.15 if who in SITTERS else 1.62))
    return (r.get(f) or r[min(r, key=lambda g: abs(g - f))])[key]


def _long(arm, who, clip, key, inplace=False):
    n = int(round(TL['end'] * people.FPS)) + 90
    return people.retarget(arm, clip, cycles=80, limit=n, inplace=inplace, action_name=f'{who}_src_{key}')


def _route(pts):
    return [tuple(p) for p in pts]


def _cap(arm, mesh, tilt=16.0, brim=74.0, t=0.011, visor=0.07, res=(48, 18)):
    """Mr. Robot's baseball cap, faded khaki: a six-panel crown cast down onto his head (over the sculpted hair) and
    set `t` out, its band low over the brow and the ears, a button on top; a curved visor out over the eyes, dipping a
    little. Skinned to the head."""
    import bmesh
    J = people._joints(arm); eye = (J['Bip01 LEye'] + J['Bip01 REye']) / 2
    c = Vector((eye.x, eye.y + 0.05, eye.z + 0.012))
    n = Vector((0, math.sin(math.radians(tilt)), math.cos(math.radians(tilt))))
    side = Vector((1, 0, 0)); back = n.cross(side).normalized()           # back: +y (the avatar faces -y)
    bvh = people._bvh(mesh)
    nu, nv = res; bm = bmesh.new(); rings = []
    for j in range(nv + 1):
        v = math.radians(brim) * (1 - j / nv); row = []
        for i in range(nu):
            u = 2 * math.pi * i / nu
            d = (n * math.cos(v) + (side * math.cos(u) + back * math.sin(u)) * math.sin(v)).normalized()
            hit = bvh.ray_cast(c + d * 0.3, -d, 0.3)
            p = hit[0] if hit[0] is not None else c + d * 0.1
            row.append(bm.verts.new(p + d * t))
        rings.append(row)
    top = bm.verts.new(c + n * (max((r.co - c).length for r in rings[-1]) + 0.004))
    for j in range(nv):
        a, b = rings[j], rings[j + 1]
        for i in range(nu): bm.faces.new((a[i], a[(i + 1) % nu], b[(i + 1) % nu], b[i]))
    for i in range(nu): bm.faces.new((rings[-1][i], rings[-1][(i + 1) % nu], top))
    inner = [bm.verts.new(c + (v.co - c) * 0.95) for v in rings[0]]
    for i in range(nu): bm.faces.new((inner[i], inner[(i + 1) % nu], rings[0][(i + 1) % nu], rings[0][i]))
    # the visor: from the front third of the band's edge, out and a little down, curved across
    front = [k for k in range(nu) if math.sin(2 * math.pi * k / nu) < -0.55]          # the band's front (-y)
    front.sort(key=lambda k: math.cos(2 * math.pi * k / nu))
    base = [rings[0][k].co.copy() for k in front]
    fwd = Vector((0, -1, -0.28)).normalized()
    rows = 5; vis = []
    for r in range(rows + 1):
        s = r / rows; row = []
        for k, p in enumerate(base):
            x = (k / (len(base) - 1)) * 2 - 1
            out = visor * (1 - 0.35 * x * x) * s
            row.append(bm.verts.new(p + fwd * out + Vector((0, 0, -0.012 * s * (1 - x * x)))))
        vis.append(row)
    under = [[bm.verts.new(v.co - Vector((0, 0, 0.004))) for v in row] for row in vis]
    for r in range(rows):
        for k in range(len(base) - 1):
            bm.faces.new((vis[r][k], vis[r][k + 1], vis[r + 1][k + 1], vis[r + 1][k]))
            bm.faces.new((under[r + 1][k], under[r + 1][k + 1], under[r][k + 1], under[r][k]))
    for k in range(len(base) - 1): bm.faces.new((vis[rows][k], vis[rows][k + 1], under[rows][k + 1], under[rows][k]))
    for f in bm.faces: f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    cloth = bpy.data.materials.get('robot_cap') or cine.material('robot_cap', (0.26, 0.21, 0.14), rough=0.9, sheen=0.3, sheen_tint=(0.3, 0.28, 0.24))
    people._join_to_head(mesh, bm, 'cap', [cloth])
    cine.log('cap on', mesh.get('person', mesh.name))


def make_person(c, col):
    """One of them, standing at the origin facing -y: the avatar, its build, its head, its height."""
    tex = {k: os.path.join(PEOPLE_TEX, v) for k, v in c.get('tex', {}).items() if os.path.exists(os.path.join(PEOPLE_TEX, v))}
    arm, mesh = people.load_avatar(c['avatar'], textures=tex, collection=col)
    arm.animation_data_clear()
    mesh['person'] = c['who']; arm['person'] = c['who']
    if c.get('shape'): people.reshape(arm, mesh, *c['shape'])
    if c.get('head'):
        h = c['head']
        people.swap_head(arm, mesh, h['glb'], None, h['front'], h['eyes'], cut=h.get('cut', 0.0), fan_cut=h.get('fan_cut', -0.03), tone=h.get('tone'),
                         neck_skin=h.get('neck_skin', False), scalp=h.get('scalp'))
        if h.get('keep_r'):
            from rooms.rear_window_build import _bust_cut
            _bust_cut(arm, mesh, c['who'], h['keep_r'])
        people.remove_hair_cards(mesh)
    if c.get('cap'):
        if not c.get('head'): people.remove_hair_cards(mesh)
        _cap(arm, mesh)
    for ca in list(mesh.data.color_attributes): mesh.data.color_attributes.remove(ca)
    bpy.context.view_layer.update()
    top = max((mesh.matrix_world @ v.co).z for v in mesh.data.vertices)
    s = c['height'] / top
    arm.scale = arm.scale * s; arm.location = (arm.location.x, arm.location.y, arm.location.z * s)
    bpy.context.view_layer.update()
    return arm, mesh


def cast(col, args):
    """Load, dress, shape and place them, and bake their acts (cached: retargets and IK take minutes)."""
    full = bool(args.get('full'))
    spec = {'cast': CAST, 'bases': BASES, 'work': WORK, 'cue': CUE, 'tl': TL, 'home': HOME, 'routes': [ROUTE_GO, ROUTE_BEHIND, ROUTE_AWAY, ROUTE_BACK, ROUTE_HOME, ROUTE_T_BACK],
            'spots': [R_SPOT, T_SPOT, T2, T_HUG, B_SPOT, E1], 'chair': [list(SEAT), list(SEAT_F)], 'seat_h': R.SEAT_H, 'full': full, 'v': 2}
    for c in CAST:
        c['work'] = WORK[c['who']]; c['idles'] = {'scene': (None, 1.0 if c['who'] == 'robot' else 0.0)}; c['cue'] = CUE.get(c['who'], {})
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
    for who, fn in (('tyrell', _tyrell_acts), ('robot', _robot_acts), ('elliot', _elliot_acts)):
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
KB = Vector((-2.74, -0.95, R.TABLE_H + 0.03))     # the keyboard's middle


def _lift(arm, k):
    """How far a chair clip's pelvis must move to sit on this seat (lower than the clip's 0.52 m)."""
    return (R.SEAT_H + 0.085 * k) - _P(arm, 'Bip01 Pelvis').z


def _type(arm, tt, w, seed=0.0):
    """Both hands on the keyboard, the fingers tapping in bursts, the head down a little to the screens."""
    if w <= 0: return
    pel, fwd, right, up = _live(arm)
    burst = max(0.0, min(1.0, 0.5 + 0.6 * math.sin(tt * 0.83 + seed) + 0.3 * math.sin(tt * 2.1)))
    for side, s in (('L', -1), ('R', 1)):
        tap = max(0.0, math.sin(tt * (15.0 + 2.0 * s) + s)) ** 6 * burst
        tgt = KB + right * (0.11 * s) + Vector((0, 0, 0.012 + 0.012 * tap)) + right * 0.01 * math.sin(tt * 1.3 + s)
        _hand_to(arm, side, tgt, w, tgt + right * s * 0.35 - fwd * 0.3 - up * 0.45, palm=-up, pw=0.7)
        people.hand_shape(arm, side, 'fist', 0.35 * w)


def _robot_at(t):
    """Where Mr. Robot's head is at t (his routes, before his act is made): for Tyrell's and Elliot's eyes."""
    T = TL
    def on(route, a, b):
        at, L = people.path([Vector(p) for p in route]); p, _ = at((t - a) / (b - a) * L); return p
    for key, route in (('r_go', ROUTE_GO), ('r_behind', ROUTE_BEHIND), ('r_away', ROUTE_AWAY), ('r_back', ROUTE_BACK), ('r_home', ROUTE_HOME)):
        a, b = T[key]
        if a <= t <= b: return on(route, a, b) + Vector((0, 0, 1.6))
    if T['reach'][0] <= t <= T['r_behind'][0] or T['put'][0] <= t <= T['put'][1]: return Vector((*P_STAND, 1.5))
    if T['head'][0] <= t <= T['r_away'][0]: return Vector((*B_SPOT[0], 1.6))
    if T['r_away'][1] <= t <= T['r_back'][0]: return Vector((*R_SPOT[0], 1.6))
    return Vector((*R0[0], 1.6))


def _tyrell_at(t):
    T = TL
    if t < T['t_up'][0] or t > T['t_sit'][1]: return Vector((SEAT.x, SEAT.y, 1.12))
    if t < T['t_step'][0]: return Vector((*UP_END, 1.7))
    if t < T['t_in'][0]: return Vector((*T_SPOT[0], 1.7))
    if t < T['hug'][0]: return Vector((*T2[0], 1.7))
    if t < T['t_back'][0]: return Vector((*T_HUG[0], 1.7))
    return Vector((SEAT.x - 0.3, SEAT.y - 0.2, 1.7))


# ---------------------------------------------------------------- Tyrell
def _tyrell_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS; T = TL; who = 'tyrell'
    people.pose_at(arm, base, frames[0]); lift = {'z': _lift(arm, k)}
    screen = Vector((R.SCREENS[0].x, (R.SCREENS[0].y + R.SCREENS[1].y) / 2, R.TABLE_H + 0.38))
    def wait(f, t):
        people.shift_root(arm, (0, 0, lift['z'])); _type(arm, t, 1.0); _look(arm, screen, 0.6)
    acts['wait'] = people.custom_act(arm, base, frames, f'{who}_wait', wait, _all(arm, True))
    if not full: return
    C = _clips(arm, who, {'up': ('m_sit_stand_up_chair_01', {}), 'down': ('m_sit_down_chair_01', {}),
                          'turn90': ('m_turn_left_90', {}), 'walk': ('m_walk_slow_01', dict(inplace=True, cycles=8))})
    seat_c = _long(arm, who, 'm_sit_chair_breathe_01', 'seat'); idle = _long(arm, who, 'm_idle_nervous_01', 'idle')
    talk = _long(arm, who, 'm_gestic_talk_excited_01', 'talk', inplace=True); still = _long(arm, who, 'm_idle_neutral_02', 'still')
    walk, vs = (C['walk'][0], C['walk'][1]), C['walk'][2]
    seat, sf_ = HOME[who]
    Q = Seq()
    Q.pad('start', 0.6, src=base, f0=frames[0], at=Matrix.Identity(4))
    f0 = seat_c[1][0] + int(Q.t() * FPS); Q.pad('typing', T['t_up'][0], src=seat_c[0], f0=f0, at=_at(arm, seat_c[0], f0, seat, sf_))
    Q.clip(arm, 'up', C['up'], seat, sf_, T['t_up'][1] - T['t_up'][0])
    Q.clip(arm, 'turn', C['turn90'], UP_END, sf_, T['t_turn'][1] - Q.t())
    Q.walk_to(arm, 'step', walk, vs, [(UP_END[0], UP_END[1] - 0.12), (-2.47, -1.3), T_SPOT[0]], T['t_step'][1])
    Q.clip(arm, 'turnb', C['turn90'], T_SPOT[0], (0.0, -1.0), T['t_turnb'][1] - Q.t())
    _idle(Q, 'still', T['talk'][0], still, *T_SPOT, arm=arm)
    f0 = talk[1][0]; Q.pad('talk', T['t_in'][0], src=talk[0], f0=f0, at=_at(arm, talk[0], f0, *T_SPOT), blend=0.8)
    Q.walk_to(arm, 'in', walk, vs, [T_SPOT[0], T2[0]], T['t_in'][1])
    _idle(Q, 'forehead', T['lower'][1], still, *T2, arm=arm)
    _idle(Q, 'hug', T['hug'][1], still, *T_HUG, arm=arm)
    Q.walk_to(arm, 'back', walk, vs, ROUTE_T_BACK, T['t_back'][1])
    Q.clip(arm, 'turn2', C['turn90'], ROUTE_T_BACK[-1], (0.0, 1.0), T['t_turn2'][1] - Q.t())
    Q.clip(arm, 'down', C['down'], seat, sf_, T['t_sit'][1] - Q.t(), end=True)
    f0 = seat_c[1][0] + int(Q.t() * FPS); Q.pad('typing2', T['end'] - 1.4, src=seat_c[0], f0=f0, at=_at(arm, seat_c[0], f0, seat, sf_))
    Q.pad('end', T['end'], src=base, f0=frames[0], at=Matrix.Identity(4), blend=1.2)
    Q.log(who)
    sit_tags = ('start', 'typing', 'typing2', 'end')

    def overlay(tt, i, lt):
        tag = Q.segs[i]['tag']; f = int(round(tt * FPS)); dur = Q.segs[i]['dur']
        sw = 1.0 if tag in sit_tags else (1 - _smooth(lt / 1.2) if tag == 'up' else _smooth((lt - 0.6) / 1.4) if tag == 'down' else 0.0)
        if sw > 0: people.shift_root(arm, (0, 0, lift['z'] * sw))
        pel, fwd, right, up_ = _live(arm); rob = _robot_at(tt)
        if tag in ('typing', 'typing2', 'start', 'end'):
            freeze = _smooth((tt - T['head'][0] - 0.4) / 0.5) if tag == 'typing' else 0.0
            _type(arm, tt, (1.0 - freeze) * (_smooth((lt - 1.0) / 1.2) if tag == 'typing2' else 1.0))
            if freeze > 0:                                                  # the barrel on his head: hands up off the keys, still
                for side, s in (('L', -1), ('R', 1)):
                    h = pel + fwd * 0.28 + right * (0.2 * s) + up_ * 0.55
                    _hand_to(arm, side, h, freeze * 0.8, h - up_ * 0.4 + right * s * 0.3, palm=fwd, pw=0.6)
                _look(arm, pel + fwd * 1.0 + up_ * 0.6 + right * 0.25, freeze * 0.4)
            else: _look(arm, screen, 0.55 if tt < T['r_go'][0] or tt > T['t_sit'][1] else 0.5)
        elif tag in ('up', 'turn', 'turnb'):
            for side, s in (('L', -1), ('R', 1)):                           # hands half raised: don't shoot
                h = pel + fwd * 0.3 + right * (0.24 * s) + up_ * 0.62
                _hand_to(arm, side, h, 0.6, h - up_ * 0.4 + right * s * 0.3, palm=fwd, pw=0.5)
            _look(arm, rob, 0.6 if tag != 'up' else 0.35)
        elif tag in ('step', 'still'):
            if tag == 'still' and tt > T['click'] - 0.3:                    # the click: a flinch, eyes shut a beat
                fl = _win(tt, T['click'] - 0.2, T['click'] + 0.5, 0.15, 0.6)
                for b_, a in zip(SPINE, (0.05, 0.05, 0.04)): people.bend(arm, b_, right, a * fl)
            for side, s in (('L', -1), ('R', 1)):
                h = pel + fwd * 0.32 + right * (0.2 * s) + up_ * 0.5
                _hand_to(arm, side, h, 0.55, h - up_ * 0.4 + right * s * 0.3, palm=fwd, pw=0.5)
            _look(arm, rob, 0.75)
        elif tag == 'talk':
            _look(arm, rob if (lt % 9) < 6.5 else rob + Vector((0, 0, 0.6)), 0.7, twist=0.2)   # to him, and up (an act of God)
        elif tag == 'in':
            _look(arm, rob, 0.8)
        elif tag == 'forehead':
            # his left hand guides the gun hand to his forehead, holds it there; the head tipped into the barrel
            w = _win(lt, 0.2, T['forehead'][1] - T['forehead'][0] + 0.2, 0.8, 0.8)
            H = _P(arm, 'Bip01 Head')
            wrist = H + fwd * 0.2 + up_ * 0.0 - right * 0.03
            _hand_to(arm, 'L', wrist, w, wrist - up_ * 0.5 - right * 0.35, palm=fwd + right * 0.3, pw=0.6)
            for b_, a in zip(SPINE, (0.03, 0.03, 0.03)): people.bend(arm, b_, right, -a * w)
            _look(arm, rob, 0.9)
        elif tag == 'hug':
            # both arms round him: hands on his back, the head beside his
            w = _win(lt, 0.3, dur - 0.2, 1.0, 1.2)
            R_ = Vector((*R_SPOT[0], 1.32)); back = Vector((1.0, 0.0, 0.0))
            sideax = Vector((0, 1, 0))
            for side, s in (('L', 1), ('R', -1)):
                h = R_ + back * 0.12 + sideax * (0.1 * s) + Vector((0, 0, 0.04 * s))
                _hand_to(arm, side, h, w, h - up_ * 0.3 - back * 0.4 + right * (0.4 if side == 'R' else -0.4), palm=-back, pw=0.6)
            for b_, a in zip(SPINE, (0.04, 0.04, 0.03)): people.bend(arm, b_, right, -a * w)
            _look(arm, R_ + Vector((0, -0.3, 0.3)), 0.6 * w)
        elif tag in ('back', 'turn2', 'down'):
            _look(arm, screen, 0.4 * _smooth(lt / 1.0))
        _record(who, arm, f)
    acts['scene'] = people.sequence(arm, base, f'{who}_scene', Q.segs, overlay=overlay)
    for a, _, _ in C.values(): bpy.data.actions.remove(a)
    for a in (seat_c, idle, talk, still): bpy.data.actions.remove(a[0])


def _all(arm, fingers=False):
    return (next(b.name for b in arm.data.bones if b.parent is None),) + ALL + (FINGERS if fingers else ())


# ---------------------------------------------------------------- Mr. Robot
def _robot_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS; T = TL; who = 'robot'
    table = Vector((SEAT.x, SEAT.y, 1.1))
    def wait(f, t): _look(arm, table, 0.5)
    acts['wait'] = people.custom_act(arm, base, frames, f'{who}_wait', wait, _all(arm))
    if not full: return
    C = _clips(arm, who, {'walk': ('m_walk_neutral_01', dict(inplace=True, cycles=10))})
    idle = _long(arm, who, 'm_idle_breathe_01', 'idle'); still = _long(arm, who, 'm_idle_neutral_02', 'still')
    walk, vs = (C['walk'][0], C['walk'][1]), C['walk'][2]
    Q = Seq()
    _idle(Q, 'watch', T['r_go'][0], idle, *R0, arm=arm)
    Q.walk_to(arm, 'go', walk, vs, ROUTE_GO, T['r_go'][1])
    _idle(Q, 'reach', T['reach'][1], still, P_STAND, P_FACE, arm=arm)
    Q.walk_to(arm, 'behind', walk, vs, ROUTE_BEHIND, T['r_behind'][1])
    _idle(Q, 'head', T['r_away'][0], still, *B_SPOT, arm=arm)
    Q.walk_to(arm, 'away', walk, vs, ROUTE_AWAY, T['r_away'][1])
    _idle(Q, 'aim', T['r_back'][0], still, *R_SPOT, arm=arm)
    Q.walk_to(arm, 'back', walk, vs, ROUTE_BACK, T['r_back'][1])
    _idle(Q, 'put', T['put'][1], still, P_STAND, P_FACE, arm=arm)
    Q.walk_to(arm, 'home', walk, vs, ROUTE_HOME, T['r_home'][1])
    _idle(Q, 'watch2', T['end'] - 1.4, idle, *R0, arm=arm)
    Q.pad('end', T['end'], src=base, f0=frames[0], at=Matrix.Identity(4), blend=1.2)
    Q.log(who)
    kettle = (R.frame_at(R.POPCORN, (0.0, -1.0)) @ Vector((0.06, 0.02, 0.98, 1))).xyz
    hold = {'on': False}

    def overlay(tt, i, lt):
        tag = Q.segs[i]['tag']; f = int(round(tt * FPS)); dur = Q.segs[i]['dur']
        pel, fwd, right, up_ = _live(arm)
        holding = T['grab'] <= tt <= T['release']
        tyh = _rec('tyrell', f)
        if tag in ('watch', 'watch2', 'end'):
            _look(arm, _tyrell_at(tt) if tt < T['r_go'][0] or tt > T['r_home'][1] else _tyrell_at(tt), 0.55)
        elif tag in ('reach', 'put'):
            # down into the kettle (through the door at the back), the hand closing on the grip; up, a look at the gun
            a, b = (T['reach'] if tag == 'reach' else T['put'])
            g = T['grab'] if tag == 'reach' else T['release']
            w = _win(tt, a + 0.4, g + 0.7, 0.9, 0.9)
            tgt = kettle + Vector((0, 0, 0.02))
            _hand_to(arm, 'R', tgt, w, tgt + right * 0.4 + up_ * 0.1 - fwd * 0.3, palm=-up_ + fwd * 0.3, pw=0.5)
            for b_, ang in zip(SPINE, (0.1, 0.08, 0.06)): people.bend(arm, b_, right, -ang * w)
            if tag == 'reach' and tt > g + 0.6:                             # a look at the gun before his chest
                w2 = _win(tt, g + 0.7, b + 0.3, 0.6, 0.6); h = pel + fwd * 0.32 + up_ * 0.62 + right * 0.08
                _hand_to(arm, 'R', h, w2, h - up_ * 0.4 + right * 0.4, palm=-right, pw=0.6)
                _look(arm, h, 0.7 * w2)
            else: _look(arm, kettle, 0.7)
        elif tag == 'behind' or tag == 'go':
            _look(arm, _tyrell_at(tt), 0.5 if tag == 'behind' else 0.3)
        elif tag == 'head':
            # the barrel at the back of his head (follows the head as he rises), the arm bent
            w = _win(tt, T['head'][0] + 0.3, T['r_away'][0] + 0.4, 0.9, 0.5)
            people.point_at(arm, 'R', tyh, w, reach=max(0.25, min(0.5, (tyh - _P(arm, 'Bip01 R UpperArm')).length - 0.18)), shape='gun', drop=0.18, out=0.15)
            _look(arm, tyh, 0.8)
        elif tag == 'away':
            w = 0.45
            people.point_at(arm, 'R', tyh, w, reach=0.4, shape='gun', drop=0.25, out=0.2)
            _look(arm, tyh, 0.6)
        elif tag == 'aim':
            # arm's length at his head; the click (a squeeze, the hand jerks a hair); a look at the gun; aimed again
            # through the talk; the barrel set to his forehead; lowered; still through the embrace
            if tt < T['look_gun'][0]:
                w = _smooth((tt - T['aim']) / 0.8); jerk = _win(tt, T['click'], T['click'] + 0.25, 0.05, 0.25)
                people.point_at(arm, 'R', tyh + Vector((0, 0, 0.03 * jerk)), w, reach=0.56, shape='gun', drop=0.12, out=0.1)
                people.hand_shape(arm, 'R', 'fist', 0.25 * jerk)
                _look(arm, tyh, 0.85)
            elif tt < T['talk'][0]:
                w = _win(tt, T['look_gun'][0], T['look_gun'][1], 0.5, 0.6)
                people.point_at(arm, 'R', tyh, 1.0 - 0.6 * w, reach=0.56, shape='gun', drop=0.12, out=0.1)
                h = _P(arm, 'Bip01 R Hand'); _look(arm, h, 0.8 * w); _look(arm, tyh, 0.8 * (1 - w))
            elif tt < T['forehead'][0] - 0.6:
                sway = 0.04 * math.sin(tt * 0.7)
                people.point_at(arm, 'R', tyh + Vector((0, 0, -0.15 + sway)), 0.92, reach=0.5, shape='gun', drop=0.16, out=0.12)
                _look(arm, tyh, 0.8)
            elif tt < T['lower'][0]:
                fh = tyh + Vector((0.09, 0, 0.06)); w = _smooth((tt - (T['forehead'][0] - 0.6)) / 0.9)
                people.point_at(arm, 'R', tyh, 1.0, reach=max(0.25, (fh - _P(arm, 'Bip01 R UpperArm')).length), shape='gun', drop=0.16, out=0.12)
                _look(arm, tyh, 0.9)
            else:
                w = 1.0 - _smooth((tt - T['lower'][0]) / 1.6)
                people.point_at(arm, 'R', tyh + Vector((0, 0, -0.4)), w, reach=0.5, shape='gun', drop=0.16, out=0.12)
                _look(arm, tyh, 0.7)
        elif tag in ('back', 'home'):
            _look(arm, kettle if tag == 'back' else _tyrell_at(tt), 0.3)
        if holding: people.hand_shape(arm, 'R', 'gun', 1.0 if tag in ('head', 'away', 'turn', 'aim') else 0.85)
        _record(who, arm, f)
    acts['scene'] = people.sequence(arm, base, f'{who}_scene', Q.segs, overlay=overlay)
    for a, _, _ in C.values(): bpy.data.actions.remove(a)
    for a in (idle, still): bpy.data.actions.remove(a[0])


# ---------------------------------------------------------------- Elliot
def _elliot_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS; T = TL; who = 'elliot'
    ty = Vector((SEAT.x, SEAT.y, 1.12))
    def wait(f, t): _look(arm, ty, 0.6)
    acts['wait'] = people.custom_act(arm, base, frames, f'{who}_wait', wait, _all(arm))
    if not full: return
    C = _clips(arm, who, {'walk': ('m_walk_slow_01', dict(inplace=True, cycles=6))})
    talk = _long(arm, who, 'm_gestic_talk_neutral_01', 'talk', inplace=True); idle = _long(arm, who, 'm_idle_nervous_01', 'idle')
    walk, vs = (C['walk'][0], C['walk'][1]), C['walk'][2]
    Q = Seq()
    f0 = talk[1][0]; Q.pad('talk', T['e_back'][0], src=talk[0], f0=f0, at=_at(arm, talk[0], f0, *E0))
    Q.walk_to(arm, 'back', walk, vs, [E0[0], (-1.45, 0.16), E1[0]], T['e_back'][1])
    _idle(Q, 'watch', T['e_home'][0], idle, *E1, arm=arm)
    Q.walk_to(arm, 'home', walk, vs, [E1[0], (-1.45, 0.16), E0[0]], T['e_home'][1])
    f0 = talk[1][0] + int(Q.t() * FPS); Q.pad('talk2', T['end'] - 1.4, src=talk[0], f0=f0, at=_at(arm, talk[0], f0, *E0))
    Q.pad('end', T['end'], src=base, f0=frames[0], at=Matrix.Identity(4), blend=1.2)
    Q.log(who)

    def overlay(tt, i, lt):
        tag = Q.segs[i]['tag']; f = int(round(tt * FPS))
        pel, fwd, right, up_ = _live(arm)
        if tag in ('talk', 'talk2', 'end'):
            _look(arm, _rec('tyrell', f), 0.6)
        elif tag in ('watch', 'back', 'home'):
            # he watches Mr. Robot (himself) do it: on him, and on Tyrell when the gun is on Tyrell
            r = _rec('robot', f); t_ = _rec('tyrell', f)
            at_ = t_ if T['click'] - 1.0 < tt < T['hug'][1] and (int(tt / 4) % 2 == 0) else r
            _look(arm, at_, 0.7, twist=0.2)
            if tag == 'watch':                                              # hands in the hoodie's pockets
                for side, s in (('L', -1), ('R', 1)):
                    h = pel + fwd * 0.12 + right * (0.1 * s) - up_ * 0.02
                    _hand_to(arm, side, h, 0.7 * _win(lt, 0.0, Q.segs[i]['dur'], 1.0, 1.0), h - up_ * 0.3 + right * s * 0.3 - fwd * 0.2, palm=-right * s, pw=0.5)
        _record(who, arm, f)
    acts['scene'] = people.sequence(arm, base, f'{who}_scene', Q.segs, overlay=overlay)
    for a, _, _ in C.values(): bpy.data.actions.remove(a)
    for a in (talk, idle): bpy.data.actions.remove(a[0])


# ---------------------------------------------------------------- the gun
def _grip(arm, f):
    """Where the pistol sits in Mr. Robot's right hand at frame f (world): its grip in the palm, the barrel along the
    hand toward the index's knuckle, the slide on the thumb's side."""
    sc = bpy.context.scene; sc.frame_set(f); bpy.context.view_layer.update()
    P = lambda b: people._world(arm, arm.pose.bones[f'Bip01 R {b}']).translation.copy()
    H = P('Hand'); idx, pinky = P('Finger1'), P('Finger4')
    fwd = ((idx + pinky) / 2 - H).normalized()
    upv = (idx - pinky); upv = (upv - fwd * upv.dot(fwd)).normalized()
    side = fwd.cross(upv)
    palm = H + fwd * 0.045 + people._palm(arm, 'R') * 0.025
    return Matrix((list(fwd) + [0], list(side) + [0], list(upv) + [0], [0, 0, 0, 1])).transposed(), palm


def _place_gun(seated):
    """Set the pistol where Mr. Robot's hand closes on it (in the kettle), held as it will be: the web keeps that
    offset while he carries it."""
    if not RIG['gun'] or not GUN: return
    robot = next(((c, arm) for c, arm, mesh in seated if c['who'] == 'robot'), None)
    if not robot: return
    c, arm = robot
    if 'scene' not in c['acts']: return
    act = c['acts']['scene']
    people.pose_at(arm, act, int(act.frame_range[0]))
    f = int(act.frame_range[0]) + int(round(GUN['grab'] * people.FPS))
    Rm, palm = _grip(arm, f)
    ms = RIG['gun']
    lo = Vector((1e9,) * 3); hi = -lo; verts = []
    for o in ms:
        for v in o.data.vertices: p = o.matrix_world @ v.co; verts.append(p); lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
    mid = (lo + hi) / 2
    low = [p for p in verts if p.z < lo.z + (hi.z - lo.z) * 0.35]
    gc = sum(low, Vector()) / max(len(low), 1)                                  # the grip: the low part, at the rear
    muzzle = Vector((1.0 if gc.x < mid.x else -1.0, 0, 0))                     # the barrel runs away from the grip
    local = Matrix((list(muzzle) + [0], list(Vector((0, 0, 1)).cross(muzzle)) + [0], [0, 0, 1, 0], [0, 0, 0, 1])).transposed()
    G = Matrix.Translation(palm) @ Rm @ local.inverted() @ Matrix.Translation(-gc)
    for o in ms:
        o.matrix_world = G @ o.matrix_world
    RIG['gun_rest'] = [o.matrix_world.copy() for o in ms]
    cine.log('gun placed at', tuple(round(v, 3) for v in palm))


def _pose_gun(t):
    """In a still preview, put the pistol in the hand if he holds it at t."""
    for o, rest in zip(RIG['gun'], RIG.get('gun_rest', [])): o.matrix_world = rest
    if not GUN or not (GUN['grab'] <= t <= GUN['release']): return
    robot = next(((c, arm) for c, arm, mesh in SEATED if c['who'] == 'robot'), None)
    if not robot: return
    c, arm = robot
    if 'scene' not in c['acts']: return
    act = c['acts']['scene']; f0 = int(act.frame_range[0])
    Rg, pg = _grip(arm, f0 + int(round(GUN['grab'] * people.FPS)))
    Rt, pt = _grip(arm, f0 + int(round(t * people.FPS)))
    D = Matrix.Translation(pt) @ Rt @ Rg.inverted() @ Matrix.Translation(-pg)
    for o, rest in zip(RIG['gun'], RIG.get('gun_rest', [])): o.matrix_world = D @ rest
    bpy.context.scene.frame_set(f0 + int(round(t * people.FPS)))


# ---------------------------------------------------------------- bake and export
def bake(sc, objs, phantoms, seated, args):
    """The room's light baked into atlases (the people and the gun out of it); then room.glb, the people and room.json."""
    os.makedirs(WEB, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    for c, arm, mesh in seated: mesh.hide_render = True
    export, atlases = stages.bake(objs, R.RH, OUT, int(args.get('size', 2048)), int(args.get('samples', 320)))
    for c, arm, mesh in seated: mesh.hide_render = False
    cine.export_glb(export, os.path.join(WEB, 'room.glb'))
    meta = stages.room_meta(R.RH, atlases); meta.update(_capture_meta()); meta['live'] = _live_meta()
    meta['people'] = _export_people(seated)
    stages.write_meta(WEB, meta)


def _export_people(seated):
    out = os.path.join(WEB, 'people'); os.makedirs(out, exist_ok=True); metas = []
    for c, arm, mesh in seated:
        people.export_person(arm, mesh, c['acts'], os.path.join(out, f"{c['who']}.glb"), roam=c.get('roam', ()))
        metas.append(person_meta(c))
    return metas


def _capture_meta():
    """How to light the people as the bake lit the room (three.js: y up, z = -Blender y): every light as an emitter;
    captured at the table, mid-room and on the right."""
    em = []
    for l in RIG['lights']:
        if l.type != 'LIGHT': continue
        r = 0.25 if l.data.type in ('SPOT', 'POINT') else 0.6; e = l.data.energy
        em.append({'x': round(l.location.x, 3), 'y': round(l.location.z, 3), 'z': round(-l.location.y, 3), 'r': r,
                   'L': round(e / (4 * math.pi * r ** 2) / 60 * 6.0, 2), 'color': [round(v, 3) for v in l.data.color]})
    at = [[round(v, 3) for v in (p.x, p.z, -p.y)] for p in (Vector((-2.3, -0.9, 1.2)), Vector((-0.6, -0.4, 1.3)), Vector((1.6, 0.0, 1.4)))]
    return {'capture': {'ceiling': [0.22, 0.22, 0.26], 'walls': [0.5, 0.36, 0.52], 'emitters': em, 'windows': [], 'at': at}}


def _live_meta():
    return {'held': [dict(GUN)]} if GUN else {}


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
