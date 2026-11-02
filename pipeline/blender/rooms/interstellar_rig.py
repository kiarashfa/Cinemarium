# The room's own rig: one small armature carries what moves in Murph's room besides the people (the door, the books
# Cooper knocks out from behind the shelf, the lunar lander model that falls with them and breaks in two), so the web
# plays them like any act (the room is a performer; its act and Murph's start together). Pushed from behind, the books
# slide out over the shelf's edge and fall tumbling to the boards; picked up, a part follows the hand that holds it
# (sampled from that person's act) and, set back, slides home onto its shelf.
import math, os, random
import bpy, bmesh
from mathutils import Vector, Matrix, Quaternion
import cine, people
import rooms.interstellar as R

FPS = people.FPS
NAME = 'room'
LANDER = os.path.join(cine.CACHE, 'objaverse', 'apollo_lunar_module_onebillionth.glb')
LANDER_H = 0.16                                    # the kit's height (true metres)


def _box_bm(bm, uvl, c, size, rnd):
    """A book centred at c, standing (its spine toward -x), its UVs from the spine atlas (as the shelved ones)."""
    R._book(bm, uvl, c.x - size[0] / 2, c.y - size[1] / 2, c.y + size[1] / 2, c.z - size[2] / 2, size[2], size[0], rnd)


