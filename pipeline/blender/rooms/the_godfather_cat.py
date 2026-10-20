# The Don's cat: a photogrammetry scan of a grey tabby lying curled on its side, forelegs stretched out, head tucked
# ("Cat" by mustafasahinfb, CC BY 4.0), cut from the cushion it was scanned on, closed underneath, and given a small
# rig of its own: the body (it breathes), the head, the two forelegs. Its acts are authored here, frame by frame: in
# the Don's lap (breathing, a paw kneading, the head lifting to look round), and carried to the desk and back.
import math, os
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Quaternion
import cine, people

SRC = os.path.join(cine.CACHE, 'objaverse', 'cat_mustafasahinfb.glb')
SCALE = 0.82                                # a young slim cat, smaller than the one scanned
# where its parts are in the scan (metres, the cushion's plane at z = 0)
BASE = Vector((0.16, 0.0, 0.0))             # the middle of what it lies on: its root, and the point set on the lap
BODY = Vector((0.2, 0.0, 0.0))
HEAD = Vector((0.03, -0.06, 0.07)); NECK = Vector((0.11, -0.03, 0.075))
LEGS = {'a': (Vector((0.07, 0.12, 0.06)), Vector((-0.04, 0.13, 0.05)), Vector((-0.15, 0.135, 0.045))),
        'b': (Vector((0.04, 0.11, 0.06)), Vector((-0.02, 0.05, 0.05)), Vector((-0.08, -0.04, 0.035)))}
BONES = ('cat_root', 'cat_body', 'cat_head', 'cat_a1', 'cat_a2', 'cat_b1', 'cat_b2')


def _cut(ob):
    """Keep the cat: drop the cushion (blue), what lies flat at its level, everything outside the cat's ellipse; keep
    the pieces of a fair size; close the holes (its underside) with a dark fur."""
    img = next(n.image for n in ob.data.materials[0].node_tree.nodes if n.type == 'TEX_IMAGE')   # the scan's own texture
    W, H = img.size; px = np.array(img.pixels[:], np.float32).reshape(H, W, 4)[..., :3]
    me = ob.data; bm = bmesh.new(); bm.from_mesh(me); bm.transform(ob.matrix_world)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)                 # glTF splits vertices at UV seams: join them again
    uv = bm.loops.layers.uv.active
    def colour(f):
        u = sum((l[uv].uv for l in f.loops), Vector((0, 0))) / len(f.loops)
        return px[int(min(max(u.y, 0), 0.999) * H), int(min(max(u.x, 0), 0.999) * W)]
    dead = []
    for f in bm.faces:
        c = f.calc_center_median(); r, g, b = colour(f)
        if b > r + 0.13 or c.z < 0.01 or ((c.x - 0.07) / 0.37) ** 2 + ((c.y + 0.15) / 0.33) ** 2 > 1: dead.append(f)
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    bm.faces.ensure_lookup_table(); seen, pieces = set(), []
    for f in bm.faces:
        if f.index in seen: continue
        stack, piece = [f], []; seen.add(f.index)
        while stack:
            g = stack.pop(); piece.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen: seen.add(h.index); stack.append(h)
        pieces.append(piece)
    keep = {f for p in pieces if len(p) >= 60 for f in p}
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f not in keep], context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    # the opening underneath (the longest boundary loop) closed with a dark fur; the scan's small holes left as they are
    loops, seen = [], set()
    for e in [e for e in bm.edges if e.is_boundary]:
        if e in seen: continue
        stack, loop = [e], []; seen.add(e)
        while stack:
            g = stack.pop(); loop.append(g)
            for v in g.verts:
                for h in v.link_edges:
                    if h.is_boundary and h not in seen: seen.add(h); stack.append(h)
        loops.append(loop)
    big = max(loops, key=lambda l: sum(e.calc_length() for e in l))
    caps = bmesh.ops.holes_fill(bm, edges=big, sides=0)['faces']
    for f in bmesh.ops.triangulate(bm, faces=caps)['faces']: f.material_index = 1
    bm.to_mesh(me); bm.free(); ob.matrix_world = Matrix.Identity(4)
    for p in me.polygons: p.use_smooth = True
    cine.log('cat cut', len(me.polygons), 'faces')


