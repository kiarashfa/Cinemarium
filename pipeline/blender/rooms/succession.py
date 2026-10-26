# Succession · the Roys' hunting lodge in Hungary, the night of "Boar on the Floor" (2x03, "Hunting"). The room is
# the Grand Ballroom at Oheka Castle, dressed for the hunt: cream boiserie of tall moulded panels between flat
# pilasters, a chimney breast at the end with a cream stone mantel round rose-tan marble slips and a sooty brick
# firebox, an iron scroll screen, a dark landscape over the mantel; suits of blackened armour at the fireplace and by
# the door; on the long wall the French windows (night behind them) in swagged champagne silk, and between them, where
# the castle's great paintings hang, clusters of antlers: a stag's skull on a carved shield ringed by roe
# frontlets on little black shields; brass sconces with small shades. One long walnut table down the room on a dark
# rug, high-backed cognac leather armchairs with nails, crystal and pewter, pillar candles in black iron, fruit, the
# brocade runner; the buffet and the bar table by the near wall. Lit only by the fire, the candles and the sconces.
#
# The ballroom is too big for the module at 1:6: like the throne room it is built at its true size in a module
# 1 / SCALE times the size, then shrunk by SCALE (0.6) with the people. The case sees the show's master: the window
# wall at the back, the fireplace end on the left, the table broadside; the room goes on past the right cut. Where the
# cut passes through walls, pilasters and the breast: a dark `section` face.
import math, os, random
import bpy, bmesh
from mathutils import Vector, Matrix
import cine
from cine import box, cyl, material, lathe, place, rounded_slab, slab_profile, cloth_panel, moulding
from rooms.seinfeld import Face, uv_rect, tube, circle, _glow
from rooms.the_godfather import _fit, _plain

SCALE = 0.6                                # the room's own scale inside the module (as the throne room's)
W, D, H = 9.6 / SCALE, 7.6 / SCALE, 3.0 / SCALE   # the module, at the ballroom's true size
T = 0.14 / SCALE                           # the module's walls
LEFT, BACK, RIGHT, FRONT = -W / 2 + T, D / 2 - T, W / 2 - T, -D / 2 + T
RH = 2.95 / SCALE                          # the cut
KH = 0.22 / SCALE                          # the cut-away's kerb
TEX = os.path.join(cine.OUT, 'textures', 'succession')
tx = lambda n: os.path.join(TEX, n)
PH = lambda n: os.path.join(cine.CACHE, 'polyhaven', n, f'{n}_1k.gltf')
OBJ = lambda n: os.path.join(cine.CACHE, 'objaverse', n)

# the boiserie
BASE, DADO, FRIEZE = 0.3, 0.95, 4.45       # the skirting's top, the dado rail, the frieze rail over the tall panels
PIL_W, PIL_O = 0.5, 0.07                   # the pilasters: width, how far they stand out
# the window wall (the back): two French windows, a pilaster either side of each, panels between
WIN_X, WW, WIN_TOP = (-4.3, 2.3), 1.7, 4.15
PIL_BACK = (-5.55, -3.05, 1.05, 3.55, 7.3)
CLUSTERS = ((-1.0, 3.15, 1.0), (5.43, 3.1, 0.82))   # the antler clusters: x, centre height, size
# the fireplace end (the left): the chimney breast, the doors either side
YF = 0.4                                   # the fireplace's axis (the table's)
BR_W, BR_D = 2.7, 0.5                      # the breast: width, depth out from the wall
XB = LEFT + BR_D                           # its face
OPEN_W, OPEN_H = 1.25, 1.0                 # the firebox's opening
SHELF = 1.42                               # the mantel shelf's top
DOORS_L = (-3.2, 4.05)                     # the end wall's doors (y centres), double, panelled walnut
DOOR_W, DOOR_H = 1.7, 3.1
PIL_LEFT = (-5.3, 5.55)
ARMOUR = ((LEFT + 0.42, YF + 1.78), (LEFT + 0.42, -4.55))
# the table and its chairs
YT = 0.4                                   # the table's axis
TX0, TX1, TW, TH = -4.1, 2.3, 1.25, 0.76   # its ends, width, height (top)
SEATS_X = (-3.42, -2.57, -1.72, -0.87, -0.02, 0.83, 1.68)
SIDE_Y = 0.84                              # chairs' seats from the table's axis
HEAD = (-4.62, YT)                         # Logan's chair at the head (it faces +x)
FOOT = (2.78, YT)
SEAT_Z = 0.48                              # cushion tops


def seat(side, k):
    """A side chair's seat centre and facing: side +1 is the far side (facing the case), -1 the near."""
    return Vector((SEATS_X[k], YT + side * SIDE_Y, 0.0)), Vector((0, -side, 0))


def head_seat():
    return Vector((*HEAD, 0.0)), Vector((1, 0, 0))


PLATE = (TX0 + 0.2, YT + 0.42)            # the sausages' plate on the table by Logan's left hand (he carries it in his act)
PULLED = {(-1, 0): (0.38, 14.0), (-1, 1): (0.32, -11.0), (-1, 2): (0.45, 18.0)}   # the boars' chairs, pushed back askew


# ---------------------------------------------------------------- materials
def mats():
    M = {}
    M['floor'] = material('oak_strips', rough=0.42, maps={'color': tx('floor_color.jpg'), 'normal': tx('floor_normal.jpg')}, scale=1.0, normal_strength=0.25)
    M['walnut'] = material('walnut', rough=0.38, maps={'color': tx('walnut_color.jpg'), 'normal': tx('walnut_normal.jpg')}, scale=1.0, normal_strength=0.3, coat=0.5, coat_rough=0.2)
    M['band'] = material('walnut_band', rough=0.45, maps={'color': tx('walnut_color.jpg')}, scale=1.0)
    M['wall'] = material('boiserie', rough=0.62, maps={'color': tx('wall_color.jpg'), 'normal': tx('wall_normal.jpg')}, scale=2.0, normal_strength=0.2)
    M['stone'] = material('mantel_stone', rough=0.55, maps={'color': tx('wall_color.jpg')}, scale=1.2)
    M['marble'] = material('marble_slips', rough=0.2, maps={'color': tx('marble_color.jpg')}, scale=0.9, coat=0.6)
    M['brick'] = material('firebox_brick', rough=0.9, maps={'color': tx('brick_color.jpg'), 'normal': tx('brick_normal.jpg')}, scale=0.9, normal_strength=0.6,
                          emission=(1.0, 0.42, 0.16), emission_strength=0.6)       # the fire's glare on it, the same in the bake and live
    M['leather'] = material('cognac_leather', rough=0.42, maps={'color': tx('leather_color.jpg'), 'normal': tx('leather_normal.jpg')}, scale=0.5, normal_strength=0.5, coat=0.3, coat_rough=0.3)
    M['drape'] = material('silk_drape', rough=0.45, maps={'color': tx('drape_color.jpg'), 'normal': tx('drape_normal.jpg')}, scale=0.6, normal_strength=0.3, sheen=0.5, sheen_tint=(0.6, 0.5, 0.4))
    M['runner'] = material('brocade_runner', rough=0.6, maps={'color': tx('runner_color.jpg')}, scale=0.45, sheen=0.4, sheen_tint=(0.6, 0.45, 0.3))
    M['rug'] = material('trellis_rug', rough=0.95, maps={'color': tx('rug_color.jpg'), 'normal': tx('pile_normal.jpg')}, scale=1.0, normal_strength=0.4, specular=0.25,
                        sheen=0.3, sheen_tint=(0.4, 0.32, 0.24))
    M['dark_wood'] = material('dark_wood', rough=0.5, maps={'color': tx('dark_wood_color.jpg')}, scale=0.6, coat=0.3)
    M['painting'] = material('courbet', rough=0.45, maps={'color': tx('painting_color.jpg')}, scale=1.0, coat=0.5, coat_rough=0.3)
    M['shade'] = material('parchment_shade', rough=0.8, maps={'color': tx('shade_color.jpg')}, scale=0.3, emission=(1.0, 0.74, 0.44), emission_strength=1.6)
    M['green_shade'] = material('green_shade', (0.012, 0.03, 0.016), rough=0.55, coat=0.3)
    M['brass'] = material('brass', (0.66, 0.46, 0.2), rough=0.3, metal=1.0)
    M['gilt'] = material('gilt', (0.62, 0.45, 0.2), rough=0.32, metal=0.9)
    M['iron'] = material('black_iron', (0.03, 0.028, 0.026), rough=0.6, metal=0.3)      # dull: lit live, a bright metal glints white
    M['pewter'] = material('pewter', (0.42, 0.41, 0.4), rough=0.32, metal=1.0)
    M['silver'] = material('silver', (0.74, 0.72, 0.7), rough=0.2, metal=1.0)
    M['steel'] = material('blackened_steel', (0.07, 0.068, 0.066), rough=0.36, metal=1.0)
    M['china'] = material('cream_china', (0.8, 0.76, 0.66), rough=0.18, coat=0.7)
    M['glass'] = material('crystal', (0.62, 0.62, 0.6), rough=0.05, coat=1.0)
    M['wine'] = material('red_wine', (0.14, 0.012, 0.02), rough=0.08, coat=1.0)
    M['water'] = material('water_in_glass', (0.5, 0.52, 0.5), rough=0.05, coat=1.0)
    M['wax'] = material('candle_wax', (0.78, 0.72, 0.58), rough=0.5, sheen=0.2, sheen_tint=(0.5, 0.45, 0.35))
    M['flame'] = material('flame', (1.0, 0.7, 0.3), rough=0.5, emission=(1.0, 0.62, 0.24), emission_strength=24.0)
    M['fire'] = material('fire', (1.0, 0.45, 0.12), rough=0.5, emission=(1.0, 0.34, 0.06), emission_strength=4.0)
    M['ember'] = material('embers', (0.3, 0.06, 0.02), rough=0.8, emission=(1.0, 0.3, 0.08), emission_strength=3.0)
    M['log'] = material('log_bark', (0.06, 0.045, 0.035), rough=0.9)
    M['soot'] = material('soot', (0.018, 0.016, 0.015), rough=0.95)
    M['night'] = material('night_glass', (0.01, 0.012, 0.016), rough=0.04, coat=1.0)
    M['white_paint'] = material('window_paint', (0.72, 0.68, 0.6), rough=0.4)
    M['food_brown'] = material('roast', (0.22, 0.1, 0.05), rough=0.55)
    M['food_pale'] = material('potato', (0.62, 0.48, 0.24), rough=0.6)
    M['food_green'] = material('greens', (0.08, 0.16, 0.05), rough=0.6)
    M['sausage'] = material('sausage', (0.32, 0.1, 0.06), rough=0.35, coat=0.4)
    M['bread'] = material('bread', (0.58, 0.36, 0.16), rough=0.7)
    M['cheese'] = material('cheese', (0.82, 0.68, 0.36), rough=0.5)
    M['grape'] = material('grapes', (0.22, 0.05, 0.12), rough=0.25, coat=0.6)
    M['green_grape'] = material('green_grapes', (0.42, 0.5, 0.14), rough=0.25, coat=0.6)
    M['leaf'] = material('autumn_leaf', (0.3, 0.14, 0.04), rough=0.6)
    M['leaf2'] = material('autumn_leaf_dark', (0.12, 0.08, 0.03), rough=0.6)
    M['berry'] = material('berries', (0.4, 0.04, 0.03), rough=0.4)
    M['napkin'] = material('linen_napkin', (0.78, 0.74, 0.66), rough=0.8)
    M['cloth_dark'] = material('arming_cloth', (0.05, 0.045, 0.04), rough=0.8)
    M['kerb'] = material('kerb', (0.16, 0.12, 0.09), rough=0.9)
    M['section'] = material('section', (0.03, 0.028, 0.026), rough=0.92)
    M['phantom'] = material('phantom_cream', (0.52, 0.46, 0.36), rough=0.9)
    _glow(M['painting'], 0.0)
    return M


