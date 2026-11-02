# Interstellar · Murph's bedroom in the farmhouse, an evening, and the tesseract behind its bookshelf. The room as the
# film has it (the shelf wall facing the door, the iron bed with its brass knobs along the shelf, two windows on the
# wall at the bed's foot): the door in the left wall, a strip of landing behind it; the bed's head toward the case,
# the bedside lamp lit; the shelf, floor to ceiling, runs from front to back as the room's right wall, open-backed,
# and behind it the tesseract: the room's world lines drawn out into a lattice of streaked beams and slits of white
# light, receding into the dark, where Cooper hangs at the backs of the books. Pine boards, plaster painted a pale
# dove grey, dark stained wood; the grey of the evening at the windows.
import math, os, random
import bpy, bmesh
from mathutils import Vector, Matrix
import cine
from cine import box, cyl, material, lathe, rounded_slab, moulding
from rooms.seinfeld import uv_rect, tube, circle

W, D = 9.6, 7.6
T = 0.14                                   # the module's walls
LEFT, BACK, RIGHT, FRONT = -W / 2 + T, D / 2 - T, W / 2 - T, -D / 2 + T
RH = 2.7                                   # the bedroom's ceiling (the walls' cut)
KH = 0.22                                  # the cut-away's kerb
TEX = os.path.join(cine.OUT, 'textures', 'interstellar')
tx = lambda n: os.path.join(TEX, n)

# the plan (true metres): the landing, the door wall, the bedroom, the shelf, the tesseract
HALL = (LEFT, -3.86)                       # the landing behind the door wall
P0, P1 = -3.86, -3.74                      # the door wall (its hall face, its room face)
SHELF_X, SHELF_D = 0.95, 0.32              # the shelf's face (room side) and depth: open at the back
TX0 = SHELF_X + SHELF_D                    # where the tesseract begins
DOOR = (-0.62, 0.22)                       # the doorway in the door wall (y); hinged at its back jamb
DOOR_H = 2.03
WINDOWS = (-2.75, -0.15)                   # the two windows in the back wall (centres, x)
WIN_W, WIN_SILL, WIN_HEAD = 0.86, 0.82, 2.26
# the bed: its head toward the case, its long side to the shelf
BED_X = (-2.18, -0.78)
BED_Y = (-3.36, -1.46)                     # the mattress
BED_TOP = 0.62
BED_HEAD_Y, BED_FOOT_Y = -3.42, -1.40      # the iron ends
SEAT = Vector((-0.70, -2.45))              # Murph's place on the bed's side
# the shelf: bays along y, shelves up the wall
BAYS = [(-3.62 + i * 0.905, -3.62 + (i + 1) * 0.905) for i in range(8)]
SHELVES = [0.10, 0.43, 0.76, 1.09, 1.42, 1.75, 2.08, 2.41]
SHELF_T = 0.028                            # a shelf board's thickness
FALL_BAY = 6                               # the bay whose books fall (y 1.81 .. 2.72, Kia's "books fallen")
FALL_SHELF = 3                             # on the shelf at 1.09 (Cooper's chest height behind it)
STAY_BAY, STAY_SHELF = 5, 4                # the book punched out at the end (the shelf above, the bay before)
DESK_Y = (0.72, 1.82)
DESK_TOP = 0.76


# ---------------------------------------------------------------- materials
def mats():
    M = {}
    M['floor'] = material('pine_boards', rough=0.55, maps={'color': tx('floor_color.jpg'), 'normal': tx('floor_normal.jpg')}, scale=2.0, normal_strength=0.5, coat=0.25, coat_rough=0.35)
    M['wall'] = material('dove_plaster', rough=0.8, maps={'color': tx('wall_color.jpg'), 'normal': tx('wall_normal.jpg')}, scale=2.0, normal_strength=0.3)
    M['stain'] = material('dark_stain', rough=0.42, maps={'color': tx('stain_color.jpg'), 'normal': tx('stain_normal.jpg')}, scale=1.0, normal_strength=0.3, coat=0.3, coat_rough=0.2)
    M['white'] = material('white_paint', (0.78, 0.77, 0.73), rough=0.45, coat=0.2)
    M['iron'] = material('black_iron', (0.03, 0.03, 0.03), rough=0.45, metal=0.6)
    M['brass'] = material('brass', (0.78, 0.58, 0.28), rough=0.28, metal=1.0)
    M['quilt'] = material('rose_quilt', rough=0.62, maps={'color': tx('quilt_color.jpg'), 'normal': tx('quilt_normal.jpg')}, scale=0.9, normal_strength=0.6, sheen=0.4, sheen_tint=(0.7, 0.55, 0.55))
    M['sheet'] = material('sheets', rough=0.75, maps={'color': tx('sheet_color.jpg')}, scale=0.5, sheen=0.3, sheen_tint=(0.6, 0.6, 0.6))
    M['rug'] = material('rag_rug', rough=0.9, maps={'color': tx('rug_color.jpg')}, scale=1.0)
    M['books'] = material('books', rough=0.6, maps={'color': tx('books_color.jpg')}, scale=1.0)
    M['cork'] = material('corkboard', rough=0.85, maps={'color': tx('cork_color.jpg')}, scale=1.0)
    M['print'] = material('farm_print', rough=0.6, maps={'color': tx('print_color.jpg')}, scale=1.0)
    M['sky'] = material('evening_sky', rough=1.0, maps={'color': tx('sky_color.jpg')}, scale=1.0)
    M['streak'] = material('world_lines', rough=0.5, maps={'color': tx('streak_color.jpg')}, scale=1.0, coat=0.4, coat_rough=0.2)
    M['streak_dark'] = material('world_lines_dark', (0.035, 0.028, 0.024), rough=0.6)
    M['slit'] = material('light_slit', (1.0, 1.0, 1.0), rough=0.5, emission=(0.86, 0.92, 1.0), emission_strength=1.0)
    M['shade'] = material('lamp_shade', (0.92, 0.84, 0.68), rough=0.8, emission=(1.0, 0.72, 0.4), emission_strength=1.6)
    M['bulb'] = material('bulb', (1.0, 0.9, 0.7), rough=0.3, emission=(1.0, 0.78, 0.48), emission_strength=18.0)
    M['curtain'] = material('curtain_cotton', (0.74, 0.7, 0.62), rough=0.85, sheen=0.3, sheen_tint=(0.5, 0.5, 0.45))
    M['radiator'] = material('radiator_paint', (0.62, 0.6, 0.56), rough=0.5, metal=0.3)
    M['chair_black'] = material('shell_chair_black', (0.025, 0.025, 0.028), rough=0.35, coat=0.4)
    M['chrome'] = material('chrome', (0.8, 0.8, 0.8), rough=0.15, metal=1.0)
    M['paper'] = material('paper', (0.86, 0.84, 0.78), rough=0.8)
    M['globe'] = material('globe_blue', (0.12, 0.26, 0.44), rough=0.3, coat=0.6)
    M['toy_red'] = material('toy_red', (0.56, 0.08, 0.06), rough=0.35, coat=0.5)
    M['toy_white'] = material('toy_white', (0.8, 0.8, 0.78), rough=0.35, coat=0.5)
    M['lander_gold'] = material('lander_gold', (0.75, 0.55, 0.2), rough=0.25, metal=1.0)
    M['lander_grey'] = material('lander_grey', (0.42, 0.42, 0.42), rough=0.45, metal=0.3)
    M['runner'] = material('hall_runner', (0.3, 0.16, 0.12), rough=0.9)
    M['kerb'] = material('kerb', (0.12, 0.09, 0.07), rough=0.9)
    M['section'] = material('section', (0.03, 0.028, 0.026), rough=0.92)
    M['phantom'] = material('phantom_ceiling', (0.7, 0.68, 0.64), rough=0.9)
    M['void'] = material('tesseract_void', (0.006, 0.006, 0.007), rough=0.95)
    return M


