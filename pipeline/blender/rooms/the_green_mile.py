# The Green Mile · E Block, Cold Mountain Penitentiary, 1935: death row, the morning John Coffey is brought in. A
# long brick hall painted cream, its floor of faded lime-green linoleum (the Mile), six cells along the back wall:
# brick piers, fronts of riveted strap iron with a door in each, strap-iron ceilings, a steel lintel and a concrete
# ledge over them carried on cast-iron brackets, a barred window high in the wall above each cell. At the left end
# the duty desk faces down the Mile (its green lamp, the candlestick telephone, the bell), the filing drawers, the
# radiator under the tall window, the notice board, the steel entry door with its grille and the W.C.; at the right
# end the restraint room's riveted door. Enamelled pendants in wire cages hang along the Mile; daylight comes in
# through the end window, the high windows and the roof lights.
#
# The block is built at its true size in a module 1 / SCALE times the size, then shrunk by SCALE (0.75) with the
# people (as the throne room, at 0.6). Behind the end wall a narrow passage, roofed, stands for the yard outside:
# the people who leave by the entry door wait there out of sight.
import math, os, random
import bpy, bmesh
from mathutils import Vector, Matrix
import cine
from cine import box, cyl, material, lathe, rounded_slab, moulding
from rooms.seinfeld import uv_rect, tube, circle

SCALE = 0.75
W, D, H = 9.6 / SCALE, 7.6 / SCALE, 3.0 / SCALE   # the module, at the block's true size
T = 0.14 / SCALE                                  # the module's walls
LEFT, BACK, RIGHT, FRONT = -W / 2 + T, D / 2 - T, W / 2 - T, -D / 2 + T
RH = 3.95                                         # the cut (true metres)
KH = 0.22 / SCALE                                 # the cut-away's kerb
TEX = os.path.join(cine.OUT, 'textures', 'the-green-mile')
tx = lambda n: os.path.join(TEX, n)

# the plan (true metres)
END_X = -4.75                                     # the Mile's end wall (its face); behind it the passage to the yard
END_T = 0.3
PASS_X = (LEFT, END_X - END_T)                    # the passage behind the end wall
PASS_Y = (-2.25, 1.3)                             # its roofed part (where the people wait)
PASS_ROOF = 2.5
ENTRY = (-1.05, -0.05)                            # the entry door (y), hinged at its +y jamb, opening into the passage
DOOR_H = 1.98                                     # low: Coffey ducks under it, as in the film
WC = (0.35, 1.05)                                 # the W.C. door (y)
WIN = (-3.5, -2.4, 2.2)                           # the end window: y0, y1, sill (its arched head above the cut)
CELL_Y = 1.95                                     # the cell fronts
N_CELLS = 6
PITCH = (RIGHT - END_X) / N_CELLS
PIER = 0.34                                       # a pier's face between two cell fronts
SIDE_T = 0.24                                     # the brick walls between cells
FRONT_H = 2.38                                    # the bars' height
CEIL = 2.46                                       # the cells' strap-iron ceilings
BAND = (2.5, 2.9)                                 # the brick band over the lintel
LEDGE = (2.9, 3.05, 0.3)                          # the ledge: bottom, top, how far it stands out
CLERE = (3.12, 3.82, 0.9)                         # the high windows over the cells: sill, head, width
RPIER = (-1.62, 0.34, 2.62)                       # the brick pier round the restraint room's door: y0, y1, height
RESTRAINT = (-1.12, -0.16)                        # the restraint room's door (y), in the right end wall
DESK = Vector((-3.5, -2.45)); DESK_W, DESK_D, DESK_H = 1.55, 0.72, 0.77    # along y, along x, top
DESK_CHAIR = Vector((-4.42, -2.45))
CHAIR_SEAT = 0.48
LAMP_Y = -0.35                                    # the pendants' line along the Mile
PENDANTS = [-2.6, -0.1, 2.4, 4.9]
BULB_Z = 3.02


def cell_x(i):
    """Cell i's (0 at the desk end) span between its side walls' faces."""
    x0 = END_X + i * PITCH; x1 = x0 + PITCH
    return x0 + (SIDE_T / 2 if i > 0 else 0.0), x1 - (SIDE_T / 2 if i < N_CELLS - 1 else 0.2)


def cell_mid(i):
    a, b = cell_x(i); return (a + b) / 2


# ---------------------------------------------------------------- materials
def mats():
    M = {}
    M['brick'] = material('gm_brick', rough=0.86, maps={'color': tx('brick_color.jpg'), 'normal': tx('brick_normal.jpg')}, scale=1.6, normal_strength=0.7)
    M['brick_dark'] = material('gm_brick_grimy', rough=0.88, maps={'color': tx('brick_grimy_color.jpg'), 'normal': tx('brick_normal.jpg')}, scale=1.6, normal_strength=0.7)
    M['lino'] = material('gm_linoleum', rough=0.28, maps={'color': tx('lino_color.jpg')}, scale=1.0, coat=0.35, coat_rough=0.12)
    M['concrete'] = material('gm_concrete', rough=0.8, maps={'color': tx('concrete_color.jpg'), 'normal': tx('concrete_normal.jpg')}, scale=2.0, normal_strength=0.4)
    M['ledge'] = material('gm_ledge', rough=0.85, maps={'color': tx('ledge_color.jpg'), 'normal': tx('concrete_normal.jpg')}, scale=2.0, normal_strength=0.4)
    M['iron'] = material('gm_iron', rough=0.55, maps={'color': tx('iron_color.jpg'), 'normal': tx('iron_normal.jpg')}, scale=0.8, normal_strength=0.4, metal=0.35)
    M['iron_dark'] = material('gm_iron_dark', (0.05, 0.05, 0.045), rough=0.5, metal=0.5)
    M['rivet'] = material('gm_rivet', (0.12, 0.12, 0.1), rough=0.45, metal=0.7)
    M['door_steel'] = material('gm_door_steel', rough=0.5, maps={'color': tx('door_steel_color.jpg'), 'normal': tx('iron_normal.jpg')}, scale=1.0, normal_strength=0.3, metal=0.4)
    M['wood'] = material('gm_desk_wood', rough=0.42, maps={'color': tx('wood_color.jpg')}, scale=0.9, coat=0.3, coat_rough=0.25)
    M['wood_light'] = material('gm_oak', rough=0.5, maps={'color': tx('oak_color.jpg')}, scale=0.9, coat=0.15)
    M['wc_door'] = material('gm_wc_door', rough=0.6, maps={'color': tx('wc_door_color.jpg')}, scale=1.0, coat=0.1)
    M['brass'] = material('gm_brass', (0.72, 0.53, 0.25), rough=0.3, metal=1.0)
    M['enamel_green'] = material('gm_shade_green', (0.055, 0.075, 0.06), rough=0.35, coat=0.4, coat_rough=0.25)
    M['enamel_white'] = material('gm_shade_inside', (0.85, 0.84, 0.78), rough=0.25, coat=0.5)
    M['lamp_green'] = material('gm_lamp_glass', (0.05, 0.28, 0.12), rough=0.15, coat=0.8, emission=(0.12, 0.5, 0.2), emission_strength=0.4)
    M['bulb'] = material('gm_bulb', (1.0, 0.92, 0.75), rough=0.3, emission=(1.0, 0.8, 0.52), emission_strength=16.0)
    M['blanket'] = material('gm_blanket', rough=0.92, maps={'color': tx('blanket_color.jpg')}, scale=0.8, sheen=0.3, sheen_tint=(0.35, 0.35, 0.33))
    M['ticking'] = material('gm_ticking', rough=0.9, maps={'color': tx('ticking_color.jpg')}, scale=0.6, sheen=0.2, sheen_tint=(0.4, 0.38, 0.32))
    M['porcelain'] = material('gm_porcelain', (0.82, 0.8, 0.74), rough=0.18, coat=0.6, coat_rough=0.1)
    M['paper'] = material('gm_paper', (0.82, 0.79, 0.7), rough=0.85)
    M['papers'] = material('gm_notices', rough=0.85, maps={'color': tx('notices_color.jpg')}, scale=1.0)
    M['cork'] = material('gm_cork', (0.36, 0.25, 0.15), rough=0.9)
    M['black'] = material('gm_black', (0.02, 0.02, 0.022), rough=0.4)
    M['bakelite'] = material('gm_bakelite', (0.03, 0.025, 0.02), rough=0.25, coat=0.6)
    M['apple'] = material('gm_apple', (0.42, 0.04, 0.03), rough=0.3, coat=0.6, coat_rough=0.15)
    M['radio_cloth'] = material('gm_radio_cloth', (0.36, 0.28, 0.17), rough=0.9)
    M['sky'] = material('gm_daylight', (1.0, 0.95, 0.84), rough=1.0, emission=(1.0, 0.93, 0.8), emission_strength=2.4)
    M['glass_frost'] = material('gm_window_glass', (0.78, 0.76, 0.68), rough=0.35, emission=(1.0, 0.92, 0.76), emission_strength=1.6)
    M['pad'] = material('gm_padding', (0.74, 0.71, 0.62), rough=0.9)
    M['kerb'] = material('gm_kerb', (0.1, 0.09, 0.08), rough=0.9)
    M['section'] = material('section', (0.03, 0.028, 0.026), rough=0.92)
    M['phantom'] = material('gm_phantom', (0.6, 0.56, 0.48), rough=0.9)
    return M


