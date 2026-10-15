# The Sopranos: assemble Dr. Melfi's office and the waiting room, seat Tony and Melfi across the glass table; Tony's
# walk-out (up from the chair, shouting, out of the door to the statue and back) is one long act, and Melfi's
# reaction to it another, played together; then preview, bake and export.
import math, os
import bpy
from mathutils import Vector, Matrix, Quaternion
import cine, people, stages
from stages import camera
import rooms.the_sopranos as R

ROOM = 'the-sopranos'
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
    R.windows(M, static)
    top = R.niche(M, static); R.bookcase(M, static); R.diplomas(M, static)
    R.chaise(M, static); R.melfi_chair(M, static); R.tony_chair(M, static)
    R.glass_table(M, static); R.rug(M, static)
    bulb = R.desk(M, static)
    wait_bulbs = R.waiting(M, static)
    stand = R.statue_plinth(M, static)
    RIG['lights'] = R.lights(top, bulb, wait_bulbs)
    _tidy()
    seated = [] if args.get('nocast') else cast(crowd, args)
    SEATED[:] = seated
    _statue(static, M, stand)
    objs = [o for o in static.objects if o.type == 'MESH']
    cine.bake_ready(objs)
    R.section(objs, M)
    for o in objs:
        if not o.data.uv_layers: cine.world_uv(o, 1.0)
        elif 'UVMap' not in o.data.uv_layers: o.data.uv_layers[0].name = 'UVMap'
    for o in objs:   # glass the web draws itself (opaque, reflective: a transparent one would vanish in the case)
        if o.name.startswith('stable') and o.name.endswith('_glass'): o['role'] = 'glass'
    for k in ('glass',):
        p = M[k].node_tree.nodes['Principled BSDF']; p.inputs['Transmission Weight'].default_value = 1.0; p.inputs['IOR'].default_value = 1.5
    objs = _merge(objs)
    for o in phantom.objects: cine.bake_ready([o]); cine.world_uv(o, 1.0); cine.phantom(o)
    cine.check_module(objs)
    c = R.C
    cams = {'case': camera('cam_case', (11.14, -18.16, 7.95), (-2.30, -1.49, 0.63), 32),
            'close': camera('cam_close', (5.0, -5.6, 3.4), (-0.6, 0.6, 0.9), 30),
            'film': camera('cam_film', tuple(R.on(R.th(270), 3.0, 1.2)), tuple(R.on(R.th(90), 2.6, 1.05)), 50),
            'door': camera('cam_door', tuple(R.on(R.DOOR[0], 2.9, 1.45)), tuple(R.on(R.th(180), 2.8, 1.1)), 48),
            'wait': camera('cam_wait', (3.45, 0.2, 1.05), (3.5, 3.4, 1.0), 46),
            'top': camera('cam_top', (0.0, -0.3, 14.0), (0.0, 0.0, 0.0), 34),
            'tony': _person_cam('tony', 35), 'melfi': _person_cam('melfi', -35),
            'tony_side': _person_cam('tony', 95), 'melfi_side': _person_cam('melfi', -95)}
    return sc, M, objs, list(phantom.objects), seated, cams


def _person_cam(who, turn, dist=2.3):
    """A look at one of them, seated: from `turn` degrees off their facing, 2.3 m away."""
    p, f = R.chair_at(who); d = Matrix.Rotation(math.radians(turn), 3, 'Z') @ f
    return camera(f'cam_{who}_{turn}', tuple(p + d * dist + Vector((0, 0, 1.25))), tuple(p + Vector((0, 0, 0.72))), 36)


def _tidy():
    """Imported props come under helper empties: keep their children where they are and drop the empties."""
    bpy.context.view_layer.update()
    for o in [o for o in bpy.data.objects if o.type == 'EMPTY']:
        for ch in o.children:
            mw = ch.matrix_world.copy(); ch.parent = None; ch.matrix_world = mw
        bpy.data.objects.remove(o, do_unlink=True)


KEEP = ('drum_', 'solid_', 'back_wall', 'wait_', 'kerb', 'floor', 'subfloor')   # names that carry rules (sections, cut tops)


