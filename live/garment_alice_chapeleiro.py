# -*- coding: utf-8 -*-
"""Alice Chapeleiro — blueprint procedural a partir do manifest 22 pecas.
Le alice_chapeleiro_manifest.json e gera OutfitBlueprint compativel
com garment_builder.build_garment_from_blueprint / build_single_piece.

Mapeamento manifest -> shape:
  TECIDO_BASE bloomer       -> skirt_ring curto
  TECIDO_BASE chemise       -> corset + skirt_ring (vestido base)
  SOBREPOSICAO meia         -> stocking_leg
  METALS_PROPS bota         -> high_boot
  SOBREPOSICAO saia_lace    -> tiered_lace_skirt
  SOBREPOSICAO saia_cream   -> skirt_ring + front_panel cards
  SOBREPOSICAO saia_teal_L1 -> skirt_ring
  SOBREPOSICAO drape_lateral-> drape_side_asym
  COMPRESSAO sash           -> sash_band
  METALS_PROPS laco_costas  -> bow_3d
  COMPRESSAO corpete        -> corset + lace_cross_corset
  SOBREPOSICAO manga_puff   -> puff_sleeve
  METALS_PROPS luva         -> glove_forearm
  METALS_PROPS choker       -> choker_band + pendant_sphere
  METALS_PROPS chapeu       -> mini_top_hat
  METALS_PROPS relogio      -> pocket_watch
  METALS_PROPS chave        -> pendant_key
  METALS_PROPS cartas       -> pendant_cards_charm
"""
from __future__ import annotations
import json, os
from garment_schema import OutfitBlueprint, GarmentPiece, AccessoryPiece, MaterialSpec

MANIFEST_DEFAULT = r"D:/Alice/tools/auto-rig-fix/work/alice_chapeleiro_manifest.json"

def _hex_to_rgba(h, a=1.0):
    h=h.lstrip('#')
    return (int(h[0:2],16)/255.0, int(h[2:4],16)/255.0, int(h[4:6],16)/255.0, a)

