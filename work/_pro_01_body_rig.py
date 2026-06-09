import bpy, math
from mathutils import Vector

# ===== CENA NOVA + APPEND CORPO OFICIAL (proporcoes corretas peito/cintura/quadril) =====
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

with bpy.data.libraries.load(r'D:/Alice/tools/auto-rig-fix/work/alice_rigged.blend') as (src, dst):
    dst.objects = ['AliceMesh']
for o in dst.objects:
    if o: bpy.context.scene.collection.objects.link(o)

body = bpy.data.objects.get('AliceMesh')
print(f'body oficial: verts={len(body.data.vertices)}')
# Limpar modifiers/parents herdados
body.parent = None
for m in list(body.modifiers): body.modifiers.remove(m)
body.vertex_groups.clear()

# Normalizar: 1.70m, pes no chao, centro X
zs = [(body.matrix_world @ v.co).z for v in body.data.vertices]
xs = [(body.matrix_world @ v.co).x for v in body.data.vertices]
h = max(zs) - min(zs)
s = 1.70 / h
body.scale = (body.scale.x*s, body.scale.y*s, body.scale.z*s)
bpy.context.view_layer.update()
zs = [(body.matrix_world @ v.co).z for v in body.data.vertices]
body.location.z -= min(zs)
bpy.context.view_layer.update()
bpy.context.view_layer.objects.active = body
for o in bpy.data.objects: o.select_set(False)
body.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
print('body normalizado 1.70m')

# Medidas reais do corpo p/ posicionar bones com precisao
def slice_stats(z_lo, z_hi):
    pts = [v.co for v in body.data.vertices if z_lo <= v.co.z <= z_hi]
    if not pts: return None
    xs = [p.x for p in pts]; ys = [p.y for p in pts]
    return (min(xs), max(xs), min(ys), max(ys))

sh = slice_stats(1.36, 1.42)   # ombros
print('shoulders slice:', sh)
shoulder_x = (sh[1]) * 0.92 if sh else 0.17

# ===== ESQUELETO DETALHADO OSSO POR OSSO (~90 bones) =====
arm_data = bpy.data.armatures.new('AliceRig_Data')
rig = bpy.data.objects.new('AliceRig', arm_data)
bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
EB = arm_data.edit_bones

def B(name, head, tail, parent=None, connect=False, deform=True):
    b = EB.new(name)
    b.head = Vector(head); b.tail = Vector(tail)
    b.use_deform = deform
    if parent:
        b.parent = EB[parent]; b.use_connect = connect
    return b

# Core
B('Hips',   (0,0,0.98), (0,0,1.06))
B('Spine',  (0,0,1.06), (0,0,1.15), 'Hips', True)
B('Spine1', (0,0,1.15), (0,0,1.24), 'Spine', True)
B('Spine2', (0,0,1.24), (0,0,1.37), 'Spine1', True)
B('Neck',   (0,0,1.37), (0,0,1.45), 'Spine2', True)
B('Head',   (0,0,1.45), (0,0,1.58), 'Neck', True)
B('HeadTop',(0,0,1.58), (0,0,1.68), 'Head', True)

