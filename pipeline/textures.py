# Prepares a room's textures from the cached CC0 sources: recolour by luminance (keeps the material's own
# variation, sets its mean colour), resize, and write web-friendly JPEGs into pipeline/out/textures/<room>/.
# Usage: python pipeline/textures.py severance
import os, sys
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CACHE = os.path.join(ROOT, 'pipeline', 'cache')


def srgb_to_lin(c): c = np.asarray(c, np.float32); return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def lin_to_srgb(c): c = np.clip(c, 0, 1); return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def tint(src, dst, target_srgb, size=2048, contrast=1.0):
    """Mean colour -> target (sRGB 0-255), keeping the texture's relative luminance variation (raised to `contrast`)."""
    im = np.asarray(Image.open(src).convert('RGB').resize((size, size), Image.LANCZOS), np.float32) / 255
    lin = srgb_to_lin(im); lum = lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    rel = (lum / max(lum.mean(), 1e-4)) ** contrast
    out = srgb_to_lin(np.array(target_srgb, np.float32) / 255)[None, None, :] * rel[..., None]
    Image.fromarray((lin_to_srgb(out) * 255 + 0.5).astype(np.uint8)).save(dst, quality=92)
    return dst


def copy(src, dst, size=2048, mode='RGB'):
    Image.open(src).convert(mode).resize((size, size), Image.LANCZOS).save(dst, quality=92)
    return dst


def severance(out):
    acg = lambda i, m: os.path.join(CACHE, 'ambientcg', i, f'{i}_2K-JPG_{m}.jpg')
    ph = lambda i, m: os.path.join(CACHE, 'polyhaven', i, f'{m}.png')
    # the carpet: Lumon's grass green under cool fluorescent light
    tint(acg('Carpet012', 'Color'), f'{out}/carpet_color.jpg', (64, 118, 80), contrast=0.85)
    copy(acg('Carpet012', 'NormalGL'), f'{out}/carpet_normal.jpg')
    copy(acg('Carpet012', 'Roughness'), f'{out}/carpet_rough.jpg', mode='L')
    # the partitions: bottle-green woven fabric
    tint(ph('rough_linen', 'Diffuse'), f'{out}/partition_color.jpg', (30, 62, 46), size=1024, contrast=1.3)
    copy(ph('rough_linen', 'nor_gl'), f'{out}/partition_normal.jpg', size=1024)
    # the chairs: charcoal knit
    tint(ph('jersey_melange', 'Diffuse'), f'{out}/chair_color.jpg', (52, 54, 58), size=1024, contrast=1.2)
    copy(ph('jersey_melange', 'nor_gl'), f'{out}/chair_normal.jpg', size=1024)
    # the walls: white paint over plaster, barely there
    tint(ph('white_plaster_02', 'Diffuse'), f'{out}/wall_color.jpg', (232, 233, 229), size=1024, contrast=0.12)
    copy(ph('white_plaster_02', 'nor_gl'), f'{out}/wall_normal.jpg', size=1024)
    # the ceiling (only seen in reflections and bounce light)
    copy(ph('ceiling_interior', 'Diffuse'), f'{out}/ceiling_color.jpg', size=1024)


def _lum(path, size):
    im = np.asarray(Image.open(path).convert('RGB').resize((size, size), Image.LANCZOS), np.float32) / 255
    return srgb_to_lin(im) @ np.array([0.2126, 0.7152, 0.0722], np.float32)


def _save(lin_rgb, dst):
    Image.fromarray((lin_to_srgb(lin_rgb) * 255 + 0.5).astype(np.uint8)).save(dst, quality=92)
    return dst


def _noise(size, px, seed):
    """Tileable band-limited noise in [0, 1], features about px texels across."""
    r = np.random.default_rng(seed).random((size, size)).astype(np.float32)
    big = Image.fromarray((np.tile(r, (3, 3)) * 255).astype(np.uint8))
    a = np.asarray(big.filter(ImageFilter.GaussianBlur(px)), np.float32)[size:2 * size, size:2 * size] / 255
    return (a - a.min()) / (a.max() - a.min() + 1e-6)