def _tag(objs, **props):
    for o in objs:
        for k, v in props.items(): o[k] = v
    return objs


# ---------------------------------------------------------------- the shell
def shell(M, arch, phantom):
    """The floor (pine boards through the bedroom and the landing, the tesseract's black below), the module's left
    and back walls, the door wall between the landing and the room (its doorway), the windows' openings in the back
    wall (a sash, muntins, a sill; the evening outside, painted on a backdrop in the wall's thickness), the skirting;
    the kerbs; the phantom ceilings and the front wall."""
    box('subfloor', (W, D, 0.02), (0, 0, -0.035), M['kerb'], bev=0, collection=arch, lm='arch')
    fl = box('floor_room', (TX0 - LEFT, BACK - FRONT, 0.03), ((LEFT + TX0) / 2, 0, -0.015), M['floor'], bev=0, collection=arch, lm='arch')
    cine.world_uv(fl, 1.0)
    box('floor_void', (RIGHT - TX0, BACK - FRONT, 0.03), ((TX0 + RIGHT) / 2, 0, -0.015), M['void'], bev=0, collection=arch, lm='arch')
    # the module's left wall (the landing's outer wall) and the back wall, its windows cut out (the landing's own window too)
    box('left_wall', (T, D - T, RH), (-W / 2 + T / 2, -T / 2, RH / 2), M['wall'], bev=0, collection=arch, lm='arch')
    openings = [(x - WIN_W / 2, x + WIN_W / 2, WIN_SILL, WIN_HEAD) for x in WINDOWS] + [(-4.5, -4.02, 1.0, 2.1)]
    _wall_with_holes('back_wall', LEFT, TX0, BACK, T, openings, M['wall'], arch)
    # the door wall: full height, the doorway in it
    _wall_x('left_doorwall', P0, P1, FRONT, BACK, [(DOOR[0], DOOR[1], 0.0, DOOR_H)], M['wall'], arch)
    # the skirting (stained) round the room and the landing
    sk = [(Vector((P1, FRONT, 0)), Vector((P1, DOOR[0], 0)), (1, 0, 0)), (Vector((P1, DOOR[1], 0)), Vector((P1, BACK, 0)), (1, 0, 0)),
          (Vector((P1, BACK, 0)), Vector((SHELF_X, BACK, 0)), (0, -1, 0)),
          (Vector((LEFT, FRONT, 0)), Vector((LEFT, BACK, 0)), (1, 0, 0)), (Vector((P0, FRONT, 0)), Vector((P0, DOOR[0], 0)), (-1, 0, 0)),
          (Vector((P0, DOOR[1], 0)), Vector((P0, BACK, 0)), (-1, 0, 0)), (Vector((LEFT, BACK, 0)), Vector((P0, BACK, 0)), (0, -1, 0))]
    prof = [(0, 0), (0.018, 0), (0.018, 0.15), (0.01, 0.165), (0, 0.17)]
    for k, (a, b, n) in enumerate(sk):
        moulding(f'skirting{k}', a, b, n, prof, M['stain'], collection=arch, lm='arch')
    # the kerbs (front and right) and the phantoms: the ceilings over the room and the landing, the front wall
    box('kerb_front', (W, T, KH), (0, -D / 2 + T / 2, KH / 2), M['kerb'], bev=0.002, collection=arch, lm='arch')
    box('kerb_right', (T, D - 2 * T, KH), (W / 2 - T / 2, 0, KH / 2), M['kerb'], bev=0.002, collection=arch, lm='arch')
    P_ = M['phantom']; ph = lambda name, size, loc, mat=P_: box(name, size, loc, mat, bev=0, collection=phantom, bake_only=1)
    ph('ph_ceiling', (TX0 - LEFT, D, 0.3), ((LEFT + TX0) / 2, 0, RH + 0.15))
    ph('ph_front', (TX0 - LEFT, 0.3, RH - KH), ((LEFT + TX0) / 2, FRONT - 0.15, KH + (RH - KH) / 2), M['wall'])


def _wall_with_holes(name, x0, x1, y, t, holes, mat, col):
    """A wall along x at depth y (its room face at y - t/2... the module's back wall: its face at BACK), cut by
    rectangular openings (x0, x1, z0, z1): the solid pieces between and over and under them."""
    yc = y + t / 2
    xs = sorted({x0, x1} | {h[0] for h in holes} | {h[1] for h in holes})
    k = 0
    for a, b in zip(xs, xs[1:]):
        hs = [h for h in holes if h[0] <= a + 1e-6 and h[1] >= b - 1e-6]
        spans = [(0.0, RH)] if not hs else [(0.0, hs[0][2]), (hs[0][3], RH)]
        for z0, z1 in spans:
            if z1 - z0 < 1e-3: continue
            box(f'{name}_{k}', (b - a, t, z1 - z0), ((a + b) / 2, yc, (z0 + z1) / 2), mat, bev=0, collection=col, lm='arch'); k += 1
    # the opening's reveals: the wall's thickness, painted
    for i, (a, b, z0, z1) in enumerate(holes):
        for s, xx in ((0, a), (1, b)):
            box(f'{name}_reveal{i}{s}', (0.004, t, z1 - z0), (xx + (0.002 if s == 0 else -0.002), yc, (z0 + z1) / 2), mat, bev=0, collection=col, lm='arch')


def _wall_x(name, x0, x1, y0, y1, holes, mat, col):
    """A wall across x0..x1 running along y, cut by openings (y0, y1, z0, z1)."""
    xc = (x0 + x1) / 2; t = x1 - x0
    ys = sorted({y0, y1} | {h[0] for h in holes} | {h[1] for h in holes}); k = 0
    for a, b in zip(ys, ys[1:]):
        hs = [h for h in holes if h[0] <= a + 1e-6 and h[1] >= b - 1e-6]
        spans = [(0.0, RH)] if not hs else [(hs[0][3], RH)]
        for z0, z1 in spans:
            box(f'{name}_{k}', (t, b - a, z1 - z0), (xc, (a + b) / 2, (z0 + z1) / 2), mat, bev=0, collection=col, lm='arch'); k += 1