M_ = {}
BEAD = [(0, 0), (0.012, 0.004), (0.02, 0.014), (0.019, 0.028), (0.01, 0.038), (0, 0.042)]
SKIRT = [(0, 0), (0.03, 0), (0.03, 0.24), (0.022, 0.26), (0.012, 0.28), (0, 0.3)]
RAIL = [(0, 0), (0.025, 0.006), (0.04, 0.02), (0.04, 0.04), (0.025, 0.055), (0, 0.06)]
FRIEZE_RAIL = [(0, 0), (0.03, 0.0), (0.05, 0.03), (0.06, 0.07), (0.04, 0.1), (0, 0.11)]


# ---------------------------------------------------------------- the boiserie
def _spans(L, cuts):
    out, u = [], 0.0
    for c0, c1 in sorted(cuts):
        if c0 > u + 1e-4: out.append((u, c0))
        u = max(u, c1)
    if u < L - 1e-4: out.append((u, L))
    return out


def frame_rect(face, name, u0, u1, z0, z1, o, col, prof=BEAD, mat=None):
    """A rectangle of applied moulding on a wall (a panel's frame)."""
    mat = mat or M_['wall']; b = max(p[1] for p in prof)
    face.run(f'{name}_b', u0, u1, z0, prof, mat, col, o=o, lm='arch')
    face.run(f'{name}_t', u0, u1, z1 - b, prof, mat, col, o=o, lm='arch')
    for k, u in enumerate((u0, u1 - b)):
        moulding(f'{name}_s{k}', face.at(u, o, z0 + b), face.at(u, o, z1 - b), face.n, prof, mat, collection=col, lm='arch')


def boiserie(face, name, col, openings=(), pilasters=(), low_openings=()):
    """A wall dressed as the ballroom's: skirting, low panels under a dado rail, tall panels to the frieze rail, a plain
    frieze up to the cut; flat pilasters (u centres) with sunk panels standing between the bays. `openings` (u0, u1)
    reach from the floor to their heads (doors, French windows): the wall is bare there."""
    cuts = [(a, b) for a, b in openings] + [(u - PIL_W / 2, u + PIL_W / 2) for u in pilasters]
    for k, (a, b) in enumerate(_spans(face.L, [(a, b) for a, b in openings])):
        face.run(f'{name}_skirt{k}', a, b, 0.0, SKIRT, M_['wall'], col, o=0.0, lm='arch')
        face.run(f'{name}_dado{k}', a, b, DADO - 0.03, RAIL, M_['wall'], col, o=0.0, lm='arch')
        face.run(f'{name}_frieze{k}', a, b, FRIEZE, FRIEZE_RAIL, M_['wall'], col, o=0.0, lm='arch')
    for k, (a, b) in enumerate(_spans(face.L, cuts)):
        if b - a < 0.3: continue
        frame_rect(face, f'{name}_lo{k}', a + 0.12, b - 0.12, BASE + 0.1, DADO - 0.12, 0.0, col)
        frame_rect(face, f'{name}_hi{k}', a + 0.16, b - 0.16, DADO + 0.2, FRIEZE - 0.22, 0.0, col)
    for k, u in enumerate(pilasters):
        a, b = u - PIL_W / 2, u + PIL_W / 2
        face.slab(f'solid_{name}_pil{k}', a, b, 0.0, RH, 0.0, PIL_O, M_['wall'], col, bev=0.006, lm='arch')
        face.run(f'{name}_pil{k}_skirt', a - 0.03, b + 0.03, 0.0, SKIRT, M_['wall'], col, o=PIL_O, lm='arch')
        face.slab(f'{name}_pil{k}_cap', a - 0.04, b + 0.04, FRIEZE - 0.02, FRIEZE + 0.14, PIL_O, 0.05, M_['wall'], col, bev=0.012, lm='arch')
        frame_rect(face, f'{name}_pil{k}_pa', a + 0.09, b - 0.09, BASE + 0.15, FRIEZE - 0.15, PIL_O, col)


def _faces():
    return {'back': Face((LEFT, BACK), (RIGHT, BACK), (0, -1)),               # u = x - LEFT
            'left': Face((LEFT, FRONT), (LEFT, BACK), (1, 0))}                # u = y - FRONT


def shell(M, arch, phantom):
    """The floor, the module's left and back walls (round the windows and doors), the chimney breast; the boiserie;
    kerbs; phantoms (the ballroom above the cut and beyond it)."""
    M_.clear(); M_.update(M)
    box('subfloor', (W, D, 0.05), (0, 0, -0.045), M['kerb'], bev=0, collection=arch, lm='arch')
    box('floor', (W - 2 * T + 0.003, D - T - 0.003, 0.03), (0, -T / 2, -0.015), M['floor'], bev=0, collection=arch, lm='arch')
    # the walnut bands round the floor's edge, 0.3 m in
    for k, (c, s) in enumerate((((LEFT + 0.45, (BACK + FRONT) / 2), (0.16, BACK - FRONT - 0.6)), (((LEFT + RIGHT) / 2, BACK - 0.45), (RIGHT - LEFT - 0.6, 0.16)))):
        box(f'floor_band{k}', (s[0], s[1], 0.004), (c[0], c[1], 0.002), M['band'], bev=0, collection=arch, lm='arch')
    # the module's back wall: the windows' openings, glass set in it
    xs = [(c - WW / 2, c + WW / 2) for c in WIN_X]
    for k, (a, b) in enumerate(_spans(W, [(a + W / 2, b + W / 2) for a, b in xs])):
        box(f'back_wall_{k}', (b - a, T, RH), (a - W / 2 + (b - a) / 2, D / 2 - T / 2, RH / 2), M['wall'], bev=0, collection=arch, lm='arch')
    for k, (a, b) in enumerate(xs):
        box(f'back_wall_head{k}', (b - a, T, RH - WIN_TOP), ((a + b) / 2, D / 2 - T / 2, (RH + WIN_TOP) / 2), M['wall'], bev=0, collection=arch, lm='arch')
    # the module's left wall, round the doors
    ys = [(c - DOOR_W / 2, c + DOOR_W / 2) for c in DOORS_L]
    for k, (a, b) in enumerate(_spans(D, [(a + D / 2, b + D / 2) for a, b in ys])):
        box(f'left_wall_{k}', (T, b - a, RH), (-W / 2 + T / 2, a - D / 2 + (b - a) / 2, RH / 2), M['wall'], bev=0, collection=arch, lm='arch')
    for k, (a, b) in enumerate(ys):
        box(f'left_wall_head{k}', (T, b - a, RH - DOOR_H), (-W / 2 + T / 2, (a + b) / 2, (RH + DOOR_H) / 2), M['wall'], bev=0, collection=arch, lm='arch')
    # the chimney breast, solid from the wall out to XB but for the firebox
    y0, y1 = YF - BR_W / 2, YF + BR_W / 2; o0, o1 = YF - OPEN_W / 2, YF + OPEN_W / 2
    for k, (a, b) in enumerate(((y0, o0), (o1, y1))):
        box(f'solid_breast{k}', (BR_D, b - a, RH), (LEFT + BR_D / 2, (a + b) / 2, RH / 2), M['wall'], bev=0, collection=arch, lm='arch')
    box('solid_breast_top', (BR_D, OPEN_W, RH - OPEN_H), (LEFT + BR_D / 2, YF, (RH + OPEN_H) / 2), M['wall'], bev=0, collection=arch, lm='arch')
    # the cut-away
    box('kerb_front', (W, T, KH), (0, -D / 2 + T / 2, KH / 2), M['kerb'], bev=0.002, collection=arch, lm='arch')
    box('kerb_right', (T, D - 2 * T, KH), (W / 2 - T / 2, 0, KH / 2), M['kerb'], bev=0.002, collection=arch, lm='arch')
    _phantoms(M, phantom)
    F = _faces()
    bw = F['back']
    boiserie(bw, 'back', arch, openings=[(c - WW / 2 - 0.16 - LEFT, c + WW / 2 + 0.16 - LEFT) for c in WIN_X], pilasters=[x - LEFT for x in PIL_BACK])
    lw = F['left']
    boiserie(lw, 'left', arch, openings=[(c - DOOR_W / 2 - 0.16 - FRONT, c + DOOR_W / 2 + 0.16 - FRONT) for c in DOORS_L] + [(y0 - FRONT, y1 - FRONT)],
             pilasters=[y - FRONT for y in PIL_LEFT])
    _breast_finish(M, arch)