def _merge(objs):
    """Join the many small pieces, one object per atlas and material: fewer meshes to draw."""
    groups = {}
    for o in objs:
        if o.get('role') or not o.get('lm') or len(o.material_slots) != 1 or o.name.startswith(KEEP): continue
        groups.setdefault((o['lm'], o.material_slots[0].material.name), []).append(o)
    # the drum's panels are many too: join them per material, keeping a name the section rule knows
    for o in objs:
        if o.name.startswith(('drum_panel', 'wait_panel', 'wait_left')) and len(o.material_slots) == 1:
            groups.setdefault(('arch', 'drum_' + o.material_slots[0].material.name), []).append(o)
    out = [o for o in objs if not any(o in g for g in groups.values())]
    for (lm, mat), g in groups.items():
        if len(g) == 1: out += g; continue
        bpy.ops.object.select_all(action='DESELECT')
        for o in g: o.select_set(True)
        bpy.context.view_layer.objects.active = g[0]
        bpy.ops.object.join()
        j = bpy.context.view_layer.objects.active; j.name = mat if mat.startswith('drum_') else f'{lm}_{mat}'; j['lm'] = lm
        out.append(j)
    cine.log(f'merged {len(objs)} meshes into {len(out)}')
    return out


def _statue(col, M, top):
    """The green-bronze nude on her pedestal: a body cast from a Rocketbox figure in a standing pose, every surface
    patina, at about half life size."""
    arm, mesh = people.load_avatar('Female_Adult_07', collection=col)
    k = [i for i, s in enumerate(mesh.material_slots) if s.material and 'opacity' in s.material.name]
    if k:   # the hair cards go: the cast hair is the scalp's own shape
        import bmesh
        bm = bmesh.new(); bm.from_mesh(mesh.data)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in k], context='FACES'); bm.to_mesh(mesh.data); bm.free()
    act, frames, _ = people.retarget(arm, 'f_idle_neutral_02', action_name='statue_pose')
    people.pose_at(arm, act, frames[0] + 40)
    people.face(arm, Vector((0, 1, 0)))                       # she faces the armchair, her back to the room
    bpy.context.view_layer.update()
    s = 0.5
    deps = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(mesh.evaluated_get(deps))
    ob = bpy.data.objects.new('statue', me); col.objects.link(ob)
    ob.matrix_world = mesh.matrix_world.copy()
    me.materials.clear(); me.materials.append(M['patina'])
    for p in me.polygons: p.material_index = 0
    lo = min((ob.matrix_world @ v.co).z for v in me.vertices)
    feet = Vector((arm.matrix_world.translation.x, arm.matrix_world.translation.y, lo))
    ob.matrix_world = Matrix.Translation(top) @ Matrix.Diagonal((s, s, s, 1)) @ Matrix.Translation(-feet) @ ob.matrix_world
    ob['lm'] = 'furn'
    for o in (arm, mesh): bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.actions.remove(act)
    cine.world_uv(ob, 0.6)


def preview(sc, cams, which, samples, path, size=(1440, 900)):
    """A Cycles render from one camera; pose=who:act:frame poses one person first; seq=who:act:s1;s2;... renders the
    act at each of those seconds (both of them posed: Melfi's watching goes with Tony's walk-out)."""
    if ARGS.get('seq'):
        who, act, ts = str(ARGS['seq']).split(':')
        pair = {'walkout': ('melfi', 'watch'), 'watch': ('tony', 'walkout')}.get(act)
        for t in ts.split(';'):
            for c, arm, mesh in SEATED:
                a = act if c['who'] == who else (pair[1] if pair and c['who'] == pair[0] else None)
                if a and a in c['acts']: people.pose_at(arm, c['acts'][a], int(c['acts'][a].frame_range[0]) + int(float(t) * people.FPS))
            stages.render(sc, cams[which], samples, path.replace('.png', f'_{act}_{float(t):04.1f}.png'), (960, 600), float(ARGS.get('exposure', 0.0)))
        return
    for spec in filter(None, str(ARGS.get('pose', '')).split(',')):
        who, act, f = spec.split(':')
        for c, arm, mesh in SEATED:
            if c['who'] == who and act in c['acts']: people.pose_at(arm, c['acts'][act], int(c['acts'][act].frame_range[0]) + int(f))
    stages.render(sc, cams[which], samples, path, size, float(ARGS.get('exposure', 0.0)))


# ---------------------------------------------------------------- the cast
# "Denial, Anger, Acceptance" (season one): Tony sunk in the olive chair, an ankle on his knee, talking with his
# hands; Melfi upright across from him, legs crossed, hands clasped, listening. Each has a looping act (`work`) and
# idles; Tony's walk-out cues Melfi's reaction, so the two play together.
def _tex(who, prefix, *names):
    return {f'{prefix}_{n}.tga': f'{who}/{prefix}_{n}.png' for n in names}


