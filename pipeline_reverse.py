# -*- coding: utf-8 -*-
"""Pipeline INVERSO: parte de GLB Alice JA vestida + limpa+polir+rigga.

vs TripoSR (image->mesh per piece):
- TripoSR gera blobs sem coerencia garment
- Reverse parte de mesh REAL Alice chapeleiro -> limpa + UV + bake + rig + export

Steps:
1. Import GLB Alice vestida (work/agent/chapeleiro/out.glb)
2. Remove lixo (Icosphere etc)
3. Normalize altura ao 1.70m
4. Fix armature scale to mesh
5. Decimate dress 199k -> 50k preserva silhouette
6. Smart UV (ja tem mas refresh)
7. Cycles bake AO + Normal pra detalhe shading
8. cv2 upscale 2K -> 4K
9. Smooth shading
10. Weight transfer corpo -> dress (auto multi-bone)
11. Surface Deform + Cloth + Collision body
12. Export GLB UE5 ready
"""
import os, sys, json, subprocess, tempfile, argparse
import cv2

ROOT = r"D:/Alice/tools/auto-rig-fix"
WORK = os.path.join(ROOT, "work")
BRIDGE = os.path.join(ROOT, "bridge_cmd.py")
SRC_GLB = os.path.join(WORK, "agent", "chapeleiro", "out.glb")
OUT_GLB = os.path.join(WORK, "alice_chapeleiro_AAA.glb")
TEX_DIR = os.path.join(WORK, "textures_reverse")
os.makedirs(TEX_DIR, exist_ok=True)