TOP = 7.2                                  # the vault's crown


def _phantoms(M, col):
    """For the light only: the walls above the cut, the vault, the near long wall (the buffet's) and the far end beyond
    the right cut, the room's floor going on."""
    P = M['phantom']; ph = lambda name, size, loc: box(name, size, loc, P, bev=0, collection=col, bake_only=1)
    x0, x1, y0 = LEFT - 0.3, 13.5, FRONT - 0.3
    ph('ph_back_hi', (x1 - x0, 0.4, TOP - RH), ((x0 + x1) / 2, BACK + 0.2, (TOP + RH) / 2))
    ph('ph_left_hi', (0.4, BACK - y0, TOP - RH), (LEFT - 0.2, (BACK + y0) / 2, (TOP + RH) / 2))
    ph('ph_front', (x1 - x0, 0.4, TOP - KH), ((x0 + x1) / 2, FRONT - 0.2, KH + (TOP - KH) / 2))
    ph('ph_far_end', (0.4, BACK - y0, TOP), (x1, (BACK + y0) / 2, TOP / 2))
    ph('ph_vault', (x1 - x0, BACK - y0, 0.4), ((x0 + x1) / 2, (BACK + y0) / 2, TOP + 0.2))
    ph('ph_floor_r', (x1 - RIGHT, BACK - y0, 0.05), ((x1 + RIGHT) / 2, (BACK + y0) / 2, -0.03))
    for k, c in enumerate(WIN_X):                                               # the windows' night beyond (dark, closed)
        ph(f'ph_night{k}', (WW + 0.4, 0.2, WIN_TOP), (c, BACK + 0.6, WIN_TOP / 2))


def _breast_finish(M, col):
    """The chimney breast's face and sides dressed: skirting, a frame round the overmantel panel, the frieze rail;
    pilaster-like returns at its corners."""
    bf = Face((XB, YF - BR_W / 2), (XB, YF + BR_W / 2), (1, 0))
    bf.run('breast_frieze', 0.0, BR_W, FRIEZE, FRIEZE_RAIL, M['wall'], col, o=0.0, lm='arch')
    frame_rect(bf, 'breast_over', 0.22, BR_W - 0.22, SHELF + 0.32, FRIEZE - 0.2, 0.0, col)
    frame_rect(bf, 'breast_over_in', 0.34, BR_W - 0.34, SHELF + 0.44, FRIEZE - 0.32, 0.0, col)
    for k, (yy, n) in enumerate(((YF - BR_W / 2, (0, -1)), (YF + BR_W / 2, (0, 1)))):
        sf = Face((LEFT, yy), (XB, yy), n) if k == 1 else Face((XB, yy), (LEFT, yy), n)
        sf.run(f'breast_side_skirt{k}', 0.0, BR_D, 0.0, SKIRT, M['wall'], col, o=0.0, lm='arch')
        sf.run(f'breast_side_dado{k}', 0.0, BR_D, DADO - 0.03, RAIL, M['wall'], col, o=0.0, lm='arch')
        sf.run(f'breast_side_frieze{k}', 0.0, BR_D, FRIEZE, FRIEZE_RAIL, M['wall'], col, o=0.0, lm='arch')


# ---------------------------------------------------------------- the fireplace
def fireplace(M, col, rnd):
    """The mantelpiece on the breast: cream stone jambs and lintel round rose-tan marble slips, the shelf; the brick
    firebox with its fire on iron dogs, the hearth, the iron scroll screen; over the shelf the autumn spray and
    Courbet's stags in gilt; a sconce either side. Returns (the fire's points, the sconces' bulbs)."""
    y, x = YF, XB; o0, o1 = y - OPEN_W / 2, y + OPEN_W / 2
    jw, sw = 0.36, 0.17                                                         # the stone jambs' width, the slips'
    for s in (-1, 1):
        yc = y + s * (OPEN_W / 2 + sw + jw / 2)
        box(f'mantel_jamb{s}', (0.13, jw, OPEN_H + sw + 0.02), (x + 0.065, yc, (OPEN_H + sw + 0.02) / 2), M['stone'], bev=0.012, collection=col, lm='furn')
        box(f'mantel_plinth{s}', (0.17, jw + 0.04, 0.16), (x + 0.085, yc, 0.08), M['stone'], bev=0.01, collection=col, lm='furn')
        box(f'fire_slip{s}', (0.04, sw, OPEN_H + sw), (x + 0.02, y + s * (OPEN_W / 2 + sw / 2), (OPEN_H + sw) / 2), M['marble'], bev=0.004, collection=col, lm='furn')
    box('fire_slip_top', (0.04, OPEN_W, sw), (x + 0.02, y, OPEN_H + sw / 2), M['marble'], bev=0.004, collection=col, lm='furn')
    lw = OPEN_W + 2 * (sw + jw)
    box('mantel_lintel', (0.13, lw, SHELF - 0.06 - (OPEN_H + sw)), (x + 0.065, y, (SHELF - 0.06 + OPEN_H + sw) / 2), M['stone'], bev=0.012, collection=col, lm='furn')
    moulding('mantel_bed', (x + 0.13, y - lw / 2, SHELF - 0.12), (x + 0.13, y + lw / 2, SHELF - 0.12), (1, 0, 0), [(0, 0), (0.02, 0.0), (0.05, 0.03), (0.07, 0.06), (0, 0.06)], M['stone'], collection=col, lm='furn')
    box('mantel_shelf', (0.32, lw + 0.16, 0.07), (x + 0.16, y, SHELF - 0.035), M['stone'], bev=0.012, collection=col, lm='furn')
    # the firebox: brick back and cheeks, a sooty floor; the hearth before it
    d = BR_D - 0.03
    # (what stands in the fire's glare is lit live: baked, its few blazing texels would squeeze the whole atlas)
    box('fire_back', (0.04, OPEN_W, OPEN_H), (LEFT + 0.05, y, OPEN_H / 2), M['brick'], bev=0, collection=col, live=1)
    for s in (-1, 1): box(f'fire_cheek{s}', (d, 0.04, OPEN_H), (LEFT + 0.03 + d / 2, y + s * (OPEN_W / 2 - 0.02), OPEN_H / 2), M['brick'], bev=0, collection=col, live=1)
    box('fire_roof', (d, OPEN_W, 0.04), (LEFT + 0.03 + d / 2, y, OPEN_H - 0.02), M['soot'], bev=0, collection=col, live=1)
    box('fire_floor', (d, OPEN_W, 0.03), (LEFT + 0.03 + d / 2, y, 0.015), M['soot'], bev=0, collection=col, live=1)
    box('hearth', (0.62, lw + 0.1, 0.04), (x + 0.31, y, 0.02), M['marble'], bev=0.006, collection=col, lm='furn')
    # the fire: iron dogs, three logs, embers, the flames
    fx = LEFT + 0.25; pts = []
    for s in (-1, 1):
        tube(f'firedog{s}', [(fx - 0.12, y + s * 0.3, 0.03), (fx + 0.1, y + s * 0.3, 0.06), (fx + 0.16, y + s * 0.3, 0.2), (fx + 0.13, y + s * 0.3, 0.27)], 0.02, M['iron'], col, seg=8, live=1)
    for k, (a, b, r) in enumerate((((fx - 0.05, y - 0.42, 0.11), (fx - 0.02, y + 0.4, 0.13), 0.065), ((fx + 0.08, y - 0.38, 0.1), (fx + 0.06, y + 0.36, 0.09), 0.055), ((fx, y - 0.25, 0.22), (fx + 0.03, y + 0.3, 0.19), 0.05))):
        tube(f'log{k}', [a, b], r, M['log'], col, seg=10, live=1)
    cyl('embers', 0.32, 0.03, (fx, y, 0.045), M['ember'], seg=24, collection=col)
    for k in range(16):
        p = Vector((fx + rnd.uniform(-0.06, 0.08), y + rnd.uniform(-0.38, 0.38), 0.16 + rnd.uniform(0, 0.08))); h = rnd.uniform(0.1, 0.26); r = rnd.uniform(0.018, 0.032)
        fl = lathe(f'fire_flame{k}', [(0.0, -0.01), (r, 0.015), (r * 1.1, h * 0.3), (r * 0.6, h * 0.65), (0.0, h)], M['fire'], loc=p, seg=8, collection=col)
        fl.scale = (0.6, 1.0, 1.0); fl.rotation_euler = (rnd.uniform(-0.25, 0.25), rnd.uniform(-0.2, 0.2), 0)
        pts.append(p + Vector((0, 0, h * 0.35)))
    # the screen: three iron panels, the middle one arched, scrolls inside
    sx = x + 0.38; hs = 0.82
    for k, (a, b, h) in enumerate(((y - 0.78, y - 0.46, 0.68), (y - 0.46, y + 0.46, hs), (y + 0.46, y + 0.78, 0.68))):
        xa = sx - (0.1 if k != 1 else 0.0); xb = sx - (0.1 if k != 1 else 0.0)
        if k == 0: xa, xb = sx - 0.16, sx
        if k == 2: xa, xb = sx, sx - 0.16
        if k == 1:
            top = [(sx, a + (b - a) * i / 16, h - 0.1 + 0.1 * math.sin(math.pi * i / 16)) for i in range(17)]
            tube('screen_top1', top, 0.012, M['iron'], col, seg=6, live=1)
        else:
            tube(f'screen_top{k}', [(xa, a, h), (xb, b, h)], 0.012, M['iron'], col, seg=6, live=1)
        tube(f'screen_bot{k}', [(xa, a, 0.06), (xb, b, 0.06)], 0.012, M['iron'], col, seg=6, live=1)
        for j, (xx, yy) in enumerate(((xa, a), (xb, b))):
            tube(f'screen_post{k}{j}', [(xx, yy, 0.0), (xx, yy, h - (0.1 if k == 1 else 0.0))], 0.013, M['iron'], col, seg=6, live=1)
        n = 3 if k == 1 else 1
        for i in range(n):
            t = (i + 0.5) / n; cx_, cy_ = xa + (xb - xa) * t, a + (b - a) * t
            for zz, rr in ((0.3, 0.11), (0.52, 0.09)):
                u = Vector((xb - xa, b - a, 0)).normalized()
                tube(f'screen_scroll{k}{i}{zz}', circle((cx_, cy_, zz), rr, u, (0, 0, 1), n=20), 0.007, M['iron'], col, closed=True, seg=5, live=1)
    # fire irons on their stand at the left of the hearth
    st = Vector((x + 0.3, y - lw / 2 - 0.12, 0.0))
    cyl('irons_base', 0.11, 0.03, st + Vector((0, 0, 0.015)), M['iron'], seg=16, collection=col, lm='furn')
    tube('irons_shaft', [st, st + Vector((0, 0, 0.72))], 0.012, M['iron'], col, seg=6, lm='furn')
    for k in range(3):
        a = 2 * math.pi * k / 3; d_ = Vector((math.cos(a), math.sin(a), 0)) * 0.05
        tube(f'iron_tool{k}', [st + d_ + Vector((0, 0, 0.08)), st + d_ * 0.6 + Vector((0, 0, 0.72))], 0.007, M['brass'], col, seg=6, lm='furn')
    # the overmantel: Courbet in gilt, sconces either side of it, the spray on the shelf
    pw, phh, fw = 1.36, 1.02, 0.11                                             # the canvas, the gilt frame's width
    c = Vector((XB, y, 3.05))
    cv = box('painting_canvas', (0.02, pw, phh), c + Vector((0.03, 0, 0)), M['painting'], bev=0, collection=col, lm='furn')
    uv_rect(cv, 'x')
    for d in cv.data.uv_layers['UVMap'].data: d.uv = (1 - d.uv[0], d.uv[1])
    for k, (dy, dz, sy, sz) in enumerate(((0, (phh + fw) / 2, pw + 2 * fw, fw), (0, -(phh + fw) / 2, pw + 2 * fw, fw), ((pw + fw) / 2, 0, fw, phh), (-(pw + fw) / 2, 0, fw, phh))):
        box(f'painting_frame{k}', (0.07, sy, sz), c + Vector((0.045, dy, dz)), M['gilt'], bev=0.018, seg=3, collection=col, lm='furn')
    for k, (dy, dz, sy, sz) in enumerate(((0, phh / 2 + 0.012, pw + 0.05, 0.024), (0, -phh / 2 - 0.012, pw + 0.05, 0.024), (pw / 2 + 0.012, 0, 0.024, phh), (-pw / 2 - 0.012, 0, 0.024, phh))):
        box(f'painting_slip{k}', (0.05, sy, sz), c + Vector((0.05, dy, dz)), M['gilt'], bev=0.008, collection=col, lm='furn')
    bulbs = [sconce(f'breast_sconce{k}', Vector((XB, y + s * 1.08, 2.62)), Vector((1, 0, 0)), M, col, arms=1) for k, s in enumerate((-1, 1))]
    spray(f'mantel_spray', Vector((XB + 0.16, y, SHELF)), 0.9, Vector((1, 0, 0)), M, col, rnd)
    return pts, [b for bb in bulbs for b in bb]


