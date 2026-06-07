# -*- coding: utf-8 -*-
"""Esteira autonoma por peca. Loop ate Qwen overall_score == 10.
Cada iter: Florence2 mask -> Blender rebuild -> render 3-views ->
inspectores (lines/shadow/texture/overlay/cv2) -> Qwen multi-criteria ->
auto-tune por next_action.

Uso autonomo (sem aprovacao usuario):
  python pipeline_piece_conveyor.py --outfit chapeleiro --piece bloomer_interno
  python pipeline_piece_conveyor.py --outfit chapeleiro --all   # todas 22

Pre-req: Blender bridge + Qwen llama-server + ComfyUI ON.
Status: work/conveyor_status.json (resume safe).
"""
import os, sys, json, time, subprocess, tempfile, argparse, shutil, urllib.request, base64, glob

ROOT = r"D:/Alice/tools/auto-rig-fix"
LIVE = os.path.join(ROOT, "live")
WORK = os.path.join(ROOT, "work")
BRIDGE = os.path.join(ROOT, "bridge_cmd.py")
QWEN = "http://127.0.0.1:8080/v1/chat/completions"
COMFY = "http://127.0.0.1:8188"
COMFY_IN = r"E:/ComfyUI_windows_portable/ComfyUI/input"
COMFY_OUT = r"E:/ComfyUI_windows_portable/ComfyUI/output"
REGISTRY = os.path.join(WORK, "manifests", "outfits_registry.json")
MANIFESTS_DIR = os.path.join(WORK, "manifests")
FL_MASKS = os.path.join(WORK, "florence_masks")
VALID_DIR = os.path.join(WORK, "validation")
INSPECT_DIR = os.path.join(WORK, "inspectors")
STATUS_FILE = os.path.join(WORK, "conveyor_status.json")
MAX_ITERS = 30
TARGET_SCORE = 10
PLATEAU_LIMIT = 8   # accept best only after 8 same-score iters (try harder)

sys.path.insert(0, LIVE)

def log(msg): print(f"[conveyor] {msg}", flush=True)

def b64(p):
    with open(p, 'rb') as f: return base64.b64encode(f.read()).decode()

def load_status():
    if os.path.exists(STATUS_FILE):
        return json.load(open(STATUS_FILE, encoding='utf-8'))
    return {"pieces": {}}

def save_status(st):
    json.dump(st, open(STATUS_FILE, 'w', encoding='utf-8'), indent=2)

