# Costume changes for Rocketbox avatars, painted into copies of their textures (the originals stay untouched).
# Most masks are placed on the body, not on the UV layout: pipeline/blender/texel_maps.py records, for every
# texel, its rest-pose position (metres, the avatar facing -y) and the bone that moves it.
# Usage: python pipeline/people_textures.py severance   ->  pipeline/out/people/<character>/*.png (1024 px)
import os, sys
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
AV = os.path.join(ROOT, 'pipeline', 'cache', 'rocketbox', 'avatars')
OUT = os.path.join(ROOT, 'pipeline', 'out', 'people')
SIZE = 1024


def load(avatar, name, size=SIZE):
    im = Image.open(os.path.join(AV, avatar, 'Textures', name)).convert('RGB')
    if size and im.size[0] != size: im = im.resize((size, size), Image.LANCZOS)
    return np.asarray(im, np.float32) / 255


def load_alpha(avatar, name, size=SIZE):
    """The alpha of a texture (hair cards cut out their strands with it)."""
    im = Image.open(os.path.join(AV, avatar, 'Textures', name)).convert('RGBA').getchannel('A')
    if size and im.size[0] != size: im = im.resize((size, size), Image.LANCZOS)
    return np.asarray(im, np.float32) / 255


def save(arr, character, name, alpha=None):
    """Write a texture; hair-card ('opacity') textures keep their alpha, or the strands become solid cards."""
    d = os.path.join(OUT, character); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name.replace('.tga', '.png'))
    if alpha is None and 'opacity' in name: raise ValueError(f'{name}: hair cards need their alpha (pass alpha=load_alpha(...))')
    if not np.isfinite(arr).all(): print('non-finite texels in', character, name, int((~np.isfinite(arr)).sum())); arr = np.nan_to_num(arr)
    rgb = (np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)
    if alpha is not None: Image.fromarray(np.dstack([rgb, (np.clip(alpha, 0, 1) * 255 + 0.5).astype(np.uint8)]), 'RGBA').save(p)
    else: Image.fromarray(rgb).save(p)
    return p


class Body:
    """Where each texel of one texture sits on the body."""
    def __init__(self, tex):
        d = np.load(os.path.join(OUT, 'maps', tex.replace('.tga', '.npz')))
        self.pos = d['pos'].astype(np.float32); self.nor = d['nor'].astype(np.float32)
        self.x, self.y, self.z = self.pos[..., 0], self.pos[..., 1], self.pos[..., 2]
        self.ok = np.isfinite(self.x)
        self.bone, self.groups = d['bone'], list(d['groups'])
        self.J = {k: v for k, v in zip(d['joint_names'], d['joints'])}

    def part(self, *keys):
        """Texels moved mostly by any bone whose name contains one of keys ('Spine', 'Thigh', ...)."""
        ids = [i for i, g in enumerate(self.groups) if any(k in g for k in keys)]
        return np.isin(self.bone, ids) & self.ok

    def where(self, cond):
        return np.where(self.ok, cond, False)

    def grow(self, mask, px=6):
        """Let a mask bleed into the empty padding around its UV islands, so filtering shows no seams."""
        m = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(px * 2 + 1))
        g = np.asarray(m, np.float32) / 255
        return np.where(self.ok, mask.astype(np.float32), g)


def hsv(a):
    mx, mn = a.max(-1), a.min(-1); d = mx - mn + 1e-6
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return h, d / (mx + 1e-6), mx


def lum(a): return a @ np.array([0.2126, 0.7152, 0.0722], np.float32)


def soft(mask, px):
    im = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(px))
    return np.asarray(im, np.float32) / 255


def blur(a, px):
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(px))
    return np.asarray(im, np.float32) / 255


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def recolour(a, mask, target, contrast=1.0, flatten=0.0):
    """Within mask: mean colour -> target (sRGB 0-255), keeping the cloth's own light and dark (its folds).
    flatten blurs the luminance first (px), to lose a weave or a print that the new cloth would not have."""
    src = blur(a, flatten) if flatten else a
    l = lum(src); m = (mask > 0.5) & (l > 0.02)        # the mean of the cloth, not of the black padding around it
    rel = np.clip(l / max(l[m].mean() if m.any() else 1, 1e-4), 0.25, 2.2) ** contrast   # near-black cloth: no blown-up specks
    col = np.array(target, np.float32)[None, None, :] / 255 * rel[..., None]
    return a * (1 - mask[..., None]) + col * mask[..., None]


def region(shape, x0, y0, x1, y1):
    h, w = shape[:2]; m = np.zeros((h, w), np.float32); m[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)] = 1; return m


def ellipse(shape, cx, cy, rx, ry):
    h, w = shape[:2]; yy, xx = np.mgrid[0:h, 0:w]
    return (((xx / w - cx) / rx) ** 2 + ((yy / h - cy) / ry) ** 2 <= 1).astype(np.float32)


def noise(shape, px, seed):
    """Band-limited noise in [0, 1], features about px texels across."""
    r = np.random.default_rng(seed).random(shape[:2]).astype(np.float32)
    n = blur(r, px) - blur(r, px * 2.2) * 0.85
    return (n - n.min()) / (n.max() - n.min() + 1e-6)


def tie(body, a, colour, top, tip, w_knot=0.022, w_blade=0.075, within=None):
    """A tie down the shirt front, from the knot under the collar (z = top) to its point (z = tip)."""
    t = np.clip((top - body.z) / (top - tip), 0, 1)
    half = np.where(t < 0.12, w_knot / 2, (w_knot + (w_blade - w_knot) * smooth(0.1, 0.9, t)) / 2)
    half = half * np.clip((body.z - tip) / 0.035, 0, 1) ** 0.6           # the point
    front = body.where((body.nor[..., 1] < -0.25) & (body.y < 0))
    m = body.where((np.abs(body.x) <= half) & (body.z <= top) & (body.z >= tip)) & front
    if within is not None: m &= within > 0.5
    m = body.grow(m.astype(np.float32), 2)
    l = lum(a); shade = np.clip(l / max(l[m > 0.5].mean() if (m > 0.5).any() else 1, 1e-4), 0.55, 1.3) ** 0.7
    col = np.array(colour, np.float32)[None, None, :] / 255 * shade[..., None]
    col = col * np.where(t[..., None] < 0.12, 0.82, 1.0)                  # the knot sits in shadow
    return a * (1 - m[..., None]) + col * m[..., None]


def beard(a, rng, regions, colour=(34, 26, 21), strength=0.62):
    """Short dense beard: dark stubble noise inside soft regions (UV ellipses), stronger where they overlap."""
    m = np.zeros(a.shape[:2], np.float32)
    for (cx, cy, rx, ry, s) in regions: m = np.maximum(m, ellipse(a.shape, cx, cy, rx, ry) * s)
    m = soft(m, 7)
    n = rng.random(a.shape[:2]).astype(np.float32)
    n = np.clip((blur(n, 0.6) - 0.35) * 2.2, 0, 1)   # sparse dark hairs over skin, not a flat fill
    hair = np.array(colour, np.float32)[None, None, :] / 255 * (0.7 + 0.6 * n[..., None])
    k = np.clip(m * strength * (0.75 + 0.5 * n), 0, 1)[..., None]
    return a * (1 - k) + hair * k


def skin_tone(a, mask, factor):
    """Deepen a skin tone: darker, a touch warmer, the same detail."""
    f = np.array(factor, np.float32)[None, None, :]
    return a * (1 - mask[..., None]) + a * f * mask[..., None]


def severance():
    rng = np.random.default_rng(7)
    made = {}

    # Mark S. (Business_Male_01): a dark navy suit, white shirt, a near-black tie; his own brown, swept hair
    b = load('Business_Male_01', 'm005_body_color.tga'); B = Body('m005_body_color.tga'); H, S, V = hsv(b)
    cloth = B.where(~B.part('Hand', 'Finger', 'Head', 'Foot', 'Toe') & (V < 0.3) & (S < 0.5))
    b = recolour(b, B.grow(cloth.astype(np.float32)), (34, 40, 58), contrast=0.95)
    red = (((H < 25) | (H > 335)) & (S > 0.35) & (V > 0.12) & ~B.part('Hand', 'Finger')).astype(np.float32)
    b = recolour(b, soft(red, 0.7), (30, 32, 42), contrast=0.8)
    made['mark'] = [save(b, 'mark', 'm005_body_color.tga')]

    # Irving B. (Male_Adult_03): salt-and-pepper curly grey hair (fuller in the mesh too), a grey suit,
    # a light blue shirt and a navy tie
    h = load('Male_Adult_03', 'm004_head_color.tga'); Hd = Body('m004_head_color.tga'); H, S, V = hsv(h)
    brow = Hd.J['Bip01 MMiddleEyebrow'][2]
    ax = np.abs(Hd.x)
    line = brow + 0.058 - 0.03 * smooth(0.03, 0.062, ax)                       # the hairline: high in front,
    line = line + (brow + 0.004 - line) * smooth(-0.075, -0.035, Hd.y)          # down to the ears at the sides,
    line = line + (brow - 0.088 - line) * smooth(-0.005, 0.05, Hd.y)            # to the nape at the back
    ear = (ax > 0.066) & (Hd.z < brow + 0.008) & (Hd.z > brow - 0.07) & (np.abs(Hd.y) < 0.04)
    hairy = Hd.where((Hd.z > line) & ~ear) * smooth(0.86, 0.74, V)
    hm = soft(Hd.grow(hairy.astype(np.float32), 3), 1.6)
    curls = noise(h.shape, 1.6, 11); pepper = smooth(0.5, 0.68, noise(h.shape, 2.4, 12))
    grey = np.array([176, 174, 170], np.float32) / 255 * (1 - pepper[..., None]) + np.array([84, 82, 80], np.float32) / 255 * pepper[..., None]
    shade = (lum(h) / max(lum(h)[hm > 0.5].mean(), 1e-4)) ** 0.5
    grey = grey * (0.72 + 0.45 * curls[..., None]) * shade[..., None]
    h = h * (1 - hm[..., None]) + grey * hm[..., None]
    made['irving'] = [save(h, 'irving', 'm004_head_color.tga')]
    o = load('Male_Adult_03', 'm004_opacity_color.tga'); oV = hsv(o)[2]
    made['irving'].append(save(recolour(o, soft((oV > 0.03).astype(np.float32), 1), (118, 116, 112), contrast=1.1), 'irving', 'm004_opacity_color.tga', load_alpha('Male_Adult_03', 'm004_opacity_color.tga')))
    b = load('Male_Adult_03', 'm004_body_color.tga'); B = Body('m004_body_color.tga'); H, S, V = hsv(b)
    shirt = ((((H > 300) | (H < 16)) & (S > 0.2) & (V > 0.08)) & ~B.part('Hand', 'Finger'))
    jacket = B.where((S < 0.32) & (V > 0.06) & ~shirt & ~B.part('Hand', 'Finger', 'Foot', 'Toe'))
    b = recolour(b, B.grow(jacket.astype(np.float32)), (84, 86, 92), contrast=0.85)
    sh = soft(shirt.astype(np.float32), 0.7)
    b = recolour(b, sh, (190, 206, 226), contrast=0.55)
    neck = B.J['Bip01 Neck'][2]
    b = tie(B, b, (38, 44, 72), neck - 0.035, B.J['Bip01 Spine'][2] + 0.02, within=sh)
    made['irving'].append(save(b, 'irving', 'm004_body_color.tga'))

    # Dylan G. (Business_Male_05, made heavy in the mesh): a deeper skin tone and a full short beard,
    # a charcoal suit, a light blue shirt (Lumon's men wear white or light blue), the black tie he has
    h = load('Business_Male_05', 'm016_head_color.tga'); Hd = Body('m016_head_color.tga')
    eyes = region(h.shape, 0.0, 0.62, 0.4, 1.0) * (Hd.z < 1.55)   # the eye and mouth islands keep their colour
    h = skin_tone(h, Hd.grow(Hd.ok.astype(np.float32)) * (1 - eyes), (0.80, 0.75, 0.72))
    h = beard(h, rng, [(0.5, 0.50, 0.17, 0.06, 1.0), (0.5, 0.515, 0.09, 0.045, 1.0), (0.33, 0.45, 0.05, 0.07, 0.55),
                       (0.67, 0.45, 0.05, 0.07, 0.55), (0.5, 0.372, 0.06, 0.01, 0.8)], colour=(22, 17, 14), strength=0.86)
    made['dylan'] = [save(h, 'dylan', 'm016_head_color.tga')]
    b = load('Business_Male_05', 'm016_body_color.tga'); B = Body('m016_body_color.tga'); H, S, V = hsv(b)
    hands = B.grow(B.part('Hand', 'Finger').astype(np.float32))
    b = skin_tone(b, hands, (0.80, 0.75, 0.72))
    purple = B.where((H > 245) & (H < 325) & (S > 0.18))
    b = recolour(b, soft(B.grow(purple.astype(np.float32)), 0.8), (176, 197, 226), contrast=0.6)
    suit = B.where(~purple & ~B.part('Hand', 'Finger') & (V < 0.42) & (S < 0.4) & (np.abs(B.x) > 0.0))
    suit &= ~B.where((np.abs(B.x) < 0.045) & (B.y < -0.08) & (B.z > B.J['Bip01 Spine1'][2]) & (V < 0.12))   # keep the black tie
    b = recolour(b, B.grow(suit.astype(np.float32)), (50, 52, 58), contrast=0.7)
    made['dylan'].append(save(b, 'dylan', 'm016_body_color.tga'))

    # Seth Milchick (Male_Adult_12, made athletic in the mesh), as in season one: a crisp white shirt, a dark
    # tie and belt, charcoal trousers, black shoes; a thin groomed moustache
    h = load('Male_Adult_12', 'm007_head_color.tga'); Hd = Body('m007_head_color.tga')
    lip, nose = Hd.J['Bip01 MUpperLip'], Hd.J['Bip01 MNose']
    # a thin line along the whole upper lip, from corner to corner (the corners sit at |x| 2.8 cm, 0.8 cm below the
    # lip joint), following the lip's curve down at the ends; the philtrum a little lighter
    u = np.clip(np.abs(Hd.x) / 0.028, 0, 1.3)
    zc = lip[2] + 0.0165 - 0.013 * u ** 2
    hh = 0.0032 * (1 - 0.3 * u ** 2)
    mo = Hd.where((Hd.y < lip[1] + 0.03) & (u < 1.08) & (np.abs(Hd.z - zc) < hh)).astype(np.float32)
    mo *= np.where(np.abs(Hd.x) < 0.004, 0.65, 1.0)
    mm = soft(Hd.grow(mo, 1), 1.5) * 0.9
    hairs = np.clip(0.55 + 0.7 * noise(h.shape, 0.6, 5), 0, 1.2)[..., None]
    h = h * (1 - mm[..., None]) + (np.array([22, 16, 13], np.float32) / 255 * hairs) * mm[..., None]
    made['milchick'] = [save(h, 'milchick', 'm007_head_color.tga')]
    b = load('Male_Adult_12', 'm007_body_color.tga'); B = Body('m007_body_color.tga'); H, S, V = hsv(b)
    belt = B.J['Bip01 Pelvis'][2] + 0.09
    upper = B.where(B.part('Spine', 'Clavicle', 'Neck', 'UpperArm', 'Forearm', 'Pelvis') & (B.z > belt))
    upper |= B.where(B.part('Hand') & (H > 170) & (H < 270) & (S > 0.08))   # the jacket's cuffs, which the hands carry
    lower = B.where(B.part('Pelvis', 'Thigh', 'Calf', 'Spine') & (B.z <= belt) & (B.z > 0.13))
    feet = B.where(B.part('Foot', 'Toe') | (B.part('Calf') & (B.z <= 0.13)))
    b = recolour(b, B.grow(upper.astype(np.float32)), (238, 239, 236), contrast=0.22, flatten=3.0)
    b = recolour(b, B.grow(lower.astype(np.float32)), (42, 43, 48), contrast=0.6, flatten=1.2)
    b = recolour(b, B.grow(feet.astype(np.float32)), (24, 24, 27), contrast=0.9)
    bl = B.where(B.part('Pelvis', 'Spine', 'Thigh') & (B.z > belt - 0.028) & (B.z < belt + 0.006))
    b = recolour(b, B.grow(bl.astype(np.float32), 1), (22, 21, 22), contrast=0.7)
    b = tie(B, b, (30, 33, 48), B.J['Bip01 Neck'][2] - 0.03, belt + 0.055, w_knot=0.024, w_blade=0.07)
    made['milchick'].append(save(b, 'milchick', 'm007_body_color.tga'))

    # Helly R. (Female_Adult_15): copper-red hair, a royal blue knit top, a navy pencil skirt to the knee,
    # nude tights and nude heels (her black boots become legs)
    h = load('Female_Adult_15', 'f018_head_color.tga'); H, S, V = hsv(h)
    hairy = (smooth(0.6, 0.48, V) * smooth(0.44, 0.56, S)).astype(np.float32)   # hair: V 0.29-0.45, S > 0.55; skin: V > 0.57, S < 0.52
    protect = np.maximum.reduce([ellipse(h.shape, 0.5, 0.36, 0.22, 0.25), region(h.shape, 0.33, 0.45, 0.67, 0.82),
                                 region(h.shape, 0.0, 0.6, 0.125, 0.92), region(h.shape, 0.1, 0.8, 0.205, 1.0), region(h.shape, 0.19, 0.86, 0.32, 1.0), region(h.shape, 0.0, 0.0, 0.08, 0.05)])
    mask = soft(hairy * (1 - protect) * (V > 0.04), 0.8)
    made['helly'] = [save(recolour(h, mask, (124, 46, 28), contrast=1.15), 'helly', 'f018_head_color.tga')]
    o = load('Female_Adult_15', 'f018_opacity_color.tga'); oV = hsv(o)[2]
    made['helly'].append(save(recolour(o, soft((oV > 0.03).astype(np.float32), 1), (124, 46, 28), contrast=1.15), 'helly', 'f018_opacity_color.tga', load_alpha('Female_Adult_15', 'f018_opacity_color.tga')))
    b = load('Female_Adult_15', 'f018_body_color.tga'); B = Body('f018_body_color.tga'); H, S, V = hsv(b)
    waist, knee = B.J['Bip01 Pelvis'][2] + 0.1, B.J['Bip01 L Calf'][2]
    top = B.where((H > 190) & (H < 270) & (S > 0.1) & (V > 0.1) & ~B.part('Thigh', 'Calf', 'Foot', 'Toe') & (B.z > waist))
    b = recolour(b, B.grow(top.astype(np.float32)), (46, 72, 156), contrast=1.0)
    skirt = B.where(B.part('Pelvis', 'Thigh', 'Spine') & (B.z > knee + 0.03) & (B.z <= waist))
    bare = skirt & (V > 0.3)                       # her skirt was shorter: the bare thigh above the knee becomes skirt too
    b = recolour(b, B.grow((skirt & ~bare).astype(np.float32)), (28, 36, 74), contrast=0.9)
    b = recolour(b, bare.astype(np.float32), (25, 33, 68), contrast=0.15, flatten=2.0)
    skin = B.where(B.part('Thigh', 'Calf') & (S > 0.18) & (V > 0.45) & (H < 40))
    tone = np.median(b[skin], 0) * 255 if skin.any() else np.array([214, 170, 146])
    legs = B.where(B.part('Calf', 'Thigh', 'Foot', 'Toe') & (B.z <= knee + 0.03) & (B.z > 0.075) & ~skin)
    b = recolour(b, B.grow(legs.astype(np.float32)), tuple(tone * 0.92), contrast=0.45, flatten=1.0)
    shoes = B.where(B.part('Foot', 'Toe', 'Calf') & (B.z <= 0.075))
    b = recolour(b, B.grow(shoes.astype(np.float32)), (178, 136, 108), contrast=0.8)
    made['helly'].append(save(b, 'helly', 'f018_body_color.tga'))
    for k, v in made.items(): print(k, [os.path.basename(p) for p in v])


def croc(shape, seed, scale=26):
    """A crocodile-skin relief as luminance: rows of rounded scales, larger down the middle of the back."""
    h, w = shape[:2]; rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    jitter = blur(rng.random((h, w)).astype(np.float32), 9) - 0.5; size = 0.7 + 0.6 * blur(rng.random((h, w)).astype(np.float32), 40)
    u, v = x / (scale * size) + jitter * 1.6, y / (scale * 0.8 * size) + jitter * 1.6 + 0.5 * np.floor(x / (scale * size))
    cu, cv = u - np.floor(u) - 0.5, v - np.floor(v) - 0.5
    cell = np.clip(1 - np.hypot(cu * 1.15, cv) * 1.6, 0, 1) ** 0.5           # each scale domes; dark seams between
    return 0.8 + 0.3 * cell


