# Interstellar: assemble Murph's bedroom, the landing and the tesseract behind the shelf, its people (Murph, Cooper
# at the door, Cooper in the tesseract) and the room's own rig (the door, the books he knocks out, the lander); then
# preview, bake and export.
import math, os, random
import bpy
from mathutils import Vector, Matrix, Quaternion
import cine, people, stages
from stages import camera
import rooms.interstellar as R

ROOM = 'interstellar'
OUT = os.path.join(cine.OUT, ROOM)
WEB = os.path.join(cine.ROOT, 'public', 'rooms', ROOM)
PEOPLE_TEX = os.path.join(cine.OUT, 'people')
ARGS = {}
SEATED = []
MATS = {}
RIG = {'lights': [], 'books': None}


def build(args):
    ARGS.clear(); ARGS.update(args)
    sc = cine.reset(int(args.get('samples', 256)))
    M = R.mats(); MATS.update(M)
    static, phantom, crowd = cine.coll('static'), cine.coll('phantom'), cine.coll('people')
    rnd = random.Random(2014)
    RIG['books'] = R.rig_books(rnd)
    seated = [] if args.get('nocast') else cast(crowd, args)
    SEATED[:] = seated
    rb = RIG['books']
    skip = {(R.FALL_BAY, R.FALL_SHELF): (rb['falls'][0][0], rb['lander'][1]), (R.STAY_BAY, R.STAY_SHELF): (rb['stay'][0][0], rb['stay'][0][1])}
    R.shell(M, static, phantom)
    wins = R.windows(M, static)
    R.doorway(M, static)
    R.bookshelf(M, static, rnd, skip)
    R.bed(M, static)
    bulb = R.furniture(M, static, rnd)
    R.landing(M, static)
    R.tesseract(M, static, rnd)
    RIG['lights'] = R.lights(bulb, wins)
    nb = cine.box('notebook', (0.17, 0.22, 0.012), tuple(NB_REST + Vector((0, 0, 0.006))), cine.material('notebook_cover', (0.16, 0.22, 0.34), rough=0.6), rot=(0, 0, 0.35), bev=0.002, collection=static, role='mug')
    nb['who'] = 'murph'
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
    cams = {'case': camera('cam_case', (1.4, -17.0, 7.0), (-0.2, 0.3, 0.8), 30),
            'close': camera('cam_close', (-1.2, -7.4, 2.4), (-0.6, 0.0, 0.9), 40),
            'bed': camera('cam_bed', (0.6, -3.4, 1.35), (-1.5, -1.6, 0.7), 50),         # Murph's place, from the shelf's front end
            'shelf': camera('cam_shelf', (-2.4, -0.6, 1.5), (0.95, 1.9, 1.1), 46),          # the books and the falling bay, from the bed's foot
            'door': camera('cam_door', (0.3, -2.2, 1.6), (-3.74, 0.0, 1.0), 48),            # the door wall: the door, the desk, the corkboard
            'tess': camera('cam_tess', (4.3, -3.3, 1.8), (1.4, 2.2, 1.2), 52),              # the tesseract, Cooper's cell
            'back': camera('cam_back', (-1.6, -3.3, 1.4), (-1.4, 3.6, 1.4), 54),            # the windows and the chest
            'top': camera('cam_top', (0.0, 0.0, 14.0), (0.0, 0.1, 0.0), 38),
            'murph': camera('cam_murph', (0.25, -3.3, 1.25), (-0.7, -2.45, 0.92), 34),
            'coop': camera('cam_coop', (-4.35, -3.5, 1.6), (-4.3, 2.8, 1.0), 44),
            'lie': camera('cam_lie', (0.3, -2.6, 2.4), (-1.2, -2.6, 0.7), 46),
            'act': camera('cam_act', (1.1, -4.9, 2.7), (-1.1, 0.4, 0.7), 52),
            'cooper': camera('cam_cooper', (2.4, 0.6, 2.0), (1.5, 2.25, 1.3), 58)}
    return sc, M, objs, list(phantom.objects), seated, cams


def _static_rig(M, col):
    """Without the cast: the rig's door, books and lander where they rest (to judge the set)."""
    import rooms.interstellar_rig as RG
    arm, mesh = RG.make_rig(RIG['books'], M, col)
    mesh.parent = None


KEEP = ('left_', 'back_wall', 'kerb', 'floor', 'subfloor', 'shelf_end', 'books_shelved')


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
            stages.render(sc, cams[which], samples, path.replace('.png', f'_{act}_{float(t):04.1f}.png'), (960, 600), float(ARGS.get('exposure', 0.0)))
        return
    for spec in filter(None, str(ARGS.get('pose', '')).split(',')):
        who, act, f = spec.split(':')
        for c, arm, mesh in SEATED:
            if c['who'] == who and act in c['acts']: people.pose_at(arm, c['acts'][act], int(c['acts'][act].frame_range[0]) + int(f))
    stages.render(sc, cams[which], samples, path, size, float(ARGS.get('exposure', 0.0)))


# ---------------------------------------------------------------- the cast
# Murph (ten) on the side of her bed, combing her wet hair; Cooper (his earlier self) on the landing, looking out of
# its window; Cooper in the tesseract, hanging at the backs of the books. Costumes after Mary Zophres
# (people_textures.interstellar). The scene (Murph's act, `scene`) cues everyone's, and the room's rig: the books
# fall, she goes to them with her notebook, he comes in, they look together and he puts the lander and the books back;
# she goes back to bed and cries, he sits by her, gets up to go; the last book is punched out, he stops at the door,
# looks back, and goes; she gets up, puts the book back, and combs her hair again.
def _tex(who, prefix, *names):
    return {f'{prefix}_{n}.tga': f'{who}/{prefix}_{n}.png' for n in names}


