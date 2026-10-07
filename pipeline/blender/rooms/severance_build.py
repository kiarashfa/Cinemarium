# Severance: assemble the room, seat the cast, then preview, bake and export.
import math, os, json
import bpy
from mathutils import Vector, Matrix
import cine, people, stages
from cine import box, cyl
from stages import camera
import rooms.severance as R
import rooms.severance_island as I

OUT = os.path.join(cine.OUT, 'severance')
PEOPLE_TEX = os.path.join(cine.OUT, 'people')

# Who sits where (desk q of the pinwheel): body, build, costume, and what they do. Each seated refiner works
# (a breathing base with typing and trackball layered on, two cycles long) and now and then breaks off into one
# of their idles; the web picks the next act at random, by weight, and crossfades. `work` is (min, max) seconds.
CAST = [
    dict(q=0, who='dylan', avatar='Business_Male_05', shape='heavy', base='m_sit_table_breathe_01', work=(10, 26),
         idles={'yawn': ('m_sit_table_idle_yawn', 1.0), 'scratch': ('m_sit_table_idle_scratch_head', 1.0),
                'shrug': ('m_sit_table_gestic_shrug_01', 0.7), 'look': ('m_sit_table_idle_look_around', 1.0)},
         tex={'m016_head_color.tga': 'dylan/m016_head_color.png', 'm016_body_color.tga': 'dylan/m016_body_color.png'}),
    dict(q=1, who='mark', avatar='Business_Male_01', shape='lean', base='m_sit_table_breathe_01', work=(18, 45),
         idles={'look': ('m_sit_table_idle_look_around', 1.2), 'roll': ('m_sit_table_idle_roll_head', 0.8),
                'face': ('m_sit_table_idle_touch_face', 1.0)},
         tex={'m005_body_color.tga': 'mark/m005_body_color.png'}),
    dict(q=2, who='irving', avatar='Male_Adult_03', hair=True, base='m_sit_table_breathe_01', work=(22, 55),
         idles={'think': ('m_sit_table_gestic_thoughtful', 1.0), 'dust': ('m_sit_table_idle_dust', 1.0),
                'look': ('m_sit_table_idle_look_around', 0.6)},
         tex={'m004_head_color.tga': 'irving/m004_head_color.png', 'm004_opacity_color.tga': 'irving/m004_opacity_color.png', 'm004_body_color.tga': 'irving/m004_body_color.png'}),
    dict(q=3, who='helly', avatar='Female_Adult_15', base='f_sit_table_breathe_01', work=(9, 24),
         idles={'hair': ('f_sit_table_idle_touch_hair', 1.2), 'look': ('f_sit_table_idle_look_around', 1.0),
                'stretch': ('f_sit_table_idle_stretch_arms', 0.6), 'face': ('f_sit_table_idle_touch_face', 0.8)},
         tex={'f018_head_color.tga': 'helly/f018_head_color.png', 'f018_opacity_color.tga': 'helly/f018_opacity_color.png', 'f018_body_color.tga': 'helly/f018_body_color.png'}),
]
# Milchick does his rounds: walks the floor, stops behind each refiner and watches a while, walks on
WALKER = dict(who='milchick', avatar='Male_Adult_12', shape='athletic', scale=1.04, walk='m_walk_cool_01',
              idles={'stand': ('m_idle_neutral_01', 1.0), 'look': ('m_idle_look_around_01', 0.8), 'listen': ('m_gestic_listen_neutral_01', 1.0)},
              tex={'m007_head_color.tga': 'milchick/m007_head_color.png', 'm007_body_color.tga': 'milchick/m007_body_color.png'})
# his route (Blender x, y), clear of the chairs; at each stop he faces the refiner whose desk it is
ROUTE = [((1.0, -1.95), 0), ((3.3, -2.5), None), ((2.65, 1.38), 1), ((3.0, 2.85), None), ((-0.68, 2.85), 2), ((-3.1, 2.8), None),
         ((-2.35, -0.28), 3), ((-3.1, -2.5), None)]


