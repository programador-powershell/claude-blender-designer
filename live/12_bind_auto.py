"""Live step 12 — bind dress direto no esqueleto (auto bone-heat). Mede vgroups via dados."""
import bpy, time
d = bpy.data.objects.get("AliceDress")
arm = bpy.data.objects.get("MixamoArmature")
arm.hide_set(False)

# limpa modifiers/parent antigos do dress
for m in list(d.modifiers): d.modifiers.remove(m)
d.parent = None
# limpa vgroups de segmentacao? NAO — guarda Barra/Cintura. auto-weight cria os de bone.

bpy.ops.object.select_all(action='DESELECT')
d.select_set(True); arm.select_set(True)
bpy.context.view_layer.objects.active = arm
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

t0=time.time()
err=None
try:
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
except Exception as e:
    err=str(e)
dt=time.time()-t0

bone_vgs=[g.name for g in d.vertex_groups if g.name.startswith("mixamorig")]
print(f"bind dt={dt:.1f}s err={err}")
print(f"bone vgroups criados: {len(bone_vgs)}")
print(f"total vgroups: {len(d.vertex_groups)} (inclui Barra/Cintura/Corpo)")
print("OK bind_auto")
