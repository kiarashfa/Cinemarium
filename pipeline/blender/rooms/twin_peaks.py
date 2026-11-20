# Twin Peaks · the Red Room as Agent Cooper dreams it (1990): a room with no walls, only scarlet velvet drapes hung
# floor to ceiling in deep pleats, lit from above in warm pools; the zigzag floor in cocoa and cream bands across the
# room; two Art Deco club chairs side by side before the back drapes (black crushed velvet, wooden bands down the
# rolled arms), a white marble Venus between them, a fluted aluminium torchiere at either end; the agent's chair on
# the left facing them, a small chrome table at his left hand with a gold Saturn lamp. In the back drapes, toward the
# right, two curtains overlap: a slit to the corridor behind them. Built at its true size.
import math, os
import bpy, bmesh
from mathutils import Vector, Matrix
import cine
from cine import box, material, lathe, rounded_slab, slab_profile, outline
from rooms.seinfeld import tube

W, D = 9.6, 7.6
T = 0.14
LEFT, BACK, RIGHT, FRONT = -W / 2 + T, D / 2 - T, W / 2 - T, -D / 2 + T
RH = 3.0                                   # the module's top: the drapes hang to it (the ceiling is a phantom above)
KH = 0.22
TEX = os.path.join(cine.OUT, 'textures', 'twin-peaks')
tx = lambda n: os.path.join(TEX, n)
SKF = os.path.join(cine.CACHE, 'sketchfab')

# the plan (true metres)
DRAPE_B = 3.25                             # the back drapes' line (y); behind it, the corridor to the back wall
DRAPE_L = -4.30                            # the left drapes' line (x)
SLIT = (3.30, 3.00, 2.92)                  # the back drapes end at x 3.30; the overlapping curtain from x 3.00, at y 2.92
PLEAT = 0.17                               # the pleats' pitch
DEPTH = 0.055
CHAIR_W, CHAIR_D = 0.92, 0.88
SEAT_H = 0.44                              # the cushion's top
ARM_H = 0.64
# the chairs: where each stands (the seat's middle on the floor) and which way it faces
CHAIRS = {'arm': (Vector((-0.05, 2.42)), Vector((0.0, -1.0))),
          'laura': (Vector((1.40, 2.42)), Vector((0.0, -1.0))),
          'dale': (Vector((-2.55, 1.30)), Vector((1.0, -0.22)).normalized())}
VENUS = Vector((0.68, 2.90))
TORCH = [Vector((-0.98, 2.80)), Vector((2.36, 2.80))]
TABLE = Vector((-2.62, 2.12))              # at the agent's left hand
TABLE_H = 0.56
LAMP_C = Vector((TABLE.x, TABLE.y, TABLE_H + 0.27))   # the Saturn globe's centre


# ---------------------------------------------------------------- materials
def mats():
    M = {}
    M['drape'] = material('tp_drape', rough=0.62, maps={'color': tx('drape_color.jpg'), 'normal': tx('drape_normal.jpg')}, scale=0.6, normal_strength=0.35,
                          sheen=0.6, sheen_tint=(0.9, 0.35, 0.3))
    M['floor'] = material('tp_floor', rough=0.42, maps={'color': tx('floor_color.jpg')}, scale=3.2)
    M['chair'] = material('tp_chair_velvet', rough=0.72, maps={'color': tx('chair_color.jpg'), 'normal': tx('chair_normal.jpg')}, scale=0.45, normal_strength=0.4,
                          sheen=0.3, sheen_tint=(0.25, 0.22, 0.24))
    M['band'] = material('tp_band_wood', rough=0.3, maps={'color': tx('band_color.jpg')}, scale=0.6, coat=0.6, coat_rough=0.12)
    M['alu'] = material('tp_brushed_alu', (0.72, 0.72, 0.74), rough=0.3, metal=1.0)
    M['chrome'] = material('tp_chrome', (0.86, 0.86, 0.88), rough=0.1, metal=1.0)
    M['gold'] = material('tp_lamp_gold', (0.86, 0.64, 0.3), rough=0.28, metal=1.0)
    M['black_glass'] = material('tp_black_glass', (0.01, 0.01, 0.012), rough=0.06, coat=1.0)
    M['marble'] = material('tp_marble', rough=0.32, maps={'color': tx('marble_color.jpg')}, scale=0.8, coat=0.2)
    M['plinth'] = material('tp_plinth', (0.02, 0.018, 0.018), rough=0.4, coat=0.3)
    M['wall'] = material('tp_dark_wall', (0.03, 0.01, 0.01), rough=0.9)
    M['section'] = material('section', (0.03, 0.012, 0.012), rough=0.92)
    M['phantom_red'] = material('tp_phantom_drape', (0.3, 0.02, 0.025), rough=0.8)
    M['phantom_ceiling'] = material('tp_phantom_ceiling', (0.04, 0.03, 0.03), rough=0.9)
    return M


