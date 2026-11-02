# The Big Lebowski · Hollywood Star Lanes, Santa Monica Boulevard (1960; the film shot there in 1997): the bowling
# alley's bar, where the Dude sits over a White Russian and the Stranger takes the stool beside him for a Sioux City
# Sarsaparilla. The bar runs along the front, its stools on the lane side, so the drinkers face the case with the lanes
# behind them, as the film's master over the bar shows them; behind a low chrome rail six Brunswick lanes (17 to 22)
# run from the left, where the curved fibreglass settees, the scoring consoles with their overhead projectors and the
# ball returns stand at their heads, to the right, where the pins wait under the peach masking band with its blue
# crowns, the banners on the fascia above it. Honey maple, cream and blue tile, peach plaster with blue neon stars,
# orange laminate; lit by rows of fluorescent troffers, the pin decks bright under the masking, recessed cans over
# the bar.
#
# The alley is too big for the module at 1:6: like the throne room it is built at its true size in a module 1 / SCALE
# times the size, then shrunk by SCALE (0.5) with the people. The lanes are half their real length (foul line to head
# pin 8.8 m of 18.3): the cut the room needs to fit.
import math, os, random
import bpy, bmesh
from mathutils import Vector, Matrix
import cine
from cine import box, cyl, material, lathe, rounded_slab, slab_profile, moulding
from rooms.seinfeld import uv_rect, tube, circle

SCALE = 0.5
W, D, H = 9.6 / SCALE, 7.6 / SCALE, 3.0 / SCALE   # the module, at the alley's true size
T = 0.14 / SCALE                           # the module's walls
LEFT, BACK, RIGHT, FRONT = -W / 2 + T, D / 2 - T, W / 2 - T, -D / 2 + T
RH = 3.6                                   # the ceiling (the walls' cut)
KH = 0.22 / SCALE                          # the cut-away's kerb
TEX = os.path.join(cine.OUT, 'textures', 'the-big-lebowski')
tx = lambda n: os.path.join(TEX, n)

# the lanes (along +x): the bed, its gutters, the capping between the two lanes of a pair (over the ball return's
# track), the division between pairs; front to back the pairs are 22/21, 20/19, 18/17 (numbers rise to the bowler's right)
LW, GW, CAP, DIV = 1.054, 0.235, 0.30, 0.14
YR = -3.6                                  # the rail between the bar's concourse and the lanes (the front lane's outer edge)
PAIRS = ((22, 21), (20, 19), (18, 17))
LANES = {}                                 # each lane's centre line (y)
for _k, (_a, _b) in enumerate(PAIRS):
    LANES[_a] = YR + DIV + GW + LW / 2 + _k * (2 * (LW + 2 * GW) + CAP + DIV)
    LANES[_b] = LANES[_a] + LW + 2 * GW + CAP
PAIR_Y = {a: (LANES[a] + LANES[b]) / 2 for a, b in PAIRS}      # the ball return's line, between the pair
DIVS = [YR + DIV / 2] + [LANES[b] + LW / 2 + GW + DIV / 2 for a, b in PAIRS]   # the divisions: the rail's side, between pairs, the back
Y_END = LANES[17] + LW / 2 + GW + DIV      # the last lane's outer edge
X_APP = -6.4                               # the approach's back end (the settees behind it)
X_FOUL = -2.1                              # the foul line
X_HEAD = 6.73                              # the head pin
X_PIT = 7.6                                # the pin deck's end (the pit)
X_MASK = 6.25                              # the masking unit's face
MASK_Z = (1.0, 2.0)                        # its bottom and top
KICK = 0.36                                # the kickbacks between the pin decks: low (real ones reach the masking), or the
                                           # case, looking along them from the front, would see no pins
X_MACH = 7.9                               # the pinsetters' housing (a solid to the right cut)
ROW = 0.3048 * math.cos(math.radians(30))  # pin rows, 12 in apart in a triangle
PINS = [(0, 0.0)] + [(1, -0.1524), (1, 0.1524)] + [(2, -0.3048), (2, 0.0), (2, 0.3048)] + [(3, -0.4572), (3, -0.1524), (3, 0.1524), (3, 0.4572)]
PIN_SPOTS = [(X_HEAD + r * ROW, dy) for r, dy in PINS]   # pins 1-10 (dy across the lane, + to the bowler's left)
BALL_R = 0.109

# the settee area at the lanes' heads, per pair (x of its parts)
X_HOOD = X_APP + 0.3                       # the ball return's hood (on the pair's line)
X_RACK = (X_APP - 0.1, -7.05)              # its rack's rails reach back toward the settee
X_CONSOLE = -7.75                          # the scoring console (on the pair's line, its desk toward the lanes)
X_SETTEE = -8.65                           # the settee's back (its middle seat at -8.35)
RACK_SPOTS = {a: [Vector((X_RACK[1] + 0.12 + k * 0.23, PAIR_Y[a], 0.584)) for k in range(3)] for a, b in PAIRS}   # balls' centres, resting on the rails
OPEN_X = (-8.9, -6.6)                      # the gap in the rail from the concourse to the settees

# the bar: the counter runs along x, the stools on its lane side (+y), the drinkers facing the case (-y)
BAR_X = (-3.4, 3.9)
BAR_Y = (-6.35, -5.75)                     # the bartender's side, the drinkers' side (the top's edge)
BAR_TOP = 1.07
STOOL_Y = -5.15
STOOL_SEAT = 0.76
STOOLS = (-2.75, -1.9, -1.05, -0.2, 0.65, 1.5, 2.35, 3.2)
SEAT_OF = {'donny': STOOLS[1], 'walter': STOOLS[2], 'dude': STOOLS[3], 'stranger': STOOLS[4]}
FOOT_RING = 0.27                           # the stools' foot ring


