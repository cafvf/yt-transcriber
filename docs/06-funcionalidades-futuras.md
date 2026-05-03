# Funcionalidades Futuras

Este documento registra **funcionalidades conscientemente postergadas** durante a fase de levantamento de requisitos. Cada item foi discutido e decidido fora do escopo do MVP por razões objetivas (complexidade desproporcional ao benefício atual, dependência de pesquisa adicional, ou prioridade de entrega). O propósito do documento é dar **memória institucional**: caso o projeto evolua, há um inventário pronto de melhorias.

A presença de um item aqui **não** implica compromisso de implementação. Cada item está marcado com prioridade subjetiva (`alta`, `média`, `baixa`) e estimativa grosseira de esforço (`pequeno`, `médio`, `grande`).

---

## A. Idiomas e tradução

### A.1 Suporte a idiomas adicionais (`média`, `pequeno`)
Hoje a allowlist é `pt,en`. Adicionar `es`, `fr`, `it`, etc. é trivial: basta:
- Atualizar o default de `LANGUAGE_ALLOWLIST` ou permitir overrides via env.
- Garantir que os modelos de alinhamento wav2vec2 do WhisperX estejam disponíveis para o idioma adicionado (a maioria dos idiomas com volume razoável de dados está coberta).
- Adicionar testes de transcrição com fixtures no novo idioma.

**Por que ficou de fora**: o usuário declarou que só consome conteúdo em PT e EN.

### A.2 Tradução automática da transcrição (`alta`, `médio`) — **solicitado**
Além de resumir a transcrição e de gerar uma nota derivada para Obsidian/leitura, o bot deve poder **traduzir o conteúdo transcrito** para outro idioma, preservando a transcrição original como fonte da verdade.

**Casos de uso previstos**:
- Traduzir a transcrição literal completa.
- Traduzir a versão limpa/paragraphizada.
- Traduzir a nota de estudo derivada, quando a feature de resumo/análise estiver implementada.
- Gerar arquivos bilíngues para estudo: original + tradução lado a lado ou em seções separadas.

**Comandos possíveis**:
- `/translate en` → traduz o último job para inglês.
- `/translate pt <video_id>` → traduz um job específico para português.
- `/translate en --source literal` → traduz a transcrição literal.
- `/translate en --source clean` → traduz a versão limpa.
- `/translate en --source note` → traduz a nota de estudo/resumo, quando existir.
- `/translate en --bilingual` → gera Markdown com texto original e tradução.

**Saídas previstas**:
- `transcricao-traduzida.<lang>.md`
- `transcricao-bilingue.<source>-<target>.md`
- futuramente, `.srt`/`.vtt` traduzidos para legendagem.

**Estratégia técnica**:
- Criar uma porta `Translator` no domínio/aplicação, com adapters intercambiáveis.
- Implementações possíveis:
  - `ArgosTranslateAdapter` para tradução offline/local;
  - `LibreTranslateAdapter` para servidor local/self-hosted;
  - `OpenAIChatTranslator` ou adapter compatível com LLM local/API, com prompts controlados;
  - adapter para modelos Hugging Face, se fizer sentido operacional.
- Traduzir por blocos/segmentos, não o arquivo inteiro de uma vez, para preservar timestamps e evitar estouro de contexto.
- Manter IDs de segmento, timestamps e falantes estáveis. Apenas o campo `text` é traduzido.
- Persistir a tradução como artefato derivado, nunca substituindo o original.

**Requisitos de qualidade**:
- Preservar termos técnicos quando a tradução literal for pior que manter o termo original, por exemplo `Spec-Driven Development`, `LLM`, `pull request`, `task`, `context engineering`.
- Permitir glossário opcional por projeto/usuário.
- Preservar links, timestamps, nomes próprios, nomes de arquivos e comandos.
- Marcar explicitamente que a tradução é derivada e pode conter erros.
- Para legendas traduzidas, respeitar limites de comprimento por linha e duração mínima/máxima de cada cue.

