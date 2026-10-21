# Game of Thrones: assemble the throne end of the Red Keep's great hall and King Robert's court; then preview, bake and
# export.
import math, os
import bpy
from mathutils import Vector, Matrix
import cine, people, stages
from stages import camera
import rooms.game_of_thrones as R

ROOM = 'game-of-thrones'
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
    # the cast first: their acts are posed frame by frame, and every pose re-evaluates the scene
    seated = [] if args.get('nocast') else cast(crowd, args)
    SEATED[:] = seated
    # the hall at its true size; UVs made there (the stone keeps its real grain); then all of it shrunk into the module
    R.shell(M, static, phantom)
    glass = R.finishes(M, static)
    R.dais(M, static)
    R.throne(M, static)
    if not args.get('noblades'): R.blades(M, static)
    for k, c in enumerate(R.COLUMNS): R.column(f'column{k}', c, M, static)
    import random
    rnd = random.Random(11); flames = []
    for k, c in enumerate(R.CANDELABRA):
        flames += R.candelabrum(f'candelabrum{k}', (c[0], c[1], R.step_z(c[1]) if abs(c[0]) < R.DAIS_X else 0.0), M, static, rnd)
    R.floor_bands(M, static)
    RIG['lights'] = R.lights(flames, glass)
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
            'close': camera('cam_close', (3.4, -6.4, 2.9), (0.0, 0.8, 1.2), 34),
            'front': camera('cam_front', (0.0, -7.4, 1.7), (0.0, 1.5, 1.4), 44),
            'throne': camera('cam_throne', (0.6, -1.2, 1.4), (0.0, 1.6, 1.3), 46),
            'left': camera('cam_left', (-3.9, -3.2, 1.7), (0.5, 1.8, 1.0), 52),
            'right': camera('cam_right', (4.2, -3.3, 1.7), (-0.6, 1.8, 1.0), 52),
            'door': camera('cam_door', (1.4, -1.0, 1.2), (3.36, 2.8, 0.9), 50),
            'top': camera('cam_top', (0.0, 0.0, 15.0), (0.0, 0.1, 0.0), 36),
            'ned': camera('cam_ned', (1.5, -3.4, 1.2), (-0.4, -0.7, 0.5), 40),            # the kneel, from the front right
            'dais': camera('cam_dais', (0.4, -2.2, 1.5), (0.0, 1.4, 0.75), 42),           # the throne, the king and the court on the landing
            'whisper': camera('cam_whisper', (-0.4, -3.6, 1.0), (-2.2, -2.3, 0.55), 38),  # Littlefinger and Varys
            'steps': camera('cam_steps', (3.6, -2.6, 1.0), (1.8, 0.2, 0.45), 40)}         # Tyrion on the steps, Jaime
    return sc, M, objs, list(phantom.objects), seated, cams


def _tidy():
    """Imported props come under helper empties: keep their children where they are and drop the empties."""
    bpy.context.view_layer.update()
    for o in [o for o in bpy.data.objects if o.type == 'EMPTY']:
        for ch in o.children:
            mw = ch.matrix_world.copy(); ch.parent = None; ch.matrix_world = mw
        bpy.data.objects.remove(o, do_unlink=True)


KEEP = ('solid_', 'left_wall', 'back_wall', 'kerb', 'floor', 'subfloor', 'bay_haunch', 'colonnette', 'win_jamb')   # names that carry rules


def _merge(objs):
    """Join the many small pieces, one object per atlas and material: fewer meshes to draw."""
    groups = {}
    for o in objs:
        if o.get('role') or len(o.material_slots) != 1 or o.name.startswith(KEEP): continue      # (the flames have no atlas: one mesh too)
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
# King Robert's court, all at their true heights (the room shrinks them with the hall). Three have sculpted heads
# (fans' models, CC BY): Tyrion, Cersei, the Hound; the others are Rocketbox faces made up as the actors.
OBJ = os.path.join(cine.CACHE, 'objaverse'); SKF = os.path.join(cine.CACHE, 'sketchfab')


def _tex(who, prefix, *names):
    return {f'{prefix}_{n}.tga': f'{who}/{prefix}_{n}.png' for n in names}