# ---------------------------------------------------------------- walls
def _wall_y(name, x0, x1, y0, y1, holes, mat, col, h=RH, z0=0.0):
    """A wall running along x (x0..x1) between y0 and y1, cut by openings (u0, u1, z0, z1) along x."""
    t = y1 - y0; yc = (y0 + y1) / 2
    xs = sorted({x0, x1} | {o[0] for o in holes} | {o[1] for o in holes}); k = 0
    for a, b in zip(xs, xs[1:]):
        hs = [o for o in holes if o[0] <= a + 1e-6 and o[1] >= b - 1e-6]
        spans = [(z0, h)] if not hs else [(z0, hs[0][2]), (hs[0][3], h)]
        for za, zb in spans:
            if zb - za < 1e-3: continue
            box(f'{name}_{k}', (b - a, t, zb - za), ((a + b) / 2, yc, (za + zb) / 2), mat, bev=0, collection=col, lm='arch'); k += 1


def _wall_x(name, x0, x1, y0, y1, holes, mat, col, h=RH, z0=0.0):
    """A wall running along y (y0..y1) between x0 and x1, cut by openings (v0, v1, z0, z1) along y."""
    t = x1 - x0; xc = (x0 + x1) / 2
    ys = sorted({y0, y1} | {o[0] for o in holes} | {o[1] for o in holes}); k = 0
    for a, b in zip(ys, ys[1:]):
        hs = [o for o in holes if o[0] <= a + 1e-6 and o[1] >= b - 1e-6]
        spans = [(z0, h)] if not hs else [(z0, hs[0][2]), (hs[0][3], h)]
        for za, zb in spans:
            if zb - za < 1e-3: continue
            box(f'{name}_{k}', (t, b - a, zb - za), (xc, (a + b) / 2, (za + zb) / 2), mat, bev=0, collection=col, lm='arch'); k += 1


def shell(M, arch, phantom):
    """The floors (the Mile's linoleum, the cells' concrete), the module's back wall with the high windows over the
    cells, the end wall (the entry door, the W.C., the window) with the passage behind it, the right end wall with the
    restraint room's door, the walls between the cells; kerbs; the phantom roof (its lights), front and right."""
    box('subfloor', (W, D, 0.02), (0, 0, -0.035), M['kerb'], bev=0, collection=arch, lm='arch')
    fl = box('floor_mile', (RIGHT - END_X, CELL_Y - FRONT, 0.03), ((END_X + RIGHT) / 2, (FRONT + CELL_Y) / 2, -0.015), M['lino'], bev=0, collection=arch, lm='arch')
    _floor_uv(fl, END_X, RIGHT, FRONT, CELL_Y)
    fc = box('floor_cells', (RIGHT - END_X, BACK - CELL_Y, 0.03), ((END_X + RIGHT) / 2, (CELL_Y + BACK) / 2, -0.015), M['concrete'], bev=0, collection=arch, lm='arch')
    cine.world_uv(fc, 1.0)
    fp = box('floor_passage', (PASS_X[1] - LEFT, BACK - FRONT, 0.03), ((LEFT + PASS_X[1]) / 2, (FRONT + BACK) / 2, -0.015), M['concrete'], bev=0, collection=arch, lm='arch')
    cine.world_uv(fp, 1.0)
    # the back wall: brick, a high barred window over each cell
    holes = [(cell_mid(i) - CLERE[2] / 2, cell_mid(i) + CLERE[2] / 2, CLERE[0], CLERE[1]) for i in range(N_CELLS)]
    _wall_y('back_wall', END_X - END_T, RIGHT, BACK, D / 2, holes, M['brick'], arch)
    box('back_wall_pass', (END_X - END_T + W / 2, T, RH), ((-W / 2 + END_X - END_T) / 2, BACK + T / 2, RH / 2), M['brick_dark'], bev=0, collection=arch, lm='arch')
    lw = box('left_wall', (T, D - T, RH), (-W / 2 + T / 2, -T / 2, RH / 2), M['brick_dark'], bev=0, collection=arch, lm='arch')
    lw.visible_shadow = False                                  # the passage is capped: the sun reaches the end window over it
    # the end wall: the entry door, the W.C., the window (to the cut: its arch is above)
    holes = [(ENTRY[0], ENTRY[1], 0.0, DOOR_H), (WC[0], WC[1], 0.0, 2.05), (WIN[0], WIN[1], WIN[2], RH + 0.01)]
    _wall_x('end_wall', END_X - END_T, END_X, FRONT, BACK, holes, M['brick'], arch)
    # the passage behind it: roofed where the people wait, its front closed by a dark cut (the building beyond)
    box('pass_roof', (PASS_X[1] - LEFT, PASS_Y[1] - PASS_Y[0], 0.12), ((LEFT + PASS_X[1]) / 2, (PASS_Y[0] + PASS_Y[1]) / 2, PASS_ROOF + 0.06), M['ledge'], bev=0, collection=arch, lm='arch')
    cap = box('pass_cap', (END_X - END_T + W / 2, BACK - FRONT + T, 0.02), ((-W / 2 + END_X - END_T) / 2, (FRONT - T + BACK) / 2 + T / 2, RH - 0.01), M['section'], bev=0, collection=arch)
    cap.visible_shadow = False
    box('pass_front', (END_X - END_T + W / 2, T, RH), ((-W / 2 + END_X - END_T) / 2, FRONT - T / 2, RH / 2), M['section'], bev=0, collection=arch)
    # the right end: a brick pier round the restraint room's door (lower than the cut: from the side of the case it
    # reads as a wall, not a black slab), kerbs either side of it
    _wall_x('pier_right', RIGHT - 0.26, RIGHT, RPIER[0], RPIER[1], [(RESTRAINT[0], RESTRAINT[1], 0.0, 1.98)], M['brick'], arch, h=RPIER[2])
    # the last cell's outer wall (the module's right side, behind the end wall), full height
    box('part_right_cell', (0.2, BACK - CELL_Y + 0.0, BAND[1]), (RIGHT - 0.1, (CELL_Y + BACK) / 2, BAND[1] / 2), M['brick'], bev=0, collection=arch, lm='arch')
    # the walls between the cells (and their ends): brick from the back wall to the fronts, up to the band's top
    for i in range(1, N_CELLS):
        x = END_X + i * PITCH
        box(f'part_cell{i}', (SIDE_T, BACK - CELL_Y, BAND[1]), (x, (CELL_Y + BACK) / 2, BAND[1] / 2), M['brick'], bev=0, collection=arch, lm='arch')
    # kerbs and phantoms
    box('kerb_front', (W, T, KH), (0, -D / 2 + T / 2, KH / 2), M['kerb'], bev=0.002, collection=arch, lm='arch')
    box('kerb_right', (T, RPIER[0] - FRONT + T, KH), (W / 2 - T / 2, (FRONT - T + RPIER[0]) / 2, KH / 2), M['kerb'], bev=0.002, collection=arch, lm='arch')
    box('kerb_right2', (T, CELL_Y - RPIER[1], KH), (W / 2 - T / 2, (RPIER[1] + CELL_Y) / 2, KH / 2), M['kerb'], bev=0.002, collection=arch, lm='arch')
    P_ = M['phantom']; ph = lambda name, size, loc, mat=P_: box(name, size, loc, mat, bev=0, collection=phantom, bake_only=1)
    for k, (x0, x1) in enumerate(_roof_spans()):
        ph(f'ph_roof{k}', (x1 - x0, D, 0.3), ((x0 + x1) / 2, 0, RH + 0.15))
    for k, (x0, x1) in enumerate(SKY_X):
        for j, (y0, y1) in enumerate((( -D / 2, SKY_Y[0]), (SKY_Y[1], D / 2))):
            ph(f'ph_roof_sky{k}{j}', (x1 - x0, y1 - y0, 0.3), ((x0 + x1) / 2, (y0 + y1) / 2, RH + 0.15))
    ph('ph_front', (W, 0.3, RH - KH), (0, FRONT - 0.15, KH + (RH - KH) / 2), M['brick'])
    ph('ph_right', (0.3, BACK - FRONT, RH - KH), (RIGHT + 0.15, (FRONT + BACK) / 2, KH + (RH - KH) / 2), M['brick'])


