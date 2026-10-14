# Seinfeld · Jerry's apartment, 5A (129 West 81st Street), as the set stood in season seven. The living room and the
# open kitchen: honey oak strips, white walls under a mottled grey glaze, grey beadboard to the dado, casings with
# rosette corner blocks; the window alcove with Jerry's desk and the venetian blinds, the black etagere with the
# Superman figure, the hall to the bathroom with the green bike on its wall, the front door standing open onto the
# corridor (Kramer's 5B across it, the corridor running on behind the kitchen as on the set), the pipe and the coat
# hooks, the almond fridge under its magnets, the slate-blue glass cabinets full of cereal, the peninsula with its
# cooktop and the two navy stools, the blue-grey couch, the cherry dining table. Afternoon: sun through the blinds.
#
# The set's walls fan out toward the audience; here they are squared to the module (back wall, left wall), so the
# visitor's view from the front right sees the door and the kitchen face on. Where the module's top cuts the solid
# between the rooms: a dark `section` face.
import math, os, random
import bpy, bmesh
from mathutils import Vector, Matrix
import cine
from cine import box, cyl, material, moulding, cloth_panel, lathe, place, slab_profile, rounded_slab

W, D, H = 9.6, 7.6, 3.0
T = 0.14                                   # the module's walls
BACK, LEFT, RIGHT, FRONT = D / 2 - T, -W / 2 + T, W / 2 - T, -D / 2 + T
TEX = os.path.join(cine.OUT, 'textures', 'seinfeld')
tx = lambda n: os.path.join(TEX, n)
PH = lambda n: os.path.join(cine.CACHE, 'polyhaven', n, f'{n}_1k.gltf')

YB, TW = 2.2, 0.12                         # the apartment's back wall: its room face, its thickness
ALCOVE = (LEFT, -2.05)                     # the window bay, back to the module's back wall
HALL = (-0.3, 0.7, 2.2)                    # the hall to the bathroom: opening x0, x1, head height
BATH_Y = 3.08                              # the bathroom's door wall (the hall's end)
DOOR = (1.15, 2.07, 2.13)                  # the front door's opening: hinge side x, latch side x, head height
DOOR_OPEN = math.radians(80)               # how far it stands open (into the room, toward the hall)
CORR = 0.82                                # the corridor's near end (x); it runs on to the cut at the right
KITCHEN = 2.75                             # where the kitchen's back wall starts
DADO, RAIL, BAND = 0.92, 2.4, 2.86         # beadboard cap, picture rail, the top of the band (cornice above)
PENINSULA = (2.38, 4.66, -0.62, -0.02)     # x0, x1, y front, y back
COUNTER_H = 0.91
STOOLS = [(2.72, -0.95), (3.26, -0.95)]
COUCH = (-1.05, -0.35)                     # centre; it faces the front (-y)
COUCH_L, COUCH_D, ARM_H = 2.1, 0.95, 0.49  # the arm Elaine perches on: Rocketbox's chair clips sit at 0.52 m, at her 0.93 at 0.49
TABLE = (-1.05, 1.2)
STAND = {'jerry': ((1.02, 0.32), (3.0, -0.6)), 'george': ((3.4, 0.36), (2.9, -1.0)), 'kramer': ((1.62, 2.0), (1.05, 0.55))}   # where, looking at
SEATS = {'elaine': (COUCH[0] + COUCH_L / 2 - 0.11, COUCH[1] + 0.02, math.radians(115))}   # x, y, facing (z rotation; a seat's front is -y)


# ---------------------------------------------------------------- materials
def mats():
    M = {}
    M['floor'] = material('oak_strip', rough=0.38, maps={'color': tx('floor_color.jpg'), 'normal': tx('floor_normal.jpg')}, scale=1.824, normal_strength=0.5, specular=0.5, coat=0.25, coat_rough=0.25)
    M['wall'] = material('wall_glaze', rough=0.82, maps={'color': tx('wall_color.jpg'), 'normal': tx('wall_normal.jpg')}, scale=2.2, normal_strength=0.25)
    M['band'] = material('wall_band', rough=0.82, maps={'color': tx('band_color.jpg')}, scale=2.2)
    M['bead'] = material('beadboard', rough=0.55, maps={'color': tx('beadboard_color.jpg'), 'normal': tx('beadboard_normal.jpg')}, scale=0.608, normal_strength=1.0, specular=0.45)
    M['trim'] = material('trim_grey', (0.30, 0.30, 0.32), rough=0.45, specular=0.45)
    M['trim_dark'] = material('trim_dark', (0.18, 0.18, 0.2), rough=0.45)
    M['door'] = material('door_cream', (0.74, 0.70, 0.61), rough=0.42, specular=0.45)
    M['panel'] = material('door_panel', (0.56, 0.62, 0.68), rough=0.45)
    M['brass'] = material('brass', (0.78, 0.58, 0.28), rough=0.28, metal=1.0)
    M['chrome'] = material('chrome', (0.8, 0.8, 0.8), rough=0.14, metal=1.0)
    M['steel'] = material('steel', (0.62, 0.63, 0.64), rough=0.3, metal=1.0)
    M['crystal'] = material('crystal_knob', (0.85, 0.86, 0.88), rough=0.05, coat=1.0)
    M['kerb'] = material('kerb', (0.25, 0.24, 0.23), rough=0.9)
    M['section'] = material('section', (0.03, 0.028, 0.026), rough=0.92)
    M['ceiling'] = material('ceiling', rough=0.9, maps={'color': tx('ceiling_color.jpg')}, scale=1.4)
    M['cabinet'] = material('cabinet_slate', (0.12, 0.15, 0.2), rough=0.42, specular=0.45)
    M['glass_dark'] = material('cabinet_glass', (0.05, 0.055, 0.06), rough=0.08, coat=0.6)
    M['laminate'] = material('counter_laminate', (0.42, 0.42, 0.44), rough=0.4, specular=0.5)
    M['board'] = material('counter_board', rough=0.55, maps={'color': tx('counter_board_color.jpg'), 'normal': tx('beadboard_normal.jpg')}, scale=0.608, normal_strength=0.9)
    M['kick'] = material('toe_kick', (0.08, 0.08, 0.085), rough=0.6)
    M['tile'] = material('tile_kitchen', rough=0.18, maps={'color': tx('tile_kitchen_color.jpg'), 'normal': tx('tile_kitchen_normal.jpg')}, scale=0.432, normal_strength=0.8, coat=0.3)
    M['tile_bath'] = material('tile_bath', rough=0.18, maps={'color': tx('tile_bath_color.jpg'), 'normal': tx('tile_bath_normal.jpg')}, scale=0.432, normal_strength=0.8, coat=0.3)
    M['fridge'] = material('fridge_front', rough=0.32, maps={'color': tx('fridge_color.jpg')}, scale=1.0, coat=0.4, coat_rough=0.2)
    M['almond'] = material('almond_enamel', (0.70, 0.65, 0.53), rough=0.3, coat=0.4, coat_rough=0.2)
    M['enamel_white'] = material('white_enamel', (0.82, 0.82, 0.8), rough=0.22, coat=0.5)
    M['plastic_white'] = material('white_plastic', (0.78, 0.78, 0.76), rough=0.4)
    M['black'] = material('black_plastic', (0.02, 0.02, 0.022), rough=0.45)
    M['rubber'] = material('black_rubber', (0.025, 0.025, 0.025), rough=0.75)
    M['cast_iron'] = material('grate', (0.03, 0.03, 0.03), rough=0.5, metal=0.6)
    M['navy'] = material('stool_navy', (0.015, 0.025, 0.085), rough=0.35, coat=0.4, coat_rough=0.3)
    M['couch'] = material('couch_weave', rough=0.88, maps={'color': tx('couch_color.jpg'), 'normal': tx('couch_normal.jpg')}, scale=0.5, normal_strength=0.6, sheen=0.4, sheen_tint=(0.35, 0.42, 0.45))
    M['cherry'] = material('cherry', (0.16, 0.045, 0.028), rough=0.3, coat=0.6, coat_rough=0.15)
    M['black_wood'] = material('black_lacquer', (0.025, 0.024, 0.024), rough=0.35, coat=0.4)
    M['red_drawer'] = material('drawer_red', (0.36, 0.08, 0.035), rough=0.4, coat=0.3)
    M['rug_coffee'] = material('rug_coffee', rough=0.95, maps={'color': tx('rug_coffee_color.jpg')}, scale=1.0)
    M['rug_dining'] = material('rug_dining', rough=0.95, maps={'color': tx('rug_dining_color.jpg')}, scale=1.0)
    M['spines'] = material('spines', rough=0.6, maps={'color': tx('spines_color.jpg')}, scale=1.0)
    M['cereal'] = material('cereal_boxes', rough=0.55, maps={'color': tx('cereal_color.jpg')}, scale=1.0)
    M['poster_racer'] = material('poster_racer', rough=0.3, maps={'color': tx('poster_racer.jpg')}, scale=1.0, coat=0.6)
    M['poster_city'] = material('poster_city', rough=0.3, maps={'color': tx('poster_city.jpg')}, scale=1.0, coat=0.6)
    for k in range(3): M[f'photo{k}'] = material(f'photo{k}', rough=0.3, maps={'color': tx(f'photo{k}.jpg')}, scale=1.0, coat=0.6)
    M['mat_board'] = material('mat_board', (0.82, 0.8, 0.75), rough=0.8)
    M['num5a'] = material('door_number_5a', rough=0.4, maps={'color': tx('door_5a.jpg')}, scale=1.0)
    M['num5b'] = material('door_number_5b', rough=0.4, maps={'color': tx('door_5b.jpg')}, scale=1.0)
    M['view'] = material('window_view', rough=0.9, maps={'color': tx('view_color.jpg')}, scale=1.0)
    M['view_light'] = material('window_daylight', (1.0, 0.95, 0.86), rough=0.9, emission=(1.0, 0.93, 0.82), emission_strength=3.2)
    M['blind'] = material('blind_slat', (0.80, 0.76, 0.66), rough=0.4)
    M['sash'] = material('sash_paint', (0.78, 0.77, 0.74), rough=0.45)
    M['radiator'] = material('radiator_paint', (0.76, 0.75, 0.72), rough=0.5, metal=0.3)
    M['sconce'] = material('sconce_glass', (0.86, 0.85, 0.82), rough=0.5, emission=(1.0, 0.86, 0.66), emission_strength=0.6)
    M['shade'] = material('lampshade', (0.9, 0.87, 0.8), rough=0.8, emission=(1.0, 0.82, 0.58), emission_strength=2.2)
    M['red_shade'] = material('pendant_red', (0.6, 0.05, 0.04), rough=0.3, coat=0.6)
    M['bike'] = material('bike_green', (0.12, 0.55, 0.12), rough=0.3, coat=0.7, coat_rough=0.1)
    M['beige'] = material('beige_plastic', (0.62, 0.58, 0.5), rough=0.45)
    M['screen'] = material('screen_dark', (0.02, 0.03, 0.03), rough=0.1, emission=(0.4, 0.55, 0.6), emission_strength=0.15)
    M['paper'] = material('paper', (0.85, 0.84, 0.8), rough=0.85)
    M['jacket'] = material('jacket_suede', (0.2, 0.1, 0.045), rough=0.85, sheen=0.3, sheen_tint=(0.4, 0.3, 0.2))
    M['hall_floor'] = material('hall_floor', (0.42, 0.38, 0.33), rough=0.5)
    M['hall_wall'] = material('hall_wall', (0.62, 0.58, 0.5), rough=0.8)
    M['skin_figure'] = material('figure_skin', (0.75, 0.5, 0.38), rough=0.4, coat=0.5)
    M['fig_blue'] = material('figure_blue', (0.05, 0.14, 0.55), rough=0.35, coat=0.6)
    M['fig_red'] = material('figure_red', (0.6, 0.04, 0.04), rough=0.35, coat=0.6)
    M['bottle_blue'] = material('bottle_blue', (0.02, 0.05, 0.3), rough=0.08, coat=1.0)
    M['wood_block'] = material('knife_block', (0.55, 0.35, 0.18), rough=0.5)
    M['bowl'] = material('fruit_bowl', (0.82, 0.8, 0.74), rough=0.2, coat=0.6)
    M['magazine'] = material('magazines', rough=0.35, maps={'color': tx('magazine_color.jpg')}, scale=1.0, coat=0.5)
    _glow(M['view'], 2.6)   # the street, sunlit: it shines on the web as in the renders
    return M


