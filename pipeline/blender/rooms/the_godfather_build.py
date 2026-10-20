# The Godfather: assemble Don Corleone's study and the front hall; the Don behind his desk with the cat in his lap,
# Bonasera before him, Hagen in his armchair with his papers, Sonny at the window with his wine; the scene played as
# the film plays it (the Don sets the cat down, rises, goes to the window, takes Bonasera's kiss on his hand and walks
# him to the door; Hagen crosses to him), Bonasera out to the front door and back; then preview, bake and export.
import math, os
import bpy
from mathutils import Vector, Matrix, Quaternion
import cine, people, stages
from stages import camera
import rooms.the_godfather as R
import rooms.the_godfather_cat as CAT

ROOM = 'the-godfather'
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
    # the cast first: their acts are posed frame by frame, and every pose re-evaluates the scene (the room's two thousand
    # pieces would make that an hour)
    seated = [] if args.get('nocast') else cast(crowd, args)
    SEATED[:] = seated
    R.shell(M, static, static, phantom)
    R.windows(M, static)
    R.fireplace(M, static)
    lamp = R.back_things(M, static)
    R.desk(M, static)
    R.chairs(M, static)
    sconces, red = R.left_things(M, static)
    R.rug(M, static)
    hall_bulb = R.hall(M, static)
    RIG['lights'] = R.lights(lamp, sconces, red, hall_bulb)
    _tidy()
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
            'close': camera('cam_close', (4.6, -5.4, 3.3), (-1.6, 1.0, 0.95), 30),
            'master': camera('cam_master', (-3.9, -3.3, 1.55), (-1.9, 2.6, 1.15), 50),          # the film's wide, from Hagen's corner
            'desk': camera('cam_desk', (-2.2, -0.6, 1.45), (-2.5, 2.6, 1.0), 40),
            'reverse': camera('cam_reverse', (-2.6, 3.2, 1.6), (0.6, -1.0, 1.0), 55),
            'right': camera('cam_right', (1.9, -1.9, 1.6), (-0.4, 2.4, 1.2), 55),
            'hall': camera('cam_hall', (3.3, -2.8, 1.7), (3.4, 3.4, 1.2), 55),
            'top': camera('cam_top', (-0.5, -0.2, 14.0), (-0.5, 0.0, 0.0), 36)}
    for who, turn in (('vito', 25), ('bonasera', 160), ('hagen', -35), ('sonny', 25)): cams[who] = _person_cam(who, turn)
    cams['lap'] = camera('cam_lap', (-2.1, 1.3, 1.35), (-2.5, 2.55, 0.68), 30)
    cams['wide'] = camera('cam_wide', (3.6, -5.4, 4.4), (-1.0, 1.0, 0.8), 52)
    cams['kiss'] = camera('cam_kiss', (1.7, -0.9, 1.75), (0.2, 1.05, 1.05), 38)
    cams['rose'] = camera('cam_rose', (-1.5, -1.0, 1.75), (-0.8, 1.1, 1.25), 34)
    return sc, M, objs, list(phantom.objects), seated, cams


def _spot(who):
    """Where someone is in their looping act, and which way they face."""
    if who in R.SPOTS: p, f = R.SPOTS[who]; return Vector((*p, 0.0)), Vector((*f, 0.0)).normalized()
    return R.chair_at(who)


def _person_cam(who, turn=25, dist=2.0):
    """A look at one of them: from `turn` degrees off their facing, 2 m away."""
    p, f = _spot(who); d = Matrix.Rotation(math.radians(turn), 3, 'Z') @ f
    h = 1.0 if who in ('vito', 'hagen') else 1.4
    return camera(f'cam_{who}', tuple(p + d * dist + Vector((0, 0, h + 0.3))), tuple(p + Vector((0, 0, h))), 36)


def _tidy():
    """Imported props come under helper empties: keep their children where they are and drop the empties."""
    bpy.context.view_layer.update()
    for o in [o for o in bpy.data.objects if o.type == 'EMPTY']:
        for ch in o.children:
            mw = ch.matrix_world.copy(); ch.parent = None; ch.matrix_world = mw
        bpy.data.objects.remove(o, do_unlink=True)


KEEP = ('solid_', 'wall_', 'back_wall', 'left_wall', 'kerb', 'floor', 'subfloor')   # names that carry rules


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
# The opening scene: the Don behind his desk stroking the cat in his lap, Bonasera standing before him pleading, Hagen
# in his armchair by the little table with his papers, Sonny at the window with a glass of wine. Each has a looping act
# and a few idles; the Don's 'scene' plays the film's scene and cues the others' (and the cat's), so they play together.
def _tex(who, prefix, *names):
    return {f'{prefix}_{n}.tga': f'{who}/{prefix}_{n}.png' for n in names}



