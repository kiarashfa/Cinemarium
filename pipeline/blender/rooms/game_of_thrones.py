# Game of Thrones · the throne room of the Red Keep in King Robert's day (season 1), its throne end: the throne wall of
# warm ashlar with the tall stained-glass window of stags high behind the Iron Throne; an arched bay either side with
# colonnettes and a round-headed doorway into a lit passage; the dais of rough dark stone, a broad flight of five steps
# to the landing, the round step and the throne's round plinth; the great columns, salmon plaster with grey-green
# vines, on stone plinths, two pairs down the nave; iron candelabra; cream marble underfoot with dark inlaid bands.
#
# The hall is too great for the module at 1:6 (it would show a 9.6 m slice of a hall forty metres long and twelve
# high, cut at three): this room alone is built at its true size in a module 1 / SCALE times the size, then everything
# in it, the court too, is shrunk by SCALE (0.6) when the room is assembled. Within it, after the art department's
# drawing of the back wall (1:50) and the season 1 stills: the doorways at their places either side of the dais, the
# window over the throne. Where the cut passes through walls, columns and arches: a dark `section` face. The hall goes
# on beyond the cut and above it (phantoms for its light).
import math, os, random
import bpy, bmesh
from mathutils import Vector, Matrix
import cine
from cine import box, cyl, material, lathe, slab_profile
from rooms.seinfeld import uv_rect, tube, circle, _glow

SCALE = 0.6                                # the room's own scale inside the module (every other room: 1)
W, D, H = 9.6 / SCALE, 7.6 / SCALE, 3.0 / SCALE   # the module, at the hall's true size
T = 0.14 / SCALE                           # the module's walls
LEFT, BACK, RIGHT, FRONT = -W / 2 + T, D / 2 - T, W / 2 - T, -D / 2 + T
RH = 2.95 / SCALE                          # the cut
KH = 0.22 / SCALE                          # the cut-away's kerb
TEX = os.path.join(cine.OUT, 'textures', 'game-of-thrones')
tx = lambda n: os.path.join(TEX, n)

YW, YW2 = 3.9, 4.6                         # the throne wall: its face, its back (the passages behind it)
BAYS = (-5.6, 5.6)                         # the arched bays either side of the dais (x centres; 11.2 m apart, as drawn)
BAY_W, BAY_D = 2.6, 0.25                   # their width, how deep they are sunk
DOOR_W, DOOR_SPRING = 1.5, 2.8             # the doorways: width, where the round head springs
COLONNETTE = 4.2                           # the bays' colonnettes reach their capitals here; the great arches spring over them
WIN_W, WIN_Z = 1.5, 3.45                   # the stag window: its width, its sill (just over the throne's crown)
DAIS_X = 4.2                               # the broad flight's half width
STEP_H, STEP_D, STEPS = 0.16, 0.42, 5      # the broad flight
LAND_D = 2.6                               # the landing's depth, from the throne wall
LAND_Y = YW - LAND_D                       # its front edge
LAND_Z = STEPS * STEP_H
R1, R2, RISE = 2.3, 1.75, 0.15             # the round step and the throne's plinth (half discs on the wall), their rise
PLINTH_Z = LAND_Z + 2 * RISE
THRONE = Vector((0.0, YW - 1.6, PLINTH_Z)) # the throne's front edge, middle; it faces -y
THRONE_H = 2.18
COL_R = 0.65
COLUMNS = ((-5.9, -1.6), (5.9, -1.6), (-5.9, -5.0), (5.9, -5.0))   # two pairs of great columns down the nave
DAIS_FRONT = LAND_Y - STEPS * STEP_D
CANDELABRA = ((-4.75, DAIS_FRONT - 0.3), (4.75, DAIS_FRONT - 0.3), (-3.0, 3.3), (3.0, 3.3))
SIDE_BAYS = (-3.3, 1.2)                    # the left wall's blind arches (y centres)


