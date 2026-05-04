# Manual de Uso

Este manual descreve, da perspectiva do **usuário final**, como interagir com o bot no dia-a-dia. Para instalação, ver [`04-manual-de-instalacao.md`](./04-manual-de-instalacao.md).

---

## 1. Primeiros passos

### 1.1 Iniciar conversa
1. No Telegram, abra a conversa com o bot (busca por `@SeuBotUsername`).
2. Envie `/start`.
3. O bot deve responder com uma saudação confirmando que está vivo. Se não responder em alguns segundos:
   - Verifique no terminal/serviço se o bot está rodando.
   - Verifique se o `user_id` configurado em `TELEGRAM_ALLOWED_USER_ID` é o seu (envie qualquer mensagem para `@userinfobot` para descobrir o seu ID).

### 1.2 Enviar primeiro link
Cole qualquer link do YouTube (formato `https://www.youtube.com/watch?v=...` ou `https://youtu.be/...`) numa mensagem. O bot:
1. Confirma o recebimento.
2. Mostra uma mensagem de progresso (que será editada conforme o processamento avança).
3. Ao final, envia o arquivo de áudio (`.ogg`) e a transcrição (`.md`).

> **Atenção**: na primeira execução, o bot vai baixar 2–3 GB de modelos (Whisper + pyannote). O download é informado no chat. Esse passo só ocorre uma vez.

---

## 2. Comandos disponíveis

Esta seção descreve o comportamento **implementado nesta versão**.

### `/start`
Saudação inicial. Use para verificar se o bot está respondendo.

### `/help`
Mostra a lista resumida de comandos implementados.

### `/status`
Mostra o job em processamento e os links pendentes na fila. Se não houver nada em andamento, responde que o bot está pronto para receber links.

### `/cancel`
- Durante processamento: sinaliza cancelamento do job em curso.
- Durante diálogo de `/rename`: aborta o diálogo sem aplicar mudanças.
- Sem nada em andamento: responde `Nada para cancelar.`

### `/list`
Lista as últimas transcrições registradas para o usuário autorizado, atualmente com limite de 10 registros. A saída inclui `video_id`, status e horário de requisição.

Exemplo de saída:

```text
Últimas transcrições:
• dQw4w9WgXcQ [completed] — 2026-05-01 12:00
```

### `/last [n]`
Reenvia o arquivo Markdown da n-ésima transcrição concluída, usando a numeração mostrada por `/list`. Sem índice, usa a transcrição mais recente. Se o arquivo tiver sido removido ou movido, o bot avisa que o Markdown não está mais disponível.

### `/export json|srt|vtt [n]`
Exporta artefatos derivados da n-ésima transcrição concluída, sem reprocessar áudio, WhisperX ou diarização. Sem índice, exporta a transcrição mais recente.

Exemplos:

```text
/export json
/export srt 2
/export vtt 3
```

Formatos gerados:

- `json`: metadados, contexto de execução, aliases de falantes e segmentos estruturados.
- `srt`: legenda SubRip com timestamps e nome exibido do falante.
- `vtt`: legenda WebVTT com timestamps e nome exibido do falante.

Se você já aplicou `/rename`, os nomes/mesclagens de falantes salvos no job são usados nos arquivos exportados.

Atalhos equivalentes:

```text
/json [n]
/srt [n]
/vtt [n]
```

### `/video_subs [n]`
Gera e envia um MP4 com a legenda adicionada como **faixa selecionável**, sem queimar a legenda na imagem. O índice `[n]` segue a mesma numeração de `/list`; sem índice, usa a transcrição mais recente.

Exemplos:

```text
/video_subs
/video_subs 2
```

Limites operacionais padrão:

- duração máxima: 30 minutos;
- tamanho máximo do vídeo final: 200 MB.

Esses limites podem ser ajustados no `.env`:

```env
MAX_VIDEO_SUBTITLES_DURATION_MIN=30
MAX_VIDEO_SUBTITLES_SIZE_MB=200
VIDEO_EXPORTS_DIR_NAME=video_exports
```

O bot usa o snapshot da transcrição para gerar um `.srt`, baixa um MP4 compatível e faz o mux da legenda com `ffmpeg` como `mov_text`.

### `/redo <link>`
Reprocessa explicitamente um link do YouTube como um **novo job** na fila.

