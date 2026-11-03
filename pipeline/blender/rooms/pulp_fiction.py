# Pulp Fiction · apartment 49, a Hollywood apartment building, one morning: Brett's place, where Jules and Vincent come
# for Marsellus Wallace's briefcase. The rooms after the film's set (dark sage walls, cream doors and trim, a mauve-brown
# carpet; the patchwork sofa, the round dinette, Brett's mustard chair; the pass-through bar with its chrome stools, the
# cream 1950s kitchen behind it) laid out on the plan drawn for the room: the hallway and the bathroom along the back,
# the living room on the left, the kitchen on the right behind the bar. The front door opens off the hallway near its
# left end, where the lift is; the bathroom door is in the same wall, by the bar.
import math, os, random
import bpy, bmesh
from mathutils import Vector, Matrix
import cine
from cine import box, cyl, material, lathe, rounded_slab, moulding
from rooms.seinfeld import uv_rect, tube, circle

W, D = 9.6, 7.6
T = 0.14                                   # the module's walls
LEFT, BACK, RIGHT, FRONT = -W / 2 + T, D / 2 - T, W / 2 - T, -D / 2 + T
RH = 2.75                                  # the ceiling (the walls' cut)
KH = 0.22                                  # the cut-away's kerb
TEX = os.path.join(cine.OUT, 'textures', 'pulp-fiction')
tx = lambda n: os.path.join(TEX, n)

# the plan (true metres)
PART = (2.02, 2.16)                        # the wall between the apartment and the hallway / bathroom (room face, back face)
BATH_X = (0.36, 0.48)                      # the wall between the hallway and the bathroom
LIFT_X = -3.5                              # the lift's front (its car fills the hallway's left end)
LIFT_Y = (2.2, 3.58)                       # its car
LIFT_DOOR = (2.6, 3.32)                    # its doorway (y), facing +x
LIFT_H = 2.1
ENTRY = (-3.25, -2.35)                     # the front door (x), hinged at its right jamb, opening into the room
BATHDOOR = (0.72, 1.48)                    # the bathroom door (x), hinged at its right jamb, opening into the bathroom
DOOR_H = 2.06
BAR = (1.72, 2.16, -0.75, 1.85)            # the pass-through bar: x0, x1 (its body), y0, y1
BAR_TOP = 1.02
WIN = (-2.85, -1.85, 0.8, 2.2)             # the living room's window in the left wall: y0, y1, sill, head
KWIN = (-3.3, -2.4, 0.95, 2.15)            # the kitchen's, in the (cut-away) right wall
TABLE = Vector((-1.45, 0.35)); TABLE_R, TABLE_H = 0.45, 0.74
BRETT_CHAIR = Vector((-0.8, 0.35))         # facing -x, across the table toward Jules
SIDE_CHAIR = Vector((-1.6, 1.22))
STOOLS = [Vector((1.36, 1.38)), Vector((1.36, 0.42))]
SOFA = (-2.6, 0.4, -3.62, -2.8)            # x0, x1, y0 (its back, toward the case), y1 (its front)
SOFA_SEAT = 0.44
CUPBOARD = (0.25, 0.75)                    # the bar's cupboard where the case is kept (y), on the kitchen side
STOVE = (RIGHT - 0.66, RIGHT, -0.78, 0.0)
FRIDGE = (RIGHT - 0.72, RIGHT, -1.98, -1.12)
FRIDGE_H = 1.62


# ---------------------------------------------------------------- materials
def mats():
    M = {}
    M['carpet'] = material('pf_carpet', rough=0.95, maps={'color': tx('carpet_color.jpg'), 'normal': tx('carpet_normal.jpg')}, scale=1.2, normal_strength=0.6, sheen=0.3, sheen_tint=(0.4, 0.32, 0.32))
    M['sage'] = material('pf_sage_wall', rough=0.82, maps={'color': tx('sage_color.jpg'), 'normal': tx('wall_normal.jpg')}, scale=2.0, normal_strength=0.25)
    M['beige'] = material('pf_beige_wall', rough=0.8, maps={'color': tx('beige_color.jpg'), 'normal': tx('wall_normal.jpg')}, scale=2.0, normal_strength=0.25)
    M['tan'] = material('pf_tan_wall', rough=0.8, maps={'color': tx('tan_color.jpg'), 'normal': tx('wall_normal.jpg')}, scale=2.0, normal_strength=0.25)
    M['lino'] = material('pf_linoleum', rough=0.45, maps={'color': tx('lino_color.jpg'), 'normal': tx('lino_normal.jpg')}, scale=1.0, normal_strength=0.3, coat=0.2, coat_rough=0.3)
    M['tile'] = material('pf_tile', rough=0.3, maps={'color': tx('tile_color.jpg'), 'normal': tx('tile_normal.jpg')}, scale=0.9, normal_strength=0.4, coat=0.3, coat_rough=0.15)
    M['trim'] = material('pf_cream_trim', (0.74, 0.69, 0.58), rough=0.4, coat=0.2, coat_rough=0.3)
    M['door'] = material('pf_cream_door', (0.76, 0.71, 0.58), rough=0.42, coat=0.25, coat_rough=0.3)
    M['green_post'] = material('pf_green_paint', (0.16, 0.21, 0.17), rough=0.5, coat=0.2)
    M['brass'] = material('pf_brass', (0.74, 0.55, 0.26), rough=0.3, metal=1.0)
    M['chrome'] = material('pf_chrome', (0.82, 0.82, 0.82), rough=0.14, metal=1.0)
    M['enamel'] = material('pf_white_enamel', (0.8, 0.79, 0.74), rough=0.22, coat=0.6, coat_rough=0.1)
    M['fridge'] = material('pf_fridge_cream', (0.78, 0.72, 0.58), rough=0.3, coat=0.6, coat_rough=0.12)
    M['black'] = material('pf_black', (0.02, 0.02, 0.022), rough=0.4)
    M['laminate'] = material('pf_laminate', rough=0.32, maps={'color': tx('laminate_color.jpg')}, scale=1.0, coat=0.4, coat_rough=0.15)
    M['mustard'] = material('pf_mustard_brocade', rough=0.7, maps={'color': tx('mustard_color.jpg'), 'normal': tx('mustard_normal.jpg')}, scale=0.4, normal_strength=0.5, sheen=0.4, sheen_tint=(0.55, 0.45, 0.25))
    M['vinyl'] = material('pf_cream_vinyl', rough=0.38, maps={'color': tx('vinyl_color.jpg'), 'normal': tx('vinyl_normal.jpg')}, scale=0.5, normal_strength=0.3, coat=0.3, coat_rough=0.2)
    M['patch'] = material('pf_patchwork', rough=0.85, maps={'color': tx('patch_color.jpg')}, scale=1.9, sheen=0.3, sheen_tint=(0.4, 0.3, 0.25))
    M['maroon'] = material('pf_maroon_cushion', (0.26, 0.06, 0.06), rough=0.7, sheen=0.4, sheen_tint=(0.4, 0.2, 0.2))
    M['yellow'] = material('pf_yellow_blanket', rough=0.85, maps={'color': tx('yellow_color.jpg')}, scale=0.6, sheen=0.3, sheen_tint=(0.5, 0.45, 0.3))
    M['tartan'] = material('pf_tartan', rough=0.85, maps={'color': tx('tartan_color.jpg')}, scale=0.6, sheen=0.3, sheen_tint=(0.4, 0.25, 0.25))
    M['nylon'] = material('pf_sleeping_bag', rough=0.5, maps={'color': tx('bag_nylon_color.jpg')}, scale=0.6, coat=0.2)
    M['wood'] = material('pf_brown_wood', (0.22, 0.13, 0.07), rough=0.45, coat=0.3, coat_rough=0.2)
    M['shade'] = material('pf_lamp_shade', (0.84, 0.78, 0.62), rough=0.8)
    M['paper'] = material('pf_paper', (0.84, 0.82, 0.76), rough=0.85)
    M['news'] = material('pf_newsprint', (0.62, 0.6, 0.55), rough=0.9)
    M['blind'] = material('pf_orange_blind', (0.86, 0.46, 0.12), rough=0.7, emission=(1.0, 0.55, 0.16), emission_strength=0.35)
    M['blind_k'] = material('pf_yellow_blind', (0.9, 0.74, 0.3), rough=0.7)
    M['outside'] = material('pf_outside', rough=1.0, maps={'color': tx('outside_color.jpg')}, scale=1.0)
    M['runner'] = material('pf_runner', rough=0.9, maps={'color': tx('runner_color.jpg')}, scale=1.0)
    M['hall_door'] = material('pf_hall_door', (0.24, 0.13, 0.07), rough=0.4, coat=0.3, coat_rough=0.2)
    M['lift'] = material('pf_lift_bronze', (0.36, 0.24, 0.14), rough=0.35, metal=0.8)
    M['glass_drop'] = material('pf_crystal', (0.9, 0.9, 0.88), rough=0.05, coat=1.0, coat_rough=0.02)
    M['bulb'] = material('pf_bulb', (1.0, 0.92, 0.75), rough=0.3, emission=(1.0, 0.82, 0.55), emission_strength=14.0)
    M['stereo'] = material('pf_stereo', (0.05, 0.05, 0.055), rough=0.35, metal=0.2)
    M['chips'] = material('pf_chips_bag', (0.86, 0.6, 0.08), rough=0.3, coat=0.5)
    M['bottle'] = material('pf_bottle', (0.24, 0.12, 0.04), rough=0.15, coat=0.8)
    M['pot'] = material('pf_pot', (0.6, 0.6, 0.6), rough=0.3, metal=0.9)
    M['ceramic'] = material('pf_ceramic', (0.88, 0.86, 0.8), rough=0.2, coat=0.6)
    M['mirror'] = material('pf_mirror', (0.28, 0.3, 0.3), rough=0.04, metal=1.0)
    M['kerb'] = material('pf_kerb', (0.1, 0.08, 0.07), rough=0.9)
    M['section'] = material('section', (0.03, 0.028, 0.026), rough=0.92)
    M['phantom'] = material('pf_phantom_ceiling', (0.72, 0.68, 0.6), rough=0.9)
    return M


