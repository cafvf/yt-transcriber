# Glossário e Decisões de Arquitetura

Este documento contém duas partes complementares:
- **Parte I** — um **glossário** de termos técnicos usados ao longo da documentação, para que qualquer leitor (mesmo sem familiaridade com áudio/ML) possa se situar.
- **Parte II** — **Architecture Decision Records (ADRs)**: registros curtos das decisões estruturantes do projeto, no formato canônico (contexto + decisão + consequências). ADRs servem para que, no futuro, ninguém se pergunte *"por que isso foi feito assim?"* sem encontrar a resposta.

---

# Parte I — Glossário

### ASR (Automatic Speech Recognition)
Reconhecimento Automático de Fala. A tarefa de transformar áudio falado em texto. Whisper, Vosk, DeepSpeech são exemplos de sistemas de ASR.

### Auto-dubbing (do YouTube)
Funcionalidade do YouTube que gera automaticamente faixas de áudio em outros idiomas para um vídeo, usando síntese de voz de IA. Os vídeos rotulados como "Auto-dubbed" possuem múltiplas faixas selecionáveis pelo espectador. Por preservação de fidelidade vocal, este bot **sempre** baixa a faixa **original** (a do criador), nunca uma versão dublada.

### Bot API (Telegram)
Interface oficial do Telegram para bots: documentação em https://core.telegram.org/bots/api. Limita uploads a 50 MB e impõe rate limits de mensagens.

### Chain of Responsibility
Padrão de projeto comportamental: uma cadeia de objetos processa uma requisição em sequência, cada um decidindo passar adiante ou tratar. No nosso pipeline, cada `Stage` é um elo que recebe o `PipelineContext`, opera nele, e o repassa.

### Compute Capability (CC)
Versão da arquitetura de uma GPU NVIDIA. Determina quais operações CUDA são suportadas. CC 5.0 = Maxwell (2014), CC 6.0 = Pascal (2016), CC 7.5 = Turing (2018), CC 8.0 = Ampere (2020), CC 9.0 = Hopper (2022). PyTorch recente requer CC ≥ 6.0 para suporte oficial. O bot exclui GPUs com CC abaixo deste limite via `MIN_GPU_COMPUTE_CAPABILITY`.

### Compute Type
Precisão numérica usada na inferência: `float32` (máxima qualidade, máxima memória), `float16` (metade da memória, GPUs modernas), `int8_float16` (mistura, quantização parcial), `int8` (mínima memória, mais rápido em CPU). O `whisperx`/`faster-whisper` quantiza pesos para acelerar.

### CTranslate2
Engine de inferência otimizada usada por baixo de `faster-whisper`. Implementa quantização INT8 e batching eficiente.

### Diarização (Speaker Diarization)
Tarefa de **"quem falou quando?"**: dividir um áudio com múltiplas pessoas falando em segmentos rotulados por falante (`SPEAKER_00`, `SPEAKER_01`, etc.), sem identificá-los nominalmente. Diferente do **speaker recognition**, que identifica quem é a pessoa.

### Embedding (de voz)
Vetor numérico de dimensão fixa (ex.: 192 ou 256) que representa as características vocais de um trecho de fala. Vozes parecidas ficam próximas no espaço vetorial. Usado pelo pyannote para agrupar segmentos no mesmo falante.

### faster-whisper
Reimplementação otimizada do Whisper da OpenAI usando CTranslate2 como backend de inferência. ~4x mais rápido que o Whisper original em GPU, ~7x em CPU. WhisperX usa faster-whisper por baixo.

### FIFO (First In, First Out)
Política de fila/retenção: o primeiro item a entrar é o primeiro a sair. Aplicada no projeto para limitar artefatos de áudio/log a 5 jobs por pasta.

### Gate
Marco de entrega no plano de execução. Cada gate tem escopo, testes obrigatórios, critérios de aceitação, e exige aprovação do usuário antes do próximo iniciar.

### Hexagonal Architecture (Ports & Adapters)
Padrão arquitetural que separa o domínio (regras de negócio puras) das tecnologias externas (UI, banco, APIs). O domínio define interfaces (`Port`s); implementações concretas (`Adapter`s) vivem fora. Maximiza testabilidade.

### HF_TOKEN (Hugging Face Token)
Token de acesso à API do Hugging Face. Necessário para baixar modelos com termos de uso (caso do pyannote). Obtido em https://huggingface.co/settings/tokens.

