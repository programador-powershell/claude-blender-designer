import bpy, math

# fix claviculas osseas pra dentro
for S in ['L','R']:
    o = bpy.data.objects.get(f'OS_Clavicula_{S}')
    if o:
        for v in o.data.vertices:
            v.co.y += 0.014
        o.data.update()

# ===== ARMATURE NOVO (design 129 validado E2, coords do corpo NOVO) =====
arm_data = bpy.data.armatures.new('HRig')
rig = bpy.data.objects.new('HRig', arm_data)
bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
for o in bpy.data.objects: o.select_set(False)
rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones

def B(name, head, tail, parent=None, connect=False, deform=True):
    b = eb.new(name)
    b.head = head; b.tail = tail
    if parent: b.parent = eb[parent]; b.use_connect = connect
    b.use_deform = deform
    return b

B('Root', (0,0,0), (0,0.12,0), None, False, False)
B('Hips', (0,0.015,0.94), (0,0.010,1.01), 'Root')
B('Spine1', (0,0.010,1.01), (0,0.004,1.11), 'Hips', True)
B('Spine2', (0,0.004,1.11), (0,-0.002,1.22), 'Spine1', True)
B('Spine3', (0,-0.002,1.22), (0,0.002,1.37), 'Spine2', True)
B('Neck', (0,0.005,1.435), (0,0.000,1.515), 'Spine3')
B('Head', (0,0.000,1.515), (0,-0.005,1.695), 'Neck', True)
B('Jaw', (0,-0.020,1.530), (0,-0.085,1.505), 'Head')
B('Eye_L', (0.030,-0.075,1.5725), (0.030,-0.105,1.5725), 'Head')
B('Eye_R', (-0.030,-0.075,1.5725), (-0.030,-0.105,1.5725), 'Head')

# bracos (coords do corpo novo: ombro 0.150, cotovelo 0.318, pulso 0.498)
for S, g in [('L',1),('R',-1)]:
    B(f'Clavicle_{S}', (g*0.015,-0.030,1.408), (g*0.135,-0.012,1.412), 'Spine3')
    B(f'UpperArm_{S}', (g*0.150,0.005,1.400), (g*0.318,0.011,1.342), f'Clavicle_{S}')
    B(f'UpperArmTwist_{S}', (g*0.234,0.008,1.371), (g*0.318,0.011,1.342), f'UpperArm_{S}', False)
    B(f'ForeArm_{S}', (g*0.318,0.011,1.342), (g*0.498,0.016,1.279), f'UpperArm_{S}', True)
    B(f'ForeArmTwist_{S}', (g*0.408,0.014,1.310), (g*0.498,0.016,1.279), f'ForeArm_{S}', False)
    B(f'Hand_{S}', (g*0.498,0.016,1.279), (g*0.560,0.018,1.255), f'ForeArm_{S}', True)
    # dedos: bases nas posicoes da mao nova (knuckle = pulso + dir*0.078)
    import mathutils
    dirv = mathutils.Vector((g*0.345, 0.012, -0.125)).normalized()
    wri = mathutils.Vector((g*0.498, 0.016, 1.279))
    kn = wri + dirv*0.078
    fingers = [('Index',-0.0165,0.030),('Middle',-0.0055,0.033),('Ring',0.0055,0.030),('Pinky',0.0165,0.024)]
    for fn, oy, seg in fingers:
        p = kn + mathutils.Vector((0, oy, 0))
        prev = f'Hand_{S}'; con = False
        d = mathutils.Vector(dirv)
        for k2 in range(1,4):
            L = seg*(1.0 if k2==1 else 0.72 if k2==2 else 0.55)
            d = (d + mathutils.Vector((0,0,-0.10))).normalized()
            np_ = p + d*L
            B(f'{fn}{k2}_{S}', tuple(p), tuple(np_), prev, con)
            prev = f'{fn}{k2}_{S}'; con = True
            p = np_
    # polegar
    tb0 = mathutils.Vector((g*0.498, 0.016-0.026, 1.279-0.006)) + dirv*0.020
    td = (dirv + mathutils.Vector((0,-0.85,-0.18))).normalized()
    p = tb0; prev = f'Hand_{S}'; con = False
    for k2, L in [(1,0.030),(2,0.026),(3,0.020)]:
        np_ = p + td*L
        B(f'Thumb{k2}_{S}', tuple(p), tuple(np_), prev, con)
        prev = f'Thumb{k2}_{S}'; con = True
        p = np_
        td = (td + mathutils.Vector((g*0.15,0,-0.05))).normalized()

