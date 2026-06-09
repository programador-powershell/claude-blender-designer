"""Spatial AI - Live Eye  (Blender GUI add-on)

Blender VE AO VIVO. Dois modos:

1. OLHO VIVO (auto): handler depsgraph_update_post dispara a cada edicao de
   mesh/transform. Re-segmenta vertex groups (Cintura_Fixacao / Vestido_Corpo /
   Barra_da_Saia) do objeto editado em tempo real, sem clique.

2. IA AVALIAR (botao): renderiza a viewport atual + envia pro maverick (NVIDIA
   NIM vision) junto com o concept art -> retorna score + problemas + sugestao
   de knobs, mostrado no painel. Voce ve o feedback ao vivo enquanto mexe.

Instalar: Blender > Text Editor > Open > este arquivo > Run Script.
Painel: View3D > N > "Spatial AI".

Env: NVIDIA_API_KEY no ambiente do Blender (ou cola no campo do painel).
"""
bl_info = {
    "name": "Spatial AI - Live Eye",
    "author": "Project Alice",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Spatial AI",
    "description": "Blender ve ao vivo: re-segmenta vertex groups na edicao + IA vision avalia render vs conceito.",
    "category": "Rigging",
}

import bpy
import os
import base64
import json
import time
from bpy.app.handlers import persistent

# ----------------------------------------------------------------------------
# 1. OLHO VIVO — re-segmenta vertex groups na edicao
# ----------------------------------------------------------------------------

_last_run = {"t": 0.0}

def segment_dress(obj):
    """Recalcula 3 zonas por altura Z: Cintura_Fixacao / Vestido_Corpo / Barra_da_Saia."""
    me = obj.data
    if not me.vertices:
        return
    zs = [v.co.z for v in me.vertices]
    mn, mx = min(zs), max(zs)
    h = mx - mn
    if h < 1e-5:
        return
    groups = {"Cintura_Fixacao": [], "Vestido_Corpo": [], "Barra_da_Saia": []}
    for v in me.vertices:
        zr = (v.co.z - mn) / h
        if 0.70 <= zr <= 0.85:
            groups["Cintura_Fixacao"].append(v.index)
        if 0.15 <= zr <= 0.88:
            groups["Vestido_Corpo"].append(v.index)
        if zr < 0.15:
            groups["Barra_da_Saia"].append(v.index)
    for name, idx in groups.items():
        vg = obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
        vg.remove(range(len(me.vertices)))
        if idx:
            vg.add(idx, 1.0, "REPLACE")


@persistent
def live_eye_handler(scene, depsgraph):
    if bpy.app.background:
        return
    # throttle 0.5s pra nao travar
    now = time.time()
    if now - _last_run["t"] < 0.5:
        return
    if not getattr(scene, "spatial_ai_live", False):
        return
    for upd in depsgraph.updates:
        if not (upd.is_updated_geometry or upd.is_updated_transform):
            continue
        oid = upd.id
        try:
            obj = bpy.data.objects.get(oid.name)
        except Exception:
            obj = None
        if obj and obj.type == "MESH" and (
            "AI_" in obj.name or "Dress" in obj.name or "Vestido" in obj.name
        ):
            segment_dress(obj)
            _last_run["t"] = now
            # feedback no header
            scene.spatial_ai_status = f"[olho] {obj.name} re-segmentado ({time.strftime('%H:%M:%S')})"
            break


def register_eye():
    unregister_eye()
    bpy.app.handlers.depsgraph_update_post.append(live_eye_handler)

def unregister_eye():
    h = bpy.app.handlers.depsgraph_update_post
    for f in list(h):
        if getattr(f, "__name__", "") == "live_eye_handler":
            h.remove(f)


# ----------------------------------------------------------------------------
# 2. IA AVALIAR — render viewport + maverick vision
# ----------------------------------------------------------------------------

def viewport_render(path):
    """Render rapido OpenGL da viewport atual."""
    bpy.context.scene.render.filepath = path
    bpy.context.scene.render.image_settings.file_format = "PNG"
    # render do viewport (workbench, rapido)
    prev = bpy.context.scene.render.engine
    bpy.ops.render.opengl(write_still=True)
    return path