**Integração com resumo e Obsidian**:
- A tradução deve poder ocorrer antes ou depois do resumo:
  - `transcrever → traduzir → resumir` é útil quando o resumo final deve ser no idioma-alvo;
  - `transcrever → resumir → traduzir` é mais barato, mas pode perder nuances.
- Para notas Obsidian, gerar frontmatter indicando:
  - idioma original;
  - idioma da tradução;
  - engine usada;
  - se o arquivo é literal, limpo, resumo ou nota derivada.

**Prioridade sugerida**: alta, pois amplia muito o uso do bot para vídeos em inglês, português e materiais de estudo, e reaproveita a mesma base estrutural necessária para resumo, SRT/VTT e notas Obsidian.

### A.3 Bilinguismo no mesmo MD (`baixa`, `grande`)
Para vídeos com falantes alternando idiomas, gerar um MD com cada turno marcado por `[lang=pt]` ou `[lang=en]`. Requer detecção de idioma por turno (não trivial) e fluxo de transcrição multimodal.

---

## B. Identificação de falantes

### B.1 Renomeação cross-vídeo via embeddings (`baixa`, `grande`)
Hoje `/rename` é local ao vídeo. Uma evolução seria reconhecer automaticamente que o `SPEAKER_00` do vídeo X tem a mesma voz do `SPEAKER_01` do vídeo Y (mesmo entrevistado, por exemplo) e propor "Sugiro nomeá-lo como 'Eduardo Giannetti', confirmar?".

Implementação:
- Extrair speaker embeddings (vetor por falante) durante a diarização (pyannote já produz).
- Persistir embeddings em uma tabela `voice_profiles` com nome amigável.
- Em vídeos novos, comparar embeddings dos falantes detectados com a base; sugerir matches acima de um threshold.
- Distância coseno > 0.8 sugere match.

Riscos: falsos positivos podem ser confusos ("você renomeou esse falante como 'João' antes — confirmar?" quando não é a mesma pessoa). Requer UX cuidadosa.

### B.2 Aprendizado supervisionado de perfis (`baixa`, `grande`)
Comando `/profile <nome>` durante diálogo de rename para "salvar este perfil de voz" no banco de embeddings, melhorando a sugestão futura.

### B.3 Hint de número de falantes (`média`, `pequeno`)
Permitir o usuário dar uma dica explícita: `<url> speakers=2` ou `<url> speakers=2-4` na mesma mensagem. O bot passaria `min_speakers`/`max_speakers` para o pyannote, melhorando a qualidade em casos limítrofes (monólogo erroneamente dividido, ou conferência com 6 pessoas detectada como 3).


### B.4 Renomeação de falantes por botões inline (`alta`, `médio`) — **solicitado**
Hoje o fluxo de renomeação depende de comando textual, por exemplo `/rename SPEAKER_00 Nome`. Uma evolução de UX seria usar **botões inline do Telegram** logo após a transcrição, permitindo renomear falantes sem memorizar comandos.

**Funcionamento previsto**:
- Ao finalizar uma transcrição com diarização, o bot envia uma mensagem auxiliar:
  - `SPEAKER_00 — renomear`
  - `SPEAKER_01 — renomear`
  - `Concluir nomes`
- Ao tocar em `Renomear SPEAKER_00`, o bot entra em modo conversacional curto e pergunta:
  - `Qual nome deseja usar para SPEAKER_00?`
- O usuário responde com o nome, e o bot:
  - atualiza o snapshot JSON da transcrição;
  - re-renderiza o Markdown com o nome amigável;
  - reenvia o `.md` revisado;
  - opcionalmente atualiza também `.srt`, `.vtt` e `.json`, quando essas saídas existirem.

**Variações úteis**:
- Botões rápidos: `Entrevistador`, `Entrevistado`, `Palestrante`, `Convidado`.
- Botão `Ignorar` para manter `SPEAKER_XX`.
- Botão `Mesclar falantes` para casos em que o pyannote dividiu a mesma pessoa em dois IDs.
- Botão `Desfazer último rename`.
- Botão `Salvar como perfil de voz`, quando B.1/B.2 forem implementados.

