"""Aplica KNOBS no rig Alice corpo+vestido usando SHD (Surface Heat Diffuse).

Espaco de acao FECHADO controlado pelo agente vision (maverick/NVIDIA).
SHD binda corpo+vestido no skeleton (nao racha mesh sobreposta). Os knobs
ajustam pose/escala/saia ANTES do bind + pos-processo.

KNOBS:
  arm_angle_x    float 0..90   abaixa bracos do corpo (eixo X) p/ dentro da manga
  arm_scale      float 0.7..1.1 encolhe bracos do corpo (caber na manga)
  skirt_to_hips  bool          saia (verts<55% alt) 100% peso Hips -> nao racha
  dress_offset_z float -.05..05 sobe/desce vestido
  shd_res        int 64..160   resolucao voxel do SHD (maior=melhor weight, +lento)

Uso:
  blender -b -P apply_knobs.py -- <knobs.json> <out.glb> body=<b.fbx> outfit=<d.fbx> [anim=<a.fbx>]
"""
import sys, os, json, statistics, math
import bpy, bmesh, addon_utils

argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
knobs_path=os.path.abspath(argv[0]); out_glb=os.path.abspath(argv[1])
body_file=outfit_file=anim_file=None
for a in argv[2:]:
    if a.startswith("body="): body_file=os.path.abspath(a[5:])
    elif a.startswith("outfit="): outfit_file=os.path.abspath(a[7:])
    elif a.startswith("anim="): anim_file=os.path.abspath(a[5:])

K={"arm_angle_x":35.0,"arm_scale":1.0,"skirt_to_hips":True,"dress_offset_z":0.0,
   "shd_res":96,"hide_body_under":True,"hide_dist":0.03}
if os.path.exists(knobs_path):
    # utf-8-sig tolera BOM (PowerShell Set-Content -Encoding UTF8 escreve BOM)
    with open(knobs_path, encoding="utf-8-sig") as _kf:
        K.update(json.load(_kf))
print(f"[knobs] {json.dumps(K)}")


def clean(o,islands=True,merge=0.0008):
    me=o.data;bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=merge);bm.verts.ensure_lookup_table()
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
    bpy.ops.object.select_all(action="DESELECT");o.select_set(True)
    bpy.context.view_layer.objects.active=o
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)


# body
bpy.ops.wm.read_factory_settings(use_empty=True)
addon_utils.enable("surface_heat_diffuse_skinning",default_set=True,persistent=True)
bpy.ops.import_scene.fbx(filepath=body_file)
drop_junk(bpy.data.objects)
body=next(o for o in bpy.data.objects if o.type=="MESH")
arm=next(o for o in bpy.data.objects if o.type=="ARMATURE")
body.name="Corpo";arm.name="MixamoArmature"

# dress
before=set(bpy.data.objects.keys())
bpy.ops.import_scene.fbx(filepath=outfit_file)
new=[bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in before]
drop_junk(new);new=[o for o in new if o.name in bpy.data.objects]
dress=next(o for o in new if o.type=="MESH")
da=next((o for o in new if o.type=="ARMATURE"),None)
if da: apply_xform(da)
apply_xform(dress);clean(dress)
if da: bpy.data.objects.remove(da,do_unlink=True)
for m in list(dress.modifiers):
    if m.type=="ARMATURE": dress.modifiers.remove(m)
dress.name="AliceDress"

# KNOB dress_offset_z
if K["dress_offset_z"]!=0.0:
    dress.location.z+=K["dress_offset_z"]; apply_xform(dress)

# KNOB pose bracos do corpo (angle_x + scale)
bpy.ops.object.select_all(action="DESELECT")
bpy.context.view_layer.objects.active=arm; bpy.ops.object.mode_set(mode="POSE")
for side in ("Left","Right"):
    ua=arm.pose.bones.get(f"mixamorig:{side}Arm")
    if ua:
        ua.rotation_mode="XYZ"; ua.rotation_euler=(math.radians(K["arm_angle_x"]),0,0)
        if K["arm_scale"]!=1.0: ua.scale=(K["arm_scale"],)*3
bpy.context.view_layer.update(); bpy.ops.pose.armature_apply(selected=False)
bpy.ops.object.mode_set(mode="OBJECT")

