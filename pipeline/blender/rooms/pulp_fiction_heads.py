# Sculpted heads, made once (Jules's and Vincent's; Paul's and Coffey's for The Green Mile; Jeff's and Lisa's for Rear Window): each sculpt (one to two million triangles) decimated to a light mesh,
# unwrapped afresh, and its colour baked across from the full sculpt (as the_big_lebowski_head.py does for the Dude).
# Writes pipeline/out/people/<who>/<who>_head.glb and a front and side look at it (with a 2 cm grid) to place the eyes.
# Usage: blender -b --factory-startup -P pipeline/blender/rooms/pulp_fiction_heads.py -- jules|vincent
import os, sys, math
import bpy
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cine

HEADS = {
    'vincent': dict(src=os.path.join(cine.CACHE, 'sketchfab', 'vincent', 'scene.gltf'), ratio=0.03),
    'jules': dict(src=os.path.join(cine.CACHE, 'tripo', 'jules.glb'), ratio=0.03, turn=-90),   # its face looks along +x: turned to -y
    'paul': dict(src=os.path.join(cine.CACHE, 'sketchfab', 'hanks', 'scene.gltf'), ratio=0.5, turn=15),           # The Green Mile: the wax-figure scan
    'coffey': dict(src=os.path.join(cine.CACHE, 'tripo', 'coffey_meshopt.glb'), ratio=0.03, turn=-90, tilt=12, tame=True),   # from a film still, made in Tripo Studio
    'jeff': dict(src=os.path.join(cine.CACHE, 'tripo', 'jeff_stewart_meshopt.glb'), ratio=0.03, turn=-90, roll=20.7),      # Rear Window: from film stills, made in Tripo Studio
    'lisa': dict(src=os.path.join(cine.CACHE, 'tripo', 'lisa_kelly_meshopt.glb'), ratio=0.03, turn=-90, roll=5.1),
    # Uncut Gems: from film stills, made in Tripo Studio
    'howard': dict(src=os.path.join(cine.CACHE, 'tripo', 'howard_meshopt.glb'), ratio=0.03, turn=-90 + 14, regrade=((150, 108, 88), 0.8),
                   crop=(-0.25, -0.06, -0.02, 0.205, 0.055), crown=(0.11, (16, 13, 12)), neck=(0.19, -0.56)),
    'arno': dict(src=os.path.join(cine.CACHE, 'tripo', 'arno_meshopt.glb'), ratio=0.03, turn=-90 + 10.3, regrade=((160, 124, 106), 0.9),
                 crop=(-0.26, -0.14, -0.03, 0.18, 0.075), neck=(0.19, -0.54)),
    'phil': dict(src=os.path.join(cine.CACHE, 'tripo', 'phil_meshopt.glb'), ratio=0.03, turn=-90 + 10, regrade=((178, 140, 120), 0.9),
                 crop=(-0.21, -0.11, 0.0, 0.18, 0.01), crown=(0.075, (126, 116, 98)), neck=(0.19, -0.6)),
    'nico': dict(src=os.path.join(cine.CACHE, 'tripo', 'nico_meshopt.glb'), ratio=0.03, turn=-90),
    # Twin Peaks: fans' models (yugengen, CC BY). Cooper is a whole figure: his head kept, a neck made under it. Laura
    # is a prom bust: the up-do, its bun and the curls at her temples pressed down onto the skull (long hair goes over).
    'dale': dict(src=os.path.join(cine.CACHE, 'sketchfab', 'cooper_yugengen.glb'), ratio=1.0, regrade=((200, 150, 125), 0.0), crop=(1.24, 1.40, -0.012, 0.205, 1.563), neck=(0.14, 1.0)),
    'laura': dict(src=os.path.join(cine.CACHE, 'sketchfab', 'laura_yugengen.glb'), ratio=0.7,
                  squash=dict(c=(-0.087, 0.07, 0.30), r=(0.36, 0.45, 0.44), face=(-0.16, 0.52), floor=-0.1)),
    # the man from another place and the giant: from stills, made in Tripo Studio (the first graded red by the room)
    'arm': dict(src=os.path.join(cine.CACHE, 'tripo', 'arm_meshopt.glb'), ratio=0.03, turn=-90, regrade=((176, 134, 116), 0.85),
                crop=(-0.50, -0.18, 0.0, 9.0, -0.03), neck=(0.25, -0.95)),
    'giant': dict(src=os.path.join(cine.CACHE, 'tripo', 'giant_meshopt.glb'), ratio=0.03, turn=-90, regrade=((200, 160, 150), 0.0), uncap=0.03,
                  crop=(-9.0, -9.0, 0.0, 9.0, 0.03), neck=(0.25, -0.95)),
}
SIZE = 2048


