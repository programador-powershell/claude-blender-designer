import bpy, math
import mathutils

body = bpy.data.objects['HumanBody']
me = body.data
skin = bpy.data.materials['MAT_HSkin']
H = 1.70

# ===== deletar maos/pes draft (caixas) — verts além do pulso/tornozelo =====
import bmesh
bm = bmesh.new()
bm.from_mesh(me)
WRIST_X = 0.155 + 0.345  # 0.50
to_del = [v for v in bm.verts if abs(v.co.x) > WRIST_X - 0.012 and v.co.z > 1.20]
# pes draft: z<0.06 e |x|>0.05 com y<-0.04 (caixas na frente)
to_del += [v for v in bm.verts if v.co.z < 0.062 and v.co.y < -0.030]
bmesh.ops.delete(bm, geom=list(set(to_del)), context='VERTS')
bm.to_mesh(me)
bm.free()
me.update()
print('draft removido')

def tube(verts, faces, pts_r, nseg=10, close_tip=True):
    """tubo por pontos (p, raio); retorna range de verts adicionados"""
    base = len(verts)
    n = len(pts_r)
    for k, (p, r) in enumerate(pts_r):
        if k < n - 1:
            d = mathutils.Vector(pts_r[k+1][0]) - mathutils.Vector(p)
        else:
            d = mathutils.Vector(p) - mathutils.Vector(pts_r[k-1][0])
        quat = d.to_track_quat('Z', 'Y')
        for i in range(nseg):
            a = 2 * math.pi * i / nseg
            off = mathutils.Vector((r * math.cos(a), r * math.sin(a), 0))
            verts.append(tuple(mathutils.Vector(p) + quat @ off))
    for kk in range(n - 1):
        for i in range(nseg):
            j = (i + 1) % nseg
            faces.append((base + kk*nseg + i, base + kk*nseg + j,
                          base + (kk+1)*nseg + j, base + (kk+1)*nseg + i))
    if close_tip:
        tipc = len(verts)
        verts.append(pts_r[-1][0])
        for i in range(nseg):
            faces.append((base + (n-1)*nseg + i, base + (n-1)*nseg + (i+1)%nseg, tipc))
    return base

# ===== MAOS reais: palma + 5 dedos x 3 falanges =====
nv = []; nf = []
for g in (1, -1):
    wx = g * 0.498
    wy, wz = 0.016, 1.279  # pulso (A-pose desce)
    # direcao da mao continua a do braco: (0.345,0.012,-0.125) normalizada
    dirv = mathutils.Vector((g*0.345, 0.012, -0.125)).normalized()
    # PALMA: tubo achatado 4 aneis
    palm_pts = []
    for s in [0.0, 0.3, 0.65, 1.0]:
        p = mathutils.Vector((wx, wy, wz)) + dirv * (0.078 * s)
        palm_pts.append((tuple(p), 0.030 - 0.004*s))
    pb = tube(nv, nf, palm_pts, 12, close_tip=False)
    # achatar palma (y escala 0.45 ao redor de wy)
    for idx in range(pb, len(nv)):
        x, y, z = nv[idx]
        nv[idx] = (x, wy + (y - wy) * 0.45, z)
    # DEDOS: 4 dedos + polegar
    knuckle = mathutils.Vector((wx, wy, wz)) + dirv * 0.078
    fingers = [
        ('index',  -0.0165, 0.0095, 0.030, 1.00),
        ('middle', -0.0055, 0.0100, 0.033, 1.00),
        ('ring',    0.0055, 0.0095, 0.030, 1.00),
        ('pinky',   0.0165, 0.0080, 0.024, 1.00),
    ]
    for nm, oy, r0, seg1, curl in fingers:
        p0 = knuckle + mathutils.Vector((0, oy, 0))
        pts = [(tuple(p0), r0)]
        p = mathutils.Vector(p0)
        d = mathutils.Vector(dirv)
        for fl, fr in [(seg1, r0*0.92), (seg1*0.72, r0*0.82), (seg1*0.55, r0*0.70)]:
            # leve curl pra baixo a cada falange
            d = (d + mathutils.Vector((0, 0, -0.10))).normalized()
            p = p + d * fl
            pts.append((tuple(p), fr))
        tube(nv, nf, pts, 8)
    # POLEGAR: sai da lateral da palma, ângulo aberto
    tb0 = mathutils.Vector((wx, wy - 0.026, wz - 0.006)) + dirv * 0.020
    td = (dirv + mathutils.Vector((0, -0.85, -0.18))).normalized()
    pts = [(tuple(tb0), 0.011)]
    p = mathutils.Vector(tb0)
    for fl, fr in [(0.030, 0.010), (0.026, 0.0085)]:
        p = p + td * fl
        pts.append((tuple(p), fr))
        td = (td + mathutils.Vector((g*0.15, 0, -0.05))).normalized()
    tube(nv, nf, pts, 8)

# ===== PES reais: calcanhar->peito do pe->dedos =====
for g in (1, -1):
    cx = g * 0.112
    # corpo do pe: tubo deitado do calcanhar a base dos dedos
    foot_pts = [
        ((cx, 0.075, 0.052), 0.040),
        ((cx, 0.030, 0.046), 0.044),
        ((cx, -0.030, 0.038), 0.042),
        ((cx, -0.080, 0.028), 0.038),
        ((cx, -0.115, 0.022), 0.033),
    ]
    fb = tube(nv, nf, foot_pts, 12, close_tip=False)
    # achatar sola (z min -> 0.004) e topo arqueado
    for idx in range(fb, len(nv)):
        x, y, z = nv[idx]
        if z < 0.020: z = 0.006 + (z - 0.006) * 0.25
        nv[idx] = (x, y, z)
    # 5 dedos do pe
    for tnum in range(5):
        ox = cx + g * (0.026 - tnum * 0.0125)
        r = 0.0085 - tnum * 0.0009
        L = 0.030 - tnum * 0.0035
        pts = [((ox, -0.118, 0.014), r), ((ox, -0.118 - L, 0.011), r*0.85)]
        tube(nv, nf, pts, 8)

