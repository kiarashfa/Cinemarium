# Rear Window · Jefferies' studio apartment in the Village, an evening at dusk. (Built in a frame mirrored left to
# right, then turned over by MIRROR at the end of the build: seen from the courtyard, the room's west wall is on the
# right. The constants below are in the build frame; mx() gives a point's place in the room.) The rear window is the case's glass:
# the visitor stands in the courtyard, where the neighbours are, and Jeff in his wheelchair at the window's west end
# looks out at us through his long lens. The room as the film has it, its window wall cut to the sill: the daybed
# along the window, the pleated floor lamp at its head; on the west wall (left) the kitchenette by the window (the
# sink under a small window onto the brick of a light well, a bamboo blind, the cylinder sconce, the bar's bottles)
# and the built-in bookcases; on the south wall (the back) the low built-ins with their round brass pulls, the
# mahogany desk with its grey-shaded lamp and cameras under three framed photographs of his assignments, the coat
# hooks with his parka; on the east wall (a partition, right) the cream fireplace with the bright still life over
# it and the hall door; the armchair and the celadon lamp before it. Beyond the partition, the building's hall
# (Lisa's way in and out), and behind the back wall the stairwell, out of sight. Dark walnut boards, plaster
# painted a warm grey-green putty, cream-grey built-ins, mahogany and brass; the dusk at the window.
import math, os, random
import bpy, bmesh
from mathutils import Vector, Matrix
import cine
from cine import box, cyl, material, lathe, rounded_slab, moulding
from rooms.seinfeld import uv_rect, tube, circle

W, D = 9.6, 7.6
T = 0.14                                   # the module's walls
LEFT, BACK, RIGHT, FRONT = -W / 2 + T, D / 2 - T, W / 2 - T, -D / 2 + T
RH = 3.0                                   # the studio's ceiling (a parlour floor: the module's top)
KH = 0.22                                  # the cut-away's kerb (the window wall, cut at the sill)
TEX = os.path.join(cine.OUT, 'textures', 'rear-window')
tx = lambda n: os.path.join(TEX, n)
PH = os.path.join(cine.CACHE, 'polyhaven')

# the plan (true metres)
BW, BW1 = 2.60, 2.74                       # the south wall (the desk's, the door's): its room face, its back
PX0, PX1 = 2.30, 2.44                      # the east partition (the fireplace's, the hall door's): room face, hall face
P_FULL = -0.60                             # the partition is full height from here back (a kerb in front)
DOOR = (1.55, 2.45)                        # the hall door in the partition (y); hinged at its back jamb
DOOR_H = 2.13
STAIR = (2.95, 3.95)                       # the stairwell's doorway in the south wall (x), the hall's far end
FIRE_Y = 0.35                              # the fireplace's centre on the partition
P_W = -2.20                                # the west wall is full height from here back (a low wall in front, by the window)
WEST_LOW = 1.02
KITCH = (-2.10, -0.80)                     # the kitchenette along the west wall (y), just behind Jeff
KWIN = (-1.75, -1.15, 1.22, 1.98)          # its small window over the sink, onto the light well (y0, y1, z0, z1)
SHELF_Y = (-0.30, 2.00)                    # the built-in bookcases on the west wall
DESK_X = (-2.72, -1.30)
DESK_TOP = 0.76
BED_X = (-2.30, -0.30)                     # the daybed along the window
BED_Y = (-3.58, -2.74)
BED_TOP = 0.50
CHAIR = Vector((-3.12, -2.48))             # Jeff's wheelchair: the seat's centre, facing the window
CHAIR_F = Vector((0.22, -1.0)).normalized()
STAND = Vector((-2.50, -2.18))             # the little table at Jeff's right: the ice bucket, two glasses
STAND_TOP = 0.64
PLEAT = Vector((0.06, -3.22))              # the pleated floor lamp at the daybed's head
ARMCHAIR = (Vector((1.62, -1.32)), Vector((-0.86, 0.5)).normalized())
SIDE_TABLE = Vector((1.98, -0.42))         # beside the armchair: the celadon lamp
MIRROR = True


def mx(v):
    """A point (or direction) of the build frame in the room: x turned over."""
    v = Vector(v); v.x = -v.x if MIRROR else v.x; return v


# ---------------------------------------------------------------- materials
def mats():
    M = {}
    M['floor'] = material('walnut_boards', rough=0.45, maps={'color': tx('floor_color.jpg'), 'normal': tx('floor_normal.jpg')}, scale=2.0, normal_strength=0.4, coat=0.2, coat_rough=0.3)
    M['wall'] = material('putty_plaster', rough=0.82, maps={'color': tx('wall_color.jpg'), 'normal': tx('wall_normal.jpg')}, scale=2.0, normal_strength=0.25)
    M['trim'] = material('cream_paint', rough=0.5, maps={'color': tx('trim_color.jpg')}, scale=1.0, coat=0.15)
    M['mahogany'] = material('mahogany', rough=0.35, maps={'color': tx('mahogany_color.jpg'), 'normal': tx('mahogany_normal.jpg')}, scale=1.0, normal_strength=0.3, coat=0.4, coat_rough=0.15)
    M['dark_wood'] = material('dark_wood', (0.05, 0.032, 0.02), rough=0.4, coat=0.3)
    M['brass'] = material('brass', (0.78, 0.58, 0.28), rough=0.28, metal=1.0)
    M['iron'] = material('black_iron', (0.025, 0.025, 0.025), rough=0.5, metal=0.6)
    M['chrome'] = material('chrome', (0.82, 0.82, 0.82), rough=0.14, metal=1.0)
    M['brick'] = material('brick', rough=0.85, maps={'color': tx('brick_color.jpg'), 'normal': tx('brick_normal.jpg')}, scale=1.2, normal_strength=0.7)
    M['lightwell'] = material('lightwell_brick', rough=0.9, maps={'color': tx('lightwell_color.jpg')}, scale=1.2)
    M['rug'] = material('rug', rough=0.92, maps={'color': tx('rug_color.jpg')}, scale=1.6, sheen=0.3, sheen_tint=(0.4, 0.3, 0.28))
    M['linen'] = material('daybed_linen', rough=0.85, maps={'color': tx('linen_color.jpg')}, scale=0.6, sheen=0.3, sheen_tint=(0.4, 0.4, 0.4))
    M['pillow'] = material('cushion_lilac', rough=0.85, maps={'color': tx('pillow_color.jpg')}, scale=0.6, sheen=0.3, sheen_tint=(0.4, 0.38, 0.4))
    M['armchair'] = material('armchair_velour', rough=0.8, maps={'color': tx('armchair_color.jpg')}, scale=0.6, sheen=0.4, sheen_tint=(0.4, 0.35, 0.3))
    M['blind'] = material('bamboo_blind', rough=0.7, maps={'color': tx('blind_color.jpg')}, scale=1.0)
    M['books'] = material('books', rough=0.6, maps={'color': tx('books_color.jpg')}, scale=1.0)
    M['basket'] = material('basket', rough=0.85, maps={'color': tx('basket_color.jpg')}, scale=1.0)
    M['still'] = material('still_life', rough=0.55, maps={'color': tx('still_life.jpg')}, scale=1.0)
    for k in ('fighter', 'race', 'smoke'): M[f'photo_{k}'] = material(f'photo_{k}', rough=0.35, maps={'color': tx(f'photo_{k}.jpg')}, scale=1.0, coat=0.5)
    M['frame_black'] = material('frame_black', (0.03, 0.028, 0.026), rough=0.35, coat=0.3)
    M['frame_pale'] = material('frame_pale', (0.62, 0.6, 0.54), rough=0.5)
    M['enamel'] = material('sink_enamel', (0.8, 0.8, 0.77), rough=0.2, coat=0.8)
    M['linoleum'] = material('counter_lino', (0.32, 0.36, 0.33), rough=0.4, coat=0.3)
    M['paper'] = material('paper', (0.82, 0.8, 0.74), rough=0.8)
    M['magazine'] = material('magazines', (0.7, 0.3, 0.24), rough=0.6)
    M['bakelite'] = material('bakelite', (0.02, 0.02, 0.02), rough=0.25, coat=0.6)
    M['bottle_green'] = material('bottle_green', (0.04, 0.12, 0.06), rough=0.12, coat=1.0)
    M['bottle_amber'] = material('bottle_amber', (0.22, 0.09, 0.02), rough=0.12, coat=1.0)
    M['bottle_clear'] = material('bottle_clear', (0.5, 0.52, 0.48), rough=0.1, coat=1.0)
    M['label'] = material('label', (0.82, 0.78, 0.66), rough=0.6)
    M['ice_bucket'] = material('ice_bucket', (0.82, 0.82, 0.82), rough=0.22, metal=1.0)
    M['parka'] = material('parka_olive', (0.2, 0.2, 0.12), rough=0.85, sheen=0.3, sheen_tint=(0.3, 0.3, 0.25))
    M['fur'] = material('parka_fur', (0.42, 0.34, 0.24), rough=0.95, sheen=0.6, sheen_tint=(0.5, 0.45, 0.35))
    M['leather'] = material('leather_brown', rough=0.5, maps={'color': tx('leather_color.jpg')}, scale=0.5, coat=0.2)
    M['spindle'] = material('spindle_maple', (0.55, 0.38, 0.16), rough=0.35, coat=0.5)
    M['celadon'] = material('celadon', (0.42, 0.55, 0.46), rough=0.18, coat=0.8)
    M['hall_wall'] = material('hall_plaster', (0.46, 0.42, 0.34), rough=0.85)
    M['hall_floor'] = material('hall_tile', (0.4, 0.38, 0.34), rough=0.5)
    M['kerb'] = material('kerb', (0.12, 0.09, 0.07), rough=0.9)
    M['section'] = material('section', (0.03, 0.028, 0.026), rough=0.92)
    M['phantom'] = material('phantom_ceiling', (0.62, 0.6, 0.54), rough=0.9)
    M['void'] = material('stair_dark', (0.02, 0.018, 0.016), rough=0.95)
    # the lamps' shades and bulbs: dark until Lisa switches them on (each pass and the web light its own)
    M['shade_pleat'] = material('shade_pleat', (0.86, 0.74, 0.46), rough=0.75, emission=(1.0, 0.78, 0.46), emission_strength=0.0)
    M['shade_drum'] = material('shade_drum', (0.88, 0.86, 0.8), rough=0.75, emission=(1.0, 0.8, 0.55), emission_strength=0.0)
    M['shade_grey'] = material('shade_grey', (0.42, 0.42, 0.4), rough=0.75, emission=(1.0, 0.78, 0.5), emission_strength=0.0)
    M['bulb'] = material('bulb_off', (0.9, 0.88, 0.8), rough=0.3, emission=(1.0, 0.8, 0.55), emission_strength=0.0)
    M['sconce'] = material('sconce_glass', (0.85, 0.84, 0.8), rough=0.4)
    M['hall_bulb'] = material('hall_bulb', (1.0, 0.86, 0.6), rough=0.3, emission=(1.0, 0.8, 0.5), emission_strength=6.0)
    return M


