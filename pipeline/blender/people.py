# Rocketbox people: import an avatar (FBX, 3ds Max Biped rig), point its textures at the cache, give it clean
# glTF-ready materials, reshape its body, and bake motion-capture clips from the Rocketbox library onto it.
#
# Every Rocketbox clip is a seamless loop (its last frame is its first), so clips are always baked whole:
# cutting one short is what makes a figure jump when its loop restarts.
import bpy, os, math
import numpy as np
from mathutils import Vector, Matrix, Quaternion
import cine

RB = os.path.join(cine.CACHE, 'rocketbox')
FPS = 30


def _import_fbx(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path, automatic_bone_orientation=False, ignore_leaf_bones=False, use_anim=True)
    return [o for o in bpy.data.objects if o not in before]


def load_avatar(name, textures=None, collection=None):
    """Returns (armature, mesh). `textures` maps texture basenames to replacement files (recoloured copies)."""
    objs = _import_fbx(os.path.join(RB, 'avatars', name, 'Export', f'{name}.fbx'))
    arm = next(o for o in objs if o.type == 'ARMATURE'); mesh = next(o for o in objs if o.type == 'MESH')
    for o in objs:
        if o.type == 'EMPTY': bpy.data.objects.remove(o, do_unlink=True)
    if collection:
        for o in (arm, mesh):
            for c in o.users_collection: c.objects.unlink(o)
            collection.objects.link(o)
    tex_dir = os.path.join(RB, 'avatars', name, 'Textures')
    textures = textures or {}
    for slot in mesh.material_slots:
        m = slot.material; nt = m.node_tree; p = nt.nodes['Principled BSDF']
        for n in list(nt.nodes):
            if n.type != 'TEX_IMAGE' or not n.image: continue
            base = os.path.basename(n.image.filepath.replace('\\', '/'))
            src = textures.get(base) or os.path.join(tex_dir, base)
            if base.endswith('_specular.tga') and not os.path.exists(src):   # some avatars name a specular map they lack
                nt.nodes.remove(n); continue
            n.image = bpy.data.images.load(src, check_existing=True)
            if base.endswith('_specular.tga'):
                # Unity-style specular: drop it, use a plain roughness instead
                for l in [l for l in nt.links if l.from_node == n]: nt.links.remove(l)
                nt.nodes.remove(n)
            elif base.endswith('_normal.tga'):
                n.image.colorspace_settings.name = 'Non-Color'
        p.inputs['Specular IOR Level'].default_value = 0.5
        p.inputs['Roughness'].default_value = 0.55 if 'head' in m.name else 0.72
        p.inputs['Metallic'].default_value = 0.0
    mesh['person'] = name
    bpy.context.view_layer.update()
    arm['rest'] = [v for row in arm.matrix_world for v in row]   # where it was imported: clips are measured from here
    return arm, mesh


# ---------------------------------------------------------------- body shape
def _joints(arm):
    return {b.name: arm.matrix_world @ b.head_local for b in arm.data.bones}


def _smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def _gauss(x, c, s): return np.exp(-0.5 * ((x - c) / s) ** 2)


def _radial(P, a, b, scale):
    """Displacement that scales points P radially about the line a->b; scale(t) with t along a->b (0..1)."""
    a, b = np.array(a[:]), np.array(b[:]); u = b - a; L = np.linalg.norm(u); u = u / L
    q = P - a; t = q @ u; r = q - t[:, None] * u
    return r * (scale(np.clip(t / L, 0, 1)) - 1)[:, None]


