# Gate Report 5 — TelegramAdapter

**Status:** ✅ Aprovado (automático)
**Data:** 2026-05-01

## Escopo entregue

- **`url_extractor.py`** — extrai a primeira URL do YouTube de um texto, tolerando subdomínios e pontuação trailing; rejeita URLs não-YouTube.
- **`job_queue.py`** — `SequentialJobQueue` genérica com worker único, suporta cancelamento de item atual e pendentes, exposição de `snapshot()` para `/status`.
- **`progress_reporter.py`** — `ProgressReporter` que edita uma única mensagem do Telegram com 5 marcos fixos (10/25/50/75/90%), debounce configurável e diagnósticos limitados.
- **`retry.py`** — `send_with_retry` com backoff exponencial (5 tentativas, 1s→2s→4s→8s) e exceção `TelegramSendError`.
- **`bot_adapter.py`** — `TelegramBotAdapter` integra todas as peças: autorização silenciosa, handlers de `/start`, `/help`, `/status`, `/cancel` e mensagens com link, criação do `Job` de domínio, integração thread-safe com o use case síncrono via `run_in_executor` + `cancel_event` compartilhado, envio de áudio + Markdown final.
- **Modificação do use case** — `TranscribeVideoUseCase.execute()` agora aceita `cancel_event: threading.Event | None`, permitindo ao adapter sinalizar cancelamento ao runner do pipeline sem acoplar bibliotecas async ao domínio.

## Decisões consolidadas neste gate

- **Comandos para Gate 6** — `/list`, `/last`, `/redo`, `/rename`, `/clearcache` foram intencionalmente postergados para o Gate 6, pois dependem da retenção FIFO e dos diálogos interativos. O `/cancel` está aqui pois é apenas dispatcher de evento.
- **Thread bridge** — o use case é síncrono (segue API do pipeline), o adapter é assíncrono (segue API do python-telegram-bot). A ponte é feita via `loop.run_in_executor()` para o use case e `asyncio.run_coroutine_threadsafe()` para os callbacks de progresso voltarem ao loop.
- **Autorização silenciosa** — todos os 5 handlers verificam `_is_authorized()` antes de qualquer ação. Para usuários não autorizados, retornam imediatamente, sem qualquer envio (Dúvidas 3 e 30).

## Métricas

| Métrica | Valor | Limiar | Status |
|---|---|---|---|
| Testes totais | 406 | n/a | ✅ |
| Testes deste gate | 51 | ≥ 40 | ✅ |
| Cobertura global | 93% | ≥ 90% | ✅ |
| Cobertura `bot_adapter.py` | 91% | ≥ 90% | ✅ |
| Cobertura `job_queue.py` | 100% | ≥ 90% | ✅ |
| Cobertura `progress_reporter.py` | 100% | ≥ 90% | ✅ |
| Cobertura `url_extractor.py` | 100% | ≥ 90% | ✅ |
| Cobertura `retry.py` | 100% | ≥ 90% | ✅ |
| ruff check | 0 | 0 | ✅ |
| ruff format | OK | OK | ✅ |
| mypy --strict | 0 | 0 | ✅ |

## Suítes adicionadas

- `tests/unit/infrastructure/telegram/test_url_extractor.py` (16 testes)
- `tests/unit/infrastructure/telegram/test_job_queue.py` (7 testes)
- `tests/unit/infrastructure/telegram/test_progress_reporter.py` (9 testes — incluindo regressão G5.1)
- `tests/unit/infrastructure/telegram/test_retry.py` (5 testes)
- `tests/unit/infrastructure/telegram/test_bot_adapter.py` (13 testes — incluindo failures, retry, cancelamento, lifecycle)

## Bugs encontrados e corrigidos (gerando testes de regressão)

| # | Bug | Teste de regressão |
|---|---|---|
| G5.1 | `transcription_progress` só avançava 1 marco por chamada; ao receber 0.95 só emitia 50%. | `test_progress_jumps_emit_all_crossed_milestones` |
| G5.2 | URL extractor capturava `youtube.com` dentro de querystring de outra URL (`google.com/search?q=youtube.com`). | `test_unrelated_urls_are_ignored[google.com/search?q=youtube.com]` |
| G5.3 | BotAdapter usava nome `VideoIdError` inexistente (na verdade é `InvalidYouTubeUrlError`). | Cobertura indireta por `test_invalid_youtube_url`. |

## Próximo gate

Gate 6 — Retenção FIFO de 5 arquivos por pasta com expurgo coordenado, diálogo interativo de `/rename`, comandos `/list`, `/last`, `/redo` (com confirmação de mudança de config), `/clearcache`. Persistência de turnos crus em JSON ao lado do MD para suportar renomeação em vídeos legados.