def _normal_from_height(h, strength):
    """A tangent-space normal map (OpenGL, +y up) from a tileable height field."""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength; dy = (np.roll(h, 1, 0) - np.roll(h, -1, 0)) * strength
    n = np.stack([-dx, -dy, np.ones_like(h)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return Image.fromarray(((n * 0.5 + 0.5) * 255 + 0.5).astype(np.uint8))


def the_matrix(out):
    """The hotel room of the red pill: an aged belle-epoque salon, its light faintly green (the film's grade)."""
    ph = lambda i, m: os.path.join(CACHE, 'polyhaven', i, f'{m}.png')
    lin = lambda c: srgb_to_lin(np.array(c, np.float32) / 255)
    S = 2048
    # damask wallpaper in the boiserie's panels: the decrepit paper's stains and tears, the jacquard's motif faint in it
    paper = _lum(ph('decrepit_wallpaper', 'Diffuse'), S); motif = _lum(ph('floral_jacquard', 'Diffuse'), S)
    mm = (motif - motif.min()) / (motif.max() - motif.min())
    rel = (paper / paper.mean()) ** 0.9 * (0.6 + 0.75 * mm)
    _save(lin((116, 122, 92))[None, None] * rel[..., None], f'{out}/wallpaper_color.jpg')
    copy(ph('decrepit_wallpaper', 'nor_gl'), f'{out}/wallpaper_normal.jpg')
    # the boiserie: cream paint gone ochre and grey over old plaster-smooth wood, a little chipped
    l = _lum(ph('white_plaster_02', 'Diffuse'), S); l = (l / l.mean()) ** 0.5
    chips = np.clip((_noise(S, 3, 41) - 0.78) * 6, 0, 1) * np.clip((_noise(S, 30, 42) - 0.5) * 3, 0, 1)
    _save(lin((150, 146, 110))[None, None] * l[..., None] * (1 - 0.45 * chips[..., None]), f'{out}/boiserie_color.jpg')
    # the floor: old dark boards
    tint(ph('old_wood_floor', 'Diffuse'), f'{out}/floor_color.jpg', (78, 60, 44), contrast=1.1)
    copy(ph('old_wood_floor', 'nor_gl'), f'{out}/floor_normal.jpg'); copy(ph('old_wood_floor', 'Rough'), f'{out}/floor_rough.jpg', mode='L')
    # the chairs: oxblood leather, rubbed lighter where hands and backs have worn it
    lea = _lum(ph('leather_red_03', 'Diffuse'), S); lea = (lea / lea.mean()) ** 1.4
    wear = np.clip((_noise(S, 30, 3) - 0.6) * 2.5, 0, 1) * 0.3 + np.clip((_noise(S, 4, 4) - 0.7) * 4, 0, 1) * 0.12
    base, rub = lin((88, 22, 19)), lin((120, 50, 42))
    _save((base[None, None] * (1 - wear[..., None]) + rub[None, None] * wear[..., None]) * lea[..., None], f'{out}/leather_color.jpg')
    copy(ph('leather_red_03', 'nor_gl'), f'{out}/leather_normal.jpg', size=1024)
    # button tufting: a diamond grid of buttons (4 diamonds across the tile), a height field -> normal map
    T = 1024; y, x = np.mgrid[0:T, 0:T].astype(np.float32) / T * 4
    u, v = (x + y) % 1 - 0.5, (x - y) % 1 - 0.5
    d = np.maximum(np.abs(u), np.abs(v)) * 2                                 # 0 in a diamond's middle, 1 at its pleats
    bx, by = (x % 1) - 0.5, (y % 1) - 0.5
    bd = np.minimum(np.hypot(bx, by), np.hypot(np.abs(bx) - 0.5, np.abs(by) - 0.5))   # to the nearest button
    h = np.maximum(np.cos(np.clip(d, 0, 1) * np.pi / 2), 0) ** 0.6 - 0.55 * np.exp(-(bd / 0.05) ** 2)
    _normal_from_height(h, 6.0).save(f'{out}/tufting_normal.jpg', quality=92)
    # the drapes: a dusty green-grey damask, heavy
    tint(ph('floral_jacquard', 'Diffuse'), f'{out}/drape_color.jpg', (82, 88, 70), size=1024, contrast=1.25)
    copy(ph('floral_jacquard', 'nor_gl'), f'{out}/drape_normal.jpg', size=1024)
    # the rug under the chairs: the jacquard's pattern as a faded red and navy weave, threadbare in patches
    m = _lum(ph('floral_jacquard', 'Diffuse'), 1024); m = (m - np.percentile(m, 5)) / (np.percentile(m, 95) - np.percentile(m, 5))
    m = np.clip((m - 0.45) * 4, 0, 1)                                         # the motif as a two-colour weave
    bare = np.clip((_noise(1024, 14, 9) - 0.7) * 3, 0, 1) * 0.6
    red, navy, thread = lin((104, 34, 30)), lin((34, 38, 56)), lin((120, 104, 82))
    rug = red[None, None] * (1 - m[..., None]) + navy[None, None] * m[..., None]
    _save(rug * (1 - bare[..., None]) + thread[None, None] * bare[..., None], f'{out}/rug_color.jpg')
    # dark veined marble for the fireplace
    n1, n2, n3, cloud = _noise(S, 160, 21), _noise(S, 48, 22), _noise(S, 14, 25), _noise(S, 60, 23)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32) / S
    warp = n1 * 5.0 + n2 * 1.2 + n3 * 0.18                                  # turbulence: veins wander and fork
    main = np.exp(-(np.abs(np.sin((xx * 2 + yy + warp) * np.pi)) / 0.05) ** 2)
    fine = np.exp(-(np.abs(np.sin((xx * 3 - yy * 2 + warp * 1.7) * np.pi)) / 0.025) ** 2) * 0.45
    vein = np.clip(main + fine, 0, 1) * (0.55 + 0.45 * _noise(S, 120, 24))
    dark, light = lin((30, 29, 28)), lin((122, 118, 110))
    _save(dark[None, None] * (0.75 + 0.5 * cloud[..., None]) * (1 - vein[..., None]) + light[None, None] * vein[..., None], f'{out}/marble_color.jpg')
    # lace for the windows: a fine net with rosettes and a scalloped hem, cut out by alpha
    L = 1024; y, x = np.mgrid[0:L, 0:L].astype(np.float32) / L
    net = (np.abs(((x * 64) % 1) - 0.5) > 0.42) | (np.abs(((y * 64) % 1) - 0.5) > 0.42)
    cx, cy = (x * 8) % 1 - 0.5, (y * 8 + 0.5 * np.floor(x * 8)) % 1 - 0.5; r = np.hypot(cx, cy); a = np.arctan2(cy, cx)
    rose = (np.abs(r - (0.28 + 0.05 * np.cos(a * 8))) < 0.025) | (np.abs(r - 0.12) < 0.02) | ((r < 0.3) & (np.abs(np.sin(a * 8)) < 0.12) & (r > 0.12))
    alpha = np.clip(net * 0.9 + rose * 1.0, 0, 1) * (0.75 + 0.25 * _noise(L, 3, 31))
    Image.fromarray(np.dstack([np.full((L, L, 3), 236, np.uint8), (alpha * 255).astype(np.uint8)]), 'RGBA').save(f'{out}/lace.png')
    # plaster where the paper has come away, and the phantom ceiling
    tint(ph('damaged_plaster', 'Diffuse'), f'{out}/plaster_color.jpg', (150, 138, 112), size=1024, contrast=0.8)
    tint(ph('ceiling_interior', 'Diffuse'), f'{out}/ceiling_color.jpg', (120, 110, 88), size=1024, contrast=0.6)


def lost(out):
    """The Swan: a DHARMA bunker of the seventies. The dome's plaster panels and dark struts, polished concrete
    underfoot; the living side in cream tiles set with terracotta, warm plaster, red leather in the booth."""
    ph = lambda i, m: os.path.join(CACHE, 'polyhaven', i, f'{m}.png')
    lin = lambda c: srgb_to_lin(np.array(c, np.float32) / 255)
    S = 2048
    # the dome's panels: rough plaster, pale and cool (the hidden lights make them glow green)
    tint(ph('concrete_wall_008', 'Diffuse'), f'{out}/panel_color.jpg', (128, 140, 122), contrast=1.2)
    copy(ph('concrete_wall_008', 'nor_gl'), f'{out}/panel_normal.jpg', size=1024)
    # the dome's floor: dark polished concrete
    tint(ph('smooth_concrete_floor', 'Diffuse'), f'{out}/concrete_floor_color.jpg', (74, 76, 72), contrast=1.1)
    copy(ph('smooth_concrete_floor', 'nor_gl'), f'{out}/concrete_floor_normal.jpg', size=1024)
    copy(ph('smooth_concrete_floor', 'Rough'), f'{out}/concrete_floor_rough.jpg', size=1024, mode='L')
    # cast concrete: the dome's riser, the columns, the section through the bunker
    tint(ph('brushed_concrete', 'Diffuse'), f'{out}/concrete_color.jpg', (128, 126, 118), contrast=1.0)
    copy(ph('brushed_concrete', 'nor_gl'), f'{out}/concrete_normal.jpg', size=1024)
    # the living side's walls: warm terracotta plaster
    tint(ph('concrete_wall_008', 'Diffuse'), f'{out}/plaster_color.jpg', (150, 96, 70), size=1024, contrast=0.55)
    # the struts and the booth's table: dark stained wood
    tint(ph('wood_table_worn', 'Diffuse'), f'{out}/strut_color.jpg', (30, 24, 20), size=1024, contrast=1.1)
    tint(ph('wood_table_worn', 'Diffuse'), f'{out}/table_wood_color.jpg', (92, 58, 36), size=1024, contrast=1.2)
    copy(ph('wood_table_worn', 'nor_gl'), f'{out}/wood_normal.jpg', size=1024)
    # the booth: red leather, worn paler where people sit
    lea = _lum(ph('leather_red_02', 'Diffuse'), 1024); lea = (lea / lea.mean()) ** 1.2
    wear = np.clip((_noise(1024, 26, 5) - 0.6) * 2.5, 0, 1) * 0.25
    base, rub = lin((112, 34, 26)), lin((140, 70, 52))
    _save((base[None, None] * (1 - wear[..., None]) + rub[None, None] * wear[..., None]) * lea[..., None], f'{out}/leather_color.jpg')
    copy(ph('leather_red_02', 'nor_gl'), f'{out}/leather_normal.jpg', size=1024)
    # the living side's floor: 40 cm cream tiles, every third on the diagonal terracotta; the texture spans 4 x 4 tiles
    n = 4; t = S // n
    grain = _lum(ph('worn_tile_floor', 'Diffuse'), S); grain = (grain / grain.mean()) ** 0.5
    y, x = np.mgrid[0:S, 0:S]; i, j = x // t, y // t; u, v = (x % t) / t, (y % t) / t
    terra = ((i + j) % 3 == 0) & ((i - j) % 2 == 0)
    tone = 0.92 + 0.16 * np.random.default_rng(8).random((n, n))[j, i]       # each tile its own firing
    col = np.where(terra[..., None], lin((150, 72, 48))[None, None], lin((206, 192, 162))[None, None]) * (tone * grain)[..., None]
    g = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v)) * t          # texels to the nearest joint
    grout = np.clip(1 - (g - 3) / 2, 0, 1)[..., None]
    _save(col * (1 - grout) + lin((96, 90, 80))[None, None] * grout, f'{out}/tile_color.jpg')
    h = np.clip((g - 2) / 6, 0, 1) * (1 + 0.02 * _noise(S, 6, 9))
    _normal_from_height(h.astype(np.float32), 1.5).resize((1024, 1024), Image.LANCZOS).save(f'{out}/tile_normal.jpg', quality=92)
    # the phantom ceiling (bounce light only)
    tint(ph('concrete_wall_008', 'Diffuse'), f'{out}/ceiling_color.jpg', (120, 112, 98), size=512, contrast=0.4)


def _rect_uv_texture(w, h, draw, mode='RGB', bg=(0, 0, 0)):
    """A canvas drawn with PIL (for textures mapped 0..1 across a face)."""
    from PIL import ImageDraw
    im = Image.new(mode, (w, h), bg); draw(im, ImageDraw.Draw(im)); return im


