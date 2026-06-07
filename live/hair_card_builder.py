"""
Project Alice — Blender Hair Card Builder

Constrói cabelo por hair cards dentro do Blender, usando blueprint JSON.

Base conceitual:
- GodotHair escolhe hair cards em vez de strand-based para equilibrar qualidade e custo.
- Este builder implementa hair cards procedurais no Blender, com camadas:
  scalp cap, bangs, side locks, back volume, loose curls, flyaways.
- Não usa nem redistribui assets do GodotHair. A lógica é compatível com a ideia
  de hair cards e shader anisotrópico.

Uso no Blender:
    import sys; sys.path.insert(0, "D:/Alice/tools/auto-rig-fix/live")
    import hair_card_builder
    hair_card_builder.build_hair_from_file("examples/alice_liddell_hair_blueprint.json")
"""
from __future__ import annotations

import json, math, random
from typing import Dict, List, Tuple

try:
    import bpy
    from mathutils import Vector
except Exception:  # permite importar fora do Blender para validar JSON
    bpy = None
    Vector = None


def _ensure_blender():
    if bpy is None:
        raise RuntimeError("Este módulo precisa rodar dentro do Blender.")


def _v(v):
    return Vector((float(v[0]), float(v[1]), float(v[2])))


def _lerp(a, b, t):
    return a * (1.0 - t) + b * t


def create_hair_material(shader: Dict) -> str:
    """Cria material de cabelo aproximando o shader GodotHair no Blender."""
    _ensure_blender()
    name = shader.get("name", "PA_Hair_Black_Anisotropic")
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.blend_method = "HASHED" if shader.get("alpha_hash", True) else "BLEND"
    mat.use_screen_refraction = False
    mat.show_transparent_back = True

    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        color = shader.get("albedo", [0.015, 0.012, 0.011])
        alpha = 1.0
        try:
            bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], alpha)
        except Exception:
            pass
        for socket_name, val in [
            ("Roughness", shader.get("azimuthal_roughness", 0.78)),
            ("Metallic", 0.0),
            ("Alpha", 0.72),
            ("Specular IOR Level", shader.get("specular", 0.65)),
            ("Anisotropic IOR Level", 0.7 if shader.get("use_anisotropic", True) else 0.0),
        ]:
            if socket_name in bsdf.inputs:
                try:
                    bsdf.inputs[socket_name].default_value = val
                except Exception:
                    pass
    return mat.name


def make_card_mesh(
    name: str,
    root,
    tip,
    width_root: float,
    width_tip: float,
    segments: int = 8,
    curve_strength: float = 0.1,
    curl_turns: float = 0.0,
    curl_radius: float = 0.0,
    normal_bias=(0, -1, 0),
    material_name: str = "PA_Hair_Black_Anisotropic",
    opacity: float = 1.0,
):
    """Cria um hair card como fita segmentada com UV root→tip."""
    _ensure_blender()
    root = _v(root); tip = _v(tip); bias = _v(normal_bias)
    direction = tip - root
    length = max(direction.length, 0.001)
    tangent = direction.normalized()

    # side vector estável: perpendicular à direção e ao viés visual
    side = tangent.cross(bias)
    if side.length < 0.001:
        side = tangent.cross(Vector((0, 0, 1)))
    if side.length < 0.001:
        side = Vector((1, 0, 0))
    side.normalize()

    sag_dir = Vector((0, 0, -1))
    verts, faces, uvs = [], [], []
    for i in range(segments + 1):
        t = i / segments
        center = _lerp(root, tip, t)
        # queda em arco e ondulação lateral para cabelo natural
        center += sag_dir * math.sin(t * math.pi) * curve_strength * length
        if curl_turns and curl_radius:
            ang = t * math.tau * curl_turns
            center += side * math.sin(ang) * curl_radius
            center += bias.normalized() * math.cos(ang) * curl_radius * 0.35
        width = _lerp(Vector((width_root, 0, 0)), Vector((width_tip, 0, 0)), t).x
        verts.append(tuple(center - side * width * 0.5))
        verts.append(tuple(center + side * width * 0.5))
        uvs.append((0, t)); uvs.append((1, t))
    for i in range(segments):
        faces.append((i*2, i*2+1, i*2+3, i*2+2))

    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    mat = bpy.data.materials.get(material_name)
    if mat:
        obj.data.materials.append(mat)

    uv_layer = mesh.uv_layers.new(name="UV_root_to_tip")
    idx = 0
    for poly in mesh.polygons:
        for vi in poly.vertices:
            uv_layer.data[idx].uv = uvs[vi]
            idx += 1
    obj["pa_hair_card"] = True
    obj["opacity_hint"] = opacity
    return obj