SKY_X = [(-2.9, -1.5), (0.2, 1.6), (3.3, 4.7)]       # the roof lights over the Mile (x), each SKY_Y across
SKY_Y = (-2.0, -0.6)


def _roof_spans():
    """The phantom roof's solid parts between the roof lights (along x)."""
    xs = [-W / 2] + [v for s in SKY_X for v in s] + [W / 2]
    return list(zip(xs[0::2], xs[1::2]))


def _floor_uv(ob, x0, x1, y0, y1):
    """0..1 UVs across the Mile (one texture for the whole floor: its seams and its worn track are placed)."""
    me = ob.data; uv = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li in poly.loop_indices:
            c = ob.matrix_basis @ me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = ((c.x - x0) / (x1 - x0), (c.y - y0) / (y1 - y0))


# ---------------------------------------------------------------- the cells
def cells(M, col, rnd):
    """Each cell's front: the brick piers, the strap-iron lattice with its door (riveted straps, a lock box, a food
    slot), the steel threshold and lintel; the brick band over it with the cell's number, the concrete ledge on its
    cast-iron brackets; the strap-iron ceiling; inside, the iron bunk with its ticking mattress and grey blanket, the
    toilet and the basin, a stool, a shelf. Cell 5 (Coffey's) is left without its door: the rig swings it."""
    y_bar = CELL_Y + 0.07
    for i in range(N_CELLS + 1):                                        # the piers (the end ones against the walls)
        x = END_X + i * PITCH
        w = PIER if 0 < i < N_CELLS else PIER / 2
        xc = x + (w / 2 if i == 0 else -w / 2 if i == N_CELLS else 0.0)
        box(f'pier{i}', (w, 0.32, BAND[1]), (xc, CELL_Y + 0.12, BAND[1] / 2), M['brick'], bev=0, collection=col, lm='arch')
    for i in range(N_CELLS):
        a = END_X + i * PITCH + (PIER / 2 if i > 0 else PIER / 2); b = END_X + (i + 1) * PITCH - (PIER / 2 if i < N_CELLS - 1 else PIER / 2)
        # the band over the lintel (brick), its top a concrete cap under the ledge
        box(f'band{i}', (b - a, 0.32, BAND[1] - BAND[0]), ((a + b) / 2, CELL_Y + 0.12, (BAND[0] + BAND[1]) / 2), M['brick'], bev=0, collection=col, lm='arch')
        box(f'lintel{i}', (b - a + 0.06, 0.1, 0.12), ((a + b) / 2, y_bar - 0.02, FRONT_H + 0.06), M['iron'], bev=0.004, collection=col, lm='furn')
        box(f'threshold{i}', (b - a, 0.16, 0.012), ((a + b) / 2, y_bar, 0.006), M['iron'], bev=0.002, collection=col, lm='furn')
        plate = box(f'number{i}', (0.16, 0.012, 0.2), ((a + b) / 2, CELL_Y - 0.045, BAND[0] + 0.2), M['door_steel'], bev=0.002, collection=col, lm='furn')
        _number(plate, i + 1, M, col)
        door_w = 0.78
        if i == COFFEY_CELL:                                             # its door is the rig's: the bars beside it, the frame over it
            _lattice(f'front{i}', a + 0.82, b, y_bar, M, col)
            box(f'front{i}_jamb', (0.06, 0.07, FRONT_H), (a + 0.03, y_bar, FRONT_H / 2), M['iron'], bev=0.003, collection=col, lm='furn')
            box(f'front{i}_head', (0.84, 0.07, 0.06), (a + 0.42, y_bar, FRONT_H - 0.03), M['iron'], bev=0.003, collection=col, lm='furn')
        else:
            _lattice(f'front{i}', a, b, y_bar, M, col, door=(a + 0.02, a + 0.02 + door_w), rnd=rnd)
        _ceiling_lattice(f'ceil{i}', a, b, M, col)
        _furnish(i, M, col, rnd)
    # the ledge over all of them, its brackets at the piers
    box('ledge', (RIGHT - END_X, LEDGE[2] + 0.32, LEDGE[1] - LEDGE[0]), ((END_X + RIGHT) / 2, CELL_Y + 0.28 - (LEDGE[2] + 0.32) / 2, (LEDGE[0] + LEDGE[1]) / 2), M['ledge'], bev=0.01, collection=col, lm='arch')
    for i in range(1, N_CELLS):
        _bracket(f'bracket{i}', END_X + i * PITCH, M, col)


COFFEY_CELL = 5
DEL_CELL = 3
CHIEF_CELL = 1


def _number(plate, n, M, col):
    """A cell's number, painted white on its plate (a few strokes)."""
    c = plate.location; segs = {1: [((0, -1), (0, 1))], 2: [((-1, 1), (1, 1)), ((1, 1), (1, 0)), ((1, 0), (-1, 0)), ((-1, 0), (-1, -1)), ((-1, -1), (1, -1))],
                                3: [((-1, 1), (1, 1)), ((1, 1), (1, -1)), ((-1, 0), (1, 0)), ((-1, -1), (1, -1))],
                                4: [((-1, 1), (-1, 0)), ((-1, 0), (1, 0)), ((1, 1), (1, -1))],
                                5: [((1, 1), (-1, 1)), ((-1, 1), (-1, 0)), ((-1, 0), (1, 0)), ((1, 0), (1, -1)), ((1, -1), (-1, -1))],
                                6: [((1, 1), (-1, 1)), ((-1, 1), (-1, -1)), ((-1, -1), (1, -1)), ((1, -1), (1, 0)), ((1, 0), (-1, 0))]}[n]
    white = material('gm_paint_white', (0.8, 0.78, 0.7), rough=0.6)
    for k, (p, q) in enumerate(segs):
        p = Vector((p[0] * 0.035, 0, p[1] * 0.06)); q = Vector((q[0] * 0.035, 0, q[1] * 0.06)); m = (p + q) / 2; d = q - p
        box(f'{plate.name}_s{k}', (abs(d.x) + 0.012, 0.004, abs(d.z) + 0.012), c + Vector((m.x, -0.008, m.z)), white, bev=0, collection=col, lm='furn')


