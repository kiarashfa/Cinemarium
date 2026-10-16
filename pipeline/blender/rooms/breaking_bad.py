# Breaking Bad · Saul Goodman's office, in the strip mall on Montgomery Boulevard, as the set stood in season two: the
# desk in a bay of white Ionic columns, the Constitution's "We the People" for wallpaper above white raised panels, a
# round window in the sage frieze over every face of the bay; a royal blue carpet, pale sage walls over an olive dado,
# the law library in red buckram, the gold damask sofa and the coral leather tub chairs, Lady Justice on the desk.
# The door (dark walnut, six panels) opens on the waiting room: beige tile, the shop window's blinds with the lettering
# read backwards, a row of chairs under it, Francesca's sliding window. Afternoon: the sun on the blinds.
#
# The set's door faces the bay; here it is turned onto the room's right side, so that the visitor's view from the
# front right looks into the bay (the show's wide shot) and through the door into the waiting room beside it.
# Where the module's top cuts the walls and the solid behind the bay: a dark `section` face.
import math, os, random
import bpy, bmesh
from mathutils import Vector, Matrix
import cine
from cine import box, cyl, material, moulding, lathe, place, rounded_slab
from rooms.seinfeld import Face, uv_rect, tube, circle, spine_row, picture, _glow
from rooms.the_sopranos import polygon_prism

W, D, H = 9.6, 7.6, 3.0
T = 0.14                                   # the module's walls
LEFT, BACK, RIGHT, FRONT = -W / 2 + T, D / 2 - T, W / 2 - T, -D / 2 + T
RH = 2.75                                  # the rooms' ceilings (phantoms above)
KH = 0.22                                  # the cut-away's kerb
TEX = os.path.join(cine.OUT, 'textures', 'breaking-bad')
tx = lambda n: os.path.join(TEX, n)
PH = lambda n: os.path.join(cine.CACHE, 'polyhaven', n, f'{n}_1k.gltf')

YN = 2.0                                   # the office's north wall (the bay opens in it)
XP, PT = 1.83, 0.14                        # the partition: its office face, its thickness
XW = XP + PT                               # its waiting-room face
P_FULL = 0.0                               # it stands full height from here back; a kerb in front of it
DOOR = (0.62, 1.52, 2.13)                  # the office door in the partition: y0 (its hinge), y1, head
DOOR_OPEN = math.radians(160)
RECEPTION = (2.35, 3.15, 0.98, 1.88)       # Francesca's window: y0, y1, sill, head
BOOTH_X = 0.62                             # the reception booth's west wall (between it and the bay: solid)
BAY = [(-3.2, YN), (-3.2, 2.69), (-2.25, BACK), (-0.55, BACK), (0.4, 2.69), (0.4, YN)]   # A..F, round the bay
BAY_C = Vector((-1.4, 2.7, 0.0))
STORE = (2.15, 3.62, 0.45, 2.42)           # the shop window in the waiting room's back wall: x0, x1, sill, head
ENTRY = (3.76, 4.56, 2.3)                  # the glass door beside it: x0, x1, head
DESK = Vector((-1.4, 2.05, 0.0))           # the desk's centre; it faces -y
SEAT = {'saul': 0.5, 'walt': 0.46, 'jesse': 0.46}   # cushion tops
CHAIRS = {'saul': (-1.4, 2.9), 'walt': (-2.08, 0.95), 'jesse': (-0.72, 0.95)}
HUELL = (Vector((2.38, 0.3, 0.0)), Vector((0.9, -0.44, 0.0)))    # where he stands by the door, which way he faces
SOFA = Vector((LEFT + 0.46, -2.0, 0.0))    # against the west wall, facing +x
WAIT_EXIT = Vector((4.15, 3.05, 0.0))      # where Jesse stands at the glass door, looking out


def chair_at(who):
    """A seat's centre and its facing (the clients face Saul; Saul faces the room)."""
    p = Vector((*CHAIRS[who], 0.0))
    if who == 'saul': return p, Vector((0, -1, 0))
    f = Vector((CHAIRS['saul'][0], CHAIRS['saul'][1], 0)) - p; f.z = 0
    return p, f.normalized()


# ---------------------------------------------------------------- materials
def mats():
    M = {}
    M['carpet'] = material('carpet', rough=0.95, maps={'color': tx('carpet_color.jpg'), 'normal': tx('carpet_normal.jpg')}, scale=0.7, normal_strength=0.6, specular=0.3)
    M['wall'] = material('wall_sage', rough=0.85, maps={'color': tx('wall_color.jpg'), 'normal': tx('wall_normal.jpg')}, scale=1.6, normal_strength=0.3)
    M['dado'] = material('dado_olive', rough=0.8, maps={'color': tx('dado_color.jpg'), 'normal': tx('wall_normal.jpg')}, scale=1.6, normal_strength=0.3)
    M['frieze'] = material('frieze_sage', (0.38, 0.41, 0.27), rough=0.85)
    M['wait_wall'] = material('wait_wall', rough=0.85, maps={'color': tx('wait_wall_color.jpg'), 'normal': tx('wall_normal.jpg')}, scale=1.6, normal_strength=0.3)
    M['booth_wall'] = material('booth_wall', rough=0.85, maps={'color': tx('booth_wall_color.jpg')}, scale=1.6)
    M['ceiling'] = material('ceiling', rough=0.9, maps={'color': tx('ceiling_color.jpg')}, scale=1.4)
    M['white'] = material('paint_white', (0.78, 0.76, 0.7), rough=0.45, coat=0.15)
    M['column'] = material('column_white', (0.8, 0.77, 0.7), rough=0.4, coat=0.25)
    M['constitution'] = material('constitution', rough=0.6, maps={'color': tx('constitution_color.jpg')}, scale=1.0)
    M['walnut'] = material('walnut', rough=0.35, maps={'color': tx('walnut_color.jpg'), 'normal': tx('wood_normal.jpg')}, scale=1.0, normal_strength=0.3, coat=0.4, coat_rough=0.2)
    M['oak'] = material('oak', rough=0.35, maps={'color': tx('oak_color.jpg'), 'normal': tx('wood_normal.jpg')}, scale=0.9, normal_strength=0.3, coat=0.5, coat_rough=0.15)
    M['oxblood'] = material('oxblood_leather', rough=0.38, maps={'color': tx('oxblood_color.jpg'), 'normal': tx('oxblood_normal.jpg')}, scale=0.5, normal_strength=0.5, coat=0.35, coat_rough=0.3)
    M['khaki'] = material('khaki_leather', rough=0.45, maps={'color': tx('khaki_color.jpg'), 'normal': tx('khaki_normal.jpg')}, scale=0.5, normal_strength=0.5, coat=0.25, coat_rough=0.35)
    M['coral'] = material('coral_leather', rough=0.42, maps={'color': tx('coral_color.jpg'), 'normal': tx('coral_normal.jpg')}, scale=0.5, normal_strength=0.4, coat=0.3, coat_rough=0.3)
    M['damask'] = material('damask', rough=0.85, maps={'color': tx('damask_color.jpg'), 'normal': tx('damask_normal.jpg')}, scale=0.55, normal_strength=0.6, sheen=0.4, sheen_tint=(0.5, 0.42, 0.25))
    M['chrome'] = material('chrome', (0.8, 0.8, 0.8), rough=0.1, metal=1.0)
    M['brass'] = material('brass', (0.7, 0.5, 0.22), rough=0.25, metal=1.0)
    M['bronze'] = material('bronze_dark', (0.16, 0.11, 0.07), rough=0.35, metal=0.9)
    M['spines'] = material('law_books', rough=0.55, maps={'color': tx('lawbooks_color.jpg')}, scale=1.0)
    M['paper'] = material('paper', (0.86, 0.85, 0.8), rough=0.85)
    M['folder'] = material('folder_manila', (0.74, 0.6, 0.38), rough=0.75)
    M['black'] = material('black_plastic', (0.02, 0.02, 0.022), rough=0.4)
    M['amber'] = material('amber_glass', (0.5, 0.26, 0.02), rough=0.15, emission=(1.0, 0.5, 0.08), emission_strength=0.7, coat=0.8)
    M['shade'] = material('lamp_shade', rough=0.8, maps={'color': tx('linen_color.jpg')}, scale=0.4, emission=(1.0, 0.82, 0.58), emission_strength=1.6)
    M['porthole'] = material('porthole_glass', (0.9, 0.88, 0.82), rough=0.5, emission=(1.0, 0.94, 0.84), emission_strength=5.0)
    M['sconce'] = material('sconce_glass', (0.8, 0.5, 0.2), rough=0.4, emission=(1.0, 0.66, 0.32), emission_strength=6.0)
    M['tile'] = material('tile', rough=0.35, maps={'color': tx('tile_color.jpg'), 'normal': tx('tile_normal.jpg')}, scale=2.4, normal_strength=0.4, coat=0.2, coat_rough=0.3)
    M['alu'] = material('anodised_bronze', (0.12, 0.1, 0.08), rough=0.35, metal=0.8)
    M['blind'] = material('blind_slat', (0.84, 0.82, 0.76), rough=0.5)
    M['view'] = material('storefront_view', rough=0.9, maps={'color': tx('storefront_view.jpg')}, scale=1.0)
    M['glass_door'] = material('glass_door', (0.2, 0.24, 0.24), rough=0.05, coat=1.0)
    M['vinyl'] = material('vinyl_burgundy', rough=0.4, maps={'color': tx('vinyl_color.jpg')}, scale=0.4, coat=0.3)
    M['magazine'] = material('magazines', rough=0.35, maps={'color': tx('magazine_color.jpg')}, scale=1.0, coat=0.5)
    M['monitor'] = material('monitor_screen', rough=0.2, maps={'color': tx('monitor.jpg')}, scale=1.0, emission=(1, 1, 1), emission_strength=0.0)
    M['beige'] = material('beige_plastic', (0.62, 0.58, 0.5), rough=0.45)
    M['filebox'] = material('file_box', rough=0.8, maps={'color': tx('filebox_color.jpg')}, scale=1.0)
    M['plaque'] = material('plaque', rough=0.3, metal=0.6, maps={'color': tx('plaque.jpg')}, scale=1.0)
    M['diploma'] = material('diploma', rough=0.4, maps={'color': tx('diploma.jpg')}, scale=1.0, coat=0.5)
    M['landscape'] = material('landscape', rough=0.5, maps={'color': tx('landscape.jpg')}, scale=1.0)
    for k in range(4): M[f'photo{k}'] = material(f'photo{k}', rough=0.3, maps={'color': tx(f'photo{k}.jpg')}, scale=1.0, coat=0.6)
    M['black_wood'] = material('frame_black', (0.03, 0.025, 0.02), rough=0.35, coat=0.4)
    M['gilt'] = material('frame_gilt', (0.62, 0.46, 0.2), rough=0.3, metal=0.9)
    M['mat_board'] = material('mat_board', (0.82, 0.8, 0.74), rough=0.9)
    M['cream'] = material('cream_paint', (0.76, 0.72, 0.62), rough=0.5, coat=0.2)
    M['mug'] = material('mug_white', (0.84, 0.83, 0.8), rough=0.2, coat=0.6)
    pt = lambda n: os.path.join(cine.CACHE, 'polyhaven', 'potted_plant_02', 'textures', f'potted_plant_02_leaves_{n}_1k.jpg')
    M['plant'] = material('plant_leaves', rough=0.55, maps={'color': pt('diff'), 'normal': pt('nor_gl')}, scale=1.0, normal_strength=0.6)
    M['kerb'] = material('kerb', (0.25, 0.22, 0.2), rough=0.9)
    M['section'] = material('section', (0.03, 0.028, 0.026), rough=0.92)
    _glow(M['view'], 2.4)   # the parking lot in the sun: it shines through the blinds on the web as in the renders
    return M


