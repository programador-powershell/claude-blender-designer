import bpy, random
from collections import Counter

arm = bpy.data.objects['Alice_Base_Rig']
dress = bpy.data.objects['PA_AliceChapeleiroDress']
body = bpy.data.objects['Alice_Base_Body']

for o in [body, dress]:
    # limpar weights lixo
    o.vertex_groups.clear()
    # remover armature modifiers velhos
    for m in list(o.modifiers):
        if m.type == 'ARMATURE': o.modifiers.remove(m)
    # clear parent mantendo transform
    mw = o.matrix_world.copy()
    o.parent = None
    o.matrix_world = mw

# Automatic weights: body primeiro
for o in [body, dress]:
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True); arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    print(f'{o.name}: auto weights done, vgroups={len(o.vertex_groups)}')

# Verify
for o in [dress, body]:
    vg = {g.index: g.name for g in o.vertex_groups}
    cnt = Counter()
    verts = o.data.vertices
    random.seed(2)
    for i in random.sample(range(len(verts)), min(4000, len(verts))):
        v = verts[i]; bw=0; bb=None
        for g in v.groups:
            if g.weight>bw: bw=g.weight; bb=vg.get(g.group)
        cnt[bb]+=1
    print(o.name, cnt.most_common(6))
print('WEIGHTS REDONE')
