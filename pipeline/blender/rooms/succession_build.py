# Succession: assemble the ballroom of the Roys' hunting lodge and the dinner of "Boar on the Floor"; then preview,
# bake and export.
import math, os, random
import bpy
from mathutils import Vector, Matrix
import cine, people, stages
from stages import camera
import rooms.succession as R

ROOM = 'succession'
OUT = os.path.join(cine.OUT, ROOM)
WEB = os.path.join(cine.ROOT, 'public', 'rooms', ROOM)
PEOPLE_TEX = os.path.join(cine.OUT, 'people')
ARGS = {}
SEATED = []
RIG = {'lights': []}
FIRST, OPEN = {}, {}                       # the act each person's room opens on; how far into it


def build(args):
    ARGS.clear(); ARGS.update(args)
    sc = cine.reset(int(args.get('samples', 256)))
    M = R.mats()
    static, phantom, crowd = cine.coll('static'), cine.coll('phantom'), cine.coll('people')
    # the cast first: their acts are posed frame by frame, and every pose re-evaluates the scene
    seated = [] if args.get('nocast') else cast(crowd, args)
    SEATED[:] = seated
    # the ballroom at its true size; UVs made there; then all of it shrunk into the module
    rnd = random.Random(2019)
    R.shell(M, static, phantom)
    R.windows(M, static)
    for k, y in enumerate(R.DOORS_L): R.door(f'door{k}', y, M, static)
    fire_pts, breast_bulbs = R.fireplace(M, static, rnd)
    wall_bulbs, stand_flames, lamp = R.wall_things(M, static, rnd)
    R.rug(M, static)
    R.table(M, static, rnd)
    flames = R.table_things(M, static, rnd)
    R.chairs_and_places(M, static, rnd)
    flames += R.near_things(M, static, rnd)
    R.floor_things(M, static, rnd)
    R.logan_plate(M, static)
    RIG['lights'] = R.lights(fire_pts, flames + stand_flames, breast_bulbs + wall_bulbs, lamp)
    _tidy()
    objs = [o for o in static.objects if o.type == 'MESH']; phantoms = [o for o in phantom.objects if o.type == 'MESH']
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
    cams = {'case': camera('cam_case', (2.6, -20.5, 7.2), (0.0, 0.2, 1.0), 30),
            'close': camera('cam_close', (2.6, -6.6, 2.7), (-0.6, 0.6, 0.9), 34),
            'front': camera('cam_front', (-0.4, -5.6, 1.3), (-0.8, 1.2, 0.85), 44),
            'fire': camera('cam_fire', (-1.2, -2.6, 1.0), (-4.3, 0.4, 0.55), 40),             # the hearth, the boars, the head of the table
            'table': camera('cam_table', (1.6, -2.4, 1.3), (-1.0, 0.5, 0.5), 40),
            'wall': camera('cam_wall', (-0.6, -2.0, 1.4), (-0.6, 3.6, 1.6), 50),              # the window wall, the trophies
            'left': camera('cam_left', (2.4, -0.4, 1.2), (-4.6, 0.3, 1.1), 50),               # down the room to the fireplace end
            'trophy': camera('cam_trophy', (-0.6, 1.2, 1.9), (-0.6, 3.7, 1.9), 30),             # the big cluster
            'diners': camera('cam_diners', (-1.2, -1.6, 1.15), (-1.9, 0.75, 0.75), 38),         # the far side, face on
            'head': camera('cam_head', (-1.6, -0.9, 1.0), (-2.75, 0.55, 0.75), 36),          # Logan at the head, Kendall
            'top': camera('cam_top', (0.0, 0.0, 15.0), (0.0, 0.1, 0.0), 36)}
    return sc, M, objs, list(phantom.objects), seated, cams


def _tidy():
    """Imported props come under helper empties: keep their children where they are and drop the empties."""
    bpy.context.view_layer.update()
    for o in [o for o in bpy.data.objects if o.type == 'EMPTY']:
        for ch in o.children:
            mw = ch.matrix_world.copy(); ch.parent = None; ch.matrix_world = mw
        bpy.data.objects.remove(o, do_unlink=True)


KEEP = ('solid_', 'left_wall', 'back_wall', 'kerb', 'floor', 'subfloor')   # names that carry rules


def _merge(objs):
    """Join the many small pieces, one object per atlas and material: fewer meshes to draw."""
    groups = {}
    for o in objs:
        if o.get('role') or len(o.material_slots) != 1 or o.name.startswith(KEEP): continue
        groups.setdefault(('live' if o.get('live') else o.get('lm', ''), o.material_slots[0].material.name), []).append(o)
    out = [o for o in objs if not any(o in g for g in groups.values())]
    for (lm, mat), g in groups.items():
        if len(g) == 1: out += g; continue
        bpy.ops.object.select_all(action='DESELECT')
        for o in g: o.select_set(True)
        bpy.context.view_layer.objects.active = g[0]
        bpy.ops.object.join()
        j = bpy.context.view_layer.objects.active; j.name = f'{lm}_{mat}' if lm else mat
        if lm and lm != 'live': j['lm'] = lm
        out.append(j)
    for o in out:                                       # the scans: no light map, lit live by the captured room
        if o.get('live'): del o['live']; o['role'] = 'mug'
    # the glass: one mesh for all of it
    glass = [o for o in out if o.get('role') == 'glass']
    if len(glass) > 1:
        bpy.ops.object.select_all(action='DESELECT')
        for o in glass: o.select_set(True)
        bpy.context.view_layer.objects.active = glass[0]; bpy.ops.object.join()
        j = bpy.context.view_layer.objects.active; j.name = 'crystal'; j['role'] = 'glass'
        out = [o for o in out if o not in glass] + [j]
    cine.log(f'merged {len(objs)} meshes into {len(out)}')
    return out


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
# The Roys and their people at dinner, true heights (the room shrinks them with itself), dressed after Michelle
# Matland's costumes for the episode; Rocketbox faces made up as the actors. Logan at the head; Kendall, Roman, Gerri
# and Frank down the far side; Tom, Greg and Karl on their knees before the hearth; a waiter at the window wall.
def _tex(who, prefix, *names):
    return {f'{prefix}_{n}.tga': f'{who}/{prefix}_{n}.png' for n in names}


