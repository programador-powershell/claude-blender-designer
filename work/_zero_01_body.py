import bpy, bmesh, math
from mathutils import Vector

# ============ CENA NOVA 100% DO ZERO ============
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
for me in list(bpy.data.meshes):
    if me.users == 0: bpy.data.meshes.remove(me)

# ============ FASE 1: CORPO HUMANO (skin modifier skeleton-edges) ============
# Anatomia feminina 1.70m T-pose - eu defino cada junta + raio
JOINTS = {
    # nome: (pos, raio_skin)
    'pelvis':     ((0, 0, 1.00), 0.118),
    'waist':      ((0, 0, 1.13), 0.092),
    'chest':      ((0, 0, 1.27), 0.115),
    'neck_base':  ((0, 0, 1.43), 0.046),
    'head_low':   ((0, 0, 1.52), 0.082),
    'head_top':   ((0, 0, 1.63), 0.078),
    'shoulder_L': (( 0.165, 0, 1.385), 0.052),
    'elbow_L':    (( 0.44, 0, 1.385), 0.038),
    'wrist_L':    (( 0.66, 0, 1.385), 0.030),
    'hand_L':     (( 0.76, 0, 1.385), 0.034),
    'shoulder_R': ((-0.165, 0, 1.385), 0.052),
    'elbow_R':    ((-0.44, 0, 1.385), 0.038),
    'wrist_R':    ((-0.66, 0, 1.385), 0.030),
    'hand_R':     ((-0.76, 0, 1.385), 0.034),
    'hip_L':      (( 0.088, 0, 0.96), 0.078),
    'knee_L':     (( 0.098, 0, 0.53), 0.052),
    'ankle_L':    (( 0.103, 0, 0.085), 0.036),
    'toe_L':      (( 0.103, -0.115, 0.03), 0.036),
    'hip_R':      ((-0.088, 0, 0.96), 0.078),
    'knee_R':     ((-0.098, 0, 0.53), 0.052),
    'ankle_R':    ((-0.103, 0, 0.085), 0.036),
    'toe_R':      ((-0.103, -0.115, 0.03), 0.036),
}
EDGES = [
    ('pelvis','waist'), ('waist','chest'), ('chest','neck_base'),
    ('neck_base','head_low'), ('head_low','head_top'),
    ('chest','shoulder_L'), ('shoulder_L','elbow_L'), ('elbow_L','wrist_L'), ('wrist_L','hand_L'),
    ('chest','shoulder_R'), ('shoulder_R','elbow_R'), ('elbow_R','wrist_R'), ('wrist_R','hand_R'),
    ('pelvis','hip_L'), ('hip_L','knee_L'), ('knee_L','ankle_L'), ('ankle_L','toe_L'),
    ('pelvis','hip_R'), ('hip_R','knee_R'), ('knee_R','ankle_R'), ('ankle_R','toe_R'),
]

names = list(JOINTS.keys())
idx = {n: i for i, n in enumerate(names)}
verts = [JOINTS[n][0] for n in names]
edges = [(idx[a], idx[b]) for a, b in EDGES]

me = bpy.data.meshes.new('Alice_Body_Mesh')
me.from_pydata(verts, edges, [])
me.update()
body = bpy.data.objects.new('Alice_Body', me)
bpy.context.scene.collection.objects.link(body)
bpy.context.view_layer.objects.active = body
body.select_set(True)

# Skin modifier + raios anatomicos
skin = body.modifiers.new('Skin', 'SKIN')
sub = body.modifiers.new('Subd', 'SUBSURF'); sub.levels = 2; sub.render_levels = 2
for i, n in enumerate(names):
    sv = me.skin_vertices[0].data[i]
    r = JOINTS[n][1]
    sv.radius = (r, r)
# Root no pelvis
me.skin_vertices[0].data[idx['pelvis']].use_root = True

# Aplicar skin+subsurf -> mesh real
bpy.ops.object.modifier_apply(modifier='Skin')
bpy.ops.object.modifier_apply(modifier='Subd')
print(f'BODY: verts={len(body.data.vertices)} polys={len(body.data.polygons)}')

# Shade smooth
bpy.ops.object.shade_smooth()

