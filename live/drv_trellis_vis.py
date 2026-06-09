# -*- coding: utf-8 -*-
"""Visualizacao TRELLIS vs build: 2 passes F12 workbench (confiavel, usa
scene.display.shading) top-down de Cam_Aerial, film transparente.
  pass A = build (clay)   pass B = ref TRELLIS (cyan silhueta)
Saidas em work/renders/ -> eu componho lado a lado/overlay com PIL.
Pre: load_trellis_ref ja rodou (ref no scene)."""
import bpy, os

OUT = r"D:\Alice\tools\auto-rig-fix\work\renders"
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene

ca = bpy.data.objects.get("Cam_Aerial")
if ca: sc.camera = ca
sc.render.engine = "BLENDER_WORKBENCH"
sc.render.resolution_x = 860; sc.render.resolution_y = 820
sc.render.film_transparent = True
sh = sc.display.shading
sh.light = "FLAT"; sh.color_type = "OBJECT"; sh.show_cavity = False; sh.show_xray = False

ref = [o for o in bpy.data.objects if o.get("trellis_ref") and o.type == "MESH"]
build = [o for o in bpy.data.objects
         if o.type == "MESH" and not o.get("trellis_ref")
         and o.name != "Ceiling" and not o.name.startswith("Beam")]
hidden = [o for o in bpy.data.objects if o.name == "Ceiling" or o.name.startswith("Beam")]

def vis(objs, on):
    for o in objs:
        o.hide_render = not on

# cores
for o in build: o.color = (0.82, 0.62, 0.42, 1.0)
for o in ref:
    o.color = (0.0, 0.85, 1.0, 1.0)
    o.display_type = "SOLID"      # silhueta solida (decimada = leve)

# PASS A: build sozinho
vis(ref, False); vis(build, True); vis(hidden, False)
sc.render.filepath = os.path.join(OUT, "vis_build_top.png")
bpy.ops.render.render(write_still=True)

# PASS B: ref TRELLIS sozinho
vis(build, False); vis(ref, True)
sc.render.filepath = os.path.join(OUT, "vis_ref_top.png")
bpy.ops.render.render(write_still=True)

# restaura: ambos visiveis em viewport, ref volta wire nao-render
vis(build, True); vis(ref, True)
for o in ref:
    o.hide_render = True
    o.display_type = "WIRE"
print("VIS_DONE", OUT)
