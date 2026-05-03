# Patch notes — pre-commit usa `python3`

## Correção

A configuração local do `pre-commit` chamava `python`, o que falha em ambientes Linux onde apenas `python3` está disponível no `PATH`.

Este patch altera os hooks locais para chamar explicitamente:

```yaml
entry: python3 scripts/security/scan_secrets.py
entry: python3 scripts/security/gitleaks_if_available.py --staged
```

A mesma correção foi aplicada em:

- `.pre-commit-config.yaml`
- `config/pre-commit-config.yaml`

## Ajuste adicional

O filtro `types_or: [text]` foi removido do scanner local. Assim, o hook recebe todos os arquivos staged e consegue bloquear extensões sensíveis como `.db`, `.sqlite`, `.log`, `cookies.txt` e `.env`, mesmo quando o pre-commit não classificaria o arquivo como texto.

## Comandos recomendados

```bash
uv run python scripts/security/bootstrap_precommit.py
uv run pre-commit clean
uv run pre-commit install
uv run pre-commit run --all-files
```
