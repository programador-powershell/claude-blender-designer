import bpy, math, random
random.seed(42)
rig = bpy.data.objects['HRig']
H = 1.70
SEG = 96
SW = r'D:/Alice/tools/auto-rig-fix/work/swatches/'

# colecao outfit (troca de roupa = excluir/incluir colecao)
oc = bpy.data.collections.get('Outfit_Chapeleiro')
if not oc:
    oc = bpy.data.collections.new('Outfit_Chapeleiro')
    bpy.context.scene.collection.children.link(oc)

def addc(ob):
    for c in ob.users_collection:
        c.objects.unlink(ob)
    oc.objects.link(ob)
    return ob

def swatch_mat(name, img_file, scale=8.0, rough=0.75, boost=1.7):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get('Principled BSDF')
    img = bpy.data.images.load(SW + img_file, check_existing=True)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (scale, scale, scale)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    it = nt.nodes.new('ShaderNodeTexImage')
    it.image = img; it.projection = 'BOX'; it.projection_blend = 0.25
    nt.links.new(mp.outputs['Vector'], it.inputs['Vector'])
    hsv = nt.nodes.new('ShaderNodeHueSaturation')
    hsv.inputs['Value'].default_value = boost
    hsv.inputs['Saturation'].default_value = 1.1
    nt.links.new(it.outputs['Color'], hsv.inputs['Color'])
    nt.links.new(hsv.outputs['Color'], b.inputs['Base Color'])
    bw = nt.nodes.new('ShaderNodeRGBToBW')
    nt.links.new(it.outputs['Color'], bw.inputs['Color'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.25
    nt.links.new(bw.outputs['Val'], bp.inputs['Height'])
    nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = rough
    try: b.inputs['Sheen Weight'].default_value = 0.45
    except KeyError: pass
    return m

m_dam = swatch_mat('MO_Damask', 'S08_verde_losango_tile.png', 7.0)
m_cream = swatch_mat('MO_Cream', 'S02_cream_rosas_tile.png', 9.0, 0.8, 2.0)
m_lace = swatch_mat('MO_LaceG', 'S06_renda_dourada_tile.png', 10.0, 0.85, 1.6)
m_black = swatch_mat('MO_BlackL', 'S04_preto_rosas_tile.png', 9.0, 0.85, 1.5)
def plain(name, color, rough=0.6, metal=0.0):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    return m
m_leather = plain('MO_Leather', (0.020, 0.016, 0.014), 0.40)
m_gold = plain('MO_Gold', (0.55, 0.40, 0.14), 0.32, 1.0)
m_str = bpy.data.materials.get('MO_Stripes')
if not m_str:
    m_str = bpy.data.materials.new('MO_Stripes'); m_str.use_nodes = True
    nt = m_str.node_tree
    b = nt.nodes.get('Principled BSDF')
    b.inputs['Roughness'].default_value = 0.82
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(geo.outputs['Position'], sep.inputs['Vector'])
    mm = nt.nodes.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; mm.inputs[1].default_value = 200.0
    nt.links.new(sep.outputs['Z'], mm.inputs[0])
    sn = nt.nodes.new('ShaderNodeMath'); sn.operation = 'SINE'
    nt.links.new(mm.outputs[0], sn.inputs[0])
    gt = nt.nodes.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.0
    nt.links.new(sn.outputs[0], gt.inputs[0])
    rp = nt.nodes.new('ShaderNodeValToRGB')
    rp.color_ramp.elements[0].color = (0.022, 0.020, 0.018, 1)
    rp.color_ramp.elements[1].color = (0.36, 0.33, 0.27, 1)
    nt.links.new(gt.outputs[0], rp.inputs['Fac'])
    nt.links.new(rp.outputs['Color'], b.inputs['Base Color'])

def loft(name, secs, mat, solidify=0.0018, arc=None, hem=(0,4,0,9), ruffle=(0,0)):
    ha1, hf1, ha2, hf2 = hem
    ra, rf = ruffle
    ph = random.uniform(0, 6.28)
    closed = arc is None
    n = len(secs)
    verts = []; faces = []
    for si, (z, cy, rx, ry) in enumerate(secs):
        tt = si / max(n-1, 1)
        for i in range(SEG):
            a = 2*math.pi*i/SEG if closed else math.radians(arc[0]) + (math.radians(arc[1])-math.radians(arc[0]))*i/(SEG-1)
            f = 1.0 + tt*ra*math.sin(rf*a + ph)
            zz = z
            if si == n-1 and ha1:
                zz = z - (ha1*abs(math.sin(hf1*a+ph)) + ha2*abs(math.sin(hf2*a+ph*1.7)))
            verts.append((rx*f*math.sin(a), cy - ry*f*math.cos(a), zz))
    for s in range(n-1):
        rng = SEG if closed else SEG-1
        for i in range(rng):
            j = (i+1) % SEG
            faces.append((s*SEG+i, s*SEG+j, (s+1)*SEG+j, (s+1)*SEG+i))
    me = bpy.data.meshes.new(name+'_Me')
    me.from_pydata(verts, [], faces); me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    if solidify:
        s = ob.modifiers.new('Sol','SOLIDIFY'); s.thickness = solidify; s.offset = 1.0
    bpy.context.view_layer.objects.active = ob
    for o in bpy.data.objects: o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.shade_smooth()
    return addc(ob)

def rig_prox(ob, allowed, k=3):
    segs = []
    for b in rig.data.bones:
        if b.name in allowed and b.use_deform:
            h = rig.matrix_world @ b.head_local
            t = rig.matrix_world @ b.tail_local
            segs.append((b.name, h, t, (t-h), max((t-h).length_squared, 1e-12)))
    ob.vertex_groups.clear(); vgs = {}
    mw = ob.matrix_world
    for v in ob.data.vertices:
        p = mw @ v.co
        ds = []
        for n, h, t, ab, L2 in segs:
            tt = max(0.0, min(1.0, (p-h).dot(ab)/L2))
            ds.append(((p-(h+ab*tt)).length, n))
        ds.sort()
        ws = [(1.0/max(d,1e-5)**2, n) for d, n in ds[:k]]
        s = sum(w for w,_ in ws)
        for w, n in ws:
            if n not in vgs: vgs[n] = ob.vertex_groups.new(name=n)
            vgs[n].add([v.index], w/s, 'REPLACE')
    am = ob.modifiers.new('Armature','ARMATURE'); am.object = rig
    bpy.context.view_layer.update()
    mw0 = ob.matrix_world.copy()
    ob.parent = rig; ob.matrix_world = mw0

SKIRT = {'Hips','Spine1'} | {f'Skirt{i}_{k}' for i in range(8) for k in (1,2)} | {'Butt_L','Butt_R'}

# === MEIAS (perna nova: cx 0.094-0.112) ===
for S, g in [('L',1),('R',-1)]:
    mei = loft(f'O_Meia_{S}', [
        (0.660, 0.012, 0.062, 0.060),
        (0.510, 0.010, 0.054, 0.054),
        (0.360, 0.022, 0.048, 0.050),
        (0.200, 0.032, 0.042, 0.046),
        (0.130, 0.036, 0.042, 0.048),
    ], m_str, 0.0013)
    for v in mei.data.vertices:
        v.co.x += g*0.100
    mei.data.update()
    rig_prox(mei, {f'Thigh_{S}', f'ThighTwist_{S}', f'Shin_{S}', f'ShinTwist_{S}'}, 2)

# === BOTAS (cano+cadarcos+sola+salto) ===
def rig_single(ob, bone):
    ob.vertex_groups.clear()
    vg = ob.vertex_groups.new(name=bone)
    vg.add([v.index for v in ob.data.vertices], 1.0, 'REPLACE')
    am = ob.modifiers.new('Armature','ARMATURE'); am.object = rig
    bpy.context.view_layer.update()
    mw0 = ob.matrix_world.copy()
    ob.parent = rig; ob.matrix_world = mw0

for S, g in [('L',1),('R',-1)]:
    cano = loft(f'O_Bota_{S}', [
        (0.440, 0.030, 0.070, 0.075),
        (0.300, 0.034, 0.062, 0.068),
        (0.150, 0.038, 0.056, 0.062),
        (0.070, 0.036, 0.058, 0.066),
    ], m_leather, 0.0032)
    for v in cano.data.vertices: v.co.x += g*0.105
    cano.data.update()
    rig_single(cano, f'Shin_{S}')
    bpy.ops.mesh.primitive_cube_add(size=1, location=(g*0.105, -0.040, 0.052))
    pe = bpy.context.object; pe.name = f'O_BotaPe_{S}'
    pe.scale = (0.135, 0.27, 0.075)
    pe.data.materials.append(m_leather)
    bpy.ops.object.shade_smooth()
    bv = pe.modifiers.new('Bev','BEVEL'); bv.width = 0.015; bv.segments = 3
    addc(pe); rig_single(pe, f'Foot_{S}')
    bpy.ops.mesh.primitive_cube_add(size=1, location=(g*0.105, -0.040, 0.014))
    so = bpy.context.object; so.name = f'O_BotaSola_{S}'
    so.scale = (0.145, 0.29, 0.030)
    so.data.materials.append(m_leather)
    addc(so); rig_single(so, f'Foot_{S}')
    bpy.ops.mesh.primitive_cube_add(size=1, location=(g*0.105, 0.058, 0.030))
    sa = bpy.context.object; sa.name = f'O_BotaSalto_{S}'
    sa.scale = (0.095, 0.080, 0.060)
    sa.data.materials.append(m_leather)
    addc(sa); rig_single(sa, f'Foot_{S}')
    for k in range(7):
        z = 0.095 + k*0.046
        for ang in (20, -20):
            bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.0028, depth=0.075,
                location=(g*0.105, -0.058 - (0.004 if z > 0.28 else 0), z),
                rotation=(0, math.radians(90-ang), 0))
            c = bpy.context.object; c.name = f'O_Lace_{S}_{k}_{ang}'
            c.data.materials.append(m_leather)
            addc(c); rig_single(c, f'Shin_{S}')

# === ANAGUA PRETA 5 TIERS (renda) ===
for ti in range(5):
    z0 = 1.000 - ti*0.085
    z1 = z0 - 0.105
    r0 = 0.135 + ti*0.038
    r1 = r0 + 0.052
    t_ = loft(f'O_Anagua_T{ti}', [
        (z0, 0.018, r0, r0*0.92),
        (z1, 0.022, r1, r1*0.92),
    ], m_black, 0.0012, hem=(0.022, 11, 0.012, 27), ruffle=(0.05, 24))
    rig_prox(t_, SKIRT, 3)

# === SAIA CREAM + SOBRESSAIA ===
s_cream = loft('O_SaiaCream', [
    (1.005, 0.016, 0.130, 0.120),
    (0.880, 0.022, 0.200, 0.185),
    (0.740, 0.026, 0.262, 0.242),
    (0.640, 0.028, 0.295, 0.272),
], m_cream, 0.0016, hem=(0.038, 5, 0.020, 11), ruffle=(0.02, 14))
rig_prox(s_cream, SKIRT, 3)
s_over = loft('O_Sobressaia', [
    (1.010, 0.016, 0.135, 0.124),
    (0.900, 0.024, 0.205, 0.188),
    (0.790, 0.030, 0.255, 0.235),
    (0.715, 0.033, 0.280, 0.258),
], m_dam, 0.0022, arc=(40, 320), hem=(0.050, 3, 0.024, 7), ruffle=(0.028, 9))
rig_prox(s_over, SKIRT, 3)

# === CORPETE (cintura nova z 1.10 hw 0.105, busto z 1.27) ===
corp = loft('O_Corpete', [
    (1.330, -0.006, 0.105, 0.125),
    (1.255, -0.010, 0.102, 0.130),
    (1.150, 0.002, 0.092, 0.098),
    (1.065, 0.006, 0.098, 0.095),
    (1.010, 0.012, 0.118, 0.112),
], m_dam, 0.0026)
rig_prox(corp, {'Spine1','Spine2','Spine3','Hips'}, 2)
trim = loft('O_TrimBusto', [(1.336, -0.006, 0.107, 0.127), (1.323, -0.007, 0.108, 0.128)], m_gold, 0.003)
rig_prox(trim, {'Spine3'}, 1)
for k in range(6):
    z = 1.075 + k*0.042
    yf = -0.128 if z > 1.18 else -0.105
    for ang in (25, -25):
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.0026, depth=0.070,
            location=(0, yf, z), rotation=(0, math.radians(90-ang), 0))
        c = bpy.context.object; c.name = f'O_Lacing_{k}_{ang}'
        c.data.materials.append(m_gold)
        addc(c); rig_single(c, 'Spine2' if z > 1.15 else 'Spine1')