# ---------------------------------------------------------------- small kit
SKIRT = [(0, 0), (0.014, 0), (0.014, 0.09), (0.01, 0.1), (0.005, 0.108), (0, 0.11)]
RAIL = [(0, 0), (0.014, 0.004), (0.022, 0.014), (0.02, 0.026), (0.01, 0.032), (0, 0.036)]
CAP = [(0, 0), (0.03, 0.0), (0.036, 0.012), (0.03, 0.03), (0.016, 0.038), (0, 0.044)]
CORNICE = [(0, 0), (0.015, 0), (0.015, 0.02), (0.035, 0.035), (0.07, 0.07), (0.09, 0.095), (0.1, 0.12), (0, 0.12)]


def uv_window(ob, u0, v0, u1, v1):
    """Squeeze an object's 0..1 UVs into a window of its texture (one face of the bay shows one part of the page)."""
    uv = ob.data.uv_layers['UVMap']
    for d in uv.data: d.uv = (u0 + d.uv[0] * (u1 - u0), v0 + d.uv[1] * (v1 - v0))
    return ob


def office_wall(face, name, col, u0=0.0, u1=None, openings=()):
    """An office wall's finish: the olive dado to 0.9 m under a walnut chair rail, a walnut skirting; the sage above is
    the wall itself. `openings` [(u0, u1)] stop the dado, rail and skirting (a door)."""
    u1 = face.L if u1 is None else u1
    spans, u = [], u0
    for a, b in sorted(openings):
        if a > u + 0.01: spans.append((u, a))
        u = max(u, b)
    if u < u1 - 0.01: spans.append((u, u1))
    for k, (a, b) in enumerate(spans):
        face.slab(f'{name}_dado{k}', a, b, 0.0, 0.9, 0.0, 0.006, M_['dado'], col, bev=0, lm='arch')
        face.run(f'{name}_rail{k}', a, b, 0.9, RAIL, M_['walnut'], col, o=0.006, lm='arch')
        face.run(f'{name}_skirt{k}', a, b, 0.0, SKIRT, M_['walnut'], col, o=0.006, lm='arch')


M_ = {}


# ---------------------------------------------------------------- the shell
def shell(M, arch, furn, phantom):
    """Floors, the module's walls (the left full, the back full with the shop window and its door), the office's north
    wall and the solid round the bay, the partition with its door and Francesca's window, the booth; kerbs, phantoms."""
    M_.clear(); M_.update(M)
    box('subfloor', (W, D, 0.03), (0, 0, -0.027), M['kerb'], bev=0, collection=arch, lm='arch')
    # the office's carpet (into the bay), the waiting room's tile, the booth's
    office = [(LEFT, -D / 2 + 0.002), (XP, -D / 2 + 0.002), (XP, YN)] + [p for p in reversed(BAY)] + [(LEFT, YN)]
    polygon_prism('floor', [(x, y) for x, y in office], -0.02, 0.0, M['carpet'], arch, lm='arch')
    box('floor_wait', (RIGHT + T - XP, D - 0.004, 0.02), ((RIGHT + T + XP) / 2, 0, -0.01), M['tile'], bev=0, collection=arch, lm='arch')
    box('floor_booth', (XP - BOOTH_X, BACK - YN, 0.02), ((XP + BOOTH_X) / 2, (BACK + YN) / 2, -0.01), M['tile'], bev=0, collection=arch, lm='arch')
    # the module's left wall and back wall (round the shop window and its door)
    box('left_wall', (T, D, RH), (-W / 2 + T / 2, 0, RH / 2), M['wall'], bev=0, collection=arch, lm='arch')
    x0, x1, s0, s1 = STORE; e0, e1, eh = ENTRY
    for k, (a, b, m) in enumerate(((LEFT, BOOTH_X + 0.12, 'wall'), (BOOTH_X + 0.12, XP, 'booth_wall'), (XP, x0, 'wait_wall'), (x1, e0, 'wait_wall'), (e1, W / 2, 'wait_wall'))):
        box(f'back_wall_{k}', (b - a, T, RH), ((a + b) / 2, D / 2 - T / 2, RH / 2), M[m], bev=0, collection=arch, lm='arch')
    box('back_wall_sill', (x1 - x0, T, s0), ((x0 + x1) / 2, D / 2 - T / 2, s0 / 2), M['wait_wall'], bev=0, collection=arch, lm='arch')
    box('back_wall_head', (x1 - x0, T, RH - s1), ((x0 + x1) / 2, D / 2 - T / 2, (RH + s1) / 2), M['wait_wall'], bev=0, collection=arch, lm='arch')
    box('back_wall_door_head', (e1 - e0, T, RH - eh), ((e0 + e1) / 2, D / 2 - T / 2, (RH + eh) / 2), M['wait_wall'], bev=0, collection=arch, lm='arch')
    # the solid round the bay: left of it (the law library's wall) and right of it (to the booth); up to the ceiling
    A, B, C, Dd, E, F = BAY
    polygon_prism('solid_left', [(LEFT, YN), A, B, C, (LEFT, BACK)], 0.0, RH, M['wall'], arch, lm='arch')
    polygon_prism('solid_right', [F, (BOOTH_X, YN), (BOOTH_X, BACK), Dd, E], 0.0, RH, M['wall'], arch, lm='arch')
    # the office's north wall from the bay to the partition (the booth's south wall behind it)
    box('wall_north', (XP - BOOTH_X, 0.14, RH), ((XP + BOOTH_X) / 2, YN + 0.07, RH / 2), M['wall'], bev=0, collection=arch, lm='arch')
    box('wall_north_booth', (XP - BOOTH_X - 0.12, 0.006, RH), ((XP + BOOTH_X + 0.12) / 2, YN + 0.143, RH / 2), M['booth_wall'], bev=0, collection=arch, lm='arch')
    # the partition: full height from P_FULL back, with the door and Francesca's window; a kerb in front
    d0, d1, dh = DOOR; r0, r1, rs, rh = RECEPTION
    for k, (a, b) in enumerate(((P_FULL, d0), (d1, r0), (r1, BACK))):
        box(f'wall_part_{k}', (PT, b - a, RH), (XP + PT / 2, (a + b) / 2, RH / 2), M['wait_wall'], bev=0, collection=arch, lm='arch')
    box('wall_part_door_head', (PT, d1 - d0, RH - dh), (XP + PT / 2, (d0 + d1) / 2, (RH + dh) / 2), M['wait_wall'], bev=0, collection=arch, lm='arch')
    box('wall_part_rec_sill', (PT, r1 - r0, rs), (XP + PT / 2, (r0 + r1) / 2, rs / 2), M['wait_wall'], bev=0, collection=arch, lm='arch')
    box('wall_part_rec_head', (PT, r1 - r0, RH - rh), (XP + PT / 2, (r0 + r1) / 2, (RH + rh) / 2), M['wait_wall'], bev=0, collection=arch, lm='arch')
    box('kerb_part', (PT, P_FULL - FRONT, KH), (XP + PT / 2, (P_FULL + FRONT) / 2, KH / 2), M['kerb'], bev=0.002, collection=arch, lm='arch')
    # the booth's west wall
    box('wall_booth', (0.12, BACK - YN - 0.14, RH), (BOOTH_X + 0.06, (BACK + YN + 0.14) / 2, RH / 2), M['booth_wall'], bev=0, collection=arch, lm='arch')
    # the cut-away
    box('kerb_front', (W, T, KH), (0, -D / 2 + T / 2, KH / 2), M['kerb'], bev=0.002, collection=arch, lm='arch')
    box('kerb_right', (T, D - 2 * T, KH), (W / 2 - T / 2, 0, KH / 2), M['kerb'], bev=0.002, collection=arch, lm='arch')
    # phantoms: the ceilings, the missing walls, the partition above its kerb (closed, for the bounce light)
    box('ceiling', (W, D, 0.04), (0, 0, RH + 0.02), M['ceiling'], bev=0, collection=phantom, bake_only=1)
    box('front_wall', (W, T, H - KH), (0, -D / 2 + T / 2, KH + (H - KH) / 2), M['wall'], bev=0, collection=phantom, bake_only=1)
    box('right_wall', (T, D, H - KH), (W / 2 - T / 2, 0, KH + (H - KH) / 2), M['wait_wall'], bev=0, collection=phantom, bake_only=1)
    box('part_phantom', (PT, P_FULL - FRONT, RH - KH), (XP + PT / 2, (P_FULL + FRONT) / 2, KH + (RH - KH) / 2), M['wall'], bev=0, collection=phantom, bake_only=1)
    _finishes(M, arch, furn)


