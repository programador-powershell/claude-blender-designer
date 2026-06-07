# -*- coding: utf-8 -*-
"""Loader genérico de outfit blueprint a partir de qualquer manifest auto-discovered.
Funciona pra chapeleiro (manual 22 pecas) ou pra outros 5 outfits gerados via discovery.

Mapeia shape strings do manifest (linguagem natural) -> shape primitives do garment_builder.
Heuristica: keywords no campo 'shape' -> shape canonico + params default.

Uso:
  from garment_outfit_loader import build_blueprint_for
  bp = build_blueprint_for('chapeleiro')   # ou 'cheshire','coelho','lagarta','rainha','base'
"""
from __future__ import annotations
import json, os, re
from garment_schema import OutfitBlueprint, GarmentPiece, AccessoryPiece, MaterialSpec

REGISTRY = r"D:/Alice/tools/auto-rig-fix/work/manifests/outfits_registry.json"
MANIFESTS_DIR = r"D:/Alice/tools/auto-rig-fix/work/manifests"


def _hex_to_rgba(h, a=1.0):
    h = h.lstrip('#')
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, a)


def _load_registry():
    with open(REGISTRY, encoding='utf-8') as f:
        return json.load(f)


def _shape_from_keywords(shape_str: str, name: str, z, level: str):
    """Heuristica: detecta shape primitive + params default a partir do texto."""
    s = (shape_str or '').lower(); n = (name or '').lower()
    z_bot, z_top = z[0], z[1]

    # Pares LR
    side = 'left' if (n.endswith('_esq') or 'left' in n or 'esq' in n) else (
           'right' if (n.endswith('_dir') or 'right' in n or 'dir' in n) else None)

    # Saias / tier / babado
    if 'tier' in s or 'renda' in s or 'lace' in s and 'saia' in s:
        return 'tiered_lace_skirt', {'waist_radius': 0.27, 'hem_radius': 0.95, 'z_top': z_top, 'z_bot': z_bot, 'tiers': 3}
    if 'saia' in s or 'skirt' in s or 'underskirt' in s:
        gap = 0.30 if 'principal' in n or 'a-line' in s or 'a line' in s else 0.0
        return 'skirt_ring', {'waist_radius': 0.27, 'hem_radius': 0.78, 'length': z_top - z_bot,
                              'folds': 36, 'segments': 120, 'front_gap': gap}
    if 'drape' in s:
        return 'drape_side_asym', {'side': side or 'right', 'z_top': z_top, 'z_bot': z_bot,
                                   'width_top': 0.18, 'width_bot': 0.35}
    # Corpete / espartilho
    if 'corpete' in s or 'corset' in s or 'espartilho' in s or 'bodice' in s:
        return 'corset', {'waist_radius': 0.20, 'bust_radius': 0.27, 'height': max(z_top - z_bot, 0.20)}
    # Sash / faixa
    if 'sash' in s or 'faixa' in s:
        return 'sash_band', {'z_top': z_top, 'z_bot': z_bot, 'radius_x': 0.24, 'radius_y': 0.17}
    # Bow / laco
    if 'bow' in s or 'laco' in n or 'lace ' in s and 'large' in s:
        return 'bow_3d', {'z': (z_top + z_bot) * 0.5, 'width': 0.34, 'height': 0.22, 'depth': 0.10}
    # Manga puff
    if 'manga' in s or 'sleeve' in s or 'puff' in s:
        return 'puff_sleeve', {'side': side or 'left', 'radius': 0.16, 'length': 0.22, 'puffs': 10}
    # Meia / stocking
    if 'meia' in s or 'stocking' in s or 'sock' in s:
        return 'stocking_leg', {'side': side or 'left', 'z_top': z_top, 'z_bot': z_bot, 'radius': 0.072}
    # Bota / boot
    if 'bota' in s or 'boot' in s:
        return 'high_boot', {'side': side or 'left', 'z_top': z_top, 'z_bot': z_bot,
                             'radius_shaft': 0.085, 'radius_foot': 0.075}
    # Luva / glove
    if 'luva' in s or 'glove' in s or 'fingerless' in s:
        return 'glove_forearm', {'side': side or 'left', 'z_top': z_top, 'z_bot': z_bot, 'radius': 0.055}
    # Choker
    if 'choker' in s or 'gargantilha' in s:
        return 'choker_band', {'z': (z_top + z_bot) * 0.5, 'radius': 0.058, 'height': 0.028}
    # Bloomer / shorts internos
    if 'bloomer' in s or 'shorts' in s or 'underwear' in s:
        return 'skirt_ring', {'waist_radius': 0.16, 'hem_radius': 0.18, 'length': z_top - z_bot,
                              'folds': 12, 'segments': 48}
    # Chemise / vestido base
    if 'chemise' in s or 'inner dress' in s or 'underdress' in s:
        return 'corset', {'waist_radius': 0.16, 'bust_radius': 0.20, 'height': 0.40}
    # Fallback panel
    return 'front_panel', {'width_top': 0.30, 'width_bottom': 0.45, 'length': z_top - z_bot,
                           'z_top': z_top, 'curve': 0.05}