CAST = [
    dict(who='tony', avatar='Male_Adult_14', shape='heavy', height=1.83, base='m_sit_chair_breathe_01', work=('talk', 8, 16), talk='m_gestic_talk_relaxed_01',
         idles={'walkout': (None, 2.2), 'nervous': ('m_sit_chair_idle_nervous_01', 0.5), 'face': ('m_sit_chair_idle_touch_face', 0.45),
                'think': ('m_sit_chair_gestic_thoughtful', 0.45), 'shrug': ('m_sit_chair_gestic_shrug_01', 0.5)},
         cue={'walkout': {'melfi': 'watch'}}, roam=('walkout',),
         tex=_tex('tony', 'm012', 'head_color', 'body_color', 'body_normal')),
    dict(who='melfi', avatar='Business_Female_02', shape='lean', shape_k=1.6, legs='slim_legs', height=1.65, base='f_sit_chair_breathe_01', work=('listen', 8, 18),
         talk='f_gestic_talk_neutral_01',
         idles={'talk': (None, 1.2), 'think': ('f_sit_chair_gestic_thoughtful', 0.6), 'glasses': ('f_sit_chair_idle_touch_face', 0.6),
                'hair': ('f_sit_chair_idle_touch_hair', 0.4), 'watch': (None, 0.0)},
         tex=_tex('melfi', 'f015', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
]
FIRST = {'tony': 'walkout'}   # the first break from the session: he storms out soon after the room comes up
SPINE = ('Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2')
ARMS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('UpperArm', 'Forearm', 'Hand'))
LEGS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('Thigh', 'Calf', 'Foot'))
HEAD = ('Bip01 Neck', 'Bip01 Head')
ALL = ('Bip01 Pelvis',) + SPINE + ARMS + LEGS + HEAD   # and the root (its name is the avatar's: see _all)


def _all(arm):
    """Every bone an authored seated act keys: the root (it carries the drop into the chair), the body, the head."""
    return (next(b.name for b in arm.data.bones if b.parent is None),) + ALL


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


def _head_of(who):
    p, f = R.chair_at(who)
    return Vector((p.x, p.y, 1.12 if who == 'tony' else 1.08)) + f * 0.05


def _seated_frame(arm):
    """The body frame from the pelvis and the stored facing (not from the feet, which the legs' IK moves)."""
    pel = people._world(arm, arm.pose.bones['Bip01 Pelvis']).translation.copy()
    fwd = Vector(arm['fwd']); up = Vector((0, 0, 1)); right = fwd.cross(up).normalized()
    return pel, fwd, right, up


def _legs_tony(arm, w=1.0):
    """Tony's figure four: the left foot planted forward, the right ankle up on the left knee, the right knee out."""
    if w <= 0: return
    pel, fwd, right, up = _seated_frame(arm)
    def bone(n): return people._world(arm, arm.pose.bones[n]).translation.copy()
    LA0, RA0 = bone('Bip01 L Foot'), bone('Bip01 R Foot')
    la = pel + fwd * 0.5 - right * 0.13; la.z = 0.1
    people.ik_leg(arm, 'L', LA0.lerp(la, w), la + fwd * 0.6 + up * 0.3 - right * 0.1)
    lk = bone('Bip01 L Calf')
    ra = lk + up * 0.1 + right * 0.03 - fwd * 0.02
    people.ik_leg(arm, 'R', RA0.lerp(ra, w), pel + right * 0.6 + fwd * 0.35 + up * 0.25, keep_foot=False)
    people.bend(arm, 'Bip01 R Foot', fwd, -0.4 * w)


