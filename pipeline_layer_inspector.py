# -*- coding: utf-8 -*-
"""
pipeline_layer_inspector — esteira profissional camada-por-camada.

Para cada LAYER (ex: saia_L1, corpete, mangas, boots, faca):
  Para cada VISTA (front, side, back):
    1. Crop o ROI da imagem ref correspondente
    2. Submete ao workflow ComfyUI layer_inspector_api.json
    3. Recolhe 9 SaveImage outputs + extrai 9 JSONs do /history (texto retornado por cada InspetorNode)
  Consolida 27 specs (9 inspetores × 3 vistas) em layer_spec.json
  Aciona bridge -> Blender game_builder.apply_layer_spec(layer_name, spec_path)
  Espera aprovacao do usuario antes de avancar pra proxima layer
"""
import os, sys, json, time, shutil, tempfile, subprocess, urllib.request

COMFY = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
COMFY_OUT = r"E:/ComfyUI_windows_portable/ComfyUI/output"
COMFY_IN  = r"E:/ComfyUI_windows_portable/ComfyUI/input"
WORK      = r"D:/Alice/tools/auto-rig-fix/work"
SPECS_DIR = os.path.join(WORK, "layer_specs")
WF_TEMPLATE = os.path.join(WORK, "workflows", "layer_inspector_api.json")
BRIDGE_CMD = r"D:/Alice/tools/auto-rig-fix/bridge_cmd.py"

INSPECTORS = ["lines", "shadow", "texture", "overred", "overgreen",
              "grid", "palette", "curves", "depth"]

def _post(path, data):
    req = urllib.request.Request(COMFY + path,
                                  data=json.dumps(data).encode(),
                                  headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())

def _get(path):
    return json.loads(urllib.request.urlopen(COMFY + path, timeout=60).read())

def upload(image_path):
    name = os.path.basename(image_path)
    dst = os.path.join(COMFY_IN, name)
    os.makedirs(COMFY_IN, exist_ok=True)
    shutil.copy2(image_path, dst)
    return name

def inspect_image(image_path, layer_name, view):
    """Roda o workflow inspetor 1x e devolve dict de specs + paths das imagens salvas."""
    name = upload(image_path)
    wf = json.load(open(WF_TEMPLATE))
    # drop comment keys (ComfyUI rejects non-node keys)
    for k in [k for k in wf if k.startswith("_")]:
        del wf[k]
    wf["1"]["inputs"]["image"] = name
    # rename SaveImage prefixes para incluir layer+view (saida unica)
    prefix_map = {"20":"lines","21":"shadow","22":"texture","23":"overred","24":"overgreen",
                  "25":"grid","26":"palette","27":"curves","28":"depth"}
    for nid, key in prefix_map.items():
        wf[nid]["inputs"]["filename_prefix"] = f"li_{layer_name}_{view}_{key}"

    r = _post("/prompt", {"prompt": wf, "client_id": f"li_{layer_name}_{view}"})
    pid = r["prompt_id"]
    # poll
    t0 = time.time()
    while time.time() - t0 < 600:
        h = _get(f"/history/{pid}")
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("completed"):
                break
            if st.get("status_str") == "error":
                raise RuntimeError(f"workflow error: {st}")
        time.sleep(2)

    # collect SaveImage outputs (per node)
    outs = h[pid].get("outputs", {})
    images = {}
    for nid, key in prefix_map.items():
        for img in outs.get(nid, {}).get("images", []):
            src = os.path.join(COMFY_OUT, img.get("subfolder", ""), img["filename"])
            if os.path.exists(src):
                dst = os.path.join(SPECS_DIR, layer_name, f"{view}_{key}.png")
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                images[key] = dst

    # ComfyUI nao retorna STRING outputs no history por padrao -- temos que ler via /view ou
    # rodar workflow com OUTPUT_NODE=True. Por enquanto specs vem so dos pixels (paths).
    # JSON spec sera extraido downstream via cv2 quando precisar (ou re-rodar inspetor isolado).
    return {"layer": layer_name, "view": view, "images": images}

def inspect_layer(layer_name, front_path, side_path=None, back_path=None):
    """Roda inspetor pras 3 vistas + grava layer_spec.json consolidado."""
    print(f"\n[INSPECT] {layer_name}")
    results = {}
    results["front"] = inspect_image(front_path, layer_name, "front")
    if side_path: results["side"] = inspect_image(side_path, layer_name, "side")
    if back_path: results["back"] = inspect_image(back_path, layer_name, "back")
    spec_path = os.path.join(SPECS_DIR, layer_name, "layer_spec.json")
    with open(spec_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"  spec -> {spec_path}")
    return spec_path

def send_to_blender(layer_name, spec_path):
    """Aciona o bridge pra Blender consumir o spec da layer."""
    script = f'''
import sys
sys.path.insert(0, r"D:/Alice/tools/auto-rig-fix/live")
import importlib, game_builder
importlib.reload(game_builder)
if hasattr(game_builder, "apply_layer_spec"):
    print("APPLY:", game_builder.apply_layer_spec("{layer_name}", r"{spec_path}"))
else:
    print("ERRO: game_builder.apply_layer_spec ainda nao existe")
'''
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(script); p = f.name
    try:
        r = subprocess.run(["python", BRIDGE_CMD, "--file", p],
                            capture_output=True, text=True, timeout=600)
        print(r.stdout)
        if r.returncode: print("STDERR:", r.stderr)
    finally:
        os.unlink(p)

if __name__ == "__main__":
    # Uso: python pipeline_layer_inspector.py <layer_name> <front_img> [side] [back]
    layer = sys.argv[1] if len(sys.argv) > 1 else "saia_L1"
    front = sys.argv[2] if len(sys.argv) > 2 else r"D:/Alice/tools/dress/regen/in_front.png"
    side  = sys.argv[3] if len(sys.argv) > 3 else r"D:/Alice/tools/dress/regen/in_left.png"
    back  = sys.argv[4] if len(sys.argv) > 4 else r"D:/Alice/tools/dress/regen/in_back.png"
    spec = inspect_layer(layer, front, side, back)
    send_to_blender(layer, spec)
