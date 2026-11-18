# Rear Window: assemble Jefferies' studio (the window the case's glass), its people (Jeff in the wheelchair with
# his long lens, Lisa) and the room's rig (the hall door, the bottle, the cork, the glasses, her stole); then
# preview, bake (the dusk, and each of the three lamps Lisa switches on, as passes of their own) and export.
import math, os, random
import bpy
from mathutils import Vector, Matrix, Quaternion
import cine, people, stages
from stages import camera
import rooms.rear_window as R

ROOM = 'rear-window'
OUT = os.path.join(cine.OUT, ROOM)
WEB = os.path.join(cine.ROOT, 'public', 'rooms', ROOM)
PEOPLE_TEX = os.path.join(cine.OUT, 'people')
ARGS = {}
SEATED = []
MATS = {}
RIG = {'lights': None, 'props': None, 'shades': []}


def build(args):
    ARGS.clear(); ARGS.update(args)
    sc = cine.reset(int(args.get('samples', 256)))
    M = R.mats(); MATS.update(M)
    static, phantom, crowd = cine.coll('static'), cine.coll('phantom'), cine.coll('people')
    rnd = random.Random(1954)
    RIG['props'] = {k: R.mx(v) for k, v in R.jeff_corner(M, static).items()}
    seated = [] if args.get('nocast') else cast(crowd, args)
    SEATED[:] = seated
    R.shell(M, static, phantom)
    R.daybed(M, static)
    R.stole(M, static, R.mx(STOLE_REST))
    R.kitchenette(M, static)
    R.bookcases(M, static, rnd)
    b_desk = R.south_wall(M, static, rnd)
    b_cel = R.east_wall(M, static)
    b_pleat = R.pleated_lamp(M, static)
    R.rug(M, static)
    hb = R.hall(M, static)
    R.models(M, static)
    RIG['lights'] = R.lights([b_pleat, b_cel, b_desk], hb)
    RIG['shades'] = [('pleat_shade', 'pleat_bulb'), ('celadon_shade', 'celadon_bulb'), ('desk_lamp_shade', 'desk_lamp_bulb')]
    if args.get('nocast'): _static_props(M, static)
    if args.get('lamps'): _lamps_on(True)
    objs = [o for o in static.objects if o.type == 'MESH']; phantoms = [o for o in phantom.objects if o.type == 'MESH']
    bpy.context.view_layer.update()
    cine.bake_ready(objs + phantoms)
    for o in objs + phantoms:
        if not o.data.uv_layers: cine.world_uv(o, 1.0)
        elif 'UVMap' not in o.data.uv_layers: o.data.uv_layers[0].name = 'UVMap'
    if R.MIRROR:                                                        # the room turned over: the west wall on the right
        F_ = Matrix.Scale(-1, 4, (1, 0, 0))
        for o in objs + phantoms: o.data.transform(F_); o.data.flip_normals(); o.data.update()
        for group in [RIG['lights']['dusk']] + RIG['lights']['lamps']:
            for l in group: l.location.x = -l.location.x
    R.section(objs, M)
    objs = _merge(objs)
    for o in phantoms: cine.phantom(o)
    cine.check_module(objs)
    cams = {'case': camera('cam_case', (-0.6, -17.0, 7.0), (0.6, 0.3, 0.8), 30),
            'close': camera('cam_close', (0.8, -7.6, 2.6), (1.2, 0.0, 0.9), 40),
            'jeff': camera('cam_jeff', (2.2, -4.6, 1.5), (3.1, -2.5, 1.0), 40),          # Jeff from the courtyard, at the window
            'room': camera('cam_room', (1.0, -3.3, 1.6), (1.4, 2.6, 1.2), 62),           # from the window into the room: the desk wall
            'west': camera('cam_west', (-1.2, -2.0, 1.6), (4.6, -0.4, 1.2), 60),         # the kitchenette and the bookcases
            'east': camera('cam_east', (2.6, -1.0, 1.6), (-2.3, 0.8, 1.2), 58),          # the fireplace and the door
            'hall': camera('cam_hall', (-3.5, -4.6, 1.8), (-3.4, 2.6, 1.0), 50),
            'top': camera('cam_top', (0.0, 0.0, 14.0), (0.0, 0.1, 0.0), 38),
            'bed': camera('cam_bed', (1.3, -4.8, 1.4), (1.3, -3.1, 0.6), 50),
            'lisa': camera('cam_lisa', (-3.2, 1.0, 1.5), (-3.45, 3.2, 1.0), 42),     # Lisa in the stairwell
            'act': camera('cam_act', (1.0, -6.4, 2.6), (1.4, -1.2, 0.9), 48),
            'jeff_face': camera('cam_jeff_face', (2.7, -3.9, 1.45), (3.1, -2.55, 1.38), 16),
            'lisa_face': camera('cam_lisa_face', (-3.45, 2.1, 1.55), (-3.45, 3.2, 1.5), 22)}
    return sc, M, objs, list(phantom.objects), seated, cams


def _static_props(M, col):
    """Without the cast: the props where they rest (to judge the set)."""
    pass


def _lamps_on(on):
    """Each lamp's shade and bulb glowing, and its light shown (a preview of the evening with the lamps lit)."""
    for k, group in enumerate(RIG['lights']['lamps']):
        for l in group: l.hide_render = not on
    for mname, s in (('shade_pleat', 1.4), ('shade_drum', 1.4), ('shade_grey', 0.9), ('bulb_off', 14.0)):
        m = bpy.data.materials.get(mname)
        if m: m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = s if on else 0.0


KEEP = ('left_', 'back_', 'kerb', 'floor', 'subfloor', 'books_shelved', 'lightwell', 'hall_face')


def _merge(objs):
    """Join the many small pieces, one object per atlas and material: fewer meshes to draw."""
    groups = {}
    for o in objs:
        if o.get('role') or o.get('backdrop') or len(o.material_slots) != 1 or o.name.startswith(KEEP): continue
        if o.name.startswith(('pleat_', 'celadon_', 'desk_lamp_')): continue    # the lamps' shades and bulbs stay apart (the web lights them)
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
    """pose=who:act:frame poses one person; seq=who:act:s1;s2;... renders the act at those seconds with everyone it
    cues (and the rig) posed alongside."""
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
# Jeff in the wheelchair at the window's west end, his left leg in plaster from hip to toes on the chair's raised leg
# rest, his Exakta with the long lens in his right hand (on his lap, or up at his eye, watching the courtyard: us);
# Lisa, in the Paris dress, coming in from the hall. Costumes after Edith Head (people_textures.rear_window). Lisa's
# act (`scene`) leads: she comes in, bends and kisses him awake, switches on the three lamps, shows the dress and
# twirls, takes the bottle from its bucket and hands it to him; he thumbs the cork out, she pours, gives him his glass,
# they touch glasses and drink; she sits on the daybed's end, lies back along it, talks; up again, her glass back on
# the table, her stole off the armchair, goodnight from the door, out down the hall. He goes back to the window.
def _tex(who, prefix, *names):
    return {f'{prefix}_{n}.tga': f'{who}/{prefix}_{n}.png' for n in names}


