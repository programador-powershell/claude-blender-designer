# claude-blender-designer — Garment Builder Update

Atualização para transformar o projeto em um pipeline de roupa procedural por camadas para Blender.

O objetivo desta atualização é complementar o pipeline atual `Image -> 3D -> Blender rigged character` com um segundo pipeline específico para roupa:

```text
Character Pipeline
imagem base -> corpo/cabeça/cabelo -> rig -> shape keys

Garment Pipeline
blueprint do vestido -> peças separadas -> tecidos -> costuras -> cloth -> acessórios -> validação
```

## O que foi adicionado

```text
live/garment_schema.py              Schema técnico de peças/camadas/acessórios
live/garment_builder.py             Construtor Blender procedural das roupas
live/garment_alice_dark_dress.py    Blueprint do vestido da Alice por camadas
live/vision_to_garment_blueprint.py Conversor VLM -> blueprint técnico de roupa
live/garment_fit_to_body.py         Ajuste de roupa ao corpo/armature
live/garment_validation_render.py   Câmeras e validação por renders
pipeline_garment_builder.py         Pipeline via bridge_cmd.py
examples/alice_dark_dress_blueprint.json
```

## Como usar

1. Copie estas pastas para a raiz do seu repositório original `claude-blender-designer`.
2. Abra o Blender com `claude_bridge.py` rodando.
3. Execute:

```bash
python pipeline_garment_builder.py --blueprint examples/alice_dark_dress_blueprint.json --character Alice_Base --outfit Alice_Dark_Dress --validate-render
```

## Importante

Esta atualização não promete reconstrução perfeita a partir de uma imagem única. Ela muda o projeto para o caminho correto: roupa como **molde/camada/peça/acessório**, com geometria separada, materiais e simulação. Para ficar perfeitamente fiel, cada peça precisa ser refinada por blueprint/manual tracing.


---

# Atualização Hair Cards — GodotHair como base conceitual

Este pacote agora inclui um pipeline de cabelo em `hair cards` inspirado no projeto `2Retr0/GodotHair`.

Arquivos principais:

```text
live/hair_schema.py
live/hair_card_builder.py
live/hair_alice_liddell.py
live/vision_to_hair_blueprint.py
pipeline_hair_builder.py
examples/alice_liddell_hair_blueprint.json
docs/HAIR_PIPELINE_GODOTHAIR_BASE.md
```

Uso:

```bash
python pipeline_hair_builder.py --preset alice --save examples/alice_liddell_hair_blueprint.json
python pipeline_hair_builder.py --blueprint examples/alice_liddell_hair_blueprint.json --build --shot
```

Observação: o patch **não copia assets do GodotHair**. Ele usa a arquitetura de cabelo por hair cards como referência técnica, com material anisotrópico aproximado no Blender e blueprint procedural para o cabelo da Alice.