def load(col):
    """The cat, cut, closed and rigged, in the scan's own frame (its root at BASE, scaled), at rest on the origin.
    Returns (armature, mesh)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=SRC)
    new = [o for o in bpy.data.objects if o not in before]
    ob = next(o for o in new if o.type == 'MESH')
    for o in new:
        if o is not ob: bpy.data.objects.remove(o, do_unlink=True)
    for c in ob.users_collection: c.objects.unlink(ob)
    col.objects.link(ob); ob.name = 'cat'
    _cut(ob)
    # the scan's fur, a shade greyer and cooler (the film's cat is a silver-grey tabby), and its dark underside
    m = ob.data.materials[0]; m.name = 'cat_fur'
    p = m.node_tree.nodes['Principled BSDF']
    t = next(n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE')
    hs = m.node_tree.nodes.new('ShaderNodeHueSaturation'); hs.inputs['Saturation'].default_value = 0.72; hs.inputs['Value'].default_value = 0.92
    m.node_tree.links.new(t.outputs['Color'], hs.inputs['Color']); m.node_tree.links.new(hs.outputs['Color'], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.85; p.inputs['Specular IOR Level'].default_value = 0.3
    p.inputs['Sheen Weight'].default_value = 0.4; p.inputs['Sheen Tint'].default_value = (0.5, 0.48, 0.45, 1)
    under = cine.material('cat_under', (0.07, 0.065, 0.06), rough=0.9)
    ob.data.materials.append(under)
    _bake_grey(m, t)
    # into the root's frame: BASE at the origin, scaled
    ob.data.transform(Matrix.Diagonal((SCALE, SCALE, SCALE, 1)) @ Matrix.Translation(-BASE))
    ob['person'] = 'cat'
    arm = _rig(ob, col)
    return arm, ob


def _bake_grey(m, t):
    """The exporter writes only the texture: fold the hue and saturation change into a copy of the image."""
    img = t.image; W, H = img.size
    a = np.array(img.pixels[:], np.float32).reshape(H, W, 4)
    rgb = a[..., :3]; l = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    rgb = l[..., None] + (rgb - l[..., None]) * 0.72                         # less colour
    rgb = rgb * np.array([1.0, 1.0, 1.03], np.float32)                      # a silver-grey tabby: darker reads black on the web
    a[..., :3] = np.clip(rgb, 0, 1)
    new = bpy.data.images.new('cat_fur', W, H); new.pixels = a.ravel(); new.pack()
    t.image = new
    nt = m.node_tree; hs = next(n for n in nt.nodes if n.type == 'HUE_SAT')
    nt.links.new(t.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color']); nt.nodes.remove(hs)


def _p(v):
    """A point of the scan, in the rig's frame."""
    return (Vector(v) - BASE) * SCALE


def _rig(ob, col):
    """An armature in the cat's frame: the root, the body (scaled to breathe), the head on its neck, two bones a
    foreleg; the skin weighted by distance to each bone, softly, within each part's own region."""
    ad = bpy.data.armatures.new('cat_rig'); arm = bpy.data.objects.new('cat_rig', ad); col.objects.link(arm)
    arm['person'] = 'cat'
    bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='EDIT')
    def bone(name, h, t, parent=None):
        b = ad.edit_bones.new(name); b.head = h; b.tail = t; b.parent = ad.edit_bones[parent] if parent else None; return b
    bone('cat_root', _p(BASE), _p(BASE) + Vector((0, 0, 0.06)))
    bone('cat_body', _p(BODY), _p(BODY) + Vector((0, 0, 0.14)), 'cat_root')
    bone('cat_head', _p(NECK), _p(HEAD), 'cat_body')
    for k, (s, e, w) in LEGS.items():
        bone(f'cat_{k}1', _p(s), _p(e), 'cat_body'); bone(f'cat_{k}2', _p(e), _p(w), f'cat_{k}1')
    bpy.ops.object.mode_set(mode='OBJECT')
    me = ob.data; P = np.array([v.co[:] for v in me.vertices], np.float32)
    def seg(a, b):
        a, b = np.array(a[:], np.float32), np.array(b[:], np.float32); ab = b - a
        t = np.clip(((P - a) @ ab) / (ab @ ab), 0, 1); return np.linalg.norm(P - (a + t[:, None] * ab), axis=1), t
    sm = lambda e0, e1, x: (lambda t: t * t * (3 - 2 * t))(np.clip((x - e0) / (e1 - e0), 0, 1))
    W = {}
    dh = np.linalg.norm(P - np.array(_p(HEAD)[:], np.float32), axis=1)
    W['cat_head'] = sm(0.085, 0.055, dh)
    for k, (s, e, w) in LEGS.items():
        d1, t1 = seg(_p(s), _p(e)); d2, t2 = seg(_p(e), _p(w))
        near = sm(0.042, 0.028, np.minimum(d1, d2)) * sm(0.0, 0.25, np.where(d1 < d2, t1, 1.0)) * (1 - W['cat_head'])
        W[f'cat_{k}2'] = near * np.where(d2 < d1, 1.0, sm(0.6, 1.0, t1) * 0.5)
        W[f'cat_{k}1'] = near - W[f'cat_{k}2']
    rest = np.clip(1 - sum(W.values()), 0, 1)
    z = P[:, 2]
    W['cat_body'] = rest * sm(0.0, 0.06, z)                                 # the underside stays planted (it breathes up)
    W['cat_root'] = rest - W['cat_body']
    for name, w in W.items():
        vg = ob.vertex_groups.new(name=name)
        for i in np.nonzero(w > 1e-3)[0]: vg.add([int(i)], float(w[i]), 'REPLACE')
    md = ob.modifiers.new('rig', 'ARMATURE'); md.object = arm
    ob.parent = arm
    for b in arm.pose.bones: b.rotation_mode = 'QUATERNION'
    return arm


