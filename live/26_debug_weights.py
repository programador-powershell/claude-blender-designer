import bpy, sys
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, live_geo; importlib.reload(live_geo)
name="cheshire"; arm_name=f"Rig_{name}"
mesh=bpy.data.objects.get(name); arm=bpy.data.objects.get(arm_name)
# nomes vgroup vs bones
vg=[g.name for g in mesh.vertex_groups]
bones=[b.name for b in arm.data.bones]
print("vgroups (5):", vg[:5], "...", len(vg))
print("bones (5):", bones[:5], "...", len(bones))
print("match LeftUpLeg vg?", "mixamorig:LeftUpLeg" in vg, " bone?", "mixamorig:LeftUpLeg" in bones)
# max weight em alguns grupos
import collections
for gname in ("mixamorig:Hips","mixamorig:LeftUpLeg","mixamorig:Spine","mixamorig:LeftArm"):
    g=mesh.vertex_groups.get(gname)
    if not g: print(gname,"AUSENTE"); continue
    gi=g.index; mx=0.0; cnt=0
    for v in mesh.data.vertices:
        for gg in v.groups:
            if gg.group==gi and gg.weight>1e-4: cnt+=1; mx=max(mx,gg.weight)
    print(f"{gname}: verts_com_peso={cnt} maxw={mx:.3f}")
# modifier show?
m=mesh.modifiers.get("Armature")
print("modifier show_viewport:", m.show_viewport, "use_vertex_groups:", m.use_vertex_groups, "obj:", m.object.name)
print("OK")
