"""Limpa pose -> rest, salva .blend, exporta GLB rigado (dress+armature)."""
import bpy, sys, os
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, live_geo; importlib.reload(live_geo)

live_geo.clear_pose("MixamoArmature")   # volta rest
arm = bpy.data.objects.get("MixamoArmature"); arm.hide_set(False)
d = bpy.data.objects.get("AliceDress")
b = bpy.data.objects.get("AliceBodyClean")
if b: b.hide_set(True)

work = r"D:\Alice\tools\auto-rig-fix\work"
os.makedirs(work, exist_ok=True)
# salva blend
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(work, "alice_dress_rigged.blend"))

# exporta GLB so dress+armature
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='DESELECT')
d.select_set(True); arm.select_set(True)
bpy.context.view_layer.objects.active = arm
glb = os.path.join(work, "alice_dress_rigged.glb")
bpy.ops.export_scene.gltf(filepath=glb, use_selection=True, export_format='GLB',
    export_skins=True, export_yup=True, export_apply=False)
print("GLB:", glb, "size_MB:", round(os.path.getsize(glb)/1e6,2))
print("OK save_export")
