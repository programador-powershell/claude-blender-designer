# Project Alice — Garment Builder por Camadas

Hunyuan3D, TripoSR e Unique3D são úteis para gerar uma malha aproximada, mas roupa complexa não deve nascer como um mesh único.

Para a roupa da Alice, o correto é separar:

```text
01 base torso blouse
02 corset fitted panel
03 inner skirt
04 outer skirt
05 overskirt side panels
06 front apron panel
07 puff sleeves
08 lace/ruffles
09 belts/straps
10 gloves
11 boots
12 chains
13 cards
14 clock/watch
15 roses/brooches
16 hat/accessories
```

Cada peça vira geometria própria no Blender, com material, espessura, anchors e física.

## Ordem de construção

```text
1. corpo alvo e armature
2. peças justas: blouse/corset
3. saias internas
4. saias externas
5. painéis soltos
6. mangas
7. babados/rendas
8. cintos e tiras
9. acessórios rígidos
10. vertex groups de pin
11. modifiers cloth/solidify/subdivision
12. armature modifiers
13. validação com render front/side/back
```

## Como evoluir para fidelidade alta

1. Gerar/usar imagens ortográficas de frente/lado/costas.
2. Traçar manualmente silhuetas de cada camada em SVG/JSON.
3. Alimentar `garment_builder.py` com pontos reais do molde.
4. Rodar validação de render.
5. Ajustar blueprint, não mexer no mesh manualmente.