def props(M, col):
    """The little things on the desks and walls (Poly Haven, CC0), placed in each desk's frame."""
    ph = lambda n: os.path.join(cine.CACHE, 'polyhaven', n, f'{n}_1k.gltf')
    out = []
    # the wall clock on the back wall, its hands separate so the web can run them
    root, ms = cine.import_gltf(ph('wall_clock'), loc=(-0.9, R.D / 2 - R.T, 1.98), collection=col, lm='furn')
    for m in ms:
        if 'hand' in m.name: m['role'] = 'clock_' + m.name.split('_')[-2][0]   # clock_h / clock_m / clock_s
    out += ms
    root, ms = cine.import_gltf(ph('fire_alarm'), loc=(2.2, R.D / 2 - R.T, 1.25), collection=col, lm='furn'); out += ms
    # per desk: notepads, a pen, a mug; Irving's binder and stapler; Dylan's finger traps
    pads = cine.import_gltf(ph('office_notepads'), collection=col, lm='furn')[1]
    pick = {m.name: m for m in pads}
    stat = {m.name: m for m in cine.import_gltf(ph('stationery_supplies'), collection=col, lm='furn')[1]}
    staple = cine.import_gltf(ph('vintage_stapler'), collection=col, lm='furn')[1]
    binder = {m.name: m for m in cine.import_gltf(ph('binder_notebook'), collection=col, lm='furn')[1]}
    used = set()

    def put(ob, F, at, rz=0.0, rx=0.0):
        # move the prop's own footprint centre to the origin, keep its orientation, then into the desk frame
        bpy.context.view_layer.update(); W0 = ob.matrix_world.copy()
        pts = [W0 @ Vector(c) for c in ob.bound_box]; c = Vector((sum(p.x for p in pts) / 8, sum(p.y for p in pts) / 8, min(p.z for p in pts)))
        ob.parent = None
        ob.matrix_world = F @ Matrix.Translation(at) @ Matrix.Rotation(rz, 4, 'Z') @ Matrix.Rotation(rx, 4, 'X') @ Matrix.Translation(-c) @ W0
        used.add(ob.name); out.append(ob)

    def dup(ob):
        c = ob.copy(); c.data = ob.data; [cl.objects.link(c) for cl in ob.users_collection]; return c
    top = 0.745
    for q in range(4):
        F = I.frame_q(q)
        put(dup(pick['office_notepads_note_stack']), F, (0.33, -0.55, top), 0.25 - q * 0.3)
        put(dup(stat['stationery_supplies_pen_blue']), F, (0.42, -0.72, top + 0.006), 1.3 + q * 0.4, math.pi / 2)
        out += I.mug(M, f'mug{q}', F @ Matrix.Translation((1.32 - 0.06 * q, -0.32, top)), col, coffee=q != 2)
    put(dup(binder['binder_notebook_closed']), I.frame_q(2), (1.25, -0.48, top + 0.002), 0.08)
    put(dup(staple[0]), I.frame_q(2), (0.36, -0.36, top + 0.013), -0.4)
    for k, s in enumerate(staple[1:]): put(dup(s), I.frame_q(2), (0.36, -0.36, top + 0.013), -0.4)
    put(dup(pick['office_notepads_sticky_stack']), I.frame_q(1), (1.2, -0.62, top), 0.3)
    traps = [cine.material(f'trap{c}', col_, rough=0.6) for c, col_ in enumerate([(0.55, 0.12, 0.08), (0.08, 0.30, 0.55), (0.62, 0.48, 0.10)])]
    for k in range(3):
        out.append(cyl(f'fingertrap{k}', 0.007, 0.11, (0, 0, 0), traps[k], rot=(0, math.pi / 2, 0), seg=12, collection=col, lm='furn'))
        out[-1].matrix_world = I.frame_q(0) @ Matrix.Translation((0.25 + 0.025 * k, -0.40 + 0.03 * k, top + 0.008)) @ Matrix.Rotation(0.3 * k - 0.2, 4, 'Z') @ Matrix.Rotation(math.pi / 2, 4, 'Y')
    # papers under the notepads
    for q in (0, 1, 3):
        out.append(box(f'papers{q}', (0.21, 0.297, 0.003), (0, 0, 0), M['paper'], bev=0.0005, collection=col, lm='furn'))
        out[-1].matrix_world = I.frame_q(q) @ Matrix.Translation((0.55, -0.45, top + 0.0015)) @ Matrix.Rotation(-0.15 + 0.1 * q, 4, 'Z')
    for m in pads + list(stat.values()) + staple + list(binder.values()):
        if m.name not in used and m.users: bpy.data.objects.remove(m, do_unlink=True)
    bpy.context.view_layer.update()
    for o in [o for o in bpy.data.objects if o.type == 'EMPTY']:
        for ch in o.children:   # keep the children where they are when their helper empty goes
            mw = ch.matrix_world.copy(); ch.parent = None; ch.matrix_world = mw
        bpy.data.objects.remove(o, do_unlink=True)
    return [o for o in out if o.name in bpy.data.objects]


