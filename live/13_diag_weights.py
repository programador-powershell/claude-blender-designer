"""Diagnostico: peso dominante dos verts da saia (zr<0.30) + quantos sem peso."""
import bpy
from collections import Counter
d=bpy.data.objects.get("AliceDress"); me=d.data
gi={g.index:g.name for g in d.vertex_groups}
bone_idx={g.index for g in d.vertex_groups if g.name.startswith("mixamorig")}
zs=[v.co.z for v in me.vertices]; mn=min(zs); mx=max(zs); h=mx-mn
dom=Counter(); unweighted=0; total=0
for v in me.vertices:
    zr=(v.co.z-mn)/h
    if zr>=0.30: continue
    total+=1
    best=None; bestw=0.0; wsum=0.0
    for g in v.groups:
        if g.group not in bone_idx: continue   # so ossos
        wsum+=g.weight
        if g.weight>bestw: bestw=g.weight; best=g.group
    if wsum<1e-4 or best is None: unweighted+=1
    else: dom[gi.get(best,"?")]+=1
print(f"verts saia(zr<0.30): {total}  sem_peso: {unweighted}")
print("top dominantes:")
for name,c in dom.most_common(8):
    print(f"  {name}: {c}")
