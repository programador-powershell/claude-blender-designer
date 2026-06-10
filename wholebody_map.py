"""COCO-WholeBody (133 keypoints) mapping tool — Project Alice.

Roda RTMW (implementação COCO-WholeBody do OpenMMLab via rtmlib) na referência
e nos renders, extrai keypoints body/feet/face/hands, compara proporções e
gera overlay visual + JSON com desvios.

Uso:
  python wholebody_map.py <img1> [img2 ...]   -> keypoints + overlay por imagem
  python wholebody_map.py --compare ref.png render.png -> tabela de desvios
"""
import sys, json, os
import numpy as np
import cv2
from rtmlib import Wholebody, draw_skeleton

# COCO-WholeBody indices: 0-16 body, 17-22 feet, 23-90 face, 91-132 hands
BODY = {
    'nose': 0, 'eye_l': 1, 'eye_r': 2, 'ear_l': 3, 'ear_r': 4,
    'shoulder_l': 5, 'shoulder_r': 6, 'elbow_l': 7, 'elbow_r': 8,
    'wrist_l': 9, 'wrist_r': 10, 'hip_l': 11, 'hip_r': 12,
    'knee_l': 13, 'knee_r': 14, 'ankle_l': 15, 'ankle_r': 16,
}

_model = None
def model():
    global _model
    if _model is None:
        _model = Wholebody(mode='balanced', backend='onnxruntime', device='cpu')
    return _model

def detect(img_path):
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(img_path)
    kps, scores = model()(img)
    if kps is None or len(kps) == 0:
        return img, None, None
    # pessoa com maior score medio
    best = int(np.argmax([s.mean() for s in scores]))
    return img, kps[best], scores[best]

def proportions(kp, sc, thr=0.3):
    """Medidas anatomicas normalizadas pela altura total (nose->ankle médio)."""
    def P(name):
        i = BODY[name]
        return kp[i] if sc[i] > thr else None
    def dist(a, b):
        return float(np.linalg.norm(a - b)) if a is not None and b is not None else None
    sh_l, sh_r = P('shoulder_l'), P('shoulder_r')
    hip_l, hip_r = P('hip_l'), P('hip_r')
    ank_l, ank_r = P('ankle_l'), P('ankle_r')
    nose = P('nose')
    ank = None
    if ank_l is not None and ank_r is not None: ank = (ank_l + ank_r) / 2
    elif ank_l is not None: ank = ank_l
    elif ank_r is not None: ank = ank_r
    height = dist(nose, ank)
    if not height:
        return {}
    def rel(v):
        return round(v / height, 4) if v else None
    out = {
        'shoulder_width': rel(dist(sh_l, sh_r)),
        'hip_width': rel(dist(hip_l, hip_r)),
        'arm_upper_l': rel(dist(sh_l, P('elbow_l'))),
        'arm_fore_l': rel(dist(P('elbow_l'), P('wrist_l'))),
        'leg_thigh_l': rel(dist(hip_l, P('knee_l'))),
        'leg_shin_l': rel(dist(P('knee_l'), ank_l)),
        'torso': rel(dist((sh_l + sh_r) / 2 if sh_l is not None and sh_r is not None else None,
                          (hip_l + hip_r) / 2 if hip_l is not None and hip_r is not None else None)),
        'head_to_shoulder': rel(dist(nose, (sh_l + sh_r) / 2 if sh_l is not None and sh_r is not None else None)),
    }
    # contagens de deteccao por grupo
    out['detected'] = {
        'body': int((sc[0:17] > thr).sum()),
        'feet': int((sc[17:23] > thr).sum()),
        'face': int((sc[23:91] > thr).sum()),
        'hands': int((sc[91:133] > thr).sum()),
    }
    return out

def run_one(path, outdir):
    img, kp, sc = detect(path)
    base = os.path.splitext(os.path.basename(path))[0]
    if kp is None:
        print(f'{base}: NENHUMA pessoa detectada')
        return None
    ov = draw_skeleton(img.copy(), kp[None], sc[None], openpose_skeleton=False, kpt_thr=0.3)
    ov_path = os.path.join(outdir, f'WB_{base}.png')
    cv2.imwrite(ov_path, ov)
    props = proportions(kp, sc)
    jp = os.path.join(outdir, f'WB_{base}.json')
    with open(jp, 'w') as f:
        json.dump({'keypoints': kp.tolist(), 'scores': sc.tolist(), 'proportions': props}, f)
    d = props.get('detected', {})
    print(f'{base}: body {d.get("body",0)}/17 feet {d.get("feet",0)}/6 '
          f'face {d.get("face",0)}/68 hands {d.get("hands",0)}/42 -> {ov_path}')
    return props

def compare(ref_path, render_path, outdir):
    pr = run_one(ref_path, outdir)
    pn = run_one(render_path, outdir)
    if not pr or not pn:
        return
    print('\n=== PROPORCOES (normalizadas pela altura) ===')
    print(f'{"medida":<18}{"ref":>8}{"render":>9}{"desvio%":>9}')
    for k in ['shoulder_width','hip_width','arm_upper_l','arm_fore_l',
              'leg_thigh_l','leg_shin_l','torso','head_to_shoulder']:
        a, b = pr.get(k), pn.get(k)
        if a and b:
            dev = (b - a) / a * 100
            flag = ' <<<' if abs(dev) > 12 else ''
            print(f'{k:<18}{a:>8.3f}{b:>9.3f}{dev:>8.1f}%{flag}')
        else:
            print(f'{k:<18}{str(a):>8}{str(b):>9}      n/a')

if __name__ == '__main__':
    outdir = r'D:\Alice\tools\auto-rig-fix\work\wholebody'
    os.makedirs(outdir, exist_ok=True)
    args = sys.argv[1:]
    if args and args[0] == '--compare':
        compare(args[1], args[2], outdir)
    else:
        for p in args:
            run_one(p, outdir)