CAST = [
    dict(who='vito', avatar='Male_Adult_03', shape=('heavy', 0.42), height=1.76, seat='vito', base='m_sit_chair_breathe_01', work=('stroke', 16, 34),
         idles={'talk': (None, 0.8), 'face': (None, 0.5), 'scene': (None, 1.5)},
         cue={'scene': {'bonasera': 'scene', 'hagen': 'scene', 'sonny': 'watch', 'cat': 'scene'}}, roam=('scene',), hands=('stroke', 'talk', 'face', 'scene'),
         flower='rose', tex=_tex('vito', 'm004', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
    dict(who='bonasera', avatar='Business_Male_07', shape=('broad', 1.0), height=1.66, base='m_gestic_talk_sad_01', work=('plead', 14, 30),
         idles={'listen': ('m_gestic_listen_sad_01', 0.6), 'wring': ('m_idle_nervous_01', 0.4), 'scene': (None, 0.0)}, roam=('scene',), hands=('scene',),
         tex=_tex('bonasera', 'm018', 'head_color', 'body_color', 'body_normal')),
    dict(who='hagen', avatar='Male_Adult_13', shape=('lean', 1.2), height=1.74, seat='hagen', base='m_sit_chair_breathe_01', work=('papers', 14, 30),
         idles={'look': (None, 0.6), 'scene': (None, 0.0)}, roam=('scene',), hands=('papers', 'look', 'scene'),
         flower='carnation', tex=_tex('hagen', 'm010', 'head_color', 'body_color', 'body_normal')),
    dict(who='sonny', avatar='Male_Adult_06', shape=('athletic', 1.0), height=1.77, base='m_idle_breathe_01', work=('wine', 12, 26),
         idles={'sip': (None, 0.8), 'peek': (None, 0.5), 'shift': ('m_idle_neutral_02', 0.4), 'watch': (None, 0.0)}, roam=(), hands=('wine', 'sip', 'peek', 'shift', 'watch'),
         flower='carnation', tex=_tex('sonny', 'm011', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
]
CAT_ENTRY = dict(who='cat', work=('lap', 16, 36), idles={'look': (None, 0.7), 'knead': (None, 0.6), 'scene': (None, 0.0)}, roam=('scene',))
FIRST = {'vito': 'scene'}               # the room opens on the scene already under way (see OPEN)
OPEN = {}
SPINE = ('Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2')
ARMS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('Clavicle', 'UpperArm', 'Forearm', 'Hand'))
LEGS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('Thigh', 'Calf', 'Foot'))
HEAD = ('Bip01 Neck', 'Bip01 Head')
FINGERS = tuple(f'Bip01 {s} Finger{f}{j}' for s in 'LR' for f in '01234' for j in ('', '1', '2'))
ALL = ('Bip01 Pelvis',) + SPINE + ARMS + LEGS + HEAD
LAP = {}                                # the cat's place in the Don's lap: 'M' (its root, world), 'sides', 'stroke' points


def _all(arm, fingers=False):
    return (next(b.name for b in arm.data.bones if b.parent is None),) + ALL + (FINGERS if fingers else ())


def _smooth(x):
    x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)


def _frame_of(arm):
    """The body frame from the pelvis and the stored facing (not from the feet, which IK moves)."""
    pel = people._world(arm, arm.pose.bones['Bip01 Pelvis']).translation.copy()
    fwd = Vector(arm['fwd']); up = Vector((0, 0, 1)); right = fwd.cross(up).normalized()
    return pel, fwd, right, up


def _live(arm):
    """The body frame now: the pelvis, and the facing it carries (stored in the pelvis's own axes as he was placed), so a
    man who has stood up and turned round looks and reaches from where he faces now."""
    pb = arm.pose.bones['Bip01 Pelvis']; M = people._world(arm, pb)
    f = M.to_3x3() @ Vector(arm['pel_fwd']); f.z = 0; f.normalize()
    up = Vector((0, 0, 1)); return M.translation.copy(), f, f.cross(up).normalized(), up


def _look(arm, at, w, fwd=None):
    """Turn the head (and a little the neck) toward a point, by the fraction w."""
    if w <= 0: return
    H = people._world(arm, arm.pose.bones['Bip01 Head']).translation
    pel, f, right, up = _live(arm)
    if fwd is not None: f = fwd; right = f.cross(up).normalized()
    d = (Vector(at) - H).normalized()
    yaw = math.atan2(d.dot(-right), d.dot(f)); pitch = math.asin(max(-1, min(1, d.z)))
    people.bend(arm, 'Bip01 Neck', up, yaw * 0.35 * w); people.bend(arm, 'Bip01 Head', up, yaw * 0.65 * w)
    people.bend(arm, 'Bip01 Neck', right, pitch * 0.3 * w); people.bend(arm, 'Bip01 Head', right, pitch * 0.7 * w)


def _head_of(who):
    """Where someone's head is in their loop (for looks)."""
    p, f = _spot(who)
    return p + Vector((0, 0, {'vito': 1.18, 'hagen': 1.1, 'bonasera': 1.55, 'sonny': 1.66}[who])) + f * 0.05


def _height(arm, mesh):
    bpy.context.view_layer.update()
    return max((mesh.matrix_world @ v.co).z for v in mesh.data.vertices)


# ---------------------------------------------------------------- props on the people
def _bind(arm, mesh, bm, bone, mats, name):
    """Geometry made in the world at the body's present pose (a glass in the hand), carried back to the rest pose
    through `bone`, skinned wholly to it and joined into the body mesh."""
    A = arm.matrix_world; pb = arm.pose.bones[bone]
    hidden = mesh.hide_viewport; mesh.hide_viewport = False
    bm.transform(mesh.matrix_world.inverted() @ A @ pb.bone.matrix_local @ pb.matrix.inverted() @ A.inverted())
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(name, me); [c.objects.link(ob) for c in mesh.users_collection]
    for m in mats: me.materials.append(m)
    ob.matrix_world = mesh.matrix_world.copy()
    vg = ob.vertex_groups.new(name=bone); vg.add(list(range(len(me.vertices))), 1.0, 'REPLACE')
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.join()
    mesh.hide_viewport = hidden


def _lapel(arm, mesh):
    """The left lapel's surface point and normal (rest pose): over the heart, a hand below the collar."""
    from mathutils.bvhtree import BVHTree
    J = people._joints(arm); neck = J['Bip01 Neck']
    deps = bpy.context.evaluated_depsgraph_get(); bvh = BVHTree.FromObject(mesh, deps); Mi = mesh.matrix_world.inverted(); M = mesh.matrix_world
    o = Vector((neck.x + 0.085, neck.y - 0.4, neck.z - 0.115))
    hit = bvh.ray_cast(Mi @ o, (Mi.to_3x3() @ Vector((0, 1, 0))).normalized())
    p = M @ hit[0] if hit[0] is not None else Vector((neck.x + 0.085, neck.y - 0.12, neck.z - 0.115))
    n = (M.to_3x3() @ hit[1]).normalized() if hit[1] is not None else Vector((0, -1, 0))
    return p, n


def _flower(arm, mesh, kind):
    """A buttonhole on the left lapel, in the rest pose: the Don's red rosebud on its stem, or a groomsman's white
    carnation (a ball of ruffled petals); skinned to the chest."""
    import bmesh, random
    p, n = _lapel(arm, mesh); bm = bmesh.new(); rnd = random.Random(3)
    if kind == 'rose':
        c = p + n * 0.016 + Vector((0, 0, 0.006))
        bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=1.0, matrix=Matrix.Translation(c) @ Matrix.Diagonal((0.011, 0.011, 0.017, 1)))
        for v in bm.verts: v.co += (v.co - c).normalized() * 0.0015 * math.sin(7 * math.atan2(v.co.y - c.y, v.co.x - c.x))
        k0 = len(bm.faces)
        bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.0025, radius2=0.002, depth=0.05, matrix=Matrix.Translation(c - Vector((0, 0, 0.035))) @ Matrix.Rotation(0.25, 4, 'X'))
        bm.faces.ensure_lookup_table()
        for f in list(bm.faces)[k0:]: f.material_index = 1
        mats = [cine.material('rosebud', (0.42, 0.015, 0.03), rough=0.45, sheen=0.4, sheen_tint=(0.6, 0.2, 0.2)), cine.material('stem_green', (0.05, 0.12, 0.03), rough=0.6)]
    else:
        c = p + n * 0.02
        bmesh.ops.create_icosphere(bm, subdivisions=3, radius=0.021, matrix=Matrix.Translation(c))
        for v in bm.verts:
            d = (v.co - c); v.co = c + d * (1 + 0.16 * math.sin(40 * d.x) * math.sin(37 * d.y) * math.sin(43 * d.z) + 0.05 * rnd.random())
        mats = [cine.material('carnation', (0.86, 0.85, 0.8), rough=0.7, sheen=0.3, sheen_tint=(0.5, 0.5, 0.5))]
    me = bpy.data.meshes.new(kind); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(kind, me); [cl.objects.link(ob) for cl in mesh.users_collection]
    for m in mats: me.materials.append(m)
    for pl in me.polygons: pl.use_smooth = True
    ob.matrix_world = mesh.matrix_world.copy(); me.transform(mesh.matrix_world.inverted())
    vg = ob.vertex_groups.new(name='Bip01 Spine2'); vg.add(list(range(len(me.vertices))), 1.0, 'REPLACE')
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.join()


def _glass_bm(at, up):
    """A stemmed wine glass with red wine in it, standing on `at` (its foot) along `up` (world)."""
    import bmesh
    bm = bmesh.new(); R_ = up.to_track_quat('Z', 'Y').to_matrix().to_4x4(); T_ = Matrix.Translation(at) @ R_
    prof = [(0.0, 0.0), (0.03, 0.0), (0.03, 0.004), (0.005, 0.01), (0.004, 0.075), (0.02, 0.085), (0.034, 0.11), (0.036, 0.14), (0.033, 0.165), (0.031, 0.165),
            (0.033, 0.14), (0.031, 0.11), (0.0, 0.09)]
    seg = 16; rings = []
    for r, z in prof:
        rings.append([bm.verts.new(T_ @ Vector((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), z))) for i in range(seg)])
    for j, (a, b) in enumerate(zip(rings, rings[1:])):
        for i in range(seg):
            f = bm.faces.new((a[i], a[(i + 1) % seg], b[(i + 1) % seg], b[i]))
            if 5 <= j <= 6 or j >= 10: f.material_index = 1                  # the bowl's lower half, the wine seen through it
    wr = [bm.verts.new(T_ @ Vector((0.029 * math.cos(2 * math.pi * i / seg), 0.029 * math.sin(2 * math.pi * i / seg), 0.128))) for i in range(seg)]
    bm.faces.new(wr)                                                       # the wine's surface
    bm.faces.ensure_lookup_table(); bm.faces[-1].material_index = 1
    return bm


def _papers_bm(c, fwd, right, up):
    """A sheaf of papers, slightly curled, lying in the hands: 22 x 28 cm."""
    import bmesh
    bm = bmesh.new()
    for k in range(3):
        grid = []
        for j in range(5):
            row = []
            for i in range(4):
                u, v = (i / 3 - 0.5) * 0.215, (j / 4 - 0.5) * 0.28
                row.append(bm.verts.new(c + right * (u + 0.004 * k) + fwd * v + up * (0.002 * k + 0.012 * (abs(u) / 0.11) ** 2)))
            grid.append(row)
        for j in range(4):
            for i in range(3): bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    return bm


# ---------------------------------------------------------------- placing them
def _seat(c, arm, base, frames):
    """Slide a seated person so the clip's pelvis sits over the chair's seat."""
    p, f = R.chair_at(c['seat'])
    people.pose_at(arm, base, frames[0])
    pel = people._world(arm, arm.pose.bones['Bip01 Pelvis']).translation
    want = p - f * 0.03
    arm.location.x += want.x - pel.x; arm.location.y += want.y - pel.y
    bpy.context.view_layer.update()
    cine.log(f"seat {c['who']}: pelvis {pel.z:.3f} m high (seat {R.SEAT[c['seat']]:.3f})")


def _stand(c, arm, base, frames):
    """A standing person: the clip's pelvis over their spot."""
    p, f = _spot(c['who'])
    people.pose_at(arm, base, frames[0])
    pel = people._world(arm, arm.pose.bones['Bip01 Pelvis']).translation
    arm.location.x += p.x - pel.x; arm.location.y += p.y - pel.y
    bpy.context.view_layer.update()


def cast(col, args):
    """Load, dress, shape and place the four and the cat, and bake their acts (cached: retargets and IK take minutes)."""
    full = bool(args.get('full'))
    spec = {'cast': CAST, 'cat': CAT_ENTRY, 'chairs': R.CHAIRS, 'seat': R.SEAT, 'spots': {k: [list(v[0]), list(v[1])] for k, v in R.SPOTS.items()},
            'desk': list(R.DESK), 'cat_desk': list(R.CAT_DESK), 'door': R.DOOR, 'full': full, 'v': 6}
    everyone = CAST + [CAT_ENTRY]
    seated = stages.cast_cache(OUT, everyone, spec, lambda: _make_cast(col, full), col)
    for c, arm, mesh in seated:
        if 'open_act' in arm: OPEN[c['who']] = (arm['open_act'], float(arm['open_at']))
        people.pose_at(arm, c['acts'][c['work'][0]], 30)
    return seated