def sconce(name, p, n, M, col, arms=3):
    """A brass sconce: an oval back plate, `arms` scrolled arms with candle cups, a small parchment shade on each.
    Returns its bulbs."""
    n = Vector(n).normalized(); side = Vector((-n.y, n.x, 0)); up = Vector((0, 0, 1)); bulbs = []
    pl = lathe(f'{name}_plate', [(0.0, 0.0), (0.05, 0.0), (0.05, 0.012), (0.0, 0.02)], M['brass'], loc=(0, 0, 0), seg=16, collection=col, lm='furn')
    pl.scale = (1.0, 1.6, 1.0); pl.rotation_euler = n.to_track_quat('Z', 'Y').to_euler(); pl.location = p
    ds = [0.0] if arms == 1 else [-1.0, 0.0, 1.0] if arms == 3 else [-1.0, 1.0]
    for k, s in enumerate(ds):
        a = p + n * 0.2 + side * s * 0.17 + up * (0.08 if s == 0 and arms == 3 else 0.02)
        tube(f'{name}_arm{k}', [p + n * 0.02 - up * 0.06, p + n * 0.1 + side * s * 0.06 - up * 0.1, a - up * 0.08, a - up * 0.02], 0.009, M['brass'], col, seg=6, lm='furn')
        cyl(f'{name}_cup{k}', 0.024, 0.025, a, M['brass'], seg=12, collection=col, live=1)
        cyl(f'{name}_candle{k}', 0.012, 0.07, a + up * 0.045, M['wax'], seg=8, collection=col, live=1)
        cyl(f'{name}_shade{k}', 0.075, 0.11, a + up * 0.12, M['shade'], r2=0.045, seg=20, collection=col, live=1)
        bulbs.append(a + up * 0.1)
    return bulbs


def spray(name, p, w, n, M, col, rnd, h=0.6):
    """An autumn spray: leafy stems fanning out of a low vessel (a mantel arrangement, an urn's), rust and dark
    leaves, a few red berries."""
    n = Vector(n).normalized(); side = Vector((-n.y, n.x, 0)); up = Vector((0, 0, 1))
    cyl(f'{name}_vessel', 0.12, 0.1, p + n * 0.02 + up * 0.05, M['brass'], r2=0.09, seg=16, collection=col, lm='furn')
    bm = bmesh.new(); bmb = bmesh.new()
    for i in range(46):
        a = rnd.uniform(-1.0, 1.0); L = h * rnd.uniform(0.55, 1.0) * (1 - 0.35 * abs(a))
        d = (side * a * (w / h) * 0.55 + up * (1 - 0.5 * a * a) + n * rnd.uniform(-0.1, 0.35)).normalized()
        base = p + up * 0.09 + n * 0.03
        for j in range(5):
            c = base + d * L * (0.35 + 0.65 * j / 4) + Vector((rnd.uniform(-0.03, 0.03), rnd.uniform(-0.03, 0.03), rnd.uniform(-0.03, 0.03)))
            s = rnd.uniform(0.035, 0.06); q = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))).normalized()
            u = q.cross(up).normalized() if abs(q.z) < 0.9 else side; v = q.cross(u).normalized()
            vs = [bm.verts.new(c + u * s), bm.verts.new(c + v * s * 0.5), bm.verts.new(c - u * s), bm.verts.new(c - v * s * 0.5)]
            f = bm.faces.new(vs); f.material_index = 0 if rnd.random() < 0.6 else 1
        if rnd.random() < 0.25:
            bmesh.ops.create_icosphere(bmb, subdivisions=1, radius=0.018, matrix=Matrix.Translation(base + d * L))
    ob = cine._mesh_obj(f'{name}_leaves', bm, M['leaf'], col, smooth=False); ob.data.materials.append(M['leaf2']); ob['lm'] = 'furn'
    ob2 = cine._mesh_obj(f'{name}_berries', bmb, M['berry'], col, smooth=True); ob2['lm'] = 'furn'


# ---------------------------------------------------------------- windows, drapes, doors
def windows(M, col):
    """The French windows in the back wall: white-painted frames and glazing bars round the night, casings; the
    champagne silk drapes swagged over each and falling to the floor either side."""
    for k, c in enumerate(WIN_X):
        x0, x1 = c - WW / 2, c + WW / 2; y = BACK
        g = box(f'win_glass{k}', (WW, 0.02, WIN_TOP), (c, y + 0.06, WIN_TOP / 2), M['night'], bev=0, collection=col, lm='furn')
        for s in (-1, 1):
            box(f'win_stile{k}{s}', (0.07, 0.07, WIN_TOP), (c + s * (WW / 2 - 0.035), y + 0.02, WIN_TOP / 2), M['white_paint'], bev=0.004, collection=col, lm='furn')
        box(f'win_meet{k}', (0.08, 0.07, WIN_TOP), (c, y + 0.02, WIN_TOP / 2), M['white_paint'], bev=0.004, collection=col, lm='furn')
        box(f'win_head{k}', (WW, 0.07, 0.08), (c, y + 0.02, WIN_TOP - 0.04), M['white_paint'], bev=0.004, collection=col, lm='furn')
        box(f'win_rail{k}', (WW, 0.07, 0.18), (c, y + 0.02, 0.09), M['white_paint'], bev=0.004, collection=col, lm='furn')
        for leaf in (-1, 1):                                                   # the glazing bars: two columns of panes a leaf
            lx0, lx1 = (x0 + 0.07, c - 0.04) if leaf < 0 else (c + 0.04, x1 - 0.07)
            for xx in (lx0 + (lx1 - lx0) / 2,):
                box(f'win_mull{k}{leaf}', (0.025, 0.04, WIN_TOP - 0.26), (xx, y + 0.03, 0.18 + (WIN_TOP - 0.26) / 2), M['white_paint'], bev=0.002, collection=col, lm='furn')
            for j in range(1, 6):
                zz = 0.18 + j * (WIN_TOP - 0.26) / 6
                box(f'win_bar{k}{leaf}{j}', (lx1 - lx0, 0.04, 0.025), ((lx0 + lx1) / 2, y + 0.03, zz), M['white_paint'], bev=0.002, collection=col, lm='furn')
        # the casing: a broad moulded architrave
        bw = Face((LEFT, BACK), (RIGHT, BACK), (0, -1))
        u0, u1 = x0 - LEFT, x1 - LEFT
        for j, u in enumerate((u0 - 0.16, u1)):
            bw.slab(f'win_casing{k}{j}', u, u + 0.16, 0.0, WIN_TOP + 0.16, 0.0, 0.04, M['wall'], col, bev=0.008, lm='arch')
        bw.slab(f'win_casing_head{k}', u0 - 0.16, u1 + 0.16, WIN_TOP, WIN_TOP + 0.16, 0.0, 0.04, M['wall'], col, bev=0.008, lm='arch')
        bw.slab(f'win_casing_crown{k}', u0 - 0.2, u1 + 0.2, WIN_TOP + 0.16, WIN_TOP + 0.24, 0.0, 0.07, M['wall'], col, bev=0.012, lm='arch')
        # drapes: a panel either side, gathered back; the swag across the top
        for j, s in enumerate((-1, 1)):
            cloth_panel(f'drape{k}{j}', 0.62, WIN_TOP + 0.5, 9, 0.05, M['drape'], loc=(c + s * (WW / 2 + 0.12), y - 0.16, WIN_TOP + 0.5), gather=0.75, hem=0.0, seed=k * 7 + j,
                        res=(28, 40), collection=col, lm='furn')
            tube(f'drape_tie{k}{j}', circle((c + s * (WW / 2 + 0.1), y - 0.16, 1.1), 0.16, (1, 0, 0), (0, 1, 0), n=16), 0.02, M['drape'], col, closed=True, seg=6, lm='furn')
        sw = cloth_panel(f'swag{k}', WW + 0.7, 0.55, 5, 0.06, M['drape'], loc=(c, y - 0.2, WIN_TOP + 0.62), gather=1.0, seed=31 + k, res=(36, 10), collection=col, lm='furn')
        for v in sw.data.vertices:                                             # the swag's hem droops in the middle
            t = (v.co.x / (WW + 0.7) + 0.5); v.co.z -= 0.22 * math.sin(math.pi * t) * (-v.co.z / 0.55)


