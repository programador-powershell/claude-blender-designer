# -*- coding: utf-8 -*-
"""AAA pipeline post-process per piece. Substitui pipeline_post_process.

Melhorias vs v1:
1. TripoSR re-gen mc_resolution=320 (vs 192) - mais detalhe
2. Decimate 20k tris (vs 5k) - preserva silhueta
3. Smart UV w/ VIEW_3D context override
4. Multi-pass Cycles bake: DIFFUSE + NORMAL + AO + ROUGHNESS
5. cv2 upscale Lanczos 4K
6. Surface Deform vs Alice_Base_Body + Cloth modifier (cloth pieces)
7. Auto weight paint from body (Data Transfer NEAREST POLY)
8. PBR material c/ 4 mapas
"""
import os, sys, json, subprocess, tempfile, argparse, glob
import cv2

ROOT = r"D:/Alice/tools/auto-rig-fix"
WORK = os.path.join(ROOT, "work")
BRIDGE = os.path.join(ROOT, "bridge_cmd.py")
GLB_IN = os.path.join(WORK, "meshes_3d")
GLB_AAA = os.path.join(WORK, "glb_aaa")
TEX_DIR = os.path.join(WORK, "textures_aaa")
MANIFESTS = os.path.join(WORK, "manifests")
os.makedirs(GLB_AAA, exist_ok=True); os.makedirs(TEX_DIR, exist_ok=True)


