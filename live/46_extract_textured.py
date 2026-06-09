"""Extrai roupa do GLB TEXTURIZADO (mantem cor/UV) usando base nua. Render colorido."""
import bpy, sys, math
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, game_builder; importlib.reload(game_builder)
game_builder.reset_world()
THR=0.03
try: THR=float(open(r"D:/Alice/tools/auto-rig-fix/work/thr.txt").read().strip())
except: pass

def imp_norm(path, name, glb=False):
    before=set(bpy.data.objects)
    if glb: bpy.ops.import_scene.gltf(filepath=path)
    else: bpy.ops.import_scene.fbx(filepath=path)
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
    co=[v.co for v in m.data.vertices]; xs=[c.x for c in co];ys=[c.y for c in co];zs=[c.z for c in co]
    dx,dy,dz=max(xs)-min(xs),max(ys)-min(ys),max(zs)-min(zs); mx=max(dx,dy,dz)
    if mx==dy: m.rotation_euler=(math.radians(90),0,0)
    elif mx==dx: m.rotation_euler=(0,math.radians(90),0)
    bpy.ops.object.transform_apply(rotation=True)
    co=[m.matrix_world@v.co for v in m.data.vertices]; zs=[c.z for c in co]; h=max(zs)-min(zs)
    if h>1e-6: m.scale=(1.7/h,)*3; bpy.ops.object.transform_apply(scale=True)
    co=[m.matrix_world@v.co for v in m.data.vertices]; xs=[c.x for c in co];ys=[c.y for c in co];zs=[c.z for c in co]
    m.location=(m.location.x-(min(xs)+max(xs))/2, m.location.y-(min(ys)+max(ys))/2, m.location.z-min(zs))
    bpy.ops.object.transform_apply(location=True)
    return m
print("loading textured GLB (1M verts, pesado)...")
imp_norm(r"E:\References\3D\alice-cheshire.glb","Hunyuan3D_Cheshire", glb=True)
imp_norm(r"E:\References\3D\SK_Alice.fbx","Alice_Base_Body")
game_builder.pose_nude_arms("Alice_Base_Body", deg=70)
print("EXTRACT:", game_builder.extract_and_fit_clothing("Alice_Base_Body","Hunyuan3D_Cheshire", THR, do_datatransfer=False))
cloth=next((o for o in bpy.data.objects if o.name.startswith("Vestido_")), None)
print("CLEAN:", game_builder.clean_small_islands(cloth.name, min_verts=12))
# render COLORIDO
for o in bpy.data.objects:
    if o is not cloth and o.type=='MESH': o.hide_set(True)
bpy.context.view_layer.objects.active=cloth
for a in bpy.context.screen.areas:
    if a.type=='VIEW_3D':
        a.spaces[0].shading.type='SOLID'; a.spaces[0].shading.color_type='TEXTURE'
        r=next((x for x in a.regions if x.type=='WINDOW'),None)
        with bpy.context.temp_override(area=a,region=r):
            bpy.ops.object.select_all(action='DESELECT'); cloth.select_set(True)
            bpy.ops.view3d.view_axis(type='FRONT'); bpy.ops.view3d.view_selected()
        break
print("OK textured")
