import bpy, os
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
try: sc.cycles.device = 'GPU'
except: pass
sc.cycles.samples = 48
sc.render.resolution_x = 700; sc.render.resolution_y = 900
sc.render.image_settings.file_format = 'PNG'
OUT = r'D:/Alice/tools/auto-rig-fix/work/manual_renders'
os.makedirs(OUT, exist_ok=True)
for cn in ['CAM_FRONT','CAM_SIDE','CAM_BACK']:
    c = bpy.data.objects.get(cn)
    if not c: continue
    sc.camera = c
    sc.render.filepath = os.path.join(OUT, f'manual_{cn}.png')
    bpy.ops.render.render(write_still=True)
print('RENDER OK')