# ---------------------------------------------------------------- materials
def mats():
    M = {}
    M['lane'] = material('maple_lane', rough=0.12, maps={'color': tx('lane_color.jpg'), 'normal': tx('lane_normal.jpg')}, scale=LW, normal_strength=0.12, coat=1.0, coat_rough=0.03)
    M['gutter'] = material('gutter', (0.09, 0.05, 0.035), rough=0.22, coat=0.6)
    M['capping'] = material('capping', (0.07, 0.036, 0.026), rough=0.3, coat=0.5)
    M['tile'] = material('concourse_tile', rough=0.3, maps={'color': tx('tile_color.jpg')}, scale=2.438, coat=0.4, coat_rough=0.15)
    M['peach'] = material('peach_plaster', rough=0.7, maps={'color': tx('peach_color.jpg'), 'normal': tx('plaster_normal.jpg')}, scale=2.0, normal_strength=0.2)
    M['cream'] = material('cream_paint', (0.78, 0.7, 0.55), rough=0.55)
    M['orange'] = material('orange_laminate', (0.78, 0.2, 0.05), rough=0.3, coat=0.5, coat_rough=0.1)
    M['shell'] = material('settee_orange', (0.82, 0.22, 0.05), rough=0.25, coat=0.8, coat_rough=0.08)
    M['shell_cream'] = material('settee_cream', (0.8, 0.72, 0.56), rough=0.3, coat=0.6, coat_rough=0.1)
    M['console'] = material('console_cream', (0.76, 0.69, 0.53), rough=0.32, coat=0.4)
    M['crown'] = material('crown_decal', rough=0.35, maps={'color': tx('crown_color.jpg')}, scale=1.0, coat=0.4)
    M['chrome'] = material('chrome', (0.8, 0.8, 0.8), rough=0.12, metal=1.0)
    M['steel'] = material('dull_steel', (0.5, 0.5, 0.5), rough=0.35, metal=1.0)
    M['bar_wood'] = material('bar_wood', rough=0.25, maps={'color': tx('bar_wood_color.jpg'), 'normal': tx('bar_wood_normal.jpg')}, scale=1.0, normal_strength=0.2, coat=0.8, coat_rough=0.08)
    M['dark_wood'] = material('rail_wood', (0.12, 0.06, 0.035), rough=0.3, coat=0.6)
    M['vinyl'] = material('stool_vinyl', rough=0.35, maps={'color': tx('vinyl_color.jpg'), 'normal': tx('vinyl_normal.jpg')}, scale=0.3, normal_strength=0.4, coat=0.4)
    M['masking'] = material('masking_band', rough=0.5, maps={'color': tx('masking_color.jpg')}, scale=1.0)
    M['mask_side'] = material('masking_side', (0.8, 0.5, 0.36), rough=0.5)
    M['diamond'] = material('masking_diamond', (0.72, 0.3, 0.2), rough=0.45)
    M['pin'] = material('pin_white', (0.86, 0.85, 0.82), rough=0.15, coat=1.0, coat_rough=0.05)
    M['pin_red'] = material('pin_red', (0.62, 0.03, 0.03), rough=0.2, coat=1.0)
    M['deck'] = material('pin_deck', (0.62, 0.48, 0.32), rough=0.25, coat=0.6)
    M['pit'] = material('pit_black', (0.012, 0.011, 0.01), rough=0.95)
    M['kickback'] = material('kickback', (0.16, 0.09, 0.06), rough=0.4)
    M['machine'] = material('machine', (0.05, 0.05, 0.055), rough=0.6)
    M['neon_blue'] = material('neon_blue', (0.5, 0.65, 1.0), rough=0.4, emission=(0.12, 0.34, 1.0), emission_strength=7.0)
    M['neon_white'] = material('neon_white', (1.0, 1.0, 1.0), rough=0.4, emission=(0.7, 0.82, 1.0), emission_strength=6.0)
    M['neon_red'] = material('neon_red', (1.0, 0.2, 0.15), rough=0.4, emission=(1.0, 0.12, 0.08), emission_strength=10.0)
    M['neon_green'] = material('neon_green', (0.3, 1.0, 0.5), rough=0.4, emission=(0.2, 1.0, 0.45), emission_strength=8.0)
    M['bulb'] = material('bulb', (1.0, 0.9, 0.7), rough=0.3, emission=(1.0, 0.78, 0.48), emission_strength=22.0)
    M['juke_glow'] = material('jukebox_glow', (1.0, 0.7, 0.3), rough=0.3, emission=(1.0, 0.55, 0.2), emission_strength=4.0)
    M['juke_red'] = material('jukebox_red', (0.9, 0.1, 0.08), rough=0.3, emission=(1.0, 0.1, 0.06), emission_strength=3.0)
    M['glass'] = material('bar_glass', (0.7, 0.72, 0.72), rough=0.05, coat=1.0)
    M['milk'] = material('white_russian', (0.78, 0.68, 0.52), rough=0.2, coat=0.6)
    M['beer'] = material('beer_bottle', (0.16, 0.07, 0.015), rough=0.1, coat=1.0)
    M['label'] = material('label_cream', (0.82, 0.76, 0.6), rough=0.5)
    M['sarsaparilla'] = material('sarsaparilla_glass', (0.08, 0.04, 0.02), rough=0.08, coat=1.0)
    M['basket'] = material('nut_basket', (0.12, 0.26, 0.62), rough=0.5)
    M['nuts'] = material('beer_nuts', (0.55, 0.3, 0.12), rough=0.5)
    M['ashtray'] = material('ashtray', (0.25, 0.25, 0.27), rough=0.3, metal=0.6)
    M['paper'] = material('napkin', (0.88, 0.86, 0.8), rough=0.8)
    M['score'] = material('score_sheet', rough=0.7, maps={'color': tx('score_color.jpg')}, scale=1.0)
    M['brunswick'] = material('brunswick_sign', rough=0.4, maps={'color': tx('brunswick_color.jpg')}, scale=1.0, emission=(0.3, 0.4, 1.0), emission_strength=0.0)
    M['black'] = material('black_plastic', (0.02, 0.02, 0.022), rough=0.4)
    M['lens'] = material('projector_lens', (0.1, 0.12, 0.14), rough=0.05, coat=1.0)
    M['kerb'] = material('kerb', (0.16, 0.12, 0.09), rough=0.9)
    M['section'] = material('section', (0.03, 0.028, 0.026), rough=0.92)
    M['phantom'] = material('phantom_ceiling', (0.7, 0.66, 0.58), rough=0.9)
    M['troffer'] = material('troffer', (1.0, 0.96, 0.88), rough=0.5, emission=(1.0, 0.94, 0.82), emission_strength=6.0)
    for n in ('17', '18', '19', '20', '21', '22'): M[f'num{n}'] = material(f'lane_number_{n}', rough=0.5, maps={'color': tx(f'num_{n}.jpg')}, scale=1.0)
    for n in ('division', 'stars', 'open', 'fall'): M[f'banner_{n}'] = material(f'banner_{n}', rough=0.6, maps={'color': tx(f'banner_{n}.jpg')}, scale=1.0)
    BALLS = [((0.03, 0.03, 0.035), 'ball_black'), ((0.04, 0.1, 0.45), 'ball_blue'), ((0.5, 0.04, 0.05), 'ball_red'), ((0.06, 0.3, 0.12), 'ball_green'),
             ((0.32, 0.06, 0.34), 'ball_purple'), ((0.6, 0.32, 0.06), 'ball_amber'), ((0.12, 0.14, 0.18), 'ball_slate'), ((0.75, 0.2, 0.45), 'ball_magenta')]
    for c, n in BALLS: M[n] = material(n, c, rough=0.12, coat=1.0, coat_rough=0.04)
    return M


BALL_MATS = ('ball_black', 'ball_blue', 'ball_red', 'ball_green', 'ball_purple', 'ball_amber', 'ball_slate')


