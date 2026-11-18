# The room's own rig: one small armature carries what moves in Jefferies' studio besides the people (the hall door,
# the Montrachet and its cork, the two glasses), so the web plays them like any act (the room is a performer; its act
# and Lisa's start together). A part in a hand follows that hand (sampled from its owner's act); set down, it slides
# home and stays. The cork, pushed out by Jeff's thumb, jumps and drops onto the rug.
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix, Quaternion
import cine, people
import rooms.rear_window as R
from rooms.interstellar_rig import Track, door as swing, carry

FPS = people.FPS
NAME = 'room'
BOTTLE_H = 0.31                                     # a Burgundy bottle (true metres)
GLASS_H = 0.17


def door_leaf(w, h, M):
    """The hall door, cream, four raised panels a side, a brass knob: (verts, faces, material) parts built about its
    hinge (at the origin), closed along -y, its room face toward -x."""
    parts = []
    def add(size, c, mat, bev=0.004):
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(c) @ Matrix.Diagonal((*size, 1)))
        if bev: bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bev, segments=1, affect='EDGES')
        parts.append((bm, mat))
    t = 0.045
    add((t, w, h), Vector((0, -w / 2, h / 2)), M['trim'])
    for s in (-1, 1):
        for k, (z0, z1) in enumerate(((0.18, 0.92), (1.08, h - 0.16))):
            for j, (y0, y1) in enumerate(((-w + 0.11, -w / 2 - 0.04), (-w / 2 + 0.04, -0.11))):
                add((0.012, y1 - y0, z1 - z0), Vector((s * (t / 2 + 0.004), (y0 + y1) / 2, (z0 + z1) / 2)), M['trim'], bev=0.01)
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=8, radius=0.028, matrix=Matrix.Translation((s * (t / 2 + 0.04), -w + 0.07, 0.96)))
        parts.append((bm, M['brass']))
        add((0.04, 0.012, 0.012), Vector((s * (t / 2 + 0.02), -w + 0.07, 0.96)), M['brass'], bev=0)
    return parts


def _bottle(bm, foot):
    """The Montrachet: a Burgundy bottle (sloping shoulders), its label and capsule; the cork apart."""
    prof = [(0.0, 0.0), (0.04, 0.0), (0.041, 0.005), (0.041, 0.17), (0.035, 0.21), (0.022, 0.25), (0.015, 0.27), (0.015, BOTTLE_H - 0.012), (0.017, BOTTLE_H - 0.008), (0.0, BOTTLE_H - 0.008)]
    return _lathe_into(bm, prof, foot, 18)


def _lathe_into(bm, prof, c, seg):
    rings = [[bm.verts.new(c + Vector((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), z))) for i in range(seg)] for r, z in prof]
    faces = []
    for a, b in zip(rings, rings[1:]):
        for i in range(seg): faces.append(bm.faces.new((a[i], a[(i + 1) % seg], b[(i + 1) % seg], b[i])))
    if prof[0][0] > 1e-4: faces.append(bm.faces.new(list(reversed(rings[0]))))
    if prof[-1][0] > 1e-4: faces.append(bm.faces.new(rings[-1]))
    return faces