Exemplo:

```text
/redo https://youtu.be/dQw4w9WgXcQ
```

Comportamento atual:

- exige URL do YouTube na própria mensagem;
- não aceita apenas `video_id` isolado;
- não pede confirmação inline;
- não mostra diff de configuração;
- não sobrescreve o job anterior; gera novo registro e novos artefatos.

A confirmação inline com diff de configuração permanece como melhoria futura.

### `/rename [n]`
Inicia o diálogo para renomear falantes da n-ésima transcrição concluída, usando a numeração mostrada por `/list`. Sem índice, usa a transcrição mais recente. O bot mostra botões inline para cada falante e também aceita um mapeamento textual em lote:

```text
SPEAKER_00=João, SPEAKER_01=Maria
```

Também aceita uma entrada por linha:

```text
SPEAKER_00=João
SPEAKER_01=Maria
```

Ao receber um mapeamento válido, o bot carrega o snapshot JSON da última transcrição, re-renderiza o Markdown com os nomes informados, atualiza o job para auditoria e reenvia o arquivo `.md`.

Se a diarização separou a mesma pessoa em mais de um label, use o **mesmo nome** para mesclar os falantes na versão final do Markdown:

```text
SPEAKER_00=Christiano, SPEAKER_02=Christiano
```

Nesse caso, o resumo da diarização agrega o tempo de fala dos dois labels e a seção de transcrição deixa de repetir cabeçalhos quando esses labels aparecerem em sequência.

### `/clearcache`
Remove arquivos dentro do diretório `models_dir` configurado. Por segurança, a operação é recusada se o diretório informado ao adaptador não for exatamente o diretório de modelos configurado em `AppSettings.models_dir`, ou se parecer amplo demais.

Na próxima transcrição que exigir modelos ausentes, eles precisarão ser baixados novamente.

### Comandos de fila

- `/queue` ou `/fila`: mostra a fila completa.
- `/clearqueue`, `/cancelqueue` ou `/limparfila`: remove apenas jobs pendentes.
- `/cancelall` ou `/cancelartudo`: sinaliza cancelamento do job atual e remove pendentes.

### Comandos planejados, mas não implementados nesta versão

- `/lasterror`
- `/redo` com confirmação inline e diff de configuração
- botões inline como `[Refazer com WhisperX]`

## 3. Cenários comuns

### 3.1 Vídeo com auto-dublagem
Vídeos rotulados como *Auto-dubbed* (ex.: o vídeo tem áudios em vários idiomas gerados automaticamente) são processados a partir da **faixa original**. O bot avisa no chat:
```
[1/7] Baixando metadados... ✓ "Título" (5min 30s, PT)
   Vídeo possui múltiplas faixas (PT, EN, ES). Baixando a original (PT).
```

### 3.2 Vídeo com legendas no YouTube
Quando o YouTube já oferece legendas no idioma original, o bot economiza tempo de transcrição:

- **Legenda manual**:
  ```
  [4/7] Verificando legendas... ✓ Encontrada (manual, PT). Pulando WhisperX.
  ```
  O `.md` é gerado a partir da legenda manual + diarização.

- **Legenda auto-gerada**:
  ```
  [4/7] Verificando legendas... ✓ Encontrada (auto-gerada, PT). Pulando WhisperX.
  ```
  O `.md` marca a origem como legenda auto-gerada do YouTube. Caso a qualidade não seja suficiente, use `/redo <link>` para reprocessar explicitamente.

### 3.3 Vídeo rejeitado
O bot pode rejeitar vídeos por vários motivos. Mensagens típicas:
- `"Vídeo dura 3h 24min, acima do limite de 3h. Job descartado."`
- `"Idioma detectado: alemão (de). Apenas pt e en são suportados. Job descartado."`
- `"Vídeo é majoritariamente música (78% sem fala). Job descartado."`
- `"Vídeo restrito a membros. Configure cookies (veja docs/04-manual-de-instalacao.md). Job descartado."`
- `"Vídeo privado, removido ou indisponível. Job descartado."`

### 3.4 Link já transcrito
Nesta versão, reenviar o mesmo link cria uma nova entrada na fila; não há deduplicação automática nem botões inline de confirmação. Para deixar a intenção explícita, prefira usar `/redo <link>` quando quiser reprocessar um vídeo já tratado.

