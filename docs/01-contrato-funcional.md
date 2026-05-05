# Contrato Funcional

Este documento consolida o **contrato funcional** do YT Transcriber Bot, fruto de cinquenta perguntas objetivas feitas ao usuário durante a fase de levantamento de requisitos. Ele é a **fonte única de verdade** sobre o comportamento esperado do sistema. Toda decisão registrada aqui possui justificativa explícita, e qualquer alteração futura deve ser refletida primeiro neste documento, depois nos testes, depois no código.

A organização é **temática**, não cronológica. Cada seção agrupa decisões de uma mesma área de negócio.

---

## A. Perfil do usuário e autorização

### A.1 Usuário único autorizado
O bot opera para **um único usuário humano**, identificado por seu `user_id` numérico do Telegram (não pelo `@username`, que é mutável). Esse identificador é provido por **variável de ambiente do usuário do sistema operacional**, sob o nome `TELEGRAM_ALLOWED_USER_ID`. A escolha do `user_id` numérico evita a vulnerabilidade de troca de username e atende ao requisito de unicidade absoluta de acesso.

### A.2 Tratamento de remetentes não-autorizados
Mensagens de qualquer outro `user_id` são **ignoradas silenciosamente**: o bot não responde, não loga, não registra a tentativa em arquivo. Esta política maximiza a privacidade e impede a enumeração do bot por terceiros (não há feedback que confirme sequer a existência do bot).

### A.3 Token do bot e segredos
O `TELEGRAM_BOT_TOKEN` (obtido do BotFather), o `TELEGRAM_ALLOWED_USER_ID` e o `HF_TOKEN` (Hugging Face, necessário para o pyannote) são **variáveis de ambiente do usuário do sistema operacional**, configuradas em `~/.bashrc`, `~/.zshrc` ou equivalente. Eles **não** ficam em arquivo `.env` versionado nem em qualquer outro local do projeto. O bot **falha rapidamente no startup** se qualquer um deles estiver ausente, com mensagem clara apontando o que está faltando e como configurar.

### A.4 Configurações não-sensíveis
Parâmetros de comportamento (modelo do Whisper, bitrate do áudio, paths, retenção, idiomas permitidos) podem ser definidos em um arquivo `.env` **opcional** na raiz do projeto. Se ausente, o sistema usa defaults sensatos definidos no código.

---

## B. Aquisição de vídeos do YouTube

### B.1 Aceitação de URLs
O bot aceita mensagens contendo URLs do YouTube em formato livre (texto solto com URL embutido), extraindo a **primeira ocorrência** de URL válido. Tipos de URL aceitos:
- Vídeos comuns: `https://www.youtube.com/watch?v=<id>`
- URLs encurtadas: `https://youtu.be/<id>` (normalizadas internamente)
- Shorts: `https://www.youtube.com/shorts/<id>` (tratados como vídeos normais)
- VOD de live finalizada: tratada como vídeo normal
- Parâmetro `&list=<playlistid>`: **ignorado** (apenas o vídeo do `?v=` é processado)

Tipos **rejeitados**:
- Lives ao vivo em andamento
- Vídeos privados ou removidos
- Vídeos idade-restritos sem cookies configurados
- Vídeos members-only sem cookies configurados (com cookies, são aceitos — ver B.6)
- Mensagens sem URL detectado: o bot responde "Não detectei link do YouTube válido. Use /help para ver os comandos."

### B.2 Faixa de áudio em vídeos com auto-dublagem
O YouTube oferece dublagens automáticas em vários idiomas para certos vídeos (rotulados como *Auto-dubbed*). O bot **sempre baixa a faixa de áudio original** (a do criador), nunca uma versão dublada, **avisando o usuário no chat** quando detecta que o vídeo tem múltiplas faixas. Esta política preserva a fidelidade da fala (vozes humanas reais) e a qualidade da diarização (que depende de características vocais autênticas).

### B.3 Aproveitamento de legendas existentes
O YouTube hospeda três tipos de legenda:
1. **Manuais** (criadas pelo autor) — alta qualidade.
2. **Auto-geradas por ASR** — qualidade variável, sem pontuação consistente.
3. **Traduzidas automaticamente** — má qualidade.

