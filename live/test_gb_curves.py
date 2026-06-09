# blender --background --python test_gb_curves.py
import bpy, sys, math, importlib
sys.path.insert(0, r'D:\Alice\tools\auto-rig-fix\live')
import game_builder as G; importlib.reload(G)

for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)

# guia de saia/cabelo (arco vertical)
cu=bpy.data.curves.new('TG','CURVE'); cu.dimensions='3D'
sp=cu.splines.new('BEZIER'); sp.bezier_points.add(5)
for i,bp in enumerate(sp.bezier_points):
    t=i/5.0; bp.co=(math.sin(t*6)*0.3,0,-t); bp.handle_left_type='AUTO'; bp.handle_right_type='AUTO'
ob=bpy.data.objects.new('TestGuide',cu); bpy.context.scene.collection.objects.link(ob)

print('RUFFLE:', G.generate_procedural_ruffles('TestGuide'))
print('HAIR  :', G.generate_hair_strands_from_guides('TestGuide', density=6))

# armature p/ skirt rig
arm_d=bpy.data.armatures.new('A'); arm=bpy.data.objects.new('Rig',arm_d)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active=arm; bpy.ops.object.mode_set(mode='EDIT')
hb=arm_d.edit_bones.new('mixamorig:Hips'); hb.head=(0,0,0); hb.tail=(0,0,0.2)
bpy.ops.object.mode_set(mode='OBJECT')
print('SKIRT :', G.create_skirt_rig_assist('Rig', ['TestGuide'], bones_per_chain=3))

# anti-clip: corpo (cubo) + roupa (cubo maior)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(0,0,0)); body=bpy.context.active_object; body.name='Body'
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.52, location=(0,0,0)); cl=bpy.context.active_object; cl.name='Cloth'
print('MASK  :', G.apply_anti_clipping_mask('Body','Cloth', detection_threshold=0.1))
print('OBJS  :', [o.name for o in bpy.data.objects])
print('ALL_OK')
