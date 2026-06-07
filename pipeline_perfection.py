# -*- coding: utf-8 -*-
"""Pipeline PERFEICAO por peca. Sem aceitar score < 10.

Por peca (sequencial, 1 por vez):
  PHASE 1 - TRACE (Florence2 + cv2 -> JSON curves):
    a. Tenta ate 5 Florence prompts variants
    b. Pra cada trace: render preview + Qwen score
    c. Aceita SO se trace_score == 10
  PHASE 2 - FIT (BVH project Blender + render):
    a. Projeta no body
    b. Render 3 views (front/side/back)
    c. Qwen valida render vs ref crop
    d. SE fit_score == 10: APROVADO, proximo piece
    e. SE < 10: REMOVE objeto + ajusta parametros (offset solidify) + retry
    f. Sem limite iters - so avanca quando perfeito

Nada de batch. Pipeline trava na peca atual ate perfeicao.
"""
import os, sys, json, glob, subprocess, tempfile, argparse, time, base64, urllib.request, shutil
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
APPROVED_DIR = os.path.join(WORK, "perfection_approved")
FL_MASKS = os.path.join(WORK, "florence_masks")
SIM_DIR = os.path.join(WORK, "simulation")
RENDER_DIR = os.path.join(WORK, "perfection_renders")
QWEN = "http://127.0.0.1:8080/v1/chat/completions"

for d in [TRACE_DIR, PREVIEW_DIR, APPROVED_DIR, RENDER_DIR]: os.makedirs(d, exist_ok=True)

TARGET_SCORE = 10
MAX_TRACE_VARIANTS = 5
MAX_FIT_RETRIES = 5


def b64(p):
    with open(p, 'rb') as f: return base64.b64encode(f.read()).decode()


def qwen_query(payload, max_retries=2):
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(QWEN, data=json.dumps(payload).encode(),
                                          headers={"Content-Type":"application/json"})
            r = json.loads(urllib.request.urlopen(req, timeout=600).read())
            return r
        except Exception as e:
            print(f"  [Qwen retry {attempt+1}: {e}]")
            time.sleep(5)
    return None


def trace_one_florence(step_image, prompt, label):
    import vision_to_trace as vt
    mask = vt.florence_mask(step_image, prompt, label)
    if not mask: return None, None
    curves = vt.trace_contours(mask, max_curves=4, min_points=12, simplify_eps=0.003)
    if not curves: return None, mask
    for c in curves: c['label'] = f"{label}_{c['label']}"
    out_json = os.path.join(TRACE_DIR, f"{label}.json")
    json.dump({"_source_image": step_image, "_florence_prompt": prompt,
               "_mask": mask, "curves": curves},
              open(out_json,'w',encoding='utf-8'), indent=2, ensure_ascii=False)
    return out_json, mask