def blender_reverse(src_glb, out_glb):
    tex_diffuse = os.path.join(TEX_DIR, "alice_chapeleiro_diffuse_2k.png").replace('\\','/')
    tex_ao = os.path.join(TEX_DIR, "alice_chapeleiro_ao_2k.png").replace('\\','/')
    tex_normal = os.path.join(TEX_DIR, "alice_chapeleiro_normal_2k.png").replace('\\','/')
    src_glb_f = src_glb.replace('\\','/')
    out_glb_f = out_glb.replace('\\','/')
    script = f"""
import bpy, math
from mathutils import Vector

# 1. Clean scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

# 2. Import GLB Alice vestida
bpy.ops.import_scene.gltf(filepath=r'{src_glb_f}')
print(f'imported: {{[o.name for o in bpy.data.objects]}}')

# 3. Remove lixo (Icosphere etc)
for o in list(bpy.data.objects):
    if o.type == 'MESH' and o.name not in ('AliceDress', 'Corpo'):
        bpy.data.objects.remove(o, do_unlink=True)

dress = bpy.data.objects.get('AliceDress')
body = bpy.data.objects.get('Corpo')
arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
if not dress or not body or not arm:
    print('MISSING_OBJECTS'); raise SystemExit

# 4. Normalize altura ao 1.70m (currently 2.70m, scale 0.63)
all_zs = []
for m in [dress, body]:
    for v in m.data.vertices:
        all_zs.append((m.matrix_world @ v.co).z)
z_min = min(all_zs); z_max = max(all_zs)
current_h = z_max - z_min
scale_factor = 1.70 / current_h
print(f'  normalize {{current_h:.3f}}m -> 1.70m (scale {{scale_factor:.3f}})')

# Scale armature (parent) - all children scale with it
arm.scale = (scale_factor, scale_factor, scale_factor)
bpy.context.view_layer.update()
# Shift Z down so feet at floor
all_zs = []
for m in [dress, body]:
    for v in m.data.vertices:
        all_zs.append((m.matrix_world @ v.co).z)
z_min_new = min(all_zs)
arm.location.z -= z_min_new
bpy.context.view_layer.update()
# Apply transforms
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for m in [dress, body]:
    bpy.ops.object.select_all(action='DESELECT')
    m.select_set(True); bpy.context.view_layer.objects.active = m
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
arm.name = 'Alice_Base_Rig'
body.name = 'Alice_Base_Body'
dress.name = 'PA_AliceChapeleiroDress'

# 5. Decimate dress 199k -> ~50k tris
n_tris = len(dress.data.polygons)
target_tris = 50000
ratio = min(1.0, target_tris / max(n_tris, 1))
if ratio < 1.0:
    bpy.context.view_layer.objects.active = dress
    dec = dress.modifiers.new('Dec','DECIMATE'); dec.ratio = ratio
    bpy.ops.object.modifier_apply(modifier='Dec')
print(f'  decimate {{n_tris}} -> {{len(dress.data.polygons)}} tris')

# 6. Smart UV (refresh)
bpy.context.view_layer.objects.active = dress
bpy.ops.object.select_all(action='DESELECT'); dress.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
try: bpy.ops.uv.cube_project(cube_size=2.0)
except Exception as e: print(f'  uv fail {{e}}')
bpy.ops.object.mode_set(mode='OBJECT')

# 7. Cycles bake DIFFUSE + AO + NORMAL
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
try: sc.cycles.device = 'GPU'
except: pass
sc.cycles.samples = 32

def make_img(name, w=2048, h=2048):
    img = bpy.data.images.get(name)
    if img: bpy.data.images.remove(img)
    return bpy.data.images.new(name, width=w, height=h, alpha=False)

img_d = make_img('dress_diffuse')
img_ao = make_img('dress_ao')
img_n = make_img('dress_normal')

# Wire material w/ existing texture + bake target
mat = dress.data.materials[0] if dress.data.materials else None
if not mat:
    mat = bpy.data.materials.new('dress_mat'); mat.use_nodes = True
    dress.data.materials.append(mat)
nt = mat.node_tree
# Find existing image texture node (from imported GLB)
src_tex_node = next((n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image), None)
print(f'  src texture: {{src_tex_node.image.name if src_tex_node else "none"}}')

# Add target image texture node
tex_d_node = nt.nodes.new('ShaderNodeTexImage'); tex_d_node.image = img_d
tex_d_node.select = True; nt.nodes.active = tex_d_node
bpy.ops.object.select_all(action='DESELECT'); dress.select_set(True)
bpy.context.view_layer.objects.active = dress
try:
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={{'COLOR'}})
    img_d.filepath_raw = r'{tex_diffuse}'; img_d.file_format = 'PNG'; img_d.save()
    print(f'  diffuse -> {tex_diffuse}')
except Exception as e: print(f'  diffuse bake fail: {{e}}')

# AO
tex_ao_node = nt.nodes.new('ShaderNodeTexImage'); tex_ao_node.image = img_ao
tex_ao_node.select = True; nt.nodes.active = tex_ao_node
try:
    bpy.ops.object.bake(type='AO')
    img_ao.filepath_raw = r'{tex_ao}'; img_ao.file_format = 'PNG'; img_ao.save()
    print(f'  AO -> {tex_ao}')
except Exception as e: print(f'  AO fail: {{e}}')

# 8. Smooth shading
bpy.ops.object.shade_smooth()

# 9. Weight transfer corpo -> dress (multi-bone)
if 'PA_Weight_Transfer' not in [m.name for m in dress.modifiers]:
    dt = dress.modifiers.new('PA_Weight_Transfer','DATA_TRANSFER')
    dt.object = body
    if hasattr(dt, 'use_vert_data'): dt.use_vert_data = True
    if hasattr(dt, 'data_types_verts'): dt.data_types_verts = {{'VGROUP_WEIGHTS'}}
    if hasattr(dt, 'vert_mapping'): dt.vert_mapping = 'POLYINTERP_NEAREST'
    try:
        bpy.ops.object.datalayout_transfer(modifier='PA_Weight_Transfer')
        bpy.ops.object.modifier_apply(modifier='PA_Weight_Transfer')
    except Exception as e: print(f'  weight transfer fail: {{e}}')

# 10. Surface Deform bind
sd = dress.modifiers.new('PA_SurfaceDeform','SURFACE_DEFORM'); sd.target = body
try: bpy.ops.object.surfacedeform_bind(modifier='PA_SurfaceDeform')
except: pass

# 11. Body Collision
if not any(m.type=='COLLISION' for m in body.modifiers):
    body.modifiers.new('Body_Coll','COLLISION')

# 12. Armature mod
if not any(m.type=='ARMATURE' for m in dress.modifiers):
    am = dress.modifiers.new('PA_Arm','ARMATURE'); am.object = arm

# Parent dress + body to arm
dress.parent = arm; body.parent = arm
dress.matrix_parent_inverse = arm.matrix_world.inverted()
body.matrix_parent_inverse = arm.matrix_world.inverted()

# 13. Export GLB UE5
bpy.ops.object.select_all(action='DESELECT')
dress.select_set(True); body.select_set(True); arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.gltf(filepath=r'{out_glb_f}', use_selection=True,
                           export_format='GLB', export_apply=True,
                           export_materials='EXPORT', export_skins=True)
print(f'EXPORTED: {out_glb_f}')
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script); p = f.name
    try:
        env = os.environ.copy(); env['PYTHONIOENCODING'] = 'utf-8'
        r = subprocess.run([sys.executable, BRIDGE, '--file', p],
                            capture_output=True, text=True, timeout=900, env=env)
        sys.stdout.write(r.stdout[-3000:])
        if r.returncode: sys.stderr.write(r.stderr)
        return os.path.exists(out_glb)
    finally:
        try: os.unlink(p)
        except: pass


def upscale_4k(src_2k_path, out_path):
    if not os.path.exists(src_2k_path): return None
    img = cv2.imread(src_2k_path)
    if img is None: return None
    img_4k = cv2.resize(img, (4096, 4096), interpolation=cv2.INTER_LANCZOS4)
    cv2.imwrite(out_path, img_4k, [cv2.IMWRITE_PNG_COMPRESSION, 6])
    return out_path


def main():
    print(f"\n{'='*60}\nREVERSE PIPELINE: {SRC_GLB}\n{'='*60}")
    if not os.path.exists(SRC_GLB):
        print(f"ERR src no existe: {SRC_GLB}"); sys.exit(1)
    ok = blender_reverse(SRC_GLB, OUT_GLB)
    if not ok:
        print(f"FAIL"); sys.exit(1)
    print(f"\nOK: {OUT_GLB}")
    # 4K upscale
    for suffix in ['diffuse', 'ao']:
        src = os.path.join(TEX_DIR, f"alice_chapeleiro_{suffix}_2k.png")
        out_4k = os.path.join(TEX_DIR, f"alice_chapeleiro_{suffix}_4k.png")
        if upscale_4k(src, out_4k):
            print(f"  4K {suffix}: {out_4k}")


if __name__ == '__main__':
    main()