# Refinos femininos: cintura estreita + busto via proportional scale simples
bm = bmesh.new(); bm.from_mesh(body.data)
for v in bm.verts:
    z = v.co.z
    # cintura: puxa pra dentro em 1.08-1.20
    if 1.06 < z < 1.22:
        f = 1.0 - 0.18 * math.sin(math.pi * (z - 1.06) / 0.16)
        v.co.x *= f; v.co.y *= f
    # busto: empurra frente y- em 1.24-1.34
    if 1.23 < z < 1.35 and v.co.y < 0:
        f = math.sin(math.pi * (z - 1.23) / 0.12)
        v.co.y -= 0.030 * f * max(0.0, 1.0 - abs(v.co.x) / 0.12)
    # quadril: leve alarga 0.92-1.02
    if 0.90 < z < 1.04:
        f = math.sin(math.pi * (z - 0.90) / 0.14)
        v.co.x *= (1.0 + 0.06 * f)
bm.to_mesh(body.data); bm.free()
body.data.update()
print('feminine shape OK')

# ============ FASE 2: ESQUELETO HUMANO (mixamo naming) ============
arm_data = bpy.data.armatures.new('Alice_Rig_Data')
arm = bpy.data.objects.new('Alice_Rig', arm_data)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')

def add_bone(name, head, tail, parent=None, connect=False):
    b = arm_data.edit_bones.new(name)
    b.head = Vector(head); b.tail = Vector(tail)
    if parent:
        b.parent = arm_data.edit_bones[parent]
        b.use_connect = connect
    return b

add_bone('mixamorig:Hips',      (0,0,1.00), (0,0,1.09))
add_bone('mixamorig:Spine',     (0,0,1.09), (0,0,1.18), 'mixamorig:Hips', True)
add_bone('mixamorig:Spine1',    (0,0,1.18), (0,0,1.27), 'mixamorig:Spine', True)
add_bone('mixamorig:Spine2',    (0,0,1.27), (0,0,1.385), 'mixamorig:Spine1', True)
add_bone('mixamorig:Neck',      (0,0,1.385), (0,0,1.47), 'mixamorig:Spine2', True)
add_bone('mixamorig:Head',      (0,0,1.47), (0,0,1.60), 'mixamorig:Neck', True)
add_bone('mixamorig:HeadTop_End',(0,0,1.60), (0,0,1.70), 'mixamorig:Head', True)
for S, sgn in [('Left', 1), ('Right', -1)]:
    add_bone(f'mixamorig:{S}Shoulder', (sgn*0.03,0,1.37), (sgn*0.165,0,1.385), 'mixamorig:Spine2')
    add_bone(f'mixamorig:{S}Arm',      (sgn*0.165,0,1.385), (sgn*0.44,0,1.385), f'mixamorig:{S}Shoulder', True)
    add_bone(f'mixamorig:{S}ForeArm',  (sgn*0.44,0,1.385), (sgn*0.66,0,1.385), f'mixamorig:{S}Arm', True)
    add_bone(f'mixamorig:{S}Hand',     (sgn*0.66,0,1.385), (sgn*0.80,0,1.385), f'mixamorig:{S}ForeArm', True)
    add_bone(f'mixamorig:{S}UpLeg',    (sgn*0.088,0,0.96), (sgn*0.098,0,0.53), 'mixamorig:Hips')
    add_bone(f'mixamorig:{S}Leg',      (sgn*0.098,0,0.53), (sgn*0.103,0,0.085), f'mixamorig:{S}UpLeg', True)
    add_bone(f'mixamorig:{S}Foot',     (sgn*0.103,0,0.085), (sgn*0.103,-0.115,0.03), f'mixamorig:{S}Leg', True)
    add_bone(f'mixamorig:{S}ToeBase',  (sgn*0.103,-0.115,0.03), (sgn*0.103,-0.165,0.02), f'mixamorig:{S}Foot', True)
bpy.ops.object.mode_set(mode='OBJECT')
print(f'RIG: {len(arm_data.bones)} bones')

# ============ FASE 3: SKINNING AUTO (mesh manifold limpa -> bone heat OK) ============
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True); arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
import random
from collections import Counter
vg = {g.index: g.name for g in body.vertex_groups}
cnt = Counter()
random.seed(5)
for i in random.sample(range(len(body.data.vertices)), min(2000, len(body.data.vertices))):
    v = body.data.vertices[i]; bw=0; bb=None
    for g in v.groups:
        if g.weight>bw: bw=g.weight; bb=vg.get(g.group)
    cnt[bb]+=1
print('weights sample:', cnt.most_common(6))
print('ZERO PHASE 1-3 DONE')
