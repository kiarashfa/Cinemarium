# Breaking Bad: assemble Saul's office and the waiting room; seat Saul at his desk and Walt and Jesse before it, stand
# Huell by the door; their acts (Jesse in from the waiting room, Walt up and pointing, Saul's finger guns, Huell's
# watch at the door); then preview, bake and export.
import math, os
import bpy
from mathutils import Vector, Matrix, Quaternion
import cine, people, stages
from stages import camera
import rooms.breaking_bad as R

ROOM = 'breaking-bad'
OUT = os.path.join(cine.OUT, ROOM)
WEB = os.path.join(cine.ROOT, 'public', 'rooms', ROOM)
PEOPLE_TEX = os.path.join(cine.OUT, 'people')
ARGS = {}
SEATED = []
RIG = {'lights': []}


def build(args):
    ARGS.clear(); ARGS.update(args)
    sc = cine.reset(int(args.get('samples', 256)))
    M = R.mats()
    static, phantom, crowd = cine.coll('static'), cine.coll('phantom'), cine.coll('people')
    R.shell(M, static, static, phantom)
    portholes = R.bay(M, static, static)
    desk_bulb, lady = R.desk(M, static)
    R.saul_chair(M, static)
    for who in ('walt', 'jesse'): R.client_chair(who, M, static)
    sofa_bulb = R.sofa(M, static)
    sconce = R.library(M, static)
    R.door(M, static)
    door_bulb = R.office_things(M, static)
    R.storefront(M, static)
    wait_bulb = R.waiting(M, static)
    booth_bulb = R.booth(M, static)
    RIG['lights'] = R.lights(portholes, desk_bulb, door_bulb, sofa_bulb, sconce, wait_bulb, booth_bulb)
    _tidy()
    seated = [] if args.get('nocast') else cast(crowd, args)
    SEATED[:] = seated
    _lady_justice(static, M, lady)
    objs = [o for o in static.objects if o.type == 'MESH']
    cine.bake_ready(objs)
    R.section(objs, M)
    for o in objs:
        if not o.data.uv_layers: cine.world_uv(o, 1.0)
        elif 'UVMap' not in o.data.uv_layers: o.data.uv_layers[0].name = 'UVMap'
    objs = _merge(objs)
    for o in phantom.objects: cine.bake_ready([o]); cine.world_uv(o, 1.0); cine.phantom(o)
    cine.check_module(objs)
    cams = {'case': camera('cam_case', (11.14, -18.16, 7.95), (-2.30, -1.49, 0.63), 32),
            'close': camera('cam_close', (5.4, -5.8, 3.6), (-1.0, 0.9, 0.9), 30),
            'bay': camera('cam_bay', (-1.4, -2.6, 1.55), (-1.4, 2.8, 1.35), 52),
            'door': camera('cam_door', (-1.6, -0.6, 1.6), (1.9, 1.05, 1.15), 50),
            'wait': camera('cam_wait', (2.7, -2.9, 1.7), (3.4, 3.4, 1.15), 50),
            'sofa': camera('cam_sofa', (-1.6, -3.4, 1.6), (-4.2, -1.4, 0.8), 52),
            'top': camera('cam_top', (0.0, -0.3, 14.0), (0.0, 0.0, 0.0), 34),
            'saul': _person_cam('saul', 25), 'walt': _person_cam('walt', 140), 'jesse': _person_cam('jesse', -140)}
    return sc, M, objs, list(phantom.objects), seated, cams


def _person_cam(who, turn, dist=2.2):
    """A look at one of them: from `turn` degrees off their facing, 2.2 m away."""
    p, f = R.chair_at(who); d = Matrix.Rotation(math.radians(turn), 3, 'Z') @ f
    return camera(f'cam_{who}_{turn}', tuple(p + d * dist + Vector((0, 0, 1.3))), tuple(p + Vector((0, 0, 0.85))), 36)


def _tidy():
    """Imported props come under helper empties: keep their children where they are and drop the empties."""
    bpy.context.view_layer.update()
    for o in [o for o in bpy.data.objects if o.type == 'EMPTY']:
        for ch in o.children:
            mw = ch.matrix_world.copy(); ch.parent = None; ch.matrix_world = mw
        bpy.data.objects.remove(o, do_unlink=True)


KEEP = ('solid_', 'wall_', 'back_wall', 'left_wall', 'kerb', 'floor', 'subfloor')   # names that carry rules (sections, cut tops)


def _merge(objs):
    """Join the many small pieces, one object per atlas and material: fewer meshes to draw."""
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


