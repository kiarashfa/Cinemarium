# The Godfather · Don Corleone's study at the Long Beach mall, on the afternoon of Connie's wedding (summer 1945),
# after Dean Tavoularis's set: dark mahogany panelling, an elliptical arch across the room before the desk, the two
# tall windows behind the Don closed with louvered shutters (the sun of the garden party slicing through them), the
# fireplace with the family's photographs and a dark landscape in gilt over it, dusty rose damask above the wainscot
# by the glazed cabinet and the lamp, the black tufted leather chair; the big carved desk and the Don's olive-gold
# tufted chair, the two hard wooden chairs facing it, Hagen's black club chair by the small table with the red-shaded
# lamp and the telephone, Sonny's window on the left wall with the decanters below the double sconce; a Persian
# vase carpet on dark boards.
#
# The set's door is in the wall facing the desk; here it is turned onto the room's right side (a partition, full
# height from the arch back, a kerb in front), and the front hall lies beyond it: cream paper with red sprays over a
# dark wainscot, the glazed front door onto the garden in the sun. Where the module's top cuts the walls and the arch:
# a dark `section` face.
import math, os, random
import bpy, bmesh
from mathutils import Vector, Matrix
import cine
from cine import box, cyl, material, lathe, place, rounded_slab, slab_profile, cloth_panel
from rooms.seinfeld import Face, uv_rect, tube, circle, spine_row, _glow

W, D, H = 9.6, 7.6, 3.0
T = 0.14                                   # the module's walls
LEFT, BACK, RIGHT, FRONT = -W / 2 + T, D / 2 - T, W / 2 - T, -D / 2 + T
RH = 2.9                                   # the ceilings (phantoms above); the cut
KH = 0.22                                  # the cut-away's kerb
TEX = os.path.join(cine.OUT, 'textures', 'the-godfather')
tx = lambda n: os.path.join(TEX, n)
PH = lambda n: os.path.join(cine.CACHE, 'polyhaven', n, f'{n}_1k.gltf')

XP, PT = 2.45, 0.14                        # the partition between the study and the hall: its study face, its thickness
XW = XP + PT                               # its hall face
P_FULL = -0.12                             # full height from here back (the arch lands on it); a kerb in front
ARCH = (-0.12, 0.3, 2.3, 2.74)             # the arch: y0, y1 (its soffit's depth), springing, crown
PIER = 0.3                                 # how far its piers stand out from the left wall and the partition
DOOR = (0.58, 1.5, 2.3)                    # the study door in the partition: y0, y1 (its hinge), head
WINDOWS = (-3.0, -2.0)                     # the two windows behind the desk (x centres, back wall)
LWIN = -1.0                                # Sonny's window (y centre, left wall)
WW, WIN_Z = 0.78, (0.5, 2.4)               # their width, sill and head
FIRE = -0.35                               # the fireplace (x centre, back wall)
PAPER_X = 0.6                              # from here to the partition the back wall is papered above a high wainscot
WAIN, WAIN_HI = 1.0, 1.45                  # the panelled walls' chair rail; the papered walls' wainscot
FRIEZE = 2.55                              # the frieze rail under the cornice
FRONT_DOOR = (3.55, 0.92, 2.36, 0.26)      # the hall's front door: x centre, width, head, its sidelights' width
DESK = Vector((-2.5, 1.72, 0.0))           # the desk's centre; it faces -y (1.9 x 0.95, its top at 0.78)
DESK_W, DESK_D, DESK_H = 1.9, 0.95, 0.78
CHAIRS = {'vito': (-2.5, 2.74), 'hagen': (-3.75, -2.3)}
SEAT = {'vito': 0.5, 'hagen': 0.44}        # cushion tops
SIDE_CHAIRS = ((-3.08, 0.8), (-1.92, 0.82))
SPOTS = {'bonasera': ((-2.5, 0.8), (0.0, 1.0)), 'sonny': ((-4.12, -0.32), (0.55, 0.84))}   # where they stand, facing
CAT_DESK = Vector((-2.84, 1.97, DESK_H))   # where the Don sets the cat down (close: he leans to it)


def chair_at(who):
    """A seat's centre and its facing: the Don faces the room; Hagen's chair is turned toward the desk."""
    p = Vector((*CHAIRS[who], 0.0))
    if who == 'vito': return p, Vector((0, -1, 0))
    f = Vector((DESK.x - 0.4, DESK.y - 0.9, 0)) - p; f.z = 0
    return p, f.normalized()


# ---------------------------------------------------------------- materials
def mats():
    M = {}
    M['floor'] = material('floor_boards', rough=0.55, maps={'color': tx('floor_color.jpg'), 'normal': tx('floor_normal.jpg')}, scale=0.8, normal_strength=0.35)   # no coat: on a floor this dark the web's reflections read as grey haze
    M['panel'] = material('mahogany_panel', rough=0.45, maps={'color': tx('panel_color.jpg'), 'normal': tx('panel_normal.jpg')}, scale=1.2, normal_strength=0.3, coat=0.3, coat_rough=0.3)
    M['mahogany'] = material('mahogany', rough=0.35, maps={'color': tx('mahogany_color.jpg'), 'normal': tx('wood_normal.jpg')}, scale=1.0, normal_strength=0.3, coat=0.6, coat_rough=0.15)
    M['damask'] = material('damask_paper', rough=0.75, maps={'color': tx('damask_color.jpg')}, scale=0.75, sheen=0.25, sheen_tint=(0.5, 0.35, 0.3))
    M['hall_paper'] = material('hall_paper', rough=0.8, maps={'color': tx('hall_paper_color.jpg')}, scale=0.9)
    M['olive'] = material('olive_leather', rough=0.42, maps={'color': tx('olive_leather_color.jpg'), 'normal': tx('olive_leather_normal.jpg')}, scale=0.45, normal_strength=0.5, coat=0.35, coat_rough=0.3)
    M['black_leather'] = material('black_leather', rough=0.38, maps={'color': tx('black_leather_color.jpg'), 'normal': tx('leather_normal.jpg')}, scale=0.45, normal_strength=0.5, coat=0.45, coat_rough=0.25)
    M['brown_leather'] = material('brown_leather', rough=0.45, maps={'color': tx('brown_leather_color.jpg'), 'normal': tx('leather_normal.jpg')}, scale=0.45, normal_strength=0.5, coat=0.25)
    M['rug'] = material('vase_carpet', rough=0.95, maps={'color': tx('rug_color.jpg'), 'normal': tx('pile_normal.jpg')}, scale=1.0, normal_strength=0.4, specular=0.25,
                        sheen=0.3, sheen_tint=(0.4, 0.3, 0.25))
    M['runner'] = material('runner_red', rough=0.9, maps={'color': tx('runner_color.jpg'), 'normal': tx('pile_normal.jpg')}, scale=0.5, normal_strength=0.4, sheen=0.3, sheen_tint=(0.5, 0.2, 0.2))
    M['ceiling'] = material('ceiling', rough=0.9, maps={'color': tx('ceiling_color.jpg')}, scale=1.4)
    M['books'] = material('books', rough=0.55, maps={'color': tx('books_color.jpg')}, scale=1.0)
    for k in range(5): M[f'photo{k}'] = material(f'photo{k}', rough=0.3, maps={'color': tx(f'photo{k}.jpg')}, scale=1.0, coat=0.6)
    M['crest'] = material('crest_print', rough=0.4, maps={'color': tx('crest_print.jpg')}, scale=1.0, coat=0.5)
    M['view'] = material('garden_view', rough=0.9, maps={'color': tx('garden_view.jpg')}, scale=1.0)
    M['shade'] = material('lamp_shade', rough=0.8, maps={'color': tx('linen_color.jpg')}, scale=0.4, emission=(1.0, 0.8, 0.52), emission_strength=1.4)
    M['red_shade'] = material('red_shade', rough=0.8, maps={'color': tx('red_shade_color.jpg')}, scale=0.4, emission=(1.0, 0.32, 0.18), emission_strength=1.1)
    M['sheer'] = material('sheer_lit', (0.92, 0.88, 0.8), rough=0.7, emission=(1.0, 0.9, 0.72), emission_strength=4.0)
    M['brass'] = material('brass', (0.7, 0.5, 0.22), rough=0.28, metal=1.0)
    M['bronze'] = material('bronze_dark', (0.14, 0.09, 0.05), rough=0.35, metal=0.9)
    M['gilt'] = material('gilt', (0.66, 0.48, 0.2), rough=0.3, metal=0.9)
    M['bakelite'] = material('bakelite', (0.015, 0.014, 0.013), rough=0.18, coat=0.8)
    M['paper'] = material('paper', (0.84, 0.82, 0.76), rough=0.85)
    M['iron'] = material('cast_iron', (0.11, 0.1, 0.09), rough=0.55, metal=0.6)
    M['marble'] = material('marble_dark', (0.06, 0.055, 0.05), rough=0.15, coat=0.8)
    M['firebox'] = material('firebox', (0.02, 0.018, 0.016), rough=0.9)
    M['ivory'] = material('ivory_china', (0.82, 0.78, 0.68), rough=0.2, coat=0.7)
    M['porcelain'] = material('famille_rose', (0.78, 0.66, 0.56), rough=0.2, coat=0.8)
    M['leaf'] = material('ivy_leaf', (0.06, 0.12, 0.04), rough=0.55)
    M['glass'] = material('crystal', (0.6, 0.62, 0.6), rough=0.05, coat=1.0)
    M['wine'] = material('wine', (0.14, 0.01, 0.02), rough=0.08, coat=1.0)
    M['cream'] = material('cream_paint', (0.72, 0.66, 0.54), rough=0.5)
    M['kerb'] = material('kerb', (0.18, 0.13, 0.1), rough=0.9)
    M['section'] = material('section', (0.03, 0.028, 0.026), rough=0.92)
    _glow(M['view'], 6.0)   # the garden in the sun, glimpsed between the louvers: it shines on the web as in the renders
    return M


