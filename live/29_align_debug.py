"""Debug align isolado: importa skel, apply, scale, translate via matrix_world.
Print hips world Y em cada etapa."""
import bpy
from mathutils import Matrix, Vector
BODY=r"D:\Alice\tools\body-rebuild\out\alice_body_clean.fbx"
sc=bpy.data.scenes.get("RigLab") or bpy.data.scenes.new("RigLab")
bpy.context.window.scene=sc
# remove skel antigo
for o in list(sc.collection.objects):
    if o.type=='ARMATURE': bpy.data.objects.remove(o, do_unlink=True)
before=set(bpy.data.objects); bpy.ops.import_scene.fbx(filepath=BODY)
newb=[o for o in bpy.data.objects if o not in before]
arm=next((o for o in newb if o.type=='ARMATURE'),None)
for o in newb:
    if o is not arm: bpy.data.objects.remove(o,do_unlink=True)
def hipsY(): return round((arm.matrix_world @ arm.data.bones["mixamorig:Hips"].head_local).y,4)
def sY():
    pts=[arm.matrix_world@b.head_local for b in arm.data.bones]+[arm.matrix_world@b.tail_local for b in arm.data.bones]
    ys=[p.y for p in pts]; return round((min(ys)+max(ys))/2,4)
print("import      hipsY=",hipsY()," sY=",sY()," loc=",[round(x,3) for x in arm.location]," rotX=",round(arm.rotation_euler.x*57.3,1)," scale=",round(arm.scale.x,4))
bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); bpy.context.view_layer.objects.active=arm
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
print("after apply hipsY=",hipsY()," sY=",sY()," loc=",[round(x,3) for x in arm.location])
# translate em world -sY
delta=Vector((0, -sY(), 0))
arm.matrix_world = Matrix.Translation(delta) @ arm.matrix_world
bpy.context.view_layer.update()
print("after trans hipsY=",hipsY()," sY=",sY()," loc=",[round(x,3) for x in arm.location])
print("OK align_debug")
