# Patch 2026-05-03 — Roadmap para backend Transformers

## Objetivo

Registrar como funcionalidade futura a expansão do pipeline de ASR para suportar um backend Hugging Face Transformers/PyTorch, complementar ao fluxo atual WhisperX/faster-whisper.

## Mudanças documentais

- Adicionada a seção `F.5 Backend Transformers para ASR em português` em `docs/06-funcionalidades-futuras.md`.
- O item documenta o uso futuro de modelos como `freds0/distil-whisper-large-v3-ptbr` via Transformers.
- O modelo `inesc-id/WhisperLv3-X-PT-All` permanece como primeiro candidato a teste no fluxo atual com WhisperX.
- A arquitetura futura sugerida é um roteador de ASR por idioma/backend/modelo, com qualidade estimada e fallback controlado.

## Status

Documentação apenas. Nenhuma mudança de runtime foi feita neste patch.
