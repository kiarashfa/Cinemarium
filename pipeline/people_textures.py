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


def leftover_black(a, target=(15, 15, 17)):
    """Anything still pale and grey (a collar, a shoe's tongue, a tag the texel map does not reach) turns black;
    skin is warm and saturated, so it stays."""
    H, S, V = hsv(a); m = ((V > 0.38) & (S < 0.24)).astype(np.float32)
    m = soft(np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)), np.float32) / 255, 0.5)
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


if __name__ == '__main__':
    globals()[sys.argv[1].replace('-', '_')]()