# === MANGAS PUFF + LUVAS RENDA ===
import mathutils
def loft_arm(name, secs, mat, solidify=0.002, fold=(0,1), cap=True):
    fa, ff = fold
    ph = random.uniform(0, 6.28)
    verts = []; faces = []
    n = len(secs)
    for si, (x, cz, r) in enumerate(secs):
        tt = si / max(n-1, 1)
        for i in range(SEG//4):
            a = 2*math.pi*i/(SEG//4)
            f = 1.0 + fa*math.sin(ff*a + ph)
            verts.append((x, 0.012 + r*f*math.cos(a), cz + r*f*math.sin(a)))
    ns = SEG//4
    for s in range(n-1):
        for i in range(ns):
            j = (i+1) % ns
            faces.append((s*ns+i, s*ns+j, (s+1)*ns+j, (s+1)*ns+i))
    if cap:
        base = (n-1)*ns
        verts.append((secs[-1][0], 0.012, secs[-1][1]))
        ci = len(verts)-1
        for i in range(ns):
            faces.append((base+i, base+(i+1)%ns, ci))
    me = bpy.data.meshes.new(name+'_Me')
    me.from_pydata(verts, [], faces); me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    if solidify:
        s = ob.modifiers.new('Sol','SOLIDIFY'); s.thickness = solidify; s.offset = 1.0
    bpy.context.view_layer.objects.active = ob
    for o in bpy.data.objects: o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.shade_smooth()
    return addc(ob)

def armz(x): return 1.400 - 0.345*(x-0.150)
for S, g in [('L',1),('R',-1)]:
    mg = loft_arm(f'O_Manga_{S}', [
        (g*0.160, armz(0.160)+0.010, 0.048),
        (g*0.195, armz(0.195)+0.014, 0.068),
        (g*0.235, armz(0.235)+0.006, 0.060),
        (g*0.262, armz(0.262), 0.036),
    ], m_dam, 0.002, fold=(0.05, 9))
    sb = mg.modifiers.new('Sub','SUBSURF'); sb.levels = 1; sb.render_levels = 2
    rig_prox(mg, {f'UpperArm_{S}', f'Clavicle_{S}'}, 1)
    fr = loft_arm(f'O_Frill_{S}', [
        (g*0.258, armz(0.258), 0.040),
        (g*0.276, armz(0.276)-0.003, 0.046),
    ], m_lace, 0.0012, fold=(0.16, 12), cap=False)
    rig_prox(fr, {f'UpperArm_{S}'}, 1)
    lv = loft_arm(f'O_Luva_{S}', [
        (g*0.370, armz(0.370)+0.001, 0.036),
        (g*0.430, armz(0.430), 0.032),
        (g*0.490, armz(0.490), 0.030),
    ], m_black, 0.0016, cap=False)
    rig_prox(lv, {f'ForeArm_{S}', f'ForeArmTwist_{S}', f'Hand_{S}'}, 2)

# === BOW costas + chapeu ===
for S, g in [('L',1),('R',-1)]:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, radius=1.0, location=(g*0.095, 0.155, 1.020))
    lp = bpy.context.object; lp.name = f'O_BowLoop_{S}'
    lp.scale = (0.095, 0.045, 0.068)
    lp.data.materials.append(m_dam)
    bpy.ops.object.shade_smooth()
    bpy.context.view_layer.update()
    addc(lp); rig_single(lp, f'Bow{S}')
bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.030, depth=0.012,
    location=(0, 0.148, 1.020), rotation=(math.radians(90), 0, 0))