def _plant_legs(arm, w):
    """Both feet down on the floor before the chair, a little apart (out of a crossed sitting, to get up)."""
    if w <= 0: return
    pel, fwd, right, up = _seated_frame(arm)
    for s, sd in (('L', -1), ('R', 1)):
        A0 = people._world(arm, arm.pose.bones[f'Bip01 {s} Foot']).translation.copy()
        tgt = pel + fwd * 0.42 + right * sd * 0.14; tgt.z = 0.1
        people.ik_leg(arm, s, A0.lerp(tgt, w), tgt + fwd * 0.6 + up * 0.4 + right * sd * 0.1, keep_foot=False)
        F = people._world(arm, arm.pose.bones[f'Bip01 {s} Foot'])
        # turn the foot back toward flat as it lands
        toe = people._world(arm, arm.pose.bones[f'Bip01 {s} Toe0']).translation - F.translation
        want = (fwd * 0.8 - up * 0.25).normalized()
        q = toe.normalized().rotation_difference(want)
        people._set_world(arm, arm.pose.bones[f'Bip01 {s} Foot'], Matrix.Translation(F.translation) @ Quaternion().slerp(q, w).to_matrix().to_4x4() @ Matrix.Translation(-F.translation) @ F)


def _legs_melfi(arm, w=1.0):
    """Melfi's crossed legs: the left foot planted a little forward, the right leg over the left knee, its foot
    pointed down along the left shin."""
    if w <= 0: return
    pel, fwd, right, up = _seated_frame(arm)
    def bone(n): return people._world(arm, arm.pose.bones[n]).translation.copy()
    LA0, RA0 = bone('Bip01 L Foot'), bone('Bip01 R Foot')
    la = pel + fwd * 0.44 - right * 0.04; la.z = 0.11
    people.ik_leg(arm, 'L', LA0.lerp(la, w), la + fwd * 0.6 + up * 0.4)
    lk = bone('Bip01 L Calf')
    ra = lk + fwd * 0.2 - up * 0.3 - right * 0.06
    ra.z = max(ra.z, 0.16)
    people.ik_leg(arm, 'R', RA0.lerp(ra, w), lk + up * 0.6 + fwd * 0.2 - right * 0.05, keep_foot=False)
    people.bend(arm, 'Bip01 R Foot', right, -0.5 * w)


def _seat_overlay(who, drop, look=0.7, legs=1.0, clasp=0.0, nod=0.0):
    """What every seated act of theirs shares: lowered into the lower chair, the legs as they sit them, the head
    toward the other; Melfi's hands clasped over her knee (clasp)."""
    other = _head_of('melfi' if who == 'tony' else 'tony')
    def apply(arm, t, T, wl=1.0):
        people.shift_root(arm, (0, 0, -drop))
        (_legs_tony if who == 'tony' else _legs_melfi)(arm, legs * wl)
        if who == 'tony':
            pel, fwd, right, up = _seated_frame(arm)
            for b, a in zip(SPINE, (0.05, 0.05, 0.03)): people.bend(arm, b, right, a)          # sunk back
        if clasp > 0:
            pel, fwd, right, up = _seated_frame(arm)
            knee = people._world(arm, arm.pose.bones['Bip01 R Calf']).translation.copy()
            for s, sd in (('L', -1), ('R', 1)):
                H = people._world(arm, arm.pose.bones[f'Bip01 {s} Hand']).translation.copy()
                tgt = H.lerp(knee + up * 0.07 + right * sd * 0.045 - fwd * 0.04, clasp)
                people.ik2(arm, s, tgt, tgt + right * sd * 0.35 - up * 0.2 - fwd * 0.15)
                people.palm_to(arm, s, -right * sd, clasp * 0.8)
        if look > 0:
            k = max(1, round(T / 6.0)); n = nod * math.sin(2 * math.pi * k * t / T) if T > 0 else 0.0
            _look(arm, other + Vector((0, 0, n * 0.06)), look)
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


def cast(col, args):
    """Load, dress, shape and seat the two, and bake their acts (cached: retargets and IK take minutes)."""
    full = bool(args.get('full'))
    spec = {'cast': CAST, 'chairs': R.CHAIRS, 'seat': R.SEAT, 'door': R.DOOR, 'statue': list(R.STATUE), 'phi': R.PHI, 'full': full, 'v': 2}
    seated = stages.cast_cache(OUT, CAST, spec, lambda: _make_cast(col, full), col)
    for c, arm, mesh in seated: people.pose_at(arm, c['acts'][c['work'][0]], 30)
    return seated


def _height(arm, mesh):
    bpy.context.view_layer.update()
    return max((mesh.matrix_world @ v.co).z for v in mesh.data.vertices)


