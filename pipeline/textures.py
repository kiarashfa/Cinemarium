# Prepares a room's textures from the cached CC0 sources: recolour by luminance (keeps the material's own
# variation, sets its mean colour), resize, and write web-friendly JPEGs into pipeline/out/textures/<room>/.
# Usage: python pipeline/textures.py severance
import os, sys
import numpy as np
from PIL import Image

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


if __name__ == '__main__':
    room = sys.argv[1]
    out = os.path.join(ROOT, 'pipeline', 'out', 'textures', room); os.makedirs(out, exist_ok=True)
    globals()[room](out)
    print('ok', sorted(os.listdir(out)))
