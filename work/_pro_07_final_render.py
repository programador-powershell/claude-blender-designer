import bpy, math, os

rig = bpy.data.objects['AliceRig']

# POSE A relaxada (ref turnaround): bracos ~65 graus pra baixo
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='POSE')
for pb in rig.pose.bones:
    pb.rotation_mode = 'XYZ'
    pb.rotation_euler = (0,0,0)
for S, g in [('L',1),('R',-1)]:
    ua = rig.pose.bones.get(f'UpperArm_{S}')
    if ua: ua.rotation_euler = (0, 0, g*math.radians(-62))
    fa = rig.pose.bones.get(f'ForeArm_{S}')
    if fa: fa.rotation_euler = (0, 0, g*math.radians(-8))
    # dedos leve curva natural
    for f in ['Index','Middle','Ring','Pinky']:
        for k in [1,2,3]:
            pb = rig.pose.bones.get(f'{f}{k}_{S}')
            if pb: pb.rotation_euler = (math.radians(12), 0, 0)
bpy.ops.object.mode_set(mode='OBJECT')

# Luz refinada + bg
for nm, e in [('L_KEY',360),('L_FILL',110),('L_RIM',300)]:
    o = bpy.data.objects.get(nm)
    if o: o.data.energy = e
sc = bpy.context.scene
sc.view_settings.view_transform = 'Filmic'
sc.view_settings.look = 'Medium High Contrast'
sc.render.engine = 'CYCLES'
try: sc.cycles.device = 'GPU'
except: pass
sc.cycles.samples = 96
sc.render.resolution_x = 900
sc.render.resolution_y = 1200

OUT = r'D:/Alice/tools/auto-rig-fix/work/pro_renders'
os.makedirs(OUT, exist_ok=True)
for cn, nm in [('CAM_FRONT','FINAL_front'),('CAM_SIDE','FINAL_side'),('CAM_BACK','FINAL_back')]:
    sc.camera = bpy.data.objects[cn]
    sc.render.filepath = os.path.join(OUT, f'{nm}.png')
    bpy.ops.render.render(write_still=True)
print('FINAL RENDERS OK')
bpy.ops.wm.save_mainfile()
