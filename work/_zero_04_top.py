import bpy, math

SEG = 48

def loft(name, sections, mat=None, solidify=0.0025, center=(0,0), axis='Z'):
    cx, cy = center
    verts = []; faces = []
    for (t, rx, ry, ramp, rfreq) in sections:
        for i in range(SEG):
            a = 2*math.pi*i/SEG
            rr = 1.0 + (ramp * math.sin(rfreq * a) if ramp else 0.0)
            if axis == 'Z':
                verts.append((cx + rx*rr*math.cos(a), cy + ry*rr*math.sin(a), t))
            else:  # X axis (mangas/luvas)
                verts.append((t, cy + rx*rr*math.cos(a), cx + ry*rr*math.sin(a)))
    n = len(sections)
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

m_tealD = bpy.data.materials['MAT_TealDamask']
m_leather = bpy.data.materials['MAT_Leather']
m_gold = bpy.data.materials.get('MAT_Gold')
if not m_gold:
    m_gold = bpy.data.materials.new('MAT_Gold'); m_gold.use_nodes = True
    b = m_gold.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (0.62, 0.45, 0.16, 1)
    b.inputs['Metallic'].default_value = 1.0
    b.inputs['Roughness'].default_value = 0.32

# ===== 08 CORPETE TEAL (cintura marcada, sobre chemise) =====
loft('PA08_Corpete', [
    (1.36, 0.122, 0.098, 0, 0),
    (1.30, 0.128, 0.104, 0, 0),
    (1.20, 0.108, 0.092, 0, 0),
    (1.12, 0.102, 0.088, 0, 0),
    (1.05, 0.118, 0.100, 0, 0),   # peplum abre
], m_tealD, solidify=0.003)
# Gold trim: 2 aneis finos no corpete
loft('PA08_Trim_Top', [
    (1.365, 0.125, 0.101, 0, 0), (1.350, 0.126, 0.102, 0, 0),
], m_gold, solidify=0.004)
loft('PA08_Trim_Waist', [
    (1.075, 0.112, 0.095, 0, 0), (1.060, 0.115, 0.098, 0, 0),
], m_gold, solidify=0.004)
# Lacing frontal: cordoes gold cruzados (cilindros finos)
for k in range(5):
    z = 1.10 + k * 0.05
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.0035, depth=0.09,
        location=(0, -0.096, z), rotation=(0, math.radians(90), 0))
    c = bpy.context.object; c.name = f'PA08_Lace_{k}'
    c.data.materials.append(m_gold)

# ===== 09 MANGAS PUFF (esferas achatadas no ombro) =====
for sgn, side in [(1,'L'), (-1,'R')]:
    loft(f'PA09_Manga_{side}', [
        (sgn*0.13, 0.055, 0.055, 0, 0),
        (sgn*0.20, 0.085, 0.085, 0.03, 10),
        (sgn*0.28, 0.080, 0.080, 0.05, 12),
        (sgn*0.33, 0.048, 0.048, 0.08, 14),  # franzido punho babado
    ] if sgn>0 else [
        (sgn*0.13, 0.055, 0.055, 0, 0),
        (sgn*0.20, 0.085, 0.085, 0.03, 10),
        (sgn*0.28, 0.080, 0.080, 0.05, 12),
        (sgn*0.33, 0.048, 0.048, 0.08, 14),
    ], m_tealD, solidify=0.0025, center=(1.385, 0), axis='X')

# ===== 10 LUVAS (antebraco ate mao) =====
for sgn, side in [(1,'L'), (-1,'R')]:
    secs = [(sgn*0.46, 0.042, 0.042, 0, 0),
            (sgn*0.58, 0.036, 0.036, 0, 0),
            (sgn*0.70, 0.034, 0.034, 0, 0),
            (sgn*0.79, 0.037, 0.037, 0, 0)]
    loft(f'PA10_Luva_{side}', secs, m_leather, solidify=0.002, center=(1.385, 0), axis='X')
    # fivela gold na luva
    bpy.ops.mesh.primitive_torus_add(major_radius=0.040, minor_radius=0.005,
        location=(sgn*0.52, 0, 1.385), rotation=(0, math.radians(90), 0))
    t = bpy.context.object; t.name = f'PA10_Fivela_{side}'
    t.data.materials.append(m_gold)

# ===== 11 SASH + BOW TRASEIRO =====
loft('PA11_Sash', [
    (1.065, 0.116, 0.099, 0, 0), (1.020, 0.122, 0.104, 0, 0),
], m_tealD, solidify=0.004)
# Bow: 2 loops esferas achatadas + nó + fitas
for sgn in [1, -1]:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.001,
        location=(sgn*0.085, 0.135, 1.06))
    L = bpy.context.object; L.name = f'PA11_BowLoop_{"L" if sgn>0 else "R"}'
    L.scale = (0.075, 0.035, 0.052)
    L.data.materials.append(m_tealD)
    bpy.ops.object.shade_smooth()
bpy.ops.mesh.primitive_cube_add(size=0.045, location=(0, 0.138, 1.06))
knot = bpy.context.object; knot.name = 'PA11_BowKnot'
knot.scale = (0.8, 0.5, 0.9)
knot.data.materials.append(m_gold)
# Fitas pendentes
for sgn in [1, -1]:
    verts=[]; faces=[]
    w = 0.045
    pts = [(sgn*0.03, 0.135, 1.04), (sgn*0.05, 0.150, 0.92), (sgn*0.065, 0.160, 0.80)]
    for (x, y, z) in pts:
        verts.append((x-w/2, y, z)); verts.append((x+w/2, y, z))
    for s in range(len(pts)-1):
        faces.append((2*s, 2*s+1, 2*s+3, 2*s+2))
    me = bpy.data.meshes.new(f'PA11_Fita_Mesh_{sgn}')
    me.from_pydata(verts, [], faces); me.update()
    ob = bpy.data.objects.new(f'PA11_Fita_{"L" if sgn>0 else "R"}', ob_data := me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(m_tealD)
    s = ob.modifiers.new('Sol','SOLIDIFY'); s.thickness = 0.002

print('TOP OK:', [o.name for o in bpy.data.objects if o.name.startswith(('PA08','PA09','PA10','PA11'))])
