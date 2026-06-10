import bpy, math, random
random.seed(99)
rig = bpy.data.objects['Skeleton']
SEG = 128  # alta resolucao radial pra franzidos finos

# ===== limpar saia antiga =====
for o in list(bpy.data.objects):
    if o.name in ('P_Saia_Renda','P_Saia_Cream','P_Sobressaia','P_PainelV'):
        bpy.data.objects.remove(o, do_unlink=True)
for d in list(bpy.data.meshes):
    if d.users == 0: bpy.data.meshes.remove(d)

m_dam   = bpy.data.materials['MAT_Damask3']
m_dia   = bpy.data.materials['MAT_Diamond3']
m_lace  = bpy.data.materials['MAT_LaceHem3']
m_gold  = bpy.data.materials['MAT_Gold3']
m_frill = bpy.data.materials.get('MAT_Frill3')

def organic_hem(a, base, a1, f1, a2, f2, ph1, ph2, jit):
    """queda de hem organica: 2 freqs + jitter por seed do angulo"""
    h = a1*abs(math.sin(f1*a + ph1)) + a2*abs(math.sin(f2*a + ph2))
    random.seed(int(a*57.29)*7 + jit)
    return base + h + random.uniform(0, a1*0.35)

def layer(name, secs, mat, solidify=0.0018, arc=None,
          hem=(0.0, 4, 0.0, 9), ruffle=(0.0, 0), trim_mat=None, trim_r=0.004):
    """secs: [(z, cy, rx, ry)]. hem=(amp1,freq1,amp2,freq2) organico na ultima secao.
    ruffle=(amp,freq): franzido radial crescente pra baixo (linhas verticais).
    trim_mat: cria cordao seguindo o hem."""
    ha1, hf1, ha2, hf2 = hem
    ra, rf = ruffle
    ph1, ph2 = random.uniform(0,6.28), random.uniform(0,6.28)
    jit = random.randint(0,9999)
    closed = arc is None
    n = len(secs)
    verts=[]; faces=[]
    hem_pts = []
    for si,(z,cy,rx,ry) in enumerate(secs):
        tt = si/max(n-1,1)
        for i in range(SEG):
            if closed:
                a = 2*math.pi*i/SEG
            else:
                a0,a1d = math.radians(arc[0]), math.radians(arc[1])
                a = a0 + (a1d-a0)*i/(SEG-1)
            f = 1.0 + tt*ra*math.sin(rf*a + ph1)
            zz = z
            if si == n-1:
                drop = organic_hem(a, 0.0, ha1, hf1, ha2, hf2, ph1, ph2, jit)
                zz = z - drop
            x = rx*f*math.sin(a)
            y = cy - ry*f*math.cos(a)
            verts.append((x, y, zz))
            if si == n-1:
                hem_pts.append((x, y, zz))
    for s in range(n-1):
        rng = SEG if closed else SEG-1
        for i in range(rng):
            j = (i+1) % SEG
            faces.append((s*SEG+i, s*SEG+j, (s+1)*SEG+j, (s+1)*SEG+i))
    me = bpy.data.meshes.new(name+'_Me'); me.from_pydata(verts,[],faces); me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    if solidify:
        s = ob.modifiers.new('Sol','SOLIDIFY'); s.thickness = solidify; s.offset = 1.0
    bpy.context.view_layer.objects.active = ob
    for o in bpy.data.objects: o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.shade_smooth()
    # trim cordao no hem
    if trim_mat and hem_pts:
        tv=[]; tf=[]
        m2 = len(hem_pts)
        for k,(x,y,z) in enumerate(hem_pts):
            for q in range(6):
                aa = 2*math.pi*q/6
                tv.append((x + trim_r*math.cos(aa)*0.7, y + trim_r*math.sin(aa)*0.7, z + trim_r*math.sin(aa)*0.7))
        lim = m2 if closed else m2-1
        for k in range(lim):
            k2 = (k+1) % m2
            for q in range(6):
                q2 = (q+1) % 6
                tf.append((k*6+q, k*6+q2, k2*6+q2, k2*6+q))
        tme = bpy.data.meshes.new(name+'_Trim_Me'); tme.from_pydata(tv,[],tf); tme.update()
        tob = bpy.data.objects.new(name+'_Trim', tme)
        bpy.context.scene.collection.objects.link(tob)
        tob.data.materials.append(trim_mat)
        bpy.context.view_layer.objects.active = tob
        for o in bpy.data.objects: o.select_set(False)
        tob.select_set(True)
        bpy.ops.object.shade_smooth()
        rig_prox(tob, SKIRT_BONES, 2)
    return ob