def _glow(m, strength):
    """Let a textured material emit its own colour map (a view through a window)."""
    nt = m.node_tree; p = nt.nodes['Principled BSDF']
    t = next(n for n in nt.nodes if n.type == 'TEX_IMAGE')
    nt.links.new(t.outputs['Color'], p.inputs['Emission Color']); p.inputs['Emission Strength'].default_value = strength


# ---------------------------------------------------------------- helpers
SKIRT = [(0, 0), (0.016, 0), (0.016, 0.11), (0.012, 0.125), (0.006, 0.135), (0, 0.14)]
CAP = [(0, 0), (0.03, 0.0), (0.034, 0.012), (0.03, 0.028), (0.018, 0.034), (0, 0.04)]          # the dado's cap rail
PICTURE = [(0, 0), (0.014, 0.004), (0.024, 0.016), (0.022, 0.03), (0.01, 0.036), (0, 0.04)]
CORNICE = [(0, 0), (0.012, 0), (0.012, 0.02), (0.03, 0.035), (0.06, 0.07), (0.08, 0.1), (0.09, 0.14), (0, 0.14)]


class Face:
    """A wall's face seen from the room: from a to b (floor points), `n` pointing into the room."""
    def __init__(self, a, b, n):
        self.a, self.b, self.n = Vector((a[0], a[1], 0)), Vector((b[0], b[1], 0)), Vector((n[0], n[1], 0)).normalized()
        self.d = (self.b - self.a).normalized(); self.L = (self.b - self.a).length

    def at(self, u, o, z):
        return self.a + self.d * u + self.n * o + Vector((0, 0, z))

    def slab(self, name, u0, u1, z0, z1, o, t, mat, col, bev=0.003, **props):
        """A board standing `o` out from the face, `t` thick (its back on the face)."""
        c = self.at((u0 + u1) / 2, o + t / 2, (z0 + z1) / 2)
        ob = box(name, (u1 - u0, t, z1 - z0), c, mat, bev=bev, collection=col, **props)
        ob.rotation_euler.z = math.atan2(self.d.y, self.d.x)
        return ob

    def run(self, name, u0, u1, z, profile, mat, col, o=0.0, **props):
        return moulding(name, self.at(u0, o, z), self.at(u1, o, z), self.n, profile, mat, collection=col, **props)


def _spans(L, cuts):
    """The parts of [0, L] outside the cut ranges [(u0, u1), ...]."""
    out, u = [], 0.0
    for c0, c1 in sorted(cuts):
        if c0 > u + 1e-4: out.append((u, c0))
        u = max(u, c1)
    if u < L - 1e-4: out.append((u, L))
    return out


def dress(face, name, M, col, openings=(), dado=True, band=True, cornice=True, bead='bead', low=True):
    """A wall's finish: skirting, beadboard to the dado and its cap rail, the picture rail, the band above it and the
    cornice. `openings` [(u0, u1, head[, sill])]: skirting and beadboard stop at those that reach the floor (a window
    sitting above the dado leaves them be); the rails stop where a head reaches them."""
    ops = [(o[0], o[1], o[2], o[3] if len(o) > 3 else 0.0) for o in openings]
    if low:
        for k, (u0, u1) in enumerate(_spans(face.L, [(u0, u1) for u0, u1, hd, sl in ops if sl < DADO + 0.03])):
            if u1 - u0 < 0.02: continue
            face.run(f'{name}_skirt{k}', u0, u1, 0.0, SKIRT, M['trim'], col, o=0.012, lm='arch')
            if dado:
                face.slab(f'{name}_bead{k}', u0, u1, 0.0, DADO, 0.0, 0.012, M[bead], col, bev=0, lm='arch')
                face.run(f'{name}_cap{k}', u0, u1, DADO, CAP, M['trim'], col, o=0.012, lm='arch')
    for k, (u0, u1) in enumerate(_spans(face.L, [(u0, u1) for u0, u1, hd, sl in ops if hd > RAIL - 0.12])):
        if u1 - u0 < 0.02: continue
        face.run(f'{name}_rail{k}', u0, u1, RAIL, PICTURE, M['trim'], col, lm='arch')
        if band: face.slab(f'{name}_band{k}', u0, u1, RAIL + 0.03, BAND, 0.0, 0.003, M['band'], col, bev=0, lm='arch')
    if cornice:
        for k, (u0, u1) in enumerate(_spans(face.L, [(u0, u1) for u0, u1, hd, sl in ops if hd > BAND - 0.02])):
            face.run(f'{name}_cornice{k}', u0, u1, BAND, CORNICE, M['trim'], col, lm='arch')


def casing(face, name, u0, u1, head, M, col, w=0.09, o=0.0, rosettes=True, foot=0.0):
    """An architrave round an opening: two legs and a head, square corner blocks with a turned rosette at the top,
    plinth blocks at the foot (the set's casings); a window's (`foot` its sill) has no plinths."""
    t = 0.022; obs = []
    for k, u in enumerate((u0 - w, u1)):
        obs.append(face.slab(f'{name}_leg{k}', u, u + w, max(foot, 0.16 if not foot else foot), head, o, t, M['trim'], col, bev=0.004, lm='arch'))
        if not foot: obs.append(face.slab(f'{name}_plinth{k}', u - 0.008, u + w + 0.008, 0.0, 0.17, o, t + 0.008, M['trim'], col, bev=0.004, lm='arch'))
        if rosettes:
            obs.append(face.slab(f'{name}_block{k}', u - 0.008, u + w + 0.008, head, head + w + 0.016, o, t + 0.008, M['trim'], col, bev=0.004, lm='arch'))
            c = face.at(u + w / 2, o + t + 0.008, head + w / 2 + 0.008)
            ro = cyl(f'{name}_rosette{k}', 0.032, 0.012, c, M['trim'], seg=24, bev=0.004, collection=col, lm='arch')
            ro.rotation_euler = face.n.to_track_quat('Z', 'Y').to_euler()
            obs.append(ro)
    obs.append(face.slab(f'{name}_head', u0, u1, head, head + w, o, t, M['trim'], col, bev=0.004, lm='arch'))
    return obs


def reveal(name, x0, x1, y0, y1, head, M, col):
    """The lined jambs and soffit of an opening through a wall running along x (y0..y1 its thickness)."""
    for k, x in enumerate((x0, x1)):
        box(f'{name}_jamb{k}', (0.02, y1 - y0, head), (x + (0.01 if k == 0 else -0.01), (y0 + y1) / 2, head / 2), M['trim'], bev=0.002, collection=col, lm='arch')
    box(f'{name}_soffit', (x1 - x0, y1 - y0, 0.02), ((x0 + x1) / 2, (y0 + y1) / 2, head - 0.01), M['trim'], bev=0.002, collection=col, lm='arch')


def uv_rect(ob, axis='y'):
    """0..1 UVs across a box's faces that look along `axis` (a picture, a decal, a fridge front)."""
    me = ob.data; uv = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
    xs = [v.co for v in me.vertices]
    i, j = {'y': (0, 2), 'x': (1, 2), 'z': (0, 1)}[axis]
    lo = [min(c[i] for c in xs), min(c[j] for c in xs)]; hi = [max(c[i] for c in xs), max(c[j] for c in xs)]
    for poly in me.polygons:
        flip = (poly.normal[{'y': 1, 'x': 0, 'z': 2}[axis]] > 0) if axis != 'z' else False
        for li in poly.loop_indices:
            c = me.vertices[me.loops[li].vertex_index].co
            u = (c[i] - lo[0]) / (hi[0] - lo[0] + 1e-9); v = (c[j] - lo[1]) / (hi[1] - lo[1] + 1e-9)
            uv.data[li].uv = (1 - u if flip else u, v)
    return ob


def tube(name, pts, r, mat, col, closed=False, seg=10, **props):
    """A round tube swept along points (a tyre, a chair's hoop, a ring of stretchers)."""
    pts = [Vector(p) for p in pts]; n = len(pts); bm = bmesh.new(); rings = []
    for i, p in enumerate(pts):
        a = pts[(i - 1) % n] if closed or i > 0 else p; b = pts[(i + 1) % n] if closed or i < n - 1 else p
        t = (b - a).normalized(); u = t.orthogonal().normalized(); v = t.cross(u)
        rings.append([bm.verts.new(p + (u * math.cos(2 * math.pi * k / seg) + v * math.sin(2 * math.pi * k / seg)) * r) for k in range(seg)])
    for i in range(n if closed else n - 1):
        a, b = rings[i], rings[(i + 1) % n]
        for k in range(seg): bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    if not closed: bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = cine._mesh_obj(name, bm, mat, col, smooth=True)
    for k, v in props.items(): ob[k] = v
    return ob


def circle(c, r, u, v, n=48, a0=0.0, a1=2 * math.pi):
    """Points on a circle about c in the plane of u and v."""
    c, u, v = Vector(c), Vector(u), Vector(v)
    return [c + (u * math.cos(a0 + (a1 - a0) * k / n) + v * math.sin(a0 + (a1 - a0) * k / n)) * r for k in range(n + (0 if a1 - a0 >= 2 * math.pi - 1e-6 else 1))]


def section(objs, M):
    """The faces the module's top cuts through (wall and solid tops), dark, as the cut face of a model is drawn."""
    for ob in objs:
        if not ob.name.startswith(('back_', 'left_')): continue
        me = ob.data
        if M['section'].name not in [m.name for m in me.materials if m]: me.materials.append(M['section'])
        k = [m.name if m else '' for m in me.materials].index(M['section'].name)
        for f in me.polygons:
            c = sum((me.vertices[i].co for i in f.vertices), Vector()) / len(f.vertices)
            if f.normal.z > 0.9 and c.z > H - 0.004: f.material_index = k


