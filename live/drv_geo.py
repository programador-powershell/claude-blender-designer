import sys, importlib
sys.path.insert(0, r'D:\Alice\tools\auto-rig-fix\live')
import interior; importlib.reload(interior)
print(interior.build_geometry())
print(interior.build_cameras())
print(interior.look('Cam_Estab', rendered=False))