# their heads: made in Tripo Studio from the film's close-ups (rooms/pulp_fiction_heads.py; Lisa's hair painted
# blonde by rooms/rear_window_heads.py), their eyes on the avatars' eye joints, their busts cut away round the neck
JEFF_HEAD = os.path.join(cine.OUT, 'people', 'jeff', 'jeff_head.glb')
LISA_HEAD = os.path.join(cine.OUT, 'people', 'lisa', 'lisa_head.glb')
CAST = [
    dict(who='jeff', avatar='Male_Adult_08', shape=('lean', 0.6), height=1.88,
         head=dict(glb=JEFF_HEAD, front='-y', eyes=((-0.174, -0.31, 0.122), (-0.007, -0.31, 0.122)), cut=0.0, fan_cut=-0.04, keep_r=(0.12, 0.072), tone=(1.5, 1.42, 1.38)),
         tex=_tex('jeff', 'm014', 'head_color', 'body_color', 'body_normal')),
    dict(who='lisa', avatar='Female_Adult_17', shape=('lean', 0.5), height=1.69,
         head=dict(glb=LISA_HEAD, front='-y', eyes=((-0.068, -0.26, 0.164), (0.113, -0.26, 0.164)), cut=0.0, fan_cut=-0.085, keep_r=(0.13, 0.08), tone=(2.25, 2.1, 2.0)),
         tex=_tex('lisa', 'f006', 'body_color', 'body_normal')),
]
BASES = {'jeff': 'm_sit_chair_breathe_01', 'lisa': 'f_idle_neutral_01'}
WORK = {'jeff': ('watch', 20, 40), 'lisa': ('wait', 6, 12), 'room': ('rest', 20, 40)}
FIRST = {'lisa': 'scene'}
CUE = {'lisa': {'scene': {'jeff': 'scene', 'room': 'scene'}}}
SPINE = ('Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2')
ARMS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('Clavicle', 'UpperArm', 'Forearm', 'Hand'))
LEGS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('Thigh', 'Calf', 'Foot'))
FINGERS = tuple(f'Bip01 {s} Finger{f}{j}' for s in 'LR' for f in '01234' for j in ('', '1', '2'))
ALL = ('Bip01 Pelvis',) + SPINE + ARMS + LEGS + ('Bip01 Neck', 'Bip01 Head')
HANDS = {}                                  # who -> {frame: (L hand matrix, R hand matrix)} in the scene (for the rig)
HEADS = {}                                  # who -> {frame: head position} in the scene (for looks)

# the scene's clock (seconds into Lisa's `scene`); her walks fill what lies between
TL = dict(go=2.0, door=5.0, door_open=(5.5, 6.6), door_close=(9.6, 10.8), kiss=14.2, kiss_end=18.2,
          lamp1=22.6, lamp2=29.0, lamp3=35.6, show=39.0, show_end=46.0,
          bottle_grab=49.2, bottle_give=51.0, pop=54.0, bottle_back=55.6, pour_a=56.4, pour_b=58.6, bottle_home=60.8,
          glass_grab=61.8, glass_give=63.0, glass_own=64.0, toast=65.4, drink=66.0,
          sit=71.4, jeff_glass_put=73.4, lie=82.0, cam_up=86.0, cam_down=97.0, sit_up=98.0, glass_put=104.0,
          stole=109.0, wave=114.0, door2=116.6, door2_open=(116.9, 118.0), door2_close=(121.0, 122.2), cam_up2=120.0, end=128.0)
STAIR_P = Vector((-3.45, 3.2))              # Lisa's place between scenes: in the stairwell, out of sight
HALL_DOOR = Vector((-2.86, 2.0)); IN_DOOR = Vector((-1.86, 2.0))
KISS_P = Vector((2.5, -2.56))
LAMP_P = [(Vector((0.26, -2.68)), (-0.55, -0.83)), (Vector((-1.5, -0.42)), (-1.0, 0.0)), (Vector((1.52, 1.78)), (0.0, 1.0))]
SWITCH = [Vector((-0.06, -3.22, 1.0)), Vector((-1.98, -0.42, 1.02)), Vector((1.52, 2.36, 1.12))]
SHOW_P = Vector((0.95, -1.05))
STAND_P = Vector((2.28, -1.6))
SIT_P, SIT_F = Vector((1.8, -3.14)), Vector((0.86, 0.5)).normalized()
LIE_P = Vector((1.25, -3.14, R.BED_TOP + 0.14))
STOLE_P, STOLE_F = Vector((-1.16, -0.96)), Vector((-0.78, -0.62)).normalized()
STOLE_REST = Vector((-1.86, -1.22, 0.69))    # draped over the armchair's arm
GIVE = Vector((2.78, -2.2, 0.95))            # the hand-over, at Jeff's right
CHAIR_T, CHAIR_FT = R.mx(R.CHAIR), R.mx(R.CHAIR_F)


def _all(arm, fingers=False):
    return (next(b.name for b in arm.data.bones if b.parent is None),) + ALL + (FINGERS if fingers else ())


def _smooth(x):
    x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)


def _win(t, a, b, rise=0.5, fall=0.5):
    """1 between a and b, eased in and out over rise and fall seconds."""
    return _smooth((t - a) / rise) * (1 - _smooth((t - b) / fall))


def _live(arm):
    pb = arm.pose.bones['Bip01 Pelvis']; M = people._world(arm, pb)
    f = M.to_3x3() @ Vector(arm['pel_fwd']); f.z = 0; f.normalize()
    up = Vector((0, 0, 1)); return M.translation.copy(), f, f.cross(up).normalized(), up


def _P(arm, bone):
    return people._world(arm, arm.pose.bones[bone]).translation.copy()


def _look(arm, at, w, limit=1.3):
    if w <= 0: return
    H = _P(arm, 'Bip01 Head'); pel, f, right, up = _live(arm)
    d = (Vector(at) - H).normalized()
    yaw = math.atan2(d.dot(-right), d.dot(f)); pitch = math.asin(max(-1, min(1, d.z)))
    yaw = max(-limit, min(limit, yaw)); pitch = max(-0.8, min(0.6, pitch))
    people.bend(arm, 'Bip01 Neck', up, yaw * 0.35 * w); people.bend(arm, 'Bip01 Head', up, yaw * 0.65 * w)
    people.bend(arm, 'Bip01 Neck', right, pitch * 0.3 * w); people.bend(arm, 'Bip01 Head', right, pitch * 0.7 * w)


def _turn_root(arm, pivot, axis, angle):
    root = next(pb for pb in arm.pose.bones if pb.parent is None)
    M = people._world(arm, root); R_ = Matrix.Translation(pivot) @ Matrix.Rotation(angle, 4, Vector(axis)) @ Matrix.Translation(-Vector(pivot))
    root.matrix = arm.matrix_world.inverted() @ R_ @ M
    bpy.context.view_layer.update()


def _hand_to(arm, side, tgt, w, pole, palm=None, pw=0.8):
    if w <= 0: return
    H0 = _P(arm, f'Bip01 {side} Hand'); g = H0.lerp(Vector(tgt), min(w, 1.0))
    people.ik2(arm, side, g, Vector(pole))
    if palm is not None: people.palm_to(arm, side, Vector(palm).normalized(), pw * min(w, 1.0))


def _record(who, arm, f, hands=True):
    HEADS.setdefault(who, {})[f] = _P(arm, 'Bip01 Head')
    if hands: HANDS.setdefault(who, {})[f] = tuple(people._world(arm, arm.pose.bones[f'Bip01 {s} Hand']).copy() for s in 'LR')


def _skinned(mesh, bm, groups, mats, name):
    """Geometry made at the rest pose and joined into the body: `groups` = [(bone, vertex indices or None for all)]."""
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(name, me); [cl.objects.link(ob) for cl in mesh.users_collection]
    for m in mats: me.materials.append(m)
    me.transform(mesh.matrix_world.inverted()); ob.matrix_world = mesh.matrix_world.copy()
    for bone, ids in groups:
        vg = ob.vertex_groups.new(name=bone); vg.add(list(range(len(me.vertices))) if ids is None else ids, 1.0, 'REPLACE')
    people._joined(mesh, ob)


