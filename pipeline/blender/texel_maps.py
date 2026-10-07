# For each texel of an avatar's textures: where it sits on the body (rest pose, metres, facing -y) and which
# bone moves it. Costume painting (pipeline/people_textures.py) then works on the body, not on the UV layout:
# "the shirt front between the collar and the belt", "the legs below the hem", "above the upper lip".
# Usage: blender -b --factory-startup -P pipeline/blender/texel_maps.py -- Business_Male_01 Male_Adult_12 ...
import sys, os
sys.dont_write_bytecode = True   # no __pycache__ next to the scripts
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import cine, people

SIZE = 1024
OUT = os.path.join(cine.OUT, 'people', 'maps')


def texel_map(mesh, mat_index, size=SIZE):
    me = mesh.data; uv = me.uv_layers.active.data; W = mesh.matrix_world
    P = np.array([(W @ v.co)[:] for v in me.vertices], np.float32)
    N = np.array([(W.to_3x3() @ v.normal).normalized()[:] for v in me.vertices], np.float32)
    dom = np.array([max(v.groups, key=lambda g: g.weight).group if len(v.groups) else -1 for v in me.vertices], np.int16)
    pos = np.full((size, size, 3), np.nan, np.float32); nor = np.zeros((size, size, 3), np.float32)
    bone = np.full((size, size), -1, np.int16)
    me.calc_loop_triangles()
    for tri in me.loop_triangles:
        if tri.material_index != mat_index: continue
        t = np.array([uv[l].uv[:] for l in tri.loops], np.float32)
        x = t[:, 0] * size - 0.5; y = (1 - t[:, 1]) * size - 0.5          # texel centres at integers, row 0 on top
        x0, x1 = int(np.floor(x.min())), int(np.ceil(x.max())); y0, y1 = int(np.floor(y.min())), int(np.ceil(y.max()))
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, size - 1), min(y1, size - 1)
        if x1 < x0 or y1 < y0: continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        d = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
        if abs(d) < 1e-12: continue
        a = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / d
        b = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / d
        c = 1 - a - b
        inside = (a >= -1e-3) & (b >= -1e-3) & (c >= -1e-3)
        if not inside.any(): continue
        vi = list(tri.vertices); w = np.stack([a, b, c], -1)[inside]
        yy, xx = gy[inside], gx[inside]
        pos[yy, xx] = w @ P[vi]; nor[yy, xx] = w @ N[vi]
        bone[yy, xx] = dom[vi][np.argmax(w, 1)]
    return pos, nor, bone


def main(names):
    os.makedirs(OUT, exist_ok=True)
    for name in names:
        cine.reset(16)
        arm, mesh = people.load_avatar(name)
        groups = [g.name for g in mesh.vertex_groups]
        joints = {b.name: (arm.matrix_world @ b.head_local)[:] for b in arm.data.bones}
        for i, slot in enumerate(mesh.material_slots):
            tex = next((n.image for n in slot.material.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image and '_color' in n.image.name), None)
            if tex is None: continue
            pos, nor, bone = texel_map(mesh, i)
            path = os.path.join(OUT, f"{os.path.splitext(os.path.basename(tex.filepath))[0]}.npz")
            np.savez_compressed(path, pos=pos.astype(np.float16), nor=nor.astype(np.float16), bone=bone, groups=np.array(groups),
                                joint_names=np.array(list(joints)), joints=np.array(list(joints.values()), np.float32))
            cine.log('texel map', name, slot.material.name, f'{np.isfinite(pos[..., 0]).mean() * 100:.0f}% covered ->', os.path.basename(path))


main(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
