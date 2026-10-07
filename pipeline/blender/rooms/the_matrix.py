# The Matrix · the red pill. A salon of a decayed belle-epoque hotel at night: cream boiserie gone ochre, its silk
# panels peeling, two tall windows with lace and tattered drapes against the rain, a dark marble fireplace (cold),
# crystal-and-brass sconces, and in front of the fire the two oxblood wingback chairs facing each other over a small
# pedestal table with a glass of water. The light is the film's: warm sconces against a green-grey night.
import math, os, random
import bmesh
from mathutils import Vector, Matrix
import cine
from cine import box, cyl, material, moulding, cloth_panel, lathe

W, D, H = 9.6, 7.6, 3.0           # the room fills the module, at its full height
T = 0.14                          # wall thickness
BACK, LEFT = D / 2 - T, -W / 2 + T  # inner faces of the back and left walls
TEX = os.path.join(cine.OUT, 'textures', 'the-matrix')
tx = lambda n: os.path.join(TEX, n)
PH = lambda n: os.path.join(cine.CACHE, 'polyhaven', n, f'{n}_1k.gltf')

DOOR_X, DOOR_W, DOOR_H = -2.95, 1.36, 2.5          # the door to the next room (back wall)
WINDOWS = (-1.25, 1.35)                            # window centres along the left wall (y)
WIN_W, WIN_Z = 1.32, (0.45, 2.62)                  # opening width, sill and head heights
CHAIRS = {'morpheus': (-1.05, 2.0, math.pi / 2), 'neo': (1.05, 2.0, -math.pi / 2)}   # x, y, facing (z rotation)
TABLE = (0.0, 2.0)
SEAT_TOP = 0.52                                    # the chairs' cushion (Rocketbox's seated clips sit at this height)
SCONCES = [('back', -1.565, 1.85), ('back', 1.565, 1.85), ('left', 0.05, 1.85)]
# the sconces of the walls the cut-away removes: their light is real (the room has them), their fixtures unseen
PHANTOM_BULBS = [(4.5, y + d, 1.95) for y in (-0.9, 2.1) for d in (-0.15, 0.15)] + [(x + d, -3.5, 1.95) for x in (-1.2, 1.8) for d in (-0.15, 0.15)]


# ---------------------------------------------------------------- materials
def mats():
    M = {}
    M['floor'] = material('floor', rough=0.7, maps={'color': tx('floor_color.jpg'), 'normal': tx('floor_normal.jpg'), 'rough': tx('floor_rough.jpg')}, scale=2.2, normal_strength=0.6, specular=0.4)
    M['boiserie'] = material('boiserie', rough=0.62, maps={'color': tx('boiserie_color.jpg')}, scale=1.4, specular=0.45)
    M['wallpaper'] = material('wallpaper', rough=0.85, maps={'color': tx('wallpaper_color.jpg'), 'normal': tx('wallpaper_normal.jpg')}, scale=1.2, normal_strength=0.5)
    M['plaster'] = material('plaster', rough=0.92, maps={'color': tx('plaster_color.jpg')}, scale=1.3)
    M['kerb'] = material('kerb', (0.30, 0.27, 0.21), rough=0.9)
    M['window_paint'] = material('window_paint', (0.45, 0.42, 0.33), rough=0.55)
    M['marble'] = material('marble', rough=0.22, maps={'color': tx('marble_color.jpg')}, scale=0.9, coat=0.4, coat_rough=0.15)
    M['iron'] = material('cast_iron', (0.025, 0.024, 0.023), rough=0.62, metal=0.6)
    M['soot'] = material('soot', (0.012, 0.011, 0.010), rough=0.95)
    M['char'] = material('charred_log', (0.035, 0.028, 0.022), rough=0.9)
    M['mahogany'] = material('mahogany', (0.12, 0.045, 0.025), rough=0.32, coat=0.5, coat_rough=0.2)
    M['door'] = material('door_paint', rough=0.55, maps={'color': tx('boiserie_color.jpg')}, scale=1.6)
    M['brass'] = material('brass', (0.72, 0.52, 0.26), rough=0.32, metal=1.0)
    M['shade'] = material('lampshade', (0.86, 0.72, 0.52), rough=0.8, emission=(1.0, 0.74, 0.44), emission_strength=4.0)
    M['candle'] = material('candle_sleeve', (0.86, 0.82, 0.72), rough=0.5)
    M['leather_tuft'] = material('leather_tufted', rough=0.42, maps={'color': tx('leather_color.jpg'), 'normal': tx('tufting_normal.jpg')}, scale=0.42, normal_strength=1.2, coat=0.25, coat_rough=0.35)
    M['leather'] = material('leather', rough=0.45, maps={'color': tx('leather_color.jpg'), 'normal': tx('leather_normal.jpg')}, scale=0.42, normal_strength=0.5, coat=0.25, coat_rough=0.35)
    M['chair_wood'] = material('chair_wood', (0.05, 0.025, 0.015), rough=0.35, coat=0.4)
    M['drape'] = material('drape', rough=0.86, maps={'color': tx('drape_color.jpg'), 'normal': tx('drape_normal.jpg')}, scale=0.6, normal_strength=0.5, sheen=0.35, sheen_tint=(0.35, 0.38, 0.3))
    M['lace'] = material('lace', rough=0.9, maps={'color': tx('lace.png'), 'alpha': tx('lace.png')}, scale=0.5)
    M['glass_view'] = material('window_view', (0.02, 0.03, 0.035), rough=0.05)
    M['rug'] = material('rug', rough=0.95, maps={'color': tx('rug_color.jpg')}, scale=1.0)
    M['glass'] = material('drinking_glass', (0.9, 0.92, 0.92), rough=0.03)
    M['water'] = material('water', (0.8, 0.85, 0.85), rough=0.02)
    M['ceiling'] = material('ceiling', rough=0.9, maps={'color': tx('ceiling_color.jpg')}, scale=1.4)
    M['debris'] = material('debris', rough=0.95, maps={'color': tx('plaster_color.jpg')}, scale=0.4)
    M['sheet'] = material('dust_sheet', (0.33, 0.32, 0.28), rough=0.95)
    for k in ('glass', 'water'):   # real glass in the renders; the web draws its own (glass inside the case's glass would vanish)
        p = M[k].node_tree.nodes['Principled BSDF']; p.inputs['Transmission Weight'].default_value = 1.0; p.inputs['IOR'].default_value = 1.5 if k == 'glass' else 1.33
    return M


