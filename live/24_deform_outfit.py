"""Teste deform de um outfit (passada). Le work/outfit.txt."""
import bpy, sys
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, live_geo; importlib.reload(live_geo)
name="cheshire"
try: name=open(r"D:/Alice/tools/auto-rig-fix/work/outfit.txt").read().strip().split("|")[0]
except Exception: pass
arm=f"Rig_{name}"
live_geo.pose_world(arm, [
    ["mixamorig:LeftUpLeg","X",30],["mixamorig:RightUpLeg","X",-30],
    ["mixamorig:LeftLeg","X",20],
    ["mixamorig:LeftArm","X",-22],["mixamorig:RightArm","X",22],
    ["mixamorig:Spine1","Y",6],
])
bpy.data.objects.get(arm).hide_set(True)
live_geo.view_shot(name,"FRONT")
print("OK deform", name)