def _make_cast(col, full):
    seated, made = [], {}
    for c in CAST:
        who = c['who']
        arm, mesh = people.load_avatar(c['avatar'], textures={k: os.path.join(PEOPLE_TEX, v) for k, v in c['tex'].items()}, collection=col)
        mesh['person'] = who; arm['person'] = who
        people.reshape(arm, mesh, *c['shape'])
        if c.get('flower'): _flower(arm, mesh, c['flower'])
        s = c['height'] / _height(arm, mesh)
        arm.scale = arm.scale * s; arm.location = (arm.location.x, arm.location.y, arm.location.z * s)
        bpy.context.view_layer.update()
        p, f = (R.chair_at(c['seat']) if c.get('seat') else _spot(who))
        f = Vector(f).normalized()
        people.face(arm, f); arm.location = (p.x, p.y, arm.location.z)
        bpy.context.view_layer.update()
        arm['fwd'] = list(f)
        base, frames, _ = people.retarget(arm, c['base'], cycles=2, action_name=f'{who}_base')
        (_seat if c.get('seat') else _stand)(c, arm, base, frames)
        people.pose_at(arm, base, frames[0])
        arm['pel_fwd'] = list(people._world(arm, arm.pose.bones['Bip01 Pelvis']).to_3x3().inverted() @ f)
        made[who] = dict(c=c, arm=arm, mesh=mesh, base=base, frames=frames, drop=(0.52 - R.SEAT[c['seat']]) if c.get('seat') else 0.0)
        seated.append((c, arm, mesh))
    # the cat, in the Don's lap as he sits in his loop
    v = made['vito']; people.pose_at(v['arm'], v['base'], v['frames'][0]); _vito_sit(v['arm'], v['drop'])
    LAP['M'] = _lap_matrix(v['arm'])
    carm, cmesh = CAT.load(col)
    _lap_points(carm, cmesh)
    # the looping acts and the idles, the meshes hidden meanwhile (posing re-evaluates every visible skinned mesh)
    for m in list(made.values()): m['mesh'].hide_viewport = True
    cmesh.hide_viewport = True
    acts = {k: {} for k in made}
    _vito_acts(made['vito'], acts['vito'], full)
    _bonasera_acts(made['bonasera'], acts['bonasera'], full)
    _hagen_acts(made['hagen'], acts['hagen'], full, col)
    _sonny_acts(made['sonny'], acts['sonny'], full, col)
    cat_acts = _cat_acts(carm, full)
    if full: _scene(made, acts, carm, cat_acts)
    for who, m in made.items():
        m['c']['acts'] = acts[who]
        for name, a in acts[who].items():
            if name not in m['c'].get('hands', ()): people.freeze(a)
        if m['base'] not in acts[who].values(): bpy.data.actions.remove(m['base'])
        people.pose_at(m['arm'], acts[who][m['c']['work'][0]], 30)
    CAT_ENTRY['acts'] = cat_acts
    for m in list(made.values()): m['mesh'].hide_viewport = False
    cmesh.hide_viewport = False
    seated.append((CAT_ENTRY, carm, cmesh))
    return seated


# ---------------------------------------------------------------- the Don, the cat in his lap
def _vito_sit(arm, drop):
    """The Don settled in his tall chair: lowered onto its cushion, sitting back against it a little."""
    people.shift_root(arm, (0, 0, -drop))
    pel, fwd, right, up = _frame_of(arm)
    for b, a in zip(SPINE, (0.04, 0.03, 0.02)): people.bend(arm, b, right, a)


def _lap_matrix(arm):
    """Where the cat lies: across the Don's thighs, a little toward his knees, its head and paws at his left, its back
    at his right (the cat's own frame: x toward his right, y toward his knees, z up)."""
    pel, fwd, right, up = _frame_of(arm)
    mid = [(people._world(arm, arm.pose.bones[f'Bip01 {s} Thigh']).translation + people._world(arm, arm.pose.bones[f'Bip01 {s} Calf']).translation) / 2 for s in 'LR']
    c = (mid[0] + mid[1]) / 2 - fwd * 0.02; c.z += 0.075
    M = Matrix.Identity(4)
    for i, v in enumerate((right, fwd, up)):
        for r in range(3): M[r][i] = v[r]
    M = Matrix.Translation(c) @ M @ Matrix.Rotation(math.radians(-10), 4, 'X')   # tipped back with the thighs' slope
    cine.log('lap at', tuple(round(x, 3) for x in c))
    return M


def _lap_points(carm, cmesh):
    """Points on the cat's top as it lies in the lap (world): along its back for the stroking hand, at its head and
    shoulders for the resting one; found by casting down onto it."""
    from mathutils.bvhtree import BVHTree
    M = LAP['M']
    carm.pose.bones['cat_root'].matrix = M @ carm.pose.bones['cat_root'].bone.matrix_local; bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get(); bvh = BVHTree.FromObject(cmesh, deps)
    def top(x, y):
        o = M @ (Vector((x, y, 0.0)) * 1.0 + Vector((0, 0, 0.5)))
        hit = bvh.ray_cast(o, Vector((0, 0, -1)), 1.0)
        return hit[0].copy() if hit[0] is not None else M @ Vector((x, y, 0.15))
    s = CAT.SCALE; b = CAT.BASE
    loc = lambda sx, sy: ((sx - b.x) * s, (sy - b.y) * s)
    LAP['stroke'] = [top(*loc(sx, sy)) for sx, sy in ((0.1, 0.02), (0.18, 0.01), (0.26, -0.01), (0.33, -0.04), (0.38, -0.07))]
    LAP['rest_L'] = top(*loc(0.07, -0.08))                                       # his left hand: over its head and neck
    LAP['scratch'] = top(*loc(0.05, -0.04))
    cine.log('cat stroke path', [tuple(round(v, 2) for v in p) for p in LAP['stroke']])
    carm.pose.bones['cat_root'].matrix = carm.pose.bones['cat_root'].bone.matrix_local; bpy.context.view_layer.update()


def _hand_aim(arm, side, d, w=1.0):
    """Bend a wrist so the hand's fingers run along `d` (world), by the fraction w."""
    hand = arm.pose.bones[f'Bip01 {side} Hand']; M = people._world(arm, hand); H = M.translation.copy()
    tip = people._world(arm, arm.pose.bones[f'Bip01 {side} Finger2']).translation - H
    q = tip.normalized().rotation_difference(Vector(d).normalized())
    people._set_world(arm, hand, Matrix.Translation(H) @ Quaternion().slerp(q, w).to_matrix().to_4x4() @ Matrix.Translation(-H) @ M)


def _hand_on(arm, side, target, out=0.3, w=1.0, along=None):
    """A hand laid flat on a point, its fingers running along `along` (world; by default forward and a little in), the
    palm down; the wrist a hand's length back from the point, a little above it; the elbow out to the side."""
    pel, fwd, right, up = _frame_of(arm)
    sd = 1 if side == 'R' else -1
    d = Vector(along) if along is not None else (fwd - right * sd * 0.5)
    d = (d - up * d.dot(up)).normalized() * 0.94 - up * 0.34
    H0 = people._world(arm, arm.pose.bones[f'Bip01 {side} Hand']).translation.copy()
    tgt = H0.lerp(Vector(target) - d * 0.07 + up * 0.035, w)
    people.ik2(arm, side, tgt, tgt - up * 0.3 + right * sd * out - fwd * 0.1)
    _hand_aim(arm, side, d, w)
    people.palm_to(arm, side, -up, 0.9 * w)


def _stroke(arm, t, T, w=1.0, period=2.6):
    """The right hand stroking the cat from its shoulders down its back, lifting and coming back over it, a whole
    number of strokes over T."""
    k = max(1, round(T / period)); ph = (k * t / T) % 1.0
    pts = LAP['stroke']
    if ph < 0.62:
        u = _smooth(ph / 0.62) * (len(pts) - 1); i = min(int(u), len(pts) - 2); p = pts[i].lerp(pts[i + 1], u - i); lift = 0.0
    else:
        u = (1 - _smooth((ph - 0.62) / 0.38)) * (len(pts) - 1); i = min(int(u), len(pts) - 2); p = pts[i].lerp(pts[i + 1], u - i)
        lift = math.sin(math.pi * (ph - 0.62) / 0.38) * 0.05
    along = (pts[-1] - pts[0]); along.z = 0
    _hand_on(arm, 'R', p + Vector((0, 0, lift)), out=0.32, w=w, along=along)


def _rest_left(arm, t, T, w=1.0):
    """The left hand resting over the cat's head and neck, the fingers working a little in its fur."""
    k = max(1, round(T / 1.7)); a = 2 * math.pi * k * t / T
    _hand_on(arm, 'L', LAP['rest_L'] + Vector((0.006 * math.cos(a), 0.006 * math.sin(a), 0.0)), out=0.28, w=w)


