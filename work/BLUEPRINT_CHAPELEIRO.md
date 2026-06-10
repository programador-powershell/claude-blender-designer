# BLUEPRINT DEFINITIVO — Alice Chapeleiro (lido das 10 imagens da pasta, 2026-06-10)

## Ordem de vestir (img 10 exploded view) — ETAPAS GATED
1. Corpo nu = alice.jpg / alice_rigged (validar ANTES de vestir)
2. Meias listradas preto+bege coxa-alta, listras ~3cm iguais (img 8)
3. Botas pretas cano-joelho: cadarço frontal ilhoses completo, plataforma, salto grosso, strap+fivela topo e tornozelo (img 8)
4. Bloomers cream curtos c/ babado (img 1)
5. Chemise/camisa branca + corset cream c/ busk frontal, boning channels, lacing X costas (img 1)
6. Anágua PRETA renda 5 TIERS franzidos, hem handkerchief, scallops (img 5 — 8 padrões de renda individuais)
7. Saia interna cream: ruching lateral (cordões verticais), barra renda, midi (img 1)
8. Saia média cream bordada: APRON frontal pontudo (V invertido) c/ colunas de ornamentos dourados, barra renda dourada, sub-camada handkerchief, CARTAS patches (5: copas/ouros/paus/rasgada/xícara) (img 3)
9. Sobressaia verde damask: assimétrica handkerchief, ABERTA na frente, tiers franzidos, painéis cascata laterais, 4 straps fivela (img 4)
10. Corpete verde: painéis c/ boning channels, decote quadrado-coração c/ trim renda DOURADA, broche cruz central, lacing dourado frontal, PEPLUM EM ABAS recortadas c/ trim, costas lacing (img 2)
11. Mangas puff c/ renda DUPLA na borda (dourada + babado) (img 2)
12. Luvas RENDA preta fingerless longas: babado borda, CAMAFEU no dorso, straps (img 8)
13. Bow traseiro GIGANTE verde c/ RELÓGIO no nó, caudas longas (img 6)
14. Chatelaine: corrente c/ chave+relógio+coração; relógio de bolso números romanos + chave (img 3/6/9)
15. Choker preto renda c/ camafeu + colares/brincos/hairpins (img 7)
16. Cabelo: preto MUITO cacheado volumoso longo, TRANÇA fina coroa c/ ornamento central (img 7)
17. Top hat verde damask: relógio+chave na banda frente, engrenagens lateral, BOW traseiro (img 7)

## Swatches de tecido (img 9 — recortar como TEXTURAS)
S1 verde damask micro-diamantes | S2 cream rosas chintz | S3 verde liso acetinado
S4 preto rosas vermelhas | S5 preto textura | S6 renda dourada densa
S7 preto cruzes/lis douradas | S8 VERDE LOSANGOS GRADE (principal!) | S9 bordô rosas
S10 cinza-verde adamascado | S11 listras douradas/verde | S12 preto micro-poás
+ 24 botões, 10 cartas (5 vintage brancas, 4 escuras emolduradas), 3 tiras renda preta prontas

## Gates de validação por etapa
- Corpo: render nu vs alice.jpg (SSIM + WholeBody + olho)
- Esqueleto: cada osso vs antropometria Drillis-Contini (% altura) + dentro da mesh
- Cada peça: render região vs crop da imagem da peça (cv2 edge ratio + olho) — NÃO avançar sem bater
- Final: 3-views vs turnaround + WholeBody 133/133 + cv2 14 faixas
