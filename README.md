# YT Transcriber Bot

Bot privado do Telegram que recebe links do YouTube enviados por um único usuário autorizado, baixa o áudio na faixa original (ignorando dublagens automáticas), realiza transcrição com **WhisperX** e **diarização de falantes** (pyannote, com fallback nativo do WhisperX), e devolve no chat (i) um arquivo de áudio comprimido em Opus/OGG focado em voz e (ii) uma transcrição em Markdown estruturada por turnos de fala.

O projeto é construído sob os princípios de **Spec-Driven Development**, **Extreme Programming**, **Test-Driven Development** purista (com abordagem híbrida apenas onde a integração externa é incontornável), **Programação Orientada a Objetos** rigorosa e uso explícito de **padrões de projeto** (Hexagonal/Ports & Adapters, Strategy, Repository, Chain of Responsibility, Command, Observer, Factory). Tudo programado usando uma IA como assistente.

A entrega é particionada em **oito gates incrementais**, cada um com critérios de aceitação objetivos e uma suíte de testes obrigatórios; correções identificadas durante a avaliação de qualquer gate geram **novos testes de regressão** antes da correção propriamente dita, garantindo que o erro não retorne.

---

## Documentação

Toda a documentação detalhada está na pasta [`docs/`](./docs/):

| Documento | Conteúdo |
|---|---|
| [`docs/01-contrato-funcional.md`](./docs/01-contrato-funcional.md) | Contrato funcional completo: as 50 decisões tomadas em conjunto com o usuário, organizadas por área temática, com justificativa para cada uma. |
| [`docs/02-arquitetura.md`](./docs/02-arquitetura.md) | Arquitetura técnica: camadas, padrões de projeto aplicados, interfaces (ports), implementações (adapters), diagramas de fluxo, modelo de dados. |
| [`docs/03-manual-de-uso.md`](./docs/03-manual-de-uso.md) | Manual do usuário final: comandos do bot, fluxos de interação passo a passo, exemplos, troubleshooting do dia-a-dia. |
| [`docs/04-manual-de-instalacao.md`](./docs/04-manual-de-instalacao.md) | Instalação detalhada em Fedora nativo e Ubuntu via WSL2: dependências de sistema, ambiente Python com `uv`, variáveis de ambiente do usuário, cookies do YouTube, aceite dos termos do pyannote, execução manual e como serviço systemd. |
| [`docs/05-plano-de-execucao.md`](./docs/05-plano-de-execucao.md) | Plano de execução em 8 gates: escopo de cada gate, lista exaustiva de testes obrigatórios, critérios de aceitação, política de regressão, modelo de relatório de gate. |
| [`docs/06-funcionalidades-futuras.md`](./docs/06-funcionalidades-futuras.md) | Roadmap de funcionalidades postergadas conscientemente (tradução cross-language, identificação de falantes entre vídeos, exportação para outros formatos, etc.). |
| [`docs/07-glossario-e-decisoes.md`](./docs/07-glossario-e-decisoes.md) | Glossário técnico (WhisperX, pyannote, diarização, VAD, alinhamento, etc.) e Architecture Decision Records (ADRs) curtos para as decisões estruturantes. |

> **Antes de qualquer implementação**, este conjunto de documentos é o **contrato** que rege o desenvolvimento. Qualquer ambiguidade deve ser resolvida revisando-os; qualquer mudança de escopo deve ser refletida primeiro neles, depois no código e nos testes.

---

## Visão geral em uma página

### O que o bot faz

1. **Recebe** um link do YouTube enviado por mensagem privada no Telegram.
2. **Verifica** se o remetente é o usuário autorizado (caso contrário, ignora silenciosamente).
3. **Valida** o link (regex de URL do YouTube, normalização de `youtu.be` e parâmetros), enfileira o job.
4. **Baixa** os metadados do vídeo (`yt-dlp`), valida duração (≤ 3h), idioma original (em `pt` ou `en`) e detecta se há áudio falado significativo.
5. **Baixa** a faixa de áudio **original** (ignorando dublagens automáticas), avisando o usuário no chat.
6. **Converte** o áudio para Opus/OGG mono a 32 kbps (foco em inteligibilidade de voz, tamanho mínimo).
7. **Procura** legendas existentes no YouTube (manuais → auto-geradas → traduzidas):
   - Se houver legenda **manual no idioma original**: usa-a como transcrição e roda **apenas a diarização**.
   - Se houver apenas **legenda auto-gerada no idioma original**: usa-a também, marcando a origem no MD; reprocessamento manual pode ser solicitado com `/redo <link>`.
   - Caso contrário: roda **WhisperX completo** (transcrição + alinhamento por palavra + diarização).
