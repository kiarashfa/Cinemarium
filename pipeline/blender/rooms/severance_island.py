# Severance, the desk island: four white desks in a pinwheel around a cross of bottle-green partitions,
# a Lumon terminal on each, task chairs on dark chair mats. Desk 0 is laid out in its own frame
# (its length along +x, the worker at -y facing +y) and rotated by q x 90 degrees for the others.
import math
import bpy, bmesh
from mathutils import Vector, Matrix
import cine
from cine import box, cyl, rounded_slab

ISLAND = Vector((0.15, 0.55, 0))
PELVIS = Vector((0.83, -1.03, 0))   # where a seated worker's pelvis sits, in desk-0 coordinates
CHAIR = Vector((0.83, -1.08, 0))
KEYS = Vector((0.74, -0.70, 0.815))  # left wrist target, over the keyboard
BALL = Vector((1.035, -0.72, 0.805))  # right wrist target, behind the trackball


def frame_q(q):
    return Matrix.Translation(ISLAND) @ Matrix.Rotation(q * math.pi / 2, 4, 'Z')


def place(objs, F):
    # matrix_basis is current as soon as location/rotation are set; matrix_world waits for a scene update
    for ob in objs: ob.matrix_world = F @ (ob.matrix_basis if ob.parent is None else ob.matrix_world)
    return objs


def keyboard_mesh(name, M, collection):
    """52 keycaps in one mesh: navy keys, a light-blue top row and two light-blue columns on the right."""
    bm = bmesh.new()
    for r in range(4):
        for c in range(13):
            v = bmesh.ops.create_cube(bm, size=1.0)['verts']
            for p in v: p.co = Vector((p.co.x * 0.0235 + (-0.205 + c * 0.0287), p.co.y * 0.0235 + (-0.115 + r * 0.0287), p.co.z * 0.009 + 0.0325))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = cine.link(bpy.data.objects.new(name, me), collection)
    me.materials.append(M['keynavy']); me.materials.append(M['keyblue'])
    for i, poly in enumerate(me.polygons):
        r, c = divmod(i // 6, 13); poly.material_index = 1 if (r == 3 or c >= 11) else 0
    cine.bevel(ob, 0.0025, 2, 40); ob['lm'] = 'furn'
    return ob


def screen_mesh(name, M, collection, w=0.325, h=0.24, bulge=0.009):
    """A slightly domed CRT face with 0..1 UVs for the live screen texture."""
    bm = bmesh.new(); nx, ny = 16, 12; vs = []
    for j in range(ny + 1):
        for i in range(nx + 1):
            u, v = i / nx, j / ny
            vs.append(bm.verts.new(((u - 0.5) * w, -bulge * (1 - (2 * u - 1) ** 2) * (1 - (2 * v - 1) ** 2), (v - 0.5) * h)))
    uvl = bm.loops.layers.uv.new('UVMap')
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i; f = bm.faces.new((vs[a], vs[a + 1], vs[a + nx + 2], vs[a + nx + 1]))
            for loop, (du, dv) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))): loop[uvl].uv = ((i + du) / nx, (j + dv) / ny)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    ob = cine.link(bpy.data.objects.new(name, me), collection); me.materials.append(M['screen'])
    return ob