**Estado conversacional necessário**:
- Guardar temporariamente qual `job_id` e qual `speaker_id` estão sendo renomeados.
- Expirar o estado após alguns minutos para evitar renomeações acidentais.
- Validar que apenas o usuário autorizado pode acionar os botões.
- Garantir idempotência: tocar duas vezes no botão não deve duplicar reprocessamentos.

**Considerações técnicas**:
- Usar `InlineKeyboardMarkup` e `CallbackQueryHandler` do `python-telegram-bot`.
- O `callback_data` deve ser curto e seguro, por exemplo `rename:<job_id>:SPEAKER_00`.
- Para não ultrapassar limites do Telegram, usar `job_id` curto ou mapear callbacks para uma tabela/estrutura interna.
- O rename deve operar sobre os segmentos persistidos em JSON, não sobre o Markdown já renderizado, para evitar substituições textuais frágeis.
- Se houver fila ativa, o rename não deve competir com o pipeline de transcrição; ele deve ser tratado como operação leve de pós-processamento.

**Prioridade sugerida**: alta, porque melhora muito o uso real em celular e reduz erro operacional. Deve vir depois da persistência robusta de segmentos JSON e antes de perfis cross-vídeo.

---

## C. Resumos e análises

### C.1 Resumo automático no chat (`média`, `pequeno`)
Após a transcrição, gerar um resumo em 5–10 linhas via LLM (chamada à API OpenAI ou modelo local) e enviar como mensagem de texto separada do MD.

### C.2 Tópicos e timestamps temáticos (`baixa`, `médio`)
Identificar mudanças de tópico no áudio e produzir um índice navegável no início do MD ("00:00 — Apresentação; 03:14 — Memória; 12:48 — Hábitos de leitura"). Pode ser feito por LLM lendo a transcrição.

### C.3 Citações destacadas (`baixa`, `pequeno`)
LLM extrai 3–5 trechos marcantes do conteúdo e os destaca em uma seção `## Trechos notáveis` do MD.

### C.4 Fluxo combinado: resumo + tradução + nota (`alta`, `médio`) — **solicitado**
Permitir que o usuário escolha se deseja apenas a transcrição, uma tradução, um resumo, ou uma nota final traduzida. Isso evita misturar três produtos diferentes no mesmo comando.

**Fluxos previstos**:
- `/summary` → resumo no idioma original.
- `/summary pt` → resumo em português, mesmo que o vídeo esteja em inglês.
- `/translate en` → tradução completa.
- `/note obsidian` → nota de estudo no idioma original.
- `/note obsidian pt` → nota de estudo em português.

**Decisão importante**:
Resumo e tradução não devem sobrescrever a transcrição literal. Eles são artefatos derivados, com nomes próprios e metadados explícitos.

**Risco metodológico**:
Tradução seguida de resumo pode introduzir dupla camada de interpretação. Para uso acadêmico ou técnico, preservar sempre o link para o trecho original com timestamp.

---

## D. Formato de saída

### D.1 Exportação SRT para legendagem de vídeo (`alta`, `pequeno`) — **solicitado**
Conversão de uma transcrição existente (em `.md`) para um arquivo de legendas `.srt`, padrão de fato para legendagem de vídeo. **Funcionalidade explicitamente solicitada** após o fechamento do contrato inicial; entrará numa próxima rodada de planejamento.

**Funcionamento previsto**:
- Comando `/srt` (sem argumentos) → converte o **último** vídeo processado.
- Comando `/srt <video_id>` → converte um vídeo específico do histórico.
- O bot lê os segmentos com timestamps (que já ficam armazenados internamente, vindos do WhisperX ou das legendas YouTube), reformata como SRT e envia o `.srt` no chat.

**Detalhes técnicos**:
- WhisperX já produz timestamps em nível de palavra. A agregação em blocos curtos (3–7s, ~42 caracteres por linha conforme padrões de legendagem profissional como BBC e Netflix) é trivial.
- Para legendas vindas do YouTube, os timestamps por segmento já vêm prontos no formato VTT/SRT.
- O `.srt` deve preservar os nomes renomeados de falantes (se `/rename` foi aplicado), prefixando cada bloco quando houver mais de um falante: `[Eduardo] Texto da fala...`.
- Opção adicional: comando `/vtt <video_id>` para o formato WebVTT (HTML5 nativo).

