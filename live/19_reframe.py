"""Reenquadra cena fisica: esconde chao, foca mesa+estilhacos, vista 3/4."""
import bpy
sc=bpy.data.scenes.get("PhysicsLab")
bpy.context.window.scene=sc
chao=bpy.data.objects.get("Chao_Fisico")
if chao: chao.hide_set(True)
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces[0].shading.type='SOLID'
        region=next((r for r in area.regions if r.type=='WINDOW'),None)
        with bpy.context.temp_override(area=area, region=region):
            bpy.ops.object.select_all(action='DESELECT')
            for o in sc.collection.objects:
                if not o.hide_get(): o.select_set(True)
            bpy.ops.view3d.view_axis(type='FRONT')
            for _ in range(3): bpy.ops.view3d.view_orbit(type='ORBITRIGHT')
            for _ in range(2): bpy.ops.view3d.view_orbit(type='ORBITUP')
            bpy.ops.view3d.view_selected()
        break
print("OK reframe")
