# YT Transcriber Bot

Bot privado do Telegram para processar vídeos do YouTube e gerar artefatos auditáveis de transcrição. O fluxo principal recebe um link, baixa metadados/áudio com `yt-dlp`, usa legendas do YouTube quando a qualidade é aceitável, transcreve com WhisperX quando necessário, diariza falantes com pyannote, renderiza Markdown e permite exportações derivadas.

A versão atual também inclui exportação JSON/SRT/VTT, MP4 com legenda selecionável, renomeação/mesclagem de falantes por botões inline, histórico local em SQLite, sumarização via LM Studio/OpenAI-compatible com controle de contexto, tokenizer opcional, deduplicação, progresso no Telegram e retentativa adaptativa em caso de timeout, além de comandos de observabilidade operacional (`/healthcheck` e `/lasterror`).

## Paradigma de desenvolvimento

O projeto é conduzido com **Spec-Driven Development (SDD)** apoiado por IA: a especificação funcional e os documentos de arquitetura orientam a implementação antes do código. A IA é usada como agente de desenvolvimento, revisão, geração de patches e ampliação de testes, mas as decisões de produto, validação manual e curadoria final permanecem humanas.

Princípios complementares:

- **Extreme Programming**: entregas incrementais, escopo pequeno por rodada e feedback rápido.
- **Test-Driven Development**: bugs relevantes devem virar testes de regressão antes ou junto da correção.
- **Arquitetura hexagonal / Ports & Adapters**: domínio e aplicação separados de Telegram, YouTube, ffmpeg, WhisperX, pyannote, SQLite e LM Studio.
- **Reprodutibilidade e auditabilidade**: cada artefato deve preservar metadados suficientes para entender entrada, modelo, idioma, origem da transcrição e parâmetros relevantes.
- **Segurança por padrão**: `.env`, cookies, tokens, logs sensíveis e bancos locais não devem ser versionados.

---

## Documentação

Toda a documentação detalhada está na pasta [`docs/`](./docs/):

| Documento | Conteúdo |
|---|---|
| [`docs/01-contrato-funcional.md`](./docs/01-contrato-funcional.md) | Contrato funcional e decisões de produto já consolidadas. |
| [`docs/02-arquitetura.md`](./docs/02-arquitetura.md) | Arquitetura técnica, camadas, ports/adapters, modelo de dados e organização de diretórios. |
| [`docs/03-manual-de-uso.md`](./docs/03-manual-de-uso.md) | Comandos atuais do bot, fluxos de uso, sumarização, exportações e troubleshooting. |
| [`docs/04-manual-de-instalacao.md`](./docs/04-manual-de-instalacao.md) | Instalação em Linux/WSL2, `uv`, dependências de sistema, cookies, pyannote e LM Studio. |
| [`docs/05-plano-de-execucao.md`](./docs/05-plano-de-execucao.md) | Histórico do plano em gates e critérios de aceitação. |
| [`docs/06-funcionalidades-futuras.md`](./docs/06-funcionalidades-futuras.md) | Roadmap revisado: busca textual/semântica, texto limpo, upload de áudio, ASR multilíngue, tradução, `/redo` e Obsidian. |
| [`docs/07-glossario-e-decisoes.md`](./docs/07-glossario-e-decisoes.md) | Glossário técnico e registros de decisão arquitetural. |
| [`docs/08-seguranca-e-segredos.md`](./docs/08-seguranca-e-segredos.md) | Política de segredos, `.gitignore`, pre-commit, scanners locais e cuidados operacionais. |

> A especificação é o contrato do projeto. Alterações relevantes devem ser refletidas primeiro nos documentos, depois nos testes, depois no código.

---

## Capacidades atuais

### Entrada, fila e histórico

- Recebe links do YouTube por mensagem direta ou por `/transcribe <link>`.
- Aceita override de idioma por `/pt <link>`, `/en <link>` ou `--lang pt|en`.
- Mantém fila sequencial com deduplicação e limite configurável.
- Permite consultar fila e status com `/queue`, `/fila` e `/status`.
- Permite cancelar job atual ou fila com `/cancel`, `/cancelall`, `/cancelartudo`, `/clearqueue`, `/cancelqueue`, `/limparfila`.
- Lista histórico com `/list` e reenvia transcrições com `/last [n]`.

### Transcrição e diarização

- Baixa metadados e áudio com `yt-dlp`.
- Usa cookies do YouTube via browser ou arquivo Netscape quando configurados.
- Rejeita legendas automáticas ruins do YouTube e cai para WhisperX.
- Usa WhisperX para ASR e pyannote/WhisperX para diarização.
- Suporta política de modelo por idioma com `WHISPER_MODEL=auto`, `WHISPER_MODEL_PT`, `WHISPER_MODEL_EN` e `WHISPER_MODEL_DEFAULT`.
- Renderiza Markdown estruturado com metadados, falantes e turnos com timestamps.