def _vito_acts(m, acts, full):
    """The Don's loop: stroking the cat, his eyes on Bonasera; idles: talking to him with his right hand while the left
    stays on the cat, and the hand to his face (his chin and cheek in his fingers)."""
    arm, base, frames, drop = m['arm'], m['base'], m['frames'], m['drop']; T = (frames[1] - frames[0]) / people.FPS
    b_head = _head_of('bonasera')
    def stroke(f, t):
        _vito_sit(arm, drop); _look(arm, b_head + Vector((0, 0, -0.05)), 0.6)
        glance = math.exp(-((t - T * 0.6) / 1.2) ** 2)                          # once a loop, a look down at the cat
        if glance > 0.02: _look(arm, LAP['stroke'][2], 0.5 * glance)
        _stroke(arm, t, T); _rest_left(arm, t, T)
    acts['stroke'] = people.custom_act(arm, base, frames, 'vito_stroke', stroke, _all(arm, fingers=True)); m['steps'] = {'stroke': stroke}
    if not full: return
    def talk(f, t):
        _vito_sit(arm, drop)
        e = people.envelope(t, T, 1.4, 1.6); pel, fwd, right, up = _frame_of(arm)
        _look(arm, b_head, 0.75)
        k = max(1, round(T / 3.1)); u = 2 * math.pi * k * t / T
        sh = people._world(arm, arm.pose.bones['Bip01 R UpperArm']).translation
        tgt = sh + fwd * (0.32 + 0.06 * math.sin(u)) - up * (0.22 - 0.1 * max(0.0, math.sin(u * 2 + 0.5))) + right * 0.12
        H0 = people._world(arm, arm.pose.bones['Bip01 R Hand']).translation.copy()
        people.ik2(arm, 'R', H0.lerp(tgt, e), H0.lerp(tgt, e) - up * 0.3 + right * 0.3)
        people.palm_to(arm, 'R', (up * 0.8 + right * 0.4).normalized(), 0.8 * e)
        if e < 1: _stroke(arm, t, T, w=1 - e)
        people.bend(arm, 'Bip01 Head', right, 0.05 * math.sin(u * 1.5) * e)
        _rest_left(arm, t, T)
    acts['talk'] = people.custom_act(arm, base, frames, 'vito_talk', talk, _all(arm, fingers=True))
    def face(f, t):
        _vito_sit(arm, drop)
        e = people.envelope(t, T, 1.8, 1.8); pel, fwd, right, up = _frame_of(arm)
        Hd = people._world(arm, arm.pose.bones['Bip01 Head']).translation
        jaw = Hd + fwd * 0.09 - up * 0.08 + right * 0.035
        H0 = people._world(arm, arm.pose.bones['Bip01 R Hand']).translation.copy()
        tgt = H0.lerp(jaw - fwd * 0.04 - up * 0.04, e)
        people.ik2(arm, 'R', tgt, tgt - up * 0.35 + right * 0.2 + fwd * 0.05)
        people.palm_to(arm, 'R', (-fwd * 0.4 - right * 0.8).normalized(), 0.8 * e)
        if e < 1: _stroke(arm, t, T, w=1 - e)
        people.bend(arm, 'Bip01 Head', fwd, -0.08 * e)                          # leaning his head into the hand
        _look(arm, b_head, 0.5)
        _rest_left(arm, t, T)
    acts['face'] = people.custom_act(arm, base, frames, 'vito_face', face, _all(arm, fingers=True))


# ---------------------------------------------------------------- Bonasera
def _bonasera_acts(m, acts, full):
    """Bonasera before the desk, telling the Don what was done to his daughter (a sad, pleading talk), his eyes on him;
    idles: listening, wringing his hands."""
    arm, base, frames = m['arm'], m['base'], m['frames']; T = (frames[1] - frames[0]) / people.FPS
    v_head = _head_of('vito')
    plead = lambda f, t: _look(arm, v_head, 0.7)
    acts['plead'] = people.custom_act(arm, base, frames, 'bonasera_plead', plead, _all(arm)); m['steps'] = {'plead': plead}
    if not full: return
    for name, (clip, _w) in m['c']['idles'].items():
        if not clip: continue
        src = people.anchor(arm, people.retarget(arm, clip, action_name=f'bonasera_{name}_src')[0], base)
        fr = (int(src.frame_range[0]), int(src.frame_range[1]))
        acts[name] = people.custom_act(arm, src, fr, f'bonasera_{name}', lambda f, t: _look(arm, v_head, 0.7), _all(arm))
        bpy.data.actions.remove(src)


# ---------------------------------------------------------------- Hagen
def _hagen_sit(arm, drop):
    people.shift_root(arm, (0, 0, -drop))
    pel, fwd, right, up = _frame_of(arm)
    for b, a in zip(SPINE, (0.06, 0.04, 0.0)): people.bend(arm, b, right, a)       # back in the deep club chair


def _papers_at(arm):
    """Where Hagen holds his papers: in his lap, tipped up toward him."""
    pel, fwd, right, up = _frame_of(arm)
    return pel + fwd * 0.34 + up * 0.17


def _hold_papers(arm, w=1.0, turn=0.0):
    """Both hands on the papers in his lap (the left at its left edge, the right at its right), `turn` lifting the
    right hand as if to turn a page."""
    pel, fwd, right, up = _frame_of(arm); c = _papers_at(arm)
    for s, sd in (('L', -1), ('R', 1)):
        H0 = people._world(arm, arm.pose.bones[f'Bip01 {s} Hand']).translation.copy()
        tgt = c + right * sd * 0.12 - fwd * 0.04 + (up * 0.06 + fwd * 0.03) * (turn if s == 'R' else 0.0)
        tgt = H0.lerp(tgt, w)
        people.ik2(arm, s, tgt, tgt - up * 0.3 + right * sd * 0.3 - fwd * 0.05)
        people.palm_to(arm, s, (up * 0.5 - right * sd * 0.6).normalized(), 0.8 * w)


def _hagen_acts(m, acts, full, col):
    """Hagen in his club chair, reading the papers in his lap (now and then a page turned); idle: he looks up at the
    Don. The papers are in his left hand throughout (skinned to it)."""
    arm, base, frames, drop = m['arm'], m['base'], m['frames'], m['drop']; T = (frames[1] - frames[0]) / people.FPS
    def papers(f, t):
        _hagen_sit(arm, drop)
        k = max(1, round(T / 9.0)); turn = max(0.0, math.sin(2 * math.pi * k * t / T)) ** 6
        _hold_papers(arm, turn=turn)
        _look(arm, _papers_at(arm), 0.8)
    acts['papers'] = people.custom_act(arm, base, frames, 'hagen_papers', papers, _all(arm, fingers=True)); m['steps'] = {'papers': papers}
    # the papers, made where the left hand holds them at the loop's first frame
    people.pose_at(arm, acts['papers'], frames[0])
    pel, fwd, right, up = _frame_of(arm)
    H = people._world(arm, arm.pose.bones['Bip01 L Hand']).translation
    c = H + right * 0.1 + fwd * 0.06 + up * 0.0
    t_fwd = (fwd * 0.8 + up * 0.6).normalized(); t_up = t_fwd.cross(right).normalized() * -1
    _bind(arm, m['mesh'], _papers_bm(c, t_fwd, right, -t_up if t_up.z < 0 else t_up), 'Bip01 L Hand', [cine.material('papers', (0.82, 0.8, 0.74), rough=0.85)], 'papers')
    if not full: return
    v_head = _head_of('vito')
    def look(f, t):
        _hagen_sit(arm, drop)
        e = people.envelope(t, T, 1.5, 1.5)
        _hold_papers(arm, w=1.0)
        _look(arm, _papers_at(arm), 0.8 * (1 - e)); _look(arm, v_head, 0.75 * e)
    acts['look'] = people.custom_act(arm, base, frames, 'hagen_look', look, _all(arm, fingers=True))


# ---------------------------------------------------------------- Sonny
def _glass_hold(arm):
    """Where Sonny holds his glass: before his chest, low, his left hand in his trouser pocket."""
    pel, fwd, right, up = people.body_frame(arm)
    sh = people._world(arm, arm.pose.bones['Bip01 R UpperArm']).translation
    return sh + fwd * 0.26 - up * 0.3 - right * 0.04


def _hold_glass(arm, w=1.0, at=None, tilt=0.0):
    pel, fwd, right, up = people.body_frame(arm)
    tgt = at if at is not None else _glass_hold(arm)
    H0 = people._world(arm, arm.pose.bones['Bip01 R Hand']).translation.copy()
    tgt = H0.lerp(tgt, w)
    people.ik2(arm, 'R', tgt, tgt - up * 0.3 + right * 0.3 - fwd * 0.05)
    people.palm_to(arm, 'R', -right, 0.9 * w)
    if tilt:
        hand = arm.pose.bones['Bip01 R Hand']; Hm = people._world(arm, hand); c = Hm.translation.copy()
        people._set_world(arm, hand, Matrix.Translation(c) @ Matrix.Rotation(-tilt, 4, right) @ Matrix.Translation(-c) @ Hm)


def _pocket(arm, w=1.0):
    pel, fwd, right, up = people.body_frame(arm)
    tgt = pel - right * 0.16 + fwd * 0.06 - up * 0.02
    H0 = people._world(arm, arm.pose.bones['Bip01 L Hand']).translation.copy()
    people.ik2(arm, 'L', H0.lerp(tgt, w), H0.lerp(tgt, w) - up * 0.2 - right * 0.3 - fwd * 0.15)


