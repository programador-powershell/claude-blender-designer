import sys, bpy
sys.path.insert(0, r'D:\Alice\tools\auto-rig-fix\live')
import importlib, interior
importlib.reload(interior)
print(interior.build_geometry())
print(interior.build_dressing())
print(interior.build_lighting())
print(interior.build_cameras())
print(interior.apply_textures())
sc = bpy.context.scene
for o in bpy.data.objects:
    if o.name == 'Ceiling' or o.name.startswith('Beam'):
        o.hide_render = True
sc.render.engine = 'BLENDER_WORKBENCH'
sc.render.resolution_x = 900; sc.render.resolution_y = 800
sh = sc.display.shading
sh.light = 'STUDIO'; sh.color_type = 'SINGLE'; sh.single_color = (0.62, 0.62, 0.62)
sh.show_cavity = True; sh.cavity_type = 'BOTH'
OUT = r'D:\Alice\tools\MapVisionBuilder\output\trellis\measure'
import os; os.makedirs(OUT, exist_ok=True)
for cam, nm in [('Cam_Aerial', 'int_meas_top'), ('Cam_Iso', 'int_meas_iso')]:
    c = bpy.data.objects.get(cam)
    if not c: print('no cam', cam); continue
    sc.camera = c; sc.render.filepath = os.path.join(OUT, nm + '.png')
    bpy.ops.render.render(write_still=True)
print('HEADLESS DONE')