# ---------------------------------------------------------------- the shell
def shell(M, arch, phantom):
    """The floor (tile for the concourse and the settees, maple for the approaches and lanes laid on it), the module's
    left and back walls, the kerbs, the pinsetters' housing at the right; the phantom ceiling with its troffers."""
    box('subfloor', (W, D, 0.05), (0, 0, -0.045), M['kerb'], bev=0, collection=arch, lm='arch')
    # the tile floor round the lanes (the concourse, the settees, the strip along the back wall); under the lanes, a
    # dark bed a little lower (the gutters dip below the tiles' level)
    for k, (x0, x1, y0, y1) in enumerate(((LEFT, RIGHT, FRONT, YR), (LEFT, X_APP, YR, BACK), (X_APP, RIGHT, Y_END, BACK))):
        fl = box(f'floor_{k}', (x1 - x0 + 0.003, y1 - y0 + 0.003, 0.03), ((x0 + x1) / 2, (y0 + y1) / 2, -0.015), M['tile'], bev=0, collection=arch, lm='arch')
        cine.world_uv(fl, 1.0)
    box('lane_bed', (X_MACH - X_APP, Y_END - YR, 0.03), ((X_APP + X_MACH) / 2, (YR + Y_END) / 2, -0.055), M['gutter'], bev=0, collection=arch, lm='arch')
    # the walls: a band of orange laminate to 0.95 m, peach plaster above
    box('back_wall', (W, T, RH), (0, D / 2 - T / 2, RH / 2), M['peach'], bev=0, collection=arch, lm='arch')
    box('left_wall', (T, D - T, RH), (-W / 2 + T / 2, -T / 2, RH / 2), M['peach'], bev=0, collection=arch, lm='arch')
    box('back_band', (RIGHT - LEFT, 0.02, 0.95), ((LEFT + RIGHT) / 2, BACK - 0.01, 0.475), M['orange'], bev=0.002, collection=arch, lm='arch')
    box('left_band', (0.02, BACK - FRONT, 0.95), (LEFT + 0.01, (BACK + FRONT) / 2, 0.475), M['orange'], bev=0.002, collection=arch, lm='arch')
    for k, (a, b) in enumerate((((LEFT, BACK - 0.02), (RIGHT, BACK - 0.02)),)):
        moulding(f'back_cap{k}', (LEFT, BACK - 0.02, 0.95), (RIGHT, BACK - 0.02, 0.95), (0, -1, 0), [(0, 0), (0.03, 0), (0.03, 0.03), (0, 0.04)], M['dark_wood'], collection=arch, lm='arch')
    moulding('left_cap', (LEFT + 0.02, FRONT, 0.95), (LEFT + 0.02, BACK, 0.95), (1, 0, 0), [(0, 0), (0.03, 0), (0.03, 0.03), (0, 0.04)], M['dark_wood'], collection=arch, lm='arch')
    box('kerb_front', (W, T, KH), (0, -D / 2 + T / 2, KH / 2), M['kerb'], bev=0.002, collection=arch, lm='arch')
    box('kerb_right', (T, D - 2 * T, KH), (W / 2 - T / 2, 0, KH / 2), M['kerb'], bev=0.002, collection=arch, lm='arch')
    # the pinsetters' housing: a solid from the masking's back to the right cut, over all six lanes, its end a wall
    box('solid_machines', (W / 2 - X_MACH, BACK - YR, RH), ((X_MACH + W / 2) / 2, (YR + BACK) / 2, RH / 2), M['peach'], bev=0, collection=arch, lm='arch')
    box('machines_band', (W / 2 - X_MACH, 0.02, 0.95), ((X_MACH + W / 2) / 2, YR - 0.01, 0.475), M['orange'], bev=0.002, collection=arch, lm='arch')
    # the phantoms: the ceiling (its troffers lit), the front wall, the right end beyond the machines
    P = M['phantom']; ph = lambda name, size, loc, mat=P: box(name, size, loc, mat, bev=0, collection=phantom, bake_only=1)
    ph('ph_ceiling', (W, D, 0.3), (0, 0, RH + 0.15))
    ph('ph_front', (W, 0.3, RH - KH), (0, FRONT - 0.15, KH + (RH - KH) / 2), M['peach'])
    ph('ph_right', (0.3, D, RH - KH), (RIGHT + 0.15, 0, KH + (RH - KH) / 2), M['peach'])


TROFFERS = []


def troffer_grid():
    """The ceiling's fluorescent panels (2 x 4 ft): rows across the lanes and over the settees, a few over the
    concourse; recessed cans over the bar instead (true metres, z = ceiling)."""
    out = []
    for x in (-8.0, -5.2, -2.2, 0.8, 3.8):
        for k in range(6): out.append(((x, YR + 0.95 + k * 1.75), (1.22, 0.61)))
    for x in (-8.0, 5.6):
        out.append(((x, -5.2), (1.22, 0.61)))
    TROFFERS[:] = out
    return out


# ---------------------------------------------------------------- the lanes
def lanes(M, col, rnd):
    """Six lanes from the approach to the pit: the maple bed (approach and lane in one), the gutters, the capping
    between the lanes of a pair and the divisions between pairs, the approach dots and the arrows, the foul line; the
    pin decks, the kickbacks between them, the pits' black curtains. Standing pins on the odd lanes (the bowled lanes'
    pins and balls belong to their lanes' own rigs)."""
    x0, x1 = X_APP, X_PIT; L = x1 - x0
    for n, y in LANES.items():
        bed = box(f'lane{n}', (L, LW, 0.03), ((x0 + x1) / 2, y, 0.015), M['lane'], bev=0.002, collection=col, lm='arch')
        cine.world_uv(bed, LW); _rot_uv(bed)
        for s in (-1, 1):                                                   # the gutters: a channel below the bed
            yc = y + s * (LW / 2 + GW / 2)
            g = _channel(f'gutter{n}_{s}', x0 + 0.05 + (X_FOUL - x0) * 0, x1, yc, GW, 0.06, M['gutter'], col)
        foul = box(f'foul{n}', (0.012, LW, 0.002), (X_FOUL, y, 0.031), M['black'], bev=0, collection=col, lm='arch')
        for k in range(7):                                                   # the arrows, 15 ft past the foul line, a V
            dy = (k - 3) * 5 * LW / 39; dx = 4.3 + abs(k - 3) * 0.15
            _tri(f'arrow{n}_{k}', (X_FOUL + dx * 0.5, y + dy), 0.06, 0.016, M['black'], col)
        for k in range(5):                                                   # the dots on the approach
            box(f'dot{n}_{k}', (0.012, 0.012, 0.002), (X_FOUL - 2.1, y + (k - 2) * 5 * LW / 39, 0.031), M['black'], bev=0, collection=col, lm='arch')
        box(f'deck{n}', (X_PIT - X_HEAD + 0.25, LW, 0.004), ((X_HEAD - 0.25 + X_PIT) / 2, y, 0.032), M['deck'], bev=0, collection=col, lm='arch')
        if n % 2:                                                              # standing pins on the odd lanes
            for k, (px, dy) in enumerate(PIN_SPOTS): pin(f'pin{n}_{k}', Vector((px, y + dy, 0.03)), M, col)
    # the cappings between the lanes of a pair (the ball return's track under it) and the divisions
    for a, b in PAIRS:
        yc = PAIR_Y[a]
        box(f'capping{a}', (x1 - X_FOUL + 0.6, CAP - 0.02, 0.07), ((X_FOUL - 0.6 + x1) / 2, yc, 0.035), M['capping'], bev=0.01, collection=col, lm='arch')
        box(f'capping{a}_app', (X_FOUL - 0.6 - X_HOOD - 0.3, CAP - 0.02, 0.025), ((X_FOUL - 0.6 + X_HOOD + 0.3) / 2, yc, 0.0125), M['capping'], bev=0.005, collection=col, lm='arch')
    for k, y in enumerate(DIVS):
        box(f'division{k}', (x1 - X_APP, DIV - 0.01, 0.05 if 0 < k < len(DIVS) - 1 else 0.08), ((X_APP + x1) / 2, y, 0.025 if 0 < k < len(DIVS) - 1 else 0.04), M['capping'], bev=0.008, collection=col, lm='arch')
    # the pin decks' kickbacks (the walls between lanes at the pins) and the pits behind
    for k, y in enumerate(DIVS + [PAIR_Y[a] for a, b in PAIRS]):
        box(f'kickback{k}', (X_MACH - (X_HEAD - 0.6), 0.05, KICK), ((X_HEAD - 0.6 + X_MACH) / 2, y, KICK / 2), M['kickback'], bev=0.004, collection=col, lm='arch')
    box('pit', (X_MACH - X_PIT, Y_END - YR, 0.02), ((X_PIT + X_MACH) / 2, (YR + Y_END) / 2, -0.08), M['pit'], bev=0, collection=col, lm='arch')
    box('pit_curtain', (0.02, Y_END - YR, MASK_Z[0] + 0.08), (X_MACH - 0.03, (YR + Y_END) / 2, (MASK_Z[0] - 0.08) / 2), M['pit'], bev=0, collection=col, lm='arch')
    box('pit_front', (0.02, Y_END - YR, 0.1), (X_PIT + 0.01, (YR + Y_END) / 2, -0.035), M['pit'], bev=0, collection=col, lm='arch')