def _sonny_acts(m, acts, full, col):
    """Sonny by the window, impatient, a glass of wine in his right hand, the left in his pocket; idles: a sip, shifting
    his weight. The glass is skinned to his hand, made as he holds it."""
    arm, base, frames = m['arm'], m['base'], m['frames']; T = (frames[1] - frames[0]) / people.FPS
    v_head = _head_of('vito')
    def wine(f, t):
        _hold_glass(arm); _pocket(arm); _look(arm, v_head, 0.5)
    acts['wine'] = people.custom_act(arm, base, frames, 'sonny_wine', wine, _all(arm, fingers=True))
    people.pose_at(arm, acts['wine'], frames[0])
    pel, fwd, right, up = people.body_frame(arm)
    H = people._world(arm, arm.pose.bones['Bip01 R Hand']).translation
    foot = H + fwd * 0.07 - right * 0.03 - up * 0.075
    _bind(arm, m['mesh'], _glass_bm(foot, Vector((0, 0, 1))), 'Bip01 R Hand',
          [cine.material('wine_glass', (0.3, 0.32, 0.31), rough=0.04, coat=1.0, specular=0.8), cine.material('wine_red', (0.16, 0.01, 0.025), rough=0.08, coat=1.0)], 'wine_glass')
    if not full: return
    def sip(f, t):
        e = people.envelope(t, T, 1.4, 1.6); Hd = people._world(arm, arm.pose.bones['Bip01 Head']).translation
        pel, fwd, right, up = people.body_frame(arm)
        mouth = Hd + fwd * 0.12 - up * 0.13 - right * 0.03
        _hold_glass(arm, at=_glass_hold(arm).lerp(mouth, e), tilt=0.6 * e); _pocket(arm)
        people.bend(arm, 'Bip01 Head', right, -0.1 * e)
        _look(arm, v_head, 0.5 * (1 - e))
    acts['sip'] = people.custom_act(arm, base, frames, 'sonny_sip', sip, _all(arm, fingers=True))
    src = people.anchor(arm, people.retarget(arm, 'm_idle_neutral_02', action_name='sonny_shift_src')[0], base)
    fr = (int(src.frame_range[0]), int(src.frame_range[1]))
    acts['shift'] = people.custom_act(arm, src, fr, 'sonny_shift', lambda f, t: (_hold_glass(arm), _pocket(arm), _look(arm, v_head, 0.4)), _all(arm, fingers=True))
    bpy.data.actions.remove(src)


# ---------------------------------------------------------------- the cat
def _cat_acts(carm, full):
    """The cat in the lap: breathing, now and then a paw kneading; idles: it lifts its head and looks round, it kneads."""
    M = LAP['M']; at = lambda t: M
    def lap(arm, t, T):
        CAT.breathe(arm, t, T)
        k = max(1, round(T / 11.0)); u = 2 * math.pi * k * t / T
        CAT.head(arm, yaw=0.05 * math.sin(u), pitch=0.03 * math.sin(u * 2 + 1))
        twitch = max(0.0, math.sin(u * 3)) ** 8
        CAT.paw(arm, 'b', 0.6 * twitch)
    acts = {'lap': CAT.act(carm, 'cat_lap', 16.0, at, lap)}
    if not full: return acts
    def look(arm, t, T):
        CAT.breathe(arm, t, T)
        e = people.envelope(t, T, 1.2, 1.6)
        CAT.head(arm, yaw=0.45 * e * math.sin(2 * math.pi * t / T * 0.7), pitch=-0.35 * e, roll=0.15 * e)
    acts['look'] = CAT.act(carm, 'cat_look', 7.0, at, look)
    def knead(arm, t, T):
        CAT.breathe(arm, t, T)
        e = people.envelope(t, T, 1.0, 1.0); u = 2 * math.pi * 1.4 * t
        CAT.paw(arm, 'a', e * math.sin(u)); CAT.paw(arm, 'b', -e * math.sin(u))
        CAT.head(arm, pitch=0.08 * e)
    acts['knead'] = CAT.act(carm, 'cat_knead', 6.0, at, knead)
    return acts


# ---------------------------------------------------------------- the scene
# The places of the scene (world, metres): where the Don stands at the window, where he and Bonasera meet for the kiss
# on the hand, where he lets him go at the door, where he and Hagen talk; Bonasera at the hall's front door.
V_WIN, V_WIN_F = Vector((-1.78, 2.95, 0)), Vector((0.25, 1.0, 0)).normalized()
V_KISS, B_KISS = Vector((0.3, 1.34, 0)), Vector((0.16, 0.72, 0))
V_STOP = Vector((1.5, 1.4, 0))
V_MEET, H_MEET = Vector((-0.6, 1.12, 0)), Vector((-1.22, 0.74, 0))
H_STAND, H_STAND_F = Vector((-3.62, 0.45, 0)), Vector((0.55, 0.84, 0)).normalized()
B_FRONT = Vector((3.55, 3.1, 0))


def _ends(arm, action, f, M):
    h, p = people.heading(arm, action, f)
    return (M.to_3x3() @ h).normalized(), M @ p


def _flat(v):
    v = Vector((v.x, v.y, 0)); return v.normalized() if v.length > 1e-6 else Vector((0, -1, 0))


def _cat_path(t, beats):
    """The cat's root (world matrix) through the scene: in the lap, lifted onto the desk, lying there, lifted back."""
    a0, a1, b0, b1 = beats
    L, Dm = LAP['M'], LAP['DESK']
    if t <= a0 or t >= b1: return L
    if a1 <= t <= b0: return Dm
    w = _smooth((t - a0) / (a1 - a0)) if t < a1 else 1 - _smooth((t - b0) / (b1 - b0))
    (tl, rl, sl), (td, rd, sd) = L.decompose(), Dm.decompose()
    p = tl.lerp(td, w) + Vector((0, 0, 0.14 * math.sin(math.pi * w)))
    return Matrix.LocRotScale(p, rl.slerp(rd, w), sl.lerp(sd, w))


def _carry_hands(arm, M, w):
    """Both hands under the cat (its chest end at his left, its rump at his right), as it lies at M; by the fraction w."""
    pel, fwd, right, up = _frame_of(arm)
    for side, local in (('L', Vector((-0.13, 0.02, 0.05))), ('R', Vector((0.15, 0.0, 0.06)))):
        tgt = M @ local; sd = 1 if side == 'R' else -1
        H0 = people._world(arm, arm.pose.bones[f'Bip01 {side} Hand']).translation.copy()
        g = H0.lerp(tgt, w)
        people.ik2(arm, side, g, g - up * 0.3 + right * sd * 0.3 - fwd * 0.1)
        people.palm_to(arm, side, (up * 0.7 - right * sd * 0.5).normalized(), 0.8 * w)


def _samples(arm, action, bone='Bip01 Head'):
    """Where a bone is (world) at every frame of an act."""
    f0, f1 = int(action.frame_range[0]), int(action.frame_range[1]); out = []
    for f in range(f0, f1 + 1):
        people.pose_at(arm, action, f); out.append(people._world(arm, arm.pose.bones[bone]).translation.copy())
    people.pose_at(arm, action, f0)
    return out


def _long(m, step, seconds):
    """A longer copy of someone's looping act (the base clip run more times under the same authoring): a scene holds
    the loop longer than its own length, and a clip played past its end stands still."""
    arm, c = m['arm'], m['c']; per = (m['frames'][1] - m['frames'][0]) / people.FPS / 2
    base, fr, _ = people.retarget(arm, c['base'], cycles=max(2, math.ceil(seconds / per) + 1), action_name=f"{c['who']}_{step}_long_base")
    act = people.custom_act(arm, base, fr, f"{c['who']}_{step}_long", m['steps'][step], _all(arm, fingers=True))
    bpy.data.actions.remove(base)
    return act


