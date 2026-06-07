# -*- coding: utf-8 -*-
"""Phase 1 AAA setup: 11 collections + 15 materials + 35 garment placeholders.
Conforme PROJECT ALICE v2 directive."""
import bpy

def setup_project_alice_pipeline():
    print("[PROJECT ALICE v2] Phase 1 AAA setup...")

    # Units METRIC 1 BU = 1 m
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 1.0
    bpy.context.scene.unit_settings.length_unit = 'METERS'

    # 11 Collections canonicas
    cols = ["PA_00_REFERENCE","PA_01_BODY","PA_02_HAIR","PA_03_GARMENT_INNER",
            "PA_04_GARMENT_OUTER","PA_05_ACCESSORIES","PA_06_WEAPONS","PA_07_VFX_PROXY",
            "PA_08_COLLISION","PA_09_EXPORT","PA_10_VALIDATION"]
    master = bpy.context.scene.collection
    created = {}
    for name in cols:
        if name not in bpy.data.collections:
            c = bpy.data.collections.new(name); master.children.link(c)
            print(f"  + col {name}")
        created[name] = bpy.data.collections[name]

    # 15 Materiais canonicos
    mats = ["MAT_PA_Skin_Pale","MAT_PA_Hair_Black",
            "MAT_PA_Fabric_Blue_Dark","MAT_PA_Fabric_Red_Queen","MAT_PA_Fabric_Purple_Cheshire",
            "MAT_PA_Lace_Black","MAT_PA_Lace_White","MAT_PA_Leather_Black",
            "MAT_PA_Metal_AntiqueGold","MAT_PA_Metal_BlackIron",
            "MAT_PA_Gem_Blue","MAT_PA_Gem_Red","MAT_PA_Gem_Purple",
            "MAT_PA_VFX_Smoke_Blue","MAT_PA_VFX_Smoke_Purple"]
    for mn in mats:
        if mn not in bpy.data.materials:
            m = bpy.data.materials.new(name=mn); m.use_nodes = True
            bsdf = m.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                if "Metal" in mn:
                    bsdf.inputs['Metallic'].default_value = 1.0
                    bsdf.inputs['Roughness'].default_value = 0.2
                elif "Gem" in mn:
                    bsdf.inputs['Roughness'].default_value = 0.05
                    if 'Transmission Weight' in bsdf.inputs:
                        bsdf.inputs['Transmission Weight'].default_value = 1.0
                elif "Leather" in mn:
                    bsdf.inputs['Roughness'].default_value = 0.4
            print(f"  + mat {mn}")

    # 35 Pecas placeholders
    pieces = {
        "01_torso_base_fabric":{"col":"PA_03_GARMENT_INNER","cat":"cloth","mat":"MAT_PA_Fabric_Blue_Dark"},
        "02_bust_panel_left":{"col":"PA_03_GARMENT_INNER","cat":"cloth","mat":"MAT_PA_Fabric_Blue_Dark"},
        "03_bust_panel_right":{"col":"PA_03_GARMENT_INNER","cat":"cloth","mat":"MAT_PA_Fabric_Blue_Dark"},
        "04_corset_front":{"col":"PA_04_GARMENT_OUTER","cat":"semi_rigid","mat":"MAT_PA_Leather_Black"},
        "05_corset_back":{"col":"PA_04_GARMENT_OUTER","cat":"semi_rigid","mat":"MAT_PA_Leather_Black"},
        "06_corset_side_left":{"col":"PA_04_GARMENT_OUTER","cat":"semi_rigid","mat":"MAT_PA_Leather_Black"},
        "07_corset_side_right":{"col":"PA_04_GARMENT_OUTER","cat":"semi_rigid","mat":"MAT_PA_Leather_Black"},
        "08_corset_lacing":{"col":"PA_04_GARMENT_OUTER","cat":"cloth","mat":"MAT_PA_Lace_Black"},
        "09_waist_belt_primary":{"col":"PA_05_ACCESSORIES","cat":"semi_rigid","mat":"MAT_PA_Leather_Black"},
        "10_waist_belt_secondary":{"col":"PA_05_ACCESSORIES","cat":"semi_rigid","mat":"MAT_PA_Leather_Black"},
        "11_inner_skirt":{"col":"PA_03_GARMENT_INNER","cat":"cloth","mat":"MAT_PA_Fabric_Blue_Dark"},
        "12_petticoat_volume":{"col":"PA_03_GARMENT_INNER","cat":"cloth","mat":"MAT_PA_Lace_White"},
        "13_middle_skirt_layer":{"col":"PA_04_GARMENT_OUTER","cat":"cloth","mat":"MAT_PA_Fabric_Blue_Dark"},
        "14_outer_skirt_layer":{"col":"PA_04_GARMENT_OUTER","cat":"cloth","mat":"MAT_PA_Fabric_Blue_Dark"},
        "15_left_overskirt":{"col":"PA_04_GARMENT_OUTER","cat":"cloth","mat":"MAT_PA_Fabric_Purple_Cheshire"},
        "16_right_overskirt":{"col":"PA_04_GARMENT_OUTER","cat":"cloth","mat":"MAT_PA_Fabric_Purple_Cheshire"},
        "17_front_apron_panel":{"col":"PA_04_GARMENT_OUTER","cat":"cloth","mat":"MAT_PA_Lace_White"},
        "18_back_bow":{"col":"PA_05_ACCESSORIES","cat":"cloth","mat":"MAT_PA_Fabric_Purple_Cheshire"},
        "19_sleeve_left":{"col":"PA_03_GARMENT_INNER","cat":"cloth","mat":"MAT_PA_Fabric_Blue_Dark"},
        "20_sleeve_right":{"col":"PA_03_GARMENT_INNER","cat":"cloth","mat":"MAT_PA_Fabric_Blue_Dark"},
        "21_cuff_left":{"col":"PA_04_GARMENT_OUTER","cat":"cloth","mat":"MAT_PA_Lace_White"},
        "22_cuff_right":{"col":"PA_04_GARMENT_OUTER","cat":"cloth","mat":"MAT_PA_Lace_White"},
        "23_lace_hem_inner":{"col":"PA_03_GARMENT_INNER","cat":"cloth","mat":"MAT_PA_Lace_White"},
        "24_lace_hem_outer":{"col":"PA_04_GARMENT_OUTER","cat":"cloth","mat":"MAT_PA_Lace_Black"},
        "25_chain_set_front":{"col":"PA_05_ACCESSORIES","cat":"rigid","mat":"MAT_PA_Metal_AntiqueGold"},
        "26_chain_set_side":{"col":"PA_05_ACCESSORIES","cat":"rigid","mat":"MAT_PA_Metal_AntiqueGold"},
        "27_pocket_watch":{"col":"PA_05_ACCESSORIES","cat":"rigid","mat":"MAT_PA_Metal_AntiqueGold"},
        "28_card_motifs":{"col":"PA_05_ACCESSORIES","cat":"accessory","mat":"MAT_PA_Lace_White"},
        "29_gem_brooch":{"col":"PA_05_ACCESSORIES","cat":"rigid","mat":"MAT_PA_Gem_Red"},
        "30_hair_accessory":{"col":"PA_02_HAIR","cat":"rigid","mat":"MAT_PA_Metal_BlackIron"},
        "31_boots_left":{"col":"PA_05_ACCESSORIES","cat":"semi_rigid","mat":"MAT_PA_Leather_Black"},
        "32_boots_right":{"col":"PA_05_ACCESSORIES","cat":"semi_rigid","mat":"MAT_PA_Leather_Black"},
        "33_gloves_left":{"col":"PA_03_GARMENT_INNER","cat":"cloth","mat":"MAT_PA_Leather_Black"},
        "34_gloves_right":{"col":"PA_03_GARMENT_INNER","cat":"cloth","mat":"MAT_PA_Leather_Black"},
        "35_vfx_layer":{"col":"PA_07_VFX_PROXY","cat":"vfx","mat":"MAT_PA_VFX_Smoke_Purple"},
    }
    count = 0
    for name, data in pieces.items():
        obj_name = f"PA_{name}"
        if obj_name not in bpy.data.objects:
            mesh = bpy.data.meshes.new(name=obj_name)
            obj = bpy.data.objects.new(obj_name, mesh)
            created[data["col"]].objects.link(obj)
            obj["piece_id"] = name; obj["category"] = data["cat"]
            obj["material_family"] = data["mat"].split("_")[3] if len(data["mat"].split("_"))>3 else "default"
            obj["collision_priority"] = 2 if data["cat"]=="semi_rigid" else (3 if data["cat"]=="rigid" else 1)
            obj["export_group"] = "hero"
            mat_ref = bpy.data.materials.get(data["mat"])
            if mat_ref: obj.data.materials.append(mat_ref)
            count += 1
    print(f"  + 35 placeholders ({count} novos)")
    print("[PROJECT ALICE v2] Phase 1 OK")

if __name__ == "__main__":
    setup_project_alice_pipeline()
