# Severance · Macrodata Refinement, Lumon.
# A wide white room under a low ceiling (7 ft 9 in), grass-green carpet, white panelled walls with dark reveals,
# and in the middle the four-desk island: white desks in a pinwheel around a cross of bottle-green partitions,
# a Lumon terminal on each (cream yoke, dark CRT, two-tone blue keyboard, trackball), charcoal task chairs on mats.
import math, os
from mathutils import Vector, Matrix, Euler
import cine
from cine import box, cyl, rounded_slab, material

W, D, H = 9.6, 7.6, 2.36          # the room fills the module; ceiling 2.36 m
T = 0.12                          # wall thickness
ISLAND = Vector((0.15, 0.55, 0))  # centre of the desk island
TEX = os.path.join(cine.OUT, 'textures', 'severance')
tx = lambda n: os.path.join(TEX, n)

# ---------------------------------------------------------------- materials
def mats():
    M = {}
    M['carpet'] = material('carpet', rough=0.95, maps={'color': tx('carpet_color.jpg'), 'normal': tx('carpet_normal.jpg'), 'rough': tx('carpet_rough.jpg')}, scale=0.9, normal_strength=0.3, specular=0.3)
    M['wall'] = material('wall', rough=0.78, maps={'color': tx('wall_color.jpg'), 'normal': tx('wall_normal.jpg')}, scale=1.6, normal_strength=0.06)
    M['reveal'] = material('reveal', (0.032, 0.034, 0.035), rough=0.6)
    M['kerb'] = material('kerb', (0.72, 0.72, 0.70), rough=0.9)
    M['laminate'] = material('laminate', (0.80, 0.80, 0.78), rough=0.3, coat=0.25, coat_rough=0.12)
    M['paint'] = material('paint_white', (0.76, 0.765, 0.75), rough=0.42)
    M['alu'] = material('aluminium', (0.80, 0.81, 0.82), rough=0.32, metal=1.0)
    M['partition'] = material('partition', rough=0.92, maps={'color': tx('partition_color.jpg'), 'normal': tx('partition_normal.jpg')}, scale=0.35, normal_strength=0.5)
    M['chair'] = material('chair_fabric', rough=0.9, maps={'color': tx('chair_color.jpg'), 'normal': tx('chair_normal.jpg')}, scale=0.25, normal_strength=0.6, sheen=0.4)
    M['plastic'] = material('black_plastic', (0.018, 0.018, 0.02), rough=0.42)
    M['chrome'] = material('chrome', (0.93, 0.93, 0.94), rough=0.12, metal=1.0)
    M['rubber'] = material('rubber', (0.01, 0.01, 0.01), rough=0.7)
    M['mat'] = material('chair_mat', (0.03, 0.033, 0.035), rough=0.14, specular=0.6)
    M['cream'] = material('terminal_cream', (0.78, 0.74, 0.63), rough=0.42, coat=0.2, coat_rough=0.2)
    M['slate'] = material('monitor_slate', (0.034, 0.045, 0.062), rough=0.48)
    M['keynavy'] = material('key_navy', (0.013, 0.026, 0.10), rough=0.4)
    M['keyblue'] = material('key_blue', (0.11, 0.30, 0.58), rough=0.4)
    M['ball'] = material('trackball', (0.012, 0.012, 0.014), rough=0.12, coat=1.0)
    M['screen'] = material('crt_screen', (0.004, 0.012, 0.014), rough=0.08, emission=(0.10, 0.62, 0.80), emission_strength=0.9, coat=1.0, coat_rough=0.02)
    M['door'] = material('door', (0.78, 0.785, 0.77), rough=0.38)
    M['steel'] = material('brushed_steel', (0.62, 0.62, 0.62), rough=0.28, metal=1.0)
    M['ceiling'] = material('ceiling', rough=0.9, maps={'color': tx('ceiling_color.jpg')}, scale=1.2)
    M['paper'] = material('paper', (0.80, 0.79, 0.74), rough=0.85)
    M['ceramic'] = material('ceramic', (0.82, 0.82, 0.80), rough=0.18, coat=1.0, coat_rough=0.05)
    M['coffee'] = material('coffee', (0.02, 0.008, 0.003), rough=0.05)
    M['troffer'] = material('troffer', (1, 1, 1), rough=0.6, emission=(1.0, 0.985, 0.96), emission_strength=6.0)
    return M


