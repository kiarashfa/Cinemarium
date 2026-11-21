# Mr. Robot · the Fun Society arcade on Coney Island, the night of the hack: a closed arcade under a dark drop ceiling.
# Along the back, a row of skee-ball lanes under a long canopy, their backglasses lit; on the left the concession
# counter, its front a run of glowing red and green panels, glass cases of prizes over it and the CONCESSION light box
# on top; the popcorn machine; the hackers' tables (two monitors on the long one, a laptop on the other); on the right
# the red 00 machine, slot machines, the ticket centre under its TICKETS neon, a change machine; GAMES in three neons
# over the back corner, washing it purple; an air-hockey table in front. Built at its true size.
import math, os
import bpy, bmesh
from mathutils import Vector, Matrix
import cine
from cine import box, cyl, material, lathe, rounded_slab
from rooms.seinfeld import tube, circle

W, D = 9.6, 7.6
T = 0.14
LEFT, BACK, RIGHT, FRONT = -W / 2 + T, D / 2 - T, W / 2 - T, -D / 2 + T
RH = 3.0                                   # the module's top (the drop ceiling is a phantom just above it)
KH = 0.22
TEX = os.path.join(cine.OUT, 'textures', 'mr-robot')
tx = lambda n: os.path.join(TEX, n)
PH = os.path.join(cine.CACHE, 'polyhaven')

# ---- the plan (true metres)
LANES = 8
LANE_W = 0.74
LANE_X0 = -3.92                            # the row's left edge
LANE_Y0, LANE_Y1 = 0.45, BACK - 0.02       # a lane from the player's end to the target hood
CANOPY = (LANE_X0 - 0.04, LANE_X0 + LANES * LANE_W + 0.06, 2.5, BACK, 2.62)   # x0, x1, y0, y1, its underside
COUNTER = (LEFT, -3.98, -2.62, 0.22)       # x0, x1 (its front), y0, y1
COUNTER_H = 1.0
POPCORN = Vector((-2.05, -2.72))           # the popcorn machine's stand (it faces the room's front)
TABLE = (-3.38, -2.62, -1.95, -0.05)       # the long table: x0, x1, y0, y1
TABLE_H = 0.74
TABLE2 = (-3.88, -2.58, -0.42, 0.28)       # the laptop table, by the first lanes
CHAIR = (Vector((-2.22, -0.92)), Vector((-1.0, 0.0)))   # Tyrell's chair: the seat's middle on the floor, its facing
SEAT_H = 0.47
SCREENS = [Vector((-3.12, -1.28)), Vector((-3.12, -0.66))]   # the two monitors on the long table (they face +x)
M00 = Vector((4.18, 0.35))                 # the 00 machine, its back to the right cut, facing the room (-x)
SLOTS = [Vector((4.24, 1.16)), Vector((4.24, 1.86))]
TICKETS = Vector((4.12, -1.25))            # the ticket centre
CHANGE = Vector((4.3, -2.62))
HOCKEY = Vector((1.75, -2.55))
GAMES = Vector((3.35, BACK - 0.01, 2.32))  # the neon board's centre on the back wall
CORNER = [Vector((2.55, BACK - 0.45)), Vector((3.35, BACK - 0.45)), Vector((4.15, BACK - 0.45))]   # under GAMES: a claw, two cabinets


# ---------------------------------------------------------------- materials
def _lit(name, image, strength, rough=0.5, colour_k=1.0):
    """A face printed and lit from within (a sign, a backglass, a screen): its image is both colour and emission."""
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); nt = m.node_tree; p = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = cine.image(image, True)
    uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = 'UVMap'; nt.links.new(uv.outputs['UV'], t.inputs['Vector'])
    nt.links.new(t.outputs['Color'], p.inputs['Base Color']); nt.links.new(t.outputs['Color'], p.inputs['Emission Color'])
    p.inputs['Emission Strength'].default_value = strength; p.inputs['Roughness'].default_value = rough
    return m


def _printed(name, image, rough=0.45, coat=0.0):
    """A printed face, not lit (a target board): its image as colour on 0..1 UVs."""
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); nt = m.node_tree; p = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = cine.image(image, True)
    uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = 'UVMap'; nt.links.new(uv.outputs['UV'], t.inputs['Vector'])
    nt.links.new(t.outputs['Color'], p.inputs['Base Color']); p.inputs['Roughness'].default_value = rough
    if coat: p.inputs['Coat Weight'].default_value = coat
    return m


