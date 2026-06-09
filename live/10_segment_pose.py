"""Live step 10 — segmenta vestido (tool do user) + poe esqueleto bracos-baixo 70 e
aplica como REST (casa com o vestido). Saida = DADOS (sem screenshot)."""
import bpy, math, json, sys
from mathutils import Matrix
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, live_geo; importlib.reload(live_geo)

# 1. segmenta (vgroups por altura) — tool do script do user
seg = live_geo.segment_dress_mesh("AliceDress")
print("SEGMENT:", seg)

# 2. pose esqueleto bracos-baixo 70 e aplica como rest
arm = bpy.data.objects.get("MixamoArmature")
arm.hide_set(False)
bpy.context.view_layer.objects.active = arm
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
mw = arm.matrix_world
def reset(n): arm.pose.bones[n].matrix_basis = Matrix.Identity(4)
def rotY(n, deg):
    bpy.context.view_layer.update()
    pb = arm.pose.bones[n]; Mw = mw @ pb.matrix; head = Mw.translation.copy()
    R = Matrix.Rotation(math.radians(deg), 4, 'Y')
    pb.matrix = mw.inverted() @ (Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ Mw)
for n in ("mixamorig:LeftArm","mixamorig:RightArm","mixamorig:LeftForeArm","mixamorig:RightForeArm"):
    reset(n)
bpy.context.view_layer.update()
rotY("mixamorig:LeftArm",  +70); rotY("mixamorig:RightArm", -70)
bpy.context.view_layer.update()

# aplica pose como REST (rest = bracos-baixo). body bound segue, sera ignorado.
bpy.ops.pose.armature_apply(selected=False)
bpy.ops.object.mode_set(mode='OBJECT')

# verifica posicoes finais dos ossos de braco (rest agora) em world
arm = bpy.data.objects.get("MixamoArmature")
for n in ("mixamorig:LeftArm","mixamorig:LeftForeArm","mixamorig:RightArm","mixamorig:RightForeArm"):
    b = arm.data.bones[n]
    h = mw @ b.head_local; t = mw @ b.tail_local
    print(f"  {n}: head=({h.x:.3f},{h.y:.3f},{h.z:.3f}) tail=({t.x:.3f},{t.y:.3f},{t.z:.3f})")
print("OK segment+pose+restapply")
