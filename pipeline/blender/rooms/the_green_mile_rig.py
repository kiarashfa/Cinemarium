# E Block's own rig: one armature carries what moves besides the people (the entry door, Coffey's cell door, his
# handcuffs and leg irons, the chain Percy leads him by, the mouse), so the web plays them like any act (the room is
# a performer; its act and Brutal's start together). What is not there waits shrunk to nothing. Built in the module's
# own metres (the block's true size times SCALE).
import math
import bpy, bmesh
from mathutils import Vector, Matrix, Quaternion
import cine, people
import rooms.the_green_mile as R

FPS = people.FPS
NAME = 'room'
S = R.SCALE
P = lambda x, y, z=0.0: Vector((x, y, z)) * S
HIDE = P(-5.6, -2.0, 1.2)                                  # where a part waits, shrunk (in the passage behind the end wall)
ENTRY_HINGE = P(R.END_X - 0.05, R.ENTRY[0] + 0.02, 0)      # the entry door hangs on its -y jamb, opens into the passage
CELL_A = R.END_X + R.COFFEY_CELL * R.PITCH + R.PIER / 2      # Coffey's cell front: its first upright
CELL_DOOR = (CELL_A + 0.02, CELL_A + 0.8)                  # the door's span (x, true metres)
CELL_HINGE = P(CELL_DOOR[0] - 0.01, R.CELL_Y + 0.07, 0)
CELL_OPEN = -math.pi / 2                                   # open: swung out into the Mile
MOUSE_LEN = 0.165                                          # nose to tail tip, true metres
MOUSE_HOME = P(R.RIGHT - 0.32, sum(R.RESTRAINT) / 2, 0)    # under the restraint room's door
PARTS = ('entry', 'celldoor', 'cuff_l', 'cuff_r', 'ank_l', 'ank_r', 'lead_a', 'lead_b', 'mouse')


