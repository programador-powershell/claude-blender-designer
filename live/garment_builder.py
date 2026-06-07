# -*- coding: utf-8 -*-
from __future__ import annotations
import math, json
try:
    import bpy
except Exception:
    bpy = None

def _require_bpy():
    if bpy is None:
        raise RuntimeError('Este módulo precisa rodar dentro do Blender Python.')

def _mat(name, color, roughness=0.65, metallic=0.0, alpha=1.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        if 'Base Color' in bsdf.inputs: bsdf.inputs['Base Color'].default_value = color
        if 'Roughness' in bsdf.inputs: bsdf.inputs['Roughness'].default_value = roughness
        if 'Metallic' in bsdf.inputs: bsdf.inputs['Metallic'].default_value = metallic
        if alpha < 1 and 'Alpha' in bsdf.inputs:
            bsdf.inputs['Alpha'].default_value = alpha
            m.blend_method = 'BLEND'
    return m

def _create_materials(bp):
    return {s.id: _mat(f'PA_{s.id}', tuple(s.color), s.roughness, s.metallic, s.alpha) for s in bp.materials}

def _coll(name):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c

def _link(obj, coll):
    try: coll.objects.link(obj)
    except Exception: pass
    for c in list(obj.users_collection):
        if c != coll:
            try: c.objects.unlink(obj)
            except Exception: pass

def _mesh(name, verts, faces, material, coll):
    me = bpy.data.meshes.new(name+'_Mesh'); me.from_pydata(verts, [], faces); me.update()
    obj = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(obj)
    if material: obj.data.materials.append(material)
    _link(obj, coll)
    return obj

def _mods(obj, piece=None, arm=None):
    sol = obj.modifiers.new('PA_thickness_solidify','SOLIDIFY'); sol.thickness = float(getattr(piece,'thickness',0.004) or 0.004); sol.offset = 0
    sub = obj.modifiers.new('PA_soft_subdivision','SUBSURF'); sub.levels = 1; sub.render_levels = 1
    if arm:
        am = obj.modifiers.new('PA_armature_follow','ARMATURE'); am.object = arm
    if piece and getattr(piece,'physics','none') == 'cloth':
        cl = obj.modifiers.new('PA_cloth_sim','CLOTH')
        try:
            cl.settings.quality = 8; cl.settings.mass = 0.22; cl.settings.tension_stiffness = 18; cl.settings.compression_stiffness = 18; cl.settings.shear_stiffness = 8; cl.settings.air_damping = 1
        except Exception: pass
    return obj

def _ring_skirt(name, waist_radius, hem_radius, length, folds, segments, material, coll, z_top=0.94, front_gap=0.0):
    verts=[]; faces=[]; rings=10
    gap_half = float(front_gap) / max(hem_radius, 0.001)
    for r in range(rings+1):
        t=r/rings; z=z_top-length*t; rad=waist_radius*(1-t)+hem_radius*t
        for i in range(segments):
            ang=2*math.pi*i/segments
            rad_i = rad*0.78 if front_gap and abs(math.sin(ang)) < gap_half and math.cos(ang) < -0.25 else rad
            pleat=1.0+0.03*math.sin(folds*ang)*(0.25+0.75*t)
            verts.append((rad_i*pleat*math.cos(ang), rad_i*0.72*pleat*math.sin(ang), z))
    for r in range(rings):
        for i in range(segments): faces.append((r*segments+i, r*segments+(i+1)%segments, (r+1)*segments+(i+1)%segments, (r+1)*segments+i))
    return _mesh(name, verts, faces, material, coll)

def _torso_shell(name, mat, coll, z_min=0.86, z_max=1.45, rx_waist=0.23, ry_waist=0.16, rx_chest=0.34, ry_chest=0.20):
    verts=[]; faces=[]; seg=64; rings=8
    for r in range(rings+1):
        t=r/rings; z=z_min*(1-t)+z_max*t; rx=rx_waist*(1-t)+rx_chest*t; ry=ry_waist*(1-t)+ry_chest*t
        for i in range(seg):
            a=2*math.pi*i/seg; x=rx*math.cos(a); y=ry*math.sin(a); zz=z
            if y < -0.05 and zz > 1.25: zz -= 0.08*(1-abs(x)/max(rx,0.001))
            verts.append((x,y,zz))
    for r in range(rings):
        for i in range(seg): faces.append((r*seg+i,r*seg+(i+1)%seg,(r+1)*seg+(i+1)%seg,(r+1)*seg+i))
    return _mesh(name, verts, faces, mat, coll)

def _front_panel(name, width_top, width_bottom, length, z_top, curve, mat, coll):
    rows=12; verts=[]; faces=[]
    for r in range(rows+1):
        t=r/rows; z=z_top-length*t; w=width_top*(1-t)+width_bottom*t; y=-0.33-curve*math.sin(math.pi*t)
        verts.append((-w/2,y,z)); verts.append((w/2,y,z))
    for r in range(rows): faces.append((2*r,2*r+1,2*r+3,2*r+2))
    return _mesh(name, verts, faces, mat, coll)

def _side_panel(name, side, width_top, width_bottom, length, mat, coll):
    s=1 if side=='left' else -1; rows=10; verts=[]; faces=[]
    for r in range(rows+1):
        t=r/rows; z=0.93-length*t; w=width_top*(1-t)+width_bottom*t; x=s*(0.25+0.18*t); y=-0.02+0.03*math.sin(t*math.pi)
        verts.append((x,y-w/2,z)); verts.append((x,y+w/2,z))
    for r in range(rows): faces.append((2*r,2*r+1,2*r+3,2*r+2))
    return _mesh(name, verts, faces, mat, coll)

def _puff_sleeve(name, side, radius, length, puffs, mat, coll):
    s=1 if side=='left' else -1; seg=32; rings=8; verts=[]; faces=[]; cx=s*0.40; cy=0; zc=1.34
    for r in range(rings+1):
        t=r/rings; x=cx+s*length*(t-0.5); rad=radius*(0.75+0.25*math.sin(math.pi*t))
        for i in range(seg):
            a=2*math.pi*i/seg; pleat=1+0.07*math.sin(puffs*a)
            verts.append((x,cy+rad*0.72*math.cos(a)*pleat,zc+rad*math.sin(a)*pleat))
    for r in range(rings):
        for i in range(seg): faces.append((r*seg+i,r*seg+(i+1)%seg,(r+1)*seg+(i+1)%seg,(r+1)*seg+i))
    return _mesh(name, verts, faces, mat, coll)

def _hem_ruffle(name, radius, z, height, waves, mat, coll):
    seg=waves*4; verts=[]; faces=[]
    for r in range(2):
        for i in range(seg):
            a=2*math.pi*i/seg; rr=radius*(1+0.035*math.sin(waves*a)); verts.append((rr*math.cos(a),rr*0.72*math.sin(a),z-height*r))
    for i in range(seg): faces.append((i,(i+1)%seg,seg+(i+1)%seg,seg+i))
    return _mesh(name, verts, faces, mat, coll)

def _curve(name, points, mat, bevel, coll):
    cu=bpy.data.curves.new(name,'CURVE'); cu.dimensions='3D'; cu.resolution_u=12; cu.bevel_depth=bevel; cu.bevel_resolution=2
    sp=cu.splines.new('POLY'); sp.points.add(len(points)-1)
    for p, co in zip(sp.points, points): p.co=(co[0],co[1],co[2],1)
    obj=bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(obj)
    if mat: obj.data.materials.append(mat)
    _link(obj, coll); return obj

def _find_armature(character_name=None):
    if character_name:
        c=[o for o in bpy.data.objects if o.type=='ARMATURE' and character_name.lower() in o.name.lower()]
        if c: return c[0]
    arms=[o for o in bpy.data.objects if o.type=='ARMATURE']
    return arms[0] if arms else None

def _bloomer_shorts(name, z_top, z_bot, waist_radius, leg_radius, ruffle_h, mat, coll):
    """Bloomer: waist band + 2 cylindrical legs + ruffle no hem de cada perna."""
    verts=[]; faces=[]; seg=24; rings_w=4; rings_l=8
    z_crotch = z_bot + (z_top - z_bot) * 0.45
    # Waist band (oval z_top -> z_crotch)
    for r in range(rings_w+1):
        t=r/rings_w; z = z_top*(1-t) + z_crotch*t
        rx = waist_radius*(1.0 - 0.05*t); ry = waist_radius*0.62*(1.0 - 0.05*t)
        for i in range(seg):
            a=2*math.pi*i/seg
            verts.append((rx*math.cos(a), ry*math.sin(a), z))
    for r in range(rings_w):
        for i in range(seg):
            faces.append((r*seg+i, r*seg+(i+1)%seg, (r+1)*seg+(i+1)%seg, (r+1)*seg+i))
    waist_top_ring = rings_w * seg  # last ring index
    # 2 leg cylinders puffy (x positive = left, x negative = right)
    leg_seg = 20
    for side in [-1, 1]:
        cx = side * waist_radius * 0.45
        leg_base = len(verts)
        for r in range(rings_l+1):
            t = r/rings_l
            z = z_crotch*(1-t) + z_bot*t
            # puffy bulge: max no mid (t=0.55) + flare no hem
            bulge = 1.0 + 0.45 * math.sin(math.pi * (0.20 + 0.80*t)) + 0.30*t
            rad = leg_radius * bulge
            for i in range(leg_seg):
                a = 2*math.pi*i/leg_seg
                # pleat radial fold
                pleat = 1.0 + 0.05 * math.sin(8*a) * (0.3 + 0.7*t)
                verts.append((cx + rad*pleat*math.cos(a), rad*pleat*0.85*math.sin(a), z))
        for r in range(rings_l):
            for i in range(leg_seg):
                faces.append((leg_base+r*leg_seg+i, leg_base+r*leg_seg+(i+1)%leg_seg,
                              leg_base+(r+1)*leg_seg+(i+1)%leg_seg, leg_base+(r+1)*leg_seg+i))
        # Ruffle ring no hem
        ruffle_base = len(verts)
        for i in range(leg_seg):
            a = 2*math.pi*i/leg_seg
            rr = leg_radius * 1.30 * (1.0 + 0.08*math.sin(8*a))
            verts.append((cx + rr*math.cos(a), rr*0.85*math.sin(a), z_bot))
            verts.append((cx + rr*math.cos(a), rr*0.85*math.sin(a), z_bot - ruffle_h))
        for i in range(leg_seg):
            j=(i+1)%leg_seg
            faces.append((ruffle_base+2*i, ruffle_base+2*j, ruffle_base+2*j+1, ruffle_base+2*i+1))
    return _mesh(name, verts, faces, mat, coll)

def _tube_segment(name, x_center, z_top, z_bot, radius, ry_ratio, segments, mat, coll, stripes=None):
    """Cilindro vertical de altura z_top->z_bot, raio rx=radius ry=radius*ry_ratio."""
    verts=[]; faces=[]; rings=8
    for r in range(rings+1):
        t=r/rings; z=z_top*(1-t)+z_bot*t
        for i in range(segments):
            a=2*math.pi*i/segments
            verts.append((x_center+radius*math.cos(a), radius*ry_ratio*math.sin(a), z))
    for r in range(rings):
        for i in range(segments):
            faces.append((r*segments+i, r*segments+(i+1)%segments, (r+1)*segments+(i+1)%segments, (r+1)*segments+i))
    return _mesh(name, verts, faces, mat, coll)

def _stocking_leg(name, side, z_top, z_bot, radius, mat, coll):
    """Meia: cilindro fino na coxa."""
    s=1 if side=='left' else -1
    return _tube_segment(name, s*0.10, z_top, z_bot, radius, 1.0, 32, mat, coll)

def _high_boot(name, side, z_top, z_bot, radius_shaft, radius_foot, mat, coll):
    """Bota cano alto + pé. Cone para shaft + cilindro foot."""
    s=1 if side=='left' else -1; verts=[]; faces=[]; seg=24
    rings=10
    for r in range(rings+1):
        t=r/rings; z=z_top*(1-t)+0.02*t
        rad = radius_shaft*(1-t)+radius_foot*t
        for i in range(seg):
            a=2*math.pi*i/seg
            verts.append((s*0.10+rad*math.cos(a), rad*math.sin(a), z))
    for r in range(rings):
        for i in range(seg):
            faces.append((r*seg+i, r*seg+(i+1)%seg, (r+1)*seg+(i+1)%seg, (r+1)*seg+i))
    obj=_mesh(name, verts, faces, mat, coll)
    # bico: cilindro horizontal frente
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=radius_foot, depth=0.18, location=(s*0.10, -0.08, 0.04))
    toe=bpy.context.object; toe.name=name+'_toe'; toe.rotation_euler[0]=math.radians(90)
    if mat: toe.data.materials.append(mat)
    _link(toe, coll)
    return obj

