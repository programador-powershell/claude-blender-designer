# -*- coding: utf-8 -*-
"""
Project Alice - Game Builder Core Engine V2.1
Blender 5.1 / Unreal Engine 5.x

Objetivo:
- Importar corpo base + armature + malha fonte (GLB/GLTF/FBX/OBJ);
- Separar a roupa em CAMADAS reais usando MASCARAS UV-SPACE e um manifesto explicito;
- Garantir montagem inside-out por layer_index (nao por adivinhacao de area);
- Aplicar comportamento por categoria: cloth / semi_rigid / rigid / hair_card;
- Transferir pesos do corpo base;
- Aplicar shrinkwrap progressivo entre camadas deformaveis;
- Criar mascara anti-clipping no corpo base;
- Adicionar helpers opcionais para dedos, ombro, saia e cabelo;
- Exportar GLB limpo para pipeline de jogo.

IMPORTANTE:
- Este script NAO tenta inferir a ordem correta do figurino por tamanho da mascara.
- A ordem eh garantida pelo arquivo de manifesto JSON.
- As mascaras DEVEM estar em UV space da malha source.
"""

from __future__ import annotations

import bpy
import bmesh
import os
import json
import traceback
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from mathutils import Vector, kdtree

DEFAULT_COLLECTIONS = [
    "PA_00_REFERENCE", "PA_01_BODY", "PA_02_HAIR", "PA_03_GARMENT_INNER",
    "PA_04_GARMENT_OUTER", "PA_05_ACCESSORIES", "PA_06_EXPORT", "PA_10_VALIDATION",
]
DEFORMABLE_CATEGORIES = {"cloth", "semi_rigid", "hair_card"}
RIGID_CATEGORIES = {"rigid", "accessory", "metal", "prop", "weapon"}
EXPORT_KEEP_MODIFIERS = {"ARMATURE"}
MIXAMO_FINGERS = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
MIXAMO_SIDES = ["Left", "Right"]
MIXAMO_PHALANGES = ["1", "2", "3"]


def log(m): print(f"[ProjectAliceV2.1] {m}")
def warn(m): print(f"[ProjectAliceV2.1][WARN] {m}")
def err(m): print(f"[ProjectAliceV2.1][ERROR] {m}")


@dataclass
class GarmentPiece:
    piece_id: str
    mask: str
    layer_index: int
    category: str = "cloth"
    target_collection: str = "PA_04_GARMENT_OUTER"
    thickness: float = 0.0015
    shrinkwrap_offset: float = 0.0025
    transfer_weights: bool = True
    anti_clipping_source: bool = False
    material: Optional[str] = None


@dataclass
class BuildConfig:
    source_mesh_name: str = "AI_Raw_Mold"
    body_name: str = "Alice_Body_Base"
    armature_name: str = "Rig_Alice"
    masks_directory: str = ""
    export_path: str = ""
    target_height_m: float = 1.70
    pieces: List[GarmentPiece] = field(default_factory=list)
    hair: Dict[str, Any] = field(default_factory=dict)


def ensure_object_mode():
    obj = bpy.context.object
    if obj and obj.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")


def clear_selection():
    ensure_object_mode()
    bpy.ops.object.select_all(action="DESELECT")


def ensure_collection(name):
    col = bpy.data.collections.get(name)
    if not col:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def ensure_project_collections():
    return {name: ensure_collection(name) for name in DEFAULT_COLLECTIONS}


def move_to_collection(obj, collection_name):
    if obj is None: return
    col = ensure_collection(collection_name)
    for user_col in list(obj.users_collection):
        user_col.objects.unlink(obj)
    if obj.name not in col.objects:
        col.objects.link(obj)


def apply_transforms(obj, loc=False, rot=True, scale=True):
    if obj is None: return
    clear_selection()
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    try: bpy.ops.object.transform_apply(location=loc, rotation=rot, scale=scale)
    except Exception as ex: warn(f"Transform apply failed on {obj.name}: {ex}")


def safe_apply_modifier(obj, modifier_name):
    if obj is None or modifier_name not in obj.modifiers: return False
    try:
        clear_selection(); obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj]):
            bpy.ops.object.modifier_apply(modifier=modifier_name)
        return True
    except Exception as ex:
        warn(f"Could not apply modifier '{modifier_name}' on '{obj.name}': {ex}")
        return False


