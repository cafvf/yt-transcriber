# Patch notes — 2026-05-03 — idioma explícito e feedback no Telegram

## Mudanças

- Adicionado suporte a idioma informado pelo usuário por mensagem:
  - `https://youtube.com/watch?v=... --lang pt`
  - `https://youtube.com/watch?v=... --lang en`
  - `/pt <link>`
  - `/en <link>`
  - `/transcribe <link> --lang pt`
  - `/redo <link> --lang pt`
- O idioma informado é usado para:
  - escolher o modelo quando `WHISPER_MODEL=auto`;
  - selecionar legendas do YouTube no idioma desejado;
  - forçar o WhisperX com `language=<idioma>` quando houver transcrição por áudio.
- O Telegram agora mostra o idioma na fila e na mensagem final:
  - `idioma informado pelo usuário`;
  - `inferido dos metadados`;
  - `detectado pelo ASR`;
  - `legenda manual/automática do YouTube`.
- `WHISPER_MODEL_PT`, `WHISPER_MODEL_EN`, `WHISPER_MODEL_DEFAULT` e `WHISPER_MODEL` agora aceitam:
  - modelos padrão (`small`, `medium`, `large-v3` etc.);
  - repositórios Hugging Face, como `inesc-id/WhisperLv3-X-PT-All`;
  - caminhos locais.

## Uso recomendado para testar o INESC

```env
WHISPER_MODEL=auto
WHISPER_MODEL_PT=inesc-id/WhisperLv3-X-PT-All
WHISPER_MODEL_EN=medium
WHISPER_MODEL_DEFAULT=medium
```

Para forçar português em um vídeo específico:

```text
/pt https://www.youtube.com/watch?v=...
```

ou:

```text
https://www.youtube.com/watch?v=... --lang pt
```

## Observação

O idioma dos metadados do YouTube pode ser usado para escolher legendas/modelo, mas ele não é rotulado como “detectado pelo ASR”. Quando o áudio é transcrito sem `--lang`, o idioma final exibido como “detectado pelo ASR” vem do WhisperX.
