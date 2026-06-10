import bpy

body = bpy.data.objects['Body']
# corpo vira colisor
if not any(m.type == 'COLLISION' for m in body.modifiers):
    c = body.modifiers.new('Coll', 'COLLISION')
    c.settings.thickness_outer = 0.004

sc = bpy.context.scene
sc.frame_start = 1
sc.frame_end = 36

def drape(name, pin_z):
    ob = bpy.data.objects.get(name)
    if not ob:
        print(f'{name} MISSING'); return
    # pin: verts acima de pin_z (cintura)
    pg = ob.vertex_groups.get('PIN') or ob.vertex_groups.new(name='PIN')
    idx = [v.index for v in ob.data.vertices if v.co.z >= pin_z]
    pg.add(idx, 1.0, 'REPLACE')
    cl = ob.modifiers.new('Cloth', 'CLOTH')
    cl.settings.quality = 8
    cl.settings.mass = 0.22
    cl.settings.tension_stiffness = 32
    cl.settings.compression_stiffness = 22
    cl.settings.shear_stiffness = 16
    cl.settings.bending_stiffness = 1.5
    cl.settings.vertex_group_mass = 'PIN'
    cl.collision_settings.use_collision = True
    cl.collision_settings.distance_min = 0.004
    cl.collision_settings.collision_quality = 3
    cl.collision_settings.use_self_collision = False
    # cloth ANTES do armature na stack (drape em rest, rig deforma depois)
    while ob.modifiers.find('Cloth') > 0 and ob.modifiers[ob.modifiers.find('Cloth')-1].type != 'SOLIDIFY':
        bpy.context.view_layer.objects.active = ob
        try:
            bpy.ops.object.modifier_move_up(modifier='Cloth')
        except Exception:
            break
    sc.frame_set(1)
    for f in range(1, 37):
        sc.frame_set(f)
    # congelar shape drapeada: mesh evaluated SEM armature (desligar display do armature antes do eval)
    am = next((m for m in ob.modifiers if m.type == 'ARMATURE'), None)
    if am: am.show_viewport = False
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me_new = bpy.data.meshes.new_from_object(ev)
    # transferir materiais
    old = ob.data
    ob.data = me_new
    for mat in old.materials:
        if mat and mat.name not in [m.name for m in me_new.materials if m]:
            me_new.materials.append(mat)
    for m in list(ob.modifiers):
        if m.type in ('CLOTH', 'SOLIDIFY'):
            ob.modifiers.remove(m)
    if am: am.show_viewport = True
    bpy.data.meshes.remove(old)
    # re-add solidify
    s = ob.modifiers.new('Sol', 'SOLIDIFY'); s.thickness = 0.002; s.offset = 1.0
    # virar colisor pra proxima camada
    cc = ob.modifiers.new('Coll', 'COLLISION')
    cc.settings.thickness_outer = 0.0025
    print(f'{name}: drape baked, verts={len(ob.data.vertices)}')

# ordem: interna -> externa (cada baked vira colisor da proxima)
drape('P_Saia_Renda', 1.018)
drape('P_Saia_Cream', 1.022)
drape('P_Sobressaia', 1.028)

# remover collision das saias (so serviu pro processo) - manter so do corpo
for nm in ['P_Saia_Renda', 'P_Saia_Cream', 'P_Sobressaia']:
    ob = bpy.data.objects.get(nm)
    if ob:
        for m in list(ob.modifiers):
            if m.type == 'COLLISION':
                ob.modifiers.remove(m)
sc.frame_set(1)
bpy.ops.wm.save_mainfile()
print('CLOTH DRAPE DONE')