**Considerações**:
- A persistência atual armazena o MD final, mas não necessariamente os segmentos com timestamps brutos. Para implementar SRT é preciso decidir: **(a)** persistir os segmentos crus em JSON ao lado do MD, ou **(b)** re-extrair os timestamps a partir do MD (heurístico, frágil), ou **(c)** só permitir SRT em vídeos cujo `.ogg` ainda não expirou (reprocessando do áudio, mais lento).
- Recomenda-se **(a)**: adicionar `data/segments/<slug>.json` ao conjunto de artefatos preservados (pequeno, ~KB), mesmo após a expiração do `.ogg`. Isso também habilita futuras features (D.3 JSON, C.1 resumo, etc.).
- Em vez de comando, alternativamente: gerar `.srt` automaticamente junto com o `.md` em todo job, e enviar os dois. Decisão a tomar quando essa feature for promovida ao escopo.

### D.2 Exportação PDF (`baixa`, `pequeno`)
Conversão do MD em PDF via WeasyPrint ou Pandoc. Já decidido em contrato (Dúvida 32) **não** implementar no MVP; aqui fica o registro.

### D.3 JSON estruturado (`baixa`, `pequeno`)
Comando `/json <video_id>` que devolve toda a estrutura (segmentos com timestamps por palavra, falantes, confidências) para uso programático.

### D.4 Transcript com texto bruto sem timestamps (`baixa`, `trivial`)
Comando `/text <video_id>` para uma versão "limpa" só com o texto, ideal para colar em outras ferramentas.


### D.5 Vídeo com legendas incorporadas (`média`, `médio`) — **solicitado**
Gerar e devolver ao usuário uma cópia do vídeo original com legendas sincronizadas. Há duas variantes tecnicamente diferentes, que devem ser tratadas como opções separadas:

1. **Legenda selecionável/soft subtitles**: o vídeo é entregue com uma faixa de legenda embutida, mas o usuário pode ligar/desligar a legenda no player. Normalmente usa contêiner `.mkv` ou `.mp4` com faixa `mov_text`/`srt`.
2. **Legenda queimada/hard subtitles**: a legenda é renderizada diretamente na imagem do vídeo. Funciona em qualquer player, mas não pode ser desligada e exige reencode completo do vídeo.

**Funcionamento previsto**:
- Comando `/video_subs` → gera vídeo legendado do último job.
- Comando `/video_subs <video_id>` → gera vídeo legendado de item específico do histórico.
- Opções futuras:
  - `/video_subs soft <video_id>` → legenda selecionável.
  - `/video_subs hard <video_id>` → legenda queimada na imagem.
  - `/video_subs --style large --position bottom <video_id>` → estilo de fonte/posição.

**Pipeline técnico provável**:
- Baixar ou reutilizar o vídeo original, não apenas o áudio.
- Gerar `.srt` ou `.ass` a partir dos segmentos persistidos.
- Para legenda selecionável:
  - muxar vídeo + áudio + legenda sem reencode quando possível.
- Para legenda queimada:
  - usar `ffmpeg` com filtro `subtitles`/ASS;
  - reencodar vídeo, aceitando maior custo computacional.

**Considerações**:
- Arquivos de vídeo podem exceder limites do Telegram. O bot deve verificar tamanho final e, se necessário, devolver apenas o `.srt`/`.ass`, dividir o arquivo, reduzir resolução/bitrate ou salvar em pasta local.
- Hard subtitles são mais compatíveis, mas mais lentas e destrutivas: a legenda vira parte da imagem.
- Soft subtitles são mais elegantes para arquivo local, mas nem todo player/app exibe a faixa corretamente.
- É recomendável implementar primeiro D.1 `.srt` e só depois esta funcionalidade, pois o vídeo legendado depende de legendas sincronizadas confiáveis.
- A opção de estilo deveria usar `.ass`, não apenas `.srt`, caso se deseje controle de fonte, borda, cor, posição e quebra de linha.