def save_rough(mask, rough_on, rough_off, character, name):
    """A roughness map (white = rough): `rough_on` where the mask is (a glossy coat), `rough_off` elsewhere."""
    r = rough_off + (rough_on - rough_off) * np.clip(mask, 0, 1)
    d = os.path.join(OUT, character); os.makedirs(d, exist_ok=True); p = os.path.join(d, name)
    Image.fromarray((np.clip(r, 0, 1) * 255 + 0.5).astype(np.uint8), 'L').save(p)
    return p


def leftover_black(a, target=(15, 15, 17), keep=None):
    """Anything still pale and grey (a collar, a shoe's tongue, a tag the texel map does not reach) turns black;
    skin is warm and saturated, so it stays; and whatever `keep` marks (the hands: pale nails, a ring)."""
    H, S, V = hsv(a); m = ((V > 0.38) & (S < 0.24)).astype(np.float32)
    m = soft(np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)), np.float32) / 255, 0.5)
    if keep is not None: m = m * (1 - keep)
    return recolour(a, m, target, contrast=0.5)


def the_matrix():
    rng = np.random.default_rng(11)
    made = {}

    # Morpheus (Male_Adult_12, made broad in the mesh): the head shaved; a long crocodile-leather coat in black with a
    # green cast over a dark shirt, black trousers and shoes; the small round glasses are modelled
    h = load('Male_Adult_12', 'm007_head_color.tga'); Hd = Body('m007_head_color.tga'); H, S, V = hsv(h)
    brow = Hd.J['Bip01 MMiddleEyebrow'][2]; ax = np.abs(Hd.x)
    line = brow + 0.05 - 0.028 * smooth(0.03, 0.062, ax)                         # the hairline, front to sides to nape
    line = line + (brow - 0.04 - line) * smooth(-0.075, -0.035, Hd.y) * smooth(0.045, 0.06, ax)   # sideburns go too
    line = line + (brow - 0.092 - line) * smooth(-0.005, 0.05, Hd.y)
    ear = (ax > 0.066) & (Hd.z < brow + 0.008) & (Hd.z > brow - 0.07) & (np.abs(Hd.y) < 0.04)
    face = Hd.where((Hd.y < -0.055) & (Hd.z < brow + 0.02) & (ax < 0.055))   # brows, eyes: keep (sideburns go)
    dark = Hd.where((Hd.z > brow - 0.065) & (V < 0.27) & ~face & ~((ax > 0.07) & (np.abs(Hd.y) < 0.025) & (Hd.z < brow - 0.005)))
    scalp = soft(Hd.grow(Hd.where(((Hd.z > line - 0.006) & ~ear) | dark).astype(np.float32), 3), 2.0)
    face = Hd.where((Hd.y < -0.05) & (Hd.z < brow) & (Hd.z > Hd.J['Bip01 MUpperLip'][2]))
    tone = h[face].mean(0) if face.any() else np.array([0.38, 0.25, 0.18])   # the scalp takes the face's own mean tone
    tone = tone.mean() + (tone - tone.mean()) * 1.3                            # a little warmer: the mean greys it
    skin = tone[None, None, :] * (0.9 + 0.2 * noise(h.shape, 3, 21)[..., None])
    skin = skin * (1 + 0.18 * smooth(brow + 0.07, brow + 0.11, Hd.z)[..., None] * (Hd.y < 0)[..., None])   # a shine on the crown
    h = h * (1 - scalp[..., None]) + skin * scalp[..., None]
    made['morpheus'] = [save(h, 'morpheus', 'm007_head_color.tga')]
    b = load('Male_Adult_12', 'm007_body_color.tga'); B = Body('m007_body_color.tga'); H, S, V = hsv(b)
    hands = B.part('Hand', 'Finger') & ~((H > 170) & (H < 270) & (S > 0.08))
    hem = 0.3                                                                       # the coat falls to mid-calf
    coat = B.where(~hands & ~B.part('Head', 'Foot', 'Toe') & (B.z > hem))
    tee = B.where(coat & (V > 0.55) & (S < 0.25) & B.part('Spine', 'Neck', 'Clavicle'))   # the shirt at the open front
    coat &= ~tee
    scales = croc(b.shape, 3)
    b = recolour(b, B.grow(coat.astype(np.float32)), (24, 30, 26), contrast=0.6, flatten=2.0)
    b = b * (1 - B.grow(coat.astype(np.float32))[..., None] * (1 - scales[..., None]) * 0.55)
    b = recolour(b, soft(tee.astype(np.float32), 0.8), (30, 33, 31), contrast=0.4)
    legs = B.where(B.part('Calf', 'Thigh', 'Foot', 'Toe') & (B.z <= hem))
    b = recolour(b, B.grow(legs.astype(np.float32), 10), (16, 16, 18), contrast=0.7)
    b = leftover_black(b)
    made['morpheus'].append(save(b, 'morpheus', 'm007_body_color.tga'))
    made['morpheus'].append(save_rough(B.grow(coat.astype(np.float32)) * (0.6 + 0.4 * scales), 0.36, 0.75, 'morpheus', 'm007_body_rough.png'))

    # Neo (Business_Male_02, made lean): all in black, a plain black coat over a black shirt, black trousers and shoes
    b = load('Business_Male_02', 'm008_body_color.tga'); B = Body('m008_body_color.tga'); H, S, V = hsv(b)
    hands = B.part('Hand', 'Finger') & (S > 0.15) & (H < 45)
    cloth = B.where(~hands & ~B.part('Head'))
    shirt = B.where(cloth & (V > 0.5) & (S < 0.2))
    b = recolour(b, B.grow((cloth & ~shirt).astype(np.float32)), (20, 20, 23), contrast=0.85)
    b = recolour(b, soft(shirt.astype(np.float32), 0.8), (14, 14, 16), contrast=0.5)
    b = leftover_black(b)
    made['neo'] = [save(b, 'neo', 'm008_body_color.tga')]

    # Trinity (Female_Adult_04): short black hair slicked back with a sheen, a long black patent coat to the knee,
    # black trousers and boots
    h = load('Female_Adult_04', 'f004_head_color.tga'); Hd = Body('f004_head_color.tga'); H, S, V = hsv(h)
    brow = Hd.J['Bip01 MMiddleEyebrow'][2]; ax = np.abs(Hd.x)
    line = brow + 0.045 - 0.03 * smooth(0.03, 0.062, ax)                      # her hairline: front, sides, nape
    line = line + (brow - 0.02 - line) * smooth(-0.07, -0.03, Hd.y)
    line = line + (brow - 0.075 - line) * smooth(-0.005, 0.05, Hd.y)
    scalp = Hd.grow(Hd.where(Hd.z > line - 0.01).astype(np.float32), 4)       # where hair can be (texels off the map: by colour)
    blond = ((H > 22) & (H < 60) & (S > 0.3) & (V > 0.3)).astype(np.float32)
    hm = soft(np.maximum(scalp, (~Hd.ok) * blond), 1.0)                       # all of the scalp, and pale strands off the map
    black = np.array([16, 15, 17], np.float32)[None, None, :] / 255 * (0.7 + 0.8 * noise(h.shape, 1.2, 31)[..., None])
    h = h * (1 - hm[..., None]) + black * hm[..., None]
    made['trinity'] = [save(h, 'trinity', 'f004_head_color.tga')]
    o = load('Female_Adult_04', 'f004_opacity_color.tga'); oV = hsv(o)[2]
    strands = soft((oV > 0.05).astype(np.float32), 0.8)
    al = load_alpha('Female_Adult_04', 'f004_opacity_color.tga'); Op = Body('f004_opacity_color.tga')
    fringe = Op.grow(Op.where((Op.y < -0.06) & (Op.z < Hd.J['Bip01 MMiddleEyebrow'][2] + 0.04)).astype(np.float32), 3)   # slicked back: no fringe
    made['trinity'].append(save(recolour(o, strands, (20, 19, 22), contrast=1.4), 'trinity', 'f004_opacity_color.tga', al * (1 - fringe)))
    b = load('Female_Adult_04', 'f004_body_color.tga'); B = Body('f004_body_color.tga'); H, S, V = hsv(b)
    knee = B.J['Bip01 L Calf'][2]
    skin = B.where((S > 0.2) & (S < 0.6) & (V > 0.45) & (H < 35))
    coat = B.where(~skin & ~B.part('Head', 'Foot', 'Toe') & (B.z > knee - 0.05))
    below = B.where(~skin & B.part('Calf', 'Foot', 'Toe', 'Thigh') & (B.z <= knee - 0.05))
    b = recolour(b, B.grow(coat.astype(np.float32), 10), (14, 14, 16), contrast=1.15)
    b = recolour(b, B.grow(below.astype(np.float32), 10), (12, 12, 13), contrast=0.8)
    H, S, V = hsv(b); rim = soft((((H > 15) & (H < 60) & (S > 0.25) & (V > 0.15) & (V < 0.5)) & ~skin).astype(np.float32), 0.8)   # brown and khaki seams
    b = recolour(b, rim, (14, 14, 16), contrast=0.8)
    b = leftover_black(b)
    made['trinity'].append(save(b, 'trinity', 'f004_body_color.tga'))
    made['trinity'].append(save_rough(B.grow(coat.astype(np.float32)), 0.16, 0.7, 'trinity', 'f004_body_rough.png'))
    for k, v in made.items(): print(k, [os.path.basename(p) for p in v])


def _bald(h, Hd, shine=0.18):
    """Shave a head: everything above the hairline (sideburns and nape too) becomes the face's own skin."""
    H, S, V = hsv(h)
    brow = Hd.J['Bip01 MMiddleEyebrow'][2]; ax = np.abs(Hd.x)
    line = brow + 0.05 - 0.028 * smooth(0.03, 0.062, ax)
    line = line + (brow - 0.04 - line) * smooth(-0.075, -0.035, Hd.y) * smooth(0.045, 0.06, ax)
    line = line + (brow - 0.092 - line) * smooth(-0.005, 0.05, Hd.y)
    ear = (ax > 0.066) & (Hd.z < brow + 0.008) & (Hd.z > brow - 0.07) & (np.abs(Hd.y) < 0.04)
    face = Hd.where((Hd.y < -0.055) & (Hd.z < brow + 0.02) & (ax < 0.055))
    dark = Hd.where((Hd.z > brow - 0.065) & (V < 0.3) & ~face & ~((ax > 0.07) & (np.abs(Hd.y) < 0.025) & (Hd.z < brow - 0.005)))
    scalp = soft(Hd.grow(Hd.where(((Hd.z > line - 0.006) & ~ear) | dark).astype(np.float32), 3), 2.0)
    face = Hd.where((Hd.y < -0.05) & (Hd.z < brow) & (Hd.z > Hd.J['Bip01 MUpperLip'][2]))
    tone = h[face].mean(0) if face.any() else np.array([0.6, 0.45, 0.38])
    tone = tone.mean() + (tone - tone.mean()) * 1.05
    skin = tone[None, None, :] * (0.9 + 0.2 * noise(h.shape, 3, 21)[..., None])
    skin = skin * (1 + shine * smooth(brow + 0.07, brow + 0.11, Hd.z)[..., None] * (Hd.y < 0)[..., None])
    return h * (1 - scalp[..., None]) + skin * scalp[..., None]


def _beard_mask(Hd, moustache=True, cheeks=0.6):
    """Where a beard grows, on the body, with soft edges: the chin and jaw back toward the ears, thinning up the
    cheeks; the upper lip; the lips themselves bare."""
    J = Hd.J; ax = np.abs(Hd.x)
    lip, low, nose = J['Bip01 MUpperLip'][2], J['Bip01 MBottomLip'][2], J['Bip01 MNose'][2]
    chin = low - 0.05
    front = smooth(0.03, -0.01, Hd.y)
    jaw = smooth(chin - 0.045, chin - 0.012, Hd.z) * smooth(0.082, 0.062, ax) * front
    jaw *= cheeks * smooth(nose + 0.005, nose - 0.025, Hd.z) + (1 - cheeks) * smooth(lip - 0.004, lip - 0.024, Hd.z)
    m = jaw
    if moustache:
        m = np.maximum(m, smooth(lip - 0.002, lip + 0.006, Hd.z) * smooth(nose - 0.004, nose - 0.012, Hd.z) * smooth(0.034, 0.022, ax) * smooth(-0.08, -0.1, Hd.y))
    m *= 1 - smooth(0.012, 0.0, np.minimum(np.abs(Hd.z - (lip + low) / 2) - 0.007, 0.03) + 0.0) * smooth(0.03, 0.02, ax) * smooth(-0.09, -0.11, Hd.y)
    return blur(np.where(Hd.ok, m, 0).astype(np.float32), 3)


def _hair_on(h, mask, rng, colour, strength):
    """Short dense hair (a beard, stubble) over skin, as sparse dark hairs rather than a flat fill."""
    n = rng.random(h.shape[:2]).astype(np.float32); n = np.clip((blur(n, 0.6) - 0.35) * 2.2, 0, 1)
    hair = np.array(colour, np.float32)[None, None, :] / 255 * (0.7 + 0.6 * n[..., None])
    k = np.clip(mask * strength * (0.75 + 0.5 * n), 0, 1)[..., None]
    return h * (1 - k) + hair * k


def _sleeves(B, hem):
    """Bare arms below a sleeve's hem: hem as a fraction from shoulder (0) to wrist (1)."""
    J = B.J; ax = np.abs(B.x)
    s, w = J['Bip01 L UpperArm'][0], J['Bip01 L Hand'][0]
    return B.where(B.part('UpperArm', 'Forearm') & (ax > s + (w - s) * hem))


def _skin_paint(b, B, mask, rng, warm=(1.0, 1.0, 1.0)):
    """Bare skin painted where cloth was: the hands' own tone (warmed by `warm`), faintly mottled."""
    H, S, V = hsv(b)
    hands = B.where(B.part('Hand') & (S > 0.15) & (V > 0.25))
    tone = (b[hands].mean(0) if hands.any() else np.array([0.62, 0.45, 0.36])) * np.array(warm, np.float32)
    skin = tone[None, None, :] * (0.92 + 0.14 * noise(b.shape, 2.5, int(rng.integers(1000)))[..., None])
    m = soft(B.grow(mask.astype(np.float32), 3), 1.0)
    return b * (1 - m[..., None]) + skin * m[..., None]


def _flat_normals(avatar, name, who, mask, amount=1.0):
    """A copy of a normal map with its relief smoothed away where `mask` is (skin painted over a sleeve, a knit made
    plain): the cloth's folds and stitches must not show through what replaced it."""
    n = load(avatar, name)
    flat = np.array([0.5, 0.5, 1.0], np.float32)[None, None, :]
    k = (np.clip(mask, 0, 1) * amount)[..., None]
    return save(n * (1 - k) + flat * k, who, name)


def lost():
    """The Swan's people, after Roland Sanchez's costumes for season two."""
    rng = np.random.default_rng(19)
    made = {}

    # Desmond (Sports_Male_03): the DHARMA jumpsuit, pale grey-blue, long-sleeved and open over a white tee, the Swan
    # patch on the chest, work boots; long dark wavy hair, a short beard, his skin a shade lighter
    h = load('Sports_Male_03', 'm300_head_color.tga'); Hd = Body('m300_head_color.tga')
    eyes = Hd.where(Hd.part('Eye')).astype(np.float32)
    h = skin_tone(h, Hd.grow(Hd.ok.astype(np.float32)) * (1 - eyes), (1.1, 1.06, 1.03))
    h = _hair_on(h, _beard_mask(Hd), rng, (34, 25, 19), 0.62)
    made['desmond'] = [save(h, 'desmond', 'm300_head_color.tga')]
    o = load('Sports_Male_03', 'm300_opacity_color.tga'); oV = hsv(o)[2]
    made['desmond'].append(save(recolour(o, soft((oV > 0.03).astype(np.float32), 1), (84, 62, 44), contrast=1.35), 'desmond', 'm300_opacity_color.tga',
                                load_alpha('Sports_Male_03', 'm300_opacity_color.tga')))
    b = load('Sports_Male_03', 'm300_body_color.tga'); B = Body('m300_body_color.tga')
    J = B.J; neck = J['Bip01 Neck'][2]
    hands, feet = B.part('Hand', 'Finger'), B.part('Foot', 'Toe')
    suit = B.where(~hands & ~feet & ~B.part('Head') & ~(B.part('Neck') & (B.z > neck - 0.01)))
    depth = np.clip((neck + 0.01 - B.z) / 0.24, 0, 1)                    # the jumpsuit open from the collar to the sternum
    tee = B.where(suit & (B.y < -0.03) & (np.abs(B.x) < 0.035 + 0.05 * depth) & (B.z > neck - 0.24))
    b = recolour(b, B.grow((suit & ~tee).astype(np.float32), 8), (150, 160, 168), contrast=0.12, flatten=24)
    b = recolour(b, soft(tee.astype(np.float32), 0.8), (214, 212, 204), contrast=0.3, flatten=6)
    patch = B.where((B.y < -0.06) & (np.hypot(B.x - 0.09, B.z - (neck - 0.15)) < 0.035))   # the Swan patch, over his heart
    ring = B.where((B.y < -0.06) & (np.abs(np.hypot(B.x - 0.09, B.z - (neck - 0.15)) - 0.03) < 0.005))
    b = recolour(b, soft(patch.astype(np.float32), 0.6), (210, 206, 192), contrast=0.2)
    b = recolour(b, soft(ring.astype(np.float32), 0.5), (40, 52, 70), contrast=0.2)
    b = recolour(b, B.grow(feet.astype(np.float32), 6), (52, 38, 28), contrast=0.6, flatten=3)
    H, S, V = hsv(b)                                                       # the jersey's orange trims, wherever they are left
    trim = B.where((((H < 32) | (H > 340)) & (S > 0.45) & (V > 0.25)) & ~hands & ~feet & ~B.part('Head'))
    b = recolour(b, soft(B.grow(trim.astype(np.float32), 2), 0.8), (150, 160, 168), contrast=0.1)
    made['desmond'].append(save(b, 'desmond', 'm300_body_color.tga'))

    # Jack (Male_Adult_08): a charcoal shirt, sleeves rolled to the elbow, dark trousers; short dark hair, stubble
    h = load('Male_Adult_08', 'm014_head_color.tga'); Hd = Body('m014_head_color.tga')
    h = _hair_on(h, _beard_mask(Hd, cheeks=0.4), rng, (40, 32, 26), 0.3)
    made['jack'] = [save(h, 'jack', 'm014_head_color.tga')]
    o = load('Male_Adult_08', 'm014_opacity_color.tga'); oV = hsv(o)[2]
    made['jack'].append(save(recolour(o, soft((oV > 0.03).astype(np.float32), 1), (46, 35, 27), contrast=1.15), 'jack', 'm014_opacity_color.tga',
                             load_alpha('Male_Adult_08', 'm014_opacity_color.tga')))
    b = load('Male_Adult_08', 'm014_body_color.tga'); B = Body('m014_body_color.tga'); H, S, V = hsv(b)
    shirt = B.where((H > 180) & (H < 240) & (S > 0.12) & (V > 0.35) & ~B.part('Hand', 'Finger'))
    b = recolour(b, B.grow(shirt.astype(np.float32), 6), (64, 68, 66), contrast=0.8, flatten=1.5)
    b = _skin_paint(b, B, _sleeves(B, 0.55), rng)
    made['jack'].append(_flat_normals('Male_Adult_08', 'm014_body_normal.tga', 'jack', B.grow(_sleeves(B, 0.55).astype(np.float32), 3)))
    legs = B.where(B.part('Thigh', 'Calf') & (V < 0.3))
    b = recolour(b, B.grow(legs.astype(np.float32), 6), (44, 40, 36), contrast=0.85)
    made['jack'].append(save(b, 'jack', 'm014_body_color.tga'))

    # Locke (Male_Adult_14): the head shaved, grey stubble; an olive tee, khaki trousers, his belt
    h = load('Male_Adult_14', 'm012_head_color.tga'); Hd = Body('m012_head_color.tga')
    h = _bald(h, Hd)
    h = _hair_on(h, _beard_mask(Hd, cheeks=0.5), rng, (150, 146, 138), 0.32)
    made['locke'] = [save(h, 'locke', 'm012_head_color.tga')]
    b = load('Male_Adult_14', 'm012_body_color.tga'); B = Body('m012_body_color.tga'); H, S, V = hsv(b)
    top = B.where(B.part('Spine', 'Clavicle', 'UpperArm', 'Forearm', 'Neck') & (S < 0.2) & (V > 0.22) & (B.z > B.J['Bip01 Pelvis'][2] - 0.02))
    b = recolour(b, B.grow(top.astype(np.float32), 6), (88, 86, 54), contrast=0.6, flatten=2.5)
    b = _skin_paint(b, B, _sleeves(B, 0.32), rng)
    made['locke'].append(save(b, 'locke', 'm012_body_color.tga'))
    made['locke'].append(_flat_normals('Male_Adult_14', 'm012_body_normal.tga', 'locke', np.maximum(B.grow(_sleeves(B, 0.32).astype(np.float32), 3), B.grow(top.astype(np.float32)) * 0.6)))

    # Ben (Male_Adult_02, made slight): a burnt-orange tee, khaki trousers; short brown hair close to the head
    h = load('Male_Adult_02', 'm003_head_color.tga'); Hd = Body('m003_head_color.tga'); H, S, V = hsv(h)
    brow = Hd.J['Bip01 MMiddleEyebrow'][2]; ax = np.abs(Hd.x)
    line = brow + 0.05 - 0.026 * smooth(0.03, 0.062, ax)
    line = line + (brow + 0.0 - line) * smooth(-0.075, -0.035, Hd.y)
    line = line + (brow - 0.085 - line) * smooth(-0.005, 0.05, Hd.y)
    ear = (ax > 0.066) & (Hd.z < brow + 0.008) & (Hd.z > brow - 0.07) & (np.abs(Hd.y) < 0.04)
    curls = Hd.where((Hd.z > brow - 0.07 - 0.05 * smooth(-0.01, 0.04, Hd.y)) & (V < 0.3) & ~((Hd.y < -0.05) & (Hd.z < brow + 0.02) & (ax < 0.055)) & ~ear)   # painted curls below the line
    hm = soft(Hd.grow(Hd.where(((Hd.z > line) & ~ear) | curls).astype(np.float32), 3), 1.6)
    crop = np.array([74, 56, 40], np.float32) / 255 * (0.75 + 0.5 * noise(h.shape, 1.4, 41)[..., None])
    h = h * (1 - hm[..., None]) + crop * hm[..., None]
    made['ben'] = [save(h, 'ben', 'm003_head_color.tga')]
    o = load('Male_Adult_02', 'm003_opacity_color.tga')
    made['ben'].append(save(o, 'ben', 'm003_opacity_color.tga', np.zeros(o.shape[:2], np.float32)))   # no curls
    b = load('Male_Adult_02', 'm003_body_color.tga'); B = Body('m003_body_color.tga'); H, S, V = hsv(b)
    knit = B.where(B.part('Spine', 'Clavicle', 'UpperArm', 'Forearm', 'Neck') & (B.z > B.J['Bip01 Pelvis'][2] - 0.02) & (B.z < B.J['Bip01 Neck'][2] + 0.01))
    knit |= B.where(B.part('Pelvis', 'Spine') & (V > 0.3) & (B.z > B.J['Bip01 Pelvis'][2] - 0.14))      # the sweater's hem over the belt
    b = recolour(b, B.grow(knit.astype(np.float32), 6), (186, 88, 36), contrast=0.35, flatten=6)
    H, S, V = hsv(b)
    cuffs = B.where(B.part('Hand', 'Forearm') & ~((S > 0.18) & (H < 35) & (V > 0.3)) & (np.abs(B.x) > B.J['Bip01 L Hand'][0] - 0.06))
    bare = _sleeves(B, 0.34) | cuffs
    b = _skin_paint(b, B, bare, rng, warm=(0.95, 0.86, 0.78))
    made['ben'].append(_flat_normals('Male_Adult_02', 'm003_body_normal.tga', 'ben', np.maximum(B.grow(bare.astype(np.float32), 3), B.grow(knit.astype(np.float32)) * 0.85)))
    legs = B.where(B.part('Thigh', 'Calf', 'Pelvis') & (V < 0.3) & ~B.part('Hand', 'Finger'))
    b = recolour(b, B.grow(legs.astype(np.float32), 6), (138, 120, 92), contrast=0.7)
    made['ben'].append(save(b, 'ben', 'm003_body_color.tga'))

    # Kate (Female_Adult_07): a fitted olive shirt, sleeves pushed up, jeans and boots; long brown hair
    o = load('Female_Adult_07', 'f007_opacity_color.tga'); oV = hsv(o)[2]
    made['kate'] = [save(recolour(o, soft((oV > 0.03).astype(np.float32), 1), (92, 64, 44), contrast=1.15), 'kate', 'f007_opacity_color.tga',
                         load_alpha('Female_Adult_07', 'f007_opacity_color.tga'))]
    b = load('Female_Adult_07', 'f007_body_color.tga'); B = Body('f007_body_color.tga'); H, S, V = hsv(b)
    skin = B.where((S > 0.2) & (S < 0.6) & (V > 0.45) & (H < 35))
    denim = (H > 190) & (H < 240) & (S > 0.08)
    leather = (H > 8) & (H < 48) & (S > 0.22) & (V < 0.55)
    jacket = B.where(~skin & ~denim & B.part('Spine', 'Clavicle', 'UpperArm', 'Forearm', 'Neck'))
    jacket |= B.where(leather & ~skin & B.part('Pelvis', 'Thigh') & (B.z > B.J['Bip01 Pelvis'][2] - 0.16))
    b = recolour(b, B.grow(jacket.astype(np.float32), 6), (72, 76, 52), contrast=0.55, flatten=3)
    cuffs = B.where(B.part('Hand', 'Forearm') & ~skin & (np.abs(B.x) > B.J['Bip01 L Hand'][0] - 0.05))
    bare = _sleeves(B, 0.6) | cuffs
    b = _skin_paint(b, B, bare, rng)
    made['kate'].append(save(b, 'kate', 'f007_body_color.tga'))
    made['kate'].append(_flat_normals('Female_Adult_07', 'f007_body_normal.tga', 'kate', B.grow(bare.astype(np.float32), 3)))
    for k, v in made.items(): print(k, [os.path.basename(p) for p in v])