def rig_prox(ob, allowed, k=3):
    segs = []
    for b in rig.data.bones:
        if b.name in allowed and b.use_deform:
            h = rig.matrix_world @ b.head_local
            t = rig.matrix_world @ b.tail_local
            segs.append((b.name, h, t, (t-h), max((t-h).length_squared,1e-12)))
    ob.vertex_groups.clear(); vgs = {}
    mw = ob.matrix_world
    for v in ob.data.vertices:
        p = mw @ v.co
        ds = []
        for n,h,t,ab,L2 in segs:
            tt = max(0.0,min(1.0,(p-h).dot(ab)/L2))
            ds.append(((p-(h+ab*tt)).length, n))
        ds.sort()
        ws = [(1.0/max(d,1e-5)**2,n) for d,n in ds[:k]]
        s = sum(w for w,_ in ws)
        for w,n in ws:
            if n not in vgs: vgs[n] = ob.vertex_groups.new(name=n)
            vgs[n].add([v.index], w/s, 'REPLACE')
    am = ob.modifiers.new('Armature','ARMATURE'); am.object = rig
    bpy.context.view_layer.update()
    mw0 = ob.matrix_world.copy()
    ob.parent = rig; ob.matrix_world = mw0

SKIRT_BONES = {'Hips','Spine1'} | {f'Skirt{i}_{kk}' for i in range(8) for kk in (1,2)} | {'Butt_L','Butt_R'}

# ===== 6 CAMADAS (ref zoom, de dentro pra fora) =====
# L6 RENDA final (mais longa, scallops finos, ate o joelho z~0.50)
L6 = layer('P_Saia_Renda', [
    (1.025, 0.018, 0.148, 0.133),
    (0.86, 0.026, 0.235, 0.215),
    (0.66, 0.030, 0.320, 0.295),
    (0.545, 0.032, 0.360, 0.335),
], m_lace, 0.0012, hem=(0.030, 9, 0.018, 23), ruffle=(0.030, 22))
rig_prox(L6, SKIRT_BONES, 3)

# L5 BABADO franzido 1 (cream, tier horizontal, franzido FORTE = linhas verticais)
L5 = layer('P_Babado1', [
    (0.760, 0.030, 0.290, 0.268),
    (0.640, 0.031, 0.325, 0.300),
], m_frill, 0.0014, hem=(0.020, 12, 0.010, 28), ruffle=(0.060, 30), trim_mat=m_gold, trim_r=0.003)
rig_prox(L5, SKIRT_BONES, 3)

# L4 BABADO franzido 2 (bege, acima do 1)
L4 = layer('P_Babado2', [
    (0.840, 0.028, 0.262, 0.242),
    (0.730, 0.030, 0.298, 0.275),
], m_lace, 0.0014, hem=(0.018, 14, 0.008, 30), ruffle=(0.055, 26))
rig_prox(L4, SKIRT_BONES, 3)

# L3 CREAM diamond + cartas (painel medio)
L3 = layer('P_Saia_Cream', [
    (1.030, 0.018, 0.152, 0.137),
    (0.90, 0.026, 0.225, 0.205),
    (0.76, 0.030, 0.285, 0.262),
    (0.665, 0.032, 0.318, 0.292),
], m_dia, 0.0016, hem=(0.040, 5, 0.022, 11), ruffle=(0.020, 14))
rig_prox(L3, SKIRT_BONES, 3)

# L2 VERDE handkerchief media (pontas organicas + trim cream)
L2 = layer('P_Saia_Verde2', [
    (1.035, 0.018, 0.156, 0.141),
    (0.92, 0.026, 0.220, 0.200),
    (0.80, 0.031, 0.272, 0.250),
    (0.715, 0.033, 0.300, 0.276),
], m_dam, 0.0020, hem=(0.062, 4, 0.028, 9), ruffle=(0.026, 11),
    trim_mat=bpy.data.materials['MAT_Frill3'], trim_r=0.0035)
rig_prox(L2, SKIRT_BONES, 3)