bw = bpy.context.object; bw.name = 'O_BowWatch'
bw.data.materials.append(m_gold)
addc(bw); rig_single(bw, 'BowKnot')
hat_rot = (0, math.radians(-12), 0)
bpy.ops.mesh.primitive_cylinder_add(vertices=36, radius=0.062, depth=0.105,
    location=(0.050, 0.0, 1.748), rotation=hat_rot)
copa = bpy.context.object; copa.name = 'O_ChapeuCopa'
copa.data.materials.append(m_dam)
addc(copa); rig_single(copa, 'HatBase')
bpy.ops.mesh.primitive_cylinder_add(vertices=36, radius=0.098, depth=0.007,
    location=(0.040, 0.0, 1.697), rotation=hat_rot)
aba = bpy.context.object; aba.name = 'O_ChapeuAba'
aba.data.materials.append(m_dam)
addc(aba); rig_single(aba, 'HatBase')
bpy.ops.mesh.primitive_cylinder_add(vertices=36, radius=0.064, depth=0.020,
    location=(0.043, 0.0, 1.710), rotation=hat_rot)
bd = bpy.context.object; bd.name = 'O_ChapeuBanda'
bd.data.materials.append(m_gold)
addc(bd); rig_single(bd, 'HatBase')

# cabelo basico (calota + mechas) — outfit-independent, vai em colecao propria
hc = bpy.data.collections.get('Cabelo')
if not hc:
    hc = bpy.data.collections.new('Cabelo')
    bpy.context.scene.collection.children.link(hc)
