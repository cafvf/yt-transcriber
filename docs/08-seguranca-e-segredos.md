# Segurança, segredos e proteção contra vazamento

Este projeto manipula credenciais e dados locais sensíveis, incluindo token do Telegram, token Hugging Face, cookies do YouTube, banco SQLite, logs, áudio baixado e transcrições privadas. A regra operacional é simples:

> Arquivos reais de configuração e runtime ficam na máquina local; o Git recebe apenas código, documentação e exemplos sem segredos.

## Arquivos que não devem ser versionados

- `.env` e variantes locais;
- `cookies.txt` ou qualquer arquivo de cookies do YouTube/navegador;
- `data/`, `downloads/`, `processed/`, `transcripts/`, `logs/`, `models/`;
- bancos `*.db`, `*.sqlite`, `*.sqlite3`;
- logs `*.log`;
- backups (`yt-transcriber-backups/`, tarballs, dumps SQLite, cópias de `.env`/env systemd);
- áudios, vídeos e legendas gerados localmente.

O `.gitignore` do projeto já bloqueia esses caminhos.

## Logs de auditoria locais

Jobs de transcrição gravam eventos estruturados em `data/logs/execution_audit.jsonl` para permitir auditoria de fila, etapas e resultado sem misturar ruído de polling do Telegram. O arquivo é local e ignorado pelo Git. Os eventos devem manter apenas metadados operacionais sanitizados: tokens, cookies, cabeçalhos `Authorization`, corpos de API, prompts, corpo de transcrição e payload completo de chat são mascarados ou omitidos.

`/healthcheck`, `/lasterror`, mensagens de falha no Telegram e logs operacionais sanitizam segredos comuns antes de expor diagnósticos, incluindo tokens configurados, cookies, cabeçalhos `Authorization`, corpos de API, prompts e transcrições ecoadas por exceções. Ainda assim, eles podem revelar metadados privados: `user_id`, paths locais preservados para recovery, nomes de arquivos, nomes de modelos, status de jobs e trechos técnicos de exceções. Compartilhe saídas completas apenas em canais privados de confiança. Para pedir ajuda pública, remova paths, IDs, títulos de vídeos e qualquer contexto que identifique o conteúdo transcrito.

`/search <texto>` também é dado privado: a consulta e seus resultados ficam
restritos aos jobs concluídos do usuário autorizado. Trechos retornados são
sanitizados e compactos; consultas, corpo integral de transcrições/resumos,
paths, tokens e resultados não devem ser gravados em logs operacionais. O índice
FTS5, quando existir, é dado derivado local e deve permanecer sob as mesmas
regras de retenção e backup do SQLite e dos artefatos privados.

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

## Backups e restore

Backups de produção privada são sensíveis. Eles podem conter banco SQLite, transcrições privadas, áudio, logs, caminhos locais, `.env`, arquivo de ambiente systemd e cookies. Use o procedimento em [`11-operator-runbook.md`](./11-operator-runbook.md#4-backup) e aplique no mínimo:

```bash
chmod -R go-rwx ~/yt-transcriber-backups
```

Recomendações:

- guarde backups em volume criptografado ou destino com controle de acesso;
- defina retenção curta para mídia e logs. Não apague snapshots de segmentos
  indiscriminadamente: eles sustentam histórico, exportações e `/rename`.
  Quando for descartá-los, faça isso junto com a transcrição e o registro do
  job, após confirmar que não precisa mais do histórico;
- nunca anexe backups a issues, chats públicos ou pull requests;
- ao restaurar, pare o serviço antes de sobrescrever `data/`, `jobs.db`, `models/` ou arquivos de ambiente;
- trate `operational_errors.jsonl` e `execution_audit.jsonl` como dados privados mesmo sendo sanitizados.

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