def create_scalp_cap(name: str, material_name: str, radius_x=0.145, radius_y=0.115, z=1.62, loc=(0, 0, 0)):
    """Cria um cap simples para esconder raízes dos cards."""
    _ensure_blender()
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=16, location=(loc[0], loc[1], loc[2] + z))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (radius_x, radius_y, 0.095)
    mat = bpy.data.materials.get(material_name)
    if mat:
        obj.data.materials.append(mat)
    obj["pa_hair_scalp_cap"] = True
    return obj


def build_hair_from_blueprint(bp: Dict, collection_name="PA_Hair") -> Dict:
    _ensure_blender()
    shader_name = create_hair_material(bp.get("shader", {}))

    coll = bpy.data.collections.get(collection_name) or bpy.data.collections.new(collection_name)
    if coll.name not in bpy.context.scene.collection.children:
        try:
            bpy.context.scene.collection.children.link(coll)
        except Exception:
            pass

    made = []
    create_scalp_cap(f"{bp.get('character','Character')}_ScalpCap", shader_name)

    for group in bp.get("groups", []):
        for card in group.get("cards", []):
            obj = make_card_mesh(
                name=f"{bp.get('character','Character')}_{card['id']}",
                root=card["root"],
                tip=card["tip"],
                width_root=card.get("width_root_m", 0.035),
                width_tip=card.get("width_tip_m", 0.006),
                segments=card.get("segments", 8),
                curve_strength=card.get("curve_strength", 0.10),
                curl_turns=card.get("curl_turns", 0.0),
                curl_radius=card.get("curl_radius_m", 0.0),
                normal_bias=card.get("normal_bias", [0, -1, 0]),
                material_name=card.get("material", shader_name),
                opacity=card.get("opacity", 1.0),
            )
            made.append(obj.name)

            if card.get("mirror", False):
                root = card["root"]; tip = card["tip"]
                mirrored = dict(card)
                mirrored["id"] = card["id"] + "_MIRROR"
                mirrored["root"] = [-root[0], root[1], root[2]]
                mirrored["tip"] = [-tip[0], tip[1], tip[2]]
                mirrored["normal_bias"] = [-card.get("normal_bias", [0, -1, 0])[0], card.get("normal_bias", [0, -1, 0])[1], card.get("normal_bias", [0, -1, 0])[2]]
                obj = make_card_mesh(
                    name=f"{bp.get('character','Character')}_{mirrored['id']}",
                    root=mirrored["root"],
                    tip=mirrored["tip"],
                    width_root=mirrored.get("width_root_m", 0.035),
                    width_tip=mirrored.get("width_tip_m", 0.006),
                    segments=mirrored.get("segments", 8),
                    curve_strength=mirrored.get("curve_strength", 0.10),
                    curl_turns=mirrored.get("curl_turns", 0.0),
                    curl_radius=mirrored.get("curl_radius_m", 0.0),
                    normal_bias=mirrored.get("normal_bias", [0, -1, 0]),
                    material_name=mirrored.get("material", shader_name),
                    opacity=mirrored.get("opacity", 1.0),
                )
                made.append(obj.name)

    return {
        "ok": True,
        "character": bp.get("character"),
        "style": bp.get("style_name"),
        "material": shader_name,
        "cards_created": len(made),
        "objects": made[:30],
        "note": "Hair cards criados. Para produção, adicione textura alpha/coverage e ajuste pesos/physics."
    }


def build_hair_from_file(path: str) -> Dict:
    with open(path, encoding="utf-8") as f:
        bp = json.load(f)
    return build_hair_from_blueprint(bp)


def add_secondary_motion_rig(character_name="Alice", stiffness=0.55, damping=0.42) -> Dict:
    """Placeholder seguro: marca os cards para posterior rig físico/secondary bones."""
    _ensure_blender()
    count = 0
    for obj in bpy.data.objects:
        if obj.get("pa_hair_card"):
            obj["secondary_motion"] = {
                "mode": "card_chain_bones",
                "stiffness": stiffness,
                "damping": damping,
                "collision": "head_neck_shoulders"
            }
            count += 1
    return {"ok": True, "hair_cards_tagged_for_secondary_motion": count}
