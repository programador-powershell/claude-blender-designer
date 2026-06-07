# -*- coding: utf-8 -*-
"""game_builder — solucao DEFINITIVA de construcao de elementos de jogo no Blender,
operada AO VIVO (via bridge) e visivel no viewport do usuario.

SUBSISTEMAS:
  A) PERSONAGEM (skin): SHD (Surface Heat Diffuse) PRIMARIO — pesa TUDO em volume
     fechado (vestido). FALLBACK nativo Bone Heat (apply_native_auto_skinning) p/
     props simples — FALHA em vestido (colapsa em Hips). shd_available() checa; modulo
     NAO crasha se SHD faltar.
  B) OBJETOS DE JOGO (fisica semantica): suporte (mesa=passivo cinematico) vs
     destrutivel (copo/xicara=fratura Voronoi PROPRIA via bmesh, sem addon; estilhacos
     dormem ate impacto).
  C) VISAO GEOMETRICA: get_live_mesh_geometry / apply_live_vertex_deformations — IA le
     e edita vertices por coords X,Y,Z, sem screenshot (tb em live_geo.py).

Tudo roda no GUI vivo via bridge. SHD: launch nao-bloqueante + poll + finalize.
"""
import bpy, os, sys, types, subprocess, platform, json, time

# ---------------------------------------------------------------------------
# A) PERSONAGEM — skin. SHD (primario, robusto p/ volume fechado/vestido) +
#    fallback NATIVO Bone Heat (so p/ props/mesh simples — FALHA em vestido).
# ---------------------------------------------------------------------------

def shd_available():
    """SHD addon+exe presente? (modulo nao crasha se faltar; degrada gracioso.)"""
    try:
        import surface_heat_diffuse_skinning as S
        exe = os.path.join(os.path.dirname(S.__file__), "bin","Windows","x64","shd.exe")
        return os.path.exists(exe)
    except Exception:
        return False

def apply_native_auto_skinning(mesh_name, arm_name):
    """Bone Heat NATIVO (parent_set ARMATURE_AUTO). 100% sem dependencia externa.
    USAR SO em props/mesh simples e fechado-manifold. FALHA em vestido (volume
    fechado/auto-interseccao) -> pesos colapsam em Hips. Pra vestido use SHD."""
    mesh = bpy.data.objects.get(mesh_name); arm = bpy.data.objects.get(arm_name)
    if not mesh or not arm:
        return json.dumps({"err": f"'{mesh_name}' ou '{arm_name}' nao existe."})
    arm.hide_set(False); mesh.hide_set(False)
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for m in list(mesh.modifiers):
        if m.type == 'ARMATURE': mesh.modifiers.remove(m)
    mesh.parent = None
    bpy.ops.object.select_all(action='DESELECT')
    mesh.select_set(True); arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    try:
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    except Exception as e:
        return json.dumps({"status":"error","err":f"Bone Heat nativo falhou (geometria furada/auto-interseccao). {e}"})
    # auto-verifica: quantos verts ficaram SEM peso de osso (sintoma do colapso)
    me=mesh.data
    bidx={g.index for g in mesh.vertex_groups}
    only_hips=0; unw=0
    hips=mesh.vertex_groups.get("mixamorig:Hips")
    for v in me.vertices:
        ws=[(g.group,g.weight) for g in v.groups if g.weight>1e-4 and g.group in bidx]
        if not ws: unw+=1
        elif hips and len(ws)==1 and ws[0][0]==hips.index: only_hips+=1
    warn=None
    if (unw+only_hips) > 0.5*len(me.vertices):
        warn="COLAPSOU (maioria sem peso ou so Hips) -> use SHD nesse mesh."
    return json.dumps({"status":"success","vgroups":len(mesh.vertex_groups),
        "unweighted":unw,"only_hips":only_hips,"warn":warn})

def skin_auto(mesh_name, arm_name):
    """Dispatcher: SHD se disponivel (melhor p/ vestido), senao nativo (com aviso)."""
    if shd_available():
        return json.dumps({"method":"shd","note":"use shd_launch + shd_finalize"})
    r=json.loads(apply_native_auto_skinning(mesh_name, arm_name))
    r["method"]="native(fallback — SHD ausente)"
    return json.dumps(r)

def _shd_paths():
    import surface_heat_diffuse_skinning as S
    addon = os.path.dirname(S.__file__)
    data = os.path.join(addon, "data")
    exe = os.path.join(addon, "bin", "Windows", "x64", "shd.exe")
    return S, addon, data, exe

def enable_shd():
    import addon_utils
    addon_utils.enable("surface_heat_diffuse_skinning", default_set=True, persistent=True)
    return "surface_heat_diffuse_skinning" in [m.__name__ for m in addon_utils.modules() if addon_utils.check(m.__name__)[1]]

def shd_launch(mesh_name, arm_name, resolution=110, loops=5, samples=64,
               influence=4, falloff=0.2, sharpness="3", solidify="n"):
    """Escreve mesh+bone, lanca shd.exe NAO-bloqueante. Retorna na hora."""
    if not shd_available():
        return json.dumps({"err":"SHD ausente. Instale Surface Heat Diffuse, ou use "
            "apply_native_auto_skinning (so funciona em props simples, NAO em vestido)."})
    ok = enable_shd()
    S, addon, data, exe = _shd_paths()
    mesh = bpy.data.objects.get(mesh_name); arm = bpy.data.objects.get(arm_name)
    arm.hide_set(False); mesh.hide_set(False)
    op = S.SFC_OT_ModalTimerOperator
    dummy = types.SimpleNamespace(_objs=[], _permulation=[], _selected_indices=[],
                                  _selected_group_index_weights=[])
    # limpa parent/modifier antigo do mesh (auto-weight falho)
    for m in list(mesh.modifiers):
        if m.type == 'ARMATURE': mesh.modifiers.remove(m)
    mesh.parent = None
    # garante OBJECT mode
    bpy.context.view_layer.objects.active = mesh
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    # write mesh data (world coords)
    op.write_mesh_data(dummy, [mesh], os.path.join(data, "untitled-mesh.txt"))
    # write bone data (precisa armature active + edit mode dentro do metodo)
    bpy.context.view_layer.objects.active = arm
    op.write_bone_data(dummy, arm, os.path.join(data, "untitled-bone.txt"))
    bpy.context.view_layer.objects.active = mesh
    # apaga weight antigo
    wpath = os.path.join(data, "untitled-weight.txt")
    if os.path.exists(wpath):
        try: os.remove(wpath)
        except Exception: pass
    # lanca exe NAO-bloqueante
    p = subprocess.Popen([exe, "untitled-mesh.txt", "untitled-bone.txt", "untitled-weight.txt",
        str(resolution), str(loops), str(samples), str(influence), str(falloff), sharpness, solidify],
        cwd=data, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return json.dumps({"launched": True, "addon_ok": ok, "pid": p.pid,
        "mesh_verts": len(mesh.data.vertices), "weight_out": wpath})

def shd_status():
    """Checa se shd.exe ainda roda + se weight.txt pronto."""
    S, addon, data, exe = _shd_paths()
    wpath = os.path.join(data, "untitled-weight.txt")
    # processo rodando?
    running = False
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq shd.exe", "/NH"],
                             capture_output=True, text=True, timeout=10).stdout
        running = "shd.exe" in out
    except Exception as e:
        running = None
    sz = os.path.getsize(wpath) if os.path.exists(wpath) else 0
    return json.dumps({"running": running, "weight_exists": os.path.exists(wpath), "weight_size": sz})

def shd_finalize(mesh_name, arm_name):
    """Le weight.txt -> cria vgroups + pesos -> parent armature. So apos exe terminar."""
    S, addon, data, exe = _shd_paths()
    enable_shd()  # garante scene.surface_protect existe
    mesh = bpy.data.objects.get(mesh_name); arm = bpy.data.objects.get(arm_name)
    op = S.SFC_OT_ModalTimerOperator
    dummy = types.SimpleNamespace(_objs=[mesh], _permulation=[], _selected_indices=[],
                                  _selected_group_index_weights=[])
    wpath = os.path.join(data, "untitled-weight.txt")
    if not os.path.exists(wpath) or os.path.getsize(wpath) < 100:
        return json.dumps({"err": "weight.txt vazio/ausente — exe nao terminou?"})
    op.read_weight_data(dummy, [mesh], wpath)
    # parent armature
    bpy.context.view_layer.objects.active = mesh
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    mesh.select_set(True); arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type='ARMATURE')
    bone_vgs = [g.name for g in mesh.vertex_groups if g.name.startswith("mixamorig")]
    return json.dumps({"finalized": True, "bone_vgroups": len(bone_vgs)})

BODY_FBX = r"D:\Alice\tools\body-rebuild\out\alice_body_clean.fbx"

def _pose_arms_rest(arm, arm_deg):
    """Pose LeftArm/RightArm pra baixo arm_deg (Y global, pivot cabeca) e aplica REST."""
    import math
    from mathutils import Matrix
    bpy.context.view_layer.objects.active = arm
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    mw = arm.matrix_world
    def rotY(n, deg):
        bpy.context.view_layer.update()
        pb = arm.pose.bones[n]; Mw = mw @ pb.matrix; head = Mw.translation.copy()
        R = Matrix.Rotation(math.radians(deg), 4, 'Y')
        pb.matrix = mw.inverted() @ (Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ Mw)
    for n in ("mixamorig:LeftArm","mixamorig:RightArm","mixamorig:LeftForeArm","mixamorig:RightForeArm"):
        arm.pose.bones[n].matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    rotY("mixamorig:LeftArm",  +arm_deg); rotY("mixamorig:RightArm", -arm_deg)
    bpy.context.view_layer.update()
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode='OBJECT')

def prep_outfit(fbx_path, name, arm_deg=70, scene_name="RigLab"):
    """Cena limpa -> importa outfit (maior mesh=name) + apply_transform -> importa
    esqueleto Mixamo (Rig_<name>) -> pose bracos-baixo + rest. Pronto p/ SHD."""
    sc = _use_scene(scene_name)
    for o in list(sc.collection.objects): bpy.data.objects.remove(o, do_unlink=True)
    arm_name = f"Rig_{name}"
    # importa outfit
    before=set(bpy.data.objects); bpy.ops.import_scene.fbx(filepath=fbx_path)
    new=[o for o in bpy.data.objects if o not in before]
    meshes=[o for o in new if o.type=='MESH']
    if not meshes: return json.dumps({"err":"sem mesh no fbx"})
    mesh=max(meshes, key=lambda o:len(o.data.vertices)); mesh.name=name
    # destaca do armature-pai MANTENDO transform (senao apply baka errado)
    bpy.ops.object.select_all(action='DESELECT'); mesh.select_set(True)
    bpy.context.view_layer.objects.active=mesh
    if mesh.parent:
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    for o in new:
        if o is not mesh: bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT'); mesh.select_set(True)
    bpy.context.view_layer.objects.active=mesh
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    # NORMALIZA: escala p/ altura 1.70 + pes z=0 + centrado x/y (casa com esqueleto 1.7)
    TARGET_H=1.70
    co=[mesh.matrix_world @ v.co for v in mesh.data.vertices]
    zs=[c.z for c in co]; xs=[c.x for c in co]; ys=[c.y for c in co]
    h=max(zs)-min(zs)
    if h>1e-6:
        s=TARGET_H/h
        mesh.scale=(s,s,s); bpy.ops.object.transform_apply(scale=True)
    co=[mesh.matrix_world @ v.co for v in mesh.data.vertices]
    zs=[c.z for c in co]; xs=[c.x for c in co]; ys=[c.y for c in co]
    cx=(min(xs)+max(xs))/2; cy=(min(ys)+max(ys))/2; mnz=min(zs)
    mesh.location=(mesh.location.x-cx, mesh.location.y-cy, mesh.location.z-mnz)
    bpy.ops.object.transform_apply(location=True)
    # importa esqueleto do body_clean, mantem so armature
    before=set(bpy.data.objects); bpy.ops.import_scene.fbx(filepath=BODY_FBX)
    newb=[o for o in bpy.data.objects if o not in before]
    arm=next((o for o in newb if o.type=='ARMATURE'), None)
    for o in newb:
        if o is not arm: bpy.data.objects.remove(o, do_unlink=True)
    arm.name=arm_name
    bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True)
    bpy.context.view_layer.objects.active=arm
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    # POSE bracos-baixo + rest PRIMEIRO (armature_apply reseta transform do objeto,
    # entao alinhar DEPOIS — senao o apply destroi o alinhamento).
    _pose_arms_rest(arm, arm_deg)
    # ALINHA esqueleto ao mesh (scale+translate) DEPOIS do pose — bones DENTRO do volume,
    # senao SHD degenera (tudo vira Hips). Critico p/ variantes tematicas.
    from mathutils import Matrix, Vector
    def _mbb():
        c=[mesh.matrix_world @ v.co for v in mesh.data.vertices]
        xs=[p.x for p in c]; ys=[p.y for p in c]; zs=[p.z for p in c]
        return (min(xs)+max(xs))/2,(min(ys)+max(ys))/2,min(zs),max(zs)-min(zs)
    def _sbb():
        pts=[]
        for b in arm.data.bones:
            pts.append(arm.matrix_world @ b.head_local); pts.append(arm.matrix_world @ b.tail_local)
        xs=[p.x for p in pts]; ys=[p.y for p in pts]; zs=[p.z for p in pts]
        return (min(xs)+max(xs))/2,(min(ys)+max(ys))/2,min(zs),max(zs)-min(zs)
    m_cx,m_cy,m_minz,m_h=_mbb(); s_cx,s_cy,s_minz,s_h=_sbb()
    f = m_h/s_h if s_h>1e-6 else 1.0
    arm.scale=(arm.scale.x*f, arm.scale.y*f, arm.scale.z*f)
    bpy.context.view_layer.update()
    s_cx,s_cy,s_minz,s_h=_sbb()
    delta=Vector((m_cx-s_cx, m_cy-s_cy, m_minz-s_minz))
    arm.matrix_world = Matrix.Translation(delta) @ arm.matrix_world
    bpy.context.view_layer.update()
    hb=arm.matrix_world @ arm.data.bones["mixamorig:Hips"].head_local
    aligned = abs(hb.y - m_cy) < 0.05
    # stats
    M=mesh.matrix_world
    zs=[(M@v.co).z for v in mesh.data.vertices]; xs=[(M@v.co).x for v in mesh.data.vertices]
    wl=arm.matrix_world @ arm.data.bones["mixamorig:LeftForeArm"].tail_local
    hb=arm.matrix_world @ arm.data.bones["mixamorig:Hips"].head_local
    return json.dumps({"mesh":name,"verts":len(mesh.data.vertices),
        "height":round(max(zs)-min(zs),3),"x":[round(min(xs),3),round(max(xs),3)],
        "arm":arm_name,"wrist_x":round(wl.x,3),"wrist_z":round(wl.z,3),"arm_deg":arm_deg,
        "hips_y":round(hb.y,3),"mesh_cy":round((min([(mesh.matrix_world@v.co).y for v in mesh.data.vertices])+max([(mesh.matrix_world@v.co).y for v in mesh.data.vertices]))/2,3),
        "aligned":bool(aligned)})