def build_blueprint(manifest_path: str = MANIFEST_DEFAULT) -> OutfitBlueprint:
    with open(manifest_path, encoding='utf-8') as f:
        m=json.load(f)
    palette = m.get('_palette_global', {})
    # 6 materiais canonicos da paleta + paper_card auxiliar
    mats=[
        MaterialSpec('teal_principal',  _hex_to_rgba(palette.get('verde_teal_principal','#2D4438')), 0.78, 0.0),
        MaterialSpec('creme_underdress',_hex_to_rgba(palette.get('creme_underdress','#C9B68F')), 0.82, 0.0),
        MaterialSpec('preto_lace',      _hex_to_rgba(palette.get('preto_lace','#0E0D0C'), 0.78), 0.85, 0.0),
        MaterialSpec('couro_bota',      _hex_to_rgba(palette.get('couro_bota_preto','#1A1612')), 0.50, 0.05),
        MaterialSpec('ouro_metal',      _hex_to_rgba(palette.get('ouro_metais','#9A7A2E')), 0.38, 0.80),
        MaterialSpec('branco_chemise',  _hex_to_rgba(palette.get('branco_chemise_interna','#E5DCC5')), 0.78, 0.0),
        MaterialSpec('paper_card',      (0.82,0.78,0.67,1.0), 0.70, 0.0),
    ]
    # Mapa hex->material id
    HEX2MAT = {
        '#2D4438':'teal_principal',
        '#C9B68F':'creme_underdress',
        '#0E0D0C':'preto_lace',
        '#1A1612':'couro_bota',
        '#9A7A2E':'ouro_metal',
        '#E5DCC5':'branco_chemise',
    }
    def mat_for(hex_color: str) -> str:
        return HEX2MAT.get(hex_color, 'teal_principal')

    pieces=[]; acc=[]
    for p in m['pieces']:
        name=p['name']; lvl=p['level']; z=p['z']; mat=mat_for(p['color_hex'])
        anchors=[p['bone_anchor']]
        z_bot, z_top = z[0], z[1]

        if name=='bloomer_interno':
            pieces.append(GarmentPiece(name,'cloth_layer',p['order'],mat,'skirt_ring',anchors,'cloth',0.003,
                params={'waist_radius':0.16,'hem_radius':0.18,'length':z_top-z_bot,'folds':12,'segments':48}))
        elif name=='chemise_branca':
            pieces.append(GarmentPiece(name+'_torso','fitted_panel',p['order'],mat,'corset',anchors,'fitted',0.003,
                params={'waist_radius':0.16,'bust_radius':0.20,'height':0.40}))
            pieces.append(GarmentPiece(name+'_skirt','cloth_layer',p['order'],mat,'skirt_ring',anchors,'cloth',0.003,
                params={'waist_radius':0.17,'hem_radius':0.32,'length':0.55,'folds':24,'segments':72}))
        elif name.startswith('meia_listrada'):
            side='left' if name.endswith('_esq') else 'right'
            pieces.append(GarmentPiece(name,'fitted_panel',p['order'],mat,'stocking_leg',anchors,'fitted',0.002,
                params={'side':side,'z_top':z_top,'z_bot':z_bot,'radius':0.072}))
        elif name.startswith('bota_alta'):
            side='left' if name.endswith('_esq') else 'right'
            pieces.append(GarmentPiece(name,'fitted_panel',p['order'],mat,'high_boot',anchors,'fitted',0.005,
                params={'side':side,'z_top':z_top,'z_bot':z_bot,'radius_shaft':0.085,'radius_foot':0.075}))
        elif name=='saia_lace_preta_L3':
            pieces.append(GarmentPiece(name,'cloth_layer',p['order'],mat,'tiered_lace_skirt',anchors,'cloth',0.003,
                params={'waist_radius':0.27,'hem_radius':0.95,'z_top':z_top,'z_bot':z_bot,'tiers':3}))
        elif name=='saia_cream_underskirt':
            pieces.append(GarmentPiece(name,'cloth_layer',p['order'],mat,'skirt_ring',anchors,'cloth',0.003,
                params={'waist_radius':0.27,'hem_radius':0.85,'length':z_top-z_bot,'folds':36,'segments':120}))
        elif name=='saia_teal_L1_principal':
            pieces.append(GarmentPiece(name,'cloth_layer',p['order'],mat,'skirt_ring',anchors,'cloth',0.004,
                params={'waist_radius':0.27,'hem_radius':0.78,'length':z_top-z_bot,'folds':42,'segments':144,'front_gap':0.30}))
        elif name=='saia_teal_drape_lateral':
            pieces.append(GarmentPiece(name,'cloth_panel',p['order'],mat,'drape_side_asym',anchors,'cloth',0.004,
                params={'side':'right','z_top':z_top,'z_bot':z_bot,'width_top':0.18,'width_bot':0.35}))
        elif name=='sash_faixa_cintura':
            pieces.append(GarmentPiece(name,'fitted_panel',p['order'],mat,'sash_band',anchors,'fitted',0.005,
                params={'z_top':z_top,'z_bot':z_bot,'radius_x':0.24,'radius_y':0.17}))
        elif name=='laco_costas_grande':
            pieces.append(GarmentPiece(name,'fitted_panel',p['order'],mat,'bow_3d',anchors,'none',0.004,
                params={'z':(z_top+z_bot)*0.5,'width':0.34,'height':0.22,'depth':0.10}))
        elif name=='corpete_teal_principal':
            pieces.append(GarmentPiece(name,'fitted_panel',p['order'],mat,'corset',anchors,'fitted',0.005,
                params={'waist_radius':0.20,'bust_radius':0.27,'height':z_top-z_bot}))
            acc.append(AccessoryPiece(name+'_laces','cord',p['order']+1,'ouro_metal','lace_cross_corset',name,
                {'width':0.18,'count':7,'z_min':z_bot+0.02,'z_max':z_top-0.02}))
        elif name.startswith('manga_puff'):
            side='left' if name.endswith('_esq') else 'right'
            pieces.append(GarmentPiece(name,'sleeve',p['order'],mat,'puff_sleeve',anchors,'cloth',0.004,
                params={'side':side,'radius':0.16,'length':0.22,'puffs':10}))
        elif name.startswith('luva_curta'):
            side='left' if name.endswith('_esq') else 'right'
            pieces.append(GarmentPiece(name,'fitted_panel',p['order'],mat,'glove_forearm',anchors,'fitted',0.003,
                params={'side':side,'z_top':z_top,'z_bot':z_bot,'radius':0.055}))
        elif name=='choker_decote':
            pieces.append(GarmentPiece(name,'fitted_panel',p['order'],mat,'choker_band',anchors,'fitted',0.002,
                params={'z':(z_top+z_bot)*0.5,'radius':0.058,'height':0.028}))
            acc.append(AccessoryPiece(name+'_gem','gem',p['order']+1,'ouro_metal','pendant_sphere',name,
                {'x':0,'y':-0.058,'z':(z_top+z_bot)*0.5,'radius':0.014}))
        elif name=='chapeu_coquinho_top':
            acc.append(AccessoryPiece(name,'hat',p['order'],mat,'mini_top_hat',None,
                {'tilt':-0.18,'z':(z_top+z_bot)*0.5,'off_x':0.04,'radius_crown':0.06,'height_crown':0.10,'radius_brim':0.10}))
        elif name=='relogio_cintura_pendant':
            acc.append(AccessoryPiece(name,'clock',p['order'],mat,'pocket_watch',None,
                {'side':'right','radius':0.045,'z':(z_top+z_bot)*0.5}))
        elif name=='chave_colar_pendant':
            acc.append(AccessoryPiece(name,'pendant',p['order'],mat,'pendant_key',None,
                {'x':0,'y':-0.12,'z':(z_top+z_bot)*0.5,'shaft':0.06,'bow_r':0.014}))
        elif name=='cartas_charm_pendant':
            acc.append(AccessoryPiece(name,'charm',p['order'],'paper_card','pendant_cards_charm',None,
                {'x':0.22,'y':-0.20,'z':(z_top+z_bot)*0.5,'count':3}))

    build_order=[p.id for p in sorted(pieces,key=lambda x:x.layer)] + \
                [a.id for a in sorted(acc,key=lambda x:x.layer)]
    notes=[
        'Inside-Out 22 pecas Alice Chapeleiro',
        'Build piece-by-piece via build_single_piece(bp, piece_id)',
        'Refs costureira em C:/Users/pslo9/Downloads/Alice chapeleiro/',
    ]
    return OutfitBlueprint('alice_chapeleiro_layered',
                           'Alice Liddell - Chapeleiro 22 pecas',
                           version='1.0', target_character='Alice_Base_Body',
                           materials=mats, pieces=pieces, accessories=acc,
                           build_order=build_order, notes=notes)

if __name__ == '__main__':
    bp=build_blueprint()
    print(bp.to_json())
