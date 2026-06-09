import bpy, math
from mathutils import Vector

SEG = 48  # resolucao radial

def loft(name, sections, mat=None, solidify=0.0025, close_top=False, close_bot=False,
          center=(0,0)):
    """Superficie loft: sections = [(z, rx, ry, ruffle_amp, ruffle_freq), ...] top->bottom.
    Cada anel SEG verts. Liga quads. EU controlo a silhueta por secao."""
    cx, cy = center
    verts = []; faces = []
    for (z, rx, ry, ramp, rfreq) in sections:
        for i in range(SEG):
            a = 2*math.pi*i/SEG
            rr = 1.0 + (ramp * math.sin(rfreq * a) if ramp else 0.0)
            verts.append((cx + rx*rr*math.cos(a), cy + ry*rr*math.sin(a), z))
    n = len(sections)
    for s in range(n-1):
        for i in range(SEG):
            j = (i+1) % SEG
            a = s*SEG+i; b = s*SEG+j; c = (s+1)*SEG+j; d = (s+1)*SEG+i
            faces.append((a,b,c,d))
    if close_top:
        ci = len(verts); verts.append((cx, cy, sections[0][0]))
        for i in range(SEG):
            faces.append((ci, (i+1)%SEG, i))
    if close_bot:
        ci = len(verts); base = (n-1)*SEG
        verts.append((cx, cy, sections[-1][0]))
        for i in range(SEG):
            faces.append((ci, base+i, base+(i+1)%SEG))
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

# ===== MATERIAIS BASE =====
m_cream  = mat_simple('MAT_Cream',  (0.82, 0.76, 0.64), 0.85)
m_leather= mat_simple('MAT_Leather',(0.028, 0.024, 0.02), 0.42)

# Stripes meias (Z sine)
m_str = bpy.data.materials.get('MAT_StripesZ')
if not m_str:
    m_str = bpy.data.materials.new('MAT_StripesZ'); m_str.use_nodes = True
    nt = m_str.node_tree; b = nt.nodes.get('Principled BSDF')
    b.inputs['Roughness'].default_value = 0.8
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
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

# ===== 01 BLOOMER (cos + 2 pernas puff + babado) =====
loft('PA01_Bloomer_Cos', [
    (1.02, 0.130, 0.105, 0, 0),
    (0.94, 0.140, 0.115, 0, 0),
    (0.88, 0.135, 0.112, 0, 0),
], m_cream)
for sgn, side in [(1,'L'), (-1,'R')]:
    loft(f'PA01_Bloomer_Perna_{side}', [
        (0.90, 0.085, 0.085, 0, 0),
        (0.80, 0.105, 0.100, 0.02, 8),
        (0.72, 0.110, 0.105, 0.03, 8),
        (0.68, 0.082, 0.080, 0.05, 12),  # franzido babado
        (0.66, 0.092, 0.090, 0.07, 12),  # babado aberto
    ], m_cream, center=(sgn*0.088, 0))

# ===== 02 CHEMISE (top decote + saiote interno) =====
loft('PA02_Chemise_Top', [
    (1.40, 0.118, 0.092, 0, 0),
    (1.32, 0.130, 0.105, 0, 0),
    (1.20, 0.108, 0.090, 0, 0),
    (1.10, 0.105, 0.088, 0, 0),
], m_cream, solidify=0.002)
loft('PA02_Chemise_Saiote', [
    (1.05, 0.125, 0.105, 0, 0),
    (0.85, 0.180, 0.155, 0.01, 10),
    (0.66, 0.230, 0.205, 0.02, 14),
    (0.60, 0.245, 0.220, 0.04, 18),
], m_cream, solidify=0.002)

# ===== 03 MEIAS LISTRADAS =====
for sgn, side in [(1,'L'), (-1,'R')]:
    loft(f'PA03_Meia_{side}', [
        (0.62, 0.062, 0.062, 0, 0),
        (0.53, 0.058, 0.058, 0, 0),
        (0.35, 0.050, 0.050, 0, 0),
        (0.16, 0.044, 0.044, 0, 0),
    ], m_str, solidify=0.0015, center=(sgn*0.100, 0))

# ===== 04 BOTAS (cano + pe + salto + sola) =====
for sgn, side in [(1,'L'), (-1,'R')]:
    cx = sgn*0.103
    loft(f'PA04_Bota_Cano_{side}', [
        (0.34, 0.062, 0.062, 0, 0),
        (0.20, 0.057, 0.057, 0, 0),
        (0.10, 0.052, 0.055, 0, 0),
        (0.045, 0.050, 0.058, 0, 0),
    ], m_leather, solidify=0.004, center=(cx, 0))
    # pe (loft no eixo Y manual)
    verts=[]; faces=[]
    foot_secs = [(-0.005, 0.050, 0.040), (-0.06, 0.048, 0.036), (-0.12, 0.044, 0.030), (-0.165, 0.036, 0.022)]
    for (y, rx, rz) in foot_secs:
        for i in range(SEG):
            a = 2*math.pi*i/SEG
            verts.append((cx + rx*math.cos(a), y, 0.045 + rz*math.sin(a)*0.9))
    for s in range(len(foot_secs)-1):
        for i in range(SEG):
            j=(i+1)%SEG
            faces.append((s*SEG+i, s*SEG+j, (s+1)*SEG+j, (s+1)*SEG+i))
    ci=len(verts); verts.append((cx, -0.175, 0.045))
    base=(len(foot_secs)-1)*SEG
    for i in range(SEG): faces.append((ci, base+i, base+(i+1)%SEG))
    me = bpy.data.meshes.new(f'PA04_Bota_Pe_{side}_Mesh')
    me.from_pydata(verts, [], faces); me.update()
    ob = bpy.data.objects.new(f'PA04_Bota_Pe_{side}', me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(m_leather)
    s = ob.modifiers.new('Sol','SOLIDIFY'); s.thickness=0.004
    bpy.context.view_layer.objects.active = ob
    for o in bpy.data.objects: o.select_set(False)
    ob.select_set(True); bpy.ops.object.shade_smooth()
    # salto
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.018, depth=0.05, location=(cx, 0.030, 0.022))
    h = bpy.context.object; h.name = f'PA04_Bota_Salto_{side}'
    h.data.materials.append(m_leather)

print('UNDER LAYERS OK:', [o.name for o in bpy.data.objects if o.name.startswith('PA0')])