def _tag(objs, **props):
    for o in objs:
        for k, v in props.items(): o[k] = v
    return objs


# ---------------------------------------------------------------- walls
def _wall_y(name, x0, x1, y0, y1, holes, mat, col, h=RH, lm='arch'):
    """A wall along x (from x0 to x1), y0..y1 thick, cut by openings (x0, x1, z0, z1)."""
    xs = sorted({x0, x1} | {a for a, b, c, d in holes} | {b for a, b, c, d in holes}); k = 0
    for a, b in zip(xs, xs[1:]):
        hs = [o for o in holes if o[0] <= a + 1e-6 and o[1] >= b - 1e-6]
        spans = [(0.0, h)] if not hs else [(0.0, hs[0][2]), (hs[0][3], h)]
        for z0, z1 in spans:
            if z1 - z0 < 1e-3: continue
            box(f'{name}_{k}', (b - a, y1 - y0, z1 - z0), ((a + b) / 2, (y0 + y1) / 2, (z0 + z1) / 2), mat, bev=0, collection=col, lm=lm); k += 1


def _wall_x(name, x0, x1, y0, y1, holes, mat, col, h=RH, lm='arch'):
    """A wall along y (from y0 to y1), x0..x1 thick, cut by openings (y0, y1, z0, z1)."""
    ys = sorted({y0, y1} | {a for a, b, c, d in holes} | {b for a, b, c, d in holes}); k = 0
    for a, b in zip(ys, ys[1:]):
        hs = [o for o in holes if o[0] <= a + 1e-6 and o[1] >= b - 1e-6]
        spans = [(0.0, h)] if not hs else [(0.0, hs[0][2]), (hs[0][3], h)]
        for z0, z1 in spans:
            if z1 - z0 < 1e-3: continue
            box(f'{name}_{k}', (x1 - x0, b - a, z1 - z0), ((x0 + x1) / 2, (a + b) / 2, (z0 + z1) / 2), mat, bev=0, collection=col, lm=lm); k += 1


def shell(M, arch, phantom):
    """The floors (the studio's walnut boards, the hall's tile, the stairwell dark), the module's left wall (the
    kitchenette's window cut in it, the light well's brick behind), the south wall across the whole width (the
    stairwell's doorway at the hall's end), the module's back wall behind the stairwell, the east partition (full
    height from P_FULL back, its door; a kerb in front), the window wall cut to the sill (cream inside, brick out),
    the hall's kerb; skirting; the phantoms: the ceilings and the window wall above the sill (its opening open)."""
    box('subfloor', (W, D, 0.02), (0, 0, -0.035), M['kerb'], bev=0, collection=arch, lm='arch')
    fl = box('floor_room', (PX0 - LEFT, BW - FRONT, 0.03), ((LEFT + PX0) / 2, (FRONT + BW) / 2, -0.015), M['floor'], bev=0, collection=arch, lm='arch')
    cine.world_uv(fl, 1.0)
    box('floor_door', (PX1 - PX0, DOOR[1] - DOOR[0], 0.03), ((PX0 + PX1) / 2, sum(DOOR) / 2, -0.015), M['floor'], bev=0, collection=arch, lm='arch')
    box('floor_hall', (RIGHT - PX1, BW - FRONT, 0.03), ((PX1 + RIGHT) / 2, (FRONT + BW) / 2, -0.015), M['hall_floor'], bev=0, collection=arch, lm='arch')
    box('floor_stair', (W - 2 * T, BACK - BW1, 0.03), (0, (BW1 + BACK) / 2, -0.015), M['void'], bev=0, collection=arch, lm='arch')
    box('floor_stairdoor', (STAIR[1] - STAIR[0], BW1 - BW, 0.03), (sum(STAIR) / 2, (BW + BW1) / 2, -0.015), M['hall_floor'], bev=0, collection=arch, lm='arch')
    # the module's left wall, the kitchenette's window in it; the light well's brick close behind (a backdrop)
    # (in the room it is the right edge of the module, full height: its outside is the building's brick, onto the light well)
    _wall_x('left_wall', -W / 2 + 0.1, LEFT, P_W, BW, [KWIN], M['wall'], arch)
    _wall_x('left_wallbrick', -W / 2, -W / 2 + 0.1, P_W, BW, [KWIN], M['brick'], arch)
    _wall_x('kerb_west', -W / 2 + 0.1, LEFT, FRONT, P_W, [], M['wall'], arch, h=WEST_LOW)
    _wall_x('kerb_westbrick', -W / 2, -W / 2 + 0.1, FRONT, P_W, [], M['brick'], arch, h=WEST_LOW)
    box('kerb_west_cap', (T + 0.03, P_W - FRONT, 0.03), (-W / 2 + T / 2 + 0.015, (FRONT + P_W) / 2, WEST_LOW + 0.015), M['trim'], bev=0.004, collection=arch, lm='arch')
    box('left_wall_back', (T, BACK + T - BW, RH), (-W / 2 + T / 2, (BW + D / 2) / 2, RH / 2), M['void'], bev=0, collection=arch, lm='arch')
    lw = box('lightwell', (0.01, KWIN[1] - KWIN[0] + 0.2, KWIN[3] - KWIN[2] + 0.2), (-W / 2 + 0.006, (KWIN[0] + KWIN[1]) / 2, (KWIN[2] + KWIN[3]) / 2), M['lightwell'], bev=0, collection=arch, lm='arch')
    cine.world_uv(lw, 1.0)
    # the south wall, the stairwell's doorway at the hall's far end; the module's back wall beyond the stairwell
    _wall_y('back_wall', LEFT, RIGHT, BW, BW1, [(STAIR[0], STAIR[1], 0.0, 2.2)], M['wall'], arch)
    box('back_module', (W, T, RH), (0, D / 2 - T / 2, RH / 2), M['void'], bev=0, collection=arch, lm='arch')
    # the east partition: full height behind P_FULL, the hall door in it; a kerb in front of it
    _wall_x('back_partition', PX0, PX1, P_FULL, BW, [(DOOR[0], DOOR[1], 0.0, DOOR_H)], M['wall'], arch)
    box('kerb_partition', (PX1 - PX0, P_FULL - FRONT, KH), ((PX0 + PX1) / 2, (FRONT + P_FULL) / 2, KH / 2), M['trim'], bev=0.002, collection=arch, lm='arch')
    # the window wall, cut at the kerb: the sill board inside, the brick face outside
    box('kerb_front', (W, 0.07, KH), (0, -D / 2 + 0.035, KH / 2), M['brick'], bev=0.002, collection=arch, lm='arch')
    box('kerb_front_in', (PX0 - LEFT, T - 0.07, KH), ((LEFT + PX0) / 2, FRONT - (T - 0.07) / 2, KH / 2), M['trim'], bev=0.002, collection=arch, lm='arch')
    box('kerb_front_hall', (RIGHT - PX0, T - 0.07, KH), ((PX0 + RIGHT) / 2, FRONT - (T - 0.07) / 2, KH / 2), M['hall_wall'], bev=0.002, collection=arch, lm='arch')
    box('kerb_sill', (PX0 - LEFT, 0.2, 0.03), ((LEFT + PX0) / 2, FRONT + 0.03, KH + 0.015), M['trim'], bev=0.004, collection=arch, lm='arch')
    box('left_hallwall', (T, BACK + T - FRONT, RH), (W / 2 - T / 2, (FRONT + BACK + T) / 2, RH / 2), M['hall_wall'], bev=0, collection=arch, lm='arch')
    # the hall's faces: its own colour on the partition's hall side and the south wall's hall stretch
    box('hall_face_partition', (0.004, BW - P_FULL, RH), (PX1 + 0.002, (P_FULL + BW) / 2, RH / 2), M['hall_wall'], bev=0, collection=arch, lm='arch')
    for k, (a, b) in enumerate(((PX1, STAIR[0]), (STAIR[1], RIGHT))):
        box(f'hall_face_back{k}', (b - a, 0.004, RH), ((a + b) / 2, BW - 0.002, RH / 2), M['hall_wall'], bev=0, collection=arch, lm='arch')
    box('hall_face_back_head', (STAIR[1] - STAIR[0], 0.004, RH - 2.2), (sum(STAIR) / 2, BW - 0.002, (RH + 2.2) / 2), M['hall_wall'], bev=0, collection=arch, lm='arch')
    # skirting round the studio
    prof = [(0, 0), (0.016, 0), (0.016, 0.14), (0.008, 0.155), (0, 0.16)]
    runs = [((LEFT, FRONT + 0.14), (LEFT, KITCH[0]), (1, 0, 0)), ((LEFT, KITCH[1]), (LEFT, BW), (1, 0, 0)),
            ((LEFT, BW), (PX0, BW), (0, -1, 0)), ((PX0, P_FULL), (PX0, DOOR[0]), (-1, 0, 0)), ((PX0, DOOR[1]), (PX0, BW), (-1, 0, 0))]
    for k, (a, b, n) in enumerate(runs):
        moulding(f'skirting{k}', Vector((*a, 0)), Vector((*b, 0)), n, prof, M['trim'], collection=arch, lm='arch')
    # phantoms: the ceilings (studio, hall, stairwell), the window wall above the sill with the window's opening, the
    # hall's missing outer wall
    P_ = M['phantom']; ph = lambda name, size, loc, mat=P_: box(name, size, loc, mat, bev=0, collection=phantom, bake_only=1)
    ph('ph_ceiling', (W, D, 0.3), (0, 0, RH + 0.15))
    WIN = WINDOW_X
    for k, (a, b) in enumerate(((-W / 2, WIN[0]), (WIN[1], PX1))):
        ph(f'ph_front{k}', (b - a, 0.3, RH - KH), ((a + b) / 2, FRONT - 0.15, KH + (RH - KH) / 2), M['wall'])
    ph('ph_front_head', (WIN[1] - WIN[0], 0.3, RH - WIN_HEAD), (sum(WIN) / 2, FRONT - 0.15, (RH + WIN_HEAD) / 2), M['wall'])
    ph('ph_front_hall', (RIGHT - PX1 + T, 0.3, RH - KH), ((PX1 + W / 2) / 2, FRONT - 0.15, KH + (RH - KH) / 2), M['hall_wall'])
    ph('ph_west_front', (0.3, P_W - FRONT, RH - WEST_LOW), (-W / 2 - 0.15, (FRONT + P_W) / 2, WEST_LOW + (RH - WEST_LOW) / 2), M['wall'])
    ph('ph_partition_front', (PX1 - PX0, P_FULL - FRONT, RH - KH), ((PX0 + PX1) / 2, (FRONT + P_FULL) / 2, KH + (RH - KH) / 2), M['wall'])