def _wall_y(name, x0, x1, y0, y1, holes, mat, col, h=RH, mat_back=None):
    """A wall running along x (x0..x1) between y0 and y1, cut by openings (u0, u1, z0, z1) along x. `mat_back`
    (optional) paints its +y face differently (a thin skin over it)."""
    t = y1 - y0; yc = (y0 + y1) / 2
    xs = sorted({x0, x1} | {o[0] for o in holes} | {o[1] for o in holes}); k = 0
    for a, b in zip(xs, xs[1:]):
        hs = [o for o in holes if o[0] <= a + 1e-6 and o[1] >= b - 1e-6]
        spans = [(0.0, h)] if not hs else [(0.0, hs[0][2]), (hs[0][3], h)]
        for z0, z1 in spans:
            if z1 - z0 < 1e-3: continue
            box(f'{name}_{k}', (b - a, t, z1 - z0), ((a + b) / 2, yc, (z0 + z1) / 2), mat, bev=0, collection=col, lm='arch')
            if mat_back is not None:
                box(f'{name}_{k}_skin', (b - a, 0.004, z1 - z0), ((a + b) / 2, y1 + 0.002, (z0 + z1) / 2), mat_back, bev=0, collection=col, lm='arch')
            k += 1


def _wall_x(name, x0, x1, y0, y1, holes, mat, col, h=RH, mat_back=None):
    """A wall running along y (y0..y1) between x0 and x1, cut by openings (v0, v1, z0, z1) along y; `mat_back` skins
    its +x face."""
    t = x1 - x0; xc = (x0 + x1) / 2
    ys = sorted({y0, y1} | {o[0] for o in holes} | {o[1] for o in holes}); k = 0
    for a, b in zip(ys, ys[1:]):
        hs = [o for o in holes if o[0] <= a + 1e-6 and o[1] >= b - 1e-6]
        spans = [(0.0, h)] if not hs else [(0.0, hs[0][2]), (hs[0][3], h)]
        for z0, z1 in spans:
            if z1 - z0 < 1e-3: continue
            box(f'{name}_{k}', (t, b - a, z1 - z0), (xc, (a + b) / 2, (z0 + z1) / 2), mat, bev=0, collection=col, lm='arch')
            if mat_back is not None:
                box(f'{name}_{k}_skin', (0.004, b - a, z1 - z0), (x1 + 0.002, (a + b) / 2, (z0 + z1) / 2), mat_back, bev=0, collection=col, lm='arch')
            k += 1


# ---------------------------------------------------------------- the shell
def shell(M, arch, phantom):
    """Floors (carpet through the living room, linoleum in the kitchen, tile in the bathroom, the hallway's boards
    under its runner), the module's left and back walls (the living room's window in the left), the wall between the
    apartment and the hallway / bathroom (the front door, the bathroom door), the hallway's wall to the bathroom, the
    lift at the hallway's end; skirting; kerbs; the phantom ceiling, front and right walls (the kitchen window's hole)."""
    box('subfloor', (W, D, 0.02), (0, 0, -0.035), M['kerb'], bev=0, collection=arch, lm='arch')
    for name, x0, x1, y0, y1, mat in (('floor_living', LEFT, BAR[0] + 0.2, FRONT, PART[0], M['carpet']),
                                      ('floor_kitchen', BAR[0] + 0.2, RIGHT, FRONT, PART[0], M['lino']),
                                      ('floor_hall', LEFT, BATH_X[0], PART[1], BACK, M['wood']),
                                      ('floor_bath', BATH_X[1], RIGHT, PART[1], BACK, M['tile'])):
        fl = box(name, (x1 - x0, y1 - y0, 0.03), ((x0 + x1) / 2, (y0 + y1) / 2, -0.015), mat, bev=0, collection=arch, lm='arch')
        cine.world_uv(fl, 1.0)
    # the module's left wall: the hallway's end behind the lift, the living room with its window
    _wall_x('left_wall', -W / 2, LEFT, FRONT - T, BACK, [(WIN[0], WIN[1], WIN[2], WIN[3])], M['sage'], arch)
    # the back wall (the hallway's far side, the bathroom's)
    _wall_y('back_wall', LEFT, BATH_X[0], BACK, D / 2, [], M['tan'], arch)
    _wall_y('back_wall_bath', BATH_X[0], RIGHT, BACK, D / 2, [], M['beige'], arch)
    # the apartment's back wall: sage on the room's side (beige in the kitchen), tan in the hallway, beige in the bathroom
    holes = [(ENTRY[0], ENTRY[1], 0.0, DOOR_H), (BATHDOOR[0], BATHDOOR[1], 0.0, DOOR_H)]
    _wall_y('part_hall', LEFT, BATH_X[0], PART[0], PART[1], [h for h in holes if h[1] < BATH_X[0]], M['sage'], arch, mat_back=M['tan'])
    _wall_y('part_bath', BATH_X[0], BAR[1], PART[0], PART[1], [h for h in holes if h[0] > BATH_X[0]], M['sage'], arch, mat_back=M['beige'])
    _wall_y('part_kitchen', BAR[1], RIGHT, PART[0], PART[1], [], M['beige'], arch)
    _wall_x('hall_bath_wall', BATH_X[0], BATH_X[1], PART[1], BACK, [], M['tan'], arch, mat_back=M['beige'])
    # the lift: its front wall across the hallway's end (bronze doors in the rig), its car behind (a roof: from above
    # the people waiting in it are hidden)
    _wall_x('lift_front', LIFT_X - 0.1, LIFT_X, PART[1], BACK, [(LIFT_DOOR[0], LIFT_DOOR[1], 0.0, LIFT_H)], M['tan'], arch)
    box('lift_roof', (LIFT_X - 0.1 - LEFT, LIFT_Y[1] - LIFT_Y[0] + 0.1, 0.06), ((LEFT + LIFT_X - 0.1) / 2, (LIFT_Y[0] + LIFT_Y[1]) / 2, LIFT_H + 0.25), M['lift'], bev=0, collection=arch, lm='arch')
    for k, y in enumerate((LIFT_Y[0], LIFT_Y[1])):
        box(f'lift_side{k}', (LIFT_X - 0.1 - LEFT, 0.04, LIFT_H + 0.25), ((LEFT + LIFT_X - 0.1) / 2, y, (LIFT_H + 0.25) / 2), M['lift'], bev=0, collection=arch, lm='arch')
    box('lift_floor', (LIFT_X - 0.1 - LEFT, LIFT_Y[1] - LIFT_Y[0], 0.02), ((LEFT + LIFT_X - 0.1) / 2, (LIFT_Y[0] + LIFT_Y[1]) / 2, 0.01), M['lift'], bev=0, collection=arch, lm='arch')
    box('lift_frame_head', (0.05, LIFT_DOOR[1] - LIFT_DOOR[0] + 0.24, 0.16), (LIFT_X + 0.025, (LIFT_DOOR[0] + LIFT_DOOR[1]) / 2, LIFT_H + 0.08), M['lift'], bev=0.003, collection=arch, lm='arch')
    for k, y in enumerate((LIFT_DOOR[0] - 0.06, LIFT_DOOR[1] + 0.06)):
        box(f'lift_frame{k}', (0.05, 0.12, LIFT_H), (LIFT_X + 0.025, y, LIFT_H / 2), M['lift'], bev=0.003, collection=arch, lm='arch')
    box('lift_dial', (0.02, 0.5, 0.12), (LIFT_X + 0.03, (LIFT_DOOR[0] + LIFT_DOOR[1]) / 2, LIFT_H + 0.32), M['brass'], bev=0.003, collection=arch, lm='arch')
    # skirting (cream) round the living room, the kitchen, the hallway
    prof = [(0, 0), (0.016, 0), (0.016, 0.11), (0.008, 0.125), (0, 0.13)]
    runs = [(Vector((LEFT, FRONT, 0)), Vector((LEFT, WIN[0] - 0.0, 0)), (1, 0, 0)), (Vector((LEFT, WIN[1], 0)), Vector((LEFT, PART[0], 0)), (1, 0, 0)),
            (Vector((LEFT, PART[0], 0)), Vector((ENTRY[0], PART[0], 0)), (0, -1, 0)), (Vector((ENTRY[1], PART[0], 0)), Vector((BATHDOOR[0], PART[0], 0)), (0, -1, 0)),
            (Vector((BATHDOOR[1], PART[0], 0)), Vector((RIGHT, PART[0], 0)), (0, -1, 0)),
            (Vector((LIFT_X, PART[1], 0)), Vector((ENTRY[0], PART[1], 0)), (0, 1, 0)), (Vector((ENTRY[1], PART[1], 0)), Vector((BATH_X[0], PART[1], 0)), (0, 1, 0)),
            (Vector((LIFT_X, BACK, 0)), Vector((BATH_X[0], BACK, 0)), (0, -1, 0))]
    for k, (a, b, n) in enumerate(runs):
        moulding(f'skirting{k}', a, b, n, prof, M['trim'], collection=arch, lm='arch')
    # kerbs and phantoms
    box('kerb_front', (W, T, KH), (0, -D / 2 + T / 2, KH / 2), M['kerb'], bev=0.002, collection=arch, lm='arch')
    box('kerb_right', (T, D - 2 * T, KH), (W / 2 - T / 2, 0, KH / 2), M['kerb'], bev=0.002, collection=arch, lm='arch')
    P_ = M['phantom']; ph = lambda name, size, loc, mat=P_: box(name, size, loc, mat, bev=0, collection=phantom, bake_only=1)
    ph('ph_ceiling', (W, D, 0.3), (0, 0, RH + 0.15))
    ph('ph_front', (W, 0.3, RH - KH), (0, FRONT - 0.15, KH + (RH - KH) / 2), M['sage'])
    # the right wall: the kitchen's and the bathroom's, the kitchen window cut in it
    for k, (y0, y1, z0, z1) in enumerate(((FRONT, KWIN[0], KH, RH), (KWIN[1], BACK, KH, RH), (KWIN[0], KWIN[1], KH, KWIN[2]), (KWIN[0], KWIN[1], KWIN[3], RH))):
        ph(f'ph_right{k}', (0.3, y1 - y0, z1 - z0), (RIGHT + 0.15, (y0 + y1) / 2, (z0 + z1) / 2), M['beige'])


