# -*- coding: utf-8 -*-
"""Pipeline 3D generation chain per piece:
  Florence2 crop (ref image) ->
  Trellis2 (image->3D mesh + UV) ->
  [opcional Hunyuan3D refine lowpoly] ->
  Import Blender (.glb) -> cleanup + attach armature ->
  Export GLB pra UE5

Substitui BVH projection com mesh AI-generated REAL (nao curves placeholder).

Pre-req:
  ComfyUI custom_nodes:
    ComfyUI-Trellis2 (instalado E:/.../custom_nodes/)
    ComfyUI-Hunyuan3DWrapper (instalado)
"""
import os, sys, json, time, shutil, urllib.request, argparse, tempfile, subprocess
sys.path.insert(0, r"D:/Alice/tools/auto-rig-fix")
sys.path.insert(0, r"D:/Alice/tools/auto-rig-fix/live")

ROOT = r"D:/Alice/tools/auto-rig-fix"
WORK = os.path.join(ROOT, "work")
LIVE = os.path.join(ROOT, "live")
BRIDGE = os.path.join(ROOT, "bridge_cmd.py")
COMFY = "http://127.0.0.1:8188"
COMFY_IN = r"E:/ComfyUI_windows_portable/ComfyUI/input"
COMFY_OUT = r"E:/ComfyUI_windows_portable/ComfyUI/output"
FL_MASKS = os.path.join(WORK, "florence_masks")
MESH_DIR = os.path.join(WORK, "meshes_3d")
GLB_DIR = os.path.join(WORK, "glb_ue5")
TRELLIS_WF = r"E:/ComfyUI_windows_portable/ComfyUI/custom_nodes/ComfyUI-Trellis2/example_workflows/MeshOnly_LowPoly.json"

os.makedirs(MESH_DIR, exist_ok=True); os.makedirs(GLB_DIR, exist_ok=True)


