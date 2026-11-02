# The Big Lebowski: assemble Hollywood Star Lanes (the bar, the lanes, their heads), its people and the lanes' own
# rigs (the balls and the pins the bowlers knock down); then preview, bake and export.
import math, os, random
import bpy
from mathutils import Vector, Matrix
import cine, people, stages
from stages import camera
import rooms.the_big_lebowski as R
import rooms.the_big_lebowski_lanes as LN

ROOM = 'the-big-lebowski'
OUT = os.path.join(cine.OUT, ROOM)
WEB = os.path.join(cine.ROOT, 'public', 'rooms', ROOM)
PEOPLE_TEX = os.path.join(cine.OUT, 'people')
ARGS = {}
SEATED = []
MATS = {}
RIG = {'lights': []}
S = R.SCALE


def P(x, y, z=0.0):
    return Vector((x, y, z)) * S


def build(args):
    ARGS.clear(); ARGS.update(args)
    sc = cine.reset(int(args.get('samples', 256)))
    M = R.mats(); MATS.update(M)
    static, phantom, crowd = cine.coll('static'), cine.coll('phantom'), cine.coll('people')
    seated = [] if args.get('nocast') else cast(crowd, args)
    SEATED[:] = seated
    rnd = random.Random(1998)
    R.shell(M, static, phantom)
    R.lanes(M, static, rnd)
    R.masking(M, static)
    R.walls(M, static, rnd)
    R.settees(M, static, rnd)
    R.rail(M, static)
    bulbs = R.bar(M, static, rnd)
    R.bar_things(M, static, rnd)
    R.jukebox('jukebox', R.JUKE, M, static)
    RIG['lights'] = R.lights(bulbs)
    objs = [o for o in static.objects if o.type == 'MESH']; phantoms = [o for o in phantom.objects if o.type == 'MESH']
    bpy.context.view_layer.update()                     # a box's matrix_world is stale until the scene updates
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
    cams = {'case': camera('cam_case', (2.6, -20.5, 7.2), (0.0, 0.2, 0.6), 30),
            'close': camera('cam_close', (0.6, -7.0, 2.2), (-0.4, 0.4, 0.5), 38),
            'bar': camera('cam_bar', (0.0, -5.2, 0.95), (0.0, -2.6, 0.55), 40),                # the master over the bar
            'heads': camera('cam_heads', (-1.0, -1.8, 1.25), (-4.2, 0.6, 0.3), 46),            # the settees, the consoles, the ball returns
            'pins': camera('cam_pins', (-0.2, -1.2, 0.7), (3.4, 0.3, 0.4), 40),               # down the lanes to the masking
            'top': camera('cam_top', (0.0, 0.0, 14.0), (0.0, 0.1, 0.0), 38),
            'throw': camera('cam_throw', (-2.0, -3.6, 1.5), (-2.3, -1.2, 0.3), 44),          # the front pair's heads, the approach, from the bar side
            'deck': camera('cam_deck', (2.4, -3.3, 1.1), (3.45, -1.1, 0.2), 40)}             # the front lanes' pins
    return sc, M, objs, list(phantom.objects), seated, cams


KEEP = ('solid_', 'left_wall', 'back_wall', 'kerb', 'floor', 'subfloor')   # names that carry rules


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
    glass = [o for o in out if o.get('role') == 'glass']
    if len(glass) > 1:
        bpy.ops.object.select_all(action='DESELECT')
        for o in glass: o.select_set(True)
        bpy.context.view_layer.objects.active = glass[0]; bpy.ops.object.join()
        j = bpy.context.view_layer.objects.active; j.name = 'glassware'; j['role'] = 'glass'
        out = [o for o in out if o not in glass] + [j]
    cine.log(f'merged {len(objs)} meshes into {len(out)}')
    return out


def preview(sc, cams, which, samples, path, size=(1440, 900)):
    """A Cycles render from one camera; pose=who:act:frame poses one person first; seq=who:act:s1;s2;... renders the
    act at each of those seconds, with the lane rig whose act shares its name (a bowler's turn) posed alongside."""
    if ARGS.get('seq'):
        who, act, ts = str(ARGS['seq']).split(':')
        for t in ts.split(';'):
            for c, arm, mesh in SEATED:
                a = act if c['who'] == who else who if c['who'].startswith('lane') else None
                if a and a in c['acts']: people.pose_at(arm, c['acts'][a], int(c['acts'][a].frame_range[0]) + int(float(t) * people.FPS))
            stages.render(sc, cams[which], samples, path.replace('.png', f'_{act}_{float(t):04.1f}.png'), (960, 600), float(ARGS.get('exposure', 0.0)))
        return
    for spec in filter(None, str(ARGS.get('pose', '')).split(',')):
        who, act, f = spec.split(':')
        for c, arm, mesh in SEATED:
            if c['who'] == who and act in c['acts']: people.pose_at(arm, c['acts'][act], int(c['acts'][act].frame_range[0]) + int(f))
    stages.render(sc, cams[which], samples, path, size, float(ARGS.get('exposure', 0.0)))


# ---------------------------------------------------------------- the cast
# At the bar, facing the case: Donny, Walter, the Dude, the Stranger (on the Dude's left, as in the film); at the
# heads of the lanes: Liam at his console, Jesus standing by his lane, Smokey on the far settee. True heights; the
# room shrinks them with itself. Costumes after Mary Zophres (people_textures.the_big_lebowski); the Dude's head is
# a sculpt of Jeff Bridges, its hair and beard browned to 1998.
BRIDGES = os.path.join(cine.OUT, 'people', 'dude', 'bridges_head.glb')   # the sculpt made light (rooms/the_big_lebowski_head.py)


def _tex(who, prefix, *names):
    return {f'{prefix}_{n}.tga': f'{who}/{prefix}_{n}.png' for n in names}