CAST = [
    dict(who='murph', avatar='Female_Child_01', height=1.47, child=True,
         shell=dict(colour=(60, 36, 26), hem=-0.36, thick=0.005, gap=0.004, fall=0.008, front=32.0, temple=14.0, nape=-30.0, width=0.026,
                    lie=0.35, tuck=0.5, layers=3, ncol=60),
         tex=_tex('murph', 'cf001', 'head_color', 'body_color', 'body_normal')),
    dict(who='coop', avatar='Male_Adult_08', shape=('lean', 0.6), height=1.82, tex=_tex('coop', 'm014', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
    dict(who='cooper', avatar='Male_Adult_08', shape=('lean', 0.6), height=1.82, tex=_tex('cooper', 'm014', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
]
CHILD_LEG = 0.84                           # the child's legs over the clips' (an adult woman's): the clips' pelvis carried lower
SEAT_Z = R.BED_TOP - 0.03                  # where she sits (the mattress gives)
MURPH_F = (0.86, -0.5)                     # sitting on the bed's side, half to the case, half to the shelf
COOP_HOME = ((-4.12, 2.62), (-1.0, 0.0))   # on the landing, at its table (facing the wall: in his bind pose, his arms must stay inside the module)
COOPER_AT = Vector((R.TX0 + 0.38, (R.BAYS[R.FALL_BAY][0] + R.BAYS[R.FALL_BAY][1]) / 2 - 0.05, 0.98))   # the pelvis, floating
BASES = {'murph': 'f_sit_chair_breathe_01', 'coop': 'm_idle_breathe_01', 'cooper': 'm_idle_breathe_01'}
WORK = {'murph': ('comb', 6, 14), 'coop': ('wait', 20, 40), 'cooper': ('float', 20, 40), 'room': ('rest', 20, 40)}
FIRST = {'murph': 'scene'}
CUE = {'murph': {'scene': {'coop': 'scene', 'cooper': 'scene', 'room': 'scene'}}}
SPINE = ('Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2')
ARMS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('Clavicle', 'UpperArm', 'Forearm', 'Hand'))
LEGS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('Thigh', 'Calf', 'Foot'))
FINGERS = tuple(f'Bip01 {s} Finger{f}{j}' for s in 'LR' for f in '01234' for j in ('', '1', '2'))
ALL = ('Bip01 Pelvis',) + SPINE + ARMS + LEGS + ('Bip01 Neck', 'Bip01 Head')
HANDS = {}                                  # who -> {frame: (L hand matrix, R hand matrix)} in the scene (for the rig)


def _all(arm, fingers=False):
    return (next(b.name for b in arm.data.bones if b.parent is None),) + ALL + (FINGERS if fingers else ())


def _smooth(x):
    x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)


def _win(t, a, b, rise=0.5, fall=0.5):
    """1 between a and b, eased in and out over rise and fall seconds."""
    return _smooth((t - a) / rise) * (1 - _smooth((t - b) / fall))


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
    yaw = max(-1.3, min(1.3, yaw)); pitch = max(-0.8, min(0.6, pitch))
    people.bend(arm, 'Bip01 Neck', up, yaw * 0.35 * w); people.bend(arm, 'Bip01 Head', up, yaw * 0.65 * w)
    people.bend(arm, 'Bip01 Neck', right, pitch * 0.3 * w); people.bend(arm, 'Bip01 Head', right, pitch * 0.7 * w)


def _turn_root(arm, pivot, axis, angle):
    """Turn the whole body about a world point (the root bone; everything rides on it): onto her side, on the bed."""
    root = next(pb for pb in arm.pose.bones if pb.parent is None)
    M = people._world(arm, root); R_ = Matrix.Translation(pivot) @ Matrix.Rotation(angle, 4, Vector(axis)) @ Matrix.Translation(-Vector(pivot))
    root.matrix = arm.matrix_world.inverted() @ R_ @ M
    bpy.context.view_layer.update()


def _hand_to(arm, side, tgt, w, pole, palm=None, pw=0.8):
    """A hand toward a point by w (IK from where the clip has it), its elbow toward `pole`, its palm facing `palm`."""
    if w <= 0: return
    H0 = people._world(arm, arm.pose.bones[f'Bip01 {side} Hand']).translation.copy(); g = H0.lerp(Vector(tgt), min(w, 1.0))
    people.ik2(arm, side, g, Vector(pole))
    if palm is not None: people.palm_to(arm, side, Vector(palm).normalized(), pw * min(w, 1.0))


def make_person(c, col):
    """One of them, standing at the origin facing -y: the avatar, its build, its hair, its kit (the comb in Murph's
    hand; the helmet, its neck ring and the life-support pack on Cooper in the tesseract), its height."""
    tex = {k: os.path.join(PEOPLE_TEX, v) for k, v in c.get('tex', {}).items() if os.path.exists(os.path.join(PEOPLE_TEX, v))}
    arm, mesh = people.load_avatar(c['avatar'], textures=tex, collection=col)
    arm.animation_data_clear()
    if c.get('child'):                                          # the children's skeleton is Bip02: the clips and the kit say Bip01
        for b in arm.data.bones: b.name = b.name.replace('Bip02', 'Bip01')
        arm['leg_k'] = CHILD_LEG
    mesh['person'] = c['who']; arm['person'] = c['who']
    if c.get('shape'): people.reshape(arm, mesh, *c['shape'])
    bpy.context.view_layer.update()
    top = max((mesh.matrix_world @ v.co).z for v in mesh.data.vertices)
    J = people._joints(arm)
    if c.get('shell'):
        if c.get('child'): _cut_ponytail(arm, mesh)
        h = dict(c['shell']); h['hem'] = J['Bip01 Neck'].z + h['hem']
        people.hair_shell(arm, mesh, **h)
    if c['who'] == 'cooper': _suit_kit(arm, mesh)
    for ca in list(mesh.data.color_attributes): mesh.data.color_attributes.remove(ca)
    s = c['height'] / top
    arm.scale = arm.scale * s; arm.location = (arm.location.x, arm.location.y, arm.location.z * s)
    bpy.context.view_layer.update()
    return arm, mesh


def _cut_ponytail(arm, mesh):
    """The avatar's ponytail (modelled, behind the head and down the nape): gone, the long wet hair is cards."""
    import bmesh
    J = people._joints(arm); hd, nk = J['Bip01 Head'], J['Bip01 Neck']
    bm = bmesh.new(); bm.from_mesh(mesh.data); W_ = mesh.matrix_world
    head_mat = next(i for i, s in enumerate(mesh.material_slots) if s.material and 'head' in s.material.name)
    dead = [f for f in bm.faces if f.material_index == head_mat and (W_ @ f.calc_center_median()).y > hd.y + 0.075 and (W_ @ f.calc_center_median()).z < hd.z + 0.06]
    bmesh.ops.delete(bm, geom=dead, context='FACES'); bm.to_mesh(mesh.data); bm.free(); mesh.data.update()
    cine.log('ponytail cut', len(dead), 'faces')


def _skinned(mesh, bm, bone, mats, name):
    """Geometry made at the rest pose, skinned wholly to one bone and joined into the body."""
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(name, me); [cl.objects.link(ob) for cl in mesh.users_collection]
    for m in mats: me.materials.append(m)
    me.transform(mesh.matrix_world.inverted()); ob.matrix_world = mesh.matrix_world.copy()
    vg = ob.vertex_groups.new(name=bone); vg.add(list(range(len(me.vertices))), 1.0, 'REPLACE')
    people._joined(mesh, ob)


def _suit_kit(arm, mesh):
    """The Endurance suit's helmet (a white shell round the head, open over the face where its visor would be, two
    lamps at the temples), the black neck ring it locks to, and the pack on his back."""
    import bmesh
    white = cine.material('suit_helmet', (0.8, 0.8, 0.78), rough=0.35, coat=0.6)
    dark = cine.material('suit_ring', (0.05, 0.05, 0.055), rough=0.4, metal=0.4)
    lamp = cine.material('suit_lamp', (1.0, 0.95, 0.85), rough=0.3, emission=(1.0, 0.95, 0.85), emission_strength=4.0)
    J = people._joints(arm); hd, nk = J['Bip01 Head'], J['Bip01 Neck']
    c = hd + Vector((0, -0.01, 0.07)); r = 0.175; fwd = Vector((0, -1, 0))
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=24, radius=r)
    for v in bm.verts: v.co = c + Vector((v.co.x, v.co.y * 1.06, v.co.z * 1.04))
    dead = [f for f in bm.faces if (f.calc_center_median() - c).normalized().dot(fwd) > 0.42 and f.calc_center_median().z > c.z - 0.12]
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    dead = [f for f in bm.faces if f.calc_center_median().z < nk.z + 0.03]
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.012)
    _skinned(mesh, bm, 'Bip01 Head', [white], 'helmet')
    bm = bmesh.new()
    for s in (-1, 1):                                                           # the lamps at its temples
        p = c + Vector((s * 0.15, -0.08, 0.03)); bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=0.018, matrix=Matrix.Translation(p))
    _skinned(mesh, bm, 'Bip01 Head', [lamp], 'helmet_lamps')
    bm = bmesh.new(); n = 32; zr = nk.z + 0.02
    rings = [[bm.verts.new(Vector((nk.x, nk.y, 0)) + Vector((math.cos(2 * math.pi * i / n) * rr, math.sin(2 * math.pi * i / n) * rr * 1.1, z))) for i in range(n)]
             for rr, z in ((0.1, zr + 0.03), (0.125, zr + 0.02), (0.13, zr - 0.02), (0.11, zr - 0.04))]
    for A, B in zip(rings, rings[1:]):
        for i in range(n): bm.faces.new((A[i], A[(i + 1) % n], B[(i + 1) % n], B[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    _skinned(mesh, bm, 'Bip01 Spine2', [dark], 'neck_ring')
    sp = J['Bip01 Spine2']; bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(Vector((sp.x, sp.y + 0.2, sp.z - 0.06))) @ Matrix.Diagonal((0.4, 0.17, 0.5, 1)))
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.03, segments=2, affect='EDGES')
    _skinned(mesh, bm, 'Bip01 Spine2', [white], 'suit_pack')
    cine.log('suit kit on cooper')


def _comb(arm, mesh):
    """A dark tortoiseshell comb in Murph's right hand, held as it rests (bound to the hand from then on)."""
    import bmesh
    shell = cine.material('comb', (0.12, 0.06, 0.03), rough=0.25, coat=0.8)
    pb = arm.pose.bones['Bip01 R Hand']; H = people._world(arm, pb).translation; palm = people._palm(arm, 'R')
    fing = (people._world(arm, arm.pose.bones['Bip01 R Finger2']).translation - H).normalized()
    side = palm.cross(fing).normalized()
    c = H + fing * 0.06 * S_ + palm * 0.012 * S_
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(c) @ Matrix((list(side) + [0], list(fing) + [0], list(palm) + [0], [0, 0, 0, 1])).transposed() @ Matrix.Diagonal((0.045 * S_, 0.15 * S_, 0.006 * S_, 1)))
    A = arm.matrix_world
    bm.transform(mesh.matrix_world.inverted() @ A @ pb.bone.matrix_local @ pb.matrix.inverted() @ A.inverted())
    me = bpy.data.meshes.new('comb'); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new('comb', me); [cl.objects.link(ob) for cl in mesh.users_collection]; me.materials.append(shell)
    ob.matrix_world = mesh.matrix_world.copy()
    vg = ob.vertex_groups.new(name='Bip01 R Hand'); vg.add(list(range(len(me.vertices))), 1.0, 'REPLACE')
    people._joined(mesh, ob)


