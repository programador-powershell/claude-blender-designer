"""SHD skinning de 1 mesh (corpo nua) + armature. Roda no Blender 5.1 (addon SHD).
  blender -b -P rig_shd_single.py -- <out.blend> body=<body.fbx> [res=128 loops=5 samples=8 influence=12 falloff=2.0]
"""
import sys, os, types as _types, subprocess
import bpy, addon_utils
argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
out = body_file = None
res, loops, samples, influence, falloff = 128, 5, 8, 12, 2.0
for a in argv:
    if a.startswith("body="): body_file = os.path.abspath(a[5:])
    elif a.startswith("res="): res = int(a[4:])
    elif a.startswith("loops="): loops = int(a[6:])
    elif a.startswith("samples="): samples = int(a[8:])
    elif a.startswith("influence="): influence = int(a[10:])
    elif a.startswith("falloff="): falloff = float(a[8:])
    else: out = os.path.abspath(a)
assert out and body_file, "need out + body="

bpy.ops.wm.read_factory_settings(use_empty=True)
ok = addon_utils.enable("surface_heat_diffuse_skinning", default_set=True, persistent=True)
assert hasattr(bpy.context.scene, "surface_resolution"), "SHD addon nao registrou (instalar no 5.1)"
bpy.ops.import_scene.fbx(filepath=body_file)
for o in list(bpy.data.objects):
    if o.type in ("CAMERA", "LIGHT"): bpy.data.objects.remove(o, do_unlink=True)
body = next(o for o in bpy.data.objects if o.type == "MESH")
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
body.name = "Corpo"; arm.name = "MixamoArmature"
for m in list(body.modifiers):
    if m.type == "ARMATURE": body.modifiers.remove(m)
body.vertex_groups.clear()
print(f"[shd] body verts={len(body.data.vertices)} bones={len(arm.data.bones)}")

sc = bpy.context.scene
sc.surface_resolution = res; sc.surface_loops = loops; sc.surface_samples = samples
sc.surface_influence = influence; sc.surface_falloff = falloff
if hasattr(sc, "surface_protect"): sc.surface_protect = False
if hasattr(sc, "detect_surface_solidify"): sc.detect_surface_solidify = False

import surface_heat_diffuse_skinning as SHD
addon_dir = os.path.dirname(SHD.__file__); data_dir = os.path.join(addon_dir, "data"); os.makedirs(data_dir, exist_ok=True)
op = SHD.SFC_OT_ModalTimerOperator
dummy = _types.SimpleNamespace(_objs=[], _permulation=[], _selected_indices=[], _selected_group_index_weights=[])
bpy.ops.object.select_all(action="DESELECT"); body.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active = arm
objs = [body]; dummy._objs = objs
bpy.context.view_layer.objects.active = body; bpy.ops.object.mode_set(mode="OBJECT")
op.write_mesh_data(dummy, objs, os.path.join(data_dir, "untitled-mesh.txt"))
bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode="OBJECT")
op.write_bone_data(dummy, arm, os.path.join(data_dir, "untitled-bone.txt"))
exe = os.path.join(addon_dir, "bin", "Windows", "x64", "shd.exe")
print(f"[shd] rodando shd.exe res={res} infl={influence} falloff={falloff}...")
proc = subprocess.run(
    [exe, "untitled-mesh.txt", "untitled-bone.txt", "untitled-weight.txt",
     str(res), str(loops), str(samples), str(influence), str(falloff), sc.surface_sharpness, "n"],
    cwd=data_dir, capture_output=True, text=True, timeout=1800)
print(f"[shd] exit={proc.returncode} tail={proc.stdout.strip()[-200:]}")
op.read_weight_data(dummy, objs, os.path.join(data_dir, "untitled-weight.txt"))
bpy.ops.object.select_all(action="DESELECT"); body.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type="ARMATURE")
print(f"[shd] bind OK body_vg={len(body.vertex_groups)}")
bpy.ops.wm.save_as_mainfile(filepath=os.path.splitext(out)[0] + ".blend")
print("[shd] saved", os.path.splitext(out)[0] + ".blend")
