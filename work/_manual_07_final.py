import bpy, math, os

arm = bpy.data.objects['Alice_Base_Rig']
dress = bpy.data.objects['PA_AliceChapeleiroDress']
body = bpy.data.objects['Alice_Base_Body']

# 1. Reset pose
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
for pb in arm.pose.bones:
    pb.rotation_euler = (0, 0, 0)
    pb.rotation_quaternion = (1, 0, 0, 0)
bpy.ops.object.mode_set(mode='OBJECT')

# 2. Chapeu fix: regiao topo deve ser teal escuro (estava claro no back)
IDX = {m.name: i for i, m in enumerate(dress.data.materials)}
fixed = 0
for poly in dress.data.polygons:
    c = dress.matrix_world @ poly.center
    if c.z > 1.60:
        if poly.material_index != IDX['MAT_Teal_Fabric']:
            poly.material_index = IDX['MAT_Teal_Fabric']; fixed += 1
print(f'hat fixed: {fixed}')

# 3. Smooth shading ambos
for o in [dress, body]:
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.shade_smooth()

# 4. UV pro bake 4K: garante UV layer
if not dress.data.uv_layers:
    bpy.context.view_layer.objects.active = dress
    bpy.ops.object.select_all(action='DESELECT'); dress.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.cube_project(cube_size=2.0)
    bpy.ops.object.mode_set(mode='OBJECT')
print(f'uv layers: {len(dress.data.uv_layers)}')

# 5. Bake DIFFUSE 4K (todos materiais -> 1 textura)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
try: sc.cycles.device = 'GPU'
except: pass
sc.cycles.samples = 24
img = bpy.data.images.get('dress_final_4k')
if img: bpy.data.images.remove(img)
img = bpy.data.images.new('dress_final_4k', width=4096, height=4096, alpha=False)

# add bake target node em TODOS materiais do dress
for m in dress.data.materials:
    nt = m.node_tree
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = img
    tex.name = 'BAKE_TARGET'
    nt.nodes.active = tex

bpy.ops.object.select_all(action='DESELECT')
dress.select_set(True); bpy.context.view_layer.objects.active = dress
sc.render.bake.use_selected_to_active = False
try:
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})
    img.filepath_raw = r'D:/Alice/tools/auto-rig-fix/work/textures_manual/dress_final_diffuse_4k.png'
    os.makedirs(r'D:/Alice/tools/auto-rig-fix/work/textures_manual', exist_ok=True)
    img.file_format = 'PNG'
    img.save()
    print('BAKED 4K diffuse')
except Exception as e:
    print(f'bake fail: {e}')

# remove bake nodes (mantem materiais procedurais como final - mais nitido que bake)
for m in dress.data.materials:
    nt = m.node_tree
    t = nt.nodes.get('BAKE_TARGET')
    if t: nt.nodes.remove(t)

# 6. Save .blend
bpy.ops.wm.save_as_mainfile(filepath=r'D:/Alice/tools/auto-rig-fix/work/alice_chapeleiro_MANUAL.blend')
print('SAVED blend')

# 7. Export GLB final (materiais procedurais viram bake no export? nao - export usa bake automatico do gltf para procedural? NAO suporta. GLB vai com cores base)
bpy.ops.object.select_all(action='DESELECT')
dress.select_set(True); body.select_set(True); arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.gltf(
    filepath=r'D:/Alice/tools/auto-rig-fix/work/alice_chapeleiro_MANUAL.glb',
    use_selection=True, export_format='GLB', export_apply=False,
    export_materials='EXPORT', export_skins=True)
print('EXPORTED GLB FINAL')