S_ = 1.0


def cast(col, args):
    """Load, dress, shape and place them, and bake their acts (cached: retargets and IK take minutes); the room's rig
    made fresh after (it follows their hands)."""
    full = bool(args.get('full'))
    spec = {'cast': CAST, 'bases': BASES, 'work': WORK, 'cue': CUE, 'tl': TL, 'seat': [SEAT_Z, MURPH_F, list(R.SEAT)], 'home': COOP_HOME,
            'cooper': list(COOPER_AT), 'full': full, 'v': 5}
    for c in CAST:
        c['work'] = WORK[c['who']]; c['idles'] = {'scene': (None, 1.0 if c['who'] == 'murph' else 0.0)}; c['cue'] = CUE.get(c['who'], {})
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
    places = {'murph': (tuple(R.SEAT), MURPH_F), 'coop': COOP_HOME, 'cooper': ((COOPER_AT.x, COOPER_AT.y), (-1.0, 0.0))}
    for c in CAST:
        arm, mesh = make_person(c, col)
        at, f = places[c['who']]
        base, frames = _place(c, arm, at, f, BASES[c['who']])
        made[c['who']] = dict(c=c, arm=arm, mesh=mesh, base=base, frames=frames, k=c['height'] / 1.78)
        seated.append((c, arm, mesh))
    acts = {k: {} for k in made}
    for m in made.values(): m['mesh'].hide_viewport = True
    _murph_acts(made['murph'], acts['murph'], full)
    _coop_acts(made['coop'], acts['coop'], full)
    _cooper_acts(made['cooper'], acts['cooper'], full)
    for who, m in made.items():
        m['c']['acts'] = acts[who]
        if m['base'] not in acts[who].values(): bpy.data.actions.remove(m['base'])
        m['mesh'].hide_viewport = False
        people.pose_at(m['arm'], acts[who][m['c']['work'][0]], int(m['frames'][0]) + 10)
    return seated


# ---------------------------------------------------------------- the scene's clock (seconds into Murph's `scene`)
TL = dict(push=1.3, fall=1.9, startle=2.15, stand=4.2, nb_grab=4.6, walk1=7.9, note=14.0,
          coop_go=2.6, door=6.4, door_open=(6.9, 8.0), enter=8.0,
          crouch1=14.6, lander_grab=17.8, rise1=18.4, lander_put=24.0, crouch2=24.8, books_grab=28.2, rise2=28.6, books_put=33.0,
          talk=33.8, murph_back=38.0, sit=43.8, nb_put=48.9, lie=49.4, cry=51.0,
          coop_bed=42.6, coop_sit=50.6, console=53.8, coop_up=63.0, coop_door=66.0, stay=71.2, coop_stop=72.2,
          coop_out=79.0, door_close=(82.6, 84.0), coop_home=86.5,
          murph_up=84.5, m_stand=86.7, m_walk=90.4, m_crouch=95.7, m_grab=98.5, m_rise=98.9, m_put=103.0, m_back=103.6, m_sit=108.8,
          comb=113.6, end=115.6)
NB_REST = Vector((-0.98, -2.15, R.BED_TOP + 0.015))          # Murph's notebook, on the bed beside her
LIE_P = Vector((-1.3, -2.52, R.BED_TOP + 0.13))              # her pelvis, lying on her side, curled, her head on the pillow
COOP_SIT = ((-0.6, -2.95), (0.8, -0.6))                      # Cooper on the bed's edge by her shoulders
FALL_SPOTS = [Vector(p) for p in ((0.62, 2.0, 0.0), (0.38, 2.28, 0.0), (0.7, 2.46, 0.0), (0.46, 2.62, 0.0), (0.24, 1.98, 0.0))]
LANDER_SPOTS = [Vector((0.5, 2.18, 0.0)), Vector((0.3, 2.42, 0.0))]
STAY_SPOT = Vector((0.58, 1.18, 0.0))
SPOTS = dict(murph_shelf=(0.0, 1.46), coop_crouch=(0.0, 2.26), coop_door=(-4.28, -0.18), coop_in=(-2.9, -0.1), murph_book=(0.16, 1.0))
HEADS = {}                                                     # who -> {frame: head position} in the scene (for looks)


def _sit_lift(arm, m, w=1.0):
    """On the bed, higher than the clip's chair: the body raised onto it by w."""
    if w > 0: people.shift_root(arm, (0, 0, m['lift'] * w))


def _at(arm, src, f, p, h):
    hh, pp = people.heading(arm, src, f); return people.carry(pp, hh, Vector((p[0], p[1], 0)), Vector((h[0], h[1], 0)).normalized())


def _record(who, arm, f, hands=True):
    HEADS.setdefault(who, {})[f] = people._world(arm, arm.pose.bones['Bip01 Head']).translation.copy()
    if hands: HANDS.setdefault(who, {})[f] = tuple(people._world(arm, arm.pose.bones[f'Bip01 {s} Hand']).copy() for s in 'LR')


# ---------------------------------------------------------------- Murph
def _comb_pose(arm, m, t, w=1.0, speed=1.0):
    """Combing her long wet hair down on the right side: the comb from the crown down past the shoulder, again and
    again, her head tipped toward it; the left hand on the bed beside her."""
    if w <= 0: return
    pel, fwd, right, up = _live(arm); k = m['k']
    H = people._world(arm, arm.pose.bones['Bip01 Head']).translation
    T_ = 2.6 / speed; u = (t % T_) / T_
    s = _smooth(u / 0.62) if u < 0.62 else 1 - _smooth((u - 0.62) / 0.38)       # down the hair, then back up to the crown
    top = H + up * 0.1 * k + right * 0.05 * k - fwd * 0.02 * k
    low = H - up * 0.3 * k + right * 0.13 * k + fwd * 0.06 * k
    g = top.lerp(low, s) + fwd * 0.05 * k * (1 - s) * (1 - s) * (u > 0.62)
    _hand_to(arm, 'R', g, w, g + right * 0.35 * k - up * 0.25 * k - fwd * 0.1 * k, palm=-(right * 0.6 + up * 0.2 - fwd * 0.2), pw=0.7)
    people.bend(arm, 'Bip01 Head', fwd, 0.16 * w); people.bend(arm, 'Bip01 Neck', fwd, 0.06 * w)
    bed = pel - right * 0.2 * k + fwd * 0.05 * k; bed.z = R.BED_TOP + 0.02
    _hand_to(arm, 'L', bed, w, bed - right * 0.3 * k + up * 0.2 * k, palm=-up, pw=0.6)


