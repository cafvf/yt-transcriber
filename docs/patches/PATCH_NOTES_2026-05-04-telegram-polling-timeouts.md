# Patch notes — 2026-05-04 — Timeouts explícitos para polling do Telegram

## Contexto

Após a geração bem-sucedida de um resumo em Markdown, o bot passou a registrar falhas de polling do Telegram com `httpx.ReadError` e `httpx.ConnectError: All connection attempts failed`. O log indica falha de conectividade com a Bot API durante `getUpdates`, não falha da LLM nem do arquivo de sumário.

## Alterações

- Adicionados timeouts configuráveis para chamadas normais da Bot API.
- Adicionados timeouts configuráveis específicos para `getUpdates`/long polling.
- O entrypoint passa a construir a aplicação PTB com timeouts explícitos via `Application.builder()`.
- `start_polling()` agora recebe `poll_interval`, `timeout`, `bootstrap_retries=-1` e `error_callback` explícitos.
- O callback de erro de polling registra mensagem compacta e operacional, evitando depender apenas do traceback padrão do PTB.
- `scripts/config/print_effective_settings.py` passa a reportar os novos parâmetros.
- `.env.example` documenta os parâmetros de rede do Telegram.

## Novas variáveis

```env
TELEGRAM_POLL_TIMEOUT_S=20
TELEGRAM_POLL_INTERVAL_S=1.0
TELEGRAM_REQUEST_CONNECT_TIMEOUT_S=20
TELEGRAM_REQUEST_READ_TIMEOUT_S=60
TELEGRAM_REQUEST_WRITE_TIMEOUT_S=300
TELEGRAM_REQUEST_POOL_TIMEOUT_S=30
TELEGRAM_GET_UPDATES_CONNECT_TIMEOUT_S=30
TELEGRAM_GET_UPDATES_READ_TIMEOUT_S=90
TELEGRAM_GET_UPDATES_WRITE_TIMEOUT_S=30
TELEGRAM_GET_UPDATES_POOL_TIMEOUT_S=30
```

## Limitação

Este patch melhora a tolerância e a diagnosticabilidade, mas não corrige perda real de conectividade. Se `api.telegram.org` estiver inacessível por rede, DNS, VPN, proxy, firewall ou instabilidade do WSL/Windows, o bot continuará sem receber novos comandos até a conectividade voltar.

## Testes sugeridos

```bash
uv run pytest tests/unit/application/test_config.py tests/unit/test_entrypoint_command_registration.py -q
uv run python scripts/config/print_effective_settings.py
```