def _finishes(M, arch, furn):
    """The office's dado, rails and skirting on every wall it shows; the waiting room's skirting; the door's casings."""
    office_wall(Face((LEFT, FRONT - 0.1), (LEFT, YN), (1, 0)), 'west', arch)
    office_wall(Face((LEFT, YN), (BAY[0][0], YN), (0, -1)), 'north_l', arch)
    office_wall(Face((BAY[-1][0], YN), (XP, YN), (0, -1)), 'north_r', arch)
    d0, d1, dh = DOOR
    fo = Face((XP, YN), (XP, P_FULL), (-1, 0))                               # the partition, office side (back to front)
    office_wall(fo, 'part_o', arch, openings=[(YN - d1 - 0.1, YN - d0 + 0.1)])
    for k, (a, b, z0) in enumerate(((0.0, YN - d1, 0.9), (YN - d0, YN - P_FULL, 0.9), (YN - d1, YN - d0, dh))):
        fo.slab(f'part_o_paint{k}', a, b, z0, RH, 0.0, 0.004, M['wall'], arch, bev=0, lm='arch')
    fw = Face((XW, P_FULL), (XW, BACK), (1, 0))                               # its waiting-room side (front to back)
    r0, r1, rs, rh = RECEPTION
    for k, (a, b) in enumerate(((0.0, d0 - P_FULL - 0.1), (d1 - P_FULL + 0.1, BACK - P_FULL))):
        fw.run(f'part_w_skirt{k}', a, b, 0.0, SKIRT, M['walnut'], arch, lm='arch')
    fb = Face((XW, BACK), (RIGHT + T, BACK), (0, -1))
    fb.run('wait_back_skirt0', 0.0, STORE[0] - XW, 0.0, SKIRT, M['walnut'], arch, lm='arch')
    # the door's casings, both sides: broad dark walnut, plinth blocks
    for face, name, u in ((fo, 'door_casing_o', YN - d1), (fw, 'door_casing_w', d0 - P_FULL)):
        w = 0.1
        for k, uu in enumerate((u - w, u + (d1 - d0))):
            face.slab(f'{name}_leg{k}', uu, uu + w, 0.0, dh + w, 0.0, 0.024, M['walnut'], arch, bev=0.004, lm='arch')
        face.slab(f'{name}_head', u, u + (d1 - d0), dh, dh + w, 0.0, 0.024, M['walnut'], arch, bev=0.004, lm='arch')
        face.slab(f'{name}_crown', u - w - 0.02, u + (d1 - d0) + w + 0.02, dh + w, dh + w + 0.03, 0.0, 0.034, M['walnut'], arch, bev=0.006, lm='arch')
    # the door's reveal (its jambs and head through the partition)
    box('door_jamb0', (PT, 0.02, dh), (XP + PT / 2, d0 + 0.01, dh / 2), M['walnut'], bev=0.002, collection=arch, lm='arch')
    box('door_jamb1', (PT, 0.02, dh), (XP + PT / 2, d1 - 0.01, dh / 2), M['walnut'], bev=0.002, collection=arch, lm='arch')
    box('door_soffit', (PT, d1 - d0, 0.02), (XP + PT / 2, (d0 + d1) / 2, dh - 0.01), M['walnut'], bev=0.002, collection=arch, lm='arch')


# ---------------------------------------------------------------- the bay
def _bay_faces():
    """The bay's five faces, each seen from inside the bay (normal toward its middle)."""
    out = []
    for a, b in zip(BAY, BAY[1:]):
        a, b = Vector((*a, 0)), Vector((*b, 0)); d = (b - a).normalized(); n = Vector((d.y, -d.x, 0))
        if n.dot(BAY_C - (a + b) / 2) < 0: n = -n
        out.append(Face(a, b, n))
    return out


def _fluted(name, r, h, z0, mat, col, flutes=20, depth=0.12, seg_h=1, half=False, **props):
    """A fluted column shaft (concave flutes between fillets), from z0 up `h`; `half`: only the front half (engaged)."""
    bm = bmesh.new(); n = flutes * 6; rings = []
    a_range = (math.pi, 2 * math.pi) if half else (0, 2 * math.pi)
    k_n = n // 2 + 1 if half else n
    for z in (z0, z0 + h):
        ring = []
        for i in range(k_n):
            a = a_range[0] + (a_range[1] - a_range[0]) * i / (n // 2 if half else n)
            f = (i % 6) / 6.0; rr = r * (1 - depth * math.sin(math.pi * min(f / 0.84, 1.0)) if f < 0.84 else r)
            ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), z)))
        rings.append(ring)
    a, b = rings
    for i in range(k_n - (1 if half else 0)):
        j = (i + 1) % k_n; bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = cine._mesh_obj(name, bm, mat, col, smooth=False)
    for k, v in props.items(): ob[k] = v
    return ob


def column(name, p, r, col, M, facing=None, plinth=0.0):
    """A white Ionic column standing at p, up to the ceiling: a square plinth (if any), an Attic base, the fluted
    shaft, the capital's echinus and its two volutes facing `facing` (and away), the abacus under the ceiling."""
    parts = []; z = 0.0
    if plinth:
        parts.append(box(f'{name}_plinth', (r * 2.9, r * 2.9, plinth), (0, 0, plinth / 2), M['column'], bev=0.006, collection=col, lm='furn'))
        parts.append(box(f'{name}_plinth_cap', (r * 3.05, r * 3.05, 0.03), (0, 0, plinth - 0.015), M['column'], bev=0.006, collection=col, lm='furn'))
        z = plinth
    base = [(0.0, 0.0), (r * 1.42, 0.0), (r * 1.42, 0.05), (r * 1.35, 0.06), (r * 1.3, 0.09), (r * 1.18, 0.1), (r * 1.18, 0.12), (r * 1.25, 0.14), (r * 1.15, 0.17), (r * 1.05, 0.18), (0.0, 0.18)]
    parts.append(lathe(f'{name}_base', [(a, b + z) for a, b in base], M['column'], seg=40, collection=col, lm='furn'))
    top = RH - 0.21
    parts.append(_fluted(f'{name}_shaft', r, top - (z + 0.18), z + 0.18, M['column'], col, lm='furn'))
    parts.append(lathe(f'{name}_neck', [(0.0, top), (r * 1.02, top), (r * 1.08, top + 0.03), (r * 1.25, top + 0.08), (r * 1.2, top + 0.11), (0.0, top + 0.11)], M['column'], seg=40, collection=col, lm='furn'))
    f = Vector(facing or (0, -1, 0)).normalized(); s = Vector((-f.y, f.x, 0))
    parts.append(box(f'{name}_abacus', (r * 3.0, r * 2.4, 0.07), (0, 0, RH - 0.035), M['column'], rot=(0, 0, math.atan2(s.y, s.x)), bev=0.008, collection=col, lm='furn'))
    parts.append(box(f'{name}_cushion', (r * 3.0, r * 1.9, 0.07), (0, 0, RH - 0.105), M['column'], rot=(0, 0, math.atan2(s.y, s.x)), bev=0.02, collection=col, lm='furn'))
    for sd in (-1, 1):                                                      # the volutes: a scroll each side
        c = s * sd * r * 1.25 + Vector((0, 0, RH - 0.12))
        v = cyl(f'{name}_volute{sd}', 0.075 * r / 0.16, r * 1.9, c, M['column'], rot=(0, 0, 0), seg=24, collection=col, lm='furn')
        v.rotation_euler = f.to_track_quat('Z', 'X').to_euler()
        parts.append(v)
        eye = cyl(f'{name}_eye{sd}', 0.03 * r / 0.16, r * 1.95, c, M['column'], seg=12, collection=col, lm='furn')
        eye.rotation_euler = f.to_track_quat('Z', 'X').to_euler(); parts.append(eye)
    for o in parts: place(o, Matrix.Translation((p[0], p[1], 0)))
    return parts