# ---------------------------------------------------------------- materials
def mats():
    M = {}
    M['ashlar'] = material('ashlar', rough=0.8, maps={'color': tx('ashlar_color.jpg'), 'normal': tx('ashlar_normal.jpg')}, scale=4.0, normal_strength=0.6)
    M['sandstone'] = material('sandstone', rough=0.75, maps={'color': tx('sandstone_color.jpg'), 'normal': tx('sandstone_normal.jpg')}, scale=2.0, normal_strength=0.5)
    M['dais'] = material('dais_stone', rough=0.82, maps={'color': tx('dais_color.jpg'), 'normal': tx('dais_normal.jpg')}, scale=2.2, normal_strength=0.9)
    M['marble'] = material('marble_cream', rough=0.32, maps={'color': tx('marble_color.jpg'), 'normal': tx('marble_normal.jpg')}, scale=4.0, normal_strength=0.2)
    M['marble_dark'] = material('marble_dark', rough=0.3, maps={'color': tx('marble_dark_color.jpg')}, scale=2.0)
    M['column'] = material('column_plaster', rough=0.7, maps={'color': tx('column_color.jpg'), 'normal': tx('column_normal.jpg')}, scale=1.0, normal_strength=0.7)
    M['passage'] = material('passage_stone', rough=0.85, maps={'color': tx('passage_color.jpg')}, scale=2.0)
    M['glass'] = material('stag_glass', rough=0.4, maps={'color': tx('stag_window.jpg')}, scale=1.0)
    M['iron'] = material('black_iron', (0.03, 0.028, 0.026), rough=0.5, metal=0.7)
    M['blade'] = material('throne_iron', (0.16, 0.155, 0.15), rough=0.45, metal=0.6)
    M['wax'] = material('candle_wax', (0.62, 0.55, 0.42), rough=0.55)
    M['flame'] = material('flame', (1.0, 0.7, 0.3), rough=0.5, emission=(1.0, 0.62, 0.24), emission_strength=24.0)
    M['oak'] = material('door_oak', (0.16, 0.1, 0.06), rough=0.6)
    M['kerb'] = material('kerb', (0.12, 0.1, 0.09), rough=0.9)
    M['section'] = material('section', (0.03, 0.028, 0.026), rough=0.92)
    M['phantom'] = material('phantom_stone', (0.42, 0.32, 0.25), rough=0.9)
    _glow(M['glass'], 3.2)                 # the window glows with the sun behind it, on the web as in the renders
    return M


# ---------------------------------------------------------------- the shell
def _wall_x(name, x0, x1, z0, z1, y0, y1, M, col, mat=None):
    """A block of a wall running along x, from x0 to x1, z0 to z1, y0 (its face) to y1."""
    if x1 - x0 < 1e-3 or z1 - z0 < 1e-3: return None
    return box(name, (x1 - x0, y1 - y0, z1 - z0), ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), mat or M['ashlar'], bev=0, collection=col, lm='arch')


def _arched(name, x0, x1, spring, y0, y1, M, col, mat=None, top=RH):
    """The wall over a round-headed opening from x0 to x1 (the head springing at `spring`), up to `top`."""
    cx, r = (x0 + x1) / 2, (x1 - x0) / 2
    pts = [(x0, top), (x0, spring)] + [(cx - r * math.cos(math.pi * k / 32), spring + r * math.sin(math.pi * k / 32)) for k in range(1, 32)] + [(x1, spring), (x1, top)]
    ob = slab_profile(name, pts, 'y', y1 - y0, [mat or M['ashlar'], mat or M['ashlar']], col, bev=0.003, lm='arch')
    ob.location.y = (y0 + y1) / 2
    return ob


def shell(M, arch, phantom):
    """The floor, the module's left and back walls, the throne wall with its window and two arched bays and doorways,
    the passages behind; kerbs; phantoms."""
    box('subfloor', (W, D, 0.05), (0, 0, -0.045), M['kerb'], bev=0, collection=arch, lm='arch')
    box('floor', (W - 2 * T + 0.003, D - T - 0.003, 0.03), (0, -T / 2, -0.015), M['marble'], bev=0, collection=arch, lm='arch')
    box('left_wall', (T, D, RH), (-W / 2 + T / 2, 0, RH / 2), M['ashlar'], bev=0, collection=arch, lm='arch')
    box('back_wall', (W - T, T, RH), (T / 2, D / 2 - T / 2, RH / 2), M['passage'], bev=0, collection=arch, lm='arch')
    ys = (YW, YW2)
    e = [LEFT, BAYS[0] - BAY_W / 2, BAYS[0] + BAY_W / 2, -WIN_W / 2, WIN_W / 2, BAYS[1] - BAY_W / 2, BAYS[1] + BAY_W / 2, RIGHT]
    _wall_x('solid_tw0', e[0], e[1], 0, RH, *ys, M, arch)
    _wall_x('solid_tw1', e[2], e[3], 0, RH, *ys, M, arch)
    _wall_x('solid_tw2', e[4], e[5], 0, RH, *ys, M, arch)
    _wall_x('solid_tw3', e[6], e[7], 0, RH, *ys, M, arch)
    _wall_x('solid_win_under', e[3], e[4], 0, WIN_Z, *ys, M, arch)
    for k, bx in enumerate(BAYS):
        b0, b1, d0, d1 = bx - BAY_W / 2, bx + BAY_W / 2, bx - DOOR_W / 2, bx + DOOR_W / 2
        y0 = YW + BAY_D
        _wall_x(f'solid_bay{k}_a', b0, d0, 0, RH, y0, YW2, M, arch)
        _wall_x(f'solid_bay{k}_b', d1, b1, 0, RH, y0, YW2, M, arch)
        _arched(f'solid_bay{k}_head', d0, d1, DOOR_SPRING, y0, YW2, M, arch)
    for k, s in enumerate((-1, 1)):                                            # the passages, divided from the window's light box
        box(f'solid_pass_div{k}', (0.3, BACK - YW2, RH), (s * (WIN_W / 2 + 0.4), (YW2 + BACK) / 2, RH / 2), M['passage'], bev=0, collection=arch, lm='arch')
    box('kerb_front', (W, T, KH), (0, -D / 2 + T / 2, KH / 2), M['kerb'], bev=0.002, collection=arch, lm='arch')
    box('kerb_right', (T, D - 2 * T, KH), (W / 2 - T / 2, 0, KH / 2), M['kerb'], bev=0.002, collection=arch, lm='arch')
    _phantoms(M, phantom)