def _lander_parts(M, col):
    """The lander model: the scan of the Apollo LM, decimated, recoloured as the film's kit (gold foil below, grey
    above), scaled to LANDER_H; split at the stages' join into the descent stage and the ascent stage. Returns two
    bmesh-ready (verts, faces, material index) lists in a frame where the model stands at the origin."""
    if not os.path.exists(LANDER):
        cine.log('no lander model:', LANDER); return None
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=LANDER)
    new = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    bpy.context.view_layer.update()
    bm = bmesh.new()
    for o in new:
        me = o.data.copy(); me.transform(o.matrix_world); tmp = bmesh.new(); tmp.from_mesh(me); tmp.to_mesh(me); bm.from_mesh(me); bpy.data.meshes.remove(me)
    for o in [o for o in bpy.data.objects if o not in before]: bpy.data.objects.remove(o, do_unlink=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    lo = Vector([min(v.co[i] for v in bm.verts) for i in range(3)]); hi = Vector([max(v.co[i] for v in bm.verts) for i in range(3)])
    s = LANDER_H / (hi.z - lo.z); c = (lo + hi) / 2
    bm.transform(Matrix.Scale(s, 4) @ Matrix.Translation(Vector((-c.x, -c.y, -lo.z))))
    me = bpy.data.meshes.new('lander_tmp'); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new('lander_tmp', me); col.objects.link(ob)
    if len(me.polygons) > 9000:
        d = ob.modifiers.new('dec', 'DECIMATE'); d.ratio = 9000 / len(me.polygons); cine.apply_modifiers(ob)
    split = LANDER_H * 0.5                                                         # the descent stage's top
    out = {'descent': [], 'ascent': []}
    me = ob.data
    for p in me.polygons:
        cz = sum(me.vertices[i].co.z for i in p.vertices) / len(p.vertices)
        key = 'descent' if cz < split else 'ascent'
        out[key].append(([me.vertices[i].co.copy() for i in p.vertices], 0 if key == 'descent' else 1))
    bpy.data.objects.remove(ob, do_unlink=True)
    return out


def make_rig(books, M, col):
    """An armature at the room's origin: a root, the door (its bone at the hinge), a bone per book that falls (at its
    place on the shelf) and per stage of the lander; one mesh, each part skinned wholly to its bone. Returns (armature,
    mesh); the parts' rest points (true metres) are kept on the armature."""
    rnd = random.Random(7)
    arm = bpy.data.objects.new(NAME, bpy.data.armatures.new(NAME)); col.objects.link(arm)
    bpy.context.view_layer.objects.active = arm; arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones
    root = eb.new(f'{NAME}_root'); root.head = Vector((0, 0, 0)); root.tail = Vector((0, 0, 0.1))
    hinge = Vector((R.P1 - 0.025, R.DOOR[1] - 0.005, 0.0))
    parts = {'door': hinge}
    xb = R.SHELF_X + 0.015
    for k, (y0, y1, h, d) in enumerate(books['falls']):
        parts[f'book{k}'] = Vector((xb + d / 2, (y0 + y1) / 2, books['fall_z'] + h / 2))
    for k, (y0, y1, h, d) in enumerate(books['stay']):
        parts['stay'] = Vector((xb + d / 2, (y0 + y1) / 2, books['stay_z'] + h / 2))
    ly = sum(books['lander']) / 2
    parts['lander_a'] = Vector((R.SHELF_X + 0.13, ly, books['fall_z']))                      # the descent stage: its foot
    parts['lander_b'] = Vector((R.SHELF_X + 0.13, ly, books['fall_z'] + LANDER_H * 0.5))     # the ascent stage: on it
    for n, p in parts.items():
        b = eb.new(f'{NAME}_{n}'); b.head = p; b.tail = p + Vector((0, 0, 0.08)); b.parent = root
    bpy.ops.object.mode_set(mode='OBJECT')
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); groups = {}
    mats = [M['stain'], M['brass'], M['white'], M['books'], M['lander_gold'], M['lander_grey']]
    def grab(name, build):
        n0 = len(bm.verts); f0 = len(bm.faces); build()
        bm.verts.ensure_lookup_table(); groups[f'{NAME}_{name}'] = list(range(n0, len(bm.verts)))
    # the door: its leaf built about the hinge
    def door():
        tmp = cine.coll('_tmp')
        for o in R.door_leaf('door', R.DOOR[1] - R.DOOR[0] - 0.01, R.DOOR_H - 0.012, M, tmp):
            bpy.context.view_layer.update()
            me = o.data.copy(); me.transform(Matrix.Translation(hinge) @ o.matrix_basis)
            idx = mats.index(o.material_slots[0].material) if o.material_slots[0].material in mats else 0
            for p in me.polygons: p.material_index = idx
            bm.from_mesh(me); bpy.data.meshes.remove(me); bpy.data.objects.remove(o, do_unlink=True)
    grab('door', door)
    for k, (y0, y1, h, d) in enumerate(books['falls']):
        def b_(k=k, y0=y0, y1=y1, h=h, d=d):
            n = len(bm.faces); R._book(bm, uvl, xb, y0, y1, books['fall_z'], h, d, rnd)
            for f in list(bm.faces)[n:]: f.material_index = 3
        grab(f'book{k}', b_)
    for (y0, y1, h, d) in books['stay']:
        def s_():
            n = len(bm.faces); R._book(bm, uvl, xb, y0, y1, books['stay_z'], h, d, rnd)
            for f in list(bm.faces)[n:]: f.material_index = 3
        grab('stay', s_)
    lp = _lander_parts(M, col)
    for key, bone in (('descent', 'lander_a'), ('ascent', 'lander_b')):
        def l_(key=key):
            foot = parts['lander_a']
            if lp is None:
                c = foot + Vector((0, 0, LANDER_H * (0.25 if key == 'descent' else 0.72)))
                vs = [bm.verts.new(c + Vector((sx * 0.05, sy * 0.05, sz * 0.035))) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
                for ids in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)): bm.faces.new([vs[i] for i in ids]).material_index = 4 if key == 'descent' else 5
                return
            for co, mi in lp[key]:
                vs = [bm.verts.new(foot + q) for q in co]
                try: bm.faces.new(vs).material_index = 4 + mi
                except ValueError: pass
        grab(bone, l_)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME); bm.to_mesh(me); bm.free()
    for m in mats: me.materials.append(m)
    mesh = bpy.data.objects.new(f'{NAME}_parts', me); col.objects.link(mesh)
    for bone, ids in groups.items():
        vg = mesh.vertex_groups.new(name=bone); vg.add(ids, 1.0, 'REPLACE')
    md = mesh.modifiers.new('rig', 'ARMATURE'); md.object = arm; mesh.parent = arm
    for o in (arm, mesh): o['person'] = NAME
    for pb in arm.pose.bones: pb.rotation_mode = 'QUATERNION'
    arm['rest'] = {f'{NAME}_{n}': list(p) for n, p in parts.items()}
    return arm, mesh


class Track:
    """One act of the rig: where every part is at every frame (position of its rest point, rotation about it), keyed
    onto its bones at the end."""
    def __init__(self, arm, n):
        self.arm, self.n = arm, n
        self.rest = {k: Vector(v) for k, v in arm['rest'].items()}
        self.track = {k: [(self.rest[k].copy(), Quaternion()) for _ in range(n + 1)] for k in self.rest}

    def set(self, part, f, pos, rot=Quaternion()):
        part = part if part.startswith(NAME) else f'{NAME}_{part}'
        if 0 <= f <= self.n: self.track[part][f] = (pos.copy(), rot.copy())

    def get(self, part, f):
        part = part if part.startswith(NAME) else f'{NAME}_{part}'
        return self.track[part][max(0, min(self.n, f))]

    def hold_from(self, part, f0, f1=None):
        p, q = self.get(part, f0)
        for f in range(f0, (self.n if f1 is None else f1) + 1): self.set(part, f, p, q)

    def key(self, action_name, f_start=1):
        arm = self.arm; act = bpy.data.actions.new(action_name); act.use_fake_user = True
        arm.animation_data_create(); arm.animation_data.action = act
        if act.slots and arm.animation_data.action_slot is None: arm.animation_data.action_slot = act.slots[0]
        for part, frames in self.track.items():
            pb = arm.pose.bones[part]; rest = self.rest[part]; L = pb.bone.matrix_local
            for f, (pos, rot) in enumerate(frames):
                T = Matrix.Translation(pos) @ rot.to_matrix().to_4x4() @ Matrix.Translation(-rest)
                pb.matrix = T @ L
                pb.keyframe_insert('location', frame=f_start + f); pb.keyframe_insert('rotation_quaternion', frame=f_start + f)
        root = arm.pose.bones[f'{NAME}_root']
        for f in (f_start, f_start + self.n):
            root.keyframe_insert('location', frame=f); root.keyframe_insert('rotation_quaternion', frame=f)
        act.frame_range = (f_start, f_start + self.n)
        return act


