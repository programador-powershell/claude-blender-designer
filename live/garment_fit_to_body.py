# -*- coding: utf-8 -*-
import json
try: import bpy
except Exception: bpy=None

def _require():
    if bpy is None: raise RuntimeError('Rodar dentro do Blender')

def add_collision_to_body(character_name='Alice_Base', thickness_outer=0.015):
    _require(); targets=[o for o in bpy.data.objects if o.type=='MESH' and character_name.lower() in o.name.lower()]
    if not targets: targets=[o for o in bpy.data.objects if o.type=='MESH']
    changed=[]
    for o in targets:
        if not any(m.type=='COLLISION' for m in o.modifiers):
            mod=o.modifiers.new('PA_body_collision','COLLISION')
            try: mod.settings.thickness_outer=thickness_outer
            except Exception: pass
        changed.append(o.name)
    return json.dumps({'collision_added':changed})

def pin_top_vertices(obj_name, z_threshold=0.90, group_name='PA_PIN_TOP'):
    _require(); obj=bpy.data.objects.get(obj_name)
    if not obj or obj.type!='MESH': return json.dumps({'err':'mesh not found'})
    vg=obj.vertex_groups.get(group_name) or obj.vertex_groups.new(name=group_name); idx=[]
    for v in obj.data.vertices:
        if (obj.matrix_world @ v.co).z >= z_threshold: idx.append(v.index)
    if idx: vg.add(idx,1.0,'REPLACE')
    for m in obj.modifiers:
        if m.type=='CLOTH':
            try: m.settings.vertex_group_mass=group_name
            except Exception: pass
    return json.dumps({'object':obj_name,'pinned':len(idx),'group':group_name})

def pin_all_garment_tops(prefix='PA_', z_threshold=0.90):
    _require(); out=[]
    for o in bpy.data.objects:
        if o.type=='MESH' and o.name.startswith(prefix):
            out.append(json.loads(pin_top_vertices(o.name,z_threshold)))
    return json.dumps(out)