HIGH_WINDOWS = [(-13.0, -10.4), (-6.2, -3.6), (0.4, 2.6)]   # the left aisle's high windows (y spans), above the cut
HIGH_Z = (7.0, 11.0)
TOP = 13.5                                                   # the vault


def _phantoms(M, col):
    """For the light only: the hall's walls above the cut (the high windows of the left aisle open in them), its far
    reaches and right side beyond the module, the vault; the passages' ceilings."""
    P = M['phantom']; far = -30.0
    ph = lambda name, size, loc: box(name, size, loc, P, bev=0, collection=col, bake_only=1)
    ph('ph_pass_ceiling', (W, BACK - YW2 + 0.3, 0.1), (0, (YW2 + BACK) / 2, RH + 0.06))
    # the throne wall above the cut, the window's shaft going on up
    for k, s in enumerate((-1, 1)):
        a, b = s * WIN_W / 2, s * (W / 2 + 8)
        ph(f'ph_tw{k}', (abs(b - a), 0.7, TOP - RH), ((a + b) / 2, (YW + YW2) / 2, (TOP + RH) / 2))
    ph('ph_tw_head', (WIN_W, 0.7, TOP - 9.0), (0, (YW + YW2) / 2, (TOP + 9.0) / 2))
    # the left wall above the cut, its high windows
    xw = LEFT - 0.35; z0, z1 = HIGH_Z
    edges = [far] + sorted(v for w in HIGH_WINDOWS for v in w) + [YW]
    for i in range(0, len(edges) - 1, 2):
        a, b = edges[i], edges[i + 1]; ph(f'ph_l{i}', (0.7, b - a, TOP - RH), (xw, (a + b) / 2, (TOP + RH) / 2))
    for i, (a, b) in enumerate(HIGH_WINDOWS):
        ph(f'ph_l_sill{i}', (0.7, b - a, z0 - RH), (xw, (a + b) / 2, (z0 + RH) / 2))
        ph(f'ph_l_head{i}', (0.7, b - a, TOP - z1), (xw, (a + b) / 2, (TOP + z1) / 2))
    ph('ph_l_low', (0.7, -D / 2 - far, RH), (xw, (-D / 2 + far) / 2, RH / 2))
    # the right side (its gallery and aisle wall), the far end, the vault, the floor going on
    x0, x1 = LEFT - 0.7, W / 2 + 7.0
    ph('ph_right', (0.7, YW - far, TOP), (x1, (YW + far) / 2, TOP / 2))
    ph('ph_far', (x1 - x0, 0.7, TOP), ((x0 + x1) / 2, far, TOP / 2))
    ph('ph_vault', (x1 - x0, YW - far, 0.4), ((x0 + x1) / 2, (YW + far) / 2, TOP + 0.2))
    ph('ph_floor', (x1 - x0, -D / 2 - far, 0.05), ((x0 + x1) / 2, (-D / 2 + far) / 2, -0.03))
    ph('ph_floor_r', (x1 - W / 2, YW + D / 2, 0.05), ((x1 + W / 2) / 2, (YW - D / 2) / 2, -0.03))


def _colonnette(name, p, h, M, col):
    """A sandstone colonnette: a moulded base, the shaft, a cushion capital at h."""
    return lathe(name, [(0.0, 0.0), (0.2, 0.0), (0.2, 0.3), (0.16, 0.36), (0.13, 0.44), (0.115, 0.5), (0.115, h - 0.32), (0.14, h - 0.26),
                        (0.2, h - 0.08), (0.22, h - 0.02), (0.22, h + 0.1), (0.0, h + 0.1)], M['sandstone'], loc=p, seg=24, collection=col, lm='arch')


