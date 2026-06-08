# -*- coding: utf-8 -*-
"""TripoSR local inference - image -> GLB.
Substitui HF Space (sem rate limit). CPU mode (5-10min/peca) ou CUDA se disponivel."""
import os, sys, argparse
sys.path.insert(0, r"D:/Alice/tools/auto-rig-fix/TripoSR")

import torch
from PIL import Image
import rembg
import numpy as np

from tsr.system import TSR
from tsr.utils import remove_background, resize_foreground

DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
MODEL = None
REMBG_SESSION = None
OUT_DIR = r"D:/Alice/tools/auto-rig-fix/work/meshes_3d"


def get_model():
    global MODEL
    if MODEL is None:
        print(f"[TripoSR] loading model on {DEVICE}...")
        MODEL = TSR.from_pretrained("stabilityai/TripoSR",
                                     config_name="config.yaml",
                                     weight_name="model.ckpt")
        MODEL.renderer.set_chunk_size(8192)
        MODEL.to(DEVICE)
    return MODEL


def get_rembg():
    global REMBG_SESSION
    if REMBG_SESSION is None:
        REMBG_SESSION = rembg.new_session()
    return REMBG_SESSION


def image_to_mesh(image_path, out_name, mc_resolution=192, fg_ratio=0.85):
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"[TripoSR] {image_path} -> {out_name}.glb")
    model = get_model()
    rembg_session = get_rembg()
    img = Image.open(image_path)
    if img.mode == 'RGBA' and (np.array(img)[:,:,3] < 255).any():
        pass  # already has alpha
    else:
        img = remove_background(img.convert('RGB'), rembg_session)
    img = resize_foreground(img, fg_ratio)
    img_arr = np.array(img).astype(np.float32) / 255.0
    if img_arr.shape[-1] == 4:
        img_arr = img_arr[..., :3] * img_arr[..., 3:4] + (1 - img_arr[..., 3:4]) * 0.5
    img = Image.fromarray((img_arr * 255).astype(np.uint8))
    with torch.no_grad():
        scene_codes = model([img], device=DEVICE)
    meshes = model.extract_mesh(scene_codes, has_vertex_color=True,
                                  resolution=mc_resolution)
    mesh = meshes[0]
    out = os.path.join(OUT_DIR, f"{out_name}.glb")
    mesh.export(out)
    print(f"[TripoSR] saved {out}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--image', required=True)
    ap.add_argument('--out-name', required=True)
    ap.add_argument('--resolution', type=int, default=192)
    a = ap.parse_args()
    r = image_to_mesh(a.image, a.out_name, mc_resolution=a.resolution)
    print(r)


if __name__ == '__main__':
    main()