# ---------------------------------------------------------------- the shell
def shell(M, arch, phantom):
    """The floor; the module's back and left walls (dark, behind the drapes); the kerbs; the phantoms: a dark
    ceiling, the drapes the cut took away (front and right), above the kerbs."""
    box('subfloor', (W, D, 0.02), (0, 0, -0.035), M['wall'], bev=0, collection=arch, lm='arch')
    fl = box('floor_room', (RIGHT - LEFT, BACK - FRONT, 0.03), ((LEFT + RIGHT) / 2, (FRONT + BACK) / 2, -0.015), M['floor'], bev=0, collection=arch, lm='arch')
    cine.world_uv(fl, 1.0)
    box('back_wall', (W, T, RH), (0, D / 2 - T / 2, RH / 2), M['wall'], bev=0, collection=arch, lm='arch')
    box('left_wall', (T, D - T, RH), (-W / 2 + T / 2, -T / 2, RH / 2), M['wall'], bev=0, collection=arch, lm='arch')
    k = box('kerb_front', (W - T, T, KH), (T / 2, -D / 2 + T / 2, KH / 2), M['drape'], bev=0, collection=arch, lm='arch'); cine.world_uv(k, 1.0)
    k = box('kerb_right', (T, D - 2 * T, KH), (W / 2 - T / 2, 0, KH / 2), M['drape'], bev=0, collection=arch, lm='arch'); cine.world_uv(k, 1.0)
    P_ = M['phantom_red']; ph = lambda name, size, loc, mat=P_: box(name, size, loc, mat, bev=0, collection=phantom, bake_only=1)
    ph('ph_ceiling', (W, D, 0.2), (0, 0, RH + 0.1), M['phantom_ceiling'])
    ph('ph_front', (W, 0.2, RH - KH), (0, FRONT - 0.3, KH + (RH - KH) / 2))
    ph('ph_right', (0.2, D, RH - KH), (RIGHT - 0.1, 0, KH + (RH - KH) / 2))