# ---------------------------------------------------------------- small kit
SKIRT = [(0, 0), (0.02, 0), (0.02, 0.15), (0.014, 0.165), (0.006, 0.175), (0, 0.18)]
RAIL = [(0, 0), (0.016, 0.004), (0.026, 0.016), (0.024, 0.032), (0.012, 0.04), (0, 0.044)]
CAP = [(0, 0), (0.035, 0.0), (0.042, 0.014), (0.036, 0.034), (0.02, 0.044), (0, 0.05)]
CORNICE = [(0, 0), (0.02, 0), (0.02, 0.03), (0.05, 0.05), (0.09, 0.09), (0.12, 0.13), (0.13, 0.17), (0, 0.17)]
M_ = {}


def _spans(L, cuts):
    out, u = [], 0.0
    for c0, c1 in sorted(cuts):
        if c0 > u + 1e-4: out.append((u, c0))
        u = max(u, c1)
    if u < L - 1e-4: out.append((u, L))
    return out


def panels(face, name, u0, u1, z0, z1, col, o=0.0, width=0.55, mat=None):
    """A row of raised and fielded panels between rails, about `width` wide, from u0 to u1, z0 to z1."""
    mat = mat or M_['panel']; L = u1 - u0
    if L < 0.15 or z1 - z0 < 0.1: return
    n = max(1, int(round(L / width))); pw = (L - 0.07 * (n + 1)) / n
    for k in range(n):
        a = u0 + 0.07 + k * (pw + 0.07)
        face.slab(f'{name}_p{k}', a, a + pw, z0 + 0.07, z1 - 0.07, o, 0.018, mat, col, bev=0.012, lm='arch')      # the field
        face.slab(f'{name}_f{k}', a - 0.012, a + pw + 0.012, z0 + 0.058, z1 - 0.058, o, 0.008, mat, col, bev=0.004, lm='arch')   # its frame


def wall_finish(face, name, col, openings=(), paper=None, wain=WAIN):
    """A wall dressed as the study's: skirting, raised panels below the chair rail; above, tall panels to the frieze rail
    (or, `paper` given, that paper over a higher wainscot); the frieze and the cornice. `openings` [(u0, u1, z0, z1)]
    are left bare, the wall dressed under a sill and over a head (above the casing)."""
    ops = list(openings)
    def upper(nm, a, b, z0):
        if paper is None:
            face.slab(f'{nm}_upper', a, b, z0, FRIEZE, 0.0, 0.01, M_['panel'], col, bev=0, lm='arch')
            panels(face, f'{nm}_hi', a, b, z0 + 0.04, FRIEZE - 0.02, col, o=0.01, width=0.5)
        else:
            face.slab(f'{nm}_paper', a, b, z0, FRIEZE, 0.0, 0.004, paper, col, bev=0, lm='arch')
    for k, (a, b) in enumerate(_spans(face.L, [(a - 0.06, b + 0.06) for a, b, z0, z1 in ops if z0 < wain])):
        face.run(f'{name}_skirt{k}', a, b, 0.0, SKIRT, M_['panel'], col, o=0.0, lm='arch')
        face.slab(f'{name}_wain{k}', a, b, 0.0, wain, 0.0, 0.012, M_['panel'], col, bev=0, lm='arch')
        panels(face, f'{name}_lo{k}', a, b, 0.18, wain - 0.04, col, o=0.012)
        face.run(f'{name}_cap{k}', a, b, wain - 0.03, CAP, M_['panel'], col, o=0.012, lm='arch')
    for k, (a, b) in enumerate(_spans(face.L, [(a - 0.06, b + 0.06) for a, b, z0, z1 in ops if z1 > wain])):
        upper(f'{name}{k}', a, b, wain)
    for k, (a, b, z0, z1) in enumerate(ops):
        if 0.05 < z0 < wain:                                                   # under a sill: a plain board, the skirting
            face.slab(f'{name}_under{k}', a - 0.06, b + 0.06, 0.0, z0 - 0.04, 0.0, 0.012, M_['panel'], col, bev=0, lm='arch')
            face.run(f'{name}_uskirt{k}', a - 0.06, b + 0.06, 0.0, SKIRT, M_['panel'], col, o=0.012, lm='arch')
        if wain < z1 < FRIEZE - 0.2:                                           # over a head and its casing
            upper(f'{name}_over{k}', a - 0.06, b + 0.06, z1 + 0.16)
    for k, (a, b) in enumerate(_spans(face.L, [(a - 0.06, b + 0.06) for a, b, z0, z1 in ops if z1 > FRIEZE - 0.05])):
        face.run(f'{name}_frieze{k}', a, b, FRIEZE, RAIL, M_['panel'], col, o=0.004, lm='arch')
        face.slab(f'{name}_band{k}', a, b, FRIEZE + 0.04, RH, 0.0, 0.008, M_['panel'], col, bev=0, lm='arch')
    face.run(f'{name}_cornice', 0.0, face.L, RH - 0.17, CORNICE, M_['panel'], col, o=0.008, lm='arch')


def casing(face, name, u0, u1, z0, head, col, w=0.1, o=0.0):
    """A broad moulded architrave round an opening, with a pedimented head (the set's carved casings)."""
    t = 0.028
    for k, u in enumerate((u0 - w, u1)):
        face.slab(f'{name}_leg{k}', u, u + w, z0, head, o, t, M_['panel'], col, bev=0.006, lm='arch')
        face.slab(f'{name}_bead{k}', u + 0.02, u + w - 0.02, z0, head, o + t, 0.008, M_['panel'], col, bev=0.004, lm='arch')
    face.slab(f'{name}_head', u0 - w, u1 + w, head, head + w, o, t, M_['panel'], col, bev=0.006, lm='arch')
    face.slab(f'{name}_crown', u0 - w - 0.03, u1 + w + 0.03, head + w, head + w + 0.05, o, t + 0.02, M_['panel'], col, bev=0.008, lm='arch')


# ---------------------------------------------------------------- the shell
def _faces():
    """The walls as the rooms see them."""
    return {'left': Face((LEFT, FRONT), (LEFT, BACK), (1, 0)),                 # the left wall, front to back
            'back': Face((LEFT, BACK), (XP, BACK), (0, -1)),                   # the study's back wall, left to right
            'part': Face((XP, BACK), (XP, P_FULL), (-1, 0)),                   # the partition's study face, back to front
            'hall_part': Face((XW, P_FULL), (XW, BACK), (1, 0)),               # its hall face, front to back
            'hall_back': Face((XW, BACK), (RIGHT, BACK), (0, -1))}             # the hall's back wall


def shell(M, arch, furn, phantom):
    """The floors, the module's left and back walls (the windows, the front door), the partition with its door, the
    arch and its piers; the finishes; kerbs and phantoms."""
    M_.clear(); M_.update(M)
    box('subfloor', (W, D, 0.03), (0, 0, -0.027), M['kerb'], bev=0, collection=arch, lm='arch')
    box('floor', (W - 2 * T + 0.002, D - T - 0.002, 0.02), (0, -T / 2, -0.01), M['floor'], bev=0, collection=arch, lm='arch')
    # the module's left wall, round Sonny's window
    y0, y1 = LWIN - WW / 2, LWIN + WW / 2; s0, s1 = WIN_Z
    for k, (a, b) in enumerate(((-D / 2, y0), (y1, D / 2))):
        box(f'left_wall_{k}', (T, b - a, RH), (-W / 2 + T / 2, (a + b) / 2, RH / 2), M['panel'], bev=0, collection=arch, lm='arch')
    box('left_wall_sill', (T, y1 - y0, s0), (-W / 2 + T / 2, LWIN, s0 / 2), M['panel'], bev=0, collection=arch, lm='arch')
    box('left_wall_head', (T, y1 - y0, RH - s1), (-W / 2 + T / 2, LWIN, (RH + s1) / 2), M['panel'], bev=0, collection=arch, lm='arch')
    # the module's back wall: the two windows, the partition, the front door and its sidelights
    xs = sorted([(c - WW / 2, c + WW / 2, s0, s1) for c in WINDOWS])
    fx, fw, fh, sw = FRONT_DOOR
    xs.append((fx - fw / 2 - sw - 0.05, fx + fw / 2 + sw + 0.05, 0.0, fh))
    cuts = [(a, b) for a, b, z0, z1 in xs]
    for k, (a, b) in enumerate(_spans(W, [(a + W / 2, b + W / 2) for a, b in cuts])):
        box(f'back_wall_{k}', (b - a, T, RH), (a - W / 2 + (b - a) / 2, D / 2 - T / 2, RH / 2), M['panel'], bev=0, collection=arch, lm='arch')
    for k, (a, b, z0, z1) in enumerate(xs):
        if z0 > 0: box(f'back_wall_sill{k}', (b - a, T, z0), ((a + b) / 2, D / 2 - T / 2, z0 / 2), M['panel'], bev=0, collection=arch, lm='arch')
        box(f'back_wall_head{k}', (b - a, T, RH - z1), ((a + b) / 2, D / 2 - T / 2, (RH + z1) / 2), M['panel'], bev=0, collection=arch, lm='arch')
    # the partition: full height from P_FULL back with the study door, a kerb in front
    d0, d1, dh = DOOR
    for k, (a, b) in enumerate(((P_FULL, d0), (d1, BACK))):
        box(f'wall_part_{k}', (PT, b - a, RH), (XP + PT / 2, (a + b) / 2, RH / 2), M['panel'], bev=0, collection=arch, lm='arch')
    box('wall_part_head', (PT, d1 - d0, RH - dh), (XP + PT / 2, (d0 + d1) / 2, (RH + dh) / 2), M['panel'], bev=0, collection=arch, lm='arch')
    box('kerb_part', (PT, P_FULL - FRONT, KH), (XP + PT / 2, (P_FULL + FRONT) / 2, KH / 2), M['kerb'], bev=0.002, collection=arch, lm='arch')
    for k, y in enumerate((d0, d1)): box(f'door_jamb{k}', (PT, 0.025, dh), (XP + PT / 2, y + (0.0125 if k == 0 else -0.0125), dh / 2), M['panel'], bev=0.002, collection=arch, lm='arch')
    box('door_soffit', (PT, d1 - d0, 0.025), (XP + PT / 2, (d0 + d1) / 2, dh - 0.0125), M['panel'], bev=0.002, collection=arch, lm='arch')
    # the cut-away
    box('kerb_front', (W, T, KH), (0, -D / 2 + T / 2, KH / 2), M['kerb'], bev=0.002, collection=arch, lm='arch')
    box('kerb_right', (T, D - 2 * T, KH), (W / 2 - T / 2, 0, KH / 2), M['kerb'], bev=0.002, collection=arch, lm='arch')
    # phantoms: the ceilings, the missing walls, the partition above its kerb (closed, for the bounce light)
    box('ceiling', (W, D, 0.04), (0, 0, RH + 0.02), M['ceiling'], bev=0, collection=phantom, bake_only=1)
    box('front_wall', (W, T, RH - KH), (0, -D / 2 + T / 2, KH + (RH - KH) / 2), M['panel'], bev=0, collection=phantom, bake_only=1)
    box('right_wall', (T, D, RH - KH), (W / 2 - T / 2, 0, KH + (RH - KH) / 2), M['hall_paper'], bev=0, collection=phantom, bake_only=1)
    box('part_phantom', (PT, P_FULL - FRONT, RH - KH), (XP + PT / 2, (P_FULL + FRONT) / 2, KH + (RH - KH) / 2), M['panel'], bev=0, collection=phantom, bake_only=1)
    _arch(M, arch)
    _finishes(M, arch)