def _bust_cut(arm, mesh, who, keep_r):
    """The sculpt below the jaw: only its neck kept (within keep_r of the neck's axis; Lisa's pearl choker with it),
    its shoulders and the still's collar gone (the body's own neckline is painted)."""
    import bmesh
    J = people._joints(arm); jaw = J.get('Bip01 MJaw', J['Bip01 Head']).z - 0.02; nk = J['Bip01 Neck']
    k = next((i for i, sl in enumerate(mesh.material_slots) if sl.material and f'{who}_head' in sl.material.name), None)
    if k is None: cine.log('no sculpt material on', who); return
    bm = bmesh.new(); bm.from_mesh(mesh.data); W_ = mesh.matrix_world; dead = []
    for f in bm.faces:
        if f.material_index != k: continue
        q = W_ @ f.calc_center_median()
        dy = q.y - (nk.y - 0.01)                                             # in front of the neck (the jaw's underside) more is kept
        if q.z < jaw and math.hypot(q.x - nk.x, dy) > (keep_r[0] if dy < 0 else keep_r[1]): dead.append(f)
    bmesh.ops.delete(bm, geom=dead, context='FACES'); bm.to_mesh(mesh.data); bm.free(); mesh.data.update()
    cine.log(who, 'bust cut', len(dead), 'faces')


def _plaster_cast(arm, mesh):
    """Jeff's cast: white plaster from high on the left thigh to the toes (the toes bare), a little lumpy; each part
    of it rigid on its bone (a straight leg never bends it)."""
    import bmesh
    J = people._joints(arm); hip, knee, ank = J['Bip01 L Thigh'], J['Bip01 L Calf'], J['Bip01 L Foot']
    toe = J.get('Bip01 L Toe0', ank + Vector((0, -0.13, -0.06)))
    plaster = cine.material('plaster_cast', (0.86, 0.85, 0.8), rough=0.85)
    bm = bmesh.new(); groups = []
    def seg(a, b, ra, rb, bone, n=7, seg_=18):
        a, b = Vector(a), Vector(b); ax = (b - a).normalized(); u = ax.orthogonal().normalized(); v = ax.cross(u)
        rings = []
        for i in range(n + 1):
            t = i / n; c = a.lerp(b, t); r = ra + (rb - ra) * t
            rings.append([bm.verts.new(c + (u * math.cos(2 * math.pi * k / seg_) + v * math.sin(2 * math.pi * k / seg_)) * r * (1 + 0.04 * math.sin(k * 2.3 + i))) for k in range(seg_)])
        for A, B in zip(rings, rings[1:]):
            for k in range(seg_): bm.faces.new((A[k], A[(k + 1) % seg_], B[(k + 1) % seg_], B[k]))
        bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
        bm.verts.ensure_lookup_table(); return bone
    n0 = 0
    for a, b, ra, rb, bone in ((hip + (knee - hip) * 0.1 + Vector((0, 0, 0.01)), knee + (knee - hip).normalized() * 0.03, 0.108, 0.088, 'Bip01 L Thigh'),
                               (knee, ank + (ank - knee).normalized() * 0.03, 0.09, 0.07, 'Bip01 L Calf')):
        seg(a, b, ra, rb, bone); bm.verts.ensure_lookup_table(); groups.append((bone, list(range(n0, len(bm.verts))))); n0 = len(bm.verts)
    # the foot: a slipper of plaster from the ankle to the toes' roots
    fwd = (toe - ank); fwd.z = 0; fwd.normalize()
    sole = ank + Vector((0, 0, -0.07))
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(sole.lerp(sole + fwd * 0.17, 0.5) + Vector((0, 0, 0.035))) @ Matrix.Rotation(math.atan2(fwd.x, -fwd.y), 4, 'Z') @ Matrix.Diagonal((0.12, 0.2, 0.12, 1)))
    bm.verts.ensure_lookup_table(); groups.append(('Bip01 L Foot', list(range(n0, len(bm.verts)))))
    _skinned(mesh, bm, groups, [plaster], 'plaster_cast')


def _camera(arm, mesh):
    """The Exakta and its long lens, made in the world at the hand's present pose (up at his eye) and bound to the
    left hand (under the lens): a chrome body with black leather sides, the prism, the 400 mm lens's black barrel with chrome rings
    and a hood, a cord strap."""
    import bmesh
    from rooms.the_godfather_build import _bind
    chrome = cine.material('exakta_chrome', (0.78, 0.78, 0.76), rough=0.2, metal=1.0)
    black = cine.material('exakta_black', (0.02, 0.02, 0.022), rough=0.4)
    pel, fwd, right, up = _live(arm)
    H = _P(arm, 'Bip01 Head'); eye = H + fwd * 0.1 * K + up * 0.02 * K
    Rm = Matrix((list(right) + [0], list(fwd) + [0], list(up) + [0], [0, 0, 0, 1])).transposed()
    def cube(c, size, mat_i):
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(c) @ Rm @ Matrix.Diagonal((*size, 1)))
        for f in bm.faces[-6:]: f.material_index = mat_i
    def barrel(c0, c1, r0, r1, mat_i, seg=24):
        a, b = Vector(c0), Vector(c1); ax = (b - a).normalized(); u = ax.orthogonal().normalized(); v = ax.cross(u)
        A = [bm.verts.new(a + (u * math.cos(2 * math.pi * k / seg) + v * math.sin(2 * math.pi * k / seg)) * r0) for k in range(seg)]
        B = [bm.verts.new(b + (u * math.cos(2 * math.pi * k / seg) + v * math.sin(2 * math.pi * k / seg)) * r1) for k in range(seg)]
        fs = [bm.faces.new((A[k], A[(k + 1) % seg], B[(k + 1) % seg], B[k])) for k in range(seg)] + [bm.faces.new(list(reversed(A))), bm.faces.new(B)]
        for f in fs: f.material_index = mat_i
    bm = bmesh.new()
    body = eye + fwd * 0.05
    cube(body, (0.155, 0.05, 0.075), 0); cube(body + fwd * 0.002, (0.11, 0.052, 0.07), 1)       # chrome ends, leather middle
    cube(body + up * 0.05, (0.055, 0.045, 0.035), 0)                                              # the prism
    L0 = body + fwd * 0.025
    barrel(L0, L0 + fwd * 0.05, 0.022, 0.024, 0)
    barrel(L0 + fwd * 0.05, L0 + fwd * 0.3, 0.033, 0.036, 1)
    for k, z in enumerate((0.12, 0.2, 0.27)): barrel(L0 + fwd * z, L0 + fwd * (z + 0.012), 0.038, 0.038, 0)
    barrel(L0 + fwd * 0.3, L0 + fwd * 0.4, 0.042, 0.046, 1)                                        # the hood
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    _bind(arm, mesh, bm, 'Bip01 L Hand', [chrome, black], 'camera')


K = 1.0
CAM_HOLD = {}