def velvet_drape(name, width, height, folds, depth, mat, loc, rot, seed, col, **props):
    """Heavy velvet hung in deep soft folds: a sheet in the x-z plane (origin at the top middle), each fold its own
    width and depth, the folds a little tighter at the heading than at the floor, a slow sway across, the hem
    resting on the floor and turned out a little; UVs in metres of cloth."""
    import random
    rnd = random.Random(seed); nx, nz = folds * 10, 30
    w_ = [0.75 + 0.5 * rnd.random() for _ in range(folds)]; tot = sum(w_); edges = [0.0]
    for w in w_: edges.append(edges[-1] + w / tot)
    amp = [depth * (0.65 + 0.6 * rnd.random()) for _ in range(folds)]
    sway = [rnd.random() * 6.283 for _ in range(3)]
    def fold_y(u, t):
        i = min(max(next((k for k in range(folds) if edges[k + 1] >= u), folds - 1), 0), folds - 1)
        v = (u - edges[i]) / max(edges[i + 1] - edges[i], 1e-6)
        y = amp[i] * math.sin(v * 2 * math.pi) * (0.72 + 0.28 * t)
        return y + depth * 0.25 * math.sin(u * 2.1 * math.pi + sway[0] + t * 1.3) + depth * 0.12 * math.sin(u * 7.3 * math.pi + sway[1])
    bm = bmesh.new(); grid = []
    for j in range(nz + 1):
        t = j / nz; z = -t * height; row = []
        for i in range(nx + 1):
            u = i / nx; y = fold_y(u, t)
            if t > 0.97: y -= (t - 0.97) / 0.03 * 0.03                       # the hem turned out onto the floor
            row.append(bm.verts.new(((u - 0.5) * width, y, z)))
        grid.append(row)
    uvl = bm.loops.layers.uv.new('UVMap')
    for j in range(nz):
        for i in range(nx):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for l, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))): l[uvl].uv = (ii / nx * width * 1.6, 1 - jj / nz * height)
    ob = cine._mesh_obj(name, bm, mat, col, smooth=True)
    ob.location = loc; ob.rotation_euler = rot
    for k, v in props.items(): ob[k] = v
    return ob


def _drape_run(name, M, col, a, b, fixed, along, seed, h=RH + 0.02):
    """Drapes hung along a line: panels about 1.6 m wide, a fold every PLEAT or so, from the top to the floor."""
    L = abs(b - a); n = max(1, round(L / 1.6)); w = L / n; out = []
    for i in range(n):
        c = min(a, b) + w * (i + 0.5); folds = max(2, round(w / PLEAT))
        if along == 'x': loc, rot = (c, fixed, RH), (0, 0, 0)
        else: loc, rot = (fixed, c, RH), (0, 0, math.pi / 2)
        out.append(velvet_drape(f'{name}{i}', w + 0.03, h, folds, DEPTH, M['drape'], loc, rot, seed + i, col, lm='arch'))
    return out


def drapes(M, arch):
    """The back drapes (to the slit), the left drapes, the overlapping curtain before the slit and its return to the
    back wall at the right cut (red both sides: the case sees it from the right)."""
    out = []
    out += _drape_run('drape_back', M, arch, DRAPE_L - 0.05, SLIT[0], DRAPE_B, 'x', 11)
    out += _drape_run('drape_left', M, arch, FRONT, DRAPE_B + 0.05, DRAPE_L, 'y', 31)
    out += _drape_run('drape_slit', M, arch, SLIT[1], RIGHT, SLIT[2], 'x', 51)
    out += _drape_run('drape_return', M, arch, SLIT[2] + 0.03, BACK, RIGHT - 0.06, 'y', 61)
    return out


# ---------------------------------------------------------------- the chairs
def _band(name, path, t, x, M, col):
    """A bent wooden band down an arm's front: a thin strip following `path` [(y, z)], `t` wide (along x)."""
    pts = [Vector(p) for p in path]; inner = []
    for i, p in enumerate(pts):
        a = pts[max(i - 1, 0)]; b = pts[min(i + 1, len(pts) - 1)]
        d = (b - a).normalized(); n = Vector((d.y, -d.x))         # to the strip's inside (into the arm)
        inner.append(p - n * 0.014)
    poly = [(p.x, p.y) for p in pts] + [(p.x, p.y) for p in reversed(inner)]
    ob = slab_profile(name, poly, 'x', t, [M['band'], M['band']], col, bev=0.003, lm='furn')
    ob.location.x = x
    return ob