def _lady_justice(col, M, at):
    """Lady Justice on the desk, in dark bronze: a body cast from a Rocketbox figure, her left arm raised with the
    scales, the sword down in her right; on a square base, about 45 cm high."""
    arm, mesh = people.load_avatar('Female_Adult_07', collection=col)
    k = [i for i, s in enumerate(mesh.material_slots) if s.material and 'opacity' in s.material.name]
    if k:
        import bmesh
        bm = bmesh.new(); bm.from_mesh(mesh.data)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in k], context='FACES'); bm.to_mesh(mesh.data); bm.free()
    act, frames, _ = people.retarget(arm, 'f_idle_neutral_02', action_name='lady_pose')
    people.pose_at(arm, act, frames[0] + 40)
    arm.animation_data.action = None                                  # hold the pose for the edits below
    people.face(arm, Vector((0, -1, 0)))
    bpy.context.view_layer.update()
    sh = people._world(arm, arm.pose.bones['Bip01 L UpperArm']).translation
    people.ik2(arm, 'L', sh + Vector((0.12, -0.05, 0.42)), sh + Vector((0.4, 0.1, 0.1)))      # the scales held high
    shr = people._world(arm, arm.pose.bones['Bip01 R UpperArm']).translation
    people.ik2(arm, 'R', shr + Vector((-0.12, -0.22, -0.4)), shr + Vector((-0.4, 0.2, -0.2)))  # the sword down
    bpy.context.view_layer.update()
    s = 0.27
    deps = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(mesh.evaluated_get(deps))
    ob = bpy.data.objects.new('lady_justice', me); col.objects.link(ob)
    ob.matrix_world = mesh.matrix_world.copy()
    me.materials.clear(); me.materials.append(M['bronze'])
    for p in me.polygons: p.material_index = 0
    lo = min((ob.matrix_world @ v.co).z for v in me.vertices)
    hl = people._world(arm, arm.pose.bones['Bip01 L Hand']).translation.copy(); hr = people._world(arm, arm.pose.bones['Bip01 R Hand']).translation.copy()
    feet = Vector((arm.matrix_world.translation.x, arm.matrix_world.translation.y, lo))
    base = Vector(at) + Vector((0, 0, 0.03))
    T = Matrix.Translation(base) @ Matrix.Diagonal((s, s, s, 1)) @ Matrix.Translation(-feet)
    ob.matrix_world = T @ ob.matrix_world
    ob['lm'] = 'furn'
    for o in (arm, mesh): bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.actions.remove(act)
    cine.world_uv(ob, 0.6)
    cine.box('lady_base', (0.1, 0.1, 0.03), Vector(at) + Vector((0, 0, 0.015)), M['bronze'], bev=0.004, collection=col, lm='furn')
    hl, hr = T @ hl, T @ hr
    cine.cyl('lady_beam', 0.002, 0.12, hl + Vector((0, 0, 0.012)), M['brass'], rot=(0, math.pi / 2, 0), seg=6, collection=col, lm='furn')
    for sd in (-1, 1):
        cine.lathe(f'lady_pan{sd}', [(0.0, 0.0), (0.018, 0.004), (0.02, 0.008), (0.0, 0.002)], M['brass'], loc=hl + Vector((sd * 0.06, 0, -0.04)), seg=12, collection=col, lm='furn')
    cine.box('lady_sword', (0.006, 0.006, 0.16), hr + Vector((0, 0, -0.07)), M['brass'], bev=0, collection=col, lm='furn')


def preview(sc, cams, which, samples, path, size=(1440, 900)):
    """A Cycles render from one camera; pose=who:act:frame poses one person first; seq=who:act:s1;s2;... renders the act
    at each of those seconds, with the acts it cues posed alongside."""
    if ARGS.get('seq'):
        who, act, ts = str(ARGS['seq']).split(':')
        cued = next((c.get('cue', {}).get(act, {}) for c, a_, m_ in SEATED if c['who'] == who), {})
        for t in ts.split(';'):
            for c, arm, mesh in SEATED:
                a = act if c['who'] == who else cued.get(c['who'])
                if a and a in c['acts']: people.pose_at(arm, c['acts'][a], int(c['acts'][a].frame_range[0]) + int(float(t) * people.FPS))
            stages.render(sc, cams[which], samples, path.replace('.png', f'_{act}_{float(t):04.1f}.png'), (960, 600), float(ARGS.get('exposure', 0.0)))
        return
    for spec in filter(None, str(ARGS.get('pose', '')).split(',')):
        who, act, f = spec.split(':')
        for c, arm, mesh in SEATED:
            if c['who'] == who and act in c['acts']: people.pose_at(arm, c['acts'][act], int(c['acts'][act].frame_range[0]) + int(f))
    stages.render(sc, cams[which], samples, path, size, float(ARGS.get('exposure', 0.0)))


# ---------------------------------------------------------------- the cast
# "Mandala" (season two): Saul behind his desk talking with his hands; Walt upright in the left client chair, listening
# hard; Jesse slumped in the right one; Huell (from season four) on guard by the door in the waiting room. Each has a
# looping act and idles; the three big ones (Jesse out to the street door and back in, Walt up and pointing at Saul,
# Saul's double finger guns) cue the others' reactions, so they play together.
def _tex(who, prefix, *names):
    return {f'{prefix}_{n}.tga': f'{who}/{prefix}_{n}.png' for n in names}


CAST = [
    dict(who='saul', avatar='Business_Male_03', shape='lean', shape_k=1.4, height=1.78, base='m_sit_chair_breathe_01', work=('talk', 9, 18),
         talk='m_gestic_talk_excited_01',
         idles={'guns': (None, 1.5), 'think': ('m_sit_chair_gestic_thoughtful', 0.5), 'shrug': ('m_sit_chair_gestic_shrug_01', 0.6), 'hush': (None, 0.0)},
         cue={'guns': {'walt': 'watch'}}, roam=('guns',), hands=('guns', 'hush'),
         tex=_tex('saul', 'm020', 'head_color', 'opacity_color', 'body_color')),
    dict(who='walt', avatar='Business_Male_04', height=1.79, base='m_sit_chair_breathe_01', work=('listen', 9, 20), extra='frames',
         idles={'point': (None, 1.6), 'face': ('m_sit_chair_idle_touch_face', 0.5), 'think': ('m_sit_chair_gestic_thoughtful', 0.5), 'watch': (None, 0.0)},
         cue={'point': {'saul': 'hush'}}, roam=('point',), hands=('point',),
         tex=_tex('walt', 'm015', 'head_color', 'body_color', 'body_normal')),
    dict(who='jesse', avatar='Male_Adult_20', height=1.76, base='m_sit_chair_breathe_01', work=('slouch', 8, 16), extra='beanie',
         idles={'enter': (None, 1.4), 'nervous': ('m_sit_chair_idle_nervous_01', 0.5), 'look': ('m_sit_chair_idle_look_around', 0.4),
                'scratch': ('m_sit_chair_idle_scratch_head', 0.4)},
         cue={'enter': {'huell': 'watch'}}, roam=('enter',), hands=(),
         tex=_tex('jesse', 'm027', 'head_color', 'body_color')),
    dict(who='huell', avatar='Male_Adult_12', shape='heavy', shape_k=1.85, height=1.85, stand=True, base='m_idle_breathe_01', work=('guard', 10, 24),
         idles={'look': ('m_idle_look_around_01', 0.6), 'shift': ('m_idle_neutral_02', 0.5), 'watch': (None, 0.0)}, hands=(),
         tex=_tex('huell', 'm007', 'head_color', 'body_color', 'body_normal')),
]
FIRST = {'jesse': 'enter'}           # the room opens on Jesse coming back in from the street door (see OPEN)
OPEN = {}                            # who: (act, seconds into it the room opens at), set when the act is made
SPINE = ('Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2')
ARMS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('Clavicle', 'UpperArm', 'Forearm', 'Hand'))
LEGS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('Thigh', 'Calf', 'Foot'))
HEAD = ('Bip01 Neck', 'Bip01 Head')
FINGERS = tuple(f'Bip01 {s} Finger{f}{j}' for s in 'LR' for f in '01234' for j in ('', '1', '2'))
ALL = ('Bip01 Pelvis',) + SPINE + ARMS + LEGS + HEAD


