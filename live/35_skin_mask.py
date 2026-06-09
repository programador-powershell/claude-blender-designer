"""Roda texture_skin_mask no maior mesh carregado + frame front. Ve separacao."""
import bpy, sys
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, game_builder; importlib.reload(game_builder)

mesh=max([o for o in bpy.context.scene.objects if o.type=='MESH'], key=lambda o:len(o.data.vertices))
print("mesh:", mesh.name, "verts:", len(mesh.data.vertices))
print("MASK:", game_builder.texture_skin_mask(mesh.name))
# frame front (sem esconder rig pq cor)
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        sp=area.spaces[0]; sp.shading.type='SOLID'; sp.shading.color_type='VERTEX'
        region=next((r for r in area.regions if r.type=='WINDOW'),None)
        with bpy.context.temp_override(area=area,region=region):
            bpy.ops.object.select_all(action='DESELECT'); mesh.select_set(True)
            bpy.ops.view3d.view_axis(type='FRONT'); bpy.ops.view3d.view_selected()
        break
print("OK skin_mask")
