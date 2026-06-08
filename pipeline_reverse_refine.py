# -*- coding: utf-8 -*-
"""Esteira refino reverse vs alice-chapeleiro.png 3-views.

1. Crop turnaround em 3 views (front/side/back)
2. Render reverse_glb em 3 views (cam_front/side/back)
3. cv2 inspectors (overlay/lines/shadow/texture/color/light) per view
4. Qwen multi-criteria score per view
5. If avg < TARGET: ajustar (brightness/saturation/lighting) + re-render
6. Loop ate score 10 OU max iters
"""
import os, sys, json, time, base64, urllib.request, argparse, subprocess, tempfile
from PIL import Image
import cv2

sys.path.insert(0, r"D:/Alice/tools/auto-rig-fix")
sys.path.insert(0, r"D:/Alice/tools/auto-rig-fix/live")
from cv2_inspectors import run_all_inspectors

ROOT = r"D:/Alice/tools/auto-rig-fix"
WORK = os.path.join(ROOT, "work")
BRIDGE = os.path.join(ROOT, "bridge_cmd.py")
TURNAROUND = r"D:/References/img/Model 3D/BASE/Alice chapeleiro/alice-chapeleiro.png"
GLB_IN = os.path.join(WORK, "alice_chapeleiro_AAA.glb")
REF_DIR = os.path.join(WORK, "ref_3views")
RENDER_DIR = os.path.join(WORK, "reverse_refine_renders")
INSPECT_DIR = os.path.join(WORK, "reverse_refine_inspect")
APPROVED = os.path.join(WORK, "reverse_refine_approved.json")
QWEN = "http://127.0.0.1:8080/v1/chat/completions"

for d in [REF_DIR, RENDER_DIR, INSPECT_DIR]: os.makedirs(d, exist_ok=True)

TARGET_SCORE = 10
MAX_ITERS = 8


def b64(p):
    with open(p, 'rb') as f: return base64.b64encode(f.read()).decode()


def crop_turnaround():
    """Split turnaround em 3 partes iguais front/side/back."""
    img = Image.open(TURNAROUND).convert('RGB')
    W, H = img.size
    # Equal thirds
    third = W // 3
    crops = {}
    for i, name in enumerate(['FRONT', 'SIDE', 'BACK']):
        crop = img.crop((i * third, 0, (i+1) * third, H))
        out = os.path.join(REF_DIR, f"ref_{name}.png")
        crop.save(out)
        crops[name] = out
    return crops


def render_3views(brightness_mult=1.0, saturation_mult=1.0):
    """Blender render reverse_glb com lighting adjust."""
    script = f"""
import bpy, os, math
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=r'{GLB_IN.replace(chr(92),"/")}')

mult_b = {brightness_mult}; mult_s = {saturation_mult}

# Lighting
bpy.ops.object.light_add(type='AREA', location=(2.5,-3,2.5))
bpy.context.object.name = 'KEY'; bpy.context.object.data.energy = 1000 * mult_b
bpy.context.object.data.size = 1.5
bpy.ops.object.light_add(type='AREA', location=(-2,-2,1.8))
bpy.context.object.name = 'FILL'; bpy.context.object.data.energy = 400 * mult_b
bpy.ops.object.light_add(type='AREA', location=(0,3,2.0))
bpy.context.object.name = 'RIM'; bpy.context.object.data.energy = 500 * mult_b

bpy.context.scene.world.use_nodes = True
bg = bpy.context.scene.world.node_tree.nodes.get('Background')
if bg:
    bg.inputs[0].default_value = (0.15, 0.15, 0.17, 1.0)
    bg.inputs[1].default_value = 0.3 * mult_b

# Boost saturation per material
for m in bpy.data.materials:
    if not m.use_nodes: continue
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    if bsdf and 'Base Color' in bsdf.inputs:
        c = bsdf.inputs['Base Color'].default_value
        # Push toward saturation mult
        avg = (c[0]+c[1]+c[2])/3
        bsdf.inputs['Base Color'].default_value = (
            avg + (c[0]-avg)*mult_s, avg + (c[1]-avg)*mult_s,
            avg + (c[2]-avg)*mult_s, c[3])

def cam(name, loc, rot):
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    c = bpy.data.objects.get(name) or bpy.data.objects.new(name, cd)
    if not c.users_collection: bpy.context.scene.collection.objects.link(c)
    c.location = loc; c.rotation_euler = rot
    c.data.type = 'ORTHO'; c.data.ortho_scale = 2.0

cam('REF_FRONT', (0,-4,1.0), (math.radians(90),0,0))
cam('REF_SIDE', (4,0,1.0), (math.radians(90),0,math.radians(90)))
cam('REF_BACK', (0,4,1.0), (math.radians(90),0,math.radians(180)))

sc = bpy.context.scene
sc.render.engine = 'CYCLES'
try: sc.cycles.device = 'GPU'
except: pass
sc.cycles.samples = 64
sc.render.resolution_x = 600; sc.render.resolution_y = 800
sc.render.image_settings.file_format = 'PNG'

OUT = r'{RENDER_DIR.replace(chr(92),"/")}'
for cn, label in [('REF_FRONT','FRONT'),('REF_SIDE','SIDE'),('REF_BACK','BACK')]:
    sc.camera = bpy.data.objects[cn]
    p = os.path.join(OUT, f'render_{{label}}.png')
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
print('RENDERED')
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script); p = f.name
    try:
        env = os.environ.copy(); env['PYTHONIOENCODING'] = 'utf-8'
        r = subprocess.run([sys.executable, BRIDGE, '--file', p],
                            capture_output=True, text=True, timeout=600, env=env)
        return r.returncode == 0
    finally:
        try: os.unlink(p)
        except: pass


def qwen_validate_view(render_path, ref_path, view_name, inspectors):
    insp_text = ""
    if inspectors:
        insp_text = f"""cv2 inspectors metrics:
  ssim={inspectors.get('ssim')} edge_overlap={inspectors.get('edge_overlap')}
  shadow_match={inspectors.get('shadow_match')} texture_match={inspectors.get('texture_match')}
  color_corr={inspectors.get('color_corr')} hue_diff={inspectors.get('hue_diff')}
  light_match={inspectors.get('light_match')}"""
    img_path = inspectors['grid'] if inspectors and inspectors.get('grid') else render_path
    payload = {
        "model": "qwen3-vl",
        "messages": [{"role":"user","content":[
            {"type":"image_url","image_url":{"url":f"data:image/png;base64,{b64(img_path)}"}},
            {"type":"image_url","image_url":{"url":f"data:image/png;base64,{b64(ref_path)}"}},
            {"type":"text","text":f"""View {view_name} fidelity check (Alice chapeleiro).
