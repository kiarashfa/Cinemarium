# Cinemarium's Blender kit: build a room at real size inside the module, light it with Cycles,
# bake the light into atlases, and export the room for the web.
#
# Conventions (Blender, Z up): the room spans x [-4.8, 4.8], y [-3.8, 3.8], z [0, H] with the floor at z = 0.
# +y is the back wall, -x the left wall (the glTF export turns +y into three.js -z). Front (-y) and right (+x)
# walls are low kerbs: the cut-away. Custom properties become glTF extras:
#   lm = 'arch' | 'furn'   which light-map atlas the object is baked into
#   bake_only = 1          present while baking (a ceiling, the missing walls), never exported
#   role = '...'           runtime behaviour (a screen, a clock hand)
import bpy, bmesh, math, os, json, time
from mathutils import Vector, Matrix, Euler

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CACHE = os.path.join(ROOT, 'pipeline', 'cache')
OUT = os.path.join(ROOT, 'pipeline', 'out')
MODULE = (9.6, 7.6, 3.0)


def log(*a):
    print('[cine]', *a, flush=True)


# ---------------------------------------------------------------- scene
def reset(samples=256):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for kind in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = kind; prefs.get_devices()
            if any(d.type == kind for d in prefs.devices):
                for d in prefs.devices: d.use = d.type == kind
                break
        except Exception:
            pass
    sc.cycles.device = 'GPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 8; sc.cycles.diffuse_bounces = 5; sc.cycles.glossy_bounces = 3; sc.cycles.transmission_bounces = 4
    sc.cycles.sample_clamp_indirect = 8.0
    world = bpy.data.worlds.new('World'); sc.world = world
    world.color = (0, 0, 0)
    try: world.use_nodes = True
    except Exception: pass
    bg = world.node_tree.nodes.get('Background') if world.node_tree else None
    if bg: bg.inputs['Color'].default_value = (0, 0, 0, 1); bg.inputs['Strength'].default_value = 0.0
    return sc


def phantom(ob):
    """Present for light (bounce and shadow), absent for the camera and reflections: a ceiling, a missing wall."""
    ob.visible_camera = False; ob.visible_glossy = False; ob.visible_transmission = False; ob['bake_only'] = 1
    return ob


def coll(name):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(c)
    return c


def link(obj, collection=None):
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


# ---------------------------------------------------------------- textures and materials
_img_cache = {}


def image(path, colour=True):
    key = (path, colour)
    if key not in _img_cache:
        im = bpy.data.images.load(path, check_existing=True)
        im.colorspace_settings.name = 'sRGB' if colour else 'Non-Color'
        _img_cache[key] = im
    return _img_cache[key]


def material(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, maps=None, scale=1.0, normal_strength=1.0,
             emission=None, emission_strength=0.0, alpha=None, specular=0.5, coat=0.0, coat_rough=0.05, sheen=0.0):
    """Principled material. maps: {'color'|'rough'|'normal'|'ao': path}; textures tile every `scale` metres of UVMap."""
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name)
    nt = m.node_tree; nodes, links = nt.nodes, nt.links
    p = nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    p.inputs['Specular IOR Level'].default_value = specular
    if coat: p.inputs['Coat Weight'].default_value = coat; p.inputs['Coat Roughness'].default_value = coat_rough
    if sheen: p.inputs['Sheen Weight'].default_value = sheen
    if emission is not None:
        p.inputs['Emission Color'].default_value = (*emission, 1); p.inputs['Emission Strength'].default_value = emission_strength
    if alpha is not None: p.inputs['Alpha'].default_value = alpha
    maps = maps or {}
    if maps:
        uv = nodes.new('ShaderNodeUVMap'); uv.uv_map = 'UVMap'
        mp = nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / scale, 1 / scale, 1)
        links.new(uv.outputs['UV'], mp.inputs['Vector'])

        def tex(path, colour):
            t = nodes.new('ShaderNodeTexImage'); t.image = image(path, colour); links.new(mp.outputs['Vector'], t.inputs['Vector']); return t
        if 'color' in maps: links.new(tex(maps['color'], True).outputs['Color'], p.inputs['Base Color'])
        if 'rough' in maps: links.new(tex(maps['rough'], False).outputs['Color'], p.inputs['Roughness'])
        if 'normal' in maps:
            nm = nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = normal_strength
            links.new(tex(maps['normal'], False).outputs['Color'], nm.inputs['Color']); links.new(nm.outputs['Normal'], p.inputs['Normal'])
    return m


