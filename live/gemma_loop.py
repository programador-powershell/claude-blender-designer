# -*- coding: utf-8 -*-
"""LOOP GEMMA (Claude=ponte, Gemma=olho). Roda no python do ComfyUI (PIL+urllib+socket).
Para cada (regiao, vista): enquadra no Blender ao vivo -> renderiza SO o modelo ->
recorta a regiao da arte de referencia -> manda AS DUAS IMAGENS pro Gemma (nao descricao)
-> Gemma devolve JSON do diff -> snapshot. Usuario assiste no viewport.

  python gemma_loop.py <regiao> <vista>
  regioes: motifs, skirt, torso, head, hat, hands, full
  vistas:  front, side, back
"""
import sys, os, json, base64
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))          # live/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # auto-rig-fix/
from bridge_cmd import send
import vision_ask as VA
import trace_overlay as TO
from PIL import Image

WORK = r"D:/Alice/tools/auto-rig-fix/work/loop"
os.makedirs(WORK, exist_ok=True)
REF = {"front": r"D:/Alice/tools/dress/regen/in_front.png",
       "side":  r"D:/Alice/tools/dress/regen/in_left.png",
       "back":  r"D:/Alice/tools/dress/regen/in_back.png"}
VIEWQ = {"front": (0.70710678, 0.70710678, 0, 0),
         "side":  (0.5, 0.5, 0.5, 0.5),
         "back":  (0, 0, -0.70710678, -0.70710678)}
# Camera ortho quats (computed via Vector(direction).to_track_quat('-Z','Y'))
# Camera positioned at (CEN - direction*dist), looking in direction toward CEN.
# front: dir=(0,+1,0) — camera at -Y looking +Y
# side : dir=(-1,0,0) — camera at +X looking -X
# back : dir=(0,-1,0) — camera at +Y looking -Y
# NOTE: viewport region_3d.view_rotation uses DIFFERENT convention. See alice-session-toolchain memory.
# regiao -> (view_location, view_distance, ref_crop_box normalizado L,T,R,B)
REGION = {
  "full":   ((0,0,0.58), 0.62, (0.00,0.00,1.00,1.00)),
  "motifs": ((0,0,0.62), 0.45, (0.12,0.30,0.88,0.98)),
  "skirt":  ((0,0,0.50), 0.40, (0.10,0.45,0.90,0.99)),
  "torso":  ((0,0,0.85), 0.30, (0.20,0.18,0.80,0.50)),
  "head":   ((0,0,1.08), 0.18, (0.28,0.00,0.72,0.16)),
  "hat":    ((0,0,1.12), 0.20, (0.25,0.00,0.75,0.14)),
  "hands":  ((0,0,0.72), 0.55, (0.00,0.32,1.00,0.70)),
}

def render_model(loc, dist, quat, out):
    """Render OFFSCREEN por CAMERA ortho — NAO mexe no viewport (usuario ve full+ref sempre)."""
    code = f"""
import bpy, mathutils
sc=bpy.context.scene
sc.render.resolution_x=900; sc.render.resolution_y=900
sc.render.image_settings.file_format='PNG'
cam=bpy.data.objects.get('LoopCam')
if cam is None:
    cd=bpy.data.cameras.new('LoopCam'); cam=bpy.data.objects.new('LoopCam',cd); sc.collection.objects.link(cam)
cam.data.type='ORTHO'; cam.data.ortho_scale={2.05*dist}
q=mathutils.Quaternion({quat})
cam.rotation_mode='QUATERNION'; cam.rotation_quaternion=q
cam.location=mathutils.Vector({tuple(loc)}) + (q @ mathutils.Vector((0,0,4.0)))
sc.camera=cam
for o in bpy.data.objects:
    if o.name.startswith('REF_'): o.hide_render=True
sc.render.filepath=r'{out}'
bpy.ops.render.render(write_still=True)
print('cam-rendered {out}')
"""
    return send({"code": code, "shot": False})

def set_compare_view(view):
    """Viewport = ELA INTEIRA + arte da vista ao lado (MATERIAL), p/ usuario comparar ao vivo."""
    loc = {"front": (0.52,0,0.6), "side": (0,0.52,0.6), "back": (-0.52,0,0.6)}[view]
    code = f"""
import bpy
for w in bpy.context.window_manager.windows:
 for a in w.screen.areas:
  if a.type=='VIEW_3D':
   sp=a.spaces.active; sp.shading.type='MATERIAL'; sp.overlay.show_overlays=True
   for o in bpy.data.objects:
     if o.name.startswith('REF_'): o.hide_set(False)
   r=sp.region_3d; r.view_perspective='ORTHO'; r.view_rotation={VIEWQ[view]}
   r.view_location={loc}; r.view_distance=1.75
   a.tag_redraw()
print('compare view {view}')
"""
    return send({"code": code, "shot": False})

