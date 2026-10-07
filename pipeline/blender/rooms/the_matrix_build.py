# The Matrix: assemble the hotel room, seat Morpheus and Neo, stand Trinity by the window, then preview, bake (the
# room's light, and the lightning on its own) and export.
import math, os, json
import bpy
from mathutils import Vector, Matrix
import cine, people, stages
from stages import camera
import rooms.the_matrix as R

ROOM = 'the-matrix'
OUT = os.path.join(cine.OUT, ROOM)
WEB = os.path.join(cine.ROOT, 'public', 'rooms', ROOM)
PEOPLE_TEX = os.path.join(cine.OUT, 'people')
ARGS = {}
RIG = {'lights': [], 'flash': []}
SEATED = []


def build(args):
    ARGS.clear(); ARGS.update(args)
    sc = cine.reset(int(args.get('samples', 256)))
    M = R.mats()
    static, phantom, crowd = cine.coll('static'), cine.coll('phantom'), cine.coll('people')
    R.walls(M, static, static, phantom)
    R.fireplace(M, static, static)
    bulbs = []
    for k, (wall, u, z) in enumerate(R.SCONCES):
        parts, b = R.sconce(f'sconce{k}', wall, u, z, M, static); bulbs += b
    for who, (x, y, facing) in R.CHAIRS.items(): R.chair(f'chair_{who}', x, y, facing, M, static)
    R.chair('chair_wall', -4.08, -2.75, math.pi / 2 - 0.12, M, static)   # another, pushed back against the wall
    R.dust_sheeted_settee(M, static)
    R.table(M, static); R.rug(M, static); R.debris(M, static)
    RIG['lights'], RIG['flash'] = R.lights(bulbs)
    for l in RIG['flash']: l.hide_render = True
    seated = cast(crowd, args); SEATED[:] = seated
    objs = [o for o in static.objects if o.type == 'MESH']
    cine.bake_ready(objs)
    for o in objs:   # procedural meshes get world-scale UVs; imported props and the cloth keep their own
        if not o.data.uv_layers: cine.world_uv(o, 1.0)
        elif 'UVMap' not in o.data.uv_layers: o.data.uv_layers[0].name = 'UVMap'
    for o in phantom.objects: cine.bake_ready([o]); cine.world_uv(o, 1.0); cine.phantom(o)
    cine.check_module(objs)
    # the web camera's views at room scale (the case view and the closer one), and a look at each person
    cams = {'case': camera('cam_case', (11.14, -18.16, 7.95), (-2.30, -1.49, 0.63), 32),
            'close': camera('cam_close', (5.0, -5.6, 3.4), (-0.2, 1.6, 0.9), 30),
            'film': camera('cam_film', (0.0, -2.6, 1.15), (0.0, 2.6, 0.95), 46),
            'morpheus': camera('cam_morpheus', (0.35, 0.9, 1.35), (-1.0, 2.05, 1.0), 36),
            'neo': camera('cam_neo', (-0.35, 0.9, 1.35), (1.0, 2.05, 1.0), 36),
            'trinity': camera('cam_trinity', (-2.0, 0.4, 1.6), (-3.5, 2.2, 1.35), 36),
            'offer': camera('cam_offer', (1.15, 1.45, 1.4), (-0.95, 2.05, 0.95), 30),
            'face': camera('cam_face', (-0.15, 1.45, 1.42), (-0.95, 2.0, 1.27), 24)}
    return sc, M, objs, list(phantom.objects), seated, cams


def preview(sc, cams, which, samples, path, size=(1440, 900)):
    """A Cycles render from one camera: the room's light, or with flash=1 the lightning alone; pose=who:act:frame,...
    poses people first (e.g. pose=morpheus:offer:150)."""
    flash = bool(ARGS.get('flash'))
    for spec in filter(None, str(ARGS.get('pose', '')).split(',')):
        who, act, f = spec.split(':')
        for c, arm, mesh in SEATED:
            if c['who'] == who and act in c['acts']: people.pose_at(arm, c['acts'][act], int(c['acts'][act].frame_range[0]) + int(f))
    _light(flash)
    stages.render(sc, cams[which], samples, path.replace('.png', '_flash.png') if flash else path, size, float(ARGS.get('exposure', 0.0)))