def export_rigged(name, out_path):
    """Exporta GLB rigado (SO mesh+seu Rig_<name>). BULLETPROOF: cena temp isolada
    + use_active_scene -> impossivel vazar outros objetos (bug do use_selection)."""
    import os
    mesh=bpy.data.objects.get(name); arm=bpy.data.objects.get(f"Rig_{name}")
    if not mesh: return json.dumps({"err":f"mesh '{name}' nao existe"})
    if bpy.context.object and bpy.context.object.mode!='OBJECT':
        try: bpy.ops.object.mode_set(mode='OBJECT')
        except Exception: pass
    prev=bpy.context.window.scene
    tmp=bpy.data.scenes.new("__export_tmp")
    tmp.collection.objects.link(mesh)
    if arm: tmp.collection.objects.link(arm)
    bpy.context.window.scene=tmp
    bpy.ops.export_scene.gltf(filepath=out_path, use_active_scene=True, export_format='GLB',
        export_skins=True, export_yup=True, export_apply=False)
    bpy.context.window.scene=prev
    bpy.data.scenes.remove(tmp)
    return json.dumps({"glb":out_path,"size_MB":round(os.path.getsize(out_path)/1e6,2)})

def clean_reexport(glb_in, name, glb_out):
    """Carrega GLB sujo (isola personagem) + reexporta limpo. Conserta os 5 vazados."""
    r=json.loads(load_glb(glb_in, name))
    if "err" in r: return json.dumps(r)
    return export_rigged(name, glb_out)

# ---------------------------------------------------------------------------
# B) OBJETOS DE JOGO — fisica semantica + destruicao (Cell Fracture)
# ---------------------------------------------------------------------------

def _voronoi_fracture(obj, n=12, seed=42):
    """Fratura Voronoi SELF-CONTAINED (sem addon). Sementes no bbox; cada celula =
    intersecao dos half-spaces (bisect entre sementes). Devolve lista de shards."""
    import bmesh, random, mathutils
    random.seed(seed)
    M = obj.matrix_world
    src = bmesh.new(); src.from_mesh(obj.data)
    bmesh.ops.transform(src, matrix=M, verts=src.verts)   # -> world
    xs=[v.co.x for v in src.verts]; ys=[v.co.y for v in src.verts]; zs=[v.co.z for v in src.verts]
    mn=(min(xs),min(ys),min(zs)); mx=(max(xs),max(ys),max(zs))
    V=mathutils.Vector
    seeds=[V((random.uniform(mn[0],mx[0]),random.uniform(mn[1],mx[1]),random.uniform(mn[2],mx[2]))) for _ in range(n)]
    shards=[]
    for i,si in enumerate(seeds):
        bm=src.copy()
        for j,sj in enumerate(seeds):
            if i==j: continue
            no=(sj-si)
            if no.length<1e-6: continue
            no.normalize(); co=(si+sj)*0.5
            geom=bm.verts[:]+bm.edges[:]+bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, dist=0, plane_co=co, plane_no=no,
                                   clear_outer=True, clear_inner=False)
        if len(bm.verts)<4: bm.free(); continue
        try: bmesh.ops.holes_fill(bm, edges=bm.edges[:])
        except Exception: pass
        me=bpy.data.meshes.new(f"{obj.name}_shard{i}")
        bm.to_mesh(me); bm.free()
        so=bpy.data.objects.new(f"{obj.name}_shard{i}", me)
        bpy.context.scene.collection.objects.link(so)
        shards.append(so)
    src.free()
    # origem de cada shard no centro da geometria (rigidbody gira natural)
    if shards:
        bpy.ops.object.select_all(action='DESELECT')
        for s in shards: s.select_set(True)
        bpy.context.view_layer.objects.active=shards[0]
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
    return shards

def _use_scene(name):
    sc = bpy.data.scenes.get(name) or bpy.data.scenes.new(name)
    bpy.context.window.scene = sc
    return sc

def build_test_teascene(scene_name="PhysicsLab"):
    """Cena isolada: Mesa (suporte) + Copo + Xicara (destrutiveis) + Chao. (imita output IA img->3D)"""
    sc = _use_scene(scene_name)
    # limpa a cena lab
    for o in list(sc.collection.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    def add_cube(name, loc, scale):
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o=bpy.context.active_object
        o.name=name; o.scale=scale; bpy.ops.object.transform_apply(scale=True); return o
    def add_cyl(name, r, d, loc):
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d, location=loc); o=bpy.context.active_object
        o.name=name; return o
    mesa = add_cube("AI_Mesa_Suporte",(0,0,0.9),(2.0,1.2,0.05))
    copo = add_cyl("AI_Copo_Destrutivel",0.12,0.4,(-0.4,0,1.15))
    xic  = add_cyl("AI_Xicara_Destrutivel",0.15,0.25,(0.4,0,1.05))
    bpy.ops.mesh.primitive_plane_add(size=10, location=(0,0,0)); chao=bpy.context.active_object
    chao.name="Chao_Fisico"
    return json.dumps({"scene":scene_name,"objs":[o.name for o in sc.collection.objects]})

def classify_scene(scene_name="PhysicsLab"):
    """Visao semantica: separa suporte (mesa) / destrutivel (copo,xicara) / chao."""
    sc = bpy.data.scenes.get(scene_name)
    m = {"suporte_cinematico":[], "destrutivel":[], "chao":[], "outro":[]}
    for o in sc.collection.objects:
        n=o.name.lower()
        if "mesa" in n or "suporte" in n: m["suporte_cinematico"].append(o.name)
        elif any(k in n for k in ("copo","xicara","destrutivel")): m["destrutivel"].append(o.name)
        elif "chao" in n: m["chao"].append(o.name)
        else: m["outro"].append(o.name)
    return json.dumps(m)

def _ensure_rbworld():
    if not bpy.context.scene.rigidbody_world:
        bpy.ops.rigidbody.world_add()
    w=bpy.context.scene.rigidbody_world
    try: w.substeps_per_frame=10
    except Exception: pass
    try: w.solver_iterations=20
    except Exception: pass
    # collection pra rigid bodies
    if not w.collection:
        col=bpy.data.collections.new("RigidBodyWorld"); w.collection=col
    return w

def _rb(obj, rbtype):
    bpy.context.view_layer.objects.active=obj
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True)
    if not obj.rigid_body: bpy.ops.rigidbody.object_add()
    obj.rigid_body.type=rbtype
    return obj.rigid_body

def setup_physics(scene_name="PhysicsLab", shards=15):
    """Mesa=PASSIVE kinematic (bater move so o que esta em cima). Chao=PASSIVE.
    Copo/Xicara=Cell Fracture -> estilhacos ACTIVE start_deactivated (dormem ate impacto)."""
    sc=_use_scene(scene_name)
    _ensure_rbworld()
    cls=json.loads(classify_scene(scene_name))
    result={"table":None,"ground":None,"fractured":{}}
    # chao
    for n in cls["chao"]:
        rb=_rb(bpy.data.objects[n],'PASSIVE'); rb.collision_shape='MESH'; result["ground"]=n
    # mesa: passivo cinematico
    for n in cls["suporte_cinematico"]:
        o=bpy.data.objects[n]; rb=_rb(o,'PASSIVE')
        rb.kinematic=True; rb.collision_shape='BOX'; rb.friction=0.6; rb.restitution=0.1
        result["table"]=n
    # destrutiveis: fratura Voronoi propria + estilhacos dormindo
    for n in cls["destrutivel"]:
        o=bpy.data.objects.get(n)
        if not o: continue
        try:
            made=_voronoi_fracture(o, n=shards)
        except Exception as e:
            result["fractured"][n]=f"ERR:{e}"; continue
        for s in made:
            rb=_rb(s,'ACTIVE'); rb.mass=0.05; rb.collision_shape='CONVEX_HULL'; rb.friction=0.5
            rb.use_deactivation=True; rb.use_start_deactivated=True
        o.hide_viewport=True; o.hide_render=True
        result["fractured"][n]=len(made)
    return json.dumps(result)

def bake_physics(scene_name="PhysicsLab", frames=40):
    """Roda a sim alguns frames (sem perturbar) -> prova que estilhacos NAO explodem sozinhos."""
    sc=_use_scene(scene_name)
    sc.frame_start=1; sc.frame_end=frames
    w=bpy.context.scene.rigidbody_world
    if w.point_cache: w.point_cache.frame_start=1; w.point_cache.frame_end=frames
    for f in range(1, frames+1):
        sc.frame_set(f)
    return json.dumps({"baked_to":frames,"frame":sc.frame_current})

# ---------------------------------------------------------------------------
# D) DIRETOR — controle PRECISO/determinístico do rig (pose por OSSO).
#    Movimento de membro = osso (limpo), NAO vertice (estica). Eu calculo a
#    rotacao EXATA pro alvo — sem tentativa-e-erro.
# ---------------------------------------------------------------------------

def _arm_to_pose(arm):
    # garante que o objeto esta no view layer (senao active falha)
    if arm.name not in bpy.context.view_layer.objects:
        try: bpy.context.scene.collection.objects.link(arm)
        except Exception: pass
    bpy.context.view_layer.objects.active = arm
    if bpy.context.object and bpy.context.object.mode != 'POSE':
        if bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        arm.select_set(True); bpy.ops.object.mode_set(mode='POSE')

def reset_pose(arm_name):
    from mathutils import Matrix
    arm=bpy.data.objects.get(arm_name)
    _arm_to_pose(arm)
    for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    return json.dumps({"reset":arm_name})

def aim_bone(arm_name, bone, target_dir):
    """Mira a DIRECAO do osso (head->tail) p/ target_dir (world). Determinístico:
    calcula rotation_difference exata. Filhos seguem (FK). target_dir=[x,y,z]."""
    from mathutils import Matrix, Vector
    arm=bpy.data.objects.get(arm_name)
    if not arm or bone not in arm.pose.bones:
        return json.dumps({"err":f"osso '{bone}' nao existe em '{arm_name}'"})
    _arm_to_pose(arm)
    bpy.context.view_layer.update()
    mw=arm.matrix_world; pb=arm.pose.bones[bone]
    head_w=mw @ pb.head; tail_w=mw @ pb.tail
    cur=(tail_w-head_w).normalized(); tgt=Vector(target_dir).normalized()
    Rq=cur.rotation_difference(tgt); R=Rq.to_matrix().to_4x4()
    Mw=mw @ pb.matrix
    pb.matrix = mw.inverted() @ (Matrix.Translation(head_w) @ R @ Matrix.Translation(-head_w) @ Mw)
    bpy.context.view_layer.update()
    nt=mw @ arm.pose.bones[bone].tail
    nh=mw @ arm.pose.bones[bone].head
    newdir=(nt-nh).normalized()
    return json.dumps({"bone":bone,"target":[round(x,3) for x in tgt],
        "achieved":[round(newdir.x,3),round(newdir.y,3),round(newdir.z,3)]})

def pose_bone(arm_name, bone, axis, deg):
    """Rotaciona osso 'deg' em torno do eixo GLOBAL (X/Y/Z) na propria cabeca."""
    import math
    from mathutils import Matrix
    arm=bpy.data.objects.get(arm_name)
    if not arm or bone not in arm.pose.bones:
        return json.dumps({"err":f"osso '{bone}' nao existe"})
    _arm_to_pose(arm); bpy.context.view_layer.update()
    mw=arm.matrix_world; pb=arm.pose.bones[bone]; Mw=mw @ pb.matrix; head=Mw.translation.copy()
    R=Matrix.Rotation(math.radians(deg),4,axis)
    pb.matrix=mw.inverted() @ (Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ Mw)
    bpy.context.view_layer.update()
    return json.dumps({"bone":bone,"axis":axis,"deg":deg})

def raise_arm(arm_name, side="Left", height=1.0, out=0.4, fwd=-0.1):
    """Levanta o braco LIMPO via osso. height: 1=reto pra cima, 0=horizontal.
    Mira Arm e ForeArm na direcao up+out. side='Left'/'Right'."""
    sgn = 1.0 if side=="Left" else -1.0
    tgt=[sgn*out, fwd, height]
    r1=json.loads(aim_bone(arm_name, f"mixamorig:{side}Arm", tgt))
    r2=json.loads(aim_bone(arm_name, f"mixamorig:{side}ForeArm", [sgn*out*0.7, fwd, height]))
    return json.dumps({"raise":side,"upperarm":r1,"forearm":r2})

# ---------------------------------------------------------------------------
# FUNDACAO ROBUSTA — gestao de mundo/cena (sem pileup, sempre estado conhecido)
# ---------------------------------------------------------------------------

def reset_world():
    """Limpa TODOS objetos + purga orfaos (mesh/armature/material/action/image).
    Estado limpo determinístico — acaba o pileup .001/.002/.003."""
    try:
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
    except Exception: pass
    for o in list(bpy.data.objects):
        try: bpy.data.objects.remove(o, do_unlink=True)
        except Exception: pass
    purged=0
    for coll in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials,
                 bpy.data.actions, bpy.data.images, bpy.data.curves):
        for d in list(coll):
            if d.users == 0:
                try: coll.remove(d); purged+=1
                except Exception: pass
    return json.dumps({"reset":True,"purged":purged})