WINDOW_X = (-4.2, 0.9)                     # the rear window's opening in the (phantom) window wall: the bay of casements
WIN_HEAD = 2.55


# ---------------------------------------------------------------- the daybed and Jeff's corner
def daybed(M, col):
    """The daybed along the window: a low dark wooden frame on square legs, a mattress in grey linen with a piped
    edge, two lilac-grey pillows at its head (by the pleated lamp), a rolled bolster at its foot."""
    xa, xb = BED_X; ya, yb = BED_Y; xc, yc = (xa + xb) / 2, (ya + yb) / 2
    box('daybed_frame', (xb - xa, yb - ya, 0.1), (xc, yc, 0.27), M['dark_wood'], bev=0.006, collection=col, lm='furn')
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(f'daybed_leg{sx}{sy}', (0.05, 0.05, 0.22), (xc + sx * ((xb - xa) / 2 - 0.05), yc + sy * ((yb - ya) / 2 - 0.05), 0.11), M['dark_wood'], bev=0.004, collection=col, lm='furn')
    rounded_slab('daybed_mattress', xb - xa - 0.02, yb - ya - 0.02, BED_TOP - 0.32, 0.05, (xc, yc, (BED_TOP + 0.32) / 2), M['linen'], edge_bev=0.03, collection=col, lm='furn')
    for k, (x, y, rz) in enumerate(((xb - 0.2, yc - 0.14, 0.1), (xb - 0.16, yc + 0.16, -0.1))):
        rounded_slab(f'daybed_pillow{k}', 0.34, 0.36, 0.1, 0.09, (x, y, BED_TOP + 0.08), M['pillow'], rot=(0.0, math.radians(-35), rz), edge_bev=0.035, collection=col, lm='furn')
    cyl('daybed_bolster', 0.07, yb - ya - 0.12, (xa + 0.1, yc, BED_TOP + 0.06), M['pillow'], rot=(math.pi / 2, 0, 0), seg=20, collection=col, lm='furn')


def jeff_corner(M, col):
    """At Jeff's right the little round table with the silver ice bucket (the bottle in it, a white napkin over its
    rim) and two glasses; the Poly Haven wheelchair is placed in furniture(). Returns the prop places (for the rig)."""
    p = STAND
    lathe('stand_top', [(0.0, 0.0), (0.24, 0.0), (0.245, 0.012), (0.24, 0.025), (0.0, 0.025)], M['mahogany'], loc=(p.x, p.y, STAND_TOP - 0.025), seg=32, collection=col, lm='furn')
    lathe('stand_column', [(0.03, 0.08), (0.022, 0.2), (0.032, 0.35), (0.02, 0.5), (0.03, STAND_TOP - 0.03), (0.0, STAND_TOP - 0.03)], M['mahogany'], loc=(p.x, p.y, 0), seg=14, collection=col, lm='furn')
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.4; d = Vector((math.cos(a), math.sin(a), 0))
        tube(f'stand_foot{k}', [Vector((p.x, p.y, 0.12)), Vector((p.x, p.y, 0)) + d * 0.2 + Vector((0, 0, 0.02))], 0.016, M['mahogany'], col, seg=8, lm='furn')
    return {'bucket': Vector((p.x - 0.06, p.y + 0.05, STAND_TOP)), 'glass_a': Vector((p.x + 0.1, p.y - 0.1, STAND_TOP)), 'glass_b': Vector((p.x + 0.14, p.y + 0.06, STAND_TOP))}