# ---------------------------------------------------------------- windows and doors
def windows(M, col):
    """The bedroom's two windows and the landing's: white sashes (the lower one, the upper), a cross of muntins in each
    sash, a white casing and sill, cotton curtains drawn to the sides; behind them, in the wall's thickness, the evening
    (the corn, a shelter belt, the grey-blue sky), lit (a backdrop: it glows, it does not light the room)."""
    out = []
    for k, (xc, w, z0, z1) in enumerate([(x, WIN_W, WIN_SILL, WIN_HEAD) for x in WINDOWS] + [(-4.26, 0.48, 1.0, 2.1)]):
        y = BACK; a, b = xc - w / 2, xc + w / 2
        bd = box(f'sky_{k}', (w + 0.1, 0.01, z1 - z0 + 0.1), (xc, BACK + T - 0.012, (z0 + z1) / 2), M['sky'], bev=0, collection=col)
        uv_rect(bd, 'y'); bd['backdrop'] = 1
        fw = 0.05                                                            # the sash frames: two sashes, meeting at the middle
        zm = (z0 + z1) / 2
        for j, (s0, s1, yo) in enumerate(((z0, zm + 0.02, 0.06), (zm - 0.02, z1, 0.03))):
            for (u0, u1, v0, v1) in ((a, a + fw, s0, s1), (b - fw, b, s0, s1), (a, b, s0, s0 + fw), (a, b, s1 - fw, s1)):
                box(f'win{k}_sash{j}_{u0:.2f}_{v0:.2f}', (u1 - u0, 0.04, v1 - v0), ((u0 + u1) / 2, y + yo, (v0 + v1) / 2), M['white'], bev=0.003, collection=col, lm='furn')
            box(f'win{k}_mullion{j}', (0.018, 0.025, s1 - s0 - 2 * fw), (xc, y + yo, (s0 + s1) / 2), M['white'], bev=0.002, collection=col, lm='furn')
            box(f'win{k}_bar{j}', (w - 2 * fw, 0.025, 0.018), (xc, y + yo, (s0 + s1) / 2), M['white'], bev=0.002, collection=col, lm='furn')
        cw = 0.08                                                            # the casing, the stool and apron below
        for (u0, u1, v0, v1) in ((a - cw, a, z0 - 0.02, z1 + cw), (b, b + cw, z0 - 0.02, z1 + cw), (a - cw, b + cw, z1, z1 + cw)):
            box(f'win{k}_casing_{u0:.2f}_{v0:.2f}', (u1 - u0, 0.022, v1 - v0), ((u0 + u1) / 2, y - 0.011, (v0 + v1) / 2), M['white'], bev=0.003, collection=col, lm='furn')
        box(f'win{k}_stool', (w + 2 * cw + 0.06, 0.12, 0.025), (xc, y - 0.04, z0 - 0.012), M['white'], bev=0.004, collection=col, lm='furn')
        box(f'win{k}_apron', (w + 2 * cw, 0.02, 0.07), (xc, y - 0.01, z0 - 0.06), M['white'], bev=0.003, collection=col, lm='furn')
        if k < 2:                                                            # curtains on a rod, drawn to the sides
            cyl(f'win{k}_rod', 0.012, w + 0.5, (xc, y - 0.1, z1 + 0.14), M['brass'], rot=(0, math.pi / 2, 0), seg=10, collection=col, lm='furn')
            for s in (-1, 1):
                c = cine.cloth_panel(f'win{k}_curtain{s}', 0.34, z1 + 0.12 - 0.05, 4, 0.025, M['curtain'], loc=(xc + s * (w / 2 + 0.08), y - 0.11, z1 + 0.12), collection=col, gather=0.85, seed=k * 2 + s)
                c['lm'] = 'furn'
        out.append((xc, w, z0, z1))
    return out


def door_leaf(name, w, h, M, col):
    """The bedroom door: dark stained, four raised panels each side, a white porcelain knob on a brass rose (built
    about its hinge edge at the origin, closed along -y, its room face toward +x)."""
    t = 0.04; parts = []
    parts.append(box(f'{name}_slab', (t, w, h), (0, -w / 2, h / 2), M['stain'], bev=0.004, collection=col))
    for s in (-1, 1):
        x = s * (t / 2 + 0.004)
        for k, (z0, z1) in enumerate(((0.16, 0.9), (1.06, h - 0.16))):
            for j, (y0, y1) in enumerate(((-w + 0.12, -w / 2 - 0.05), (-w / 2 + 0.05, -0.12))):
                parts.append(box(f'{name}_panel{s}{k}{j}', (0.012, y1 - y0, z1 - z0), (x, (y0 + y1) / 2, (z0 + z1) / 2), M['stain'], bev=0.012, seg=2, collection=col))
        parts.append(cyl(f'{name}_rose{s}', 0.026, 0.008, (s * (t / 2 + 0.004), -w + 0.07, 0.95), M['brass'], rot=(0, math.pi / 2, 0), seg=20, collection=col))
        parts.append(lathe(f'{name}_knob{s}', [(0.0, 0.0), (0.008, 0.0), (0.008, 0.03), (0.028, 0.05), (0.024, 0.07), (0.0, 0.075)], M['white'], loc=(s * (t / 2 + 0.008), -w + 0.07, 0.95), seg=16, collection=col))
        parts[-1].rotation_euler = (0, s * math.pi / 2, 0)
    return parts


def doorway(M, col):
    """The doorway's casings (both faces of the door wall, dark stained, a cap over the head), its jambs; the door
    itself belongs to the room's rig (it opens)."""
    for face, x, s in (('room', P1, 1), ('hall', P0, -1)):
        for k, y in enumerate((DOOR[0] - 0.09, DOOR[1])):
            box(f'casing_{face}{k}', (0.022, 0.09, DOOR_H + 0.09), (x + s * 0.011, y + 0.045, (DOOR_H + 0.09) / 2), M['stain'], bev=0.003, collection=col, lm='arch')
        box(f'casing_{face}_head', (0.03, DOOR[1] - DOOR[0] + 0.24, 0.11), (x + s * 0.015, (DOOR[0] + DOOR[1]) / 2, DOOR_H + 0.09 + 0.055), M['stain'], bev=0.004, collection=col, lm='arch')
    for k, y in enumerate((DOOR[0] + 0.01, DOOR[1] - 0.01)):
        box(f'jamb{k}', (P1 - P0, 0.02, DOOR_H), ((P0 + P1) / 2, y, DOOR_H / 2), M['stain'], bev=0.002, collection=col, lm='arch')
    box('jamb_head', (P1 - P0, DOOR[1] - DOOR[0], 0.02), ((P0 + P1) / 2, (DOOR[0] + DOOR[1]) / 2, DOOR_H - 0.01), M['stain'], bev=0.002, collection=col, lm='arch')