# ---------------------------------------------------------------- helpers
SKIRT = [(0, 0), (0.026, 0), (0.026, 0.15), (0.02, 0.17), (0.012, 0.19), (0.008, 0.2), (0, 0.2)]
DADO = [(0, 0), (0.016, 0.004), (0.03, 0.016), (0.034, 0.03), (0.028, 0.045), (0.014, 0.056), (0, 0.06)]
FRAME = [(0, 0), (0.008, 0.002), (0.016, 0.01), (0.018, 0.018), (0.012, 0.026), (0, 0.03)]
CORNICE = [(0, 0), (0.02, 0), (0.02, 0.025), (0.035, 0.03), (0.06, 0.06), (0.085, 0.1), (0.11, 0.13), (0.12, 0.16), (0.12, 0.2),
           (0.145, 0.215), (0.16, 0.24), (0.16, 0.28), (0, 0.28)]


class Wall:
    """One of the two full walls, seen from the room: `u` runs along it, `out` points into the room."""
    def __init__(self, side):
        self.side = side
        if side == 'back': self.out = Vector((0, -1, 0)); self.at = lambda u, o, z: Vector((u, BACK - o, z))
        else: self.out = Vector((1, 0, 0)); self.at = lambda u, o, z: Vector((LEFT + o, u, z))
        self.run = (LEFT, 4.66) if side == 'back' else (-3.66, BACK)

    def plane(self, name, u0, u1, z0, z1, o, mat, col, **props):
        """A flat rectangle on the wall, `o` metres out from its face."""
        c = self.at((u0 + u1) / 2, o, (z0 + z1) / 2)
        size = (u1 - u0, 0.004, z1 - z0) if self.side == 'back' else (0.004, u1 - u0, z1 - z0)
        return box(name, size, c, mat, bev=0, collection=col, **props)

    def slab(self, name, u0, u1, z0, z1, o, t, mat, col, bev=0.004, **props):
        """A board standing `o` out from the wall face, `t` thick."""
        c = self.at((u0 + u1) / 2, o + t / 2, (z0 + z1) / 2)
        size = (u1 - u0, t, z1 - z0) if self.side == 'back' else (t, u1 - u0, z1 - z0)
        return box(name, size, c, mat, bev=bev, collection=col, **props)

    def run_h(self, name, u0, u1, z, profile, mat, col, o=0.0, **props):
        """A horizontal moulding along the wall at height z (profile: out from the face, up)."""
        return moulding(name, self.at(u0, o, z), self.at(u1, o, z), self.out, profile, mat, collection=col, **props)

    def rect_frame(self, name, u0, u1, z0, z1, o, mat, col, **props):
        """A small moulded frame round a panel field."""
        obs = []
        for k, (a, b) in enumerate(((self.at(u0, o, z0), self.at(u1, o, z0)), (self.at(u0, o, z1), self.at(u1, o, z1)))):
            prof = FRAME if k == 0 else [(x, -y) for x, y in FRAME]
            obs.append(moulding(f'{name}_h{k}', a, b, self.out, prof, mat, collection=col, **props))
        for k, u in enumerate((u0, u1)):
            a, b = self.at(u, o, z0), self.at(u, o, z1)
            prof = [(x, y if k == 0 else -y) for x, y in FRAME]
            ob = moulding(f'{name}_v{k}', a, b, self.out, prof, mat, collection=col, **props)
            obs.append(ob)
        return obs


def place(ob, M):
    """Move an object built about the origin into a frame M (a chair's). matrix_world is stale right after
    setting location or rotation, so compose with matrix_basis."""
    ob.matrix_basis = M @ ob.matrix_basis
    return ob


# ---------------------------------------------------------------- architecture
def walls(M, arch, furn, phantom):
    out = []
    box('subfloor', (W, D, 0.03), (0, 0, -0.027), M['kerb'], bev=0, collection=arch, lm='arch')
    box('floor', (W - 2 * T + 0.02, D - 2 * T + 0.02, 0.02), (-0.0, 0.0, -0.01), M['floor'], bev=0.0, collection=arch, lm='arch')
    # the backings: plaster, behind the boiserie (seen only where the paper has torn away)
    box('back_backing', (W, T, H), (0, D / 2 - T / 2, H / 2), M['plaster'], bev=0, collection=arch, lm='arch')
    _left_backing(M, arch)
    for side in ('back', 'left'): _boiserie(Wall(side), M, arch, furn)
    for y in WINDOWS: _window(y, M, arch, furn)
    _door(M, arch, furn)
    # the cut-away: front and right walls end in a low kerb
    box('kerb_front', (W, T, 0.22), (0, -D / 2 + T / 2, 0.11), M['kerb'], bev=0.002, collection=arch, lm='arch')
    box('kerb_right', (T, D - 2 * T, 0.22), (W / 2 - T / 2, 0, 0.11), M['kerb'], bev=0.002, collection=arch, lm='arch')
    # phantoms: the ceiling and the missing walls, for the bounce light (never exported)
    box('ceiling', (W, D, 0.04), (0, 0, H + 0.02), M['ceiling'], bev=0, collection=phantom, bake_only=1)
    box('front_wall', (W, T, H - 0.22), (0, -D / 2 + T / 2, 0.22 + (H - 0.22) / 2), M['boiserie'], bev=0, collection=phantom, bake_only=1)
    box('right_wall', (T, D, H - 0.22), (W / 2 - T / 2, 0, 0.22 + (H - 0.22) / 2), M['boiserie'], bev=0, collection=phantom, bake_only=1)
    return out


