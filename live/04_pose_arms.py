"""Live step 04 — pose bracos pra baixo via matriz direta (sem ops/selecao).
Rotaciona LeftArm/RightArm em Y GLOBAL em torno da cabeca do osso.
Le ANGLE de work/arm_angle.txt (default 78). Idempotente (reset matrix_basis)."""
import bpy, math
from mathutils import Matrix

ANGLE = 78.0
try:
    ANGLE = float(open(r"D:/Alice/tools/auto-rig-fix/work/arm_angle.txt").read().strip())
except Exception: pass
print("ANGLE =", ANGLE)

arm = bpy.data.objects.get("MixamoArmature")
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')

mw = arm.matrix_world

def reset(name):
    arm.pose.bones[name].matrix_basis = Matrix.Identity(4)

def rot_world_Y(name, deg):
    bpy.context.view_layer.update()
    pb = arm.pose.bones[name]
    Mw = mw @ pb.matrix                       # bone em world
    head = Mw.translation.copy()
    R = Matrix.Rotation(math.radians(deg), 4, 'Y')   # Y global
    Mw_new = Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ Mw
    pb.matrix = mw.inverted() @ Mw_new        # volta p/ armature space

# reset T-pose nos dois bracos (idempotente)
for n in ("mixamorig:LeftArm","mixamorig:RightArm",
          "mixamorig:LeftForeArm","mixamorig:RightForeArm"):
    reset(n)
bpy.context.view_layer.update()

rot_world_Y("mixamorig:LeftArm",  +ANGLE)
rot_world_Y("mixamorig:RightArm", -ANGLE)
bpy.context.view_layer.update()

# corpo visivel, vestido escondido, front ortho
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
print("OK pose", ANGLE)
