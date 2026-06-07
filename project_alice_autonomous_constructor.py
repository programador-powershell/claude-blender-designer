#!/usr/bin/env python3
"""
Project Alice - Autonomous Layer-by-Layer Constructor v2.0
Data-driven, high-fidelity, step-by-step clothing builder for AAA quality.

Usage:
    python project_alice_autonomous_constructor.py

When you send reference images of a specific clothing layer (corset exploded view, skirt tiers, etc.):
1. Analyze the image with Qwen3 VL or Claude Vision to identify which piece it corresponds to.
2. The constructor will build ONLY that layer with perfect technical setup.
3. It will pause and give you precise sculpting instructions to match the reference 100%.
"""

import bpy
import json
import os
import sys
from pathlib import Path

class ProjectAliceAutonomousConstructor:
    def __init__(self, spec_path="specs/chapeleiro_dress_spec.json"):
        self.spec_path = spec_path
        self.spec = self._load_spec()
        self.state_file = "work/constructor_state.json"
        self.current_index = self._load_state()

    def _load_spec(self):
        with open(self.spec_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                return state.get("current_index", 0)
        return 0

    def _save_state(self):
        os.makedirs("work", exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump({"current_index": self.current_index}, f)

    def build_next_layer(self, force_piece_id=None):
        """Builds the next layer in order, or a specific piece if force_piece_id is given."""
        
        if force_piece_id:
            piece_id = force_piece_id
            print(f"[AUTONOMOUS] Forçando construção da peça específica: {piece_id}")
        else:
            if self.current_index >= len(self.spec["layer_order"]):
                print("[AUTONOMOUS] ✅ Todas as camadas do Vestido do Chapeleiro foram construídas com sucesso!")
                print("Próximo passo: Rig + Weight Paint + Export para Unreal 5.7")
                return

            piece_id = self.spec["layer_order"][self.current_index]
            print(f"\n[AUTONOMOUS] === Camada {self.current_index + 1} / {len(self.spec['layer_order'])} ===")

        if piece_id not in self.spec["pieces"]:
            print(f"[ERRO] Peça '{piece_id}' não encontrada no spec JSON.")
            return

        piece = self.spec["pieces"][piece_id]
        print(f"Construindo: {piece['display_name']}")

        # 1. Create or get the object
        obj = self._ensure_object_exists(piece)

        # 2. Apply all technical setup from JSON (this is the autonomous magic)
        self._apply_full_technical_setup(obj, piece)

        # 3. Print clear instructions for high-fidelity sculpting based on the image you sent
        self._print_high_fidelity_instructions(piece)

        # 4. Advance state only if not forced
        if not force_piece_id:
            self.current_index += 1
            self._save_state()

        print(f"\n[AUTONOMOUS] Camada '{piece_id}' configurada com sucesso.")
        print("→ Esculpa agora seguindo as instruções acima + sua imagem de referência.")
        print("→ Quando terminar, rode o script novamente para avançar.")

    def _ensure_object_exists(self, piece):
        obj_name = f"PA_{piece['piece_id']}"
        col_name = piece["collection"]

        if obj_name in bpy.data.objects:
            obj = bpy.data.objects[obj_name]
            print(f"  -> Objeto já existe: {obj_name}")
        else:
            # Create high-quality base mesh according to shape_type
            if piece.get("shape_type") == "hero_female_base":
                bpy.ops.mesh.primitive_cylinder_add(
                    radius=0.18, depth=1.05, location=(0, 0, 0.95), vertices=64
                )
            elif piece.get("shape_type") in ["corset_panel", "skirt_base", "overskirt_panel"]:
                bpy.ops.mesh.primitive_cylinder_add(
                    radius=0.28, depth=0.55, location=(0, 0, 1.15), vertices=48
                )
            else:
                bpy.ops.mesh.primitive_cube_add(size=0.4, location=(0, 0, 1.2))

            obj = bpy.context.active_object
            obj.name = obj_name
            obj.data.name = obj_name

            # Move to correct collection
            for c in obj.users_collection:
                c.objects.unlink(obj)
            if col_name in bpy.data.collections:
                bpy.data.collections[col_name].objects.link(obj)
            else:
                print(f"  [AVISO] Coleção {col_name} não encontrada. Crie primeiro com o setup do skill.md")

            print(f"  -> Objeto base de alta qualidade criado: {obj_name}")

        return obj

    def _apply_full_technical_setup(self, obj, piece):
        """Applies everything from the JSON spec automatically."""
        
        # Custom Properties (mandatory for Project Alice pipeline)
        obj["piece_id"] = piece["piece_id"]
        obj["layer_index"] = piece["layer_index"]
        obj["category"] = piece["category"]
        obj["deformation_type"] = piece["deformation_type"]
        obj["material_family"] = piece.get("material", "default")
        obj["export_group"] = piece.get("export_group", "hero")

        # Modifiers from spec
        for mod_name, params in piece.get("modifiers", {}).items():
            if mod_name == "Shrinkwrap":
                if not obj.modifiers.get("Shrinkwrap"):
                    mod = obj.modifiers.new("Shrinkwrap", 'SHRINKWRAP')
                    target_name = params.get("target", "PA_Body_Base")
                    if target_name in bpy.data.objects:
                        mod.target = bpy.data.objects[target_name]
                    mod.offset = params.get("offset", 0.0025)
            elif mod_name == "Solidify":
                if not obj.modifiers.get("Solidify"):
                    mod = obj.modifiers.new("Solidify", 'SOLIDIFY')
                    mod.thickness = params.get("thickness", 0.003)
                    mod.offset = params.get("offset", 0.0)

        # Vertex Groups (especially important for cloth pinning)
        for vg_name in piece.get("pin_groups", []):
            if vg_name not in obj.vertex_groups:
                obj.vertex_groups.new(name=vg_name)
                print(f"  -> Vertex Group criado: {vg_name}")

        # Cloth physics settings (for pieces marked as cloth)
        if piece["category"] == "cloth" and piece.get("cloth_settings"):
            # Note: Full cloth setup usually needs to be done in Object Mode after sculpting
            print(f"  -> Configurações de Cloth preparadas no JSON (aplique manualmente após sculpt)")

        print(f"  -> Setup técnico completo aplicado em {obj.name}")

    def _print_high_fidelity_instructions(self, piece):
        """Gives precise instructions so the result is 100% faithful to the reference image."""
        print("\n" + "="*70)
        print("INSTRUÇÕES DE ESCULPIMENTO DE ALTA FIDELIDADE")
        print("="*70)
        print(f"Peça: {piece['display_name']}")
        print(f"Descrição técnica: {piece.get('shape_description', 'Siga a imagem')}")
        print("\nAÇÃO OBRIGATÓRIA:")
        print("1. Use a imagem de referência que você enviou (exploded view ou vista da peça).")
        print("2. Esculpa esta peça para ficar o mais próximo possível da imagem.")
        print("3. Preste atenção especial em:")
        if "corset" in piece["piece_id"]:
            print("   - Costuras verticais e formato cônico")
            print("   - Peplum inferior")
            print("   - Furos para lacing nas laterais")
        elif "skirt" in piece["piece_id"] or "overskirt" in piece["piece_id"]:
            print("   - Volume e forma da saia")
            print("   - Número de tiers / babados")
            print("   - Posição exata de estampas de cartas e laços")
        elif "back_bow" in piece["piece_id"]:
            print("   - Tamanho e forma do laço grande")
            print("   - Relógio no centro do laço")
        print("\nDepois de terminar o sculpt, rode o script novamente.")
        print("="*70 + "\n")

    def build_specific_layer_from_image(self, image_path, suggested_piece_id=None):
        """
        Use this when the user sends a new reference image.
        The user (or Qwen/Claude) should tell which piece it corresponds to.
        """
        print(f"\n[IMAGE MODE] Imagem recebida: {image_path}")
        print("Por favor, confirme ou escolha a peça correspondente no JSON.")
        if suggested_piece_id:
            print(f"Sugestão: {suggested_piece_id}")
            self.build_next_layer(force_piece_id=suggested_piece_id)
        else:
            print("Exemplos de piece_id válidos: corset_front, inner_skirt, back_bow, etc.")
            print("Depois rode: python project_alice_autonomous_constructor.py --piece corset_front")


if __name__ == "__main__":
    constructor = ProjectAliceAutonomousConstructor()
    
    # Check for command line arguments for specific piece
    if len(sys.argv) > 1 and sys.argv[1] == "--piece" and len(sys.argv) > 2:
        constructor.build_next_layer(force_piece_id=sys.argv[2])
    else:
        constructor.build_next_layer()