def _left_backing(M, arch):
    """The left wall in pieces around its two window openings."""
    x = -W / 2 + T / 2; z0, z1 = WIN_Z; edges = [-D / 2]
    for c in WINDOWS: edges += [c - WIN_W / 2, c + WIN_W / 2]
    edges.append(BACK)
    for k in range(0, len(edges), 2):
        a, b = edges[k], edges[k + 1]
        box(f'left_backing_{k}', (T, b - a, H), (x, (a + b) / 2, H / 2), M['plaster'], bev=0, collection=arch, lm='arch')
    for c in WINDOWS:
        box(f'left_sill_{c}', (T, WIN_W, z0), (x, c, z0 / 2), M['plaster'], bev=0, collection=arch, lm='arch')
        box(f'left_lintel_{c}', (T, WIN_W, H - z1), (x, c, (H + z1) / 2), M['plaster'], bev=0, collection=arch, lm='arch')


def _bays(wall):
    """The panel bays of a wall: (u0, u1, what), with the openings and the fireplace left out."""
    if wall.side == 'back':
        cuts = [(DOOR_X - DOOR_W / 2 - 0.12, DOOR_X + DOOR_W / 2 + 0.12, 'door'), (-0.98, 0.98, 'fire')]
        stops = [LEFT, -3.75, -2.15, -0.98, 0.98, 2.15, 3.4, 4.66]
    else:
        cuts = [(c - WIN_W / 2 - 0.12, c + WIN_W / 2 + 0.12, 'window') for c in WINDOWS]
        stops = [-3.66, -2.03, -0.47, 0.57, 2.13, BACK]
    bays = []
    for a, b in zip(stops, stops[1:]):
        what = next((w for c0, c1, w in cuts if abs(c0 - a) < 0.05 and abs(c1 - b) < 0.05), 'panel')
        bays.append((a, b, what))
    return bays


def _boiserie(wall, M, arch, furn):
    rnd = random.Random(7 if wall.side == 'back' else 11)
    s = wall.side
    u0, u1 = wall.run
    wall.run_h(f'{s}_skirting', u0, u1, 0.0, SKIRT, M['boiserie'], arch, lm='arch')
    wall.run_h(f'{s}_cornice', u0, u1, H - 0.28, CORNICE, M['boiserie'], arch, lm='arch')
    for i, (a, b, what) in enumerate(_bays(wall)):
        n = f'{s}_bay{i}'
        if what in ('door', 'window'): continue
        if what == 'fire':
            # above the mantel: a silk panel for the mirror to hang on
            wall.slab(f'{n}_board', a, b, 1.42, H - 0.28, 0.0, 0.012, M['boiserie'], arch, lm='arch')
            wall.plane(f'{n}_paper', a + 0.1, b - 0.1, 1.55, H - 0.4, 0.016, M['wallpaper'], arch, lm='arch')
            wall.rect_frame(f'{n}_frame', a + 0.1, b - 0.1, 1.55, H - 0.4, 0.012, M['boiserie'], arch, lm='arch')
            continue
        # the dado: a board, a raised panel, the rail
        wall.slab(f'{n}_dado', a, b, 0.2, 0.9, 0.0, 0.016, M['boiserie'], arch, lm='arch')
        wall.slab(f'{n}_dado_panel', a + 0.09, b - 0.09, 0.3, 0.8, 0.016, 0.014, M['boiserie'], arch, bev=0.01, lm='arch')
        wall.run_h(f'{n}_rail', a, b, 0.9, DADO, M['boiserie'], arch, lm='arch')
        # the upper panel: a board, a silk field in a moulded frame; some fields torn to the plaster
        wall.slab(f'{n}_board', a, b, 0.96, H - 0.28, 0.0, 0.012, M['boiserie'], arch, lm='arch')
        f0, f1, z0, z1 = a + 0.11, b - 0.11, 1.08, H - 0.42
        tear = rnd.random() < 0.55
        if tear:
            zt = z0 + (z1 - z0) * (0.18 + 0.4 * rnd.random())
            wall.plane(f'{n}_plaster', f0, f1, z0, z1, 0.013, M['plaster'], arch, lm='arch')
            _torn_paper(wall, f'{n}_paper', f0, f1, zt, z1, 0.016, M['wallpaper'], arch, rnd)
            _curls(wall, f'{n}_curl', f0, f1, zt, M['wallpaper'], furn, rnd)
        else:
            wall.plane(f'{n}_paper', f0, f1, z0, z1, 0.016, M['wallpaper'], arch, lm='arch')
        wall.rect_frame(f'{n}_frame', f0, f1, z0, z1, 0.012, M['boiserie'], arch, lm='arch')
        # a slim stile at the bay's edge
        wall.slab(f'{n}_stile', a - 0.03, a + 0.03, 0.96, H - 0.28, 0.012, 0.01, M['boiserie'], arch, lm='arch')