def door(name, yc, M, col):
    """A pair of panelled walnut doors on the end wall, closed, in a broad cream architrave with a cornice over it."""
    lf = Face((LEFT, FRONT), (LEFT, BACK), (1, 0)); u0, u1 = yc - DOOR_W / 2 - FRONT, yc + DOOR_W / 2 - FRONT
    for k, s in enumerate((-1, 1)):
        a, b = (u0, (u0 + u1) / 2) if s < 0 else ((u0 + u1) / 2, u1)
        lf.slab(f'{name}_leaf{k}', a, b, 0.0, DOOR_H, -0.02, 0.06, M['walnut'], col, bev=0.006, lm='furn')
        for j, (z0, z1) in enumerate(((0.15, 0.95), (1.1, 2.2), (2.35, DOOR_H - 0.15))):
            lf.slab(f'{name}_panel{k}{j}', a + 0.11, b - 0.11, z0, z1, 0.04, 0.025, M['walnut'], col, bev=0.016, lm='furn')
        lf.slab(f'{name}_handle{k}', (b - 0.1) if s < 0 else (a + 0.06), (b - 0.06) if s < 0 else (a + 0.1), 1.02, 1.2, 0.04, 0.03, M['brass'], col, bev=0.006, lm='furn')
    for j, u in enumerate((u0 - 0.16, u1)):
        lf.slab(f'{name}_casing{j}', u, u + 0.16, 0.0, DOOR_H + 0.16, 0.0, 0.045, M['wall'], col, bev=0.008, lm='arch')
    lf.slab(f'{name}_casing_head', u0 - 0.16, u1 + 0.16, DOOR_H, DOOR_H + 0.16, 0.0, 0.045, M['wall'], col, bev=0.008, lm='arch')
    lf.slab(f'{name}_frieze', u0 - 0.16, u1 + 0.16, DOOR_H + 0.16, DOOR_H + 0.42, 0.0, 0.03, M['wall'], col, bev=0.006, lm='arch')
    lf.slab(f'{name}_cornice', u0 - 0.24, u1 + 0.24, DOOR_H + 0.42, DOOR_H + 0.52, 0.0, 0.1, M['wall'], col, bev=0.02, lm='arch')
    frame_rect(lf, f'{name}_over', u0 + 0.1, u1 - 0.1, DOOR_H + 0.62, FRIEZE - 0.15, 0.0, col)


# ---------------------------------------------------------------- the trophies, the armour, the lamps
_MODELS = {}


def _model(key, path, prep):
    """Import a model once and prepare it (its materials, how dense); later calls copy it."""
    if key not in _MODELS:
        root, ms = cine.import_gltf(path, collection=None)
        for o in ms:
            for c in list(o.users_collection): c.objects.unlink(o)
        prep(ms); _MODELS[key] = ms
    out = []
    for o in _MODELS[key]:
        c = o.copy(); c.data = o.data.copy(); out.append(c)
    return out


def _flatten(ms):
    bpy.context.view_layer.update()
    for o in ms:
        mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    return ms


def _thin(ms, ratio):
    for o in ms:
        md = o.modifiers.new('thin', 'DECIMATE'); md.ratio = ratio; md.use_collapse_triangulate = True


def _antler_mat(name, img_mat, tint, rough=0.55):
    """A scan's own colour map, desaturated toward `tint` (antler, bone): the scans came with odd casts."""
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); nt = m.node_tree; p = nt.nodes['Principled BSDF']
    src = next((n.image for n in img_mat.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image), None) if img_mat and img_mat.node_tree else None
    if src:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = src
        hsv = nt.nodes.new('ShaderNodeHueSaturation'); hsv.inputs['Saturation'].default_value = 0.0
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 1.0
        nt.links.new(t.outputs['Color'], hsv.inputs['Color']); nt.links.new(hsv.outputs['Color'], mix.inputs['A'])
        mix.inputs['B'].default_value = (*tint, 1.0); nt.links.new(mix.outputs['Result'], p.inputs['Base Color'])
    else:
        p.inputs['Base Color'].default_value = (*tint, 1.0)
    p.inputs['Roughness'].default_value = rough
    return m


def _place_model(ms, at, size, axis, facing, col, ground=False):
    """Copies of a prepared model, sized and set at `at`, turned so its own -y faces `facing` (the wall's normal). A
    scan's thousands of ragged islands would starve the light-map atlas: these are lit live, like the people (`live`)."""
    for o in ms:
        for c in list(o.users_collection): c.objects.unlink(o)
        col.objects.link(o); o['live'] = 1
    bpy.context.view_layer.update()
    R = Matrix.Rotation(math.atan2(facing[1], facing[0]) + math.pi / 2, 4, 'Z')
    for o in ms: o.matrix_world = R @ o.matrix_world
    _fit(ms, at, size, axis, ground=ground)
    return ms


def _weld(ms):
    """glTF import splits a scan's vertices at its UV seams: weld them first (the UVs live on the loops and stay), or
    thinning tears it apart."""
    for o in ms:
        bm = bmesh.new(); bm.from_mesh(o.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4 * max(o.dimensions)); bm.to_mesh(o.data); bm.free()


def _prep_skull(ms):
    """A stag's skull and antlers (RISD Nature Lab's scan of a white-tailed deer, facing the room as it comes): welded,
    thinned; each piece keeps its own photographs, a touch warmer."""
    _flatten(ms); _weld(ms); _thin(ms, 0.01)
    for o in ms:
        for sl in o.material_slots: sl.material = _antler_mat(f'stag_skull_{sl.material.name}', sl.material, (1.0, 0.9, 0.78))


def _prep_frontlet(ms):
    """A roe deer's frontlet on its little shield (c.turansky's scan), thinned hard: it hangs in rings of eight."""
    _flatten(ms); _thin(ms, 0.004)
    for o in ms:
        for sl in o.material_slots: sl.material = _antler_mat(f'roe_frontlet_{sl.material.name}', sl.material, (0.86, 0.72, 0.56))
        o.matrix_world = Matrix.Rotation(math.radians(52), 4, 'X') @ o.matrix_world      # the scan lies tilted back: its plaque made upright
    bpy.context.view_layer.update()
    P = [o.matrix_world @ v.co for o in ms for v in o.data.vertices]
    lo = Vector([min(p[i] for p in P) for i in range(3)]); hi = Vector([max(p[i] for p in P) for i in range(3)])
    cine.log('frontlet bounds', tuple(round(v, 1) for v in hi - lo))


def cluster(name, x, zc, size, M, col, rnd):
    """A cluster of trophies in a wall panel: a stag's skull and antlers on a carved dark shield in the middle, roe frontlets on
    little black shields round it, two below. Returns nothing."""
    y = BACK; c = Vector((x, y - 0.02, zc))
    sh = rounded_slab(f'{name}_shield', 0.62 * size, 0.95 * size, 0.06, 0.28 * size, (0, 0, 0), M['dark_wood'], edge_bev=0.02, collection=col, lm='furn')
    sh.rotation_euler.x = math.pi / 2; sh.location = c + Vector((0, -0.03, -0.05 * size))
    _place_model(_model('skull', OBJ('deer_skull_risd.glb'), _prep_skull), c + Vector((0, -0.2 * size, 0.22 * size)), 1.35 * size, 'z', (0, -1), col)
    ring = [(math.cos(a), math.sin(a)) for a in (math.radians(d) for d in (0, 40, 140, 180, 220, 320))]
    for k, (ca, sa) in enumerate(ring + [(-0.35, -1.25), (0.35, -1.25)]):
        p = c + Vector((ca * 0.95 * size, 0.0, sa * 0.78 * size + 0.05 * size))
        _place_model(_model('frontlet', OBJ('mounted_antlers_turansky.glb'), _prep_frontlet), p + Vector((0, -0.1 * size, 0.06 * size)), 0.42 * size * rnd.uniform(0.9, 1.1), 'z', (0, -1), col)


def armour(name, p, facing, M, col):
    """A suit of plate on a low walnut stand, the steel blackened, its arming cloth dark."""
    def prep(ms):
        keep = [o for o in ms if 'Clean' in o.name]
        for o in ms:
            if o not in keep: bpy.data.objects.remove(o, do_unlink=True)
        ms[:] = keep; _flatten(ms); _thin(ms, 0.1)
        for o in ms:
            for sl in o.material_slots: sl.material = M['steel'] if 'Metal' in o.name else M['cloth_dark']
    ms = _model('armour', OBJ('knight_armour_soidev.glb'), prep)
    box(f'{name}_stand', (0.62, 0.62, 0.1), (p[0], p[1], 0.05), M['walnut'], bev=0.012, collection=col, lm='furn')
    _place_model(ms, (p[0], p[1], 0.1), 1.86, 'z', facing, col, ground=True)