**Prioridade sugerida**: depois da exportação SRT/VTT e JSON estruturado, porque depende diretamente desses artefatos.

---

## E. Operação e integração

### E.1 Webhook em vez de polling (`baixa`, `pequeno`)
Para reduzir latência. Exige porta HTTPS exposta, fora do uso pessoal típico em máquina residencial.

### E.2 Modo multi-usuário (`baixa`, `médio`)
Permitir N usuários autorizados, com filas separadas e quotas de uso. Quebra a simplicidade atual; só faz sentido se o projeto virar serviço.

### E.3 Painel web local (`baixa`, `grande`)
Interface web em Flask/FastAPI para visualizar histórico, MDs, métricas, com server local em `http://localhost:8765`. Permite buscar texto dentro das transcrições.

### E.4 Integração com Obsidian / Notion (`baixa`, `médio`)
Auto-importar MDs gerados para um vault Obsidian local (apenas mover/copiar arquivos para a pasta correta) ou para um workspace Notion via API. Útil se o usuário usa essas ferramentas como knowledge base.

### E.5 Comando `/search <texto>` (`média`, `médio`)
Busca full-text dentro de todos os MDs históricos. SQLite tem extensão FTS5 que torna isso simples.

### E.6 Quotas e estatísticas (`baixa`, `pequeno`)
Comando `/stats` mostrando: número total de vídeos transcritos, horas de áudio processadas, tempo médio por vídeo, modelo mais usado, etc.

---

## F. Performance e qualidade

### F.1 Cache de modelos pré-carregados (`média`, `pequeno`)
Manter o modelo Whisper carregado em memória entre jobs (em vez de recarregar a cada vídeo), economizando 5–30s por job. Cuidado: aumenta RAM/VRAM idle. Evictar após N minutos de inatividade.

### F.2 Modelos quantizados extras (`baixa`, `médio`)
Suporte explícito a modelos `distil-whisper` (3x mais rápidos que `whisper-medium` com qualidade similar para EN) e a builds quantizados em `int4`. Requer testes de qualidade extensivos.

### F.3 GPU em paralelo com pré-processamento (`baixa`, `médio`)
Enquanto a GPU transcreve um vídeo, baixar/converter o próximo em CPU em paralelo. Quebra o "single-threaded" atual; só vale se a fila for frequente.

### F.4 Caching de embeddings de áudio (`baixa`, `grande`)
Para acelerar `/redo`: persistir mel-spectrograms ou features de wav2vec2 em disco, evitando reextração.


### F.5 Backend Transformers para ASR em português (`alta`, `médio`) — **solicitado**
Adicionar um segundo backend de transcrição baseado em **Hugging Face Transformers/PyTorch**, complementar ao fluxo atual `WhisperX → faster-whisper/CTranslate2`.

**Motivação**:
- O backend atual é adequado para modelos compatíveis com WhisperX/faster-whisper, como `medium`, `large-v3` e modelos publicados em formato compatível com CTranslate2.
- Alguns modelos fine-tuned para português brasileiro são publicados principalmente no formato nativo Transformers/PyTorch, como `freds0/distil-whisper-large-v3-ptbr`.
- Esses modelos podem ser úteis quando `large-v3` ou mesmo modelos PT compatíveis com WhisperX não entregarem fidelidade suficiente em fala brasileira espontânea, técnica ou acelerada.

**Relação com o modelo INESC**:
- O modelo `inesc-id/WhisperLv3-X-PT-All` deve ser testado primeiro no fluxo atual, pois é apresentado para uso direto com WhisperX.
- O backend Transformers não substitui esse caminho; ele complementa o INESC como rota alternativa para modelos Hugging Face que não carregam bem pelo WhisperX/faster-whisper.
- A política futura desejada é um roteador de ASR, não um único modelo fixo.

