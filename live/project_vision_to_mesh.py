# -*- coding: utf-8 -*-
"""Projeta curvas 2D (u,v) de vision JSON na superficie 3D do corpo via BVH raycast.
Cada curve vira mesh anatomicamente colada no corpo + Shrinkwrap + Solidify + Subsurf."""
import bpy, bmesh, json, mathutils
from mathutils.bvhtree import BVHTree


def project_vision_coordinates_to_mesh(base_body_name, vision_json_path, camera_distance=3.0):
    """Projeta coords 2D (u,v) da IA direto na superficie 3D do corpo via BVH."""
    print("[PROJECT ALICE] Remodelagem optica de alta precisao...")
    base_body = bpy.data.objects.get(base_body_name)
    if not base_body:
        raise RuntimeError(f"Corpo base '{base_body_name}' nao encontrado.")

    bpy.context.view_layer.objects.active = base_body
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    with open(vision_json_path, 'r', encoding='utf-8') as f:
        vision_data = json.load(f)

    curves = vision_data.get("curves", [])
    if not curves:
        print("[AVISO] Nenhuma curva no JSON."); return

    mesh_data = base_body.to_mesh()
    bvh = BVHTree.FromMesh(mesh_data)

    bbox = [base_body.matrix_world @ mathutils.Vector(c) for c in base_body.bound_box]
    min_x = min(v.x for v in bbox); max_x = max(v.x for v in bbox)
    min_z = min(v.z for v in bbox); max_z = max(v.z for v in bbox)
    center_y = sum(v.y for v in bbox) / len(bbox)
    width_3d = max_x - min_x; height_3d = max_z - min_z

    created = []
    for idx, curve in enumerate(curves):
        label = curve.get("label", f"componente_{idx}")
        points = curve.get("points", [])
        if len(points) < 3: continue

        comp_mesh = bpy.data.meshes.new(name=f"Mesh_{label}")
        comp_obj = bpy.data.objects.new(f"PA_Garment_{label}", comp_mesh)
        target_col = bpy.data.collections.get("PA_04_GARMENT_OUTER") or bpy.context.scene.collection
        target_col.objects.link(comp_obj)

        bm = bmesh.new()
        mesh_verts = []
        for pt in points:
            u, v = pt[0], pt[1]
            proj_x = min_x + (u * width_3d)
            proj_z = min_z + ((1.0 - v) * height_3d)
            ray_origin = mathutils.Vector((proj_x, center_y - camera_distance, proj_z))
            ray_direction = mathutils.Vector((0.0, 1.0, 0.0))
            location, normal, index, distance = bvh.ray_cast(ray_origin, ray_direction)
            if location is None:
                location = mathutils.Vector((proj_x, center_y, proj_z))
            v_mesh = bm.verts.new(location)
            mesh_verts.append(v_mesh)

        bm.verts.ensure_lookup_table()
        for i in range(len(mesh_verts) - 1):
            bm.edges.new((mesh_verts[i], mesh_verts[i+1]))
        if len(mesh_verts) > 3 and points[0] == points[-1]:
            bm.edges.new((mesh_verts[-1], mesh_verts[0]))

        bm.to_mesh(comp_mesh); bm.free()
        _apply_shaping_modifiers(comp_obj, base_body)
        created.append(comp_obj.name)

    base_body.to_mesh_clear()
    print(f"[PROJECT ALICE] {len(created)} componentes moldados: {created}")
    return created


def _apply_shaping_modifiers(garment_obj, body_obj):
    """Stack engenharia: Shrinkwrap snap + Solidify + Subsurf."""
    sw = garment_obj.modifiers.new("Anatomical_Snap", 'SHRINKWRAP')
    sw.target = body_obj; sw.wrap_method = 'PROJECT'
    sw.use_project_y = True
    sw.use_negative_direction = True; sw.use_positive_direction = True

    sol = garment_obj.modifiers.new("Garment_Thickness", 'SOLIDIFY')
    sol.thickness = 0.0020; sol.offset = 1.0

    sub = garment_obj.modifiers.new("Topology_Smooth", 'SUBSURF')
    sub.levels = 1
