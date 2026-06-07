# -*- coding: utf-8 -*-
"""Pipeline vision-BVH: pra cada peca manifest:
1. Florence2 mask na step image -> cv2 contour -> JSON curves (u,v normalizado)
2. Blender: project_vision_coordinates_to_mesh -> mesh anatomico colado no body via BVH raycast
3. Stack Shrinkwrap + Solidify + Subsurf

Resultado: roupa moldada na anatomia exata do corpo, no na ellipse mockup.
"""
import os, sys, json, glob, subprocess, tempfile, argparse

ROOT = r"D:/Alice/tools/auto-rig-fix"
LIVE = os.path.join(ROOT, "live")
WORK = os.path.join(ROOT, "work")
BRIDGE = os.path.join(ROOT, "bridge_cmd.py")
REGISTRY = os.path.join(WORK, "manifests", "outfits_registry.json")
MANIFESTS = os.path.join(WORK, "manifests")
TRACE_DIR = os.path.join(WORK, "trace")
os.makedirs(TRACE_DIR, exist_ok=True)
sys.path.insert(0, LIVE)


def trace_one(ref_image, prompt, out_json, label):
    """Roda vision_to_trace.py: Florence2 + cv2 -> curves JSON."""
    import vision_to_trace as vt
    mask = vt.florence_mask(ref_image, prompt, label)
    if not mask: return None
    curves = vt.trace_contours(mask)
    for c in curves: c['label'] = f"{label}_{c['label']}"
    data = {"_source_image": ref_image, "_florence_prompt": prompt,
            "_mask": mask, "curves": curves}
    json.dump(data, open(out_json,'w',encoding='utf-8'), indent=2, ensure_ascii=False)
    print(f"  [trace] {len(curves)} curves -> {out_json}")
    return out_json


def project_blender(vision_json, body_name='Alice_Base_Body'):
    """Roda projection no Blender via bridge."""
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


def run_piece(outfit_cfg, manifest, piece, fl_prompts):
    name = piece['name']
    out_json = os.path.join(TRACE_DIR, f"{name}.json")
    if os.path.exists(out_json):
        print(f"[SKIP trace] {name} (cached)")
    else:
        # Resolve step image
        steps = sorted(glob.glob(os.path.join(outfit_cfg['refs_dir'], outfit_cfg['step_images_pattern'])))
        if not steps: print(f"  [ERR] sem steps"); return False
        try: idx = int(str(piece.get('ref_img','img1')).replace('img','').split('/')[0]) - 1
        except: idx = 0
        idx = max(0, min(idx, len(steps)-1))
        step = steps[idx]
        prompt = fl_prompts.get(name, piece.get('shape',name))
        print(f"\n[trace] {name} <- {os.path.basename(step)} prompt='{prompt}'")
        ok = trace_one(step, prompt, out_json, name)
        if not ok: return False
    # Project no Blender
    print(f"[project] {name}")
    return project_blender(out_json)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--outfit', default='chapeleiro')
    ap.add_argument('--piece', default=None)
    ap.add_argument('--all', action='store_true')
    a = ap.parse_args()

    reg = json.load(open(REGISTRY, encoding='utf-8'))
    cfg = reg['outfits'][a.outfit]
    m = json.load(open(os.path.join(MANIFESTS, cfg['manifest']), encoding='utf-8'))
    fl_prompts = {p['name']: p['florence2_prompt'] for p in m.get('florence2_prompts_per_piece',[])}

    if a.piece:
        p = next((x for x in m['pieces'] if x['name']==a.piece), None)
        if not p: print(f"ERR piece {a.piece} not in manifest"); sys.exit(1)
        ok = run_piece(cfg, m, p, fl_prompts)
        sys.exit(0 if ok else 1)

    if a.all:
        ok_list, fail_list = [], []
        for p in sorted(m['pieces'], key=lambda x: x['order']):
            print(f"\n========== PIECE {p['order']:02d} {p['name']} ==========")
            ok = run_piece(cfg, m, p, fl_prompts)
            (ok_list if ok else fail_list).append(p['name'])
        print(f"\n===== REPORT =====\nOK: {len(ok_list)} | FAIL: {len(fail_list)}")
        for n in ok_list: print(f"  + {n}")
        for n in fail_list: print(f"  - {n}")
        return
    ap.error('precisa --piece or --all')


if __name__ == '__main__':
    main()
