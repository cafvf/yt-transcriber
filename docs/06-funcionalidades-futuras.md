# Funcionalidades Futuras

Este documento registra funcionalidades ainda não implementadas ou conscientemente postergadas. Ele deve permanecer alinhado ao estado real do código: itens já entregues devem sair daqui e ser documentados no README/manual/changelog ou em patch notes.

A presença de um item aqui **não** implica compromisso automático de implementação. Cada item tem prioridade subjetiva e esforço aproximado. A promoção de um item para desenvolvimento deve seguir o fluxo do projeto: especificação → testes → implementação → documentação.

---

## Próxima prioridade: observabilidade operacional

### 1. `/healthcheck` (`alta`, `pequeno`) — **próxima implementação recomendada**

Comando interno para validar rapidamente se o ambiente está pronto para operar. Deve evitar a situação em que um erro de `.env`, LM Studio, Telegram, `ffmpeg` ou diretório só aparece depois de um processamento longo.

**Escopo mínimo:**

- Confirmar qual `.env` efetivo está sendo usado.
- Garantir que `.env.example` não está sendo usado como runtime.
- Validar presença das variáveis obrigatórias, sem imprimir segredos.
- Verificar `ffmpeg` disponível.
- Verificar `yt-dlp` importável/executável e versão quando possível.
- Verificar diretórios de dados, downloads, transcripts, summaries, logs e models.
- Verificar se o SQLite está acessível.
- Verificar cookies do YouTube quando `YOUTUBE_COOKIES_FILE` ou `YOUTUBE_COOKIES_BROWSER` estiverem configurados.
- Verificar conectividade básica com a Bot API do Telegram.
- Verificar conectividade com `SUMMARY_BASE_URL`, quando sumarização estiver habilitada.
- Validar se `SUMMARY_MODEL` aparece em `GET /v1/models`, quando `SUMMARY_VALIDATE_MODEL=true`.
- Reportar espaço livre em disco.

**Saída esperada:**

```text
✅ Configuração: OK (.env: /caminho/do/projeto/.env)
✅ ffmpeg: OK
✅ yt-dlp: OK
✅ SQLite: OK
✅ Telegram: OK
✅ LM Studio: OK (modelo qwen/qwen3.5-9b encontrado)
⚠️ Cookies YouTube: não configurados
```

**Requisitos de segurança:**

- Nunca imprimir `TELEGRAM_BOT_TOKEN`, `HF_TOKEN`, cookies ou API keys.
- Mascarar valores sensíveis como `123456:ABC...` ou `hf_...`.
- Não enviar logs longos no Telegram.

**Testes mínimos:**

- Healthcheck totalmente OK.
- LM Studio indisponível.
- Modelo configurado ausente em `/v1/models`.
- `.env.example` rejeitado.
- Ausência de vazamento de tokens na resposta.
- `/help` lista `/healthcheck`.

### 2. `/lasterror` (`alta`, `pequeno`) — **próxima implementação recomendada**

Comando para recuperar o último erro operacional relevante de forma sanitizada. Deve reduzir a necessidade de copiar tracebacks completos do terminal.

**Escopo mínimo:**

- Mostrar o último job com status de falha, se existir.
- Exibir vídeo/título, `video_id`, horário, etapa aproximada e mensagem de erro.
- Mostrar trecho final sanitizado do traceback ou do log, com limite de caracteres.
- Informar quando não há erro recente.

**Saída esperada:**

```text
Último erro registrado:
Job: #42 — <título>
Video ID: abc123
Etapa: summary
Horário: 2026-05-04 13:08
Erro: ChatCompletionTimeoutError: timeout após 600s

Trecho técnico sanitizado:
...
```

**Requisitos de segurança:**

- Nunca expor tokens, cookies, API keys ou conteúdo integral de `.env`.
- Limitar tamanho da resposta para respeitar o Telegram.
- Se o erro estiver em arquivo, enviar apenas trecho final ou indicar caminho local.

**Testes mínimos:**

- `/lasterror` com job falho.
- `/lasterror` sem erro recente.
- Sanitização de tokens e cookies.
- Limite de tamanho da mensagem.
- `/help` lista `/lasterror`.

---

## Busca e recuperação de conhecimento

### 3. `/search <texto>` (`alta`, `médio`) — **prioridade alta após observabilidade**

Busca full-text em transcrições, resumos e metadados já processados.

