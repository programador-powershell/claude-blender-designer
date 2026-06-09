# -*- coding: utf-8 -*-
"""
pipeline_unique3d - Image -> Unique3D -> GLB -> Blender bridge -> game_builder.
Unique3D = front-view + auto multi-view + normal-based mesh reconstruction.
"""
import os, sys, subprocess, tempfile, shutil

UNIQUE_DIR = r"D:/Alice/tools/Unique3D"
UNIQUE_PY  = r"C:/Users/pslo9/miniconda3/envs/unique3d/python.exe"
OUT_DIR    = r"D:/Alice/tools/auto-rig-fix/work/generated"
BRIDGE_CMD = r"D:/Alice/tools/auto-rig-fix/bridge_cmd.py"

INNER = r'''
import sys, os, shutil
sys.path.insert(0, r"{repo}")
os.environ["HF_HOME"] = r"D:/_caches/huggingface"
from PIL import Image
from app.gradio_3dgen import generate3dv2

front = r"{front}"
out_glb = r"{out_glb}"
img = Image.open(front).convert("RGBA")
print("[unique3d] running generate3dv2 ...")
ret_mesh, _ = generate3dv2(img, input_processing=True, seed={seed}, render_video=False, do_refine=False)
print("[unique3d] gen ->", ret_mesh)
if ret_mesh and os.path.exists(ret_mesh):
    shutil.copy2(ret_mesh, out_glb)
    print("[unique3d] saved", out_glb)
else:
    print("[unique3d] ERR: ret_mesh missing")
'''

def gerar(front, nome="Alice_Unique3D", seed=42):
    os.makedirs(OUT_DIR, exist_ok=True)
    out_glb = os.path.join(OUT_DIR, f"{nome}.glb")
    inner = INNER.format(repo=UNIQUE_DIR, front=front, out_glb=out_glb, seed=seed)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(inner); ip = f.name
    print(f"[1/2] Unique3D front={front}")
    try:
        r = subprocess.run([UNIQUE_PY, ip], cwd=UNIQUE_DIR)
        if r.returncode != 0:
            print(f"ERR unique3d exit {r.returncode}"); return None
    finally:
        os.unlink(ip)
    return out_glb if os.path.exists(out_glb) else None

def enviar(glb, nome):
    print("[2/2] -> Blender bridge / game_builder")
    s = f'''
import sys
sys.path.insert(0, r'D:/Alice/tools/auto-rig-fix/live')
import importlib, game_builder
importlib.reload(game_builder)
print("RESULT:", game_builder.execute_ultimate_pipeline(r"{glb}", "{nome}"))
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(s); p = f.name
    try:
        r = subprocess.run(["python", BRIDGE_CMD, "--file", p], capture_output=True, text=True, timeout=900)
        print(r.stdout);
        if r.returncode: print("STDERR:", r.stderr)
    finally:
        os.unlink(p)

if __name__ == "__main__":
    front = sys.argv[1] if len(sys.argv) > 1 else r"D:/Alice/tools/dress/regen/in_front.png"
    nome  = sys.argv[2] if len(sys.argv) > 2 else "Alice_Unique3D"
    if not os.path.exists(front): print("imagem nao existe"); sys.exit(1)
    glb = gerar(front, nome)
    if glb:
        print(f"GLB: {glb}")
        enviar(glb, nome)
    else:
        print("abortado.")
