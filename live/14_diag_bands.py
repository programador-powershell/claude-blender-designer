"""Diagnostico por faixa: % verts SEM peso de osso, por banda Z. Ve onde bone-heat falhou."""
import bpy
d=bpy.data.objects.get("AliceDress"); me=d.data
bone_idx={g.index for g in d.vertex_groups if g.name.startswith("mixamorig")}
zs=[v.co.z for v in me.vertices]; mn=min(zs); mx=max(zs); h=mx-mn
band={}
for v in me.vertices:
    zr=(v.co.z-mn)/h
    bz=round(zr*10)/10
    e=band.setdefault(bz,{"n":0,"unw":0})
    e["n"]+=1
    wsum=sum(g.weight for g in v.groups if g.group in bone_idx)
    if wsum<1e-4: e["unw"]+=1
print("zr | n | sem_peso | %")
for bz in sorted(band):
    e=band[bz]; pct=100*e["unw"]/e["n"]
    print(f"  {bz:.1f} n={e['n']:6d} unw={e['unw']:6d} {pct:5.1f}%")