def bay(M, arch, furn):
    """The bay behind the desk: on every face white raised panels to 1 m under a cap rail, the Constitution to 2 m, a
    white cornice, the sage frieze with its round window; an engaged column at each corner, two free-standing on
    plinths at the mouth. Returns the windows' centres and normals (lit from behind)."""
    faces = _bay_faces(); lights = []
    # which part of the page each face shows (u0, v0, u1, v1); the back face carries "We the People"
    pages = [(0.02, 0.22, 0.42, 0.62), (0.45, 0.3, 0.98, 0.7), (0.08, 0.62, 0.92, 0.99), (0.05, 0.12, 0.6, 0.5), (0.55, 0.0, 0.98, 0.4)]
    for k, f in enumerate(faces):
        L = f.L
        f.slab(f'bay{k}_wainscot', 0.0, L, 0.0, 1.0, 0.0, 0.016, M['white'], arch, bev=0, lm='arch')
        n_p = max(1, int(round((L - 0.12) / 0.5)))                               # raised panels, ~0.5 m wide
        pw = (L - 0.1 - 0.06 * (n_p - 1)) / n_p
        for j in range(n_p):
            u = 0.05 + j * (pw + 0.06)
            f.slab(f'bay{k}_panel{j}', u + 0.04, u + pw - 0.04, 0.2, 0.86, 0.016, 0.014, M['white'], arch, bev=0.012, lm='arch')
            f.slab(f'bay{k}_frame{j}', u, u + pw, 0.16, 0.9, 0.016, 0.004, M['white'], arch, bev=0.003, lm='arch')
        f.run(f'bay{k}_skirt', 0.0, L, 0.0, SKIRT, M['white'], arch, o=0.016, lm='arch')
        f.run(f'bay{k}_cap', 0.0, L, 0.97, CAP, M['white'], arch, o=0.016, lm='arch')
        paper = f.slab(f'bay{k}_paper', 0.0, L, 1.015, 2.0, 0.0, 0.004, M['constitution'], arch, bev=0, lm='arch')
        _uv_on_face(paper, f, pages[k])
        f.run(f'bay{k}_cornice', 0.0, L, 1.98, CORNICE, M['white'], arch, lm='arch')
        f.slab(f'bay{k}_frieze', 0.0, L, 2.1, RH, 0.0, 0.006, M['frieze'], arch, bev=0, lm='arch')
        # the round window: a moulded white ring, its frosted glass lit from behind
        c = f.at(L / 2, 0.0, 2.43)
        u_, v_ = f.d, Vector((0, 0, 1))                                          # a round moulding: a fat torus and a fine bead
        tube(f'bay{k}_ring', circle(c + f.n * 0.02, 0.25, u_, v_, n=48), 0.045, M['white'], furn, closed=True, seg=12, lm='furn')
        tube(f'bay{k}_bead', circle(c + f.n * 0.03, 0.2, u_, v_, n=48), 0.012, M['white'], furn, closed=True, seg=8, lm='furn')
        glass = cyl(f'bay{k}_glass', 0.205, 0.01, (0, 0, 0), M['porthole'], seg=40, bev=0, collection=furn)
        glass.matrix_basis = Matrix.Translation(c + f.n * 0.012) @ f.n.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        lights.append((c, f.n, f, L))
        if k == 2:                                                               # a scrolled crest over the middle one
            for sd in (-1, 1):
                sc = cyl(f'bay{k}_scroll{sd}', 0.045, 0.03, f.at(L / 2 + sd * 0.2, 0.015, 2.68), M['white'], seg=20, collection=arch, lm='arch')
                sc.rotation_euler = f.n.to_track_quat('Z', 'Y').to_euler()
            f.slab(f'bay{k}_crest', L / 2 - 0.2, L / 2 + 0.2, 2.66, 2.72, 0.0, 0.03, M['white'], arch, bev=0.008, lm='arch')
    # the columns: engaged at the four corners, two free-standing at the mouth on their plinths
    for k, p in enumerate(BAY[1:-1]):
        p = Vector((*p, 0)); inward = (BAY_C - p); inward.z = 0; inward.normalize()
        column(f'col_e{k}', tuple(p + inward * 0.16), 0.13, furn, M, facing=inward)
    for k, (p, sd) in enumerate(((BAY[0], -1), (BAY[-1], 1))):
        column(f'col_f{k}', (p[0] + sd * 0.08, p[1] - 0.24), 0.16, furn, M, facing=(0, -1, 0), plinth=0.28)
    return lights


def _uv_on_face(ob, face, win):
    """0..1 UVs across a slab laid on a bay face (along the face, up), squeezed into the page window `win`."""
    me = ob.data; uv = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
    pts = [ob.matrix_basis @ v.co for v in me.vertices]                  # matrix_world is stale here
    us = [(p - face.a).dot(face.d) for p in pts]; zs = [p.z for p in pts]
    u0, u1, z0, z1 = min(us), max(us), min(zs), max(zs)
    for poly in me.polygons:
        for li in poly.loop_indices:
            p = pts[me.loops[li].vertex_index]
            u = ((p - face.a).dot(face.d) - u0) / (u1 - u0 + 1e-9); v = (p.z - z0) / (z1 - z0 + 1e-9)
            uv.data[li].uv = (win[0] + u * (win[2] - win[0]), win[1] + v * (win[3] - win[1]))


# ---------------------------------------------------------------- the desk and its chairs
def _frame(p, f):
    """Built facing -y about the origin, turned to face f at p."""
    return Matrix.Translation((p[0], p[1], 0)) @ Matrix.Rotation(math.atan2(f[1], f[0]) + math.pi / 2, 4, 'Z')


def desk(M, col):
    """Saul's desk: a big carved oak double-pedestal desk, its panelled front to the room; on it the brass banker's lamp
    with its amber shade, files and law books, the red reporters between bookends, Lady Justice (cast apart), the
    black phone, the gold pen stand, his mug, papers. Returns the lamp's bulb and the statuette's spot."""
    parts = []; add = lambda o: (parts.append(o), o)[1]
    zt = 0.76; Wd, Dp = 1.86, 0.96
    add(rounded_slab('desk_top', Wd, Dp, 0.05, 0.03, (0, 0, zt - 0.025), M['oak'], edge_bev=0.012, collection=col, lm='furn'))
    add(box('desk_top_band', (Wd - 0.04, Dp - 0.04, 0.05), (0, 0, zt - 0.075), M['oak'], bev=0.006, collection=col, lm='furn'))
    for s in (-1, 1):
        x = s * (Wd / 2 - 0.29)
        add(box(f'desk_ped{s}', (0.54, Dp - 0.08, zt - 0.1), (x, 0.0, (zt - 0.1) / 2 + 0.0), M['oak'], bev=0.008, collection=col, lm='furn'))
        add(box(f'desk_plinth{s}', (0.58, Dp - 0.04, 0.08), (x, 0.0, 0.04), M['oak'], bev=0.01, collection=col, lm='furn'))
        for k, (z0, z1) in enumerate(((0.12, 0.38), (0.42, zt - 0.14))):     # raised and fielded panels on its front
            add(box(f'desk_panel{s}{k}', (0.42, 0.02, z1 - z0), (x, -(Dp - 0.08) / 2 - 0.006, (z0 + z1) / 2), M['oak'], bev=0.016, seg=3, collection=col, lm='furn'))
        add(box(f'desk_corbel{s}', (0.06, 0.06, 0.2), (s * (Wd / 2 - 0.04), -(Dp / 2 - 0.05), zt - 0.2), M['oak'], bev=0.012, collection=col, lm='furn'))
    add(box('desk_modesty', (Wd - 1.16, 0.04, zt - 0.22), (0, -(Dp - 0.08) / 2 + 0.04, (zt - 0.22) / 2 + 0.12), M['oak'], bev=0.006, collection=col, lm='furn'))
    add(box('desk_carving', (0.5, 0.02, 0.12), (0, -(Dp - 0.08) / 2 + 0.015, zt - 0.17), M['oak'], bev=0.02, seg=3, collection=col, lm='furn'))
    add(box('desk_blotter', (0.7, 0.46, 0.006), (0.0, 0.12, zt + 0.003), M['oxblood'], bev=0.002, collection=col, lm='furn'))
    for k in range(4): add(box(f'desk_paper{k}', (0.215, 0.28, 0.003), (0.08 + 0.03 * k, 0.1 + 0.015 * k, zt + 0.008 + 0.003 * k), M['paper'], rot=(0, 0, 0.12 * k - 0.15), bev=0, collection=col, lm='furn'))
    # the lamp on the desk's left (as the room sees it), files and books beside it
    lb = Vector((-0.62, 0.18, zt))
    add(cyl('lamp_foot', 0.075, 0.025, lb + Vector((0, 0, 0.0125)), M['brass'], seg=24, collection=col, lm='furn'))
    add(cyl('lamp_stem', 0.009, 0.36, lb + Vector((0, 0, 0.2)), M['brass'], seg=10, collection=col, lm='furn'))
    add(cyl('lamp_arm', 0.008, 0.12, lb + Vector((0, -0.04, 0.37)), M['brass'], rot=(math.pi / 2, 0, 0), seg=10, collection=col, lm='furn'))
    sh = add(cyl('lamp_shade', 0.065, 0.3, lb + Vector((0, -0.07, 0.36)), M['amber'], rot=(0, math.pi / 2, 0), seg=24, r2=0.065, collection=col))
    sh.scale = (1.0, 1.0, 1.0)
    bulb = lb + Vector((0, -0.08, 0.33))
    for k in range(4): add(box(f'desk_files{k}', (0.3, 0.24, 0.025), (-0.66 + 0.01 * k, -0.18, zt + 0.0125 + 0.026 * k), M['folder'] if k % 2 else M['paper'], rot=(0, 0, 0.05 * k), bev=0.002, collection=col, lm='furn'))
    for k in range(3): add(box(f'desk_tome{k}', (0.28, 0.21, 0.05), (-0.66, -0.18, zt + 0.11 + 0.05 * k), M['oxblood'] if k != 1 else M['walnut'], rot=(0, 0, -0.08 * k), bev=0.004, collection=col, lm='furn'))
    # the right end: the reporters between brass bookends, Lady Justice, the phone
    for k in range(5): add(box(f'desk_book{k}', (0.05, 0.22, 0.28), (0.5 + 0.052 * k, 0.24, zt + 0.14), M['oxblood'], bev=0.004, collection=col, lm='furn'))
    for s in (-1, 1): add(box(f'desk_bookend{s}', (0.02, 0.12, 0.16), (0.5 + 0.104 + s * 0.15, 0.24, zt + 0.08), M['brass'], bev=0.004, collection=col, lm='furn'))
    add(box('desk_phone', (0.2, 0.22, 0.06), (0.52, -0.12, zt + 0.03), M['black'], bev=0.012, collection=col, lm='furn'))
    add(box('desk_phone_handset', (0.22, 0.06, 0.04), (0.52, -0.06, zt + 0.08), M['black'], bev=0.015, collection=col, lm='furn'))
    add(box('desk_pen_base', (0.18, 0.08, 0.025), (0.0, -0.32, zt + 0.0125), M['black'], bev=0.006, collection=col, lm='furn'))
    for s in (-1, 1): add(cyl(f'desk_pen{s}', 0.004, 0.16, (s * 0.05, -0.3, zt + 0.09), M['brass'], rot=(math.radians(-20), 0, 0), seg=8, collection=col, lm='furn'))
    add(lathe('desk_mug', [(0.0, 0.0), (0.04, 0.0), (0.042, 0.1), (0.038, 0.1), (0.0, 0.01)], M['mug'], loc=(-0.28, -0.24, zt), seg=18, collection=col, lm='furn'))
    for o in parts: place(o, _frame(DESK, (0, -1)))
    lady = _frame(DESK, (0, -1)) @ Vector((0.82, -0.05, zt))
    return _frame(DESK, (0, -1)) @ bulb, lady