def club_chair(name, M, col, at, facing):
    """An Art Deco club armchair (built facing -y about the seat's front middle on the floor, then placed): a deep
    rolled arm either side with three bent wooden bands down its front, a plump seat cushion, a rounded back, a low
    plinth, all in black crushed velvet."""
    parts = []; aw = 0.2; hw = CHAIR_W / 2; d0, d1 = -CHAIR_D / 2, CHAIR_D / 2
    parts.append(rounded_slab(f'{name}_plinth', CHAIR_W - 0.06, CHAIR_D - 0.08, 0.12, 0.05, (0, 0.0, 0.06), M['chair'], collection=col, lm='furn'))
    parts.append(rounded_slab(f'{name}_seat', CHAIR_W - 2 * aw + 0.02, CHAIR_D - 0.26, 0.2, 0.06, (0, d0 + 0.02 + (CHAIR_D - 0.26) / 2, SEAT_H - 0.1), M['chair'], collection=col, lm='furn', edge_bev=0.03))
    back = outline([(d1 - 0.27, 0.12), (d1 - 0.25, 0.5), (d1 - 0.2, 0.78), (d1 - 0.1, 0.84), (d1 - 0.01, 0.8), (d1, 0.4), (d1 - 0.02, 0.12)], 8)
    parts.append(slab_profile(f'{name}_back', back, 'x', CHAIR_W - 0.02, [M['chair'], M['chair']], col, bev=0.03, lm='furn'))
    arm = outline([(d0 + 0.02, 0.1), (d0, 0.4), (d0 + 0.01, ARM_H - 0.06), (d0 + 0.06, ARM_H), (d0 + 0.2, ARM_H + 0.01), (d1 - 0.1, ARM_H + 0.03),
                   (d1 - 0.02, ARM_H - 0.04), (d1 - 0.02, 0.12)], 8)
    for s in (-1, 1):
        a = slab_profile(f'{name}_arm{s:+d}', arm, 'x', aw, [M['chair'], M['chair']], col, bev=0.065, lm='furn')
        a.location.x = s * (hw - aw / 2); parts.append(a)
        front = [(d0 - 0.004, 0.06 + 0.5 * k / 12) for k in range(12)] + \
                [(d0 + 0.004 + 0.05 * (1 - math.cos(u * math.pi / 2)) - 0.004, ARM_H - 0.08 + 0.085 * math.sin(u * math.pi / 2)) for u in (0.2, 0.4, 0.6, 0.8, 1.0)]
        for k, dx in enumerate((-0.055, 0.0, 0.055)):
            parts.append(_band(f'{name}_band{s:+d}{k}', front, 0.032, s * (hw - aw / 2) + dx, M, col))
    a = math.atan2(facing.y, facing.x) - math.atan2(-1.0, 0.0)
    F = Matrix.Translation((at.x, at.y, 0)) @ Matrix.Rotation(a, 4, 'Z')
    bpy.context.view_layer.update()
    for o in parts: cine.place(o, F)
    return parts


def chairs(M, col):
    out = []
    for who, (p, f) in CHAIRS.items(): out += club_chair(f'chair_{who}', M, col, p, f)
    return out


def seat_point(who):
    """Where a sitter's pelvis goes in a chair (the seat's middle, a little back from its front), and the facing."""
    p, f = CHAIRS[who]
    return Vector((p.x, p.y, SEAT_H)) - Vector((f.x, f.y, 0)) * 0.02, f


# ---------------------------------------------------------------- the Venus, the lamps, the table
def venus(M, col):
    """The Venus de Milo (a cast's scan, CC0) on a low black plinth between the two chairs, her face to the room:
    white marble. A dense scan: drawn live, not light-mapped."""
    from rooms.the_godfather import _fit
    box('venus_plinth', (0.42, 0.42, 0.14), (VENUS.x, VENUS.y, 0.07), M['plinth'], bev=0.006, collection=col, lm='furn')
    _, ms = cine.import_gltf(os.path.join(SKF, 'venus_de_milo_smk.glb'), collection=col)
    for o in ms:
        o.data.materials.clear(); o.data.materials.append(M['marble'])
        if not o.data.uv_layers: cine.world_uv(o, 1.0)
    _fit(ms, (VENUS.x, VENUS.y, 0.14), 1.56, axis='z', ground=True, ratio=0.7)
    for o in ms:
        o.matrix_world = Matrix.Translation((VENUS.x, VENUS.y, 0)) @ Matrix.Rotation(math.radians(VENUS_TURN), 4, 'Z') @ Matrix.Translation((-VENUS.x, -VENUS.y, 0)) @ o.matrix_world
        o['role'] = 'mug'; o.name = 'venus'
        if 'lm' in o: del o['lm']
    return ms


