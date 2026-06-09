"""Live step 03 — inspeciona bones de braco da MixamoArmature + corpo sozinho front ortho."""
import bpy, math

arm = bpy.data.objects.get("MixamoArmature")
print("=== ARM BONES (ombro/braco/antebraco/mao) ===")
for b in arm.data.bones:
    n = b.name
    if any(k in n for k in ("Shoulder","Arm","ForeArm","Hand")) and "Hand" != n[-4:].strip(":") :
        h = arm.matrix_world @ b.head_local
        t = arm.matrix_world @ b.tail_local
        print(f"  {n}: head=({h.x:.3f},{h.y:.3f},{h.z:.3f}) tail=({t.x:.3f},{t.y:.3f},{t.z:.3f})")

# esconde vestido, mostra so corpo
d = bpy.data.objects.get("AliceDress")
b = bpy.data.objects.get("AliceBodyClean")
if d: d.hide_set(True)
if b: b.hide_set(False)

for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        region=next((r for r in area.regions if r.type=='WINDOW'),None)
        with bpy.context.temp_override(area=area, region=region):
            bpy.ops.object.select_all(action='DESELECT')
            b.select_set(True)
            bpy.ops.view3d.view_axis(type='FRONT')
            bpy.ops.view3d.view_selected()
        break
print("OK inspect")