def load_glb(path, name):
    """reset_world + importa GLB + renomeia canonico (mesh=name, arm=Rig_<name>).
    Retorna nomes exatos. Pos: estado conhecido, sem ambiguidade de nome."""
    import os
    if not os.path.exists(path):
        return json.dumps({"err":f"nao existe: {path}"})
    reset_world()
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new=[o for o in bpy.data.objects if o not in before]
    meshes=[o for o in new if o.type=='MESH']
    if not meshes: return json.dumps({"err":"GLB sem mesh"})
    mesh=max(meshes, key=lambda o:len(o.data.vertices))   # personagem = maior mesh
    # armature que DEFORMA o personagem (modifier), senao qualquer armature
    arm=None
    for m in mesh.modifiers:
        if m.type=='ARMATURE' and m.object: arm=m.object; break
    if not arm: arm=next((o for o in new if o.type=='ARMATURE'), None)
    # ISOLA: deleta todo o resto (lixo de GLB sujo: shards/mesa/icosphere)
    removed=0
    for o in list(new):
        if o is not mesh and o is not arm:
            try: bpy.data.objects.remove(o, do_unlink=True); removed+=1
            except Exception: pass
    mesh.name=name; arm_name=None
    if arm: arm.name=f"Rig_{name}"; arm_name=arm.name
    return json.dumps({"mesh":name,"armature":arm_name,"verts":len(mesh.data.vertices),
        "isolated_removed":removed})

def load_fbx_outfit(fbx_path, name):
    """reset_world + prep_outfit completo (normaliza+aliña+pose). P/ rigar do zero."""
    reset_world()
    return prep_outfit(fbx_path, name)

def frame(target=None, axis="FRONT", hide_rig=True):
    """Enquadra + esconde rig (p/ ver so a malha). Reutiliza live_geo se houver."""
    if hide_rig:
        for o in bpy.context.view_layer.objects:   # so os do view layer atual
            if o.type=='ARMATURE':
                try: o.hide_set(True)
                except Exception: pass
    for area in bpy.context.screen.areas:
        if area.type=='VIEW_3D':
            area.spaces[0].shading.type='SOLID'
            region=next((r for r in area.regions if r.type=='WINDOW'),None)
            act=bpy.context.view_layer.objects.active
            if act and act.mode!='OBJECT':
                try: bpy.ops.object.mode_set(mode='OBJECT')
                except Exception: pass
            with bpy.context.temp_override(area=area, region=region):
                bpy.ops.object.select_all(action='DESELECT')
                t=bpy.data.objects.get(target) if target else None
                if t: t.hide_set(False); t.select_set(True); bpy.ops.view3d.view_axis(type=axis); bpy.ops.view3d.view_selected()
                else: bpy.ops.view3d.view_axis(type=axis); bpy.ops.view3d.view_all()
            break
    return json.dumps({"framed":axis,"target":target})

# ---------------------------------------------------------------------------
# F) ALINHAMENTO CIRURGICO (fluxo do diretor) — deforma o mesh FUNDIDO ate o
#    corpo dele casar com o CORPO BASE. Corpo alinhado -> roupa alinhada.
#    Warp por campo de deslocamento (KDTree): verts de corpo snap no base,
#    verts de roupa seguem suave (interp). Sem cor, sem screenshot.
# ---------------------------------------------------------------------------

def get_mesh_stats(object_name):
    """bbox + contagem (delegado live_geo; aqui p/ o fluxo do diretor)."""
    import sys as _s
    if r"D:\Alice\tools\auto-rig-fix\live" not in _s.path:
        _s.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
    import live_geo, importlib; importlib.reload(live_geo)
    return live_geo.get_mesh_stats(object_name)

def surgical_align(fused_name, base_name, body_thr=0.05, k=8, falloff=0.85):
    """Deforma 'fused' p/ o corpo casar com 'base'. Verts de corpo (dist<body_thr
    do base) -> snap na superficie base. Demais (roupa) -> deslocamento interpolado
    dos verts de corpo vizinhos (segue o corpo). Retorna JSON da operacao."""
    from mathutils import kdtree, Vector
    fused = bpy.data.objects.get(fused_name); base = bpy.data.objects.get(base_name)
    if not fused or not base:
        return json.dumps({"err": f"precisa '{fused_name}' e '{base_name}'"})
    Fm = fused.matrix_world; Bm = base.matrix_world
    bverts = [Bm @ v.co for v in base.data.vertices]
    kd = kdtree.KDTree(len(bverts))
    for i, p in enumerate(bverts): kd.insert(p, i)
    kd.balance()
    fverts = [Fm @ v.co for v in fused.data.vertices]
    disp = {}; body_idx = []
    for i, p in enumerate(fverts):
        co, bi, d = kd.find(p)
        if d < body_thr:
            disp[i] = co - p; body_idx.append(i)
    if len(body_idx) < 20:
        return json.dumps({"err": f"poucos verts de corpo ({len(body_idx)}) — alinhar/posar antes"})
    bkd = kdtree.KDTree(len(body_idx))
    for j, i in enumerate(body_idx): bkd.insert(fverts[i], j)
    bkd.balance()
    Fi = Fm.inverted(); moved = 0
    for i, p in enumerate(fverts):
        if i in disp:
            npos = p + disp[i]
        else:
            nbrs = bkd.find_n(p, k)
            wsum = 0.0; dsum = Vector((0, 0, 0))
            for (co, j, dd) in nbrs:
                w = 1.0/(dd*dd + 1e-5); dsum += disp[body_idx[j]]*w; wsum += w
            npos = p + (dsum/wsum)*falloff if wsum > 0 else p
        fused.data.vertices[i].co = Fi @ npos; moved += 1
    fused.data.update(); bpy.context.view_layer.update()
    return json.dumps({"status": "Deformacao Cirurgica Completa",
        "objeto": fused_name, "alinhado_com": base_name,
        "verts_corpo_snap": len(body_idx), "verts_roupa_warp": moved-len(body_idx),
        "total": moved, "msg": f"'{fused_name}' deformado p/ vestir '{base_name}' via projecao de vertices de corpo."})

def remove_sparse_verts(name, radius=0.02, min_neighbors=6):
    """Remove verts em regiao ESPARSA = fiapos flutuantes. RAPIDO (grid voxel numpy):
    bin verts em celulas de tam=radius, conta por celula, remove verts em celula rala.
    Vestido (denso) sobrevive."""
    import numpy as np, bmesh
    o=bpy.data.objects.get(name); me=o.data; nv=len(me.vertices)
    co=np.empty(nv*3, dtype=np.float64); me.vertices.foreach_get("co", co); co=co.reshape(-1,3)
    cell=np.floor(co/radius).astype(np.int64)
    keys=(cell[:,0]*73856093)^(cell[:,1]*19349663)^(cell[:,2]*83492791)
    uniq,inv,counts=np.unique(keys, return_inverse=True, return_counts=True)
    cellcount=counts[inv]
    kill_idx=np.where(cellcount<min_neighbors)[0]
    bm=bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    kill=[bm.verts[int(i)] for i in kill_idx]
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    bm.to_mesh(me); bm.free(); me.update()
    return json.dumps({"removed_sparse":len(kill_idx),"remaining":len(me.vertices)})

def clean_small_islands(name, min_verts=250):
    """Remove ilhas pequenas (fiapos de pele/cabelo soltos) apos extracao. Mantem
    ilhas grandes (vestido, cabelo). Flood-fill por conectividade."""
    import bmesh
    o=bpy.data.objects.get(name); me=o.data
    bm=bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    seen=set(); kill=[]
    for v in bm.verts:
        if v.index in seen: continue
        # flood fill ilha
        stack=[v]; island=[]; seen.add(v.index)
        while stack:
            cur=stack.pop(); island.append(cur)
            for e in cur.link_edges:
                ov=e.other_vert(cur)
                if ov.index not in seen: seen.add(ov.index); stack.append(ov)
        if len(island)<min_verts: kill.extend(island)
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    bm.to_mesh(me); bm.free(); me.update()
    return json.dumps({"removed_island_verts":len(kill),"remaining":len(me.vertices)})

def pose_nude_arms(name, deg=70, x_thr=0.16):
    """Posa bracos do corpo NUO pra baixo geometricamente (sem rig). Rotaciona verts
    com |x|>x_thr (bracos T-pose) em torno do ombro, no plano XZ (eixo Y), blend suave."""
    import math
    from mathutils import Matrix, Vector
    o=bpy.data.objects.get(name); me=o.data; M=o.matrix_world; Mi=M.inverted()
    co=[M@v.co for v in me.vertices]
    zs=[c.z for c in co]; sh_z=min(zs)+(max(zs)-min(zs))*0.79  # altura ombro ~79%
    for side,sgn in (("L",1),("R",-1)):
        # ombro: ponto onde o braco sai (|x|~x_thr na altura do ombro)
        shoulder=Vector((sgn*x_thr, 0, sh_z))
        R=Matrix.Rotation(math.radians(sgn*deg),4,'Y')
        seam=0.04  # blend so na costura do ombro (4cm), resto RIGIDO -> braco reto
        for i,c in enumerate(co):
            if (sgn>0 and c.x>x_thr) or (sgn<0 and c.x<-x_thr):
                t=min(1.0,(abs(c.x)-x_thr)/seam)   # 0->1 rapido, depois 1 (rigido)
                rel=c-shoulder; rot=(R@rel)+shoulder
                newc=c.lerp(rot, t)
                me.vertices[i].co = Mi@newc
    me.update(); bpy.context.view_layer.update()
    return json.dumps({"posed_arms":name,"deg":deg})

def extract_and_fit_clothing(base_body_name, fused_mesh_name, distance_threshold=0.018,
                             do_shrinkwrap=False, do_datatransfer=True):
    """Isola roupa: deleta verts do fundido perto da pele base (KDTree proximidade),
    [shrinkwrap off por padrao — colapsa roupa larga], data-transfer pesos, liga rig."""
    import bmesh
    from mathutils.kdtree import KDTree
    base_obj=bpy.data.objects.get(base_body_name); fused_obj=bpy.data.objects.get(fused_mesh_name)
    if not base_obj or not fused_obj:
        return json.dumps({"err": f"precisa '{base_body_name}' e '{fused_mesh_name}'"})
    if bpy.context.object and bpy.context.object.mode!='OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    # KDTree do corpo base (world space)
    bm_base=base_obj.data
    kd=KDTree(len(bm_base.vertices))
    for i,v in enumerate(bm_base.vertices): kd.insert(base_obj.matrix_world@v.co, i)
    kd.balance()
    # copia de trabalho do fundido
    cloth=fused_obj.copy(); cloth.data=fused_obj.data.copy()
    cloth.name=f"Vestido_{fused_mesh_name.split('_')[-1] if '_' in fused_mesh_name else fused_mesh_name}"
    bpy.context.scene.collection.objects.link(cloth)
    # bmesh: deleta verts perto da pele
    bm=bmesh.new(); bm.from_mesh(cloth.data); bm.verts.ensure_lookup_table()
    kill=[]
    for v in bm.verts:
        co,idx,dist=kd.find(cloth.matrix_world@v.co)
        if dist<distance_threshold: kill.append(v)
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    orphans=[v for v in bm.verts if not v.link_edges]
    bmesh.ops.delete(bm, geom=orphans, context='VERTS')
    bm.to_mesh(cloth.data); bm.free(); cloth.data.update()
    # shrinkwrap + data transfer pesos
    bpy.ops.object.select_all(action='DESELECT'); cloth.select_set(True)
    bpy.context.view_layer.objects.active=cloth
    if do_shrinkwrap:
        sw=cloth.modifiers.new("Ajuste_Anatomico","SHRINKWRAP"); sw.target=base_obj
        sw.wrap_method='NEAREST_SURFACEPOINT'; sw.wrap_mode='ABOVE_SURFACE'; sw.offset=0.002
        try: bpy.ops.object.modifier_apply(modifier=sw.name)
        except Exception as e: print("sw err",e)
    if do_datatransfer:
        dt=cloth.modifiers.new("Clonagem_Pesos","DATA_TRANSFER"); dt.object=base_obj
        dt.use_vert_data=True; dt.data_types_verts={'VGROUP_WEIGHTS'}; dt.vert_mapping='POLYINTERP_NEAREST'
        try: bpy.ops.object.modifier_apply(modifier=dt.name)
        except Exception as e: print("dt err",e)
    if base_obj.parent and base_obj.parent.type=='ARMATURE':
        cloth.parent=base_obj.parent
        am=cloth.modifiers.new("Armature","ARMATURE"); am.object=base_obj.parent
    return json.dumps({"status":"success","isolated_mesh":cloth.name,
        "removed_skin_verts":len(kill),"remaining_verts":len(cloth.data.vertices),
        "msg":"Pele removida, roupa isolada + ajustada + pesos clonados."})

def prep_base_body_posed(arm_deg=70, name="Alice_Base_Body", fbx=None):
    """Carrega nua RIGADA, posa bracos-baixo POR OSSO (POSE, nao rest) + aplica modifier
    Armature -> baka forma bracos-baixo limpa. Rig-based (NAO geometrico). fbx default=rigada."""
    import math
    from mathutils import Matrix
    if fbx is None: fbx=r"E:\References\3D\alice_FULL_rigged.fbx"
    before=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=fbx)
    new=[o for o in bpy.data.objects if o not in before]
    body=max([o for o in new if o.type=='MESH'], key=lambda o:len(o.data.vertices))
    arm=next((o for o in new if o.type=='ARMATURE'), None)
    if arm:
        # POSE bracos-baixo (SEM armature_apply, senao modifier vira identidade)
        bpy.context.view_layer.objects.active=arm
        if bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True)
        bpy.context.view_layer.objects.active=arm
        bpy.ops.object.mode_set(mode='POSE')
        mw=arm.matrix_world
        def rotY(n,deg):
            bpy.context.view_layer.update()
            pb=arm.pose.bones[n]; Mw=mw@pb.matrix; head=Mw.translation.copy()
            R=Matrix.Rotation(math.radians(deg),4,'Y')
            pb.matrix=mw.inverted()@(Matrix.Translation(head)@R@Matrix.Translation(-head)@Mw)
        rotY("mixamorig:LeftArm",+arm_deg); rotY("mixamorig:RightArm",-arm_deg)
        rotY("mixamorig:LeftForeArm",+arm_deg*0.5); rotY("mixamorig:RightForeArm",-arm_deg*0.5)
        bpy.context.view_layer.update()
        bpy.ops.object.mode_set(mode='OBJECT')
        # aplica o modifier Armature na malha (baka a pose braços-baixo)
        bpy.context.view_layer.objects.active=body
        had=False
        for m in list(body.modifiers):
            if m.type=='ARMATURE':
                try: bpy.ops.object.modifier_apply(modifier=m.name); had=True
                except Exception: pass
        if not had:  # sem modifier? parenteado -> adiciona, aplica
            md=body.modifiers.new("arm","ARMATURE"); md.object=arm
            try: bpy.ops.object.modifier_apply(modifier=md.name)
            except Exception: pass
        bpy.data.objects.remove(arm, do_unlink=True)
    body.name=name
    co=[v.co for v in body.data.vertices]; xs=[c.x for c in co]
    return json.dumps({"base": name, "verts": len(body.data.vertices),
        "x_span": round(max(xs)-min(xs),3)})