def _lattice(name, a, b, y, M, col, door=None, rnd=None):
    """A cell front of strap iron between x a and b: the frame, the verticals ~11 cm apart, the flat bands every 45 cm,
    riveted where they cross; the door's frame thicker, its lock box and food slot."""
    h = FRONT_H; t = 0.05
    box(f'{name}_jambL', (0.06, 0.07, h), (a + 0.03, y, h / 2), M['iron'], bev=0.003, collection=col, lm='furn')
    box(f'{name}_jambR', (0.06, 0.07, h), (b - 0.03, y, h / 2), M['iron'], bev=0.003, collection=col, lm='furn')
    box(f'{name}_top', (b - a, 0.07, 0.06), ((a + b) / 2, y, h - 0.03), M['iron'], bev=0.003, collection=col, lm='furn')
    box(f'{name}_foot', (b - a, 0.07, 0.07), ((a + b) / 2, y, 0.035), M['iron'], bev=0.003, collection=col, lm='furn')
    n = max(4, int(round((b - a - 0.12) / 0.112)))
    xs = [a + 0.06 + (b - a - 0.12) * (k + 0.5) / n for k in range(n)]
    for k, x in enumerate(xs):
        box(f'{name}_v{k}', (0.022, t, h - 0.12), (x, y, h / 2), M['iron'], bev=0, collection=col, lm='furn')
    zs = [0.45, 0.9, 1.35, 1.8]
    for k, z in enumerate(zs):
        box(f'{name}_h{k}', (b - a - 0.12, 0.012, 0.055), ((a + b) / 2, y - t / 2 - 0.006, z), M['iron'], bev=0, collection=col, lm='furn')
        box(f'{name}_hb{k}', (b - a - 0.12, 0.012, 0.055), ((a + b) / 2, y + t / 2 + 0.006, z), M['iron'], bev=0, collection=col, lm='furn')
    if door:
        d0, d1 = door
        for k, x in enumerate((d0, d1)):
            box(f'{name}_dstile{k}', (0.05, 0.075, h - 0.12), (x, y - 0.002, h / 2), M['iron'], bev=0.003, collection=col, lm='furn')
        box(f'{name}_lock', (0.16, 0.09, 0.24), (d1 - 0.1, y - 0.01, 1.08), M['door_steel'], bev=0.006, collection=col, lm='furn')
        box(f'{name}_keyhole', (0.02, 0.004, 0.04), (d1 - 0.1, y - 0.058, 1.08), M['black'], bev=0, collection=col, lm='furn')
        box(f'{name}_slot', (0.36, 0.09, 0.12), ((d0 + d1) / 2, y - 0.01, 1.24), M['door_steel'], bev=0.004, collection=col, lm='furn')
        for k, z in enumerate((0.3, h - 0.3)):
            cyl(f'{name}_hinge{k}', 0.025, 0.14, (d0 - 0.03, y - 0.03, z), M['iron_dark'], seg=10, collection=col, lm='furn')


def _ceiling_lattice(name, a, b, M, col):
    """The cell's ceiling of strap iron: flat bars across and along, 20 cm apart (seen from above, the cell below)."""
    y0, y1 = CELL_Y + 0.1, BACK
    n = max(3, int((b - a) / 0.2))
    for k in range(n + 1):
        x = a + (b - a) * k / n
        box(f'{name}_a{k}', (0.012, y1 - y0, 0.05), (x, (y0 + y1) / 2, CEIL), M['iron'], bev=0, collection=col, lm='furn')
    m = int((y1 - y0) / 0.2)
    for k in range(m + 1):
        y = y0 + (y1 - y0) * k / m
        box(f'{name}_b{k}', (b - a, 0.012, 0.05), ((a + b) / 2, y, CEIL - 0.0), M['iron'], bev=0, collection=col, lm='furn')


def _furnish(i, M, col, rnd):
    """Inside cell i: the bunk along its left wall (the iron frame, the ticking mattress, the blanket, a pillow),
    the toilet and the basin against the back wall, a stool; in the empty ones a rolled mattress."""
    a, b = cell_x(i); a += 0.02 if i == 0 else 0.0
    yb = BACK
    bx0, bx1 = a + 0.04, a + 0.8; by0, by1 = CELL_Y + 0.55, yb - 0.08; z = 0.42
    for k, (x, y) in enumerate(((bx0, by0), (bx1, by0), (bx0, by1), (bx1, by1))):
        box(f'bunk{i}_leg{k}', (0.04, 0.04, z), (x + (0.02 if k % 2 == 0 else -0.02), y + (0.02 if k < 2 else -0.02), z / 2), M['iron_dark'], bev=0.002, collection=col, lm='furn')
    for k, y in enumerate((by0, by1)):
        box(f'bunk{i}_end{k}', (bx1 - bx0, 0.04, 0.05), ((bx0 + bx1) / 2, y + (0.02 if k == 0 else -0.02), z), M['iron_dark'], bev=0.002, collection=col, lm='furn')
    for k, x in enumerate((bx0, bx1)):
        box(f'bunk{i}_rail{k}', (0.04, by1 - by0, 0.05), (x + (0.02 if k == 0 else -0.02), (by0 + by1) / 2, z), M['iron_dark'], bev=0.002, collection=col, lm='furn')
    occupied = i in (COFFEY_CELL, DEL_CELL, CHIEF_CELL)
    if occupied or rnd.random() < 0.6:
        rounded_slab(f'bunk{i}_mattress', bx1 - bx0 - 0.02, by1 - by0 - 0.02, 0.1, 0.04, ((bx0 + bx1) / 2, (by0 + by1) / 2, z + 0.075), M['ticking'], edge_bev=0.03, collection=col, lm='furn')
        rounded_slab(f'bunk{i}_blanket', bx1 - bx0 + 0.02, (by1 - by0) * 0.62, 0.03, 0.02, ((bx0 + bx1) / 2, by0 + (by1 - by0) * 0.31, z + 0.13), M['blanket'], edge_bev=0.012, collection=col, lm='furn')
        rounded_slab(f'bunk{i}_pillow', (bx1 - bx0) * 0.8, 0.3, 0.08, 0.04, ((bx0 + bx1) / 2, by1 - 0.22, z + 0.17), M['ticking'], edge_bev=0.035, collection=col, lm='furn')
    else:
        cyl(f'bunk{i}_roll', 0.17, bx1 - bx0 - 0.06, ((bx0 + bx1) / 2, by1 - 0.3, z + 0.19), M['ticking'], rot=(0, math.pi / 2, 0), seg=16, collection=col, lm='furn')
    # the toilet in the back right corner, the basin beside it on the back wall
    t = Vector((b - 0.32, yb - 0.32, 0))
    lathe(f'wc{i}_bowl', [(0.0, 0.0), (0.12, 0.0), (0.14, 0.3), (0.2, 0.4), (0.0, 0.4)], M['porcelain'], loc=t, seg=18, collection=col, lm='furn')
    tube(f'wc{i}_pipe', [t + Vector((0, 0.18, 0.36)), t + Vector((0, 0.3, 0.6)), t + Vector((0, 0.3, 1.6))], 0.022, M['iron_dark'], col, seg=8, lm='furn')
    s = Vector((b - 0.36, yb - 0.17, 0.82))
    box(f'basin{i}', (0.4, 0.3, 0.14), s, M['porcelain'], bev=0.03, collection=col, lm='furn')
    box(f'basin{i}_bowl', (0.32, 0.22, 0.01), s + Vector((0, 0, 0.065)), M['iron_dark'], bev=0.01, collection=col, lm='furn')
    tube(f'basin{i}_tap', [s + Vector((0, 0.12, 0.07)), s + Vector((0, 0.12, 0.16)), s + Vector((0, 0.05, 0.17))], 0.01, M['brass'], col, seg=6, lm='furn')
    box(f'shelf{i}', (0.5, 0.2, 0.025), (b - 0.3, yb - 0.11, 1.55), M['wood_light'], bev=0.003, collection=col, lm='furn')
    if rnd.random() < 0.7 or occupied:
        sx = (a + b) / 2 + 0.25; sy = CELL_Y + 0.9 + rnd.uniform(-0.2, 0.3)
        cyl(f'stool{i}_seat', 0.16, 0.035, (sx, sy, 0.47), M['wood_light'], seg=20, collection=col, lm='furn')
        for k in range(3):
            ang = 2 * math.pi * k / 3 + 0.4
            tube(f'stool{i}_leg{k}', [Vector((sx + math.cos(ang) * 0.1, sy + math.sin(ang) * 0.1, 0.45)), Vector((sx + math.cos(ang) * 0.16, sy + math.sin(ang) * 0.16, 0.0))], 0.014, M['wood_light'], col, seg=6, lm='furn')
    if i == CHIEF_CELL:                                                     # a tin cup and a book on the shelf
        lathe(f'cup{i}', [(0.0, 0.0), (0.04, 0.0), (0.042, 0.09), (0.0, 0.09)], M['iron'], loc=(b - 0.42, yb - 0.11, 1.565), seg=12, collection=col, lm='furn')
        box(f'book{i}', (0.16, 0.12, 0.04), (b - 0.2, yb - 0.11, 1.585), material('gm_book', (0.24, 0.1, 0.07), rough=0.7), bev=0.004, collection=col, lm='furn')


