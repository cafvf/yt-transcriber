# Patch notes — security pre-commit fix

Este patch corrige a instalação dos hooks de segurança.

## Correções

- `pre-commit` foi movido para as dependências principais do `pyproject.toml`, para que `uv sync` instale o comando sem depender de flags de grupos de desenvolvimento.
- `requirements-dev.txt` foi adicionado como fallback para ambientes onde o lock/grupo de desenvolvimento não esteja sincronizado.
- `config/pre-commit-config.yaml` foi adicionado como cópia de recuperação da configuração principal.
- `scripts/security/bootstrap_precommit.py` foi adicionado para recriar `.pre-commit-config.yaml` quando dotfiles não forem copiados por engano.
- A documentação de segurança agora explica que `cp -r pacote/* .` não copia dotfiles e pode causar `InvalidConfigError: .pre-commit-config.yaml is not a file`.

## Comandos recomendados

```bash
uv lock
uv sync
uv run python scripts/security/bootstrap_precommit.py
uv run pre-commit run --all-files
```

Fallback:

```bash
uv pip install -r requirements-dev.txt
uv run python scripts/security/bootstrap_precommit.py
uv run pre-commit run --all-files
```