def _make_cast(col, full):
    seated, made = [], {}
    for c in CAST:
        arm, mesh = people.load_avatar(c['avatar'], textures={k: os.path.join(PEOPLE_TEX, v) for k, v in c['tex'].items()}, collection=col)
        mesh['person'] = c['who']; arm['person'] = c['who']
        if c.get('shape'): people.reshape(arm, mesh, c['shape'], c.get('shape_k', 1.0))
        if c.get('legs'): people.reshape(arm, mesh, c['legs'])
        s = c['height'] / _height(arm, mesh)
        arm.scale = arm.scale * s; arm.location = (arm.location.x, arm.location.y, arm.location.z * s)
        bpy.context.view_layer.update()
        p, f = R.chair_at(c['who'])
        people.face(arm, f); arm.location = (p.x, p.y, arm.location.z)
        bpy.context.view_layer.update()
        arm['fwd'] = list(f)
        base, frames, _ = people.retarget(arm, c['base'], cycles=2, action_name=f"{c['who']}_base")
        _seat(c, arm, base, frames)
        T = (frames[1] - frames[0]) / people.FPS
        drop = 0.52 - R.SEAT[c['who']]
        acts = {}; who = c['who']
        talk, tf, _ = people.retarget(arm, c['talk'], action_name=f'{who}_talk_src')
        k = max(1, round((frames[1] - frames[0]) / (tf[1] - tf[0])))
        if k > 1: bpy.data.actions.remove(talk); talk = people.retarget(arm, c['talk'], cycles=k, action_name=f'{who}_talk_src')[0]
        layered = people.layer(base, talk, name=f'{who}_talk_layer'); bpy.data.actions.remove(talk)
        if who == 'tony':
            ov = _seat_overlay('tony', drop, look=0.75)
            acts['talk'] = people.custom_act(arm, layered, frames, 'tony_talk', lambda f_, t: ov(arm, t, T), _all(arm))
        else:
            ov = _seat_overlay('melfi', drop, look=0.8, clasp=1.0, nod=0.35)
            acts['listen'] = people.custom_act(arm, base, frames, 'melfi_listen', lambda f_, t: ov(arm, t, T), _all(arm))
            if full:
                tv = _seat_overlay('melfi', drop, look=0.6, clasp=0.0)
                acts['talk'] = people.custom_act(arm, layered, frames, 'melfi_talk', lambda f_, t: tv(arm, t, T), _all(arm))
        bpy.data.actions.remove(layered)
        if full:
            for name, (clip, _w) in c['idles'].items():
                if not clip or name in acts: continue
                src = people.anchor(arm, people.retarget(arm, clip, action_name=f'{who}_{name}_src')[0], base)
                fr = (int(src.frame_range[0]), int(src.frame_range[1])); Ti = (fr[1] - fr[0]) / people.FPS
                ov = _seat_overlay(who, drop, look=0.35, clasp=0.0)
                acts[name] = people.custom_act(arm, src, fr, f'{who}_{name}', lambda f_, t, ov=ov, Ti=Ti: ov(arm, t, Ti), _all(arm))
                bpy.data.actions.remove(src)
        c['acts'] = acts; made[who] = (c, arm, mesh, base, frames, drop)
        seated.append((c, arm, mesh))
    if full:
        tc, tarm, tmesh, tbase, tframes, tdrop = made['tony']
        tc['acts']['walkout'] = _walkout(tarm, tbase, tc['acts']['talk'], tdrop)
        mc, marm, mmesh, mbase, mframes, mdrop = made['melfi']
        mc['acts']['watch'] = _watch(marm, mc, mdrop, tarm, tc['acts']['walkout'])
    for c, arm, mesh in seated:
        for a in c['acts'].values(): people.freeze(a)
        base = made[c['who']][3]
        if base not in c['acts'].values(): bpy.data.actions.remove(base)
        people.pose_at(arm, c['acts'][c['work'][0]], 30)
    return seated


# ---------------------------------------------------------------- the walk-out
def _path(pts):
    """A smooth path through points (Catmull-Rom): returns (point at s metres, tangent at s, length)."""
    P = [Vector((p[0], p[1], 0)) for p in pts]; P = [P[0]] + P + [P[-1]]
    samples = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(24):
            t = k / 24; t2, t3 = t * t, t * t * t
            samples.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    samples.append(P[-2])
    acc = [0.0]
    for a, b in zip(samples, samples[1:]): acc.append(acc[-1] + (b - a).length)
    L = acc[-1]
    def at(s):
        s = min(max(s, 0.0), L)
        i = next((i for i in range(1, len(acc)) if acc[i] >= s), len(acc) - 1)
        w = (s - acc[i - 1]) / max(acc[i] - acc[i - 1], 1e-6)
        p = samples[i - 1].lerp(samples[i], w)
        j0, j1 = max(i - 3, 0), min(i + 2, len(samples) - 1)
        tng = (samples[j1] - samples[j0]); tng = tng.normalized() if tng.length > 1e-6 else Vector((1, 0, 0))
        return p, tng
    return at, L


