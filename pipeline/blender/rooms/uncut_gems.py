# Uncut Gems · KMH, Howard Ratner's jewellery showroom on 47th Street, the night of game seven. A windowless room
# lit by LEDs: honey oak panelling on the back wall hung with framed snapshots of the store's famous customers, the
# game on a big TV on its arm by the corner; along the left wall the pale pink display cases with their gabled
# tops and silver 'KMH' letters, lilac light inside on blue velvet busts, necklaces and the hanging chains; the
# glass showcase counter mid-room, its blue LED lines, chrome-armed stools before it; the dark speckled granite
# floor; chrome tracks of cone lights overhead, a blue neon line round the top of the walls. In the back right
# corner the security vestibule (the mantrap): a glass box in chrome frames, its inner door toward the showroom,
# the building's wooden door at its back, its pale mint walls lit cold; plants and a black leather armchair by it.
# Built at its true size (the showroom fits the module as it is).
import math, os, random
import bpy, bmesh
from mathutils import Vector, Matrix
import cine
from cine import box, cyl, material, lathe, rounded_slab
from rooms.seinfeld import uv_rect, tube, circle
from rooms.lost import screen

W, D = 9.6, 7.6
T = 0.14
LEFT, BACK, RIGHT, FRONT = -W / 2 + T, D / 2 - T, W / 2 - T, -D / 2 + T
RH = 3.0                                   # the module's top: the cut (the drop ceiling is a phantom just above)
KH = 0.22
TEX = os.path.join(cine.OUT, 'textures', 'uncut-gems')
tx = lambda n: os.path.join(TEX, n)
PH = os.path.join(cine.CACHE, 'polyhaven')

# the plan (true metres; after the drawing: the oak photo wall at the back, the pink cases on the left wall, the
# counter mid-left, the vestibule in the back right corner)
OAK = 0.022                                # the panelling's thickness
MX0, MY0 = 2.50, 0.62                      # the vestibule: its left glass face (x) and its front glass face (y)
VDOOR = (2.80, 3.72)                       # the inner door in the front face (x), hinged at its left jamb, swinging out
VDOOR_H = 2.18
HEAD = 2.40                                # the glass's head: a white header above it to the ceiling
ODOOR = (3.50, 4.40)                       # the building's door in the back wall, inside the vestibule
CASES_Y = (-2.95, 2.32)                    # the pink cases along the left wall
CASE_D = 0.50
N_CASES = 4
COUNTER_X = (-2.80, -1.85)                 # the showcase counter
COUNTER_Y = (-2.28, 1.57)
COUNTER_H = 1.02
BASE_H = 0.82
STATION = (-0.78, -0.22)                   # the counter's solid top (y): the buzzer, the phone, the mirror
BUZZER = Vector((-1.93, -0.32, COUNTER_H + 0.012))
PHONE = Vector((-2.02, -0.62, COUNTER_H + 0.004))   # Howard's phone where it lies on the counter
STOOLS = [Vector((-1.40, -0.50)), Vector((-1.40, 0.75)), Vector((-1.40, -1.75))]
STOOL_SEAT = 0.66
TV = Vector((-3.55, BACK - 0.62, 2.02))    # the screen's centre, on its arm out from the wall
TV_F = Vector((0.52, -0.85, 0.0)).normalized()
TV_W, TV_H = 1.04, 0.60
CCTV = Vector((2.02, BACK - 0.16, 2.42))   # the camera monitor high on the oak wall by the vestibule
ARMCHAIR = (Vector((1.62, 1.75)), Vector((-0.6, -0.8)).normalized())
PLANTS = [Vector((2.18, 0.30)), Vector((4.30, 0.28))]


# ---------------------------------------------------------------- materials
def mats():
    M = {}
    M['floor'] = material('ug_granite', rough=0.32, maps={'color': tx('floor_color.jpg'), 'normal': tx('floor_normal.jpg')}, scale=2.4, normal_strength=0.3, coat=0.1, coat_rough=0.2)
    M['oak'] = material('ug_oak', rough=0.32, maps={'color': tx('oak_color.jpg'), 'normal': tx('oak_normal.jpg')}, scale=1.6, normal_strength=0.25, coat=0.5, coat_rough=0.12)
    M['oak_groove'] = material('ug_oak_groove', (0.09, 0.05, 0.025), rough=0.6)
    M['mint'] = material('ug_mint', rough=0.75, maps={'color': tx('mint_color.jpg'), 'normal': tx('plaster_normal.jpg')}, scale=2.0, normal_strength=0.2)
    M['plaster'] = material('ug_plaster', rough=0.75, maps={'color': tx('plaster_color.jpg'), 'normal': tx('plaster_normal.jpg')}, scale=2.0, normal_strength=0.2)
    M['pink'] = material('ug_pink_lacquer', (0.74, 0.44, 0.53), rough=0.3, coat=0.5, coat_rough=0.12)
    M['lilac'] = material('ug_lilac_back', rough=0.7, maps={'color': tx('chains_color.jpg')}, scale=1.0)
    M['lilac_lit'] = material('ug_lilac_led', (0.8, 0.66, 0.92), rough=0.5, emission=(0.86, 0.68, 1.0), emission_strength=5.0)
    M['shelf'] = material('ug_shelf_glass', (0.78, 0.74, 0.84), rough=0.08, coat=1.0)
    M['kmh'] = material('ug_kmh', rough=0.3, maps={'color': tx('kmh_color.jpg')}, scale=1.0, coat=0.5)
    M['cream'] = material('ug_cream_lacquer', (0.82, 0.79, 0.73), rough=0.28, coat=0.5, coat_rough=0.1)
    M['chrome'] = material('ug_chrome', (0.85, 0.85, 0.86), rough=0.12, metal=1.0)
    M['brushed'] = material('ug_brushed_steel', (0.62, 0.62, 0.62), rough=0.35, metal=1.0)
    M['blue_led'] = material('ug_blue_led', (0.2, 0.5, 1.0), rough=0.4, emission=(0.12, 0.45, 1.0), emission_strength=2.2)
    M['velvet'] = material('ug_velvet_blue', rough=0.9, maps={'color': tx('velvet_color.jpg')}, scale=0.4, sheen=0.5, sheen_tint=(0.4, 0.5, 0.6))
    M['tray'] = material('ug_velvet_navy', rough=0.9, maps={'color': tx('tray_color.jpg')}, scale=0.4, sheen=0.5, sheen_tint=(0.3, 0.35, 0.5))
    M['gold'] = material('ug_gold', (0.95, 0.72, 0.32), rough=0.18, metal=1.0)
    M['silver'] = material('ug_silver', (0.92, 0.92, 0.95), rough=0.1, metal=1.0)
    M['pearl'] = material('ug_pearl', (0.92, 0.9, 0.85), rough=0.2, coat=1.0)
    M['leather'] = material('ug_black_leather', rough=0.42, maps={'color': tx('leather_color.jpg'), 'normal': tx('leather_normal.jpg')}, scale=0.5, normal_strength=0.4, coat=0.25)
    M['photos'] = material('ug_photos', rough=0.3, maps={'color': tx('photos_color.jpg')}, scale=1.0, coat=0.6)
    M['frame_gold'] = material('ug_frame_gold', (0.7, 0.52, 0.22), rough=0.3, metal=0.9)
    M['frame_black'] = material('ug_frame_black', (0.02, 0.02, 0.02), rough=0.35, coat=0.4)
    M['black'] = material('ug_black_plastic', (0.012, 0.012, 0.014), rough=0.3, coat=0.3)
    M['screen'] = material('ug_screen', (0.01, 0.012, 0.015), rough=0.1)
    M['white'] = material('ug_white_plastic', (0.84, 0.84, 0.82), rough=0.4)
    M['door_wood'] = material('ug_door_oak', rough=0.4, maps={'color': tx('oak_color.jpg'), 'normal': tx('oak_normal.jpg')}, scale=1.2, normal_strength=0.2, coat=0.3)
    M['frost'] = material('ug_frost', (0.86, 0.9, 0.9), rough=0.6)
    M['sign'] = material('ug_sign', rough=0.5, maps={'color': tx('sign_color.jpg')}, scale=1.0)
    M['soil'] = material('ug_soil', (0.05, 0.035, 0.025), rough=0.95)
    M['petal'] = material('ug_orchid', (0.92, 0.9, 0.9), rough=0.5, sheen=0.3, sheen_tint=(0.5, 0.5, 0.5))
    M['stem'] = material('ug_stem', (0.12, 0.2, 0.06), rough=0.6)
    M['kerb'] = material('ug_kerb', (0.1, 0.08, 0.06), rough=0.9)
    M['section'] = material('section', (0.03, 0.028, 0.026), rough=0.92)
    M['phantom'] = material('ug_phantom_ceiling', (0.78, 0.78, 0.8), rough=0.9)
    M['mirror_ceiling'] = material('ug_phantom_mirror', (0.5, 0.5, 0.55), rough=0.15, metal=0.8)
    return M


