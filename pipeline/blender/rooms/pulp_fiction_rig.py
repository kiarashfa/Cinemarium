# The room's own rig: one armature carries what moves in apartment 49 besides the people (the lift's doors, the front
# door, the bathroom door, the bar's cupboard door, the dinette table and what is on it, the briefcase and its lid,
# the three guns, their muzzle flashes, the stains, the bullet holes in the wall), so the web plays them like any act
# (the room is a performer; its act and Jules's start together). What is not there yet waits shrunk to nothing.
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix, Quaternion
import cine, people
import rooms.pulp_fiction as R

FPS = people.FPS
NAME = 'room'
TABLE_TOP = R.TABLE_H
# what is on the table (true metres): Brett's burger in its paper, two more wrapped, the bag, the cup, the fries
FOOD = {'burger': Vector((-1.12, 0.42, TABLE_TOP + 0.035)), 'wrap0': Vector((-1.5, 0.62, TABLE_TOP + 0.02)), 'wrap1': Vector((-1.62, 0.12, TABLE_TOP + 0.02)),
        'bag': Vector((-1.32, 0.66, TABLE_TOP + 0.16)), 'cup': Vector((-1.2, 0.12, TABLE_TOP + 0.09)), 'fries': Vector((-1.4, 0.32, TABLE_TOP + 0.02))}
CASE_W, CASE_D, CASE_H = 0.46, 0.34, 0.1                                             # the case lying flat: across, deep, thick
CASE_IN = Vector((R.BAR[0] + 0.24, (R.CUPBOARD[0] + R.CUPBOARD[1]) / 2, 0.13))     # lying on the cupboard's floor
LID_HINGE = Vector((-CASE_D / 2, 0, CASE_H * 0.62))                                  # the lid's hinge, from the case's centre
HOLES = [Vector((R.LEFT + 0.004, y, z)) for y, z in ((-1.62, 1.52), (-1.4, 1.71), (-1.18, 1.38), (-1.48, 1.18), (-1.02, 1.6), (-1.3, 1.92))]
HIDE = Vector((-4.3, 2.9, 2.1))                                                     # where a part waits, shrunk (in the lift's roof: inside the module)


