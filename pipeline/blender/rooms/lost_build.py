# LOST: assemble the Swan, seat Desmond at the terminal with Jack and Locke behind him, Ben and Kate in the booth over
# coffee; then preview, bake and export.
import math, os
import bpy
from mathutils import Vector, Matrix
import cine, people, stages
from stages import camera
import rooms.lost as R

ROOM = 'lost'
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
    R.shell(M, static, phantom)
    R.dome(M, static, static)
    bulbs = R.computer_corner(M, static)
    bulbs += R.booth(M, static, static)
    R.mainframes(M, static)
    R.pingpong(M, static); R.record_console(M, static)
    R.logo(M, static, (R.BOOTH[0] - 0.25, R.BOOTH[2] - 0.014, 1.78), 0.0)
    R.lights(bulbs)
    _tidy(static)
    seated = [] if args.get('nocast') else cast(crowd, args)
    SEATED[:] = seated
    objs = [o for o in static.objects if o.type == 'MESH']
    cine.bake_ready(objs)
    R.section(objs, M)
    for o in objs:   # procedural meshes get world-scale UVs; imported props keep their own
        if not o.data.uv_layers: cine.world_uv(o, 1.0)
        elif 'UVMap' not in o.data.uv_layers: o.data.uv_layers[0].name = 'UVMap'
    for o in phantom.objects: cine.bake_ready([o]); cine.world_uv(o, 1.0); cine.phantom(o)
    cine.check_module(objs)
    # the web camera's views at room scale (the case view and the closer one), and looks at the corners and the cast
    cams = {'case': camera('cam_case', (11.14, -18.16, 7.95), (-2.30, -1.49, 0.63), 32),
            'close': camera('cam_close', (5.0, -5.6, 3.4), (-0.6, 1.0, 0.9), 30),
            'dome': camera('cam_dome', (1.6, -2.2, 1.7), (-3.2, 0.9, 1.4), 50),
            'desk': camera('cam_desk', (-2.1, -1.0, 1.75), (-4.1, 0.3, 1.0), 40),
            'booth': camera('cam_booth', (2.75, 0.2, 1.6), (2.75, 3.4, 1.0), 44),
            'top': camera('cam_top', (0.0, -0.5, 14.0), (0.0, 0.0, 0.0), 34),
            'desmond': camera('cam_desmond', (-3.85, -0.75, 1.5), (-3.55, 0.28, 1.15), 40),
            'jack': camera('cam_jack', (-3.6, -1.6, 1.75), (-2.42, -0.42, 1.5), 36),
            'locke': camera('cam_locke', (-3.6, 0.0, 1.8), (-2.5, 1.02, 1.5), 36),
            'ben': camera('cam_ben', (3.3, 1.9, 1.4), (1.95, 2.98, 1.0), 38),
            'kate': camera('cam_kate', (2.2, 1.9, 1.4), (3.55, 2.9, 1.0), 38)}
    return sc, M, objs, list(phantom.objects), seated, cams


def _tidy(col):
    """Imported props come under helper empties: keep their children where they are and drop the empties."""
    bpy.context.view_layer.update()
    for o in [o for o in bpy.data.objects if o.type == 'EMPTY']:
        for ch in o.children:
            mw = ch.matrix_world.copy(); ch.parent = None; ch.matrix_world = mw
        bpy.data.objects.remove(o, do_unlink=True)


def preview(sc, cams, which, samples, path, size=(1440, 900)):
    """A Cycles render from one camera; pose=who:act:frame,... poses people first."""
    for spec in filter(None, str(ARGS.get('pose', '')).split(',')):
        who, act, f = spec.split(':')
        for c, arm, mesh in SEATED:
            if c['who'] == who and act in c['acts']: people.pose_at(arm, c['acts'][act], int(c['acts'][act].frame_range[0]) + int(f))
    stages.render(sc, cams[which], samples, path, size, float(ARGS.get('exposure', 0.0)))


