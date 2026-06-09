import bpy, math
from mathutils import Vector

rig = bpy.data.objects['AliceRig']
body = bpy.data.objects['AliceMesh']

# ===== FIX MANGAS: suavizar (subsurf) =====
for S in ['L','R']:
    m = bpy.data.objects.get(f'GD_Manga_{S}')
    if m and not any(md.type=='SUBSURF' for md in m.modifiers):
        sb = m.modifiers.new('Subd','SUBSURF'); sb.levels = 1; sb.render_levels = 2

# ===== RIG TODAS PECAS GD_ (proximity skinning por peca) =====
segs = []
for b in rig.data.bones:
    if not b.use_deform: continue
    h = rig.matrix_world @ b.head_local
    t = rig.matrix_world @ b.tail_local
    segs.append((b.name, h, t))

def dseg(p, a, bb):
    ab = bb - a
    L2 = ab.length_squared
    if L2 < 1e-12: return (p-a).length
    t = max(0.0, min(1.0, (p-a).dot(ab)/L2))
    return (p - (a + ab*t)).length

pieces = [o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('GD_')]
print(f'rigging {len(pieces)} pecas...')
for ob in pieces:
    ob.vertex_groups.clear()
    for m in list(ob.modifiers):
        if m.type == 'ARMATURE': ob.modifiers.remove(m)
    vgs = {}
    mw = ob.matrix_world
    for v in ob.data.vertices:
        wp = mw @ v.co
        d = sorted(((dseg(wp,h,t), n) for n,h,t in segs))[:3]
        ws = [(1.0/max(di,1e-5)**2, n) for di,n in d]
        s = sum(w for w,_ in ws)
        for w, n in ws:
            if n not in vgs: vgs[n] = ob.vertex_groups.new(name=n)
            vgs[n].add([v.index], w/s, 'REPLACE')
    am = ob.modifiers.new('Armature','ARMATURE'); am.object = rig
    # Armature primeiro na stack
    while ob.modifiers.find('Armature') > 0:
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_move_up(modifier='Armature')
    mwx = ob.matrix_world.copy()
    ob.parent = rig; ob.matrix_world = mwx
print('all pieces rigged (proximity 3-bone)')

# Weight smooth nas pecas de tecido (gradiente pro - vestido.mp4 style)
cloth_pieces = ['GD_Saia_Lace','GD_Saia_Cream','GD_Saia_Teal_T1','GD_Saia_Teal_T2',
                'GD_Corpete','GD_Manga_L','GD_Manga_R','GD_Cabelo_Massa']
for nm in cloth_pieces:
    ob = bpy.data.objects.get(nm)
    if not ob: continue
    bpy.context.view_layer.objects.active = ob
    for o in bpy.data.objects: o.select_set(False)
    ob.select_set(True)
    try:
        bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
        bpy.ops.object.vertex_group_smooth(group_select_mode='ALL', factor=0.5, repeat=4, expand=0.3)
        bpy.ops.object.vertex_group_normalize_all(lock_active=False)
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception as e:
        print(f'{nm} smooth fail: {e}')
print('weights smoothed')

# ===== JIGGLE BONES (mecanica.mp4): wiggle-bones addon nos Breast/Butt/Skirt =====
try:
    import addon_utils
    addon_utils.enable('bl_ext.blender_org.wiggle_bones', default_set=True)
    # wiggle 2: scene props + per-bone
    sc = bpy.context.scene
    if hasattr(sc, 'wiggle_enable'): sc.wiggle_enable = True
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='POSE')
    jiggle_bones = ['Breast_L','Breast_R','Butt_L','Butt_R','SkirtF','SkirtB','SkirtL','SkirtR']
    n_ok = 0
    for bn in jiggle_bones:
        pb = rig.pose.bones.get(bn)
        if not pb: continue
        for attr, val in [('wiggle_enable', True), ('wiggle_mute', False),
                          ('wiggle_stiff', 0.55), ('wiggle_damp', 0.6),
                          ('wiggle_mass', 0.4), ('wiggle_stretch', 0.0)]:
            if hasattr(pb, attr):
                try: setattr(pb, attr, val); n_ok += 1
                except Exception: pass
    bpy.ops.object.mode_set(mode='OBJECT')
    print(f'jiggle configured: {n_ok} props set')
except Exception as e:
    print(f'wiggle addon: {e}')

bpy.ops.wm.save_mainfile()
print('RIG ALL DONE + SAVED')