def _weave(B, base, fleck, rng, scale=1.0):
    """A woollen cloth's colour, made on the body: base with a fine fleck of light and dark threads and a soft slub."""
    n1 = noise(B.x.shape, 0.6 * scale, int(rng.integers(1000))); n2 = noise(B.x.shape, 2.5 * scale, int(rng.integers(1000)))
    c = np.array(base, np.float32)[None, None] / 255 * (0.82 + 0.3 * n2[..., None])
    f = np.clip((n1 - 0.62) * 4, 0, 1)[..., None]; d = np.clip((0.3 - n1) * 4, 0, 1)[..., None]
    return c * (1 - f - d * 0.6) + np.array(fleck, np.float32)[None, None] / 255 * f + c * 0.35 * d * 0.6


def _checks(B, size, a, b, line=None, lw=0.0):
    """A check on the body (x across, z up): squares `size` metres of colours a and b, or a plaid of `line` stripes."""
    x, z = np.nan_to_num(B.x), np.nan_to_num(B.z)
    if line is None:
        m = ((np.floor(x / size) + np.floor(z / size)) % 2).astype(np.float32)[..., None]
        return np.array(a, np.float32) / 255 * (1 - m) + np.array(b, np.float32) / 255 * m
    u, v = (x / size) % 1, (z / size) % 1
    s = ((np.abs(u - 0.5) < lw) | (np.abs(v - 0.5) < lw)).astype(np.float32)[..., None]
    s2 = ((np.abs(u - 0.1) < lw * 0.5) | (np.abs(v - 0.1) < lw * 0.5)).astype(np.float32)[..., None] * 0.6
    c = np.array(a, np.float32)[None, None] / 255
    return c * (1 - s - s2) + np.array(line, np.float32)[None, None] / 255 * s + np.array(b, np.float32)[None, None] / 255 * s2


def _paint(a, mask, colour_img, shade=None, k=0.6, flatten=0.0):
    """Within mask: an image of colour, carrying the cloth's own light and dark (its folds) by `k`; `flatten` blurs that
    first (px), so a knit's pattern (an argyle) does not show through the new cloth."""
    l = lum(blur(a, flatten) if flatten else a); m = mask > 0.5
    rel = np.clip(l / max(l[m].mean() if m.any() else 1, 1e-4), 0.4, 1.8) ** k if shade is None else shade
    return a * (1 - mask[..., None]) + colour_img * rel[..., None] * mask[..., None]


def _hairline(Hd, front=0.05, side=0.004, nape=-0.088):
    """The hairline on a head (front, sides, nape), as heights relative to the eyebrows."""
    brow = Hd.J['Bip01 MMiddleEyebrow'][2]; ax = np.abs(Hd.x)
    line = brow + front - 0.03 * smooth(0.03, 0.062, ax)
    line = line + (brow + side - line) * smooth(-0.075, -0.035, Hd.y)
    line = line + (brow + nape - line) * smooth(-0.005, 0.05, Hd.y)
    ear = (ax > 0.066) & (Hd.z < brow + 0.008) & (Hd.z > brow - 0.07) & (np.abs(Hd.y) < 0.04)
    return brow, line, ear


def seinfeld():
    """Jerry's apartment in season seven, as in "The Wink" (costumes after Charmaine Simmons): Jerry in a denim-blue
    button-down, black jeans and a black belt, white sneakers; George in a brown tweed jacket over a navy-and-mustard
    plaid shirt; Kramer in a grey flecked bouclé jacket over a black-and-white checkerboard shirt, black trousers and
    his black boots; Elaine in a red blazer over a cream blouse, a cream skirt with small red flowers, black tights
    and boots."""
    rng = np.random.default_rng(29)
    made = {}

    # Jerry (Male_Adult_08): dark brown full hair; the shirt a deeper blue, the jeans black, a black belt, white sneakers
    h = load('Male_Adult_08', 'm014_head_color.tga'); Hd = Body('m014_head_color.tga')
    brow, line, ear = _hairline(Hd, front=0.052)
    hm = soft(Hd.grow(Hd.where((Hd.z > line - 0.004) & ~ear).astype(np.float32), 3), 1.4) * smooth(0.8, 0.6, hsv(h)[2])
    h = recolour(h, hm, (40, 29, 22), contrast=1.2)
    made['jerry'] = [save(h, 'jerry', 'm014_head_color.tga')]
    o = load('Male_Adult_08', 'm014_opacity_color.tga'); oV = hsv(o)[2]
    made['jerry'].append(save(recolour(o, soft((oV > 0.03).astype(np.float32), 1), (38, 27, 21), contrast=1.2), 'jerry', 'm014_opacity_color.tga',
                              load_alpha('Male_Adult_08', 'm014_opacity_color.tga')))
    b = load('Male_Adult_08', 'm014_body_color.tga'); B = Body('m014_body_color.tga'); H, S, V = hsv(b)
    shirt = B.where((H > 180) & (H < 240) & (S > 0.12) & (V > 0.35) & ~B.part('Hand', 'Finger'))
    b = recolour(b, B.grow(shirt.astype(np.float32), 24), (64, 94, 150), contrast=0.85, flatten=1.2)
    belt = B.J['Bip01 Pelvis'][2] + 0.085
    legs = B.where(B.part('Thigh', 'Calf', 'Pelvis', 'Foot') & (B.z < belt) & (B.z > 0.075) & ~B.part('Hand', 'Finger'))
    b = recolour(b, B.grow(legs.astype(np.float32), 24), (30, 30, 34), contrast=0.85)
    bl = B.where(B.part('Pelvis', 'Spine', 'Thigh') & (B.z > belt - 0.035) & (B.z < belt + 0.004))
    b = recolour(b, B.grow(bl.astype(np.float32), 1), (18, 17, 18), contrast=0.6)
    b = recolour(b, soft(B.where(bl & (np.abs(B.x) < 0.013) & (B.y < 0)).astype(np.float32), 0.6), (150, 146, 136), contrast=0.4)   # the buckle
    feet = B.where(B.part('Foot', 'Toe', 'Calf') & (B.z <= 0.075))
    b = recolour(b, B.grow(feet.astype(np.float32), 6), (226, 226, 222), contrast=0.45, flatten=1.5)
    sole = B.where(feet & (B.z < 0.03))
    b = recolour(b, soft(sole.astype(np.float32), 0.6), (200, 196, 186), contrast=0.3)
    made['jerry'].append(save(b, 'jerry', 'm014_body_color.tga'))

    # George (Male_Adult_13, made broad, short): bald crown, a short dark fringe round the sides and back; a brown tweed
    # jacket, open over a navy plaid shirt with a mustard line, buttoned to the collar; dark slacks, brown shoes
    h = load('Male_Adult_13', 'm010_head_color.tga'); Hd = Body('m010_head_color.tga')
    h = _bald(h, Hd, shine=0.22)
    brow = Hd.J['Bip01 MMiddleEyebrow'][2]; ax = np.abs(Hd.x)
    behind = smooth(-0.07, -0.045, Hd.y)                                     # behind the temples, round the back
    top = brow + 0.035 + 0.022 * smooth(0.0, 0.07, Hd.y)                       # its upper edge, a little higher at the back
    low = brow - 0.045 - 0.045 * smooth(-0.01, 0.06, Hd.y)                     # its lower edge: sideburns, then the nape
    ears = ((ax > 0.066) & (Hd.z < brow + 0.008) & (Hd.z > brow - 0.07) & (np.abs(Hd.y) < 0.04)).astype(np.float32)
    ears = ears * smooth(brow + 0.012, brow - 0.006, Hd.z)                    # only the ear itself, not the hair above it
    rm = np.where(Hd.ok, behind * smooth(top + 0.022, top - 0.016, Hd.z) * smooth(low - 0.015, low + 0.012, Hd.z) * (1 - ears), 0).astype(np.float32)
    rm = blur(Hd.grow(rm, 4), 6.0)
    h = h * (1 - 0.5 * rm[..., None]) + np.array([40, 31, 26], np.float32) / 255 * 0.5 * rm[..., None]
    h = _hair_on(h, rm, rng, (30, 24, 20), 0.9)
    made['george'] = [save(h, 'george', 'm010_head_color.tga')]
    b = load('Male_Adult_13', 'm010_body_color.tga'); B = Body('m010_body_color.tga'); H, S, V = hsv(b)
    J = B.J; neck, pel = J['Bip01 Neck'][2], J['Bip01 Pelvis'][2]
    hands = B.part('Hand', 'Finger') & (S > 0.15) & (H < 45)
    upper = B.where(~hands & B.part('Spine', 'Clavicle', 'Neck', 'UpperArm', 'Forearm', 'Pelvis') & (B.z > pel - 0.13) & ~(B.part('Neck') & (B.z > neck + 0.02)))
    depth = np.clip((neck - B.z) / 0.5, 0, 1)
    front = B.where(upper & (B.y < -0.02) & (np.abs(B.x) < 0.04 + 0.03 * (1 - depth)) & (B.z > pel + 0.12))   # the shirt between the lapels
    collar = B.where(B.part('Neck', 'Spine2', 'Clavicle') & (B.z > neck - 0.05) & (B.z < neck + 0.03) & (np.abs(B.x) < 0.07))
    shirt = front | collar
    jacket = upper & ~shirt
    tweed = _weave(B, (104, 80, 60), (170, 150, 120), rng)
    b = _paint(b, B.grow(jacket.astype(np.float32), 32), tweed, k=0.22, flatten=16)
    plaid = _checks(B, 0.035, (30, 36, 64), (70, 80, 110), line=(176, 146, 62), lw=0.05)
    b = _paint(b, soft(shirt.astype(np.float32), 0.8), plaid, k=0.4, flatten=10)
    legs = B.where(B.part('Thigh', 'Calf', 'Pelvis') & (B.z <= pel - 0.13) & (B.z > 0.12))
    b = recolour(b, B.grow(legs.astype(np.float32), 6), (62, 56, 50), contrast=0.6, flatten=1.5)
    feet = B.where(B.part('Foot', 'Toe') | (B.part('Calf') & (B.z <= 0.12)))
    b = recolour(b, B.grow(feet.astype(np.float32), 6), (58, 40, 28), contrast=0.8)
    b = leftover_black(b, (40, 34, 30))
    made['george'].append(save(b, 'george', 'm010_body_color.tga'))
    made['george'].append(_flat_normals('Male_Adult_13', 'm010_body_normal.tga', 'george', B.grow(upper.astype(np.float32), 3) * 0.8))

    # Kramer (Male_Adult_06, made lean, tall): the big dark curls; a grey flecked bouclé jacket, open over a black and
    # white checkerboard shirt; black trousers, black boots
    h = load('Male_Adult_06', 'm011_head_color.tga'); Hd = Body('m011_head_color.tga'); H, S, V = hsv(h)
    brow, line, ear = _hairline(Hd, front=0.06)
    hm = soft(Hd.grow(Hd.where((Hd.z > line - 0.01) & ~ear).astype(np.float32), 3), 1.4) * smooth(0.75, 0.55, V)
    h = recolour(h, hm, (50, 34, 25), contrast=1.25)
    made['kramer'] = [save(h, 'kramer', 'm011_head_color.tga')]
    o = load('Male_Adult_06', 'm011_opacity_color.tga'); oV = hsv(o)[2]
    made['kramer'].append(save(recolour(o, soft((oV > 0.03).astype(np.float32), 1), (52, 36, 26), contrast=1.3), 'kramer', 'm011_opacity_color.tga',
                               load_alpha('Male_Adult_06', 'm011_opacity_color.tga')))
    b = load('Male_Adult_06', 'm011_body_color.tga'); B = Body('m011_body_color.tga'); H, S, V = hsv(b)
    J = B.J; neck, pel = J['Bip01 Neck'][2], J['Bip01 Pelvis'][2]
    hands = B.part('Hand', 'Finger') & (S > 0.15) & (H < 45) & ~(((H < 15) | (H > 340)) & (S > 0.5))
    upper = B.where(~hands & B.part('Spine', 'Clavicle', 'Neck', 'UpperArm', 'Forearm', 'Pelvis', 'Hand', 'Thigh') & (B.z > pel - 0.11) & ~(B.part('Neck') & (B.z > neck + 0.03)))   # the coat to the hips
    depth = np.clip((neck - B.z) / 0.5, 0, 1)
    front = B.where(upper & (B.y < -0.02) & (np.abs(B.x) < 0.045 + 0.04 * (1 - depth)) & (B.z > pel + 0.1))
    collar = B.where(B.part('Neck', 'Spine2', 'Clavicle') & (B.z > neck - 0.06) & (B.z < neck + 0.04) & (np.abs(B.x) < 0.075))
    shirt = front | collar
    jacket = upper & ~shirt
    boucle = _weave(B, (112, 110, 106), (214, 212, 206), rng, scale=0.7)
    b = _paint(b, B.grow(jacket.astype(np.float32), 32), boucle, k=0.4, flatten=3)
    b = _paint(b, soft(shirt.astype(np.float32), 0.6), _checks(B, 0.032, (236, 234, 228), (18, 18, 20)), k=0.25)
    legs = B.where(B.part('Thigh', 'Calf', 'Pelvis') & (B.z <= pel - 0.11) & (B.z > 0.12))
    b = recolour(b, B.grow(legs.astype(np.float32), 24), (26, 26, 29), contrast=0.8)
    H, S, V = hsv(b); red = B.grow(B.where(((H < 15) | (H > 340)) & (S > 0.45) & ~hands).astype(np.float32), 4)   # the henley's red, wherever it is left
    b = _paint(b, soft(red, 0.8), boucle, k=0.3)
    feet = B.where(B.part('Foot', 'Toe') | (B.part('Calf') & (B.z <= 0.12)))
    b = recolour(b, B.grow(feet.astype(np.float32), 6), (20, 19, 20), contrast=0.9, flatten=1.0)
    made['kramer'].append(save(b, 'kramer', 'm011_body_color.tga'))
    made['kramer'].append(_flat_normals('Male_Adult_06', 'm011_body_normal.tga', 'kramer', B.grow(upper.astype(np.float32), 3) * 0.7))

    # Elaine (Business_Female_03): her big dark curls; the blazer red over a cream blouse, the cream skirt with small red
    # flowers, black tights and boots
    o = load('Business_Female_03', 'f016_opacity_color.tga'); oV = hsv(o)[2]
    made['elaine'] = [save(recolour(o, soft((oV > 0.02).astype(np.float32), 1), (40, 28, 21), contrast=1.3), 'elaine', 'f016_opacity_color.tga',
                           load_alpha('Business_Female_03', 'f016_opacity_color.tga'))]
    h = load('Business_Female_03', 'f016_head_color.tga'); Hd = Body('f016_head_color.tga'); H, S, V = hsv(h)
    brow, line, ear = _hairline(Hd, front=0.045)
    hm = soft(Hd.grow(Hd.where((Hd.z > line) & ~ear).astype(np.float32), 3), 1.4) * smooth(0.5, 0.35, V)
    h = recolour(h, hm, (40, 28, 21), contrast=1.2)
    made['elaine'].append(save(h, 'elaine', 'f016_head_color.tga'))
    b = load('Business_Female_03', 'f016_body_color.tga'); B = Body('f016_body_color.tga'); H, S, V = hsv(b)
    J = B.J; neck, pel = J['Bip01 Neck'][2], J['Bip01 Pelvis'][2]; knee = J['Bip01 L Calf'][2]
    hem = pel - 0.1                                                           # the blazer's hem, over the hips
    hands = B.part('Hand', 'Finger') & (S > 0.15) & (H < 40) & (V > 0.42)    # skin is lighter than the blazer's brown cuffs
    upper = B.where(~hands & B.part('Spine', 'Clavicle', 'Neck', 'UpperArm', 'Forearm', 'Pelvis', 'Hand', 'Thigh') & (B.z > hem) & ~(B.part('Neck') & (B.z > neck - 0.03)))
    depth = np.clip((neck - B.z) / 0.3, 0, 1)
    blouse = B.where(upper & (B.y < -0.02) & (np.abs(B.x) < 0.012 + 0.04 * (1 - depth)) & (B.z > neck - 0.26))
    b = _paint(b, B.grow((upper & ~blouse).astype(np.float32), 32), np.array([176, 36, 34], np.float32)[None, None] / 255 * np.ones(b.shape, np.float32), k=0.55, flatten=6)
    b = recolour(b, soft(blouse.astype(np.float32), 0.7), (232, 224, 208), contrast=0.3, flatten=2.0)
    skirt = B.where(B.part('Pelvis', 'Thigh', 'Calf', 'Spine') & (B.z <= hem) & (B.z > knee - 0.04))
    cream = np.array([222, 208, 182], np.float32)[None, None] / 255 * np.ones(b.shape, np.float32)
    flowers = np.clip((noise(b.shape, 1.2, 33) - 0.78) * 6, 0, 1) * (noise(b.shape, 8, 34) > 0.35)
    leaves = np.clip((noise(b.shape, 1.0, 35) - 0.8) * 6, 0, 1) * 0.7
    cream = cream * (1 - flowers[..., None] - leaves[..., None]) + np.array([180, 50, 56], np.float32) / 255 * flowers[..., None] + np.array([96, 120, 80], np.float32) / 255 * leaves[..., None]
    b = _paint(b, B.grow(skirt.astype(np.float32), 24), cream, k=0.35)
    tights = B.where(B.part('Calf', 'Thigh') & (B.z <= knee - 0.04) & (B.z > 0.13))   # black tights below the skirt
    b = recolour(b, B.grow(tights.astype(np.float32), 12), (22, 20, 22), contrast=0.6, flatten=1.0)
    boots = B.where(B.part('Foot', 'Toe', 'Calf') & (B.z <= 0.13))
    b = recolour(b, B.grow(boots.astype(np.float32), 6), (24, 21, 21), contrast=0.8)
    made['elaine'].append(save(b, 'elaine', 'f016_body_color.tga'))
    made['elaine'].append(_flat_normals('Business_Female_03', 'f016_body_normal.tga', 'elaine', B.grow(skirt.astype(np.float32), 3) * 0.7))
    for k, v in made.items(): print(k, [os.path.basename(p) for p in v])


