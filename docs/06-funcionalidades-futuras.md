# Funcionalidades Futuras

Este documento registra funcionalidades conscientemente postergadas. A presença de um item aqui não implica compromisso automático de implementação; cada item deve ser promovido por especificação, testes e validação manual antes de entrar no código.

O roadmap abaixo foi revisado após a estabilização de `/healthcheck` e `/lasterror`. A prioridade atual é aumentar a utilidade dos artefatos já gerados, ampliar a cobertura de entrada/idiomas e só depois integrar com sistemas externos de notas.

---

## Funcionalidades recém-promovidas para implementação

As funcionalidades abaixo saíram do roadmap e devem permanecer documentadas no README, no contrato funcional, no manual e nas patch notes:

- `/healthcheck`: diagnóstico operacional de configuração, dependências, diretórios, SQLite, cookies, LM Studio, tokenizer/orçamento de sumarização e espaço em disco.
- `/lasterror`: recuperação do último erro operacional sanitizado, cobrindo jobs `failed` e erros derivados de `/summary`, exportações, vídeo legendado, limpeza de cache e exceções defensivas do pipeline.

Elas não devem ser tratadas como futuras. Evoluções incrementais ainda podem ser propostas como refinamentos de observabilidade, não como nova feature principal.

---

## Roadmap priorizado

### 1. `/search <texto>` + arquitetura para busca semântica (`alta`, `médio`)

Busca textual em transcrições, resumos e metadados já processados, com arquitetura preparada para uma camada semântica futura.

**Motivação.** O histórico local só é realmente útil se puder ser pesquisado por tema, pessoa, expressão técnica, vídeo, canal ou data. Esta funcionalidade transforma o bot de um processador de vídeos em uma base consultável de conhecimento.

**Escopo mínimo do MVP textual.**

- Comando `/search <texto>`.
- Busca em Markdown de transcrição, resumos, título, canal, URL, `video_id`, idioma e nomes amigáveis de falantes.
- Retorno compacto no Telegram com os melhores resultados, cada um contendo índice histórico, título, `video_id`, data e trecho relevante.
- Reenvio do artefato via `/last [n]`, `/summary [n]` ou exportação já existente.
- Atualização do índice após nova transcrição, `/rename` e `/summary`.

**Estratégia técnica sugerida para o MVP.**

- Usar SQLite FTS5 quando disponível.
- Manter fallback documentado se FTS5 não estiver presente no SQLite local.
- Indexar textos derivados como artefatos, sem substituir a transcrição literal.
- Criar testes de ranking básico, busca sem resultado, sanitização e compatibilidade com transcrições antigas.

**Evolução semântica futura dentro da mesma linha.**

- Comando futuro `/search semantic <texto>` ou opção equivalente.
- Comando futuro `/related [n]` para recuperar transcrições semanticamente próximas.
- Índice vetorial com embeddings locais.
- Recuperação de trechos relevantes para revisão, estudo e integração futura com Obsidian/Zotero.

A busca semântica não deve entrar no primeiro MVP para evitar dependência prematura de embeddings. O desenho do índice textual, porém, deve evitar acoplamento que dificulte a camada vetorial depois.

---

### 2. `/text [n]` — texto limpo da transcrição (`alta`, `pequeno`)

Exportar uma versão limpa da transcrição, em `.txt`, para leitura, cópia, revisão humana ou uso como entrada em outra LLM.

**Escopo mínimo.**

- Comando `/text [n]`.
- Sem índice, usa a transcrição mais recente.
- Gera arquivo `.txt` derivado do snapshot da transcrição.
- Preserva título, metadados mínimos e falantes quando disponíveis.
- Remove formatação Markdown pesada.
- Não reprocessa áudio, ASR ou diarização.

**Variações futuras possíveis.**

- `/text clean [n]`: texto corrido, sem timestamps.
- `/text speakers [n]`: texto agrupado por falante.
- `/text timestamps [n]`: texto simples preservando timestamps essenciais.