def reshape(arm, mesh, shape, k=1.0):
    """Change a body's build by moving its rest-pose vertices: radial scaling about the spine and limb axes,
    weighted by the skin weights so the joints blend. The skeleton is untouched, so every clip still fits.
    shape: 'heavy' (an obese build; `k` how much), 'athletic' (broad shoulders, big arms, a narrow waist), 'broad' (big and heavy-set:
    chest, arms, some belly, a thick neck), 'lean' (a longer face; `k` how much)."""
    me = mesh.data
    if me.shape_keys: raise RuntimeError('reshape expects a mesh without shape keys')
    J = _joints(arm); M = mesh.matrix_world; Mi = M.inverted()
    P = np.array([(M @ v.co)[:] for v in me.vertices]); n = len(P)
    names = [g.name for g in mesh.vertex_groups]
    W = np.zeros((n, len(names)))
    for i, v in enumerate(me.vertices):
        for g in v.groups: W[i, g.group] = g.weight
    W /= np.maximum(W.sum(1, keepdims=True), 1e-6)
    w = lambda *keys: W[:, [i for i, g in enumerate(names) if any(k in g for k in keys)]].sum(1) if any(any(k in g for k in keys) for g in names) else np.zeros(n)
    j = lambda k: J[f'Bip01 {k}']
    D = np.zeros_like(P)
    zp, zn = j('Pelvis').z, j('Neck').z
    h = (P[:, 2] - zp) / (zn - zp)
    spine = sorted([j(k) for k in ('Pelvis', 'Spine', 'Spine1', 'Spine2', 'Neck')], key=lambda v: v.z)
    cx = np.interp(P[:, 2], [v.z for v in spine], [v.x for v in spine]); cy = np.interp(P[:, 2], [v.z for v in spine], [v.y for v in spine])
    rx, ry = P[:, 0] - cx, P[:, 1] - cy
    front = _smooth(-0.02, 0.03, -ry)                      # the avatar faces -y
    belly, chest, hip, seat = _gauss(h, 0.28, 0.2), _gauss(h, 0.76, 0.14), _gauss(h, -0.04, 0.14), _gauss(h, -0.12, 0.11)
    limb = lambda a, b, s0, s1: (lambda t: s0 + (s1 - s0) * t)
    if shape == 'heavy':                                   # k > 1: heavier still (Huell); every displacement scales by it
        sf = 1 + 0.85 * belly + 0.28 * chest + 0.12 * hip
        sx = 1 + 0.32 * belly + 0.2 * chest + 0.24 * hip
        sb = 1 + 0.16 * belly + 0.1 * chest + 0.3 * seat
        sy = front * sf + (1 - front) * sb
        torso = w('Pelvis', 'Spine', 'Clavicle') * 1.0
        D[:, 0] += torso * rx * (sx - 1); D[:, 1] += torso * ry * (sy - 1)
        D[:, 2] -= torso * front * 0.025 * belly * np.clip(-ry / 0.15, 0, 1.5)        # the belly hangs a little
        for s in 'LR':
            D += w(f'{s} UpperArm')[:, None] * _radial(P, j(f'{s} UpperArm'), j(f'{s} Forearm'), limb(0, 0, 1.34, 1.2))
            D += w(f'{s} Forearm')[:, None] * _radial(P, j(f'{s} Forearm'), j(f'{s} Hand'), limb(0, 0, 1.18, 1.06))
            D += w(f'{s} Thigh')[:, None] * _radial(P, j(f'{s} Thigh'), j(f'{s} Calf'), limb(0, 0, 1.42, 1.16))
            D += w(f'{s} Calf')[:, None] * _radial(P, j(f'{s} Calf'), j(f'{s} Foot'), limb(0, 0, 1.16, 1.05))
        D += w('Neck')[:, None] * _radial(P, j('Neck'), j('Head'), lambda t: 1.42 - 0.12 * t)
        # a round, full face: wider cheeks and jaw, a soft double chin
        hd = j('Head'); lip = j('MUpperLip').z
        face = w('Head', 'MJaw', 'Mouth', 'Lip', 'Cheek', 'Masseter', 'Caninus') * _smooth(0.02, -0.03, P[:, 1] - hd.y)
        under = face * _smooth(lip + 0.045, lip - 0.06, P[:, 2])
        D[:, 0] += under * (P[:, 0] - hd.x) * 0.26; D[:, 1] += under * np.minimum(P[:, 1] - hd.y, 0) * 0.1
        chin = face * _gauss(P[:, 2], lip - 0.075, 0.025)
        D[:, 1] -= chin * 0.012; D[:, 2] -= chin * 0.008
        D *= k
    elif shape == 'athletic':
        sf = 1 + 0.15 * chest - 0.05 * belly
        sx = 1 + 0.13 * chest + 0.07 * _gauss(h, 0.56, 0.14) - 0.03 * belly
        sb = 1 + 0.09 * chest
        sy = front * sf + (1 - front) * sb
        torso = w('Pelvis', 'Spine', 'Clavicle')
        D[:, 0] += torso * rx * (sx - 1); D[:, 1] += torso * ry * (sy - 1)
        for s in 'LR':
            sh = j(f'{s} UpperArm')
            d = np.linalg.norm(P - np.array(sh[:]), axis=1)
            cap = (w(f'{s} UpperArm') + w(f'{s} Clavicle') * 0.7) * _gauss(d, 0.0, 0.075)          # deltoids
            D += cap[:, None] * (P - np.array(sh[:])) * 0.3
            D += w(f'{s} UpperArm')[:, None] * _radial(P, sh, j(f'{s} Forearm'), lambda t: 1.1 + 0.16 * _gauss(t, 0.5, 0.22) - 0.04 * t)
            D += w(f'{s} Forearm')[:, None] * _radial(P, j(f'{s} Forearm'), j(f'{s} Hand'), limb(0, 0, 1.15, 1.02))
            D += w(f'{s} Thigh')[:, None] * _radial(P, j(f'{s} Thigh'), j(f'{s} Calf'), limb(0, 0, 1.09, 1.04))
            D += w(f'{s} Calf')[:, None] * _radial(P, j(f'{s} Calf'), j(f'{s} Foot'), limb(0, 0, 1.07, 1.02))
        D += w('Neck')[:, None] * _radial(P, j('Neck'), j('Head'), lambda t: 1.17 - 0.08 * t)
        # trapezius: the shoulders' slope from neck to deltoid rises a little
        tr = w('Clavicle', 'Neck', 'Spine2') * _gauss(np.abs(P[:, 0]), 0.09, 0.05) * _smooth(j('Neck').z - 0.12, j('Neck').z - 0.02, P[:, 2]) * (1 - front * 0.6)
        D[:, 2] += tr * 0.012
    elif shape == 'broad':
        sf = 1 + 0.2 * chest + 0.32 * belly + 0.06 * hip
        sx = 1 + 0.16 * chest + 0.16 * belly + 0.1 * hip
        sb = 1 + 0.12 * chest + 0.08 * belly + 0.14 * seat
        sy = front * sf + (1 - front) * sb
        torso = w('Pelvis', 'Spine', 'Clavicle')
        D[:, 0] += torso * rx * (sx - 1); D[:, 1] += torso * ry * (sy - 1)
        for s in 'LR':
            sh = j(f'{s} UpperArm')
            D += w(f'{s} UpperArm')[:, None] * _radial(P, sh, j(f'{s} Forearm'), lambda t: 1.18 + 0.08 * _gauss(t, 0.5, 0.25) - 0.04 * t)
            D += w(f'{s} Forearm')[:, None] * _radial(P, j(f'{s} Forearm'), j(f'{s} Hand'), limb(0, 0, 1.14, 1.04))
            D += w(f'{s} Thigh')[:, None] * _radial(P, j(f'{s} Thigh'), j(f'{s} Calf'), limb(0, 0, 1.18, 1.08))
            D += w(f'{s} Calf')[:, None] * _radial(P, j(f'{s} Calf'), j(f'{s} Foot'), limb(0, 0, 1.08, 1.03))
        D += w('Neck')[:, None] * _radial(P, j('Neck'), j('Head'), lambda t: 1.26 - 0.1 * t)
    elif shape == 'slim_legs':
        # trouser legs made into legs (a skirt and tights are painted on): each cross-section of a thigh or a calf is
        # scaled about its bone to a leg's mean radius there; the hips stay as they are
        for s in 'LR':
            for bone, nxt, prof in (('Thigh', 'Calf', ((0.0, 0.088), (0.15, 0.084), (0.5, 0.071), (0.85, 0.058), (1.0, 0.054))),
                                    ('Calf', 'Foot', ((0.0, 0.052), (0.3, 0.053), (0.7, 0.041), (0.92, 0.033), (1.0, 0.032)))):
                a, b = np.array(j(f'{s} {bone}')[:]), np.array(j(f'{s} {nxt}')[:]); u = b - a; L = np.linalg.norm(u); u /= L
                wb = w(f'{s} {bone}'); q = P - a; t = (q @ u) / L; r = np.linalg.norm(q - np.outer(q @ u, u), axis=1)
                sel = (wb > 0.5) & (t > -0.05) & (t < 1.05)
                bins = np.linspace(0, 1, 11); cur = []
                for t0, t1 in zip(bins, bins[1:]):
                    m = sel & (t >= t0) & (t < t1); cur.append(np.mean(r[m]) if m.sum() > 3 else np.nan)
                cur = np.array(cur); ok = np.isfinite(cur); mid = (bins[:-1] + bins[1:]) / 2
                want = np.interp(mid, [p[0] for p in prof], [p[1] for p in prof])
                ratio = np.clip(want[ok] / cur[ok], 0.35, 1.2)
                hip = (lambda x: _smooth(0.04, 0.22, x)) if bone == 'Thigh' else (lambda x: np.ones_like(x))
                sc_ = lambda x, m=mid[ok], rt=ratio, hip=hip: 1 + (np.interp(x, m, rt) - 1) * hip(x)
                D += wb[:, None] * _radial(P, j(f'{s} {bone}'), j(f'{s} {nxt}'), sc_)
    elif shape == 'lean':
        hd = j('Head'); brow = j('MMiddleEyebrow').z; lip = j('MUpperLip').z
        face = w('Head', 'MJaw', 'Mouth', 'Lip', 'Cheek', 'Masseter', 'Caninus') * _smooth(brow, brow - 0.06, P[:, 2]) * _smooth(0.03, -0.02, P[:, 1] - hd.y)
        D[:, 0] -= face * (P[:, 0] - hd.x) * 0.07 * k
        D[:, 2] -= face * _smooth(lip + 0.02, lip - 0.05, P[:, 2]) * 0.007 * k
    else:
        raise ValueError(shape)
    for i, v in enumerate(me.vertices):
        if D[i].any(): v.co = Mi @ Vector((P[i] + D[i]).tolist())
    _fresh_normals(mesh)
    cine.log('reshape', mesh.get('person', mesh.name), shape, f'max {np.abs(D).max() * 100:.1f} cm')


def hair_volume(arm, mesh, lift=0.016, curl=0.005, seed=3):
    """Fuller hair: move the scalp (everything above the hairline but the ears) out along its normals, lumpy."""
    J = _joints(arm); M = mesh.matrix_world; Mi = M.inverted(); N3 = M.to_3x3()
    brow = J['Bip01 MMiddleEyebrow'].z; me = mesh.data
    head = {i for i, g in enumerate(mesh.vertex_groups) if g.name == 'Bip01 Head'}
    rng = np.random.default_rng(seed); K = rng.normal(size=(12, 3)) * 70; ph = rng.random(12) * 6.28
    moved = 0
    for v in me.vertices:
        if not any(g.group in head and g.weight > 0.5 for g in v.groups): continue
        p = M @ v.co; ax = abs(p.x)
        line = brow + 0.058 - 0.03 * float(_smooth(0.03, 0.062, ax))
        line += (brow + 0.004 - line) * float(_smooth(-0.075, -0.035, p.y))
        line += (brow - 0.088 - line) * float(_smooth(-0.005, 0.05, p.y))
        if ax > 0.066 and brow - 0.07 < p.z < brow + 0.008 and abs(p.y) < 0.04: continue      # the ears
        k = float(_smooth(line - 0.005, line + 0.02, p.z))
        if k <= 0: continue
        lump = float(np.mean(np.sin(K @ np.array(p[:]) + ph)))
        nrm = (N3 @ v.normal).normalized()
        v.co = Mi @ (p + nrm * k * (lift + curl * lump)); moved += 1
    _fresh_normals(mesh); cine.log('hair volume', mesh.get('person', mesh.name), moved, 'vertices')


