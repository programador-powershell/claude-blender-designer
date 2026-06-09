"""Agente vision DEFINITIVO — Blender VE o render E compara com o concept art.

Loop fechado:
  1. apply_knobs.py -> rig SHD com knobs -> GLB+blend
  2. render_views.py -> 3 PNGs (front/34/side) BLINDADO
  3. maverick (NVIDIA NIM vision) recebe: [concept art] + [3 renders] + historico
     -> retorna {score, problems[], knobs} comparando render vs conceito
  4. score>=alvo ou max_iters -> para. senao re-aplica knobs e repete.

Espaco de acao FECHADO (knobs nomeados, ranges travados). Modelo NAO escreve
codigo. Determinismo + nao explode.

Uso:
  python agent.py --outfit <slug> --iters 5 --target 9
    slug: dress|cheshire|rainha|chapeleiro|coelho|lagarta
"""
import os, sys, json, base64, subprocess, argparse

HERE=os.path.dirname(os.path.abspath(__file__))
BLENDER=r"D:\Blender Foundation\blender.exe"
BODY=r"D:\Alice\tools\body-rebuild\out\alice_body_clean.fbx"
POSEANIM=r"D:\model\anims\Standing Idle.fbx"
APPLY=os.path.join(HERE,"apply_knobs.py")
RENDER=os.path.join(HERE,"render_views.py")

NVIDIA_KEY=os.getenv("NVIDIA_API_KEY","")
MODEL="meta/llama-4-maverick-17b-128e-instruct"

# slug -> (outfit fbx, concept png)
OUTFITS={
 "dress":     (r"E:\References\3D\SK_AliceDress.fbx",      r"D:\project-alice-challenge\public\concepts\personagens\alice.png"),
 "cheshire":  (r"E:\References\3D\SK_Alice_Cheshire.fbx",  r"D:\project-alice-challenge\public\concepts\personagens\alice-vestido-cheshire.png"),
 "rainha":    (r"E:\References\3D\SK_Alice_Rainha.fbx",    r"D:\project-alice-challenge\public\concepts\personagens\alice-vestido-rainha.png"),
 "chapeleiro":(r"E:\References\3D\SK_Alice_Chapeleiro.fbx",r"D:\project-alice-challenge\public\concepts\personagens\alice-vestido-chapeleiro.png"),
 "coelho":    (r"E:\References\3D\SK_Alice_Coelho.fbx",    r"D:\project-alice-challenge\public\concepts\personagens\alice-vestido-coelho.png"),
 "lagarta":   (r"E:\References\3D\SK_Alice_Lagarta.fbx",   r"D:\project-alice-challenge\public\concepts\personagens\alice-vestido-lagarta.png"),
}

KNOB_SCHEMA={
 "arm_angle_x":[0,90],"arm_scale":[0.7,1.1],"dress_offset_z":[-0.05,0.05],
 "skirt_to_hips":"bool","hide_body_under":"bool","hide_dist":[0.01,0.06],
 "cut_body_arms":"bool","cut_margin":[0.0,0.08],"shd_res":[64,160],
}

SYSTEM=(
 "Voce e revisor de rig 3D. Comparar o RENDER 3D (clay cinza, 3 vistas: front/34/side) "
 "com a ARTE CONCEITUAL (1a imagem). Objetivo: o 3D bater com o conceito. "
 "Ignore COR/textura (render e clay). Foque GEOMETRIA/SILHUETA.\n\n"
 "PROBLEMAS e correcoes (knobs):\n"
 "1. BRACOS DUPLICADOS (braco do corpo furando pra fora da manga, parece 4 bracos): "
 "cut_body_arms=true + baixar cut_margin (0.0-0.02 corta mais). Tambem hide_body_under=true.\n"
 "2. SAIA RACHADA/LASCADA (babados em fragmentos): skirt_to_hips=true; se persistir subir shd_res(128-160).\n"
 "3. MESH EXPLODIDO/CAOTICO (parte vira tabuas/lixo): subir shd_res=160 + cut_margin maior.\n"
 "4. VESTIDO ALTO/BAIXO vs corpo: dress_offset_z.\n\n"
 "Responda SO JSON:\n"
 '{"score":<0-10>,"problems":["..."],"matches_concept":<true/false>,'
 '"knobs":{"arm_angle_x":N,"arm_scale":N,"dress_offset_z":N,"skirt_to_hips":bool,'
 '"hide_body_under":bool,"hide_dist":N,"cut_body_arms":bool,"cut_margin":N,"shd_res":N}}\n'
 f"Ranges:{json.dumps(KNOB_SCHEMA)}. score 10=silhueta bate com conceito, sem bracos "
 "duplicados, saia inteira. Critico."
)