def apply_all_non_armature_modifiers(obj):
    if obj is None or obj.type != "MESH": return
    for mod in list(obj.modifiers):
        if mod.type not in EXPORT_KEEP_MODIFIERS:
            safe_apply_modifier(obj, mod.name)


def import_model(filepath, name_prefix=None):
    if not filepath or not os.path.exists(filepath):
        raise FileNotFoundError(f"Input model not found: {filepath}")
    before = set(bpy.data.objects)
    ext = os.path.splitext(filepath)[1].lower()
    log(f"Importing: {filepath}")
    if ext in {".glb", ".gltf"}: bpy.ops.import_scene.gltf(filepath=filepath)
    elif ext == ".fbx": bpy.ops.import_scene.fbx(filepath=filepath)
    elif ext == ".obj": bpy.ops.wm.obj_import(filepath=filepath)
    else: raise ValueError(f"Unsupported ext: {ext}")
    new_objs = [o for o in bpy.data.objects if o not in before]
    if name_prefix:
        for obj in new_objs: obj.name = f"{name_prefix}_{obj.name}"
    log(f"Imported {len(new_objs)} objects")
    return new_objs


def export_glb(export_path, objects):
    if not export_path: return {"status": "skipped"}
    export_dir = os.path.dirname(export_path)
    if export_dir and not os.path.exists(export_dir): os.makedirs(export_dir, exist_ok=True)
    clear_selection()
    count = 0
    for obj in objects:
        if obj and obj.name in bpy.data.objects:
            if obj.type == "MESH": apply_all_non_armature_modifiers(obj)
            obj.select_set(True); count += 1
    armatures = [o for o in objects if o and o.type == "ARMATURE"]
    for arm in armatures: arm.select_set(True)
    bpy.context.view_layer.objects.active = armatures[0] if armatures else (objects[0] if objects else None)
    bpy.ops.export_scene.gltf(filepath=export_path, export_format='GLB',
        use_selection=True, export_apply=True, export_yup=True,
        export_texcoords=True, export_normals=True, export_tangents=True,
        export_materials='EXPORT', export_animations=False, export_skins=True, export_morph=True)
    return {"status": "success", "path": export_path, "selected_objects": count}


def find_largest_mesh(objects):
    meshes = [o for o in objects if o.type == "MESH"]
    return max(meshes, key=lambda o: len(o.data.vertices)) if meshes else None


def find_first_armature(objects):
    return next((o for o in objects if o.type == "ARMATURE"), None)


def mesh_world_bbox(obj):
    return [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]


def mesh_height(obj):
    bbox = mesh_world_bbox(obj)
    return max(v.z for v in bbox) - min(v.z for v in bbox)


def get_mesh_bounding_proportions(mesh_obj):
    bbox = mesh_world_bbox(mesh_obj)
    z_min, z_max = min(v.z for v in bbox), max(v.z for v in bbox)
    x_min, x_max = min(v.x for v in bbox), max(v.x for v in bbox)
    y_min, y_max = min(v.y for v in bbox), max(v.y for v in bbox)
    height = max(z_max - z_min, 1e-6)
    center_x = (x_min + x_max) * 0.5
    return {"z_min":z_min,"z_max":z_max,"x_min":x_min,"x_max":x_max,
            "y_min":y_min,"y_max":y_max,"height":height,
            "hips":z_min+height*0.52,"chest":z_min+height*0.73,
            "mouth":z_min+height*0.85,
            "eye_left":Vector((center_x-0.035,0.06,z_min+height*0.885)),
            "eye_right":Vector((center_x+0.035,0.06,z_min+height*0.885)),
            "shoulder_width":(x_max-x_min)*0.45}


def normalize_mesh_to_height(obj, target_height_m=1.70):
    h = mesh_height(obj)
    if h <= 1e-6: warn(f"Cannot normalize {obj.name}"); return
    scale = target_height_m / h
    obj.scale = (obj.scale.x*scale, obj.scale.y*scale, obj.scale.z*scale)
    apply_transforms(obj, loc=False, rot=False, scale=True)
    bbox = mesh_world_bbox(obj)
    z_min = min(v.z for v in bbox)
    obj.location.z -= z_min
    apply_transforms(obj, loc=True, rot=False, scale=False)
    log(f"Normalized {obj.name} to {target_height_m:.3f}m")