### Long polling
Técnica de comunicação onde o cliente faz uma requisição HTTP e o servidor segura a resposta até ter algo para enviar. Usada pelo `python-telegram-bot` em modo polling para receber updates sem precisar expor um webhook.

### Markdown (MD)
Linguagem de marcação leve usada como formato da transcrição final. Nossa escolha porque é texto puro, legível em qualquer editor, e renderizado bem por clientes Telegram modernos e ferramentas de notas (Obsidian, Notion, etc.).

### Opus
Codec de áudio livre, otimizado para voz e música em internet. Em bitrates baixos (~32 kbps) entrega excelente inteligibilidade de voz. Usado em WebRTC, Discord, e (no nosso caso) na entrega do áudio comprimido.

### OOM (Out Of Memory)
Erro quando o processo tenta alocar mais memória (RAM ou VRAM) do que está disponível. Comum em GPUs pequenas com modelos grandes. O bot trata via retentativa com modelo menor em CPU.

### pyannote.audio
Biblioteca Python especializada em **diarização** e tarefas relacionadas (VAD, segmentação, speaker embeddings). Mantida pelo Hervé Bredin (CNRS/IRIT). Atualmente na versão 3.1+. É a tecnologia subjacente da diarização do WhisperX.

### Repository Pattern
Padrão de projeto: abstrai a persistência de uma agregação de domínio. O domínio fala com uma interface (`JobRepository`); implementações concretas (`SqliteJobRepository`, `InMemoryJobRepository`) vivem fora.

### slug
Versão sanitizada de um título para uso em nome de arquivo ou URL: lowercase, sem acentos, sem caracteres especiais, espaços por hífens. Ex.: `"Não vou! 🎉"` → `nao-vou`.

### SOLID
Acrônimo dos cinco princípios da OO segundo Robert C. Martin: **S**ingle Responsibility, **O**pen/Closed, **L**iskov Substitution, **I**nterface Segregation, **D**ependency Inversion.

### SPEAKER_XX
Convenção de label para falantes anônimos produzida pelo pyannote, numerada por ordem de aparição. Renomeável posteriormente via comando `/rename`.

### Specification Pattern
Padrão de projeto: encapsula regras de validação como objetos compostáveis. `UrlIsYoutube() & DurationWithinLimit(180)` é uma especificação composta.

### Strategy Pattern
Padrão de projeto: define uma família de algoritmos intercambiáveis. Usado para `TranscriptionEngine`, `DiarizationEngine`, etc.

### TDD (Test-Driven Development)
Ciclo Red-Green-Refactor: escreve teste falhando, escreve mínimo de código para passar, refatora. **Purista** significa aplicar isso em cada método; **híbrido**, no nosso caso, significa relaxar para integrações externas onde mock detalhado seria mais frágil que o teste real.

### Turn (turno de fala)
Sequência contígua de fala de um único falante até a próxima troca. A diarização produz turnos; o MD organiza a transcrição por turnos.

### VAD (Voice Activity Detection)
Detecção de Atividade de Voz. Identifica em um áudio quais segmentos contêm fala humana e quais são silêncio/música/ruído. Usado pelo WhisperX para evitar alucinações em silêncio e pelo bot para rejeitar vídeos com pouca fala.

### Value Object
Objeto que representa um valor (não tem identidade própria), imutável. `VideoId`, `Slug`, `Duration` no nosso domínio.

### VRAM
Memória da GPU. Recurso escasso em GPUs antigas. Modelos do Whisper têm requisitos de VRAM explícitos: `tiny` 1 GB, `base` 1 GB, `small` 2 GB, `medium` 5 GB, `large-v3` 10 GB.

### wav2vec2
Arquitetura de modelo da Meta AI para representação de fala. WhisperX usa modelos wav2vec2 fine-tuned por idioma para fazer **alinhamento forçado** (forced alignment) — produzir timestamps por palavra a partir do texto de saída do Whisper.

### WhisperX
Projeto que estende o Whisper original com:
- Backend `faster-whisper` (mais rápido).
- Alinhamento por palavra via wav2vec2.
- Diarização integrada via pyannote.
- Pré-processamento com VAD para reduzir alucinações.

Repositório: https://github.com/m-bain/whisperX. Versão atual no momento da especificação: **3.8.5** (abril/2026).

