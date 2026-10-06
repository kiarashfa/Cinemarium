# Severance: assemble the room, seat the cast, then preview, bake and export.
import math, os, json, time
import bpy
from mathutils import Vector, Matrix
import cine, people
from cine import box, cyl
import rooms.severance as R
import rooms.severance_island as I

OUT = os.path.join(cine.OUT, 'severance')
PEOPLE_TEX = os.path.join(cine.OUT, 'people')

# who sits where (desk q of the pinwheel), with which body, clip and costume
CAST = [
    dict(q=0, who='dylan', avatar='Business_Male_05', clip='m_sit_table_idle_neutral_01', tex={'m016_head_color.tga': 'dylan/m016_head_color.png', 'm016_body_color.tga': 'dylan/m016_body_color.png'}),
    dict(q=1, who='mark', avatar='Business_Male_06', clip='m_sit_table_breathe_01', tex={'m025_body_color.tga': 'mark/m025_body_color.png'}),
    dict(q=2, who='irving', avatar='Male_Adult_03', clip='m_sit_table_gestic_thoughtful', tex={'m004_body_color.tga': 'irving/m004_body_color.png'}),
    dict(q=3, who='helly', avatar='Female_Adult_15', clip='f_sit_table_idle_neutral_01', tex={'f018_head_color.tga': 'helly/f018_head_color.png', 'f018_opacity_color.tga': 'helly/f018_opacity_color.png', 'f018_body_color.tga': 'helly/f018_body_color.png'}),
]


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
    import hashlib
    spec = json.dumps({'cast': [{k: v for k, v in c.items() if k != 'action'} for c in CAST], 'island': list(I.ISLAND), 'pelvis': list(I.PELVIS),
                       'keys': list(I.KEYS), 'ball': list(I.BALL), 'quick': quick, 'v': 3}, sort_keys=True)
    path = os.path.join(OUT, f"cast_{hashlib.md5(spec.encode()).hexdigest()[:10]}.blend")
    if os.path.exists(path):
        with bpy.data.libraries.load(path, link=False) as (src, dst): dst.objects = list(src.objects)
        seated = []
        for c in CAST:
            arm = next(o for o in dst.objects if o.type == 'ARMATURE' and o.get('person') == c['who'])
            mesh = next(o for o in dst.objects if o.type == 'MESH' and o.get('person') == c['who'])
            for o in (arm, mesh): col.objects.link(o)
            c['action'] = arm['action']; people.pose_at(arm, bpy.data.actions[c['action']], 30)
            seated.append((c, arm, mesh))
        cine.log('cast from cache', os.path.basename(path))
        return seated
    seated = _cast(col, quick)
    keep = set()
    for c, arm, mesh in seated: arm['action'] = c['action']; keep |= {arm, mesh}
    os.makedirs(OUT, exist_ok=True)
    bpy.data.libraries.write(path, keep, fake_user=True)
    cine.log('cast cached', os.path.basename(path))
    return seated


def _cast(col, quick):
    seated = []
    for c in CAST:
        arm, mesh = people.load_avatar(c['avatar'], textures={k: os.path.join(PEOPLE_TEX, v) for k, v in c['tex'].items()}, collection=col)
        n = 60 if quick else 300
        base = people.retarget(arm, c['clip'], frames=(1, n), action_name=f"{c['who']}_base")
        F = I.frame_q(c['q']); p = F @ I.PELVIS
        arm.location = (p.x, p.y, arm.location.z)
        arm.rotation_euler.z = -math.pi / 2 + math.pi + c['q'] * math.pi / 2
        bpy.context.view_layer.update()
        facing = (F.to_3x3() @ Vector((0, 1, 0))).normalized()
        act = people.desk_work(arm, base, F @ I.KEYS, F @ I.BALL, (1, n), seed=c['q'] + 3, name=f"{c['who']}_work", facing=facing)
        people.pose_at(arm, act, 30)
        c['action'] = act.name
        mesh['person'] = c['who']; arm['person'] = c['who']
        seated.append((c, arm, mesh))
    return seated


def camera(name, loc, look, fov=32):
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name)); bpy.context.scene.collection.objects.link(cam)
    cam.location = loc; cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.sensor_fit = 'VERTICAL'; cam.data.angle = math.radians(fov); cam.data.clip_end = 200
    return cam


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
    # the web camera's view, at room scale (the case shot from the one-at-a-time layout, and a closer one)
    cams = {'case': camera('cam_case', (11.14, -18.16, 7.95), (-2.30, -1.49, 0.63), 32),
            'close': camera('cam_close', (5.6, -6.2, 3.7), (0.2, 0.35, 0.75), 30),
            'dylan': camera('cam_dylan', (1.75, -1.75, 1.75), (0.95, -0.25, 0.85), 34),
            'mark': camera('cam_mark', (-0.35, 0.55, 1.75), (1.05, 1.4, 0.9), 34)}
    return sc, M, objs, list(phantom.objects), seated, cams