def match_skeleton_proportions(ai_mesh_obj, armature_obj):
    ai_prop = get_mesh_bounding_proportions(ai_mesh_obj)
    base_bbox = mesh_world_bbox(armature_obj)
    base_dim = Vector((max(v.x for v in base_bbox)-min(v.x for v in base_bbox),
                        max(v.y for v in base_bbox)-min(v.y for v in base_bbox),
                        max(v.z for v in base_bbox)-min(v.z for v in base_bbox)))
    scale_factor = Vector(((ai_prop["shoulder_width"]*2.0)/base_dim.x if base_dim.x>1e-6 else 1.0,
                            (ai_prop["height"]*0.15)/base_dim.y if base_dim.y>1e-6 else 1.0,
                            ai_prop["height"]/base_dim.z if base_dim.z>1e-6 else 1.0))
    armature_obj.scale = scale_factor
    apply_transforms(armature_obj, loc=False, rot=False, scale=True)
    return {"status":"success","scale_factor":list(scale_factor)}


def ensure_material(name, base_color=(0.5,0.5,0.5,1.0), roughness=0.65, metallic=0.0):
    mat = bpy.data.materials.get(name)
    if mat: return mat
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        try:
            bsdf.inputs["Base Color"].default_value = base_color
            bsdf.inputs["Roughness"].default_value = roughness
            bsdf.inputs["Metallic"].default_value = metallic
        except Exception: pass
    return mat


def bootstrap_project_materials():
    presets = {
        "MAT_PA_Skin_Pale":((0.86,0.72,0.68,1),0.55,0.0),
        "MAT_PA_Hair_Black":((0.015,0.012,0.018,1),0.38,0.0),
        "MAT_PA_Fabric_Green_Teal":((0.12,0.25,0.23,1),0.72,0.0),
        "MAT_PA_Fabric_Cream":((0.86,0.83,0.77,1),0.70,0.0),
        "MAT_PA_Fabric_Black":((0.03,0.03,0.035,1),0.70,0.0),
        "MAT_PA_Lace_Black":((0.02,0.02,0.025,1),0.85,0.0),
        "MAT_PA_Lace_Cream":((0.78,0.74,0.69,1),0.85,0.0),
        "MAT_PA_Leather_Black":((0.03,0.025,0.02,1),0.42,0.0),
        "MAT_PA_Metal_AntiqueGold":((0.80,0.58,0.22,1),0.30,1.0),
    }
    for name, vals in presets.items(): ensure_material(name, *vals)


def load_manifest(manifest_path, masks_dir):
    if not manifest_path or not os.path.exists(manifest_path):
        raise FileNotFoundError("Manifest JSON required")
    with open(manifest_path, "r", encoding="utf-8") as f: data = json.load(f)
    pieces = []
    for item in data.get("pieces", []):
        pieces.append(GarmentPiece(
            piece_id=item["piece_id"], mask=item["mask"],
            layer_index=int(item["layer_index"]),
            category=item.get("category","cloth"),
            target_collection=item.get("target_collection","PA_04_GARMENT_OUTER"),
            thickness=float(item.get("thickness",0.0015)),
            shrinkwrap_offset=float(item.get("shrinkwrap_offset",0.0025)),
            transfer_weights=bool(item.get("transfer_weights",True)),
            anti_clipping_source=bool(item.get("anti_clipping_source",False)),
            material=item.get("material")))
    pieces.sort(key=lambda p: p.layer_index)
    return BuildConfig(
        source_mesh_name=data.get("source_mesh_name","AI_Raw_Mold"),
        body_name=data.get("body_name","Alice_Body_Base"),
        armature_name=data.get("armature_name","Rig_Alice"),
        masks_directory=masks_dir,
        export_path=data.get("export_path",""),
        target_height_m=float(data.get("target_height_m",1.70)),
        pieces=pieces, hair=data.get("hair",{}))


def load_mask_pixels(mask_path):
    if not os.path.exists(mask_path): raise FileNotFoundError(f"Mask: {mask_path}")
    img = bpy.data.images.load(mask_path, check_existing=True)
    w, h = img.size
    return img, w, h, list(img.pixels)