def _all(arm, fingers=False):
    """Every bone an authored act keys: the root (it carries the drop into the chair), the body, the head; the fingers
    when the act shapes the hands."""
    return (next(b.name for b in arm.data.bones if b.parent is None),) + ALL + (FINGERS if fingers else ())


def _smooth(x):
    x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)


def _look(arm, at, w):
    """Turn the head (and a little the neck) toward a point, by the fraction w."""
    if w <= 0: return
    H = people._world(arm, arm.pose.bones['Bip01 Head']).translation
    pel, fwd, right, up = people.body_frame(arm)
    d = (Vector(at) - H).normalized()
    yaw = math.atan2(d.dot(-right), d.dot(fwd)); pitch = math.asin(max(-1, min(1, d.z)))
    people.bend(arm, 'Bip01 Neck', up, yaw * 0.35 * w); people.bend(arm, 'Bip01 Head', up, yaw * 0.65 * w)
    people.bend(arm, 'Bip01 Neck', right, pitch * 0.3 * w); people.bend(arm, 'Bip01 Head', right, pitch * 0.7 * w)


def _head_of(who):
    """Where a seated person's head is (or Huell's, standing)."""
    if who == 'huell': return R.HUELL[0] + Vector((0, 0, 1.72))
    p, f = R.chair_at(who)
    return Vector((p.x, p.y, 1.16 if who == 'saul' else 1.12)) + f * 0.06


def _between():
    """Saul's eyes go between his two clients."""
    return (_head_of('walt') + _head_of('jesse')) / 2


def _frame_of(arm):
    """The body frame from the pelvis and the stored facing (not from the feet, which the legs' IK moves)."""
    pel = people._world(arm, arm.pose.bones['Bip01 Pelvis']).translation.copy()
    fwd = Vector(arm['fwd']); up = Vector((0, 0, 1)); right = fwd.cross(up).normalized()
    return pel, fwd, right, up


def _spread(arm, w, wide=0.2, reach=0.5):
    """Jesse's knees fallen apart: both feet planted wide and forward."""
    if w <= 0: return
    pel, fwd, right, up = _frame_of(arm)
    for s, sd in (('L', -1), ('R', 1)):
        A0 = people._world(arm, arm.pose.bones[f'Bip01 {s} Foot']).translation.copy()
        tgt = pel + fwd * reach + right * sd * wide; tgt.z = 0.1
        people.ik_leg(arm, s, A0.lerp(tgt, w), tgt + fwd * 0.5 + up * 0.45 + right * sd * 0.35)


def _overlay(who, drop):
    """What every seated act of theirs shares: lowered into the chair, then each one's own sitting (Saul leans to his
    clients over the desk, Walt sits up straight, Jesse slumps, knees apart), the head toward whom they listen to."""
    def apply(arm, t, T, look=0.7, nod=0.0, legs=1.0):
        people.shift_root(arm, (0, 0, -drop))
        pel, fwd, right, up = _frame_of(arm)
        if who == 'saul':
            for b, a in zip(SPINE, (-0.06, -0.05, -0.03)): people.bend(arm, b, right, a)          # over the desk
            at = _between()
        elif who == 'walt':
            for b, a in zip(SPINE, (-0.02, -0.02, 0.0)): people.bend(arm, b, right, a)
            at = _head_of('saul')
        else:
            people.shift_root(arm, fwd * 0.07 - up * 0.03)                                   # slid down in the seat
            for b, a in zip(SPINE, (0.1, 0.07, 0.03)): people.bend(arm, b, right, a)          # slumped back
            _spread(arm, legs)
            at = _head_of('saul')
        k = max(1, round(T / 6.0)) if T > 0 else 1
        n = nod * math.sin(2 * math.pi * k * t / T) if T > 0 else 0.0
        _look(arm, at + Vector((0, 0, n * 0.06)), look)
    return apply


def _seat(c, arm, base, frames):
    """Slide a seated person so the clip's pelvis sits over the chair's seat; report how the heights agree."""
    p, f = R.chair_at(c['who'])
    people.pose_at(arm, base, frames[0])
    pel = people._world(arm, arm.pose.bones['Bip01 Pelvis']).translation
    want = p - f * 0.04
    arm.location.x += want.x - pel.x; arm.location.y += want.y - pel.y
    bpy.context.view_layer.update()
    cine.log(f"seat {c['who']}: pelvis {pel.z:.3f} m high (seat {R.SEAT[c['who']]:.3f})")


def _stand(c, arm, base, frames):
    """Huell: the clip's pelvis over his spot by the door."""
    p = R.HUELL[0]
    people.pose_at(arm, base, frames[0])
    pel = people._world(arm, arm.pose.bones['Bip01 Pelvis']).translation
    arm.location.x += p.x - pel.x; arm.location.y += p.y - pel.y
    bpy.context.view_layer.update()


def cast(col, args):
    """Load, dress, shape and place the four, and bake their acts (cached: retargets and IK take minutes)."""
    full = bool(args.get('full'))
    spec = {'cast': CAST, 'chairs': R.CHAIRS, 'seat': R.SEAT, 'huell': [list(v) for v in R.HUELL], 'door': R.DOOR, 'exit': list(R.WAIT_EXIT),
            'full': full, 'v': 3}
    seated = stages.cast_cache(OUT, CAST, spec, lambda: _make_cast(col, full), col)
    for c, arm, mesh in seated:
        if 'open_act' in arm: OPEN[c['who']] = (arm['open_act'], float(arm['open_at']))
        people.pose_at(arm, c['acts'][c['work'][0]], 30)
    return seated


