"""Recarrega rainha limpa + levanta braco esquerdo pelo OSSO (limpo, deterministico)."""
import bpy, sys
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, game_builder; importlib.reload(game_builder)
import live_geo; importlib.reload(live_geo)

sc=bpy.data.scenes.get("GeoTest") or bpy.data.scenes.new("GeoTest")
bpy.context.window.scene=sc
for o in list(sc.collection.objects): bpy.data.objects.remove(o, do_unlink=True)
before=set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=r"D:\Alice\tools\auto-rig-fix\work\rigged\rainha_rigged.glb")
new=[o for o in bpy.data.objects if o not in before]
mesh=max([o for o in new if o.type=='MESH'], key=lambda o:len(o.data.vertices)); mesh.name="rainha_geo"
arm=next((o for o in new if o.type=='ARMATURE'), None)
print("RAISE:", game_builder.raise_arm(arm.name, side="Left", height=1.0, out=0.5))
arm.hide_set(True)
live_geo.view_shot("rainha_geo","FRONT")
print("OK raise_clean", arm.name)
