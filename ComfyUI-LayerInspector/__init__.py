# -*- coding: utf-8 -*-
"""
ComfyUI-LayerInspector — 9 nodes especializados pra dissecar uma layer de arte 2D
e produzir JSON spec consumido pelo Blender game_builder.

Cada node retorna IMAGE + JSON (string) com dados estruturados:
- LinesExtractor    : Canny + Hough -> JSON {edges_count, edges_density, lines:[{x1,y1,x2,y2}]}
- ShadowExtractor   : HSV V baixo -> JSON {shadow_map_path, shadow_pct, shadow_centroid}
- TextureExtractor  : high-pass -> JSON {texture_map_path, hf_energy}
- OverlayRed        : pinta contornos vermelhos do REF
- OverlayGreen      : pinta bordas verdes do RENDER
- GridOverlay       : grid label A-J / 1-10 + cellsize px
- ColorPalette      : kmeans dominant N -> JSON {palette:[[r,g,b,pct],...]}
- CurveTracer       : skeleton + Hilditch -> JSON {curves:[{points:[[x,y],...], length}]}
- DepthEstimator    : MiDaS-small (opcional) -> JSON {depth_min, depth_max, depth_map_path}

Usado pelo orchestrator pipeline_layer_inspector.py que itera por layer da arte.
"""
import os, json
import numpy as np

try:
    import torch
except Exception:
    torch = None

try:
    import cv2
except Exception:
    cv2 = None


def _img_to_np(image_tensor):
    """ComfyUI IMAGE tensor (B,H,W,3) float [0,1] -> numpy uint8 BGR"""
    if torch is None: raise RuntimeError("torch missing")
    arr = (image_tensor[0].cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR) if cv2 is not None else arr[..., ::-1]

def _np_to_img(arr_bgr):
    """numpy uint8 BGR -> ComfyUI IMAGE tensor (1,H,W,3) float [0,1]"""
    if cv2 is not None:
        rgb = cv2.cvtColor(arr_bgr, cv2.COLOR_BGR2RGB)
    else:
        rgb = arr_bgr[..., ::-1]
    t = torch.from_numpy(rgb.astype(np.float32) / 255.0).unsqueeze(0)
    return t


# ---------------------------------------------------------------------------
# 1. LinesExtractor — Canny + Hough
# ---------------------------------------------------------------------------
class LinesExtractor:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "image": ("IMAGE",),
            "canny_low": ("INT", {"default": 50, "min": 1, "max": 500}),
            "canny_high": ("INT", {"default": 150, "min": 1, "max": 500}),
            "hough_threshold": ("INT", {"default": 50, "min": 1, "max": 500}),
            "min_line_length": ("INT", {"default": 30, "min": 1, "max": 2000}),
            "max_line_gap": ("INT", {"default": 10, "min": 0, "max": 500}),
        }}
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("lines_overlay", "spec_json")
    FUNCTION = "process"
    CATEGORY = "LayerInspector"

    def process(self, image, canny_low, canny_high, hough_threshold,
                min_line_length, max_line_gap):
        bgr = _img_to_np(image)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, canny_low, canny_high)
        out = bgr.copy()
        lines_list = []
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, hough_threshold,
                                minLineLength=min_line_length, maxLineGap=max_line_gap)
        if lines is not None:
            for ln in lines:
                x1, y1, x2, y2 = ln[0].tolist()
                cv2.line(out, (x1, y1), (x2, y2), (0, 255, 255), 1)
                lines_list.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2,
                                   "len": float(((x2-x1)**2+(y2-y1)**2)**0.5)})
        density = float((edges > 0).sum()) / edges.size
        spec = {"edges_count": int((edges > 0).sum()),
                "edges_density": round(density, 4),
                "lines": lines_list[:500],
                "hough_total": len(lines_list)}
        return (_np_to_img(out), json.dumps(spec))


# ---------------------------------------------------------------------------
# 2. ShadowExtractor — HSV V baixo
# ---------------------------------------------------------------------------
class ShadowExtractor:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "image": ("IMAGE",),
            "value_threshold": ("INT", {"default": 80, "min": 0, "max": 255}),
            "saturation_max": ("INT", {"default": 255, "min": 0, "max": 255}),
        }}
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("shadow_map", "spec_json")
    FUNCTION = "process"
    CATEGORY = "LayerInspector"

    def process(self, image, value_threshold, saturation_max):
        bgr = _img_to_np(image)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        shadow_mask = (hsv[:, :, 2] < value_threshold) & (hsv[:, :, 1] <= saturation_max)
        out = np.zeros_like(bgr)
        out[shadow_mask] = (40, 0, 80)  # roxo
        ys, xs = np.where(shadow_mask)
        cx, cy = (int(xs.mean()), int(ys.mean())) if len(xs) else (0, 0)
        pct = float(shadow_mask.sum()) / shadow_mask.size
        spec = {"shadow_pct": round(pct, 4),
                "shadow_centroid": [cx, cy],
                "shadow_pixels": int(shadow_mask.sum())}
        return (_np_to_img(out), json.dumps(spec))