### 3.5 Falha durante a transcrição
Se ocorrer um erro (OOM, crash, etc.), o bot tenta uma vez com modelo menor em CPU:
```
[5/7] Transcrevendo... ✗ Erro: out of memory (medium, cuda).
       Retentando com small em cpu...
[5/7] Transcrevendo... ✓
```

Se a retentativa também falhar:
```
✗ Falha persistente na transcrição. Job marcado como falho.
Para detalhes técnicos: /lasterror
```

### 3.6 Bot reiniciou no meio de um processamento
Quando você volta a ter contato:
```
Voltei online. Tinha 2 jobs em fila e 1 em processamento (interrompido).
O job interrompido foi marcado como falho. Reprocessar?

[Reprocessar]  [Não]
```

---

## 4. Estrutura do arquivo `.md` recebido

Exemplo abreviado:

```markdown
# Transcrição — How to remember EVERYTHING you've ever read?

**URL**: https://www.youtube.com/watch?v=j2p8p7cg0q8
**Canal**: Amado Mundo
**Duração**: 00:05:30
**Data do vídeo**: 2026-04-30
**Data da transcrição**: 2026-05-01 14:32 (GMT-3)
**Modelo**: WhisperX 3.8.5 / pyannote 3.1
**Idioma detectado**: pt (confiança: 0.97)
**Origem da transcrição**: WhisperX
**Falantes identificados**: 2

---

## Resumo da diarização
- **SPEAKER_00**: 02min 08s (39%)
- **SPEAKER_01**: 03min 22s (61%)

---

## Transcrição

### [00:00:00 — 00:00:14] SPEAKER_00
Olá pessoal, hoje estou aqui com o Eduardo Giannetti...

### [00:00:14 — 00:00:48] SPEAKER_01
Obrigado pelo convite, é um prazer estar aqui novamente...
```

Após `/rename` aplicado:

```markdown
### [00:00:00 — 00:00:14] Entrevistador
Olá pessoal, hoje estou aqui com o Eduardo Giannetti...

### [00:00:14 — 00:00:48] Eduardo Giannetti
Obrigado pelo convite, é um prazer estar aqui novamente...
```

---

## 5. Boas práticas

### 5.1 Para melhor qualidade
- Use modelos maiores (`medium`, `large-v3`) se sua GPU comportar. Configure via `WHISPER_MODEL`.
- Prefira vídeos com áudio limpo (sem ruído de fundo intenso).
- Para entrevistas/podcasts: a diarização funciona melhor com microfones separados (cada falante em sua trilha de captura).

### 5.2 Para economizar tempo
- Aproveite as legendas do YouTube quando estiverem disponíveis (o bot faz isso sozinho).
- Para vídeos longos, considere rodar em GPU se disponível.

### 5.3 Para gerenciar disco
- A política FIFO mantém só os 5 últimos jobs com áudio. MDs ficam para sempre.
- Use `/clearcache` se os modelos baixados estiverem ocupando muito disco.
- Os MDs são pequenos (KBs), não se preocupe com eles.

---

## 6. Troubleshooting do dia-a-dia

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Bot não responde | Processo parado | Verifique se o bot está rodando (terminal ou `systemctl status`). |
| Bot responde mas ignora seu link | `user_id` errado em `TELEGRAM_ALLOWED_USER_ID` | Confirme seu ID com `@userinfobot` e ajuste a env. |
| Erro "ffmpeg not found" no startup | ffmpeg não instalado | `sudo dnf install ffmpeg` ou `sudo apt install ffmpeg`. |
| Erro "401 Unauthorized" do HF | `HF_TOKEN` ausente, errado ou termos pyannote não aceitos | Confirme env e aceite os termos (links em `04-manual-de-instalacao.md`). |
| Erro "No module named 'whisperx'", "No module named 'torch'" ou "No module named 'pyannote'" | Ambiente criado sem a stack de ML | Rode `uv sync` na versão 0.1.2 ou superior. Em versões antigas, rode `uv sync --extra ml`. Depois reinicie o bot. |
| Transcrição muito lenta | Rodando em CPU sem necessidade | Configure GPU (`DEVICE=cuda`) ou modelo menor (`WHISPER_MODEL=small`). |
| Diarização cria muitos falantes para 1 pessoa | Variação acústica acentuada | Use `/rename` atribuindo o mesmo nome a múltiplos labels. |
| Mensagem "Vídeo é majoritariamente música" em vídeo de palestra | Áudio com música de abertura longa | Não é tratado no MVP; veja [funcionalidades futuras](./06-funcionalidades-futuras.md). |
| Erros não rastreados | — | Use `/lasterror` para ver o stack trace e cole no log do projeto. |