def make_rig(M, col):
    """An armature at the room's origin: a root and a bone per moving part, at the part's rest point; one mesh, each
    part skinned to its bone (a chain's links blended between its two ends' bones). Returns (armature, mesh)."""
    rest = {'entry': ENTRY_HINGE.copy(), 'celldoor': CELL_HINGE.copy(),
            'cuff_l': P(0.0, -1.0, 1.0), 'cuff_r': P(0.22, -1.0, 1.0), 'ank_l': P(0.0, -1.5, 0.08), 'ank_r': P(0.4, -1.5, 0.08),
            'lead_a': P(1.0, -1.0, 1.0), 'lead_b': P(1.6, -1.0, 1.0), 'mouse': MOUSE_HOME.copy()}
    arm = bpy.data.objects.new(NAME, bpy.data.armatures.new(NAME)); col.objects.link(arm)
    bpy.context.view_layer.objects.active = arm; arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones
    root = eb.new(f'{NAME}_root'); root.head = Vector((0, 0, 0)); root.tail = Vector((0, 0, 0.1))
    for n, p in rest.items():
        b = eb.new(f'{NAME}_{n}'); b.head = p; b.tail = p + Vector((0, 0, 0.06)); b.parent = root
    bpy.ops.object.mode_set(mode='OBJECT')
    steel = _m('chain'); mats = [M['door_steel'], M['iron'], M['iron_dark'], M['rivet'], M['black'], steel, _m('mouse'), _m('mouse_eye')]
    idx = {m.name: i for i, m in enumerate(mats)}
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); dl = bm.verts.layers.deform.verify()
    groups = {}                                                  # bone name -> its vertex group's index (in order)

    def gi(part):
        b = f'{NAME}_{part}'
        if b not in groups: groups[b] = len(groups)
        return groups[b]

    def add(objs, weights, T=Matrix.Identity(4)):
        """Fold built objects into the rig's mesh (their own materials); weights(co) -> {part: w} per vertex."""
        bpy.context.view_layer.update()
        for o in objs:
            me = o.data.copy(); me.transform(T @ o.matrix_basis)
            mi = idx.get(o.material_slots[0].material.name, 0) if o.material_slots else 0
            for p_ in me.polygons: p_.material_index = mi
            n0 = len(bm.verts); bm.from_mesh(me); bm.verts.ensure_lookup_table()
            for v in bm.verts[n0:]:
                for part, w in weights(v.co).items():
                    if w > 0: v[dl][gi(part)] = w
            bpy.data.meshes.remove(me); bpy.data.objects.remove(o, do_unlink=True)

    tmp = cine.coll('_rigtmp')
    rigid = lambda part: (lambda co: {part: 1.0})
    # the entry door: riveted steel, closed in the doorway (along y from the hinge), its grille at eye height
    w = R.ENTRY[1] - R.ENTRY[0] - 0.04; h = R.DOOR_H - 0.03; x = R.END_X - 0.05
    y0 = R.ENTRY[0] + 0.02
    objs = [cine.box('ed', (0.06, w, h), (x, y0 + w / 2, h / 2 + 0.015), M['door_steel'], bev=0.004, collection=tmp)]
    for k, z in enumerate((0.3, 0.98, 1.66)):
        objs.append(cine.box(f'es{k}', (0.072, w - 0.06, 0.08), (x, y0 + w / 2, z), M['door_steel'], bev=0.003, collection=tmp))
        for j in range(7):
            for s in (-1, 1):
                objs.append(cine.cyl(f'er{k}{j}{s}', 0.009, 0.08, (x, y0 + 0.06 + (w - 0.12) * j / 6, z), M['rivet'], rot=(0, math.pi / 2, 0), seg=6, collection=tmp))
    gy, gz = y0 + w / 2, 1.5                                         # the viewing grille: a dark slot behind diamond mesh
    objs.append(cine.box('eg', (0.08, 0.3, 0.2), (x, gy, gz), M['black'], bev=0, collection=tmp))
    for k in range(-4, 5):
        for s in (-1, 1):
            objs.append(cine.box(f'em{k}{s}', (0.09, 0.012, 0.3), (x, gy + k * 0.035, gz), M['iron_dark'], rot=(s * 0.6, 0, 0), bev=0, collection=tmp))
    objs.append(cine.box('eh', (0.1, 0.06, 0.14), (x, y0 + w - 0.12, 1.02), M['iron_dark'], bev=0.004, collection=tmp))
    add(objs, rigid('entry'), Matrix.Scale(S, 4))
    # Coffey's cell door: strap iron like the fronts, its lock box and food slot; built closed (along x from the hinge)
    d0, d1 = CELL_DOOR; y = R.CELL_Y + 0.07; hh = R.FRONT_H - 0.04
    objs = []
    for k, xx in enumerate((d0 + 0.025, d1 - 0.025)):
        objs.append(cine.box(f'cs{k}', (0.05, 0.075, hh), (xx, y, hh / 2 + 0.02), M['iron'], bev=0.003, collection=tmp))
    for k, z in enumerate((0.05, hh - 0.01)):
        objs.append(cine.box(f'cr{k}', (d1 - d0, 0.07, 0.06), ((d0 + d1) / 2, y, z), M['iron'], bev=0.003, collection=tmp))
    n = 6
    for k in range(n):
        objs.append(cine.box(f'cv{k}', (0.022, 0.05, hh - 0.1), (d0 + 0.05 + (d1 - d0 - 0.1) * (k + 0.5) / n, y, hh / 2 + 0.02), M['iron'], bev=0, collection=tmp))
    for k, z in enumerate((0.45, 0.9, 1.35, 1.8)):
        for s in (-1, 1):
            objs.append(cine.box(f'ch{k}{s}', (d1 - d0 - 0.06, 0.012, 0.055), ((d0 + d1) / 2, y + s * 0.031, z), M['iron'], bev=0, collection=tmp))
    objs.append(cine.box('cl', (0.16, 0.09, 0.24), (d1 - 0.1, y - 0.01, 1.08), M['door_steel'], bev=0.006, collection=tmp))
    objs.append(cine.box('ck', (0.02, 0.004, 0.04), (d1 - 0.1, y - 0.058, 1.08), M['black'], bev=0, collection=tmp))
    objs.append(cine.box('cf', (0.36, 0.09, 0.12), ((d0 + d1) / 2, y - 0.01, 1.24), M['door_steel'], bev=0.004, collection=tmp))
    add(objs, rigid('celldoor'), Matrix.Scale(S, 4))
    # the handcuffs and the leg irons: a ring at each end, a chain of links between (blended from one end to the other)
    def bracelet(c, r, t, part):
        objs = [_torus(f'br_{part}', c, r, t, steel, tmp, axis='x')]
        add(objs, rigid(part))
    def chain(a, b, pa, pb, link=0.034, wire=0.0055, sag=0.0):
        L = (b - a).length; n = max(2, int(L / (link * 0.78))); d = (b - a).normalized()
        for k in range(n):
            u = (k + 0.5) / n; c = a.lerp(b, u) - Vector((0, 0, sag * 4 * u * (1 - u)))
            o = _link(f'ln_{pa}{k}', c, d, link, wire, k % 2 == 1, steel, tmp)
            add([o], lambda co, u=u: {pa: 1 - u, pb: u})
    for part in ('cuff_l', 'cuff_r'): bracelet(rest[part], 0.042 * S, 0.008 * S, part)
    chain(rest['cuff_l'], rest['cuff_r'], 'cuff_l', 'cuff_r', link=0.034 * S, wire=0.006 * S)
    for part in ('ank_l', 'ank_r'): bracelet(rest[part], 0.06 * S, 0.01 * S, part)
    chain(rest['ank_l'], rest['ank_r'], 'ank_l', 'ank_r', link=0.04 * S, wire=0.007 * S)
    chain(rest['lead_a'], rest['lead_b'], 'lead_a', 'lead_b', link=0.034 * S, wire=0.006 * S)
    # the mouse (a scan, made light): its nose toward +x, standing on the floor at its rest point
    add(_mouse(tmp), rigid('mouse'), Matrix.Translation(rest['mouse']))
    bpy.data.collections.remove(tmp)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME); bm.to_mesh(me); bm.free()
    for m in mats: me.materials.append(m)
    mesh = bpy.data.objects.new(f'{NAME}_parts', me); col.objects.link(mesh)
    for bone, i in sorted(groups.items(), key=lambda kv: kv[1]): mesh.vertex_groups.new(name=bone)
    for p in me.polygons: p.use_smooth = True
    md = mesh.modifiers.new('rig', 'ARMATURE'); md.object = arm; mesh.parent = arm
    for o in (arm, mesh): o['person'] = NAME
    for pb in arm.pose.bones: pb.rotation_mode = 'QUATERNION'
    arm['rest'] = {f'{NAME}_{n}': list(p) for n, p in rest.items()}
    return arm, mesh


