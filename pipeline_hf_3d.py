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
                                  armature='Alice_Base_Rig',
                                  z_bot=0.5, z_top=1.0, bone_anchor='mixamorig:Hips'):
    """Import GLB + FIT to Alice body region + Armature + Shrinkwrap + Export.
    z_bot/z_top = world Z range alvo do manifest.
    bone_anchor = Mixamo bone pra weight 1.0."""
    ue5_glb = os.path.join(GLB_DIR, f"{piece_name}_ue5.glb").replace('\\','/')
    glb_path = glb_path.replace('\\','/')
    script = f"""
import bpy, math
from mathutils import Vector
glb = r'{glb_path}'
name = '{piece_name}'
z_bot = {z_bot}; z_top = {z_top}
bone_anchor = '{bone_anchor}'

# 1. Import GLB
prev_objs = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=glb)
imported = [o for o in bpy.data.objects if o not in prev_objs and o.type == 'MESH']
if not imported:
    print('NO_MESH_IMPORTED'); raise SystemExit
obj = imported[0]
obj.name = f'PA_Mesh_{{name}}'

# 2. Get Alice body bounds + bone position
body_obj = bpy.data.objects.get('{body}')
arm = bpy.data.objects.get('{armature}')
if not body_obj or not arm:
    print('MISSING_BODY_OR_ARM'); raise SystemExit

# Body bbox world
body_verts_z = [(body_obj.matrix_world @ v.co).z for v in body_obj.data.vertices]
body_verts_x = [(body_obj.matrix_world @ v.co).x for v in body_obj.data.vertices]
body_verts_y = [(body_obj.matrix_world @ v.co).y for v in body_obj.data.vertices]
body_z_min, body_z_max = min(body_verts_z), max(body_verts_z)

# Bone world position
bone = arm.data.bones.get(bone_anchor)
if bone:
    bone_world = arm.matrix_world @ bone.head_local
else:
    bone_world = Vector((0, 0, (z_top + z_bot) / 2))

# 3. Scale piece pra fit z range
piece_bbox = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
piece_z_size = max(v.z for v in piece_bbox) - min(v.z for v in piece_bbox)
piece_xy_size = max(max(v.x for v in piece_bbox) - min(v.x for v in piece_bbox),
                     max(v.y for v in piece_bbox) - min(v.y for v in piece_bbox))
target_z_size = z_top - z_bot

# Estimate body horizontal width at this z (approx)
target_xy_size = 0.40  # waist ~40cm. Adjusted by region:
if 'Foot' in bone_anchor or 'Leg' in bone_anchor: target_xy_size = 0.20
elif 'Hand' in bone_anchor or 'Arm' in bone_anchor: target_xy_size = 0.18
elif 'Neck' in bone_anchor or 'Head' in bone_anchor: target_xy_size = 0.25

scale_z = target_z_size / max(piece_z_size, 0.001)
scale_xy = target_xy_size / max(piece_xy_size, 0.001)
# Use min scale pra evitar overshoot
scale_factor = min(scale_z, scale_xy)
obj.scale = (scale_factor, scale_factor, scale_factor)
bpy.context.view_layer.update()

# 4. Position: center XY = body center XY, center Z = midpoint manifest range
piece_bbox = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
piece_cx = (max(v.x for v in piece_bbox) + min(v.x for v in piece_bbox)) / 2
piece_cy = (max(v.y for v in piece_bbox) + min(v.y for v in piece_bbox)) / 2
piece_cz = (max(v.z for v in piece_bbox) + min(v.z for v in piece_bbox)) / 2

# Side offset por left/right
side_offset = 0
if name.endswith('_esq') or 'left' in name.lower(): side_offset = -0.08
elif name.endswith('_dir') or 'right' in name.lower(): side_offset = 0.08

target_cx = side_offset
target_cy = 0
target_cz = (z_bot + z_top) / 2
obj.location.x += target_cx - piece_cx
obj.location.y += target_cy - piece_cy
obj.location.z += target_cz - piece_cz
bpy.context.view_layer.update()

# 5. Add Shrinkwrap pra body
sw = obj.modifiers.new('PA_Body_Wrap','SHRINKWRAP')
sw.target = body_obj
sw.wrap_method = 'NEAREST_SURFACEPOINT'
sw.wrap_mode = 'OUTSIDE_SURFACE'
sw.offset = 0.005  # 5mm offset

# 6. Add Armature modifier + parent
am = obj.modifiers.new('PA_Armature','ARMATURE'); am.object = arm
obj.parent = arm
obj.matrix_parent_inverse = arm.matrix_world.inverted()

# 7. Vertex group + weight 1.0 ao bone anchor
vg = obj.vertex_groups.new(name=bone_anchor)
vg.add([v.index for v in obj.data.vertices], 1.0, 'REPLACE')

# 8. Move pra collection PA_04
col = bpy.data.collections.get('PA_04_GARMENT_OUTER')
if not col:
    col = bpy.data.collections.new('PA_04_GARMENT_OUTER')
    bpy.context.scene.collection.children.link(col)
for c in obj.users_collection: c.objects.unlink(obj)
col.objects.link(obj)

print(f'IMPORTED+FIT: {{obj.name}} scale={{scale_factor:.3f}} pos=({{target_cx:.2f}},{{target_cy:.2f}},{{target_cz:.2f}}) bone={{bone_anchor}}')

# 9. Export UE5 com modifiers applied
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True); bpy.context.view_layer.objects.active = obj
bpy.ops.export_scene.gltf(filepath=r'{ue5_glb}', use_selection=True,
                           export_format='GLB', export_apply=True,
                           export_materials='EXPORT', export_skins=True)
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


def run_piece(piece_name, piece_meta=None):
    st = load_status()
    if st['pieces'].get(piece_name, {}).get('done'):
        print(f"  [SKIP] {piece_name} done"); return True
    crop = os.path.join(FL_MASKS, f"{piece_name}_crop.png")
    if not os.path.exists(crop):
        print(f"  [SKIP] sem crop {crop}"); return False
    print(f"\n========== {piece_name} ==========")
    cached = os.path.join(MESH_DIR, f"{piece_name}.glb")
    if os.path.exists(cached):
        print(f"  [cached] {cached}"); glb = cached
    else:
        glb = gen_mesh_hf(crop, piece_name)
        if not glb: return False
    # Pega z+bone do manifest
    z_bot, z_top = 0.5, 1.0
    bone_anchor = 'mixamorig:Hips'
    if piece_meta:
        z = piece_meta.get('z', [0.5, 1.0])
        z_bot, z_top = z[0], z[1]
        bone_anchor = piece_meta.get('bone_anchor', bone_anchor)
    ue5 = blender_import_attach_export(glb, piece_name,
                                        z_bot=z_bot, z_top=z_top,
                                        bone_anchor=bone_anchor)
    ok = ue5 is not None
    st['pieces'][piece_name] = {"done": ok, "glb": glb, "ue5": ue5,
                                 "z": [z_bot, z_top], "bone": bone_anchor}
    save_status(st)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--piece', default=None)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--outfit', default='chapeleiro')
    a = ap.parse_args()
    reg = json.load(open(REGISTRY, encoding='utf-8'))
    cfg = reg['outfits'][a.outfit]
    m = json.load(open(os.path.join(MANIFESTS, cfg['manifest']), encoding='utf-8'))
    by_name = {p['name']: p for p in m['pieces']}
    if a.piece:
        sys.exit(0 if run_piece(a.piece, by_name.get(a.piece)) else 1)
    if a.all:
        ok, fail = [], []
        for p in sorted(m['pieces'], key=lambda x: x['order']):
            (ok if run_piece(p['name'], p) else fail).append(p['name'])
        print(f"\n===== REPORT =====\nOK: {len(ok)} | FAIL: {len(fail)}")
        for n in ok: print(f"  + {n}")
        for n in fail: print(f"  - {n}")
        return
    ap.error("precisa --piece or --all")


if __name__ == '__main__':
    main()