## Política de modelo por idioma

A configuração recomendada é deixar o bot escolher o modelo automaticamente:

```env
WHISPER_MODEL=auto
WHISPER_MODEL_PT=large-v3
WHISPER_MODEL_EN=medium
WHISPER_MODEL_DEFAULT=medium
```

Assim, vídeos em português usam `large-v3`, vídeos em inglês usam `medium` e vídeos com idioma indeterminado usam `medium`.

Para sobrescrever a política e usar sempre o mesmo modelo, defina, por exemplo:

```env
WHISPER_MODEL=medium
```

## Idioma por vídeo

Por padrão, o bot tenta inferir o idioma a partir dos metadados do YouTube e, quando transcreve por áudio, o ASR também pode detectar o idioma. Para vídeos em que você já sabe o idioma, é possível informar explicitamente:

```text
https://www.youtube.com/watch?v=... --lang pt
https://www.youtube.com/watch?v=... --lang en
/pt https://www.youtube.com/watch?v=...
/en https://www.youtube.com/watch?v=...
/transcribe https://www.youtube.com/watch?v=... --lang pt
/redo https://www.youtube.com/watch?v=... --lang pt
```

Quando o idioma é informado manualmente, ele tem prioridade sobre os metadados do YouTube. Isso afeta a escolha do modelo em `WHISPER_MODEL=auto`, a busca por legendas do YouTube e o carregamento do WhisperX com idioma explícito.

O Telegram informa o idioma durante a fila e na conclusão, distinguindo entre idioma informado pelo usuário, idioma inferido dos metadados, idioma detectado pelo ASR e idioma vindo de legenda do YouTube.

## Referência rápida de comandos

O comando `/help` no Telegram deve listar todos os comandos públicos atuais. A lista está agrupada por uso:

### Entrada e idioma

- `/transcribe <link> [--lang pt|en]` — enfileira explicitamente um link para transcrição.
- `/pt <link>` — transcreve informando português como idioma do vídeo.
- `/en <link>` — transcreve informando inglês como idioma do vídeo.
- `/redo <link> [--lang pt|en]` — reprocessa um vídeo.

### Estado, fila e cancelamento

- `/status` — mostra o job atual e o estado operacional.
- `/queue` ou `/fila` — mostra a fila completa.
- `/clearqueue`, `/cancelqueue` ou `/limparfila` — remove apenas os pendentes.
- `/cancel` — solicita cancelamento do job atual.
- `/cancelall` ou `/cancelartudo` — cancela o atual e remove pendentes.

### Histórico e revisão

- `/list` — lista transcrições concluídas, com título e horário quando disponíveis.
- `/last [n]` — reenvia a n-ésima transcrição concluída.
- `/rename [n]` — abre botões para renomear ou mesclar falantes.

### Exportações

- `/export json [n]`, `/json [n]` — exporta JSON estruturado.
- `/export srt [n]`, `/srt [n]` — exporta legenda SRT.
- `/export vtt [n]`, `/vtt [n]` — exporta legenda VTT.
- `/video_subs [n]` ou `/videosubs [n]` — envia MP4 com legenda selecionável.

### Manutenção

- `/start` — mostra a mensagem inicial.
- `/help` — mostra a referência de comandos.
- `/clearcache` — apaga modelos baixados no diretório de cache configurado.


## Sumarização com LM Studio

O comando `/summary [n]` gera um arquivo Markdown derivado da transcrição já concluída, sem reprocessar áudio, WhisperX ou diarização.

Exemplos:

```text
/summary
/summary 2
```

A integração usa uma API compatível com OpenAI, como o servidor local do LM Studio. Configuração típica no `.env`:

