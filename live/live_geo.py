# -*- coding: utf-8 -*-
"""live_geo — tools do script do user (visao geometrica + edicao ao vivo) adaptadas
pra rodar DENTRO do Blender via bridge (sem stdio MCP, que nao funciona com bpy).

Blender VE por dados X,Y,Z (nao screenshot). IA le coords -> decide -> edita verts.
Carrego via bridge: import live_geo; live_geo.<tool>(...). Print do retorno = meu olho.
"""
import bpy, mathutils, json

# ---------------------------------------------------------------------------
# VISAO GEOMETRICA (substitui screenshot)
# ---------------------------------------------------------------------------

def get_mesh_stats(object_name):
    """Bbox + contagem rapida. Barato (nao lista verts)."""
    obj = bpy.data.objects.get(object_name)
    if not obj or obj.type != 'MESH':
        return json.dumps({"err": f"'{object_name}' nao e mesh"})
    me = obj.data
    cs = [obj.matrix_world @ v.co for v in me.vertices]
    xs=[c.x for c in cs]; ys=[c.y for c in cs]; zs=[c.z for c in cs]
    return json.dumps({"object": object_name, "verts": len(me.vertices),
        "vgroups": [g.name for g in obj.vertex_groups],
        "world_X":[round(min(xs),4),round(max(xs),4)],
        "world_Y":[round(min(ys),4),round(max(ys),4)],
        "world_Z":[round(min(zs),4),round(max(zs),4)]}, ensure_ascii=False)

def get_mesh_geometry(object_name, sample_rate=1, xmin=None,xmax=None,
                      zmin=None,zmax=None,world=True,limit=4000):
    """Coords dos verts (local ou world). Filtro opcional por faixa X/Z e amostragem.
    limit corta o payload (verts gigantes estouram contexto)."""
    obj = bpy.data.objects.get(object_name)
    if not obj or obj.type != 'MESH':
        return json.dumps({"err": f"'{object_name}' invalido"})
    bpy.context.view_layer.update()
    me = obj.data
    M = obj.matrix_world
    out=[]
    for i in range(0, len(me.vertices), max(1,sample_rate)):
        v = me.vertices[i]
        co = M @ v.co if world else v.co
        if xmin is not None and co.x < xmin: continue
        if xmax is not None and co.x > xmax: continue
        if zmin is not None and co.z < zmin: continue
        if zmax is not None and co.z > zmax: continue
        out.append({"id":v.index,"co":[round(co.x,4),round(co.y,4),round(co.z,4)]})
        if len(out)>=limit: break
    return json.dumps({"object":object_name,"total":len(me.vertices),
        "returned":len(out),"world":world,"verts":out}, ensure_ascii=False)

def count_in_region(object_name, xmin=None,xmax=None,zmin=None,zmax=None,absx=None,world=True):
    """So conta verts numa regiao (pra eu saber 'quantos braco furam' sem listar)."""
    obj = bpy.data.objects.get(object_name); me=obj.data; M=obj.matrix_world
    n=0
    for v in me.vertices:
        co = M @ v.co if world else v.co
        if absx is not None and abs(co.x) < absx: continue
        if xmin is not None and co.x < xmin: continue
        if xmax is not None and co.x > xmax: continue
        if zmin is not None and co.z < zmin: continue
        if zmax is not None and co.z > zmax: continue
        n+=1
    return json.dumps({"object":object_name,"count":n})

# ---------------------------------------------------------------------------
# EDICAO AO VIVO
# ---------------------------------------------------------------------------

def modify_mesh_vertices(object_name, vertex_updates):
    """vertex_updates: lista [{"id":i,"co":[x,y,z]}] em LOCAL. Reposiciona ao vivo."""
    obj = bpy.data.objects.get(object_name); me=obj.data
    if bpy.context.active_object and bpy.context.active_object.mode!='OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    n=0
    for u in vertex_updates:
        i=u.get("id"); co=u.get("co")
        if i is not None and co is not None and i < len(me.vertices):
            me.vertices[i].co = mathutils.Vector(co); n+=1
    me.update(); bpy.context.view_layer.update()
    return json.dumps({"modificados":n})

