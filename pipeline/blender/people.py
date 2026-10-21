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


def reproportion(arm, mesh, k):
    """Change the length of limb segments, mesh and skeleton together, before any clip is retargeted: `k` maps a bone
    name to the factor for the segment from its head to its child's (e.g. {'Thigh': 0.5, 'Calf': 0.55}, both sides).
    Every bone keeps its rest orientation (only heads move), so clips still apply; a vertex moves with its bones'
    segments, blended by its skin weights. Sets arm['leg_k'] (the legs' new length over the old) for `retarget`."""
    J = {b.name: (arm.matrix_world @ b.head_local).copy() for b in arm.data.bones}
    kids = {b.name: [c.name for c in b.children] for b in arm.data.bones}
    def main_child(b):
        c = kids[b]
        if not c: return None
        return max(c, key=lambda n: (J[n] - J[b]).length) if len(c) > 1 and not any(s in b for s in ('Hand',)) else c[0]
    delta = {}
    def walk(b, d):
        delta[b] = d
        f = k.get(b.split(' ')[-1])
        for c in kids[b]:                                          # a scaled segment carries all its children's heads
            walk(c, d + (J[c] - J[b]) * (f - 1.0) if f is not None else d)
    root = next(b.name for b in arm.data.bones if b.parent is None); walk(root, Vector())
    # the feet stay on the floor: everything comes down by what the legs lost
    drop = Vector((0, 0, (delta['Bip01 L Foot'].z + delta['Bip01 R Foot'].z) / 2))
    for b in delta: delta[b] = delta[b] - drop
    # the mesh: each vertex follows its bones; on a scaled segment, the share of the change by where it lies along it
    me = mesh.data; M = mesh.matrix_world; Mi = M.inverted()
    names = [g.name for g in mesh.vertex_groups]
    for v in me.vertices:
        p = M @ v.co; tot, w_sum = Vector(), 0.0
        for g in v.groups:
            b = names[g.group]
            if b not in delta or g.weight <= 0: continue
            d = delta[b]; ch = main_child(b)
            if ch is not None and b.split(' ')[-1] in k:
                seg = J[ch] - J[b]; t = min(max((p - J[b]).dot(seg) / max(seg.length_squared, 1e-9), 0.0), 1.0)
                d = delta[b] + (delta[ch] - delta[b]) * t
            tot += d * g.weight; w_sum += g.weight
        if w_sum > 0: v.co = Mi @ (p + tot / w_sum)
    _fresh_normals(mesh)
    # the skeleton: heads (and tails, keeping each bone's direction) moved by their deltas
    bpy.context.view_layer.objects.active = arm; arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    Ai = arm.matrix_world.inverted().to_3x3()
    for eb in arm.data.edit_bones:
        d = Ai @ delta.get(eb.name, Vector())
        eb.head = eb.head + d; eb.tail = eb.tail + d
    bpy.ops.object.mode_set(mode='OBJECT')
    J2 = {b.name: (arm.matrix_world @ b.head_local) for b in arm.data.bones}
    leg = lambda JJ: (JJ['Bip01 L Thigh'] - JJ['Bip01 L Foot']).length
    arm['leg_k'] = leg(J2) / leg(J)
    bpy.context.view_layer.update()
    cine.log('reproportion', mesh.get('person', mesh.name), {kk: round(v, 2) for kk, v in k.items()}, f"legs x{arm['leg_k']:.2f}")


