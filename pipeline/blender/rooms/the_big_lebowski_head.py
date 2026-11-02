# The Dude's head, made once: the Jeff Bridges sculpt (2 million triangles, its UVs in thousands of small islands)
# decimated to a light mesh, unwrapped afresh, and its colour baked across from the full sculpt (decimating the
# sculpt directly tears its UVs: the face comes out speckled). Writes pipeline/out/people/dude/bridges_head.glb.
# Usage: blender -b --factory-startup -P pipeline/blender/rooms/the_big_lebowski_head.py
import os, sys, math
import bpy
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cine

SRC = os.path.join(cine.CACHE, 'sketchfab', 'bridges', 'scene.gltf')
OUT = os.path.join(cine.OUT, 'people', 'dude')
RATIO, SIZE = 0.035, 2048


def main():
    cine.reset(16)
    sc = bpy.context.scene
    bpy.ops.import_scene.gltf(filepath=SRC)
    parts = [o for o in bpy.data.objects if o.type == 'MESH']
    for o in parts:
        mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    for o in [o for o in bpy.data.objects if o.type == 'EMPTY']: bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]; bpy.ops.object.join()
    hi = bpy.context.view_layer.objects.active; hi.name = 'bridges_hi'
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # the light copy: welded, decimated, unwrapped
    lo = hi.copy(); lo.data = hi.data.copy(); lo.name = 'bridges_head'; sc.collection.objects.link(lo)
    bpy.context.view_layer.objects.active = lo
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.remove_doubles(threshold=1e-5); bpy.ops.object.mode_set(mode='OBJECT')
    md = lo.modifiers.new('thin', 'DECIMATE'); md.ratio = RATIO; md.use_collapse_triangulate = True
    with bpy.context.temp_override(object=lo, active_object=lo): bpy.ops.object.modifier_apply(modifier=md.name)
    for l in list(lo.data.uv_layers): lo.data.uv_layers.remove(l)
    uv = lo.data.uv_layers.new(name='UVMap')
    bpy.ops.object.select_all(action='DESELECT'); lo.select_set(True); bpy.context.view_layer.objects.active = lo
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
    bpy.ops.uv.pack_islands(rotate=True, margin=0.003, shape_method='CONVEX')
    bpy.ops.object.mode_set(mode='OBJECT')
    cine.log('head decimated to', len(lo.data.polygons), 'faces')
    # its own material, the bake's target image
    img = bpy.data.images.new('bridges_head_color', SIZE, SIZE)
    m = bpy.data.materials.new('bridges_head'); nt = m.node_tree; p = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = img; nt.links.new(t.outputs['Color'], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.55; p.inputs['Metallic'].default_value = 0.0
    lo.data.materials.clear(); lo.data.materials.append(m); nt.nodes.active = t
    # bake the sculpt's colour across (diffuse colour only, from the full mesh to the light one)
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 4
    bpy.ops.object.select_all(action='DESELECT'); hi.select_set(True); lo.select_set(True); bpy.context.view_layer.objects.active = lo
    sc.render.bake.use_selected_to_active = True; sc.render.bake.cage_extrusion = 0.02; sc.render.bake.max_ray_distance = 0.06
    sc.render.bake.margin = 8
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, use_selected_to_active=True, cage_extrusion=0.02, max_ray_distance=0.06, margin=8)
    os.makedirs(OUT, exist_ok=True)
    img.filepath_raw = os.path.join(OUT, 'bridges_head_color.png'); img.file_format = 'PNG'; img.save()
    bpy.data.objects.remove(hi, do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT'); lo.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'bridges_head.glb'), export_format='GLB', use_selection=True, export_image_format='AUTO')
    cine.log('wrote', os.path.join(OUT, 'bridges_head.glb'))


main()