def saul_chair(M, col):
    """Saul's chair: a tall oxblood leather executive chair, its back buttoned, rolled arms, on a five-star base."""
    p, f = chair_at('saul'); parts = []; add = lambda o: (parts.append(o), o)[1]
    st = SEAT['saul']
    add(rounded_slab('xchair_seat', 0.58, 0.56, 0.13, 0.08, (0, -0.02, st - 0.065), M['oxblood'], edge_bev=0.035, collection=col, lm='furn'))
    bk = add(rounded_slab('xchair_back', 0.6, 0.16, 0.86, 0.12, (0, 0, 0), M['oxblood'], edge_bev=0.05, collection=col, lm='furn'))
    bk.rotation_euler.x = math.radians(-10); bk.location = (0, 0.29, st + 0.46)
    for k in range(4):                                                     # the buttoned back: rows of tufts
        for j in range(3):
            add(cyl(f'xchair_tuft{k}{j}', 0.012, 0.012, (-0.16 + 0.16 * j + (0.08 if k % 2 else 0) * (j < 2), 0.205 - 0.02 * k * 0.0, st + 0.3 + 0.17 * k), M['oxblood'], rot=(math.pi / 2, 0, 0), seg=10, collection=col, lm='furn'))
    for s in (-1, 1):
        add(rounded_slab(f'xchair_arm{s}', 0.1, 0.5, 0.1, 0.04, (s * 0.31, -0.02, st + 0.2), M['oxblood'], edge_bev=0.03, collection=col, lm='furn'))
        add(box(f'xchair_armpost{s}', (0.04, 0.04, 0.2), (s * 0.31, -0.06, st + 0.06), M['chrome'], bev=0.008, collection=col, lm='furn'))
    add(cyl('xchair_column', 0.03, st - 0.16, (0, 0, (st - 0.16) / 2 + 0.06), M['chrome'], seg=14, collection=col, lm='furn'))
    for k in range(5):
        a = k * 2 * math.pi / 5 + 0.3
        add(box(f'xchair_leg{k}', (0.32, 0.045, 0.035), (0.16 * math.cos(a), 0.16 * math.sin(a), 0.07), M['chrome'], rot=(0, 0, a), bev=0.008, collection=col, lm='furn'))
        add(cyl(f'xchair_castor{k}', 0.025, 0.03, (0.31 * math.cos(a), 0.31 * math.sin(a), 0.026), M['black'], rot=(math.pi / 2, 0, a), seg=10, collection=col, lm='furn'))
    for o in parts: place(o, _frame(p, f))


def client_chair(who, M, col):
    """A client chair: khaki leather seat and back with brass nailheads round its edges, on a bent chrome flat-bar frame
    (a sled base, its arms looping up and forward)."""
    p, f = chair_at(who); parts = []; add = lambda o: (parts.append(o), o)[1]
    st = SEAT[who]
    add(rounded_slab(f'{who}_cchair_seat', 0.52, 0.5, 0.08, 0.04, (0, -0.02, st - 0.04), M['khaki'], edge_bev=0.025, collection=col, lm='furn'))
    bk = add(rounded_slab(f'{who}_cchair_back', 0.52, 0.06, 0.42, 0.04, (0, 0, 0), M['khaki'], edge_bev=0.02, collection=col, lm='furn'))
    bk.rotation_euler.x = math.radians(-12); bk.location = (0, 0.26, st + 0.28)
    for s in (-1, 1):
        x = s * 0.29
        add(tube(f'{who}_cchair_bar{s}', [(x, -0.3, 0.012), (x, 0.28, 0.012), (x, 0.31, 0.05), (x, 0.18, st - 0.09), (x, -0.16, st - 0.09), (x, -0.24, st + 0.1), (x, 0.12, st + 0.2), (x, 0.24, st + 0.22)], 0.011, M['chrome'], col, seg=8, lm='furn'))
        for k in range(7):                                                   # nailheads along the seat's sides
            add(cyl(f'{who}_cchair_nail{s}{k}', 0.005, 0.004, (s * 0.262, -0.24 + 0.07 * k, st - 0.03), M['brass'], rot=(0, math.pi / 2, 0), seg=8, collection=col, lm='furn'))
    for o in parts: place(o, _frame(p, f))