def cast(col, quick=True):
    """Seat the four refiners (cached: retargeting and the typing IK take minutes, the cache seconds)."""
    spec = {'cast': [{k: v for k, v in c.items() if k != 'acts'} for c in CAST], 'island': list(I.ISLAND), 'pelvis': list(I.PELVIS),
            'keys': list(I.KEYS), 'ball': list(I.BALL), 'quick': quick, 'v': 7}
    seated = stages.cast_cache(OUT, CAST, spec, lambda: _cast(col, quick), col)
    for c, arm, mesh in seated: people.pose_at(arm, c['acts']['work'], 30)
    return seated


def _cast(col, quick):
    seated = []
    for c in CAST:
        arm, mesh = people.load_avatar(c['avatar'], textures={k: os.path.join(PEOPLE_TEX, v) for k, v in c['tex'].items()}, collection=col)
        mesh['person'] = c['who']; arm['person'] = c['who']
        if c.get('shape'): people.reshape(arm, mesh, c['shape'])
        if c.get('hair'): people.hair_volume(arm, mesh)
        base, frames, _ = people.retarget(arm, c['base'], cycles=2, action_name=f"{c['who']}_base", limit=60 if quick else None)
        F = I.frame_q(c['q']); p = F @ I.PELVIS
        arm.location = (p.x, p.y, arm.location.z)
        arm.rotation_euler.z = -math.pi / 2 + math.pi + c['q'] * math.pi / 2
        bpy.context.view_layer.update()
        facing = (F.to_3x3() @ Vector((0, 1, 0))).normalized()
        work = people.desk_work(arm, base, F @ I.KEYS, F @ I.BALL, frames, seed=c['q'] + 3, name=f"{c['who']}_work", facing=facing)
        people.freeze(work)
        bpy.data.actions.remove(base)
        c['acts'] = {'work': work}
        if not quick:
            for k, (clip, _w) in c['idles'].items():
                c['acts'][k] = people.retarget(arm, clip, action_name=f"{c['who']}_{k}")[0]
        people.pose_at(arm, work, 30)
        seated.append((c, arm, mesh))
    return seated


def build(args):
    sc = cine.reset(int(args.get('samples', 256)))
    M = R.mats()
    static, phantom, crowd = cine.coll('static'), cine.coll('phantom'), cine.coll('people')
    R.walls(M, static, phantom)
    R.lights()
    I.island(M, static)
    props(M, static)
    seated = cast(crowd, quick=not args.get('full'))
    objs = [o for o in static.objects if o.type == 'MESH']
    cine.bake_ready(objs)
    for o in objs:   # procedural meshes get world-scale UVs; imported props and the screens keep their own
        if not o.data.uv_layers: cine.world_uv(o, 1.0)
        elif 'UVMap' not in o.data.uv_layers: o.data.uv_layers[0].name = 'UVMap'
    for o in phantom.objects: cine.bake_ready([o]); cine.world_uv(o, 1.0); cine.phantom(o)
    cine.check_module(objs)
    # the web camera's view, at room scale (the case view, and the closer one)
    cams = {'case': camera('cam_case', (11.14, -18.16, 7.95), (-2.30, -1.49, 0.63), 32),
            'close': camera('cam_close', (5.6, -6.2, 3.7), (0.2, 0.35, 0.75), 30),
            'dylan': camera('cam_dylan', (1.95, 0.3, 1.5), (0.98, -0.45, 0.92), 36),
            'mark': camera('cam_mark', (-0.35, 0.55, 1.75), (1.05, 1.4, 0.9), 34),
            'irving': camera('cam_irving', (-1.85, 0.75, 1.55), (-0.7, 1.55, 0.95), 34),
            'helly': camera('cam_helly', (-1.6, -1.35, 1.55), (-0.88, -0.3, 0.95), 34),
            'milchick': camera('cam_milchick', (1.75, -0.95, 1.72), (1.0, -1.95, 1.4), 34)}
    return sc, M, objs, list(phantom.objects), seated, cams


