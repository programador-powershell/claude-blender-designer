import bpy, math, random
from mathutils import Vector

random.seed(42)

# Limpar saias cloth falhas
for nm in ['SKIRT_Lace','SKIRT_Cream','SKIRT_Teal']:
    o = bpy.data.objects.get(nm)
    if o: bpy.data.objects.remove(o, do_unlink=True)
for me in list(bpy.data.meshes):
    if me.users == 0: bpy.data.meshes.remove(me)

SEG = 96  # alta resolucao radial pra folds

def loft2(name, sections, mat, solidify=0.0022, hem_drop=0.0, hem_freq=4,
           fold=(0.0, 12, 0.0, 5), axis='Z'):
    """sections: [(t, cx, cy, rx, ry)] - elipse com CENTRO deslocado por secao.
    fold: (amp1, freq1, amp2, freq2) - 2 frequencias de dobras, crescem pra baixo.
    hem_drop: hem desce variavel (pontas)."""
    a1, f1, a2, f2 = fold
    ph1 = random.uniform(0, 6.28); ph2 = random.uniform(0, 6.28)
    verts = []; faces = []
    n = len(sections)
    for si, (t, cx, cy, rx, ry) in enumerate(sections):
        tt = si / max(n-1, 1)
        for i in range(SEG):
            a = 2*math.pi*i/SEG
            folds = 1.0 + tt*(a1*math.sin(f1*a + ph1) + a2*math.sin(f2*a + ph2))
            zz = t
            if hem_drop and si == n-1:
                zz = t - hem_drop * abs(math.sin(hem_freq*a + ph1))
            if axis == 'Z':
                verts.append((cx + rx*folds*math.cos(a), cy + ry*folds*math.sin(a), zz))
            else:
                verts.append((zz, cy + rx*folds*math.cos(a), cx + ry*folds*math.sin(a)))
    for s in range(n-1):
        for i in range(SEG):
            j = (i+1) % SEG
            faces.append((s*SEG+i, s*SEG+j, (s+1)*SEG+j, (s+1)*SEG+i))
    me = bpy.data.meshes.new(name+'_Mesh')
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
    return ob

def matp(name, color, rough=0.8, metal=0.0):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*color, 1.0)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    return m

m_teal  = bpy.data.materials.get('MAT_TealDamask') or matp('MAT_TealDamask', (0.045,0.085,0.066), 0.78)
m_cream = bpy.data.materials.get('MAT_CreamL') or matp('MAT_CreamL', (0.80,0.74,0.62), 0.85)
m_blk   = bpy.data.materials.get('MAT_BlkLace') or matp('MAT_BlkLace', (0.035,0.03,0.03), 0.9)
m_leather = matp('MAT_LeatherP', (0.028,0.024,0.02), 0.42)
m_gold  = matp('MAT_GoldP', (0.62,0.45,0.16), 0.32, 1.0)
m_hair  = matp('MAT_HairP', (0.018,0.015,0.016), 0.38)

# Stripes meias
m_str = bpy.data.materials.get('MAT_StrZ')
if not m_str:
    m_str = bpy.data.materials.new('MAT_StrZ'); m_str.use_nodes = True
    nt = m_str.node_tree; b = nt.nodes.get('Principled BSDF')
    b.inputs['Roughness'].default_value = 0.8
    geo = nt.nodes.new('ShaderNodeNewGeometry'); sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(geo.outputs['Position'], sep.inputs['Vector'])
    mm = nt.nodes.new('ShaderNodeMath'); mm.operation='MULTIPLY'; mm.inputs[1].default_value=70.0
    nt.links.new(sep.outputs['Z'], mm.inputs[0])
    sn = nt.nodes.new('ShaderNodeMath'); sn.operation='SINE'
    nt.links.new(mm.outputs[0], sn.inputs[0])
    gt = nt.nodes.new('ShaderNodeMath'); gt.operation='GREATER_THAN'; gt.inputs[1].default_value=0.0
    nt.links.new(sn.outputs[0], gt.inputs[0])
    rp = nt.nodes.new('ShaderNodeValToRGB')
    rp.color_ramp.elements[0].color = (0.05,0.045,0.04,1)
    rp.color_ramp.elements[1].color = (0.72,0.69,0.65,1)
    nt.links.new(gt.outputs[0], rp.inputs['Fac'])
    nt.links.new(rp.outputs['Color'], b.inputs['Base Color'])