# ---------------------------------------------------------------- the bookshelf
def bookshelf(M, col, rnd, skip):
    """The wall of books, floor to ceiling and front to back: stained uprights between the bays, a shelf every 33 cm,
    a plinth, a cornice under the ceiling; no back (the tesseract sees the books from behind). The books: hardbacks
    and paperbacks of every height, packed, a few leaning, some lying flat in stacks, gaps here and there; toys and a
    globe among them. `skip` (bay, shelf) -> the y ranges kept clear for the rig's books and the lander. Returns the
    books' places on the rig's shelves ({(bay, shelf): [(y0, y1, h, d)]})."""
    x0, x1 = SHELF_X, TX0; xc = (x0 + x1) / 2
    for i, (a, b) in enumerate(BAYS):
        box(f'shelf_upright{i}', (SHELF_D, 0.034, RH - 0.01), (xc, a, (RH - 0.01) / 2), M['stain'], bev=0.003, collection=col, lm='furn')
    box(f'shelf_upright{len(BAYS)}', (SHELF_D, 0.034, RH - 0.01), (xc, BAYS[-1][1], (RH - 0.01) / 2), M['stain'], bev=0.003, collection=col, lm='furn')
    y0, y1 = BAYS[0][0], BAYS[-1][1]
    box('shelf_plinth', (0.03, y1 - y0, SHELVES[0]), (x0 + 0.015, (y0 + y1) / 2, SHELVES[0] / 2), M['stain'], bev=0.003, collection=col, lm='furn')
    box('shelf_cornice', (SHELF_D + 0.04, y1 - y0 + 0.04, 0.12), (xc - 0.02, (y0 + y1) / 2, RH - 0.07), M['stain'], bev=0.006, collection=col, lm='furn')
    for z in SHELVES:
        box(f'shelf_board{int(z * 100)}', (SHELF_D, y1 - y0, SHELF_T), (xc, (y0 + y1) / 2, z - SHELF_T / 2), M['stain'], bev=0.003, collection=col, lm='furn')
    # the gap between the shelf's ends and the walls: closed by the stained ends
    box('shelf_end_front', (SHELF_D, abs(FRONT - y0) + 0.002, RH), (xc, (FRONT + y0) / 2, RH / 2), M['stain'], bev=0, collection=col, lm='furn')
    box('shelf_end_back', (SHELF_D, abs(BACK - y1) + 0.002, RH), (xc, (BACK + y1) / 2, RH / 2), M['stain'], bev=0, collection=col, lm='furn')
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap')
    rig_rows = {}
    for i, (a, b) in enumerate(BAYS):
        for j, z in enumerate(SHELVES[:-1] + [SHELVES[-1]]):
            top = (SHELVES[j + 1] - SHELF_T) if j + 1 < len(SHELVES) else RH - 0.13
            room = top - z
            y = a + 0.02; yend = b - 0.02
            keep = skip.get((i, j))
            row = []
            while y < yend - 0.015:
                if keep and keep[0] - 0.005 <= y < keep[1]:
                    y = keep[1] + 0.003; continue
                r = rnd.random()
                if r < 0.04 and room > 0.2:                                     # a gap
                    y += rnd.uniform(0.04, 0.12); continue
                if r < 0.1:                                                     # a stack lying flat
                    n = rnd.randint(2, 5); w_ = rnd.uniform(0.15, 0.22); zz = z
                    if y + w_ > yend: break
                    for _ in range(n):
                        th = rnd.uniform(0.02, 0.04)
                        if zz + th > top - 0.01: break
                        _book(bm, uvl, x0 + 0.02 + rnd.uniform(0, 0.03), y, y + w_, zz, th, rnd.uniform(0.18, 0.24), rnd, flat=True); zz += th
                    y += w_ + 0.005; continue
                th = rnd.uniform(0.016, 0.05) if rnd.random() < 0.8 else rnd.uniform(0.05, 0.075)
                h = min(room - 0.012, rnd.uniform(0.17, 0.3) if rnd.random() < 0.85 else rnd.uniform(0.12, 0.17))
                dpt = min(SHELF_D - 0.03, rnd.uniform(0.13, 0.24))
                if y + th > yend: break
                _book(bm, uvl, x0 + 0.015 + rnd.uniform(0, 0.02), y, y + th, z, h, dpt, rnd)
                y += th + rnd.uniform(0.0, 0.003)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = cine._mesh_obj('books_shelved', bm, M['books'], col, smooth=False); ob['lm'] = 'furn'
    cine.log('books', len(ob.data.polygons) // 6)
    return ob


def _book(bm, uvl, xf, y0, y1, z, h, d, rnd, flat=False, xf_mat=None):
    """A book as a box: its spine toward the room (-x) taking a random cell of the spine atlas, its fore-edge toward
    the back (+x) and its top and bottom the page edges; standing (flat=False: y0..y1 its thickness, h its height) or
    lying (y0..y1 its height across, h its thickness)."""
    x0, x1 = xf, xf + d; z0, z1 = z, z + h
    v = [bm.verts.new((x, y, zz)) for x in (x0, x1) for y in (y0, y1) for zz in (z0, z1)]
    if xf_mat is not None:
        for q in v: q.co = xf_mat @ q.co
    i_, j_ = rnd.randrange(32), rnd.randrange(4)
    cu0, cu1 = i_ / 64, (i_ + 1) / 64 - 0.002; cv0, cv1 = j_ / 4 + 0.01, (j_ + 1) / 4 - 0.01
    pu0, pu1 = 0.55 + rnd.random() * 0.3, 0.0; pu1 = pu0 + 0.08
    def face(ids, uv):
        f = bm.faces.new([v[k] for k in ids])
        for l, q in zip(f.loops, uv): l[uvl].uv = q
    spine = [(cu0, cv0), (cu1, cv0), (cu1, cv1), (cu0, cv1)] if not flat else [(cu0, cv0), (cu0, cv1), (cu1, cv1), (cu1, cv0)]
    face((0, 2, 3, 1), spine)                                                  # -x: the spine
    pg = [(pu0, 0.1), (pu1, 0.1), (pu1, 0.9), (pu0, 0.9)]
    face((4, 5, 7, 6), pg)                                                     # +x: the fore-edge
    face((1, 3, 7, 5), pg); face((0, 4, 6, 2), pg)                             # top, bottom
    cov = [(cu0, cv0), (cu0 + 0.001, cv0), (cu0 + 0.001, cv1), (cu0, cv1)]
    face((0, 1, 5, 4), cov); face((2, 6, 7, 3), cov)                           # the boards (the cover's colour)


def rig_books(rnd):
    """The rig's books (the ones Cooper pushes out, and the one he punches out last): their places on their shelves
    (true metres: y0, y1, height, depth), and the lander's spot beside them."""
    a, b = BAYS[FALL_BAY]; z = SHELVES[FALL_SHELF]
    falls, y = [], a + 0.24
    for k in range(5):
        th = rnd.uniform(0.03, 0.05); falls.append((y, y + th, rnd.uniform(0.22, 0.27), rnd.uniform(0.17, 0.21))); y += th + 0.002
    lander = (y + 0.02, y + 0.2)                                               # the lander model stands beside them
    a2, b2 = BAYS[STAY_BAY]; y2 = (a2 + b2) / 2
    stay = [(y2, y2 + 0.045, 0.26, 0.2)]
    return {'falls': falls, 'fall_z': z, 'lander': lander, 'stay': stay, 'stay_z': SHELVES[STAY_SHELF]}


# ---------------------------------------------------------------- the bed and the rest of the room
def bed(M, col):
    """The iron bed: black tube ends with brass top rails and brass ball knobs on the posts, a row of spindles; the
    side rails; the mattress, a white sheet turned down over the dusty rose quilt, two pillows."""
    xa, xb = BED_X
    for name, y, hp, hc in (('head', BED_HEAD_Y, 1.28, 1.16), ('foot', BED_FOOT_Y, 0.98, 0.88)):
        for k, x in enumerate((xa - 0.03, xb + 0.03)):
            cyl(f'bed_{name}_post{k}', 0.019, hp, (x, y, hp / 2), M['iron'], seg=14, collection=col, lm='furn')
            lathe(f'bed_{name}_knob{k}', [(0.0, 0.0), (0.02, 0.0), (0.022, 0.012), (0.032, 0.035), (0.034, 0.05), (0.028, 0.068), (0.012, 0.078), (0.0, 0.08)], M['brass'], loc=(x, y, hp), seg=18, collection=col, lm='furn')
            lathe(f'bed_{name}_collar{k}', [(0.024, 0.0), (0.024, 0.03), (0.0, 0.03)], M['brass'], loc=(x, y, hc - 0.32), seg=14, collection=col, lm='furn')
        tube(f'bed_{name}_top', [Vector((xa - 0.03, y, hc)), Vector((xb + 0.03, y, hc))], 0.014, M['brass'], col, seg=10, lm='furn')
        tube(f'bed_{name}_rail', [Vector((xa - 0.03, y, hc - 0.32)), Vector((xb + 0.03, y, hc - 0.32))], 0.011, M['iron'], col, seg=8, lm='furn')
        tube(f'bed_{name}_low', [Vector((xa - 0.03, y, 0.36)), Vector((xb + 0.03, y, 0.36))], 0.011, M['iron'], col, seg=8, lm='furn')
        n = 9
        for i in range(1, n):
            x = xa - 0.03 + (xb - xa + 0.06) * i / n
            tube(f'bed_{name}_spindle{i}', [Vector((x, y, 0.36)), Vector((x, y, hc - 0.32))], 0.0075, M['iron'], col, seg=6, lm='furn')
            tube(f'bed_{name}_bar{i}', [Vector((x, y, hc - 0.32)), Vector((x, y, hc))], 0.0075, M['brass'] if i % 2 == 0 else M['iron'], col, seg=6, lm='furn')
    for k, x in enumerate((xa - 0.03, xb + 0.03)):
        box(f'bed_side{k}', (0.03, BED_FOOT_Y - BED_HEAD_Y, 0.1), (x, (BED_HEAD_Y + BED_FOOT_Y) / 2, 0.36), M['iron'], bev=0.004, collection=col, lm='furn')
    ya, yb = BED_Y
    box('bed_spring', (xb - xa, yb - ya, 0.12), ((xa + xb) / 2, (ya + yb) / 2, 0.42), M['iron'], bev=0.01, collection=col, lm='furn')
    rounded_slab('mattress', xb - xa + 0.02, yb - ya + 0.02, 0.16, 0.06, ((xa + xb) / 2, (ya + yb) / 2, BED_TOP - 0.08), M['sheet'], edge_bev=0.04, collection=col, lm='furn')
    # the quilt over the lower two thirds, hanging over the sides; the sheet turned down over it
    q0 = ya + 0.55
    _drape('quilt', xa - 0.07, xb + 0.07, q0, yb + 0.06, BED_TOP + 0.012, 0.3, M['quilt'], col, rumple=0.012, seed=3)
    _drape('sheet_fold', xa - 0.05, xb + 0.05, q0 - 0.16, q0 + 0.02, BED_TOP + 0.026, 0.12, M['sheet'], col, rumple=0.006, seed=4)
    for k, x in enumerate(((xa + xb) / 2 - 0.33, (xa + xb) / 2 + 0.33)):
        rounded_slab(f'pillow{k}', 0.6, 0.38, 0.13, 0.12, (x, ya + 0.24, BED_TOP + 0.06), M['sheet'], rot=(math.radians(12), 0, 0), edge_bev=0.05, collection=col, lm='furn')


def _drape(name, x0, x1, y0, y1, z, hang, mat, col, rumple=0.01, seed=1, nx=40, ny=30):
    """A cover laid over the bed: flat on top with a little rumple, falling over the sides (x0, x1) and the foot (y1)
    by `hang`."""
    rnd = random.Random(seed); bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap')
    W_, D_ = x1 - x0 + 2 * hang, y1 - y0 + hang
    grid = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            u, v = i / nx * W_, j / ny * D_
            x, y = x0 - hang + u, y0 + v; zz = z
            if x < x0: zz = z - (x0 - x); x = x0 - 0.01 * (x0 - x) / hang
            elif x > x1: zz = z - (x - x1); x = x1 + 0.01 * (x - x1) / hang
            if y > y1: zz = min(zz, z - (y - y1)); y = y1 + 0.01 * (y - y1) / hang
            zz += rumple * (math.sin(u * 9 + rnd.random()) * math.sin(v * 7) * 0.6 + rnd.uniform(-0.3, 0.3))
            row.append(bm.verts.new((x, y, zz)))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for l, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))): l[uvl].uv = (ii / nx * W_, jj / ny * D_)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        if f.normal.z < -0.2: f.normal_flip()
    ob = cine._mesh_obj(name, bm, mat, col, smooth=True); ob['lm'] = 'furn'
    sol = ob.modifiers.new('thick', 'SOLIDIFY'); sol.thickness = 0.008
    return ob


