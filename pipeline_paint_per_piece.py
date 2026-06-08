# -*- coding: utf-8 -*-
"""Pinta dress mesh por peça baseado em Florence crops.

Strategy:
1. Para cada peça do manifest: sample cor dominante do Florence crop
2. Map manifest piece -> bone_anchor -> cor RGB
3. No dress mesh: cada vertex tem multi-bone weights; pega bone dominante
4. Atribui vertex color via lookup bone -> piece -> color
5. Bake vertex colors -> diffuse texture
6. Material w/ texture
7. Re-render
"""
import os, sys, json, subprocess, tempfile
import cv2
import numpy as np
from PIL import Image

ROOT = r"D:/Alice/tools/auto-rig-fix"
WORK = os.path.join(ROOT, "work")
BRIDGE = os.path.join(ROOT, "bridge_cmd.py")
GLB_IN = os.path.join(WORK, "alice_chapeleiro_AAA.glb")
GLB_OUT = os.path.join(WORK, "alice_chapeleiro_PAINTED.glb")
FL_MASKS = os.path.join(WORK, "florence_masks")
MANIFEST = os.path.join(WORK, "manifests", "chapeleiro.json")
TEX_DIR = os.path.join(WORK, "textures_painted")
os.makedirs(TEX_DIR, exist_ok=True)


def dominant_color(crop_path, k=3):
    """K-means dominant color (skip transparent + near-black bg)."""
    img = cv2.imread(crop_path, cv2.IMREAD_UNCHANGED)
    if img is None: return None
    # If RGBA: filter by alpha
    if img.shape[-1] == 4:
        mask = img[:, :, 3] > 128
        px = img[mask, :3]
    else:
        # Skip near-black pixels (likely bg)
        flat = img.reshape(-1, 3)
        brightness = flat.sum(axis=1)
        px = flat[brightness > 60]
    if len(px) < 10: return None
    px = np.float32(px)
    # k-means
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, centers = cv2.kmeans(px, k, None, crit, 5, cv2.KMEANS_RANDOM_CENTERS)
    # Pick largest cluster
    counts = np.bincount(labels.flatten())
    dom_idx = counts.argmax()
    bgr = centers[dom_idx]
    # BGR -> RGB float 0..1
    return (float(bgr[2])/255, float(bgr[1])/255, float(bgr[0])/255)


def build_piece_color_map():
    """piece_name -> (bone_anchor, RGB tuple, z_range, order).
    USA manifest color_hex (Florence crops escuros bg).
    Ordem reversa pra outer layers prevalecerem (saia_teal > saia_cream > saia_lace)."""
    m = json.load(open(MANIFEST, encoding='utf-8'))
    palette = {}
    for p in m['pieces']:
        name = p['name']
        bone = p.get('bone_anchor', 'mixamorig:Hips')
        z = p.get('z', [0.5, 1.0])
        hx = p.get('color_hex', '#888888').lstrip('#')
        color = (int(hx[0:2],16)/255, int(hx[2:4],16)/255, int(hx[4:6],16)/255)
        palette[name] = {"bone": bone, "color": color, "z": z,
                         "order": p.get('order', 99)}
    return palette


