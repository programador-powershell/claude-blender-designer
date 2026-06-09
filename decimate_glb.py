"""Decima GLB animado pra web (mantem skin+anim). Decimate COLLAPSE preserva
vertex groups (weights) e shape keys. Mantem armature+action.

Uso: blender -b -P decimate_glb.py -- <in.glb> <out.glb> [ratio=0.18]
"""
import sys, os
import bpy

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
src=os.path.abspath(argv[0]); out=os.path.abspath(argv[1])
ratio=float(argv[2]) if len(argv)>2 else 0.18

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)

arm=next((o for o in bpy.data.objects if o.type=="ARMATURE"),None)
applied=bool(bpy.data.actions)
if arm and bpy.data.actions and not arm.animation_data:
    arm.animation_data_create()
if arm and bpy.data.actions:
    arm.animation_data.action=bpy.data.actions[0]

# remove junk (Icosphere/Cube placeholder do exporter, <=320 polys)
for o in [x for x in bpy.data.objects if x.type=="MESH" and len(x.data.polygons)<=320]:
    print(f"[dec] junk removido: {o.name}")
    bpy.data.objects.remove(o,do_unlink=True)

for o in [x for x in bpy.data.objects if x.type=="MESH"]:
    bpy.context.view_layer.objects.active=o
    m=o.modifiers.new("Dec","DECIMATE")
    m.decimate_type="COLLAPSE"; m.ratio=ratio; m.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier="Dec")
    print(f"[dec] {o.name} -> {len(o.data.vertices)} verts")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(
    filepath=out, export_format="GLB", use_selection=True,
    export_apply=False, export_animations=applied,
    export_animation_mode="ACTIONS", export_nla_strips=True,
    export_force_sampling=True, export_yup=True,
    export_image_format="JPEG",   # textura JPEG = menor
)
mb=os.path.getsize(out)/1024/1024
print(f"[dec] OK -> {out} ({mb:.1f} MB)")