def lamp_green(name, p, M, col):
    """The lamp by the fireplace: a dark green conical shade on a tall carved walnut stand (a lion on the set).
    Returns its bulb."""
    p = Vector(p)
    lathe(f'{name}_stand', [(0.0, 0.0), (0.2, 0.0), (0.2, 0.06), (0.14, 0.12), (0.1, 0.5), (0.13, 0.62), (0.08, 0.9), (0.11, 1.0), (0.0, 1.02)], M['walnut'], loc=p, seg=20, collection=col, lm='furn')
    lathe(f'{name}_lamp', [(0.0, 0.0), (0.09, 0.0), (0.1, 0.05), (0.04, 0.12), (0.03, 0.4), (0.0, 0.42)], M['brass'], loc=p + Vector((0, 0, 1.02)), seg=16, collection=col, lm='furn')
    cyl(f'{name}_shade', 0.3, 0.32, p + Vector((0, 0, 1.58)), M['green_shade'], r2=0.14, seg=32, collection=col, live=1)
    return p + Vector((0, 0, 1.44))


def candelabrum(name, p, M, col, rnd, h=1.62):
    """A tall black iron candelabrum on three scrolled feet, three candles; lit live (its arms are in its flames' glare).
    Returns its flames."""
    p = Vector(p); flames = []
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.4; d = Vector((math.cos(a), math.sin(a), 0))
        tube(f'{name}_foot{k}', [p + d * 0.02 + Vector((0, 0, 0.3)), p + d * 0.16 + Vector((0, 0, 0.12)), p + d * 0.26 + Vector((0, 0, 0.02)), p + d * 0.3 + Vector((0, 0, 0.06))], 0.016, M['iron'], col, seg=8, live=1)
    lathe(f'{name}_shaft', [(0.0, 0.26), (0.035, 0.26), (0.05, 0.33), (0.022, 0.42), (0.02, h - 0.3), (0.045, h - 0.24), (0.02, h - 0.2), (0.0, h - 0.19)], M['iron'], loc=p, seg=12, collection=col, live=1)
    for k, s in enumerate((-1, 0, 1)):
        q = p + Vector((s * 0.2, 0, h - 0.08 + (0.1 if s == 0 else 0)))
        if s: tube(f'{name}_arm{k}', [p + Vector((0, 0, h - 0.24)), p + Vector((s * 0.12, 0, h - 0.26)), q], 0.012, M['iron'], col, seg=6, live=1)
        flames.append(_candle(f'{name}_c{k}', q, M, col, rnd, r=0.028, hmin=0.18, hmax=0.26))
    return flames


def _candle(name, q, M, col, rnd, r=0.035, hmin=0.12, hmax=0.3):
    """A candle in an iron cup; wax and cup are lit live (their flame is a finger away). Returns the flame's place."""
    cyl(f'{name}_cup', r + 0.012, 0.03, q + Vector((0, 0, 0.015)), M['iron'], seg=12, collection=col, live=1)
    h = rnd.uniform(hmin, hmax)
    cyl(f'{name}_wax', r, h, q + Vector((0, 0, 0.03 + h / 2)), M['wax'], seg=14, collection=col, live=1)
    f = q + Vector((0, 0, 0.03 + h + 0.024))
    lathe(f'{name}_flame', [(0.0, -0.013), (0.009, -0.004), (0.01, 0.007), (0.006, 0.02), (0.0, 0.034)], M['flame'], loc=f, seg=8, collection=col)
    return f + Vector((0, 0, 0.006))


def wall_things(M, col, rnd):
    """The trophies, the armour, the lamp, the sconces on the window wall, a candelabrum under each cluster, a dark
    console under the big one. Returns (sconce bulbs, candle flames, the lamp's bulb)."""
    for k, (x, zc, s) in enumerate(CLUSTERS): cluster(f'cluster{k}', x, zc, s, M, col, rnd)
    # single frontlets: the corner panel of the window wall, the end wall's panels between the doors and the breast
    for k, (p, n) in enumerate((((-6.75, BACK, 3.3), (0, -1)), ((LEFT, -1.57, 3.5), (1, 0)), ((LEFT, 2.4, 3.6), (1, 0)))):
        p = Vector(p) + Vector((n[0], n[1], 0)) * 0.13
        _place_model(_model('frontlet', OBJ('mounted_antlers_turansky.glb'), _prep_frontlet), p, 0.52, 'z', n, col)
    for k, p in enumerate(ARMOUR): armour(f'armour{k}', p, (1, 0), M, col)
    lamp = lamp_green('lamp_green', (LEFT + 0.42, YF - 1.78, 0.0), M, col)
    bulbs = []
    for k, x in enumerate((-2.42, 0.42, 4.2, 6.66)):
        bulbs += sconce(f'wall_sconce{k}', Vector((x, BACK - PIL_O * 0, 2.75)), Vector((0, -1, 0)), M, col, arms=3)
    flames = []
    for k, (x, zc, s) in enumerate(CLUSTERS):
        flames += candelabrum(f'stand_candles{k}', (x, BACK - 0.95, 0.0), M, col, rnd)
    r, cm = cine.import_gltf(PH('ClassicConsole_01'), loc=(0, 0, 0), rot=(0, 0, math.pi), scale=1.0, collection=col, lm='furn')
    _fit(cm, (CLUSTERS[0][0], BACK - 0.28, 0.0), 1.7, 'x', ground=True, ratio=0.5)
    bpy.context.view_layer.update()
    top = max((o.matrix_world @ Vector(cn)).z for o in cm for cn in o.bound_box)
    spray('console_spray', Vector((CLUSTERS[0][0] - 0.55, BACK - 0.3, top)), 0.5, Vector((0, -1, 0)), M, col, rnd, h=0.5)
    for k, dx in enumerate((0.3, 0.55)):
        lathe(f'console_decanter{k}', [(0.0, 0.0), (0.06, 0.0), (0.075, 0.06), (0.07, 0.14), (0.03, 0.2), (0.02, 0.26), (0.026, 0.27), (0.0, 0.27)], M['glass'], loc=(CLUSTERS[0][0] + dx, BACK - 0.3, top), seg=16, collection=col, role='glass')
    return bulbs, flames, lamp


# ---------------------------------------------------------------- the table and the chairs
def _frame(p, f):
    f = Vector((f[0], f[1], 0)).normalized()
    return Matrix.Translation(Vector((p[0], p[1], 0))) @ Matrix.Rotation(math.atan2(f.y, f.x) + math.pi / 2, 4, 'Z')


def dining_chair(name, p, f, M, col, turn=0.0):
    """A high-backed armchair in cognac leather on carved walnut: the back's crest swept up to a shallow arch, brass
    nails along its edges, padded arms on scrolled supports, cabriole front legs. Faces `f` (local -y is its front)."""
    parts = []; add = lambda o: (parts.append(o), o)[1]; st = SEAT_Z; L = M['leather']
    add(rounded_slab(f'{name}_seat', 0.56, 0.52, 0.1, 0.05, (0, -0.02, st - 0.05), L, edge_bev=0.03, collection=col, lm='furn'))
    add(box(f'{name}_rail', (0.6, 0.56, 0.09), (0, 0.0, st - 0.145), M['walnut'], bev=0.01, collection=col, lm='furn'))
    outline = cine.outline([(-0.28, 0.0), (0.28, 0.0), (0.29, 0.5), (0.24, 0.66), (0.0, 0.72), (-0.24, 0.66), (-0.29, 0.5)], n=8)
    bk = add(slab_profile(f'{name}_back', outline, 'y', 0.09, [L, L], col, bev=0.03, lm='furn'))
    bk.location = (0, 0.25, st + 0.06); bk.rotation_euler.x = math.radians(-8)
    nails = bmesh.new()
    for k in range(len(outline)):
        if k % 2: continue
        x, z = outline[k]
        bmesh.ops.create_icosphere(nails, subdivisions=1, radius=0.008, matrix=Matrix.Translation(Vector((x * 0.97, -0.047, z * 0.985))))
    nb = cine._mesh_obj(f'{name}_nails', nails, M['brass'], col, smooth=True); nb['lm'] = 'furn'
    nb.location = bk.location; nb.rotation_euler = bk.rotation_euler; add(nb)
    for s in (-1, 1):
        add(rounded_slab(f'{name}_armpad{s}', 0.08, 0.42, 0.05, 0.025, (s * 0.31, 0.0, st + 0.21), L, edge_bev=0.015, collection=col, lm='furn'))
        add(tube(f'{name}_armpost{s}', [(s * 0.31, -0.2, st - 0.1), (s * 0.32, -0.22, st + 0.06), (s * 0.31, -0.19, st + 0.19)], 0.022, M['walnut'], col, seg=8, lm='furn'))
        add(tube(f'{name}_legf{s}', [(s * 0.26, -0.22, st - 0.19), (s * 0.28, -0.25, 0.25), (s * 0.25, -0.24, 0.07), (s * 0.27, -0.27, 0.0)], 0.024, M['walnut'], col, seg=8, lm='furn'))
        add(lathe(f'{name}_legb{s}', [(0.0, 0.0), (0.02, 0.0), (0.024, st - 0.19), (0.0, st - 0.19)], M['walnut'], loc=(s * 0.25, 0.23, 0.0), seg=8, collection=col, lm='furn'))
    M_ = _frame(p, f) @ Matrix.Rotation(math.radians(turn), 4, 'Z')
    for o in parts: place(o, M_)
    return parts


def table(M, col, rnd):
    """The long walnut table: a thick top on six heavy turned legs and an apron, the brocade runner down it. Returns
    the top's height."""
    cx, L = (TX0 + TX1) / 2, TX1 - TX0
    box('table_top', (L, TW, 0.06), (cx, YT, TH - 0.03), M['walnut'], bev=0.012, collection=col, lm='furn')
    box('table_apron', (L - 0.2, TW - 0.2, 0.12), (cx, YT, TH - 0.12), M['walnut'], bev=0.006, collection=col, lm='furn')
    for k, x in enumerate((TX0 + 0.25, cx, TX1 - 0.25)):
        for s in (-1, 1):
            lathe(f'table_leg{k}{s}', [(0.0, 0.0), (0.06, 0.0), (0.07, 0.05), (0.05, 0.1), (0.09, 0.28), (0.07, 0.4), (0.05, 0.5), (0.055, TH - 0.18), (0.0, TH - 0.18)],
                  M['walnut'], loc=(x, YT + s * (TW / 2 - 0.16), 0.0), seg=16, collection=col, lm='furn')
    r = box('table_runner', (L + 0.5, 0.5, 0.004), (cx, YT, TH + 0.002), M['runner'], bev=0, collection=col, lm='furn')
    for s in (-1, 1): box(f'table_runner_end{s}', (0.004, 0.5, 0.25), (cx + s * (L / 2 + 0.25), YT, TH - 0.125), M['runner'], bev=0, collection=col, lm='furn')
    return TH