**Funcionamento previsto**:
- Criar uma porta comum `TranscriptionEngine`/`ASREngine`, mantendo a saída normalizada no formato interno do bot: segmentos, timestamps, idioma, modelo e metadados.
- Implementar `TransformersWhisperTranscriptionEngine` usando `transformers`, `torch` e `AutoProcessor`/`WhisperProcessor` + `WhisperForConditionalGeneration` ou `AutoModelForSpeechSeq2Seq`, conforme o modelo.
- Permitir configuração por idioma e backend.

**Configuração futura sugerida**:

```env
ASR_BACKEND=auto

ASR_PT_PRIMARY_BACKEND=whisperx
ASR_PT_PRIMARY_MODEL=inesc-id/WhisperLv3-X-PT-All

ASR_PT_FALLBACK_BACKEND=transformers
ASR_PT_FALLBACK_MODEL=freds0/distil-whisper-large-v3-ptbr

ASR_EN_PRIMARY_BACKEND=whisperx
ASR_EN_PRIMARY_MODEL=medium

ENABLE_ASR_QUALITY_GATE=true
```

**Comandos futuros possíveis**:
- `/redo --backend whisperx --model inesc-id/WhisperLv3-X-PT-All`
- `/redo --backend transformers --model freds0/distil-whisper-large-v3-ptbr`
- `/redo --ptbr`
- `/redo --accurate-pt`
- `/redo --no-youtube-captions`

**Interação com qualidade de transcrição**:
- Usar o teste de qualidade de ASR para decidir fallback:
  - se a transcrição por legenda automática falhar → baixar áudio;
  - se `whisperx + INESC` falhar ou produzir texto com sinais de baixa qualidade → tentar `transformers + freds0`;
  - se ambos falharem e houver configuração externa → sugerir ou acionar backend cloud.
- Registrar no Markdown qual backend/modelo foi usado, para rastreabilidade.

**Limitações e riscos**:
- A saída Transformers pode ter timestamps menos convenientes que WhisperX; talvez seja necessário usar chunking com timestamps aproximados ou uma etapa posterior de alinhamento.
- O consumo de RAM/VRAM pode ser maior, principalmente se Transformers carregar modelos PyTorch sem quantização.
- A diarização continua separada: o backend Transformers transcreve; pyannote/WhisperX diarization ainda identifica falantes.
- Comparações devem ser empíricas, em vídeos reais do usuário, não decididas apenas por benchmark genérico.

**Critério de aceite futuro**:
- O bot deve conseguir transcrever um vídeo PT-BR com `ASR_PT_FALLBACK_BACKEND=transformers` e `ASR_PT_FALLBACK_MODEL=freds0/distil-whisper-large-v3-ptbr`.
- O Markdown final deve indicar backend, modelo e se houve fallback.
- A saída deve preservar compatibilidade com renderer, `/rename`, merge de falantes, exportação futura SRT/VTT e notas Obsidian.

**Prioridade sugerida**: alta depois do teste com INESC, porque cria flexibilidade real para comparar modelos locais especializados em português sem reescrever o pipeline inteiro.

---

## G. Diarização avançada

### G.1 Suporte a NVIDIA NeMo (`baixa`, `médio`)
Adicionar `NemoDiarizationAdapter` como terceira opção (depois de WhisperX e pyannote direto). Util se houver casos onde NeMo supera o pyannote.

### G.2 Diarização sensível a sobreposição de fala (`baixa`, `grande`)
pyannote 3.1 já lida razoavelmente com sobreposição, mas modelos especializados (Powerset multi-label) podem dar melhor qualidade. Custa mais inferência.

### G.3 Detecção de emoção/sentimento por turno (`baixa`, `grande`)
Modelos como `superb/wav2vec2-base-superb-er` classificam emoção por segmento. Adicionaria uma coluna `emoção` aos blocos do MD. Util para entrevistas sensíveis.

---

## H. Robustez

### H.1 Health-check periódico (`média`, `pequeno`)
Endpoint local ou comando interno que valida: ffmpeg vivo, banco acessível, modelos disponíveis, espaço em disco suficiente, conexão Telegram OK. Reportar via `/healthcheck`.