def _walkout(arm, base, talk, drop):
    """Tony's walk-out, about 40 seconds: heated in the chair; he springs up and shouts at her, jabbing a finger; turns
    and strides out past his chair, through the door into the waiting room, where he stands fuming before the statue;
    then comes back, turns, and drops into the chair again."""
    FPS = people.FPS
    up, upf, _ = people.retarget(arm, 'm_sit_stand_up_chair_01', action_name='tony_src_up')
    rage, ragef, _ = people.retarget(arm, 'm_gestic_talk_angry_01', action_name='tony_src_rage')
    walk, walkf, speed = people.retarget(arm, 'm_walk_fast_01', inplace=True, cycles=6, action_name='tony_src_walk')
    fume, fumef, _ = people.retarget(arm, 'm_idle_angry_02', cycles=2, action_name='tony_src_fume')
    down, downf, _ = people.retarget(arm, 'm_sit_down_chair_01', action_name='tony_src_down')
    cine.log(f'walk speed {speed:.2f} m/s; clips: up {(upf[1] - upf[0]) / FPS:.1f}s rage {(ragef[1] - ragef[0]) / FPS:.1f}s down {(downf[1] - downf[0]) / FPS:.1f}s')
    t0f = int(talk.frame_range[0])
    h_s, p_s = people.heading(arm, talk, t0f)                  # seated: where the act starts and ends
    h_s = Vector(arm['fwd'])
    melfi = _head_of('melfi'); statue = Vector((R.STATUE.x, R.STATUE.y, 1.45))

    def ends(action, f, M):
        h, p = people.heading(arm, action, f)
        return (M.to_3x3() @ h).normalized(), M @ p
    # up: its first moment over the seated pelvis, facing as he sits
    hu, pu = people.heading(arm, up, upf[0])
    M_up = people.carry(pu, hu, p_s, h_s)
    hu1, pu1 = ends(up, upf[1], M_up)
    # the outburst from where he stands
    hr, pr = people.heading(arm, rage, ragef[0])
    M_rage = people.carry(pr, hr, pu1, hu1)
    rage_dur = min(7.5, (ragef[1] - ragef[0]) / FPS)
    hr1, pr1 = ends(rage, ragef[0] + int(rage_dur * FPS), M_rage)
    # down: its last moment over the seated pelvis; its first is where the walk back must end
    hd, pd = people.heading(arm, down, downf[1])
    M_down = people.carry(pd, hd, p_s, h_s)
    hd0, pd0 = ends(down, downf[0], M_down)
    door = R.on(R.DOOR[0], R.R); door_in = R.on(R.DOOR[0], R.R - 0.6); door_out = R.on(R.DOOR[0], R.R + 0.45)
    stop = Vector((R.STATUE.x - 0.28, R.STATUE.y - 0.85, 0))
    chair, f = R.chair_at('tony'); side = Vector((-f.y, f.x, 0))   # the chair's left, seen from the chair: toward the door
    out = [pr1, pr1 - f * 0.25 + side * 0.45, chair + side * 0.75 - f * 0.1, door_in, door, door_out, stop]
    back = [stop, door_out, door, door_in, chair + side * 0.8 - f * 0.3, pd0]
    path_out, L_out = _path(out); path_back, L_back = _path(back)
    hw, pw = people.heading(arm, walk, walkf[0])
    def along(path, L):
        def M(lt):
            p, t = path(lt * speed)
            return people.carry(pw, hw, p, t)
        return M
    hf, pf = people.heading(arm, fume, fumef[0])
    M_fume = people.carry(pf, hf, stop, (statue - stop).normalized())
    segs = [dict(src=talk, f0=t0f, dur=3.2, at=Matrix.Identity(4)),
            dict(src=up, f0=upf[0], dur=(upf[1] - upf[0]) / FPS, at=M_up, blend=0.7),
            dict(src=rage, f0=ragef[0], dur=rage_dur, at=M_rage, blend=0.6),
            dict(src=walk, f0=walkf[0], dur=L_out / speed, at=along(path_out, L_out), blend=0.8),
            dict(src=fume, f0=fumef[0], dur=7.0, at=M_fume, blend=0.8),
            dict(src=walk, f0=walkf[0] + 15, dur=L_back / speed, at=along(path_back, L_back), blend=0.9),
            dict(src=down, f0=downf[0], dur=(downf[1] - downf[0]) / FPS, at=M_down, blend=0.9),
            dict(src=talk, f0=t0f, dur=2.8, at=Matrix.Identity(4), blend=1.2)]
    t_rage = segs[0]['dur'] + segs[1]['dur']
    t_out = t_rage + segs[2]['dur']; t_fume = t_out + segs[3]['dur']; t_back = t_fume + segs[4]['dur']
    t_down = t_back + segs[5]['dur']
    def overlay(t, k, lt):
        if k == 0:                                                                    # the legs uncross before he rises
            _plant_legs(arm, _smooth((lt - 1.3) / 1.5)); _look(arm, melfi, 0.3)
        elif k == 7: _look(arm, melfi, 0.3 * _smooth((lt - 0.5) / 1.5))
        elif k == 2:                                                                  # the finger jabbed at her
            T = segs[2]['dur']; e = people.envelope(lt, T, 0.8, 1.2)
            sh = people._world(arm, arm.pose.bones['Bip01 R UpperArm']).translation.copy()
            d = (melfi - sh).normalized(); jab = 0.06 * max(0.0, math.sin(2 * math.pi * 1.4 * lt)) ** 2
            tgt = people._world(arm, arm.pose.bones['Bip01 R Hand']).translation.lerp(sh + d * (0.5 + jab), e)
            people.ik2(arm, 'R', tgt, tgt - Vector((0, 0, 0.4)) + d.cross(Vector((0, 0, 1))) * 0.2)
            _look(arm, melfi, 0.8 * e)
        elif k == 3: _look(arm, door_out + Vector((0, 0, 1.6)), 0.3)
        elif k == 4:
            T = segs[4]['dur']
            _look(arm, statue, 0.7 * _smooth((lt - 1.0) / 1.5) * _smooth((T - lt - 0.8) / 1.0))
        elif k == 6: _look(arm, melfi, 0.4 * _smooth((lt - 0.5) / 1.0))
    act = people.sequence(arm, talk, 'tony_walkout', segs, overlay=overlay)
    for a in (up, rage, walk, fume, down): bpy.data.actions.remove(a)
    arm['walkout_times'] = [t_rage, t_out, t_fume, t_back, t_down]
    return act