# ---------------------------------------------------------------- the west wall: kitchenette and bookcases
def kitchenette(M, col):
    """The kitchenette by the window: a cream base cabinet (two doors, round brass knobs) with a green linoleum top
    and a white enamel sink; the small window over it onto the light well (cream sash, a bamboo blind half down); a
    shelf of bottles and glasses (the bar) beside it; the cylinder sconce on the wall between it and the shelves."""
    y0, y1 = KITCH; d = 0.58; xc = LEFT + d / 2; yc = (y0 + y1) / 2
    box('kitch_base', (d, y1 - y0, 0.86), (xc, yc, 0.43), M['trim'], bev=0.004, collection=col, lm='furn')
    box('kitch_top', (d + 0.03, y1 - y0 + 0.02, 0.035), (xc + 0.015, yc, 0.877), M['linoleum'], bev=0.003, collection=col, lm='furn')
    for k, (a, b) in enumerate(((y0 + 0.04, yc - 0.01), (yc + 0.01, y1 - 0.04))):
        box(f'kitch_door{k}', (0.02, b - a, 0.62), (LEFT + d + 0.008, (a + b) / 2, 0.45), M['trim'], bev=0.006, collection=col, lm='furn')
        cyl(f'kitch_knob{k}', 0.014, 0.02, (LEFT + d + 0.025, b - 0.06 if k == 0 else a + 0.06, 0.66), M['brass'], rot=(0, math.pi / 2, 0), seg=12, collection=col, lm='furn')
    box('kitch_toe', (0.02, y1 - y0 - 0.02, 0.1), (LEFT + d - 0.05, yc, 0.05), M['dark_wood'], bev=0, collection=col, lm='furn')
    sc = Vector((LEFT + 0.3, (KWIN[0] + KWIN[1]) / 2, 0.9))
    rounded_slab('sink_rim', 0.46, 0.5, 0.025, 0.04, sc + Vector((0, 0, 0.0)), M['enamel'], edge_bev=0.008, collection=col, lm='furn')
    rounded_slab('sink_bowl', 0.38, 0.42, 0.012, 0.05, sc + Vector((0, 0, -0.16)), M['enamel'], edge_bev=0.004, collection=col, lm='furn')
    tube('sink_tap', [sc + Vector((-0.2, 0, 0.0)), sc + Vector((-0.2, 0, 0.2)), sc + Vector((-0.08, 0, 0.22)), sc + Vector((-0.05, 0, 0.17))], 0.012, M['chrome'], col, seg=10, lm='furn')
    # the small window: a cream frame, a sash bar, the blind half down
    a, b, z0, z1 = KWIN
    for k, (u0, u1, v0, v1) in enumerate(((a - 0.06, a, z0 - 0.03, z1 + 0.06), (b, b + 0.06, z0 - 0.03, z1 + 0.06), (a - 0.06, b + 0.06, z1, z1 + 0.06))):
        box(f'kwin_casing{k}', (0.022, u1 - u0, v1 - v0), (LEFT + 0.011, (u0 + u1) / 2, (v0 + v1) / 2), M['trim'], bev=0.003, collection=col, lm='furn')
    box('kwin_stool', (0.12, b - a + 0.16, 0.025), (LEFT + 0.05, (a + b) / 2, z0 - 0.015), M['trim'], bev=0.003, collection=col, lm='furn')
    for k, (u0, u1, v0, v1) in enumerate(((a, a + 0.045, z0, z1), (b - 0.045, b, z0, z1), (a, b, z0, z0 + 0.045), (a, b, z1 - 0.045, z1), (a, b, (z0 + z1) / 2 - 0.02, (z0 + z1) / 2 + 0.02))):
        box(f'kwin_sash{k}', (0.04, u1 - u0, v1 - v0), (LEFT - 0.05, (u0 + u1) / 2, (v0 + v1) / 2), M['trim'], bev=0.002, collection=col, lm='furn')
    bl = box('kwin_blind', (0.012, b - a + 0.04, (z1 - z0) * 0.48), (LEFT + 0.03, (a + b) / 2, z1 - (z1 - z0) * 0.24), M['blind'], bev=0, collection=col, lm='furn')
    uv_rect(bl, 'x')
    cyl('kwin_blind_roll', 0.025, b - a + 0.06, (LEFT + 0.035, (a + b) / 2, z1 - (z1 - z0) * 0.48), M['blind'], rot=(math.pi / 2, 0, 0), seg=12, collection=col, lm='furn')
    # the bar: a shelf over the counter's far end, bottles on it and on the counter
    box('bar_shelf', (0.24, 0.62, 0.025), (LEFT + 0.12, y1 - 0.36, 1.5), M['trim'], bev=0.003, collection=col, lm='furn')
    rnd = random.Random(7)
    for k in range(9):
        on_shelf = k < 5
        y = y1 - 0.62 + 0.11 * (k if on_shelf else k - 5) + 0.06; z = 1.513 if on_shelf else 0.895
        x = LEFT + 0.1 + (0 if on_shelf else 0.12)
        mat = (M['bottle_green'], M['bottle_amber'], M['bottle_clear'])[k % 3]
        h = rnd.uniform(0.24, 0.32)
        lathe(f'bar_bottle{k}', [(0.0, 0.0), (0.036, 0.0), (0.038, h * 0.62), (0.014, h * 0.8), (0.012, h), (0.0, h)], mat, loc=(x, y, z), seg=14, collection=col, lm='furn')
        cyl(f'bar_label{k}', 0.0385, h * 0.22, (x, y, z + h * 0.34), M['label'], seg=14, bev=0, collection=col, lm='furn')
    # the cylinder sconce: a white glass drum on a brass arm
    s = Vector((LEFT + 0.12, KITCH[1] + 0.22, 1.78))
    box('sconce_plate', (0.02, 0.08, 0.12), (LEFT + 0.01, s.y, s.z), M['brass'], bev=0.003, collection=col, lm='furn')
    tube('sconce_arm', [Vector((LEFT + 0.02, s.y, s.z)), s], 0.008, M['brass'], col, seg=8, lm='furn')
    cyl('sconce_drum', 0.06, 0.2, s + Vector((0, 0, 0.03)), M['sconce'], seg=20, collection=col, lm='furn')


def bookcases(M, col, rnd):
    """The built-in bookcases on the west wall: cream cupboards below (doors, round brass knobs) and open shelves
    above to 2.3 m, books packed and leaning, brass jugs and a carved elephant among them, framed snapshots; the
    round basket-shield on the wall past them."""
    y0, y1 = SHELF_Y; d = 0.36; xf = LEFT + d; xc = LEFT + d / 2; top = 2.32
    box('shelf_case', (d, y1 - y0, 0.84), (xc, (y0 + y1) / 2, 0.42), M['trim'], bev=0.004, collection=col, lm='furn')
    nb = 4; bw = (y1 - y0) / nb
    for i in range(nb):
        a, b = y0 + i * bw + 0.02, y0 + (i + 1) * bw - 0.02
        box(f'shelf_cup{i}', (0.02, b - a, 0.66), (xf + 0.008, (a + b) / 2, 0.45), M['trim'], bev=0.008, collection=col, lm='furn')
        cyl(f'shelf_knob{i}', 0.015, 0.02, (xf + 0.026, b - 0.06, 0.6), M['brass'], rot=(0, math.pi / 2, 0), seg=12, collection=col, lm='furn')
    box('shelf_counter', (d + 0.03, y1 - y0 + 0.02, 0.03), (xc + 0.015, (y0 + y1) / 2, 0.855), M['trim'], bev=0.004, collection=col, lm='furn')
    for i in range(nb + 1):
        y = y0 + i * bw
        box(f'shelf_upright{i}', (d - 0.06, 0.03, top - 0.87), (LEFT + (d - 0.06) / 2, y, (top + 0.87) / 2), M['trim'], bev=0.003, collection=col, lm='furn')
    shelves = [0.87, 1.24, 1.6, 1.96, top - 0.03]
    for z in shelves:
        box(f'shelf_board{int(z * 100)}', (d - 0.06, y1 - y0, 0.024), (LEFT + (d - 0.06) / 2, (y0 + y1) / 2, z + 0.012), M['trim'], bev=0.003, collection=col, lm='furn')
    box('shelf_cornice', (d - 0.02, y1 - y0 + 0.06, 0.08), (LEFT + (d - 0.02) / 2, (y0 + y1) / 2, top + 0.04), M['trim'], bev=0.004, collection=col, lm='furn')
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); ornaments = []
    for i in range(nb):
        a, b = y0 + i * bw + 0.03, y0 + (i + 1) * bw - 0.03
        for j, z in enumerate(shelves[:-1]):
            room = shelves[j + 1] - z - 0.04; y = a
            while y < b - 0.02:
                r = rnd.random()
                if r < 0.07 and b - y > 0.22:                                  # an ornament: a brass jug or a snapshot
                    ornaments.append((Vector((LEFT + 0.16, y + 0.09, z + 0.024)), rnd.random())); y += 0.2; continue
                if r < 0.13:                                                    # a stack lying flat
                    w_ = rnd.uniform(0.16, 0.22); zz = z + 0.024
                    if y + w_ > b: break
                    for _ in range(rnd.randint(2, 5)):
                        th = rnd.uniform(0.02, 0.04)
                        if zz + th > z + room: break
                        _book(bm, uvl, LEFT + 0.04, y, y + w_, zz, th, rnd.uniform(0.18, 0.24), rnd, flat=True); zz += th
                    y += w_ + 0.005; continue
                th = rnd.uniform(0.018, 0.05); h = min(room, rnd.uniform(0.18, 0.3)); dp = rnd.uniform(0.15, 0.24)
                if y + th > b: break
                _book(bm, uvl, LEFT + 0.03 + (0.25 - dp), y, y + th, z + 0.024, h, dp, rnd)
                y += th + rnd.uniform(0.0, 0.004)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = cine._mesh_obj('books_shelved', bm, M['books'], col, smooth=False); ob['lm'] = 'furn'
    for k, (p, r) in enumerate(ornaments):
        if r < 0.5:
            lathe(f'shelf_jug{k}', [(0.0, 0.0), (0.05, 0.0), (0.06, 0.06), (0.04, 0.15), (0.03, 0.2), (0.045, 0.24), (0.0, 0.24)], M['brass'], loc=p, seg=18, collection=col, lm='furn')
        else:
            box(f'shelf_snap{k}', (0.015, 0.13, 0.17), p + Vector((0, 0, 0.085)), M['frame_black'], rot=(0, -0.2, 0), bev=0.003, collection=col, lm='furn')


