# -*- coding: utf-8 -*-
from garment_schema import OutfitBlueprint, GarmentPiece, AccessoryPiece, MaterialSpec

def build_blueprint() -> OutfitBlueprint:
    mats = [
        MaterialSpec('ivory_fabric', (0.78, 0.72, 0.62, 1), 0.78, 0),
        MaterialSpec('dark_blue_fabric', (0.015, 0.025, 0.055, 1), 0.82, 0),
        MaterialSpec('black_lace', (0.005, 0.004, 0.006, 0.78), 0.9, 0),
        MaterialSpec('aged_gold', (0.9, 0.63, 0.26, 1), 0.38, 0.8),
        MaterialSpec('black_leather', (0.01, 0.008, 0.006, 1), 0.5, 0.05),
        MaterialSpec('blood_red', (0.35, 0.01, 0.015, 1), 0.58, 0),
        MaterialSpec('paper_card', (0.82, 0.78, 0.67, 1), 0.7, 0),
    ]
    pieces = [
        GarmentPiece('base_ivory_bodice','fitted_panel',1,'ivory_fabric','torso_shell',['spine','chest','neck'],'fitted',0.004,params={'neck':'deep_v'}),
        GarmentPiece('dark_corset','fitted_panel',2,'black_leather','corset',['spine','chest','waist'],'fitted',0.006,params={'waist_radius':0.26,'bust_radius':0.38,'height':0.46}),
        GarmentPiece('inner_black_petticoat','cloth_layer',3,'black_lace','skirt_ring',['hips','waist'],'cloth',0.003,params={'waist_radius':0.28,'hem_radius':0.92,'length':0.72,'folds':36,'segments':144}),
        GarmentPiece('ivory_front_apron','cloth_panel',4,'ivory_fabric','front_panel',['waist'],'cloth',0.004,params={'width_top':0.36,'width_bottom':0.54,'length':0.68,'z_top':0.92,'curve':0.08}),
        GarmentPiece('outer_dark_skirt','cloth_layer',5,'dark_blue_fabric','skirt_ring',['hips','waist'],'cloth',0.004,params={'waist_radius':0.31,'hem_radius':1.05,'length':0.77,'folds':42,'segments':168,'front_gap':0.42}),
        GarmentPiece('side_overskirt_left','cloth_panel',6,'dark_blue_fabric','side_panel',['waist'],'cloth',0.004,params={'side':'left','width_top':0.25,'width_bottom':0.48,'length':0.62}),
        GarmentPiece('side_overskirt_right','cloth_panel',6,'dark_blue_fabric','side_panel',['waist'],'cloth',0.004,params={'side':'right','width_top':0.25,'width_bottom':0.48,'length':0.62}),
        GarmentPiece('back_bow_panel','cloth_panel',7,'dark_blue_fabric','bow_tail',['spine','waist'],'cloth',0.004,params={'width':0.62,'length':0.52,'z_top':0.98}),
        GarmentPiece('puff_sleeve_left','sleeve',8,'dark_blue_fabric','puff_sleeve',['left_upper_arm','shoulder'],'cloth',0.004,params={'side':'left','radius':0.18,'length':0.24,'puffs':10}),
        GarmentPiece('puff_sleeve_right','sleeve',8,'dark_blue_fabric','puff_sleeve',['right_upper_arm','shoulder'],'cloth',0.004,params={'side':'right','radius':0.18,'length':0.24,'puffs':10}),
        GarmentPiece('lace_hem_outer','trim',9,'black_lace','hem_ruffle_ring',['outer_dark_skirt'],'cloth',0.002,params={'radius':1.06,'z':0.18,'height':0.10,'waves':56}),
        GarmentPiece('lace_hem_inner','trim',9,'black_lace','hem_ruffle_ring',['inner_black_petticoat'],'cloth',0.002,params={'radius':0.94,'z':0.16,'height':0.08,'waves':48}),
    ]
    acc = [
        AccessoryPiece('front_lacing_cross','cord',10,'aged_gold','corset_lacing','dark_corset',{'count':7,'width':0.19,'z_min':1.05,'z_max':1.38}),
        AccessoryPiece('waist_belt','belt',11,'black_leather','torus_belt','dark_corset',{'radius_x':0.34,'radius_y':0.24,'z':0.93}),
        AccessoryPiece('clock_left_hip','clock',12,'aged_gold','pocket_watch','outer_dark_skirt',{'side':'left','radius':0.075,'z':0.78}),
        AccessoryPiece('card_motifs_skirt','cards',13,'paper_card','scattered_cards','outer_dark_skirt',{'count':18,'radius':0.88}),
        AccessoryPiece('gold_embroidery_curves','embroidery',14,'aged_gold','embroidery_curves','outer_dark_skirt',{'count':26}),
        AccessoryPiece('red_rose_brooches','brooches',15,'blood_red','rose_brooches','outer_dark_skirt',{'count':7}),
        AccessoryPiece('mini_hat','hat',18,'dark_blue_fabric','mini_top_hat',None,{'tilt':-0.18}),
    ]
    return OutfitBlueprint('alice_dark_dress_layered','Alice Liddell — Dark Layered Dress',materials=mats,pieces=pieces,accessories=acc,build_order=[p.id for p in sorted(pieces,key=lambda p:p.layer)]+[a.id for a in sorted(acc,key=lambda a:a.layer)],notes=['Blueprint inicial: refine com tracing manual para fidelidade perfeita.'])

if __name__ == '__main__':
    print(build_blueprint().to_json())