# ---------------------------------------------------------------------------
# E) SEGMENTACAO PELE vs ROUPA por COR (textura) — separar corpo do vestido.
#    Amostra cor por vert (UV->textura, numpy), classifica tom de pele, pinta
#    mascara p/ validar visual, depois deleta a pele (corpo) -> so roupa.
# ---------------------------------------------------------------------------

def _sample_vert_colors(mesh, img_name):
    """Cor RGB por vertice amostrando a textura via UV. numpy vetorizado."""
    import numpy as np
    me=mesh.data
    img=bpy.data.images.get(img_name)
    if not img or not img.has_data: return None
    nv=len(me.vertices); nl=len(me.loops)
    luv=np.empty(nl*2,dtype=np.float32); me.uv_layers.active.data.foreach_get("uv",luv); luv=luv.reshape(nl,2)
    lvi=np.empty(nl,dtype=np.int64); me.loops.foreach_get("vertex_index",lvi)
    vuv=np.zeros((nv,2),dtype=np.float32); seen=np.zeros(nv,dtype=bool)
    for i in range(nl):
        v=lvi[i]
        if not seen[v]: vuv[v]=luv[i]; seen[v]=True
    W,H=img.size
    px=np.array(img.pixels[:],dtype=np.float32).reshape(H,W,4)
    u=np.clip(vuv[:,0]%1.0,0,1); vv=np.clip(vuv[:,1]%1.0,0,1)
    xi=(u*(W-1)).astype(np.int64); yi=(vv*(H-1)).astype(np.int64)
    return px[yi,xi,:3]   # (nv,3)

def texture_skin_mask(mesh_name, img_name="texture_pbr_20250901",
                      r_min=0.28, rb_min=0.03, bright_max=0.88, bright_min=0.12, sat_max=0.55):
    """Classifica PELE (tom de carne) vs ROUPA por cor. Pinta color attr 'skin_mask'
    (vermelho=pele, cinza=roupa) + mostra no viewport. Retorna contagem."""
    import numpy as np
    obj=bpy.data.objects.get(mesh_name); me=obj.data
    cols=_sample_vert_colors(obj, img_name)
    if cols is None: return json.dumps({"err":f"textura '{img_name}' sem dados"})
    R,G,B=cols[:,0],cols[:,1],cols[:,2]
    mx=np.maximum(np.maximum(R,G),B); mn=np.minimum(np.minimum(R,G),B)
    bright=(R+G+B)/3.0; sat=np.where(mx>1e-5,(mx-mn)/mx,0)
    skin=(R>r_min)&(R>=G-0.02)&(G>=B-0.02)&((R-B)>rb_min)&(bright<bright_max)&(bright>bright_min)&(sat<sat_max)
    # color attr
    if "skin_mask" in me.color_attributes: me.color_attributes.remove(me.color_attributes["skin_mask"])
    ca=me.color_attributes.new("skin_mask","FLOAT_COLOR","POINT")
    out=np.zeros((len(me.vertices),4),dtype=np.float32); out[:,3]=1.0
    out[skin]=[1,0,0,1]; out[~skin]=[0.55,0.55,0.55,1]
    ca.data.foreach_set("color", out.ravel())
    me.update()
    # viewport mostra color attribute
    for area in bpy.context.screen.areas:
        if area.type=='VIEW_3D':
            sp=area.spaces[0]; sp.shading.type='SOLID'; sp.shading.color_type='VERTEX'
    return json.dumps({"verts":len(me.vertices),"skin":int(skin.sum()),
        "cloth":int((~skin).sum()),"skin_pct":round(100*float(skin.sum())/len(me.vertices),1)})

# ---------------------------------------------------------------------------
# C) VISAO GEOMETRICA — ler/editar vertices por coords X,Y,Z (sem screenshot).
#    Consolidado aqui (tb existe em live_geo). Com limite/regiao: 200k verts
#    crus estouram o contexto -> use sample_rate / bbox / limit.
# ---------------------------------------------------------------------------

def get_live_mesh_geometry(object_name, sample_rate=1, limit=4000,
                           xmin=None, xmax=None, zmin=None, zmax=None, world=False):
    """Coords X,Y,Z dos vertices em JSON (substitui screenshot). sample_rate amostra;
    limit corta o payload; xmin/xmax/zmin/zmax filtram regiao. world=True usa coords mundo."""
    obj = bpy.data.objects.get(object_name)
    if not obj or obj.type != 'MESH':
        return json.dumps({"err": f"'{object_name}' nao encontrado ou nao e malha."})
    bpy.context.view_layer.update()
    me = obj.data; M = obj.matrix_world
    out = []
    for i in range(0, len(me.vertices), max(1, sample_rate)):
        v = me.vertices[i]
        co = (M @ v.co) if world else v.co
        if xmin is not None and co.x < xmin: continue
        if xmax is not None and co.x > xmax: continue
        if zmin is not None and co.z < zmin: continue
        if zmax is not None and co.z > zmax: continue
        out.append({"id": v.index, "co": [round(co.x,4), round(co.y,4), round(co.z,4)]})
        if len(out) >= limit: break
    return json.dumps({"object_name": object_name,
        "world_location":[round(obj.location.x,4),round(obj.location.y,4),round(obj.location.z,4)],
        "total_vertices": len(me.vertices), "returned": len(out), "world": world,
        "vertices": out})

def apply_live_vertex_deformations(object_name, vertex_updates_json):
    """Recebe [{"id":i,"co":[x,y,z]}] (LOCAL) e reposiciona verts ao vivo no viewport.
    Aceita lista OU string JSON."""
    import mathutils
    obj = bpy.data.objects.get(object_name)
    if not obj or obj.type != 'MESH':
        return json.dumps({"err": f"'{object_name}' nao e malha valida."})
    try:
        updates = json.loads(vertex_updates_json) if isinstance(vertex_updates_json, str) else vertex_updates_json
        me = obj.data
        om = bpy.context.object.mode if bpy.context.active_object else 'OBJECT'
        if om != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
        n=0; mxv=len(me.vertices)
        for u in updates:
            i=u.get("id"); co=u.get("co")
            if i is not None and co is not None and i < mxv:
                me.vertices[i].co = mathutils.Vector(co); n+=1
        me.update(); bpy.context.view_layer.update()
        if om != 'OBJECT':
            try: bpy.ops.object.mode_set(mode=om)
            except Exception: pass
        return json.dumps({"status":"success","modified_vertices":n})
    except Exception as e:
        return json.dumps({"err": f"Falha na gravacao geometrica: {e}"})

# ---------------------------------------------------------------------------
# F) DETALHAMENTO PROCEDURAL POR CURVAS (linha-por-linha: babados + cabelo)
#    A IA de visao traca curvas Bezier sobre a arte; estas funcoes constroem
#    geometria 3D limpa SOBRE os trilhos (em vez de prompt textual -> malha borrada).
# ---------------------------------------------------------------------------

def _curve_world_points(curve_obj):
    """Pontos 3D (world) de TODOS os splines (bezier ou poly) da curva, em ordem."""
    from mathutils import Vector
    Mw = curve_obj.matrix_world; pts = []
    for spl in curve_obj.data.splines:
        if spl.type == 'BEZIER':
            for p in spl.bezier_points: pts.append(Mw @ p.co.copy())
        else:
            for p in spl.points: pts.append(Mw @ Vector((p.co[0], p.co[1], p.co[2])))
    return pts

def generate_procedural_ruffles(curve_name, ruffle_width=0.04, frequency=35.0,
                                amplitude=0.015, solidify=0.004, mat_name=None):
    """Curva-guia (IA) -> tira CORRUGADA (babado) onda-por-onda ao longo do trilho.
    normal horizontal + modulacao senoidal; cai ruffle_width em Z. Solidify p/ espessura."""
    import bmesh, math
    from mathutils import Vector
    cobj = bpy.data.objects.get(curve_name)
    if not cobj or cobj.type != 'CURVE':
        return json.dumps({"err": f"Curva guia '{curve_name}' nao encontrada/!=CURVE."})
    pts = _curve_world_points(cobj)
    if len(pts) < 2:
        return json.dumps({"err": f"Curva '{curve_name}' tem <2 pontos."})
    me = bpy.data.meshes.new(f"Mesh_{curve_name}_Babado")
    obj = bpy.data.objects.new(f"Babado_{curve_name}", me)
    bpy.context.scene.collection.objects.link(obj)
    bm = bmesh.new(); n = len(pts); pt=pb=None
    for i, p in enumerate(pts):
        t = i / (n - 1)
        tan = (pts[i+1]-p).normalized() if i < n-1 else (p-pts[i-1]).normalized()
        nrm = Vector((-tan.y, tan.x, 0.0))
        nrm = nrm.normalized() if nrm.length > 1e-6 else Vector((1,0,0))
        wave = nrm * (math.sin(t*frequency*math.pi*2) * amplitude)
        vt = bm.verts.new(p + wave)
        vb = bm.verts.new(p + wave - Vector((0,0,ruffle_width)))
        if pt and pb: bm.faces.new((pb, vb, vt, pt))
        pt, pb = vt, vb
    bm.to_mesh(me); bm.free(); me.update()
    for poly in me.polygons: poly.use_smooth = True
    if solidify and solidify > 0:
        m = obj.modifiers.new('sol','SOLIDIFY'); m.thickness = float(solidify)
    if mat_name and bpy.data.materials.get(mat_name):
        me.materials.append(bpy.data.materials[mat_name])
    return json.dumps({"status":"success","ruffle_object":obj.name,"polygons":len(me.polygons)})

def generate_hair_strands_from_guides(guide_curves_object, density=12,
                                      strand_radius=0.003, jitter=0.012, seed=7):
    """Curvas-guia (IA tracou madeixas) -> N fios por guia (jitter) como curva com BEVEL
    (tubo fino) = fios volumetricos renderizaveis. (NAO usa o op nativo hair-curves, que
    exige surface e falha headless — versao robusta + convertivel em mesh p/ jogo.)"""
    from mathutils import Vector
    import random; random.seed(seed)
    src = bpy.data.objects.get(guide_curves_object)
    if not src or src.type != 'CURVE':
        return json.dumps({"err": f"Guias de cabelo '{guide_curves_object}' nao e CURVE."})
    cur = bpy.data.curves.new(f"{src.name}_hairgen", 'CURVE'); cur.dimensions = '3D'
    cur.bevel_depth = float(strand_radius); cur.bevel_resolution = 1
    obj = bpy.data.objects.new(f"Cabelo_{guide_curves_object}", cur)
    bpy.context.scene.collection.objects.link(obj)
    strands = 0
    for spl in src.data.splines:
        if spl.type == 'BEZIER':
            base = [p.co.copy() for p in spl.bezier_points]
        else:
            base = [Vector((p.co[0],p.co[1],p.co[2])) for p in spl.points]
        if len(base) < 2: continue
        for d in range(max(1, density)):
            j = Vector((0,0,0)) if d == 0 else Vector((random.uniform(-jitter,jitter),
                          random.uniform(-jitter,jitter), random.uniform(-jitter,jitter)))
            ns = cur.splines.new('POLY'); ns.points.add(len(base)-1)
            for i, co in enumerate(base):
                taper = i/(len(base)-1)            # jitter cresce na ponta (raiz fixa)
                jj = j*taper
                ns.points[i].co = (co.x+jj.x, co.y+jj.y, co.z+jj.z, 1.0)
            strands += 1
    obj.matrix_world = src.matrix_world.copy()
    return json.dumps({"status":"success","hair_object":obj.name,"strands":strands})

# ---------------------------------------------------------------------------
# G) RIG DE SAIA (cadeias de ossos, estilo Nyanneco) + MASCARA ANTI-CLIPPING
# ---------------------------------------------------------------------------

