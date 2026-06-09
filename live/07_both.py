"""Live step 07 — mostra corpo(posado)+vestido juntos. Front ortho. Teste de alinhamento."""
import bpy
d = bpy.data.objects.get("AliceDress"); b = bpy.data.objects.get("AliceBodyClean")
mx = bpy.data.objects.get("MixamoArmature")
if mx: mx.hide_set(True)
if d: d.hide_set(False)
if b: b.hide_set(False)
bpy.context.view_layer.objects.active = b
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        region=next((r for r in area.regions if r.type=='WINDOW'),None)
        with bpy.context.temp_override(area=area, region=region):
            bpy.ops.object.select_all(action='DESELECT'); d.select_set(True); b.select_set(True)
            bpy.ops.view3d.view_axis(type='FRONT'); bpy.ops.view3d.view_selected()
        break
print("OK both")