def preview(sc, cams, which, samples, path, size=(1440, 900)):
    sc.camera = cams[which]; sc.render.resolution_x, sc.render.resolution_y = size; sc.render.resolution_percentage = 100
    sc.cycles.samples = samples; sc.cycles.use_denoising = True; sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'None'; sc.view_settings.exposure = 0.0
    sc.render.image_settings.file_format = 'PNG'; sc.render.filepath = path
    t0 = time.time(); bpy.ops.render.render(write_still=True); cine.log(f'preview {which} {time.time() - t0:.0f}s -> {path}')


WEB = os.path.join(cine.ROOT, 'public', 'rooms', 'severance')


def bake(sc, objs, phantoms, seated, args):
    size, samples = int(args.get('size', 2048)), int(args.get('samples', 384))
    os.makedirs(WEB, exist_ok=True)
    screens = [o for o in objs if o.get('role') == 'screen']
    others = [o for o in objs if not o.get('lm') and o not in screens]
    lit, exterior = cine.cull_and_split([o for o in objs if o.get('lm') and o not in screens], R.H)
    objs = lit + exterior + screens + others
    groups = {g: [o for o in lit if o.get('lm') == g] for g in ('arch', 'furn')}
    atlases = {}
    for g, members in groups.items():
        cine.lightmap_uvs(members, margin=0.003 if g == 'arch' else 0.004)
        img = cine.bake_atlas(members, g, size, samples)
        dn = cine.denoise(img)
        import shutil
        path = os.path.join(OUT, f'lm_{g}.exr'); shutil.copy(bpy.path.abspath(dn.filepath), path); atlases[g] = path   # masters stay out of the site
        cine.log('saved', path, f'{os.path.getsize(path) / 1e6:.1f} MB')
    for m in bpy.data.materials:   # the bake targets must not reach the export
        if m.node_tree and '__bake' in m.node_tree.nodes: m.node_tree.nodes.remove(m.node_tree.nodes['__bake'])
    for o in objs:
        if o in screens: o['lm'] = ''
    cine.export_glb(objs, os.path.join(WEB, 'room.glb'))
    export_people(seated)
    meta = {
        'module': cine.MODULE, 'wallHeight': R.H,
        'lightmaps': {g: os.path.basename(p) for g, p in atlases.items()},
        # Cycles' diffuse light pass is E/pi; three.js multiplies the light map by albedo/pi, so scale by pi
        'lightMapIntensity': math.pi,
        'troffers': [{'x': x, 'y': R.H - 0.005, 'z': -y, 'w': R.TROFFER_SIZE[0], 'd': R.TROFFER_SIZE[1], 'watts': R.TROFFER_W} for x, y in R.TROFFERS],
        'people': [{'who': c['who'], 'file': f"{c['who']}.glb", 'clip': c['action']} for c, arm, mesh in seated] + [{'who': 'milchick', 'file': 'milchick.glb', 'clip': 'milchick_walk', 'walk': True}],
        'walk': [[-3.2, 2.9], [-3.2, -2.6], [3.4, -2.6], [3.4, 2.9]],
    }
    with open(os.path.join(WEB, 'room.json'), 'w') as f: json.dump(meta, f, indent=1)
    cine.log('wrote room.json')


def _shrink_images(mesh, size=1024):
    for slot in mesh.material_slots:
        for n in slot.material.node_tree.nodes:
            if n.type == 'TEX_IMAGE' and n.image and n.image.size[0] > size: n.image.scale(size, size)


def export_people(seated):
    """One glTF per person: body, rig and its looping action, textures at 1024 px (a figure is 0.29 m at 1:6)."""
    out = os.path.join(WEB, 'people'); os.makedirs(out, exist_ok=True)
    crowd = [(c['who'], arm, mesh) for c, arm, mesh in seated]
    # Milchick does his rounds: Business_Male_05 in its own check suit, walking in place (the web moves him)
    arm, mesh = people.load_avatar('Business_Male_05', collection=bpy.data.collections['people'])
    walk = people.retarget(arm, 'm_walk_cool_01', inplace=True, action_name='milchick_walk')
    arm.location = (0, 0, arm.location.z); crowd.append(('milchick', arm, mesh))
    for who, arm, mesh in crowd:
        _shrink_images(mesh)
        keep = arm.matrix_world.copy()   # seated people export where they sit; the walker at the origin, facing +z in three.js
        bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); mesh.select_set(True)
        bpy.context.view_layer.objects.active = arm
        path = os.path.join(out, f'{who}.glb')
        bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_animations=True, export_animation_mode='ACTIVE_ACTIONS',
                                  export_force_sampling=True, export_frame_step=2, export_optimize_animation_size=True, export_def_bones=True,
                                  export_leaf_bone=False, export_image_format='WEBP', export_image_quality=85, export_extras=True, export_yup=True)
        arm.matrix_world = keep
        cine.log('person', who, f'{os.path.getsize(path) / 1e6:.1f} MB')
