# -*- coding: utf-8 -*-
"""vision_trace — VISAO de linha (CV) da arte do vestido -> curvas Bezier limpas (JSON).
Gemma/VLM aqui nao presta (sem mmproj); fluxo-de-linha = computer vision deterministico.
Roda no python do ComfyUI (tem cv2/numpy/scipy):
  python vision_trace.py <img> <mode skirt|hair> <out.json> [debug.png]
Saida JSON: {image_size:[W,H], curves:[{kind, pts2d:[[u,v],...]}]}  (u,v normalizados 0..1, v=top->down)
"""
import cv2, numpy as np, sys, json

IMG, MODE, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
DBG = sys.argv[4] if len(sys.argv) > 4 else None

im = cv2.imread(IMG)
if im is None: raise SystemExit(f"nao leu {IMG}")
H, W = im.shape[:2]
gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)

# silhueta da figura (bg escuro -> Otsu) + maior componente
_, m = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9,9), np.uint8))
ncc, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
if ncc > 1:
    big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    m = (lab == big).astype(np.uint8) * 255

def row_span(y):
    xs = np.where(m[y] > 0)[0]
    return (int(xs.min()), int(xs.max())) if len(xs) else None

edges = cv2.Canny(gray, 35, 110)
edges = cv2.bitwise_and(edges, m)               # so dentro da figura
curves = []

if MODE == "skirt":
    # saia = parte de baixo. tiers = linhas horizontais (ruffles) -> picos no perfil de borda por linha
    y0 = int(H * 0.46); y1 = int(H * 0.96)
    hor = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1)))
    prof = hor[y0:y1].sum(axis=1).astype(float)
    if prof.max() > 0: prof /= prof.max()
    # picos espacados (tiers)
    rows = []
    win = max(6, (y1 - y0) // 22)
    i = 0
    while i < len(prof):
        seg = prof[i:i+win]
        if len(seg) and seg.max() > 0.28:
            r = y0 + i + int(np.argmax(seg))
            if not rows or (r - rows[-1]) > win: rows.append(r)
        i += win
    for cy in rows:
        sp = row_span(cy)
        if not sp: continue
        x1c, x2c = sp
        if (x2c - x1c) < W * 0.18: continue
        pts = []
        for xx in range(x1c, x2c + 1, max(2, (x2c - x1c) // 26)):
            band = hor[max(y0, cy-win):min(y1, cy+win), xx].nonzero()[0]
            yy = (max(y0, cy-win) + int(np.median(band))) if len(band) else cy
            pts.append([round(xx / W, 4), round(yy / H, 4)])
        if len(pts) >= 4: curves.append({"kind": "skirt_tier", "pts2d": pts})

elif MODE == "hair":
    # cabelo = topo/laterais da cabeca-ombro. strands = linhas ~verticais
    y0 = int(H * 0.04); y1 = int(H * 0.42)
    ver = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25)))
    cols = []
    win = max(6, W // 26)
    x = 0
    while x < W:
        seg = ver[y0:y1, x:x+win]
        if seg.sum() > (y1 - y0) * 0.12 * 255:
            cols.append(x + win // 2)
        x += win
    for cx in cols:
        pts = []
        for yy in range(y0, y1, max(3, (y1 - y0) // 18)):
            band = ver[yy, max(0, cx-win):min(W, cx+win)].nonzero()[0]
            xx = (max(0, cx-win) + int(np.median(band))) if len(band) else cx
            if m[yy, min(W-1, xx)] == 0: continue
            pts.append([round(xx / W, 4), round(yy / H, 4)])
        if len(pts) >= 4: curves.append({"kind": "hair_strand", "pts2d": pts})
else:
    raise SystemExit("mode = skirt | hair")

json.dump({"image_size": [W, H], "mode": MODE, "curves": curves}, open(OUT, "w"), indent=1)
print(f"[trace] {MODE}: {len(curves)} curvas -> {OUT}")

if DBG:
    viz = im.copy()
    for c in curves:
        pts = np.array([[int(u*W), int(v*H)] for u, v in c["pts2d"]], np.int32)
        col = (0, 230, 60) if c["kind"] == "skirt_tier" else (60, 200, 255)
        cv2.polylines(viz, [pts], False, col, 2)
        for p in pts: cv2.circle(viz, tuple(p), 2, (0, 0, 255), -1)
    cv2.imwrite(DBG, viz)
    print(f"[trace] debug -> {DBG}")