def crop_ref(view, box, out):
    im = Image.open(REF[view]).convert("RGB")
    w,h = im.size
    l,t,r,b = box
    im.crop((int(l*w),int(t*h),int(r*w),int(b*h))).save(out)
    return out

def snapshot(label):
    code = ("import sys; sys.path.insert(0, r'D:\\\\Alice\\\\tools\\\\auto-rig-fix\\\\live')\n"
            "import importlib, game_builder; importlib.reload(game_builder)\n"
            f"print(game_builder.snapshot(label='{label}'))")
    return send({"code": code, "shot": False})

PROMPTS = {
 "motifs": ('Three images: [1]=CONCEPT ART, [2]=3D render, [3]=overlay (RED=art lines, GREEN=model). Focus ONLY on the '
   'CLOCK motifs and PLAYING-CARD motifs on the dress, and whether the skirt reads as MANY '
   'separate fabric layers (not one piece). Reply ONLY JSON: '
   '{"clocks":{"in_art":int,"in_model":int,"placement":str,"issue":str},'
   '"cards":{"in_art":int,"in_model":int,"placement":str,"issue":str},'
   '"skirt_layers":{"art":int,"model":int,"issue":str},'
   '"fidelity_0to100":int,"fixes":[str]}'),
}
DEFAULT_PROMPT = ('Three images: [1]=CONCEPT ART (target), [2]=current 3D render, '
   '[3]=OVERLAY where RED=art contour lines, GREEN=model contour lines, YELLOW=they match, '
   'on a labelled grid (cols A.., rows 1..). RED without nearby GREEN = where the model is WRONG. '
   'Report COMPLETE deviations covering ALL of: '
   '(a) silhouette/contour, (b) COLOR (hue+saturation per region), '
   '(c) TONAL VALUES (black/dark/mid/light/white levels - is the model too light or too dark?), '
   '(d) LINE WORK (sharp edges, decorative lines, stitching, panel seams visible in art), '
   '(e) LIGHTING (highlight placement, specular hits, rim light direction), '
   '(f) SHADOWS (cast shadows, occlusion in folds, depth of crevices). '
   'For each deviation specify which aspect (silhouette/color/tone/line/light/shadow). '
   'Reply ONLY JSON: {"region":str,"fidelity_0to100":int,'
   '"deviations":[{"cell":str,"aspect":str,"problem":str,"fix":str}]}')

def main():
    region = sys.argv[1] if len(sys.argv)>1 else "motifs"
    view   = sys.argv[2] if len(sys.argv)>2 else "front"
    loc,dist,box = REGION[region]
    quat = VIEWQ[view]
    cur = f"{WORK}/{region}_{view}_cur.png"
    ref = f"{WORK}/{region}_{view}_ref.png"
    ovl = f"{WORK}/{region}_{view}_overlay.png"
    print(f"[loop] {region}/{view}")
    set_compare_view(view)                 # viewport: ela INTEIRA + arte ao lado (usuario ve)
    print("  compare view:", view)
    r = render_model(loc, dist, quat, cur)  # render da parte OFFSCREEN por camera
    print("  render:", "OK" if r.get("ok") else r.get("out"))
    crop_ref(view, box, ref)
    print("  ref crop:", ref)
    cov = TO.make_overlay(ref, cur, ovl, grid=12)         # grid + cv2 linhas da arte por cima
    print(f"  overlay (desenho por cima): {ovl}  cobertura_linhas={cov}%")
    prompt = PROMPTS.get(region, DEFAULT_PROMPT)
    print("  -> Gemma lendo [arte, overlay+grid]...")
    ans = VA.ask_multi([ref, ovl], prompt, num_predict=800)   # 2 imgs (menos memoria/crash)
    print("GEMMA_JSON:", ans)
    snap = snapshot(f"{region}_{view}")
    print("  snapshot:", snap.get("out","").strip().splitlines()[-1] if snap.get("out") else "?")

if __name__ == "__main__":
    main()