def _glove_forearm(name, side, z_top, z_bot, radius, mat, coll):
    """Luva fingerless: cilindro horizontal antebraço."""
    s=1 if side=='left' else -1; verts=[]; faces=[]; seg=24; rings=6
    x0=s*0.30; x1=s*0.60
    for r in range(rings+1):
        t=r/rings; x=x0*(1-t)+x1*t; z=z_top*(1-t)+z_bot*t
        rad=radius*(1+0.05*math.sin(t*math.pi))
        for i in range(seg):
            a=2*math.pi*i/seg
            verts.append((x, rad*math.cos(a), z+rad*math.sin(a)))
    for r in range(rings):
        for i in range(seg):
            faces.append((r*seg+i, r*seg+(i+1)%seg, (r+1)*seg+(i+1)%seg, (r+1)*seg+i))
    return _mesh(name, verts, faces, mat, coll)

def _choker_band(name, z, radius, height, mat, coll):
    """Gargantilha: torus achatado no pescoço."""
    seg=48; rings=4; verts=[]; faces=[]
    for r in range(rings+1):
        t=r/rings; zz=z + height*(t-0.5)
        for i in range(seg):
            a=2*math.pi*i/seg
            verts.append((radius*math.cos(a), radius*0.85*math.sin(a), zz))
    for r in range(rings):
        for i in range(seg):
            faces.append((r*seg+i, r*seg+(i+1)%seg, (r+1)*seg+(i+1)%seg, (r+1)*seg+i))
    return _mesh(name, verts, faces, mat, coll)