### yt-dlp
Fork mantido do `youtube-dl`, ferramenta de linha de comando para baixar vídeos do YouTube e centenas de outros sites. Atualizado frequentemente para acompanhar mudanças do YouTube.

---

# Parte II — Architecture Decision Records

ADRs documentam **por que** uma decisão foi tomada, não apenas **qual** decisão. Cada um é deliberadamente curto.

---

## ADR-001 — Hexagonal/Ports & Adapters como espinha dorsal

**Contexto.** O sistema integra com Telegram, YouTube, ffmpeg, WhisperX, pyannote, SQLite e (potencialmente) outros adapters no futuro. Cada um traz suas próprias APIs, idiossincrasias e instabilidades. O usuário exigiu TDD purista.

**Decisão.** Adotamos arquitetura Hexagonal (Ports & Adapters), com domínio puro no centro e adapters concretos isolados nas bordas.

**Consequências.**
- (+) Testabilidade máxima: domínio testável sem rede, disco ou GPU.
- (+) Trocar uma tecnologia (ex.: Telegram → Discord) afeta apenas um adapter.
- (+) Padrão Strategy se aplica naturalmente para engines intercambiáveis.
- (−) Mais arquivos e mais classes do que uma abordagem procedural.
- (−) Curva de aprendizado para quem nunca viu o padrão.

---

## ADR-002 — Single user, autorização silenciosa

**Contexto.** O bot é privado. Qualquer outro `user_id` que tente interagir é um intruso ou um engano.

**Decisão.** Mensagens de não-autorizados são **silenciosamente descartadas**, sem responder, sem logar.

**Consequências.**
- (+) Não revela a existência do bot a terceiros.
- (+) Zero ruído nos logs.
- (−) Se você esquecer seu `user_id` correto e usar uma conta nova, vai parecer que o bot não está respondendo.

---

## ADR-003 — Segredos como variáveis de ambiente do usuário, configuração não-sensível em `.env`

**Contexto.** Tokens (Telegram, Hugging Face) e identidade (`user_id`) não devem ser versionados nem confundidos com configuração de comportamento.

**Decisão.** Segredos vivem em `~/.bashrc` (ou `/etc/yt-transcriber-bot/env` para systemd). Configurações comportamentais (modelo Whisper, bitrate, etc.) podem ficar em `.env` opcional na raiz do projeto.

**Consequências.**
- (+) Segredos nunca acidentalmente commitados.
- (+) Princípio do menor privilégio: o `.env` pode ser revisado sem expor tokens.
- (−) Configuração de systemd exige duplicar segredos em `/etc/yt-transcriber-bot/env`.

---

## ADR-004 — Sem limite genérico de duração; limite hard de 3h por requisito do usuário

**Contexto.** Usuário inicialmente pediu "sem limite de duração". Após análise, concordou em limitar a 3h para evitar casos extremos.

**Decisão.** `MAX_VIDEO_DURATION_MIN=180` (configurável). Aviso (não bloqueio) acima de 60min.

**Consequências.**
- (+) Protege contra acidentes (vídeos de 8h, p.ex.).
- (+) Mensagem de aviso prepara o usuário para esperas longas.
- (−) Se quiser transcrever uma palestra de 4h, precisa subir a env e reiniciar.

---

## ADR-005 — WhisperX para diarização (primário) com pyannote direto como fallback

**Contexto.** O usuário questionou se WhisperX faz diarização própria. Pesquisa mostrou que **não**: o WhisperX expõe `whisperx.diarize.DiarizationPipeline`, mas internamente carrega modelos pyannote. Existem duas formas de usar pyannote: pelo wrapper do WhisperX ou direto via `pyannote.audio.Pipeline`.

**Decisão.** Usar o wrapper do WhisperX como **primário** (caminho oficial recomendado pela documentação) e cair para `pyannote.audio.Pipeline` direto como **fallback** automático em caso de exceção do primário (mudança de API interna, bug de versão, falha de download do modelo via wrapper).

**Consequências.**
- (+) Caminho recomendado/atual usado por padrão.
- (+) Robustez contra evoluções do WhisperX (se quebrar o wrapper, o fallback assume).
- (+) Strategy pattern (`DiarizationEngine`) permite adicionar futuros engines (NVIDIA NeMo, etc.) sem refactor.
- (−) Manutenção de dois caminhos de código.

---

