"""Extrai roupa do fundido via script do diretor (deleta pele perto do corpo base)."""
import bpy, sys, json
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, game_builder; importlib.reload(game_builder)
from mathutils import Vector

THR=0.018
try: THR=float(open(r"D:/Alice/tools/auto-rig-fix/work/thr.txt").read().strip())
except Exception: pass

game_builder.reset_world()
game_builder.load_glb(r"D:/Project Alice 2/Dependencies/hunyuan3d_env/Hunyuan3D-2/out/cheshire_full.glb","Hunyuan3D_Cheshire_Mesh")
game_builder.prep_base_body_posed(arm_deg=70, name="Alice_Base_Body")
ref=bpy.data.objects["Hunyuan3D_Cheshire_Mesh"]; base=bpy.data.objects["Alice_Base_Body"]

# alinha base ao ref (escala/centro/pes) p/ proximidade funcionar
def bb(o):
    c=[o.matrix_world@v.co for v in o.data.vertices]
    xs=[p.x for p in c];ys=[p.y for p in c];zs=[p.z for p in c]
    return Vector(((min(xs)+max(xs))/2,(min(ys)+max(ys))/2,min(zs))), max(zs)-min(zs)
rc,rh=bb(ref); bc,bh=bb(base); f=rh/bh
base.scale=(f,f,f); bpy.context.view_layer.update()
bc,bh=bb(base); base.location+=(rc-bc); bpy.context.view_layer.update()

print("EXTRACT:", game_builder.extract_and_fit_clothing("Alice_Base_Body","Hunyuan3D_Cheshire_Mesh", THR))

# esconde corpo + ref, mostra so a roupa isolada
cloth=next((o for o in bpy.data.objects if o.name.startswith("Vestido_")), None)
ref.hide_set(True); base.hide_set(True)
if cloth:
    bpy.context.view_layer.objects.active=cloth
    for a in bpy.context.screen.areas:
        if a.type=='VIEW_3D':
            a.spaces[0].shading.type='SOLID'
            r=next((x for x in a.regions if x.type=='WINDOW'),None)
            with bpy.context.temp_override(area=a,region=r):
                bpy.ops.object.select_all(action='DESELECT'); cloth.select_set(True)
                bpy.ops.view3d.view_axis(type='FRONT'); bpy.ops.view3d.view_selected()
            break
print("OK extract", THR)