Política do bot:
- **Legenda manual no idioma original do áudio**: usada como transcrição; apenas a diarização é executada. Avisa o usuário e marca no MD a origem (`Transcrição: legenda manual do YouTube`).
- **Legenda auto-gerada no idioma original**: usada como fallback antes de recorrer ao WhisperX; o MD marca `Transcrição: legenda auto-gerada do YouTube`. O botão inline `[Refazer com WhisperX]` permanece como evolução futura; na versão atual, use `/redo <link>`.
- **Legenda traduzida** ou em outro idioma: tratada como **inexistente**.
- **Sem legenda válida**: WhisperX é executado normalmente.

A justificativa é poupar tempo de CPU/GPU quando o YouTube já fornece transcrição confiável, sem sacrificar qualidade.

### B.4 Validação de duração
- **Limite hard**: 3 horas (180 minutos). Vídeos acima são rejeitados antes do download, com mensagem clara.
- O limite é configurável via `MAX_VIDEO_DURATION_MIN` (default 180).
- Vídeos acima de **1 hora** geram um aviso no chat (não bloqueio): "Vídeo longo (X min). Em CPU pode levar Y min para transcrever."

### B.5 Validação de idioma e conteúdo
- **Idiomas permitidos**: português brasileiro (`pt`) e inglês (`en`). Configurável via `LANGUAGE_ALLOWLIST`.
- Vídeos cujo idioma original detectado esteja fora da allowlist são **rejeitados** com mensagem identificando o idioma detectado.
- Vídeos sem fala suficiente (música, instrumental) são **rejeitados** após análise por VAD (Voice Activity Detection): se menos de um percentual mínimo do áudio for fala, o job é descartado.
- A capacidade de processar outros idiomas e/ou traduzir transcrições está documentada em [`06-funcionalidades-futuras.md`](./06-funcionalidades-futuras.md).

### B.6 Vídeos members-only e cookies
Para acessar vídeos restritos a membros de canais aos quais o usuário é assinante, o bot suporta dois mecanismos de autenticação, em ordem de preferência:
1. **Cookies extraídos do navegador**: variável `YOUTUBE_COOKIES_BROWSER=firefox` (ou `chrome`, `chromium`, etc.) faz o `yt-dlp` ler diretamente do perfil do navegador instalado. Mais conveniente, exige acesso ao filesystem do perfil.
2. **Cookies em arquivo Netscape**: variável `YOUTUBE_COOKIES_FILE=/caminho/para/cookies.txt` aponta para um arquivo exportado por extensões como *Get cookies.txt LOCALLY*. Mais portável.

Se ambas estiverem definidas, a primeira (browser) é tentada primeiro. Se ambas estiverem ausentes e o vídeo requerer autenticação, o bot **rejeita** com mensagem orientando como configurar.

O [manual de instalação](./04-manual-de-instalacao.md) traz o passo a passo detalhado de exportação de cookies.

---

## C. Áudio de saída

### C.1 Codec, formato e bitrate
O áudio entregue ao usuário é convertido para:
- **Container**: OGG
- **Codec**: Opus (`libopus`)
- **Canais**: mono
- **Bitrate**: 32 kbps (configurável via `AUDIO_BITRATE_KBPS`)

Esta combinação foi escolhida pela excelente inteligibilidade de voz por byte do Opus em bitrates baixos, resultando em arquivos pequenos (~14 MB por hora de fala) e plenamente compatíveis com o limite de 50 MB do Telegram Bot API.

### C.2 Particionamento para arquivos longos
Se mesmo após compressão o arquivo passar de 50 MB (improvável dentro do limite de 3h, mas possível), o áudio é **dividido em partes sequenciais** (`audio_part01.ogg`, `audio_part02.ogg`, ...) e enviado como múltiplos arquivos no chat, na ordem.

---

## D. Transcrição

### D.1 Motor primário e fallback
- **Primário**: `whisperx` (versão estável corrente, `>=3.8,<4.0`), backend `faster-whisper`.
- O modelo de transcrição é configurável via `WHISPER_MODEL` (`tiny`, `base`, `small`, `medium`, `large-v3`).