## ADR-006 — Auto-detecção de hardware com fallback para CPU em GPUs antigas

**Contexto.** Usuário tem GPUs heterogêneas (Quadro T2000 OK, GeForce 940MX problemática). PyTorch recente (2.4+) tem suporte oficialmente removido para Compute Capability < 6.0 (Maxwell e anteriores).

**Decisão.** Algoritmo `EngineFactory` detecta GPU; se CC < `MIN_GPU_COMPUTE_CAPABILITY` (default 6.0) **ou** VRAM insuficiente para o modelo configurado, cai para CPU. Configurável via env.

**Consequências.**
- (+) Mesma codebase roda otimizado em hardware diverso.
- (+) Atualidade dos módulos preservada (não precisamos fixar PyTorch antigo para suportar GPUs antigas).
- (−) Algoritmo precisa ser revisitado quando novas GPUs/arquiteturas surgirem.

---

## ADR-007 — Opus/OGG mono 32 kbps como formato de áudio entregue

**Contexto.** Telegram Bot API limita uploads a 50 MB. Áudios de voz humana são plenamente inteligíveis em bitrates baixos com Opus. Usuário pediu "foco em voz".

**Decisão.** Convertemos para Opus em container OGG, mono, 32 kbps. Bitrate configurável.

**Consequências.**
- (+) Arquivos pequenos (~14 MB/h) sempre cabem no limite Telegram.
- (+) Inteligibilidade excelente para voz; música seria pobre, mas rejeitamos vídeos majoritariamente musicais.
- (−) Não serve como "arquivo de qualidade" para edição de áudio (não era o objetivo).

---

## ADR-008 — `.md` como único formato de transcrição, sem PDF nem resumo no chat

**Contexto.** Usuário pediu explicitamente entrega como `.md`, sem PDF, sem resumo inline no chat.

**Decisão.** A transcrição final é **um único arquivo `.md`** com cabeçalho de auditoria e turnos de fala. Sem variantes.

**Consequências.**
- (+) Simplicidade absoluta.
- (+) MDs são tiny (KBs), preserváveis indefinidamente como histórico.
- (−) Quem precisar de PDF terá de converter externamente (pandoc, weasyprint).

---

## ADR-009 — Retenção FIFO de 5 jobs em áudios/logs, MDs preservados indefinidamente

**Contexto.** Áudios brutos (do download) e processados ocupam dezenas de MB cada. Logs são pequenos mas crescem. MDs são minúsculos.

**Decisão.** FIFO de 5 jobs em `downloads/`, `processed/` e logs associados.
Markdown e snapshots de segmentos são preservados para histórico e edição. O
Markdown contém link/ID apenas quando a origem é YouTube; mídia Telegram é
privada e não recebe identidade sintética.

**Consequências.**
- (+) Disco controlado nos artefatos pesados.
- (+) Histórico textual preservado indefinidamente.
- (+) Auditoria sempre possível pelo link no MD.
- (−) Se o vídeo for removido do YouTube, perde-se o áudio para sempre (mas o texto permanece).

---

## ADR-010 — TDD purista (com pequeno hibridismo para integrações inevitáveis)

**Contexto.** Usuário exigiu TDD; questão era "purista ou pragmático?". Escolhemos purista, com exceção declarada para integrações externas.

**Decisão.** Domínio e use cases: TDD purista 100%. Adapters: testes unitários com mocks (purista) **mais** testes de integração marcados (`@pytest.mark.integration`) que rodam com dependências reais. E2E (`@pytest.mark.e2e`) com vídeo real no Gate 7.

**Consequências.**
- (+) Cobertura efetiva e profunda do código.
- (+) Testes rápidos no ciclo de dev (só unitários).
- (+) Integração validada quando necessário.
- (−) Mais esforço de fixturização.

---

## ADR-011 — uv como gerenciador de ambiente

**Contexto.** Python 3.11 + ferramentas modernas. Opções: pip puro, poetry, uv.

**Decisão.** uv. É rápido, suporta `pyproject.toml` nativamente, gera `uv.lock` reproduzível, e é o mais novo padrão da comunidade.

**Consequências.**
- (+) Setup do dev em segundos (vs minutos com pip).
- (+) Lockfile automático e reproduzível.
- (−) Tecnologia recente; menos documentação que pip/poetry.

---

## ADR-012 — Polling, não webhook