def _height(arm, mesh):
    bpy.context.view_layer.update()
    return max((mesh.matrix_world @ v.co).z for v in mesh.data.vertices)


def _make_cast(col, full):
    gold = cine.material('wire_gold', (0.75, 0.56, 0.3), rough=0.25, metal=1.0)
    knit = cine.material('beanie_knit', (0.016, 0.016, 0.018), rough=0.95, sheen=0.15, sheen_tint=(0.2, 0.2, 0.2))
    red = cine.material('beanie_rim', (0.34, 0.03, 0.04), rough=0.9)
    seated, made = [], {}
    for c in CAST:
        who = c['who']
        arm, mesh = people.load_avatar(c['avatar'], textures={k: os.path.join(PEOPLE_TEX, v) for k, v in c['tex'].items()}, collection=col)
        mesh['person'] = who; arm['person'] = who
        if c.get('shape'): people.reshape(arm, mesh, c['shape'], c.get('shape_k', 1.0))
        if c.get('extra') == 'frames': people.add_frames(arm, mesh, gold)
        if c.get('extra') == 'beanie': people.beanie(arm, mesh, knit, red)
        s = c['height'] / _height(arm, mesh)
        arm.scale = arm.scale * s; arm.location = (arm.location.x, arm.location.y, arm.location.z * s)
        bpy.context.view_layer.update()
        if c.get('stand'): p, f = R.HUELL
        else: p, f = R.chair_at(who)
        f = Vector(f).normalized()
        people.face(arm, f); arm.location = (p.x, p.y, arm.location.z)
        bpy.context.view_layer.update()
        arm['fwd'] = list(f)
        base, frames, _ = people.retarget(arm, c['base'], cycles=2, action_name=f'{who}_base')
        (_stand if c.get('stand') else _seat)(c, arm, base, frames)
        T = (frames[1] - frames[0]) / people.FPS
        acts = {}
        if c.get('stand'):
            acts['guard'] = people.custom_act(arm, base, frames, 'huell_guard', lambda f_, t: _guard(arm, t, T, 1.0), _all(arm))
            if full:
                for name, (clip, _w) in c['idles'].items():
                    if not clip: continue
                    src = people.anchor(arm, people.retarget(arm, clip, action_name=f'{who}_{name}_src')[0], base)
                    fr = (int(src.frame_range[0]), int(src.frame_range[1])); Ti = (fr[1] - fr[0]) / people.FPS
                    acts[name] = people.custom_act(arm, src, fr, f'{who}_{name}', lambda f_, t, Ti=Ti: _guard(arm, t, Ti, 0.75), _all(arm))
                    bpy.data.actions.remove(src)
            c['acts'] = acts; made[who] = (c, arm, mesh, base, frames, 0.0)
            seated.append((c, arm, mesh)); continue
        drop = 0.52 - R.SEAT[who]; ov = _overlay(who, drop)
        if who == 'saul':
            talk, tf, _ = people.retarget(arm, c['talk'], action_name='saul_talk_src')
            k = max(1, round((frames[1] - frames[0]) / (tf[1] - tf[0])))
            if k > 1: bpy.data.actions.remove(talk); talk = people.retarget(arm, c['talk'], cycles=k, action_name='saul_talk_src')[0]
            layered = people.layer(base, talk, keys=('Neck', 'Head'), name='saul_talk_layer'); bpy.data.actions.remove(talk)
            acts['talk'] = people.custom_act(arm, layered, frames, 'saul_talk', lambda f_, t: (ov(arm, t, T, look=0.55), _desk_hands(arm, t, T)), _all(arm, fingers=True))
            bpy.data.actions.remove(layered)
        elif who == 'walt':
            acts['listen'] = people.custom_act(arm, base, frames, 'walt_listen', lambda f_, t: ov(arm, t, T, look=0.8, nod=0.25), _all(arm))
        else:
            acts['slouch'] = people.custom_act(arm, base, frames, 'jesse_slouch', lambda f_, t: ov(arm, t, T, look=0.5), _all(arm))
        if full:
            for name, (clip, _w) in c['idles'].items():
                if not clip or name in acts: continue
                src = people.anchor(arm, people.retarget(arm, clip, action_name=f'{who}_{name}_src')[0], base)
                fr = (int(src.frame_range[0]), int(src.frame_range[1])); Ti = (fr[1] - fr[0]) / people.FPS
                fix = (lambda: _over_desk(arm)) if who == 'saul' else (lambda: None)
                acts[name] = people.custom_act(arm, src, fr, f'{who}_{name}', lambda f_, t, Ti=Ti, fix=fix: (ov(arm, t, Ti, look=0.3), fix()), _all(arm))
                bpy.data.actions.remove(src)
        c['acts'] = acts; made[who] = (c, arm, mesh, base, frames, drop)
        seated.append((c, arm, mesh))
    if full:
        jc, jarm, *_r = made['jesse']; jdrop = made['jesse'][5]
        jc['acts']['enter'] = _enter(jarm, jc['acts']['slouch'], jdrop)
        wc, warm = made['walt'][0], made['walt'][1]
        wc['acts']['point'] = _point(warm, wc['acts']['listen'])
        sc_, sarm = made['saul'][0], made['saul'][1]
        sc_['acts']['guns'] = _guns(sarm, sc_['acts']['talk'])
        hc, harm, _m, hbase, hframes, _d = made['huell']
        hc['acts']['watch'] = _huell_watch(harm, hc, jarm, jc['acts']['enter'])
        sc_['acts']['hush'] = _hush(sarm, sc_, made['saul'][5], warm, wc['acts']['point'])
        wc['acts']['watch'] = _walt_watch(warm, wc, made['walt'][5], sarm, sc_['acts']['guns'])
    for c, arm, mesh in seated:
        for name, a in c['acts'].items():
            if name not in c.get('hands', ()): people.freeze(a)
        base = made[c['who']][3]
        if base not in c['acts'].values(): bpy.data.actions.remove(base)
        people.pose_at(arm, c['acts'][c['work'][0]], 30)
    return seated