def _murph_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS
    people.pose_at(arm, base, frames[0])
    pz = people._world(arm, arm.pose.bones['Bip01 Pelvis']).translation.z
    m['lift'] = (SEAT_Z + 0.07 * k) - pz
    cine.log(f'murph on the bed: pelvis {pz:.3f}, lifted {m["lift"]:+.3f}')

    def comb(f, t):
        _sit_lift(arm, m); _comb_pose(arm, m, t)
    acts['comb'] = people.custom_act(arm, base, frames, 'murph_comb', comb, _all(arm, fingers=True))
    people.pose_at(arm, acts['comb'], frames[0]); _comb(arm, m['mesh'])
    if not full: return
    walk, wf, vs = people.retarget(arm, 'f_walk_slow_01', inplace=True, cycles=12, action_name='murph_src_walk')
    idle, idf, _ = people.retarget(arm, 'f_idle_neutral_01', cycles=10, action_name='murph_src_idle')
    up_, uf, _ = people.retarget(arm, 'f_sit_stand_up_chair_01', action_name='murph_src_up')
    down, df, _ = people.retarget(arm, 'f_sit_down_chair_01', action_name='murph_src_down')
    note, nf, _ = people.retarget(arm, 'f_documents_note', cycles=3, action_name='murph_src_note')
    talk, tf, _ = people.retarget(arm, 'f_gestic_talk_sad_01', cycles=2, action_name='murph_src_talk')
    cin, cif, _ = people.retarget(arm, 'f_crouch_in', action_name='murph_src_cin')
    cid, cidf, _ = people.retarget(arm, 'f_crouch_idle', cycles=4, action_name='murph_src_cidle')
    cout, cof, _ = people.retarget(arm, 'f_crouch_out', action_name='murph_src_cout')
    cine.log(f'murph walks at {vs:.2f} m/s')
    seat = Vector((R.SEAT.x, R.SEAT.y)); F0 = Vector(MURPH_F).normalized()
    # where she stands once up (the clip rises forward of the seat), then her walks
    p_up = seat + F0 * 0.28
    shelf = Vector(SPOTS['murph_shelf']); h_shelf = (1.0, 0.45)
    r1 = people.path([p_up, Vector((0.05, -1.4)), Vector((-0.1, 0.4)), shelf])
    r2 = people.path([shelf, Vector((-0.15, 0.0)), Vector((0.0, -1.5)), p_up])
    book = Vector(SPOTS['murph_book'])
    r3 = people.path([p_up, Vector((0.12, -1.2)), book])
    r4 = people.path([book, Vector((0.12, -1.2)), p_up])
    T = TL; segs = []

    def add(tag, **kw): kw['tag'] = tag; segs.append(kw)
    def pad(tag, until, **kw):
        t = sum(s['dur'] for s in segs); kw['dur'] = max(0.4, until - t); add(tag, **kw)
    I = Matrix.Identity(4)
    pad('comb', T['stand'], src=base, f0=frames[0], at=I)
    add('stand', src=up_, f0=uf[0], dur=(uf[1] - uf[0]) / FPS, at=_at(arm, up_, uf[0], seat, F0), blend=0.6)
    pad('turn', T['walk1'], src=idle, f0=idf[0], at=_at(arm, idle, idf[0], p_up, (0.5, 0.86)), blend=0.8)
    add('walk1', src=walk, f0=wf[0], dur=r1[1] / vs, at=people.walk_along(arm, walk, wf[0], vs, r1), blend=0.7)
    pad('look', T['note'], src=idle, f0=idf[0] + 30, at=_at(arm, idle, idf[0] + 30, shelf, h_shelf), blend=0.7)
    pad('note', T['talk'] - 0.2, src=note, f0=nf[0], at=_at(arm, note, nf[0], shelf, h_shelf), blend=0.8)
    pad('talk', T['murph_back'], src=talk, f0=tf[0], at=_at(arm, talk, tf[0], shelf, (0.0, 1.0)), blend=0.8)
    add('walk2', src=walk, f0=wf[0] + 10, dur=r2[1] / vs, at=people.walk_along(arm, walk, wf[0] + 10, vs, r2), blend=0.7)
    pad('arrive', T['sit'], src=idle, f0=idf[0] + 60, at=_at(arm, idle, idf[0] + 60, p_up, -F0), blend=0.8)
    add('sit', src=down, f0=df[0], dur=(df[1] - df[0]) / FPS, at=_at(arm, down, df[1], seat, F0), blend=0.6)
    pad('sat', T['lie'], src=base, f0=frames[0] + 20, at=I, blend=0.6)
    pad('lie', T['murph_up'], src=base, f0=frames[0] + 40, at=I, blend=0.3)
    pad('situp', T['m_stand'], src=base, f0=frames[0] + 60, at=I, blend=0.3)
    add('stand2', src=up_, f0=uf[0], dur=(uf[1] - uf[0]) / FPS, at=_at(arm, up_, uf[0], seat, F0), blend=0.6)
    pad('turn2', T['m_walk'], src=idle, f0=idf[0] + 90, at=_at(arm, idle, idf[0] + 90, p_up, (0.3, 0.95)), blend=0.8)
    add('walk3', src=walk, f0=wf[0] + 20, dur=r3[1] / vs, at=people.walk_along(arm, walk, wf[0] + 20, vs, r3), blend=0.7)
    pad('to_book', T['m_crouch'], src=idle, f0=idf[0] + 120, at=_at(arm, idle, idf[0] + 120, book, (1.0, 0.2)), blend=0.6)
    add('crouch', src=cin, f0=cif[0], dur=(cif[1] - cif[0]) / FPS, at=_at(arm, cin, cif[0], book, (1.0, 0.2)), blend=0.5)
    pad('down', T['m_rise'], src=cid, f0=cidf[0], at=_at(arm, cid, cidf[0], book, (1.0, 0.2)), blend=0.4)
    add('rise', src=cout, f0=cof[0], dur=(cof[1] - cof[0]) / FPS, at=_at(arm, cout, cof[0], book, (1.0, 0.2)), blend=0.4)
    pad('shelve', T['m_back'], src=idle, f0=idf[0] + 150, at=_at(arm, idle, idf[0] + 150, book, (1.0, 0.2)), blend=0.6)
    add('walk4', src=walk, f0=wf[0] + 30, dur=r4[1] / vs, at=people.walk_along(arm, walk, wf[0] + 30, vs, r4), blend=0.7)
    pad('arrive2', T['m_sit'], src=idle, f0=idf[0] + 60, at=_at(arm, idle, idf[0] + 60, p_up, -F0), blend=0.8)
    add('sit2', src=down, f0=df[0], dur=(df[1] - df[0]) / FPS, at=_at(arm, down, df[1], seat, F0), blend=0.6)
    pad('combs', T['end'], src=base, f0=frames[0], at=I, blend=0.8)
    t0 = {}; t = 0.0
    for sg in segs: t0[sg['tag']] = t; sg['t0'] = t; t += sg['dur']
    cine.log('murph scene: ' + ', '.join(f"{sg['tag']} {sg['t0']:.1f}" for sg in segs) + f' end {t:.1f}')
    rb = RIG['books']; stay = rb['stay'][0]; stay_home = Vector((R.SHELF_X + 0.015 + stay[3] / 2, (stay[0] + stay[1]) / 2, rb['stay_z'] + stay[2] / 2))
    fall_c = Vector((R.SHELF_X, (R.BAYS[R.FALL_BAY][0] + R.BAYS[R.FALL_BAY][1]) / 2, 1.2))

    def overlay(tt, i, lt):
        sg = segs[i]; tag = sg['tag']; f = int(round(tt * FPS))
        pel, fwd, right, up = _live(arm)
        seatedw = {'comb': 1.0, 'sat': 1.0, 'lie': 1.0, 'situp': 1.0, 'combs': 1.0, 'stand': 1 - _smooth(lt / 1.2), 'stand2': 1 - _smooth(lt / 1.2),
                   'sit': _smooth((lt - 0.6) / 1.4), 'sit2': _smooth((lt - 0.6) / 1.4)}.get(tag, 0.0)
        _sit_lift(arm, m, seatedw)
        if tag == 'comb':
            stop = _smooth((tt - T['startle']) / 0.35)
            _comb_pose(arm, m, tt, w=1 - stop)
            _look(arm, fall_c, _smooth((tt - T['startle']) / 0.3))                         # startled: her head snaps round to the shelf
            if tt > T['startle']: people.bend(arm, 'Bip01 Spine2', up, 0.25 * _smooth((tt - T['startle']) / 0.6))
        elif tag in ('stand', 'turn'):
            _look(arm, fall_c, 0.8)
            if tt < T['nb_grab'] + 0.3:                                                     # the notebook off the bed beside her
                _hand_to(arm, 'L', NB_REST + Vector((0, 0, 0.02)), _win(tt, T['nb_grab'] - 0.5, T['nb_grab'] + 0.1, 0.4, 0.4), NB_REST + up * 0.3 - right * 0.3)
        elif tag in ('walk1', 'look'):
            _look(arm, fall_c, 0.6)
        elif tag == 'note':
            _look(arm, fall_c + Vector((0, 0, 0.1)) if (lt % 6) < 3.5 else fall_c - Vector((0, 0, 0.6)), 0.5)
        elif tag == 'talk':
            _look(arm, HEADS.get('coop', {}).get(f, fall_c), 0.7)
        elif tag in ('sat', 'lie', 'situp'):
            if tag == 'lie' or (tag == 'sat' and lt > sg['dur'] - 0.01): pass
            w = _smooth(lt / 2.0) if tag == 'lie' else (1 - _smooth(lt / 1.8) if tag == 'situp' else 0.0)
            if tag == 'lie' and tt > T['murph_up']: w = 1.0
            if w > 0: _lie(arm, m, w, tt, crying=tag == 'lie')
            if tag == 'sat' and tt < T['nb_put'] + 0.4:                                    # the notebook down on the bed
                _hand_to(arm, 'L', NB_REST + Vector((0, 0, 0.02)), _win(tt, T['nb_put'] - 0.6, T['nb_put'] + 0.1, 0.5, 0.4), NB_REST + up * 0.3 - right * 0.3)
        elif tag in ('crouch', 'down', 'rise'):
            spot = STAY_SPOT + Vector((0, 0, 0.03))
            if tt < T['m_grab'] + 0.1: _hand_to(arm, 'R', spot, _win(tt, T['m_grab'] - 0.8, T['m_grab'] + 0.2, 0.5, 0.1), spot + up * 0.3 + right * 0.3)
            else: _hand_to(arm, 'R', pel + fwd * 0.28 * k + up * 0.25 * k + right * 0.1 * k, 1.0, pel + right * 0.4 * k)
            _look(arm, spot, 0.6)
        elif tag == 'shelve':
            gap = stay_home - Vector((0.06, 0, 0))
            e = _smooth(lt / 0.9)
            held = pel + fwd * 0.28 * k + up * 0.25 * k + right * 0.1 * k
            _hand_to(arm, 'R', held.lerp(gap, e) if tt < T['m_put'] else gap.lerp(held, _smooth((tt - T['m_put']) / 0.5)), 1.0, gap + right * 0.4 - up * 0.3, palm=-fwd + right, pw=0.6)
            _look(arm, stay_home, 0.7)
        elif tag in ('arrive2', 'sit2', 'combs'):
            w = _smooth((tt - T['comb']) / 1.2)
            if tag == 'combs': _comb_pose(arm, m, tt, w=w)
        _record('murph', arm, f)
    acts['scene'] = people.sequence(arm, base, 'murph_scene', segs, overlay=overlay)
    for a in (walk, idle, up_, down, note, talk, cin, cid, cout): bpy.data.actions.remove(a)
    m['scene_n'] = int(acts['scene'].frame_range[1] - acts['scene'].frame_range[0])


