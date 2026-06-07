# -*- coding: utf-8 -*-
"""Discovery automatica: Qwen3-VL analisa as 10 step images de um outfit
e gera manifest com lista de pecas detectadas (ordem, name, level, bone_anchor,
z range, color_hex, ref_img, shape, rigidity).

Cada step image mostra UMA peca isolada flutuante numa pose neutra. Qwen
identifica: que peca eh, onde no corpo, cor dominante, rigid vs cloth.

Uso:
  python pipeline_outfit_discovery.py --outfit cheshire
  python pipeline_outfit_discovery.py --outfit coelho
  python pipeline_outfit_discovery.py --outfit lagarta
  python pipeline_outfit_discovery.py --outfit rainha
  python pipeline_outfit_discovery.py --outfit base

Output: work/manifests/<outfit>.json
"""
import os, sys, json, base64, urllib.request, glob, argparse, time

QWEN = os.environ.get("QWEN_URL", "http://127.0.0.1:8080/v1/chat/completions")
REGISTRY = r"D:/Alice/tools/auto-rig-fix/work/manifests/outfits_registry.json"
MANIFESTS_DIR = r"D:/Alice/tools/auto-rig-fix/work/manifests"

PALETTE_TEMPLATE = {
    "verde_teal_principal": "#2D4438",
    "creme_underdress": "#C9B68F",
    "preto_lace": "#0E0D0C",
    "couro_bota_preto": "#1A1612",
    "ouro_metais": "#9A7A2E",
    "branco_chemise_interna": "#E5DCC5"
}

VALID_LEVELS = ["TECIDO_BASE", "SOBREPOSICAO", "COMPRESSAO", "METALS_PROPS"]
VALID_BONES = [
    "mixamorig:Hips", "mixamorig:Spine", "mixamorig:Spine1", "mixamorig:Spine2",
    "mixamorig:Neck", "mixamorig:Head",
    "mixamorig:LeftLeg", "mixamorig:RightLeg",
    "mixamorig:LeftFoot", "mixamorig:RightFoot",
    "mixamorig:LeftArm", "mixamorig:RightArm",
    "mixamorig:LeftForeArm", "mixamorig:RightForeArm",
    "mixamorig:LeftHand", "mixamorig:RightHand"
]
VALID_RIGIDITY = ["soft_cloth", "tight_cling", "rigid"]

def b64(p):
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode()


def ask_qwen_for_piece(turnaround_b64, step_b64, step_num, outfit_name):
    prompt = f'''You are a 3D character TA analyzing an Alice character outfit step-by-step.
Image 1: Alice turnaround for outfit "{outfit_name}".
Image 2: step image #{step_num} showing ONE isolated piece floating against background.

Identify the piece shown in step #{step_num}. Return STRICT JSON:
{{
  "name": "snake_case_id_no_spaces",
  "level": "TECIDO_BASE|SOBREPOSICAO|COMPRESSAO|METALS_PROPS",
  "bone_anchor": "mixamorig:<bone>",
  "z_bottom_m": 0.00,
  "z_top_m": 1.80,
  "color_hex": "#RRGGBB",
  "shape": "1-2 word shape (e.g. saia A-line, bota cano alto, espartilho)",
  "rigidity": "soft_cloth|tight_cling|rigid",
  "is_paired_LR": true|false,
  "estimated_pieces_count_if_pair": 1
}}

Rules:
- TECIDO_BASE = underwear/inner
- SOBREPOSICAO = outer cloth layers (saias, vestidos, mangas)
- COMPRESSAO = tight fit (corpete, sash)
- METALS_PROPS = hard accessories (bota, luva, chapeu, joia, arma)
- Alice height ~1.70m. Hips ~0.90m. Chest ~1.30m. Neck ~1.45m. Head top ~1.80m.

Reply ONLY the JSON, no prose, no fence.'''
    payload = {
        "model": "qwen3-vl",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{turnaround_b64}"}},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{step_b64}"}},
                {"type": "text", "text": prompt}
            ]
        }],
        "max_tokens": 320, "temperature": 0.0
    }
    req = urllib.request.Request(QWEN, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=180).read())
    txt = r["choices"][0]["message"]["content"].strip()
    if txt.startswith("```"):
        txt = txt.strip("`").lstrip("json").strip()
    return json.loads(txt)