VENUS_TURN = 0.0                           # the scan already faces the room's front (-y)


def torchiere(name, M, col, at):
    """A fluted aluminium torchiere: a round stepped foot, a slim stem, a flared trumpet shade (1.9 m)."""
    prof = [(0.0, 0.0), (0.17, 0.0), (0.17, 0.018), (0.12, 0.03), (0.04, 0.05), (0.014, 0.08), (0.011, 1.62), (0.016, 1.64),
            (0.03, 1.7), (0.06, 1.77), (0.11, 1.83), (0.17, 1.875), (0.215, 1.9), (0.205, 1.9), (0.16, 1.874), (0.1, 1.83), (0.0, 1.8)]
    ob = lathe(name, prof, M['alu'], loc=(at.x, at.y, 0), seg=40, collection=col, lm='furn')
    for k in range(20):                                                       # the trumpet's flutes: thin ribs up its outside
        a = 2 * math.pi * k / 20; d = Vector((math.cos(a), math.sin(a), 0))
        pts = [Vector((at.x, at.y, z)) + d * (r + 0.004) for r, z in ((0.03, 1.7), (0.06, 1.77), (0.11, 1.83), (0.17, 1.875), (0.212, 1.898))]
        tube(f'{name}_flute{k}', pts, 0.0035, M['alu'], col, seg=6, lm='furn')
    return ob


def side_table(M, col):
    """The bent-chrome side table: a black glass top on two frames of three flat bars that run down and along the
    floor; on it the Saturn lamp: a stepped gold foot, the globe, its tilted ring."""
    c = TABLE; tw, td = 0.5, 0.38
    box('table_top', (tw, td, 0.022), (c.x, c.y, TABLE_H - 0.011), M['black_glass'], bev=0.004, collection=col, lm='furn')
    for s in (-1, 1):
        for k, dy in enumerate((-0.12, 0.0, 0.12)):
            x0 = c.x + s * (tw / 2 - 0.03); x1 = c.x + s * (tw / 2 - 0.16)
            y = c.y + dy; r = 0.06
            pts = [Vector((x1, y, TABLE_H - 0.025)), Vector((x0 - s * r, y, TABLE_H - 0.025))]
            pts += [Vector((x0 - s * r + s * r * math.sin(u * math.pi / 2), y, TABLE_H - 0.025 - r + r * math.cos(u * math.pi / 2))) for u in (0.33, 0.66, 1.0)]
            pts += [Vector((x0, y, r + 0.012))]
            pts += [Vector((x0 - s * r + s * r * math.cos(u * math.pi / 2), y, 0.012 + r - r * math.sin(u * math.pi / 2))) for u in (0.33, 0.66, 1.0)]
            pts += [Vector((x1 - s * 0.04, y, 0.012))]
            tube(f'table_bar{s:+d}{k}', pts, 0.011, M['chrome'], col, seg=8, lm='furn')
    z = TABLE_H
    lathe('saturn_foot', [(0.0, z), (0.075, z), (0.075, z + 0.012), (0.055, z + 0.02), (0.055, z + 0.032), (0.03, z + 0.045), (0.016, z + 0.1),
                          (0.02, z + 0.15), (0.0, z + 0.16)], M['gold'], loc=(c.x, c.y, 0), seg=32, collection=col, lm='furn')
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=20, radius=0.115)
    g = cine._mesh_obj('saturn_globe', bm, M['gold'], col); g.location = LAMP_C; g['lm'] = 'furn'
    from rooms.seinfeld import circle
    ring = circle((0, 0, 0), 0.175, (1, 0, 0), (0, 1, 0), n=48)
    R_ = Matrix.Translation(LAMP_C) @ Matrix.Rotation(math.radians(22), 4, 'X') @ Matrix.Rotation(math.radians(-15), 4, 'Y')
    tube('saturn_ring', [R_ @ p for p in ring], 0.01, M['gold'], col, closed=True, seg=8, lm='furn')


