import bpy, math, os

# Clean all
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
for m in list(bpy.data.materials):
    bpy.data.materials.remove(m)
for img in list(bpy.data.images):
    if img.users == 0: bpy.data.images.remove(img)

# Import best base: painted reverse GLB (real dress geometry + 33-bone rig)
bpy.ops.import_scene.gltf(filepath=r'D:/Alice/tools/auto-rig-fix/work/alice_chapeleiro_PAINTED.glb')

objs = {o.name: o for o in bpy.data.objects}
print('objects:', list(objs.keys()))
dress = next((o for o in bpy.data.objects if o.type=='MESH' and 'Dress' in o.name), None)
body = next((o for o in bpy.data.objects if o.type=='MESH' and ('Body' in o.name or 'Corpo' in o.name)), None)
arm = next((o for o in bpy.data.objects if o.type=='ARMATURE'), None)
if dress: print(f'dress: {dress.name} verts={len(dress.data.vertices)} vcols={len(dress.data.vertex_colors)} vgroups={len(dress.vertex_groups)}')
if body: print(f'body: {body.name} verts={len(body.data.vertices)}')
if arm: print(f'arm: {arm.name} bones={len(arm.data.bones)}')

# Studio lighting
bpy.ops.object.light_add(type='AREA', location=(2.5,-3,2.5))
key = bpy.context.object; key.name='L_KEY'; key.data.energy=1000; key.data.size=2.0
key.rotation_euler = (math.radians(55), 0, math.radians(35))
bpy.ops.object.light_add(type='AREA', location=(-2.5,-2,1.5))
fill = bpy.context.object; fill.name='L_FILL'; fill.data.energy=350; fill.data.size=2.0
fill.rotation_euler = (math.radians(70), 0, math.radians(-40))
bpy.ops.object.light_add(type='AREA', location=(0,3.5,2.2))
rim = bpy.context.object; rim.name='L_RIM'; rim.data.energy=700; rim.data.size=1.5
rim.rotation_euler = (math.radians(-55), 0, 0)

w = bpy.context.scene.world
w.use_nodes = True
bg = w.node_tree.nodes.get('Background')
if bg:
    bg.inputs[0].default_value = (0.12, 0.12, 0.14, 1.0)
    bg.inputs[1].default_value = 0.35

def cam(name, loc, rot):
    cd = bpy.data.cameras.new(name); c = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(c)
    c.location = loc; c.rotation_euler = rot
    c.data.type='ORTHO'; c.data.ortho_scale = 2.0
    return c

cam('CAM_FRONT', (0,-4,0.95), (math.radians(90),0,0))
cam('CAM_SIDE',  (4,0,0.95),  (math.radians(90),0,math.radians(90)))
cam('CAM_BACK',  (0,4,0.95),  (math.radians(90),0,math.radians(180)))

print('SETUP OK')