def create_skirt_rig_assist(arm_name, curve_names_list, parent_bone_name="mixamorig:Hips",
                            bones_per_chain=3):
    """Curvas longitudinais da saia -> cadeias de ossos sequenciais no rig (vinculadas ao
    Hips). Dinamica secundaria de balanco sem custo de fisica de tecido."""
    from mathutils import Vector
    arm = bpy.data.objects.get(arm_name)
    if not arm or arm.type != 'ARMATURE':
        return json.dumps({"err": f"Esqueleto '{arm_name}' invalido/ausente."})
    if isinstance(curve_names_list, str):
        curve_names_list = [c.strip() for c in curve_names_list.split(',') if c.strip()]
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        try: bpy.ops.object.mode_set(mode='OBJECT')
        except Exception: pass
    bpy.context.view_layer.objects.active = arm
    Mi = arm.matrix_world.inverted()
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones
    has_parent = parent_bone_name in eb
    chains = 0; bones = 0
    for c_idx, c_name in enumerate(curve_names_list):
        c_obj = bpy.data.objects.get(c_name)
        if not c_obj or c_obj.type != 'CURVE': continue
        pts = _curve_world_points(c_obj)
        if len(pts) < 2: continue
        seg = max(1, len(pts)//bones_per_chain)
        last = parent_bone_name if has_parent else None
        for b in range(bones_per_chain):
            ps = pts[min(b*seg, len(pts)-2)]; pe = pts[min((b+1)*seg, len(pts)-1)]
            nb = eb.new(f"skirt_{c_idx}_{b}")
            nb.head = Mi @ ps; nb.tail = Mi @ pe
            if last and last in eb:
                nb.parent = eb[last]; nb.use_connect = False
            last = nb.name; bones += 1
        chains += 1
    bpy.ops.object.mode_set(mode='OBJECT'); bpy.context.view_layer.update()
    return json.dumps({"status":"success","chains_built":chains,"bones_added":bones,
                       "parent_found":has_parent})

def apply_anti_clipping_mask(body_mesh_name, clothing_mesh_name, detection_threshold=0.02):
    """Troca modular de vestido sem vazamento: esconde (MASK invertido) os verts da PELE
    do corpo que ficam SOB o tecido (KDTree do vestido). Sem carne por baixo -> sem clip."""
    from mathutils import kdtree
    body = bpy.data.objects.get(body_mesh_name); cloth = bpy.data.objects.get(clothing_mesh_name)
    if not body or not cloth:
        return json.dumps({"err":"Corpo ou vestido nao localizado."})
    cv = [cloth.matrix_world @ v.co for v in cloth.data.vertices]
    if not cv: return json.dumps({"err":"Vestido sem vertices."})
    kd = kdtree.KDTree(len(cv))
    for i,p in enumerate(cv): kd.insert(p, i)
    kd.balance()
    gname = f"Mask_{cloth.name}"
    vg = body.vertex_groups.get(gname) or body.vertex_groups.new(name=gname)
    hidden = 0
    for v in body.data.vertices:
        co, idx, dist = kd.find(body.matrix_world @ v.co)
        if dist is not None and dist < detection_threshold:
            vg.add([v.index], 1.0, 'REPLACE'); hidden += 1
        else:
            vg.remove([v.index])
    mname = f"AntiClip_{cloth.name}"
    mod = body.modifiers.get(mname) or body.modifiers.new(name=mname, type='MASK')
    mod.vertex_group = gname; mod.invert_vertex_group = True   # esconde o que esta no grupo
    return json.dumps({"status":"success","masked_vertices":hidden,"modifier":mod.name})

# ---------------------------------------------------------------------------
# H) PONTE VISAO->CURVAS: JSON do vision_trace.py (linhas 2D da arte) -> curvas-guia
#    3D na malha alvo (mapeia u,v -> bbox frontal + PROJETA na superficie). Alimenta F+G.
# ---------------------------------------------------------------------------

def curves_from_trace(json_path, target_mesh, front_offset=0.02, project=True):
    """Le {image_size,mode,curves:[{pts2d:[[u,v]..]}]} do vision_trace e cria 1 curva-guia
    por traco, mapeada na bbox frontal da malha alvo e PROJETADA na superficie (closest pt).
    u(0..1)=esq->dir->X, v(0..1)=topo->baixo->Z, frente=ymin. Retorna nomes p/ ruffles/skirt/hair."""
    from mathutils import Vector
    data = json.load(open(json_path, encoding='utf-8'))
    tgt = bpy.data.objects.get(target_mesh)
    if not tgt or tgt.type != 'MESH':
        return json.dumps({"err": f"Malha alvo '{target_mesh}' invalida."})
    Mw = tgt.matrix_world; Mi = Mw.inverted()
    cs = [Mw @ Vector(c) for c in tgt.bound_box]
    xs=[c.x for c in cs]; ys=[c.y for c in cs]; zs=[c.z for c in cs]
    xmin,xmax,ymin,zmin,zmax = min(xs),max(xs),min(ys),min(zs),max(zs)
    Wd, Hd = (xmax-xmin) or 1.0, (zmax-zmin) or 1.0
    made = []
    for ci, c in enumerate(data.get('curves', [])):
        pts2d = c.get('pts2d', [])
        if len(pts2d) < 2: continue
        cu = bpy.data.curves.new(f"Guide_{data.get('mode','c')}_{ci}", 'CURVE'); cu.dimensions='3D'
        sp = cu.splines.new('POLY'); sp.points.add(len(pts2d)-1)
        for i,(u,v) in enumerate(pts2d):
            wx = xmin+u*Wd; wz = zmax-v*Hd
            wp = Vector((wx, ymin-front_offset, wz))
            if project:
                # RAYCAST frente->tras no (X,Z) -> superficie FRONTAL (mantem espalhamento;
                # closest_point colapsava tudo no centro). fallback closest se nao acertar.
                o_l = Mi @ Vector((wx, ymin-1.0, wz)); d_l = (Mi.to_3x3() @ Vector((0,1,0))).normalized()
                hit, loc, nrm, idx = tgt.ray_cast(o_l, d_l)
                if hit:
                    wp = Mw @ (loc + nrm*front_offset)
                else:
                    res = tgt.closest_point_on_mesh(Mi @ wp)
                    if res[0]: wp = Mw @ (res[1] + res[2]*front_offset)
            sp.points[i].co = (wp.x, wp.y, wp.z, 1.0)
        ob = bpy.data.objects.new(cu.name, cu); bpy.context.scene.collection.objects.link(ob)
        made.append(ob.name)
    return json.dumps({"status":"success","mode":data.get('mode'),"guides":made,"count":len(made)})

def skirt_rings_from_mesh(mesh_name, n_tiers=5, z_hi=0.55, z_lo=0.06, dirs=40, out=0.02):
    """Aneis-TIER fechados extraidos do PROPRIO mesh: em N alturas (frac z_hi=quadril ->
    z_lo=barra) raycast de FORA pra dentro em `dirs` direcoes -> contorno EXTERNO da saia.
    Da tiers SIMETRICOS e cobertura TOTAL (corrige os gaps/assimetria do trace so-frontal).
    Cada anel alimenta generate_procedural_ruffles."""
    from mathutils import Vector
    import math
    obj = bpy.data.objects.get(mesh_name)
    if not obj or obj.type != 'MESH':
        return json.dumps({"err": f"Malha '{mesh_name}' invalida."})
    Mw = obj.matrix_world; Mi = Mw.inverted()
    cs = [Mw @ Vector(c) for c in obj.bound_box]
    xs=[c.x for c in cs]; ys=[c.y for c in cs]; zs=[c.z for c in cs]
    xmin,xmax,ymin,ymax,zmin,zmax = min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)
    cx=(xmin+xmax)/2; cy=(ymin+ymax)/2; H=(zmax-zmin) or 1.0
    far = max(xmax-xmin, ymax-ymin)*0.75 + 0.5
    made = []
    for t in range(n_tiers):
        zf = z_hi - (z_hi-z_lo)*(t/max(1, n_tiers-1))
        wz = zmin + zf*H
        pts = []
        for a in range(dirs):
            ang = 2*math.pi*a/dirs; ca, sa = math.cos(ang), math.sin(ang)
            o = Mi @ Vector((cx+far*ca, cy+far*sa, wz))
            d = (Mi.to_3x3() @ Vector((-ca, -sa, 0))).normalized()
            hit, loc, nrm, idx = obj.ray_cast(o, d)
            if hit:
                pts.append(Mw @ loc + Vector((ca, sa, 0))*out)
        if len(pts) < 8: continue
        cu = bpy.data.curves.new(f"Ring_{t}", 'CURVE'); cu.dimensions='3D'
        sp = cu.splines.new('POLY'); sp.points.add(len(pts)-1); sp.use_cyclic_u = True
        for i, p in enumerate(pts): sp.points[i].co = (p.x, p.y, p.z, 1.0)
        ob = bpy.data.objects.new(cu.name, cu); bpy.context.scene.collection.objects.link(ob)
        made.append(ob.name)
    return json.dumps({"status":"success","rings":made,"count":len(made)})

# ---------------------------------------------------------------------------
# I) SNAPSHOTS / ROLLBACK (loop ao vivo: snapshot por passo -> desaprovou, volta)
# ---------------------------------------------------------------------------
SNAP_DIR = r"D:\Alice\tools\auto-rig-fix\work\snap"

def snapshot(label="step"):
    """Salva COPIA numerada do .blend (nao muda o arquivo ativo). Ponto de rollback."""
    import os, glob, re
    os.makedirs(SNAP_DIR, exist_ok=True)
    n = len(glob.glob(os.path.join(SNAP_DIR, "*.blend")))
    safe = re.sub(r'[^A-Za-z0-9_-]', '_', str(label))[:40]
    p = os.path.join(SNAP_DIR, f"{n:03d}_{safe}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=p, copy=True)
    return json.dumps({"snapshot": n, "label": safe, "path": p})

def snaps():
    """Lista snapshots existentes (indice + nome)."""
    import os, glob
    fs = sorted(glob.glob(os.path.join(SNAP_DIR, "*.blend")))
    return json.dumps({"count": len(fs), "snaps": [os.path.basename(p) for p in fs]})

def rollback(index):
    """Reabre o snapshot <index> (desfaz alteracoes ate aquele ponto). Bridge sobrevive."""
    import os, glob
    fs = sorted(glob.glob(os.path.join(SNAP_DIR, "*.blend")))
    tgt = next((p for p in fs if os.path.basename(p).startswith(f"{int(index):03d}_")), None)
    if not tgt:
        return json.dumps({"err": f"snapshot {index} nao existe", "have": [os.path.basename(p) for p in fs]})
    bpy.ops.wm.open_mainfile(filepath=tgt)
    return json.dumps({"rolled_back_to": os.path.basename(tgt)})


# ===========================================================================
# MERGE: image-to-rig pipeline (Hunyuan/Trellis GLB -> full rig + skirt + face)
# ===========================================================================

from mathutils import Vector
import math as _math

def auto_process_ai_generated_mesh(file_path, character_name="AI_Character", target_height=1.70):
    if not os.path.exists(file_path):
        return json.dumps({"err": f"Arquivo nao encontrado: {file_path}"})
    if bpy.context.active_object and bpy.context.active_object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for o in list(bpy.context.scene.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    ext = os.path.splitext(file_path)[-1].lower()
    if ext in ['.glb', '.gltf']: bpy.ops.import_scene.gltf(filepath=file_path)
    elif ext == '.obj': bpy.ops.import_scene.obj(filepath=file_path)
    elif ext == '.fbx': bpy.ops.import_scene.fbx(filepath=file_path)
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    if not meshes: return json.dumps({"err": "Nenhum mesh importado."})
    bpy.ops.object.select_all(action='DESELECT')
    for m in meshes: m.select_set(True)
    main_mesh = meshes[0]; bpy.context.view_layer.objects.active = main_mesh
    if len(meshes) > 1: bpy.ops.object.join()
    main_mesh.name = f"{character_name}_Mesh"
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
    co = [main_mesh.matrix_world @ v.co for v in main_mesh.data.vertices]
    zs = [p.z for p in co]; h = max(zs) - min(zs)
    if h > 1e-5:
        sf = target_height / h; main_mesh.scale = (sf, sf, sf)
        bpy.ops.object.transform_apply(scale=True)
    co2 = [main_mesh.matrix_world @ v.co for v in main_mesh.data.vertices]
    main_mesh.location.z -= min(p.z for p in co2)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return json.dumps({"status": "OK", "mesh_name": main_mesh.name})

def build_complete_skeleton(arm_name="AI_Armature"):
    amt = bpy.data.armatures.new(f"{arm_name}_Data")
    arm_obj = bpy.data.objects.new(arm_name, amt)
    bpy.context.scene.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')
    bones_def = {
        "mixamorig:Hips": ((0,0,0.9),(0,0,1.1),None),
        "mixamorig:Spine": ((0,0,1.1),(0,0,1.25),"mixamorig:Hips"),
        "mixamorig:Spine1": ((0,0,1.25),(0,0,1.42),"mixamorig:Spine"),
        "mixamorig:Neck": ((0,0,1.42),(0,0,1.52),"mixamorig:Spine1"),
        "mixamorig:Head": ((0,0,1.52),(0,0,1.75),"mixamorig:Neck"),
        "mixamorig:Jaw": ((0,0.02,1.54),(0,0.09,1.52),"mixamorig:Head"),
        "mixamorig:Eye_L": ((-0.035,0.06,1.64),(-0.035,0.10,1.64),"mixamorig:Head"),
        "mixamorig:Eye_R": ((0.035,0.06,1.64),(0.035,0.10,1.64),"mixamorig:Head"),
    }
    for side, sign in [("Left",-1),("Right",1)]:
        bones_def.update({
            f"mixamorig:{side}UpLeg": ((sign*0.09,0,0.9),(sign*0.10,0,0.5),"mixamorig:Hips"),
            f"mixamorig:{side}Leg": ((sign*0.10,0,0.5),(sign*0.11,-0.02,0.1),f"mixamorig:{side}UpLeg"),
            f"mixamorig:{side}Foot": ((sign*0.11,-0.02,0.1),(sign*0.11,0.12,0.0),f"mixamorig:{side}Leg"),
            f"mixamorig:{side}Shoulder": ((0,0,1.40),(sign*0.14,0,1.42),"mixamorig:Spine1"),
            f"mixamorig:{side}Arm": ((sign*0.14,0,1.42),(sign*0.36,-0.01,1.40),f"mixamorig:{side}Shoulder"),
            f"mixamorig:{side}ForeArm": ((sign*0.36,-0.01,1.40),(sign*0.54,-0.03,1.38),f"mixamorig:{side}Arm"),
            f"mixamorig:{side}Hand": ((sign*0.54,-0.03,1.38),(sign*0.61,-0.04,1.36),f"mixamorig:{side}ForeArm"),
        })
        for f_idx, finger in enumerate(["Thumb","Index","Middle","Ring","Pinky"]):
            offset_y = (f_idx-2)*0.012
            p0 = Vector((sign*0.61,-0.04+offset_y,1.36)); last_p = f"mixamorig:{side}Hand"
            for ph in ["1","2","3"]:
                p1 = p0 + Vector((sign*0.022,0,-0.003))
                bn = f"mixamorig:{side}Hand{finger}{ph}"
                bones_def[bn] = (p0.copy(), p1.copy(), last_p); last_p = bn; p0 = p1.copy()
    for name,(head,tail,parent) in bones_def.items():
        eb = amt.edit_bones.new(name); eb.head = head; eb.tail = tail
        if parent: eb.parent = amt.edit_bones.get(parent)
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm_obj

def apply_skirt_layers_and_weighting(mesh_name, arm_name, layers=3, bones_per_ring=8):
    arm = bpy.data.objects.get(arm_name); mesh = bpy.data.objects.get(mesh_name)
    if not arm or not mesh: return
    bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='EDIT')
    skirt_bones = []; base_z, height = 0.9, 0.65
    for lyr in range(layers):
        radius = 0.14 + (lyr*0.09)
        for b in range(bones_per_ring):
            angle = (b/bones_per_ring)*2*_math.pi
            x = _math.cos(angle)*radius; y = _math.sin(angle)*radius
            parent = "mixamorig:Hips"; segments = 3; z_step = height/segments
            for seg in range(segments):
                bn = f"skirt_L{lyr}_R{b}_S{seg}"
                eb = arm.data.edit_bones.new(bn)
                z_start = base_z - (seg*z_step); z_end = base_z - ((seg+1)*z_step)
                flare = 1.0 + (seg*0.25)
                eb.head = Vector((x*flare, y*flare, z_start))
                eb.tail = Vector((x*(flare+0.1), y*(flare+0.1), z_end))
                eb.parent = arm.data.edit_bones.get(parent); parent = bn
                skirt_bones.append(bn)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = mesh
    # vectorize: precompute all vert world positions ONCE
    import numpy as _np
    n = len(mesh.data.vertices)
    co = _np.empty(n*3, _np.float32); mesh.data.vertices.foreach_get('co', co); co = co.reshape(n,3)
    mw = _np.array(mesh.matrix_world); W = (_np.c_[co, _np.ones(n)] @ mw.T)[:,:3]
    for bn in skirt_bones:
        vg = mesh.vertex_groups.get(bn) or mesh.vertex_groups.new(name=bn)
        bone = arm.data.bones.get(bn)
        bh = arm.matrix_world @ bone.head_local
        bh_np = _np.array([bh.x, bh.y, bh.z], _np.float32)
        zband = _np.abs(W[:,2] - bh_np[2]) < 0.12
        if not zband.any(): continue
        d = _np.linalg.norm(W[zband] - bh_np, axis=1)
        sel_local = d < 0.15
        if not sel_local.any(): continue
        idxs = _np.where(zband)[0][sel_local]
        weights = (1.0 - (d[sel_local]/0.15)) * 0.85
        for i, w in zip(idxs.tolist(), weights.tolist()):
            vg.add([i], float(w), 'REPLACE')

def apply_facial_shape_keys(mesh_name):
    mesh = bpy.data.objects.get(mesh_name)
    if not mesh: return
    bpy.context.view_layer.objects.active = mesh
    if not mesh.data.shape_keys: mesh.shape_key_add(name="Basis")
    sk_m = mesh.shape_key_add(name="Mouth_Open")
    sk_bl = mesh.shape_key_add(name="Blink_L")
    sk_br = mesh.shape_key_add(name="Blink_R")
    mc = Vector((0,0.08,1.58)); elc = Vector((-0.035,0.06,1.64)); erc = Vector((0.035,0.06,1.64))
    import numpy as _np
    n = len(mesh.data.vertices)
    co = _np.empty(n*3, _np.float32); mesh.data.vertices.foreach_get('co', co); co = co.reshape(n,3)
    mw = _np.array(mesh.matrix_world); W = (_np.c_[co, _np.ones(n)] @ mw.T)[:,:3]
    mcn = _np.array([mc.x,mc.y,mc.z]); eln = _np.array([elc.x,elc.y,elc.z]); ern = _np.array([erc.x,erc.y,erc.z])
    mouth_sel = (_np.linalg.norm(W - mcn, axis=1) < 0.045) & (W[:,2] < mcn[2])
    bl_sel = (_np.linalg.norm(W - eln, axis=1) < 0.028) & (W[:,2] > eln[2])
    br_sel = (_np.linalg.norm(W - ern, axis=1) < 0.028) & (W[:,2] > ern[2])
    for idx in _np.where(mouth_sel)[0]:
        sk_m.data[int(idx)].co.z -= 0.025; sk_m.data[int(idx)].co.y += 0.005
    for idx in _np.where(bl_sel)[0]:
        sk_bl.data[int(idx)].co.z -= 0.012
    for idx in _np.where(br_sel)[0]:
        sk_br.data[int(idx)].co.z -= 0.012

def setup_advanced_finger_constraints(arm_name):
    arm = bpy.data.objects.get(arm_name)
    if not arm: return
    bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='POSE')
    for side in ["Left","Right"]:
        for f in ["Thumb","Index","Middle","Ring","Pinky"]:
            for ph in ["1","2","3"]:
                pb = arm.pose.bones.get(f"mixamorig:{side}Hand{f}{ph}")
                if not pb: continue
                for c in list(pb.constraints): pb.constraints.remove(c)
                c = pb.constraints.new('LIMIT_ROTATION')
                c.use_limit_x = c.use_limit_y = c.use_limit_z = True; c.owner_space = 'LOCAL'
                if f == "Thumb":
                    c.min_x, c.max_x, c.min_y, c.max_y, c.min_z, c.max_z = -0.25, 0.85, -0.15, 0.15, -0.45, 0.45
                else:
                    if ph in ["2","3"]:
                        c.min_x, c.max_x, c.min_y, c.max_y, c.min_z, c.max_z = 0.0, 1.60, -0.001, 0.001, -0.001, 0.001
                    else:
                        c.min_x, c.max_x, c.min_y, c.max_y, c.min_z, c.max_z = -0.05, 1.40, -0.01, 0.01, -0.15, 0.15
    bpy.ops.object.mode_set(mode='OBJECT')