def _lie(arm, m, w, t, crying=False):
    """From sitting on the bed's side to lying on her side, curled, her head on the pillow, facing the shelf (+x): the
    sitting pose turned to face +x, laid over about +x (her spine along -y), moved onto the mattress; crying: her
    shoulders shaking, her hands at her face."""
    pel, fwd, right, up = _live(arm); k = m['k']
    a0 = math.atan2(fwd.y, fwd.x)
    _turn_root(arm, pel, (0, 0, 1), -a0 * w)
    pel2 = people._world(arm, arm.pose.bones['Bip01 Pelvis']).translation.copy()
    people.shift_root(arm, (LIE_P - pel2) * w)
    _turn_root(arm, LIE_P.lerp(pel2, 1 - w), (1, 0, 0), math.radians(88) * w)
    pel, fwd, right, up = _live(arm)
    if crying and w > 0.9:
        e = _win(t, TL['cry'] - 1.0, TL['murph_up'] - 0.8, 1.0, 0.8)
        sob = math.sin(2 * math.pi * t * 1.6) * 0.04 * e * (0.6 + 0.4 * math.sin(t * 0.7))
        people.bend(arm, 'Bip01 Spine2', Vector((1, 0, 0)), sob); people.bend(arm, 'Bip01 Spine1', Vector((1, 0, 0)), -sob * 0.5)
        H = people._world(arm, arm.pose.bones['Bip01 Head']).translation
        for s in 'LR':
            g = H + Vector((0.07, -0.04 if s == 'L' else 0.04, -0.04))
            _hand_to(arm, s, g, e * 0.9, g + Vector((0.2, 0, -0.3)))
        people.bend(arm, 'Bip01 Head', Vector((0, 1, 0)), 0.25 * e)