def _bracket(name, x, M, col):
    """A cast-iron spandrel under the ledge at a pier: a quarter arc from the pier's face out to the ledge's edge,
    its two legs, two rings in the spandrel (after the set's brackets)."""
    y0 = CELL_Y - 0.04; z0 = BAND[1] - 0.55; ztop = LEDGE[0] - 0.005; out = LEDGE[2] - 0.04
    r = 0.012
    tube(f'{name}_leg', [Vector((x, y0, z0)), Vector((x, y0, ztop))], r, M['iron_dark'], col, seg=6, lm='furn')
    tube(f'{name}_arm', [Vector((x, y0, ztop)), Vector((x, y0 - out, ztop))], r, M['iron_dark'], col, seg=6, lm='furn')
    arc = [Vector((x, y0 - out * math.cos(a), ztop - (ztop - z0) * math.sin(a))) for a in [math.pi / 2 * k / 12 for k in range(13)]]
    tube(f'{name}_arc', arc, r, M['iron_dark'], col, seg=6, lm='furn')
    for k, (dy, dz, rr) in enumerate(((0.07, 0.07, 0.05), (0.16, 0.05, 0.035))):
        c = Vector((x, y0 - dy - rr * 0.3, ztop - dz - rr * 0.5))
        tube(f'{name}_ring{k}', circle(c, rr, (0, 1, 0), (0, 0, 1), n=16), 0.007, M['iron_dark'], col, closed=True, seg=6, lm='furn')


