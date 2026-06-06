# -*- coding: utf-8 -*-
"""
pipeline_orquestrador - AUTOMACAO PONTA A PONTA (IMAGE -> 3D -> BLENDER RIG)
Roda FORA do Blender. Pega imagem, chama TripoSR p/ gerar GLB,
injeta no Blender via bridge_cmd.py -> game_builder.execute_ultimate_pipeline().
"""
import os, sys, subprocess, json, tempfile, shutil

# CONFIG
TRIPOSR_DIR = r"D:/Alice/tools/TripoSR"
TRIPOSR_PY  = r"E:/ComfyUI_windows_portable/python_embeded/python.exe"  # tem torch/cv2
OUT_DIR     = r"D:/Alice/tools/auto-rig-fix/work/generated"
BRIDGE_CMD  = r"D:/Alice/tools/auto-rig-fix/bridge_cmd.py"
BRIDGE_PY   = r"python"  # bridge_cmd usa python sistema (subprocess via socket)

def gerar_malha_3d_do_zero(caminho_imagem, nome_personagem):
    print(f"\n[1/2] TripoSR esculpindo: {nome_personagem} <- {caminho_imagem}")
    os.makedirs(OUT_DIR, exist_ok=True)
    arquivo_saida_glb = os.path.join(OUT_DIR, f"{nome_personagem}.glb")
    arquivo_saida_obj = os.path.join(OUT_DIR, f"{nome_personagem}.obj")

    # TripoSR run.py
    run_py = os.path.join(TRIPOSR_DIR, "run.py")
    if not os.path.exists(run_py):
        print(f"ERRO: TripoSR run.py nao encontrado em {run_py}")
        return None

    cmd = [
        TRIPOSR_PY, run_py,
        caminho_imagem,
        "--output-dir", OUT_DIR,
        "--model-save-format", "glb",
    ]
    try:
        subprocess.run(cmd, check=True, cwd=TRIPOSR_DIR)
    except subprocess.CalledProcessError as e:
        print(f"ERRO TripoSR exit {e.returncode}")
        return None

    # TripoSR salva como 0/mesh.glb ou mesh.glb
    for cand in [
        os.path.join(OUT_DIR, "0", "mesh.glb"),
        os.path.join(OUT_DIR, "mesh.glb"),
        os.path.join(OUT_DIR, "0", "mesh.obj"),
        os.path.join(OUT_DIR, "mesh.obj"),
    ]:
        if os.path.exists(cand):
            ext = os.path.splitext(cand)[1]
            dest = arquivo_saida_glb if ext == ".glb" else arquivo_saida_obj
            shutil.copy2(cand, dest)
            print(f"-> Malha 3D salva: {dest}")
            return dest

    print("ERRO: TripoSR rodou mas output nao localizado")
    return None

def enviar_para_blender_automatizado(caminho_modelo_3d, nome_personagem):
    print(f"[2/2] Injetando no Blender via bridge_cmd.py...")
    # script Python p/ rodar dentro do Blender via bridge
    script = f"""
import sys
sys.path.insert(0, r'D:/Alice/tools/auto-rig-fix/live')
import importlib, game_builder
importlib.reload(game_builder)
res = game_builder.execute_ultimate_pipeline(r"{caminho_modelo_3d}", "{nome_personagem}")
print("RESULT:", res)
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script); script_path = f.name

    try:
        r = subprocess.run(
            [BRIDGE_PY, BRIDGE_CMD, "--file", script_path],
            capture_output=True, text=True, timeout=600
        )
        print(r.stdout)
        if r.returncode != 0:
            print("STDERR:", r.stderr)
    finally:
        os.unlink(script_path)

# --- EXECUCAO ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python pipeline_orquestrador.py <imagem.png> [nome_personagem]")
        print("Ex:  python pipeline_orquestrador.py D:/Alice/tools/dress/regen/in_front.png Alice_v1")
        sys.exit(1)

    sua_imagem = sys.argv[1]
    nome_do_avatar = sys.argv[2] if len(sys.argv) > 2 else "Alice_Do_Zero_IA"

    if not os.path.exists(sua_imagem):
        print(f"ERRO: imagem nao encontrada: {sua_imagem}"); sys.exit(1)

    modelo_criado = gerar_malha_3d_do_zero(sua_imagem, nome_do_avatar)
    if modelo_criado:
        enviar_para_blender_automatizado(modelo_criado, nome_do_avatar)
    else:
        print("Pipeline abortado.")