def place_setting(name, p, f, M, col, rnd, eaten=0.5, empty=False):
    """A place: the gold-rimmed plate with what is left of dinner, knife and fork, a wine glass (wine in it) and a
    water tumbler, a napkin. `p` is the plate's centre on the table, `f` the diner's facing."""
    f = Vector((f[0], f[1], 0)).normalized(); s = Vector((-f.y, f.x, 0)); z = TH
    q = Vector((p[0], p[1], z))
    lathe(f'{name}_plate', [(0.0, 0.0), (0.09, 0.0), (0.1, 0.008), (0.13, 0.016), (0.14, 0.022), (0.0, 0.012)], M['china'], loc=q, seg=28, collection=col, lm='furn')
    tube(f'{name}_rim', circle(q + Vector((0, 0, 0.021)), 0.131, (1, 0, 0), (0, 1, 0), n=28), 0.003, M['gilt'], col, closed=True, seg=4, lm='furn')
    if not empty:
        for j in range(3):
            m = (M['food_brown'], M['food_pale'], M['food_green'])[j]
            if rnd.random() > eaten + 0.3:
                c = q + s * rnd.uniform(-0.05, 0.05) + f * rnd.uniform(-0.05, 0.04) + Vector((0, 0, 0.026))
                bmb = bmesh.new(); bmesh.ops.create_icosphere(bmb, subdivisions=2, radius=0.032, matrix=Matrix.Translation(c) @ Matrix.Diagonal((1.0, 0.8, 0.45, 1)))
                o = cine._mesh_obj(f'{name}_food{j}', bmb, m, col, smooth=True); o['lm'] = 'furn'
    for k, sd in enumerate((-1, 1)):
        box(f'{name}_cutlery{k}', (0.018, 0.2, 0.006), q + s * sd * 0.19 + Vector((0, 0, 0.003)), M['silver'], rot=(0, 0, math.atan2(f.y, f.x) + math.pi / 2), bev=0.002, collection=col, lm='furn')
    g = q + s * 0.17 + f * 0.2
    lathe(f'{name}_wineglass', [(0.0, 0.0), (0.035, 0.0), (0.035, 0.004), (0.005, 0.012), (0.005, 0.08), (0.032, 0.1), (0.042, 0.15), (0.038, 0.2), (0.0, 0.19)], M['glass'], loc=g, seg=14, collection=col, role='glass')
    if not empty and rnd.random() < 0.8:
        lathe(f'{name}_wine', [(0.0, 0.0), (0.03, 0.0), (0.038, 0.03), (0.0, 0.03)], M['wine'], loc=g + Vector((0, 0, 0.1)), seg=14, collection=col, lm='furn')
    t = q - s * 0.05 + f * 0.24
    lathe(f'{name}_tumbler', [(0.0, 0.0), (0.033, 0.0), (0.036, 0.1), (0.0, 0.1)], M['glass'], loc=t, seg=14, collection=col, role='glass')
    if rnd.random() < 0.7:
        box(f'{name}_napkin', (0.14, 0.18, 0.025), q - s * 0.24 - f * 0.02 + Vector((0, 0, 0.012)), M['napkin'], rot=(0, 0, rnd.uniform(-0.3, 0.3)), bev=0.01, collection=col, lm='furn')


def table_things(M, col, rnd):
    """Down the table's middle: pillar candles in black iron, two brass three-light candelabra, pewter jugs, cut crystal
    water jugs, footed silver bowls of apples and grapes, bread. Returns the candles' flames."""
    flames = []
    xs = [TX0 + 0.3 + i * (TX1 - TX0 - 0.6) / 9 for i in range(10)]
    for k, x in enumerate(xs):
        y = YT + (0.08 if k % 2 else -0.08); q = Vector((x, y, TH))
        if k in (2, 7):
            ms = _model('candelabra', OBJ('candelabra_andreivnk.glb'), lambda ms: (_flatten(ms), [setattr(sl, 'material', M['iron']) for o in ms for sl in o.material_slots if 'Candle' not in o.name]))
            _place_model(ms, q, 0.5, 'z', (0, -1), col, ground=True)
            bpy.context.view_layer.update()
            for j, o in enumerate(o for o in ms if 'Candle' in o.name):
                P = [o.matrix_world @ Vector(cn) for cn in o.bound_box]
                f = Vector((sum(p.x for p in P) / 8, sum(p.y for p in P) / 8, max(p.z for p in P) + 0.02))
                lathe(f'candelabra_flame{k}{j}', [(0.0, -0.013), (0.009, -0.004), (0.01, 0.007), (0.006, 0.02), (0.0, 0.034)], M['flame'], loc=f, seg=8, collection=col)
                flames.append(f + Vector((0, 0, 0.01)))
            continue
        lathe(f'pillar_holder{k}', [(0.0, 0.0), (0.07, 0.0), (0.075, 0.015), (0.03, 0.04), (0.025, 0.09), (0.06, 0.11), (0.06, 0.125), (0.0, 0.125)], M['iron'], loc=q, seg=16, collection=col, lm='furn')
        h = rnd.uniform(0.12, 0.26); r = 0.04
        cyl(f'pillar{k}', r, h, q + Vector((0, 0, 0.125 + h / 2)), M['wax'], seg=16, collection=col, live=1)
        f = q + Vector((0, 0, 0.125 + h + 0.022))
        lathe(f'pillar_flame{k}', [(0.0, -0.013), (0.009, -0.004), (0.011, 0.008), (0.007, 0.022), (0.0, 0.036)], M['flame'], loc=f, seg=8, collection=col)
        flames.append(f + Vector((0, 0, 0.008)))
    for k, x in enumerate((TX0 + 1.1, TX1 - 1.4)):                              # fruit
        q = Vector((x, YT - 0.02, TH))
        lathe(f'fruit_bowl{k}', [(0.0, 0.0), (0.07, 0.0), (0.07, 0.01), (0.02, 0.03), (0.02, 0.09), (0.16, 0.13), (0.19, 0.17), (0.0, 0.12)], M['silver'], loc=q, seg=24, collection=col, lm='furn')
        for j in range(5):
            a = 2 * math.pi * j / 5 + k; c = q + Vector((0.085 * math.cos(a), 0.085 * math.sin(a), 0.19))
            bmb = bmesh.new(); bmesh.ops.create_icosphere(bmb, subdivisions=2, radius=0.042, matrix=Matrix.Translation(c))
            o = cine._mesh_obj(f'apple{k}{j}', bmb, material('apple_red', (0.42, 0.04, 0.03), rough=0.3, coat=0.5), col, smooth=True); o['lm'] = 'furn'
        bmg = bmesh.new()
        for j in range(26):
            c = q + Vector((rnd.uniform(-0.08, 0.1), rnd.uniform(-0.06, 0.06), 0.2 + rnd.uniform(0, 0.09)))
            bmesh.ops.create_icosphere(bmg, subdivisions=1, radius=0.016, matrix=Matrix.Translation(c))
        o = cine._mesh_obj(f'grapes{k}', bmg, M['green_grape'] if k else M['grape'], col, smooth=True); o['lm'] = 'furn'
    for k, (x, sd) in enumerate(((TX0 + 0.7, 1), (TX0 + 2.6, -1), (TX1 - 0.6, 1))):   # jugs
        q = Vector((x, YT + sd * 0.2, TH))
        lathe(f'pewter_jug{k}', [(0.0, 0.0), (0.06, 0.0), (0.07, 0.04), (0.065, 0.14), (0.045, 0.2), (0.05, 0.24), (0.0, 0.24)], M['pewter'], loc=q, seg=18, collection=col, lm='furn')
        tube(f'pewter_jug_handle{k}', [q + Vector((-0.06, 0, 0.18)), q + Vector((-0.11, 0, 0.16)), q + Vector((-0.1, 0, 0.07)), q + Vector((-0.065, 0, 0.05))], 0.008, M['pewter'], col, seg=6, lm='furn')
    for k, x in enumerate((TX0 + 1.75, TX1 - 2.2)):
        q = Vector((x, YT - 0.18, TH))
        lathe(f'crystal_jug{k}', [(0.0, 0.0), (0.07, 0.0), (0.08, 0.05), (0.075, 0.18), (0.055, 0.24), (0.06, 0.27), (0.0, 0.26)], M['glass'], loc=q, seg=18, collection=col, role='glass')
        lathe(f'crystal_jug_water{k}', [(0.0, 0.0), (0.068, 0.0), (0.076, 0.05), (0.072, 0.16), (0.0, 0.16)], M['water'], loc=q + Vector((0, 0, 0.005)), seg=18, collection=col, lm='furn')
    for k, x in enumerate((TX0 + 1.4, TX1 - 1.0)):
        q = Vector((x, YT + 0.22, TH))
        cyl(f'bread_board{k}', 0.13, 0.02, q + Vector((0, 0, 0.01)), M['walnut'], seg=20, collection=col, lm='furn')
        bmb = bmesh.new(); bmesh.ops.create_icosphere(bmb, subdivisions=2, radius=0.08, matrix=Matrix.Translation(q + Vector((0, 0, 0.05))) @ Matrix.Diagonal((1.4, 0.9, 0.55, 1)))
        o = cine._mesh_obj(f'loaf{k}', bmb, M['bread'], col, smooth=True); o['lm'] = 'furn'
    return flames


def chairs_and_places(M, col, rnd):
    """Sixteen chairs: the head (Logan's), seven a side, the foot; a place laid at each but the foot. The boars' three
    chairs on the near side stand pushed back askew; plates left half eaten."""
    hp, hf = head_seat()
    dining_chair('chair_head', hp, hf, M, col)
    place_setting('place_head', (TX0 + 0.22, YT), hf, M, col, rnd)
    for side in (1, -1):
        for k in range(len(SEATS_X)):
            p, f = seat(side, k)
            push, turn = PULLED.get((side, k), (0.0, 0.0))
            dining_chair(f'chair_{"far" if side > 0 else "near"}{k}', p - f * push, f, M, col, turn=turn)
            place_setting(f'place_{side}_{k}', (SEATS_X[k], YT + side * (TW / 2 - 0.2)), f, M, col, rnd, eaten=rnd.uniform(0.2, 0.8))
    dining_chair('chair_foot', Vector((*FOOT, 0)), Vector((-1, 0, 0)), M, col)


