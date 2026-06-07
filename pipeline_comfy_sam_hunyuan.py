# -*- coding: utf-8 -*-
"""
pipeline_comfy_sam_hunyuan - end-to-end: Image -> SAM masks + Hunyuan3D GLB
(via ComfyUI API) -> Blender bridge -> game_builder slice + rig.

ComfyUI must be running at http://127.0.0.1:8188.
The workflow JSON template is loaded from work/workflows/sam_hunyuan_api.json.
"""
import os, sys, json, time, urllib.request, urllib.parse, shutil, tempfile, subprocess

COMFY_URL = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
COMFY_OUT = r"E:/ComfyUI_windows_portable/ComfyUI/output"
COMFY_IN  = r"E:/ComfyUI_windows_portable/ComfyUI/input"
WORK_DIR  = r"D:/Alice/tools/auto-rig-fix/work"
MASKS_DIR = os.path.join(WORK_DIR, "masks")
GLB_DIR   = os.path.join(WORK_DIR, "generated")
BRIDGE_CMD = r"D:/Alice/tools/auto-rig-fix/bridge_cmd.py"
WORKFLOW_TEMPLATE = os.path.join(WORK_DIR, "workflows", "sam_hunyuan_api.json")

def _post(path, data):
    req = urllib.request.Request(COMFY_URL + path, data=json.dumps(data).encode(),
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

def _get(path):
    with urllib.request.urlopen(COMFY_URL + path, timeout=60) as r:
        return json.loads(r.read())

def upload_image(image_path):
    """Upload image to ComfyUI/input/."""
    name = os.path.basename(image_path)
    dst = os.path.join(COMFY_IN, name)
    os.makedirs(COMFY_IN, exist_ok=True)
    shutil.copy2(image_path, dst)
    return name

def queue_workflow(workflow_dict, client_id="pipeline_alice"):
    """POST /prompt and return prompt_id."""
    payload = {"prompt": workflow_dict, "client_id": client_id}
    return _post("/prompt", payload)["prompt_id"]

def wait_for_prompt(prompt_id, timeout=1800):
    """Poll /history/<id> until done."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            h = _get(f"/history/{prompt_id}")
            if prompt_id in h and h[prompt_id].get("status", {}).get("completed"):
                return h[prompt_id]
        except Exception:
            pass
        time.sleep(3)
    raise TimeoutError(f"prompt {prompt_id} timed out after {timeout}s")

def collect_outputs(prompt_result, mask_keys=("knife", "belts", "gloves"), glb_key="glb"):
    """Walk outputs node-by-node and copy result files to MASKS_DIR / GLB_DIR."""
    os.makedirs(MASKS_DIR, exist_ok=True); os.makedirs(GLB_DIR, exist_ok=True)
    saved = {}
    outputs = prompt_result.get("outputs", {})
    for nid, nout in outputs.items():
        if "images" in nout:
            for img in nout["images"]:
                src = os.path.join(COMFY_OUT, img.get("subfolder", ""), img["filename"])
                if not os.path.exists(src): continue
                low = img["filename"].lower()
                for k in mask_keys:
                    if k in low:
                        dst = os.path.join(MASKS_DIR, f"alice_mask_{k}.png")
                        shutil.copy2(src, dst); saved[f"mask_{k}"] = dst
        if "mesh" in nout or "glb" in nout or "model" in nout:
            for f in nout.get("mesh", nout.get("glb", nout.get("model", []))):
                src = os.path.join(COMFY_OUT, f.get("subfolder", ""), f["filename"])
                if os.path.exists(src):
                    dst = os.path.join(GLB_DIR, "alice.glb")
                    shutil.copy2(src, dst); saved["glb"] = dst
    return saved

def patch_workflow(template, image_name):
    """Inject input image filename into LoadImage node of the workflow."""
    wf = json.loads(json.dumps(template))  # deep copy
    for nid, node in wf.items():
        if node.get("class_type") == "LoadImage":
            node["inputs"]["image"] = image_name
            break
    return wf

def send_to_blender(glb_path, masks_dir, character="Alice_Comfy"):
    """Trigger Blender bridge to rig the GLB and slice accessories by masks."""
    script = f'''
import sys
sys.path.insert(0, r"D:/Alice/tools/auto-rig-fix/live")
import importlib, game_builder
importlib.reload(game_builder)
print("PIPELINE:", game_builder.execute_ultimate_pipeline(r"{glb_path}", "{character}"))
arm = "Rig_{character}"; mesh = "{character}_Mesh"
print("SLICE:", game_builder.universal_accessory_slicer(mesh, arm, r"{masks_dir}", "alice"))
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script); path = f.name
    try:
        r = subprocess.run(["python", BRIDGE_CMD, "--file", path], capture_output=True, text=True, timeout=1800)
        print(r.stdout)
        if r.returncode: print("STDERR:", r.stderr)
    finally:
        os.unlink(path)

def main(image_path, character="Alice_Comfy"):
    if not os.path.exists(image_path):
        print("imagem nao encontrada:", image_path); sys.exit(1)
    if not os.path.exists(WORKFLOW_TEMPLATE):
        print("workflow template ausente:", WORKFLOW_TEMPLATE); sys.exit(1)

    print(f"[1/4] upload {os.path.basename(image_path)} -> ComfyUI/input")
    name = upload_image(image_path)

    print("[2/4] queue workflow (SAM + Hunyuan3D)")
    template = json.load(open(WORKFLOW_TEMPLATE))
    wf = patch_workflow(template, name)
    pid = queue_workflow(wf)
    print(f"  prompt_id={pid}")

    print("[3/4] waiting for completion (timeout 30min)")
    result = wait_for_prompt(pid)
    saved = collect_outputs(result)
    print(f"  saved: {saved}")

    if "glb" not in saved:
        print("ERRO: GLB nao gerado"); sys.exit(2)

    print("[4/4] Blender bridge: rig + slice accessories")
    send_to_blender(saved["glb"], MASKS_DIR, character)
    print("DONE")

if __name__ == "__main__":
    img = sys.argv[1] if len(sys.argv) > 1 else r"D:/Alice/tools/dress/regen/in_front.png"
    char = sys.argv[2] if len(sys.argv) > 2 else "Alice_Comfy"
    main(img, char)