def _tag(objs, **props):
    for o in objs:
        for k, v in props.items(): o[k] = v
    return objs


def prism(name, pts, z0, z1, mat, col, lm='furn', bev=0.004):
    """A vertical prism over a 2D outline (counter-clockwise), z0..z1."""
    bm = bmesh.new()
    a = [bm.verts.new((x, y, z0)) for x, y in pts]; b = [bm.verts.new((x, y, z1)) for x, y in pts]
    bm.faces.new(list(reversed(a))); bm.faces.new(b)
    n = len(pts)
    for i in range(n): bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    ob = cine._mesh_obj(name, bm, mat, col, smooth=False); ob['lm'] = lm
    if bev: cine.bevel(ob, bev, 2, 40)
    return ob


# ---------------------------------------------------------------- the shell
def shell(M, arch, phantom):
    """The granite floor; the back wall (oak to the vestibule, its mint inside it) and the left wall (oak) full
    height; the front and right walls cut to kerbs; the vestibule's floor; skirting; the blue neon line at the top of
    the showroom's walls; the phantoms: the drop ceiling (a mirrored coffer over the middle), the missing walls, the
    vestibule's ceiling."""
    box('subfloor', (W, D, 0.02), (0, 0, -0.035), M['kerb'], bev=0, collection=arch, lm='arch')
    fl = box('floor_room', (RIGHT - LEFT, BACK - FRONT, 0.03), ((LEFT + RIGHT) / 2, (FRONT + BACK) / 2, -0.015), M['floor'], bev=0, collection=arch, lm='arch')
    cine.world_uv(fl, 1.0)
    # the walls (the module's own), their room faces clad
    box('back_wall', (W, T, RH), (0, D / 2 - T / 2, RH / 2), M['plaster'], bev=0, collection=arch, lm='arch')
    box('left_wall', (T, D - T, RH), (-W / 2 + T / 2, -T / 2, RH / 2), M['plaster'], bev=0, collection=arch, lm='arch')
    box('kerb_front', (W - T, T, KH), (T / 2, -D / 2 + T / 2, KH / 2), M['oak'], bev=0, collection=arch, lm='arch')
    box('kerb_right', (T, D - 2 * T, KH), (W / 2 - T / 2, 0, KH / 2), M['plaster'], bev=0, collection=arch, lm='arch')
    oak = []
    oak.append(box('oak_back', (MX0 - LEFT, OAK, RH), ((LEFT + MX0) / 2, BACK - OAK / 2, RH / 2), M['oak'], bev=0, collection=arch, lm='arch'))
    oak.append(box('oak_left', (OAK, BACK - FRONT - OAK, RH), (LEFT + OAK / 2, (FRONT + BACK - OAK) / 2, RH / 2), M['oak'], bev=0, collection=arch, lm='arch'))
    oak.append(box('oak_front', (RIGHT - LEFT - OAK, OAK, KH - 0.002), ((LEFT + OAK + RIGHT) / 2, FRONT + OAK / 2, KH / 2), M['oak'], bev=0, collection=arch, lm='arch'))
    for o in oak: cine.world_uv(o, 1.0)
    # the panels' reveals: a dark groove every 0.61 m along the oak, and a rail at 2.44
    for k, x in enumerate([LEFT + 0.61 * i for i in range(1, 12) if LEFT + 0.61 * i < MX0 - 0.1]):
        box(f'oak_groove_b{k}', (0.008, 0.004, RH), (x, BACK - OAK - 0.001, RH / 2), M['oak_groove'], bev=0, collection=arch, lm='arch')
    for k, y in enumerate([FRONT + 0.61 * i for i in range(1, 12) if FRONT + 0.61 * i < BACK - 0.1]):
        box(f'oak_groove_l{k}', (0.004, 0.008, RH), (LEFT + OAK + 0.001, y, RH / 2), M['oak_groove'], bev=0, collection=arch, lm='arch')
    box('oak_rail_b', (MX0 - LEFT, 0.004, 0.008), ((LEFT + MX0) / 2, BACK - OAK - 0.001, 2.44), M['oak_groove'], bev=0, collection=arch, lm='arch')
    box('oak_rail_l', (0.004, BACK - FRONT, 0.008), (LEFT + OAK + 0.001, (FRONT + BACK) / 2, 2.44), M['oak_groove'], bev=0, collection=arch, lm='arch')
    mi = box('mint_back', (RIGHT - MX0, 0.012, RH), ((MX0 + RIGHT) / 2, BACK - 0.006, RH / 2), M['mint'], bev=0, collection=arch, lm='arch')
    cine.world_uv(mi, 1.0)
    # skirting: brushed steel along the oak
    box('skirt_back', (MX0 - LEFT - OAK, 0.012, 0.1), ((LEFT + OAK + MX0) / 2, BACK - OAK - 0.006, 0.05), M['brushed'], bev=0.002, collection=arch, lm='arch')
    box('skirt_left', (0.012, BACK - FRONT - OAK, 0.1), (LEFT + OAK + 0.006, (FRONT + BACK - OAK) / 2, 0.05), M['brushed'], bev=0.002, collection=arch, lm='arch')
    box('skirt_mint', (RIGHT - MX0, 0.012, 0.1), ((MX0 + RIGHT) / 2, BACK - 0.018, 0.05), M['white'], bev=0.002, collection=arch, lm='arch')
    # the blue neon at the top of the walls (the coffer's edge light, as filmed)
    box('neon_back', (MX0 - LEFT - OAK, 0.03, 0.025), ((LEFT + OAK + MX0) / 2, BACK - OAK - 0.05, RH - 0.06), M['blue_led'], bev=0, collection=arch)
    box('neon_left', (0.03, BACK - FRONT - OAK - 0.05, 0.025), (LEFT + OAK + 0.05, (FRONT + BACK - OAK - 0.05) / 2, RH - 0.06), M['blue_led'], bev=0, collection=arch)
    # phantoms: the drop ceiling with its mirrored coffer, the front and right walls above the kerbs, the vestibule's
    # ceiling (lower: under its header)
    P_ = M['phantom']; ph = lambda name, size, loc, mat=P_: box(name, size, loc, mat, bev=0, collection=phantom, bake_only=1)
    ph('ph_ceiling', (W, D, 0.2), (0, 0, RH + 0.1))
    ph('ph_coffer', (4.6, 3.2, 0.02), (-1.1, -0.3, RH - 0.005), M['mirror_ceiling'])
    ph('ph_front', (W, 0.2, RH - KH), (0, -D / 2 - 0.1, KH + (RH - KH) / 2), M['oak'])
    ph('ph_right', (0.2, D, RH - KH), (W / 2 + 0.1, 0, KH + (RH - KH) / 2), M['plaster'])
    ph('ph_vest_ceiling', (RIGHT - MX0, BACK - MY0, 0.04), ((MX0 + RIGHT) / 2, (MY0 + BACK) / 2, HEAD + 0.12), M['plaster'])