def _arch_ring(name, centre, axis, r, M, col, w=0.2, depth=0.36):
    """A great arch's sandstone archivolt, springing from two capitals (centre at the springing, `axis` the arch's
    span, `w` its half width across the face, `depth` out from the wall), cut flat at RH."""
    out = axis.cross(Vector((0, 0, 1))).normalized()
    if out.dot(Vector((0, -1, 0)) if abs(axis.x) > 0.5 else Vector((1, 0, 0))) < 0: out = -out   # toward the room
    bm = bmesh.new(); n = 80
    def at(t, rr):
        p = centre - axis * rr * math.cos(t) + Vector((0, 0, rr * math.sin(t)))
        if p.z > RH:                                                    # clamp onto the cut along the circle's radius
            p = centre - axis * rr * math.cos(t) * 1.0 + Vector((0, 0, RH - centre.z))
        return p
    for half in (0, 1):
        ts = [math.pi * (i / n) for i in range(n + 1)]
        ts = ts[:n // 2 + 1] if half == 0 else ts[n // 2:]
        quads = []
        for t in ts:
            pi, po = at(t, r - w), at(t, r + w)
            if pi.z >= RH - 1e-4 and po.z >= RH - 1e-4: continue
            pi.z = min(pi.z, RH); po.z = min(po.z, RH)
            quads.append([bm.verts.new(pi), bm.verts.new(po), bm.verts.new(po + out * depth), bm.verts.new(pi + out * depth)])
        for qa, qb in zip(quads, quads[1:]):
            for j in range(4): bm.faces.new((qa[j], qa[(j + 1) % 4], qb[(j + 1) % 4], qb[j]))
        if quads: bm.faces.new(quads[0]); bm.faces.new(list(reversed(quads[-1])))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = cine._mesh_obj(name, bm, M['sandstone'], col, smooth=False); ob['lm'] = 'arch'
    return ob


def finishes(M, col):
    """The bays' colonnettes and their great arches (sprung, then cut), the doorways' sandstone surrounds and oak doors
    folded open, the window's reveal and sill and glass, the left wall's blind arches, the plinth courses."""
    for k, bx in enumerate(BAYS):
        b0, b1 = bx - BAY_W / 2, bx + BAY_W / 2
        for j, x in enumerate((b0 + 0.16, b1 - 0.16)):
            _colonnette(f'colonnette{k}{j}', (x, YW + 0.12, 0.0), COLONNETTE, M, col)
        _arch_ring(f'bay_arch{k}', Vector((bx, YW - 0.06, COLONNETTE + 0.1)), Vector((1, 0, 0)), BAY_W / 2 - 0.16, M, col)
        # the doorway: a sandstone surround with a roll moulding following its round head
        d0, d1 = bx - DOOR_W / 2, bx + DOOR_W / 2; yf = YW + BAY_D
        r = DOOR_W / 2 + 0.08
        ring = [Vector((bx - r * math.cos(math.pi * i / 32), yf - 0.02, DOOR_SPRING + r * math.sin(math.pi * i / 32))) for i in range(33)]
        tube(f'door_roll{k}', [Vector((bx - r, yf - 0.02, 0.0))] + ring + [Vector((bx + r, yf - 0.02, 0.0))], 0.06, M['sandstone'], col, seg=10, lm='arch')
        for j, x in enumerate((d0 - 0.1, d1 + 0.1)):
            box(f'door_jamb{k}{j}', (0.2, YW2 - yf + 0.02, DOOR_SPRING), (x, (yf + YW2) / 2, DOOR_SPRING / 2), M['sandstone'], bev=0.005, collection=col, lm='arch')
        for j, x in enumerate((d0 + 0.05, d1 - 0.05)):                          # two oak leaves folded back into the passage
            leaf = box(f'door_leaf{k}{j}', (0.09, DOOR_W / 2 - 0.02, DOOR_SPRING + 0.35), (x, YW2 + DOOR_W / 4 + 0.03, (DOOR_SPRING + 0.35) / 2), M['oak'], bev=0.008, collection=col, lm='furn')
            for z in (0.5, 1.6, 2.7):
                box(f'door_strap{k}{j}{z}', (0.1, DOOR_W / 2 - 0.1, 0.07), (x, leaf.location.y, z), M['iron'], bev=0.005, collection=col, lm='furn')
    # the window: a sandstone reveal and sill, the glass near the wall's back (its lower part: it goes on above the cut)
    x0, x1 = -WIN_W / 2, WIN_W / 2
    box('win_sill', (WIN_W + 0.16, YW2 - YW + 0.08, 0.1), (0, (YW + YW2) / 2 - 0.04, WIN_Z - 0.05), M['sandstone'], bev=0.008, collection=col, lm='arch')
    for j, x in enumerate((x0, x1)):
        box(f'win_jamb{j}', (0.08, YW2 - YW, RH - WIN_Z), (x + (0.04 if j == 0 else -0.04), (YW + YW2) / 2, (WIN_Z + RH) / 2), M['sandstone'], bev=0.004, collection=col, lm='arch')
    g = box('win_glass', (WIN_W - 0.16, 0.03, RH - WIN_Z), (0, YW2 - 0.08, (WIN_Z + RH) / 2), M['glass'], bev=0, collection=col, lm='furn')
    uv_rect(g, 'y')
    for d in g.data.uv_layers['UVMap'].data: d.uv = (d.uv[0], d.uv[1] * (RH - WIN_Z) / 5.2)
    # the left wall's blind arches: sunk round-headed panels between colonnettes, as the bays
    for k, yc in enumerate(SIDE_BAYS):
        for j, y in enumerate((yc - BAY_W / 2 + 0.16, yc + BAY_W / 2 - 0.16)):
            _colonnette(f'colonnette_l{k}{j}', (LEFT + 0.14, y, 0.0), COLONNETTE, M, col)
        _arch_ring(f'bay_arch_l{k}', Vector((LEFT - 0.04, yc, COLONNETTE + 0.1)), Vector((0, 1, 0)), BAY_W / 2 - 0.16, M, col)
        rr = 0.75
        ring = [Vector((LEFT + 0.04, yc - rr * math.cos(math.pi * i / 32), 2.6 + rr * math.sin(math.pi * i / 32))) for i in range(33)]
        tube(f'blind_roll{k}', [Vector((LEFT + 0.04, yc - rr, 0.45))] + ring + [Vector((LEFT + 0.04, yc + rr, 0.45))], 0.05, M['sandstone'], col, seg=10, lm='arch')
    # the plinth courses at the foot of the walls
    for k, (a, b) in enumerate(((LEFT, BAYS[0] - BAY_W / 2), (BAYS[0] + BAY_W / 2, BAYS[1] - BAY_W / 2), (BAYS[1] + BAY_W / 2, RIGHT))):
        box(f'tw_plinth{k}', (b - a, 0.08, 0.42), ((a + b) / 2, YW - 0.04, 0.21), M['sandstone'], bev=0.008, collection=col, lm='arch')
    box('lw_plinth', (0.08, YW - FRONT, 0.42), (LEFT + 0.04, (YW + FRONT) / 2, 0.21), M['sandstone'], bev=0.008, collection=col, lm='arch')
    return g


# ---------------------------------------------------------------- the dais
def _half_disc(name, r, z0, z1, M, col, seg=56):
    """A half disc of dark stone against the throne wall (centred on it at x 0), z0 to z1."""
    pts = [(r * math.cos(math.pi + math.pi * k / seg), YW + r * math.sin(math.pi + math.pi * k / seg)) for k in range(seg + 1)]
    bm = bmesh.new()
    a = [bm.verts.new((x, y, z0)) for x, y in pts]; b = [bm.verts.new((x, y, z1)) for x, y in pts]
    bm.faces.new(list(reversed(a))); bm.faces.new(b)
    n = len(pts)
    for i in range(n): bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = cine._mesh_obj(name, bm, M['dais'], col, smooth=False); cine.bevel(ob, 0.015, 2, 40); ob['lm'] = 'furn'
    return ob


def dais(M, col):
    """The broad flight of five steps across the bay between the doorways up to the landing, the round step and the
    throne's round plinth: rough dark stone, the edges worn."""
    for k in range(STEPS):
        y0 = LAND_Y - k * STEP_D; z1 = LAND_Z - k * STEP_H
        box(f'dais_step{k}', (2 * DAIS_X, YW - (y0 - STEP_D), z1), (0, (YW + y0 - STEP_D) / 2, z1 / 2), M['dais'], bev=0.018, collection=col, lm='furn')
    _half_disc('dais_round', R1, LAND_Z - 0.01, LAND_Z + RISE, M, col)
    _half_disc('dais_plinth', R2, LAND_Z + RISE - 0.01, PLINTH_Z, M, col)


def step_z(y):
    """The dais's height at y (on the broad flight, between its ends)."""
    if y >= LAND_Y: return LAND_Z
    k = math.floor((LAND_Y - y) / STEP_D)                  # step k's tread runs from LAND_Y - (k + 1) STEP_D to LAND_Y - k STEP_D
    return max(0.0, LAND_Z - k * STEP_H)


# ---------------------------------------------------------------- the Iron Throne
THRONE_GLB = os.path.join(cine.CACHE, 'objaverse', 'iron_throne_the_mangle.glb')


def throne(M, col):
    """The fan model (The Mangle, CC BY) at the throne's true height, its front edge at THRONE, facing the hall."""
    root, ms = cine.import_gltf(THRONE_GLB, collection=col, lm='furn')
    bpy.context.view_layer.update()
    P = [o.matrix_world @ v.co for o in ms for v in o.data.vertices]
    lo = Vector((min(p.x for p in P), min(p.y for p in P), min(p.z for p in P))); hi = Vector((max(p.x for p in P), max(p.y for p in P), max(p.z for p in P)))
    k = THRONE_H / (hi.z - lo.z)
    T_ = Matrix.Translation(THRONE) @ Matrix.Diagonal((k, k, k, 1)) @ Matrix.Translation(-Vector(((lo.x + hi.x) / 2, lo.y, lo.z)))
    for o in ms:
        if o.parent is None or o.parent.type != 'MESH':
            mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = T_ @ mw
    bpy.context.view_layer.update()
    for o in ms:
        for sl in o.material_slots:
            m = sl.material; p = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if m and m.node_tree else None
            if p: p.inputs['Metallic'].default_value = 0.25; p.inputs['Roughness'].default_value = 0.5
    cine.log('throne', tuple(round(v, 3) for v in (hi - lo) * k))
    return ms


def blades(M, col, n=27, seed=7):
    """Real blades in the throne's crown, so the fan holds up close: tapered, ridged, a little irregular, rising from
    behind the backrest and leaning back with it, each with a crossguard half hidden."""
    rnd = random.Random(seed); bm = bmesh.new()
    base = THRONE + Vector((0, 1.05, 1.32))
    for i in range(n):
        a = math.radians(-62 + 124 * i / (n - 1) + rnd.uniform(-3, 3))
        L = 0.72 + 0.34 * math.cos(a) ** 2 + rnd.uniform(-0.08, 0.06)
        d = Vector((math.sin(a) * 0.86, 0.36 + 0.06 * rnd.random(), math.cos(a))).normalized()
        side = d.cross(Vector((0, 1, 0))).normalized(); fl = side.cross(d).normalized()
        o = base + Vector((math.sin(a) * 0.16, 0.0, -0.06 * abs(math.sin(a))))
        w0, t = 0.045 + rnd.uniform(-0.005, 0.008), 0.006
        ring = lambda p, w: [bm.verts.new(p + side * w), bm.verts.new(p + fl * t), bm.verts.new(p - side * w), bm.verts.new(p - fl * t)]
        rings = [ring(o, w0), ring(o + d * L * 0.82, w0 * 0.8), ring(o + d * L, 0.002)]
        for ra, rb in zip(rings, rings[1:]):
            for j in range(4): bm.faces.new((ra[j], ra[(j + 1) % 4], rb[(j + 1) % 4], rb[j]))
        R_ = Matrix.Identity(4)
        for j, v in enumerate((side, fl, d)):
            for r_ in range(3): R_[r_][j] = v[r_]
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(o - d * 0.04) @ R_ @ Matrix.Diagonal((0.22, 0.025, 0.03, 1)))
    for f in bm.faces: f.smooth = False
    ob = cine._mesh_obj('throne_blades', bm, M['blade'], col, smooth=False); ob['lm'] = 'furn'
    return ob