def make_rig(M, col):
    """An armature at the room's origin: a root and a bone per moving part, at the part's rest point; one mesh, each
    part skinned wholly to its bone. Returns (armature, mesh); the parts' rest points are kept on the armature."""
    arm = bpy.data.objects.new(NAME, bpy.data.armatures.new(NAME)); col.objects.link(arm)
    bpy.context.view_layer.objects.active = arm; arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones
    root = eb.new(f'{NAME}_root'); root.head = Vector((0, 0, 0)); root.tail = Vector((0, 0, 0.1))
    parts = {'lift_l': Vector((R.LIFT_X + 0.03, R.LIFT_DOOR[0], 0)), 'lift_r': Vector((R.LIFT_X + 0.03, R.LIFT_DOOR[1], 0)),
             'entry': Vector((R.ENTRY[1] - 0.01, (R.PART[0] + R.PART[1]) / 2, 0)), 'bathdoor': Vector((R.BATHDOOR[1] - 0.01, (R.PART[0] + R.PART[1]) / 2, 0)),
             'cupdoor': Vector((R.BAR[1] + 0.012, R.CUPBOARD[1], 0.12)),
             'table': Vector((R.TABLE.x, R.TABLE.y, 0)), 'case': CASE_IN.copy(), 'lid': CASE_IN + LID_HINGE,
             'gun_jules': HIDE.copy(), 'gun_vincent': HIDE.copy(), 'gun_fourth': HIDE.copy(),
             'flash_jules': HIDE.copy(), 'flash_vincent': HIDE.copy(), 'flash_fourth': HIDE.copy()}
    for k, p in FOOD.items(): parts[k] = p.copy()
    for k in range(3): parts[f'stain_roger{k}'] = HIDE.copy()
    for k in range(4): parts[f'stain_brett{k}'] = HIDE.copy()
    for k, p in enumerate(HOLES): parts[f'hole{k}'] = p.copy()
    for n, p in parts.items():
        b = eb.new(f'{NAME}_{n}'); b.head = p; b.tail = p + Vector((0, 0, 0.08)); b.parent = root
    bpy.ops.object.mode_set(mode='OBJECT')
    mats = [M['lift'], M['door'], M['brass'], M['trim'], M['laminate'], M['chrome'], M['paper'], _m('case'), _m('glow'), _m('gun'), _m('flash'),
            _m('blood'), _m('hole'), _m('bag'), _m('cup'), _m('burger'), _m('fries'), M['black']]
    idx = {m.name: i for i, m in enumerate(mats)}
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); groups = {}

    def grab(name, build):
        n0 = len(bm.verts); build(); bm.verts.ensure_lookup_table(); groups[f'{NAME}_{name}'] = list(range(n0, len(bm.verts)))

    def add(objs, T=Matrix.Identity(4)):
        """Fold built objects into the rig's mesh (by their own material), then delete them."""
        bpy.context.view_layer.update()
        for o in objs:
            me = o.data.copy(); me.transform(T @ o.matrix_basis)
            mi = idx.get(o.material_slots[0].material.name, 0) if o.material_slots else 0
            for p in me.polygons: p.material_index = mi
            bm.from_mesh(me); bpy.data.meshes.remove(me); bpy.data.objects.remove(o, do_unlink=True)

    tmp = cine.coll('_rigtmp')
    # the lift's two bronze leaves (closed: meeting in the middle)
    hw = (R.LIFT_DOOR[1] - R.LIFT_DOOR[0]) / 2
    for side, s in (('lift_l', 1), ('lift_r', -1)):
        p = parts[side]
        grab(side, lambda p=p, s=s: add([cine.box('lf', (0.03, hw, R.LIFT_H - 0.01), (p.x, p.y + s * hw / 2, (R.LIFT_H - 0.01) / 2), M['lift'], bev=0.003, collection=tmp),
                                         cine.box('lfl', (0.034, 0.012, R.LIFT_H - 0.3), (p.x, p.y + s * (hw - 0.01), R.LIFT_H / 2), M['chrome'], bev=0.002, collection=tmp)]))
    # the front door (hinged at its right jamb, its room face toward -y; '49' on its hall face) and the bathroom's
    def door(name, x0, x1, y, flip):
        w = x1 - x0 - 0.02
        objs = R.door_leaf(name, w, R.DOOR_H - 0.01, M, tmp, num='49' if name == 'entry' else None)
        T = Matrix.Translation((x1 - 0.01, y, 0)) @ Matrix.Rotation(math.pi, 4, 'Z')
        if flip: T = T @ Matrix.Scale(-1, 4, Vector((0, 1, 0)))
        add(objs, T)
    grab('entry', lambda: door('entry', R.ENTRY[0], R.ENTRY[1], (R.PART[0] + R.PART[1]) / 2, False))
    grab('bathdoor', lambda: door('bathdoor', R.BATHDOOR[0], R.BATHDOOR[1], (R.PART[0] + R.PART[1]) / 2, True))
    # the bar's cupboard door (kitchen side), hinged at its +y edge
    grab('cupdoor', lambda: add([cine.box('cd', (0.018, R.CUPBOARD[1] - R.CUPBOARD[0] - 0.02, 0.7), (R.BAR[1] + 0.009, (R.CUPBOARD[0] + R.CUPBOARD[1]) / 2, 0.47), M['trim'], bev=0.004, collection=tmp),
                                     cine.cyl('ck', 0.011, 0.02, (R.BAR[1] + 0.025, R.CUPBOARD[0] + 0.05, 0.72), M['brass'], rot=(0, math.pi / 2, 0), seg=10, collection=tmp)]))
    # the dinette: a round laminate top with a chrome band, four splayed chrome legs
    def table():
        c = Vector((R.TABLE.x, R.TABLE.y, 0)); objs = [cine.cyl('tt', R.TABLE_R, 0.03, c + Vector((0, 0, R.TABLE_H - 0.015)), M['laminate'], seg=48, collection=tmp),
                                                       cine.cyl('tb', R.TABLE_R + 0.008, 0.035, c + Vector((0, 0, R.TABLE_H - 0.02)), M['chrome'], seg=48, collection=tmp)]
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2
            from rooms.seinfeld import tube
            objs.append(tube('tl', [c + Vector((math.cos(a) * 0.12, math.sin(a) * 0.12, R.TABLE_H - 0.03)), c + Vector((math.cos(a) * 0.32, math.sin(a) * 0.32, 0.0))], 0.012, M['chrome'], tmp, seg=8))
        add(objs)
    grab('table', table)
    # the food: the burger in its paper (a bun, the patty, cheese), the wrapped ones, the paper bag, the cup and straw, fries
    for k in FOOD: grab(k, lambda k=k: add(_food(k, FOOD[k], tmp)))
    # the briefcase: black leather, brass locks and corners, a handle; the lid hinged along its back edge; inside, the glow
    grab('case', lambda: add(_case_body(CASE_IN, tmp)))
    grab('lid', lambda: add(_case_lid(CASE_IN, tmp)))
    # the guns (each built round its grip at the origin, its barrel along +x) and their flashes, all at HIDE
    for who, kind in (('jules', 'star'), ('vincent', 'colt'), ('fourth', 'magnum')):
        grab(f'gun_{who}', lambda kind=kind: add(_gun(kind, tmp), Matrix.Translation(HIDE)))
        grab(f'flash_{who}', lambda: add(_flash(tmp), Matrix.Translation(HIDE)))
    for k in range(3): grab(f'stain_roger{k}', lambda k=k: add(_stain(tmp, 0.05 + 0.01 * k, k), Matrix.Translation(HIDE)))
    for k in range(4): grab(f'stain_brett{k}', lambda k=k: add(_stain(tmp, 0.045 + 0.012 * (k % 2), k + 5), Matrix.Translation(HIDE)))
    for k, p in enumerate(HOLES):
        grab(f'hole{k}', lambda p=p, k=k: add([cine.cyl('h', 0.009, 0.004, p, _m('hole'), rot=(0, math.pi / 2, 0), seg=10, collection=tmp),
                                               cine.cyl('hr', 0.016, 0.002, p - Vector((0.001, 0, 0)), _m('hole_rim'), rot=(0, math.pi / 2, 0), seg=10, collection=tmp)]))
    bpy.data.collections.remove(tmp)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME); bm.to_mesh(me); bm.free()
    for m in mats: me.materials.append(m)
    me.materials.append(_m('hole_rim'))
    mesh = bpy.data.objects.new(f'{NAME}_parts', me); col.objects.link(mesh)
    for bone, ids in groups.items():
        vg = mesh.vertex_groups.new(name=bone); vg.add(ids, 1.0, 'REPLACE')
    md = mesh.modifiers.new('rig', 'ARMATURE'); md.object = arm; mesh.parent = arm
    for o in (arm, mesh): o['person'] = NAME
    for pb in arm.pose.bones: pb.rotation_mode = 'QUATERNION'
    arm['rest'] = {f'{NAME}_{n}': list(p) for n, p in parts.items()}
    return arm, mesh


