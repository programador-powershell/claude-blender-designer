import bpy, math
from mathutils import Vector

body = bpy.data.objects['AliceMesh']

# Body collision pra cloth
for m in list(body.modifiers):
    if m.type == 'COLLISION': body.modifiers.remove(m)
col = body.modifiers.new('Collision','COLLISION')
col.settings.thickness_outer = 0.003

def make_panel_skirt(name, n_panels=6, waist_r=0.155, hem_r=0.34, z_top=1.04, z_bot=0.58,
                      res_u=10, res_v=16, gap=0.025, mat=None):
    """Saia por paineis de costureira: n paineis trapezoidais em volta do corpo
    + sewing edges entre bordas adjacentes. Cloth sim costura e drapeia."""
    verts = []; faces = []; sew_edges = []
    panel_pts = []  # [(panel, row, col)] -> vert index
    for p in range(n_panels):
        a0 = 2*math.pi*p/n_panels + gap/waist_r
        a1 = 2*math.pi*(p+1)/n_panels - gap/waist_r
        grid = {}
        for r in range(res_v+1):
            t = r/res_v
            z = z_top*(1-t) + z_bot*t
            rad = waist_r*(1-t) + hem_r*t
            for c_ in range(res_u+1):
                u = c_/res_u
                a = a0*(1-u) + a1*u
                vi = len(verts)
                verts.append((rad*math.cos(a), rad*math.sin(a)*0.85, z))
                grid[(r,c_)] = vi
        for r in range(res_v):
            for c_ in range(res_u):
                faces.append((grid[(r,c_)], grid[(r,c_+1)], grid[(r+1,c_+1)], grid[(r+1,c_)]))
        panel_pts.append(grid)
    # SEWING: borda direita do painel p <-> borda esquerda do painel p+1
    for p in range(n_panels):
        gA = panel_pts[p]; gB = panel_pts[(p+1) % n_panels]
        for r in range(res_v+1):
            sew_edges.append((gA[(r,res_u)], gB[(r,0)]))
    me = bpy.data.meshes.new(name+'_Mesh')
    all_edges = sew_edges  # face edges criadas automaticamente
    me.from_pydata(verts, all_edges, faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if mat: ob.data.materials.append(mat)
    # Pin group: cintura (row 0)
    vg = ob.vertex_groups.new(name='PIN')
    pin_idx = []
    for p in range(n_panels):
        for c_ in range(res_u+1):
            pin_idx.append(panel_pts[p][(0,c_)])
    vg.add(pin_idx, 1.0, 'REPLACE')
    # Cloth com SEWING
    cl = ob.modifiers.new('Cloth','CLOTH')
    cl.settings.use_sewing_springs = True
    cl.settings.sewing_force_max = 8.0
    cl.settings.quality = 8
    cl.settings.mass = 0.3
    cl.settings.tension_stiffness = 20
    cl.settings.compression_stiffness = 12
    cl.settings.shear_stiffness = 8
    cl.settings.bending_stiffness = 0.4
    cl.settings.vertex_group_mass = 'PIN'
    cl.collision_settings.use_collision = True
    cl.collision_settings.distance_min = 0.004
    cl.collision_settings.use_self_collision = True
    cl.collision_settings.self_distance_min = 0.003
    return ob

m_tealD = bpy.data.materials.get('MAT_TealDamask')
if not m_tealD:
    m_tealD = bpy.data.materials.new('MAT_TealDamask'); m_tealD.use_nodes = True
    b = m_tealD.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (0.045, 0.085, 0.066, 1)
    b.inputs['Roughness'].default_value = 0.78
m_cream = bpy.data.materials.get('MAT_CreamL')
if not m_cream:
    m_cream = bpy.data.materials.new('MAT_CreamL'); m_cream.use_nodes = True
    b = m_cream.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (0.80, 0.74, 0.62, 1)
    b.inputs['Roughness'].default_value = 0.85
m_blk = bpy.data.materials.get('MAT_BlkLace')
if not m_blk:
    m_blk = bpy.data.materials.new('MAT_BlkLace'); m_blk.use_nodes = True
    b = m_blk.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (0.035, 0.03, 0.03, 1)
    b.inputs['Roughness'].default_value = 0.9

# 3 camadas de saia por paineis costurados (cloth sim real)
make_panel_skirt('SKIRT_Lace_Black', 6, 0.150, 0.36, 1.03, 0.54, mat=m_blk)
make_panel_skirt('SKIRT_Cream',      6, 0.155, 0.33, 1.035, 0.60, mat=m_cream)
make_panel_skirt('SKIRT_Teal',       6, 0.160, 0.30, 1.04, 0.66, mat=m_tealD)

# ===== RODAR SIM 60 frames =====
sc = bpy.context.scene
sc.frame_start = 1; sc.frame_end = 60
for f in range(1, 61):
    sc.frame_set(f)
print('sim 60 frames done')

# Aplicar cloth no estado final (drape baked)
dg = bpy.context.evaluated_depsgraph_get()
for nm in ['SKIRT_Lace_Black','SKIRT_Cream','SKIRT_Teal']:
    ob = bpy.data.objects[nm]
    ob_eval = ob.evaluated_get(dg)
    me_new = bpy.data.meshes.new_from_object(ob_eval)
    old = ob.data
    ob.data = me_new
    for m in list(ob.modifiers):
        if m.type == 'CLOTH': ob.modifiers.remove(m)
    bpy.data.meshes.remove(old)
    # Solidify final
    s = ob.modifiers.new('Sol','SOLIDIFY'); s.thickness = 0.002; s.offset = 1.0
    bpy.context.view_layer.objects.active = ob
    for o in bpy.data.objects: o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.shade_smooth()
    print(f'{nm}: drape applied, verts={len(ob.data.vertices)}')

bpy.ops.wm.save_mainfile()
print('SEWING SIM DONE')
