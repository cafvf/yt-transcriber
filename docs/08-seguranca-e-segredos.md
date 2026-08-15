# Segurança, segredos e proteção contra vazamento

Este projeto manipula credenciais e dados locais sensíveis, incluindo token do Telegram, token Hugging Face, cookies do YouTube, banco SQLite, logs, áudio baixado e transcrições privadas. A regra operacional é simples:

> Arquivos reais de configuração e runtime ficam na máquina local; o Git recebe apenas código, documentação e exemplos sem segredos.

A superfície Telegram suportada é **single-operator e private-chat-only**. O operador configurado não deve iniciar processamento, consultas privadas, mutações, diagnósticos ou entrega de artefatos a partir de grupos, supergrupos ou canais.

## Arquivos que não devem ser versionados

- `.env` e variantes locais;
- `cookies.txt` ou qualquer arquivo de cookies do YouTube/navegador;
- `data/`, `downloads/`, `processed/`, `transcripts/`, `logs/`, `models/`;
- bancos `*.db`, `*.sqlite`, `*.sqlite3`;
- logs `*.log`;
- backups (`yt-transcriber-backups/`, tarballs e dumps SQLite);
- áudios, vídeos e legendas gerados localmente.

O `.gitignore` do projeto já bloqueia esses caminhos.

## Classificação de dados privados

São privados por padrão, mesmo depois de sanitização:

- mídia de origem e arquivos convertidos;
- transcrições, snapshots, aliases de falantes e artefatos derivados;
- consultas e resultados de busca, índices locais e histórico;
- identificadores de transporte/provedor quando não forem necessários ao operador;
- paths locais e nomes de arquivos que revelem estrutura privada;
- logs, auditoria e registros de erro;
- backups e evidências operacionais.

Sanitizar um valor remove ou mascara material inadequado para divulgação, mas **não transforma o dado em público**. Compartilhe logs e diagnósticos completos somente em canais privados de confiança.

## Logs de auditoria locais

Jobs de transcrição gravam eventos estruturados em `data/logs/execution_audit.jsonl` para permitir auditoria de fila, etapas e resultado sem misturar ruído de polling do Telegram. O arquivo é local e ignorado pelo Git. Os eventos mantêm apenas metadados operacionais sanitizados: tokens, cookies, cabeçalhos `Authorization`, corpos de API, prompts, corpo de transcrição e payload completo de chat são mascarados ou omitidos. Paths são tratados como privados quando uma indicação de disponibilidade é suficiente.

`/healthcheck`, `/lasterror`, mensagens de falha no Telegram e logs operacionais usam a mesma política central de sanitização para tokens, cookies, cabeçalhos `Authorization`, corpos de API, prompts e transcrições ecoadas por exceções. Se a própria sanitização falhar, o detalhe bruto não é devolvido: usa-se uma mensagem genérica segura.

`/search <texto>` também é dado privado: a consulta e seus resultados ficam restritos aos jobs concluídos do usuário autorizado. Trechos retornados são sanitizados e compactos; consultas, corpo integral de transcrições/resumos, paths, tokens e resultados não devem ser gravados em logs operacionais. O índice FTS5, quando existir, é dado derivado local e deve permanecer sob as mesmas regras de retenção e backup do SQLite e dos artefatos privados.

## Arquivo de exemplo

Use `.env.example` como modelo seguro:

```bash
cp .env.example .env
```

Depois edite o `.env` local com seus valores reais. Nunca committe o `.env` real.

Para Hugging Face, use o menor escopo prático para a capacidade aprovada — normalmente um token **read-only** quando o acesso ao modelo permitir. Para qualquer outro provedor, limite a chave ao endpoint/serviço necessário; não reutilize credenciais amplas se existir uma credencial mais restrita.

`SUMMARY_TOKENIZER_TRUST_REMOTE_CODE` é uma configuração de segurança. O padrão é `false`. Só habilite código remoto para um tokenizer/modelo explicitamente confiável e após revisão deliberada; cache local não altera essa política.

`uv.lock` é a autoridade reprodutível para instalações aprovadas (`uv sync --locked`). O uso de `transformers` no tokenizer de sumarização é uma capacidade opcional explícita: em `SUMMARY_TOKENIZER_BACKEND=auto`, ausência/falha de carregamento local cai para a estimativa por caracteres; em `hf`, a ausência é erro explícito. Essa relação de fallback é coberta por testes e não autoriza download ou execução de código remoto.

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

## Credenciais expostas

Se uma credencial reutilizável apareceu em log, chat, issue, screenshot, prompt de IA ou commit fora do controle previsto, considere-a comprometida. O procedimento correto é:

1. **revogar ou rotacionar** a credencial no provedor;
2. gerar nova credencial com o menor escopo prático;
3. atualizar apenas a fonte local de runtime autorizada;
4. eliminar cópias locais desnecessárias e impedir novo versionamento;
5. verificar logs/artefatos compartilhados e registrar a resposta ao incidente sem reproduzir o segredo.

Mascarar, apagar a mensagem ou reescrever o histórico local **não substitui** revogação/rotação.

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

Backups de dados continuam privados. O **backup operacional padrão não deve carregar credenciais reutilizáveis**: exclua `.env`, arquivo de ambiente systemd, cookies de navegador/YouTube e outros segredos. Esses itens devem ser reprovisionados separadamente no host de destino.

Até a reconciliação operacional completa do PLAN-006, qualquer instrução legada de runbook que copie esses arquivos para o backup padrão deve ser considerada **obsoleta e insegura**. O procedimento operacional futuro poderá documentar um pacote de recuperação de credenciais separado, mas ele não faz parte do backup padrão.

O procedimento completo de backup/restore e a reconciliação do runbook pertencem ao fechamento operacional posterior; esta política de segurança já é normativa para qualquer execução intermediária.

Aplique no mínimo:

```bash
chmod -R go-rwx ~/yt-transcriber-backups
```

Helpers operacionais que criam evidências ou backups devem usar diretórios `0700` e arquivos `0600`. Confirme os modos depois de copiar dados para outro host ou volume, pois permissões do destino podem ser mais permissivas.

Recomendações:

- guarde backups em volume criptografado ou destino com controle de acesso;
- defina retenção curta para mídia e logs. Não apague snapshots de segmentos indiscriminadamente: eles sustentam histórico, exportações e `/rename`;
- nunca anexe backups a issues, chats públicos ou pull requests;
- ao restaurar, pare o serviço antes de sobrescrever dados persistentes;
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