def rest_act(arm, name, seconds=4.0):
    """Nothing moving: the door shut, the books on their shelves, the lander beside them."""
    return Track(arm, int(seconds * FPS)).key(name)


# ---------------------------------------------------------------- what the parts do
def door(L, f0, f1, a0, a1):
    """The door swung from a0 to a1 (radians, + opens into the room) between f0 and f1, eased."""
    hinge = L.rest[f'{NAME}_door']
    for f in range(f0, L.n + 1):
        u = min(1.0, max(0.0, (f - f0) / max(1, f1 - f0))); u = u * u * (3 - 2 * u)
        L.set('door', f, hinge, Quaternion(Vector((0, 0, 1)), a0 + (a1 - a0) * u))


def fall(L, part, f0, land, yaw, rnd, push=0.22, flat=True, spin=None):
    """A part pushed out from behind at f0: it slides `push` metres out over the shelf's edge (-x), tips and drops,
    tumbling, to `land` (its rest point on the boards: the floor under a book lying flat), turned `yaw` about z; a
    small bounce; it lies there to the end."""
    p0, q0 = L.get(part, f0)
    n_slide = int(0.22 * FPS)
    for i in range(n_slide + 1):
        u = i / n_slide; u = u * u
        L.set(part, f0 + i, p0 + Vector((-push * u, 0, 0)), q0)
    fs = f0 + n_slide; ps = p0 + Vector((-push, 0, 0))
    h = ps.z - land.z; T_ = math.sqrt(max(2 * max(h, 0.05) / 9.81, 0.05)) * 1.15; nf = max(3, int(T_ * FPS))
    q_land = Quaternion(Vector((0, 0, 1)), yaw) @ (Quaternion(Vector((1, 0, 0)), math.pi / 2 * (1 if rnd.random() < 0.5 else -1)) if flat else Quaternion())
    if spin: q_land = spin @ q_land
    for i in range(nf + 1):
        u = i / nf
        p = ps.lerp(land, u); p.z = ps.z + (land.z - ps.z) * u * u
        q = q0.slerp(q_land, min(1.0, u * 1.25))
        L.set(part, fs + i, p, q)
    fl = fs + nf
    for i in range(1, int(0.25 * FPS)):
        u = i / (0.25 * FPS)
        L.set(part, fl + i, land + Vector((0, 0, 0.025 * math.sin(math.pi * u) * (1 - u))), q_land)
    L.hold_from(part, fl + int(0.25 * FPS) - 1)
    return fl


def carry(L, part, f_grab, f_rel, hands, settle=0.45, home=None):
    """A part in a hand from f_grab to f_rel: it keeps the place relative to the hand it had when the hand closed on
    it (`hands`: {frame: hand matrix, world}); set down at f_rel it slides `settle` seconds to `home` (its rest on the
    shelf, by default) and stays."""
    p0, q0 = L.get(part, f_grab)
    M0 = Matrix.Translation(p0) @ q0.to_matrix().to_4x4()
    H0 = hands[min(hands, key=lambda f: abs(f - f_grab))]
    off = H0.inverted() @ M0
    last = M0
    for f in range(f_grab, f_rel + 1):
        H = hands.get(f) or hands[min(hands, key=lambda g: abs(g - f))]
        Mf = H @ off; last = Mf
        L.set(part, f, Mf.to_translation(), Mf.to_quaternion())
    tgt_p, tgt_q = (home if home else (L.rest[part if part.startswith(NAME) else f'{NAME}_{part}'], Quaternion()))
    n = int(settle * FPS)
    for i in range(1, n + 1):
        u = i / n; u = u * u * (3 - 2 * u)
        L.set(part, f_rel + i, last.to_translation().lerp(tgt_p, u), last.to_quaternion().slerp(tgt_q, u))
    L.hold_from(part, f_rel + n)
