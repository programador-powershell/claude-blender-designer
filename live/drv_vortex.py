import sys, importlib
sys.path.insert(0, r'D:\Alice\tools\auto-rig-fix\live')
import interior, vortex
importlib.reload(interior); importlib.reload(vortex)
print(vortex.build_all())