### D.2 Auto-detecção de hardware
No startup e a cada job, o bot decide entre CPU e GPU pelo seguinte algoritmo:
1. Se `torch.cuda.is_available()` for `False`, usa CPU.
2. Se a GPU tiver Compute Capability menor que `MIN_GPU_COMPUTE_CAPABILITY` (default 6.0), usa CPU. Esta política exclui GPUs Maxwell antigas (ex.: GeForce 940MX, CC 5.0) que apresentam incompatibilidades com versões recentes de PyTorch.
3. Se a VRAM disponível for menor que o requisito do modelo configurado (tabela: `tiny`/`base` 1 GB, `small` 2 GB, `medium` 5 GB, `large-v3` 10 GB), usa CPU e loga "VRAM insuficiente".
4. Caso contrário, usa CUDA com `compute_type` adequado (`float16` em GPUs com FP16 nativo, `int8_float16` para economizar memória, `int8` em CPU).

A variável `DEVICE` aceita `auto` (default), `cpu` ou `cuda` para forçar.

### D.3 Política de retentativa em falha de transcrição
Se a transcrição falhar no meio (ex.: out-of-memory, crash do CUDA, timeout), o bot:
1. Limpa arquivos parciais e libera memória.
2. **Retenta uma vez**, forçando CPU e descendo um nível no modelo (ex.: `medium` → `small`).
3. **Notifica o usuário** sobre a falha e sobre a retentativa em curso, em mensagem clara.
4. Se a retentativa também falhar, o job é marcado como `failed` e o usuário recebe instruções para usar `/lasterror`.

### D.4 Detecção e validação de idioma
- O WhisperX detecta o idioma automaticamente nos primeiros segundos de áudio.
- Se o idioma detectado não estiver em `LANGUAGE_ALLOWLIST`, o job é abortado (ver B.5).
- Se a confiança da detecção for baixa (< 0.5), o bot escolhe o melhor candidato dentro da allowlist e marca isso no MD.

---

## E. Diarização

### E.1 Motor primário e fallback
- **Primário**: `whisperx.diarize.DiarizationPipeline`, que internamente carrega o modelo `pyannote/speaker-diarization-community-1` (ou versão equivalente embutida na release atual do WhisperX). Este caminho é o oficialmente recomendado pela documentação do WhisperX.
- **Fallback**: `pyannote.audio.Pipeline.from_pretrained("pyannote/speaker-diarization-community-1")` chamado diretamente. Acionado quando o caminho primário lançar exceção (incompatibilidade de versão, mudança de API interna, falha de download do modelo). A integração aceita tanto a API recente `token=...` quanto a API legada `use_auth_token=...`.

Ambos atrás de uma interface única `DiarizationEngine` (Strategy pattern), permitindo trocar para outros engines no futuro (ex.: NVIDIA NeMo, modelos comerciais).

### E.2 Hint de número de falantes
Por padrão, o pyannote decide livremente o número de falantes. **Não há mecanismo de hint do usuário** no MVP (sem parâmetros tipo `?speakers=2` na URL). Em caso de detecção exagerada (ex.: monólogo dividido em vários `SPEAKER_XX`), o usuário pode mitigar via `/rename` atribuindo o **mesmo nome** a múltiplos labels.

### E.3 Cruzamento com legendas existentes
Quando a transcrição vem de legenda do YouTube (B.3) e a diarização é executada, o cruzamento é feito por interseção temporal: cada bloco de legenda recebe o `SPEAKER_XX` cujo intervalo cobre a maior fração do bloco. Este método tem precisão menor que o alinhamento por palavra do WhisperX, e isso é informado ao usuário no MD.

---

## F. Renderização do Markdown

### F.1 Template
O arquivo `.md` segue o template:

```markdown
# Transcrição — <Título do vídeo>

**URL**: https://www.youtube.com/watch?v=<id>
**Canal**: <nome>
**Duração**: HH:MM:SS
**Data do vídeo**: YYYY-MM-DD
**Data da transcrição**: YYYY-MM-DD HH:MM (TZ)
**Modelo**: WhisperX <versão> / pyannote <versão>
**Idioma detectado**: <pt|en> (confiança: 0.XX)
**Origem da transcrição**: <WhisperX | legenda manual do YouTube | legenda auto-gerada do YouTube>
**Falantes identificados**: N

---

## Resumo da diarização
- **SPEAKER_00**: HHmin SSs (XX%)
- **SPEAKER_01**: HHmin SSs (XX%)

---

## Transcrição

### [00:00:00 — 00:00:14] SPEAKER_00
<texto do turno>

### [00:00:14 — 00:00:31] SPEAKER_01
<texto do turno>
```