def furniture(M, col, rnd):
    """The bedside: a stained nightstand at the bed's head, its lamp (a cream drum shade on a brass column) lit, an
    alarm clock, a glass of water; the rag rug by the bed; the desk against the door wall with the black shell chair,
    papers, a desk lamp and the globe, the corkboard over it; a chest of drawers between the windows with toy rockets
    and the space shuttle on it; the rocking chair in the far corner; a radiator under the first window. Returns the
    lamp's bulb (the light's place)."""
    nx, ny = BED_X[0] - 0.38, BED_HEAD_Y + 0.18
    _nightstand('nightstand', Vector((nx, ny, 0)), M, col)
    lamp_at = Vector((nx + 0.04, ny + 0.02, 0.62))
    lathe('lamp_base', [(0.0, 0.0), (0.08, 0.0), (0.08, 0.015), (0.03, 0.04), (0.018, 0.3), (0.026, 0.32), (0.012, 0.36), (0.0, 0.36)], M['brass'], loc=lamp_at, seg=20, collection=col, lm='furn')
    lathe('lamp_shade', [(0.15, 0.0), (0.155, 0.003), (0.12, 0.22), (0.115, 0.225)], M['shade'], loc=lamp_at + Vector((0, 0, 0.26)), seg=32, collection=col)   # glowing: no light map
    bulb = lamp_at + Vector((0, 0, 0.38))
    lathe('lamp_bulb', [(0.0, -0.03), (0.03, 0.0), (0.024, 0.04), (0.0, 0.05)], M['bulb'], loc=bulb, seg=12, collection=col)
    clock = lathe('alarm_clock', [(0.0, 0.0), (0.045, 0.0), (0.05, 0.05), (0.045, 0.1), (0.0, 0.1)], M['toy_white'], loc=(nx - 0.12, ny - 0.1, 0.62), seg=16, collection=col, lm='furn')
    clock.rotation_euler = (math.pi / 2, 0, 0.3); clock.location.z += 0.05
    # the rug, an oval by the bed's side where her feet are
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); c = Vector((SEAT.x + 0.45, SEAT.y + 0.1, 0.004)); n = 48
    ring = [bm.verts.new(c + Vector((0.55 * math.cos(2 * math.pi * i / n), 0.85 * math.sin(2 * math.pi * i / n), 0))) for i in range(n)]
    f = bm.faces.new(ring)
    for l in f.loops: q = l.vert.co - c; l[uvl].uv = (0.5 + q.x / 1.1, 0.5 + q.y / 1.7)
    rug = cine._mesh_obj('rug', bm, M['rug'], col, smooth=False); rug['lm'] = 'furn'
    sol = rug.modifiers.new('thick', 'SOLIDIFY'); sol.thickness = 0.008; sol.offset = 1
    # the desk on the door wall: drawers at the left, turned legs, papers, the lamp, the globe
    _desk(M, col, rnd)
    cb = box('corkboard', (0.025, DESK_Y[1] - DESK_Y[0] - 0.1, 0.62), (P1 + 0.0125, (DESK_Y[0] + DESK_Y[1]) / 2, 1.48), M['cork'], bev=0.003, collection=col, lm='furn')
    uv_rect(cb, 'x')
    for k, (y, z) in enumerate(((DESK_Y[0] + 0.03, 1.48), (DESK_Y[1] - 0.03, 1.48))):
        box(f'cork_frame{k}', (0.03, 0.03, 0.66), (P1 + 0.015, y, z), M['stain'], bev=0.003, collection=col, lm='furn')
    for k, z in enumerate((1.17, 1.79)):
        box(f'cork_frame_h{k}', (0.03, DESK_Y[1] - DESK_Y[0] - 0.04, 0.03), (P1 + 0.015, (DESK_Y[0] + DESK_Y[1]) / 2, z), M['stain'], bev=0.003, collection=col, lm='furn')
    # the chest of drawers between the windows; on it toy rockets, the shuttle, a jar of pencils
    cx = (WINDOWS[0] + WINDOWS[1]) / 2; cy = BACK - 0.26
    box('chest_body', (1.0, 0.48, 1.0), (cx, cy, 0.52), M['stain'], bev=0.006, collection=col, lm='furn')
    box('chest_top', (1.04, 0.52, 0.03), (cx, cy, 1.035), M['stain'], bev=0.006, collection=col, lm='furn')
    for j in range(4):
        z = 0.2 + j * 0.22
        box(f'chest_drawer{j}', (0.94, 0.02, 0.19), (cx, cy - 0.245, z), M['stain'], bev=0.006, collection=col, lm='furn')
        for s in (-1, 1): cyl(f'chest_pull{j}{s}', 0.014, 0.025, (cx + s * 0.25, cy - 0.26, z), M['brass'], rot=(math.pi / 2, 0, 0), seg=12, collection=col, lm='furn')
    _rocket('toy_rocket0', Vector((cx - 0.3, cy, 1.05)), 0.28, M, col)
    _rocket('toy_rocket1', Vector((cx + 0.32, cy + 0.05, 1.05)), 0.2, M, col)
    _shuttle('toy_shuttle', Vector((cx, cy - 0.04, 1.05)), M, col)
    # the radiator under the first window
    xr = WINDOWS[0]
    for k in range(14):
        x = xr - 0.32 + k * 0.05
        rounded_slab(f'radiator_fin{k}', 0.035, 0.16, 0.56, 0.015, (x, BACK - 0.14, 0.42), M['radiator'], edge_bev=0.008, collection=col, lm='furn')
    box('radiator_top', (0.72, 0.17, 0.02), (xr, BACK - 0.14, 0.71), M['radiator'], bev=0.004, collection=col, lm='furn')
    tube('radiator_pipe', [Vector((xr + 0.38, BACK - 0.14, 0.0)), Vector((xr + 0.38, BACK - 0.14, 0.2)), Vector((xr + 0.34, BACK - 0.14, 0.24))], 0.014, M['radiator'], col, seg=8, lm='furn')
    return bulb