def _watch(arm, c, drop, tony, walkout):
    """Melfi through Tony's walk-out (the same length, played with it): composed, her hands clasped; she follows him
    as he rises and shouts and goes, looks to the door a while after he has gone, lowers her eyes, and looks up as he
    comes back in and sits."""
    FPS = people.FPS; f0, f1 = int(walkout.frame_range[0]), int(walkout.frame_range[1]); n = f1 - f0
    heads = []
    for f in range(f0, f1 + 1):
        people.pose_at(tony, walkout, f); heads.append(people._world(tony, tony.pose.bones['Bip01 Head']).translation.copy())
    people.pose_at(tony, walkout, f0)
    t_rage, t_out, t_fume, t_back, t_down = list(tony['walkout_times'])
    door = R.on(R.DOOR[0], R.R - 0.2, 1.5)
    k = max(1, math.ceil(n / 300) + 1)
    base, frames, _ = people.retarget(arm, c['base'], cycles=k, action_name='melfi_watch_base')
    ov = _seat_overlay('melfi', drop, look=0.0, clasp=1.0)
    def step(f_, t):
        ov(arm, t, n / FPS)
        i = min(int(round(t * FPS)), n); h = heads[i]
        gone = _smooth((t - (t_fume + 1.0)) / 1.5) * (1 - _smooth((t - (t_back + 1.0)) / 1.2))   # he is out of the room
        down_eyes = _smooth((t - (t_fume + 3.5)) / 1.5) * (1 - _smooth((t - (t_back - 0.5)) / 1.0))
        at = h.lerp(door, gone).lerp(Vector((h.x, h.y, 0.3)).lerp(arm.matrix_world.translation, 0.6), down_eyes * 0.6)
        _look(arm, at, 0.85)
        if t_rage < t < t_out:                                  # she holds still, a little back from him
            pel, fwd, right, up = _seated_frame(arm)
            people.bend(arm, 'Bip01 Spine2', right, 0.04 * people.envelope(t - t_rage, t_out - t_rage, 0.6, 1.0))
    act = people.custom_act(arm, base, (frames[0], frames[0] + n), 'melfi_watch', step, _all(arm))
    bpy.data.actions.remove(base)
    return act


