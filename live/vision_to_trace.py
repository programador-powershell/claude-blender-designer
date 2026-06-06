# -*- coding: utf-8 -*-
"""
vision_to_trace - Render image -> Qwen3-VL/Gemma vision -> JSON curves -> bump on mesh.
Bridges vision_ask.py output into game_builder.apply_vision_details_to_mesh().
"""
import json, os, sys, base64, urllib.request, io

LLAMA_URL = os.environ.get("LLAMA_URL", "http://127.0.0.1:8080/v1/chat/completions")

PROMPT_TRACE = (
    "Analyze this character art. Identify all decorative DETAIL contour lines "
    "(playing-card motifs, clock/watch, ribbons, bows, ruffles, stitching, "
    "lace, panel seams, buttons, chains, fabric crinkles). Skip the silhouette. "
    "Reply ONLY valid JSON: "
    '{"curves":[{"label":str,"region":str,"points":[[u,v],...]}]} '
    "where u,v are normalized 0..1 coords (u=x/width, v=y/height). "
    "Each curve must have >= 4 points. Be exhaustive (30+ curves). No prose."
)

def _img_b64(path, max_side=896):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    im.thumbnail((max_side, max_side))
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=92)
    return base64.b64encode(buf.getvalue()).decode()

def ask_llama(image_path, prompt=PROMPT_TRACE, num_predict=2000):
    b64 = _img_b64(image_path)
    payload = {
        "model": "any",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
            ]
        }],
        "max_tokens": num_predict,
        "temperature": 0.1,
        "enable_thinking": False,
    }
    req = urllib.request.Request(LLAMA_URL, data=json.dumps(payload).encode(),
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read())
    return d["choices"][0]["message"]["content"]

def trace_image_to_json(image_path, out_json):
    txt = ask_llama(image_path)
    # extract JSON block
    s = txt.find("{"); e = txt.rfind("}")
    if s < 0 or e < 0:
        raise RuntimeError(f"no JSON in VLM reply: {txt[:300]}")
    try:
        data = json.loads(txt[s:e+1])
    except json.JSONDecodeError as ex:
        raise RuntimeError(f"bad JSON: {ex}; raw: {txt[s:e+1][:400]}")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return out_json, len(data.get("curves", []))

if __name__ == "__main__":
    img = sys.argv[1] if len(sys.argv) > 1 else r"D:/Alice/tools/dress/regen/in_front.png"
    out = sys.argv[2] if len(sys.argv) > 2 else r"D:/Alice/tools/auto-rig-fix/work/vision_trace.json"
    p, n = trace_image_to_json(img, out)
    print(f"saved {p} with {n} curves")
