# Patch notes — compatibilidade de diarização

Correções aplicadas:

- trocada a autenticação primária de WhisperX/pyannote para `token=...`, mantendo fallback para `use_auth_token=...` em versões antigas;
- atualizado o fallback direto do pyannote para `pyannote/speaker-diarization-community-1`, compatível com `pyannote.audio` 4.x;
- adicionado parser compatível com saídas antigas (`Annotation.itertracks`) e novas (`output.speaker_diarization` / `output.exclusive_speaker_diarization`);
- adicionados testes de regressão para backends reais com APIs recentes.

Observação operacional: é necessário aceitar os termos do modelo `pyannote/speaker-diarization-community-1` no Hugging Face e usar um `HF_TOKEN` com permissão de leitura.