def _torus(name, c, r, t, mat, col, axis='x', seg=14, ring=6):
    bm = bmesh.new()
    rings = []
    for i in range(seg):
        a = 2 * math.pi * i / seg; ca, sa = math.cos(a), math.sin(a)
        rings.append([bm.verts.new(c + Vector((0, (r + t * math.cos(2 * math.pi * j / ring)) * ca, (r + t * math.cos(2 * math.pi * j / ring)) * sa))
                                   + Vector((t * math.sin(2 * math.pi * j / ring), 0, 0))) for j in range(ring)])
    for i in range(seg):
        A, B = rings[i], rings[(i + 1) % seg]
        for j in range(ring): bm.faces.new((A[j], A[(j + 1) % ring], B[(j + 1) % ring], B[j]))
    return cine._mesh_obj(name, bm, mat, col)


def _link(name, c, d, L, t, turned, mat, col):
    """One oval chain link centred at c, its length along d, lying flat or turned a quarter."""
    up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    side = d.cross(up).normalized(); nrm = side.cross(d).normalized()
    if turned: side, nrm = nrm, side
    bm = bmesh.new(); seg, ring = 10, 4; rings = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        p = c + d * math.cos(a) * (L / 2 - t) + side * math.sin(a) * (L * 0.3)
        out = (d * math.cos(a) + side * math.sin(a)).normalized()
        rings.append([bm.verts.new(p + (out * math.cos(2 * math.pi * j / ring) + nrm * math.sin(2 * math.pi * j / ring)) * t) for j in range(ring)])
    for i in range(seg):
        A, B = rings[i], rings[(i + 1) % seg]
        for j in range(ring): bm.faces.new((A[j], A[(j + 1) % ring], B[(j + 1) % ring], B[j]))
    return cine._mesh_obj(name, bm, mat, col)


def _mouse(col):
    """The house mouse scan: whiskers dropped, the body thinned to a few thousand faces, scaled to a real mouse,
    turned so its nose looks along +x, its feet on z = 0 at the origin."""
    path = cine.CACHE + '/objaverse/house_mouse_sekinger.glb'
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    keep = []
    for o in new:
        if o.type != 'MESH' or any(m and 'moustache' in m.name for m in o.data.materials): bpy.data.objects.remove(o, do_unlink=True); continue
        keep.append(o)
    bpy.context.view_layer.update()
    for o in keep:
        mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
        if len(o.data.polygons) > 4000:
            md = o.modifiers.new('thin', 'DECIMATE'); md.ratio = 3000 / len(o.data.polygons)
            with bpy.context.temp_override(object=o, active_object=o): bpy.ops.object.modifier_apply(modifier=md.name)
    for o in [o for o in bpy.data.objects if o in new and o.type == 'EMPTY']: bpy.data.objects.remove(o, do_unlink=True)
    pts = [o.matrix_world @ v.co for o in keep for v in o.data.vertices]
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    k = MOUSE_LEN * S / (hi.x - lo.x)
    nose_x = lo.x                                                  # the scan's nose is at its -x end
    body_c = Vector((nose_x + (hi.x - lo.x) * 0.3, (lo.y + hi.y) / 2, lo.z))
    T = Matrix.Rotation(math.pi, 4, 'Z') @ Matrix.Scale(k, 4) @ Matrix.Translation(-body_c)   # nose to +x, about the body
    for o in keep:
        o.matrix_world = T @ o.matrix_world
        for sl in o.material_slots:
            src = sl.material
            if src and 'eye' in src.name.lower(): sl.material = _m('mouse_eye')
            else:
                img = next((n.image for n in src.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image), None) if src else None
                sl.material = _m('mouse', img)
        if not o.data.uv_layers: o.data.uv_layers.new(name='UVMap')
        o.data.uv_layers[0].name = 'UVMap'
    return keep