m_hair = bpy.data.materials.get('MAT_HHair')
bpy.ops.mesh.primitive_uv_sphere_add(segments=28, ring_count=14, radius=0.098, location=(0, 0.008, 1.575))
cal = bpy.context.object; cal.name = 'C_Calota'
cal.scale = (1.02, 1.12, 1.06)
cal.data.materials.append(m_hair)
bpy.ops.object.shade_smooth()
for c in cal.users_collection: c.objects.unlink(cal)
hc.objects.link(cal)
cal.vertex_groups.clear()
vg = cal.vertex_groups.new(name='Head')
vg.add([v.index for v in cal.data.vertices], 1.0, 'REPLACE')
am = cal.modifiers.new('Armature','ARMATURE'); am.object = rig
bpy.context.view_layer.update()
mw0 = cal.matrix_world.copy(); cal.parent = rig; cal.matrix_world = mw0
SEGm = 10
def mecha(name, x0, y0, z0, L, r0, wav, chain):
    pts = []
    n = 12
    ph = random.uniform(0, 6.28)
    for k in range(n):
        t = k/(n-1)
        pts.append((x0 + wav*math.sin(6*t*3.14+ph)*t + x0*0.4*t,
                    min(y0 + 0.028*t, 0.135), z0 - L*t))
    verts = []; faces = []
    for k, (px, py, pz) in enumerate(pts):
        r = r0*(1 - 0.5*k/(n-1))
        for i in range(SEGm):
            a = 2*math.pi*i/SEGm
            verts.append((px+r*math.cos(a), py+r*math.sin(a), pz))
    for s in range(n-1):
        for i in range(SEGm):
            j = (i+1) % SEGm
            faces.append((s*SEGm+i, s*SEGm+j, (s+1)*SEGm+j, (s+1)*SEGm+i))
    me = bpy.data.meshes.new(name+'_Me')
    me.from_pydata(verts, [], faces); me.update()
    ob = bpy.data.objects.new(name, me)
    hc.objects.link(ob)
    ob.data.materials.append(m_hair)
    bpy.context.view_layer.objects.active = ob
    for o2 in bpy.data.objects: o2.select_set(False)
    ob.select_set(True)
    bpy.ops.object.shade_smooth()
    segs = []
    for bn in chain:
        b = rig.data.bones[bn]
        h = rig.matrix_world @ b.head_local
        t = rig.matrix_world @ b.tail_local
        segs.append((bn, h, t, (t-h), max((t-h).length_squared, 1e-12)))
    vgs = {}
    for v in ob.data.vertices:
        p = ob.matrix_world @ v.co
        ds = []
        for n2, h, t, ab, L2 in segs:
            tt = max(0.0, min(1.0, (p-h).dot(ab)/L2))
            ds.append(((p-(h+ab*tt)).length, n2))
        ds.sort()
        ws = [(1.0/max(d,1e-5)**2, n2) for d, n2 in ds[:2]]
        s = sum(w for w,_ in ws)
        for w, n2 in ws:
            if n2 not in vgs: vgs[n2] = ob.vertex_groups.new(name=n2)
            vgs[n2].add([v.index], w/s, 'REPLACE')
    am = ob.modifiers.new('Armature','ARMATURE'); am.object = rig
    bpy.context.view_layer.update()
    mw0 = ob.matrix_world.copy(); ob.parent = rig; ob.matrix_world = mw0