def comfy_post(path, data):
    req = urllib.request.Request(COMFY+path, data=json.dumps(data).encode(),
                                  headers={"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=300).read())


def comfy_get(path):
    return json.loads(urllib.request.urlopen(COMFY+path, timeout=60).read())


def trellis2_image_to_mesh(image_path, out_name, workflow_path=TRELLIS_WF):
    """Run Trellis2 workflow: image -> .glb mesh."""
    if not os.path.exists(workflow_path):
        print(f"  [ERR] Trellis2 workflow nao existe: {workflow_path}")
        return None
    os.makedirs(COMFY_IN, exist_ok=True)
    name = os.path.basename(image_path)
    shutil.copy2(image_path, os.path.join(COMFY_IN, name))
    wf = json.load(open(workflow_path, encoding='utf-8'))
    # Patch LoadImage node to use our image
    for node_id, node in wf.items():
        if isinstance(node, dict) and node.get('class_type') == 'LoadImage':
            node['inputs']['image'] = name
        if isinstance(node, dict) and 'Save' in node.get('class_type','') and 'GLB' in node.get('class_type','').upper():
            node['inputs']['filename_prefix'] = f"trellis_{out_name}"
    # Strip non-node keys
    wf = {k:v for k,v in wf.items() if not k.startswith('_')}
    r = comfy_post("/prompt", {"prompt": wf, "client_id": f"trellis_{out_name}"})
    pid = r["prompt_id"]
    print(f"  [Trellis2] prompt_id={pid}")
    t0 = time.time()
    last_status = ""
    while time.time()-t0 < 1800:  # 30min max
        h = comfy_get(f"/history/{pid}")
        if pid in h:
            st = h[pid].get('status',{})
            if st.get('completed'): break
            if st.get('status_str')=='error':
                print(f"  [Trellis2 ERR] {st}"); return None
        time.sleep(10)
    # Find generated GLB
    glb_files = []
    for node_id, node_out in h[pid].get('outputs',{}).items():
        for fmt in ['gltf', 'glb']:
            if fmt in node_out:
                for g in node_out[fmt]:
                    glb_files.append(os.path.join(COMFY_OUT, g.get('subfolder',''), g['filename']))
    if not glb_files: print(f"  [Trellis2] no GLB output"); return None
    src = glb_files[0]
    dst = os.path.join(MESH_DIR, f"{out_name}.glb")
    shutil.copy2(src, dst)
    print(f"  [Trellis2] mesh -> {dst} ({time.time()-t0:.0f}s)")
    return dst


def blender_import_and_attach(glb_path, piece_name, attach_armature='Alice_Base_Rig'):
    """Import GLB no Blender + rename + attach armature."""
    script = f"""
import bpy
glb = r'{glb_path}'
name = '{piece_name}'
arm_name = '{attach_armature}'

bpy.ops.import_scene.gltf(filepath=glb)
imported = [o for o in bpy.context.selected_objects if o.type == 'MESH']
if not imported:
    print('NO_MESH_IMPORTED'); raise SystemExit
obj = imported[0]
obj.name = f'PA_Mesh_{{name}}'
# Move to collection PA_04_GARMENT_OUTER if exists
target_col = bpy.data.collections.get('PA_04_GARMENT_OUTER')
if target_col:
    for c in obj.users_collection: c.objects.unlink(obj)
    target_col.objects.link(obj)

# Attach armature
arm = bpy.data.objects.get(arm_name)
if arm:
    am = obj.modifiers.new('PA_arm','ARMATURE'); am.object = arm
    obj.parent = arm
    obj.matrix_parent_inverse = arm.matrix_world.inverted()

print('IMPORTED:', obj.name)
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script); p = f.name
    try:
        env = os.environ.copy(); env['PYTHONIOENCODING'] = 'utf-8'
        r = subprocess.run([sys.executable, BRIDGE, '--file', p],
                            capture_output=True, text=True, timeout=180, env=env)
        sys.stdout.write(r.stdout)
        if r.returncode: sys.stderr.write(r.stderr)
        return r.returncode == 0
    finally:
        try: os.unlink(p)
        except: pass


def blender_export_glb(piece_name, body_name='Alice_Base_Body'):
    """Export piece mesh as GLB para UE5."""
    out_glb = os.path.join(GLB_DIR, f"{piece_name}_ue5.glb")
    script = f"""
import bpy
name = 'PA_Mesh_{piece_name}'
obj = bpy.data.objects.get(name)
if not obj:
    print('NOT_FOUND', name); raise SystemExit
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True); bpy.context.view_layer.objects.active = obj
bpy.ops.export_scene.gltf(filepath=r'{out_glb}', use_selection=True, export_format='GLB',
                           export_apply=True, export_materials='EXPORT')
print('EXPORTED:', r'{out_glb}')
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script); p = f.name
    try:
        env = os.environ.copy(); env['PYTHONIOENCODING'] = 'utf-8'
        r = subprocess.run([sys.executable, BRIDGE, '--file', p],
                            capture_output=True, text=True, timeout=180, env=env)
        if r.returncode == 0: return out_glb
        sys.stderr.write(r.stderr); return None
    finally:
        try: os.unlink(p)
        except: pass


def run_piece(piece_name):
    """Chain Trellis2 -> Blender import -> UE5 export."""
    crop = os.path.join(FL_MASKS, f"{piece_name}_crop.png")
    if not os.path.exists(crop):
        print(f"  [SKIP] sem Florence crop pra {piece_name}: {crop}"); return False
    glb = trellis2_image_to_mesh(crop, piece_name)
    if not glb: return False
    if not blender_import_and_attach(glb, piece_name): return False
    ue5_glb = blender_export_glb(piece_name)
    if not ue5_glb: return False
    print(f"  CHAIN COMPLETE pra {piece_name}: {ue5_glb}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--piece', default=None)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--outfit', default='chapeleiro')
    a = ap.parse_args()

    if a.piece:
        ok = run_piece(a.piece); sys.exit(0 if ok else 1)
    if a.all:
        reg = json.load(open(os.path.join(WORK, "manifests", "outfits_registry.json"), encoding='utf-8'))
        cfg = reg['outfits'][a.outfit]
        m = json.load(open(os.path.join(WORK, "manifests", cfg['manifest']), encoding='utf-8'))
        ok_list, fail_list = [], []
        for p in sorted(m['pieces'], key=lambda x: x['order']):
            print(f"\n{'='*60}\n3D CHAIN: {p['name']}\n{'='*60}")
            ok = run_piece(p['name'])
            (ok_list if ok else fail_list).append(p['name'])
        print(f"\n===== REPORT 3D CHAIN =====\nOK: {len(ok_list)} | FAIL: {len(fail_list)}")
        for n in ok_list: print(f"  + {n}")
        for n in fail_list: print(f"  - {n}")
        return
    ap.error('precisa --piece or --all')


if __name__ == '__main__':
    main()
