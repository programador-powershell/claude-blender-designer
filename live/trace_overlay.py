# -*- coding: utf-8 -*-
"""trace_overlay — "desenhar por cima": linhas da ARTE (cv2 Canny) sobre o RENDER + grid.
Registra arte e render pela bbox da silhueta antes de sobrepor. Imperfeicao = VERMELHO
(arte) sem VERDE (modelo) por perto. Bate = AMARELO. cv2 (python ComfyUI).
  CLI: python trace_overlay.py <ref.png> <render.png> <out.png> [grid=12] [c1=35] [c2=110]
  API: make_overlay(ref_p, ren_p, out_p, grid=12) -> coverage_pct
"""
import cv2, numpy as np, sys

def _crop_to_content(img, thr=18):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, m = cv2.threshold(g, thr, 255, cv2.THRESH_BINARY)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    if n > 1:
        big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA])); ys, xs = np.where(lab == big)
    else:
        ys, xs = np.where(m > 0)
    if len(xs) == 0: return img
    p = 4
    return img[max(0,ys.min()-p):min(img.shape[0],ys.max()+p), max(0,xs.min()-p):min(img.shape[1],xs.max()+p)]

def _edges(img, c1, c2):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g = cv2.bilateralFilter(g, 5, 50, 50)
    return cv2.dilate(cv2.Canny(g, c1, c2), np.ones((2, 2), np.uint8))

def make_overlay(ref_p, ren_p, out_p, grid=12, c1=35, c2=110, size=900):
    ref, ren = cv2.imread(ref_p), cv2.imread(ren_p)
    if ref is None or ren is None: raise SystemExit("nao leu ref/render")
    ref = cv2.resize(_crop_to_content(ref), (size, size))
    ren = cv2.resize(_crop_to_content(ren), (size, size))
    eref, eren = _edges(ref, c1, c2), _edges(ren, c1, c2)
    base = (ren.astype(float) * 0.5).astype(np.uint8)
    base[eref > 0] = (0, 0, 255)                       # ARTE vermelho
    base[eren > 0] = (0, 255, 0)                       # MODELO verde
    base[(eref > 0) & (eren > 0)] = (0, 255, 255)      # bate amarelo
    for i in range(1, grid):
        x = size * i // grid; cv2.line(base, (x, 0), (x, size), (110, 110, 110), 1)
        y = size * i // grid; cv2.line(base, (0, y), (size, y), (110, 110, 110), 1)
    for i in range(grid):
        cv2.putText(base, chr(65+i), (size*i//grid+int(size*0.4/grid), 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255,220,0), 1)
        cv2.putText(base, str(i+1), (3, size*i//grid+int(size*0.6/grid)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255,220,0), 1)
    eren_d = cv2.dilate(eren, np.ones((7, 7), np.uint8))
    cov = 100 * int(((eref > 0) & (eren_d > 0)).sum()) // (int((eref > 0).sum()) or 1)
    cv2.imwrite(out_p, base)
    return cov

if __name__ == "__main__":
    a = sys.argv
    cov = make_overlay(a[1], a[2], a[3], int(a[4]) if len(a)>4 else 12,
                       int(a[5]) if len(a)>5 else 35, int(a[6]) if len(a)>6 else 110)
    print(f"[overlay] art=RED model=GREEN match=YELLOW cobertura={cov}% -> {a[3]}")