def mats():
    M = {}
    M['floor'] = material('mr_floor', rough=0.7, maps={'color': tx('floor_color.jpg'), 'normal': tx('floor_normal.jpg'), 'rough': tx('floor_rough.jpg')}, scale=2.4, normal_strength=0.5)
    M['wall'] = material('mr_wall', rough=0.85, maps={'color': tx('wall_color.jpg'), 'normal': tx('wall_normal.jpg')}, scale=2.0, normal_strength=0.4)
    M['shutter'] = material('mr_shutter', rough=0.55, metal=0.4, maps={'color': tx('shutter_color.jpg'), 'normal': tx('shutter_normal.jpg')}, scale=1.2)
    M['coney'] = _printed('mr_coney', tx('coney_color.jpg'), rough=0.6)
    M['kerb'] = material('mr_kerb', (0.05, 0.045, 0.05), rough=0.8)
    M['section'] = material('section', (0.03, 0.028, 0.03), rough=0.92)
    M['ph_ceiling'] = material('mr_ph_ceiling', (0.06, 0.06, 0.065), rough=0.9)
    M['ph_wall'] = material('mr_ph_wall', (0.05, 0.04, 0.05), rough=0.9)
    M['black'] = material('mr_black', (0.012, 0.012, 0.014), rough=0.5)
    M['satin'] = material('mr_satin_black', (0.02, 0.02, 0.022), rough=0.3, coat=0.4)
    M['chrome'] = material('mr_chrome', (0.8, 0.8, 0.82), rough=0.12, metal=1.0)
    M['alu'] = material('mr_alu', (0.62, 0.62, 0.64), rough=0.35, metal=1.0)
    M['steel'] = material('mr_steel', (0.55, 0.55, 0.56), rough=0.3, metal=1.0)
    M['lane'] = material('mr_lane_wood', rough=0.35, maps={'color': tx('lane_color.jpg')}, scale=1.2, coat=0.5, coat_rough=0.1)
    for k, c in (('red', (0.34, 0.02, 0.025)), ('blue', (0.02, 0.05, 0.26)), ('yellow', (0.62, 0.4, 0.03)), ('green', (0.02, 0.2, 0.08)), ('cream', (0.66, 0.62, 0.54))):
        M[k] = material(f'mr_paint_{k}', c, rough=0.4, coat=0.3)
    M['net'] = material('mr_net', (0.02, 0.02, 0.022), rough=0.6)
    M['target'] = _printed('mr_target', tx('lane_target.jpg'), rough=0.35, coat=0.3)
    M['backglass'] = _lit('mr_backglass', tx('lane_backglass.jpg'), 1.3)
    M['tube'] = material('mr_tube', (0.9, 0.92, 0.95), rough=0.3, emission=(0.86, 0.92, 1.0), emission_strength=5.0)
    M['canopy_fascia'] = material('mr_canopy_fascia', (0.8, 0.6, 0.06), rough=0.45, emission=(0.9, 0.62, 0.08), emission_strength=0.35)
    M['counter_top'] = material('mr_counter_top', (0.74, 0.73, 0.7), rough=0.3, coat=0.4)
    M['panel_red'] = material('mr_panel_red', (0.3, 0.02, 0.02), rough=0.4, emission=(1.0, 0.04, 0.03), emission_strength=2.6)
    M['panel_green'] = material('mr_panel_green', (0.02, 0.28, 0.09), rough=0.4, emission=(0.03, 1.0, 0.28), emission_strength=2.0)
    M['prizes'] = _lit('mr_prizes', tx('prizes.jpg'), 0.35)
    M['amber'] = material('mr_amber_strip', (1.0, 0.7, 0.35), rough=0.3, emission=(1.0, 0.66, 0.3), emission_strength=12.0)
    M['concession'] = _lit('mr_sign_concession', tx('sign_concession.jpg'), 3.0)
    M['games'] = _lit('mr_sign_games', tx('sign_games.jpg'), 6.0)
    M['tickets'] = _lit('mr_sign_tickets', tx('sign_tickets.jpg'), 4.0)
    M['ticketcenter'] = _lit('mr_sign_ticketcenter', tx('sign_ticketcenter.jpg'), 2.2)
    M['nosmoking'] = _printed('mr_sign_nosmoking', tx('sign_nosmoking.jpg'))
    M['m00'] = _lit('mr_machine_00', tx('machine_00.jpg'), 1.6)
    M['m00_body'] = material('mr_m00_body', (0.42, 0.04, 0.05), rough=0.35, coat=0.5)
    for k in range(3): M[f'slot{k}'] = _lit(f'mr_slot_{k}', tx(f'slot_{k}.jpg'), 1.4)
    for k in range(4): M[f'cab{k}'] = _lit(f'mr_cabinet_{k}', tx(f'cabinet_{k}.jpg'), 1.2)
    M['change'] = _lit('mr_change', tx('change.jpg'), 0.6)
    M['desktop'] = _lit('mr_screen_desktop', tx('screen_desktop.jpg'), 2.2, rough=0.2)
    M['terminal'] = _lit('mr_screen_terminal', tx('screen_terminal.jpg'), 2.2, rough=0.2)
    M['plastic'] = material('mr_plastic', (0.025, 0.025, 0.028), rough=0.45)
    M['table'] = material('mr_table', rough=0.55, maps={'color': tx('table_color.jpg')}, scale=1.0)
    M['chair'] = material('mr_chair', (0.36, 0.03, 0.03), rough=0.65, sheen=0.3, sheen_tint=(0.3, 0.1, 0.1))
    M['popcorn'] = material('mr_popcorn', (0.95, 0.82, 0.45), rough=0.8)
    M['pop_lamp'] = material('mr_popcorn_lamp', (1.0, 0.85, 0.6), rough=0.3, emission=(1.0, 0.8, 0.5), emission_strength=20.0)
    M['felt'] = material('mr_hockey_top', (0.82, 0.84, 0.86), rough=0.25, coat=0.6)
    return M


