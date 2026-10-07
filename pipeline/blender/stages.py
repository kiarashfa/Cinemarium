# The stages every room's build shares (build.py calls the room's own build(), preview(), bake() and people_stage(),
# which lean on these): cameras at room scale, Cycles previews, the cast cache, the light bake (one pass, or several:
# a room's own light and a storm's), and the exports: room.glb, one glTF per person, room.json.
import os, json, math, time, hashlib, shutil
import bpy
from mathutils import Vector
import cine, people


def camera(name, loc, look, fov=32):
    """A camera at room scale looking at `look`; the vertical field of view in degrees, as the web measures it."""
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name)); bpy.context.scene.collection.objects.link(cam)
    cam.location = loc; cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.sensor_fit = 'VERTICAL'; cam.data.angle = math.radians(fov); cam.data.clip_end = 200
    return cam


def render(sc, cam, samples, path, size=(1440, 900), exposure=0.0):
    """A denoised Cycles render through `cam` (AgX, as the web tone-maps): the target the web version should match."""
    sc.camera = cam; sc.render.resolution_x, sc.render.resolution_y = size; sc.render.resolution_percentage = 100
    sc.cycles.samples = samples; sc.cycles.use_denoising = True; sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'None'; sc.view_settings.exposure = exposure
    sc.render.image_settings.file_format = 'PNG'; sc.render.filepath = path
    t0 = time.time(); bpy.ops.render.render(write_still=True); cine.log(f'render {cam.name} {time.time() - t0:.0f}s -> {path}')


def cast_cache(out_dir, cast, spec, build, col):
    """The cast is slow to make (retargets, IK, every act): keep it in a .blend named by a hash of `spec` (bump its
    'v' after changing people.py or the costumes). `build()` returns [(c, arm, mesh)] with c['acts'] filled; from the
    cache, each c in `cast` gets its acts back by name. Returns [(c, arm, mesh)]."""
    key = hashlib.md5(json.dumps(spec, sort_keys=True, default=str).encode()).hexdigest()[:10]
    path = os.path.join(out_dir, f'cast_{key}.blend')
    if os.path.exists(path):
        with bpy.data.libraries.load(path, link=False) as (src, dst): dst.objects = list(src.objects); dst.actions = list(src.actions)
        seated = []
        for c in cast:
            arm = next(o for o in dst.objects if o.type == 'ARMATURE' and o.get('person') == c['who'])
            mesh = next(o for o in dst.objects if o.type == 'MESH' and o.get('person') == c['who'])
            for o in (arm, mesh): col.objects.link(o)
            c['acts'] = {k: bpy.data.actions[v] for k, v in json.loads(arm['acts']).items()}
            seated.append((c, arm, mesh))
        cine.log('cast from cache', os.path.basename(path))
        return seated
    seated = build()
    keep = set()
    for c, arm, mesh in seated: arm['acts'] = json.dumps({k: a.name for k, a in c['acts'].items()}); keep |= {arm, mesh, *c['acts'].values()}
    os.makedirs(out_dir, exist_ok=True)
    bpy.data.libraries.write(path, keep, fake_user=True)
    cine.log('cast cached', os.path.basename(path))
    return seated


# surfaces the web draws itself: a terminal's screen, a window's glass (rain), lace, a drinking glass and its water
LIVE_ROLES = ('screen', 'window', 'lace', 'glass', 'water')


def bake(objs, wall_h, out_dir, size=2048, samples=320, passes=None):
    """Bake a room's light into atlases: 'arch' (the shell) and 'furn' (everything in it), per pass. `passes` maps a
    suffix to (switch, scale): '' is the room's own light; a second pass ('flash') bakes, say, lightning alone, at
    `scale` of the size and samples. `switch(on)` turns that pass's lights on and the others off.
    Surfaces the web draws live (LIVE_ROLES) are never light-mapped.
    Returns (export list, {atlas name: EXR master})."""
    passes = passes or {'': (None, 1.0)}
    live = [o for o in objs if o.get('role') in LIVE_ROLES]
    for o in live:
        if 'lm' in o: del o['lm']
    others = [o for o in objs if not o.get('lm')]
    lit, exterior = cine.cull_and_split([o for o in objs if o.get('lm')], wall_h)
    groups = {g: [o for o in lit if o.get('lm') == g] for g in ('arch', 'furn')}
    for g, members in groups.items(): cine.lightmap_uvs(members, margin=0.003 if g == 'arch' else 0.004)
    atlases = {}
    for suffix, (switch, k) in passes.items():
        if switch: switch(True)
        for g, members in groups.items():
            name = f'{g}_{suffix}' if suffix else g
            img = cine.bake_atlas(members, name, int(size * k), int(samples * k))
            dn = cine.denoise(img)
            path = os.path.join(out_dir, f'lm_{name}.exr'); shutil.copy(bpy.path.abspath(dn.filepath), path); atlases[name] = path
            cine.log('saved', path, f'{os.path.getsize(path) / 1e6:.1f} MB')
        if switch: switch(False)
    for m in bpy.data.materials:   # the bake targets must not reach the export
        if m.node_tree and '__bake' in m.node_tree.nodes: m.node_tree.nodes.remove(m.node_tree.nodes['__bake'])
    return lit + exterior + others, atlases


def room_meta(wall_h, atlases):
    """room.json's light-map part (encode_lightmaps.py turns the EXR masters into WebP and updates it)."""
    meta = {'module': cine.MODULE, 'wallHeight': wall_h, 'lightmaps': {g: os.path.basename(atlases[g]) for g in ('arch', 'furn') if g in atlases},
            # Cycles' diffuse light pass is E/pi; three.js multiplies the light map by albedo/pi, so scale by pi
            'lightMapIntensity': math.pi}
    flash = {g: os.path.basename(atlases[f'{g}_flash']) for g in ('arch', 'furn') if f'{g}_flash' in atlases}
    if flash: meta['flashmaps'] = flash
    return meta


def export_people(seated, web_dir, meta_of):
    """One glTF per person (body, rig, every act; their acts checked first) and their entries for room.json."""
    out = os.path.join(web_dir, 'people'); os.makedirs(out, exist_ok=True)
    metas = []
    for c, arm, mesh in seated:
        people.export_person(arm, mesh, c['acts'], os.path.join(out, f"{c['who']}.glb"))
        metas.append(meta_of(c))
    return metas


def write_meta(web_dir, meta):
    with open(os.path.join(web_dir, 'room.json'), 'w') as f: json.dump(meta, f, indent=1)
    cine.log('wrote room.json')


def update_meta(web_dir, **parts):
    """Replace parts of an existing room.json (the people after a people-only run), keeping the rest."""
    path = os.path.join(web_dir, 'room.json'); meta = json.load(open(path)) if os.path.exists(path) else {}
    meta.update(parts); write_meta(web_dir, meta)
    return meta