CAST = [
    dict(who='dude', avatar='Male_Adult_06', shape=('heavy', 0.3), height=1.85,
         head=dict(glb=BRIDGES, keep=None, front='-y', eyes=((-0.040, -0.29, 0.621), (0.1325, -0.27, 0.622)), cut=0.02, fan_cut=-0.015),
         tex=_tex('dude', 'm011', 'body_color', 'body_normal')),
    dict(who='walter', avatar='Male_Adult_05', shape=('heavy', 1.0), height=1.88, tex=_tex('walter', 'm009', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
    dict(who='donny', avatar='Male_Adult_02', shape=('lean', 1.3), height=1.74, tex=_tex('donny', 'm003', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
    dict(who='stranger', avatar='Male_Adult_03', shape=('lean', 0.5), height=1.87, tex=_tex('stranger', 'm004', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
    dict(who='jesus', avatar='Male_Adult_07', shape=('lean', 1.2), height=1.80, tex=_tex('jesus', 'm013', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
    dict(who='liam', avatar='Male_Adult_13', shape=('heavy', 0.8), height=1.78, tex=_tex('liam', 'm010', 'head_color', 'body_color', 'body_normal')),
    dict(who='smokey', avatar='Business_Male_07', shape=('lean', 1.6), height=1.80,
         shell=dict(colour=(150, 146, 140), hem=-0.34, thick=0.006, gap=0.005, fall=0.014, front=34.0, temple=12.0, nape=-30.0, width=0.03, swept_cards=True),
         tex=_tex('smokey', 'm018', 'head_color', 'body_color', 'body_normal')),
]
BAR = ('donny', 'walter', 'dude', 'stranger')
SETTEE_SEAT = 0.44                                     # the settees' seat tops


def _settee_seat(a, deg):
    """A seat on pair a's settee at `deg` round its arc (0: the middle, facing +x): its centre and facing."""
    ctr = Vector((R.X_SETTEE + 1.25, R.PAIR_Y[a], 0)); d = Vector((-math.cos(math.radians(deg)), math.sin(math.radians(deg)), 0))
    return (ctr + d * 0.95).to_2d(), (-d).to_2d()


SEATS = {who: ((R.SEAT_OF[who], R.STOOL_Y), (0.0, -1.0)) for who in BAR}
SEATS['liam'] = (tuple(_settee_seat(20, 0)[0]), (1.0, 0.0))
SEATS['smokey'] = tuple(tuple(v) for v in _settee_seat(18, -20))
SPOTS = {'jesus': ((-6.85, 0.2), (0.45, -0.89))}
SEAT_Z = {who: R.STOOL_SEAT for who in BAR} | {'liam': SETTEE_SEAT, 'smokey': SETTEE_SEAT}
BASES = {who: 'm_sit_chair_breathe_01' for who in SEATS} | {'jesus': 'm_idle_breathe_01'}
WORK = {'dude': ('sit', 14, 30), 'walter': ('sit', 10, 22), 'donny': ('sit', 10, 22), 'stranger': ('sit', 14, 30), 'jesus': ('stand', 10, 22),
        'liam': ('sit', 12, 26), 'smokey': ('sit', 12, 26)}
IDLES = {'dude': {'sip': (None, 0.6), 'talk': ('m_gestic_talk_relaxed_01', 0.6), 'laugh': ('m_gestic_laugh_low', 0.3)},
         'stranger': {'talk': ('m_gestic_talk_cool', 0.6), 'hat': (None, 0.5), 'sip': (None, 0.4)},
         'walter': {'talk': ('m_gestic_talk_excited_01', 0.7), 'look': ('m_sit_chair_idle_look_around', 0.4)},
         'donny': {'nuts': (None, 0.6), 'look': ('m_sit_chair_idle_look_around', 0.4)},
         'jesus': {'dance': (None, 0.5), 'look': ('m_idle_look_around_01', 0.5)},
         'liam': {'point': (None, 0.5), 'look': ('m_sit_chair_idle_look_around', 0.4)},
         'smokey': {'look': ('m_sit_chair_idle_look_around', 0.5), 'shrug': ('m_sit_chair_gestic_shrug_01', 0.3)}}
CUE, FIRST, OPEN, ROAM = {}, {}, {}, {}
HANDS = {c['who'] for c in CAST}
SPINE = ('Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2')
ARMS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('Clavicle', 'UpperArm', 'Forearm', 'Hand'))
LEGS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('Thigh', 'Calf', 'Foot'))
FINGERS = tuple(f'Bip01 {s} Finger{f}{j}' for s in 'LR' for f in '01234' for j in ('', '1', '2'))
ALL = ('Bip01 Pelvis',) + SPINE + ARMS + LEGS + ('Bip01 Neck', 'Bip01 Head')


def _all(arm, fingers=False):
    return (next(b.name for b in arm.data.bones if b.parent is None),) + ALL + (FINGERS if fingers else ())


def _smooth(x):
    x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)


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


def _head_of(who):
    """Where someone's head is in their loop (for looks)."""
    c = next(c for c in CAST if c['who'] == who); k = c['height'] / 1.75
    if who in SEATS: (x, y), f = SEATS[who]; return P(x, y, SEAT_Z[who] + 0.72 * k) + Vector((*f, 0)) * 0.05 * S
    (x, y), f = SPOTS[who]; return P(x, y, 1.65 * k)


def make_person(c, col):
    """One of them, standing at the origin facing -y: the avatar, its build, its head (the Dude's sculpt), its height."""
    tex = {k: os.path.join(PEOPLE_TEX, v) for k, v in c.get('tex', {}).items() if os.path.exists(os.path.join(PEOPLE_TEX, v))}
    arm, mesh = people.load_avatar(c['avatar'], textures=tex, collection=col)
    arm.animation_data_clear()                                  # the FBX's take keys the object's scale (0.01): a render would undo the height
    mesh['person'] = c['who']; arm['person'] = c['who']
    if c.get('shape'): people.reshape(arm, mesh, *c['shape'])
    if c.get('head'):
        h = c['head']
        people.swap_head(arm, mesh, h['glb'], h['keep'], h['front'], h['eyes'], cut=h.get('cut', 0.0), fan_cut=h.get('fan_cut', -0.03), decimate=h.get('decimate'),
                         neck_skin=h.get('neck_skin', False))
        _bridges_hair(arm, mesh)
        _bridges_collar(arm, mesh)
    if c.get('shell') or c.get('head'): people.remove_hair_cards(mesh)
    bpy.context.view_layer.update()
    top = max((mesh.matrix_world @ v.co).z for v in mesh.data.vertices)
    J = people._joints(arm)
    if c.get('shell'):
        h = dict(c['shell']); h['hem'] = J['Bip01 Neck'].z + h['hem']
        people.hair_shell(arm, mesh, **h)
    {'walter': _aviators, 'stranger': _stranger_kit, 'jesus': _ponytail}.get(c['who'], lambda a, m: None)(arm, mesh)
    for ca in list(mesh.data.color_attributes): mesh.data.color_attributes.remove(ca)
    s = c['height'] / top
    arm.scale = arm.scale * s; arm.location = (arm.location.x, arm.location.y, arm.location.z * s)
    bpy.context.view_layer.update()
    return arm, mesh


def _bridges_hair(arm, mesh):
    """The sculpt is Bridges now, white-haired: his hair back to the Dude's light brown, the beard a darker brown with
    a little grey in it (the eyes, the brows' skin and the lips kept: only the pale, unsaturated texels change)."""
    import numpy as np
    J = people._joints(arm); eyes = [J['Bip01 LEye'], J['Bip01 REye']]; lip = J.get('Bip01 MUpperLip', J['Bip01 Head']).z
    fan = {i for i, sl in enumerate(mesh.material_slots) if sl.material and 'bridges_head' in sl.material.name}
    if not fan: cine.log('no sculpt material on', mesh.name); return
    k = next(iter(fan)); m = mesh.material_slots[k].material
    p = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    im = next(l.from_node.image for l in p.inputs['Base Color'].links if getattr(l.from_node, 'image', None))
    if im.size[0] > 2048: im.scale(2048, 2048)
    w, h = im.size; mask_hair = np.zeros((h, w), bool); mask_beard = np.zeros((h, w), bool)
    uv = mesh.data.uv_layers.active; W_ = mesh.matrix_world
    mid = (eyes[0] + eyes[1]) / 2; brow = J['Bip01 MMiddleEyebrow'].z
    for poly in mesh.data.polygons:
        if poly.material_index != k: continue
        q = W_ @ poly.center
        if min((q - e).length for e in eyes) < 0.022: continue                    # the eyes and their lids
        front = q.y < mid.y + 0.02 and abs(q.x - mid.x) < 0.058
        if front and lip + 0.012 < q.z < brow + 0.045: continue                   # the forehead, the cheeks, the nose: skin
        if q.z < lip - 0.075: continue                                            # the neck under the beard
        pts = [(uv.data[li].uv.x * w, uv.data[li].uv.y * h) for li in poly.loop_indices]
        people._uv_fill(mask_beard if (q.z < lip + 0.012 and q.y < mid.y + 0.07) else mask_hair, pts)
    px = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(px); px = px.reshape(h, w, 4); rgb = px[..., :3]
    mx = rgb.max(-1); mn = rgb.min(-1); sat = (mx - mn) / (mx + 1e-6)
    pale = (sat < 0.2) & (mx > 0.16)                                           # white hair (the face itself is left out above)
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    rng = np.random.default_rng(5)
    for mask, col, grey in ((mask_hair & pale, (0.36, 0.25, 0.15), 0.0), (mask_beard & pale, (0.24, 0.16, 0.1), 0.18)):
        if not mask.any(): continue
        rel = np.clip(lum[mask] / max(lum[mask].mean(), 1e-4), 0.45, 1.8)
        c = np.array(col, np.float32)[None, :] * rel[:, None]
        g = rng.random(len(rel)) < grey
        c[g] = (np.array([0.46, 0.4, 0.33], np.float32)[None, :] * rel[g, None])   # warm greys (the collar's cut takes the cold ones)
        rgb[mask] = c
    px[..., :3] = rgb; im.pixels.foreach_set(px.ravel()); im.pack()
    cine.log('the sculpt browned', int((mask_hair & pale).sum()), 'hair texels', int((mask_beard & pale).sum()), 'beard texels')


def _bridges_collar(arm, mesh):
    """The bust's shirt collar, left on the sculpt's neck below the jaw: the faces there whose colour is the shirt's
    grey denim (pale and unsaturated: the hair and beard are browned by now, the skin is warm) go; the cardigan's collar
    is round the neck instead."""
    import bmesh
    import numpy as np
    J = people._joints(arm); jaw = J.get('Bip01 MJaw', J['Bip01 Head']).z - 0.015
    k = next(i for i, sl in enumerate(mesh.material_slots) if sl.material and 'bridges_head' in sl.material.name)
    p = next(n for n in mesh.material_slots[k].material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    im = next(l.from_node.image for l in p.inputs['Base Color'].links if getattr(l.from_node, 'image', None))
    w, h = im.size; px = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(px); px = px.reshape(h, w, 4)[..., :3]
    bm = bmesh.new(); bm.from_mesh(mesh.data); W_ = mesh.matrix_world; uv = bm.loops.layers.uv.active
    dead = []
    for f in bm.faces:
        if f.material_index != k or (W_ @ f.calc_center_median()).z > jaw: continue
        u = sum((l[uv].uv for l in f.loops), Vector((0, 0))) / len(f.loops)
        c = px[int(min(max(u.y, 0), 0.999) * h), int(min(max(u.x, 0), 0.999) * w)]
        if (c.max() - c.min()) / (c.max() + 1e-6) < 0.16: dead.append(f)
    bmesh.ops.delete(bm, geom=dead, context='FACES'); bm.to_mesh(mesh.data); bm.free(); mesh.data.update()
    cine.log('collar cut from the sculpt', len(dead), 'faces')


def _aviators(arm, mesh):
    """Walter's aviators: gold wire frames, big teardrop lenses tinted amber."""
    import bmesh
    gold = cine.material('aviator_gold', (0.72, 0.56, 0.28), rough=0.25, metal=1.0)
    lens = cine.material('aviator_lens', (0.3, 0.17, 0.03), rough=0.04, coat=1.0)
    people.add_frames(arm, mesh, gold, w=0.056, h=0.046, r=0.0011, corner=0.017, tilt=6.0)
    J = people._joints(arm); L, Rr = J['Bip01 LEye'], J['Bip01 REye']; mid = (L + Rr) / 2
    fwd = J['Bip01 MNose'] - mid; fwd.z = 0; fwd.normalize(); side = (L - Rr).normalized(); up = Vector((0, 0, 1))
    bm = bmesh.new()
    for c, s in ((L + fwd * 0.0305 + side * 0.003, 1), (Rr + fwd * 0.0305 - side * 0.003, -1)):
        ring = []
        for i in range(20):
            a = 2 * math.pi * i / 20; x = math.cos(a) * 0.027; z = math.sin(a) * 0.022
            if z < 0: x *= 1 - 0.25 * (-z / 0.022) * (1 if x * s < 0 else 0.4)          # a teardrop: narrower low, toward the nose
            ring.append(bm.verts.new(c + side * x + up * (z - 0.002)))
        bm.faces.new(ring)
    _join(mesh, bm, 'lenses', [lens])
    cine.log('aviators on walter')


def _join(mesh, bm, name, mats):
    people._join_to_head(mesh, bm, name, mats)


def _stranger_kit(arm, mesh):
    """The Stranger's cream straw cowboy hat (a pinched crown with a braided dark band, the brim curling up at the
    sides and dipping front and back) and his big grey walrus moustache."""
    import bmesh
    straw = cine.material('straw_hat', (0.74, 0.68, 0.54), rough=0.75, sheen=0.3, sheen_tint=(0.6, 0.55, 0.45))
    band = cine.material('hat_band', (0.12, 0.09, 0.07), rough=0.6)
    img = people._hair_image('stranger_moustache', (214, 208, 198), 11, size=(256, 256), streak=0.35, jag=0.0)
    grey = cine.material('moustache_grey', (0.66, 0.64, 0.6), rough=0.95, specular=0.2)
    if not grey.node_tree.nodes.get('strands'):
        t = grey.node_tree.nodes.new('ShaderNodeTexImage'); t.name = 'strands'; t.image = img
        grey.node_tree.links.new(t.outputs['Color'], grey.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    c, em, J = people._head_frame(arm)
    top = max((mesh.matrix_world @ v.co).z for v in mesh.data.vertices if (mesh.matrix_world @ v.co).z > em.z)
    bm = bmesh.new(); seg = 40
    zb = em.z + 0.055                                                            # the brim's line, above the brows
    base = Vector((c.x, c.y - 0.005, zb))
    rings = []
    for (r, dz) in ((0.23, 0.0), (0.2, 0.0), (0.12, 0.0), (0.098, 0.004), (0.098, 0.03), (0.094, 0.08), (0.086, 0.11), (0.07, 0.125), (0.0, 0.112)):
        ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg; ca, sa = math.cos(a), math.sin(a)
            rx, ry = r * 1.0, r * (1.12 if r < 0.15 else 1.0)                    # the crown longer front to back
            z = dz
            if r > 0.15: z += 0.05 * ((r - 0.12) / 0.11) * ca * ca - 0.012 * sa * sa   # the brim curls up at the sides
            if 0.0 < r < 0.11 and dz > 0.09: z -= 0.03 * max(0, 1 - abs(ca) * 2.2)     # the crown's crease, along it
            if r == 0.0: z -= 0.015
            ring.append(bm.verts.new(base + Vector((ca * rx, sa * ry, z))))
        rings.append(ring)
    for A, B in zip(rings, rings[1:]):
        for i in range(seg): bm.faces.new((A[i], A[(i + 1) % seg], B[(i + 1) % seg], B[i]))
    under = [bm.verts.new(v.co - Vector((0, 0, 0.006))) for v in rings[0]]
    for i in range(seg): bm.faces.new((under[(i + 1) % seg], under[i], rings[0][i], rings[0][(i + 1) % seg]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces: f.smooth = True
    _join(mesh, bm, 'hat', [straw])
    bm = bmesh.new()                                                             # the band round the crown's foot
    ring_lo = [bm.verts.new(base + Vector((math.cos(2 * math.pi * i / seg) * 0.101, math.sin(2 * math.pi * i / seg) * 0.113, 0.006))) for i in range(seg)]
    ring_hi = [bm.verts.new(base + Vector((math.cos(2 * math.pi * i / seg) * 0.1, math.sin(2 * math.pi * i / seg) * 0.112, 0.026))) for i in range(seg)]
    for i in range(seg): bm.faces.new((ring_lo[i], ring_lo[(i + 1) % seg], ring_hi[(i + 1) % seg], ring_hi[i]))
    _join(mesh, bm, 'hat_band', [band])
    # the moustache: a thick, drooping bar from mouth corner to mouth corner, over the upper lip
    nose, lip = J['Bip01 MNose'], J['Bip01 MUpperLip']
    side = (J['Bip01 LEye'] - J['Bip01 REye']).normalized(); fwd = Vector((0, -1, 0)); up = Vector((0, 0, 1))
    c0 = lip + fwd * 0.012 + up * 0.006
    bm = bmesh.new(); prof = []
    for i in range(15):
        u = (i / 14) * 2 - 1                                                     # -1 .. 1 across
        r = 0.017 * (1 - 0.35 * abs(u) ** 2.5)                                    # a full walrus: thick to its ends
        p = c0 + side * u * 0.05 - up * (0.006 + 0.036 * abs(u) ** 1.6) - fwd * 0.016 * abs(u) ** 2
        prof.append((p, r))
    rings = []
    for p, r in prof:
        rings.append([bm.verts.new(p + up * math.sin(2 * math.pi * k / 10) * r + fwd * math.cos(2 * math.pi * k / 10) * r * 0.8) for k in range(10)])
    uvl = bm.loops.layers.uv.new('UVMap')
    for i, (A, B) in enumerate(zip(rings, rings[1:])):
        for k in range(10):
            f = bm.faces.new((A[k], A[(k + 1) % 10], B[(k + 1) % 10], B[k]))
            for l, (ii, kk) in zip(f.loops, ((i, k), (i, k + 1), (i + 1, k + 1), (i + 1, k))): l[uvl].uv = (ii / 14 * 3, kk / 10)   # strands round the bar: down
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces: f.smooth = True
    _join(mesh, bm, 'moustache', [grey])
    cine.log('hat and moustache on the stranger')


def _ponytail(arm, mesh):
    """Jesus's hair under its net, gathered into a long black pony tail down the back of his neck."""
    import bmesh
    black = cine.material('jesus_hair', (0.018, 0.016, 0.016), rough=0.35, coat=0.4)
    c, em, J = people._head_frame(arm); neck = J['Bip01 Neck']
    p0 = Vector((c.x, c.y + 0.085, em.z - 0.02)); pts = [p0 + Vector((0, 0.012 * math.sin(t * 1.4), -0.3 * t)) + Vector((0, 0.02 * t, 0)) for t in [i / 10 for i in range(11)]]
    bm = bmesh.new(); rings = []
    for i, p in enumerate(pts):
        r = 0.022 * (1 - 0.75 * (i / 10)) + 0.004
        rings.append([bm.verts.new(p + Vector((math.cos(2 * math.pi * k / 10) * r, math.sin(2 * math.pi * k / 10) * r * 0.8, 0))) for k in range(10)])
    for A, B in zip(rings, rings[1:]):
        for k in range(10): bm.faces.new((A[k], A[(k + 1) % 10], B[(k + 1) % 10], B[k]))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces: f.smooth = True
    me = bpy.data.meshes.new('ponytail'); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new('ponytail', me); [cl.objects.link(ob) for cl in mesh.users_collection]; me.materials.append(black)
    me.transform(mesh.matrix_world.inverted()); ob.matrix_world = mesh.matrix_world
    people._skin_by_height(ob, J); people._joined(mesh, ob)


def cast(col, args):
    """Load, dress, shape and place them, and bake their acts (cached: retargets and IK take minutes)."""
    full = bool(args.get('full'))
    spec = {'cast': CAST, 'seats': SEATS, 'spots': SPOTS, 'bases': BASES, 'work': WORK, 'idles': IDLES, 'cue': CUE, 'scale': S, 'seat_z': SEAT_Z,
            'bar': [R.BAR_TOP, R.BAR_Y, R.STOOL_Y, R.FOOT_RING], 'full': full, 'v': 7}
    spec['bowls'] = BOWLS
    for c in CAST:
        c['work'] = WORK[c['who']]; c['idles'] = IDLES[c['who']]; c['cue'] = CUE.get(c['who'], {}); c['roam'] = ROAM.get(c['who'], ())
    seated = stages.cast_cache(OUT, CAST, spec, lambda: _make_cast(col, full), col)
    seated += _lanes(seated, col)                                         # the lanes' rigs: quick, made fresh every time
    for c, arm, mesh in seated:
        people.pose_at(arm, c['acts'][c['work'][0]], int(c['acts'][c['work'][0]].frame_range[0]) + 30)
    return seated


def _place(c, arm):
    """Shrink a person with the room and set them at their seat or spot, facing their way; the base clip retargeted
    there (cycles 2: a perfect loop) and slid so its pelvis is over the place (a sitter's raised or lowered onto it)."""
    who = c['who']
    arm.scale = arm.scale * S; arm.location = arm.location * S
    bpy.context.view_layer.update()
    (x, y), f = SEATS[who] if who in SEATS else SPOTS[who]
    f = Vector((*f, 0)).normalized()
    people.face(arm, f); arm.location = (x * S, y * S, arm.location.z); bpy.context.view_layer.update()
    arm['fwd'] = list(f)
    base, frames, _ = people.retarget(arm, BASES[who], cycles=2, action_name=f'{who}_base')
    people.pose_at(arm, base, frames[0])
    pel = people._world(arm, arm.pose.bones['Bip01 Pelvis']).translation
    want = P(x, y) + (f * 0.03 * S if who in SEATS else Vector())
    arm.location.x += want.x - pel.x; arm.location.y += want.y - pel.y
    bpy.context.view_layer.update()
    drop = 0.0
    if who in SEATS:
        people.pose_at(arm, base, frames[0])
        pz = people._world(arm, arm.pose.bones['Bip01 Pelvis']).translation.z
        drop = pz - (SEAT_Z[who] * S + 0.09 * S * c['height'] / 1.75)
        cine.log(f'seat {who}: pelvis {pz / S:.3f} (true m), seat {SEAT_Z[who]:.3f}, drop {drop / S:+.3f}')
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
    acts = {k: {} for k in made}
    _bar_acts(made, acts, full)
    _liam_acts(made['liam'], acts['liam'], full)
    _smokey_acts(made['smokey'], acts['smokey'], full)
    _jesus_acts(made['jesus'], acts['jesus'], full)
    for m in made.values(): m['mesh'].hide_viewport = True
    if full: _bowling(made, acts)
    for who, m in made.items():
        m['c']['acts'] = acts[who]
        for name, a in acts[who].items():
            if who not in HANDS: people.freeze(a)
        if m['base'] not in acts[who].values(): bpy.data.actions.remove(m['base'])
        people.pose_at(m['arm'], acts[who][m['c']['work'][0]], int(m['frames'][0]) + 30)
        m['mesh'].hide_viewport = False
    return seated


def _clip_act(m, acts, name, clip, step, fingers=True, layered=False):
    """An idle from a clip: anchored on the base, authored over by `step` (a stool's height, looks). `layered`: the
    clip's arms and head over the seated base (a standing talk clip made a seated one)."""
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


# ---------------------------------------------------------------- at the bar
def _seated(arm, m, lean=0.08):
    """On a seat higher (a stool) or lower (a settee) than the clip's: the body raised or lowered onto it; on a stool
    the feet up on its foot ring."""
    people.shift_root(arm, (0, 0, -m['drop']))
    pel, fwd, right, up = _live(arm); k = m['k']
    for b_, a in zip(SPINE, (lean * 0.5, lean * 0.3, lean * 0.2)): people.bend(arm, b_, right, -a)
    who = m['c']['who']
    if who in BAR:
        (x, y), f = SEATS[who]; c = P(x, y)
        for side, sd in (('L', -1), ('R', 1)):
            tgt = c + fwd * 0.16 * S + right * sd * 0.085 * S + Vector((0, 0, R.FOOT_RING * S + 0.075 * k))
            people.ik_leg(arm, side, tgt, tgt + fwd * 0.5 * k + up * 0.25 * k + right * sd * 0.1 * k, keep_foot=True)


def _bar_hands(arm, m, w=1.0, spread=0.12, reach=0.42, which='LR', clasp=False):
    """Forearms on the bar top, the hands on it before them (clasped: together)."""
    if w <= 0: return
    pel, fwd, right, up = _live(arm); k = m['k']
    z = R.BAR_TOP * S + 0.03 * k
    for side, sd in (('L', -1), ('R', 1)):
        if side not in which: continue
        tgt = Vector((pel.x, pel.y, z)) + fwd * reach * k + right * sd * (0.03 if clasp else spread) * k
        H0 = people._world(arm, arm.pose.bones[f'Bip01 {side} Hand']).translation.copy(); g = H0.lerp(tgt, w)
        people.ik2(arm, side, g, g - up * 0.35 * k + right * sd * 0.4 * k - fwd * 0.1 * k)
        people.palm_to(arm, side, (-up * 0.4 - right * sd * 0.6).normalized() if clasp else -up, 0.8 * w)


def _glass_hand(arm, m, w=1.0, lift=0.0, side='R'):
    """A hand round a glass standing on the bar (`lift` 0..1 raises it to the mouth for a sip)."""
    pel, fwd, right, up = _live(arm); k = m['k']; sd = 1 if side == 'R' else -1
    rest = Vector((pel.x, pel.y, R.BAR_TOP * S + 0.05 * k)) + fwd * 0.4 * k + right * sd * 0.14 * k
    mouth = people._world(arm, arm.pose.bones['Bip01 Head']).translation + fwd * 0.1 * k - up * 0.07 * k + right * sd * 0.02 * k
    tgt = rest.lerp(mouth, _smooth(lift))
    H0 = people._world(arm, arm.pose.bones[f'Bip01 {side} Hand']).translation.copy(); g = H0.lerp(tgt, w)
    people.ik2(arm, side, g, g - up * 0.35 * k + right * sd * 0.45 * k)
    people.palm_to(arm, side, (-right * sd).normalized(), 0.9 * w)
    if lift > 0: people.bend(arm, 'Bip01 Head', right, -0.25 * _smooth(lift))


def _bar_acts(made, acts, full):
    """The four at the bar. The Dude: a forearm on the bar, his White Russian in his right hand, his head turned to the
    Stranger; a sip, talking with his hands, a low laugh. The Stranger: easy over his sarsaparilla, eyes on the Dude;
    talking, a touch at his hat brim, a sip. Walter: both forearms on the bar, talking at the Dude past him, now and
    then with both hands; Donny at the end, looking from one to the other, a hand to the basket of beer nuts."""
    dude, stranger = _head_of('dude'), _head_of('stranger')
    for who, m in ((w, made[w]) for w in BAR):
        arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; T = (frames[1] - frames[0]) / people.FPS
        if who == 'dude':
            def sit(f, t, arm=arm, m=m):
                _seated(arm, m, 0.12); _bar_hands(arm, m, which='L', reach=0.38); _glass_hand(arm, m); _look(arm, stranger, 0.55)
        elif who == 'stranger':
            def sit(f, t, arm=arm, m=m):
                _seated(arm, m, 0.06); _bar_hands(arm, m, which='L', reach=0.36); _glass_hand(arm, m); _look(arm, dude, 0.6)
        elif who == 'walter':
            def sit(f, t, arm=arm, m=m, T=T):
                _seated(arm, m, 0.14); _bar_hands(arm, m, clasp=True, reach=0.36); _look(arm, dude + Vector((0.03 * math.sin(2 * math.pi * t / T), 0, 0)), 0.6)
        else:
            def sit(f, t, arm=arm, m=m, T=T):
                _seated(arm, m, 0.1); _bar_hands(arm, m, reach=0.36, spread=0.1)
                _look(arm, _head_of('walter').lerp(dude, 0.5 + 0.5 * math.sin(2 * math.pi * t / T)), 0.6)
        acts[who]['sit'] = people.custom_act(arm, base, frames, f'{who}_sit', sit, _all(arm, fingers=True)); m['sit'] = sit
        people.pose_at(arm, acts[who]['sit'], frames[0])
        if who in ('dude', 'stranger'): _bind_glass(m, 'milk' if who == 'dude' else 'sarsaparilla')
        if not full: continue
        for name, (clip, w) in IDLES[who].items():
            if clip:
                lay = clip.startswith('m_gestic')
                look = stranger if who == 'dude' else dude
                _clip_act(m, acts[who], name, clip, lambda f, t, arm=arm, m=m, look=look: (_seated(arm, m, 0.08), _look(arm, look, 0.35)), layered=lay)
        if who in ('dude', 'stranger'):
            def sip(f, t, arm=arm, m=m, T=T, who=who):
                e = people.envelope(t - 1.0, 3.2, 1.0, 1.0) if 1.0 < t < 4.2 else 0.0
                _seated(arm, m, 0.1); _bar_hands(arm, m, which='L', reach=0.38); _glass_hand(arm, m, lift=e)
                _look(arm, stranger if who == 'dude' else dude, 0.55 * (1 - e))
            acts[who]['sip'] = people.custom_act(arm, base, frames, f'{who}_sip', sip, _all(arm, fingers=True))
        if who == 'stranger':
            def hat(f, t, arm=arm, m=m):
                e = people.envelope(t - 1.0, 3.0, 0.8, 0.9) if 1.0 < t < 4.0 else 0.0
                _seated(arm, m, 0.06); _bar_hands(arm, m, which='L', reach=0.36); _glass_hand(arm, m, w=1 - e)
                pel, fwd, right, up = _live(arm); kk = m['k']
                H = people._world(arm, arm.pose.bones['Bip01 Head']).translation
                brim = H + fwd * 0.17 * kk + up * 0.11 * kk + right * 0.05 * kk
                if e > 0:
                    H0 = people._world(arm, arm.pose.bones['Bip01 R Hand']).translation.copy(); g = H0.lerp(brim, e)
                    people.ik2(arm, 'R', g, g - up * 0.3 * kk + right * 0.4 * kk); people.palm_to(arm, 'R', (-up + fwd).normalized(), e)
                _look(arm, dude, 0.6)
            acts[who]['hat'] = people.custom_act(arm, base, frames, f'{who}_hat', hat, _all(arm, fingers=True))
        if who == 'donny':
            def nuts(f, t, arm=arm, m=m):
                _seated(arm, m, 0.1); _bar_hands(arm, m, which='L', reach=0.36)
                pel, fwd, right, up = _live(arm); kk = m['k']
                basket = P(R.SEAT_OF['donny'] + 0.12, R.BAR_Y[1] - 0.18, R.BAR_TOP + 0.05)
                mouth = people._world(arm, arm.pose.bones['Bip01 Head']).translation + fwd * 0.09 * kk - up * 0.07 * kk
                cyc = [(1.0, 1.6, basket), (2.6, 1.0, mouth), (4.2, 1.4, basket), (5.6, 1.0, mouth)]
                rest = Vector((pel.x, pel.y, R.BAR_TOP * S + 0.03 * kk)) + fwd * 0.36 * kk + right * 0.12 * kk
                g = rest
                for t0, d, p in cyc:
                    if t >= t0: g = g.lerp(p, _smooth((t - t0) / 0.6))
                g = g.lerp(rest, _smooth((t - 7.0) / 1.0))
                people.ik2(arm, 'R', g, g - up * 0.35 * kk + right * 0.4 * kk); people.palm_to(arm, 'R', -up, 0.6)
                _look(arm, basket, 0.4 * people.envelope(t - 0.8, 2.0, 0.5, 0.5) if 0.8 < t < 2.8 else 0.0)
            acts[who]['nuts'] = people.custom_act(arm, base, frames, 'donny_nuts', nuts, _all(arm, fingers=True))


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
    people._joined(mesh, ob)
    mesh.hide_viewport = hidden


def _bind_glass(m, drink):
    """A tumbler in the right hand as it rests on the bar (the Dude's White Russian, the Stranger's sarsaparilla):
    standing on the bar under the palm's side, carried by the hand from then on."""
    import bmesh
    arm, mesh, k = m['arm'], m['mesh'], m['k']
    pel, fwd, right, up = _live(arm)
    H = people._world(arm, arm.pose.bones['Bip01 R Hand']).translation
    palm = people._palm(arm, 'R')
    at = H + palm * 0.04 * k; at.z = R.BAR_TOP * S + 0.002
    shell = cine.material('tumbler', (0.6, 0.62, 0.6), rough=0.05, coat=1.0)
    fill = cine.material({'milk': 'white_russian_drink', 'sarsaparilla': 'sarsaparilla_drink'}[drink],
                         (0.78, 0.68, 0.52) if drink == 'milk' else (0.1, 0.045, 0.02), rough=0.15, coat=0.8)
    bm = bmesh.new(); seg = 14
    T_ = Matrix.Translation(at) @ Matrix.Scale(S, 4)                             # true size, shrunk with the room
    prof = [(0.0, 0.0), (0.034, 0.0), (0.038, 0.095), (0.035, 0.095), (0.031, 0.012), (0.0, 0.012)]
    rings = [[bm.verts.new(T_ @ Vector((rr * math.cos(2 * math.pi * i / seg), rr * math.sin(2 * math.pi * i / seg), z))) for i in range(seg)] for rr, z in prof]
    for a, b in zip(rings, rings[1:]):
        for i in range(seg): f = bm.faces.new((a[i], a[(i + 1) % seg], b[(i + 1) % seg], b[i])); f.material_index = 0
    liq = [[bm.verts.new(T_ @ Vector((rr * math.cos(2 * math.pi * i / seg), rr * math.sin(2 * math.pi * i / seg), z))) for i in range(seg)] for rr, z in ((0.032, 0.013), (0.034, 0.065))]
    for i in range(seg): f = bm.faces.new((liq[0][i], liq[0][(i + 1) % seg], liq[1][(i + 1) % seg], liq[1][i])); f.material_index = 1
    f = bm.faces.new(liq[1]); f.material_index = 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    _bind(arm, mesh, bm, 'Bip01 R Hand', [shell, fill], 'glass')
    cine.log('glass in', m['c']['who'], 'hand')


# ---------------------------------------------------------------- at the lanes' heads
def _liam_acts(m, acts, full):
    """Liam on the settee at his console, leaning over the score sheet, a pencil going (his right hand), watching
    Jesus's lane; idle: up on his elbow, pointing down the lane and shouting; a look round."""
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; T = (frames[1] - frames[0]) / people.FPS
    desk = P(R.X_CONSOLE + 0.02, R.PAIR_Y[20], 0.79)
    pins = P(R.X_HEAD, R.LANES[20], 0.2)
    def sit(f, t):
        _seated(arm, m, 0.32); pel, fwd, right, up = _live(arm)
        for side, sd, dx in (('L', -1, 0.0), ('R', 1, 0.02 * math.sin(2 * math.pi * t / 0.9) * people.envelope(t % 6.0, 6.0, 1.0, 1.0))):
            tgt = desk + right * sd * 0.12 * k + fwd * (-0.06 + dx) * k
            H0 = people._world(arm, arm.pose.bones[f'Bip01 {side} Hand']).translation.copy()
            people.ik2(arm, side, tgt, tgt - up * 0.3 * k + right * sd * 0.4 * k - fwd * 0.2 * k); people.palm_to(arm, side, -up, 0.8)
        _look(arm, desk.lerp(pins, 0.5 + 0.5 * math.sin(2 * math.pi * t / T)), 0.6)
    acts['sit'] = people.custom_act(arm, base, frames, 'liam_sit', sit, _all(arm, fingers=True)); m['sit'] = sit
    if not full: return
    def point(f, t):
        e = people.envelope(t - 1.0, 4.0, 0.8, 1.0) if 1.0 < t < 5.0 else 0.0
        sit(f, t)
        if e > 0: people.point_at(arm, 'R', pins + Vector((0, 0, 0.3 * S)), w=e, jab=0.4); _look(arm, pins, 0.7 * e)
    acts['point'] = people.custom_act(arm, base, frames, 'liam_point', point, _all(arm, fingers=True))
    _clip_act(m, acts, 'look', IDLES['liam']['look'][0], lambda f, t: _seated(arm, m, 0.2))


def _smokey_acts(m, acts, full):
    """Smokey on the far settee, sitting back, his hands on his thighs, watching the lanes; idles from his seat."""
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']
    lanes = P(2.0, R.LANES[18], 0.4)
    def sit(f, t):
        _seated(arm, m, -0.04); _look(arm, lanes, 0.5)
    acts['sit'] = people.custom_act(arm, base, frames, 'smokey_sit', sit, _all(arm, fingers=True)); m['sit'] = sit
    if not full: return
    for name, (clip, w) in IDLES['smokey'].items():
        if clip: _clip_act(m, acts, name, clip, lambda f, t: _seated(arm, m, 0.0))


def _jesus_acts(m, acts, full):
    """Jesus by his lane, standing hip-shot, his weight on one leg, a hand on his hip, eyeing the room; idles: a look
    round; the hips going (his little dance)."""
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']
    bar = P(0.0, R.STOOL_Y, 1.3)
    def stand(f, t):
        pel, fwd, right, up = _live(arm)
        for b_, a in zip(SPINE, (0.05, 0.03, 0.02)): people.bend(arm, b_, fwd, a)
        hip = pel + right * 0.17 * k + up * 0.05 * k - fwd * 0.02 * k
        people.ik2(arm, 'R', hip, hip + right * 0.3 * k - fwd * 0.2 * k + up * 0.1 * k); people.palm_to(arm, 'R', -right, 0.7)
        _look(arm, bar, 0.4)
    acts['stand'] = people.custom_act(arm, base, frames, 'jesus_stand', stand, _all(arm, fingers=True)); m['sit'] = stand
    if not full: return
    _clip_act(m, acts, 'look', IDLES['jesus']['look'][0], lambda f, t: None)
    dance, dfr, _ = people.retarget(arm, 'm_dancing_sexy', action_name='jesus_src_dance')
    dance = people.anchor(arm, dance, base)
    seg = [dict(src=base, f0=frames[0], dur=0.8, at=Matrix.Identity(4)),
           dict(src=dance, f0=dfr[0] + 30, dur=4.4, at=Matrix.Identity(4), blend=0.8),
           dict(src=base, f0=frames[0] + 20, dur=1.6, at=Matrix.Identity(4), blend=0.9)]
    acts['dance'] = people.sequence(arm, base, 'jesus_dance', seg)
    bpy.data.actions.remove(dance)


# ---------------------------------------------------------------- the bowling
# Each bowled lane is a performer of its own (rooms/the_big_lebowski_lanes.py): it rests, and now and then it is a
# bowler's turn, which cues his act; both start together, so the ball follows his hand until he lets it go. Walter
# and Donny take turns on lane 22 (the pair nearest the bar), Jesus has lane 20, Smokey lane 18.
LANE_CAST = [
    dict(who='lane22', lane=22, balls=[('ball_black', 0), ('ball_blue', 1)], work=('rest', 14, 34),
         idles={'walter': (None, 1.0), 'donny': (None, 0.8)}, cue={'walter': {'walter': 'bowl'}, 'donny': {'donny': 'bowl'}}, roam=()),
    dict(who='lane20', lane=20, balls=[('ball_magenta', 0)], work=('rest', 22, 44), idles={'jesus': (None, 1.0)}, cue={'jesus': {'jesus': 'bowl'}}, roam=()),
    dict(who='lane18', lane=18, balls=[('ball_green', 0)], work=('rest', 30, 60), idles={'smokey': (None, 1.0)}, cue={'smokey': {'smokey': 'bowl'}}, roam=()),
]
BOWLS = {'walter': dict(lane=22, ball=0, rig='lane22', react='m_cheer_01'),
         'donny': dict(lane=22, ball=1, rig='lane22', react='m_claphands_01'),
         'jesus': dict(lane=20, ball=0, rig='lane20', react='dance'),
         'smokey': dict(lane=18, ball=0, rig='lane18', react='m_claphands_01')}
FIRST.update({'lane22': 'walter', 'lane20': 'jesus'})
ROAM.update({who: ('bowl',) for who in BOWLS})
for _w in BOWLS: IDLES[_w]['bowl'] = (None, 0.0)


def _lane_rigs(col):
    """The three lane rigs, each with its resting act."""
    out = {}
    for c in LANE_CAST:
        arm, mesh = LN.make_rig(c['who'], c['lane'], c['balls'], MATS, col)
        out[c['who']] = (arm, mesh, {'rest': LN.rest_act(arm, c['lane'], f"{c['who']}_rest")})
    return out


def _arc(keys, t):
    """A smooth curve through (time, value) keys (cosine eased between them), held at its ends."""
    if t <= keys[0][0]: return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1: u = (t - t0) / (t1 - t0); u = 0.5 - 0.5 * math.cos(math.pi * u); return v0 + (v1 - v0) * u
    return keys[-1][1]


def _bowl(m, cfg):
    """One bowler's turn, a single act (it starts and ends in his place): up from his stool (or the settee, or his
    spot), round to his pair's rack, the ball up off the rails in both hands, out to the head of the approach, the
    stance, four steps with the push-away and the pendulum swing, the slide and the release low by the foul line, the
    follow-through; he watches it hit, his reaction (a fist up, a clap, Jesus's hips), round and back to his place.
    Returns the act, the ball's centre (true metres) by frame while he holds it, the release frame and the segments'
    start times."""
    arm, base, frames, k, who = m['arm'], m['base'], m['frames'], m['k'], m['c']['who']
    FPS = people.FPS; lane = cfg['lane']; pair = next(a for a, b in R.PAIRS if lane in (a, b))
    yL, yP = R.LANES[lane], R.PAIR_Y[pair]
    walk, wf, vs = people.retarget(arm, 'm_walk_neutral_01', inplace=True, cycles=16, action_name=f'{who}_src_walk')
    idle, idf, _ = people.retarget(arm, 'm_idle_breathe_01', cycles=8, action_name=f'{who}_src_idle')
    turn, tf, _ = people.retarget(arm, 'm_turn_left_180', action_name=f'{who}_src_turn')
    seated_home = who in SEATS
    react = cfg['react']
    rc, rcf, _ = people.retarget(arm, 'm_dancing_sexy' if react == 'dance' else react, action_name=f'{who}_src_react')
    cine.log(f'{who} walks at {vs / S:.2f} m/s (true)')

    def at(src, f, p, h):
        hh, pp = people.heading(arm, src, f); return people.carry(pp, hh, p, Vector((*h, 0)).normalized())
    # the places (true metres)
    slot = next(c for c in LANE_CAST if c['who'] == cfg['rig'])['balls'][cfg['ball']][1]
    ball0 = R.RACK_SPOTS[pair][slot]
    G = (ball0.x + 0.02, yP - 0.5)                                        # beside the rack, facing it
    yB = yL + 0.06                                                        # his line down the approach
    F = (R.X_FOUL - 0.32, yB)                                             # his slide foot at the foul line
    D = 3.0; A = (F[0] - D - 0.55, yB)                                    # the stance, four steps back
    if seated_home:
        (hx, hy), hf = SEATS[who]
        if who in BAR: OFF, out_pts, off_h = (hx + 0.05, hy + 0.55), [(hx - 0.8, -4.6), (-6.2, -4.5), (-7.45, -4.15), (-7.75, -3.35), (-7.45, -2.75)], (-1.0, 0.0)
        else: OFF, out_pts, off_h = (hx + 0.45 * hf[0], hy + 0.45 * hf[1]), [(-7.15, yP - 0.75)], (0.6, -0.8)
    else:
        (hx, hy), hf = SPOTS[who]; OFF, out_pts, off_h = (hx, hy), [(hx - 0.1, yP - 0.85)], hf
    r_out = people.path([P(*OFF)] + [P(*q) for q in out_pts] + [P(*G)])
    r_set = people.path([P(*G), P(G[0] + 0.45, (G[1] + yB) / 2 - 0.1), P(*A)])
    r_app = people.path([P(*A), P(F[0] - 0.55, yB)])
    r_back = people.path([P(F[0] - 0.4, yB), P(A[0] + 0.6, yB - 0.2), P(-6.6, yP - 0.7)] + [P(*q) for q in reversed(out_pts)] + [P(*OFF)])
    T_turn = (tf[1] - tf[0]) / FPS
    lick = who == 'jesus'
    segs = []

    def add(tag, **kw): kw['tag'] = tag; segs.append(kw)
    if seated_home:
        add('seated', src=base, f0=frames[0], dur=1.0, at=Matrix.Identity(4))
        add('rise', src=idle, f0=idf[0], dur=1.0, at=at(idle, idf[0], P(*OFF), off_h), blend=1.3)
    else:
        add('home', src=base, f0=frames[0], dur=0.8, at=Matrix.Identity(4))
    add('walk_out', src=walk, f0=wf[0], dur=r_out[1] / vs, at=people.walk_along(arm, walk, wf[0], vs, r_out), blend=0.7)
    add('grab', src=idle, f0=idf[0] + 20, dur=3.6 if lick else 2.6, at=at(idle, idf[0] + 20, P(*G), (0, 1)), blend=0.7)
    add('walk_set', src=walk, f0=wf[0] + 10, dur=max(r_set[1] / vs, 0.9), at=people.walk_along(arm, walk, wf[0], vs, r_set), blend=0.6)
    add('stance', src=idle, f0=idf[0] + 40, dur=1.7, at=at(idle, idf[0] + 40, P(*A), (1, 0)), blend=0.7)
    add('approach', src=walk, f0=wf[0], dur=r_app[1] / (vs * 1.15), rate=1.15, at=people.walk_along(arm, walk, wf[0], vs * 1.15, r_app), blend=0.35)
    add('slide', src=idle, f0=idf[0] + 60, dur=1.9, at=at(idle, idf[0] + 60, P(*F), (1, 0)), blend=0.3)
    add('watch', src=idle, f0=idf[0] + 80, dur=1.6, at=at(idle, idf[0] + 80, P(*F), (1, 0)), blend=0.7)
    if react == 'dance':
        add('react', src=rc, f0=rcf[0] + 30, dur=4.2, at=at(rc, rcf[0] + 30, P(*F), (0.3, -1)), blend=0.8)
    else:
        add('react', src=rc, f0=rcf[0], dur=min(2.6, (rcf[1] - rcf[0]) / FPS), at=at(rc, rcf[0], P(*F), (1, 0)), blend=0.6)
    add('turn', src=turn, f0=tf[0], dur=T_turn, at=at(turn, tf[0], P(*F), (1, 0)), blend=0.6)
    add('walk_back', src=walk, f0=wf[0] + 15, dur=r_back[1] / vs, at=people.walk_along(arm, walk, wf[0], vs, r_back), blend=0.7)
    if seated_home:
        add('arrive', src=idle, f0=idf[0] + 30, dur=0.5, at=at(idle, idf[0] + 30, P(*OFF), (-off_h[0], -off_h[1]) if who in BAR else off_h), blend=0.6)
        add('sit', src=base, f0=frames[0] + 40, dur=2.2, at=Matrix.Identity(4), blend=1.4)
    else:
        add('home', src=base, f0=frames[0] + 40, dur=1.8, at=Matrix.Identity(4), blend=1.2)
    t0 = {}; t = 0.0
    for sg in segs: t0.setdefault(sg['tag'], t); sg['t0'] = t; t += sg['dur']
    T_end = t
    D6 = next(sg['dur'] for sg in segs if sg['tag'] == 'approach')
    T_rel = t0['approach'] + D6 + 0.45
    theta = [(0.28 * D6, 0.95), (0.55 * D6, 0.0), (0.85 * D6, -1.25), (D6 + 0.45, 0.12), (D6 + 0.9, 2.25), (D6 + 1.9, 2.0)]
    ballpath = {}
    B0 = ball0 * S; Lp = 0.68 * k
    g_t, l_t = 0.9, 1.5                                                  # in the grab: the hands on the ball, then up with it

    def chest(arm_):
        pel, fwd, right, up = _live(arm_); return pel + fwd * 0.3 * k + up * 0.42 * k

    def hands_on(arm_, c, w=1.0):
        pel, fwd, right, up = _live(arm_)
        for side, sd in (('L', -1), ('R', 1)):
            tgt = c + right * sd * (R.BALL_R * S + 0.02 * k) - up * 0.02 * k
            H0 = people._world(arm_, arm_.pose.bones[f'Bip01 {side} Hand']).translation.copy(); g = H0.lerp(tgt, w)
            people.ik2(arm_, side, g, g - up * 0.3 * k + right * sd * 0.4 * k - fwd * 0.1 * k)
            people.palm_to(arm_, side, -right * sd, 0.8 * w)

    def overlay(tt, i, lt):
        sg = segs[i]; tag = sg['tag']; f = int(round(tt * FPS))
        pel, fwd, right, up = _live(arm)
        if tag in ('seated', 'sit'):
            w = 1.0 if tag == 'seated' else _smooth(lt / 1.4)
            _seated_w(arm, m, w)
            if who in BAR: _bar_hands(arm, m, w=w, reach=0.36)
            return
        if tag == 'rise': _seated_w(arm, m, 1 - _smooth(lt / 1.2)); return
        if tag == 'grab':
            if lt < g_t:                                                 # down to the ball on the rails
                e = _smooth((lt - 0.2) / (g_t - 0.2))
                for b_, a in zip(SPINE, (0.25, 0.2, 0.1)): people.bend(arm, b_, right, -a * e)
                hands_on(arm, B0, e)
            else:
                c = B0.lerp(chest(arm), _smooth((lt - g_t) / (l_t - g_t)))
                if lick and lt > 1.7:                                     # Jesus: the ball up to his face, a lick
                    H = people._world(arm, arm.pose.bones['Bip01 Head']).translation
                    c = c.lerp(H + fwd * 0.13 * k - up * 0.04 * k, people.envelope(lt - 1.7, 1.8, 0.5, 0.6))
                e = 1 - _smooth((lt - g_t) / (l_t - g_t))
                for b_, a in zip(SPINE, (0.25, 0.2, 0.1)): people.bend(arm, b_, right, -a * e)
                hands_on(arm, c); ballpath[f] = c
            return
        if tag in ('walk_set', 'stance'):
            c = chest(arm); hands_on(arm, c); ballpath[f] = c
            if tag == 'stance': _look(arm, P(R.X_HEAD, yL, 0.2), 0.5 * _smooth(lt / 0.8))
            return
        if tag in ('approach', 'slide', 'watch'):
            tau = tt - t0['approach']
            e_sl = _smooth(lt / 0.45) * (1 - _smooth((lt - 1.2) / 0.7)) if tag == 'slide' else 0.0
            if e_sl > 0:                                                  # the slide: low over the bent left knee, the right leg back
                people.shift_root(arm, -up * 0.42 * k * e_sl + fwd * 0.1 * k * e_sl)
                pel, fwd, right, up = _live(arm)
                Fp = P(*F)
                al = Fp + fwd * 0.22 * k - right * 0.09 * k + up * 0.08 * k
                A0 = people._world(arm, arm.pose.bones['Bip01 L Foot']).translation.copy()
                people.ik_leg(arm, 'L', A0.lerp(al, e_sl), al + fwd * 0.6 * k + up * 0.3 * k, keep_foot=True)
                ar = Fp - fwd * 0.6 * k - right * 0.18 * k + up * 0.09 * k
                A1 = people._world(arm, arm.pose.bones['Bip01 R Foot']).translation.copy()
                people.ik_leg(arm, 'R', A1.lerp(ar, e_sl), ar - fwd * 0.1 * k - up * 0.3 * k + right * 0.2 * k, keep_foot=True)
                for b_, a in zip(SPINE, (0.35, 0.25, 0.15)): people.bend(arm, b_, right, -a * e_sl)
                people.bend(arm, 'Bip01 Head', right, 0.35 * e_sl)
            th = _arc(theta, tau)
            SR = people._world(arm, arm.pose.bones['Bip01 R UpperArm']).translation
            rh = fwd * math.sin(th) - up * math.cos(th)
            on_arc = SR + rh * Lp + right * 0.04 * k
            c = chest(arm).lerp(on_arc, _smooth(tau / (0.28 * D6))) if tau < 0.28 * D6 else on_arc
            fade = 1.0 if tag != 'watch' else 1 - _smooth(lt / 1.0)
            hand = c - rh * 0.1 * k
            H0 = people._world(arm, arm.pose.bones['Bip01 R Hand']).translation.copy(); g = H0.lerp(hand, fade)
            people.ik2(arm, 'R', g, g + right * 0.35 * k - fwd * 0.15 * k)
            people.palm_to(arm, 'R', rh, 0.8 * fade)
            # the left hand: on the ball for the push-away, then out to the side for balance
            SL = people._world(arm, arm.pose.bones['Bip01 L UpperArm']).translation
            bal = SL - right * 0.5 * k - up * 0.12 * k + fwd * 0.1 * k
            wl = 1 - _smooth((tau - 0.15 * D6) / (0.2 * D6))
            tgt = (c - right * (R.BALL_R * S + 0.02 * k)).lerp(bal, 1 - wl)
            HL = people._world(arm, arm.pose.bones['Bip01 L Hand']).translation.copy(); gl = HL.lerp(tgt, fade)
            people.ik2(arm, 'L', gl, gl - up * 0.3 * k - right * 0.3 * k)
            _look(arm, P(R.X_HEAD, yL, 0.2), 0.6 * fade)
            if tau <= D6 + 0.45 + 1e-6: ballpath[f] = c
            return
        if tag == 'react' and react != 'dance':
            _look(arm, P(R.X_HEAD, yL, 0.2), 0.4)
    act = people.sequence(arm, base, f'{who}_bowl', segs, overlay=overlay)
    for a in (walk, idle, turn, rc): bpy.data.actions.remove(a)
    f_rel = int(round(T_rel * FPS))
    path_true = {f: p / S for f, p in ballpath.items() if f <= f_rel}
    f_rel = max(path_true)                                                # the last frame his hand has it
    cine.log(f'{who} bowl: {T_end:.1f} s, grab {min(path_true) / FPS:.1f} s, release {f_rel / FPS:.1f} s; ' + ', '.join(f"{sg['tag']} {sg['t0']:.1f}" for sg in segs))
    return act, path_true, f_rel, t0


def _seated_w(arm, m, w):
    """_seated by a fraction: raised (or lowered) onto the seat by w, the feet drawn onto a stool's ring with it."""
    if w <= 0: return
    people.shift_root(arm, (0, 0, -m['drop'] * w))
    who = m['c']['who']
    if who in BAR:
        pel, fwd, right, up = _live(arm); k = m['k']; (x, y), f = SEATS[who]; c = P(x, y)
        for side, sd in (('L', -1), ('R', 1)):
            tgt = c + fwd * 0.16 * S + right * sd * 0.085 * S + Vector((0, 0, R.FOOT_RING * S + 0.075 * k))
            A0 = people._world(arm, arm.pose.bones[f'Bip01 {side} Foot']).translation.copy(); g = A0.lerp(tgt, w)
            people.ik_leg(arm, side, g, g + fwd * 0.5 * k + up * 0.25 * k + right * sd * 0.1 * k, keep_foot=True)


def _bowling(made, acts):
    """Every bowler's turn; the ball's way in his hands kept on his armature for his lane's act (made with the rigs)."""
    import json
    for who, cfg in BOWLS.items():
        m = made[who]
        act, path_true, f_rel, t0 = _bowl(m, cfg)
        acts[who]['bowl'] = act
        m['arm']['bowl_ball'] = json.dumps({'path': {str(f): list(p) for f, p in path_true.items()}, 'release': f_rel,
                                            'n': int(act.frame_range[1] - act.frame_range[0]), 'grab_t': t0['grab']})


def _lanes(seated, col):
    """The lane rigs and their acts: resting, and one per bowler's turn, made from the ball's way in his hands (the
    same length as his act: they start together)."""
    import json
    rigs = _lane_rigs(col); out = []
    arms = {c['who']: arm for c, arm, mesh in seated}
    for who, cfg in BOWLS.items():
        if who not in arms or 'bowl_ball' not in arms[who]: continue
        d = json.loads(arms[who]['bowl_ball']); path_true = {int(f): Vector(p) for f, p in d['path'].items()}
        arm_l, mesh_l, lacts = rigs[cfg['rig']]
        c = next(c for c in LANE_CAST if c['who'] == cfg['rig'])
        balls = [f"{cfg['rig']}_ball{j}" for j in range(len(c['balls']))]
        lacts[who], f_hit = LN.bowl_act(arm_l, cfg['lane'], f"{cfg['rig']}_{who}", d['n'], balls[cfg['ball']], path_true, d['release'],
                                        seed=sum(map(ord, who)), others=[b for j, b in enumerate(balls) if j != cfg['ball']])
        if FIRST.get(cfg['rig']) == who: OPEN[cfg['rig']] = (who, round(d['grab_t'] + 0.3, 2))   # the room opens on this turn, the bowler at the rack
    for c in LANE_CAST:
        arm, mesh, a = rigs[c['who']]; c['acts'] = a; out.append((c, arm, mesh))
    return out


# ---------------------------------------------------------------- bake and export
def bake(sc, objs, phantoms, seated, args):
    """The alley's light baked into atlases (the people out of it: they all move); then room.glb, the people (and the
    lanes' rigs) and room.json."""
    os.makedirs(WEB, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    for c, arm, mesh in seated: mesh.hide_render = True
    export, atlases = stages.bake(objs, R.RH * R.SCALE, OUT, int(args.get('size', 2048)), int(args.get('samples', 320)))
    for c, arm, mesh in seated: mesh.hide_render = False
    cine.export_glb(export, os.path.join(WEB, 'room.glb'))
    meta = stages.room_meta(R.RH * R.SCALE, atlases); meta.update(_capture_meta())
    meta['people'] = _export_people(seated)
    stages.write_meta(WEB, meta)


def _export_people(seated):
    out = os.path.join(WEB, 'people'); os.makedirs(out, exist_ok=True); metas = []
    for c, arm, mesh in seated:
        pelvis = f"{c['who']}_root" if c['who'].startswith('lane') else 'Bip01 Pelvis'
        people.export_person(arm, mesh, c['acts'], os.path.join(out, f"{c['who']}.glb"), roam=c.get('roam', ()), pelvis=pelvis)
        metas.append(person_meta(c))
    return metas


def _capture_meta():
    """How to light the people as the bake lit the room (three.js: y up, z = -Blender y; module metres): the troffers
    as the ceiling's light, the bulbs over the bar and the neon as small bright spheres."""
    bulbs = []
    for l in RIG['lights']:
        if l.type != 'LIGHT' or l.data.type != 'POINT': continue
        r = 0.02 if l.name.startswith('bulb') else 0.05; e = l.data.energy
        bulbs.append({'x': round(l.location.x, 3), 'y': round(l.location.z, 3), 'z': round(-l.location.y, 3), 'r': r,
                      'L': round(e / (4 * math.pi * r ** 2) / 60, 2), 'color': [round(v, 3) for v in l.data.color]})
    at = [[round(v, 3) for v in (p.x, p.z, -p.y)] for p in (P(0.0, R.STOOL_Y, 1.3), P(-6.5, 0.5, 1.2), P(2.0, 2.0, 1.0))]
    return {'capture': {'ceiling': [0.62, 0.56, 0.46], 'walls': [0.5, 0.36, 0.28], 'emitters': bulbs, 'windows': [], 'at': at}}


def person_meta(c):
    """The acts in a person's (or a lane's) file, the looping one first, how long it lasts and how often each idle
    comes up; an act that cues others names them; the act the room opens on, and how far into it."""
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
    stages.update_meta(WEB, people=_export_people(seated), **_capture_meta())
    for c, arm, mesh in seated: people.pose_at(arm, c['acts'][c['work'][0]], int(c['acts'][c['work'][0]].frame_range[0]) + 60)
    for which in str(args.get('cams', 'bar,heads')).split(','):
        preview(sc, cams, which, int(args.get('samples', 64)), os.path.join(OUT, f'people_{which}.png'), size=(1200, 800))