# ---------------------------------------------------------------- geometry
def _mesh_obj(name, bm, mat, collection=None, smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth:
        for poly in me.polygons: poly.use_smooth = True
    ob = bpy.data.objects.new(name, me); link(ob, collection)
    if mat: me.materials.append(mat)
    return ob


def bevel(ob, width=0.003, segments=2, angle=50):
    """Bevel every sharp edge (real objects catch light on their edges) and keep the faces flat-shaded."""
    md = ob.modifiers.new('bevel', 'BEVEL'); md.width = width; md.segments = segments; md.limit_method = 'ANGLE'
    md.angle_limit = math.radians(angle); md.harden_normals = True; md.use_clamp_overlap = True; md.profile = 0.6
    return ob


def box(name, size, loc, mat, rot=(0, 0, 0), bev=0.003, seg=2, collection=None, **props):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    ob = _mesh_obj(name, bm, mat, collection)
    ob.location = loc; ob.rotation_euler = rot
    if bev: bevel(ob, bev, seg)
    for k, v in props.items(): ob[k] = v
    return ob


def cyl(name, r, h, loc, mat, rot=(0, 0, 0), seg=32, r2=None, bev=0.0015, collection=None, **props):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h)
    ob = _mesh_obj(name, bm, mat, collection)
    ob.location = loc; ob.rotation_euler = rot
    if bev: bevel(ob, bev, 2, 30)
    for k, v in props.items(): ob[k] = v
    return ob


