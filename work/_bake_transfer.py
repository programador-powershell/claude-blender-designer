import bpy

scan_col = bpy.data.collections.get('Scan_Trellis')
scan_objs = [o for o in scan_col.objects if o.type == 'MESH']
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
try:
    sc.cycles.device = 'GPU'
except Exception:
    pass
sc.cycles.samples = 16  # bake diffuse color: poucos samples bastam
sc.render.bake.use_pass_direct = False
sc.render.bake.use_pass_indirect = False
sc.render.bake.use_selected_to_active = True
sc.render.bake.cage_extrusion = 0.10
sc.render.bake.max_ray_distance = 0.25

TARGETS = ['O_Sobressaia', 'O_SaiaCream', 'O_Corpete']
for tname in TARGETS:
    ob = bpy.data.objects.get(tname)
    if not ob:
        print('MISSING', tname); continue
    # UV
    bpy.context.view_layer.objects.active = ob
    for o in bpy.data.objects: o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    try:
        bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.004)
    except Exception:
        bpy.ops.uv.cube_project(cube_size=0.5)
    bpy.ops.object.mode_set(mode='OBJECT')
    # imagem alvo
    img_name = f'BAKE_{tname}'
    img = bpy.data.images.get(img_name)
    if not img:
        img = bpy.data.images.new(img_name, 1024, 1024, alpha=False)
    # node de imagem ATIVO no material da peça
    mat = ob.data.materials[0]
    nt = mat.node_tree
    node = nt.nodes.get('BakeTarget')
    if not node:
        node = nt.nodes.new('ShaderNodeTexImage')
        node.name = 'BakeTarget'
    node.image = img
    nt.nodes.active = node
    # selecao: scan (sources) + peça (active)
    for o in bpy.data.objects: o.select_set(False)
    for s in scan_objs: s.select_set(True)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    try:
        bpy.ops.object.bake(type='DIFFUSE')
        # salvar
        img.filepath_raw = f'D:/Alice/tools/auto-rig-fix/work/swatches/{img_name}.png'
        img.file_format = 'PNG'
        img.save()
        # ligar no Base Color (UV map agora!)
        bsdf = nt.nodes.get('Principled BSDF')
        # remover link antigo de base color
        for l in list(nt.links):
            if l.to_node == bsdf and l.to_socket.name == 'Base Color':
                nt.links.remove(l)
        uvn = nt.nodes.get('BakeUV')
        if not uvn:
            uvn = nt.nodes.new('ShaderNodeUVMap')
            uvn.name = 'BakeUV'
        nt.links.new(uvn.outputs['UV'], node.inputs['Vector'])
        nt.links.new(node.outputs['Color'], bsdf.inputs['Base Color'])
        print(f'BAKED {tname}')
    except Exception as e:
        print(f'BAKE FAIL {tname}: {str(e)[:120]}')

# esconder scan de novo
for o in scan_objs:
    o.hide_render = True
    o.hide_viewport = True
bpy.ops.wm.save_mainfile()
print('BAKE TRANSFER DONE')