def _sash_band(name, z_top, z_bot, radius_x, radius_y, mat, coll):
    """Faixa de cintura: anel horizontal apertado."""
    seg=64; rings=4; verts=[]; faces=[]
    for r in range(rings+1):
        t=r/rings; z=z_top*(1-t)+z_bot*t
        for i in range(seg):
            a=2*math.pi*i/seg
            verts.append((radius_x*math.cos(a), radius_y*math.sin(a), z))
    for r in range(rings):
        for i in range(seg):
            faces.append((r*seg+i, r*seg+(i+1)%seg, (r+1)*seg+(i+1)%seg, (r+1)*seg+i))
    return _mesh(name, verts, faces, mat, coll)

def _bow_3d(name, z, width, height, depth, mat, coll):
    """Laço 3D nas costas: 2 loops + nó central + 2 fitas pendentes."""
    objs=[]
    for s in [-1, 1]:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.001, location=(s*width*0.5, 0.30, z))
        loop=bpy.context.object; loop.name=f'{name}_loop_{"L" if s<0 else "R"}'
        loop.scale=(width*0.45, depth, height*0.45)
        if mat: loop.data.materials.append(mat)
        _link(loop, coll); objs.append(loop)
    bpy.ops.mesh.primitive_cube_add(size=0.04, location=(0, 0.31, z))
    knot=bpy.context.object; knot.name=f'{name}_knot'; knot.scale=(0.8, 0.4, 1.0)
    if mat: knot.data.materials.append(mat)
    _link(knot, coll); objs.append(knot)
    for s in [-1, 1]:
        ribbon=_front_panel(f'{name}_ribbon_{"L" if s<0 else "R"}',
                            width*0.25, width*0.18, height*1.8, z, 0.02, mat, coll)
        ribbon.location.x=s*width*0.12; ribbon.location.y=0.32
    return objs[0] if objs else None

