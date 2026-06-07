# -*- coding: utf-8 -*-
"""Loop sim per piece chapeleiro. Para cada peca:
1. Skip se ja approved
2. Garante Florence2 crop existe (chama florence_mask se faltar)
3. simulate_until_approved (max 8 iters c/ damping)
4. Salva resultado, avanca proxima peca
"""
import os, sys, json, glob, shutil, urllib.request, time
sys.path.insert(0, r"D:/Alice/tools/auto-rig-fix")
sys.path.insert(0, r"D:/Alice/tools/auto-rig-fix/live")

from pipeline_pre_blender_sim import simulate_until_approved

REGISTRY = r"D:/Alice/tools/auto-rig-fix/work/manifests/outfits_registry.json"
MANIFESTS = r"D:/Alice/tools/auto-rig-fix/work/manifests"
FL_MASKS = r"D:/Alice/tools/auto-rig-fix/work/florence_masks"
SIM_APPROVED = r"D:/Alice/tools/auto-rig-fix/work/sim_approved"
COMFY = "http://127.0.0.1:8188"
COMFY_IN = r"E:/ComfyUI_windows_portable/ComfyUI/input"
COMFY_OUT = r"E:/ComfyUI_windows_portable/ComfyUI/output"


def ensure_florence_crop(piece_name, refs_dir, pattern, fl_prompt, ref_img_key):
    crop = os.path.join(FL_MASKS, f"{piece_name}_crop.png")
    if os.path.exists(crop): return crop
    os.makedirs(FL_MASKS, exist_ok=True)
    os.makedirs(COMFY_IN, exist_ok=True)
    steps = sorted(glob.glob(os.path.join(refs_dir, pattern)))
    if not steps: return None
    try: idx = int(str(ref_img_key).replace('img','').split('/')[0]) - 1
    except: idx = 0
    idx = max(0, min(idx, len(steps)-1))
    step = steps[idx]
    name = os.path.basename(step)
    shutil.copy2(step, os.path.join(COMFY_IN, name))
    wf = {
        "1": {"inputs":{"image":name,"upload":"image"},"class_type":"LoadImage"},
        "2": {"inputs":{"model":"microsoft/Florence-2-base-ft","precision":"fp16"},
              "class_type":"DownloadAndLoadFlorence2Model"},
        "10": {"inputs":{"image":["1",0],"florence2_model":["2",0],"text_input":fl_prompt,
                "task":"referring_expression_segmentation","fill_mask":True,
                "output_mask_select":"","keep_model_loaded":True,"max_new_tokens":1024,
                "num_beams":3,"do_sample":False,"seed":1},
               "class_type":"Florence2Run"},
        "20": {"inputs":{"mask":["10",1]},"class_type":"MaskToImage"},
        "30": {"inputs":{"images":["20",0],"filename_prefix":f"fl_{piece_name}"},
               "class_type":"SaveImage"}
    }
    req = urllib.request.Request(COMFY+"/prompt",
                                  data=json.dumps({"prompt":wf,"client_id":f"sim_{piece_name}"}).encode(),
                                  headers={"Content-Type":"application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=120).read())
    pid = r["prompt_id"]
    t0 = time.time()
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
    mask_dst = os.path.join(FL_MASKS, f"{piece_name}.png")
    shutil.copy2(src, mask_dst)
    from PIL import Image
    src_step = os.path.join(refs_dir, name)
    img = Image.open(src_step).convert('RGB')
    mask = Image.open(mask_dst).convert('L').resize(img.size)
    bbox = mask.getbbox()
    if not bbox: return None
    cr = img.crop(bbox); mk = mask.crop(bbox)
    rgba = cr.convert('RGBA'); rgba.putalpha(mk)
    rgba.save(crop)
    return crop


def main():
    reg = json.load(open(REGISTRY, encoding='utf-8'))
    cfg = reg['outfits']['chapeleiro']
    m = json.load(open(os.path.join(MANIFESTS, cfg['manifest']), encoding='utf-8'))
    fl_prompts = {p['name']: p['florence2_prompt'] for p in m.get('florence2_prompts_per_piece',[])}
    refs_dir = cfg['refs_dir']; pattern = cfg['step_images_pattern']
    os.makedirs(SIM_APPROVED, exist_ok=True)

    results = {'approved':[], 'best_only':[], 'failed':[]}
    for p in sorted(m['pieces'], key=lambda x: x['order']):
        name = p['name']
        approved_file = os.path.join(SIM_APPROVED, f"{name}.json")
        if os.path.exists(approved_file):
            print(f"\n[SKIP] {name} ja approved")
            results['approved'].append(name); continue
        print(f"\n========== PIECE {p['order']:02d} {name} ==========")
        # Florence2 crop
        fl_prompt = fl_prompts.get(name, p.get('shape',name))
        crop = ensure_florence_crop(name, refs_dir, pattern, fl_prompt, p.get('ref_img','img1'))
        if not crop:
            print(f"  [SKIP] sem Florence crop"); results['failed'].append(name); continue
        # Sim loop
        try:
            r = simulate_until_approved(name, max_iters=6)
            if r:
                results['approved'].append(name)
            else:
                results['best_only'].append(name)
        except Exception as e:
            print(f"  [ERR] {e}"); results['failed'].append(name)

    print("\n===== FINAL REPORT =====")
    print(f"APPROVED 9+: {len(results['approved'])}/{len(m['pieces'])}")
    for n in results['approved']: print(f"  + {n}")
    print(f"BEST ONLY (sem 9): {len(results['best_only'])}/{len(m['pieces'])}")
    for n in results['best_only']: print(f"  ~ {n}")
    print(f"FAILED: {len(results['failed'])}/{len(m['pieces'])}")
    for n in results['failed']: print(f"  - {n}")

if __name__ == '__main__':
    main()