def swap_head(arm, mesh, glb, keep, front, eyes, cut=0.0, fan_cut=-0.03, decimate=None, skin=None, thin=None, keep_cards=False, tone=None, neck_skin=False, match_neck=False, follow=0.0, scalp=None):
    """Put a sculpted head (a fan's model) on a Rocketbox body: the avatar's own head and hair go above the neck; the
    model's parts named in `keep` (substrings of object names, or all) are joined, turned so its face looks along the
    avatar's (-y; `front` is the model's own facing axis after import, '+y' or '-y'), scaled and moved so its eyes sit
    on the avatar's eye joints (`eyes`: the object whose two clusters are the eyeballs, or two points in the model's
    space), cut below `fan_cut` metres under the neck joint (a bust's shoulders), skinned to the head (the neck below
    the jaw blending into the neck bone) and joined into the body mesh. `cut`: how far above the neck joint the
    avatar's own skin is cut away. `decimate`: {part substring: ratio} thins dense parts (strand hair). `tone`: an RGB
    factor on the model's colour images (a photographed face matched to the body's skin). `neck_skin`: what is dark
    on the model's neck below the jaw (a costume's collar in the photographs) is painted as the neck's own skin.
    `match_neck`: the model's neck below the jaw widens or narrows to meet the body's neck where it was cut.
    `follow` (metres): the body's head is cut that far above the model's own lower edge, round the neck, instead of
    flat at `cut` (a short neck with a slanted edge). `scalp`: the hair painted on the model's scalp recoloured
    (sRGB 0-255). Returns the model's material names (for the export to keep their images)."""
    import bmesh
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=glb)
    new = [o for o in bpy.data.objects if o not in before]
    parts = [o for o in new if o.type == 'MESH' and (keep is None or any(s in o.name for s in keep))]
    for o in new:
        if o not in parts and o.type == 'MESH': bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    for o in parts:
        mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
        if decimate:
            r = next((v for s_, v in decimate.items() if s_ in o.name), None)
            if r:
                md = o.modifiers.new('thin', 'DECIMATE'); md.ratio = r
                with bpy.context.temp_override(object=o, active_object=o): bpy.ops.object.modifier_apply(modifier=md.name)
        if thin:                                                                    # strand hair: keep a share of its strands
            r = next((v for s_, v in thin.items() if s_ in o.name), None)
            if r:
                import random
                rnd = random.Random(7); bmt = bmesh.new(); bmt.from_mesh(o.data)
                bmesh.ops.delete(bmt, geom=[f for f in bmt.faces if rnd.random() > r], context='FACES')
                bmesh.ops.delete(bmt, geom=[v for v in bmt.verts if not v.link_faces], context='VERTS')
                bmt.to_mesh(o.data); bmt.free(); o.data.update()
    for o in [o for o in bpy.data.objects if o.type == 'EMPTY' and o in new]: bpy.data.objects.remove(o, do_unlink=True)
    for o in parts:                                                   # an unlit scan (emission only) becomes a lit surface
        for sl in o.material_slots:
            m = sl.material
            if not m or not m.node_tree or any(n.type == 'BSDF_PRINCIPLED' for n in m.node_tree.nodes): continue
            nt = m.node_tree; img = next((n.image for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image), None)
            for n in list(nt.nodes): nt.nodes.remove(n)
            out = nt.nodes.new('ShaderNodeOutputMaterial'); p = nt.nodes.new('ShaderNodeBsdfPrincipled')
            nt.links.new(p.outputs['BSDF'], out.inputs['Surface'])
            if img is not None: t = nt.nodes.new('ShaderNodeTexImage'); t.image = img; nt.links.new(t.outputs['Color'], p.inputs['Base Color'])
            try: m.surface_render_method = 'DITHERED'; m.blend_method = 'OPAQUE'
            except Exception: pass
            cine.log('unlit material made lit', m.name)
    # the model's eyes, in the world (as imported)
    if isinstance(eyes, str):
        eo = next(o for o in parts if eyes in o.name)
        P = [eo.matrix_world @ v.co for v in eo.data.vertices]
        zmid = (min(p.z for p in P) + max(p.z for p in P)) / 2; P = [p for p in P if p.z >= zmid]   # the eyes, not a neck ring with them
        cx = sum(p.x for p in P) / len(P)
        L = [p for p in P if p.x >= cx]; R_ = [p for p in P if p.x < cx]
        e1, e2 = sum(L, Vector()) / len(L), sum(R_, Vector()) / len(R_)
    else: e1, e2 = Vector(eyes[0]), Vector(eyes[1])
    # the avatar's eyes and facing (-y in the rest pose)
    J = _joints(arm); aL, aR = J['Bip01 LEye'], J['Bip01 REye']
    am = (aL + aR) / 2; ad = (aL - aR).length
    # turn the model about z so its face looks along -y (its eyes then span x); scale to the avatar's eye distance
    rz = math.pi if front == '+y' else 0.0
    Rz = Matrix.Rotation(rz, 4, 'Z')
    m1, m2 = Rz @ e1, Rz @ e2; mm = (m1 + m2) / 2; md_ = (m1 - m2).length
    s = ad / md_
    # level the eye line (a small roll about y) and match the eyes' side order to the avatar's (L at +x)
    ev = (m1 - m2) if (m1 - m2).x * (aL - aR).x > 0 else (m2 - m1)
    roll = math.atan2(ev.z, ev.x) - math.atan2((aL - aR).z, (aL - aR).x)
    Ry = Matrix.Rotation(roll, 4, 'Y')
    T_ = Matrix.Translation(am) @ Ry @ Matrix.Diagonal((s, s, s, 1)) @ Matrix.Translation(-mm) @ Rz
    for o in parts: o.matrix_world = T_ @ o.matrix_world
    bpy.context.view_layer.update()
    # the avatar's own head: its skin above the cut, its eyes and teeth and hair cards
    neck = J['Bip01 Neck']; zc = neck.z + cut
    me = mesh.data; M = mesh.matrix_world
    head_mats = {i for i, sl in enumerate(mesh.material_slots) if sl.material and ('head' in sl.material.name or ('opacity' in sl.material.name and not keep_cards))}
    bm = bmesh.new(); bm.from_mesh(me)
    dead = {f for f in bm.faces if f.material_index in head_mats and min((M @ v.co).z for v in f.verts) > zc}
    if follow:                                                      # the cut follows the model's own lower edge, round the neck
        F_ = [o.matrix_world @ v.co for o in parts for v in o.data.vertices]
        bins = [None] * 36
        for q in F_:
            k_ = int((math.atan2(q.y - neck.y, q.x - neck.x) + math.pi) / (2 * math.pi) * 36) % 36
            if bins[k_] is None or q.z < bins[k_]: bins[k_] = q.z
        def edge_z(q):
            k_ = int((math.atan2(q.y - neck.y, q.x - neck.x) + math.pi) / (2 * math.pi) * 36) % 36
            return (bins[k_] if bins[k_] is not None else zc - follow) + follow
        dead = {f for f in bm.faces if f.material_index in head_mats and (lambda q: q.z > edge_z(q))(M @ f.calc_center_median())}
    # below the cut: a long hair mass modelled down the back, and small pieces of the head's material (a necklace's beads)
    def behind(f):
        q = M @ f.calc_center_median(); r = math.hypot(q.x - neck.x, q.y - neck.y)
        return q.y > neck.y + 0.075 or (q.y > neck.y + 0.01 and r > 0.075)
    dead |= {f for f in bm.faces if f.material_index in head_mats and behind(f)}
    seen = set()
    for f in bm.faces:
        if f in seen or f.material_index not in head_mats: continue
        comp, stack = [], [f]; seen.add(f)
        while stack:
            g = stack.pop(); comp.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h not in seen: seen.add(h); stack.append(h)
        if len(comp) < 80 and max((M @ v.co).z for g in comp for v in g.verts) < neck.z: dead |= set(comp)
    bmesh.ops.delete(bm, geom=list(dead), context='FACES'); bm.to_mesh(me); bm.free(); me.update()
    # the model: everything below the fan cut goes (a bust's shoulders, a collar)
    zf = neck.z + fan_cut
    for o in parts:
        bmf = bmesh.new(); bmf.from_mesh(o.data); W_ = o.matrix_world
        bmesh.ops.delete(bmf, geom=[v for v in bmf.verts if (W_ @ v.co).z < zf], context='VERTS')
        bmf.to_mesh(o.data); bmf.free(); o.data.update()
    # skin: the head bone, the neck bone blended in below the jaw
    jaw = J.get('Bip01 MJaw', J['Bip01 Head']).z - 0.03
    if neck_skin: _neck_skin(parts, jaw)
    if scalp: _scalp_colour(parts, am, scalp)
    if match_neck: _match_neck(mesh, head_mats, parts, zc, jaw)
    for o in parts:
        for vg in list(o.vertex_groups): o.vertex_groups.remove(vg)
        gh, gn = o.vertex_groups.new(name='Bip01 Head'), o.vertex_groups.new(name='Bip01 Neck')
        W_ = o.matrix_world
        for v in o.data.vertices:
            z = (W_ @ v.co).z; t = min(max((jaw - z) / 0.07, 0.0), 1.0)
            if t < 1: gh.add([v.index], 1.0 - t, 'REPLACE')
            if t > 0: gn.add([v.index], t, 'REPLACE')
        for p in o.data.polygons: p.use_smooth = True
    mats = [sl.material.name for o in parts for sl in o.material_slots if sl.material]
    for o in parts:                                               # glTF's default is metallic: skin and hair are not
        for sl in o.material_slots:
            p = next((n for n in sl.material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if sl.material and sl.material.node_tree else None
            if p is None: continue
            for inp in ('Metallic', 'Roughness'):                     # packed metal/rough maps: the exporter cannot split them
                for l in list(p.inputs[inp].links): sl.material.node_tree.links.remove(l)
            p.inputs['Metallic'].default_value = 0.0; p.inputs['Roughness'].default_value = 0.55
            p.inputs['Specular IOR Level'].default_value = 0.4
            if tone:
                for l in p.inputs['Base Color'].links:
                    im = getattr(l.from_node, 'image', None)
                    if im is None or im.get('toned'): continue
                    px = np.empty(len(im.pixels), np.float32); im.pixels.foreach_get(px); px = px.reshape(-1, 4)
                    px[:, :3] = np.clip(px[:, :3] * np.array(tone, np.float32)[None, :], 0, 1)
                    im.pixels.foreach_set(px.ravel()); im.pack(); im['toned'] = 1
    if skin:
        for o in parts:
            for sl in o.material_slots:
                if sl.material and any(k_ in sl.material.name for k_ in skin): sl.material['fan_skin'] = 1
    for o in parts:                                               # a scan's vertex colours: the web multiplies them into the face
        for ca in list(o.data.color_attributes): o.data.color_attributes.remove(ca)
    uvname = mesh.data.uv_layers.active.name                      # a join keeps UV maps by name: give the model's the body's
    for o in parts:
        for l in list(o.data.uv_layers)[1:]: o.data.uv_layers.remove(l)
        if o.data.uv_layers: o.data.uv_layers[0].name = uvname
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.join()
    _fresh_normals(mesh)
    cine.log('head swapped', mesh.get('person', mesh.name), os.path.basename(glb), f'scale {s:.4f}', f'{len(parts)} parts')
    return mats


def _match_neck(mesh, head_mats, parts, zc, jaw):
    """The model's neck meets the body's: below the jaw its vertices move toward the ring of the body's neck at the
    cut (its middle and radius), fully at the cut and below it, where they sit just inside."""
    M = mesh.matrix_world
    av = [M @ mesh.data.vertices[i].co for p in mesh.data.polygons if p.material_index in head_mats for i in p.vertices]
    def ring(P, z0, dz=0.01):
        Q = [q for q in P if abs(q.z - z0) < dz]
        if len(Q) < 8: return None
        c = sum(Q, Vector()) / len(Q); return c, sum(math.hypot(q.x - c.x, q.y - c.y) for q in Q) / len(Q)
    fan = [(o, v, o.matrix_world @ v.co) for o in parts for v in o.data.vertices]
    zr = min(min(w.z for _, _, w in fan) + 0.006, zc - 0.006)                    # where the two necks overlap
    a = ring(av, zr, 0.006); f = ring([w for _, _, w in fan], zr, 0.006)
    if a is None or f is None:
        cine.log('neck rings not found', len(av), len(fan), round(zc, 3), min((w.z for _, _, w in fan), default=0), a is None, f is None); return
    (ca, ra), (cf, rf) = a, f; k = ra / rf
    def sm(e0, e1, x): t = min(max((x - e0) / (e1 - e0), 0.0), 1.0); return t * t * (3 - 2 * t)
    for o, v, w in fan:
        if w.z >= jaw: continue
        t = sm(jaw, min(zr + 0.01, jaw - 0.005), w.z); inner = 1.0 - 0.03 * sm(zc, zc - 0.01, w.z)
        nx = ca.x + (w.x - cf.x) * k * inner; ny = ca.y + (w.y - cf.y) * k * inner
        v.co = o.matrix_world.inverted() @ Vector((w.x + (nx - w.x) * t, w.y + (ny - w.y) * t, w.z))
    for o in parts: o.data.update()
    cine.log(f'neck matched: body r {ra:.3f}, model r {rf:.3f}, centres {(ca - cf).length * 100:.1f} cm apart')


def _uv_fill(m, pts):
    """A polygon (UV pixels) filled into a boolean mask, as a triangle fan."""
    for a, b, c in ((pts[0], pts[i], pts[i + 1]) for i in range(1, len(pts) - 1)):
        x0, x1 = int(max(min(a[0], b[0], c[0]), 0)), int(min(max(a[0], b[0], c[0]) + 1, m.shape[1]))
        y0, y1 = int(max(min(a[1], b[1], c[1]), 0)), int(min(max(a[1], b[1], c[1]) + 1, m.shape[0]))
        if x1 <= x0 or y1 <= y0: continue
        yy, xx = np.mgrid[y0:y1, x0:x1] + 0.5
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-9: continue
        l1 = ((b[1] - c[1]) * (xx - c[0]) + (c[0] - b[0]) * (yy - c[1])) / d
        l2 = ((c[1] - a[1]) * (xx - c[0]) + (a[0] - c[0]) * (yy - c[1])) / d
        m[y0:y1, x0:x1] |= (l1 >= -0.02) & (l2 >= -0.02) & (l1 + l2 <= 1.02)


def _uv_paint(parts, select, paint, what):
    """Repaint a model's colour images where its faces are `select`ed (by their world centre): `paint(rgb, mask,
    skin)` changes the texels in place (`skin`: the skin-coloured ones)."""
    for o in parts:
        uv = o.data.uv_layers.active
        if uv is None: continue
        W_ = o.matrix_world
        for k, sl in enumerate(o.material_slots):
            p = next((n for n in sl.material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if sl.material else None
            im = next((l.from_node.image for l in p.inputs['Base Color'].links if getattr(l.from_node, 'image', None)), None) if p else None
            if im is None: continue
            w, h = im.size; m = np.zeros((h, w), bool)                          # rows bottom-up, as Blender's pixels
            for poly in o.data.polygons:
                if poly.material_index == k and select(W_ @ poly.center):
                    _uv_fill(m, [(uv.data[li].uv.x * w, uv.data[li].uv.y * h) for li in poly.loop_indices])
            px = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(px); px = px.reshape(h, w, 4)
            rgb = px[..., :3]; mx = rgb.max(-1); mn = rgb.min(-1); sat = (mx - mn) / (mx + 1e-6)
            skin = m & (mx > 0.35) & (sat > 0.12) & (sat < 0.6) & (rgb[..., 0] >= rgb[..., 1])
            n = paint(rgb, m, skin)
            px[..., :3] = rgb; im.pixels.foreach_set(px.ravel()); im.pack()
            cine.log(what, o.name, n, 'texels')


def _neck_skin(parts, jaw):
    """Paint over the dark parts of a model's colour image where its neck is (faces below the jaw): a collar the
    photographs caught becomes the neck's skin (the median of the skin-coloured texels there)."""
    def paint(rgb, m, skin):
        if skin.sum() < 50: return 0
        tone_ = np.median(rgb[skin], 0); dark = m & ~skin
        rgb[dark] = tone_[None, :] * (0.94 + 0.08 * np.random.default_rng(3).random((int(dark.sum()), 1)))
        return int(dark.sum())
    _uv_paint(parts, lambda q: q.z < jaw - 0.005, paint, 'neck painted as skin')


def _scalp_colour(parts, eyes, colour):
    """The hair a model's photographs caught on its scalp (above the brows, behind the ears) in another colour (sRGB
    0-255), its light and dark kept."""
    col = np.array(colour, np.float32) / 255
    def paint(all_):
        def p_(rgb, m, skin):
            hair = m if all_ else m & ~skin; l = rgb[hair] @ np.array([0.2126, 0.7152, 0.0722], np.float32)
            rgb[hair] = col[None, :] * np.clip((l / max(l.mean(), 1e-4)) ** 0.4, 0.7, 1.2)[:, None]
            return int(hair.sum())
        return p_
    top = lambda q: q.z > eyes.z + 0.06 or q.y > eyes.y + 0.11                      # well above the hairline: all hair
    _uv_paint(parts, lambda q: q.z > eyes.z + 0.035 and not top(q), paint(False), 'hairline recoloured')
    _uv_paint(parts, top, paint(True), 'scalp recoloured')


def _joined(mesh, ob):
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.join()


def skirt(arm, mesh, mat, hem=0.02, top=0.0, ease=0.018, flare=0.22, folds=14, depth=0.012, front_open=0.0, seg=72, rows=26, name='skirt'):
    """A long skirt (a gown, a robe) from the waist (`top` metres above the pelvis joint) to `hem` (z, rest pose),
    hugging the hips (`ease` out from them) and flaring as it falls (`flare` metres wider at the hem than at the
    hip), pleated in `folds` soft folds `depth` deep; `front_open` (radians) leaves a split in front. Skinned: the
    waist to the pelvis, then each part to the thigh and calf on its side, the middle front and back shared between
    both legs so it parts as they walk. `mat`: its material (0..1 UVs round and down). Joined into the body mesh."""
    import bmesh
    J = _joints(arm); bvh = _bvh(mesh)
    pel = J['Bip01 Pelvis']; zt = pel.z + top
    c = Vector((pel.x, pel.y, 0)); bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); grid = []
    r_hip = 0.0
    for j in range(rows + 1):
        t = j / rows; z = zt + (hem - zt) * t; ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg; d = Vector((math.sin(a), -math.cos(a), 0))     # a = 0: the front (-y)
            o = Vector((c.x, c.y, z)) + d * 0.6; h = bvh.ray_cast(o, -d, 0.6)[0]
            r_body = (Vector((h.x, h.y, 0)) - c).length if h is not None and (Vector((h.x, h.y, 0)) - c).length < 0.3 else 0.12
            e = 0.004 + (ease - 0.004) * min(t / 0.25, 1.0)                          # the waist hugs the body; the ease comes below it
            if j == 0: ring.append(r_body + e)
            else:
                r_prev = grid[j - 1][i]                                                # never in; wider by the flare as it falls
                ring.append(max(r_prev, r_body + e) + flare * ((t ** 1.3) - (((j - 1) / rows) ** 1.3)))
        grid.append(ring)
    V = []
    for j, ring in enumerate(grid):
        t = j / rows; z = zt + (hem - zt) * t; row = []
        for i, r in enumerate(ring):
            a = 2 * math.pi * i / seg; d = Vector((math.sin(a), -math.cos(a), 0))
            r += depth * math.sin(folds * a) * t ** 0.8
            row.append(bm.verts.new(Vector((c.x, c.y, z)) + d * r))
        V.append(row)
    for j in range(rows):
        for i in range(seg):
            a0 = 2 * math.pi * i / seg
            if front_open and (min(a0, 2 * math.pi - a0) < front_open / 2): continue
            i2 = (i + 1) % seg
            f = bm.faces.new((V[j][i], V[j][i2], V[j + 1][i2], V[j + 1][i]))
            for l, (uu, vv) in zip(f.loops, ((i / seg, j / rows), ((i + 1) / seg, j / rows), ((i + 1) / seg, (j + 1) / rows), (i / seg, (j + 1) / rows))): l[uvl].uv = (uu, 1 - vv)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces: f.smooth = True
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); [cl.objects.link(ob) for cl in mesh.users_collection]; me.materials.append(mat)
    # weights: the waist band to the pelvis; below it, each side to its thigh then calf; the middle shared
    gs = {n: ob.vertex_groups.new(name=n) for n in ('Bip01 Pelvis', 'Bip01 L Thigh', 'Bip01 R Thigh', 'Bip01 L Calf', 'Bip01 R Calf')}
    kz = J['Bip01 L Calf'].z
    def sm(e0, e1, x): x = min(max((x - e0) / (e1 - e0), 0.0), 1.0); return x * x * (3 - 2 * x)
    for v in me.vertices:
        p = v.co; wp = 1 - sm(zt - 0.12, zt - 0.32, p.z)
        side = sm(-0.05, 0.05, p.x - c.x)                                           # 0: the right leg, 1: the left
        mid = 1 - abs(side * 2 - 1)
        wl, wr = side * (1 - wp), (1 - side) * (1 - wp)
        calf = sm(kz + 0.05, kz - 0.15, p.z) * 0.6
        for n, w in (('Bip01 Pelvis', wp + mid * 0.25 * (1 - wp)), ('Bip01 L Thigh', wl * (1 - calf) * (1 - 0.25 * mid)), ('Bip01 R Thigh', wr * (1 - calf) * (1 - 0.25 * mid)),
                     ('Bip01 L Calf', wl * calf), ('Bip01 R Calf', wr * calf)):
            if w > 1e-4: gs[n].add([v.index], w, 'REPLACE')
    me.transform(mesh.matrix_world.inverted()); ob.matrix_world = mesh.matrix_world
    me.uv_layers[0].name = mesh.data.uv_layers.active.name
    _joined(mesh, ob); cine.log('skirt on', mesh.get('person', mesh.name), f'hem at z {hem:.2f}')


def cape(arm, mesh, mat, hem, width=0.5, drop_out=0.06, folds=9, depth=0.02, seg=40, rows=22, collar=0.02, name='cape'):
    """A cloak hung from the shoulders down the back to `hem` (z, rest pose): across the shoulders from collar bone to
    collar bone, `width` wide at the shoulders widening by half again to the hem, standing `drop_out` off the back,
    pleated; skinned to the upper back and collar bones at the top, the pelvis and the thighs lower down (it swings
    with the walk). Joined into the body mesh."""
    import bmesh
    J = _joints(arm); bvh = _bvh(mesh)
    neck = J['Bip01 Neck']; top = neck.z - collar; sh = (J['Bip01 L UpperArm'] + J['Bip01 R UpperArm']) / 2
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); V = []
    for j in range(rows + 1):
        t = j / rows; z = top + (hem - top) * t; row = []
        w = width * (1 + 0.5 * t ** 0.8)
        for i in range(seg + 1):
            s = i / seg - 0.5; x = neck.x + s * w
            o = Vector((x, neck.y + 0.6, z)); h = bvh.ray_cast(o, Vector((0, -1, 0)), 0.9)[0]
            yb = (h.y if h is not None else neck.y + 0.12)
            y = yb + 0.012 + drop_out * t ** 0.7 + depth * math.sin(folds * math.pi * s * 2) * t
            # over the shoulders: the top rows wrap forward round the shoulders' tops
            if j == 0: y = min(y, sh.y + 0.05 + abs(s) * 0.06)
            row.append(bm.verts.new(Vector((x, y, z))))
        V.append(row)
    for j in range(rows):
        for i in range(seg):
            f = bm.faces.new((V[j][i], V[j][i + 1], V[j + 1][i + 1], V[j + 1][i]))
            for l, (uu, vv) in zip(f.loops, ((i / seg, j / rows), ((i + 1) / seg, j / rows), ((i + 1) / seg, (j + 1) / rows), (i / seg, (j + 1) / rows))): l[uvl].uv = (uu, 1 - vv)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces: f.smooth = True
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); [cl.objects.link(ob) for cl in mesh.users_collection]; me.materials.append(mat)
    names = ('Bip01 Spine2', 'Bip01 L Clavicle', 'Bip01 R Clavicle', 'Bip01 Spine', 'Bip01 Pelvis', 'Bip01 L Thigh', 'Bip01 R Thigh')
    gs = {n: ob.vertex_groups.new(name=n) for n in names}
    pel = J['Bip01 Pelvis']
    def sm(e0, e1, x): x = min(max((x - e0) / (e1 - e0), 0.0), 1.0); return x * x * (3 - 2 * x)
    for v in me.vertices:
        p = v.co; up = sm(pel.z, top - 0.05, p.z); low = 1 - up
        side = sm(-0.08, 0.08, p.x - neck.x)
        top_side = up * sm(0.05, 0.18, abs(p.x - neck.x))
        wts = {'Bip01 Spine2': up * (1 - top_side) * 0.8, 'Bip01 L Clavicle' if p.x > neck.x else 'Bip01 R Clavicle': top_side, 'Bip01 Spine': up * (1 - top_side) * 0.2,
               'Bip01 Pelvis': low * (1 - sm(pel.z - 0.05, pel.z - 0.4, p.z)) + low * sm(pel.z - 0.05, pel.z - 0.4, p.z) * 0.5,
               'Bip01 L Thigh': low * sm(pel.z - 0.05, pel.z - 0.4, p.z) * 0.5 * side, 'Bip01 R Thigh': low * sm(pel.z - 0.05, pel.z - 0.4, p.z) * 0.5 * (1 - side)}
        for n, w in wts.items():
            if w > 1e-4: gs[n].add([v.index], w, 'REPLACE')
    me.transform(mesh.matrix_world.inverted()); ob.matrix_world = mesh.matrix_world
    me.uv_layers[0].name = mesh.data.uv_layers.active.name
    _joined(mesh, ob); cine.log('cape on', mesh.get('person', mesh.name), f'hem at z {hem:.2f}')