# KNOB hide_body_under — deleta verts do CORPO que estao cobertos pelo vestido
# (dentro de hide_dist da superficie do dress). Resolve "braco duplicado":
# o braco do corpo sob a manga e removido, sobra so a manga do vestido. O corpo
# visivel (rosto, decote, maos pra fora) fica intacto. Toggle-nua perde as
# partes cobertas, mas nua provavelmente nao vai pro jogo.
if K.get("hide_body_under"):
    import mathutils
    dist=K.get("hide_dist",0.03)
    # KDTree dos verts do dress (world)
    dverts=[dress.matrix_world@v.co for v in dress.data.vertices]
    kd=mathutils.kdtree.KDTree(len(dverts))
    for i,co in enumerate(dverts): kd.insert(co,i)
    kd.balance()
    bm=bmesh.new(); bm.from_mesh(body.data); bm.verts.ensure_lookup_table()
    rem=[]
    for v in bm.verts:
        co=body.matrix_world@v.co
        near=kd.find(co)
        if near[2] is not None and near[2]<dist:
            rem.append(v)
    for v in rem: bm.verts.remove(v)
    bm.to_mesh(body.data); bm.free(); body.data.update()
    print(f"[knobs] hide_body_under: removidos {len(rem)} verts do corpo cobertos (dist<{dist})")

# KNOB cut_body_arms — RESOLVE 4 bracos de vez. O braco do corpo (esticado,
# |x| ate ~0.62) e MAIS LONGO que a manga do vestido (|x| ate ~0.37). A ponta
# do braco do corpo fura pra fora da manga = parece 4 bracos. Aqui deletamos os
# verts do corpo cujo |x| passa de (dress_xmax + margem). A manga do vestido
# cobre o braco; o corpo so precisa existir ate onde a manga vai.
if K.get("cut_body_arms", True):
    dxs=[abs((dress.matrix_world@v.co).x) for v in dress.data.vertices]
    dress_xmax=max(dxs) if dxs else 0.4
    margin=K.get("cut_margin",0.02)
    cut_at=dress_xmax+margin
    bm=bmesh.new(); bm.from_mesh(body.data); bm.verts.ensure_lookup_table()
    cut=[v for v in bm.verts if abs((body.matrix_world@v.co).x)>cut_at]
    for v in cut: bm.verts.remove(v)
    bm.to_mesh(body.data); bm.free(); body.data.update()
    print(f"[knobs] cut_body_arms: cortados {len(cut)} verts do corpo alem de |x|>{cut_at:.2f} (manga vai ate {dress_xmax:.2f})")

# limpa weights antigos -> SHD refaz
for m in list(body.modifiers):
    if m.type=="ARMATURE": body.modifiers.remove(m)
body.vertex_groups.clear(); dress.vertex_groups.clear()

# SHD synchronous
import surface_heat_diffuse_skinning as SHD
import types as _t, subprocess
addon_dir=os.path.dirname(SHD.__file__); data_dir=os.path.join(addon_dir,"data"); os.makedirs(data_dir,exist_ok=True)
sc=bpy.context.scene
sc.surface_resolution=int(K["shd_res"]); sc.surface_loops=5; sc.surface_samples=8
sc.surface_influence=12; sc.surface_falloff=2.0
if hasattr(sc,"surface_protect"): sc.surface_protect=False
if hasattr(sc,"detect_surface_solidify"): sc.detect_surface_solidify=False
op=SHD.SFC_OT_ModalTimerOperator
dummy=_t.SimpleNamespace(_objs=[],_permulation=[],_selected_indices=[],_selected_group_index_weights=[])
objs=sorted([body,dress],key=lambda o:o.name); dummy._objs=objs
for o in objs:
    bpy.context.view_layer.objects.active=o; bpy.ops.object.mode_set(mode="OBJECT")
