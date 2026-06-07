# -*- coding: utf-8 -*-
import json, os, math
try: import bpy
except Exception: bpy=None

def _require():
    if bpy is None: raise RuntimeError('Rodar dentro do Blender')

def _cam(name, loc, rot):
    cam_data=bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    cam=bpy.data.objects.get(name) or bpy.data.objects.new(name, cam_data)
    if not cam.users_collection: bpy.context.scene.collection.objects.link(cam)
    cam.location=loc; cam.rotation_euler=rot; cam.data.type='ORTHO'; cam.data.ortho_scale=2.15
    return cam

def setup_turnaround_cameras():
    _require(); cams=[]
    cams.append(_cam('PA_VALIDATE_FRONT',(0,-4,1.05),(math.radians(78),0,0)))
    cams.append(_cam('PA_VALIDATE_SIDE',(4,0,1.05),(math.radians(78),0,math.radians(90))))
    cams.append(_cam('PA_VALIDATE_BACK',(0,4,1.05),(math.radians(78),0,math.radians(180))))
    return json.dumps({'cameras':[c.name for c in cams]})

def render_validation_set(out_dir='D:/Alice/tools/auto-rig-fix/work/garment_validation'):
    _require(); os.makedirs(out_dir, exist_ok=True); setup_turnaround_cameras()
    scene=bpy.context.scene; scene.render.resolution_x=1200; scene.render.resolution_y=1600; files=[]
    for name in ['PA_VALIDATE_FRONT','PA_VALIDATE_SIDE','PA_VALIDATE_BACK']:
        scene.camera=bpy.data.objects[name]; path=os.path.join(out_dir, name+'.png'); scene.render.filepath=path; bpy.ops.render.render(write_still=True); files.append(path)
    return json.dumps({'renders':files}, ensure_ascii=False)