_MATS = {}


def _m(name):
    """The rig's own materials."""
    if name in _MATS: return _MATS[name]
    tx = R.tx
    m = {'case': lambda: cine.material('pf_case_leather', (0.03, 0.028, 0.026), rough=0.38, coat=0.4, coat_rough=0.3),
         'glow': lambda: cine.material('pf_case_glow', (1.0, 0.72, 0.25), rough=0.4, emission=(1.0, 0.62, 0.16), emission_strength=6.0),
         'gun': lambda: cine.material('pf_gun_nickel', (0.72, 0.72, 0.7), rough=0.18, metal=1.0),
         'flash': lambda: cine.material('pf_muzzle_flash', (1.0, 0.86, 0.5), rough=0.5, emission=(1.0, 0.78, 0.36), emission_strength=24.0),
         'blood': lambda: cine.material('pf_stain', (0.2, 0.012, 0.01), rough=0.35, coat=0.3),
         'hole': lambda: cine.material('pf_bullet_hole', (0.012, 0.01, 0.01), rough=0.9),
         'hole_rim': lambda: cine.material('pf_hole_rim', (0.55, 0.53, 0.47), rough=0.9),
         'bag': lambda: cine.material('pf_kahuna_bag', rough=0.85, maps={'color': tx('bag_color.jpg')}, scale=1.0),
         'cup': lambda: cine.material('pf_kahuna_cup', rough=0.4, maps={'color': tx('cup_color.jpg')}, scale=1.0, coat=0.3),
         'burger': lambda: cine.material('pf_burger_bun', (0.62, 0.36, 0.14), rough=0.55),
         'fries': lambda: cine.material('pf_fries', (0.86, 0.66, 0.26), rough=0.6)}[name]()
    _MATS[name] = m; return m


