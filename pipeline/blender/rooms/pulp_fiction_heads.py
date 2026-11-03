# Jules's and Vincent's heads, made once: each sculpt (one to two million triangles) decimated to a light mesh,
# unwrapped afresh, and its colour baked across from the full sculpt (as the_big_lebowski_head.py does for the Dude).
# Writes pipeline/out/people/<who>/<who>_head.glb and a front and side look at it (with a 2 cm grid) to place the eyes.
# Usage: blender -b --factory-startup -P pipeline/blender/rooms/pulp_fiction_heads.py -- jules|vincent
import os, sys, math
import bpy
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cine

HEADS = {
    'vincent': dict(src=os.path.join(cine.CACHE, 'sketchfab', 'vincent', 'scene.gltf'), ratio=0.03),
    'jules': dict(src=os.path.join(cine.CACHE, 'tripo', 'jules.glb'), ratio=0.03, turn=-90),   # its face looks along +x: turned to -y
}
SIZE = 2048


def main(who):
    h = HEADS[who]; out = os.path.join(cine.OUT, 'people', who)
    cine.reset(16)
    sc = bpy.context.scene
    bpy.ops.import_scene.gltf(filepath=h['src'])
    parts = [o for o in bpy.data.objects if o.type == 'MESH']
    for o in parts:
        mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    for o in [o for o in bpy.data.objects if o.type == 'EMPTY']: bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    if len(parts) > 1: bpy.ops.object.join()
    hi = bpy.context.view_layer.objects.active; hi.name = f'{who}_hi'
    if h.get('turn'): hi.rotation_mode = 'XYZ'; hi.rotation_euler.z += math.radians(h['turn'])   # glTF imports in quaternions
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    lo = hi.copy(); lo.data = hi.data.copy(); lo.name = f'{who}_head'; sc.collection.objects.link(lo)
    bpy.context.view_layer.objects.active = lo
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.remove_doubles(threshold=1e-5); bpy.ops.object.mode_set(mode='OBJECT')
    md = lo.modifiers.new('thin', 'DECIMATE'); md.ratio = h['ratio']; md.use_collapse_triangulate = True
    with bpy.context.temp_override(object=lo, active_object=lo): bpy.ops.object.modifier_apply(modifier=md.name)
    for l in list(lo.data.uv_layers): lo.data.uv_layers.remove(l)
    lo.data.uv_layers.new(name='UVMap')
    bpy.ops.object.select_all(action='DESELECT'); lo.select_set(True); bpy.context.view_layer.objects.active = lo
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
    bpy.ops.uv.pack_islands(rotate=True, margin=0.003, shape_method='CONVEX')
    bpy.ops.object.mode_set(mode='OBJECT')
    cine.log(who, 'head decimated to', len(lo.data.polygons), 'faces')
    img = bpy.data.images.new(f'{who}_head_color', SIZE, SIZE)
    m = bpy.data.materials.new(f'{who}_head'); nt = m.node_tree; p = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = img; nt.links.new(t.outputs['Color'], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.55; p.inputs['Metallic'].default_value = 0.0
    lo.data.materials.clear(); lo.data.materials.append(m); nt.nodes.active = t
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 4
    bpy.ops.object.select_all(action='DESELECT'); hi.select_set(True); lo.select_set(True); bpy.context.view_layer.objects.active = lo
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, use_selected_to_active=True, cage_extrusion=0.02, max_ray_distance=0.06, margin=8)
    os.makedirs(out, exist_ok=True)
    img.filepath_raw = os.path.join(out, f'{who}_head_color.png'); img.file_format = 'PNG'; img.save()
    bb = [lo.matrix_world @ Vector(c) for c in lo.bound_box]
    lo_ = Vector([min(v[i] for v in bb) for i in range(3)]); hi_ = Vector([max(v[i] for v in bb) for i in range(3)])
    cine.log(who, 'bounds', tuple(round(v, 3) for v in lo_), tuple(round(v, 3) for v in hi_))
    bpy.data.objects.remove(hi, do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT'); lo.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, f'{who}_head.glb'), export_format='GLB', use_selection=True, export_image_format='AUTO')
    cine.log('wrote', os.path.join(out, f'{who}_head.glb'))
    # looks: front (along +y and -y: the sculpt's front is found by eye) and side, orthographic, with a grid
    c = (lo_ + hi_) / 2; span = max(hi_ - lo_) * 1.15
    w = bpy.data.worlds.new('w'); w.color = (0.5, 0.5, 0.5); sc.world = w
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sc.collection.objects.link(sun); sun.rotation_euler = (0.6, 0.2, 0.4); sun.data.energy = 3
    gm = bpy.data.materials.new('grid'); gm.diffuse_color = (1, 0, 0, 1)
    sc.render.resolution_x = sc.render.resolution_y = 900; sc.cycles.samples = 16
    for name, d in (('ny', Vector((0, -1, 0))), ('py', Vector((0, 1, 0))), ('px', Vector((1, 0, 0)))):
        cam = bpy.data.objects.new(f'cam_{name}', bpy.data.cameras.new(f'cam_{name}')); sc.collection.objects.link(cam)
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = span
        cam.location = c + d * 2.0; cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        sc.camera = cam; sc.render.filepath = os.path.join(out, f'{who}_look_{name}.png'); bpy.ops.render.render(write_still=True)


main(sys.argv[sys.argv.index('--') + 1])