op.write_mesh_data(dummy,objs,os.path.join(data_dir,"untitled-mesh.txt"))
bpy.context.view_layer.objects.active=arm; bpy.ops.object.mode_set(mode="OBJECT")
op.write_bone_data(dummy,arm,os.path.join(data_dir,"untitled-bone.txt"))
exe=os.path.join(addon_dir,"bin","Windows","x64","shd.exe")
subprocess.run([exe,"untitled-mesh.txt","untitled-bone.txt","untitled-weight.txt",
    str(int(K["shd_res"])),"5","8","12","2.0",sc.surface_sharpness,"n"],
    cwd=data_dir,capture_output=True,text=True,timeout=1800)
op.read_weight_data(dummy,objs,os.path.join(data_dir,"untitled-weight.txt"))
bpy.ops.object.select_all(action="DESELECT")
for o in objs: o.select_set(True)
arm.select_set(True); bpy.context.view_layer.objects.active=arm
bpy.ops.object.parent_set(type="ARMATURE")
print(f"[knobs] SHD bind: body_vg={len(body.vertex_groups)} dress_vg={len(dress.vertex_groups)}")

# KNOB skirt_to_hips — saia 100% Hips, nao racha
if K["skirt_to_hips"]:
    me=dress.data; zs=[v.co.z for v in me.vertices]; mn,mx=min(zs),max(zs); h=mx-mn
    skirt_top=mn+0.55*h
    hips=dress.vertex_groups.get("mixamorig:Hips") or dress.vertex_groups.new(name="mixamorig:Hips")
    legs=[vg for vg in dress.vertex_groups if any(k in vg.name for k in ("Leg","UpLeg","Foot","Toe"))]
    sk=[v.index for v in me.vertices if v.co.z<skirt_top]
    for vi in sk:
        for vg in legs:
            try: vg.remove([vi])
            except: pass
        hips.add([vi],1.0,"REPLACE")
    print(f"[knobs] skirt_to_hips: {len(sk)} verts saia -> Hips")

# anim — atribui action ao armature do corpo + PUSH pra NLA (glTF exporter so
# exporta anim que esta em NLA track OU active action com fake_user).
applied=False
act_name=None
if anim_file and os.path.exists(anim_file):
    b2=set(bpy.data.objects.keys())
    bpy.ops.import_scene.fbx(filepath=anim_file)
    ao=[bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in b2]
    aarm=next((o for o in ao if o.type=="ARMATURE"),None)
    if aarm and aarm.animation_data and aarm.animation_data.action:
        act=aarm.animation_data.action
        # Blender 5.1: act.fcurves removido (Action Slots). Diagnostico opcional.
        try:
            fcs = act.fcurves  # legacy
            tot = len(fcs)
        except AttributeError:
            tot = "?(slots)"
        print(f"[knobs] anim '{act.name}' frames={act.frame_range} fcurves={tot}")
        if not arm.animation_data: arm.animation_data_create()
        arm.animation_data.action=act
        act.use_fake_user=True
        # PUSH pra NLA track (garante export)
        try:
            track=arm.animation_data.nla_tracks.new()
            track.name="ExportTrack"
            track.strips.new(act.name, int(act.frame_range[0]), act)
            # tira da active pra nao duplicar (NLA ja segura)
            print(f"[knobs] action pushed pra NLA track")
        except Exception as e:
            print(f"[knobs] NLA push WARN {e}")
        bpy.context.scene.frame_start=int(act.frame_range[0])
        bpy.context.scene.frame_end=int(act.frame_range[1])
        act_name=act.name
        applied=True
    for o in ao:
        if o is not aarm and o.name in bpy.data.objects:
            try: bpy.data.objects.remove(o,do_unlink=True)
            except: pass
    if aarm and aarm.name in bpy.data.objects:
        bpy.data.objects.remove(aarm,do_unlink=True)

os.makedirs(os.path.dirname(out_glb),exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.splitext(out_glb)[0]+".blend")
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True);dress.select_set(True);arm.select_set(True)
bpy.context.view_layer.objects.active=arm
bpy.ops.export_scene.gltf(
    filepath=out_glb,export_format="GLB",use_selection=True,export_apply=False,
    export_animations=applied,
    export_animation_mode="ACTIONS" if applied else "ACTIVE_ACTIONS",
    export_nla_strips=True,
    export_force_sampling=True,
    export_yup=True,
)
# valida anim no glb
import struct
print(f"[knobs] OK -> {out_glb} (anim={applied} act={act_name})")
