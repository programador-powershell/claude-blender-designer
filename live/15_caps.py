"""Checa capacidades: SHD addon, shd.exe, cell_fracture, rigidbody."""
import bpy, addon_utils, os
print("=== ADDONS ===")
for mod in addon_utils.modules():
    n = mod.__name__
    if any(k in n.lower() for k in ("heat","fracture","cell","rigid")):
        enabled = addon_utils.check(n)[1]
        print(f"  {n}: enabled={enabled}")
print("=== OPS ===")
print("  cell_fracture:", hasattr(bpy.ops.object, "cell_fracture"))
try:
    print("  cell_fracture poll:", bpy.ops.object.cell_fracture.poll())
except Exception as e:
    print("  cell_fracture poll err:", e)
print("  rigidbody.world_add:", hasattr(bpy.ops.rigidbody, "world_add"))
# SHD exe
shd_dir = r"C:\Users\pslo9\AppData\Roaming\Blender Foundation\Blender\5.1\scripts\addons\surface_heat_diffuse_skinning"
print("=== SHD ===")
print("  dir existe:", os.path.isdir(shd_dir))
if os.path.isdir(shd_dir):
    for f in os.listdir(shd_dir):
        if f.endswith(".exe") or f.endswith(".py"): print("   ", f)
# modulos SHD importaveis?
try:
    import surface_heat_diffuse_skinning as S
    print("  import SHD ok:", [a for a in dir(S) if "OT_" in a or "Operator" in a][:5])
except Exception as e:
    print("  import SHD err:", e)
print("OK caps")