def _food(k, p, col):
    from rooms.seinfeld import tube, uv_rect
    M = R
    out = []
    if k == 'burger':
        out.append(cine.box('paper', (0.2, 0.2, 0.003), p - Vector((0, 0, 0.033)), _m('fries') if False else bpy.data.materials['pf_paper'], rot=(0, 0, 0.4), bev=0, collection=col))
        out.append(cine.lathe('bun_lo', [(0.0, 0.0), (0.055, 0.0), (0.058, 0.012), (0.0, 0.016)], _m('burger'), loc=p - Vector((0, 0, 0.03)), seg=18, collection=col))
        out.append(cine.cyl('patty', 0.058, 0.014, p - Vector((0, 0, 0.008)), cine.material('pf_patty', (0.2, 0.1, 0.06), rough=0.7), seg=18, collection=col))
        out.append(cine.box('cheese', (0.1, 0.1, 0.003), p + Vector((0, 0, 0.0)), cine.material('pf_cheese', (0.95, 0.66, 0.12), rough=0.4), rot=(0, 0, 0.6), bev=0, collection=col))
        out.append(cine.lathe('bun_hi', [(0.0, 0.0), (0.058, 0.0), (0.054, 0.02), (0.036, 0.034), (0.0, 0.038)], _m('burger'), loc=p + Vector((0, 0, 0.003)), seg=18, collection=col))
    elif k.startswith('wrap'):
        out.append(cine.rounded_slab('w', 0.12, 0.12, 0.05, 0.03, p + Vector((0, 0, 0.005)), bpy.data.materials['pf_paper'], edge_bev=0.02, collection=col))
    elif k == 'bag':
        b = cine.box('bag', (0.2, 0.12, 0.32), p, _m('bag'), bev=0.004, collection=col); uv_rect(b, 'y'); out.append(b)
        out.append(cine.box('bag_fold', (0.2, 0.12, 0.03), p + Vector((0, 0, 0.17)), _m('bag'), rot=(0.3, 0, 0), bev=0.004, collection=col))
    elif k == 'cup':
        cp = cine.lathe('cup', [(0.0, -0.09), (0.04, -0.09), (0.05, 0.08), (0.052, 0.085), (0.0, 0.085)], _m('cup'), loc=p, seg=24, collection=col)
        me = cp.data; uv = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
        for poly in me.polygons:
            for li in poly.loop_indices:
                c = me.vertices[me.loops[li].vertex_index].co; uv.data[li].uv = ((math.atan2(c.y, c.x) / (2 * math.pi)) % 1.0, (c.z + 0.09) / 0.18)
        out.append(cp)
        out.append(tube('straw', [p + Vector((0, 0, 0.06)), p + Vector((0.01, 0.0, 0.2)), p + Vector((0.03, 0, 0.22))], 0.004, bpy.data.materials['pf_paper'], col, seg=6))
    elif k == 'fries':
        out.append(cine.box('fries_paper', (0.18, 0.14, 0.004), p - Vector((0, 0, 0.018)), bpy.data.materials['pf_paper'], rot=(0, 0, -0.3), bev=0, collection=col))
        rnd = random.Random(3)
        for j in range(14):
            out.append(cine.box('fry', (0.08, 0.008, 0.008), p + Vector((rnd.uniform(-0.05, 0.05), rnd.uniform(-0.04, 0.04), -0.012 + rnd.uniform(0, 0.012))), _m('fries'), rot=(0, rnd.uniform(-0.2, 0.2), rnd.uniform(0, 3.1)), bev=0, collection=col))
    return out


def _case_body(c, col):
    """The case's lower shell lying flat (its back edge toward -x, where the lid hinges), the brass locks on its
    front (+x) face, the handle; the glow inside (a lit pane just under the rim, seen when the lid is up)."""
    out = [cine.box('cb', (CASE_D, CASE_W, CASE_H * 0.62), c + Vector((0, 0, CASE_H * 0.31)), _m('case'), bev=0.008, collection=col),
           cine.box('glow', (CASE_D - 0.03, CASE_W - 0.03, 0.004), c + Vector((0, 0, CASE_H * 0.62 + 0.001)), _m('glow'), bev=0, collection=col)]
    for s in (-1, 1):
        out.append(cine.box('lock', (0.006, 0.05, 0.02), c + Vector((CASE_D / 2 + 0.003, s * 0.14, CASE_H * 0.58)), bpy.data.materials['pf_brass'], bev=0.002, collection=col))
    from rooms.seinfeld import tube
    out.append(tube('handle', [c + Vector((CASE_D / 2 + 0.005, -0.06, CASE_H * 0.5)), c + Vector((CASE_D / 2 + 0.03, -0.05, CASE_H * 0.5)),
                               c + Vector((CASE_D / 2 + 0.03, 0.05, CASE_H * 0.5)), c + Vector((CASE_D / 2 + 0.005, 0.06, CASE_H * 0.5))], 0.007, _m('case'), col, seg=6))
    return out