def mask_uv_hits_face(face, uv_layer, width, height, pixels, threshold=0.5):
    for loop in face.loops:
        uv = loop[uv_layer].uv
        u = max(0.0, min(0.999999, uv.x)); v = max(0.0, min(0.999999, uv.y))
        px = min(int(u*width), width-1); py = min(int(v*height), height-1)
        idx = (py*width+px)*4
        if idx < len(pixels) and pixels[idx] > threshold: return True
    return False


def validate_uv_masks_exist(config):
    missing = []
    for piece in config.pieces:
        mp = piece.mask if os.path.isabs(piece.mask) else os.path.join(config.masks_directory, piece.mask)
        if not os.path.exists(mp): missing.append(mp)
    return {"ok": len(missing)==0, "missing":missing}


def separate_faces_by_uv_mask(source_obj, mask_path, new_name):
    if source_obj is None or source_obj.type != "MESH": raise ValueError("source_obj must be mesh")
    if not source_obj.data.uv_layers.active:
        raise RuntimeError(f"'{source_obj.name}' no active UV layer")
    img, w, h, pixels = load_mask_pixels(mask_path)
    clear_selection(); source_obj.select_set(True)
    bpy.context.view_layer.objects.active = source_obj
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(source_obj.data)
    uv_layer = bm.loops.layers.uv.active
    for face in bm.faces: face.select_set(False)
    hit_count = 0
    for face in bm.faces:
        if mask_uv_hits_face(face, uv_layer, w, h, pixels):
            face.select_set(True); hit_count += 1
    bmesh.update_edit_mesh(source_obj.data)
    if hit_count == 0:
        bpy.ops.object.mode_set(mode="OBJECT")
        try: bpy.data.images.remove(img)
        except: pass
        warn(f"No faces for {mask_path}"); return None
    before = set(bpy.data.objects)
    bpy.ops.mesh.separate(type="SELECTED")
    bpy.ops.object.mode_set(mode="OBJECT")
    created = [o for o in bpy.data.objects if o not in before]
    try: bpy.data.images.remove(img)
    except: pass
    if not created: warn(f"No new obj from separate"); return None
    new_obj = max(created, key=lambda o: len(o.data.vertices))
    new_obj.name = new_name; new_obj.data.name = f"{new_name}_Mesh"
    log(f"Layer '{new_name}' verts={len(new_obj.data.vertices)}")
    return new_obj


def add_armature_modifier(obj, armature):
    if obj is None or armature is None: return
    mod = obj.modifiers.get("Armature") or obj.modifiers.new(name="Armature", type="ARMATURE")
    mod.object = armature


def transfer_weights_from_body(piece, body):
    dt = piece.modifiers.new(name="Weight_Transfer", type="DATA_TRANSFER")
    dt.object = body
    # Blender 5.x: use_vert_data + data_types_verts + vert_mapping
    if hasattr(dt, 'use_vert_data'): dt.use_vert_data = True
    else: dt.use_vertex_groups_data = True
    if hasattr(dt, 'data_types_verts'): dt.data_types_verts = {'VGROUP_WEIGHTS'}
    else: dt.data_types_vertex = {'VGROUP_WEIGHTS'}
    if hasattr(dt, 'vert_mapping'): dt.vert_mapping = 'POLYINTERP_NEAREST'
    return safe_apply_modifier(piece, "Weight_Transfer")


def find_nearest_bone(obj, armature_obj):
    bbox = mesh_world_bbox(obj)
    center = sum(bbox, Vector()) / 8.0
    nearest = None; min_dist = float("inf")
    for bone in armature_obj.pose.bones:
        bh = armature_obj.matrix_world @ bone.head
        d = (center - bh).length
        if d < min_dist: min_dist = d; nearest = bone.name
    return nearest


def pin_rigid_piece_to_nearest_bone(obj, armature):
    target_bone = find_nearest_bone(obj, armature)
    if not target_bone: return {"status":"error","piece":obj.name,"err":"no bone"}
    obj.vertex_groups.clear()
    vg = obj.vertex_groups.new(name=target_bone)
    vg.add([v.index for v in obj.data.vertices], 1.0, 'REPLACE')
    add_armature_modifier(obj, armature)
    return {"status":"success","piece":obj.name,"bone":target_bone}