SX = shoulder_x
for S, g in [('L',1),('R',-1)]:
    # Bracos + twist
    B(f'Clavicle_{S}', (g*0.025,0,1.35), (g*SX,0,1.375), 'Spine2')
    B(f'UpperArm_{S}', (g*SX,0,1.375), (g*(SX+0.13),0,1.375), f'Clavicle_{S}', True)
    B(f'UpperArmTwist_{S}', (g*(SX+0.13),0,1.375), (g*(SX+0.26),0,1.375), f'UpperArm_{S}', True)
    B(f'ForeArm_{S}', (g*(SX+0.26),0,1.375), (g*(SX+0.38),0,1.375), f'UpperArmTwist_{S}', True)
    B(f'ForeArmTwist_{S}', (g*(SX+0.38),0,1.375), (g*(SX+0.48),0,1.375), f'ForeArm_{S}', True)
    B(f'Hand_{S}', (g*(SX+0.48),0,1.375), (g*(SX+0.54),0,1.375), f'ForeArmTwist_{S}', True)
    # 5 dedos x 3 falanges (como dedos.mp4)
    fingers = [('Thumb',  -0.030, 0.022, 0.018, 0.015),
               ('Index',  -0.015, 0.028, 0.022, 0.017),
               ('Middle',  0.000, 0.030, 0.024, 0.018),
               ('Ring',    0.014, 0.028, 0.022, 0.016),
               ('Pinky',   0.027, 0.022, 0.017, 0.013)]
    hx = SX + 0.54
    for fname, yoff, l1, l2, l3 in fingers:
        base = hx + (0.012 if fname=='Thumb' else 0.0)
        p = f'Hand_{S}'
        x0 = g*base
        B(f'{fname}1_{S}', (x0, yoff, 1.375), (g*(base+l1), yoff, 1.375), p, False)
        B(f'{fname}2_{S}', (g*(base+l1), yoff, 1.375), (g*(base+l1+l2), yoff, 1.375), f'{fname}1_{S}', True)
        B(f'{fname}3_{S}', (g*(base+l1+l2), yoff, 1.375), (g*(base+l1+l2+l3), yoff, 1.375), f'{fname}2_{S}', True)
    # Pernas + twist
    B(f'Thigh_{S}', (g*0.085,0,0.96), (g*0.092,0,0.74), 'Hips')
    B(f'ThighTwist_{S}', (g*0.092,0,0.74), (g*0.096,0,0.53), f'Thigh_{S}', True)
    B(f'Shin_{S}', (g*0.096,0,0.53), (g*0.100,0,0.30), f'ThighTwist_{S}', True)
    B(f'ShinTwist_{S}', (g*0.100,0,0.30), (g*0.102,0,0.085), f'Shin_{S}', True)
    B(f'Foot_{S}', (g*0.102,0,0.085), (g*0.102,-0.11,0.03), f'ShinTwist_{S}', True)
    B(f'Toe_{S}', (g*0.102,-0.11,0.03), (g*0.102,-0.16,0.025), f'Foot_{S}', True)
    # JIGGLE bones (mecanica.mp4: chest + butt)
    B(f'Breast_{S}', (g*0.055,-0.06,1.28), (g*0.055,-0.13,1.27), 'Spine2', False, True)
    B(f'Butt_{S}',   (g*0.06, 0.06,0.96), (g*0.06, 0.13,0.94), 'Hips', False, True)
# Skirt helper bones (4 direcoes - cloth follow)
for nm, off in [('SkirtF',(0,-0.10,0)), ('SkirtB',(0,0.10,0)), ('SkirtL',(0.12,0,0)), ('SkirtR',(-0.12,0,0))]:
    B(nm, (off[0]*0.7, off[1]*0.7, 0.98), (off[0], off[1], 0.72), 'Hips', False, True)

bpy.ops.object.mode_set(mode='OBJECT')
print(f'RIG PRO: {len(arm_data.bones)} bones (dedos+twist+jiggle+skirt)')

# ===== SKINNING corpo oficial =====
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True); rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
import random
from collections import Counter
vg = {g.index: g.name for g in body.vertex_groups}
cnt = Counter()
random.seed(7)
nv = len(body.data.vertices)
for i in random.sample(range(nv), min(3000, nv)):
    v = body.data.vertices[i]; bw=0; bb=None
    for g_ in v.groups:
        if g_.weight>bw: bw=g_.weight; bb=vg.get(g_.group)
    cnt[bb]+=1
print('weights:', cnt.most_common(8))
bpy.ops.wm.save_as_mainfile(filepath=r'D:/Alice/tools/auto-rig-fix/work/alice_PRO.blend')
print('PRO PHASE 1 SAVED')