# L1 SOBRESSAIA verde aberta na frente (trim claro nas bordas) + V atras
L1 = layer('P_Sobressaia', [
    (1.040, 0.018, 0.160, 0.145),
    (0.93, 0.027, 0.222, 0.203),
    (0.82, 0.033, 0.268, 0.246),
    (0.745, 0.036, 0.292, 0.268),
], m_dam, 0.0024, arc=(40, 320), hem=(0.050, 3, 0.024, 7), ruffle=(0.030, 9),
    trim_mat=bpy.data.materials['MAT_Frill3'], trim_r=0.004)
rig_prox(L1, SKIRT_BONES, 3)

# ===== LINHAS DE COSTURA no corpete (princess seams) + lacing fino =====
m_seam = bpy.data.materials.get('MAT_Seam3')
if not m_seam:
    m_seam = bpy.data.materials.new('MAT_Seam3'); m_seam.use_nodes = True
    sb = m_seam.node_tree.nodes.get('Principled BSDF')
    sb.inputs['Base Color'].default_value = (0.010, 0.022, 0.015, 1)
    sb.inputs['Roughness'].default_value = 0.9

def cord(name, pts, r, mat, bone):
    tv=[]; tf=[]
    n2 = len(pts)
    for k,(x,y,z) in enumerate(pts):
        for q in range(6):
            aa = 2*math.pi*q/6
            tv.append((x+r*math.cos(aa), y+r*math.sin(aa)*0.5, z+r*math.sin(aa)))
    for k in range(n2-1):
        for q in range(6):
            q2=(q+1)%6
            tf.append((k*6+q, k*6+q2, (k+1)*6+q2, (k+1)*6+q))
    me = bpy.data.meshes.new(name+'_Me'); me.from_pydata(tv,[],tf); me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    bpy.context.view_layer.objects.active = ob
    for o in bpy.data.objects: o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.shade_smooth()
    ob.vertex_groups.clear()
    vg = ob.vertex_groups.new(name=bone)
    vg.add([v.index for v in ob.data.vertices], 1.0, 'REPLACE')
    am = ob.modifiers.new('Armature','ARMATURE'); am.object = rig
    bpy.context.view_layer.update()
    mw0 = ob.matrix_world.copy(); ob.parent = rig; ob.matrix_world = mw0

# princess seams: 4 linhas verticais frente/lados do corpete
corp = bpy.data.objects['P_Corpete']
for sx, nmx in [(-0.062,'L1'),(-0.025,'L2'),(0.025,'R2'),(0.062,'R1')]:
    pts = []
    for k in range(10):
        z = 1.05 + k*(1.33-1.05)/9
        # raio frontal do corpete na altura z (aprox interp das secs)
        t = (1.33 - z)/(1.33-1.04)
        ry = 0.118 + (0.105-0.118)*abs(0.5-t)*2
        cy = -0.012 if z>1.2 else 0.008
        y = cy - math.sqrt(max(ry*ry - sx*sx, 1e-6)) * 1.42  # frente expandida
        pts.append((sx, y*0.92, z))
    cord(f'P_Seam_{nmx}', pts, 0.0016, m_seam, 'Spine2')

# lacing mais fino
for o in bpy.data.objects:
    if o.name.startswith('P_CorpLace_'):
        o.scale = (0.78, 0.78, 1.0)

# mangas: franzido real (subdivide nao da; aplicar displacement senoidal nos verts)
for S in ['L','R']:
    mg = bpy.data.objects.get(f'P_Manga_{S}')
    if mg:
        for v in mg.data.vertices:
            ang = math.atan2(v.co.z - 1.376, v.co.y - 0.018)
            v.co.y += 0.0045*math.sin(14*ang)
            v.co.z += 0.0045*math.cos(14*ang)*0.5
        mg.data.update()

# meias: listras mais finas e suaves
mstr = bpy.data.materials.get('MAT_Stripes3')
if mstr:
    mm = next((n for n in mstr.node_tree.nodes if n.type=='MATH' and n.operation=='MULTIPLY'), None)
    if mm: mm.inputs[1].default_value = 200.0
    rp = next((n for n in mstr.node_tree.nodes if n.type=='VALTORGB'), None)
    if rp: rp.color_ramp.elements[1].color = (0.34,0.31,0.26,1)

bpy.ops.wm.save_mainfile()
print('SAIA PRO 6 CAMADAS + SEAMS OK')
