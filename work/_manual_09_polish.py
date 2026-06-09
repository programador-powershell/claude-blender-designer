import bpy

pieces = ['Alice_Base_Body', 'PA_Botas_Luvas', 'PA_Cabelo', 'PA_Hem_Lace_Cream',
          'PA_Meias_Listradas', 'PA_Saia_Corpete_Teal']

# ===== 1. WEIGHT SMOOTHING PROFISSIONAL (como screenshots ref) =====
for name in pieces:
    o = bpy.data.objects.get(name)
    if not o: continue
    bpy.context.view_layer.objects.active = o
    for ob in bpy.data.objects: ob.select_set(False)
    o.select_set(True)
    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
    try:
        bpy.ops.object.vertex_group_smooth(group_select_mode='ALL', factor=0.5, repeat=6, expand=0.5)
        bpy.ops.object.vertex_group_normalize_all(lock_active=False)
        print(f'{name}: weights smoothed+normalized')
    except Exception as e:
        print(f'{name}: smooth fail {e}')
    bpy.ops.object.mode_set(mode='OBJECT')

# ===== 2. CARD PRINTS na saia (ref: cartas de baralho espalhadas) =====
m_teal = bpy.data.materials['MAT_Teal_Fabric']
nt = m_teal.node_tree
bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
old_ramp = next((n for n in nt.nodes if n.type == 'VALTORGB'), None)

# Brick texture = cartas retangulares esparsas
brick = nt.nodes.new('ShaderNodeTexBrick'); brick.location = (-650, 420)
brick.inputs['Scale'].default_value = 9.0
brick.inputs['Mortar Size'].default_value = 0.36   # mortar grande = cartas pequenas esparsas
brick.inputs['Color1'].default_value = (0.78, 0.72, 0.60, 1)  # carta cream
brick.inputs['Color2'].default_value = (0.78, 0.72, 0.60, 1)
brick.inputs['Mortar'].default_value = (0, 0, 0, 1)            # mortar preto = mask
brick.offset = 0.7
# Mask: so algumas células viram carta -> noise gate
noise_g = nt.nodes.new('ShaderNodeTexNoise'); noise_g.location = (-650, 200)
noise_g.inputs['Scale'].default_value = 7.0
gate = nt.nodes.new('ShaderNodeMath'); gate.operation = 'GREATER_THAN'; gate.location = (-450, 200)
gate.inputs[1].default_value = 0.72   # ~25% das celulas
nt.links.new(noise_g.outputs['Fac'], gate.inputs[0])
# brick fac (1 onde carta) * gate
mult = nt.nodes.new('ShaderNodeMath'); mult.operation = 'MULTIPLY'; mult.location = (-300, 300)
# brick color->bw via fac: usar saida Fac do brick invertida (fac=1 mortar)
inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.location = (-450, 420)
inv.inputs[0].default_value = 1.0
nt.links.new(brick.outputs['Fac'], inv.inputs[1])
nt.links.new(inv.outputs[0], mult.inputs[0])
nt.links.new(gate.outputs[0], mult.inputs[1])
# Mix teal_damask <-> carta_cream
mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.location = (60, 260)
mix.inputs['B'].default_value = (0.70, 0.63, 0.50, 1)  # carta envelhecida
if old_ramp:
    nt.links.new(old_ramp.outputs['Color'], mix.inputs['A'])
nt.links.new(mult.outputs[0], mix.inputs['Factor'])
# Re-link base color
for l in list(bsdf.inputs['Base Color'].links):
    nt.links.remove(l)
nt.links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
print('card prints added to saia')

# ===== 3. Gold trim sutil no corpete via z-band emission-ish =====
# (borda corpete z 1.06-1.09 e 1.32-1.35 -> tom gold via geometry z mask)
geo = nt.nodes.new('ShaderNodeNewGeometry'); geo.location = (-900, -350)
sep = nt.nodes.new('ShaderNodeSeparateXYZ'); sep.location = (-750, -350)
nt.links.new(geo.outputs['Position'], sep.inputs['Vector'])
# band 1: corpete top (1.31-1.345)
b1a = nt.nodes.new('ShaderNodeMath'); b1a.operation = 'GREATER_THAN'; b1a.inputs[1].default_value = 1.310; b1a.location = (-600, -300)
b1b = nt.nodes.new('ShaderNodeMath'); b1b.operation = 'LESS_THAN'; b1b.inputs[1].default_value = 1.345; b1b.location = (-600, -440)
nt.links.new(sep.outputs['Z'], b1a.inputs[0])
nt.links.new(sep.outputs['Z'], b1b.inputs[0])
band1 = nt.nodes.new('ShaderNodeMath'); band1.operation = 'MULTIPLY'; band1.location = (-450, -370)
nt.links.new(b1a.outputs[0], band1.inputs[0])
nt.links.new(b1b.outputs[0], band1.inputs[1])
# band 2: cintura (1.055-1.085)
b2a = nt.nodes.new('ShaderNodeMath'); b2a.operation = 'GREATER_THAN'; b2a.inputs[1].default_value = 1.055; b2a.location = (-600, -580)
b2b = nt.nodes.new('ShaderNodeMath'); b2b.operation = 'LESS_THAN'; b2b.inputs[1].default_value = 1.085; b2b.location = (-600, -720)
nt.links.new(sep.outputs['Z'], b2a.inputs[0])
nt.links.new(sep.outputs['Z'], b2b.inputs[0])
band2 = nt.nodes.new('ShaderNodeMath'); band2.operation = 'MULTIPLY'; band2.location = (-450, -650)
nt.links.new(b2a.outputs[0], band2.inputs[0])
nt.links.new(b2b.outputs[0], band2.inputs[1])
bands = nt.nodes.new('ShaderNodeMath'); bands.operation = 'ADD'; bands.location = (-300, -500)
nt.links.new(band1.outputs[0], bands.inputs[0])
nt.links.new(band2.outputs[0], bands.inputs[1])
# Mix gold
mix2 = nt.nodes.new('ShaderNodeMix'); mix2.data_type = 'RGBA'; mix2.location = (240, 100)
mix2.inputs['B'].default_value = (0.55, 0.40, 0.13, 1)
nt.links.new(mix.outputs['Result'], mix2.inputs['A'])
nt.links.new(bands.outputs[0], mix2.inputs['Factor'])
for l in list(bsdf.inputs['Base Color'].links):
    nt.links.remove(l)
nt.links.new(mix2.outputs['Result'], bsdf.inputs['Base Color'])
# metallic nas bands
mixM = nt.nodes.new('ShaderNodeMath'); mixM.operation = 'MULTIPLY'; mixM.location = (240, -150)
mixM.inputs[1].default_value = 0.9
nt.links.new(bands.outputs[0], mixM.inputs[0])
nt.links.new(mixM.outputs[0], bsdf.inputs['Metallic'])
print('gold trims added (corpete top + cintura)')

bpy.ops.wm.save_mainfile()
print('POLISH DONE + SAVED')
