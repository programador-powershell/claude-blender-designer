"""Live step 06 — tuna braco+antebraco com feedback numerico do punho.
Le work/pose.txt: 'arm_deg fore_deg' (ex '90 10'). Mira punho x~0.20 z~0.85."""
import bpy, math
from mathutils import Matrix

arm_deg, fore_deg = 90.0, 0.0
try:
    parts = open(r"D:/Alice/tools/auto-rig-fix/work/pose.txt").read().split()
    arm_deg = float(parts[0]); fore_deg = float(parts[1]) if len(parts)>1 else 0.0
except Exception: pass
print(f"arm_deg={arm_deg} fore_deg={fore_deg}")

arm = bpy.data.objects.get("MixamoArmature")
arm.hide_set(False)                                  # visivel ANTES de virar active
bpy.context.view_layer.objects.active = arm          # active = arm (visivel)
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
mw = arm.matrix_world

def reset(n): arm.pose.bones[n].matrix_basis = Matrix.Identity(4)
def rotY(n, deg):
    bpy.context.view_layer.update()
    pb = arm.pose.bones[n]
    Mw = mw @ pb.matrix
    head = Mw.translation.copy()
    R = Matrix.Rotation(math.radians(deg), 4, 'Y')
    pb.matrix = mw.inverted() @ (Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ Mw)

for n in ("mixamorig:LeftArm","mixamorig:RightArm","mixamorig:LeftForeArm","mixamorig:RightForeArm"):
    reset(n)
bpy.context.view_layer.update()
rotY("mixamorig:LeftArm",  +arm_deg)
rotY("mixamorig:RightArm", -arm_deg)
rotY("mixamorig:LeftForeArm",  +fore_deg)
rotY("mixamorig:RightForeArm", -fore_deg)
bpy.context.view_layer.update()

# feedback: punho (tail do ForeArm) em world
for side in ("Left","Right"):
    pb = arm.pose.bones[f"mixamorig:{side}ForeArm"]
    wrist = mw @ pb.tail
    print(f"  {side} wrist world: x={wrist.x:.3f} y={wrist.y:.3f} z={wrist.z:.3f}")

arm.hide_set(True)
bpy.ops.object.mode_set(mode='OBJECT')
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
print("OK tune")