# ---------------------------------------------------------------------------
# 3. TextureExtractor — high-pass
# ---------------------------------------------------------------------------
class TextureExtractor:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "image": ("IMAGE",),
            "blur_radius": ("INT", {"default": 9, "min": 1, "max": 99}),
            "boost": ("FLOAT", {"default": 2.0, "min": 0.1, "max": 10.0}),
        }}
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("texture_map", "spec_json")
    FUNCTION = "process"
    CATEGORY = "LayerInspector"

    def process(self, image, blur_radius, boost):
        bgr = _img_to_np(image)
        k = blur_radius if blur_radius % 2 == 1 else blur_radius + 1
        blurred = cv2.GaussianBlur(bgr, (k, k), 0)
        hf = cv2.subtract(bgr, blurred).astype(np.float32) * boost + 128
        hf = hf.clip(0, 255).astype(np.uint8)
        gray = cv2.cvtColor(hf, cv2.COLOR_BGR2GRAY)
        energy = float(((gray.astype(np.float32) - 128) ** 2).mean())
        spec = {"hf_energy": round(energy, 3),
                "blur_radius": k, "boost": boost}
        return (_np_to_img(hf), json.dumps(spec))


# ---------------------------------------------------------------------------
# 4. OverlayRed — REF contour
# ---------------------------------------------------------------------------
class OverlayRed:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "image": ("IMAGE",),
            "alpha": ("FLOAT", {"default": 0.6, "min": 0.0, "max": 1.0}),
        }}
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("overlay", "spec_json")
    FUNCTION = "process"
    CATEGORY = "LayerInspector"

    def process(self, image, alpha):
        bgr = _img_to_np(image)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 40, 120)
        out = bgr.copy()
        red_mask = edges > 0
        out[red_mask] = (out[red_mask] * (1 - alpha) +
                         np.array([0, 0, 255]) * alpha).astype(np.uint8)
        spec = {"red_pixels": int(red_mask.sum()), "alpha": alpha}
        return (_np_to_img(out), json.dumps(spec))


# ---------------------------------------------------------------------------
# 5. OverlayGreen — MODEL edge
# ---------------------------------------------------------------------------
class OverlayGreen:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "image": ("IMAGE",),
            "alpha": ("FLOAT", {"default": 0.6, "min": 0.0, "max": 1.0}),
        }}
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("overlay", "spec_json")
    FUNCTION = "process"
    CATEGORY = "LayerInspector"

    def process(self, image, alpha):
        bgr = _img_to_np(image)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 40, 120)
        out = bgr.copy()
        gmask = edges > 0
        out[gmask] = (out[gmask] * (1 - alpha) +
                      np.array([0, 200, 0]) * alpha).astype(np.uint8)
        spec = {"green_pixels": int(gmask.sum()), "alpha": alpha}
        return (_np_to_img(out), json.dumps(spec))


# ---------------------------------------------------------------------------
# 6. GridOverlay — A-J / 1-10
# ---------------------------------------------------------------------------
class GridOverlay:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "image": ("IMAGE",),
            "cols": ("INT", {"default": 10, "min": 2, "max": 26}),
            "rows": ("INT", {"default": 10, "min": 2, "max": 99}),
            "thickness": ("INT", {"default": 1, "min": 1, "max": 5}),
        }}
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("grid", "spec_json")
    FUNCTION = "process"
    CATEGORY = "LayerInspector"

    def process(self, image, cols, rows, thickness):
        bgr = _img_to_np(image).copy()
        h, w = bgr.shape[:2]
        cw, rh = w // cols, h // rows
        color = (0, 255, 255)
        for c in range(1, cols):
            cv2.line(bgr, (c*cw, 0), (c*cw, h), color, thickness)
        for r in range(1, rows):
            cv2.line(bgr, (0, r*rh), (w, r*rh), color, thickness)
        # labels
        font = cv2.FONT_HERSHEY_SIMPLEX
        for c in range(cols):
            cv2.putText(bgr, chr(ord('A')+c), (c*cw+4, 16), font, 0.4, color, 1)
        for r in range(rows):
            cv2.putText(bgr, str(r+1), (4, r*rh+16), font, 0.4, color, 1)
        spec = {"cols": cols, "rows": rows, "cellsize_px": [cw, rh]}
        return (_np_to_img(bgr), json.dumps(spec))


