# -*- coding: utf-8 -*-
import os, sys, json, base64, urllib.request, io
LLAMA_URL = os.environ.get('LLAMA_URL', 'http://127.0.0.1:8080/v1/chat/completions')
PROMPT = '''Você é um modelista técnico 3D. Analise a roupa da personagem e responda SOMENTE JSON válido. Separe a roupa como uma costureira faria: corset, blusa base, saias internas/externas, avental, mangas, rendas, babados, cintos, correntes, cartas, relógio, rosas, luvas, botas e chapéu. Schema: {"pieces":[{"id":str,"category":str,"layer":int,"shape":str,"material_hint":str,"anchors":[str],"physics":"fitted|cloth|rigid","visible_details":[str]}],"accessories":[{"id":str,"category":str,"layer":int,"material_hint":str,"parent_piece":str|null,"visible_details":[str]}],"notes":[str]}'''

def _img_b64(path, max_side=1280):
    from PIL import Image
    im = Image.open(path).convert('RGB'); im.thumbnail((max_side, max_side)); buf = io.BytesIO(); im.save(buf, 'JPEG', quality=92)
    return base64.b64encode(buf.getvalue()).decode()

def ask(images):
    content=[{'type':'text','text':PROMPT}]
    for p in images:
        content.append({'type':'image_url','image_url':{'url':f'data:image/jpeg;base64,{_img_b64(p)}'}})
    payload={'model':'any','messages':[{'role':'user','content':content}], 'temperature':0.1, 'max_tokens':3500, 'enable_thinking':False}
    req=urllib.request.Request(LLAMA_URL, data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=240) as r: d=json.loads(r.read())
    txt=d['choices'][0]['message']['content']; s=txt.find('{'); e=txt.rfind('}')
    if s<0 or e<0: raise RuntimeError('VLM não retornou JSON')
    return json.loads(txt[s:e+1])

if __name__ == '__main__':
    out = sys.argv[-1] if sys.argv[-1].lower().endswith('.json') else 'garment_trace.json'
    imgs = [x for x in sys.argv[1:] if not x.lower().endswith('.json')]
    data=ask(imgs)
    with open(out,'w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)
    print(out)