8. **Diariza** com pyannote via WhisperX (primário) ou pyannote direto (fallback).
9. **Renderiza** um arquivo Markdown com cabeçalho de auditoria (URL, canal, duração, modelo usado, idioma, falantes) e a transcrição organizada em **turnos de fala** com timestamps.
10. **Envia** ao usuário, no chat, o arquivo `.ogg` comprimido e o arquivo `.md`, com mensagens de progresso editadas em tempo real (5 marcos: 10%, 25%, 50%, 75%, 90%).
11. **Persiste** o job no SQLite local. Aplica retenção FIFO de 5 jobs nas pastas de áudio e logs (os arquivos `.md` ficam **indefinidamente** como histórico, com link no cabeçalho para auditoria).
12. **Permite** renomear posteriormente os falantes (`SPEAKER_00 → "João"`) via diálogo interativo no comando `/rename`, regenerando e reenviando o `.md`.

### Restrições e premissas

- **Usuário único autorizado** (seu `user_id` numérico do Telegram), via variável de ambiente. Qualquer outro remetente é ignorado silenciosamente, sem log nem resposta.
- **Idiomas suportados**: português brasileiro (`pt`) e inglês (`en`). Outros idiomas são rejeitados com mensagem clara.
- **Duração máxima**: 3 horas (configurável). Acima de 1h, há um aviso (não bloqueio) sobre o tempo estimado de processamento.
- **Hardware**: auto-detecção GPU↔CPU. GPUs com Compute Capability < 6.0 (ex.: GeForce 940MX) são tratadas como CPU para evitar incompatibilidades. Em caso de OOM/erro durante a transcrição, retentativa automática com modelo menor em CPU.
- **Sem música/instrumental**: vídeos sem fala suficiente (detectado por VAD) são rejeitados.
- **Vídeos members-only**: aceitos quando configurados cookies de uma conta autenticada.
- **Lives ao vivo, idade-restritos sem cookies, vídeos privados/removidos**: rejeitados.

### Stack técnica

