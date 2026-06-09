# Pipeline de fidelidade do vestido (Gemma = olho, Claude = ponte)

Loop ao vivo no Blender: Gemma 4 12B (vision via llama.cpp) compara ARTE × RENDER e
devolve desvios por célula de grid; Claude executa via bridge + snapshot cada passo.
Usuário vê tudo no viewport (ela inteira + arte ao lado). Nada em background.

## Componentes (D:\Alice\tools\auto-rig-fix\)
- `claude_bridge.py`  — roda no Blender (Text Editor > Run). Socket porta 9877.
- `bridge_cmd.py`     — cliente: `python bridge_cmd.py "<code>"` | `--file f.py` | `--gb fn` | `--shot`.
- `live/vision_ask.py`   — Gemma/llama (default) ou qwen/ollama. `ask()` / `ask_multi([imgs], prompt)`. thinking OFF, downscale 640.
- `live/trace_overlay.py`— "desenhar por cima": `make_overlay(ref, render, out, grid=12)`. Registra por silhueta; ARTE=vermelho, MODELO=verde, bate=amarelo, grid rotulado. Retorna % cobertura.
- `live/gemma_loop.py`   — orquestrador. `python gemma_loop.py <regiao> <vista>`.
- `live/load_refs.py`    — empties IMAGE REF_front/side/back ao lado do modelo.
- `live/game_builder.py` — snapshot(label) / rollback(idx) / etc.

## Servidor Gemma (o olho)
`D:\llama.cpp\serve_gemma.cmd`  (b9515 CUDA12.4, Q4_K_M + mmproj, -ngl 28, -fa on, --cache-ram 0).
Endpoint OpenAI: http://127.0.0.1:8080. ⚠️ --cache-ram 0 evita crash por crescimento de memória.

## Fluxo
1. `load_refs.py` uma vez → arte front/side/back no Blender.
2. Por vista (front/side/back) e região (skirt/torso/head/hat/hands/motifs/full):
   `python gemma_loop.py <regiao> <vista>`
   - viewport = ELA INTEIRA + arte ao lado (set_compare_view, MATERIAL) — usuário compara ao vivo.
   - render da parte OFFSCREEN por câmera ortho 'LoopCam' (não mexe no viewport).
   - recorta região da arte → trace_overlay → Gemma JSON {fidelity, deviations:[{cell,problem,fix}]}.
   - snapshot automático.
3. Repete loop corrigindo até ~100% de fidelidade. Aprova/rollback pelo usuário.

## Regiões (view_location, distance, ref_crop) e VIEWQ (quats front/side/back) em gemma_loop.py.

## Lições (o que dá certo / não)
- Gemma assertivo p/ LISTAR falhas; NÃO juiz de aprovar/reprovar (olho humano = régua).
- NÃO achatar normal map (reprovado) nem adicionar babado procedural (reprovado 3×).
- Manter asset original detalhado (964k). Geometria só por deform reversível ou re-gen.
