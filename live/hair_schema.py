"""
Project Alice — Hair Card Schema

Schema técnico para cabelo baseado no conceito do GodotHair:
- cabelo em hair cards, não fios individuais;
- cada card representa um tufo;
- cada tufo tem raíz, direção, largura, comprimento, curvatura, camadas e física;
- shaders usam parâmetros inspirados em albedo, roughness longitudinal/azimutal,
  specular e cuticle tilt.

Este módulo não copia assets do GodotHair. Ele cria blueprints e geometrias
procedurais em Blender para o pipeline Project Alice.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Tuple
import json

Vec3 = Tuple[float, float, float]


@dataclass
class HairShader:
    name: str = "PA_Hair_Black_Anisotropic"
    albedo: Tuple[float, float, float] = (0.015, 0.012, 0.011)
    root_tint: Tuple[float, float, float] = (0.005, 0.004, 0.004)
    tip_tint: Tuple[float, float, float] = (0.045, 0.038, 0.036)
    longitudinal_roughness: float = 0.32
    azimuthal_roughness: float = 0.78
    specular: float = 0.65
    cuticle_tilt_offset: float = 0.10
    alpha_hash: bool = True
    use_anisotropic: bool = True
    random_seed_variation: float = 0.18


@dataclass
class HairCard:
    id: str
    group: str
    root: Vec3
    tip: Vec3
    width_root_m: float
    width_tip_m: float
    segments: int = 8
    curve_strength: float = 0.12
    curl_turns: float = 0.0
    curl_radius_m: float = 0.0
    normal_bias: Vec3 = (0.0, -1.0, 0.0)
    layer: int = 0
    mirror: bool = False
    physics: str = "secondary_bone"
    collision_radius_m: float = 0.04
    material: str = "PA_Hair_Black_Anisotropic"
    opacity: float = 1.0


@dataclass
class HairGroup:
    id: str
    label: str
    anchor_bone: str
    cards: List[HairCard] = field(default_factory=list)
    mirror_x: bool = False
    priority: int = 0
    notes: str = ""


@dataclass
class HairBlueprint:
    character: str
    style_name: str
    scale: str = "1 Blender unit = 1 meter"
    source_reference: Dict[str, str] = field(default_factory=dict)
    shader: HairShader = field(default_factory=HairShader)
    groups: List[HairGroup] = field(default_factory=list)
    validation: Dict[str, Any] = field(default_factory=lambda: {
        "must_not_intersect_face": True,
        "must_cover_scalp_from_front": True,
        "must_have_back_volume": True,
        "must_keep_neck_clear_for_rig": True,
        "target_card_count_min": 120,
        "target_card_count_max": 900
    })

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)


def load_hair_blueprint(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