### Revisão de falantes

- `/rename [n]` abre botões inline para renomear um ou vários falantes em sequência.
- O mesmo nome pode ser atribuído a múltiplos `SPEAKER_XX` para mesclar falantes.
- Também aceita mapeamento em lote (`SPEAKER_00=João, SPEAKER_01=Maria`).
- O Markdown é re-renderizado e blocos consecutivos do mesmo nome exibido são unidos.

### Exportações

- `/json [n]` ou `/export json [n]`: exporta JSON estruturado.
- `/srt [n]` ou `/export srt [n]`: exporta legenda SubRip.
- `/vtt [n]` ou `/export vtt [n]`: exporta legenda WebVTT.
- `/video_subs [n]` ou `/videosubs [n]`: gera MP4 com legenda selecionável, sem queimar legenda na imagem.

### Sumarização via LM Studio

- `/summary [n]` gera Markdown de resumo a partir de uma transcrição já concluída.
- Usa backend OpenAI-compatible, com LM Studio como alvo local recomendado.
- Valida `SUMMARY_MODEL` contra `/v1/models`, quando habilitado.
- Envia `enable_thinking=false`, `chat_template_kwargs={"enable_thinking": false}` e `reasoning_effort="none"` quando `SUMMARY_DISABLE_THINKING=true`.
- Rejeita resposta vazia que contenha apenas `reasoning_content`.
- Usa chunking por tokenizer Hugging Face local quando disponível; caso contrário, usa estimativa por caracteres/token.
- Deduplica trechos adjacentes e une segmentos consecutivos do mesmo falante antes da sumarização.
- Usa limites separados para resumos parciais e síntese final.
- Em caso de timeout, subdivide o chunk e tenta novamente até o limite configurado.
- Mostra progresso no Telegram durante o processamento.


### Observabilidade operacional

- `/healthcheck` executa um diagnóstico consolidado do ambiente, incluindo configuração obrigatória, `.env` efetivo, `ffmpeg`/`ffprobe`, `yt-dlp`, módulos Python essenciais, diretórios graváveis, SQLite, espaço em disco, cookies do YouTube, LM Studio e presença de `SUMMARY_MODEL` em `/v1/models`.
- `/lasterror` exibe o último erro operacional sanitizado, cobrindo jobs de transcrição falhos e falhas derivadas de `/summary`, exportações, vídeo com legenda, limpeza de cache, `/clearcache` e exceções defensivas no pipeline.
- Erros operacionais derivados são registrados em `data/logs/operational_errors.jsonl` com operação, etapa, severidade, classe da exceção, contexto, traceback final sanitizado e sugestões de verificação quando disponíveis.
- A execução de jobs também gera auditoria estruturada em `data/logs/execution_audit.jsonl`, com eventos de fila/job/etapa e sem corpo de transcrição, payload de chat, tokens, cookies ou ruído de polling do Telegram.

---

## Status atual

| Área | Status |
|---|---|
| Bootstrap, configuração, domínio e persistência | Implementados |
| Download YouTube, cookies e metadados | Implementados |
| Transcrição WhisperX e diarização pyannote | Implementadas |
| Markdown de transcrição | Implementado |
| Fila, cancelamento e histórico | Implementados |
| Renomeação e mesclagem de falantes | Implementadas |
| Exportação JSON/SRT/VTT | Implementada |
| MP4 com legenda selecionável | Implementado |
| Sumarização via LM Studio/OpenAI-compatible | Implementada e estabilizada operacionalmente |
| Segurança local e pre-commit | Implementados |
| `/healthcheck` e `/lasterror` | Implementados |
| Busca textual nas transcrições e resumos | Próxima funcionalidade priorizada |
| Busca semântica | Planejada como evolução arquitetural da busca |
| Exportação de texto limpo `/text [n]` | Funcionalidade futura priorizada |
| Transcrição de arquivo de áudio enviado ao Telegram | Funcionalidade futura registrada |
| Backend ASR multilíngue alternativo | Funcionalidade futura priorizada antes de tradução e Obsidian |
| Tradução controlada | Funcionalidade futura posterior ao suporte ASR multilíngue |
| Notas Obsidian/Notion | Funcionalidade futura de menor prioridade relativa |

Limitações atuais importantes:

- `/healthcheck` não substitui logs completos: ele resume o estado operacional e deve ser usado como triagem inicial.
- `/lasterror` depende de erro persistido no banco de jobs ou em `data/logs/operational_errors.jsonl`; falhas catastróficas antes da inicialização completa do bot ainda exigem consulta ao terminal, systemd ou arquivo de log.
- `/redo <link>` reprocessa imediatamente como novo job; confirmação inline com diff de configuração permanece futura.
- `/video_subs` gera apenas legenda selecionável; legenda queimada não está no escopo atual.
- O bot ainda não aceita upload direto de áudio como entrada; apenas links do YouTube.
- A busca no histórico ainda não está implementada.