# ---------------------------------------------------------------------------
# 7. ColorPalette — kmeans dominant
# ---------------------------------------------------------------------------
class ColorPalette:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "image": ("IMAGE",),
            "n_colors": ("INT", {"default": 8, "min": 2, "max": 32}),
            "mask_bg": ("BOOLEAN", {"default": True}),
        }}
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("palette_swatches", "spec_json")
    FUNCTION = "process"
    CATEGORY = "LayerInspector"

    def process(self, image, n_colors, mask_bg):
        bgr = _img_to_np(image)
        flat = bgr.reshape(-1, 3).astype(np.float32)
        if mask_bg:
            # drop white/black backgrounds
            br = flat.mean(axis=1)
            flat = flat[(br > 10) & (br < 245)]
            if flat.size == 0: flat = bgr.reshape(-1, 3).astype(np.float32)
        # OpenCV kmeans
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
        _, labels, centers = cv2.kmeans(flat, n_colors, None, criteria, 5, cv2.KMEANS_PP_CENTERS)
        centers = centers.astype(np.uint8)
        counts = np.bincount(labels.flatten(), minlength=n_colors)
        order = np.argsort(-counts)
        palette = []
        for i in order:
            b, g, r = centers[i].tolist()
            palette.append({"rgb": [int(r), int(g), int(b)],
                            "hex": f"#{r:02x}{g:02x}{b:02x}",
                            "pct": round(float(counts[i]) / counts.sum(), 4)})
        # render swatches
        sw_h, sw_w = 80, 80 * n_colors
        sw = np.zeros((sw_h, sw_w, 3), np.uint8)
        for i, p in enumerate(palette):
            sw[:, i*80:(i+1)*80] = (p["rgb"][2], p["rgb"][1], p["rgb"][0])
            cv2.putText(sw, f"{p['pct']*100:.1f}%", (i*80+4, sw_h-8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,255), 1)
        spec = {"palette": palette}
        return (_np_to_img(sw), json.dumps(spec))


# ---------------------------------------------------------------------------
# 8. CurveTracer — skeleton via distance transform
# ---------------------------------------------------------------------------
class CurveTracer:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "image": ("IMAGE",),
            "binarize_thresh": ("INT", {"default": 128, "min": 0, "max": 255}),
            "min_curve_len": ("INT", {"default": 20, "min": 2, "max": 5000}),
        }}
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("curves_overlay", "spec_json")
    FUNCTION = "process"
    CATEGORY = "LayerInspector"

    def process(self, image, binarize_thresh, min_curve_len):
        bgr = _img_to_np(image)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        _, binar = cv2.threshold(gray, binarize_thresh, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(binar, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_KCOS)
        out = bgr.copy()
        curves = []
        for c in contours:
            if cv2.arcLength(c, False) < min_curve_len: continue
            pts = c.reshape(-1, 2).tolist()
            curves.append({"points": pts[:200], "length": float(cv2.arcLength(c, False))})
            cv2.polylines(out, [c], False, (0, 255, 0), 1)
        spec = {"curves": curves[:200], "curve_count": len(curves)}
        return (_np_to_img(out), json.dumps(spec))


# ---------------------------------------------------------------------------
# 9. DepthEstimator — MiDaS-small (offline if available)
# ---------------------------------------------------------------------------
class DepthEstimator:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "image": ("IMAGE",),
        }}
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("depth_map", "spec_json")
    FUNCTION = "process"
    CATEGORY = "LayerInspector"

    def process(self, image):
        # Fallback simples (sem modelo): laplaciano + gaussian -> profundidade aprox por defocus
        # MiDaS pode ser plugado depois.
        bgr = _img_to_np(image)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
        # invert + normalize: brighter = closer assumption
        d = 255.0 - cv2.GaussianBlur(gray, (15, 15), 0)
        d = (d - d.min()) / max(d.max() - d.min(), 1e-5) * 255.0
        depth = d.astype(np.uint8)
        depth_bgr = cv2.applyColorMap(depth, cv2.COLORMAP_INFERNO)
        spec = {"depth_min": float(d.min()),
                "depth_max": float(d.max()),
                "depth_mean": float(d.mean()),
                "method": "fallback_blur_inverse"}
        return (_np_to_img(depth_bgr), json.dumps(spec))


NODE_CLASS_MAPPINGS = {
    "LinesExtractor": LinesExtractor,
    "ShadowExtractor": ShadowExtractor,
    "TextureExtractor": TextureExtractor,
    "OverlayRed": OverlayRed,
    "OverlayGreen": OverlayGreen,
    "GridOverlay": GridOverlay,
    "ColorPalette": ColorPalette,
    "CurveTracer": CurveTracer,
    "DepthEstimator": DepthEstimator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LinesExtractor":   "Layer ► Lines (Canny+Hough)",
    "ShadowExtractor":  "Layer ► Shadow (HSV V)",
    "TextureExtractor": "Layer ► Texture (high-pass)",
    "OverlayRed":       "Layer ► Overlay Red (REF contour)",
    "OverlayGreen":     "Layer ► Overlay Green (MODEL edge)",
    "GridOverlay":      "Layer ► Grid (A-J / 1-10)",
    "ColorPalette":     "Layer ► Color Palette (kmeans)",
    "CurveTracer":      "Layer ► Curve Tracer",
    "DepthEstimator":   "Layer ► Depth (fallback)",
}