def blender_paint(palette):
    palette_json = json.dumps(palette)
    script = f"""
import bpy, json
from mathutils import Vector

palette = json.loads(r'''{palette_json}''')

# Clean + import
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=r'{GLB_IN.replace(chr(92),"/")}')

dress = next((o for o in bpy.data.objects if o.type=='MESH' and 'Dress' in o.name), None)
body = next((o for o in bpy.data.objects if o.type=='MESH' and ('Body' in o.name or 'Corpo' in o.name)), None)
arm = next((o for o in bpy.data.objects if o.type=='ARMATURE'), None)
if not dress:
    print('NO_DRESS'); raise SystemExit

# Build bone_name -> color lookup (e tambem prefix matches)
bone_color = {{}}
piece_z_color = []
items = sorted(palette.items(), key=lambda kv: kv[1].get('order', 99))
# Higher order = outer = wins. Iterate from outer to inner so first match = outer.
for name, info in reversed(items):
    bone = info['bone']; color = info['color']; z = info['z']
    bone_color[bone] = color  # later overwrite = inner wins for bone match
    piece_z_color.append((z[0], z[1], color, bone, info.get('order',0)))
# Override: outer (high order) for bone lookup
for name, info in items:
    bone_color[info['bone']] = info['color']
# Z list ordered outer-first
piece_z_color.sort(key=lambda t: -t[4])
print(f'bones in palette: {{len(bone_color)}}')
print(f'z order (outer first): {{[(round(t[0],2), round(t[1],2), t[4]) for t in piece_z_color[:8]]}}')

# Per vertex: find dominant bone -> color. Fallback z-range matching.
mesh = dress.data
# Ensure vertex color layer
if not mesh.vertex_colors:
    mesh.vertex_colors.new(name='Col')
vcol = mesh.vertex_colors.active

# Build vertex -> dominant bone
vg_index_to_name = {{vg.index: vg.name for vg in dress.vertex_groups}}
default_color = (0.5, 0.5, 0.5, 1.0)
painted = 0
fallback = 0
loop_idx = 0
for poly in mesh.polygons:
    for vi in poly.vertices:
        v = mesh.vertices[vi]
        best_w = 0; best_name = None
        for g in v.groups:
            if g.weight > best_w:
                best_w = g.weight; best_name = vg_index_to_name.get(g.group)
        col = bone_color.get(best_name)
        if not col:
            # z-range fallback
            wz = (dress.matrix_world @ v.co).z
            for t in piece_z_color:
                z0, z1, c = t[0], t[1], t[2]
                if z0 <= wz <= z1:
                    col = c; fallback += 1; break
        if not col: col = (0.5, 0.5, 0.5)
        else: painted += 1
        vcol.data[loop_idx].color = (col[0], col[1], col[2], 1.0)
        loop_idx += 1
print(f'painted={{painted}} fallback_z={{fallback}}')

# Material: vertex color -> Base Color
mat = bpy.data.materials.get('Painted_Dress') or bpy.data.materials.new('Painted_Dress')
mat.use_nodes = True
nt = mat.node_tree
for n in list(nt.nodes): nt.nodes.remove(n)
out = nt.nodes.new('ShaderNodeOutputMaterial')
bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
vc = nt.nodes.new('ShaderNodeVertexColor'); vc.layer_name = 'Col'
nt.links.new(vc.outputs['Color'], bsdf.inputs['Base Color'])
nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
dress.data.materials.clear(); dress.data.materials.append(mat)

# Export
bpy.ops.object.select_all(action='DESELECT')
for o in [dress, body, arm]:
    if o: o.select_set(True)
if arm: bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.gltf(filepath=r'{GLB_OUT.replace(chr(92),"/")}',
                           use_selection=True, export_format='GLB',
                           export_apply=True, export_materials='EXPORT',
                           export_skins=True)
print(f'EXPORTED: {GLB_OUT.replace(chr(92),"/")}')
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script); p = f.name
    try:
        env = os.environ.copy(); env['PYTHONIOENCODING'] = 'utf-8'
        r = subprocess.run([sys.executable, BRIDGE, '--file', p],
                            capture_output=True, text=True, timeout=300, env=env)
        sys.stdout.write(r.stdout[-2500:])
        if r.returncode: sys.stderr.write(r.stderr)
        return os.path.exists(GLB_OUT)
    finally:
        try: os.unlink(p)
        except: pass


def render_painted():
    script = f"""
import bpy, os, math
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=r'{GLB_OUT.replace(chr(92),"/")}')

bpy.ops.object.light_add(type='AREA', location=(2.5,-3,2.5))
bpy.context.object.data.energy = 1000; bpy.context.object.data.size = 1.5
bpy.ops.object.light_add(type='AREA', location=(-2,-2,1.8))
bpy.context.object.data.energy = 400
bpy.ops.object.light_add(type='AREA', location=(0,3,2.0))
bpy.context.object.data.energy = 500
bpy.context.scene.world.use_nodes = True
bg = bpy.context.scene.world.node_tree.nodes.get('Background')
if bg:
    bg.inputs[0].default_value = (0.15, 0.15, 0.17, 1.0)
    bg.inputs[1].default_value = 0.3

def cam(name, loc, rot):
    cd = bpy.data.cameras.new(name); c = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(c)
    c.location = loc; c.rotation_euler = rot
    c.data.type = 'ORTHO'; c.data.ortho_scale = 2.0

cam('PAINT_FRONT', (0,-4,1.0), (math.radians(90),0,0))
cam('PAINT_SIDE', (4,0,1.0), (math.radians(90),0,math.radians(90)))
cam('PAINT_BACK', (0,4,1.0), (math.radians(90),0,math.radians(180)))

sc = bpy.context.scene
sc.render.engine = 'CYCLES'
try: sc.cycles.device = 'GPU'
except: pass
sc.cycles.samples = 64
sc.render.resolution_x = 800; sc.render.resolution_y = 1000
sc.render.image_settings.file_format = 'PNG'
OUT = r'{os.path.join(WORK,"painted_renders").replace(chr(92),"/")}'
os.makedirs(OUT, exist_ok=True)
for cn in ['PAINT_FRONT','PAINT_SIDE','PAINT_BACK']:
    sc.camera = bpy.data.objects[cn]
    sc.render.filepath = os.path.join(OUT, f'painted_{{cn}}.png')
    bpy.ops.render.render(write_still=True)
print('DONE')
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script); p = f.name
    try:
        env = os.environ.copy(); env['PYTHONIOENCODING'] = 'utf-8'
        subprocess.run([sys.executable, BRIDGE, '--file', p],
                        capture_output=True, text=True, timeout=600, env=env)
    finally:
        try: os.unlink(p)
        except: pass


def main():
    print(f"\n{'='*60}\nPAINT PER PIECE\n{'='*60}")
    palette = build_piece_color_map()
    print(f"Palette ({len(palette)} pieces):")
    for n, info in palette.items():
        c = info['color']
        print(f"  {n}: bone={info['bone']} z={info['z']} RGB=({c[0]:.2f},{c[1]:.2f},{c[2]:.2f})")
    print(f"\n[blender paint]")
    if not blender_paint(palette):
        print("FAIL paint"); sys.exit(1)
    print(f"\n[render]")
    render_painted()
    print(f"\nOK: {GLB_OUT}")


if __name__ == '__main__':
    main()
