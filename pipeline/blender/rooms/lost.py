# LOST · the Swan. Station 3 of the DHARMA Initiative, underground: the computer room under its geodesic dome (dark
# struts, plaster panels washed green by hidden lights, mainframes and tape drives along the wall, the terminal on its
# desk and the counter above it), opening onto the living room (cream tiles set with terracotta, warm plaster, round
# concrete columns) and its booth under the oval window, the blinds lit from behind. The dome and the module's back and
# left walls are cut through at three metres, showing the concrete they are cast in.
import math, os, random
import bpy, bmesh
from mathutils import Vector, Matrix
import cine
from cine import box, cyl, material, lathe, place, slab_profile, rounded_slab

W, D, H = 9.6, 7.6, 3.0
T = 0.14                                   # wall thickness
BACK = D / 2 - T                           # inner face of the back wall
TEX = os.path.join(cine.OUT, 'textures', 'lost')
tx = lambda n: os.path.join(TEX, n)
PH = lambda n: os.path.join(cine.CACHE, 'polyhaven', n, f'{n}_1k.gltf')

# the dome: a 4-frequency geodesic hemisphere on a low riser wall; only its left and back reach the module's walls
DOME_C = Vector((-1.26, 0.26))             # centre, in plan
DOME_R = 3.4                               # radius (riser and sphere)
RISER = 0.9                                # where the dome springs from its riser
X0 = 0.5                                   # the cut through the dome meets the back wall here
THETA_A = math.atan2(D / 2 - DOME_C.y, X0 - DOME_C.x)                 # the cut at the back (the living room's side)
THETA_B = math.atan2(-D / 2 - DOME_C.y, -W / 2 - DOME_C.x) % (2 * math.pi)   # the cut at the front-left corner
STRUT_W, STRUT_D = 0.075, 0.11             # struts: width, depth inward from the panels

# the computer corner (Desmond faces the dome, -x)
DESK = (-4.52, -3.84, 0.26)                # back edge x, front edge x, centre y
DESK_TOP = 0.76
TERM_X = -4.07                             # the terminal's centre (its keys 0.35 m before Desmond)
TERM = Matrix.Translation((TERM_X, 0.28, 0.76)) @ Matrix.Rotation(math.pi / 2, 4, 'Z')   # its frame: local -y faces Desmond (+x)
CODE = '4 8 15 16 23 42'


def key_local(row, col):
    """A key's top in the terminal's frame: row 0 the numbers (back), 1-2 letters, 3 the space bar (front, col ignored)."""
    if row == 3: return (-0.01, -0.176, 0.083)
    return (-0.158 + col * 0.0255 + row * 0.008, -0.092 - row * 0.028, 0.095 - row * 0.004)


def key_world(ch):
    """Where a character's key is, in the room: digits on the number row, a space on the bar, Enter at the right."""
    if ch == ' ': p = key_local(3, 0)
    elif ch == '\n': p = key_local(2, 12)
    else: p = key_local(0, (int(ch) - 1) % 10)
    return TERM @ Vector(p)
SEATS = {'desmond': (-3.56, 0.28, -math.pi / 2)}                        # x, y, facing (z rotation; a seat's front is -y)
SEAT_TOP = 0.49                            # the table clips sit a seated pelvis 0.58 m up: the stool and the benches
STAND = {'jack': ((-2.78, -0.36), (-4.1, 0.22)), 'locke': ((-2.86, 0.86), (-4.1, 0.34))}    # where, looking at

# the booth on the living side: two benches facing across a table, under the oval window
BX = 2.75                                  # its centre line
BOOTH = (1.6, 3.9, 2.1)                    # inner faces of the two piers, and their fronts (y)
WIN = (BX, 1.42, 1.66, 0.78)               # oval window: centre x, centre z, width, height
TABLE = (BX, 0.80, 1.22)                   # x, width, length out from the wall
TABLE_TOP = 0.775
SEATS.update({'ben': (1.89, 2.98, math.pi / 2), 'kate': (3.61, 2.90, -math.pi / 2)})
MUGS = {'ben': (2.44, 2.84, -1), 'kate': (3.06, 3.04, 1)}              # where each puts their coffee down (x, y), handle toward -y or +y


# ---------------------------------------------------------------- materials
def mats():
    M = {}
    M['tile'] = material('tile', rough=0.42, maps={'color': tx('tile_color.jpg'), 'normal': tx('tile_normal.jpg')}, scale=1.6, normal_strength=0.8, specular=0.5)
    M['conc_floor'] = material('concrete_floor', rough=0.35, maps={'color': tx('concrete_floor_color.jpg'), 'normal': tx('concrete_floor_normal.jpg'), 'rough': tx('concrete_floor_rough.jpg')}, scale=2.4, normal_strength=0.4, specular=0.5)
    M['panel'] = material('dome_panel', rough=0.92, maps={'color': tx('panel_color.jpg'), 'normal': tx('panel_normal.jpg')}, scale=1.6, normal_strength=0.8)
    M['strut'] = material('dome_strut', rough=0.62, maps={'color': tx('strut_color.jpg'), 'normal': tx('wood_normal.jpg')}, scale=1.2, normal_strength=0.4)
    M['concrete'] = material('concrete', rough=0.86, maps={'color': tx('concrete_color.jpg'), 'normal': tx('concrete_normal.jpg')}, scale=2.0, normal_strength=0.6)
    M['plaster'] = material('plaster', rough=0.9, maps={'color': tx('plaster_color.jpg')}, scale=1.5)
    M['kerb'] = material('kerb', (0.22, 0.21, 0.19), rough=0.9)
    M['leather'] = material('booth_leather', rough=0.42, maps={'color': tx('leather_color.jpg'), 'normal': tx('leather_normal.jpg')}, scale=0.5, normal_strength=0.5, coat=0.3, coat_rough=0.3)
    M['wood'] = material('table_wood', rough=0.35, maps={'color': tx('table_wood_color.jpg'), 'normal': tx('wood_normal.jpg')}, scale=0.9, normal_strength=0.3, coat=0.4, coat_rough=0.2)
    M['dark_wood'] = material('dark_wood', rough=0.5, maps={'color': tx('strut_color.jpg')}, scale=0.6)
    M['laminate'] = material('desk_laminate', (0.42, 0.50, 0.52), rough=0.38, specular=0.45)
    M['edge'] = material('desk_edge', (0.05, 0.05, 0.05), rough=0.5)
    M['steel'] = material('steel', (0.56, 0.57, 0.58), rough=0.3, metal=1.0)
    M['chrome'] = material('chrome', (0.8, 0.8, 0.8), rough=0.12, metal=1.0)
    M['beige'] = material('beige_plastic', (0.58, 0.54, 0.44), rough=0.45)
    M['cabinet'] = material('cabinet_paint', (0.27, 0.28, 0.26), rough=0.5)
    M['cabinet_dark'] = material('cabinet_dark', (0.09, 0.095, 0.09), rough=0.5)
    M['bezel'] = material('bezel', (0.06, 0.05, 0.045), rough=0.45)
    M['black'] = material('black_rubber', (0.025, 0.025, 0.025), rough=0.7)
    M['vinyl'] = material('black_vinyl', (0.03, 0.03, 0.03), rough=0.35, coat=0.3)
    M['screen'] = material('screen_glass', (0.01, 0.015, 0.012), rough=0.1)      # the web draws the screens live
    M['blinds'] = material('blinds', (0.74, 0.66, 0.5), rough=0.42)
    M['lightbox'] = material('lightbox', (1.0, 0.85, 0.62), rough=0.9, emission=(1.0, 0.78, 0.5), emission_strength=4.0)
    M['shade'] = material('lampshade', (0.82, 0.62, 0.38), rough=0.8, emission=(1.0, 0.72, 0.42), emission_strength=3.0)
    M['film_can'] = material('film_can', (0.62, 0.63, 0.62), rough=0.28, metal=1.0)
    M['ceramic_y'] = material('mug_yellow', (0.72, 0.56, 0.14), rough=0.18, coat=0.6)
    M['ceramic_g'] = material('bowl_green', (0.22, 0.42, 0.22), rough=0.18, coat=0.6)
    M['ceramic_w'] = material('mug_cream', (0.78, 0.74, 0.64), rough=0.18, coat=0.6)
    M['coffee'] = material('coffee', (0.03, 0.015, 0.008), rough=0.05)
    M['paper'] = material('paper', (0.82, 0.8, 0.74), rough=0.85)
    M['logo'] = material('logo_wood', (0.30, 0.20, 0.12), rough=0.5, coat=0.3)
    M['enamel'] = material('lamp_enamel', (0.02, 0.022, 0.022), rough=0.3, coat=0.5)
    M['felt'] = material('table_tennis', (0.03, 0.17, 0.11), rough=0.6)
    M['white_line'] = material('white_line', (0.8, 0.8, 0.76), rough=0.6)
    M['net'] = material('net', (0.06, 0.06, 0.06), rough=0.8)
    M['rubber_red'] = material('rubber_red', (0.45, 0.03, 0.03), rough=0.55)
    M['record'] = material('record', (0.01, 0.01, 0.01), rough=0.2, coat=0.6)
    M['section'] = material('section', (0.03, 0.028, 0.026), rough=0.92)          # where the module's top cuts through
    M['ceiling'] = material('ceiling', rough=0.9, maps={'color': tx('ceiling_color.jpg')}, scale=1.4)
    return M


