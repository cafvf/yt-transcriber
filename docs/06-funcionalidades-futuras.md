# Funcionalidades Futuras

Este documento registra funcionalidades conscientemente postergadas. A presença de um item aqui não implica compromisso automático de implementação; cada item deve ser promovido por especificação, testes e validação manual antes de entrar no código.

---

## Funcionalidades recém-promovidas para implementação

As funcionalidades abaixo saíram do roadmap e devem permanecer documentadas no README, no contrato funcional, no manual e nas patch notes:

- `/healthcheck`: diagnóstico operacional de configuração, dependências, diretórios, SQLite, cookies, LM Studio, tokenizer/orçamento de sumarização e espaço em disco.
- `/lasterror`: recuperação do último erro operacional sanitizado, cobrindo jobs `failed` e erros derivados de `/summary`, exportações, vídeo legendado, limpeza de cache e exceções defensivas do pipeline.

Elas não devem ser tratadas como futuras. Evoluções incrementais ainda podem ser propostas como refinamentos de observabilidade, não como nova feature principal.

---

## Próxima prioridade: busca e recuperação de conhecimento

### 1. `/search <texto>` (`alta`, `médio`) — prioridade alta

Busca full-text em transcrições, resumos e metadados já processados.

**Motivação.** O histórico local só é realmente útil se puder ser pesquisado por tema, pessoa, expressão técnica, vídeo, canal ou data. Esta funcionalidade transforma o bot de um processador de vídeos em uma base consultável de conhecimento.

**Escopo mínimo.**

- Comando `/search <texto>`.
- Busca em Markdown de transcrição, resumos, título, canal, URL, `video_id`, idioma e nomes amigáveis de falantes.
- Retorno compacto no Telegram com os melhores resultados, cada um contendo índice histórico, título, `video_id`, data e trecho relevante.
- Reenvio do artefato via `/last [n]`, `/summary [n]` ou exportação já existente.
- Atualização do índice após nova transcrição, `/rename` e `/summary`.

**Estratégia técnica sugerida.**

- Usar SQLite FTS5 quando disponível.
- Manter fallback documentado se FTS5 não estiver presente no SQLite local.
- Indexar textos derivados como artefatos, sem substituir a transcrição literal.
- Criar testes de ranking básico, busca sem resultado, sanitização e compatibilidade com transcrições antigas.

### 2. `/stats` (`baixa`, `pequeno`)

Comando para estatísticas operacionais: vídeos processados, horas transcritas, tempo médio por etapa, número de falhas, taxa de uso de legenda do YouTube versus WhisperX, modelos usados e tamanho médio dos artefatos.

---

## Entrada de áudio fora do YouTube

### 3. Transcrição de arquivo de áudio enviado ao Telegram (`alta`, `médio`)

Permitir que o usuário envie um arquivo de áudio diretamente ao bot e receba a mesma saída do pipeline de YouTube: Markdown, diarização, exportações e, futuramente, resumo/tradução.

**Escopo previsto.**

- Receber `audio`, `voice` ou `document` com MIME de áudio.
- Validar tamanho, duração e extensão.
- Salvar em diretório de downloads com metadados mínimos.
- Criar job sem `youtube_url`, mas com `source_type=telegram_audio`.
- Reaproveitar normalização de áudio, WhisperX, diarização, renderização, exportações e sumarização.

**Cuidados.**

- Limites do Telegram para upload/download.
- Diferença entre mensagens `voice` comprimidas e arquivos de áudio de maior qualidade.
- Política de retenção semelhante à de vídeos processados.

---

## Artefatos derivados e integração com conhecimento

### 4. Integração com Obsidian / Notion (`média`, `médio`)

Autoexportar transcrições e resumos para um vault Obsidian local ou workspace Notion.

**Ideia inicial.**

- Gerar Markdown com YAML frontmatter.
- Incluir URL original, `video_id`, canal, data, idioma, modelos usados e links para artefatos.
- Permitir comandos como `/note obsidian [n]`.
- Preservar a transcrição literal como fonte da verdade.

### 5. Tradução automática da transcrição (`média`, `médio`)

Gerar artefatos traduzidos a partir da transcrição original, sem substituir o original.

**Comandos possíveis.**

- `/translate en [n]`.
- `/translate pt [n]`.
- `/translate en --bilingual [n]`.

A tradução deve preservar timestamps, falantes, nomes próprios, links e metadados. Deve ser marcada explicitamente como artefato derivado sujeito a erro.

### 6. Texto limpo sem timestamps (`baixa`, `pequeno`)

Comando `/text [n]` para exportar uma versão limpa da transcrição, sem timestamps e com falas paragraphizadas.

---

## Vídeo e legendagem

### 7. Legenda queimada/hard subtitles (`baixa`, `médio`)

A versão atual já gera MP4 com legenda selecionável. Uma evolução possível é gerar legenda queimada na imagem.

**Trade-off.** Legenda queimada aumenta compatibilidade em plataformas simples, mas cria artefato maior, mais lento e irreversível. Não é prioridade atual.

### 8. Estilos avançados de legenda (`baixa`, `médio`)

Gerar `.ass` com fonte, borda, cor, posição e quebra de linha controlada. Útil apenas se hard subtitles ou publicação externa forem prioridades.

---

## ASR, diarização e qualidade

### 9. Backend Transformers para ASR em português (`alta`, `médio`)

Adicionar backend baseado em Hugging Face Transformers/PyTorch como alternativa ao fluxo WhisperX/faster-whisper, especialmente para modelos de português que não são diretamente compatíveis com faster-whisper.

### 10. Hint de número de falantes (`média`, `pequeno`)

Permitir informar `speakers=2` ou `speakers=2-4` junto do link/áudio, repassando `min_speakers`/`max_speakers` para a diarização.

### 11. Perfis de voz cross-vídeo (`baixa`, `grande`)

Persistir embeddings de falantes para sugerir nomes em vídeos futuros. Requer UX cuidadosa para evitar falsos positivos.

### 12. Tratamento de trechos musicais (`média`, `médio`)

Em vez de rejeitar vídeos parcialmente musicais, detectar trechos com música e transcrever apenas os trechos com fala, marcando `[música]` no Markdown.

### 13. Limpeza de áudio (`baixa`, `médio`)

Aplicar redução de ruído, normalização ou filtro passa-alta antes da transcrição. Deve ser validado empiricamente, pois pode piorar áudio já comprimido.

---

## Operação e engenharia

### 14. Webhook em vez de polling (`baixa`, `pequeno`)

Trocar polling por webhook para reduzir latência. Só faz sentido com HTTPS exposto e operação mais estável em servidor.

### 15. Backup automático do SQLite (`baixa`, `pequeno`)

Criar backups periódicos de `data/jobs.db` para `data/backups/jobs-YYYYMMDD.db`, mantendo as últimas N cópias.

### 16. Logs estruturados em JSON opcional (`baixa`, `pequeno`)

Adicionar `LOG_FORMAT=json` para integração futura com observabilidade externa.

### 17. Docker Compose (`baixa`, `pequeno`)

Empacotar bot em container. Útil para servidor, mas menos prioritário no fluxo local com GPU/WSL2.

### 18. GitHub Actions CI (`baixa`, `pequeno`)

Rodar testes unitários e linters em PRs, sem depender de GPU ou modelos pesados.