def _arch(M, col):
    """The elliptical arch across the study before the desk, carried on panelled piers at the left wall and at the
    partition's end, its spandrels panelled up to the cut, a moulded impost at the springing."""
    y0, y1, zs, zc = ARCH; xl, xr = LEFT + PIER, XP - PIER; cx, a = (xl + xr) / 2, (xr - xl) / 2
    pts = [(xl, RH), (xl, zs)] + [(cx - a * math.cos(math.pi * k / 48), zs + (zc - zs) * math.sin(math.pi * k / 48)) for k in range(1, 48)] + [(xr, zs), (xr, RH)]
    ob = slab_profile('solid_arch', pts, 'y', y1 - y0, [M['panel'], M['panel']], col, bev=0.004, lm='arch')
    ob.location.y = (y0 + y1) / 2
    for k, (x0, x1) in enumerate(((LEFT, xl), (xr, XP))):                      # the piers, full height
        box(f'solid_pier{k}', (x1 - x0, y1 - y0, RH), ((x0 + x1) / 2, (y0 + y1) / 2, RH / 2), M['panel'], bev=0.004, collection=col, lm='arch')
        for j, (z0, z1) in enumerate(((0.2, 0.95), (1.05, zs - 0.12))):        # sunk panels on their faces, front and back
            for s, yy in ((-1, y0), (1, y1)):
                box(f'pier{k}_panel{j}{s}', (x1 - x0 - 0.1, 0.012, z1 - z0), ((x0 + x1) / 2, yy + s * 0.006, (z0 + z1) / 2), M['panel'], bev=0.006, collection=col, lm='arch')
        box(f'pier{k}_impost', (x1 - x0 + 0.06, y1 - y0 + 0.06, 0.07), ((x0 + x1) / 2, (y0 + y1) / 2, zs - 0.035), M['panel'], bev=0.012, collection=col, lm='arch')
        box(f'pier{k}_plinth', (x1 - x0 + 0.03, y1 - y0 + 0.03, 0.18), ((x0 + x1) / 2, (y0 + y1) / 2, 0.09), M['panel'], bev=0.006, collection=col, lm='arch')
    # a moulded edge round the arch's face on both sides
    for s, yy in ((-1, y0), (1, y1)):
        ring = [Vector((cx - (a - 0.04) * math.cos(math.pi * k / 48), yy + s * 0.012, zs + (zc - zs - 0.02) * math.sin(math.pi * k / 48))) for k in range(49)]
        tube(f'arch_bead{s}', ring, 0.016, M['panel'], col, seg=8, lm='arch')


def _finishes(M, col):
    """Panelling on the left wall and around the windows and the fireplace; damask over a high wainscot from the
    fireplace to the partition and on the partition; the hall's wainscot and paper; the casings."""
    F = _faces()
    lw = F['left']; s0, s1 = WIN_Z
    wall_finish(lw, 'left', col, openings=[(LWIN - WW / 2 - FRONT, LWIN + WW / 2 - FRONT, s0, s1), (ARCH[0] - FRONT - 0.01, ARCH[1] - FRONT + 0.01, 0, RH)])
    bw = F['back']
    ops = [(c - WW / 2 - LEFT, c + WW / 2 - LEFT, s0, s1) for c in WINDOWS]
    fire = (FIRE - 0.85 - LEFT, FIRE + 0.85 - LEFT)
    wall_finish(Face((LEFT, BACK), (PAPER_X, BACK), (0, -1)), 'back', col, openings=ops + [(fire[0], fire[1], 0.0, WAIN - 0.01)])
    wall_finish(Face((PAPER_X, BACK), (XP, BACK), (0, -1)), 'back_paper', col, paper=M['damask'], wain=WAIN_HI)
    d0, d1, dh = DOOR
    pf = F['part']
    wall_finish(pf, 'part', col, paper=M['damask'], wain=WAIN_HI, openings=[(BACK - d1, BACK - d0, 0.0, dh), (BACK - ARCH[1] - 0.01, BACK - P_FULL, 0, RH)])
    for k, c in enumerate(WINDOWS):                                              # the windows' casings and stools
        casing(bw, f'win{k}_casing', c - WW / 2 - LEFT, c + WW / 2 - LEFT, s0 - 0.04, s1, col, w=0.08)
    casing(lw, 'lwin_casing', LWIN - WW / 2 - FRONT, LWIN + WW / 2 - FRONT, s0 - 0.04, s1, col, w=0.08)
    casing(pf, 'door_casing_s', BACK - d1, BACK - d0, 0.0, dh, col)
    # the hall: a dark wainscot, cream paper with red sprays above, the casings of both doors
    hp, hb = F['hall_part'], F['hall_back']
    fx, fw, fh, sw = FRONT_DOOR
    hall_wall(hp, 'hall_part', col, openings=[(d0 - P_FULL, d1 - P_FULL, 0.0, dh)])
    hall_wall(hb, 'hall_back', col, openings=[(fx - fw / 2 - sw - 0.05 - XW, fx + fw / 2 + sw + 0.05 - XW, 0.0, fh)])
    casing(hp, 'door_casing_h', d0 - P_FULL, d1 - P_FULL, 0.0, dh, col)
    casing(hb, 'front_casing', fx - fw / 2 - sw - 0.05 - XW, fx + fw / 2 + sw + 0.05 - XW, 0.0, fh, col, w=0.1)
    box('lwin_stool', (0.16, WW + 0.2, 0.035), (LEFT + 0.07, LWIN, s0 - 0.02), M['panel'], bev=0.006, collection=col, lm='arch')
    for k, c in enumerate(WINDOWS): box(f'win{k}_stool', (WW + 0.2, 0.16, 0.035), (c, BACK - 0.07, s0 - 0.02), M['panel'], bev=0.006, collection=col, lm='arch')


def hall_wall(face, name, col, openings=()):
    """The hall's walls: skirting and a panelled wainscot to 1 m, the cream paper above (over the doors too), a picture
    rail, the cornice."""
    for k, (a, b) in enumerate(_spans(face.L, [(a - 0.06, b + 0.06) for a, b, z0, z1 in openings])):
        face.run(f'{name}_skirt{k}', a, b, 0.0, SKIRT, M_['panel'], col, lm='arch')
        face.slab(f'{name}_wain{k}', a, b, 0.0, WAIN, 0.0, 0.012, M_['panel'], col, bev=0, lm='arch')
        panels(face, f'{name}_lo{k}', a, b, 0.18, WAIN - 0.04, col, o=0.012)
        face.run(f'{name}_cap{k}', a, b, WAIN - 0.03, CAP, M_['panel'], col, o=0.012, lm='arch')
        face.slab(f'{name}_paper{k}', a, b, WAIN, RH, 0.0, 0.004, M_['hall_paper'], col, bev=0, lm='arch')
    for k, (a, b, z0, z1) in enumerate(openings):
        face.slab(f'{name}_paper_over{k}', a - 0.06, b + 0.06, z1 + 0.15, RH, 0.0, 0.004, M_['hall_paper'], col, bev=0, lm='arch')
    face.run(f'{name}_rail', 0.0, face.L, 2.55, RAIL, M_['panel'], col, o=0.004, lm='arch')
    face.run(f'{name}_cornice', 0.0, face.L, RH - 0.17, CORNICE, M_['panel'], col, o=0.004, lm='arch')