def inject_secondary_physics_bones(mesh_name, arm_name, parent_spine="mixamorig:Spine1", parent_hips="mixamorig:Hips"):
    mesh = bpy.data.objects.get(mesh_name); arm = bpy.data.objects.get(arm_name)
    if not mesh or not arm: return
    bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='EDIT')
    defs = {
        "physics_breast_L": (Vector((-0.065, 0.08, 0.02)), Vector((-0.065, 0.16, 0.02)), parent_spine),
        "physics_breast_R": (Vector((0.065, 0.08, 0.02)), Vector((0.065, 0.16, 0.02)), parent_spine),
        "physics_butt_L":   (Vector((-0.075,-0.06,-0.05)), Vector((-0.075,-0.14,-0.08)), parent_hips),
        "physics_butt_R":   (Vector((0.075,-0.06,-0.05)), Vector((0.075,-0.14,-0.08)), parent_hips),
    }
    new_bones = []
    for bn, (h_off, t_off, p_name) in defs.items():
        pb = arm.data.edit_bones.get(p_name)
        if not pb: continue
        eb = arm.data.edit_bones.new(bn)
        eb.head = pb.head + (pb.matrix.to_3x3() @ h_off)
        eb.tail = pb.head + (pb.matrix.to_3x3() @ t_off)
        eb.parent = pb; new_bones.append(bn)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = mesh
    import numpy as _np
    n = len(mesh.data.vertices)
    co = _np.empty(n*3, _np.float32); mesh.data.vertices.foreach_get('co', co); co = co.reshape(n,3)
    mw = _np.array(mesh.matrix_world); W = (_np.c_[co, _np.ones(n)] @ mw.T)[:,:3]
    for bn in new_bones:
        vg = mesh.vertex_groups.get(bn) or mesh.vertex_groups.new(name=bn)
        bone = arm.data.bones.get(bn)
        bh = arm.matrix_world @ bone.head_local
        bh_np = _np.array([bh.x, bh.y, bh.z], _np.float32)
        radius = 0.09 if "breast" in bn else 0.12
        d = _np.linalg.norm(W - bh_np, axis=1)
        inside = d < radius
        if "_L" in bn: inside &= (W[:,0] <= 0)
        elif "_R" in bn: inside &= (W[:,0] >= 0)
        if not inside.any(): continue
        idxs = _np.where(inside)[0]
        weights = ((1.0 - (d[inside]/radius))**2) * 0.75
        for i, w in zip(idxs.tolist(), weights.tolist()):
            vg.add([i], float(w), 'REPLACE')
    bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='POSE')
    for bn in new_bones:
        pb = arm.pose.bones.get(bn)
        if not pb: continue
        c = pb.constraints.new('LIMIT_ROTATION')
        c.use_limit_x = c.use_limit_y = c.use_limit_z = True; c.owner_space = 'LOCAL'
        if "breast" in bn:
            c.min_x, c.max_x, c.min_y, c.max_y, c.min_z, c.max_z = -0.15, 0.15, -0.05, 0.05, -0.12, 0.12
        else:
            c.min_x, c.max_x, c.min_y, c.max_y, c.min_z, c.max_z = -0.10, 0.10, -0.02, 0.02, -0.08, 0.08
    bpy.ops.object.mode_set(mode='OBJECT')

