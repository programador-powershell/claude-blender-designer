# -*- coding: utf-8 -*-
"""6-aspect cv2 inspectors per piece: overlay_red, overlay_green, lines,
shadows, textures, colors. Compose grid PNG + numeric scores."""
import os, cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont
from skimage.metrics import structural_similarity as ssim


def _load_pair(render_path, ref_path):
    r = cv2.imread(render_path); f = cv2.imread(ref_path)
    if r is None or f is None: return None, None
    H = min(r.shape[0], f.shape[0]); W = min(r.shape[1], f.shape[1])
    return cv2.resize(r, (W, H)), cv2.resize(f, (W, H))


def overlay_red_green(render, ref):
    """Red = mismatch zone, Green = match zone."""
    diff = cv2.absdiff(render, ref).max(axis=2)
    red = render.copy(); red[diff > 40] = [0, 0, 255]
    green = ref.copy(); green[diff < 20] = [0, 255, 0]
    return red, green, float(np.mean(diff))


def lines_inspector(render, ref):
    """Canny edges both + edge_overlap score."""
    rg = cv2.cvtColor(render, cv2.COLOR_BGR2GRAY)
    fg = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)
    er = cv2.Canny(rg, 50, 150); ef = cv2.Canny(fg, 50, 150)
    er_c = cv2.cvtColor(er, cv2.COLOR_GRAY2BGR)
    ef_c = cv2.cvtColor(ef, cv2.COLOR_GRAY2BGR)
    overlap = float((er & ef).sum()) / max(ef.sum(), 1)
    # combine: render edges blue, ref edges yellow, overlap white
    combo = np.zeros_like(render)
    combo[er > 0] = [255, 0, 0]
    combo[ef > 0] = [0, 255, 255]
    combo[(er > 0) & (ef > 0)] = [255, 255, 255]
    return combo, round(overlap, 3)


def shadow_inspector(render, ref):
    """HSV V-channel comparison (lighting/shadow distribution)."""
    rh = cv2.cvtColor(render, cv2.COLOR_BGR2HSV)
    fh = cv2.cvtColor(ref, cv2.COLOR_BGR2HSV)
    rv = rh[:,:,2]; fv = fh[:,:,2]
    diff = cv2.absdiff(rv, fv)
    rv_c = cv2.applyColorMap(rv, cv2.COLORMAP_BONE)
    fv_c = cv2.applyColorMap(fv, cv2.COLORMAP_BONE)
    combo = np.hstack([rv_c, fv_c])
    shadow_match = 1.0 - float(np.mean(diff)) / 255.0
    return combo, round(shadow_match, 3)


def texture_inspector(render, ref):
    """LBP-like local std (texture roughness map) + similarity."""
    rg = cv2.cvtColor(render, cv2.COLOR_BGR2GRAY).astype(np.float32)
    fg = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY).astype(np.float32)
    k = 9
    rm = cv2.blur(rg, (k,k)); fm = cv2.blur(fg, (k,k))
    rs = np.sqrt(np.clip(cv2.blur(rg*rg, (k,k)) - rm*rm, 0, None))
    fs = np.sqrt(np.clip(cv2.blur(fg*fg, (k,k)) - fm*fm, 0, None))
    rs_n = np.clip(rs*4, 0, 255).astype(np.uint8)
    fs_n = np.clip(fs*4, 0, 255).astype(np.uint8)
    diff = cv2.absdiff(rs_n, fs_n)
    txt_match = 1.0 - float(np.mean(diff)) / 255.0
    combo = np.hstack([cv2.cvtColor(rs_n, cv2.COLOR_GRAY2BGR),
                       cv2.cvtColor(fs_n, cv2.COLOR_GRAY2BGR)])
    return combo, round(txt_match, 3)