# aplicar ao mesh: juntar geometria nova
bm = bmesh.new()
bm.from_mesh(me)
vmap = []
for v in nv:
    vmap.append(bm.verts.new(v))
bm.verts.index_update()
for f in nf:
    try:
        bm.faces.new([vmap[i] for i in f])
    except ValueError:
        pass
bm.to_mesh(me)
bm.free()
me.update()

# ===== ROSTO: olhos (esferas separadas) + cavidades/labios via verts do tubo =====
NSEG, NRING = 32, 84
for k in range(NRING):
    t = 0.005 + (0.495 - 0.005) * k / (NRING - 1)
    if not (0.055 < t < 0.135): continue
    z = H * (1 - t)
    for i in range(NSEG):
        idx = k * NSEG + i
        if idx >= NSEG * NRING: break
        v = me.vertices[idx]
        x, y = v.co.x, v.co.y
        if y > -0.01: continue  # so face frontal
        # ORBITAS: cavidade leve nos olhos (t 0.068-0.082, x +-0.024)
        orb = math.exp(-((t - 0.075) / 0.007) ** 2) * math.exp(-((abs(x) - 0.024) / 0.011) ** 2)
        v.co.y += 0.0048 * orb
        # SULCO da boca (t ~0.112) + labios rolinho
        lip = math.exp(-((t - 0.110) / 0.004) ** 2) * math.exp(-(x / 0.016) ** 2)
        v.co.y -= 0.0028 * lip
        philtrum = math.exp(-((t - 0.103) / 0.0035) ** 2) * math.exp(-(x / 0.005) ** 2)
        v.co.y += 0.0015 * philtrum
me.update()

# olhos: 2 esferas brancas + iris
m_eye = bpy.data.materials.get('MAT_Eye')
if not m_eye:
    m_eye = bpy.data.materials.new('MAT_Eye'); m_eye.use_nodes = True
    eb = m_eye.node_tree.nodes.get('Principled BSDF')
    eb.inputs['Base Color'].default_value = (0.88, 0.87, 0.86, 1)
    eb.inputs['Roughness'].default_value = 0.15
m_iris = bpy.data.materials.get('MAT_Iris')
if not m_iris:
    m_iris = bpy.data.materials.new('MAT_Iris'); m_iris.use_nodes = True
    ib = m_iris.node_tree.nodes.get('Principled BSDF')
    ib.inputs['Base Color'].default_value = (0.13, 0.07, 0.04, 1)
    ib.inputs['Roughness'].default_value = 0.25
z_eye = H * (1 - 0.075)
for g in (1, -1):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=14, ring_count=10, radius=0.0115,
        location=(g*0.0235, -0.0445, z_eye))
    eye = bpy.context.object; eye.name = f'F_Eye_{"L" if g>0 else "R"}'
    eye.data.materials.append(m_eye)
    bpy.ops.object.shade_smooth()
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.0052,
        location=(g*0.0235, -0.0545, z_eye))
    ir = bpy.context.object; ir.name = f'F_Iris_{"L" if g>0 else "R"}'
    ir.scale = (1, 0.45, 1)
    ir.data.materials.append(m_iris)
    bpy.ops.object.shade_smooth()
    # sobrancelha
    bpy.ops.mesh.primitive_cube_add(size=1, location=(g*0.0245, -0.0560, z_eye + 0.017))
    br = bpy.context.object; br.name = f'F_Brow_{"L" if g>0 else "R"}'
    br.scale = (0.017, 0.004, 0.0035)
    br.rotation_euler = (0, 0, g*math.radians(-8))
    mb = bpy.data.materials.get('MAT_HHair')
    if not mb:
        mb = bpy.data.materials.new('MAT_HHair'); mb.use_nodes = True
        hb = mb.node_tree.nodes.get('Principled BSDF')
        hb.inputs['Base Color'].default_value = (0.015, 0.012, 0.012, 1)
        hb.inputs['Roughness'].default_value = 0.6
    br.data.materials.append(mb)
# orelhas: 2 meio-toros
for g in (1, -1):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.013, minor_radius=0.005,
        location=(g*0.0560, -0.010, H*(1-0.085)), rotation=(0, math.radians(90), 0))
    ear = bpy.context.object; ear.name = f'F_Ear_{"L" if g>0 else "R"}'
    ear.scale = (1, 0.7, 1.25)
    ear.data.materials.append(skin)
    bpy.ops.object.shade_smooth()
# labios material (paint polys da zona)
m_lip = bpy.data.materials.get('MAT_HLips')
if not m_lip:
    m_lip = bpy.data.materials.new('MAT_HLips'); m_lip.use_nodes = True
    lb = m_lip.node_tree.nodes.get('Principled BSDF')
    lb.inputs['Base Color'].default_value = (0.55, 0.28, 0.27, 1)
    lb.inputs['Roughness'].default_value = 0.32
if len(me.materials) < 2:
    me.materials.append(m_lip)
z_lip = H * (1 - 0.110)
nlip = 0
for poly in me.polygons:
    c = poly.center
    if abs(c.x) < 0.014 and c.y < -0.052 and abs(c.z - z_lip) < 0.008:
        poly.material_index = 1; nlip += 1

bpy.ops.wm.save_mainfile()
print(f'EXTREMIDADES: +{len(nv)} verts (maos 5 dedos x2, pes 5 dedos x2), rosto: olhos/iris/brows/orelhas/labios({nlip})')
