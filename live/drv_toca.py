import sys, importlib
sys.path.insert(0, r'D:\Alice\tools\auto-rig-fix\live')
import interior, toca
importlib.reload(interior); importlib.reload(toca)
print(toca.build_all())