def rounded_slab(name, w, d, h, r, loc, mat, rot=(0, 0, 0), seg=8, edge_bev=0.004, collection=None, **props):
    """A slab with rounded vertical corners (a desk top), bevelled along its top and bottom edges."""
    bm = bmesh.new(); pts = []
    for cx, cy, a0 in ((w / 2 - r, d / 2 - r, 0), (-w / 2 + r, d / 2 - r, 90), (-w / 2 + r, -d / 2 + r, 180), (w / 2 - r, -d / 2 + r, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    bot = [bm.verts.new((x, y, -h / 2)) for x, y in pts]; top = [bm.verts.new((x, y, h / 2)) for x, y in pts]
    bm.faces.new(list(reversed(bot))); bm.faces.new(top)
    n = len(pts)
    for i in range(n): bm.faces.new((bot[i], bot[(i + 1) % n], top[(i + 1) % n], top[i]))
    ob = _mesh_obj(name, bm, mat, collection)
    ob.location = loc; ob.rotation_euler = rot
    if edge_bev: bevel(ob, edge_bev, 3, 60)
    for k, v in props.items(): ob[k] = v
    return ob


def apply_modifiers(ob):
    bpy.context.view_layer.objects.active = ob
    for md in list(ob.modifiers):
        try: bpy.ops.object.modifier_apply(modifier=md.name)
        except Exception as e: log('modifier', ob.name, md.name, e)


def world_uv(ob, scale=1.0):
    """UVMap from world-space box projection, in metres / scale: tiling textures keep their real size."""
    me = ob.data
    uv = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
    mw = ob.matrix_world; nmat = mw.to_3x3().inverted().transposed()
    for poly in me.polygons:
        n = (nmat @ poly.normal).normalized(); ax = max(range(3), key=lambda i: abs(n[i]))
        for li in poly.loop_indices:
            co = mw @ me.vertices[me.loops[li].vertex_index].co
            u, v = ((co.y, co.z), (co.x, co.z), (co.x, co.y))[ax]
            if ax == 0 and n.x < 0: u = -u
            if ax == 1 and n.y > 0: u = -u
            uv.data[li].uv = (u / scale, v / scale)


def import_gltf(path, loc=(0, 0, 0), rot=(0, 0, 0), scale=1.0, collection=None, **props):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new(os.path.basename(path).split('.')[0], None); link(root, collection)
    for o in new:
        for c in o.users_collection: c.objects.unlink(o)
        link(o, collection)
        if o.parent is None: o.parent = root
    root.location = loc; root.rotation_euler = rot; root.scale = (scale,) * 3
    bpy.context.view_layer.update()
    meshes = [o for o in new if o.type == 'MESH']
    for o in meshes:
        for k, v in props.items(): o[k] = v
    return root, meshes


def bake_ready(objs):
    """Flatten: apply modifiers, bake world transforms into the mesh, so every static object is plain geometry."""
    for ob in objs:
        if ob.type != 'MESH': continue
        if ob.data.users > 1: ob.data = ob.data.copy()
        apply_modifiers(ob)
        mw = ob.matrix_world.copy(); ob.parent = None; ob.matrix_world = mw
        ob.data.transform(mw); ob.matrix_world = Matrix.Identity(4)
        ob.data.update()


def cull_and_split(objs, wall_h, kerb_h=0.22):
    """Give the light-map atlas only to faces that see the room's light.
    - deleted: faces lying on the floor face-down, panel backs against their backing (never seen)
    - moved to an 'exterior' twin without a light map, lit live instead: the outside of the module (wall backs,
      the slab's edges) and the cut tops of walls and kerbs, which in the bake sit under the phantoms
    Returns the objects that keep a light map and the new exterior objects."""
    W, D = MODULE[0], MODULE[1]
    keep, exterior = [], []
    for ob in objs:
        me = ob.data; bm = bmesh.new(); bm.from_mesh(me)
        name = ob.name
        dead, outside = [], []
        for f in bm.faces:
            n, c = f.normal, f.calc_center_median()
            zmax = max(v.co.z for v in f.verts)
            if n.z < -0.9 and zmax < 0.006: dead.append(f); continue
            if (name.startswith('back_panel') and n.y > 0.9) or (name.startswith('left_panel') and n.x < -0.9): dead.append(f); continue
            on_edge = (abs(c.x) > W / 2 - 0.002 and c.x * n.x > 0.5 * abs(c.x)) or (abs(c.y) > D / 2 - 0.002 and c.y * n.y > 0.5 * abs(c.y))
            cut_top = n.z > 0.9 and ((c.z > wall_h - 0.003 and name.startswith(('back_', 'left_'))) or (name.startswith('kerb') and c.z > kerb_h - 0.003))
            if on_edge or cut_top or name == 'subfloor': outside.append(f)
        if outside:
            ext = ob.copy(); ext.data = me.copy(); ext.name = name + '_ext'
            for k in list(ext.keys()): del ext[k]
            ext['exterior'] = 1
            for c_ in ob.users_collection: c_.objects.link(ext)
            be = bmesh.new(); be.from_mesh(ext.data); be.faces.ensure_lookup_table()
            idx = {f.index for f in outside}
            bmesh.ops.delete(be, geom=[f for f in be.faces if f.index not in idx], context='FACES'); be.to_mesh(ext.data); be.free()
            exterior.append(ext)
        bmesh.ops.delete(bm, geom=list({*dead, *outside}), context='FACES')
        bm.to_mesh(me); bm.free(); me.update()
        if len(me.polygons): keep.append(ob)
        else: bpy.data.objects.remove(ob, do_unlink=True)
    log(f'cull: {len(keep)} light-mapped objects, {len(exterior)} exterior twins')
    return keep, exterior


# ---------------------------------------------------------------- light maps
def lightmap_uvs(objs, margin=0.004):
    """Second UV set 'Lightmap', all objects packed into one atlas at a uniform texel density."""
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objs:
        me = ob.data
        if 'UVMap' not in me.uv_layers:
            if len(me.uv_layers): me.uv_layers[0].name = 'UVMap'
            else: world_uv(ob)
        lm = me.uv_layers.get('Lightmap') or me.uv_layers.new(name='Lightmap')
        me.uv_layers.active = lm
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=margin, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    # concave packing is tight but slow with thousands of islands (every bevelled keycap face); convex is close and fast
    bpy.ops.uv.pack_islands(rotate=True, margin=margin, shape_method='CONVEX' if sum(len(o.data.polygons) for o in objs) > 20000 else 'CONCAVE', scale=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    for ob in objs:
        ob.data.uv_layers['UVMap'].active_render = True


def bake_atlas(objs, name, size, samples, margin_px=12):
    """Diffuse light (direct + indirect, no colour) into a float atlas shared by `objs`."""
    sc = bpy.context.scene
    img = bpy.data.images.new(f'lm_{name}', size, size, float_buffer=True, alpha=False)
    mats = {s.material for ob in objs for s in ob.material_slots if s.material}
    for m in mats:
        nt = m.node_tree; n = nt.nodes.get('__bake') or nt.nodes.new('ShaderNodeTexImage'); n.name = '__bake'
        n.image = img; nt.nodes.active = n
    for ob in objs: ob.data.uv_layers.active = ob.data.uv_layers['Lightmap']
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objs: ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    sc.cycles.samples = samples; sc.render.bake.margin = margin_px; sc.render.bake.margin_type = 'EXTEND'
    t0 = time.time()
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'}, margin=margin_px, use_clear=True)
    log(f'baked {name} {size}px x{samples} in {time.time() - t0:.0f}s')
    for ob in objs: ob.data.uv_layers.active = ob.data.uv_layers['UVMap']
    return img


def denoise(img):
    """OIDN through the compositor: the atlas in, the denoised atlas out (same size)."""
    w, h = img.size
    sc = bpy.data.scenes.new('__denoise'); sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100; sc.render.engine = 'BLENDER_EEVEE'
    sc.view_settings.view_transform = 'Standard'; sc.display_settings.display_device = 'sRGB'
    g = bpy.data.node_groups.new('__dn', 'CompositorNodeTree'); sc.compositing_node_group = g
    i = g.nodes.new('CompositorNodeImage'); i.image = img
    d = g.nodes.new('CompositorNodeDenoise'); d.inputs['HDR'].default_value = True
    try: d.inputs['Prefilter'].default_value = 'Accurate'
    except Exception: pass
    o = g.nodes.new('NodeGroupOutput'); g.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    g.links.new(i.outputs['Image'], d.inputs['Image']); g.links.new(d.outputs['Image'], o.inputs[0])
    cam = bpy.data.objects.new('__dncam', bpy.data.cameras.new('__dncam')); sc.collection.objects.link(cam); sc.camera = cam
    bpy.ops.render.render(scene=sc.name)
    tmp = os.path.join(OUT, f'__{img.name}_dn.exr')
    sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_depth = '16'
    bpy.data.images['Render Result'].save_render(tmp, scene=sc)
    out = bpy.data.images.load(tmp); out.name = img.name + '_dn'
    bpy.data.scenes.remove(sc)
    return out


def save_exr(img, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.filepath_raw = path; img.file_format = 'OPEN_EXR'
    sc = bpy.context.scene; sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_depth = '16'
    sc.render.image_settings.exr_codec = 'ZIP'
    img.save_render(path, scene=sc)


def check_module(objs):
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for ob in objs:
        for c in ob.bound_box:
            p = ob.matrix_world @ Vector(c); lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
    W, D, H = MODULE; tol = 0.005
    ok = lo.x >= -W / 2 - tol and hi.x <= W / 2 + tol and lo.y >= -D / 2 - tol and hi.y <= D / 2 + tol and hi.z <= H + tol and lo.z >= -0.05 - tol
    log(f'bounds x[{lo.x:.3f},{hi.x:.3f}] y[{lo.y:.3f},{hi.y:.3f}] z[{lo.z:.3f},{hi.z:.3f}] fits module: {ok}')
    if not ok:
        for ob in objs:
            ps = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
            if min(p.z for p in ps) < -0.05 - tol or max(p.z for p in ps) > H + tol or min(p.x for p in ps) < -W / 2 - tol or max(p.x for p in ps) > W / 2 + tol \
                    or min(p.y for p in ps) < -D / 2 - tol or max(p.y for p in ps) > D / 2 + tol:
                log('  outside the module:', ob.name, tuple(round(min(p[i] for p in ps), 3) for i in range(3)), tuple(round(max(p[i] for p in ps), 3) for i in range(3)))
        raise SystemExit('room exceeds the module')


def export_glb(objs, path, draco=False):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objs: ob.select_set(True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_extras=True, export_apply=True,
                              export_texcoords=True, export_normals=True, export_tangents=False, export_materials='EXPORT',
                              export_image_format='WEBP', export_image_quality=88, export_lights=False, export_cameras=False,
                              export_draco_mesh_compression_enable=draco, export_yup=True)
    log('exported', path, f'{os.path.getsize(path) / 1e6:.1f} MB')
