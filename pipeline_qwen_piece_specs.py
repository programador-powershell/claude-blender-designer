# -*- coding: utf-8 -*-
"""Qwen3-VL itera N pecas do manifest do outfit + gera JSON spec por peca.
Pra cada peca: le turnaround + step image ref da peca, pergunta cor RGB, bbox,
shape, z_world, wraps_360, paired_LR, florence2_prompt_refined.

Outfits suportados: chapeleiro, base, cheshire, coelho, lagarta, rainha.
Registry: work/manifests/outfits_registry.json.

Uso:
  python pipeline_qwen_piece_specs.py --outfit chapeleiro
  python pipeline_qwen_piece_specs.py --outfit cheshire
"""
import os, sys, json, base64, urllib.request, time, glob, argparse

QWEN = os.environ.get("QWEN_URL", "http://127.0.0.1:8080/v1/chat/completions")
REGISTRY = r"D:/Alice/tools/auto-rig-fix/work/manifests/outfits_registry.json"
MANIFESTS_DIR = r"D:/Alice/tools/auto-rig-fix/work/manifests"
OUT_BASE = r"D:/Alice/tools/auto-rig-fix/work/qwen_specs"


def b64(p):
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode()


def ask(piece, turnaround_b64, ref_b64):
    prompt = f'''You are a 3D character TA. Two reference images attached.
Image 1: Alice turnaround.
Image 2: step image showing piece isolated.

Piece: "{piece['name']}" (description: {piece.get('shape','')}).

Return STRICT JSON with these keys:
  "color_dominant_rgb": [r,g,b],
  "color_secondary_rgb": [r,g,b],
  "bbox_turnaround_front_norm": [x0,y0,x1,y1],
  "shape_keywords": [str,str,str],
  "estimated_z_world_m": [z_bottom, z_top],
  "wraps_360": true|false,
  "is_paired_LR": true|false,
  "florence2_prompt_refined": "concise phrase for Florence2 segmentation"

Reply ONLY the JSON. No prose, no markdown fence.'''
    payload = {
        "model": "qwen3-vl",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{turnaround_b64}"}},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{ref_b64}"}},
                {"type": "text", "text": prompt}
            ]
        }],
        "max_tokens": 400, "temperature": 0.0
    }
    req = urllib.request.Request(QWEN, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=180).read())
    txt = r["choices"][0]["message"]["content"].strip()
    if txt.startswith("```"):
        txt = txt.strip("`").lstrip("json").strip()
    try:
        return json.loads(txt)
    except Exception as e:
        return {"_err": str(e), "_raw": txt}


def load_registry():
    with open(REGISTRY, encoding='utf-8') as f:
        return json.load(f)


def resolve_step_image_for_piece(refs_dir, pattern, ref_img_key):
    """ref_img_key e.g. 'img1' -> mapeia pra Nth step image."""
    steps = sorted(glob.glob(os.path.join(refs_dir, pattern)))
    if not steps:
        return None
    try:
        idx = int(str(ref_img_key).replace('img', '').split('/')[0]) - 1
        idx = max(0, min(idx, len(steps) - 1))
        return steps[idx]
    except Exception:
        return steps[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--outfit', required=True,
                    choices=['chapeleiro','base','cheshire','coelho','lagarta','rainha'])
    args = ap.parse_args()

    reg = load_registry()
    cfg = reg['outfits'][args.outfit]
    refs_dir = cfg['refs_dir']
    pattern = cfg['step_images_pattern']
    manifest_path = os.path.join(MANIFESTS_DIR, cfg['manifest'])
    turnaround_path = (os.path.join(refs_dir, cfg['turnaround'])
                       if cfg.get('turnaround') else os.path.join(refs_dir, cfg['alice_base_ref']))

    if not os.path.exists(manifest_path):
        print(f"ERRO: manifest nao existe: {manifest_path}")
        print(f"  Rode discover_outfit_pieces.py --outfit {args.outfit} primeiro.")
        return 1

    out_dir = os.path.join(OUT_BASE, args.outfit)
    os.makedirs(out_dir, exist_ok=True)

    with open(manifest_path, encoding='utf-8') as f:
        m = json.load(f)
    pieces = m['pieces']
    t_b64 = b64(turnaround_path)

    print(f"[{args.outfit}] {len(pieces)} pecas. refs={refs_dir}")
    for p in pieces:
        out = os.path.join(out_dir, f"piece_{p['order']:02d}_{p['name']}_spec.json")
        if os.path.exists(out):
            print(f"  SKIP {p['name']} (existe)")
            continue
        ref_key = p.get('ref_img', 'img1')
        ref_path = resolve_step_image_for_piece(refs_dir, pattern, ref_key)
        if not ref_path or not os.path.exists(ref_path):
            print(f"  REF AUSENTE {p['name']} -> usando turnaround")
            ref_path = turnaround_path
        r_b64 = b64(ref_path)
        t0 = time.time()
        print(f"  [{p['order']:02d}] {p['name']} ... ", end="", flush=True)
        try:
            spec = ask(p, t_b64, r_b64)
            spec['_manifest_entry'] = p
            spec['_outfit'] = args.outfit
            with open(out, 'w', encoding='utf-8') as f:
                json.dump(spec, f, indent=2, ensure_ascii=False)
            print(f"{time.time()-t0:.0f}s OK")
        except Exception as e:
            print(f"ERR {e}")

if __name__ == "__main__":
    sys.exit(main() or 0)