# ---------------------------------------------------------------- the end of the Mile: the desk, the doors, the window
def desk_end(M, col, rnd):
    """The duty desk facing down the Mile (dark wood, turned legs, a drawer pedestal), its chair; on it the green
    banker's lamp, the candlestick telephone, the brass bell, the ledger and papers, an apple, a cup; behind, the
    filing drawers, a side table with the radio, the radiator under the window, the notice board, the clock over the
    entry door, pipes up the wall; the W.C. door with its stencil. Returns the lamp's bulb."""
    c = DESK; hx, hy = DESK_D / 2, DESK_W / 2
    box('desk_top', (DESK_D + 0.04, DESK_W + 0.04, 0.04), (c.x, c.y, DESK_H - 0.02), M['wood'], bev=0.006, collection=col, lm='furn')
    box('desk_apron', (DESK_D - 0.06, DESK_W - 0.06, 0.12), (c.x, c.y, DESK_H - 0.1), M['wood'], bev=0.004, collection=col, lm='furn')
    box('desk_front', (0.02, DESK_W - 0.1, DESK_H - 0.25), (c.x + hx - 0.04, c.y, (DESK_H - 0.16) / 2 + 0.06), M['wood'], bev=0.004, collection=col, lm='furn')   # the modesty panel toward the Mile
    box('desk_pedestal', (DESK_D - 0.08, 0.42, DESK_H - 0.12), (c.x, c.y + hy - 0.25, (DESK_H - 0.12) / 2), M['wood'], bev=0.005, collection=col, lm='furn')
    for k in range(3):
        box(f'desk_drawer{k}', (0.012, 0.36, 0.17), (c.x - hx + 0.035, c.y + hy - 0.25, 0.14 + k * 0.2), M['wood'], bev=0.004, collection=col, lm='furn')
        box(f'desk_pull{k}', (0.02, 0.08, 0.015), (c.x - hx + 0.025, c.y + hy - 0.25, 0.18 + k * 0.2), M['brass'], bev=0.003, collection=col, lm='furn')
    for k, (sx, sy) in enumerate(((-1, -1), (1, -1))):
        lathe(f'desk_leg{k}', [(0.0, 0.0), (0.03, 0.0), (0.025, 0.08), (0.035, 0.14), (0.022, 0.25), (0.028, 0.55), (0.032, 0.64), (0.0, 0.65)], M['wood'],
              loc=(c.x + sx * (hx - 0.05), c.y + sy * (hy - 0.05), 0.0), seg=12, collection=col, lm='furn')
    # the chair behind it (a wooden office chair with arms)
    ch = DESK_CHAIR
    box('chair_seat', (0.46, 0.46, 0.04), (ch.x, ch.y, 0.46), M['wood_light'], bev=0.01, collection=col, lm='furn')
    box('chair_back', (0.04, 0.44, 0.38), (ch.x - 0.23, ch.y, 0.72), M['wood_light'], bev=0.01, collection=col, lm='furn')
    for k, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        cyl(f'chair_leg{k}', 0.018, 0.45, (ch.x + sx * 0.2, ch.y + sy * 0.2, 0.225), M['wood_light'], seg=8, collection=col, lm='furn')
    for s in (-1, 1):
        box(f'chair_arm{s}', (0.42, 0.05, 0.03), (ch.x - 0.02, ch.y + s * 0.23, 0.68), M['wood_light'], bev=0.008, collection=col, lm='furn')
        cyl(f'chair_armpost{s}', 0.012, 0.2, (ch.x + 0.15, ch.y + s * 0.23, 0.57), M['wood_light'], seg=8, collection=col, lm='furn')
    # on the desk (its top at DESK_H): the lamp at the back left, the telephone, the bell, papers, the ledger, an apple
    top = DESK_H
    L = Vector((c.x - 0.18, c.y + 0.5, top))
    lathe('lamp_base', [(0.0, 0.0), (0.09, 0.0), (0.085, 0.02), (0.03, 0.04), (0.0, 0.045)], M['brass'], loc=L, seg=20, collection=col, lm='furn')
    tube('lamp_stem', [L + Vector((0, 0, 0.04)), L + Vector((0, 0, 0.36))], 0.008, M['brass'], col, seg=8, lm='furn')
    sh = cyl('lamp_shade', 0.07, 0.36, L + Vector((0.03, 0, 0.38)), M['lamp_green'], rot=(math.pi / 2, 0, 0), seg=20, collection=col)   # the green glass (glowing: no light map)
    sh.scale = (1.0, 1.0, 1.0)
    bulb = L + Vector((0.05, 0, 0.33))
    P = Vector((c.x + 0.05, c.y - 0.52, top))
    lathe('phone_base', [(0.0, 0.0), (0.06, 0.0), (0.055, 0.025), (0.02, 0.05), (0.014, 0.3), (0.022, 0.32), (0.03, 0.34), (0.0, 0.35)], M['bakelite'], loc=P, seg=16, collection=col, lm='furn')
    lathe('phone_mouth', [(0.0, 0.0), (0.024, 0.0), (0.03, 0.04), (0.0, 0.045)], M['bakelite'], loc=P + Vector((0.04, 0, 0.31)), seg=12, collection=col, lm='furn')
    tube('phone_hook', [P + Vector((-0.01, 0.0, 0.28)), P + Vector((-0.06, 0.0, 0.3))], 0.005, M['brass'], col, seg=6, lm='furn')
    lathe('phone_ear', [(0.0, 0.0), (0.022, 0.0), (0.026, 0.05), (0.012, 0.1), (0.0, 0.1)], M['bakelite'], loc=P + Vector((-0.07, 0.0, 0.2)), seg=12, collection=col, lm='furn')
    lathe('desk_bell', [(0.0, 0.0), (0.045, 0.0), (0.045, 0.01), (0.04, 0.03), (0.025, 0.05), (0.006, 0.058), (0.0, 0.065)], M['brass'], loc=(c.x + 0.2, c.y - 0.2, top), seg=16, collection=col, lm='furn')
    box('ledger', (0.3, 0.42, 0.035), (c.x - 0.05, c.y + 0.05, top + 0.018), material('gm_ledger', (0.18, 0.08, 0.05), rough=0.6), rot=(0, 0, 0.08), bev=0.004, collection=col, lm='furn')
    for k in range(5):
        box(f'paper{k}', (0.21, 0.28, 0.002), (c.x + rnd.uniform(-0.15, 0.15), c.y + rnd.uniform(-0.45, 0.2), top + 0.002 + 0.0015 * k), M['paper'], rot=(0, 0, rnd.uniform(-0.4, 0.4)), bev=0, collection=col, lm='furn')
    lathe('apple', [(0.0, 0.0), (0.03, 0.006), (0.038, 0.03), (0.032, 0.058), (0.008, 0.066), (0.0, 0.06)], M['apple'], loc=(c.x + 0.24, c.y + 0.28, top), seg=14, collection=col, lm='furn')
    lathe('desk_cup', [(0.0, 0.0), (0.035, 0.0), (0.04, 0.08), (0.036, 0.08), (0.03, 0.006), (0.0, 0.006)], M['porcelain'], loc=(c.x - 0.25, c.y - 0.25, top), seg=14, collection=col, lm='furn')
    box('desk_tray', (0.26, 0.34, 0.05), (c.x - 0.2, c.y - 0.05, top + 0.025), M['wood'], bev=0.004, collection=col, lm='furn')
    # behind the desk, along the end wall (its face at END_X): the filing drawers, the side table and radio, the radiator
    x = END_X
    fx0, fx1, fy0, fy1 = x, x + 0.52, FRONT + 0.15, FRONT + 1.55
    box('files', (fx1 - fx0, fy1 - fy0, 1.42), ((fx0 + fx1) / 2, (fy0 + fy1) / 2, 0.71), M['wood'], bev=0.006, collection=col, lm='furn')
    for r in range(6):
        for q in range(4):
            yy = fy0 + 0.04 + (fy1 - fy0 - 0.08) * (q + 0.5) / 4; zz = 0.14 + r * 0.215
            box(f'files_d{r}{q}', (0.012, (fy1 - fy0 - 0.08) / 4 - 0.025, 0.19), (fx1 + 0.004, yy, zz + 0.09), M['wood'], bev=0.003, collection=col, lm='furn')
            box(f'files_p{r}{q}', (0.012, 0.06, 0.03), (fx1 + 0.012, yy, zz + 0.13), M['brass'], bev=0.002, collection=col, lm='furn')
            box(f'files_c{r}{q}', (0.006, 0.07, 0.035), (fx1 + 0.012, yy, zz + 0.07), M['paper'], bev=0, collection=col, lm='furn')
    rx0, rx1 = x + 0.02, x + 0.24
    ry0, ry1 = WIN[0] + 0.12, WIN[1] - 0.12
    n = int((ry1 - ry0) / 0.065)
    for k in range(n):
        yy = ry0 + (ry1 - ry0) * (k + 0.5) / n
        rounded_slab(f'radiator{k}', 0.2, 0.05, 0.66, 0.02, ((rx0 + rx1) / 2, yy, 0.47), M['iron'], edge_bev=0.012, collection=col, lm='furn')
    tube('radiator_pipe', [Vector((rx0 + 0.06, ry0, 0.12)), Vector((rx0 + 0.06, ry1, 0.12))], 0.02, M['iron'], col, seg=8, lm='furn')
    tube('pipe_up0', [Vector((x + 0.06, WIN[1] + 0.1, 0.0)), Vector((x + 0.06, WIN[1] + 0.1, RH - 0.01))], 0.028, M['iron'], col, seg=10, lm='furn')
    tube('pipe_up1', [Vector((x + 0.06, WIN[1] + 0.2, 0.0)), Vector((x + 0.06, WIN[1] + 0.2, RH - 0.01))], 0.018, M['iron'], col, seg=8, lm='furn')
    # the notice board between the window and the entry door
    nb = box('notice_board', (0.03, 0.84, 0.62), (x + 0.015, -1.78, 1.62), M['cork'], bev=0.004, collection=col, lm='furn')
    pp = box('notices', (0.006, 0.76, 0.54), (x + 0.033, -1.78, 1.62), M['papers'], bev=0, collection=col, lm='furn'); uv_rect(pp, 'x')
    for k, (dz, dl) in enumerate(((0.33, 0.9), (-0.33, 0.9))):
        box(f'notice_frame{k}', (0.04, 0.9, 0.04), (x + 0.02, -1.78, 1.62 + dz), M['wood'], bev=0.004, collection=col, lm='furn')
    for k, dy in enumerate((-0.45, 0.45)):
        box(f'notice_frame_s{k}', (0.04, 0.04, 0.7), (x + 0.02, -1.78 + dy, 1.62), M['wood'], bev=0.004, collection=col, lm='furn')
    # the clock over the entry door
    cc = Vector((x + 0.04, (ENTRY[0] + ENTRY[1]) / 2, DOOR_H + 0.42))
    cyl('wall_clock', 0.17, 0.05, cc, M['wood'], rot=(0, math.pi / 2, 0), seg=28, collection=col, lm='furn')
    cyl('clock_face', 0.145, 0.006, cc + Vector((0.027, 0, 0)), M['porcelain'], rot=(0, math.pi / 2, 0), seg=28, collection=col, lm='furn')
    for k, (ang, ln) in enumerate(((0.6, 0.09), (2.4, 0.12))):
        d = Vector((0, math.sin(ang), math.cos(ang)))
        box(f'clock_hand{k}', (0.004, 0.008, ln), cc + Vector((0.032, 0, 0)) + d * ln / 2, M['black'], rot=(-ang, 0, 0), bev=0, collection=col, lm='furn')
    # the side table against the end wall by cell 1, the radio on it
    sx, sy = x + 0.3, 1.55
    box('side_top', (0.5, 0.62, 0.035), (sx, sy, 0.74), M['wood'], bev=0.005, collection=col, lm='furn')
    for k, (dx, dy) in enumerate(((-0.2, -0.26), (0.2, -0.26), (-0.2, 0.26), (0.2, 0.26))):
        cyl(f'side_leg{k}', 0.02, 0.72, (sx + dx, sy + dy, 0.36), M['wood'], seg=8, collection=col, lm='furn')
    rb = Vector((sx + 0.02, sy, 0.76))
    box('radio_body', (0.24, 0.36, 0.3), rb + Vector((0, 0, 0.15)), M['wood'], bev=0.012, collection=col, lm='furn')
    cyl('radio_crown', 0.18, 0.24, rb + Vector((0, 0, 0.3)), M['wood'], rot=(0, math.pi / 2, 0), seg=24, collection=col, lm='furn')
    box('radio_grille', (0.01, 0.24, 0.2), rb + Vector((0.122, 0, 0.27)), M['radio_cloth'], bev=0.003, collection=col, lm='furn')
    for k, dy in enumerate((-0.07, 0.0, 0.07)):
        cyl(f'radio_knob{k}', 0.016, 0.02, rb + Vector((0.13, dy, 0.06)), M['bakelite'], rot=(0, math.pi / 2, 0), seg=10, collection=col, lm='furn')
    # a wastebasket by the desk
    lathe('wastebasket', [(0.0, 0.0), (0.12, 0.0), (0.15, 0.34), (0.14, 0.34), (0.11, 0.01), (0.0, 0.01)], M['iron_dark'], loc=(c.x - 0.2, c.y - DESK_W / 2 - 0.25, 0), seg=16, collection=col, lm='furn')
    return bulb