def _accessory_from_keywords(shape_str: str, name: str, z):
    """Detecta se eh acessorio (hard prop). Retorna (shape, params) ou None."""
    s = (shape_str or '').lower(); n = (name or '').lower()
    z_bot, z_top = z[0], z[1]
    z_mid = (z_top + z_bot) * 0.5
    if 'hat' in s or 'chapeu' in n or 'top hat' in s:
        return 'mini_top_hat', {'tilt': -0.18, 'z': z_mid, 'off_x': 0.04,
                                'radius_crown': 0.06, 'height_crown': 0.10, 'radius_brim': 0.10}
    if 'watch' in s or 'relogio' in n or 'pocket' in s:
        return 'pocket_watch', {'side': 'right', 'radius': 0.045, 'z': z_mid}
    if 'key' in s or 'chave' in n:
        return 'pendant_key', {'x': 0, 'y': -0.12, 'z': z_mid, 'shaft': 0.06, 'bow_r': 0.014}
    if 'cards' in s or 'cartas' in n or 'charm' in s:
        return 'pendant_cards_charm', {'x': 0.22, 'y': -0.20, 'z': z_mid, 'count': 3}
    if 'gem' in s or 'pendant' in s or 'jewel' in s or 'pedra' in s:
        return 'pendant_sphere', {'x': 0, 'y': -0.10, 'z': z_mid, 'radius': 0.020}
    if 'belt' in s or 'cinto' in n:
        return 'torus_belt', {'radius_x': 0.30, 'radius_y': 0.22, 'z': z_mid}
    return None


