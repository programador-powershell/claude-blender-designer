"""Render 3 vistas (front/34/side) de um GLB/blend num frame estavel.
BLINDADO: camera sempre enquadra (bbox so de meshes reais, ignora
icosphere/cube junk, fallback se bbox degenerado). Saida: <prefix>_{front,34,side}.png

Uso: blender -b <rig.blend> -P render_views.py -- <prefix> [frame=1]
  OU blender -b -P render_views.py -- <prefix> [frame] glb=<file.glb>
"""
import sys, os, math
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
prefix = os.path.abspath(argv[0])
frame = 1
glb = None
for a in argv[1:]:
    if a.startswith("glb="): glb=os.path.abspath(a[4:])
    else:
        try: frame=int(a)
        except: pass

if glb:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)

# anim: aplica primeira action se houver
arm=next((o for o in bpy.data.objects if o.type=="ARMATURE"),None)
if arm and bpy.data.actions:
    if not arm.animation_data: arm.animation_data_create()
    arm.animation_data.action=bpy.data.actions[0]

sc=bpy.context.scene
try: sc.frame_set(frame)
except: pass

# bbox SO de meshes reais (>320 polys; ignora icosphere/cube junk)
real=[o for o in bpy.data.objects if o.type=="MESH" and len(o.data.polygons)>320]
if not real:
    real=[o for o in bpy.data.objects if o.type=="MESH"]

dg=bpy.context.evaluated_depsgraph_get()
xs=[];ys=[];zs=[]
for o in real:
    ev=o.evaluated_get(dg); me=ev.to_mesh(); mw=o.matrix_world
    for v in me.vertices:
        w=mw@v.co; xs.append(w.x);ys.append(w.y);zs.append(w.z)
    ev.to_mesh_clear()

# fallback se bbox degenerado
if not xs or (max(xs)-min(xs))<0.01:
    cx,cy,cz,hgt = 0,0,1,2
else:
    cx,cy,cz=(min(xs)+max(xs))/2,(min(ys)+max(ys))/2,(min(zs)+max(zs))/2
    hgt=max(max(zs)-min(zs), max(xs)-min(xs), 1.0)
d=hgt*1.5

def shot(loc, path):
    for o in [x for x in bpy.data.objects if x.type in ("CAMERA","LIGHT")]:
        bpy.data.objects.remove(o,do_unlink=True)
    cam=bpy.data.objects.new("C",bpy.data.cameras.new("C")); sc.collection.objects.link(cam)
    cam.data.lens=50
    cam.location=loc
    cam.rotation_mode="QUATERNION"
    cam.rotation_quaternion=(Vector((cx,cy,cz))-Vector(loc)).to_track_quat("-Z","Y")
    sc.camera=cam
    # ortho-ish framing: ajusta lens p/ caber
    cam.data.angle=2*math.atan((hgt*0.62)/d)
    for ll in [(cx,cy-d,cz+hgt),(cx+d,cy,cz+hgt*0.5),(cx-d,cy,cz)]:
        l=bpy.data.objects.new("L",bpy.data.lights.new("L","SUN")); l.data.energy=2.5
        sc.collection.objects.link(l); l.location=ll
        l.rotation_mode="QUATERNION"; l.rotation_quaternion=(Vector((cx,cy,cz))-Vector(ll)).to_track_quat("-Z","Y")
    sc.render.engine="BLENDER_WORKBENCH"
    sc.display.shading.light="STUDIO"; sc.display.shading.color_type="SINGLE"
    sc.display.shading.single_color=(0.85,0.75,0.65); sc.display.shading.show_shadows=True
    sc.render.resolution_x=420; sc.render.resolution_y=620
    sc.render.film_transparent=False
    sc.render.filepath=path
    bpy.ops.render.render(write_still=True)

shot((cx, cy-d, cz),            prefix+"_front.png")
shot((cx+d*0.85, cy-d*0.6, cz), prefix+"_34.png")
shot((cx+d, cy, cz),            prefix+"_side.png")
print(f"[render_views] OK {prefix} frame={frame} bbox_h={hgt:.2f} meshes={len(real)}")