def _cam_hands(arm, w_up, t=0.0, scan=0.0):
    """His hands on the camera: right on its body, left under the lens; up at his eye by w_up (watching the
    courtyard, swinging slowly by `scan`), else resting on his lap, the lens along his thigh, the left hand free."""
    pel, fwd, right, up = _live(arm)
    H = _P(arm, 'Bip01 Head')
    sw = math.sin(t * 0.35) * 0.18 * scan
    d = (fwd * math.cos(sw) - right * math.sin(sw)).normalized()
    eye = H + fwd * 0.1 * K + up * 0.02 * K
    l_up = eye + d * 0.25 - up * 0.07 - right * 0.01
    l_lap = pel + fwd * 0.34 * K + up * 0.17 * K - right * 0.04
    _hand_to(arm, 'L', l_lap.lerp(l_up, w_up), 1.0, pel - right * 0.45 - up * 0.2 + fwd * 0.1, palm=up, pw=0.8)
    if w_up > 0.02:
        r_up = eye + d * 0.04 + right * 0.05 - up * 0.05
        _hand_to(arm, 'R', r_up, w_up, pel + right * 0.45 - up * 0.2 + fwd * 0.1, palm=-right * 0.8 + fwd * 0.2 + up * 0.1, pw=0.8 * w_up)
    people.hand_shape(arm, 'L', 'fist', 0.45)
    if w_up > 0.02: people.hand_shape(arm, 'R', 'fist', 0.55 * w_up)
    if w_up > 0.5: _look(arm, eye + d * 2.0, (w_up - 0.5) * 2 * 0.9)


def make_person(c, col):
    tex = {k: os.path.join(PEOPLE_TEX, v) for k, v in c.get('tex', {}).items() if os.path.exists(os.path.join(PEOPLE_TEX, v))}
    arm, mesh = people.load_avatar(c['avatar'], textures=tex, collection=col)
    arm.animation_data_clear()
    mesh['person'] = c['who']; arm['person'] = c['who']
    if c.get('shape'): people.reshape(arm, mesh, *c['shape'])
    bpy.context.view_layer.update()
    top = max((mesh.matrix_world @ v.co).z for v in mesh.data.vertices)
    if c.get('head'):
        h = c['head']
        people.swap_head(arm, mesh, h['glb'], None, h['front'], h['eyes'], cut=h['cut'], fan_cut=h['fan_cut'], tone=h.get('tone'), neck_skin=h.get('neck_skin', False))
        _bust_cut(arm, mesh, c['who'], h['keep_r'])
        people.remove_hair_cards(mesh)
    J = people._joints(arm)
    if c['who'] == 'lisa':
        tulle = cine.material('tulle_skirt', rough=0.8, maps={'color': os.path.join(R.TEX, 'tulle_color.jpg')}, scale=1.0, sheen=0.6, sheen_tint=(0.7, 0.7, 0.7))
        people.skirt(arm, mesh, tulle, hem=J['Bip01 L Calf'].z - 0.16, top=0.1, ease=0.03, flare=0.42, folds=20, depth=0.022, seg=96, rows=30, name='skirt')
        for n in tulle.node_tree.nodes:                                   # the skirt's UVs take the body's map's name
            if n.type == 'UVMAP': n.uv_map = mesh.data.uv_layers.active.name
    if c['who'] == 'jeff': _plaster_cast(arm, mesh)
    for ca in list(mesh.data.color_attributes): mesh.data.color_attributes.remove(ca)
    s = c['height'] / top
    arm.scale = arm.scale * s; arm.location = (arm.location.x, arm.location.y, arm.location.z * s)
    bpy.context.view_layer.update()
    return arm, mesh


def cast(col, args):
    full = bool(args.get('full'))
    spec = {'cast': CAST, 'bases': BASES, 'work': WORK, 'cue': CUE, 'tl': TL, 'chair': [list(CHAIR_T), list(CHAIR_FT)], 'full': full, 'v': 9}
    for c in CAST:
        c['work'] = WORK[c['who']]; c['idles'] = {'scene': (None, 1.0 if c['who'] == 'lisa' else 0.0)}; c['cue'] = CUE.get(c['who'], {})
        c['roam'] = ('scene',) if c['who'] == 'lisa' else ()
    seated = stages.cast_cache(OUT, CAST, spec, lambda: _make_cast(col, full), col)
    seated += _room_rig(seated, col)
    for c, arm, mesh in seated:
        people.pose_at(arm, c['acts'][c['work'][0]], int(c['acts'][c['work'][0]].frame_range[0]) + 10)
    return seated


def _place(c, arm, at, f, base_name, cycles=2):
    who = c['who']; f = Vector((*f, 0)).normalized()
    people.face(arm, f); arm.location = (at[0], at[1], arm.location.z); bpy.context.view_layer.update()
    arm['fwd'] = list(f)
    base, frames, _ = people.retarget(arm, base_name, cycles=cycles, action_name=f'{who}_base')
    people.pose_at(arm, base, frames[0])
    pel = _P(arm, 'Bip01 Pelvis')
    arm.location.x += at[0] - pel.x; arm.location.y += at[1] - pel.y
    bpy.context.view_layer.update()
    people.pose_at(arm, base, frames[0])
    arm['pel_fwd'] = list(people._world(arm, arm.pose.bones['Bip01 Pelvis']).to_3x3().inverted() @ f)
    return base, frames


def _make_cast(col, full):
    seated, made = [], {}
    places = {'jeff': (tuple((CHAIR_T - CHAIR_FT * 0.06)[:2]), tuple(CHAIR_FT[:2])), 'lisa': (tuple(STAIR_P), (0.0, -1.0))}
    for c in CAST:
        arm, mesh = make_person(c, col)
        at, f = places[c['who']]
        base, frames = _place(c, arm, at, f, BASES[c['who']])
        made[c['who']] = dict(c=c, arm=arm, mesh=mesh, base=base, frames=frames, k=c['height'] / 1.78)
        seated.append((c, arm, mesh))
    acts = {k: {} for k in made}
    for m in made.values(): m['mesh'].hide_viewport = True
    for who, m in sorted(made.items(), key=lambda kv: kv[0] != 'lisa'):  # one at a time (Lisa first: Jeff looks at her), the other off
        for o, mm in made.items(): mm['arm'].hide_viewport = o != who
        (_lisa_acts if who == 'lisa' else _jeff_acts)(m, acts[who], full)
    for m in made.values(): m['arm'].hide_viewport = False
    for who, m in made.items():
        m['c']['acts'] = acts[who]
        if m['base'] not in acts[who].values(): bpy.data.actions.remove(m['base'])
        m['mesh'].hide_viewport = False
        people.pose_at(m['arm'], acts[who][m['c']['work'][0]], int(m['frames'][0]) + 10)
    return seated


# ---------------------------------------------------------------- Lisa
def _at(arm, src, f, p, h):
    hh, pp = people.heading(arm, src, f); return people.carry(pp, hh, Vector((p[0], p[1], 0)), Vector((h[0], h[1], 0)).normalized())