def rug(M, col):
    r = box('rug', (8.6, 4.6, 0.012), ((TX0 + TX1) / 2, YT, 0.006), M['rug'], bev=0.003, collection=col, lm='arch')
    uv_rect(r, 'z')
    return r


def near_things(M, col, rnd):
    """By the near wall (beyond the front cut): the buffet, its platters and cheeses and candles; the round bar table
    with its decanters and bottles. Returns the buffet's flames."""
    c = Vector((3.4, -5.0, 0.0)); flames = []
    box('buffet_top', (2.6, 0.72, 0.05), c + Vector((0, 0, 0.86)), M['walnut'], bev=0.01, collection=col, lm='furn')
    box('buffet_body', (2.5, 0.62, 0.62), c + Vector((0, 0, 0.53)), M['walnut'], bev=0.008, collection=col, lm='furn')
    for s in (-1, 1):
        for sy in (-1, 1): lathe(f'buffet_leg{s}{sy}', [(0.0, 0.0), (0.04, 0.0), (0.05, 0.1), (0.03, 0.22), (0.0, 0.22)], M['walnut'], loc=c + Vector((s * 1.18, sy * 0.27, 0.0)), seg=12, collection=col, lm='furn')
    top = 0.885
    for k, dx in enumerate((-0.85, 0.0, 0.85)):
        q = c + Vector((dx, 0.0, top))
        cyl(f'platter{k}', 0.24, 0.02, q + Vector((0, 0, 0.01)), M['silver'], seg=28, collection=col, lm='furn')
        if k == 1:
            for j in range(3):
                cyl(f'cheese{j}', 0.1 - 0.02 * j, 0.08, q + Vector((-0.06 + 0.07 * j, 0.03 * j, 0.06)), M['cheese'], seg=20, collection=col, lm='furn')
        else:
            bmb = bmesh.new()
            for j in range(9):
                bmesh.ops.create_icosphere(bmb, subdivisions=1, radius=0.035, matrix=Matrix.Translation(q + Vector((rnd.uniform(-0.15, 0.15), rnd.uniform(-0.12, 0.12), 0.05))) @ Matrix.Diagonal((1.6, 1, 0.7, 1)))
            o = cine._mesh_obj(f'platter_food{k}', bmb, M['food_brown'] if k == 0 else M['bread'], col, smooth=True); o['lm'] = 'furn'
    for k, dx in enumerate((-1.15, -0.4, 0.45, 1.15)):
        flames.append(_candle(f'buffet_candle{k}', c + Vector((dx, 0.2, top)), M, col, rnd, r=0.045, hmin=0.12, hmax=0.22))
    b = Vector((5.9, -3.6, 0.0))
    cyl('bar_top', 0.5, 0.04, b + Vector((0, 0, 0.78)), material('bar_marble', (0.18, 0.15, 0.13), rough=0.15, coat=0.8), seg=40, collection=col, lm='furn')
    lathe('bar_pedestal', [(0.0, 0.0), (0.35, 0.0), (0.35, 0.05), (0.12, 0.1), (0.07, 0.4), (0.1, 0.7), (0.3, 0.76), (0.0, 0.76)], M['walnut'], loc=b, seg=24, collection=col, lm='furn')
    r, wb = cine.import_gltf(PH('wine_bottles_01'), loc=(0, 0, 0), scale=1.0, collection=col, lm='furn')
    _fit(wb, b + Vector((0.12, 0.08, 0.8)), 0.36, 'z', ground=True, ratio=0.5)
    for o in wb:     # coloured glass drawn opaque: transmission vanishes inside the case
        for sl in o.material_slots:
            p = next((n for n in sl.material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if sl.material and sl.material.node_tree else None
            if p: p.inputs['Transmission Weight'].default_value = 0.0
    for k, (dx, dy) in enumerate(((-0.22, 0.05), (-0.1, -0.2), (0.25, -0.15))):
        lathe(f'bar_decanter{k}', [(0.0, 0.0), (0.07, 0.0), (0.085, 0.07), (0.08, 0.16), (0.03, 0.22), (0.022, 0.29), (0.03, 0.3), (0.0, 0.3)], M['glass'], loc=b + Vector((dx, dy, 0.8)), seg=16, collection=col, role='glass')
        lathe(f'bar_whisky{k}', [(0.0, 0.0), (0.066, 0.0), (0.08, 0.07), (0.077, 0.12), (0.0, 0.12)], material('whisky', (0.36, 0.16, 0.04), rough=0.08, coat=1.0), loc=b + Vector((dx, dy, 0.805)), seg=16, collection=col, lm='furn')
    return flames


def logan_plate(M, col):
    """The plate of sausages Logan carries to the hearth: drawn live (it travels in his hand), lit like the people."""
    q = Vector((PLATE[0], PLATE[1], TH)); parts = []
    parts.append(lathe('plate_logan_china', [(0.0, 0.0), (0.09, 0.0), (0.1, 0.008), (0.13, 0.016), (0.14, 0.022), (0.0, 0.012)], M['china'], loc=q, seg=28, collection=col))
    parts.append(tube('plate_logan_rim', circle(q + Vector((0, 0, 0.021)), 0.131, (1, 0, 0), (0, 1, 0), n=28), 0.003, M['gilt'], col, closed=True, seg=4))
    for k, (dx, dy, a) in enumerate(((-0.03, -0.03, 0.3), (0.0, 0.02, 0.5), (0.035, -0.01, 0.2), (0.01, 0.05, 0.7))):
        p = q + Vector((dx, dy, 0.032)); d = Vector((math.cos(a), math.sin(a), 0))
        parts.append(tube(f'plate_logan_sausage{k}', [p - d * 0.08, p - d * 0.02 + Vector((0.008, 0.008, 0)), p + d * 0.04, p + d * 0.09], 0.017, M['sausage'], col, seg=8))
    for o in parts: o['role'] = 'mug'; o['who'] = 'logan'
    return parts


def floor_things(M, col, rnd):
    """Before the hearth: the sausages Logan throws down, and one dropped half way."""
    for k, (x, y, a) in enumerate(((-6.05, YF + 0.2, 0.4), (-5.9, YF - 0.35, -0.9), (-5.7, YF + 0.75, 1.6), (-6.2, YF - 0.9, 2.2))):
        p = Vector((x, y, 0.022)); d = Vector((math.cos(a), math.sin(a), 0))
        tube(f'floor_sausage{k}', [p - d * 0.09, p - d * 0.03 + Vector((0.01, 0.01, 0)), p + d * 0.04, p + d * 0.1], 0.02, M['sausage'], col, seg=8, lm='furn')


# ---------------------------------------------------------------- the cut
def section(objs, M):
    """Every face the cut passes through, flat and dark (in the module, after `shrink`)."""
    for ob in objs:
        if not ob.name.startswith(('solid_', 'left_wall', 'back_wall', 'kerb')): continue
        me = ob.data
        if M['section'].name not in [m.name for m in me.materials if m]: me.materials.append(M['section'])
        k = [m.name if m else '' for m in me.materials].index(M['section'].name)
        for f in me.polygons:
            c = sum((me.vertices[i].co for i in f.vertices), Vector()) / len(f.vertices)
            if f.normal.z > 0.9 and abs(c.z - RH * SCALE) < 0.006: f.material_index = k


# ---------------------------------------------------------------- light
WARM = (1.0, 0.66, 0.36)                   # candle flames
FIRE = (1.0, 0.5, 0.2)
SHADE = (1.0, 0.72, 0.44)                  # bulbs under parchment


def lights(fire_pts, flames, sconce_bulbs, lamp_bulb):
    """Only what burns in the room: the fire (a glow filling the opening, the flames themselves), every candle, the
    sconces under their small shades, the green-shaded lamp. Returns the lights (true size: `shrink` brings them in)."""
    out = []
    def light(name, kind, loc, energy, colour, **kw):
        ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = colour
        for k, v in kw.items(): setattr(ld, k, v)
        ob = cine.link(bpy.data.objects.new(name, ld)); ob.location = loc; out.append(ob)
        if kind in ('AREA', 'SPOT', 'SUN'): ob.visible_camera = False; ob.visible_glossy = False
        return ob
    def aim(ob, d): ob.rotation_euler = Vector(d).to_track_quat('-Z', 'Y').to_euler()
    aim(light('fire_glow', 'AREA', (XB - 0.02, YF, OPEN_H * 0.45), 520.0, FIRE, shape='RECTANGLE', size=OPEN_W * 0.9, size_y=OPEN_H * 0.8), (1, 0, 0))
    for k, p in enumerate(fire_pts[::4]): light(f'fire{k}', 'POINT', p, 140.0, FIRE, shadow_soft_size=0.12)
    for k, f in enumerate(flames): light(f'candle{k}', 'POINT', f + Vector((0, 0, 0.03)), 6.0, WARM, shadow_soft_size=0.012)
    for k, b in enumerate(sconce_bulbs): light(f'sconce{k}', 'POINT', b, 9.0, SHADE, shadow_soft_size=0.03)
    light('lamp_green', 'POINT', lamp_bulb, 40.0, (1.0, 0.76, 0.46), shadow_soft_size=0.05)
    return out


def shrink(objs, lights_):
    """Bring the ballroom, built at its true size, into the module (as the throne room)."""
    S_ = Matrix.Scale(SCALE, 4)
    for o in objs: o.matrix_world = S_ @ o.matrix_world
    for l in lights_:
        l.location = l.location * SCALE
        d = l.data
        if d.type == 'AREA': d.size *= SCALE; d.size_y *= SCALE
        if d.type in ('POINT', 'SPOT', 'AREA'): d.energy *= SCALE ** 2; d.shadow_soft_size *= SCALE
    bpy.context.view_layer.update()