def remove_hair_cards(mesh):
    """Drop the avatar's own hair cards (the 'opacity' material's faces): a hair shell or a sculpted head replaces them."""
    import bmesh
    k = {i for i, sl in enumerate(mesh.material_slots) if sl.material and 'opacity' in sl.material.name}
    bm = bmesh.new(); bm.from_mesh(mesh.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in k], context='FACES'); bm.to_mesh(mesh.data); bm.free(); mesh.data.update()


def transplant_hair(arm, mesh, donor, image, hem=None, fit=1.04, lift=0.0, back=0.0, stretch=1.0, flare=0.15, front_keep=0.03, name='hair'):
    """Another avatar's hair cards on this head: the donor's 'opacity' faces, moved and scaled so its eyes sit on
    these eyes (`fit` scales them a little more about the skull's middle: a man's head is larger), `lift` and `back`
    (metres) nudge them; `stretch` lengthens what hangs below the ears (behind them, from `front_keep` metres back of
    the skull's middle) by that factor, `flare` pushing it out as it falls (metres per metre); cut off below `hem` (z,
    rest pose) if given; their texture replaced by `image` (an RGBA file: the donor's own, recoloured); skinned head ->
    neck -> upper back; joined into the body mesh."""
    import bmesh
    before = set(bpy.data.objects)
    _import_fbx(os.path.join(RB, 'avatars', donor, 'Export', f'{donor}.fbx'))
    new = [o for o in bpy.data.objects if o not in before]
    darm = next(o for o in new if o.type == 'ARMATURE'); dmesh = next(o for o in new if o.type == 'MESH')
    bpy.context.view_layer.update()
    DJ = {b.name: darm.matrix_world @ b.head_local for b in darm.data.bones}
    k = [i for i, sl in enumerate(dmesh.material_slots) if sl.material and 'opacity' in sl.material.name and 'glasses' not in sl.material.name]
    bm = bmesh.new(); bm.from_mesh(dmesh.data); bm.transform(dmesh.matrix_world)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index not in k], context='FACES')
    J = _joints(arm)
    dm = (DJ['Bip01 LEye'] + DJ['Bip01 REye']) / 2; tm = (J['Bip01 LEye'] + J['Bip01 REye']) / 2
    s = (J['Bip01 LEye'] - J['Bip01 REye']).length / (DJ['Bip01 LEye'] - DJ['Bip01 REye']).length * fit
    dc = dm + Vector((0, 0.06, 0.03))                                           # the donor's skull middle
    T_ = Matrix.Translation(tm + Vector((0, 0.06 + back, 0.03 + lift))) @ Matrix.Diagonal((s, s, s, 1)) @ Matrix.Translation(-dc)
    bm.transform(T_)
    if stretch != 1.0:                                                          # longer hair: what falls below the ears, longer
        c = tm + Vector((0, 0.06 + back, 0.03 + lift)); zr = c.z - 0.035
        for v in bm.verts:
            p = v.co
            if p.z >= zr: continue
            behind = min(max((p.y - (c.y - front_keep)) / 0.04, 0.0), 1.0)
            dz = (p.z - zr) * (stretch - 1.0) * behind
            out = Vector((p.x - c.x, p.y - c.y, 0)); out = out.normalized() if out.length > 1e-6 else Vector((0, 1, 0))
            v.co = Vector((p.x, p.y, p.z + dz)) + out * (-dz) * flare
    if hem is not None:
        res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, hem), plane_no=(0, 0, 1))
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < hem - 1e-5], context='VERTS')
    for f in bm.faces: f.material_index = 0
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    uv = me.uv_layers[0].name if me.uv_layers else None
    for l in list(me.uv_layers)[1:]: me.uv_layers.remove(l)
    for o in new: bpy.data.objects.remove(o, do_unlink=True)
    ob = bpy.data.objects.new(name, me); [cl.objects.link(ob) for cl in mesh.users_collection]
    img = bpy.data.images.load(image, check_existing=True)
    me.materials.clear(); me.materials.append(_hair_material(f"hair_{mesh.get('person', 'x')}", img, rough=0.5))
    _skin_by_height(ob, J, tm.x)
    me.transform(mesh.matrix_world.inverted()); ob.matrix_world = mesh.matrix_world
    if me.uv_layers: me.uv_layers[0].name = mesh.data.uv_layers.active.name
    for p in me.polygons: p.use_smooth = True
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.join()
    cine.log('hair from', donor, 'on', mesh.get('person', mesh.name), f'scale {s:.3f}', f'cut at {hem:.2f}' if hem is not None else '')


