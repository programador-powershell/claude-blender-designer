"""Rig DEFINITIVO via Surface Heat Diffuse Skinning (addon mesh-online).

Por que isto resolve onde Data Transfer/Surface Deform falharam:
  - SHD trata corpo+vestido como VOLUME e difunde calor dos bones -> weights
    corretos em mesh sobreposta (vestido sobre corpo). Nao racha a saia, nao
    precisa pose-match perfeito. E a tecnica padrao pra roupa.
  - Alice de vestido NAO vai pro Mixamo (vestido cobre pernas). SHD usa o
    skeleton Mixamo que JA temos no corpo, e estende pro vestido.

Pipeline:
  1. body limpo (alice_body_clean.fbx) — tem MixamoArmature + weights
  2. dress — apply_transform (mata scale 89x) + clean
  3. seleciona armature + body + dress
  4. wm.surface_heat_diffuse -> binda os 2 no armature (heat diffuse)
  5. aplica anim -> corpo+vestido movem juntos sem rachar
  6. export

Uso:
  blender -b -P rig_shd.py -- <out.glb> body=<body.fbx> outfit=<dress.fbx> [anim=<a.fbx>]
     [res=128] [loops=5] [samples=8] [influence=12] [falloff=2.0]
"""
import sys, os, statistics
import bpy, bmesh

argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
out_glb=body_file=outfit_file=anim_file=None
res,loops,samples,influence,falloff = 128,5,8,12,2.0
for a in argv:
    if a.startswith("body="): body_file=os.path.abspath(a[5:])
    elif a.startswith("outfit="): outfit_file=os.path.abspath(a[7:])
    elif a.startswith("anim="): anim_file=os.path.abspath(a[5:])
    elif a.startswith("res="): res=int(a[4:])
    elif a.startswith("loops="): loops=int(a[6:])
    elif a.startswith("samples="): samples=int(a[8:])
    elif a.startswith("influence="): influence=int(a[10:])
    elif a.startswith("falloff="): falloff=float(a[8:])
    else: out_glb=os.path.abspath(a)
assert out_glb and body_file and outfit_file

import addon_utils  # enable acontece APOS read_factory_settings (senao desregistra)


def clean(o, islands=True, merge=0.0008):
    me=o.data; bm=bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=merge); bm.verts.ensure_lookup_table()
    if islands:
        seen=set();comps=[]
        for v in bm.verts:
            if v.index in seen:continue
            st=[v];c=[]
            while st:
                x=st.pop()
                if x.index in seen:continue
                seen.add(x.index);c.append(x)
                for e in x.link_edges:
                    ov=e.other_vert(x)
                    if ov.index not in seen:st.append(ov)
            comps.append(c)
        comps.sort(key=len,reverse=True);big=len(comps[0]);keep=set()
        for i,c in enumerate(comps):
            if i==0 or len(c)>=big*0.02: keep.update(v.index for v in c)
        for v in [v for v in bm.verts if v.index not in keep]: bm.verts.remove(v)
    for v in [v for v in bm.verts if not v.link_faces]: bm.verts.remove(v)
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
    bm.to_mesh(me);bm.free();me.update()


def drop_junk(objs):
    for o in list(objs):
        if o.type in ("CAMERA","LIGHT"): bpy.data.objects.remove(o,do_unlink=True)
        elif o.type=="MESH" and len(o.data.polygons)<=320: bpy.data.objects.remove(o,do_unlink=True)


def apply_xform(o):
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True)
    bpy.context.view_layer.objects.active=o
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)


# 1. body
bpy.ops.wm.read_factory_settings(use_empty=True)
# enable addon DEPOIS do factory reset (reset desregistra addons)
addon_utils.enable("surface_heat_diffuse_skinning", default_set=True, persistent=True)
assert hasattr(bpy.context.scene, "surface_resolution"), "SHD addon nao registrou props"
bpy.ops.import_scene.fbx(filepath=body_file)
drop_junk(bpy.data.objects)
body=next(o for o in bpy.data.objects if o.type=="MESH")
arm=next(o for o in bpy.data.objects if o.type=="ARMATURE")
body.name="Corpo"; arm.name="MixamoArmature"
# remove weights antigos do corpo? NAO — SHD refaz tudo. Mas limpa vgroups pra
# garantir bind fresco dos dois meshes igual.
print(f"[shd] body verts={len(body.data.vertices)} bones={len(arm.data.bones)}")

# 2. dress
before=set(bpy.data.objects.keys())
bpy.ops.import_scene.fbx(filepath=outfit_file)
new=[bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in before]
drop_junk(new); new=[o for o in new if o.name in bpy.data.objects]
dress=next(o for o in new if o.type=="MESH")
da=next((o for o in new if o.type=="ARMATURE"),None)
if da: apply_xform(da)
apply_xform(dress); clean(dress)
if da: bpy.data.objects.remove(da,do_unlink=True)
for m in list(dress.modifiers):
    if m.type=="ARMATURE": dress.modifiers.remove(m)
