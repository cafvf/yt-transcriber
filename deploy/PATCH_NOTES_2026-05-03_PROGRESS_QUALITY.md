# Patch notes — 2026-05-03 — progresso fixo e qualidade de legenda automática

## Objetivo

Melhorar a experiência durante etapas longas e evitar que legendas automáticas ruins do YouTube substituam uma transcrição WhisperX de melhor qualidade.

## Mudanças principais

### 1. Progresso fixo para etapas longas

O bot agora usa marcos fixos de progresso em etapas sem percentual confiável:

- 10%
- 25%
- 50%
- 75%
- 90%

Esses valores não pretendem representar progresso matemático real. Eles indicam marcos internos da etapa para deixar claro que o pipeline continua ativo.

A lógica foi aplicada a:

- transcrição WhisperX;
- alinhamento de timestamps;
- diarização WhisperX/pyannote;
- associação dos falantes aos segmentos transcritos.

### 2. Progresso de diarização

A porta de diarização agora aceita callback opcional de progresso, no mesmo estilo da transcrição.

Foram atualizados:

- `DiarizationEngine`;
- `CompositeDiarizationEngine`;
- `WhisperXDiarizationEngine`;
- `PyannoteDiarizationEngine`;
- backends reais WhisperX e pyannote;
- fakes de teste.

### 3. Gate de qualidade para legenda automática

Legendas manuais do YouTube continuam sendo aceitas preferencialmente.

Legendas automáticas passam por avaliação heurística antes de serem usadas. O bot rejeita legenda automática quando há evidência forte de:

- repetição interna excessiva;
- sobreposição excessiva entre cues consecutivos;
- ausência de texto útil.

Quando a legenda automática é rejeitada, o pipeline segue normalmente:

1. baixa o áudio;
2. converte para OGG/Opus;
3. transcreve com WhisperX;
4. diariza;
5. gera Markdown.

### 4. Melhorias de mensagens de progresso

Os nomes de steps enviados ao Telegram agora são mapeados corretamente para mensagens humanas, por exemplo:

- `fetch_metadata` → `📋 Lendo metadados`
- `try_youtube_subtitles` → `📑 Avaliando legendas do YouTube`
- `transcribe` → `🎙️ Transcrevendo`
- `diarize` → `👥 Identificando falantes`

## Validação feita neste ambiente

```bash
python -m compileall -q src tests
```

Também foi executado teste unitário direcionado da diarização:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src pytest -q tests/unit/infrastructure/diarization/test_diarization_engines.py
```

Resultado:

```text
22 passed
```

A suíte completa não foi executada neste sandbox por ausência de dependências como `python-slugify`. No ambiente local do projeto, validar com:

```bash
uv run pytest
```
