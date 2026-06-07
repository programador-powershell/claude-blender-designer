# -*- coding: utf-8 -*-
"""Pipeline vision-BVH com GATE: peca por peca, validar trace ANTES Blender.

Por peca:
1. Florence2 mask + cv2 contours -> JSON curves (u,v)
2. PIL render preview: contornos sobre body silhouette
3. Qwen3-VL valida preview vs ref crop (score 0-10)
4. SE score >= 8 -> proceed BVH project no Blender
5. SE score < 8 -> try diff Florence2 prompt OU skip peca + log
6. Sequencial 1 peca por vez (sem batch). Nao avanca proxima ate aceitar atual
"""
import os, sys, json, glob, subprocess, tempfile, argparse, time, base64, urllib.request
import cv2, numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, r"D:/Alice/tools/auto-rig-fix")
sys.path.insert(0, r"D:/Alice/tools/auto-rig-fix/live")

ROOT = r"D:/Alice/tools/auto-rig-fix"
LIVE = os.path.join(ROOT, "live")
WORK = os.path.join(ROOT, "work")
BRIDGE = os.path.join(ROOT, "bridge_cmd.py")
REGISTRY = os.path.join(WORK, "manifests", "outfits_registry.json")
MANIFESTS = os.path.join(WORK, "manifests")
TRACE_DIR = os.path.join(WORK, "trace")
PREVIEW_DIR = os.path.join(WORK, "trace_preview")
APPROVED_DIR = os.path.join(WORK, "trace_approved")
FL_MASKS = os.path.join(WORK, "florence_masks")
SIM_DIR = os.path.join(WORK, "simulation")
QWEN = "http://127.0.0.1:8080/v1/chat/completions"

os.makedirs(TRACE_DIR, exist_ok=True); os.makedirs(PREVIEW_DIR, exist_ok=True)
os.makedirs(APPROVED_DIR, exist_ok=True)

MIN_SCORE = 8
MAX_TRACE_ATTEMPTS = 3


def b64(p):
    with open(p, 'rb') as f: return base64.b64encode(f.read()).decode()


