import bpy, math, random
random.seed(7)
SEG = 96

def loft2(name, sections, mat, solidify=0.0022, hem_drop=0.0, hem_freq=4,
           fold=(0.0,12,0.0,5), axis='Z', cap_end=False):
    a1,f1,a2,f2 = fold
    ph1 = random.uniform(0,6.28); ph2 = random.uniform(0,6.28)
    verts=[]; faces=[]
    n = len(sections)
    for si,(t,cx,cy,rx,ry) in enumerate(sections):
        tt = si/max(n-1,1)
        for i in range(SEG):
            a = 2*math.pi*i/SEG
            folds = 1.0 + tt*(a1*math.sin(f1*a+ph1)+a2*math.sin(f2*a+ph2))
            zz = t
            if hem_drop and si==n-1:
                zz = t - hem_drop*abs(math.sin(hem_freq*a+ph1))
            if axis=='Z': verts.append((cx+rx*folds*math.cos(a), cy+ry*folds*math.sin(a), zz))
            else: verts.append((zz, cy+rx*folds*math.cos(a), cx+ry*folds*math.sin(a)))
    for s in range(n-1):
        for i in range(SEG):
            j=(i+1)%SEG
            faces.append((s*SEG+i, s*SEG+j, (s+1)*SEG+j, (s+1)*SEG+i))
    if cap_end:
        base = (n-1)*SEG
        verts.append(tuple(sum(c)/SEG for c in zip(*[verts[base+i] for i in range(SEG)])))
        ci = len(verts)-1
        for i in range(SEG):
            faces.append((base+i, base+(i+1)%SEG, ci))
    me = bpy.data.meshes.new(name+'_Mesh')
    me.from_pydata(verts,[],faces); me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    if solidify:
        s = ob.modifiers.new('Sol','SOLIDIFY'); s.thickness=solidify; s.offset=1.0
    bpy.context.view_layer.objects.active = ob
    for o in bpy.data.objects: o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.shade_smooth()
    return ob

m_teal = bpy.data.materials['MAT_TealDamask']
m_leather = bpy.data.materials['MAT_LeatherP']
m_hair = bpy.data.materials['MAT_HairP']
rig = bpy.data.objects['AliceRig']

# ===== A. SAIA: faixa cream FINA (ref) =====
for nm, lift in [('GD_Saia_Lace', 0.055), ('GD_Saia_Cream', 0.035)]:
    ob = bpy.data.objects.get(nm)
    if ob:
        zs = [v.co.z for v in ob.data.vertices]
        zmin = min(zs)
        for v in ob.data.vertices:
            # levantar so a parte baixa (comprimir hem pra cima)
            d = v.co.z - zmin
            if d < 0.12: v.co.z += lift * (1 - d/0.12)
        ob.data.update()

# ===== B. BOTAS rebuild (raio real perna: rx0.092 ry0.10 cy0.035) =====
for S, g in [('L',1),('R',-1)]:
    for nm in [f'GD_Bota_Cano_{S}']:
        o = bpy.data.objects.get(nm)
        if o: bpy.data.objects.remove(o, do_unlink=True)
    cano = loft2(f'GD_Bota_Cano_{S}', [
        (0.42, g*0.098, 0.040, 0.085, 0.092),
        (0.30, g*0.100, 0.042, 0.080, 0.088),
        (0.16, g*0.101, 0.042, 0.078, 0.086),
        (0.06, g*0.101, 0.040, 0.080, 0.090),
    ], m_leather, 0.004)
    pe = bpy.data.objects.get(f'GD_Bota_Pe_{S}')
    if pe:
        pe.scale = (0.075, 0.13, 0.045)
        pe.location = (g*0.101, -0.045, 0.035)
    sl = bpy.data.objects.get(f'GD_Salto_{S}')
    if sl:
        sl.scale = (1.4, 1.4, 1.2)
    # rig cano: Shin
    cano.vertex_groups.clear()
    vg = cano.vertex_groups.new(name=f'Shin_{S}')
    vg.add([v.index for v in cano.data.vertices], 1.0, 'REPLACE')
    am = cano.modifiers.new('Armature','ARMATURE'); am.object = rig
    cano.parent = rig

# ===== C. MANGAS rebuild: puff pequeno FECHADO (cap) =====
for S, g in [('L',1),('R',-1)]:
    o = bpy.data.objects.get(f'GD_Manga_{S}')
    if o: bpy.data.objects.remove(o, do_unlink=True)
    manga = loft2(f'GD_Manga_{S}', [
        (g*0.150, 1.375, 0.0, 0.052, 0.052),
        (g*0.190, 1.378, 0.0, 0.068, 0.068),
        (g*0.230, 1.376, 0.0, 0.062, 0.062),
        (g*0.255, 1.374, 0.0, 0.040, 0.040),
    ], m_teal, 0.0022, fold=(0.04,9,0.018,4), axis='X', cap_end=True)
    sb = manga.modifiers.new('Subd','SUBSURF'); sb.levels=1; sb.render_levels=2
    manga.vertex_groups.clear()
    vg = manga.vertex_groups.new(name=f'UpperArm_{S}')
    vg.add([v.index for v in manga.data.vertices], 1.0, 'REPLACE')
    am = manga.modifiers.new('Armature','ARMATURE'); am.object = rig
    manga.parent = rig

# ===== D. CABELO: ondas no Y + massa larga side =====
hm = bpy.data.objects.get('GD_Cabelo_Massa')
if hm:
    for v in hm.data.vertices:
        v.co.y += 0.014*math.sin(7*v.co.z*3.2 + 1.1)
        v.co.y = 0.095 + (v.co.y-0.095)*1.20
    hm.data.update()
for S, g in [('L',1),('R',-1)]:
    mc = bpy.data.objects.get(f'GD_Mecha_{S}')
    if mc:
        for v in mc.data.vertices:
            v.co.x = g*0.088 + (v.co.x-g*0.088)*1.5
            v.co.y += 0.008*math.sin(11*v.co.z*3.0)
        mc.data.update()

# ===== E. CORPETE subsurf suaviza =====
cp = bpy.data.objects.get('GD_Corpete')
if cp and not any(m.type=='SUBSURF' for m in cp.modifiers):
    sb = cp.modifiers.new('Subd','SUBSURF'); sb.levels=1; sb.render_levels=2

bpy.ops.wm.save_mainfile()
print('CICLO 2 OK')