def make_rig(props, M, col):
    """An armature at the room's origin: a root; the door (its bone at the hinge); the bottle (at its foot, in the
    bucket), the cork (in its neck), two glasses (at their feet, on the little table). One mesh, each part skinned
    wholly to its bone; the ice bucket and its napkin skinned to the root (they never move). Returns (armature,
    mesh); the parts' rest points are kept on the armature."""
    arm = bpy.data.objects.new(NAME, bpy.data.armatures.new(NAME)); col.objects.link(arm)
    bpy.context.view_layer.objects.active = arm; arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones
    root = eb.new(f'{NAME}_root'); root.head = Vector((0, 0, 0)); root.tail = Vector((0, 0, 0.1))
    hinge = R.mx(Vector((R.PX0 - 0.03, R.DOOR[1] - 0.005, 0.0)))
    bucket = props['bucket']; foot = bucket + Vector((0, 0, 0.02))
    parts = {'door': hinge, 'bottle': foot, 'cork': foot + Vector((0, 0, BOTTLE_H - 0.03)), 'glass_a': props['glass_a'], 'glass_b': props['glass_b']}
    for n, p in parts.items():
        b = eb.new(f'{NAME}_{n}'); b.head = p; b.tail = p + Vector((0, 0, 0.08)); b.parent = root
    bpy.ops.object.mode_set(mode='OBJECT')
    mats = [M['trim'], M['brass'], M['bottle_green'], M['label'], M['ice_bucket'], M['paper'], M['iron'], M['bottle_clear']]
    bm = bmesh.new(); groups = {}
    def grab(bone, build):
        n0 = len(bm.verts); build(); bm.verts.ensure_lookup_table(); groups[f'{NAME}_{bone}'] = list(range(n0, len(bm.verts)))
    def door():
        for pb, mat in door_leaf(R.DOOR[1] - R.DOOR[0] - 0.01, R.DOOR_H - 0.012, M):
            pb.transform(Matrix.Translation(hinge))
            me = bpy.data.meshes.new('_tmp'); pb.to_mesh(me); pb.free()
            for p in me.polygons: p.material_index = mats.index(mat)
            bm.from_mesh(me); bpy.data.meshes.remove(me)
    grab('door', door)
    def bottle():
        for f in _bottle(bm, foot): f.material_index = 2
        for f in _lathe_into(bm, [(0.0415, 0.07), (0.0415, 0.15), (0.0, 0.15)][:2] + [(0.0, 0.15)], foot, 18): f.material_index = 3
        for f in _lathe_into(bm, [(0.0165, BOTTLE_H - 0.07), (0.0175, BOTTLE_H - 0.008), (0.0, BOTTLE_H - 0.008)], foot, 14): f.material_index = 6
    grab('bottle', bottle)
    def cork():
        for f in _lathe_into(bm, [(0.0, 0.0), (0.0105, 0.0), (0.011, 0.04), (0.0, 0.04)], parts['cork'], 10): f.material_index = 5
    grab('cork', cork)
    for g in ('glass_a', 'glass_b'):
        def gl(g=g):
            prof = [(0.0, 0.0), (0.034, 0.0), (0.034, 0.004), (0.005, 0.01), (0.004, 0.085), (0.03, 0.1), (0.038, 0.13), (0.036, GLASS_H), (0.033, GLASS_H), (0.034, 0.13), (0.026, 0.1), (0.0, 0.092)]
            for f in _lathe_into(bm, prof, parts[g], 20): f.material_index = 7
        grab(g, gl)
    def fixed():
        for f in _lathe_into(bm, [(0.0, 0.0), (0.065, 0.0), (0.07, 0.01), (0.07, 0.04), (0.06, 0.05), (0.085, 0.2), (0.09, 0.215), (0.08, 0.215), (0.075, 0.2), (0.0, 0.2)], bucket, 28): f.material_index = 4
        for k in range(2):
            for f in _lathe_into(bm, [(0.004, 0.0), (0.004, 0.02), (0.0, 0.02)], bucket + Vector(((-1) ** k * 0.088, 0, 0.18)), 8): f.material_index = 4
    grab('root', fixed)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME); bm.to_mesh(me); bm.free()
    for m in mats: me.materials.append(m)
    mesh = bpy.data.objects.new(f'{NAME}_parts', me); col.objects.link(mesh)
    for bone, ids in groups.items():
        vg = mesh.vertex_groups.get(bone) or mesh.vertex_groups.new(name=bone); vg.add(ids, 1.0, 'REPLACE')
    md = mesh.modifiers.new('rig', 'ARMATURE'); md.object = arm; mesh.parent = arm
    for o in (arm, mesh): o['person'] = NAME
    for pb in arm.pose.bones: pb.rotation_mode = 'QUATERNION'
    arm['rest'] = {f'{NAME}_{n}': list(p) for n, p in parts.items()}
    return arm, mesh


def rest_act(arm, name, seconds=4.0):
    """Nothing moving: the door shut, the bottle in its bucket, the glasses on the table."""
    return Track(arm, int(seconds * FPS)).key(name)


def pop(L, f0, land, rnd):
    """The cork out of the neck at f0: up and over in a short arc, a spin, onto the rug at `land`, a bounce."""
    p0, q0 = L.get('cork', f0)
    nf = int(0.7 * FPS); up = Vector((0, 0, 0.45))
    axis = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)).normalized()
    for i in range(nf + 1):
        u = i / nf; p = p0.lerp(land, u) + up * 4 * u * (1 - u) * (1 if p0.z > land.z else 0.5)
        L.set('cork', f0 + i, p, Quaternion(axis, 9.0 * u) @ q0)
    q_land = Quaternion(axis, math.pi / 2)
    for i in range(1, int(0.2 * FPS)):
        u = i / (0.2 * FPS); L.set('cork', f0 + nf + i, land + Vector((0, 0, 0.03 * math.sin(math.pi * u))), q_land)
    L.hold_from('cork', f0 + nf + int(0.2 * FPS) - 1)