# ---------------------------------------------------------------- bake and export
def bake(sc, objs, phantoms, seated, args):
    """The room's light baked into atlases (Tony, who leaves his chair, out of it); then room.glb, the people and
    room.json."""
    os.makedirs(WEB, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    for c, arm, mesh in seated:
        if c['who'] == 'tony': mesh.hide_render = True
    export, atlases = stages.bake(objs, R.RH, OUT, int(args.get('size', 2048)), int(args.get('samples', 320)))   # the walls stop at the soffit
    for c, arm, mesh in seated: mesh.hide_render = False
    cine.export_glb(export, os.path.join(WEB, 'room.glb'))
    meta = stages.room_meta(R.RH, atlases); meta.update(_capture_meta())
    meta['people'] = stages.export_people(seated, WEB, person_meta)
    stages.write_meta(WEB, meta)


def _capture_meta():
    """How to light the people as the bake lit the room (three.js: y up, z = -Blender y): the lamps and downlights as
    small bright spheres, the windows as glowing panes facing into their rooms."""
    bulbs = []
    for l in bpy.data.objects:
        if l.type != 'LIGHT' or l.data.type not in ('POINT', 'SPOT'): continue
        r = 0.03; e = l.data.energy * (0.5 if l.data.type == 'SPOT' else 1.0)
        bulbs.append({'x': round(l.location.x, 3), 'y': round(l.location.z, 3), 'z': round(-l.location.y, 3), 'r': r,
                      'L': round(e / (4 * math.pi * r ** 2) / 60, 2), 'color': [round(c, 3) for c in l.data.color]})
    windows = []
    for a, hw in (R.NWIN, R.WWIN):
        p = R.on(a, R.RO + 0.2); i = R.inward(a)
        windows.append({'x': round(p.x, 3), 'y': sum(R.WIN_Z) / 2, 'z': round(-p.y, 3), 'w': round(math.radians(2 * hw) * R.RO, 3), 'h': R.WIN_Z[1] - R.WIN_Z[0],
                        'L': 3.0, 'color': list(R.DAY), 'ry': round(math.atan2(i.x, -i.y), 4)})
    windows.append({'x': 3.5, 'y': sum(R.WIN_Z) / 2 - 0.05, 'z': -(R.D / 2 - 0.1), 'w': 1.55, 'h': 0.85, 'L': 3.0, 'color': list(R.DAY), 'ry': 0.0})
    c = R.C
    return {'capture': {'ceiling': [0.6, 0.58, 0.54], 'walls': [0.32, 0.2, 0.13], 'emitters': bulbs, 'windows': windows,
                        'at': [[round(c.x, 3), 1.2, round(-c.y, 3)], [3.5, 1.3, -1.0]]}}


def person_meta(c):
    """The acts in a person's file, the looping one first, how long it lasts and how often each idle comes up; an act
    that cues another person's names it (Tony's walk-out and Melfi's watching are played together)."""
    work, lo, hi = c['work']
    acts = [{'name': work, 'loop': True, 'min': lo, 'max': hi}]
    for k, (clip, w) in c['idles'].items():
        if k not in c['acts']: continue
        a = {'name': k, 'w': w}
        if k in c.get('cue', {}): a['cue'] = c['cue'][k]
        if FIRST.get(c['who']) == k: a['first'] = True
        acts.append(a)
    return {'who': c['who'], 'file': f"{c['who']}.glb", 'acts': acts}


def people_stage(sc, cams, seated, args):
    """Re-export only the people (their glTF files and their part of room.json); the baked room stays as it is.
    Then a look at each of them in the room (Cycles)."""
    stages.update_meta(WEB, people=stages.export_people(seated, WEB, person_meta), **_capture_meta())
    for c, arm, mesh in seated: people.pose_at(arm, c['acts'][c['work'][0]], 60)
    for which in str(args.get('cams', 'tony,melfi')).split(','):
        preview(sc, cams, which, int(args.get('samples', 64)), os.path.join(OUT, f'people_{which}.png'), size=(900, 900))