def hair_cards(arm, mesh, scale=(1.0, 1.0, 1.0), lift=0.0, key='opacity'):
    """Bigger hair: scale the hair cards (the faces of the `key` material) about the middle of the skull, by `scale`
    (across, front to back, up), and raise the crown by `lift` metres (upright curls). The face's own fringe, below
    the brows in front, moves less."""
    J = _joints(arm); M = mesh.matrix_world; Mi = M.inverted(); me = mesh.data
    k = [i for i, s in enumerate(mesh.material_slots) if s.material and key in s.material.name]
    if not k: raise RuntimeError(f"{mesh.get('person', mesh.name)}: no '{key}' material")
    vs = {v for p in me.polygons if p.material_index in k for v in p.vertices}
    eye = (J['Bip01 LEye'] + J['Bip01 REye']) / 2; brow = J['Bip01 MMiddleEyebrow'].z
    c = Vector((eye.x, eye.y + 0.05, eye.z + 0.01))                  # the skull's middle (the avatar faces -y)
    for i in vs:
        p = M @ me.vertices[i].co; d = p - c
        face = float(_smooth(brow + 0.01, brow - 0.03, p.z) * _smooth(-0.02, -0.06, d.y))   # in front, below the brows
        s = [1 + (sc - 1) * (1 - 0.8 * face) for sc in scale]
        q = c + Vector((d.x * s[0], d.y * s[1], d.z * s[2] if d.z > 0 else d.z))
        q.z += lift * float(_smooth(0.0, 0.1, d.z)) * (1 - face)
        me.vertices[i].co = Mi @ q
    _fresh_normals(mesh); cine.log('hair cards', mesh.get('person', mesh.name), len(vs), 'vertices')


def hair_mass(arm, mesh, depth, n=300, size=0.018, colours=((0.03, 0.018, 0.012), (0.05, 0.032, 0.022)), fall=None, front=0.05,
              squash=(1.0, 1.0, 1.0), seed=5):
    """Curly hair as a mass of small lumps over the scalp, skinned to the head and joined into the body: Kramer's
    upright curls, Elaine's big dark curls. depth(p, d) gives the hair's thickness (m) at scalp point p (d = p minus the
    skull's middle, the avatar facing -y); `fall` (z) lets it hang below the hairline at the back and sides, to that
    height (shoulder-length hair). Lumps sit at random depths, larger toward the outside."""
    import bmesh
    rng = np.random.default_rng(seed)
    J = _joints(arm); M = mesh.matrix_world; me = mesh.data
    eye = (J['Bip01 LEye'] + J['Bip01 REye']) / 2; brow = J['Bip01 MMiddleEyebrow'].z
    c = Vector((eye.x, eye.y + 0.05, eye.z + 0.01))
    head = {i for i, g in enumerate(mesh.vertex_groups) if g.name == 'Bip01 Head'}
    hk = [i for i, s in enumerate(mesh.material_slots) if s.material and 'head' in s.material.name]
    on_head = {v for p in me.polygons if p.material_index in hk for v in p.vertices}
    scalp = []
    for v in me.vertices:
        if v.index not in on_head or not any(g.group in head and g.weight > 0.5 for g in v.groups): continue
        p = M @ v.co; ax = abs(p.x)
        line = brow + front - 0.03 * float(_smooth(0.03, 0.062, ax))
        line += (brow + 0.004 - line) * float(_smooth(-0.075, -0.035, p.y))
        line += (brow - 0.088 - line) * float(_smooth(-0.005, 0.05, p.y))
        if ax > 0.066 and brow - 0.07 < p.z < brow + 0.008 and abs(p.y) < 0.04: continue      # the ears
        if p.z < line: continue
        scalp.append((p, (M.to_3x3() @ v.normal).normalized()))
    if not scalp: raise RuntimeError('no scalp found')
    bm = bmesh.new(); mat_of = []
    def lump(at, r):
        m = Matrix.Translation(at) @ Quaternion(Vector(rng.normal(size=3)).normalized(), rng.uniform(0, math.pi)).to_matrix().to_4x4() @ Matrix.Diagonal((r * squash[0], r * squash[1], r * squash[2], 1))
        res = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0, matrix=m)
        k = int(rng.random() < 0.45)
        for f in {f for v in res['verts'] for f in v.link_faces}: f.material_index = k
    for _ in range(n):
        p, nrm = scalp[rng.integers(len(scalp))]
        t = depth(p, p - c)
        if t <= 0.002: continue
        u = rng.random() ** 0.7
        lump(p + nrm * (t * u), size * (0.7 + 0.6 * u) * rng.uniform(0.8, 1.2))
    if fall is not None:   # hanging from the back and sides of the scalp down to `fall`, close round the neck
        low = [s for s in scalp if s[0].z < brow + 0.01 and (s[0].y - c.y) > -0.045 and abs(s[0].x - c.x) < 0.075]
        for _ in range(int(n * 0.6)):
            p, nrm = low[rng.integers(len(low))]
            out = Vector((p.x - c.x, p.y - c.y, 0)).normalized()
            z = rng.uniform(fall, p.z); t = depth(p, p - c) * rng.uniform(0.4, 1.0)
            at = Vector((p.x, p.y, z)) + out * (t + 0.01 * (p.z - z) / max(p.z - fall, 1e-3))
            lump(at, size * rng.uniform(0.8, 1.25))
    for f in bm.faces: f.smooth = True
    hm = bpy.data.meshes.new('curls'); bm.to_mesh(hm); bm.free()
    ob = bpy.data.objects.new('curls', hm); [col.objects.link(ob) for col in mesh.users_collection]
    for k, cl in enumerate(colours):
        m = bpy.data.materials.new(f"curls_{mesh.get('person', 'x')}_{k}"); p_ = m.node_tree.nodes['Principled BSDF']
        p_.inputs['Base Color'].default_value = (*cl, 1); p_.inputs['Roughness'].default_value = 0.6; p_.inputs['Specular IOR Level'].default_value = 0.35
        hm.materials.append(m)
    ob.matrix_world = mesh.matrix_world.copy(); hm.transform(mesh.matrix_world.inverted()); ob.matrix_world = mesh.matrix_world
    vg = ob.vertex_groups.new(name='Bip01 Head'); vg.add(list(range(len(hm.vertices))), 1.0, 'REPLACE')
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.join()
    cine.log('hair mass', mesh.get('person', mesh.name), len(hm.vertices), 'vertices')


def _fresh_normals(mesh):
    """Imported custom normals would keep the old shape's shading; let the moved surface shade as itself."""
    me = mesh.data; me.update()
    if me.has_custom_normals:
        with bpy.context.temp_override(object=mesh, active_object=mesh, selected_objects=[mesh]):
            bpy.ops.mesh.customdata_custom_splitnormals_clear()


# ---------------------------------------------------------------- clips
def _fcurves(action):
    for layer in action.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                for fc in list(cb.fcurves): yield cb, fc


def _clip_armature(name, inplace, cyclic=False):
    """The clip's own armature, animated. Animation-only FBX files import with their first frame as the rest pose,
    so their channels cannot be copied to an avatar directly; we copy the resulting world pose instead."""
    objs = _import_fbx(os.path.join(RB, 'animations', f'{name}.fbx'))
    src = next(o for o in objs if o.type == 'ARMATURE')
    for o in objs:
        if o is not src: bpy.data.objects.remove(o, do_unlink=True)
    act = src.animation_data.action
    travel = 0.0
    for cb, fc in _fcurves(act):
        if inplace and fc.data_path == 'location' and fc.array_index in (0, 1):   # drop the travel over the floor, keep bob and sway
            k = fc.keyframe_points; travel = math.hypot(travel, k[-1].co[1] - k[0].co[1])
            v0 = k[0].co[1]
            for p in k: p.co[1] = v0; p.handle_left[1] = v0; p.handle_right[1] = v0
        if cyclic: fc.modifiers.new('CYCLES')
    return src, act, travel