# ---------------------------------------------------------------- Cooper at the door
def _coop_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS
    table = Vector((R.LEFT + 0.18, 2.6, 0.8))

    def wait(f, t):
        pel, fwd, right, up = _live(arm)
        for b_, a in zip(SPINE, (0.1, 0.08, 0.06)): people.bend(arm, b_, right, -a)       # leaning on the landing's table
        for side, sd in (('L', -1), ('R', 1)):
            g = table + right * sd * 0.2 * k + Vector((0, 0, 0.04))
            _hand_to(arm, side, g, 0.9, g + right * sd * 0.4 + up * 0.3, palm=-up, pw=0.7)
        _look(arm, table + Vector((0, 0.1 * math.sin(t * 0.3), 0)), 0.5)
    acts['wait'] = people.custom_act(arm, base, frames, 'coop_wait', wait, _all(arm))
    if not full: return
    walk, wf, vs = people.retarget(arm, 'm_walk_slow_01', inplace=True, cycles=14, action_name='coop_src_walk')
    idle, idf, _ = people.retarget(arm, 'm_idle_neutral_01', cycles=10, action_name='coop_src_idle')
    door, dof, _ = people.retarget(arm, 'm_try_door_inwards', action_name='coop_src_door')
    cin, cif, _ = people.retarget(arm, 'm_crouch_in', action_name='coop_src_cin')
    cid, cidf, _ = people.retarget(arm, 'm_crouch_idle', cycles=4, action_name='coop_src_cidle')
    cout, cof, _ = people.retarget(arm, 'm_crouch_out', action_name='coop_src_cout')
    talk, tf, _ = people.retarget(arm, 'm_gestic_talk_sad_01', cycles=2, action_name='coop_src_talk')
    down, df, _ = people.retarget(arm, 'm_sit_down_chair_01', action_name='coop_src_down')
    sitb, sbf, _ = people.retarget(arm, 'm_sit_chair_breathe_01', cycles=4, action_name='coop_src_sit')
    upc, uf, _ = people.retarget(arm, 'm_sit_stand_up_chair_01', action_name='coop_src_up')
    turn, trf, _ = people.retarget(arm, 'm_turn_left_180', action_name='coop_src_turn')
    home, hf = Vector(COOP_HOME[0]), Vector(COOP_HOME[1])
    dpt = Vector(SPOTS['coop_door']); din = Vector(SPOTS['coop_in']); cr = Vector(SPOTS['coop_crouch'])
    sit_p, sit_f = Vector(COOP_SIT[0]), Vector(COOP_SIT[1]).normalized()
    stand_p = sit_p + sit_f * 0.32
    r_hall = people.path([home, Vector((-4.3, 1.8)), Vector((-4.32, 0.6)), dpt])
    r_in = people.path([dpt, Vector((-3.6, -0.18)), din, Vector((-1.6, 0.8)), cr - Vector((0.1, 0.0))])
    r_bed = people.path([cr, Vector((-0.2, 0.9)), Vector((-0.1, -1.4)), stand_p])
    r_door = people.path([stand_p, Vector((-0.6, -1.8)), Vector((-2.2, -0.5)), din, Vector((-3.55, -0.18))])
    r_out = people.path([Vector((-3.55, -0.18)), dpt, Vector((-4.3, 0.6)), Vector((-4.3, 2.0)), home])
    T = TL; segs = []; I = Matrix.Identity(4)

    def add(tag, **kw): kw['tag'] = tag; segs.append(kw)
    def pad(tag, until, **kw):
        t = sum(s['dur'] for s in segs); kw['dur'] = max(0.4, until - t); add(tag, **kw)
    pad('wait', T['coop_go'], src=base, f0=frames[0], at=I)
    add('hall', src=walk, f0=wf[0], dur=r_hall[1] / vs, at=people.walk_along(arm, walk, wf[0], vs, r_hall), blend=0.8)
    pad('at_door', T['door'], src=idle, f0=idf[0], at=_at(arm, idle, idf[0], dpt, (1, 0)), blend=0.6)
    pad('door', T['enter'], src=door, f0=dof[0], at=_at(arm, door, dof[0], dpt, (1, 0)), blend=0.5)
    add('in', src=walk, f0=wf[0] + 10, dur=r_in[1] / vs, at=people.walk_along(arm, walk, wf[0] + 10, vs, r_in), blend=0.6)
    pad('look', T['crouch1'], src=idle, f0=idf[0] + 30, at=_at(arm, idle, idf[0] + 30, cr, (1, 0.1)), blend=0.6)
    add('crouch1', src=cin, f0=cif[0], dur=(cif[1] - cif[0]) / FPS / 1.6, rate=1.6, at=_at(arm, cin, cif[0], cr, (1, 0.1)), blend=0.5)
    pad('down1', T['rise1'], src=cid, f0=cidf[0], at=_at(arm, cid, cidf[0], cr, (1, 0.1)), blend=0.4)
    add('rise1', src=cout, f0=cof[0], dur=(cof[1] - cof[0]) / FPS / 1.6, rate=1.6, at=_at(arm, cout, cof[0], cr, (1, 0.1)), blend=0.4)
    pad('show', T['lander_put'] - 1.0, src=talk, f0=tf[0], at=_at(arm, talk, tf[0], cr, (0.2, -1)), blend=0.8)
    pad('put1', T['crouch2'], src=idle, f0=idf[0] + 60, at=_at(arm, idle, idf[0] + 60, cr, (1, 0.1)), blend=0.6)
    add('crouch2', src=cin, f0=cif[0], dur=(cif[1] - cif[0]) / FPS / 1.6, rate=1.6, at=_at(arm, cin, cif[0], cr, (1, 0.1)), blend=0.5)
    pad('down2', T['rise2'], src=cid, f0=cidf[0] + 20, at=_at(arm, cid, cidf[0] + 20, cr, (1, 0.1)), blend=0.4)
    add('rise2', src=cout, f0=cof[0], dur=(cof[1] - cof[0]) / FPS / 1.6, rate=1.6, at=_at(arm, cout, cof[0], cr, (1, 0.1)), blend=0.4)
    pad('put2', T['talk'], src=idle, f0=idf[0] + 90, at=_at(arm, idle, idf[0] + 90, cr, (1, 0.1)), blend=0.6)
    pad('talk', T['coop_bed'], src=talk, f0=tf[0] + 40, at=_at(arm, talk, tf[0] + 40, cr, (-0.2, -1)), blend=0.8)
    add('bed', src=walk, f0=wf[0] + 20, dur=r_bed[1] / vs, at=people.walk_along(arm, walk, wf[0] + 20, vs, r_bed), blend=0.7)
    pad('stand_by', T['coop_sit'], src=idle, f0=idf[0] + 120, at=_at(arm, idle, idf[0] + 120, stand_p, -sit_f), blend=0.7)
    add('sit', src=down, f0=df[0], dur=(df[1] - df[0]) / FPS, at=_at(arm, down, df[1], sit_p, sit_f), blend=0.6)
    pad('console', T['coop_up'], src=sitb, f0=sbf[0], at=_at(arm, sitb, sbf[0], sit_p, sit_f), blend=0.6)
    add('up', src=upc, f0=uf[0], dur=(uf[1] - uf[0]) / FPS, at=_at(arm, upc, uf[0], sit_p, sit_f), blend=0.6)
    pad('pause', T['coop_door'], src=idle, f0=idf[0] + 150, at=_at(arm, idle, idf[0] + 150, stand_p, (-0.7, 0.7)), blend=0.7)
    add('to_door', src=walk, f0=wf[0] + 30, dur=r_door[1] / vs, at=people.walk_along(arm, walk, wf[0] + 30, vs, r_door), blend=0.7)
    pad('stop', T['coop_stop'] + 0.2, src=idle, f0=idf[0] + 180, at=_at(arm, idle, idf[0] + 180, Vector((-3.55, -0.18)), (-1, 0)), blend=0.5)
    add('turn', src=turn, f0=trf[0], dur=(trf[1] - trf[0]) / FPS, at=_at(arm, turn, trf[0], Vector((-3.55, -0.18)), (-1, 0)), blend=0.5)
    pad('linger', T['coop_out'], src=idle, f0=idf[0] + 210, at=_at(arm, idle, idf[0] + 210, Vector((-3.55, -0.18)), (1, 0.35)), blend=0.6)
    add('turn2', src=turn, f0=trf[0], dur=(trf[1] - trf[0]) / FPS, at=_at(arm, turn, trf[0], Vector((-3.55, -0.18)), (1, 0.35)), blend=0.5)
    add('out', src=walk, f0=wf[0] + 40, dur=r_out[1] / vs, at=people.walk_along(arm, walk, wf[0] + 40, vs, r_out), blend=0.6)
    pad('home', TL['end'], src=base, f0=frames[0] + 30, at=I, blend=0.9)
    t = 0.0
    for sg in segs: sg['t0'] = t; t += sg['dur']
    cine.log('coop scene: ' + ', '.join(f"{sg['tag']} {sg['t0']:.1f}" for sg in segs) + f' end {t:.1f}')
    rb = RIG['books']; lander_home = Vector((R.SHELF_X + 0.13, sum(rb['lander']) / 2, rb['fall_z'] + 0.06))
    books_home = Vector((R.SHELF_X + 0.1, (rb['falls'][0][0] + rb['falls'][-1][1]) / 2, rb['fall_z'] + 0.12))
    murph = lambda f: HEADS.get('murph', {}).get(f, Vector((0, 1.4, 1.2)))

    def overlay(tt, i, lt):
        sg = segs[i]; tag = sg['tag']; f = int(round(tt * FPS))
        pel, fwd, right, up = _live(arm)
        if tag in ('down1', 'crouch1', 'rise1'):
            for side, spot in (('L', LANDER_SPOTS[1]), ('R', LANDER_SPOTS[0])):
                tgt = spot + Vector((0, 0, 0.05))
                if tt < T['lander_grab'] + 0.1: _hand_to(arm, side, tgt, _win(tt, T['lander_grab'] - 0.7, T['lander_grab'] + 0.2, 0.5, 0.1), tgt + up * 0.4 + right * (0.3 if side == 'R' else -0.3))
                else: _hand_to(arm, side, pel + fwd * 0.3 * k + up * 0.25 * k + right * (0.08 if side == 'R' else -0.08) * k, 1.0, pel + right * (0.4 if side == 'R' else -0.4))
            _look(arm, LANDER_SPOTS[0], 0.6)
        elif tag in ('show', 'put1'):
            held = pel + fwd * 0.32 * k + up * 0.42 * k
            if tag == 'show': tgt = held; _look(arm, held.lerp(murph(f), 0.5 + 0.5 * math.sin(lt * 0.8)), 0.6)
            else: tgt = held.lerp(lander_home - Vector((0.08, 0, 0)), _smooth(lt / 0.8)) if tt < T['lander_put'] else (lander_home - Vector((0.08, 0, 0))).lerp(held - up * 0.3, _smooth((tt - T['lander_put']) / 0.5)); _look(arm, lander_home, 0.6)
            for side, sd in (('L', -1), ('R', 1)):
                _hand_to(arm, side, tgt + right * sd * 0.07 * k, 1.0, tgt + right * sd * 0.4 - up * 0.3, palm=up * 0.6 - right * sd, pw=0.6)
        elif tag in ('crouch2', 'down2', 'rise2'):
            stack = sum(FALL_SPOTS, Vector()) / len(FALL_SPOTS) + Vector((0, 0, 0.06))
            for side, sd in (('L', -1), ('R', 1)):
                tgt = stack + right * sd * 0.12
                if tt < T['books_grab'] + 0.1: _hand_to(arm, side, tgt, _win(tt, T['books_grab'] - 1.0, T['books_grab'] + 0.2, 0.5, 0.1), tgt + up * 0.4 + right * sd * 0.3)
                else: _hand_to(arm, side, pel + fwd * 0.3 * k + up * 0.25 * k + right * sd * 0.12 * k, 1.0, pel + right * sd * 0.4, palm=-right * sd, pw=0.7)
            _look(arm, stack, 0.6)
        elif tag == 'put2':
            held = pel + fwd * 0.3 * k + up * 0.3 * k
            gap = books_home - Vector((0.1, 0, 0))
            tgt = held.lerp(gap, _smooth(lt / 0.9)) if tt < T['books_put'] else gap.lerp(held - up * 0.3, _smooth((tt - T['books_put']) / 0.5))
            for side, sd in (('L', -1), ('R', 1)):
                _hand_to(arm, side, tgt + right * sd * 0.12 * k, 1.0, tgt + right * sd * 0.4 - up * 0.3, palm=-right * sd, pw=0.7)
            _look(arm, books_home, 0.6)
        elif tag in ('talk', 'show'):
            _look(arm, murph(f), 0.6)
        elif tag in ('stand_by',):
            _look(arm, LIE_P + Vector((0, -0.4, 0.15)), 0.7)
        elif tag in ('console', 'sit', 'up'):
            w = {'console': 1.0, 'sit': _smooth((lt - 0.6) / 1.4), 'up': 1 - _smooth(lt / 1.2)}[tag]
            people.shift_root(arm, (0, 0, m.get('lift', 0.0) * w))
            if tag == 'console':
                sh = LIE_P + Vector((0.05, -0.32, 0.12))                                       # her shoulder
                e = _win(tt, T['console'] - 0.8, T['coop_up'] - 0.6, 0.9, 0.8)
                people.bend(arm, 'Bip01 Spine1', up, 0.35 * e); people.bend(arm, 'Bip01 Spine2', up, 0.25 * e)
                _hand_to(arm, 'R', sh + Vector((0, 0, 0.04 + 0.01 * math.sin(lt * 2.4))), e, sh + Vector((0.3, -0.2, 0.3)), palm=Vector((0, 0, -1)), pw=0.7)
                _look(arm, LIE_P + Vector((0.0, -0.45, 0.2)), 0.8 * e)
        elif tag in ('stop', 'turn', 'linger'):
            if tag == 'linger':
                _look(arm, Vector((R.SHELF_X, 1.36, 1.5)) if lt < 2.5 else LIE_P + Vector((0, -0.4, 0.2)), 0.7)
        _record('coop', arm, f)
    # his seat on the bed: the clip's chair height to the bed's
    people.pose_at(arm, sitb, sbf[0]); pz = people._world(arm, arm.pose.bones['Bip01 Pelvis']).translation.z
    m['lift'] = (SEAT_Z + 0.09 * k) - pz
    acts['scene'] = people.sequence(arm, base, 'coop_scene', segs, overlay=overlay)
    for a in (walk, idle, door, cin, cid, cout, talk, down, sitb, upc, turn): bpy.data.actions.remove(a)


