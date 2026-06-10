"""Revisao cv2 v2: faixas ANCORADAS EM KEYPOINTS WholeBody (sem vies de bbox).
Zonas anatomicas definidas por landmarks reais de cada imagem:
chapeu(acima nose+offset), rosto, pescoco-ombro, busto, cintura(meio
shoulder-hip), quadril, saia-alta(hip..hip+33% hip-knee), saia-media,
saia-baixa(..knee), canela(knee..ankle), pes."""
import cv2, sys, json
import numpy as np
sys.path.insert(0, r'D:/Alice/tools/auto-rig-fix')
from wholebody_map import detect, BODY

def edges(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g = cv2.bilateralFilter(g, 7, 60, 60)
    return cv2.Canny(g, 40, 120)

def zones_from_kp(kp, sc, H):
    def P(n):
        i = BODY[n]
        return kp[i] if sc[i] > 0.3 else None
    nose = P('nose')
    sh = [(P('shoulder_l') + P('shoulder_r')) / 2 if P('shoulder_l') is not None and P('shoulder_r') is not None else None][0]
    hip = [(P('hip_l') + P('hip_r')) / 2 if P('hip_l') is not None and P('hip_r') is not None else None][0]
    kn = [(P('knee_l') + P('knee_r')) / 2 if P('knee_l') is not None and P('knee_r') is not None else None][0]
    an = [(P('ankle_l') + P('ankle_r')) / 2 if P('ankle_l') is not None and P('ankle_r') is not None else None][0]
    ny, sy, hy, ky, ay = nose[1], sh[1], hip[1], kn[1], an[1]
    head_h = (sy - ny)
    return [
        ('chapeu',        max(0, ny - head_h * 2.2), max(0, ny - head_h * 0.9)),
        ('cabeca/rosto',  max(0, ny - head_h * 0.9), ny + head_h * 0.55),
        ('pescoco/ombro', ny + head_h * 0.55, sy + (hy - sy) * 0.18),
        ('busto/corpete', sy + (hy - sy) * 0.18, sy + (hy - sy) * 0.62),
        ('cintura',       sy + (hy - sy) * 0.62, hy),
        ('saia alta',     hy, hy + (ky - hy) * 0.38),
        ('saia media',    hy + (ky - hy) * 0.38, hy + (ky - hy) * 0.72),
        ('saia baixa/hem',hy + (ky - hy) * 0.72, ky + (ay - ky) * 0.10),
        ('canela',        ky + (ay - ky) * 0.10, ay),
        ('pes',           ay, min(H, ay + (ay - ky) * 0.28)),
    ]

ref_p, ren_p = sys.argv[1], sys.argv[2]
out = []
imgs = {}
for tag, p in [('ref', ref_p), ('ren', ren_p)]:
    img, kp, sc = detect(p)
    e = edges(img)
    zs = zones_from_kp(kp, sc, img.shape[0])
    dens = {}
    for nm, y0, y1 in zs:
        y0i, y1i = int(y0), int(max(y1, y0 + 2))
        dens[nm] = float(e[y0i:y1i].mean())
    imgs[tag] = dens
print(f'{"zona":<16}{"ref":>7}{"render":>8}{"ratio":>7}  diag')
for nm, _, _ in zones_from_kp(*detect(ref_p)[1:], cv2.imread(ref_p).shape[0]):
    a = imgs['ref'][nm]; b = imgs['ren'][nm]
    r = b / a if a > 0.3 else float('nan')
    diag = '<<< FALTA' if (a > 2 and r < 0.45) else ('< pouco' if (a > 2 and r < 0.7) else ('>> excesso' if r > 1.8 else ''))
    print(f'{nm:<16}{a:>7.1f}{b:>8.1f}{r:>7.2f}  {diag}')