def placement(arm):
    """How the avatar has been moved, turned and scaled since it was imported (identity if it has not)."""
    if 'rest' not in arm: raise RuntimeError(f'{arm.name}: no rest placement (load avatars with people.load_avatar)')
    r = list(arm['rest']); return arm.matrix_world @ Matrix([r[0:4], r[4:8], r[8:12], r[12:16]]).inverted()


def retarget(arm, name, inplace=False, cycles=1, action_name=None, limit=None):
    """Bakes clip `name` onto avatar `arm` as a new action, whole (or `cycles` times over, seamlessly).
    World-space copy of every shared bone; then only the root keeps its translation, so the avatar keeps its own
    proportions. Returns (action, (first, last) frame, speed in m/s for travelling clips).
    A clip's motion lives on its armature *object* (location, rotation and scale keyed on every frame), so the clip is
    carried by a helper placed as the avatar has been placed: an act baked after the avatar was seated lands on the
    seat, not at the room's origin."""
    src, act, travel = _clip_armature(name, inplace, cyclic=cycles > 1)
    P = placement(arm); grow = P.to_scale().x                 # a taller avatar strides further
    carrier = bpy.data.objects.new('__carrier', None); bpy.context.scene.collection.objects.link(carrier)
    carrier.matrix_world = P; src.parent = carrier; src.matrix_parent_inverse.identity()
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    period = f1 - f0; f1 = f0 + period * cycles if limit is None else min(f0 + limit, f0 + period * cycles)
    names = {b.name for b in src.data.bones}
    for pb in arm.pose.bones:
        if pb.name in names:
            c = pb.constraints.new('COPY_TRANSFORMS'); c.target = src; c.subtarget = pb.name; c.name = '__rt'
    keep = (arm.location.copy(), arm.rotation_euler.copy())
    bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE'); bpy.ops.pose.select_all(action='SELECT')
    arm.animation_data_create(); arm.animation_data.action = None
    bpy.ops.nla.bake(frame_start=f0, frame_end=f1, only_selected=True, visual_keying=True, clear_constraints=True, use_current_action=False, bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')
    baked = arm.animation_data.action; baked.name = action_name or name; baked.use_fake_user = True
    arm.location, arm.rotation_euler = keep
    root = next(b.name for b in arm.data.bones if b.parent is None)
    for cb, fc in _fcurves(baked):
        bone = fc.data_path.split('"')[1] if '"' in fc.data_path else ''
        if fc.data_path.endswith('.scale') or (fc.data_path.endswith('.location') and bone != root): cb.fcurves.remove(fc)
    for pb in arm.pose.bones:
        if pb.name != root: pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.data.objects.remove(src, do_unlink=True); bpy.data.actions.remove(act); bpy.data.objects.remove(carrier, do_unlink=True)
    speed = travel * grow / (period / FPS) if inplace else 0.0
    return baked, (f0, f1), speed


def freeze(action, keys=('Finger',), frame=None):
    """Hold some bones (the fingers, by default) still at one frame: they cost bytes and read as nothing at 1:6."""
    for cb, fc in _fcurves(action):
        if any(k in fc.data_path for k in keys):
            k = fc.keyframe_points; v = fc.evaluate(frame if frame is not None else k[0].co[0])
            for i in range(len(k) - 1, 0, -1): k.remove(k[i])
            k[0].co[1] = v; k[0].handle_left[1] = v; k[0].handle_right[1] = v


def _world(arm, pb): return arm.matrix_world @ pb.matrix


def _set_world(arm, pb, M):
    """Pose a bone by its world matrix, keeping only the rotation: retargeted bones (all but the root) never move or
    scale, and the decomposed matrix leaves tiny scale and offset errors in those unkeyed channels that compound
    frame after frame (a head grown a thousandfold) unless they are reset."""
    pb.matrix = arm.matrix_world.inverted() @ M
    pb.scale = (1, 1, 1)
    if pb.parent: pb.location = (0, 0, 0)
    bpy.context.view_layer.update()


def _aim(arm, pb, child_head, target):
    """Rotate bone pb (about its head) so that the point child_head moves toward target. Keeps its twist."""
    M = _world(arm, pb); head = M.translation
    q = (child_head - head).rotation_difference(target - head)
    R = q.to_matrix().to_4x4()
    _set_world(arm, pb, Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ M)


def ik2(arm, side, target, pole):
    """Two-bone IK on the real joints (Biped bones do not point along the limb, so Blender's IK cannot be used):
    place the wrist on `target` with the elbow bending toward `pole`."""
    up, fo, ha = (arm.pose.bones[f'Bip01 {side} {b}'] for b in ('UpperArm', 'Forearm', 'Hand'))
    S = _world(arm, up).translation.copy(); E = _world(arm, fo).translation.copy(); W = _world(arm, ha).translation.copy()
    a, b = (E - S).length, (W - E).length
    d = min(max((target - S).length, abs(a - b) + 1e-4), a + b - 1e-4)
    axis = (target - S).normalized()
    # the elbow on the circle of solutions, on the side of the pole
    x = (a * a - b * b + d * d) / (2 * d); r = math.sqrt(max(a * a - x * x, 0.0))
    pv = (pole - S); pv = (pv - axis * pv.dot(axis)).normalized()
    E2 = S + axis * x + pv * r
    _aim(arm, up, E, E2)
    W1 = _world(arm, ha).translation.copy()
    _aim(arm, fo, W1, S + axis * d)


def ik_leg(arm, side, target, pole, keep_foot=True):
    """Two-bone IK on a leg (thigh, calf): the ankle on `target`, the knee bent toward `pole`. The foot keeps the
    world orientation it had (flat on the floor stays flat), unless keep_foot is False."""
    th, ca, ft = (arm.pose.bones[f'Bip01 {side} {b}'] for b in ('Thigh', 'Calf', 'Foot'))
    F = _world(arm, ft).to_3x3().copy()
    S = _world(arm, th).translation.copy(); E = _world(arm, ca).translation.copy(); A = _world(arm, ft).translation.copy()
    a, b = (E - S).length, (A - E).length
    d = min(max((target - S).length, abs(a - b) + 1e-4), a + b - 1e-4)
    axis = (target - S).normalized()
    x = (a * a - b * b + d * d) / (2 * d); r = math.sqrt(max(a * a - x * x, 0.0))
    pv = (pole - S); pv = (pv - axis * pv.dot(axis)).normalized()
    _aim(arm, th, E, S + axis * x + pv * r)
    _aim(arm, ca, _world(arm, ft).translation.copy(), S + axis * d)
    if keep_foot:
        p = _world(arm, ft).translation.copy()
        _set_world(arm, ft, Matrix.Translation(p) @ F.to_4x4())


def shift_root(arm, d):
    """Move the whole body by the world vector d (the root bone; everything rides on it): a person lowered into a
    lounge chair lower than the clip's."""
    root = next(pb for pb in arm.pose.bones if pb.parent is None)
    M = _world(arm, root); pb_M = Matrix.Translation(Vector(d)) @ M
    root.matrix = arm.matrix_world.inverted() @ pb_M
    bpy.context.view_layer.update()


def _pose(arm):
    """The pose now: every bone's local rotation, and the root's armature-space matrix."""
    root = next(pb for pb in arm.pose.bones if pb.parent is None)
    return {pb.name: pb.rotation_quaternion.copy() for pb in arm.pose.bones}, root.matrix.copy()


def _mix(p, q, w):
    """Blend two poses (from _pose) by w (0 = p, 1 = q): rotations slerped, the root's matrix too."""
    rot = {k: p[0][k].slerp(q[0][k], w) for k in p[0]}
    (ta, ra, sa), (tb, rb, sb) = p[1].decompose(), q[1].decompose()
    root = Matrix.LocRotScale(ta.lerp(tb, w), ra.slerp(rb, w), sa.lerp(sb, w))
    return rot, root


def sequence(arm, base, name, segments, overlay=None, blend=0.6):
    """One long act from several clips played in turn, each carried to where the last left off. A segment is a dict:
    src (action), f0 (its first frame), dur (seconds), rate (1), at (Matrix, world: where its root goes, or a
    function of t, the segment's own seconds, returning one: a walk carried along a path), blend (seconds of crossfade
    into it). overlay(t, seg_index, local_t) may adjust the pose before it is keyed (IK, a look, a pointing arm).
    Returns the act (frames from base's first frame)."""
    sc = bpy.context.scene; A = arm.matrix_world.copy(); Ai = A.inverted()
    root = next(pb for pb in arm.pose.bones if pb.parent is None)
    t0s, t = [], 0.0
    for s in segments: t0s.append(t); t += s['dur']
    total = t; f0 = int(base.frame_range[0]); n = int(round(total * FPS))

    def at(k, lt):
        s = segments[k]; pose_at(arm, s['src'], s['f0'] + min(lt, s['dur'] + s.get('hold', 0.0)) * FPS * s.get('rate', 1.0))
        rot, M = _pose(arm)
        W = s['at'](lt) if callable(s['at']) else s['at']
        return rot, Ai @ W @ A @ M
    act = base.copy(); act.name = name; act.use_fake_user = True
    for f in range(n + 1):
        t = f / FPS
        k = max(i for i, t0 in enumerate(t0s) if t0 <= t + 1e-9) if t < total else len(segments) - 1
        lt = t - t0s[k]; pose = at(k, lt)
        bl = segments[k].get('blend', blend)
        if k > 0 and lt < bl:                                   # crossfade from where the last segment would be now
            w = lt / bl; w = w * w * (3 - 2 * w)
            pose = _mix(at(k - 1, t - t0s[k - 1]), pose, w)
        arm.animation_data.action = act
        if act.slots and arm.animation_data.action_slot is None: arm.animation_data.action_slot = act.slots[0]
        sc.frame_set(f0 + f)
        for b, q in pose[0].items(): arm.pose.bones[b].rotation_quaternion = q
        root.matrix = pose[1]
        bpy.context.view_layer.update()
        if overlay: overlay(t, k, lt)
        root.keyframe_insert('location', frame=f0 + f)
        for pb in arm.pose.bones: pb.keyframe_insert('rotation_quaternion', frame=f0 + f)
    for _, fc in _fcurves(act):
        for kp in [kp for kp in fc.keyframe_points if not f0 <= kp.co[0] <= f0 + n][::-1]: fc.keyframe_points.remove(kp)
        fc.update()
    act.frame_range = (f0, f0 + n)
    cine.log('sequence', name, f'{total:.1f} s', len(segments), 'segments')
    return act


def path(pts):
    """A smooth path over the floor through points (Catmull-Rom): returns (at, length), at(s) giving the point s metres
    along it and the tangent there. A walk is an in-place clip carried along one (see `walk_along`)."""
    P = [Vector((p[0], p[1], 0)) for p in pts]; P = [P[0]] + P + [P[-1]]
    samples = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(24):
            t = k / 24; t2, t3 = t * t, t * t * t
            samples.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    samples.append(P[-2])
    acc = [0.0]
    for a, b in zip(samples, samples[1:]): acc.append(acc[-1] + (b - a).length)
    L = acc[-1]
    def at(s):
        s = min(max(s, 0.0), L)
        i = next((i for i in range(1, len(acc)) if acc[i] >= s), len(acc) - 1)
        w = (s - acc[i - 1]) / max(acc[i] - acc[i - 1], 1e-6)
        p = samples[i - 1].lerp(samples[i], w)
        j0, j1 = max(i - 3, 0), min(i + 2, len(samples) - 1)
        tng = (samples[j1] - samples[j0]); tng = tng.normalized() if tng.length > 1e-6 else Vector((1, 0, 0))
        return p, tng
    return at, L


def walk_along(arm, walk, f0, speed, route):
    """A sequence segment's carrier for an in-place walk clip following `route` (from `path`): a function of the
    segment's own seconds returning the world matrix that sets the walker on the path, facing along it."""
    hw, pw = heading(arm, walk, f0); at, L = route
    def M(lt):
        p, t = at(lt * speed)
        return carry(pw, hw, p, t)
    return M


def heading(arm, action, frame):
    """Where the body faces at a frame of an action (world, horizontal), and the pelvis there."""
    pose_at(arm, action, frame)
    return forward(arm), _world(arm, arm.pose.bones['Bip01 Pelvis']).translation.copy()


def carry(p_from, h_from, p_to, h_to):
    """The world matrix that moves a body at p_from facing h_from to p_to facing h_to (turning about the vertical)."""
    a = math.atan2(h_to.y, h_to.x) - math.atan2(h_from.y, h_from.x)
    p_from = Vector((p_from.x, p_from.y, 0)); p_to = Vector((p_to.x, p_to.y, 0))
    return Matrix.Translation(p_to) @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Translation(-p_from)


def desk_work(arm, base, left, right, frames, seed=1, name=None, facing=None):
    """MDR refining over the seated clip `base`: the left hand taps the keys in bursts, the right hand rolls the
    trackball (busier while the keys rest), the head drifts between screen and keys. Every motion has a whole
    number of cycles over the clip, so the action loops without a seam. left/right: world wrist targets."""
    import random
    rnd = random.Random(seed)
    sc = bpy.context.scene
    fwd = (facing or Vector((0, 1, 0))).normalized(); side = Vector((fwd.y, -fwd.x, 0))  # the worker's right
    act = base.copy(); act.name = name or f'{arm.name}_work'; act.use_fake_user = True
    pose_at(arm, act, frames[0])
    f0, f1 = frames; n = f1 - f0; T = n / FPS
    left, right = Vector(left), Vector(right)
    k = lambda per: max(1, round(T / per))                               # whole cycles of about `per` seconds
    ph = [rnd.random() * 6.283 for _ in range(12)]
    kb, kb2, ks, kt, kr, kh, kh2, kp = k(7.5), k(3.3), k(5.0), k(1 / 2.6), k(1 / 0.75), k(9.0), k(4.1), k(6.3)
    bones = [arm.pose.bones[f'Bip01 {s} {b}'] for s in 'LR' for b in ('UpperArm', 'Forearm')]
    head = arm.pose.bones['Bip01 Head']
    for f in range(f0, f1 + 1):
        sc.frame_set(f); bpy.context.view_layer.update()
        u = (f - f0) / n * 2 * math.pi
        burst = min(1.0, max(0.0, 0.45 + 0.65 * math.sin(kb * u + ph[0]) + 0.3 * math.sin(kb2 * u + ph[1])))
        tap = max(0.0, math.sin(kt * u + ph[2])) ** 6 * burst
        tL = left + side * (0.014 * math.sin(ks * u + ph[3])) + fwd * (0.008 * math.sin(2 * ks * u + ph[4])) + Vector((0, 0, 0.007 * tap + 0.006 * (1 - burst)))
        roll = 0.25 + 0.75 * (1 - 0.7 * burst); a = kr * u + ph[5]
        tR = right + (side * math.cos(a) + fwd * math.sin(a)) * 0.007 * roll
        for s, tgt in (('L', tL), ('R', tR)):
            out = side if s == 'R' else -side
            ik2(arm, s, tgt, tgt + out * 0.35 - fwd * 0.25 - Vector((0, 0, 0.45)))
        for pb in bones: pb.keyframe_insert('rotation_quaternion', frame=f)
        # the head: small turns between the screen and the keys, about the head joint
        yaw = math.radians(4.5 * math.sin(kh * u + ph[6]) + 2.0 * math.sin(kh2 * u + ph[7]))
        pitch = math.radians(2.5 * math.sin(kp * u + ph[8]) + 3.0 * burst - 1.5)
        Mh = _world(arm, head); c = Mh.translation.copy()
        R = Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Rotation(pitch, 4, side)
        _set_world(arm, head, Matrix.Translation(c) @ R @ Matrix.Translation(-c) @ Mh)
        head.keyframe_insert('rotation_quaternion', frame=f)
    return act



# ---------------------------------------------------------------- layering and authored acts
UPPER = ('Clavicle', 'UpperArm', 'Forearm', 'Hand', 'Finger', 'Neck', 'Head')


def _channelbag(action):
    return next(cb for layer in action.layers for strip in layer.strips for cb in strip.channelbags)


def fit_time(action, f0, f1):
    """Stretch an action's keys so it spans exactly f0..f1 (a whole number of its own cycles, made to match another
    clip's length: both then loop together without a seam)."""
    a0, a1 = action.frame_range; k = (f1 - f0) / max(a1 - a0, 1e-6)
    for cb, fc in _fcurves(action):
        for p in fc.keyframe_points:
            for attr in ('co', 'handle_left', 'handle_right'):
                v = getattr(p, attr); v[0] = f0 + (v[0] - a0) * k
        fc.update()
    action.frame_range = (f0, f1)


def layer(base, top, keys=UPPER, name=None):
    """A new action: `base` everywhere, but the bones whose names contain one of `keys` move as in `top` (fitted to
    base's span first). Seated base, standing talk: a man talking with his hands in an armchair."""
    act = base.copy(); act.name = name or f'{base.name}+{top.name}'; act.use_fake_user = True
    fit_time(top, *base.frame_range)
    cb = _channelbag(act)
    hit = lambda fc: '"' in fc.data_path and any(k in fc.data_path.split('"')[1] for k in keys)
    for fc in [fc for fc in cb.fcurves if hit(fc)]: cb.fcurves.remove(fc)
    for _, fc in _fcurves(top):
        if not hit(fc): continue
        new = cb.fcurves.new(fc.data_path, index=fc.array_index); new.keyframe_points.add(len(fc.keyframe_points))
        for src, dst in zip(fc.keyframe_points, new.keyframe_points):
            dst.co = src.co; dst.handle_left = src.handle_left; dst.handle_right = src.handle_right; dst.interpolation = src.interpolation
        new.update()
    return act


def envelope(t, T, rise=1.6, fall=1.6):
    """0 -> 1 over `rise` seconds, held, 1 -> 0 over the last `fall` seconds of T: smooth at both ends."""
    def s(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
    return s(t / rise) * s((T - t) / fall)


def bend(arm, bone, axis, angle):
    """Turn a bone about its own head by `angle` radians about the world `axis` (a spine leaning forward)."""
    pb = arm.pose.bones[bone]; M = _world(arm, pb); c = M.translation.copy()
    _set_world(arm, pb, Matrix.Translation(c) @ Matrix.Rotation(angle, 4, axis) @ Matrix.Translation(-c) @ M)


def custom_act(arm, base, frames, name, step, bones):
    """An authored act over a base clip: for every frame the base pose is evaluated, `step(f, t)` adjusts it (IK,
    bends), and `bones` are keyed. Built like desk_work, so whatever loops in the base still loops."""
    act = base.copy(); act.name = name; act.use_fake_user = True
    pose_at(arm, act, frames[0]); sc = bpy.context.scene
    for f in range(frames[0], frames[1] + 1):
        sc.frame_set(f); bpy.context.view_layer.update()
        step(f, (f - frames[0]) / FPS)
        for b in bones:
            pb = arm.pose.bones[b]; pb.keyframe_insert('rotation_quaternion', frame=f)
            if pb.parent is None: pb.keyframe_insert('location', frame=f)   # the root carries the body (a seat's drop)
    # the act is only its own frames: the rest of the base would make a one-shot run on (and its props linger)
    for _, fc in _fcurves(act):
        for k in [k for k in fc.keyframe_points if not frames[0] <= k.co[0] <= frames[1]][::-1]: fc.keyframe_points.remove(k)
        fc.update()
    act.frame_range = frames
    return act


def forward(arm):
    """Where the body faces now (world, horizontal), measured from heel to toe of both feet: an armature imports with
    its own rotation, so its axes do not say which way the person faces."""
    f = Vector()
    for s in 'LR':
        f += _world(arm, arm.pose.bones[f'Bip01 {s} Toe0']).translation - _world(arm, arm.pose.bones[f'Bip01 {s} Foot']).translation
    f.z = 0; return f.normalized()


def face(arm, direction):
    """Turn the avatar about the vertical so it faces `direction` (world, horizontal)."""
    bpy.context.view_layer.update(); f = forward(arm); d = Vector(direction); d.z = 0; d.normalize()
    arm.rotation_euler.z += math.atan2(d.y, d.x) - math.atan2(f.y, f.x)
    bpy.context.view_layer.update()


def body_frame(arm):
    """The seated or standing body's frame now: pelvis position, forward, right and up (world)."""
    pel = _world(arm, arm.pose.bones['Bip01 Pelvis']).translation.copy()
    fwd = arm.get('fwd'); fwd = Vector(fwd) if fwd else forward(arm)
    up = Vector((0, 0, 1)); right = fwd.cross(up).normalized()
    return pel, fwd, right, up


def add_glasses(arm, mesh, lens_r=0.017, mat=None):
    """Small round pince-nez glasses on the eyes, skinned to the head and joined into the body mesh (rest pose)."""
    import bmesh
    J = _joints(arm); L, R = J['Bip01 LEye'], J['Bip01 REye']; mid = (L + R) / 2
    fwd = J['Bip01 MNose'] - mid; fwd.z = 0; fwd.normalize(); side = (L - R).normalized()   # the face's own axes
    bm = bmesh.new()
    def disc(c):
        ring = [bm.verts.new(c + (side * math.cos(a) + Vector((0, 0, 1)) * math.sin(a)) * lens_r) for a in (i * 2 * math.pi / 20 for i in range(20))]
        back = [bm.verts.new(v.co - fwd * 0.002) for v in ring]
        bm.faces.new(ring); bm.faces.new(list(reversed(back)))
        for i in range(20): bm.faces.new((ring[i], back[i], back[(i + 1) % 20], ring[(i + 1) % 20]))
    off = fwd * 0.03                                                  # clear of the lids and brows, on the bridge of the nose
    disc(L + off); disc(R + off)
    a, b = L + off - side * lens_r, R + off + side * lens_r           # the bridge between the inner rims
    br = [bm.verts.new(p) for p in (a + Vector((0, 0, 0.004)), b + Vector((0, 0, 0.004)), b + Vector((0, 0, 0.006)), a + Vector((0, 0, 0.006)))]
    bm.faces.new(br)
    me = bpy.data.meshes.new('glasses'); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new('glasses', me); [c.objects.link(ob) for c in mesh.users_collection]
    ob.matrix_world = mesh.matrix_world.copy(); ob.data.transform(mesh.matrix_world.inverted()); ob.matrix_world = mesh.matrix_world
    if mat: me.materials.append(mat)
    vg = ob.vertex_groups.new(name='Bip01 Head'); vg.add(list(range(len(me.vertices))), 1.0, 'REPLACE')
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.join()
    cine.log('glasses on', mesh.get('person', mesh.name))


def _join_to_head(mesh, bm, name, mats):
    """A rest-pose bmesh (world space) made an object skinned wholly to the head and joined into the body mesh."""
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); [c.objects.link(ob) for c in mesh.users_collection]
    for m in mats: me.materials.append(m)
    ob.matrix_world = mesh.matrix_world.copy(); me.transform(mesh.matrix_world.inverted()); ob.matrix_world = mesh.matrix_world
    vg = ob.vertex_groups.new(name='Bip01 Head'); vg.add(list(range(len(me.vertices))), 1.0, 'REPLACE')
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.join()


def _wire(bm, pts, r, closed=False, seg=6):
    """A thin round wire along points (a glasses' rim, a temple)."""
    pts = [Vector(p) for p in pts]; n = len(pts); rings = []
    for i, p in enumerate(pts):
        a = pts[(i - 1) % n] if closed or i > 0 else p; b = pts[(i + 1) % n] if closed or i < n - 1 else p
        t = (b - a).normalized(); u = t.orthogonal().normalized(); v = t.cross(u)
        rings.append([bm.verts.new(p + (u * math.cos(2 * math.pi * k / seg) + v * math.sin(2 * math.pi * k / seg)) * r) for k in range(seg)])
    for i in range(n if closed else n - 1):
        a, b = rings[i], rings[(i + 1) % n]
        for k in range(seg): bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))