# ===== SAIAS 3 CAMADAS - fit anatomico (cy +0.02 cobre bunda) + folds 2-freq =====
# lace preta interna longa
loft2('GD_Saia_Lace', [
    (1.045, 0, 0.020, 0.155, 0.140),
    (0.92,  0, 0.025, 0.215, 0.200),
    (0.76,  0, 0.030, 0.275, 0.260),
    (0.56,  0, 0.030, 0.330, 0.315),
], m_blk, 0.0018, hem_drop=0.055, hem_freq=4, fold=(0.030, 11, 0.018, 5))
# cream media com pontas
loft2('GD_Saia_Cream', [
    (1.05, 0, 0.020, 0.158, 0.143),
    (0.93, 0, 0.025, 0.210, 0.195),
    (0.78, 0, 0.030, 0.262, 0.247),
    (0.62, 0, 0.030, 0.305, 0.290),
], m_cream, 0.0020, hem_drop=0.075, hem_freq=4, fold=(0.026, 9, 0.015, 4))
# teal externa 2 tiers
loft2('GD_Saia_Teal_T1', [
    (1.055, 0, 0.020, 0.162, 0.147),
    (0.96,  0, 0.025, 0.205, 0.190),
    (0.875, 0, 0.028, 0.245, 0.228),
], m_teal, 0.0025, hem_drop=0.020, hem_freq=8, fold=(0.028, 12, 0.014, 5))
loft2('GD_Saia_Teal_T2', [
    (0.885, 0, 0.028, 0.248, 0.232),
    (0.79,  0, 0.030, 0.280, 0.262),
    (0.69,  0, 0.030, 0.300, 0.285),
], m_teal, 0.0025, hem_drop=0.030, hem_freq=10, fold=(0.034, 14, 0.018, 6))

# ===== CORPETE (fit busto/cintura real, centro deslocado) =====
loft2('GD_Corpete', [
    (1.335, 0, -0.005, 0.128, 0.118),
    (1.27,  0, -0.012, 0.122, 0.125),
    (1.17,  0,  0.005, 0.112, 0.098),
    (1.09,  0,  0.008, 0.118, 0.092),
    (1.04,  0,  0.015, 0.138, 0.115),  # peplum
], m_teal, 0.003, fold=(0.0, 1, 0.0, 1))
# trims gold
loft2('GD_Trim_Top', [(1.34, 0, -0.005, 0.130, 0.120), (1.325, 0, -0.006, 0.131, 0.121)], m_gold, 0.004, fold=(0,1,0,1))
loft2('GD_Trim_Waist', [(1.065, 0, 0.010, 0.126, 0.100), (1.050, 0, 0.012, 0.128, 0.103)], m_gold, 0.004, fold=(0,1,0,1))
# lacing cords frente
for k in range(5):
    z = 1.10 + k*0.045
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.003, depth=0.085,
        location=(0, -0.105, z), rotation=(0, math.radians(90), 0))
    c = bpy.context.object; c.name = f'GD_Lacing_{k}'
    c.data.materials.append(m_gold)

# ===== MEIAS (pernas reais: centro x +-0.095, cy 0.02) =====
for g, S in [(1,'L'), (-1,'R')]:
    loft2(f'GD_Meia_{S}', [
        (0.64, g*0.094, 0.022, 0.072, 0.072),
        (0.52, g*0.097, 0.022, 0.064, 0.066),
        (0.34, g*0.100, 0.035, 0.056, 0.058),
        (0.18, g*0.100, 0.040, 0.050, 0.052),
    ], m_str, 0.0014, fold=(0,1,0,1))

# ===== BOTAS =====
for g, S in [(1,'L'), (-1,'R')]:
    loft2(f'GD_Bota_Cano_{S}', [
        (0.36, g*0.100, 0.038, 0.062, 0.066),
        (0.22, g*0.100, 0.040, 0.057, 0.060),
        (0.10, g*0.100, 0.040, 0.054, 0.058),
        (0.05, g*0.100, 0.038, 0.054, 0.060),
    ], m_leather, 0.0035, fold=(0,1,0,1))
    # pe + salto
    bpy.ops.mesh.primitive_cube_add(size=1, location=(g*0.100, -0.045, 0.030))
    pe = bpy.context.object; pe.name = f'GD_Bota_Pe_{S}'
    pe.scale = (0.052, 0.115, 0.030)
    pe.data.materials.append(m_leather)
    bpy.ops.object.shade_smooth()
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.016, depth=0.045,
        location=(g*0.100, 0.045, 0.0225))
    sl = bpy.context.object; sl.name = f'GD_Salto_{S}'
    sl.data.materials.append(m_leather)

