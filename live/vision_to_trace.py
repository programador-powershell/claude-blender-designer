# -*- coding: utf-8 -*-
"""Florence2 mask -> cv2.findContours -> JSON curves (u,v normalized 0..1).
Compativel com project_vision_to_mesh.project_vision_coordinates_to_mesh.

Uso:
  python vision_to_trace.py --ref step_image.png --prompt "bloomer shorts" --out work/trace/bloomer.json
"""
import os, sys, json, argparse, time, shutil, urllib.request
import cv2
from PIL import Image

COMFY = "http://127.0.0.1:8188"
COMFY_IN = r"E:/ComfyUI_windows_portable/ComfyUI/input"
COMFY_OUT = r"E:/ComfyUI_windows_portable/ComfyUI/output"


def florence_mask(image_path, prompt, out_name):
    os.makedirs(COMFY_IN, exist_ok=True)
    name = os.path.basename(image_path)
    shutil.copy2(image_path, os.path.join(COMFY_IN, name))
    wf = {
        "1": {"inputs":{"image":name,"upload":"image"},"class_type":"LoadImage"},
        "2": {"inputs":{"model":"microsoft/Florence-2-base-ft","precision":"fp16"},
              "class_type":"DownloadAndLoadFlorence2Model"},
        "10":{"inputs":{"image":["1",0],"florence2_model":["2",0],"text_input":prompt,
              "task":"referring_expression_segmentation","fill_mask":True,
              "output_mask_select":"","keep_model_loaded":True,"max_new_tokens":1024,
              "num_beams":3,"do_sample":False,"seed":1},"class_type":"Florence2Run"},
        "20":{"inputs":{"mask":["10",1]},"class_type":"MaskToImage"},
        "30":{"inputs":{"images":["20",0],"filename_prefix":f"tr_{out_name}"},
              "class_type":"SaveImage"}
    }
    req = urllib.request.Request(COMFY+"/prompt",
        data=json.dumps({"prompt":wf,"client_id":f"tr_{out_name}"}).encode(),
        headers={"Content-Type":"application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=120).read())
    pid = r["prompt_id"]; t0 = time.time()
    while time.time()-t0 < 300:
        h = json.loads(urllib.request.urlopen(COMFY+f"/history/{pid}", timeout=30).read())
        if pid in h:
            st = h[pid].get('status',{})
            if st.get('completed'): break
            if st.get('status_str')=='error': return None
        time.sleep(2)
    outs = h[pid].get('outputs',{}).get('30',{}).get('images',[])
    if not outs: return None
    src = os.path.join(COMFY_OUT, outs[0].get('subfolder',''), outs[0]['filename'])
    dst = os.path.join("D:/Alice/tools/auto-rig-fix/work/florence_masks",
                        f"trace_{out_name}.png")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def trace_contours(mask_path, max_curves=4, min_points=12, simplify_eps=0.003):
    """Extract contours via cv2 + simplify + normalize (0..1)."""
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if mask is None: return []
    h, w = mask.shape
    _, binary = cv2.threshold(mask, 80, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:max_curves]
    curves = []
    for i, c in enumerate(contours):
        if len(c) < min_points: continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, simplify_eps * peri, True)
        pts_norm = [[float(p[0][0])/w, float(p[0][1])/h] for p in approx]
        if len(pts_norm) >= 3:
            if pts_norm[0] != pts_norm[-1]: pts_norm.append(pts_norm[0])
            curves.append({"label": f"curve_{i:02d}", "points": pts_norm,
                           "area_norm": float(cv2.contourArea(c))/(w*h)})
    return curves


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ref', required=True)
    ap.add_argument('--prompt', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--label', default=None)
    a = ap.parse_args()
    label = a.label or os.path.splitext(os.path.basename(a.out))[0]
    print(f"[trace] ref={a.ref} prompt='{a.prompt}'")
    mask_path = florence_mask(a.ref, a.prompt, label)
    if not mask_path: print("ERR Florence mask failed"); sys.exit(1)
    print(f"[trace] mask: {mask_path}")
    curves = trace_contours(mask_path)
    for c in curves: c['label'] = f"{label}_{c['label']}"
    out_data = {"_source_image": a.ref, "_florence_prompt": a.prompt,
                "_mask": mask_path, "curves": curves}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(out_data, open(a.out,'w',encoding='utf-8'), indent=2, ensure_ascii=False)
    print(f"[trace] {len(curves)} curves -> {a.out}")

if __name__ == '__main__':
    main()