def add_frames(arm, mesh, mat, w=0.05, h=0.033, r=0.0012, corner=0.008, tilt=4.0):
    """Wire-rimmed rectangular glasses (Walt's): two rounded-rectangle rims `w` x `h` before the eyes, a bridge, and the
    temples back over the ears; skinned to the head and joined into the body mesh (rest pose)."""
    import bmesh
    J = _joints(arm); L, R = J['Bip01 LEye'], J['Bip01 REye']; mid = (L + R) / 2
    fwd = J['Bip01 MNose'] - mid; fwd.z = 0; fwd.normalize(); side = (L - R).normalized(); up = Vector((0, 0, 1))
    up = (Matrix.Rotation(math.radians(tilt), 3, side) @ up).normalized()          # the rims lean back a little at the top
    bm = bmesh.new(); off = fwd * 0.03
    def rim(c):
        pts = []
        for qx, qy, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
            cc = c + side * qx * (w / 2 - corner) + up * qy * (h / 2 - corner)
            for k in range(5):
                a = math.radians(a0 + 90 * k / 4); pts.append(cc + (side * math.cos(a) + up * math.sin(a)) * corner)
        _wire(bm, pts, r, closed=True)
    cl, cr = L + off + side * 0.003, R + off - side * 0.003
    rim(cl); rim(cr)
    a, b = cr + side * (w / 2), cl - side * (w / 2)
    _wire(bm, [a + up * 0.006, (a + b) / 2 + up * 0.009 + fwd * 0.002, b + up * 0.006], r)   # the bridge
    for c, s in ((cl, 1), (cr, -1)):                                                         # the temples, to the ears
        e = c + side * s * (w / 2) + up * (h / 2 - 0.006)
        ear = Vector((mid.x, mid.y, mid.z)) + side * s * 0.074 - fwd * 0.08 + up * 0.0
        _wire(bm, [e, e - fwd * 0.012 + side * s * 0.004, ear, ear - fwd * 0.012 - up * 0.014], r * 1.1)
    _join_to_head(mesh, bm, 'frames', [mat])
    cine.log('frames on', mesh.get('person', mesh.name))