_MATS = {}


def _m(name, img=None):
    """The rig's own materials (the mouse's coat browned, as Mr. Jingles)."""
    if name in _MATS: return _MATS[name]
    if name == 'chain': m = cine.material('gm_chain_steel', (0.42, 0.42, 0.4), rough=0.32, metal=1.0)
    elif name == 'mouse_eye': m = cine.material('gm_mouse_eye', (0.01, 0.01, 0.01), rough=0.08, coat=1.0)
    else:
        m = cine.material('gm_mouse_coat', (0.42, 0.3, 0.2), rough=0.8, sheen=0.4, sheen_tint=(0.45, 0.35, 0.25))
        if img is not None:
            nt = m.node_tree; p = nt.nodes['Principled BSDF']
            t = nt.nodes.new('ShaderNodeTexImage'); t.image = img
            mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 1.0
            nt.links.new(t.outputs['Color'], mix.inputs[6]); mix.inputs[7].default_value = (0.95, 0.7, 0.5, 1)
            nt.links.new(mix.outputs[2], p.inputs['Base Color'])
    _MATS[name] = m; return m


# ---------------------------------------------------------------- tracks
class Track:
    """One act of the rig: where every part is at every frame (its rest point's position, a rotation about it, a
    scale), keyed onto its bones at the end."""
    def __init__(self, arm, n, shown=('entry', 'celldoor')):
        self.arm, self.n = arm, n
        self.rest = {k: Vector(v) for k, v in arm['rest'].items()}
        self.track = {k: [(self.rest[k].copy(), Quaternion(), 1.0 if any(k.endswith(s) for s in shown) else 0.0) for _ in range(n + 1)] for k in self.rest}

    def _k(self, part): return part if part.startswith(NAME) else f'{NAME}_{part}'

    def set(self, part, f, pos, rot=Quaternion(), s=1.0):
        if 0 <= f <= self.n: self.track[self._k(part)][f] = (pos.copy(), rot.copy(), s)

    def get(self, part, f):
        return self.track[self._k(part)][max(0, min(self.n, f))]

    def key(self, action_name, f_start=1):
        arm = self.arm; act = bpy.data.actions.new(action_name); act.use_fake_user = True
        arm.animation_data_create(); arm.animation_data.action = act
        if act.slots and arm.animation_data.action_slot is None: arm.animation_data.action_slot = act.slots[0]
        for part, frames in self.track.items():
            pb = arm.pose.bones[part]; rest = self.rest[part]; L = pb.bone.matrix_local
            for f, (pos, rot, s) in enumerate(frames):
                T = Matrix.Translation(pos) @ rot.to_matrix().to_4x4() @ Matrix.Scale(max(s, 1e-4), 4) @ Matrix.Translation(-rest)
                pb.matrix = T @ L
                for ch in ('location', 'rotation_quaternion', 'scale'): pb.keyframe_insert(ch, frame=f_start + f)
        root = arm.pose.bones[f'{NAME}_root']
        for f in (f_start, f_start + self.n):
            for ch in ('location', 'rotation_quaternion', 'scale'): root.keyframe_insert(ch, frame=f)
        act.frame_range = (f_start, f_start + self.n)
        return act


def ease(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)


def door_angle(keys, f):
    """A door's angle at frame f from (frame, angle) keys, eased between them."""
    if f <= keys[0][0]: return keys[0][1]
    for (f0, a0), (f1, a1) in zip(keys, keys[1:]):
        if f <= f1: return a0 + (a1 - a0) * ease((f - f0) / max(1, f1 - f0))
    return keys[-1][1]
