# -*- coding: utf-8 -*-
"""Head-to-head VLM: gemma (llama.cpp) vs qwen3-vl (ollama) fazendo JSON do render.
Mesma imagem, mesmo prompt JSON-only. Mede: JSON valido? latencia. Salva raw p/ auditar.
Roda no python do ComfyUI (tem PIL)."""
import os, sys, json, time, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vision_ask as VA

BASE = r"D:\References\img\Model 3D\BASE"
OUT  = r"D:\Alice\tools\auto-rig-fix\work\vlm_compare.json"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

PROMPT = (
    "You are a 3D render auditor. Output ONLY a JSON object (no markdown, no prose) with EXACTLY these keys: "
    '"character" (string), "hair" (string), "outfit_colors" (array of strings), '
    '"outfit_style" (string), "key_props" (array of strings), "pose" (string), '
    '"view" (one of: "single","turnaround"), "notable_flaws" (array of strings). '
    "Base every value strictly on what is visible in the image."
)

def extract_json(s):
    if not s: return None, "empty"
    t = s.strip()
    if "```" in t:
        # pega bloco entre fences
        parts = t.split("```")
        for p in parts:
            p2 = p.strip()
            if p2.startswith("json"): p2 = p2[4:].strip()
            if p2.startswith("{"): t = p2; break
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b < 0 or b <= a: return None, "no-braces"
    frag = t[a:b+1]
    try:
        return json.loads(frag), "ok"
    except Exception as e:
        return None, f"parse-fail:{e}"

REQUIRED = {"character","hair","outfit_colors","outfit_style","key_props","pose","view","notable_flaws"}

def run(backend, img):
    t = time.time()
    try:
        raw = VA.ask(img, PROMPT, num_predict=400, backend=backend)
        err = None
    except Exception as e:
        raw, err = "", f"call-fail:{e}"
    dt = time.time() - t
    obj, status = extract_json(raw)
    keys_ok = bool(obj) and REQUIRED.issubset(set(obj.keys()))
    return {"backend": backend, "latency": round(dt,1), "valid_json": obj is not None,
            "keys_complete": keys_ok, "status": status, "raw": raw, "json": obj}

imgs = sorted(glob.glob(os.path.join(BASE, "*.jpg")))
results = {}
print(f"{'image':<14}{'backend':<8}{'lat':>6} {'json':>5} {'keys':>5}  status")
for img in imgs:
    name = os.path.basename(img)
    results[name] = {}
    for bk in ("llama", "ollama"):
        r = run(bk, img)
        results[name][bk] = r
        print(f"{name:<14}{bk:<8}{r['latency']:>6} {str(r['valid_json']):>5} {str(r['keys_complete']):>5}  {r['status']}")

json.dump(results, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
# sumario
def score(bk):
    rs = [results[n][bk] for n in results]
    return sum(r["valid_json"] for r in rs), sum(r["keys_complete"] for r in rs), round(sum(r["latency"] for r in rs)/len(rs),1)
for bk,label in (("llama","GEMMA"),("ollama","QWEN ")):
    vj,kc,al = score(bk)
    print(f"== {label}: json_valido {vj}/{len(results)}  keys_completas {kc}/{len(results)}  lat_media {al}s")
print("SAVED", OUT)