def configure_piece_behavior(piece, spec, body, armature, previous_deformable):
    if spec.material:
        mat = bpy.data.materials.get(spec.material) or ensure_material(spec.material)
        piece.data.materials.clear(); piece.data.materials.append(mat)
    category = spec.category.lower()
    if category in RIGID_CATEGORIES:
        result = pin_rigid_piece_to_nearest_bone(piece, armature)
        move_to_collection(piece, "PA_05_ACCESSORIES")
        return result
    if spec.thickness > 0:
        sol = piece.modifiers.new(name="Cloth_Thickness", type="SOLIDIFY")
        sol.thickness = spec.thickness; sol.offset = 1.0
        sol.use_quality_normals = True
    if previous_deformable is not None and category in {"semi_rigid","cloth"}:
        sw = piece.modifiers.new(name="Anatomical_Hug", type="SHRINKWRAP")
        sw.target = previous_deformable
        sw.wrap_method = 'NEAREST_SURFACEPOINT'
        sw.wrap_mode = 'OUTSIDE'
        sw.offset = spec.shrinkwrap_offset
    add_armature_modifier(piece, armature)
    if spec.transfer_weights: transfer_weights_from_body(piece, body)
    move_to_collection(piece, spec.target_collection)
    return {"status":"success","piece":piece.name,"category":category}


def setup_anti_clipping_mask(body_obj, garment_obj, detection_threshold=None):
    if not body_obj or not garment_obj: return {"status":"skipped"}
    if body_obj.type != "MESH" or garment_obj.type != "MESH":
        return {"status":"skipped","reason":"non-mesh"}
    if detection_threshold is None:
        detection_threshold = max(mesh_height(body_obj)*0.006, 0.005)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_garment = garment_obj.evaluated_get(depsgraph)
    g_mesh = eval_garment.to_mesh()
    try:
        if not g_mesh.vertices: return {"status":"skipped"}
        g_vertices = [garment_obj.matrix_world @ v.co for v in g_mesh.vertices]
        kd = kdtree.KDTree(len(g_vertices))
        for i, p in enumerate(g_vertices): kd.insert(p, i)
        kd.balance()
        group_name = f"Occlusion_{garment_obj.name}"
        vg = body_obj.vertex_groups.get(group_name) or body_obj.vertex_groups.new(name=group_name)
        hidden = 0
        for v in body_obj.data.vertices:
            _, _, dist = kd.find(body_obj.matrix_world @ v.co)
            if dist < detection_threshold:
                vg.add([v.index], 1.0, 'REPLACE'); hidden += 1
            else:
                try: vg.remove([v.index])
                except RuntimeError: pass
        mod = body_obj.modifiers.get("Anti_Clipping") or body_obj.modifiers.new(name="Anti_Clipping", type="MASK")
        mod.vertex_group = group_name
        mod.invert_vertex_group = True
        return {"status":"success","hidden_vertices":hidden,"threshold":detection_threshold}
    finally:
        eval_garment.to_mesh_clear()


def validate_scene_for_build(config):
    missing = []
    source = bpy.data.objects.get(config.source_mesh_name)
    body = bpy.data.objects.get(config.body_name)
    arm = bpy.data.objects.get(config.armature_name)
    if not source: missing.append(config.source_mesh_name)
    if not body: missing.append(config.body_name)
    if not arm: missing.append(config.armature_name)
    if missing: return {"ok":False,"missing":missing}
    issues = []
    if source.type != "MESH": issues.append(f"{source.name} not MESH")
    if body.type != "MESH": issues.append(f"{body.name} not MESH")
    if arm.type != "ARMATURE": issues.append(f"{arm.name} not ARMATURE")
    if source.type == "MESH" and not source.data.uv_layers.active:
        issues.append(f"{source.name} no active UV layer")
    mc = validate_uv_masks_exist(config)
    if not mc["ok"]: issues.append("Some UV masks missing")
    return {"ok":len(issues)==0,"issues":issues,"missing_masks":mc.get("missing",[])}