# ---------------------------------------------------------------- the windows: shutters, the garden beyond
def shutters(name, c, n, M, col, open_deg=58.0):
    """Interior louvered shutters filling a window: two leaves, each a frame of stiles and rails round two banks of
    louvers (a mid rail between), the louvers tilted `open_deg` from closed, their inner edge low, so the afternoon
    sun slices in. Returns nothing; the garden behind is drawn bright for the camera only."""
    n = Vector((n[0], n[1], 0)).normalized(); side = Vector((-n.y, n.x, 0)); c = Vector((c[0], c[1], 0))
    z0, z1 = WIN_Z; lw = WW / 2; t = 0.026
    bm = bmesh.new()
    def plank(p, sx, sy, sz, rot=None):
        M_ = Matrix.Translation(p) @ (rot or Matrix.Identity(4)) @ Matrix.Diagonal((sx, sy, sz, 1))
        bmesh.ops.create_cube(bm, size=1.0, matrix=M_)
    R = Matrix.Rotation(math.atan2(side.y, side.x), 4, 'Z')                 # local x along the wall, y into the room
    for k in (-1, 1):
        lc = c + side * k * lw / 2 + n * 0.03
        for s in (-1, 1): plank(Vector((lc.x, lc.y, (z0 + z1) / 2)) + side * s * (lw / 2 - 0.025), 0.05, t, z1 - z0, R)   # stiles
        mid = z0 + (z1 - z0) * 0.42
        for z in (z0 + 0.04, mid, z1 - 0.04): plank(Vector((lc.x, lc.y, z)), lw - 0.1, t, 0.07, R)                    # rails
        tilt = Matrix.Rotation(math.radians(90 - open_deg), 4, Vector((side.x, side.y, 0)))
        for a, b in ((z0 + 0.075, mid - 0.035), (mid + 0.035, z1 - 0.075)):
            m = int((b - a) / 0.046)
            for j in range(m):
                z = a + (j + 0.5) * (b - a) / m
                plank(Vector((lc.x, lc.y, z)), lw - 0.1, 0.056, 0.006, tilt @ R)
    for f in bm.faces: f.smooth = False
    ob = cine._mesh_obj(name, bm, M['panel'], col, smooth=False); ob['lm'] = 'furn'
    # the garden beyond, in the sun: bright for the camera, invisible to light (the sun and the sky come through)
    v = uv_rect(box(f'{name}_view', (WW + 0.2, 0.01, z1 - z0 + 0.2) if abs(n.y) > 0.5 else (0.01, WW + 0.2, z1 - z0 + 0.2), c - n * 0.12 + Vector((0, 0, (z0 + z1) / 2)), M['view'], bev=0, collection=col), 'y' if abs(n.y) > 0.5 else 'x')
    for attr in ('visible_shadow', 'visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter'): setattr(v, attr, False)
    return ob


def windows(M, col):
    for k, c in enumerate(WINDOWS): shutters(f'shutter{k}', (c, BACK - 0.0), (0, -1), M, col)
    shutters('shutter_l', (LEFT, LWIN), (1, 0), M, col)
    # a long cast-iron column radiator under the pair, painted dark
    L = WINDOWS[1] - WINDOWS[0] + WW - 0.1; cx = (WINDOWS[0] + WINDOWS[1]) / 2; cols = 28
    for k in range(cols):
        x = cx - L / 2 + (k + 0.5) * L / cols
        box(f'radiator_col{k}', (0.04, 0.17, 0.42), (x, BACK - 0.14, 0.09 + 0.21), M['iron'], bev=0.012, seg=2, collection=col, lm='furn')
    box('radiator_top', (L, 0.17, 0.015), (cx, BACK - 0.14, 0.52), M['iron'], bev=0.004, collection=col, lm='furn')
    for s in (-1, 1): box(f'radiator_foot{s}', (0.05, 0.17, 0.09), (cx + s * (L / 2 - 0.06), BACK - 0.14, 0.045), M['iron'], bev=0.006, collection=col, lm='furn')


# ---------------------------------------------------------------- the fireplace and the back wall's things
def fireplace(M, col):
    """A dark marble surround in a carved mahogany mantelpiece, the firebox swept for summer, the hearth; on the
    shelf the family in frames, the clock, two urns; the landscape in its gilt frame above. Returns the shelf's z."""
    x = FIRE; y = BACK; w, hm, dp = 1.6, 1.3, 0.24
    box('fire_hearth', (w + 0.2, 0.45, 0.04), (x, y - 0.225, 0.02), M['marble'], bev=0.006, collection=col, lm='furn')
    box('fire_box', (0.72, 0.3, 0.78), (x, y - 0.12, 0.43), M['firebox'], bev=0.004, collection=col, lm='furn')
    for s in (-1, 1):
        box(f'fire_marble{s}', (0.2, 0.05, 0.86), (x + s * 0.46, y - 0.26, 0.47), M['marble'], bev=0.004, collection=col, lm='furn')
        box(f'fire_leg{s}', (0.16, dp, hm - 0.08), (x + s * (w / 2 - 0.08), y - dp / 2, (hm - 0.08) / 2), M['mahogany'], bev=0.008, collection=col, lm='furn')
        box(f'fire_console{s}', (0.12, dp + 0.06, 0.18), (x + s * (w / 2 - 0.08), y - dp / 2 - 0.03, hm - 0.2), M['mahogany'], bev=0.02, seg=3, collection=col, lm='furn')
    box('fire_marble_top', (0.92, 0.05, 0.14), (x, y - 0.26, 0.93), M['marble'], bev=0.004, collection=col, lm='furn')
    box('fire_frieze', (w - 0.3, 0.06, 0.22), (x, y - dp + 0.03, hm - 0.17), M['mahogany'], bev=0.01, collection=col, lm='furn')
    box('fire_shelf', (w + 0.12, dp + 0.1, 0.05), (x, y - (dp + 0.1) / 2, hm - 0.025), M['mahogany'], bev=0.012, collection=col, lm='furn')
    # the overmantel: a panel and the landscape in gilt
    root, ms = cine.import_gltf(PH('fancy_picture_frame_01'), loc=(x, y - 0.03, 1.95), rot=(0, 0, math.pi), scale=1.15, collection=col, lm='furn')
    _fit(ms, (x, y - 0.03, 1.98), 1.05, 'x')
    # on the shelf: the clock in the middle, framed photographs, a pair of urns at the ends
    top = hm
    r, cm = cine.import_gltf(PH('mantel_clock_01'), loc=(x, y - 0.12, top), rot=(0, 0, math.pi), scale=1.0, collection=col, lm='furn')
    _fit(cm, (x, y - 0.12, top), 0.3, 'z', ground=True, ratio=0.25)
    for k, (dx, f) in enumerate(((-0.42, 'standing_picture_frame_01'), (0.36, 'standing_picture_frame_02'), (0.55, 'standing_picture_frame_01'))):
        r, fm = cine.import_gltf(PH(f), loc=(x + dx, y - 0.1, top), rot=(0, 0, math.pi + math.radians(-8 + 16 * (k % 2))), scale=1.0, collection=col, lm='furn')
        _fit(fm, (x + dx, y - 0.1, top), 0.2 - 0.03 * (k == 2), 'x', ground=True)
        _photo(fm, M[f'photo{k}'])
    for s in (-1, 1):
        r, vm = cine.import_gltf(PH('antique_ceramic_vase_01'), loc=(x + s * 0.74, y - 0.1, top), scale=1.0, collection=col, lm='furn')
        _fit(vm, (x + s * 0.74, y - 0.1, top), 0.32, 'z', ground=True, ratio=0.4)
    return top


def _fit(meshes, at, size, axis='x', ground=False, ratio=None):
    """Scale an imported model (its meshes together) to `size` metres along an axis and centre it at `at` (its base on
    at's z when `ground`): Poly Haven's models come at their own sizes and pivots. Its roughness and metalness maps
    are dropped (the exporter cannot write the channels it splits out of their packed maps, and a texture left without
    its image breaks the whole file on the web); `ratio` thins a dense model's mesh (a small bronze at 1:6 needs no
    twenty thousand vertices)."""
    _plain(meshes)
    if ratio:
        for o in meshes:
            md = o.modifiers.new('thin', 'DECIMATE'); md.ratio = ratio; md.use_collapse_triangulate = True
    bpy.context.view_layer.update()
    lo = Vector((1e9,) * 3); hi = -lo
    for o in meshes:
        for cn in o.bound_box:
            p = o.matrix_world @ Vector(cn); lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
    k = size / max((hi - lo)['xyz'.index(axis)], 1e-6); c = (lo + hi) / 2
    if ground: c.z = lo.z
    T_ = Matrix.Translation(Vector(at)) @ Matrix.Diagonal((k, k, k, 1)) @ Matrix.Translation(-c)
    for o in meshes:
        if o.parent is None or o.parent.type != 'MESH':
            mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = T_ @ mw
    bpy.context.view_layer.update()
    return k


def _plain(meshes):
    """Unplug every image from the materials' roughness and metallic inputs (constant values instead)."""
    for o in meshes:
        for sl in o.material_slots:
            m = sl.material
            if not m or not m.node_tree: continue
            p = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if p is None: continue
            for k, v in (('Roughness', 0.55), ('Metallic', 0.0)):
                for l in list(p.inputs[k].links): m.node_tree.links.remove(l)
                p.inputs[k].default_value = v


def _photo(meshes, mat):
    """Put one of the family's photographs in a standing frame (the frame's own picture material replaced)."""
    for o in meshes:
        for sl in o.material_slots:
            if sl.material and any(k in sl.material.name.lower() for k in ('picture', 'photo', 'image', 'canvas', 'print')): sl.material = mat


