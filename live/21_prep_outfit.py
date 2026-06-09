"""Prep um outfit + vista frontal. Le work/outfit.txt: 'name|fbx|arm_deg'."""
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
# esconde esqueleto, front view
arm=bpy.data.objects.get(f"Rig_{name}")
if arm: arm.hide_set(True)
live_geo.view_shot(name, "FRONT")
print("OK prep", name)
