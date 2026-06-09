"""Fluxo profissional do diretor:
1. carrega Hunyuan3D_Reference_Model (fundido) + Alice_Base_Body (corpo posado)
2. analisa por DADOS (stats) - sem screenshot
3. alinha base ao referencia (escala/centro/pes)
4. deformacao cirurgica: corpo do fundido casa com o base -> roupa segue."""
import bpy, sys, json
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, game_builder; importlib.reload(game_builder)
import live_geo; importlib.reload(live_geo)
from mathutils import Vector

game_builder.reset_world()
print("REF:", game_builder.load_glb(
    r"D:/Project Alice 2/Dependencies/hunyuan3d_env/Hunyuan3D-2/out/cheshire_full.glb",
    "Hunyuan3D_Reference_Model"))
print("BASE:", game_builder.prep_base_body_posed(arm_deg=70, name="Alice_Base_Body"))

ref=bpy.data.objects["Hunyuan3D_Reference_Model"]; base=bpy.data.objects["Alice_Base_Body"]
# 2. analise por dados
print("STATS_REF:", game_builder.get_mesh_stats("Hunyuan3D_Reference_Model"))
print("STATS_BASE:", game_builder.get_mesh_stats("Alice_Base_Body"))

# 3. alinha base ao ref (escala altura + centro xy + pes z)
def bb(o):
    c=[o.matrix_world@v.co for v in o.data.vertices]
    xs=[p.x for p in c];ys=[p.y for p in c];zs=[p.z for p in c]
    return Vector(((min(xs)+max(xs))/2,(min(ys)+max(ys))/2,min(zs))), max(zs)-min(zs)
rc,rh=bb(ref); bc,bh=bb(base)
f=rh/bh if bh>1e-6 else 1
base.scale=(f,f,f); bpy.context.view_layer.update()
bc,bh=bb(base); base.location += (rc-bc); bpy.context.view_layer.update()
print(f"ALIGN: refH={rh:.3f} baseH={bb(base)[1]:.3f}")

# 4. deformacao cirurgica
print("SURGICAL:", game_builder.surgical_align("Hunyuan3D_Reference_Model","Alice_Base_Body",
      body_thr=0.05, k=8, falloff=0.85))
print("OK director_flow")