# ---------------------------------------------------------------- acts
def _key(arm, f):
    for b in arm.pose.bones:
        b.keyframe_insert('rotation_quaternion', frame=f); b.keyframe_insert('location', frame=f); b.keyframe_insert('scale', frame=f)


def _turn(pb, axis, ang):
    """A bone's local rotation by `ang` about an axis given in the armature's frame (its rest axes)."""
    ax = pb.bone.matrix_local.to_3x3().inverted() @ Vector(axis)
    pb.rotation_quaternion = pb.rotation_quaternion @ Quaternion(ax.normalized(), ang)


def act(arm, name, seconds, at, pose):
    """An act of `seconds`, the root set by `at(t)` (an armature-space matrix: the cat's place) and `pose(arm, t, T)`
    adding the rest (breathing, the head, the paws) every frame. A loop's motions must make whole cycles over it."""
    a = bpy.data.actions.new(name); a.use_fake_user = True
    arm.animation_data_create(); arm.animation_data.action = a
    if a.slots and arm.animation_data.action_slot is None: arm.animation_data.action_slot = a.slots[0]
    n = int(round(seconds * people.FPS)); root = arm.pose.bones['cat_root']
    for f in range(n + 1):
        t = f / people.FPS
        for b in arm.pose.bones: b.rotation_quaternion = Quaternion(); b.location = (0, 0, 0); b.scale = (1, 1, 1)
        M = at(t)                                                       # where the root goes (armature space)
        root.matrix = M @ root.bone.matrix_local
        bpy.context.view_layer.update()
        pose(arm, t, seconds)
        _key(arm, f + 1)
    a.frame_range = (1, n + 1)
    return a


def breathe(arm, t, T, rate=0.5, depth=0.022):
    """The body's slow rise and fall (a cat at rest: about one breath every two seconds), a whole number over T."""
    k = max(1, round(T * rate)); s = 1 + depth * (0.5 - 0.5 * math.cos(2 * math.pi * k * t / T))
    arm.pose.bones['cat_body'].scale = (1 + (s - 1) * 0.6, 1 + (s - 1) * 0.6, s)


def head(arm, yaw=0.0, pitch=0.0, roll=0.0):
    pb = arm.pose.bones['cat_head']
    _turn(pb, (0, 0, 1), yaw); _turn(pb, (1, 0, 0), pitch); _turn(pb, (0, 1, 0), roll)


def paw(arm, leg, curl):
    """A foreleg's push (kneading): the upper bone swings, the lower one curls back; `curl` about -1..1."""
    _turn(arm.pose.bones[f'cat_{leg}1'], (0, 0, 1), 0.16 * curl)
    _turn(arm.pose.bones[f'cat_{leg}2'], (0, 0, 1), -0.3 * curl)