- **Linguagem**: Python 3.11
- **Gerenciador de ambiente**: [`uv`](https://docs.astral.sh/uv/)
- **Bot framework**: [`python-telegram-bot`](https://python-telegram-bot.org/) v21+ (assíncrono)
- **Download YouTube**: [`yt-dlp`](https://github.com/yt-dlp/yt-dlp)
- **Conversão de áudio**: `ffmpeg` (binário do sistema, codec `libopus`)
- **Transcrição**: [`whisperx`](https://github.com/m-bain/whisperX) (faster-whisper backend + alinhamento wav2vec2)
- **Diarização**: `whisperx.diarize.DiarizationPipeline` (primário) → `pyannote.audio` 3.1+ (fallback)
- **Persistência**: SQLite via SQLAlchemy 2.x (ORM)
- **Configuração**: `pydantic-settings` v2 com validação no startup
- **Logging**: `logging` stdlib + `RotatingFileHandler`, formato texto humano
- **Slugify**: `python-slugify` (trata acentos e Unicode)
- **Testes**: `pytest`, `pytest-asyncio`, `pytest-mock`, `pytest-cov`
- **Qualidade**: `ruff format`, `ruff check`, `mypy --strict`

### Padrões de projeto aplicados

- **Hexagonal / Ports & Adapters**: domínio puro no centro; adaptadores para Telegram, YouTube, ffmpeg, WhisperX, pyannote, SQLite.
- **Strategy**: `TranscriptionEngine`, `DiarizationEngine`, `StorageBackend` — todos intercambiáveis.
- **Repository**: `JobRepository` sobre SQLAlchemy, com implementação in-memory para testes.
- **Chain of Responsibility**: `Pipeline` é uma cadeia de `Stage`s (Download → Convert → Transcribe → Diarize → Render → Deliver), cada um testável isoladamente.
- **Command handlers**: cada comando do Telegram (`/rename`, `/redo`, etc.) é tratado por um handler explícito no adaptador.
- **Observer / Event Bus**: `Stage`s emitem eventos de progresso; `TelegramProgressReporter` os escuta e atualiza a mensagem no chat.
- **Factory**: `EngineFactory` cria a instância de `TranscriptionEngine` adequada ao hardware detectado.
- **SOLID** rigoroso em todas as classes.

---

## Status do projeto

Este pacote contém uma implementação funcional até o escopo de **Gate 6**, com correções adicionais aplicadas em 2026-05-01 para alinhar código, documentação e comandos expostos ao usuário.

| Área | Status atual |
|---|---|
| Bootstrap, domínio, configuração e persistência | Implementados |
| Download YouTube, conversão de áudio, transcrição, diarização e renderização Markdown | Implementados com adaptadores reais e testes com fakes/mocks |
| Telegram adapter | Implementado com fila sequencial, progresso, `/start`, `/help`, `/status`, `/cancel`, `/list`, `/last`, `/redo`, `/rename` e `/clearcache` |
| Retenção FIFO | Aplicada após job concluído; mantém Markdown/snapshots e remove artefatos voláteis antigos |
| Snapshots para `/rename` | Persistidos automaticamente junto com cada Markdown gerado |
| Validação E2E com YouTube/Telegram/modelos reais | Ainda requer execução em ambiente com dependências externas, tokens e `ffmpeg` |

Limitações atuais importantes:

- `/redo <link>` reprocessa imediatamente como um novo job. A confirmação inline com diff de configuração permanece como melhoria futura.
- `/rename` usa um mapeamento textual em lote, por exemplo `SPEAKER_00=João, SPEAKER_01=Maria`.
- Se a diarização dividir a mesma pessoa em múltiplos labels, atribua o mesmo nome a eles, por exemplo `SPEAKER_00=João, SPEAKER_02=João`; o Markdown será re-renderizado com esses falantes mesclados.
- `/last` reenvia o último Markdown disponível; o áudio continua sendo enviado ao final de um processamento novo.
- `/clearcache` só remove arquivos se o diretório informado for exatamente o `models_dir` configurado, para evitar apagamento acidental de diretórios amplos.

---

## Como começar (após implementação concluída)

> Esta seção será expandida em [`docs/04-manual-de-instalacao.md`](./docs/04-manual-de-instalacao.md). Resumo aqui apenas para visão geral.

```bash
# 1. Clonar e entrar
git clone <repo>
cd yt-transcriber-bot

# 2. Instalar uv (uma vez)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Criar ambiente e instalar deps
#    Inclui torch, WhisperX e pyannote.audio; o download pode ser grande.
uv sync

# 4. Instalar dependências de sistema
sudo dnf install ffmpeg          # Fedora
sudo apt install ffmpeg          # Ubuntu/WSL

# 5. Configurar variáveis de ambiente do usuário
#    (instruções detalhadas em docs/04-manual-de-instalacao.md)
export TELEGRAM_BOT_TOKEN="123456:ABC..."
export TELEGRAM_ALLOWED_USER_ID="123456789"
export HF_TOKEN="hf_..."

# 6. Aceitar termos do pyannote (uma vez, pelo navegador)
#    Versões atuais de WhisperX/pyannote.audio usam community-1:
#    https://huggingface.co/pyannote/speaker-diarization-community-1
#    Em ambientes antigos, também pode ser necessário aceitar:
#    https://huggingface.co/pyannote/speaker-diarization-3.1
#    https://huggingface.co/pyannote/segmentation-3.0

# 7. Rodar
uv run python -m yt_transcriber_bot
```

---

## Segurança e pre-commit

O projeto inclui proteção local contra vazamento acidental de tokens, cookies, bancos, logs e arquivos de runtime.

Configuração recomendada:

```bash
cp .env.example .env
uv sync --dev
uv run pre-commit install
uv run pre-commit run --all-files
```

Os hooks locais bloqueiam `.env`, cookies do YouTube, bancos SQLite, logs e padrões comuns de tokens. Se `gitleaks` estiver instalado no sistema, ele roda como camada complementar; se não estiver, o hook avisa e continua.

Veja detalhes em `docs/08-seguranca-e-segredos.md`.


## Licença

A definir pelo proprietário do projeto.


## Política de modelo Whisper por idioma

Por padrão, o bot usa `WHISPER_MODEL=auto`. Nesse modo, ele seleciona o modelo de transcrição a partir do idioma original do vídeo:

```env
WHISPER_MODEL=auto
WHISPER_MODEL_PT=large-v3
WHISPER_MODEL_EN=medium
WHISPER_MODEL_DEFAULT=medium
```

Use `WHISPER_MODEL=small`, `medium` ou `large-v3` apenas quando quiser forçar um modelo para todos os idiomas.

Para português técnico ou fala rápida, `large-v3` tende a ser uma escolha mais segura, embora mais lenta e pesada. Para inglês, `medium` costuma oferecer bom equilíbrio entre qualidade e custo.

### Idioma explícito por vídeo

Além de enviar um link diretamente, você pode informar o idioma do vídeo:

```text
https://www.youtube.com/watch?v=... --lang pt
/pt https://www.youtube.com/watch?v=...
/en https://www.youtube.com/watch?v=...
/redo https://www.youtube.com/watch?v=... --lang pt
```

Isso é recomendado para português quando `WHISPER_MODEL=auto`, especialmente se `WHISPER_MODEL_PT` estiver configurado para um modelo especializado como `inesc-id/WhisperLv3-X-PT-All`.
