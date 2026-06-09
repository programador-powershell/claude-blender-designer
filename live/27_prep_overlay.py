"""Prep outfit (com alinhamento) + overlay esqueleto no mesh. Le outfit.txt."""
import bpy, sys
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, game_builder; importlib.reload(game_builder)
import live_geo; importlib.reload(live_geo)
name, fbx, deg = "cheshire", r"E:\References\3D\SK_Alice_Cheshire.fbx", 70
try:
    parts=open(r"D:/Alice/tools/auto-rig-fix/work/outfit.txt").read().strip().split("|")
    name=parts[0]; fbx=parts[1]; deg=float(parts[2])
except Exception: pass
print("PREP:", game_builder.prep_outfit(fbx, name, arm_deg=deg))
# overlay: esqueleto em FRENTE, stick, sobre o mesh
arm=bpy.data.objects.get(f"Rig_{name}"); mesh=bpy.data.objects.get(name)
arm.hide_set(False); arm.show_in_front=True; arm.data.display_type='STICK'
bpy.context.view_layer.objects.active=mesh
if bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces[0].shading.type='SOLID'
        region=next((r for r in area.regions if r.type=='WINDOW'),None)
        with bpy.context.temp_override(area=area,region=region):
            bpy.ops.object.select_all(action='DESELECT'); mesh.select_set(True)
            bpy.ops.view3d.view_axis(type='FRONT'); bpy.ops.view3d.view_selected()
        break
print("OK prep_overlay", name)