def _case_lid(c, col):
    """The lid: the upper shell, hinged along the back (-x) edge at the rim's height."""
    return [cine.box('cl', (CASE_D, CASE_W, CASE_H * 0.38), c + Vector((0, 0, CASE_H * 0.62 + CASE_H * 0.19)), _m('case'), bev=0.008, collection=col),
            cine.box('cl_in', (CASE_D - 0.03, CASE_W - 0.03, 0.003), c + Vector((0, 0, CASE_H * 0.62 + 0.004)), _m('glow'), bev=0, collection=col)]


def _gun(kind, col):
    """A pistol round its grip (at the origin), its barrel along +x, the grip down: a nickel slide, the grip (pearl
    for the Colt and the Star; the Magnum's revolver long and silver)."""
    pearl = cine.material('pf_pearl_grip', (0.86, 0.84, 0.78), rough=0.3, coat=0.6)
    if kind == 'magnum':
        return [cine.box('g_frame', (0.17, 0.028, 0.04), Vector((0.06, 0, 0.055)), _m('gun'), bev=0.004, collection=col),
                cine.cyl('g_barrel', 0.011, 0.16, Vector((0.17, 0, 0.065)), _m('gun'), rot=(0, math.pi / 2, 0), seg=10, collection=col),
                cine.cyl('g_cyl', 0.022, 0.04, Vector((0.05, 0, 0.05)), _m('gun'), rot=(0, math.pi / 2, 0), seg=12, collection=col),
                cine.box('g_grip', (0.04, 0.03, 0.1), Vector((-0.01, 0, 0.0)), cine.material('pf_wood_grip', (0.25, 0.12, 0.06), rough=0.4), rot=(0, 0.3, 0), bev=0.006, collection=col)]
    L = 0.2 if kind == 'colt' else 0.19
    return [cine.box('g_slide', (L, 0.026, 0.035), Vector((L / 2 - 0.04, 0, 0.06)), _m('gun'), bev=0.003, collection=col),
            cine.box('g_frame', (0.1, 0.024, 0.02), Vector((0.03, 0, 0.035)), _m('gun'), bev=0.003, collection=col),
            cine.box('g_grip', (0.045, 0.03, 0.11), Vector((-0.012, 0, -0.01)), pearl, rot=(0, 0.25, 0), bev=0.006, collection=col)]


def _flash(col):
    """A muzzle flash: a small star of crossed blades, very bright, at the muzzle (origin), pointing +x."""
    out = []
    for k in range(3):
        a = k * math.pi / 3
        out.append(cine.box('fl', (0.12, 0.006, 0.05), Vector((0.06, 0, 0)), _m('flash'), rot=(a, 0, 0), bev=0, collection=col))
    out.append(cine.cyl('flc', 0.03, 0.03, Vector((0.015, 0, 0)), _m('flash'), rot=(0, math.pi / 2, 0), seg=10, collection=col))
    return out


def _stain(col, r, seed):
    """A stain soaked into a shirt: an irregular dark red disc, lying in the xz plane (facing -y) at the origin."""
    rnd = random.Random(seed); bm = bmesh.new(); n = 18
    c = bm.verts.new((0, 0, 0)); ring = []
    for i in range(n):
        a = 2 * math.pi * i / n; rr = r * (0.7 + 0.5 * rnd.random())
        ring.append(bm.verts.new((math.cos(a) * rr, 0.0, math.sin(a) * rr * (1.0 + 0.4 * (math.sin(a) < 0)))))
    for i in range(n): bm.faces.new((c, ring[(i + 1) % n], ring[i]))
    ob = cine._mesh_obj('stain', bm, _m('blood'), col, smooth=False)
    return [ob]


# ---------------------------------------------------------------- tracks
class Track:
    """One act of the rig: where every part is at every frame (its rest point's position, a rotation about it, a
    scale), keyed onto its bones at the end."""
    def __init__(self, arm, n):
        self.arm, self.n = arm, n
        self.rest = {k: Vector(v) for k, v in arm['rest'].items()}
        hidden = lambda k: (self.rest[k] - HIDE).length < 1e-6
        self.track = {k: [(self.rest[k].copy(), Quaternion(), 0.0 if hidden(k) or 'hole' in k else 1.0) for _ in range(n + 1)] for k in self.rest}

    def _k(self, part): return part if part.startswith(NAME) else f'{NAME}_{part}'

    def set(self, part, f, pos, rot=Quaternion(), s=1.0):
        if 0 <= f <= self.n: self.track[self._k(part)][f] = (pos.copy(), rot.copy(), s)

    def get(self, part, f):
        return self.track[self._k(part)][max(0, min(self.n, f))]

    def hold_from(self, part, f0, f1=None):
        p, q, s = self.get(part, f0)
        for f in range(f0, (self.n if f1 is None else f1) + 1): self.set(part, f, p, q, s)

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


