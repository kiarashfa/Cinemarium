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


if __name__ == '__main__':
    room = sys.argv[1]
    out = os.path.join(ROOT, 'pipeline', 'out', 'textures', room); os.makedirs(out, exist_ok=True)
    globals()[room.replace('-', '_')](out)   # room ids may have hyphens (the-matrix)
    print('ok', sorted(os.listdir(out)))