### F.2 Granularidade dos blocos
Cada bloco corresponde a **um turno de fala**: sempre que o falante muda, abre-se um novo bloco. Turnos consecutivos do mesmo falante são fundidos em um único bloco mesmo que o WhisperX os retorne segmentados.

### F.3 Nomeação dos falantes
- Por padrão, labels genéricos `SPEAKER_00`, `SPEAKER_01`, ...
- O usuário pode renomear posteriormente via `/rename` (ver J.4).
- Renomeações ficam **escopadas ao vídeo**; não há propagação automática entre vídeos.

### F.4 Nome do arquivo
O `.md` é salvo com o nome derivado do **título do vídeo slugificado** (acentos removidos, espaços por hífens, lowercase, caracteres especiais sanitizados). Em caso de colisão (mesmo título já transcrito antes), sufixos `-2`, `-3`, etc. são adicionados.

Exemplo: `"Entrevista com Eduardo Giannetti — Memória e Leitura"` → `entrevista-com-eduardo-giannetti-memoria-e-leitura.md`.

### F.5 Auditoria por link
O cabeçalho **sempre** contém o link do YouTube original. Isso permite, mesmo após o áudio expirar pela política FIFO (ver H), reauditar o conteúdo: o `.md` é autossuficiente como registro histórico.

---

## G. Persistência (SQLite)

### G.1 Banco de dados
Banco SQLite local em `data/jobs.db`, manipulado via SQLAlchemy 2.x. Tabelas principais:
- `jobs` — um registro por job (id, video_id, url, título, canal, duração, status, paths dos artefatos, modelo usado, device, idioma detectado, origem da transcrição, contagem de falantes, timestamps de criação/conclusão, mensagem de erro se aplicável).
- `speakers` — mapeamento `(job_id, speaker_label) → nome_amigável` para renomeações.
- `queue` — fila persistente de jobs pendentes (sobrevive a reinicializações do bot).

### G.2 Persistência da fila
Jobs enfileirados ficam no banco. Em caso de reinício do bot, eles continuam de onde estavam (jobs `pending` voltam para a fila; jobs `processing` são marcados como `failed` e o usuário é notificado quando o bot voltar online — ver L.2).

---

## H. Política de retenção (FIFO)

### H.1 Regra geral
Por job, são produzidos quatro tipos de artefato em pastas separadas: áudio bruto baixado (`data/downloads/`), áudio comprimido para entrega (`data/processed/`), transcrição final (`data/transcripts/`), e log do job (`logs/`).

A **unidade de retenção é o job inteiro**: quando o limite é atingido, todos os artefatos do job mais antigo são removidos juntos.

### H.2 Limite e tratamento diferenciado dos MDs
- **`downloads/`, `processed/`, `logs/`**: limite de **5 jobs**. Quando o 6º job conclui, os artefatos do 1º (mais antigo por timestamp de conclusão) são removidos.
- **`transcripts/` (arquivos `.md`)**: **sem limite**. Os MDs são preservados indefinidamente como histórico, pois são pequenos (KBs) e contêm o link do YouTube no cabeçalho, servindo como registro auditável.

### H.3 Reprocessamento e renomeação
- `/redo`: na versão atual, cria um novo job explícito para reprocessamento do link informado. Substituição in-place e diff de configuração permanecem como evolução futura.
- `/rename`: regenera apenas o `.md` (ou cria um novo no lugar se necessário); **não** altera a posição na fila FIFO; **não** renova o timestamp do job.

### H.4 Jobs falhados
Jobs que falharam (status `failed` ou `cancelled`) **não contam** para o limite de 5: eles não geraram artefatos finais. O registro no SQLite permanece para auditoria.

### H.5 Operação em vídeos legados
Após a expiração FIFO, o `.md` permanece, mas os áudios não. Operações possíveis:
- `/rename` em vídeo legado: permitido, com aviso "Áudio deste vídeo expirou — você só verá os labels e seus tempos de fala". O reenvio final inclui apenas o `.md`.
- `/redo` em vídeo legado: rebaixa o áudio do zero, regerando todos os artefatos.

---

## I. Interação com o Telegram