def _rot_uv(ob):
    """The lane's boards run along x: the texture's boards run along u, laid by a box projection; nothing to turn."""
    return ob


def _channel(name, x0, x1, yc, w, d, mat, col, seg=8):
    """A gutter: a half-round channel of width w and depth d along x, its rim at the lane's level."""
    bm = bmesh.new(); prof = []
    for i in range(seg + 1):
        a = math.pi * i / seg; prof.append((yc - w / 2 * math.cos(a), 0.03 - d * math.sin(a)))
    ra = [bm.verts.new((x0, y, z)) for y, z in prof]; rb = [bm.verts.new((x1, y, z)) for y, z in prof]
    for i in range(seg): bm.faces.new((ra[i], rb[i], rb[i + 1], ra[i + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        if f.normal.z < 0: f.normal_flip()
    ob = cine._mesh_obj(name, bm, mat, col, smooth=True); ob['lm'] = 'arch'
    return ob


def _tri(name, at, l, w, mat, col):
    bm = bmesh.new(); x, y = at; z = 0.031
    vs = [bm.verts.new(p) for p in ((x + l, y, z), (x, y - w / 2, z), (x, y + w / 2, z))]; bm.faces.new(vs)
    ob = cine._mesh_obj(name, bm, mat, col, smooth=False); ob['lm'] = 'arch'
    return ob


PIN_PROFILE = [(0.0, 0.0), (0.0258, 0.0), (0.0335, 0.012), (0.046, 0.04), (0.0575, 0.08), (0.0606, 0.114), (0.0585, 0.15), (0.048, 0.19),
               (0.0335, 0.226), (0.0235, 0.254), (0.0227, 0.27), (0.0262, 0.296), (0.0315, 0.326), (0.0318, 0.345), (0.028, 0.366), (0.018, 0.378), (0.0, 0.381)]


def pin_bm(bm, M_idx=(0, 1), seg=16, xf=Matrix.Identity(4)):
    """A tenpin (USBC: 15 in tall, 4.77 in at the belly), its two red neck stripes as a second material; added to bm."""
    rings = []
    for r, z in PIN_PROFILE:
        rings.append([bm.verts.new(xf @ Vector((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), z))) for i in range(seg)] if r > 0 else [bm.verts.new(xf @ Vector((0, 0, z)))])
    faces = []
    for (ra, za), (rb, zb), A, B in zip(PIN_PROFILE, PIN_PROFILE[1:], rings, rings[1:]):
        for i in range(seg):
            if len(A) == 1: f = bm.faces.new((A[0], B[(i + 1) % seg], B[i]))
            elif len(B) == 1: f = bm.faces.new((A[i], A[(i + 1) % seg], B[0]))
            else: f = bm.faces.new((A[i], A[(i + 1) % seg], B[(i + 1) % seg], B[i]))
            zc = (za + zb) / 2; f.material_index = M_idx[1] if (0.236 < zc < 0.252 or 0.276 < zc < 0.29) else M_idx[0]; f.smooth = True
            faces.append(f)
    return faces


def pin(name, at, M, col):
    bm = bmesh.new(); pin_bm(bm, xf=Matrix.Translation(at))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = cine._mesh_obj(name, bm, M['pin'], col, smooth=True); ob.data.materials.append(M['pin_red']); ob['lm'] = 'furn'
    return ob


def ball_bm(bm, at, r=BALL_R, seg=20, rows=10):
    """A bowling ball: a sphere turned from rings (every vertex made here, so it can be weighted to a bone as one).
    Returns {'verts': [...], 'faces': [...]}."""
    c = Vector(at); top = bm.verts.new(c + Vector((0, 0, r))); bot = bm.verts.new(c - Vector((0, 0, r)))
    rings = []
    for j in range(1, rows):
        a = math.pi * j / rows; z, rr = r * math.cos(a), r * math.sin(a)
        rings.append([bm.verts.new(c + Vector((rr * math.cos(2 * math.pi * i / seg), rr * math.sin(2 * math.pi * i / seg), z))) for i in range(seg)])
    faces = [bm.faces.new((top, rings[0][i], rings[0][(i + 1) % seg])) for i in range(seg)]
    for A, B in zip(rings, rings[1:]):
        faces += [bm.faces.new((A[i], B[i], B[(i + 1) % seg], A[(i + 1) % seg])) for i in range(seg)]
    faces += [bm.faces.new((bot, rings[-1][(i + 1) % seg], rings[-1][i])) for i in range(seg)]
    for f in faces: f.smooth = True
    return {'verts': [top, bot] + [v for ring in rings for v in ring], 'faces': faces}


def ball(name, at, mat, col, holes=None):
    bm = bmesh.new(); ball_bm(bm, at)
    ob = cine._mesh_obj(name, bm, mat, col, smooth=True); ob['lm'] = 'furn'
    return ob


# ---------------------------------------------------------------- the masking units and the fascia
def masking(M, col):
    """Over the pin decks: one long peach masking unit across the six lanes (a box from its face to the machines),
    its face the painted band (an oval window and a blue crown per lane, a salmon diamond between); raised diamonds on
    the joins; above it the cream fascia with the banners; under it, the deck lights (in `lights`)."""
    y0, y1 = YR, Y_END
    z0, z1 = MASK_Z
    body = box('solid_masking', (X_MACH - X_MASK, y1 - y0, z1 - z0), ((X_MASK + X_MACH) / 2, (y0 + y1) / 2, (z0 + z1) / 2), M['mask_side'], bev=0.004, collection=col, lm='arch')
    face = box('masking_face', (0.01, y1 - y0, z1 - z0), (X_MASK - 0.006, (y0 + y1) / 2, (z0 + z1) / 2), M['masking'], bev=0, collection=col, lm='arch')
    _uv_face_x(face, y1, y0, z0, z1)                                       # u from the back lane (17) to the front (22)
    # the fascia over it to the ceiling, the banners hung on it
    box('solid_fascia', (0.3, y1 - y0, RH - z1), (X_MASK + 0.15, (y0 + y1) / 2, (z1 + RH) / 2), M['cream'], bev=0.004, collection=col, lm='arch')
    for k, (name, yc, w) in enumerate((('division', LANES[21] + 0.6, 2.4), ('stars', LANES[19] + 0.4, 2.4), ('open', LANES[17] - 0.5, 1.8), ('fall', LANES[22] - 0.25, 1.8))):
        b = box(f'banner_{name}', (0.012, w, w * 0.25), (X_MASK - 0.01, yc, z1 + 0.42), M[f'banner_{name}'], bev=0, collection=col, lm='arch')
        _uv_face_x(b, yc + w / 2, yc - w / 2, z1 + 0.42 - w * 0.125, z1 + 0.42 + w * 0.125)
    # the masking's lower lip and the stars on the fascia between the banners
    box('masking_lip', (0.06, y1 - y0, 0.06), (X_MASK - 0.02, (y0 + y1) / 2, z0 + 0.03), M['diamond'], bev=0.01, collection=col, lm='arch')


def _uv_face_x(ob, ya, yb, za, zb):
    """0..1 UVs on a face looking along -x: u from y = ya to yb, v from za to zb."""
    me = ob.data; uv = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
    M_ = ob.matrix_basis                                                   # matrix_world is stale right after placing
    for poly in me.polygons:
        for li in poly.loop_indices:
            c = M_ @ me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = ((c.y - ya) / (yb - ya), (c.z - za) / (zb - za))


def starburst(name, c, normal, r, M, col, n=14, seed=0, core='neon_white', rays='neon_blue'):
    """A Googie neon star: thin rays of two lengths from a white core, standing a little off the wall."""
    rnd = random.Random(seed); N = Vector(normal).normalized()
    U = N.cross(Vector((0, 0, 1))).normalized() if abs(N.z) < 0.9 else Vector((1, 0, 0)); V = N.cross(U).normalized()
    bm = bmesh.new()
    for i in range(n):
        a = 2 * math.pi * (i + 0.5 * (i % 2) * rnd.random()) / n; L = r * (1.0 if i % 2 == 0 else 0.58) * rnd.uniform(0.92, 1.06)
        d = U * math.cos(a) + V * math.sin(a); s = d.cross(N).normalized()
        w = 0.022
        p = [c + d * 0.05 + s * w, c + d * L, c + d * 0.05 - s * w]
        vs = [bm.verts.new(q) for q in p]; vs2 = [bm.verts.new(q + N * 0.015) for q in p]
        bm.faces.new(vs2)
        for k in range(3): bm.faces.new((vs[k], vs[(k + 1) % 3], vs2[(k + 1) % 3], vs2[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = cine._mesh_obj(name, bm, M[rays], col, smooth=False)                      # neon: it shines, no light map
    cc = cyl(f'{name}_core', r * 0.08, 0.03, c + N * 0.02, M[core], seg=16, bev=0, collection=col)
    cc.rotation_euler = N.to_track_quat('Z', 'Y').to_euler()
    return ob


STARS = []


def walls(M, col, rnd):
    """The neon stars on the back and left walls, the ball racks along the left wall with the Brunswick sign over them,
    a starburst over the bar's end."""
    for k, x in enumerate((-6.6, -2.6, 1.4, 5.0)):
        z = 2.35 + 0.25 * (k % 2); r = 0.42 + 0.08 * (k % 2)
        STARS.append((Vector((x, BACK - 0.05, z)), r)); starburst(f'star_back{k}', Vector((x, BACK - 0.03, z)), (0, -1, 0), r, M, col, seed=k)
    for k, y in enumerate((-5.9, -1.8, 2.6)):
        z = 2.4 + 0.2 * (k % 2)
        STARS.append((Vector((LEFT + 0.05, y, z)), 0.45)); starburst(f'star_left{k}', Vector((LEFT + 0.03, y, z)), (1, 0, 0), 0.45, M, col, seed=10 + k)
    # the ball racks: three tiers of orange shelving along the left wall behind the settees, house balls on them
    for k, (ya, yb) in enumerate(((YR + 0.3, PAIR_Y[22] + 1.2), (PAIR_Y[20] - 1.0, PAIR_Y[20] + 1.3), (PAIR_Y[18] - 1.0, Y_END - 0.2))):
        rack(f'rack{k}', ya, yb, M, col, rnd)
    sg = box('brunswick_sign', (0.03, 1.8, 0.45), (LEFT + 0.03, PAIR_Y[20] + 0.15, 1.95), M['brunswick'], bev=0.004, collection=col, lm='furn')
    uv_rect(sg, 'x')


def rack(name, ya, yb, M, col, rnd, depth=0.36):
    """Orange enamel shelving against the left wall: three sloped tiers of balls, end panels."""
    x = LEFT + depth / 2 + 0.02
    for k, z in enumerate((0.3, 0.72, 1.14)):
        box(f'{name}_shelf{k}', (depth, yb - ya, 0.025), (x, (ya + yb) / 2, z), M['orange'], bev=0.004, collection=col, lm='furn')
        box(f'{name}_lip{k}', (0.03, yb - ya, 0.05), (x + depth / 2 - 0.015, (ya + yb) / 2, z + 0.035), M['orange'], bev=0.004, collection=col, lm='furn')
        y = ya + 0.14
        while y < yb - 0.12:
            if rnd.random() < 0.88: ball(f'{name}_ball{k}_{int(y * 100)}', (x + 0.02, y, z + 0.0125 + BALL_R), M[rnd.choice(BALL_MATS)], col)
            y += 2 * BALL_R + 0.02
    for k, y in enumerate((ya, yb)):
        box(f'{name}_end{k}', (depth, 0.03, 1.3), (x, y, 0.65), M['orange'], bev=0.004, collection=col, lm='furn')


# ---------------------------------------------------------------- the lanes' heads
def settees(M, col, rnd):
    """At each pair's head: the curved fibreglass settee (orange seat shells in a cream outer shell) facing the lanes,
    two loose orange shell chairs, the Brunswick scoring console with its overhead projector, and the ball return's
    hood with its chrome rack (balls in it on the lanes nobody bowls)."""
    for a, b in PAIRS:
        yc = PAIR_Y[a]
        settee(f'settee{a}', Vector((X_SETTEE, yc, 0)), M, col)
        console(f'console{a}', Vector((X_CONSOLE, yc, 0)), a, b, M, col)
        hood(f'hood{a}', Vector((X_HOOD, yc, 0)), M, col)
        shell_chair(f'chair{a}', Vector((-7.9, yc + 1.35, 0)), math.radians(-30), M, col)
    for a in (22, 20, 18):                                                       # a house ball waiting on each rack (the bowlers' own are their lanes')
        ball(f'rack_ball_{a}', RACK_SPOTS[a][2], M['ball_slate'], col)


def settee(name, c, M, col, R=1.25, a0=-50, a1=50, n=4):
    """A curved bank of moulded seats facing +x round c (the arc's centre lies ahead of it): a cream outer shell, n
    orange seat shells, chrome feet."""
    ctr = c + Vector((R, 0, 0))
    def at(a, r, z): return ctr + Vector((-math.cos(math.radians(a)) * r, math.sin(math.radians(a)) * r, z))
    bm = bmesh.new(); seg = 40
    # the outer shell: a curved back (0.42 to 0.95 m) and the base under the seats
    for (r0, r1, z0, z1) in ((R - 0.02, R + 0.04, 0.12, 0.95), (R - 0.55, R + 0.04, 0.1, 0.4)):
        ring = []
        for i in range(seg + 1):
            a = a0 + (a1 - a0) * i / seg
            ring.append([bm.verts.new(at(a, r, z)) for r, z in ((r0, z0), (r1, z0), (r1, z1), (r0, z1))])
        for A, B in zip(ring, ring[1:]):
            for k in range(4): bm.faces.new((A[k], A[(k + 1) % 4], B[(k + 1) % 4], B[k]))
        bm.faces.new(ring[0][::-1]); bm.faces.new(ring[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = cine._mesh_obj(f'{name}_shell', bm, M['shell_cream'], col, smooth=False); cine.bevel(ob, 0.02, 3, 40); ob['lm'] = 'furn'
    # the seat shells
    for i in range(n):
        a = a0 + (a1 - a0) * (i + 0.5) / n; p = at(a, R - 0.3, 0.42); d = (ctr - p); d.z = 0; d.normalize()
        seat = rounded_slab(f'{name}_seat{i}', 0.46, 0.46, 0.04, 0.12, p, M['shell'], rot=(0, 0, math.atan2(d.y, d.x)), collection=col, lm='furn')
        bk = rounded_slab(f'{name}_back{i}', 0.46, 0.05, 0.42, 0.1, at(a, R - 0.05, 0.68), M['shell'], rot=(math.radians(-8), 0, math.atan2(d.y, d.x) + math.pi / 2), collection=col, lm='furn')
    for a in (a0 + 5, 0, a1 - 5):
        cyl(f'{name}_foot{int(a)}', 0.025, 0.1, at(a, R - 0.3, 0.05), M['chrome'], seg=10, collection=col, lm='furn')


def shell_chair(name, p, rot, M, col):
    """A loose moulded shell chair: orange shell on four chrome legs."""
    T_ = Matrix.Translation(p) @ Matrix.Rotation(rot, 4, 'Z')
    obs = [rounded_slab(f'{name}_seat', 0.44, 0.44, 0.03, 0.1, (0, 0, 0.45), M['shell'], collection=col, lm='furn'),
           rounded_slab(f'{name}_back', 0.44, 0.04, 0.36, 0.1, (-0.2, 0, 0.68), M['shell'], rot=(0, math.radians(-12), math.pi / 2), collection=col, lm='furn')]
    for sx in (-1, 1):
        for sy in (-1, 1):
            obs.append(cyl(f'{name}_leg{sx}{sy}', 0.011, 0.45, (0.17 * sx, 0.17 * sy, 0.22), M['chrome'], seg=8, collection=col, lm='furn'))
    for o in obs: cine.place(o, T_)


def console(name, p, a, b, M, col):
    """The Brunswick scoring console: a cream pedestal (a blue crown on its front) under a sloped desk with the score
    sheets, a pole rising behind to the overhead projector head (two lenses) and the pair's lane numbers."""
    box(f'{name}_foot', (0.42, 0.42, 0.04), p + Vector((0, 0, 0.02)), M['chrome'], bev=0.01, collection=col, lm='furn')
    lathe(f'{name}_pedestal', [(0.0, 0.04), (0.16, 0.04), (0.12, 0.2), (0.13, 0.62), (0.2, 0.7), (0.0, 0.7)], M['console'], loc=p, seg=24, collection=col, lm='furn')
    cr = box(f'{name}_crown', (0.004, 0.14, 0.12), p + Vector((0.132, 0, 0.4)), M['crown'], bev=0, collection=col, lm='furn'); uv_rect(cr, 'x')
    desk = rounded_slab(f'{name}_desk', 0.62, 0.9, 0.05, 0.08, p + Vector((0.02, 0, 0.74)), M['console'], rot=(0, math.radians(-10), 0), collection=col, lm='furn')
    for k, dy in enumerate((-0.2, 0.2)):
        sh = box(f'{name}_sheet{k}', (0.26, 0.32, 0.003), p + Vector((0.02, dy, 0.775)), M['score'], rot=(0, math.radians(-10), 0), bev=0, collection=col, lm='furn')
        uv_rect(sh, 'z')
    cyl(f'{name}_pole', 0.025, 1.05, p + Vector((-0.25, 0, 1.25)), M['chrome'], seg=12, collection=col, lm='furn')
    head = rounded_slab(f'{name}_head', 0.3, 0.6, 0.26, 0.08, p + Vector((-0.22, 0, 1.86)), M['console'], collection=col, lm='furn')
    for k, dy in enumerate((-0.14, 0.14)):
        ln = cyl(f'{name}_lens{k}', 0.07, 0.06, p + Vector((-0.05, dy, 1.86)), M['lens'], rot=(0, math.radians(90), 0), seg=20, collection=col, lm='furn')
    for k, (n_, dy) in enumerate(((a, -0.17), (b, 0.17))):                          # the lane numbers on its back, facing the settee
        nb = box(f'{name}_num{k}', (0.004, 0.24, 0.15), p + Vector((-0.375, dy, 1.86)), M[f'num{n_}'], bev=0, collection=col, lm='furn')
        _uv_face_x(nb, dy + 0.12 + p.y, dy - 0.12 + p.y, 1.86 - 0.075, 1.86 + 0.075)


def hood(name, p, M, col):
    """The ball return at the approach's back end: the cream hood (orange top, a blue crown) over the lift, the
    chrome teardrop air vent (the hand dryer) on it, the chrome rails of the rack sweeping back toward the settee."""
    hb = rounded_slab(f'{name}_body', 0.55, 0.42, 0.62, 0.1, p + Vector((0, 0, 0.31)), M['shell_cream'], collection=col, lm='furn')
    top = slab_profile(f'{name}_top', [(-0.29, 0.6), (0.29, 0.6), (0.29, 0.74), (0.05, 0.86), (-0.29, 0.8)], 'y', 0.44, [M['shell'], M['shell']], col, bev=0.03, lm='furn')
    top.location = p
    cr = box(f'{name}_crown', (0.004, 0.16, 0.13), p + Vector((-0.285, 0, 0.42)), M['crown'], bev=0, collection=col, lm='furn'); uv_rect(cr, 'x')
    lathe(f'{name}_dryer', [(0.0, 0.0), (0.07, 0.02), (0.06, 0.08), (0.03, 0.14), (0.0, 0.16)], M['chrome'], loc=p + Vector((0.1, 0, 0.8)), seg=20, collection=col, lm='furn')
    for s in (-1, 1):                                                            # the rails, a sweeping chrome arm
        pts = [p + Vector((-0.25, s * 0.07, 0.5)), p + Vector((-0.6, s * 0.07, 0.5)), p + Vector((X_RACK[1] - p.x + 0.05, s * 0.07, 0.5))]
        tube(f'{name}_rail{s}', pts, 0.014, M['chrome'], col, seg=8, lm='furn')
    lathe(f'{name}_stand', [(0.0, 0.0), (0.12, 0.0), (0.12, 0.02), (0.03, 0.05), (0.025, 0.48), (0.0, 0.48)], M['chrome'], loc=Vector((X_RACK[1] + 0.12, p.y, 0)), seg=16, collection=col, lm='furn')




# ---------------------------------------------------------------- the rail, the bar, the stools
def rail(M, col):
    """The low chrome rail between the concourse and the lanes, a dark wood handrail on posts; open from the
    concourse to the settees at the left."""
    x0, x1 = OPEN_X[1], X_MASK - 0.05
    tube('rail_top', [Vector((x0, YR, 0.92)), Vector((x1, YR, 0.92))], 0.03, M['dark_wood'], col, seg=12, lm='furn')
    tube('rail_low', [Vector((x0, YR, 0.45)), Vector((x1, YR, 0.45))], 0.012, M['chrome'], col, seg=8, lm='furn')
    n = int((x1 - x0) / 1.4)
    for k in range(n + 1):
        x = x0 + (x1 - x0) * k / n
        cyl(f'rail_post{k}', 0.02, 0.9, (x, YR, 0.45), M['chrome'], seg=10, collection=col, lm='furn')
    x2 = OPEN_X[0]                                                               # the settees' side of the opening: a short return to the wall
    tube('rail_left', [Vector((LEFT + 0.05, YR, 0.92)), Vector((x2, YR, 0.92))], 0.03, M['dark_wood'], col, seg=12, lm='furn')
    for k, x in enumerate((LEFT + 0.1, x2)):
        cyl(f'rail_lpost{k}', 0.02, 0.9, (x, YR, 0.45), M['chrome'], seg=10, collection=col, lm='furn')


def bar(M, col, rnd):
    """The bar: a long counter of varnished wood, its top rounded on the drinkers' edge, panelled on their side with a
    chrome foot rail; on the bartender's side (facing the case) the drawers and the open shelves with glasses; the
    stools (chrome pedestals, red vinyl seats, foot rings). Returns the bulbs over it (none: the string of bulbs on its
    fascia hid the drinkers from the case)."""
    x0, x1 = BAR_X; yb, yd = BAR_Y; L = x1 - x0; xc = (x0 + x1) / 2
    yi = yb + 0.32                                                               # the body's back (the open shelves are in front of it)
    box('bar_body', (L, yd + 0.02 - yi, 0.98), (xc, (yi + yd + 0.02) / 2, 0.49), M['bar_wood'], bev=0.006, collection=col, lm='furn')
    box('bar_drawers', (L, yi - yb, 0.2), (xc, (yb + yi) / 2, 0.88), M['bar_wood'], bev=0.006, collection=col, lm='furn')
    box('bar_kick', (L, yi - yb - 0.06, 0.08), (xc, (yb + yi) / 2 + 0.03, 0.04), M['dark_wood'], bev=0.004, collection=col, lm='furn')
    for k in range(int(L / 1.8) + 1):                                            # the shelves' uprights
        box(f'bar_upright{k}', (0.03, yi - yb, 0.7), (x0 + 0.015 + (L - 0.03) * k / int(L / 1.8), (yb + yi) / 2, 0.43), M['bar_wood'], bev=0.004, collection=col, lm='furn')
    rounded_slab('bar_top', L + 0.1, yd - yb + 0.32, 0.05, 0.06, (xc, (yb + yd) / 2 + 0.1, BAR_TOP - 0.025), M['bar_wood'], edge_bev=0.02, collection=col, lm='furn')
    moulding('bar_edge', (x0 - 0.05, yd + 0.24, BAR_TOP - 0.05), (x1 + 0.05, yd + 0.24, BAR_TOP - 0.05), (0, 1, 0), [(0, 0), (0.02, 0.0), (0.035, 0.025), (0.02, 0.05), (0, 0.05)], M['dark_wood'], collection=col, lm='furn')
    tube('bar_footrail', [Vector((x0, yd + 0.12, 0.2)), Vector((x1, yd + 0.12, 0.2))], 0.022, M['chrome'], col, seg=10, lm='furn')
    for k in range(int(L / 1.2) + 1):
        x = x0 + 0.1 + (L - 0.2) * k / int(L / 1.2)
        cyl(f'bar_rail_post{k}', 0.012, 0.2, (x, yd + 0.07, 0.1), M['chrome'], seg=8, collection=col, lm='furn')
    # the drinkers' side: panels (raised frames)
    n = int(L / 0.9)
    for k in range(n):
        u0 = x0 + 0.06 + k * (L - 0.12) / n; u1 = u0 + (L - 0.12) / n - 0.06
        box(f'bar_panel{k}', (u1 - u0, 0.015, 0.6), ((u0 + u1) / 2, yd - 0.215 + 0.25, 0.52), M['bar_wood'], bev=0.006, collection=col, lm='furn')
    # the bartender's side: a run of drawers under the top, open shelves below with tumblers and stacked cups
    for k in range(int(L / 0.6)):
        x = x0 + 0.3 + k * 0.6
        if x > x1 - 0.3: break
        box(f'bar_drawer{k}', (0.54, 0.02, 0.16), (x, yb - 0.005, 0.86), M['bar_wood'], bev=0.006, collection=col, lm='furn')
        box(f'bar_pull{k}', (0.12, 0.02, 0.018), (x, yb - 0.02, 0.86), M['chrome'], bev=0.004, collection=col, lm='furn')
    for z in (0.08, 0.42):
        box(f'bar_shelf{int(z * 100)}', (L - 0.12, 0.34, 0.02), (xc, yb + 0.14, z), M['bar_wood'], bev=0.004, collection=col, lm='furn')
        x = x0 + 0.25
        while x < x1 - 0.25:
            if rnd.random() < 0.5:
                for j in range(rnd.randint(3, 6)): glass(f'shelf_glass{int(z * 100)}_{int(x * 100)}_{j}', Vector((x + j * 0.085, yb + 0.12, z + 0.01)), M, col, h=0.11, r=0.035)
                x += 0.6
            else:
                for j in range(rnd.randint(3, 8)): lathe(f'cup{int(z * 100)}_{int(x * 100)}_{j}', [(0.0, 0.0), (0.03, 0.0), (0.042, 0.1), (0.0, 0.1)], M['paper'], loc=(x, yb + 0.12, z + 0.01 + j * 0.022), seg=12, collection=col, lm='furn')
                x += 0.35
    # the stools
    for k, x in enumerate(STOOLS): stool(f'stool{k}', Vector((x, STOOL_Y, 0)), M, col)
    return []                                                                    # (a fascia of bulbs over the bar hid the drinkers from the case)


def stool(name, p, M, col):
    """A bar stool: a round red vinyl seat with a chrome band, a chrome column, a foot ring, a domed foot."""
    lathe(f'{name}_foot', [(0.0, 0.0), (0.2, 0.0), (0.19, 0.02), (0.07, 0.06), (0.04, 0.1), (0.0, 0.1)], M['chrome'], loc=p, seg=24, collection=col, lm='furn')
    cyl(f'{name}_column', 0.03, STOOL_SEAT - 0.16, p + Vector((0, 0, (STOOL_SEAT - 0.16) / 2 + 0.08)), M['chrome'], seg=14, collection=col, lm='furn')
    tube(f'{name}_ring', circle(p + Vector((0, 0, FOOT_RING)), 0.19, (1, 0, 0), (0, 1, 0), n=24), 0.011, M['chrome'], col, closed=True, seg=8, lm='furn')
    for a in (0, 120, 240):
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        tube(f'{name}_spoke{a}', [p + Vector((0, 0, FOOT_RING)) + d * 0.03, p + Vector((0, 0, FOOT_RING)) + d * 0.19], 0.008, M['chrome'], col, seg=6, lm='furn')
    lathe(f'{name}_seat', [(0.0, STOOL_SEAT - 0.09), (0.2, STOOL_SEAT - 0.09), (0.205, STOOL_SEAT - 0.03), (0.195, STOOL_SEAT - 0.005), (0.15, STOOL_SEAT), (0.0, STOOL_SEAT)], M['vinyl'], loc=p, seg=28, collection=col, lm='furn')
    lathe(f'{name}_band', [(0.207, STOOL_SEAT - 0.088), (0.207, STOOL_SEAT - 0.06), (0.0, STOOL_SEAT - 0.06)], M['chrome'], loc=p, seg=28, collection=col, lm='furn')


def glass(name, p, M, col, h=0.1, r=0.04, fill=None):
    """A tumbler (an old-fashioned glass), optionally filled."""
    lathe(name, [(0.0, 0.0), (r * 0.9, 0.0), (r, h), (r * 0.92, h), (r * 0.82, 0.012), (0.0, 0.012)], M['glass'], loc=p, seg=16, collection=col, role='glass')
    if fill: lathe(f'{name}_fill', [(0.0, 0.013), (r * 0.84, 0.013), (r * 0.88, h * 0.62), (0.0, h * 0.62)], M[fill], loc=p, seg=16, collection=col, lm='furn')


def bottle(name, p, M, col, mat='beer', h=0.24):
    """A long-neck bottle with a cream label."""
    lathe(name, [(0.0, 0.0), (0.03, 0.0), (0.031, 0.006), (0.031, h * 0.6), (0.018, h * 0.78), (0.012, h * 0.95), (0.013, h), (0.0, h)], M[mat], loc=p, seg=16, collection=col, lm='furn')
    lathe(f'{name}_label', [(0.0315, h * 0.18), (0.0315, h * 0.42), (0.0, h * 0.42)], M['label'], loc=p, seg=16, collection=col, lm='furn')


def bar_things(M, col, rnd):
    """On the counter: before Donny a woven blue basket of beer nuts and a soda can; Walter's beer bottle and an
    ashtray; the Stranger's sarsaparilla bottle; napkins, a glass or two along the bar."""
    z = BAR_TOP; yd = BAR_Y[1]
    xd, xw, xs = SEAT_OF['donny'], SEAT_OF['walter'], SEAT_OF['stranger']
    lathe('nut_basket', [(0.0, 0.0), (0.06, 0.0), (0.1, 0.05), (0.095, 0.05), (0.055, 0.008), (0.0, 0.008)], M['basket'], loc=(xd + 0.12, yd - 0.18, z), seg=24, collection=col, lm='furn')
    lathe('nut_heap', [(0.0, 0.02), (0.085, 0.035), (0.04, 0.055), (0.0, 0.06)], M['nuts'], loc=(xd + 0.12, yd - 0.18, z), seg=16, collection=col, lm='furn')
    lathe('soda_can', [(0.0, 0.0), (0.033, 0.0), (0.033, 0.122), (0.027, 0.125), (0.0, 0.125)], M['ball_amber'], loc=(xd - 0.12, yd - 0.12, z), seg=16, collection=col, lm='furn')
    bottle('walter_beer', Vector((xw + 0.16, yd - 0.12, z)), M, col)
    lathe('ashtray_w', [(0.0, 0.0), (0.06, 0.0), (0.065, 0.025), (0.05, 0.025), (0.045, 0.01), (0.0, 0.01)], M['ashtray'], loc=(xw - 0.15, yd - 0.2, z), seg=20, collection=col, lm='furn')
    bottle('sarsaparilla_bottle', Vector((xs + 0.2, yd - 0.16, z)), M, col, mat='sarsaparilla', h=0.22)
    for k, x in enumerate((xw - 0.02, SEAT_OF['dude'] + 0.02, xs + 0.0)):
        box(f'napkin{k}', (0.12, 0.12, 0.002), (x, yd - 0.12, z + 0.001), M['paper'], rot=(0, 0, rnd.uniform(-0.3, 0.3)), bev=0, collection=col, lm='furn')
    lathe('ashtray_s', [(0.0, 0.0), (0.06, 0.0), (0.065, 0.025), (0.05, 0.025), (0.045, 0.01), (0.0, 0.01)], M['ashtray'], loc=(2.6, yd - 0.22, z), seg=20, collection=col, lm='furn')


def jukebox(name, p, M, col):
    """A 1950s jukebox beside the bar's far end (it plays 'Tumbling Tumbleweeds'): a wooden cabinet, a glowing
    arch of amber and red tubes, a chrome grille."""
    box(f'{name}_cabinet', (0.85, 0.62, 1.05), p + Vector((0, 0, 0.525)), M['bar_wood'], bev=0.02, collection=col, lm='furn')
    arch = []
    for i in range(25):
        a = math.pi * i / 24; arch.append(p + Vector((-0.4 * math.cos(a), -0.3, 1.05 + 0.42 * math.sin(a))))
    tube(f'{name}_arch', arch, 0.05, M['juke_glow'], col, seg=10)                  # the glowing parts: no light map
    tube(f'{name}_arch_red', [q + Vector((0, -0.04, 0)) for q in arch[2:-2]], 0.02, M['juke_red'], col, seg=8)
    box(f'{name}_dome', (0.7, 0.5, 0.36), p + Vector((0, 0.02, 1.2)), M['juke_glow'], bev=0.1, seg=4, collection=col)
    box(f'{name}_grille', (0.6, 0.02, 0.45), p + Vector((0, -0.315, 0.45)), M['chrome'], bev=0.01, collection=col, lm='furn')


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
FLUO = (1.0, 0.93, 0.8)                    # warm-white fluorescent tubes (the film's warm, saturated alley)
BULB = (1.0, 0.76, 0.46)
NEON = (0.45, 0.62, 1.0)


def lights(bulbs):
    """The troffers (area lights under the phantom ceiling), the pin-deck lights under the masking, the bulbs over the
    bar, a little blue from each neon star, the jukebox's glow. Returns the lights (true size: `shrink` brings them in)."""
    out = []
    def light(name, kind, loc, energy, colour, **kw):
        ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = colour
        for k, v in kw.items(): setattr(ld, k, v)
        ob = cine.link(bpy.data.objects.new(name, ld)); ob.location = loc; out.append(ob)
        if kind in ('AREA', 'SPOT', 'SUN'): ob.visible_camera = False; ob.visible_glossy = False
        return ob
    for k, ((x, y), (sx, sy)) in enumerate(troffer_grid()):
        light(f'troffer{k}', 'AREA', (x, y, RH - 0.02), 60.0, FLUO, shape='RECTANGLE', size=sx, size_y=sy)
    for k, x in enumerate(BAR_X[0] + 0.6 + i * 1.4 for i in range(6)):          # recessed cans over the bar
        light(f'can{k}', 'SPOT', (x, -5.9, RH - 0.02), 120.0, BULB, spot_size=math.radians(75), spot_blend=0.6, shadow_soft_size=0.06)
    for n, y in LANES.items():                                                   # the deck lights: the pins glow under the masking
        ob = light(f'deck{n}', 'AREA', (X_HEAD + 0.35, y, MASK_Z[0] - 0.04), 70.0, (1.0, 0.95, 0.86), shape='RECTANGLE', size=0.9, size_y=LW)
    for k, b in enumerate(bulbs[::4]): light(f'bulb{k}', 'POINT', b, 4.0, BULB, shadow_soft_size=0.03)
    for k, (c, r) in enumerate(STARS): light(f'neon{k}', 'POINT', c + (Vector((0, -0.25, 0)) if c.y > 0 else Vector((0.25, 0, 0))), 14.0, NEON, shadow_soft_size=r * 0.6)
    light('jukebox', 'POINT', JUKE + Vector((0, -0.6, 1.2)), 20.0, (1.0, 0.6, 0.3), shadow_soft_size=0.2)
    return out


JUKE = Vector((6.3, -5.7, 0))


def shrink(objs, lights_):
    """Bring the alley, built at its true size, into the module (as the throne room)."""
    S_ = Matrix.Scale(SCALE, 4)
    for o in objs: o.matrix_world = S_ @ o.matrix_world
    for l in lights_:
        l.location = l.location * SCALE
        d = l.data
        if d.type == 'AREA': d.size *= SCALE; d.size_y *= SCALE
        if d.type in ('POINT', 'SPOT', 'AREA'): d.energy *= SCALE ** 2; d.shadow_soft_size *= SCALE
    bpy.context.view_layer.update()