# ---------------------------------------------------------------- helpers
def section(objs, M):
    """The faces the module's top cuts through (the concrete round the dome, the wall and pier tops), dark, as the cut
    face of a model is drawn."""
    for ob in objs:
        if not ob.name.startswith(('back_', 'left_')): continue
        me = ob.data
        if M['section'].name not in [m.name for m in me.materials if m]: me.materials.append(M['section'])
        k = [m.name if m else '' for m in me.materials].index(M['section'].name)
        for f in me.polygons:
            c = sum((me.vertices[i].co for i in f.vertices), Vector()) / len(f.vertices)
            if f.normal.z > 0.9 and c.z > H - 0.004: f.material_index = k


def dome_point(theta, r, z):
    return Vector((DOME_C.x + r * math.cos(theta), DOME_C.y + r * math.sin(theta), z))


def sphere_r(z):
    """The dome's radius at height z (the riser below its spring)."""
    return DOME_R if z <= RISER else math.sqrt(max(DOME_R ** 2 - (z - RISER) ** 2, 0.0))


def in_sector(p):
    a = math.atan2(p.y - DOME_C.y, p.x - DOME_C.x) % (2 * math.pi)
    return THETA_A - 1e-6 <= a <= THETA_B + 1e-6


def clip_to_sector(bm, top=H):
    """Cut a mesh to the part of the dome that stands: between the two cuts, below the module's top."""
    c3 = Vector((DOME_C.x, DOME_C.y, 0))
    for theta, keep_positive in ((THETA_A, True), (THETA_B, False)):
        n = Vector((-math.sin(theta), math.cos(theta), 0))
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=c3, plane_no=n, clear_inner=keep_positive, clear_outer=not keep_positive)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, top), plane_no=(0, 0, 1), clear_outer=True)


def geodesic():
    """The dome's vertices and faces at room scale: a 4V icosphere's upper half, turned so the computer desk faces the
    middle of a panel, scaled to the dome and set on its riser."""
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if min(v.co.z for v in f.verts) < -1e-4], context='FACES')
    eq = [v for v in bm.verts if abs(v.co.z) < 1e-4]
    a0 = min(math.atan2(v.co.y, v.co.x) % (2 * math.pi / 20) for v in eq)
    rot = Matrix.Rotation(math.radians(9) - a0, 3, 'Z')            # equator vertices at 9 + 18k degrees: 171 and 189 flank the desk
    for v in bm.verts: v.co = Vector((DOME_C.x, DOME_C.y, RISER)) + rot @ (v.co * DOME_R)
    return bm


def equator():
    """The riser's 20-gon (the dome's equator vertices), in order of angle, at z = 0."""
    return [dome_point(math.radians(9 + 18 * k), DOME_R, 0.0) for k in range(20)]


def sector_polyline(pts, inset=0.0):
    """The part of a closed ring (about the dome's centre) inside the standing sector, cut exactly at its ends; each
    point moved `inset` toward the centre."""
    out = []
    n = len(pts)
    ang = lambda p: math.atan2(p.y - DOME_C.y, p.x - DOME_C.x) % (2 * math.pi)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        if in_sector(a): out.append((ang(a), a))
        for theta in (THETA_A, THETA_B):
            # where the edge a-b crosses the ray at theta
            u = Vector((math.cos(theta), math.sin(theta), 0)); nrm = Vector((-u.y, u.x, 0))
            da, db = (a - Vector((DOME_C.x, DOME_C.y, a.z))).dot(nrm), (b - Vector((DOME_C.x, DOME_C.y, b.z))).dot(nrm)
            if da * db < 0:
                p = a.lerp(b, da / (da - db))
                if (p - Vector((DOME_C.x, DOME_C.y, p.z))).dot(u) > 0: out.append((theta, p))
    out.sort(key=lambda t: t[0])
    res = []
    for a, p in out:
        d = Vector((DOME_C.x - p.x, DOME_C.y - p.y, 0)).normalized()
        res.append(p + d * inset)
    return res