# pernas (corpo novo: coxa cx 0.095, joelho 0.508, tornozelo 0.115 cy 0.038)
for S, g in [('L',1),('R',-1)]:
    B(f'Thigh_{S}', (g*0.092,0.018,0.920), (g*0.094,0.008,0.508), 'Hips')
    B(f'ThighTwist_{S}', (g*0.093,0.013,0.715), (g*0.094,0.008,0.508), f'Thigh_{S}', False)
    B(f'Shin_{S}', (g*0.094,0.008,0.508), (g*0.112,0.038,0.115), f'Thigh_{S}', True)
    B(f'ShinTwist_{S}', (g*0.103,0.023,0.310), (g*0.112,0.038,0.115), f'Shin_{S}', False)
    B(f'Foot_{S}', (g*0.112,0.038,0.115), (g*0.110,-0.080,0.030), f'Shin_{S}', True)
    B(f'Toe_{S}', (g*0.110,-0.080,0.030), (g*0.110,-0.140,0.022), f'Foot_{S}', True)
    B(f'Heel_{S}', (g*0.112,0.038,0.115), (g*0.112,0.075,0.012), f'Foot_{S}', False, False)

# jiggle + skirt + hair + acessorios (estrutura p/ roupas modulares)
B('Breast_L', (0.045,-0.060,1.275), (0.050,-0.110,1.262), 'Spine3')
B('Breast_R', (-0.045,-0.060,1.275), (-0.050,-0.110,1.262), 'Spine3')
B('Butt_L', (0.050,0.065,0.945), (0.055,0.105,0.915), 'Hips')
B('Butt_R', (-0.050,0.065,0.945), (-0.055,0.105,0.915), 'Hips')
B('Belly', (0,-0.040,1.020), (0,-0.070,0.995), 'Hips')
for i, ang in enumerate(range(0, 360, 45)):
    a = math.radians(ang)
    dx, dy = math.sin(a), -math.cos(a)
    nm = f'Skirt{i}'
    B(f'{nm}_1', (dx*0.12, dy*0.12+0.02, 1.000), (dx*0.19, dy*0.19+0.025, 0.860), 'Hips')
    B(f'{nm}_2', (dx*0.19, dy*0.19+0.025, 0.860), (dx*0.27, dy*0.27+0.03, 0.690), f'{nm}_1', True)
chains = [('HairF',0.00,-0.075,1.660,0.00,-0.02),('HairL1',0.080,-0.028,1.640,0.035,0.01),
          ('HairL2',0.090,0.045,1.620,0.030,0.02),('HairR1',-0.080,-0.028,1.640,-0.035,0.01),
          ('HairR2',-0.090,0.045,1.620,-0.030,0.02),('HairB1',0.038,0.090,1.620,0.010,0.015),
          ('HairB2',-0.038,0.090,1.620,-0.010,0.015)]
for nm, x0, y0, z0, dx, dy in chains:
    px, py, pz = x0, y0, z0
    prev, con = 'Head', False
    for k in range(1,5):
        nx, ny, nz = px+dx, py+dy, pz-0.16
        B(f'{nm}_{k}', (px,py,pz), (nx,ny,nz), prev, con)
        prev, con = f'{nm}_{k}', True
        px, py, pz = nx, ny, nz
B('HatBase', (0.045,0.0,1.695), (0.052,0.0,1.755), 'Head')
B('HatTop', (0.052,0.0,1.755), (0.058,0.0,1.815), 'HatBase', True)
B('BowKnot', (0,0.14,1.01), (0,0.19,1.01), 'Hips')
B('BowL', (0.015,0.15,1.015), (0.110,0.17,1.035), 'BowKnot')
B('BowR', (-0.015,0.15,1.015), (-0.110,0.17,1.035), 'BowKnot')
B('Watch', (0.14,-0.05,0.96), (0.155,-0.075,0.91), 'Hips')
B('WatchChain1', (0.12,-0.01,1.01), (0.13,-0.03,0.985), 'Hips')
B('WatchChain2', (0.13,-0.03,0.985), (0.14,-0.05,0.96), 'WatchChain1', True)
B('CardHat', (0.045,-0.048,1.725), (0.045,-0.056,1.760), 'HatBase')
for S, g in [('L',1),('R',-1)]:
    B(f'Sleeve{S}_1', (g*0.185,0.008,1.395), (g*0.240,0.009,1.415), f'UpperArm_{S}')
    B(f'Sleeve{S}_2', (g*0.205,0.008,1.355), (g*0.260,0.009,1.338), f'UpperArm_{S}')
B('Choker', (0,-0.040,1.450), (0,-0.060,1.465), 'Neck')
bpy.ops.object.mode_set(mode='OBJECT')
n_bones = len(arm_data.bones)