def back_things(M, col):
    """Right of the fireplace: the glazed cabinet against the damask, the lamp on its pedestal table, the crest-framed
    print above; the ivy in its famille-rose cachepot on a stand by the window; the palm in its jardiniere in the
    corner; the black tufted chair. Left of the windows: a tall glazed curio cabinet. Returns the lamp's bulb."""
    r, cm = cine.import_gltf(PH('vintage_cabinet_01'), loc=(1.05, BACK - 0.25, 0.0), rot=(0, 0, 0), scale=1.0, collection=col, lm='furn')
    _fit(cm, (1.08, BACK - 0.24, 0.0), 1.05, 'x', ground=True, ratio=0.4)
    # the crest-framed print above it: a carved pediment over a red print
    p = Vector((1.08, BACK, 2.48))
    o = uv_rect(box('crest_print', (0.5, 0.012, 0.16), p + Vector((0, -0.03, 0)), M['crest'], bev=0.002, collection=col, lm='furn'))
    box('crest_frame', (0.6, 0.03, 0.24), p + Vector((0, -0.012, 0)), M['gilt'], bev=0.006, collection=col, lm='furn')
    box('crest_pediment', (0.36, 0.035, 0.08), p + Vector((0, -0.016, 0.16)), M['gilt'], bev=0.02, seg=3, collection=col, lm='furn')
    # the lamp on a round pedestal table before the cabinet's left side
    t = Vector((0.75, 2.85, 0.0))
    cyl('lamp_table_top', 0.26, 0.03, t + Vector((0, 0, 0.7)), M['mahogany'], seg=40, bev=0.006, collection=col, lm='furn')
    lathe('lamp_table_pedestal', [(0.0, 0.0), (0.24, 0.0), (0.24, 0.03), (0.06, 0.07), (0.045, 0.3), (0.07, 0.42), (0.04, 0.6), (0.08, 0.685), (0.0, 0.685)], M['mahogany'], loc=t, seg=32, collection=col, lm='furn')
    bulb = column_lamp('lamp_cream', t + Vector((0.0, 0.0, 0.715)), M, col, shade=M['shade'], shade_r=0.2)
    # the ivy on its stand between the window and the fireplace
    st = Vector((-1.42, BACK - 0.26, 0.0))
    lathe('ivy_stand', [(0.0, 0.0), (0.17, 0.0), (0.17, 0.03), (0.05, 0.08), (0.035, 0.7), (0.06, 0.82), (0.16, 0.86), (0.16, 0.9), (0.0, 0.9)], M['mahogany'], loc=st, seg=24, collection=col, lm='furn')
    lathe('ivy_pot', [(0.0, 0.0), (0.09, 0.0), (0.12, 0.04), (0.14, 0.15), (0.15, 0.2), (0.13, 0.21), (0.0, 0.21)], M['porcelain'], loc=st + Vector((0, 0, 0.9)), seg=32, collection=col, lm='furn')
    r, pm = cine.import_gltf(PH('potted_plant_02'), loc=st + Vector((0, 0, 1.0)), rot=(0, 0, 0.8), scale=1.0, collection=col, lm='furn')
    _fit(pm, st + Vector((0, 0, 1.02)), 0.55, 'z', ground=True, ratio=0.5)
    for o in list(pm):
        if any(sl.material and sl.material.name.lower().endswith('_pot') for sl in o.material_slots): bpy.data.objects.remove(o, do_unlink=True)
    # the palm in its jardiniere, in the corner by the partition
    jp = Vector((2.05, BACK - 0.42, 0.0))
    r, jm = cine.import_gltf(PH('antique_ceramic_vase_01'), loc=jp, scale=1.0, collection=col, lm='furn')
    _fit(jm, jp, 0.5, 'z', ground=True, ratio=0.4)
    r, palm = cine.import_gltf(PH('pachira_aquatica_01'), loc=jp + Vector((0, 0, 0.4)), scale=1.0, collection=col, lm='furn')
    _fit(palm, jp + Vector((0, 0, 0.42)), 1.3, 'z', ground=True, ratio=0.3)
    # a tall glazed curio cabinet left of the windows
    glazed_case('curio', (-4.2, BACK - 0.22), (0.72, 0.38, 2.15), (0, -1), M, col)
    tufted_chair('chesterfield', Vector((1.55, 1.95, 0)), Vector((-0.55, -1, 0)), M, col)
    return bulb


def glazed_case(name, c, size, n, M, col, rows=5):
    """A tall mahogany bookcase with glazed doors (the glass left out, its muntins kept), a cornice, books on most
    shelves and a few objects."""
    w, d, h = size; n = Vector((n[0], n[1], 0)).normalized(); parts = []; rnd = random.Random(hash(name) % 997)
    add = lambda o: (parts.append(o), o)[1]
    add(box(f'{name}_back', (w, 0.02, h), (0, d / 2 - 0.01, h / 2), M['mahogany'], bev=0, collection=col, lm='furn'))
    for s in (-1, 1): add(box(f'{name}_side{s}', (0.03, d, h), (s * (w / 2 - 0.015), 0, h / 2), M['mahogany'], bev=0.003, collection=col, lm='furn'))
    add(box(f'{name}_base', (w + 0.03, d + 0.02, 0.14), (0, -0.01, 0.07), M['mahogany'], bev=0.006, collection=col, lm='furn'))
    add(box(f'{name}_cornice', (w + 0.08, d + 0.06, 0.08), (0, -0.03, h + 0.04), M['mahogany'], bev=0.012, collection=col, lm='furn'))
    zs = [0.14 + k * (h - 0.2) / rows for k in range(rows + 1)]
    for k, z in enumerate(zs): add(box(f'{name}_shelf{k}', (w - 0.06, d - 0.03, 0.02), (0, 0.0, z), M['mahogany'], bev=0.002, collection=col, lm='furn'))
    for k, (a, b) in enumerate(zip(zs, zs[1:])):
        if rnd.random() < 0.8:
            spine_row(f'{name}_row{k}', w - 0.1, a + 0.01, min(b - a - 0.03, 0.3), d - 0.06, {'spines': M['books']}, col, parts, rnd)
            parts[-1].location = (0, 0.02, 0)
        else:
            add(lathe(f'{name}_urn{k}', [(0.0, 0.0), (0.04, 0.0), (0.07, 0.08), (0.06, 0.16), (0.03, 0.2), (0.04, 0.22), (0.0, 0.22)], M['ivory'], loc=(0.0, 0.0, a + 0.01), seg=20, collection=col, lm='furn'))
    for s in (-1, 1):                                                           # the doors' frames and muntins (no glass)
        x0 = s * w / 4; wd = w / 2 - 0.02; hd = h - 0.24; zc = h / 2 + 0.05
        for sx in (-1, 1): add(box(f'{name}_dstile{s}{sx}', (0.035, 0.022, hd), (x0 + sx * (wd / 2 - 0.0175), -d / 2 - 0.011, zc), M['mahogany'], bev=0.003, collection=col, lm='furn'))
        for sz in (-1, 1): add(box(f'{name}_drail{s}{sz}', (wd, 0.022, 0.045), (x0, -d / 2 - 0.011, zc + sz * (hd / 2 - 0.0225)), M['mahogany'], bev=0.003, collection=col, lm='furn'))
        for j in range(1, 4): add(box(f'{name}_bar{s}{j}', (wd - 0.06, 0.012, 0.012), (x0, -d / 2 - 0.011, zc - hd / 2 + j * hd / 4), M['mahogany'], bev=0.002, collection=col, lm='furn'))
        add(cyl(f'{name}_knob{s}', 0.009, 0.02, (x0 - s * (wd / 2 - 0.05), -d / 2 - 0.03, zc), M['brass'], rot=(math.pi / 2, 0, 0), seg=10, collection=col, lm='furn'))
    F = Matrix.Translation((c[0], c[1], 0)) @ Matrix.Rotation(math.atan2(-n.x, n.y) + math.pi, 4, 'Z')
    for o in parts: place(o, F)


def column_lamp(name, p, M, col, shade=None, shade_r=0.18):
    """A turned brass lamp with a pleated drum shade; returns its bulb."""
    p = Vector(p)
    lathe(f'{name}_body', [(0.0, 0.0), (0.08, 0.0), (0.08, 0.02), (0.05, 0.05), (0.035, 0.1), (0.06, 0.18), (0.07, 0.24), (0.04, 0.32), (0.015, 0.36), (0.012, 0.46), (0.0, 0.46)], M['brass'], loc=p, seg=24, collection=col, lm='furn')
    bm = bmesh.new(); seg = 48; rings = []
    for z, r in ((0.0, shade_r), (0.26, shade_r * 0.7)):
        rings.append([bm.verts.new((r * (1 + 0.03 * (k % 2)) * math.cos(2 * math.pi * k / seg), r * (1 + 0.03 * (k % 2)) * math.sin(2 * math.pi * k / seg), z)) for k in range(seg)])
    for k in range(seg): bm.faces.new((rings[0][k], rings[0][(k + 1) % seg], rings[1][(k + 1) % seg], rings[1][k]))
    sh = cine._mesh_obj(f'{name}_shade', bm, shade or M['shade'], col, smooth=False); sh.location = p + Vector((0, 0, 0.36)); sh['lm'] = 'furn'
    sh.modifiers.new('solid', 'SOLIDIFY').thickness = 0.004
    return p + Vector((0, 0, 0.45))


# ---------------------------------------------------------------- the desk and the chairs
def _frame(p, f):
    """Built facing -y about the origin, turned to face f at p."""
    return Matrix.Translation((p[0], p[1], 0)) @ Matrix.Rotation(math.atan2(f[1], f[0]) + math.pi / 2, 4, 'Z')


