import bpy, sys
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, live_geo; importlib.reload(live_geo)
name="cheshire"; arm_name=f"Rig_{name}"
mesh=bpy.data.objects.get(name); arm=bpy.data.objects.get(arm_name)
print("mesh modifiers:", [(m.name,m.type,getattr(m,'object',None).name if getattr(m,'object',None) else None) for m in mesh.modifiers])
print("mesh parent:", mesh.parent.name if mesh.parent else None)
# rest bbox evaluated
deps=bpy.context.evaluated_depsgraph_get()
def ebox(o):
    oe=o.evaluated_get(deps); me=oe.to_mesh()
    co=[oe.matrix_world @ v.co for v in me.vertices]
    zs=[c.z for c in co]; xs=[c.x for c in co]
    r=(round(min(xs),3),round(max(xs),3),round(min(zs),3),round(max(zs),3))
    oe.to_mesh_clear(); return r
print("bbox REST (x0,x1,z0,z1):", ebox(mesh))
# aplica pose
live_geo.pose_world(arm_name, [["mixamorig:LeftUpLeg","X",35],["mixamorig:RightUpLeg","X",-35]])
deps=bpy.context.evaluated_depsgraph_get()
print("bbox POSED:", ebox(mesh))
# confere matrix_basis do bone
import math
pb=arm.pose.bones["mixamorig:LeftUpLeg"]
print("LeftUpLeg basis != identity:", any(abs(pb.matrix_basis[i][j]-(1 if i==j else 0))>1e-4 for i in range(4) for j in range(4)))
print("OK debug")