def _lisa_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS

    def wait(f, t):
        _look(arm, Vector((-3.45, 2.0, 1.5)) + Vector((0.3 * math.sin(t * 0.4), 0, 0)), 0.3)
    acts['wait'] = people.custom_act(arm, base, frames, 'lisa_wait', wait, _all(arm))
    if not full: return
    walk, wf, vs = people.retarget(arm, 'f_walk_self-assured', inplace=True, cycles=16, action_name='lisa_src_walk')
    idle, idf, _ = people.retarget(arm, 'f_idle_neutral_01', cycles=10, action_name='lisa_src_idle')
    door, dof, _ = people.retarget(arm, 'f_try_door_inwards', action_name='lisa_src_door')
    pres, pf, _ = people.retarget(arm, 'f_gestic_presentation_right_01', action_name='lisa_src_pres')
    turn, trf, _ = people.retarget(arm, 'f_turn_right_180', action_name='lisa_src_turn')
    talk, tf, _ = people.retarget(arm, 'f_gestic_talk_relaxed_01', cycles=3, action_name='lisa_src_talk')
    down, df, _ = people.retarget(arm, 'f_sit_down_chair_01', action_name='lisa_src_down')
    sitb, sbf, _ = people.retarget(arm, 'f_sit_chair_breathe_01', cycles=10, action_name='lisa_src_sit')
    upc, uf, _ = people.retarget(arm, 'f_sit_stand_up_chair_01', action_name='lisa_src_up')
    wave, wvf, _ = people.retarget(arm, 'f_wave_01', action_name='lisa_src_wave')
    cine.log(f'lisa walks at {vs:.2f} m/s')
    T = TL; segs = []; I = Matrix.Identity(4)
    def add(tag, **kw): kw['tag'] = tag; segs.append(kw)
    def pad(tag, until, **kw):
        t = sum(s['dur'] for s in segs); kw['dur'] = max(0.4, until - t); add(tag, **kw)
    def walk_to(tag, pts, off=0):
        r = people.path([Vector(p) for p in pts]); add(tag, src=walk, f0=wf[0] + off, dur=r[1] / vs, at=people.walk_along(arm, walk, wf[0] + off, vs, r), blend=0.7)
    def stand(tag, until, p, h, src=idle, f0=None, blend=0.7):
        f0 = (idf[0] if src is idle else f0) if f0 is None else f0
        pad(tag, until, src=src, f0=f0, at=_at(arm, src, f0, p, h), blend=blend)
    Fj = (-0.95, -0.3)                                                        # toward Jeff, from the room
    pad('wait', T['go'], src=base, f0=frames[0], at=I)
    walk_to('w_hall', [STAIR_P, (-3.45, 2.5), (-3.15, 2.05), HALL_DOOR])
    stand('at_door', T['door'], HALL_DOOR, (1, 0))
    stand('door', T['door'] + 1.6, HALL_DOOR, (1, 0), src=door, f0=dof[0], blend=0.5)
    walk_to('w_in', [HALL_DOOR, IN_DOOR, (-0.6, 0.9), (1.4, -1.5), KISS_P], off=10)
    stand('lean', T['kiss'], KISS_P, (1.0, 0.04), f0=idf[0] + 30)
    stand('kiss', T['kiss_end'], KISS_P, (1.0, 0.04), f0=idf[0] + 60, blend=0.5)
    for j, (p, h) in enumerate(LAMP_P):
        prev = KISS_P if j == 0 else LAMP_P[j - 1][0]
        mid = {0: [(1.0, -2.4)], 1: [(-0.8, -1.6)], 2: [(-0.2, 0.6)]}[j]
        walk_to(f'w_lamp{j}', [prev] + mid + [p], off=20 + 10 * j)
        stand(f'lamp{j}', T[f'lamp{j + 1}'] + 1.0, p, h, f0=idf[0] + 90 + 30 * j)
    walk_to('w_show', [LAMP_P[2][0], (1.3, 0.6), SHOW_P], off=50)
    stand('show_in', T['show'], SHOW_P, (0, -1), f0=idf[0] + 180)
    add('present', src=pres, f0=pf[0], dur=min((pf[1] - pf[0]) / FPS, 4.0), at=_at(arm, pres, pf[0], SHOW_P, (0, -1)), blend=0.6)
    add('twirl1', src=turn, f0=trf[0], dur=(trf[1] - trf[0]) / FPS, at=_at(arm, turn, trf[0], SHOW_P, (0, -1)), blend=0.4)
    add('twirl2', src=turn, f0=trf[0], dur=(trf[1] - trf[0]) / FPS, at=_at(arm, turn, trf[0], SHOW_P, (0, 1)), blend=0.3)
    stand('shown', T['show_end'], SHOW_P, (0, -1), f0=idf[0] + 210, blend=0.5)
    walk_to('w_stand', [SHOW_P, (1.7, -1.2), STAND_P], off=60)
    stand('bottle', T['glass_own'] + 0.6, STAND_P, (0.57, -0.82), f0=idf[0] + 240)
    stand('toast', T['sit'] - 3.0, STAND_P, (0.57, -0.82), f0=idf[0] + 270)
    walk_to('w_bed', [STAND_P, (2.0, -2.3), SIT_P - SIT_F * 0.32], off=70)
    stand('turn_sit', T['sit'], SIT_P - SIT_F * 0.32, -SIT_F, f0=idf[0] + 300, blend=0.6)
    add('sit', src=down, f0=df[0], dur=(df[1] - df[0]) / FPS, at=_at(arm, down, df[1], SIT_P, SIT_F), blend=0.6)
    pad('sat', T['lie'], src=sitb, f0=sbf[0], at=_at(arm, sitb, sbf[0], SIT_P, SIT_F), blend=0.6)
    pad('lie', T['sit_up'], src=sitb, f0=sbf[0] + 40, at=_at(arm, sitb, sbf[0] + 40, SIT_P, SIT_F), blend=0.3)
    pad('situp', T['sit_up'] + 2.0, src=sitb, f0=sbf[0] + 80, at=_at(arm, sitb, sbf[0] + 80, SIT_P, SIT_F), blend=0.3)
    add('stand_up', src=upc, f0=uf[0], dur=(uf[1] - uf[0]) / FPS, at=_at(arm, upc, uf[0], SIT_P, SIT_F), blend=0.6)
    walk_to('w_put', [SIT_P + SIT_F * 0.3, (2.0, -2.1), STAND_P], off=80)
    stand('put', T['glass_put'] + 1.0, STAND_P, (0.57, -0.82), f0=idf[0] + 330)
    walk_to('w_stole', [STAND_P, (0.8, -1.4), (-0.5, -1.3), STOLE_P], off=90)
    stand('stole', T['stole'] + 1.2, STOLE_P, STOLE_F, f0=idf[0] + 360)
    walk_to('w_door', [STOLE_P, (-1.2, 0.6), IN_DOOR], off=100)
    stand('turn_wave', T['wave'], IN_DOOR, (0.8, -0.6), f0=idf[0] + 390)
    add('wave', src=wave, f0=wvf[0], dur=min((wvf[1] - wvf[0]) / FPS, 2.6), at=_at(arm, wave, wvf[0], IN_DOOR, (0.8, -0.6)), blend=0.5)
    stand('door2', T['door2'] + 1.6, IN_DOOR, (-1, 0), src=door, f0=dof[0], blend=0.6)
    walk_to('w_out', [IN_DOOR, HALL_DOOR, (-3.2, 2.1), (-3.45, 2.6), STAIR_P], off=110)
    pad('gone', T['end'], src=base, f0=frames[0], at=I, blend=0.8)
    t = 0.0
    for sg in segs: sg['t0'] = t; t += sg['dur']
    cine.log('lisa scene: ' + ', '.join(f"{sg['tag']} {sg['t0']:.1f}" for sg in segs) + f' end {t:.1f}')
    jeff_head = Vector((CHAIR_T.x, CHAIR_T.y, 1.12))
    bottle_at = RIG['props']['bucket'] + Vector((0, 0, 0.2)); ga, gb = RIG['props']['glass_a'], RIG['props']['glass_b']
    give = GIVE
    pseated = people.pose_at(arm, sitb, sbf[0]); pz = _P(arm, 'Bip01 Pelvis').z
    lift = (R.BED_TOP + 0.08 * k) - pz

    def overlay(tt, i, lt):
        sg = segs[i]; tag = sg['tag']; f = int(round(tt * FPS))
        pel, fwd, right, up = _live(arm)
        sw = {'sit': _smooth((lt - 0.6) / 1.4), 'sat': 1.0, 'lie': 1.0, 'situp': 1.0, 'stand_up': 1 - _smooth(lt / 1.2)}.get(tag, 0.0)
        if sw > 0: people.shift_root(arm, (0, 0, lift * sw))
        if tag in ('lean', 'kiss'):                                           # bent over him, a hand on his shoulder
            e = _smooth(lt / 1.4) if tag == 'lean' else 1 - _smooth((lt - (sg['dur'] - 1.3)) / 1.3)
            if tag == 'lean' and lt < sg['dur'] - 1.4: e *= 0.0
            for b_, a in zip(SPINE, (0.22, 0.2, 0.16)): people.bend(arm, b_, right, -a * e)
            _look(arm, jeff_head, 0.9)
            sh = jeff_head + Vector((-0.12, 0.05, -0.25))
            _hand_to(arm, 'R', sh, e, sh + Vector((0.3, 0.3, -0.3)), palm=Vector((0, 0, -1)), pw=0.6)
        elif tag.startswith('lamp'):
            j = int(tag[4]); s_ = SWITCH[j]; tt0 = TL[f'lamp{j + 1}']
            w = _win(tt, tt0 - 0.9, tt0 + 0.3, 0.6, 0.6)
            _hand_to(arm, 'R', s_, w, s_ + right * 0.4 - up * 0.3, palm=-up, pw=0.5)
            _look(arm, s_, 0.6)
        elif tag in ('present', 'twirl1', 'twirl2', 'shown', 'show_in'):
            if tag in ('shown', 'show_in'): _look(arm, jeff_head, 0.5)
        elif tag == 'bottle':
            # the bottle out of the bucket, held out to him; back from him, poured into the two glasses, set back
            if tt < T['bottle_give']:
                g = bottle_at if tt < T['bottle_grab'] else bottle_at.lerp(give, _smooth((tt - T['bottle_grab']) / (T['bottle_give'] - T['bottle_grab'])))
                _hand_to(arm, 'R', g, _win(tt, T['bottle_grab'] - 0.8, T['bottle_give'] + 0.2, 0.6, 0.3), g + right * 0.4 - up * 0.3, palm=-right * 0.6 - fwd * 0.4, pw=0.6)
                _look(arm, g, 0.6)
            elif tt < T['bottle_back'] - 0.6:
                _hand_to(arm, 'R', give, 1 - _smooth((tt - T['bottle_give']) / 0.8), give + right * 0.4 - up * 0.3, palm=-right * 0.6 - fwd * 0.4, pw=0.6)
                _look(arm, give + Vector((0, 0, 0.1)), 0.7)
            else:
                pours = ((T['pour_a'], ga), (T['pour_b'], gb))
                if tt < T['bottle_back']: g = give
                elif tt < T['pour_a']: g = give.lerp(ga + Vector((0.0, 0.0, 0.24)), _smooth((tt - T['bottle_back']) / (T['pour_a'] - T['bottle_back'])))
                elif tt < T['pour_b']: g = ga.lerp(gb, _smooth((tt - T['pour_a'] - 1.2) / 0.8)) + Vector((0, 0, 0.24))
                elif tt < T['bottle_home']: g = (gb + Vector((0, 0, 0.24))).lerp(bottle_at, _smooth((tt - T['pour_b'] - 1.2) / 0.8))
                else: g = bottle_at.lerp(ga + Vector((0, 0, 0.08)), _smooth((tt - T['bottle_home'] - 0.2) / (T['glass_grab'] - T['bottle_home'] - 0.2)))
                tilt = max(_win(tt, T['pour_a'] + 0.2, T['pour_a'] + 1.0, 0.3, 0.3), _win(tt, T['pour_b'] + 0.2, T['pour_b'] + 1.0, 0.3, 0.3))
                wr = _smooth((tt - (T['bottle_back'] - 0.6)) / 0.6)
                if tt > T['glass_grab']:
                    g = (ga + Vector((0, 0, 0.08))).lerp(give, _smooth((tt - T['glass_grab']) / (T['glass_give'] - T['glass_grab'])))
                    wr *= 1 - _smooth((tt - T['glass_give'] - 0.2) / 0.8)
                    gl = gb + Vector((0, 0, 0.08)); wl = _smooth((tt - T['glass_give']) / 0.8)
                    _hand_to(arm, 'L', gl, wl, gl - right * 0.4 - up * 0.3, palm=right * 0.7 + up * 0.3, pw=0.6)
                palm = (-right * 0.6 - fwd * 0.4).lerp(-up, tilt)
                _hand_to(arm, 'R', g, wr, g + right * 0.4 - up * 0.3, palm=palm, pw=0.6)
                _look(arm, g, 0.6)
        elif tag == 'toast':
            near = give + Vector((0.05, 0.05, 0.1))
            held = pel + fwd * 0.3 * k + up * 0.3 * k - right * 0.12 * k
            mouth = _P(arm, 'Bip01 Head') + fwd * 0.08 + up * -0.06
            clink = _win(tt, T['toast'] - 0.5, T['toast'] + 0.3, 0.5, 0.5); sip = _win(tt, T['drink'], T['drink'] + 1.2, 0.8, 0.8)
            g = (gb + Vector((0, 0, 0.08))).lerp(held, _smooth(lt / 0.8)).lerp(near, clink).lerp(mouth, sip)
            _hand_to(arm, 'L', g, 1.0, g - right * 0.4 - up * 0.3, palm=right * 0.7 + up * 0.3, pw=0.6)
            _look(arm, jeff_head, 0.7 * (1 - sip))
        elif tag in ('w_bed', 'turn_sit', 'sit', 'sat'):
            held = pel + fwd * 0.28 * k + up * 0.28 * k - right * 0.12 * k
            mouth = _P(arm, 'Bip01 Head') + fwd * 0.08 + up * -0.06
            sip = _win(tt, T['sit'] + 4.0, T['sit'] + 6.0, 0.8, 0.8)
            g = held.lerp(mouth, sip)
            _hand_to(arm, 'L', g, 1.0, g - right * 0.4 - up * 0.3, palm=right * 0.7 + up * 0.3, pw=0.6)
            _look(arm, jeff_head, 0.6)
        elif tag in ('lie', 'situp'):
            w = _smooth(lt / 2.2) if tag == 'lie' else 1 - _smooth(lt / 1.8)
            held = pel + fwd * 0.28 * k + up * 0.28 * k - right * 0.12 * k
            _lie(arm, m, w)
            e = max(0.0, (w - 0.5) * 2); hip = _P(arm, 'Bip01 Pelvis') + Vector((-0.05, -0.08, 0.14))
            _hand_to(arm, 'L', held.lerp(hip, e), 1.0, held + Vector((-0.2, -0.3, 0.3)), palm=Vector((0, 0, -1)).lerp(right * 0.7 + up * 0.3, 1 - e), pw=0.5)
            _look(arm, jeff_head, 0.6)
        elif tag in ('stand_up', 'w_put', 'put', 'w_stole'):
            held = pel + fwd * 0.28 * k + up * 0.28 * k - right * 0.12 * k
            g = held; w = 1.0
            if tag == 'put': g = held.lerp(gb + Vector((0, 0, 0.02)), _win(tt, T['glass_put'] - 0.8, T['glass_put'] + 0.3, 0.6, 0.6))
            if tag == 'w_stole': w = 1 - _smooth(lt / 0.8)
            _hand_to(arm, 'L', g, w, g - right * 0.4 - up * 0.3, palm=right * 0.7 + up * 0.3, pw=0.6)
        elif tag == 'stole':
            w = _win(tt, T['stole'] - 0.8, T['stole'] + 0.3, 0.6, 0.6)
            _hand_to(arm, 'R', STOLE_REST + Vector((0, 0, 0.03)), w, STOLE_REST + right * 0.4 + up * 0.3, palm=-up, pw=0.6)
            for b_, a in zip(SPINE, (0.12, 0.1, 0.06)): people.bend(arm, b_, right, -a * w)
        elif tag in ('turn_wave', 'wave'):
            _look(arm, jeff_head, 0.8)
        _record('lisa', arm, f)
    acts['scene'] = people.sequence(arm, base, 'lisa_scene', segs, overlay=overlay)
    for a in (walk, idle, door, pres, turn, talk, down, sitb, upc, wave): bpy.data.actions.remove(a)
    m['scene_n'] = int(acts['scene'].frame_range[1] - acts['scene'].frame_range[0])


