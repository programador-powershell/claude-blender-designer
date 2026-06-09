"""Teste de deform: passada (pernas) + balanco (bracos) + leve coluna. Esconde esqueleto,
enquadra. Eu olho 1x se saia acompanha sem estilhacar."""
import bpy, sys
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, live_geo; importlib.reload(live_geo)

mx = bpy.data.objects.get("MixamoArmature")
b = bpy.data.objects.get("AliceBodyClean")
if b: b.hide_set(True)   # corpo nu nao usado
live_geo.pose_world("MixamoArmature", [
    ["mixamorig:LeftUpLeg","X", 30],   # perna esq frente
    ["mixamorig:RightUpLeg","X",-30],  # dir tras
    ["mixamorig:LeftLeg","X", 20],     # joelho esq
    ["mixamorig:LeftArm","X",-22],     # braco esq tras (contra-balanco)
    ["mixamorig:RightArm","X", 22],    # dir frente
    ["mixamorig:Spine1","Y", 6],
])
mx.hide_set(True)  # esconde esqueleto pra ver so a malha
live_geo.view_shot("AliceDress","FRONT")
print("OK deform_test")