def beanie(arm, mesh, knit, rim=None, axis_tilt=22.0, brim=98.0, t=0.009, cuff=16.0, stripe=3.5, res=(48, 24)):
    """A close-fitting knit cap over the skull (Jesse's), skinned to the head: a dome of rings about an axis leaning
    back by `axis_tilt` degrees, its brim the cone `brim` degrees from that axis (low over the forehead, lower behind,
    at the tops of the ears); every point cast down onto the head and set `t` out; the cuff (the last `cuff` degrees)
    thicker, a `stripe` of `rim` colour at its edge."""
    import bmesh
    from mathutils.bvhtree import BVHTree
    J = _joints(arm); eye = (J['Bip01 LEye'] + J['Bip01 REye']) / 2
    c = Vector((eye.x, eye.y + 0.05, eye.z + 0.01))                       # the skull's middle (the avatar faces -y)
    n = Vector((0, math.sin(math.radians(axis_tilt)), math.cos(math.radians(axis_tilt))))
    side = Vector((1, 0, 0)); back = n.cross(side).normalized()
    deps = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(mesh, deps)                                    # in the mesh's own space
    Mi = mesh.matrix_world.inverted(); M = mesh.matrix_world
    nu, nv = res; bm = bmesh.new(); rings = []
    for j in range(nv + 1):
        v = math.radians(brim) * (1 - j / nv); row = []
        for i in range(nu):
            u = 2 * math.pi * i / nu
            d = (n * math.cos(v) + (side * math.cos(u) + back * math.sin(u)) * math.sin(v)).normalized()
            o = Mi @ (c + d * 0.3); dl = Mi.to_3x3() @ -d                   # the mesh's own units (imported at 0.01)
            hit = bvh.ray_cast(o, dl.normalized(), dl.length * 0.4)
            p = (M @ hit[0]) if hit[0] is not None else c + d * 0.1
            deg = math.degrees(v); tt = t + 0.004 * min(max((deg - (brim - cuff)) / 4.0, 0.0), 1.0)   # the cuff, turned up
            row.append(bm.verts.new(p + d * tt))
        rings.append(row)
    top = bm.verts.new(c + n * max((r.co - c).length for r in rings[-1]))
    faces = []
    for j in range(nv):
        a, b = rings[j], rings[j + 1]
        for i in range(nu): faces.append((bm.faces.new((a[i], a[(i + 1) % nu], b[(i + 1) % nu], b[i])), j))
    for i in range(nu): faces.append((bm.faces.new((rings[-1][i], rings[-1][(i + 1) % nu], top)), nv))
    inner = [bm.verts.new(c + (v.co - c) * 0.96) for v in rings[0]]          # the brim's turned edge, in toward the head
    for i in range(nu): faces.append((bm.faces.new((inner[i], inner[(i + 1) % nu], rings[0][(i + 1) % nu], rings[0][i])), -1))
    for f, j in faces:
        f.smooth = True
        deg = brim * (1 - max(j, 0) / nv)
        f.material_index = 1 if rim is not None and (j < 0 or deg > brim - stripe) else 0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    _join_to_head(mesh, bm, 'beanie', [knit] + ([rim] if rim is not None else []))
    cine.log('beanie on', mesh.get('person', mesh.name))