---

## Como começar

```bash
# 1. Clonar e entrar
git clone <repo>
cd yt-transcriber-bot

# 2. Instalar uv, se ainda não existir
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Criar ambiente e instalar dependências
uv sync

# 4. Instalar dependências de sistema
sudo dnf install ffmpeg          # Fedora
sudo apt install ffmpeg          # Ubuntu/WSL

# 5. Criar configuração local
cp .env.example .env

# 6. Editar .env com tokens e caminhos locais
# TELEGRAM_BOT_TOKEN=...
# TELEGRAM_ALLOWED_USER_ID=...
# HF_TOKEN=...

# 7. Verificar configuração efetiva
uv run python scripts/config/print_effective_settings.py

# 8. Rodar o bot
uv run python -m yt_transcriber_bot
```

Para diarização, aceite os termos dos modelos pyannote no Hugging Face conforme descrito em [`docs/04-manual-de-instalacao.md`](./docs/04-manual-de-instalacao.md).

---

## Configuração recomendada de modelos

### Whisper por idioma

```env
WHISPER_MODEL=auto
WHISPER_MODEL_PT=large-v3
WHISPER_MODEL_EN=medium
WHISPER_MODEL_DEFAULT=medium
```

Para português técnico ou fala espontânea brasileira, teste modelos especializados, por exemplo:

```env
WHISPER_MODEL_PT=inesc-id/WhisperLv3-X-PT-All
```

### Sumarização local

Exemplo para LM Studio:

```env
SUMMARY_BACKEND=openai_compatible
SUMMARY_BASE_URL=http://127.0.0.1:1234/v1
SUMMARY_MODEL=qwen/qwen3.5-9b
SUMMARY_TEMPERATURE=0.2
SUMMARY_DISABLE_THINKING=true
SUMMARY_VALIDATE_MODEL=true
SUMMARY_STRICT_MODEL_MATCH=true

SUMMARY_TOKENIZER_BACKEND=auto
SUMMARY_MAX_INPUT_TOKENS=6000
SUMMARY_MAX_CHARS_PER_CHUNK=18000
SUMMARY_CHARS_PER_TOKEN=2.5
SUMMARY_PARTIAL_MAX_TOKENS=512
SUMMARY_FINAL_MAX_TOKENS=1024
SUMMARY_TIMEOUT_S=600
SUMMARY_TIMEOUT_SPLIT_RETRIES=2
```

Use em `SUMMARY_MODEL` exatamente o `id` retornado por:

```bash
curl http://127.0.0.1:1234/v1/models
```

---

## Segurança e pre-commit

Configuração recomendada:

```bash
cp .env.example .env
uv sync --dev
uv run pre-commit install
uv run pre-commit run --all-files
```

Os hooks locais bloqueiam `.env`, cookies do YouTube, bancos SQLite, logs e padrões comuns de tokens. Se `gitleaks` estiver instalado no sistema, ele roda como camada complementar; se não estiver, o hook avisa e continua.

Nunca publique tokens, cookies, logs completos com segredos, bancos SQLite de produção ou arquivos `.env`.

---

## Próximo gate recomendado

**Gate 8 — Busca e recuperação de conhecimento**

A observabilidade operacional (`/healthcheck` e `/lasterror`) está implementada. O próximo incremento recomendado é transformar o histórico local em uma base consultável, começando por busca textual e deixando a arquitetura preparada para busca semântica.

Escopo proposto para o MVP:

- `/search <texto>` para busca textual em transcrições, resumos e metadados.
- Indexação de Markdown, summaries, título, canal, URL, `video_id`, idioma e falantes renomeados.
- Uso de SQLite FTS5 quando disponível, com fallback documentado se o ambiente não suportar FTS5.
- Atualização automática do índice após nova transcrição, `/rename` e `/summary`.
- Testes de ranking básico, busca sem resultado, sanitização e compatibilidade com transcrições antigas.

Evolução prevista da própria busca:

- `/search semantic <texto>` ou comando equivalente para busca por embeddings locais.
- `/related [n]` para encontrar transcrições/resumos semanticamente próximos.
- Separação explícita entre índice textual e índice vetorial, sem substituir a transcrição literal como fonte da verdade.

Roadmap priorizado após o Gate 8:

1. `/text [n]` para exportação de texto limpo.
2. Upload de arquivo de áudio pelo Telegram para transcrição sem YouTube.
3. Backend alternativo de ASR e suporte multilíngue ampliado.
4. `/translate` como artefato derivado posterior ao suporte multilíngue.
5. Melhorias no `/redo`.
6. Integração com Obsidian/Notion.

Itens removidos da prioridade principal atual:

- `/stats`, por não ser necessário ao fluxo de uso atual.
- Recuperação avançada após interrupção, por não justificar complexidade imediata.

---

## Licença

A definir pelo proprietário do projeto.