# ---------------------------------------------------------------- columns, candelabra, the floor's bands
def column(name, c, M, col):
    """A great round column: a two-stepped stone plinth, a moulded base, the plastered shaft with its vines (0..1 UVs
    once round, metres up), cut at the module's top."""
    c = Vector((c[0], c[1], 0.0)); r = COL_R
    box(f'{name}_plinth0', (2 * r + 0.62, 2 * r + 0.62, 0.5), c + Vector((0, 0, 0.25)), M['sandstone'], bev=0.015, collection=col, lm='arch')
    box(f'{name}_plinth1', (2 * r + 0.42, 2 * r + 0.42, 0.34), c + Vector((0, 0, 0.67)), M['sandstone'], bev=0.025, seg=3, collection=col, lm='arch')
    lathe(f'{name}_base', [(0.0, 0.0), (r + 0.16, 0.0), (r + 0.16, 0.07), (r + 0.13, 0.14), (r + 0.08, 0.2), (r + 0.05, 0.23), (r + 0.03, 0.28), (0.0, 0.28)],
          M['sandstone'], loc=c + Vector((0, 0, 0.84)), seg=64, collection=col, lm='arch')
    z0, z1, seg = 1.1, RH, 64; bm = bmesh.new(); uv = bm.loops.layers.uv.new('UVMap')
    rings = [[bm.verts.new(c + Vector((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), z))) for i in range(seg + 1)] for z in (z0, z1)]
    circ = 2 * math.pi * r
    for i in range(seg):
        f = bm.faces.new((rings[0][i], rings[0][i + 1], rings[1][i + 1], rings[1][i]))
        for l, (u, v) in zip(f.loops, ((i / seg, z0 / circ), ((i + 1) / seg, z0 / circ), ((i + 1) / seg, z1 / circ), (i / seg, z1 / circ))): l[uv].uv = (u, v)
    bm.faces.new([rings[1][i] for i in range(seg)])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    ob = cine._mesh_obj(f'solid_{name}', bm, M['column'], col, smooth=True); ob['lm'] = 'arch'
    return ob


