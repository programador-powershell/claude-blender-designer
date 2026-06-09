"""Importa cheshire RAW (so apply rotation+scale do fbx), mede extents por eixo +
euler. Detecta qual eixo e a altura real (corpo em pe)."""
import bpy
sc=bpy.data.scenes.get("RigLab") or bpy.data.scenes.new("RigLab")
bpy.context.window.scene=sc
for o in list(sc.collection.objects): bpy.data.objects.remove(o, do_unlink=True)
before=set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=r"E:\References\3D\SK_Alice_Cheshire.fbx")
new=[o for o in bpy.data.objects if o not in before]
mesh=max([o for o in new if o.type=='MESH'], key=lambda o:len(o.data.vertices))
print("euler(deg):", [round(a*57.2958,1) for a in mesh.rotation_euler], "scale:", [round(s,4) for s in mesh.scale])
co=[mesh.matrix_world @ v.co for v in mesh.data.vertices]
xs=[c.x for c in co]; ys=[c.y for c in co]; zs=[c.z for c in co]
dx=max(xs)-min(xs); dy=max(ys)-min(ys); dz=max(zs)-min(zs)
print(f"raw extents dx={dx:.3f} dy={dy:.3f} dz={dz:.3f}")
print(f"  X[{min(xs):.2f},{max(xs):.2f}] Y[{min(ys):.2f},{max(ys):.2f}] Z[{min(zs):.2f},{max(zs):.2f}]")
print("maior eixo (=altura provavel):", max([("X",dx),("Y",dy),("Z",dz)], key=lambda t:t[1])[0])
print("OK orient")
