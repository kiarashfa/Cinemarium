# The Sopranos · Dr. Melfi's office, after Edward Pisoni's round room: a drum 22 feet across, walled in a warm red-brown
# veneer, with a long curved clerestory (vertical blinds, summer woods beyond), a shorter one behind Melfi's chair, a
# lit niche with a sink, a bookcase lined in red; the dark leather chaise under the window, the two chairs facing over
# a round glass table on a big rug, the rosewood desk. Its door opens on the waiting room, where a green-bronze nude
# stands before the armchair between two lamps. The plan is turned 25 degrees so that the case sees the room as the
# show's wide shot does; the drum's back half stands full height, its front half and the waiting room's open sides
# are cut to a kerb, and where the cut passes through the building's solid its face is drawn dark.
import math, os, random
import bpy, bmesh
from mathutils import Vector, Matrix
import cine
from cine import box, cyl, material, lathe, place, rounded_slab
from rooms.seinfeld import uv_rect, tube, circle, spine_row, _glow

W, D = 9.6, 7.6
H = 3.0                                    # the module's height (the cut through the building above the rooms)
RH = 2.6                                   # the rooms' walls, up to the soffit (the ceilings are phantoms above)
KH = 0.22                                  # the kerb, where the cut-away leaves the walls
TW = 0.14                                  # the module's own walls
TEX = os.path.join(cine.OUT, 'textures', 'the-sopranos')
tx = lambda n: os.path.join(TEX, n)
PH = lambda n: os.path.join(cine.CACHE, 'polyhaven', n, f'{n}_1k.gltf')

# the drum: centre, inner radius (the veneer's face), the wall behind it
C = Vector((-1.15, -0.15, 0.0))
R = 3.355
RO = R + 0.15
PHI = 25.0                                 # the plan turned: its north lies at 115 degrees (toward the back-left)
FULL = (40.0, 218.0)                       # the drum's arc left full height (degrees, from +x): the half the case looks into
WX = 2.4                                   # the waiting room: from x = WX to the module's right edge
WIN_Z = (1.3, 2.05)                        # the clerestories' sill and head
WAIT_Y0 = C.y + (R + 0.15) * math.sin(math.radians(25))   # where the waiting room's solid left wall begins (the drum bulges in below)


def th(plan):
    """A plan angle (the show's: north 90, east 0) in the module (degrees from +x)."""
    return plan + PHI


def on(a, r, z=0.0):
    """The point at angle a (degrees) and radius r from the drum's centre."""
    return Vector((C.x + r * math.cos(math.radians(a)), C.y + r * math.sin(math.radians(a)), z))


def inward(a):
    return Vector((-math.cos(math.radians(a)), -math.sin(math.radians(a)), 0.0))


# openings in the drum: (plan angle of the centre, half-width in degrees, kind)
NWIN = (th(90), 25.0)                      # the long curved clerestory, north
WWIN = (th(180), 12.0)                     # behind Melfi
NICHE = (th(135), 9.5)                     # the sink niche
BOOKS = (th(35), 8.5)                      # the bookcase behind Tony
DOOR = (th(-22), 11.0)                     # the double door to the waiting room (in the cut-away half)
CHAIRS = {'melfi': (th(180), 1.3), 'tony': (th(8), 1.3)}   # angle, radius of each chair's seat centre
SEAT = {'melfi': 0.46, 'tony': 0.47}       # cushion tops
CHAISE = (th(90), 2.86)
DESK = (th(215), 2.3)
STATUE = Vector((3.52, 1.95, 0.0))


def chair_at(who):
    """A chair's seat centre and its facing (the two chairs face each other)."""
    a, r = CHAIRS[who]; o = 'tony' if who == 'melfi' else 'melfi'
    p = on(a, r); q = on(*CHAIRS[o])
    f = (q - p); f.z = 0
    return p, f.normalized()


# ---------------------------------------------------------------- materials
def mats():
    M = {}
    M['veneer'] = material('veneer', rough=0.38, maps={'color': tx('veneer_color.jpg'), 'normal': tx('veneer_normal.jpg'), 'rough': tx('veneer_rough.jpg')}, scale=1.1, normal_strength=0.4, specular=0.5, coat=0.35, coat_rough=0.25)
    M['veneer_light'] = material('veneer_light', rough=0.38, maps={'color': tx('veneer_light_color.jpg'), 'normal': tx('veneer_normal.jpg')}, scale=1.1, normal_strength=0.4, coat=0.35, coat_rough=0.25)
    M['core'] = material('wall_core', (0.035, 0.028, 0.024), rough=0.9)
    M['reveal'] = material('reveal_paint', (0.82, 0.8, 0.74), rough=0.75)
    M['carpet'] = material('carpet', rough=0.95, maps={'color': tx('carpet_color.jpg'), 'normal': tx('carpet_normal.jpg')}, scale=0.8, normal_strength=0.5, specular=0.3)
    M['rug'] = material('rug', rough=0.95, maps={'color': tx('rug_color.jpg')}, scale=1.0, specular=0.3)
    M['terrazzo'] = material('terrazzo', rough=0.35, maps={'color': tx('terrazzo_color.jpg')}, scale=1.6, coat=0.3, coat_rough=0.3)
    M['kerb'] = material('kerb', (0.25, 0.22, 0.2), rough=0.9)
    M['section'] = material('section', (0.03, 0.028, 0.026), rough=0.92)
    M['ceiling'] = material('ceiling', rough=0.9, maps={'color': tx('ceiling_color.jpg')}, scale=1.4)
    M['chenille'] = material('chenille', rough=0.9, maps={'color': tx('chenille_color.jpg'), 'normal': tx('chenille_normal.jpg')}, scale=0.35, normal_strength=0.6, sheen=0.5, sheen_tint=(0.4, 0.4, 0.3))
    M['celadon'] = material('celadon', rough=0.88, maps={'color': tx('celadon_color.jpg'), 'normal': tx('celadon_normal.jpg')}, scale=0.3, normal_strength=0.5, sheen=0.3, sheen_tint=(0.5, 0.55, 0.5))
    M['leather'] = material('leather', rough=0.42, maps={'color': tx('leather_color.jpg'), 'normal': tx('leather_normal.jpg')}, scale=0.6, normal_strength=0.5, coat=0.3, coat_rough=0.35)
    M['boucle'] = material('boucle', rough=0.92, maps={'color': tx('boucle_color.jpg'), 'normal': tx('boucle_normal.jpg')}, scale=0.25, normal_strength=0.8, sheen=0.3, sheen_tint=(0.5, 0.5, 0.45))
    M['birch'] = material('birch', (0.6, 0.42, 0.24), rough=0.35, coat=0.5, coat_rough=0.2)
    M['mahogany'] = material('mahogany_leg', (0.13, 0.05, 0.03), rough=0.35, coat=0.5)
    M['rosewood'] = material('rosewood', rough=0.3, maps={'color': tx('rosewood_color.jpg')}, scale=0.9, coat=0.6, coat_rough=0.12)
    M['steel'] = material('brushed_steel', (0.62, 0.62, 0.6), rough=0.32, metal=1.0)
    M['chrome'] = material('chrome', (0.8, 0.8, 0.8), rough=0.12, metal=1.0)
    M['glass'] = material('table_glass', (0.55, 0.62, 0.6), rough=0.03, coat=1.0)
    M['shelf_glass'] = material('shelf_glass', (0.6, 0.66, 0.64), rough=0.05, coat=1.0)
    M['glass_edge'] = material('glass_edge', (0.5, 0.66, 0.6), rough=0.05, coat=1.0)
    M['tissue'] = material('tissue', (0.9, 0.9, 0.88), rough=0.9)
    M['lacquer_red'] = material('lacquer_red', (0.32, 0.05, 0.035), rough=0.3, coat=0.6)
    M['niche'] = material('niche_paint', (0.62, 0.6, 0.55), rough=0.7)
    M['counter'] = material('counter_stone', (0.36, 0.34, 0.31), rough=0.3, coat=0.4)
    M['blind'] = material('blind_fabric', (0.86, 0.83, 0.74), rough=0.85)
    M['view'] = material('window_view', rough=0.9, maps={'color': tx('view_color.jpg')}, scale=1.0)
    M['spines'] = material('spines', rough=0.6, maps={'color': tx('spines_color.jpg')}, scale=1.0)
    M['black'] = material('black_plastic', (0.02, 0.02, 0.022), rough=0.45)
    M['black_leather'] = material('black_leather', (0.018, 0.017, 0.017), rough=0.4, coat=0.3)
    M['ceramic'] = material('ceramic', (0.82, 0.8, 0.76), rough=0.2, coat=0.6)
    M['mug'] = material('mug_green', (0.12, 0.2, 0.17), rough=0.25, coat=0.6)
    M['paper'] = material('paper', (0.86, 0.85, 0.8), rough=0.85)
    M['folder'] = material('folder', (0.62, 0.42, 0.4), rough=0.7)
    M['candle'] = material('candle', (0.92, 0.82, 0.5), rough=0.5, emission=(1.0, 0.75, 0.4), emission_strength=0.6)
    M['bronze'] = material('bronze', (0.16, 0.11, 0.06), rough=0.38, metal=0.9)
    M['patina'] = material('patina', rough=0.55, maps={'color': tx('patina_color.jpg')}, scale=0.6, metal=0.35)
    M['shade'] = material('drum_shade', rough=0.8, maps={'color': tx('linen_color.jpg')}, scale=0.4, emission=(1.0, 0.82, 0.58), emission_strength=1.8)
    M['strip'] = material('shelf_light', (1.0, 0.9, 0.72), rough=0.5, emission=(1.0, 0.82, 0.58), emission_strength=6.0)
    M['lamp_head'] = material('lamp_glow', (1.0, 0.95, 0.85), rough=0.5, emission=(1.0, 0.9, 0.75), emission_strength=8.0)
    M['magazine'] = material('magazines', rough=0.35, maps={'color': tx('magazine_color.jpg')}, scale=1.0, coat=0.5)
    M['print'] = material('botanical', rough=0.6, maps={'color': tx('botanical.jpg')}, scale=1.0)
    for k in range(2): M[f'diploma{k}'] = material(f'diploma{k}', rough=0.4, maps={'color': tx(f'diploma{k}.jpg')}, scale=1.0, coat=0.6)
    M['switch'] = material('switch_plate', (0.78, 0.76, 0.7), rough=0.4)
    _glow(M['view'], 1.3)   # the woods in daylight: they shine through the blinds on the web as in the renders
    return M