def ring_sweep(name, ring, profile, mat, col, **props):
    """A profile [(inward, up)] swept along an open polyline about the dome (a riser, a cove), capped at both ends."""
    bm = bmesh.new(); rows = []
    for p in ring:
        d = Vector((DOME_C.x - p.x, DOME_C.y - p.y, 0)).normalized()
        rows.append([bm.verts.new(p + d * i + Vector((0, 0, u))) for i, u in profile])
    n = len(profile)
    for r0, r1 in zip(rows, rows[1:]):
        for k in range(n): bm.faces.new((r0[k], r0[(k + 1) % n], r1[(k + 1) % n], r1[k]))
    bm.faces.new(rows[0]); bm.faces.new(list(reversed(rows[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = cine._mesh_obj(name, bm, mat, col, smooth=False)
    for k, v in props.items(): ob[k] = v
    return ob


def screen(name, w, h, mat, col, bulge=0.0, **props):
    """A face the web draws live (role 'screen'): a plane in x-z facing -y, 0..1 UVs across it (u along +x, v up),
    domed by `bulge` like a CRT."""
    bm = bmesh.new(); nx, ny = 12, 9; vs = []
    for j in range(ny + 1):
        for i in range(nx + 1):
            u, v = i / nx, j / ny
            vs.append(bm.verts.new(((u - 0.5) * w, -bulge * (1 - (2 * u - 1) ** 2) * (1 - (2 * v - 1) ** 2), (v - 0.5) * h)))
    uvl = bm.loops.layers.uv.new('UVMap')
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i; f = bm.faces.new((vs[a], vs[a + 1], vs[a + nx + 2], vs[a + nx + 1]))
            for loop, (du, dv) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))): loop[uvl].uv = ((i + du) / nx, (j + dv) / ny)
    ob = cine._mesh_obj(name, bm, mat, col, smooth=True); ob['role'] = 'screen'
    for k, v in props.items(): ob[k] = v
    return ob


# ---------------------------------------------------------------- the dome
def dome(M, arch, furn):
    """Panels, struts and hubs, the riser with its cove (the hidden lights wash the panels from it), the concrete the
    dome is cast in, cut flat at the top of the module."""
    bm = geodesic()
    edges = [(e.verts[0].co.copy(), e.verts[1].co.copy()) for e in bm.edges]
    hubs = [v.co.copy() for v in bm.verts if v.co.z > RISER + 0.01]
    c3 = Vector((DOME_C.x, DOME_C.y, RISER))
    # the panels, facing in
    clip_to_sector(bm)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    panels = cine._mesh_obj('left_dome_panels', bm, M['panel'], arch, smooth=False); panels['lm'] = 'arch'
    # the struts: a beam on every edge, standing in from the panels, and a hub where they meet
    sb = bmesh.new()
    def beam(a, b, w, d):
        n = ((a + b) / 2 - c3).normalized(); e = (b - a).normalized(); s = e.cross(n).normalized()
        vs = [sb.verts.new(p + s * ds + n * dr) for p in (a, b) for ds, dr in ((-w / 2, 0.01), (w / 2, 0.01), (w / 2, -d), (-w / 2, -d))]
        for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)): sb.faces.new([vs[i] for i in f])
    for a, b in edges: beam(a, b, STRUT_W, STRUT_D)
    for p in hubs:
        n = (p - c3).normalized(); t1 = n.orthogonal().normalized(); t2 = n.cross(t1)
        ring_o = [sb.verts.new(p + (t1 * math.cos(k * math.pi / 4) + t2 * math.sin(k * math.pi / 4)) * 0.075 - n * (STRUT_D + 0.012)) for k in range(8)]
        ring_i = [sb.verts.new(p + (t1 * math.cos(k * math.pi / 4) + t2 * math.sin(k * math.pi / 4)) * 0.075 + n * 0.005) for k in range(8)]
        sb.faces.new(ring_o)
        for k in range(8): sb.faces.new((ring_o[k], ring_i[k], ring_i[(k + 1) % 8], ring_o[(k + 1) % 8]))
    bmesh.ops.recalc_face_normals(sb, faces=sb.faces)
    clip_to_sector(sb, top=H - 0.09)
    struts = cine._mesh_obj('left_dome_struts', sb, M['strut'], arch, smooth=False); struts['lm'] = 'arch'
    # the riser, and the cove along its top: a ledge with an upstand that hides the strip lights
    ring = sector_polyline(equator())
    ring_sweep('left_dome_riser', ring, [(0.0, 0.0), (0.02, 0.0), (0.02, RISER), (0.0, RISER)], M['concrete'], arch, lm='arch')
    ring_sweep('left_dome_cove', ring, [(0.0, RISER - 0.07), (0.24, RISER - 0.07), (0.24, RISER + 0.13), (0.205, RISER + 0.13), (0.205, RISER - 0.02), (0.0, RISER - 0.02)],
               M['concrete'], arch, lm='arch')
    poche(M, arch)


def _ray_to_module(theta):
    """Where the ray from the dome's centre at angle theta meets the module's outline (the back or left side)."""
    u = Vector((math.cos(theta), math.sin(theta)))
    ts = []
    if u.y > 1e-9: ts.append((D / 2 - DOME_C.y) / u.y)
    if u.y < -1e-9: ts.append((-D / 2 - DOME_C.y) / u.y)
    if u.x < -1e-9: ts.append((-W / 2 - DOME_C.x) / u.x)
    if u.x > 1e-9: ts.append((W / 2 - DOME_C.x) / u.x)
    t = min(t for t in ts if t > 0)
    return DOME_C + u * t