def _over_desk(arm):
    """Saul's hands kept out of the desk (an idle danced in an armchair would lay them in his lap, under its top):
    any hand under the top and forward of his belly is lifted onto it, the elbow down and out."""
    pel, fwd, right, up = _frame_of(arm)
    edge = (R.DESK.y + 0.48)                                                   # the desk's back edge (y)
    for s, sd in (('L', -1), ('R', 1)):
        H = people._world(arm, arm.pose.bones[f'Bip01 {s} Hand']).translation
        if H.z < 0.82 and H.y < edge + 0.12:
            tgt = Vector((H.x, min(H.y, edge - 0.04), 0.82))
            people.ik2(arm, s, tgt, tgt - up * 0.35 + right * sd * 0.28 + fwd * 0.05)


def _desk_hands(arm, t, T):
    """Saul talking across his desk: forearms over its edge, both hands working the air in front of him, in turn, palms
    turning up and out as he makes his case; every motion a whole number of cycles over the loop."""
    pel, fwd, right, up = _frame_of(arm)
    u = 2 * math.pi * t / T if T > 0 else 0.0
    k = lambda per: max(1, round(T / per)) if T > 0 else 1
    edge = R.DESK.y + 0.48
    for s, sd, ph in (('L', -1, 0.0), ('R', 1, 1.9)):
        busy = 0.5 + 0.5 * math.sin(k(5.2) * u + ph)                            # the hands take turns
        loop = (math.sin(k(1.3) * u + ph), math.cos(k(1.3) * u + ph))
        lift = max(0.0, math.sin(k(2.6) * u + ph * 1.3)) ** 1.5
        base = Vector((pel.x, edge - 0.08, 0.84)) + right * sd * 0.2
        tgt = base + right * sd * 0.05 * loop[0] * busy + fwd * 0.04 * loop[1] * busy + up * (0.04 + 0.16 * lift * busy)
        people.ik2(arm, s, tgt, tgt - up * 0.35 + right * sd * 0.3 + fwd * 0.02)
        people.palm_to(arm, s, (up * (0.4 + 0.6 * lift) + right * sd * 0.5 - fwd * 0.2).normalized(), 0.5 + 0.4 * busy)


def _guard(arm, t, T, w):
    """Huell's guard: hands clasped low before him under the belly, a slow look round the room now and then."""
    pel, fwd, right, up = people.body_frame(arm)
    c = pel + fwd * 0.3 - up * 0.08
    for s, sd in (('L', -1), ('R', 1)):
        people.ik2(arm, s, c + right * sd * 0.035 + up * (0.01 if s == 'L' else -0.01), c + right * sd * 0.45 + up * 0.15 - fwd * 0.1)
        people.palm_to(arm, s, -right * sd, 0.6 * w)
    k = max(1, round(T / 9.0)) if T > 0 else 1
    yaw = 0.25 * math.sin(2 * math.pi * k * t / T) if T > 0 else 0.0
    people.bend(arm, 'Bip01 Head', up, yaw * w)


# ---------------------------------------------------------------- Jesse: out to the street door and back in
def _enter(arm, slouch, drop):
    """Jesse, about 34 seconds: up out of the chair, round it and out through the office door past Huell, across the
    waiting room to the glass street door, where he stands looking out; then back in the same way and down into the
    chair again. The room opens as he turns back from the door (OPEN), so the first thing seen is him coming in."""
    FPS = people.FPS
    up, upf, _ = people.retarget(arm, 'm_sit_stand_up_chair_01', action_name='jesse_src_up')
    walk, walkf, speed = people.retarget(arm, 'm_walk_cool_01', inplace=True, cycles=8, action_name='jesse_src_walk')
    look, lookf, _ = people.retarget(arm, 'm_idle_look_around_01', cycles=2, action_name='jesse_src_look')
    down, downf, _ = people.retarget(arm, 'm_sit_down_chair_01', action_name='jesse_src_down')
    cine.log(f'jesse walk speed {speed:.2f} m/s')
    t0f = int(slouch.frame_range[0])
    _h, p_s = people.heading(arm, slouch, t0f); h_s = Vector(arm['fwd'])
    def ends(action, f, M):
        h, p = people.heading(arm, action, f)
        return (M.to_3x3() @ h).normalized(), M @ p
    hu, pu = people.heading(arm, up, upf[0]); M_up = people.carry(pu, hu, p_s, h_s)
    hu1, pu1 = ends(up, upf[1], M_up)
    hd, pd = people.heading(arm, down, downf[1]); M_down = people.carry(pd, hd, p_s, h_s)
    hd0, pd0 = ends(down, downf[0], M_down)
    d0, d1, dh = R.DOOR; door_y = (d0 + d1) / 2
    right = Vector((h_s.y, -h_s.x, 0))
    ex = R.WAIT_EXIT
    out = [pu1, pu1 + right * 0.4 - h_s * 0.05, Vector((0.35, door_y - 0.25, 0)), Vector((1.35, door_y, 0)), Vector((R.XP + 0.07, door_y, 0)),
           Vector((2.6, door_y + 0.28, 0)), Vector((3.55, 2.25, 0)), ex]
    back = [ex, Vector((3.45, 2.2, 0)), Vector((2.6, door_y + 0.25, 0)), Vector((R.XP + 0.07, door_y, 0)), Vector((1.1, door_y + 0.12, 0)),
            Vector((0.1, pd0.y + 0.08, 0)), pd0]
    r_out, r_back = people.path(out), people.path(back)
    hl, pl = people.heading(arm, look, lookf[0])
    M_look = people.carry(pl, hl, ex, Vector((0, 1, 0)))                       # facing the glass door
    look_dur = 6.0
    segs = [dict(src=slouch, f0=t0f, dur=2.4, at=Matrix.Identity(4)),
            dict(src=up, f0=upf[0], dur=(upf[1] - upf[0]) / FPS, at=M_up, blend=0.7),
            dict(src=walk, f0=walkf[0], dur=r_out[1] / speed, at=people.walk_along(arm, walk, walkf[0], speed, r_out), blend=0.8),
            dict(src=look, f0=lookf[0], dur=look_dur, at=M_look, blend=0.9),
            dict(src=walk, f0=walkf[0] + 12, dur=r_back[1] / speed, at=people.walk_along(arm, walk, walkf[0], speed, r_back), blend=0.9),
            dict(src=down, f0=downf[0], dur=(downf[1] - downf[0]) / FPS, at=M_down, blend=1.0),
            dict(src=slouch, f0=t0f, dur=2.6, at=Matrix.Identity(4), blend=1.2)]
    t = [0.0]
    for sg in segs: t.append(t[-1] + sg['dur'])
    saul = _head_of('saul')
    def overlay(tt, k, lt):
        if k == 0: _look(arm, saul, 0.4)
        elif k == 3: _look(arm, ex + Vector((0, 1.5, 1.55)), 0.4 * _smooth(lt / 1.0) * _smooth((look_dur - lt) / 1.0))
        elif k == 6: _look(arm, saul, 0.4 * _smooth((lt - 0.4) / 1.2))
    act = people.sequence(arm, slouch, 'jesse_enter', segs, overlay=overlay)
    for a in (up, walk, look, down): bpy.data.actions.remove(a)
    arm['enter_times'] = t
    arm['open_act'], arm['open_at'] = 'enter', round(t[4] - 1.2, 2)          # he turns from the glass door
    OPEN['jesse'] = ('enter', arm['open_at'])
    cine.log(f"jesse enter {t[-1]:.1f} s; out of the chair {t[2]:.1f}, at the door {t[3]:.1f}, back in {t[5]:.1f}; the room opens at {arm['open_at']}")
    return act