# ---------------------------------------------------------------- doors and windows
def door_leaf(name, w, h, M, col, mat=None, num=None, knob_side=1):
    """A five-panel door built about its hinge edge at the origin, closed along +x, its faces toward +y and -y: stiles,
    rails and raised panels (cream, or `mat`), a brass knob both sides at its free edge; the hall side's number."""
    mat = mat or M['door']; t = 0.042; parts = []
    parts.append(box(f'{name}_slab', (w, t, h), (w / 2, 0, h / 2), mat, bev=0.004, collection=col))
    for s in (-1, 1):
        y = s * (t / 2 + 0.004)
        for k, (z0, z1) in enumerate(((0.14, 0.52), (0.62, 1.0), (1.1, 1.48), (1.58, h - 0.12))):
            parts.append(box(f'{name}_panel{s}{k}', (w - 0.24, 0.01, z1 - z0), (w / 2, y, (z0 + z1) / 2), mat, bev=0.01, seg=2, collection=col))
        parts.append(cyl(f'{name}_rose{s}', 0.028, 0.008, (w - 0.07, s * (t / 2 + 0.004), 0.97), M['brass'], rot=(math.pi / 2, 0, 0), seg=18, collection=col))
        kn = lathe(f'{name}_knob{s}', [(0.0, 0.0), (0.009, 0.0), (0.009, 0.035), (0.026, 0.052), (0.024, 0.07), (0.0, 0.075)], M['brass'], loc=(w - 0.07, s * (t / 2 + 0.008), 0.97), seg=16, collection=col)
        kn.rotation_euler = (-s * math.pi / 2, 0, 0); parts.append(kn)
    if num:
        for k, ch in enumerate(num):
            parts.append(box(f'{name}_num{k}', (0.04, 0.006, 0.07), (w / 2 - 0.03 + k * 0.06, t / 2 + 0.006, 1.55), M['brass'], bev=0.001, collection=col))
    return parts


def doorways(M, col):
    """The casings round the front door and the bathroom door (both faces), the lift's; the deadbolt plate."""
    for nm, (x0, x1) in (('entry', ENTRY), ('bath', BATHDOOR)):
        for face, y, s in (('room', PART[0], -1), ('back', PART[1], 1)):
            for k, x in enumerate((x0 - 0.045, x1 + 0.045)):
                box(f'casing_{nm}_{face}{k}', (0.09, 0.022, DOOR_H + 0.09), (x, y + s * 0.011, (DOOR_H + 0.09) / 2), M['trim'], bev=0.003, collection=col, lm='arch')
            box(f'casing_{nm}_{face}_head', (x1 - x0 + 0.24, 0.03, 0.11), ((x0 + x1) / 2, y + s * 0.015, DOOR_H + 0.09 + 0.055), M['trim'], bev=0.004, collection=col, lm='arch')
        for k, x in enumerate((x0 + 0.01, x1 - 0.01)):
            box(f'jamb_{nm}{k}', (0.02, PART[1] - PART[0], DOOR_H), (x, (PART[0] + PART[1]) / 2, DOOR_H / 2), M['trim'], bev=0.002, collection=col, lm='arch')
        box(f'jamb_{nm}_head', (x1 - x0, PART[1] - PART[0], 0.02), ((x0 + x1) / 2, (PART[0] + PART[1]) / 2, DOOR_H - 0.01), M['trim'], bev=0.002, collection=col, lm='arch')
    # a light switch by the front door, the bathroom's by its door
    for k, x in enumerate((ENTRY[0] - 0.22, BATHDOOR[1] + 0.2)):
        box(f'switch{k}', (0.075, 0.008, 0.12), (x, PART[0] - 0.004, 1.2), M['ceramic'], bev=0.002, collection=col, lm='furn')


def windows(M, col):
    """The living room's window in the left wall: a white sash pair, a cross of muntins, the casing and stool; the
    orange roller blind pulled half down, lit by the sun behind it; the morning outside (a backdrop in the wall).
    Returns its opening."""
    y0, y1, z0, z1 = WIN; yc = (y0 + y1) / 2; w = y1 - y0; x = LEFT
    bd = box('outside_living', (0.01, w + 0.1, z1 - z0 + 0.1), (-W / 2 + 0.012, yc, (z0 + z1) / 2), M['outside'], bev=0, collection=col)
    uv_rect(bd, 'x'); bd['backdrop'] = 1; bd.visible_shadow = False          # it glows: the sun passes through it
    fw = 0.05; zm = (z0 + z1) / 2
    for j, (s0, s1, xo) in enumerate(((z0, zm + 0.02, -0.06), (zm - 0.02, z1, -0.03))):
        for (v0, v1, u0, u1) in ((y0, y0 + fw, s0, s1), (y1 - fw, y1, s0, s1), (y0, y1, s0, s0 + fw), (y0, y1, s1 - fw, s1)):
            box(f'win_sash{j}_{v0:.2f}_{u0:.2f}', (0.04, v1 - v0, u1 - u0), (x + xo, (v0 + v1) / 2, (u0 + u1) / 2), M['trim'], bev=0.003, collection=col, lm='furn')
        box(f'win_mullion{j}', (0.025, 0.018, s1 - s0 - 2 * fw), (x + xo, yc, (s0 + s1) / 2), M['trim'], bev=0.002, collection=col, lm='furn')
        box(f'win_bar{j}', (0.025, w - 2 * fw, 0.018), (x + xo, yc, (s0 + s1) / 2), M['trim'], bev=0.002, collection=col, lm='furn')
    cw = 0.08
    for (v0, v1, u0, u1) in ((y0 - cw, y0, z0 - 0.02, z1 + cw), (y1, y1 + cw, z0 - 0.02, z1 + cw), (y0 - cw, y1 + cw, z1, z1 + cw)):
        box(f'win_casing_{v0:.2f}_{u0:.2f}', (0.022, v1 - v0, u1 - u0), (x + 0.011, (v0 + v1) / 2, (u0 + u1) / 2), M['trim'], bev=0.003, collection=col, lm='furn')
    box('win_stool', (0.12, w + 2 * cw + 0.06, 0.025), (x + 0.04, yc, z0 - 0.012), M['trim'], bev=0.004, collection=col, lm='furn')
    # the roller blind, half down, its roller and pull; a dark iron curtain rod over it (no curtains)
    blind_bottom = z0 + (z1 - z0) * 0.45
    box('win_blind', (0.006, w - 0.04, z1 - blind_bottom), (x - 0.085, yc, (z1 + blind_bottom) / 2), M['blind'], bev=0, collection=col)   # it glows: no light map
    cyl('win_blind_roller', 0.022, w - 0.02, (x - 0.085, yc, z1 + 0.01), M['trim'], rot=(math.pi / 2, 0, 0), seg=12, collection=col, lm='furn')
    box('win_blind_slat', (0.012, w - 0.03, 0.02), (x - 0.085, yc, blind_bottom), M['wood'], bev=0.002, collection=col, lm='furn')
    tube('win_blind_pull', [Vector((x - 0.09, yc, blind_bottom)), Vector((x - 0.09, yc, blind_bottom - 0.12))], 0.003, M['wood'], col, seg=6, lm='furn')
    cyl('win_rod', 0.01, w + 0.5, (x - 0.12, yc, z1 + 0.16), M['black'], rot=(math.pi / 2, 0, 0), seg=10, collection=col, lm='furn')
    for s in (-1, 1):
        box(f'win_rod_bracket{s}', (0.12, 0.012, 0.03), (x - 0.06, yc + s * (w / 2 + 0.2), z1 + 0.16), M['black'], bev=0.002, collection=col, lm='furn')
    return WIN


