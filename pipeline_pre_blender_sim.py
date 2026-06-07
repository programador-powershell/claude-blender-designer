# -*- coding: utf-8 -*-
"""Pre-Blender simulation loop.

Pra cada peca:
1. Compose 2D simulation: body silhouette + piece overlay (shape, position, color, size)
2. Send to Qwen3-VL com ref crop Florence2: avalia shape/position/curves/lines
3. Auto-tune params baseado em Qwen feedback
4. Loop ate Qwen aprovar (score 9+)
5. Salva params aprovados em work/sim_approved/<piece>.json
6. SO ENTAO chama Blender build

Camera-space coords (front view ortho scale 2.2, res 600x800):
  Y(image) = pixel from top
  Z(world) = (1 - Y/800) * 2.2 (approx; cam centered z=1.0)
"""
import os, sys, json, base64, urllib.request, argparse, time, math
from PIL import Image, ImageDraw, ImageChops
sys.path.insert(0, r"D:/Alice/tools/auto-rig-fix/live")

ROOT = r"D:/Alice/tools/auto-rig-fix"
WORK = os.path.join(ROOT, "work")
SIM_DIR = os.path.join(WORK, "simulation")
SIM_APPROVED = os.path.join(WORK, "sim_approved")
FL_MASKS = os.path.join(WORK, "florence_masks")
MANIFESTS_DIR = os.path.join(WORK, "manifests")
QWEN = "http://127.0.0.1:8080/v1/chat/completions"

# Camera convention (matches _render_3views/sim)
CAM_ORTHO_SCALE = 2.2
RES_W, RES_H = 600, 800
CAM_Z_CENTER = 1.0  # camera location.z
# vertical world units in view = ortho_scale * (H/W) ? Actually for ortho cam, vertical = ortho_scale * (H/W)
# Blender ortho_scale = horizontal width. Vertical = ortho_scale * (H/W) = 2.2 * (800/600) = 2.933
VERT_WORLD = CAM_ORTHO_SCALE * (RES_H / RES_W)


def world_z_to_pixel_y(z):
    """World Z (meters) -> pixel Y from top of image."""
    # camera Y=0 at z=1.0; image vertical spans z=[1.0-VERT_WORLD/2, 1.0+VERT_WORLD/2]
    z_top = CAM_Z_CENTER + VERT_WORLD/2
    z_bot = CAM_Z_CENTER - VERT_WORLD/2
    norm = (z_top - z) / (z_top - z_bot)
    return int(norm * RES_H)


def world_radius_to_pixel_w(r):
    """World radius (meters) -> pixel width (full horizontal projection)."""
    return int(2 * r * RES_W / CAM_ORTHO_SCALE)


def b64(p):
    with open(p, 'rb') as f: return base64.b64encode(f.read()).decode()


