import bpy, math
from mathutils import Vector

# Remove Icosphere lixo
ico = bpy.data.objects.get('Icosphere')
if ico: bpy.data.objects.remove(ico, do_unlink=True)

dress = bpy.data.objects['PA_AliceChapeleiroDress']
body = bpy.data.objects['Alice_Base_Body']
arm = bpy.data.objects['Alice_Base_Rig']

# ============ MATERIAIS PBR PROCEDURAIS ============
def new_mat(name):
    m = bpy.data.materials.get(name)
    if m: bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial'); out.location = (600, 0)
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled'); bsdf.location = (300, 0)
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return m, nt, bsdf

# 1. Teal fabric (saia/corpete/mangas) - damask weave
m_teal, nt, bsdf = new_mat('MAT_Teal_Fabric')
bsdf.inputs['Base Color'].default_value = (0.085, 0.16, 0.13, 1.0)
bsdf.inputs['Roughness'].default_value = 0.78
tex = nt.nodes.new('ShaderNodeTexNoise'); tex.location = (-300, -200)
tex.inputs['Scale'].default_value = 180.0
tex.inputs['Detail'].default_value = 8.0
bump = nt.nodes.new('ShaderNodeBump'); bump.location = (0, -200)
bump.inputs['Strength'].default_value = 0.12
nt.links.new(tex.outputs['Fac'], bump.inputs['Height'])
nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
# subtle color variation damask
ramp = nt.nodes.new('ShaderNodeValToRGB'); ramp.location = (-100, 200)
ramp.color_ramp.elements[0].color = (0.07, 0.14, 0.11, 1)
ramp.color_ramp.elements[1].color = (0.11, 0.20, 0.16, 1)
tex2 = nt.nodes.new('ShaderNodeTexWave'); tex2.location = (-400, 200)
tex2.inputs['Scale'].default_value = 14.0
tex2.inputs['Distortion'].default_value = 6.0
nt.links.new(tex2.outputs['Fac'], ramp.inputs['Fac'])
nt.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])

# 2. Cream lace hem
m_cream, nt, bsdf = new_mat('MAT_Cream_Lace')
bsdf.inputs['Base Color'].default_value = (0.82, 0.76, 0.64, 1.0)
bsdf.inputs['Roughness'].default_value = 0.88
tex = nt.nodes.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value = 300.0
bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.25
nt.links.new(tex.outputs['Fac'], bump.inputs['Height'])
nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])

# 3. Black lace
m_blklace, nt, bsdf = new_mat('MAT_Black_Lace')
bsdf.inputs['Base Color'].default_value = (0.035, 0.03, 0.03, 1.0)
bsdf.inputs['Roughness'].default_value = 0.92
tex = nt.nodes.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value = 250.0
bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.3
nt.links.new(tex.outputs['Fac'], bump.inputs['Height'])
nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])

# 4. Striped stockings BW - horizontal stripes via Z coordinate
m_stripes, nt, bsdf = new_mat('MAT_Stripes_BW')
bsdf.inputs['Roughness'].default_value = 0.80
geo = nt.nodes.new('ShaderNodeNewGeometry'); geo.location = (-700, 0)
sep = nt.nodes.new('ShaderNodeSeparateXYZ'); sep.location = (-550, 0)
nt.links.new(geo.outputs['Position'], sep.inputs['Vector'])
mathn = nt.nodes.new('ShaderNodeMath'); mathn.operation = 'MULTIPLY'; mathn.location = (-400, 0)
mathn.inputs[1].default_value = 55.0   # stripe frequency
nt.links.new(sep.outputs['Z'], mathn.inputs[0])
sinn = nt.nodes.new('ShaderNodeMath'); sinn.operation = 'SINE'; sinn.location = (-250, 0)
nt.links.new(mathn.outputs[0], sinn.inputs[0])
gt = nt.nodes.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.location = (-100, 0)
gt.inputs[1].default_value = 0.0
nt.links.new(sinn.outputs[0], gt.inputs[0])
rampS = nt.nodes.new('ShaderNodeValToRGB'); rampS.location = (50, 100)
rampS.color_ramp.elements[0].color = (0.06, 0.055, 0.05, 1)   # black
rampS.color_ramp.elements[1].color = (0.75, 0.72, 0.68, 1)    # white
nt.links.new(gt.outputs[0], rampS.inputs['Fac'])
nt.links.new(rampS.outputs['Color'], bsdf.inputs['Base Color'])

# 5. Black leather (botas/luvas)
m_leather, nt, bsdf = new_mat('MAT_Black_Leather')
bsdf.inputs['Base Color'].default_value = (0.028, 0.024, 0.02, 1.0)
bsdf.inputs['Roughness'].default_value = 0.42
tex = nt.nodes.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value = 90.0
tex.inputs['Detail'].default_value = 6.0
bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.08
nt.links.new(tex.outputs['Fac'], bump.inputs['Height'])
nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])

