import bpy
from mathutils import Vector

dress = bpy.data.objects['PA_AliceChapeleiroDress']
body = bpy.data.objects['Alice_Base_Body']
mesh = dress.data

# ===== Teal mais ESCURO (ref #2D4438 dark gothic) =====
m_teal = bpy.data.materials['MAT_Teal_Fabric']
nt = m_teal.node_tree
ramp = next((n for n in nt.nodes if n.type == 'VALTORGB'), None)
if ramp:
    ramp.color_ramp.elements[0].color = (0.030, 0.062, 0.048, 1)
    ramp.color_ramp.elements[1].color = (0.055, 0.105, 0.082, 1)

# ===== Reassign regioes (iter 2 - meu olho) =====
IDX = {m.name: i for i, m in enumerate(dress.data.materials)}
vg_name = {vg.index: vg.name for vg in dress.vertex_groups}

def region_v2(wco, bone):
    z = wco.z; x = wco.x; y = wco.y
    b = bone or ''
    r_axis = (x*x + y*y) ** 0.5
    # LUVAS pretas: antebraco/mao
    if 'Hand' in b or 'ForeArm' in b:
        return IDX['MAT_Black_Leather']
    # MANGAS puff teal: braco/ombro
    if ('Arm' in b and 'ForeArm' not in b) or 'Shoulder' in b:
        return IDX['MAT_Teal_Fabric']
    # CHAPEU mini top hat: bem no topo
    if z > 1.66:
        return IDX['MAT_Teal_Fabric']
    # CABELO: cabeca + mechas atras (preto)
    if 1.30 < z <= 1.66 and r_axis < 0.30 and ('Head' in b or 'Neck' in b or 'Spine2' in b):
        # rosto fica na frente y<-0.04 e estreito - manter pele? mesh dress nao tem rosto
        return IDX['MAT_Hair_Black']
    if y > 0.04 and 0.92 < z <= 1.35 and abs(x) < 0.25:
        return IDX['MAT_Hair_Black']  # mechas longas caindo atras
    # BOW gold traseiro
    if y > 0.10 and 0.95 < z < 1.30 and abs(x) < 0.30:
        return IDX['MAT_Gold_Antique']
    # BOTAS
    if z < 0.40:
        return IDX['MAT_Black_Leather']
    # MEIAS listradas: so pernas finas (raio pequeno)
    if 0.40 <= z < 0.64 and r_axis < 0.17:
        return IDX['MAT_Stripes_BW']
    # HEM cream lace: barra larga
    if 0.40 <= z < 0.70:
        return IDX['MAT_Cream_Lace']
    # SAIA teal
    if 0.70 <= z < 1.08:
        return IDX['MAT_Teal_Fabric']
    # CORPETE teal
    if 1.08 <= z < 1.36:
        return IDX['MAT_Teal_Fabric']
    # DECOTE chemise cream
    if 1.36 <= z < 1.52:
        return IDX['MAT_Cream_Chemise']
    return IDX['MAT_Teal_Fabric']

count = {}
for poly in mesh.polygons:
    center = dress.matrix_world @ poly.center
    v0 = mesh.vertices[poly.vertices[0]]
    best_w = 0; best_b = None
    for g in v0.groups:
        if g.weight > best_w:
            best_w = g.weight; best_b = vg_name.get(g.group)
    mi = region_v2(center, best_b)
    poly.material_index = mi
    count[mi] = count.get(mi, 0) + 1

names = [m.name for m in dress.data.materials]
print('faces v2:')
for i, n in enumerate(names):
    print(f'  {n}: {count.get(i,0)}')

# ===== BODY: meias listradas nas pernas + skin resto =====
m_skin = bpy.data.materials['MAT_Skin_Pale']
m_stripes = bpy.data.materials['MAT_Stripes_BW']
m_leather = bpy.data.materials['MAT_Black_Leather']
body.data.materials.clear()
body.data.materials.append(m_skin)      # 0
body.data.materials.append(m_stripes)   # 1
body.data.materials.append(m_leather)   # 2
bcount = {0:0, 1:0, 2:0}
for poly in body.data.polygons:
    c = body.matrix_world @ poly.center
    if c.z < 0.38:
        poly.material_index = 2   # dentro da bota
    elif c.z < 0.62:
        poly.material_index = 1   # meia listrada
    else:
        poly.material_index = 0
    bcount[poly.material_index] += 1
print(f'body: skin={bcount[0]} stripes={bcount[1]} boot={bcount[2]}')
print('FIX V2 OK')
