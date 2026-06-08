# -*- coding: utf-8 -*-
"""Post-process por peca:
1. Decimate raw mesh -> lowpoly target_tris (default 5000)
2. Smart UV Project (auto unwrap)
3. Bake vertex colors -> texture 1024
4. cv2 upscale 1024 -> 4096 Lanczos
5. Apply texture to material (Principled BSDF Base Color)
6. Cleanup: remove non-manifold + smooth shading
7. Re-export GLB com texture embedded

Output: work/glb_ue5_processed/<piece>_processed.glb
"""
import os, sys, json, subprocess, tempfile, argparse, glob
import cv2, numpy as np

ROOT = r"D:/Alice/tools/auto-rig-fix"
WORK = os.path.join(ROOT, "work")
BRIDGE = os.path.join(ROOT, "bridge_cmd.py")
GLB_IN = os.path.join(WORK, "meshes_3d")
GLB_OUT = os.path.join(WORK, "glb_ue5_processed")
TEX_DIR = os.path.join(WORK, "textures_4k")
os.makedirs(GLB_OUT, exist_ok=True); os.makedirs(TEX_DIR, exist_ok=True)


def blender_process(glb_in, piece_name, target_tris=5000, tex_size=1024):
    tex_path = os.path.join(TEX_DIR, f"{piece_name}_1k.png").replace('\\','/')
    glb_out = os.path.join(GLB_OUT, f"{piece_name}_processed.glb").replace('\\','/')
    glb_in = glb_in.replace('\\','/')
    script = f"""
import bpy, bmesh, math
# Clean scene (keep only Alice_Base_*)
for o in list(bpy.data.objects):
    if o.name.startswith('PA_Proc_'): bpy.data.objects.remove(o, do_unlink=True)

# Import
prev = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=r'{glb_in}')
imported = [o for o in bpy.data.objects if o not in prev and o.type == 'MESH']
if not imported:
    print('NO_MESH'); raise SystemExit
obj = imported[0]
obj.name = 'PA_Proc_{piece_name}'
bpy.context.view_layer.objects.active = obj
bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True)

# 1. Decimate -> lowpoly
n_tris = len(obj.data.polygons)
ratio = min(1.0, {target_tris} / max(n_tris, 1))
if ratio < 1.0:
    dec = obj.modifiers.new('Dec','DECIMATE'); dec.ratio = ratio
    bpy.ops.object.modifier_apply(modifier='Dec')
print(f'decimate {{n_tris}} -> {{len(obj.data.polygons)}} tris ratio={{ratio:.3f}}')

# 2. UV unwrap (cube_project: works headless, sem non-manifold delete)
bpy.context.view_layer.objects.active = obj
bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
try: bpy.ops.uv.cube_project(cube_size=2.0)
except Exception as e: print(f'cube_project fail: {{e}}')
bpy.ops.object.mode_set(mode='OBJECT')
print(f'after UV: {{len(obj.data.polygons)}} faces, {{len(obj.data.vertices)}} verts')

# 3. Bake vertex colors -> texture
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'GPU' if bpy.context.preferences.addons.get('cycles') else 'CPU'
sc.cycles.samples = 32
# Create texture image
img_name = f'tex_{piece_name}'
img = bpy.data.images.get(img_name)
if img: bpy.data.images.remove(img)
img = bpy.data.images.new(img_name, width={tex_size}, height={tex_size}, alpha=False)
# Material w/ texture node + vertex color source
mat = bpy.data.materials.new(f'mat_{piece_name}')
mat.use_nodes = True
nt = mat.node_tree
for n in list(nt.nodes): nt.nodes.remove(n)
out = nt.nodes.new('ShaderNodeOutputMaterial')
bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
vc_node = nt.nodes.new('ShaderNodeVertexColor')
# Connect vertex color -> bsdf base color (for bake source)
nt.links.new(vc_node.outputs['Color'], bsdf.inputs['Base Color'])
nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
# Add image texture node (target for bake)
tex_node = nt.nodes.new('ShaderNodeTexImage')
tex_node.image = img
tex_node.select = True; nt.nodes.active = tex_node
# Clear old materials
obj.data.materials.clear()
obj.data.materials.append(mat)
# Bake
bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True)
bpy.context.view_layer.objects.active = obj
try:
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={{'COLOR'}})
    img.filepath_raw = r'{tex_path}'
    img.file_format = 'PNG'
    img.save()
    print(f'baked + saved {tex_path}')
except Exception as e:
    print(f'bake err: {{e}}')

# 4. Smooth shading
bpy.ops.object.shade_smooth()

# 5. Reconnect material: tex_image -> base color (replace vertex_color)
for link in list(nt.links):
    if link.to_socket == bsdf.inputs['Base Color']: nt.links.remove(link)
nt.links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])

# Save tex_size info pra upscale externo
print(f'TEX_PATH:{tex_path}')

# Export
bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=r'{glb_out}', use_selection=True,
                           export_format='GLB', export_apply=True,
                           export_materials='EXPORT', export_image_format='AUTO')
print(f'EXPORTED:{glb_out}')
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script); p = f.name
    try:
        env = os.environ.copy(); env['PYTHONIOENCODING'] = 'utf-8'
        r = subprocess.run([sys.executable, BRIDGE, '--file', p],
                            capture_output=True, text=True, timeout=600, env=env)
        sys.stdout.write(r.stdout[-2000:])
        if r.returncode: sys.stderr.write(r.stderr); return None
        return {"glb": glb_out if os.path.exists(glb_out) else None,
                "tex_1k": tex_path if os.path.exists(tex_path) else None}
    finally:
        try: os.unlink(p)
        except: pass


def upscale_to_4k(tex_1k_path, piece_name):
    """cv2 Lanczos upscale 1024 -> 4096."""
    if not os.path.exists(tex_1k_path): return None
    img = cv2.imread(tex_1k_path)
    if img is None: return None
    img_4k = cv2.resize(img, (4096, 4096), interpolation=cv2.INTER_LANCZOS4)
    out = os.path.join(TEX_DIR, f"{piece_name}_4k.png")
    cv2.imwrite(out, img_4k, [cv2.IMWRITE_PNG_COMPRESSION, 6])
    return out


def process_piece(piece_name):
    glb_in = os.path.join(GLB_IN, f"{piece_name}.glb")
    if not os.path.exists(glb_in):
        print(f"  [SKIP] sem GLB raw {glb_in}"); return False
    print(f"\n========== POST-PROCESS {piece_name} ==========")
    r = blender_process(glb_in, piece_name, target_tris=5000, tex_size=1024)
    if not r or not r.get('glb'):
        print(f"  [ERR] blender process fail"); return False
    print(f"  GLB processed: {r['glb']}")
    if r.get('tex_1k'):
        tex_4k = upscale_to_4k(r['tex_1k'], piece_name)
        if tex_4k:
            print(f"  TEX 4K upscaled: {tex_4k}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--piece', default=None)
    ap.add_argument('--all', action='store_true')
    a = ap.parse_args()
    if a.piece:
        sys.exit(0 if process_piece(a.piece) else 1)
    if a.all:
        glbs = sorted(glob.glob(os.path.join(GLB_IN, "*.glb")))
        ok, fail = [], []
        for g in glbs:
            name = os.path.splitext(os.path.basename(g))[0]
            (ok if process_piece(name) else fail).append(name)
        print(f"\n===== REPORT POST-PROCESS =====")
        print(f"OK: {len(ok)} | FAIL: {len(fail)}")
        for n in ok: print(f"  + {n}")
        for n in fail: print(f"  - {n}")
        return
    ap.error("--piece or --all required")


if __name__ == '__main__':
    main()