def delete_verts_region(object_name, absx=None,xmin=None,xmax=None,zmin=None,zmax=None,world=True):
    """Deleta verts numa regiao (ex: excesso de braco |x|>thr). Usa bmesh."""
    import bmesh
    obj=bpy.data.objects.get(object_name); me=obj.data; M=obj.matrix_world
    if bpy.context.active_object and bpy.context.active_object.mode!='OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bm=bmesh.new(); bm.from_mesh(me)
    kill=[]
    for v in bm.verts:
        co = M @ v.co if world else v.co
        ok=True
        if absx is not None and not (abs(co.x)>absx): ok=False
        if xmin is not None and not (co.x>=xmin): ok=False
        if xmax is not None and not (co.x<=xmax): ok=False
        if zmin is not None and not (co.z>=zmin): ok=False
        if zmax is not None and not (co.z<=zmax): ok=False
        if ok: kill.append(v)
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    bm.to_mesh(me); bm.free(); me.update()
    return json.dumps({"deletados":len(kill),"restam":len(me.vertices)})

# ---------------------------------------------------------------------------
# PIPELINE VESTIDO (do script do user)
# ---------------------------------------------------------------------------

def skirt_to_hips_by_legweight(object_name, zmax_rel=0.58):
    """Anti-estilhaco: verts cujo peso DOMINANTE e osso de perna E abaixo de zmax_rel
    -> 100% Hips. Saia vira sino rigido. Arms (peso em braco) intactos."""
    obj = bpy.data.objects.get(object_name); me = obj.data
    hips = obj.vertex_groups.get("mixamorig:Hips")
    if not hips:
        return json.dumps({"err":"sem mixamorig:Hips"})
    leg_kw = ("UpLeg","Leg","Foot","ToeBase")
    gi_leg = {g.index for g in obj.vertex_groups if any(k in g.name for k in leg_kw)}
    gi_byidx = {g.index:g for g in obj.vertex_groups}
    zs=[v.co.z for v in me.vertices]; mn=min(zs); mx=max(zs); h=mx-mn
    moved=0
    for v in me.vertices:
        zr=(v.co.z-mn)/h
        if zr>zmax_rel: continue
        # peso dominante
        best=None; bestw=0.0
        for g in v.groups:
            if g.weight>bestw: bestw=g.weight; best=g.group
        if best in gi_leg:
            # zera todos, poe Hips=1
            for g in list(v.groups):
                grp = gi_byidx.get(g.group)
                if grp: grp.remove([v.index])
            hips.add([v.index],1.0,'REPLACE')
            moved+=1
    me.update()
    return json.dumps({"reassigned_to_hips":moved})

def pose_bone_rotY(arm_name, bone, deg):
    """Rotaciona 1 bone em Y global (pra testar deform). Nao aplica rest."""
    import math
    from mathutils import Matrix
    arm=bpy.data.objects.get(arm_name)
    bpy.context.view_layer.objects.active=arm
    if bpy.context.object.mode!='POSE': bpy.ops.object.mode_set(mode='POSE')
    bpy.context.view_layer.update()
    mw=arm.matrix_world; pb=arm.pose.bones[bone]; Mw=mw@pb.matrix; head=Mw.translation.copy()
    R=Matrix.Rotation(math.radians(deg),4,'Y')
    pb.matrix=mw.inverted()@(Matrix.Translation(head)@R@Matrix.Translation(-head)@Mw)
    bpy.context.view_layer.update()
    return json.dumps({"posed":bone,"deg":deg})

def pose_world(arm_name, rots):
    """rots = [[bone, axis('X'/'Y'/'Z'), deg], ...]. Reseta esses bones e rotaciona
    cada um em torno da PROPRIA cabeca no eixo GLOBAL. Pra testar deform ao vivo."""
    import math
    from mathutils import Matrix
    arm = bpy.data.objects.get(arm_name)
    bpy.context.view_layer.objects.active = arm
    if bpy.context.object.mode != 'POSE':
        bpy.ops.object.mode_set(mode='POSE')
    mw = arm.matrix_world
    for bone, axis, deg in rots:
        arm.pose.bones[bone].matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    for bone, axis, deg in rots:
        bpy.context.view_layer.update()
        pb = arm.pose.bones[bone]; Mw = mw @ pb.matrix; head = Mw.translation.copy()
        R = Matrix.Rotation(math.radians(deg), 4, axis)
        pb.matrix = mw.inverted() @ (Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ Mw)
    bpy.context.view_layer.update()
    return json.dumps({"posed": len(rots)})