def terminal(M, F, q, collection):
    """The Lumon terminal; local origin on the desk top at the centre of its base, the worker at -y."""
    o = [rounded_slab(f'term{q}_base', 0.54, 0.30, 0.026, 0.026, (0, 0, 0.013), M['cream'], collection=collection, lm='furn'),
         box(f'term{q}_well', (0.42, 0.14, 0.006), (-0.035, -0.071, 0.027), M['slate'], bev=0.002, collection=collection, lm='furn')]
    kb = keyboard_mesh(f'term{q}_keys', M, collection); kb.location = (-0.03, 0.0, 0.0); o.append(kb)
    o.append(cyl(f'term{q}_ballring', 0.031, 0.008, (0.205, -0.07, 0.03), M['slate'], collection=collection, lm='furn'))
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=0.019)
    ball = cine._mesh_obj(f'term{q}_ball', bm, M['ball'], collection); ball.location = (0.205, -0.07, 0.04); ball['lm'] = 'furn'; o.append(ball)
    for sx in (-1, 1):
        o.append(box(f'term{q}_arm{sx}', (0.03, 0.06, 0.27), (sx * 0.262, 0.09, 0.026 + 0.135), M['cream'], bev=0.012, seg=3, collection=collection, lm='furn'))
        o.append(cyl(f'term{q}_pivot{sx}', 0.034, 0.014, (sx * 0.240, 0.09, 0.255), M['cream'], rot=(0, math.pi / 2, 0), collection=collection, lm='furn'))
    mon = [box(f'term{q}_crt', (0.40, 0.31, 0.30), (0, 0.035, 0), M['slate'], bev=0.035, seg=4, collection=collection, lm='furn')]
    for nm, sz, at in (('top', (0.43, 0.03, 0.04), (0, -0.125, 0.135)), ('bot', (0.43, 0.03, 0.04), (0, -0.125, -0.135)),
                       ('l', (0.05, 0.03, 0.31), (-0.19, -0.125, 0)), ('r', (0.05, 0.03, 0.31), (0.19, -0.125, 0))):
        mon.append(box(f'term{q}_bezel_{nm}', sz, at, M['cream'], bev=0.008, seg=2, collection=collection, lm='furn'))
    scr = screen_mesh(f'screen_{q}', M, collection); scr.location = (0, -0.127, 0); scr['role'] = 'screen'; scr['q'] = q; mon.append(scr)
    place(mon, Matrix.Translation((0, 0.09, 0.255)) @ Matrix.Rotation(math.radians(-8), 4, 'X'))
    o += mon
    return place(o, F @ Matrix.Translation((0.83, -0.58, 0.745)))


def chair(M, F, q, collection):
    """A task chair; local origin on the floor under the seat centre, its front toward +y."""
    o = [cyl(f'chair{q}_hub', 0.05, 0.06, (0, 0, 0.095), M['chrome'], collection=collection, lm='furn')]
    for k in range(5):
        a = k * 2 * math.pi / 5 + 0.3; cx, cy = 0.31 * math.cos(a), 0.31 * math.sin(a)
        o.append(box(f'chair{q}_leg{k}', (0.30, 0.045, 0.03), (0.15 * math.cos(a), 0.15 * math.sin(a), 0.09), M['chrome'], rot=(0, 0, a), bev=0.008, collection=collection, lm='furn'))
        o.append(cyl(f'chair{q}_stem{k}', 0.012, 0.04, (cx, cy, 0.065), M['plastic'], collection=collection, lm='furn'))
        o.append(cyl(f'chair{q}_wheel{k}', 0.026, 0.022, (cx, cy, 0.027), M['rubber'], rot=(math.pi / 2, 0, a + math.pi / 2), collection=collection, lm='furn'))
    o += [cyl(f'chair{q}_lift', 0.022, 0.2, (0, 0, 0.22), M['chrome'], collection=collection, lm='furn'),
          cyl(f'chair{q}_shroud', 0.03, 0.1, (0, 0, 0.33), M['plastic'], collection=collection, lm='furn'),
          box(f'chair{q}_mech', (0.22, 0.24, 0.05), (0, 0.01, 0.385), M['plastic'], bev=0.01, collection=collection, lm='furn'),
          rounded_slab(f'chair{q}_shell', 0.5, 0.48, 0.022, 0.06, (0, 0.01, 0.405), M['plastic'], collection=collection, lm='furn'),
          box(f'chair{q}_seat', (0.49, 0.47, 0.06), (0, 0.01, 0.423), M['chair'], bev=0.026, seg=4, collection=collection, lm='furn')]
    back = [box(f'chair{q}_back', (0.45, 0.065, 0.5), (0, 0, 0), M['chair'], bev=0.028, seg=4, collection=collection, lm='furn'),
            box(f'chair{q}_backshell', (0.46, 0.02, 0.5), (0, -0.04, 0), M['plastic'], bev=0.008, collection=collection, lm='furn')]
    o += place(back, Matrix.Translation((0, -0.25, 0.79)) @ Matrix.Rotation(math.radians(-9), 4, 'X'))
    o.append(box(f'chair{q}_spine', (0.07, 0.03, 0.34), (0, -0.265, 0.53), M['plastic'], rot=(math.radians(-6), 0, 0), bev=0.01, collection=collection, lm='furn'))
    for sx in (-1, 1):
        o.append(box(f'chair{q}_armpost{sx}', (0.03, 0.05, 0.19), (sx * 0.27, -0.03, 0.5), M['plastic'], bev=0.01, collection=collection, lm='furn'))
        o.append(box(f'chair{q}_armpad{sx}', (0.07, 0.26, 0.028), (sx * 0.27, 0.0, 0.605), M['plastic'], bev=0.012, seg=3, collection=collection, lm='furn'))
    return place(o, F @ Matrix.Translation(CHAIR))