def desk(M, col):
    """The Don's desk: a big carved mahogany pedestal desk on scrolled feet, its front panelled and carved, a tooled red
    leather top; on it the walnut document box, the black telephone, papers and a pen stand, a small bronze horse, a
    glass ashtray."""
    parts = []; add = lambda o: (parts.append(o), o)[1]
    zt, Wd, Dp = DESK_H, DESK_W, DESK_D
    add(rounded_slab('desk_top', Wd, Dp, 0.045, 0.02, (0, 0, zt - 0.0225), M['mahogany'], edge_bev=0.012, collection=col, lm='furn'))
    add(box('desk_leather', (Wd - 0.18, Dp - 0.18, 0.004), (0, 0, zt + 0.001), M['brown_leather'], bev=0, collection=col, lm='furn'))
    add(box('desk_apron', (Wd - 0.06, Dp - 0.06, 0.09), (0, 0, zt - 0.09), M['mahogany'], bev=0.01, collection=col, lm='furn'))
    for s in (-1, 1):
        x = s * (Wd / 2 - 0.28)
        add(box(f'desk_ped{s}', (0.52, Dp - 0.1, zt - 0.2), (x, 0.0, (zt - 0.2) / 2 + 0.07), M['mahogany'], bev=0.008, collection=col, lm='furn'))
        add(box(f'desk_plinth{s}', (0.58, Dp - 0.04, 0.07), (x, 0.0, 0.07), M['mahogany'], bev=0.012, collection=col, lm='furn'))
        for sx in (-1, 1):
            for sy in (-1, 1):                                                       # scrolled bun feet
                add(lathe(f'desk_foot{s}{sx}{sy}', [(0.0, 0.0), (0.035, 0.0), (0.05, 0.02), (0.045, 0.04), (0.0, 0.04)], M['mahogany'], loc=(x + sx * 0.25, sy * (Dp / 2 - 0.06), 0.0), seg=16, collection=col, lm='furn'))
        for k, (z0, z1) in enumerate(((0.12, 0.38), (0.42, zt - 0.16))):            # raised and carved panels on the front
            add(box(f'desk_panel{s}{k}', (0.4, 0.024, z1 - z0), (x, -(Dp - 0.1) / 2 - 0.008, (z0 + z1) / 2), M['mahogany'], bev=0.018, seg=3, collection=col, lm='furn'))
            add(box(f'desk_carve{s}{k}', (0.24, 0.012, (z1 - z0) * 0.5), (x, -(Dp - 0.1) / 2 - 0.022, (z0 + z1) / 2), M['mahogany'], bev=0.012, seg=3, collection=col, lm='furn'))
        for sy in (-1, 1):                                                           # carved corner columns
            add(lathe(f'desk_column{s}{sy}', [(0.0, 0.0), (0.035, 0.0), (0.03, 0.06), (0.024, 0.1), (0.034, 0.2), (0.026, 0.32), (0.034, 0.46), (0.03, 0.56), (0.036, 0.6), (0.0, 0.6)], M['mahogany'],
                        loc=(x + s * 0.27, sy * (Dp / 2 - 0.05), 0.08), seg=16, collection=col, lm='furn'))
    add(box('desk_modesty', (Wd - 1.16, 0.03, zt - 0.3), (0, -(Dp - 0.1) / 2 + 0.06, (zt - 0.3) / 2 + 0.2), M['mahogany'], bev=0.006, collection=col, lm='furn'))
    add(box('desk_drawer', (Wd - 1.2, 0.03, 0.1), (0, -(Dp - 0.06) / 2 - 0.006, zt - 0.1), M['mahogany'], bev=0.012, seg=3, collection=col, lm='furn'))
    add(box('desk_scroll', (0.5, 0.02, 0.06), (0, -(Dp - 0.06) / 2 - 0.022, zt - 0.1), M['mahogany'], bev=0.02, seg=3, collection=col, lm='furn'))
    # the document box at the front, the telephone at the Don's right, papers, the pen stand, the horse, the ashtray
    add(box('desk_box', (0.36, 0.26, 0.11), (-0.12, -0.24, zt + 0.055), M['mahogany'], bev=0.006, collection=col, lm='furn'))
    add(box('desk_box_lid', (0.37, 0.27, 0.025), (-0.12, -0.24, zt + 0.115), M['mahogany'], bev=0.008, collection=col, lm='furn'))
    ph = Vector((-0.62, -0.22, zt))
    add(box('phone_base', (0.17, 0.2, 0.05), ph + Vector((0, 0, 0.025)), M['bakelite'], bev=0.018, collection=col, lm='furn'))
    add(cyl('phone_dial', 0.05, 0.012, ph + Vector((0, -0.07, 0.055)), M['bakelite'], rot=(math.radians(-60), 0, 0), seg=20, collection=col, lm='furn'))
    hs = add(tube('phone_handset', [ph + Vector((-0.09, 0.03, 0.07)), ph + Vector((-0.05, 0.03, 0.085)), ph + Vector((0.05, 0.03, 0.085)), ph + Vector((0.09, 0.03, 0.07))], 0.016, M['bakelite'], col, seg=10, lm='furn'))
    for s in (-1, 1): add(box(f'phone_cup{s}', (0.04, 0.06, 0.04), ph + Vector((s * 0.09, 0.03, 0.06)), M['bakelite'], bev=0.012, collection=col, lm='furn'))
    for k in range(3): add(box(f'desk_paper{k}', (0.215, 0.28, 0.003), (0.22 + 0.03 * k, 0.02 + 0.01 * k, zt + 0.006 + 0.003 * k), M['paper'], rot=(0, 0, 0.14 * k - 0.2), bev=0, collection=col, lm='furn'))
    add(box('pen_base', (0.18, 0.08, 0.025), (0.32, 0.27, zt + 0.0125), M['marble'], bev=0.006, collection=col, lm='furn'))
    for s in (-1, 1): add(cyl(f'pen{s}', 0.004, 0.16, (0.32 + s * 0.05, 0.25, zt + 0.09), M['bakelite'], rot=(math.radians(20), 0, 0), seg=8, collection=col, lm='furn'))
    add(lathe('ashtray', [(0.0, 0.0), (0.07, 0.0), (0.075, 0.03), (0.06, 0.03), (0.055, 0.012), (0.0, 0.012)], M['glass'], loc=(0.66, -0.18, zt), seg=24, collection=col, lm='furn'))
    for o in parts: place(o, _frame(DESK, (0, -1)))
    r, hm = cine.import_gltf(PH('horse_statue_01'), loc=(0, 0, 0), rot=(0, 0, 2.6), scale=1.0, collection=col, lm='furn')
    hp = _frame(DESK, (0, -1)) @ Vector((0.68, 0.22, zt))
    _fit(hm, hp, 0.22, 'z', ground=True, ratio=0.15)
    for o in hm:
        for sl in o.material_slots: sl.material = M['bronze']


def vito_chair(M, col):
    """The Don's chair: a high-backed tufted leather armchair in olive-gold, brass nails round its edges, carved
    mahogany arms and legs."""
    p, f = chair_at('vito'); parts = []; add = lambda o: (parts.append(o), o)[1]
    st = SEAT['vito']
    add(rounded_slab('vchair_seat', 0.62, 0.58, 0.13, 0.08, (0, -0.02, st - 0.065), M['olive'], edge_bev=0.035, collection=col, lm='furn'))
    add(box('vchair_rail', (0.66, 0.6, 0.12), (0, 0.0, st - 0.18), M['mahogany'], bev=0.01, collection=col, lm='furn'))
    bk = add(rounded_slab('vchair_back', 0.66, 0.16, 0.9, 0.14, (0, 0, 0), M['olive'], edge_bev=0.05, collection=col, lm='furn'))
    bk.rotation_euler.x = math.radians(-9); bk.location = (0, 0.3, st + 0.5)
    for k in range(4):                                                         # the tufts, in a diamond lattice
        for j in range(4 - k % 2):
            x = -0.21 + 0.14 * j + (0.07 if k % 2 else 0)
            b = add(cyl(f'vchair_tuft{k}{j}', 0.011, 0.012, (x, 0.215 - 0.03 * k * 0.15, st + 0.28 + 0.18 * k), M['olive'], rot=(math.pi / 2 - math.radians(9), 0, 0), seg=10, collection=col, lm='furn'))
    for k in range(17):                                                        # brass nails round the back's top and sides
        a = math.pi * k / 16
        add(cyl(f'vchair_nail{k}', 0.006, 0.006, (-0.31 * math.cos(a), 0.215, st + 0.9 + 0.06 * math.sin(a) - 0.06), M['brass'], rot=(math.pi / 2, 0, 0), seg=8, collection=col, lm='furn'))
    for s in (-1, 1):
        add(rounded_slab(f'vchair_arm{s}', 0.09, 0.56, 0.06, 0.03, (s * 0.35, -0.04, st + 0.24), M['mahogany'], edge_bev=0.012, collection=col, lm='furn'))
        add(rounded_slab(f'vchair_armpad{s}', 0.07, 0.4, 0.03, 0.02, (s * 0.35, -0.02, st + 0.28), M['olive'], edge_bev=0.012, collection=col, lm='furn'))
        add(lathe(f'vchair_post{s}', [(0.0, 0.0), (0.025, 0.0), (0.03, 0.06), (0.02, 0.12), (0.028, 0.2), (0.0, 0.2)], M['mahogany'], loc=(s * 0.35, -0.28, st), seg=12, collection=col, lm='furn'))
        for sy in (-1, 1):
            add(lathe(f'vchair_leg{s}{sy}', [(0.0, 0.0), (0.03, 0.0), (0.035, 0.05), (0.025, 0.12), (0.032, 0.2), (0.028, st - 0.24), (0.0, st - 0.24)], M['mahogany'], loc=(s * 0.29, sy * 0.25, 0.0), seg=12, collection=col, lm='furn'))
    for o in parts: place(o, _frame(p, f))