**Motivação:**

O histórico local só é realmente útil se puder ser pesquisado por tema, pessoa, termo técnico ou trecho de fala. Essa funcionalidade transforma o bot de transcritor em uma base consultável.

**Escopo recomendado:**

- Indexar Markdown de transcrições.
- Indexar resumos em `data/summaries`, quando existirem.
- Indexar título, canal, URL, `video_id`, idioma, data e falantes renomeados.
- Usar SQLite FTS5 quando disponível.
- Mostrar resultados com título, data, trecho destacado e comando para recuperar o item.

**Comandos possíveis:**

```text
/search geomecânica bayesiana
/search "Spec-Driven Development"
/search speaker:Christiano in:summary tokenizer
```

**Saída esperada:**

```text
3 resultados para "geomecânica bayesiana":
1. [2026-05-04] Título do vídeo — 02:13: "..."
   Use /last 2 ou /summary 2
```

**Pontos de atenção:**

- Não reprocessar transcrições durante a busca.
- Preservar compatibilidade com arquivos antigos.
- Definir política para atualizar índice após `/rename` e `/summary`.

### 4. `/stats` (`baixa`, `pequeno`)

Comando para estatísticas operacionais:

- número total de vídeos processados;
- horas transcritas;
- tempo médio por vídeo;
- taxa de uso de legenda YouTube vs WhisperX;
- modelos usados;
- falhas por etapa;
- tamanho acumulado de artefatos.

---

## Entrada de áudio fora do YouTube

### 5. Transcrição de arquivo de áudio enviado ao Telegram (`alta`, `médio`) — **registrado a pedido do usuário**

Permitir que o usuário envie um arquivo de áudio diretamente ao bot e receba a mesma saída do pipeline de YouTube: Markdown, diarização, exportações e, futuramente, resumo/tradução.

**Entradas previstas:**

- arquivo de áudio enviado como documento (`.mp3`, `.m4a`, `.wav`, `.ogg`, `.opus`, `.flac`);
- mensagem de voz do Telegram;
- áudio nativo do Telegram;
- opcionalmente vídeo local curto, extraindo apenas o áudio.

**Comportamento esperado:**

- O bot detecta arquivo de áudio e pergunta/assume idioma conforme configuração.
- Converte para formato interno padronizado.
- Roda WhisperX/diarização como no pipeline de YouTube.
- Gera Markdown e snapshot JSON.
- Permite `/rename`, `/json`, `/srt`, `/vtt` e `/summary` sobre o job gerado.

**Comandos possíveis:**

```text
# fluxo implícito
<enviar audio.mp3>

# fluxo explícito, se necessário
/audio --lang pt
/audio --lang en
```

**Decisões pendentes:**

- Limite máximo de tamanho do arquivo recebido.
- Limite máximo de duração.
- Se mensagens de voz curtas devem ser transcritas automaticamente ou exigir confirmação.
- Como nomear o job quando não há título/canal do YouTube.
- Se deve haver fila separada para uploads.

**Testes mínimos:**

- Upload de `.mp3` com idioma explícito.
- Upload de áudio sem idioma explícito.
- Arquivo acima do limite.
- Formato não suportado.
- Compatibilidade com `/rename`, `/summary` e exportações.

---

## Artefatos derivados e integração com conhecimento

### 6. Integração com Obsidian / Notion (`média`, `médio`)

Autoexportar transcrições e resumos para um vault Obsidian local ou workspace Notion.

**Escopo recomendado para Obsidian:**

- Copiar Markdown para pasta configurada.
- Gerar YAML frontmatter com URL, título, canal, idioma, modelo, data e tags.
- Criar links para transcrição literal, resumo e arquivos de legenda.
- Preservar o usuário como curador final: o bot sugere estrutura, mas não reorganiza o vault sem confirmação.

**Comandos possíveis:**

```text
/note obsidian
/note obsidian 2
```

### 7. Tradução automática da transcrição (`média`, `médio`)

Gerar artefatos traduzidos a partir da transcrição original, sem substituir o original.

**Escopo recomendado:**

- `/translate pt [n]` e `/translate en [n]`.
- Tradução por segmentos para preservar timestamps.
- Glossário opcional para termos técnicos.
- Marcação explícita de que a tradução é derivada e pode conter erros.

**Observação:**

