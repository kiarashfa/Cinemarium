# Entry point: blender -b --factory-startup -P pipeline/blender/build.py -- <room> <stage> [key=value ...]
#   stage: preview  (a Cycles render from the web camera, to judge the room)
#          bake     (light-map atlases, denoised, plus room.glb and room.json for the web)
#          people   (only the people: their glTF files and their part of room.json, then a look at each)
import sys, os
sys.dont_write_bytecode = True   # no __pycache__ next to the scripts
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cine

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
room, stage = argv[0], argv[1]
args = {k: (float(v) if v.replace('.', '', 1).isdigit() else v) for k, v in (a.split('=', 1) for a in argv[2:])}
mod = __import__(f'rooms.{room}_build', fromlist=['build'])
if stage in ('bake', 'people'): args['full'] = True
sc, M, objs, phantoms, seated, cams = mod.build(args)
out = os.path.join(cine.OUT, room); os.makedirs(out, exist_ok=True)
if stage == 'preview':
    for which in str(args.get('cams', 'case,close')).split(','):
        mod.preview(sc, cams, which, int(args.get('samples', 128)), os.path.join(out, f'preview_{which}.png'))
elif stage == 'bake':
    mod.bake(sc, objs, phantoms, seated, args)
elif stage == 'people':
    mod.people_stage(sc, cams, seated, args)
cine.log('done', room, stage)
