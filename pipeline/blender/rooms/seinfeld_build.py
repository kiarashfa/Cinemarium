# Seinfeld: assemble Jerry's apartment, stand Jerry mid-room and George behind the counter, perch Elaine on the couch's
# arm, put Kramer in the open doorway; then preview, bake and export.
import math, os
import bpy
from mathutils import Vector, Matrix
import cine, people, stages
from stages import camera
import rooms.seinfeld as R

ROOM = 'seinfeld'
OUT = os.path.join(cine.OUT, ROOM)
WEB = os.path.join(cine.ROOT, 'public', 'rooms', ROOM)
PEOPLE_TEX = os.path.join(cine.OUT, 'people')
ARGS = {}
SEATED = []


def build(args):
    ARGS.clear(); ARGS.update(args)
    sc = cine.reset(int(args.get('samples', 256)))
    M = R.mats()
    static, phantom, crowd = cine.coll('static'), cine.coll('phantom'), cine.coll('people')
    R.shell(M, static, static, phantom)
    R.doors(M, static); R.windows(M, static); R.desk(M, static)
    lamp = R.living(M, static)
    R.etagere(M, static); R.bike(M, static)
    pendant = R.hall_things(M, static)
    under = R.kitchen(M, static)
    sconces = R.pictures(M, static)
    R.lights(sconces, lamp, pendant, under)
    _tidy()
    seated = [] if args.get('nocast') else cast(crowd, args)
    SEATED[:] = seated
    objs = [o for o in static.objects if o.type == 'MESH']
    cine.bake_ready(objs)
    R.section(objs, M)
    for o in objs:   # procedural meshes get world-scale UVs; imported props and the 0..1 faces keep their own
        if not o.data.uv_layers: cine.world_uv(o, 1.0)
        elif 'UVMap' not in o.data.uv_layers: o.data.uv_layers[0].name = 'UVMap'
    objs = _merge(objs)
    for o in phantom.objects: cine.bake_ready([o]); cine.world_uv(o, 1.0); cine.phantom(o)
    cine.check_module(objs)
    # the web camera's views at room scale (the case view and the closer one), the broadcast view, and looks at the cast
    cams = {'case': camera('cam_case', (11.14, -18.16, 7.95), (-2.30, -1.49, 0.63), 32),
            'close': camera('cam_close', (5.0, -5.6, 3.4), (0.2, 0.9, 0.9), 30),
            'film': camera('cam_film', (0.6, -3.5, 1.45), (0.9, 1.6, 1.15), 54),
            'kitchen': camera('cam_kitchen', (0.2, -2.4, 1.5), (3.6, 1.2, 1.1), 46),
            'alcove': camera('cam_alcove', (-1.0, -1.6, 1.5), (-3.6, 3.2, 1.2), 50),
            'hall': camera('cam_hall', (1.9, -0.6, 1.6), (0.1, 2.9, 1.3), 40),
            'top': camera('cam_top', (0.0, -0.4, 14.0), (0.0, 0.0, 0.0), 34),
            'jerry': camera('cam_jerry', (2.6, -1.4, 1.65), (1.02, 0.32, 1.45), 34),
            'george': camera('cam_george', (2.2, -1.5, 1.5), (3.4, 0.36, 1.25), 34),
            'kramer': camera('cam_kramer', (2.4, 0.2, 1.75), (1.62, 2.0, 1.55), 38),
            'elaine': camera('cam_elaine', (0.9, -1.6, 1.3), (-0.11, -0.33, 0.95), 36)}
    return sc, M, objs, list(phantom.objects), seated, cams


def _tidy():
    """Imported props come under helper empties: keep their children where they are and drop the empties."""
    bpy.context.view_layer.update()
    for o in [o for o in bpy.data.objects if o.type == 'EMPTY']:
        for ch in o.children:
            mw = ch.matrix_world.copy(); ch.parent = None; ch.matrix_world = mw
        bpy.data.objects.remove(o, do_unlink=True)


KEEP = ('back_', 'left_', 'kerb', 'floor', 'subfloor')   # their names carry rules (section faces, the cut tops)