**Contexto.** O bot roda em máquina residencial atrás de NAT. Webhook exigiria HTTPS público.

**Decisão.** `python-telegram-bot` em modo long polling.

**Consequências.**
- (+) Funciona em qualquer rede sem configuração de firewall.
- (+) Sem necessidade de HTTPS, certificados, IP estático.
- (−) Latência marginalmente maior (irrelevante na prática).

---

## ADR-013 — SQLite + SQLAlchemy 2.x

**Contexto.** Persistência simples para um único usuário, sem necessidade de servidor de DB.

**Decisão.** SQLite arquivo local (`data/jobs.db`) acessado via SQLAlchemy 2.x ORM.

**Consequências.**
- (+) Zero infraestrutura: instala junto com Python.
- (+) ORM facilita testes (in-memory SQLite nos unit tests via `:memory:`).
- (+) Suficiente para qualquer escala razoável de uso pessoal.
- (−) Não escala para multi-usuário (não é objetivo).

---

## ADR-014 — Fila sequencial single-threaded

**Contexto.** Usuário único. WhisperX/pyannote consomem GPU/RAM significativos; concorrência traria contenção.

**Decisão.** Um `SequentialQueueWorker` consome a fila um job de cada vez.

**Consequências.**
- (+) Zero risco de race condition (filesystem, GPU, modelos em memória).
- (+) Implementação trivial e robusta.
- (−) Vídeos esperam na fila — aceitável dado o uso pessoal.

---

## ADR-015 — Renomeação de falantes escopada ao vídeo (sem cross-video)

**Contexto.** Reconhecer "o mesmo falante" entre vídeos diferentes exige speaker embeddings persistidos e matching por threshold, com risco real de falsos positivos.

**Decisão.** `/rename` afeta **apenas** o vídeo corrente. Identificação cross-video fica em [`06-funcionalidades-futuras.md`](./06-funcionalidades-futuras.md).

**Consequências.**
- (+) Comportamento previsível, sem surpresas.
- (+) UX simples.
- (−) Em cenários de muitos vídeos com mesmas pessoas, mais trabalho manual.

---

## ADR-016 — `/redo` atual imediato; confirmação planejada

**Contexto.** Reprocessar um vídeo longo gasta minutos de GPU/CPU.

**Decisão atual.** `/redo <link>` reprocessa imediatamente como novo job e não
sobrescreve o job anterior. A deduplicação bloqueia apenas duplicatas do mesmo
vídeo+idioma que ainda estejam em processamento ou na fila.

**Decisão planejada.** Uma evolução futura deve apresentar confirmação inline
com diff de configuração e botões `[Confirmar]` `[Cancelar]`, inclusive quando o
usuário invocar `/redo` explicitamente.

**Consequências.**
- (+) O comportamento atual é simples e explícito para reprocessar.
- (−) Ainda não protege contra `/redo` acidental em vídeos longos.
- (−) Ainda não informa diferenças de configuração antes de gastar CPU/GPU.

---

## ADR-017 — Verbosidade via mensagem editada com 5 marcos fixos

**Contexto.** Usuário pediu bot verboso, mas com cuidado: rate limit do Telegram (~1 edição/seg) e poluição visual.

**Decisão.** Uma única mensagem por job, editada ao longo das etapas. Marcos de progresso intra-etapa: 10%, 25%, 50%, 75%, 90%. Throttle de 1s mínimo entre edições.

**Consequências.**
- (+) Chat limpo (uma mensagem cresce, não enche).
- (+) Visibilidade total do progresso.
- (+) Sem risco de rate limit.
- (−) Histórico não preserva os passos intermediários (só o estado final).

---

## ADR-018 — `manus-config` / connectors NÃO são usados neste projeto

**Contexto.** Manus oferece sistema de connectors para integrações externas. Para um bot Python local, não há benefício em usá-los.

**Decisão.** Nenhuma integração via Manus connectors. Todas as integrações (Telegram, YouTube, Hugging Face) são via bibliotecas Python convencionais executando localmente na máquina do usuário.

**Consequências.**
- (+) Independência total de Manus em runtime.
- (+) Funciona em qualquer máquina sem dependência de serviço externo.


---

## ADR-019 — Observabilidade operacional via `/healthcheck` e `/lasterror`

