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


def reshape(arm, mesh, shape):
    """Change a body's build by moving its rest-pose vertices: radial scaling about the spine and limb axes,
    weighted by the skin weights so the joints blend. The skeleton is untouched, so every clip still fits.
    shape: 'heavy' (an obese build), 'athletic' (broad shoulders, big arms, a narrow waist), 'lean' (a longer face)."""
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
    if shape == 'heavy':
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
    elif shape == 'lean':
        hd = j('Head'); brow = j('MMiddleEyebrow').z; lip = j('MUpperLip').z
        face = w('Head', 'MJaw', 'Mouth', 'Lip', 'Cheek', 'Masseter', 'Caninus') * _smooth(brow, brow - 0.06, P[:, 2]) * _smooth(0.03, -0.02, P[:, 1] - hd.y)
        D[:, 0] -= face * (P[:, 0] - hd.x) * 0.07
        D[:, 2] -= face * _smooth(lip + 0.02, lip - 0.05, P[:, 2]) * 0.007
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


def retarget(arm, name, inplace=False, cycles=1, action_name=None, limit=None):
    """Bakes clip `name` onto avatar `arm` as a new action, whole (or `cycles` times over, seamlessly).
    World-space copy of every shared bone; then only the root keeps its translation, so the avatar keeps its own
    proportions. Returns (action, (first, last) frame, speed in m/s for travelling clips)."""
    src, act, travel = _clip_armature(name, inplace, cyclic=cycles > 1)
    grow = arm.scale.x / src.scale.x                          # a taller avatar strides further
    src.location, src.rotation_euler, src.scale = arm.location.copy(), arm.rotation_euler.copy(), arm.scale.copy()
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
    bpy.data.objects.remove(src, do_unlink=True); bpy.data.actions.remove(act)
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
    pb.matrix = arm.matrix_world.inverted() @ M
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


def pose_at(arm, action, frame):
    arm.animation_data_create(); arm.animation_data.action = action
    if arm.animation_data.action_slot is None and action.slots: arm.animation_data.action_slot = action.slots[0]
    bpy.context.scene.frame_set(int(frame)); bpy.context.view_layer.update()


def export_person(arm, mesh, acts, path, image_size=1024):
    """One glTF per person: body, rig and every act as its own animation (NLA tracks, each named after its act)."""
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
