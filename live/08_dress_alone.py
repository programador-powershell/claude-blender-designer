import bpy
d=bpy.data.objects.get("AliceDress"); b=bpy.data.objects.get("AliceBodyClean")
mx=bpy.data.objects.get("MixamoArmature")
if mx: mx.hide_set(True)
b.hide_set(True); d.hide_set(False)
bpy.context.view_layer.objects.active=d
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        region=next((r for r in area.regions if r.type=='WINDOW'),None)
        with bpy.context.temp_override(area=area,region=region):
            bpy.ops.object.select_all(action='DESELECT'); d.select_set(True)
            bpy.ops.view3d.view_axis(type='FRONT'); bpy.ops.view3d.view_selected()
        break
print("dress alone")