def _lie(arm, m, w):
    """From sitting on the daybed's end to lying along it on her right side, her head toward its pillows (-x), facing
    the window (-y), propped on her right elbow, her knees drawn up a little: the sitting pose turned to face -y, laid
    over about y (up -> -x), moved onto the mattress; the shoulders raised off it."""
    if w <= 0: return
    pel, fwd, right, up = _live(arm)
    a0 = math.atan2(fwd.y, fwd.x) - math.atan2(-1.0, 0.0)
    _turn_root(arm, pel, (0, 0, 1), -a0 * w)
    pel2 = _P(arm, 'Bip01 Pelvis')
    people.shift_root(arm, (LIE_P - pel2) * w)
    _turn_root(arm, LIE_P.lerp(pel2, 1 - w), (0, 1, 0), -math.radians(78) * w)
    if w > 0.5:
        e = (w - 0.5) * 2
        for b_, a in zip(SPINE, (0.1, 0.12, 0.1)): people.bend(arm, b_, Vector((0, 1, 0)), a * e)        # shoulders up off the mattress
        H = _P(arm, 'Bip01 Head'); el = H + Vector((0.02, 0.06, -0.24))
        _hand_to(arm, 'R', el, e, el + Vector((0.3, -0.2, -0.2)), palm=Vector((0, 0, -1)), pw=0.5)


