"""Executor de comando-diretor. Le work/cmd.txt (JSON):
  {"load":"<glb>","name":"rainha","ops":[["raise_arm",{...}], ...],"frame":"FRONT"}
Robusto: load_glb reseta mundo. ops chamam funcoes do game_builder por nome."""
import bpy, sys, json
sys.path.insert(0, r"D:\Alice\tools\auto-rig-fix\live")
import importlib, game_builder; importlib.reload(game_builder)
import live_geo; importlib.reload(live_geo)

cfg=json.load(open(r"D:/Alice/tools/auto-rig-fix/work/cmd.txt", encoding="utf-8"))
name=cfg.get("name","char")
if cfg.get("load"):
    print("LOAD:", game_builder.load_glb(cfg["load"], name))
elif cfg.get("load_fbx"):
    print("LOADFBX:", game_builder.load_fbx_outfit(cfg["load_fbx"], name))
for op in cfg.get("ops", []):
    fn=op[0]; kw=op[1] if len(op)>1 else {}
    print(f"OP {fn}:", getattr(game_builder, fn)(**kw))
game_builder.frame(target=cfg.get("frame_target", name), axis=cfg.get("frame","FRONT"))
print("OK cmd")
