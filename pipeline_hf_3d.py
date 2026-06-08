# -*- coding: utf-8 -*-
"""Pipeline 3D automatico via HF Spaces (gradio_client).
Substitui Trellis2 ComfyUI. Por peca:
1. Florence crop -> upload HF Space
2. Space gera mesh (GLB)
3. Download GLB -> work/meshes_3d/<piece>.glb
4. Blender import + Armature + parent Alice_Base_Rig
5. Export pra work/glb_ue5/<piece>_ue5.glb

Spaces tentados em ordem (fallback se um cair):
- stabilityai/stable-fast-3d
- ashawkey/InstantMesh (HF)
- VAST-AI/TripoSR
"""
import os, sys, json, time, shutil, argparse, subprocess, tempfile, glob

ROOT = r"D:/Alice/tools/auto-rig-fix"
WORK = os.path.join(ROOT, "work")
LIVE = os.path.join(ROOT, "live")
BRIDGE = os.path.join(ROOT, "bridge_cmd.py")
FL_MASKS = os.path.join(WORK, "florence_masks")
MESH_DIR = os.path.join(WORK, "meshes_3d")
GLB_DIR = os.path.join(WORK, "glb_ue5")
REGISTRY = os.path.join(WORK, "manifests", "outfits_registry.json")
MANIFESTS = os.path.join(WORK, "manifests")
STATUS_FILE = os.path.join(WORK, "hf3d_status.json")

os.makedirs(MESH_DIR, exist_ok=True); os.makedirs(GLB_DIR, exist_ok=True)

def call_triposr(crop_path):
    """stabilityai/TripoSR: preprocess -> generate -> (obj, glb)."""
    from gradio_client import Client, handle_file
    c = Client("stabilityai/TripoSR")
    pre = c.predict(input_image=handle_file(crop_path), remove_background=True,
                    foreground_ratio=0.85, api_name="/preprocess")
    print(f"  [TripoSR] preprocess -> {pre}")
    obj_glb = c.predict(processed_image=handle_file(pre),
                         marching_cubes_resolution=256, api_name="/generate")
    print(f"  [TripoSR] generate -> {obj_glb}")
    if isinstance(obj_glb, (list, tuple)) and len(obj_glb) >= 2:
        return obj_glb[1]  # GLB is second output
    return None


def call_instantmesh(crop_path):
    """TencentARC/InstantMesh: preprocess -> mvs -> make3d -> (obj, glb)."""
    from gradio_client import Client, handle_file
    c = Client("TencentARC/InstantMesh")
    pre = c.predict(input_image=handle_file(crop_path),
                    do_remove_background=True, api_name="/preprocess")
    print(f"  [InstantMesh] preprocess done")
    pre_path = pre['path'] if isinstance(pre, dict) else pre
    mvs = c.predict(input_image=handle_file(pre_path),
                    sample_steps=75, sample_seed=42, api_name="/generate_mvs")
    print(f"  [InstantMesh] mvs done")
    obj_glb = c.predict(api_name="/make3d")
    print(f"  [InstantMesh] make3d -> {obj_glb}")
    if isinstance(obj_glb, (list, tuple)) and len(obj_glb) >= 2:
        return obj_glb[1]
    return None


SPACE_FUNCS = [
    ("stabilityai/TripoSR", call_triposr),
    ("TencentARC/InstantMesh", call_instantmesh),
]


def load_status():
    if os.path.exists(STATUS_FILE):
        return json.load(open(STATUS_FILE, encoding='utf-8'))
    return {"pieces": {}}


def save_status(st):
    json.dump(st, open(STATUS_FILE, 'w', encoding='utf-8'), indent=2)


def gen_mesh_hf(crop_path, out_name, max_tries=2):
    last_err = None
    for space_id, fn in SPACE_FUNCS:
        for attempt in range(1, max_tries+1):
            try:
                print(f"  [HF] {space_id} attempt {attempt}")
                glb_src = fn(crop_path)
                if glb_src and os.path.exists(glb_src):
                    dst = os.path.join(MESH_DIR, f"{out_name}.glb")
                    shutil.copy2(glb_src, dst)
                    print(f"  [HF OK] {space_id} -> {dst}")
                    return dst
                print(f"  [HF] no GLB output (got: {glb_src})")
            except Exception as e:
                last_err = str(e)
                print(f"  [HF err] {space_id}: {last_err[:200]}")
                time.sleep(3)
    print(f"  [HF FAIL] last_err: {last_err}")
    return None