def _wrist_band(b, B, side, colour, w0, w1, k=0.5):
    """A metal band round a wrist (a watch, a bracelet): texels of the forearm and hand between w0 and w1 metres up the
    arm from the hand joint (the arms lie along x in the rest pose: the left at +x)."""
    hx = B.J[f'Bip01 {side} Hand'][0]; s = (hx - B.x) if side == 'L' else (B.x - hx)
    m = B.where(B.part(f'{side} Forearm', f'{side} Hand') & (s > w0) & (s < w1))
    shine = 0.75 + 0.5 * noise(b.shape, 0.8, 71 if side == 'L' else 72)
    return b * (1 - soft(m.astype(np.float32), 0.5)[..., None]) + np.array(colour, np.float32) / 255 * shine[..., None] * soft(m.astype(np.float32), 0.5)[..., None] * k / 0.5


def the_sopranos():
    """Dr. Melfi's office in "Denial, Anger, Acceptance" (season one, costumes after Juliet Polcsa): Tony in a black
    short-sleeve knit shirt with a tonal pattern, black trousers and belt, black shoes, his gold watch and bracelet;
    Melfi in an oatmeal tweed skirt suit over a black top, a long brown patterned scarf, sheer tights, black pumps,
    her rimless glasses, her bob gone auburn."""
    rng = np.random.default_rng(31)
    made = {}

    # Tony (Male_Adult_14: the same photographed face as Medical_Male_03, without the moustache): the receding hair
    # near black, the skin olive, a five o'clock shadow, darker brows, brown eyes
    h = load('Male_Adult_14', 'm012_head_color.tga'); Hd = Body('m012_head_color.tga'); H, S, V = hsv(h)
    brow, line, ear = _hairline(Hd, front=0.05)
    eyeballs = np.isin(Hd.bone, [i for i, g in enumerate(Hd.groups) if g in ('Bip01 LEye', 'Bip01 REye')]) & Hd.ok   # not the brows ('Eyebrow')
    h = skin_tone(h, Hd.grow(Hd.ok.astype(np.float32)) * (1 - eyeballs), (0.93, 0.85, 0.74))
    hair = Hd.where(((Hd.z > brow - 0.075) & ~ear & ~((Hd.y < -0.05) & (Hd.z < brow + 0.03) & (np.abs(Hd.x) < 0.06))) | (Hd.z > line - 0.004))
    hm = soft(Hd.grow(hair.astype(np.float32), 3), 1.2) * smooth(0.62, 0.4, V)                # the hair is darker than the scalp
    h = recolour(h, hm, (34, 26, 22), contrast=1.25)
    h = _hair_on(h, _beard_mask(Hd, cheeks=0.55), rng, (40, 33, 28), 0.26)                    # shaved that morning, dark beard
    H, S, V = hsv(h)
    iris = (eyeballs & ~((V > 0.7) & (S < 0.2))).astype(np.float32)
    h = recolour(h, soft(iris, 0.5), (66, 44, 30), contrast=1.0)
    made['tony'] = [save(h, 'tony', 'm012_head_color.tga')]
    b = load('Male_Adult_14', 'm012_body_color.tga'); B = Body('m012_body_color.tga'); H, S, V = hsv(b)
    J = B.J; pel = J['Bip01 Pelvis'][2]; belt = pel + 0.09
    hands = B.part('Hand', 'Finger') & (S > 0.15) & (H < 45)
    cuffs = B.where(B.part('Hand', 'Forearm') & ~hands & (np.abs(B.x) > J['Bip01 L Hand'][0] - 0.07))   # the long sleeves' cuffs: bare wrists now
    shirt = B.where(~hands & ~cuffs & B.part('Spine', 'Clavicle', 'Neck', 'UpperArm', 'Forearm', 'Pelvis') & (B.z > belt) & (S < 0.2))
    knit = 0.82 + 0.3 * (np.sin(np.nan_to_num(B.z) * 260 + 8 * np.abs(np.sin(np.nan_to_num(B.x) * 90))) > 0.6)   # a tonal zigzag rib
    knit = knit * (0.9 + 0.2 * noise(b.shape, 0.7, 73))
    b = _paint(b, B.grow(shirt.astype(np.float32), 8), np.array([30, 30, 33], np.float32)[None, None] / 255 * knit[..., None], k=0.45, flatten=6)
    bare = _sleeves(B, 0.4) | cuffs
    b = _skin_paint(b, B, bare, rng, warm=(0.95, 0.86, 0.76))
    hair_arm = np.clip((noise(b.shape, 0.5, 74) - 0.55) * 3, 0, 1) * soft(B.grow(bare.astype(np.float32), 2), 1.0)
    b = b * (1 - 0.35 * hair_arm[..., None]) + np.array([40, 30, 24], np.float32) / 255 * 0.35 * hair_arm[..., None]
    b = skin_tone(b, B.grow(hands.astype(np.float32), 3), (0.93, 0.85, 0.74))
    made['tony'].append(_flat_normals('Male_Adult_14', 'm012_body_normal.tga', 'tony', np.maximum(B.grow(bare.astype(np.float32), 3), B.grow(shirt.astype(np.float32)) * 0.7)))
    khaki = (H > 22) & (H < 55) & (S > 0.18) & (V > 0.2)
    legs = B.where(B.part('Thigh', 'Calf', 'Pelvis', 'Spine') & ((B.z <= belt) | khaki) & (B.z > 0.1) & ~hands & ~shirt)
    b = recolour(b, B.grow(legs.astype(np.float32), 8), (26, 26, 29), contrast=0.75, flatten=1.0)
    bl = B.where(B.part('Pelvis', 'Spine', 'Thigh') & (B.z > belt - 0.035) & (B.z < belt + 0.004))
    bl |= B.where(B.part('Pelvis', 'Spine', 'Thigh') & (np.abs(B.z - belt) < 0.07) & (H < 40) & (S > 0.25) & (V < 0.42))   # his own brown belt
    b = recolour(b, B.grow(bl.astype(np.float32), 1), (16, 15, 16), contrast=0.6)
    b = recolour(b, soft(B.where(bl & (np.abs(B.x) < 0.016) & (B.y < 0)).astype(np.float32), 0.6), (176, 174, 168), contrast=0.4)   # the buckle
    feet = B.where(B.part('Foot', 'Toe') | (B.part('Calf') & (B.z <= 0.1)))
    b = recolour(b, B.grow(feet.astype(np.float32), 6), (17, 16, 17), contrast=0.9, flatten=0.8)
    b = _wrist_band(b, B, 'L', (196, 156, 74), 0.012, 0.034)                                 # the gold watch
    b = _wrist_band(b, B, 'R', (206, 166, 82), 0.014, 0.022)                                 # the gold bracelet
    b = leftover_black(b, (26, 26, 29))
    made['tony'].append(save(b, 'tony', 'm012_body_color.tga'))

    # Melfi (Business_Female_02, made lean in the face): the bob auburn, the lipstick muted; the burgundy jacket becomes
    # oatmeal tweed, the striped top black with the scarf over it, the trousers a tweed skirt to the knee and sheer
    # tights below (the legs are slimmed in the mesh), black pumps
    auburn = (72, 42, 29)
    h = load('Business_Female_02', 'f015_head_color.tga'); Hd = Body('f015_head_color.tga'); H, S, V = hsv(h)
    brow = Hd.J['Bip01 MMiddleEyebrow'][2]
    # in the layout (as Helly's): the face and throat, the eye and mouth islands keep their colour; the rest that is
    # blond is hair (the scalp, the locks along the sides and the cards' islands below)
    protect = np.maximum.reduce([ellipse(h.shape, 0.5, 0.37, 0.215, 0.235), region(h.shape, 0.0, 0.5, 1.0, 0.72), region(h.shape, 0.0, 0.58, 0.14, 1.0),
                                 region(h.shape, 0.1, 0.84, 0.36, 1.0)])
    blond = (H > 16) & (H < 60) & (S > 0.14) & (V > 0.1)
    hair = (blond & (protect < 0.5)) | Hd.where((Hd.z > brow + 0.07) & (Hd.y > -0.02))
    h = recolour(h, soft(hair.astype(np.float32), 0.8), auburn, contrast=1.15)
    lips = (ellipse(h.shape, 0.5, 0.405, 0.075, 0.035) > 0.5) & ((H < 20) | (H > 325)) & (S > 0.3)
    lm = soft(lips.astype(np.float32), 1.0)[..., None]; L = lum(h)[..., None]
    h = h * (1 - lm) + (L + (h - L) * 0.6) * 0.95 * lm                                          # the lipstick muted, not red
    made['melfi'] = [save(h, 'melfi', 'f015_head_color.tga')]
    o = load('Business_Female_02', 'f015_opacity_color.tga'); oV = hsv(o)[2]
    made['melfi'].append(save(recolour(o, soft((oV > 0.03).astype(np.float32), 1), auburn, contrast=1.2), 'melfi', 'f015_opacity_color.tga',
                              load_alpha('Business_Female_02', 'f015_opacity_color.tga')))
    b = load('Business_Female_02', 'f015_body_color.tga'); B = Body('f015_body_color.tga'); H, S, V = hsv(b)
    J = B.J; neck, pel = J['Bip01 Neck'][2], J['Bip01 Pelvis'][2]; knee = J['Bip01 L Calf'][2]
    hands = B.part('Hand', 'Finger') & (S > 0.15) & (H < 40) & (V > 0.4)
    trousers = B.part('Pelvis', 'Thigh', 'Calf', 'Spine') & (V < 0.3) & (S < 0.45) & (B.z < pel + 0.03)   # dark, under the jacket's hem
    upper = B.where(~hands & B.part('Spine', 'Clavicle', 'Neck', 'UpperArm', 'Forearm', 'Pelvis', 'Hand') & (B.z > pel - 0.12) & ~trousers)
    depth = np.clip((neck - B.z) / 0.3, 0, 1)
    front = B.where((B.y < -0.02) & (np.abs(B.x) < 0.014 + 0.05 * (1 - depth)) & (B.z > neck - 0.27) & B.part('Spine', 'Clavicle', 'Neck'))
    collar = B.where((B.z > neck - 0.012) & ~B.part('Hand', 'UpperArm', 'Forearm'))            # the turtleneck's collar, all round
    top = (front | collar) & ~B.part('Hand', 'UpperArm', 'Forearm')                           # the striped top: black now, the scarf over it
    jacket = upper & ~top
    tweed = _weave(B, (150, 132, 108), (206, 194, 170), rng, scale=0.8)
    b = _paint(b, B.grow(jacket.astype(np.float32), 24), tweed, k=0.35, flatten=8)
    scarf = B.where(top & (B.y < -0.02) & (np.abs(np.abs(B.x) - (0.03 + 0.022 * depth)) < 0.02))   # its two ends, down either side
    scarf |= B.where(collar & (B.z < neck + 0.005))                                          # and round the neck
    paisley = np.array([70, 48, 36], np.float32)[None, None] / 255 * (0.6 + 0.8 * noise(b.shape, 1.6, 75)[..., None])
    b = recolour(b, soft(top.astype(np.float32), 0.6), (18, 17, 18), contrast=0.3, flatten=4)
    b = _paint(b, soft(scarf.astype(np.float32), 0.8), paisley, k=0.4)
    skirt = B.where(B.part('Pelvis', 'Thigh', 'Spine') & (B.z <= pel - 0.12 + 0.002) & (B.z > knee + 0.02)) | B.where(trousers & (B.z > knee + 0.02))
    b = _paint(b, B.grow(skirt.astype(np.float32), 16), tweed, k=0.3, flatten=8)
    H, S, V = hsv(b)                                                                          # the burgundy, wherever it is left
    red = B.where(((H < 20) | (H > 320)) & (S > 0.3) & (V < 0.55) & ~B.part('Hand', 'Finger', 'Head', 'Foot', 'Toe') & (B.z > knee))
    b = _paint(b, soft(B.grow(red.astype(np.float32), 2), 0.8), tweed, k=0.3)
    hem = B.where(B.part('Thigh', 'Calf') & (np.abs(B.z - (knee + 0.025)) < 0.006))
    b = b * (1 - 0.35 * soft(hem.astype(np.float32), 0.6)[..., None])                       # the hem's shadow
    tone = np.median(b[B.where(hands)], 0) * 255 if hands.any() else np.array([214, 168, 146])
    legs = B.where(B.part('Calf', 'Thigh', 'Foot') & (B.z <= knee + 0.02) & (B.z > 0.085))
    b = recolour(b, B.grow(legs.astype(np.float32), 12), tuple(tone * np.array([0.86, 0.8, 0.76])), contrast=0.35, flatten=2.0)   # sheer tights
    shoes = B.where(B.part('Foot', 'Toe', 'Calf') & (B.z <= 0.085))
    b = recolour(b, B.grow(shoes.astype(np.float32), 6), (16, 15, 16), contrast=0.8)
    made['melfi'].append(save(b, 'melfi', 'f015_body_color.tga'))
    made['melfi'].append(_flat_normals('Business_Female_02', 'f015_body_normal.tga', 'melfi', np.maximum(B.grow(legs.astype(np.float32), 4), B.grow(skirt.astype(np.float32), 4) * 0.8)))
    for k, v in made.items(): print(k, [os.path.basename(p) for p in v])


def _moustache(Hd, width=0.033, low=-0.003, high=0.012):
    """A full moustache over the upper lip, to the mouth's corners (heights relative to the upper lip joint)."""
    J = Hd.J; ax = np.abs(Hd.x)
    lip, nose = J['Bip01 MUpperLip'][2], J['Bip01 MNose'][2]
    m = smooth(lip + low - 0.004, lip + low + 0.002, Hd.z) * smooth(min(nose - 0.004, lip + high + 0.004), lip + high - 0.002, Hd.z)
    m = m * smooth(width + 0.006, width - 0.006, ax) * smooth(0.0, -0.02, Hd.y - J['Bip01 MUpperLip'][1] - 0.02)
    corners = smooth(lip + low + 0.004, lip + low - 0.01, Hd.z) * smooth(width + 0.004, width - 0.006, ax) * smooth(width - 0.016, width - 0.006, ax)   # down a little at the corners
    m = np.maximum(m, corners * smooth(lip - 0.022, lip - 0.012, Hd.z) * smooth(0.0, -0.02, Hd.y - J['Bip01 MUpperLip'][1] - 0.02))
    return blur(np.where(Hd.ok, m, 0).astype(np.float32), 1.5)


def _stripes(B, period, lines, base, along='x'):
    """Pinstripes on the body: `lines` [(offset 0..1, width 0..1, colour)] repeating every `period` metres across x
    (vertical stripes) or up z (horizontal bands)."""
    u = (np.nan_to_num(B.x if along == 'x' else B.z) / period) % 1.0
    c = np.array(base, np.float32)[None, None] / 255 * np.ones(B.x.shape + (3,), np.float32)
    for off, w, col in lines:
        d = np.abs(((u - off + 0.5) % 1.0) - 0.5)
        m = (np.clip((w / 2 - d) / (w * 0.35 + 1e-4) + 0.5, 0, 1) * B.ok)[..., None]   # off the body (padding): the base
        c = c * (1 - m) + np.array(col, np.float32)[None, None] / 255 * m
    return c


def _roses(b, B, mask, rng, n=40, r=(0.03, 0.05)):
    """Big printed roses scattered over the body where `mask` is (a hoodie's shoulders and sleeves): `n` blooms, each a
    red disc `r` metres across with dark petal lines curling round its heart, white leaves at their edges; placed in
    body space, so a bloom crosses the texture's seams whole."""
    ids = np.argwhere(mask); pick = ids[rng.choice(len(ids), n, replace=False)]
    C = B.pos[pick[:, 0], pick[:, 1]]; R = rng.uniform(*r, n).astype(np.float32)
    yy, xx = np.where((B.grow(mask.astype(np.float32), 3) > 0.5) & B.ok)
    P = B.pos[yy, xx]; d = np.linalg.norm(P[:, None, :] - C[None, :, :], axis=2) / R[None, :]
    k = d.argmin(1); dn = d[np.arange(len(k)), k]
    rose = np.clip((1 - dn) * 8, 0, 1)
    off = P - C[k]; ang = np.arctan2(off[:, 2], off[:, 0] + off[:, 1])
    petal = (np.sin(dn * 16 + ang * 3) > 0.55) & (dn < 0.92)
    heart = dn < 0.28
    leaf = np.clip((dn - 1.0) * 14, 0, 1) * np.clip((1.18 - dn) * 14, 0, 1) * (np.sin(ang * 4) > 0.75)
    col = np.where(heart[:, None], [0.32, 0.03, 0.05], np.where(petal[:, None], [0.4, 0.04, 0.06], [0.68, 0.1, 0.13]))
    out = b.copy(); cur = out[yy, xx]
    cur = cur * (1 - rose[:, None]) + col * rose[:, None]
    cur = cur * (1 - 0.85 * leaf[:, None]) + np.array([0.86, 0.85, 0.82]) * 0.85 * leaf[:, None]
    out[yy, xx] = cur
    return out


