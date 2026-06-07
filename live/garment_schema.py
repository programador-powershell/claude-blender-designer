# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
import json

@dataclass
class MaterialSpec:
    id: str
    color: Tuple[float, float, float, float] = (0.05, 0.06, 0.09, 1.0)
    roughness: float = 0.65
    metallic: float = 0.0
    alpha: float = 1.0

@dataclass
class GarmentPiece:
    id: str
    category: str
    layer: int
    material: str
    shape: str
    anchors: List[str] = field(default_factory=list)
    physics: str = "none"
    thickness: float = 0.006
    z_offset: float = 0.0
    params: Dict[str, Any] = field(default_factory=dict)
    details: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class AccessoryPiece:
    id: str
    category: str
    layer: int
    material: str
    shape: str
    parent_piece: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OutfitBlueprint:
    outfit_id: str
    display_name: str
    version: str = "1.0"
    scale: str = "1 BU = 1 meter"
    target_character: str = "Alice_Base"
    materials: List[MaterialSpec] = field(default_factory=list)
    pieces: List[GarmentPiece] = field(default_factory=list)
    accessories: List[AccessoryPiece] = field(default_factory=list)
    build_order: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, **kwargs) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, **kwargs)

def load_blueprint(path: str) -> OutfitBlueprint:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return OutfitBlueprint(
        outfit_id=data['outfit_id'],
        display_name=data.get('display_name', data['outfit_id']),
        version=data.get('version', '1.0'),
        scale=data.get('scale', '1 BU = 1 meter'),
        target_character=data.get('target_character', 'Alice_Base'),
        materials=[MaterialSpec(**x) for x in data.get('materials', [])],
        pieces=[GarmentPiece(**x) for x in data.get('pieces', [])],
        accessories=[AccessoryPiece(**x) for x in data.get('accessories', [])],
        build_order=data.get('build_order', []),
        notes=data.get('notes', []),
    )

def validate_blueprint(bp: OutfitBlueprint) -> Dict[str, Any]:
    errors = []
    mids = {m.id for m in bp.materials}
    pids = {p.id for p in bp.pieces}
    for p in bp.pieces:
        if p.material not in mids:
            errors.append(f"piece {p.id}: material '{p.material}' not found")
        if p.layer < 0:
            errors.append(f"piece {p.id}: negative layer")
    for a in bp.accessories:
        if a.material not in mids:
            errors.append(f"accessory {a.id}: material '{a.material}' not found")
        if a.parent_piece and a.parent_piece not in pids:
            errors.append(f"accessory {a.id}: parent_piece '{a.parent_piece}' not found")
    return {"ok": not errors, "errors": errors, "pieces": len(bp.pieces), "accessories": len(bp.accessories)}
