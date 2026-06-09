import bpy, math, random
from collections import Counter

arm = bpy.data.objects['Alice_Rig']
pieces = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('PA')]
print(f'rigging {len(pieces)} pecas...')

# Auto weights por peca (meshes limpas manifold -> bone heat OK)
ok_count = 0
for o in pieces:
    try:
        bpy.ops.object.select_all(action='DESELECT')
        o.select_set(True); arm.select_set(True)
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
        ok_count += 1
    except Exception as e:
        print(f'  {o.name}: FAIL {e}')
print(f'rigged: {ok_count}/{len(pieces)}')

# Verify sample (saia teal)
saia = bpy.data.objects.get('PA07_Saia_Teal_Tier1')
if saia and saia.vertex_groups:
    vg = {g.index: g.name for g in saia.vertex_groups}
    cnt = Counter()
    for v in saia.data.vertices:
        bw=0; bb=None
        for g in v.groups:
            if g.weight>bw: bw=g.weight; bb=vg.get(g.group)
        cnt[bb]+=1
    print('saia weights:', cnt.most_common(4))

# POSE TEST: braco + perna
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
la = arm.pose.bones.get('mixamorig:LeftArm')
if la: la.rotation_mode='XYZ'; la.rotation_euler=(0,0,math.radians(-45))
rl = arm.pose.bones.get('mixamorig:RightUpLeg')
if rl: rl.rotation_mode='XYZ'; rl.rotation_euler=(math.radians(-22),0,0)
bpy.ops.object.mode_set(mode='OBJECT')
sc = bpy.context.scene
sc.camera = bpy.data.objects['CAM_FRONT']
sc.render.filepath = r'D:/Alice/tools/auto-rig-fix/work/zero_renders/pose_test.png'
bpy.ops.render.render(write_still=True)

# Reset pose
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
for pb in arm.pose.bones:
    pb.rotation_euler = (0,0,0); pb.rotation_quaternion = (1,0,0,0)
bpy.ops.object.mode_set(mode='OBJECT')

# SAVE + EXPORT
bpy.ops.wm.save_as_mainfile(filepath=r'D:/Alice/tools/auto-rig-fix/work/alice_chapeleiro_ZERO.blend')
bpy.ops.object.select_all(action='SELECT')
for o in bpy.data.objects:
    if o.type in ('CAMERA','LIGHT'): o.select_set(False)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.gltf(
    filepath=r'D:/Alice/tools/auto-rig-fix/work/alice_chapeleiro_ZERO.glb',
    use_selection=True, export_format='GLB', export_apply=False,
    export_materials='EXPORT', export_skins=True)
print('ZERO BUILD SAVED + EXPORTED')
