import bpy, math
from mathutils import Vector

body = bpy.data.objects['AliceMesh']

# Remover saias falhas
for nm in ['SKIRT_Lace_Black','SKIRT_Cream','SKIRT_Teal']:
    o = bpy.data.objects.get(nm)
    if o: bpy.data.objects.remove(o, do_unlink=True)
for me in list(bpy.data.meshes):
    if me.users == 0: bpy.data.meshes.remove(me)

def make_skirt(name, waist_r, hem_r, z_top, z_bot, mat, flare_wave=0.0):
    """Saia conica continua (sem gap) + pin cintura. Cloth assenta/drapeia (nao costura do zero).
    flare_wave: ondulacao no hem pra iniciar folds."""
    SEGU = 64; SEGV = 14
    verts=[]; faces=[]
    for r in range(SEGV+1):
        t = r/SEGV
        z = z_top*(1-t) + z_bot*t
        rad = waist_r*(1-t) + hem_r*t
        for i in range(SEGU):
            a = 2*math.pi*i/SEGU
            rr = rad * (1.0 + flare_wave*t*math.sin(8*a))
            verts.append((rr*math.cos(a), rr*math.sin(a)*0.88, z))
    for r in range(SEGV):
        for i in range(SEGU):
            j=(i+1)%SEGU
            faces.append((r*SEGU+i, r*SEGU+j, (r+1)*SEGU+j, (r+1)*SEGU+i))
    me = bpy.data.meshes.new(name+'_Mesh')
    me.from_pydata(verts, [], faces); me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    vg = ob.vertex_groups.new(name='PIN')
    vg.add(list(range(SEGU*2)), 1.0, 'REPLACE')   # 2 rows topo pinadas
    cl = ob.modifiers.new('Cloth','CLOTH')
    cl.settings.quality = 10
    cl.settings.mass = 0.25
    cl.settings.tension_stiffness = 40
    cl.settings.compression_stiffness = 25
    cl.settings.shear_stiffness = 18
    cl.settings.bending_stiffness = 1.2
    cl.settings.vertex_group_mass = 'PIN'
    cl.collision_settings.use_collision = True
    cl.collision_settings.distance_min = 0.005
    cl.collision_settings.collision_quality = 4
    return ob

def bake_and_fix(ob, frames=30):
    sc = bpy.context.scene
    sc.frame_start = 1; sc.frame_end = frames
    sc.frame_set(1)
    for f in range(1, frames+1):
        sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me_new = bpy.data.meshes.new_from_object(ev)
    old = ob.data; ob.data = me_new
    for m in list(ob.modifiers):
        if m.type == 'CLOTH': ob.modifiers.remove(m)
    bpy.data.meshes.remove(old)
    # vira colisor da proxima camada
    c = ob.modifiers.new('Coll','COLLISION')
    c.settings.thickness_outer = 0.003
    s = ob.modifiers.new('Sol','SOLIDIFY'); s.thickness = 0.0022; s.offset = 1.0
    bpy.context.view_layer.objects.active = ob
    for o in bpy.data.objects: o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.shade_smooth()
    print(f'{ob.name}: baked drape verts={len(ob.data.vertices)}')

m_teal = bpy.data.materials['MAT_TealDamask']
m_cream = bpy.data.materials['MAT_CreamL']
m_blk = bpy.data.materials['MAT_BlkLace']

# CAMADA 1: lace preta (interna, mais longa)
s1 = make_skirt('SKIRT_Lace', 0.150, 0.30, 1.02, 0.55, m_blk, flare_wave=0.05)
bake_and_fix(s1, 30)
# CAMADA 2: cream (media)
s2 = make_skirt('SKIRT_Cream', 0.155, 0.28, 1.025, 0.61, m_cream, flare_wave=0.06)
bake_and_fix(s2, 30)
# CAMADA 3: teal (externa, mais curta)
s3 = make_skirt('SKIRT_Teal', 0.160, 0.27, 1.03, 0.67, m_teal, flare_wave=0.07)
bake_and_fix(s3, 30)

bpy.ops.wm.save_mainfile()
print('SEQUENTIAL CLOTH DONE')