def apply_vision_details_to_mesh(mesh_name, json_trace_path,
                                  res=2048, line_width=3, line_intensity=0.92,
                                  bump_strength=0.6, add_displacement=False,
                                  disp_strength=0.008, project_axis='Y'):
    """
    Injeta JSON de 'linhas de forca' do vision_trace.py como Displacement+Normal Map.
    Reconstrui relevo visual (motifs/babados/dobras finas) que a IA (Hunyuan/Unique3D)
    perdeu, sem precisar gerar geometria nova.

    res: textura quadrada lado (2048 default).
    line_width: stroke px (anti-aliased).
    line_intensity: 0..1 (escuro=fundo, claro=relevo).
    bump_strength: forca do bump no shader (0..2).
    add_displacement: True = adiciona Displace modifier (deforma malha de verdade).
    disp_strength: amplitude do Displace (metros).
    project_axis: eixo de proj UV ('Y'=frontal, 'X'=lateral, 'Z'=topo).
    """
    if not os.path.exists(json_trace_path):
        return json.dumps({"err": f"trace nao encontrado: {json_trace_path}"})
    with open(json_trace_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    mesh = bpy.data.objects.get(mesh_name)
    if not mesh:
        return json.dumps({"err": f"mesh {mesh_name} nao encontrada"})

    import numpy as _np

    # 1) raster curves -> heightmap (numpy)
    W = H = int(res)
    height = _np.zeros((H, W), dtype=_np.float32)
    curves = data.get("curves", data.get("contours", []))
    n_pts = 0

    def _stamp(ix, iy, val, w):
        # anti-aliased filled circle stroke
        r = max(1, int(w))
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                d = (dx*dx + dy*dy) ** 0.5
                if d > r: continue
                xx, yy = ix + dx, iy + dy
                if 0 <= xx < W and 0 <= yy < H:
                    falloff = max(0.0, 1.0 - d / r)
                    v = val * falloff
                    if v > height[yy, xx]:
                        height[yy, xx] = v

    def _line(p0, p1, val, w):
        x0, y0 = p0; x1, y1 = p1
        # normalize 0..1 if needed
        if x0 <= 1: x0 *= W
        if y0 <= 1: y0 *= H
        if x1 <= 1: x1 *= W
        if y1 <= 1: y1 *= H
        steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(steps + 1):
            t = i / max(steps, 1)
            ix = int(x0 + (x1 - x0) * t)
            iy = int(y0 + (y1 - y0) * t)
            _stamp(ix, iy, val, w)

    for cv in curves:
        pts = cv.get("points", cv) if isinstance(cv, dict) else cv
        if len(pts) < 2: continue
        for k in range(len(pts) - 1):
            _line(pts[k], pts[k+1], line_intensity, line_width)
            n_pts += 1

    # 2) smooth height pra suavizar antes de gerar normal
    # box blur 3x3 manual
    def _blur(a, passes=2):
        out = a.copy()
        for _ in range(passes):
            tmp = _np.zeros_like(out)
            tmp[1:-1,1:-1] = (out[:-2,:-2]+out[:-2,1:-1]+out[:-2,2:]+
                              out[1:-1,:-2]+out[1:-1,1:-1]+out[1:-1,2:]+
                              out[2:,:-2]+out[2:,1:-1]+out[2:,2:]) / 9.0
            out = tmp
        return out
    height_s = _blur(height, passes=1)

    # 3) gerar tres imagens Blender: height, color (deriva), normal RGB
    def _ensure_img(name, w, h, float_buf=False):
        img = bpy.data.images.get(name)
        if img is None:
            img = bpy.data.images.new(name, w, h, alpha=False, float_buffer=float_buf)
        return img

    # heightmap (gray)
    img_h = _ensure_img(f"{mesh_name}_VisionHeight", W, H, float_buf=True)
    pix_h = _np.stack([height_s, height_s, height_s, _np.ones_like(height_s)], axis=-1)
    img_h.pixels = pix_h.ravel().tolist()

    # normal map: derivative
    gx = _np.zeros_like(height_s); gy = _np.zeros_like(height_s)
    gx[:,1:-1] = (height_s[:,2:] - height_s[:,:-2]) * 0.5
    gy[1:-1,:] = (height_s[2:,:] - height_s[:-2,:]) * 0.5
    # encode RGB normal (tangent space): R=gx*0.5+0.5, G=gy*0.5+0.5, B=1.0
    nz = _np.ones_like(height_s)
    norm = _np.sqrt(gx*gx + gy*gy + nz*nz)
    nx = gx / norm; ny = gy / norm; nzn = nz / norm
    img_n = _ensure_img(f"{mesh_name}_VisionNormal", W, H, float_buf=True)
    pix_n = _np.stack([nx*0.5+0.5, ny*0.5+0.5, nzn*0.5+0.5, _np.ones_like(nzn)], axis=-1)
    img_n.pixels = pix_n.ravel().tolist()

    # 4) UV: project from view (front/side/top) se ainda nao tem
    if not mesh.data.uv_layers:
        bpy.context.view_layer.objects.active = mesh
        for o in bpy.context.selected_objects: o.select_set(False)
        mesh.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        if project_axis == 'Y':
            bpy.ops.uv.project_from_view(orthographic=False)
        else:
            bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
        bpy.ops.object.mode_set(mode='OBJECT')

    # 5) material + Principled BSDF + normal map + bump
    if not mesh.data.materials or not mesh.data.materials[0]:
        m = bpy.data.materials.new(f"{mesh_name}_VisionMat"); m.use_nodes = True
        mesh.data.materials.clear(); mesh.data.materials.append(m)
    mat = mesh.data.materials[0]
    if not mat.use_nodes: mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get('Principled BSDF') or nt.nodes.new('ShaderNodeBsdfPrincipled')

    # remove old vision nodes
    for nd in list(nt.nodes):
        if nd.name.startswith('VisionDetail_'):
            nt.nodes.remove(nd)

    tex_n = nt.nodes.new('ShaderNodeTexImage'); tex_n.name = 'VisionDetail_NrmTex'
    tex_n.image = img_n; tex_n.image.colorspace_settings.name = 'Non-Color'
    nmap = nt.nodes.new('ShaderNodeNormalMap'); nmap.name = 'VisionDetail_NormalMap'
    nmap.inputs['Strength'].default_value = bump_strength
    nt.links.new(tex_n.outputs['Color'], nmap.inputs['Color'])

    tex_h = nt.nodes.new('ShaderNodeTexImage'); tex_h.name = 'VisionDetail_HeightTex'
    tex_h.image = img_h; tex_h.image.colorspace_settings.name = 'Non-Color'
    bump = nt.nodes.new('ShaderNodeBump'); bump.name = 'VisionDetail_Bump'
    bump.inputs['Strength'].default_value = bump_strength * 0.5
    nt.links.new(tex_h.outputs['Color'], bump.inputs['Height'])
    # chain: bump feeds normal map, normal map feeds BSDF
    nt.links.new(bump.outputs['Normal'], nmap.inputs['Normal'])
    nt.links.new(nmap.outputs['Normal'], bsdf.inputs['Normal'])

    # 6) optional real Displacement modifier
    disp_info = None
    if add_displacement:
        # remove old vision displace
        for m in list(mesh.modifiers):
            if m.name == 'VisionDisplace': mesh.modifiers.remove(m)
        # ensure subsurf for detail
        if not any(m.type == 'SUBSURF' for m in mesh.modifiers):
            sub = mesh.modifiers.new('VisionSubsurf', 'SUBSURF')
            sub.levels = 1; sub.render_levels = 2
        dt = bpy.data.textures.get(f"{mesh_name}_VisionDispTex")
        if dt is None:
            dt = bpy.data.textures.new(f"{mesh_name}_VisionDispTex", type='IMAGE')
        dt.image = img_h
        mod = mesh.modifiers.new('VisionDisplace', 'DISPLACE')
        mod.texture = dt
        mod.strength = disp_strength
        mod.mid_level = 0.0
        mod.texture_coords = 'UV'
        disp_info = {"strength": disp_strength, "modifier": "VisionDisplace"}

    return json.dumps({
        "status": "OK",
        "curves": len(curves),
        "segments": n_pts,
        "height_img": img_h.name,
        "normal_img": img_n.name,
        "bump_strength": bump_strength,
        "displacement": disp_info,
    })

def execute_ultimate_pipeline(generated_file_path, character_name="Alice_Perfeita", use_shd=True):
    """Merged pipeline: ingest GLB -> skeleton -> physics bones -> skirt layers ->
    SHD skinning (fallback ARMATURE_AUTO) -> finger constraints -> facial shape keys."""
    res = json.loads(auto_process_ai_generated_mesh(generated_file_path, character_name))
    if "err" in res: return json.dumps(res)
    mesh_name = res["mesh_name"]
    arm_obj = build_complete_skeleton(f"Rig_{character_name}"); arm_name = arm_obj.name
    inject_secondary_physics_bones(mesh_name, arm_name)
    apply_skirt_layers_and_weighting(mesh_name, arm_name, layers=3, bones_per_ring=8)
    skin_result = "unknown"
    if use_shd and shd_available():
        import time as _time
        try:
            launch = json.loads(shd_launch(mesh_name, arm_name))
            if launch.get("launched"):
                # poll until weight.txt ready (max 240s)
                for _ in range(120):
                    _time.sleep(2)
                    st = json.loads(shd_status())
                    if st.get("weight_size", 0) > 100 and not st.get("running"):
                        break
                fin = json.loads(shd_finalize(mesh_name, arm_name))
                skin_result = f"SHD ok: {fin}"
            else:
                skin_result = f"SHD launch failed: {launch}"
        except Exception as e:
            skin_result = f"SHD exception: {e}; fallback ARMATURE_AUTO"
            bpy.ops.object.select_all(action='DESELECT')
            bpy.data.objects[mesh_name].select_set(True); arm_obj.select_set(True)
            bpy.context.view_layer.objects.active = arm_obj
            bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    else:
        bpy.ops.object.select_all(action='DESELECT')
        bpy.data.objects[mesh_name].select_set(True); arm_obj.select_set(True)
        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
        skin_result = "ARMATURE_AUTO (SHD unavailable)"
    setup_advanced_finger_constraints(arm_name)
    apply_facial_shape_keys(mesh_name)
    return json.dumps({"status":"OK","mesh":mesh_name,"arm":arm_name,"skin":skin_result})


def find_nearest_bone(accessory_obj, armature_obj):
    """Centro de massa do acessorio -> osso mais proximo do esqueleto."""
    from mathutils import Vector
    bbox = [accessory_obj.matrix_world @ Vector(corner) for corner in accessory_obj.bound_box]
    center = sum(bbox, Vector()) / 8.0
    nearest_bone_name = None
    min_dist = float('inf')
    for bone in armature_obj.pose.bones:
        bone_head_global = armature_obj.matrix_world @ bone.head
        dist = (center - bone_head_global).length
        if dist < min_dist:
            min_dist = dist
            nearest_bone_name = bone.name
    return nearest_bone_name


def configure_accessory_physics(obj_name, character_mesh_name, tipo):
    """Bind do acessorio extraido em osso fixo (sem cloth) por tipo."""
    obj = bpy.data.objects.get(obj_name)
    if not obj:
        return
    obj.vertex_groups.clear()
    bone_by_type = {
        "knife": "mixamorig:RightUpLeg",
        "belts": "mixamorig:Spine1",
        "gloves": "mixamorig:LeftHand",
    }
    bone = bone_by_type.get(tipo, "mixamorig:Hips")
    vg = obj.vertex_groups.new(name=bone)
    for v in obj.data.vertices:
        vg.add([v.index], 1.0, 'REPLACE')


def separate_accessories_by_uv_mask(mesh_name, masks_directory, base_name="alice"):
    """Le mascaras 2D do SAM/ComfyUI, mapeia UV->pixel branco, separa acessorios."""
    import bmesh
    main_obj = bpy.data.objects.get(mesh_name)
    if not main_obj or main_obj.type != 'MESH':
        return json.dumps({"err": f"mesh {mesh_name} invalido"})
    config_acessorios = {
        "knife": {"suffix": "_mask_knife.png", "target_name": "Acessorio_Faca_Rigida"},
        "belts": {"suffix": "_mask_belts.png", "target_name": "Acessorio_Cintos_Corpo"},
        "gloves": {"suffix": "_mask_gloves.png", "target_name": "Acessorio_Luvas"},
    }
    separated = []
    for chave, config in config_acessorios.items():
        mask_path = os.path.join(masks_directory, f"{base_name}{config['suffix']}")
        if not os.path.exists(mask_path):
            continue
        mask_img = bpy.data.images.load(mask_path)
        W, H = mask_img.size
        pixels = list(mask_img.pixels)
        bpy.context.view_layer.objects.active = main_obj
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(main_obj.data)
        uv_layer = bm.loops.layers.uv.active
        if uv_layer is None:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.data.images.remove(mask_img)
            continue
        bpy.ops.mesh.select_all(action='DESELECT')
        for face in bm.faces:
            sel = False
            for loop in face.loops:
                uv = loop[uv_layer].uv
                px = min(int(uv.x * W), W - 1)
                py = min(int(uv.y * H), H - 1)
                idx = (py * W + px) * 4
                if pixels[idx] > 0.5 and pixels[idx + 1] > 0.5 and pixels[idx + 2] > 0.5:
                    sel = True
                    break
            if sel:
                face.select_set(True)
        bmesh.update_edit_mesh(main_obj.data)
        selected_faces = [f for f in bm.faces if f.select]
        if selected_faces:
            bpy.ops.mesh.separate(type='SELECTED')
            bpy.ops.object.mode_set(mode='OBJECT')
            new_obj = [o for o in bpy.context.selected_objects if o != main_obj][-1]
            new_obj.name = config['target_name']
            configure_accessory_physics(new_obj.name, main_obj.name, chave)
            separated.append(new_obj.name)
            bpy.context.view_layer.objects.active = main_obj
        else:
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.data.images.remove(mask_img)
    return json.dumps({"status": "OK", "separated": separated})


def universal_accessory_slicer(mesh_name, armature_name, masks_directory, base_prefix="alice"):
    """Versao universal: varre todas as mascaras na pasta + anchora osso mais proximo."""
    import bmesh
    import glob
    main_obj = bpy.data.objects.get(mesh_name)
    arm_obj = bpy.data.objects.get(armature_name)
    if not main_obj or not arm_obj:
        return json.dumps({"err": "mesh ou armature ausente"})
    mask_files = glob.glob(os.path.join(masks_directory, f"{base_prefix}_mask_*.png"))
    separated = []
    for mask_path in mask_files:
        mask_img = bpy.data.images.load(mask_path)
        W, H = mask_img.size
        pixels = list(mask_img.pixels)
        bpy.context.view_layer.objects.active = main_obj
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(main_obj.data)
        uv_layer = bm.loops.layers.uv.active
        if uv_layer is None:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.data.images.remove(mask_img)
            continue
        bpy.ops.mesh.select_all(action='DESELECT')
        for face in bm.faces:
            sel = False
            for loop in face.loops:
                uv = loop[uv_layer].uv
                px = min(int(uv.x * W), W - 1)
                py = min(int(uv.y * H), H - 1)
                idx = (py * W + px) * 4
                if pixels[idx] > 0.5 and pixels[idx + 1] > 0.5 and pixels[idx + 2] > 0.5:
                    sel = True
                    break
            if sel:
                face.select_set(True)
        bmesh.update_edit_mesh(main_obj.data)
        if any(f.select for f in bm.faces):
            bpy.ops.mesh.separate(type='SELECTED')
            bpy.ops.object.mode_set(mode='OBJECT')
            acc_obj = [o for o in bpy.context.selected_objects if o != main_obj][-1]
            acc_obj.name = f"Prop_{os.path.basename(mask_path).replace('.png', '')}"
            target_bone = find_nearest_bone(acc_obj, arm_obj)
            acc_obj.vertex_groups.clear()
            vg = acc_obj.vertex_groups.new(name=target_bone)
            for v in acc_obj.data.vertices:
                vg.add([v.index], 1.0, 'REPLACE')
            separated.append({"obj": acc_obj.name, "bone": target_bone})
            bpy.context.view_layer.objects.active = main_obj
        else:
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.data.images.remove(mask_img)
    return json.dumps({"status": "OK", "separated": separated})


# ===========================================================================
# AAA layered pipeline: clean base mesh + proportional mold + dress isolation
# + data-transfer weight binding (replaces manual painting).
# ===========================================================================

DEFAULT_BASE_TEMPLATE = r"D:/Alice/tools/auto-rig-fix/work/alice_rigged.fbx"

def load_clean_base_mesh(template_path=None):
    """Importa malha anatomica perfeita pre-rigada. Retorna (body_mesh, armature)."""
    template_path = template_path or DEFAULT_BASE_TEMPLATE
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"base anatomico nao encontrado: {template_path}")
    existing = set(bpy.data.objects)
    if template_path.endswith('.fbx'):
        bpy.ops.import_scene.fbx(filepath=template_path)
    elif template_path.endswith('.blend'):
        with bpy.data.libraries.load(template_path, link=False) as (data_from, data_to):
            data_to.objects = data_from.objects
        for o in data_to.objects:
            if o is not None:
                bpy.context.scene.collection.objects.link(o)
    elif template_path.endswith('.glb') or template_path.endswith('.gltf'):
        bpy.ops.import_scene.gltf(filepath=template_path)
    new_objs = set(bpy.data.objects) - existing
    base_body = None
    base_armature = None
    for o in new_objs:
        if o.type == 'MESH' and base_body is None:
            base_body = o
            base_body.name = "Base_Body"
        elif o.type == 'ARMATURE' and base_armature is None:
            base_armature = o
            base_armature.name = "Base_Armature"
    return base_body, base_armature

def match_proportions(ai_mesh_obj, base_armature_obj):
    """Mede bbox do AI mesh e escala armature base p/ encaixar (uniforme p/ evitar squash)."""
    from mathutils import Vector
    ai_bbox = [ai_mesh_obj.matrix_world @ Vector(c) for c in ai_mesh_obj.bound_box]
    ai_dim = Vector((max(v.x for v in ai_bbox) - min(v.x for v in ai_bbox),
                     max(v.y for v in ai_bbox) - min(v.y for v in ai_bbox),
                     max(v.z for v in ai_bbox) - min(v.z for v in ai_bbox)))
    base_bbox = [base_armature_obj.matrix_world @ Vector(c) for c in base_armature_obj.bound_box]
    base_dim = Vector((max(v.x for v in base_bbox) - min(v.x for v in base_bbox),
                       max(v.y for v in base_bbox) - min(v.y for v in base_bbox),
                       max(v.z for v in base_bbox) - min(v.z for v in base_bbox)))
    sz = ai_dim.z / base_dim.z if base_dim.z > 1e-5 else 1.0
    base_armature_obj.scale = (sz, sz, sz)
    bpy.context.view_layer.objects.active = base_armature_obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return {"scale_uniform": round(sz, 4),
            "ai_dim": [round(v, 3) for v in ai_dim],
            "base_dim": [round(v, 3) for v in base_dim]}

def optimize_clothing_interior(clothing_mesh_name, solidify_thickness=0.002, smooth_iters=2):
    """Solidify + Smooth pra dar volume de tecido e limpar ruido geometrico do Hunyuan."""
    obj = bpy.data.objects.get(clothing_mesh_name)
    if not obj:
        return
    for m in list(obj.modifiers):
        if m.name in ("Cloth_Thickness", "Cloth_Surface_Smooth"):
            obj.modifiers.remove(m)
    sol = obj.modifiers.new("Cloth_Thickness", 'SOLIDIFY')
    sol.thickness = solidify_thickness
    sol.use_even_offset = True
    sm = obj.modifiers.new("Cloth_Surface_Smooth", 'SMOOTH')
    sm.factor = 0.5
    sm.iterations = smooth_iters

def professional_layer_binding(base_body_name, clothing_mesh_name):
    """Data Transfer pesos perna/joelho base -> vestido. Armature copiado + Collision no base."""
    body = bpy.data.objects.get(base_body_name)
    cloth = bpy.data.objects.get(clothing_mesh_name)
    if not body or not cloth:
        return json.dumps({"err": "camadas ausentes"})
    body_arm_mod = next((m for m in body.modifiers if m.type == 'ARMATURE'), None)
    if not body_arm_mod or not body_arm_mod.object:
        return json.dumps({"err": "base body sem Armature modifier"})
    for m in list(cloth.modifiers):
        if m.type == 'ARMATURE' and m.name in ("Armature", "Armature_Binding"):
            cloth.modifiers.remove(m)
    arm_mod = cloth.modifiers.new("Armature_Binding", 'ARMATURE')
    arm_mod.object = body_arm_mod.object
    for m in list(cloth.modifiers):
        if m.name == "AAA_Weight_Transfer":
            cloth.modifiers.remove(m)
    dt = cloth.modifiers.new("AAA_Weight_Transfer", 'DATA_TRANSFER')
    dt.object = body
    dt.use_vert_data = True
    dt.data_types_verts = {'VGROUP_WEIGHTS'}
    dt.vert_mapping = 'NEAREST'
    bpy.context.view_layer.objects.active = cloth
    try:
        bpy.ops.object.datalayout_transfer(modifier="AAA_Weight_Transfer")
    except Exception:
        pass
    bpy.ops.object.modifier_apply(modifier="AAA_Weight_Transfer")
    if not any(m.type == 'COLLISION' for m in body.modifiers):
        body.modifiers.new("Body_Collision", 'COLLISION')
        try:
            body.collision.thickness_outer = 0.005
        except Exception:
            pass
    return json.dumps({"bound": cloth.name,
                       "armature": body_arm_mod.object.name,
                       "vgroups_transferred": len(cloth.vertex_groups)})