def _hair_image(name, colour, seed, size=(1024, 512), streak=0.5, jag=0.14, curl=0.0, clumps=False):
    """An RGBA strand texture: u across the strands (fine streaks in clumps), v down their length; the ends (v near 1)
    ragged in the alpha. `colour` sRGB 0-255; `curl` waves the streaks (curly or wavy hair)."""
    rng = np.random.default_rng(seed); W_, H_ = size
    u = np.arange(W_) / W_; v = np.arange(H_)[:, None] / H_
    col = np.zeros(W_)
    for f, a in ((8, 0.45), (40, 0.3), (160, 0.25), (500, 0.18)):                 # clumps and single strands
        ph = rng.random(f) * 2 * np.pi; col += a * np.interp(u * f, np.arange(f + 1), np.r_[np.sin(ph), np.sin(ph[0])])
    shift = (curl * 0.02 * np.sin(v * 2 * np.pi * 6 + u[None, :] * 40)) if curl else 0.0
    idx = ((u[None, :] + shift) % 1.0 * W_).astype(int) % W_
    lum_ = (1.0 + streak * 0.5 * col[idx] / np.abs(col).max()) * np.ones((H_, 1))
    lum_ *= 0.82 + 0.18 * np.clip(v * 4, 0, 1)                                      # darker at the roots
    lum_ *= 1.0 + 0.12 * np.sin(v * 2 * np.pi * 3 + u[None, :] * 13) * curl         # waves catch the light
    base = np.array(colour, np.float32) / 255
    rgb = np.clip(base[None, None, :] * lum_[..., None], 0, 1)
    ends = 1 - jag * rng.random(W_) ** 0.6                                           # each strand's own length
    ends = np.convolve(ends, np.ones(3) / 3, mode='same')
    alpha = (v < ends[None, :]).astype(np.float32)
    if clumps:                                                                      # strands in clumps with gaps between them
        g = np.zeros(W_)
        for f, a_ in ((24, 0.6), (90, 0.4), (300, 0.3)):
            ph = rng.random(f) * 2 * np.pi; g += a_ * np.interp(u * f, np.arange(f + 1), np.r_[np.sin(ph), np.sin(ph[0])])
        keep = (g > np.quantile(g, 0.32)).astype(np.float32)
        alpha = alpha * keep[None, :]
    img = bpy.data.images.new(name, W_, H_, alpha=True)
    px = np.dstack([rgb, alpha])[::-1].astype(np.float32)                           # Blender's rows run bottom-up
    img.pixels.foreach_set(px.ravel()); img.pack()
    return img