# ---------------------------------------------------------------- Walt: up and pointing at Saul
def _point(arm, listen):
    """Walt, about 15 seconds: he gets up out of the chair, and furious, jabs his finger at Saul across the desk (the
    angry talk's left hand going, the right arm bent and thrust, the index finger out), then sits down hard again."""
    FPS = people.FPS
    up, upf, _ = people.retarget(arm, 'm_sit_stand_up_chair_01', action_name='walt_src_up')
    rage, ragef, _ = people.retarget(arm, 'm_gestic_talk_angry_02', action_name='walt_src_rage')
    down, downf, _ = people.retarget(arm, 'm_sit_down_chair_01', action_name='walt_src_down')
    t0f = int(listen.frame_range[0])
    _h, p_s = people.heading(arm, listen, t0f); h_s = Vector(arm['fwd'])
    def ends(action, f, M):
        h, p = people.heading(arm, action, f)
        return (M.to_3x3() @ h).normalized(), M @ p
    hu, pu = people.heading(arm, up, upf[0]); M_up = people.carry(pu, hu, p_s, h_s)
    hu1, pu1 = ends(up, upf[1], M_up)
    hr, pr = people.heading(arm, rage, ragef[0]); M_rage = people.carry(pr, hr, pu1, hu1)
    rage_dur = min(6.5, (ragef[1] - ragef[0]) / FPS)
    hr1, pr1 = ends(rage, ragef[0] + int(rage_dur * FPS), M_rage)
    hd, pd = people.heading(arm, down, downf[1]); M_down = people.carry(pd, hd, p_s, h_s)
    hd0, pd0 = ends(down, downf[0], M_down)
    cine.log(f'walt point: the outburst ends {((pr1 - pd0) * Vector((1, 1, 0))).length * 100:.0f} cm from where he sits down')
    saul = _head_of('saul') + Vector((0, 0, 0.05))
    segs = [dict(src=listen, f0=t0f, dur=2.0, at=Matrix.Identity(4)),
            dict(src=up, f0=upf[0], dur=(upf[1] - upf[0]) / FPS, at=M_up, blend=0.6),
            dict(src=rage, f0=ragef[0], dur=rage_dur, at=M_rage, blend=0.6),
            dict(src=down, f0=downf[0], dur=(downf[1] - downf[0]) / FPS, at=M_down, blend=0.9),
            dict(src=listen, f0=t0f, dur=2.4, at=Matrix.Identity(4), blend=1.1)]
    t = [0.0]
    for sg in segs: t.append(t[-1] + sg['dur'])
    def overlay(tt, k, lt):
        if k == 1: _look(arm, saul, 0.6 * _smooth(lt / 1.0))
        elif k == 2:
            e = people.envelope(lt, rage_dur, 0.7, 1.0)
            beat = max(0.0, math.sin(2 * math.pi * 1.3 * lt)) ** 2                   # the jabs
            people.point_at(arm, 'R', saul, e, reach=0.45, jab=0.09 * beat, shape='point')
            _look(arm, saul, 0.85 * e + 0.6 * (1 - e))
        elif k == 3: _look(arm, saul, 0.6 * (1 - _smooth(lt / 2.0)))
        elif k == 4: _look(arm, saul, 0.8 * _smooth(lt / 1.2))
    act = people.sequence(arm, listen, 'walt_point', segs, overlay=overlay)
    for a in (up, rage, down): bpy.data.actions.remove(a)
    arm['point_times'] = t
    return act