---

### 3. Transcrição de arquivo de áudio enviado ao Telegram (`alta`, `médio`)

Permitir que o usuário envie um arquivo de áudio diretamente ao bot e receba a mesma saída do pipeline de YouTube: Markdown, diarização, exportações e resumo.

**Escopo previsto.**

- Receber `audio`, `voice` ou `document` com MIME de áudio.
- Aceitar formatos como `.mp3`, `.wav`, `.m4a`, `.ogg` e `.flac`, conforme suporte real do `ffmpeg`.
- Validar tamanho, duração e extensão.
- Salvar em diretório de downloads com metadados mínimos.
- Criar job sem `youtube_url`, mas com `source_type=telegram_audio` ou equivalente.
- Reaproveitar normalização de áudio, WhisperX, diarização, renderização, exportações e sumarização.

**Cuidados.**

- Limites do Telegram para upload/download.
- Diferença entre mensagens `voice` comprimidas e arquivos de áudio de maior qualidade.
- Política de retenção semelhante à de vídeos processados.
- Ajustes no histórico, já que alguns jobs não terão `video_id` nem URL do YouTube.

---

### 4. Backend alternativo de ASR e suporte multilíngue ampliado (`alta`, `médio/grande`)

Adicionar ou estruturar backends alternativos ao fluxo atual com WhisperX/faster-whisper, permitindo melhor cobertura para idiomas além de português e inglês.

**Motivação.** Antes de investir em tradução e notas externas, o bot deve conseguir lidar melhor com vídeos em outros idiomas. Isso reduz dependência de legendas do YouTube e amplia o corpus processável.

**Possibilidades técnicas.**

- Faster-Whisper direto como backend alternativo ao WhisperX quando diarização/alinhamento completo não for necessário.
- Backend Transformers/PyTorch para modelos Hugging Face não compatíveis diretamente com faster-whisper.
- Modelos especializados por idioma.
- Configurações por idioma, por exemplo `WHISPER_MODEL_ES`, `WHISPER_MODEL_FR`, `WHISPER_MODEL_DEFAULT`.
- Fallback automático por idioma ou por falha de backend.

**Cuidados.**

- Não quebrar a política atual `WHISPER_MODEL=auto`.
- Preservar reprodutibilidade: backend, modelo, idioma e parâmetros devem entrar nos metadados do Markdown/JSON.
- Evitar adicionar muitos comandos antes de estabilizar a arquitetura interna.

---

### 5. `/translate` — tradução controlada como artefato derivado (`média/alta`, `médio`)

Gerar artefatos traduzidos a partir da transcrição original, sem substituir o original. Esta funcionalidade deve vir depois do suporte ASR multilíngue ampliado.

**Comandos possíveis.**

- `/translate pt [n]`.
- `/translate en [n]`.
- `/translate pt --bilingual [n]`.

**Escopo previsto.**

- Traduzir Markdown da transcrição.
- Preservar timestamps, falantes, nomes próprios, links e metadados quando possível.
- Marcar explicitamente o resultado como artefato derivado sujeito a erro.
- Reaproveitar infraestrutura de chunking, tokenizer, timeout adaptativo e validação de modelo já usada no `/summary`.
- Futuramente, gerar SRT/VTT traduzidos.

---

### 6. Melhorias no `/redo` (`média`, `médio`)

A versão atual de `/redo <link>` cria um novo job explícito. Melhorias futuras devem reduzir retrabalho e tornar o reprocessamento mais seletivo.

**Possibilidades.**

- Confirmação inline antes de reprocessar vídeos longos.
- Mostrar diferença entre configuração antiga e atual.
- Refazer apenas resumo.
- Refazer apenas tradução.
- Refazer apenas exportação.
- Refazer com outro backend/modelo.
- Reaproveitar áudio/metadados existentes quando seguro.

---