def view_shot(target_name=None, axis='FRONT'):
    """Enquadra + seta solid. (screenshot vem pela bridge --shot)."""
    # forca OBJECT mode (pose mode quebra select_all de objeto)
    act = bpy.context.view_layer.objects.active
    if act and act.mode != 'OBJECT':
        try: bpy.ops.object.mode_set(mode='OBJECT')
        except Exception: pass
    for area in bpy.context.screen.areas:
        if area.type=='VIEW_3D':
            area.spaces[0].shading.type='SOLID'
            region=next((r for r in area.regions if r.type=='WINDOW'),None)
            with bpy.context.temp_override(area=area, region=region):
                bpy.ops.object.select_all(action='DESELECT')
                if target_name and bpy.data.objects.get(target_name):
                    o=bpy.data.objects[target_name]; o.hide_set(False); o.select_set(True)
                    bpy.ops.view3d.view_axis(type=axis); bpy.ops.view3d.view_selected()
                else:
                    bpy.ops.view3d.view_axis(type=axis); bpy.ops.view3d.view_all()
            break
    return json.dumps({"framed":axis})

def clear_pose(arm_name):
    from mathutils import Matrix
    arm=bpy.data.objects.get(arm_name)
    bpy.context.view_layer.objects.active=arm
    if bpy.context.object.mode!='POSE': bpy.ops.object.mode_set(mode='POSE')
    for pb in arm.pose.bones: pb.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()
    bpy.ops.object.mode_set(mode='OBJECT')
    return json.dumps({"pose":"cleared"})

def hem_spread(object_name, zmax_rel=0.15):
    """Mede dispersao do hem da saia (verts baixos) na malha AVALIADA (com deform).
    Retorna xspread/yspread -> detecta estilhaco (spread explode)."""
    deps=bpy.context.evaluated_depsgraph_get()
    obj=bpy.data.objects.get(object_name).evaluated_get(deps)
    me=obj.data; M=obj.matrix_world
    zs=[(M@v.co).z for v in me.vertices]; mn=min(zs); mx=max(zs); h=mx-mn
    xs=[];ys=[];zz=[]
    for v in me.vertices:
        co=M@v.co; zr=(co.z-mn)/h
        if zr<=zmax_rel: xs.append(co.x); ys.append(co.y); zz.append(co.z)
    if not xs: return json.dumps({"err":"sem hem"})
    return json.dumps({"hem_n":len(xs),
        "x":[round(min(xs),3),round(max(xs),3)],
        "y":[round(min(ys),3),round(max(ys),3)],
        "z":[round(min(zz),3),round(max(zz),3)]})

# ---------------------------------------------------------------------------
# TRELLIS-2 NA VISUALIZACAO (o "olho que mede" dentro do viewport)
# Traz a malha MEDIDA do TRELLIS pro live scene como referencia wireframe
# (nao-renderiza, alinhada ao chao, escalada pra metros do build). Eu modelo
# as pecas separadas ALINHADAS a ela em vez de cego. + funcoes de medicao.
# ---------------------------------------------------------------------------

_TRELLIS_DIR = r"D:\Alice\tools\MapVisionBuilder\output\trellis"
_REF_COLL = "TRELLIS_REF"
_REF_TAG = "trellis_ref"

def _trellis_glb(area):
    """Resolve area (num '1'/1/'01' ou nome 'interior'/'vortice') -> caminho .glb.
    Ignora duplicata *_trellis.glb. Retorna (path|None, candidatos)."""
    import os, glob
    files = sorted(glob.glob(os.path.join(_TRELLIS_DIR, "*.glb")))
    files = [f for f in files if not os.path.basename(f).endswith("_trellis.glb")]
    s = str(area).strip().lower()
    if s.isdigit():
        pre = f"{int(s):02d}_"
        for f in files:
            if os.path.basename(f).startswith(pre):
                return f, [os.path.basename(x) for x in files]
    for f in files:
        if s in os.path.basename(f).lower():
            return f, [os.path.basename(x) for x in files]
    return None, [os.path.basename(x) for x in files]

def _ref_objs():
    return [o for o in bpy.data.objects if o.get(_REF_TAG)]

def _world_bbox(objs):
    """Bbox combinado via bound_box (8 cantos) — barato p/ malhas gigantes."""
    import mathutils
    xs=[]; ys=[]; zs=[]
    for o in objs:
        if o.type != 'MESH': continue
        M = o.matrix_world
        for c in o.bound_box:
            w = M @ mathutils.Vector(c)
            xs.append(w.x); ys.append(w.y); zs.append(w.z)
    if not xs: return None
    return (min(xs),max(xs),min(ys),max(ys),min(zs),max(zs))

