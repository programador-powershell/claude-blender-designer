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


---

# CATÁLOGO COMPLETO — D:\References (501 arquivos, indexado 2026-06-11)

## /3D — modelos prontos (64 na raiz + texturas)
**Personagens GLB (com vestido/outfit):** alice.glb, alice-vestido.glb, alice-chapepeiro.glb (sic), alice-cheshire.glb, alice-coelho.glb, alice-lagarta.glb, alice-rainha.glb, cavaleiro.glb, cavaleiro-vestido.glb, chapeleiro.glb, cheshire.glb, coelho.glb, coelho-vestido.glb, lagarta.glb, lidia.glb, lidia-vestido.glb, lidia-boss-vestido.glb, rainha.glb, soldado.glb, biscoito-mob.glb
**Skeletal FBX (UE-ready SK_*):** SK_Alice, SK_AliceDress, SK_Alice_Chapeleiro, SK_Alice_Cheshire, SK_Alice_Coelho, SK_Alice_Lagarta, SK_Alice_Rainha, SK_CavaleiroDress, SK_Coelho, SK_Lidia, SK_LidiaBoss, SK_LidiaDress, SK_RainhaDress
**T-Poses FBX:** Alice, Coelho, Lidia, cavaleiro, chapeleiro, coelho-vestido
**Mixamo FBX (rigados):** alice, cavaleiro, chapeleiro, cheshire, coelho, coelho-vestido, lagarta, lidia, rainha (+ .fbm com texturas PBR)
**Armas/Props GLB:** adaga, espadao, faca, foice, cajado, odachi, punhal, bule, carta
**Texturas PBR (base/mr/normal por pasta _tex):** alice, alice_chapeleiro, alice_cheshire, alice_coelho, alice_lagarta, alice_rainha, alice_vestido, cavaleiro, cavaleiro_vestido, chapeleiro, cheshire, coelho, coelho_vestido, lagarta, lidia, lidia_boss, lidia_vestido, rainha (18 sets)
**Fotos base:** alice.jpg, cavaleiro.jpg, chapeleiro.jpg, coelho.jpg, lidia.jpg, rainha.jpg

## /img — arte conceitual (145)
**Model 3D/BASE/** — pacotes de outfit (10 imgs passo-a-passo + turnaround + alice.jpg cada):
- `Alice chapeleiro/` — 10 ChatGPT (11_05_53-56) + alice-chapeleiro.png (turnaround 3-views) + alice.jpg ← BLUEPRINT acima
- `alice base/` — 10 ChatGPT (11_25_16-20) + alice-faca-cozinha.png + alice.jpg
- `alice cheshire/` — 10 ChatGPT (13_36_47-53) + alice-gato.png + alice.jpg
- `alice coelho/` — 10 ChatGPT (13_26_39-46) + alice.jpg
- `alice lagarta/` — 10 ChatGPT (13_44_17-23) + alice-lagarta.png + alice.jpg
- `alice rainha/` — 10 ChatGPT (13_51_24-25) + alice-rainha.png + alice.jpg
- BASE raiz: alice.jpg, cavaleiro.jpg, chapeleiro.jpg, coelho.jpg, lidia.jpg, rainha.jpg
- Model 3D raiz: Alice-3D.png, Lidia-3D.png, Lidia_Boss.png
**Perfil/** (6): alice, arma-inicial, armas, boss-mennores, lidia, lidia-boss
**cenas/** (17): cena1-15,17,18 (sem 5 e 16) + lidia-boss.png
**color/** (8): paleta ChatGPT 25/mai 02_36_46-48
**efeitos/** (4): debuff-skill, obter-skill, rose-drift, transformação-vestido

## /model — rigs e animações de combate (180)
**Rigs:** SK_Alice.fbx, Alice_Tpose.fbx, Alice_for_mixamo.fbx, Eve.fbx (+Eve.fbm SpacePirate tex), Y Bot.fbx, lidia.fbx
**anims/** raiz (14): Eve_Attack/Death/Dodge/Hit/Idle/Run/Walk/Skel, Brutal Assassination, Convulsing, Dual Weapon Combo, Fast Run...
**anims/Great Sword Pack/** (52): draw, attack, blocking, casting, crouching, idle, impact, jump, 180 turn, high spin attack...
**anims/Pro Sword and Shield Pack/** (55)
**anims/Pro Longbow Pack/** (40)
→ Total ~161 animações de combate prontas pra retarget no esqueleto da Alice

## Raiz
- `roteiro.txt` + `roteiro_apenas_historia.txt` — roteiro do jogo (fonte canônica de armas/lore)
- `wolrd-map.jpg` (sic) — mapa-múndi (guia do terreno UE5)
- `logo-gg.png`

## Usos imediatos no pipeline atual
1. **SK_Alice_Chapeleiro.fbx + alice_chapeleiro_tex/** = versão SKELETAL JÁ EXISTENTE do chapeleiro com PBR (base+mr+normal) — comparar/canibalizar texturas no builder three.js
2. Pacotes BASE dos outros 5 outfits = mesmos blueprints prontos pra replicar o builder (cheshire, coelho, lagarta, rainha, base)
3. Anim packs = retarget direto no HRig/GLB (great sword = espadão do roteiro)
4. color/ = paleta oficial pra calibrar tiles
