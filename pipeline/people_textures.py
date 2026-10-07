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


if __name__ == '__main__':
    globals()[sys.argv[1].replace('-', '_')]()