def _drape_side_asym(name, side, z_top, z_bot, width_top, width_bot, mat, coll):
    """Drape lateral assimétrico: painel curvo descendo do quadril."""
    s=1 if side=='right' else -1; rows=10; verts=[]; faces=[]
    for r in range(rows+1):
        t=r/rows; z=z_top*(1-t)+z_bot*t
        w=width_top*(1-t)+width_bot*t
        x_mid=s*(0.22+0.10*t); y_mid=-0.05+0.12*math.sin(t*math.pi)
        verts.append((x_mid+s*w*0.0, y_mid-w*0.5, z))
        verts.append((x_mid+s*w*1.0, y_mid+w*0.5, z))
    for r in range(rows): faces.append((2*r, 2*r+1, 2*r+3, 2*r+2))
    return _mesh(name, verts, faces, mat, coll)

def _tiered_lace_skirt(name, waist_radius, hem_radius, z_top, z_bot, tiers, mat, coll):
    """Saia em N tiers (renda) com babado entre cada tier."""
    seg=96; verts=[]; faces=[]
    tier_h=(z_top-z_bot)/tiers
    for tier in range(tiers):
        z0=z_top-tier*tier_h; z1=z_top-(tier+1)*tier_h
        t0=tier/tiers; t1=(tier+1)/tiers
        r0=waist_radius*(1-t0)+hem_radius*t0
        r1=waist_radius*(1-t1)+hem_radius*t1
        ring_base=len(verts)
        for i in range(seg):
            a=2*math.pi*i/seg; verts.append((r0*math.cos(a), r0*0.72*math.sin(a), z0))
        for i in range(seg):
            a=2*math.pi*i/seg
            ruffle=1+0.08*math.sin(24*a)
            verts.append((r1*ruffle*math.cos(a), r1*ruffle*0.72*math.sin(a), z1))
        for i in range(seg):
            faces.append((ring_base+i, ring_base+(i+1)%seg, ring_base+seg+(i+1)%seg, ring_base+seg+i))
    return _mesh(name, verts, faces, mat, coll)