### 7. Integração com Obsidian / Notion (`média`, `médio`)

Autoexportar transcrições, resumos e traduções para um vault Obsidian local ou workspace Notion. Esta funcionalidade fica mais adiante porque o formato Markdown atual já atende parcialmente ao uso em Obsidian.

**Ideia inicial.**

- Gerar Markdown com YAML frontmatter.
- Incluir URL original, `video_id`, canal, data, idioma, modelos usados e links para artefatos.
- Permitir comandos como `/note obsidian [n]`.
- Preservar a transcrição literal como fonte da verdade.
- Incorporar resumo, tradução e texto limpo quando existirem.

---

## Funcionalidades úteis, mas fora da prioridade principal atual

### Estatísticas operacionais (`baixa`, `pequeno`)

Comando `/stats` para vídeos processados, horas transcritas, tempo médio por etapa, número de falhas, taxa de uso de legenda do YouTube versus WhisperX, modelos usados e tamanho médio dos artefatos.

**Decisão atual.** Não é prioridade porque não atende uma dor imediata do fluxo de estudo/transcrição. Pode ser retomado se houver necessidade de auditoria de uso ou otimização operacional.

### Recuperação avançada após interrupção (`baixa`, `médio`)

Detecção e retomada seletiva de jobs interrompidos por queda do processo, hibernação ou reinício.

**Decisão atual.** Não é prioridade porque a complexidade é alta em relação ao ganho imediato. O foco operacional atual deve permanecer em `/healthcheck`, `/lasterror`, logs sanitizados e reprocessamento explícito.

---

## Vídeo e legendagem

### Legenda queimada/hard subtitles (`baixa`, `médio`)

A versão atual já gera MP4 com legenda selecionável. Uma evolução possível é gerar legenda queimada na imagem.

**Trade-off.** Legenda queimada aumenta compatibilidade em plataformas simples, mas cria artefato maior, mais lento e irreversível. Não é prioridade atual.

### Estilos avançados de legenda (`baixa`, `médio`)

Gerar `.ass` com fonte, borda, cor, posição e quebra de linha controlada. Útil apenas se hard subtitles ou publicação externa forem prioridades.

---

## ASR, diarização e qualidade complementar

### Hint de número de falantes (`média`, `pequeno`)

Permitir informar `speakers=2` ou `speakers=2-4` junto do link/áudio, repassando `min_speakers`/`max_speakers` para a diarização.

### Perfis de voz cross-vídeo (`baixa`, `grande`)

Persistir embeddings de falantes para sugerir nomes em vídeos futuros. Requer UX cuidadosa para evitar falsos positivos.

### Tratamento de trechos musicais (`média`, `médio`)

Em vez de rejeitar vídeos parcialmente musicais, detectar trechos com música e transcrever apenas os trechos com fala, marcando `[música]` no Markdown.

### Limpeza de áudio (`baixa`, `médio`)

Aplicar redução de ruído, normalização ou filtro passa-alta antes da transcrição. Deve ser validado empiricamente, pois pode piorar áudio já comprimido.

---

## Operação e engenharia

### Webhook em vez de polling (`baixa`, `pequeno`)

Trocar polling por webhook para reduzir latência. Só faz sentido com HTTPS exposto e operação mais estável em servidor.

### Backup automático do SQLite (`baixa`, `pequeno`)

Criar backups periódicos de `data/jobs.db` para `data/backups/jobs-YYYYMMDD.db`, mantendo as últimas N cópias.

### Logs estruturados em JSON opcional (`baixa`, `pequeno`)

Adicionar `LOG_FORMAT=json` para integração futura com observabilidade externa.

### Docker Compose (`baixa`, `pequeno`)

Empacotar bot em container. Útil para servidor, mas menos prioritário no fluxo local com GPU/WSL2.

### GitHub Actions CI (`baixa`, `pequeno`)

Rodar testes unitários e linters em PRs, sem depender de GPU ou modelos pesados.
