# Rocketbox people: import an avatar (FBX, 3ds Max Biped rig), point its textures at the cache, give it clean
# glTF-ready materials, and apply motion-capture clips from the Rocketbox library (same rig, no retargeting).
import bpy, os, math
from mathutils import Vector, Matrix
import cine

RB = os.path.join(cine.CACHE, 'rocketbox')


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
            outs = [(l.to_node, l.to_socket.name) for l in nt.links if l.from_node == n]
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


def _clip_armature(name, inplace):
    """The clip's own armature, animated. Animation-only FBX files import with their first frame as the rest pose,
    so their channels cannot be copied to an avatar directly; we copy the resulting world pose instead."""
    objs = _import_fbx(os.path.join(RB, 'animations', f'{name}.fbx'))
    src = next(o for o in objs if o.type == 'ARMATURE')
    for o in objs:
        if o is not src: bpy.data.objects.remove(o, do_unlink=True)
    act = src.animation_data.action
    if inplace:  # drop the root's travel over the floor; keep its bob and sway
        for layer in act.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    for fc in cb.fcurves:
                        if fc.data_path == 'location' and fc.array_index in (0, 1):
                            v0 = fc.keyframe_points[0].co[1]
                            for k in fc.keyframe_points: k.co[1] = v0; k.handle_left[1] = v0; k.handle_right[1] = v0
    return src, act


def retarget(arm, name, inplace=False, frames=None, action_name=None):
    """Bakes clip `name` onto avatar `arm` as a new action (world-space copy of every shared bone)."""
    src, act = _clip_armature(name, inplace)
    src.location, src.rotation_euler, src.scale = arm.location.copy(), arm.rotation_euler.copy(), arm.scale.copy()
    f0, f1 = (int(act.frame_range[0]), int(act.frame_range[1])) if frames is None else frames
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
    bpy.data.objects.remove(src, do_unlink=True); bpy.data.actions.remove(act)
    return baked


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
    """MDR refining: over the seated clip `base`, the left wrist taps on the keyboard and the right hand rolls the
    trackball, baked into one looping action. left/right: world wrist targets; facing: the worker's forward."""
    import random
    rnd = random.Random(seed)
    sc = bpy.context.scene
    fwd = (facing or Vector((0, 1, 0))).normalized(); side = Vector((fwd.y, -fwd.x, 0))  # the worker's right
    act = base.copy(); act.name = name or f'{arm.name}_work'; act.use_fake_user = True
    pose_at(arm, act, frames[0])
    f0, f1 = frames; n = f1 - f0
    left, right = Vector(left), Vector(right)
    bones = [arm.pose.bones[f'Bip01 {s} {b}'] for s in 'LR' for b in ('UpperArm', 'Forearm')]
    for f in range(f0, f1 + 1):
        sc.frame_set(f); bpy.context.view_layer.update()
        t = (f - f0) / n
        tap = max(0.0, math.sin(t * math.pi * 2 * 23 + 0.4 * math.sin(t * 61))) ** 6
        tL = left + side * (0.012 * math.sin(t * math.pi * 2 * 2)) + fwd * (0.008 * math.sin(t * math.pi * 2 * 5)) + Vector((0, 0, 0.006 * tap))
        roll = 0.5 + 0.5 * math.sin(t * math.pi * 2 * 3); a = t * math.pi * 2 * 9
        tR = right + (side * math.cos(a) + fwd * math.sin(a)) * 0.007 * roll
        for s, tgt in (('L', tL), ('R', tR)):
            out = side if s == 'R' else -side
            ik2(arm, s, tgt, tgt + out * 0.35 - fwd * 0.25 - Vector((0, 0, 0.45)))
        for pb in bones: pb.keyframe_insert('rotation_quaternion', frame=f)
    return act


def pose_at(arm, action, frame):
    arm.animation_data_create(); arm.animation_data.action = action
    if arm.animation_data.action_slot is None and action.slots: arm.animation_data.action_slot = action.slots[0]
    bpy.context.scene.frame_set(int(frame)); bpy.context.view_layer.update()