Não há interesse atual em criar múltiplos perfis de resumo. O foco deve ser artefatos objetivos: transcrição literal, resumo técnico único, tradução, busca e integração com base de conhecimento.

### 8. Texto limpo sem timestamps (`baixa`, `pequeno`)

Comando `/text [n]` para exportar uma versão limpa da transcrição, sem timestamps e com falas paragraphizadas.

---

## Vídeo e legendagem

### 9. Legenda queimada/hard subtitles (`baixa`, `médio`)

A versão atual já gera MP4 com legenda selecionável. Uma evolução possível é gerar legenda queimada na imagem.

**Riscos:**

- Reencode completo e mais lento.
- Arquivos maiores.
- Legenda não pode ser desligada.
- Requer controle de estilo `.ass` para boa legibilidade.

### 10. Estilos avançados de legenda (`baixa`, `médio`)

Gerar `.ass` com fonte, borda, cor, posição e quebra de linha controlada. Útil apenas se hard subtitles ou publicação externa forem prioridades.

---

## ASR, diarização e qualidade

### 11. Backend Transformers para ASR em português (`alta`, `médio`)

Adicionar backend baseado em Hugging Face Transformers/PyTorch como alternativa ao fluxo WhisperX/faster-whisper.

**Motivação:**

Alguns modelos ajustados para português brasileiro são publicados principalmente em formato Transformers. Isso pode ser útil para comparar modelos locais especializados em fala técnica, rápida ou espontânea.

**Estratégia:**

- Criar roteador de ASR por backend/modelo.
- Manter saída normalizada compatível com renderer, snapshots, `/rename`, exportações e `/summary`.
- Usar WhisperX/pyannote para diarização quando o backend Transformers não fornecer alinhamento suficiente.

### 12. Hint de número de falantes (`média`, `pequeno`)

Permitir informar `speakers=2` ou `speakers=2-4` junto do link/áudio, repassando `min_speakers`/`max_speakers` para a diarização.

### 13. Perfis de voz cross-vídeo (`baixa`, `grande`)

Persistir embeddings de falantes para sugerir nomes em vídeos futuros. Requer UX cuidadosa para evitar falsos positivos.

### 14. Tratamento de trechos musicais (`média`, `médio`)

Em vez de rejeitar vídeos parcialmente musicais, detectar trechos com música e transcrever apenas os trechos com fala, marcando `[música]` no Markdown.

### 15. Limpeza de áudio (`baixa`, `médio`)

Aplicar redução de ruído, normalização ou filtro passa-alta antes da transcrição. Deve ser validado empiricamente, pois pode piorar áudio já comprimido.

---

## Operação e engenharia

### 16. Webhook em vez de polling (`baixa`, `pequeno`)

Trocar polling por webhook para reduzir latência. Só faz sentido com HTTPS exposto e operação mais estável em servidor.

### 17. Backup automático do SQLite (`baixa`, `pequeno`)

Criar backups periódicos de `data/jobs.db` para `data/backups/jobs-YYYYMMDD.db`, mantendo últimas N cópias.

### 18. Logs estruturados em JSON opcional (`baixa`, `pequeno`)

Adicionar `LOG_FORMAT=json` para integração futura com observabilidade externa.

### 19. Docker Compose (`baixa`, `pequeno`)

Empacotar bot em container. Útil para servidor, mas menos prioritário no fluxo local com GPU/WSL2.

### 20. GitHub Actions CI (`baixa`, `pequeno`)

Rodar testes unitários e linters em PRs, sem depender de GPU ou modelos pesados.

---

## Itens deliberadamente não priorizados agora

- Perfis múltiplos de resumo (`short`, `academic`, `feynman`, etc.). O resumo único atual é suficiente; aumentar variações tende a criar complexidade de UX e testes sem ganho imediato claro.
- PDF automático. Markdown é mais auditável e mais adequado ao fluxo Obsidian/estudo.
- Modo multiusuário. O projeto permanece focado em uso privado de um único usuário autorizado.

---

## Critério para promover um item daqui ao escopo

Quando um item for escolhido:

1. Registrar a decisão no contrato funcional ou em patch note de escopo.
2. Definir comportamento esperado e limites operacionais.
3. Criar testes unitários e, quando cabível, testes de integração com fakes.
4. Implementar em pequenos passos.
5. Atualizar README, manual e `/help`.
6. Remover ou reclassificar o item neste documento.

Nada neste documento é promessa; tudo é memória de produto e engenharia.