# ---------------------------------------------------------------- Cooper in the tesseract
def _float(arm, m, t):
    """Hanging in the tesseract at the backs of the books: raised off the lattice, a slow drift, his legs hanging bent,
    leaning to the shelf; his hands on its frame."""
    k = m['k']
    pel = people._world(arm, arm.pose.bones['Bip01 Pelvis']).translation
    want = COOPER_AT + Vector((0.015 * math.sin(t * 0.5), 0.03 * math.sin(t * 0.31), 0.025 * math.sin(t * 0.43)))
    people.shift_root(arm, want - pel)
    pel, fwd, right, up = _live(arm)
    for b_, a in zip(SPINE, (0.08, 0.06, 0.05)): people.bend(arm, b_, right, -a)
    for side, sd, dz, dx in (('L', -1, 0.82, 0.12), ('R', 1, 0.76, -0.14)):
        a = pel + right * sd * 0.11 * k - up * dz * k + fwd * dx * k
        people.ik_leg(arm, side, a, a + fwd * 0.5 + up * 0.3, keep_foot=False)


def _cooper_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS
    yb = COOPER_AT.y; xs = R.TX0 + 0.02
    frame_l, frame_r = Vector((xs, yb - 0.42, 1.55)), Vector((xs, yb + 0.44, 1.4))
    def holds(w=1.0):
        pel, fwd, right, up = _live(arm)
        for side, p in (('L', frame_l), ('R', frame_r)):
            _hand_to(arm, side, p, w, p + Vector((0.4, 0, -0.4)), palm=Vector((-1, 0, 0)), pw=0.6)

    def float_(f, t):
        _float(arm, m, t); holds(); _look(arm, Vector((0.0, 0.0, 1.2)), 0.4)
    acts['float'] = people.custom_act(arm, base, frames, 'cooper_float', float_, _all(arm))
    if not full: return
    n = int(round(TL['end'] * FPS))
    longb, lf, _ = people.retarget(arm, BASES['cooper'], cycles=40, limit=n + 10, action_name='cooper_src_long')
    rb = RIG['books']; fy = (rb['falls'][0][0] + rb['falls'][-1][1]) / 2
    books = Vector((R.TX0 - 0.03, fy, rb['fall_z'] + 0.14))
    stay = rb['stay'][0]; stay_p = Vector((R.TX0 - 0.02, (stay[0] + stay[1]) / 2, rb['stay_z'] + 0.14))
    T = TL

    def scene(f, t):
        _float(arm, m, t)
        pel, fwd, right, up = _live(arm)
        push = _win(t, T['push'] - 0.4, T['fall'] + 0.2, 0.35, 0.6)
        punch = _win(t, T['stay'] - 1.2, T['stay'] + 0.3, 0.9, 0.5)
        lean = _win(t, T['stay'] + 0.4, T['coop_out'] + 2.0, 1.2, 2.0)
        bang = _win(t, 56.0, 62.0, 1.0, 1.0)
        holds(1.0 - max(push, punch * 0.6))
        if push > 0:
            for side, sd in (('L', -1), ('R', 1)):
                tgt = books + Vector((0, sd * 0.13, 0)) + Vector((-0.12 * _smooth((t - T['push']) / 0.6), 0, 0))
                _hand_to(arm, side, tgt, push, tgt + Vector((0.5, sd * 0.2, -0.4)), palm=Vector((-1, 0, 0)), pw=0.8)
        if bang > 0:
            hit = 0.5 + 0.5 * math.sin(2 * math.pi * (t - 56.0) / 1.3)
            tgt = Vector((xs - 0.01 * hit, yb + 0.1, 1.55 + 0.08 * hit))
            _hand_to(arm, 'R', tgt, bang, tgt + Vector((0.45, 0.2, -0.3)), palm=Vector((-1, 0, 0)), pw=0.7)
        if punch > 0:
            back = _smooth((t - (T['stay'] - 1.2)) / 0.8) * (1 - _smooth((t - (T['stay'] - 0.25)) / 0.25))
            tgt = stay_p + Vector((0.32 * back - 0.08 * _smooth((t - (T['stay'] - 0.2)) / 0.2), 0, 0.05 * back))
            _hand_to(arm, 'R', tgt, punch, tgt + Vector((0.4, 0.25, -0.35)), palm=Vector((-1, 0, 0)), pw=0.6)
            people.hand_shape(arm, 'R', 'fist', punch)
            people.bend(arm, 'Bip01 Spine2', up, -0.25 * back * punch)
        if lean > 0:
            for b_, a in zip(SPINE, (0.12, 0.12, 0.1)): people.bend(arm, b_, right, -a * lean)
            people.bend(arm, 'Bip01 Head', right, -0.3 * lean)
            sob = math.sin(2 * math.pi * t * 1.3) * 0.03 * lean
            people.bend(arm, 'Bip01 Spine2', right, sob)
        tgt = HEADS.get('murph', {}).get(f, Vector((0, 0, 1.2)))
        if T['door'] < t < T['coop_out'] + 3 and (T['coop_door'] - 1 < t or t < T['talk']):
            tgt = HEADS.get('coop', {}).get(f, tgt) if (T['coop_door'] - 1 < t < T['coop_out'] + 3) else tgt
        _look(arm, tgt, 0.7 * (1 - lean * 0.7))
    acts['scene'] = people.custom_act(arm, longb, (lf[0], lf[0] + n), 'cooper_scene', scene, _all(arm, fingers=True))
    bpy.data.actions.remove(longb)