def candelabrum(name, p, M, col, rnd):
    """A tall black-iron candelabrum: three scrolled feet, a turned shaft, a ring of eight candles and three above it.
    Returns the flames' places."""
    p = Vector((p[0], p[1], p[2] if len(p) > 2 else 0.0)); flames = []
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.3; d = Vector((math.cos(a), math.sin(a), 0))
        tube(f'{name}_foot{k}', [p + d * 0.02 + Vector((0, 0, 0.34)), p + d * 0.18 + Vector((0, 0, 0.14)), p + d * 0.31 + Vector((0, 0, 0.02)),
                                 p + d * 0.36 + Vector((0, 0, 0.07)), p + d * 0.33 + Vector((0, 0, 0.11))], 0.018, M['iron'], col, seg=8, lm='furn')
    lathe(f'{name}_shaft', [(0.0, 0.3), (0.04, 0.3), (0.06, 0.38), (0.026, 0.46), (0.024, 1.15), (0.05, 1.22), (0.024, 1.28), (0.02, 1.5),
                            (0.06, 1.55), (0.0, 1.57)], M['iron'], loc=p, seg=12, collection=col, lm='furn')
    tube(f'{name}_ring', circle(p + Vector((0, 0, 1.34)), 0.3, (1, 0, 0), (0, 1, 0), n=48), 0.014, M['iron'], col, closed=True, seg=8, lm='furn')
    for k in range(8):
        a = 2 * math.pi * k / 8; q = p + Vector((0.3 * math.cos(a), 0.3 * math.sin(a), 1.34))
        tube(f'{name}_arm{k}', [p + Vector((0, 0, 1.26)), p + Vector((0.15 * math.cos(a), 0.15 * math.sin(a), 1.28)), q], 0.011, M['iron'], col, seg=6, lm='furn')
        flames.append(_candle(f'{name}_c{k}', q, M, col, rnd))
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.5; q = p + Vector((0.11 * math.cos(a), 0.11 * math.sin(a), 1.56))
        tube(f'{name}_top{k}', [p + Vector((0, 0, 1.54)), q], 0.01, M['iron'], col, seg=6, lm='furn')
        flames.append(_candle(f'{name}_t{k}', q, M, col, rnd))
    return flames


