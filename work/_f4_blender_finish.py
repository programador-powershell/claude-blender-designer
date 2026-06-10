import bpy, math, sys
from mathutils import Vector

GLB = sys.argv[-1] if sys.argv[-1].endswith('.glb') else r'D:/Alice/tools/auto-rig-fix/work/meshes_3d/chapeleiro_trellis_tex.glb'

# ===== FASE 4: import + limpeza + separacao + fit + rig =====
pre = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=GLB)
new = [o for o in bpy.data.objects if o not in pre and o.type == 'MESH']
print('importados:', [o.name for o in new])

col = bpy.data.collections.get('Scan_Trellis')
if not col:
    col = bpy.data.collections.new('Scan_Trellis')
    bpy.context.scene.collection.children.link(col)

rig = bpy.data.objects.get('HRig')
body = bpy.data.objects.get('HumanBody')

for ob in new:
    for c in ob.users_collection:
        c.objects.unlink(ob)
    col.objects.link(ob)
    # LIMPEZA: merge by distance + tris->quads + recalc normals
    bpy.context.view_layer.objects.active = ob
    for o in bpy.data.objects: o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0008)
    bpy.ops.mesh.tris_convert_to_quads()
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.shade_smooth()

# FIT: normalizar escala/posicao ao tamanho do corpo (1.70m em pe na origem)
if new:
    root = new[0]
    # bbox conjunto
    mins = Vector((1e9,)*3); maxs = Vector((-1e9,)*3)
    for ob in new:
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            mins = Vector(map(min, mins, w)); maxs = Vector(map(max, maxs, w))
    h = maxs.z - mins.z
    if h > 0.01:
        s = 1.78 / h  # ligeiramente maior que o corpo (roupa+chapeu)
        for ob in new:
            ob.scale = ob.scale * s
        bpy.context.view_layer.update()
        mins2 = Vector((1e9,)*3); maxs2 = Vector((-1e9,)*3)
        for ob in new:
            for c in ob.bound_box:
                w = ob.matrix_world @ Vector(c)
                mins2 = Vector(map(min, mins2, w)); maxs2 = Vector(map(max, maxs2, w))
        for ob in new:
            ob.location.z -= mins2.z
            ob.location.x -= (maxs2.x + mins2.x) / 2
            ob.location.y -= (maxs2.y + mins2.y) / 2

# SEPARACAO POR PARTES: by loose parts no maior mesh
if new:
    main = max(new, key=lambda o: len(o.data.vertices))
    bpy.context.view_layer.objects.active = main
    for o in bpy.data.objects: o.select_set(False)
    main.select_set(True)
    try:
        bpy.ops.mesh.separate(type='LOOSE')
    except Exception as e:
        print('separate:', e)
    parts = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    print(f'partes apos separacao: {len(parts)}')
    # nomear por altura (chapeu/cabeca/torso/saia/pernas)
    for p in parts:
        bb = [p.matrix_world @ Vector(c) for c in p.bound_box]
        zc = sum(b.z for b in bb) / 8
        nv = len(p.data.vertices)
        zona = 'chapeu' if zc > 1.62 else ('cabeca' if zc > 1.40 else ('torso' if zc > 1.00 else ('saia' if zc > 0.55 else 'pernas')))
        p.name = f'SCAN_{zona}_{nv}'

# RIG: proximity skinning ao HRig (bones de corpo+saia)
if rig:
    allowed_prefix = ('Hips','Spine','Neck','Head','Clavicle','UpperArm','ForeArm','Hand',
                      'Thigh','Shin','Foot','Toe','Skirt','Breast','Butt')
    segs = []
    for b in rig.data.bones:
        if not b.use_deform or not b.name.startswith(allowed_prefix): continue
        h = rig.matrix_world @ b.head_local
        t = rig.matrix_world @ b.tail_local
        segs.append((b.name, h, t, (t-h), max((t-h).length_squared, 1e-12)))
    for ob in col.objects:
        if ob.type != 'MESH': continue
        ob.vertex_groups.clear()
        vgs = {}
        mw = ob.matrix_world
        for v in ob.data.vertices:
            p = mw @ v.co
            ds = []
            for n, h, t, ab, L2 in segs:
                tt = max(0.0, min(1.0, (p-h).dot(ab)/L2))
                ds.append(((p-(h+ab*tt)).length, n))
            ds.sort()
            ws = [(1.0/max(d,1e-5)**2, n) for d, n in ds[:3]]
            s2 = sum(w for w,_ in ws)
            for w, n in ws:
                if n not in vgs: vgs[n] = ob.vertex_groups.new(name=n)
                vgs[n].add([v.index], w/s2, 'REPLACE')
        am = ob.modifiers.new('Armature','ARMATURE'); am.object = rig
        bpy.context.view_layer.update()
        mw0 = ob.matrix_world.copy()
        ob.parent = rig; ob.matrix_world = mw0
    print('scan rigado ao HRig')

bpy.ops.wm.save_mainfile()
print('FASE 4 DONE')
