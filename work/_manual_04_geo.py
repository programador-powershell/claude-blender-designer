import bpy
from mathutils import Vector

dress = bpy.data.objects['PA_AliceChapeleiroDress']
mesh = dress.data
IDX = {m.name: i for i, m in enumerate(dress.data.materials)}

def region_v3(c):
    """100% geometrico - meu mapa anatomico da ref chapeleiro."""
    z = c.z; x = c.x; y = c.y
    ax = abs(x)
    r_axis = (x*x + y*y) ** 0.5
    # LUVAS pretas: maos/antebraco extremos
    if ax > 0.52 and z > 1.20:
        return IDX['MAT_Black_Leather']
    # MANGAS puff teal: braco
    if ax > 0.28 and z > 1.15:
        return IDX['MAT_Teal_Fabric']
    # CHAPEU: topo
    if z > 1.64:
        return IDX['MAT_Teal_Fabric']
    # CABELO: cabeca/atras
    if z > 1.32 and r_axis < 0.30:
        if y > -0.02:  # tras e topo da cabeca
            return IDX['MAT_Hair_Black']
        if z > 1.55:   # topo frente tambem cabelo (franja)
            return IDX['MAT_Hair_Black']
        # decote frente
        return IDX['MAT_Cream_Chemise']
    # MECHAS longas atras
    if y > 0.10 and 0.95 < z <= 1.35 and ax < 0.28:
        return IDX['MAT_Hair_Black']
    # BOW gold traseiro (saia atras alto)
    if y > 0.16 and 0.98 < z < 1.22:
        return IDX['MAT_Gold_Antique']
    # BOTAS
    if z < 0.40:
        return IDX['MAT_Black_Leather']
    # MEIAS listradas: pernas finas
    if 0.40 <= z < 0.66 and r_axis < 0.165:
        return IDX['MAT_Stripes_BW']
    # HEM cream lace
    if 0.40 <= z < 0.68:
        return IDX['MAT_Cream_Lace']
    # SAIA + CORPETE teal
    if 0.68 <= z < 1.36:
        return IDX['MAT_Teal_Fabric']
    return IDX['MAT_Teal_Fabric']

count = {}
for poly in mesh.polygons:
    c = dress.matrix_world @ poly.center
    mi = region_v3(c)
    poly.material_index = mi
    count[mi] = count.get(mi, 0) + 1

names = [m.name for m in dress.data.materials]
print('faces v3 (geo only):')
for i, n in enumerate(names):
    print(f'  {n}: {count.get(i,0)}')

# ===== REFAZER WEIGHTS (lixo Toe_End) =====
body = bpy.data.objects['Alice_Base_Body']
arm = bpy.data.objects['Alice_Base_Rig']

# Verificar weights do body primeiro
vgb = {vg.index: vg.name for vg in body.vertex_groups}
from collections import Counter
bcnt = Counter()
for v in body.data.vertices[:3000]:
    bw=0; bb=None
    for g in v.groups:
        if g.weight>bw: bw=g.weight; bb=vgb.get(g.group)
    bcnt[bb]+=1
print('body sample weights:', bcnt.most_common(6))