### I.1 Modo de conexão
O bot usa **long polling** (não webhook), evitando a necessidade de portas expostas e HTTPS. Adequado para uso pessoal em máquina residencial atrás de NAT.

### I.2 Mensagens de progresso
O bot é **verboso**. Para cada job, uma única mensagem é enviada e **editada** ao longo das etapas (evita poluir o chat). Exemplo:

```
[1/7] Baixando metadados... ✓ "Título" (5min 30s, PT)
[2/7] Baixando faixa de áudio original... ✓ (12.4 MB)
[3/7] Convertendo para Opus/OGG 32 kbps... ✓ (1.2 MB)
[4/7] Verificando legendas... ✗ Não disponível — usando WhisperX
[5/7] Transcrevendo (modelo: small, device: cpu)... 50%... 75%... ✓
[6/7] Diarizando... ✓ 2 falantes
[7/7] Renderizando Markdown... ✓
✅ Pronto! Enviando arquivos...
```

Marcos de progresso dentro de etapas longas (transcrição): **10%, 25%, 50%, 75%, 90%**. Throttle: no máximo uma edição por segundo, conforme limite da Bot API.

### I.3 Linguagem das mensagens
Todas as mensagens do bot ao usuário são em **português brasileiro**.

### I.4 Limites e particionamento
- Mensagens de texto: limite Telegram de 4096 chars (não relevante para nosso fluxo, pois transcrições vão em arquivo).
- Upload: 50 MB. Vídeos > 3h são bloqueados (ver B.4); o particionamento descrito em C.2 cobre o caso raro de vídeos longos com fala muito densa.

### I.5 Sem PDF, sem resumo no chat
A entrega é **estritamente** o `.md` + o `.ogg` (e/ou múltiplos `.ogg` particionados). Sem versão PDF, sem resumo inline no chat.

---

## J. Comandos do bot

### J.1 Lista completa

| Comando | O que faz |
|---|---|
| `/start` | Boas-vindas e confirmação de que o bot está vivo. |
| `/help` | Lista todos os comandos com descrição curta. |
| `/status` | Mostra job em processamento (se houver) e tamanho atual da fila. |
| `/last` | Reenvia o último `.md` (e o `.ogg`, se ainda existir). |
| `/list` | Lista os últimos N jobs com `video_id`, título e status (artefatos disponíveis ou expirados). |
| `/redo <link>` | Solicita reprocessamento imediato de um link como novo job. Confirmação com diff de configuração permanece como evolução futura. |
| `/cancel` | Cancela o job em andamento ou interrompe um diálogo de `/rename`. |
| `/rename` | Inicia diálogo interativo para renomear os falantes do último vídeo processado. |
| `/clearcache` | Apaga os modelos do Whisper/pyannote baixados, liberando disco. |
| `/clearqueue` | Esvazia a fila pendente, sem cancelar o job em andamento. |
| `/lasterror` | Mostra o stack trace técnico do último erro ocorrido. |

### J.2 Confirmação no `/redo`
Na versão atual, `/redo <link>` executa imediatamente como novo job. A confirmação antes da execução, com diff de configuração entre a transcrição anterior e a corrente, permanece como evolução futura para reduzir o risco de reprocessamento involuntário de vídeos longos.

### J.3 `/cancel` — escopo
- Durante **processamento** (download, conversão, transcrição, diarização): aborta o subprocess apropriado, limpa arquivos parciais, marca job como `cancelled`.
- Durante **diálogo de `/rename`**: aborta o diálogo, sem alterar o `.md` original.
- **Sem nada em andamento**: responde "Nada a cancelar".
- Cancela apenas o job atual; para limpar a fila inteira existe `/clearqueue`.

### J.4 `/rename` — fluxo interativo
1. Usuário envia `/rename` (sem argumentos) → o bot opera sobre o último vídeo processado.
2. Se o áudio do vídeo expirou (vídeo legado), o bot avisa e pede confirmação para prosseguir sem áudio.
3. O bot inicia um diálogo: "Vídeo *<título>*. Renomear `SPEAKER_00` (apareceu primeiro, X% do tempo) para? (envie o nome ou /skip)" — repete para cada `SPEAKER_XX`.
4. Ao final, regenera o `.md` substituindo todos os labels pelas novas atribuições.
5. Se dois ou mais labels receberem o mesmo nome, o renderer trata isso como **mesclagem manual de falantes**: agrega o tempo no resumo da diarização e une blocos consecutivos no Markdown quando o nome exibido for o mesmo.
6. Atualiza o registro em `speakers` no SQLite.
7. Reenvia o `.md` (e o `.ogg`, se ainda existir).

