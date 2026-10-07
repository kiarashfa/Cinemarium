# Light maps for the web: float EXR (the bake's master) -> 8-bit sRGB WebP of E / scale, where scale is the
# 99.9th percentile of the atlas (diffuse room light has a modest range; the rare brighter texels clip).
# The web loads them as sRGB textures and sets lightMapIntensity = pi * scale.
# Usage: blender -b --factory-startup -P pipeline/blender/encode_lightmaps.py -- <room>
import bpy, sys, os, json
sys.dont_write_bytecode = True   # no __pycache__ next to the scripts
import numpy as np

room = sys.argv[sys.argv.index('--') + 1]
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
web = os.path.join(ROOT, 'public', 'rooms', room)
meta_path = os.path.join(web, 'room.json')
meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
sc = bpy.context.scene
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'; sc.view_settings.exposure = 0; sc.view_settings.gamma = 1
sc.display_settings.display_device = 'sRGB'
scales = {}
for group in ('arch', 'furn'):
    src = os.path.join(ROOT, 'pipeline', 'out', room, f'lm_{group}.exr')
    if not os.path.exists(src): src = os.path.join(web, f'lm_{group}.exr')
    if not os.path.exists(src): continue
    img = bpy.data.images.load(src); w, h = img.size
    px = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(px); px = px.reshape(h, w, 4)
    rgb = px[..., :3]; lum = rgb.max(-1)
    lit = lum[lum > 1e-4]
    scale = float(np.percentile(lit, 99.9)) if lit.size else 1.0
    out = np.clip(rgb / scale, 0, 1)
    # dither before quantisation so slow gradients on walls do not band
    out = out + (np.random.default_rng(1).random(out.shape, np.float32) - 0.5) / 255 * 0.8
    o = bpy.data.images.new(f'lm_{group}_web', w, h, float_buffer=True, alpha=False)
    o.colorspace_settings.name = 'Linear Rec.709'
    buf = np.ones((h, w, 4), np.float32); buf[..., :3] = np.clip(out, 0, 1)
    o.pixels.foreach_set(buf.ravel())
    sc.render.image_settings.file_format = 'WEBP'; sc.render.image_settings.quality = 92; sc.render.image_settings.color_mode = 'RGB'
    dst = os.path.join(web, f'lm_{group}.webp'); o.save_render(dst, scene=sc)
    scales[group] = scale
    print(f'[lm] {group}: scale {scale:.3f}, {os.path.getsize(dst) / 1e6:.2f} MB')
if meta:
    meta['lightmaps'] = {g: f'lm_{g}.webp' for g in scales}
    meta['lightmapScale'] = scales
    json.dump(meta, open(meta_path, 'w'), indent=1)
    print('[lm] room.json updated')
