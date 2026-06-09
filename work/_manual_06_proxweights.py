import bpy, random
from mathutils import Vector
from collections import Counter

arm = bpy.data.objects['Alice_Base_Rig']
dress = bpy.data.objects['PA_AliceChapeleiroDress']
body = bpy.data.objects['Alice_Base_Body']

# Bones deform: segmentos world (head, tail)
segs = []
for b in arm.data.bones:
    if 'Toe_End' in b.name or 'HeadTop_End' in b.name: continue  # ends sem deform util
    h = arm.matrix_world @ b.head_local
    t = arm.matrix_world @ b.tail_local
    segs.append((b.name, h, t))
print(f'bones deform: {len(segs)}')

def dist_pt_seg(p, a, b):
    ab = b - a
    L2 = ab.length_squared
    if L2 < 1e-12: return (p - a).length
    t = max(0.0, min(1.0, (p - a).dot(ab) / L2))
    return (p - (a + ab * t)).length

for o in [body, dress]:
    o.vertex_groups.clear()
    vgs = {name: o.vertex_groups.new(name=name) for name, _, _ in segs}
    mw = o.matrix_world
    for v in o.data.vertices:
        wp = mw @ v.co
        # 2 bones mais proximos
        d = []
        for name, h, t in segs:
            d.append((dist_pt_seg(wp, h, t), name))
        d.sort()
        d0, n0 = d[0]; d1, n1 = d[1]
        # inverse distance blend (power 2)
        w0 = 1.0 / max(d0, 1e-5) ** 2
        w1 = 1.0 / max(d1, 1e-5) ** 2
        s = w0 + w1
        vgs[n0].add([v.index], w0 / s, 'REPLACE')
        vgs[n1].add([v.index], w1 / s, 'REPLACE')
    # Armature modifier (primeiro da stack)
    for m in list(o.modifiers):
        if m.type == 'ARMATURE': o.modifiers.remove(m)
    am = o.modifiers.new('Armature', 'ARMATURE'); am.object = arm
    while o.modifiers.find('Armature') > 0:
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_move_up(modifier='Armature')
    # parent keep transform
    mwx = o.matrix_world.copy()
    o.parent = arm
    o.matrix_world = mwx
    print(f'{o.name}: prox weights ok')

# Verify
for o in [dress, body]:
    vg = {g.index: g.name for g in o.vertex_groups}
    cnt = Counter()
    random.seed(3)
    verts = o.data.vertices
    for i in random.sample(range(len(verts)), 3000):
        v = verts[i]; bw=0; bb=None
        for g in v.groups:
            if g.weight>bw: bw=g.weight; bb=vg.get(g.group)
        cnt[bb]+=1
    print(o.name, cnt.most_common(8))
print('PROX WEIGHTS DONE')