`/cancel` durante o diálogo cancela sem aplicar.

### J.5 Reprocessamento por link repetido
Quando o usuário envia um link cujo `video_id` já existe no banco:
- Se a configuração corrente é **igual** à anterior: bot reenvia o `.md` (e `.ogg` se disponível) e pergunta "Reprocessar mesmo assim?" com botões `[Reprocessar]` `[Manter]`.
- Se a configuração mudou desde a última: bot mostra o diff e pergunta da mesma forma.


### J.6 Observabilidade operacional

`/healthcheck` deve funcionar como triagem operacional rápida. Ele não imprime segredos, mas reporta se os segredos mínimos existem, qual `.env` efetivo foi usado, se `.env.example` não entrou como runtime, se binários e módulos essenciais estão disponíveis, se diretórios e SQLite estão acessíveis, se há espaço em disco, se cookies configurados existem e se o backend de sumarização local responde com o modelo esperado.

`/lasterror` deve consolidar duas fontes:

1. jobs de transcrição marcados como `failed` no repositório principal;
2. erros operacionais derivados registrados em `data/logs/operational_errors.jsonl`, por exemplo falhas de `/summary`, `/export`, `/video_subs`, `/clearcache` e exceções defensivas no pipeline.

A saída deve conter operação, etapa, severidade, classe da exceção, mensagem sanitizada, contexto limitado, traceback final sanitizado quando disponível e sugestões de verificação. Tokens, cookies, API keys, cabeçalhos `Authorization` e valores de `.env` nunca devem ser exibidos.

---

## K. Erros e retentativas

### K.1 Falha no download (YouTube)
Bloqueios típicos: vídeo privado, removido, geo-restrito, idade-restrito sem cookies, members-only sem cookies, bot-detection (raríssimo em IP residencial).

Política: **avisar o erro específico e descartar o job**. Sem retentativa automática.

### K.2 Falha na transcrição
OOM, crash do CUDA, timeout, segfault de subprocess. Política descrita em D.3: limpa, retenta uma vez com modelo menor em CPU, notifica.

### K.3 Falha no envio pelo Telegram
Rede caiu, Telegram fora do ar, rate limit excedido. Política: **retentativa 5 vezes com backoff exponencial** (1s, 2s, 4s, 8s, 16s); após a última, desiste, marca o job como `delivery_failed` e loga.

### K.4 Reinício do bot durante processamento
Política mínima: jobs em `processing` não devem permanecer indefinidamente como ativos após reinício. Recuperação avançada, retomada seletiva e UX de reprocessamento assistido não fazem parte da prioridade principal atual; se necessárias, devem ser tratadas como evolução futura de baixa prioridade.

---

## L. Operação e observabilidade

### L.1 Logs por job
Cada job gera um arquivo de log próprio em `logs/<slug-do-titulo>.log`, contendo todas as etapas do processamento (download, conversão, transcrição, diarização, renderização, entrega) com timestamps e níveis (`INFO`, `WARNING`, `ERROR`). Formato **texto humano**, exemplo:

```
2026-05-01 14:32:01 [INFO] download.start url=https://...
2026-05-01 14:32:04 [INFO] download.metadata title="..." duration=330 lang=pt
2026-05-01 14:32:08 [INFO] download.audio bytes=12421344
2026-05-01 14:32:09 [INFO] convert.start codec=libopus bitrate=32k
...
```

Um log mínimo `logs/bot.log` adicional captura eventos de ciclo de vida do bot (startup, shutdown, erros gerais). Quando a política FIFO expira um job, o log correspondente é deletado junto.

### L.2 Reinício e jobs interrompidos
No startup, o bot deve evitar estados inconsistentes: jobs que estavam em execução antes da queda não podem permanecer indefinidamente como `processing`. A política mínima é marcar esses casos de forma diagnosticável e permitir reprocessamento explícito pelo usuário, quando aplicável.