def _nightstand(name, p, M, col):
    box(f'{name}_top', (0.46, 0.4, 0.025), p + Vector((0, 0, 0.6)), M['stain'], bev=0.005, collection=col, lm='furn')
    box(f'{name}_case', (0.42, 0.36, 0.2), p + Vector((0, 0, 0.48)), M['stain'], bev=0.004, collection=col, lm='furn')
    box(f'{name}_drawer', (0.36, 0.02, 0.15), p + Vector((0.0, -0.185, 0.48)), M['stain'], bev=0.005, collection=col, lm='furn')
    cyl(f'{name}_pull', 0.012, 0.02, p + Vector((0, -0.2, 0.48)), M['brass'], rot=(math.pi / 2, 0, 0), seg=10, collection=col, lm='furn')
    box(f'{name}_shelf', (0.38, 0.32, 0.02), p + Vector((0, 0, 0.14)), M['stain'], bev=0.003, collection=col, lm='furn')
    for sx in (-1, 1):
        for sy in (-1, 1):
            lathe(f'{name}_leg{sx}{sy}', [(0.02, 0.0), (0.016, 0.05), (0.022, 0.2), (0.016, 0.38), (0.02, 0.4), (0.0, 0.4)], M['stain'], loc=p + Vector((sx * 0.19, sy * 0.16, 0)), seg=10, collection=col, lm='furn')


def _desk(M, col, rnd):
    x0 = P1 + 0.02; dd = 0.56; xc = x0 + dd / 2; ya, yb = DESK_Y
    box('desk_top', (dd, yb - ya, 0.03), (xc, (ya + yb) / 2, DESK_TOP - 0.015), M['stain'], bev=0.005, collection=col, lm='furn')
    box('desk_apron', (dd - 0.06, yb - ya - 0.06, 0.1), (xc, (ya + yb) / 2, DESK_TOP - 0.08), M['stain'], bev=0.004, collection=col, lm='furn')
    box('desk_drawers', (dd - 0.04, 0.38, DESK_TOP - 0.06), (xc, yb - 0.21, (DESK_TOP - 0.06) / 2), M['stain'], bev=0.005, collection=col, lm='furn')
    for j in range(3):
        z = 0.14 + j * 0.2
        box(f'desk_drawer{j}', (0.02, 0.34, 0.17), (x0 + dd - 0.01, yb - 0.21, z), M['stain'], bev=0.005, collection=col, lm='furn')
        cyl(f'desk_pull{j}', 0.012, 0.02, (x0 + dd + 0.005, yb - 0.21, z), M['brass'], rot=(0, math.pi / 2, 0), seg=10, collection=col, lm='furn')
    for k, (x, y) in enumerate(((x0 + 0.04, ya + 0.04), (x0 + dd - 0.04, ya + 0.04))):
        lathe(f'desk_leg{k}', [(0.024, 0.0), (0.018, 0.08), (0.026, 0.3), (0.018, 0.6), (0.022, DESK_TOP - 0.1), (0.0, DESK_TOP - 0.1)], M['stain'], loc=(x, y, 0), seg=12, collection=col, lm='furn')
    # papers, a stack of books, the globe, a desk lamp (off), a jar of pencils
    for k in range(5):
        box(f'desk_paper{k}', (0.21, 0.28, 0.002), (xc + rnd.uniform(-0.08, 0.05), ya + 0.35 + rnd.uniform(-0.05, 0.12), DESK_TOP + 0.001 + k * 0.0015), M['paper'], rot=(0, 0, rnd.uniform(-0.4, 0.4)), bev=0, collection=col, lm='furn')
    g = Vector((xc - 0.05, yb - 0.18, DESK_TOP))
    lathe('globe_stand', [(0.0, 0.0), (0.07, 0.0), (0.07, 0.015), (0.015, 0.03), (0.012, 0.08), (0.0, 0.08)], M['brass'], loc=g, seg=16, collection=col, lm='furn')
    s = bpy.ops.mesh.primitive_uv_sphere_add(radius=0.11, segments=24, ring_count=12, location=g + Vector((0, 0, 0.2)))
    gl = bpy.context.active_object; gl.name = 'globe'; gl.data.materials.append(M['globe']); gl['lm'] = 'furn'
    for c in gl.users_collection: c.objects.unlink(gl)
    col.objects.link(gl)
    tube('globe_arc', circle(g + Vector((0, 0, 0.2)), 0.125, (0, 0, 1), (1, 0, 0), n=20, a0=-1.9, a1=1.9), 0.005, M['brass'], col, seg=6, lm='furn')
    cyl('pencil_jar', 0.035, 0.1, (xc + 0.12, ya + 0.12, DESK_TOP + 0.05), M['toy_red'], seg=14, collection=col, lm='furn')
    # the black plastic shell chair on chrome legs, pulled out a little, facing the desk
    T_ = Matrix.Translation((x0 + dd + 0.32, (ya + yb) / 2 - 0.1, 0)) @ Matrix.Rotation(math.pi + 0.15, 4, 'Z')
    parts = [rounded_slab('chair_seat', 0.44, 0.42, 0.03, 0.1, (0, 0, 0.46), M['chair_black'], collection=col, lm='furn'),
             rounded_slab('chair_back', 0.44, 0.035, 0.34, 0.1, (0, 0.21, 0.72), M['chair_black'], rot=(math.radians(-10), 0, 0), collection=col, lm='furn')]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(tube(f'chair_leg{sx}{sy}', [Vector((0.19 * sx, 0.18 * sy, 0)), Vector((0.17 * sx, 0.16 * sy, 0.45))], 0.009, M['chrome'], col, seg=8, lm='furn'))
    for o in parts: cine.place(o, T_)