# ===== MANGAS PUFF + LUVAS (braco z=1.375, span x ate 0.40) =====
for g, S in [(1,'L'), (-1,'R')]:
    loft2(f'GD_Manga_{S}', [
        (g*0.155, 1.375, 0.0, 0.062, 0.062),
        (g*0.215, 1.378, 0.0, 0.085, 0.085),
        (g*0.275, 1.376, 0.0, 0.078, 0.078),
        (g*0.310, 1.374, 0.0, 0.048, 0.048),
    ], m_teal, 0.0024, fold=(0.05, 10, 0.02, 5), axis='X')
    loft2(f'GD_Luva_{S}', [
        (g*0.330, 1.375, 0.0, 0.040, 0.040),
        (g*0.380, 1.375, 0.0, 0.036, 0.036),
        (g*0.420, 1.375, 0.0, 0.038, 0.038),
    ], m_leather, 0.0018, fold=(0,1,0,1), axis='X')

# ===== CABELO (calota fit cabeca + massa tras + mechas) =====
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.097,
    location=(0, 0.030, 1.555))
sc_ = bpy.context.object; sc_.name = 'GD_Cabelo_Calota'
sc_.scale = (1.0, 1.12, 1.06)
sc_.data.materials.append(m_hair)
bpy.ops.object.shade_smooth()
# massa traseira
loft2('GD_Cabelo_Massa', [
    (1.56, 0, 0.085, 0.090, 0.055),
    (1.42, 0, 0.105, 0.105, 0.062),
    (1.24, 0, 0.115, 0.108, 0.058),
    (1.05, 0, 0.118, 0.092, 0.048),
    (0.92, 0, 0.115, 0.070, 0.038),
], m_hair, 0.0, hem_drop=0.06, hem_freq=5, fold=(0.06, 7, 0.03, 3))
# mechas frente
for g in [1,-1]:
    loft2(f'GD_Mecha_{"L" if g>0 else "R"}', [
        (1.56, g*0.080, -0.030, 0.020, 0.020),
        (1.42, g*0.098, -0.028, 0.017, 0.017),
        (1.26, g*0.092, -0.015, 0.013, 0.013),
    ], m_hair, 0.0, fold=(0,1,0,1))

# ===== CHAPEU mini top hat =====
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.060, depth=0.082,
    location=(0.048, 0.005, 1.715), rotation=(0, math.radians(-14), 0))
cp = bpy.context.object; cp.name = 'GD_Chapeu_Copa'; cp.data.materials.append(m_teal)
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.092, depth=0.007,
    location=(0.038, 0.005, 1.673), rotation=(0, math.radians(-14), 0))
ab = bpy.context.object; ab.name = 'GD_Chapeu_Aba'; ab.data.materials.append(m_teal)
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.062, depth=0.016,
    location=(0.044, 0.005, 1.690), rotation=(0, math.radians(-14), 0))
bd = bpy.context.object; bd.name = 'GD_Chapeu_Banda'; bd.data.materials.append(m_gold)

# ===== BOW traseiro + acessorios =====
for g in [1,-1]:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.001,
        location=(g*0.080, 0.150, 1.05))
    L = bpy.context.object; L.name = f'GD_BowLoop_{"L" if g>0 else "R"}'
    L.scale = (0.070, 0.032, 0.048)
    L.data.materials.append(m_teal)
    bpy.ops.object.shade_smooth()
bpy.ops.mesh.primitive_cube_add(size=0.042, location=(0, 0.152, 1.05))
kn = bpy.context.object; kn.name = 'GD_BowKnot'; kn.scale=(0.8,0.5,0.9)
kn.data.materials.append(m_gold)
bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.026, depth=0.009,
    location=(-0.135, -0.055, 0.99), rotation=(math.radians(90),0,0))
wt = bpy.context.object; wt.name = 'GD_Relogio'; wt.data.materials.append(m_gold)

n = len([o for o in bpy.data.objects if o.name.startswith('GD_')])
print(f'GARMENTS V2: {n} pecas')
bpy.ops.wm.save_mainfile()
print('SAVED')