# ---------------------------------------------------------------- the shell
def shell(M, arch, furn, phantom):
    """The floor, the module's walls with the windows, the apartment's back wall with its openings, the solid between
    the rooms, the bike hall and the bathroom, the corridor; kerbs and phantoms."""
    box('subfloor', (W, D, 0.03), (0, 0, -0.027), M['kerb'], bev=0, collection=arch, lm='arch')
    box('floor', (W - 0.02, YB + D / 2 - 0.01, 0.02), (0, (YB - D / 2) / 2, -0.01), M['floor'], bev=0, collection=arch, lm='arch')
    box('floor_alcove', (ALCOVE[1] - ALCOVE[0] + 0.01, BACK - YB + 0.01, 0.02), ((ALCOVE[0] + ALCOVE[1]) / 2, (BACK + YB) / 2, -0.01), M['floor'], bev=0, collection=arch, lm='arch')
    box('floor_hall', (HALL[1] - HALL[0], BACK - YB, 0.02), ((HALL[0] + HALL[1]) / 2, (BACK + YB) / 2, -0.01), M['floor'], bev=0, collection=arch, lm='arch')
    box('floor_bath', (HALL[1] - HALL[0], BACK - BATH_Y - 0.12, 0.022), ((HALL[0] + HALL[1]) / 2, (BACK + BATH_Y + 0.12) / 2, -0.009), M['tile'], bev=0, collection=arch, lm='arch')
    box('floor_corridor', (RIGHT - CORR + T, BACK - YB - TW, 0.02), ((RIGHT + T + CORR) / 2, (BACK + YB + TW) / 2, -0.01), M['hall_floor'], bev=0, collection=arch, lm='arch')
    # the module's left wall, solid; its back wall with the alcove's two windows and the bathroom's
    box('left_wall', (T, D, H), (-W / 2 + T / 2, 0, H / 2), M['wall'], bev=0, collection=arch, lm='arch')
    cuts = [(c - 0.275, c + 0.275) for c in WINDOWS] + [BATH_WIN]
    edges = [-W / 2 + T] + [e for c in sorted(cuts) for e in c] + [W / 2]
    for k in range(0, len(edges), 2):
        a, b = edges[k], edges[k + 1]
        box(f'back_wall_{k}', (b - a, T, H), ((a + b) / 2, D / 2 - T / 2, H / 2), M['wall'], bev=0, collection=arch, lm='arch')
    for k, (a, b) in enumerate(cuts):
        z0, z1 = (WIN_Z if k < len(WINDOWS) else BATH_WIN_Z)
        box(f'back_sill_{k}', (b - a, T, z0), ((a + b) / 2, D / 2 - T / 2, z0 / 2), M['wall'], bev=0, collection=arch, lm='arch')
        box(f'back_lintel_{k}', (b - a, T, H - z1), ((a + b) / 2, D / 2 - T / 2, (H + z1) / 2), M['wall'], bev=0, collection=arch, lm='arch')
    # the solid behind the etagere and the pier (its faces: the alcove's side, the back wall, the hall's left wall)
    box('back_solid', (HALL[0] - ALCOVE[1], BACK - YB, H), ((HALL[0] + ALCOVE[1]) / 2, (BACK + YB) / 2, H / 2), M['wall'], bev=0, collection=arch, lm='arch')
    # between the hall (and bathroom) and the corridor
    box('back_party', (CORR - HALL[1], BACK - YB, H), ((CORR + HALL[1]) / 2, (BACK + YB) / 2, H / 2), M['wall'], bev=0, collection=arch, lm='arch')
    # the apartment's back wall from the hall to the right: round the door, and the kitchen's back
    d0, d1, dh = DOOR
    box('back_wall_left_of_door', (d0 - CORR, TW, H), ((d0 + CORR) / 2, YB + TW / 2, H / 2), M['wall'], bev=0, collection=arch, lm='arch')
    box('back_wall_over_door', (d1 - d0, TW, H - dh), ((d0 + d1) / 2, YB + TW / 2, (H + dh) / 2), M['wall'], bev=0, collection=arch, lm='arch')
    box('back_wall_kitchen', (RIGHT + T - d1, TW, H), ((RIGHT + T + d1) / 2, YB + TW / 2, H / 2), M['wall'], bev=0, collection=arch, lm='arch')
    box('back_wall_over_hall', (HALL[1] - HALL[0], TW, H - HALL[2]), ((HALL[0] + HALL[1]) / 2, YB + TW / 2, (H + HALL[2]) / 2), M['wall'], bev=0, collection=arch, lm='arch')
    # the bathroom's door wall, across the hall's end, its doorway
    b0, b1, bh = -0.1, 0.55, 2.05
    for k, (a, b) in enumerate(((HALL[0], b0), (b1, HALL[1]))):
        box(f'back_bath_wall{k}', (b - a, 0.12, H), ((a + b) / 2, BATH_Y + 0.06, H / 2), M['wall'], bev=0, collection=arch, lm='arch')
    box('back_bath_over', (b1 - b0, 0.12, H - bh), ((b0 + b1) / 2, BATH_Y + 0.06, (H + bh) / 2), M['wall'], bev=0, collection=arch, lm='arch')
    # the cut-away: front and right walls end in a low kerb
    box('kerb_front', (W, T, 0.22), (0, -D / 2 + T / 2, 0.11), M['kerb'], bev=0.002, collection=arch, lm='arch')
    box('kerb_right', (T, D - 2 * T, 0.22), (W / 2 - T / 2, 0, 0.11), M['kerb'], bev=0.002, collection=arch, lm='arch')
    # phantoms: the ceiling and the missing walls, for the bounce light (never exported)
    box('ceiling', (W, D, 0.04), (0, 0, H + 0.02), M['ceiling'], bev=0, collection=phantom, bake_only=1)
    box('front_wall', (W, T, H - 0.22), (0, -D / 2 + T / 2, 0.22 + (H - 0.22) / 2), M['wall'], bev=0, collection=phantom, bake_only=1)
    box('right_wall', (T, D, H - 0.22), (W / 2 - T / 2, 0, 0.22 + (H - 0.22) / 2), M['wall'], bev=0, collection=phantom, bake_only=1)
    _finishes(M, arch, furn)


def _finishes(M, arch, furn):
    """Beadboard, rails, band and cornice on every face the room shows; casings with rosettes; the reveals."""
    d0, d1, dh = DOOR; h0, h1, hh = HALL
    # the left wall, front to back (the alcove included)
    dress(Face((LEFT, FRONT), (LEFT, BACK), (1, 0)), 'left_face', M, arch)
    # the alcove: its back wall (the windows) and its right side (the solid's face)
    fa = Face((ALCOVE[0], BACK), (ALCOVE[1], BACK), (0, -1))
    dress(fa, 'back_alcove', M, arch, openings=[(c - 0.275 - ALCOVE[0], c + 0.275 - ALCOVE[0], WIN_Z[1], WIN_Z[0]) for c in WINDOWS])
    # the kitchen's back wall above its cabinets: the rail, band and cornice run on
    dress(Face((KITCHEN, YB), (RIGHT + T, YB), (0, -1)), 'back_kitchen', M, arch, low=False)
    dress(Face((ALCOVE[1], BACK), (ALCOVE[1], YB), (-1, 0)), 'back_alcove_side', M, arch)
    # the back wall: the pier and the etagere's stretch, round the hall, round the door, up to the kitchen
    fb = Face((ALCOVE[1], YB), (KITCHEN, YB), (0, -1))
    o = lambda x: x - ALCOVE[1]
    dress(fb, 'back_face', M, arch, openings=[(o(h0), o(h1), hh), (o(d0), o(d1), dh)])
    casing(fb, 'hall_casing', o(h0), o(h1), hh, M, arch)
    casing(fb, 'door_casing', o(d0), o(d1), dh, M, arch)
    reveal('hall_reveal', h0, h1, YB, YB + TW, hh, M, arch)
    reveal('door_reveal', d0, d1, YB, YB + TW, dh, M, arch)
    # the hall: its left wall (the bike's), its right wall, its end with the bathroom's doorway
    dress(Face((h0, YB + TW), (h0, BATH_Y), (1, 0)), 'back_hall_l', M, arch, band=False)
    dress(Face((h1, BATH_Y), (h1, YB + TW), (-1, 0)), 'back_hall_r', M, arch, band=False)
    fe = Face((h0, BATH_Y), (h1, BATH_Y), (0, -1))
    dress(fe, 'back_hall_end', M, arch, openings=[(-0.1 - h0, 0.55 - h0, 2.05)], band=False)
    casing(fe, 'bath_casing', -0.1 - h0, 0.55 - h0, 2.05, M, arch, w=0.075, rosettes=False)
    # the bathroom: salmon tile to 1.25 m, white above
    for k, f in enumerate((Face((h0, BACK), (h1, BACK), (0, -1)), Face((h0, BATH_Y + 0.12), (h0, BACK), (1, 0)), Face((h1, BACK), (h1, BATH_Y + 0.12), (-1, 0)))):
        f.slab(f'bath_tile{k}', 0.0, f.L, 0.0, 1.25, 0.0, 0.01, M['tile_bath'], arch, bev=0, lm='arch')
        f.slab(f'bath_tile_cap{k}', 0.0, f.L, 1.25, 1.29, 0.0, 0.02, M['tile_bath'], arch, bev=0.004, lm='arch')
    # the corridor: its far wall (5B), its near end; its side of the apartment's wall
    fc = Face((CORR, BACK), (RIGHT + T, BACK), (0, -1))
    dress(fc, 'corridor_far', M, arch, openings=[(d0 - CORR, d1 - CORR, dh)], band=False)
    casing(fc, 'door5b_casing', d0 - CORR, d1 - CORR, dh, M, arch)
    dress(Face((CORR, YB + TW), (CORR, BACK), (1, 0)), 'corridor_end', M, arch, band=False)
    fn = Face((RIGHT + T, YB + TW), (CORR, YB + TW), (0, 1))
    dress(fn, 'corridor_near', M, arch, openings=[(RIGHT + T - d1, RIGHT + T - d0, dh)], band=False)
    casing(fn, 'door5a_outer_casing', RIGHT + T - d1, RIGHT + T - d0, dh, M, arch)


# ---------------------------------------------------------------- doors
def door_leaf(name, w, h, M, col, num=None, inside=True):
    """A four-panel door, built about its hinge edge at the origin, closed along +x, its outside facing +y:
    cream stiles and rails, pale blue-grey raised panels both sides; brass knob plate, the deadbolts, the peephole
    and the number outside; the chain inside."""
    t = 0.045; parts = []
    def add(o): parts.append(o); return o
    add(box(f'{name}_slab', (w, t, h), (w / 2, 0, h / 2), M['door'], bev=0.004, collection=col, lm='furn'))
    for s in (-1, 1):
        y = s * (t / 2 + 0.004)
        for k, (z0, z1) in enumerate(((0.14, 0.86), (1.0, h - 0.14))):
            for j, (x0, x1) in enumerate(((0.12, w / 2 - 0.05), (w / 2 + 0.05, w - 0.12))):
                add(box(f'{name}_panel{s}{k}{j}', (x1 - x0, 0.01, z1 - z0), ((x0 + x1) / 2, y, (z0 + z1) / 2), M['panel'], bev=0.012, seg=2, collection=col, lm='furn'))
    out = t / 2 + 0.004
    # outside: the number, the peephole under it, two deadbolts and the knob on its plate, by the latch edge
    if num:
        add(uv_rect(box(f'{name}_number', (0.12, 0.004, 0.075), (w / 2, out, 1.66), M[num], bev=0, collection=col, lm='furn')))
    add(cyl(f'{name}_peephole', 0.011, 0.012, (w / 2, out + 0.004, 1.52), M['brass'], rot=(math.pi / 2, 0, 0), seg=16, bev=0.002, collection=col, lm='furn'))
    add(cyl(f'{name}_peephole_lens', 0.006, 0.004, (w / 2, out + 0.011, 1.52), M['glass_dark'], rot=(math.pi / 2, 0, 0), seg=12, bev=0, collection=col, lm='furn'))
    for z in (1.32, 1.16):
        for s in (-1, 1) if inside else (1,):
            add(cyl(f'{name}_bolt{s}{z}', 0.019, 0.016, (w - 0.075, s * (out + 0.006), z), M['brass'], rot=(math.pi / 2, 0, 0), seg=20, bev=0.003, collection=col, lm='furn'))
    for s in (-1, 1):
        add(box(f'{name}_plate{s}', (0.05, 0.006, 0.2), (w - 0.075, s * (out + 0.002), 0.98), M['brass'], bev=0.003, collection=col, lm='furn'))
        add(lathe(f'{name}_knob{s}', [(0.0, 0.0), (0.012, 0.0), (0.012, 0.035), (0.03, 0.05), (0.032, 0.07), (0.0, 0.075)], M['crystal'], loc=(w - 0.075, s * (out + 0.004), 0.98), seg=12, collection=col, lm='furn')).rotation_euler = (-s * math.pi / 2, 0, 0)
    if inside:   # the chain, its keeper on the jamb side
        add(box(f'{name}_chain_track', (0.11, 0.008, 0.018), (w - 0.13, -(out + 0.004), 1.45), M['brass'], bev=0.002, collection=col, lm='furn'))
        add(cyl(f'{name}_chain', 0.003, 0.14, (w - 0.07, -(out + 0.006), 1.40), M['brass'], seg=6, bev=0, rot=(0, math.radians(60), 0), collection=col, lm='furn'))
    for z in (0.25, 1.05, h - 0.25):
        add(cyl(f'{name}_hinge{z}', 0.008, 0.1, (0.0, 0.0, z), M['brass'], seg=10, bev=0, collection=col, lm='furn'))
    return parts