# ---------------------------------------------------------------- the room's rig
def _room_rig(seated, col):
    """The room's rig and its acts: at rest, and the scene (the books and the lander falling, carried and set back by
    the hands that hold them, the door opening and closing)."""
    import rooms.interstellar_rig as RG
    arm, mesh = RG.make_rig(RIG['books'], MATS, col)
    c = dict(who='room', work=WORK['room'], idles={'scene': (None, 0.0)}, cue={}, roam=())
    acts = {'rest': RG.rest_act(arm, 'room_rest')}
    FPS = people.FPS
    arms = {cc['who']: a for cc, a, me in seated}
    if 'scene' in next(cc for cc, a, me in seated if cc['who'] == 'murph')['acts']:
        n = int(round(TL['end'] * FPS))
        hands = {who: _hands_of(arms[who], next(cc for cc, a, me in seated if cc['who'] == who)['acts']['scene']) for who in ('murph', 'coop')}
        L = RG.Track(arm, n); rnd = random.Random(9)
        F = lambda s: int(round(s * FPS))
        for j in range(len(RIG['books']['falls'])):
            spot = FALL_SPOTS[j]; th = RIG['books']['falls'][j][1] - RIG['books']['falls'][j][0]
            RG.fall(L, f'book{j}', F(TL['fall']) + j * 2, spot + Vector((0, 0, th / 2)), rnd.uniform(-1.2, 1.2), rnd)
        for j, part in enumerate(('lander_a', 'lander_b')):
            RG.fall(L, part, F(TL['fall']) + 4 + j, LANDER_SPOTS[j], rnd.uniform(-2, 2), rnd, flat=False,
                    spin=Quaternion(Vector((0, 1, 0)), 1.4 if j else 0.0))
        RG.door(L, F(TL['door_open'][0]), F(TL['door_open'][1]), 0.0, math.radians(84))
        RG.door(L, F(TL['door_close'][0]), F(TL['door_close'][1]), math.radians(84), 0.0)
        hc = hands['coop']
        RG.carry(L, 'lander_a', F(TL['lander_grab']), F(TL['lander_put']), {f: h[0] for f, h in hc.items()})
        RG.carry(L, 'lander_b', F(TL['lander_grab']), F(TL['lander_put']), {f: h[1] for f, h in hc.items()})
        g0 = F(TL['books_grab']); mid = {f: Matrix.Translation((h[0].translation + h[1].translation) / 2) @ h[1].to_quaternion().to_matrix().to_4x4() for f, h in hc.items()}
        for j in range(len(RIG['books']['falls'])):                                # gathered into a stack between his hands
            p_floor, q_floor = L.get(f'book{j}', g0 - F(0.7))
            stack = mid[g0].translation + Vector((0, 0, 0.035 * j - 0.06))
            for i in range(F(0.7) + 1):
                u = _smooth(i / F(0.7)); L.set(f'book{j}', g0 - F(0.7) + i, p_floor.lerp(stack, u), q_floor.slerp(Quaternion(Vector((1, 0, 0)), math.pi / 2), u))
            RG.carry(L, f'book{j}', g0, F(TL['books_put']), mid, settle=0.5 + 0.06 * j)
        RG.fall(L, 'stay', F(TL['stay']), STAY_SPOT + Vector((0, 0, 0.02)), 0.6, rnd, push=0.3)
        RG.carry(L, 'stay', F(TL['m_grab']), F(TL['m_put']), {f: h[1] for f, h in hands['murph'].items()})
        acts['scene'] = L.key('room_scene')
    c['acts'] = acts
    return [(c, arm, mesh)]


def _hands_of(arm, act):
    """Both hands' world matrices at every frame of an act (frame 0 = its start)."""
    out = {}; f0 = int(act.frame_range[0])
    for f in range(f0, int(act.frame_range[1]) + 1):
        people.pose_at(arm, act, f)
        out[f - f0] = tuple(people._world(arm, arm.pose.bones[f'Bip01 {s} Hand']).copy() for s in 'LR')
    return out


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
    meta['live'] = _live_meta()
    stages.write_meta(WEB, meta)


def _live_meta():
    return {'held': [{'who': 'murph', 'act': 'scene', 'prop': 'notebook', 'hand': 'L', 'grab': TL['nb_grab'], 'release': TL['nb_put']}]}


def _export_people(seated):
    out = os.path.join(WEB, 'people'); os.makedirs(out, exist_ok=True); metas = []
    for c, arm, mesh in seated:
        pelvis = 'room_root' if c['who'] == 'room' else 'Bip01 Pelvis'
        people.export_person(arm, mesh, c['acts'], os.path.join(out, f"{c['who']}.glb"), roam=c.get('roam', ()), pelvis=pelvis)
        metas.append(person_meta(c))
    return metas


def _capture_meta():
    """How to light the people as the bake lit the room (three.js: y up, z = -Blender y): the lamp as a small bright
    sphere, the windows' evening, the tesseract's cold light; captured in the bedroom and in the tesseract."""
    bulbs = []
    for l in RIG['lights']:
        if l.type != 'LIGHT' or l.data.type != 'POINT': continue
        r = 0.04; e = l.data.energy
        bulbs.append({'x': round(l.location.x, 3), 'y': round(l.location.z, 3), 'z': round(-l.location.y, 3), 'r': r,
                      'L': round(e / (4 * math.pi * r ** 2) / 60, 2), 'color': [round(v, 3) for v in l.data.color]})
    at = [[round(v, 3) for v in (p.x, p.z, -p.y)] for p in (Vector((-1.2, -1.5, 1.1)), Vector((-1.0, 1.6, 1.2)), Vector((2.0, 2.2, 1.3)))]
    return {'capture': {'ceiling': [0.3, 0.3, 0.32], 'walls': [0.34, 0.34, 0.36], 'emitters': bulbs, 'windows': [], 'at': at}}


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