def breaking_bad():
    """Saul's office in "Mandala" (season two; costumes after Kathleen Detoro), Huell from season four: Walt in a
    black cotton zip jacket open over a lavender shirt with fine purple and white stripes, dark trousers, his
    Wallabees; Jesse in a black hoodie printed with red roses over a blue tee, baggy jeans, dark sneakers (his beanie is
    modelled); Saul in a charcoal pinstripe suit, a lavender shirt, a red diamond tie and a red pocket square, a gold
    lapel pin; Huell in a black jacket open over a striped polo, dark trousers."""
    rng = np.random.default_rng(43)
    made = {}

    # Walt (Business_Male_04, bald): a ginger-brown moustache going grey; the waistcoat and the shirt's sleeves become the
    # open black jacket, the shirt's front and collar lavender with fine stripes, a white undershirt at the throat; the
    # trousers dark brown-grey; brown Wallabees on crepe soles
    h = load('Business_Male_04', 'm015_head_color.tga'); Hd = Body('m015_head_color.tga')
    mo = _moustache(Hd, width=0.037, low=-0.005, high=0.017)
    h = recolour(h, mo * 0.85, (118, 82, 54), contrast=0.6)                                 # the moustache's body
    h = _hair_on(h, mo, rng, (128, 88, 56), 1.0)
    h = _hair_on(h, mo, rng, (104, 70, 46), 0.6)
    h = _hair_on(h, mo * (noise(h.shape, 0.8, 91) > 0.62), rng, (176, 160, 140), 0.5)     # the grey in it
    h = _hair_on(h, _beard_mask(Hd, moustache=False, cheeks=0.3), rng, (120, 100, 84), 0.12)   # a faint shadow
    made['walt'] = [save(h, 'walt', 'm015_head_color.tga')]
    b = load('Business_Male_04', 'm015_body_color.tga'); B = Body('m015_body_color.tga'); H, S, V = hsv(b)
    J = B.J; neck, pel = J['Bip01 Neck'][2], J['Bip01 Pelvis'][2]; belt = pel + 0.09
    hands = B.part('Hand', 'Finger') & (S > 0.12) & (H < 45)
    upper = B.where(~hands & B.part('Spine', 'Clavicle', 'Neck', 'UpperArm', 'Forearm', 'Pelvis', 'Hand') & (B.z > belt - 0.04) & ~(B.part('Neck') & (B.z > neck + 0.035)))
    depth = np.clip((neck - B.z) / 0.45, 0, 1)
    front = B.where(upper & (B.y < -0.03) & (np.abs(B.x) < 0.03 + 0.05 * depth) & (B.z > belt - 0.02))   # the jacket hangs open
    collar = B.where(upper & B.part('Neck', 'Spine2', 'Clavicle') & (B.z > neck - 0.045) & (B.y < 0.0) & (np.abs(B.x) < 0.075))
    shirt = front | collar
    jacket = upper & ~shirt
    b = recolour(b, B.grow(jacket.astype(np.float32), 24), (26, 26, 28), contrast=0.75, flatten=5)
    b = leftover_black(b, (26, 26, 28), keep=B.grow(B.part('Hand', 'Finger').astype(np.float32), 2))   # before the shirt: lavender reads as 'pale grey'
    lav = _stripes(B, 0.011, [(0.0, 0.16, (106, 72, 146)), (0.5, 0.1, (236, 232, 242))], (172, 154, 202))
    b = _paint(b, soft(shirt.astype(np.float32), 0.7), lav, k=0.45, flatten=4)
    tee = B.where(shirt & (np.abs(B.x) < 0.016) & (B.z > neck - 0.07) & (B.z < neck - 0.02) & (B.y < -0.05))
    b = recolour(b, soft(tee.astype(np.float32), 0.6), (226, 224, 218), contrast=0.3)
    legs = B.where(B.part('Thigh', 'Calf', 'Pelvis', 'Spine') & (B.z < belt - 0.04) & (B.z > 0.1) & ~hands)
    b = recolour(b, B.grow(legs.astype(np.float32), 16), (58, 50, 44), contrast=0.7, flatten=2.0)
    feet = B.where(B.part('Foot', 'Toe') | (B.part('Calf') & (B.z <= 0.085)))
    b = recolour(b, B.grow(feet.astype(np.float32), 6), (100, 70, 44), contrast=0.6, flatten=2.0)
    b = recolour(b, soft(B.where(feet & (B.z < 0.028)).astype(np.float32), 0.6), (188, 154, 108), contrast=0.3)   # crepe soles
    made['walt'].append(save(b, 'walt', 'm015_body_color.tga'))
    made['walt'].append(_flat_normals('Business_Male_04', 'm015_body_normal.tga', 'walt', np.maximum(B.grow(shirt.astype(np.float32), 3) * 0.6, B.grow(jacket.astype(np.float32), 3) * 0.5)))

    # Jesse (Male_Adult_20): a little stubble; the brown hoodie black, red roses and white leaves over the shoulders and
    # down the sleeves, a blue tee at the neck; the jeans a deeper indigo; dark sneakers, white soles
    h = load('Male_Adult_20', 'm027_head_color.tga'); Hd = Body('m027_head_color.tga')
    h = _hair_on(h, _beard_mask(Hd, cheeks=0.45), rng, (70, 52, 38), 0.22)
    brow, line, ear = _hairline(Hd, front=0.05)
    hm = soft(Hd.grow(Hd.where((Hd.z > line - 0.004) & ~ear).astype(np.float32), 3), 1.4) * smooth(0.72, 0.5, hsv(h)[2])
    h = recolour(h, hm, (70, 54, 40), contrast=1.1)                                           # his hair a mid brown
    made['jesse'] = [save(h, 'jesse', 'm027_head_color.tga')]
    b = load('Male_Adult_20', 'm027_body_color.tga'); B = Body('m027_body_color.tga'); H, S, V = hsv(b)
    J = B.J; neck, pel = J['Bip01 Neck'][2], J['Bip01 Pelvis'][2]
    hands = B.part('Hand', 'Finger') & (S > 0.12) & (H < 45) & (V > 0.25)
    denim = (H > 180) & (H < 250) & (S > 0.1)
    hoodie = B.where(~hands & ~denim & B.part('Spine', 'Clavicle', 'Neck', 'UpperArm', 'Forearm', 'Pelvis', 'Hand', 'Head') & (B.z > pel - 0.1) & ~(B.part('Head') & (B.z > neck + 0.06)))
    b = recolour(b, B.grow(hoodie.astype(np.float32), 24), (22, 22, 25), contrast=0.85, flatten=2.5)
    sleeves = B.where(hoodie & (B.part('UpperArm', 'Forearm') | (B.part('Clavicle', 'Spine2') & (np.abs(B.x) > 0.08))))
    b = _roses(b, B, sleeves, rng, n=46)
    tee = B.where(hoodie & (B.y < -0.03) & (np.abs(B.x) < 0.045) & (B.z > neck - 0.05) & (B.z < neck + 0.01))
    b = recolour(b, soft(tee.astype(np.float32), 0.8), (64, 104, 168), contrast=0.4)
    H, S, V = hsv(b)
    jeans = B.where(B.part('Thigh', 'Calf', 'Pelvis') & (H > 180) & (H < 250) & (S > 0.08) & (B.z > 0.06))
    b = recolour(b, B.grow(jeans.astype(np.float32), 8), (52, 72, 108), contrast=0.9)
    feet = B.where(B.part('Foot', 'Toe'))
    b = recolour(b, B.grow(feet.astype(np.float32), 6), (34, 34, 38), contrast=0.7)
    b = recolour(b, soft(B.where(feet & (B.z < 0.025)).astype(np.float32), 0.6), (226, 224, 218), contrast=0.3)
    made['jesse'].append(save(b, 'jesse', 'm027_body_color.tga'))

    # Saul (Business_Male_03): the hair a lighter reddish brown, gone back at the temples; the suit charcoal with an
    # olive cast and a fine chalk stripe, the shirt lavender, the tie red with black and cream diamonds, a red pocket
    # square, a gold pin on the lapel
    hair_c = (82, 58, 42)
    h = load('Business_Male_03', 'm020_head_color.tga'); Hd = Body('m020_head_color.tga'); H, S, V = hsv(h)
    brow, line, ear = _hairline(Hd, front=0.062)
    ax = np.abs(Hd.x)
    temples = Hd.where((Hd.y < -0.04) & (ax > 0.028) & (ax < 0.062) & (Hd.z > brow + 0.035) & (Hd.z < brow + 0.06 + 0.5 * (ax - 0.028)))   # the receding corners
    face = Hd.where((Hd.y < -0.05) & (Hd.z < brow + 0.035) & (ax < 0.06))
    fore = Hd.where((Hd.y < -0.06) & (ax < 0.03) & (Hd.z > brow + 0.012) & (Hd.z < brow + 0.035))   # the forehead's own skin
    tone = np.median(h[fore], 0) if fore.any() else np.array([0.75, 0.58, 0.48])
    skin = tone[None, None, :] * (0.92 + 0.14 * noise(h.shape, 2.5, 96)[..., None])
    tm = soft(Hd.grow(temples.astype(np.float32), 2), 4.0)
    h = h * (1 - tm[..., None]) + skin * tm[..., None]
    hm = soft(Hd.grow(Hd.where((Hd.z > brow - 0.075) & ~ear & ~face & (V < 0.35)).astype(np.float32), 3), 1.2) * (1 - tm)
    h = recolour(h, hm, hair_c, contrast=1.2)
    made['saul'] = [save(h, 'saul', 'm020_head_color.tga')]
    o = load('Business_Male_03', 'm020_opacity_color.tga'); oV = hsv(o)[2]
    al = load_alpha('Business_Male_03', 'm020_opacity_color.tga'); Op = Body('m020_opacity_color.tga')
    oax = np.abs(Op.x)
    receding = Op.grow(Op.where((Op.y < -0.04) & (oax > 0.026) & (oax < 0.07) & (Op.z > brow + 0.03) & (Op.z < brow + 0.075 + 0.5 * (oax - 0.026))).astype(np.float32), 3)
    made['saul'].append(save(recolour(o, soft((oV > 0.03).astype(np.float32), 1), hair_c, contrast=1.25), 'saul', 'm020_opacity_color.tga', al * (1 - receding)))
    b = load('Business_Male_03', 'm020_body_color.tga'); B = Body('m020_body_color.tga'); H, S, V = hsv(b)
    J = B.J; neck, pel = J['Bip01 Neck'][2], J['Bip01 Pelvis'][2]
    hands = B.part('Hand', 'Finger') & (S > 0.12) & (H < 45) & (V > 0.3)
    green = (H > 120) & (H < 200) & (S > 0.12)
    white = (V > 0.5) & (S < 0.15) & ~hands
    suit = B.where(~hands & ~white & ~green & ~B.part('Head', 'Foot', 'Toe') & (B.z > 0.1))
    chalk = _stripes(B, 0.013, [(0.0, 0.07, (62, 62, 60))], (44, 44, 43))                  # faint: at 1:6 it only greys the cloth
    b = _paint(b, B.grow(suit.astype(np.float32), 16), chalk, k=0.7, flatten=2.0)
    b = recolour(b, soft(B.grow(B.where(white).astype(np.float32), 2), 0.6), (186, 168, 212), contrast=0.5)
    tie = B.where(green & ~hands) | B.where((B.y < -0.06) & (np.abs(B.x) < 0.04) & (B.z > pel + 0.1) & (B.z < neck - 0.02) & green)
    u, v = np.nan_to_num(B.x) / 0.022, np.nan_to_num(B.z) / 0.03
    dia = ((np.abs((u % 1) - 0.5) + np.abs((v % 1) - 0.5)) < 0.32)
    inner = ((np.abs((u % 1) - 0.5) + np.abs((v % 1) - 0.5)) < 0.16)
    tie_c = np.where(dia[..., None], np.where(inner[..., None], np.array([226, 210, 176], np.float32) / 255, np.array([22, 18, 20], np.float32) / 255), np.array([158, 30, 36], np.float32) / 255)
    b = _paint(b, soft(B.grow(tie.astype(np.float32), 2), 0.6), tie_c, k=0.4)
    pocket = B.where(suit & (B.y < -0.06) & (np.abs(B.x - 0.085) < 0.022) & (np.abs(B.z - (neck - 0.15)) < 0.012))   # over his heart
    b = recolour(b, soft(pocket.astype(np.float32), 0.6), (176, 30, 34), contrast=0.4)
    pin = B.where(suit & (B.y < -0.06) & (np.hypot(B.x - 0.075, B.z - (neck - 0.075)) < 0.006))
    b = recolour(b, soft(pin.astype(np.float32), 0.4), (210, 170, 70), contrast=0.3)
    made['saul'].append(save(b, 'saul', 'm020_body_color.tga'))

    # Huell (Male_Adult_12, made very heavy): the head shaved, a thin moustache and a shadow on the chin; the denim
    # jacket black nylon, the white tee a polo in blue, lilac and pink stripes, the jeans dark, black shoes
    h = load('Male_Adult_12', 'm007_head_color.tga'); Hd = Body('m007_head_color.tga')
    h = _bald(h, Hd, shine=0.22)
    h = _hair_on(h, _moustache(Hd, width=0.028, low=0.0, high=0.007), rng, (18, 14, 12), 0.8)
    h = _hair_on(h, _beard_mask(Hd, moustache=False, cheeks=0.0), rng, (20, 16, 14), 0.35)
    made['huell'] = [save(h, 'huell', 'm007_head_color.tga')]
    b = load('Male_Adult_12', 'm007_body_color.tga'); B = Body('m007_body_color.tga'); H, S, V = hsv(b)
    J = B.J; neck, pel = J['Bip01 Neck'][2], J['Bip01 Pelvis'][2]
    hands = B.part('Hand', 'Finger') & ~((H > 170) & (H < 270) & (S > 0.08))
    tee = B.where((V > 0.55) & (S < 0.25) & B.part('Spine', 'Neck', 'Clavicle', 'Pelvis') & (B.z > pel + 0.08))
    jacket = B.where(~hands & ~tee & B.part('Spine', 'Clavicle', 'Neck', 'UpperArm', 'Forearm', 'Hand', 'Pelvis') & (B.z > pel + 0.02))
    b = recolour(b, B.grow(jacket.astype(np.float32), 16), (22, 22, 26), contrast=0.5, flatten=6)
    b = leftover_black(b, (22, 22, 26), keep=B.grow(B.part('Hand', 'Finger').astype(np.float32), 2))
    polo = _stripes(B, 0.085, [(0.1, 0.22, (70, 96, 160)), (0.36, 0.16, (140, 118, 176)), (0.6, 0.16, (204, 140, 164)), (0.82, 0.1, (226, 226, 232))], (44, 62, 120), along='z')
    b = _paint(b, soft(tee.astype(np.float32), 0.7), polo, k=0.35, flatten=3)
    legs = B.where(B.part('Thigh', 'Calf', 'Pelvis') & (B.z <= pel + 0.02) & (B.z > 0.12) & ~tee)
    b = recolour(b, B.grow(legs.astype(np.float32), 16), (32, 34, 42), contrast=0.6, flatten=2)
    feet = B.where(B.part('Foot', 'Toe') | (B.part('Calf') & (B.z <= 0.12)))
    b = recolour(b, B.grow(feet.astype(np.float32), 6), (22, 22, 24), contrast=0.8)
    made['huell'].append(save(b, 'huell', 'm007_body_color.tga'))
    made['huell'].append(_flat_normals('Male_Adult_12', 'm007_body_normal.tga', 'huell', np.maximum(B.grow(jacket.astype(np.float32), 3) * 0.7, B.grow(legs.astype(np.float32), 3) * 0.6)))
    for k, v in made.items(): print(k, [os.path.basename(p) for p in v])


def _bow_tie(B, neck, colour=(14, 14, 16), w=0.046, h=0.02, at=0.03):
    """A black bow tie under the collar: two wings widening out from a narrow knot, `at` below the neck joint."""
    zc = neck - at; ax = np.abs(np.nan_to_num(B.x)); dz = np.abs(np.nan_to_num(B.z) - zc)
    wing = (ax > 0.008) & (ax < w) & (dz < h * (0.32 + 0.68 * smooth(0.008, w, ax)) / 2)
    knot = (ax <= 0.009) & (dz < h * 0.32)
    return B.where((wing | knot) & (B.y < -0.03))


def _shirt_front(B, neck, top, bottom, half_top, half_bottom):
    """The white of a shirt between a jacket's (or waistcoat's) lapels: a V from `half_top` either side of the middle
    at z = top down to `half_bottom` at z = bottom (heights as offsets below the neck joint)."""
    z = np.nan_to_num(B.z); t = np.clip(((neck - z) - top) / (bottom - top), 0, 1)
    half = half_top + (half_bottom - half_top) * t
    return B.where((np.abs(np.nan_to_num(B.x)) < half) & (B.y < -0.02) & (neck - z > top - 0.02) & (neck - z < bottom))


def _studs(b, B, neck, zs, colour=(30, 28, 26), r=0.0045):
    """Small dark shirt studs down the middle of the front."""
    for dz in zs:
        m = B.where((np.hypot(np.nan_to_num(B.x), np.nan_to_num(B.z) - (neck - dz)) < r) & (B.y < -0.03))
        b = recolour(b, soft(m.astype(np.float32), 0.5), colour, contrast=0.3)
    return b


