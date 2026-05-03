# Patch 2026-05-03 — Segurança, pre-commit e Gitleaks opcional

## Objetivo

Reduzir o risco de versionar acidentalmente dados pessoais, tokens, cookies do YouTube, logs, bancos locais, áudios e transcrições privadas.

## Mudanças

- Adicionado `.env.example` seguro com placeholders.
- Expandido `.gitignore` para bloquear `.env`, cookies, bancos, logs, artefatos de áudio/vídeo e pastas de runtime.
- Adicionado `.pre-commit-config.yaml` com hooks locais, sem dependência de repositórios remotos do pre-commit.
- Adicionado `scripts/security/scan_secrets.py`, scanner local sem dependências externas.
- Adicionado `scripts/security/gitleaks_if_available.py`, que roda `gitleaks` se estiver instalado e apenas avisa quando não estiver.
- Adicionado `.gitleaks.toml` com padrões específicos para Telegram, Hugging Face, OpenAI, GitHub, Google e cookies Netscape/YouTube.
- Adicionado `pre-commit` ao grupo `dev` do `pyproject.toml`.
- Adicionada documentação em `docs/08-seguranca-e-segredos.md`.
- Atualizados README e manual de instalação com instruções de segurança.

## Comandos recomendados

```bash
uv sync --dev
uv run pre-commit install
uv run pre-commit run --all-files
```

Varredura manual:

```bash
uv run python scripts/security/scan_secrets.py --all
uv run python scripts/security/gitleaks_if_available.py --all
```