def blender_import_attach_export(glb_path, piece_name, body='Alice_Base_Body',
                                  armature='Alice_Base_Rig'):
    """Import GLB + rename + Armature + parent + Export pra UE5."""
    ue5_glb = os.path.join(GLB_DIR, f"{piece_name}_ue5.glb").replace('\\','/')
    glb_path = glb_path.replace('\\','/')
    script = f"""
import bpy, os
glb = r'{glb_path}'
name = '{piece_name}'
bpy.ops.import_scene.gltf(filepath=glb)
imported = [o for o in bpy.context.selected_objects if o.type == 'MESH']
if not imported:
    print('NO_MESH_IMPORTED'); raise SystemExit
obj = imported[0]
obj.name = f'PA_Mesh_{{name}}'
arm = bpy.data.objects.get('{armature}')
if arm:
    am = obj.modifiers.new('PA_arm','ARMATURE'); am.object = arm
    obj.parent = arm
    obj.matrix_parent_inverse = arm.matrix_world.inverted()
# Move to outer collection if exists
col = bpy.data.collections.get('PA_04_GARMENT_OUTER')
if col:
    for c in obj.users_collection: c.objects.unlink(obj)
    col.objects.link(obj)
print('IMPORTED:', obj.name)
# Export pra UE5
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True); bpy.context.view_layer.objects.active = obj
bpy.ops.export_scene.gltf(filepath=r'{ue5_glb}', use_selection=True,
                           export_format='GLB', export_apply=True,
                           export_materials='EXPORT')
print('EXPORTED:', r'{ue5_glb}')
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script); p = f.name
    try:
        env = os.environ.copy(); env['PYTHONIOENCODING'] = 'utf-8'
        r = subprocess.run([sys.executable, BRIDGE, '--file', p],
                            capture_output=True, text=True, timeout=240, env=env)
        sys.stdout.write(r.stdout)
        if r.returncode: sys.stderr.write(r.stderr); return None
        return ue5_glb if os.path.exists(ue5_glb) else None
    finally:
        try: os.unlink(p)
        except: pass


def run_piece(piece_name):
    st = load_status()
    if st['pieces'].get(piece_name, {}).get('done'):
        print(f"  [SKIP] {piece_name} done"); return True
    crop = os.path.join(FL_MASKS, f"{piece_name}_crop.png")
    if not os.path.exists(crop):
        print(f"  [SKIP] sem crop {crop}"); return False
    print(f"\n========== {piece_name} ==========")
    # Try local cached mesh first
    cached = os.path.join(MESH_DIR, f"{piece_name}.glb")
    if os.path.exists(cached):
        print(f"  [cached] {cached}"); glb = cached
    else:
        glb = gen_mesh_hf(crop, piece_name)
        if not glb: return False
    ue5 = blender_import_attach_export(glb, piece_name)
    ok = ue5 is not None
    st['pieces'][piece_name] = {"done": ok, "glb": glb, "ue5": ue5}
    save_status(st)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--piece', default=None)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--outfit', default='chapeleiro')
    a = ap.parse_args()
    if a.piece:
        sys.exit(0 if run_piece(a.piece) else 1)
    if a.all:
        reg = json.load(open(REGISTRY, encoding='utf-8'))
        cfg = reg['outfits'][a.outfit]
        m = json.load(open(os.path.join(MANIFESTS, cfg['manifest']), encoding='utf-8'))
        ok, fail = [], []
        for p in sorted(m['pieces'], key=lambda x: x['order']):
            (ok if run_piece(p['name']) else fail).append(p['name'])
        print(f"\n===== REPORT =====\nOK: {len(ok)} | FAIL: {len(fail)}")
        for n in ok: print(f"  + {n}")
        for n in fail: print(f"  - {n}")
        return
    ap.error("precisa --piece or --all")


if __name__ == '__main__':
    main()
