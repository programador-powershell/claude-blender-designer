import bpy

# Fix mancha branca chapeu: faces do Hem_Lace em z>1.55 -> teal
hem = bpy.data.objects.get('PA_Hem_Lace_Cream')
m_teal = bpy.data.materials['MAT_Teal_Fabric']
if hem:
    if 'MAT_Teal_Fabric' not in [m.name for m in hem.data.materials]:
        hem.data.materials.append(m_teal)
    idx_teal = [m.name for m in hem.data.materials].index('MAT_Teal_Fabric')
    fixed = 0
    for poly in hem.data.polygons:
        c = hem.matrix_world @ poly.center
        if c.z > 1.50:
            poly.material_index = idx_teal; fixed += 1
    print(f'hat patch: {fixed} faces -> teal')

# Cabelo idem (faces cream perdidas)
cab = bpy.data.objects.get('PA_Cabelo')

# Pose test final: valida rig pos-smoothing
import math
arm = bpy.data.objects['Alice_Base_Rig']
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
for pb in arm.pose.bones:
    pb.rotation_euler = (0,0,0); pb.rotation_quaternion = (1,0,0,0)
la = arm.pose.bones.get('mixamorig:LeftArm')
if la: la.rotation_mode='XYZ'; la.rotation_euler=(0,0,math.radians(-50))
rl = arm.pose.bones.get('mixamorig:RightUpLeg')
if rl: rl.rotation_mode='XYZ'; rl.rotation_euler=(math.radians(-25),0,0)
bpy.ops.object.mode_set(mode='OBJECT')
sc = bpy.context.scene
sc.camera = bpy.data.objects['CAM_FRONT']
sc.render.filepath = r'D:/Alice/tools/auto-rig-fix/work/manual_renders/pose_final.png'
bpy.ops.render.render(write_still=True)

# Reset pose
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
for pb in arm.pose.bones:
    pb.rotation_euler = (0,0,0); pb.rotation_quaternion = (1,0,0,0)
bpy.ops.object.mode_set(mode='OBJECT')

# Save + export GLB final com TODAS pecas separadas rigadas
bpy.ops.wm.save_mainfile()
bpy.ops.object.select_all(action='SELECT')
for o in bpy.data.objects:
    if o.type in ('CAMERA','LIGHT'): o.select_set(False)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.gltf(
    filepath=r'D:/Alice/tools/auto-rig-fix/work/alice_chapeleiro_FINAL.glb',
    use_selection=True, export_format='GLB', export_apply=False,
    export_materials='EXPORT', export_skins=True)
print('FINAL EXPORTED')