def _torn_paper(wall, name, u0, u1, z_tear, z1, o, mat, col, rnd):
    """The silk paper still hanging from the top of its field, its lower edge torn ragged."""
    bm = bmesh.new(); n = 26
    top = [bm.verts.new(wall.at(u0 + (u1 - u0) * i / n, o, z1)) for i in range(n + 1)]
    edge = []
    for i in range(n + 1):
        z = z_tear + (rnd.random() - 0.3) * 0.12 + 0.08 * math.sin(i * 0.7 + rnd.random())
        edge.append(bm.verts.new(wall.at(u0 + (u1 - u0) * i / n, o, max(z, z_tear - 0.1))))
    for i in range(n): bm.faces.new((edge[i], edge[i + 1], top[i + 1], top[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = cine._mesh_obj(name, bm, mat, col, smooth=False); ob['lm'] = 'arch'
    if wall.side == 'back':
        for f in ob.data.polygons: f.flip() if f.normal.y > 0 else None
    else:
        for f in ob.data.polygons: f.flip() if f.normal.x < 0 else None
    return ob


def _curls(wall, name, u0, u1, z, mat, col, rnd):
    """A strip or two of paper curling away from the tear."""
    for k in range(rnd.randint(1, 2)):
        u = u0 + 0.1 + (u1 - u0 - 0.2) * rnd.random(); w = 0.06 + 0.07 * rnd.random(); L = 0.18 + 0.2 * rnd.random()
        bm = bmesh.new(); prev = None; n = 8
        for i in range(n + 1):
            t = i / n; ang = t * (1.4 + rnd.random() * 0.6)
            o = 0.016 + math.sin(ang) * L / 3; zz = z - math.sin(ang) * 0 - t * L * math.cos(ang * 0.6)
            row = [bm.verts.new(wall.at(u - w / 2, o, zz)), bm.verts.new(wall.at(u + w / 2, o, zz))]
            if prev: bm.faces.new((prev[0], prev[1], row[1], row[0]))
            prev = row
        ob = cine._mesh_obj(f'{name}{k}', bm, mat, col, smooth=True); ob['lm'] = 'furn'
        ob.modifiers.new('solid', 'SOLIDIFY').thickness = 0.0015


def _window(c, M, arch, furn):
    """A tall casement window in the left wall: lined reveals, a painted frame, glazing bars, the night beyond (drawn
    live on the web: rain on the glass), lace, two tattered drapes on a brass pole."""
    z0, z1 = WIN_Z; x0 = -W / 2; w = WIN_W; n = f'win{c:+.2f}'
    # the reveals: painted boards lining the opening
    for s in (-1, 1): box(f'{n}_reveal{s}', (T + 0.03, 0.03, z1 - z0), (x0 + (T + 0.03) / 2, c + s * (w / 2 - 0.015), (z0 + z1) / 2), M['boiserie'], bev=0.002, collection=arch, lm='arch')
    box(f'{n}_soffit', (T + 0.03, w, 0.03), (x0 + (T + 0.03) / 2, c, z1 - 0.015), M['boiserie'], bev=0.002, collection=arch, lm='arch')
    box(f'{n}_sill', (T + 0.09, w + 0.08, 0.04), (x0 + (T + 0.09) / 2, c, z0 - 0.02), M['boiserie'], bev=0.006, collection=arch, lm='arch')
    # the architrave round it, on the room side
    wl = Wall('left')
    for s in (-1, 1): wl.slab(f'{n}_arch{s}', c + s * (w / 2 + 0.06) - 0.06, c + s * (w / 2 + 0.06) + 0.06, z0 - 0.04, z1 + 0.12, 0.0, 0.025, M['boiserie'], arch, bev=0.008, lm='arch')
    wl.slab(f'{n}_arch_head', c - w / 2 - 0.12, c + w / 2 + 0.12, z1, z1 + 0.12, 0.0, 0.025, M['boiserie'], arch, bev=0.008, lm='arch')
    wl.slab(f'{n}_apron', c - w / 2 - 0.06, c + w / 2 + 0.06, 0.2, z0 - 0.04, 0.0, 0.016, M['boiserie'], arch, lm='arch')
    # the casement: frame, two leaves of three panes, a transom light
    xf = x0 + 0.06; fw = 0.06; tz = z1 - 0.48
    for s in (-1, 1): box(f'{n}_jamb{s}', (0.07, fw, z1 - z0), (xf, c + s * (w / 2 - fw / 2), (z0 + z1) / 2), M['window_paint'], bev=0.004, collection=furn, lm='furn')
    for k, z in enumerate((z0 + fw / 2, z1 - fw / 2, tz)): box(f'{n}_rail{k}', (0.07, w, fw if k < 2 else 0.07), (xf, c, z), M['window_paint'], bev=0.004, collection=furn, lm='furn')
    box(f'{n}_meet', (0.07, 0.06, tz - z0), (xf, c, (z0 + tz) / 2), M['window_paint'], bev=0.004, collection=furn, lm='furn')
    for s in (-1, 1):
        yc = c + s * w / 4
        for k in range(1, 3):
            zb = z0 + fw + (tz - z0 - fw) * k / 3
            box(f'{n}_bar{s}{k}', (0.03, w / 2 - 0.07, 0.022), (xf - 0.01, yc, zb), M['window_paint'], bev=0.003, collection=furn, lm='furn')
        box(f'{n}_handle{s}', (0.03, 0.012, 0.12), (xf + 0.05, c + s * 0.05, (z0 + tz) / 2), M['brass'], bev=0.003, collection=furn, lm='furn')
    box(f'{n}_transom_bar', (0.03, 0.022, z1 - tz), (xf - 0.01, c, (tz + z1) / 2), M['window_paint'], bev=0.003, collection=furn, lm='furn')
    # the glass: the night beyond, drawn live on the web (rain running down it); light passes it in the bake
    g = box(f'{n}_glass', (0.004, w - 0.04, z1 - z0 - 0.04), (xf - 0.02, c, (z0 + z1) / 2), M['glass_view'], bev=0, collection=furn, role='window')
    for attr in ('visible_shadow', 'visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter'): setattr(g, attr, False)
    # lace, hanging straight in front of the glass, faintly waved
    lace = cloth_panel(f'{n}_lace', w + 0.12, z1 - z0 - 0.02, folds=7, depth=0.012, mat=M['lace'], loc=(LEFT + 0.05, c, z1 - 0.02), rot=(0, 0, math.pi / 2),
                       res=(56, 18), seed=int(c * 10) + 50, collection=furn, role='lace')
    for attr in ('visible_shadow',): setattr(lace, attr, True)
    # the drapes: heavy damask, gathered to the sides, hems frayed; a brass pole with finials
    for s in (-1, 1):
        cloth_panel(f'{n}_drape{s}', 0.62, z1 + 0.06, folds=6, depth=0.05, mat=M['drape'], loc=(LEFT + 0.13, c + s * (w / 2 + 0.16), z1 + 0.08),
                    rot=(0, 0, math.pi / 2), gather=0.8, hem=0.07, seed=int(c * 10) + 60 + s, res=(40, 30), collection=furn, lm='furn')
    cyl(f'{n}_pole', 0.017, w + 1.0, (LEFT + 0.13, c, z1 + 0.1), M['brass'], rot=(math.pi / 2, 0, 0), seg=16, collection=furn, lm='furn')
    for s in (-1, 1):
        lathe(f'{n}_finial{s}', [(0, -0.03), (0.022, -0.025), (0.03, -0.005), (0.026, 0.012), (0.012, 0.03), (0, 0.04)], M['brass'],
              loc=(LEFT + 0.13, c + s * (w / 2 + 0.52), z1 + 0.1), seg=16, collection=furn, lm='furn').rotation_euler = (math.pi / 2 * s, 0, 0)


def _door(M, arch, furn):
    """Tall double doors to the next room: panelled leaves, a moulded architrave, brass knobs."""
    wb = Wall('back'); c, w, h = DOOR_X, DOOR_W, DOOR_H
    for s in (-1, 1):
        u0, u1 = (c - w / 2, c) if s < 0 else (c, c + w / 2)
        wb.slab(f'door_leaf{s}', u0 + 0.004, u1 - 0.004, 0.0, h, 0.0, 0.05, M['door'], furn, bev=0.004, lm='furn')
        for k, (z0, z1) in enumerate(((0.12, 0.62), (0.74, 1.62), (1.74, 2.38))):
            wb.slab(f'door_panel{s}{k}', u0 + 0.1, u1 - 0.1, z0, z1, 0.05, 0.014, M['door'], furn, bev=0.012, lm='furn')
        knob = Vector(wb.at(c + s * 0.07, 0.09, 1.02))
        cyl(f'door_knob{s}', 0.026, 0.03, knob, M['brass'], rot=(math.pi / 2, 0, 0), seg=20, bev=0.008, collection=furn, lm='furn')
        box(f'door_rose{s}', (0.05, 0.012, 0.16), wb.at(c + s * 0.07, 0.056, 1.0), M['brass'], bev=0.004, collection=furn, lm='furn')
    for s in (-1, 1): wb.slab(f'door_arch{s}', c + s * (w / 2 + 0.06) - 0.06, c + s * (w / 2 + 0.06) + 0.06, 0.0, h + 0.12, 0.0, 0.028, M['boiserie'], arch, bev=0.008, lm='arch')
    wb.slab('door_arch_head', c - w / 2 - 0.12, c + w / 2 + 0.12, h, h + 0.12, 0.0, 0.028, M['boiserie'], arch, bev=0.008, lm='arch')
    wb.run_h('door_cornice', c - w / 2 - 0.16, c + w / 2 + 0.16, h + 0.12, [(0, 0), (0.05, 0), (0.06, 0.02), (0.06, 0.05), (0, 0.06)], M['boiserie'], arch, lm='arch')
    wb.slab('door_overpanel', c - w / 2 - 0.12, c + w / 2 + 0.12, h + 0.18, H - 0.28, 0.0, 0.012, M['boiserie'], arch, lm='arch')


# ---------------------------------------------------------------- the fireplace
def fireplace(M, col, furn):
    """Dark veined marble on a chimney breast: plinths, carved jambs, a frieze with a cartouche, a moulded shelf;
    a cast-iron firebox, a grate with the charred ends of logs, a marble hearth; the mirror, clock and candlesticks."""
    yf = BACK - 0.34; obs = []
    add = lambda o: (obs.append(o), o)[1]
    box('fire_breast', (1.96, 0.02, 1.42), (0, BACK - 0.01, 0.71), M['marble'], bev=0, collection=col, lm='arch')
    for s in (-1, 1):
        x = s * 0.82
        add(box(f'fire_plinth{s}', (0.32, 0.36, 0.12), (x, yf + 0.18, 0.06), M['marble'], bev=0.008, collection=col, lm='furn'))
        add(box(f'fire_jamb{s}', (0.26, 0.32, 1.0), (x, yf + 0.16 + 0.01, 0.62), M['marble'], bev=0.01, collection=col, lm='furn'))
        add(box(f'fire_jamb_panel{s}', (0.16, 0.02, 0.76), (x, yf + 0.005, 0.6), M['marble'], bev=0.006, collection=col, lm='furn'))
        for k, (zz, hh, ww) in enumerate(((1.07, 0.03, 0.30), (1.1, 0.025, 0.28))):
            add(box(f'fire_capital{s}{k}', (ww, 0.35, hh), (x, yf + 0.165, zz), M['marble'], bev=0.006, collection=col, lm='furn'))
        for k in range(3):   # a corbel under each end of the shelf: three steps, deeper at the top
            add(box(f'fire_corbel{s}{k}', (0.16 - 0.03 * k, 0.05 + 0.025 * k, 0.04), (s * 0.9, yf - 0.02 - 0.012 * k, 1.24 + 0.04 * k), M['marble'], bev=0.008, collection=col, lm='furn'))
    add(box('fire_frieze', (1.9, 0.32, 0.24), (0, yf + 0.16, 1.24), M['marble'], bev=0.01, collection=col, lm='furn'))
    cart = add(cyl('fire_cartouche', 0.11, 0.03, (0, yf - 0.012, 1.24), M['marble'], rot=(math.pi / 2, 0, 0), seg=40, bev=0.01, collection=col, lm='furn'))
    cart.scale = (1.5, 1.0, 1.0)
    for s in (-1, 1): add(cyl(f'fire_scroll{s}', 0.03, 0.03, (s * 0.26, yf - 0.01, 1.24), M['marble'], rot=(math.pi / 2, 0, 0), seg=24, bev=0.008, collection=col, lm='furn'))
    add(box('fire_shelf', (2.1, 0.46, 0.06), (0, yf + 0.13, 1.39), M['marble'], bev=0.014, collection=col, lm='furn'))
    # the firebox: iron back and cheeks, soot, the grate with the cold ends of logs
    add(box('fire_back', (1.12, 0.02, 0.86), (0, BACK - 0.03, 0.55), M['iron'], bev=0, collection=col, lm='furn'))
    for s in (-1, 1):
        ch = add(box(f'fire_cheek{s}', (0.02, 0.32, 0.86), (s * 0.55, yf + 0.17, 0.55), M['iron'], bev=0, collection=col, lm='furn'))
        ch.rotation_euler.z = -s * 0.25
    add(box('fire_top', (1.12, 0.32, 0.02), (0, yf + 0.17, 0.98), M['soot'], bev=0, collection=col, lm='furn'))
    add(box('fire_floor', (1.12, 0.33, 0.02), (0, yf + 0.17, 0.12), M['soot'], bev=0, collection=col, lm='furn'))
    for k in range(7): add(box(f'fire_grate_bar{k}', (0.012, 0.24, 0.012), (-0.3 + 0.1 * k, yf + 0.16, 0.24), M['iron'], bev=0.002, collection=col, lm='furn'))
    for s in (-1, 1):
        add(box(f'fire_grate_front{s}', (0.66, 0.012, 0.012), (0, yf + 0.04 + (0.24 if s > 0 else 0), 0.3 + (0.06 if s < 0 else 0)), M['iron'], bev=0.002, collection=col, lm='furn'))
        add(cyl(f'fire_dog{s}', 0.016, 0.26, (s * 0.38, yf + 0.06, 0.25), M['iron'], seg=12, collection=col, lm='furn'))
        add(lathe(f'fire_dog_knob{s}', [(0, 0), (0.03, 0.01), (0.034, 0.04), (0.02, 0.06), (0, 0.065)], M['brass'], loc=(s * 0.38, yf + 0.06, 0.38), seg=16, collection=col, lm='furn'))
    for k, (x, a) in enumerate(((-0.12, 0.25), (0.08, -0.2), (-0.02, 0.05))):
        lg = add(cyl(f'fire_log{k}', 0.045 - 0.008 * k, 0.5, (x, yf + 0.17, 0.3 + 0.07 * (k == 2)), M['char'], rot=(0, math.pi / 2, a), seg=14, collection=col, lm='furn'))
    add(box('fire_hearth', (2.0, 0.5, 0.035), (0, yf - 0.25 + 0.02, 0.0175), M['marble'], bev=0.006, collection=col, lm='furn'))
    # on the mantel and above it
    root, ms = cine.import_gltf(PH('mantel_clock_01'), loc=(0, yf + 0.12, 1.42), collection=furn, lm='furn'); obs += ms
    root, ms = cine.import_gltf(PH('ornate_mirror_01'), loc=(0, BACK - 0.04, 2.08), collection=furn, lm='furn'); obs += ms
    return obs


# ---------------------------------------------------------------- sconces, chairs, the table
def sconce(name, wall, u, z, M, col):
    """Twin brass arms from an oval plate, candle sleeves, small pleated shades; returns the two bulb positions."""
    wl = Wall(wall); n = name; parts = []
    base = wl.at(u, 0.0, z); out = wl.out; along = Vector((1, 0, 0)) if wall == 'back' else Vector((0, 1, 0))
    parts.append(box(f'{n}_plate', (0.1, 0.016, 0.16) if wall == 'back' else (0.016, 0.1, 0.16), base + out * 0.008, M['brass'], bev=0.03, seg=4, collection=col, lm='furn'))
    bulbs = []
    for s in (-1, 1):
        # an arm: out from the plate, then up to the cup
        a0 = base + out * 0.02; a1 = base + out * 0.12 + along * s * 0.15 + Vector((0, 0, -0.04)); a2 = a1 + Vector((0, 0, 0.08))
        for k, (p, q) in enumerate(((a0, a1), (a1, a2))):
            d = q - p; L = d.length; m = (p + q) / 2
            arm = cyl(f'{n}_arm{s}{k}', 0.007, L, m, M['brass'], seg=10, collection=col, lm='furn')
            arm.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
            parts.append(arm)
        parts.append(lathe(f'{n}_cup{s}', [(0.004, 0), (0.026, 0.005), (0.03, 0.016), (0.018, 0.02), (0, 0.02)], M['brass'], loc=a2, seg=20, collection=col, lm='furn'))
        parts.append(cyl(f'{n}_candle{s}', 0.011, 0.07, a2 + Vector((0, 0, 0.055)), M['candle'], seg=14, collection=col, lm='furn'))
        sh = cyl(f'{n}_shade{s}', 0.062, 0.085, a2 + Vector((0, 0, 0.115)), M['shade'], r2=0.034, seg=24, bev=0.002, collection=col, lm='furn')
        sh.data.polygons.foreach_set('use_smooth', [True] * len(sh.data.polygons))
        parts.append(sh)
        bulbs.append(a2 + Vector((0, 0, 0.1)))
    parts.append(cyl(f'{n}_stem', 0.009, 0.1, base + out * 0.03 + Vector((0, 0, -0.06)), M['brass'], seg=10, collection=col, lm='furn'))
    return parts, bulbs


def slab_profile(name, pts, axis, t, mats, col, inward=None, bev=0.025, **props):
    """A shaped panel: the 2D outline `pts` (smooth points) in the plane across `axis` ('x' or 'y'), `t` thick,
    centred on that plane; edges rounded. mats = [inner, outer]: faces whose normal points along `inward` get the
    first (tufted leather on the side a sitter sees), the rest the second."""
    bm = bmesh.new()
    def co(p, d): return (d, p[0], p[1]) if axis == 'x' else (p[0], d, p[1])
    a = [bm.verts.new(co(p, -t / 2)) for p in pts]; b = [bm.verts.new(co(p, t / 2)) for p in pts]
    n = len(pts)
    bm.faces.new(a); bm.faces.new(list(reversed(b)))
    for i in range(n): bm.faces.new((a[i], b[i], b[(i + 1) % n], a[(i + 1) % n]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = cine._mesh_obj(name, bm, mats[0], col, smooth=False)
    ob.data.materials.append(mats[1])
    inward = Vector(inward) if inward is not None else None
    for f in ob.data.polygons: f.material_index = 0 if inward is not None and f.normal.dot(inward) > 0.7 else 1
    cine.bevel(ob, bev, 4, 40)
    for k, v in props.items(): ob[k] = v
    return ob


def _curve(ctrl, n=10):
    """A smooth outline through control points (Catmull-Rom), closed."""
    pts = []; m = len(ctrl)
    for i in range(m):
        p0, p1, p2, p3 = (Vector(ctrl[(i + k) % m]) for k in (-1, 0, 1, 2))
        for s in range(n):
            t = s / n; t2, t3 = t * t, t * t * t
            pts.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    return [(p.x, p.y) for p in pts]


def chair(name, x, y, facing, M, col):
    """A tufted wingback in oxblood leather, after the two in the film: a camel-backed outer shell, wings that sweep
    forward from the top of the back and curl down into rolled arms, a tufted inner back and wings, a seat cushion,
    a skirt and short turned legs. Built facing -y, then turned to `facing`."""
    parts = []; tuft, plain = M['leather_tuft'], M['leather']
    def add(o): parts.append(o); return o
    for sx in (-1, 1):
        for sy in (-1, 1):
            add(lathe(f'{name}_leg{sx}{sy}', [(0.016, 0), (0.022, 0.012), (0.026, 0.05), (0.02, 0.085), (0.027, 0.1), (0.0, 0.1)], M['chair_wood'], loc=(sx * 0.35, sy * 0.35, 0), seg=16, collection=col, lm='furn'))
    add(box(f'{name}_skirt', (0.84, 0.82, 0.25), (0, -0.01, 0.225), plain, bev=0.035, seg=4, collection=col, lm='furn'))
    add(box(f'{name}_seat', (0.6, 0.6, 0.13), (0, -0.07, 0.405), plain, bev=0.055, seg=5, collection=col, lm='furn'))
    # the outer back: a camel-backed shell, plain leather outside, tufted where it shows inside above the inner back
    shell = _curve([(-0.43, 0.1), (0.43, 0.1), (0.43, 1.06), (0.3, 1.17), (0.0, 1.22), (-0.3, 1.17), (-0.43, 1.06)], 8)
    add(slab_profile(f'{name}_shell', shell, 'y', 0.07, [tuft, plain], col, inward=(0, -1, 0), bev=0.03, lm='furn')).location = (0, 0.39, 0)
    # the inner back: a deep tufted cushion, leaning back
    ib = add(slab_profile(f'{name}_innerback', _curve([(-0.31, 0.0), (0.31, 0.0), (0.31, 0.74), (0.0, 0.8), (-0.31, 0.74)], 6), 'y', 0.12, [tuft, plain], col, inward=(0, -1, 0), bev=0.04, lm='furn'))
    ib.location = (0, 0.3, 0.43); ib.rotation_euler.x = -0.16
    for sx in (-1, 1):
        # arms: a tufted inner face, a plain outside, a roll on top with a scrolled front
        add(slab_profile(f'{name}_arm{sx}', [(-0.41, 0.33), (0.38, 0.33), (0.38, 0.58), (-0.41, 0.58)], 'x', 0.12, [tuft, plain], col, inward=(-sx, 0, 0), bev=0.025, lm='furn')).location = (sx * 0.36, 0, 0)
        add(cyl(f'{name}_armroll{sx}', 0.066, 0.8, (sx * 0.372, -0.01, 0.585), plain, rot=(math.pi / 2, 0, 0), seg=28, bev=0.018, collection=col, lm='furn'))
        add(cyl(f'{name}_armface{sx}', 0.074, 0.028, (sx * 0.372, -0.41, 0.565), plain, rot=(math.pi / 2, 0, 0), seg=28, bev=0.012, collection=col, lm='furn'))
        # wings: from the top of the back, sweeping forward and curling down to the arm
        wing = _curve([(0.37, 0.6), (0.37, 1.12), (0.22, 1.17), (0.04, 1.13), (-0.09, 1.0), (-0.13, 0.84), (-0.08, 0.68), (0.05, 0.62)], 8)
        wg = add(slab_profile(f'{name}_wing{sx}', wing, 'x', 0.085, [tuft, plain], col, inward=(-sx, 0, 0), bev=0.03, lm='furn'))
        wg.location = (sx * 0.38, 0, 0); wg.rotation_euler.y = sx * 0.06
    lift = SEAT_TOP - 0.47                            # built for a 47 cm seat: taller legs raise the rest
    for o in parts:
        if '_leg' in o.name: o.scale.z = (0.1 + lift) / 0.1
        else: o.location.z += lift
    Mf = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(facing, 4, 'Z')
    for o in parts: place(o, Mf)
    return parts


def table(M, col):
    """A small pedestal table: a round top on a turned column and three splayed feet; the glass of water on it."""
    x, y = TABLE; parts = []
    parts.append(cyl('table_top', 0.235, 0.024, (x, y, 0.668), M['mahogany'], seg=48, bev=0.008, collection=col, lm='furn'))
    parts.append(lathe('table_column', [(0.06, 0.12), (0.045, 0.15), (0.03, 0.2), (0.04, 0.3), (0.028, 0.42), (0.022, 0.5), (0.034, 0.58), (0.05, 0.63), (0.06, 0.656), (0.0, 0.656)],
                       M['mahogany'], loc=(x, y, 0), seg=24, collection=col, lm='furn'))
    for k in range(3):
        a = k * 2 * math.pi / 3 + 0.3
        ft = box(f'table_foot{k}', (0.24, 0.035, 0.05), (x + math.cos(a) * 0.13, y + math.sin(a) * 0.13, 0.07), M['mahogany'], bev=0.012, collection=col, lm='furn')
        ft.rotation_euler = (0, 0.42, a); parts.append(ft)
    # the glass of water (the web draws its own glass and water: see the roles)
    parts.append(lathe('drinking_glass', [(0.0, 0.68), (0.03, 0.68), (0.032, 0.685), (0.036, 0.79), (0.033, 0.79), (0.029, 0.69), (0.0, 0.69)], M['glass'], loc=(x + 0.05, y - 0.04, 0), seg=32, collection=col, role='glass'))
    parts.append(cyl('water', 0.03, 0.075, (x + 0.05, y - 0.04, 0.69 + 0.0375), M['water'], seg=32, bev=0, collection=col, role='water'))
    return parts


def dust_sheeted_settee(M, col, x=3.25, y=-2.55):
    """A settee left under a dust sheet: the sheet slumps over the arms and back and falls to the floor."""
    parts = []
    for name, size, loc, bev in (('body', (1.9, 0.82, 0.42), (0, 0, 0.21), 0.09), ('back', (1.9, 0.24, 0.5), (0, 0.29, 0.62), 0.1),
                                 ('arm0', (0.24, 0.82, 0.3), (-0.83, 0, 0.55), 0.1), ('arm1', (0.24, 0.82, 0.3), (0.83, 0, 0.55), 0.1)):
        parts.append(box(f'settee_{name}', size, loc, M['sheet'], bev=bev, seg=5, collection=col, lm='furn'))
    hang = cloth_panel('settee_sheet_front', 2.0, 0.34, folds=9, depth=0.025, mat=M['sheet'], loc=(0, -0.43, 0.34), hem=0.0, seed=71, res=(48, 8), collection=col, lm='furn')
    parts.append(hang)
    Mf = Matrix.Translation((x, y, 0)) @ Matrix.Rotation(math.radians(8), 4, 'Z')
    for o in parts: place(o, Mf)
    return parts


def rug(M, col):
    x, y = TABLE
    r = box('rug', (3.0, 2.0, 0.008), (x, y, 0.004), M['rug'], bev=0.002, collection=col, lm='arch')
    return [r]


def debris(M, col, seed=5):
    """Flakes of plaster and paper fallen along the walls, more of them under the torn panels and the windows."""
    rnd = random.Random(seed); bm = bmesh.new()
    def flake(cx, cy):
        s = 0.015 + rnd.random() ** 2 * 0.07; t = 0.003 + rnd.random() * 0.006
        a = rnd.random() * math.pi; pts = []
        for i in range(5):
            ang = a + i * 2 * math.pi / 5 + rnd.random() * 0.5; rr = s * (0.5 + 0.5 * rnd.random())
            pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
        bot = [bm.verts.new((px, py, 0.0005)) for px, py in pts]; top = [bm.verts.new((px, py, t)) for px, py in pts]
        bm.faces.new(top)
        for i in range(5): bm.faces.new((bot[i], bot[(i + 1) % 5], top[(i + 1) % 5], top[i]))
    for k in range(260):
        if rnd.random() < 0.55:   # along the back wall
            cx, cy = rnd.uniform(-4.5, 4.5), BACK - 0.05 - rnd.random() ** 2 * 0.6
            if abs(cx) < 1.05 or abs(cx - DOOR_X) < 0.75: continue
        else:                     # along the left wall
            cx, cy = LEFT + 0.05 + rnd.random() ** 2 * 0.7, rnd.uniform(-3.5, 3.5)
        flake(cx, cy)
    for k in range(40):           # a few out in the room
        flake(rnd.uniform(-3.5, 3.8), rnd.uniform(-2.8, 3.2))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = cine._mesh_obj('debris', bm, M['debris'], col, smooth=False); ob['lm'] = 'furn'
    return [ob]


# ---------------------------------------------------------------- light
WARM = (1.0, 0.84, 0.55)          # tungsten bulbs, nudged toward the film's green
NIGHT = (0.52, 0.74, 0.70)        # the street at night through rain and lace: green-grey
FLASH = (0.80, 0.88, 1.0)         # lightning


def lights(bulbs):
    """The room's own light: the sconce bulbs and the night at the windows. Returns (lights, lightning lights)."""
    import bpy
    out = []
    for k, p in enumerate(list(bulbs) + PHANTOM_BULBS):
        ld = bpy.data.lights.new(f'bulb{k}', 'POINT'); ld.energy = 30.0 if k < len(bulbs) else 15.0; ld.shadow_soft_size = 0.02; ld.color = WARM
        ob = cine.link(bpy.data.objects.new(f'bulb{k}', ld)); ob.location = p; out.append(ob)
    flash = []
    for c in WINDOWS:
        # (height, width along the wall): an area light emits along its local -z; turned -90 degrees about y it faces
        # +x, into the room, its local x vertical
        for name, power, (hgt, wid), x, colour, group in (('night', 200.0, (2.1, 1.3), -W / 2 - 0.15, NIGHT, out), ('lightning', 2600.0, (3.0, 2.6), -W / 2 - 1.2, FLASH, flash)):
            ld = bpy.data.lights.new(f'{name}{c}', 'AREA'); ld.shape = 'RECTANGLE'; ld.size, ld.size_y = hgt, wid; ld.energy = power; ld.color = colour
            ob = cine.link(bpy.data.objects.new(f'{name}{c}', ld)); ob.location = (x, c, (WIN_Z[0] + WIN_Z[1]) / 2 + (0.6 if name == 'lightning' else 0))
            ob.rotation_euler = (0, -math.pi / 2 + (0.25 if name == 'lightning' else 0), 0)   # lightning a little from above
            group.append(ob)
    return out, flash
