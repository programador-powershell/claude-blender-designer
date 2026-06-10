"""Revisao cv2 profissional: edge maps + overlay + edge density por faixa vertical.
Mede onde o render carece de linhas/camadas vs ref."""
import cv2, sys
import numpy as np

def silhouette_bbox(img, bg_thr=28):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    m = (g > bg_thr).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5,5), np.uint8))
    ys, xs = np.where(m > 0)
    return xs.min(), xs.max(), ys.min(), ys.max()

def norm_crop(img, H=1100):
    x0, x1, y0, y1 = silhouette_bbox(img)
    c = img[y0:y1+1, x0:x1+1]
    s = H / c.shape[0]
    return cv2.resize(c, (int(c.shape[1]*s), H))

def edges(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g = cv2.bilateralFilter(g, 7, 60, 60)
    return cv2.Canny(g, 40, 120)

ref_p, ren_p, out_prefix = sys.argv[1], sys.argv[2], sys.argv[3]
ref = norm_crop(cv2.imread(ref_p))
ren = norm_crop(cv2.imread(ren_p))
# centralizar horizontal: pad pra mesma largura
W = max(ref.shape[1], ren.shape[1])
def padw(i):
    d = W - i.shape[1]
    return cv2.copyMakeBorder(i, 0, 0, d//2, d-d//2, cv2.BORDER_CONSTANT)
ref, ren = padw(ref), padw(ren)
eref, eren = edges(ref), edges(ren)

# overlay: ref edges = vermelho, render edges = verde, ambos = amarelo
ov = np.zeros((1100, W, 3), np.uint8)
ov[..., 2] = eref
ov[..., 1] = eren
cv2.imwrite(f'{out_prefix}_edge_overlay.png', ov)

# edge density por faixa vertical (14 faixas) - so dentro da silhueta
bands = 14
zona = ['chapeu','cabeca','rosto/pescoco','ombros/busto','corpete','cintura',
        'saia tier1','saia tier2','saia tier3','hem/renda','joelho/meia',
        'canela/bota','bota baixa','pes']
print(f'{"faixa":<16}{"ref":>7}{"render":>8}{"ratio":>7}  diag')
for b in range(bands):
    y0, y1 = b*1100//bands, (b+1)*1100//bands
    dr = eref[y0:y1].mean()
    dn = eren[y0:y1].mean()
    ratio = dn/dr if dr > 0.5 else float('nan')
    diag = ''
    if dr > 2 and ratio < 0.45: diag = '<<< FALTA DETALHE'
    elif dr > 2 and ratio < 0.7: diag = '< pouco detalhe'
    z = zona[b] if b < len(zona) else f'faixa{b}'
    print(f'{z:<16}{dr:>7.1f}{dn:>8.1f}{ratio:>7.2f}  {diag}')

# lado a lado edges
sbs = np.concatenate([cv2.cvtColor(eref, cv2.COLOR_GRAY2BGR),
                      np.full((1100, 4, 3), 60, np.uint8),
                      cv2.cvtColor(eren, cv2.COLOR_GRAY2BGR)], axis=1)
cv2.imwrite(f'{out_prefix}_edges_sbs.png', sbs)
print('saved:', f'{out_prefix}_edge_overlay.png', f'{out_prefix}_edges_sbs.png')
