# -*- coding: utf-8 -*-
"""Templates de prompts vision (Qwen3-VL/Florence2/GPT-Image-2 compativeis).
Baseado em patterns curados de EvoLinkAI/awesome-gpt-image-2-API-and-Prompts.

Patterns chave:
1. Identity preservation: "Use uploaded ref as exact reference. Maintain [features]"
2. Multi-criteria comparison: "Compare images per criteria: [list]. Score each."
3. Reference-based extraction: "Identify ONLY [target]. Preserve color/shape/proportions."
"""
from __future__ import annotations

# ============ EXTRACTION (1 piece from step image) ============
PIECE_EXTRACTION = """SUBJECT: Use uploaded reference image. Identify ONLY the garment piece "{piece_name}" ({shape_hint}).

REFERENCE CRITERIA - preserve these exactly:
- Color: dominant + secondary RGB values (sample from masked region)
- Shape: outline keywords (3-5 short tags)
- Position: bbox normalized (x0,y0,x1,y1) in front view turnaround
- Proportions: z_world meters [z_bot, z_top] on 1.70m character
- Symmetry: wraps_360 / is_paired_LR
- Material rigidity: soft_cloth / tight_cling / rigid

OUTPUT JSON ONLY (no fence, no prose):
{{
  "name": "{piece_name}",
  "color_dominant_rgb": [r,g,b],
  "color_secondary_rgb": [r,g,b],
  "bbox_turnaround_front_norm": [x0,y0,x1,y1],
  "shape_keywords": ["tag1","tag2","tag3"],
  "z_world_m": [{z_bot}, {z_top}],
  "wraps_360": true|false,
  "is_paired_LR": true|false,
  "florence2_prompt_refined": "concise english phrase",
  "build_notes": "1 sentence: how piece sits on body"
}}"""


# ============ SOULSLIKE EXPERT CONTEXT (system) ============
SOULSLIKE_EXPERT_SYSTEM = """You are an EXPERT 3D character TA at AAA studio level (Game Science / FromSoftware /
Round8 / NeoWiz). Specialty: Unreal Engine 5.4+ photorealistic gothic/victorian/dark-fantasy
characters using Nanite virtualized geometry, Lumen GI, Chaos Cloth, MetaHuman skin shader.

Reference benchmarks (memorize these visual standards):
- Black Myth Wukong (Game Science, UE5.4): Sun Wukong robes = layered PBR cloth, Surface Deform
  + Chaos Cloth physics, 8k textures, normal+roughness+metallic+SSS skin shader. Robe drape on
  motion = wind+gravity + body collision. Hair = groom + hair cards. 60fps Nanite meshes.
  Install: D:/SteamLibrary/steamapps/common/BlackMythWukong (UE5 paks)
- Elden Ring Ranni: blue silk dress with skirt physics + collision; hair cards anisotropic
- Lies of P Sophia: lace + silk + brass details PBR + cloth pin-anchor cintura
- Bloodborne Lady Maria: layered black gothic outfit, multi-pass material, lace alpha cards
- Lord of the Rings (UE5 demo): metahuman hair groom, cloth wrinkles via tessellation

Quality criteria for SCORE 10 (pixel-perfect, indistinguishable from photo):
- PBR material match: albedo + roughness + metallic + normal + SSS
- Cloth drape: gravity-correct folds + body-deformation natural
- Fabric weight differentiation (silk vs leather vs cotton lace)
- All visible details (lace pattern, stitching, embroidery, button hardware)
- Body fit pixel-correct: no float >2mm, no intersect, no clipping
- Lighting match: HDRI studio if ref is product/mannequin photo
- Shadow falloff + ambient occlusion at body contact
- Hair card alpha + anisotropic specular if applicable
- 360-degree coverage (front/side/back all faithful)

Score discipline (BE RUTHLESS - this is AAA quality control):
- 10: Indistinguishable from reference. Pixel-perfect PBR.
- 9: 1 minor mismatch (lighting tone shift) — NOT ACCEPTABLE for ship
- 8: 1 critical OR 2+ minor mismatches — REJECT
- 5-7: Recognizable shape but multiple gaps
- 0-4: Wrong geometry/material entirely

Score 10 is the ONLY pass. Anything else = continue iterating."""

# ============ VALIDATION (render vs ref) ============
RENDER_VS_REF = """COMPARE: Image 1 = 3D render of piece "{piece_name}". Image 2 = source reference crop.

CRITERIA (score each 0-10, 10=identical):
1. SHAPE: outline silhouette match
2. COLOR: dominant hue + saturation
3. POSITION: piece placement on body region
4. PROPORTION: piece size vs body
5. DETAIL: visible features (babado/lace/stripes/buttons)

OUTPUT JSON ONLY:
{{
  "shape_score": 0-10,
  "color_score": 0-10,
  "position_score": 0-10,
  "proportion_score": 0-10,
  "detail_score": 0-10,
  "overall_score": 0-10,
  "top_3_issues": ["issue1","issue2","issue3"],
  "next_action": "accept|refine_shape|refine_color|refine_position|refine_detail"
}}"""


# ============ TURNAROUND ANALYSIS (full character) ============
TURNAROUND_ANALYSIS = """SUBJECT: Use uploaded turnaround as exact character reference. The character is Alice Liddell, 1.70m tall.

PRESERVE: face structure, body proportions, all garment layers, hair style.

ANALYZE per layer (Inside-Out):
1. Base body anatomy (chest_z, waist_z, hip_z, knee_z, foot_z)
2. Innermost layer (chemise/bloomer)
3. Mid layers (saias, corpete)
4. Outer accessories (chapeu, joias, armas)

OUTPUT STRICT JSON listing each visible piece with: name, z_range, bone_anchor (Mixamo), color_hex, layer_index.
{format_instructions}"""


# ============ STEP IMAGE PARSING (1 of 10 step images) ============
STEP_IMAGE_PARSE = """REFERENCE: This is step image #{step_num} of {total_steps} showing ONE isolated piece floating on dark background.

IDENTIFY exactly:
- name: snake_case_id (no spaces)
- category: TECIDO_BASE | SOBREPOSICAO | COMPRESSAO | METALS_PROPS
- garment_class: skirt|corset|sleeve|stocking|boot|glove|choker|hat|jewelry|weapon|other
- bone_anchor: closest Mixamo bone (mixamorig:Hips/Spine1/LeftLeg/etc)
- z_world_m: [z_bottom, z_top] on 1.70m character
- color_hex: #RRGGBB dominant
- shape_keywords: 3 short tags
- is_paired_LR: true/false
- rigidity: soft_cloth|tight_cling|rigid

OUTPUT JSON ONLY. No prose."""


def piece_extraction_prompt(piece_name, shape_hint, z_bot, z_top):
    return PIECE_EXTRACTION.format(piece_name=piece_name, shape_hint=shape_hint,
                                    z_bot=z_bot, z_top=z_top)

def render_vs_ref_prompt(piece_name):
    return RENDER_VS_REF.format(piece_name=piece_name)

def soulslike_system_prompt():
    return SOULSLIKE_EXPERT_SYSTEM

def step_image_parse_prompt(step_num, total_steps=10):
    return STEP_IMAGE_PARSE.format(step_num=step_num, total_steps=total_steps)