def _build_piece(piece, mats, coll, arm):
    mat=mats.get(piece.material); p=piece.params or {}; name='PA_'+piece.id
    if piece.shape=='torso_shell': obj=_torso_shell(name, mat, coll)
    elif piece.shape=='corset': obj=_torso_shell(name, mat, coll, 1.14-p.get('height',.46)/2, 1.14+p.get('height',.46)/2, p.get('waist_radius',.26), p.get('waist_radius',.26)*.68, p.get('bust_radius',.36), p.get('bust_radius',.36)*.62)
    elif piece.shape=='skirt_ring': obj=_ring_skirt(name,p.get('waist_radius',.3),p.get('hem_radius',1.0),p.get('length',.7),p.get('folds',36),p.get('segments',144),mat,coll,front_gap=p.get('front_gap',0.0))
    elif piece.shape=='front_panel': obj=_front_panel(name,p.get('width_top',.35),p.get('width_bottom',.55),p.get('length',.65),p.get('z_top',.93),p.get('curve',.05),mat,coll)
    elif piece.shape=='side_panel': obj=_side_panel(name,p.get('side','left'),p.get('width_top',.25),p.get('width_bottom',.48),p.get('length',.62),mat,coll)
    elif piece.shape=='bow_tail': obj=_front_panel(name,p.get('width',.6),p.get('width',.6)*.55,p.get('length',.5),p.get('z_top',.98),.03,mat,coll); obj.rotation_euler[2]=math.pi; obj.location.y=.48
    elif piece.shape=='puff_sleeve': obj=_puff_sleeve(name,p.get('side','left'),p.get('radius',.18),p.get('length',.24),p.get('puffs',10),mat,coll)
    elif piece.shape=='hem_ruffle_ring': obj=_hem_ruffle(name,p.get('radius',1.0),p.get('z',.18),p.get('height',.08),p.get('waves',48),mat,coll)
    elif piece.shape=='stocking_leg': obj=_stocking_leg(name,p.get('side','left'),p.get('z_top',.55),p.get('z_bot',.05),p.get('radius',.08),mat,coll)
    elif piece.shape=='high_boot': obj=_high_boot(name,p.get('side','left'),p.get('z_top',.35),p.get('z_bot',.0),p.get('radius_shaft',.085),p.get('radius_foot',.075),mat,coll)
    elif piece.shape=='glove_forearm': obj=_glove_forearm(name,p.get('side','left'),p.get('z_top',1.55),p.get('z_bot',1.45),p.get('radius',.06),mat,coll)
    elif piece.shape=='choker_band': obj=_choker_band(name,p.get('z',1.45),p.get('radius',.07),p.get('height',.025),mat,coll)
    elif piece.shape=='sash_band': obj=_sash_band(name,p.get('z_top',1.13),p.get('z_bot',1.03),p.get('radius_x',.27),p.get('radius_y',.19),mat,coll)
    elif piece.shape=='bow_3d': obj=_bow_3d(name,p.get('z',1.12),p.get('width',.32),p.get('height',.22),p.get('depth',.08),mat,coll)
    elif piece.shape=='drape_side_asym': obj=_drape_side_asym(name,p.get('side','right'),p.get('z_top',1.08),p.get('z_bot',.70),p.get('width_top',.18),p.get('width_bot',.35),mat,coll)
    elif piece.shape=='tiered_lace_skirt': obj=_tiered_lace_skirt(name,p.get('waist_radius',.30),p.get('hem_radius',.95),p.get('z_top',1.05),p.get('z_bot',.35),p.get('tiers',3),mat,coll)
    elif piece.shape=='bloomer_shorts': obj=_bloomer_shorts(name,p.get('z_top',.85),p.get('z_bot',.55),p.get('waist_radius',.18),p.get('leg_radius',.085),p.get('ruffle_h',.025),mat,coll)
    else: obj=_front_panel(name,.25,.45,.5,.95,.03,mat,coll)
    return _mods(obj, piece, arm)

