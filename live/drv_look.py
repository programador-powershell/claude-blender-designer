import sys, importlib
sys.path.insert(0, r'D:\Alice\tools\auto-rig-fix\live')
import interior; importlib.reload(interior)
CAM = open(r'D:\Alice\tools\auto-rig-fix\work\.cam').read().strip()
rv = open(r'D:\Alice\tools\auto-rig-fix\work\.rend').read().strip()
REND = 'clay' if rv == 'clay' else (rv == '1')
try:
    fr = int(open(r'D:\Alice\tools\auto-rig-fix\work\.frame').read().strip())
    bpy.context.scene.frame_set(fr)
except Exception:
    pass
print(interior.look(CAM, rendered=REND))