def preview(sc, cams, which, samples, path, size=(1440, 900)):
    stages.render(sc, cams[which], samples, path, size)


WEB = os.path.join(cine.ROOT, 'public', 'rooms', 'severance')


def bake(sc, objs, phantoms, seated, args):
    os.makedirs(WEB, exist_ok=True)
    export, atlases = stages.bake(objs, R.H, OUT, int(args.get('size', 2048)), int(args.get('samples', 384)))
    cine.export_glb(export, os.path.join(WEB, 'room.glb'))
    walker, _ = export_people(seated)
    meta = stages.room_meta(R.H, atlases)
    meta['troffers'] = [{'x': x, 'y': R.H - 0.005, 'z': -y, 'w': R.TROFFER_SIZE[0], 'd': R.TROFFER_SIZE[1], 'watts': R.TROFFER_W} for x, y in R.TROFFERS]
    meta['people'] = [person_meta(c) for c, arm, mesh in seated] + [walker]
    stages.write_meta(WEB, meta)


def person_meta(c):
    """What the web needs to run a seated refiner: the acts in their file and how often each comes up."""
    acts = [{'name': 'work', 'loop': True, 'min': c['work'][0], 'max': c['work'][1]}]
    acts += [{'name': k, 'w': w} for k, (clip, w) in c['idles'].items()]
    return {'who': c['who'], 'file': f"{c['who']}.glb", 'acts': acts}


def export_people(seated):
    """One glTF per person (body, rig, every act); the seated export where they sit. Returns the walker's meta."""
    out = os.path.join(WEB, 'people'); os.makedirs(out, exist_ok=True)
    for c, arm, mesh in seated:
        people.export_person(arm, mesh, c['acts'], os.path.join(out, f"{c['who']}.glb"))
    w = WALKER
    arm, mesh = people.load_avatar(w['avatar'], textures={k: os.path.join(PEOPLE_TEX, v) for k, v in w['tex'].items()}, collection=bpy.data.collections['people'])
    mesh['person'] = w['who']; arm['person'] = w['who']
    people.reshape(arm, mesh, w['shape'])
    arm.scale = arm.scale * w['scale']; arm.location = (0, 0, arm.location.z * w['scale'])
    bpy.context.view_layer.update()
    walk, _, speed = people.retarget(arm, w['walk'], inplace=True, action_name=f"{w['who']}_walk")
    acts = {'walk': walk}
    for k, (clip, _w) in w['idles'].items(): acts[k] = people.retarget(arm, clip, action_name=f"{w['who']}_{k}")[0]
    for a in acts.values(): people.freeze(a)
    people.export_person(arm, mesh, acts, os.path.join(out, f"{w['who']}.glb"))   # at the origin, facing +z in three.js
    route = []
    for (x, y), q in ROUTE:
        stop = None
        if q is not None:
            p = I.frame_q(q) @ I.PELVIS
            stop = {'face': [round(p.x, 3), round(p.y, 3)], 'dwell': [7, 15]}
        route.append({'at': [x, y], 'stop': stop})
    return {'who': w['who'], 'file': f"{w['who']}.glb", 'walker': True, 'speed': round(speed, 3),
            'acts': [{'name': 'walk', 'loop': True}] + [{'name': k, 'w': wt} for k, (clip, wt) in w['idles'].items()], 'route': route}, (arm, acts)


def people_stage(sc, cams, seated, args):
    """Re-export only the people (their glTF files and their part of room.json); the baked room stays as it is.
    Then a look at each of them in the room (Cycles), Milchick at his first stop."""
    walker, (arm, acts) = export_people(seated)
    stages.update_meta(WEB, people=[person_meta(c) for c, a, m in seated] + [walker])
    (x, y), q = ROUTE[0]
    arm.location = (x, y, arm.location.z); arm.rotation_euler.z += math.pi   # he faces -y as imported: turn him to the refiner
    people.pose_at(arm, acts['stand'], 40)
    for c, a, m in seated: people.pose_at(a, c['acts']['work'], 200)
    for which in str(args.get('cams', 'dylan,mark,irving,helly,milchick')).split(','):
        preview(sc, cams, which, int(args.get('samples', 96)), os.path.join(OUT, f'people_{which}.png'), size=(900, 900))
