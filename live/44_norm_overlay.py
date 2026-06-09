"""Normaliza NUA + CHES igual (apply+orient+escala1.7+centra) e overlay p/ ver se
compartilham o corpo (nua cabe dentro do vestido?)."""
import bpy, sys, math
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, game_builder; importlib.reload(game_builder)
from mathutils import Vector
game_builder.reset_world()

def imp_norm(path, name):
    before=set(bpy.data.objects); bpy.ops.import_scene.fbx(filepath=path)
    new=[o for o in bpy.data.objects if o not in before]
    m=max([o for o in new if o.type=='MESH'], key=lambda o:len(o.data.vertices)); m.name=name
    bpy.ops.object.select_all(action='DESELECT'); m.select_set(True); bpy.context.view_layer.objects.active=m
    if m.parent: bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    for o in new:
        if o is not m:
            try: bpy.data.objects.remove(o,do_unlink=True)
            except: pass
    bpy.ops.object.select_all(action='DESELECT'); m.select_set(True); bpy.context.view_layer.objects.active=m
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    # orienta: maior eixo -> Z
    co=[v.co for v in m.data.vertices]
    xs=[c.x for c in co];ys=[c.y for c in co];zs=[c.z for c in co]
    dx=max(xs)-min(xs);dy=max(ys)-min(ys);dz=max(zs)-min(zs)
    mx=max(dx,dy,dz)
    if mx==dy: m.rotation_euler=(math.radians(90),0,0)
    elif mx==dx: m.rotation_euler=(0,math.radians(90),0)
    bpy.ops.object.transform_apply(rotation=True)
    # escala p/ 1.7 + centra xy + pes z=0
    co=[m.matrix_world@v.co for v in m.data.vertices]
    zs=[c.z for c in co]; h=max(zs)-min(zs)
    if h>1e-6: m.scale=(1.7/h,)*3; bpy.ops.object.transform_apply(scale=True)
    co=[m.matrix_world@v.co for v in m.data.vertices]
    xs=[c.x for c in co];ys=[c.y for c in co];zs=[c.z for c in co]
    m.location=(m.location.x-(min(xs)+max(xs))/2, m.location.y-(min(ys)+max(ys))/2, m.location.z-min(zs))
    bpy.ops.object.transform_apply(location=True)
    return m
nua=imp_norm(r"E:\References\3D\SK_Alice.fbx","NUA")
ches=imp_norm(r"E:\References\3D\SK_Alice_Cheshire.fbx","CHES")
def bb(o):
    c=[o.matrix_world@v.co for v in o.data.vertices]
    xs=[p.x for p in c];zs=[p.z for p in c]
    return (round(min(xs),2),round(max(xs),2)),(round(min(zs),2),round(max(zs),2))
print("NUA X,Z:", bb(nua), "verts", len(nua.data.vertices))
print("CHES X,Z:", bb(ches), "verts", len(ches.data.vertices))
ches.display_type='WIRE'
bpy.context.view_layer.objects.active=nua
for a in bpy.context.screen.areas:
    if a.type=='VIEW_3D':
        a.spaces[0].shading.type='SOLID'
        r=next((x for x in a.regions if x.type=='WINDOW'),None)
        with bpy.context.temp_override(area=a,region=r):
            bpy.ops.object.select_all(action='DESELECT'); nua.select_set(True); ches.select_set(True)
            bpy.ops.view3d.view_axis(type='FRONT'); bpy.ops.view3d.view_selected()
        break
print("OK norm_overlay")