def _scene(made, acts, carm, cat_acts):
    """The scene, as one act each (the Don's leads and cues the rest; all as long as his)."""
    FPS = people.FPS
    V, B, Hg, S = made['vito'], made['bonasera'], made['hagen'], made['sonny']
    va, ba, ha = V['arm'], B['arm'], Hg['arm']
    stroke, plead, papers = _long(V, 'stroke', 10.0), _long(B, 'plead', 40.0), _long(Hg, 'papers', 30.0)
    # the cat's place on the desk: as in the lap, turned a little, its base on the leather
    rot = LAP['M'].to_quaternion() @ Quaternion(Vector((0, 0, 1)), math.radians(25))
    LAP['DESK'] = Matrix.LocRotScale(R.CAT_DESK + Vector((0, 0, 0.004)), Quaternion(Vector((0, 0, 1)), rot.to_euler().z), Vector((1, 1, 1)))
    # ---- the Don's clips
    up, upf, _ = people.retarget(va, 'm_sit_stand_up_chair_01', action_name='vito_src_up')
    down, downf, _ = people.retarget(va, 'm_sit_down_chair_01', action_name='vito_src_down')
    walk, walkf, vs = people.retarget(va, 'm_walk_slow_01', inplace=True, cycles=8, action_name='vito_src_walk')
    talk, talkf, _ = people.retarget(va, 'm_gestic_talk_self_assured_01', cycles=3, action_name='vito_src_talk')
    turn, turnf, _ = people.retarget(va, 'm_turn_left_180', action_name='vito_src_turn')
    cine.log(f'vito walks at {vs:.2f} m/s')
    t0f = int(stroke.frame_range[0])
    _h, p_s = people.heading(va, stroke, t0f); h_s = Vector(va['fwd'])
    hu, pu = people.heading(va, up, upf[0]); M_up = people.carry(pu, hu, p_s, h_s)
    hu1, pu1 = _ends(va, up, upf[1], M_up)
    back = max(0.0, (pu1 - p_s).dot(h_s) - 0.16)                                 # held back from the desk as he rises
    up_dur, down_dur = (upf[1] - upf[0]) / FPS, (downf[1] - downf[0]) / FPS
    M_up_f = lambda lt: Matrix.Translation(-h_s * back * _smooth(lt / up_dur)) @ M_up
    pu1 = pu1 - h_s * back
    hd, pd = people.heading(va, down, downf[1]); M_down = people.carry(pd, hd, p_s, h_s)
    hd0, pd0 = _ends(va, down, downf[0], M_down)
    M_down_f = lambda lt: Matrix.Translation(-h_s * back * (1 - _smooth(lt / down_dur))) @ M_down
    pd0 = pd0 - h_s * back
    r_win = people.path([pu1, pu1 + Vector((0.3, 0.12, 0)), Vector((-1.95, 2.72, 0)), V_WIN])
    r_kiss = people.path([V_WIN, Vector((-1.28, 2.62, 0)), Vector((-1.08, 1.85, 0)), Vector((-0.55, 1.3, 0)), V_KISS])
    r_out = people.path([V_KISS, Vector((0.85, 1.36, 0)), V_STOP])
    r_meet = people.path([V_STOP, Vector((0.55, 1.22, 0)), V_MEET])
    r_home = people.path([V_MEET, Vector((-0.82, 1.7, 0)), Vector((-1.18, 2.4, 0)), Vector((-1.85, 2.47, 0)), pd0])
    kiss_f = _flat(B_KISS - V_KISS); meet_f = _flat(H_MEET - V_MEET)
    ht, pt = people.heading(va, talk, talkf[0])
    M_talk_win = people.carry(pt, ht, V_WIN, V_WIN_F)
    M_talk_kiss = people.carry(pt, ht, V_KISS, kiss_f)
    M_talk_meet = people.carry(pt, ht, V_MEET, meet_f)
    htn, ptn = people.heading(va, turn, turnf[0]); M_turn = people.carry(ptn, htn, V_STOP, Vector((1, 0, 0)))
    turn_dur = (turnf[1] - turnf[0]) / FPS
    talk_len = (talkf[1] - talkf[0]) / FPS
    segs_v = [dict(src=stroke, f0=t0f, dur=2.0, at=Matrix.Identity(4)),
              dict(src=stroke, f0=t0f + 60, dur=4.2, at=Matrix.Identity(4), blend=0.3),                               # 1 the cat to the desk
              dict(src=up, f0=upf[0], dur=up_dur, at=M_up_f, blend=0.7),                                             # 2 up
              dict(src=walk, f0=walkf[0], dur=r_win[1] / vs, at=people.walk_along(va, walk, walkf[0], vs, r_win), blend=0.8),   # 3 to the window
              dict(src=talk, f0=talkf[0], dur=min(7.0, talk_len), at=M_talk_win, blend=0.8),                       # 4 at the window
              dict(src=walk, f0=walkf[0] + 15, dur=r_kiss[1] / vs, at=people.walk_along(va, walk, walkf[0], vs, r_kiss), blend=0.8),   # 5 round the desk
              dict(src=talk, f0=talkf[0] + 90, dur=min(5.0, talk_len - 3.0), at=M_talk_kiss, blend=0.8),          # 6 to Bonasera
              dict(src=talk, f0=talkf[0] + 240, dur=3.4, at=M_talk_kiss, blend=0.6),                               # 7 the kiss on his hand
              dict(src=walk, f0=walkf[0], dur=r_out[1] / vs, at=people.walk_along(va, walk, walkf[0], vs, r_out), blend=0.8),   # 8 to the door, his arm round him
              dict(src=turn, f0=turnf[0], dur=turn_dur, at=M_turn, blend=0.6),                                       # 9 he turns back
              dict(src=walk, f0=walkf[0] + 8, dur=r_meet[1] / vs, at=people.walk_along(va, walk, walkf[0], vs, r_meet), blend=0.6),   # 10 to Hagen
              dict(src=talk, f0=talkf[0] + 30, dur=6.0, at=M_talk_meet, blend=0.8),                                # 11 with Hagen; the rose
              dict(src=walk, f0=walkf[0] + 20, dur=r_home[1] / vs, at=people.walk_along(va, walk, walkf[0], vs, r_home), blend=0.8),   # 12 back round the desk
              dict(src=down, f0=downf[0], dur=down_dur, at=M_down_f, blend=0.9),                                     # 13 down into his chair
              dict(src=stroke, f0=t0f + 120, dur=4.2, at=Matrix.Identity(4), blend=0.9),                             # 14 the cat back
              dict(src=stroke, f0=t0f, dur=2.4, at=Matrix.Identity(4), blend=1.0)]                                   # 15 stroking it
    tv = [0.0]
    for sg in segs_v: tv.append(tv[-1] + sg['dur'])
    T_end = tv[-1]
    beats = (tv[1] + 0.6, tv[2] - 0.6, tv[14] + 0.5, tv[15] - 0.5)              # the cat leaves the lap, lands, is lifted, is back
    KISS = V_KISS + kiss_f * 0.34 + Vector((0, 0, 0.98))                       # the Don's hand, held out for the kiss
    cine.log('scene beats (s): ' + ', '.join(f'{k}:{t:.1f}' for k, t in enumerate(tv)))
    # ---- Bonasera: his plea, across to meet the Don, the kiss, out with him to the door, the hall, back
    bwalk, bwalkf, bs = people.retarget(ba, 'm_walk_slow_01', inplace=True, cycles=12, action_name='bonasera_src_walk')
    blisten, blf, _ = people.retarget(ba, 'm_gestic_listen_sad_01', cycles=4, action_name='bonasera_src_listen')
    blook, blkf, _ = people.retarget(ba, 'm_idle_look_around_01', cycles=4, action_name='bonasera_src_look')
    b0f = int(plead.frame_range[0])
    r_b1 = people.path([Vector((*R.SPOTS['bonasera'][0], 0)), Vector((-2.3, 0.45, 0)), Vector((-1.4, 0.38, 0)), Vector((-0.5, 0.48, 0)), B_KISS])
    r_b2 = people.path([B_KISS, Vector((0.8, 0.88, 0)), Vector((1.6, 0.98, 0)), Vector((2.25, 1.03, 0)), Vector((2.6, 1.04, 0)), Vector((2.98, 1.22, 0)),
                        Vector((3.28, 1.85, 0)), Vector((3.45, 2.6, 0)), B_FRONT])
    r_b3 = people.path([B_FRONT, Vector((3.38, 2.45, 0)), Vector((3.12, 1.6, 0)), Vector((2.75, 1.08, 0)), Vector((2.3, 1.02, 0)), Vector((1.4, 0.74, 0)),
                        Vector((0.2, 0.42, 0)), Vector((-1.4, 0.36, 0)), Vector((-2.3, 0.45, 0)), Vector((*R.SPOTS['bonasera'][0], 0))])
    hl, pl = people.heading(ba, blisten, blf[0]); M_bl = people.carry(pl, hl, B_KISS, -kiss_f)
    hk, pk = people.heading(ba, blook, blkf[0]); M_bk = people.carry(pk, hk, B_FRONT, Vector((0, 1, 0)))
    t_go = tv[5] - 1.2                                                          # he steps over as the Don comes round the desk
    t_arrive = t_go + r_b1[1] / bs
    t_kiss, t_out = tv[7], tv[8]
    t_front = t_out + r_b2[1] / bs
    t_back = T_end - 3.2 - r_b3[1] / bs
    cine.log(f'bonasera walks at {bs:.2f} m/s: leaves {t_go:.1f}, there {t_arrive:.1f} (the Don {tv[6]:.1f}), out {t_out:.1f}, front door {t_front:.1f}, back {t_back:.1f}')
    segs_b = [dict(src=plead, f0=b0f, dur=t_go, at=Matrix.Identity(4)),
              dict(src=bwalk, f0=bwalkf[0], dur=r_b1[1] / bs, at=people.walk_along(ba, bwalk, bwalkf[0], bs, r_b1), blend=0.9),
              dict(src=blisten, f0=blf[0], dur=t_kiss - t_arrive, at=M_bl, blend=0.8),
              dict(src=blisten, f0=blf[0] + int((t_kiss - t_arrive) * FPS), dur=t_out - t_kiss, at=M_bl, blend=0.3),
              dict(src=bwalk, f0=bwalkf[0], dur=r_b2[1] / bs, at=people.walk_along(ba, bwalk, bwalkf[0], bs, r_b2), blend=0.8),
              dict(src=blook, f0=blkf[0], dur=max(2.0, t_back - t_front), at=M_bk, blend=0.9),
              dict(src=bwalk, f0=bwalkf[0] + 10, dur=r_b3[1] / bs, at=people.walk_along(ba, bwalk, bwalkf[0], bs, r_b3), blend=0.9),
              dict(src=plead, f0=b0f, dur=3.2, at=Matrix.Identity(4), blend=1.2)]
    tb = [0.0]
    for sg in segs_b: tb.append(tb[-1] + sg['dur'])
    def b_overlay(tt, k, lt):
        if k == 2: _look(ba, KISS + Vector((0, 0, 0.6)), 0.7)
        elif k == 3:                                                            # the bow: both hands take the Don's, the lips to it
            e = people.envelope(lt, t_out - t_kiss, 0.9, 0.9)
            pel, fwd, right, up_ = people.body_frame(ba); fwd = -kiss_f; right = fwd.cross(Vector((0, 0, 1))).normalized()
            for b_, a in zip(SPINE, (0.22, 0.2, 0.14)): people.bend(ba, b_, right, -a * e)
            people.bend(ba, 'Bip01 Neck', right, -0.25 * e)
            for s, sd in (('L', -1), ('R', 1)):
                g = KISS - Vector((0, 0, 0.03)) + right * sd * 0.05 - fwd * 0.06
                H0 = people._world(ba, ba.pose.bones[f'Bip01 {s} Hand']).translation.copy()
                people.ik2(ba, s, H0.lerp(g, e), H0.lerp(g, e) - Vector((0, 0, 0.3)) + right * sd * 0.3)
                people.palm_to(ba, s, Vector((0, 0, 1)), 0.7 * e)
        elif k == 5: _look(ba, B_FRONT + Vector((0, 1.5, 1.55)), 0.5)
        elif k == 7: _look(ba, _head_of('vito'), 0.7 * _smooth(lt / 1.5))
    b_scene = people.sequence(ba, plead, 'bonasera_scene', segs_b, overlay=b_overlay)
    b_shoulder = _samples(ba, b_scene, 'Bip01 R UpperArm')
    for a in (bwalk, blisten, blook, plead): bpy.data.actions.remove(a)
    # ---- the Don, played now that Bonasera's place is known (his arm round him, his hand at his lips)
    Mc = lambda t: _cat_path(t, beats)
    def v_overlay(tt, k, lt):
        pel, fwd, right, up_ = _frame_of(va) if k in (1, 14, 15) else _live(va)
        if k in (1, 14):                                                     # lifting the cat to the desk (or back)
            dur = segs_v[k]['dur']; e = people.envelope(lt, dur, 0.6, 0.6)
            for b_, a in zip(SPINE, (0.18, 0.16, 0.1)): people.bend(va, b_, right, -a * e)
            people.bend(va, 'Bip01 Spine1', up_, -0.2 * e)
            _carry_hands(va, Mc(tt), e)
            _look(va, Mc(tt).translation + Vector((0, 0, 0.05)), 0.8 * e)
            if k == 14 and lt > dur - 1.4: w_ = _smooth((lt - dur + 1.4) / 1.2); _stroke(va, tt, T_end, w=w_); _rest_left(va, tt, T_end, w=w_)
        elif k == 4:                                                           # at the window: then his head turns to Bonasera
            _look(va, V_WIN + V_WIN_F * 2 + Vector((0, 0, 1.4)), 0.5 * (1 - _smooth((lt - 3.5) / 1.5)))
            _look(va, _head_of('bonasera'), 0.7 * _smooth((lt - 3.5) / 1.5))
        elif k in (5, 6): _look(va, B_KISS + Vector((0, 0, 1.55)), 0.6)
        elif k == 7:                                                           # the hand held out, palm down; his eyes on him
            e = people.envelope(lt, segs_v[7]['dur'], 0.8, 0.9)
            H0 = people._world(va, va.pose.bones['Bip01 R Hand']).translation.copy()
            g = H0.lerp(KISS, e)
            people.ik2(va, 'R', g, g - up_ * 0.3 + right * 0.3)
            people.palm_to(va, 'R', -up_, 0.9 * e)
            _look(va, KISS + Vector((0, 0, 0.25)), 0.7)
        elif k == 8:                                                           # the arm round Bonasera's shoulders
            dur = segs_v[8]['dur']; e = _smooth(lt / 0.8) * (1 - _smooth((lt - dur + 1.2) / 1.0))
            i = min(int(round(tt * FPS)), len(b_shoulder) - 1); sh = b_shoulder[i]
            H0 = people._world(va, va.pose.bones['Bip01 R Hand']).translation.copy()
            g = H0.lerp(sh + Vector((0, 0, 0.03)), e)
            people.ik2(va, 'R', g, g - up_ * 0.2 + right * 0.2 - fwd * 0.2)
            people.palm_to(va, 'R', -up_, 0.6 * e)
            _look(va, sh + Vector((0, 0, 0.25)), 0.5)
        elif k == 11:                                                          # with Hagen: the rose to his nose
            e = people.envelope(lt - 2.0, 2.4, 0.7, 0.8) if 2.0 < lt < 4.4 else 0.0
            _look(va, H_MEET + Vector((0, 0, 1.6)), 0.7 * (1 - e))
            if e > 0:
                rose = people._world(va, va.pose.bones['Bip01 Spine2']).translation + fwd * 0.14 - right * 0.09 - up_ * 0.02
                H0 = people._world(va, va.pose.bones['Bip01 L Hand']).translation.copy()
                g = H0.lerp(rose + up_ * 0.04, e)
                people.ik2(va, 'L', g, g - up_ * 0.3 - right * 0.3)
                people.bend(va, 'Bip01 Neck', right, -0.3 * e); people.bend(va, 'Bip01 Head', right, -0.35 * e)   # his nose down to it
        elif k == 15: _stroke(va, tt, T_end); _rest_left(va, tt, T_end)
    v_scene = people.sequence(va, stroke, 'vito_scene', segs_v, overlay=v_overlay)
    for a in (up, down, walk, talk, turn, stroke): bpy.data.actions.remove(a)
    va['open_act'], va['open_at'] = 'scene', round(tv[5] - 2.0, 2)              # the room opens as he leaves the window
    OPEN['vito'] = ('scene', va['open_at'])
    acts['vito']['scene'] = v_scene
    acts['bonasera']['scene'] = b_scene
    v_heads = _samples(va, v_scene)
    # ---- Hagen: up from his chair as the Don rises, across to the desk; then to the Don; back to his papers
    hup, hupf, _ = people.retarget(ha, 'm_sit_stand_up_chair_01', action_name='hagen_src_up')
    hdown, hdownf, _ = people.retarget(ha, 'm_sit_down_chair_01', action_name='hagen_src_down')
    hwalk, hwalkf, hs = people.retarget(ha, 'm_walk_neutral_02', inplace=True, cycles=8, action_name='hagen_src_walk')
    hlis, hlisf, _ = people.retarget(ha, 'm_gestic_listen_neutral_01', cycles=6, action_name='hagen_src_listen')
    h0f = int(papers.frame_range[0])
    _h, ph_s = people.heading(ha, papers, h0f); hh_s = Vector(ha['fwd'])
    hu_, pu_ = people.heading(ha, hup, hupf[0]); MH_up = people.carry(pu_, hu_, ph_s, hh_s)
    hu1_, pu1_ = _ends(ha, hup, hupf[1], MH_up)
    hd_, pd_ = people.heading(ha, hdown, hdownf[1]); MH_down = people.carry(pd_, hd_, ph_s, hh_s)
    hd0_, pd0_ = _ends(ha, hdown, hdownf[0], MH_down)
    hup_dur, hdown_dur = (hupf[1] - hupf[0]) / FPS, (hdownf[1] - hdownf[0]) / FPS
    r_h1 = people.path([pu1_, Vector((-3.62, -1.2, 0)), Vector((-3.6, -0.2, 0)), H_STAND])
    r_h2 = people.path([H_STAND, Vector((-2.8, 0.22, 0)), Vector((-1.85, 0.32, 0)), H_MEET])
    r_h3 = people.path([H_MEET, Vector((-2.3, 0.08, 0)), Vector((-3.3, -0.9, 0)), pd0_])
    hl_, pl_ = people.heading(ha, hlis, hlisf[0])
    MH_stand = people.carry(pl_, hl_, H_STAND, H_STAND_F); MH_meet = people.carry(pl_, hl_, H_MEET, _flat(V_MEET - H_MEET))
    t_hup = tv[2]; t_hgo2 = tv[10] - 0.5
    t_hstand = t_hup + hup_dur + r_h1[1] / hs
    t_hmeet = t_hgo2 + r_h2[1] / hs
    t_hback = tv[12] + 0.8
    t_hsit = t_hback + r_h3[1] / hs
    drop = Hg['drop']
    segs_h = [dict(src=papers, f0=h0f, dur=t_hup, at=Matrix.Identity(4)),
              dict(src=hup, f0=hupf[0], dur=hup_dur, at=MH_up, blend=0.7),
              dict(src=hwalk, f0=hwalkf[0], dur=r_h1[1] / hs, at=people.walk_along(ha, hwalk, hwalkf[0], hs, r_h1), blend=0.8),
              dict(src=hlis, f0=hlisf[0], dur=t_hgo2 - t_hstand, at=MH_stand, blend=0.8),
              dict(src=hwalk, f0=hwalkf[0] + 10, dur=r_h2[1] / hs, at=people.walk_along(ha, hwalk, hwalkf[0], hs, r_h2), blend=0.8),
              dict(src=hlis, f0=hlisf[0] + 60, dur=t_hback - t_hmeet, at=MH_meet, blend=0.8),
              dict(src=hwalk, f0=hwalkf[0] + 20, dur=r_h3[1] / hs, at=people.walk_along(ha, hwalk, hwalkf[0], hs, r_h3), blend=0.8),
              dict(src=hdown, f0=hdownf[0], dur=hdown_dur, at=MH_down, blend=0.9),
              dict(src=papers, f0=h0f, dur=max(1.5, T_end - t_hsit - hdown_dur), at=Matrix.Identity(4), blend=1.0)]
    th = [0.0]
    for sg in segs_h: th.append(th[-1] + sg['dur'])
    cine.log(f'hagen walks at {hs:.2f} m/s: up {t_hup:.1f}, stands {t_hstand:.1f}, meets {t_hmeet:.1f}, back {t_hback:.1f}, down {th[8]:.1f}, ends {th[-1]:.1f} (the Don {T_end:.1f})')
    def h_overlay(tt, k, lt):
        if k == 1: people.shift_root(ha, (0, 0, -drop * (1 - _smooth(lt / (hup_dur * 0.6)))))
        if k == 7: people.shift_root(ha, (0, 0, -drop * _smooth((lt - hdown_dur * 0.4) / (hdown_dur * 0.6))))
        if k in (3, 5):
            i = min(int(round(tt * FPS)), len(v_heads) - 1); _look(ha, v_heads[i], 0.6)
    h_scene = people.sequence(ha, papers, 'hagen_scene', segs_h, overlay=h_overlay)
    for a in (hup, hdown, hwalk, hlis, papers): bpy.data.actions.remove(a)
    acts['hagen']['scene'] = h_scene
    # ---- Sonny watches it all from the window, his glass in hand (a sip halfway)
    sa, sbase, sfr = S['arm'], S['base'], S['frames']
    n = int(round(T_end * FPS)); k_ = max(1, math.ceil(n / (sfr[1] - sfr[0])) + 1)
    swbase, swf, _ = people.retarget(sa, CAST[3]['base'], cycles=k_, action_name='sonny_watch_base')
    def s_step(f, t):
        i = min(int(round(t * FPS)), len(v_heads) - 1)
        e = people.envelope(t - 30.0, 5.0, 1.4, 1.6) if 30.0 < t < 35.0 else 0.0
        Hd = people._world(sa, sa.pose.bones['Bip01 Head']).translation; pel, fwd, right, up_ = people.body_frame(sa)
        mouth = Hd + fwd * 0.12 - up_ * 0.13 - right * 0.03
        _hold_glass(sa, at=_glass_hold(sa).lerp(mouth, e), tilt=0.6 * e); _pocket(sa)
        _look(sa, v_heads[i], 0.7 * (1 - e))
    acts['sonny']['watch'] = people.custom_act(sa, swbase, (swf[0], swf[0] + n), 'sonny_watch', s_step, _all(sa, fingers=True))
    bpy.data.actions.remove(swbase)
    # ---- the cat: lifted onto the desk and back, legs hanging as it goes, breathing and looking round on the desk
    def c_pose(arm, t, T):
        CAT.breathe(arm, t, T)
        a0, a1, b0, b1 = beats
        hang = (_smooth((t - a0) / 0.5) * (1 - _smooth((t - a1) / 0.5))) + (_smooth((t - b0) / 0.5) * (1 - _smooth((t - b1) / 0.5)))
        CAT.paw(arm, 'a', -0.8 * hang); CAT.paw(arm, 'b', -0.6 * hang)
        on_desk = _smooth((t - a1 - 1.0) / 1.0) * (1 - _smooth((t - b0 + 1.5) / 1.0))
        CAT.head(arm, yaw=0.5 * on_desk * math.sin(2 * math.pi * (t - a1) / 9.0), pitch=-0.3 * on_desk + 0.15 * hang)
    cat_acts['scene'] = CAT.act(carm, 'cat_scene', T_end, lambda t: _cat_path(t, beats), c_pose)
    cine.log(f'the scene: {T_end:.1f} s; the room opens at {OPEN["vito"][1]}')