def doors(M, furn):
    """5A standing open into the room (its outside, with the number and the peephole, toward the kitchen); 5B across
    the corridor, shut; the bathroom's door open against the hall."""
    d0, d1, dh = DOOR; w = d1 - d0 - 0.006
    leaf = door_leaf('door5a', w, dh - 0.008, M, furn, num='num5a')
    # built closed along +x from its hinge, its outside toward the corridor (+y): it swings about the hinge into the room,
    # its outside (the number, the peephole) turning toward the kitchen
    F = Matrix.Translation((d0 + 0.003, YB + 0.028, 0.004)) @ Matrix.Rotation(-DOOR_OPEN, 4, 'Z')
    for o in leaf: place(o, F)
    leaf = door_leaf('door5b', w, dh - 0.008, M, furn, num='num5b', inside=False)
    F = Matrix.Translation((d1 - 0.003, BACK - 0.03, 0.004)) @ Matrix.Rotation(math.pi, 4, 'Z')   # shut, its outside to the corridor
    for o in leaf: place(o, F)
    # the bathroom door, open flat against the hall's right wall
    bd = box('bath_door', (0.035, 0.62, 2.0), (HALL[1] - 0.03, BATH_Y - 0.33, 1.0), M['sash'], bev=0.004, collection=furn, lm='furn')


# ---------------------------------------------------------------- the window alcove
WINDOWS = (-4.18, -3.53)                   # window centres in the module's back wall (x)
WIN_Z = (0.96, 2.3)
BATH_WIN = (0.05, 0.55)
BATH_WIN_Z = (1.35, 2.2)


def windows(M, furn):
    """Two double-hung windows in the alcove, venetian blinds half open, radiators under them; the view across the
    street beyond (lit, seen only by the camera: the sun comes through); the bathroom's small window, its blind."""
    for k, c in enumerate(WINDOWS):
        _window(f'win{k}', c, 0.55, WIN_Z, M, furn)
        _radiator(f'radiator{k}', c, M, furn)
    _window('bathwin', (BATH_WIN[0] + BATH_WIN[1]) / 2, BATH_WIN[1] - BATH_WIN[0], BATH_WIN_Z, M, furn, sill_depth=0.06)


def _window(n, c, w, zz, M, furn, sill_depth=0.1):
    z0, z1 = zz; y = BACK
    fb = Face((c - w / 2 - 0.2, y), (c + w / 2 + 0.2, y), (0, -1))
    casing(fb, f'{n}_casing', 0.2, 0.2 + w, z1, M, furn, w=0.07 if w > 0.5 else 0.05, rosettes=False, foot=z0 - 0.04)
    box(f'{n}_stool', (w + 0.2, sill_depth + 0.03, 0.03), (c, y - sill_depth / 2 + 0.01, z0 - 0.015), M['trim'], bev=0.004, collection=furn, lm='furn')
    for s in (-1, 1): box(f'{n}_reveal{s}', (0.02, T, z1 - z0), (c + s * (w / 2 - 0.01), y + T / 2, (z0 + z1) / 2), M['trim'], bev=0, collection=furn, lm='furn')
    box(f'{n}_soffit', (w, T, 0.02), (c, y + T / 2, z1 - 0.01), M['trim'], bev=0, collection=furn, lm='furn')
    # two sashes, meeting halfway; glass left out (the day is warm and the light passes)
    zm = (z0 + z1) / 2
    for k, (a, b, yy) in enumerate(((z0, zm + 0.02, y + 0.06), (zm - 0.02, z1, y + 0.03))):
        for s in (-1, 1): box(f'{n}_stile{k}{s}', (0.04, 0.035, b - a), (c + s * (w / 2 - 0.04), yy, (a + b) / 2), M['sash'], bev=0.003, collection=furn, lm='furn')
        for zr in (a + 0.025, b - 0.025): box(f'{n}_rail{k}{zr:.2f}', (w - 0.06, 0.035, 0.035), (c, yy, zr), M['sash'], bev=0.003, collection=furn, lm='furn')
    # the blind: slats tilted half open, from the head down to a little above the meeting rail, its bottom rail, cords
    top, bottom = z1 - 0.06, zm - 0.12 if w > 0.5 else z0 + 0.04
    nsl = int((top - bottom) / 0.022)
    for k in range(nsl):
        z = top - k * 0.022
        box(f'{n}_slat{k}', (w - 0.03, 0.025, 0.0016), (c, y - 0.035, z), M['blind'], rot=(math.radians(38), 0, 0), bev=0, collection=furn, lm='furn')
    box(f'{n}_headrail', (w - 0.01, 0.04, 0.035), (c, y - 0.035, z1 - 0.03), M['blind'], bev=0.003, collection=furn, lm='furn')
    box(f'{n}_bottomrail', (w - 0.02, 0.03, 0.012), (c, y - 0.035, bottom - 0.02), M['blind'], bev=0.002, collection=furn, lm='furn')
    # the view across the street: drawn bright for the camera, and invisible to light (the sun and the sky pass)
    v = uv_rect(box(f'{n}_view', (w + 0.1, 0.01, z1 - z0 + 0.1), (c, D / 2 - 0.006, (z0 + z1) / 2), M['view'], bev=0, collection=furn))
    for attr in ('visible_shadow', 'visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter'): setattr(v, attr, False)


def _radiator(n, c, M, furn):
    """A cast-iron column radiator under the window, on two feet, its valve."""
    cols = 12; L = 0.58; hgt = 0.62
    for k in range(cols):
        x = c - L / 2 + (k + 0.5) * L / cols
        rounded_slab(f'{n}_col{k}', 0.038, 0.16, hgt, 0.018, (x, BACK - 0.13, 0.08 + hgt / 2), M['radiator'], collection=furn, lm='furn')
    for s in (-1, 1): box(f'{n}_foot{s}', (0.04, 0.16, 0.08), (c + s * (L / 2 - 0.05), BACK - 0.13, 0.04), M['radiator'], bev=0.006, collection=furn, lm='furn')
    cyl(f'{n}_valve', 0.016, 0.08, (c + L / 2 + 0.04, BACK - 0.13, 0.14), M['steel'], seg=12, collection=furn, lm='furn')


def desk(M, furn):
    """Jerry's desk at the alcove's right: a black frame and top, the beige Macintosh, keyboard, the arm lamp, the phone
    and the answering machine, papers; the black office chair."""
    x0, x1 = -3.12, -2.12; y1 = BACK - 0.02; y0 = y1 - 0.6; zt = 0.74; xc = (x0 + x1) / 2
    box('desk_top', (x1 - x0, y1 - y0, 0.025), (xc, (y0 + y1) / 2, zt - 0.0125), M['black_wood'], bev=0.004, collection=furn, lm='furn')
    for sx in (x0 + 0.03, x1 - 0.03):
        for sy in (y0 + 0.03, y1 - 0.03): box(f'desk_leg{sx:.2f}{sy:.2f}', (0.025, 0.025, zt - 0.025), (sx, sy, (zt - 0.025) / 2), M['black_wood'], bev=0.003, collection=furn, lm='furn')
    box('desk_rail', (x1 - x0 - 0.06, 0.02, 0.06), (xc, y1 - 0.03, zt - 0.06), M['black_wood'], bev=0.002, collection=furn, lm='furn')
    # the Macintosh: a tall beige box, its dark screen, the floppy slot
    mx, my = xc - 0.18, y1 - 0.24
    box('mac_case', (0.25, 0.28, 0.34), (mx, my, zt + 0.17), M['beige'], bev=0.012, collection=furn, lm='furn')
    box('mac_screen', (0.17, 0.006, 0.13), (mx, my - 0.142, zt + 0.235), M['screen'], bev=0.004, collection=furn, lm='furn')
    box('mac_slot', (0.07, 0.006, 0.006), (mx + 0.03, my - 0.142, zt + 0.1), M['black'], bev=0, collection=furn, lm='furn')
    box('mac_keyboard', (0.3, 0.12, 0.025), (mx + 0.02, y0 + 0.13, zt + 0.0125), M['beige'], rot=(math.radians(-4), 0, 0), bev=0.004, collection=furn, lm='furn')
    box('phone', (0.12, 0.2, 0.06), (x1 - 0.2, y0 + 0.2, zt + 0.03), M['black'], bev=0.012, collection=furn, lm='furn')
    box('answering_machine', (0.2, 0.15, 0.05), (x1 - 0.2, y1 - 0.15, zt + 0.025), M['black'], bev=0.008, collection=furn, lm='furn')
    for k in range(4): box(f'desk_paper{k}', (0.21, 0.29, 0.002), (xc + 0.1 + 0.02 * k, (y0 + y1) / 2 + 0.01 * k, zt + 0.001 + 0.002 * k), M['paper'], rot=(0, 0, 0.1 * k - 0.15), bev=0, collection=furn, lm='furn')
    root, ms = cine.import_gltf(PH('desk_lamp_arm_01'), loc=(x1 - 0.14, y1 - 0.3, zt), rot=(0, 0, math.radians(-30)), collection=furn, lm='furn')
    for o in ms:
        for sl in o.material_slots:
            if not sl.material.name.endswith('_light'): sl.material = M['black']
    # the chair: five castors, a column, a black seat and back
    cx, cy = xc - 0.05, y0 - 0.2
    for k in range(5):
        a = k * 2 * math.pi / 5 + 0.4
        box(f'chair_leg{k}', (0.26, 0.03, 0.025), (cx + math.cos(a) * 0.13, cy + math.sin(a) * 0.13, 0.06), M['black'], rot=(0, 0, a), bev=0.005, collection=furn, lm='furn')
        cyl(f'chair_castor{k}', 0.02, 0.02, (cx + math.cos(a) * 0.25, cy + math.sin(a) * 0.25, 0.022), M['rubber'], rot=(math.pi / 2, 0, a), seg=10, collection=furn, lm='furn')
    cyl('chair_column', 0.022, 0.36, (cx, cy, 0.25), M['steel'], seg=12, collection=furn, lm='furn')
    rounded_slab('chair_seat', 0.46, 0.44, 0.07, 0.06, (cx, cy, 0.47), M['black'], collection=furn, lm='furn')
    rounded_slab('chair_back', 0.42, 0.06, 0.48, 0.025, (cx, cy - 0.22, 0.82), M['black'], rot=(math.radians(-8), 0, 0), collection=furn, lm='furn')
    # a framed poster above the desk
    picture('poster_desk', 'poster_city', (xc, BACK, 1.62), (0.5, 0.64), (0, -1), M, furn)


# ---------------------------------------------------------------- pictures, sconces
def picture(name, mat, centre, size, n, M, col, frame=0.025, mat_w=0.0):
    """A framed picture on a wall: a black frame, a mat, the image (0..1 across) a little behind the frame's face."""
    n = Vector((n[0], n[1], 0)).normalized(); c = Vector(centre); w, h = size
    ax = 'y' if abs(n.y) > 0.5 else 'x'
    sz = lambda a, b, t: (a, t, b) if ax == 'y' else (t, a, b)
    obs = [box(f'{name}_frame', sz(w, h, 0.025), c + n * 0.0125, M['black_wood'], bev=0.004, collection=col, lm='furn')]
    if mat_w: obs.append(box(f'{name}_mat', sz(w - 2 * frame, h - 2 * frame, 0.004), c + n * 0.026, M['mat_board'], bev=0, collection=col, lm='furn'))
    img = box(f'{name}_image', sz(w - 2 * frame - 2 * mat_w, h - 2 * frame - 2 * mat_w, 0.004), c + n * 0.028, M[mat], bev=0, collection=col, lm='furn')
    uv_rect(img, ax); obs.append(img)
    return obs


