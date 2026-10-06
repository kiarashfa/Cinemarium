# Costume changes for Rocketbox avatars, painted into copies of their textures (the originals stay untouched).
# Coordinates are fractions of the texture (x right, y down), read off each avatar's UV layout.
# Usage: python pipeline/people_textures.py severance   ->  pipeline/out/people/<character>/*.png
import os, sys
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
AV = os.path.join(ROOT, 'pipeline', 'cache', 'rocketbox', 'avatars')
OUT = os.path.join(ROOT, 'pipeline', 'out', 'people')


def load(avatar, name):
    return np.asarray(Image.open(os.path.join(AV, avatar, 'Textures', name)).convert('RGB'), np.float32) / 255


def save(arr, character, name):
    d = os.path.join(OUT, character); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name.replace('.tga', '.png'))
    Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p)
    return p


def hsv(a):
    mx, mn = a.max(-1), a.min(-1); d = mx - mn + 1e-6
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return h, d / (mx + 1e-6), mx


def lum(a): return a @ np.array([0.2126, 0.7152, 0.0722], np.float32)


def soft(mask, px):
    im = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(px))
    return np.asarray(im, np.float32) / 255


def recolour(a, mask, target, contrast=1.0):
    """Within mask: mean colour -> target (sRGB 0-255), keeping the cloth's own light and dark (its folds)."""
    l = lum(a); m = mask > 0.5
    rel = (l / max(l[m].mean() if m.any() else 1, 1e-4)) ** contrast
    col = np.array(target, np.float32)[None, None, :] / 255 * rel[..., None]
    return a * (1 - mask[..., None]) + col * mask[..., None]


def region(shape, x0, y0, x1, y1):
    h, w = shape[:2]; m = np.zeros((h, w), np.float32); m[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)] = 1; return m


def ellipse(shape, cx, cy, rx, ry):
    h, w = shape[:2]; yy, xx = np.mgrid[0:h, 0:w]
    return (((xx / w - cx) / rx) ** 2 + ((yy / h - cy) / ry) ** 2 <= 1).astype(np.float32)


def tie(a, x, y0, y1, w0, w1, colour, knot=0.03):
    """Paint a tie down a shirt front: a knot at y0, a blade widening from w0 to w1, a point at y1."""
    h, w = a.shape[:2]; yy, xx = np.mgrid[0:h, 0:w]; u, v = xx / w, yy / h
    t = np.clip((v - y0) / (y1 - y0), 0, 1)
    half = np.where(v < y0 + knot, w0 * 0.75, w0 + (w1 - w0) * t) / 2
    half = np.where(v > y1 - 0.025, half * np.clip((y1 - v) / 0.025, 0, 1), half)
    m = ((np.abs(u - x) <= half) & (v >= y0) & (v <= y1)).astype(np.float32)
    m = soft(m, 1.2)
    l = lum(a); shade = np.clip(l / max(l[m > 0.5].mean(), 1e-4), 0.6, 1.25) ** 0.8
    stripe = 1 + 0.06 * np.sin((u * 2048 + v * 2048) * 0.35)
    col = np.array(colour, np.float32)[None, None, :] / 255 * (shade * stripe)[..., None]
    knot_shade = np.where(v < y0 + knot, 0.85, 1.0)[..., None]
    return a * (1 - m[..., None]) + col * knot_shade * m[..., None]


