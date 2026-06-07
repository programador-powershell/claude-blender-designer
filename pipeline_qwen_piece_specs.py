# -*- coding: utf-8 -*-
"""Qwen3-VL itera 22 pecas do manifest + gera JSON spec por peca.
Pra cada peca: lê alice-chapeleiro.png (turnaround) + costureira img source,
pergunta cor RGB, bbox no turnaround, posicao relativa (z_top z_bot do corpo),
shape detalhe. Salva piece_<NN>_<name>_spec.json em work/qwen_specs/.

Usa apenas Qwen — sem olho Claude. Output consumido pelo orchestrator Florence2."""
import os, sys, json, base64, urllib.request, time

QWEN = os.environ.get("QWEN_URL", "http://127.0.0.1:8080/v1/chat/completions")
MANIFEST = r"D:/Alice/tools/auto-rig-fix/work/alice_chapeleiro_manifest.json"
REFS_DIR = r"C:/Users/pslo9/Downloads/Alice chapeleiro"
TURNAROUND = os.path.join(REFS_DIR, "alice-chapeleiro.png")
OUT_DIR = r"D:/Alice/tools/auto-rig-fix/work/qwen_specs"

REF_MAP = {
    "img1": "ChatGPT Image 7 de jun. de 2026, 11_05_53 (1).png",
    "img2": "ChatGPT Image 7 de jun. de 2026, 11_05_53 (2).png",
    "img3": "ChatGPT Image 7 de jun. de 2026, 11_05_53 (3).png",
    "img4": "ChatGPT Image 7 de jun. de 2026, 11_05_53 (4).png",
    "img5": "ChatGPT Image 7 de jun. de 2026, 11_05_54 (5).png",
    "img6": "ChatGPT Image 7 de jun. de 2026, 11_05_54 (6).png",
    "img7": "ChatGPT Image 7 de jun. de 2026, 11_05_54 (7).png",
    "img8": "ChatGPT Image 7 de jun. de 2026, 11_05_55 (8).png",
    "img9": "ChatGPT Image 7 de jun. de 2026, 11_05_55 (9).png",
    "img10": "ChatGPT Image 7 de jun. de 2026, 11_05_56 (10).png",
}

def b64(p):
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode()

def ask(piece, turnaround_b64, ref_b64):
    prompt = f'''You are a 3D character TA. Two reference images attached.
Image 1: Alice Chapeleiro 3-view turnaround (front/side/back).
Image 2: "costureira" breakdown showing the isolated piece.

Analyze the piece named: "{piece['name']}" (description: {piece['shape']}).

Return STRICT JSON with these keys:
  "color_dominant_rgb": [r,g,b],  // 0-255 main color
  "color_secondary_rgb": [r,g,b],
  "bbox_turnaround_front_norm": [x0,y0,x1,y1],  // 0..1 fractions within turnaround front view
  "shape_keywords": [str,str,str],  // 3-5 short tags
  "estimated_z_world_m": [z_bottom, z_top],  // alice height = 1.70m
  "wraps_360": true|false,  // does piece wrap around body 360deg?
  "is_paired_LR": true|false,  // is there a left+right pair?
  "florence2_prompt_refined": "concise phrase for Florence2 referring expression segmentation"

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
    try: return json.loads(txt)
    except Exception as e: return {"_err": str(e), "_raw": txt}

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(MANIFEST) as f: m = json.load(f)
    pieces = m["pieces"]
    t_b64 = b64(TURNAROUND)
    for p in pieces:
        out = os.path.join(OUT_DIR, f"piece_{p['order']:02d}_{p['name']}_spec.json")
        if os.path.exists(out):
            print(f"SKIP {p['name']} (existe)")
            continue
        ref_key = p["ref_img"].split("/")[0]
        ref_path = os.path.join(REFS_DIR, REF_MAP.get(ref_key, REF_MAP["img10"]))
        if not os.path.exists(ref_path):
            print(f"REF AUSENTE {ref_key} -> usando img10"); ref_path = os.path.join(REFS_DIR, REF_MAP["img10"])
        r_b64 = b64(ref_path)
        t0 = time.time()
        print(f"[{p['order']:02d}] {p['name']} ... ", end="", flush=True)
        try:
            spec = ask(p, t_b64, r_b64)
            spec["_manifest_entry"] = p
            with open(out, "w", encoding="utf-8") as f:
                json.dump(spec, f, indent=2, ensure_ascii=False)
            print(f"{time.time()-t0:.0f}s OK")
        except Exception as e:
            print(f"ERR {e}")

if __name__ == "__main__":
    main()
