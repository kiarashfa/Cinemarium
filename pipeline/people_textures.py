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


def save(arr, character, name):
    d = os.path.join(OUT, character); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name.replace('.tga', '.png'))
    Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p)
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
    made['irving'].append(save(recolour(o, soft((oV > 0.03).astype(np.float32), 1), (118, 116, 112), contrast=1.1), 'irving', 'm004_opacity_color.tga'))
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
    made['helly'].append(save(recolour(o, soft((oV > 0.03).astype(np.float32), 1), (124, 46, 28), contrast=1.15), 'helly', 'f018_opacity_color.tga'))
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


if __name__ == '__main__':
    globals()[sys.argv[1]]()