def _crop_and_crown(hi, h):
    """A bust from a cropped still, made a head: `crop` (chin z, nape z, jaw centre x, half width, eye z) keeps the head
    above a plane from under the chin to the nape, and below the eyes only the jaw's width (the collar and shoulders
    go); `crown` (height, colour) closes a crown the still's frame cut flat with a dome of hair."""
    import bmesh
    bm = bmesh.new(); bm.from_mesh(hi.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)                 # the import splits vertices at UV seams
    ys = [v.co.y for v in bm.verts]; y0, y1 = min(ys), max(ys)
    if h.get('uncap'):                                                      # a closed sculpt: the flat cap the generator put under its neck taken off
        down = [f for f in bm.faces if f.normal.z < -0.85]
        if down:
            n = sum((f.normal * f.calc_area() for f in down), Vector()).normalized()
            big = max(down, key=lambda f: f.calc_area() if f.normal.dot(n) > 0.995 else 0.0); d0 = big.calc_center_median().dot(n)
            band = h['uncap'] if not isinstance(h['uncap'], bool) else 0.0     # and a band of skin above it: a clean edge to carry a neck from
            cap = [f for f in bm.faces if f.calc_center_median().dot(n) > d0 - 0.012 - band]
            bmesh.ops.delete(bm, geom=cap, context='FACES')
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
            cine.log('uncapped', len(cap), 'faces')
    if h.get('crop'):
        chin, nape, xc, hw, eye = h['crop']
        dead = []
        for f in bm.faces:
            q = f.calc_center_median(); t = min(max((q.y - y0) / max(y1 - y0, 1e-6), 0.0), 1.0)
            if q.z < chin + (nape - chin) * t or (q.z < chin + 0.2 and abs(q.x - xc) > hw): dead.append(f)   # the collar at the jaw's sides
        bmesh.ops.delete(bm, geom=dead, context='FACES')
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
        cine.log('cropped', len(dead), 'faces')
    sq = h.get('squash')
    if sq:                                                                  # an up-do pressed down onto the skull: every hair vertex outside an
        c, r = Vector(sq['c']), Vector(sq['r'])                             # ellipsoid (the skull under the hair) is brought onto it, the face left
        fy, fz = sq['face']                                                 # (in front of y = fy, below z = fz); no holes, the cards cover it
        n = 0
        for v in bm.verts:
            p = v.co
            if p.z < sq['floor'] or (p.y < fy and p.z < fz): continue
            d = Vector(((p.x - c.x) / r.x, (p.y - c.y) / r.y, (p.z - c.z) / r.z)); k = d.length
            if k > 1.0: v.co = c + (p - c) / k; n += 1
        cine.log('squashed', n, 'vertices onto the skull')
    if h.get('crown'):
        H, colour = h['crown']
        ups = sorted(f.calc_center_median().z for f in bm.faces if f.normal.z > 0.97)
        zt = ups[int(len(ups) * 0.9)] if ups else max(v.co.z for v in bm.verts)     # the flat cap the frame cut: most up-facing faces sit on it
        zc_ = zt - 0.025                                                    # a slab off the top: its outline is where the dome stands
        cap = [f for f in bm.faces if f.calc_center_median().z > zc_]
        cine.log('crown cap at', round(zt, 3), len(cap), 'faces')
        bmesh.ops.delete(bm, geom=cap, context='FACES')
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
        edges = [e for e in bm.edges if e.is_boundary and min(v.co.z for v in e.verts) > zt - 0.06]
        loop = _loop(edges)
        if loop:
            c = sum((v.co for v in loop), Vector()) / len(loop); c.z = sum(v.co.z for v in loop) / len(loop)
            mat_i = len(hi.data.materials)
            hm = bpy.data.materials.new('crown_hair'); nt = hm.node_tree; p = nt.nodes['Principled BSDF']
            nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 140.0; nz.inputs['Detail'].default_value = 6.0
            ramp = nt.nodes.new('ShaderNodeValToRGB'); col = [v / 255 for v in colour]
            ramp.color_ramp.elements[0].color = (*(x ** 2.2 * 0.6 for x in col), 1); ramp.color_ramp.elements[1].color = (*(x ** 2.2 * 1.3 for x in col), 1)
            nt.links.new(nz.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], p.inputs['Base Color'])
            hi.data.materials.append(hm)
            rings = [loop]; N = 8
            for k in range(1, N):
                a = k / N * math.pi / 2
                rings.append([bm.verts.new(c + (v.co - c) * math.cos(a) * Vector((1, 1, 0)) + Vector((0, 0, (v.co.z - c.z) * math.cos(a) + H * math.sin(a)))) for v in loop])
            top = bm.verts.new(c + Vector((0, 0, H)))
            new = []
            for A, B in zip(rings, rings[1:]):
                for i in range(len(loop)):
                    j = (i + 1) % len(loop)
                    try: new.append(bm.faces.new((A[i], A[j], B[j], B[i])))
                    except ValueError: pass
            for i in range(len(loop)):
                try: new.append(bm.faces.new((rings[-1][i], rings[-1][(i + 1) % len(loop)], top)))
                except ValueError: pass
            for f in new: f.material_index = mat_i; f.smooth = True
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            cine.log('crown closed over', len(loop), 'edge points, height', H)
        else: cine.log('crown: no top loop found')
    if h.get('neck'):
        # a neck of its own: the crop's lower edge carried down and drawn in to a neck's round (the collar in the
        # still hid it), its colour a mid grey that the regrade makes the skin's
        r, z_bot = h['neck']; chin, nape, xc, hw, eye = h['crop']
        edges = [e for e in bm.edges if e.is_boundary and max(v.co.z for v in e.verts) < eye - 0.08]
        loop = _loop(edges)
        if loop:
            yc = y0 + 0.6 * (y1 - y0)
            mat_i = len(hi.data.materials)
            nm = bpy.data.materials.new('crop_neck'); nm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.1, 0.1, 0.1, 1)
            hi.data.materials.append(nm)
            rings = [loop]; N = 6
            for k in range(1, N + 1):
                u = k / N; s = u * u * (3 - 2 * u); ring = []
                for v in loop:
                    d = Vector((v.co.x - xc, v.co.y - yc, 0)); d = d.normalized() if d.length > 1e-6 else Vector((1, 0, 0))
                    tgt = Vector((xc, yc, 0)) + d * r
                    p = Vector((v.co.x, v.co.y, 0)).lerp(tgt, s); ring.append(bm.verts.new((p.x, p.y, v.co.z + (z_bot - v.co.z) * u)))
                rings.append(ring)
            new = []
            for A, B in zip(rings, rings[1:]):
                for i in range(len(loop)):
                    j = (i + 1) % len(loop)
                    try: new.append(bm.faces.new((A[i], A[j], B[j], B[i])))
                    except ValueError: pass
            for f in new: f.material_index = mat_i; f.smooth = True
            made = [v for r_ in rings[1:] for v in r_]                       # the crop's jagged edge smoothed out of the columns below it
            for _ in range(12): bmesh.ops.smooth_vert(bm, verts=made, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            cine.log('neck carried down from', len(loop), 'edge points to', z_bot)
        else: cine.log('neck: no lower edge found')
    bm.to_mesh(hi.data); bm.free(); hi.data.update()


def _neck_mask(lo, h, img, m):
    """The texels of the made neck, found by its faces (below the crop) and an emission bake of them: the colour bake's
    rays from the neck's thin faces can strike the jaw above, so its colour alone does not find them all."""
    import numpy as np
    chin, nape, xc, hw, eye = h['crop']
    ys = [v.co.y for v in lo.data.vertices]; y0, y1 = min(ys), max(ys)
    mk = bpy.data.images.new('neck_mask', SIZE, SIZE)
    mats = []
    for k in (0, 1):
        mm = bpy.data.materials.new(f'mask{k}'); nt = mm.node_tree
        for n in list(nt.nodes): nt.nodes.remove(n)
        o_ = nt.nodes.new('ShaderNodeOutputMaterial'); e_ = nt.nodes.new('ShaderNodeEmission'); e_.inputs['Strength'].default_value = 1.0
        e_.inputs['Color'].default_value = (k, k, k, 1); nt.links.new(e_.outputs['Emission'], o_.inputs['Surface'])
        t_ = nt.nodes.new('ShaderNodeTexImage'); t_.image = mk; nt.nodes.active = t_; mats.append(mm)
    lo.data.materials.clear(); lo.data.materials.append(mats[0]); lo.data.materials.append(mats[1])
    for f in lo.data.polygons:
        q = f.center; t = min(max((q.y - y0) / max(y1 - y0, 1e-6), 0.0), 1.0)
        f.material_index = 1 if (q.z < chin + (nape - chin) * t - 0.005 or (q.z < chin + 0.2 and abs(q.x - xc) > hw + 0.005)) else 0
    bpy.ops.object.select_all(action='DESELECT'); lo.select_set(True); bpy.context.view_layer.objects.active = lo
    bpy.ops.object.bake(type='EMIT', use_selected_to_active=False, margin=8)
    px = np.empty(SIZE * SIZE * 4, np.float32); mk.pixels.foreach_get(px)
    lo.data.materials.clear(); lo.data.materials.append(m)
    for f in lo.data.polygons: f.material_index = 0
    mask = px.reshape(-1, 4)[:, 0] > 0.5
    cine.log('neck mask', int(mask.sum()), 'texels')
    return mask


def _loop(edges):
    """The longest closed chain of boundary edges, its vertices in order."""
    if not edges: return []
    adj = {}
    for e in edges:
        a, b = e.verts; adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
    seen, best = set(), []
    for s in adj:
        if s in seen: continue
        chain = [s]; seen.add(s); prev, cur = None, s
        while True:
            nxt = next((n for n in adj[cur] if n is not prev and n not in seen), None)
            if nxt is None: break
            chain.append(nxt); seen.add(nxt); prev, cur = cur, nxt
        if len(chain) > len(best): best = chain
    return best


def main(who):
    h = HEADS[who]; out = os.path.join(cine.OUT, 'people', who)
    cine.reset(16)
    sc = bpy.context.scene
    bpy.ops.import_scene.gltf(filepath=h['src'])
    parts = [o for o in bpy.data.objects if o.type == 'MESH']
    for o in parts:
        mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    for o in [o for o in bpy.data.objects if o.type == 'EMPTY']: bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    if len(parts) > 1: bpy.ops.object.join()
    hi = bpy.context.view_layer.objects.active; hi.name = f'{who}_hi'
    for sl in hi.material_slots:                                          # an unlit scan: its image into a lit surface (the bake reads base colour)
        m = sl.material
        if not m or any(n.type == 'BSDF_PRINCIPLED' for n in m.node_tree.nodes): continue
        nt = m.node_tree; img = next((n.image for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image), None)
        for n in list(nt.nodes): nt.nodes.remove(n)
        o_ = nt.nodes.new('ShaderNodeOutputMaterial'); p_ = nt.nodes.new('ShaderNodeBsdfPrincipled'); nt.links.new(p_.outputs['BSDF'], o_.inputs['Surface'])
        if img is not None: t_ = nt.nodes.new('ShaderNodeTexImage'); t_.image = img; nt.links.new(t_.outputs['Color'], p_.inputs['Base Color'])
    if h.get('turn'): hi.rotation_mode = 'XYZ'; hi.rotation_euler.z += math.radians(h['turn'])   # glTF imports in quaternions
    if h.get('tilt'):                                                     # a face photographed from below, looking up: brought level
        bpy.context.view_layer.update(); hi.matrix_world = Matrix.Rotation(math.radians(h['tilt']), 4, 'X') @ hi.matrix_world
    if h.get('roll'):                                                     # a head tilted to one side in its still: its eyes brought level
        bpy.context.view_layer.update(); hi.matrix_world = Matrix.Rotation(math.radians(h['roll']), 4, 'Y') @ hi.matrix_world
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if h.get('crop') or h.get('crown') or h.get('neck') or h.get('squash') or h.get('uncap'): _crop_and_crown(hi, h)
    lo = hi.copy(); lo.data = hi.data.copy(); lo.name = f'{who}_head'; sc.collection.objects.link(lo)
    bpy.context.view_layer.objects.active = lo
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.remove_doubles(threshold=1e-5); bpy.ops.object.mode_set(mode='OBJECT')
    md = lo.modifiers.new('thin', 'DECIMATE'); md.ratio = h['ratio']; md.use_collapse_triangulate = True
    with bpy.context.temp_override(object=lo, active_object=lo): bpy.ops.object.modifier_apply(modifier=md.name)
    for l in list(lo.data.uv_layers): lo.data.uv_layers.remove(l)
    lo.data.uv_layers.new(name='UVMap')
    bpy.ops.object.select_all(action='DESELECT'); lo.select_set(True); bpy.context.view_layer.objects.active = lo
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
    bpy.ops.uv.pack_islands(rotate=True, margin=0.003, shape_method='CONVEX')
    bpy.ops.object.mode_set(mode='OBJECT')
    cine.log(who, 'head decimated to', len(lo.data.polygons), 'faces')
    img = bpy.data.images.new(f'{who}_head_color', SIZE, SIZE)
    m = bpy.data.materials.new(f'{who}_head'); nt = m.node_tree; p = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = img; nt.links.new(t.outputs['Color'], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.55; p.inputs['Metallic'].default_value = 0.0
    lo.data.materials.clear(); lo.data.materials.append(m); nt.nodes.active = t
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 4
    bpy.ops.object.select_all(action='DESELECT'); hi.select_set(True); lo.select_set(True); bpy.context.view_layer.objects.active = lo
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, use_selected_to_active=True, cage_extrusion=0.02, max_ray_distance=0.06, margin=8)
    os.makedirs(out, exist_ok=True)
    neck_geo = _neck_mask(lo, h, img, m) if h.get('neck') else None
    if h.get('tame'):                                                     # the photograph's highlights on a bald head: back to the skin's tone
        import numpy as np
        px = np.empty(SIZE * SIZE * 4, np.float32); img.pixels.foreach_get(px); a = np.clip(px.reshape(-1, 4)[:, :3], 0, 1) ** (1 / 2.2)   # in sRGB
        mx, mn = a.max(1), a.min(1); sat = (mx - mn) / (mx + 1e-6)
        skin = (mx > 0.05) & (mx < 0.5) & (sat > 0.25)
        tone = a[skin].mean(0)
        hot = np.clip((mx - 0.4) / 0.18, 0, 1) * np.clip((0.75 - sat) / 0.2, 0, 1)
        g = hot.reshape(SIZE, SIZE)                                       # softened, so the painted patches have no edge
        for _ in range(3): g = (g + np.roll(g, 2, 0) + np.roll(g, -2, 0) + np.roll(g, 2, 1) + np.roll(g, -2, 1)) / 5
        hot = g.ravel()
        rel = np.clip(a.mean(1) / max(tone.mean(), 1e-4), 0.6, 1.5) ** 0.3
        a = a * (1 - hot[:, None]) + tone[None] * rel[:, None] * hot[:, None]
        px.reshape(-1, 4)[:, :3] = np.clip(a, 0, 1) ** 2.2
        img.pixels.foreach_set(px)
        cine.log(who, 'highlights tamed', int((hot > 0.5).sum()), 'texels')
    if h.get('regrade'):                                                  # a still graded hard (teal): its light and dark kept, its colour the skin's
        import numpy as np
        t_, mix = h['regrade']
        px = np.empty(SIZE * SIZE * 4, np.float32); img.pixels.foreach_get(px); a = px.reshape(-1, 4)[:, :3]
        L = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        ref = float(np.median(L[(L > 0.02) & (L < 0.6)]))
        tl = (np.array(t_, np.float32) / 255) ** 2.2
        g = tl[None, :] * (L / max(ref, 1e-4))[:, None] * (1.0 - 0.35 * np.clip((0.012 - L) / 0.012, 0, 1))[:, None]   # the darkest (hair, brows) toward neutral
        dark = np.clip((0.075 - L) / 0.045, 0, 1)[:, None]
        g = g * (1 - dark) + L[:, None] * dark
        neck = ((np.abs(a - 0.1 ** (1 / 2.2)).max(1) < 0.015) | neck_geo) if neck_geo is not None else None   # the made neck's flat grey (pixels read in sRGB), found before the grade moves it
        empty = a.sum(1) == 0                                                 # texels no island covers: given the neck's tone, so thin neck strips draw in no black
        a[:] = np.clip(a * (1 - mix) + g * mix, 0, 1)
        if neck is not None and neck.any():                               # the neck in the face's own skin, its edge softened into the jaw
            L2 = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
            skin = (~neck) & (~empty) & (a[:, 0] > a[:, 1]) & (a[:, 1] > a[:, 2]) & (L2 > 0.08) & (L2 < 0.6)
            lo_, hi_ = np.percentile(L2[skin], (60, 95)) if skin.any() else (0, 1)
            sel = skin & (L2 >= lo_) & (L2 <= hi_)                           # the lit skin, not its shadows
            tone = np.median(a[sel], 0) if sel.any() else tl
            neck = neck | empty
            w_ = neck.astype(np.float32).reshape(SIZE, SIZE)
            for _ in range(3): w_ = (w_ + np.roll(w_, 2, 0) + np.roll(w_, -2, 0) + np.roll(w_, 2, 1) + np.roll(w_, -2, 1)) / 5
            w_ = np.maximum(w_.ravel(), neck)[:, None]
            a[:] = a * (1 - w_) + tone[None] * w_
            cine.log(who, 'neck painted', int(neck.sum()), 'texels to', tuple(round(float(x), 3) for x in tone))
        img.pixels.foreach_set(px)
        cine.log(who, 'regraded to', t_)
    img.filepath_raw = os.path.join(out, f'{who}_head_color.png'); img.file_format = 'PNG'; img.save()
    bb = [lo.matrix_world @ Vector(c) for c in lo.bound_box]
    lo_ = Vector([min(v[i] for v in bb) for i in range(3)]); hi_ = Vector([max(v[i] for v in bb) for i in range(3)])
    cine.log(who, 'bounds', tuple(round(v, 3) for v in lo_), tuple(round(v, 3) for v in hi_))
    bpy.data.objects.remove(hi, do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT'); lo.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, f'{who}_head.glb'), export_format='GLB', use_selection=True, export_image_format='AUTO')
    cine.log('wrote', os.path.join(out, f'{who}_head.glb'))
    # looks: front (along +y and -y: the sculpt's front is found by eye) and side, orthographic, with a grid
    c = (lo_ + hi_) / 2; span = max(hi_ - lo_) * 1.15
    w = bpy.data.worlds.new('w'); w.color = (0.5, 0.5, 0.5); sc.world = w
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sc.collection.objects.link(sun); sun.rotation_euler = (0.6, 0.2, 0.4); sun.data.energy = 3
    gm = bpy.data.materials.new('grid'); gm.diffuse_color = (1, 0, 0, 1)
    sc.render.resolution_x = sc.render.resolution_y = 900; sc.cycles.samples = 16
    for name, d in (('ny', Vector((0, -1, 0))), ('py', Vector((0, 1, 0))), ('px', Vector((1, 0, 0)))):
        cam = bpy.data.objects.new(f'cam_{name}', bpy.data.cameras.new(f'cam_{name}')); sc.collection.objects.link(cam)
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = span
        cam.location = c + d * 2.0; cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        sc.camera = cam; sc.render.filepath = os.path.join(out, f'{who}_look_{name}.png'); bpy.ops.render.render(write_still=True)


main(sys.argv[sys.argv.index('--') + 1])