# ---------------------------------------------------------------- Saul: the double finger guns
def _guns(arm, talk):
    """Saul, about 13 seconds: he pushes up out of his chair behind the desk, and grinning, levels both index fingers
    at the two of them (thumbs cocked), bouncing them three times; then drops back into his chair, talking."""
    FPS = people.FPS
    up, upf, _ = people.retarget(arm, 'm_sit_stand_up_chair_01', action_name='saul_src_up')
    stand, standf, _ = people.retarget(arm, 'm_gestic_talk_cool', action_name='saul_src_stand')
    down, downf, _ = people.retarget(arm, 'm_sit_down_chair_01', action_name='saul_src_down')
    t0f = int(talk.frame_range[0])
    _h, p_s = people.heading(arm, talk, t0f); h_s = Vector(arm['fwd'])
    def ends(action, f, M):
        h, p = people.heading(arm, action, f)
        return (M.to_3x3() @ h).normalized(), M @ p
    hu, pu = people.heading(arm, up, upf[0]); M_up = people.carry(pu, hu, p_s, h_s)
    hu1, pu1 = ends(up, upf[1], M_up)
    # the clip rises a long step forward of the chair (41 cm), into the desk: he is held back as he rises (to stand 20
    # cm before the seat, his belly clear of the desk's edge) and let forward again as he sits; behind the desk's
    # front the legs' overlap with the chair goes unseen
    back = max(0.0, (pu1 - p_s).dot(h_s) - 0.2)
    up_dur, down_dur = (upf[1] - upf[0]) / FPS, (downf[1] - downf[0]) / FPS
    M_up_f = lambda lt: Matrix.Translation(-h_s * back * _smooth(lt / up_dur)) @ M_up
    pu1 = pu1 - h_s * back
    cine.log(f'saul up: held back {back * 100:.0f} cm; he stands {(pu1 - p_s).dot(h_s) * 100:.0f} cm before the seat (the desk edge is {(R.CHAIRS["saul"][1] - (R.DESK.y + 0.48)) * 100:.0f} cm)')
    hs, ps = people.heading(arm, stand, standf[0]); M_stand = people.carry(ps, hs, pu1, hu1)
    guns_dur = 4.6
    hd, pd = people.heading(arm, down, downf[1]); M_down = people.carry(pd, hd, p_s, h_s)
    M_down_f = lambda lt: Matrix.Translation(-h_s * back * (1 - _smooth(lt / down_dur))) @ M_down
    at = _between() + Vector((0, 0, 0.1))
    segs = [dict(src=talk, f0=t0f, dur=2.0, at=Matrix.Identity(4)),
            dict(src=up, f0=upf[0], dur=up_dur, at=M_up_f, blend=0.6),
            dict(src=stand, f0=standf[0], dur=guns_dur, at=M_stand, blend=0.6),
            dict(src=down, f0=downf[0], dur=down_dur, at=M_down_f, blend=0.8),
            dict(src=talk, f0=t0f, dur=2.4, at=Matrix.Identity(4), blend=1.1)]
    t = [0.0]
    for sg in segs: t.append(t[-1] + sg['dur'])
    def overlay(tt, k, lt):
        if k == 1: _look(arm, at, 0.6)
        elif k == 2:
            e = people.envelope(lt, guns_dur, 0.6, 0.8)
            bounce = 0.07 * max(0.0, math.sin(2 * math.pi * 1.6 * max(lt - 0.6, 0.0))) * _smooth((3.4 - lt) / 0.4)   # three bounces
            pel, fwd, right, up_ = _frame_of(arm)
            people.bend(arm, 'Bip01 Spine1', right, -0.1 * e)                       # leaning into it
            for s, sd in (('L', -1), ('R', 1)):                                     # both arms out at them, nearly straight
                people.point_at(arm, s, at + right * sd * 0.12 + Vector((0, 0, 0.1 + bounce)), e, reach=0.5, jab=bounce * 0.6, shape='gun', drop=0.15, out=0.12)
            _look(arm, at, 0.8 * e)
            people.bend(arm, 'Bip01 Head', fwd, 0.12 * e)                            # the head cocked
        elif k == 4: _look(arm, _between(), 0.7 * _smooth(lt / 1.0))
    act = people.sequence(arm, talk, 'saul_guns', segs, overlay=overlay)
    for a in (up, stand, down): bpy.data.actions.remove(a)
    arm['guns_times'] = t
    return act


# ---------------------------------------------------------------- the cued reactions
def _heads(other, act):
    """Where someone's head is at every frame of an act."""
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1]); out = []
    for f in range(f0, f1 + 1):
        people.pose_at(other, act, f); out.append(people._world(other, other.pose.bones['Bip01 Head']).translation.copy())
    people.pose_at(other, act, f0)
    return out


def _base_for(arm, c, n, name):
    k = max(1, math.ceil(n / 300) + 1)
    return people.retarget(arm, c['base'], cycles=k, action_name=name)


def _huell_watch(arm, c, jesse, enter):
    """Huell through Jesse's trip (as long, played with it): on guard, his eyes go to Jesse as he comes out of the
    office past him, follow him to the street door and back, and let him go in."""
    heads = _heads(jesse, enter); n = len(heads) - 1
    base, frames, _ = _base_for(arm, c, n, 'huell_watch_base')
    me = R.HUELL[0] + Vector((0, 0, 1.7))
    def step(f_, t):
        _guard(arm, t, n / people.FPS, 1.0)
        i = min(int(round(t * people.FPS)), n); h = heads[i]
        near = _smooth((5.0 - (h - me).length) / 1.5) * _smooth((h.x - (R.XP - 0.6)) / 0.6)
        _look(arm, h, 0.85 * near)
    act = people.custom_act(arm, base, (frames[0], frames[0] + n), 'huell_watch', step, _all(arm))
    bpy.data.actions.remove(base)
    return act