Img1: 3D render OR 3x3 inspector grid.
Img2: reference photo.
{insp_text}
Score 0-10 EACH: silhouette, color, lighting, detail, overlay_match.
JSON ONLY: {{"silhouette":0-10,"color":0-10,"lighting":0-10,"detail":0-10,"overlay":0-10,"overall":0-10,"adjust":{{"brightness_delta":-0.5..+0.5,"saturation_delta":-0.5..+0.5}}}}"""}
        ]}], "max_tokens": 200, "temperature": 0.0
    }
    req = urllib.request.Request(QWEN, data=json.dumps(payload).encode(),
                                  headers={"Content-Type":"application/json"})
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=600).read())
        txt = r['choices'][0]['message']['content'].strip()
        if txt.startswith('```'): txt = txt.strip('`').lstrip('json').strip()
        return json.loads(txt)
    except Exception as e:
        return {"_err": str(e), "overall": 0}


def main():
    print(f"\n{'='*60}\nREVERSE REFINE PIPELINE\n{'='*60}")
    if not os.path.exists(GLB_IN):
        print(f"ERR sem GLB: {GLB_IN}"); sys.exit(1)

    # 1. Crop turnaround 3-views
    print("\n[crop turnaround]")
    refs = crop_turnaround()
    for n, p in refs.items(): print(f"  {n}: {p}")

    # 2. Loop refine
    brightness = 1.0; saturation = 1.0
    history = []
    best_score = 0; best_params = (1.0, 1.0)
    for it in range(1, MAX_ITERS+1):
        print(f"\n--- ITER {it}/{MAX_ITERS} brightness={brightness:.2f} sat={saturation:.2f} ---")
        if not render_3views(brightness, saturation):
            print("  RENDER FAIL"); break
        # Per view: inspectors + Qwen
        view_scores = {}
        avg_adjust_b = 0; avg_adjust_s = 0
        for view in ['FRONT', 'SIDE', 'BACK']:
            r_path = os.path.join(RENDER_DIR, f"render_{view}.png")
            f_path = refs[view]
            insp = run_all_inspectors(r_path, f_path, os.path.join(INSPECT_DIR, f"it{it:02d}_{view}"), view)
            if insp:
                print(f"  {view} insp: ssim={insp['ssim']} edge={insp['edge_overlap']} color={insp['color_corr']}")
            t0 = time.time()
            q = qwen_validate_view(r_path, f_path, view, insp)
            print(f"  {view} Qwen [{time.time()-t0:.0f}s]: overall={q.get('overall')} {q}")
            view_scores[view] = q.get('overall', 0)
            adj = q.get('adjust', {})
            avg_adjust_b += float(adj.get('brightness_delta', 0))
            avg_adjust_s += float(adj.get('saturation_delta', 0))
        avg_score = sum(view_scores.values()) / 3
        avg_adjust_b /= 3; avg_adjust_s /= 3
        print(f"  AVG score: {avg_score:.1f}")
        history.append({"iter": it, "brightness": brightness, "saturation": saturation,
                         "view_scores": view_scores, "avg_score": avg_score})
        if avg_score > best_score:
            best_score = avg_score; best_params = (brightness, saturation)
        if avg_score >= TARGET_SCORE:
            print(f"  APPROVED 10/10 avg")
            json.dump({"approved": True, "iter": it, "params": {"brightness": brightness, "saturation": saturation},
                       "history": history}, open(APPROVED, 'w', encoding='utf-8'), indent=2)
            return
        # Adjust (damped)
        brightness = max(0.3, min(3.0, brightness + avg_adjust_b * 0.5))
        saturation = max(0.3, min(2.0, saturation + avg_adjust_s * 0.5))
    print(f"\nMAX ITERS - best avg {best_score:.1f} params={best_params}")
    json.dump({"approved": False, "best_score": best_score, "best_params": list(best_params),
               "history": history}, open(APPROVED, 'w', encoding='utf-8'), indent=2)


if __name__ == '__main__':
    main()