**Contexto.** Durante a estabilização de sumarização local com LM Studio, os erros mais custosos não estavam no algoritmo de transcrição, mas na operação: `.env` incorreto, modelo divergente, servidor LM Studio desligado, timeouts, tokenizer indisponível e falhas de rede do Telegram. Depender apenas de logs completos do terminal tornava a depuração lenta e propensa a vazamento acidental de segredos.

**Decisão.** O bot expõe dois comandos de observabilidade para o usuário autorizado:

- `/healthcheck`, para triagem ativa de configuração, dependências, diretórios, SQLite, cookies, LM Studio, modelo configurado, tokenizer/orçamento de sumarização e espaço em disco;
- `/lasterror`, para recuperar o último erro operacional sanitizado, combinando jobs `failed`, jobs `delivery_failed` e erros derivados persistidos em `data/logs/operational_errors.jsonl`, incluindo falha de entrega registrada como `transcribe_delivery`.

Erros derivados de comandos como `/summary`, `/export`, `/video_subs` e `/clearcache` não devem transformar automaticamente uma transcrição concluída em job `failed`; eles são registrados como eventos operacionais separados.

**Consequências.**

- (+) Diagnóstico rápido direto no Telegram, sem copiar tracebacks longos.
- (+) Menor risco de expor tokens, cookies ou `.env` ao pedir suporte.
- (+) Falhas de artefatos derivados ficam rastreáveis sem corromper o estado do job original.
- (+) `/healthcheck` vira checklist operacional antes de tarefas longas.
- (−) Falhas catastróficas antes da inicialização completa ainda dependem de logs externos.
- (−) O arquivo JSONL de erros precisa de política futura de retenção se crescer demais.


## ADR-020 — Priorização pós-observabilidade

**Contexto.** Após a estabilização de `/healthcheck` e `/lasterror`, o projeto passou a ter melhor diagnóstico operacional. A discussão de produto indicou que estatísticas operacionais e retomada seletiva avançada no meio de um job não são dores funcionais imediatas. Por outro lado, busca em transcrições, exportação de texto limpo, entrada por áudio e suporte multilíngue ampliam diretamente a utilidade do bot no fluxo de pesquisa e estudo.

**Decisão.** O roadmap funcional passa a priorizar, nesta ordem: `/search <texto>` com arquitetura preparada para busca semântica, `/text [n]`, upload de áudio pelo Telegram, backend ASR multilíngue, `/translate`, melhorias no `/redo` e, por fim, integração com Obsidian/Notion. `/stats` permanece fora da prioridade principal.

Para a trilha de produção, a recuperação de `pending` e a reconciliação mínima
após restart foram tratadas como hardening técnico separado do gate funcional.
Retomada seletiva dentro de ASR/diarização continua sendo evolução posterior.

**Consequências.**

- (+) O próximo desenvolvimento foca no reaproveitamento dos artefatos já gerados.
- (+) A tradução fica dependente de suporte ASR multilíngue mais sólido, reduzindo retrabalho.
- (+) A integração com Obsidian/Notion será mais rica quando já houver busca, texto limpo, eventual tradução e melhor cobertura de idiomas.
- (−) Métricas operacionais agregadas e retomada seletiva de progresso interno não serão tratadas no curto prazo.

---

## ADR-021 — Busca textual privada com FTS5 opcional

**Contexto.** O histórico local contém transcrições e resumos úteis, mas `/list`
não permite recuperar conteúdo por tema. A disponibilidade de FTS5 varia entre
builds locais de SQLite e os artefatos permanecem dados privados.

**Decisão.** `/search <texto>` consulta somente jobs `completed` do usuário
autorizado, em metadados e documentos derivados de transcrições/snapshots e
resumos. O adapter de persistência usa FTS5 quando a capacidade está disponível;
quando não estiver — ou se uma operação FTS recuperável falhar — aplica fallback
compatível limitado com o mesmo contrato de resultado. Cada resposta inclui
índice histórico, título, `video_id`, data e trecho sanitizado. O documento
derivado é atualizado após transcrição, `/rename` e `/summary` e não substitui
os artefatos literais.

**Consequências.**

- (+) Consulta útil sem nova dependência nem requisito de FTS5 no startup.
- (+) Isolamento por usuário e sanitização preservam a política privada.
- (+) Índices podem ser reconstruídos/backfilled sem migração destrutiva.
- (−) Fallback tem limites e pode oferecer ranking menos sofisticado.
- (−) Busca vetorial/semântica continua uma evolução separada.