def call_maverick(render_png, concept_png, api_key):
    try:
        from openai import OpenAI
    except ImportError:
        return {"error": "openai nao instalado no Python do Blender"}
    cli = OpenAI(api_key=api_key, base_url="https://integrate.api.nvidia.com/v1")
    def b64(p):
        with open(p, "rb") as f:
            return base64.b64encode(f.read()).decode()
    content = [{"type": "text", "text":
        "1a img = CONCEITO. 2a = RENDER atual do Blender. Compare silhueta/geometria "
        "(ignore cor). Liste problemas (bracos duplicados, saia rachada, proporcao) "
        "e diga score 0-10. Responda JSON {\"score\":N,\"problems\":[...],\"fix\":\"...\"}"}]
    if concept_png and os.path.exists(concept_png):
        content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64(concept_png)}"}})
    content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64(render_png)}"}})
    try:
        r = cli.chat.completions.create(
            model="meta/llama-4-maverick-17b-128e-instruct",
            messages=[{"role": "user", "content": content}],
            max_tokens=500, temperature=0.2)
        t = r.choices[0].message.content
        s, e = t.find("{"), t.rfind("}")
        return json.loads(t[s:e+1]) if s >= 0 else {"raw": t}
    except Exception as ex:
        return {"error": str(ex)}


class SPATIALAI_OT_evaluate(bpy.types.Operator):
    bl_idname = "spatial_ai.evaluate"
    bl_label = "IA Avaliar Agora"
    bl_description = "Renderiza a viewport e pede ao maverick (NVIDIA) p/ comparar com o conceito"

    def execute(self, context):
        sc = context.scene
        key = sc.spatial_ai_key or os.getenv("NVIDIA_API_KEY", "")
        if not key:
            self.report({"ERROR"}, "Setar NVIDIA_API_KEY (campo ou env)")
            return {"CANCELLED"}
        render_png = os.path.join(bpy.app.tempdir, "spatial_ai_view.png")
        viewport_render(render_png)
        verdict = call_maverick(render_png, sc.spatial_ai_concept, key)
        if "error" in verdict:
            sc.spatial_ai_status = f"[IA erro] {verdict['error'][:60]}"
            self.report({"ERROR"}, verdict["error"][:120])
            return {"CANCELLED"}
        score = verdict.get("score", "?")
        probs = ", ".join(verdict.get("problems", []))[:80]
        sc.spatial_ai_status = f"[IA] score={score} | {probs}"
        sc.spatial_ai_fix = verdict.get("fix", "")[:200]
        self.report({"INFO"}, f"IA score={score}")
        return {"FINISHED"}


# ----------------------------------------------------------------------------
# 3. UI
# ----------------------------------------------------------------------------

class SPATIALAI_PT_panel(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Spatial AI"
    bl_label = "Spatial AI - Live Eye"

    def draw(self, context):
        l = self.layout
        sc = context.scene
        l.prop(sc, "spatial_ai_live", text="Olho Vivo (auto re-segmenta)", toggle=True)
        l.separator()
        l.label(text="Conceito (comparar):")
        l.prop(sc, "spatial_ai_concept", text="")
        l.prop(sc, "spatial_ai_key", text="NVIDIA Key")
        l.operator("spatial_ai.evaluate", icon="HIDE_OFF")
        l.separator()
        box = l.box()
        box.label(text="Status:", icon="INFO")
        box.label(text=sc.spatial_ai_status or "(idle)")
        if sc.spatial_ai_fix:
            box.label(text="Fix sugerido:", icon="MODIFIER")
            for line in [sc.spatial_ai_fix[i:i+40] for i in range(0, len(sc.spatial_ai_fix), 40)]:
                box.label(text=line)


classes = (SPATIALAI_OT_evaluate, SPATIALAI_PT_panel)

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.spatial_ai_live = bpy.props.BoolProperty(name="Olho Vivo", default=False)
    bpy.types.Scene.spatial_ai_concept = bpy.props.StringProperty(name="Conceito", subtype="FILE_PATH", default="")
    bpy.types.Scene.spatial_ai_key = bpy.props.StringProperty(name="Key", subtype="PASSWORD", default="")
    bpy.types.Scene.spatial_ai_status = bpy.props.StringProperty(default="")
    bpy.types.Scene.spatial_ai_fix = bpy.props.StringProperty(default="")
    register_eye()
    print("[Spatial AI] Live Eye registrado. Painel: View3D > N > Spatial AI")

def unregister():
    unregister_eye()
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    for p in ("spatial_ai_live","spatial_ai_concept","spatial_ai_key","spatial_ai_status","spatial_ai_fix"):
        if hasattr(bpy.types.Scene, p):
            delattr(bpy.types.Scene, p)

if __name__ == "__main__":
    register()