def doors(M, col):
    """The casings and the fixed doors: the entry door's steel frame (its leaf is the rig's), the W.C.'s painted wood
    door with its stencil (half open toward the passage), the restraint room's riveted steel door (shut), the floor
    grille beside it."""
    x = END_X
    for k, y in enumerate((ENTRY[0] - 0.05, ENTRY[1] + 0.05)):
        box(f'entry_frame{k}', (0.06, 0.1, DOOR_H + 0.1), (x + 0.02, y, (DOOR_H + 0.1) / 2), M['iron'], bev=0.004, collection=col, lm='furn')
    box('entry_frame_head', (0.06, ENTRY[1] - ENTRY[0] + 0.2, 0.1), (x + 0.02, (ENTRY[0] + ENTRY[1]) / 2, DOOR_H + 0.05), M['iron'], bev=0.004, collection=col, lm='furn')
    for k, y in enumerate((WC[0] - 0.04, WC[1] + 0.04)):
        box(f'wc_casing{k}', (0.03, 0.08, 2.09), (x + 0.015, y, 1.045), M['wood'], bev=0.003, collection=col, lm='furn')
    box('wc_casing_head', (0.03, WC[1] - WC[0] + 0.16, 0.08), (x + 0.015, (WC[0] + WC[1]) / 2, 2.09), M['wood'], bev=0.003, collection=col, lm='furn')
    lf = box('wc_leaf', (0.04, WC[1] - WC[0] - 0.02, 2.02), (0, 0, 0), M['wc_door'], bev=0.004, collection=col, lm='furn'); uv_rect(lf, 'x')
    for d in lf.data.uv_layers['UVMap'].data: d.uv = (1 - d.uv.x, d.uv.y)
    lf.location = (x - END_T + 0.02 - 0.0, WC[0] + 0.01 + (WC[1] - WC[0] - 0.02) / 2, 1.02)
    lf.location = (x - 0.04, (WC[0] + WC[1]) / 2, 1.02)                      # shut
    # the restraint room door (shut), riveted, a small barred grille; the floor grille beside it
    xr = RIGHT - 0.26
    y0, y1 = RESTRAINT
    for k, y in enumerate((y0 - 0.05, y1 + 0.05)):
        box(f'restraint_frame{k}', (0.06, 0.1, 2.08), (xr - 0.02, y, 1.04), M['iron'], bev=0.004, collection=col, lm='furn')
    box('restraint_frame_head', (0.06, y1 - y0 + 0.2, 0.1), (xr - 0.02, (y0 + y1) / 2, 2.03), M['iron'], bev=0.004, collection=col, lm='furn')
    dl = box('restraint_leaf', (0.05, y1 - y0 - 0.01, 1.955), (xr + 0.02, (y0 + y1) / 2, 0.0175 + 1.955 / 2), M['door_steel'], bev=0.004, collection=col, lm='furn')
    uv_rect(dl, 'x')
    for k, z in enumerate((0.25, 0.95, 1.65)):
        box(f'restraint_strap{k}', (0.012, y1 - y0 - 0.04, 0.07), (xr - 0.01, (y0 + y1) / 2, z), M['door_steel'], bev=0.003, collection=col, lm='furn')
        for j in range(6):
            cyl(f'restraint_rivet{k}{j}', 0.008, 0.008, (xr - 0.018, y0 + 0.06 + (y1 - y0 - 0.12) * j / 5, z), M['rivet'], rot=(0, math.pi / 2, 0), seg=8, collection=col, lm='furn')
    box('restraint_lock', (0.05, 0.12, 0.2), (xr - 0.02, y0 + 0.12, 1.05), M['iron_dark'], bev=0.004, collection=col, lm='furn')
    box('restraint_hasp', (0.03, 0.2, 0.05), (xr - 0.03, y0 + 0.08, 1.2), M['iron_dark'], bev=0.003, collection=col, lm='furn')
    for k in range(4):
        box(f'restraint_grille{k}', (0.012, 0.012, 0.22), (xr - 0.012, (y0 + y1) / 2 - 0.09 + k * 0.06, 1.58), M['iron_dark'], bev=0, collection=col, lm='furn')
    box('restraint_grille_back', (0.004, 0.24, 0.24), (xr - 0.002, (y0 + y1) / 2, 1.58), M['black'], bev=0, collection=col, lm='furn')
    gr = box('floor_grille', (0.012, 0.42, 0.3), (xr - 0.006, 0.45, 0.2), M['iron_dark'], bev=0.002, collection=col, lm='furn')
    for k in range(7):
        box(f'floor_grille_slat{k}', (0.014, 0.012, 0.26), (xr - 0.012, 0.27 + k * 0.06, 0.2), M['iron'], bev=0, collection=col, lm='furn')