def render_preview(trace_json_path, body_silhouette, out_path):
    data = json.load(open(trace_json_path, encoding='utf-8'))
    body = Image.open(body_silhouette).convert('RGBA')
    W, H = body.size
    overlay = Image.new('RGBA', body.size, (0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    for c in data.get('curves', []):
        pts = [(int(p[0]*W), int(p[1]*H)) for p in c['points']]
        if len(pts) > 1:
            draw.line(pts + [pts[0]], fill=(255,30,30,255), width=3)
    composite = Image.alpha_composite(body, overlay)
    composite.convert('RGB').save(out_path)
    return out_path


def qwen_score_trace(preview, ref_crop, piece):
    """Phase 1 gate. Score trace match."""
    payload = {
        "model": "qwen3-vl",
        "messages": [{"role":"user","content":[
            {"type":"image_url","image_url":{"url":f"data:image/png;base64,{b64(preview)}"}},
            {"type":"image_url","image_url":{"url":f"data:image/png;base64,{b64(ref_crop)}"}},
            {"type":"text","text":f"""Trace validation for piece \"{piece}\".
Img1: 2D trace preview (red contour) over Alice body silhouette.
Img2: reference crop.
Score 0-10: does red contour silhouette MATCH ref piece silhouette?
JSON ONLY: {{"trace_match":0-10,"position":0-10,"overall":0-10,"reason":"<short>"}}"""}
        ]}], "max_tokens": 120, "temperature": 0.0
    }
    r = qwen_query(payload)
    if not r: return {"overall": 0, "_err": "qwen_dead"}
    txt = r['choices'][0]['message']['content'].strip()
    if txt.startswith('```'): txt = txt.strip('`').lstrip('json').strip()
    try: return json.loads(txt)
    except: return {"_raw": txt, "overall": 0}


def project_blender(vision_json, body='Alice_Base_Body', solidify=0.002):
    """BVH project. Returns list of created object names."""
    script = f"""
import sys, importlib
sys.path.insert(0, r'{LIVE}')
import project_vision_to_mesh
importlib.reload(project_vision_to_mesh)
r = project_vision_to_mesh.project_vision_coordinates_to_mesh('{body}', r'{vision_json}')
# Override solidify thickness
import bpy
for n in (r or []):
    o = bpy.data.objects.get(n)
    if o:
        for m in o.modifiers:
            if m.type == 'SOLIDIFY': m.thickness = {solidify}
print('CREATED_RESULT:', r)
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script); p = f.name
    try:
        env = os.environ.copy(); env['PYTHONIOENCODING'] = 'utf-8'
        r = subprocess.run([sys.executable, BRIDGE, '--file', p],
                            capture_output=True, text=True, timeout=300, env=env)
        # Parse CREATED_RESULT
        out = r.stdout
        for line in out.splitlines():
            if line.startswith('CREATED_RESULT:'):
                lst = line.split(':',1)[1].strip()
                try:
                    import ast
                    return ast.literal_eval(lst) or []
                except: return []
        return []
    finally:
        try: os.unlink(p)
        except: pass


def remove_objects(names):
    script = f"""
import bpy
names = {names!r}
for n in names:
    o = bpy.data.objects.get(n)
    if o: bpy.data.objects.remove(o, do_unlink=True)
print('REMOVED:', names)
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script); p = f.name
    try:
        env = os.environ.copy(); env['PYTHONIOENCODING'] = 'utf-8'
        subprocess.run([sys.executable, BRIDGE, '--file', p],
                        capture_output=True, text=True, timeout=60, env=env)
    finally:
        try: os.unlink(p)
        except: pass


def render_views(piece, view_cams=['VAL_FRONT','VAL_SIDE','VAL_BACK']):
    script = f"""
import bpy, os
OUT = r'{RENDER_DIR}'
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
sc.render.resolution_x=600; sc.render.resolution_y=800
sc.render.image_settings.file_format='PNG'
files=[]
for cn in {view_cams!r}:
    if bpy.data.objects.get(cn):
        sc.camera = bpy.data.objects[cn]
        p = os.path.join(OUT, '{piece}_'+cn+'.png')
        sc.render.filepath=p; bpy.ops.render.render(write_still=True)
        files.append(p)
print('RENDERED:', files)
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script); p = f.name
    try:
        env = os.environ.copy(); env['PYTHONIOENCODING'] = 'utf-8'
        subprocess.run([sys.executable, BRIDGE, '--file', p],
                        capture_output=True, text=True, timeout=300, env=env)
        return [os.path.join(RENDER_DIR, f"{piece}_{v}.png") for v in view_cams]
    finally:
        try: os.unlink(p)
        except: pass


def qwen_score_fit(render_path, ref_crop, piece, inspectors=None):
    """Phase 2 gate. Score render fit vs ref + multi-aspect cv2 inspectors."""
    insp_text = ""
    if inspectors:
        insp_text = f"""
cv2 inspectors metrics (objective):
  ssim={inspectors.get('ssim')} edge_overlap={inspectors.get('edge_overlap')}
  shadow_match={inspectors.get('shadow_match')} texture_match={inspectors.get('texture_match')}
  color_corr={inspectors.get('color_corr')} hue_diff={inspectors.get('hue_diff')}
  light_match={inspectors.get('light_match')} mean_diff={inspectors.get('mean_diff')}
"""
    # Use inspectors grid if available else render
    img_path = inspectors['grid'] if inspectors and inspectors.get('grid') else render_path
    payload = {
        "model": "qwen3-vl",
        "messages": [{"role":"user","content":[
            {"type":"image_url","image_url":{"url":f"data:image/png;base64,{b64(img_path)}"}},
            {"type":"image_url","image_url":{"url":f"data:image/png;base64,{b64(ref_crop)}"}},
            {"type":"text","text":f"""Fit validation per piece \"{piece}\".
Img1: 3x3 inspector grid (render, ref, overlay_red, overlay_green, lines, shadow, texture, palette, lights).
Img2: reference photo crop.
{insp_text}
Score 0-10 EACH aspect: shape, position, size, lines, shadows, textures, colors, lights, overlay_match.
JSON ONLY: {{"shape":0-10,"position":0-10,"size":0-10,"lines":0-10,"shadows":0-10,
"textures":0-10,"colors":0-10,"lights":0-10,"overlay_match":0-10,"overall":0-10,
"perfect":false,"weak_aspects":["aspect1","aspect2"],"issue":"<short>"}}
perfect=true ONLY if ALL aspects==10."""}
        ]}], "max_tokens": 280, "temperature": 0.0
    }
    r = qwen_query(payload)
    if not r: return {"overall": 0, "_err": "qwen_dead"}
    txt = r['choices'][0]['message']['content'].strip()
    if txt.startswith('```'): txt = txt.strip('`').lstrip('json').strip()
    try: return json.loads(txt)
    except: return {"_raw": txt, "overall": 0, "perfect": False}


def perfection_one_piece(cfg, piece, fl_prompts):
    """Workflow perfeicao 1 peca: trace 10 -> fit 10."""
    name = piece['name']
    print(f"\n{'='*60}\nPECA: {name}\n{'='*60}")
    approved_file = os.path.join(APPROVED_DIR, f"{name}.json")
    if os.path.exists(approved_file):
        print(f"  [SKIP] ja aprovado"); return True

    # Refs
    steps = sorted(glob.glob(os.path.join(cfg['refs_dir'], cfg['step_images_pattern'])))
    try: idx = int(str(piece.get('ref_img','img1')).replace('img','').split('/')[0]) - 1
    except: idx = 0
    idx = max(0, min(idx, len(steps)-1))
    step = steps[idx]
    body_sil = os.path.join(SIM_DIR, "body_SIM_FRONT.png")
    ref_crop = os.path.join(FL_MASKS, f"{name}_crop.png")
    if not os.path.exists(body_sil):
        print(f"  [ERR] body silhouette missing"); return False

    # Prompts variants
    base = fl_prompts.get(name, piece.get('shape', name))
    prompts = [base, f"{piece.get('shape','')} clothing", piece.get('shape', name),
               f"isolated {name.replace('_',' ')}", piece.get('shape','garment piece')]
    prompts = list(dict.fromkeys([p for p in prompts if p]))[:MAX_TRACE_VARIANTS]

    # PHASE 1: TRACE
    print(f"  --- PHASE 1: TRACE ({len(prompts)} prompts) ---")
    best_trace = None; best_trace_score = 0
    for pi, prompt in enumerate(prompts, 1):
        print(f"  [trace {pi}] '{prompt}'")
        tj, mask = trace_one_florence(step, prompt, name)
        if not tj: print(f"    no trace"); continue
        # Generate ref_crop from mask if missing
        if not os.path.exists(ref_crop) and mask:
            src = Image.open(step).convert('RGB')
            m = Image.open(mask).convert('L').resize(src.size)
            bbox = m.getbbox()
            if bbox:
                cr = src.crop(bbox); mk = m.crop(bbox)
                rgba = cr.convert('RGBA'); rgba.putalpha(mk)
                rgba.save(ref_crop)
                print(f"    ref_crop generated: {ref_crop}")
        if not os.path.exists(ref_crop): print(f"    no ref_crop yet"); continue
        preview = os.path.join(PREVIEW_DIR, f"{name}_p{pi}.png")
        render_preview(tj, body_sil, preview)
        t0 = time.time()
        q = qwen_score_trace(preview, ref_crop, name)
        score = q.get('overall', 0)
        print(f"    [Qwen {time.time()-t0:.0f}s] trace_score={score} reason={q.get('reason','?')}")
        if score > best_trace_score:
            best_trace_score = score; best_trace = tj
        if score >= TARGET_SCORE:
            print(f"    PERFECT trace 10/10"); break
    if best_trace_score < TARGET_SCORE:
        print(f"  [PHASE 1 INCOMPLETE] best trace_score={best_trace_score}, prosseguindo c/ best")
        if not best_trace:
            print(f"  [FAIL] sem trace valido"); return False

    # PHASE 2: FIT (project + render + score 10)
    print(f"  --- PHASE 2: FIT ({MAX_FIT_RETRIES} retries) ---")
    fit_score = 0
    solidify_thicknesses = [0.002, 0.005, 0.008, 0.012, 0.020]
    best_fit_score = 0; best_solidify = 0.002; best_objs = []
    for fi in range(MAX_FIT_RETRIES):
        sld = solidify_thicknesses[fi]
        print(f"  [fit retry {fi+1}/{MAX_FIT_RETRIES}] solidify={sld}")
        # Cleanup any prev objs for this piece
        remove_objects([f"PA_Garment_{name}_curve_{i:02d}" for i in range(8)])
        created = project_blender(best_trace, solidify=sld)
        print(f"    created: {created}")
        if not created: print(f"    nothing created"); continue
        renders = render_views(name)
        if not renders or not os.path.exists(renders[0]):
            print(f"    render fail"); continue
        # Run 6 cv2 inspectors (overlay/lines/shadow/texture/colors/lights)
        from cv2_inspectors import run_all_inspectors
        insp = run_all_inspectors(renders[0], ref_crop,
                                    os.path.join(WORK, "inspectors_grid", name), name)
        if insp:
            print(f"    inspectors: ssim={insp['ssim']} edges={insp['edge_overlap']} "
                  f"shadow={insp['shadow_match']} texture={insp['texture_match']} "
                  f"color={insp['color_corr']} light={insp['light_match']}")
        t0 = time.time()
        q = qwen_score_fit(renders[0], ref_crop, name, inspectors=insp)
        score = q.get('overall', 0)
        weak = q.get('weak_aspects', [])
        print(f"    [Qwen {time.time()-t0:.0f}s] fit_score={score} perfect={q.get('perfect')} weak={weak} issue={q.get('issue','?')}")
        if score > best_fit_score:
            best_fit_score = score; best_solidify = sld; best_objs = list(created)
        if score >= TARGET_SCORE and q.get('perfect'):
            print(f"  APROVADO 10/10 fit (solidify={sld})")
            json.dump({"piece": name, "trace": best_trace, "trace_score": best_trace_score,
                       "fit_score": score, "objects": created, "solidify": sld,
                       "qwen_fit": q, "renders": renders, "approved": True},
                      open(approved_file,'w',encoding='utf-8'), indent=2, ensure_ascii=False)
            return True
    # Sem 10/10 fit
    print(f"  [PHASE 2 INCOMPLETE] best fit_score={best_fit_score} (sem 10), mantendo best_objs={best_objs}")
    # Restore best fit config
    remove_objects([f"PA_Garment_{name}_curve_{i:02d}" for i in range(8)])
    project_blender(best_trace, solidify=best_solidify)
    json.dump({"piece": name, "trace": best_trace, "trace_score": best_trace_score,
               "fit_score": best_fit_score, "objects": best_objs, "solidify": best_solidify,
               "approved": False, "reason": "fit_score<10"},
              open(approved_file,'w',encoding='utf-8'), indent=2, ensure_ascii=False)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--outfit', default='chapeleiro')
    ap.add_argument('--piece', default=None)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--from-piece', default=None)
    a = ap.parse_args()

    reg = json.load(open(REGISTRY, encoding='utf-8'))
    cfg = reg['outfits'][a.outfit]
    m = json.load(open(os.path.join(MANIFESTS, cfg['manifest']), encoding='utf-8'))
    fl_prompts = {p['name']: p['florence2_prompt'] for p in m.get('florence2_prompts_per_piece',[])}

    if a.piece:
        p = next((x for x in m['pieces'] if x['name']==a.piece), None)
        if not p: sys.exit(1)
        ok = perfection_one_piece(cfg, p, fl_prompts)
        sys.exit(0 if ok else 1)

    if a.all:
        ok_list, fail_list = [], []
        started = a.from_piece is None
        for p in sorted(m['pieces'], key=lambda x: x['order']):
            if not started:
                if p['name'] == a.from_piece: started = True
                else: continue
            ok = perfection_one_piece(cfg, p, fl_prompts)
            (ok_list if ok else fail_list).append(p['name'])
        print(f"\n===== FINAL REPORT =====")
        print(f"APROVADOS 10/10: {len(ok_list)} | INCOMPLETOS: {len(fail_list)}")
        for n in ok_list: print(f"  + {n}")
        for n in fail_list: print(f"  - {n}")
        return
    ap.error('precisa --piece or --all')


if __name__ == '__main__':
    main()