# ---------------------------------------------------------------- Jeff
def _jeff_frame(arm, m, t, scene):
    """Jeff's pose at t: seated in the wheelchair, the plaster leg straight out on the leg rest; in the scene (or
    else watching the courtyard through the lens)."""
    k = m['k']
    people.shift_root(arm, (0, 0, m['lift']))
    pel, fwd, right, up = _live(arm)
    hip = _P(arm, 'Bip01 L Thigh')
    ank = hip + fwd * 0.9 * k - up * 0.12 * k + right * 0.0
    people.ik_leg(arm, 'L', ank, hip + fwd * 0.4 + up * 0.6, keep_foot=False)
    T = TL
    if not scene:                                                        # watching: up at the eye, now and then lowered a while
        u = (t % 26.0)
        w = 1.0 - _win(u, 17.0, 23.0, 1.2, 1.2)
        _cam_hands(arm, w, t, scan=1.0)
        if w < 0.5: _look(arm, Vector((pel.x + 0.6, pel.y - 4.0, 1.3)), 0.6)
        return
    lisa = HEADS.get('lisa', {}); f = int(round(t * people.FPS))
    at_lisa = lisa.get(f, Vector((0, 0, 1.5)))
    doze = _smooth((t - 3.2) / 2.0) * (1 - _smooth((t - (T['kiss'] + 0.8)) / 1.4))
    wake = 1 - _smooth((t - 3.2) / 2.0) + (1 - _smooth((t - (T['kiss'] + 0.8)) / 1.4) <= 0) * 0
    wake = 1.0 if t > T['kiss'] + 2.2 else 0.0 if t > 3.2 else 1 - doze
    up_w = max(1 - _smooth(t / 3.0), _win(t, T['cam_up'], T['cam_down'], 1.4, 1.4), _smooth((t - T['cam_up2']) / 1.6))
    _cam_hands(arm, up_w, t, scan=0.6)
    if doze > 0:                                                         # asleep: his head on his chest, a little slumped
        for b_, a in zip(SPINE, (0.04, 0.05, 0.06)): people.bend(arm, b_, right, a * doze)
        people.bend(arm, 'Bip01 Neck', right, 0.35 * doze); people.bend(arm, 'Bip01 Head', right, 0.25 * doze)
        people.bend(arm, 'Bip01 Head', fwd, 0.12 * doze)
    if up_w < 0.5 and wake > 0: _look(arm, at_lisa, 0.8 * wake * (1 - up_w * 2))
    # his right hand: the bottle taken from her, the cork thumbed out, the bottle back; his glass, the toast, a sip, set down
    give = GIVE
    def lh(g, w, palm=None):
        _hand_to(arm, 'R', g, w, pel + right * 0.5 - up * 0.1 + fwd * 0.1, palm=palm, pw=0.6)
    if T['bottle_give'] - 0.8 < t < T['bottle_back'] + 0.6:
        w = _win(t, T['bottle_give'] - 0.6, T['bottle_back'] + 0.1, 0.5, 0.5)
        g = give + (Vector((0.04, 0.12, 0.05)) if T['bottle_give'] + 0.6 < t < T['bottle_back'] - 0.4 else Vector())
        lh(g, w, palm=-right * 0.6 + fwd * 0.4)
        if T['pop'] - 1.6 < t < T['pop'] + 0.3: people.bend(arm, 'Bip01 R Finger0', up, 0.4 * _win(t, T['pop'] - 1.4, T['pop'], 0.6, 0.2))
        _look(arm, give + Vector((0, 0, 0.25)), 0.7 * w)
    elif T['glass_give'] - 0.8 < t < T['jeff_glass_put'] + 0.8:
        mouth = _P(arm, 'Bip01 Head') + fwd * 0.08 - up * 0.07
        held = pel + fwd * 0.3 * k + up * 0.3 * k + right * 0.14 * k
        clink = _win(t, T['toast'] - 0.5, T['toast'] + 0.3, 0.5, 0.5); sip = _win(t, T['drink'], T['drink'] + 2.4, 0.8, 0.8)
        g = give.lerp(held, _smooth((t - T['glass_give']) / 0.8)).lerp(give + Vector((0.0, 0.05, 0.1)), clink).lerp(mouth, sip)
        if t > T['jeff_glass_put'] - 1.2: g = g.lerp(RIG['props']['glass_a'] + Vector((0, 0, 0.02)), _smooth((t - (T['jeff_glass_put'] - 1.2)) / 1.0))
        w = _win(t, T['glass_give'] - 0.6, T['jeff_glass_put'] + 0.2, 0.5, 0.6)
        lh(g, w, palm=-right * 0.7 + up * 0.3)
    elif T['wave'] < t < T['wave'] + 2.6:
        w = _win(t, T['wave'], T['wave'] + 2.2, 0.6, 0.6)
        g = pel + up * 0.65 * k + fwd * 0.18 * k + right * 0.3 * k + right * 0.06 * math.sin(t * 9) * w
        lh(g, w, palm=fwd)


def _jeff_acts(m, acts, full):
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; FPS = people.FPS
    people.pose_at(arm, base, frames[0])
    m['lift'] = (0.52 + 0.08 * k) - _P(arm, 'Bip01 Pelvis').z
    cine.log(f'jeff in the chair: lifted {m["lift"]:+.3f}')
    # the camera, bound to his right hand as he holds it up at his eye
    people.shift_root(arm, (0, 0, m['lift'])); _cam_hands(arm, 1.0, 0.0, scan=0.0); _camera(arm, m['mesh'])
    n = int(26.0 * FPS)
    longw, lwf, _ = people.retarget(arm, BASES['jeff'], cycles=12, limit=n + 10, action_name='jeff_src_watch')
    acts['watch'] = people.custom_act(arm, longw, (lwf[0], lwf[0] + n), 'jeff_watch', lambda f, t: _jeff_frame(arm, m, t, False), _all(arm, fingers=True))
    bpy.data.actions.remove(longw)
    if not full: return
    n = int(round(TL['end'] * FPS))
    longb, lf, _ = people.retarget(arm, BASES['jeff'], cycles=40, limit=n + 10, action_name='jeff_src_long')
    def scene(f, t):
        _jeff_frame(arm, m, t, True); _record('jeff', arm, f - lf[0])
    acts['scene'] = people.custom_act(arm, longb, (lf[0], lf[0] + n), 'jeff_scene', scene, _all(arm, fingers=True))
    bpy.data.actions.remove(longb)


