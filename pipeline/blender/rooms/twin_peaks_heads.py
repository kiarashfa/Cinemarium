# Twin Peaks: Laura's sculpted head (made by rooms/pulp_fiction_heads.py from a prom bust) keeps its up-do's colours
# where the up-do was pressed onto the skull (a silver tiara, pale curls): here everything above her fringe and behind
# her face is painted golden blonde, its light and dark kept, so what shows between the hair cards is hair. Writes the
# head back. Usage: blender -b --factory-startup -P pipeline/blender/rooms/twin_peaks_heads.py
import os, sys
import bpy, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cine, people

GLB = os.path.join(cine.OUT, 'people', 'laura', 'laura_head.glb')
BLONDE = (196, 156, 96)
TOP = 0.34                                 # the brows (sculpt z): the fringe above them painted too; the eyes are at 0.21-0.25


def main():
    cine.reset(16)
    bpy.ops.import_scene.gltf(filepath=GLB)
    parts = [o for o in bpy.data.objects if o.type == 'MESH']
    def face(q): return q.y < -0.22 and q.z < TOP and ((q.x + 0.087) / 0.36) ** 2 + ((q.z - 0.1) / 0.5) ** 2 < 1.0
    def hair(q): return q.z > -0.05 and not face(q) and (q.z > TOP or q.y > -0.22)
    col = np.array(BLONDE, np.float32) / 255; W = np.array([0.2126, 0.7152, 0.0722], np.float32)
    def paint(rgb, m, skin):
        l = rgb[m] @ W; mean = max(float(l.mean()), 1e-4)
        rgb[m] = col[None, :] * np.clip((l / mean) ** 0.5, 0.6, 1.35)[:, None]; return int(m.sum())
    people._uv_paint(parts, hair, paint, 'laura hair blonde')
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=GLB, export_format='GLB', use_selection=True, export_image_format='AUTO')
    cine.log('wrote', GLB)


main()