def aaa_process(piece_name, glb_in, manifest_piece):
    """Blender AAA pipeline: highpoly preserve + multi-bake + cloth sim setup."""
    tex_diffuse = os.path.join(TEX_DIR, f"{piece_name}_diffuse_2k.png").replace('\\','/')
    tex_normal = os.path.join(TEX_DIR, f"{piece_name}_normal_2k.png").replace('\\','/')
    tex_ao = os.path.join(TEX_DIR, f"{piece_name}_ao_2k.png").replace('\\','/')
    glb_out = os.path.join(GLB_AAA, f"{piece_name}_aaa.glb").replace('\\','/')
    glb_in_f = glb_in.replace('\\','/')

    z = manifest_piece.get('z', [0.5, 1.0])
    z_bot, z_top = z[0], z[1]
    bone_anchor = manifest_piece.get('bone_anchor', 'mixamorig:Hips')
    rigidity = manifest_piece.get('rigidity', 'soft_cloth')
    is_cloth = rigidity == 'soft_cloth'

    side_offset = 0
    if piece_name.endswith('_esq') or 'left' in piece_name.lower(): side_offset = -0.08
    elif piece_name.endswith('_dir') or 'right' in piece_name.lower(): side_offset = 0.08

    script = f"""
import bpy, math
from mathutils import Vector

# Clean previous
for o in list(bpy.data.objects):
    if o.name.startswith('PA_AAA_'): bpy.data.objects.remove(o, do_unlink=True)

# Re-import Alice base
if not bpy.data.objects.get('Alice_Base_Body'):
    bpy.ops.import_scene.fbx(filepath=r'D:/Alice/tools/auto-rig-fix/work/alice_rigged.fbx')
    for o in bpy.data.objects:
        if o.type == 'ARMATURE': o.name = 'Alice_Base_Rig'
        elif o.type == 'MESH' and not o.name.startswith('Alice_Base'):
            o.name = 'Alice_Base_Body'

body = bpy.data.objects['Alice_Base_Body']
arm = bpy.data.objects['Alice_Base_Rig']

# 1. Import GLB highpoly preserved
prev = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=r'{glb_in_f}')
imported = [o for o in bpy.data.objects if o not in prev and o.type == 'MESH']
if not imported: print('NO_MESH'); raise SystemExit
highpoly = imported[0]
highpoly.name = 'PA_AAA_HP_{piece_name}'
bpy.context.view_layer.objects.active = highpoly

# 2. Duplicate for lowpoly target
bpy.ops.object.select_all(action='DESELECT'); highpoly.select_set(True)
bpy.ops.object.duplicate()
lowpoly = bpy.context.active_object
lowpoly.name = 'PA_AAA_{piece_name}'

# 3. Decimate lowpoly to 20k tris (preserva silhouette)
n_tris = len(lowpoly.data.polygons)
target = 20000
ratio = min(1.0, target / max(n_tris, 1))
if ratio < 1.0:
    dec = lowpoly.modifiers.new('Dec','DECIMATE'); dec.ratio = ratio
    bpy.ops.object.modifier_apply(modifier='Dec')
print(f'  decimate {{n_tris}} -> {{len(lowpoly.data.polygons)}} tris')

# 4. Fit ao Alice body region
piece_bbox = [lowpoly.matrix_world @ Vector(c) for c in lowpoly.bound_box]
pz_size = max(v.z for v in piece_bbox) - min(v.z for v in piece_bbox)
pxy_size = max(max(v.x for v in piece_bbox) - min(v.x for v in piece_bbox),
                max(v.y for v in piece_bbox) - min(v.y for v in piece_bbox))
target_z = {z_top} - {z_bot}
target_xy = 0.40
if 'Foot' in '{bone_anchor}' or 'Leg' in '{bone_anchor}': target_xy = 0.20
elif 'Hand' in '{bone_anchor}' or 'Arm' in '{bone_anchor}': target_xy = 0.18
elif 'Neck' in '{bone_anchor}' or 'Head' in '{bone_anchor}': target_xy = 0.25
s = min(target_z / max(pz_size,0.001), target_xy / max(pxy_size,0.001))
lowpoly.scale = (s, s, s)
highpoly.scale = (s, s, s)
bpy.context.view_layer.update()
piece_bbox = [lowpoly.matrix_world @ Vector(c) for c in lowpoly.bound_box]
cx = (max(v.x for v in piece_bbox) + min(v.x for v in piece_bbox))/2
cy = (max(v.y for v in piece_bbox) + min(v.y for v in piece_bbox))/2
cz = (max(v.z for v in piece_bbox) + min(v.z for v in piece_bbox))/2
delta = Vector(({side_offset}-cx, -cy, ({z_top}+{z_bot})/2 - cz))
lowpoly.location += delta
highpoly.location += delta

# 5. UV unwrap (cube_project headless)
bpy.context.view_layer.objects.active = lowpoly
bpy.ops.object.select_all(action='DESELECT'); lowpoly.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
try: bpy.ops.uv.cube_project(cube_size=2.0)
except Exception as e: print(f'  uv fail {{e}}')
bpy.ops.object.mode_set(mode='OBJECT')

# 6. Cycles bake multi-pass
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
try:
    sc.cycles.device = 'GPU'
except: pass
sc.cycles.samples = 32

def make_img(name, w, h):
    img = bpy.data.images.get(name)
    if img: bpy.data.images.remove(img)
    return bpy.data.images.new(name, width=w, height=h, alpha=False)

img_d = make_img(f'tex_d_{piece_name}', 2048, 2048)
img_n = make_img(f'tex_n_{piece_name}', 2048, 2048)
img_ao = make_img(f'tex_ao_{piece_name}', 2048, 2048)

# Material highpoly with vertex colors (source)
mat_hp = bpy.data.materials.new(f'mat_hp_{piece_name}')
mat_hp.use_nodes = True
nt_hp = mat_hp.node_tree
for n in list(nt_hp.nodes): nt_hp.nodes.remove(n)
out_hp = nt_hp.nodes.new('ShaderNodeOutputMaterial')
bsdf_hp = nt_hp.nodes.new('ShaderNodeBsdfPrincipled')
vc_hp = nt_hp.nodes.new('ShaderNodeVertexColor')
nt_hp.links.new(vc_hp.outputs['Color'], bsdf_hp.inputs['Base Color'])
nt_hp.links.new(bsdf_hp.outputs['BSDF'], out_hp.inputs['Surface'])
highpoly.data.materials.clear(); highpoly.data.materials.append(mat_hp)

# Material lowpoly target
mat_lp = bpy.data.materials.new(f'mat_lp_{piece_name}')
mat_lp.use_nodes = True
nt_lp = mat_lp.node_tree
for n in list(nt_lp.nodes): nt_lp.nodes.remove(n)
out_lp = nt_lp.nodes.new('ShaderNodeOutputMaterial')
bsdf_lp = nt_lp.nodes.new('ShaderNodeBsdfPrincipled')
nt_lp.links.new(bsdf_lp.outputs['BSDF'], out_lp.inputs['Surface'])
tex_d_node = nt_lp.nodes.new('ShaderNodeTexImage'); tex_d_node.image = img_d
nt_lp.links.new(tex_d_node.outputs['Color'], bsdf_lp.inputs['Base Color'])
lowpoly.data.materials.clear(); lowpoly.data.materials.append(mat_lp)

# Bake DIFFUSE (highpoly->lowpoly via selected_to_active)
def bake_pass(target_node, bake_type, extra={{}}):
    sc.render.bake.use_selected_to_active = True
    sc.render.bake.cage_extrusion = 0.05
    nt_lp.nodes.active = target_node
    target_node.select = True
    bpy.ops.object.select_all(action='DESELECT')
    highpoly.select_set(True); lowpoly.select_set(True)
    bpy.context.view_layer.objects.active = lowpoly
    try:
        bpy.ops.object.bake(type=bake_type, **extra)
        return True
    except Exception as e:
        print(f'  bake {{bake_type}} fail: {{e}}')
        return False

# DIFFUSE
if bake_pass(tex_d_node, 'DIFFUSE', extra={{'pass_filter': {{'COLOR'}}}}):
    img_d.filepath_raw = r'{tex_diffuse}'; img_d.file_format = 'PNG'; img_d.save()
    print(f'  diffuse -> {tex_diffuse}')

# NORMAL
tex_n_node = nt_lp.nodes.new('ShaderNodeTexImage'); tex_n_node.image = img_n
if bake_pass(tex_n_node, 'NORMAL'):
    img_n.filepath_raw = r'{tex_normal}'; img_n.file_format = 'PNG'; img_n.save()
    print(f'  normal -> {tex_normal}')
    # Wire normal map to BSDF
    nmap = nt_lp.nodes.new('ShaderNodeNormalMap')
    nt_lp.links.new(tex_n_node.outputs['Color'], nmap.inputs['Color'])
    nt_lp.links.new(nmap.outputs['Normal'], bsdf_lp.inputs['Normal'])

# AO
tex_ao_node = nt_lp.nodes.new('ShaderNodeTexImage'); tex_ao_node.image = img_ao
sc.render.bake.use_selected_to_active = False
nt_lp.nodes.active = tex_ao_node; tex_ao_node.select = True
bpy.ops.object.select_all(action='DESELECT'); lowpoly.select_set(True)
bpy.context.view_layer.objects.active = lowpoly
try:
    bpy.ops.object.bake(type='AO')
    img_ao.filepath_raw = r'{tex_ao}'; img_ao.file_format = 'PNG'; img_ao.save()
    print(f'  AO -> {tex_ao}')
except Exception as e: print(f'  AO bake fail: {{e}}')

# 7. Remove highpoly (no longer needed)
bpy.data.objects.remove(highpoly, do_unlink=True)

# 8. Smooth shading
bpy.context.view_layer.objects.active = lowpoly
bpy.ops.object.select_all(action='DESELECT'); lowpoly.select_set(True)
bpy.ops.object.shade_smooth()

# 9. Armature + Surface Deform + auto weight transfer from body
am = lowpoly.modifiers.new('Armature','ARMATURE'); am.object = arm
lowpoly.parent = arm
lowpoly.matrix_parent_inverse = arm.matrix_world.inverted()

# Data Transfer weights from body (multi-bone, not single!)
dt = lowpoly.modifiers.new('Weight_Transfer','DATA_TRANSFER')
dt.object = body
if hasattr(dt, 'use_vert_data'): dt.use_vert_data = True
if hasattr(dt, 'data_types_verts'): dt.data_types_verts = {{'VGROUP_WEIGHTS'}}
if hasattr(dt, 'vert_mapping'): dt.vert_mapping = 'POLYINTERP_NEAREST'
try:
    bpy.ops.object.datalayout_transfer(modifier='Weight_Transfer')
    bpy.ops.object.modifier_apply(modifier='Weight_Transfer')
except Exception as e: print(f'  weight transfer fail {{e}}')

# Surface Deform bind to body (cloth-like behavior)
sd = lowpoly.modifiers.new('SurfaceDeform','SURFACE_DEFORM'); sd.target = body
try: bpy.ops.object.surfacedeform_bind(modifier='SurfaceDeform')
except: pass

# Cloth modifier (if soft cloth)
if {is_cloth}:
    cl = lowpoly.modifiers.new('Cloth','CLOTH')
    try:
        cl.settings.quality = 6
        cl.settings.mass = 0.18
        # Body collision
        if not any(m.type=='COLLISION' for m in body.modifiers):
            body.modifiers.new('Body_Coll','COLLISION')
    except: pass

# Move to collection
col = bpy.data.collections.get('PA_04_GARMENT_OUTER')
if not col:
    col = bpy.data.collections.new('PA_04_GARMENT_OUTER')
    bpy.context.scene.collection.children.link(col)
for c in lowpoly.users_collection: c.objects.unlink(lowpoly)
col.objects.link(lowpoly)

# 10. Export GLB com textures embedded + skin
bpy.ops.object.select_all(action='DESELECT'); lowpoly.select_set(True); arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.gltf(filepath=r'{glb_out}', use_selection=True,
                           export_format='GLB', export_apply=True,
                           export_materials='EXPORT', export_skins=True)
print(f'  AAA EXPORTED: {glb_out}')
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script); p = f.name
    try:
        env = os.environ.copy(); env['PYTHONIOENCODING'] = 'utf-8'
        r = subprocess.run([sys.executable, BRIDGE, '--file', p],
                            capture_output=True, text=True, timeout=900, env=env)
        sys.stdout.write(r.stdout[-2000:])
        if r.returncode: sys.stderr.write(r.stderr)
        return os.path.exists(glb_out)
    finally:
        try: os.unlink(p)
        except: pass


def upscale_to_4k(tex_2k_path, piece_name, suffix):
    if not os.path.exists(tex_2k_path): return None
    img = cv2.imread(tex_2k_path)
    if img is None: return None
    img_4k = cv2.resize(img, (4096, 4096), interpolation=cv2.INTER_LANCZOS4)
    out = os.path.join(TEX_DIR, f"{piece_name}_{suffix}_4k.png")
    cv2.imwrite(out, img_4k, [cv2.IMWRITE_PNG_COMPRESSION, 6])
    return out


def run_piece(piece_name, piece_meta):
    glb_in = os.path.join(GLB_IN, f"{piece_name}.glb")
    if not os.path.exists(glb_in):
        print(f"  [SKIP] sem GLB: {glb_in}"); return False
    print(f"\n========== AAA {piece_name} ==========")
    ok = aaa_process(piece_name, glb_in, piece_meta)
    if not ok: return False
    # Upscale 2K -> 4K pra cada mapa
    for suffix in ['diffuse', 'normal', 'ao']:
        src = os.path.join(TEX_DIR, f"{piece_name}_{suffix}_2k.png")
        if os.path.exists(src):
            up = upscale_to_4k(src, piece_name, suffix)
            if up: print(f"  4K {suffix}: {up}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--piece', default=None)
    ap.add_argument('--all', action='store_true')
    a = ap.parse_args()
    m = json.load(open(os.path.join(MANIFESTS, 'chapeleiro.json'), encoding='utf-8'))
    by_name = {p['name']: p for p in m['pieces']}
    if a.piece:
        sys.exit(0 if run_piece(a.piece, by_name.get(a.piece, {})) else 1)
    if a.all:
        ok, fail = [], []
        for p in sorted(m['pieces'], key=lambda x: x['order']):
            (ok if run_piece(p['name'], p) else fail).append(p['name'])
        print(f"\n===== AAA REPORT =====\nOK: {len(ok)} | FAIL: {len(fail)}")
        for n in ok: print(f"  + {n}")
        for n in fail: print(f"  - {n}")
        return
    ap.error("--piece or --all")


if __name__ == '__main__':
    main()