# ---------------------------------------------------------------- the vestibule
def vestibule(M, col):
    """The mantrap: chrome frames standing on a brushed sill, the glass left open (glass would vanish in the case),
    a frosted band across each fixed pane; the white header from the glass's head to the ceiling; the building's
    oak door in the back wall with its steel push bar, the intercom; a camera in the corner. The inner door is the
    rig's (it swings)."""
    t = 0.05                                                                     # the frames' section
    # front face (y = MY0), from the corner to the right cut
    for k, x in enumerate((MX0, VDOOR[0] - t / 2, VDOOR[1] + t / 2, RIGHT - t / 2)):
        box(f'vest_post_f{k}', (t, t, HEAD), (x, MY0, HEAD / 2), M['chrome'], bev=0.004, collection=col, lm='furn')
    for k, y in enumerate((MY0 + 1.0, MY0 + 2.0, BACK - t / 2)):
        box(f'vest_post_l{k}', (t, t, HEAD), (MX0, y, HEAD / 2), M['chrome'], bev=0.004, collection=col, lm='furn')
    box('vest_head_f', (RIGHT - MX0, t, t), ((MX0 + RIGHT) / 2, MY0, HEAD), M['chrome'], bev=0.004, collection=col, lm='furn')
    box('vest_head_l', (t, BACK - MY0, t), (MX0, (MY0 + BACK) / 2, HEAD), M['chrome'], bev=0.004, collection=col, lm='furn')
    for k, (a, b) in enumerate(((MX0, VDOOR[0] - t), (VDOOR[1] + t, RIGHT))):
        box(f'vest_sill_f{k}', (b - a, t, 0.12), ((a + b) / 2, MY0, 0.06), M['brushed'], bev=0.003, collection=col, lm='furn')
        box(f'vest_frost_f{k}', (b - a, 0.012, 0.08), ((a + b) / 2, MY0, 1.46), M['frost'], bev=0, collection=col, lm='furn')
    box('vest_sill_l', (t, BACK - MY0, 0.12), (MX0, (MY0 + BACK) / 2, 0.06), M['brushed'], bev=0.003, collection=col, lm='furn')
    box('vest_frost_l', (0.012, BACK - MY0, 0.08), (MX0, (MY0 + BACK) / 2, 1.46), M['frost'], bev=0, collection=col, lm='furn')
    box('vest_threshold', (VDOOR[1] - VDOOR[0], 0.12, 0.012), (sum(VDOOR) / 2, MY0, 0.006), M['brushed'], bev=0.002, collection=col, lm='furn')
    # the header: white above the glass, to the ceiling (front and left faces), and the vestibule's own ceiling
    box('vest_header_f', (RIGHT - MX0 + 0.08, 0.1, RH - HEAD - t / 2), ((MX0 - 0.08 + RIGHT) / 2, MY0, (RH + HEAD + t / 2) / 2), M['plaster'], bev=0, collection=col, lm='furn')
    box('vest_header_l', (0.1, BACK - MY0, RH - HEAD - t / 2), (MX0, (MY0 + BACK) / 2, (RH + HEAD + t / 2) / 2), M['plaster'], bev=0, collection=col, lm='furn')
    # the building's door: oak in a steel frame, a push bar, a closer; the intercom box beside it
    a, b = ODOOR; dz = 2.12
    for k, (x0, x1, z0, z1) in enumerate(((a - 0.05, a, 0, dz + 0.05), (b, b + 0.05, 0, dz + 0.05), (a - 0.05, b + 0.05, dz, dz + 0.05))):
        box(f'odoor_frame{k}', (x1 - x0, 0.04, z1 - z0), ((x0 + x1) / 2, BACK - 0.03, (z0 + z1) / 2), M['brushed'], bev=0.002, collection=col, lm='furn')
    dl = box('odoor_leaf', (b - a, 0.045, dz), ((a + b) / 2, BACK - 0.035, dz / 2), M['door_wood'], bev=0.004, collection=col, lm='furn'); cine.world_uv(dl, 1.0)
    box('odoor_bar', (b - a - 0.16, 0.05, 0.04), ((a + b) / 2, BACK - 0.085, 1.0), M['brushed'], bev=0.006, collection=col, lm='furn')
    for s in (a + 0.1, b - 0.1): box(f'odoor_bar_end{s:.2f}', (0.06, 0.06, 0.08), (s, BACK - 0.08, 1.0), M['brushed'], bev=0.004, collection=col, lm='furn')
    box('odoor_closer', (0.3, 0.06, 0.07), (b - 0.25, BACK - 0.08, dz - 0.08), M['brushed'], bev=0.004, collection=col, lm='furn')
    box('intercom_v', (0.12, 0.035, 0.2), (a - 0.25, BACK - 0.03, 1.35), M['brushed'], bev=0.004, collection=col, lm='furn')
    box('intercom_v_grille', (0.08, 0.004, 0.06), (a - 0.25, BACK - 0.05, 1.4), M['black'], bev=0, collection=col, lm='furn')
    # outside, on the oak by the vestibule: the alarm keypad and the intercom
    box('keypad', (0.14, 0.03, 0.18), (MX0 - 0.3, BACK - OAK - 0.015, 1.4), M['white'], bev=0.006, collection=col, lm='furn')
    box('keypad_face', (0.1, 0.004, 0.08), (MX0 - 0.3, BACK - OAK - 0.032, 1.43), M['black'], bev=0, collection=col, lm='furn')