def clear_trellis_ref():
    """Remove a referencia TRELLIS do scene (objs + collection)."""
    objs = _ref_objs()
    n = len(objs)
    for o in objs:
        try: bpy.data.objects.remove(o, do_unlink=True)
        except Exception: pass
    c = bpy.data.collections.get(_REF_COLL)
    if c:
        try: bpy.data.collections.remove(c)
        except Exception: pass
    return json.dumps({"removidos": n})

def load_trellis_ref(area, fit_x=None, fit_y=None, fit_z=None,
                     center=True, floor=True, rot_z=0.0,
                     wire=True, in_front=False, replace=True, decimate=0.02):
    """Importa o GLB MEDIDO do TRELLIS como REFERENCIA no viewport vivo.
    - area: '1'/1/'interior'/... -> resolve o .glb
    - fit_x|fit_y|fit_z: escala UNIFORME pra que aquele eixo do bbox = N metros
      (preserva proporcao do TRELLIS = verdade). So 1 deve ser dado.
    - center: centraliza XY na origem. floor: poe Z minimo em 0. rot_z: yaw graus.
    - wire: display wireframe (guia nao-intrusiva). in_front: desenha por cima.
    Nao renderiza (hide_render). Retorna MEDIDAS (bbox cru e final em metros)."""
    import os, math, mathutils
    path, cand = _trellis_glb(area)
    if not path:
        return json.dumps({"err": f"area '{area}' nao achada", "candidatos": cand}, ensure_ascii=False)
    if replace:
        clear_trellis_ref()
    if bpy.context.active_object and bpy.context.active_object.mode != 'OBJECT':
        try: bpy.ops.object.mode_set(mode='OBJECT')
        except Exception: pass
    before = set(bpy.data.objects)
    try:
        bpy.ops.import_scene.gltf(filepath=path)
    except Exception as e:
        return json.dumps({"err": f"import falhou: {e}", "path": path}, ensure_ascii=False)
    new = [o for o in bpy.data.objects if o not in before]
    if not new:
        return json.dumps({"err": "import 0 objs", "path": path}, ensure_ascii=False)
    root = bpy.data.objects.new("TRELLIS_REF_ROOT", None)
    bpy.context.scene.collection.objects.link(root)
    root[_REF_TAG] = 1
    for o in new:
        o[_REF_TAG] = 1
        if o.parent is None or o.parent not in new:
            o.parent = root
            o.matrix_parent_inverse = root.matrix_world.inverted()
    bpy.context.view_layer.update()
    raw = _world_bbox(new)
    if not raw:
        return json.dumps({"err": "sem mesh no glb", "path": path}, ensure_ascii=False)
    rx, ry, rz = raw[1]-raw[0], raw[3]-raw[2], raw[5]-raw[4]
    s = 1.0
    if fit_x: s = fit_x/rx if rx else 1.0
    elif fit_y: s = fit_y/ry if ry else 1.0
    elif fit_z: s = fit_z/rz if rz else 1.0
    if rot_z:
        root.rotation_euler[2] = math.radians(rot_z)
    root.scale = (s, s, s)
    bpy.context.view_layer.update()
    bb = _world_bbox(new)
    dx = (bb[0]+bb[1])/2.0; dy = (bb[2]+bb[3])/2.0
    off = mathutils.Vector((0,0,0))
    if center: off.x = -dx; off.y = -dy
    if floor: off.z = -bb[4]
    root.location = (root.location.x+off.x, root.location.y+off.y, root.location.z+off.z)
    bpy.context.view_layer.update()
    fb = _world_bbox(new)
    coll = bpy.data.collections.get(_REF_COLL) or bpy.data.collections.new(_REF_COLL)
    if coll.name not in [c.name for c in bpy.context.scene.collection.children]:
        bpy.context.scene.collection.children.link(coll)
    for o in [root]+new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
        o.hide_render = True
        o.lock_location = (True,True,True); o.lock_rotation=(True,True,True); o.lock_scale=(True,True,True)
        if o.type == 'MESH':
            # decimate p/ wire legivel (1.5M verts viram blob solido). nao destrutivo:
            # slices leem o.data original (full-res) ignorando esse modifier.
            if decimate and 0 < decimate < 1:
                for m in [md for md in o.modifiers if md.type=='DECIMATE']:
                    o.modifiers.remove(m)
                dm = o.modifiers.new("ref_dec", 'DECIMATE')
                dm.decimate_type = 'COLLAPSE'; dm.ratio = float(decimate)
            o.display_type = 'WIRE' if wire else 'SOLID'
            o.show_in_front = bool(in_front)
            o.color = (0.1, 0.9, 1.0, 1.0)
        try: o.select_set(False)
        except Exception: pass
    return json.dumps({
        "loaded": os.path.basename(path), "objs": len(new), "scale": round(s,5),
        "bbox_cru":[round(v,4) for v in raw], "dim_cru":[round(rx,4),round(ry,4),round(rz,4)],
        "bbox_final":[round(v,4) for v in fb],
        "dim_final_m":[round(fb[1]-fb[0],3),round(fb[3]-fb[2],3),round(fb[5]-fb[4],3)],
        "nota":"referencia wireframe nao-renderiza; modele as pecas alinhadas a ela"
    }, ensure_ascii=False)

