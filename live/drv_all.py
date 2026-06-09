import sys, importlib
sys.path.insert(0, r'D:\Alice\tools\auto-rig-fix\live')
import interior; importlib.reload(interior)
print(interior.build_geometry())
print(interior.build_dressing())
print(interior.build_lights_cams())
print(interior.apply_textures())