def the_godfather():
    """Don Corleone's study on the wedding day, after Anna Hill Johnstone's costumes: the Don in a black single-breasted
    dinner jacket with satin lapels over a black waistcoat cut in a low V, the white stiff front with its studs, a wing
    collar and a black bow tie, his hair iron grey and slicked back, a thin moustache (the red rosebud is modelled);
    Bonasera the undertaker in a black suit, a white shirt and black tie, bald with a dark fringe and a heavy black
    moustache; Hagen in a black dinner jacket over a white front, his thin light hair; Sonny the groomsman in a black
    double-breasted dinner jacket, his dark curls (their white carnations are modelled)."""
    rng = np.random.default_rng(1945)
    made = {}
    BLACK = (16, 16, 18); WHITE = (232, 228, 218)

    def suit(av, tex, who, front, waistcoat=None, keep_shirt=False, legs_black=True):
        """A black suit painted over an avatar's clothes: every bit of cloth above the hem black but the shirt front
        (`front`: the white V), a waistcoat's narrower V (`waistcoat`) black inside it; the legs and shoes black."""
        b = load(av, tex); B = Body(tex); H, S, V = hsv(b)
        J = B.J; neck, pel = J['Bip01 Neck'][2], J['Bip01 Pelvis'][2]
        hands = B.part('Hand', 'Finger') & (S > 0.28) & (S < 0.55) & (H > 4) & (H < 45) & (V > 0.25)   # skin, not a red cuff or tweed
        cloth = B.where(~hands & B.part('Spine', 'Clavicle', 'Neck', 'UpperArm', 'Forearm', 'Pelvis', 'Hand') & (B.z > pel - 0.12)
                        & ~(B.part('Neck') & (B.z > neck + 0.035)))
        shirt = cloth & _shirt_front(B, neck, *front)
        collar = cloth & B.where(B.part('Neck', 'Spine2', 'Clavicle') & (B.z > neck - 0.035) & (B.z < neck + 0.03) & (np.abs(B.x) < 0.07) & (B.y < 0.02))
        white = shirt | collar
        jacket = cloth & ~white
        b = recolour(b, B.grow(jacket.astype(np.float32), 24), BLACK, contrast=0.55, flatten=6)
        b = leftover_black(b, BLACK, keep=B.grow(B.part('Hand', 'Finger').astype(np.float32), 2))
        H, S, V = hsv(b)                                                         # a coloured shirt left over (a collar, a cuff)
        red = B.where(~hands & ~B.part('Head') & (S > 0.3) & ((H < 25) | (H > 330)) & (V > 0.12) & ~B.part('Hand', 'Finger'))
        b = recolour(b, B.grow(red.astype(np.float32), 3), BLACK, contrast=0.5)
        H, S, V = hsv(b)                                                         # and in the padding round the islands (seams)
        b = recolour(b, ((S > 0.5) & ((H < 8) | (H > 335)) & ~B.ok).astype(np.float32), BLACK, contrast=0.3)
        b = recolour(b, soft(white.astype(np.float32), 0.6), WHITE, contrast=0.35, flatten=3)
        if waistcoat is not None:
            wc = shirt & ~_shirt_front(B, neck, *waistcoat)
            b = recolour(b, soft(wc.astype(np.float32), 0.6), (12, 12, 14), contrast=0.3)
        b = recolour(b, soft(_bow_tie(B, neck).astype(np.float32), 0.4), (10, 10, 12), contrast=0.3)
        H, S, V = hsv(b)
        legs = B.where(B.part('Thigh', 'Calf', 'Pelvis', 'Spine') & (B.z < pel + 0.02) & (B.z > 0.09) & ~hands & ~white)
        if legs_black: b = recolour(b, B.grow(legs.astype(np.float32), 16), (18, 18, 20), contrast=0.6, flatten=2.5)
        feet = B.where(B.part('Foot', 'Toe') | (B.part('Calf') & (B.z <= 0.09)))
        b = recolour(b, B.grow(feet.astype(np.float32), 6), (12, 12, 13), contrast=0.7, flatten=1.0)
        return b, B, neck, pel, jacket, legs

    # Vito (Male_Adult_03): iron-grey hair slicked back, a thin dark moustache, a sallow cast to the skin; the tweed
    # jacket black, the red shirt's V a white stiff front between the black waistcoat's lapels, two studs, the bow tie
    hair_c = (46, 43, 40)
    h = load('Male_Adult_03', 'm004_head_color.tga'); Hd = Body('m004_head_color.tga'); H, S, V = hsv(h)
    brow, line, ear = _hairline(Hd, front=0.055)
    face = Hd.where((Hd.y < -0.05) & (Hd.z < brow + 0.03) & (np.abs(Hd.x) < 0.06))
    hm = soft(Hd.grow(Hd.where((Hd.z > line - 0.006) & ~ear & ~face).astype(np.float32), 3), 1.4)
    h = recolour(h, hm, hair_c, contrast=1.0)
    temples = Hd.where((np.abs(Hd.x) > 0.055) & (Hd.z < brow + 0.05) & (Hd.z > brow - 0.04)) & (hm > 0.5)
    h = recolour(h, soft(temples.astype(np.float32), 4) * 0.45, (118, 114, 108), contrast=1.0)   # grey at the temples
    mo = _moustache(Hd, width=0.036, low=0.001, high=0.0055)                                  # a thin line, out to the mouth's corners
    h = _hair_on(h, mo, rng, (50, 44, 40), 0.8); h = _hair_on(h, mo, rng, (96, 90, 84), 0.25)
    skin = Hd.where(~(hm > 0.5) & (Hd.z < brow + 0.06)).astype(np.float32)
    h = skin_tone(h, soft(skin, 2) * (1 - mo), (0.96, 0.9, 0.8))
    made['vito'] = [save(h, 'vito', 'm004_head_color.tga')]
    o = load('Male_Adult_03', 'm004_opacity_color.tga'); al = load_alpha('Male_Adult_03', 'm004_opacity_color.tga')
    made['vito'].append(save(recolour(o, np.ones(o.shape[:2], np.float32), hair_c, contrast=1.1), 'vito', 'm004_opacity_color.tga', al))
    b, B, neck, pel, jacket, legs = suit('Male_Adult_03', 'm004_body_color.tga', 'vito', (0.03, 0.42, 0.085, 0.006), waistcoat=(0.03, 0.4, 0.06, 0.0))
    b = _studs(b, B, neck, (0.1, 0.17))
    made['vito'].append(save(b, 'vito', 'm004_body_color.tga'))
    made['vito'].append(_flat_normals('Male_Adult_03', 'm004_body_normal.tga', 'vito', B.grow(jacket.astype(np.float32), 3) * 0.75))

    # Bonasera (Business_Male_07): the fringe dark, the brows heavy, a full black moustache, olive skin; the white shirt
    # kept at the collar and in the jacket's V with the tie black; the jacket and trousers black
    h = load('Business_Male_07', 'm018_head_color.tga'); Hd = Body('m018_head_color.tga'); H, S, V = hsv(h)
    brow, line, ear = _hairline(Hd, front=0.03)
    ax = np.abs(Hd.x)
    fringe = Hd.where(((ax > 0.058) | (Hd.y > 0.03)) & (Hd.z > brow - 0.08) & (Hd.z < brow + 0.02 + 0.02 * smooth(0.0, 0.06, Hd.y)) & ~ear & ~(Hd.y < -0.05))
    fm = soft(fringe.astype(np.float32), 8) * smooth(brow - 0.085, brow - 0.06, Hd.z)
    h = _hair_on(h, fm, rng, (44, 38, 34), 0.6); h = _hair_on(h, fm, rng, (70, 64, 60), 0.25)
    arch = brow + 0.003 + 0.004 * np.cos(np.clip((ax - 0.028) / 0.022, -1.5, 1.5))
    brows = Hd.where((Hd.y < -0.06) & (np.abs(Hd.z - arch) < 0.0045) & (ax > 0.009) & (ax < 0.046))
    h = _hair_on(h, soft(brows.astype(np.float32), 1.2), rng, (30, 26, 24), 0.7)
    mo = blur(_moustache(Hd, width=0.035, low=-0.004, high=0.013), 1.5)
    h = recolour(h, mo * 0.7, (34, 30, 27), contrast=0.7); h = _hair_on(h, mo, rng, (24, 20, 18), 0.85)
    h = _hair_on(h, _beard_mask(Hd, moustache=False, cheeks=0.35), rng, (60, 50, 44), 0.18)
    skin = Hd.where(Hd.z < brow + 0.2).astype(np.float32)
    h = skin_tone(h, soft(skin, 2) * (1 - mo), (0.92, 0.85, 0.76))
    made['bonasera'] = [save(h, 'bonasera', 'm018_head_color.tga')]
    b, B, neck, pel, jacket, legs = suit('Business_Male_07', 'm018_body_color.tga', 'bonasera', (0.03, 0.3, 0.07, 0.004))
    tie = B.where((np.abs(B.x) < 0.024 - 0.012 * np.clip((neck - B.z - 0.03) / 0.25, 0, 1) + 0.012 * np.clip((neck - B.z - 0.06) / 0.2, 0, 1))
                  & (neck - B.z > 0.025) & (neck - B.z < 0.3) & (B.y < -0.03))
    b = recolour(b, soft(tie.astype(np.float32), 0.6), (12, 12, 14), contrast=0.4)
    made['bonasera'].append(save(b, 'bonasera', 'm018_body_color.tga'))
    made['bonasera'].append(_flat_normals('Business_Male_07', 'm018_body_normal.tga', 'bonasera', np.maximum(B.grow(jacket.astype(np.float32), 3) * 0.8, B.grow(legs.astype(np.float32), 3) * 0.6)))

    # Hagen (Male_Adult_13): his hair a lighter brown, thinning at the crown; the argyle sweater a black dinner jacket
    # with a white front and studs, the jeans black, the brown shoes black
    h = load('Male_Adult_13', 'm010_head_color.tga'); Hd = Body('m010_head_color.tga'); H, S, V = hsv(h)
    brow, line, ear = _hairline(Hd, front=0.06)
    face = Hd.where((Hd.y < -0.05) & (Hd.z < brow + 0.035) & (np.abs(Hd.x) < 0.06))
    hm = soft(Hd.grow(Hd.where((Hd.z > line - 0.006) & ~ear & ~face & (V < 0.5)).astype(np.float32), 3), 1.2)
    h = recolour(h, hm, (92, 74, 56), contrast=1.15)
    made['hagen'] = [save(h, 'hagen', 'm010_head_color.tga')]
    b, B, neck, pel, jacket, legs = suit('Male_Adult_13', 'm010_body_color.tga', 'hagen', (0.03, 0.38, 0.07, 0.008))
    b = _studs(b, B, neck, (0.1, 0.17))
    made['hagen'].append(save(b, 'hagen', 'm010_body_color.tga'))
    made['hagen'].append(_flat_normals('Male_Adult_13', 'm010_body_normal.tga', 'hagen', np.maximum(B.grow(jacket.astype(np.float32), 3) * 0.85, B.grow(legs.astype(np.float32), 3) * 0.6)))

    # Sonny (Male_Adult_06): dark curls, olive skin; the red henley a black double-breasted dinner jacket (its V short,
    # closing high on the chest), the jeans black, the grey sneakers black shoes
    hair_c = (36, 27, 22)
    h = load('Male_Adult_06', 'm011_head_color.tga'); Hd = Body('m011_head_color.tga'); H, S, V = hsv(h)
    brow, line, ear = _hairline(Hd, front=0.078, nape=-0.14)
    face = Hd.where((Hd.y < -0.05) & (Hd.z < brow + 0.03) & (np.abs(Hd.x) < 0.06))
    hm = soft(Hd.grow(Hd.where((Hd.z > line - 0.01) & ~ear & ~face).astype(np.float32), 3), 1.2)
    h = recolour(h, hm, hair_c, contrast=1.25)
    h = skin_tone(h, soft(Hd.where(Hd.ok).astype(np.float32), 1) * (1 - hm), (0.95, 0.88, 0.8))
    made['sonny'] = [save(h, 'sonny', 'm011_head_color.tga')]
    o = load('Male_Adult_06', 'm011_opacity_color.tga'); al = load_alpha('Male_Adult_06', 'm011_opacity_color.tga')
    made['sonny'].append(save(recolour(o, np.ones(o.shape[:2], np.float32), hair_c, contrast=1.3), 'sonny', 'm011_opacity_color.tga', al))
    b, B, neck, pel, jacket, legs = suit('Male_Adult_06', 'm011_body_color.tga', 'sonny', (0.03, 0.2, 0.06, 0.004))
    made['sonny'].append(save(b, 'sonny', 'm011_body_color.tga'))
    made['sonny'].append(_flat_normals('Male_Adult_06', 'm011_body_normal.tga', 'sonny', np.maximum(B.grow(jacket.astype(np.float32), 3) * 0.85, B.grow(legs.astype(np.float32), 3) * 0.6)))
    for k, v in made.items(): print(k, [os.path.basename(p) for p in v])


def _hair_recolour(avatar, name, who, out_name, colour, contrast=1.0, shine=1.0):
    """A donor's hair cards in another colour: the strands' own light and dark kept (raised to `contrast`), their alpha
    kept; `shine` scales the highlights (greasy hair duller)."""
    a = load(avatar, name); al = load_alpha(avatar, name)
    l = lum(a); m = al > 0.3
    rel = np.clip(l / max(l[m].mean(), 1e-4), 0.2, 2.5) ** contrast
    rel = np.where(rel > 1, 1 + (rel - 1) * shine, rel)
    col = np.array(colour, np.float32)[None, None, :] / 255 * rel[..., None]
    return save(col, who, out_name, alpha=al)


def _gt_pat(B, name, scale, contrast=1.0, _cache={}):
    """A cloth's pattern (a Poly Haven texture's light and dark, mean 1) laid on the body by its position."""
    if name not in _cache:
        im = np.asarray(Image.open(os.path.join(ROOT, 'pipeline', 'cache', 'polyhaven', name, 'Diffuse.png')).convert('L').resize((1024, 1024), Image.LANCZOS), np.float32) / 255
        _cache[name] = im / max(im.mean(), 1e-4)
    L = _cache[name]; n = L.shape[0]
    u = ((np.nan_to_num(B.x) + 0.6 * np.nan_to_num(B.y)) / scale) % 1.0; v = (np.nan_to_num(B.z) / scale) % 1.0
    return np.clip(L[(v * (n - 1)).astype(int), (u * (n - 1)).astype(int)], 0.2, 3.0) ** contrast


def _gt_cloth(name, size=1024):
    im = np.asarray(Image.open(os.path.join(ROOT, 'pipeline', 'cache', 'polyhaven', name, 'Diffuse.png')).convert('L').resize((size, size), Image.LANCZOS), np.float32) / 255
    return im / max(im.mean(), 1e-4)


def _gt_fill(b, B, mask, colour, pattern=None, k=0.45, flatten=3, grow=8):
    """Paint `colour` where mask is (grown into the padding), keeping the cloth's folds by `k`, times a pattern."""
    m = B.grow(mask.astype(np.float32), grow) if grow else mask.astype(np.float32)
    out = recolour(b, m, colour, contrast=k, flatten=flatten)
    if pattern is not None: out = out * (1 - m[..., None]) + out * m[..., None] * pattern[..., None]
    return out


def _gt_regions(B):
    """The body's parts for a costume: torso (to the hips), arms, hands, thighs (with the seat), calves, feet."""
    J = B.J; neck, pel = J['Bip01 Neck'][2], J['Bip01 Pelvis'][2]; knee = J['Bip01 L Calf'][2]
    hands = B.part('Hand', 'Finger')
    torso = B.where(B.part('Spine', 'Clavicle', 'Pelvis', 'Neck') & (B.z > pel - 0.1) & ~(B.part('Neck') & (B.z > neck + 0.035)))
    arms = B.part('UpperArm', 'Forearm') & ~hands
    thighs = B.where(B.part('Thigh') | (B.part('Pelvis', 'Spine') & (B.z <= pel - 0.1)))
    return dict(J=J, neck=neck, pel=pel, knee=knee, hands=hands, torso=torso, arms=arms, thighs=thighs, calves=B.part('Calf'), feet=B.part('Foot', 'Toe'))


def _gt_clasps(b, B, xs, zs, r, colour=(196, 160, 86)):
    m = np.zeros(B.x.shape, np.float32)
    for x0 in xs:
        for z0 in zs: m = np.maximum(m, B.where((((B.x - x0) / r) ** 2 + ((B.z - z0) / (r * 0.7)) ** 2 < 1) & (B.y < 0)).astype(np.float32))
    return _gt_fill(b, B, soft(m, 0.6) > 0.3, colour, k=0.3, flatten=0, grow=1)


def _gt_head_hair(h, Hd, colour, front=0.06, contrast=1.0):
    brow, line, ear = _hairline(Hd, front=front)
    face = Hd.where((Hd.y < -0.05) & (Hd.z < brow + 0.03) & (np.abs(Hd.x) < 0.06))
    hm = soft(Hd.grow(Hd.where((Hd.z > line - 0.01) & ~ear & ~face).astype(np.float32), 3), 1.4)
    return recolour(h, hm, colour, contrast=contrast), hm, brow