def compose_sim(body_path, params, out_path):
    """Compose body silhouette + piece overlay (ellipse based on rx,ry,z range)."""
    body = Image.open(body_path).convert('RGBA')
    overlay = Image.new('RGBA', body.size, (0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    z_top = params.get('z_top', 1.0); z_bot = params.get('z_bot', 0.5)
    rx = params.get('rx', 0.20); ry = params.get('ry', 0.15)
    color = params.get('color_rgb', [200,180,140])
    y_top = world_z_to_pixel_y(z_top); y_bot = world_z_to_pixel_y(z_bot)
    w = world_radius_to_pixel_w(rx)
    x_cen = RES_W // 2
    x0 = x_cen - w//2; x1 = x_cen + w//2
    # Ellipse-shaped piece overlay
    draw.ellipse([x0, y_top, x1, y_bot], fill=(*color, 180), outline=(255,0,0,255), width=2)
    # Annotate
    draw.text((10, 10), f"z=[{z_bot:.2f},{z_top:.2f}] rx={rx:.2f} ry={ry:.2f}",
              fill=(255,255,255,255))
    composite = Image.alpha_composite(body, overlay)
    composite.convert('RGB').save(out_path)
    return out_path


def qwen_sim_validate(sim_path, ref_path, piece, params):
    """Ask Qwen: does simulated overlay match reference shape/position/curves?
    No system prompt (compact context for sim loop speed)."""
    rb = b64(sim_path); fb = b64(ref_path)
    prompt = f"""Pre-Blender simulation check for piece "{piece}".
Img1: 2D sim - red ellipse overlay on Alice body silhouette at proposed position.
Img2: reference crop from source image.
Params: z=[{params.get('z_bot')},{params.get('z_top')}] rx={params.get('rx')} ry={params.get('ry')}.

Score 0-10 each: shape, position, size, overall.
Return JSON ONLY (no fence):
{{"shape_score":0,"position_score":0,"size_score":0,"overall_score":0,
"adjustment_hint":{{"z_top_delta":0,"z_bot_delta":0,"rx_multiplier":1.0,"ry_multiplier":1.0}},
"ready_for_blender":false}}
ready_for_blender=true only if overall>=9. Hints: deltas in meters (-0.10..+0.10), multipliers 0.5..2.0."""
    payload = {
        "model": "qwen3-vl",
        "messages": [{"role":"user","content":[
            {"type":"image_url","image_url":{"url":f"data:image/png;base64,{rb}"}},
            {"type":"image_url","image_url":{"url":f"data:image/png;base64,{fb}"}},
            {"type":"text","text":prompt}
        ]}],
        "max_tokens": 200, "temperature": 0.0
    }
    req = urllib.request.Request(QWEN, data=json.dumps(payload).encode(),
                                  headers={"Content-Type":"application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=600).read())
    txt = r['choices'][0]['message']['content'].strip()
    if txt.startswith('```'): txt = txt.strip('`').lstrip('json').strip()
    try: return json.loads(txt)
    except Exception: return {"_raw": txt, "overall_score": 0, "ready_for_blender": False}


def apply_hints(params, hints, damping=0.5):
    """Apply Qwen adjustment hints with damping (avoid oscillation)."""
    new = dict(params)
    if 'z_top_delta' in hints:
        new['z_top'] = round(new.get('z_top',1.0) + float(hints['z_top_delta']) * damping, 4)
    if 'z_bot_delta' in hints:
        new['z_bot'] = round(new.get('z_bot',0.5) + float(hints['z_bot_delta']) * damping, 4)
    if 'rx_multiplier' in hints:
        mult = 1.0 + (float(hints['rx_multiplier']) - 1.0) * damping
        new['rx'] = round(new.get('rx',0.22) * mult, 4)
    if 'ry_multiplier' in hints:
        mult = 1.0 + (float(hints['ry_multiplier']) - 1.0) * damping
        new['ry'] = round(new.get('ry',0.16) * mult, 4)
    return new


def simulate_until_approved(piece_name, manifest_path=None, max_iters=8):
    """Loop pre-Blender simulation ate Qwen aprovar."""
    os.makedirs(SIM_APPROVED, exist_ok=True)
    os.makedirs(SIM_DIR, exist_ok=True)
    body_front = os.path.join(SIM_DIR, "body_SIM_FRONT.png")
    if not os.path.exists(body_front):
        print(f"ERR: body silhouette missing: {body_front}")
        print("  Rode _render_body_only.py primeiro")
        return None

    # Load piece data from manifest
    manifest_path = manifest_path or os.path.join(MANIFESTS_DIR, "chapeleiro.json")
    m = json.load(open(manifest_path, encoding='utf-8'))
    pdata = next((x for x in m['pieces'] if x['name'] == piece_name), None)
    if not pdata: print(f"ERR piece {piece_name} not in manifest"); return None

    # Ref crop Florence2
    ref_crop = os.path.join(FL_MASKS, f"{piece_name}_crop.png")
    if not os.path.exists(ref_crop):
        print(f"ERR Florence ref crop missing: {ref_crop}")
        return None

    # Initial params from manifest
    z = pdata.get('z', [0.5, 1.0])
    # Default radii by bone anchor
    bone = (pdata.get('bone_anchor','') or '').lower()
    if 'hips' in bone or 'spine' in bone:
        rx, ry = 0.22, 0.16
    elif 'leg' in bone or 'foot' in bone:
        rx, ry = 0.10, 0.10
    elif 'arm' in bone or 'hand' in bone:
        rx, ry = 0.08, 0.08
    else:
        rx, ry = 0.20, 0.15
    params = {'z_top': z[1], 'z_bot': z[0], 'rx': rx, 'ry': ry,
              'color_rgb': [200, 180, 140]}

    history = []
    best_params = dict(params); best_score = 0
    for it in range(1, max_iters+1):
        sim_path = os.path.join(SIM_DIR, f"sim_{piece_name}_it{it:02d}.png")
        compose_sim(body_front, params, sim_path)
        print(f"[SIM iter {it}] {params}")
        t0 = time.time()
        q = qwen_sim_validate(sim_path, ref_crop, piece_name, params)
        score = q.get('overall_score', 0)
        print(f"  Qwen [{time.time()-t0:.0f}s]: {q}")
        history.append({"iter": it, "params": dict(params), "qwen": q,
                        "sim_path": sim_path})
        if score > best_score:
            best_score = score; best_params = dict(params)
            print(f"  ^ NEW BEST {score}")
        elif score < best_score - 2:  # significant regression
            print(f"  ! REGRESSION (score {score} < best {best_score}-2). Revert to best.")
            params = dict(best_params)
            continue
        if q.get('ready_for_blender') and score >= 9:
            approved = os.path.join(SIM_APPROVED, f"{piece_name}.json")
            json.dump({"piece": piece_name, "approved_params": params,
                       "iters": it, "history": history},
                      open(approved, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
            print(f"\nAPPROVED iter {it} -> {approved}")
            return params
        # apply hints with damping (decay over iters)
        damping = max(0.2, 0.5 - 0.05*it)
        hints = q.get('adjustment_hint', {})
        if hints:
            params = apply_hints(params, hints, damping=damping)
    # max iters: save best
    best = max(history, key=lambda h: h['qwen'].get('overall_score', 0))
    print(f"MAX ITERS - best score {best['qwen'].get('overall_score')} not approved")
    approved = os.path.join(SIM_APPROVED, f"{piece_name}_best.json")
    json.dump({"piece": piece_name, "best_params": best['params'],
               "best_score": best['qwen'].get('overall_score'),
               "history": history, "approved": False},
              open(approved, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--piece', required=True)
    ap.add_argument('--manifest', default=None)
    ap.add_argument('--max-iters', type=int, default=8)
    a = ap.parse_args()
    r = simulate_until_approved(a.piece, a.manifest, a.max_iters)
    sys.exit(0 if r else 1)

if __name__ == '__main__':
    main()
