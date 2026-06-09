"""TESTE LIVE GEO: levanta braco esquerdo da rainha por edicao de vertices.
Roda cada vert da cadeia do braco em torno do ombro (Y global), blend pela weight
do braco (ombro nao rasga). Usa apply_live_vertex_deformations. Le angulo de work/raise.txt."""
import bpy, math, sys
from mathutils import Matrix
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, game_builder; importlib.reload(game_builder)
import live_geo; importlib.reload(live_geo)

THETA=-100.0
try: THETA=float(open(r"D:/Alice/tools/auto-rig-fix/work/raise.txt").read().strip())
except Exception: pass

mesh=bpy.data.objects.get("rainha_geo")
arm=bpy.data.objects.get("MixamoArmature.001")
pivot=arm.matrix_world @ arm.data.bones["mixamorig:LeftArm"].head_local
# cadeia do braco (exclui Shoulder p/ pivotar limpo no ombro)
chain={g.index for g in mesh.vertex_groups
       if g.name.startswith("mixamorig:Left") and ("Arm" in g.name or "Hand" in g.name)
       and "Shoulder" not in g.name}
R=Matrix.Rotation(math.radians(THETA),4,'Y')
MW=mesh.matrix_world; MWi=MW.inverted()
updates=[]
for v in mesh.data.vertices:
    w=sum(g.weight for g in v.groups if g.group in chain)
    if w<0.01: continue
    w=min(1.0,w)
    wco=MW@v.co; rel=wco-pivot; rot=(R@rel)+pivot
    nw=wco.lerp(rot,w); nl=MWi@nw
    updates.append({"id":v.index,"co":[nl.x,nl.y,nl.z]})

# demonstra READ
print("READ sample:", game_builder.get_live_mesh_geometry("rainha_geo",sample_rate=80000,limit=2))
# WRITE
print("APPLY:", game_builder.apply_live_vertex_deformations("rainha_geo", updates))
print("theta=",THETA," arm_verts_moved=",len(updates))

arm.hide_set(True)
live_geo.view_shot("rainha_geo","FRONT")
print("OK geo_raise")