def _accessory(a, mats, coll):
    mat=mats.get(a.material); p=a.params or {}; name='PA_'+a.id
    if a.shape=='torus_belt':
        bpy.ops.mesh.primitive_torus_add(major_radius=p.get('radius_x',.34), minor_radius=.012, location=(0,0,p.get('z',.94)))
        o=bpy.context.object; o.name=name; o.scale.y=p.get('radius_y',.24)/max(p.get('radius_x',.34),.001); o.data.materials.append(mat); _link(o,coll); return [o]
    if a.shape=='pocket_watch':
        x=-0.42 if p.get('side','left')=='left' else .42; bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=p.get('radius',.07), location=(x,-.52,p.get('z',.78)))
        o=bpy.context.object; o.name=name; o.data.materials.append(mat); _link(o,coll); return [o]
    if a.shape=='scattered_cards':
        arr=[]; count=p.get('count',12); rad=p.get('radius',.8)
        for i in range(count):
            ang=2*math.pi*i/count; o=_front_panel(f'{name}_{i:02d}',.055,.06,.09,.45+.25*((i%5)/5),0,mat,coll); o.location.x+=rad*math.cos(ang); o.location.y+=.72*rad*math.sin(ang); o.rotation_euler[2]=ang; arr.append(o)
        return arr
    if a.shape=='embroidery_curves':
        arr=[]; count=p.get('count',18)
        for i in range(count):
            ang=2*math.pi*i/count; pts=[((.78-.18*t)*math.cos(ang+.18*math.sin(t*math.pi)), .72*(.78-.18*t)*math.sin(ang+.18*math.sin(t*math.pi)), .25+.45*t) for t in [k/15 for k in range(16)]]
            arr.append(_curve(f'{name}_{i:02d}', pts, mat, .0035, coll))
        return arr
    if a.shape=='corset_lacing':
        w=p.get('width',.18); n=p.get('count',7); z0=p.get('z_min',1.04); z1=p.get('z_max',1.38); pts=[]
        for i in range(n):
            z=z0+(z1-z0)*i/(n-1); pts += [(-w/2,-.235,z),(w/2,-.235,z+(z1-z0)/(n*2))]
        return [_curve(name, pts, mat, .005, coll)]
    if a.shape=='rose_brooches':
        arr=[]; count=p.get('count',6)
        for i in range(count):
            ang=2*math.pi*i/count; bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=.025, location=(.72*math.cos(ang),.52*math.sin(ang),.45+.18*(i%3)))
            o=bpy.context.object; o.name=f'{name}_{i:02d}'; o.data.materials.append(mat); _link(o,coll); arr.append(o)
        return arr
    if a.shape=='mini_top_hat':
        objs=[]
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=p.get('radius_crown',.07), depth=p.get('height_crown',.10), location=(p.get('off_x',.04),-.02,p.get('z',1.84)))
        crown=bpy.context.object; crown.name=name+'_crown'; crown.rotation_euler[1]=p.get('tilt',-.15)
        if mat: crown.data.materials.append(mat)
        _link(crown,coll); objs.append(crown)
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=p.get('radius_brim',.11), depth=.008, location=(p.get('off_x',.04),-.02,p.get('z',1.84)-p.get('height_crown',.10)*.5))
        brim=bpy.context.object; brim.name=name+'_brim'; brim.rotation_euler[1]=p.get('tilt',-.15)
        if mat: brim.data.materials.append(mat)
        _link(brim,coll); objs.append(brim)
        return objs
    if a.shape=='pendant_sphere':
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=p.get('radius',.025), location=(p.get('x',0), p.get('y',-.10), p.get('z',1.46)))
        o=bpy.context.object; o.name=name
        if mat: o.data.materials.append(mat)
        _link(o,coll); return [o]
    if a.shape=='pendant_key':
        objs=[]
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=p.get('bow_r',.015), depth=p.get('shaft',.06), location=(p.get('x',0), p.get('y',-.12), p.get('z',1.42)))
        shaft=bpy.context.object; shaft.name=name+'_shaft'; shaft.rotation_euler[0]=math.radians(90)
        if mat: shaft.data.materials.append(mat)
        _link(shaft,coll); objs.append(shaft)
        bpy.ops.mesh.primitive_torus_add(major_radius=p.get('bow_r',.018), minor_radius=.004, location=(p.get('x',0), p.get('y',-.12), p.get('z',1.42)+p.get('shaft',.06)*.5))
        bow=bpy.context.object; bow.name=name+'_bow'
        if mat: bow.data.materials.append(mat)
        _link(bow,coll); objs.append(bow)
        return objs
    if a.shape=='pendant_cards_charm':
        arr=[]; count=p.get('count',3)
        for i in range(count):
            o=_front_panel(f'{name}_{i:02d}',.025,.028,.04, p.get('z',1.20)+i*.015, 0.005, mat, coll)
            o.location.x=p.get('x',0)+(i-1)*.018; o.location.y=p.get('y',-.32)
            arr.append(o)
        return arr
    if a.shape=='lace_cross_corset':
        w=p.get('width',.20); n=p.get('count',8); z0=p.get('z_min',1.13); z1=p.get('z_max',1.32); pts=[]
        for i in range(n):
            z=z0+(z1-z0)*i/(n-1)
            pts += [(-w/2,-.235,z),(w/2,-.235,z+(z1-z0)/(n*2))]
        return [_curve(name, pts, mat, .004, coll)]
    return []

