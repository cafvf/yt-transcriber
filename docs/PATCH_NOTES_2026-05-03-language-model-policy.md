# Patch 2026-05-03 — Política de modelo Whisper por idioma

## Objetivo

Melhorar a qualidade de transcrição em português sem penalizar excessivamente vídeos em inglês.

## Mudanças

- `WHISPER_MODEL` agora aceita `auto` e passa a usar este valor como padrão.
- Em `WHISPER_MODEL=auto`, o bot escolhe o modelo pelo idioma original do vídeo:
  - português (`pt`) → `large-v3`;
  - inglês (`en`) → `medium`;
  - idioma desconhecido/outro → `medium`.
- Novas variáveis de configuração:
  - `WHISPER_MODEL_PT`;
  - `WHISPER_MODEL_EN`;
  - `WHISPER_MODEL_DEFAULT`.
- `WHISPER_MODEL` explícito continua tendo prioridade sobre a política automática.
- A assinatura de transcrição agora inclui os modelos por idioma, evitando reuso indevido de cache quando a política muda.

## Exemplo recomendado

```env
WHISPER_MODEL=auto
WHISPER_MODEL_PT=large-v3
WHISPER_MODEL_EN=medium
WHISPER_MODEL_DEFAULT=medium
```

## Observação

Se a GPU não tiver VRAM suficiente, a política existente de runtime ainda pode reduzir o modelo em CUDA ou cair para CPU. Em CPU, `large-v3` pode ser lento.