def seinfeld(out):
    """Jerry's apartment, 5A: honey oak strips underfoot, white walls under a mottled grey glaze, grey beadboard to the
    dado, the blue-grey couch, black-and-white flecked rugs with red borders, white kitchen tiles, the pink bathroom."""
    from PIL import ImageDraw, ImageFont
    ph = lambda i, m: os.path.join(CACHE, 'polyhaven', i, f'{m}.png')
    lin = lambda c: srgb_to_lin(np.array(c, np.float32) / 255)
    rng = np.random.default_rng(81)
    S = 2048
    # the floor: 57 mm oak strips running front to back, random lengths, each board its own tone, fine dark joints;
    # the texture spans 1.824 m (32 strips), the laminate's grain laid along the boards
    grain = _lum(ph('laminate_floor_02', 'Diffuse'), S).T; grain = (grain / grain.mean()) ** 0.8
    n = 32; sw = S // n
    col = np.zeros((S, S, 3), np.float32); h = np.ones((S, S), np.float32)
    y = np.arange(S)
    for i in range(n):
        x0 = i * sw; cuts = [int(rng.uniform(0, 1) * S)]
        while cuts[-1] < cuts[0] + S: cuts.append(cuts[-1] + int(rng.uniform(0.25, 0.65) * S))
        tone = np.zeros(S, np.float32); joint = np.zeros(S, bool)
        for a, b in zip(cuts, cuts[1:]):
            idx = np.arange(a, b) % S; tone[idx] = rng.uniform(0.86, 1.12); joint[a % S] = joint[(a + 1) % S] = True
        warm = rng.uniform(-0.05, 0.05)
        c = lin((178 + 30 * warm, 126, 74 - 40 * warm))
        col[:, x0:x0 + sw] = c[None, None] * (tone[:, None] * grain[:, x0:x0 + sw])[..., None]
        col[:, x0:x0 + 1] *= 0.42; h[:, x0:x0 + 1] = 0.0
        col[joint, x0:x0 + sw] *= 0.5; h[joint, x0:x0 + sw] = 0.2
    _save(col, f'{out}/floor_color.jpg')
    _normal_from_height(h, 1.2).resize((1024, 1024), Image.LANCZOS).save(f'{out}/floor_normal.jpg', quality=92)
    # the walls: white paint under a mottled grey-beige glaze (the set's faux finish); the band above the picture rail a
    # shade greyer; the phantom ceiling
    pl = _lum(ph('painted_plaster_wall', 'Diffuse'), S); pl = (pl / pl.mean())
    mott = 0.86 + 0.14 * _noise(S, 90, 5) + 0.06 * _noise(S, 22, 6)
    rel = pl ** 0.7 * (0.93 + 0.07 * (mott - 0.86) / 0.2)
    _save(lin((226, 222, 213))[None, None] * rel[..., None], f'{out}/wall_color.jpg')
    _save(lin((190, 186, 180))[None, None] * rel[..., None], f'{out}/band_color.jpg')
    copy(ph('painted_plaster_wall', 'nor_gl'), f'{out}/wall_normal.jpg', size=1024)
    tint(ph('white_plaster_02', 'Diffuse'), f'{out}/ceiling_color.jpg', (210, 206, 198), size=512, contrast=0.4)
    # beadboard: 76 mm boards with a bead and a V-groove at each joint, painted grey; the texture spans 8 boards
    B = 1024; x = (np.arange(B) / B * 8) % 1.0
    prof = np.clip(np.minimum(x, 1 - x) / 0.035, 0, 1) ** 0.7 - 0.25 * np.exp(-((x - 0.07) / 0.02) ** 2)
    hb = np.tile(prof[None, :], (B, 1)).astype(np.float32)
    _normal_from_height(hb, 3.0).save(f'{out}/beadboard_normal.jpg', quality=92)
    paint = (0.93 + 0.07 * _noise(B, 40, 9)) * (0.82 + 0.18 * hb)
    _save(lin((156, 153, 158))[None, None] * paint[..., None], f'{out}/beadboard_color.jpg')
    _save(lin((158, 158, 162))[None, None] * paint[..., None], f'{out}/counter_board_color.jpg')
    # the couch and the armchair: a blue-grey woven upholstery
    tint(ph('cotton_jersey', 'Diffuse'), f'{out}/couch_color.jpg', (84, 108, 116), size=1024, contrast=1.4)
    copy(ph('cotton_jersey', 'nor_gl'), f'{out}/couch_normal.jpg', size=1024)
    # the rugs (0..1 across each): a black border, a black-and-white fleck, a fine red line, the coffee table's with a
    # red field in the middle
    for name, field in (('rug_coffee', True), ('rug_dining', False)):
        R = 1024; yy, xx = np.mgrid[0:R, 0:R].astype(np.float32) / R
        d = np.minimum(np.minimum(xx, 1 - xx), np.minimum(yy, 1 - yy))
        fleck = (rng.random((R, R)) > 0.5).astype(np.float32); fleck = np.asarray(Image.fromarray((fleck * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7)), np.float32) / 255
        c = lin((210, 208, 202))[None, None] * fleck[..., None] + lin((22, 22, 24))[None, None] * (1 - fleck[..., None])
        c = np.where((d < 0.06)[..., None], lin((18, 18, 20))[None, None], c)
        c = np.where(((d > 0.135) & (d < 0.15))[..., None], lin((150, 30, 28))[None, None], c)
        if field: c = np.where((d > 0.26)[..., None], lin((128, 30, 26))[None, None] * (0.9 + 0.1 * fleck[..., None]), c)
        _save(c, f'{out}/{name}_color.jpg')
    # tiles: the kitchen's white 108 mm squares (4 x 4 per texture), the bathroom's salmon pink
    for name, base, grout in (('tile_kitchen', (226, 226, 222), (150, 150, 148)), ('tile_bath', (214, 162, 150), (190, 170, 160))):
        T = 1024; t = T // 4; yy, xx = np.mgrid[0:T, 0:T]
        g = np.minimum(np.minimum(xx % t, t - xx % t), np.minimum(yy % t, t - yy % t))
        tone = 0.95 + 0.08 * rng.random((4, 4))[yy // t, xx // t]
        grt = np.clip(1 - (g - 2.5) / 2, 0, 1)[..., None]
        _save(lin(base)[None, None] * tone[..., None] * (1 - grt) + lin(grout)[None, None] * grt, f'{out}/{name}_color.jpg')
        _normal_from_height(np.clip((g - 2) / 5, 0, 1).astype(np.float32), 1.5).save(f'{out}/{name}_normal.jpg', quality=92)
    # the fridge doors (0..1 across the pair): almond enamel under magnets, snapshots, clippings, stickers and menus
    F = _rect_uv_texture(1024, 2048, lambda im, dr: None, bg=(226, 216, 190))
    dr = ImageDraw.Draw(F)
    for k in range(140):
        cx, cy = rng.uniform(0.04, 0.96) * 1024, rng.uniform(0.12, 0.8) * 2048
        if 470 < cx < 560: continue                                   # the gap between the doors
        kind = rng.random(); w, hh = (rng.uniform(40, 150), rng.uniform(50, 200)) if kind < 0.6 else (rng.uniform(25, 60),) * 2
        colr = tuple(int(v) for v in ((rng.uniform(200, 250),) * 3 if kind < 0.35 else rng.uniform(30, 240, 3)))
        dr.rectangle([cx - w / 2, cy - hh / 2, cx + w / 2, cy + hh / 2], fill=colr)
        if kind < 0.35:
            for j in range(int(hh // 14)): dr.line([cx - w / 2 + 6, cy - hh / 2 + 8 + j * 14, cx + w / 2 - 6, cy - hh / 2 + 8 + j * 14], fill=(120, 120, 125), width=2)
    dr.rectangle([60, 900, 200, 1150], fill=(28, 28, 30))                # the ice and water dispenser in the left door
    F.save(f'{out}/fridge_color.jpg', quality=92)
    # cereal and the cupboards' contents (an atlas of 8 x 4 box fronts): bright colour fields, a band, a bowl shape
    C = _rect_uv_texture(1024, 1024, lambda im, dr: None, bg=(240, 236, 228)); dr = ImageDraw.Draw(C)
    pal = [(216, 40, 36), (250, 200, 30), (30, 90, 180), (240, 120, 30), (60, 150, 70), (245, 245, 240), (130, 60, 150), (200, 30, 90), (40, 170, 200), (230, 210, 160)]
    for i in range(8):
        for j in range(4):
            x0, y0 = i * 128, j * 256; a, b = pal[rng.integers(10)], pal[rng.integers(10)]
            dr.rectangle([x0, y0, x0 + 127, y0 + 255], fill=a)
            dr.rectangle([x0 + 8, y0 + 18, x0 + 119, y0 + 70], fill=b)
            dr.ellipse([x0 + 24, y0 + 120, x0 + 104, y0 + 200], fill=(245, 242, 235)); dr.ellipse([x0 + 34, y0 + 130, x0 + 94, y0 + 175], fill=pal[rng.integers(10)])
    C.save(f'{out}/cereal_color.jpg', quality=92)
    # spines (books, VHS boxes, board games): 64 vertical spines across, two rows
    P = _rect_uv_texture(2048, 1024, lambda im, dr: None, bg=(20, 20, 22)); dr = ImageDraw.Draw(P)
    for r in range(2):
        for i in range(64):
            x0 = i * 32; vhs = r == 1
            c = (18, 18, 20) if vhs and rng.random() < 0.7 else tuple(int(v) for v in rng.uniform(40, 230, 3))
            dr.rectangle([x0 + 1, r * 512, x0 + 30, r * 512 + 511], fill=c)
            band = (235, 235, 230) if vhs else tuple(int(v) for v in rng.uniform(160, 250, 3))
            dr.rectangle([x0 + 4, r * 512 + 140, x0 + 27, r * 512 + 330], fill=band)
    P.save(f'{out}/spines_color.jpg', quality=92)
    # pictures on the walls (originals in the manner of the set's): a silver racer on a mountain road under a dark title
    # band; a pop city of coloured blocks; framed photographs in black and white
    W_, H_ = 1024, 1300
    p1 = _rect_uv_texture(W_, H_, lambda im, dr: None, bg=(236, 232, 222)); dr = ImageDraw.Draw(p1)
    dr.rectangle([90, 90, W_ - 90, 1000], fill=(150, 160, 170))
    dr.polygon([(90, 560), (300, 300), (520, 470), (760, 260), (W_ - 90, 520), (W_ - 90, 1000), (90, 1000)], fill=(110, 92, 70))
    dr.polygon([(90, 1000), (420, 640), (600, 640), (W_ - 90, 1000)], fill=(150, 120, 90))
    dr.ellipse([300, 690, 700, 900], fill=(205, 208, 212)); dr.ellipse([330, 700, 660, 800], fill=(225, 228, 232))
    for cx in (390, 620): dr.ellipse([cx - 45, 820, cx + 45, 910], fill=(28, 28, 30))
    dr.ellipse([720, 700, 900, 820], fill=(178, 34, 30))
    dr.rectangle([90, 1040, W_ - 90, 1180], fill=(26, 26, 30))
    p1.save(f'{out}/poster_racer.jpg', quality=92)
    p2 = _rect_uv_texture(1024, 1300, lambda im, dr: None, bg=(250, 246, 236)); dr = ImageDraw.Draw(p2)
    for k in range(60):
        x0, w = rng.uniform(60, 900), rng.uniform(60, 180); y1 = rng.uniform(500, 1200); hh = rng.uniform(150, 600)
        dr.rectangle([x0, y1 - hh, x0 + w, y1], fill=pal[rng.integers(10)], outline=(20, 20, 20), width=6)
        for j in range(int(hh // 50)): dr.rectangle([x0 + 15, y1 - hh + 20 + j * 50, x0 + 35, y1 - hh + 40 + j * 50], fill=(250, 240, 120))
    dr.rectangle([0, 1200, 1024, 1300], fill=(60, 140, 60))
    p2.save(f'{out}/poster_city.jpg', quality=92)
    for k in range(3):
        g = (_noise(512, 18 + 10 * k, 60 + k) * 0.7 + 0.15 + 0.15 * _noise(512, 3, 70 + k)) * 255
        Image.fromarray(np.dstack([g * 0.98, g * 0.98, g * 0.95]).astype(np.uint8)).save(f'{out}/photo{k}.jpg', quality=90)
    # magazines on the coffee table (an atlas of 4 x 2 covers): a photograph, a masthead band, a few lines
    G = _rect_uv_texture(1024, 1024, lambda im, dr: None, bg=(236, 232, 224)); dr = ImageDraw.Draw(G)
    for i in range(4):
        for j in range(2):
            x0, y0 = i * 256, j * 512; c = pal[rng.integers(10)]
            dr.rectangle([x0 + 10, y0 + 90, x0 + 245, y0 + 430], fill=tuple(int(v * 0.7 + 60) for v in c))
            dr.ellipse([x0 + 60, y0 + 160, x0 + 190, y0 + 330], fill=tuple(int(v) for v in rng.uniform(120, 230, 3)))
            dr.rectangle([x0 + 10, y0 + 18, x0 + 245, y0 + 78], fill=(200, 30, 30) if j else (20, 20, 24))
            for k in range(3): dr.rectangle([x0 + 20, y0 + 445 + k * 18, x0 + 200 - 30 * k, y0 + 455 + k * 18], fill=(60, 60, 64))
    G.save(f'{out}/magazine_color.jpg', quality=92)
    # the door's number, and the bathroom's window view (a sunlit brick building across the way, soft)
    f = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 300) if os.path.exists('C:/Windows/Fonts/arialbd.ttf') else ImageFont.load_default()
    num = Image.new('RGB', (512, 320), (236, 230, 214)); ImageDraw.Draw(num).text((256, 160), '5A', fill=(30, 28, 26), font=f, anchor='mm')
    num.save(f'{out}/door_5a.jpg', quality=92)
    num = Image.new('RGB', (512, 320), (236, 230, 214)); ImageDraw.Draw(num).text((256, 160), '5B', fill=(30, 28, 26), font=f, anchor='mm')
    num.save(f'{out}/door_5b.jpg', quality=92)
    V = 1024; yy, xx = np.mgrid[0:V, 0:V].astype(np.float32) / V
    brick = ((yy * 40) % 1 > 0.1) & (((xx * 14 + 0.5 * np.floor(yy * 40)) % 1) > 0.06)
    v = np.where(brick[..., None], lin((170, 96, 70)), lin((200, 188, 170))) * (0.85 + 0.3 * _noise(V, 30, 77))[..., None]
    win = (((xx * 4) % 1 > 0.25) & ((xx * 4) % 1 < 0.75) & ((yy * 3) % 1 > 0.2) & ((yy * 3) % 1 < 0.8))
    v = np.where(win[..., None], lin((70, 80, 92)), v)
    _save(v * 1.4, f'{out}/view_color.jpg')


def the_sopranos(out):
    """Dr. Melfi's office: sapele veneer gone warm red-brown, a grey-green loop carpet, the big rug's beige basketweave
    with its key border, olive chenille, celadon wool, the chaise's dark leather, the rosewood desk; the waiting room's
    speckled floor; the summer trees behind the blinds; diplomas, a botanical print, books."""
    import math
    from PIL import ImageDraw
    ph = lambda i, m: os.path.join(CACHE, 'polyhaven', i, f'{m}.png')
    acg = lambda i, m: os.path.join(CACHE, 'ambientcg', i, f'{i}_2K-JPG_{m}.jpg')
    lin = lambda c: srgb_to_lin(np.array(c, np.float32) / 255)
    rng = np.random.default_rng(99)
    S = 2048
    # the veneer: sapele's straight grain, warmed and darkened to the set's red-brown, a little figure across it
    v = _lum(ph('sapele_veneer', 'Diffuse'), S); v = (v / v.mean()) ** 1.25
    fig = 0.94 + 0.12 * _noise(S, 70, 3)
    _save(lin((118, 72, 46))[None, None] * (v * fig)[..., None], f'{out}/veneer_color.jpg')
    copy(ph('sapele_veneer', 'nor_gl'), f'{out}/veneer_normal.jpg', size=1024)
    copy(ph('sapele_veneer', 'Rough'), f'{out}/veneer_rough.jpg', size=1024, mode='L')
    # the door and the shelves' faces: the same veneer, a shade lighter (honey, as the door reads)
    _save(lin((140, 92, 58))[None, None] * (v * fig)[..., None], f'{out}/veneer_light_color.jpg')
    # the desk and the credenza: dark figured rosewood
    tint(ph('rosewood_veneer1', 'Diffuse'), f'{out}/rosewood_color.jpg', (66, 32, 22), size=1024, contrast=1.15)
    # the floor: a grey-green loop carpet, wall to wall
    tint(acg('Carpet012', 'Color'), f'{out}/carpet_color.jpg', (104, 106, 90), contrast=0.7)
    copy(acg('Carpet012', 'NormalGL'), f'{out}/carpet_normal.jpg', size=1024)
    # Tony's chair: olive chenille (the velour's nap); Melfi's: celadon-grey wool
    tint(ph('velour_velvet', 'Diffuse'), f'{out}/chenille_color.jpg', (92, 90, 62), size=1024, contrast=1.3)
    copy(ph('velour_velvet', 'nor_gl'), f'{out}/chenille_normal.jpg', size=1024)
    tint(ph('poly_wool_herringbone', 'Diffuse'), f'{out}/celadon_color.jpg', (148, 156, 140), size=1024, contrast=0.9)
    copy(ph('poly_wool_herringbone', 'nor_gl'), f'{out}/celadon_normal.jpg', size=1024)
    # the chaise: dark olive-brown leather
    tint(ph('brown_leather', 'Diffuse'), f'{out}/leather_color.jpg', (52, 46, 36), size=1024, contrast=1.2)
    copy(ph('brown_leather', 'nor_gl'), f'{out}/leather_normal.jpg', size=1024)
    # the waiting room's armchair: an oatmeal boucle (the waffle's weave)
    tint(ph('waffle_pique_cotton', 'Diffuse'), f'{out}/boucle_color.jpg', (176, 168, 150), size=1024, contrast=1.6)
    copy(ph('waffle_pique_cotton', 'nor_gl'), f'{out}/boucle_normal.jpg', size=1024)
    # the big rug (0..1 across it, 3.6 x 2.7 m): a beige basketweave field, a taupe key border between two fine lines
    R = 2048; yy, xx = np.mgrid[0:R, 0:R].astype(np.float32) / R
    weave = _lum(ph('waffle_pique_cotton', 'Diffuse'), 512); weave = np.tile((weave / weave.mean()) ** 1.4, (4, 4))
    field = lin((188, 172, 142))[None, None] * weave[..., None] * (0.95 + 0.08 * _noise(R, 120, 11))[..., None]
    du, dv = np.minimum(xx, 1 - xx) * 3.6, np.minimum(yy, 1 - yy) * 2.7          # metres to the nearest edge
    d = np.minimum(du, dv)
    band = (d > 0.1) & (d < 0.3)
    # the key: a meander along the band (s along the edge, t across it), 0.2 m per repeat
    s = np.where(du < dv, yy * 2.7, xx * 3.6); t = (d - 0.1) / 0.2
    f = (s / 0.2) % 1
    key = ((t < 0.18) | (t > 0.82) | ((f < 0.16) & (t < 0.82)) | ((f > 0.16) & (f < 0.66) & (t > 0.64) & (t < 0.82)) |
           ((f > 0.5) & (f < 0.66) & (t > 0.34) & (t < 0.82)) | ((f > 0.32) & (f < 0.66) & (t > 0.34) & (t < 0.5)))
    border = np.where((band & key)[..., None], lin((118, 100, 80))[None, None] * weave[..., None], field)
    lines = (np.abs(d - 0.06) < 0.008) | (np.abs(d - 0.34) < 0.006)
    border = np.where(lines[..., None], lin((118, 100, 80))[None, None], border)
    _save(np.where((d < 0.035)[..., None], lin((150, 134, 108))[None, None] * weave[..., None], border), f'{out}/rug_color.jpg')
    # the waiting room's floor: a grey speckled terrazzo-like vinyl
    sp = rng.random((S, S)).astype(np.float32)
    speck = (sp > 0.985).astype(np.float32) * 0.55 + (sp < 0.02).astype(np.float32) * -0.4
    speck = np.asarray(Image.fromarray(((speck + 0.5) * 255).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255 - 0.5
    _save(lin((150, 148, 140))[None, None] * (1 + 1.2 * speck + 0.05 * _noise(S, 80, 12))[..., None], f'{out}/terrazzo_color.jpg')
    # the view: summer woods close behind the building, out of focus (trunks, green, bright gaps)
    V = 1024; yy, xx = np.mgrid[0:V, 0:V].astype(np.float32) / V
    leaf = 0.4 * _noise(V, 10, 21) + 0.35 * _noise(V, 30, 22) + 0.25 * _noise(V, 4, 23)
    view = lin((96, 140, 70))[None, None] * (0.55 + 0.9 * leaf)[..., None]
    gaps = np.clip((leaf - 0.6) * 4, 0, 1)
    view = view * (1 - gaps[..., None]) + lin((222, 230, 214))[None, None] * gaps[..., None]
    for k in range(9):
        x0 = rng.uniform(0.02, 0.98); w = rng.uniform(0.012, 0.035)
        trunk = np.exp(-((xx - x0 - 0.02 * np.sin(yy * 6 + k)) / w) ** 4) * np.clip((yy - rng.uniform(0.0, 0.4)) * 4, 0, 1)
        view = view * (1 - trunk[..., None]) + lin((58, 50, 40))[None, None] * trunk[..., None]
    view = np.asarray(Image.fromarray((lin_to_srgb(view) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5)), np.float32) / 255
    Image.fromarray((view * 255).clip(0, 255).astype(np.uint8)).save(f'{out}/view_color.jpg', quality=92)
    # diplomas (0..1 across each): cream paper, a black-letter heading, lines, a gold seal, in a thin black frame
    for k in range(2):
        D_ = _rect_uv_texture(1024, 800, lambda im, dr: None, bg=(232, 224, 204)); dr = ImageDraw.Draw(D_)
        dr.rectangle([10, 10, 1013, 789], outline=(20, 18, 16), width=22)
        dr.rectangle([70, 70, 953, 729], outline=(150, 130, 90), width=3)
        dr.rectangle([220, 130, 804, 190], fill=(40, 34, 30))
        for j in range(7): dr.rectangle([180 + 20 * (j % 2), 250 + j * 46, 844 - 20 * (j % 2), 262 + j * 46], fill=(90, 84, 78))
        dr.ellipse([440, 590, 580, 730] if k else [130, 590, 270, 730], fill=(190, 150, 60), outline=(120, 90, 30), width=6)
        D_.save(f'{out}/diploma{k}.jpg', quality=92)
    # the botanical print: a white mat, a faint sepia drawing of a leafy stem
    P = _rect_uv_texture(900, 1100, lambda im, dr: None, bg=(236, 232, 222)); dr = ImageDraw.Draw(P)
    dr.rectangle([150, 160, 750, 940], fill=(228, 220, 200))
    pts = [(450 + 30 * math.sin(i / 9), 900 - i * 6) for i in range(120)]
    dr.line(pts, fill=(120, 96, 70), width=5)
    for i in range(8, 120, 13):
        x, y = pts[i]; sd = 1 if (i // 13) % 2 else -1
        dr.ellipse([x + (10 if sd > 0 else -150), y - 40, x + (150 if sd > 0 else -10), y + 10], outline=(130, 104, 76), width=4)
    P.save(f'{out}/botanical.jpg', quality=92)
    # books: 64 spines across in two rows (medical and analytic texts: dark cloth, gilt bands, white paperbacks)
    B = _rect_uv_texture(2048, 1024, lambda im, dr: None, bg=(20, 18, 16)); dr = ImageDraw.Draw(B)
    pal = [(70, 22, 22), (24, 40, 30), (24, 30, 56), (120, 96, 60), (210, 204, 190), (40, 36, 34), (150, 40, 30), (90, 70, 50), (200, 170, 110), (60, 80, 90)]
    for r in range(2):
        for i in range(64):
            x0 = i * 32; c = pal[rng.integers(len(pal))]; c = tuple(int(np.clip(v * rng.uniform(0.85, 1.15), 0, 255)) for v in c)
            dr.rectangle([x0 + 1, r * 512, x0 + 30, r * 512 + 511], fill=c)
            g = (200, 170, 90) if sum(c) < 300 else (40, 36, 34)
            for zb in (60, 440): dr.rectangle([x0 + 3, r * 512 + zb, x0 + 28, r * 512 + zb + 8], fill=g)
            dr.rectangle([x0 + 9, r * 512 + 120, x0 + 22, r * 512 + 300], fill=g)
    B.save(f'{out}/spines_color.jpg', quality=92)
    # magazines in the waiting room (an atlas of 4 x 2 covers)
    G = _rect_uv_texture(1024, 1024, lambda im, dr: None, bg=(236, 232, 224)); dr = ImageDraw.Draw(G)
    for i in range(4):
        for j in range(2):
            x0, y0 = i * 256, j * 512; c = pal[rng.integers(len(pal))]
            dr.rectangle([x0 + 10, y0 + 90, x0 + 245, y0 + 430], fill=tuple(int(v * 0.6 + 80) for v in c))
            dr.ellipse([x0 + 60, y0 + 160, x0 + 190, y0 + 330], fill=tuple(int(v) for v in rng.uniform(120, 230, 3)))
            dr.rectangle([x0 + 10, y0 + 18, x0 + 245, y0 + 78], fill=(190, 30, 30) if (i + j) % 2 else (20, 20, 24))
    G.save(f'{out}/magazine_color.jpg', quality=92)
    # the statue's bronze: a green patina, darker in the hollows (a noise the lightmap does not carry)
    pat = 0.7 + 0.5 * _noise(1024, 16, 31) + 0.2 * _noise(1024, 3, 32)
    _save(lin((62, 96, 84))[None, None] * pat[..., None], f'{out}/patina_color.jpg')
    # linen for the drum shades; the phantom ceiling
    tint(ph('rough_linen', 'Diffuse'), f'{out}/linen_color.jpg', (226, 214, 188), size=512, contrast=0.8)
    tint(ph('white_plaster_02', 'Diffuse'), f'{out}/ceiling_color.jpg', (214, 210, 200), size=512, contrast=0.4)


def breaking_bad(out):
    """Saul Goodman's office: a royal blue carpet, pale sage walls over an olive dado, the Constitution's first page as
    the bay's wallpaper (amber parchment), honey oak, oxblood and khaki and coral leathers, the gold damask sofa, red
    law books; the waiting room's beige tile and yellow walls, the parking lot behind the blinds seen through the
    lettered glass; framed photographs, the diploma, magazines."""
    import math
    from PIL import ImageDraw, ImageFont
    ph = lambda i, m: os.path.join(CACHE, 'polyhaven', i, f'{m}.png')
    acg = lambda i, m: os.path.join(CACHE, 'ambientcg', i, f'{i}_2K-JPG_{m}.jpg')
    lin = lambda c: srgb_to_lin(np.array(c, np.float32) / 255)
    rng = np.random.default_rng(57)
    S = 2048
    font = lambda name, size: ImageFont.truetype(f'C:/Windows/Fonts/{name}', size) if os.path.exists(f'C:/Windows/Fonts/{name}') else ImageFont.load_default()
    # the carpet: a dense royal blue loop pile, wall to wall
    tint(acg('Carpet012', 'Color'), f'{out}/carpet_color.jpg', (30, 46, 116), size=1024, contrast=0.75)
    copy(acg('Carpet012', 'NormalGL'), f'{out}/carpet_normal.jpg', size=1024)
    # the office's walls: flat paint over plaster, pale sage above, a dark olive dado below; the waiting room's warm yellow
    pl = _lum(ph('painted_plaster_wall', 'Diffuse'), 1024); pl = (pl / pl.mean()) ** 0.3
    mott = 0.95 + 0.05 * _noise(1024, 60, 5)
    for name, c in (('wall', (164, 166, 124)), ('dado', (86, 82, 50)), ('wait_wall', (210, 184, 128)), ('booth_wall', (196, 186, 160))):
        _save(lin(c)[None, None] * (pl * mott)[..., None], f'{out}/{name}_color.jpg')
    copy(ph('painted_plaster_wall', 'nor_gl'), f'{out}/wall_normal.jpg', size=1024)
    tint(ph('white_plaster_02', 'Diffuse'), f'{out}/ceiling_color.jpg', (220, 218, 210), size=512, contrast=0.4)
    # the Constitution: the National Archives' scan of page one, its parchment warmed to the set's amber; the margins trimmed
    C = Image.open(os.path.join(CACHE, 'commons', 'constitution_page1.jpg')).convert('RGB')
    w, h = C.size; C = C.crop((int(w * 0.035), int(h * 0.02), int(w * 0.975), int(h * 0.985))).resize((2048, 2560), Image.LANCZOS)
    c = srgb_to_lin(np.asarray(C, np.float32) / 255); l = c @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    paper = np.clip(l / np.percentile(l, 70), 0, 1.15)
    ink = np.clip(1 - paper, 0, 1) ** 0.8
    age = 0.88 + 0.16 * _noise(2048, 90, 41); age = np.vstack([age, age[:512]])     # the page is taller than square
    parch = lin((232, 192, 118))[None, None] * (paper ** 0.5 * age)[..., None]
    con = parch * (1 - ink[..., None]) + lin((70, 42, 22))[None, None] * ink[..., None]
    _save(con, f'{out}/constitution_color.jpg')
    # the desk and the second desk: honey oak, open-grained; the door and casings: dark stained walnut
    tint(ph('rosewood_veneer1', 'Diffuse'), f'{out}/oak_color.jpg', (128, 82, 44), size=1024, contrast=1.25)
    tint(ph('sapele_veneer', 'Diffuse'), f'{out}/walnut_color.jpg', (58, 34, 22), size=1024, contrast=1.15)
    copy(ph('sapele_veneer', 'nor_gl'), f'{out}/wood_normal.jpg', size=1024)
    # leathers: Saul's oxblood chair, the khaki-olive client chairs, the coral tub chairs
    tint(ph('leather_red_03', 'Diffuse'), f'{out}/oxblood_color.jpg', (78, 20, 18), size=1024, contrast=1.15)
    copy(ph('leather_red_03', 'nor_gl'), f'{out}/oxblood_normal.jpg', size=1024)
    tint(ph('brown_leather', 'Diffuse'), f'{out}/khaki_color.jpg', (124, 112, 76), size=1024, contrast=1.1)
    copy(ph('brown_leather', 'nor_gl'), f'{out}/khaki_normal.jpg', size=1024)
    tint(ph('leather_red_02', 'Diffuse'), f'{out}/coral_color.jpg', (190, 84, 70), size=1024, contrast=0.9)
    copy(ph('leather_red_02', 'nor_gl'), f'{out}/coral_normal.jpg', size=1024)
    # the sofa: a gold-brown damask (the jacquard's flowers, warmed, their contrast raised)
    tint(ph('floral_jacquard', 'Diffuse'), f'{out}/damask_color.jpg', (162, 120, 62), size=1024, contrast=1.6)
    copy(ph('floral_jacquard', 'nor_gl'), f'{out}/damask_normal.jpg', size=1024)
    # the waiting room: beige ceramic tile; its chairs' burgundy vinyl
    tint(ph('large_floor_tiles_02', 'Diffuse'), f'{out}/tile_color.jpg', (196, 178, 150), size=1024, contrast=0.8)
    copy(ph('large_floor_tiles_02', 'nor_gl'), f'{out}/tile_normal.jpg', size=1024)
    tint(ph('velour_velvet', 'Diffuse'), f'{out}/vinyl_color.jpg', (96, 26, 30), size=512, contrast=0.5)
    # law books: 64 spines across in two rows, red and oxblood buckram with black labels and gilt bands, some green,
    # some tan calf (the reporters), a few white binders
    B = _rect_uv_texture(2048, 1024, lambda im, dr: None, bg=(20, 16, 14)); dr = ImageDraw.Draw(B)
    pal = [(150, 26, 22), (128, 20, 20), (170, 40, 30), (110, 18, 16), (24, 64, 40), (176, 132, 80), (150, 26, 22), (128, 20, 20), (220, 214, 200), (60, 24, 20)]
    for r in range(2):
        for i in range(64):
            x0 = i * 32; c = pal[rng.integers(len(pal))]; c = tuple(int(np.clip(v * rng.uniform(0.85, 1.12), 0, 255)) for v in c)
            dr.rectangle([x0 + 1, r * 512, x0 + 30, r * 512 + 511], fill=c)
            if sum(c) > 500: continue
            g = (206, 172, 92)
            for zb in (50, 70, 430, 450): dr.rectangle([x0 + 3, r * 512 + zb, x0 + 28, r * 512 + zb + 6], fill=g)
            dr.rectangle([x0 + 6, r * 512 + 130, x0 + 25, r * 512 + 200], fill=(18, 16, 14)); dr.rectangle([x0 + 6, r * 512 + 260, x0 + 25, r * 512 + 300], fill=(18, 16, 14))
            dr.rectangle([x0 + 9, r * 512 + 145, x0 + 22, r * 512 + 150], fill=g); dr.rectangle([x0 + 9, r * 512 + 160, x0 + 22, r * 512 + 164], fill=g)
    B.save(f'{out}/lawbooks_color.jpg', quality=92)
    # the file boxes' fronts (white, a hand hole, a label); the diploma (University of American Samoa, in a gilt frame)
    F = _rect_uv_texture(512, 320, lambda im, dr: None, bg=(232, 230, 222)); dr = ImageDraw.Draw(F)
    dr.rounded_rectangle([196, 40, 316, 80], 18, fill=(60, 58, 54)); dr.rectangle([120, 140, 392, 230], outline=(140, 136, 130), width=4)
    for j in range(3): dr.rectangle([140, 160 + j * 22, 360 - 40 * j, 168 + j * 22], fill=(70, 70, 76))
    F.save(f'{out}/filebox_color.jpg', quality=92)
    D_ = _rect_uv_texture(1024, 800, lambda im, dr: None, bg=(236, 228, 206)); dr = ImageDraw.Draw(D_)
    dr.rectangle([60, 60, 963, 739], outline=(150, 120, 60), width=4)
    dr.text((512, 170), 'University of American Samoa', fill=(30, 26, 22), font=font('timesbd.ttf', 58), anchor='mm')
    dr.text((512, 270), 'Saul Goodman', fill=(30, 26, 22), font=font('timesi.ttf', 64), anchor='mm')
    dr.text((512, 350), 'Juris Doctor', fill=(40, 36, 30), font=font('times.ttf', 44), anchor='mm')
    for j in range(4): dr.rectangle([220 + 30 * (j % 2), 420 + j * 34, 804 - 30 * (j % 2), 428 + j * 34], fill=(110, 100, 88))
    dr.ellipse([440, 580, 584, 724], fill=(196, 40, 36), outline=(150, 20, 20), width=6)
    D_.save(f'{out}/diploma.jpg', quality=92)
    # photographs of Saul with people (soft, warm colour snapshots); the landscape over the sofa (a desert mesa at dusk)
    for k in range(4):
        P = np.zeros((512, 640, 3), np.float32); yy, xx = np.mgrid[0:512, 0:640].astype(np.float32)
        P[:] = lin(tuple(int(v) for v in rng.uniform(60, 160, 3)))[None, None] * (0.8 + 0.4 * _noise(640, 60, 80 + k)[:512, :640])[..., None]
        for j, cx in enumerate((230, 410)):
            body = (((xx - cx) / 90) ** 2 + ((yy - 470) / 220) ** 2) < 1; head = (((xx - cx) / 42) ** 2 + ((yy - 200) / 52) ** 2) < 1
            P[body] = lin((36, 34, 40) if j else tuple(int(v) for v in rng.uniform(40, 200, 3)))
            P[head] = lin((214, 168, 140)) * (0.9 + 0.2 * j)
        P = np.asarray(Image.fromarray((lin_to_srgb(P) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4)))
        Image.fromarray(P).save(f'{out}/photo{k}.jpg', quality=90)
    V = 1024; yy, xx = np.mgrid[0:V, 0:V].astype(np.float32) / V
    land = np.where((yy < 0.55)[..., None], lin((230, 150, 90)) * (1 - 0.6 * yy[..., None]), lin((120, 70, 40)) * (0.8 + 0.3 * _noise(V, 30, 51)[..., None]))
    mesa = (yy > 0.4 - 0.12 * ((xx > 0.25) & (xx < 0.7))) & (yy < 0.56)
    land = np.where(mesa[..., None], lin((96, 48, 36)), land)
    _save(land, f'{out}/landscape.jpg')
    # the storefront seen from inside: the parking lot in hard Albuquerque sun beyond the glass, the Sandias on the
    # horizon, out of focus; on the glass, the red lettering read backwards (SAUL GOODMAN / ATTORNEY AT LAW)
    W_, H_ = 2048, 1024; yy, xx = np.mgrid[0:H_, 0:W_].astype(np.float32); yy /= H_; xx /= W_
    sky = lin((150, 186, 226)) * (1 - 0.4 * yy[..., None]) + lin((230, 236, 240)) * 0.4 * yy[..., None]
    mtn = yy > 0.34 - 0.06 * np.sin(xx * 5.3 + 1) - 0.03 * np.sin(xx * 13)
    view = np.where(mtn[..., None], lin((120, 116, 128)), sky)
    lot = yy > 0.5
    view = np.where(lot[..., None], lin((118, 112, 104)) * (0.9 + 0.2 * _noise(W_, 20, 61)[:H_, :W_])[..., None], view)
    for k in range(9):   # parked cars, bright bodies and dark glass
        x0 = rng.uniform(0.0, 0.92); cw = rng.uniform(0.07, 0.1)
        car = (xx > x0) & (xx < x0 + cw) & (yy > 0.56) & (yy < 0.7)
        view = np.where(car[..., None], lin(tuple(int(v) for v in rng.uniform(60, 240, 3))), view)
        view = np.where((car & (yy < 0.62) & (xx > x0 + cw * 0.15) & (xx < x0 + cw * 0.85))[..., None], lin((40, 46, 52)), view)
    view = np.asarray(Image.fromarray((lin_to_srgb(view) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(10)))
    I = Image.fromarray(view); dr = ImageDraw.Draw(I)
    txt = Image.new('RGBA', (W_, H_), (0, 0, 0, 0)); dt = ImageDraw.Draw(txt)
    dt.text((W_ / 2, H_ * 0.47), 'SAUL GOODMAN', fill=(200, 28, 26, 255), font=font('arialbd.ttf', 230), anchor='mm', stroke_width=8, stroke_fill=(250, 250, 246, 255))
    dt.text((W_ / 2, H_ * 0.68), 'ATTORNEY AT LAW', fill=(250, 250, 246, 255), font=font('arialbd.ttf', 120), anchor='mm', stroke_width=5, stroke_fill=(200, 28, 26, 255))
    dt.text((W_ / 2, H_ * 0.82), '(505) 165-CALL', fill=(200, 28, 26, 255), font=font('arialbd.ttf', 80), anchor='mm')
    txt = txt.transpose(Image.FLIP_LEFT_RIGHT)                       # read from inside, backwards
    I.paste(txt, (0, 0), txt); I.save(f'{out}/storefront_view.jpg', quality=92)
    # the brass plaque by the door; Francesca's monitor; magazines
    Pq = _rect_uv_texture(512, 256, lambda im, dr: None, bg=(176, 140, 64)); dr = ImageDraw.Draw(Pq)
    dr.rectangle([10, 10, 501, 245], outline=(110, 84, 30), width=8)
    dr.text((256, 100), 'SAUL GOODMAN', fill=(40, 30, 14), font=font('timesbd.ttf', 56), anchor='mm')
    dr.text((256, 170), '& ASSOCIATES', fill=(40, 30, 14), font=font('timesbd.ttf', 40), anchor='mm')
    Pq.save(f'{out}/plaque.jpg', quality=92)
    Mn = _rect_uv_texture(512, 384, lambda im, dr: None, bg=(30, 70, 150)); dr = ImageDraw.Draw(Mn)
    dr.rectangle([0, 360, 512, 384], fill=(200, 200, 204)); dr.rectangle([40, 60, 300, 300], fill=(236, 236, 240))
    for j in range(8): dr.rectangle([60, 80 + j * 26, 280 - 20 * (j % 3), 92 + j * 26], fill=(80, 80, 90))
    Mn.save(f'{out}/monitor.jpg', quality=92)
    G = _rect_uv_texture(1024, 1024, lambda im, dr: None, bg=(236, 232, 224)); dr = ImageDraw.Draw(G)
    mp = [(190, 40, 40), (30, 60, 140), (240, 200, 60), (40, 120, 70), (20, 20, 24), (220, 110, 40)]
    for i in range(4):
        for j in range(2):
            x0, y0 = i * 256, j * 512; c = mp[rng.integers(len(mp))]
            dr.rectangle([x0 + 10, y0 + 90, x0 + 245, y0 + 430], fill=tuple(int(v * 0.6 + 80) for v in c))
            dr.ellipse([x0 + 60, y0 + 160, x0 + 190, y0 + 330], fill=tuple(int(v) for v in rng.uniform(120, 230, 3)))
            dr.rectangle([x0 + 10, y0 + 18, x0 + 245, y0 + 78], fill=mp[rng.integers(len(mp))])
    G.save(f'{out}/magazine_color.jpg', quality=92)
    # the bronze (Lady Justice, the scales, the lamps' brass) carries no texture; linen for the lamp shades
    tint(ph('rough_linen', 'Diffuse'), f'{out}/linen_color.jpg', (232, 220, 192), size=512, contrast=0.8)


def the_godfather(out):
    """Don Corleone's study on the wedding day: dark-stained boards, mahogany panelling and the carved desk, dusty
    rose damask above the wainscot, the olive-gold leather of the Don's chair and the black of the others, the Persian
    vase carpet; books, the family's photographs on the mantel, the crest-framed print; the hall's cream paper with red
    sprays and its red runner; the garden in the sun, beyond the shutters and the glass of the front door."""
    import math
    from PIL import ImageDraw
    ph = lambda i, m: os.path.join(CACHE, 'polyhaven', i, f'{m}.png')
    lin = lambda c: srgb_to_lin(np.array(c, np.float32) / 255)
    rng = np.random.default_rng(72)
    # the floor: narrow boards stained almost black-brown, waxed
    tint(ph('wooden_floor_02', 'Diffuse'), f'{out}/floor_color.jpg', (62, 40, 26), size=2048, contrast=1.15)
    copy(ph('wooden_floor_02', 'nor_gl'), f'{out}/floor_normal.jpg', size=1024)
    # panelling, shutters, casings and the hall's wainscot: dark lacquered mahogany; the desk a redder, figured mahogany
    tint(ph('lacquered_cherry_wood', 'Diffuse'), f'{out}/panel_color.jpg', (54, 30, 20), size=1024, contrast=1.2)
    copy(ph('lacquered_cherry_wood', 'nor_gl'), f'{out}/panel_normal.jpg', size=1024)
    tint(ph('rosewood_veneer1', 'Diffuse'), f'{out}/mahogany_color.jpg', (74, 36, 22), size=1024, contrast=1.3)
    copy(ph('sapele_veneer', 'nor_gl'), f'{out}/wood_normal.jpg', size=1024)
    # the damask paper above the wainscot: the jacquard's flowers on a dusty rose ground
    d = np.asarray(Image.open(ph('floral_jacquard', 'Diffuse')).convert('RGB'), np.float32) / 255
    h, w = d.shape[:2]; d = d[:, :min(w, h)] if w > h else d[:w]                     # a square, whole repeat
    dl = srgb_to_lin(d) @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    rel = np.asarray(Image.fromarray(((dl / dl.max()) * 255).astype(np.uint8)).resize((1024, 1024), Image.LANCZOS), np.float32) / 255
    rel = (rel / rel.mean()) ** 1.5
    mott = 0.94 + 0.08 * _noise(1024, 70, 9)
    _save(lin((176, 120, 106))[None, None] * (0.78 + 0.22 * rel * mott)[..., None], f'{out}/damask_color.jpg')
    # leathers: the Don's chair olive-gold, the club chair and the chesterfield black, the side chairs' seats brown
    tint(ph('leather_white', 'Diffuse'), f'{out}/olive_leather_color.jpg', (92, 80, 46), size=1024, contrast=1.3)
    copy(ph('leather_white', 'nor_gl'), f'{out}/olive_leather_normal.jpg', size=1024)
    tint(ph('brown_leather', 'Diffuse'), f'{out}/black_leather_color.jpg', (22, 20, 19), size=1024, contrast=1.1)
    copy(ph('brown_leather', 'nor_gl'), f'{out}/leather_normal.jpg', size=1024)
    tint(ph('brown_leather', 'Diffuse'), f'{out}/brown_leather_color.jpg', (72, 40, 24), size=1024, contrast=1.1)
    # the carpet: the Met's 17th-century vase carpet, its margin trimmed, a shade darker under the Don's low light
    C = Image.open(os.path.join(CACHE, 'met', 'vase_carpet.jpg')).convert('RGB')
    a = np.asarray(C, np.float32) / 255; m = a.mean(-1) < 0.55                        # the rug, not the photo's grey ground
    rows, cols = np.where(m.mean(1) > 0.6)[0], np.where(m.mean(0) > 0.6)[0]
    iw, ih = (cols.max() - cols.min()) * 0.015, (rows.max() - rows.min()) * 0.012   # the photo is a little askew: inset
    C = C.crop((int(cols.min() + iw), int(rows.min() + ih), int(cols.max() - iw), int(rows.max() - ih)))
    C = C.resize((1236, 2048), Image.LANCZOS).transpose(Image.ROTATE_90)            # long side across the room
    c = srgb_to_lin(np.asarray(C, np.float32) / 255) * 0.82
    _save(c, f'{out}/rug_color.jpg')
    copy(ph('velour_velvet', 'nor_gl'), f'{out}/pile_normal.jpg', size=512)
    # the hall: a cream paper with sprays of red flowers and green leaves (as on the stair), its red velvet runner
    S = 1024; P = np.ones((S, S, 3), np.float32) * lin((214, 196, 160))[None, None] * (0.94 + 0.08 * _noise(S, 40, 3))[..., None]
    I = Image.fromarray((lin_to_srgb(P) * 255).astype(np.uint8)); dr = ImageDraw.Draw(I)
    for j in range(4):
        for i in range(4):
            cx, cy = (i + 0.5 + 0.5 * (j % 2)) * S / 4 % S, (j + 0.5) * S / 4
            for k in range(7):                                                        # leaves round the spray
                a_ = k * 0.9 + j; lx, ly = cx + 34 * math.cos(a_), cy + 30 * math.sin(a_)
                dr.ellipse([lx - 14, ly - 6, lx + 14, ly + 6], fill=(92, 112, 64))
            for k in range(5):                                                        # the blooms
                bx, by = cx + rng.uniform(-22, 22), cy + rng.uniform(-18, 18); r = rng.uniform(9, 14)
                dr.ellipse([bx - r, by - r, bx + r, by + r], fill=(176, 52, 38)); dr.ellipse([bx - r / 3, by - r / 3, bx + r / 3, by + r / 3], fill=(120, 30, 24))
    I.save(f'{out}/hall_paper_color.jpg', quality=92)
    tint(ph('velour_velvet', 'Diffuse'), f'{out}/runner_color.jpg', (104, 22, 24), size=512, contrast=0.6)
    tint(ph('white_plaster_02', 'Diffuse'), f'{out}/ceiling_color.jpg', (206, 196, 176), size=512, contrast=0.4)
    tint(ph('rough_linen', 'Diffuse'), f'{out}/linen_color.jpg', (236, 216, 178), size=512, contrast=0.8)
    tint(ph('rough_linen', 'Diffuse'), f'{out}/red_shade_color.jpg', (150, 34, 26), size=512, contrast=0.8)
    # books: two rows of 64 spines, oxblood, bottle green, tan calf and black, gilt bands and labels
    B = _rect_uv_texture(2048, 1024, lambda im, dr: None, bg=(18, 14, 12)); dr = ImageDraw.Draw(B)
    pal = [(110, 26, 20), (90, 20, 18), (30, 52, 34), (24, 40, 30), (150, 104, 60), (120, 80, 46), (34, 30, 28), (70, 40, 26), (130, 34, 24)]
    for r in range(2):
        for i in range(64):
            x0 = i * 32; c_ = pal[rng.integers(len(pal))]; c_ = tuple(int(np.clip(v * rng.uniform(0.8, 1.15), 0, 255)) for v in c_)
            dr.rectangle([x0 + 1, r * 512, x0 + 30, r * 512 + 511], fill=c_)
            g = (190, 152, 80)
            for zb in (40, 60, 440, 460): dr.rectangle([x0 + 3, r * 512 + zb, x0 + 28, r * 512 + zb + 5], fill=g)
            if rng.random() < 0.6: dr.rectangle([x0 + 6, r * 512 + 120, x0 + 25, r * 512 + 180], fill=(16, 14, 12)); dr.rectangle([x0 + 9, r * 512 + 140, x0 + 22, r * 512 + 144], fill=g)
    B.save(f'{out}/books_color.jpg', quality=92)
    # the family's photographs: soft sepia and grey portraits, one or two figures against a pale studio ground
    for k in range(5):
        Q = np.zeros((640, 512, 3), np.float32); yy, xx = np.mgrid[0:640, 0:512].astype(np.float32)
        tone = lin((150, 128, 100)) if k % 2 == 0 else lin((140, 138, 132))
        Q[:] = tone[None, None] * (0.85 + 0.3 * (1 - yy / 640))[..., None]
        for j, cx in enumerate((256,) if k % 3 else (180, 330)):
            body = (((xx - cx) / 110) ** 2 + ((yy - 600) / 260) ** 2) < 1; head = (((xx - cx) / 48) ** 2 + ((yy - 290) / 60) ** 2) < 1
            Q[body] = tone * 0.22; Q[head] = tone * (0.75 + 0.1 * j)
            hair = head & (yy < 270); Q[hair] = tone * 0.15
        Q = np.asarray(Image.fromarray((lin_to_srgb(Q) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5)))
        Image.fromarray(Q).save(f'{out}/photo{k}.jpg', quality=90)
    # the crest-framed print over the cabinet: figures in gold on a red ground
    Pr = _rect_uv_texture(768, 256, lambda im, dr: None, bg=(150, 34, 28)); dr = ImageDraw.Draw(Pr)
    for k in range(9):
        x0 = 50 + k * 76; dr.ellipse([x0, 90, x0 + 40, 130], fill=(214, 186, 120)); dr.rectangle([x0 + 6, 125, x0 + 34, 200], fill=(214, 186, 120))
    dr.rectangle([8, 8, 759, 247], outline=(210, 180, 110), width=6); Pr.save(f'{out}/crest_print.jpg', quality=92)
    # the garden in the afternoon sun, through louvers and sheers: blown out, warm, green below, a striped awning, the
    # wedding's pinks and whites; seen only by the camera (the light is the sun's)
    W_, H_ = 2048, 1024; yy, xx = np.mgrid[0:H_, 0:W_].astype(np.float32); yy /= H_; xx /= W_
    sky = lin((255, 244, 214)) * (1.0 - 0.15 * yy[..., None])
    trees = yy > 0.18 + 0.1 * np.sin(xx * 9 + 1) * np.sin(xx * 3.1) + 0.05 * _noise(W_, 30, 7)[:H_, :W_]
    view = np.where(trees[..., None], lin((150, 170, 92)) * (0.7 + 0.5 * _noise(W_, 12, 8)[:H_, :W_])[..., None], sky)
    awning = (yy > 0.42) & (yy < 0.5) & (xx > 0.2) & (xx < 0.85)
    view = np.where(awning[..., None], np.where(((xx * 60) % 2 < 1)[..., None], lin((238, 232, 214)), lin((62, 110, 70))), view)
    lawn = yy > 0.68
    view = np.where(lawn[..., None], lin((128, 156, 70)) * (0.85 + 0.25 * _noise(W_, 20, 9)[:H_, :W_])[..., None], view)
    for k in range(140):                                                             # the guests
        x0 = rng.uniform(0, 1); y0 = rng.uniform(0.52, 0.8); r = rng.uniform(0.006, 0.012)
        dot = ((xx - x0) / (r * 0.6)) ** 2 + ((yy - y0) / (r * 2.4)) ** 2 < 1
        view = np.where(dot[..., None], lin(tuple(int(v) for v in [(232, 170, 176), (240, 236, 226), (40, 36, 34), (200, 120, 110)][k % 4])), view)
    view = np.asarray(Image.fromarray((lin_to_srgb(view) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(9)))
    Image.fromarray(view).save(f'{out}/garden_view.jpg', quality=92)
    # the hall mirror: old silvering, dark and smoky, a little foxed (the model's glass is white in its colour map and
    # gets its look from its metal map, which the room drops: left white it reads as a blank)
    m = os.path.join(CACHE, 'polyhaven', 'ornate_mirror_01', 'textures', 'ornate_mirror_01_')
    D = np.asarray(Image.open(m + 'diff_1k.jpg').convert('RGB'), np.float32)
    A = np.asarray(Image.open(m + 'arm_1k.jpg').convert('RGB'), np.float32) / 255
    glass = ((A[..., 2] > 0.5) & (A[..., 1] < 0.25)).astype(np.uint8) * 255
    k = np.asarray(Image.fromarray(glass).filter(ImageFilter.GaussianBlur(1.5)), np.float32)[..., None] / 255
    n = _noise(1024, 90, 11)[..., None]; spots = np.clip((150 - D.mean(-1, keepdims=True)) / 80, 0, 1)
    smoke = np.array((34, 31, 27), np.float32) * (0.8 + 0.35 * n) + spots * 40
    Image.fromarray((D * (1 - k) + smoke * k).clip(0, 255).astype(np.uint8)).save(f'{out}/mirror_color.jpg', quality=92)


if __name__ == '__main__':
    room = sys.argv[1]
    out = os.path.join(ROOT, 'pipeline', 'out', 'textures', room); os.makedirs(out, exist_ok=True)
    globals()[room.replace('-', '_')](out)   # room ids may have hyphens (the-matrix)
    print('ok', sorted(os.listdir(out)))