def _book(bm, uvl, xf, y0, y1, z, h, d, rnd, flat=False):
    """A book as a box, its spine toward the room (+x) taking a random cell of the spine atlas."""
    x0, x1 = xf, xf + d; z0, z1 = z, z + h
    v = [bm.verts.new((x, y, zz)) for x in (x0, x1) for y in (y0, y1) for zz in (z0, z1)]
    i_, j_ = rnd.randrange(32), rnd.randrange(4)
    cu0, cu1 = i_ / 64, (i_ + 1) / 64 - 0.002; cv0, cv1 = j_ / 4 + 0.01, (j_ + 1) / 4 - 0.01
    def face(ids, uv):
        f = bm.faces.new([v[k] for k in ids])
        for l, q in zip(f.loops, uv): l[uvl].uv = q
    spine = [(cu0, cv0), (cu1, cv0), (cu1, cv1), (cu0, cv1)] if not flat else [(cu0, cv0), (cu0, cv1), (cu1, cv1), (cu1, cv0)]
    pg = [(0.6, 0.1), (0.68, 0.1), (0.68, 0.9), (0.6, 0.9)]
    face((4, 5, 7, 6), spine); face((0, 2, 3, 1), pg); face((1, 3, 7, 5), pg); face((0, 4, 6, 2), pg)
    cov = [(cu0, cv0), (cu0 + 0.001, cv0), (cu0 + 0.001, cv1), (cu0, cv1)]
    face((0, 1, 5, 4), cov); face((2, 6, 7, 3), cov)


def _basket(name, c, n, r, M, col):
    """A round woven basket-shield hung flat on a wall: a shallow dish, its face the coiled pattern."""
    n = Vector(n).normalized(); prof = [(0.0, 0.03), (r * 0.5, 0.028), (r * 0.9, 0.015), (r, 0.0), (r * 0.96, -0.005), (0.0, 0.0)]
    ob = lathe(name, [(a, b) for a, b in prof], M['basket'], loc=(0, 0, 0), seg=40, collection=col, lm='furn')
    me = ob.data; uv = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co; uv.data[li].uv = (0.5 + co.x / (2 * r), 0.5 + co.y / (2 * r))
    q = Vector((0, 0, 1)).rotation_difference(n); ob.rotation_mode = 'QUATERNION'; ob.rotation_quaternion = q; ob.location = c
    return ob


# ---------------------------------------------------------------- the south wall: built-ins, desk, photographs
def south_wall(M, col, rnd):
    """Along the back: the low built-ins (cream, round brass pulls) with magazines stacked on them; the mahogany desk
    on turned legs, its grey-shaded lamp, the broken camera, a flash, papers, the black telephone; the yellow spindle
    chair; the three photographs over it; the coat hooks by the corner with the parka, the camera bag, the umbrella.
    Returns the desk lamp's bulb."""
    yb = BW
    for k, (a, b) in enumerate(((LEFT + 0.02, -3.0), (0.25, 1.45))):
        d = 0.46; yc = yb - d / 2; xc = (a + b) / 2
        box(f'builtin{k}', (b - a, d, 0.74), (xc, yc, 0.37), M['trim'], bev=0.004, collection=col, lm='furn')
        box(f'builtin{k}_top', (b - a + 0.02, d + 0.02, 0.03), (xc, yc - 0.01, 0.755), M['trim'], bev=0.004, collection=col, lm='furn')
        n = max(1, int((b - a) / 0.5))
        for j in range(n):
            u0 = a + (b - a) * j / n + 0.03; u1 = a + (b - a) * (j + 1) / n - 0.03
            box(f'builtin{k}_drawer{j}', (u1 - u0, 0.02, 0.26), ((u0 + u1) / 2, yb - d - 0.008, 0.54), M['trim'], bev=0.006, collection=col, lm='furn')
            box(f'builtin{k}_door{j}', (u1 - u0, 0.02, 0.34), ((u0 + u1) / 2, yb - d - 0.008, 0.2), M['trim'], bev=0.006, collection=col, lm='furn')
            cyl(f'builtin{k}_pull{j}', 0.03, 0.012, ((u0 + u1) / 2, yb - d - 0.024, 0.54), M['brass'], rot=(math.pi / 2, 0, 0), seg=18, collection=col, lm='furn')
        for s in range(3):                                                     # stacks of magazines
            x = a + 0.25 + s * (b - a - 0.5) / 2; h = rnd.uniform(0.08, 0.2)
            box(f'builtin{k}_mags{s}', (0.3, 0.24, h), (x, yb - 0.24, 0.77 + h / 2), M['magazine'] if s % 2 else M['paper'], rot=(0, 0, rnd.uniform(-0.1, 0.1)), bev=0.002, collection=col, lm='furn')
    # the desk
    xa, xb = DESK_X; dd = 0.62; yc = yb - dd / 2 - 0.02; xc = (xa + xb) / 2
    box('desk_top', (xb - xa, dd, 0.035), (xc, yc, DESK_TOP - 0.018), M['mahogany'], bev=0.006, collection=col, lm='furn')
    box('desk_apron', (xb - xa - 0.08, dd - 0.08, 0.1), (xc, yc, DESK_TOP - 0.085), M['mahogany'], bev=0.004, collection=col, lm='furn')
    for k in range(2):
        box(f'desk_drawer{k}', (0.5, 0.02, 0.08), (xc + (k - 0.5) * 0.6, yc - dd / 2 + 0.03, DESK_TOP - 0.085), M['mahogany'], bev=0.004, collection=col, lm='furn')
        cyl(f'desk_pull{k}', 0.012, 0.02, (xc + (k - 0.5) * 0.6, yc - dd / 2 + 0.015, DESK_TOP - 0.085), M['brass'], rot=(math.pi / 2, 0, 0), seg=10, collection=col, lm='furn')
    for sx in (-1, 1):
        for sy in (-1, 1):
            lathe(f'desk_leg{sx}{sy}', [(0.028, 0.0), (0.02, 0.06), (0.03, 0.12), (0.022, 0.2), (0.034, 0.34), (0.024, 0.52), (0.03, DESK_TOP - 0.14), (0.0, DESK_TOP - 0.14)],
                  M['mahogany'], loc=(xc + sx * ((xb - xa) / 2 - 0.05), yc + sy * (dd / 2 - 0.05), 0), seg=14, collection=col, lm='furn')
    # on the desk: the lamp (a black ceramic urn, a grey drum shade), papers, the broken camera, a flash, the telephone
    lp = Vector((xb - 0.22, yb - 0.24, DESK_TOP))
    lathe('desk_lamp_base', [(0.0, 0.0), (0.08, 0.0), (0.08, 0.02), (0.06, 0.04), (0.09, 0.14), (0.05, 0.26), (0.02, 0.3), (0.012, 0.42), (0.0, 0.42)], M['bakelite'], loc=lp, seg=24, collection=col, role='mug')
    lathe('desk_lamp_shade', [(0.22, 0.0), (0.225, 0.004), (0.16, 0.24), (0.155, 0.244)], M['shade_grey'], loc=lp + Vector((0, 0, 0.34)), seg=36, collection=col)
    bulb = lp + Vector((0, 0, 0.44))
    lathe('desk_lamp_bulb', [(0.0, -0.03), (0.03, 0.0), (0.024, 0.04), (0.0, 0.05)], M['bulb'], loc=bulb, seg=12, collection=col)
    for k in range(6):
        box(f'desk_paper{k}', (0.22, 0.29, 0.002), (xc - 0.2 + rnd.uniform(-0.1, 0.1), yc + rnd.uniform(-0.1, 0.08), DESK_TOP + 0.001 + k * 0.0016), M['paper'], rot=(0, 0, rnd.uniform(-0.5, 0.5)), bev=0, collection=col, lm='furn')
    cam = Vector((xa + 0.3, yc + 0.05, DESK_TOP))                              # the broken press camera: a black box, its bellows burst
    box('desk_camera', (0.2, 0.14, 0.16), cam + Vector((0, 0, 0.08)), M['bakelite'], rot=(0, 0, 0.5), bev=0.006, collection=col, lm='furn')
    box('desk_camera_front', (0.14, 0.04, 0.14), cam + Vector((0.07, -0.1, 0.07)), M['iron'], rot=(0.3, 0.2, 0.9), bev=0.004, collection=col, lm='furn')
    cyl('desk_flash', 0.06, 0.04, cam + Vector((0.22, 0.12, 0.25)), M['chrome'], rot=(1.2, 0, 0.4), r2=0.02, seg=20, collection=col, lm='furn')
    cyl('desk_flash_grip', 0.02, 0.22, cam + Vector((0.22, 0.12, 0.11)), M['bakelite'], seg=12, collection=col, lm='furn')
    _telephone('desk_phone', Vector((xa + 0.15, yc - 0.18, DESK_TOP)), M, col)
    # the spindle chair, pulled out from the desk
    _spindle_chair('desk_chair', Matrix.Translation((xc - 0.1, yc - 0.62, 0)) @ Matrix.Rotation(math.pi + 0.35, 4, 'Z'), M, col)
    # the three photographs over the desk, black frames, white mats printed in
    for k, (name, dx) in enumerate((('photo_fighter', -0.62), ('photo_race', 0.0), ('photo_smoke', 0.62))):
        c = Vector((xc + dx, yb - 0.015, 1.72))
        box(f'{name}_frame', (0.56, 0.025, 0.46), c, M['frame_black'], bev=0.004, collection=col, lm='furn')
        pr = box(f'{name}_print', (0.5, 0.004, 0.4), c + Vector((0, -0.015, 0)), M[name], bev=0, collection=col, lm='furn'); uv_rect(pr, 'y')
    # the coat hooks by the corner: a board of brass hooks, the parka, the camera bag, an umbrella
    hx = 1.78; box('hooks_board', (0.7, 0.025, 0.1), (hx, yb - 0.013, 1.78), M['trim'], bev=0.003, collection=col, lm='furn')
    for k in range(3): tube(f'hook{k}', [Vector((hx - 0.25 + k * 0.25, yb - 0.025, 1.76)), Vector((hx - 0.25 + k * 0.25, yb - 0.08, 1.8))], 0.006, M['brass'], col, seg=6, lm='furn')
    p = cine.cloth_panel('parka', 0.52, 1.0, 3, 0.06, M['parka'], loc=(hx - 0.25, yb - 0.1, 1.7), collection=col, gather=0.75, seed=3); p['lm'] = 'furn'
    s = p.modifiers.new('t', 'SOLIDIFY'); s.thickness = 0.03
    for k, (dx, dz, r) in enumerate(((-0.1, 1.74, 0.09), (0.0, 1.78, 0.1), (0.1, 1.74, 0.09), (0.0, 1.66, 0.11))):   # the hood's fur, bunched at the hook
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=14, ring_count=8, location=(hx - 0.25 + dx, yb - 0.13, dz))
        o = bpy.context.active_object; o.name = f'parka_fur{k}'; o.scale = (1.0, 0.6, 0.8); o.data.materials.append(M['fur']); o['lm'] = 'furn'
        for c_ in o.users_collection: c_.objects.unlink(o)
        col.objects.link(o)
    box('camera_bag', (0.24, 0.1, 0.2), (hx + 0.02, yb - 0.08, 1.38), M['leather'], bev=0.02, collection=col, lm='furn')
    tube('camera_bag_strap', [Vector((hx - 0.08, yb - 0.08, 1.46)), Vector((hx, yb - 0.08, 1.78)), Vector((hx + 0.12, yb - 0.08, 1.46))], 0.006, M['leather'], col, seg=6, lm='furn')
    tube('umbrella', [Vector((hx + 0.26, yb - 0.08, 1.76)), Vector((hx + 0.3, yb - 0.12, 0.02))], 0.022, M['bakelite'], col, seg=10, lm='furn')
    _basket('basket_south', Vector((-3.6, yb - 0.02, 1.7)), (0, -1, 0), 0.28, M, col)
    # more of his pictures: a second row over the built-ins, smaller prints in black frames
    for k, (x, z, w, h, ph_) in enumerate(((-4.05, 1.32, 0.34, 0.26, 'race'), (-2.98, 1.38, 0.3, 0.38, 'smoke'), (0.55, 1.4, 0.42, 0.32, 'fighter'),
                                           (1.1, 1.62, 0.3, 0.24, 'race'), (0.62, 1.86, 0.28, 0.2, 'smoke'))):
        c = Vector((x, yb - 0.015, z))
        box(f'print{k}_frame', (w + 0.05, 0.022, h + 0.05), c, M['frame_black'], bev=0.003, collection=col, lm='furn')
        pr = box(f'print{k}', (w, 0.004, h), c + Vector((0, -0.013, 0)), M[f'photo_{ph_}'], bev=0, collection=col, lm='furn'); uv_rect(pr, 'y')
    # a photographer's tripod by the bookcases, a reflector flood on a stand, a leather case on the floor
    tp = Vector((-3.55, 1.85, 0))
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.3
        tube(f'tripod_leg{k}', [tp + Vector((math.cos(a) * 0.34, math.sin(a) * 0.34, 0)), tp + Vector((0, 0, 1.18))], 0.011, M['chrome'], col, seg=8, lm='furn')
    tube('tripod_column', [tp + Vector((0, 0, 1.1)), tp + Vector((0, 0, 1.4))], 0.015, M['chrome'], col, seg=8, lm='furn')
    box('tripod_head', (0.08, 0.08, 0.06), tp + Vector((0, 0, 1.43)), M['bakelite'], bev=0.006, collection=col, lm='furn')
    fp = Vector((-1.0, 2.2, 0))
    lathe('flood_foot', [(0.0, 0.0), (0.18, 0.0), (0.18, 0.02), (0.0, 0.03)], M['iron'], loc=fp, seg=20, collection=col, lm='furn')
    tube('flood_pole', [fp + Vector((0, 0, 0.02)), fp + Vector((0, 0, 1.62))], 0.012, M['chrome'], col, seg=8, lm='furn')
    refl = lathe('flood_reflector', [(0.03, 0.0), (0.12, 0.05), (0.2, 0.14), (0.205, 0.15)], M['chrome'], loc=(0, 0, 0), seg=28, collection=col, lm='furn')
    refl.rotation_euler = (math.radians(-110), 0, math.radians(20)); refl.location = fp + Vector((0, -0.02, 1.66))
    box('floor_case', (0.5, 0.3, 0.26), (-0.4, 2.15, 0.13), M['leather'], rot=(0, 0, 0.3), bev=0.02, collection=col, lm='furn')
    return bulb