def _hush(arm, c, drop, walt, point):
    """Saul through Walt's outburst (as long, played with it): he sits back from it, both palms up and out ("Guys,
    guys! Hey!"), his eyes on Walt; then back to the desk."""
    heads = _heads(walt, point); n = len(heads) - 1
    t_up, t_rage, t_down = list(walt['point_times'])[1:4]
    base, frames, _ = _base_for(arm, c, n, 'saul_hush_base')
    ov = _overlay('saul', drop)
    def step(f_, t):
        ov(arm, t, n / people.FPS, look=0.0)
        i = min(int(round(t * people.FPS)), n)
        e = _smooth((t - t_rage + 0.3) / 0.8) * (1 - _smooth((t - t_down - 0.6) / 1.0))
        pel, fwd, right, up = _frame_of(arm)
        for b, a in zip(SPINE, (0.05, 0.05, 0.03)): people.bend(arm, b, right, a * e)     # back from it
        for s, sd in (('L', -1), ('R', 1)):
            sh = people._world(arm, arm.pose.bones[f'Bip01 {s} UpperArm']).translation
            H = people._world(arm, arm.pose.bones[f'Bip01 {s} Hand']).translation.copy()
            tgt = H.lerp(sh + fwd * 0.3 + right * sd * 0.18 - up * 0.08, e)
            people.ik2(arm, s, tgt, tgt - up * 0.3 + right * sd * 0.3)
            people.palm_to(arm, s, fwd, 0.9 * e)
        _look(arm, heads[i], 0.85)
    act = people.custom_act(arm, base, (frames[0], frames[0] + n), 'saul_hush', step, _all(arm, fingers=True))
    bpy.data.actions.remove(base)
    return act


def _walt_watch(arm, c, drop, saul, guns):
    """Walt through Saul's finger guns (as long, played with it): his eyes follow Saul up out of the chair and back
    down; a slow shake of the head at the guns."""
    heads = _heads(saul, guns); n = len(heads) - 1
    t_up, t_stand, t_down = list(saul['guns_times'])[1:4]
    base, frames, _ = _base_for(arm, c, n, 'walt_watch_base')
    ov = _overlay('walt', drop)
    def step(f_, t):
        ov(arm, t, n / people.FPS, look=0.0)
        i = min(int(round(t * people.FPS)), n)
        _look(arm, heads[i], 0.85)
        e = _smooth((t - t_stand - 0.8) / 0.6) * (1 - _smooth((t - t_down + 0.2) / 0.6))
        pel, fwd, right, up = _frame_of(arm)
        people.bend(arm, 'Bip01 Head', up, 0.12 * e * math.sin(2 * math.pi * 1.1 * (t - t_stand)))
    act = people.custom_act(arm, base, (frames[0], frames[0] + n), 'walt_watch', step, _all(arm))
    bpy.data.actions.remove(base)
    return act


# ---------------------------------------------------------------- bake and export
def bake(sc, objs, phantoms, seated, args):
    """The room's light baked into atlases (the people out of it: every one of them leaves his place at some point,
    or stands); then room.glb, the people and room.json."""
    os.makedirs(WEB, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    for c, arm, mesh in seated: mesh.hide_render = True
    export, atlases = stages.bake(objs, R.RH, OUT, int(args.get('size', 2048)), int(args.get('samples', 320)))
    for c, arm, mesh in seated: mesh.hide_render = False
    cine.export_glb(export, os.path.join(WEB, 'room.glb'))
    meta = stages.room_meta(R.RH, atlases); meta.update(_capture_meta())
    meta['people'] = stages.export_people(seated, WEB, person_meta)
    stages.write_meta(WEB, meta)


def _capture_meta():
    """How to light the people as the bake lit the room (three.js: y up, z = -Blender y): the lamps, cans and round
    windows as small bright spheres, the shop window and its door as glowing panes facing into the waiting room."""
    bulbs = []
    for l in bpy.data.objects:
        if l.type != 'LIGHT' or l.data.type not in ('POINT', 'SPOT'): continue
        r = 0.03; e = l.data.energy * (0.5 if l.data.type == 'SPOT' else 1.0)
        bulbs.append({'x': round(l.location.x, 3), 'y': round(l.location.z, 3), 'z': round(-l.location.y, 3), 'r': r,
                      'L': round(e / (4 * math.pi * r ** 2) / 60, 2), 'color': [round(c, 3) for c in l.data.color]})
    x0, x1, s0, s1 = R.STORE; e0, e1, eh = R.ENTRY
    windows = [{'x': round((x0 + x1) / 2, 3), 'y': round((s0 + s1) / 2, 3), 'z': round(-(R.BACK + 0.05), 3), 'w': round(x1 - x0, 3), 'h': round(s1 - s0, 3),
                'L': 2.4, 'color': list(R.SUN), 'ry': 0.0},
               {'x': round((e0 + e1) / 2, 3), 'y': round(eh / 2, 3), 'z': round(-(R.BACK + 0.05), 3), 'w': round(e1 - e0, 3), 'h': round(eh, 3),
                'L': 2.0, 'color': list(R.SUN), 'ry': 0.0}]
    return {'capture': {'ceiling': [0.62, 0.6, 0.55], 'walls': [0.3, 0.3, 0.2], 'emitters': bulbs, 'windows': windows,
                        'at': [[-1.4, 1.2, -1.6], [3.2, 1.3, -1.8]]}}


def person_meta(c):
    """The acts in a person's file, the looping one first, how long it lasts and how often each idle comes up; an act
    that cues another person's names it; the act the room opens on, and how far into it."""
    work, lo, hi = c['work']
    acts = [{'name': work, 'loop': True, 'min': lo, 'max': hi}]
    for k, (clip, w) in c['idles'].items():
        if k not in c['acts']: continue
        a = {'name': k, 'w': w}
        if k in c.get('cue', {}): a['cue'] = c['cue'][k]
        if FIRST.get(c['who']) == k: a['first'] = True
        if OPEN.get(c['who'], (None,))[0] == k: a['at'] = OPEN[c['who']][1]
        acts.append(a)
    return {'who': c['who'], 'file': f"{c['who']}.glb", 'acts': acts}


def people_stage(sc, cams, seated, args):
    """Re-export only the people (their glTF files and their part of room.json); the baked room stays as it is. Then a
    look at each of them in the room (Cycles)."""
    stages.update_meta(WEB, people=stages.export_people(seated, WEB, person_meta), **_capture_meta())
    for c, arm, mesh in seated: people.pose_at(arm, c['acts'][c['work'][0]], 60)
    for which in str(args.get('cams', 'saul,walt,jesse')).split(','):
        preview(sc, cams, which, int(args.get('samples', 64)), os.path.join(OUT, f'people_{which}.png'), size=(900, 900))