CAST = [
    dict(who='logan', avatar='Male_Adult_03', shape=('heavy', 0.75), height=1.75, tex=_tex('logan', 'm004', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
    dict(who='kendall', avatar='Business_Male_06', shape=('lean', 1.0), height=1.76, tex=_tex('kendall', 'm025', 'head_color', 'body_color', 'body_normal')),
    dict(who='roman', avatar='Male_Adult_08', shape=('lean', 1.4), height=1.70, tex=_tex('roman', 'm014', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
    dict(who='gerri', avatar='Business_Female_02', shape=None, height=1.64, drop=('glasses',), tex=_tex('gerri', 'f015', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
    dict(who='frank', avatar='Business_Male_07', shape=('lean', 1.2), height=1.76, tex=_tex('frank', 'm018', 'head_color', 'body_color', 'body_normal')),
    dict(who='tom', avatar='Male_Adult_06', shape=('athletic', 0.6), height=1.91, tex=_tex('tom', 'm011', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
    dict(who='greg', avatar='Male_Adult_02', shape=('lean', 1.6), height=2.01, tex=_tex('greg', 'm003', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
    dict(who='karl', avatar='Male_Adult_13', shape=('heavy', 0.35), height=1.84, tex=_tex('karl', 'm010', 'head_color', 'body_color', 'body_normal')),
    dict(who='waiter', avatar='Business_Male_01', shape=('lean', 1.0), height=1.81, tex=_tex('waiter', 'm005', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
]
S = R.SCALE


def P(x, y, z=0.0):
    return Vector((x, y, z)) * S


SEATS = {'logan': (R.HEAD, (1.0, 0.0)),                                # (x, y) of the seat, the facing (true metres)
         'kendall': ((R.SEATS_X[0], R.YT + R.SIDE_Y), (0.0, -1.0)),
         'roman': ((R.SEATS_X[1], R.YT + R.SIDE_Y), (0.0, -1.0)),
         'gerri': ((R.SEATS_X[2], R.YT + R.SIDE_Y), (0.0, -1.0)),
         'frank': ((R.SEATS_X[3], R.YT + R.SIDE_Y), (0.0, -1.0))}
KNEEL = {'tom': ((-6.12, R.YF + 0.18), (1.0, 0.0)),                    # before the hearth, facing the table
         'greg': ((-6.2, R.YF + 0.92), (1.0, -0.22)),
         'karl': ((-6.06, R.YF - 0.6), (1.0, 0.25))}
SPOTS = {'waiter': ((0.55, 5.3), (0.0, -1.0))}
BASES = {'logan': 'm_sit_chair_breathe_01', 'kendall': 'm_sit_table_breathe_01', 'roman': 'm_sit_chair_breathe_01', 'gerri': 'f_sit_table_breathe_01',
         'frank': 'm_sit_table_breathe_01', 'tom': 'm_idle_breathe_01', 'greg': 'm_idle_breathe_02', 'karl': 'm_idle_breathe_03', 'waiter': 'm_idle_breathe_02'}
WORK = {'logan': ('sit', 14, 30), 'kendall': ('sit', 12, 26), 'roman': ('sit', 10, 22), 'gerri': ('sit', 12, 26), 'frank': ('sit', 12, 26),
        'tom': ('kneel', 10, 22), 'greg': ('kneel', 10, 22), 'karl': ('kneel', 12, 24), 'waiter': ('stand', 14, 30)}
IDLES = {'logan': {'scene': (None, 1.6), 'talk': ('m_gestic_talk_relaxed_01', 0.5)},
         'kendall': {'look': ('m_sit_table_idle_look_around', 0.5), 'think': ('m_sit_table_gestic_thoughtful', 0.4), 'shoulders': (None, 0.0)},
         'roman': {'phone': (None, 0.7), 'laugh': ('m_gestic_laugh_low', 0.5), 'watch': (None, 0.0)},
         'gerri': {'look': ('f_sit_table_idle_look_around', 0.5), 'think': ('f_sit_table_gestic_thoughtful', 0.4), 'hair': ('f_sit_table_idle_touch_hair', 0.3), 'watch': (None, 0.0)},
         'frank': {'nervous': ('m_sit_table_idle_nervous_01', 0.5), 'face': ('m_sit_table_idle_touch_face', 0.4), 'look': ('m_sit_table_idle_look_around', 0.4), 'watch': (None, 0.0)},
         'tom': {'oink': (None, 0.6), 'look': (None, 0.5), 'scramble': (None, 0.0)},
         'greg': {'oink': (None, 0.5), 'look': (None, 0.5), 'scramble': (None, 0.0)},
         'karl': {'oink': (None, 0.4), 'look': (None, 0.5), 'scramble': (None, 0.0)},
         'waiter': {'look': ('m_idle_look_around_01', 0.5), 'round': (None, 0.4), 'watch': (None, 0.0)}}
CUE = {'logan': {'scene': {'kendall': 'shoulders', 'roman': 'watch', 'gerri': 'watch', 'frank': 'watch', 'tom': 'scramble', 'greg': 'scramble',
                           'karl': 'scramble', 'waiter': 'watch'}}}
FIRST.update({'logan': 'scene'})
ROAM = {'logan': ('scene',), 'waiter': ('round',)}
HANDS = {'logan', 'kendall', 'roman', 'gerri', 'frank', 'tom', 'greg', 'karl', 'waiter'}
SPINE = ('Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2')
ARMS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('Clavicle', 'UpperArm', 'Forearm', 'Hand'))
LEGS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('Thigh', 'Calf', 'Foot'))
FINGERS = tuple(f'Bip01 {s} Finger{f}{j}' for s in 'LR' for f in '01234' for j in ('', '1', '2'))
ALL = ('Bip01 Pelvis',) + SPINE + ARMS + LEGS + ('Bip01 Neck', 'Bip01 Head')
PLATE = R.PLATE


def _all(arm, fingers=False):
    return (next(b.name for b in arm.data.bones if b.parent is None),) + ALL + (FINGERS if fingers else ())


def _smooth(x):
    x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)


def _flat(v):
    v = Vector((v.x, v.y, 0)); return v.normalized() if v.length > 1e-6 else Vector((0, -1, 0))


def _ends(arm, action, f, M):
    h, p = people.heading(arm, action, f)
    return (M.to_3x3() @ h).normalized(), M @ p


def _live(arm):
    """The body frame now: the pelvis, and the facing it carries (stored in the pelvis's own axes when placed)."""
    pb = arm.pose.bones['Bip01 Pelvis']; M = people._world(arm, pb)
    f = M.to_3x3() @ Vector(arm['pel_fwd']); f.z = 0; f.normalize()
    up = Vector((0, 0, 1)); return M.translation.copy(), f, f.cross(up).normalized(), up


def _look(arm, at, w):
    """Turn the head (and a little the neck) toward a point, by the fraction w."""
    if w <= 0: return
    H = people._world(arm, arm.pose.bones['Bip01 Head']).translation
    pel, f, right, up = _live(arm)
    d = (Vector(at) - H).normalized()
    yaw = math.atan2(d.dot(-right), d.dot(f)); pitch = math.asin(max(-1, min(1, d.z)))
    yaw = max(-1.2, min(1.2, yaw)); pitch = max(-0.7, min(0.6, pitch))
    people.bend(arm, 'Bip01 Neck', up, yaw * 0.35 * w); people.bend(arm, 'Bip01 Head', up, yaw * 0.65 * w)
    people.bend(arm, 'Bip01 Neck', right, pitch * 0.3 * w); people.bend(arm, 'Bip01 Head', right, pitch * 0.7 * w)


def _seat_of(who):
    (x, y), f = SEATS[who]; return P(x, y), Vector((*f, 0)).normalized()


def _head_of(who):
    """Where someone's head is in their loop (for looks)."""
    c = next(c for c in CAST if c['who'] == who); k = c['height'] / 1.75
    if who in SEATS: p, f = _seat_of(who); return p + Vector((0, 0, 1.2 * k * S)) + f * 0.05 * S
    if who in KNEEL: (x, y), f = KNEEL[who]; return P(x, y, 0.95 * k)
    (x, y), f = SPOTS[who]; return P(x, y, 1.65 * k)


def _samples(arm, action, bone='Bip01 Head'):
    f0, f1 = int(action.frame_range[0]), int(action.frame_range[1]); out = []
    for f in range(f0, f1 + 1):
        people.pose_at(arm, action, f); out.append(people._world(arm, arm.pose.bones[bone]).translation.copy())
    people.pose_at(arm, action, f0)
    return out


def _drop_material(mesh, key):
    """Drop the faces of an avatar's material whose name holds `key` (Gerri's glasses)."""
    import bmesh
    k = {i for i, sl in enumerate(mesh.material_slots) if sl.material and key in sl.material.name}
    bm = bmesh.new(); bm.from_mesh(mesh.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in k], context='FACES'); bm.to_mesh(mesh.data); bm.free(); mesh.data.update()


def make_person(c, col):
    """One of them, standing at the origin facing -y: the avatar, its build, its height."""
    tex = {k: os.path.join(PEOPLE_TEX, v) for k, v in c.get('tex', {}).items() if os.path.exists(os.path.join(PEOPLE_TEX, v))}
    arm, mesh = people.load_avatar(c['avatar'], textures=tex, collection=col)
    arm.animation_data_clear()                                  # the FBX's take keys the object's scale (0.01): a render would undo the height
    mesh['person'] = c['who']; arm['person'] = c['who']
    for key in c.get('drop', ()): _drop_material(mesh, key)
    if c.get('shape'): people.reshape(arm, mesh, *c['shape'])
    bpy.context.view_layer.update()
    top = max((mesh.matrix_world @ v.co).z for v in mesh.data.vertices)
    for ca in list(mesh.data.color_attributes): mesh.data.color_attributes.remove(ca)
    s = c['height'] / top
    arm.scale = arm.scale * s; arm.location = (arm.location.x, arm.location.y, arm.location.z * s)
    bpy.context.view_layer.update()
    return arm, mesh


def cast(col, args):
    """Load, dress, shape and place them, and bake their acts (cached: retargets and IK take minutes)."""
    full = bool(args.get('full'))
    spec = {'cast': CAST, 'seats': SEATS, 'kneel': KNEEL, 'spots': SPOTS, 'bases': BASES, 'work': WORK, 'idles': IDLES, 'cue': CUE, 'scale': S,
            'seat_z': R.SEAT_Z, 'table': [R.TX0, R.TX1, R.TW, R.TH, R.YT], 'plate': PLATE, 'at_boars': AT_BOARS, 'full': full, 'v': 3}
    for c in CAST:
        c['work'] = WORK[c['who']]; c['idles'] = IDLES[c['who']]; c['cue'] = CUE.get(c['who'], {}); c['roam'] = ROAM.get(c['who'], ())
    seated = stages.cast_cache(OUT, CAST, spec, lambda: _make_cast(col, full), col)
    for c, arm, mesh in seated:
        if 'open_act' in arm: OPEN[c['who']] = (arm['open_act'], float(arm['open_at']))
        if 'plate_grab' in arm: PLATE_HELD.update(grab=float(arm['plate_grab']), release=float(arm['plate_release']))
        people.pose_at(arm, c['acts'][c['work'][0]], int(c['acts'][c['work'][0]].frame_range[0]) + 30)
        for part, maps in MAPS.get(c['who'], {}).items(): _maps(mesh, part, maps)
    return seated


# grey maps laid on after the cast is made or loaded (the cache keeps the images by path)
MAPS = {'kendall': {'body': {'Roughness': 'kendall/m025_body_rough.png'}}}


def _maps(mesh, part, maps):
    """Grey maps on one of the avatar's materials ('body', 'head'): {'Metallic' | 'Roughness': image}."""
    for slot in mesh.material_slots:
        m = slot.material
        if not m or part not in m.name or 'opacity' in m.name: continue
        nt = m.node_tree; p = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        for inp, path in maps.items():
            if p.inputs[inp].links: continue
            t = nt.nodes.new('ShaderNodeTexImage'); t.image = cine.image(os.path.join(PEOPLE_TEX, path), colour=False)
            nt.links.new(t.outputs['Color'], p.inputs[inp])


PLATE_HELD = {}


def _place(c, arm):
    """Shrink a person with the room and set them at their seat or spot, facing their way; the base clip retargeted
    there (cycles 2: a perfect loop) and slid so its pelvis is over the place (a sitter's lowered onto the seat)."""
    who = c['who']
    arm.scale = arm.scale * S; arm.location = arm.location * S
    bpy.context.view_layer.update()
    if who in SEATS: (x, y), f = SEATS[who]
    elif who in KNEEL: (x, y), f = KNEEL[who]
    else: (x, y), f = SPOTS[who]
    f = Vector((*f, 0)).normalized()
    people.face(arm, f); arm.location = (x * S, y * S, arm.location.z); bpy.context.view_layer.update()
    arm['fwd'] = list(f)
    base, frames, _ = people.retarget(arm, BASES[who], cycles=2, action_name=f'{who}_base')
    people.pose_at(arm, base, frames[0])
    pel = people._world(arm, arm.pose.bones['Bip01 Pelvis']).translation
    want = P(x, y) + (f * 0.04 * S if who in SEATS else Vector())
    arm.location.x += want.x - pel.x; arm.location.y += want.y - pel.y
    bpy.context.view_layer.update()
    drop = 0.0
    if who in SEATS:                                       # the clip's pelvis over its own seat: lowered (or raised) onto this one
        people.pose_at(arm, base, frames[0])
        pz = people._world(arm, arm.pose.bones['Bip01 Pelvis']).translation.z
        k_ = c['height'] / 1.75
        drop = pz - (R.SEAT_Z * S + 0.09 * S * k_)
        cine.log(f'seat {who}: pelvis {pz / S:.3f} (true m), seat {R.SEAT_Z:.3f}, drop {drop / S:+.3f}')
    people.pose_at(arm, base, frames[0])
    arm['pel_fwd'] = list(people._world(arm, arm.pose.bones['Bip01 Pelvis']).to_3x3().inverted() @ f)
    return base, frames, drop


def _make_cast(col, full):
    seated, made = [], {}
    for c in CAST:
        arm, mesh = make_person(c, col)
        base, frames, drop = _place(c, arm)
        made[c['who']] = dict(c=c, arm=arm, mesh=mesh, base=base, frames=frames, drop=drop, k=S * c['height'] / 1.78)
        seated.append((c, arm, mesh))
    for m in made.values(): m['mesh'].hide_viewport = True
    acts = {k: {} for k in made}
    _logan_acts(made['logan'], acts['logan'], full)
    for who in ('kendall', 'gerri', 'frank'): _diner_acts(made[who], acts[who], full)
    _roman_acts(made['roman'], acts['roman'], full)
    for who in ('tom', 'greg', 'karl'): _boar_acts(made[who], acts[who], full)
    _waiter_acts(made['waiter'], acts['waiter'], full)
    if full: _scene(made, acts)
    for who, m in made.items():
        m['c']['acts'] = acts[who]
        for name, a in acts[who].items():
            if who not in HANDS: people.freeze(a)
        if m['base'] not in acts[who].values(): bpy.data.actions.remove(m['base'])
        people.pose_at(m['arm'], acts[who][m['c']['work'][0]], int(m['frames'][0]) + 30)
        m['mesh'].hide_viewport = False
    return seated


def _clip_act(m, acts, name, clip, step, fingers=True, layered=False):
    """An idle from a clip: anchored on the base, authored over by `step` (looks, a drop onto the seat). `layered`:
    the clip's arms and head over the seated base (a standing talk clip made a seated one)."""
    arm, base = m['arm'], m['base']; who = m['c']['who']
    if layered:
        top = people.retarget(arm, clip, action_name=f'{who}_{name}_top')[0]
        src = people.layer(base, top, name=f'{who}_{name}_src'); bpy.data.actions.remove(top)
        fr = m['frames']
    else:
        src = people.anchor(arm, people.retarget(arm, clip, action_name=f'{who}_{name}_src')[0], base)
        fr = (int(src.frame_range[0]), int(src.frame_range[1]))
    acts[name] = people.custom_act(arm, src, fr, f'{who}_{name}', step, _all(arm, fingers=fingers))
    bpy.data.actions.remove(src)


def _long_base(m, seconds, name):
    """The base clip run long enough for an act of `seconds` (a clip played past its end stands still)."""
    arm, c = m['arm'], m['c']; per = (m['frames'][1] - m['frames'][0]) / people.FPS / 2
    return people.retarget(arm, BASES[c['who']], cycles=max(2, math.ceil(seconds / per) + 1), action_name=f"{c['who']}_{name}_base")


# ---------------------------------------------------------------- sitting at the table
def _sit(arm, drop):
    people.shift_root(arm, (0, 0, -drop))


def _table_hands(arm, k, w=1.0, clasp=False, spread=0.11, reach=0.3):
    """Forearms on the table's edge, the hands on the top before the plate (clasped: the hands together, as Logan
    holds them while he listens)."""
    if w <= 0: return
    pel, fwd, right, up = _live(arm)
    z = R.TH * S + 0.025 * k
    for side, sd in (('L', -1), ('R', 1)):
        sh = people._world(arm, arm.pose.bones[f'Bip01 {side} UpperArm']).translation
        tgt = Vector((pel.x, pel.y, z)) + fwd * reach * k + right * sd * (0.025 if clasp else spread) * k
        H0 = people._world(arm, arm.pose.bones[f'Bip01 {side} Hand']).translation.copy()
        g = H0.lerp(tgt, w)
        people.ik2(arm, side, g, g - up * 0.35 * k + right * sd * 0.35 * k - fwd * 0.1 * k)
        people.palm_to(arm, side, (-up * 0.4 - right * sd * 0.6).normalized() if clasp else -up, 0.8 * w)


def _diner(arm, drop, k, look_at=None, lw=0.6, lean=0.08):
    _sit(arm, drop)
    pel, fwd, right, up = _live(arm)
    for b_, a in zip(SPINE, (lean * 0.5, lean * 0.3, lean * 0.2)): people.bend(arm, b_, right, -a)     # (negative: forward)
    if look_at is not None: _look(arm, look_at, lw)


def _logan_acts(m, acts, full):
    """Logan at the head of the table, heavy in the leather chair, his hands clasped on the table, his eyes going
    slowly down the table and back; idle: talking with his hands (a standing talk over the seated base)."""
    arm, base, frames, drop, k = m['arm'], m['base'], m['frames'], m['drop'], m['k']; T = (frames[1] - frames[0]) / people.FPS
    near, far = P(R.SEATS_X[3], R.YT + R.SIDE_Y, 1.2), P(R.SEATS_X[0], R.YT + R.SIDE_Y, 1.25)
    def sit(f, t):
        _diner(arm, drop, k, near.lerp(far, 0.5 + 0.5 * math.sin(2 * math.pi * t / T)), 0.7, lean=0.12)
        _table_hands(arm, k, clasp=True, reach=0.36)
    acts['sit'] = people.custom_act(arm, base, frames, 'logan_sit', sit, _all(arm, fingers=True)); m['steps'] = {'sit': sit}
    if not full: return
    _clip_act(m, acts, 'talk', IDLES['logan']['talk'][0], lambda f, t: _diner(arm, drop, k, far, 0.5, lean=0.1), layered=True)


def _diner_acts(m, acts, full):
    """Kendall, Gerri, Frank at the far side, forearms on the table, their eyes on Logan at the head; idles from their
    seated clips."""
    arm, base, frames, drop, k = m['arm'], m['base'], m['frames'], m['drop'], m['k']; who = m['c']['who']
    logan = _head_of('logan')
    sit = lambda f, t: (_diner(arm, drop, k, logan, 0.55), _table_hands(arm, k, w=0.6))
    acts['sit'] = people.custom_act(arm, base, frames, f'{who}_sit', sit, _all(arm, fingers=True)); m['steps'] = {'sit': sit}
    if not full: return
    for name, (clip, w) in IDLES[who].items():
        if clip: _clip_act(m, acts, name, clip, lambda f, t: _diner(arm, drop, k, logan, 0.25))


def _phone_hold(arm, k, w=1.0):
    """A phone held low in both hands over the lap, the screen up, the head bent to it."""
    pel, fwd, right, up = _live(arm)
    c = pel + fwd * 0.3 * k + up * 0.2 * k
    for side, sd in (('L', -1), ('R', 1)):
        H0 = people._world(arm, arm.pose.bones[f'Bip01 {side} Hand']).translation.copy(); g = H0.lerp(c + right * sd * 0.045 * k, w)
        people.ik2(arm, side, g, g - up * 0.3 * k + right * sd * 0.3 * k - fwd * 0.1 * k)
        people.palm_to(arm, side, (up * 0.6 - right * sd * 0.4).normalized(), 0.7 * w)
    people.bend(arm, 'Bip01 Neck', right, -0.25 * w); people.bend(arm, 'Bip01 Head', right, -0.3 * w)


def _roman_acts(m, acts, full):
    """Roman slouched back in his chair, an arm on the table, watching his father with a half smile; idles: his phone in
    his lap (he is filming under the table); a laugh."""
    arm, base, frames, drop, k = m['arm'], m['base'], m['frames'], m['drop'], m['k']
    logan = _head_of('logan')
    def sit(f, t):
        _sit(arm, drop); pel, fwd, right, up = _live(arm)
        for b_, a in zip(SPINE, (0.06, 0.04, 0.02)): people.bend(arm, b_, right, a)          # slouched back
        _look(arm, logan, 0.6)
        sh = people._world(arm, arm.pose.bones['Bip01 R UpperArm']).translation
        g = Vector((sh.x, sh.y, R.TH * S + 0.025 * k)) + fwd * 0.3 * k + right * 0.05 * k
        people.ik2(arm, 'R', g, g - up * 0.3 * k + right * 0.35 * k); people.palm_to(arm, 'R', -up, 0.8)
    acts['sit'] = people.custom_act(arm, base, frames, 'roman_sit', sit, _all(arm, fingers=True)); m['steps'] = {'sit': sit}
    if not full: return
    def phone(f, t):
        T = (frames[1] - frames[0]) / people.FPS
        _sit(arm, drop); _phone_hold(arm, k, people.envelope(t, T, 1.2, 1.2))
    acts['phone'] = people.custom_act(arm, base, frames, 'roman_phone', phone, _all(arm, fingers=True))
    _clip_act(m, acts, 'laugh', IDLES['roman']['laugh'][0], lambda f, t: (_sit(arm, drop), _look(arm, logan, 0.4)), layered=True)


# ---------------------------------------------------------------- on their knees
def _kneel(arm, k, w=1.0, back=0.0, hands=1.0):
    """Down on both knees on the boards: the knees under the hips, the pelvis lowered until the thighs stand up from
    them (`back` sits the hips back toward the heels), the shins flat behind along the floor, the soles up; the hands
    on the thighs."""
    if w <= 0: return
    pel, fwd, right, up = _live(arm)
    th = people._world(arm, arm.pose.bones['Bip01 L Thigh']).translation; kn = people._world(arm, arm.pose.bones['Bip01 L Calf']).translation
    ft = people._world(arm, arm.pose.bones['Bip01 L Foot']).translation
    a, b = (kn - th).length, (ft - kn).length
    knees = {s: Vector((h.x, h.y, 0.055 * k)) + fwd * 0.05 * k for s, h in ((s, people._world(arm, arm.pose.bones[f'Bip01 {s} Thigh']).translation.copy()) for s in 'LR')}
    hip_z = 0.055 * k + a * (1.0 - 0.45 * back)
    people.shift_root(arm, Vector((0, 0, -(th.z - hip_z) * w)) - fwd * back * a * 0.55 * w)
    for side in 'LR':
        knee = knees[side]; ankle = knee - fwd * b * 0.97 + up * 0.035 * k
        A0 = people._world(arm, arm.pose.bones[f'Bip01 {side} Foot']).translation.copy()
        people.ik_leg(arm, side, A0.lerp(ankle, w), knee + fwd * 0.6 * k - up * 0.1 * k, keep_foot=False)
        fb = arm.pose.bones[f'Bip01 {side} Foot']; F = people._world(arm, fb); c_ = F.translation.copy()   # the foot laid back along the floor
        people._set_world(arm, fb, Matrix.Translation(c_) @ Matrix.Rotation(0.9 * w, 4, right) @ Matrix.Translation(-c_) @ F)
    if hands > 0:
        for side, sd in (('L', -1), ('R', 1)):
            hip = people._world(arm, arm.pose.bones[f'Bip01 {side} Thigh']).translation; knee = people._world(arm, arm.pose.bones[f'Bip01 {side} Calf']).translation
            tgt = hip.lerp(knee, 0.55) + fwd * 0.13 * k + right * sd * 0.02 * k + up * 0.03 * k     # on the front of the thigh
            H0 = people._world(arm, arm.pose.bones[f'Bip01 {side} Hand']).translation.copy(); g = H0.lerp(tgt, hands * w)
            people.ik2(arm, side, g, g + right * sd * 0.35 * k - fwd * 0.05 * k + up * 0.15 * k)
            people.palm_to(arm, side, -up, 0.7 * hands * w)


def _fours(arm, k, w, reach=0.0, phase=0.0, look=None):
    """On all fours: the back bent down from the kneel, the hands flat on the boards ahead under the shoulders, the head
    up; `reach` swings a hand out further for a sausage (alternating with `phase`)."""
    if w <= 0: return
    pel, fwd, right, up = _live(arm)
    for b_, a in zip(SPINE, (0.5, 0.4, 0.3)): people.bend(arm, b_, right, -a * w)
    people.bend(arm, 'Bip01 Neck', right, 0.45 * w); people.bend(arm, 'Bip01 Head', right, 0.35 * w)
    for side, sd in (('L', -1), ('R', 1)):
        sh = people._world(arm, arm.pose.bones[f'Bip01 {side} UpperArm']).translation
        r_ = max(0.0, math.sin(phase + (0 if side == 'L' else math.pi))) * reach
        tgt = Vector((sh.x, sh.y, 0.04 * k)) + fwd * (0.1 + r_) * k + right * sd * 0.05 * k
        H0 = people._world(arm, arm.pose.bones[f'Bip01 {side} Hand']).translation.copy(); g = H0.lerp(tgt, w)
        people.ik2(arm, side, g, g + right * sd * 0.4 * k - fwd * 0.2 * k + up * 0.1 * k)
        people.palm_to(arm, side, -up, 0.8 * w)
    if look is not None: _look(arm, look, 0.5 * w)


def _boar_acts(m, acts, full):
    """Tom, Greg and Karl kneeling on the boards before the fire, hands on their thighs, eyes on Logan's chair; idles:
    an oink (the head lifted, bobbing); a look at the man beside him."""
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; who = m['c']['who']; T = (frames[1] - frames[0]) / people.FPS
    logan = _head_of('logan') + Vector((0, 0, 0.1 * S))
    others = [w for w in KNEEL if w != who]
    kneel = lambda f, t: (_kneel(arm, k, back=0.15 if who == 'tom' else 0.0), _look(arm, logan, 0.5))
    acts['kneel'] = people.custom_act(arm, base, frames, f'{who}_kneel', kneel, _all(arm, fingers=True)); m['steps'] = {'kneel': kneel}
    if not full: return
    def oink(f, t):
        _kneel(arm, k, back=0.15 if who == 'tom' else 0.0)
        e = people.envelope(t, T, 1.0, 1.4); pel, fwd, right, up = _live(arm)
        people.bend(arm, 'Bip01 Head', right, (0.3 + 0.12 * math.sin(2 * math.pi * t / 0.55)) * e)
        _look(arm, logan, 0.4)
    acts['oink'] = people.custom_act(arm, base, frames, f'{who}_oink', oink, _all(arm, fingers=True))
    other = _head_of(others[0])
    def look(f, t):
        _kneel(arm, k, back=0.15 if who == 'tom' else 0.0); e = people.envelope(t, T, 1.5, 1.5)
        _look(arm, logan, 0.5 * (1 - e)); _look(arm, other, 0.8 * e)
    acts['look'] = people.custom_act(arm, base, frames, f'{who}_look', look, _all(arm, fingers=True))


# ---------------------------------------------------------------- the waiter
def _behind_back(arm, k, w=1.0):
    """Hands clasped behind the back, at the small of it."""
    pel, fwd, right, up = _live(arm)
    for side, sd in (('L', -1), ('R', 1)):
        tgt = pel - fwd * 0.16 * k + up * 0.06 * k + right * sd * 0.03 * k
        H0 = people._world(arm, arm.pose.bones[f'Bip01 {side} Hand']).translation.copy(); g = H0.lerp(tgt, w)
        people.ik2(arm, side, g, g + right * sd * 0.4 * k - fwd * 0.1 * k)


def _waiter_acts(m, acts, full):
    """The waiter at the window wall, upright, his hands behind his back, his eyes on the head of the table; idles: a
    look round; a round of the room, out to the far door and back."""
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']
    logan = _head_of('logan')
    stand = lambda f, t: (_behind_back(arm, k), _look(arm, logan, 0.4))
    acts['stand'] = people.custom_act(arm, base, frames, 'waiter_stand', stand, _all(arm, fingers=True)); m['steps'] = {'stand': stand}
    if not full: return
    _clip_act(m, acts, 'look', IDLES['waiter']['look'][0], lambda f, t: _behind_back(arm, k, 0.8))
    walk, walkf, vs = people.retarget(arm, 'm_walk_neutral_02', inplace=True, cycles=16, action_name='waiter_src_walk')
    turn, turnf, _ = people.retarget(arm, 'm_turn_left_180', action_name='waiter_src_turn')
    (x, y), f0 = SPOTS['waiter']; home = P(x, y); hs = Vector((*f0, 0)).normalized()
    door = P(-6.75, R.DOORS_L[1] - 0.2)
    r_go = people.path([home, P(0.1, 4.75), P(-2.2, 4.45), P(-4.4, 4.35), door]); r_back = people.path([door, P(-4.4, 4.45), P(-2.2, 4.55), P(0.0, 4.75), home])
    htn, ptn = people.heading(arm, turn, turnf[0]); tdur = (turnf[1] - turnf[0]) / people.FPS
    segs = [dict(src=base, f0=frames[0], dur=1.0, at=Matrix.Identity(4)),
            dict(src=turn, f0=turnf[0], dur=tdur, at=people.carry(ptn, htn, home, hs), blend=0.5),
            dict(src=walk, f0=walkf[0], dur=r_go[1] / vs, at=people.walk_along(arm, walk, walkf[0], vs, r_go), blend=0.7),
            dict(src=base, f0=frames[0], dur=2.5, at=people.carry(*people.heading(arm, base, frames[0])[::-1], door, Vector((-1, 0, 0))), blend=0.8),
            dict(src=turn, f0=turnf[0], dur=tdur, at=people.carry(ptn, htn, door, Vector((-1, 0, 0))), blend=0.5),
            dict(src=walk, f0=walkf[0] + 12, dur=r_back[1] / vs, at=people.walk_along(arm, walk, walkf[0], vs, r_back), blend=0.7),
            dict(src=turn, f0=turnf[0], dur=tdur, at=people.carry(ptn, htn, home, -hs), blend=0.5),
            dict(src=base, f0=frames[0], dur=1.6, at=Matrix.Identity(4), blend=1.0)]
    acts['round'] = people.sequence(arm, base, 'waiter_round', segs, overlay=lambda tt, i, lt: _behind_back(arm, k, 0.9) if i in (0, 3, 7) else None)
    for a in (walk, turn): bpy.data.actions.remove(a)


# ---------------------------------------------------------------- the scene
# Logan's way round the room (true metres): behind Kendall's chair, back to his place for the plate, round his chair
# to the boars at the hearth, back, down.
BEHIND_KENDALL = (R.SEATS_X[0], R.YT + R.SIDE_Y + 0.68)
PLATE_STAND = (R.TX0 - 0.42, PLATE[1] + 0.02)
AT_BOARS = (-5.28, R.YF - 0.95)          # off to the boars' side, clear of Karl, facing them across the hearth


def _scene(made, acts):
    """Logan's act (the room opens on it): up from his chair, round behind Kendall (his hands on his son's shoulders,
    talking down at him), back for the plate of sausages, round his chair to the hearth, 'Boar on the floor!': he
    pitches the sausages down to the three on their knees, stands over them, then back to the table, the plate down,
    into his chair. Cued with it: Kendall under his father's hands, the boars scrambling on all fours, every other eye
    following him."""
    FPS = people.FPS; L = made['logan']; la, lb, lfr, ldrop, lk = L['arm'], L['base'], L['frames'], L['drop'], L['k']
    up, upf, _ = people.retarget(la, 'm_sit_stand_up_chair_01', action_name='logan_src_up')
    down, downf, _ = people.retarget(la, 'm_sit_down_chair_01', action_name='logan_src_down')
    walk, walkf, vs = people.retarget(la, 'm_walk_slow_01', inplace=True, cycles=12, action_name='logan_src_walk')
    talk, talkf, _ = people.retarget(la, 'm_gestic_talk_self_assured_01', cycles=3, action_name='logan_src_talk')
    angry, angryf, _ = people.retarget(la, 'm_gestic_talk_angry_01', limit=400, action_name='logan_src_angry')
    lis, lisf, _ = people.retarget(la, 'm_gestic_listen_neutral_01', cycles=4, action_name='logan_src_listen')
    sitb = _long_base(L, 6.0, 'scene_sit')[0]
    cine.log(f'logan walks at {vs / S:.2f} m/s (true)')
    t0f = lfr[0]
    _h, p_s = people.heading(la, lb, t0f); h_s = Vector(la['fwd'])
    hu, pu = people.heading(la, up, upf[0]); M_up = people.carry(pu, hu, p_s, h_s)
    hu1, pu1 = _ends(la, up, upf[1], M_up)
    back = max(0.0, (pu1 - p_s).dot(h_s) - 0.12 * S)                       # the table's end is close: he rises back from it
    up_dur, down_dur = (upf[1] - upf[0]) / FPS, (downf[1] - downf[0]) / FPS
    M_up_f = lambda lt: Matrix.Translation(-h_s * back * _smooth(lt / up_dur)) @ M_up
    pu1 = pu1 - h_s * back
    hd, pd = people.heading(la, down, downf[1]); M_down = people.carry(pd, hd, p_s, h_s)
    hd0, pd0 = _ends(la, down, downf[0], M_down)
    M_down_f = lambda lt: Matrix.Translation(-h_s * back * (1 - _smooth(lt / down_dur))) @ M_down
    pd0 = pd0 - h_s * back
    BK, PS, AB = P(*BEHIND_KENDALL), P(*PLATE_STAND), P(*AT_BOARS)
    r1 = people.path([pu1, pu1 + P(0.15, 0.45), P(R.HEAD[0] + 0.3, R.YT + 1.25), P(-4.0, BK.y / S), BK])
    r2 = people.path([BK, P(-4.05, BK.y / S - 0.15), P(R.HEAD[0] + 0.42, R.YT + 0.95), PS])
    r3 = people.path([PS, P(R.HEAD[0] - 0.33, R.YT + 0.68), P(R.HEAD[0] - 0.75, R.YT + 0.3), P(R.HEAD[0] - 0.82, R.YT - 0.35), AB])
    r4 = people.path([AB, P(R.HEAD[0] - 0.82, R.YT - 0.3), P(R.HEAD[0] - 0.75, R.YT + 0.32), P(R.HEAD[0] - 0.33, R.YT + 0.7), PS])
    r5 = people.path([PS, pd0])
    ht, pt = people.heading(la, talk, talkf[0]); ha, pa = people.heading(la, angry, angryf[0]); hl, pl = people.heading(la, lis, lisf[0])
    M_bk = people.carry(pt, ht, BK, Vector((0, -1, 0)))
    M_ps = people.carry(pl, hl, PS, Vector((1, 0, 0)))
    M_ab = people.carry(pa, ha, AB, Vector((-0.75, 0.66, 0)).normalized())
    M_abl = people.carry(pl, hl, AB, Vector((-0.6, 0.8, 0)).normalized())
    M_ps2 = people.carry(pl, hl, PS, Vector((1, 0, 0)))
    segs = [dict(src=sitb, f0=t0f, dur=2.5, at=Matrix.Identity(4)),                                                    # 0 at the head
            dict(src=up, f0=upf[0], dur=up_dur, at=M_up_f, blend=0.7),                                                 # 1 up
            dict(src=walk, f0=walkf[0], dur=r1[1] / vs, at=people.walk_along(la, walk, walkf[0], vs, r1), blend=0.8),  # 2 round to Kendall
            dict(src=talk, f0=talkf[0], dur=6.5, at=M_bk, blend=0.8),                                                  # 3 his hands on his shoulders
            dict(src=walk, f0=walkf[0] + 15, dur=r2[1] / vs, at=people.walk_along(la, walk, walkf[0], vs, r2), blend=0.8),   # 4 back for the plate
            dict(src=lis, f0=lisf[0], dur=2.4, at=M_ps, blend=0.7),                                                    # 5 the plate up
            dict(src=walk, f0=walkf[0], dur=r3[1] / vs, at=people.walk_along(la, walk, walkf[0], vs, r3), blend=0.8),  # 6 to the hearth
            dict(src=angry, f0=angryf[0] + 60, dur=7.5, at=M_ab, blend=0.8),                                           # 7 boar on the floor
            dict(src=lis, f0=lisf[0] + 90, dur=4.5, at=M_abl, blend=0.8),                                              # 8 stands over them
            dict(src=walk, f0=walkf[0] + 20, dur=r4[1] / vs, at=people.walk_along(la, walk, walkf[0], vs, r4), blend=0.8),   # 9 back
            dict(src=lis, f0=lisf[0] + 30, dur=2.2, at=M_ps2, blend=0.7),                                              # 10 the plate down
            dict(src=walk, f0=walkf[0] + 8, dur=max(r5[1] / vs, 0.8), at=people.walk_along(la, walk, walkf[0], vs, r5), blend=0.7),   # 11 to his chair
            dict(src=down, f0=downf[0], dur=down_dur, at=M_down_f, blend=0.9),                                         # 12 down
            dict(src=sitb, f0=t0f + 60, dur=2.5, at=Matrix.Identity(4), blend=1.0)]                                    # 13 at the head again
    tv = [0.0]
    for sg in segs: tv.append(tv[-1] + sg['dur'])
    T_end = tv[-1]
    cine.log('logan scene beats (s): ' + ', '.join(f'{i}:{t:.1f}' for i, t in enumerate(tv)))
    # Kendall's shoulders while his father stands behind him (Kendall is seated: his pose barely moves)
    K = made['kendall']; people.pose_at(K['arm'], K['base'], K['frames'][0]); _sit(K['arm'], K['drop'])
    k_sh = {s: people._world(K['arm'], K['arm'].pose.bones[f'Bip01 {s} UpperArm']).translation.copy() for s in 'LR'}
    plate_at = P(PLATE[0], PLATE[1], R.TH + 0.03)
    t_grab = tv[5] + 1.1; t_release = tv[10] + 1.1
    def held_at():
        pel, fwd, right, up_ = _live(la)
        return people._world(la, la.pose.bones['Bip01 L UpperArm']).translation + (fwd * 0.3 - up_ * 0.25 - right * 0.08) * lk
    def plate_hand(lt, dur, pick):
        """The left hand down to the plate on the table and up with it (`pick`), or down with it and away; he leans to
        the table meanwhile. The hand closes on the plate (or lets go) at 1.1 s."""
        pel, fwd, right, up_ = _live(la)
        H0 = people._world(la, la.pose.bones['Bip01 L Hand']).translation.copy(); held = held_at(); on = plate_at + up_ * 0.02 * lk
        if pick: g = H0.lerp(on, _smooth(lt / 1.0)) if lt < 1.2 else on.lerp(held, _smooth((lt - 1.2) / 0.9))
        else: g = held.lerp(on, _smooth(lt / 1.0)) if lt < 1.2 else on.lerp(H0, _smooth((lt - 1.2) / 0.9))
        people.ik2(la, 'L', g, g - up_ * 0.3 * lk - right * 0.3 * lk); people.palm_to(la, 'L', up_, 0.8)
        for b_, ang in zip(SPINE, (0.12, 0.1, 0.06)): people.bend(la, b_, right, -ang * people.envelope(lt, dur, 0.8, 0.8))
    def hold_plate(w=1.0):
        pel, fwd, right, up_ = _live(la); g = held_at()
        H0 = people._world(la, la.pose.bones['Bip01 L Hand']).translation.copy(); g = H0.lerp(g, w)
        people.ik2(la, 'L', g, g - up_ * 0.3 * lk - right * 0.3 * lk); people.palm_to(la, 'L', up_, 0.8 * w)
    def overlay(tt, i, lt):
        if i in (0, 13): _diner(la, ldrop, lk, _head_of('kendall'), 0.5, lean=0.12); _table_hands(la, lk, w=0.8 if i == 0 else _smooth(lt / 1.5) * 0.8, clasp=True, reach=0.36)
        elif i == 3:                                                                # his hands on Kendall's shoulders
            e = people.envelope(lt, segs[3]['dur'], 1.0, 1.0); pel, fwd, right, up_ = _live(la)
            for b_, ang in zip(SPINE, (0.16, 0.14, 0.1)): people.bend(la, b_, right, -ang * e)
            for s in 'LR':
                g0 = people._world(la, la.pose.bones[f'Bip01 {s} Hand']).translation.copy()
                g = g0.lerp(k_sh[s] + Vector((0, 0, 0.05 * lk)) + Vector((0, 0.02 * lk, 0)), e)
                people.ik2(la, s, g, g + up_ * 0.1 * lk + right * (0.4 if s == 'R' else -0.4) * lk + fwd * 0.2 * lk)
                people.palm_to(la, s, -up_, 0.8 * e)
            _look(la, _head_of('kendall') - Vector((0, 0, 0.1 * S)), 0.6)
        elif i == 5: plate_hand(lt, segs[5]['dur'], True)
        elif i in (6, 8, 9): hold_plate()
        elif i == 7:                                                                # the sausages pitched down, one after another
            hold_plate(); pel, fwd, right, up_ = _live(la)
            for j, tj in enumerate((1.4, 3.3, 5.2)):
                e = people.envelope(lt - tj, 1.4, 0.5, 0.6) if tj < lt < tj + 1.4 else 0.0
                if e <= 0: continue
                sh = people._world(la, la.pose.bones['Bip01 R UpperArm']).translation
                plate = people._world(la, la.pose.bones['Bip01 L Hand']).translation
                fling = sh + (fwd * 0.42 - up_ * 0.42 + right * 0.1) * lk
                u = min(max((lt - tj) / 1.4, 0.0), 1.0)
                g = plate.lerp(fling, _smooth((u - 0.3) / 0.5)) + up_ * 0.06 * lk * math.sin(math.pi * u)
                H0 = people._world(la, la.pose.bones['Bip01 R Hand']).translation.copy()
                people.ik2(la, 'R', H0.lerp(g, e), H0.lerp(g, e) - up_ * 0.3 * lk + right * 0.3 * lk)
            _look(la, P(-6.1, R.YF + 0.2, 0.5), 0.6)
        elif i == 10: plate_hand(lt, segs[10]['dur'], False)
    act = people.sequence(la, lb, 'logan_scene', segs, overlay=overlay)
    for a in (up, down, walk, talk, angry, lis, sitb): bpy.data.actions.remove(a)
    acts['logan']['scene'] = act
    la['open_act'], la['open_at'] = 'scene', round(tv[2], 2)
    la['plate_grab'], la['plate_release'] = round(t_grab, 2), round(t_release, 2)
    OPEN['logan'] = ('scene', la['open_at']); PLATE_HELD.update(grab=t_grab, release=t_release)
    heads = _samples(la, act)
    n = int(round(T_end * FPS))
    def follow(who, name, step):
        m = made[who]; arm = m['arm']
        lb_, lf_, _ = _long_base(m, T_end + 1.0, 'cue')
        def st(f, t):
            i = min(int(round(t * FPS)), len(heads) - 1); step(t, heads[i])
        acts[who][name] = people.custom_act(arm, lb_, (lf_[0], lf_[0] + n), f'{who}_{name}', st, _all(arm, fingers=True))
        bpy.data.actions.remove(lb_)
    # Kendall: under his father's hands he sits still and looks down at the table; otherwise his eyes follow him
    def kendall(t, h):
        m = made['kendall']; arm = m['arm']; e = people.envelope(t - tv[3], segs[3]['dur'], 1.0, 1.0) if tv[3] < t < tv[4] else 0.0
        _diner(arm, m['drop'], m['k'], h, 0.6 * (1 - e)); _table_hands(arm, m['k'], w=0.6)
        pel, fwd, right, up_ = _live(arm); people.bend(arm, 'Bip01 Head', right, -0.25 * e)
    follow('kendall', 'shoulders', kendall)
    for who in ('gerri', 'frank'):
        m = made[who]
        follow(who, 'watch', lambda t, h, m=m: (_diner(m['arm'], m['drop'], m['k'], h, 0.7), _table_hands(m['arm'], m['k'], w=0.6)))
    Rm = made['roman']
    def roman(t, h):
        _sit(Rm['arm'], Rm['drop']); pel, fwd, right, up_ = _live(Rm['arm'])
        for b_, a in zip(SPINE, (0.06, 0.04, 0.02)): people.bend(Rm['arm'], b_, right, a)
        _look(Rm['arm'], h, 0.7)
    follow('roman', 'watch', roman)
    Wt = made['waiter']
    follow('waiter', 'watch', lambda t, h: (_behind_back(Wt['arm'], Wt['k']), _look(Wt['arm'], h, 0.5)))
    # the boars: on their knees till the first sausage falls, then down on all fours scrabbling for them, then up again
    t_down, t_up = tv[7] + 1.6, tv[8] + 2.0
    for j, who in enumerate(('tom', 'greg', 'karl')):
        m = made[who]
        def boar(t, h, m=m, j=j):
            arm, k = m['arm'], m['k']; back = 0.15 if m['c']['who'] == 'tom' else 0.0
            w = _smooth((t - t_down - 0.3 * j) / 1.0) * (1 - _smooth((t - t_up - 0.2 * j) / 1.2))
            _kneel(arm, k, back=back * (1 - w), hands=1 - w)
            _fours(arm, k, w, reach=0.18, phase=2 * math.pi * t / (1.3 + 0.2 * j) + j, look=P(-5.75, R.YF + 0.2 * (j - 1), 0.0))
            if w < 0.5: _look(arm, h, 0.6 * (1 - 2 * w))
        follow(who, 'scramble', boar)
    cine.log(f'the scene: {T_end:.1f} s; opens at {la["open_at"]}; plate {t_grab:.1f}-{t_release:.1f}')


# ---------------------------------------------------------------- bake and export
def bake(sc, objs, phantoms, seated, args):
    """The ballroom's light baked into atlases (the people out of it: they all move); then room.glb, the people and
    room.json."""
    os.makedirs(WEB, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    for c, arm, mesh in seated: mesh.hide_render = True
    export, atlases = stages.bake(objs, R.RH * R.SCALE, OUT, int(args.get('size', 2048)), int(args.get('samples', 320)))
    for c, arm, mesh in seated: mesh.hide_render = False
    cine.export_glb(export, os.path.join(WEB, 'room.glb'))
    meta = stages.room_meta(R.RH * R.SCALE, atlases); meta.update(_capture_meta()); meta.update(_live_meta())
    meta['people'] = _export_people(seated)
    stages.write_meta(WEB, meta)


def _export_people(seated):
    out = os.path.join(WEB, 'people'); os.makedirs(out, exist_ok=True); metas = []
    for c, arm, mesh in seated:
        people.export_person(arm, mesh, c['acts'], os.path.join(out, f"{c['who']}.glb"), roam=c.get('roam', ()))
        metas.append(person_meta(c))
    return metas


def _capture_meta():
    """How to light the people as the bake lit the room (three.js: y up, z = -Blender y; module metres): the fire, the
    candles and the shaded bulbs as small bright spheres."""
    bulbs = []
    for l in RIG['lights']:
        if l.type != 'LIGHT' or l.data.type != 'POINT': continue
        r = 0.012 if l.name.startswith('candle') else 0.04 if l.name.startswith('fire') else 0.03; e = l.data.energy
        bulbs.append({'x': round(l.location.x, 3), 'y': round(l.location.z, 3), 'z': round(-l.location.y, 3), 'r': r,
                      'L': round(e / (4 * math.pi * r ** 2) / 60, 2), 'color': [round(v, 3) for v in l.data.color]})
    S = R.SCALE
    fire = {'x': round((R.XB - 0.02) * S, 3), 'y': round(R.OPEN_H * 0.45 * S, 3), 'z': round(-R.YF * S, 3), 'w': round(R.OPEN_W * S, 3), 'h': round(R.OPEN_H * 0.8 * S, 3),
            'L': 4.0, 'color': list(R.FIRE), 'ry': round(-math.pi / 2, 4)}
    at = [[round(v, 3) for v in (p.x, p.z, -p.y)] for p in (Vector((-1.0, R.YT, 1.1)) * S, Vector((-5.8, R.YF, 0.6)) * S, Vector((0.5, 4.8, 1.4)) * S)]
    return {'capture': {'ceiling': [0.05, 0.04, 0.03], 'walls': [0.14, 0.1, 0.07], 'emitters': bulbs, 'windows': [fire], 'at': at}}


def _live_meta():
    """What the web plays live: the plate of sausages in Logan's left hand, from when he takes it up to when he sets it
    down again."""
    if not PLATE_HELD: return {}
    return {'live': {'held': [{'who': 'logan', 'act': 'scene', 'prop': 'plate_logan', 'hand': 'L', 'grab': round(PLATE_HELD['grab'], 2),
                               'release': round(PLATE_HELD['release'], 2)}]}}



def person_meta(c):
    """The acts in a person's file, the looping one first, how long it lasts and how often each idle comes up; an act
    that cues others names them; the act the room opens on, and how far into it."""
    work, lo, hi = c['work']
    acts = [{'name': work, 'loop': True, 'min': lo, 'max': hi}]
    for k, (clip, w) in c['idles'].items():
        if k not in c['acts'] or w <= 0: continue
        a = {'name': k, 'w': w}
        if k in c.get('cue', {}): a['cue'] = c['cue'][k]
        if FIRST.get(c['who']) == k: a['first'] = True
        if OPEN.get(c['who'], (None,))[0] == k: a['at'] = OPEN[c['who']][1]
        acts.append(a)
    for k in c['acts']:
        if k != work and not any(a['name'] == k for a in acts): acts.append({'name': k, 'w': 0})      # only ever cued
    return {'who': c['who'], 'file': f"{c['who']}.glb", 'acts': acts}


def people_stage(sc, cams, seated, args):
    """Re-export only the people (their glTF files and their part of room.json); the baked room stays as it is. Then a
    look at them in the room (Cycles)."""
    stages.update_meta(WEB, people=_export_people(seated), **_capture_meta(), **_live_meta())
    for c, arm, mesh in seated: people.pose_at(arm, c['acts'][c['work'][0]], int(c['acts'][c['work'][0]].frame_range[0]) + 60)
    for which in str(args.get('cams', 'close,front')).split(','):
        preview(sc, cams, which, int(args.get('samples', 64)), os.path.join(OUT, f'people_{which}.png'), size=(1200, 800))
