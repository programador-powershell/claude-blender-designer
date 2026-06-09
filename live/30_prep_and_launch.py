"""Prep outfit + lanca SHD (nao-bloqueante). Le work/outfit.txt: name|fbx|arm_deg."""
import bpy, sys
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, game_builder; importlib.reload(game_builder)
parts=open(r"D:/Alice/tools/auto-rig-fix/work/outfit.txt").read().strip().split("|")
name=parts[0]; fbx=parts[1]; deg=float(parts[2])
print("PREP:", game_builder.prep_outfit(fbx, name, arm_deg=deg))
print("LAUNCH:", game_builder.shd_launch(name, f"Rig_{name}", resolution=110, influence=4))
print("OK prep_and_launch", name)