# ---------------------------------------------------------------- the cut
def section(objs, M):
    """Every face the module's top cuts through (the walls' tops), flat and dark."""
    for ob in objs:
        if not ob.name.startswith(('left_', 'back_', 'kerb')): continue
        me = ob.data
        if M['section'].name not in [m.name for m in me.materials if m]: me.materials.append(M['section'])
        k = [m.name if m else '' for m in me.materials].index(M['section'].name)
        for f in me.polygons:
            c = ob.matrix_world @ (sum((me.vertices[i].co for i in f.vertices), Vector()) / len(f.vertices))
            if f.normal.z > 0.9 and abs(c.z - RH) < 0.006: f.material_index = k


# ---------------------------------------------------------------- light
WARM = (1.0, 0.8, 0.62)                    # the dream's amber top light
KEY = (1.0, 0.8, 0.6)


def lights():
    """Warm spots high over the drapes, each throwing a pool down the pleats (bright in the middle, dark at the top);
    a soft key from the front over the floor and the chairs; a low warm fill over the middle."""
    out = []
    def light(name, kind, loc, energy, colour, rot=None, **kw):
        ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = colour
        for k, v in kw.items(): setattr(ld, k, v)
        ob = cine.link(bpy.data.objects.new(name, ld)); ob.location = loc
        if rot: ob.rotation_euler = rot
        if kind in ('AREA', 'SPOT', 'SUN'): ob.visible_camera = False; ob.visible_glossy = False
        out.append(ob); return ob
    aim = lambda p, t: (Vector(t) - Vector(p)).to_track_quat('-Z', 'Y').to_euler()
    for k, x in enumerate((-3.4, -1.7, 0.0, 1.7, 3.4)):                       # the back drapes
        p = (x, DRAPE_B - 1.3, RH - 0.05); t = (x, DRAPE_B, 1.15)
        light(f'pool_b{k}', 'SPOT', p, 420.0, WARM, rot=aim(p, t), spot_size=math.radians(70), spot_blend=0.85, shadow_soft_size=0.25)
    p = (3.9, SLIT[2] - 1.3, RH - 0.05); t = (3.9, SLIT[2], 1.15)
    light('pool_slit', 'SPOT', p, 380.0, WARM, rot=aim(p, t), spot_size=math.radians(70), spot_blend=0.85, shadow_soft_size=0.25)
    for k, y in enumerate((-2.6, -0.9, 0.8, 2.4)):                            # the left drapes
        p = (DRAPE_L + 1.3, y, RH - 0.05); t = (DRAPE_L, y, 1.15)
        light(f'pool_l{k}', 'SPOT', p, 380.0, WARM, rot=aim(p, t), spot_size=math.radians(70), spot_blend=0.85, shadow_soft_size=0.25)
    light('key_front', 'AREA', (0.0, FRONT - 0.2, 2.7), 900.0, KEY, rot=aim((0.0, FRONT - 0.2, 2.7), (-0.4, 1.4, 0.6)), shape='RECTANGLE', size=5.0, size_y=1.6)
    light('fill_top', 'AREA', (-0.6, 1.2, RH - 0.04), 260.0, WARM, rot=(0, 0, 0), shape='RECTANGLE', size=4.0, size_y=2.6)
    return out