# ---------------------------------------------------------------- the room's rig
def _room_rig(seated, col):
    import rooms.rear_window_rig as RG
    arm, mesh = RG.make_rig(RIG['props'], MATS, col)
    c = dict(who='room', work=WORK['room'], idles={'scene': (None, 0.0)}, cue={}, roam=())
    acts = {'rest': RG.rest_act(arm, 'room_rest')}
    FPS = people.FPS
    arms = {cc['who']: (cc, a) for cc, a, me in seated}
    if 'scene' in arms['lisa'][0]['acts']:
        n = int(round(TL['end'] * FPS)); F = lambda s: int(round(s * FPS))
        hands = {who: _hands_of(arms[who][1], arms[who][0]['acts']['scene']) for who in ('lisa', 'jeff')}
        L = RG.Track(arm, n); rnd = random.Random(5)
        for (a, b), (c0, c1) in ((TL['door_open'], (0.0, math.radians(80))), (TL['door_close'], (math.radians(80), 0.0)),
                                 (TL['door2_open'], (0.0, math.radians(80))), (TL['door2_close'], (math.radians(80), 0.0))):
            RG.swing(L, F(a), F(b), c0, c1)
        hl = {f: h[1] for f, h in hands['lisa'].items()}; hj = {f: h[1] for f, h in hands['jeff'].items()}
        hl_l = {f: h[0] for f, h in hands['lisa'].items()}
        for part in ('bottle', 'cork'):
            RG.carry(L, part, F(TL['bottle_grab']), F(TL['bottle_give']), hl, settle=0.0, home=None)
            RG.carry(L, part, F(TL['bottle_give']), F(TL['bottle_back'] if part == 'bottle' else TL['pop']), hj, settle=0.0)
        RG.pop(L, F(TL['pop']), Vector((2.4, -2.9, 0.012)), rnd)
        RG.carry(L, 'bottle', F(TL['bottle_back']), F(TL['bottle_home']), hl)
        RG.carry(L, 'glass_a', F(TL['glass_grab']), F(TL['glass_give']), hl, settle=0.0)
        RG.carry(L, 'glass_a', F(TL['glass_give']), F(TL['jeff_glass_put']), hj)
        RG.carry(L, 'glass_b', F(TL['glass_give'] + 0.9), F(TL['glass_put']), hl_l)
        acts['scene'] = L.key('room_scene')
    c['acts'] = acts
    return [(c, arm, mesh)]


def _hands_of(arm, act):
    out = {}; f0 = int(act.frame_range[0])
    for f in range(f0, int(act.frame_range[1]) + 1):
        people.pose_at(arm, act, f)
        out[f - f0] = tuple(people._world(arm, arm.pose.bones[f'Bip01 {s} Hand']).copy() for s in 'LR')
    return out


# ---------------------------------------------------------------- bake and export
def _switch(k):
    """A lamp pass: only lamp k's light (and its shade and bulb glowing); the dusk and the hall dark."""
    def sw(on):
        for l in RIG['lights']['dusk']: l.hide_render = on
        for j, group in enumerate(RIG['lights']['lamps']):
            for l in group: l.hide_render = not (on and j == k)
        shade = ('shade_pleat', 'shade_drum', 'shade_grey')[k]
        bpy.data.materials[shade].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 1.4 if on else 0.0
        for o in bpy.data.objects:
            if o.name.startswith(RIG['shades'][k][1]) and o.type == 'MESH':
                o.hide_render = not on
        bpy.data.materials['hall_bulb'].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 0.0 if on else 6.0
    return sw


def bake(sc, objs, phantoms, seated, args):
    os.makedirs(WEB, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    for c, arm, mesh in seated: mesh.hide_render = True
    passes = {'': (None, 1.0)}
    for k in range(3): passes[f'lamp{k + 1}'] = (_switch(k), 0.5)
    export, atlases = stages.bake(objs, R.RH, OUT, int(args.get('size', 2048)), int(args.get('samples', 320)), passes=passes)
    for c, arm, mesh in seated: mesh.hide_render = False
    for o in export:                                                       # the lamps' shades and bulbs: drawn and lit by the web
        for j, (shade, bulb) in enumerate(RIG['shades']):
            if o.name.startswith((shade, bulb)): o['role'] = 'lamp'; o['q'] = j + 1
    cine.export_glb(export, os.path.join(WEB, 'room.glb'))
    meta = stages.room_meta(R.RH, atlases); meta.update(_capture_meta())
    meta['people'] = _export_people(seated)
    meta['live'] = _live_meta()
    stages.write_meta(WEB, meta)


def _live_meta():
    lamps = [{'q': k + 1, 'who': 'lisa', 'act': 'scene', 'on': TL[f'lamp{k + 1}'], 'off': TL['end'] - 3.5,
              'at': [round(v, 3) for v in (b.x, b.z, -b.y)], 'color': list(R.LAMP)}
             for k, b in enumerate(l[0].location for l in RIG['lights']['lamps'])]
    return {'held': [{'who': 'lisa', 'act': 'scene', 'prop': 'stole', 'hand': 'R', 'grab': TL['stole'], 'release': TL['end'] - 0.5}], 'lamps': lamps}


def _export_people(seated):
    out = os.path.join(WEB, 'people'); os.makedirs(out, exist_ok=True); metas = []
    for c, arm, mesh in seated:
        pelvis = 'room_root' if c['who'] == 'room' else 'Bip01 Pelvis'
        people.export_person(arm, mesh, c['acts'], os.path.join(out, f"{c['who']}.glb"), roam=c.get('roam', ()), pelvis=pelvis)
        metas.append(person_meta(c))
    return metas


def _capture_meta():
    """How to light the people as the bake lit the room (three.js: y up, z = -Blender y): the dusk at the window, the
    hall's bulb; the lamps reach them live (live.lamps). Captured by the window and mid-room."""
    hb = next(l for l in RIG['lights']['dusk'] if l.name == 'hall_ceiling')
    r = 0.05; bulbs = [{'x': round(hb.location.x, 3), 'y': round(hb.location.z, 3), 'z': round(-hb.location.y, 3), 'r': r,
                        'L': round(hb.data.energy / (4 * math.pi * r ** 2) / 60, 2), 'color': list(R.HALL_LIGHT)}]
    wx = R.mx(Vector((sum(R.WINDOW_X) / 2, 0, 0))).x; ww = R.WINDOW_X[1] - R.WINDOW_X[0]
    wins = [{'x': round(wx, 3), 'y': 1.4, 'z': round(-(R.FRONT - 0.3), 3), 'w': ww, 'h': 2.2, 'L': 1.6, 'color': [0.95, 0.62, 0.48], 'ry': 0.0}]
    at = [[round(v, 3) for v in (p.x, p.z, -p.y)] for p in (Vector((2.6, -2.4, 1.1)), Vector((0.4, 0.4, 1.3)))]
    return {'capture': {'ceiling': [0.24, 0.23, 0.22], 'walls': [0.3, 0.29, 0.26], 'emitters': bulbs, 'windows': wins, 'at': at}}


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