def vestibule_door(M):
    """The inner door's parts about its hinge (at the origin), closed along +x: a chrome frame round the open glass,
    the two vertical bar handles, a 'PUSH' plate, the 'WILL RETURN' card hung on a chain; [(bmesh, material)]."""
    parts = []; w = VDOOR[1] - VDOOR[0] - 0.01; h = VDOOR_H; t = 0.045
    def add(size, c, mat, bev=0.003, uv=None):
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(c) @ Matrix.Diagonal((*size, 1)))
        if uv:
            uvl = bm.loops.layers.uv.new('UVMap')
            for f in bm.faces:
                for l in f.loops:
                    p = l.vert.co; l[uvl].uv = ((p.x - (c.x - size[0] / 2)) / size[0], (p.z - (c.z - size[2] / 2)) / size[2])
        elif bev: bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bev, segments=1, affect='EDGES')
        parts.append((bm, mat))
    add((t, t, h), Vector((t / 2, 0, h / 2)), M['chrome']); add((t, t, h), Vector((w - t / 2, 0, h / 2)), M['chrome'])
    add((w, t, t), Vector((w / 2, 0, h - t / 2)), M['chrome']); add((w, t, 0.14), Vector((w / 2, 0, 0.07)), M['brushed'])
    add((w - 2 * t, 0.01, 0.07), Vector((w / 2, 0, 1.0)), M['frost'])
    for s in (-1, 1):                                                       # the twin bar handles, both sides
        for k, x in enumerate((w - 0.16, w - 0.24)):
            add((0.022, 0.022, 0.9), Vector((x, s * 0.07, 1.05)), M['chrome'], bev=0.006)
            for z in (0.62, 1.48): add((0.02, 0.06, 0.02), Vector((x, s * 0.04, z)), M['chrome'], bev=0)
    add((0.1, 0.006, 0.18), Vector((w - 0.12, -0.028, 1.4)), M['brushed'])                     # PUSH (the showroom side is -y: it opens out)
    add((0.22, 0.004, 0.275), Vector((w * 0.42, -0.03, 1.62)), M['sign'], uv=True)               # the card, on the glass
    add((0.004, 0.004, 0.5), Vector((w * 0.42 - 0.06, -0.03, 2.0)), M['chrome'], bev=0); add((0.004, 0.004, 0.5), Vector((w * 0.42 + 0.06, -0.03, 2.0)), M['chrome'], bev=0)
    return parts


# ---------------------------------------------------------------- the pink cases on the left wall
def _bust(name, c, M, col, h=0.34, neck='gold'):
    """A necklace bust in blue velvet: a stepped base, the neck and shoulders; a necklace round it."""
    prof = [(0.0, 0.0), (0.07, 0.0), (0.07, 0.015), (0.03, 0.03), (0.035, h * 0.45), (0.1, h * 0.62), (0.11, h * 0.7), (0.06, h * 0.78), (0.035, h * 0.82), (0.033, h), (0.0, h)]
    o = lathe(name, prof, M['velvet'], loc=c, seg=20, collection=col, lm='furn'); o.scale = (1.0, 0.45, 1.0)
    pts = circle(Vector((c.x, c.y, c.z + h * 0.6)), 0.075, (1, 0, 0), (0, 0.45, 0), n=20, a0=0.0, a1=2 * math.pi)
    tube(f'{name}_neck', [Vector((p.x, p.y, p.z - 0.04 * abs(math.sin(i / 20 * math.pi)))) for i, p in enumerate(pts)], 0.006, M['gold'] if neck == 'gold' else M['silver'] if neck == 'silver' else M['pearl'], col, closed=True, seg=6, lm='furn')
    return o