dress.name="AliceDress"
print(f"[shd] dress verts={len(dress.data.vertices)}")

# limpa modifiers/vgroups antigos do corpo p/ SHD refazer ambos do zero
for m in list(body.modifiers):
    if m.type=="ARMATURE": body.modifiers.remove(m)
body.vertex_groups.clear()
dress.vertex_groups.clear()

# 3. params SHD
sc=bpy.context.scene
sc.surface_resolution=res
sc.surface_loops=loops
sc.surface_samples=samples
sc.surface_influence=influence
sc.surface_falloff=falloff
if hasattr(sc,"surface_protect"): sc.surface_protect=False
if hasattr(sc,"detect_surface_solidify"): sc.detect_surface_solidify=False
print(f"[shd] params res={res} loops={loops} samples={samples} infl={influence} falloff={falloff}")

# 4. SHD SYNCHRONOUS (sem modal — headless nao tem event loop).
#    Reusa os metodos da classe do addon: write mesh/bone -> roda shd.exe ->
#    espera (.wait) -> read_weight_data -> parent_set. Igual ao execute()+modal
#    mas bloqueante.
import surface_heat_diffuse_skinning as SHD
import platform, subprocess
addon_dir = os.path.dirname(SHD.__file__)
data_dir = os.path.join(addon_dir, "data")
os.makedirs(data_dir, exist_ok=True)

op = SHD.SFC_OT_ModalTimerOperator  # classe do operator (nao instanciavel direto)
import types as _types
# dummy self com os atributos que os metodos usam (sao autocontidos)
dummy = _types.SimpleNamespace(
    _objs=[], _permulation=[], _selected_indices=[], _selected_group_index_weights=[]
)

bpy.ops.object.select_all(action="DESELECT")
body.select_set(True); dress.select_set(True); arm.select_set(True)
bpy.context.view_layer.objects.active=arm

objs = sorted([body, dress], key=lambda o: o.name)
dummy._objs = objs
for obj in objs:
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="OBJECT")
# chama metodos unbound passando dummy como self
op.write_mesh_data(dummy, objs, os.path.join(data_dir, "untitled-mesh.txt"))
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="OBJECT")
op.write_bone_data(dummy, arm, os.path.join(data_dir, "untitled-bone.txt"))

exe = os.path.join(addon_dir, "bin", "Windows", "x64", "shd.exe")
print(f"[shd] rodando shd.exe (res={res})...")
proc = subprocess.run(
    [exe, "untitled-mesh.txt", "untitled-bone.txt", "untitled-weight.txt",
     str(res), str(loops), str(samples), str(influence), str(falloff),
     sc.surface_sharpness, "n"],
    cwd=data_dir, capture_output=True, text=True, timeout=1800,
)
print(f"[shd] exe exit={proc.returncode}; tail: {proc.stdout.strip()[-200:]}")

# le os weights de volta pros meshes
op.read_weight_data(dummy, objs, os.path.join(data_dir, "untitled-weight.txt"))

# bind: parent meshes ao armature
bpy.ops.object.select_all(action="DESELECT")
for o in objs: o.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type="ARMATURE")
print(f"[shd] bind OK: body_vg={len(body.vertex_groups)} dress_vg={len(dress.vertex_groups)}")

# 5. anim
applied=False
if anim_file and os.path.exists(anim_file):
    b2=set(bpy.data.objects.keys())
    bpy.ops.import_scene.fbx(filepath=anim_file)
    ao=[bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in b2]
    aarm=next((o for o in ao if o.type=="ARMATURE"),None)
    if aarm and aarm.animation_data and aarm.animation_data.action:
        act=aarm.animation_data.action
        if not arm.animation_data: arm.animation_data_create()
        arm.animation_data.action=act
        sc.frame_start=int(act.frame_range[0]); sc.frame_end=int(act.frame_range[1])
        applied=True
        print(f"[shd] anim '{act.name}' frames={act.frame_range}")
    for o in ao:
        if o is not aarm and o.name in bpy.data.objects:
            try: bpy.data.objects.remove(o,do_unlink=True)
            except: pass

# 6. export
os.makedirs(os.path.dirname(out_glb),exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.splitext(out_glb)[0]+".blend")
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True); dress.select_set(True); arm.select_set(True)
bpy.context.view_layer.objects.active=arm
bpy.ops.export_scene.gltf(filepath=out_glb,export_format="GLB",use_selection=True,export_apply=False,export_animations=applied)
print(f"[shd] GLB -> {out_glb} anim={applied}")