def build_garment_layers(config):
    source = bpy.data.objects.get(config.source_mesh_name)
    body = bpy.data.objects.get(config.body_name)
    arm = bpy.data.objects.get(config.armature_name)
    validation = validate_scene_for_build(config)
    if not validation["ok"]: return {"status":"error","validation":validation}
    results = []; created = []
    previous_deformable = body; anti_clip_piece = None
    for spec in config.pieces:
        mp = spec.mask if os.path.isabs(spec.mask) else os.path.join(config.masks_directory, spec.mask)
        new_name = f"PA_{spec.layer_index:02d}_{spec.piece_id}"
        try:
            piece = separate_faces_by_uv_mask(source, mp, new_name)
            if not piece:
                results.append({"piece":spec.piece_id,"status":"skipped","reason":"no faces"}); continue
            created.append(piece)
            result = configure_piece_behavior(piece, spec, body, arm, previous_deformable)
            results.append(result)
            if spec.category.lower() in DEFORMABLE_CATEGORIES: previous_deformable = piece
            if spec.anti_clipping_source: anti_clip_piece = piece
        except Exception as ex:
            results.append({"piece":spec.piece_id,"status":"error","err":str(ex),
                            "trace":traceback.format_exc(limit=3)})
    anti_clip = setup_anti_clipping_mask(body, anti_clip_piece) if anti_clip_piece else None
    if source and source.name in bpy.data.objects:
        source.name = f"{source.name}_LEFTOVER"
        move_to_collection(source, "PA_10_VALIDATION")
        source.hide_viewport = True; source.hide_render = True
    return {"status":"success","created":[o.name for o in created],
            "results":results,"anti_clipping":anti_clip}


def apply_proportional_facial_shape_keys(mesh_name):
    mesh = bpy.data.objects.get(mesh_name)
    if not mesh or mesh.type != "MESH": return {"status":"skipped"}
    prop = get_mesh_bounding_proportions(mesh)
    clear_selection(); mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    if not mesh.data.shape_keys: mesh.shape_key_add(name="Basis")
    sk_mouth = mesh.data.shape_keys.key_blocks.get("Mouth_Open") or mesh.shape_key_add(name="Mouth_Open")
    sk_bl = mesh.data.shape_keys.key_blocks.get("Blink_L") or mesh.shape_key_add(name="Blink_L")
    sk_br = mesh.data.shape_keys.key_blocks.get("Blink_R") or mesh.shape_key_add(name="Blink_R")
    mouth_center = Vector((0.0, 0.08, prop["mouth"]))
    changed = {"mouth":0,"blink_l":0,"blink_r":0}
    for idx, v in enumerate(mesh.data.vertices):
        co_w = mesh.matrix_world @ v.co
        if (co_w - mouth_center).length < prop["height"]*0.026 and co_w.z < prop["mouth"]:
            sk_mouth.data[idx].co.z -= prop["height"]*0.014
            sk_mouth.data[idx].co.y += prop["height"]*0.003
            changed["mouth"] += 1
        if (co_w - prop["eye_left"]).length < prop["height"]*0.018 and co_w.z > prop["eye_left"].z:
            sk_bl.data[idx].co.z -= prop["height"]*0.007; changed["blink_l"] += 1
        if (co_w - prop["eye_right"]).length < prop["height"]*0.018 and co_w.z > prop["eye_right"].z:
            sk_br.data[idx].co.z -= prop["height"]*0.007; changed["blink_r"] += 1
    return {"status":"success","mesh":mesh_name,"changed":changed}


def setup_advanced_finger_constraints(arm_name):
    arm = bpy.data.objects.get(arm_name)
    if not arm or arm.type != "ARMATURE": return {"status":"skipped"}
    clear_selection(); arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    applied = []
    for side in MIXAMO_SIDES:
        for finger in MIXAMO_FINGERS:
            for ph in MIXAMO_PHALANGES:
                bone_name = f"mixamorig:{side}Hand{finger}{ph}"
                pb = arm.pose.bones.get(bone_name)
                if not pb: continue
                for c in list(pb.constraints): pb.constraints.remove(c)
                c = pb.constraints.new("LIMIT_ROTATION")
                c.use_limit_x = True; c.use_limit_y = True; c.use_limit_z = True
                c.owner_space = 'LOCAL'
                if finger == "Thumb":
                    c.min_x, c.max_x = -0.2, 0.9; c.min_y, c.max_y = -0.2, 0.2; c.min_z, c.max_z = -0.3, 0.3
                else:
                    c.min_x, c.max_x = 0.0, 1.4; c.min_y, c.max_y = -0.01, 0.01; c.min_z, c.max_z = -0.01, 0.01
                applied.append(bone_name)
    bpy.ops.object.mode_set(mode="OBJECT")
    return {"status":"success","constraints":len(applied)}


