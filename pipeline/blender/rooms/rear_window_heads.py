# Rear Window: Lisa's sculpted head (made by rooms/pulp_fiction_heads.py from a still) has her hair as dark as the
# still's shadows made it: here it is painted honey blonde, its light and dark kept, everywhere off the face oval
# and above the jaw (by position on the head, in the sculpt's own space: its eyes at EYES). Writes the head back.
# Usage: blender -b --factory-startup -P pipeline/blender/rooms/rear_window_heads.py
import os, sys
import bpy, numpy as np
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cine, people

GLB = os.path.join(cine.OUT, 'people', 'lisa', 'lisa_head.glb')
EYES = (Vector((-0.068, -0.26, 0.164)), Vector((0.113, -0.26, 0.164)))
BLONDE = (100, 80, 52)                     # before the fit brightens the sculpt (tone ~2.2): a honey blonde


def main():
    cine.reset(16)
    bpy.ops.import_scene.gltf(filepath=GLB)
    parts = [o for o in bpy.data.objects if o.type == 'MESH']
    cx = (EYES[0].x + EYES[1].x) / 2; ez = EYES[0].z
    def face(q): return q.y < -0.1 and ((q.x - cx) / 0.2) ** 2 + ((q.z - (ez - 0.1)) / 0.29) ** 2 < 1.0
    def core(q): return q.y < -0.1 and abs(q.x - cx) < 0.08 and ez - 0.25 < q.z < ez + 0.04
    def neck(q): return abs(q.x - cx) < 0.17 and q.z < ez - 0.24
    def hair(q): return not face(q) and not neck(q) and q.z > ez - 0.36
    col = np.array(BLONDE, np.float32) / 255; W = np.array([0.2126, 0.7152, 0.0722], np.float32); ref = {}
    def blonde(rgb, m, mean):
        l = rgb[m] @ W; rgb[m] = col[None, :] * np.clip((l / max(mean, 1e-4)) ** 0.6, 0.45, 1.5)[:, None]
    def skin_ref(rgb, m, skin):
        ref['skin'] = float(np.median(rgb[m] @ W)) if m.any() else 0.2; return int(m.sum())
    def paint(rgb, m, skin):
        ref['hair'] = float((rgb[m] @ W).mean()); blonde(rgb, m, ref['hair']); return int(m.sum())
    def temples(rgb, m, skin):                                            # in the face's oval only what is darker than her skin
        dark = m & ((rgb @ W) < ref['skin'] * 0.62); blonde(rgb, dark, ref.get('hair', ref['skin'] * 0.5)); return int(dark.sum())
    people._uv_paint(parts, core, skin_ref, 'lisa skin sampled')
    people._uv_paint(parts, hair, paint, 'lisa hair blonde')
    edge = lambda q: face(q) and (q.z > ez + 0.11 or (abs(q.x - cx) > 0.15 and q.z > ez - 0.3))   # the forehead over the brows, the oval's sides
    people._uv_paint(parts, edge, temples, 'lisa hairline blonde')
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=GLB, export_format='GLB', use_selection=True, export_image_format='AUTO')
    cine.log('wrote', GLB)


main()