def color_inspector(render, ref):
    """Color histogram correlation + dominant hue diff."""
    hist_r = cv2.calcHist([render], [0,1,2], None, [8,8,8], [0,256]*3)
    hist_f = cv2.calcHist([ref], [0,1,2], None, [8,8,8], [0,256]*3)
    cv2.normalize(hist_r, hist_r); cv2.normalize(hist_f, hist_f)
    corr = cv2.compareHist(hist_r, hist_f, cv2.HISTCMP_CORREL)
    # Dominant hue
    rh = cv2.cvtColor(render, cv2.COLOR_BGR2HSV)[:,:,0]
    fh = cv2.cvtColor(ref, cv2.COLOR_BGR2HSV)[:,:,0]
    dom_r = int(np.median(rh)); dom_f = int(np.median(fh))
    palette = np.zeros((100, 400, 3), dtype=np.uint8)
    palette[:,:200] = cv2.cvtColor(np.uint8([[[dom_r,255,255]]]), cv2.COLOR_HSV2BGR)[0,0]
    palette[:,200:] = cv2.cvtColor(np.uint8([[[dom_f,255,255]]]), cv2.COLOR_HSV2BGR)[0,0]
    cv2.putText(palette, f"render h={dom_r}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)
    cv2.putText(palette, f"ref h={dom_f}", (210, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)
    return palette, round(corr, 3), abs(dom_r - dom_f)


def lights_inspector(render, ref):
    """Brightness histogram + bright/dark area ratio."""
    rg = cv2.cvtColor(render, cv2.COLOR_BGR2GRAY)
    fg = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)
    r_bright = float(np.mean(rg > 200))
    f_bright = float(np.mean(fg > 200))
    r_dark = float(np.mean(rg < 50))
    f_dark = float(np.mean(fg < 50))
    light_match = 1.0 - (abs(r_bright-f_bright) + abs(r_dark-f_dark))/2
    # histogram side-by-side
    hist_r = cv2.calcHist([rg], [0], None, [64], [0,256]).flatten()
    hist_f = cv2.calcHist([fg], [0], None, [64], [0,256]).flatten()
    hist_r = hist_r/max(hist_r.max(),1); hist_f = hist_f/max(hist_f.max(),1)
    H, W = 200, 400
    img = np.zeros((H, W, 3), dtype=np.uint8)
    for i, (v_r, v_f) in enumerate(zip(hist_r, hist_f)):
        x = int(i * W / 64)
        cv2.line(img, (x, H), (x, int(H - v_r * H)), (255, 100, 100), 2)
        cv2.line(img, (x+2, H), (x+2, int(H - v_f * H)), (100, 255, 100), 1)
    cv2.putText(img, f"R bright={r_bright:.2f} dark={r_dark:.2f}", (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,100,100), 1)
    cv2.putText(img, f"F bright={f_bright:.2f} dark={f_dark:.2f}", (5, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100,255,100), 1)
    return img, round(light_match, 3)


def run_all_inspectors(render_path, ref_path, out_dir, piece):
    """Run all 6 + ssim + compose grid PNG. Returns dict with scores + paths."""
    os.makedirs(out_dir, exist_ok=True)
    r, f = _load_pair(render_path, ref_path)
    if r is None: return None
    H, W = r.shape[:2]
    ssim_s = ssim(cv2.cvtColor(r, cv2.COLOR_BGR2GRAY), cv2.cvtColor(f, cv2.COLOR_BGR2GRAY))
    red, green, mean_diff = overlay_red_green(r, f)
    lines, edge_ov = lines_inspector(r, f)
    shadow, shadow_m = shadow_inspector(r, f)
    texture, tex_m = texture_inspector(r, f)
    palette, color_corr, hue_diff = color_inspector(r, f)
    lights, light_m = lights_inspector(r, f)
    paths = {}
    for name, img in [('overlay_red', red), ('overlay_green', green),
                       ('lines', lines), ('shadow', shadow),
                       ('texture', texture), ('palette', palette), ('lights', lights)]:
        p = os.path.join(out_dir, f"{piece}_{name}.png")
        cv2.imwrite(p, img); paths[name] = p
    # Compose 3x3 grid (resize each to same dims)
    cell_W, cell_H = 300, 300
    def to_cell(img):
        h, w = img.shape[:2]
        if w != cell_W or h != cell_H:
            img = cv2.resize(img, (cell_W, cell_H))
        return img
    cells = [
        (r, "render"), (f, "ref"), (red, "overlay_red"),
        (green, "overlay_green"), (lines, "lines"), (shadow, "shadow"),
        (texture, "texture"), (palette, "palette"), (lights, "lights")
    ]
    grid = np.zeros((cell_H*3, cell_W*3, 3), dtype=np.uint8)
    for i, (img, name) in enumerate(cells):
        row, col = i // 3, i % 3
        c = to_cell(img)
        cv2.putText(c, name, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 2)
        grid[row*cell_H:(row+1)*cell_H, col*cell_W:(col+1)*cell_W] = c
    grid_p = os.path.join(out_dir, f"{piece}_INSPECTORS_GRID.png")
    cv2.imwrite(grid_p, grid)
    return {
        "ssim": round(ssim_s, 3),
        "mean_diff": round(mean_diff, 1),
        "edge_overlap": edge_ov,
        "shadow_match": shadow_m,
        "texture_match": tex_m,
        "color_corr": color_corr,
        "hue_diff": hue_diff,
        "light_match": light_m,
        "paths": paths,
        "grid": grid_p
    }