def setup_shoulder_sleeve_helpers(arm_name):
    arm = bpy.data.objects.get(arm_name)
    if not arm or arm.type != "ARMATURE": return {"status":"skipped"}
    clear_selection(); arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    created = []
    for short_side, long_side in [("L","Left"),("R","Right")]:
        ref = f"mixamorig:{long_side}Arm"; parent_ref = f"mixamorig:{long_side}Shoulder"
        if ref in arm.data.edit_bones:
            name = f"helper_shoulder_{short_side}"
            if name not in arm.data.edit_bones:
                src = arm.data.edit_bones[ref]
                eb = arm.data.edit_bones.new(name)
                eb.head = src.head.copy(); eb.tail = eb.head + Vector((0,0,0.08))
                eb.parent = arm.data.edit_bones.get(parent_ref) or src.parent
                created.append(name)
    bpy.ops.object.mode_set(mode="OBJECT")
    return {"status":"success","created":created}


def setup_secondary_dynamics_rig(arm_name):
    arm = bpy.data.objects.get(arm_name)
    if not arm or arm.type != "ARMATURE": return {"status":"skipped"}
    clear_selection(); arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    created = []
    pelvis = arm.data.edit_bones.get("mixamorig:Hips")
    head = arm.data.edit_bones.get("mixamorig:Head")
    spine = arm.data.edit_bones.get("mixamorig:Spine2") or arm.data.edit_bones.get("mixamorig:Spine1")
    if pelvis:
        for name, offset in [("dyn_skirt_front",Vector((0,-0.08,-0.12))),
                              ("dyn_skirt_back",Vector((0,0.10,-0.12))),
                              ("dyn_skirt_left",Vector((-0.14,0,-0.10))),
                              ("dyn_skirt_right",Vector((0.14,0,-0.10)))]:
            if name not in arm.data.edit_bones:
                eb = arm.data.edit_bones.new(name)
                eb.head = pelvis.tail + offset
                eb.tail = eb.head + Vector((0,0,-0.18)); eb.parent = pelvis
                created.append(name)
    if head:
        for name, offset in [("dyn_hair_back_01",Vector((0,0.10,-0.05))),
                              ("dyn_hair_back_02",Vector((0,0.14,-0.22)))]:
            if name not in arm.data.edit_bones:
                eb = arm.data.edit_bones.new(name)
                eb.head = head.tail + offset
                eb.tail = eb.head + Vector((0,0.08,-0.18)); eb.parent = head
                created.append(name)
    if spine and "dyn_back_bow" not in arm.data.edit_bones:
        eb = arm.data.edit_bones.new("dyn_back_bow")
        eb.head = spine.tail + Vector((0,0.10,-0.02))
        eb.tail = eb.head + Vector((0,0.12,-0.08)); eb.parent = spine
        created.append("dyn_back_bow")
    bpy.ops.object.mode_set(mode="OBJECT")
    return {"status":"success","created":created}


def create_hair_card_mesh(name, points, width, material_name="MAT_PA_Hair_Black"):
    if len(points) < 2: return None
    pts = [Vector(p) for p in points]
    verts = []; faces = []
    for i, p in enumerate(pts):
        tangent = (pts[i+1]-p).normalized() if i < len(pts)-1 else (p-pts[i-1]).normalized()
        side = tangent.cross(Vector((0,0,1)))
        if side.length < 1e-4: side = Vector((1,0,0))
        side.normalize()
        local_width = width * (1.0 - 0.65*(i/max(1,len(pts)-1)))
        verts.append(p - side*local_width*0.5); verts.append(p + side*local_width*0.5)
    for i in range(len(pts)-1):
        faces.append((i*2, i*2+1, i*2+3, i*2+2))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata([tuple(v) for v in verts], [], faces); mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(bpy.data.materials.get(material_name) or ensure_material(material_name))
    move_to_collection(obj, "PA_02_HAIR")
    return obj