def side_chair(name, p, f, M, col):
    """A hard dark wooden chair (the visitor's: no padding), turned legs and stretchers, a square back with a carved top
    rail and three splats, a brown leather slip seat."""
    parts = []; add = lambda o: (parts.append(o), o)[1]; st = 0.47
    add(box(f'{name}_seat', (0.46, 0.44, 0.04), (0, 0, st - 0.02), M['mahogany'], bev=0.008, collection=col, lm='furn'))
    add(box(f'{name}_slip', (0.4, 0.38, 0.015), (0, -0.005, st + 0.007), M['brown_leather'], bev=0.006, collection=col, lm='furn'))
    for sx in (-1, 1):
        for sy in (-1, 1):
            h = st - 0.04 if sy < 0 else 0.98
            add(lathe(f'{name}_leg{sx}{sy}', [(0.0, 0.0), (0.02, 0.0), (0.024, 0.06), (0.016, 0.14), (0.022, 0.24), (0.018, h - 0.02), (0.0, h)], M['mahogany'], loc=(sx * 0.2, sy * 0.19, 0.0), seg=12, collection=col, lm='furn'))
        add(box(f'{name}_stretch{sx}', (0.022, 0.36, 0.025), (sx * 0.2, 0.0, 0.14), M['mahogany'], bev=0.004, collection=col, lm='furn'))
    add(box(f'{name}_stretch_f', (0.38, 0.022, 0.025), (0, -0.19, 0.2), M['mahogany'], bev=0.004, collection=col, lm='furn'))
    add(box(f'{name}_toprail', (0.46, 0.035, 0.1), (0, 0.19, 0.93), M['mahogany'], bev=0.014, seg=3, collection=col, lm='furn'))
    add(box(f'{name}_backrail', (0.38, 0.03, 0.05), (0, 0.19, st + 0.1), M['mahogany'], bev=0.006, collection=col, lm='furn'))
    for k in (-1, 0, 1): add(box(f'{name}_splat{k}', (0.045, 0.018, 0.3), (k * 0.1, 0.19, st + 0.3), M['mahogany'], bev=0.006, collection=col, lm='furn'))
    for o in parts: place(o, _frame(p, f))


def club_chair(name, p, f, M, col, st=0.44):
    """Hagen's chair: a deep black leather club chair, rolled arms, a loose cushion, short turned feet."""
    parts = []; add = lambda o: (parts.append(o), o)[1]; L = M['black_leather']
    add(rounded_slab(f'{name}_base', 0.86, 0.84, 0.3, 0.08, (0, 0, 0.24), L, edge_bev=0.03, collection=col, lm='furn'))
    add(rounded_slab(f'{name}_cushion', 0.58, 0.64, 0.12, 0.08, (0, -0.06, st - 0.06), L, edge_bev=0.04, collection=col, lm='furn'))
    bk = add(rounded_slab(f'{name}_back', 0.84, 0.22, 0.48, 0.1, (0, 0.31, st + 0.25), L, edge_bev=0.05, collection=col, lm='furn')); bk.rotation_euler.x = math.radians(-10)
    for s in (-1, 1):
        add(rounded_slab(f'{name}_arm{s}', 0.16, 0.82, 0.32, 0.06, (s * 0.35, 0.0, st + 0.06), L, edge_bev=0.03, collection=col, lm='furn'))
        add(cyl(f'{name}_roll{s}', 0.085, 0.78, (s * 0.36, -0.02, st + 0.22), L, rot=(math.pi / 2, 0, 0), seg=24, collection=col, lm='furn'))
        for sy in (-1, 1): add(lathe(f'{name}_foot{s}{sy}', [(0.0, 0.0), (0.025, 0.0), (0.03, 0.05), (0.025, 0.09), (0.0, 0.09)], M['mahogany'], loc=(s * 0.36, sy * 0.34, 0.0), seg=12, collection=col, lm='furn'))
    for o in parts: place(o, _frame(p, f))


def tufted_chair(name, p, f, M, col):
    """The black tufted leather armchair on carved cabriole legs: a deep buttoned back with scrolled arms."""
    parts = []; add = lambda o: (parts.append(o), o)[1]; L = M['black_leather']; st = 0.46
    add(rounded_slab(f'{name}_seat', 0.7, 0.62, 0.14, 0.07, (0, -0.02, st - 0.07), L, edge_bev=0.035, collection=col, lm='furn'))
    add(box(f'{name}_rail', (0.74, 0.66, 0.1), (0, 0.0, st - 0.18), M['mahogany'], bev=0.012, collection=col, lm='furn'))
    bk = add(rounded_slab(f'{name}_back', 0.74, 0.18, 0.66, 0.16, (0, 0.3, st + 0.36), L, edge_bev=0.06, collection=col, lm='furn')); bk.rotation_euler.x = math.radians(-8)
    for k in range(3):
        for j in range(4 - k % 2):
            add(cyl(f'{name}_tuft{k}{j}', 0.01, 0.012, (-0.22 + 0.147 * j + (0.073 if k % 2 else 0), 0.205, st + 0.15 + 0.17 * k), L, rot=(math.pi / 2 - math.radians(8), 0, 0), seg=8, collection=col, lm='furn'))
    for s in (-1, 1):
        add(rounded_slab(f'{name}_arm{s}', 0.14, 0.62, 0.26, 0.05, (s * 0.37, -0.02, st + 0.08), L, edge_bev=0.03, collection=col, lm='furn'))
        add(cyl(f'{name}_scroll{s}', 0.07, 0.6, (s * 0.39, -0.03, st + 0.22), L, rot=(math.pi / 2, 0, 0), seg=20, collection=col, lm='furn'))
        for sy in (-1, 1):
            add(tube(f'{name}_leg{s}{sy}', [(s * 0.32, sy * 0.27, st - 0.22), (s * 0.34, sy * 0.29, 0.2), (s * 0.31, sy * 0.3, 0.07), (s * 0.34, sy * 0.33, 0.0)], 0.026, M['mahogany'], col, seg=10, lm='furn'))
    for o in parts: place(o, _frame(p, f))


def chairs(M, col):
    vito_chair(M, col)
    for k, (x, y) in enumerate(SIDE_CHAIRS):
        side_chair(f'side_chair{k}', (x, y), (DESK.x - x, DESK.y - y), M, col)
    p, f = chair_at('hagen')
    club_chair('club', p, f, M, col, SEAT['hagen'])


# ---------------------------------------------------------------- the left side: Hagen's corner, Sonny's window
def left_things(M, col):
    """Hagen's little table with the red-shaded lamp and the telephone; the carved console under the double sconce
    with crystal decanters and glasses; the tall bookcase behind the arch. Returns (sconce bulbs, the red lamp's bulb)."""
    tp = Vector((LEFT + 0.32, -2.95, 0.0))
    box('htable_top', (0.5, 0.5, 0.03), tp + Vector((0, 0, 0.6)), M['mahogany'], bev=0.006, collection=col, lm='furn')
    box('htable_apron', (0.44, 0.44, 0.08), tp + Vector((0, 0, 0.55)), M['mahogany'], bev=0.004, collection=col, lm='furn')
    for sx in (-1, 1):
        for sy in (-1, 1): lathe(f'htable_leg{sx}{sy}', [(0.0, 0.0), (0.02, 0.0), (0.026, 0.1), (0.018, 0.3), (0.024, 0.5), (0.0, 0.51)], M['mahogany'], loc=tp + Vector((sx * 0.2, sy * 0.2, 0.0)), seg=12, collection=col, lm='furn')
    red = column_lamp('lamp_red', tp + Vector((0.05, 0.08, 0.615)), M, col, shade=M['red_shade'], shade_r=0.15)
    ph = tp + Vector((-0.06, -0.12, 0.615))
    box('hphone_base', (0.17, 0.2, 0.05), ph + Vector((0, 0, 0.025)), M['bakelite'], bev=0.018, collection=col, lm='furn')
    tube('hphone_handset', [ph + Vector((-0.09, 0.03, 0.07)), ph + Vector((-0.05, 0.03, 0.085)), ph + Vector((0.05, 0.03, 0.085)), ph + Vector((0.09, 0.03, 0.07))], 0.016, M['bakelite'], col, seg=10, lm='furn')
    # the console and the decanters
    r, cm = cine.import_gltf(PH('ClassicConsole_01'), loc=(0, 0, 0), rot=(0, 0, math.pi / 2), scale=1.0, collection=col, lm='furn')
    s = _fit(cm, (LEFT + 0.22, -2.05, 0.0), 1.05, 'y', ground=True, ratio=0.5)
    bpy.context.view_layer.update()
    top = max((o.matrix_world @ Vector(cn)).z for o in cm for cn in o.bound_box)
    for k, (dy, h) in enumerate(((-0.25, 0.3), (0.0, 0.26), (0.24, 0.32))):
        lathe(f'decanter{k}', [(0.0, 0.0), (0.06, 0.0), (0.075, 0.06), (0.07, 0.14), (0.03, 0.2), (0.02, h - 0.06), (0.026, h - 0.05), (0.0, h - 0.05)], M['glass'], loc=(LEFT + 0.22, -2.05 + dy, top), seg=20, collection=col, role='glass')
        lathe(f'stopper{k}', [(0.0, 0.0), (0.012, 0.0), (0.03, 0.03), (0.0, 0.06)], M['glass'], loc=(LEFT + 0.22, -2.05 + dy, top + h - 0.05), seg=12, collection=col, role='glass')
        lathe(f'decanter_wine{k}', [(0.0, 0.0), (0.056, 0.0), (0.07, 0.06), (0.066, 0.1), (0.0, 0.1)], M['wine'], loc=(LEFT + 0.22, -2.05 + dy, top + 0.004), seg=20, collection=col, lm='furn')
    for k in range(4):
        lathe(f'console_glass{k}', [(0.0, 0.0), (0.03, 0.0), (0.03, 0.004), (0.004, 0.01), (0.004, 0.07), (0.035, 0.1), (0.04, 0.15), (0.0, 0.15)], M['glass'], loc=(LEFT + 0.3, -2.42 + 0.09 * k, top), seg=16, collection=col, role='glass')
    # the double sconce over it: a brass plate, two arms, small pleated shades
    sc = Vector((LEFT + 0.01, -2.05, 1.95)); bulbs = []
    box('sconce_plate', (0.02, 0.12, 0.24), sc + Vector((0.01, 0, 0)), M['brass'], bev=0.004, collection=col, lm='furn')
    for s in (-1, 1):
        a = sc + Vector((0.16, s * 0.13, 0.05))
        tube(f'sconce_arm{s}', [sc + Vector((0.02, 0, -0.04)), sc + Vector((0.1, s * 0.05, -0.06)), a + Vector((0, 0, -0.04)), a], 0.008, M['brass'], col, seg=8, lm='furn')
        cyl(f'sconce_cup{s}', 0.025, 0.03, a + Vector((0, 0, 0.015)), M['brass'], seg=12, collection=col, lm='furn')
        sh = cyl(f'sconce_shade{s}', 0.07, 0.11, a + Vector((0, 0, 0.11)), M['shade'], r2=0.045, seg=24, collection=col, lm='furn')
        bulbs.append(a + Vector((0, 0, 0.08)))
    # the tall bookcase behind the arch, against the left wall
    glazed_case('left_case', (LEFT + 0.21, 1.75), (1.5, 0.4, 2.2), (1, 0), M, col, rows=6)
    return bulbs, red