# ---------------------------------------------------------------- the sitting corner, the law library
def tub_chair(name, p, f, M, col):
    """A coral leather tub chair: one curved shell for back and arms, a loose seat cushion, short chrome feet."""
    parts = []; bm = bmesh.new(); n = 32; rings = []
    for i in range(n + 1):
        u = -1 + 2 * i / n; ang = u * math.radians(130)
        cx, cy = 0.36 * math.sin(ang), 0.05 + 0.33 * math.cos(ang)
        top = 0.74 - 0.14 * min(1, max(0, (abs(ang) - math.radians(40)) / math.radians(90))) ** 1.2
        o = Vector((math.sin(ang), math.cos(ang), 0))
        rings.append([bm.verts.new(Vector((cx, cy, z)) + o * dr) for dr, z in ((-0.1, 0.16), (0.0, 0.16), (0.0, top), (-0.1, top))])
    for a, b in zip(rings, rings[1:]):
        for k in range(4): bm.faces.new((a[k], b[k], b[(k + 1) % 4], a[(k + 1) % 4]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    sh = cine._mesh_obj(f'{name}_shell', bm, M['coral'], col, smooth=True); sh['lm'] = 'furn'
    md = sh.modifiers.new('bevel', 'BEVEL'); md.width = 0.035; md.segments = 4; md.limit_method = 'ANGLE'; md.angle_limit = math.radians(40)
    parts.append(sh)
    parts.append(rounded_slab(f'{name}_base', 0.62, 0.58, 0.18, 0.2, (0, -0.02, 0.17), M['coral'], edge_bev=0.03, collection=col, lm='furn'))
    parts.append(rounded_slab(f'{name}_cushion', 0.56, 0.56, 0.1, 0.18, (0, -0.06, 0.38), M['coral'], edge_bev=0.04, collection=col, lm='furn'))
    for sx in (-1, 1):
        for sy in (-1, 1): parts.append(cyl(f'{name}_foot{sx}{sy}', 0.02, 0.08, (sx * 0.24, sy * 0.22, 0.04), M['chrome'], seg=10, collection=col, lm='furn'))
    for o in parts: place(o, _frame(p, f))


def sofa(M, col):
    """The gold damask sofa against the west wall: a deep frame, rolled arms, three seat cushions, a high back with
    three cushions and two bolsters, on short dark feet; the coffee table before it with a book and a mug."""
    p, f = SOFA, (1, 0); L, Dp = 2.1, 0.92; m = M['damask']; parts = []; add = lambda o: (parts.append(o), o)[1]
    add(rounded_slab('sofa_base', L, Dp, 0.3, 0.05, (0, 0, 0.22), m, collection=col, lm='furn'))
    add(rounded_slab('sofa_back', L - 0.1, 0.22, 0.5, 0.06, (0, Dp / 2 - 0.11, 0.6), m, collection=col, lm='furn'))
    for s in (-1, 1):
        add(rounded_slab(f'sofa_arm{s}', 0.2, Dp, 0.36, 0.06, (s * (L / 2 - 0.1), 0, 0.42), m, collection=col, lm='furn'))
        add(cyl(f'sofa_roll{s}', 0.11, Dp - 0.04, (s * (L / 2 - 0.09), 0, 0.62), m, rot=(math.pi / 2, 0, 0), seg=24, collection=col, lm='furn'))
        for sy in (-1, 1): add(lathe(f'sofa_foot{s}{sy}', [(0.0, 0.0), (0.028, 0.0), (0.035, 0.05), (0.03, 0.07), (0.0, 0.07)], M['walnut'], loc=(s * (L / 2 - 0.08), sy * (Dp / 2 - 0.08), 0.0), seg=12, collection=col, lm='furn'))
    for k in range(3):
        x = (k - 1) * (L - 0.42) / 3
        add(rounded_slab(f'sofa_seat{k}', (L - 0.42) / 3 - 0.01, Dp - 0.26, 0.15, 0.06, (x, -0.08, 0.44), m, collection=col, lm='furn'))
        bc = add(rounded_slab(f'sofa_cushion{k}', (L - 0.42) / 3 - 0.02, 0.2, 0.44, 0.08, (x, Dp / 2 - 0.27, 0.72), m, collection=col, lm='furn'))
        bc.rotation_euler.x = math.radians(-12)
    for o in parts: place(o, _frame(p, f))
    t = Vector((SOFA.x + 0.95, SOFA.y, 0.0))
    box('coffee_top', (0.62, 1.15, 0.05), t + Vector((0, 0, 0.42)), M['walnut'], bev=0.01, collection=col, lm='furn')
    box('coffee_apron', (0.56, 1.09, 0.08), t + Vector((0, 0, 0.36)), M['walnut'], bev=0.006, collection=col, lm='furn')
    for sx in (-1, 1):
        for sy in (-1, 1): lathe(f'coffee_leg{sx}{sy}', [(0.0, 0.0), (0.022, 0.0), (0.03, 0.1), (0.022, 0.2), (0.03, 0.3), (0.0, 0.32)], M['walnut'], loc=t + Vector((sx * 0.25, sy * 0.5, 0.0)), seg=12, collection=col, lm='furn')
    box('coffee_book', (0.26, 0.34, 0.06), t + Vector((0.02, -0.08, 0.475)), M['oxblood'], rot=(0, 0, 0.1), bev=0.005, collection=col, lm='furn')
    box('coffee_book2', (0.22, 0.3, 0.04), t + Vector((0.04, -0.06, 0.525)), M['walnut'], rot=(0, 0, -0.06), bev=0.004, collection=col, lm='furn')
    box('coffee_pad', (0.2, 0.3, 0.008), t + Vector((0.0, 0.3, 0.449)), M['folder'], rot=(0, 0, 0.3), bev=0, collection=col, lm='furn')
    lathe('coffee_mug', [(0.0, 0.0), (0.04, 0.0), (0.042, 0.1), (0.038, 0.1), (0.0, 0.01)], M['mug'], loc=t + Vector((0.1, 0.12, 0.445)), seg=18, collection=col, lm='furn')
    tub_chair('tub0', Vector((t.x + 0.95, t.y - 0.05, 0)), (-1, 0.05), M, col)
    top = side_table('sofa_table', (LEFT + 0.25, SOFA.y + 1.32, 0.0), M, col)
    scales('sofa_scales', top + Vector((0.05, 0.12, 0)), M, col)
    return column_lamp('sofa_lamp', top + Vector((0.0, -0.08, 0)), M, col)


def column_lamp(name, p, M, col, shade_r=0.17):
    """A brass column table lamp with a pleated cream shade; returns its bulb."""
    lathe(f'{name}_body', [(0.0, 0.0), (0.075, 0.0), (0.075, 0.02), (0.05, 0.04), (0.03, 0.08), (0.028, 0.34), (0.04, 0.36), (0.02, 0.4), (0.008, 0.46), (0.0, 0.46)], M['brass'], loc=p, seg=24, collection=col, lm='furn')
    sh = lathe(f'{name}_shade', [(shade_r, 0.0), (shade_r * 0.62, 0.24), (shade_r * 0.6, 0.24), (shade_r * 0.98, 0.0)], M['shade'], loc=Vector(p) + Vector((0, 0, 0.4)), seg=32, collection=col, lm='furn')
    return Vector(p) + Vector((0, 0, 0.5))


def side_table(name, p, M, col, size=(0.46, 0.4, 0.58)):
    """A cream painted side table with a drawer and brass pulls."""
    w, d, h = size
    box(f'{name}_top', (w, d, 0.03), Vector(p) + Vector((0, 0, h - 0.015)), M['cream'], bev=0.006, collection=col, lm='furn')
    box(f'{name}_case', (w - 0.03, d - 0.03, h - 0.12), Vector(p) + Vector((0, 0, 0.09 + (h - 0.12) / 2)), M['cream'], bev=0.006, collection=col, lm='furn')
    for sx in (-1, 1):
        for sy in (-1, 1): box(f'{name}_leg{sx}{sy}', (0.035, 0.035, 0.1), Vector(p) + Vector((sx * (w / 2 - 0.03), sy * (d / 2 - 0.03), 0.05)), M['cream'], bev=0.006, collection=col, lm='furn')
    return Vector(p) + Vector((0, 0, h))


def scales(name, p, M, col):
    """Brass scales of justice: a column, a beam, two hanging pans."""
    p = Vector(p)
    cyl(f'{name}_foot', 0.05, 0.015, p + Vector((0, 0, 0.0075)), M['brass'], seg=20, collection=col, lm='furn')
    cyl(f'{name}_post', 0.007, 0.32, p + Vector((0, 0, 0.17)), M['brass'], seg=8, collection=col, lm='furn')
    cyl(f'{name}_beam', 0.005, 0.26, p + Vector((0, 0, 0.32)), M['brass'], rot=(0, math.pi / 2, 0), seg=8, collection=col, lm='furn')
    for s in (-1, 1):
        for k in range(3):
            a = k * 2 * math.pi / 3
            tube(f'{name}_chain{s}{k}', [p + Vector((s * 0.13, 0, 0.32)), p + Vector((s * 0.13 + 0.035 * math.cos(a), 0.035 * math.sin(a), 0.2))], 0.0012, M['brass'], col, seg=4, lm='furn')
        lathe(f'{name}_pan{s}', [(0.0, 0.0), (0.045, 0.012), (0.05, 0.02), (0.0, 0.006)], M['brass'], loc=p + Vector((s * 0.13, 0, 0.185)), seg=20, collection=col, lm='furn')


def library(M, col):
    """The law library: a tall walnut bookcase against the north wall left of the bay, six shelves of red and green
    buckram reporters; white file boxes stacked beside it; the amber wall sconce; the diploma; a second tub chair."""
    x0, x1 = LEFT + 0.04, BAY[0][0] - 0.5; dpt = 0.36; h = 2.45; parts = []; rnd = random.Random(7)
    add = lambda o: (parts.append(o), o)[1]
    w = x1 - x0; cx = (x0 + x1) / 2; y = YN - dpt / 2
    add(box('lib_back', (w, 0.02, h), (cx, YN - 0.01, h / 2), M['walnut'], bev=0, collection=col, lm='furn'))
    for s in (-1, 1): add(box(f'lib_side{s}', (0.03, dpt, h), (cx + s * (w / 2 - 0.015), y, h / 2), M['walnut'], bev=0.003, collection=col, lm='furn'))
    add(box('lib_crown', (w + 0.06, dpt + 0.04, 0.06), (cx, y - 0.02, h - 0.03), M['walnut'], bev=0.008, collection=col, lm='furn'))
    add(box('lib_plinth', (w, dpt, 0.1), (cx, y, 0.05), M['walnut'], bev=0.004, collection=col, lm='furn'))
    shelves = [0.1 + k * (h - 0.16) / 6 for k in range(7)]
    for k, zs in enumerate(shelves): add(box(f'lib_shelf{k}', (w - 0.06, dpt - 0.02, 0.025), (cx, y, zs), M['walnut'], bev=0.002, collection=col, lm='furn'))
    for k, zs in enumerate(shelves[:-1]):
        o0 = len(parts)
        spine_row(f'lib_row{k}', w - 0.1, zs + 0.0125, 0.3, dpt - 0.04, M, col, parts, rnd, x_at=0.0)
        for o in parts[o0:]: o.location = (cx, YN - dpt + 0.02 + (dpt - 0.04) / 2, 0)
    # file boxes stacked at the bookcase's end, against the west wall
    for k in range(5):
        b = uv_rect(box(f'filebox{k}', (0.32, 0.4, 0.26), (LEFT + 0.2, YN - 0.62 - 0.42 * (k // 3), 0.13 + 0.26 * (k % 3)), M['filebox'], rot=(0, 0, math.pi / 2), bev=0.004, collection=col, lm='furn'), 'x')
    # the sconce: an amber glass half-cylinder on a brass plate, on the west wall
    sc = Vector((LEFT, 0.25, 1.72))
    box('sconce_plate', (0.02, 0.1, 0.2), sc + Vector((0.01, 0, 0)), M['brass'], bev=0.004, collection=col, lm='furn')
    g = cyl('sconce_glass', 0.07, 0.24, sc + Vector((0.06, 0, 0)), M['sconce'], seg=20, collection=col)
    g.scale = (0.7, 1.0, 1.0)
    # the diploma in a gilt frame; a framed landscape over the sofa
    picture('diploma', 'diploma', (LEFT, -0.35, 1.55), (0.46, 0.38), (1, 0), M, col, frame=0.03)
    picture('landscape', 'landscape', (LEFT, SOFA.y, 1.6), (1.0, 0.7), (1, 0), M, col, frame=0.045)
    tub_chair('tub1', Vector((LEFT + 0.95, 0.5, 0)), (1, -0.5), M, col)
    return sc + Vector((0.08, 0, 0))


def door(M, col):
    """The office door: dark walnut, six raised panels a side, a brass knob; standing open into the office."""
    d0, d1, dh = DOOR; w = d1 - d0 - 0.006; h = dh - 0.008; t = 0.045; parts = []; add = lambda o: (parts.append(o), o)[1]
    add(box('door_slab', (w, t, h), (w / 2, 0, h / 2), M['walnut'], bev=0.004, collection=col, lm='furn'))
    for s in (-1, 1):
        for k, (z0, z1) in enumerate(((0.12, 0.72), (0.84, 1.44), (1.56, h - 0.1))):
            for j, (x0, x1) in enumerate(((0.1, w / 2 - 0.04), (w / 2 + 0.04, w - 0.1))):
                add(box(f'door_panel{s}{k}{j}', (x1 - x0, 0.012, z1 - z0), ((x0 + x1) / 2, s * (t / 2 + 0.004), (z0 + z1) / 2), M['walnut'], bev=0.016, seg=3, collection=col, lm='furn'))
        add(lathe(f'door_knob{s}', [(0.0, 0.0), (0.03, 0.0), (0.03, 0.006), (0.01, 0.012), (0.012, 0.05), (0.028, 0.06), (0.028, 0.075), (0.0, 0.08)], M['brass'], loc=(w - 0.07, s * (t / 2 + 0.002), 0.98), seg=16, collection=col, lm='furn')).rotation_euler = (-s * math.pi / 2, 0, 0)
    for z in (0.25, 1.05, h - 0.25): add(cyl(f'door_hinge{z}', 0.008, 0.1, (0.0, 0.0, z), M['brass'], seg=10, bev=0, collection=col, lm='furn'))
    # built closed along +x from its hinge (at y0, the office side), swung into the office and round toward the front
    F = Matrix.Translation((XP - 0.03, d0 + 0.003, 0.004)) @ Matrix.Rotation(math.pi / 2 + DOOR_OPEN, 4, 'Z')
    for o in parts: place(o, F)


def office_things(M, col):
    """By the door: the cream side table with the column lamp; the palm in its brass planter in the corner by the bay;
    framed photographs of Saul with people and a framed document on the partition; Lady Justice. Returns the bulb."""
    top = side_table('door_table', (XP - 0.3, YN - 0.24, 0.0), M, col)
    bulb = column_lamp('door_lamp', top, M, col)
    planter = Vector((BAY[-1][0] + 0.42, YN - 0.32, 0))
    lathe('planter', [(0.0, 0.0), (0.2, 0.0), (0.25, 0.08), (0.29, 0.42), (0.31, 0.47), (0.28, 0.49), (0.0, 0.49)], M['brass'], loc=planter, seg=32, collection=col, lm='furn')
    root, ms = cine.import_gltf(PH('potted_plant_02'), loc=tuple(planter + Vector((0, 0, 0.05))), rot=(0, 0, 0.6), scale=2.1, collection=col, lm='furn')
    pots = [o for o in ms if any(sl.material and sl.material.name.lower().endswith('_pot') for sl in o.material_slots)]
    for o in ms:
        if o in pots: continue
        for sl in o.material_slots: sl.material = M['plant']                 # plain colour and relief: the exporter cannot
    for o in pots: bpy.data.objects.remove(o, do_unlink=True)                # write the leaves' packed roughness; its own pot
                                                                             # is hidden in the brass planter
    for k, (y, z) in enumerate(((0.3, 1.78), (0.3, 1.45), (0.3, 1.12))):
        picture(f'photo{k}', f'photo{k}', (XP, y, z), (0.26, 0.22), (-1, 0), M, col, frame=0.02)
    picture('framed_doc', 'diploma', (XP - 0.3, YN, 1.55), (0.3, 0.38), (0, -1), M, col, frame=0.02)
    return bulb


# ---------------------------------------------------------------- the waiting room and the booth
def storefront(M, col):
    """The shop window and its glass door in the waiting room's back wall: bronze anodised frames, white mini-blinds
    with their slats half open over the window, the parking lot beyond (seen only by the camera; the sun passes)."""
    x0, x1, s0, s1 = STORE; e0, e1, eh = ENTRY; y = BACK
    for k, (a, b, z0, z1) in enumerate(((x0, x1, s0, s1), (e0, e1, 0.0, eh))):
        for s, xx in ((-1, a), (1, b)): box(f'store_jamb{k}{s}', (0.05, T, z1 - z0), (xx - s * 0.025, y + T / 2, (z0 + z1) / 2), M['alu'], bev=0.003, collection=col, lm='furn')
        box(f'store_head{k}', (b - a, T, 0.05), ((a + b) / 2, y + T / 2, z1 - 0.025), M['alu'], bev=0.003, collection=col, lm='furn')
        box(f'store_sill{k}', (b - a, T, 0.05), ((a + b) / 2, y + T / 2, z0 + 0.025), M['alu'], bev=0.003, collection=col, lm='furn')
        v = uv_rect(box(f'store_view{k}', (b - a, 0.006, z1 - z0), ((a + b) / 2, D / 2 - 0.004, (z0 + z1) / 2), M['view'], bev=0, collection=col))
        if k == 1: uv_window(v, 0.78, 0.0, 0.98, 1.0)
        else: uv_window(v, 0.0, 0.08, 0.76, 0.92)
        for attr in ('visible_shadow', 'visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter'): setattr(v, attr, False)
    box('store_mullion', (0.04, T, s1 - s0), ((x0 + x1) / 2, y + T / 2, (s0 + s1) / 2), M['alu'], bev=0.003, collection=col, lm='furn')
    box('door_pushbar', (e1 - e0 - 0.16, 0.03, 0.04), ((e0 + e1) / 2, y - 0.04, 1.02), M['alu'], bev=0.006, collection=col, lm='furn')
    box('door_rail', (e1 - e0, 0.03, 0.12), ((e0 + e1) / 2, y + 0.02, 0.06), M['alu'], bev=0.004, collection=col, lm='furn')
    # the mini-blinds: 25 mm white slats tilted half open, from the head down, the cord's tilt wand
    top, bottom = s1 - 0.06, s0 + 0.06; n = int((top - bottom) / 0.022)
    bm = bmesh.new()
    for k in range(n):
        z = top - k * 0.022
        r = bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(((x0 + x1) / 2, y - 0.04, z)) @ Matrix.Rotation(math.radians(42), 4, 'X') @ Matrix.Diagonal((x1 - x0 - 0.04, 0.025, 0.0016, 1)))
    sl = cine._mesh_obj('store_slats', bm, M['blind'], col, smooth=False); sl['lm'] = 'furn'
    box('store_blind_head', (x1 - x0 - 0.02, 0.05, 0.04), ((x0 + x1) / 2, y - 0.04, s1 - 0.03), M['blind'], bev=0.004, collection=col, lm='furn')
    box('store_blind_foot', (x1 - x0 - 0.04, 0.03, 0.012), ((x0 + x1) / 2, y - 0.04, bottom - 0.02), M['blind'], bev=0.002, collection=col, lm='furn')
    cyl('store_wand', 0.004, 0.7, (x1 - 0.06, y - 0.07, s1 - 0.4), M['blind'], seg=6, collection=col, lm='furn')


def waiting(M, col):
    """The waiting room: three burgundy vinyl chairs on chrome frames under the shop window, a side table with
    magazines and a lamp at the end of the row; Francesca's window in the partition (its sliding glass and counter);
    the brass plaque by the office door. Returns the lamp's bulb."""
    y = BACK - 0.36
    for k in range(2):
        x = 2.74 + 0.56 * k; parts = []
        parts.append(rounded_slab(f'wchair{k}_seat', 0.48, 0.46, 0.08, 0.04, (0, 0, 0.44), M['vinyl'], edge_bev=0.02, collection=col, lm='furn'))
        bk = rounded_slab(f'wchair{k}_back', 0.48, 0.06, 0.4, 0.04, (0, 0.21, 0.72), M['vinyl'], edge_bev=0.02, collection=col, lm='furn'); bk.rotation_euler.x = math.radians(-8); parts.append(bk)
        for s in (-1, 1):
            parts.append(tube(f'wchair{k}_frame{s}', [(s * 0.25, -0.22, 0.0), (s * 0.25, -0.2, 0.4), (s * 0.25, -0.22, 0.62), (s * 0.25, 0.16, 0.62), (s * 0.25, 0.22, 0.0)], 0.011, M['chrome'], col, seg=8, lm='furn'))
        for o in parts: place(o, Matrix.Translation((x, y, 0)))
    st = side_table('wait_table', (XW + 0.25, BACK - 0.25, 0.0), M, col, size=(0.42, 0.42, 0.56))
    bulb = column_lamp('wait_lamp', st + Vector((0.04, 0.06, 0)), M, col, shade_r=0.15)
    for j in range(3): uv_rect(box(f'wmag{j}', (0.21, 0.28, 0.004), st + Vector((-0.05 + 0.02 * j, -0.08, 0.003 + 0.004 * j)), M['magazine'], rot=(0, 0, 0.2 * j - 0.25), bev=0, collection=col, lm='furn'), 'z')
    # Francesca's window: an aluminium frame round two sliding panes, a laminate counter ledge on the waiting room's side
    r0, r1, rs, rh = RECEPTION
    for s, yy in ((-1, r0), (1, r1)): box(f'rec_jamb{s}', (PT + 0.02, 0.04, rh - rs), (XP + PT / 2, yy - s * 0.02, (rs + rh) / 2), M['alu'], bev=0.003, collection=col, lm='furn')
    box('rec_head', (PT + 0.02, r1 - r0, 0.04), (XP + PT / 2, (r0 + r1) / 2, rh - 0.02), M['alu'], bev=0.003, collection=col, lm='furn')
    box('rec_counter', (0.26, r1 - r0 + 0.16, 0.035), (XW + 0.1, (r0 + r1) / 2, rs + 0.0175), M['oak'], bev=0.006, collection=col, lm='furn')
    for k, (a, b, o) in enumerate(((r0 + 0.02, (r0 + r1) / 2 + 0.03, 0.035), ((r0 + r1) / 2 - 0.03, r1 - 0.02, 0.065))):
        box(f'rec_sash{k}', (0.02, b - a, rh - rs - 0.06), (XP + o, (a + b) / 2, (rs + rh) / 2), M['alu'], bev=0.002, collection=col, lm='furn')
    plaque = uv_rect(box('plaque', (0.012, 0.36, 0.18), (XW + 0.006, DOOR[1] + 0.34, 1.5), M['plaque'], bev=0.002, collection=col, lm='furn'), 'x')
    return bulb


def booth(M, col):
    """Francesca's booth behind the window: a desk along the partition with a beige computer, its monitor, a phone and
    papers, her chair, a filing cabinet, a desk lamp. Returns the lamp's bulb."""
    x1 = XP - 0.01; zt = 0.74
    box('booth_desk', (0.62, 1.3, 0.035), (x1 - 0.31, (RECEPTION[0] + RECEPTION[1]) / 2, zt - 0.0175), M['oak'], bev=0.004, collection=col, lm='furn')
    for s in (-1, 1): box(f'booth_desk_side{s}', (0.6, 0.03, zt - 0.035), (x1 - 0.31, (RECEPTION[0] + RECEPTION[1]) / 2 + s * 0.62, (zt - 0.035) / 2), M['oak'], bev=0.003, collection=col, lm='furn')
    m = Vector((x1 - 0.3, RECEPTION[0] + 0.05, zt))
    box('booth_monitor', (0.3, 0.32, 0.3), m + Vector((0, 0, 0.17)), M['beige'], bev=0.015, collection=col, lm='furn')
    s_ = uv_rect(box('booth_screen', (0.004, 0.25, 0.19), m + Vector((-0.152, 0, 0.19)), M['monitor'], bev=0, collection=col, lm='furn'), 'x')
    box('booth_keys', (0.16, 0.42, 0.025), m + Vector((-0.2, 0.25, 0.0125)), M['beige'], bev=0.005, collection=col, lm='furn')
    box('booth_phone', (0.18, 0.2, 0.06), (x1 - 0.2, RECEPTION[1] - 0.2, zt + 0.03), M['black'], bev=0.012, collection=col, lm='furn')
    for k in range(3): box(f'booth_paper{k}', (0.21, 0.29, 0.003), (x1 - 0.32, RECEPTION[1] - 0.45 + 0.02 * k, zt + 0.002 + 0.003 * k), M['paper'], rot=(0, 0, 0.1 * k), bev=0, collection=col, lm='furn')
    cx, cy = x1 - 0.85, (RECEPTION[0] + RECEPTION[1]) / 2
    rounded_slab('booth_chair_seat', 0.46, 0.44, 0.07, 0.06, (cx, cy, 0.47), M['black'], collection=col, lm='furn')
    bk = rounded_slab('booth_chair_back', 0.06, 0.42, 0.45, 0.025, (cx - 0.22, cy, 0.8), M['black'], collection=col, lm='furn')
    cyl('booth_chair_col', 0.022, 0.36, (cx, cy, 0.25), M['chrome'], seg=12, collection=col, lm='furn')
    box('booth_cabinet', (0.46, 0.62, 1.3), (BOOTH_X + 0.38, BACK - 0.35, 0.65), M['beige'], bev=0.006, collection=col, lm='furn')
    for k in range(4): box(f'booth_drawer{k}', (0.004, 0.5, 0.26), (BOOTH_X + 0.61, BACK - 0.35, 0.18 + 0.31 * k), M['beige'], bev=0.003, collection=col, lm='furn')
    return Vector((x1 - 0.2, RECEPTION[1] - 0.1, zt + 0.35))


# ---------------------------------------------------------------- the cut
def section(objs, M):
    """Every face the cut passes through, flat and dark: the walls' and the solid's tops at the ceiling."""
    for ob in objs:
        if not ob.name.startswith(('solid_', 'wall_', 'back_wall', 'left_wall', 'kerb')): continue
        me = ob.data
        if M['section'].name not in [m.name for m in me.materials if m]: me.materials.append(M['section'])
        k = [m.name if m else '' for m in me.materials].index(M['section'].name)
        for f in me.polygons:
            c = sum((me.vertices[i].co for i in f.vertices), Vector()) / len(f.vertices)
            if f.normal.z > 0.9 and (abs(c.z - RH) < 0.004 or abs(c.z - H) < 0.004): f.material_index = k


# ---------------------------------------------------------------- light
WARM = (1.0, 0.76, 0.5)                    # tungsten
SUN = (1.0, 0.92, 0.8)                     # Albuquerque afternoon


def lights(portholes, desk_bulb, door_bulb, sofa_bulb, sconce, wait_bulb, booth_bulb):
    """The office's recessed cans (dim), the five round windows lit from behind, the banker's lamp, the column lamps,
    the amber sconce; the sun on the shop window, the waiting room's cans, Francesca's lamp. Returns the lights."""
    out = []
    def light(name, kind, loc, energy, colour, **kw):
        ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = colour
        for k, v in kw.items(): setattr(ld, k, v)
        ob = cine.link(bpy.data.objects.new(name, ld)); ob.location = loc; out.append(ob)
        if kind in ('AREA', 'SPOT'): ob.visible_camera = False; ob.visible_glossy = False
        return ob
    def aim(ob, d): ob.rotation_euler = Vector(d).to_track_quat('-Z', 'Y').to_euler()
    for k, (x, y) in enumerate(((-3.6, -2.2), (-1.4, -2.2), (0.8, -2.2), (-3.6, 0.2), (-1.4, 0.4), (0.8, 0.2), (-1.4, 2.6))):
        aim(light(f'can{k}', 'SPOT', (x, y, RH - 0.03), 120.0, WARM, spot_size=math.radians(75), spot_blend=0.6, shadow_soft_size=0.04), (0, 0, -1))
    for k, (c, n, f, L) in enumerate(portholes):
        aim(light(f'porthole{k}', 'AREA', tuple(c + n * 0.03), 26.0, (1.0, 0.9, 0.74), shape='DISK', size=0.38), n)
        # a wash over the face from the ceiling, a little in front of it: the paper glows gold as on the set
        p = f.at(L / 2, 0.55, RH - 0.05)
        aim(light(f'bay_wash{k}', 'SPOT', tuple(p), 70.0 * min(1.0, L / 1.3), WARM, spot_size=math.radians(70), spot_blend=0.8, shadow_soft_size=0.05),
            tuple(f.at(L / 2, 0.0, 1.35) - p))
    light('banker_lamp', 'POINT', desk_bulb, 9.0, (1.0, 0.7, 0.32), shadow_soft_size=0.03)
    light('door_lamp', 'POINT', door_bulb, 30.0, WARM, shadow_soft_size=0.06)
    light('sofa_lamp', 'POINT', sofa_bulb, 30.0, WARM, shadow_soft_size=0.06)
    light('sconce', 'POINT', sconce, 12.0, (1.0, 0.62, 0.3), shadow_soft_size=0.04)
    x0, x1, s0, s1 = STORE
    aim(light('sun_window', 'AREA', ((x0 + x1) / 2, BACK + 0.6, (s0 + s1) / 2 + 0.3), 520.0, SUN, shape='RECTANGLE', size=x1 - x0, size_y=s1 - s0), (0.0, -1.0, -0.45))
    e0, e1, eh = ENTRY
    aim(light('sun_door', 'AREA', ((e0 + e1) / 2, BACK + 0.6, eh / 2 + 0.3), 320.0, SUN, shape='RECTANGLE', size=e1 - e0, size_y=eh), (0.0, -1.0, -0.45))
    for k, y in enumerate((-1.6, 1.4)):
        aim(light(f'wait_can{k}', 'SPOT', (3.3, y, RH - 0.03), 60.0, WARM, spot_size=math.radians(75), spot_blend=0.6, shadow_soft_size=0.04), (0, 0, -1))
    light('wait_lamp', 'POINT', wait_bulb, 25.0, WARM, shadow_soft_size=0.06)
    light('booth_lamp', 'POINT', booth_bulb, 12.0, WARM, shadow_soft_size=0.04)
    aim(light('booth_can', 'SPOT', (1.2, 2.9, RH - 0.03), 35.0, WARM, spot_size=math.radians(80), spot_blend=0.6), (0, 0, -1))
    return out
