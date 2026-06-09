"""Live step 09 — esqueleto(70deg) sobre o vestido. Confere se ossos correm DENTRO
dos bracos/pernas do vestido (pre-requisito SHD)."""
import bpy
d=bpy.data.objects.get("AliceDress"); b=bpy.data.objects.get("AliceBodyClean")
mx=bpy.data.objects.get("MixamoArmature")
# esconde corpo, mostra vestido + esqueleto em FRENTE (xray do armature)
b.hide_set(True)
d.hide_set(False)
mx.hide_set(False)
mx.show_in_front = True
mx.data.display_type = 'STICK'
bpy.context.view_layer.objects.active = d
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        sp=area.spaces[0]; sp.shading.type='SOLID'
        region=next((r for r in area.regions if r.type=='WINDOW'),None)
        with bpy.context.temp_override(area=area,region=region):
            bpy.ops.object.select_all(action='DESELECT'); d.select_set(True)
            bpy.ops.view3d.view_axis(type='FRONT'); bpy.ops.view3d.view_selected()
        break
print("OK overlay")
