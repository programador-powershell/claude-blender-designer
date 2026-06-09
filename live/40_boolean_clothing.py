"""Boolean: vestido_solido - corpo_solido = roupa oca. Tecnica geometrica (sem cor).
Carrega corpo base, alinha dentro do mesh vestido (ja carregado como 'dress'), boolean diff."""
import bpy, sys
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, game_builder; importlib.reload(game_builder)
from mathutils import Vector

dress = bpy.data.objects.get("dress")   # mesh vestido Hunyuan (headless)
# importa corpo base, isola mesh
before=set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=r"D:\Alice\tools\body-rebuild\out\alice_body_clean.fbx")
new=[o for o in bpy.data.objects if o not in before]
body=max([o for o in new if o.type=='MESH'], key=lambda o:len(o.data.vertices)); body.name="basebody"
for o in new:
    if o is not body:
        try: bpy.data.objects.remove(o, do_unlink=True)
        except: pass
# clear parent keep transform + apply
bpy.ops.object.select_all(action='DESELECT'); body.select_set(True); bpy.context.view_layer.objects.active=body
if body.parent: bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)

def bb(o):
    c=[o.matrix_world@v.co for v in o.data.vertices]
    xs=[p.x for p in c];ys=[p.y for p in c];zs=[p.z for p in c]
    return Vector(((min(xs)+max(xs))/2,(min(ys)+max(ys))/2,min(zs))), max(zs)-min(zs)
# alinha corpo ao vestido: feet+center, escala por altura
dc,dh=bb(dress); bc,bh=bb(body)
f=dh/bh if bh>1e-6 else 1
body.scale=(f,f,f); bpy.context.view_layer.update()
bc,bh=bb(body)
body.location += (dc-bc); bpy.context.view_layer.update()
print("aligned body to dress. dressH",round(dh,3),"bodyH now",round(bb(body)[1],3))
print("OK align (proximo: boolean)")