# ---------------------------------------------------------------- the cast
# Who is where and what they do. Morpheus and Neo sit facing each other; Trinity stands by the window, watching.
# Each seated person has one looping act (`work`, min/max seconds) and idles (weights) the web crossfades between.
CAST = [
    dict(who='morpheus', avatar='Male_Adult_12', shape='broad', scale=1.03, chair='morpheus', base='m_sit_chair_breathe_01',
         talk='m_gestic_talk_relaxed_01', work=('talk', 14, 30), glasses=True,
         idles={'offer': (None, 1.3), 'steeple': (None, 1.0), 'thoughtful': ('m_sit_chair_gestic_thoughtful', 0.6), 'relaxed': ('m_sit_chair_idle_relaxed_01', 0.6)},
         tex={'m007_head_color.tga': 'morpheus/m007_head_color.png', 'm007_body_color.tga': 'morpheus/m007_body_color.png'},
         rough={'body': 'morpheus/m007_body_rough.png'}),
    dict(who='neo', avatar='Business_Male_02', shape='lean', scale=1.04, chair='neo', base='m_sit_chair_breathe_01', work=('lean', 16, 34),
         idles={'face': ('m_sit_chair_idle_touch_face', 1.0), 'scratch': ('m_sit_chair_idle_scratch_head', 0.6), 'look': ('m_sit_chair_idle_look_around', 0.9),
                'nervous': ('m_sit_chair_idle_nervous_01', 0.8), 'waiting': ('m_sit_chair_idle_waiting_01', 0.6)},
         tex={'m008_body_color.tga': 'neo/m008_body_color.png'}),
    dict(who='trinity', avatar='Female_Adult_04', scale=1.0, stand=(-3.55, 2.25), look=(0.0, 2.0), base='f_idle_breathe_01', work=('stand', 10, 24),
         idles={'listen': ('f_gestic_listen_self-assured_01', 1.2), 'look': ('f_idle_look_around_01', 0.8), 'neutral': ('f_idle_neutral_02', 1.0),
                'roll': ('f_idle_roll_head_01', 0.5), 'waiting': ('f_idle_waiting_01', 0.7)},
         tex={'f004_head_color.tga': 'trinity/f004_head_color.png', 'f004_opacity_color.tga': 'trinity/f004_opacity_color.png', 'f004_body_color.tga': 'trinity/f004_body_color.png'},
         rough={'body': 'trinity/f004_body_rough.png'}),
]
SPINE = ('Bip01 Spine', 'Bip01 Spine1', 'Bip01 Spine2')
ARMS = tuple(f'Bip01 {s} {b}' for s in 'LR' for b in ('UpperArm', 'Forearm', 'Hand'))


