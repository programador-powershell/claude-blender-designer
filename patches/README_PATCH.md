# Patch de fidelidade para roupa da Alice

Este patch adiciona um pipeline separado para roupas complexas, complementando o pipeline atual de personagem.

## Próximo passo para perfeição

Gerar um JSON de molde real a partir de imagens front/side/back:

```bash
python live/vision_to_garment_blueprint.py front.png side.png back.png out_garment_trace.json
```

Depois converter esse trace em medidas reais dentro do `examples/alice_dark_dress_blueprint.json`.