# ---------------------------------------------------------------- hands
FINGERS = {'thumb': '0', 'index': '1', 'middle': '2', 'ring': '3', 'pinky': '4'}
SHAPES = {   # curl per finger (degrees for each of its three joints): a fist, a pointing hand, a finger gun
    'fist': {'thumb': (20, 30, 30), 'index': (70, 90, 60), 'middle': (75, 95, 60), 'ring': (75, 95, 60), 'pinky': (75, 90, 60)},
    'point': {'thumb': (25, 35, 30), 'index': (0, 4, 4), 'middle': (75, 95, 60), 'ring': (78, 95, 60), 'pinky': (80, 90, 60)},
    'gun': {'thumb': (-18, -6, 0), 'index': (0, 0, 0), 'middle': (72, 95, 60), 'ring': (76, 95, 60), 'pinky': (78, 90, 60)},
}


def _palm(arm, side):
    """The palm's normal (world): the side the fingers close toward. The plane of the wrist and the index and little
    finger's knuckles; of its two sides, the one the thumb's tip lies on (it rests in front of the palm)."""
    P = lambda b: _world(arm, arm.pose.bones[f'Bip01 {side} {b}']).translation.copy()
    H = P('Hand'); n = (P('Finger1') - H).cross(P('Finger4') - H).normalized()
    return n if (P('Finger02') - H).dot(n) >= 0 else -n


def hand_shape(arm, side, shape, w=1.0):
    """Close a hand's fingers into `shape` (SHAPES) by the fraction w: each joint turns about the axis across the
    finger, toward the palm (Biped finger bones do not bend about one local axis: the axis is taken in the world)."""
    if w <= 0: return
    palm = _palm(arm, side)
    for finger, angles in SHAPES[shape].items():
        f = FINGERS[finger]; chain = [f'Bip01 {side} Finger{f}{s}' for s in ('', '1', '2')]
        for k, (b, ang) in enumerate(zip(chain, angles)):
            if not ang or b not in arm.pose.bones: continue
            pb = arm.pose.bones[b]; base = _world(arm, pb).translation.copy()
            nxt = _world(arm, arm.pose.bones[chain[k + 1]]).translation.copy() if k < 2 else base + (base - _world(arm, pb.parent).translation)
            d = (nxt - base).normalized()
            ax = d.cross(palm)                                              # turning about it carries d toward the palm
            if ax.length < 1e-6: continue
            bend(arm, b, ax.normalized(), math.radians(ang) * w)