def desk(M, F, q, collection):
    o = [rounded_slab(f'desk{q}_top', 1.6, 0.8, 0.03, 0.03, (0.83, -0.43, 0.73), M['laminate'], collection=collection, lm='furn'),
         box(f'desk{q}_side', (0.025, 0.74, 0.715), (0.06, -0.43, 0.3575), M['paint'], bev=0.003, collection=collection, lm='furn'),
         box(f'desk{q}_ped', (0.43, 0.62, 0.68), (1.36, -0.43, 0.03 + 0.34), M['paint'], bev=0.004, collection=collection, lm='furn')]
    for k, (z, h) in enumerate([(0.555, 0.15), (0.395, 0.15), (0.155, 0.31)]):
        o.append(box(f'desk{q}_drawer{k}', (0.415, 0.012, h - 0.006), (1.36, -0.746, z), M['paint'], bev=0.003, collection=collection, lm='furn'))
        o.append(box(f'desk{q}_pull{k}', (0.13, 0.014, 0.012), (1.36, -0.757, z + h / 2 - 0.035), M['steel'], bev=0.003, collection=collection, lm='furn'))
    for fx in (1.18, 1.54):
        for fy in (-0.7, -0.16): o.append(cyl(f'desk{q}_foot_{fx}_{fy}', 0.012, 0.03, (fx, fy, 0.015), M['plastic'], collection=collection, lm='furn'))
    o.append(rounded_slab(f'desk{q}_mat', 1.05, 0.95, 0.004, 0.02, (0.83, -1.32, 0.002), M['mat'], edge_bev=0.0015, collection=collection, lm='furn'))
    return place(o, F)


def partitions(M, collection):
    o = []
    for name, rot in (('x', 0), ('y', math.pi / 2)):
        p = [box(f'part_{name}_core', (3.5, 0.05, 1.235), (0, 0, 0.0175 + 1.235 / 2), M['partition'], bev=0.004, collection=collection, lm='arch'),
             box(f'part_{name}_cap', (3.52, 0.058, 0.018), (0, 0, 1.262), M['alu'], bev=0.004, collection=collection, lm='arch')]
        for sx in (-1, 1):
            p.append(box(f'part_{name}_end{sx}', (0.018, 0.058, 1.27), (sx * 1.759, 0, 0.635), M['alu'], bev=0.004, collection=collection, lm='arch'))
            p.append(box(f'part_{name}_foot{sx}', (0.06, 0.07, 0.018), (sx * 1.7, 0, 0.009), M['plastic'], bev=0.003, collection=collection, lm='arch'))
        o += place(p, Matrix.Translation(ISLAND) @ Matrix.Rotation(rot, 4, 'Z'))
    return o


def mug(M, name, at, collection, coffee=True):
    o = [cyl(f'{name}_body', 0.041, 0.095, (0, 0, 0.0475), M['ceramic'], seg=32, collection=collection, lm='furn')]
    bpy.ops.mesh.primitive_torus_add(major_radius=0.026, minor_radius=0.0065, location=(0.045, 0, 0.05), rotation=(math.pi / 2, 0, 0))
    h = bpy.context.object; h.name = f'{name}_handle'; h.data.materials.append(M['ceramic']); h['lm'] = 'furn'
    for c in h.users_collection: c.objects.unlink(h)
    collection.objects.link(h); o.append(h)
    if coffee: o.append(cyl(f'{name}_coffee', 0.036, 0.004, (0, 0, 0.082), M['coffee'], collection=collection, lm='furn'))
    return place(o, at)


def island(M, collection):
    objs = partitions(M, collection)
    for q in range(4):
        F = frame_q(q)
        objs += desk(M, F, q, collection) + terminal(M, F, q, collection) + chair(M, F, q, collection)
    return objs
