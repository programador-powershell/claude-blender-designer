import bpy, math
from mathutils import Vector

body = bpy.data.objects['AliceMesh']
rig = bpy.data.objects['AliceRig']

# Desparentar + limpar weights errados
body.parent = None
for m in list(body.modifiers): body.modifiers.remove(m)
body.vertex_groups.clear()

# Rotacionar mesh DATA pra Z-up: +90 graus X
body.rotation_euler = (math.radians(90), 0, 0)
bpy.context.view_layer.objects.active = body
for o in bpy.data.objects: o.select_set(False)
body.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
zs = [v.co.z for v in body.data.vertices]
ys = [v.co.y for v in body.data.vertices]
xs = [v.co.x for v in body.data.vertices]
print(f'pos-rot bbox: x[{min(xs):.2f},{max(xs):.2f}] y[{min(ys):.2f},{max(ys):.2f}] z[{min(zs):.2f},{max(zs):.2f}]')
# Chao + centro
body.location.z = -min(zs)
body.location.y = -(min(ys)+max(ys))/2
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Medidas por fatia (agora Z-up correto)
def stats(z_lo, z_hi):
    pts = [v.co for v in body.data.vertices if z_lo <= v.co.z <= z_hi]
    if not pts: return None
    xs = [p.x for p in pts]; ys = [p.y for p in pts]
    return {'x_max': max(xs), 'x_min': min(xs), 'y_min': min(ys), 'y_max': max(ys)}
sh = stats(1.34, 1.42)
hips = stats(0.92, 1.00)
print('shoulders:', sh)
print('hips:', hips)
shoulder_x = sh['x_max']*0.90 if sh else 0.17

# Reposicionar bones bracos/clavicula conforme largura real
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
EB = rig.data.edit_bones
SX = shoulder_x
for S, g in [('L',1),('R',-1)]:
    if f'Clavicle_{S}' in EB:
        EB[f'Clavicle_{S}'].tail = Vector((g*SX, 0, 1.375))
        arm_chain = ['UpperArm','UpperArmTwist','ForeArm','ForeArmTwist','Hand']
        # arm span ate ponta mao: usar x_max real do corpo em z braco
        arm_slice = stats(1.30, 1.45)
        tip = arm_slice['x_max']*0.99 if arm_slice else SX+0.54
        seg = (tip - SX) / 5.0
        x = SX
        for bn in arm_chain:
            b = EB[f'{bn}_{S}']
            b.head = Vector((g*x, 0, 1.375))
            x += seg
            b.tail = Vector((g*x, 0, 1.375))
        # dedos: comecam na ponta da mao
        fingers = [('Thumb',-0.030),('Index',-0.015),('Middle',0.0),('Ring',0.014),('Pinky',0.027)]
        for fname, yoff in fingers:
            l = 0.022
            xx = x
            for k in range(1,4):
                b = EB[f'{fname}{k}_{S}']
                b.head = Vector((g*xx, yoff, 1.375))
                xx += l*(1.0-0.2*(k-1))
                b.tail = Vector((g*xx, yoff, 1.375))
bpy.ops.object.mode_set(mode='OBJECT')
print('bones realinhados ao corpo real')

# ===== PROXIMITY SKINNING (meu metodo, funciona em mesh suja) =====
segs = []
for b in rig.data.bones:
    if not b.use_deform: continue
    h = rig.matrix_world @ b.head_local
    t = rig.matrix_world @ b.tail_local
    segs.append((b.name, h, t))
print(f'deform bones: {len(segs)}')

def dseg(p, a, bb):
    ab = bb - a
    L2 = ab.length_squared
    if L2 < 1e-12: return (p-a).length
    t = max(0.0, min(1.0, (p-a).dot(ab)/L2))
    return (p - (a + ab*t)).length

vgs = {name: body.vertex_groups.new(name=name) for name,_,_ in segs}
mw = body.matrix_world
for v in body.data.vertices:
    wp = mw @ v.co
    d = sorted(((dseg(wp,h,t), n) for n,h,t in segs))[:3]
    ws = [(1.0/max(di,1e-5)**2, n) for di,n in d]
    s = sum(w for w,_ in ws)
    for w, n in ws:
        vgs[n].add([v.index], w/s, 'REPLACE')
am = body.modifiers.new('Armature','ARMATURE'); am.object = rig
mwx = body.matrix_world.copy()
body.parent = rig; body.matrix_world = mwx
print('proximity skinning 3-bone OK')

# Smooth weights (nivel weight paint pro)
bpy.context.view_layer.objects.active = body
for o in bpy.data.objects: o.select_set(False)
body.select_set(True)
bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
bpy.ops.object.vertex_group_smooth(group_select_mode='ALL', factor=0.5, repeat=5, expand=0.4)
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
bpy.ops.object.mode_set(mode='OBJECT')
print('weights smoothed')
bpy.ops.wm.save_mainfile()
print('PRO PHASE 2 OK')