def build_blueprint_for(outfit_name: str) -> OutfitBlueprint:
    """Carrega manifest do outfit + monta OutfitBlueprint mapeado."""
    reg = _load_registry()
    if outfit_name not in reg['outfits']:
        raise KeyError(f"outfit '{outfit_name}' nao encontrado no registry")
    cfg = reg['outfits'][outfit_name]
    manifest_path = os.path.join(MANIFESTS_DIR, cfg['manifest'])
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"manifest nao existe: {manifest_path}\n"
                                f"  Rode: python pipeline_outfit_discovery.py --outfit {outfit_name}")

    with open(manifest_path, encoding='utf-8') as f:
        m = json.load(f)

    palette = m.get('_palette_global', {})
    mats = [
        MaterialSpec('teal_principal',   _hex_to_rgba(palette.get('verde_teal_principal', '#2D4438')), 0.78, 0.0),
        MaterialSpec('creme_underdress', _hex_to_rgba(palette.get('creme_underdress', '#C9B68F')), 0.82, 0.0),
        MaterialSpec('preto_lace',       _hex_to_rgba(palette.get('preto_lace', '#0E0D0C'), 0.78), 0.85, 0.0),
        MaterialSpec('couro_bota',       _hex_to_rgba(palette.get('couro_bota_preto', '#1A1612')), 0.50, 0.05),
        MaterialSpec('ouro_metal',       _hex_to_rgba(palette.get('ouro_metais', '#9A7A2E')), 0.38, 0.80),
        MaterialSpec('branco_chemise',   _hex_to_rgba(palette.get('branco_chemise_interna', '#E5DCC5')), 0.78, 0.0),
        MaterialSpec('paper_card',       (0.82, 0.78, 0.67, 1.0), 0.70, 0.0),
        MaterialSpec('vermelho_rainha',  (0.78, 0.05, 0.07, 1.0), 0.62, 0.0),
        MaterialSpec('roxo_lagarta',     (0.30, 0.10, 0.45, 1.0), 0.72, 0.0),
        MaterialSpec('rosa_gato',        (0.92, 0.42, 0.68, 1.0), 0.70, 0.0),
        MaterialSpec('azul_coelho',      (0.18, 0.42, 0.85, 1.0), 0.70, 0.0),
    ]
    HEX2MAT = {
        '#2D4438': 'teal_principal', '#C9B68F': 'creme_underdress',
        '#0E0D0C': 'preto_lace', '#1A1612': 'couro_bota',
        '#9A7A2E': 'ouro_metal', '#E5DCC5': 'branco_chemise',
    }
    def mat_for(hex_color: str) -> str:
        hc = (hex_color or '#888888').upper()
        if hc in HEX2MAT: return HEX2MAT[hc]
        # closest by simple heuristic (R/G/B dominance)
        try:
            r = int(hc[1:3], 16); g = int(hc[3:5], 16); b = int(hc[5:7], 16)
            if r > 150 and g < 100 and b < 100: return 'vermelho_rainha'
            if r > 200 and g > 200 and b < 150: return 'creme_underdress'
            if r > 200 and g > 100 and b > 150: return 'rosa_gato'
            if b > 150 and r < 100: return 'azul_coelho'
            if r > 100 and g < 80 and b > 100: return 'roxo_lagarta'
            if r < 50 and g < 50 and b < 50: return 'preto_lace'
        except Exception:
            pass
        return 'teal_principal'

    pieces = []; acc = []
    for p in m['pieces']:
        name = p['name']; lvl = p.get('level', 'SOBREPOSICAO')
        z = p.get('z', [0.0, 1.0]); shape_str = p.get('shape', '')
        mat = mat_for(p.get('color_hex'))
        anchors = [p.get('bone_anchor', 'mixamorig:Hips')]
        order = p.get('order', len(pieces) + 1)

        # Detecta acessorio
        acc_match = _accessory_from_keywords(shape_str, name, z)
        if acc_match and lvl == 'METALS_PROPS' and not any(k in name for k in ['bota', 'luva', 'meia']):
            shape, params = acc_match
            acc.append(AccessoryPiece(name, 'prop', order, mat, shape, None, params))
            continue

        # Detecta piece
        shape, params = _shape_from_keywords(shape_str, name, z, lvl)
        rigidity = p.get('rigidity', 'soft_cloth')
        physics = 'cloth' if rigidity == 'soft_cloth' else 'fitted'
        thickness = 0.003 if rigidity == 'soft_cloth' else 0.005
        pieces.append(GarmentPiece(name, lvl.lower(), order, mat, shape, anchors,
                                   physics, thickness, params=params))

    build_order = ([p.id for p in sorted(pieces, key=lambda x: x.layer)] +
                   [a.id for a in sorted(acc, key=lambda x: x.layer)])
    notes = [
        f"Outfit: {cfg['display_name']}",
        f"Manifest: {manifest_path}",
        f"Refs: {cfg['refs_dir']}",
        "Generalist loader — params default; refine via inspecao Blender."
    ]
    return OutfitBlueprint(f'alice_{outfit_name}_layered',
                           cfg['display_name'],
                           version='1.0', target_character='Alice_Base_Body',
                           materials=mats, pieces=pieces, accessories=acc,
                           build_order=build_order, notes=notes)


if __name__ == '__main__':
    import sys
    outfit = sys.argv[1] if len(sys.argv) > 1 else 'chapeleiro'
    bp = build_blueprint_for(outfit)
    print(f"outfit: {bp.outfit_id}")
    print(f"pieces: {len(bp.pieces)} | acc: {len(bp.accessories)} | order: {len(bp.build_order)}")
    for p in bp.pieces[:5]:
        print(f"  - {p.id} ({p.shape})")