def build_garment_from_blueprint(bp, character_name='Alice_Base', collection_name='PA_Alice_Garment'):
    _require_bpy()
    from garment_schema import validate_blueprint
    report = validate_blueprint(bp)
    if not report['ok']: raise ValueError(report)
    coll=_coll(collection_name); mats=_create_materials(bp); arm=_find_armature(character_name); objs=[]
    for piece in sorted(bp.pieces, key=lambda p:p.layer): objs.append(_build_piece(piece,mats,coll,arm))
    for acc in sorted(bp.accessories, key=lambda a:a.layer): objs.extend(_accessory(acc,mats,coll))
    for o in objs:
        try: o['project_alice_garment']=bp.outfit_id
        except Exception: pass
    return json.dumps({'status':'success','outfit':bp.outfit_id,'objects':len(objs),'armature': arm.name if arm else None}, ensure_ascii=False)

def build_alice_dark_dress(character_name='Alice_Base'):
    import garment_alice_dark_dress
    return build_garment_from_blueprint(garment_alice_dark_dress.build_blueprint(), character_name)

def build_single_piece(bp, piece_id, character_name='Alice_Base', collection_name=None):
    """Constroi UMA peca apenas (piece-by-piece workflow).
    bp: OutfitBlueprint (mantem mats + lookup acessorio se piece_id for acessorio).
    """
    _require_bpy()
    coll_name = collection_name or f'PA_{bp.outfit_id}'
    coll=_coll(coll_name); mats=_create_materials(bp); arm=_find_armature(character_name); objs=[]
    p_match = next((p for p in bp.pieces if p.id == piece_id), None)
    a_match = next((a for a in bp.accessories if a.id == piece_id), None)
    if p_match is not None:
        objs.append(_build_piece(p_match, mats, coll, arm))
        kind='piece'
    elif a_match is not None:
        objs.extend(_accessory(a_match, mats, coll))
        kind='accessory'
    else:
        return json.dumps({'status':'error','msg':f'piece_id {piece_id} not in blueprint'})
    for o in objs:
        try: o['project_alice_garment']=bp.outfit_id; o['piece_id']=piece_id
        except Exception: pass
    return json.dumps({'status':'success','outfit':bp.outfit_id,'piece_id':piece_id,'kind':kind,
                       'objects':[o.name for o in objs if o is not None],'armature':arm.name if arm else None}, ensure_ascii=False)

def list_pieces_in_order(bp):
    """Retorna lista ordenada de (kind, id, layer, shape) para iterar peca-a-peca."""
    rows=[]
    for p in sorted(bp.pieces, key=lambda x:x.layer):
        rows.append(('piece', p.id, p.layer, p.shape))
    for a in sorted(bp.accessories, key=lambda x:x.layer):
        rows.append(('accessory', a.id, a.layer, a.shape))
    return rows

def remove_piece(piece_id, collection_name=None):
    """Remove objetos PA_<piece_id>* (rollback de uma peca antes de reconstruir)."""
    _require_bpy()
    pref=f'PA_{piece_id}'
    rm=[]
    for o in list(bpy.data.objects):
        if o.name.startswith(pref):
            rm.append(o.name); bpy.data.objects.remove(o, do_unlink=True)
    return json.dumps({'removed':rm})