def b64(p):
    with open(p,"rb") as f: return base64.b64encode(f.read()).decode()

def run_apply(knobs, outfit_fbx, out_glb):
    kp=os.path.join(HERE,"work","knobs.json"); os.makedirs(os.path.dirname(kp),exist_ok=True)
    json.dump(knobs,open(kp,"w"))
    r=subprocess.run([BLENDER,"-b","--python",APPLY,"--",kp,out_glb,
        f"body={BODY}",f"outfit={outfit_fbx}"],  # sem anim no rig (T-pose rest, riggado). anim/retarget no UE.
        capture_output=True,text=True,timeout=900)
    ok=os.path.exists(out_glb)
    if not ok: print("  [apply FALHOU]", r.stdout[-800:])
    return ok

def run_render(blend, prefix):
    subprocess.run([BLENDER,"-b",blend,"--python",RENDER,"--",prefix,"120"],
        capture_output=True,text=True,timeout=600)
    return [prefix+s for s in ("_front.png","_34.png","_side.png")]

def ask(concept, imgs, prev, history):
    from openai import OpenAI
    cli=OpenAI(api_key=NVIDIA_KEY,base_url="https://integrate.api.nvidia.com/v1")
    hist_txt=""
    if history:
        hist_txt="Historico (knob->score): "+"; ".join(f"it{h['iter']} s{h['score']}" for h in history)
    content=[{"type":"text","text":f"1a img=CONCEITO. Resto=RENDER 3D atual. Knobs={json.dumps(prev)}. {hist_txt}. Avalie e corrija."}]
    content.append({"type":"image_url","image_url":{"url":f"data:image/png;base64,{b64(concept)}"}})
    for p in imgs:
        if os.path.exists(p):
            content.append({"type":"image_url","image_url":{"url":f"data:image/png;base64,{b64(p)}"}})
    r=cli.chat.completions.create(model=MODEL,
        messages=[{"role":"system","content":SYSTEM},{"role":"user","content":content}],
        max_tokens=700,temperature=0.2)
    t=r.choices[0].message.content
    s=t.find("{"); e=t.rfind("}")
    return json.loads(t[s:e+1])

def clamp(k):
    o=dict(k)
    for key,rng in KNOB_SCHEMA.items():
        if rng=="bool": o[key]=bool(o.get(key,False))
        elif key in o:
            try: o[key]=max(rng[0],min(rng[1],float(o[key])))
            except: pass
    return o

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--outfit",required=True,choices=list(OUTFITS.keys()))
    ap.add_argument("--iters",type=int,default=5)
    ap.add_argument("--target",type=float,default=9.0)
    a=ap.parse_args()
    if not NVIDIA_KEY: print("ERRO: NVIDIA_API_KEY"); return 1

    outfit_fbx, concept = OUTFITS[a.outfit]
    if not os.path.exists(concept):
        print(f"WARN concept nao achado: {concept}")
    wd=os.path.join(HERE,"work","agent",a.outfit); os.makedirs(wd,exist_ok=True)
    glb=os.path.join(wd,"out.glb"); blend=os.path.splitext(glb)[0]+".blend"

    knobs={"arm_angle_x":35,"arm_scale":1.0,"dress_offset_z":0.0,"skirt_to_hips":True,
           "hide_body_under":True,"hide_dist":0.03,"cut_body_arms":True,"cut_margin":0.02,"shd_res":110}
    history=[]; best=None
    for it in range(1,a.iters+1):
        print(f"\n=== {a.outfit} ITER {it}/{a.iters} === {json.dumps(knobs)}")
        if not run_apply(knobs,outfit_fbx,glb): break
        imgs=run_render(blend,os.path.join(wd,f"it{it}"))
        try: v=ask(concept,imgs,knobs,history)
        except Exception as e: print("  [maverick ERRO]",e); break
        sc=v.get("score",0); pr=v.get("problems",[]); mc=v.get("matches_concept")
        print(f"  SCORE={sc} matches={mc} problems={pr}")
        history.append({"iter":it,"score":sc,"knobs":dict(knobs),"problems":pr})
        if best is None or sc>best["score"]: best={"iter":it,"score":sc,"knobs":dict(knobs),"glb":glb}
        if sc>=a.target: print(f"  >>> target {a.target} atingido"); break
        knobs=clamp(v.get("knobs",knobs))
    json.dump(history,open(os.path.join(wd,"history.json"),"w"),indent=2)
    print(f"\n=== {a.outfit} FIM. melhor score={best['score'] if best else '?'} it={best['iter'] if best else '?'} ===")
    if best: print("knobs:",json.dumps(best["knobs"]))
    return 0

if __name__=="__main__": sys.exit(main())
