# The room's own rig: one small armature carries what moves in the showroom besides the people (the vestibule's
# inner glass door, Howard's phone), so the web plays them like any act (the room is a performer; its act and
# Howard's start together). The phone, picked up, follows his hand; set down, it slides back to its place.
import math
import bpy, bmesh
from mathutils import Vector, Matrix, Quaternion
import cine, people
import rooms.uncut_gems as R
from rooms.interstellar_rig import Track, door as swing, carry

FPS = people.FPS
NAME = 'room'
HINGE = Vector((R.VDOOR[0] + 0.005, R.MY0, 0.0))


def make_rig(M, col):
    """An armature at the room's origin: a root, the door (its bone at the hinge), the phone (at its rest on the
    counter). One mesh, each part skinned wholly to its bone. Returns (armature, mesh)."""
    arm = bpy.data.objects.new(NAME, bpy.data.armatures.new(NAME)); col.objects.link(arm)
    bpy.context.view_layer.objects.active = arm; arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones
    root = eb.new(f'{NAME}_root'); root.head = Vector((0, 0, 0)); root.tail = Vector((0, 0, 0.1))
    parts = {'door': HINGE, 'phone': R.PHONE.copy()}
    for n, p in parts.items():
        b = eb.new(f'{NAME}_{n}'); b.head = p; b.tail = p + Vector((0, 0, 0.08)); b.parent = root
    bpy.ops.object.mode_set(mode='OBJECT')
    mats = [M['chrome'], M['brushed'], M['frost'], M['sign'], M['black'], M['screen']]
    bm = bmesh.new(); groups = {}
    def grab(bone, build):
        n0 = len(bm.verts); build(); bm.verts.ensure_lookup_table(); groups[f'{NAME}_{bone}'] = list(range(n0, len(bm.verts)))
    def door():
        for pb, mat in R.vestibule_door(M):
            pb.transform(Matrix.Translation(HINGE))
            me = bpy.data.meshes.new('_tmp'); pb.to_mesh(me); pb.free()
            for p in me.polygons: p.material_index = mats.index(mat)
            bm.from_mesh(me); bpy.data.meshes.remove(me)
    grab('door', door)
    def phone():
        p = parts['phone']
        for size, c, mi in (((0.075, 0.152, 0.009), p + Vector((0, 0, 0.0045)), 4), ((0.066, 0.135, 0.002), p + Vector((0, 0, 0.0095)), 5)):
            pb = bmesh.new(); bmesh.ops.create_cube(pb, size=1.0, matrix=Matrix.Translation(c) @ Matrix.Rotation(0.35, 4, 'Z') @ Matrix.Diagonal((*size, 1)))
            me = bpy.data.meshes.new('_tmp'); pb.to_mesh(me); pb.free()
            for q in me.polygons: q.material_index = mi
            bm.from_mesh(me); bpy.data.meshes.remove(me)
    grab('phone', phone)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME); bm.to_mesh(me); bm.free()
    for m in mats: me.materials.append(m)
    uv = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
    mesh = bpy.data.objects.new(f'{NAME}_parts', me); col.objects.link(mesh)
    for bone, ids in groups.items():
        vg = mesh.vertex_groups.get(bone) or mesh.vertex_groups.new(name=bone); vg.add(ids, 1.0, 'REPLACE')
    md = mesh.modifiers.new('rig', 'ARMATURE'); md.object = arm; mesh.parent = arm
    for o in (arm, mesh): o['person'] = NAME
    for pb in arm.pose.bones: pb.rotation_mode = 'QUATERNION'
    arm['rest'] = {f'{NAME}_{n}': list(p) for n, p in parts.items()}
    return arm, mesh


def rest_act(arm, name, seconds=4.0):
    """Nothing moving: the door shut, the phone on the counter."""
    return Track(arm, int(seconds * FPS)).key(name)


def door_keys(L, keys):
    """The door's angle through the act: keys [(frame, radians)], eased between (negative opens out, toward -y)."""
    for f in range(L.n + 1):
        k = max((i for i, (g, _) in enumerate(keys) if g <= f), default=0)
        if k + 1 < len(keys):
            (f0, a0), (f1, a1) = keys[k], keys[k + 1]; u = min(1.0, max(0.0, (f - f0) / max(1, f1 - f0))); u = u * u * (3 - 2 * u)
            a = a0 + (a1 - a0) * u
        else: a = keys[-1][1]
        L.set('door', f, HINGE, Quaternion(Vector((0, 0, 1)), a))
