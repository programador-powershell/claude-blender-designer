# -*- coding: utf-8 -*-
"""Punch-list per-parte da Alice nua vs BASE/alice.jpg. Render por LoopCam (offscreen),
overlay registrado, gemma pontua. Roda no python do ComfyUI."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import trace_overlay as TO, vision_ask as VA
from bridge_cmd import send
from PIL import Image
REF = r'D:/References/img/Model 3D/BASE/alice.jpg'
WK = r'D:/Alice/tools/auto-rig-fix/work/loop'
os.makedirs(WK, exist_ok=True)
H = 1.701
REGIONS = {'cabeca': (1.55, 0.34), 'tronco': (1.22, 0.44), 'quadril': (0.92, 0.32), 'pernas': (0.45, 0.60)}

def render_region(zc, zspan, out):
    OS = zspan * 1.25
    code = f"""
import bpy, mathutils
sc=bpy.context.scene; sc.render.resolution_x=700; sc.render.resolution_y=700; sc.render.image_settings.file_format='PNG'
cam=bpy.data.objects['LoopCam']; cam.data.ortho_scale={OS}
q=mathutils.Quaternion((0.70710678,0.70710678,0,0)); cam.rotation_mode='QUATERNION'; cam.rotation_quaternion=q
cam.location=mathutils.Vector((0,0,{zc}))+(q@mathutils.Vector((0,0,4.0))); sc.camera=cam
for o in bpy.data.objects:
    if o.name.startswith('REF'): o.hide_render=True
sc.render.filepath=r"{out}"
bpy.ops.render.render(write_still=True)
print('r')
"""
    return send({"code": code, "shot": False})

def crop_art(zc, zspan, out):
    im = Image.open(REF).convert('RGB'); W, Hh = im.size
    f0 = (zc - zspan/2)/H; f1 = (zc + zspan/2)/H
    y0 = int((1-f1)*Hh); y1 = int((1-f0)*Hh)
    im.crop((0, max(0,y0), W, min(Hh,y1))).save(out)

P = ('[1]=concept art region, [2]=overlay (RED=art lines, GREEN=model lines) on grid. '
     'Reply ONLY JSON {"fidelity_0to100":int,"top_issue":str}')
for name, (zc, zspan) in REGIONS.items():
    cur = f"{WK}/alice_{name}_cur.png"; ref = f"{WK}/alice_{name}_ref.png"; ovl = f"{WK}/alice_{name}_ovl.png"
    render_region(zc, zspan, cur); crop_art(zc, zspan, ref)
    cov = TO.make_overlay(ref, cur, ovl, grid=10)
    ans = VA.ask_multi([ref, ovl], P, num_predict=300).replace("\n", " ")
    print(f"{name:8} cov={cov}%  {ans[:220]}")