# ===== BIND OSSOS MESH -> BONES (raio-X animavel) =====
import re
bone_map = {
    'OS_Cranio':'Head','OS_Mandibula':'Jaw','OS_Sacro':'Hips','OS_Esterno':'Spine3',
    'OS_Iliaco_L':'Hips','OS_Iliaco_R':'Hips',
    'OS_Clavicula_L':'Clavicle_L','OS_Clavicula_R':'Clavicle_R',
    'OS_Escapula_L':'Clavicle_L','OS_Escapula_R':'Clavicle_R',
    'OS_Umero_L':'UpperArm_L','OS_Umero_R':'UpperArm_R',
    'OS_Radio_L':'ForeArm_L','OS_Radio_R':'ForeArm_R',
    'OS_Ulna_L':'ForeArm_L','OS_Ulna_R':'ForeArm_R',
    'OS_Femur_L':'Thigh_L','OS_Femur_R':'Thigh_R',
    'OS_ColoFemur_L':'Thigh_L','OS_ColoFemur_R':'Thigh_R',
    'OS_Patela_L':'Shin_L','OS_Patela_R':'Shin_R',
    'OS_Tibia_L':'Shin_L','OS_Tibia_R':'Shin_R',
    'OS_Fibula_L':'Shin_L','OS_Fibula_R':'Shin_R',
    'OS_Calcaneo_L':'Foot_L','OS_Calcaneo_R':'Foot_R',
}
col = bpy.data.collections.get('Esqueleto')
n_bound = 0
for ob in col.objects:
    nm = ob.name
    bone = bone_map.get(nm)
    if not bone:
        if nm.startswith('OS_Vert_') or nm.startswith('OS_Proc_'):
            tipo = nm.split('_')[2][0]
            num = int(re.findall(r'\d+', nm)[0])
            if tipo == 'C': bone = 'Neck'
            elif tipo == 'T': bone = 'Spine3' if num <= 8 else 'Spine2'
            else: bone = 'Spine1'
        elif nm.startswith('OS_Costela'):
            num = int(nm.split('_')[2])
            bone = 'Spine3' if num <= 7 else 'Spine2'
        elif nm.startswith('OS_Meta'):
            bone = 'Toe_L' if nm.endswith('_L') else 'Toe_R'
        else:
            bone = 'Hips'
    ob.vertex_groups.clear()
    vg = ob.vertex_groups.new(name=bone)
    vg.add([v.index for v in ob.data.vertices], 1.0, 'REPLACE')
    am = ob.modifiers.new('Armature','ARMATURE'); am.object = rig
    bpy.context.view_layer.update()
    mw0 = ob.matrix_world.copy()
    ob.parent = rig; ob.matrix_world = mw0
    n_bound += 1

# face parts -> Head
for ob in bpy.data.objects:
    if ob.name.startswith('F_'):
        ob.vertex_groups.clear()
        bone = 'Eye_L' if 'Iris_L' in ob.name or 'Eye_L' in ob.name else ('Eye_R' if 'Iris_R' in ob.name or 'Eye_R' in ob.name else 'Head')
        vg = ob.vertex_groups.new(name=bone)
        vg.add([v.index for v in ob.data.vertices], 1.0, 'REPLACE')
        am = ob.modifiers.new('Armature','ARMATURE'); am.object = rig
        bpy.context.view_layer.update()
        mw0 = ob.matrix_world.copy()
        ob.parent = rig; ob.matrix_world = mw0

# ===== SKINNING corpo (proximity 3-bone, bones de corpo) =====
body = bpy.data.objects['HumanBody']
prefixes = ('Hips','Spine','Neck','Head','Jaw','Clavicle','UpperArm','ForeArm','Hand',
    'Thumb','Index','Middle','Ring','Pinky','Thigh','Shin','Foot','Toe','Breast','Butt','Belly')
segs = []
for b in rig.data.bones:
    if not b.use_deform or not b.name.startswith(prefixes): continue
    h = rig.matrix_world @ b.head_local
    t = rig.matrix_world @ b.tail_local
    segs.append((b.name, h, t, (t-h), max((t-h).length_squared, 1e-12)))
body.vertex_groups.clear()
vgs = {}
mw = body.matrix_world
for v in body.data.vertices:
    p = mw @ v.co
    ds = []
    for n, h, t, ab, L2 in segs:
        tt = max(0.0, min(1.0, (p-h).dot(ab)/L2))
        ds.append(((p-(h+ab*tt)).length, n))
    ds.sort()
    ws = [(1.0/max(d,1e-5)**2, n) for d, n in ds[:3]]
    s = sum(w for w,_ in ws)
    for w, n in ws:
        if n not in vgs: vgs[n] = body.vertex_groups.new(name=n)
        vgs[n].add([v.index], w/s, 'REPLACE')
am = body.modifiers.new('Armature','ARMATURE'); am.object = rig
bpy.context.view_layer.update()
mw0 = body.matrix_world.copy()
body.parent = rig; body.matrix_world = mw0
# smooth
bpy.context.view_layer.objects.active = body
for o in bpy.data.objects: o.select_set(False)
body.select_set(True)
bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
bpy.ops.object.vertex_group_smooth(group_select_mode='ALL', factor=0.5, repeat=6, expand=0.35)
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
bpy.ops.object.mode_set(mode='OBJECT')

bpy.ops.wm.save_mainfile()
print(f'RIG: {n_bones} bones | ossos bound: {n_bound} | corpo skinned')
