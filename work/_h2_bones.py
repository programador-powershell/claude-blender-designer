import bpy, math

# colecao esqueleto
col = bpy.data.collections.get('Esqueleto')
if not col:
    col = bpy.data.collections.new('Esqueleto')
    bpy.context.scene.collection.children.link(col)

m_bone = bpy.data.materials.get('MAT_Bone')
if not m_bone:
    m_bone = bpy.data.materials.new('MAT_Bone')
    m_bone.use_nodes = True
    b = m_bone.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (0.92, 0.88, 0.80, 1)
    b.inputs['Roughness'].default_value = 0.55
    try:
        b.inputs['Subsurface Weight'].default_value = 0.15
        b.inputs['Subsurface Radius'].default_value = (0.008, 0.006, 0.004)
    except KeyError:
        pass

def add(ob):
    for c in ob.users_collection:
        c.objects.unlink(ob)
    col.objects.link(ob)
    if not ob.data.materials:
        ob.data.materials.append(m_bone)
    return ob

def long_bone(name, p0, p1, r_shaft, r_head, r_tail=None):
    """osso longo: diafise fina + epifises bulbosas (anatomia real)"""
    if r_tail is None: r_tail = r_head
    import mathutils
    a = mathutils.Vector(p0); b = mathutils.Vector(p1)
    d = b - a
    L = d.length
    SEG, RING = 10, 9
    profile = [(0.0, r_head*0.9), (0.06, r_head), (0.16, r_shaft*1.25), (0.32, r_shaft),
               (0.5, r_shaft*0.92), (0.68, r_shaft), (0.84, r_tail*1.25), (0.94, r_tail), (1.0, r_tail*0.9)]
    quat = d.to_track_quat('Z', 'Y')
    verts = []; faces = []
    for k, (s, r) in enumerate(profile):
        c = a + d * s
        for i in range(SEG):
            ang = 2*math.pi*i/SEG
            off = mathutils.Vector((r*math.cos(ang), r*math.sin(ang), 0))
            verts.append(c + quat @ off)
    n = len(profile)
    for kk in range(n-1):
        for i in range(SEG):
            j = (i+1) % SEG
            faces.append((kk*SEG+i, kk*SEG+j, (kk+1)*SEG+j, (kk+1)*SEG+i))
    # caps
    c0 = len(verts); verts.append(a)
    for i in range(SEG): faces.append(((0)*SEG+(i+1)%SEG, (0)*SEG+i, c0))
    c1 = len(verts); verts.append(b)
    for i in range(SEG): faces.append(((n-1)*SEG+i, (n-1)*SEG+(i+1)%SEG, c1))
    me = bpy.data.meshes.new(name+'_Me')
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    for o in bpy.data.objects: o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.shade_smooth()
    return add(ob)

# ===== CRANIO: calota + maxilar =====
bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=14, radius=0.066, location=(0, -0.012, 1.595))
cr = bpy.context.object; cr.name = 'OS_Cranio'
cr.scale = (0.82, 1.0, 0.88)
bpy.ops.object.shade_smooth()
add(cr)
# mandibula: arco
bpy.ops.mesh.primitive_torus_add(major_radius=0.040, minor_radius=0.008,
    location=(0, -0.030, 1.508), rotation=(math.radians(15), 0, 0))
mand = bpy.context.object; mand.name = 'OS_Mandibula'
mand.scale = (0.95, 1.15, 1.0)
add(mand)

# ===== COLUNA: 24 vertebras (7C + 12T + 5L) + sacro =====
spine_pts = []  # (z, y_curve) curva em S real
for k in range(24):
    s = k / 23
    z = 1.475 - s * 0.515  # C1 z1.475 -> L5 z0.96
    # lordose cervical(-y leve), cifose toracica(+y), lordose lombar(-y)
    y = 0.030 + 0.028*math.sin(s*math.pi) - 0.020*math.exp(-((s-0.92)/0.12)**2) - 0.012*math.exp(-((s-0.04)/0.10)**2)
    spine_pts.append((z, y))
for k, (z, y) in enumerate(spine_pts):
    tipo = 'C' if k < 7 else ('T' if k < 19 else 'L')
    num = k+1 if k < 7 else (k-6 if k < 19 else k-18)
    r = 0.011 if tipo=='C' else (0.014 if tipo=='T' else 0.017)
    bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=r, depth=0.016, location=(0, y, z))
    vb = bpy.context.object; vb.name = f'OS_Vert_{tipo}{num}'
    add(vb)
    # processo espinhoso
    bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=0.005, depth=0.022,
        location=(0, y+0.020, z), rotation=(math.radians(-80), 0, 0))
    pe = bpy.context.object; pe.name = f'OS_Proc_{tipo}{num}'
    add(pe)
# sacro
bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.030, radius2=0.012, depth=0.085,
    location=(0, 0.045, 0.905), rotation=(math.radians(12), 0, 0))
sac = bpy.context.object; sac.name = 'OS_Sacro'
add(sac)

