import bpy, math
from mathutils import Vector

# ===== A. CORES: verde escuro rico (ref quase-preto esverdeado) =====
m_teal = bpy.data.materials['MAT_TealDamask']
nt = m_teal.node_tree
ramp = next((n for n in nt.nodes if n.type=='VALTORGB'), None)
if ramp:
    ramp.color_ramp.elements[0].color = (0.012, 0.030, 0.020, 1)
    ramp.color_ramp.elements[1].color = (0.030, 0.065, 0.042, 1)
else:
    b = nt.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (0.020, 0.045, 0.030, 1)

m_cream = bpy.data.materials['MAT_CreamL']
b = m_cream.node_tree.nodes.get('Principled BSDF')
b.inputs['Base Color'].default_value = (0.62, 0.55, 0.42, 1)  # cream envelhecido

# ===== B. SAIA: encurtar + silhueta ref (volume alto, hem acima joelho) =====
def reshape(name, scale_z_factor, hem_min_z):
    ob = bpy.data.objects.get(name)
    if not ob: return
    for v in ob.data.vertices:
        # comprimir verticalmente a partir da cintura (z~1.05)
        v.co.z = 1.05 - (1.05 - v.co.z) * scale_z_factor
        if v.co.z < hem_min_z - 0.06:
            v.co.z = hem_min_z - 0.06 + (v.co.z - (hem_min_z-0.06))*0.3
    ob.data.update()

reshape('GD_Saia_Lace', 0.82, 0.62)    # lace interna: hem ~0.62
reshape('GD_Saia_Cream', 0.80, 0.66)   # cream: ~0.66
reshape('GD_Saia_Teal_T1', 0.95, 0.86)
reshape('GD_Saia_Teal_T2', 0.85, 0.72) # teal: ~0.72

# ===== C. MANGAS menores + LUVAS longas =====
for S, g in [('L',1),('R',-1)]:
    m = bpy.data.objects.get(f'GD_Manga_{S}')
    if m:
        # encolher raio (escala radial em torno do eixo do braco z=1.375)
        for v in m.data.vertices:
            v.co.y *= 0.72
            v.co.z = 1.375 + (v.co.z - 1.375) * 0.72
            # encurtar span
            v.co.x = g*0.155 + (v.co.x - g*0.155) * 0.80
        m.data.update()
    l = bpy.data.objects.get(f'GD_Luva_{S}')
    if l:
        # alongar luva: comeca mais perto do ombro (acima do cotovelo ref)
        for v in l.data.vertices:
            v.co.x = g*0.27 + (v.co.x - g*0.330) * 1.25
        l.data.update()

# ===== D. BOTAS plataforma alta =====
for S, g in [('L',1),('R',-1)]:
    c = bpy.data.objects.get(f'GD_Bota_Cano_{S}')
    if c:
        for v in c.data.vertices:
            v.co.z = v.co.z * 1.22  # cano sobe ate ~0.44
            # engrossar
            v.co.x = g*0.100 + (v.co.x - g*0.100) * 1.12
            v.co.y = 0.039 + (v.co.y - 0.039) * 1.12
        c.data.update()
    pe = bpy.data.objects.get(f'GD_Bota_Pe_{S}')
    if pe:
        pe.scale.z *= 1.5  # plataforma grossa
        pe.location.z += 0.012

# ===== E. CABELO: volume + ondas =====
hm = bpy.data.objects.get('GD_Cabelo_Massa')
if hm:
    for v in hm.data.vertices:
        v.co.x *= 1.35
        v.co.y = 0.08 + (v.co.y - 0.08) * 1.25
        # ondas
        v.co.x += 0.018 * math.sin(9 * v.co.z * 3.5)
    hm.data.update()
cal = bpy.data.objects.get('GD_Cabelo_Calota')
if cal:
    cal.scale = (1.08, 1.12, 1.05)
for S, g in [('L',1),('R',-1)]:
    mc = bpy.data.objects.get(f'GD_Mecha_{S}')
    if mc:
        for v in mc.data.vertices:
            v.co.x = g*0.085 + (v.co.x - g*0.085) * 1.6
            # alongar ate o peito
            v.co.z = 1.56 - (1.56 - v.co.z) * 1.55
        mc.data.update()

# ===== F. CHAPEU mais alto =====
cp = bpy.data.objects.get('GD_Chapeu_Copa')
if cp:
    cp.scale.z *= 1.35
    cp.location.z += 0.015
bd = bpy.data.objects.get('GD_Chapeu_Banda')
if bd: bd.location.z -= 0.004

bpy.ops.wm.save_mainfile()
print('CICLO 1 APLICADO')
