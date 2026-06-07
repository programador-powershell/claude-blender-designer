"""
Blueprint procedural para o cabelo da Alice Liddell:
- preto;
- repartido ao meio;
- franja lateral leve;
- volume ondulado nas laterais;
- mechas longas descendo até abaixo do ombro;
- costas com massa ondulada para rig e movimento.
"""
from __future__ import annotations

import random, math
from hair_schema import HairBlueprint, HairGroup, HairCard, HairShader


def make_alice_liddell_hair(seed: int = 42) -> HairBlueprint:
    random.seed(seed)
    shader = HairShader(
        name="PA_Alice_Black_Hair_GodotHairInspired",
        albedo=(0.012, 0.010, 0.009),
        root_tint=(0.004, 0.003, 0.003),
        tip_tint=(0.045, 0.040, 0.036),
        longitudinal_roughness=0.30,
        azimuthal_roughness=0.82,
        specular=0.72,
        cuticle_tilt_offset=0.10,
        alpha_hash=True,
        use_anisotropic=True,
    )
    bp = HairBlueprint(
        character="Alice_Liddell",
        style_name="long_black_wavy_center_part_hair_cards",
        source_reference={
            "front": "input/characters/alice_head_front.png",
            "side": "input/characters/alice_head_side.png",
            "back": "input/characters/alice_head_back.png",
            "base_concept": "GodotHair hair-card approach"
        },
        shader=shader
    )

    groups = []

    bangs = HairGroup(id="bangs_center_part", label="Franja repartida ao meio", anchor_bone="Head", priority=1)
    for i in range(18):
        side = -1 if i < 9 else 1
        j = i % 9
        x = side * (0.012 + j * 0.007)
        root = (x, -0.085 + random.uniform(-0.01, 0.01), 1.735 + random.uniform(-0.015, 0.005))
        tip = (side * (0.055 + j * 0.004), -0.128 + random.uniform(-0.015, 0.015), 1.58 - j*0.008 + random.uniform(-0.015, 0.015))
        bangs.cards.append(HairCard(
            id=f"bang_{i:02d}",
            group=bangs.id,
            root=root,
            tip=tip,
            width_root_m=0.026,
            width_tip_m=0.004,
            segments=7,
            curve_strength=0.08,
            curl_turns=0.25 + random.random()*0.2,
            curl_radius_m=0.008,
            normal_bias=(side*0.2, -1, 0.05),
            layer=1,
            material=shader.name
        ))
    groups.append(bangs)

    side_locks = HairGroup(id="side_locks", label="Mechas laterais longas", anchor_bone="Head", priority=2)
    for side in [-1, 1]:
        for j in range(34):
            layer = j % 5
            root = (side*(0.055 + random.random()*0.07), -0.025 + random.uniform(-0.02, 0.03), 1.68 - layer*0.01)
            tip = (side*(0.16 + random.random()*0.08), -0.06 + random.uniform(-0.05, 0.06), 1.22 + random.uniform(-0.08, 0.12))
            side_locks.cards.append(HairCard(
                id=f"side_{'L' if side<0 else 'R'}_{j:02d}",
                group=side_locks.id,
                root=root,
                tip=tip,
                width_root_m=0.038 + random.random()*0.018,
                width_tip_m=0.006 + random.random()*0.004,
                segments=10,
                curve_strength=0.16 + random.random()*0.08,
                curl_turns=0.55 + random.random()*1.2,
                curl_radius_m=0.012 + random.random()*0.018,
                normal_bias=(side*0.55, -0.55, -0.05),
                layer=2 + layer,
                material=shader.name,
                opacity=0.92
            ))
    groups.append(side_locks)

    back = HairGroup(id="back_volume", label="Volume traseiro ondulado", anchor_bone="Head", priority=3)
    for j in range(90):
        band = j % 9
        x = random.uniform(-0.12, 0.12)
        root = (x, 0.065 + random.uniform(-0.02, 0.035), 1.69 - band*0.006)
        tip = (x + random.uniform(-0.10, 0.10), 0.10 + random.uniform(-0.03, 0.075), 1.10 + random.uniform(-0.10, 0.16))
        back.cards.append(HairCard(
            id=f"back_{j:03d}",
            group=back.id,
            root=root,
            tip=tip,
            width_root_m=0.045 + random.random()*0.020,
            width_tip_m=0.007 + random.random()*0.006,
            segments=11,
            curve_strength=0.19 + random.random()*0.08,
            curl_turns=0.8 + random.random()*1.5,
            curl_radius_m=0.012 + random.random()*0.025,
            normal_bias=(random.uniform(-0.15,0.15), 0.9, -0.05),
            layer=3 + band,
            material=shader.name,
            opacity=0.95
        ))
    groups.append(back)

    fly = HairGroup(id="flyaways", label="Fios soltos e silhueta irregular", anchor_bone="Head", priority=4)
    for j in range(42):
        side = -1 if j % 2 == 0 else 1
        root = (side*random.uniform(0.04, 0.14), random.uniform(-0.07, 0.08), random.uniform(1.42, 1.72))
        tip = (root[0] + side*random.uniform(0.04, 0.12), root[1] + random.uniform(-0.05, 0.05), root[2] - random.uniform(0.10, 0.28))
        fly.cards.append(HairCard(
            id=f"fly_{j:02d}",
            group=fly.id,
            root=root,
            tip=tip,
            width_root_m=0.010 + random.random()*0.006,
            width_tip_m=0.0015,
            segments=5,
            curve_strength=0.24,
            curl_turns=0.8 + random.random()*2.0,
            curl_radius_m=0.012,
            normal_bias=(side*0.8, random.uniform(-0.3,0.4), 0.0),
            layer=8,
            material=shader.name,
            opacity=0.55
        ))
    groups.append(fly)

    bp.groups = groups
    return bp


if __name__ == "__main__":
    make_alice_liddell_hair().save("alice_liddell_hair_blueprint.json")