Recuperação avançada após interrupção — isto é, retomar exatamente do ponto de falha, reaproveitar parcialmente artefatos intermediários ou oferecer UX interativa de retomada — foi removida da prioridade principal atual. O caminho operacional preferido é usar `/healthcheck`, `/lasterror`, logs sanitizados e reprocessamento explícito.

### L.3 Cache de modelos
Modelos do Whisper e pyannote são baixados **on-demand** na primeira execução que os requer. Cache em `models/` (configurável). O bot **avisa no chat** quando inicia e quando termina um download de modelo. O comando `/clearcache` apaga todos os modelos baixados.

### L.4 Validação de dependências de sistema
No startup, o bot valida que `ffmpeg` está instalado (chamando `ffmpeg -version`). Se ausente, **aborta** com mensagem clara e instrução por distro:
- Fedora: `sudo dnf install ffmpeg`
- Ubuntu/WSL: `sudo apt install ffmpeg`

### L.5 Modos de execução
1. **Manual**: `uv run python -m yt_transcriber_bot`
2. **Serviço systemd**: arquivo `yt-transcriber-bot.service` de exemplo é fornecido, com configuração para auto-start no boot e restart automático em crash.

Detalhes em [`04-manual-de-instalacao.md`](./04-manual-de-instalacao.md).

### L.6 Hibernação
Não há tratamento especial para hibernação da máquina. O `python-telegram-bot` reconecta automaticamente após o despertar; o PyTorch retoma a inferência sem perda de estado.

---

## M. Qualidade de código e testes

### M.1 Princípios
- **Extreme Programming**: ciclos curtos, refactor contínuo, código pertence ao time, testes contínuos.
- **Test-Driven Development purista**: ciclo Red-Green-Refactor por método, com **abordagem híbrida** apenas onde a integração externa é incontornável (rede, GPU, modelos grandes, API real do Telegram).
- **Programação Orientada a Objetos** rigorosa, com SOLID.
- **Padrões de projeto** explicitamente aplicados (ver [`02-arquitetura.md`](./02-arquitetura.md)).

### M.2 Cobertura
- **100%** de cobertura de linhas em código de domínio (entidades, services, pipeline, comandos).
- **≥ 80%** em adaptadores de I/O (algumas linhas de tratamento de erro só são alcançáveis em integração).
- Cada gate roda `pytest --cov` e falha se a cobertura cair abaixo da meta.

### M.3 Lint, format e type check
- **Format**: `ruff format` (PEP 8 + isort).
- **Lint**: `ruff check` com regras strict.
- **Type check**: `mypy --strict` em todo o código de produção.
- **Pre-commit hook** opcional para rodar tudo antes de cada commit.

### M.4 Política de "bug → novo teste de regressão"
Qualquer falha encontrada na avaliação de um gate **gera primeiro um teste que falha reproduzindo o bug**, e só depois o bug é corrigido. O teste de regressão fica permanentemente na suíte. Esta política impede o retorno do mesmo erro ao longo da evolução.

### M.5 Versionamento de dependências
Faixas semver no `pyproject.toml` (`whisperx>=3.8,<4.0`, `torch>=2.4,<3.0`, etc.); arquivo `uv.lock` versionado garante reprodutibilidade exata.

---

## N. Validação E2E

### N.1 Vídeo de referência
Toda a validação E2E usa o vídeo `https://www.youtube.com/watch?v=j2p8p7cg0q8` ("How to remember EVERYTHING you've ever read? With Eduardo Giannetti", canal *Amado Mundo*, 5min 30s, idioma original PT, 2 falantes, com auto-dub disponível). Características que validam todo o fluxo:
- Idioma PT na allowlist.
- Duração curta (5min 30s) para iterar rápido em CPU.
- Dois falantes claros, ideal para diarização.
- Auto-dub presente, validando a regra de baixar a faixa original.
- Caso o sandbox enfrente bloqueio do YouTube por IP de datacenter, **basta um clipe de 2 minutos** do vídeo para o teste — aceito pelo usuário.

### N.2 Divisão de responsabilidades no E2E
- **No sandbox de desenvolvimento**: pipeline interno completo (conversão → transcrição → diarização → renderização do MD), com download mockado caso o YouTube bloqueie. Telegram simulado por um *fake bot* que executa o pipeline diretamente.
- **No ambiente do usuário**: validação real do download do YouTube, da entrega via Telegram com seu token, e do uso da GPU Quadro T2000.

