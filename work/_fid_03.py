import bpy, math
from mathutils import Vector

rig = bpy.data.objects['AliceRig']
body = bpy.data.objects['AliceMesh']

# ===== 1. LUVAS: proximity skinning (UpperArm+ForeArm+Hand) =====
segs = []
for b in rig.data.bones:
    if not b.use_deform: continue
    segs.append((b.name, rig.matrix_world @ b.head_local, rig.matrix_world @ b.tail_local))
def dseg(p,a,bb):
    ab = bb-a; L2 = ab.length_squared
    if L2<1e-12: return (p-a).length
    t = max(0.0,min(1.0,(p-a).dot(ab)/L2))
    return (p-(a+ab*t)).length

for S in ['L','R']:
    ob = bpy.data.objects.get(f'GD_Luva_{S}')
    if not ob: continue
    allowed = {f'UpperArm_{S}', f'UpperArmTwist_{S}', f'ForeArm_{S}', f'ForeArmTwist_{S}', f'Hand_{S}'}
    sub = [(n,h,t) for n,h,t in segs if n in allowed]
    ob.vertex_groups.clear()
    vgs = {}
    mw = ob.matrix_world
    for v in ob.data.vertices:
        wp = mw @ v.co
        d = sorted(((dseg(wp,h,t),n) for n,h,t in sub))[:2]
        ws = [(1.0/max(di,1e-5)**2,n) for di,n in d]
        s = sum(w for w,_ in ws)
        for w,n in ws:
            if n not in vgs: vgs[n] = ob.vertex_groups.new(name=n)
            vgs[n].add([v.index], w/s, 'REPLACE')
    if not any(m.type=='ARMATURE' for m in ob.modifiers):
        am = ob.modifiers.new('Armature','ARMATURE'); am.object = rig
        ob.parent = rig

# ===== 2. CORPETE + TRIMS: weights so Spine (sem braco puxando) =====
spine_only = {'Spine','Spine1','Spine2','Hips'}
for nm in ['GD_Corpete','GD_Trim_Top','GD_Trim_Waist']:
    ob = bpy.data.objects.get(nm)
    if not ob: continue
    sub = [(n,h,t) for n,h,t in segs if n in spine_only]
    ob.vertex_groups.clear()
    vgs = {}
    mw = ob.matrix_world
    for v in ob.data.vertices:
        wp = mw @ v.co
        d = sorted(((dseg(wp,h,t),n) for n,h,t in sub))[:2]
        ws = [(1.0/max(di,1e-5)**2,n) for di,n in d]
        s = sum(w for w,_ in ws)
        for w,n in ws:
            if n not in vgs: vgs[n] = ob.vertex_groups.new(name=n)
            vgs[n].add([v.index], w/s, 'REPLACE')

# saias tambem: so Hips/Spine/Skirt bones (sem perna puxando lateral)
skirt_ok = {'Hips','Spine','SkirtF','SkirtB','SkirtL','SkirtR','Butt_L','Butt_R'}
for nm in ['GD_Saia_Lace','GD_Saia_Cream','GD_Saia_Teal_T1','GD_Saia_Teal_T2']:
    ob = bpy.data.objects.get(nm)
    if not ob: continue
    sub = [(n,h,t) for n,h,t in segs if n in skirt_ok]
    ob.vertex_groups.clear()
    vgs = {}
    mw = ob.matrix_world
    for v in ob.data.vertices:
        wp = mw @ v.co
        d = sorted(((dseg(wp,h,t),n) for n,h,t in sub))[:3]
        ws = [(1.0/max(di,1e-5)**2,n) for di,n in d]
        s = sum(w for w,_ in ws)
        for w,n in ws:
            if n not in vgs: vgs[n] = ob.vertex_groups.new(name=n)
            vgs[n].add([v.index], w/s, 'REPLACE')

# ===== 3. MATERIAL: teal um pouco mais legivel (luz le verde, nao preto) =====
m_teal = bpy.data.materials['MAT_TealDamask']
nt = m_teal.node_tree
ramp = next((n for n in nt.nodes if n.type=='VALTORGB'), None)
if ramp:
    ramp.color_ramp.elements[0].color = (0.018, 0.042, 0.028, 1)
    ramp.color_ramp.elements[1].color = (0.048, 0.105, 0.068, 1)

# ===== 4. PES do corpo: encolher pra dentro das botas =====
for v in body.data.vertices:
    if v.co.z < 0.075:
        cx = 0.101 if v.co.x > 0 else -0.101
        v.co.x = cx + (v.co.x - cx) * 0.55
        v.co.y = -0.01 + (v.co.y + 0.01) * 0.55
body.data.update()
# pe da bota maior cobre
for S, g in [('L',1),('R',-1)]:
    pe = bpy.data.objects.get(f'GD_Bota_Pe_{S}')
    if pe:
        pe.scale = (0.085, 0.155, 0.052)
        pe.location = (g*0.101, -0.050, 0.040)

# ===== 5. CHAPEU: descer no cabelo =====
for nm, dz in [('GD_Chapeu_Copa',-0.022),('GD_Chapeu_Aba',-0.022),('GD_Chapeu_Banda',-0.022)]:
    o = bpy.data.objects.get(nm)
    if o: o.location.z += dz

# ===== 6. LUZ: fill lateral pra ler material =====
fill = bpy.data.objects.get('L_FILL')
if fill: fill.data.energy = 150
key = bpy.data.objects.get('L_KEY')
if key: key.data.energy = 400

bpy.ops.wm.save_mainfile()
print('CICLO 3 OK')
