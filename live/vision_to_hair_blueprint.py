"""
Project Alice — Vision to Hair Blueprint

Este módulo define o contrato de saída para uma LLM Vision local.
Ela NÃO deve gerar descrição solta; deve classificar a imagem em grupos de cabelo:
bangs, side_locks, back_volume, loose_strands, accessories.

O output esperado é um JSON compatível com hair_schema.py.
"""

SYSTEM_PROMPT = """
Você é o analisador técnico de cabelo do Project Alice.

Base técnica:
- Use hair cards, não fios individuais.
- Cada card representa uma mecha/tufo.
- Organize por camadas: scalp_cap, bangs, side_locks, back_volume, flyaways.
- Não copie pixels; gere uma receita vetorial para Blender.

Entrada:
1. imagem da cabeça frente;
2. imagem lateral, se existir;
3. imagem costas, se existir;
4. máscara de cabelo;
5. landmarks aproximados de crânio/face.

Saída obrigatória:
JSON válido com:
- character;
- style_name;
- shader;
- groups[];
- cards[] com root, tip, width_root_m, width_tip_m, segments, curve_strength,
  curl_turns, curl_radius_m, normal_bias, layer, physics.

Regras:
- Cabelo da Alice: preto, longo, repartido ao meio, ondulado, volume lateral.
- Não deixe cards atravessarem olhos/boca.
- Preserve abertura frontal do rosto.
- A parte traseira deve ter massa suficiente para cobrir nuca e costas superiores.
- Use flyaways finos para silhueta natural.
- Se não tiver vista lateral/costas, marque incerteza no campo validation.
"""


def expected_schema_hint() -> dict:
    return {
        "character": "Alice_Liddell",
        "style_name": "long_black_wavy_center_part",
        "shader": {
            "albedo": [0.012, 0.010, 0.009],
            "longitudinal_roughness": 0.30,
            "azimuthal_roughness": 0.82,
            "specular": 0.72,
            "cuticle_tilt_offset": 0.10
        },
        "groups": [
            {
                "id": "bangs_center_part",
                "anchor_bone": "Head",
                "cards": [
                    {
                        "id": "bang_00",
                        "root": [0.02, -0.08, 1.72],
                        "tip": [0.08, -0.12, 1.55],
                        "width_root_m": 0.026,
                        "width_tip_m": 0.004,
                        "segments": 7
                    }
                ]
            }
        ]
    }