# ---------------------------------------------------------------- the living room
def sofa(M, col):
    """The sofa against the case: its back toward the front (low, tight-upholstered), facing the room; boxy arms; a
    patchwork tweed all over, two maroon pillows at its right end (Roger's head), a yellow blanket thrown over its seat."""
    x0, x1, y0, y1 = SOFA; xc = (x0 + x1) / 2; L = x1 - x0; d = y1 - y0
    box('sofa_base', (L, d, 0.2), (xc, (y0 + y1) / 2, 0.15), M['patch'], bev=0.02, collection=col, lm='furn')
    rounded_slab('sofa_back', L - 0.02, 0.22, 0.48, 0.06, (xc, y0 + 0.11, 0.56), M['patch'], edge_bev=0.04, collection=col, lm='furn')
    for s, x in ((-1, x0 + 0.1), (1, x1 - 0.1)):
        rounded_slab(f'sofa_arm{s}', 0.2, d, 0.36, 0.05, (x, (y0 + y1) / 2, 0.43), M['patch'], edge_bev=0.035, collection=col, lm='furn')
    n = 3; cw = (L - 0.4) / n
    for k in range(n):
        rounded_slab(f'sofa_cushion{k}', cw - 0.01, d - 0.24, 0.15, 0.06, (x0 + 0.2 + cw * (k + 0.5), y0 + 0.22 + (d - 0.24) / 2, 0.33), M['patch'], edge_bev=0.05, collection=col, lm='furn')
    for k in range(4):
        cyl(f'sofa_foot{k}', 0.02, 0.05, (x0 + 0.08 + (L - 0.16) * (k % 2), y0 + 0.08 + (d - 0.16) * (k // 2), 0.025), M['wood'], seg=10, collection=col, lm='furn')
    for k, (x, rz) in enumerate(((x1 - 0.32, 0.25), (x1 - 0.5, -0.3))):
        rounded_slab(f'sofa_pillow{k}', 0.42, 0.14, 0.34, 0.1, (x, y0 + 0.32, 0.56), M['maroon'], rot=(math.radians(-18), 0, rz), edge_bev=0.06, collection=col, lm='furn')
    _throw('sofa_blanket', x0 + 0.35, x0 + 1.25, y0 + 0.22, y1 + 0.02, 0.42, 0.28, M['yellow'], col, seed=5)


def _throw(name, x0, x1, y0, y1, z, hang, mat, col, rumple=0.015, seed=1, nx=24, ny=18):
    """A blanket thrown over a seat: lying over (x0..x1, y0..y1) at z, falling over its front edge (y1) by `hang`."""
    rnd = random.Random(seed); bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); grid = []
    D_ = y1 - y0 + hang
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            u, v = i / nx * (x1 - x0), j / ny * D_
            x, y, zz = x0 + u, y0 + v, z
            if y > y1: zz = z - (y - y1); y = y1 + 0.02 * (y - y1) / hang
            zz += rumple * (math.sin(u * 11 + rnd.random()) * math.sin(v * 8) + rnd.uniform(-0.4, 0.4))
            row.append(bm.verts.new((x, y, zz)))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for l, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))): l[uvl].uv = (ii / nx * (x1 - x0), jj / ny * D_)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        if f.normal.z < -0.2: f.normal_flip()
    ob = cine._mesh_obj(name, bm, mat, col, smooth=True); ob['lm'] = 'furn'
    s = ob.modifiers.new('thick', 'SOLIDIFY'); s.thickness = 0.008
    return ob


def _floor_heap(name, cx, cy, rx, ry, h, mat, col, seed=1, n=26):
    """A soft heap on the floor (a sleeping bag bunched up, a blanket): a low lumpy dome."""
    rnd = random.Random(seed); bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); rings = []
    for j in range(8):
        t = j / 7; r = 1.0 - t * t
        ring = []
        for i in range(n):
            a = 2 * math.pi * i / n; k = 1 + 0.18 * math.sin(a * 3 + seed) + rnd.uniform(-0.06, 0.06)
            ring.append(bm.verts.new((cx + rx * r * k * math.cos(a), cy + ry * r * k * math.sin(a), 0.004 + h * math.sin(t * math.pi / 2) * (0.8 + 0.3 * rnd.random()))))
        rings.append(ring)
    for j in range(7):
        for i in range(n):
            f = bm.faces.new((rings[j][i], rings[j][(i + 1) % n], rings[j + 1][(i + 1) % n], rings[j + 1][i]))
            for l in f.loops: l[uvl].uv = (l.vert.co.x * 2, l.vert.co.y * 2)
    top = bm.verts.new((cx, cy, h + 0.01));
    for i in range(n): bm.faces.new((rings[-1][i], rings[-1][(i + 1) % n], top))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = cine._mesh_obj(name, bm, mat, col, smooth=True); ob['lm'] = 'furn'
    return ob


