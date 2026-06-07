# Alice Chapeleiro — Build Piece-by-Piece + Hair

Pipeline procedural integrado a partir do pacote `claude-blender-designer-garment-update`,
adaptado ao manifest existente `work/alice_chapeleiro_manifest.json` (22 pecas canonicas).

## Pre-requisitos

1. Blender 5.x aberto com `claude_bridge.py` rodando (Text Editor > Run Script). Portas 9877-9881.
2. Cena com `Alice_Base_Body` (mesh) + `Alice_Base_Rig` (armature Mixamo) ja importados.
3. CWD ao executar: `D:\Alice\tools\auto-rig-fix\`.

## Fluxo recomendado piece-by-piece

```bash
# 1) lista build_order (25 itens: 19 pieces + 6 accessories)
python pipeline_garment_builder.py --chapeleiro --list-pieces

# 2) constroi UMA peca, valida com renders 3-views
python pipeline_garment_builder.py --chapeleiro --piece bloomer_interno --validate-render

# 3) se ruim: remove e reconstroi com params ajustados
python pipeline_garment_builder.py --chapeleiro --remove-piece bloomer_interno
# (editar live/garment_alice_chapeleiro.py params)
python pipeline_garment_builder.py --chapeleiro --piece bloomer_interno --validate-render

# 4) avanca pra proxima peca
python pipeline_garment_builder.py --chapeleiro --piece chemise_branca_torso --validate-render
```

## Ordem canonica (Inside-Out)

| # | piece_id | shape | bone_anchor |
|---|----------|-------|-------------|
|01| bloomer_interno | skirt_ring | mixamorig:Hips |
|02| chemise_branca_torso | corset | mixamorig:Spine1 |
|02| chemise_branca_skirt | skirt_ring | mixamorig:Spine1 |
|03| meia_listrada_esq | stocking_leg | LeftLeg |
|04| meia_listrada_dir | stocking_leg | RightLeg |
|05| bota_alta_esq | high_boot | LeftFoot |
|06| bota_alta_dir | high_boot | RightFoot |
|07| saia_lace_preta_L3 | tiered_lace_skirt (3 tiers) | Hips |
|08| saia_cream_underskirt | skirt_ring | Hips |
|09| saia_teal_L1_principal | skirt_ring (front_gap) | Hips |
|10| saia_teal_drape_lateral | drape_side_asym | Hips |
|11| sash_faixa_cintura | sash_band | Spine |
|12| laco_costas_grande | bow_3d | Spine |
|13| corpete_teal_principal | corset + lace_cross_corset | Spine1 |
|14| manga_puff_esq | puff_sleeve | LeftArm |
|15| manga_puff_dir | puff_sleeve | RightArm |
|16| luva_curta_esq | glove_forearm | LeftHand |
|17| luva_curta_dir | glove_forearm | RightHand |
|18| choker_decote | choker_band + pendant_sphere | Neck |
|19| chapeu_coquinho_top | mini_top_hat | Head |
|20| relogio_cintura_pendant | pocket_watch | Spine |
|21| chave_colar_pendant | pendant_key | Neck |
|22| cartas_charm_pendant | pendant_cards_charm | Spine |

## Hair (218 cards)

```bash
# preset Alice cabelo preto longo ondulado (gera blueprint)
python pipeline_hair_builder.py --preset alice --save examples/alice_liddell_hair_blueprint.json

# constroi no Blender (precisa bridge rodando)
python pipeline_hair_builder.py --blueprint examples/alice_liddell_hair_blueprint.json --build
```

Grupos: `bangs_center_part` 18 + `side_locks` 68 + `back_volume` 90 + `flyaways` 42 = **218 cards**.
Material: `PA_Alice_Black_Hair_GodotHairInspired` (anisotropic, alpha hash).
Conceito: hair cards inspirados em 2Retr0/GodotHair (NAO bundla assets).

## Arquitetura

```
live/
  garment_schema.py            Dataclasses OutfitBlueprint/Piece/Accessory/Material
  garment_builder.py           20+ shapes proceduais (skirt/corset/boot/bow/etc)
  garment_alice_chapeleiro.py  Le manifest -> OutfitBlueprint mapeado
  garment_alice_dark_dress.py  Blueprint exemplo (Dark Dress, NAO usado p/ chapeleiro)
  garment_fit_to_body.py       Collision corpo + pin top vertices (cloth)
  garment_validation_render.py Cameras ortho front/side/back + render

  hair_schema.py               Dataclasses HairBlueprint/HairCard/HairGroup/Shader
  hair_card_builder.py         Construtor hair cards no Blender
  hair_alice_liddell.py        Preset Alice (218 cards procedurais)

pipeline_garment_builder.py    Orchestrator CLI (--chapeleiro --piece <id>)
pipeline_hair_builder.py       Orchestrator CLI (--preset alice --build)

examples/
  alice_chapeleiro_blueprint.json  Blueprint exportado (25 itens)
  alice_liddell_hair_blueprint.json Blueprint hair (218 cards)
```

## Refino futuro

- Substituir shapes proceduais por trace real via `vision_to_garment_blueprint.py`
  (input: imagens front/side/back -> JSON molde refinado).
- Ajustar params em `garment_alice_chapeleiro.py` apos cada validate-render.
- Hair: trocar shader Principled por Hair BSDF aniso real quando Blender suportar.