def trellis_slices(n=8, stride=37, axis='Z'):
    """Mede secoes transversais da REFERENCIA TRELLIS ja carregada: divide o eixo
    em n faixas e reporta extensao X/Y (largura da sala em cada altura) -> casar
    paredes/curvas. stride amostra verts (malha gigante). So apos load_trellis_ref."""
    objs = [o for o in _ref_objs() if o.type=='MESH']
    if not objs:
        return json.dumps({"err":"sem ref TRELLIS carregada (rode load_trellis_ref)"})
    pts=[]
    for o in objs:
        me = o.data; M = o.matrix_world  # full-res original (ignora decimate)
        for i in range(0, len(me.vertices), max(1,stride)):
            pts.append(M @ me.vertices[i].co)
    if not pts:
        return json.dumps({"err":"sem verts"})
    ai = {'X':0,'Y':1,'Z':2}[axis]
    av = [p[ai] for p in pts]; amn=min(av); amx=max(av); h=(amx-amn) or 1e-6
    bands=[]
    for b in range(n):
        lo = amn + h*b/n; hi = amn + h*(b+1)/n
        sx=[p.x for p in pts if lo<=p[ai]<hi]; sy=[p.y for p in pts if lo<=p[ai]<hi]
        if not sx: bands.append({"band":b,"empty":True}); continue
        bands.append({"band":b, axis.lower():[round(lo,3),round(hi,3)],
            "x":[round(min(sx),3),round(max(sx),3),round(max(sx)-min(sx),3)],
            "y":[round(min(sy),3),round(max(sy),3),round(max(sy)-min(sy),3)]})
    return json.dumps({"axis":axis,"samples":len(pts),"bands":bands}, ensure_ascii=False)

def trellis_compare(object_name):
    """Compara bbox da minha peca vs bbox da REFERENCIA TRELLIS -> deltas por eixo
    (quanto minha proporcao desvia da medida)."""
    obj = bpy.data.objects.get(object_name)
    if not obj or obj.type!='MESH':
        return json.dumps({"err":f"'{object_name}' invalido"})
    ref = [o for o in _ref_objs() if o.type=='MESH']
    if not ref:
        return json.dumps({"err":"sem ref TRELLIS carregada"})
    mb = _world_bbox([obj]); rb = _world_bbox(ref)
    md=[mb[1]-mb[0],mb[3]-mb[2],mb[5]-mb[4]]; rd=[rb[1]-rb[0],rb[3]-rb[2],rb[5]-rb[4]]
    return json.dumps({"obj":object_name,
        "dim_obj":[round(v,3) for v in md],"dim_trellis":[round(v,3) for v in rd],
        "delta":[round(md[i]-rd[i],3) for i in range(3)],
        "ratio":[round(md[i]/rd[i],3) if rd[i] else None for i in range(3)]}, ensure_ascii=False)

def segment_dress_mesh(object_name):
    """Injeta vgroups por altura Z relativa: Cintura_Fixacao/Vestido_Corpo/Barra_da_Saia."""
    obj=bpy.data.objects.get(object_name); me=obj.data
    zs=[v.co.z for v in me.vertices]; mn=min(zs); mx=max(zs); h=mx-mn
    groups={"Cintura_Fixacao":[],"Vestido_Corpo":[],"Barra_da_Saia":[]}
    for v in me.vertices:
        zr=(v.co.z-mn)/h
        if 0.70<=zr<=0.82: groups["Cintura_Fixacao"].append(v.index)
        if 0.15<=zr<=0.85: groups["Vestido_Corpo"].append(v.index)
        if zr<0.15: groups["Barra_da_Saia"].append(v.index)
    bpy.context.view_layer.objects.active=obj
    for g,idx in groups.items():
        vg=obj.vertex_groups.get(g) or obj.vertex_groups.new(name=g)
        vg.add(idx,1.0,'ADD')
    return json.dumps({k:len(v) for k,v in groups.items()})
