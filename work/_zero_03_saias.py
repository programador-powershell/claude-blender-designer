import bpy, math

SEG = 64

def loft(name, sections, mat=None, solidify=0.0025, center=(0,0), zigzag=0):
    """zigzag: amplitude de pontas handkerchief no hem (ultima secao)."""
    cx, cy = center
    verts = []; faces = []
    n = len(sections)
    for si, (z, rx, ry, ramp, rfreq) in enumerate(sections):
        for i in range(SEG):
            a = 2*math.pi*i/SEG
            rr = 1.0 + (ramp * math.sin(rfreq * a) if ramp else 0.0)
            zz = z
            if zigzag and si == n-1:
                zz = z - zigzag * abs(math.sin(4 * a))   # 8 pontas
            verts.append((cx + rx*rr*math.cos(a), cy + ry*rr*math.sin(a), zz))
    for s in range(n-1):
        for i in range(SEG):
            j = (i+1) % SEG
            faces.append((s*SEG+i, s*SEG+j, (s+1)*SEG+j, (s+1)*SEG+i))
    me = bpy.data.meshes.new(name+'_Mesh')
    me.from_pydata(verts, [], faces); me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if mat: ob.data.materials.append(mat)
    if solidify:
        s = ob.modifiers.new('Sol','SOLIDIFY'); s.thickness = solidify; s.offset = 1.0
    bpy.context.view_layer.objects.active = ob
    for o in bpy.data.objects: o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.shade_smooth()
    return ob

def mat_simple(name, color, rough=0.8, metal=0.0):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*color, 1.0)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    return m

m_blklace = mat_simple('MAT_BlackLace', (0.035, 0.030, 0.030), 0.92)
m_creamtx = mat_simple('MAT_CreamSkirt', (0.78, 0.71, 0.58), 0.85)

# Teal damask + card prints (mesmo design do manual)
m_tealD = bpy.data.materials.get('MAT_TealDamask')
if not m_tealD:
    m_tealD = bpy.data.materials.new('MAT_TealDamask'); m_tealD.use_nodes = True
    nt = m_tealD.node_tree; b = nt.nodes.get('Principled BSDF')
    b.inputs['Roughness'].default_value = 0.78
    wave = nt.nodes.new('ShaderNodeTexWave'); wave.inputs['Scale'].default_value=14.0; wave.inputs['Distortion'].default_value=6.0
    rampT = nt.nodes.new('ShaderNodeValToRGB')
    rampT.color_ramp.elements[0].color = (0.030, 0.062, 0.048, 1)
    rampT.color_ramp.elements[1].color = (0.055, 0.105, 0.082, 1)
    nt.links.new(wave.outputs['Fac'], rampT.inputs['Fac'])
    # card prints
    brick = nt.nodes.new('ShaderNodeTexBrick')
    brick.inputs['Scale'].default_value = 9.0
    brick.inputs['Mortar Size'].default_value = 0.36
    brick.offset = 0.7
    inv = nt.nodes.new('ShaderNodeMath'); inv.operation='SUBTRACT'; inv.inputs[0].default_value=1.0
    nt.links.new(brick.outputs['Fac'], inv.inputs[1])
    ng = nt.nodes.new('ShaderNodeTexNoise'); ng.inputs['Scale'].default_value=7.0
    gate = nt.nodes.new('ShaderNodeMath'); gate.operation='GREATER_THAN'; gate.inputs[1].default_value=0.72
    nt.links.new(ng.outputs['Fac'], gate.inputs[0])
    mlt = nt.nodes.new('ShaderNodeMath'); mlt.operation='MULTIPLY'
    nt.links.new(inv.outputs[0], mlt.inputs[0]); nt.links.new(gate.outputs[0], mlt.inputs[1])
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type='RGBA'
    mx.inputs['B'].default_value = (0.70, 0.63, 0.50, 1)
    nt.links.new(rampT.outputs['Color'], mx.inputs['A'])
    nt.links.new(mlt.outputs[0], mx.inputs['Factor'])
    nt.links.new(mx.outputs['Result'], b.inputs['Base Color'])
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value=180.0
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value=0.12
    nt.links.new(nz.outputs['Fac'], bp.inputs['Height'])
    nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])

# ===== 05 SAIA LACE PRETA (interna, mais longa, zigzag) =====
loft('PA05_Saia_LacePreta', [
    (1.03, 0.135, 0.112, 0, 0),
    (0.88, 0.205, 0.180, 0.012, 12),
    (0.70, 0.270, 0.245, 0.025, 16),
    (0.55, 0.310, 0.285, 0.045, 20),
], m_blklace, solidify=0.0018, zigzag=0.05)

# ===== 06 SAIA CREAM (media, handkerchief points) =====
loft('PA06_Saia_Cream', [
    (1.04, 0.138, 0.115, 0, 0),
    (0.90, 0.200, 0.175, 0.010, 10),
    (0.74, 0.255, 0.230, 0.020, 12),
    (0.61, 0.290, 0.265, 0.030, 14),
], m_creamtx, solidify=0.002, zigzag=0.07)

# ===== 07 SAIA TEAL PRINCIPAL (externa, 2 tiers + ruffles) =====
loft('PA07_Saia_Teal_Tier1', [
    (1.05, 0.142, 0.118, 0, 0),
    (0.95, 0.185, 0.160, 0.010, 12),
    (0.86, 0.225, 0.200, 0.022, 16),
    (0.82, 0.240, 0.215, 0.040, 20),   # babado tier1
], m_tealD, solidify=0.0025)
loft('PA07_Saia_Teal_Tier2', [
    (0.86, 0.225, 0.200, 0.010, 14),
    (0.76, 0.262, 0.238, 0.025, 18),
    (0.67, 0.285, 0.262, 0.045, 22),   # babado tier2
], m_tealD, solidify=0.0025)
# Overskirt drape lateral assimetrico (aberto na frente - so 2/3 tras)
verts=[]; faces=[]
n_arc = 40
secs = [(1.04, 0.150, 0.125), (0.92, 0.215, 0.190), (0.80, 0.265, 0.242), (0.70, 0.290, 0.268)]
for (z, rx, ry) in secs:
    for i in range(n_arc+1):
        a = math.pi*0.25 + (math.pi*1.5) * i/n_arc   # arco 270 graus (abre frente)
        verts.append((rx*math.cos(a), ry*math.sin(a), z))
for s in range(len(secs)-1):
    for i in range(n_arc):
        a0=s*(n_arc+1)+i; b0=a0+1; c0=(s+1)*(n_arc+1)+i+1; d0=(s+1)*(n_arc+1)+i
        faces.append((a0,b0,c0,d0))
me = bpy.data.meshes.new('PA07_Overskirt_Mesh')
me.from_pydata(verts, [], faces); me.update()
ob = bpy.data.objects.new('PA07_Overskirt', me)
bpy.context.scene.collection.objects.link(ob)
ob.data.materials.append(m_tealD)
s = ob.modifiers.new('Sol','SOLIDIFY'); s.thickness=0.0025; s.offset=1.0
bpy.context.view_layer.objects.active = ob
for o in bpy.data.objects: o.select_set(False)
ob.select_set(True); bpy.ops.object.shade_smooth()

print('SAIAS OK:', [o.name for o in bpy.data.objects if o.name.startswith(('PA05','PA06','PA07'))])