def living(M, col, rnd):
    """The living room's things: the sofa; the floor lamp and the chrome cantilever chair by the window; the desk on
    the left wall; the side table at the sofa's end (a phone, newspapers); the sleeping bags, the tartan blanket and a
    cushion on the carpet; the built-in cabinet between the doors (open shelves over cupboards: a boom box, two lamps,
    a bag of chips, folded clothes, tapes); the gooseneck lamp by the bathroom door; the cream side chair; the stools
    at the bar; the bird sconce by the front door."""
    sofa(M, col)
    # the floor lamp: a brass column, a cream drum shade (off: morning)
    p = Vector((LEFT + 0.32, FRONT + 0.36, 0))
    lathe('floorlamp', [(0.0, 0.0), (0.15, 0.0), (0.15, 0.02), (0.03, 0.04), (0.012, 1.4), (0.02, 1.42), (0.0, 1.44)], M['brass'], loc=p, seg=20, collection=col, lm='furn')
    lathe('floorlamp_shade', [(0.2, 0.0), (0.205, 0.004), (0.16, 0.26), (0.155, 0.265)], M['shade'], loc=p + Vector((0, 0, 1.3)), seg=32, collection=col, lm='furn')
    # the chrome tube cantilever armchair, a dark seat, turned toward the room
    T_ = Matrix.Translation((LEFT + 1.25, FRONT + 0.5, 0)) @ Matrix.Rotation(math.radians(-140), 4, 'Z')
    parts = [rounded_slab('cant_seat', 0.5, 0.48, 0.06, 0.08, (0, 0, 0.42), M['black'], collection=col, lm='furn'),
             rounded_slab('cant_back', 0.5, 0.05, 0.42, 0.08, (0, 0.24, 0.68), M['black'], rot=(math.radians(-12), 0, 0), collection=col, lm='furn')]
    for s in (-1, 1):
        parts.append(tube(f'cant_frame{s}', [Vector((s * 0.27, -0.3, 0.01)), Vector((s * 0.27, 0.28, 0.01)), Vector((s * 0.27, 0.3, 0.05)), Vector((s * 0.27, -0.22, 0.38)),
                                              Vector((s * 0.27, -0.22, 0.62)), Vector((s * 0.27, 0.12, 0.62))], 0.012, M['chrome'], col, seg=8, lm='furn'))
    tube('cant_tie', [Vector((-0.27, 0.28, 0.01)), Vector((0.27, 0.28, 0.01))], 0.011, M['chrome'], col, seg=8, lm='furn'); parts.append(bpy.data.objects['cant_tie'])
    for o in parts: cine.place(o, T_)
    # the desk on the left wall: a plain wood desk, a lamp, papers, the phone
    y0, y1 = -0.55, 0.65; dx = 0.55; xc = LEFT + dx / 2
    box('desk_top', (dx, y1 - y0, 0.035), (xc, (y0 + y1) / 2, 0.74), M['wood'], bev=0.004, collection=col, lm='furn')
    box('desk_drawers', (dx - 0.04, 0.4, 0.68), (xc, y1 - 0.22, 0.36), M['wood'], bev=0.004, collection=col, lm='furn')
    for j in range(3):
        box(f'desk_drawer{j}', (0.015, 0.36, 0.19), (LEFT + dx - 0.01, y1 - 0.22, 0.13 + j * 0.22), M['wood'], bev=0.004, collection=col, lm='furn')
        cyl(f'desk_pull{j}', 0.01, 0.02, (LEFT + dx + 0.004, y1 - 0.22, 0.13 + j * 0.22), M['brass'], rot=(0, math.pi / 2, 0), seg=10, collection=col, lm='furn')
    for k, y in enumerate((y0 + 0.04,)):
        for j, x in enumerate((LEFT + 0.04, LEFT + dx - 0.04)):
            box(f'desk_leg{k}{j}', (0.035, 0.035, 0.72), (x, y, 0.36), M['wood'], bev=0.002, collection=col, lm='furn')
    for k in range(4):
        box(f'desk_paper{k}', (0.22, 0.29, 0.002), (xc + rnd.uniform(-0.05, 0.05), y0 + 0.35 + rnd.uniform(-0.05, 0.1), 0.759 + k * 0.0015), M['paper'], rot=(0, 0, rnd.uniform(-0.5, 0.5)), bev=0, collection=col, lm='furn')
    lathe('desk_lamp', [(0.0, 0.0), (0.07, 0.0), (0.07, 0.02), (0.012, 0.03), (0.01, 0.34), (0.0, 0.34)], M['brass'], loc=(xc - 0.08, y1 - 0.15, 0.757), seg=14, collection=col, lm='furn')
    lathe('desk_lamp_shade', [(0.11, 0.0), (0.06, 0.13), (0.055, 0.135)], M['shade'], loc=(xc - 0.08, y1 - 0.15, 0.757 + 0.24), seg=24, collection=col, lm='furn')
    _phone('desk_phone', Vector((xc + 0.05, y0 + 0.12, 0.757)), M, col)
    # the side table at the sofa's right end: a 1950s tripod table, a phone, newspapers, a cup
    p = Vector((SOFA[1] + 0.3, FRONT + 0.32, 0))
    box('sidetable_top', (0.48, 0.38, 0.025), p + Vector((0, 0, 0.55)), M['laminate'], bev=0.004, collection=col, lm='furn')
    box('sidetable_shelf', (0.42, 0.32, 0.015), p + Vector((0, 0, 0.18)), M['wood'], bev=0.003, collection=col, lm='furn')
    for sx in (-1, 1):
        for sy in (-1, 1):
            tube(f'sidetable_leg{sx}{sy}', [p + Vector((sx * 0.2, sy * 0.15, 0.55)), p + Vector((sx * 0.25, sy * 0.19, 0.0))], 0.008, M['brass'], col, seg=6, lm='furn')
    for k in range(6):
        box(f'news{k}', (0.32, 0.26, 0.01), p + Vector((rnd.uniform(-0.03, 0.03), rnd.uniform(-0.02, 0.02), 0.2 + k * 0.012)), M['news'], rot=(0, 0, rnd.uniform(-0.3, 0.3)), bev=0.002, collection=col, lm='furn')
    _phone('side_phone', p + Vector((-0.08, 0.02, 0.5625)), M, col)
    # on the carpet: two sleeping bags bunched up, the tartan blanket, a patchwork cushion, a pair of sneakers
    _floor_heap('sleeping_bag0', -1.9, -1.95, 0.62, 0.3, 0.16, M['nylon'], col, seed=3)
    _floor_heap('sleeping_bag1', -1.1, -2.05, 0.5, 0.36, 0.13, M['nylon'], col, seed=4)
    _floor_heap('tartan_blanket', -1.55, -1.55, 0.7, 0.26, 0.06, M['tartan'], col, seed=6)
    rounded_slab('floor_cushion', 0.45, 0.42, 0.12, 0.08, (-0.45, -2.05, 0.06), M['patch'], rot=(0, 0, 0.4), edge_bev=0.05, collection=col, lm='furn')
    for k, (x, y, r) in enumerate(((-2.75, -2.4, 0.3), (-2.62, -2.48, 0.5))):
        rounded_slab(f'sneaker{k}', 0.28, 0.1, 0.09, 0.04, (x, y, 0.045), M['ceramic'], rot=(0, 0, r), edge_bev=0.03, collection=col, lm='furn')
    # the built-in cabinet between the doors: cupboards, a counter, open shelves up to the head of the doors
    x0, x1 = -2.05, -0.25; yb = PART[0]
    box('cab_lower', (x1 - x0, 0.42, 0.88), ((x0 + x1) / 2, yb - 0.21, 0.44), M['trim'], bev=0.004, collection=col, lm='furn')
    box('cab_counter', (x1 - x0 + 0.04, 0.46, 0.03), ((x0 + x1) / 2, yb - 0.23, 0.895), M['trim'], bev=0.004, collection=col, lm='furn')
    nd = 3
    for k in range(nd):
        u0 = x0 + 0.02 + k * (x1 - x0 - 0.04) / nd; u1 = u0 + (x1 - x0 - 0.04) / nd - 0.02
        box(f'cab_door{k}', (u1 - u0, 0.015, 0.7), ((u0 + u1) / 2, yb - 0.425, 0.42), M['trim'], bev=0.004, collection=col, lm='furn')
        cyl(f'cab_knob{k}', 0.012, 0.02, (u1 - 0.05, yb - 0.44, 0.62), M['brass'], rot=(math.pi / 2, 0, 0), seg=10, collection=col, lm='furn')
        box(f'cab_drawer{k}', (u1 - u0, 0.015, 0.1), ((u0 + u1) / 2, yb - 0.425, 0.84), M['trim'], bev=0.003, collection=col, lm='furn')
    for k, x in enumerate((x0, x1)):
        box(f'cab_side{k}', (0.025, 0.3, 1.25), (x, yb - 0.15, 0.91 + 0.625), M['trim'], bev=0.003, collection=col, lm='furn')
    for k, z in enumerate((1.3, 1.68, 2.06)):
        box(f'cab_shelf{k}', (x1 - x0, 0.3, 0.022), ((x0 + x1) / 2, yb - 0.15, z), M['trim'], bev=0.003, collection=col, lm='furn')
    box('cab_back', (x1 - x0, 0.01, 1.25), ((x0 + x1) / 2, yb - 0.005, 0.91 + 0.625), M['trim'], bev=0, collection=col, lm='furn')
    box('boombox', (0.48, 0.16, 0.24), (x0 + 0.38, yb - 0.25, 0.91 + 0.12), M['stereo'], bev=0.01, collection=col, lm='furn')
    for s in (-1, 1): cyl(f'boombox_spk{s}', 0.065, 0.01, (x0 + 0.38 + s * 0.15, yb - 0.335, 1.02), M['black'], rot=(math.pi / 2, 0, 0), seg=18, collection=col, lm='furn')
    for k, x in enumerate((x0 + 0.85, x0 + 1.25)):
        lathe(f'cab_lamp{k}', [(0.0, 0.0), (0.07, 0.0), (0.08, 0.06), (0.05, 0.2), (0.015, 0.24), (0.0, 0.24)], M['ceramic'], loc=(x, yb - 0.22, 0.91), seg=18, collection=col, lm='furn')
        lathe(f'cab_lamp_shade{k}', [(0.14, 0.0), (0.145, 0.004), (0.1, 0.22), (0.095, 0.225)], M['shade'], loc=(x, yb - 0.22, 0.91 + 0.2), seg=24, collection=col, lm='furn')
    rounded_slab('chips', 0.22, 0.07, 0.3, 0.03, (x1 - 0.2, yb - 0.24, 0.91 + 0.15), M['chips'], rot=(0, 0, 0.3), edge_bev=0.02, collection=col, lm='furn')
    for k in range(5):                                                   # folded clothes, tapes and records on the shelves
        box(f'clothes{k}', (0.3, 0.22, 0.06), (x0 + 0.25 + k * 0.32, yb - 0.15, 1.31 + 0.03 + (k % 2) * 0.05), random.choice([M['maroon'], M['nylon'], M['news'], M['tartan']]), bev=0.015, collection=col, lm='furn')
        for j in range(8):
            box(f'tape{k}_{j}', (0.018, 0.12, 0.1), (x0 + 0.1 + k * 0.33 + j * 0.022, yb - 0.12, 1.69 + 0.05), M['stereo'] if j % 3 else M['maroon'], bev=0.001, collection=col, lm='furn')
    # the gooseneck floor lamp by the bathroom door
    p = Vector((0.28, PART[0] - 0.3, 0))
    lathe('gooseneck_base', [(0.0, 0.0), (0.13, 0.0), (0.13, 0.02), (0.02, 0.04), (0.0, 0.04)], M['brass'], loc=p, seg=18, collection=col, lm='furn')
    tube('gooseneck', [p + Vector((0, 0, 0.03)), p + Vector((0, 0, 1.2)), p + Vector((0.04, -0.06, 1.42)), p + Vector((0.14, -0.16, 1.48))], 0.009, M['brass'], col, seg=8, lm='furn')
    lathe('gooseneck_shade', [(0.0, 0.0), (0.04, 0.0), (0.09, 0.09), (0.085, 0.095)], M['brass'], loc=p + Vector((0.16, -0.18, 1.36)), seg=18, collection=col, lm='furn')
    # the cream vinyl side chair behind the table
    _side_chair('side_chair', SIDE_CHAIR, math.radians(200), M['vinyl'], M, col)
    # the stools at the bar: chrome, a cream vinyl seat with a back
    for k, s in enumerate(STOOLS):
        _stool(f'stool{k}', s, M, col)
    # the ceramic bird sconce left of the front door
    p = Vector((ENTRY[0] - 0.5, PART[0] - 0.02, 1.72))
    lathe('sconce_cup', [(0.0, 0.0), (0.04, 0.0), (0.07, 0.08), (0.065, 0.085)], M['ceramic'], loc=p + Vector((0, -0.06, 0)), seg=16, collection=col, lm='furn')
    box('sconce_plate', (0.09, 0.012, 0.16), p + Vector((0, 0, 0.02)), M['ceramic'], bev=0.004, collection=col, lm='furn')
    rounded_slab('sconce_bird', 0.12, 0.03, 0.05, 0.02, p + Vector((0.02, -0.05, 0.15)), M['brass'], rot=(0, 0.3, 0), edge_bev=0.01, collection=col, lm='furn')


