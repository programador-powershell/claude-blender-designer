"""Mostra o mesh TEXTURIZADO (cor real) front. Eu vejo pele vs roupa como profissional."""
import bpy
mesh=max([o for o in bpy.context.scene.objects if o.type=='MESH'], key=lambda o:len(o.data.vertices))
# remove color attr da mascara (senao polui) e mostra TEXTURA
me=mesh.data
if "skin_mask" in me.color_attributes: me.color_attributes.remove(me.color_attributes["skin_mask"])
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        sp=area.spaces[0]; sp.shading.type='SOLID'; sp.shading.color_type='TEXTURE'
        region=next((r for r in area.regions if r.type=='WINDOW'),None)
        with bpy.context.temp_override(area=area,region=region):
            bpy.ops.object.select_all(action='DESELECT'); mesh.select_set(True)
            bpy.ops.view3d.view_axis(type='FRONT'); bpy.ops.view3d.view_selected()
        break
print("OK textured", mesh.name)