def render_trace_preview(trace_json_path, body_silhouette, out_path):
    """PIL: contornos da trace sobre body silhouette."""
    data = json.load(open(trace_json_path, encoding='utf-8'))
    body = Image.open(body_silhouette).convert('RGBA')
    W, H = body.size
    overlay = Image.new('RGBA', body.size, (0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    for c in data.get('curves', []):
        pts = [(int(p[0]*W), int(p[1]*H)) for p in c['points']]
        if len(pts) > 1:
            draw.line(pts + [pts[0]], fill=(255,30,30,255), width=3)
    n = len(data.get('curves', []))
    draw.text((10,10), f"trace {os.path.basename(trace_json_path)} curves={n}", fill=(255,255,255,255))
    composite = Image.alpha_composite(body, overlay)
    composite.convert('RGB').save(out_path)
    return out_path


def qwen_validate_trace(preview_path, ref_crop, piece):
    """Qwen score trace preview vs reference crop."""
    rb = b64(preview_path); fb = b64(ref_crop)
    prompt = f"""Trace validation for piece "{piece}".
Img1: 2D trace preview (red contour) overlay on Alice body silhouette.
Img2: reference crop from source image.
Score 0-10: does the red trace contour MATCH the silhouette of the reference piece?
JSON ONLY: {{"shape_match_score":0,"position_match_score":0,"overall":0,"ready_for_3d":false,"reason":"<short>"}}
ready_for_3d=true ONLY if overall>=8."""
    payload = {
        "model": "qwen3-vl",
        "messages": [{"role":"user","content":[
            {"type":"image_url","image_url":{"url":f"data:image/png;base64,{rb}"}},
            {"type":"image_url","image_url":{"url":f"data:image/png;base64,{fb}"}},
            {"type":"text","text":prompt}
        ]}],
        "max_tokens": 150, "temperature": 0.0
    }
    req = urllib.request.Request(QWEN, data=json.dumps(payload).encode(),
                                  headers={"Content-Type":"application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=600).read())
    txt = r['choices'][0]['message']['content'].strip()
    if txt.startswith('```'): txt = txt.strip('`').lstrip('json').strip()
    try: return json.loads(txt)
    except Exception: return {"_raw": txt, "overall": 0, "ready_for_3d": False}


def project_to_blender(vision_json, body_name='Alice_Base_Body'):
    """Roda BVH project no Blender via bridge."""
    script = f"""
import sys, importlib
sys.path.insert(0, r'{LIVE}')
import project_vision_to_mesh
importlib.reload(project_vision_to_mesh)
r = project_vision_to_mesh.project_vision_coordinates_to_mesh('{body_name}', r'{vision_json}')
print('CREATED:', r)
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script); p = f.name
    try:
        env = os.environ.copy(); env['PYTHONIOENCODING'] = 'utf-8'
        r = subprocess.run([sys.executable, BRIDGE, '--file', p],
                            capture_output=True, text=True, timeout=300, env=env)
        sys.stdout.write(r.stdout)
        if r.returncode: sys.stderr.write(r.stderr)
        return r.returncode == 0
    finally:
        try: os.unlink(p)
        except: pass


def trace_one(step_image, prompt, label):
    """Florence2 + cv2 -> curves."""
    import vision_to_trace as vt
    mask = vt.florence_mask(step_image, prompt, label)
    if not mask: return None
    curves = vt.trace_contours(mask, max_curves=4, min_points=12, simplify_eps=0.003)
    for c in curves: c['label'] = f"{label}_{c['label']}"
    out_json = os.path.join(TRACE_DIR, f"{label}.json")
    json.dump({"_source_image": step_image, "_florence_prompt": prompt,
               "_mask": mask, "curves": curves},
              open(out_json,'w',encoding='utf-8'), indent=2, ensure_ascii=False)
    return out_json


def gated_pipeline_one(cfg, manifest, piece, fl_prompts):
    """Pipeline 1 peca: trace -> preview -> Qwen gate -> Blender SO se aprovado."""
    name = piece['name']
    print(f"\n========== {name} ==========")
    # Resolve refs
    steps = sorted(glob.glob(os.path.join(cfg['refs_dir'], cfg['step_images_pattern'])))
    try: idx = int(str(piece.get('ref_img','img1')).replace('img','').split('/')[0]) - 1
    except: idx = 0
    idx = max(0, min(idx, len(steps)-1))
    step = steps[idx]
    base_prompt = fl_prompts.get(name, piece.get('shape',name))
    body_sil = os.path.join(SIM_DIR, "body_SIM_FRONT.png")
    if not os.path.exists(body_sil):
        print(f"  [ERR] body silhouette missing: {body_sil}"); return False
    ref_crop = os.path.join(FL_MASKS, f"{name}_crop.png")
    if not os.path.exists(ref_crop):
        # Try alternate naming
        alt = os.path.join(FL_MASKS, f"{name}.png")
        if os.path.exists(alt): ref_crop = alt
        else: print(f"  [WARN] sem ref_crop, prosseguindo sem Qwen validation"); ref_crop = None

    # Try multiple Florence prompts
    prompts_try = [base_prompt, piece.get('shape', name), f"{name} on mannequin"]
    for attempt, prompt in enumerate(prompts_try[:MAX_TRACE_ATTEMPTS], 1):
        print(f"  [trace attempt {attempt}/{MAX_TRACE_ATTEMPTS}] prompt='{prompt}'")
        trace_json = trace_one(step, prompt, name)
        if not trace_json: continue
        data = json.load(open(trace_json, encoding='utf-8'))
        if not data.get('curves'):
            print(f"    no curves"); continue
        print(f"    {len(data['curves'])} curves")
        preview = os.path.join(PREVIEW_DIR, f"{name}_preview.png")
        render_trace_preview(trace_json, body_sil, preview)
        # Qwen gate
        if ref_crop:
            print(f"  [qwen gate]...")
            t0 = time.time()
            q = qwen_validate_trace(preview, ref_crop, name)
            print(f"    [{time.time()-t0:.0f}s] {q}")
            if q.get('overall', 0) >= MIN_SCORE and q.get('ready_for_3d'):
                # APPROVED -> save + project Blender
                ap = os.path.join(APPROVED_DIR, f"{name}.json")
                json.dump({"piece": name, "trace_json": trace_json,
                           "qwen": q, "preview": preview, "approved": True},
                          open(ap,'w',encoding='utf-8'), indent=2, ensure_ascii=False)
                print(f"  APPROVED score={q['overall']} -> projetando Blender...")
                ok = project_to_blender(trace_json)
                return ok
            else:
                print(f"  REJECTED score={q.get('overall')} reason={q.get('reason','?')}")
        else:
            print(f"  [no ref_crop - auto-approve trace] projetando...")
            ok = project_to_blender(trace_json)
            return ok
    # All attempts failed
    print(f"  [FAIL] {MAX_TRACE_ATTEMPTS} tentativas sem aprovacao Qwen")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--outfit', default='chapeleiro')
    ap.add_argument('--piece', default=None)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--from-piece', default=None, help='resume from this piece name')
    a = ap.parse_args()

    reg = json.load(open(REGISTRY, encoding='utf-8'))
    cfg = reg['outfits'][a.outfit]
    m = json.load(open(os.path.join(MANIFESTS, cfg['manifest']), encoding='utf-8'))
    fl_prompts = {p['name']: p['florence2_prompt'] for p in m.get('florence2_prompts_per_piece',[])}

    if a.piece:
        p = next((x for x in m['pieces'] if x['name']==a.piece), None)
        if not p: print(f"ERR piece {a.piece} not in manifest"); sys.exit(1)
        ok = gated_pipeline_one(cfg, m, p, fl_prompts)
        sys.exit(0 if ok else 1)

    if a.all:
        ok_list, fail_list = [], []
        started = a.from_piece is None
        for p in sorted(m['pieces'], key=lambda x: x['order']):
            if not started:
                if p['name'] == a.from_piece: started = True
                else: continue
            ok = gated_pipeline_one(cfg, m, p, fl_prompts)
            (ok_list if ok else fail_list).append(p['name'])
        print(f"\n===== REPORT =====\nAPPROVED+BUILT: {len(ok_list)} | REJECTED: {len(fail_list)}")
        for n in ok_list: print(f"  + {n}")
        for n in fail_list: print(f"  - {n}")
        return
    ap.error('precisa --piece or --all')


if __name__ == '__main__':
    main()