def cases(M, col, rnd):
    """Four pink cases on the left wall: a drawer base, a lilac-lit recess (the chains behind, two glass shelves,
    busts with necklaces, ring and watch stands), the frieze with 'KMH', a gable over it; pilasters between them; a
    white orchid on one; the split air conditioner and the clock on the wall above. Returns the recesses' light
    places [(centre, width)]."""
    y0, y1 = CASES_Y; gap = 0.06; w = (y1 - y0 - gap * (N_CASES - 1)) / N_CASES; x0 = LEFT + OAK; xf = x0 + CASE_D
    out = []
    for i in range(N_CASES):
        a = y0 + i * (w + gap); b = a + w; yc = (a + b) / 2; nm = f'case{i}'
        box(f'{nm}_plinth', (CASE_D - 0.04, w, 0.08), (x0 + (CASE_D - 0.04) / 2, yc, 0.04), M['brushed'], bev=0.002, collection=col, lm='furn')
        box(f'{nm}_base', (CASE_D, w, 0.84), (x0 + CASE_D / 2, yc, 0.08 + 0.42), M['pink'], bev=0.004, collection=col, lm='furn')
        for k in range(3):                                                     # drawer lines and their chrome pulls
            z = 0.26 + k * 0.24
            box(f'{nm}_drawer{k}', (0.004, w - 0.1, 0.006), (xf + 0.002, yc, z + 0.11), M['oak_groove'], bev=0, collection=col, lm='furn')
            box(f'{nm}_pull{k}', (0.016, 0.18, 0.016), (xf + 0.01, yc, z), M['chrome'], bev=0.004, collection=col, lm='furn')
        z0, z1 = 0.92, 2.02
        bk = box(f'{nm}_back', (0.01, w - 0.08, z1 - z0), (x0 + 0.01, yc, (z0 + z1) / 2), M['lilac'], bev=0, collection=col, lm='furn'); uv_rect(bk, 'x')
        for s in (-1, 1):
            box(f'{nm}_side{s}', (CASE_D, 0.04, z1 - z0), (x0 + CASE_D / 2, yc + s * (w / 2 - 0.02), (z0 + z1) / 2), M['pink'], bev=0.003, collection=col, lm='furn')
        box(f'{nm}_floor', (CASE_D - 0.02, w - 0.08, 0.012), (x0 + (CASE_D - 0.02) / 2, yc, z0 + 0.006), M['velvet'], bev=0, collection=col, lm='furn')
        box(f'{nm}_led', (CASE_D - 0.06, w - 0.1, 0.012), (x0 + (CASE_D - 0.06) / 2, yc, z1 - 0.012), M['lilac_lit'], bev=0, collection=col)
        for j, zs in enumerate((1.28, 1.64)):
            box(f'{nm}_shelf{j}', (CASE_D - 0.1, w - 0.1, 0.01), (x0 + (CASE_D - 0.1) / 2 + 0.02, yc, zs), M['shelf'], bev=0, collection=col, lm='furn')
        # what is shown: busts on the floor of the recess, stands on the shelves
        nb = 3
        for j in range(nb):
            yy = a + w * (j + 0.5) / nb
            _bust(f'{nm}_bust{j}', Vector((x0 + 0.2, yy, z0 + 0.012)), M, col, h=0.3, neck=('gold', 'silver', 'pearl')[(i + j) % 3])
        for j, zs in enumerate((1.285, 1.645)):
            for q in range(4):
                yy = a + w * (q + 0.5) / 4; c = Vector((x0 + 0.22, yy, zs + 0.005))
                if (q + j + i) % 2:
                    cyl(f'{nm}_ring{j}{q}', 0.03, 0.05, c + Vector((0, 0, 0.025)), M['velvet'], r2=0.018, seg=12, collection=col, lm='furn')
                    lathe(f'{nm}_ringg{j}{q}', [(0.012, 0.0), (0.014, 0.004), (0.012, 0.008), (0.0, 0.008)], M['gold'], loc=c + Vector((0, 0, 0.05)), seg=10, collection=col, lm='furn')
                else:
                    rounded_slab(f'{nm}_watch{j}{q}', 0.05, 0.08, 0.07, 0.02, c + Vector((0, 0, 0.035)), M['velvet'], edge_bev=0.01, collection=col, lm='furn')
                    cyl(f'{nm}_watchf{j}{q}', 0.02, 0.012, c + Vector((0.03, 0, 0.05)), M['silver' if q % 3 else 'gold'], rot=(0, math.pi / 2, 0), seg=14, collection=col, lm='furn')
        # the frieze with its letters, and the gable
        fr = box(f'{nm}_frieze', (0.04, w, 0.28), (xf - 0.02, yc, 2.16), M['kmh'], bev=0, collection=col, lm='furn'); uv_rect(fr, 'x')
        for d_ in fr.data.uv_layers['UVMap'].data: d_.uv.x = 1.0 - d_.uv.x
        box(f'{nm}_frieze_back', (CASE_D - 0.04, w, 0.28), (x0 + (CASE_D - 0.04) / 2, yc, 2.16), M['pink'], bev=0, collection=col, lm='furn')
        bm = bmesh.new(); pts = [(yc - w / 2, 2.3), (yc + w / 2, 2.3), (yc + w / 2, 2.34), (yc, 2.58), (yc - w / 2, 2.34)]
        A = [bm.verts.new((x0, y, z)) for y, z in pts]; B = [bm.verts.new((xf, y, z)) for y, z in pts]
        bm.faces.new(A); bm.faces.new(list(reversed(B)))
        for k in range(len(pts)): bm.faces.new((A[k], B[k], B[(k + 1) % len(pts)], A[(k + 1) % len(pts)]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        g = cine._mesh_obj(f'{nm}_gable', bm, M['pink'], col, smooth=False); g['lm'] = 'furn'
        tube(f'{nm}_gable_edge', [Vector((xf + 0.004, yc - w / 2, 2.34)), Vector((xf + 0.004, yc, 2.58)), Vector((xf + 0.004, yc + w / 2, 2.34))], 0.008, M['silver'], col, seg=6, lm='furn')
        out.append((Vector((x0 + 0.25, yc, z1 - 0.05)), w - 0.1))
    # the orchid on the second case's floor
    oc = Vector((x0 + 0.36, y0 + (w + gap) * 1 + 0.2, 0.932))
    cyl('orchid_pot', 0.055, 0.1, oc + Vector((0, 0, 0.05)), M['white'], r2=0.045, seg=16, collection=col, lm='furn')
    for s in range(3):
        a_ = s * 2.1; top = oc + Vector((0.05 * math.cos(a_), 0.05 * math.sin(a_), 0.36))
        tube(f'orchid_stem{s}', [oc + Vector((0, 0, 0.1)), oc + Vector((0.02 * math.cos(a_), 0.02 * math.sin(a_), 0.25)), top], 0.003, M['stem'], col, seg=5, lm='furn')
        for p in range(4):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.022, segments=10, ring_count=6, location=top + Vector((0.035 * p * math.cos(a_ + 0.6), 0.035 * p * math.sin(a_ + 0.6), -0.03 * p)))
            o = bpy.context.active_object; o.name = f'orchid_flower{s}{p}'; o.scale = (1.0, 1.0, 0.45); o.data.materials.append(M['petal']); o['lm'] = 'furn'
            for c_ in o.users_collection: c_.objects.unlink(o)
            col.objects.link(o)
    # the pilasters between the cases: oak shows; the air conditioner and the wall clock above
    ac_y = 0.9
    rounded_slab('ac_unit', 0.22, 0.9, 0.3, 0.04, (LEFT + OAK + 0.11, ac_y, 2.78), M['white'], edge_bev=0.01, collection=col, lm='furn')
    box('ac_vent', (0.005, 0.8, 0.05), (LEFT + OAK + 0.222, ac_y, 2.66), M['black'], bev=0, collection=col, lm='furn')
    return out


# ---------------------------------------------------------------- the counter
def counter(M, col, rnd):
    """The glass showcase counter: a cream base with a blue LED line round its foot and its waist, chamfered ends;
    the case on it (chrome rim and posts, the glass left open), navy velvet trays inside with rings, chains and
    watches, a blue LED under the rim; the solid stretch at the middle (the buzzer, Howard's phone's place, a round
    mirror on a stand, the desk phone); chrome-armed stools before it."""
    xa, xb = COUNTER_X; ya, yb = COUNTER_Y; ch = 0.18
    def outline(m):
        return [(xa + m + ch, ya + m), (xb - m - ch, ya + m), (xb - m, ya + m + ch), (xb - m, yb - m - ch), (xb - m - ch, yb - m), (xa + m + ch, yb - m), (xa + m, yb - m - ch), (xa + m, ya + m + ch)]
    prism('counter_toe', outline(0.05), 0.0, 0.08, M['black'], col, bev=0.002)
    prism('counter_toe_led', outline(0.045), 0.06, 0.075, M['blue_led'], col, lm=None, bev=0)
    prism('counter_base', outline(0.0), 0.08, BASE_H, M['cream'], col)
    prism('counter_waist_led', outline(-0.004), BASE_H - 0.03, BASE_H - 0.015, M['blue_led'], col, lm=None, bev=0)
    for k, (a, b) in enumerate(((ya, STATION[0]), (STATION[1], yb))):
        sub = [(x, min(max(y, a), b)) for x, y in outline(0.0)]
        # the case: a velvet tray on the base, its jewels, the LED under the rim, the chrome rim and posts
        tr = box(f'counter_tray{k}', (xb - xa - 0.1, b - a - 0.1, 0.02), ((xa + xb) / 2, (a + b) / 2, BASE_H + 0.01), M['tray'], bev=0, collection=col, lm='furn')
        n = int((b - a) / 0.16)
        for j in range(n):
            for i in range(4):
                c = Vector((xa + 0.13 + i * (xb - xa - 0.26) / 3, a + 0.1 + (j + 0.5) * (b - a - 0.2) / n, BASE_H + 0.022))
                r = rnd.random()
                if r < 0.45:
                    lathe(f'counter_ring{k}_{j}_{i}', [(0.011, 0.0), (0.013, 0.003), (0.011, 0.006), (0.0, 0.006)], M['gold' if r < 0.3 else 'silver'], loc=c, seg=10, collection=col, lm='furn')
                    bpy.ops.mesh.primitive_ico_sphere_add(radius=0.006, subdivisions=1, location=c + Vector((0, 0, 0.009)))
                    o = bpy.context.active_object; o.name = f'counter_stone{k}_{j}_{i}'; o.data.materials.append(M['silver']); o['lm'] = 'furn'
                    for c_ in o.users_collection: c_.objects.unlink(o)
                    col.objects.link(o)
                elif r < 0.75:
                    pts = circle(c + Vector((0, 0, 0.002)), 0.05, (1, 0, 0), (0, 0.6, 0), n=14)
                    tube(f'counter_chain{k}_{j}_{i}', pts, 0.003, M['gold'], col, closed=True, seg=5, lm='furn')
                else:
                    rounded_slab(f'counter_watch{k}_{j}_{i}', 0.04, 0.05, 0.012, 0.01, c + Vector((0, 0, 0.006)), M['silver' if r > 0.9 else 'gold'], edge_bev=0.003, collection=col, lm='furn')
        # the rim round the case's top (a ring of chrome: its outline less its inside)
        o_in = [(x + (0.025 if x < (xa + xb) / 2 else -0.025), min(max(y + (0.025 if y < (a + b) / 2 else -0.025), a + 0.025), b - 0.025)) for x, y in sub]
        bm = bmesh.new()
        A = [bm.verts.new((x, y, COUNTER_H - 0.02)) for x, y in sub]; B = [bm.verts.new((x, y, COUNTER_H)) for x, y in sub]
        Ai = [bm.verts.new((x, y, COUNTER_H - 0.02)) for x, y in o_in]; Bi = [bm.verts.new((x, y, COUNTER_H)) for x, y in o_in]
        nn = len(sub)
        for i in range(nn):
            j = (i + 1) % nn
            for f in ((A[i], A[j], B[j], B[i]), (Bi[i], Bi[j], Ai[j], Ai[i]), (B[i], B[j], Bi[j], Bi[i]), (Ai[i], Ai[j], A[j], A[i])):
                try: bm.faces.new(f)
                except ValueError: pass
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        rim = cine._mesh_obj(f'counter_rim{k}', bm, M['chrome'], col, smooth=False); rim['lm'] = 'furn'
        led = rim.copy(); led.data = rim.data.copy(); led.name = f'counter_led{k}'; col.objects.link(led)
        led.data.materials[0] = M['blue_led']; led.location.z = -0.022; led.scale = (1.0, 1.0, 0.5); del led['lm']
        for i, (x, y) in enumerate(sub):
            if i % 1 == 0 and (abs(y - a) > 1e-3 or True):
                box(f'counter_post{k}_{i}', (0.018, 0.018, COUNTER_H - BASE_H - 0.02), (x + (0.009 if x < (xa + xb) / 2 else -0.009), min(max(y, a + 0.009), b - 0.009), (BASE_H + COUNTER_H - 0.02) / 2), M['chrome'], bev=0, collection=col, lm='furn')
    # the solid stretch: a cream top over the base, the buzzer, the phone's place, a round mirror, the desk phone
    a, b = STATION
    box('station_case', (xb - xa, b - a, COUNTER_H - BASE_H), ((xa + xb) / 2, (a + b) / 2, (BASE_H + COUNTER_H) / 2), M['cream'], bev=0.004, collection=col, lm='furn')
    box('station_top', (xb - xa + 0.03, b - a + 0.01, 0.02), ((xa + xb) / 2, (a + b) / 2, COUNTER_H + 0.01), M['chrome'], bev=0.003, collection=col, lm='furn')
    cyl('buzzer_box', 0.025, 0.014, BUZZER - Vector((0, 0, 0.005)), M['black'], seg=14, collection=col, lm='furn')
    cyl('buzzer_button', 0.012, 0.01, BUZZER + Vector((0, 0, 0.004)), M['blue_led'], seg=12, collection=col)
    mc = Vector(((xa + xb) / 2 - 0.12, b - 0.12, COUNTER_H + 0.02))
    lathe('mirror_foot', [(0.0, 0.0), (0.07, 0.0), (0.07, 0.01), (0.012, 0.02), (0.01, 0.2), (0.0, 0.2)], M['chrome'], loc=mc, seg=20, collection=col, lm='furn')
    cyl('mirror_disc', 0.1, 0.012, mc + Vector((0, 0, 0.3)), M['chrome'], rot=(math.pi / 2, 0, math.radians(70)), seg=28, collection=col, lm='furn')
    box('deskphone', (0.17, 0.2, 0.06), ((xa + xb) / 2 - 0.12, a + 0.16, COUNTER_H + 0.05), M['black'], rot=(0.15, 0, 0.3), bev=0.012, collection=col, lm='furn')
    for k, p in enumerate(STOOLS): stool(f'stool{k}', p, math.pi / 2, M, col)


def stool(name, p, face, M, col):
    """A counter stool: a chrome disc foot and column, a black leather bucket seat, a chrome arc round its back;
    facing `face` (radians from +y)."""
    T_ = Matrix.Translation((p.x, p.y, 0)) @ Matrix.Rotation(face, 4, 'Z'); parts = []
    parts.append(lathe(f'{name}_foot', [(0.0, 0.0), (0.22, 0.0), (0.22, 0.012), (0.05, 0.03), (0.0, 0.03)], M['chrome'], seg=28, collection=col, lm='furn'))
    parts.append(cyl(f'{name}_column', 0.025, STOOL_SEAT - 0.08, (0, 0, (STOOL_SEAT - 0.08) / 2 + 0.03), M['chrome'], seg=14, collection=col, lm='furn'))
    parts.append(tube(f'{name}_ring', circle(Vector((0, 0, 0.3)), 0.17, (1, 0, 0), (0, 1, 0), n=24), 0.009, M['chrome'], col, closed=True, seg=6, lm='furn'))
    parts.append(lathe(f'{name}_seat', [(0.0, STOOL_SEAT - 0.05), (0.21, STOOL_SEAT - 0.05), (0.23, STOOL_SEAT - 0.01), (0.22, STOOL_SEAT + 0.03), (0.18, STOOL_SEAT + 0.04), (0.0, STOOL_SEAT + 0.02)], M['leather'], seg=28, collection=col, lm='furn'))
    arc = circle(Vector((0, 0, STOOL_SEAT + 0.2)), 0.22, (1, 0, 0), (0, 1, 0), n=20, a0=math.radians(200), a1=math.radians(340))
    parts.append(tube(f'{name}_arm', [Vector((arc[0].x, arc[0].y, STOOL_SEAT + 0.03))] + arc + [Vector((arc[-1].x, arc[-1].y, STOOL_SEAT + 0.03))], 0.014, M['chrome'], col, seg=8, lm='furn'))
    bm = bmesh.new(); seg = 16
    for i in range(seg):                                                         # the padded back inside the arc
        a0 = math.radians(205 + 130 * i / seg); a1 = math.radians(205 + 130 * (i + 1) / seg)
        v = [bm.verts.new((0.2 * math.cos(a), 0.2 * math.sin(a), z)) for a, z in ((a0, STOOL_SEAT + 0.02), (a1, STOOL_SEAT + 0.02), (a1, STOOL_SEAT + 0.19), (a0, STOOL_SEAT + 0.19))]
        bm.faces.new(v)
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.03)
    ob = cine._mesh_obj(f'{name}_back', bm, M['leather'], col); ob['lm'] = 'furn'; parts.append(ob)
    for o in parts: cine.place(o, T_)


