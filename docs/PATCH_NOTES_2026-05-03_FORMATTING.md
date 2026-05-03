# Patch notes — 2026-05-03 — formatação e legendas automáticas

## Correções

- Adicionado pós-processamento conservador para legendas automáticas do YouTube em VTT.
- Removida sobreposição típica de legendas automáticas em modo “janela rolante”.
- Colapsadas repetições adjacentes dentro de um mesmo cue de legenda.
- Renderização Markdown agora divide turnos longos de um mesmo falante em blocos menores.
- Texto renderizado agora é paragraphizado por fim de frase, evitando blocos monolíticos de vários minutos.

## Motivação

O arquivo gerado anteriormente usava legendas automáticas do YouTube e apresentou frases repetidas duas ou três vezes. Isso ocorre quando cues consecutivos de VTT automático repetem parte do texto anterior. Além disso, quando a diarização identifica apenas um falante, o renderer antigo agregava todos os segmentos do mesmo falante em poucos blocos muito longos.

## Validação local no sandbox

```bash
python -m compileall -q src tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src pytest -q \
  tests/unit/infrastructure/youtube/test_yt_dlp_downloader.py \
  tests/unit/infrastructure/rendering/test_markdown_renderer.py
```

Resultado:

```text
64 passed, 1 warning
```
