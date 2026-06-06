# -*- coding: utf-8 -*-
"""
pipeline_hunyuan - Image(s) -> Hunyuan3D-2mv-turbo -> GLB -> Blender bridge.
Multi-view: front + left + back -> single textured GLB -> game_builder pipeline.
"""
import os, sys, subprocess, tempfile, json

HUNYUAN_REPO = r"D:/Project Alice 2/Dependencies/hunyuan3d_env/Hunyuan3D-2"
HUNYUAN_PY   = r"D:/Project Alice 2/Dependencies/hunyuan3d_env/python/python.exe"
HUNYUAN_MV_REPO     = "tencent/Hunyuan3D-2mv"
HUNYUAN_MV_SUBFOLDER= "hunyuan3d-dit-v2-mv"  # non-turbo full quality
HF_HOME             = r"D:/_caches/huggingface"
OUT_DIR      = r"D:/Alice/tools/auto-rig-fix/work/generated"
BRIDGE_CMD   = r"D:/Alice/tools/auto-rig-fix/bridge_cmd.py"

# Hunyuan inner-script template (runs in hunyuan portable python)
HUNYUAN_INNER = r'''
import sys, os
os.environ["HF_HOME"] = r"{hfhome}"
os.environ["HUGGINGFACE_HUB_CACHE"] = os.path.join(r"{hfhome}", "hub")
sys.path.insert(0, r"{repo}")
from PIL import Image
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline

out_glb = r"{out_glb}"
front = r"{front}"
left  = r"{left}"
back  = r"{back}"

views = {{}}
views["front"] = Image.open(front).convert("RGBA")
if left and os.path.exists(left): views["left"]  = Image.open(left).convert("RGBA")
if back and os.path.exists(back): views["back"]  = Image.open(back).convert("RGBA")

print("[hunyuan] loading {repo_id}/{subf}...")
pipe = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
    "{repo_id}", subfolder="{subf}"
)
print(f"[hunyuan] inference views={{list(views.keys())}}")
mesh = pipe(image=views)[0]
mesh.export(out_glb)
print(f"[hunyuan] saved {{out_glb}}")
'''

def gerar_glb(front, left=None, back=None, nome="Alice_Hunyuan"):
    os.makedirs(OUT_DIR, exist_ok=True)
    out_glb = os.path.join(OUT_DIR, f"{nome}.glb")
    inner = HUNYUAN_INNER.format(
        repo=HUNYUAN_REPO, hfhome=HF_HOME, repo_id=HUNYUAN_MV_REPO, subf=HUNYUAN_MV_SUBFOLDER,
        out_glb=out_glb, front=front, left=left or "", back=back or "",
    )
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(inner); inner_path = f.name
    print(f"[1/2] Hunyuan3D-2mv-turbo (front/left/back) ...")
    try:
        r = subprocess.run([HUNYUAN_PY, inner_path], cwd=HUNYUAN_REPO, capture_output=False)
        if r.returncode != 0:
            print(f"ERRO hunyuan exit {r.returncode}"); return None
    finally:
        try: os.unlink(inner_path)
        except: pass
    if not os.path.exists(out_glb):
        print(f"ERRO GLB nao gerado em {out_glb}"); return None
    return out_glb

def enviar_blender(glb_path, nome):
    print(f"[2/2] Bridge -> game_builder.execute_ultimate_pipeline ...")
    script = f"""
import sys
sys.path.insert(0, r'D:/Alice/tools/auto-rig-fix/live')
import importlib, game_builder
importlib.reload(game_builder)
print('RESULT:', game_builder.execute_ultimate_pipeline(r"{glb_path}", "{nome}"))
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script); sp = f.name
    try:
        r = subprocess.run(["python", BRIDGE_CMD, "--file", sp], capture_output=True, text=True, timeout=900)
        print(r.stdout)
        if r.returncode != 0: print("STDERR:", r.stderr)
    finally:
        os.unlink(sp)

if __name__ == "__main__":
    base = r"D:/Alice/tools/dress/regen"
    front = sys.argv[1] if len(sys.argv) > 1 else f"{base}/in_front.png"
    left  = sys.argv[2] if len(sys.argv) > 2 else f"{base}/in_left.png"
    back  = sys.argv[3] if len(sys.argv) > 3 else f"{base}/in_back.png"
    nome  = sys.argv[4] if len(sys.argv) > 4 else "Alice_Hunyuan_v1"
    glb = gerar_glb(front, left, back, nome)
    if glb:
        print(f"GLB: {glb}")
        enviar_blender(glb, nome)
