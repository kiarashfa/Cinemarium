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


if __name__ == '__main__':
    room = sys.argv[1]
    out = os.path.join(ROOT, 'pipeline', 'out', 'textures', room); os.makedirs(out, exist_ok=True)
    globals()[room.replace('-', '_')](out)   # room ids may have hyphens (the-matrix)
    print('ok', sorted(os.listdir(out)))
