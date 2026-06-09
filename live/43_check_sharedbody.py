"""Carrega SK_Alice (nua) + SK_Alice_Cheshire (vestido) RAW (mesmo source -> sobrepoem).
Overlay: corpo nu solido + vestido wire. Se corpo nu cabe dentro -> compartilham base."""
import bpy, sys
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, game_builder; importlib.reload(game_builder)
game_builder.reset_world()

def imp(path, name):
    before=set(bpy.data.objects); bpy.ops.import_scene.fbx(filepath=path)
    new=[o for o in bpy.data.objects if o not in before]
    m=max([o for o in new if o.type=='MESH'], key=lambda o:len(o.data.vertices)); m.name=name
    for o in new:
        if o is not m:
            try: bpy.data.objects.remove(o,do_unlink=True)
            except: pass
    return m
nua=imp(r"E:\References\3D\SK_Alice.fbx","NUA")
ches=imp(r"E:\References\3D\SK_Alice_Cheshire.fbx","CHES")
def bb(o):
    c=[o.matrix_world@v.co for v in o.data.vertices]
    xs=[p.x for p in c];ys=[p.y for p in c];zs=[p.z for p in c]
    return (round(min(xs),3),round(max(xs),3)),(round(min(zs),3),round(max(zs),3))
print("NUA  X,Z:", bb(nua))
print("CHES X,Z:", bb(ches))
# overlay: nua solida, ches wire
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
print("OK shared")