CAST = [
    dict(who='robert', avatar='Male_Adult_05', shape=('heavy', 1.0), height=1.75,
         shell=dict(colour=(42, 33, 27), hem=-0.03, thick=0.008, gap=0.006, fall=0.016, front=36.0, temple=16.0, nape=-26.0, curl=1.0, width=0.036),
         skirt=dict(image='robert/coat.png', hem=0.36, top=-0.02, ease=0.03, flare=0.2, folds=10, depth=0.012, front_open=0.55),
         crown=True, tex=_tex('robert', 'm009', 'head_color', 'body_color', 'body_normal'), maps=dict(head={'Roughness': 'robert/m009_head_rough.png'})),
    dict(who='ned', avatar='Medical_Male_01', shape=('lean', 1.2), height=1.78,
         shell=dict(colour=(86, 64, 46), hem=-0.15, thick=0.004, gap=0.005, fall=0.012, front=34.0, temple=14.0, nape=-30.0),
         tex=_tex('ned', 'm152', 'head_color', 'body_color', 'body_normal'), maps=dict(head={'Roughness': 'ned/m152_head_rough.png'})),
    dict(who='jaime', avatar='Male_Adult_16', shape=('athletic', 1.0), height=1.85,
         cape=dict(image='jaime/cloak.png', hem=0.32), tex=_tex('jaime', 'm019', 'head_color', 'body_color', 'body_normal'),
         maps=dict(body={'Metallic': 'jaime/m019_body_metal.png', 'Roughness': 'jaime/m019_body_rough.png'})),
    dict(who='joffrey', avatar='Male_Adult_11', shape=('lean', 1.0), height=1.73,
         shell=dict(colour=(236, 202, 130), hem=0.06, thick=0.005, gap=0.004, fall=0.008, front=40.0, temple=20.0, nape=-16.0, width=0.03, layers=2),
         skirt=dict(image='joffrey/coat.png', hem=0.5, top=0.0, ease=0.025, flare=0.16, folds=10, depth=0.01, front_open=0.5),
         tex=_tex('joffrey', 'm001', 'head_color', 'body_color', 'body_normal')),
    dict(who='littlefinger', avatar='Male_Adult_07', shape=('lean', 1.0), height=1.73,
         skirt=dict(image='littlefinger/coat.png', hem=0.3, top=0.0, ease=0.022, flare=0.12, folds=12, depth=0.008, front_open=0.4),
         tex=_tex('littlefinger', 'm013', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
    dict(who='varys', avatar='Business_Male_04', shape=('heavy', 0.55), height=1.79,
         skirt=dict(image='varys/robe.png', hem=0.035, top=-0.06, ease=0.03, flare=0.14, folds=12, depth=0.01),
         tex=_tex('varys', 'm015', 'body_color', 'body_normal')),
    dict(who='tyrion', avatar='Male_Adult_06', shape=('athletic', 1.0), height=1.35,
         proportion={'Thigh': 0.5, 'Calf': 0.56, 'UpperArm': 0.7, 'Forearm': 0.76},
         head=dict(glb=os.path.join(OBJ, 'tyrion_head_kling.glb'), keep=None, front='+y', eyes='Object_3', cut=0.02, fan_cut=-0.025, decimate={'Object': 0.55}),
         tex=_tex('tyrion', 'm011', 'body_color', 'body_normal')),
    dict(who='cersei', avatar='Female_Adult_15', shape=None, height=1.68,
         shell=dict(colour=(222, 184, 118), hem=-0.3, thick=0.007, gap=0.006, fall=0.014, front=40.0, temple=16.0, nape=-26.0, curl=1.0, width=0.036),
         head=dict(glb=os.path.join(OBJ, 'cersei_head_imthirutj.glb'), keep=None, front='-y',
                   eyes=((-0.285, -1.12, 0.314), (0.291, -1.12, 0.314)), cut=0.03, fan_cut=-0.025, decimate={'Object': 0.3}, tone=(1.14, 1.04, 0.97), neck_skin=True, follow=0.008, scalp=(132, 118, 80)),
         skirt=dict(image='cersei/gown.png', hem=0.0, top=0.08, ease=0.02, flare=0.32, folds=16, depth=0.014),
         tex=_tex('cersei', 'f018', 'head_color', 'opacity_color', 'body_color', 'body_normal')),
    dict(who='hound', avatar='Male_Adult_12', shape=('broad', 1.0), height=1.98,
         head=dict(glb=os.path.join(SKF, 'the_hound_madcatd.glb'), keep=['Object_4', 'Object_6', 'Object_8', 'Object_28', 'Object_25', 'Object_12'],
                   front='-y', eyes='Object_6', cut=0.02, fan_cut=-0.09, decimate={'Object_4': 0.35, 'Object_6': 0.15, 'Object_12': 0.15, 'Object_8': 0.4}, thin={'Object_25': 0.28, 'Object_28': 0.5},
                   scalp=(34, 28, 24), tone=(0.92, 0.82, 0.74), colours={'huzi': (40, 30, 24), 'material_5': (44, 34, 28), 'xiongjia': (16, 16, 18)}),
         shell=dict(colour=(44, 36, 30), hem=-0.2, thick=0.004, gap=0.005, fall=0.014, front=36.0, temple=12.0, nape=-30.0, swept_cards=True),
         tex=_tex('hound', 'm007', 'body_color', 'body_normal'), maps=dict(body={'Metallic': 'hound/m007_body_metal.png', 'Roughness': 'hound/m007_body_rough.png'})),
]


def _cloth(who, image):
    """A costume's modelled cloth (a gown, a robe, a cloak): its painted texture."""
    m = bpy.data.materials.new(f'{who}_cloth'); nt = m.node_tree; p = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.join(PEOPLE_TEX, image), check_existing=True)
    nt.links.new(t.outputs['Color'], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.62; p.inputs['Specular IOR Level'].default_value = 0.4
    p.inputs['Sheen Weight'].default_value = 0.3; p.inputs['Sheen Tint'].default_value = (0.5, 0.45, 0.4, 1)
    return m


def _crown(arm, mesh):
    """King Robert's crown: a gold band round the brow with tines rising from it like a stag's antlers, some forked;
    skinned to the head, joined into the body."""
    import bmesh
    c, em, J = people._head_frame(arm); bvh = people._bvh(mesh)
    gold = cine.material('crown_gold', (0.78, 0.58, 0.24), rough=0.32, metal=1.0)
    bm = bmesh.new(); zc = em.z + 0.045; ring = []
    for i in range(48):
        a = 2 * math.pi * i / 48; d = Vector((math.sin(a), -math.cos(a), 0.0))
        h = bvh.ray_cast(Vector((c.x, c.y, zc)) + d * 0.3, -d, 0.3)[0]
        r = ((Vector((h.x, h.y, 0)) - Vector((c.x, c.y, 0))).length if h is not None else 0.1) + 0.006
        ring.append((a, d, r))
    def tube_bm(pts, rad):
        n = len(pts); rings = []
        for i, p in enumerate(pts):
            t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized(); u = t.orthogonal().normalized(); v = t.cross(u)
            rr = rad * (1 - 0.7 * i / max(n - 1, 1))
            rings.append([bm.verts.new(p + (u * math.cos(2 * math.pi * k / 6) + v * math.sin(2 * math.pi * k / 6)) * rr) for k in range(6)])
        for a_, b_ in zip(rings, rings[1:]):
            for k in range(6): bm.faces.new((a_[k], a_[(k + 1) % 6], b_[(k + 1) % 6], b_[k]))
    band = []
    for a, d, r in ring:
        for dz in (-0.012, 0.012): band.append(Vector((c.x, c.y, zc + dz)) + d * r)
    vb = [bm.verts.new(p) for p in band]
    for i in range(48):
        j = (i + 1) % 48; bm.faces.new((vb[2 * i], vb[2 * j], vb[2 * j + 1], vb[2 * i + 1]))
    import random
    rnd = random.Random(9)
    for i in range(0, 48, 4):                                                  # twelve tines, every third one forked
        a, d, r = ring[i]; base = Vector((c.x, c.y, zc + 0.01)) + d * r
        tip = base + d * 0.012 + Vector((0, 0, 0.05 + 0.02 * rnd.random()))
        mid = (base + tip) / 2 + d * 0.01
        tube_bm([base, mid, tip], 0.0045)
        if (i // 4) % 3 == 0:
            side = Vector((-d.y, d.x, 0)) * (1 if rnd.random() < 0.5 else -1)
            tube_bm([mid, mid + side * 0.015 + Vector((0, 0, 0.025))], 0.003)
    for f in bm.faces: f.smooth = True
    me = bpy.data.meshes.new('crown'); bm.to_mesh(me); bm.free(); me.materials.append(gold)
    ob = bpy.data.objects.new('crown', me); [cl.objects.link(ob) for cl in mesh.users_collection]
    vg = ob.vertex_groups.new(name='Bip01 Head'); vg.add(list(range(len(me.vertices))), 1.0, 'REPLACE')
    me.transform(mesh.matrix_world.inverted()); ob.matrix_world = mesh.matrix_world
    people._joined(mesh, ob)


def _maps(mesh, part, maps):
    """Grey maps on one of the avatar's materials ('body', 'head'): {'Metallic' | 'Roughness': image}."""
    for slot in mesh.material_slots:
        m = slot.material
        if not m or part not in m.name or 'opacity' in m.name: continue
        nt = m.node_tree; p = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        for inp, path in maps.items():
            t = nt.nodes.new('ShaderNodeTexImage'); t.image = cine.image(os.path.join(PEOPLE_TEX, path), colour=False)
            nt.links.new(t.outputs['Color'], p.inputs[inp])


def make_person(c, col):
    """One of the court, standing at the origin facing -y: the avatar, its build, its proportions, its head, its
    height."""
    tex = {k: os.path.join(PEOPLE_TEX, v) for k, v in c.get('tex', {}).items() if os.path.exists(os.path.join(PEOPLE_TEX, v))}
    arm, mesh = people.load_avatar(c['avatar'], textures=tex, collection=col)
    arm.animation_data_clear()                                  # the FBX's take keys the object's scale (0.01): a render would undo the height
    mesh['person'] = c['who']; arm['person'] = c['who']
    if c.get('shape'): people.reshape(arm, mesh, *c['shape'])
    if c.get('proportion'): people.reproportion(arm, mesh, c['proportion'])
    if c.get('head'):
        h = c['head']
        people.swap_head(arm, mesh, h['glb'], h['keep'], h['front'], h['eyes'], cut=h.get('cut', 0.0), fan_cut=h.get('fan_cut', -0.03), decimate=h.get('decimate'),
                         thin=h.get('thin'), keep_cards=bool(c.get('keep_cards')), tone=h.get('tone'), neck_skin=h.get('neck_skin', False), match_neck=h.get('match_neck', False), follow=h.get('follow', 0.0), scalp=h.get('scalp'))
        for sl in mesh.material_slots:                                # strand hair and brows with no texture: their colour
            rgb = next((v for k_, v in h.get('colours', {}).items() if sl.material and k_ == sl.material.name), None)
            if rgb is None: continue
            p = next(n for n in sl.material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            for l in list(p.inputs['Base Color'].links): sl.material.node_tree.links.remove(l)
            p.inputs['Base Color'].default_value = (*[(v / 255) ** 2.2 for v in rgb], 1.0); p.inputs['Roughness'].default_value = 0.7
    if c.get('shell') or (c.get('head') and not c.get('keep_cards')): people.remove_hair_cards(mesh)
    bpy.context.view_layer.update()
    top = max((mesh.matrix_world @ v.co).z for v in mesh.data.vertices)        # the height to the crown of the head (no hair, no crown)
    J = people._joints(arm)
    if c.get('shell'):
        h = dict(c['shell']); h['hem'] = J['Bip01 Neck'].z + h['hem']
        people.hair_shell(arm, mesh, **h)
    if c.get('crown'): _crown(arm, mesh)
    for part, maps in c.get('maps', {}).items(): _maps(mesh, part, maps)
    if c.get('skirt'):
        h = dict(c['skirt']); h['hem'] = h['hem'] * top / c['height']                # the hem's height in the rest pose, before the scaling
        people.skirt(arm, mesh, _cloth(c['who'], h.pop('image')), **h)
    if c.get('cape'):
        h = dict(c['cape']); h['hem'] = h['hem'] * top / c['height']
        people.cape(arm, mesh, _cloth(c['who'], h.pop('image')), **h)
    for ca in list(mesh.data.color_attributes): mesh.data.color_attributes.remove(ca)   # joins fill them for added parts; the web multiplies them in
    s = c['height'] / top
    arm.scale = arm.scale * s; arm.location = (arm.location.x, arm.location.y, arm.location.z * s)
    bpy.context.view_layer.update()
    return arm, mesh


# ---------------------------------------------------------------- the court in the hall
# Places are given in the hall's true metres and brought into the module by SCALE, like the hall; the court is shrunk
# with it. Robert on the throne; Cersei at his right hand on the landing with her wine, Joffrey at his left, the Hound
# behind Joffrey; Jaime at the dais's foot on guard; Ned before the steps (his act: he kneels, rises, speaks, goes out
# by the left doorway and comes back; the king waves him up, the court watches); Tyrion on the steps with his wine;
# Littlefinger and Varys whispering by the left columns.
S = R.SCALE


def P(x, y, z=0.0):
    return Vector((x, y, z)) * S


def floor_z(x, y):
    """The hall's floor at (x, y), true metres: the broad flight, the landing, the round step and the plinth."""
    if abs(x) > R.DAIS_X or y < R.DAIS_FRONT: return 0.0
    if y < R.LAND_Y: return R.step_z(y)
    r = math.hypot(x, y - R.YW)
    return R.LAND_Z + (2 * R.RISE if r <= R.R2 else R.RISE if r <= R.R1 else 0.0)


SPOTS = {                                      # (x, y) in the hall, the facing
    'ned': ((-0.6, -1.8), (0.25, 1.0)),
    'cersei': ((-2.25, 2.2), (0.45, -1.0)),
    'joffrey': ((2.15, 2.05), (-0.4, -1.0)),
    'hound': ((3.6, 2.3), (-0.6, -1.0)),
    'jaime': ((4.75, 0.25), (-0.65, -1.0)),
    'littlefinger': ((-3.2, -3.55), (-0.8, -0.6)),
    'varys': ((-4.1, -4.15), (0.8, 0.6)),
}
SEATS = {'robert': ((0.0, 3.0, R.PLINTH_Z + 0.56), (0.0, -1.0)),          # the throne's seat (measured), its facing
         'tyrion': ((2.45, -0.1, R.step_z(-0.1)), (-0.3, -1.0))}           # the fourth step, his feet on the fifth
BASES = {'robert': 'm_sit_chair_breathe_01', 'ned': 'm_idle_breathe_01', 'jaime': 'm_idle_breathe_02', 'joffrey': 'm_idle_neutral_03',
         'littlefinger': 'm_gestic_talk_cool', 'varys': 'm_gestic_listen_neutral_02', 'tyrion': 'm_sit_chair_breathe_01',
         'cersei': 'f_idle_breathe_02', 'hound': 'm_idle_breathe_03'}
WORK = {'robert': ('sit', 16, 34), 'ned': ('stand', 10, 22), 'jaime': ('guard', 14, 30), 'joffrey': ('stand', 10, 24), 'littlefinger': ('talk', 12, 24),
        'varys': ('listen', 12, 24), 'tyrion': ('sit', 14, 30), 'cersei': ('wine', 12, 26), 'hound': ('guard', 16, 34)}
IDLES = {'robert': {'laugh': ('m_gestic_laugh_loud', 0.6), 'look': ('m_sit_chair_idle_look_around', 0.5), 'wave': (None, 0.0)},
         'ned': {'kneel': (None, 1.4), 'listen': ('m_gestic_listen_neutral_01', 0.4)},
         'jaime': {'look': ('m_idle_look_around_01', 0.5), 'watch': (None, 0.0)},
         'joffrey': {'laugh': ('m_gestic_laugh_low', 0.5), 'pace': (None, 0.6), 'watch': (None, 0.0)},
         'littlefinger': {'listen': ('m_gestic_listen_neutral_01', 0.7), 'glance': ('m_idle_neutral_02', 0.4)},
         'varys': {'talk': ('m_gestic_talk_relaxed_01', 0.0)},
         'tyrion': {'sip': (None, 0.8), 'toast': (None, 0.4), 'shrug': ('m_sit_chair_gestic_shrug_01', 0.4)},
         'cersei': {'sip': (None, 0.7), 'talk': ('f_gestic_talk_self-assured_01', 0.4), 'watch': (None, 0.0)},
         'hound': {'look': ('m_idle_look_around_02', 0.5)}}
CUE = {'ned': {'kneel': {'robert': 'wave', 'cersei': 'watch', 'joffrey': 'watch', 'jaime': 'watch'}},
       'littlefinger': {'listen': {'varys': 'talk'}}}
FIRST = {'ned': 'kneel'}
ROAM = {'ned': ('kneel',), 'joffrey': ('pace',)}
HANDS = {'cersei', 'tyrion', 'jaime', 'varys', 'robert', 'hound'}          # acts that shape the hands (a goblet, a hilt, sleeves)
SPINE = ('Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2')
ARMS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('Clavicle', 'UpperArm', 'Forearm', 'Hand'))
LEGS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('Thigh', 'Calf', 'Foot'))
FINGERS = tuple(f'Bip01 {s} Finger{f}{j}' for s in 'LR' for f in '01234' for j in ('', '1', '2'))
ALL = ('Bip01 Pelvis',) + SPINE + ARMS + LEGS + ('Bip01 Neck', 'Bip01 Head')
OPEN = {}


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
    yaw = max(-1.2, min(1.2, yaw))
    people.bend(arm, 'Bip01 Neck', up, yaw * 0.35 * w); people.bend(arm, 'Bip01 Head', up, yaw * 0.65 * w)
    people.bend(arm, 'Bip01 Neck', right, pitch * 0.3 * w); people.bend(arm, 'Bip01 Head', right, pitch * 0.7 * w)


def _head_of(who):
    """Where someone's head is in their loop (for looks)."""
    c = next(c for c in CAST if c['who'] == who)
    if who in SEATS: (x, y, z), f = SEATS[who]; return P(x, y, z + 0.82 * c['height'] / 1.75) + Vector((*f, 0)).normalized() * 0.05 * S
    (x, y), f = SPOTS[who]
    return P(x, y, floor_z(x, y) + 0.93 * c['height'])


def _samples(arm, action, bone='Bip01 Head'):
    """Where a bone is (world) at every frame of an act."""
    f0, f1 = int(action.frame_range[0]), int(action.frame_range[1]); out = []
    for f in range(f0, f1 + 1):
        people.pose_at(arm, action, f); out.append(people._world(arm, arm.pose.bones[bone]).translation.copy())
    people.pose_at(arm, action, f0)
    return out


def _bind(arm, mesh, bm, bone, mats, name):
    """Geometry made in the world at the body's present pose (a goblet in the hand), carried back to the rest pose
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


def _goblet_bm(at, up, k):
    """A footed metal goblet standing on `at` along `up`, `k` its scale (the room's): 17 cm tall at true size."""
    import bmesh
    bm = bmesh.new(); T_ = Matrix.Translation(at) @ up.to_track_quat('Z', 'Y').to_matrix().to_4x4() @ Matrix.Scale(k, 4)
    prof = [(0.0, 0.0), (0.038, 0.0), (0.036, 0.008), (0.008, 0.02), (0.006, 0.07), (0.014, 0.08), (0.034, 0.1), (0.042, 0.13), (0.043, 0.17),
            (0.04, 0.17), (0.038, 0.135), (0.0, 0.115)]
    seg = 14; rings = [[bm.verts.new(T_ @ Vector((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), z))) for i in range(seg)] for r, z in prof]
    for a, b in zip(rings, rings[1:]):
        for i in range(seg): bm.faces.new((a[i], a[(i + 1) % seg], b[(i + 1) % seg], b[i]))
    w = [bm.verts.new(T_ @ Vector((0.037 * math.cos(2 * math.pi * i / seg), 0.037 * math.sin(2 * math.pi * i / seg), 0.15))) for i in range(seg)]
    bm.faces.new(w); bm.faces.ensure_lookup_table(); bm.faces[-1].material_index = 1      # the wine
    return bm


def _sword_bm(arm, k):
    """A sword in its scabbard at the left hip (the rest pose, world): the scabbard hanging back and down from the
    belt, the cross-guard and the grip forward and up, a round pommel; `k` the person's scale."""
    import bmesh
    J = people._joints(arm); pel = J['Bip01 Pelvis']
    fwd = Vector(arm['fwd']); up = Vector((0, 0, 1)); right = fwd.cross(up).normalized()
    hip = pel + (-right * 0.17 + fwd * 0.02 + up * 0.02) * k
    d = (-right * 0.08 - fwd * 0.45 - up).normalized()         # the scabbard's line: down, back, a little out
    side = d.cross(fwd).normalized()
    bm = bmesh.new()
    def bar(p0, p1, w, t, n=4):
        dd = (p1 - p0).normalized(); s_ = dd.orthogonal().normalized(); f_ = dd.cross(s_)
        rings = [[bm.verts.new(p + (s_ * math.cos(2 * math.pi * i / n + math.pi / 4) * w + f_ * math.sin(2 * math.pi * i / n + math.pi / 4) * t)) for i in range(n)] for p in (p0, p1)]
        for i in range(n): bm.faces.new((rings[0][i], rings[0][(i + 1) % n], rings[1][(i + 1) % n], rings[1][i]))
        bm.faces.new(rings[0][::-1]); bm.faces.new(rings[1])
    tip = hip + d * 0.88 * k
    bar(hip, tip, 0.03 * k, 0.012 * k)                                            # the scabbard
    g0 = hip - d * 0.02 * k
    bar(g0 - side * 0.11 * k, g0 + side * 0.11 * k, 0.012 * k, 0.012 * k)         # the cross-guard
    grip = g0 - d * 0.2 * k
    bar(g0, grip, 0.016 * k, 0.016 * k)
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.026 * k, matrix=Matrix.Translation(grip - d * 0.02 * k))
    return bm, grip


def _add_sword(arm, mesh, k, metal):
    import bmesh
    bm, grip = _sword_bm(arm, k)
    me = bpy.data.meshes.new('sword'); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new('sword', me); [cl.objects.link(ob) for cl in mesh.users_collection]
    me.materials.append(cine.material('scabbard_leather', (0.05, 0.035, 0.025), rough=0.6)); n_sc = 6
    me.materials.append(metal)
    for p in me.polygons: p.material_index = 0 if p.index < n_sc else 1
    ob.matrix_world = mesh.matrix_world.copy(); me.transform(mesh.matrix_world.inverted())
    vg = ob.vertex_groups.new(name='Bip01 Pelvis'); vg.add(list(range(len(me.vertices))), 1.0, 'REPLACE')
    people._joined(mesh, ob)
    return grip


def cast(col, args):
    """Load, dress, shape and place the court, and bake their acts (cached: retargets and IK take minutes)."""
    full = bool(args.get('full'))
    spec = {'cast': CAST, 'spots': SPOTS, 'seats': SEATS, 'bases': BASES, 'work': WORK, 'idles': IDLES, 'cue': CUE, 'scale': S, 'full': full, 'v': 5}
    for c in CAST:
        c['work'] = WORK[c['who']]; c['idles'] = IDLES[c['who']]; c['cue'] = CUE.get(c['who'], {}); c['roam'] = ROAM.get(c['who'], ())
    seated = stages.cast_cache(OUT, CAST, spec, lambda: _make_cast(col, full), col)
    for c, arm, mesh in seated:
        if 'open_act' in arm: OPEN[c['who']] = (arm['open_act'], float(arm['open_at']))
        people.pose_at(arm, c['acts'][c['work'][0]], int(c['acts'][c['work'][0]].frame_range[0]) + 30)
    return seated


def _place(c, arm):
    """Shrink a person with the hall and set them at their spot or seat, facing their way; the base clip retargeted
    there (cycles 2: a perfect loop) and slid so its pelvis is over the spot (or the seat, lowered onto it)."""
    who = c['who']
    arm.scale = arm.scale * S; arm.location = arm.location * S
    bpy.context.view_layer.update()
    if who in SEATS: (x, y, z), f = SEATS[who]; zf = R.step_z(y - 0.42) if who == 'tyrion' else R.PLINTH_Z
    else: (x, y), f = SPOTS[who]; zf = floor_z(x, y)
    f = Vector((*f, 0)).normalized()
    z0 = arm.location.z                                    # the armature's origin is at the hips: keep it above the floor
    people.face(arm, f); arm.location = (x * S, y * S, z0 + zf * S); bpy.context.view_layer.update()
    arm['fwd'] = list(f)
    base, frames, _ = people.retarget(arm, BASES[who], cycles=2, action_name=f'{who}_base')
    people.pose_at(arm, base, frames[0])
    pel = people._world(arm, arm.pose.bones['Bip01 Pelvis']).translation
    want = P(x, y) - f * (0.03 * S if who in SEATS else 0.0)
    arm.location.x += want.x - pel.x; arm.location.y += want.y - pel.y
    bpy.context.view_layer.update()
    drop = 0.0
    if who in SEATS:                                       # the clip's pelvis over a 0.52 m seat: lowered (or raised) onto this one
        people.pose_at(arm, base, frames[0])
        pz = people._world(arm, arm.pose.bones['Bip01 Pelvis']).translation.z
        k_ = arm.get('leg_k', 1.0) * c['height'] / 1.75
        drop = pz - (z * S + 0.09 * S * k_)
        cine.log(f'seat {who}: pelvis {pz / S:.3f} (hall m), seat {z:.3f}, drop {drop / S:+.3f}')
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
    # props: goblets, swords (made before the acts, at the rest pose or the first pose)
    gold = cine.material('goblet_gold', (0.8, 0.6, 0.28), rough=0.3, metal=1.0); pewter = cine.material('goblet_pewter', (0.55, 0.55, 0.56), rough=0.35, metal=1.0)
    wine = cine.material('goblet_wine', (0.12, 0.008, 0.02), rough=0.1)
    steel = cine.material('sword_steel', (0.62, 0.6, 0.58), rough=0.3, metal=1.0); gilt = cine.material('sword_gilt', (0.78, 0.58, 0.26), rough=0.3, metal=1.0)
    for who, metal in (('jaime', gilt), ('hound', steel)):
        m = made[who]; m['grip'] = _add_sword(m['arm'], m['mesh'], m['k'], metal)
    for m in made.values(): m['mesh'].hide_viewport = True
    acts = {k: {} for k in made}
    _robert_acts(made['robert'], acts['robert'], full); _cersei_acts(made['cersei'], acts['cersei'], full); _tyrion_acts(made['tyrion'], acts['tyrion'], full)
    for who, mats_ in (('cersei', [gold, wine]), ('tyrion', [pewter, wine])):
        m = made[who]; people.pose_at(m['arm'], acts[who][m['c']['work'][0]], int(m['frames'][0]))
        pel, fwd, right, up = _live(m['arm'])
        H = people._world(m['arm'], m['arm'].pose.bones['Bip01 R Hand']).translation
        foot = H + (fwd * 0.06 - right * 0.03 - up * 0.08) * m['k']
        _bind(m['arm'], m['mesh'], _goblet_bm(foot, Vector((0, 0, 1)), m['k']), 'Bip01 R Hand', mats_, 'goblet')
    _ned_acts(made['ned'], acts['ned'], full); _jaime_acts(made['jaime'], acts['jaime'], full); _joffrey_acts(made['joffrey'], acts['joffrey'], full)
    _littlefinger_acts(made['littlefinger'], acts['littlefinger'], full); _varys_acts(made['varys'], acts['varys'], full); _hound_acts(made['hound'], acts['hound'], full)
    if full: _kneel_scene(made, acts)
    for who, m in made.items():
        m['c']['acts'] = acts[who]
        for name, a in acts[who].items():
            if who not in HANDS: people.freeze(a)
        if m['base'] not in acts[who].values(): bpy.data.actions.remove(m['base'])
        people.pose_at(m['arm'], acts[who][m['c']['work'][0]], int(m['frames'][0]) + 30)
        m['mesh'].hide_viewport = False
    return seated


def _clip_act(m, acts, name, clip, step, fingers=False):
    """An idle from a clip: anchored on the base, authored over by `step` (looks, a held goblet)."""
    arm, base = m['arm'], m['base']; who = m['c']['who']
    src = people.anchor(arm, people.retarget(arm, clip, action_name=f'{who}_{name}_src')[0], base)
    fr = (int(src.frame_range[0]), int(src.frame_range[1]))
    acts[name] = people.custom_act(arm, src, fr, f'{who}_{name}', step, _all(arm, fingers=fingers))
    bpy.data.actions.remove(src)


def _long_base(m, seconds, name):
    """The base clip run long enough for an act of `seconds` (a clip played past its end stands still)."""
    arm, c = m['arm'], m['c']; per = (m['frames'][1] - m['frames'][0]) / people.FPS / 2
    return people.retarget(arm, BASES[c['who']], cycles=max(2, math.ceil(seconds / per) + 1), action_name=f"{c['who']}_{name}_base")


# ---------------------------------------------------------------- the king
def _sit(arm, drop):
    people.shift_root(arm, (0, 0, -drop))


def _robert_acts(m, acts, full):
    """The king on the Iron Throne, sprawled, his eyes over the hall; idles: a laugh (his whole body), looking round;
    cued by Ned's kneeling: he waves him up, the right hand lifted off the arm, palm up, a flick."""
    arm, base, frames, drop, k = m['arm'], m['base'], m['frames'], m['drop'], m['k']; T = (frames[1] - frames[0]) / people.FPS
    ned = _head_of('ned')
    def sit(f, t):
        _sit(arm, drop); u = 2 * math.pi * t / T
        _look(arm, ned + P(1.5 * math.sin(u), 0, 0.3), 0.6)
        pel, fwd, right, up = _live(arm)
        for b_, a in zip(SPINE, (-0.06, -0.05, -0.03)): people.bend(arm, b_, right, a)       # leaning back into the iron
    acts['sit'] = people.custom_act(arm, base, frames, 'robert_sit', sit, _all(arm, fingers=True)); m['steps'] = {'sit': sit}
    if not full: return
    lb = people.retarget(arm, 'm_gestic_laugh_loud', action_name='robert_laugh_top')[0]
    lay = people.layer(base, lb, name='robert_laugh_layer')
    acts['laugh'] = people.custom_act(arm, lay, frames, 'robert_laugh', lambda f, t: (_sit(arm, drop), _look(arm, ned + P(0, 0, 0.6), 0.3)), _all(arm, fingers=True))
    bpy.data.actions.remove(lb); bpy.data.actions.remove(lay)
    _clip_act(m, acts, 'look', 'm_sit_chair_idle_look_around', lambda f, t: _sit(arm, drop), fingers=True)


def _wave(arm, t0, dur, k, t):
    """The king's right hand lifted from the throne's arm, palm up, flicked twice: 'rise'."""
    e = people.envelope(t - t0, dur, 0.7, 0.9) if t0 < t < t0 + dur else 0.0
    if e <= 0: return
    pel, fwd, right, up = _live(arm)
    sh = people._world(arm, arm.pose.bones['Bip01 R UpperArm']).translation
    flick = 0.06 * max(0.0, math.sin(2 * math.pi * (t - t0) / 0.9)) * k
    tgt = sh + (fwd * 0.34 + right * 0.16 - up * 0.12) * k + up * flick
    H0 = people._world(arm, arm.pose.bones['Bip01 R Hand']).translation.copy()
    g = H0.lerp(tgt, e)
    people.ik2(arm, 'R', g, g - up * 0.3 * k + right * 0.3 * k)
    people.palm_to(arm, 'R', (up * 0.9 + fwd * 0.3).normalized(), 0.9 * e)


# ---------------------------------------------------------------- the queen, her wine
def _hold(arm, side, k, w=1.0, at=None, tilt=0.0):
    """A goblet held before the chest, low, in the right hand (or a point it goes to)."""
    pel, fwd, right, up = _live(arm); sd = 1 if side == 'R' else -1
    sh = people._world(arm, arm.pose.bones[f'Bip01 {side} UpperArm']).translation
    tgt = at if at is not None else sh + (fwd * 0.24 - up * 0.3 - right * sd * 0.05) * k
    H0 = people._world(arm, arm.pose.bones[f'Bip01 {side} Hand']).translation.copy()
    g = H0.lerp(tgt, w)
    people.ik2(arm, side, g, g - up * 0.3 * k + right * sd * 0.3 * k - fwd * 0.05 * k)
    people.palm_to(arm, side, -right * sd, 0.9 * w)
    if tilt:
        hand = arm.pose.bones[f'Bip01 {side} Hand']; Hm = people._world(arm, hand); c_ = Hm.translation.copy()
        people._set_world(arm, hand, Matrix.Translation(c_) @ Matrix.Rotation(-tilt, 4, right) @ Matrix.Translation(-c_) @ Hm)


def _mouth(arm, k):
    Hd = people._world(arm, arm.pose.bones['Bip01 Head']).translation; pel, fwd, right, up = _live(arm)
    return Hd + (fwd * 0.12 - up * 0.12 - right * 0.03) * k


def _cersei_acts(m, acts, full):
    """The queen on the landing at the king's side, her goblet in her right hand, her eyes on the hall; idles: a sip;
    a word to the king (her own talk clip, the goblet kept); cued by Ned: she watches him, cold."""
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']; T = (frames[1] - frames[0]) / people.FPS
    ned, king = _head_of('ned'), _head_of('robert')
    def wine(f, t):
        _hold(arm, 'R', k); _look(arm, ned.lerp(king, 0.5 + 0.5 * math.sin(2 * math.pi * t / T)), 0.55)
    acts['wine'] = people.custom_act(arm, base, frames, 'cersei_wine', wine, _all(arm, fingers=True)); m['steps'] = {'wine': wine}
    if not full: return
    def sip(f, t):
        e = people.envelope(t, T, 1.4, 1.6)
        _hold(arm, 'R', k, at=people._world(arm, arm.pose.bones['Bip01 R Hand']).translation.lerp(_mouth(arm, k), e), tilt=0.6 * e)
        pel, fwd, right, up = _live(arm); people.bend(arm, 'Bip01 Head', right, -0.12 * e)
        _look(arm, ned, 0.5 * (1 - e))
    acts['sip'] = people.custom_act(arm, base, frames, 'cersei_sip', sip, _all(arm, fingers=True))
    _clip_act(m, acts, 'talk', 'f_gestic_talk_self-assured_01', lambda f, t: (_hold(arm, 'R', k), _look(arm, king, 0.75)), fingers=True)


# ---------------------------------------------------------------- the Imp on the steps
def _tyrion_feet(arm, k):
    """His feet planted on the step below the one he sits on."""
    z = R.step_z(SEATS['tyrion'][0][1] - 0.42) * S
    for s in 'LR':
        ft = people._world(arm, arm.pose.bones[f'Bip01 {s} Foot']).translation.copy()
        rest = arm.get('ankle', 0.07 * k)
        if ft.z < z + rest:
            pel, fwd, right, up = _live(arm)
            people.ik_leg(arm, s, Vector((ft.x, ft.y, z + rest)), ft + fwd * 0.5 * k + up * 0.4 * k)


def _tyrion_acts(m, acts, full):
    """Tyrion sitting on the steps below the throne, his goblet in hand, watching the court with a half smile; idles: a
    sip; a toast lifted to the king; a shrug."""
    arm, base, frames, drop, k = m['arm'], m['base'], m['frames'], m['drop'], m['k']; T = (frames[1] - frames[0]) / people.FPS
    J = people._joints(arm); arm['ankle'] = (J['Bip01 L Foot'].z - arm.location.z) * 1.0
    ned, king, lf = _head_of('ned'), _head_of('robert'), _head_of('littlefinger')
    def sit(f, t):
        _sit(arm, drop); _tyrion_feet(arm, k)
        pel, fwd, right, up = _live(arm)
        _hold(arm, 'R', k * 0.8, at=people._world(arm, arm.pose.bones['Bip01 R Thigh']).translation + (fwd * 0.28 + up * 0.12 - right * 0.04) * k)
        _look(arm, ned.lerp(lf, 0.5 + 0.5 * math.sin(2 * math.pi * t / T)), 0.6)
    acts['sit'] = people.custom_act(arm, base, frames, 'tyrion_sit', sit, _all(arm, fingers=True)); m['steps'] = {'sit': sit}
    if not full: return
    def sip(f, t):
        _sit(arm, drop); _tyrion_feet(arm, k); e = people.envelope(t, T, 1.3, 1.5)
        pel, fwd, right, up = _live(arm)
        rest = people._world(arm, arm.pose.bones['Bip01 R Thigh']).translation + (fwd * 0.28 + up * 0.12 - right * 0.04) * k
        _hold(arm, 'R', k * 0.8, at=rest.lerp(_mouth(arm, k), e), tilt=0.7 * e)
        people.bend(arm, 'Bip01 Head', right, -0.15 * e); _look(arm, ned, 0.5 * (1 - e))
    acts['sip'] = people.custom_act(arm, base, frames, 'tyrion_sip', sip, _all(arm, fingers=True))
    def toast(f, t):
        _sit(arm, drop); _tyrion_feet(arm, k); e = people.envelope(t, T, 1.2, 1.4)
        pel, fwd, right, up = _live(arm)
        rest = people._world(arm, arm.pose.bones['Bip01 R Thigh']).translation + (fwd * 0.28 + up * 0.12 - right * 0.04) * k
        sh = people._world(arm, arm.pose.bones['Bip01 R UpperArm']).translation
        _hold(arm, 'R', k * 0.8, at=rest.lerp(sh + (up * 0.25 + fwd * 0.12 + right * 0.08) * k, e))
        _look(arm, king, 0.8 * e + 0.3)
    acts['toast'] = people.custom_act(arm, base, frames, 'tyrion_toast', toast, _all(arm, fingers=True))
    def shrug(f, t):
        _sit(arm, drop); _tyrion_feet(arm, k)
        pel, fwd, right, up = _live(arm)
        _hold(arm, 'R', k * 0.8, at=people._world(arm, arm.pose.bones['Bip01 R Thigh']).translation + (fwd * 0.28 + up * 0.12 - right * 0.04) * k)
        _look(arm, lf, 0.6)
    _clip_act(m, acts, 'shrug', 'm_sit_chair_gestic_shrug_01', shrug, fingers=True)


# ---------------------------------------------------------------- the Kingsguard, the Hound
def _hilt(arm, m, side='L', w=1.0):
    """A hand resting on the sword's grip at the left hip (the grip is skinned to the pelvis: carried from the rest
    pose through it)."""
    k = m['k']; pel, fwd, right, up = _live(arm)
    rest_pel = arm.matrix_world @ arm.data.bones['Bip01 Pelvis'].matrix_local
    g = people._world(arm, arm.pose.bones['Bip01 Pelvis']) @ rest_pel.inverted() @ Vector(m['grip']) + up * 0.02 * k
    H0 = people._world(arm, arm.pose.bones[f'Bip01 {side} Hand']).translation.copy()
    sd = 1 if side == 'R' else -1
    tgt = H0.lerp(g - fwd * 0.02 * k, w)
    people.ik2(arm, side, tgt, tgt - up * 0.2 * k - right * sd * 0.35 * k - fwd * 0.2 * k)
    people.palm_to(arm, side, (-up * 0.6 + right * sd * 0.6).normalized(), 0.8 * w)


def _jaime_acts(m, acts, full):
    """Ser Jaime at the dais's foot in his gilt armour, his left hand on his sword's grip, at ease and watchful."""
    arm, base, frames = m['arm'], m['base'], m['frames']
    ned, joff = _head_of('ned'), _head_of('joffrey')
    def guard(f, t): _hilt(arm, m); _look(arm, ned + P(-1.0, 1.0, 0), 0.5)
    acts['guard'] = people.custom_act(arm, base, frames, 'jaime_guard', guard, _all(arm, fingers=True)); m['steps'] = {'guard': guard}
    if not full: return
    _clip_act(m, acts, 'look', 'm_idle_look_around_01', lambda f, t: _hilt(arm, m), fingers=True)


def _hound_acts(m, acts, full):
    """The Hound behind the prince, his left hand on his sword, his eyes on the hall."""
    arm, base, frames = m['arm'], m['base'], m['frames']
    ned = _head_of('ned')
    def guard(f, t): _hilt(arm, m); _look(arm, ned, 0.45)
    acts['guard'] = people.custom_act(arm, base, frames, 'hound_guard', guard, _all(arm, fingers=True)); m['steps'] = {'guard': guard}
    if not full: return
    _clip_act(m, acts, 'look', 'm_idle_look_around_02', lambda f, t: _hilt(arm, m), fingers=True)


# ---------------------------------------------------------------- the prince
def _joffrey_acts(m, acts, full):
    """Joffrey on the landing, chin up, looking down on Ned; idles: a sneering laugh; a few paces along the landing and
    back."""
    arm, base, frames = m['arm'], m['base'], m['frames']
    ned = _head_of('ned')
    stand = lambda f, t: _look(arm, ned, 0.6)
    acts['stand'] = people.custom_act(arm, base, frames, 'joffrey_stand', stand, _all(arm)); m['steps'] = {'stand': stand}
    if not full: return
    _clip_act(m, acts, 'laugh', 'm_gestic_laugh_low', lambda f, t: _look(arm, ned, 0.5))
    # pace: a few steps toward the throne's right, a turn, back, a turn to where he stood
    walk, walkf, vs = people.retarget(arm, 'm_walk_cool_01', inplace=True, cycles=6, action_name='joffrey_src_walk')
    turn, turnf, _ = people.retarget(arm, 'm_turn_left_180', action_name='joffrey_src_turn')
    (x, y), f0 = SPOTS['joffrey']; home = P(x, y); far = P(x + 1.25, y + 0.35)
    h_s = Vector((*f0, 0)).normalized()
    _h, p_s = people.heading(arm, base, frames[0])
    r_go = people.path([home, home.lerp(far, 0.5) + P(0, -0.1), far]); r_back = people.path([far, home.lerp(far, 0.5) + P(0, 0.08), home])
    htn, ptn = people.heading(arm, turn, turnf[0]); tdur = (turnf[1] - turnf[0]) / people.FPS
    go_dir = _flat(far - home)
    segs = [dict(src=base, f0=frames[0], dur=1.0, at=Matrix.Identity(4)),
            dict(src=walk, f0=walkf[0], dur=r_go[1] / vs, at=people.walk_along(arm, walk, walkf[0], vs, r_go), blend=0.8),
            dict(src=turn, f0=turnf[0], dur=tdur, at=people.carry(ptn, htn, far, go_dir), blend=0.5),
            dict(src=walk, f0=walkf[0] + 12, dur=r_back[1] / vs, at=people.walk_along(arm, walk, walkf[0], vs, r_back), blend=0.6),
            dict(src=turn, f0=turnf[0], dur=tdur, at=people.carry(ptn, htn, home, -go_dir), blend=0.5),
            dict(src=base, f0=frames[0], dur=1.6, at=Matrix.Identity(4), blend=1.0)]
    acts['pace'] = people.sequence(arm, base, 'joffrey_pace', segs, overlay=lambda tt, k_, lt: _look(arm, ned, 0.3) if k_ in (0, 5) else None)
    for a in (walk, turn): bpy.data.actions.remove(a)


# ---------------------------------------------------------------- the whisperers
def _sleeves(arm, k, w=1.0):
    """Varys's hands folded into his sleeves before his belly."""
    pel, fwd, right, up = _live(arm)
    for side, sd in (('L', -1), ('R', 1)):
        tgt = pel + (fwd * 0.2 + up * 0.17 + right * sd * 0.035) * k
        H0 = people._world(arm, arm.pose.bones[f'Bip01 {side} Hand']).translation.copy(); g = H0.lerp(tgt, w)
        people.ik2(arm, side, g, g - up * 0.25 * k + right * sd * 0.35 * k - fwd * 0.05 * k)
        people.palm_to(arm, side, -right * sd * 0.7 + up * 0.3, 0.8 * w)


def _littlefinger_acts(m, acts, full):
    """Littlefinger by the columns, close to Varys, talking low (his own cool talk), a glance up at the throne; idle:
    he listens while Varys speaks."""
    arm, base, frames = m['arm'], m['base'], m['frames']
    v = _head_of('varys'); king = _head_of('robert')
    talk = lambda f, t: _look(arm, v, 0.7)
    acts['talk'] = people.custom_act(arm, base, frames, 'littlefinger_talk', talk, _all(arm)); m['steps'] = {'talk': talk}
    if not full: return
    _clip_act(m, acts, 'listen', 'm_gestic_listen_neutral_01', lambda f, t: _look(arm, v, 0.7))
    _clip_act(m, acts, 'glance', 'm_idle_neutral_02', lambda f, t: _look(arm, king, 0.6))


def _varys_acts(m, acts, full):
    """Varys listening, his hands in his sleeves, his head inclined to Littlefinger; cued: he speaks in turn (his
    hands staying in his sleeves)."""
    arm, base, frames, k = m['arm'], m['base'], m['frames'], m['k']
    lf = _head_of('littlefinger')
    def listen(f, t): _sleeves(arm, k); _look(arm, lf, 0.75)
    acts['listen'] = people.custom_act(arm, base, frames, 'varys_listen', listen, _all(arm, fingers=True)); m['steps'] = {'listen': listen}
    if not full: return
    _clip_act(m, acts, 'talk', 'm_gestic_talk_relaxed_01', lambda f, t: (_sleeves(arm, k, 0.85), _look(arm, lf, 0.75)), fingers=True)


# ---------------------------------------------------------------- Lord Stark before the throne
def _ned_acts(m, acts, full):
    """Ned before the steps, standing straight, his eyes on the king; idle: listening."""
    arm, base, frames = m['arm'], m['base'], m['frames']
    king = _head_of('robert')
    stand = lambda f, t: _look(arm, king, 0.7)
    acts['stand'] = people.custom_act(arm, base, frames, 'ned_stand', stand, _all(arm)); m['steps'] = {'stand': stand}
    if not full: return
    _clip_act(m, acts, 'listen', 'm_gestic_listen_neutral_01', lambda f, t: _look(arm, king, 0.7))


# the way to the left doorway and the passage behind the throne wall (hall metres), round the candelabrum and the column
NED_OUT = [(-0.95, -2.35), (-2.3, -2.3), (-3.55, -1.65), (-4.05, -0.95), (-4.6, -0.3), (-5.25, 1.0), (-5.6, 2.6), (-5.6, 3.9), (-5.6, 4.8), (-5.6, 5.3)]
NED_BACK = [(-5.6, 5.3), (-5.6, 4.6), (-5.6, 3.6), (-5.4, 1.6), (-4.7, -0.15), (-4.0, -0.95), (-3.2, -1.7), (-2.0, -2.2), (-1.15, -2.2)]


def _kneel_scene(made, acts):
    """Ned's act (the room opens on it): he kneels before the throne, rises at the king's wave, speaks, goes out by the
    left doorway into the passage and comes back to his place. Cued with it: the king's wave, the queen's, the
    prince's and Ser Jaime's eyes following him."""
    FPS = people.FPS; N = made['ned']; na, nb, nfr, k = N['arm'], N['base'], N['frames'], N['k']
    cin, cinf, _ = people.retarget(na, 'm_crouch_in', action_name='ned_src_cin')
    cidle, cidlef, _ = people.retarget(na, 'm_crouch_idle', cycles=3, action_name='ned_src_cidle')
    cout, coutf, _ = people.retarget(na, 'm_crouch_out', action_name='ned_src_cout')
    talk, talkf, _ = people.retarget(na, 'm_gestic_talk_neutral_02', cycles=2, action_name='ned_src_talk')
    turn, turnf, _ = people.retarget(na, 'm_turn_left_180', action_name='ned_src_turn')
    walk, walkf, vs = people.retarget(na, 'm_walk_neutral_01', inplace=True, cycles=14, action_name='ned_src_walk')
    look, lookf, _ = people.retarget(na, 'm_idle_look_around_01', action_name='ned_src_look')
    (x, y), f0 = SPOTS['ned']; home = P(x, y); h_s = Vector((*f0, 0)).normalized()
    _h, p_s = people.heading(na, nb, nfr[0])
    def at_home(src, fr):
        hh, pp = people.heading(na, src, fr); return people.carry(pp, hh, home, h_s)
    dur = lambda fr: (fr[1] - fr[0]) / FPS
    r_out = people.path([home] + [P(*q) for q in NED_OUT]); r_back = people.path([P(*q) for q in NED_BACK] + [home])
    out_end = P(*NED_OUT[-1]); turn_back = people.carry(*people.heading(na, turn, turnf[0])[::-1], out_end, Vector((0, 1, 0)))
    away = _flat(P(*NED_OUT[0]) - home)
    segs = [dict(src=nb, f0=nfr[0], dur=1.5, at=Matrix.Identity(4)),                                         # 0 standing
            dict(src=cin, f0=cinf[0], dur=dur(cinf), at=at_home(cin, cinf[0]), blend=0.6),                   # 1 down on his knee
            dict(src=cidle, f0=cidlef[0], dur=3.6, at=at_home(cidle, cidlef[0]), blend=0.5),                 # 2 kneeling, head bowed
            dict(src=cout, f0=coutf[0], dur=dur(coutf), at=at_home(cout, coutf[0]), blend=0.5),              # 3 up at the king's word
            dict(src=talk, f0=talkf[0], dur=6.0, at=at_home(talk, talkf[0]), blend=0.6),                     # 4 he speaks
            dict(src=turn, f0=turnf[0], dur=dur(turnf), at=at_home(turn, turnf[0]), blend=0.5),              # 5 turns away
            dict(src=walk, f0=walkf[0], dur=r_out[1] / vs, at=people.walk_along(na, walk, walkf[0], vs, r_out), blend=0.7),   # 6 out
            dict(src=look, f0=lookf[0], dur=2.5, at=people.carry(*people.heading(na, look, lookf[0])[::-1], out_end, Vector((0, 1, 0))), blend=0.8),  # 7 in the passage
            dict(src=turn, f0=turnf[0], dur=dur(turnf), at=turn_back, blend=0.5),                            # 8 turns back
            dict(src=walk, f0=walkf[0] + 10, dur=r_back[1] / vs, at=people.walk_along(na, walk, walkf[0], vs, r_back), blend=0.6),   # 9 back
            dict(src=nb, f0=nfr[0], dur=2.0, at=Matrix.Identity(4), blend=1.2)]                              # 10 in his place
    tv = [0.0]
    for sg in segs: tv.append(tv[-1] + sg['dur'])
    T_end = tv[-1]; king = _head_of('robert')
    cine.log('ned kneels: ' + ', '.join(f'{i}:{t:.1f}' for i, t in enumerate(tv)) + f' (walks {vs / S:.2f} m/s true)')
    def kneel_leg(w):
        """The crouch made a knight's kneel: the right knee down on the floor, the shin back along it."""
        if w <= 0: return
        pel, fwd, right, up = _live(na)
        hip = people._world(na, na.pose.bones['Bip01 R Thigh']).translation.copy()
        ft = people._world(na, na.pose.bones['Bip01 R Foot']).translation.copy()
        tgt = Vector((hip.x, hip.y, home.z)) - fwd * 0.3 * k - right * 0.02 * k + up * 0.085 * k
        people.ik_leg(na, 'R', ft.lerp(tgt, w), hip + (fwd * 0.6 - up * 0.5) * k, keep_foot=False)
    def overlay(tt, i, lt):
        if i in (1, 2, 3):
            d = segs[i]['dur']
            kneel_leg(_smooth(lt / d) if i == 1 else 1.0 if i == 2 else 1 - _smooth(lt / (d * 0.7)))
        if i == 2:                                                                  # head bowed
            pel, fwd, right, up = _live(na); e = _smooth(lt / 0.8) * (1 - _smooth((lt - segs[2]['dur'] + 0.6) / 0.6))
            people.bend(na, 'Bip01 Neck', right, -0.25 * e); people.bend(na, 'Bip01 Head', right, -0.3 * e)
        elif i in (0, 4, 10): _look(na, king, 0.7)
    act = people.sequence(na, nb, 'ned_kneel', segs, overlay=overlay)
    for a in (cin, cidle, cout, talk, turn, walk, look): bpy.data.actions.remove(a)
    acts['ned']['kneel'] = act
    na['open_act'], na['open_at'] = 'kneel', 0.0
    heads = _samples(na, act)
    # the cued ones: as long as his act; their eyes follow him; the king waves him up as he kneels
    t_wave = tv[2] + 0.6
    def follow(who, step):
        m = made[who]; arm = m['arm']
        lb, lf, _ = _long_base(m, T_end + 1.0, 'cue')
        n = int(round(T_end * FPS))
        def st(f, t):
            i = min(int(round(t * FPS)), len(heads) - 1); step(t, heads[i])
        acts[who][IDLES_CUED[who]] = people.custom_act(arm, lb, (lf[0], lf[0] + n), f'{who}_{IDLES_CUED[who]}', st, _all(arm, fingers=True))
        bpy.data.actions.remove(lb)
    R_ = made['robert']
    follow('robert', lambda t, h: (_sit(R_['arm'], R_['drop']), _look(R_['arm'], h, 0.7), _wave(R_['arm'], t_wave, 3.2, R_['k'], t)))
    C = made['cersei']
    follow('cersei', lambda t, h: (_hold(C['arm'], 'R', C['k']), _look(C['arm'], h, 0.75)))
    Jo = made['joffrey']
    follow('joffrey', lambda t, h: _look(Jo['arm'], h, 0.7))
    Ja = made['jaime']
    follow('jaime', lambda t, h: (_hilt(Ja['arm'], Ja), _look(Ja['arm'], h, 0.65)))
    OPEN['ned'] = ('kneel', 0.0)


IDLES_CUED = {'robert': 'wave', 'cersei': 'watch', 'joffrey': 'watch', 'jaime': 'watch'}


# ---------------------------------------------------------------- bake and export
def bake(sc, objs, phantoms, seated, args):
    """The hall's light baked into atlases (the court out of it: they all move); then room.glb, the people and
    room.json."""
    os.makedirs(WEB, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    for c, arm, mesh in seated: mesh.hide_render = True
    export, atlases = stages.bake(objs, R.RH * S, OUT, int(args.get('size', 2048)), int(args.get('samples', 320)))
    for c, arm, mesh in seated: mesh.hide_render = False
    cine.export_glb(export, os.path.join(WEB, 'room.glb'))
    meta = stages.room_meta(R.RH * S, atlases); meta.update(_capture_meta())
    meta['people'] = _export_people(seated)
    stages.write_meta(WEB, meta)


def _export_people(seated):
    out = os.path.join(WEB, 'people'); os.makedirs(out, exist_ok=True); metas = []
    for c, arm, mesh in seated:
        people.export_person(arm, mesh, c['acts'], os.path.join(out, f"{c['who']}.glb"), roam=c.get('roam', ()))
        metas.append(person_meta(c))
    return metas


def _capture_meta():
    """How to light the court as the bake lit the hall (three.js: y up, z = -Blender y; module metres): the candles and
    the passages' torches as small bright spheres; the stag window and the left aisle's high windows (the sun's way in)
    as glowing panes."""
    bulbs = []
    for l in RIG['lights']:
        if l.type != 'LIGHT' or l.data.type != 'POINT': continue
        r = 0.012 if l.name.startswith('candle') else 0.05; e = l.data.energy
        bulbs.append({'x': round(l.location.x, 3), 'y': round(l.location.z, 3), 'z': round(-l.location.y, 3), 'r': r,
                      'L': round(e / (4 * math.pi * r ** 2) / 60, 2), 'color': [round(v, 3) for v in l.data.color]})
    z0 = R.WIN_Z * S; z1 = R.RH * S
    windows = [{'x': 0.0, 'y': round((z0 + z1) / 2, 3), 'z': round(-(R.YW2 - 0.1) * S, 3), 'w': round((R.WIN_W - 0.16) * S, 3), 'h': round(z1 - z0, 3), 'L': 2.2,
                'color': [1.0, 0.82, 0.62], 'ry': 0.0}]
    h0, h1 = R.HIGH_Z
    for a, b in R.HIGH_WINDOWS:
        windows.append({'x': round((R.LEFT - 0.3) * S, 3), 'y': round((h0 + h1) / 2 * S, 3), 'z': round(-(a + b) / 2 * S, 3), 'w': round((b - a) * S, 3),
                        'h': round((h1 - h0) * S, 3), 'L': 3.0, 'color': list(R.SUN), 'ry': round(math.pi / 2, 4)})
    at = [[round(v, 3) for v in (p.x, p.z, -p.y)] for p in (P(0, 2.2, 1.9), P(0, -2.2, 1.2), P(-4.0, -3.6, 1.2), P(3.5, -0.2, 1.2))]
    return {'capture': {'ceiling': [0.07, 0.055, 0.045], 'walls': [0.16, 0.11, 0.08], 'emitters': bulbs, 'windows': windows, 'at': at}}


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
    """Re-export only the people (their glTF files and their part of room.json); the baked hall stays as it is. Then a
    look at the court in the hall (Cycles)."""
    stages.update_meta(WEB, people=_export_people(seated), **_capture_meta())
    for c, arm, mesh in seated: people.pose_at(arm, c['acts'][c['work'][0]], int(c['acts'][c['work'][0]].frame_range[0]) + 60)
    for which in str(args.get('cams', 'close,front')).split(','):
        preview(sc, cams, which, int(args.get('samples', 64)), os.path.join(OUT, f'people_{which}.png'), size=(1200, 800))