def _merge(objs):
    """Join the many small pieces of furniture and trim, one object per atlas and material: fewer meshes to draw."""
    groups = {}
    for o in objs:
        if o.get('role') or not o.get('lm') or len(o.material_slots) != 1 or o.name.startswith(KEEP): continue
        groups.setdefault((o['lm'], o.material_slots[0].material.name), []).append(o)
    out = [o for o in objs if not any(o in g for g in groups.values())]
    for (lm, mat), g in groups.items():
        if len(g) == 1: out += g; continue
        bpy.ops.object.select_all(action='DESELECT')
        for o in g: o.select_set(True)
        bpy.context.view_layer.objects.active = g[0]
        bpy.ops.object.join()
        j = bpy.context.view_layer.objects.active; j.name = f'{lm}_{mat}'; j['lm'] = lm
        out.append(j)
    cine.log(f'merged {len(objs)} meshes into {len(out)}')
    return out


def preview(sc, cams, which, samples, path, size=(1440, 900)):
    """A Cycles render from one camera; pose=who:act:frame,... poses people first."""
    for spec in filter(None, str(ARGS.get('pose', '')).split(',')):
        who, act, f = spec.split(':')
        for c, arm, mesh in SEATED:
            if c['who'] == who and act in c['acts']: people.pose_at(arm, c['acts'][act], int(c['acts'][act].frame_range[0]) + int(f))
    stages.render(sc, cams[which], samples, path, size, float(ARGS.get('exposure', 0.0)))


# ---------------------------------------------------------------- the cast
# Who is where and what they do, as in "The Wink" (season seven): Kramer has just come in and stands in the open door,
# talking with his hands; Jerry stands mid-room, hands on hips now and then; George leans on the counter from the
# kitchen side, his hand going up to his winking eye; Elaine perches on the couch's arm. They play it out front, as a
# sitcom does. Each has one looping act (`work`: name, min, max seconds) and idles (clip, or None for an authored act).
def _tex(who, prefix, *names):
    return {f'{prefix}_{n}.tga': f'{who}/{prefix}_{n}.png' for n in names}


def _s(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0); return t * t * (3 - 2 * t)


# the hair's thickness over the scalp (people.hair_mass): d is the scalp point less the skull's middle, the face toward -y
KRAMER_HAIR = lambda p, d: 0.012 + 0.105 * _s(0.0, 0.08, d.z) * (1 - 0.55 * _s(0.04, 0.075, abs(d.x))) * (1 - 0.4 * _s(0.0, 0.08, d.y))   # up, not out
ELAINE_HAIR = lambda p, d: 0.018 + 0.012 * _s(0.0, 0.08, d.z) + 0.024 * _s(0.035, 0.07, abs(d.x)) * (1 - _s(0.06, 0.1, d.z))   # full at the sides
JERRY_HAIR = lambda p, d: 0.005 + 0.024 * _s(0.0, 0.09, d.z) * (1 - 0.5 * _s(0.02, 0.09, d.y))   # the volume on top, at the front
HAIR = {'kramer': KRAMER_HAIR, 'elaine': ELAINE_HAIR, 'jerry': JERRY_HAIR}   # by name, so the cast's cache key stays put