chains = {'L1': [f'HairL1_{k}' for k in range(1,5)], 'L2': [f'HairL2_{k}' for k in range(1,5)],
          'R1': [f'HairR1_{k}' for k in range(1,5)], 'R2': [f'HairR2_{k}' for k in range(1,5)],
          'B1': [f'HairB1_{k}' for k in range(1,5)], 'B2': [f'HairB2_{k}' for k in range(1,5)],
          'F': [f'HairF_{k}' for k in range(1,3)]}
specs = [
    (0.075,-0.045,1.615,0.45,0.024,0.016,'L1'), (0.092,0.005,1.605,0.58,0.030,0.022,'L1'),
    (0.098,0.052,1.590,0.66,0.034,0.026,'L2'), (0.085,0.082,1.575,0.70,0.032,0.024,'L2'),
    (-0.075,-0.045,1.615,0.45,0.024,0.016,'R1'), (-0.092,0.005,1.605,0.58,0.030,0.022,'R1'),
    (-0.098,0.052,1.590,0.66,0.034,0.026,'R2'), (-0.085,0.082,1.575,0.70,0.032,0.024,'R2'),
    (0.040,0.092,1.585,0.72,0.038,0.020,'B1'), (0.000,0.098,1.582,0.75,0.040,0.016,'B1'),
    (-0.040,0.092,1.585,0.72,0.038,0.020,'B2'), (0.068,0.085,1.578,0.62,0.030,0.024,'B1'),
    (-0.068,0.085,1.578,0.62,0.030,0.024,'B2'),
]
for i, (x, y, z, L, r, w, ch) in enumerate(specs):
    mecha(f'C_Mecha_{i}', x, y, z, L, r, w, chains[ch])
for i, fx in enumerate([-0.052,-0.026,0.0,0.026,0.052]):
    mecha(f'C_Franja_{i}', fx, -0.066, 1.640, 0.105+abs(fx)*0.4, 0.017, 0.004, chains['F'])

n_outfit = len(oc.objects)
n_hair = len(hc.objects)
bpy.ops.wm.save_mainfile()
print(f'OUTFIT: {n_outfit} pecas | CABELO: {n_hair} pecas')
