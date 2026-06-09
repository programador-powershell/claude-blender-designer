"""Demo fisica: cria cena-teste, classifica, monta fisica. Enquadra pra eu ver."""
import bpy, sys
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, game_builder; importlib.reload(game_builder)
import live_geo; importlib.reload(live_geo)

print("BUILD:", game_builder.build_test_teascene())
print("CLASSIFY:", game_builder.classify_scene())
print("PHYSICS:", game_builder.setup_physics())

# enquadra a cena lab (3/4-ish via FRONT depois orbit nao da; uso FRONT)
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces[0].shading.type='SOLID'
        region=next((r for r in area.regions if r.type=='WINDOW'),None)
        with bpy.context.temp_override(area=area, region=region):
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.view3d.view_axis(type='FRONT'); bpy.ops.view3d.view_selected()
        break
print("OK physics_demo")