CAST = [
    dict(who='jerry', avatar='Male_Adult_08', shape='lean', shape_k=1.3, scale=1.0, stand='jerry', base='m_idle_breathe_01', work=('listen', 8, 18), listen='m_gestic_listen_neutral_01',
         hair=((1.06, 1.05, 1.12), 0.012), mass=dict(depth='jerry', n=220, size=0.02, squash=(1.3, 1.3, 0.42), colours=((0.028, 0.019, 0.014), (0.045, 0.03, 0.022)), front=0.055),
         idles={'talk': ('m_gestic_talk_neutral_02', 1.3), 'hips': (None, 1.2), 'shrug': ('m_gestic_shrug_01', 0.8), 'look': ('m_idle_look_around_01', 0.4)},
         tex=_tex('jerry', 'm014', 'head_color', 'opacity_color', 'body_color')),
    dict(who='george', avatar='Male_Adult_13', shape='broad', scale=0.92, stand='george', base='m_idle_neutral_01', work=('lean', 8, 18),
         idles={'talk': ('m_gestic_talk_nervous_01', 1.2), 'wink': (None, 1.3), 'shrug': ('m_gestic_shrug_02', 0.8), 'deny': ('m_gestic_listen_deny_01', 0.5)},
         tex=_tex('george', 'm010', 'head_color', 'body_color', 'body_normal')),
    dict(who='kramer', avatar='Male_Adult_06', shape='lean', shape_k=2.0, scale=1.055, stand='kramer', base='m_idle_breathe_02', work=('talk', 7, 16), talk='m_gestic_talk_excited_01',
         hair=((1.1, 1.08, 1.25), 0.02), mass=dict(depth='kramer', n=520, size=0.016, squash=(0.8, 0.8, 1.5), colours=((0.034, 0.021, 0.014), (0.06, 0.04, 0.027)), front=0.06),
         idles={'burst': (None, 1.3), 'frame': (None, 1.0), 'listen': ('m_gestic_listen_excited_01', 0.9), 'shake': ('m_idle_shake_arms_01', 0.7), 'laugh': ('m_gestic_laugh_loud', 0.5)},
         tex=_tex('kramer', 'm011', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
    dict(who='elaine', avatar='Business_Female_03', scale=0.93, seat='elaine', base='f_sit_chair_breathe_01', work=('sit', 8, 18),
         hair=((1.08, 1.06, 1.08), 0.01), mass=dict(depth='elaine', n=420, size=0.015, fall=1.4, colours=((0.022, 0.014, 0.01), (0.04, 0.026, 0.018)), front=0.045),
         idles={'talk': ('f_gestic_talk_excited_01', 1.4), 'shrug': ('f_sit_chair_gestic_shrug_01', 0.8), 'hair': ('f_sit_chair_idle_touch_hair', 0.7),
                'look': ('f_sit_chair_idle_look_around', 0.5), 'think': ('f_sit_chair_gestic_thoughtful', 0.5)},
         tex=_tex('elaine', 'f016', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
]
SPINE = ('Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2')
ARMS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('UpperArm', 'Forearm', 'Hand'))
HEAD = ('Bip01 Neck', 'Bip01 Head')
KRAMER_AT = Vector((R.STAND['kramer'][0][0], R.STAND['kramer'][0][1], 1.75))


def _smooth(x):
    x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)


def _look(arm, at, w):
    """Turn the head (and a little the neck) toward a point, by the fraction w."""
    H = people._world(arm, arm.pose.bones['Bip01 Head']).translation
    pel, fwd, right, up = people.body_frame(arm)
    d = (Vector(at) - H).normalized()
    yaw = math.atan2(d.dot(-right), d.dot(fwd)); pitch = math.asin(max(-1, min(1, d.z)))
    people.bend(arm, 'Bip01 Neck', up, yaw * 0.35 * w); people.bend(arm, 'Bip01 Head', up, yaw * 0.65 * w)
    people.bend(arm, 'Bip01 Neck', right, pitch * 0.3 * w); people.bend(arm, 'Bip01 Head', right, pitch * 0.7 * w)


def _seat(c, arm, base, frames):
    """Slide a seated person so the clip's pelvis sits over the seat; report how the heights agree."""
    x, y, facing = R.SEATS[c['seat']]
    people.pose_at(arm, base, frames[0])
    pel = people._world(arm, arm.pose.bones['Bip01 Pelvis']).translation
    want = Vector((x, y, 0)) + Matrix.Rotation(facing, 3, 'Z') @ Vector((0, -0.01, 0))
    arm.location.x += want.x - pel.x; arm.location.y += want.y - pel.y
    bpy.context.view_layer.update()
    cine.log(f"seat {c['who']}: pelvis {pel.z:.3f} m high (arm top {R.ARM_H:.3f})")


def _lean(arm, T):
    """George at the counter from the kitchen side: both hands flat on its top, leaning in a little, his head turning
    between Jerry and Kramer. Whole cycles over the act, so it loops without a seam."""
    k = max(1, round(T / 8.0)); jerry = Vector((*R.STAND['jerry'][0], 1.62))
    def step(f, t):
        pel, fwd, right, up = people.body_frame(arm)
        for b, a in zip(SPINE, (0.05, 0.07, 0.05)): people.bend(arm, b, right, -a)
        pel, fwd, right, up = people.body_frame(arm)
        for s, sd in (('L', -1), ('R', 1)):
            tgt = pel + fwd * 0.5 + right * sd * 0.24; tgt.z = R.COUNTER_H + 0.045
            people.ik2(arm, s, tgt, tgt + right * sd * 0.4 - fwd * 0.2 + up * 0.1)
            people.palm_to(arm, s, Vector((0, 0, -1)), 0.9)
        u = 0.5 + 0.5 * math.sin(2 * math.pi * k * t / T)
        _look(arm, jerry.lerp(KRAMER_AT, _smooth((u - 0.3) * 2.5)), 0.8)
    return step


def _wink(arm, T):
    """The wink he cannot stop: his right hand goes up to his right eye and holds it, the left stays on the counter."""
    def step(f, t):
        e = people.envelope(t, T, 1.0, 1.4)
        pel, fwd, right, up = people.body_frame(arm)
        for b, a in zip(SPINE, (0.05, 0.07, 0.05)): people.bend(arm, b, right, -a * (1 - 0.5 * e))
        pel, fwd, right, up = people.body_frame(arm)
        tgt = pel + fwd * 0.5 - right * 0.24; tgt.z = R.COUNTER_H + 0.045
        people.ik2(arm, 'L', tgt, tgt - right * 0.4 - fwd * 0.2 + up * 0.1); people.palm_to(arm, 'L', Vector((0, 0, -1)), 0.9)
        eye = people._world(arm, arm.pose.bones['Bip01 REye']).translation.copy()
        rest = pel + fwd * 0.5 + right * 0.24; rest.z = R.COUNTER_H + 0.045
        at_eye = eye + fwd * 0.06 - up * 0.075 + right * 0.035
        tgt = rest.lerp(at_eye, e)
        people.ik2(arm, 'R', tgt, tgt + right * 0.35 - up * 0.3)
        people.palm_to(arm, 'R', (-fwd).lerp(Vector((0, 0, -1)), 1 - e), 1.0)
        people.bend(arm, 'Bip01 Head', right, -0.08 * e)
    return step


def _hips(arm, T):
    """Jerry with his hands on his hips, his head turning to Kramer at the door."""
    def step(f, t):
        e = people.envelope(t, T, 1.2, 1.4)
        if e <= 0: return
        pel, fwd, right, up = people.body_frame(arm)
        for s, sd in (('L', -1), ('R', 1)):
            H = people._world(arm, arm.pose.bones[f'Bip01 {s} Hand']).translation.copy()
            tgt = H.lerp(pel + up * 0.13 + right * sd * 0.19 - fwd * 0.01, e)
            people.ik2(arm, s, tgt, tgt + right * sd * 0.45 - fwd * 0.15 + up * 0.15)
            people.palm_to(arm, s, -right * sd, e)
        _look(arm, KRAMER_AT, 0.85 * _smooth((t - 1.0) / 1.0) * _smooth((T - 1.5 - t) / 1.0))
    return step


def _burst(arm, T):
    """Kramer's entrance: a jolt back, both arms flung up and out, palms open, a shake of the head, then he settles
    forward into the room."""
    def step(f, t):
        jolt = _smooth(t / 0.3) * (1 - _smooth((t - 1.7) / 1.2))
        settle = _smooth((t - 1.8) / 0.8) * (1 - _smooth((t - T + 1.4) / 1.2))
        pel, fwd, right, up = people.body_frame(arm)
        for b, a in zip(SPINE, (0.06, 0.09, 0.07)): people.bend(arm, b, right, a * jolt - 0.6 * a * settle)
        pel, fwd, right, up = people.body_frame(arm)
        wob = 0.03 * math.sin(2 * math.pi * 3.2 * t) * jolt
        for s, sd in (('L', -1), ('R', 1)):
            H = people._world(arm, arm.pose.bones[f'Bip01 {s} Hand']).translation.copy()
            sh = people._world(arm, arm.pose.bones[f'Bip01 {s} UpperArm']).translation.copy()
            flung = sh + right * sd * 0.42 + up * (0.12 + wob * sd) + fwd * 0.1
            tgt = H.lerp(flung, jolt)
            people.ik2(arm, s, tgt, tgt - up * 0.4 + right * sd * 0.2 - fwd * 0.1)
            people.palm_to(arm, s, fwd, jolt)
        people.bend(arm, 'Bip01 Head', right, 0.12 * jolt); people.bend(arm, 'Bip01 Head', up, 0.15 * math.sin(2 * math.pi * 2.5 * t) * jolt)
    return step


def _frame(arm, T):
    """Kramer leaning on the doorframe: his left hand up on the latch jamb, a tilt toward it, his head cocked."""
    jamb = Vector((R.DOOR[1] - 0.03, R.YB - 0.04, 1.6))
    def step(f, t):
        e = people.envelope(t, T, 1.4, 1.6)
        if e <= 0: return
        pel, fwd, right, up = people.body_frame(arm)
        people.bend(arm, 'Bip01 Spine1', fwd, 0.07 * e); people.bend(arm, 'Bip01 Spine2', fwd, 0.05 * e)
        H = people._world(arm, arm.pose.bones['Bip01 L Hand']).translation.copy()
        tgt = H.lerp(jamb, e)
        people.ik2(arm, 'L', tgt, tgt - right * 0.3 - up * 0.35 - fwd * 0.1)
        people.palm_to(arm, 'L', (jamb - people._world(arm, arm.pose.bones['Bip01 L UpperArm']).translation).normalized(), e)
        people.bend(arm, 'Bip01 Head', fwd, -0.1 * e)
    return step


def cast(col, args):
    """Load, dress, shape and place the four, and bake their acts (cached: retargets and IK take minutes)."""
    full = bool(args.get('full'))
    spec = {'cast': CAST, 'seats': R.SEATS, 'stand': R.STAND, 'counter': R.COUNTER_H, 'arm': R.ARM_H, 'door': R.DOOR, 'full': full, 'v': 3}
    seated = stages.cast_cache(OUT, CAST, spec, lambda: _make_cast(col, full), col)
    for c, arm, mesh in seated: people.pose_at(arm, c['acts'][c['work'][0]], 30)
    return seated


def _make_cast(col, full):
    seated = []
    for c in CAST:
        arm, mesh = people.load_avatar(c['avatar'], textures={k: os.path.join(PEOPLE_TEX, v) for k, v in c['tex'].items()}, collection=col)
        mesh['person'] = c['who']; arm['person'] = c['who']
        if c.get('shape'): people.reshape(arm, mesh, c['shape'], c.get('shape_k', 1.0))
        if c.get('hair'): people.hair_cards(arm, mesh, *c['hair'])
        if c.get('mass'): people.hair_mass(arm, mesh, **{**c['mass'], 'depth': HAIR[c['mass']['depth']]})
        if c.get('scale', 1.0) != 1.0:
            arm.scale = arm.scale * c['scale']; arm.location = (arm.location.x, arm.location.y, arm.location.z * c['scale'])
        bpy.context.view_layer.update()
        if c.get('seat'):
            x, y, facing = R.SEATS[c['seat']]; want = Matrix.Rotation(facing, 3, 'Z') @ Vector((0, -1, 0))   # a seat's front is its local -y
        else:
            (x, y), (lx, ly) = R.STAND[c['stand']]; want = Vector((lx - x, ly - y, 0))
        people.face(arm, want); arm.location = (x, y, arm.location.z)
        bpy.context.view_layer.update()
        arm['fwd'] = list(want.normalized())
        base, frames, _ = people.retarget(arm, c['base'], cycles=2, action_name=f"{c['who']}_base")
        if c.get('seat'): _seat(c, arm, base, frames)
        T = (frames[1] - frames[0]) / people.FPS
        acts = {}; who = c['who']
        if who == 'jerry':
            acts['listen'] = people.anchor(arm, people.retarget(arm, c['listen'], action_name='jerry_listen')[0], base)
            if full:
                n = int(9 * people.FPS); acts['hips'] = people.custom_act(arm, base, (frames[0], frames[0] + n), 'jerry_hips', _hips(arm, n / people.FPS), ARMS + HEAD)
        elif who == 'george':
            acts['lean'] = people.custom_act(arm, base, frames, 'george_lean', _lean(arm, T), SPINE + ARMS + HEAD)
            if full:
                n = int(7 * people.FPS); acts['wink'] = people.custom_act(arm, base, (frames[0], frames[0] + n), 'george_wink', _wink(arm, n / people.FPS), SPINE + ARMS + ('Bip01 Head',))
        elif who == 'kramer':
            acts['talk'] = people.anchor(arm, people.retarget(arm, c['talk'], action_name='kramer_talk')[0], base)
            if full:
                n = int(5.5 * people.FPS); acts['burst'] = people.custom_act(arm, base, (frames[0], frames[0] + n), 'kramer_burst', _burst(arm, n / people.FPS), SPINE + ARMS + ('Bip01 Head',))
                n = int(9 * people.FPS); acts['frame'] = people.custom_act(arm, base, (frames[0], frames[0] + n), 'kramer_frame', _frame(arm, n / people.FPS), SPINE + ARMS + ('Bip01 Head',))
        else:
            acts['sit'] = base
            if full:
                talk, tf, _ = people.retarget(arm, c['idles']['talk'][0], action_name='elaine_talk_src')
                acts['talk'] = people.layer(base, talk, name='elaine_talk'); bpy.data.actions.remove(talk)
            base = None
        if full:
            for k, (clip, _w) in c['idles'].items():   # each starts where the looping act starts
                if clip and k not in acts: acts[k] = people.anchor(arm, people.retarget(arm, clip, action_name=f"{who}_{k}")[0], acts[c['work'][0]])
        if base and base not in acts.values(): bpy.data.actions.remove(base)
        for a in acts.values(): people.freeze(a)
        c['acts'] = acts
        people.pose_at(arm, acts[c['work'][0]], 30)
        seated.append((c, arm, mesh))
    return seated


# ---------------------------------------------------------------- bake and export
def bake(sc, objs, phantoms, seated, args):
    """The room's light baked into atlases; then room.glb, the people and room.json."""
    os.makedirs(WEB, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    export, atlases = stages.bake(objs, R.H, OUT, int(args.get('size', 2048)), int(args.get('samples', 320)))
    cine.export_glb(export, os.path.join(WEB, 'room.glb'))
    meta = stages.room_meta(R.H, atlases); meta.update(_capture_meta())
    meta['people'] = stages.export_people(seated, WEB, person_meta)
    stages.write_meta(WEB, meta)


def _capture_meta():
    """How to light the people as the bake lit the room (three.js coordinates: y up, z = -Blender y): the bulbs as small
    bright spheres, the windows (the alcove's, the bathroom's, the daylight on the cut-away's side) as glowing panes."""
    bulbs = []
    for l in bpy.data.objects:
        if l.type != 'LIGHT' or l.data.type != 'POINT': continue
        r = 0.03
        bulbs.append({'x': round(l.location.x, 3), 'y': round(l.location.z, 3), 'z': round(-l.location.y, 3), 'r': r,
                      'L': round(l.data.energy / (4 * math.pi * r ** 2) / 60, 2), 'color': [round(c, 3) for c in l.data.color]})
    windows = [{'x': c, 'y': sum(R.WIN_Z) / 2, 'z': -(R.BACK - 0.02), 'w': 0.55, 'h': R.WIN_Z[1] - R.WIN_Z[0], 'L': 4.0, 'color': list(R.SUN), 'ry': 0.0} for c in R.WINDOWS]
    # the daylight from the side the cut-away removes, strong enough that faces turned to the case read in the light
    windows += [{'x': x, 'y': 1.5, 'z': R.D / 2 - 0.2, 'w': 1.6, 'h': 1.8, 'L': 4.5, 'color': [1.0, 0.94, 0.86], 'ry': math.pi} for x in (-2.6, 0.4, 3.2)]
    return {'capture': {'ceiling': [0.78, 0.76, 0.71], 'walls': [0.72, 0.7, 0.65], 'emitters': bulbs, 'windows': windows,
                        'at': [[-0.6, 1.25, 0.3], [2.8, 1.3, -0.6]]}}


def person_meta(c):
    """The acts in a person's file, the looping one first, with how long it lasts and how often each idle comes up."""
    work, lo, hi = c['work']
    acts = [{'name': work, 'loop': True, 'min': lo, 'max': hi}]
    acts += [{'name': k, 'w': w} for k, (clip, w) in c['idles'].items() if k in c['acts']]
    return {'who': c['who'], 'file': f"{c['who']}.glb", 'acts': acts}


def people_stage(sc, cams, seated, args):
    """Re-export only the people (their glTF files and their part of room.json); the baked room stays as it is.
    Then a look at each of them in the room (Cycles)."""
    stages.update_meta(WEB, people=stages.export_people(seated, WEB, person_meta), **_capture_meta())
    for c, arm, mesh in seated: people.pose_at(arm, c['acts'][c['work'][0]], 60)
    for which in str(args.get('cams', 'jerry,george,kramer,elaine')).split(','):
        preview(sc, cams, which, int(args.get('samples', 64)), os.path.join(OUT, f'people_{which}.png'), size=(900, 900))