# ---------------------------------------------------------------- geometry helpers
def arc_slab(name, r0, r1, a0, a1, z0, z1, mat, col, seg=None, **props):
    """A curved slab about the drum's centre: radii r0..r1, angles a0..a1 (degrees), heights z0..z1."""
    seg = seg or max(2, int(abs(a1 - a0) / 2.5))
    bm = bmesh.new(); rings = []
    for i in range(seg + 1):
        a = a0 + (a1 - a0) * i / seg
        rings.append([bm.verts.new(on(a, r, z)) for r, z in ((r0, z0), (r1, z0), (r1, z1), (r0, z1))])
    for i in range(seg):
        a, b = rings[i], rings[i + 1]
        for k in range(4): bm.faces.new((a[k], b[k], b[(k + 1) % 4], a[(k + 1) % 4]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = cine._mesh_obj(name, bm, mat, col, smooth=False)
    for k, v in props.items(): ob[k] = v
    return ob


def arc_sheet(name, r, a0, a1, z0, z1, mat, col, seg=None, flip=False, **props):
    """A curved sheet facing the drum's centre (or away, flip), UVs 0..1 across it (a view, a blind's field)."""
    seg = seg or max(2, int(abs(a1 - a0) / 2.0))
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); cols = []
    for i in range(seg + 1):
        a = a0 + (a1 - a0) * i / seg; cols.append((bm.verts.new(on(a, r, z0)), bm.verts.new(on(a, r, z1)), i / seg))
    for (a0v, a1v, u0), (b0v, b1v, u1) in zip(cols, cols[1:]):
        f = bm.faces.new((a0v, b0v, b1v, a1v) if not flip else (a1v, b1v, b0v, a0v))
        for l in f.loops:
            u = u0 if l.vert in (a0v, a1v) else u1; v = 0.0 if l.vert in (a0v, b0v) else 1.0
            l[uvl].uv = (1 - u if flip else u, v)
    ob = cine._mesh_obj(name, bm, mat, col, smooth=True)
    for k, v in props.items(): ob[k] = v
    return ob


def frame_at(a, r, z=0.0):
    """A frame on the drum's wall at angle a: origin there, local -y facing into the room, x along the wall."""
    p = on(a, r, z); n = inward(a)
    return Matrix.Translation(p) @ Matrix.Rotation(math.atan2(n.y, n.x) + math.pi / 2, 4, 'Z')


def polygon_prism(name, pts, z0, z1, mat, col, **props):
    """A vertical prism over a plan polygon (counter-clockwise points), from z0 to z1."""
    bm = bmesh.new()
    bot = [bm.verts.new((p[0], p[1], z0)) for p in pts]; top = [bm.verts.new((p[0], p[1], z1)) for p in pts]
    bm.faces.new(list(reversed(bot))); bm.faces.new(top)
    n = len(pts)
    for i in range(n): bm.faces.new((bot[i], bot[(i + 1) % n], top[(i + 1) % n], top[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = cine._mesh_obj(name, bm, mat, col, smooth=False)
    for k, v in props.items(): ob[k] = v
    return ob


def arc_pts(r, a0, a1, step=2.0):
    n = max(2, int(abs(a1 - a0) / step))
    return [tuple(on(a0 + (a1 - a0) * i / n, r)[:2]) for i in range(n + 1)]


# ---------------------------------------------------------------- the shell
def _openings():
    """The drum wall's openings: (a0, a1, z0, z1, kind)."""
    out = []
    for (a, hw), kind in ((NWIN, 'window'), (WWIN, 'window')): out.append((a - hw, a + hw, WIN_Z[0], WIN_Z[1], kind))
    out.append((NICHE[0] - NICHE[1], NICHE[0] + NICHE[1], 0.93, 2.02, 'niche'))
    out.append((BOOKS[0] - BOOKS[1], BOOKS[0] + BOOKS[1], 0.52, 2.24, 'books'))
    out.append((DOOR[0] - DOOR[1], DOOR[0] + DOOR[1], 0.0, 2.15, 'door'))
    return out


def _full(a):
    a = a % 360
    return FULL[0] <= a <= FULL[1]


def shell(M, arch, furn, phantom):
    """Floors, the drum's veneered wall (full height on its back half, a kerb in front) with its openings, the solid
    the drum is set in, the waiting room's walls; the phantom ceilings and missing walls."""
    box('subfloor', (W, D, 0.03), (0, 0, -0.027), M['kerb'], bev=0, collection=arch, lm='arch')
    floor = polygon_prism('floor', arc_pts(R + 0.02, 0, 360, 2.0)[:-1], -0.02, 0.0, M['carpet'], arch, lm='arch')
    box('floor_wait', (W / 2 - 1.9, D - 2 * TW, 0.02), ((1.9 + W / 2) / 2, 0, -0.01), M['terrazzo'], bev=0, collection=arch, lm='arch')
    # the drum: panels about 1.05 m wide with fine joints, a dark shadow gap at the floor, a joint at the door head
    ops = _openings()
    n = int(round(2 * math.pi * R / 1.05)); step = 360.0 / n
    gap = math.degrees(0.004 / R)
    for i in range(n):
        a0, a1 = i * step + gap / 2, (i + 1) * step - gap / 2
        # split the panel where openings begin and end
        cuts = sorted({a0, a1, *[x for o in ops for x in (o[0], o[1]) if a0 < x < a1]})
        for b0, b1 in zip(cuts, cuts[1:]):
            mid = (b0 + b1) / 2; full = _full(mid); top = RH if full else KH
            o = next((o for o in ops if o[0] <= mid <= o[1]), None)
            spans = [(0.05, top)]
            if o:
                if o[4] == 'door': spans = [] if not full else [(o[3], RH)]
                else: spans = [(0.05, min(o[2], top)), (o[3], top)] if full else [(0.05, min(o[2], top))]
            for z0, z1 in spans:
                if z1 - z0 < 0.005: continue
                for zz0, zz1 in ((z0, min(z1, 2.15)), (max(z0, 2.15), z1)):   # the joint at 2.15 m
                    if zz1 - zz0 > 0.005:
                        arc_slab(f'drum_panel_{i}_{b0:.1f}_{zz0:.2f}', R, R + 0.022, b0, b1, zz0 + (0.002 if zz0 > 2.1 else 0), zz1, M['veneer'], arch, seg=4, lm='arch')
    # the wall behind the veneer (the joints and the shadow gap show it), full height or a kerb
    for a0, a1 in ((FULL[0], FULL[1]), (FULL[1], FULL[0] + 360)):
        full = a0 == FULL[0]; top = RH if full else KH
        segs = [(a0, a1)]
        for o in ops:   # the openings pass through it
            nxt = []
            for s0, s1 in segs:
                if o[1] <= s0 or o[0] >= s1: nxt.append((s0, s1)); continue
                if s0 < o[0]: nxt.append((s0, o[0]))
                if o[1] < s1: nxt.append((o[1], s1))
                lo, hi = max(s0, o[0]), min(s1, o[1])
                if o[4] != 'door' or full:
                    if o[2] > 0.02: arc_slab(f'drum_core_{o[4]}_{lo:.0f}_lo', R + 0.02, RO, lo, hi, 0.0, min(o[2], top), M['core'], arch, lm='arch')
                    if full and o[3] < RH: arc_slab(f'drum_core_{o[4]}_{lo:.0f}_hi', R + 0.02, RO, lo, hi, o[3], RH, M['core'], arch, lm='arch')
            segs = nxt
        for s0, s1 in segs: arc_slab(f'drum_core_{s0:.0f}', R + 0.02, RO, s0, s1, 0.0, top, M['core'], arch, lm='arch')
    _solid(M, arch)
    _waiting_walls(M, arch, furn)
    # phantoms: the drum's front half as it really is (closed, full height), the ceilings, the module's missing walls
    arc_slab('drum_phantom', R, RO, FULL[1], FULL[0] + 360, KH, RH, M['veneer'], phantom, seg=60, bake_only=1)
    polygon_prism('ceiling_soffit', arc_pts(RO, 0, 360, 3.0)[:-1], RH, RH + 0.03, M['ceiling'], phantom, bake_only=1)
    box('ceiling_wait', (W / 2 - WX, D, 0.03), ((WX + W / 2) / 2, 0, RH + 0.015), M['ceiling'], bev=0, collection=phantom, bake_only=1)
    box('front_wall', (W, TW, RH - KH), (0, -D / 2 + TW / 2, (RH + KH) / 2), M['veneer'], bev=0, collection=phantom, bake_only=1)
    box('right_wall', (TW, D, RH - KH), (W / 2 - TW / 2, 0, (RH + KH) / 2), M['veneer'], bev=0, collection=phantom, bake_only=1)
    box('wait_inner_wall', (0.12, WAIT_Y0 + D / 2, RH - KH), (WX - 0.06, (WAIT_Y0 - D / 2) / 2, (RH + KH) / 2), M['veneer'], bev=0, collection=phantom, bake_only=1)
    for o in ops:   # the door's leaves, shut, for the bake (the room is closed while the two talk)
        if o[4] == 'door': arc_slab('door_phantom', R, RO, o[0], o[1], KH, o[3], M['veneer_light'], phantom, bake_only=1)


BAYS = [(NWIN, 0.32 + 0.12), (WWIN, 0.2 + 0.06), (NICHE, 0.3 + 0.03), (BOOKS, 0.32 + 0.03)]   # (opening, depth behind the wall)


def rim(a_from, a_to, step=3.0):
    """The drum's outer edge from angle a_from down to a_to, stepping out round the bays the openings need."""
    pts = []; a = a_from
    marks = sorted({a_from, a_to, *[x for (c, hw), d in BAYS for x in (c - hw - 0.3, c + hw + 0.3) if a_to < x < a_from]}, reverse=True)
    for m0, m1 in zip(marks, marks[1:]):
        mid = (m0 + m1) / 2
        bay = next((d for (c, hw), d in BAYS if c - hw - 0.3 <= mid <= c + hw + 0.3), 0.0)
        seg = arc_pts(RO + bay, m0, m1, step)
        if bay and pts: pts.append(tuple(on(m0, RO)[:2]))
        pts += seg if not pts or not bay else seg
        if bay: pts.append(tuple(on(m1, RO)[:2]))
    out = []
    for p in pts:
        p = (min(max(p[0], -W / 2 + 0.002), W / 2), min(max(p[1], -D / 2), D / 2 - 0.002))   # a bay may reach the module's edge, not past it
        if not out or (abs(out[-1][0] - p[0]) > 1e-5 or abs(out[-1][1] - p[1]) > 1e-5): out.append(p)
    return out


def _solid(M, arch):
    """The building the drum is set in: behind its full half up to the walls' top, a kerb's height elsewhere; the
    cut through it drawn dark."""
    A = on(FULL[1], RO); a_e = 25.0; E = on(a_e, RO)
    # full height: from the drum's outer face round its back to the module's walls and the waiting room's left wall
    left_y = A.y + (-W / 2 - A.x) * math.tan(math.radians(FULL[1]))      # where the cut at FULL[1] meets the left wall
    pts = [(E.x, E.y), (WX, E.y), (WX, D / 2), (-W / 2, D / 2), (-W / 2, left_y), (A.x, A.y)]
    pts += rim(FULL[1], a_e)[1:-1]
    polygon_prism('solid_full', pts, 0.0, RH, M['section'], arch, lm='arch')
    # kerb height: the rest outside the drum and the waiting room, the door's way through left open
    d0, d1 = DOOR[0] - DOOR[1], DOOR[0] + DOOR[1]
    P = on(d0, RO); Q = on(d1, RO)
    lo = [(A.x, A.y), (-W / 2, left_y), (-W / 2, -D / 2), (WX, -D / 2), (WX, P.y)] + arc_pts(RO, d0, FULL[1] - 360, 3.0)
    polygon_prism('solid_kerb_front', lo, 0.0, KH, M['section'], arch, lm='arch')
    hi = [(Q.x, Q.y), (WX, Q.y), (WX, E.y), (E.x, E.y)] + arc_pts(RO, a_e, d1, 2.0)[1:-1]
    polygon_prism('solid_kerb_door', hi, 0.0, KH, M['section'], arch, lm='arch')


def _waiting_walls(M, arch, furn):
    """The waiting room: its back wall (the module's) with a clerestory, its left wall on the solid, veneered alike;
    kerbs on its open sides."""
    y = D / 2 - TW; x0, x1 = WX, W / 2
    c, w = 3.5, 1.55
    for i, (a, b) in enumerate(((x0, c - w / 2), (c + w / 2, x1))):
        box(f'back_wall_{i}', (b - a, TW, RH), ((a + b) / 2, D / 2 - TW / 2, RH / 2), M['core'], bev=0, collection=arch, lm='arch')
    box('back_wall_sill', (w, TW, WIN_Z[0] - 0.1), (c, D / 2 - TW / 2, (WIN_Z[0] - 0.1) / 2), M['core'], bev=0, collection=arch, lm='arch')
    box('back_wall_head', (w, TW, RH - WIN_Z[1]), (c, D / 2 - TW / 2, (RH + WIN_Z[1]) / 2), M['core'], bev=0, collection=arch, lm='arch')
    # veneer panels on it, 1.05 m wide; the window cut out
    xs = [x0]
    while xs[-1] < x1 - 0.2: xs.append(min(xs[-1] + 1.05, x1))
    for i, (a, b) in enumerate(zip(xs, xs[1:])):
        for z0, z1 in ((0.05, 2.15), (2.152, RH)):
            if a < c + w / 2 and b > c - w / 2 and z0 < WIN_Z[1] and z1 > WIN_Z[0] - 0.1:
                parts = [(a, c - w / 2), (c + w / 2, b)]
                for k, (p0, p1) in enumerate(parts):
                    if p1 - p0 > 0.01: box(f'wait_panel_{i}_{z0:.1f}_{k}', (p1 - p0 - 0.004, 0.022, z1 - z0), ((p0 + p1) / 2, y - 0.011, (z0 + z1) / 2), M['veneer'], bev=0.001, collection=arch, lm='arch')
                for zz0, zz1 in ((z0, max(z0, WIN_Z[0] - 0.1)), (min(z1, WIN_Z[1]), z1)):
                    if zz1 - zz0 > 0.01:
                        p0, p1 = max(a, c - w / 2), min(b, c + w / 2)
                        box(f'wait_panel_{i}_{zz0:.2f}_w', (p1 - p0 - 0.004, 0.022, zz1 - zz0), ((p0 + p1) / 2, y - 0.011, (zz0 + zz1) / 2), M['veneer'], bev=0.001, collection=arch, lm='arch')
            else:
                box(f'wait_panel_{i}_{z0:.1f}', (b - a - 0.004, 0.022, z1 - z0), ((a + b) / 2, y - 0.011, (z0 + z1) / 2), M['veneer'], bev=0.001, collection=arch, lm='arch')
    # its left wall, on the solid: panels from WAIT_Y0 to the back
    ys = [WAIT_Y0]
    while ys[-1] < y - 0.2: ys.append(min(ys[-1] + 1.05, y))
    for i, (a, b) in enumerate(zip(ys, ys[1:])):
        for z0, z1 in ((0.05, 2.15), (2.152, RH)):
            box(f'wait_left_panel_{i}_{z0:.1f}', (0.022, b - a - 0.004, z1 - z0), (WX + 0.011, (a + b) / 2, (z0 + z1) / 2), M['veneer'], bev=0.001, collection=arch, lm='arch')
    # the window: reveals, blinds, the woods
    window_flat('wwin', c, w, M, furn)
    box('kerb_front', (W, TW, KH), (0, -D / 2 + TW / 2, KH / 2), M['kerb'], bev=0.002, collection=arch, lm='arch')
    box('kerb_right', (TW, D - 2 * TW, KH), (W / 2 - TW / 2, 0, KH / 2), M['kerb'], bev=0.002, collection=arch, lm='arch')


def section(objs, M):
    """Every face the cut passes through, flat and dark: the walls' and the solid's tops, and the solid's cut sides."""
    for ob in objs:
        if not ob.name.startswith(('drum_', 'solid_', 'back_wall', 'wait_', 'kerb')): continue
        me = ob.data
        if M['section'].name not in [m.name for m in me.materials if m]: me.materials.append(M['section'])
        k = [m.name if m else '' for m in me.materials].index(M['section'].name)
        for f in me.polygons:
            c = sum((me.vertices[i].co for i in f.vertices), Vector()) / len(f.vertices)
            if f.normal.z > 0.9 and (abs(c.z - RH) < 0.004 or abs(c.z - KH) < 0.004): f.material_index = k
            # the drum's ends where the full half drops to the kerb
            if ob.name.startswith('drum_') and abs(f.normal.z) < 0.1:
                a = math.degrees(math.atan2(c.y - C.y, c.x - C.x)) % 360
                r = math.hypot(c.x - C.x, c.y - C.y)
                if (abs(a - FULL[0]) < 0.6 or abs(a - FULL[1]) < 0.6) and R + 0.01 < r < RO - 0.005: f.material_index = k


# ---------------------------------------------------------------- windows, niche, bookcase
def window_curved(name, a, hw, M, col, bay=0.32):
    """A clerestory through the drum's wall: white reveals out to the glass, vertical blinds half open, the woods."""
    a0, a1 = a - hw, a + hw; z0, z1 = WIN_Z; rg = RO + bay
    arc_slab(f'{name}_sill', R - 0.01, rg, a0, a1, z0 - 0.03, z0, M['reveal'], col, lm='furn')
    arc_slab(f'{name}_head', R, rg, a0, a1, z1, z1 + 0.03, M['reveal'], col, lm='furn')
    for e, s in ((a0, 1), (a1, -1)):
        de = math.degrees(0.012 / R) * s
        arc_slab(f'{name}_jamb{s}', R, rg, e, e + de, z0, z1, M['reveal'], col, seg=1, lm='furn')
    v = arc_sheet(f'{name}_view', rg - 0.005, a0 + 0.4, a1 - 0.4, z0 + 0.02, z1 - 0.02, M['view'], col)
    for attr in ('visible_shadow', 'visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter'): setattr(v, attr, False)
    # the blinds: louvres 89 mm wide every 80 mm, turned 55 degrees, from a headrail under the head
    rb = R + 0.12; arc_slab(f'{name}_headrail', rb - 0.02, rb + 0.02, a0 + 0.3, a1 - 0.3, z1 - 0.04, z1 - 0.005, M['blind'], col, lm='furn')
    n = int(math.radians(2 * hw) * rb / 0.08)
    bm = bmesh.new()
    for i in range(n):
        aa = a0 + (i + 0.5) * 2 * hw / n; p = on(aa, rb); t = Vector((-math.sin(math.radians(aa)), math.cos(math.radians(aa)), 0))
        nrm = -inward(aa); ang = math.radians(55)
        u = (t * math.cos(ang) + nrm * math.sin(ang)) * 0.0445
        zb, zt = z0 + 0.015, z1 - 0.045
        vs = [bm.verts.new(p - u + Vector((0, 0, zb))), bm.verts.new(p + u + Vector((0, 0, zb))), bm.verts.new(p + u + Vector((0, 0, zt))), bm.verts.new(p - u + Vector((0, 0, zt)))]
        bm.faces.new(vs)
    ob = cine._mesh_obj(f'{name}_louvres', bm, M['blind'], col, smooth=False); ob['lm'] = 'furn'
    ob.modifiers.new('solid', 'SOLIDIFY').thickness = 0.0015


def window_flat(name, c, w, M, col):
    """The waiting room's clerestory in the back wall (the module's edge: the glass sits in the wall's depth): reveals,
    blinds hanging in front, the woods."""
    z0, z1 = WIN_Z; z0 -= 0.1; y = D / 2 - TW
    box(f'{name}_sill', (w + 0.02, TW + 0.02, 0.03), (c, y + TW / 2 - 0.01, z0 - 0.015), M['reveal'], bev=0.002, collection=col, lm='furn')
    box(f'{name}_head', (w, TW, 0.03), (c, y + TW / 2, z1 + 0.015), M['reveal'], bev=0, collection=col, lm='furn')
    for s in (-1, 1): box(f'{name}_jamb{s}', (0.03, TW, z1 - z0), (c + s * (w / 2 + 0.015), y + TW / 2, (z0 + z1) / 2), M['reveal'], bev=0, collection=col, lm='furn')
    v = uv_rect(box(f'{name}_view', (w, 0.006, z1 - z0), (c, D / 2 - 0.006, (z0 + z1) / 2), M['view'], bev=0, collection=col))
    for attr in ('visible_shadow', 'visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter'): setattr(v, attr, False)
    box(f'{name}_headrail', (w + 0.04, 0.04, 0.035), (c, y - 0.06, z1 + 0.02), M['blind'], bev=0.003, collection=col, lm='furn')
    n = int(w / 0.08); bm = bmesh.new()
    for i in range(n):
        x = c - w / 2 + (i + 0.5) * w / n; u = Vector((math.cos(math.radians(55)), math.sin(math.radians(55)), 0)) * 0.0445
        zb, zt = z0 + 0.005, z1 + 0.005; p = Vector((x, y - 0.06, 0))
        bm.faces.new([bm.verts.new(p - u + Vector((0, 0, zb))), bm.verts.new(p + u + Vector((0, 0, zb))), bm.verts.new(p + u + Vector((0, 0, zt))), bm.verts.new(p - u + Vector((0, 0, zt)))])
    ob = cine._mesh_obj(f'{name}_louvres', bm, M['blind'], col, smooth=False); ob['lm'] = 'furn'
    ob.modifiers.new('solid', 'SOLIDIFY').thickness = 0.0015


def windows(M, col):
    window_curved('nwin', *NWIN, M, col, bay=0.32)
    window_curved('wwin_drum', *WWIN, M, col, bay=0.2)
    # two small bronzes on the long sill: a leaping dancer, a reclining woman
    for k, (da, kind) in enumerate(((-14, 'leap'), (16, 'recline'))):
        p = on(NWIN[0] + da, R + 0.1, WIN_Z[0]); _bronze(f'sill_bronze{k}', p, kind, NWIN[0] + da, M, col)


def _bronze(name, p, kind, a, M, col):
    """A small abstract bronze figure on a black plinth (lumps along a curve)."""
    box(f'{name}_plinth', (0.12, 0.07, 0.02), p + Vector((0, 0, 0.01)), M['black'], rot=(0, 0, math.radians(a + 90)), bev=0.002, collection=col, lm='furn')
    t = Vector((-math.sin(math.radians(a)), math.cos(math.radians(a)), 0))
    if kind == 'leap':
        pts = [p + t * (-0.06 + 0.12 * i / 8) + Vector((0, 0, 0.03 + 0.09 * math.sin(math.pi * i / 8) + 0.02 * (i == 3))) for i in range(9)]
        tube(f'{name}_body', pts, 0.008, M['bronze'], col, seg=8, lm='furn')
        tube(f'{name}_leg', [pts[2], pts[2] + Vector((0, 0, -0.07)) + t * 0.02], 0.005, M['bronze'], col, seg=6, lm='furn')
    else:
        pts = [p + t * (-0.05 + 0.1 * i / 8) + Vector((0, 0, 0.026 + 0.03 * math.sin(math.pi * i / 10) * (i > 3))) for i in range(9)]
        tube(f'{name}_body', pts, 0.011, M['bronze'], col, seg=8, lm='furn')
        cyl(f'{name}_head', 0.012, 0.02, pts[-1] + Vector((0, 0, 0.02)), M['bronze'], seg=10, collection=col, lm='furn')


def niche(M, col):
    """The lit niche with a sink: plain painted inside, two glass shelves with cups and a carafe, a stone counter with a
    small steel sink and an espresso maker; veneered cupboard doors below, flush, two knobs."""
    a, hw = NICHE; F = frame_at(a, R); wdt = 2 * R * math.sin(math.radians(hw)); d = 0.3; z0, z1 = 0.93, 2.02
    parts = []
    add = lambda o: (parts.append(o), o)[1]
    add(box('niche_back', (wdt, 0.02, z1 - z0), (0, d, (z0 + z1) / 2), M['niche'], bev=0, collection=col, lm='furn'))
    for s in (-1, 1): add(box(f'niche_side{s}', (0.02, d, z1 - z0), (s * wdt / 2, d / 2, (z0 + z1) / 2), M['niche'], bev=0, collection=col, lm='furn'))
    add(box('niche_top', (wdt, d, 0.02), (0, d / 2, z1), M['niche'], bev=0, collection=col, lm='furn'))
    add(box('niche_counter', (wdt + 0.02, d + 0.03, 0.035), (0, d / 2 - 0.015, z0 - 0.0175), M['counter'], bev=0.003, collection=col, lm='furn'))
    for k, zs in enumerate((1.36, 1.68)): add(box(f'niche_shelf{k}', (wdt - 0.04, d - 0.06, 0.008), (0, d / 2 + 0.02, zs), M['shelf_glass'], bev=0, collection=col, lm='furn'))
    add(rounded_slab('niche_sink', 0.34, 0.24, 0.006, 0.04, (-wdt / 4, d / 2, z0 + 0.003), M['steel'], collection=col, lm='furn'))
    add(tube('niche_tap', [(-wdt / 4, d - 0.04, z0), (-wdt / 4, d - 0.04, z0 + 0.2), (-wdt / 4, d - 0.12, z0 + 0.22), (-wdt / 4, d - 0.15, z0 + 0.17)], 0.008, M['chrome'], col, seg=8, lm='furn'))
    add(box('niche_espresso', (0.2, 0.24, 0.3), (wdt / 4, d / 2 + 0.03, z0 + 0.15), M['steel'], bev=0.01, collection=col, lm='furn'))
    add(cyl('niche_carafe', 0.06, 0.16, (wdt / 4 + 0.02, d / 2 - 0.08, z0 + 0.08), M['shelf_glass'], seg=16, collection=col, lm='furn'))
    rnd = random.Random(4)
    for k in range(5):   # cups and glasses on the shelves
        zs = 1.36 if k < 3 else 1.68; x = -wdt / 2 + 0.12 + k % 3 * 0.18 + rnd.uniform(-0.02, 0.02)
        add(lathe(f'niche_cup{k}', [(0.0, 0), (0.03, 0), (0.035, 0.07), (0.032, 0.07), (0.0, 0.01)], M['ceramic'] if k % 2 else M['shelf_glass'], loc=(x, d / 2 + 0.03, zs + 0.004), seg=14, collection=col, lm='furn'))
    add(lathe('niche_vase', [(0.0, 0), (0.04, 0), (0.05, 0.08), (0.025, 0.2), (0.03, 0.24), (0.0, 0.24)], M['ceramic'], loc=(wdt / 2 - 0.12, d / 2 + 0.04, 1.684), seg=16, collection=col, lm='furn'))
    # the cupboard below: two veneer doors, flush with the wall (the wall's panels stop at the niche)
    for s in (-1, 1):
        add(box(f'niche_door{s}', (wdt / 2 - 0.006, 0.02, z0 - 0.08), (s * wdt / 4, -0.01, 0.05 + (z0 - 0.08) / 2), M['veneer'], bev=0.002, collection=col, lm='furn'))
        add(cyl(f'niche_knob{s}', 0.012, 0.02, (s * 0.03, -0.025, z0 - 0.2), M['chrome'], rot=(math.pi / 2, 0, 0), seg=12, collection=col, lm='furn'))
    for o in parts: place(o, F)
    return F @ Vector((0, d / 2, z1 - 0.04))


def bookcase(M, col):
    """The recessed bookcase behind Tony's chair: veneer shelves, a red-lacquered back, strip lights under the
    shelves, books, a few objects."""
    a, hw = BOOKS; F = frame_at(a, R); wdt = 2 * R * math.sin(math.radians(hw)); d = 0.32; z0, z1 = 0.52, 2.24
    parts = []; rnd = random.Random(12)
    add = lambda o: (parts.append(o), o)[1]
    add(box('books_back', (wdt, 0.02, z1 - z0), (0, d, (z0 + z1) / 2), M['lacquer_red'], bev=0, collection=col, lm='furn'))
    for s in (-1, 1): add(box(f'books_side{s}', (0.02, d, z1 - z0), (s * wdt / 2, d / 2, (z0 + z1) / 2), M['veneer'], bev=0, collection=col, lm='furn'))
    shelves = [z0 + k * (z1 - z0) / 4 for k in range(5)]
    for k, zs in enumerate(shelves):
        add(box(f'books_shelf{k}', (wdt, d, 0.03), (0, d / 2, zs), M['veneer'], bev=0.002, collection=col, lm='furn'))
        if 0 < k: add(box(f'books_strip{k}', (wdt - 0.06, 0.012, 0.006), (0, 0.04, zs - 0.018), M['strip'], bev=0, collection=col, lm='furn'))
    for k, zs in enumerate(shelves[:-1]):
        spine_row(f'books_row{k}', wdt - 0.06, zs + 0.015, 0.3, d - 0.04, M, col, parts, rnd, x_at=0.0)
        parts[-1].location.y += d / 2 + 0.01
    for o in parts: place(o, F)


def diplomas(M, col):
    """Her diplomas between the drum's cut and the bookcase: a medical degree, the state's licence."""
    a = (FULL[0] + BOOKS[0] - BOOKS[1]) / 2 + 0.4
    for k, z in enumerate((1.62, 1.24)):
        F = frame_at(a, R - 0.005, z)
        o = uv_rect(box(f'diploma{k}', (0.36, 0.012, 0.28), (0, 0, 0), M[f'diploma{k}'], bev=0.002, collection=col, lm='furn'))
        place(o, F)
    # the light switch and an outlet by the niche, as on the set
    for k, (aa, z, s) in enumerate(((NICHE[0] + NICHE[1] + 4, 1.22, (0.07, 0.006, 0.115)), (NWIN[0] + 4, 0.35, (0.07, 0.006, 0.115)))):
        place(box(f'switch{k}', s, (0, -0.003, 0), M['switch'], bev=0.001, collection=col, lm='furn'), frame_at(aa, R, z))


# ---------------------------------------------------------------- furniture
def chaise(M, col):
    """The chaise under the long window: a leather mattress on a slim frame, its head end raised and sloping, thin
    chrome legs."""
    a, r = CHAISE; F = frame_at(a, r)
    L, Wd = 1.9, 0.66; parts = []
    add = lambda o: (parts.append(o), o)[1]
    add(rounded_slab('chaise_frame', L, Wd, 0.05, 0.02, (0, 0, 0.3), M['black_leather'], collection=col, lm='furn'))
    add(rounded_slab('chaise_mattress', L - 0.42, Wd - 0.02, 0.1, 0.03, (0.2, 0, 0.375), M['leather'], edge_bev=0.025, collection=col, lm='furn'))
    hd = add(rounded_slab('chaise_head', 0.5, Wd - 0.02, 0.1, 0.03, (0, 0, 0), M['leather'], edge_bev=0.025, collection=col, lm='furn'))
    hd.rotation_euler.y = math.radians(-24); hd.location = (-L / 2 + 0.25, 0, 0.45)
    for sx in (-1, 1):
        for sy in (-1, 1): add(box(f'chaise_leg{sx}{sy}', (0.022, 0.022, 0.28), (sx * (L / 2 - 0.1), sy * (Wd / 2 - 0.08), 0.14), M['chrome'], bev=0.003, collection=col, lm='furn'))
    for sy in (-1, 1): add(box(f'chaise_rail{sy}', (L - 0.2, 0.018, 0.018), (0, sy * (Wd / 2 - 0.08), 0.05), M['chrome'], bev=0.003, collection=col, lm='furn'))
    # its head toward Melfi's side (plan west: the larger angle)
    for o in parts: place(o, F)


def melfi_chair(M, col):
    """Melfi's chair, a 1950s lounge chair (Heywood-Wakefield's, as sold since): blond birch Z frames, a seat and a
    back upholstered in celadon wool. Built facing -y, about its seat centre."""
    p, f = chair_at('melfi'); parts = []
    add = lambda o: (parts.append(o), o)[1]
    st = SEAT['melfi']
    add(rounded_slab('mchair_seat', 0.56, 0.54, 0.11, 0.04, (0, -0.02, st - 0.055), M['celadon'], edge_bev=0.02, collection=col, lm='furn'))
    bk = add(rounded_slab('mchair_back', 0.56, 0.1, 0.52, 0.04, (0, 0, 0), M['celadon'], edge_bev=0.02, collection=col, lm='furn'))
    bk.rotation_euler.x = math.radians(-16); bk.location = (0, 0.26, st + 0.24)
    for s in (-1, 1):
        x = s * 0.31
        # the Z: the arm forward at 0.6 m, down and back to the rear foot; the front leg splayed forward
        add(tube(f'mchair_arm{s}', [(x, 0.24, 0.6), (x, -0.3, 0.6)], 0.018, M['birch'], col, seg=8, lm='furn'))
        add(tube(f'mchair_z{s}', [(x, -0.3, 0.6), (x, 0.32, 0.0)], 0.02, M['birch'], col, seg=8, lm='furn'))
        add(tube(f'mchair_front{s}', [(x, -0.2, st - 0.1), (x, -0.34, 0.0)], 0.018, M['birch'], col, seg=8, lm='furn'))
        add(tube(f'mchair_rail{s}', [(x, -0.22, st - 0.1), (x, 0.25, st - 0.06)], 0.016, M['birch'], col, seg=8, lm='furn'))
    for o in parts: place(o, _chair_frame(p, f))


def _chair_frame(p, f):
    """A chair built facing -y about its seat centre, turned to face f at p."""
    return Matrix.Translation((p.x, p.y, 0)) @ Matrix.Rotation(math.atan2(f.y, f.x) + math.pi / 2, 4, 'Z')


def tony_chair(M, col):
    """Tony's chair: a tub club chair in olive chenille, its back and arms one curved shell, a loose seat cushion,
    short tapered mahogany legs. Built facing -y."""
    p, f = chair_at('tony'); parts = []
    st = SEAT['tony']
    # the shell: a horseshoe in plan (0.8 wide, 0.78 deep), 0.13 thick, its top sloping from 0.8 at the back to the arms
    bm = bmesh.new(); n = 36; rings = []
    for i in range(n + 1):
        u = -1 + 2 * i / n; ang = u * math.radians(125)
        cx, cy = 0.4 * math.sin(ang), 0.06 + 0.36 * math.cos(ang)
        if abs(ang) > math.radians(90): cy = 0.06 + 0.36 * math.cos(ang) - 0.0
        top = 0.8 - (0.8 - 0.63) * min(1, max(0, (abs(ang) - math.radians(35)) / math.radians(65))) ** 1.3
        o = Vector((math.sin(ang), math.cos(ang), 0))
        rings.append([bm.verts.new(Vector((cx, cy, z)) + o * dr) for dr, z in ((-0.13, 0.12), (0.0, 0.12), (0.0, top), (-0.13, top))])
    for a, b in zip(rings, rings[1:]):
        for k in range(4): bm.faces.new((a[k], b[k], b[(k + 1) % 4], a[(k + 1) % 4]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    sh = cine._mesh_obj('tchair_shell', bm, M['chenille'], col, smooth=True); sh['lm'] = 'furn'
    md = sh.modifiers.new('bevel', 'BEVEL'); md.width = 0.04; md.segments = 4; md.limit_method = 'ANGLE'; md.angle_limit = math.radians(40)
    parts.append(sh)
    parts.append(rounded_slab('tchair_base', 0.68, 0.62, 0.16, 0.2, (0, -0.06, 0.2), M['chenille'], edge_bev=0.03, collection=col, lm='furn'))
    parts.append(rounded_slab('tchair_cushion', 0.58, 0.58, 0.12, 0.16, (0, -0.1, st - 0.06), M['chenille'], edge_bev=0.04, collection=col, lm='furn'))
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(cyl(f'tchair_leg{sx}{sy}', 0.024, 0.13, (sx * 0.28, -0.04 + sy * 0.27, 0.065), M['mahogany'], r2=0.016, seg=12, collection=col, lm='furn'))
            parts[-1].rotation_euler = (0, 0, 0)
    for o in parts: place(o, _chair_frame(p, f))


def glass_table(M, col):
    """The round glass table between them, its base of thin brushed-steel rings and rods; the steel tissue box."""
    c = C
    # the top: clear glass reads, at this scale, as its green edge (a glass slab drawn opaque would be a dark disc)
    tube('table_glass_edge', circle((c.x, c.y, 0.446), 0.455, (1, 0, 0), (0, 1, 0), n=64), 0.0065, M['glass_edge'], col, closed=True, seg=6, lm='furn')
    for k, (z, r) in enumerate(((0.43, 0.36), (0.3, 0.335), (0.26, 0.335), (0.012, 0.36))):
        tube(f'table_ring{k}', circle((c.x, c.y, z), r, (1, 0, 0), (0, 1, 0), n=48), 0.006, M['steel'], col, closed=True, seg=8, lm='furn')
    for k in range(6):
        a = k * math.pi / 3 + 0.2; x, y = c.x + 0.345 * math.cos(a), c.y + 0.345 * math.sin(a)
        cyl(f'table_rod{k}', 0.006, 0.43, (x, y, 0.225), M['steel'], seg=8, collection=col, lm='furn')
    box('tissue_box', (0.13, 0.13, 0.11), (c.x + 0.04, c.y + 0.02, 0.452 + 0.055), M['steel'], bev=0.006, collection=col, lm='furn')
    t = lathe('tissue', [(0.0, 0.0), (0.03, 0.0), (0.02, 0.03), (0.035, 0.05), (0.0, 0.06)], M['tissue'], loc=(c.x + 0.04, c.y + 0.02, 0.56), seg=8, collection=col, lm='furn')
    t.scale = (1.0, 0.5, 1.0)


def rug(M, col):
    """The big rug under the chairs and the table, its long side along the two chairs."""
    p, f = chair_at('melfi')
    r = uv_rect(box('rug', (3.6, 2.7, 0.008), (0, 0, 0.004), M['rug'], bev=0.002, collection=col, lm='arch'), axis='z')
    place(r, Matrix.Translation((C.x, C.y, 0)) @ Matrix.Rotation(math.atan2(f.y, f.x), 4, 'Z'))


def desk(M, col):
    """The rosewood desk (its rounded front to the room), a black leather desk chair behind it; the phone, a green
    mug, a blotter, papers, a file rack, a clock and a candle; the arm lamp."""
    a, r = DESK; F = frame_at(a, r) @ Matrix.Rotation(math.pi, 4, 'Z')   # local -y: toward the room's centre
    parts = []
    add = lambda o: (parts.append(o), o)[1]
    add(rounded_slab('desk_top', 1.7, 0.82, 0.04, 0.12, (0, 0, 0.74), M['rosewood'], edge_bev=0.008, collection=col, lm='furn'))
    for s in (-1, 1): add(box(f'desk_pedestal{s}', (0.42, 0.72, 0.7), (s * 0.6, 0.02, 0.37), M['rosewood'], bev=0.006, collection=col, lm='furn'))
    add(box('desk_modesty', (0.8, 0.03, 0.5), (0, -0.3, 0.45), M['rosewood'], bev=0.004, collection=col, lm='furn'))
    add(box('desk_blotter', (0.62, 0.42, 0.006), (0, 0.05, 0.763), M['black_leather'], bev=0.002, collection=col, lm='furn'))
    add(box('desk_folder', (0.24, 0.31, 0.012), (0.04, 0.05, 0.772), M['folder'], rot=(0, 0, 0.1), bev=0.002, collection=col, lm='furn'))
    for k in range(3): add(box(f'desk_paper{k}', (0.21, 0.29, 0.004), (-0.55 + 0.03 * k, -0.05 + 0.02 * k, 0.762 + 0.004 * k), M['paper'], rot=(0, 0, 0.12 * k - 0.1), bev=0, collection=col, lm='furn'))
    add(box('desk_phone', (0.2, 0.22, 0.07), (0.6, -0.08, 0.795), M['black'], bev=0.012, collection=col, lm='furn'))
    add(lathe('desk_mug', [(0.0, 0.0), (0.04, 0.0), (0.042, 0.1), (0.038, 0.1), (0.0, 0.01)], M['mug'], loc=(0.36, -0.12, 0.76), seg=16, collection=col, lm='furn'))
    for k in range(6): add(box(f'desk_rack{k}', (0.004, 0.24, 0.16 + 0.02 * k), (-0.78 + 0.03 * k, 0.18, 0.84 + 0.01 * k), M['steel'], bev=0, collection=col, lm='furn'))
    add(cyl('desk_clock', 0.045, 0.03, (-0.4, 0.25, 0.79), M['chrome'], rot=(math.radians(80), 0, 0), seg=20, collection=col, lm='furn'))
    add(cyl('desk_candle', 0.03, 0.08, (-0.3, 0.3, 0.8), M['candle'], seg=14, collection=col, lm='furn'))
    # the arm lamp: a weighted base, the arm, its head angled down over the blotter, lit
    base = Vector((-0.7, 0.22, 0.76))
    add(cyl('lamp_base', 0.09, 0.02, base + Vector((0, 0, 0.01)), M['steel'], seg=24, collection=col, lm='furn'))
    elbow = base + Vector((0.05, -0.02, 0.48)); headp = base + Vector((0.42, -0.2, 0.36))
    add(tube('lamp_arm', [base + Vector((0, 0, 0.02)), elbow, headp], 0.007, M['steel'], col, seg=8, lm='furn'))
    hd = add(cyl('lamp_shade', 0.05, 0.1, headp + Vector((0.03, -0.01, -0.04)), M['steel'], r2=0.025, seg=20, collection=col, lm='furn'))
    hd.rotation_euler = (math.radians(20), math.radians(-60), 0)
    add(cyl('lamp_glow', 0.043, 0.004, headp + Vector((0.05, -0.02, -0.075)), M['lamp_head'], seg=20, collection=col, lm='furn'))
    # the desk chair, behind: a black leather seat and back on a five-star base
    add(rounded_slab('dchair_seat', 0.52, 0.5, 0.09, 0.06, (0, 0.62, 0.5), M['black_leather'], edge_bev=0.02, collection=col, lm='furn'))
    bk = add(rounded_slab('dchair_back', 0.48, 0.08, 0.5, 0.1, (0, 0, 0), M['black_leather'], edge_bev=0.03, collection=col, lm='furn'))
    bk.location = (0, 0.86, 0.86); bk.rotation_euler.x = math.radians(-12)
    add(cyl('dchair_post', 0.025, 0.36, (0, 0.62, 0.27), M['chrome'], seg=12, collection=col, lm='furn'))
    for k in range(5):
        aa = k * 2 * math.pi / 5; add(box(f'dchair_leg{k}', (0.32, 0.04, 0.03), (0.16 * math.cos(aa), 0.62 + 0.16 * math.sin(aa), 0.06), M['chrome'], rot=(0, 0, aa), bev=0.006, collection=col, lm='furn'))
    for o in parts: place(o, F)
    return F @ Vector((0.45, -0.22, 0.98))   # the lamp's bulb


# ---------------------------------------------------------------- the waiting room
def waiting(M, col):
    """Under the waiting room's window: a blond-wood armchair in oatmeal boucle between two glass side tables, each
    with a drum lamp; magazines; before it, on its pedestal, the green-bronze nude. Returns the lamps' bulbs."""
    y = D / 2 - TW; bulbs = []
    ch = Vector((3.5, y - 0.42, 0)); parts = []
    add = lambda o: (parts.append(o), o)[1]
    add(rounded_slab('wchair_seat', 0.6, 0.56, 0.12, 0.05, (0, 0, 0.4), M['boucle'], edge_bev=0.025, collection=col, lm='furn'))
    bk = add(rounded_slab('wchair_back', 0.6, 0.12, 0.48, 0.05, (0, 0, 0), M['boucle'], edge_bev=0.025, collection=col, lm='furn'))
    bk.location = (0, 0.25, 0.68); bk.rotation_euler.x = math.radians(-10)
    for s in (-1, 1):
        add(box(f'wchair_arm{s}', (0.05, 0.6, 0.035), (s * 0.33, -0.02, 0.6), M['birch'], bev=0.012, collection=col, lm='furn'))
        for sy in (-1, 1): add(box(f'wchair_leg{s}{sy}', (0.04, 0.04, 0.6), (s * 0.33, sy * 0.24, 0.3), M['birch'], bev=0.008, collection=col, lm='furn'))
        add(box(f'wchair_rail{s}', (0.035, 0.5, 0.035), (s * 0.33, 0, 0.32), M['birch'], bev=0.006, collection=col, lm='furn'))
    for o in parts: place(o, Matrix.Translation(ch))
    for k, x in enumerate((ch.x - 0.72, ch.x + 0.72)):
        t = Vector((x, y - 0.32, 0))
        box(f'stable{k}_glass', (0.5, 0.5, 0.012), t + Vector((0, 0, 0.55)), M['glass'], bev=0.002, collection=col, lm='furn')
        for sx in (-1, 1):
            for sy in (-1, 1): box(f'stable{k}_leg{sx}{sy}', (0.018, 0.018, 0.54), t + Vector((sx * 0.23, sy * 0.23, 0.27)), M['steel'], bev=0.002, collection=col, lm='furn')
            box(f'stable{k}_rail{sx}', (0.46, 0.018, 0.018), t + Vector((0, sx * 0.23, 0.53)), M['steel'], bev=0.002, collection=col, lm='furn')
        # the drum lamp: a round base, a slim chrome stem, a linen drum shade
        cyl(f'wlamp{k}_base', 0.075, 0.02, t + Vector((0.05, 0.06, 0.566)), M['chrome'], seg=24, collection=col, lm='furn')
        cyl(f'wlamp{k}_stem', 0.006, 0.42, t + Vector((0.05, 0.06, 0.78)), M['chrome'], seg=8, collection=col, lm='furn')
        sh = cyl(f'wlamp{k}_shade', 0.17, 0.26, t + Vector((0.05, 0.06, 1.05)), M['shade'], seg=40, bev=0.002, collection=col, lm='furn')
        bulbs.append(t + Vector((0.05, 0.06, 1.02)))
        if k == 1:
            for j in range(3): uv_rect(box(f'magazine{j}', (0.21, 0.28, 0.004), t + Vector((-0.08 + 0.02 * j, -0.06, 0.558 + 0.004 * j)), M['magazine'], rot=(0, 0, 0.2 * j - 0.2), bev=0, collection=col, lm='furn'), axis='z')
    return bulbs


def statue_plinth(M, col):
    """The statue's pedestal: a slender column and the round plinth it stands on (the figure is cast from a body)."""
    s = STATUE
    lathe('statue_pedestal', [(0.0, 0.0), (0.2, 0.0), (0.2, 0.03), (0.13, 0.05), (0.11, 0.9), (0.16, 0.93), (0.16, 0.96), (0.0, 0.96)],
          M['patina'], loc=(s.x, s.y, 0), seg=40, collection=col, lm='furn')
    return Vector((s.x, s.y, 0.96))


# ---------------------------------------------------------------- light
WARM = (1.0, 0.8, 0.56)                    # the downlights and lamps, tungsten
DAY = (0.86, 0.95, 0.84)                   # daylight through the woods: faintly green


def lights(niche_top, lamp_bulb, wait_bulbs):
    """The ring of downlights in the soffit, the daylight at the three windows, the niche's light, the bookcase's
    strips, the desk lamp; the waiting room's two lamps and two downlights. Returns the lights."""
    out = []
    def light(name, kind, loc, energy, colour, **kw):
        ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = colour
        for k, v in kw.items(): setattr(ld, k, v)
        ob = cine.link(bpy.data.objects.new(name, ld)); ob.location = loc; out.append(ob)
        if kind in ('AREA', 'SPOT'): ob.visible_camera = False; ob.visible_glossy = False
        return ob
    def aim(ob, d): ob.rotation_euler = Vector(d).to_track_quat('-Z', 'Y').to_euler()
    for k in range(10):   # the downlights: a ring in the soffit, warm cones down the walls and onto the floor
        a = k * 36 + 8; p = on(a, R - 0.7, RH - 0.03)
        aim(light(f'down{k}', 'SPOT', p, 80.0, WARM, spot_size=math.radians(85), spot_blend=0.7, shadow_soft_size=0.04), (0, 0, -1))
    for k in range(5):    # and round the tray, over the chairs
        a = k * 72 + 30; p = on(a, 1.45, RH + 0.2)
        aim(light(f'tray{k}', 'SPOT', p, 70.0, WARM, spot_size=math.radians(90), spot_blend=0.8, shadow_soft_size=0.05), (0, 0, -1))
    for nm, (a, hw), bay in (('nwin', NWIN, 0.32), ('wwin', WWIN, 0.2)):   # daylight beyond the blinds, in the bay
        wdt = math.radians(2 * hw) * (RO + 0.1)
        p = on(a, RO + bay - 0.04, sum(WIN_Z) / 2)
        aim(light(f'day_{nm}', 'AREA', p, 150.0 * wdt, DAY, shape='RECTANGLE', size=wdt * 0.95, size_y=WIN_Z[1] - WIN_Z[0] - 0.05), inward(a) + Vector((0, 0, -0.1)))
    aim(light('day_wait', 'AREA', (3.5, D / 2 + 0.35, sum(WIN_Z) / 2 - 0.05), 150.0, DAY, shape='RECTANGLE', size=1.55, size_y=0.85), (0, -1, -0.12))
    aim(light('niche_light', 'AREA', niche_top, 22.0, WARM, shape='RECTANGLE', size=0.5, size_y=0.22), (0, 0, -1))
    light('desk_lamp', 'POINT', lamp_bulb, 8.0, (1.0, 0.88, 0.7), shadow_soft_size=0.03)
    for k, p in enumerate(wait_bulbs): light(f'wlamp{k}', 'POINT', p, 28.0, WARM, shadow_soft_size=0.06)
    for k, y in enumerate((-1.5, 1.2)):
        aim(light(f'wait_down{k}', 'SPOT', (3.5, y, RH - 0.03), 45.0, WARM, spot_size=math.radians(80), spot_blend=0.6, shadow_soft_size=0.04), (0, 0, -1))
    return out