# ===== CAIXA TORACICA: 12 pares de costelas + esterno =====
for k in range(12):
    s = k / 11
    z = 1.392 - s * 0.205
    vy = 0.030 + 0.028*math.sin((7+k)/23*math.pi)
    width = 0.075 + 0.035*math.sin(s*math.pi*0.85)
    depth = 0.055 + 0.022*math.sin(s*math.pi*0.8)
    for g in (1, -1):
        bpy.ops.mesh.primitive_torus_add(major_radius=width, minor_radius=0.0042,
            major_segments=22, minor_segments=6,
            location=(g*0.004, vy - depth*0.7, z),
            rotation=(math.radians(8 + s*14), 0, 0))
        rb = bpy.context.object; rb.name = f'OS_Costela_{k+1}_{"L" if g>0 else "R"}'
        rb.scale = (1.0, depth/width if width>0 else 0.7, 0.55)
        # so metade lateral-frontal (deletar metade oposta via bisect rapido: shrink x oposto)
        for v in rb.data.vertices:
            if (v.co.x * g) < -0.01:
                v.co.x *= 0.18
        rb.data.update()
        add(rb)
# esterno
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -0.075, 1.300))
st = bpy.context.object; st.name = 'OS_Esterno'
st.scale = (0.018, 0.006, 0.085)
add(st)

# ===== CLAVICULAS + ESCAPULAS =====
for g, S in [(1,'L'), (-1,'R')]:
    long_bone(f'OS_Clavicula_{S}', (g*0.012, -0.052, 1.408), (g*0.135, -0.018, 1.418), 0.0042, 0.007)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(g*0.075, 0.052, 1.345))
    sc_ = bpy.context.object; sc_.name = f'OS_Escapula_{S}'
    sc_.scale = (0.045, 0.008, 0.062)
    sc_.rotation_euler = (0, g*math.radians(-12), g*math.radians(8))
    add(sc_)

# ===== PELVIS: 2 iliacos =====
for g, S in [(1,'L'), (-1,'R')]:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=0.052,
        location=(g*0.052, 0.022, 0.945))
    il = bpy.context.object; il.name = f'OS_Iliaco_{S}'
    il.scale = (0.75, 0.55, 1.0)
    bpy.ops.object.shade_smooth()
    # escavar: nao (low poly ok)
    add(il)

# ===== OSSOS LONGOS (com epifises) =====
for g, S in [(1,'L'), (-1,'R')]:
    # bracos (A-pose ~20graus: ombro (0.155,0.005,1.405) -> cotovelo -> pulso)
    sho = (g*0.150, 0.005, 1.400)
    elb = (g*0.318, 0.011, 1.342)
    wri = (g*0.470, 0.016, 1.288)
    long_bone(f'OS_Umero_{S}', sho, elb, 0.0085, 0.016, 0.013)
    long_bone(f'OS_Radio_{S}', elb, (wri[0]-g*0.006, wri[1]-0.006, wri[2]), 0.006, 0.009, 0.008)
    long_bone(f'OS_Ulna_{S}', (elb[0], elb[1]+0.009, elb[2]+0.004), (wri[0]+g*0.004, wri[1]+0.006, wri[2]-0.003), 0.0052, 0.010, 0.006)
    # pernas: femur com COLO+CABECA (anatomia real)
    hip_socket = (g*0.058, 0.018, 0.940)
    fem_top = (g*0.092, 0.012, 0.918)   # grande trocanter
    knee = (g*0.094, 0.008, 0.508)
    long_bone(f'OS_Femur_{S}', fem_top, knee, 0.011, 0.019, 0.020)
    # colo do femur (liga trocanter a cabeca no acetabulo)
    long_bone(f'OS_ColoFemur_{S}', fem_top, hip_socket, 0.009, 0.009, 0.014)
    # patela
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=8, radius=0.016,
        location=(g*0.094, -0.042, 0.505))
    pa = bpy.context.object; pa.name = f'OS_Patela_{S}'
    pa.scale = (1.0, 0.55, 1.1)
    add(pa)
    ankle = (g*0.112, 0.038, 0.115)
    long_bone(f'OS_Tibia_{S}', knee, ankle, 0.0095, 0.017, 0.013)
    long_bone(f'OS_Fibula_{S}', (knee[0]+g*0.022, knee[1]+0.012, knee[2]-0.01),
              (ankle[0]+g*0.014, ankle[1]+0.004, ankle[2]+0.004), 0.0045, 0.007, 0.008)
    # pe: calcaneo + metatarsos
    bpy.ops.mesh.primitive_cube_add(size=1, location=(g*0.112, 0.062, 0.045))
    ca = bpy.context.object; ca.name = f'OS_Calcaneo_{S}'
    ca.scale = (0.030, 0.050, 0.038)
    add(ca)
    for mt in range(5):
        mx = g*(0.082 + mt*0.0145)
        long_bone(f'OS_Meta{mt+1}_{S}', (mx, 0.005, 0.035), (mx, -0.085, 0.022), 0.0030, 0.0045)

n = len([o for o in col.objects])
bpy.ops.wm.save_mainfile()
print(f'ESQUELETO OSSEO: {n} ossos mesh')