def sconce(name, p, n, M, col):
    """The set's half-bowl uplighter: a frosted half dish on the wall; returns the bulb."""
    n = Vector((n[0], n[1], 0)).normalized(); c = Vector(p)
    bm = bmesh.new(); seg, rings = 24, 8
    verts = []
    for j in range(rings + 1):
        phi = (math.pi / 2) * j / rings; row = []
        for i in range(seg + 1):
            th = math.pi * i / seg
            row.append(bm.verts.new((0.14 * math.cos(th) * math.cos(phi), 0.14 * math.sin(th) * math.cos(phi), -0.09 * math.sin(phi))))
        verts.append(row)
    for j in range(rings):
        for i in range(seg): bm.faces.new((verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = cine._mesh_obj(name, bm, M['sconce'], col, smooth=True); ob['lm'] = 'furn'
    ob.modifiers.new('solid', 'SOLIDIFY').thickness = 0.004
    ob.matrix_basis = Matrix.Translation(c) @ Matrix.Rotation(math.atan2(n.y, n.x) - math.pi / 2, 4, 'Z')
    return c + n * 0.06 - Vector((0, 0, 0.035))


# ---------------------------------------------------------------- the living room
def couch(M, col):
    """The blue-grey couch: a low frame, wide flat arms, two seat cushions, two back cushions, two throw pillows."""
    x, y = COUCH; L, Dp = COUCH_L, COUCH_D; f = M['couch']; parts = []
    def add(o): parts.append(o); return o
    add(rounded_slab('couch_base', L, Dp, 0.26, 0.05, (0, 0, 0.18), f, collection=col, lm='furn'))
    add(rounded_slab('couch_back', L - 0.06, 0.2, 0.42, 0.06, (0, Dp / 2 - 0.1, 0.5), f, collection=col, lm='furn'))
    for s in (-1, 1):
        add(rounded_slab(f'couch_arm{s}', 0.22, Dp, ARM_H - 0.08, 0.05, (s * (L / 2 - 0.11), 0, 0.08 + (ARM_H - 0.08) / 2), f, collection=col, lm='furn'))
        add(rounded_slab(f'couch_seat{s}', (L - 0.44) / 2 - 0.01, Dp - 0.24, 0.14, 0.06, (s * (L - 0.44) / 4, -0.08, 0.38), f, collection=col, lm='furn'))
        bc = add(rounded_slab(f'couch_backcushion{s}', (L - 0.44) / 2 - 0.02, 0.2, 0.42, 0.08, (s * (L - 0.44) / 4, Dp / 2 - 0.26, 0.64), f, collection=col, lm='furn'))
        bc.rotation_euler.x = math.radians(-12)
        pw = add(rounded_slab(f'couch_pillow{s}', 0.4, 0.13, 0.36, 0.05, (s * (L / 2 - 0.42), Dp / 2 - 0.36, 0.6), f, collection=col, lm='furn'))
        pw.rotation_euler = (math.radians(-18), 0, s * math.radians(14))
        for sy in (-1, 1): add(box(f'couch_foot{s}{sy}', (0.05, 0.05, 0.05), (s * (L / 2 - 0.06), sy * (Dp / 2 - 0.06), 0.025), M['black_wood'], bev=0.006, collection=col, lm='furn'))
    for o in parts: place(o, Matrix.Translation((x, y, 0)))
    return parts


def armchair(x, y, facing, M, col):
    f = M['couch']; parts = []
    def add(o): parts.append(o); return o
    add(rounded_slab('arm_base', 0.95, 0.9, 0.26, 0.05, (0, 0, 0.18), f, collection=col, lm='furn'))
    add(rounded_slab('arm_back', 0.9, 0.2, 0.42, 0.06, (0, 0.35, 0.5), f, collection=col, lm='furn'))
    for s in (-1, 1): add(rounded_slab(f'arm_arm{s}', 0.2, 0.9, 0.46, 0.05, (s * 0.375, 0, 0.31), f, collection=col, lm='furn'))
    add(rounded_slab('arm_seat', 0.56, 0.68, 0.14, 0.06, (0, -0.08, 0.38), f, collection=col, lm='furn'))
    bc = add(rounded_slab('arm_cushion', 0.54, 0.2, 0.4, 0.08, (0, 0.2, 0.64), f, collection=col, lm='furn')); bc.rotation_euler.x = math.radians(-12)
    for o in parts: place(o, Matrix.Translation((x, y, 0)) @ Matrix.Rotation(facing, 4, 'Z'))
    return parts


def living(M, col):
    """The couch and its armchair, the coffee table with magazines, the black side table and its lamp, the rugs; the
    dining table and two black chairs behind the couch; the black-and-red bookshelf under the racer poster. Returns
    the lamp's bulb."""
    couch(M, col)
    armchair(-3.08, -1.5, math.radians(28), M, col)
    rug('rug_coffee', (-1.05, -1.15), (2.3, 1.75), M['rug_coffee'], col)
    rug('rug_dining', (TABLE[0], TABLE[1] + 0.05), (1.7, 1.55), M['rug_dining'], col)
    # the coffee table: a low dark cherry slab on square legs, magazines and the remote
    cx, cy = COUCH[0], -1.55
    box('coffee_top', (1.15, 0.58, 0.04), (cx, cy, 0.38), M['cherry'], bev=0.006, collection=col, lm='furn')
    for sx in (-1, 1):
        for sy in (-1, 1): box(f'coffee_leg{sx}{sy}', (0.05, 0.05, 0.36), (cx + sx * 0.52, cy + sy * 0.24, 0.18), M['cherry'], bev=0.004, collection=col, lm='furn')
    rnd = random.Random(4)
    for k in range(5):
        mg = box(f'magazine{k}', (0.21, 0.28, 0.006), (cx - 0.25 + 0.2 * k + rnd.uniform(-0.04, 0.04), cy + rnd.uniform(-0.1, 0.1), 0.403 + 0.006 * (k % 2)), M['magazine'], rot=(0, 0, rnd.uniform(-0.6, 0.6)), bev=0.001, collection=col, lm='furn')
        uv_rect(mg, 'z'); uv = mg.data.uv_layers['UVMap']
        for l in uv.data: l.uv = ((k % 4 + l.uv[0]) / 4, ((k // 4) + l.uv[1]) / 2)
    box('remote', (0.05, 0.17, 0.02), (cx + 0.35, cy + 0.12, 0.41), M['black'], rot=(0, 0, 0.3), bev=0.005, collection=col, lm='furn')
    # the side table at the couch's left end, the lamp on it: a black urn and a white cone shade
    sx, sy = COUCH[0] - COUCH_L / 2 - 0.33, COUCH[1] + 0.05
    box('side_table', (0.5, 0.5, 0.6), (sx, sy, 0.3), M['black_wood'], bev=0.008, collection=col, lm='furn')
    lathe('lamp_base', [(0.0, 0.0), (0.08, 0.0), (0.12, 0.08), (0.13, 0.22), (0.1, 0.33), (0.04, 0.38), (0.015, 0.42), (0.015, 0.56), (0.0, 0.56)], M['black_wood'], loc=(sx, sy, 0.6), seg=32, collection=col, lm='furn')
    sh = cyl('lamp_shade', 0.24, 0.26, (sx, sy, 0.6 + 0.62), M['shade'], r2=0.1, seg=40, bev=0.002, collection=col, lm='furn')
    sh.data.polygons.foreach_set('use_smooth', [True] * len(sh.data.polygons))
    # the dining table: a round cherry top on a dark pedestal, two black chairs
    tx_, ty = TABLE
    cyl('table_top', 0.46, 0.035, (tx_, ty, 0.74), M['cherry'], seg=64, bev=0.008, collection=col, lm='furn')
    lathe('table_pedestal', [(0.0, 0.0), (0.3, 0.0), (0.3, 0.03), (0.08, 0.06), (0.06, 0.2), (0.07, 0.6), (0.14, 0.7), (0.14, 0.722), (0.0, 0.722)], M['black_wood'], loc=(tx_, ty, 0), seg=40, collection=col, lm='furn')
    for k, s in enumerate((-1, 1)): dining_chair(f'dchair{k}', tx_ + s * 0.68, ty + 0.05, -s * math.pi / 2, M, col)
    # the television on its black cart, facing the couch from the room's open side: a 27-inch set, the VCR under it
    tvx, tvy = COUCH[0], -2.85
    box('tv_cart', (0.8, 0.48, 0.06), (tvx, tvy, 0.5), M['black_wood'], bev=0.006, collection=col, lm='furn')
    box('tv_cart_shelf', (0.76, 0.44, 0.03), (tvx, tvy, 0.12), M['black_wood'], bev=0.004, collection=col, lm='furn')
    for sx in (-1, 1):
        for sy in (-1, 1): box(f'tv_cart_leg{sx}{sy}', (0.03, 0.03, 0.5), (tvx + sx * 0.37, tvy + sy * 0.21, 0.25), M['black_wood'], bev=0.003, collection=col, lm='furn')
    box('vcr', (0.43, 0.32, 0.09), (tvx, tvy, 0.18), M['black'], bev=0.005, collection=col, lm='furn')
    rounded_slab('tv_body', 0.7, 0.5, 0.56, 0.06, (tvx, tvy - 0.02, 0.81), M['black'], collection=col, lm='furn')
    box('tv_screen', (0.56, 0.01, 0.42), (tvx - 0.03, tvy + 0.235, 0.83), M['glass_dark'], bev=0.03, seg=4, collection=col, lm='furn')
    # the low bookshelf on the left wall, black with a red drawer, under the racer poster
    bx, by = LEFT + 0.19, -0.45
    shelf_unit('lowshelf', (bx, by), (1.05, 0.36, 0.9), math.pi / 2, M, col, rows=2, drawer_at=1)
    picture('poster_racer', 'poster_racer', (LEFT, by, 1.72), (0.92, 1.16), (1, 0), M, col, mat_w=0.06)
    picture('photo_left', 'photo1', (LEFT, 1.15, 1.6), (0.4, 0.5), (1, 0), M, col, mat_w=0.05)
    return [Vector((sx, sy, 0.6 + 0.62))]


def rug(name, c, size, mat, col):
    r = box(name, (size[0], size[1], 0.008), (c[0], c[1], 0.004), mat, bev=0.002, collection=col, lm='arch')
    uv_rect(r, 'z'); return r


def dining_chair(name, x, y, facing, M, col):
    """A black bentwood chair (local -y its front): a round seat, splayed legs with a ring, a hooped back on spindles."""
    parts = []; b = M['black_wood']
    def add(o): parts.append(o); o['lm'] = 'furn'; return o
    add(cyl(f'{name}_seat', 0.21, 0.035, (0, 0, 0.46), b, seg=32, bev=0.008, collection=col))
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2; top = Vector((math.cos(a) * 0.14, math.sin(a) * 0.14, 0.445)); foot = Vector((math.cos(a) * 0.2, math.sin(a) * 0.2, 0.0))
        add(tube(f'{name}_leg{k}', [foot, top], 0.013, b, col, seg=10))
    add(tube(f'{name}_ring', circle((0, 0, 0.2), 0.177, (1, 0, 0), (0, 1, 0), 32), 0.009, b, col, closed=True, seg=8))
    for k in range(5):
        a = math.radians(-50 + 25 * k); p = Vector((math.sin(a) * 0.17, math.cos(a) * 0.17, 0.0))
        add(tube(f'{name}_spindle{k}', [p + Vector((0, 0, 0.47)), p + Vector((0, 0.02, 0.88))], 0.008, b, col, seg=8))
    add(tube(f'{name}_hoop', circle((0, 0.02, 0.88), 0.18, (1, 0, 0), (0, 1, 0), 20, math.radians(20), math.radians(160)), 0.012, b, col, seg=8))
    for o in parts: place(o, Matrix.Translation((x, y, 0)) @ Matrix.Rotation(facing, 4, 'Z'))
    return parts


def shelf_unit(name, c, size, facing, M, col, rows=4, drawer_at=None, books=None):
    """A black shelf unit (local -y its front): posts, shelves, a red-fronted drawer; books and tapes on the shelves."""
    w, d, h = size; parts = []; b = M['black_wood']
    def add(o): parts.append(o); return o
    for sx in (-1, 1):
        for sy in (-1, 1): add(box(f'{name}_post{sx}{sy}', (0.03, 0.03, h), (sx * (w / 2 - 0.015), sy * (d / 2 - 0.015), h / 2), b, bev=0.003, collection=col, lm='furn'))
    zs = [0.06 + k * (h - 0.08) / rows for k in range(rows + 1)]
    for k, z in enumerate(zs): add(box(f'{name}_shelf{k}', (w - 0.01, d - 0.01, 0.022), (0, 0, z), b, bev=0.003, collection=col, lm='furn'))
    add(box(f'{name}_back', (w - 0.04, 0.008, h - 0.1), (0, d / 2 - 0.006, h / 2), b, bev=0, collection=col, lm='furn'))
    if drawer_at is not None:
        z0, z1 = zs[drawer_at], zs[drawer_at + 1]
        add(box(f'{name}_drawer', (w - 0.05, 0.02, z1 - z0 - 0.03), (0, -d / 2 + 0.01, (z0 + z1) / 2), M['red_drawer'], bev=0.004, collection=col, lm='furn'))
        add(cyl(f'{name}_pull', 0.012, 0.02, (0, -d / 2 - 0.005, (z0 + z1) / 2), b, rot=(math.pi / 2, 0, 0), seg=12, collection=col, lm='furn'))
    rnd = random.Random(hash(name) % 1000)
    for k, (z0, z1) in enumerate(zip(zs, zs[1:])):
        if drawer_at is not None and k == drawer_at: continue
        f0, f1 = (0.0, 1.0) if books is None else books.get(k, (0.0, 0.0))   # books {row: (from, to)} as fractions of the width
        if f1 - f0 < 0.05: continue
        spine_row(f'{name}_books{k}', (w - 0.08) * (f1 - f0), z0 + 0.011, min(z1 - z0 - 0.04, 0.3), d - 0.06, M, col, parts, rnd, vhs=rnd.random() < 0.4,
                  x_at=(w - 0.08) * ((f0 + f1) / 2 - 0.5))
    for o in parts: place(o, Matrix.Translation((c[0], c[1], 0)) @ Matrix.Rotation(facing, 4, 'Z'))
    return parts


def spine_row(name, w, z, hmax, depth, M, col, parts, rnd, vhs=False, x_at=0.0):
    """A row of books (or VHS boxes) standing on a shelf, their spines toward the front (-y), a gap here and there."""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); x = -w / 2
    while x < w / 2 - 0.03:
        t = 0.03 if vhs else rnd.uniform(0.018, 0.045); hb = 0.19 if vhs else rnd.uniform(0.17, max(0.18, hmax)); db = 0.105 if vhs else min(depth, rnd.uniform(0.14, 0.22))
        if rnd.random() < 0.07: x += rnd.uniform(0.04, 0.1); continue
        lean = 0.0 if vhs or rnd.random() > 0.1 else rnd.uniform(-0.15, 0.15)
        M_ = Matrix.Translation((x_at + x + t / 2, -depth / 2 + db / 2, z + hb / 2)) @ Matrix.Rotation(lean, 4, 'Y') @ Matrix.Diagonal((t, db, hb, 1))
        r = bmesh.ops.create_cube(bm, size=1.0, matrix=M_)
        col_i = rnd.randrange(64); row = 1 if vhs else 0
        u0, u1 = col_i / 64, (col_i + 1) / 64; v0, v1 = (0.5, 1.0) if row == 0 else (0.0, 0.5)
        for f in {f for v in r['verts'] for f in v.link_faces}:
            for l in f.loops:
                lc = M_.inverted() @ l.vert.co
                l[uvl].uv = (u0 + (lc.x + 0.5) * (u1 - u0), v0 + (lc.z + 0.5) * (v1 - v0))
        x += t + 0.002
    ob = cine._mesh_obj(name, bm, M['spines'], col, smooth=False); ob['lm'] = 'furn'; parts.append(ob)


def etagere(M, col):
    """The black etagere against the back wall: books and tapes, the stereo, the clock, board games on top, and the
    Superman figure on its middle shelf."""
    x0, x1 = -1.6, -0.4; d = 0.4; xc = (x0 + x1) / 2; yc = YB - d / 2; h = 1.95
    parts = shelf_unit('etagere', (xc, yc), (x1 - x0, d, h), 0.0, M, col, rows=4, drawer_at=1, books={0: (0.0, 1.0), 2: (0.0, 0.42)})
    # the stereo on the second shelf from the top: a stack of black components
    zs = [0.06 + k * (h - 0.08) / 4 for k in range(5)]
    for k in range(3): box(f'stereo{k}', (0.43, 0.3, 0.075), (xc + 0.28, yc + 0.02, zs[3] + 0.011 + 0.04 + k * 0.08), M['black'], bev=0.004, collection=col, lm='furn')
    root, ms = cine.import_gltf(PH('mantel_clock_01'), loc=(xc - 0.3, yc - 0.02, zs[3] + 0.011), scale=0.7, collection=col, lm='furn')
    for o in ms:
        for sl in o.material_slots:
            if 'glass' not in sl.material.name.lower(): sl.material = M['black']
    superman(M, col, (xc + 0.05, yc - 0.06, zs[2] + 0.011))
    for k, (cw, cd, c_) in enumerate(((0.5, 0.3, 'red'), (0.42, 0.28, 'blue'), (0.46, 0.26, 'paper'))):   # board games
        box(f'game{k}', (cw, cd, 0.05), (xc - 0.15 + 0.04 * k, yc + 0.02, h + 0.035 + 0.052 * k), M['fig_red'] if c_ == 'red' else M['fig_blue'] if c_ == 'blue' else M['magazine'], rot=(0, 0, 0.04 * k - 0.04), bev=0.003, collection=col, lm='furn')
    return parts


def superman(M, col, at):
    """A 30 cm figure of the Man of Steel: blue suit, red boots, trunks and cape, on a round base."""
    x, y, z = at; parts = []
    def add(o): parts.append(o); return o
    add(cyl('fig_base', 0.05, 0.012, (0, 0, 0.006), M['black'], seg=24, collection=col, lm='furn'))
    for s in (-1, 1):
        add(cyl(f'fig_boot{s}', 0.013, 0.05, (s * 0.022, 0, 0.037), M['fig_red'], seg=10, collection=col, lm='furn'))
        add(cyl(f'fig_leg{s}', 0.012, 0.075, (s * 0.02, 0, 0.1), M['fig_blue'], seg=10, collection=col, lm='furn'))
        add(cyl(f'fig_arm{s}', 0.009, 0.08, (s * 0.045, 0, 0.19), M['fig_blue'], rot=(0, s * 0.25, 0), seg=10, collection=col, lm='furn'))
    add(box('fig_trunks', (0.06, 0.035, 0.03), (0, 0, 0.145), M['fig_red'], bev=0.008, collection=col, lm='furn'))
    add(box('fig_chest', (0.07, 0.04, 0.08), (0, 0, 0.2), M['fig_blue'], bev=0.012, collection=col, lm='furn'))
    add(cyl('fig_head', 0.017, 0.035, (0, 0, 0.262), M['skin_figure'], seg=14, bev=0.008, collection=col, lm='furn'))
    add(box('fig_hair', (0.036, 0.034, 0.012), (0, 0.002, 0.281), M['black'], bev=0.005, collection=col, lm='furn'))
    cape = add(box('fig_cape', (0.07, 0.006, 0.16), (0, 0.03, 0.15), M['fig_red'], rot=(math.radians(12), 0, 0), bev=0.002, collection=col, lm='furn'))
    for o in parts: place(o, Matrix.Translation((x, y, z)))
    return parts


def bike(M, col):
    """Jerry's green road bike hung on the hall's left wall by its front wheel: tyres, rims, hubs and spokes, the
    diamond frame, black drop bars and saddle, the chainring. Drawn in a side view (x forward, z up, from the rear
    hub), then stood nearly upright on the wall."""
    g = M['bike']; parts = []
    def add(o): parts.append(o); o['lm'] = 'furn'; return o
    R = 0.335; rear, front = Vector((0, 0, 0)), Vector((0.98, 0, 0))
    bb, seat, head_t, head_b = Vector((0.41, 0, -0.07)), Vector((0.27, 0, 0.5)), Vector((0.86, 0, 0.52)), Vector((0.89, 0, 0.38))
    X, Z = Vector((1, 0, 0)), Vector((0, 0, 1))
    for k, c in enumerate((rear, front)):
        add(tube(f'bike_tyre{k}', circle(c, R, X, Z, 48), 0.013, M['rubber'], col, closed=True, seg=8))
        add(tube(f'bike_rim{k}', circle(c, R - 0.022, X, Z, 48), 0.008, M['steel'], col, closed=True, seg=6))
        add(tube(f'bike_hub{k}', [c - Vector((0, 0.04, 0)), c + Vector((0, 0.04, 0))], 0.018, M['steel'], col))
        for j in range(16):
            a = j * math.pi / 8; d_ = X * math.cos(a) + Z * math.sin(a)
            add(tube(f'bike_spoke{k}{j}', [c + Vector((0, 0.03 * (1 if j % 2 else -1), 0)), c + d_ * (R - 0.03)], 0.0016, M['steel'], col, seg=4))
    for nm, a, b, r in (('down', head_b, bb, 0.018), ('seat_tube', bb, seat, 0.016), ('top', seat, head_t, 0.015), ('head', head_b, head_t, 0.02),
                        ('chainstay', bb, rear, 0.011), ('seatstay', seat - (seat - bb) * 0.06, rear, 0.010), ('fork', head_b, front, 0.012)):
        add(tube(f'bike_{nm}', [a, b], r, g, col))
    post = seat + (seat - bb).normalized() * 0.1
    add(tube('bike_post', [seat, post], 0.012, M['steel'], col))
    add(box('bike_saddle', (0.25, 0.08, 0.04), post + Vector((0, 0, 0.02)), M['black'], bev=0.014, collection=col))
    stem = head_t + Vector((0.09, 0, 0.03))
    add(tube('bike_stem', [head_t, stem], 0.012, M['steel'], col))
    for s_ in (-1, 1):   # the drops: out to the side, forward, down and back
        y = s_ * 0.2
        add(tube(f'bike_bar{s_}', [stem, stem + Vector((0, y, 0)), stem + Vector((0.08, y, -0.02)), stem + Vector((0.1, y, -0.1)), stem + Vector((0.04, y, -0.15))], 0.012, M['black'], col))
    add(tube('bike_chainring', circle(bb + Vector((0, 0.03, 0)), 0.095, X, Z, 36), 0.004, M['steel'], col, closed=True, seg=6))
    add(tube('bike_crank', [bb + Vector((0, 0.04, 0)), bb + Vector((0.12, 0.05, -0.12))], 0.008, M['steel'], col))
    # on the wall: front wheel up; the bike's plane along the wall, a hand's width out from it
    xw = HALL[0] + 0.24
    F = Matrix.Translation((xw, 3.0, 0.62)) @ Matrix.Rotation(-math.pi / 2, 4, 'Z') @ Matrix.Rotation(math.radians(-74), 4, 'Y')
    for o in parts: place(o, F)
    hook_at = F @ (front + Z * (R - 0.01))
    add(tube('bike_hook', [Vector((HALL[0], hook_at.y, hook_at.z + 0.04)), Vector((hook_at.x, hook_at.y, hook_at.z + 0.04)), Vector((hook_at.x, hook_at.y, hook_at.z - 0.02))], 0.006, M['steel'], col))
    return parts


def hall_things(M, col):
    """The red enamel pendant in the hall, the bathroom's pedestal sink and towel, the speaker by the door, the pipe,
    the intercom and switch, the coat hooks with a suede jacket, the trash can. Returns the bulbs."""
    hx = (HALL[0] + HALL[1]) / 2
    cyl('pendant_cord', 0.003, 0.5, (hx, 2.7, H - 0.25), M['black'], seg=6, bev=0, collection=col, lm='furn')
    sh = lathe('pendant_shade', [(0.0, 0.0), (0.02, 0.0), (0.03, -0.03), (0.16, -0.11), (0.17, -0.125), (0.0, -0.125)], M['red_shade'], loc=(hx, 2.7, H - 0.5), seg=40, collection=col, lm='furn')
    lathe('sink_pedestal', [(0.0, 0.0), (0.12, 0.0), (0.09, 0.05), (0.07, 0.4), (0.09, 0.62), (0.0, 0.62)], M['enamel_white'], loc=(0.3, BACK - 0.2, 0), seg=32, collection=col, lm='furn')
    rounded_slab('sink_basin', 0.52, 0.4, 0.16, 0.12, (0.3, BACK - 0.21, 0.72), M['enamel_white'], collection=col, lm='furn')
    cyl('sink_tap', 0.012, 0.1, (0.3, BACK - 0.06, 0.83), M['chrome'], seg=12, collection=col, lm='furn')
    cloth_panel('bath_towel', 0.36, 0.55, folds=3, depth=0.01, mat=M['red_drawer'], loc=(HALL[1] - 0.02, 3.42, 1.45), rot=(0, 0, math.pi / 2), res=(12, 10), seed=8, collection=col, lm='furn')
    # by the front door: the black speaker, the pipe, the intercom and switch, the hooks and a jacket, the trash can
    box('speaker', (0.3, 0.3, 0.78), (0.9, YB - 0.18, 0.39), M['black'], bev=0.01, collection=col, lm='furn')
    cyl('pipe', 0.03, H, (KITCHEN - 0.04, YB - 0.04, H / 2), M['trim'], seg=20, bev=0, collection=col, lm='furn')
    for z in (0.3, 2.7): cyl(f'pipe_collar{z}', 0.038, 0.03, (KITCHEN - 0.04, YB - 0.04, z), M['trim'], seg=20, bev=0.004, collection=col, lm='furn')
    box('intercom', (0.13, 0.025, 0.2), (DOOR[1] + 0.2, YB - 0.012, 1.45), M['brass'], bev=0.006, collection=col, lm='furn')
    cyl('intercom_grille', 0.035, 0.006, (DOOR[1] + 0.2, YB - 0.026, 1.49), M['trim_dark'], rot=(math.pi / 2, 0, 0), seg=20, collection=col, lm='furn')
    box('switch', (0.075, 0.012, 0.12), (DOOR[1] + 0.2, YB - 0.006, 1.2), M['plastic_white'], bev=0.003, collection=col, lm='furn')
    for k, x in enumerate((DOOR[1] + 0.36, DOOR[1] + 0.5)):
        cyl(f'hook{k}', 0.008, 0.06, (x, YB - 0.03, 1.72), M['brass'], rot=(math.pi / 2, 0, 0), seg=8, collection=col, lm='furn')
    # a suede jacket on the hooks: hung by its collar, the shoulders sloping, the body and sleeves falling straight
    jx = DOOR[1] + 0.43
    coat = [(0.0, 1.76), (0.06, 1.74), (0.2, 1.66), (0.235, 1.58), (0.25, 1.2), (0.235, 1.0), (0.0, 0.98), (-0.235, 1.0), (-0.25, 1.2), (-0.235, 1.58), (-0.2, 1.66), (-0.06, 1.74)]
    jk = slab_profile('jacket', cine.outline(coat, 4), 'y', 0.075, [M['jacket'], M['jacket']], col, bev=0.025, lm='furn')
    jk.location = (jx, YB - 0.045, 0)
    for s_ in (-1, 1): box(f'jacket_sleeve{s_}', (0.08, 0.06, 0.5), (jx + s_ * 0.2, YB - 0.09, 1.3), M['jacket'], rot=(0, s_ * 0.04, 0), bev=0.025, seg=3, collection=col, lm='furn')
    box('jacket_collar', (0.16, 0.05, 0.05), (jx, YB - 0.09, 1.71), M['jacket'], bev=0.02, collection=col, lm='furn')
    lathe('trash_can', [(0.0, 0.0), (0.15, 0.0), (0.17, 0.5), (0.175, 0.52), (0.0, 0.52)], M['black'], loc=(KITCHEN - 0.25, YB - 0.24, 0), seg=32, collection=col, lm='furn')
    return [Vector((hx, 2.7, H - 0.56))]


# ---------------------------------------------------------------- the kitchen
def kitchen(M, col):
    """The almond fridge under its magnets, the slate-blue glass cabinets (cereal), the tiled back counter with the
    sink and the microwave, the run along the right, the peninsula with its boarded face, the cooktop, the cutting
    board, knife block and fruit, the blue bottle; the two navy stools. Returns the under-cabinet light's place."""
    y_back = YB
    # the fridge: two doors (the left narrower, the dispenser in it), handles, the magnet-covered front
    fx0, fx1, fd, fh = KITCHEN + 0.05, KITCHEN + 0.95, 0.72, 1.76
    box('fridge_body', (fx1 - fx0, fd - 0.04, fh), ((fx0 + fx1) / 2, y_back - fd / 2 - 0.02, fh / 2 + 0.02), M['almond'], bev=0.015, collection=col, lm='furn')
    split = fx0 + 0.4
    for k, (a, b) in enumerate(((fx0 + 0.005, split - 0.004), (split + 0.004, fx1 - 0.005))):
        dr = box(f'fridge_door{k}', (b - a, 0.05, fh - 0.06), ((a + b) / 2, y_back - fd - 0.005, fh / 2 + 0.04), M['fridge'], bev=0.012, collection=col, lm='furn')
        # 0..1 across the pair of doors, so the magnets run on across the gap
        me = dr.data; uv = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
        for poly in me.polygons:
            for li in poly.loop_indices:
                c = me.vertices[me.loops[li].vertex_index].co + dr.location
                uv.data[li].uv = ((c.x - fx0) / (fx1 - fx0), (c.z - 0.04) / (fh - 0.06))
        box(f'fridge_handle{k}', (0.025, 0.04, 0.7), ((b - 0.04) if k == 0 else (a + 0.04), y_back - fd - 0.05, 1.05), M['almond'], bev=0.008, collection=col, lm='furn')
    box('fridge_grille', (fx1 - fx0 - 0.04, 0.02, 0.06), ((fx0 + fx1) / 2, y_back - fd - 0.0, 0.05), M['trim_dark'], bev=0.003, collection=col, lm='furn')
    rnd = random.Random(21)
    for k in range(5):   # snacks and a box of crackers on top
        w_, h_ = rnd.uniform(0.12, 0.25), rnd.uniform(0.05, 0.14)
        box(f'fridge_top{k}', (w_, 0.2, h_), (fx0 + 0.12 + k * 0.17, y_back - 0.32 + rnd.uniform(-0.05, 0.05), fh + 0.02 + h_ / 2), M['cereal'], rot=(0, 0, rnd.uniform(-0.3, 0.3)), bev=0.005, collection=col, lm='furn')
    # the back counter, right of the fridge: slate base cabinets, a grey top, the tiled splash, the sink, the microwave
    cx0, cx1, cd = fx1 + 0.02, RIGHT, 0.62
    base_run('back_counter', (cx0, y_back - cd), (cx1, y_back), M, col)
    box('splash', (cx1 - cx0, 0.012, 0.6), ((cx0 + cx1) / 2, y_back - 0.006, COUNTER_H + 0.3), M['tile'], bev=0, collection=col, lm='arch')
    box('sink_bowl', (0.5, 0.4, 0.02), (cx1 - 0.42, y_back - 0.32, COUNTER_H + 0.003), M['steel'], bev=0.01, collection=col, lm='furn')
    lathe('faucet', [(0.0, 0.0), (0.025, 0.0), (0.02, 0.02), (0.012, 0.05), (0.01, 0.25), (0.0, 0.26)], M['chrome'], loc=(cx1 - 0.42, y_back - 0.08, COUNTER_H), seg=16, collection=col, lm='furn')
    sp = cyl('faucet_spout', 0.009, 0.18, (cx1 - 0.42, y_back - 0.16, COUNTER_H + 0.24), M['chrome'], rot=(math.pi / 2, 0, 0), seg=12, collection=col, lm='furn')
    box('microwave', (0.5, 0.36, 0.29), (cx0 + 0.3, y_back - 0.24, COUNTER_H + 0.145), M['plastic_white'], bev=0.012, collection=col, lm='furn')
    box('microwave_door', (0.33, 0.006, 0.2), (cx0 + 0.24, y_back - 0.422, COUNTER_H + 0.15), M['glass_dark'], bev=0.004, collection=col, lm='furn')
    box('microwave_panel', (0.1, 0.006, 0.22), (cx0 + 0.47, y_back - 0.422, COUNTER_H + 0.15), M['trim'], bev=0.003, collection=col, lm='furn')
    cyl('towel_roll', 0.06, 0.28, (cx0 + 0.75, y_back - 0.08, 1.38), M['paper'], rot=(0, math.pi / 2, 0), seg=24, collection=col, lm='furn')
    # the glass cabinets: over the fridge and over the counter, cereal and dishes behind the panes
    wall_cabinets('cab_fridge', fx0 - 0.02, fx1 + 0.01, 1.86, RAIL, M, col, rows=1)
    wall_cabinets('cab_counter', cx0, cx1, 1.48, RAIL, M, col, rows=3)
    # the run along the right (the set's sink wall), the peninsula and its return toward the fridge
    base_run('right_run', (RIGHT - cd, PENINSULA[3]), (RIGHT, y_back - cd), M, col, face='x')
    x0, x1, yf, yb_ = PENINSULA
    base_run('peninsula', (x0, yf), (x1, yb_), M, col, boarded=('-y', '-x'), overhang=0.04)
    base_run('peninsula_return', (x0, yb_), (x0 + 0.6, 0.48), M, col, boarded=('-x', '+y'), overhang=0.04)
    # the cooktop: white enamel, four burners with black grates and knobs
    kx, ky = 3.95, (yf + yb_) / 2
    box('cooktop', (0.62, 0.5, 0.012), (kx, ky, COUNTER_H + 0.006), M['enamel_white'], bev=0.006, collection=col, lm='furn')
    for i, (dx, dy) in enumerate(((-0.15, -0.12), (0.15, -0.12), (-0.15, 0.12), (0.15, 0.12))):
        cyl(f'burner{i}', 0.045, 0.016, (kx + dx, ky + dy, COUNTER_H + 0.018), M['cast_iron'], seg=20, collection=col, lm='furn')
        for a in (0, math.pi / 2): box(f'grate{i}{a:.1f}', (0.2, 0.012, 0.012), (kx + dx, ky + dy, COUNTER_H + 0.03), M['cast_iron'], rot=(0, 0, a), bev=0, collection=col, lm='furn')
        cyl(f'knob{i}', 0.014, 0.02, (kx - 0.24 + 0.07 * i, yf + 0.01, COUNTER_H - 0.06), M['black'], rot=(math.pi / 2, 0, 0), seg=12, collection=col, lm='furn')
    lathe('pot', [(0.0, 0.0), (0.1, 0.0), (0.105, 0.12), (0.11, 0.125), (0.0, 0.125)], M['black'], loc=(kx + 0.15, ky + 0.12, COUNTER_H + 0.035), seg=28, collection=col, lm='furn')
    lathe('kettle', [(0.0, 0.0), (0.09, 0.0), (0.1, 0.05), (0.08, 0.14), (0.03, 0.18), (0.012, 0.21), (0.0, 0.21)], M['fig_blue'], loc=(kx - 0.15, ky - 0.12, COUNTER_H + 0.035), seg=28, collection=col, lm='furn')
    # on the counter: the cutting board with a paper on it, the knife block, the fruit bowl, the blue bottle
    root, ms = cine.import_gltf(PH('wooden_cutting_board'), loc=(2.88, -0.3, COUNTER_H), rot=(0, 0, 0.06), scale=1.25, collection=col, lm='furn')
    box('card', (0.13, 0.19, 0.002), (2.9, -0.3, COUNTER_H + 0.054), M['paper'], rot=(0, 0, -0.25), bev=0, collection=col, lm='furn')
    box('knife_block', (0.1, 0.2, 0.22), (3.45, -0.22, COUNTER_H + 0.1), M['wood_block'], rot=(math.radians(-18), 0, 0.3), bev=0.008, collection=col, lm='furn')
    for k in range(5): box(f'knife{k}', (0.016, 0.025, 0.09), (3.45 + 0.012 * (k - 2), -0.2 - 0.03 * (k % 2), COUNTER_H + 0.25), M['black'], rot=(math.radians(-18), 0, 0.3), bev=0.004, collection=col, lm='furn')
    lathe('fruit_bowl', [(0.0, 0.0), (0.06, 0.0), (0.13, 0.06), (0.14, 0.075), (0.128, 0.075), (0.05, 0.012), (0.0, 0.012)], M['bowl'], loc=(3.3, -0.45, COUNTER_H), seg=36, collection=col, lm='furn')
    cine.import_gltf(PH('bananas'), loc=(3.3, -0.44, COUNTER_H + 0.02), rot=(0, 0, 0.5), collection=col, lm='furn')
    for k, (dx, dy) in enumerate(((-0.06, -0.05), (0.05, -0.06), (0.0, 0.06))):
        cine.import_gltf(PH('food_apple_01'), loc=(3.3 + dx, -0.45 + dy, COUNTER_H + 0.02), rot=(0, 0, k), scale=0.8, collection=col, lm='furn')
    lathe('bottle', [(0.0, 0.0), (0.035, 0.0), (0.036, 0.2), (0.03, 0.23), (0.012, 0.27), (0.012, 0.31), (0.0, 0.31)], M['bottle_blue'], loc=(3.08, -0.18, COUNTER_H), seg=20, collection=col, lm='furn')
    for k, (x, y) in enumerate(STOOLS): stool(f'stool{k}', x, y, M, col)
    return [Vector(((cx0 + cx1) / 2, y_back - 0.2, 1.43))]


def base_run(name, p0, p1, M, col, face='y', boarded=(), overhang=0.03):
    """A run of base cabinets from p0 to p1 (plan corners): a recessed toe kick, the carcass (slate doors on `face`, or
    the boarded grey on the `boarded` sides: '-y', '+y', '-x'), the grey laminate top overhanging the boarded sides."""
    (x0, y0), (x1, y1) = p0, p1; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; w, d = x1 - x0, y1 - y0
    box(f'{name}_kick', (w - 0.1, d - 0.1, 0.1), (cx, cy, 0.05), M['kick'], bev=0, collection=col, lm='furn')
    box(f'{name}_body', (w, d, COUNTER_H - 0.14), (cx, cy, 0.1 + (COUNTER_H - 0.14) / 2), M['board'] if boarded else M['cabinet'], bev=0.004, collection=col, lm='furn')
    if not boarded:   # the doors on the face toward the room
        n = max(1, round((w if face == 'y' else d) / 0.45))
        for k in range(n):
            if face == 'y':
                a = x0 + k * w / n; box(f'{name}_door{k}', (w / n - 0.012, 0.018, COUNTER_H - 0.2), (a + w / (2 * n), y0 - 0.009, 0.1 + (COUNTER_H - 0.14) / 2), M['cabinet'], bev=0.006, collection=col, lm='furn')
            else:
                a = y0 + k * d / n; box(f'{name}_door{k}', (0.018, d / n - 0.012, COUNTER_H - 0.2), (x0 - 0.009, a + d / (2 * n), 0.1 + (COUNTER_H - 0.14) / 2), M['cabinet'], bev=0.006, collection=col, lm='furn')
    ox0 = overhang if '-x' in boarded else 0.015; oy0 = overhang if '-y' in boarded else 0.015; oy1 = overhang if '+y' in boarded else 0.0
    box(f'{name}_top', (w + ox0, d + oy0 + oy1, 0.04), (cx - ox0 / 2, cy + (oy1 - oy0) / 2, COUNTER_H - 0.02), M['laminate'], bev=0.012, seg=3, collection=col, lm='furn')


def wall_cabinets(name, x0, x1, z0, z1, M, col, rows=2, depth=0.34):
    """Slate-blue wall cabinets with glazed doors: the carcass, the doors' frames and mullions, and behind them shelves of
    cereal boxes (the panes are left out: clear glass reads as nothing at this scale, and hides what is behind it)."""
    y1 = YB; y0 = y1 - depth; w = x1 - x0; n = max(1, round(w / 0.46))
    box(f'{name}_back', (w, 0.012, z1 - z0), ((x0 + x1) / 2, y1 - 0.006, (z0 + z1) / 2), M['cabinet'], bev=0, collection=col, lm='furn')
    for s, x in ((-1, x0), (1, x1)): box(f'{name}_side{s}', (0.02, depth, z1 - z0), (x - s * 0.01, (y0 + y1) / 2, (z0 + z1) / 2), M['cabinet'], bev=0.003, collection=col, lm='furn')
    for z in (z0 + 0.01, z1 - 0.01): box(f'{name}_tb{z:.2f}', (w, depth, 0.02), ((x0 + x1) / 2, (y0 + y1) / 2, z), M['cabinet'], bev=0.003, collection=col, lm='furn')
    rnd = random.Random(len(name) * 7)
    zs = [z0 + 0.02 + k * (z1 - z0 - 0.04) / rows for k in range(rows + 1)]
    for k, (a, b) in enumerate(zip(zs, zs[1:])):
        if k: box(f'{name}_shelf{k}', (w - 0.04, depth - 0.04, 0.015), ((x0 + x1) / 2, (y0 + y1) / 2 + 0.01, a), M['cabinet'], bev=0, collection=col, lm='furn')
        x = x0 + 0.04
        while x < x1 - 0.1:   # cereal boxes, side by side, fronts toward the room (an atlas of 8 x 4 fronts)
            bw, bh = rnd.uniform(0.17, 0.22), min(b - a - 0.04, rnd.uniform(0.24, 0.3))
            bx = box(f'{name}_cereal{k}_{x:.2f}', (bw, 0.065, bh), (x + bw / 2, y1 - 0.12, a + 0.008 + bh / 2), M['cereal'], bev=0.003, collection=col, lm='furn')
            i, j = rnd.randrange(8), rnd.randrange(4); me = bx.data; uv = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
            for poly in me.polygons:
                for li in poly.loop_indices:
                    c = me.vertices[me.loops[li].vertex_index].co
                    uv.data[li].uv = ((i + 0.5 + c.x / bw) / 8, (j + 0.5 + c.z / bh) / 4)
            x += bw + rnd.uniform(0.005, 0.03)
    # the doors: frames of slate, the glass a little in from them, a mullion across
    for k in range(n):
        a = x0 + k * w / n; b = a + w / n; cx = (a + b) / 2; dz = z1 - z0
        for s in (-1, 1): box(f'{name}_stile{k}{s}', (0.045, 0.022, dz - 0.01), (cx + s * (w / n / 2 - 0.025), y0 - 0.011, (z0 + z1) / 2), M['cabinet'], bev=0.004, collection=col, lm='furn')
        for z in (z0 + 0.025, z1 - 0.025): box(f'{name}_rail{k}{z:.2f}', (w / n - 0.05, 0.022, 0.045), (cx, y0 - 0.011, z), M['cabinet'], bev=0.004, collection=col, lm='furn')
        box(f'{name}_mullion{k}', (w / n - 0.05, 0.018, 0.022), (cx, y0 - 0.011, z0 + dz * 0.55), M['cabinet'], bev=0.003, collection=col, lm='furn')
        box(f'{name}_knob{k}', (0.015, 0.02, 0.04), (b - 0.05 if k % 2 == 0 else a + 0.05, y0 - 0.03, z0 + 0.08), M['brass'], bev=0.004, collection=col, lm='furn')


def stool(name, x, y, M, col):
    """A navy-painted wooden counter stool: a square seat with rounded edges, four splayed legs, two rungs of
    stretchers."""
    parts = []; n = M['navy']; hs = 0.74
    def add(o): parts.append(o); return o
    add(rounded_slab(f'{name}_seat', 0.38, 0.38, 0.04, 0.05, (0, 0, hs - 0.02), n, collection=col, lm='furn'))
    add(box(f'{name}_apron', (0.32, 0.32, 0.06), (0, 0, hs - 0.07), n, bev=0.006, collection=col, lm='furn'))
    for sx in (-1, 1):
        for sy in (-1, 1):
            top, foot = Vector((sx * 0.14, sy * 0.14, hs - 0.04)), Vector((sx * 0.19, sy * 0.19, 0.0))
            d_ = top - foot; lg = add(box(f'{name}_leg{sx}{sy}', (0.04, 0.04, d_.length), (top + foot) / 2, n, bev=0.006, collection=col, lm='furn'))
            lg.rotation_euler = d_.to_track_quat('Z', 'Y').to_euler()
    for z, r in ((0.22, 0.177), (0.46, 0.163)):
        for a in range(4):
            ang = a * math.pi / 2
            st = add(box(f'{name}_rung{z}{a}', (2 * r, 0.028, 0.028), (math.cos(ang) * r, math.sin(ang) * r, z), n, rot=(0, 0, ang + math.pi / 2), bev=0.004, collection=col, lm='furn'))
    for o in parts: place(o, Matrix.Translation((x, y, 0)))
    return parts


def pictures(M, col):
    """The pier's framed photographs and the picture over the speaker; the sconces (returns their bulbs)."""
    for k, (z, sz) in enumerate(((1.62, (0.24, 0.3)), (1.22, (0.3, 0.24)))):
        picture(f'pier_photo{k}', f'photo{k}', ((ALCOVE[1] + (-1.6)) / 2, YB, z), sz, (0, -1), M, col, mat_w=0.03)
    picture('photo_door', 'photo2', (0.95, YB, 1.7), (0.3, 0.38), (0, -1), M, col, mat_w=0.04)
    bulbs = []
    for k, (p, n) in enumerate((((LEFT, -1.75, 1.95), (1, 0)), ((LEFT, 0.55, 1.95), (1, 0)), (((ALCOVE[1] - 1.6) / 2, YB, 2.05), (0, -1)),
                                ((-0.3 - 0.21, YB, 2.0), (0, -1)), ((DOOR[1] + 0.33, YB, 2.1), (0, -1)), ((2.3, BACK, 2.0), (0, -1)))):
        bulbs.append(sconce(f'sconce{k}', p, n, M, col))
    return bulbs


# ---------------------------------------------------------------- light
SUN = (1.0, 0.86, 0.68)
SKY = (0.78, 0.86, 1.0)
WARM = (1.0, 0.78, 0.52)


def lights(sconce_bulbs, lamp_bulbs, pendant, under_cab):
    """The afternoon sun through the alcove's blinds and the bathroom's window, the sky at those windows, the sconces
    (uplit), the table lamp, the hall's pendant, the light under the kitchen cabinets, the corridor's ceiling light;
    and the daylight from the living room's windows on the side the cut-away removes. Returns the lights."""
    out = []
    def light(name, kind, loc, energy, colour, **kw):
        ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = colour
        for k, v in kw.items(): setattr(ld, k, v)
        ob = cine.link(bpy.data.objects.new(name, ld)); ob.location = loc; out.append(ob)
        if kind == 'AREA': ob.visible_camera = False; ob.visible_glossy = False   # light, not a thing in the room
        return ob
    def aim(ob, d): ob.rotation_euler = Vector(d).to_track_quat('-Z', 'Y').to_euler()
    sun = light('sun', 'SUN', (0, 6, 6), 9.0, SUN, angle=math.radians(0.6)); aim(sun, (-0.32, -1.0, -0.72))
    for k, c in enumerate(WINDOWS):
        aim(light(f'sky{k}', 'AREA', (c, D / 2 + 0.05, (WIN_Z[0] + WIN_Z[1]) / 2), 55.0, SKY, shape='RECTANGLE', size=0.55, size_y=WIN_Z[1] - WIN_Z[0]), (0, -1, 0))
    aim(light('sky_bath', 'AREA', ((BATH_WIN[0] + BATH_WIN[1]) / 2, D / 2 + 0.05, sum(BATH_WIN_Z) / 2), 18.0, SKY, shape='RECTANGLE', size=0.5, size_y=0.85), (0, -1, 0))
    for k, p in enumerate(sconce_bulbs): light(f'sconce_bulb{k}', 'POINT', p, 22.0, WARM, shadow_soft_size=0.03)
    for k, p in enumerate(lamp_bulbs): light(f'lamp_bulb{k}', 'POINT', p, 26.0, WARM, shadow_soft_size=0.05)
    for k, p in enumerate(pendant): light(f'pendant_bulb{k}', 'POINT', p, 14.0, WARM, shadow_soft_size=0.03)
    for k, p in enumerate(under_cab): aim(light(f'undercab{k}', 'AREA', p, 14.0, (1.0, 0.92, 0.8), shape='RECTANGLE', size=1.0, size_y=0.06), (0, 0, -1))
    for k, x in enumerate((1.8, 3.6)): aim(light(f'corridor{k}', 'AREA', (x, (YB + TW + BACK) / 2, H - 0.04), 40.0, WARM, shape='DISK', size=0.3), (0, 0, -1))
    # the living room's own windows are on the cut-away's side: their daylight, soft, from the front
    for k, x in enumerate((-2.6, 0.4, 3.2)):
        aim(light(f'front_day{k}', 'AREA', (x, -D / 2 + 0.2, 1.7), 140.0, (1.0, 0.94, 0.86), shape='RECTANGLE', size=1.6, size_y=1.4), (0, 1, -0.15))
    return out
