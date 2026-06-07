import bpy, math, os
OUT = r"D:/Alice/tools/auto-rig-fix/work/simulation"
os.makedirs(OUT, exist_ok=True)

# Hide all PA_* pieces (only body+rig visible)
for o in bpy.data.objects:
    if o.name.startswith('PA_'):
        o.hide_render = True

def cam(name, loc, rot):
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    c = bpy.data.objects.get(name) or bpy.data.objects.new(name, cd)
    if not c.users_collection: bpy.context.scene.collection.objects.link(c)
    c.location = loc; c.rotation_euler = rot
    c.data.type='ORTHO'; c.data.ortho_scale=2.2
    return c

cam('SIM_FRONT', (0,-4,1.0), (math.radians(90),0,0))
cam('SIM_SIDE',  (4,0,1.0),  (math.radians(90),0,math.radians(90)))
cam('SIM_BACK',  (0,4,1.0),  (math.radians(90),0,math.radians(180)))
sc = bpy.context.scene
sc.render.resolution_x = 600; sc.render.resolution_y = 800
sc.render.image_settings.file_format = 'PNG'
files=[]
for cn in ['SIM_FRONT','SIM_SIDE','SIM_BACK']:
    sc.camera = bpy.data.objects[cn]
    p = os.path.join(OUT, f'body_{cn}.png')
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    files.append(p)
# Restore visibility
for o in bpy.data.objects:
    if o.name.startswith('PA_'):
        o.hide_render = False
print('BODY RENDERS:', files)