def _candle(name, q, M, col, rnd):
    cyl(f'{name}_cup', 0.045, 0.03, q + Vector((0, 0, 0.015)), M['iron'], seg=12, collection=col, lm='furn')
    h = rnd.uniform(0.12, 0.28)
    cyl(f'{name}_wax', 0.032, h, q + Vector((0, 0, 0.03 + h / 2)), M['wax'], seg=12, collection=col, lm='furn')
    f = q + Vector((0, 0, 0.03 + h + 0.024))
    lathe(f'{name}_flame', [(0.0, -0.013), (0.009, -0.004), (0.01, 0.007), (0.006, 0.02), (0.0, 0.034)], M['flame'], loc=f, seg=8, collection=col)
    return f + Vector((0, 0, 0.006))


def floor_bands(M, col):
    """The dark marble inlaid in the cream: a broad frame down the nave with a disc at its heart, frames in the aisles
    between the columns; flush with the floor."""
    t, z = 0.3, 0.002
    def frame(name, x0, x1, y0, y1):
        for k, (a, b, c_, d) in enumerate(((x0, x1, y0, y0 + t), (x0, x1, y1 - t, y1), (x0, x0 + t, y0 + t, y1 - t), (x1 - t, x1, y0 + t, y1 - t))):
            box(f'{name}_{k}', (b - a, d - c_, 0.004), ((a + b) / 2, (c_ + d) / 2, z), M['marble_dark'], bev=0, collection=col, lm='arch')
    frame('band_nave', -3.0, 3.0, FRONT, DAIS_FRONT - 0.5)
    cyl('band_disc0', 0.85, 0.004, (0, (FRONT + DAIS_FRONT - 0.5) / 2 + 0.6, z), M['marble_dark'], seg=72, bev=0, collection=col, lm='arch')
    for k, (a, b) in enumerate(((-7.4, -4.3), (4.3, 7.4))):
        frame(f'band_side{k}', a, b, -3.95, -2.65)
        cyl(f'band_side_disc{k}', 0.42, 0.004, ((a + b) / 2, -3.3, z), M['marble_dark'], seg=48, bev=0, collection=col, lm='arch')