def _hair_material(name, img, rough=0.5):
    m = bpy.data.materials.new(name); nt = m.node_tree; p = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = img
    nt.links.new(t.outputs['Color'], p.inputs['Base Color']); nt.links.new(t.outputs['Alpha'], p.inputs['Alpha'])
    p.inputs['Roughness'].default_value = rough; p.inputs['Specular IOR Level'].default_value = 0.35
    try: m.blend_method = 'CLIP'; m.alpha_threshold = 0.45
    except Exception: pass
    try: m.surface_render_method = 'DITHERED'
    except Exception: pass
    return m


def _bvh(mesh):
    from mathutils.bvhtree import BVHTree
    deps = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(deps); M = mesh.matrix_world
    me = ev.to_mesh(); verts = [M @ v.co for v in me.vertices]; polys = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys)


def _head_frame(arm):
    """The skull's middle (rest pose, the avatar facing -y) and the eye height."""
    J = _joints(arm); em = (J['Bip01 LEye'] + J['Bip01 REye']) / 2
    return Vector((em.x, em.y + 0.06, em.z + 0.03)), em, J


def _skin_by_height(ob, J, side_x=0.0):
    """Hair or beard weights: the head above the jaw, the neck, then the upper back and the collar bones below."""
    neck, head = J['Bip01 Neck'], J['Bip01 Head']
    names = ['Bip01 Head', 'Bip01 Neck', 'Bip01 Spine2', 'Bip01 L Clavicle', 'Bip01 R Clavicle']
    gs = {n: ob.vertex_groups.new(name=n) for n in names}
    def sm(e0, e1, x): t = min(max((x - e0) / (e1 - e0), 0.0), 1.0); return t * t * (3 - 2 * t)
    for v in ob.data.vertices:
        p = v.co; z = p.z
        wh = sm(neck.z + 0.02, head.z + 0.03, z)                              # head above, the neck below
        wn = (1 - wh) * sm(neck.z - 0.1, neck.z - 0.01, z)
        rest = 1 - wh - wn
        side = sm(0.04, 0.16, abs(p.x - side_x))
        wc = rest * 0.6 * side; ws = rest - wc
        for n, w in (('Bip01 Head', wh), ('Bip01 Neck', wn), ('Bip01 Spine2', ws), ('Bip01 L Clavicle' if p.x > side_x else 'Bip01 R Clavicle', wc)):
            if w > 1e-4: gs[n].add([v.index], w, 'ADD')