def beard(a, rng, regions, colour=(34, 26, 21), strength=0.62):
    """Short dense beard: dark stubble noise inside soft regions (ellipses), stronger where they overlap."""
    m = np.zeros(a.shape[:2], np.float32)
    for (cx, cy, rx, ry, s) in regions: m = np.maximum(m, ellipse(a.shape, cx, cy, rx, ry) * s)
    m = soft(m, 14)
    n = rng.random(a.shape[:2]).astype(np.float32)
    n = np.asarray(Image.fromarray((n * 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(1)), np.float32) / 255
    n = np.clip((n - 0.35) * 2.2, 0, 1)   # sparse dark hairs over skin, not a flat fill
    hair = np.array(colour, np.float32)[None, None, :] / 255 * (0.7 + 0.6 * n[..., None])
    k = np.clip(m * strength * (0.75 + 0.5 * n), 0, 1)[..., None]
    return a * (1 - k) + hair * k


def severance():
    rng = np.random.default_rng(7)
    made = {}
    # Mark S.: the white shirt gets Lumon's dark tie
    a = load('Business_Male_06', 'm025_body_color.tga')
    made['mark'] = [save(tie(a, 0.5, 0.405, 0.695, 0.03, 0.055, (30, 40, 66)), 'mark', 'm025_body_color.tga')]
    # Helly R.: copper-red hair, a deep green blouse
    h = load('Female_Adult_15', 'f018_head_color.tga'); H, S, V = hsv(h)
    sstep = lambda e0, e1, x: np.clip((x - e0) / (e1 - e0), 0, 1) ** 2 * (3 - 2 * np.clip((x - e0) / (e1 - e0), 0, 1))
    hairy = (sstep(0.6, 0.48, V) * sstep(0.44, 0.56, S)).astype(np.float32)   # hair: V 0.29-0.45, S > 0.55; skin: V > 0.57, S < 0.52
    protect = np.maximum.reduce([ellipse(h.shape, 0.5, 0.36, 0.22, 0.25), region(h.shape, 0.33, 0.45, 0.67, 0.82),
                                 region(h.shape, 0.0, 0.6, 0.125, 0.92), region(h.shape, 0.1, 0.8, 0.205, 1.0), region(h.shape, 0.19, 0.86, 0.32, 1.0), region(h.shape, 0.0, 0.0, 0.08, 0.05)])
    mask = soft(hairy * (1 - protect) * (V > 0.04), 1.5)
    made['helly'] = [save(recolour(h, mask, (124, 46, 28), contrast=1.15), 'helly', 'f018_head_color.tga')]
    o = load('Female_Adult_15', 'f018_opacity_color.tga'); oV = hsv(o)[2]
    made['helly'].append(save(recolour(o, soft((oV > 0.03).astype(np.float32), 1), (124, 46, 28), contrast=1.15), 'helly', 'f018_opacity_color.tga'))
    b = load('Female_Adult_15', 'f018_body_color.tga'); H, S, V = hsv(b)
    blouse = soft(((H > 190) & (H < 260) & (S > 0.12) & (V > 0.12)).astype(np.float32), 1.5)
    made['helly'].append(save(recolour(b, blouse, (34, 72, 58), contrast=1.05), 'helly', 'f018_body_color.tga'))
    # Irving B.: charcoal-navy suit over a white shirt and a wine tie
    b = load('Male_Adult_03', 'm004_body_color.tga'); H, S, V = hsv(b)
    shirt = (((H > 320) | (H < 12)) & (S > 0.3) & (V > 0.12) & (V < 0.75)).astype(np.float32)
    jacket = ((S < 0.32) & (V > 0.09) & (V < 0.75)).astype(np.float32) * region(b.shape, 0.0, 0.40, 1.0, 0.86) * (1 - shirt)
    jacket = np.maximum(jacket, ((S < 0.32) & (V > 0.09)).astype(np.float32) * region(b.shape, 0.33, 0.0, 0.67, 0.42))
    b = recolour(b, soft(jacket, 1.2), (52, 57, 70), contrast=0.9)
    b = recolour(b, soft(shirt, 1.2), (222, 225, 230), contrast=0.6)
    made['irving'] = [save(tie(b, 0.5, 0.462, 0.62, 0.026, 0.045, (92, 30, 40)), 'irving', 'm004_body_color.tga')]
    # Dylan G.: a full short beard (the head texture already has a goatee)
    h = load('Business_Male_05', 'm016_head_color.tga')
    made['dylan'] = [save(beard(h, rng, [(0.5, 0.50, 0.17, 0.06, 1.0), (0.5, 0.515, 0.09, 0.045, 1.0), (0.33, 0.45, 0.05, 0.07, 0.55),
                                         (0.67, 0.45, 0.05, 0.07, 0.55), (0.5, 0.372, 0.06, 0.01, 0.8)]), 'dylan', 'm016_head_color.tga')]
    b = load('Business_Male_05', 'm016_body_color.tga'); H, S, V = hsv(b)
    tie_purple = soft(((H > 250) & (H < 320) & (S > 0.2)).astype(np.float32), 1)
    made['dylan'].append(save(recolour(b, tie_purple, (150, 112, 38)), 'dylan', 'm016_body_color.tga'))
    for k, v in made.items(): print(k, [os.path.basename(p) for p in v])


if __name__ == '__main__':
    globals()[sys.argv[1]]()