def point_at(arm, side, target, w=1.0, reach=0.42, jab=0.0, shape='point', drop=0.25, out=0.22):
    """An arm thrown out toward `target` (world) by the fraction w, the elbow kept bent (`reach` metres from the
    shoulder to the wrist, plus `jab`), the hand turned so its index finger runs at the target, the fingers in `shape`
    ('point', or 'gun' for a finger gun: the thumb cocked up)."""
    if w <= 0: return
    sh = _world(arm, arm.pose.bones[f'Bip01 {side} UpperArm']).translation.copy()
    H0 = _world(arm, arm.pose.bones[f'Bip01 {side} Hand']).translation.copy()
    lat = sh - _world(arm, arm.pose.bones['Bip01 Neck']).translation; lat.z = 0; lat.normalize()   # the shoulder's outward side
    d = (Vector(target) - sh).normalized()
    tgt = H0.lerp(sh + d * (reach + jab), w)
    ik2(arm, side, tgt, tgt - Vector((0, 0, drop)) + lat * out)                 # the elbow down and out
    hand = arm.pose.bones[f'Bip01 {side} Hand']; H = _world(arm, hand).translation.copy()
    hand_shape(arm, side, shape, w)
    tip = _world(arm, arm.pose.bones[f'Bip01 {side} Finger12']).translation.copy()
    q = (tip - H).normalized().rotation_difference((Vector(target) - H).normalized())
    M = _world(arm, hand)
    _set_world(arm, hand, Matrix.Translation(H) @ Quaternion().slerp(q, w).to_matrix().to_4x4() @ Matrix.Translation(-H) @ M)
    if shape == 'gun': palm_to(arm, side, -lat, 0.8 * w)                     # the palm turned in, the thumb up


def palm_to(arm, side, want, w=1.0):
    """Turn a hand about its forearm so its palm faces `want` (world), by the fraction w: palms up for an offer,
    palms together for steepled fingers. The palm's normal comes from the thumb and middle finger."""
    hand, fo = arm.pose.bones[f'Bip01 {side} Hand'], arm.pose.bones[f'Bip01 {side} Forearm']
    H = _world(arm, hand).translation.copy(); d = (H - _world(arm, fo).translation).normalized()
    th = _world(arm, arm.pose.bones[f'Bip01 {side} Finger0']).translation - H
    mid = _world(arm, arm.pose.bones[f'Bip01 {side} Finger2']).translation - H
    p = (th.cross(mid) if side == 'R' else mid.cross(th)).normalized()
    pp, wp = p - d * p.dot(d), Vector(want) - d * Vector(want).dot(d)
    if pp.length < 1e-6 or wp.length < 1e-6: return
    ang = math.atan2(pp.cross(wp).dot(d), pp.dot(wp))
    M = _world(arm, hand)
    _set_world(arm, hand, Matrix.Translation(H) @ Matrix.Rotation(ang * w, 4, d) @ Matrix.Translation(-H) @ M)


def pose_at(arm, action, frame):
    arm.animation_data_create(); arm.animation_data.action = action
    if arm.animation_data.action_slot is None and action.slots: arm.animation_data.action_slot = action.slots[0]
    bpy.context.scene.frame_set(int(frame)); bpy.context.view_layer.update()


def anchor(arm, act, ref):
    """Shift an act's root (horizontally) so its first frame starts exactly where `ref`'s does: mocap actors did not
    stand on the same spot for every clip, and the web crossfades acts in place."""
    pel = arm.pose.bones['Bip01 Pelvis']
    pose_at(arm, ref, ref.frame_range[0]); p0 = (arm.matrix_world @ pel.matrix).translation.copy()
    pose_at(arm, act, act.frame_range[0]); p1 = (arm.matrix_world @ pel.matrix).translation.copy()
    d = p0 - p1; d.z = 0
    if d.length < 1e-4: return act
    root = next(b for b in arm.data.bones if b.parent is None)
    local = (arm.matrix_world.to_3x3() @ root.matrix_local.to_3x3()).inverted() @ d
    for cb, fc in _fcurves(act):
        if fc.data_path == f'pose.bones["{root.name}"].location':
            for k in fc.keyframe_points:
                for attr in ('co', 'handle_left', 'handle_right'): getattr(k, attr)[1] += local[fc.array_index]
            fc.update()
    cine.log('anchored', act.name, f'{d.length * 100:.1f} cm')
    return act


def check_acts(arm, acts, spot=0.05, turn=15.0, drift=0.3, roam=(), pelvis='Bip01 Pelvis'):
    """Every act must begin where the first act begins (the same spot within `spot` m, the same heading within `turn`
    degrees) and stay near there (`drift` m): the web crossfades acts in place, so an act baked in another frame
    makes the person jump. An act named in `roam` may wander (a walk out of the room and back), but must end where it
    began. Raises with the culprits. `pelvis`: the bone that carries the body (an animal's own root)."""
    pelvis = arm.pose.bones[pelvis]
    def at(action, f):
        pose_at(arm, action, f); M = arm.matrix_world @ pelvis.matrix; return M.translation.copy(), M.to_quaternion()
    flat = lambda v: math.hypot(v.x, v.y)
    (ref_name, ref), bad = next(iter(acts.items())), []
    p0, q0 = at(ref, ref.frame_range[0])
    for name, a in acts.items():
        f0, f1 = int(a.frame_range[0]), int(a.frame_range[1])
        p, q = at(a, f0)
        ang = math.degrees(q0.rotation_difference(q).angle); ang = min(ang, 360 - ang)
        far = max(flat(at(a, f)[0] - p) for f in range(f0, f1 + 1, 5))
        if name in roam: far = flat(at(a, f1)[0] - p)          # it may go where it likes, but comes back
        if flat(p - p0) > spot or ang > turn or far > drift:
            bad.append(f"{name}: starts {flat(p - p0) * 100:.0f} cm and {ang:.0f}° from '{ref_name}', {'ends' if name in roam else 'wanders'} {far * 100:.0f} cm")
    if bad: raise RuntimeError(f"{arm.get('person', arm.name)}: acts out of place: " + '; '.join(bad))
    cine.log('acts in place', arm.get('person', arm.name), ', '.join(acts))


def export_person(arm, mesh, acts, path, image_size=1024, roam=(), pelvis='Bip01 Pelvis'):
    """One glTF per person: body, rig and every act as its own animation (NLA tracks, each named after its act).
    The acts are checked first (check_acts): a person whose acts do not share one spot is never exported."""
    check_acts(arm, acts, roam=roam, pelvis=pelvis)
    for slot in mesh.material_slots:
        for nd in slot.material.node_tree.nodes:
            if nd.type == 'TEX_IMAGE' and nd.image and nd.image.size[0] > image_size: nd.image.scale(image_size, image_size)
    ad = arm.animation_data_create(); ad.action = None
    for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
    for act_name, action in acts.items():
        tr = ad.nla_tracks.new(); tr.name = act_name
        st = tr.strips.new(act_name, int(action.frame_range[0]), action)
        if action.slots and getattr(st, 'action_slot', None) is None: st.action_slot = action.slots[0]
    bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); mesh.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_animations=True, export_animation_mode='NLA_TRACKS',
                              export_anim_slide_to_zero=True, export_force_sampling=True, export_frame_step=2, export_optimize_animation_size=True,
                              export_def_bones=True, export_leaf_bone=False, export_image_format='WEBP', export_image_quality=85,
                              export_extras=True, export_yup=True)
    for t in list(ad.nla_tracks): ad.nla_tracks.remove(t)
    cine.log('person', mesh.get('person'), f'{len(acts)} acts', f'{os.path.getsize(path) / 1e6:.1f} MB')