def _rocket(name, p, h, M, col):
    """A toy rocket: a white body, a red nose, three fins."""
    lathe(name, [(0.0, 0.0), (h * 0.09, 0.0), (h * 0.1, h * 0.65), (h * 0.07, h * 0.82), (0.0, h * 0.82)], M['toy_white'], loc=p, seg=16, collection=col, lm='furn')
    lathe(f'{name}_nose', [(h * 0.07, h * 0.82), (h * 0.04, h * 0.92), (0.0, h)], M['toy_red'], loc=p, seg=16, collection=col, lm='furn')
    for k in range(3):
        a = 2 * math.pi * k / 3
        box(f'{name}_fin{k}', (h * 0.16, 0.006, h * 0.22), p + Vector((math.cos(a) * h * 0.13, math.sin(a) * h * 0.13, h * 0.11)), M['toy_red'], rot=(0, 0, a), bev=0.002, collection=col, lm='furn')


def _shuttle(name, p, M, col):
    """The space shuttle model: a white fuselage lying along x, its delta wings, a black nose."""
    b = lathe(f'{name}_body', [(0.0, 0.0), (0.03, 0.01), (0.035, 0.05), (0.035, 0.26), (0.03, 0.3), (0.0, 0.3)], M['toy_white'], loc=(0, 0, 0), seg=14, collection=col, lm='furn')
    b.rotation_euler = (0, math.pi / 2, 0); b.location = p + Vector((-0.15, 0, 0.04))
    bm = bmesh.new(); vs = [bm.verts.new(q) for q in ((-0.12, -0.13, 0), (0.08, -0.03, 0), (0.08, 0.03, 0), (-0.12, 0.13, 0))]; bm.faces.new(vs)
    w = cine._mesh_obj(f'{name}_wing', bm, M['toy_white'], col, smooth=False); w.location = p + Vector((0, 0, 0.025)); w['lm'] = 'furn'
    s = w.modifiers.new('t', 'SOLIDIFY'); s.thickness = 0.006
    box(f'{name}_tail', (0.07, 0.006, 0.07), p + Vector((-0.11, 0, 0.09)), M['toy_white'], bev=0.002, collection=col, lm='furn')


def landing(M, col):
    """The landing beyond the door: the boards, a long runner, a small table against the outer wall at the far end
    with a lamp, a framed farm print; its ceiling light."""
    xc = (HALL[0] + HALL[1]) / 2
    box('hall_runner', (0.5, BACK - FRONT - 0.6, 0.006), (xc, 0.0, 0.003), M['runner'], bev=0.001, collection=col, lm='furn')
    box('hall_table', (0.3, 0.6, 0.03), (LEFT + 0.16, 2.6, 0.78), M['stain'], bev=0.004, collection=col, lm='furn')
    for k, y in enumerate((2.34, 2.86)):
        cyl(f'hall_table_leg{k}', 0.015, 0.77, (LEFT + 0.16, y, 0.385), M['stain'], seg=8, collection=col, lm='furn')
    pr = box('hall_print', (0.02, 0.5, 0.38), (LEFT + 0.012, 0.9, 1.6), M['print'], bev=0.002, collection=col, lm='furn'); uv_rect(pr, 'x')
    box('hall_print_frame', (0.025, 0.56, 0.44), (LEFT + 0.008, 0.9, 1.6), M['stain'], bev=0.004, collection=col, lm='furn')


