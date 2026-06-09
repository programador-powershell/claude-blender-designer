"""Live step 05 — deleta Armature junk do vestido (65 bones,0 peso), esconde display
do esqueleto, mostra so malha corpo, front ortho. Ve braco posado limpo."""
import bpy

# deleta a Armature junk do vestido (nome exato "Armature")
junk = bpy.data.objects.get("Armature")
if junk and junk.type == 'ARMATURE':
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    junk.select_set(True); bpy.context.view_layer.objects.active = junk
    bpy.ops.object.delete()
    print("deletou Armature junk do vestido")

# esconde DISPLAY do esqueleto Mixamo (nao deleta — so tira do viewport)
mx = bpy.data.objects.get("MixamoArmature")
if mx: mx.hide_set(True)

d = bpy.data.objects.get("AliceDress"); b = bpy.data.objects.get("AliceBodyClean")
if d: d.hide_set(True)
if b: b.hide_set(False)
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        region=next((r for r in area.regions if r.type=='WINDOW'),None)
        with bpy.context.temp_override(area=area, region=region):
            bpy.ops.object.select_all(action='DESELECT'); b.select_set(True)
            bpy.ops.view3d.view_axis(type='FRONT'); bpy.ops.view3d.view_selected()
        break
print("OK clean view")