def windows(M, col):
    """The end window (small panes in an iron frame, glowing daylight; its arch above the cut) and the high barred
    windows over the cells (their panes lit by the day outside)."""
    x = END_X - END_T
    y0, y1, z0 = WIN
    bd = box('end_window_light', (0.01, y1 - y0, RH - z0), (x + 0.03, (y0 + y1) / 2, (z0 + RH) / 2), M['sky'], bev=0, collection=col)
    bd.visible_shadow = False
    for k in range(7):
        y = y0 + (y1 - y0) * k / 6
        box(f'end_window_mv{k}', (0.05, 0.03 if 0 < k < 6 else 0.07, RH - z0), (x + 0.06, y, (z0 + RH) / 2), M['iron_dark'], bev=0, collection=col, lm='furn')
    nz = int((RH - z0) / 0.16)
    for k in range(nz + 1):
        z = z0 + (RH - z0) * k / nz
        box(f'end_window_mh{k}', (0.05, y1 - y0, 0.025 if 0 < k else 0.06), (x + 0.06, (y0 + y1) / 2, z), M['iron_dark'], bev=0, collection=col, lm='furn')
    box('end_window_sill', (0.32, y1 - y0 + 0.12, 0.06), (END_X - 0.1, (y0 + y1) / 2, z0 - 0.03), M['ledge'], bev=0.004, collection=col, lm='furn')
    # the high windows over the cells, in the back wall
    for i in range(N_CELLS):
        xc = cell_mid(i); w = CLERE[2]; za, zb = CLERE[0], CLERE[1]
        g = box(f'clere_light{i}', (w, 0.01, zb - za), (xc, D / 2 - 0.03, (za + zb) / 2), M['glass_frost'], bev=0, collection=col)
        g.visible_shadow = False
        for k in range(5):
            xx = xc - w / 2 + w * k / 4
            box(f'clere_mv{i}_{k}', (0.03 if 0 < k < 4 else 0.05, 0.04, zb - za), (xx, BACK + 0.04, (za + zb) / 2), M['iron_dark'], bev=0, collection=col, lm='furn')
        for k in range(4):
            zz = za + (zb - za) * k / 3
            box(f'clere_mh{i}_{k}', (w, 0.04, 0.025 if 0 < k < 3 else 0.05), (xc, BACK + 0.04, zz), M['iron_dark'], bev=0, collection=col, lm='furn')
        for k in range(9):                                                 # the bars inside the glass
            box(f'clere_bar{i}_{k}', (0.02, 0.02, zb - za), (xc - w / 2 + w * (k + 0.5) / 9, BACK - 0.03, (za + zb) / 2), M['iron'], bev=0, collection=col, lm='furn')
        box(f'clere_sill{i}', (w + 0.1, 0.16, 0.05), (xc, BACK - 0.06, za - 0.025), M['ledge'], bev=0.003, collection=col, lm='furn')


def pendants(M, col):
    """The Mile's lights: green enamel shades, white inside, a bare bulb in a wire cage under each, hung on rods from
    the roof (to the cut). Returns the bulbs."""
    out = []
    for k, x in enumerate(PENDANTS):
        p = Vector((x, LAMP_Y, BULB_Z))
        tube(f'pend_rod{k}', [Vector((x, LAMP_Y, RH - 0.005)), p + Vector((0, 0, 0.2))], 0.009, M['iron_dark'], col, seg=8, lm='furn')
        lathe(f'pend_cap{k}', [(0.0, 0.0), (0.05, 0.0), (0.04, 0.06), (0.0, 0.07)], M['enamel_green'], loc=p + Vector((0, 0, 0.13)), seg=16, collection=col, lm='furn')
        lathe(f'pend_shade{k}', [(0.05, 0.13), (0.12, 0.09), (0.21, 0.03), (0.25, 0.0), (0.245, -0.008)], M['enamel_green'], loc=p, seg=32, collection=col, lm='furn')
        lathe(f'pend_inside{k}', [(0.24, -0.006), (0.2, 0.025), (0.11, 0.082), (0.045, 0.12)], M['enamel_white'], loc=p, seg=32, collection=col, lm='furn')
        lathe(f'pend_bulb{k}', [(0.0, -0.11), (0.035, -0.08), (0.03, -0.02), (0.015, 0.02), (0.0, 0.03)], M['bulb'], loc=p, seg=12, collection=col)
        for j in range(6):                                                  # the cage
            a = 2 * math.pi * j / 6
            tube(f'pend_cage{k}_{j}', [p + Vector((math.cos(a) * 0.06, math.sin(a) * 0.06, 0.02)), p + Vector((math.cos(a) * 0.07, math.sin(a) * 0.07, -0.08)),
                                        p + Vector((0, 0, -0.15))], 0.003, M['iron_dark'], col, seg=4, lm='furn')
        out.append(p - Vector((0, 0, 0.05)))
    return out


# ---------------------------------------------------------------- the cut
def section(objs, M):
    """Every face the module's top cuts through (the walls' tops), flat and dark; the right end wall's outer face."""
    for ob in objs:
        if not ob.name.startswith(('back_wall', 'left_wall', 'end_', 'pass_', 'kerb')): continue
        me = ob.data
        if M['section'].name not in [m.name for m in me.materials if m]: me.materials.append(M['section'])
        k = [m.name if m else '' for m in me.materials].index(M['section'].name)
        for f in me.polygons:
            c = sum((me.vertices[i].co for i in f.vertices), Vector()) / len(f.vertices)
            c = ob.matrix_world @ c
            if f.normal.z > 0.9 and abs(c.z - RH * SCALE) < 0.006: f.material_index = k


# ---------------------------------------------------------------- light
SUN = (1.0, 0.84, 0.62)                    # a late-morning sun, warm (the film's amber)
SKY = (0.86, 0.9, 1.0)
WARM = (1.0, 0.72, 0.42)


def lights(bulbs, lamp):
    """The sun through the end window (a hard patch across the floor before the desk), the window's sky, the high
    windows' daylight over the cells, the roof lights over the Mile; the pendants' bulbs, the desk lamp; a dim day in
    the passage. Returns the lights (true size: `shrink` brings them in)."""
    out = []
    def light(name, kind, loc, energy, colour, rot=None, **kw):
        ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = colour
        for k, v in kw.items(): setattr(ld, k, v)
        ob = cine.link(bpy.data.objects.new(name, ld)); ob.location = loc
        if rot: ob.rotation_euler = rot
        if kind in ('AREA', 'SPOT', 'SUN'): ob.visible_camera = False; ob.visible_glossy = False
        out.append(ob); return ob
    sd = Vector((1.0, 0.3, -1.25)).normalized()                       # from high over the end wall, down the Mile
    light('sun', 'SUN', (0, 0, 8), 11.0, SUN, rot=sd.to_track_quat('-Z', 'Y').to_euler(), angle=math.radians(1.0))
    y0, y1, z0 = WIN
    light('window_sky', 'AREA', (END_X - END_T + 0.1, (y0 + y1) / 2, (z0 + RH) / 2), 260.0, SKY, rot=(0, math.pi / 2, 0), shape='RECTANGLE', size=RH - z0, size_y=y1 - y0)
    for i in range(N_CELLS):
        light(f'clere{i}', 'AREA', (cell_mid(i), BACK - 0.06, (CLERE[0] + CLERE[1]) / 2), 45.0, (1.0, 0.92, 0.8), rot=(-math.pi / 2, 0, 0), shape='RECTANGLE', size=CLERE[2], size_y=CLERE[1] - CLERE[0])
    for k, (x0, x1) in enumerate(SKY_X):
        light(f'rooflight{k}', 'AREA', ((x0 + x1) / 2, (SKY_Y[0] + SKY_Y[1]) / 2, RH + 0.02), 200.0, (1.0, 0.93, 0.82), shape='RECTANGLE', size=x1 - x0, size_y=SKY_Y[1] - SKY_Y[0])
    for k, p in enumerate(bulbs):
        light(f'pendant{k}', 'POINT', p, 75.0, WARM, shadow_soft_size=0.04)
    light('desk_lamp', 'POINT', lamp, 10.0, WARM, shadow_soft_size=0.03)
    light('passage', 'AREA', ((LEFT + PASS_X[1]) / 2, (PASS_Y[0] + PASS_Y[1]) / 2, PASS_ROOF - 0.05), 30.0, (1.0, 0.94, 0.84), shape='RECTANGLE', size=0.8, size_y=2.5)
    return out


def shrink(objs, lights_):
    """Bring the block, built at its true size, into the module (as the throne room)."""
    S_ = Matrix.Scale(SCALE, 4)
    for o in objs: o.matrix_world = S_ @ o.matrix_world
    for l in lights_:
        l.location = l.location * SCALE
        d = l.data
        if d.type == 'AREA': d.size *= SCALE; d.size_y *= SCALE
        if d.type in ('POINT', 'SPOT', 'AREA'): d.energy *= SCALE ** 2; d.shadow_soft_size *= SCALE
    bpy.context.view_layer.update()