def _phone(name, p, M, col):
    """A desk telephone: a dark body, the handset across its cradle, a dial."""
    rounded_slab(f'{name}_body', 0.2, 0.22, 0.09, 0.04, p + Vector((0, 0, 0.045)), M['black'], edge_bev=0.02, collection=col, lm='furn')
    rounded_slab(f'{name}_handset', 0.22, 0.05, 0.04, 0.02, p + Vector((0, 0.04, 0.1)), M['black'], edge_bev=0.015, collection=col, lm='furn')
    cyl(f'{name}_dial', 0.045, 0.01, p + Vector((0, -0.05, 0.095)), M['ceramic'], rot=(math.radians(25), 0, 0), seg=18, collection=col, lm='furn')


def _side_chair(name, at, yaw, seat_mat, M, col, upholstered=False):
    """A dinette side chair: a padded seat and back on chrome or wood legs; facing -y in its own frame, turned `yaw`."""
    T_ = Matrix.Translation((at.x, at.y, 0)) @ Matrix.Rotation(yaw, 4, 'Z')
    parts = [rounded_slab(f'{name}_seat', 0.46, 0.44, 0.08, 0.06, (0, 0, 0.44), seat_mat, edge_bev=0.03, collection=col, lm='furn'),
             rounded_slab(f'{name}_back', 0.44, 0.07, 0.46 if not upholstered else 0.5, 0.08, (0, 0.21, 0.75), seat_mat, rot=(math.radians(-8), 0, 0), edge_bev=0.03, collection=col, lm='furn')]
    legm = M['wood'] if upholstered else M['chrome']
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(tube(f'{name}_leg{sx}{sy}', [Vector((0.2 * sx, 0.18 * sy, 0.0)), Vector((0.19 * sx, 0.17 * sy, 0.41))], 0.014 if upholstered else 0.01, legm, col, seg=8, lm='furn'))
    for o in parts: cine.place(o, T_)
    return parts


def _stool(name, at, M, col):
    """A chrome bar stool: a ring of four splayed legs and a foot ring, a round cream vinyl seat, a low back."""
    h = 0.74; parts = []
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        parts.append(tube(f'{name}_leg{k}', [Vector((0.2 * math.cos(a), 0.2 * math.sin(a), 0.0)), Vector((0.12 * math.cos(a), 0.12 * math.sin(a), h - 0.06))], 0.011, M['chrome'], col, seg=8, lm='furn'))
    parts.append(tube(f'{name}_ring', circle(Vector((0, 0, 0.28)), 0.175, (1, 0, 0), (0, 1, 0), n=24), 0.008, M['chrome'], col, closed=True, seg=6, lm='furn'))
    parts.append(cyl(f'{name}_seat', 0.2, 0.07, (0, 0, h - 0.025), M['vinyl'], seg=28, collection=col, lm='furn'))
    parts.append(rounded_slab(f'{name}_back', 0.34, 0.05, 0.18, 0.05, (0, 0.17, h + 0.22), M['vinyl'], rot=(math.radians(-10), 0, 0), edge_bev=0.02, collection=col, lm='furn'))
    for s in (-1, 1):
        parts.append(tube(f'{name}_backpost{s}', [Vector((s * 0.12, 0.15, h)), Vector((s * 0.12, 0.17, h + 0.14))], 0.008, M['chrome'], col, seg=6, lm='furn'))
    T_ = Matrix.Translation((at.x, at.y, 0)) @ Matrix.Rotation(math.radians(-90), 4, 'Z')   # its back toward the room (the sitter faces the bar)
    for o in parts: cine.place(o, T_)


def brett_chair(M, col):
    """Brett's chair: a mustard-gold brocade upholstered side chair on short wooden legs, facing -x."""
    return _side_chair('brett_chair', BRETT_CHAIR, math.radians(-90), M['mustard'], M, col, upholstered=True)


# ---------------------------------------------------------------- the bar and the kitchen
def bar(M, col):
    """The pass-through bar between the living room and the kitchen: a green-painted body, a cream counter that
    overhangs the living-room side for the stools, a high shelf over it on two posts; cupboards on the kitchen side
    (the case's is a rig part); the posts and header of the opening."""
    x0, x1, y0, y1 = BAR
    box('bar_body', (x1 - x0, y1 - y0, BAR_TOP - 0.03), ((x0 + x1) / 2, (y0 + y1) / 2, (BAR_TOP - 0.03) / 2), M['green_post'], bev=0.004, collection=col, lm='furn')
    box('bar_top', (x1 - x0 + 0.26, y1 - y0 + 0.04, 0.035), ((x0 + x1) / 2 - 0.12, (y0 + y1) / 2, BAR_TOP - 0.0175), M['trim'], bev=0.006, collection=col, lm='furn')
    box('bar_kickplate', (0.02, y1 - y0, 0.1), (x1 + 0.01, (y0 + y1) / 2, 0.05), M['black'], bev=0, collection=col, lm='furn')
    # the cupboards on the kitchen side: three doors (the case's, in the middle, belongs to the rig)
    for k, (v0, v1) in enumerate(((y0 + 0.04, CUPBOARD[0] - 0.02), (CUPBOARD[1] + 0.02, y1 - 0.04))):
        n = max(1, int((v1 - v0) / 0.5))
        for j in range(n):
            a = v0 + j * (v1 - v0) / n; b = a + (v1 - v0) / n - 0.02
            box(f'bar_door{k}{j}', (0.018, b - a, 0.7), (x1 + 0.009, (a + b) / 2, 0.47), M['trim'], bev=0.004, collection=col, lm='furn')
            cyl(f'bar_knob{k}{j}', 0.011, 0.02, (x1 + 0.025, b - 0.05, 0.72), M['brass'], rot=(0, math.pi / 2, 0), seg=10, collection=col, lm='furn')
    box('bar_cupboard_inside', (x1 - x0 - 0.06, CUPBOARD[1] - CUPBOARD[0], 0.68), ((x0 + x1) / 2 + 0.02, (CUPBOARD[0] + CUPBOARD[1]) / 2, 0.46), M['black'], bev=0, collection=col, lm='furn')
    # the high shelf on two chrome posts; the opening's posts up to the header, the header itself
    for k, y in enumerate((y0 + 0.06, y1 - 0.06)):
        cyl(f'bar_post{k}', 0.014, 0.42, ((x0 + x1) / 2, y, BAR_TOP + 0.21), M['chrome'], seg=10, collection=col, lm='furn')
    box('bar_shelf', (0.3, y1 - y0, 0.025), ((x0 + x1) / 2, (y0 + y1) / 2, BAR_TOP + 0.43), M['trim'], bev=0.004, collection=col, lm='furn')
    box('bar_post_low', (x1 - x0, 0.12, BAR_TOP), ((x0 + x1) / 2, y1 + 0.06 + 0.04, BAR_TOP / 2), M['green_post'], bev=0.003, collection=col, lm='arch')