# ---------------------------------------------------------------- the oak wall: photos, the TV, the monitor
def photo_wall(M, col, rnd):
    """Some twenty framed snapshots on the oak (gold and black frames), each print a cell of the atlas; the TV on
    its articulated arm by the corner, angled to the room (its face drawn live); the camera monitor high by the
    vestibule (live too)."""
    cols_x = [-2.62, -2.05, -1.48, -0.9, -0.32, 0.26, 0.84, 1.4]
    k = 0; yb = BACK - OAK
    for i, x in enumerate(cols_x):
        z = 2.55 - rnd.uniform(0.0, 0.12)
        while z > 1.15 and k < 32:
            w = rnd.uniform(0.3, 0.42); h = w * rnd.choice((0.8, 1.25, 1.0)); zc = z - h / 2
            if zc - h / 2 < 1.05: break
            cx = x + rnd.uniform(-0.04, 0.04); fr = M['frame_gold'] if rnd.random() < 0.55 else M['frame_black']
            box(f'photo_frame{k}', (w + 0.04, 0.022, h + 0.04), (cx, yb - 0.011, zc), fr, bev=0.004, collection=col, lm='furn')
            pr = box(f'photo_print{k}', (w - 0.02, 0.004, h - 0.02), (cx, yb - 0.024, zc), M['photos'], bev=0, collection=col, lm='furn')
            uv_rect(pr, 'y')
            cell = k % 16; me = pr.data; uv = me.uv_layers['UVMap']
            for d in uv.data: d.uv = ((cell % 4 + 0.06 + d.uv.x * 0.88) / 4, (3 - cell // 4 + 0.06 + d.uv.y * 0.88) / 4)
            k += 1; z = zc - h / 2 - 0.07
    # the TV: a wall plate, the folding arm, the set (black, a thin bezel), its face
    plate = Vector((TV.x - 0.15, yb - 0.01, TV.z))
    box('tv_plate', (0.3, 0.02, 0.4), plate, M['black'], bev=0.004, collection=col, lm='furn')
    elbow = Vector((TV.x - 0.42, yb - 0.34, TV.z - 0.02))
    back = TV - TV_F * 0.06
    tube('tv_arm0', [plate - Vector((0, 0.01, 0)), elbow], 0.022, M['black'], col, seg=10, lm='furn')
    tube('tv_arm1', [elbow, back], 0.022, M['black'], col, seg=10, lm='furn')
    ang = math.atan2(TV_F.y, TV_F.x) - math.atan2(-1, 0)
    Rz = Matrix.Translation(TV) @ Matrix.Rotation(ang, 4, 'Z')
    cine.place(box('tv_set', (TV_W + 0.04, 0.06, TV_H + 0.05), (0, 0.03, 0), M['black'], bev=0.006, collection=col, lm='furn'), Rz)
    cine.place(box('tv_logo', (0.06, 0.004, 0.012), (0, -0.002, -TV_H / 2 - 0.012), M['silver'], bev=0, collection=col, lm='furn'), Rz)
    cine.place(screen('tv_screen', TV_W, TV_H, M['screen'], col, q=0), Rz @ Matrix.Translation((0, -0.002, 0.01)))
    # the camera monitor: an older set on a shelf bracket, its face the cameras' views
    cine.place(box('cctv_set', (0.5, 0.3, 0.36), (0, 0.06, 0), M['black'], bev=0.01, collection=col, lm='furn'), Matrix.Translation(CCTV))
    box('cctv_shelf', (0.5, 0.36, 0.02), (CCTV.x, CCTV.y + 0.02, CCTV.z - 0.19), M['black'], bev=0.003, collection=col, lm='furn')
    cine.place(screen('cctv_screen', 0.42, 0.28, M['screen'], col, q=1), Matrix.Translation(CCTV + Vector((0, -0.092, 0.0))))


# ---------------------------------------------------------------- the waiting corner
def armchair(M, col):
    """A boxy armchair in black leather in a chrome tube cage (after Le Corbusier's): before the vestibule."""
    p, f = ARMCHAIR; ang = math.atan2(f.y, f.x) - math.atan2(-1, 0)
    T_ = Matrix.Translation((p.x, p.y, 0)) @ Matrix.Rotation(ang, 4, 'Z'); parts = []
    w, d, h = 0.76, 0.7, 0.66
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(box(f'lc_leg{sx}{sy}', (0.025, 0.025, 0.36), (sx * w / 2, sy * d / 2, 0.18), M['chrome'], bev=0.004, collection=col, lm='furn'))
    for sy in (-1, 1):
        parts.append(box(f'lc_rail_x{sy}', (w, 0.025, 0.025), (0, sy * d / 2, 0.36), M['chrome'], bev=0.004, collection=col, lm='furn'))
        parts.append(box(f'lc_rail_xt{sy}', (w, 0.025, 0.025), (0, sy * d / 2, 0.1), M['chrome'], bev=0.004, collection=col, lm='furn'))
    for sx in (-1, 1):
        parts.append(box(f'lc_rail_y{sx}', (0.025, d, 0.025), (sx * w / 2, 0, 0.36), M['chrome'], bev=0.004, collection=col, lm='furn'))
        parts.append(rounded_slab(f'lc_arm{sx}', 0.16, d - 0.04, 0.3, 0.03, (sx * (w / 2 - 0.08), 0.0, 0.52), M['leather'], edge_bev=0.02, collection=col, lm='furn'))
    parts.append(rounded_slab('lc_back', w - 0.32, 0.16, 0.32, 0.03, (0, d / 2 - 0.08, 0.53), M['leather'], edge_bev=0.02, collection=col, lm='furn'))
    parts.append(rounded_slab('lc_seat', w - 0.32, d - 0.18, 0.12, 0.03, (0, -0.08, 0.43), M['leather'], edge_bev=0.025, collection=col, lm='furn'))
    for o in parts: cine.place(o, T_)


# ---------------------------------------------------------------- lights' fixtures
def tracks(M, col):
    """Two chrome tracks across the showroom just under the ceiling, white cone lights hanging from them. Returns
    each cone's mouth (where its light is) and its aim."""
    heads = []
    for k, (y, xs) in enumerate(((-1.25, (-3.5, 1.8)), (1.35, (-3.5, 1.8)))):
        box(f'track{k}', (xs[1] - xs[0], 0.03, 0.025), ((xs[0] + xs[1]) / 2, y, RH - 0.05), M['white'], bev=0.003, collection=col, lm='furn')
        for i in range(8):
            x = xs[0] + 0.2 + i * (xs[1] - xs[0] - 0.4) / 7
            tube(f'track{k}_rod{i}', [Vector((x, y, RH - 0.06)), Vector((x, y, RH - 0.3))], 0.005, M['chrome'], col, seg=6, lm='furn')
            aim = Vector((0.0, 0.25 if k == 0 else -0.25, -1.0)).normalized() if i % 2 else Vector((-0.3 if x > -2.3 else 0.3, 0.0, -1.0)).normalized()
            c = Vector((x, y, RH - 0.34))
            q = Vector((0, 0, -1)).rotation_difference(aim)
            cone = lathe(f'track{k}_cone{i}', [(0.018, 0.08), (0.03, 0.06), (0.06, 0.0), (0.058, -0.005), (0.0, 0.07)], M['white'], seg=18, collection=col, lm='furn')
            cone.rotation_mode = 'QUATERNION'; cone.rotation_quaternion = q; cone.location = c
            heads.append((c + aim * 0.01, aim))
    return heads


def models(M, col):
    """Poly Haven models: the two big plants by the vestibule (their clay pots made brushed steel), the wall clock
    over the cases' end, the camera in the vestibule's corner."""
    from rooms.the_godfather import _fit
    for k, p in enumerate(PLANTS):
        _, ms = cine.import_gltf(os.path.join(PH, 'potted_plant_02', 'potted_plant_02_1k.gltf'), collection=col, lm='furn')
        for o in ms:
            for sl in o.material_slots:
                if sl.material and '_pot' in sl.material.name: sl.material = M['brushed']
        _fit(ms, (p.x, p.y, 0.0), 1.15, axis='z', ground=True)
        for o in ms: o.matrix_world = Matrix.Translation((p.x, p.y, 0)) @ Matrix.Rotation(k * 1.9, 4, 'Z') @ Matrix.Translation((-p.x, -p.y, 0)) @ o.matrix_world
    _, ms = cine.import_gltf(os.path.join(PH, 'wall_clock', 'wall_clock_1k.gltf'), collection=col, lm='furn')
    _fit(ms, (LEFT + OAK + 0.03, 2.95, 2.25), 0.4, axis='z')
    for o in ms: o.matrix_world = Matrix.Translation((LEFT + OAK + 0.03, 2.95, 2.25)) @ Matrix.Rotation(-math.pi / 2, 4, 'Z') @ Matrix.Translation((-(LEFT + OAK + 0.03), -2.95, -2.25)) @ o.matrix_world
    _, ms = cine.import_gltf(os.path.join(PH, 'security_camera_01', 'security_camera_01_1k.gltf'), collection=col, lm='furn')
    _fit(ms, (RIGHT - 0.25, BACK - 0.2, HEAD - 0.1), 0.3, axis='z')


# ---------------------------------------------------------------- the cut
def section(objs, M):
    """Every face the module's top cuts through (the walls' tops, the header's), flat and dark."""
    for ob in objs:
        if not ob.name.startswith(('left_', 'back_', 'kerb', 'oak_', 'mint_', 'vest_header')): continue
        me = ob.data
        if M['section'].name not in [m.name for m in me.materials if m]: me.materials.append(M['section'])
        k = [m.name if m else '' for m in me.materials].index(M['section'].name)
        for f in me.polygons:
            c = ob.matrix_world @ (sum((me.vertices[i].co for i in f.vertices), Vector()) / len(f.vertices))
            if f.normal.z > 0.9 and abs(c.z - RH) < 0.006: f.material_index = k


# ---------------------------------------------------------------- light
CEIL_LED = (1.0, 0.97, 0.93)               # the ceiling's LED panels: a cool white
TRACK = (1.0, 0.9, 0.78)                   # the cone lights: a little warmer
LILAC = (0.84, 0.64, 1.0)                  # inside the cases
VEST = (0.74, 1.0, 0.9)                    # the vestibule's cold panel (the film reads it teal-green)
TV_GLOW = (0.6, 0.85, 1.0)


def lights(heads, recesses):
    out = []
    def light(name, kind, loc, energy, colour, rot=None, **kw):
        ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = colour
        for k, v in kw.items(): setattr(ld, k, v)
        ob = cine.link(bpy.data.objects.new(name, ld)); ob.location = loc
        if rot: ob.rotation_euler = rot
        if kind in ('AREA', 'SPOT', 'SUN'): ob.visible_camera = False; ob.visible_glossy = False
        out.append(ob); return ob
    for k, (x, y) in enumerate(((-3.0, -1.6), (-0.6, -1.6), (-3.0, 1.0), (-0.6, 1.0), (1.4, -1.6), (1.4, -0.2))):
        light(f'ceiling{k}', 'AREA', (x, y, RH - 0.02), 150.0, CEIL_LED, shape='RECTANGLE', size=1.2, size_y=0.6)
    for k, (c, aim) in enumerate(heads):
        light(f'cone{k}', 'SPOT', c, 28.0, TRACK, rot=aim.to_track_quat('-Z', 'Y').to_euler(), spot_size=math.radians(55), spot_blend=0.4, shadow_soft_size=0.03)
    for k, (c, w) in enumerate(recesses):                              # an area light in each case, facing the room (+x)
        light(f'case_led{k}', 'AREA', c, 18.0, LILAC, rot=(0, -math.radians(55), 0), shape='RECTANGLE', size=0.2, size_y=w)
    light('vest_panel', 'AREA', ((MX0 + RIGHT) / 2, (MY0 + BACK) / 2, HEAD + 0.08), 140.0, VEST, shape='RECTANGLE', size=1.2, size_y=1.6)
    light('vest_fill', 'AREA', (RIGHT + 0.05, (MY0 + BACK) / 2, 1.4), 30.0, VEST, rot=(0, math.pi / 2, 0), shape='RECTANGLE', size=2.2, size_y=2.6)
    light('tv_glow', 'AREA', TV + TV_F * 0.05, 10.0, TV_GLOW, rot=TV_F.to_track_quat('-Z', 'Y').to_euler(), shape='RECTANGLE', size=TV_W, size_y=TV_H)
    light('counter_glow', 'AREA', (sum(COUNTER_X) / 2, sum(COUNTER_Y) / 2, BASE_H + 0.12), 12.0, (0.4, 0.6, 1.0), rot=(math.pi, 0, 0), shape='RECTANGLE', size=0.8, size_y=3.6)
    return out
