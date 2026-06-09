# -*- coding: utf-8 -*-
"""Compara silhueta ARTE x MODELO por faixa de altura (CV objetivo, sem VLM).
Saida: por banda z, razao largura arte/modelo -> onde modelo estreito(>1)/largo(<1).
python silhouette_diff.py <ref> <render> [bands=16]"""
import sys, cv2, numpy as np, json
ref_p, ren_p = sys.argv[1], sys.argv[2]
BANDS = int(sys.argv[3]) if len(sys.argv) > 3 else 16

def silmask(p):
    im = cv2.imread(p).astype(np.int16)
    bg = im[3,3].astype(np.int16)                     # cor do fundo (canto)
    diff = np.abs(im - bg).sum(2)
    m = (diff > 32).astype(np.uint8) * 255            # figura = difere do fundo
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3,3), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((11,11), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    if n > 1:
        big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA])); m = (lab == big).astype(np.uint8)*255
    ys, xs = np.where(m > 0)
    crop = m[ys.min():ys.max()+1, xs.min():xs.max()+1]
    h, w = crop.shape
    return cv2.resize(crop, (max(1, int(w*900/h)), 900))   # normaliza so por ALTURA

H = 900
ma = silmask(ref_p); mm = silmask(ren_p)
def widths(m):
    w = []
    for y in range(H):
        xs = np.where(m[y] > 0)[0]
        w.append((xs.max()-xs.min()) if len(xs) else 0)
    return np.array(w, float)
wa, wm = widths(ma), widths(mm)
Z_TOP, Z_BOT = 1.70, 0.0   # mapeia row->z (row0=topo=z1.70)
print("band | z-range        | art_w | mdl_w | ratio(art/mdl)")
res = []
for b in range(BANDS):
    r0, r1 = b*H//BANDS, (b+1)*H//BANDS
    a = wa[r0:r1].mean(); md = wm[r0:r1].mean()
    ratio = (a/md) if md > 5 else 1.0
    z1 = Z_TOP - (r0/H)*Z_TOP; z0 = Z_TOP - (r1/H)*Z_TOP
    res.append({"z0": round(z0,3), "z1": round(z1,3), "ratio": round(ratio,3)})
    print(f"{b:2d}   | {z0:.2f}-{z1:.2f}      | {a:5.0f} | {md:5.0f} | {ratio:.3f}")
json.dump(res, open(r"D:/Alice/tools/auto-rig-fix/work/sil_bands.json","w"))
print("SAVED sil_bands.json")