def hair_shell(arm, mesh, colour, hem, thick=0.008, fall=0.012, front=30.0, temple=12.0, nape=-28.0, fringe=None, curl=0.0, seed=4, name='hair',
               lie=0.6, tuck=0.35, back_only=100.0, layers=3, ncol=56, width=0.032, gap=0.006, swept_cards=False):
    """Long hair as cards: `layers` x `ncol` narrow ribbons (`width` metres) laid along paths from the crown over the
    scalp (`thick` out from it, each layer `gap` further) to the hairline (the face left open: the hairline at `front`
    degrees above the skull's middle in front, `temple` at the sides, `nape` behind), and from behind the ears
    (`back_only` degrees either side of the back) straight down to `hem` (z, rest pose), resting on the neck and
    shoulders (`fall` out from them, spreading by `lie`, tucking in by `tuck` as they fall). A strand texture cuts
    each card into clumps (alpha), the ends ragged; skinned head -> neck -> upper back; joined into the body."""
    import bmesh
    c, em, J = _head_frame(arm); bvh = _bvh(mesh)
    rng = np.random.default_rng(seed)
    def hit_in(origin, d, maxd=0.6):
        h = bvh.ray_cast(origin, d, maxd); return h[0]
    def hairline(phi):
        a = abs(math.degrees(phi)); b = front if fringe is None else fringe
        if a >= 140: return math.radians(b)
        if a >= 95: return math.radians(temple + (b - temple) * ((a - 95) / 45) ** 2)
        return math.radians(nape + (temple - nape) * (a / 95) ** 1.5)
    def path(phi, t_off, back=0.0):
        th_end = hairline(phi) + math.radians(back); pts, nrm = [], []
        swept = abs(math.degrees(phi)) >= back_only                         # over the brow: from the hairline back over the crown
        th0 = math.radians(150) if swept else math.radians(86)
        for k in range(16 if swept else 12):
            th = th0 + (th_end - th0) * (k / (15 if swept else 11))
            d = Vector((math.cos(th) * math.sin(phi), math.cos(th) * math.cos(phi), math.sin(th)))
            h = hit_in(c + d * 0.35, -d)
            lay = 0.35 if swept else 1.0                                              # swept back: close on the scalp
            pts.append((h if h is not None else c + d * 0.1) + d * t_off * lay); nrm.append(d)
        if abs(math.degrees(phi)) < back_only:
            dxy = Vector((math.sin(phi), math.cos(phi), 0)); ax = Vector((c.x, c.y - 0.02, 0))
            r_prev = (pts[-1] - Vector((ax.x, ax.y, pts[-1].z))).dot(dxy)
            z0 = pts[-1].z; zh = hem + 0.025 * rng.standard_normal(); n = max(4, int((z0 - zh) / 0.022)); dz = (z0 - zh) / n
            for k in range(1, n + 1):
                z = z0 - dz * k; o = Vector((ax.x, ax.y, z)) + dxy * 0.5
                h = hit_in(o, -dxy, 0.6)
                r = ((h - Vector((ax.x, ax.y, z))).dot(dxy) + fall + t_off) if h is not None else r_prev
                if r > r_prev + 0.06 or r > 0.2: r = r_prev
                r = r_prev + (r - r_prev) * lie if r > r_prev else max(r, r_prev - tuck * dz)
                r_prev = r; pts.append(Vector((ax.x, ax.y, z)) + dxy * r); nrm.append(dxy)
        return pts, nrm
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); ncards = 0
    for L in range(layers):
        for i in range(ncol):
            phi = -math.pi + 2 * math.pi * (i + 0.5 + 0.5 * (L % 2) + rng.uniform(-0.25, 0.25)) / ncol
            sw = abs(math.degrees(phi)) >= back_only
            if sw and (L > 0 or not swept_cards): continue                       # over the brow: the scalp's painted hair, or one close layer
            pts, nrm = path(phi, thick + gap * L + rng.uniform(0, gap * 0.5), back=rng.uniform(0, 4))
            if len(pts) < 2: continue
            w = width * rng.uniform(0.85, 1.25) * (1.6 if sw else 1.0); u0 = rng.uniform(0, 0.75); L_ = np.r_[0, np.cumsum([(b - a).length for a, b in zip(pts, pts[1:])])]
            row = []
            for k, (p, n) in enumerate(zip(pts, nrm)):
                tng = (pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]).normalized()
                side = tng.cross(n).normalized() * (w / 2)
                row.append((bm.verts.new(p - side), bm.verts.new(p + side), L_[k] / max(L_[-1], 1e-6)))
            for a, b in zip(row, row[1:]):                                       # over the brow: roots at the hairline, swept back
                f = bm.faces.new((a[0], a[1], b[1], b[0]))
                for l, (uu, vv) in zip(f.loops, ((u0, a[2]), (u0 + 0.25, a[2]), (u0 + 0.25, b[2]), (u0, b[2]))): l[uvl].uv = (uu, vv if sw else 1 - vv)
            ncards += 1
    for f in bm.faces: f.smooth = True
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); [cl.objects.link(ob) for cl in mesh.users_collection]
    me.materials.append(_hair_material(f"hair_{mesh.get('person', 'x')}", _hair_image(f"hair_{mesh.get('person', 'x')}", colour, seed, curl=curl, clumps=True, jag=0.45)))
    _skin_by_height(ob, J, c.x)
    me.transform(mesh.matrix_world.inverted()); ob.matrix_world = mesh.matrix_world
    me.uv_layers[0].name = mesh.data.uv_layers.active.name
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.join()
    cine.log('hair cards', mesh.get('person', mesh.name), ncards, f'cards to z {hem:.2f}')


