# Project Alice — Hair Pipeline baseado em GodotHair

Este patch adiciona ao `claude-blender-designer` um módulo de cabelo por **hair cards**, inspirado na arquitetura do projeto `2Retr0/GodotHair`.

## O que foi aproveitado como conceito

O GodotHair explica duas abordagens principais:

- **strand-based hair**: muitos fios individuais como curvas, mais fiel, mas caro para tempo real;
- **hair cards**: quad/cards planos representando tufos de cabelo, com texturas e camadas para simular volume.

Para o Project Alice, o patch usa **hair cards procedurais no Blender**, porque é mais viável para personagem de jogo e mais fácil de rigar que milhões de fios.

## O que este patch NÃO faz

Este patch **não copia assets, meshes ou shaders do GodotHair**.

O README do GodotHair informa que os modelos em `/assets/hair/models` não devem ser considerados production-ready e são CC BY-NC 4.0. Por isso, este pacote usa apenas a ideia técnica:

```text
cabelo = grupos de hair cards + shader anisotrópico + root/tip UV + física secundária
```

## Arquivos adicionados

```text
live/hair_schema.py
live/hair_card_builder.py
live/hair_alice_liddell.py
live/vision_to_hair_blueprint.py
pipeline_hair_builder.py
examples/alice_liddell_hair_blueprint.json
docs/HAIR_PIPELINE_GODOTHAIR_BASE.md
```

## Como gerar blueprint da Alice

```bash
python pipeline_hair_builder.py --preset alice --save examples/alice_liddell_hair_blueprint.json
```

## Como construir no Blender

Com o bridge do projeto ativo dentro do Blender:

```bash
python pipeline_hair_builder.py --blueprint examples/alice_liddell_hair_blueprint.json --build --shot
```

## Como o cabelo é dividido

```text
01 scalp_cap
02 bangs_center_part
03 side_locks
04 back_volume
05 flyaways
06 secondary_motion_tags
```

## Como usar com LLM Vision

A LLM Vision deve gerar JSON técnico, não descrição solta.

Ela deve analisar a imagem da cabeça/cabelo e classificar:

```text
- franja;
- mechas laterais;
- volume traseiro;
- fios soltos;
- acessórios;
- região que não pode cobrir rosto;
- comprimento;
- direção dos cachos;
- densidade.
```

O resultado deve ser compatível com `hair_schema.py`.

## Próximo passo recomendado

Depois de gerar os cards, o ideal é adicionar:

```text
- textura alpha/coverage para fios;
- textura de tangent root→tip;
- pesos para ossos secundários;
- colisão cabeça/pescoço/ombro;
- LODs: perto, médio, longe;
- export GLB/FBX com materiais.
```