def build_hair_cards_from_blueprint(hair_config, armature=None):
    cards = hair_config.get("cards", [])
    if not cards: return {"status":"skipped"}
    created = []
    for idx, card in enumerate(cards):
        obj = create_hair_card_mesh(card.get("name",f"PA_HairCard_{idx:03d}"),
                                     card.get("points",[]),
                                     float(card.get("width",0.025)),
                                     card.get("material","MAT_PA_Hair_Black"))
        if obj:
            created.append(obj.name)
            if armature:
                target_bone = card.get("bone","mixamorig:Head")
                obj.vertex_groups.clear()
                vg = obj.vertex_groups.new(name=target_bone)
                vg.add([v.index for v in obj.data.vertices], 1.0, 'REPLACE')
                add_armature_modifier(obj, armature)
    return {"status":"success","created":created}


def clear_scene_objects():
    ensure_object_mode()
    for obj in list(bpy.context.scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def execute_layered_pipeline(source_path, template_path, manifest_path, masks_dir,
                              export_path=None, clear_scene=False,
                              character_name="Alice_Final"):
    try:
        if clear_scene: clear_scene_objects()
        ensure_project_collections()
        bootstrap_project_materials()
        config = load_manifest(manifest_path, masks_dir)
        if export_path: config.export_path = export_path
        imported_template = import_model(template_path, name_prefix="TPL")
        body = find_largest_mesh(imported_template)
        arm = find_first_armature(imported_template)
        if not body: raise RuntimeError("Template no body mesh")
        if not arm: raise RuntimeError("Template no armature")
        body.name = config.body_name; body.data.name = f"{config.body_name}_Mesh"
        normalize_mesh_to_height(body, config.target_height_m)
        move_to_collection(body, "PA_01_BODY")
        arm.name = config.armature_name
        move_to_collection(arm, "PA_01_BODY")
        imported_source = import_model(source_path, name_prefix="SRC")
        source = find_largest_mesh(imported_source)
        if not source: raise RuntimeError("Source no mesh")
        source.name = config.source_mesh_name
        source.data.name = f"{config.source_mesh_name}_Mesh"
        normalize_mesh_to_height(source, config.target_height_m)
        move_to_collection(source, "PA_00_REFERENCE")
        match_skeleton_proportions(source, arm)
        build_result = build_garment_layers(config)
        shape_result = apply_proportional_facial_shape_keys(config.body_name)
        finger_result = setup_advanced_finger_constraints(config.armature_name)
        shoulder_result = setup_shoulder_sleeve_helpers(config.armature_name)
        secondary_result = setup_secondary_dynamics_rig(config.armature_name)
        hair_result = build_hair_cards_from_blueprint(config.hair, arm)
        export_result = None
        if config.export_path:
            export_candidates = [o for o in bpy.data.objects
                                 if o.users_collection and any(c.name.startswith("PA_") for c in o.users_collection)
                                 and o.type in {"MESH","ARMATURE"} and not o.hide_render]
            export_result = export_glb(config.export_path, export_candidates)
        return json.dumps({"status":"SUCCESS","character":character_name,
                           "config":{"source_mesh_name":config.source_mesh_name,
                                     "body_name":config.body_name,
                                     "armature_name":config.armature_name,
                                     "masks_directory":config.masks_directory,
                                     "export_path":config.export_path},
                           "build":build_result,"shape_keys":shape_result,
                           "fingers":finger_result,"shoulders":shoulder_result,
                           "secondary":secondary_result,"hair":hair_result,
                           "export":export_result,
                           "guarantee":{"layer_order_source":"manifest.layer_index",
                                        "layer_order_guaranteed":True,
                                        "requires_uv_space_masks":True}},
                          ensure_ascii=False, indent=2)
    except Exception as ex:
        return json.dumps({"status":"ERROR","err":str(ex),
                           "trace":traceback.format_exc()},
                          ensure_ascii=False, indent=2)


def main():
    import sys
    args = sys.argv
    args = args[args.index("--")+1:] if "--" in args else []
    def get_arg(name, default=""):
        if name in args:
            idx = args.index(name)
            if idx+1 < len(args): return args[idx+1]
        return default
    print(execute_layered_pipeline(
        source_path=get_arg("--source"),
        template_path=get_arg("--template"),
        manifest_path=get_arg("--manifest"),
        masks_dir=get_arg("--masks"),
        export_path=get_arg("--export"),
        clear_scene=("--clear-scene" in args),
        character_name=get_arg("--name","Alice_Final")))


if __name__ == "__main__": main()