def rug(M, col):
    """The vase carpet, its long side across the room, from the desk to Hagen's chair."""
    r = box('rug', (3.8, 2.4, 0.012), (-2.25, -0.6, 0.006), M['rug'], bev=0.003, collection=col, lm='arch')
    uv_rect(r, 'z')
    for d in r.data.uv_layers['UVMap'].data: d.uv = (0.006 + 0.988 * d.uv[0], 0.006 + 0.988 * d.uv[1])   # the photograph's last rows are its ground
    return r


# ---------------------------------------------------------------- the hall
def hall(M, col):
    """The front hall: the glazed front door with its sidelights (sheers lit by the garden's sun), the hall table with a
    lamp and a mirror, a red runner on the boards. Returns the hall lamp's bulb."""
    fx, fw, fh, sw = FRONT_DOOR; y = BACK
    # the door: a mahogany leaf with three tall glazed panes over a panelled bottom; sidelights the same
    for k, (c, w) in enumerate(((fx, fw), (fx - fw / 2 - sw / 2 - 0.025, sw), (fx + fw / 2 + sw / 2 + 0.025, sw))):
        box(f'front_frame{k}', (w, 0.06, fh), (c, y + 0.04, fh / 2), M['mahogany'], bev=0.004, collection=col, lm='furn')
    # hollow the leaf's glazing as bright sheers (the frame boxes above carry the wood; the panes sit just in front)
    for k, (c, w) in enumerate(((fx, fw), (fx - fw / 2 - sw / 2 - 0.025, sw), (fx + fw / 2 + sw / 2 + 0.025, sw))):
        n = 3 if k == 0 else 1; pw = (w - 0.1 - 0.05 * (n - 1)) / n
        for j in range(n):
            x0 = c - w / 2 + 0.05 + j * (pw + 0.05)
            box(f'front_pane{k}{j}', (pw, 0.01, fh - 1.05), (x0 + pw / 2, y + 0.005, 0.95 + (fh - 1.05) / 2), M['sheer'], bev=0, collection=col)
        box(f'front_panel{k}', (w - 0.12, 0.012, 0.6), (c, y + 0.004, 0.45), M['mahogany'], bev=0.012, seg=3, collection=col, lm='furn')
    cyl('front_knob', 0.022, 0.03, (fx + fw / 2 - 0.08, y - 0.005, 1.0), M['brass'], rot=(math.pi / 2, 0, 0), seg=14, collection=col, lm='furn')
    # the hall table and the mirror on the partition, a lamp; the runner on the boards
    tp = Vector((XW + 0.2, 2.62, 0.0))
    box('hall_table_top', (0.36, 1.0, 0.03), tp + Vector((0, 0, 0.82)), M['mahogany'], bev=0.006, collection=col, lm='furn')
    box('hall_table_apron', (0.3, 0.94, 0.1), tp + Vector((0, 0, 0.76)), M['mahogany'], bev=0.006, collection=col, lm='furn')
    for sy in (-1, 1):
        for sx in (-1, 1): lathe(f'hall_table_leg{sx}{sy}', [(0.0, 0.0), (0.02, 0.0), (0.025, 0.1), (0.017, 0.4), (0.023, 0.7), (0.0, 0.72)], M['mahogany'], loc=tp + Vector((sx * 0.12, sy * 0.44, 0.0)), seg=12, collection=col, lm='furn')
    bulb = column_lamp('lamp_hall', tp + Vector((0.0, 0.32, 0.835)), M, col, shade_r=0.15)
    box('hall_tray', (0.2, 0.3, 0.012), tp + Vector((0.02, -0.15, 0.84)), M['brass'], bev=0.004, collection=col, lm='furn')
    r, mm = cine.import_gltf(PH('ornate_mirror_01'), loc=(0, 0, 0), rot=(0, 0, math.pi / 2), scale=1.0, collection=col, lm='furn')
    _fit(mm, (XW + 0.03, 2.62, 1.62), 0.8, 'y', ratio=0.3)
    for o in mm:                                       # its glass: dark old silvering (textures.py)
        for sl in o.material_slots:
            p = next((n for n in sl.material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if sl.material and sl.material.node_tree else None
            src = p and p.inputs['Base Color'].links and p.inputs['Base Color'].links[0].from_node
            if src and src.type == 'TEX_IMAGE': src.image = bpy.data.images.load(tx('mirror_color.jpg'), check_existing=True)
    box('hall_runner', (0.8, 3.4, 0.01), (3.28, 1.75, 0.005), M['runner'], bev=0.002, collection=col, lm='furn')
    return bulb


# ---------------------------------------------------------------- the cut
def section(objs, M):
    """Every face the cut passes through, flat and dark: the walls' and the arch's tops."""
    for ob in objs:
        if not ob.name.startswith(('solid_', 'wall_', 'back_wall', 'left_wall', 'kerb')): continue
        me = ob.data
        if M['section'].name not in [m.name for m in me.materials if m]: me.materials.append(M['section'])
        k = [m.name if m else '' for m in me.materials].index(M['section'].name)
        for f in me.polygons:
            c = sum((me.vertices[i].co for i in f.vertices), Vector()) / len(f.vertices)
            if f.normal.z > 0.9 and abs(c.z - RH) < 0.004: f.material_index = k


# ---------------------------------------------------------------- light
WARM = (1.0, 0.72, 0.44)                   # tungsten
SUN = (1.0, 0.84, 0.62)                    # a late summer afternoon
SUN_DIR = Vector((0.42, -0.8, -0.5)).normalized()   # the way the sun's light travels: in through the back and the left


def lights(lamp_bulb, sconce_bulbs, red_bulb, hall_bulb):
    """The sun through the shutters (a hard sun, slats on the floor, the desk and the Don's chair), the sky's soft
    light at each window, Willis's soft top light over the desk, the practicals (the cream lamp, the double sconce,
    Hagen's red lamp), the hall's sun through the sheers and its lamp. Returns the lights."""
    out = []
    def light(name, kind, loc, energy, colour, **kw):
        ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = colour
        for k, v in kw.items(): setattr(ld, k, v)
        ob = cine.link(bpy.data.objects.new(name, ld)); ob.location = loc; out.append(ob)
        if kind in ('AREA', 'SPOT', 'SUN'): ob.visible_camera = False; ob.visible_glossy = False
        return ob
    def aim(ob, d): ob.rotation_euler = Vector(d).to_track_quat('-Z', 'Y').to_euler()
    aim(light('sun', 'SUN', (0, 0, 6), 9.0, SUN, angle=math.radians(0.6)), SUN_DIR)
    z0, z1 = WIN_Z
    for k, c in enumerate(WINDOWS):                                              # the sky and the garden's bounce, outside
        aim(light(f'sky{k}', 'AREA', (c, BACK + 0.45, (z0 + z1) / 2), 120.0, (1.0, 0.92, 0.8), shape='RECTANGLE', size=WW, size_y=z1 - z0), (0, -1, -0.15))
    aim(light('sky_l', 'AREA', (LEFT - 0.45, LWIN, (z0 + z1) / 2), 100.0, (1.0, 0.92, 0.8), shape='RECTANGLE', size=WW, size_y=z1 - z0), (1, 0, -0.15))
    aim(light('top', 'AREA', (DESK.x, DESK.y + 0.1, RH - 0.05), 170.0, (1.0, 0.82, 0.6), shape='RECTANGLE', size=1.6, size_y=1.2), (0, 0, -1))
    light('lamp_cream', 'POINT', lamp_bulb, 40.0, WARM, shadow_soft_size=0.06)
    for k, b in enumerate(sconce_bulbs): light(f'sconce{k}', 'POINT', b, 16.0, WARM, shadow_soft_size=0.03)
    light('lamp_red', 'POINT', red_bulb, 22.0, (1.0, 0.42, 0.26), shadow_soft_size=0.05)
    fx, fw, fh, sw = FRONT_DOOR
    aim(light('hall_sun', 'AREA', (fx, BACK + 0.5, fh / 2 + 0.3), 260.0, SUN, shape='RECTANGLE', size=fw + 2 * sw, size_y=fh), (0, -1, -0.35))
    light('lamp_hall', 'POINT', hall_bulb, 24.0, WARM, shadow_soft_size=0.05)
    return out