def rest_act(arm, name, seconds=4.0):
    """Nothing moving: the doors shut, the table laid, the case in its cupboard, the guns and the stains away."""
    return Track(arm, int(seconds * FPS)).key(name)


def ease(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)


def swing(L, part, f0, f1, a0, a1, axis=(0, 0, 1)):
    """A hinged part (a door) swung from a0 to a1 radians about its rest point between f0 and f1, held after."""
    p = L.rest[L._k(part)]
    for f in range(f0, L.n + 1):
        u = ease((f - f0) / max(1, f1 - f0))
        L.set(part, f, p, Quaternion(Vector(axis), a0 + (a1 - a0) * u))


def slide(L, part, f0, f1, d0, d1):
    """A sliding part (a lift leaf) moved from offset d0 to d1 (vectors) between f0 and f1, held after."""
    p = L.rest[L._k(part)]
    for f in range(f0, L.n + 1):
        u = ease((f - f0) / max(1, f1 - f0)); L.set(part, f, p + d0.lerp(d1, u))


def follow(L, part, f0, f1, mats, off=Matrix.Identity(4), s=1.0):
    """A part riding on a moving frame (a hand, a chest) from f0 to f1: its pose = the frame's matrix @ off."""
    for f in range(f0, f1 + 1):
        H = mats.get(f) or mats[min(mats, key=lambda g: abs(g - f))]
        Mf = H @ off; L.set(part, f, Mf.to_translation(), Mf.to_quaternion(), s)


def carry(L, part, f_grab, f_rel, hands, settle=0.35, home=None):
    """A part in a hand from f_grab to f_rel (it keeps its place relative to the hand from when the hand closed on
    it); set down at f_rel it slides `settle` seconds to `home` ((position, rotation), or its rest) and stays."""
    p0, q0, s0 = L.get(part, f_grab)
    M0 = Matrix.Translation(p0) @ q0.to_matrix().to_4x4()
    H0 = hands.get(f_grab) or hands[min(hands, key=lambda f: abs(f - f_grab))]
    off = H0.inverted() @ M0; last = M0
    for f in range(f_grab, f_rel + 1):
        H = hands.get(f) or hands[min(hands, key=lambda g: abs(g - f))]
        last = H @ off; L.set(part, f, last.to_translation(), last.to_quaternion(), s0)
    tp, tq = home if home else (L.rest[L._k(part)], Quaternion())
    n = max(1, int(settle * FPS))
    for i in range(1, n + 1):
        u = ease(i / n); L.set(part, f_rel + i, last.to_translation().lerp(tp, u), last.to_quaternion().slerp(tq, u), s0)
    L.hold_from(part, f_rel + n)


def fall(L, part, f0, land, rot, dur=0.45, bounce=0.02):
    """A part knocked off (the table's things): from where it is at f0 it drops in an arc to `land`, turned to `rot`,
    a little bounce, then stays."""
    p0, q0, s0 = L.get(part, f0); n = max(3, int(dur * FPS))
    for i in range(n + 1):
        u = i / n; p = p0.lerp(land, u); p.z = p0.z + (land.z - p0.z) * u * u + 0.12 * math.sin(math.pi * u)
        L.set(part, f0 + i, p, q0.slerp(rot, min(1.0, u * 1.3)), s0)
    for i in range(1, int(0.2 * FPS)):
        u = i / (0.2 * FPS); L.set(part, f0 + n + i, land + Vector((0, 0, bounce * math.sin(math.pi * u) * (1 - u))), rot, s0)
    L.hold_from(part, f0 + n + int(0.2 * FPS) - 1)


def show(L, part, f0, f1=None, at=None):
    """A part that appears at f0 (a flash, a stain, a hole) and stays (to f1, or the end), at its rest or `at`."""
    p = L.rest[L._k(part)] if at is None else at
    for f in range(f0, (L.n if f1 is None else f1) + 1):
        cur = L.get(part, f); L.set(part, f, cur[0] if at is None and (cur[0] - HIDE).length > 1e-6 else p, cur[1], 1.0)