### H.2 Auto-update de yt-dlp (`baixa`, `pequeno`)
yt-dlp é frequentemente atualizado para acompanhar mudanças do YouTube. Comando `/updateytdlp` que faz `pip install --upgrade yt-dlp` no venv. Ou auto-detectar idade do binário e avisar.

### H.3 Backup automático do SQLite (`baixa`, `pequeno`)
Cron interno que copia `data/jobs.db` para `data/backups/jobs-YYYYMMDD.db` semanalmente, mantendo as últimas 4.

### H.4 Métricas Prometheus (`baixa`, `médio`)
Expor métricas (jobs processados, falhas, tempo por etapa) em `/metrics` para um Prometheus local. Para usuário avançado.

---

## I. UX

### I.1 Modos de verbosidade (`baixa`, `pequeno`)
Comando `/verbose on|off` que liga/desliga as mensagens de progresso intermediárias.

### I.2 Modo "noturno" (`baixa`, `pequeno`)
Bot só processa entre HH e HH (ex.: madrugada) para não atrapalhar o dia. Variáveis `QUIET_HOURS_START`, `QUIET_HOURS_END`.

### I.3 Notificações por email (`baixa`, `médio`)
Em jobs longos, enviar email quando concluir, em paralelo ao Telegram.

### I.4 Múltiplas faixas de áudio (`baixa`, `pequeno`)
Em vídeos com auto-dub, oferecer comando para baixar a faixa dublada também (ex.: `/dub en <video_id>`), gerando MD adicional.

---

## J. Tratamento de áudio

### J.1 Vídeos parcialmente musicais (`média`, `médio`)
Hoje o bot rejeita vídeos com pouca fala. Uma evolução: identificar **trechos** musicais e pulá-los na transcrição (registrando "[música]" no MD), mas processar os trechos com fala. Permite, por exemplo, transcrever uma palestra com música de abertura/encerramento longa.

### J.2 Limpeza de áudio (`baixa`, `médio`)
Aplicar redução de ruído (`noisereduce`), normalização, filtro passa-alta antes da transcrição. Pode melhorar qualidade em vídeos com áudio ruim.

### J.3 Detecção de aplausos/risadas (`baixa`, `pequeno`)
Marcar `[aplausos]`, `[risadas]`, `[música]` no MD usando classificadores leves de eventos sonoros (YAMNet ou similares).

---

## K. Engenharia de software

### K.1 Migração para Alembic (`baixa`, `pequeno`)
Substituir o script de criação manual de schema por migrações Alembic, facilitando mudanças futuras no esquema do SQLite.

### K.2 Logs estruturados em JSON opcional (`baixa`, `pequeno`)
Decisão atual é texto humano. Uma opção `LOG_FORMAT=json` poderia ser adicionada para integração com ferramentas de observabilidade.

### K.3 Suporte a Docker Compose (`baixa`, `pequeno`)
Dockerfile + docker-compose.yml para rodar o bot em container, abstraindo dependências do sistema. Útil em servidores não-Fedora/Ubuntu.

### K.4 GitHub Actions CI (`baixa`, `pequeno`)
Workflow que roda os testes unitários (não integração/e2e, que exigem GPU/modelos pesados) em cada PR.

### K.5 Pre-commit hooks (`baixa`, `trivial`)
`.pre-commit-config.yaml` que roda ruff + mypy automaticamente antes de cada commit.

---

## Critério para promover um item daqui ao escopo

Quando você quiser implementar um destes itens:

1. Promovê-lo a uma **nova rodada de levantamento de requisitos** (perguntas dirigidas).
2. Adicionar as decisões resultantes ao [contrato funcional](./01-contrato-funcional.md) numa nova seção.
3. Estender o [plano de execução](./05-plano-de-execucao.md) com um **novo gate** (ou estender um existente, se o item couber natural­mente).
4. Implementar seguindo o mesmo ciclo TDD purista + bug→regressão.
5. Remover o item deste documento (movê-lo para um `CHANGELOG.md` na seção da release que o entregou).

Nada deste documento é "promessa": tudo é "memória".
