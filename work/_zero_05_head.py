import bpy, math

m_gold = bpy.data.materials['MAT_Gold']
m_tealD = bpy.data.materials['MAT_TealDamask']
m_hair = bpy.data.materials.get('MAT_HairB')
if not m_hair:
    m_hair = bpy.data.materials.new('MAT_HairB'); m_hair.use_nodes = True
    b = m_hair.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (0.018, 0.015, 0.016, 1)
    b.inputs['Roughness'].default_value = 0.38

# ===== 12 CABELO =====
# Calota (scalp)
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.092,
    location=(0, 0.005, 1.565))
scalp = bpy.context.object; scalp.name = 'PA12_Cabelo_Calota'
scalp.scale = (1.0, 1.08, 1.05)
scalp.data.materials.append(m_hair)
bpy.ops.object.shade_smooth()

# Massa traseira (cabelo longo ondulado caindo ate cintura)
SEG = 32
verts=[]; faces=[]
secs = [
    (1.58, 0.085, 0.055, 0.012),
    (1.46, 0.105, 0.075, 0.018),
    (1.30, 0.115, 0.085, 0.025),
    (1.12, 0.110, 0.080, 0.030),
    (0.98, 0.095, 0.065, 0.035),
]
for (z, rx, ry, wav) in secs:
    for i in range(SEG):
        a = math.pi*0.15 + math.pi*0.7 * i/(SEG-1)   # arco atras
        rr = 1.0 + wav * math.sin(7*a + z*9)
        verts.append((rx*rr*math.cos(a+math.pi/2)*1.6 - rx*0.8*math.cos(a+math.pi/2)*0.6,
                      0.02 + ry*rr*math.sin(a*0.5)*1.2 + 0.05,
                      z))
# simplificar: regenerar com arco simples atras
verts=[]
for (z, rx, ry, wav) in secs:
    for i in range(SEG):
        t = i/(SEG-1)
        a = math.pi * (0.12 + 0.76*t)   # de +x atras ate -x atras
        rr = 1.0 + wav * math.sin(9*a + z*8)
        x = rx * rr * math.cos(a)
        y = 0.035 + ry * rr * abs(math.sin(a)) * 0.9 + 0.02
        verts.append((x, y, z))
for s in range(len(secs)-1):
    for i in range(SEG-1):
        a0=s*SEG+i; b0=a0+1; c0=(s+1)*SEG+i+1; d0=(s+1)*SEG+i
        faces.append((a0,b0,c0,d0))
me = bpy.data.meshes.new('PA12_Cabelo_Massa_Mesh')
me.from_pydata(verts, [], faces); me.update()
hm = bpy.data.objects.new('PA12_Cabelo_Massa', me)
bpy.context.scene.collection.objects.link(hm)
hm.data.materials.append(m_hair)
s = hm.modifiers.new('Sol','SOLIDIFY'); s.thickness = 0.025
bpy.context.view_layer.objects.active = hm
for o in bpy.data.objects: o.select_set(False)
hm.select_set(True); bpy.ops.object.shade_smooth()

# Mechas frontais (2 tubos curvos)
for sgn in [1,-1]:
    verts=[]; faces=[]
    pts = [(sgn*0.075, -0.045, 1.56), (sgn*0.095, -0.045, 1.42), (sgn*0.090, -0.030, 1.26)]
    R = 0.022; S2 = 10
    for pi_, (x,y,z) in enumerate(pts):
        for i in range(S2):
            a = 2*math.pi*i/S2
            verts.append((x + R*math.cos(a)*(1-pi_*0.25), y + R*math.sin(a)*(1-pi_*0.25), z))
    for s_ in range(len(pts)-1):
        for i in range(S2):
            j=(i+1)%S2
            faces.append((s_*S2+i, s_*S2+j, (s_+1)*S2+j, (s_+1)*S2+i))
    me = bpy.data.meshes.new(f'PA12_Mecha_{sgn}_Mesh')
    me.from_pydata(verts, [], faces); me.update()
    ob = bpy.data.objects.new(f'PA12_Mecha_{"L" if sgn>0 else "R"}', me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(m_hair)
    bpy.context.view_layer.objects.active = ob
    for o in bpy.data.objects: o.select_set(False)
    ob.select_set(True); bpy.ops.object.shade_smooth()

# ===== 13 CHAPEU MINI TOP HAT (inclinado, banda gold) =====
import mathutils
hat_loc = (0.045, -0.01, 1.685)
hat_rot = (0, math.radians(-12), 0)
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.062, depth=0.085, location=hat_loc, rotation=hat_rot)
crown = bpy.context.object; crown.name = 'PA13_Chapeu_Copa'
crown.data.materials.append(m_tealD)
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.095, depth=0.008,
    location=(hat_loc[0]-0.009, hat_loc[1], hat_loc[2]-0.044), rotation=hat_rot)
brim = bpy.context.object; brim.name = 'PA13_Chapeu_Aba'
brim.data.materials.append(m_tealD)
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.064, depth=0.018,
    location=(hat_loc[0]-0.004, hat_loc[1], hat_loc[2]-0.026), rotation=hat_rot)
band = bpy.context.object; band.name = 'PA13_Chapeu_Banda'
band.data.materials.append(m_gold)

# ===== 14 ACESSORIOS: relogio + chave + cartas =====
# Relogio de bolso pendurado na cintura direita
bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.028, depth=0.010,
    location=(-0.13, -0.07, 0.99), rotation=(math.radians(90), 0, 0))
watch = bpy.context.object; watch.name = 'PA14_Relogio'
watch.data.materials.append(m_gold)
# Chave colar
bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.004, depth=0.045,
    location=(0.02, -0.105, 1.30), rotation=(math.radians(90), 0, 0))
key = bpy.context.object; key.name = 'PA14_Chave'
key.data.materials.append(m_gold)
bpy.ops.mesh.primitive_torus_add(major_radius=0.010, minor_radius=0.003,
    location=(0.02, -0.105, 1.325), rotation=(math.radians(90), 0, 0))
keyb = bpy.context.object; keyb.name = 'PA14_Chave_Argola'
keyb.data.materials.append(m_gold)
# 3 cartas miniatura penduradas
m_card = bpy.data.materials.get('MAT_Card')
if not m_card:
    m_card = bpy.data.materials.new('MAT_Card'); m_card.use_nodes = True
    b = m_card.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (0.82, 0.78, 0.67, 1)
    b.inputs['Roughness'].default_value = 0.7
for k in range(3):
    bpy.ops.mesh.primitive_plane_add(size=0.035, location=(0.12 + k*0.012, -0.075, 0.97 - k*0.012),
        rotation=(math.radians(80), 0, math.radians(k*15)))
    card = bpy.context.object; card.name = f'PA14_Carta_{k}'
    card.scale = (0.7, 1.0, 1.0)
    card.data.materials.append(m_card)

print('HEAD+ACC OK:', [o.name for o in bpy.data.objects if o.name.startswith(('PA12','PA13','PA14'))])