def load_registry():
    with open(REGISTRY, encoding='utf-8') as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--outfit', required=True,
                    choices=['chapeleiro','base','cheshire','coelho','lagarta','rainha'])
    ap.add_argument('--force', action='store_true', help='sobrescreve manifest existente')
    args = ap.parse_args()

    reg = load_registry()
    cfg = reg['outfits'][args.outfit]
    refs_dir = cfg['refs_dir']
    pattern = cfg['step_images_pattern']
    manifest_path = os.path.join(MANIFESTS_DIR, cfg['manifest'])

    if os.path.exists(manifest_path) and not args.force:
        print(f"manifest existe: {manifest_path} (use --force pra sobrescrever)")
        return 0

    turnaround_path = (os.path.join(refs_dir, cfg['turnaround'])
                       if cfg.get('turnaround') else os.path.join(refs_dir, cfg['alice_base_ref']))
    if not os.path.exists(turnaround_path):
        print(f"ERRO: turnaround nao existe: {turnaround_path}")
        return 1

    steps = sorted(glob.glob(os.path.join(refs_dir, pattern)))
    print(f"[{args.outfit}] {len(steps)} step images encontradas")
    if not steps:
        print(f"  ERRO: nenhuma step image em {refs_dir} pattern={pattern}")
        return 1

    t_b64 = b64(turnaround_path)
    pieces = []
    order = 1

    for i, step_path in enumerate(steps, 1):
        s_b64 = b64(step_path)
        t0 = time.time()
        print(f"  [{i:02d}/{len(steps)}] {os.path.basename(step_path)} ... ", end="", flush=True)
        try:
            r = ask_qwen_for_piece(t_b64, s_b64, i, cfg['display_name'])
            level = r.get('level', 'SOBREPOSICAO')
            if level not in VALID_LEVELS: level = 'SOBREPOSICAO'
            bone = r.get('bone_anchor', 'mixamorig:Hips')
            if bone not in VALID_BONES: bone = 'mixamorig:Hips'
            rigidity = r.get('rigidity', 'soft_cloth')
            if rigidity not in VALID_RIGIDITY: rigidity = 'soft_cloth'

            base_name = r.get('name', f'piece_{i:02d}')
            if r.get('is_paired_LR'):
                for side, suffix in [('esq', '_esq'), ('dir', '_dir')]:
                    pieces.append({
                        "order": order, "name": base_name + suffix,
                        "level": level, "bone_anchor": bone.replace("Left", side.capitalize().replace("Esq","Left").replace("Dir","Right")).replace("Right", "Right" if side=="dir" else "Left"),
                        "z": [r.get('z_bottom_m', 0.0), r.get('z_top_m', 1.0)],
                        "color_hex": r.get('color_hex', '#888888'),
                        "ref_img": f"img{i}",
                        "shape": r.get('shape', 'unknown'),
                        "rigidity": rigidity
                    })
                    order += 1
            else:
                pieces.append({
                    "order": order, "name": base_name,
                    "level": level, "bone_anchor": bone,
                    "z": [r.get('z_bottom_m', 0.0), r.get('z_top_m', 1.0)],
                    "color_hex": r.get('color_hex', '#888888'),
                    "ref_img": f"img{i}",
                    "shape": r.get('shape', 'unknown'),
                    "rigidity": rigidity
                })
                order += 1
            print(f"{time.time()-t0:.0f}s OK -> {base_name} ({level})")
        except Exception as e:
            print(f"ERR {e}")

    manifest = {
        "_doc": f"Manifest auto-discovered via Qwen3-VL pra {args.outfit}. {len(pieces)} pecas detectadas.",
        "_turnaround_ref": turnaround_path,
        "_costureira_refs_dir": refs_dir + "/",
        "_body_template": "D:/Alice/tools/auto-rig-fix/work/alice_rigged.fbx",
        "_alice_height_m": 1.70,
        "_palette_global": PALETTE_TEMPLATE,
        "_outfit_id": args.outfit,
        "_weapon": cfg.get('weapon'),
        "pieces": pieces,
        "florence2_prompts_per_piece": [
            {"name": p['name'], "florence2_prompt": p['shape']}
            for p in pieces
        ]
    }
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"\nMANIFEST SALVO: {manifest_path} ({len(pieces)} pecas)")
    return 0

if __name__ == "__main__":
    sys.exit(main() or 0)