```env
SUMMARY_BACKEND=openai_compatible
SUMMARY_BASE_URL=http://127.0.0.1:1234/v1
SUMMARY_MODEL=qwen3.5-9b
SUMMARY_TEMPERATURE=0.2
SUMMARY_MAX_TOKENS=1024
SUMMARY_MAX_CHARS_PER_CHUNK=4000
SUMMARY_MAX_INPUT_TOKENS=2500
SUMMARY_CHARS_PER_TOKEN=2.0
SUMMARY_OUTPUT_LANGUAGE=auto
SUMMARY_DISABLE_THINKING=true
SUMMARY_VALIDATE_MODEL=true
SUMMARY_STRICT_MODEL_MATCH=true
```

Antes de usar, abra o LM Studio, carregue o modelo desejado e inicie o servidor local. O bot chama `GET /v1/models` para validar o `SUMMARY_MODEL` e depois `POST /v1/chat/completions`.

Use em `SUMMARY_MODEL` exatamente o `id` retornado por:

```bash
curl http://127.0.0.1:1234/v1/models
```

Se o LM Studio responder com um modelo diferente daquele configurado, o bot falha com diagnóstico claro. Isso evita resumos pouco reprodutíveis quando o servidor usa outro modelo carregado. Se você quiser aceitar aliases do servidor, defina `SUMMARY_STRICT_MODEL_MATCH=false`; se quiser pular a validação em `/v1/models`, defina `SUMMARY_VALIDATE_MODEL=false`.

`SUMMARY_DISABLE_THINKING=true` é recomendado para resumos. Nessa configuração, o bot envia uma instrução de resposta direta, inclui `enable_thinking=false` e `chat_template_kwargs={"enable_thinking": false}` no corpo da chamada OpenAI-compatible e remove blocos `<think>...</think>` caso o servidor ainda os retorne.

Se o LM Studio retornar `content=""` e preencher apenas `reasoning_content`, o bot rejeita a resposta e mostra um diagnóstico. Isso indica que o modelo/preset ainda está em modo thinking. Nesse caso, desative **Enable Thinking** no LM Studio ou use um preset non-thinking; o bot não transforma `reasoning_content` em resumo para não expor raciocínio interno nem gerar artefatos incorretos.

Para confirmar que o `.env` está sendo lido pela mesma configuração usada pelo bot, rode na raiz do projeto:

```bash
uv run python scripts/config/print_effective_settings.py
```

Confira principalmente `summary_base_url`, `summary_model`, `summary_max_input_tokens` e `summary_disable_thinking`.

Para modelos com contexto de 4096 tokens, como alguns presets locais do Qwen, mantenha `SUMMARY_MAX_INPUT_TOKENS` entre `2000` e `2500`. O bot usa esse valor para dividir a transcrição antes de chamar a LLM. Se o LM Studio registrar erro semelhante a `request (...) exceeds the available context size (4096 tokens)`, reduza primeiro:

```env
SUMMARY_MAX_INPUT_TOKENS=2000
SUMMARY_MAX_CHARS_PER_CHUNK=3000
SUMMARY_MAX_TOKENS=768
```

### LM Studio rodando no Windows e bot rodando no WSL2

Se o LM Studio estiver aberto no **Windows** e o bot estiver rodando dentro do **WSL2**, habilite o **Mirrored Mode** do WSL2. Sem isso, `SUMMARY_BASE_URL=http://127.0.0.1:1234/v1` ou `http://127.0.0.1:1234/v1` pode resultar em `Connection refused`, porque o `localhost` do WSL2 não alcança necessariamente o servidor local do Windows no modo NAT padrão.

No Windows, crie ou edite o arquivo:

```text
%USERPROFILE%\.wslconfig
```

com:

```ini
[wsl2]
networkingMode=mirrored
dnsTunneling=true
autoProxy=true
```

Depois reinicie o WSL a partir do PowerShell:

```powershell
wsl --shutdown
```

Reabra o terminal WSL2, inicie o servidor do LM Studio no Windows e teste **dentro do WSL2**:

```bash
curl http://127.0.0.1:1234/v1/models
```

Se retornar JSON com modelos, mantenha no `.env`:

```env
SUMMARY_BASE_URL=http://127.0.0.1:1234/v1
```

Use `localhost` apenas se também funcionar no teste com `curl`. Em caso de bloqueio, verifique o firewall do Windows e se o LM Studio está realmente com o servidor local iniciado.