def _rough_map(mesh, path):
    """A roughness map on the avatar's body material: glossy leather and patent, matte cloth and skin."""
    for slot in mesh.material_slots:
        m = slot.material
        if not m or 'head' in m.name.lower() or 'opacity' in m.name.lower(): continue
        nt = m.node_tree; t = nt.nodes.new('ShaderNodeTexImage'); t.image = cine.image(path, colour=False)
        nt.links.new(t.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Roughness'])


def _seat(c, arm, base, frames):
    """Slide a seated person so the clip's pelvis sits over the chair's seat; report how the heights agree."""
    x, y, facing = R.CHAIRS[c['chair']]
    people.pose_at(arm, base, frames[0])
    pel = people._world(arm, arm.pose.bones['Bip01 Pelvis']).translation
    want = Vector((x, y, 0)) + Matrix.Rotation(facing, 3, 'Z') @ Vector((0, -0.01, 0))
    arm.location.x += want.x - pel.x; arm.location.y += want.y - pel.y
    bpy.context.view_layer.update()
    cine.log(f"seat {c['who']}: pelvis {pel.z:.3f} m high (seat top {R.SEAT_TOP:.3f})")


def _offer(arm, T):
    """Leaning in, both hands held out over the knees, palms up: a pill in each (the pills are drawn on the web)."""
    def step(f, t):
        e = people.envelope(t, T, 1.8, 1.8)
        if e <= 0: return
        pel, fwd, right, up = people.body_frame(arm)
        for b, a in zip(SPINE, (0.07, 0.08, 0.06)): people.bend(arm, b, right, -a * e)
        pel = people._world(arm, arm.pose.bones['Bip01 Pelvis']).translation.copy()
        for s, sd in (('L', -1), ('R', 1)):
            H = people._world(arm, arm.pose.bones[f'Bip01 {s} Hand']).translation.copy()
            tgt = H.lerp(pel + fwd * 0.46 + up * 0.27 + right * sd * 0.16, e)
            people.ik2(arm, s, tgt, tgt + right * sd * 0.35 - up * 0.35 - fwd * 0.1)
            people.palm_to(arm, s, up, e)
    return step


def _steeple(arm, T):
    """Elbows on the arms of the chair, fingertips together before the chest: listening."""
    def step(f, t):
        e = people.envelope(t, T, 1.6, 1.6)
        if e <= 0: return
        pel, fwd, right, up = people.body_frame(arm)
        for s, sd in (('L', -1), ('R', 1)):
            H = people._world(arm, arm.pose.bones[f'Bip01 {s} Hand']).translation.copy()
            tgt = H.lerp(pel + fwd * 0.26 + up * 0.38 + right * sd * 0.035, e)
            people.ik2(arm, s, tgt, tgt + right * sd * 0.3 - up * 0.3 - fwd * 0.05)
            people.palm_to(arm, s, -right * sd, e)
    return step


def _lean(arm, T):
    """Neo, leaning forward, forearms on his thighs, hands clasped between his knees, looking up across at Morpheus.
    Every motion is constant or a whole number of cycles over the clip, so the act loops without a seam."""
    def step(f, t):
        pel, fwd, right, up = people.body_frame(arm)
        for b, a in zip(SPINE, (0.15, 0.15, 0.12)): people.bend(arm, b, right, -a)
        people.bend(arm, 'Bip01 Neck', right, 0.16)
        k = max(1, round(T / 7.0)); yaw = math.radians(3.0 * math.sin(2 * math.pi * k * t / T)); pitch = 0.2 + 0.03 * math.sin(2 * math.pi * 2 * k * t / T)
        people.bend(arm, 'Bip01 Head', right, pitch); people.bend(arm, 'Bip01 Head', up, yaw)
        pel = people._world(arm, arm.pose.bones['Bip01 Pelvis']).translation.copy()
        for s, sd in (('L', -1), ('R', 1)):
            tgt = pel + fwd * 0.4 + up * 0.03 + right * sd * 0.05
            people.ik2(arm, s, tgt, tgt + right * sd * 0.35 - fwd * 0.25 + up * 0.05)
            people.palm_to(arm, s, -right * sd, 0.8)
    return step


def cast(col, args):
    """Load, dress, shape and place the three, and bake their acts (cached: retargets and IK take minutes)."""
    full = bool(args.get('full'))
    spec = {'cast': CAST, 'chairs': R.CHAIRS, 'seat': R.SEAT_TOP, 'full': full, 'v': 8}
    seated = stages.cast_cache(OUT, CAST, spec, lambda: _make_cast(col, full), col)
    for c, arm, mesh in seated: people.pose_at(arm, c['acts'][c['work'][0]], 30)
    return seated


def _make_cast(col, full):
    seated = []
    lens = cine.material('lens', (0.01, 0.012, 0.012), rough=0.04, metal=0.9, coat=1.0)
    for c in CAST:
        arm, mesh = people.load_avatar(c['avatar'], textures={k: os.path.join(PEOPLE_TEX, v) for k, v in c['tex'].items()}, collection=col)
        mesh['person'] = c['who']; arm['person'] = c['who']
        if c.get('shape'): people.reshape(arm, mesh, c['shape'])
        if c.get('scale', 1.0) != 1.0:
            arm.scale = arm.scale * c['scale']; arm.location = (arm.location.x, arm.location.y, arm.location.z * c['scale'])
        bpy.context.view_layer.update()
        if c.get('glasses'): people.add_glasses(arm, mesh, mat=lens)
        for k, p in c.get('rough', {}).items(): _rough_map(mesh, os.path.join(PEOPLE_TEX, p))
        if c.get('chair'):
            x, y, facing = R.CHAIRS[c['chair']]; want = Matrix.Rotation(facing, 3, 'Z') @ Vector((0, -1, 0))   # a chair's front is its local -y
        else:
            (x, y), (lx, ly) = c['stand'], c['look']; want = Vector((lx - x, ly - y, 0))
        people.face(arm, want); arm.location = (x, y, arm.location.z)
        bpy.context.view_layer.update()
        arm['fwd'] = list(want.normalized())           # the body's forward, for the authored acts
        base, frames, _ = people.retarget(arm, c['base'], cycles=2, action_name=f"{c['who']}_base")
        if c.get('chair'): _seat(c, arm, base, frames)
        T = (frames[1] - frames[0]) / people.FPS
        acts = {}
        if c['who'] == 'morpheus':
            talk, tf, _ = people.retarget(arm, c['talk'], action_name='morpheus_talk_src')
            k = max(1, round((frames[1] - frames[0]) / (tf[1] - tf[0])))
            if k > 1: bpy.data.actions.remove(talk); talk = people.retarget(arm, c['talk'], cycles=k, action_name='morpheus_talk_src')[0]
            acts['talk'] = people.layer(base, talk, name='morpheus_talk'); bpy.data.actions.remove(talk)
            if full:
                n = int(10.5 * people.FPS); acts['offer'] = people.custom_act(arm, base, (frames[0], frames[0] + n), 'morpheus_offer', _offer(arm, n / people.FPS), SPINE + ARMS)
                n = int(12 * people.FPS); acts['steeple'] = people.custom_act(arm, base, (frames[0], frames[0] + n), 'morpheus_steeple', _steeple(arm, n / people.FPS), ARMS)
        elif c['who'] == 'neo':
            acts['lean'] = people.custom_act(arm, base, frames, 'neo_lean', _lean(arm, T), SPINE + ARMS + ('Bip01 Neck', 'Bip01 Head'))
        else:
            acts['stand'] = base; base = None
        if full:
            for k, (clip, _w) in c['idles'].items():   # each starts where the looping act starts
                if clip: acts[k] = people.anchor(arm, people.retarget(arm, clip, action_name=f"{c['who']}_{k}")[0], acts[c['work'][0]])
        if base: bpy.data.actions.remove(base)
        for a in acts.values(): people.freeze(a)
        c['acts'] = acts
        people.pose_at(arm, acts[c['work'][0]], 30)
        seated.append((c, arm, mesh))
    return seated


# ---------------------------------------------------------------- bake and export
def _light(flash):
    """The room's own light, or the lightning alone (the sconce shades dark while it flashes)."""
    for l in RIG['lights']: l.hide_render = flash
    for l in RIG['flash']: l.hide_render = not flash
    for m in bpy.data.materials:
        if not m.node_tree or 'Principled BSDF' not in m.node_tree.nodes: continue
        e = m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
        if flash and e.default_value > 0: m['emit'] = e.default_value; e.default_value = 0.0
        elif not flash and 'emit' in m: e.default_value = m['emit']


def bake(sc, objs, phantoms, seated, args):
    """The room's light and the lightning's, baked into atlases; then room.glb, the people and room.json."""
    os.makedirs(WEB, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    export, atlases = stages.bake(objs, R.H, OUT, int(args.get('size', 2048)), int(args.get('samples', 320)),
                                  passes={'': (lambda on: _light(False), 1.0), 'flash': (lambda on: _light(on), 0.5)})
    cine.export_glb(export, os.path.join(WEB, 'room.glb'))
    meta = stages.room_meta(R.H, atlases); meta.update(_capture_meta())
    meta['people'] = stages.export_people(seated, WEB, person_meta)
    stages.write_meta(WEB, meta)


def _capture_meta():
    """What the web needs to light the people as the bake lit the room: the ceiling and walls the cut-away hides, the
    bulbs as small bright spheres (three.js coordinates: y up, z = -Blender y), and the lightning's direction."""
    bulbs = [{'x': round(l.location.x, 3), 'y': round(l.location.z, 3), 'z': round(-l.location.y, 3), 'r': 0.03,
              'L': round(l.data.energy / (4 * math.pi * 0.03 ** 2) / 60, 2), 'color': list(R.WARM)} for l in RIG['lights'] if l.data.type == 'POINT']
    windows = [{'x': -R.W / 2 + 0.06, 'y': (R.WIN_Z[0] + R.WIN_Z[1]) / 2, 'z': -c, 'w': R.WIN_W, 'h': R.WIN_Z[1] - R.WIN_Z[0], 'L': 0.5, 'color': list(R.NIGHT)} for c in R.WINDOWS]
    return {'capture': {'ceiling': [0.11, 0.105, 0.08], 'walls': [0.22, 0.22, 0.16], 'emitters': bulbs, 'windows': windows, 'at': [0.0, 1.2, -R.TABLE[1]]},
            'live': {'flash': {'from': [-1.0, 0.45, 0.0], 'color': list(R.FLASH)}, 'pills': {'who': 'morpheus', 'act': 'offer'}}}


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
    for which in str(args.get('cams', 'morpheus,neo,trinity')).split(','):
        preview(sc, cams, which, int(args.get('samples', 64)), os.path.join(OUT, f'people_{which}.png'), size=(900, 900))