# 6. Antique gold (bow/trims/relogio/chave)
m_gold, nt, bsdf = new_mat('MAT_Gold_Antique')
bsdf.inputs['Base Color'].default_value = (0.62, 0.45, 0.16, 1.0)
bsdf.inputs['Metallic'].default_value = 1.0
bsdf.inputs['Roughness'].default_value = 0.32
tex = nt.nodes.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value = 40.0
bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.05
nt.links.new(tex.outputs['Fac'], bump.inputs['Height'])
nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])

# 7. Hair black glossy
m_hair, nt, bsdf = new_mat('MAT_Hair_Black')
bsdf.inputs['Base Color'].default_value = (0.018, 0.015, 0.016, 1.0)
bsdf.inputs['Roughness'].default_value = 0.38
try: bsdf.inputs['Anisotropic'].default_value = 0.6
except: pass

# 8. Cream chemise (peito/blusa interna)
m_chemise, nt, bsdf = new_mat('MAT_Cream_Chemise')
bsdf.inputs['Base Color'].default_value = (0.84, 0.79, 0.68, 1.0)
bsdf.inputs['Roughness'].default_value = 0.82

# 9. Skin pra body
m_skin, nt, bsdf = new_mat('MAT_Skin_Pale')
bsdf.inputs['Base Color'].default_value = (0.78, 0.62, 0.55, 1.0)
bsdf.inputs['Roughness'].default_value = 0.55
try:
    bsdf.inputs['Subsurface Weight'].default_value = 0.15
    bsdf.inputs['Subsurface Radius'].default_value = (0.012, 0.005, 0.003)
except Exception: pass

body.data.materials.clear()
body.data.materials.append(m_skin)

# ============ ASSIGN MATERIAL SLOTS NO DRESS POR REGIAO ============
mats_order = [m_teal, m_cream, m_blklace, m_stripes, m_leather, m_gold, m_hair, m_chemise]
dress.data.materials.clear()
for m in mats_order: dress.data.materials.append(m)
IDX = {m.name: i for i, m in enumerate(mats_order)}

vg_name = {vg.index: vg.name for vg in dress.vertex_groups}
mesh = dress.data

def region_for(wco, bone):
    """EU decido material por regiao anatomica (bone dominante + world pos)."""
    z = wco.z; x = wco.x; y = wco.y
    b = bone or ''
    # CABELO: Head/Neck + atras OU topo (z>1.45 e y>0) - cabelo longo cai atras ate ~1.0
    if ('Head' in b or 'Neck' in b) and z > 1.38:
        return IDX['MAT_Hair_Black']
    # mechas longas atras (y>0.05, z entre 0.9-1.45, perto do eixo)
    if y > 0.06 and 0.95 < z < 1.45 and abs(x) < 0.22 and ('Spine' in b or 'Head' in b or 'Neck' in b):
        return IDX['MAT_Hair_Black']
    # CHAPEU topo cabeca
    if z > 1.62:
        return IDX['MAT_Teal_Fabric']
    # BOTAS: pe/canela
    if z < 0.42 and ('Foot' in b or 'Leg' in b or z < 0.38):
        return IDX['MAT_Black_Leather']
    # MEIAS listradas: canela/joelho/coxa baixa
    if 0.42 <= z < 0.62:
        return IDX['MAT_Stripes_BW']
    # HEM cream lace: barra da saia
    if 0.62 <= z < 0.74:
        return IDX['MAT_Cream_Lace']
    # SAIA teal principal
    if 0.74 <= z < 1.06:
        return IDX['MAT_Teal_Fabric']
    # CORPETE teal
    if 1.06 <= z < 1.34 and 'Arm' not in b and 'Hand' not in b:
        return IDX['MAT_Teal_Fabric']
    # LUVAS: maos/antebraco
    if 'Hand' in b or 'ForeArm' in b:
        return IDX['MAT_Black_Leather']
    # MANGAS puff: braco superior
    if 'Arm' in b or 'Shoulder' in b:
        return IDX['MAT_Teal_Fabric']
    # PEITO/decote chemise
    if 1.34 <= z < 1.5:
        return IDX['MAT_Cream_Chemise']
    return IDX['MAT_Teal_Fabric']

count_per_mat = {}
for poly in mesh.polygons:
    # face center world + dominant bone do 1o vert
    center = dress.matrix_world @ poly.center
    v0 = mesh.vertices[poly.vertices[0]]
    best_w = 0; best_b = None
    for g in v0.groups:
        if g.weight > best_w:
            best_w = g.weight; best_b = vg_name.get(g.group)
    mi = region_for(center, best_b)
    poly.material_index = mi
    count_per_mat[mi] = count_per_mat.get(mi, 0) + 1

print('faces per material:')
for i, m in enumerate(mats_order):
    print(f'  {m.name}: {count_per_mat.get(i, 0)}')
print('MATERIALS ASSIGNED')