def poche(M, col):
    """The concrete around the dome, between it and the module's back and left sides, cut flat at the top: its inner
    face just behind the panels, a ring beam over their cut edges, radial faces where the dome is cut away."""
    corner_back = math.atan2(D / 2 - DOME_C.y, -W / 2 - DOME_C.x)
    thetas = sorted(set([THETA_A + (THETA_B - THETA_A) * i / 90 for i in range(91)] + [corner_back]))
    lip = sphere_r(H - 0.09) - 0.26                  # over the struts' cut tops
    prof = [(sphere_r(0) + 0.03, 0.0), (DOME_R + 0.03, RISER)]
    for k in range(1, 9):
        z = RISER + (H - 0.09 - RISER) * k / 8; prof.append((sphere_r(z) + 0.03, z))
    prof += [(lip, H - 0.09), (lip, H)]
    bm = bmesh.new(); slices = []
    for th in thetas:
        o = _ray_to_module(th)
        inner = [bm.verts.new(dome_point(th, r, z)) for r, z in prof]
        outer = [bm.verts.new((o.x, o.y, H)), bm.verts.new((o.x, o.y, 0.0))]
        slices.append(inner + outer)
    n = len(slices[0])
    for s0, s1 in zip(slices, slices[1:]):
        for k in range(n): bm.faces.new((s0[k], s1[k], s1[(k + 1) % n], s0[(k + 1) % n]))
    bm.faces.new(slices[0]); bm.faces.new(list(reversed(slices[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = cine._mesh_obj('left_poche', bm, M['concrete'], col, smooth=False); ob['lm'] = 'arch'
    return ob


# ---------------------------------------------------------------- the shell of the living side
def shell(M, arch, phantom):
    box('subfloor', (W, D, 0.03), (0, 0, -0.027), M['kerb'], bev=0, collection=arch, lm='arch')
    box('floor', (W - 0.02, D - 0.02, 0.02), (0, 0, -0.01), M['tile'], bev=0.0, collection=arch, lm='arch')
    # the dome's floor: dark concrete inside its footprint, a steel strip where it meets the tiles
    bm = bmesh.new(); ring = [dome_point(math.radians(9 + 18 * k), DOME_R - 0.01, 0.003) for k in range(20)]
    bm.faces.new([bm.verts.new(p) for p in ring])
    cine._mesh_obj('dome_floor', bm, M['conc_floor'], arch, smooth=False)['lm'] = 'arch'
    sb = bmesh.new()
    for k in range(20):
        a, b = ring[k], ring[(k + 1) % 20]
        if in_sector((a + b) / 2): continue
        d0 = Vector((a.x - DOME_C.x, a.y - DOME_C.y, 0)).normalized(); d1 = Vector((b.x - DOME_C.x, b.y - DOME_C.y, 0)).normalized()
        q = [sb.verts.new(p) for p in (a - d0 * 0.012 + Vector((0, 0, 0.001)), b - d1 * 0.012 + Vector((0, 0, 0.001)), b + d1 * 0.012 + Vector((0, 0, 0.001)), a + d0 * 0.012 + Vector((0, 0, 0.001)))]
        sb.faces.new(q)
    cine._mesh_obj('dome_threshold', sb, M['steel'], arch, smooth=False)['lm'] = 'arch'
    # the back wall of the living side, with the booth's oval window cut through it
    wall = box('back_wall', (W / 2 - X0 + 0.2, T, H), ((W / 2 + X0 - 0.2) / 2, D / 2 - T / 2, H / 2), M['plaster'], bev=0, collection=arch, lm='arch')
    cut = _stadium_prism('window_cut', WIN[2], WIN[3], 0.6, (WIN[0], D / 2 - T / 2, WIN[1]), arch)
    md = wall.modifiers.new('window', 'BOOLEAN'); md.object = cut; md.operation = 'DIFFERENCE'; md.solver = 'EXACT'
    cine.apply_modifiers(wall); bpy.data.objects.remove(cut, do_unlink=True)
    box('back_skirting', (W / 2 - X0, 0.014, 0.1), ((W / 2 + X0) / 2, BACK - 0.007, 0.05), M['kerb'], bev=0.002, collection=arch, lm='arch')
    # a round concrete column where the dome's cut meets the back wall
    cyl('column_back', 0.3, H, (X0, BACK - 0.34, H / 2), M['concrete'], seg=48, bev=0, collection=arch, lm='arch')
    # the cut-away: front and right walls end in a low kerb
    box('kerb_front', (W, T, 0.22), (0, -D / 2 + T / 2, 0.11), M['kerb'], bev=0.002, collection=arch, lm='arch')
    box('kerb_right', (T, D - 2 * T, 0.22), (W / 2 - T / 2, 0, 0.11), M['kerb'], bev=0.002, collection=arch, lm='arch')
    # phantoms: the ceiling and the missing walls, for the bounce light (never exported)
    box('ceiling', (W, D, 0.04), (0, 0, H + 0.02), M['ceiling'], bev=0, collection=phantom, bake_only=1)
    box('front_wall', (W, T, H - 0.22), (0, -D / 2 + T / 2, 0.22 + (H - 0.22) / 2), M['plaster'], bev=0, collection=phantom, bake_only=1)
    box('right_wall', (T, D, H - 0.22), (W / 2 - T / 2, 0, 0.22 + (H - 0.22) / 2), M['plaster'], bev=0, collection=phantom, bake_only=1)


def _stadium(w, h, n=24):
    """An oval with straight top and bottom (a stadium), w wide and h high, about the origin, in (x, z)."""
    r = h / 2; cx = w / 2 - r; pts = []
    for s, c in ((1, cx), (-1, -cx)):
        for i in range(n + 1):
            a = -math.pi / 2 + math.pi * i / n
            pts.append((c + s * r * math.cos(a), s * r * math.sin(a)))
    return pts


def _stadium_prism(name, w, h, depth, loc, col, mat=None):
    bm = bmesh.new(); pts = _stadium(w, h)
    a = [bm.verts.new((x, -depth / 2, z)) for x, z in pts]; b = [bm.verts.new((x, depth / 2, z)) for x, z in pts]
    bm.faces.new(a); bm.faces.new(list(reversed(b)))
    for i in range(len(pts)): bm.faces.new((a[i], a[(i + 1) % len(pts)], b[(i + 1) % len(pts)], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = cine._mesh_obj(name, bm, mat, col, smooth=False); ob.location = loc
    return ob


# ---------------------------------------------------------------- the booth
def booth(M, arch, furn):
    """Two piers out from the back wall, an arched header between them, the oval window (a deep frame, venetian
    blinds, a light box behind: the window is false, as everything down here), the benches and the table."""
    x0, x1, yf = BOOTH
    box('back_pier', (0.5, BACK - yf, H), (x0 - 0.25, (BACK + yf) / 2, H / 2), M['plaster'], bev=0.004, collection=arch, lm='arch')
    # on the open side, a slim post carries the header (a pier there would hide the bench from the room)
    box('back_post', (0.12, 0.12, H), (x1 + 0.06, yf + 0.11, H / 2), M['dark_wood'], bev=0.006, collection=arch, lm='arch')
    # the header: its underside an elliptic arch from pier to post
    span = x1 - x0; pts = [(x0, 2.3), (x0, H), (x1 + 0.12, H), (x1 + 0.12, 2.3), (x1, 2.3)]
    pts += [(BX + span / 2 * math.cos(math.pi * i / 24), 2.3 + 0.32 * math.sin(math.pi * i / 24)) for i in range(1, 24)]
    hd = slab_profile('back_header', pts, 'y', 0.22, [M['plaster'], M['plaster']], arch, bev=0.006, lm='arch')
    hd.location = (0, yf + 0.11, 0)
    # the window: a moulded oval frame standing out of the wall, a deep reveal, blinds, the lit box behind
    cx, cz, w, h = WIN
    fr = _stadium_frame('window_frame', w + 0.16, h + 0.16, w, h, 0.05, (cx, BACK - 0.025, cz), M['wood'], furn); fr['lm'] = 'furn'
    rv = _stadium_frame('window_reveal', w + 0.002, h + 0.002, w - 0.02, h - 0.02, T - 0.004, (cx, D / 2 - T / 2, cz), M['plaster'], furn); rv['lm'] = 'furn'
    r = h / 2 - 0.012
    for k in range(int((h - 0.03) / 0.042)):
        z = cz - h / 2 + 0.025 + k * 0.042; dz = abs(z - cz)
        half = (w / 2 - r) + math.sqrt(max(r * r - dz * dz, 0.0)) - 0.012
        sl = box(f'blind{k}', (2 * half, 0.034, 0.0025), (cx, D / 2 - T + 0.05, z), M['blinds'], rot=(math.radians(28), 0, 0), bev=0, collection=furn, lm='furn')
    for s in (-1, 1): cyl(f'blind_cord{s}', 0.0015, h - 0.04, (cx + s * w * 0.3, D / 2 - T + 0.035, cz), M['blinds'], seg=6, bev=0, collection=furn, lm='furn')
    _stadium_prism('window_light', w + 0.02, h + 0.02, 0.01, (cx, D / 2 - 0.03, cz), furn, M['lightbox'])
    # the benches: a plinth, a seat, a tall back against the pier, all in red leather
    for who, sx in (('ben', -1), ('kate', 1)):
        face = x0 if sx < 0 else x1; o = -sx                      # into the booth
        L0, L1 = 2.28, BACK
        yc, ln = (L0 + L1) / 2, L1 - L0
        box(f'bench_{who}_plinth', (0.5, ln, 0.1), (face + o * 0.27, yc, 0.05), M['dark_wood'], bev=0.006, collection=furn, lm='furn')
        box(f'bench_{who}_base', (0.48, ln - 0.02, 0.34), (face + o * 0.27, yc, 0.27), M['leather'], bev=0.02, seg=3, collection=furn, lm='furn')
        box(f'bench_{who}_seat', (0.5, ln - 0.03, 0.09), (face + o * 0.28, yc, SEAT_TOP - 0.045), M['leather'], bev=0.035, seg=4, collection=furn, lm='furn')
        bk = box(f'bench_{who}_back', (0.16, ln - 0.03, 0.62), (face + o * 0.095, yc, SEAT_TOP + 0.3), M['leather'], bev=0.045, seg=4, collection=furn, lm='furn')
        bk.rotation_euler.y = sx * math.radians(8)
        box(f'bench_{who}_cap', (0.2, ln, 0.05), (face + o * 0.1, yc, SEAT_TOP + 0.64), M['dark_wood'], bev=0.01, collection=furn, lm='furn')
    # the table: a dark top with its corners cut where it meets the room, on a single column and foot
    tw, tl = TABLE[1], TABLE[2]; y0 = BACK; c = 0.16
    pts = [(BX - tw / 2, y0), (BX + tw / 2, y0), (BX + tw / 2, y0 - tl + c), (BX + tw / 2 - c, y0 - tl), (BX - tw / 2 + c, y0 - tl), (BX - tw / 2, y0 - tl + c)]
    top = slab_profile('table_top', [(x, y) for x, y in pts], 'z', 0.035, [M['wood'], M['wood']], furn, bev=0.006, lm='furn')
    top.location.z = 0.74 + 0.0175
    cyl('table_column', 0.05, 0.7, (BX, y0 - tl / 2, 0.37), M['steel'], seg=24, collection=furn, lm='furn')
    cyl('table_foot', 0.24, 0.025, (BX, y0 - tl / 2, 0.0125), M['steel'], seg=40, bev=0.006, collection=furn, lm='furn')
    return _table_things(M, furn)


def _stadium_frame(name, w_out, h_out, w_in, h_in, depth, loc, mat, col):
    """A flat ring between two stadiums (a window frame), `depth` thick along y."""
    bm = bmesh.new(); po, pi = _stadium(w_out, h_out), _stadium(w_in, h_in); n = len(po)
    rows = [[bm.verts.new((x, y, z)) for x, z in pts] for pts, y in ((po, -depth / 2), (pi, -depth / 2), (pi, depth / 2), (po, depth / 2))]
    for r0, r1 in zip(rows, rows[1:] + rows[:1]):
        for i in range(n): bm.faces.new((r0[i], r0[(i + 1) % n], r1[(i + 1) % n], r1[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = cine._mesh_obj(name, bm, mat, col, smooth=False); ob.location = loc
    return ob


def mug(name, x, y, z, mat, M, col, live=False, handle=(1, 0), **props):
    """A diner mug: a thick body, a loop handle on the side `handle` points to (x, y), coffee in it."""
    parts = [lathe(f'{name}_body', [(0.0, 0.0), (0.036, 0.0), (0.04, 0.006), (0.042, 0.09), (0.037, 0.092), (0.034, 0.012), (0.0, 0.012)], mat, loc=(x, y, z), seg=28, collection=col)]
    a = math.atan2(handle[1], handle[0])
    hd = cyl(f'{name}_handle', 0.026, 0.012, (x + math.cos(a) * 0.042, y + math.sin(a) * 0.042, z + 0.048), mat, rot=(math.pi / 2, 0, a), seg=16, bev=0.003, collection=col)
    hd.scale = (0.8, 1.0, 1.0)
    parts.append(hd)
    parts.append(cyl(f'{name}_coffee', 0.034, 0.002, (x, y, z + 0.078), M['coffee'], seg=24, bev=0, collection=col))
    for o in parts:
        for k, v in props.items(): o[k] = v
        if not live: o['lm'] = 'furn'
    return parts


def _table_things(M, furn):
    """On the table: the lamp by the window, a percolator, a plate of cookies, a tray of papers; the two mugs (live:
    they are picked up). Returns the lamp's bulb."""
    top = TABLE_TOP; yb = BACK - 0.14
    lathe('table_lamp_base', [(0.0, 0.0), (0.07, 0.0), (0.075, 0.015), (0.04, 0.03), (0.055, 0.1), (0.06, 0.16), (0.03, 0.24), (0.018, 0.3), (0.012, 0.42), (0.0, 0.42)],
          M['wood'], loc=(BX - 0.18, yb, top), seg=28, collection=furn, lm='furn')
    sh = cyl('table_lamp_shade', 0.12, 0.17, (BX - 0.18, yb, top + 0.47), M['shade'], r2=0.1, seg=32, bev=0.002, collection=furn, lm='furn')
    lathe('percolator', [(0.0, 0.0), (0.058, 0.0), (0.062, 0.02), (0.05, 0.18), (0.045, 0.2), (0.03, 0.22), (0.012, 0.24), (0.0, 0.25)], M['chrome'], loc=(BX + 0.2, yb - 0.02, top), seg=28, collection=furn, lm='furn')
    cyl('plate', 0.1, 0.012, (BX + 0.02, BACK - 0.62, top + 0.006), M['ceramic_w'], seg=32, bev=0.003, collection=furn, lm='furn')
    rnd = random.Random(3)
    for k in range(5):
        a = rnd.random() * 6.28; r = rnd.random() * 0.05
        cyl(f'cookie{k}', 0.025, 0.008, (BX + 0.02 + math.cos(a) * r, BACK - 0.62 + math.sin(a) * r, top + 0.016 + 0.006 * k), M['logo'], seg=16, bev=0.002, collection=furn, lm='furn')
    box('tray', (0.3, 0.22, 0.02), (BX + 0.12, BACK - 0.34, top + 0.01), M['dark_wood'], rot=(0, 0, 0.15), bev=0.004, collection=furn, lm='furn')
    box('tray_papers', (0.21, 0.15, 0.006), (BX + 0.12, BACK - 0.34, top + 0.022), M['paper'], rot=(0, 0, 0.2), bev=0.001, collection=furn, lm='furn')
    for who, mat in (('ben', M['ceramic_y']), ('kate', M['ceramic_w'])):
        x, y, hs = MUGS[who]
        mug(f'mug_{who}', x, y, top, mat, M, furn, live=True, handle=(0, hs), role='mug', who=who)
    return [Vector((BX - 0.18, yb, top + 0.45))]


# ---------------------------------------------------------------- the computer corner
def computer_corner(M, furn):
    """The desk against the dome's riser, the terminal (its screen drawn live), the arm lamp, film cans, a bowl and a
    cup; the counter on its box above, its digits drawn live; Desmond's stool. Returns the lamp's bulb."""
    bx, fx, yc = DESK; dw = 1.9; dd = bx - fx
    rounded_slab('desk_top', -dd, dw, 0.035, 0.015, ((bx + fx) / 2, yc, DESK_TOP - 0.0175), M['laminate'], collection=furn, lm='furn')
    box('desk_edge', (0.012, dw, 0.04), (fx - 0.006, yc, DESK_TOP - 0.02), M['edge'], bev=0.003, collection=furn, lm='furn')
    for sy in (-1, 1):
        for sx, x in ((0, bx + 0.05), (1, fx - 0.06)):
            box(f'desk_leg{sy}{sx}', (0.04, 0.04, DESK_TOP - 0.035), (x, yc + sy * (dw / 2 - 0.05), (DESK_TOP - 0.035) / 2), M['steel'], bev=0.004, collection=furn, lm='furn')
    box('desk_modesty', (0.02, dw - 0.12, 0.42), (bx + 0.06, yc, DESK_TOP - 0.25), M['cabinet'], bev=0.003, collection=furn, lm='furn')
    box('desk_drawers', (dd - 0.1, 0.42, DESK_TOP - 0.1), ((bx + fx) / 2 + 0.02, yc - dw / 2 + 0.26, (DESK_TOP - 0.1) / 2 + 0.03), M['cabinet'], bev=0.006, collection=furn, lm='furn')
    for k in range(3):
        box(f'desk_drawer{k}', (0.012, 0.38, 0.17), (fx + 0.035, yc - dw / 2 + 0.26, 0.13 + k * 0.2), M['cabinet'], bev=0.004, collection=furn, lm='furn')
        box(f'desk_pull{k}', (0.015, 0.1, 0.015), (fx + 0.025, yc - dw / 2 + 0.26, 0.2 + k * 0.2), M['chrome'], bev=0.003, collection=furn, lm='furn')
    # the terminal: a keyboard base, the monitor housing on it, a dark bezel, the screen; a disk drive beside it
    t = TERM
    parts = []
    def add(o): parts.append(o); return o
    add(box('term_base', (0.46, 0.44, 0.075), (0, 0.02, 0.0375), M['beige'], bev=0.01, collection=furn, lm='furn'))
    kb = add(box('term_keyboard_well', (0.38, 0.16, 0.012), (0, -0.12, 0.072), M['bezel'], bev=0.003, collection=furn, lm='furn'))
    kb.rotation_euler.x = math.radians(-7)
    keys = bmesh.new()
    for r in range(3):
        for k in range(13):
            (x0, y0, z0), w = key_local(r, k), (0.021 if (r, k) != (2, 12) else 0.034)
            bmesh.ops.create_cube(keys, size=1.0, matrix=Matrix.Translation((x0, y0, z0 - 0.006)) @ Matrix.Diagonal((w, 0.022, 0.012, 1)))
    x0, y0, z0 = key_local(3, 0)
    bmesh.ops.create_cube(keys, size=1.0, matrix=Matrix.Translation((x0, y0, z0 - 0.006)) @ Matrix.Diagonal((0.13, 0.022, 0.012, 1)))
    ko = add(cine._mesh_obj('term_keys', keys, M['bezel'], furn, smooth=False)); ko['lm'] = 'furn'
    add(box('term_monitor', (0.44, 0.34, 0.31), (0, 0.06, 0.075 + 0.155), M['beige'], bev=0.012, collection=furn, lm='furn'))
    add(box('term_bezel', (0.4, 0.012, 0.25), (0, -0.112, 0.075 + 0.155), M['bezel'], bev=0.006, collection=furn, lm='furn'))
    sc_ = add(screen('term_screen', 0.27, 0.2, M['screen'], furn, bulge=0.008, q=0)); sc_.location = (-0.045, -0.119, 0.075 + 0.155)
    add(box('term_badge', (0.07, 0.006, 0.05), (0.13, -0.119, 0.075 + 0.2), M['chrome'], bev=0.002, collection=furn, lm='furn'))
    add(box('term_led', (0.008, 0.006, 0.008), (0.14, -0.119, 0.075 + 0.12), material('led_red', (0.9, 0.05, 0.03), emission=(1, 0.05, 0.02), emission_strength=8), bev=0, collection=furn, lm='furn'))
    add(box('drive', (0.2, 0.3, 0.1), (0.36, 0.06, 0.05), M['beige'], bev=0.008, collection=furn, lm='furn'))
    add(box('drive_slot', (0.13, 0.006, 0.012), (0.36, -0.092, 0.06), M['bezel'], bev=0.002, collection=furn, lm='furn'))
    for o in parts: place(o, t)
    # the arm lamp, bent over the keys; film cans stacked by the wall; a green bowl, a yellow cup
    root, ms = cine.import_gltf(PH('desk_lamp_arm_01'), loc=(bx + 0.1, yc + 0.62, DESK_TOP), rot=(0, 0, math.radians(200)), collection=furn, lm='furn')
    for o in ms:                                                     # black enamel, not Poly Haven's orange
        for sl in o.material_slots:
            if not sl.material.name.endswith('_light'): sl.material = M['enamel']
    for k in range(6):
        cyl(f'film_can{k}', 0.16, 0.026, (bx + 0.2, yc - 0.62, DESK_TOP + 0.013 + k * 0.027), M['film_can'], seg=40, bev=0.003, collection=furn, lm='furn')
    lathe('bowl_green', [(0.0, 0.0), (0.04, 0.0), (0.07, 0.03), (0.085, 0.06), (0.08, 0.062), (0.064, 0.032), (0.0, 0.008)], M['ceramic_g'], loc=(fx + 0.2, yc + 0.68, DESK_TOP), seg=28, collection=furn, lm='furn')
    mug('cup_yellow', fx + 0.17, yc + 0.48, DESK_TOP, M['ceramic_y'], M, furn)
    counter(M, furn)
    # Desmond's stool: five castors, a gas column, a round black seat
    x, y, _ = SEATS['desmond']; sx = x + 0.06
    for k in range(5):
        a = k * 2 * math.pi / 5 + 0.3
        lg = box(f'stool_leg{k}', (0.26, 0.03, 0.025), (sx + math.cos(a) * 0.13, y + math.sin(a) * 0.13, 0.07), M['steel'], rot=(0, 0, a), bev=0.006, collection=furn, lm='furn')
        cyl(f'stool_castor{k}', 0.022, 0.02, (sx + math.cos(a) * 0.25, y + math.sin(a) * 0.25, 0.024), M['black'], rot=(math.pi / 2, 0, a), seg=12, collection=furn, lm='furn')
    cyl('stool_column', 0.025, 0.36, (sx, y, 0.26), M['steel'], seg=16, collection=furn, lm='furn')
    cyl('stool_seat', 0.2, 0.07, (sx, y, SEAT_TOP - 0.035), M['vinyl'], seg=40, bev=0.025, collection=furn, lm='furn')
    return [Vector((bx + 0.27, yc + 0.3, DESK_TOP + 0.55))]


# ---------------------------------------------------------------- the counter
COUNTER = (1.86, 1.05, 0.38)               # centre height, width, height
COUNTER_TURN = math.radians(-25)           # turned from facing the desk toward the room, so the digits read from the case


def counter(M, furn):
    """The counter, as on the set: a steel-framed box on a bracket above the terminal, its face a black panel with five
    windows (three for the minutes, two for the seconds), a split-flap digit in each (the digits are drawn live, and
    flip). It hangs from the dome, facing Desmond's desk."""
    cz, w, h = COUNTER; cy = DESK[2] + 0.02
    back = DOME_C.x - math.sqrt(sphere_r(cz + h / 2) ** 2 - (cy - DOME_C.y) ** 2) + STRUT_D + 0.03 + w / 2 * math.sin(-COUNTER_TURN)
    d = 0.24; x = back + d / 2
    F = Matrix.Translation((x, cy, 0)) @ Matrix.Rotation(COUNTER_TURN, 4, 'Z') @ Matrix.Translation((-x, -cy, 0))
    parts = []
    def box(name, *a, **k):
        o = cine.box(name, *a, **k); parts.append(o); return o
    box('counter_case', (d, w, h), (x, cy, cz), M['cabinet_dark'], bev=0.012, collection=furn, lm='furn')
    for s in (-1, 1):
        box(f'counter_rail{s}', (d + 0.01, w + 0.02, 0.022), (x, cy, cz + s * (h / 2 + 0.006)), M['steel'], bev=0.004, collection=furn, lm='furn')
    parts.append(place(screen('counter_face', w - 0.06, h - 0.07, M['screen'], furn, q=1), Matrix.Translation((x + d / 2 + 0.002, cy, cz)) @ Matrix.Rotation(math.pi / 2, 4, 'Z')))
    # mullions between the windows: the face is set back, the frame stands proud
    fx = x + d / 2 + 0.012
    edges = [-(w - 0.06) / 2] + [e for u0, u1 in _counter_windows() for e in (u0, u1)] + [(w - 0.06) / 2]
    for k in range(0, len(edges), 2):
        a, b = edges[k], edges[k + 1]
        if b - a > 0.002: box(f'counter_mullion{k}', (0.02, b - a, h - 0.07), (fx, cy + (a + b) / 2, cz), M['cabinet_dark'], bev=0.003, collection=furn, lm='furn')
    for s in (-1, 1): box(f'counter_lip{s}', (0.02, w - 0.06, 0.03), (fx, cy, cz + s * (h / 2 - 0.05)), M['cabinet_dark'], bev=0.003, collection=furn, lm='furn')
    box('counter_plate', (0.006, 0.16, 0.022), (x + d / 2 + 0.003, cy, cz - h / 2 + 0.005), M['chrome'], bev=0.002, collection=furn, lm='furn')
    for s in (-1, 1):
        box(f'counter_arm{s}', (0.5, 0.04, 0.04), (back - 0.12, cy + s * (w / 2 - 0.1), cz - h / 2 - 0.03), M['steel'], bev=0.004, collection=furn, lm='furn')
        box(f'counter_stay{s}', (0.04, 0.04, 0.32), (back - 0.25, cy + s * (w / 2 - 0.1), cz - h / 2 - 0.18), M['steel'], bev=0.004, collection=furn, lm='furn')
    for o in parts: o.matrix_basis = F @ o.matrix_basis


COUNTER_TILE, COUNTER_GAP, COUNTER_SEP = 0.118, 0.012, 0.05


def _counter_windows():
    """The five windows across the face (from its centre, toward +y): three minute digits, a gap, two seconds."""
    t, g, sep = COUNTER_TILE, COUNTER_GAP, COUNTER_SEP
    x = -(5 * t + 3 * g + sep) / 2; out = []
    for i in range(5):
        out.append((x, x + t)); x += t + (sep if i == 2 else g)
    return out


# ---------------------------------------------------------------- the mainframes
CABINETS = [(97, 'tape'), (110, 'lamps'), (123, 'tape'), (136, 'lamps'), (149, 'lamps'), (207, 'lamps')]


def mainframes(M, furn):
    """Tall cabinets against the dome: tape drives (two reels behind glass, turning) and panels of lamps (blinking);
    both faces drawn live. Each stands 0.25 m in from the riser, facing the dome's centre."""
    for k, (deg, kind) in enumerate(CABINETS):
        th = math.radians(deg); r = DOME_R - 0.3 - 0.28
        p = dome_point(th, r, 0.0)
        F = Matrix.Translation(p) @ Matrix.Rotation(th - math.pi / 2, 4, 'Z')    # local -y faces the centre
        n = f'cab{k}'; parts = []
        def add(o): parts.append(o); return o
        add(box(f'{n}_body', (0.7, 0.56, 1.72), (0, 0, 0.88), M['cabinet'], bev=0.008, collection=furn, lm='furn'))
        add(box(f'{n}_plinth', (0.66, 0.5, 0.04), (0, 0.01, 0.02), M['black'], bev=0.003, collection=furn, lm='furn'))
        add(box(f'{n}_top', (0.72, 0.58, 0.035), (0, 0, 1.755), M['cabinet_dark'], bev=0.005, collection=furn, lm='furn'))
        if kind == 'tape':
            add(box(f'{n}_window_frame', (0.6, 0.012, 0.6), (0, -0.282, 1.3), M['chrome'], bev=0.004, collection=furn, lm='furn'))
            add(screen(f'{n}_reels', 0.56, 0.56, M['screen'], furn, q=20 + k)).location = (0, -0.289, 1.3)
            add(box(f'{n}_heads', (0.5, 0.03, 0.22), (0, -0.29, 0.86), M['cabinet_dark'], bev=0.006, collection=furn, lm='furn'))
            for j in range(4):
                add(box(f'{n}_btn{j}', (0.05, 0.02, 0.03), (-0.15 + j * 0.1, -0.305, 0.86), M['chrome'], bev=0.004, collection=furn, lm='furn'))
            add(box(f'{n}_door', (0.62, 0.01, 0.62), (0, -0.284, 0.4), M['cabinet'], bev=0.004, collection=furn, lm='furn'))
            add(box(f'{n}_vent', (0.5, 0.012, 0.12), (0, -0.29, 0.2), M['cabinet_dark'], bev=0.002, collection=furn, lm='furn'))
        else:
            add(screen(f'{n}_lamps', 0.58, 0.62, M['screen'], furn, q=10 + k)).location = (0, -0.282, 1.22)
            add(box(f'{n}_switches', (0.58, 0.03, 0.18), (0, -0.29, 0.78), M['cabinet_dark'], bev=0.005, collection=furn, lm='furn'))
            for j in range(8):
                add(box(f'{n}_sw{j}', (0.018, 0.03, 0.04), (-0.245 + j * 0.07, -0.31, 0.78), M['chrome'], bev=0.003, collection=furn, lm='furn'))
            add(box(f'{n}_door', (0.62, 0.01, 0.6), (0, -0.284, 0.38), M['cabinet'], bev=0.004, collection=furn, lm='furn'))
        add(box(f'{n}_label', (0.3, 0.006, 0.05), (0, -0.285, 1.66), M['paper'], bev=0.001, collection=furn, lm='furn'))
        for o in parts: place(o, F)


# ---------------------------------------------------------------- the living room
PINGPONG = (3.0, -2.2)


def pingpong(M, furn):
    """The table-tennis table: a dark green top with its white lines, the net on its posts, folding steel legs; two
    bats and a ball left on it."""
    x, y = PINGPONG; L, Wd, z = 2.74, 1.525, 0.76
    box('pp_top', (L, Wd, 0.025), (x, y, z - 0.0125), M['felt'], bev=0.003, collection=furn, lm='furn')
    for s in (-1, 1):
        box(f'pp_side{s}', (L, 0.02, 0.0012), (x, y + s * (Wd / 2 - 0.01), z + 0.0006), M['white_line'], bev=0, collection=furn, lm='furn')
        box(f'pp_end{s}', (0.02, Wd, 0.0012), (x + s * (L / 2 - 0.01), y, z + 0.0006), M['white_line'], bev=0, collection=furn, lm='furn')
    box('pp_centre', (L, 0.003, 0.0012), (x, y, z + 0.0006), M['white_line'], bev=0, collection=furn, lm='furn')
    box('pp_net', (0.004, Wd + 0.3, 0.1525), (x, y, z + 0.076), M['net'], bev=0, collection=furn, lm='furn')
    box('pp_net_tape', (0.008, Wd + 0.3, 0.012), (x, y, z + 0.15), M['white_line'], bev=0.001, collection=furn, lm='furn')
    for s in (-1, 1): cyl(f'pp_post{s}', 0.012, 0.17, (x, y + s * (Wd / 2 + 0.15), z + 0.07), M['steel'], seg=12, collection=furn, lm='furn')
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(f'pp_leg{sx}{sy}', (0.035, 0.035, z - 0.04), (x + sx * (L / 2 - 0.3), y + sy * (Wd / 2 - 0.12), (z - 0.04) / 2), M['steel'], bev=0.004, collection=furn, lm='furn')
        box(f'pp_rail{sx}', (0.03, Wd - 0.2, 0.03), (x + sx * (L / 2 - 0.3), y, 0.12), M['steel'], bev=0.004, collection=furn, lm='furn')
    for k, (dx, dy, a) in enumerate(((-0.55, 0.3, 0.4), (0.62, -0.25, 2.6))):
        cyl(f'pp_bat{k}', 0.075, 0.012, (x + dx, y + dy, z + 0.006), M['rubber_red'], seg=24, bev=0.002, collection=furn, lm='furn')
        box(f'pp_handle{k}', (0.1, 0.028, 0.02), (x + dx + math.cos(a) * 0.11, y + dy + math.sin(a) * 0.11, z + 0.01), M['wood'], rot=(0, 0, a), bev=0.006, collection=furn, lm='furn')
    cyl('pp_ball', 0.02, 0.04, (x - 0.2, y - 0.4, z + 0.02), M['white_line'], seg=16, bev=0.012, collection=furn, lm='furn')


def record_console(M, furn):
    """A teak console under the DHARMA plaque, the turntable on it with a record on the platter, a stack of LPs."""
    x0, x1, yb = 0.82, 1.58, BOOTH[2]; d = 0.44; hgt = 0.62; xc = (x0 + x1) / 2; yc = yb - d / 2
    box('console_body', (x1 - x0, d, hgt - 0.1), (xc, yc, 0.1 + (hgt - 0.1) / 2), M['wood'], bev=0.008, collection=furn, lm='furn')
    for s in (-1, 1): box(f'console_leg{s}', (0.03, d - 0.06, 0.1), (xc + s * ((x1 - x0) / 2 - 0.06), yc, 0.05), M['dark_wood'], bev=0.004, collection=furn, lm='furn')
    for k in range(2): box(f'console_door{k}', ((x1 - x0) / 2 - 0.02, 0.01, hgt - 0.16), (xc + (k - 0.5) * ((x1 - x0) / 2), yc - d / 2 - 0.004, 0.1 + (hgt - 0.1) / 2), M['dark_wood'], bev=0.003, collection=furn, lm='furn')
    tx_, ty = xc - 0.12, yc + 0.02
    box('turntable_plinth', (0.44, 0.36, 0.07), (tx_, ty, hgt + 0.035), M['dark_wood'], bev=0.006, collection=furn, lm='furn')
    cyl('turntable_platter', 0.15, 0.012, (tx_ - 0.04, ty, hgt + 0.076), M['steel'], seg=48, collection=furn, lm='furn')
    cyl('turntable_record', 0.152, 0.003, (tx_ - 0.04, ty, hgt + 0.0835), M['record'], seg=48, bev=0, collection=furn, lm='furn')
    cyl('turntable_label', 0.045, 0.004, (tx_ - 0.04, ty, hgt + 0.085), M['rubber_red'], seg=24, bev=0, collection=furn, lm='furn')
    box('turntable_arm', (0.012, 0.22, 0.01), (tx_ + 0.15, ty + 0.01, hgt + 0.1), M['chrome'], rot=(0, 0, 0.35), bev=0.003, collection=furn, lm='furn')
    rnd = random.Random(12)
    for k in range(7):
        c = [(0.55, 0.32, 0.12), (0.14, 0.22, 0.4), (0.7, 0.62, 0.42), (0.35, 0.1, 0.1), (0.2, 0.36, 0.22), (0.8, 0.5, 0.2), (0.12, 0.12, 0.12)][k]
        box(f'lp{k}', (0.31, 0.31, 0.005), (xc + 0.2 + rnd.uniform(-0.01, 0.01), yc + rnd.uniform(-0.02, 0.02), hgt + 0.003 + k * 0.006), material(f'sleeve{k}', c, rough=0.6),
            rot=(0, 0, rnd.uniform(-0.08, 0.08)), bev=0.001, collection=furn, lm='furn')


# ---------------------------------------------------------------- the DHARMA mark
def logo(M, col, at, facing):
    """The Swan's octagonal plaque: a wooden octagon, the bagua ring and the swan in relief (darker)."""
    parts = []
    oc = cyl('logo_plate', 0.24, 0.025, (0, 0, 0), M['logo'], rot=(math.pi / 2, 0, 0), seg=8, bev=0.006, collection=col, lm='furn'); oc.rotation_euler.y = math.pi / 8
    parts.append(oc)
    for k in range(8):
        a = k * math.pi / 4 + math.pi / 8
        bar = box(f'logo_trigram{k}', (0.09, 0.012, 0.03), (math.cos(a) * 0.16, -0.016, math.sin(a) * 0.16), M['dark_wood'], rot=(0, -a + math.pi / 2, 0), bev=0.002, collection=col, lm='furn')
        parts.append(bar)
    parts.append(cyl('logo_disc', 0.1, 0.012, (0, -0.018, 0), M['dark_wood'], rot=(math.pi / 2, 0, 0), seg=32, bev=0.003, collection=col, lm='furn'))
    F = Matrix.Translation(at) @ Matrix.Rotation(facing, 4, 'Z')
    for o in parts: place(o, F)


# ---------------------------------------------------------------- light
WARM = (1.0, 0.76, 0.48)            # tungsten in the living room
DAY = (1.0, 0.8, 0.55)              # the false window's light box
TEAL = (0.36, 0.84, 0.6)            # the dome's hidden lights
SCREEN_GREEN = (0.35, 1.0, 0.45)
DOWNLIGHTS = [(1.6, 0.9), (3.6, 0.9), (1.4, -1.8), (3.6, -1.8), (BX, 2.0)]   # recessed in the (phantom) ceiling


def lights(bulbs):
    """The room's own light: the dome's cove and its crown, the desk lamp and the screen; the living room's downlights,
    the booth's lamp and its window. Returns the lights."""
    import bpy
    out = []
    def light(name, kind, loc, energy, colour, **kw):
        ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = colour
        for k, v in kw.items(): setattr(ld, k, v)
        ob = cine.link(bpy.data.objects.new(name, ld)); ob.location = loc; out.append(ob)
        return ob
    def aim(ob, d): ob.rotation_euler = Vector(d).to_track_quat('-Z', 'Y').to_euler()
    def orient(ob, d, along):
        # an area light shines along its local -z; its size_y runs along its local y
        z = -Vector(d).normalized(); y = (Vector(along) - z * Vector(along).dot(z)).normalized(); x = y.cross(z)
        ob.matrix_world = Matrix.Translation(ob.location) @ Matrix((x, y, z)).transposed().to_4x4()
    # the cove: strips along the riser's top, washing the panels upward
    n = 14
    for k in range(n):
        th = THETA_A + (THETA_B - THETA_A) * (k + 0.5) / n
        p = dome_point(th, DOME_R - 0.12, RISER + 0.05)
        ob = light(f'cove{k}', 'AREA', p, 26.0, TEAL, shape='RECTANGLE', size=0.06, size_y=0.9)
        orient(ob, Vector((math.cos(th), math.sin(th), 0)) * 0.35 + Vector((0, 0, 1)), Vector((-math.sin(th), math.cos(th), 0)))
    # the dome's crown, above the cut: a soft cool light coming down
    aim(light('crown', 'AREA', (DOME_C.x, DOME_C.y, H - 0.05), 80.0, TEAL, shape='DISK', size=3.6), (0, 0, -1))
    for k, p in enumerate(bulbs):
        if k == 0: light('desk_lamp', 'POINT', p, 14.0, (1.0, 0.86, 0.66), shadow_soft_size=0.03)
        else: light(f'table_lamp{k}', 'POINT', p, 22.0, WARM, shadow_soft_size=0.05)
    # the terminal's glow
    bx, fx, yc = DESK
    aim(light('screen_glow', 'AREA', (TERM_X + 0.14, yc - 0.025, DESK_TOP + 0.23), 2.5, SCREEN_GREEN, shape='RECTANGLE', size=0.27, size_y=0.2), (1, 0, 0))
    # the living room: recessed downlights, warm
    for k, (x, y) in enumerate(DOWNLIGHTS):
        aim(light(f'downlight{k}', 'SPOT', (x, y, H - 0.02), 70.0, WARM, spot_size=math.radians(110), spot_blend=0.6, shadow_soft_size=0.05), (0, 0, -1))
    # the false window: its light box, through the blinds
    cx, cz, w, h = WIN
    aim(light('window_box', 'AREA', (cx, D / 2 - 0.045, cz), 95.0, DAY, shape='RECTANGLE', size=w - 0.1, size_y=h - 0.1), (0, -1, 0))
    return out
