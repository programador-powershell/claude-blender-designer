"""Importa rainha_rigged.glb em cena GeoTest. Reporta mesh/armature/bone shoulder.
Front view ANTES."""
import bpy, sys
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, game_builder; importlib.reload(game_builder)
import live_geo; importlib.reload(live_geo)

sc = bpy.data.scenes.get("GeoTest") or bpy.data.scenes.new("GeoTest")
bpy.context.window.scene = sc
for o in list(sc.collection.objects): bpy.data.objects.remove(o, do_unlink=True)

before=set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=r"D:\Alice\tools\auto-rig-fix\work\rigged\rainha_rigged.glb")
new=[o for o in bpy.data.objects if o not in before]
mesh=max([o for o in new if o.type=='MESH'], key=lambda o:len(o.data.vertices))
arm=next((o for o in new if o.type=='ARMATURE'), None)
mesh.name="rainha_geo"
print("mesh:", mesh.name, "verts:", len(mesh.data.vertices))
print("armature:", arm.name if arm else None)
print("vgroups left arm?:", [g.name for g in mesh.vertex_groups if "Left" in g.name and ("Arm" in g.name or "Hand" in g.name or "Shoulder" in g.name)])
if arm:
    for bn in ("mixamorig:LeftArm","mixamorig:LeftForeArm"):
        b=arm.data.bones.get(bn)
        if b:
            h=arm.matrix_world@b.head_local
            print(f"  {bn} head world: ({h.x:.3f},{h.y:.3f},{h.z:.3f})")
live_geo.view_shot("rainha_geo","FRONT")
print("OK geo_import")