---

## O. Segurança e privacidade

- Segredos nunca em arquivos versionados (ver A.3).
- Tentativas de acesso de não-autorizados: descartadas silenciosamente, sem log (A.2).
- Cookies do YouTube tratados como segredo equivalente a senhas; nunca logados.
- Logs de transcrição contêm conteúdo do vídeo; não há vazamento por design (logs ficam apenas no disco local do usuário).

---

## Referência cruzada das 50 dúvidas originais

Para auditoria, abaixo o mapeamento entre cada dúvida original e a seção que materializa a decisão:

| Dúvida | Tema | Seção |
|---|---|---|
| 1 | SO suportado | (premissa de instalação) |
| 2 | Hardware (GPU, RAM) e diarização | D.2, E |
| 3 | Limite de duração, formato áudio, transcrição, progresso, fila | B.4, C, F, I.2, G.2 |
| 4 | Template MD, granularidade, falantes, idioma, nome arquivo | F |
| 5 | Estrutura pastas, retenção, reprocesso, renomeação, SQLite, comandos | H, J, G |
| 6 | Env vars, autorização, HF_TOKEN, logs | A.3, A.2, L.1 |
| 7 | Stack, padrões, TDD, Python, uv, gates | M, [02-arquitetura.md] |
| 8 | Forma de validação E2E | N |
| 9 | Limitações do sandbox | N.2 |
| 10 | `/rename` interativo via comando, não automático | J.4 |
| 11 | Erros: YT bloqueio, transcrição, Telegram | K |
| 12 | Auto-dub: faixa original + legendas existentes | B.2, B.3 |
| 13 | Bot-detection no sandbox: usar mocks/clipe | N.2 |
| 14 | `/rename` simples sem args, último MD | J.4 |
| 15 | Hierarquia de legendas: manual > auto > traduzida | B.3 |
| 16 | Legendas só no idioma original | B.3 |
| 17 | Rejeição de música/idioma fora | B.5 |
| 18 | Lives, shorts, playlists, members-only | B.1, B.6 |
| 19 | FIFO 5; MD legado preservado; link no cabeçalho | H.2, F.5 |
| 20 | Reinício: jobs `processing` → `failed`, fila persiste, retentativa | L.2 |
| 21 | Verbosidade: mensagem editada, marcos 10/25/50/75/90 | I.2 |
| 22 | `/cancel` cobre processamento e diálogo | J.3 |
| 23 | Detecção de mudança de config | J.5 |
| 24 | Extrair URL de mensagem livre | B.1 |
| 25 | Modelos on-demand + `/clearcache` | L.3 |
| 26 | Validação ffmpeg | L.4 |
| 27 | Cookies (browser ou file) | B.6 |
| 28 | MDs sem limite, FIFO só nos demais | H.2 |
| 29 | Rename em legado: permitido com aviso | H.5 |
| 30 | Sem hint de speakers; mitigar por nomes iguais | E.2 |
| 31 | Legenda traduzida = inválida | B.3 |
| 32 | Sem PDF, sem resumo no chat | I.5 |
| 33 | Reinício: notificar usuário | L.2 |
| 34 | Avisar download/conclusão de modelo | L.3 |
| 35 | Mocks com fixtures gravados | M.1 |
| 36 | 100% de cobertura no domínio | M.2 |
| 37 | `ruff` + `mypy --strict` | M.3 |
| 38 | Logs em texto humano simples | L.1 |
| 39 | Polling | I.1 |
| 40 | Limite Telegram, throttle de edição, particionamento | I.2, I.4, C.2 |
| 41 | Sem tratamento especial de hibernação | L.6 |
| 42 | Manual + systemd opcional | L.5 |
| 43 | Lista de 11 comandos confirmada | J.1 |
| 44 | Mensagens em português | I.3 |
| 45 | Faixas semver + `uv.lock` versionado | M.5 |
| 46 | Algoritmo de auto-detect de GPU | D.2 |
| 47 | E2E parcial no sandbox; final com o usuário | N.2 |
| 48 | Limite hard 3h | B.4 |
| 49 | `/rename` em legado: confirmação e reenvio só do MD | H.5, J.4 |
| 50 | `/redo` pede confirmação com diff | J.2 |