# ---------------------------------------------------------------- bake and export
def bake(sc, objs, phantoms, seated, args):
    """The room's light baked into atlases (the people and the cat out of it: all of them move); then room.glb, the
    people and room.json."""
    os.makedirs(WEB, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    for c, arm, mesh in seated: mesh.hide_render = True
    export, atlases = stages.bake(objs, R.RH, OUT, int(args.get('size', 2048)), int(args.get('samples', 320)))
    for c, arm, mesh in seated: mesh.hide_render = False
    cine.export_glb(export, os.path.join(WEB, 'room.glb'))
    meta = stages.room_meta(R.RH, atlases); meta.update(_capture_meta())
    meta['people'] = _export_people(seated)
    stages.write_meta(WEB, meta)


def _export_people(seated):
    """One glTF a person (and one for the cat, carried by its own root bone), and their entries for room.json."""
    out = os.path.join(WEB, 'people'); os.makedirs(out, exist_ok=True); metas = []
    for c, arm, mesh in seated:
        people.export_person(arm, mesh, c['acts'], os.path.join(out, f"{c['who']}.glb"), roam=c.get('roam', ()),
                             pelvis='cat_root' if c['who'] == 'cat' else 'Bip01 Pelvis')
        metas.append(person_meta(c))
    return metas


def _capture_meta():
    """How to light the people as the bake lit the room (three.js: y up, z = -Blender y): the lamps and the sconce's
    bulbs and the top light as small bright spheres, the shuttered windows and the hall's glazed door as glowing panes."""
    bulbs = []
    for l in bpy.data.objects:
        if l.type != 'LIGHT' or l.data.type not in ('POINT', 'SPOT', 'AREA') or l.name.startswith(('sky', 'hall_sun')): continue
        r = 0.3 if l.data.type == 'AREA' else 0.03; e = l.data.energy
        bulbs.append({'x': round(l.location.x, 3), 'y': round(l.location.z, 3), 'z': round(-l.location.y, 3), 'r': r,
                      'L': round(e / (4 * math.pi * r ** 2) / 60, 2), 'color': [round(c, 3) for c in l.data.color]})
    z0, z1 = R.WIN_Z
    windows = [{'x': round(c, 3), 'y': round((z0 + z1) / 2, 3), 'z': round(-(R.BACK + 0.05), 3), 'w': R.WW, 'h': round(z1 - z0, 3), 'L': 1.6,
                'color': list(R.SUN), 'ry': 0.0} for c in R.WINDOWS]
    windows.append({'x': round(R.LEFT - 0.05, 3), 'y': round((z0 + z1) / 2, 3), 'z': round(-R.LWIN, 3), 'w': R.WW, 'h': round(z1 - z0, 3), 'L': 1.3,
                    'color': list(R.SUN), 'ry': round(math.pi / 2, 4)})
    fx, fw, fh, sw = R.FRONT_DOOR
    windows.append({'x': fx, 'y': round(fh / 2, 3), 'z': round(-(R.BACK + 0.05), 3), 'w': round(fw + 2 * sw, 3), 'h': fh, 'L': 2.4, 'color': list(R.SUN), 'ry': 0.0})
    return {'capture': {'ceiling': [0.2, 0.16, 0.12], 'walls': [0.1, 0.07, 0.05], 'emitters': bulbs, 'windows': windows,
                        'at': [[-1.7, 1.2, -1.2], [3.4, 1.3, -1.6]]}}


def person_meta(c):
    """The acts in a person's file, the looping one first, how long it lasts and how often each idle comes up; an act
    that cues others names them; the act the room opens on, and how far into it."""
    work, lo, hi = c['work']
    acts = [{'name': work, 'loop': True, 'min': lo, 'max': hi}]
    for k, (clip, w) in c['idles'].items():
        if k not in c['acts']: continue
        a = {'name': k, 'w': w}
        if k in c.get('cue', {}): a['cue'] = c['cue'][k]
        if FIRST.get(c['who']) == k: a['first'] = True
        if OPEN.get(c['who'], (None,))[0] == k: a['at'] = OPEN[c['who']][1]
        acts.append(a)
    for k in c['acts']:
        if k != work and k not in c['idles']: acts.append({'name': k, 'w': 0})      # only ever cued
    return {'who': c['who'], 'file': f"{c['who']}.glb", 'acts': acts}


def people_stage(sc, cams, seated, args):
    """Re-export only the people (their glTF files and their part of room.json); the baked room stays as it is. Then a
    look at each of them in the room (Cycles)."""
    stages.update_meta(WEB, people=_export_people(seated), **_capture_meta())
    for c, arm, mesh in seated: people.pose_at(arm, c['acts'][c['work'][0]], 60)
    for which in str(args.get('cams', 'vito,bonasera,hagen,sonny')).split(','):
        preview(sc, cams, which, int(args.get('samples', 64)), os.path.join(OUT, f'people_{which}.png'), size=(900, 900))
