"""Finaliza SHD + verifica cobertura por banda + exporta GLB. Le work/outfit.txt."""
import bpy, sys, os
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, game_builder; importlib.reload(game_builder)
import live_geo; importlib.reload(live_geo)

name="cheshire"
try:
    name=open(r"D:/Alice/tools/auto-rig-fix/work/outfit.txt").read().strip().split("|")[0]
except Exception: pass
arm_name=f"Rig_{name}"

print("FINALIZE:", game_builder.shd_finalize(name, arm_name))

# cobertura: % sem peso de osso (deve ~0)
d=bpy.data.objects.get(name); me=d.data
bone_idx={g.index for g in d.vertex_groups if g.name.startswith("mixamorig")}
unw=sum(1 for v in me.vertices if sum(g.weight for g in v.groups if g.group in bone_idx)<1e-4)
print(f"COVERAGE: {len(me.vertices)} verts, sem_peso={unw} ({100*unw/len(me.vertices):.1f}%)")

# export
out=rf"D:\Alice\tools\auto-rig-fix\work\rigged\{name}_rigged.glb"
os.makedirs(os.path.dirname(out), exist_ok=True)
print("EXPORT:", game_builder.export_rigged(name, out))

# esconde esqueleto, front view p/ eu validar
arm=bpy.data.objects.get(arm_name)
if arm: arm.hide_set(True)
live_geo.view_shot(name, "FRONT")
print("OK finalize", name)
