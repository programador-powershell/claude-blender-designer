# blender --background --python test_vision_chain.py
import bpy, sys, importlib, json, math
from mathutils import Vector
sys.path.insert(0, r'D:\Alice\tools\auto-rig-fix\live')
import game_builder as G; importlib.reload(G)

print(G.load_glb(r'E:\References\3D\alice-chapepeiro.glb', 'Dress'))
r = json.loads(G.curves_from_trace(r'D:\Alice\tools\dress\skirt.json', 'Dress', front_offset=0.015))
print('GUIDES', r.get('count'), r.get('guides'))
ruf = 0
for g in r.get('guides', []):
    res = json.loads(G.generate_procedural_ruffles(g, ruffle_width=0.035, frequency=22, amplitude=0.013))
    if res.get('status') == 'success': ruf += 1
    # esconde a curva-guia do render
    go = bpy.data.objects.get(g)
    if go: go.hide_render = True; go.hide_set(True)
print('RUFFLES_OK', ruf)

# render front workbench
sc = bpy.context.scene; sc.render.engine = 'BLENDER_WORKBENCH'
sc.render.resolution_x = 480; sc.render.resolution_y = 680
sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'SINGLE'; sh.single_color=(0.72,0.72,0.74)
sh.show_cavity = True; sh.cavity_type = 'BOTH'
for o in bpy.data.objects:
    if o.type == 'ARMATURE': o.hide_render = True
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render]
xs=[];ys=[];zs=[]
for o in meshes:
    for c in o.bound_box:
        w=o.matrix_world@Vector(c); xs.append(w.x);ys.append(w.y);zs.append(w.z)
ctr=Vector(((min(xs)+max(xs))/2,(min(ys)+max(ys))/2,(min(zs)+max(zs))/2))
szz=max(max(xs)-min(xs),max(zs)-min(zs)) or 1
bpy.ops.object.camera_add(); cam=bpy.context.active_object; cam.data.type='ORTHO'; cam.data.ortho_scale=szz*1.15
cam.location=ctr+Vector((0,-szz*3,0)); d=ctr-cam.location; cam.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
sc.camera=cam; sc.render.filepath=r'D:\Alice\tools\dress\chain_ruffled.png'; bpy.ops.render.render(write_still=True)
print('CHAIN_DONE')