# ---------------------------------------------------------------- the tesseract
def tesseract(M, col, rnd):
    """Behind the shelf, the tesseract: the world lines of the room's things drawn out across time. Bundles of thin
    slats streaked with the colours of the books and the wood (each slat a strip of a different moment), crossing on
    three axes like a bookcase's frame grown huge: two screens of them parallel to the shelf (at 2.5 and 3.8 m), their
    rails along the wall at the shelves' heights and their stiles at the bays'; struts back from the shelf to the
    first screen; a lattice floor and roof; between the bundles, deeper layers and slits of white light, like light
    through blinds (the light that guides it, from Murph's window). The near cell, where Cooper hangs at the backs of
    the books, is open toward the back of the room."""
    xa, xb = TX0, RIGHT
    cell = ((BAYS[FALL_BAY][0] + BAYS[FALL_BAY][1]) / 2 - 1.1, (BAYS[FALL_BAY][0] + BAYS[FALL_BAY][1]) / 2 + 1.1)
    def bundle(name, p0, p1, w, h, n=None):
        """A bundle of slats from p0 to p1 (axis-aligned), w across and h deep: a dark core and n streaked slats
        side by side on its faces, a hair apart, each a strip of the world-line texture."""
        p0, p1 = Vector(p0), Vector(p1); d = p1 - p0; L = d.length; ax = max(range(3), key=lambda i: abs(d[i]))
        mid = (p0 + p1) / 2; o = [i for i in range(3) if i != ax]
        size = [0, 0, 0]; size[ax] = L; size[o[0]] = w * 0.8; size[o[1]] = h * 0.8
        box(f'{name}_core', tuple(size), tuple(mid), M['streak_dark'], bev=0, collection=col, lm='arch')
        n = n or max(3, int(w / 0.035))
        for k in range(n):                                                   # slats across w, each at its own depth
            t = (k + 0.5) / n - 0.5; th = h * rnd.uniform(0.75, 1.0)
            sz = [0, 0, 0]; sz[ax] = L - rnd.uniform(0, 0.06); sz[o[0]] = w / n * 0.86; sz[o[1]] = th
            c = mid.copy(); c[o[0]] += t * w; c[o[1]] += rnd.uniform(-0.02, 0.02)
            ob = box(f'{name}_{k}', tuple(sz), tuple(c), M['streak'], bev=0.0015, collection=col, lm='arch')
            _streak_uv(ob, ax, rnd)
    # the two screens: rails at the shelves' heights (some doubled), stiles at the bays'
    for s, x in enumerate((2.5, 3.8)):
        for j, z in enumerate(SHELVES[1:]):
            if rnd.random() < 0.15: continue
            y0_, y1_ = FRONT, BACK
            if s == 0 and 0.6 < z < 2.3:                                     # Cooper's cell: the first screen opens round him
                bundle(f'rail{s}_{j}a', (x, FRONT, z), (x, cell[0], z), 0.14, 0.12); bundle(f'rail{s}_{j}b', (x, cell[1], z), (x, BACK, z), 0.14, 0.12)
            else:
                bundle(f'rail{s}_{j}', (x, y0_, z), (x, y1_, z), 0.14 if s == 0 else 0.2, 0.12)
        for i, (a, b) in enumerate(BAYS + [(BAYS[-1][1], 0)]):
            if s == 0 and cell[0] - 0.1 < a < cell[1] + 0.1: continue
            if rnd.random() < 0.25: continue
            bundle(f'stile{s}_{i}', (x, a, 0.0), (x, a, 3.0), 0.16 if s == 0 else 0.24, 0.14)
    # struts back from the shelf's frame to the first screen, and on to the second (the corridors' edges)
    for i, (a, b) in enumerate(BAYS + [(BAYS[-1][1], 0)]):
        for j, z in enumerate(SHELVES[1:]):
            if rnd.random() < 0.6: continue
            inside = cell[0] - 0.05 < a < cell[1] + 0.05 and 0.6 < z < 2.3
            x0_ = 2.5 if inside else xa + 0.01
            bundle(f'strut{i}_{j}', (x0_, a, z), (xb, a, z), 0.06, 0.05, n=2)
    # the lattice floor and roof: bundles across and along, the black void below
    for i in range(6):
        x = xa + 0.3 + i * (xb - xa - 0.5) / 5
        bundle(f'floor_along{i}', (x, FRONT, 0.1), (x, BACK, 0.1), 0.18, 0.1)
        bundle(f'roof_along{i}', (x, FRONT, 2.9), (x, BACK, 2.9), 0.16, 0.1)
    for j in range(11):
        y = FRONT + 0.3 + j * (BACK - FRONT - 0.6) / 10
        bundle(f'floor_across{j}', (xa + 0.05, y, 0.24), (xb, y, 0.24), 0.14, 0.08)
        bundle(f'roof_across{j}', (xa + 0.05, y, 2.78), (xb, y, 2.78), 0.14, 0.08)
    # the slits of light: thin white bars behind the far screen and across the roof
    slits = []
    for j in range(9):
        z = 0.5 + j * 0.25
        slits.append(box(f'slit_far{j}', (0.02, BACK - FRONT - 0.3, 0.014), (xb - 0.25, 0.0, z), M['slit'], bev=0, collection=col))
    return slits


def _streak_uv(ob, ax, rnd):
    """The world-line texture laid along the beam: u along its length (metres / 3), v across a random strip of it."""
    me = ob.data; uv = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
    v0 = rnd.random(); M_ = ob.matrix_basis
    for poly in me.polygons:
        for li in poly.loop_indices:
            c = M_ @ me.vertices[me.loops[li].vertex_index].co
            other = [c[i] for i in range(3) if i != ax]
            uv.data[li].uv = (c[ax] / 3.0, v0 + (other[0] + other[1]) * 0.6)


# ---------------------------------------------------------------- the cut
def section(objs, M):
    """Every face the module's cut passes through (the walls' tops), flat and dark."""
    for ob in objs:
        if not ob.name.startswith(('left_', 'back_wall', 'kerb', 'shelf_end', 'shelf_upright', 'stile')): continue
        me = ob.data
        if M['section'].name not in [m.name for m in me.materials if m]: me.materials.append(M['section'])
        k = [m.name if m else '' for m in me.materials].index(M['section'].name)
        for f in me.polygons:
            c = sum((me.vertices[i].co for i in f.vertices), Vector()) / len(f.vertices)
            if f.normal.z > 0.9 and (abs(c.z - RH) < 0.006 or abs(c.z - 3.0) < 0.006): f.material_index = k


# ---------------------------------------------------------------- light
LAMP = (1.0, 0.68, 0.38)                   # the bedside lamp: a warm bulb in a cream shade
DUSK = (0.6, 0.68, 0.82)                   # the evening at the windows
HALL_LIGHT = (1.0, 0.74, 0.46)
SLIT = (0.82, 0.9, 1.0)


def lights(bulb, wins):
    """The bedside lamp (a point in the shade, warm); the evening through each window (a soft area light outside the
    glass, grey-blue); the landing's ceiling light; in the tesseract, the cold light through its slits (area lights
    along the far bundles and over the top). Returns the lights."""
    out = []
    def light(name, kind, loc, energy, colour, rot=None, **kw):
        ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = colour
        for k, v in kw.items(): setattr(ld, k, v)
        ob = cine.link(bpy.data.objects.new(name, ld)); ob.location = loc
        if rot: ob.rotation_euler = rot
        if kind in ('AREA', 'SPOT', 'SUN'): ob.visible_camera = False; ob.visible_glossy = False
        out.append(ob); return ob
    light('lamp', 'POINT', bulb, 60.0, LAMP, shadow_soft_size=0.05)
    for k, (xc, w, z0, z1) in enumerate(wins):                          # an area light shines along its -z: turned into the room
        light(f'window{k}', 'AREA', (xc, BACK + 0.02, (z0 + z1) / 2), 70.0 if k < 2 else 16.0, DUSK, rot=(-math.pi / 2, 0, 0), shape='RECTANGLE', size=w, size_y=z1 - z0)
    light('hall_ceiling', 'POINT', ((HALL[0] + HALL[1]) / 2, 0.6, RH - 0.25), 22.0, HALL_LIGHT, shadow_soft_size=0.08)
    light('tess_far', 'AREA', (RIGHT - 0.1, 0.0, 1.5), 110.0, SLIT, rot=(0, math.pi / 2, 0), shape='RECTANGLE', size=2.6, size_y=BACK - FRONT - 0.4)
    light('tess_top', 'AREA', ((2.7 + RIGHT) / 2, 0.0, 2.97), 45.0, SLIT, shape='RECTANGLE', size=RIGHT - 2.7, size_y=BACK - FRONT - 0.8)
    light('tess_near', 'AREA', (2.0, (BAYS[FALL_BAY][0] + BAYS[FALL_BAY][1]) / 2, 2.75), 45.0, (0.95, 0.88, 0.8), shape='DISK', size=0.8)
    return out