# ============ FLORENCE2 ============
def florence_mask(step_image, prompt, out_name):
    os.makedirs(FL_MASKS, exist_ok=True)
    os.makedirs(COMFY_IN, exist_ok=True)
    name = os.path.basename(step_image)
    shutil.copy2(step_image, os.path.join(COMFY_IN, name))
    wf = {
        "1": {"inputs": {"image": name, "upload": "image"}, "class_type": "LoadImage"},
        "2": {"inputs": {"model": "microsoft/Florence-2-base-ft", "precision": "fp16"},
              "class_type": "DownloadAndLoadFlorence2Model"},
        "10": {"inputs": {"image": ["1",0], "florence2_model": ["2",0], "text_input": prompt,
                          "task": "referring_expression_segmentation", "fill_mask": True,
                          "output_mask_select": "", "keep_model_loaded": True,
                          "max_new_tokens": 1024, "num_beams": 3, "do_sample": False, "seed": 1},
               "class_type": "Florence2Run"},
        "20": {"inputs": {"mask": ["10",1]}, "class_type": "MaskToImage"},
        "30": {"inputs": {"images": ["20",0], "filename_prefix": f"fl_{out_name}"},
               "class_type": "SaveImage"}
    }
    req = urllib.request.Request(COMFY+"/prompt", data=json.dumps({"prompt": wf, "client_id": f"co_{out_name}"}).encode(),
                                  headers={"Content-Type":"application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=120).read())
    pid = r["prompt_id"]
    t0=time.time()
    while time.time()-t0 < 300:
        h = json.loads(urllib.request.urlopen(COMFY+f"/history/{pid}", timeout=30).read())
        if pid in h:
            st = h[pid].get('status',{})
            if st.get('completed'): break
            if st.get('status_str')=='error': raise RuntimeError(f"wf err: {st}")
        time.sleep(2)
    outs = h[pid].get('outputs',{}).get('30',{}).get('images',[])
    if not outs: return None
    src = os.path.join(COMFY_OUT, outs[0].get('subfolder',''), outs[0]['filename'])
    mask_dst = os.path.join(FL_MASKS, f"{out_name}.png")
    shutil.copy2(src, mask_dst)
    # Save RGBA crop
    from PIL import Image
    src_img = Image.open(step_image).convert('RGB')
    mask = Image.open(mask_dst).convert('L').resize(src_img.size)
    bbox = mask.getbbox()
    if not bbox:
        log(f"  WARN: empty mask for {out_name}"); return None
    crop_rgb = src_img.crop(bbox); crop_mask = mask.crop(bbox)
    rgba = crop_rgb.convert('RGBA'); rgba.putalpha(crop_mask)
    crop_dst = os.path.join(FL_MASKS, f"{out_name}_crop.png")
    rgba.save(crop_dst)
    return {"mask": mask_dst, "crop": crop_dst, "bbox": bbox}

# ============ BLENDER OPS ============
def bridge_exec(script):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script); p = f.name
    try:
        r = subprocess.run([sys.executable, BRIDGE, '--file', p],
                            capture_output=True, text=True, timeout=600)
        return r.returncode == 0, r.stdout, r.stderr
    finally:
        try: os.unlink(p)
        except Exception: pass

def rebuild_piece(outfit, piece, tune_params=None):
    tune_json = json.dumps(tune_params or {})
    s = f"""
import sys, importlib, json
sys.path.insert(0, r'{LIVE}')
import garment_schema, garment_builder, garment_fit_to_body, garment_outfit_loader
importlib.reload(garment_schema); importlib.reload(garment_builder)
importlib.reload(garment_fit_to_body); importlib.reload(garment_outfit_loader)
tune = json.loads(r'''{tune_json}''')
print('REMOVE:', garment_builder.remove_piece('{piece}'))
bp = garment_outfit_loader.build_blueprint_for('{outfit}')
# Apply tune overrides
for p in bp.pieces:
    if p.id == '{piece}':
        if tune.get('z_top') is not None: p.params['z_top'] = tune['z_top']
        if tune.get('z_bot') is not None: p.params['z_bot'] = tune['z_bot']
        if tune.get('rx') is not None: p.params['rx'] = tune['rx']
        if tune.get('ry') is not None: p.params['ry'] = tune['ry']
print('BUILD:', garment_builder.build_single_piece(bp, '{piece}', character_name='Alice_Base_Body', collection_name='PA_Alice_{outfit.capitalize()}'))
"""
    ok, out, err = bridge_exec(s)
    return ok, out

def render_3views(piece):
    s = f"""
import bpy, math, os
OUT = r'{VALID_DIR}'
os.makedirs(OUT, exist_ok=True)
def cam(name, loc, rot):
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    c = bpy.data.objects.get(name) or bpy.data.objects.new(name, cd)
    if not c.users_collection: bpy.context.scene.collection.objects.link(c)
    c.location = loc; c.rotation_euler = rot
    c.data.type='ORTHO'; c.data.ortho_scale=2.2
    return c
cam('VAL_FRONT',(0,-4,1.0),(math.radians(90),0,0))
cam('VAL_SIDE',(4,0,1.0),(math.radians(90),0,math.radians(90)))
cam('VAL_BACK',(0,4,1.0),(math.radians(90),0,math.radians(180)))
# Setup lighting if not present
if not bpy.data.objects.get('CONV_KEY'):
    bpy.ops.object.light_add(type='AREA', location=(2,-3,3)); bpy.context.object.name='CONV_KEY'; bpy.context.object.data.energy=500
if not bpy.data.objects.get('CONV_FILL'):
    bpy.ops.object.light_add(type='AREA', location=(-2,-2,2)); bpy.context.object.name='CONV_FILL'; bpy.context.object.data.energy=200
sc = bpy.context.scene
sc.render.resolution_x=600; sc.render.resolution_y=800
sc.render.image_settings.file_format='PNG'
files=[]
for cn in ['VAL_FRONT','VAL_SIDE','VAL_BACK']:
    sc.camera = bpy.data.objects[cn]
    p = os.path.join(OUT, f'{piece}_'+cn+'.png')
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    files.append(p)
print('RENDERS:', files)
"""
    ok, out, err = bridge_exec(s)
    return [os.path.join(VALID_DIR, f"{piece}_VAL_{v}.png") for v in ['FRONT','SIDE','BACK']]

# ============ INSPECTORS (cv2 + LayerInspector) ============
def cv2_inspect(render_path, ref_crop_path, out_prefix):
    """SSIM + diff overlay + edge match score."""
    import cv2, numpy as np
    from skimage.metrics import structural_similarity as ssim
    os.makedirs(INSPECT_DIR, exist_ok=True)
    r = cv2.imread(render_path); f = cv2.imread(ref_crop_path)
    if r is None or f is None: return {}
    h = min(r.shape[0], f.shape[0]); w = min(r.shape[1], f.shape[1])
    r = cv2.resize(r, (w, h)); f = cv2.resize(f, (w, h))
    rg = cv2.cvtColor(r, cv2.COLOR_BGR2GRAY); fg = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
    s = ssim(rg, fg)
    # Edge detection both
    edges_r = cv2.Canny(rg, 50, 150); edges_f = cv2.Canny(fg, 50, 150)
    edge_overlap = float((edges_r & edges_f).sum()) / max(edges_f.sum(), 1)
    # Color hist diff
    hist_r = cv2.calcHist([r], [0,1,2], None, [8,8,8], [0,256]*3)
    hist_f = cv2.calcHist([f], [0,1,2], None, [8,8,8], [0,256]*3)
    cv2.normalize(hist_r, hist_r); cv2.normalize(hist_f, hist_f)
    color_corr = cv2.compareHist(hist_r, hist_f, cv2.HISTCMP_CORREL)
    # Diff overlay (red where mismatch, green where match)
    diff = cv2.absdiff(r, f).max(axis=2)
    overlay_red = r.copy(); overlay_red[diff > 40] = [0, 0, 255]
    overlay_green = f.copy(); overlay_green[diff < 20] = [0, 255, 0]
    cv2.imwrite(os.path.join(INSPECT_DIR, f'{out_prefix}_overlay_red.png'), overlay_red)
    cv2.imwrite(os.path.join(INSPECT_DIR, f'{out_prefix}_overlay_green.png'), overlay_green)
    cv2.imwrite(os.path.join(INSPECT_DIR, f'{out_prefix}_edges_render.png'), edges_r)
    cv2.imwrite(os.path.join(INSPECT_DIR, f'{out_prefix}_edges_ref.png'), edges_f)
    return {"ssim": round(s,3), "edge_overlap": round(edge_overlap,3), "color_corr": round(color_corr,3)}

# ============ QWEN ============
def qwen_validate(render_path, ref_path, piece):
    from vision_prompt_lib import render_vs_ref_prompt, soulslike_system_prompt
    rb = b64(render_path); fb = b64(ref_path)
    prompt = render_vs_ref_prompt(piece)
    payload = {
        "model": "qwen3-vl",
        "messages": [
            {"role":"system","content": soulslike_system_prompt()},
            {"role":"user","content":[
                {"type":"image_url","image_url":{"url":f"data:image/png;base64,{rb}"}},
                {"type":"image_url","image_url":{"url":f"data:image/png;base64,{fb}"}},
                {"type":"text","text":prompt}
            ]}
        ],
        "max_tokens": 300, "temperature": 0.0
    }
    req = urllib.request.Request(QWEN, data=json.dumps(payload).encode(),
                                  headers={"Content-Type":"application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=600).read())
    txt = r['choices'][0]['message']['content'].strip()
    if txt.startswith('```'): txt = txt.strip('`').lstrip('json').strip()
    try: return json.loads(txt)
    except Exception: return {"_raw": txt, "overall_score": 0}

# ============ AUTO-TUNE ============
def auto_tune(prev_params, next_action, current_params, iter_n=1):
    """Heuristic tune by Qwen's next_action. Iter-varying to break plateaus."""
    new = dict(current_params or {})
    a = (next_action or '').lower()
    delta = 0.02 * iter_n   # increase amplitude each iter
    if 'position' in a:
        new['z_top'] = (new.get('z_top') or 1.0) + delta
        new['z_bot'] = (new.get('z_bot') or 0.5) + delta
    elif 'proportion' in a:
        sc = 1.0 + 0.05 * iter_n
        new['rx'] = (new.get('rx') or 0.22) * sc
        new['ry'] = (new.get('ry') or 0.16) * sc
    elif 'shape' in a:
        new['rx'] = (new.get('rx') or 0.22) * (1.0 - 0.03*iter_n)
        new['ry'] = (new.get('ry') or 0.16) * (1.0 + 0.05*iter_n)
    elif 'color' in a or 'detail' in a:
        # Bump lighting energy
        new['_light_energy_mult'] = (new.get('_light_energy_mult') or 1.0) * 1.5
        new['_segments'] = min((new.get('_segments') or 24) + 8, 64)
    return new

# ============ CONVEYOR ============
def conveyor(outfit, piece):
    log(f"START piece={piece} outfit={outfit}")
    st = load_status()
    pkey = f"{outfit}:{piece}"
    if st['pieces'].get(pkey, {}).get('accepted'):
        log(f"  already accepted - skip"); return True
    reg = json.load(open(REGISTRY, encoding='utf-8'))
    cfg = reg['outfits'][outfit]
    manifest = json.load(open(os.path.join(MANIFESTS_DIR, cfg['manifest']), encoding='utf-8'))
    pdata = next((x for x in manifest['pieces'] if x['name'] == piece), None)
    if not pdata: log(f"  ERR piece not in manifest"); return False

    # Florence2 prompt
    prompts_map = {p['name']: p['florence2_prompt'] for p in manifest.get('florence2_prompts_per_piece', [])}
    fl_prompt = prompts_map.get(piece, pdata.get('shape', piece))
    # Step image
    steps = sorted(glob.glob(os.path.join(cfg['refs_dir'], cfg['step_images_pattern'])))
    if not steps: log(f"  ERR no step images"); return False
    # Use img1 (overview) for pieces - it shows all on mannequin
    step_idx = 0
    if pdata.get('ref_img', '').startswith('img'):
        try: step_idx = max(0, min(int(pdata['ref_img'].replace('img','').split('/')[0]) - 1, len(steps)-1))
        except: pass
    step_path = steps[step_idx]
    log(f"  step={os.path.basename(step_path)} florence_prompt='{fl_prompt}'")

    # FLORENCE2 (1x se ja existe)
    crop_path = os.path.join(FL_MASKS, f"{piece}_crop.png")
    if not os.path.exists(crop_path):
        log(f"  Florence2 mask...")
        r = florence_mask(step_path, fl_prompt, piece)
        if not r: log(f"  ERR florence empty mask"); return False
        crop_path = r['crop']
    log(f"  ref crop: {crop_path}")

    tune = {}
    history = []
    for iter_n in range(1, MAX_ITERS+1):
        log(f"  ITER {iter_n}/{MAX_ITERS} tune={tune}")
        # REBUILD
        ok, _ = rebuild_piece(outfit, piece, tune_params=tune)
        if not ok: log(f"  ERR rebuild"); return False
        # RENDER
        renders = render_3views(piece)
        front = renders[0]
        if not os.path.exists(front): log(f"  ERR render"); return False
        # CV2 INSPECT
        cv = cv2_inspect(front, crop_path, f"{piece}_it{iter_n:02d}")
        log(f"  cv2: {cv}")
        # QWEN
        try:
            q = qwen_validate(front, crop_path, piece)
        except Exception as e:
            log(f"  Qwen err: {e}"); q = {"overall_score": 0, "_err": str(e)}
        log(f"  qwen: overall={q.get('overall_score')} action={q.get('next_action')}")
        history.append({"iter": iter_n, "tune": tune, "cv2": cv, "qwen": q})
        # Save running status
        st['pieces'][pkey] = {"history": history, "accepted": False,
                              "best_score": max((h['qwen'].get('overall_score',0) for h in history), default=0)}
        save_status(st)
        score = q.get('overall_score', 0)
        if score >= TARGET_SCORE:
            log(f"  ACCEPTED (score {score})")
            st['pieces'][pkey]['accepted'] = True
            st['pieces'][pkey]['final_iter'] = iter_n
            save_status(st)
            return True
        # Plateau detect: if last PLATEAU_LIMIT iters no improvement, accept best
        recent = [h['qwen'].get('overall_score',0) for h in history[-PLATEAU_LIMIT:]]
        if len(recent) >= PLATEAU_LIMIT and max(recent) == recent[-1] == recent[0]:
            log(f"  PLATEAU ({recent}) - accepting best score {score}")
            st['pieces'][pkey]['accepted'] = True
            st['pieces'][pkey]['final_iter'] = iter_n
            st['pieces'][pkey]['reason'] = 'plateau'
            save_status(st)
            return True
        # AUTO-TUNE
        tune = auto_tune(tune, q.get('next_action'), tune, iter_n=iter_n)
    # Max iters reached - accept best anyway (autonomous mode)
    log(f"  MAX ITERS - accepting best score {st['pieces'][pkey]['best_score']}")
    st['pieces'][pkey]['accepted'] = True
    st['pieces'][pkey]['reason'] = 'max_iters'
    save_status(st)
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--outfit', default='chapeleiro')
    ap.add_argument('--piece', default=None)
    ap.add_argument('--all', action='store_true')
    a = ap.parse_args()
    if a.piece:
        ok = conveyor(a.outfit, a.piece)
        sys.exit(0 if ok else 1)
    if a.all:
        reg = json.load(open(REGISTRY, encoding='utf-8'))
        cfg = reg['outfits'][a.outfit]
        manifest = json.load(open(os.path.join(MANIFESTS_DIR, cfg['manifest']), encoding='utf-8'))
        for p in sorted(manifest['pieces'], key=lambda x: x['order']):
            ok = conveyor(a.outfit, p['name'])
            if not ok: log(f"FAIL on {p['name']} - stopping")
        return
    ap.error("--piece or --all required")

if __name__ == '__main__':
    main()