def _gt_beard(h, Hd, mask, rng, colour, n=9000, length=9, base=0.55, grey=0.0):
    """A beard of strands: the skin under it darkened toward `colour` (by `base`), then `n` short strokes drawn down
    the face (along the texture's own downward direction, from the texel map), each a little lighter or darker; `grey`
    is the share of grey hairs."""
    from PIL import ImageDraw
    h = recolour(h, np.clip(mask * 1.3, 0, 1) * base, colour, contrast=0.6)
    z = np.where(Hd.ok, Hd.z, np.nan); gy, gx = np.gradient(z)
    gx, gy = np.nan_to_num(-gx), np.nan_to_num(-gy); g = np.hypot(gx, gy) + 1e-9; dx, dy = gx / g, gy / g   # down the face, in pixels
    H_, W_ = mask.shape; layer = Image.new('RGBA', (W_, H_), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    p = np.clip(mask, 0, 1).ravel(); p = p / p.sum()
    idx = rng.choice(p.size, n, p=p); col = np.array(colour, np.float32)
    for i in idx:
        y, x = divmod(int(i), W_)
        if not Hd.ok[y, x]: continue
        L = length * rng.uniform(0.6, 1.3); a = rng.uniform(-0.35, 0.35)
        ux, uy = dx[y, x] * np.cos(a) - dy[y, x] * np.sin(a), dx[y, x] * np.sin(a) + dy[y, x] * np.cos(a)
        c = col * rng.uniform(0.6, 1.45) if rng.random() > grey else np.array([150, 144, 138], np.float32) * rng.uniform(0.8, 1.1)
        d.line([(x, y), (x + ux * L, y + uy * L)], fill=tuple(int(v) for v in np.clip(c, 0, 255)) + (int(200 * mask[y, x] ** 0.5),), width=1)
    lay = np.asarray(layer, np.float32) / 255; k = lay[..., 3:4]
    return h * (1 - k) + lay[..., :3] * k


def game_of_thrones():
    """King Robert's court, season one (costumes by Michele Clapton). The hair cards are generated in the build; here
    Cersei's own long cards (Female_Adult_15) turn honey gold; then each costume on its body, and the cloth of the
    modelled gown, robe and cloak."""
    _hair_recolour('Female_Adult_15', 'f018_opacity_color.tga', 'cersei', 'f018_opacity_color.tga', (214, 174, 108), contrast=1.15)
    _hair_recolour('Male_Adult_07', 'm013_opacity_color.tga', 'littlefinger', 'm013_opacity_color.tga', (40, 34, 30))
    rng = np.random.default_rng(2011)
    pat, fill = _gt_pat, _gt_fill

    # ---- King Robert (Male_Adult_05): a long sleeveless surcoat of deep purple-navy wool, gold knotwork clasps down
    # its front, a brown belt with its long tail; tan leather sleeves with tooled gold at the shoulders; brown boots;
    # his hair and full beard near black
    b = load('Male_Adult_05', 'm009_body_color.tga'); B = Body('m009_body_color.tga'); r = _gt_regions(B)
    coat = r['torso'] | (r['thighs'] & B.where(B.z > r['knee'] - 0.02))
    b = fill(b, B, coat, (52, 40, 70), pat(B, 'poly_wool_herringbone', 0.35, 0.6))
    b = fill(b, B, r['arms'], (138, 100, 58), pat(B, 'brown_leather', 0.3, 0.8))
    caps = B.where(B.part('UpperArm', 'Clavicle') & (np.abs(B.x) > 0.15) & (np.abs(B.x) < 0.27) & (B.z > r['neck'] - 0.12))
    b = fill(b, B, caps, (176, 136, 70), pat(B, 'floral_jacquard', 0.12, 1.2), k=0.3, grow=4)
    b = _gt_clasps(b, B, [0.0], [r['neck'] - 0.1 - 0.075 * k for k in range(5)], 0.022)
    belt = B.where((np.abs(B.z - (r['pel'] + 0.07)) < 0.025) & B.part('Spine', 'Pelvis'))
    tail = B.where((B.x > 0.03) & (B.x < 0.06) & (B.z < r['pel'] + 0.07) & (B.z > r['pel'] - 0.32) & (B.y < 0))
    b = fill(b, B, belt | tail, (86, 54, 32), pat(B, 'brown_leather', 0.2), k=0.3, grow=2)
    boots = r['calves'] | r['feet'] | B.where(B.part('Thigh') & (B.z < r['knee'] - 0.02))
    b = fill(b, B, boots, (70, 46, 30), pat(B, 'brown_leather', 0.25))
    save(b, 'robert', 'm009_body_color.tga')
    _flat_normals('Male_Adult_05', 'm009_body_normal.tga', 'robert', B.grow((coat | r['arms'] | boots).astype(np.float32), 4) * 0.8)
    h = load('Male_Adult_05', 'm009_head_color.tga'); Hd = Body('m009_head_color.tga')
    h, hm, brow = _gt_head_hair(h, Hd, (38, 30, 25), front=0.05)
    bm_ = _beard_mask(Hd, moustache=True, cheeks=0.9)
    h = _gt_beard(h, Hd, bm_, rng, (44, 32, 24), n=14000, length=10, base=0.75, grey=0.04)
    save(h, 'robert', 'm009_head_color.tga')
    save_rough(np.maximum(bm_, hm) * 0.9, 0.9, 0.55, 'robert', 'm009_head_rough.png')

    wool = _gt_cloth('poly_wool_herringbone')
    save(np.array([52, 40, 70], np.float32)[None, None] / 255 * np.clip(wool ** 0.6, 0.7, 1.3)[..., None], 'robert', 'coat.tga')

    # ---- Ned (Medical_Male_01): a sleeveless brown leather jerkin quilted in long ribs, laced up the front, over a dark
    # grey-green wool tunic; the Hand's gold pin on his left breast; dark breeches and boots; a short dark brown beard
    b = load('Medical_Male_01', 'm152_body_color.tga'); B = Body('m152_body_color.tga'); r = _gt_regions(B)
    jerkin = r['torso'] | (r['thighs'] & B.where(B.z > r['pel'] - 0.22))
    ribs = 0.86 + 0.14 * np.abs(np.sin(np.nan_to_num(B.x) * np.pi / 0.03))
    b = fill(b, B, jerkin, (92, 62, 40), pat(B, 'brown_leather', 0.25, 0.8) * ribs)
    lace = B.where((np.abs(B.x) < 0.012) & (B.z > r['pel']) & (B.z < r['neck'] - 0.05) & (B.y < 0))
    b = fill(b, B, lace, (40, 28, 20), k=0.2, flatten=0, grow=1)
    b = fill(b, B, r['arms'], (52, 58, 48), pat(B, 'rough_linen', 0.2, 0.6))
    legs = r['thighs'] & B.where(B.z <= r['pel'] - 0.22)
    b = fill(b, B, legs, (48, 38, 30), pat(B, 'rough_linen', 0.3, 0.4))
    boots = r['calves'] | r['feet'] | B.where(B.part('Thigh') & (B.z < r['knee'] + 0.02))
    b = fill(b, B, boots, (40, 30, 24), pat(B, 'brown_leather', 0.25))
    pin = B.where((np.abs(B.x - 0.085) < 0.011) & (np.abs(B.z - (r['neck'] - 0.15)) < 0.03) & (B.y < 0))
    b = fill(b, B, pin, (206, 168, 80), k=0.2, flatten=0, grow=1)
    save(b, 'ned', 'm152_body_color.tga')
    _flat_normals('Medical_Male_01', 'm152_body_normal.tga', 'ned', B.grow((jerkin | r['arms'] | legs | boots).astype(np.float32), 4) * 0.85)
    h = load('Medical_Male_01', 'm152_head_color.tga'); Hd = Body('m152_head_color.tga')
    bm_ = _beard_mask(Hd, moustache=True, cheeks=0.6)
    h = _gt_beard(h, Hd, bm_, rng, (62, 44, 30), n=9000, length=6, base=0.55, grey=0.03)
    h, hm, brow = _gt_head_hair(h, Hd, (82, 60, 42), front=0.075)
    save(h, 'ned', 'm152_head_color.tga')
    save_rough(np.maximum(bm_, hm) * 0.9, 0.9, 0.55, 'ned', 'm152_head_rough.png')

    # ---- Jaime (Male_Adult_16): the Kingsguard's gilded armour, a breastplate with a skirt of gilt scales to mid thigh,
    # scaled pauldrons, brown leather bracers, a cream padded coat below, brown boots (the white cloak is modelled);
    # light stubble
    b = load('Male_Adult_16', 'm019_body_color.tga'); B = Body('m019_body_color.tga'); r = _gt_regions(B)
    X, Z = np.nan_to_num(B.x), np.nan_to_num(B.z)
    def scales(sc):
        row = np.floor(Z / (sc * 0.7)); off = 0.5 * (row % 2)
        return 0.72 + 0.4 * np.sin((X / sc + off) * np.pi) ** 2 * ((Z / (sc * 0.7)) % 1) ** 0.6
    plate = r['torso'] & B.where(B.z > r['pel'] - 0.02)
    ribs_ = 0.9 + 0.1 * np.cos(np.nan_to_num(B.z) * np.pi / 0.045) ** 8         # the breastplate's lames, edge on edge
    b = fill(b, B, plate, (206, 158, 74), ribs_, k=0.5, flatten=6)
    skirt_ = (r['torso'] & B.where(B.z <= r['pel'] - 0.02)) | (r['thighs'] & B.where(B.z > r['pel'] - 0.3))
    sk = scales(0.035); b = fill(b, B, skirt_, (190, 142, 64), sk, k=0.4)
    paul = r['arms'] & B.part('UpperArm')
    pl = scales(0.03); b = fill(b, B, paul, (198, 150, 70), pl, k=0.4)
    brace = r['arms'] & B.part('Forearm')
    b = fill(b, B, brace, (186, 140, 64), ribs_, k=0.4)
    legs = r['thighs'] & B.where((B.z <= r['pel'] - 0.3) & (B.z > r['knee'] - 0.02))
    b = fill(b, B, legs, (70, 46, 30), pat(B, 'brown_leather', 0.25, 0.7))
    boots = r['calves'] | r['feet'] | B.where(B.part('Thigh') & (B.z < r['knee'] - 0.02))
    b = fill(b, B, boots, (84, 56, 36), pat(B, 'brown_leather', 0.25))
    save(b, 'jaime', 'm019_body_color.tga')
    gilt = B.grow((plate | skirt_ | paul | brace).astype(np.float32), 4)
    save_rough(gilt * np.clip(0.55 + 0.45 * (np.where(skirt_, sk, 1) * np.where(paul, pl, 1) - 0.72) / 0.4, 0, 1), 1.0, 0.0, 'jaime', 'm019_body_metal.png')
    save_rough(gilt, 0.3, 0.7, 'jaime', 'm019_body_rough.png')
    _flat_normals('Male_Adult_16', 'm019_body_normal.tga', 'jaime', B.grow((plate | skirt_ | paul | brace | legs | boots).astype(np.float32), 4) * 0.95)
    h = load('Male_Adult_16', 'm019_head_color.tga'); Hd = Body('m019_head_color.tga')
    h = _hair_on(h, _beard_mask(Hd, moustache=True, cheeks=0.7), rng, (150, 118, 80), 0.3)
    h, hm, brow = _gt_head_hair(h, Hd, (186, 150, 92), contrast=1.1)
    save(h, 'jaime', 'm019_head_color.tga')
    weave = _gt_cloth('rough_linen', 512)
    save(np.ones((512, 512, 3), np.float32) * np.array([226, 220, 204], np.float32)[None, None] / 255 * (0.82 + 0.18 * weave)[..., None] * 0.92, 'jaime', 'cloak.tga')

    # ---- Joffrey (Male_Adult_11): a knee-length coat of crimson brocade with a black and gold damask, high at the
    # collar; a black belt; black breeches and boots; his short hair gold
    b = load('Male_Adult_11', 'm001_body_color.tga'); B = Body('m001_body_color.tga'); r = _gt_regions(B)
    coat = r['torso'] | r['arms'] | (r['thighs'] & B.where(B.z > r['knee'] + 0.04))
    b = fill(b, B, coat, (118, 24, 30), np.clip(pat(B, 'floral_jacquard', 0.16, 1.4), 0.45, 1.6))
    b = fill(b, B, B.where((np.abs(B.z - (r['pel'] + 0.05)) < 0.02) & B.part('Spine', 'Pelvis')), (18, 16, 16), k=0.3, grow=2)
    legs = (r['thighs'] & B.where(B.z <= r['knee'] + 0.04)) | r['calves'] | r['feet']
    b = fill(b, B, legs, (22, 20, 20), pat(B, 'brown_leather', 0.25, 0.5))
    save(b, 'joffrey', 'm001_body_color.tga')
    _flat_normals('Male_Adult_11', 'm001_body_normal.tga', 'joffrey', B.grow((coat | legs).astype(np.float32), 4) * 0.85)
    h = load('Male_Adult_11', 'm001_head_color.tga'); Hd = Body('m001_head_color.tga')
    h, hm, brow = _gt_head_hair(h, Hd, (170, 134, 76), contrast=0.5)
    save(h, 'joffrey', 'm001_head_color.tga')

    fj = _gt_cloth('floral_jacquard')
    save(np.array([118, 24, 30], np.float32)[None, None] / 255 * np.clip(fj ** 1.4, 0.45, 1.6)[..., None], 'joffrey', 'coat.tga')

    # ---- Littlefinger (Male_Adult_07): the long dark brown coat ribbed with fine pale stripes, high collared, to the
    # calf; dark breeches and boots; the silver mockingbird; short dark hair greying at the temples, goatee, moustache
    b = load('Male_Adult_07', 'm013_body_color.tga'); B = Body('m013_body_color.tga'); r = _gt_regions(B)
    coat = r['torso'] | r['arms'] | r['thighs'] | B.where(r['calves'] & (B.z > r['knee'] - 0.16))
    st = _stripes(B, 0.022, [(0.5, 0.12, (122, 98, 66))], (58, 42, 32))
    b = _paint(b, B.grow(coat.astype(np.float32), 8), st, k=0.5, flatten=3)
    boots = B.where(r['calves'] & (B.z <= r['knee'] - 0.16)) | r['feet']
    b = fill(b, B, boots, (26, 22, 20), pat(B, 'brown_leather', 0.25))
    pin = B.where(((B.x - 0.07) ** 2 + (B.z - (r['neck'] - 0.09)) ** 2 < 0.006 ** 2) & (B.y < 0))     # the mockingbird, a small silver brooch
    b = fill(b, B, pin, (150, 150, 152), k=0.3, flatten=0, grow=1)
    save(b, 'littlefinger', 'm013_body_color.tga')
    _flat_normals('Male_Adult_07', 'm013_body_normal.tga', 'littlefinger', B.grow((coat | boots).astype(np.float32), 4) * 0.85)
    h = load('Male_Adult_07', 'm013_head_color.tga'); Hd = Body('m013_head_color.tga')
    J = Hd.J; ax = np.abs(Hd.x); low = J['Bip01 MBottomLip'][2]
    goatee = blur(Hd.where((ax < 0.015 + 0.004 * smooth(low - 0.05, low - 0.01, Hd.z)) & (Hd.z < low - 0.004) & (Hd.z > low - 0.045) & (Hd.y < -0.04)).astype(np.float32), 4)
    mo = _moustache(Hd, width=0.026, low=0.0, high=0.007)
    h = _gt_beard(h, Hd, np.maximum(goatee, mo), rng, (40, 33, 28), n=3500, length=5, base=0.5, grey=0.08)
    h = _hair_on(h, _beard_mask(Hd, moustache=False, cheeks=0.5), rng, (60, 50, 44), 0.2)
    h, hm, brow = _gt_head_hair(h, Hd, (40, 34, 30))
    temples = Hd.where((ax > 0.052) & (Hd.z < brow + 0.06) & (Hd.z > brow - 0.04)) & (hm > 0.5)
    h = recolour(h, soft(temples.astype(np.float32), 4) * 0.5, (110, 106, 100), contrast=1.0)
    save(h, 'littlefinger', 'm013_head_color.tga')

    uu = (np.arange(1024)[None, :] / 1024 * 46) % 1.0                        # 46 pale ribs round the coat
    rib = np.clip((0.06 - np.abs(uu - 0.5)) / 0.02 + 0.5, 0, 1) * np.ones((1024, 1))
    base = np.array([58, 42, 32], np.float32) / 255; line = np.array([122, 98, 66], np.float32) / 255
    save((base[None, None] * (1 - rib[..., None]) + line[None, None] * rib[..., None]) * (0.9 + 0.2 * _gt_cloth('rough_linen'))[..., None], 'littlefinger', 'coat.tga')

    # ---- Varys (Business_Male_04): a robe of pale gold silk with a large woven pattern, a blue-grey brocade stole down
    # either side of its front, soft dark slippers (the robe's skirt is modelled)
    b = load('Business_Male_04', 'm015_body_color.tga'); B = Body('m015_body_color.tga'); r = _gt_regions(B)
    robe = r['torso'] | r['arms'] | r['thighs'] | r['calves']
    b = fill(b, B, robe, (204, 180, 124), np.clip(pat(B, 'quatrefoil_jacquard_fabric', 0.3, 0.9), 0.6, 1.4))
    stole = B.where((np.abs(B.x) > 0.045) & (np.abs(B.x) < 0.11) & (B.y < 0.0) & (B.z < r['neck'] + 0.02)) & (r['torso'] | r['thighs'])
    b = fill(b, B, stole, (112, 116, 128), pat(B, 'floral_jacquard', 0.12, 1.2), k=0.4, grow=3)
    b = fill(b, B, r['feet'], (40, 32, 28), k=0.4)
    save(b, 'varys', 'm015_body_color.tga')
    _flat_normals('Business_Male_04', 'm015_body_normal.tga', 'varys', B.grow(robe.astype(np.float32), 4) * 0.9)
    q = _gt_cloth('quatrefoil_jacquard_fabric'); fj = _gt_cloth('floral_jacquard')
    img = np.array([204, 180, 124], np.float32)[None, None] / 255 * np.clip(q ** 0.9, 0.6, 1.4)[..., None]
    uu = np.arange(1024)[None, :] / 1024
    front = np.broadcast_to((uu < 0.07) | (uu > 0.93), (1024, 1024))       # the stole's ends down the front, either side
    img = np.where(front[..., None], np.array([112, 116, 128], np.float32)[None, None] / 255 * fj[..., None], img)
    save(img, 'varys', 'robe.tga')

    # ---- Tyrion (Male_Adult_06; the head is sculpted): a sleeveless jerkin of maroon brocade with gold toggles over
    # dark red sleeves; black breeches and boots
    b = load('Male_Adult_06', 'm011_body_color.tga'); B = Body('m011_body_color.tga'); r = _gt_regions(B)
    jerk = r['torso'] | (r['thighs'] & B.where(B.z > r['pel'] - 0.2))
    b = fill(b, B, jerk, (88, 24, 28), np.clip(pat(B, 'floral_jacquard', 0.14, 1.1), 0.5, 1.5))
    b = fill(b, B, r['arms'], (104, 30, 30), pat(B, 'leather_red_02', 0.2, 0.6))
    b = _gt_clasps(b, B, [0.0], [r['neck'] - 0.1 - 0.06 * k for k in range(5)], 0.014, colour=(190, 150, 80))
    legs = (r['thighs'] & B.where(B.z <= r['pel'] - 0.2)) | r['calves'] | r['feet']
    b = fill(b, B, legs, (30, 26, 24), pat(B, 'brown_leather', 0.25, 0.5))
    save(b, 'tyrion', 'm011_body_color.tga')
    _flat_normals('Male_Adult_06', 'm011_body_normal.tga', 'tyrion', B.grow((jerk | r['arms'] | legs).astype(np.float32), 4) * 0.85)

    # ---- Cersei (Female_Adult_15; the head is sculpted): the red silk gown, gold embroidery round its deep V, a wide
    # gold sash at the waist, long red sleeves with gold at the cuffs (its skirt is modelled)
    b = load('Female_Adult_15', 'f018_body_color.tga'); B = Body('f018_body_color.tga'); r = _gt_regions(B)
    gown = r['torso'] | r['arms'] | r['thighs'] | r['calves'] | r['feet']
    open_ = np.clip((B.z - (r['neck'] - 0.24)) / 0.2, 0, 1) * 0.05
    vee = B.where((np.abs(B.x) < open_) & (B.z > r['neck'] - 0.24) & (B.y < 0))
    H_, S_, V_ = hsv(b)
    bare = (H_ < 40) & (S_ > 0.22) & (V_ > 0.3)                             # the avatar's own skin in its open neck
    collar = B.where((B.z > r['neck'] - 0.09) & ~bare & ~r['hands'])          # the blouse's white collar
    vee = vee & B.where(B.z <= r['neck'] - 0.09)
    b = fill(b, B, (gown | collar) & ~vee, (148, 22, 28), pat(B, 'crepe_satin', 0.3, 0.7))
    trim = B.where((np.abs(np.abs(B.x) - open_) < 0.014) & (B.z > r['neck'] - 0.26) & (B.y < 0))
    b = fill(b, B, trim, (196, 156, 82), pat(B, 'floral_jacquard', 0.06, 1.2), k=0.3, grow=2)
    sash = B.where((np.abs(B.z - (r['pel'] + 0.1)) < 0.045) & B.part('Spine', 'Pelvis'))
    b = fill(b, B, sash, (186, 148, 80), pat(B, 'floral_jacquard', 0.1, 0.8), k=0.3, grow=2)
    wrist = abs(r['J']['Bip01 L Hand'][0]); cuff = B.where(B.part('Forearm') & (np.abs(B.x) > wrist - 0.06))
    b = fill(b, B, cuff, (190, 150, 80), k=0.3, grow=2)
    match = np.array([1.0, 1.1, 1.22], np.float32)                         # her skin as the sculpted face has it (paler, less orange)
    b = _skin_paint(b, B, vee, rng, warm=tuple(match))
    hs = B.where(r['hands'] & bare)[..., None]; b = np.clip(b * np.where(hs, match[None, None, :], 1.0), 0, 1)
    save(b, 'cersei', 'f018_body_color.tga')
    h = load('Female_Adult_15', 'f018_head_color.tga'); Hd = Body('f018_head_color.tga')
    lift = 1 + 0.22 * smooth(r['neck'] + 0.02, r['neck'] + 0.07, np.nan_to_num(Hd.z))   # the neck's top lit as the face above it (no chin over it now)
    low = smooth(r['neck'], r['neck'] - 0.05, np.nan_to_num(Hd.z, nan=9))[..., None]      # the open neckline: paler, less orange
    k_ = np.array([0.9, 0.92, 0.96], np.float32)[None, None, :] * (1 - low) + np.array([0.98, 1.06, 1.16], np.float32)[None, None, :] * low
    save(np.clip(h * k_ * lift[..., None], 0, 1), 'cersei', 'f018_head_color.tga')
    _flat_normals('Female_Adult_15', 'f018_body_normal.tga', 'cersei', B.grow(gown.astype(np.float32), 4) * 0.9)
    cs = _gt_cloth('crepe_satin'); fj = _gt_cloth('floral_jacquard')
    img = np.array([148, 22, 28], np.float32)[None, None] / 255 * np.clip(cs ** 0.8, 0.7, 1.3)[..., None]
    vv = np.arange(1024)[:, None] / 1024; uu = np.arange(1024)[None, :] / 1024
    gold = np.array([196, 156, 82], np.float32)[None, None] / 255 * np.clip(fj, 0.6, 1.4)[..., None]
    panel = ((uu < 0.06) | (uu > 0.94)) | (vv > 0.94)                      # the gold underskirt seen in front, the hem's border
    img = np.where(np.broadcast_to(panel, (1024, 1024))[..., None], gold, img)
    save(img, 'cersei', 'gown.tga')

    # ---- the Hound (Male_Adult_12; the head is sculpted, with its gorget): dark steel, a coat of riveted rings over the
    # chest and down to mid thigh, plates at the shoulders, a diagonal baldric, dark leather forearms and gloves, dark
    # breeches and boots
    b = load('Male_Adult_12', 'm007_body_color.tga'); B = Body('m007_body_color.tga'); r = _gt_regions(B)
    X, Z = np.nan_to_num(B.x), np.nan_to_num(B.z)
    rings = 0.7 + 0.5 * (np.sin(X * np.pi / 0.012) ** 2 * np.sin(Z * np.pi / 0.012) ** 2)
    coat = r['torso'] | (r['thighs'] & B.where(B.z > r['pel'] - 0.28))
    b = fill(b, B, coat, (74, 74, 78), rings, k=0.5)
    plates = r['arms'] & B.part('UpperArm')
    b = fill(b, B, plates, (88, 88, 94), k=0.4, flatten=6)
    b = fill(b, B, (r['arms'] & B.part('Forearm')) | r['hands'], (42, 34, 28), pat(B, 'brown_leather', 0.2))
    baldric = B.where((np.abs((X + Z * 0.55) - (r['neck'] * 0.55 - 0.02)) < 0.03) & (B.z > r['pel']) & (B.y < 0)) & r['torso']
    b = fill(b, B, baldric, (72, 50, 34), pat(B, 'brown_leather', 0.15), k=0.4, grow=2)
    legs = (r['thighs'] & B.where(B.z <= r['pel'] - 0.28)) | r['calves'] | r['feet']
    b = fill(b, B, legs, (30, 28, 26), pat(B, 'brown_leather', 0.25, 0.5))
    save(b, 'hound', 'm007_body_color.tga')
    steel = B.grow((coat & ~baldric).astype(np.float32), 3); pl_ = B.grow(plates.astype(np.float32), 3)
    save_rough(np.maximum(steel * np.clip((rings - 0.7) / 0.5, 0.3, 1.0) * 0.85, pl_ * 0.9), 1.0, 0.0, 'hound', 'm007_body_metal.png')
    save_rough(np.maximum(steel, pl_), 0.45, 0.75, 'hound', 'm007_body_rough.png')
    _flat_normals('Male_Adult_12', 'm007_body_normal.tga', 'hound', B.grow((coat | plates | legs).astype(np.float32), 4) * 0.85)


def _quilt(B, pitch=0.075, line=0.004):
    """A quilted gilet's channels across the body every `pitch` metres (mean about 1): each one puffed, lightest a
    little above its middle (lit from above), falling off into a dark stitched seam."""
    z = np.nan_to_num(B.z); f = (z / pitch) % 1.0                  # 0 at a seam, 1 at the next one up
    d = np.abs(f - 0.5) * 2                                        # 0 mid-channel, 1 at a seam
    puff = 0.74 + 0.36 * np.clip(np.cos(np.clip(d, 0, 1) * np.pi / 2), 0, 1) ** 0.7 + 0.06 * (f - 0.5)
    return np.where(np.abs(f - 0.5) * pitch > pitch / 2 - line, 0.5, puff)


def _specks(B, mask, rng, n, r, colour):
    """Small round specks scattered over a mask (studs on a cardigan, a print's flowers): (mask, colours) to paint."""
    m = np.zeros(B.x.shape, np.float32); idx = np.flatnonzero(mask & B.ok)
    if not len(idx): return m
    pick = rng.choice(idx, size=min(n, len(idx)), replace=False)
    H, W = m.shape
    for i in pick:
        y, x = divmod(int(i), W); rr = max(1, int(r))
        m[max(0, y - rr):y + rr + 1, max(0, x - rr):x + rr + 1] = 1.0
    return m * mask


def succession():
    """The Roys' dinner at the lodge in Hungary ("Hunting", 2019; costumes by Michelle Matland): Logan in an olive-brown
    windowpane tweed jacket over a burgundy shirt, a black paisley silk at his throat, white hair and white beard;
    Kendall in a burgundy quilted leather gilet over a dark brown crewneck; Roman in a black shirt; Gerri in a blush
    cardigan scattered with studs over a black blouse printed with red flowers, her hair ash blonde; Frank in a taupe
    shawl-collar cardigan over black, bald with a grey fringe; Tom in a navy quarter-zip over a blue check shirt; Greg
    in a charcoal crewneck and tan corduroys; Karl in a black jacket over black, his hair silver; the waiter in a white
    shirt, black bow tie, stone waistcoat and a long white apron."""
    rng = np.random.default_rng(2019)
    pat = _gt_pat
    fill = lambda b, B, mask, colour, pattern=None, **kw: _gt_fill(b, B, mask, colour, pattern, **{'grow': 22, **kw})   # grown far into the padding: no seams at small mips

    def head_hair(av, tex, who, colour, front=0.06, contrast=1.0, skin=None):
        h = load(av, tex); Hd = Body(tex)
        h, hm, brow = _gt_head_hair(h, Hd, colour, front=front, contrast=contrast)
        if skin: h = skin_tone(h, soft(Hd.where(Hd.ok).astype(np.float32), 1) * (1 - hm), skin)
        return h, Hd, hm, brow

    def legs_shoes(b, B, r, trousers, shoes, pattern=None):
        legs = r['thighs'] | B.where(r['calves'] & (B.z > 0.09))
        b = fill(b, B, legs, trousers, pattern)
        feet = r['feet'] | B.where(r['calves'] & (B.z <= 0.09))
        return fill(b, B, feet, shoes, k=0.5, flatten=1), legs, feet

    # ---- Logan (Male_Adult_03): the tweed jacket olive-brown with a rust windowpane, the shirt's V burgundy, a black
    # paisley silk knotted at the throat; charcoal trousers, brown brogues; white hair swept back, a short white beard
    b = load('Male_Adult_03', 'm004_body_color.tga'); B = Body('m004_body_color.tga'); r = _gt_regions(B); neck = r['neck']
    hands = r['hands']
    jacket = (r['torso'] | r['arms']) & ~hands
    vee = _shirt_front(B, neck, 0.02, 0.28, 0.075, 0.004)
    tweed = np.clip(pat(B, 'wool_boucle', 0.16, 0.45), 0.7, 1.3)
    X, Z = np.nan_to_num(B.x), np.nan_to_num(B.z)
    pane = 1 - 0.12 * ((np.abs(((X + 0.6 * np.nan_to_num(B.y)) / 0.085) % 1.0 - 0.5) < 0.04) | (np.abs((Z / 0.085) % 1.0 - 0.5) < 0.04))
    b = fill(b, B, jacket & ~vee, (84, 72, 48), tweed * pane, k=0.55, flatten=5)
    b = fill(b, B, vee, (82, 22, 30), k=0.5, flatten=3, grow=2)
    silk = B.where((np.abs(B.x) < 0.062) & (B.z > neck - 0.07) & (B.z < neck + 0.03) & (B.y < 0.01) & ~hands)
    b = fill(b, B, silk, (24, 22, 24), k=0.4, flatten=1, grow=2)
    b = recolour(b, soft(_specks(B, silk, rng, 160, 1, None), 0.4) * 0.8, (210, 204, 196), contrast=0.3)
    b, legs, feet = legs_shoes(b, B, r, (40, 38, 38), (52, 34, 22))
    save(b, 'logan', 'm004_body_color.tga')
    _flat_normals('Male_Adult_03', 'm004_body_normal.tga', 'logan', B.grow((jacket | legs).astype(np.float32), 4) * 0.7)
    # the scalp under the cards grey over pink skin, kept back from the brow: painted white, the gaps between the
    # strands read as one solid cap
    h, Hd, hm, brow = head_hair('Male_Adult_03', 'm004_head_color.tga', 'logan', (138, 126, 120), front=0.02, contrast=1.3, skin=(1.02, 0.9, 0.84))
    # the hair's mask runs over the avatar's high forehead: give back the skin it took (saturated in the original)
    h0 = load('Male_Adult_03', 'm004_head_color.tga'); S_ = hsv(h0)[1]
    took = soft(np.clip((S_ - 0.17) / 0.08, 0, 1).astype(np.float32) * Hd.where((Hd.y < -0.03) & (Hd.z < brow + 0.05)), 2.5)
    h = h * (1 - took[..., None]) + skin_tone(h0, Hd.ok.astype(np.float32), (1.02, 0.9, 0.84)) * took[..., None]
    bm_ = _beard_mask(Hd, moustache=True, cheeks=0.45)
    h = _gt_beard(h, Hd, bm_, rng, (206, 202, 196), n=11000, length=6, base=0.5, grey=0.0)
    save(h, 'logan', 'm004_head_color.tga')
    _hair_recolour('Male_Adult_03', 'm004_opacity_color.tga', 'logan', 'm004_opacity_color.tga', (194, 190, 184), contrast=1.8, shine=0.7)

    # ---- Kendall (Business_Male_06): the quilted burgundy leather gilet (tan lining at its stand collar, a snap
    # placket), the dark brown crewneck's sleeves and neck; black trousers and shoes; dark hair
    b = load('Business_Male_06', 'm025_body_color.tga'); B = Body('m025_body_color.tga'); r = _gt_regions(B); neck = r['neck']
    gilet = r['torso'] & B.where(B.z < neck + 0.02)
    collar = B.where(B.part('Neck', 'Spine2') & (B.z > neck - 0.015) & (B.z < neck + 0.035) & (np.abs(B.x) < 0.075) & (B.y > -0.05)) & ~r['hands']
    crew = B.where((np.abs(B.x) < 0.065) & (B.z > neck - 0.05) & (B.z < neck + 0.02) & (B.y < -0.02))
    b = fill(b, B, gilet & ~crew, (96, 30, 32), _quilt(B) * np.clip(pat(B, 'leather_red_02', 0.25, 0.5), 0.8, 1.2), k=0.3, flatten=2)
    b = fill(b, B, collar & ~crew, (150, 112, 74), k=0.4, grow=2)
    b = fill(b, B, (r['arms'] & ~r['hands']) | crew, (58, 42, 34), np.clip(pat(B, 'knitted_fleece', 0.12, 1.0), 0.75, 1.25), k=0.5)
    placket = B.where((np.abs(B.x) < 0.006) & (B.z < neck - 0.05) & (B.z > r['pel'] - 0.08) & (B.y < 0))
    b = fill(b, B, placket, (54, 16, 18), k=0.3, flatten=0, grow=1)
    b, legs, feet = legs_shoes(b, B, r, (22, 22, 24), (16, 15, 15))
    save(b, 'kendall', 'm025_body_color.tga')
    save_rough(B.grow((gilet & ~crew).astype(np.float32), 2), 0.38, 0.8, 'kendall', 'm025_body_rough.png')   # the leather's sheen
    _flat_normals('Business_Male_06', 'm025_body_normal.tga', 'kendall', B.grow((gilet | r['arms'] | legs).astype(np.float32), 4) * 0.8)
    h, Hd, hm, brow = head_hair('Business_Male_06', 'm025_head_color.tga', 'kendall', (40, 31, 26), front=0.065, contrast=1.0, skin=(0.97, 0.92, 0.86))
    h = _hair_on(h, _beard_mask(Hd, moustache=True, cheeks=0.6), rng, (60, 48, 40), 0.18)
    save(h, 'kendall', 'm025_head_color.tga')

    # ---- Roman (Male_Adult_08): a black shirt, dark trousers, black shoes; dark hair slicked back; pale
    b = load('Male_Adult_08', 'm014_body_color.tga'); B = Body('m014_body_color.tga'); r = _gt_regions(B)
    shirt = (r['torso'] | r['arms']) & ~r['hands']
    b = fill(b, B, shirt, (24, 24, 27), pat(B, 'cotton_jersey', 0.2, 0.3) if os.path.exists(os.path.join(ROOT, 'pipeline', 'cache', 'polyhaven', 'cotton_jersey', 'Diffuse.png')) else None, k=0.6, flatten=3)
    b = leftover_black(b, (22, 22, 25), keep=B.grow(r['hands'].astype(np.float32), 2))
    b, legs, feet = legs_shoes(b, B, r, (30, 30, 33), (14, 13, 13))
    save(b, 'roman', 'm014_body_color.tga')
    _flat_normals('Male_Adult_08', 'm014_body_normal.tga', 'roman', B.grow((shirt | legs).astype(np.float32), 4) * 0.6)
    h, Hd, hm, brow = head_hair('Male_Adult_08', 'm014_head_color.tga', 'roman', (34, 27, 24), front=0.07, contrast=1.1, skin=(1.03, 0.98, 0.95))
    save(h, 'roman', 'm014_head_color.tga')
    _hair_recolour('Male_Adult_08', 'm014_opacity_color.tga', 'roman', 'm014_opacity_color.tga', (36, 28, 24), contrast=1.1, shine=1.3)

    # ---- Gerri (Business_Female_02): the red blazer a blush cardigan scattered with little studs, the blouse in its V
    # black with red and pink flowers, a gold pendant; black trousers and shoes; ash blonde hair
    b = load('Business_Female_02', 'f015_body_color.tga'); B = Body('f015_body_color.tga'); r = _gt_regions(B); neck = r['neck']
    H_, S_, V_ = hsv(b); bare = (H_ < 40) & (S_ > 0.2) & (V_ > 0.3)
    card = (r['torso'] | r['arms']) & ~r['hands'] & ~B.where(bare & (B.z > neck - 0.14))
    vee = B.where((np.abs(B.x) < 0.012 + 0.07 * np.clip((B.z - (neck - 0.3)) / 0.26, 0, 1)) & (B.z > neck - 0.3) & (B.y < -0.02)) & card
    b = fill(b, B, card & ~vee, (204, 150, 140), np.clip(pat(B, 'knitted_fleece', 0.12, 0.8), 0.8, 1.2), k=0.45)
    b = recolour(b, soft(_specks(B, card & ~vee, rng, 900, 1, None), 0.3) * 0.7, (236, 222, 214), contrast=0.2)
    b = fill(b, B, vee, (20, 18, 20), k=0.4, grow=2)
    fl = _specks(B, vee, rng, 140, 3, None)
    b = recolour(b, soft(fl, 0.8) * 0.85, (168, 40, 52), contrast=0.4)
    b = recolour(b, soft(_specks(B, vee, rng, 60, 2, None), 0.6) * 0.7, (220, 150, 160), contrast=0.4)
    pend = B.where(((B.x) ** 2 + (B.z - (neck - 0.16)) ** 2 < 0.008 ** 2) & (B.y < 0))
    b = fill(b, B, pend, (196, 160, 86), k=0.2, flatten=0, grow=1)
    b, legs, feet = legs_shoes(b, B, r, (24, 22, 24), (16, 14, 14))
    save(b, 'gerri', 'f015_body_color.tga')
    _flat_normals('Business_Female_02', 'f015_body_normal.tga', 'gerri', B.grow((card | legs).astype(np.float32), 4) * 0.8)
    h = load('Business_Female_02', 'f015_head_color.tga'); Hd = Body('f015_head_color.tga')
    h, hm, brow = _gt_head_hair(h, Hd, (184, 160, 116), front=0.065, contrast=0.8)
    save(h, 'gerri', 'f015_head_color.tga')
    _hair_recolour('Business_Female_02', 'f015_opacity_color.tga', 'gerri', 'f015_opacity_color.tga', (198, 174, 128), contrast=0.9)

    # ---- Frank (Business_Male_07): a taupe shawl-collar cardigan in a chunky knit over black; dark grey trousers,
    # black shoes; bald, a grey fringe round the back of the head
    b = load('Business_Male_07', 'm018_body_color.tga'); B = Body('m018_body_color.tga'); r = _gt_regions(B); neck = r['neck']
    card = (r['torso'] | r['arms']) & ~r['hands']
    inner = _shirt_front(B, neck, -0.01, 0.3, 0.05, 0.004)
    b = fill(b, B, card & ~inner, (112, 94, 76), np.clip(pat(B, 'knitted_fleece', 0.09, 1.4), 0.6, 1.4), k=0.5)
    b = fill(b, B, inner, (22, 21, 22), k=0.4, grow=2)
    shawl = B.where((np.abs(np.abs(B.x) - (0.05 * np.clip((B.z - (neck - 0.3)) / 0.3, 0, 1) + 0.006)) < 0.022) & (B.z > neck - 0.32) & (B.z < neck + 0.03) & (B.y < -0.02)) & card
    b = fill(b, B, shawl, (124, 106, 86), np.clip(pat(B, 'knitted_fleece', 0.06, 1.6), 0.6, 1.4), k=0.4, grow=2)
    b = leftover_black(b, (24, 23, 24), keep=B.grow(r['hands'].astype(np.float32), 2))
    b, legs, feet = legs_shoes(b, B, r, (48, 46, 46), (16, 15, 15))
    save(b, 'frank', 'm018_body_color.tga')
    _flat_normals('Business_Male_07', 'm018_body_normal.tga', 'frank', B.grow((card | legs).astype(np.float32), 4) * 0.7)
    h = load('Business_Male_07', 'm018_head_color.tga'); Hd = Body('m018_head_color.tga')
    brow, line, ear = _hairline(Hd, front=0.03); ax = np.abs(Hd.x)
    fringe = Hd.where(((ax > 0.058) | (Hd.y > 0.03)) & (Hd.z > brow - 0.08) & (Hd.z < brow + 0.025 + 0.02 * smooth(0.0, 0.06, Hd.y)) & ~ear & ~(Hd.y < -0.05))
    fm = soft(fringe.astype(np.float32), 8) * smooth(brow - 0.085, brow - 0.06, np.nan_to_num(Hd.z))
    h = _hair_on(h, fm, rng, (128, 124, 118), 0.65); h = _hair_on(h, fm, rng, (176, 172, 166), 0.3)
    save(h, 'frank', 'm018_head_color.tga')

    # ---- Tom (Male_Adult_06): a navy quarter-zip, a blue check collar at its neck; dark trousers, brown shoes; brown
    # hair short at the sides
    b = load('Male_Adult_06', 'm011_body_color.tga'); B = Body('m011_body_color.tga'); r = _gt_regions(B); neck = r['neck']
    jumper = (r['torso'] | r['arms']) & ~r['hands']
    collar = B.where(B.part('Neck', 'Spine2', 'Clavicle') & (B.z > neck - 0.03) & (B.z < neck + 0.035) & (np.abs(B.x) < 0.075)) & ~r['hands']
    b = fill(b, B, jumper & ~collar, (30, 36, 58), np.clip(pat(B, 'knitted_fleece', 0.1, 0.9), 0.75, 1.25), k=0.5, flatten=4)
    chk = 0.82 + 0.3 * (((np.nan_to_num(B.x) / 0.008).astype(int) + (np.nan_to_num(B.z) / 0.008).astype(int)) % 2)
    b = fill(b, B, collar, (84, 108, 150), chk, k=0.3, grow=2)
    zipm = B.where((np.abs(B.x) < 0.005) & (B.z < neck + 0.02) & (B.z > neck - 0.17) & (B.y < 0)) & jumper
    b = fill(b, B, zipm, (120, 120, 126), k=0.3, flatten=0, grow=1)
    b, legs, feet = legs_shoes(b, B, r, (34, 36, 44), (62, 40, 26))
    save(b, 'tom', 'm011_body_color.tga')
    _flat_normals('Male_Adult_06', 'm011_body_normal.tga', 'tom', B.grow((jumper | legs).astype(np.float32), 4) * 0.8)
    h, Hd, hm, brow = head_hair('Male_Adult_06', 'm011_head_color.tga', 'tom', (82, 62, 46), front=0.07, contrast=1.0)
    save(h, 'tom', 'm011_head_color.tga')
    _hair_recolour('Male_Adult_06', 'm011_opacity_color.tga', 'tom', 'm011_opacity_color.tga', (86, 64, 46), contrast=1.0)

    # ---- Greg (Male_Adult_02): a charcoal crewneck; tan corduroys; brown shoes; dark brown hair
    b = load('Male_Adult_02', 'm003_body_color.tga'); B = Body('m003_body_color.tga'); r = _gt_regions(B)
    jumper = (r['torso'] | r['arms']) & ~r['hands']
    b = fill(b, B, jumper, (36, 34, 34), np.clip(pat(B, 'knitted_fleece', 0.1, 0.9), 0.75, 1.25), k=0.55, flatten=4)
    b, legs, feet = legs_shoes(b, B, r, (150, 118, 80), (70, 46, 30), pattern=np.clip(pat(B, 'ribbed_corduroy', 0.08, 1.4), 0.7, 1.3))
    save(b, 'greg', 'm003_body_color.tga')
    _flat_normals('Male_Adult_02', 'm003_body_normal.tga', 'greg', B.grow((jumper | legs).astype(np.float32), 4) * 0.8)
    h, Hd, hm, brow = head_hair('Male_Adult_02', 'm003_head_color.tga', 'greg', (52, 40, 32), front=0.07)
    save(h, 'greg', 'm003_head_color.tga')
    _hair_recolour('Male_Adult_02', 'm003_opacity_color.tga', 'greg', 'm003_opacity_color.tga', (54, 41, 32), contrast=1.0)

    # ---- Karl (Male_Adult_13): a black jacket over a black shirt, black trousers and shoes; silver hair
    b = load('Male_Adult_13', 'm010_body_color.tga'); B = Body('m010_body_color.tga'); r = _gt_regions(B)
    jacket = (r['torso'] | r['arms']) & ~r['hands']
    b = fill(b, B, jacket, (26, 26, 28), np.clip(pat(B, 'poly_wool_herringbone', 0.15, 0.4), 0.85, 1.15), k=0.55, flatten=6)
    b = leftover_black(b, (24, 24, 26), keep=B.grow(r['hands'].astype(np.float32), 2))
    b, legs, feet = legs_shoes(b, B, r, (26, 26, 28), (14, 13, 13))
    save(b, 'karl', 'm010_body_color.tga')
    _flat_normals('Male_Adult_13', 'm010_body_normal.tga', 'karl', B.grow((jacket | legs).astype(np.float32), 4) * 0.8)
    h, Hd, hm, brow = head_hair('Male_Adult_13', 'm010_head_color.tga', 'karl', (170, 166, 160), front=0.075, contrast=0.6, skin=(1.0, 0.94, 0.9))
    save(h, 'karl', 'm010_head_color.tga')

    # ---- the waiter (Business_Male_01): white shirt sleeves, a stone waistcoat with the shirt's V and a black bow tie,
    # a long white apron from the waist to the shin over black trousers; black shoes; dark hair slicked down
    b = load('Business_Male_01', 'm005_body_color.tga'); B = Body('m005_body_color.tga'); r = _gt_regions(B); neck = r['neck']
    vee = _shirt_front(B, neck, 0.03, 0.26, 0.07, 0.004)
    collar = B.where(B.part('Neck', 'Spine2', 'Clavicle') & (B.z > neck - 0.035) & (B.z < neck + 0.03) & (np.abs(B.x) < 0.07)) & ~r['hands']
    b = fill(b, B, r['arms'] & ~r['hands'], (230, 228, 222), k=0.5, flatten=2)
    b = fill(b, B, r['torso'] & ~vee & ~collar, (190, 170, 134), np.clip(pat(B, 'poly_wool_herringbone', 0.1, 0.5), 0.85, 1.15), k=0.5, flatten=4)
    b = fill(b, B, vee | collar, (232, 230, 224), k=0.4, grow=2)
    b = recolour(b, soft(_bow_tie(B, neck).astype(np.float32), 0.4), (12, 12, 14), contrast=0.3)
    b, legs, feet = legs_shoes(b, B, r, (20, 20, 22), (12, 12, 12))
    knee = r['knee']
    apron = B.where((B.y < 0.02) & (B.z < r['pel'] + 0.06) & (B.z > knee - 0.24) & (np.abs(B.x) < 0.24)) & (r['thighs'] | r['calves'] | r['torso'])
    b = fill(b, B, apron, (228, 226, 218), k=0.4, flatten=2, grow=4)
    save(b, 'waiter', 'm005_body_color.tga')
    _flat_normals('Business_Male_01', 'm005_body_normal.tga', 'waiter', B.grow((r['torso'] | r['arms'] | legs).astype(np.float32), 4) * 0.7)
    h, Hd, hm, brow = head_hair('Business_Male_01', 'm005_head_color.tga', 'waiter', (34, 28, 25), front=0.07)
    save(h, 'waiter', 'm005_head_color.tga')
    _hair_recolour('Business_Male_01', 'm005_opacity_color.tga', 'waiter', 'm005_opacity_color.tga', (34, 28, 25), contrast=1.0, shine=1.2)


if __name__ == '__main__':
    globals()[sys.argv[1].replace('-', '_')]()