# ---------------------------------------------------------------- architecture
def walls(M, arch, phantom):
    box('subfloor', (W, D, 0.03), (0, 0, -0.027), M['reveal'], bev=0, collection=arch, lm='arch')
    # carpet from the left and back wall backings to the kerbs: x [-4.70, 4.68], y [-3.68, 3.70]
    box('carpet', (9.38, 7.38, 0.012), (-0.01, 0.01, -0.006), M['carpet'], bev=0.002, collection=arch, lm='arch')
    # the walls: a dark backing, white panels 1.2 m wide in front of it with 12 mm reveals, a 9 cm shadow gap at the floor
    box('back_backing', (W, T - 0.02, H), (0, D / 2 - (T - 0.02) / 2, H / 2), M['reveal'], bev=0, collection=arch, lm='arch')
    box('left_backing', (T - 0.02, D - 0.10, H), (-W / 2 + (T - 0.02) / 2, -0.05, H / 2), M['reveal'], bev=0, collection=arch, lm='arch')
    door_x = (2.45, 3.45)
    x0, x1, n = -W / 2 + T, W / 2, 8
    pw = (x1 - x0) / n
    for i in range(n):
        a, b = x0 + i * pw + 0.006, x0 + (i + 1) * pw - 0.006
        if b > door_x[0] - 0.05 and a < door_x[1] + 0.05:
            # panels around the door: split at the opening
            for s, e in ((a, door_x[0] - 0.04), (door_x[1] + 0.04, b)):
                if e - s > 0.05: box(f'back_panel_{i}_{s:.2f}', (e - s, 0.02, H - 0.09), ((s + e) / 2, D / 2 - T + 0.01, 0.09 + (H - 0.09) / 2), M['wall'], bev=0.0025, collection=arch, lm='arch')
            s, e = max(a, door_x[0] - 0.04), min(b, door_x[1] + 0.04)
            box(f'back_header_{i}', (e - s, 0.02, H - 2.14), ((s + e) / 2, D / 2 - T + 0.01, 2.14 + (H - 2.14) / 2), M['wall'], bev=0.0025, collection=arch, lm='arch')
        else:
            box(f'back_panel_{i}', (b - a, 0.02, H - 0.09), ((a + b) / 2, D / 2 - T + 0.01, 0.09 + (H - 0.09) / 2), M['wall'], bev=0.0025, collection=arch, lm='arch')
    y0, y1, n = -D / 2, D / 2 - T, 6
    pw = (y1 - y0) / n
    for i in range(n):
        a, b = y0 + i * pw + 0.006, y0 + (i + 1) * pw - 0.006
        box(f'left_panel_{i}', (0.02, b - a, H - 0.09), (-W / 2 + T - 0.01, (a + b) / 2, 0.09 + (H - 0.09) / 2), M['wall'], bev=0.0025, collection=arch, lm='arch')
    # the door: a flush white leaf in a slim frame, a long steel pull
    dc = (door_x[0] + door_x[1]) / 2
    box('door_leaf', (0.92, 0.035, 2.06), (dc, D / 2 - T + 0.005, 1.035), M['door'], bev=0.003, collection=arch, lm='arch')
    for sx in (-1, 1): box(f'door_jamb_{sx}', (0.035, 0.05, 2.12), (dc + sx * 0.4775, D / 2 - T + 0.012, 1.06), M['paint'], bev=0.002, collection=arch, lm='arch')
    box('door_head', (0.99, 0.05, 0.035), (dc, D / 2 - T + 0.012, 2.1225), M['paint'], bev=0.002, collection=arch, lm='arch')
    cyl('door_pull', 0.011, 0.62, (dc - 0.36, D / 2 - T - 0.045, 1.05), M['steel'], collection=arch, lm='furn')
    for z in (0.78, 1.32): box(f'door_pull_post_{z}', (0.012, 0.05, 0.012), (dc - 0.36, D / 2 - T - 0.02, z), M['steel'], bev=0.002, collection=arch, lm='furn')
    # a light switch plate and a thermostat by the door
    box('switch_plate', (0.075, 0.008, 0.118), (door_x[0] - 0.22, D / 2 - T - 0.004, 1.2), M['paint'], bev=0.002, collection=arch, lm='furn')
    box('thermostat', (0.09, 0.022, 0.09), (door_x[0] - 0.22, D / 2 - T - 0.011, 1.5), M['paint'], bev=0.006, collection=arch, lm='furn')
    # a slot diffuser high on the left wall
    box('diffuser', (0.03, 1.2, 0.09), (-W / 2 + T + 0.005, 0.2, H - 0.16), M['reveal'], bev=0.002, collection=arch, lm='arch')
    for k in range(5): box(f'diffuser_vane_{k}', (0.036, 1.18, 0.006), (-W / 2 + T + 0.006, 0.2, H - 0.2 + k * 0.02), M['paint'], bev=0, collection=arch, lm='arch')
    # the cut-away: front and right walls end in a low kerb, their section showing
    box('kerb_front', (W, T, 0.22), (0, -D / 2 + T / 2, 0.11), M['kerb'], bev=0.002, collection=arch, lm='arch')
    box('kerb_right', (T, D - T - T, 0.22), (W / 2 - T / 2, 0, 0.11), M['kerb'], bev=0.002, collection=arch, lm='arch')
    # phantoms: what a real room would have, so the light bounces as it would (never exported)
    box('ceiling', (W, D, 0.04), (0, 0, H + 0.02), M['ceiling'], bev=0, collection=phantom, bake_only=1)
    box('front_wall', (W, T, H - 0.22), (0, -D / 2 + T / 2, 0.22 + (H - 0.22) / 2), M['wall'], bev=0, collection=phantom, bake_only=1)
    box('right_wall', (T, D, H - 0.22), (W / 2 - T / 2, 0, 0.22 + (H - 0.22) / 2), M['wall'], bev=0, collection=phantom, bake_only=1)


TROFFERS = [(x, y) for x in (-3.6, -1.2, 1.2, 3.6) for y in (-2.4, 0.0, 2.4)]
TROFFER_SIZE, TROFFER_W = (0.6, 1.2), 26.0


def lights():
    """Recessed 600 x 1200 fluorescent troffers in a 2.4 m grid, just under the (phantom) ceiling."""
    return [bpy_light(f'troffer_{x}_{y}', (x, y, H - 0.005), TROFFER_SIZE, TROFFER_W) for x, y in TROFFERS]


def bpy_light(name, loc, size, power):
    import bpy
    ld = bpy.data.lights.new(name, 'AREA'); ld.shape = 'RECTANGLE'; ld.size, ld.size_y = size; ld.energy = power
    ld.color = (0.97, 0.985, 1.0)
    try: ld.use_soft_falloff = True
    except Exception: pass
    ob = cine.link(bpy.data.objects.new(name, ld)); ob.location = loc
    return ob