def beard_shell(arm, mesh, colour, thick=0.012, chin=0.022, top=-0.035, moustache=True, neck=0.04, seed=6, mats=('head',), name='beard'):
    """A beard grown off the face: the head's own faces below the cheekbones (`top` metres under the eyes) and under the
    jaw down `neck` below the chin, offset out along their normals (`thick`, more at the chin), the lips left clear (and
    the upper lip too without `moustache`); textured with short strands, skinned to the head; joined into the body."""
    import bmesh
    c, em, J = _head_frame(arm)
    me = mesh.data; M = mesh.matrix_world
    ks = {i for i, sl in enumerate(mesh.material_slots) if sl.material and any(k in sl.material.name for k in mats)}
    lip = J.get('Bip01 MUpperLip', em - Vector((0, 0.03, 0.06))); jawz = lip.z - 0.075
    def inside(p):
        if p.y > c.y - 0.01 or p.z > em.z + top: return False                     # the front of the head, below the cheekbones
        if p.z < jawz - neck: return False
        dx = abs(p.x - em.x)
        if dx > 0.072: return False
        mouth = ((p.x - lip.x) / 0.026) ** 2 + ((p.z - (lip.z - 0.012)) / 0.012) ** 2 < 1
        if mouth: return False
        if not moustache and p.z > lip.z - 0.006 and dx < 0.03: return False
        if p.z > lip.z - 0.004 and dx < 0.028 and p.z < lip.z + 0.016 and not moustache: return False
        return True
    bm = bmesh.new(); bm.from_mesh(me); bm.transform(M)
    keep = [f for f in bm.faces if f.material_index in ks and all(inside(v.co) for v in f.verts)]
    out = bmesh.new(); uvl = out.loops.layers.uv.new('UVMap'); vmap = {}
    for f in keep:
        vs = []
        for v in f.verts:
            if v.index not in vmap:
                n = v.normal.normalized(); t = thick + chin * max(0.0, 1 - abs(v.co.x - em.x) / 0.04) * max(0.0, (lip.z - 0.03 - v.co.z) / 0.06)
                vmap[v.index] = out.verts.new(v.co + n * t)
            vs.append(vmap[v.index])
        try:
            nf = out.faces.new(vs)
            for l in nf.loops: l[uvl].uv = ((l.vert.co.x - em.x) * 12 + 0.5, (l.vert.co.z - jawz) * 8)
        except ValueError: pass
    bm.free()
    for f in out.faces: f.smooth = True
    bm2 = bpy.data.meshes.new(name); out.to_mesh(bm2); out.free()
    ob = bpy.data.objects.new(name, bm2); [cl.objects.link(ob) for cl in mesh.users_collection]
    bm2.materials.append(_hair_material(f"beard_{mesh.get('person', 'x')}", _hair_image(f"beard_{mesh.get('person', 'x')}", colour, seed, size=(512, 256), streak=0.7, jag=0.0), rough=0.6))
    vg = ob.vertex_groups.new(name='Bip01 Head'); vg.add(list(range(len(bm2.vertices))), 1.0, 'REPLACE')
    ob.matrix_world = Matrix.Identity(4); bm2.transform(mesh.matrix_world.inverted()); ob.matrix_world = mesh.matrix_world
    bm2.uv_layers[0].name = mesh.data.uv_layers.active.name
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.join()
    cine.log('beard', mesh.get('person', mesh.name), len(keep), 'faces')


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
    # a taller avatar strides further; one with shorter legs (`leg_k`, from `reproportion`) carries the clip's pelvis
    # lower and strides shorter: the clip's skeleton is scaled by it about the feet (rotations are what is copied)
    P = placement(arm) @ Matrix.Scale(arm.get('leg_k', 1.0), 4); grow = P.to_scale().x
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
