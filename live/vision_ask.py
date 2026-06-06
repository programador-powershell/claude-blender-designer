# -*- coding: utf-8 -*-
"""vision_ask — o OLHO do closed-loop: manda IMAGEM (screenshot do viewport ou arte)
pro VLM local e devolve descricao/validacao.

Backend: llama.cpp em http://127.0.0.1:8080 (Qwen3-VL 30B local).

Uso:
  python vision_ask.py <image> "<prompt>"
"""
import base64, json, urllib.request, sys, os, io

LLAMA_URL   = os.environ.get("LLAMA_URL",  "http://127.0.0.1:8080/v1/chat/completions")
MAX_SIDE    = int(os.environ.get("VISION_MAX_SIDE", "640"))      # downscale p/ payload/velocidade/memoria

def _img_b64(path, max_side=MAX_SIDE):
    raw = open(path, "rb").read()
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        im.thumbnail((max_side, max_side))
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=88)
        return base64.b64encode(buf.getvalue()).decode(), "image/jpeg"
    except Exception:
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
        return base64.b64encode(raw).decode(), mime

def _ask_llama(image_path, prompt, num_predict):
    b64, mime = _img_b64(image_path)
    body = json.dumps({
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}]}],
        "max_tokens": num_predict, "temperature": 0.2,
        "chat_template_kwargs": {"enable_thinking": False}}).encode()
    req = urllib.request.Request(LLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=900).read())
    return d["choices"][0]["message"].get("content", "")

def _ask_llama_multi(image_paths, prompt, num_predict):
    content = [{"type": "text", "text": prompt}]
    for p in image_paths:
        b64, mime = _img_b64(p)
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
    body = json.dumps({
        "messages": [{"role": "user", "content": content}],
        "max_tokens": num_predict, "temperature": 0.2,
        "chat_template_kwargs": {"enable_thinking": False}}).encode()
    req = urllib.request.Request(LLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=900).read())
    return d["choices"][0]["message"].get("content", "")

def ask(image_path, prompt, num_predict=400):
    return _ask_llama(image_path, prompt, num_predict)

def ask_multi(image_paths, prompt, num_predict=600):
    """Compara VARIAS imagens numa chamada (ex: [arte_ref, render_atual])."""
    return _ask_llama_multi(image_paths, prompt, num_predict)

if __name__ == "__main__":
    IMG = sys.argv[1]
    PROMPT = sys.argv[2] if len(sys.argv) > 2 else "Describe this image."
    print(ask(IMG, PROMPT))