def _telephone(name, p, M, col):
    """A black desk telephone: its body, the dial, the handset in its cradle."""
    rounded_slab(f'{name}_body', 0.16, 0.2, 0.09, 0.04, p + Vector((0, 0, 0.045)), M['bakelite'], edge_bev=0.02, collection=col, lm='furn')
    cyl(f'{name}_dial', 0.04, 0.01, p + Vector((0, -0.06, 0.085)), M['chrome'], rot=(0.5, 0, 0), seg=20, collection=col, lm='furn')
    tube(f'{name}_handset', [p + Vector((-0.09, 0.02, 0.12)), p + Vector((-0.04, 0.02, 0.135)), p + Vector((0.04, 0.02, 0.135)), p + Vector((0.09, 0.02, 0.12))], 0.02, M['bakelite'], col, seg=10, lm='furn')


def _spindle_chair(name, M_, M, col):
    """The yellow spindle-back chair (maple, a saddle seat, a bow of spindles) built at the origin facing -y."""
    parts = [rounded_slab(f'{name}_seat', 0.42, 0.4, 0.04, 0.12, (0, 0, 0.44), M['spindle'], edge_bev=0.012, collection=col, lm='furn')]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(tube(f'{name}_leg{sx}{sy}', [Vector((0.17 * sx, 0.16 * sy, 0.0)), Vector((0.15 * sx, 0.14 * sy, 0.43))], 0.016, M['spindle'], col, seg=8, lm='furn'))
    bow = circle(Vector((0, 0.08, 0.86)), 0.2, (1, 0, 0), (0, 1, 0), n=16, a0=0.15, a1=math.pi - 0.15)
    parts.append(tube(f'{name}_bow', [p + Vector((0, 0.06, 0)) for p in bow], 0.014, M['spindle'], col, seg=8, lm='furn'))
    for k in range(6):
        a = 0.3 + k * (math.pi - 0.6) / 5; top = Vector((0.2 * math.cos(a), 0.08 + 0.2 * math.sin(a) + 0.06, 0.86))
        parts.append(tube(f'{name}_spindle{k}', [Vector((top.x * 0.9, 0.12 + 0.04 * math.sin(a), 0.46)), top], 0.008, M['spindle'], col, seg=6, lm='furn'))
    for o in parts: cine.place(o, M_)


