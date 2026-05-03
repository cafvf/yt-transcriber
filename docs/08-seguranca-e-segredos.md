# Segurança, segredos e proteção contra vazamento

Este projeto manipula credenciais e dados locais sensíveis, incluindo token do Telegram, token Hugging Face, cookies do YouTube, banco SQLite, logs, áudio baixado e transcrições privadas. A regra operacional é simples:

> Arquivos reais de configuração e runtime ficam na máquina local; o Git recebe apenas código, documentação e exemplos sem segredos.

## Arquivos que não devem ser versionados

- `.env` e variantes locais;
- `cookies.txt` ou qualquer arquivo de cookies do YouTube/navegador;
- `data/`, `downloads/`, `processed/`, `transcripts/`, `logs/`, `models/`;
- bancos `*.db`, `*.sqlite`, `*.sqlite3`;
- logs `*.log`;
- áudios, vídeos e legendas gerados localmente.

O `.gitignore` do projeto já bloqueia esses caminhos.

## Arquivo de exemplo

Use `.env.example` como modelo seguro:

```bash
cp .env.example .env
```

Depois edite o `.env` local com seus valores reais. Nunca committe o `.env` real.

## Pre-commit

Instale as dependências de desenvolvimento:

```bash
uv sync --dev
```

Instale os hooks:

```bash
uv run pre-commit install
```

Execute manualmente em todos os arquivos:

```bash
uv run pre-commit run --all-files
```

O projeto usa hooks locais, sem depender de repositórios remotos do `pre-commit`:

1. `local-secret-guard`: bloqueia arquivos sensíveis e padrões óbvios de tokens;
2. `gitleaks-if-available`: roda `gitleaks` se o binário estiver instalado no sistema.

Se `gitleaks` não estiver instalado, o hook apenas avisa e continua. O scanner local continua obrigatório.

## Gitleaks opcional

Se quiser a camada complementar, instale o `gitleaks` no sistema e confirme:

```bash
gitleaks version
```

Depois rode:

```bash
uv run python scripts/security/gitleaks_if_available.py --all
```

ou diretamente:

```bash
gitleaks detect --source . --redact --verbose --config .gitleaks.toml
```

## Varredura local sem Gitleaks

Mesmo sem Gitleaks, o scanner local pode ser usado:

```bash
uv run python scripts/security/scan_secrets.py --all
```

Ele verifica, entre outros:

- tokens do Telegram;
- tokens Hugging Face;
- chaves OpenAI/GitHub/Google;
- conteúdo típico de arquivo cookies Netscape;
- atribuições sensíveis como `TELEGRAM_BOT_TOKEN=...` e `HF_TOKEN=...`;
- arquivos grandes demais para commit;
- bancos, logs, cookies e `.env` reais.

## Antes de publicar o repositório

Rode:

```bash
uv run pre-commit run --all-files
uv run python scripts/security/scan_secrets.py --all
uv run python scripts/security/gitleaks_if_available.py --all
```

Se o projeto for para GitHub, habilite também Secret Scanning e Push Protection, quando disponíveis.

## Tokens já expostos

Se um token apareceu em log, chat, issue ou commit, considere-o comprometido. O procedimento correto é:

1. revogar o token no provedor;
2. gerar novo token;
3. atualizar apenas o `.env` local;
4. garantir que logs antigos com o token não sejam commitados.


## Correção de instalação dos hooks

Se `uv run pre-commit run --all-files` retornar:

```text
InvalidConfigError: .pre-commit-config.yaml is not a file
```

verifique se o patch foi copiado preservando dotfiles. Evite comandos como:

```bash
cp -r yt-transcriber-bot/* .
```

porque `*` não copia arquivos iniciados por ponto. Prefira:

```bash
cp -a yt-transcriber-bot/. .
```

ou rode o bootstrap:

```bash
uv run python scripts/security/bootstrap_precommit.py
```

O arquivo `config/pre-commit-config.yaml` é uma cópia de recuperação para recriar `.pre-commit-config.yaml` quando dotfiles forem omitidos acidentalmente.

## Instalação do pre-commit

`pre-commit` também foi mantido nas dependências principais do projeto para que `uv sync` disponibilize o comando sem exigir flags extras. Se o lock estiver antigo, rode:

```bash
uv lock
uv sync
```

Como fallback:

```bash
uv pip install -r requirements-dev.txt
```