# ---------------------------------------------------------------- shared shapes
def panel(name, w, h, c, facing, mat, col, lm='furn', flip_u=False):
    """A flat face `w` by `h` centred at c, facing the unit vector `facing` (horizontal, or up), with 0..1 UVs (u across,
    v up): a sign, a screen, a printed board."""
    f = Vector(facing).normalized()
    up = Vector((0, 0, 1)) if abs(f.z) < 0.9 else Vector((0, 1, 0))
    u = up.cross(f).normalized(); v = f.cross(u).normalized()
    if flip_u: u = -u
    c = Vector(c); bm = bmesh.new()
    vs = [bm.verts.new(c + u * (sx * w / 2) + v * (sy * h / 2)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    fc = bm.faces.new(vs); uvl = bm.loops.layers.uv.new('UVMap')
    for l, (a, b) in zip(fc.loops, ((0, 0), (1, 0), (1, 1), (0, 1))): l[uvl].uv = (a, b)
    ob = cine._mesh_obj(name, bm, mat, col, smooth=False)
    if lm: ob['lm'] = lm
    return ob


def framed(name, M, col, F, parts):
    """Boxes given in a local frame (x across, y back, z up) placed by the matrix F."""
    out = []
    for n, size, loc, mat in parts:
        out.append(box(f'{name}_{n}', size, loc, mat, bev=0.004, collection=col, lm='furn'))
    bpy.context.view_layer.update()
    for o in out: cine.place(o, F)
    return out


def frame_at(at, facing):
    """A local frame: origin `at` on the floor, local -y along `facing` (a machine's front)."""
    a = math.atan2(facing[1], facing[0]) - math.atan2(-1.0, 0.0)
    return Matrix.Translation((at[0], at[1], 0)) @ Matrix.Rotation(a, 4, 'Z')


# ---------------------------------------------------------------- the shell
def shell(M, arch, phantom):
    """The floor; the back and left walls (painted block), the corrugated panel with CONEY in the back corner; the
    kerbs; the phantoms: the drop ceiling, the cut-away front and right walls."""
    box('subfloor', (W, D, 0.02), (0, 0, -0.035), M['kerb'], bev=0, collection=arch, lm='arch')
    fl = box('floor_room', (RIGHT - LEFT, BACK - FRONT, 0.03), ((LEFT + RIGHT) / 2, (FRONT + BACK) / 2, -0.015), M['floor'], bev=0, collection=arch, lm='arch')
    cine.world_uv(fl, 1.0)
    w = box('back_wall', (W, T, RH), (0, D / 2 - T / 2, RH / 2), M['wall'], bev=0, collection=arch, lm='arch'); cine.world_uv(w, 1.0)
    w = box('left_wall', (T, D - T, RH), (-W / 2 + T / 2, -T / 2, RH / 2), M['wall'], bev=0, collection=arch, lm='arch'); cine.world_uv(w, 1.0)
    for nm, size, loc in (('kerb_front', (W - T, T, KH), (T / 2, -D / 2 + T / 2, KH / 2)), ('kerb_right', (T, D - 2 * T, KH), (W / 2 - T / 2, 0, KH / 2))):
        k = box(nm, size, loc, M['wall'], bev=0, collection=arch, lm='arch'); cine.world_uv(k, 1.0)
    # the corrugated panel over the back corner (behind the GAMES neon): painted CONEY, old
    x0 = CANOPY[1] + 0.05
    panel('coney_wall', RIGHT - x0, 2.2, ((x0 + RIGHT) / 2, BACK - 0.012, 1.85), (0, -1, 0), M['coney'], arch, lm='arch')
    ph = lambda name, size, loc, mat: box(name, size, loc, mat, bev=0, collection=phantom, bake_only=1)
    ph('ph_ceiling', (W, D, 0.2), (0, 0, RH + 0.1), M['ph_ceiling'])
    ph('ph_front', (W, 0.2, RH - KH), (0, FRONT - 0.3, KH + (RH - KH) / 2), M['ph_wall'])
    ph('ph_right', (0.2, D, RH - KH), (RIGHT + 0.25, 0, KH + (RH - KH) / 2), M['ph_wall'])


# ---------------------------------------------------------------- the skee-ball lanes
def lane(k, M, col):
    """One skee-ball lane (Thunder Ball), built along +y from the player's end: the cabinet with the ball tray, the
    sloping alley between painted sides and a black net, the hump, the target hood tilted up with its rings, the side
    cheeks, the backglass box lit on top."""
    x = LANE_X0 + LANE_W * (k + 0.5); y0, y1 = LANE_Y0, LANE_Y1; L = y1 - y0
    side = (M['red'], M['blue'], M['yellow'], M['green'])[k % 4]
    out = []; B = lambda n, size, loc, mat, **kw: out.append(box(f'lane{k}_{n}', size, loc, mat, collection=col, lm='furn', **kw)) or out[-1]
    w = LANE_W - 0.03; hw = w / 2
    # the player's cabinet: 0.55 deep, 0.78 high, the tray on top, a painted front with a cream stripe
    B('cab', (w, 0.55, 0.74), (x, y0 + 0.275, 0.37), M['satin'])
    B('front', (w - 0.04, 0.02, 0.5), (x, y0 - 0.005, 0.42), side)
    B('stripe', (w - 0.04, 0.022, 0.06), (x, y0 - 0.006, 0.56), M['cream'])
    B('tray', (w - 0.12, 0.42, 0.04), (x, y0 + 0.3, 0.76), M['black'])
    # the alley: from the cabinet's back to the hood, rising a little; the sides painted, the rails chrome
    a0, a1 = y0 + 0.55, y1 - 0.95; z0, z1 = 0.72, 0.86
    n = (a1 - a0); ang = math.atan2(z1 - z0, n)
    al = box(f'lane{k}_alley', (w - 0.1, n + 0.02, 0.03), (x, (a0 + a1) / 2, (z0 + z1) / 2), M['lane'], rot=(ang, 0, 0), collection=col, lm='furn')
    cine.world_uv(al, 1.0); out.append(al)
    for s in (-1, 1):
        B(f'side{s:+d}', (0.05, n + 0.55, 0.36), (x + s * (hw - 0.025), (a0 + a1) / 2 - 0.27, 0.68), side)
        out.append(tube(f'lane{k}_rail{s:+d}', [(x + s * (hw - 0.025), a0 - 0.5, 0.88), (x + s * (hw - 0.025), a1, 0.88 + (z1 - z0))], 0.012, M['chrome'], col, seg=8, lm='furn'))
        B(f'netpost{s:+d}', (0.03, 0.03, 0.9), (x + s * (hw - 0.03), a1 - 0.05, 1.3), M['black'])
    B('hump', (w - 0.1, 0.12, 0.06), (x, a1 - 0.18, z1 + 0.02), M['lane'], rot=(0.5, 0, 0))
    # the net over the back half of the alley (a dark mesh panel each side and over the top)
    # the target hood: a board tilted up toward the back, the rings printed on it, cheeks either side
    h0 = Vector((x, a1, z1)); h1 = Vector((x, y1 - 0.06, 1.72)); hl = (h1 - h0).length; t_ang = math.atan2(h1.z - h0.z, h1.y - h0.y)
    B('hood', (w - 0.06, hl, 0.04), (x, (h0.y + h1.y) / 2, (h0.z + h1.z) / 2 - 0.03), M['satin'], rot=(t_ang, 0, 0))
    nrm = Vector((0, -math.sin(t_ang), math.cos(t_ang)))
    tg = panel(f'lane{k}_target', w - 0.12, hl - 0.06, (h0 + h1) / 2 + nrm * 0.0, nrm, M['target'], col)
    out.append(tg)
    for s in (-1, 1):
        cheek = [(a1 - 0.05, 0.7), (y1 - 0.02, 0.7), (y1 - 0.02, 2.0), (a1 - 0.05, 1.2)]
        ob = cine.slab_profile(f'lane{k}_cheek{s:+d}', cheek, 'x', 0.04, [side, side], col, bev=0.004, lm='furn'); ob.location.x = x + s * (hw - 0.02); out.append(ob)
    # the backglass box on top, lit
    B('glassbox', (w, 0.34, 0.62), (x, y1 - 0.17, 2.32), M['satin'])
    out.append(panel(f'lane{k}_backglass', w - 0.05, 0.5, (x, y1 - 0.345, 2.32), (0, -1, 0), M['backglass'], col))
    B('marquee_trim', (w, 0.36, 0.03), (x, y1 - 0.18, 2.64), M['chrome'])
    return out


def lanes(M, col):
    out = []
    for k in range(LANES): out += lane(k, M, col)
    # the canopy over the row: a dark box hung from the ceiling, its yellow fascia, the tubes under it
    x0, x1, y0, y1, zu = CANOPY
    out.append(box('canopy', (x1 - x0, y1 - y0, RH - zu), ((x0 + x1) / 2, (y0 + y1) / 2, (zu + RH) / 2), M['black'], bev=0.006, collection=col, lm='furn'))
    out.append(box('canopy_fascia', (x1 - x0 + 0.02, 0.03, 0.16), ((x0 + x1) / 2, y0 - 0.016, zu + 0.08), M['canopy_fascia'], bev=0.004, collection=col, lm='furn'))
    for j in range(5):
        xa = x0 + 0.15 + j * (x1 - x0 - 0.3) / 5; xb = xa + (x1 - x0 - 0.3) / 5 - 0.1
        out.append(cyl(f'canopy_tube{j}', 0.014, xb - xa, ((xa + xb) / 2, y0 + 0.12, zu - 0.02), M['tube'], rot=(0, math.pi / 2, 0), seg=10, collection=col, lm='furn'))
    return out


# ---------------------------------------------------------------- the concession counter and its cases
def concession(M, col):
    x0, x1, y0, y1 = COUNTER; out = []
    B = lambda n, size, loc, mat, **kw: out.append(box(f'conc_{n}', size, loc, mat, collection=col, lm='furn', **kw)) or out[-1]
    B('body', (x1 - x0, y1 - y0, COUNTER_H - 0.04), ((x0 + x1) / 2, (y0 + y1) / 2, (COUNTER_H - 0.04) / 2), M['satin'])
    B('top', (x1 - x0 + 0.06, y1 - y0 + 0.04, 0.04), ((x0 + x1) / 2 + 0.03, (y0 + y1) / 2, COUNTER_H - 0.02), M['counter_top'])
    B('kick', (0.02, y1 - y0, 0.1), (x1 + 0.005, (y0 + y1) / 2, 0.05), M['black'])
    # the front: lit panels, red and green, in steel frames
    n = 6; pw = (y1 - y0) / n
    for i in range(n):
        yc = y0 + pw * (i + 0.5)
        B(f'panel{i}', (0.02, pw - 0.05, 0.78), (x1 + 0.012, yc, 0.53), M['panel_red'] if i % 2 == 0 else M['panel_green'])
        B(f'mull{i}', (0.03, 0.03, 0.84), (x1 + 0.016, y0 + pw * i, 0.53), M['steel'])
    B(f'mull{n}', (0.03, 0.03, 0.84), (x1 + 0.016, y1, 0.53), M['steel'])
    # the cases over it: the prizes' shelves at the back, aluminium uprights and rails in front (no glass: open)
    out.append(panel('conc_prizes', y1 - y0 - 0.04, 1.06, (x0 + 0.06, (y0 + y1) / 2, COUNTER_H + 0.58), (1, 0, 0), M['prizes'], col, flip_u=False))
    for i in range(n + 1):
        B(f'upright{i}', (0.03, 0.03, 1.15), (x1 - 0.02, y0 + pw * i, COUNTER_H + 0.6), M['alu'])
    for z in (COUNTER_H + 0.04, COUNTER_H + 1.16):
        B(f'rail{z:.2f}', (0.035, y1 - y0, 0.03), (x1 - 0.02, (y0 + y1) / 2, z), M['alu'])
    for z in (COUNTER_H + 0.38, COUNTER_H + 0.74):
        B(f'shelf{z:.2f}', (x1 - x0 - 0.1, y1 - y0 - 0.06, 0.012), ((x0 + x1) / 2, (y0 + y1) / 2, z), M['alu'])
    B('case_top', (x1 - x0, y1 - y0, 0.04), ((x0 + x1) / 2, (y0 + y1) / 2, COUNTER_H + 1.2), M['satin'])
    B('amber', (0.03, y1 - y0 - 0.1, 0.015), (x1 - 0.08, (y0 + y1) / 2, COUNTER_H + 1.16), M['amber'])
    # the CONCESSION light box over the cases, a dark header round it
    B('header', (0.22, y1 - y0 + 0.04, 0.46), (x1 - 0.06, (y0 + y1) / 2, COUNTER_H + 1.45), M['satin'])
    out.append(panel('conc_sign', y1 - y0 - 0.1, 0.34, (x1 + 0.052, (y0 + y1) / 2, COUNTER_H + 1.45), (1, 0, 0), M['concession'], col))
    return out


# ---------------------------------------------------------------- the popcorn machine
def popcorn(M, col):
    """A kettle machine on its stand: a red base cabinet on castors, the glass box over it (left open: its glass would
    vanish in the case), red corner posts and a red roof with a marquee, the steel kettle hung from the roof, the
    popcorn heaped round it, a lamp in the roof."""
    F = frame_at(POPCORN, (0.0, -1.0)); w, d = 0.62, 0.46; out = []
    parts = [('base', (w, d, 0.72), (0, 0, 0.42), M['red']), ('base_trim', (w + 0.02, d + 0.02, 0.03), (0, 0, 0.79), M['chrome']),
             ('floor', (w - 0.04, d - 0.04, 0.03), (0, 0, 0.82), M['steel']), ('roof', (w + 0.02, d + 0.02, 0.1), (0, 0, 1.47), M['red']),
             ('marquee', (w - 0.04, 0.02, 0.12), (0, -d / 2 - 0.005, 1.47), M['cream'])]
    for sx in (-1, 1):
        for sy in (-1, 1): parts.append((f'post{sx}{sy}', (0.03, 0.03, 0.62), (sx * (w / 2 - 0.015), sy * (d / 2 - 0.015), 1.12), M['red']))
    parts.append(('door_bar', (w - 0.06, 0.015, 0.02), (0, d / 2 - 0.01, 0.84), M['chrome']))
    out += framed('popcorn', M, col, F, parts)
    pile = []
    import random; rnd = random.Random(7)
    bm = bmesh.new()
    for i in range(220):                                                        # the heap: little lumps over the floor, deeper at the back
        p = Vector((rnd.uniform(-w / 2 + 0.05, w / 2 - 0.05), rnd.uniform(-d / 2 + 0.05, d / 2 - 0.05), 0))
        p.z = 0.84 + 0.02 + 0.07 * (p.y + d / 2) / d * rnd.random()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=rnd.uniform(0.012, 0.02), matrix=Matrix.Translation(p))
    o = cine._mesh_obj('popcorn_heap', bm, M['popcorn'], col); o['lm'] = 'furn'; out.append(o); cine.place(o, F)
    k = lathe('popcorn_kettle', [(0.0, 1.06), (0.1, 1.06), (0.11, 1.08), (0.115, 1.2), (0.12, 1.21), (0.0, 1.21)], M['steel'], seg=24, collection=col, lm='furn')
    k.location = (0.06, 0.02, 0); cine.place(k, F); out.append(k)
    out += framed('popcorn_rod', M, col, F, [('rod', (0.015, 0.015, 0.22), (0.06, 0.02, 1.32), M['chrome'])])
    lamp = box('popcorn_lamp', (0.2, 0.06, 0.012), (0, 0, 1.41), M['pop_lamp'], collection=col); cine.place(lamp, F); out.append(lamp)
    return out


def popcorn_lamp_point():
    return (frame_at(POPCORN, (0.0, -1.0)) @ Vector((0, 0, 1.36, 1))).xyz


# ---------------------------------------------------------------- the hackers' tables
def tables(M, col):
    out = []
    def table(name, x0, x1, y0, y1):
        o = [box(f'{name}_top', (x1 - x0, y1 - y0, 0.03), ((x0 + x1) / 2, (y0 + y1) / 2, TABLE_H - 0.015), M['table'], collection=col, lm='furn')]
        cine.world_uv(o[0], 1.0)
        for sx in (x0 + 0.06, x1 - 0.06):
            for sy in (y0 + 0.06, y1 - 0.06):
                o.append(cyl(f'{name}_leg{sx:.1f}{sy:.1f}', 0.016, TABLE_H - 0.03, (sx, sy, (TABLE_H - 0.03) / 2), M['steel'], seg=10, collection=col, lm='furn'))
        return o
    out += table('table1', *TABLE)
    out += table('table2', *TABLE2)
    # two monitors on the long table, facing the chair (+x), turned a little toward the room's front
    for k, p in enumerate(SCREENS):
        F = Matrix.Translation((p.x, p.y, TABLE_H)) @ Matrix.Rotation(math.radians(90 + 12), 4, 'Z')   # local -y faces +x, turned
        parts = [(f'mon{k}_foot', (0.22, 0.18, 0.012), (0, 0.04, 0.006), M['plastic']), (f'mon{k}_neck', (0.05, 0.03, 0.3), (0, 0.06, 0.16), M['plastic']),
                 (f'mon{k}_body', (0.56, 0.05, 0.36), (0, 0.02, 0.38), M['plastic'])]
        out += framed('screen', M, col, F, parts)
        scr = panel(f'screen{k}', 0.52, 0.31, (0, -0.006, 0.385), (0, -1, 0), M['terminal'] if k == 1 else M['desktop'], col)
        cine.place(scr, F); out.append(scr)
        if k == 1:                                                              # the terminal: drawn live (the hack running)
            scr['role'] = 'screen'; scr['q'] = 0; del scr['lm']
    # the keyboard and mouse before them; a takeaway bag; cables to the floor
    kb = box('keyboard', (0.15, 0.44, 0.02), (-2.74, -0.95, TABLE_H + 0.01), M['plastic'], collection=col, lm='furn'); out.append(kb)
    out.append(box('mouse', (0.1, 0.06, 0.03), (-2.74, -0.6, TABLE_H + 0.015), M['plastic'], collection=col, lm='furn'))
    out.append(box('bag', (0.16, 0.12, 0.2), (-3.2, -1.78, TABLE_H + 0.1), M['cream'], rot=(0, 0, 0.3), collection=col, lm='furn'))
    out.append(box('tower', (0.2, 0.45, 0.45), (-3.15, -1.75, 0.225), M['plastic'], collection=col, lm='furn'))
    out.append(tube('cable_a', [(-3.1, -1.1, TABLE_H), (-3.3, -1.1, 0.4), (-3.32, -1.4, 0.03), (-3.0, -1.6, 0.012)], 0.006, M['black'], col, seg=6, lm='furn'))
    # the laptop table: an open laptop, a monitor
    lp = Matrix.Translation((-3.1, -0.05, TABLE_H)) @ Matrix.Rotation(math.radians(-70), 4, 'Z')
    out += framed('laptop', M, col, lp, [('base', (0.34, 0.24, 0.02), (0, 0, 0.01), M['plastic'])])
    lid = box('laptop_lid', (0.34, 0.012, 0.23), (0, 0.12, 0.13), M['plastic'], rot=(-0.25, 0, 0), collection=col, lm='furn'); cine.place(lid, lp); out.append(lid)
    ls = panel('laptop_screen', 0.3, 0.19, (0, 0.11, 0.135), (0, -math.cos(0.25), math.sin(0.25)), M['desktop'], col); cine.place(ls, lp); out.append(ls)
    return out


def chair(M, col):
    """Tyrell's office chair: a five-star base on castors, the gas lift, a padded seat and back in dark red."""
    p, f = CHAIR; F = frame_at(p, f); out = []
    parts = [('seat', (0.48, 0.46, 0.07), (0, 0.0, SEAT_H - 0.03), M['chair']), ('back', (0.46, 0.06, 0.52), (0, 0.25, SEAT_H + 0.33), M['chair']),
             ('spine', (0.05, 0.04, 0.3), (0, 0.24, SEAT_H + 0.02), M['black']), ('lift', (0.05, 0.05, 0.3), (0, 0, 0.27), M['chrome'])]
    out += framed('chair', M, col, F, parts)
    for k in range(5):
        a = 2 * math.pi * k / 5; d = Vector((math.cos(a), math.sin(a), 0))
        o = box(f'chair_star{k}', (0.3, 0.04, 0.03), (d.x * 0.15, d.y * 0.15, 0.08), M['black'], rot=(0, 0, a), collection=col, lm='furn'); cine.place(o, F); out.append(o)
        o = cyl(f'chair_castor{k}', 0.025, 0.02, (d.x * 0.29, d.y * 0.29, 0.03), M['black'], rot=(math.pi / 2, 0, a), seg=10, collection=col, lm='furn'); cine.place(o, F); out.append(o)
    return out


def seat_point():
    p, f = CHAIR
    return Vector((p.x, p.y, SEAT_H)), f


# ---------------------------------------------------------------- the right side and the corner
def machine_00(M, col):
    """The 00 machine: a tall red cabinet, its face the two great rings, a lit marquee."""
    F = frame_at(M00, (-1.0, 0.0)); w = 0.96
    parts = [('body', (w, 0.7, 1.9), (0, 0.1, 0.95), M['m00_body']), ('top', (w + 0.04, 0.74, 0.08), (0, 0.1, 1.94), M['chrome']),
             ('base', (w + 0.02, 0.72, 0.1), (0, 0.1, 0.05), M['black'])]
    out = framed('m00', M, col, F, parts)
    face = panel('m00_face', w - 0.06, 1.62, (0, -0.256, 1.0), (0, -1, 0), M['m00'], col); cine.place(face, F); out.append(face)
    return out


def cabinet(name, M, col, at, facing, mat, kind='slot'):
    """An upright: a slot machine (the reels and a lit belly glass) or a video cabinet (a lit marquee, the screen)."""
    F = frame_at(at, facing); w = 0.62
    parts = [('body', (w, 0.62, 1.72), (0, 0.06, 0.86), M['satin']), ('top', (w + 0.02, 0.64, 0.05), (0, 0.06, 1.745), M['chrome' if kind == 'slot' else 'black']),
             ('ledge', (w, 0.18, 0.05), (0, -0.3, 0.92), M['black' if kind == 'slot' else 'plastic'])]
    out = framed(name, M, col, F, parts)
    face = panel(f'{name}_face', w - 0.06, 1.5, (0, -0.256, 0.95), (0, -1, 0), mat, col); cine.place(face, F); out.append(face)
    if kind == 'slot':
        h = cyl(f'{name}_handle', 0.012, 0.4, (w / 2 + 0.03, 0.0, 1.2), M['chrome'], seg=8, collection=col, lm='furn'); cine.place(h, F); out.append(h)
        b = cyl(f'{name}_knob', 0.035, 0.07, (w / 2 + 0.03, 0.0, 1.42), M['red'], seg=12, collection=col, lm='furn'); cine.place(b, F); out.append(b)
    return out


def right_side(M, col):
    out = machine_00(M, col)
    for k, p in enumerate(SLOTS): out += cabinet(f'slot{k}', M, col, p, (-1.0, 0.0), M[f'slot{k}'], 'slot')
    for k, p in enumerate(CORNER): out += cabinet(f'corner{k}', M, col, p, (0.0, -1.0), M[f'cab{k}'], 'video')
    out += cabinet('change', M, col, CHANGE, (-1.0, 0.0), M['change'], 'video')
    # the ticket centre: a low counter booth with a glass-topped case, its sign and the TICKETS banners over it
    F = frame_at(TICKETS, (-1.0, 0.0))
    parts = [('desk', (1.4, 0.6, 1.0), (0, 0.0, 0.5), M['blue']), ('top', (1.44, 0.64, 0.04), (0, 0.0, 1.02), M['counter_top']),
             ('post_l', (0.06, 0.06, 1.4), (-0.66, 0.2, 1.72), M['chrome']), ('post_r', (0.06, 0.06, 1.4), (0.66, 0.2, 1.72), M['chrome']),
             ('board', (1.4, 0.06, 0.44), (0, 0.2, 2.2), M['satin'])]
    out += framed('ticket', M, col, F, parts)
    s = panel('ticket_sign', 1.3, 0.4, (0, 0.165, 2.2), (0, -1, 0), M['ticketcenter'], col); cine.place(s, F); out.append(s)
    for k, dx in enumerate((-0.42, 0.42)):
        s = panel(f'tickets_neon{k}', 0.62, 0.24, (dx, 0.1, 2.6), (0, -1, 0), M['tickets'], col); cine.place(s, F); out.append(s)
        out += framed(f'tickets_back{k}', M, col, F, [('b', (0.66, 0.03, 0.28), (dx, 0.125, 2.6), M['black'])])
    # the GAMES board on the back wall
    out.append(box('games_board', (1.22, 0.05, 0.78), (GAMES.x, BACK - 0.03, GAMES.z), M['black'], collection=col, lm='furn'))
    out.append(panel('games_sign', 1.16, 0.72, (GAMES.x, BACK - 0.058, GAMES.z), (0, -1, 0), M['games'], col))
    # NO SMOKING by the 00 machine, high on the corner's side
    out.append(panel('nosmoking', 0.3, 0.15, (CANOPY[1] + 0.25, BACK - 0.012, 2.0), (0, -1, 0), M['nosmoking'], col))
    # the air-hockey table in front: a long cabinet, the white top, its rails
    F = frame_at(HOCKEY, (0.0, -1.0))
    parts = [('body', (1.1, 2.0, 0.7), (0, 0, 0.35), M['red']), ('top', (1.0, 1.9, 0.02), (0, 0, 0.72), M['felt']),
             ('rail_l', (0.05, 2.0, 0.08), (-0.53, 0, 0.74), M['blue']), ('rail_r', (0.05, 2.0, 0.08), (0.53, 0, 0.74), M['blue']),
             ('rail_f', (1.1, 0.05, 0.08), (0, -0.98, 0.74), M['blue']), ('rail_b', (1.1, 0.05, 0.08), (0, 0.98, 0.74), M['blue'])]
    out += framed('hockey', M, col, F, parts)
    for k, dy in enumerate((-0.6, 0.6)):
        m = cyl(f'hockey_mallet{k}', 0.045, 0.04, (0.1 * k, dy, 0.75), M['red'], seg=16, collection=col, lm='furn'); cine.place(m, F); out.append(m)
    return out


def clutter(M, col):
    """Boxes and crates by the counter's end, a trash can, a fire extinguisher, cables across the floor."""
    from rooms.the_godfather import _fit
    out = []
    for name, at, size, axis, rz in (('cardboard_box_01', (-4.25, 0.8, 0.0), 0.5, 'x', 0.2), ('plastic_crate_01', (-4.3, 1.35, 0.0), 0.5, 'x', -0.1),
                                    ('metal_trash_can', (-1.25, -3.2, 0.0), 0.5, 'z', 0.0), ('korean_fire_extinguisher_01', (-4.5, -3.2, 0.0), 0.5, 'z', 0.0)):
        path = os.path.join(PH, name, f'{name}_1k.gltf')
        if not os.path.exists(path): cine.log('missing', path); continue
        _, ms = cine.import_gltf(path, collection=col)
        _fit(ms, at, size, axis=axis, ground=True)
        for o in ms:
            o['lm'] = 'furn'
            o.matrix_world = Matrix.Translation(at) @ Matrix.Rotation(rz, 4, 'Z') @ Matrix.Translation(-Vector(at)) @ o.matrix_world
        out += ms
    out.append(tube('cable_floor', [(-2.6, -0.2, 0.012), (-1.8, 0.1, 0.012), (-0.8, 0.25, 0.012), (0.4, 0.2, 0.012), (1.4, 0.32, 0.012)], 0.008, M['black'], col, seg=6, lm='furn'))
    return out


def gun(M, col):
    """The pistol (Poly Haven's service pistol), in the popcorn: a live prop (role mug) a hand carries during the act;
    the build sets where it rests (as it is held when the hand closes on it)."""
    from rooms.the_godfather import _fit
    path = os.path.join(PH, 'service_pistol', 'service_pistol_1k.gltf')
    _, ms = cine.import_gltf(path, collection=col)
    _fit(ms, (0, 0, 0), 0.19, axis='x')
    F = frame_at(POPCORN, (0.0, -1.0)) @ Matrix.Translation((0.02, -0.05, 0.9)) @ Matrix.Rotation(0.4, 4, 'Z')   # in the heap until the build places it
    for o in ms:
        if o.parent is None or o.parent.type != 'MESH': o.matrix_world = F @ o.matrix_world
    out = []
    for o in ms:
        o['role'] = 'mug'; o.name = 'gun_' + o.name
        if 'lm' in o: del o['lm']
        out.append(o)
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
            c = ob.matrix_world @ (sum((me.vertices[i].co for i in f.vertices), Vector()) / len(f.vertices))
            if f.normal.z > 0.9 and abs(c.z - RH) < 0.006: f.material_index = k


# ---------------------------------------------------------------- light
PURPLE = (0.62, 0.16, 1.0)
WHITE = (0.86, 0.92, 1.0)
AMBER = (1.0, 0.68, 0.36)


def lights():
    """The arcade after hours: the backglasses and the canopy's tubes over the lanes; the counter's red and green
    panels throwing their colour across the floor; the amber strip in the prize cases; GAMES washing the back corner
    and the right side purple; the two screens' cyan on the table and whoever sits at it; the TICKETS neon; the lamp in
    the popcorn machine; one troffer left on over the middle, dim; a soft fill from the front so the case reads."""
    out = []
    def light(name, kind, loc, energy, colour, rot=None, **kw):
        ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = colour
        for k, v in kw.items(): setattr(ld, k, v)
        ob = cine.link(bpy.data.objects.new(name, ld)); ob.location = loc
        if rot: ob.rotation_euler = rot
        if kind in ('AREA', 'SPOT', 'SUN'): ob.visible_camera = False; ob.visible_glossy = False
        out.append(ob); return ob
    aim = lambda p, t: (Vector(t) - Vector(p)).to_track_quat('-Z', 'Y').to_euler()
    x0, x1, y0, y1, zu = CANOPY
    for j in range(3):                                                          # under the canopy, down over the lanes' targets
        xc = x0 + (x1 - x0) * (j + 0.5) / 3; p = (xc, y0 + 0.2, zu - 0.04)
        light(f'canopy{j}', 'AREA', p, 85.0, WHITE, rot=aim(p, (xc, y0 + 0.9, 1.1)), shape='RECTANGLE', size=(x1 - x0) / 3 - 0.1, size_y=0.12)
    for j in range(2):                                                          # the backglasses' glow on the floor before the lanes
        xc = x0 + (x1 - x0) * (j + 0.5) / 2; p = (xc, LANE_Y1 - 0.4, 2.2)
        light(f'backglass{j}', 'AREA', p, 50.0, (1.0, 0.94, 0.84), rot=aim(p, (xc, -0.6, 0.0)), shape='RECTANGLE', size=(x1 - x0) / 2, size_y=0.5)
    cx = COUNTER[1] + 0.08
    for k, (yc, col_) in enumerate(((-2.2, (1.0, 0.08, 0.06)), (-1.3, (0.08, 1.0, 0.3)), (-0.4, (1.0, 0.08, 0.06)), (0.05, (0.08, 1.0, 0.3)))):
        p = (cx, yc, 0.55)
        light(f'panel{k}', 'AREA', p, 70.0, col_, rot=aim(p, (cx + 1.0, yc, 0.2)), shape='RECTANGLE', size=0.5, size_y=0.6)
    p = (COUNTER[1] - 0.1, (COUNTER[2] + COUNTER[3]) / 2, COUNTER_H + 1.1)
    light('cases', 'AREA', p, 120.0, AMBER, rot=aim(p, (p[0] - 0.2, p[1], 0.9)), shape='RECTANGLE', size=0.25, size_y=COUNTER[3] - COUNTER[2])
    light('cases_out', 'AREA', (COUNTER[1] + 0.05, p[1], COUNTER_H + 1.0), 60.0, AMBER, rot=aim((COUNTER[1] + 0.05, p[1], COUNTER_H + 1.0), (0.0, p[1], 0.0)), shape='RECTANGLE', size=0.2, size_y=2.4)
    light('games', 'POINT', (GAMES.x, BACK - 0.5, GAMES.z), 140.0, PURPLE, shadow_soft_size=0.4)
    light('purple_wash', 'AREA', (2.6, 0.6, RH - 0.05), 320.0, PURPLE, rot=(0, 0, 0), shape='RECTANGLE', size=3.6, size_y=4.6)
    light('tickets', 'POINT', (TICKETS.x - 0.4, TICKETS.y, 2.5), 40.0, (1.0, 0.7, 0.2), shadow_soft_size=0.3)
    for k, p in enumerate(SCREENS):
        q = (p.x + 0.1, p.y, TABLE_H + 0.38)
        light(f'screen{k}', 'AREA', q, 16.0, (0.55, 0.95, 1.0), rot=aim(q, (q[0] + 1.0, q[1] + 0.1, 1.0)), shape='RECTANGLE', size=0.5, size_y=0.3)
    light('popcorn', 'POINT', popcorn_lamp_point(), 12.0, (1.0, 0.78, 0.45), shadow_soft_size=0.05)
    light('troffer', 'AREA', (-0.8, -0.9, RH - 0.03), 70.0, (0.78, 0.86, 1.0), rot=(0, 0, 0), shape='RECTANGLE', size=0.6, size_y=1.2)
    light('fill_front', 'AREA', (0.0, FRONT - 0.2, 2.6), 110.0, (0.82, 0.78, 0.92), rot=aim((0.0, FRONT - 0.2, 2.6), (-0.6, 0.4, 0.7)), shape='RECTANGLE', size=5.0, size_y=1.4)
    return out