# ---------------------------------------------------------------- the east wall: fireplace, door, armchair
def east_wall(M, col):
    """On the partition: the cream fireplace (pilasters, a frieze with a carved rosette, the mantel shelf, a cast-iron
    grate in a black firebox, a hearth), the still life over it in a wide pale frame, brass candlesticks and the
    tambour clock on the mantel (placed with the models); the hall door's casing. Before it, the armchair and its side
    table with the celadon lamp. Returns the lamp's bulb."""
    x = PX0; yc = FIRE_Y; w = 1.55; t = 0.2
    for s in (-1, 1):
        box(f'fire_pilaster{s}', (t, 0.24, 1.12), (x - t / 2, yc + s * (w / 2 - 0.12), 0.56), M['trim'], bev=0.006, collection=col, lm='furn')
    box('fire_frieze', (t, w - 0.48, 0.3), (x - t / 2, yc, 0.97), M['trim'], bev=0.006, collection=col, lm='furn')
    rose = lathe('fire_rosette', [(0.0, 0.03), (0.04, 0.03), (0.07, 0.015), (0.08, 0.0), (0.0, 0.0)], M['trim'], loc=(0, 0, 0), seg=24, collection=col, lm='furn')
    rose.rotation_euler = (0, -math.pi / 2, 0); rose.location = (x - t, yc, 0.97)
    box('fire_shelf', (t + 0.09, w + 0.1, 0.05), (x - (t + 0.09) / 2, yc, 1.145), M['trim'], bev=0.008, collection=col, lm='furn')
    box('fire_box', (0.06, w - 0.48, 0.82), (x - 0.03, yc, 0.41), M['iron'], bev=0, collection=col, lm='furn')
    for k in range(6):
        box(f'fire_grate{k}', (0.24, 0.012, 0.012), (x - 0.15, yc - 0.25 + k * 0.1, 0.18), M['iron'], bev=0.002, collection=col, lm='furn')
    box('fire_hearth', (0.42, w + 0.1, 0.03), (x - 0.21, yc, 0.015), M['trim'], bev=0.004, collection=col, lm='furn')
    c = Vector((x - 0.02, yc, 1.78))
    box('still_frame', (0.04, 1.06, 0.88), c, M['frame_pale'], bev=0.01, collection=col, lm='furn')
    pr = box('still_canvas', (0.006, 0.86, 0.68), c + Vector((-0.022, 0, 0)), M['still'], bev=0, collection=col, lm='furn'); uv_rect(pr, 'x')
    # the hall door's casing on the room's face and the hall's; the threshold
    for face, xx, s in (('room', PX0, -1), ('hall', PX1, 1)):
        for k, y in enumerate((DOOR[0] - 0.045, DOOR[1] + 0.045)):
            box(f'casing_{face}{k}', (0.022, 0.09, DOOR_H + 0.09), (xx + s * 0.011, y, (DOOR_H + 0.09) / 2), M['trim'], bev=0.004, collection=col, lm='furn')
        box(f'casing_{face}_head', (0.026, DOOR[1] - DOOR[0] + 0.18, 0.1), (xx + s * 0.013, sum(DOOR) / 2, DOOR_H + 0.05), M['trim'], bev=0.004, collection=col, lm='furn')
    # the armchair, upholstered, rolled arms, on short turned legs
    p, f = ARMCHAIR; ang = math.atan2(f.y, f.x) + math.pi / 2
    T_ = Matrix.Translation((p.x, p.y, 0)) @ Matrix.Rotation(ang, 4, 'Z')
    parts = [rounded_slab('armchair_seat', 0.62, 0.58, 0.16, 0.08, (0, 0.02, 0.38), M['armchair'], edge_bev=0.04, collection=col, lm='furn'),
             rounded_slab('armchair_back', 0.72, 0.18, 0.62, 0.08, (0, 0.33, 0.72), M['armchair'], rot=(math.radians(-8), 0, 0), edge_bev=0.05, collection=col, lm='furn'),
             rounded_slab('armchair_base', 0.82, 0.78, 0.2, 0.06, (0, 0.06, 0.22), M['armchair'], edge_bev=0.03, collection=col, lm='furn')]
    for s in (-1, 1):
        parts.append(rounded_slab(f'armchair_arm{s}', 0.14, 0.72, 0.3, 0.06, (s * 0.36, 0.04, 0.52), M['armchair'], edge_bev=0.05, collection=col, lm='furn'))
        for sy in (-1, 1):
            parts.append(lathe(f'armchair_leg{s}{sy}', [(0.025, 0.0), (0.02, 0.06), (0.028, 0.12), (0.0, 0.12)], M['dark_wood'], loc=(s * 0.34, 0.06 + sy * 0.32, 0), seg=10, collection=col, lm='furn'))
    for o in parts: cine.place(o, T_)
    # its side table, the celadon lamp on it (a ginger-jar base, a white drum shade)
    q = SIDE_TABLE
    lathe('side_top', [(0.0, 0.0), (0.26, 0.0), (0.265, 0.015), (0.26, 0.03), (0.0, 0.03)], M['mahogany'], loc=(q.x, q.y, 0.6), seg=28, collection=col, lm='furn')
    for k in range(3):
        a = 2 * math.pi * k / 3; d = Vector((math.cos(a), math.sin(a), 0)) * 0.19
        tube(f'side_leg{k}', [Vector((q.x, q.y, 0)) + d, Vector((q.x, q.y, 0.6)) + d * 0.9], 0.016, M['mahogany'], col, seg=8, lm='furn')
    lp = Vector((q.x, q.y, 0.63))
    lathe('celadon_base', [(0.0, 0.0), (0.07, 0.0), (0.1, 0.06), (0.12, 0.16), (0.1, 0.26), (0.05, 0.31), (0.03, 0.34), (0.0, 0.34)], M['celadon'], loc=lp, seg=28, collection=col, role='mug')   # under the bulb: drawn live (a hot texel would set the lamp pass's scale)
    tube('celadon_stem', [lp + Vector((0, 0, 0.34)), lp + Vector((0, 0, 0.52))], 0.008, M['brass'], col, seg=8, role='mug')
    lathe('celadon_shade', [(0.2, 0.0), (0.205, 0.004), (0.15, 0.27), (0.145, 0.274)], M['shade_drum'], loc=lp + Vector((0, 0, 0.36)), seg=36, collection=col)
    bulb = lp + Vector((0, 0, 0.5))
    lathe('celadon_bulb', [(0.0, -0.03), (0.03, 0.0), (0.024, 0.04), (0.0, 0.05)], M['bulb'], loc=bulb, seg=12, collection=col)
    return bulb