# ---------------------------------------------------------------- the cast
# Who is where and what they do. Desmond sits at the terminal: he watches the screen and the counter, and now and then
# enters the numbers (the web types them on the screen and resets the counter as he presses Enter). Jack and Locke stand
# behind him. Ben and Kate sit across the booth's table, over coffee: Ben talks, Kate listens; each picks up a mug.
# Each person has one looping act (`work`: name, min, max seconds) and idles (clip or None for an authored act, weight).
def _tex(who, prefix, *names):
    return {f'{prefix}_{n}.tga': f'{who}/{prefix}_{n}.png' for n in names}


CAST = [
    dict(who='desmond', avatar='Sports_Male_03', shape='lean', scale=0.99, seat='desmond', base='m_sit_table_breathe_01', work=('watch', 8, 20),
         idles={'enter': (None, 2.6), 'look': ('m_sit_table_idle_look_around', 0.7), 'scratch': ('m_sit_table_idle_scratch_head', 0.5),
                'hair': ('m_sit_table_idle_touch_hair', 0.6), 'think': ('m_sit_table_gestic_thoughtful', 0.5)},
         tex=_tex('desmond', 'm300', 'head_color', 'opacity_color', 'body_color')),
    dict(who='jack', avatar='Male_Adult_08', scale=0.99, stand='jack', base='m_idle_breathe_01', work=('stand', 8, 18),
         idles={'hips': (None, 1.4), 'look': ('m_idle_look_around_01', 0.6), 'listen': ('m_gestic_listen_neutral_01', 1.0), 'waiting': ('m_idle_waiting_01', 0.5)},
         tex=_tex('jack', 'm014', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
    dict(who='locke', avatar='Male_Adult_14', shape='athletic', scale=1.0, stand='locke', base='m_idle_neutral_01', work=('stand', 10, 22),
         idles={'listen': ('m_gestic_listen_neutral_01', 1.0), 'neutral': ('m_idle_neutral_02', 0.8), 'breathe': ('m_idle_breathe_02', 0.7), 'look': ('m_idle_look_around_01', 0.5)},
         tex=_tex('locke', 'm012', 'head_color', 'body_color', 'body_normal')),
    dict(who='ben', avatar='Male_Adult_02', shape='lean', scale=0.97, seat='ben', base='m_sit_table_breathe_01', work=('talk', 10, 24),
         idles={'sip': (None, 1.6), 'think': ('m_sit_table_gestic_thoughtful', 0.8), 'face': ('m_sit_table_idle_touch_face', 0.6), 'look': ('m_sit_table_idle_look_around', 0.4)},
         tex=_tex('ben', 'm003', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
    dict(who='kate', avatar='Female_Adult_07', scale=0.95, seat='kate', base='f_sit_table_breathe_01', work=('listen', 8, 20),
         idles={'sip': (None, 1.5), 'talk': (None, 1.0), 'hair': ('f_sit_table_idle_touch_hair', 0.8), 'face': ('f_sit_table_idle_touch_face', 0.5), 'look': ('f_sit_table_idle_look_around', 0.4)},
         tex=_tex('kate', 'f007', 'opacity_color', 'body_color', 'body_normal')),
]
SPINE = ('Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2')
ARMS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('UpperArm', 'Forearm', 'Hand'))
HEAD = ('Bip01 Neck', 'Bip01 Head')
# Desmond's code: when each key goes down in his 'enter' act (seconds), then Enter; the web types and resets by this
TYPE_START, TYPE_STEP, ENTER_AT, ENTER_LEN = 2.0, 0.42, 2.0 + 15 * 0.42 + 0.9, 14.0
# the coffee: when the hand closes on the mug and lets it go in a 'sip' act (seconds); the web carries the mug between
SIP_GRAB, SIP_RELEASE, SIP_LEN = 1.5, 6.2, 8.0


def _seat(c, arm, base, frames):
    """Slide a seated person so the clip's pelvis sits over the seat; report how the heights agree."""
    x, y, facing = R.SEATS[c['seat']]
    people.pose_at(arm, base, frames[0])
    pel = people._world(arm, arm.pose.bones['Bip01 Pelvis']).translation
    want = Vector((x, y, 0)) + Matrix.Rotation(facing, 3, 'Z') @ Vector((0, -0.01, 0))
    arm.location.x += want.x - pel.x; arm.location.y += want.y - pel.y
    bpy.context.view_layer.update()
    cine.log(f"seat {c['who']}: pelvis {pel.z:.3f} m high (seat top {R.SEAT_TOP:.3f})")


def _smooth(x):
    x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)


def _look(arm, at, w, up):
    """Turn the head (and a little the neck) toward a point, by the fraction w."""
    head = arm.pose.bones['Bip01 Head']
    H = people._world(arm, head).translation
    pel, fwd, right, up_ = people.body_frame(arm)
    d = (Vector(at) - H).normalized()
    yaw = math.atan2(d.dot(-right), d.dot(fwd)); pitch = math.asin(max(-1, min(1, d.z)))
    people.bend(arm, 'Bip01 Neck', up_, yaw * 0.35 * w); people.bend(arm, 'Bip01 Head', up_, yaw * 0.65 * w)
    people.bend(arm, 'Bip01 Neck', right, pitch * 0.3 * w); people.bend(arm, 'Bip01 Head', right, pitch * 0.7 * w)


def _keys_pose(arm, lt, rt, fwd, right):
    """Both wrists over the keyboard: wrist targets lt, rt (world), elbows out and down."""
    for s, tgt in (('L', lt), ('R', rt)):
        out = right if s == 'R' else -right
        people.ik2(arm, s, tgt, tgt + out * 0.35 - fwd * 0.25 - Vector((0, 0, 0.45)))
        people.palm_to(arm, s, Vector((0, 0, -1)), 0.85)


def _wrist(key, fwd):
    """Where the wrist is when a finger is on `key`: a hand's length back toward the body, a little above."""
    return key - fwd * 0.085 + Vector((0, 0, 0.035))


def _watch(arm, T):
    """Desmond at the terminal, waiting: hands resting at the keyboard's edge, eyes on the screen, now and then up at the
    counter. Every motion is a whole number of cycles over the act, so it loops without a seam."""
    scr = R.TERM @ Vector((-0.045, -0.12, 0.23)); ctr = Vector((R.TERM.translation.x - 0.1, R.TERM.translation.y, R.COUNTER[0]))
    k = max(1, round(T / 9.0))
    def step(f, t):
        pel, fwd, right, up = people.body_frame(arm)
        home_l, home_r = R.key_world('2') + fwd * 0.05, R.key_world('9') + fwd * 0.05
        _keys_pose(arm, _wrist(home_l, fwd) - Vector((0, 0, 0.015)), _wrist(home_r, fwd) - Vector((0, 0, 0.015)), fwd, right)
        up_at = _smooth((math.sin(2 * math.pi * k * t / T) - 0.55) * 3.0)             # a glance up at the counter
        _look(arm, scr.lerp(ctr, up_at), 0.9, up)
    return step


def _enter(arm, T):
    """Desmond enters the numbers: the hands go to the keys, the code typed a key at a time (left hand 1-5, right
    6-0, the right thumb on the space bar), Enter with the right hand, then he looks up at the counter as it resets."""
    scr = R.TERM @ Vector((-0.045, -0.12, 0.23)); ctr = Vector((R.TERM.translation.x - 0.1, R.TERM.translation.y, R.COUNTER[0]))
    keys = [(TYPE_START + i * TYPE_STEP, ch) for i, ch in enumerate(R.CODE)] + [(ENTER_AT, '\n')]
    def hand_of(ch): return 'L' if ch in '12345' else 'R'
    def step(f, t):
        pel, fwd, right, up = people.body_frame(arm)
        e = people.envelope(t, T, 1.4, 1.6)
        home = {'L': _wrist(R.key_world('3'), fwd), 'R': _wrist(R.key_world('8'), fwd)}
        tgt = dict(home)
        for side in 'LR':
            # this hand's previous and next key, and how far between them it is
            mine = [(tk, ch) for tk, ch in keys if hand_of(ch) == side]
            prev = max([k_ for k_ in mine if k_[0] <= t], default=None, key=lambda k_: k_[0])
            nxt = min([k_ for k_ in mine if k_[0] > t], default=None, key=lambda k_: k_[0])
            p0 = _wrist(R.key_world(prev[1]), fwd) if prev and t - prev[0] < 0.6 else home[side]
            if nxt and nxt[0] - t < 0.35:
                a = _smooth(1 - (nxt[0] - t) / 0.35); p = p0.lerp(_wrist(R.key_world(nxt[1]), fwd), a)
            elif prev and t - prev[0] < 0.6:
                p = p0.lerp(home[side], _smooth((t - prev[0] - 0.25) / 0.35))
            else:
                p = home[side]
            press = sum(max(0.0, 1 - abs(t - tk) / 0.09) for tk, ch in mine)            # the key goes down
            tgt[side] = p - Vector((0, 0, 0.012 * min(press, 1.0)))
        rest = {s: _wrist(R.key_world('2' if s == 'L' else '9'), fwd) + fwd * 0.05 - Vector((0, 0, 0.015)) for s in 'LR'}
        _keys_pose(arm, rest['L'].lerp(tgt['L'], e), rest['R'].lerp(tgt['R'], e), fwd, right)
        for b, a in zip(SPINE, (0.03, 0.04, 0.03)): people.bend(arm, b, right, -a * e)          # leaning in to type
        down = _smooth((t - 1.0) / 0.8) * (1 - _smooth((t - ENTER_AT + 0.1) / 0.4))
        lookup = _smooth((t - ENTER_AT - 0.3) / 0.7) * (1 - _smooth((t - ENTER_AT - 5.0) / 1.5))
        keys_at = R.key_world('5') + Vector((0, 0, 0.0))
        at = scr.lerp(keys_at, 0.45 * down).lerp(ctr, lookup)
        _look(arm, at, 0.9, up)
    return step


def _hips(arm, T):
    """Jack, hands on his hips, watching the screen over Desmond's shoulder."""
    def step(f, t):
        e = people.envelope(t, T, 1.4, 1.4)
        if e <= 0: return
        pel, fwd, right, up = people.body_frame(arm)
        for s, sd in (('L', -1), ('R', 1)):
            H = people._world(arm, arm.pose.bones[f'Bip01 {s} Hand']).translation.copy()
            # each hand tucked against the other arm, the forearms crossed before the chest
            tgt = pel + fwd * 0.19 + up * (0.42 if s == 'L' else 0.39) - right * sd * 0.1
            p = H.lerp(tgt, e)
            people.ik2(arm, s, p, p + right * sd * 0.3 - up * 0.2 - fwd * 0.05)
            people.palm_to(arm, s, -fwd if s == 'L' else up, e * 0.7)
    return step


def _talk(arm, T, lap=False):
    """Talking across the table: forearms on its edge, the right hand lifting and opening as he makes a point, the
    left now and then; small nods and turns of the head. Whole cycles over the act, so it loops."""
    k1, k2, k3 = max(1, round(T / 5.5)), max(1, round(T / 9.0)), max(1, round(T / 3.7))
    def step(f, t):
        pel, fwd, right, up = people.body_frame(arm)
        lean = (0.07, 0.09, 0.07) if lap else (0.04, 0.05, 0.04)
        for b, a in zip(SPINE, lean): people.bend(arm, b, right, -a)                           # leaning in
        pel, fwd, right, up = people.body_frame(arm)
        u = 2 * math.pi * t / T
        g_r = _smooth((math.sin(k1 * u) - 0.1) * 1.6)                                          # the right hand's gestures
        g_l = _smooth((math.sin(k2 * u + 2.0) - 0.55) * 2.5) * 0.7
        z = R.TABLE_TOP + 0.03 - pel.z
        for s, sd, g in (('L', -1, g_l), ('R', 1, g_r)):
            rest = pel + fwd * 0.3 + up * 0.1 + right * sd * 0.07 if lap else pel + fwd * 0.44 + up * z + right * sd * 0.15   # her hands on her thighs
            lift = fwd * 0.05 + up * (0.13 + 0.03 * math.sin(k3 * u + sd)) + right * sd * 0.07
            tgt = rest + lift * g
            people.ik2(arm, s, tgt, tgt + right * sd * 0.35 - up * 0.25 - fwd * 0.2)
            people.palm_to(arm, s, (-up).lerp(up * 0.6 - right * sd * 0.4, g).normalized(), 1.0)
        nod = math.radians(3.5) * math.sin(k3 * u) * (0.5 + 0.5 * g_r)
        people.bend(arm, 'Bip01 Head', right, nod); people.bend(arm, 'Bip01 Head', up, math.radians(4) * math.sin(k2 * u))
    return step


def _sip(arm, T, mug, side, lean_in=0.12):
    """Picking the mug up by its handle, a sip, putting it back where it was: the reach leans the body in a little."""
    sd = 1 if side == 'R' else -1
    def step(f, t):
        pel, fwd, right, up = people.body_frame(arm)
        head = people._world(arm, arm.pose.bones['Bip01 Head']).translation.copy()
        grip = Vector(mug) + right * sd * 0.07 - fwd * 0.03 + Vector((0, 0, 0.06))       # the wrist by the handle
        mouth = head + fwd * 0.15 - up * 0.07 + right * sd * 0.05
        H = people._world(arm, arm.pose.bones[f'Bip01 {side} Hand']).translation.copy()
        reach = _smooth(t / SIP_GRAB) * (1 - _smooth((t - SIP_RELEASE) / (T - SIP_RELEASE - 0.3)))
        lift = _smooth((t - SIP_GRAB - 0.1) / 1.1) * (1 - _smooth((t - SIP_RELEASE + 1.3) / 1.1))
        lean = lean_in * (reach - 0.6 * lift)
        for b, a in zip(SPINE, (0.3, 0.4, 0.3)): people.bend(arm, b, right, -lean * a)
        pel, fwd, right, up = people.body_frame(arm)
        tgt = H.lerp(grip.lerp(mouth, lift), reach)
        people.ik2(arm, side, tgt, tgt + right * sd * 0.3 - up * 0.35 - fwd * 0.1)
        people.palm_to(arm, side, -right * sd, reach)
        if lift > 0: people.bend(arm, 'Bip01 Head', right, 0.12 * lift)                    # a tip of the head to drink
    return step


def cast(col, args):
    """Load, dress, shape and place the five, and bake their acts (cached: retargets and IK take minutes)."""
    full = bool(args.get('full'))
    spec = {'cast': CAST, 'seats': R.SEATS, 'stand': R.STAND, 'mugs': R.MUGS, 'term': [list(r) for r in R.TERM], 'counter': R.COUNTER,
            'type': (TYPE_START, TYPE_STEP, ENTER_AT, ENTER_LEN), 'sip': (SIP_GRAB, SIP_RELEASE, SIP_LEN), 'full': full, 'v': 6}
    seated = stages.cast_cache(OUT, CAST, spec, lambda: _make_cast(col, full), col)
    for c, arm, mesh in seated: people.pose_at(arm, c['acts'][c['work'][0]], 30)
    return seated


def _make_cast(col, full):
    seated = []
    for c in CAST:
        arm, mesh = people.load_avatar(c['avatar'], textures={k: os.path.join(PEOPLE_TEX, v) for k, v in c['tex'].items()}, collection=col)
        mesh['person'] = c['who']; arm['person'] = c['who']
        if c.get('shape'): people.reshape(arm, mesh, c['shape'])
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
        acts = {}
        who = c['who']
        if who == 'desmond':
            acts['watch'] = people.custom_act(arm, base, frames, 'desmond_watch', _watch(arm, T), SPINE + ARMS + HEAD)
            if full:
                n = int(ENTER_LEN * people.FPS)
                acts['enter'] = people.custom_act(arm, base, (frames[0], frames[0] + n), 'desmond_enter', _enter(arm, n / people.FPS), SPINE + ARMS + HEAD)
        elif who in ('ben', 'kate'):
            talking = people.custom_act(arm, base, frames, f'{who}_talk', _talk(arm, T, lap=who == 'kate'), SPINE + ARMS + ('Bip01 Head',))
            if who == 'ben': acts['talk'] = talking
            else: acts['listen'] = base
            if full:
                if who == 'kate': acts['talk'] = talking
                mx, my, hs = R.MUGS[who]; n = int(SIP_LEN * people.FPS)
                acts['sip'] = people.custom_act(arm, base, (frames[0], frames[0] + n), f'{who}_sip', _sip(arm, n / people.FPS, (mx, my, R.TABLE_TOP), 'R', 0.62 if who == 'kate' else 0.12), SPINE + ARMS + ('Bip01 Head',))
            elif who == 'kate': bpy.data.actions.remove(talking)
            if who == 'kate': base = None
        else:
            acts['stand'] = base; base = None
            if full and who == 'jack':
                acts['hips'] = people.custom_act(arm, acts['stand'], frames, 'jack_hips', _hips(arm, T), ARMS)
        if full:
            for k, (clip, _w) in c['idles'].items():   # each starts where the looping act starts
                if clip: acts[k] = people.anchor(arm, people.retarget(arm, clip, action_name=f"{who}_{k}")[0], acts[c['work'][0]])
        if base: bpy.data.actions.remove(base)
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
    """What the web needs: how to light the people as the bake lit the room (the dome's people by its cool light, the
    booth's by its warm; three.js coordinates, y up, z = -Blender y), and what it plays live (the terminal and the
    counter, the mugs)."""
    import bpy as _b
    bulbs = []
    for l in _b.data.objects:
        if l.type != 'LIGHT' or l.data.type not in ('POINT', 'SPOT'): continue
        r = 0.03 if l.data.type == 'POINT' else 0.05
        bulbs.append({'x': round(l.location.x, 3), 'y': round(l.location.z, 3), 'z': round(-l.location.y, 3), 'r': r,
                      'L': round(l.data.energy / (4 * math.pi * r ** 2) / 60, 2), 'color': [round(c, 3) for c in l.data.color]})
    cx, cz, w, h = R.WIN
    windows = [{'x': cx, 'y': cz, 'z': -(R.D / 2 - 0.05), 'w': w, 'h': h, 'L': 1.2, 'color': list(R.DAY), 'ry': 0.0}]
    for k in range(6):   # the dome's cove, as glowing strips along the riser
        th = R.THETA_A + (R.THETA_B - R.THETA_A) * (k + 0.5) / 6; p = R.dome_point(th, R.DOME_R - 0.12, R.RISER + 0.4)
        windows.append({'x': round(p.x, 3), 'y': round(p.z, 3), 'z': round(-p.y, 3), 'w': 1.4, 'h': 0.8, 'L': 0.9, 'color': list(R.TEAL), 'ry': round(math.pi / 2 + th, 3)})
    s = R.SEATS
    return {'capture': {'ceiling': [0.1, 0.11, 0.1], 'walls': [0.2, 0.15, 0.11], 'emitters': bulbs, 'windows': windows,
                        'at': [[-3.0, 1.3, -0.3], [2.75, 1.1, -2.9]]},
            'live': {'terminal': {'who': 'desmond', 'act': 'enter', 'text': R.CODE, 'start': TYPE_START, 'step': TYPE_STEP, 'enter': ENTER_AT},
                     'held': [{'who': who, 'act': 'sip', 'prop': f'mug_{who}', 'hand': 'R', 'grab': SIP_GRAB, 'release': SIP_RELEASE} for who in ('ben', 'kate')]}}


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
    for which in str(args.get('cams', 'desmond,jack,locke,ben,kate')).split(','):
        preview(sc, cams, which, int(args.get('samples', 64)), os.path.join(OUT, f'people_{which}.png'), size=(900, 900))