def compile_professional_character_pipeline(ai_glb_path, template_path=None, masks_dir=None,
                                             clean_scene=True):
    """Orquestracao AAA: AI GLB -> base humano limpo -> molde proporcional -> slice acessorios
    -> isolar vestido -> data transfer pesos."""
    if clean_scene:
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=ai_glb_path)
    ai_meshes = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if not ai_meshes:
        return json.dumps({"err": "GLB sem mesh"})
    ai_mesh = ai_meshes[0]
    ai_mesh.name = "AI_Mesh_Mold"
    base_body, base_arm = load_clean_base_mesh(template_path)
    if not base_body or not base_arm:
        return json.dumps({"err": "base humano nao carregou"})
    prop = match_proportions(ai_mesh, base_arm)
    sliced = []
    if masks_dir and os.path.exists(masks_dir):
        r = json.loads(universal_accessory_slicer(ai_mesh.name, base_arm.name, masks_dir, "alice"))
        sliced = r.get("separated", [])
    ai_mesh.name = "Camada_Vestido_Principal"
    optimize_clothing_interior(ai_mesh.name)
    bind = json.loads(professional_layer_binding(base_body.name, ai_mesh.name))
    return json.dumps({"status": "OK",
                       "base": base_body.name,
                       "arm": base_arm.name,
                       "scale": prop,
                       "sliced": sliced,
                       "binding": bind,
                       "vestido": ai_mesh.name})


# ===========================================================================
# apply_layer_spec — consome JSON do pipeline_layer_inspector + constroi camada
# proceduralmente sobre Alice_Base_Body. Cada camada usa color palette p/ material,
# texture_map p/ bump, curves p/ outline (futuro: loft 3D direto dos pontos).
# ===========================================================================

# Geometria default por nome de camada (z_hem, z_top, n_ring, n_h, hem_radius, palette_swap)
LAYER_PRESETS = {
    "saia_L1":    {"z_hem": 0.45, "z_top": 1.10, "n_ring": 96, "n_h": 26,
                   "waist_rx": 0.115, "waist_ry": 0.075, "hem_rx": 0.345, "hem_ry": 0.300, "power": 2.0},
    "saia_L2":    {"z_hem": 0.55, "z_top": 1.10, "n_ring": 96, "n_h": 22,
                   "waist_rx": 0.115, "waist_ry": 0.075, "hem_rx": 0.320, "hem_ry": 0.280, "power": 2.0},
    "saia_L3":    {"z_hem": 0.65, "z_top": 1.10, "n_ring": 96, "n_h": 18,
                   "waist_rx": 0.115, "waist_ry": 0.075, "hem_rx": 0.300, "hem_ry": 0.260, "power": 2.0},
    "corpete":    {"z_hem": 1.05, "z_top": 1.32, "n_ring": 96, "n_h": 22,
                   "waist_rx": 0.110, "waist_ry": 0.075, "hem_rx": 0.155, "hem_ry": 0.110, "power": 1.0},
    "mangas":     {"z_hem": 1.32, "z_top": 1.42, "n_ring": 48, "n_h": 10,
                   "waist_rx": 0.040, "waist_ry": 0.040, "hem_rx": 0.080, "hem_ry": 0.080, "power": 1.0},
    "boots":      {"z_hem": 0.00, "z_top": 0.30, "n_ring": 48, "n_h": 10,
                   "waist_rx": 0.055, "waist_ry": 0.055, "hem_rx": 0.075, "hem_ry": 0.075, "power": 1.0},
}

def _build_aline_mesh(name, preset, parent_armature):
    """Cria mesh A-line lofted (cintura -> barra) parented ao Armature."""
    import math
    h = preset
    verts = []
    faces = []
    for i in range(h["n_h"]):
        t = i / (h["n_h"] - 1)
        z = h["z_hem"] + (h["z_top"] - h["z_hem"]) * t
        s = ((h["z_top"] - z) / (h["z_top"] - h["z_hem"])) ** h["power"]
        rx = h["waist_rx"] + (h["hem_rx"] - h["waist_rx"]) * s
        ry = h["waist_ry"] + (h["hem_ry"] - h["waist_ry"]) * s
        for j in range(h["n_ring"]):
            a = 2 * math.pi * j / h["n_ring"]
            verts.append((rx * math.cos(a), ry * math.sin(a), z))
    for ri in range(h["n_h"] - 1):
        for j in range(h["n_ring"]):
            A = ri * h["n_ring"] + j
            B = ri * h["n_ring"] + (j + 1) % h["n_ring"]
            C = (ri + 1) * h["n_ring"] + (j + 1) % h["n_ring"]
            D = (ri + 1) * h["n_ring"] + j
            faces.append((A, B, C, D))
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    for p in me.polygons:
        p.use_smooth = True
    if parent_armature:
        o.parent = parent_armature
        o.matrix_parent_inverse = parent_armature.matrix_world.inverted()
        vg = o.vertex_groups.new(name="mixamorig:Hips")
        vg.add(list(range(len(me.vertices))), 1.0, 'REPLACE')
        md = o.modifiers.new("Armature", 'ARMATURE')
        md.object = parent_armature
    sub = o.modifiers.new("Subsurf", 'SUBSURF')
    sub.levels = 1; sub.render_levels = 2
    return o

def _palette_to_material(name, palette_list):
    """Cria material com cor dominante + emit secundaria baseado em palette spec."""
    if not palette_list: palette_list = [{"rgb": [120, 120, 120]}]
    dom = palette_list[0]["rgb"]
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (dom[0]/255, dom[1]/255, dom[2]/255, 1)
        try: bsdf.inputs['Roughness'].default_value = 0.55
        except Exception: pass
    return mat

def _load_palette_from_inspector(spec_dict, view="front"):
    """Tenta ler color palette do PNG de swatches: amostra cor a cada 80px (cellsize do swatch)."""
    images = spec_dict.get(view, {}).get("images", {})
    swatch_path = images.get("palette")
    if not swatch_path or not os.path.exists(swatch_path):
        return []
    import numpy as np
    try:
        img = bpy.data.images.load(swatch_path, check_existing=True)
        W, H = img.size
        px = np.array(img.pixels[:]).reshape(H, W, 4)
        # cellsize 80
        ncols = max(1, W // 80)
        pal = []
        for i in range(ncols):
            cx = i * 80 + 40
            if cx >= W: break
            sample = px[H//3:2*H//3, cx]
            mean = sample.mean(axis=0)
            r, g, b = int(mean[0]*255), int(mean[1]*255), int(mean[2]*255)
            pal.append({"rgb": [r, g, b]})
        return pal
    except Exception as e:
        print("palette load err:", e)
        return []

def apply_layer_spec(layer_name, spec_path):
    """Consome layer_spec.json (do pipeline_layer_inspector) + constroi a camada
    sobre Alice_Base_Body. Geometria do preset, material do color palette do inspetor."""
    if not os.path.exists(spec_path):
        return json.dumps({"err": f"spec nao existe: {spec_path}"})
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)
    preset = LAYER_PRESETS.get(layer_name)
    if not preset:
        return json.dumps({"err": f"layer '{layer_name}' sem preset",
                           "known": list(LAYER_PRESETS.keys())})
    arm = bpy.data.objects.get("Alice_Base_Rig") or bpy.data.objects.get("Armature")
    if not arm:
        return json.dumps({"err": "Alice_Base_Rig nao encontrado"})
    obj_name = f"Layer_{layer_name}"
    o = _build_aline_mesh(obj_name, preset, arm)
    palette = _load_palette_from_inspector(spec, "front")
    mat = _palette_to_material(f"{layer_name}_mat", palette)
    o.data.materials.clear()
    o.data.materials.append(mat)
    # viewport tag redraw
    for w in bpy.context.window_manager.windows:
        for a in w.screen.areas:
            if a.type == 'VIEW_3D': a.tag_redraw()
    return json.dumps({"status": "OK",
                       "layer": layer_name,
                       "obj": obj_name,
                       "verts": len(o.data.vertices),
                       "color_dom_rgb": palette[0]["rgb"] if palette else None,
                       "spec_views": list(spec.keys())})


# ===========================================================================
# Inside-Out Assembly: SAM mascaras ordenadas por area (grande -> pequeno)
# Camada 1 = vestido base (maior mask, data transfer pesos do corpo)
# Camada 2 = harness/corpete (shrinkwrap sobre vestido +2mm)
# Camada 3+ = props rigidos (find_nearest_bone + bind 1.0)
# ===========================================================================

def _mask_white_pixel_count(filepath):
    try:
        img = bpy.data.images.load(filepath, check_existing=False)
        pixels = list(img.pixels)
        white = sum(1 for i in range(0, len(pixels), 4) if pixels[i] > 0.5)
        bpy.data.images.remove(img)
        return white
    except Exception:
        return 0

def compile_complex_layered_character(glb_path, template_path=None, masks_dir=None,
                                       base_prefix="alice", clean_scene=True):
    """Inside-Out assembly. Importa GLB, importa base humano, ordena masks por area,
    fatia + binda camadas progressivamente (skin -> base layer -> harness -> props)."""
    import bmesh, glob
    from mathutils import Vector

    if clean_scene:
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o, do_unlink=True)

    bpy.ops.import_scene.gltf(filepath=glb_path)
    ai_meshes = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if not ai_meshes:
        return json.dumps({"err": "GLB sem mesh"})
    ai_mesh = ai_meshes[0]
    ai_mesh.name = "AI_Raw_Mold"

    base_body, base_arm = load_clean_base_mesh(template_path)
    if not base_body or not base_arm:
        return json.dumps({"err": "base humano nao carregou"})

    prop = match_proportions(ai_mesh, base_arm)

    if not masks_dir or not os.path.exists(masks_dir):
        return json.dumps({"err": "masks_dir invalido"})

    pattern = os.path.join(masks_dir, f"{base_prefix}_mask_*.png")
    mask_files = glob.glob(pattern)
    sorted_masks = []
    for p in mask_files:
        sz = _mask_white_pixel_count(p)
        if sz > 500:
            sorted_masks.append((p, sz))
    sorted_masks.sort(key=lambda x: x[1], reverse=True)

    created = []
    previous_target = base_body

    for idx, (mask_path, size) in enumerate(sorted_masks):
        mask_img = bpy.data.images.load(mask_path)
        W, H = mask_img.size
        pixels = list(mask_img.pixels)

        bpy.context.view_layer.objects.active = ai_mesh
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(ai_mesh.data)
        uv_layer = bm.loops.layers.uv.active
        if uv_layer is None:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.data.images.remove(mask_img)
            continue
        bpy.ops.mesh.select_all(action='DESELECT')
        for face in bm.faces:
            for loop in face.loops:
                uv = loop[uv_layer].uv
                px = min(int(uv.x * W), W - 1)
                py = min(int(uv.y * H), H - 1)
                pix_idx = (py * W + px) * 4
                if pixels[pix_idx] > 0.5:
                    face.select_set(True)
                    break
        bmesh.update_edit_mesh(ai_mesh.data)

        if not any(f.select for f in bm.faces):
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.data.images.remove(mask_img)
            continue

        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')
        layer_obj = [o for o in bpy.context.selected_objects if o != ai_mesh][-1]

        if idx == 0:
            layer_obj.name = "AAA_Camada1_VestidoBase"
            sol = layer_obj.modifiers.new("Espessura", 'SOLIDIFY')
            sol.thickness = 0.001
            arm_mod = layer_obj.modifiers.new("Rig_Armature", 'ARMATURE')
            arm_mod.object = base_arm
            dt = layer_obj.modifiers.new("Pesos_Anatomo", 'DATA_TRANSFER')
            dt.object = base_body
            dt.use_vert_data = True
            dt.data_types_verts = {'VGROUP_WEIGHTS'}
            dt.vert_mapping = 'NEAREST'
            bpy.context.view_layer.objects.active = layer_obj
            try:
                bpy.ops.object.datalayout_transfer(modifier="Pesos_Anatomo")
            except Exception:
                pass
            bpy.ops.object.modifier_apply(modifier="Pesos_Anatomo")
            previous_target = layer_obj
        elif idx == 1:
            layer_obj.name = "AAA_Camada2_HarnessPreto"
            sw = layer_obj.modifiers.new("Abracar_Vestido", 'SHRINKWRAP')
            sw.target = previous_target
            sw.wrap_method = 'NEAREST_SURFACEPOINT'
            sw.offset = 0.002
            arm_mod = layer_obj.modifiers.new("Rig_Armature", 'ARMATURE')
            arm_mod.object = base_arm
            dt = layer_obj.modifiers.new("Pesos_Harness", 'DATA_TRANSFER')
            dt.object = base_body
            dt.use_vert_data = True
            dt.data_types_verts = {'VGROUP_WEIGHTS'}
            dt.vert_mapping = 'NEAREST'
            bpy.context.view_layer.objects.active = layer_obj
            try:
                bpy.ops.object.datalayout_transfer(modifier="Pesos_Harness")
            except Exception:
                pass
            bpy.ops.object.modifier_apply(modifier="Pesos_Harness")
        else:
            layer_obj.name = f"AAA_Camada3_Prop_{idx}"
            target_bone = find_nearest_bone(layer_obj, base_arm)
            layer_obj.vertex_groups.clear()
            vg = layer_obj.vertex_groups.new(name=target_bone)
            vg.add([v.index for v in layer_obj.data.vertices], 1.0, 'REPLACE')
            arm_mod = layer_obj.modifiers.new("Rig_Armature", 'ARMATURE')
            arm_mod.object = base_arm

        created.append({"layer": layer_obj.name, "mask_area_px": size})
        bpy.context.view_layer.objects.active = ai_mesh
        bpy.data.images.remove(mask_img)

    bpy.data.objects.remove(ai_mesh, do_unlink=True)

    if not any(m.type == 'COLLISION' for m in base_body.modifiers):
        base_body.modifiers.new("Pele_Colisao", 'COLLISION')

    return json.dumps({"status": "OK",
                       "base_body": base_body.name,
                       "armature": base_arm.name,
                       "scale": prop,
                       "layers_created": created})