def kitchen(M, col, rnd):
    """The kitchen: base cabinets and a counter with the sink along the back wall turning down the right side, wall
    cabinets over them (cream, chrome pulls); the 1950s white enamel gas range with its pots; the cream General Electric
    fridge, rounded, a chrome handle; liquor bottles and a pot on the range, a toaster, the coffee pot; the small
    crystal chandelier. Returns the chandelier's bulb."""
    yb = PART[0]; top = 0.92
    runs = [((BAR[1] + 0.1, RIGHT - 0.62), (yb - 0.62, yb), 'y'), ((RIGHT - 0.62, RIGHT), (0.12, yb - 0.62), 'x')]
    for k, ((x0, x1), (y0, y1), ax) in enumerate(runs):
        box(f'kit_base{k}', (x1 - x0, y1 - y0, top - 0.1), ((x0 + x1) / 2, (y0 + y1) / 2, (top - 0.1) / 2 + 0.1), M['trim'], bev=0.004, collection=col, lm='furn')
        box(f'kit_toe{k}', (x1 - x0 - (0.06 if ax == 'y' else 0), y1 - y0 - (0.06 if ax == 'x' else 0), 0.1), ((x0 + x1) / 2 + (0.03 if ax == 'x' else 0), (y0 + y1) / 2 - (0.03 if ax == 'y' else 0), 0.05), M['black'], bev=0, collection=col, lm='furn')
        box(f'kit_counter{k}', (x1 - x0 + 0.03, y1 - y0 + 0.03, 0.035), ((x0 + x1) / 2, (y0 + y1) / 2, top + 0.0175), M['tile'], bev=0.004, collection=col, lm='furn')
        L = (x1 - x0) if ax == 'y' else (y1 - y0); n = max(1, int(L / 0.45))
        for j in range(n):
            a = j * L / n + 0.02; b = (j + 1) * L / n - 0.02
            if ax == 'y':
                box(f'kit_door{k}{j}', (b - a, 0.018, 0.62), (x0 + (a + b) / 2, y0 - 0.009, 0.48), M['trim'], bev=0.004, collection=col, lm='furn')
                box(f'kit_pull{k}{j}', (0.08, 0.012, 0.012), (x0 + b - 0.07, y0 - 0.022, 0.72), M['chrome'], bev=0.002, collection=col, lm='furn')
            else:
                box(f'kit_door{k}{j}', (0.018, b - a, 0.62), (x0 - 0.009, y0 + (a + b) / 2, 0.48), M['trim'], bev=0.004, collection=col, lm='furn')
                box(f'kit_pull{k}{j}', (0.012, 0.08, 0.012), (x0 - 0.022, y0 + b - 0.07, 0.72), M['chrome'], bev=0.002, collection=col, lm='furn')
        # the wall cabinets above
        if ax == 'y':
            box(f'kit_wall{k}', (x1 - x0, 0.34, 0.72), ((x0 + x1) / 2, yb - 0.17, 1.86), M['trim'], bev=0.004, collection=col, lm='furn')
            for j in range(n):
                a = j * L / n + 0.02; b = (j + 1) * L / n - 0.02
                box(f'kit_wdoor{k}{j}', (b - a, 0.016, 0.66), (x0 + (a + b) / 2, yb - 0.348, 1.86), M['trim'], bev=0.004, collection=col, lm='furn')
    # the sink in the back counter
    sx = (BAR[1] + 0.1 + RIGHT - 0.62) / 2
    box('kit_sink', (0.6, 0.42, 0.02), (sx, yb - 0.32, top + 0.03), M['enamel'], bev=0.01, collection=col, lm='furn')
    box('kit_sink_bowl', (0.5, 0.34, 0.012), (sx, yb - 0.32, top + 0.025), M['black'], bev=0.01, collection=col, lm='furn')
    tube('kit_tap', [Vector((sx, yb - 0.08, top + 0.04)), Vector((sx, yb - 0.08, top + 0.26)), Vector((sx, yb - 0.24, top + 0.28))], 0.012, M['chrome'], col, seg=8, lm='furn')
    # the range: white enamel, four burners, an oven door, a backguard with a clock; pots and bottles on it
    x0, x1, y0, y1 = STOVE; xc, yc = (x0 + x1) / 2, (y0 + y1) / 2
    box('stove_body', (x1 - x0, y1 - y0, top), (xc, yc, top / 2), M['enamel'], bev=0.01, collection=col, lm='furn')
    box('stove_oven', (0.02, y1 - y0 - 0.12, 0.45), (x0 - 0.01, yc, 0.38), M['enamel'], bev=0.008, collection=col, lm='furn')
    box('stove_handle', (0.02, y1 - y0 - 0.2, 0.02), (x0 - 0.04, yc, 0.64), M['chrome'], bev=0.004, collection=col, lm='furn')
    box('stove_window', (0.004, 0.3, 0.14), (x0 - 0.022, yc, 0.42), M['black'], bev=0.003, collection=col, lm='furn')
    box('stove_backguard', (0.08, y1 - y0, 0.24), (x1 - 0.04, yc, top + 0.12), M['enamel'], bev=0.01, collection=col, lm='furn')
    for k in range(4):
        cyl(f'stove_knob{k}', 0.018, 0.025, (x0 - 0.01, y0 + 0.12 + k * 0.17, 0.83), M['black'], rot=(0, math.pi / 2, 0), seg=12, collection=col, lm='furn')
        bx = xc - 0.12 + (k % 2) * 0.24; by = y0 + 0.2 + (k // 2) * 0.38
        cyl(f'stove_grate{k}', 0.1, 0.012, (bx, by, top + 0.006), M['black'], seg=18, collection=col, lm='furn')
    lathe('pot0', [(0.0, 0.0), (0.1, 0.0), (0.1, 0.12), (0.105, 0.125), (0.0, 0.125)], M['pot'], loc=(xc - 0.12, y0 + 0.2, top + 0.012), seg=20, collection=col, lm='furn')
    tube('pot0_handle', [Vector((xc - 0.12, y0 + 0.1, top + 0.12)), Vector((xc - 0.12, y0 - 0.12, top + 0.13))], 0.008, M['black'], col, seg=6, lm='furn')
    lathe('pot1', [(0.0, 0.0), (0.12, 0.0), (0.12, 0.09), (0.0, 0.09)], M['pot'], loc=(xc + 0.12, y0 + 0.58, top + 0.012), seg=20, collection=col, lm='furn')
    for k, (dx, dy, hh) in enumerate(((-0.05, 0.42, 0.3), (0.0, 0.5, 0.26), (-0.12, 0.55, 0.28))):
        lathe(f'bottle{k}', [(0.0, 0.0), (0.04, 0.0), (0.042, hh * 0.65), (0.015, hh * 0.8), (0.013, hh), (0.0, hh)], M['bottle'], loc=(xc + dx, y0 + dy, top + 0.012), seg=14, collection=col, lm='furn')
    # the fridge: rounded cream body, the freezer door over the main one, the chrome handle and its badge
    x0, x1, y0, y1 = FRIDGE; xc, yc = (x0 + x1) / 2, (y0 + y1) / 2
    rounded_slab('fridge_body', x1 - x0, y1 - y0, FRIDGE_H - 0.06, 0.1, (xc, yc, FRIDGE_H / 2 + 0.03), M['fridge'], rot=(0, 0, math.pi / 2), edge_bev=0.06, collection=col, lm='furn')
    box('fridge_seam', (0.008, y1 - y0 - 0.1, 0.008), (x0 - 0.002, yc, FRIDGE_H * 0.72), M['black'], bev=0, collection=col, lm='furn')
    box('fridge_handle', (0.03, 0.035, 0.36), (x0 - 0.03, y1 - 0.12, FRIDGE_H * 0.5), M['chrome'], bev=0.008, collection=col, lm='furn')
    box('fridge_handle_top', (0.03, 0.24, 0.035), (x0 - 0.03, yc + 0.1, FRIDGE_H * 0.82), M['chrome'], bev=0.008, collection=col, lm='furn')
    box('fridge_badge', (0.006, 0.3, 0.035), (x0 - 0.005, yc, FRIDGE_H * 0.86), M['chrome'], bev=0.002, collection=col, lm='furn')
    box('fridge_foot', (x1 - x0 - 0.04, y1 - y0 - 0.04, 0.06), (xc, yc, 0.03), M['black'], bev=0, collection=col, lm='furn')
    box('fridge_box', (0.3, 0.24, 0.1), (xc, yc, FRIDGE_H + 0.05), M['maroon'], bev=0.004, collection=col, lm='furn')
    # on the counter: a toaster, a coffee pot, a jar
    box('toaster', (0.26, 0.16, 0.18), (BAR[1] + 0.45, yb - 0.3, top + 0.12), M['chrome'], bev=0.03, collection=col, lm='furn')
    lathe('coffee_pot', [(0.0, 0.0), (0.07, 0.0), (0.075, 0.12), (0.05, 0.2), (0.0, 0.22)], M['pot'], loc=(RIGHT - 0.3, 0.7, top + 0.035), seg=16, collection=col, lm='furn')
    # the small crystal chandelier over the kitchen
    c = Vector(((BAR[1] + RIGHT) / 2, 0.2, RH))
    tube('chand_rod', [c, c - Vector((0, 0, 0.3))], 0.006, M['brass'], col, seg=6, lm='furn')
    lathe('chand_body', [(0.0, 0.0), (0.05, 0.02), (0.06, 0.06), (0.0, 0.08)], M['brass'], loc=c - Vector((0, 0, 0.38)), seg=14, collection=col, lm='furn')
    for k in range(5):
        a = 2 * math.pi * k / 5; p = c - Vector((0, 0, 0.36)) + Vector((math.cos(a), math.sin(a), 0)) * 0.16
        tube(f'chand_arm{k}', [c - Vector((0, 0, 0.36)), p], 0.005, M['brass'], col, seg=6, lm='furn')
        lathe(f'chand_cup{k}', [(0.0, 0.0), (0.02, 0.0), (0.025, 0.03), (0.0, 0.03)], M['glass_drop'], loc=p, seg=10, collection=col, lm='furn')
        lathe(f'chand_drop{k}', [(0.0, 0.0), (0.012, 0.02), (0.0, 0.05)], M['glass_drop'], loc=p - Vector((0, 0, 0.07)), seg=8, collection=col, lm='furn')
        lathe(f'chand_bulb{k}', [(0.0, 0.0), (0.012, 0.0), (0.01, 0.04), (0.0, 0.05)], M['bulb'], loc=p + Vector((0, 0, 0.03)), seg=8, collection=col)
    return c - Vector((0, 0, 0.3))


# ---------------------------------------------------------------- the hallway and the bathroom
def hallway(M, col):
    """The building's hallway: a long red runner, two neighbours' doors in the far wall (dark wood, brass numbers),
    two ceiling fixtures; the lift at its end. Returns the fixtures' places."""
    x0, x1 = LIFT_X, BATH_X[0]
    box('hall_runner', (x1 - x0 - 0.3, 0.8, 0.006), ((x0 + x1) / 2, (PART[1] + BACK) / 2, 0.003), M['runner'], bev=0.001, collection=col, lm='furn')
    for k, x in enumerate((-2.6, -0.9)):
        for o in door_leaf(f'hall_door{k}', 0.86, DOOR_H, M, col, mat=M['hall_door'], num='48' if k == 0 else '50'):
            o.rotation_euler = (0, 0, math.pi); o.location = Vector((x + 0.43, BACK - 0.02, 0)) + Matrix.Rotation(math.pi, 3, 'Z') @ o.location
            o['lm'] = 'furn'
        for s in (-1, 1):
            box(f'hall_door{k}_casing{s}', (0.08, 0.02, DOOR_H + 0.08), (x + s * 0.47, BACK - 0.01, (DOOR_H + 0.08) / 2), M['trim'], bev=0.003, collection=col, lm='arch')
        box(f'hall_door{k}_head', (1.02, 0.025, 0.08), (x, BACK - 0.012, DOOR_H + 0.08), M['trim'], bev=0.003, collection=col, lm='arch')
    lights = []
    for k, x in enumerate((-2.9, -1.1)):
        p = Vector((x, (PART[1] + BACK) / 2, RH))
        lathe(f'hall_fixture{k}', [(0.0, -0.1), (0.16, -0.06), (0.17, 0.0), (0.0, 0.0)], M['ceramic'], loc=p, seg=20, collection=col)
        lights.append(p - Vector((0, 0, 0.14)))
    return lights


def bathroom(M, col):
    """The bathroom: a white tub along the back wall, the toilet, a pedestal sink with a mirror cabinet over it, a towel
    on its rail; a bare bulb over the mirror. Returns the bulb."""
    x0, x1 = 2.95, RIGHT - 0.02
    box('tub', (x1 - x0, 0.72, 0.55), ((x0 + x1) / 2, BACK - 0.36, 0.275), M['enamel'], bev=0.04, collection=col, lm='furn')
    box('tub_inside', (x1 - x0 - 0.14, 0.58, 0.02), ((x0 + x1) / 2, BACK - 0.36, 0.53), M['ceramic'], bev=0.04, collection=col, lm='furn')
    t = Vector((2.35, BACK - 0.3, 0))
    lathe('toilet_bowl', [(0.0, 0.0), (0.12, 0.0), (0.14, 0.3), (0.2, 0.4), (0.0, 0.4)], M['enamel'], loc=t + Vector((0, -0.12, 0)), seg=20, collection=col, lm='furn')
    box('toilet_tank', (0.44, 0.18, 0.36), t + Vector((0, 0.16, 0.6)), M['enamel'], bev=0.02, collection=col, lm='furn')
    s = Vector((1.05, BACK - 0.26, 0))
    lathe('sink_pedestal', [(0.0, 0.0), (0.1, 0.0), (0.06, 0.6), (0.0, 0.62)], M['enamel'], loc=s, seg=18, collection=col, lm='furn')
    box('sink_basin', (0.56, 0.42, 0.14), s + Vector((0, 0, 0.78)), M['enamel'], bev=0.04, collection=col, lm='furn')
    box('mirror_cabinet', (0.46, 0.12, 0.6), s + Vector((0, 0.18, 1.5)), M['trim'], bev=0.006, collection=col, lm='furn')
    box('mirror', (0.4, 0.004, 0.54), s + Vector((0, 0.118, 1.5)), M['mirror'], bev=0, collection=col, lm='furn')
    tube('towel_rail', [Vector((x0 - 0.4, BACK - 0.05, 1.1)), Vector((x0 - 0.05, BACK - 0.05, 1.1))], 0.01, M['chrome'], col, seg=8, lm='furn')
    box('towel', (0.3, 0.03, 0.5), (x0 - 0.22, BACK - 0.07, 0.86), M['maroon'], bev=0.01, collection=col, lm='furn')
    bulb = s + Vector((0, 0.1, 1.95))
    lathe('bath_bulb', [(0.0, -0.03), (0.03, 0.0), (0.024, 0.04), (0.0, 0.05)], M['bulb'], loc=bulb, seg=12, collection=col)
    return bulb


# ---------------------------------------------------------------- the cut
def section(objs, M):
    """Every face the module's cut passes through (the walls' tops), flat and dark."""
    for ob in objs:
        if not ob.name.startswith(('left_', 'back_wall', 'part_', 'hall_bath', 'lift_front', 'kerb', 'bar_header')): continue
        me = ob.data
        if M['section'].name not in [m.name for m in me.materials if m]: me.materials.append(M['section'])
        k = [m.name if m else '' for m in me.materials].index(M['section'].name)
        for f in me.polygons:
            c = sum((me.vertices[i].co for i in f.vertices), Vector()) / len(f.vertices)
            if f.normal.z > 0.9 and abs(c.z - RH) < 0.006: f.material_index = k


# ---------------------------------------------------------------- light
SUN = (1.0, 0.86, 0.66)                    # a warm morning sun through the living room's window
SKY = (0.78, 0.86, 1.0)
WARM = (1.0, 0.76, 0.5)


def lights(chand, hall, bath_bulb):
    """The sun through the living room's window (hard, low, laying the window's shape across the carpet and onto the
    cabinet), the sky at that window and the kitchen's (soft area lights outside the glass); the kitchen's chandelier,
    the hallway's ceiling fixtures, the bathroom's bulb."""
    out = []
    def light(name, kind, loc, energy, colour, rot=None, **kw):
        ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = colour
        for k, v in kw.items(): setattr(ld, k, v)
        ob = cine.link(bpy.data.objects.new(name, ld)); ob.location = loc
        if rot: ob.rotation_euler = rot
        if kind in ('AREA', 'SPOT', 'SUN'): ob.visible_camera = False; ob.visible_glossy = False
        out.append(ob); return ob
    sd = Vector((1.0, 0.42, -0.62)).normalized()                       # toward +x, a little to the back, down
    light('sun', 'SUN', (0, 0, 5), 6.0, SUN, rot=sd.to_track_quat('-Z', 'Y').to_euler(), angle=math.radians(1.2))
    y0, y1, z0, z1 = WIN
    light('window_sky', 'AREA', (LEFT - 0.05, (y0 + y1) / 2, (z0 + z1) / 2), 220.0, SKY, rot=(0, math.pi / 2, 0), shape='RECTANGLE', size=z1 - z0, size_y=y1 - y0)
    y0, y1, z0, z1 = KWIN
    light('kitchen_window', 'AREA', (RIGHT + 0.05, (y0 + y1) / 2, (z0 + z1) / 2), 180.0, (1.0, 0.94, 0.84), rot=(0, -math.pi / 2, 0), shape='RECTANGLE', size=z1 - z0, size_y=y1 - y0)
    light('chandelier', 'POINT', chand - Vector((0, 0, 0.1)), 35.0, WARM, shadow_soft_size=0.12)
    for k, p in enumerate(hall):
        light(f'hall{k}', 'POINT', p, 30.0, WARM, shadow_soft_size=0.1)
    light('bath_bulb', 'POINT', bath_bulb, 28.0, WARM, shadow_soft_size=0.04)
    return out