def pleated_lamp(M, col):
    """The tall floor lamp at the daybed's head: a brass column on a round foot, and a big shallow pleated shade (a
    cone of cream-yellow pleats); a small table under it with brass jugs."""
    p = PLEAT
    lathe('pleat_foot', [(0.0, 0.0), (0.16, 0.0), (0.16, 0.02), (0.05, 0.05), (0.0, 0.05)], M['brass'], loc=(p.x, p.y, 0), seg=28, collection=col, lm='furn')
    tube('pleat_column', [Vector((p.x, p.y, 0.04)), Vector((p.x, p.y, 1.46))], 0.013, M['brass'], col, seg=10, role='mug')
    # the pleated shade: a cone, its rim scalloped into pleats
    bm = bmesh.new(); n = 72; r0, r1, z0, z1 = 0.36, 0.1, 1.28, 1.48
    ring0 = [bm.verts.new((p.x + (r0 + 0.015 * (k % 2)) * math.cos(2 * math.pi * k / n), p.y + (r0 + 0.015 * (k % 2)) * math.sin(2 * math.pi * k / n), z0)) for k in range(n)]
    ring1 = [bm.verts.new((p.x + (r1 + 0.005 * (k % 2)) * math.cos(2 * math.pi * k / n), p.y + (r1 + 0.005 * (k % 2)) * math.sin(2 * math.pi * k / n), z1)) for k in range(n)]
    for k in range(n): bm.faces.new((ring0[k], ring0[(k + 1) % n], ring1[(k + 1) % n], ring1[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    sh = cine._mesh_obj('pleat_shade', bm, M['shade_pleat'], col, smooth=False)
    s = sh.modifiers.new('t', 'SOLIDIFY'); s.thickness = 0.004
    bulb = Vector((p.x, p.y, 1.36))
    lathe('pleat_bulb', [(0.0, -0.03), (0.03, 0.0), (0.024, 0.04), (0.0, 0.05)], M['bulb'], loc=bulb, seg=12, collection=col)
    t = Vector((p.x + 0.02, p.y + 0.38, 0))
    box('head_table', (0.4, 0.34, 0.03), t + Vector((0, 0, 0.56)), M['mahogany'], bev=0.004, collection=col, lm='furn')
    box('head_table_case', (0.36, 0.3, 0.44), t + Vector((0, 0, 0.33)), M['mahogany'], bev=0.004, collection=col, lm='furn')
    for k, dx in enumerate((-0.1, 0.08)):
        lathe(f'head_jug{k}', [(0.0, 0.0), (0.04, 0.0), (0.05, 0.05), (0.035, 0.14), (0.025, 0.19), (0.04, 0.22), (0.0, 0.22)], M['brass'], loc=t + Vector((dx, 0.02 * k, 0.575)), seg=16, collection=col, lm='furn')
    return bulb


def stole(M, col, at):
    """Lisa's white chiffon stole, folded over the armchair's arm (`at`, build frame): drawn live, carried in her hand."""
    m = material('stole_chiffon', (0.86, 0.86, 0.84), rough=0.7, sheen=0.5, sheen_tint=(0.6, 0.6, 0.6))
    o = cine.cloth_panel('stole', 0.24, 0.5, 3, 0.02, m, loc=(at.x, at.y + 0.04, at.z + 0.03), rot=(0, 0, math.pi / 2), collection=col, gather=0.8, seed=11)
    o['role'] = 'mug'; o['who'] = 'lisa'
    return o


def rug(M, col):
    r = box('rug', (3.2, 2.6, 0.008), (-1.3, -0.6, 0.004), M['rug'], bev=0.001, collection=col, lm='furn')
    cine.world_uv(r, 1.0)


# ---------------------------------------------------------------- the hall and the stairwell
def hall(M, col):
    """The building's hall beyond the partition: tile, a runner, a radiator; the apartment's door number; its ceiling
    light; the stairwell's doorway at the far end, dark."""
    xc = (PX1 + RIGHT) / 2
    box('hall_runner', (0.8, BW - FRONT - 0.5, 0.006), (xc, (FRONT + BW) / 2, 0.003), M['rug'], bev=0.001, collection=col, lm='furn')
    for k in range(10):
        rounded_slab(f'hall_radiator{k}', 0.16, 0.035, 0.6, 0.015, (RIGHT - 0.12, -1.6 + k * 0.05, 0.38), M['iron'], edge_bev=0.008, collection=col, lm='furn')
    box('hall_door_number', (0.005, 0.08, 0.1), (PX1 + 0.006, sum(DOOR) / 2, 1.75), M['brass'], bev=0.002, collection=col, lm='furn')
    lathe('hall_fixture', [(0.0, 0.0), (0.12, 0.0), (0.1, 0.06), (0.0, 0.09)], M['sconce'], loc=(xc, 0.6, RH - 0.1), seg=20, collection=col, lm='furn')
    return Vector((xc, 0.6, RH - 0.14))


# ---------------------------------------------------------------- the models: wheelchair, clock, candlesticks, vases
def models(M, col):
    """Poly Haven models placed and sized: the wheelchair (its teal leather made Jeff's brown), the tambour clock and
    the brass candlesticks on the mantel."""
    from rooms.the_godfather import _fit
    out = {}
    root, ms = cine.import_gltf(os.path.join(PH, 'wheelchair_01', 'wheelchair_01_1k.gltf'), collection=col, lm='furn')
    for o in ms:                                   # its one material's colour map, the teal leather made brown (textures.py)
        for sl in o.material_slots:
            nt = sl.material.node_tree if sl.material else None
            for n in (nt.nodes if nt else []):
                if n.type == 'TEX_IMAGE' and n.image and 'diff' in n.image.name: n.image = cine.image(tx('wheelchair_diff.jpg'))
    _fit(ms, (0, 0, 0), 0.92, axis='z', ground=True)
    ang = math.atan2(CHAIR_F.y, CHAIR_F.x) - math.atan2(-1, 0)
    T_ = Matrix.Translation((CHAIR.x, CHAIR.y, 0)) @ Matrix.Rotation(ang, 4, 'Z')
    for o in ms:
        if o.parent is None or o.parent.type != 'MESH': o.matrix_world = T_ @ o.matrix_world
    out['wheelchair'] = ms
    # the chair's elevating leg rest under his plaster leg (his left: toward the west wall in the room), padded
    f_t = mx(Vector((CHAIR_F.x, CHAIR_F.y, 0))); left_t = Vector((-f_t.y, f_t.x, 0)); c_t = mx(Vector((CHAIR.x, CHAIR.y, 0)))
    for k, (d, z, size) in enumerate(((0.62, 0.4, (0.15, 0.5, 0.035)), (0.36, 0.3, (0.03, 0.03, 0.2)), (0.84, 0.3, (0.03, 0.03, 0.2)))):
        p = mx(c_t + f_t * d + left_t * 0.1 + Vector((0, 0, z)))
        ang = math.atan2(CHAIR_F.y, CHAIR_F.x) - math.atan2(-1, 0)
        box(f'legrest{k}', size, p, M['leather'] if k == 0 else M['chrome'], rot=(0, 0, ang), bev=0.006 if k == 0 else 0.002, collection=col, lm='furn')
    _, ms = cine.import_gltf(os.path.join(PH, 'mantel_clock_01', 'mantel_clock_01_1k.gltf'), collection=col, lm='furn')
    _fit(ms, (PX0 - 0.12, FIRE_Y, 1.17), 0.3, axis='y', ground=True)
    for o in ms: o.matrix_world = Matrix.Translation((PX0 - 0.12, FIRE_Y, 0)) @ Matrix.Rotation(math.pi / 2, 4, 'Z') @ Matrix.Translation((-PX0 + 0.12, -FIRE_Y, 0)) @ o.matrix_world
    for s in (-1, 1):
        _, ms = cine.import_gltf(os.path.join(PH, 'brass_candleholders', 'brass_candleholders_1k.gltf'), collection=col, lm='furn')
        _fit(ms, (PX0 - 0.1, FIRE_Y + s * 0.58, 1.17), 0.34, axis='z', ground=True)
    for k, (vid, at, h) in enumerate((('brass_vase_01', (LEFT + 0.16, 0.95, 1.274), 0.24), ('brass_vase_03', (LEFT + 0.16, -1.05, 1.634), 0.22))):
        _, ms = cine.import_gltf(os.path.join(PH, vid, f'{vid}_1k.gltf'), collection=col, lm='furn')
        _fit(ms, at, h, axis='z', ground=True)
    return out


# ---------------------------------------------------------------- the cut
def section(objs, M):
    """Every face the module's top cuts through (the walls' tops), flat and dark."""
    for ob in objs:
        if not ob.name.startswith(('left_', 'back_', 'kerb')): continue
        me = ob.data
        if M['section'].name not in [m.name for m in me.materials if m]: me.materials.append(M['section'])
        k = [m.name if m else '' for m in me.materials].index(M['section'].name)
        for f in me.polygons:
            c = sum((me.vertices[i].co for i in f.vertices), Vector()) / len(f.vertices)
            if f.normal.z > 0.9 and abs(c.z - RH) < 0.006: f.material_index = k


# ---------------------------------------------------------------- light
DUSK_LOW = (1.0, 0.56, 0.36)               # the orange of the sky low over the roofs
DUSK_HIGH = (0.5, 0.58, 0.82)              # the blue above it
COURT = (1.0, 0.8, 0.55)                   # the neighbours' windows, lit, across the courtyard
LAMP = (1.0, 0.72, 0.42)                   # the three lamps Lisa switches on
HALL_LIGHT = (1.0, 0.76, 0.48)


def lights(bulbs, hall_bulb):
    """The dusk through the rear window (a warm low area light and a cool high one, outside, turned into the room; a
    faint warm glow of the courtyard's lit windows), the hall's ceiling light and a dim bulb in the stairwell; the
    three lamps (pleated, celadon, desk) as small warm points in their shades, hidden until their pass. Returns
    {'dusk': [...], 'lamps': [[...], [...], [...]]}."""
    out = {'dusk': [], 'lamps': [[], [], []]}
    def light(name, kind, loc, energy, colour, rot=None, group=None, **kw):
        ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = colour
        for k, v in kw.items(): setattr(ld, k, v)
        ob = cine.link(bpy.data.objects.new(name, ld)); ob.location = loc
        if rot: ob.rotation_euler = rot
        if kind in ('AREA', 'SPOT', 'SUN'): ob.visible_camera = False; ob.visible_glossy = False
        group.append(ob); return ob
    wx = sum(WINDOW_X) / 2; ww = WINDOW_X[1] - WINDOW_X[0]
    # an area light shines along its local -z: turned (+90 deg about x) to face +y, into the room
    light('dusk_low', 'AREA', (wx, FRONT - 0.45, 1.0), 80.0, DUSK_LOW, rot=(math.pi / 2, 0, 0), group=out['dusk'], shape='RECTANGLE', size=ww, size_y=1.2)
    light('dusk_high', 'AREA', (wx, FRONT - 0.45, 2.1), 70.0, DUSK_HIGH, rot=(math.pi / 2 - 0.25, 0, 0), group=out['dusk'], shape='RECTANGLE', size=ww, size_y=1.0)
    light('court_glow', 'AREA', (wx - 0.8, FRONT - 1.6, 1.4), 30.0, COURT, rot=(math.pi / 2, 0, 0), group=out['dusk'], shape='DISK', size=1.4)
    light('hall_ceiling', 'POINT', hall_bulb, 26.0, HALL_LIGHT, group=out['dusk'], shadow_soft_size=0.08)
    light('stair_bulb', 'POINT', (sum(STAIR) / 2, 3.25, 2.4), 6.0, HALL_LIGHT, group=out['dusk'], shadow_soft_size=0.06)
    for k, (b, e) in enumerate(zip(bulbs, (120.0, 90.0, 80.0))):
        l = light(f'lamp{k + 1}', 'POINT', b, e, LAMP, group=out['lamps'][k], shadow_soft_size=0.04)
        l.hide_render = True
    return out