def section(objs, M):
    """Every face the cut passes through, flat and dark: the walls', the columns' and the arches' tops (in the module,
    after `shrink`)."""
    for ob in objs:
        if not ob.name.startswith(('solid_', 'left_wall', 'back_wall', 'bay_arch', 'colonnette', 'win_jamb', 'kerb')): continue
        me = ob.data
        if M['section'].name not in [m.name for m in me.materials if m]: me.materials.append(M['section'])
        k = [m.name if m else '' for m in me.materials].index(M['section'].name)
        for f in me.polygons:
            c = sum((me.vertices[i].co for i in f.vertices), Vector()) / len(f.vertices)
            if f.normal.z > 0.9 and abs(c.z - RH * SCALE) < 0.006: f.material_index = k


# ---------------------------------------------------------------- light
WARM = (1.0, 0.66, 0.36)                   # candle flames
SUN = (1.0, 0.86, 0.66)                    # a summer afternoon in King's Landing
SUN_DIR = Vector((0.62, 0.45, -0.64)).normalized()   # the way the sun travels: down through the left aisle's high windows


def lights(flames, glass):
    """The sun through the high windows of the left aisle (shafts across the dais, the throne and the floor), the sky's
    light in them; the stag window glowing over the throne and throwing its colours down the steps; the candles; the
    passages' torches. Returns the lights (at the hall's true size: `shrink` brings them into the module)."""
    out = []
    def light(name, kind, loc, energy, colour, **kw):
        ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = colour
        for k, v in kw.items(): setattr(ld, k, v)
        ob = cine.link(bpy.data.objects.new(name, ld)); ob.location = loc; out.append(ob)
        if kind in ('AREA', 'SPOT', 'SUN'): ob.visible_camera = False; ob.visible_glossy = False
        return ob
    def aim(ob, d): ob.rotation_euler = Vector(d).to_track_quat('-Z', 'Y').to_euler()
    aim(light('sun', 'SUN', (0, 0, 30), 11.0, SUN, angle=math.radians(1.0)), SUN_DIR)
    z0, z1 = HIGH_Z
    for k, (a, b) in enumerate(HIGH_WINDOWS):
        aim(light(f'sky{k}', 'AREA', (LEFT - 0.9, (a + b) / 2, (z0 + z1) / 2), 2400.0, (0.9, 0.92, 1.0), shape='RECTANGLE', size=b - a, size_y=z1 - z0), (1, 0, -0.35))
    aim(light('window', 'AREA', (0, YW2 + 0.35, 6.0), 1800.0, (1.0, 0.84, 0.6), shape='RECTANGLE', size=WIN_W, size_y=5.2), (0, -1, -0.45))
    for k, f in enumerate(flames): light(f'candle{k}', 'POINT', f + Vector((0, 0, 0.03)), 4.0, WARM, shadow_soft_size=0.012)
    for k, bx in enumerate(BAYS):
        light(f'torch{k}', 'POINT', (bx, BACK - 0.35, 2.6), 380.0, WARM, shadow_soft_size=0.1)
    return out


def shrink(objs, lights_):
    """Bring the hall, built at its true size, into the module: every object and light scaled by SCALE about the
    origin; the lights' sizes with them and their power by SCALE squared (the same radiance on smaller surfaces)."""
    S_ = Matrix.Scale(SCALE, 4)
    for o in objs: o.matrix_world = S_ @ o.matrix_world
    for l in lights_:
        l.location = l.location * SCALE
        d = l.data
        if d.type == 'AREA': d.size *= SCALE; d.size_y *= SCALE
        if d.type in ('POINT', 'SPOT', 'AREA'): d.energy *= SCALE ** 2; d.shadow_soft_size *= SCALE
    bpy.context.view_layer.update()
