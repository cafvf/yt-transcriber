# Auditoria e mapa de atualização da documentação

Data de referência: 2026-07-12. Este documento registra a reconciliação entre
os guias do repositório e o código em `src/yt_transcriber_bot/`. Ele não é um
manual de operação; os guias atuais são o README e os documentos 01 a 11.

## Escopo

Foram revisados `README.md`, `.env.example`, `pyproject.toml` e os documentos
canônicos em `docs/01` a `docs/11`. Notas em `docs/patches/`, relatórios em
`docs/gate-reports/` e evidências em `ops-evidence/` são registros históricos:
não foram reescritos para não alterar a evidência que descrevem.

## Pontos corrigidos

| Tema | Situação encontrada | Regra documentada agora |
|---|---|---|
| Entrada Telegram | Alguns textos descreviam apenas URLs do YouTube. | O bot aceita URL do YouTube, áudio, voz e documento de áudio; mídia Telegram é privada e não recebe identidade YouTube. |
| Pipeline | Diagramas tratavam o fluxo YouTube como universal. | YouTube pode consultar metadados/legendas antes do ASR; Telegram começa na mídia já adquirida e usa o sufixo comum de conversão, ASR, diarização e renderização. |
| `/redo` | Havia referências ao comando como futuro. | Ele já cria um novo job imediatamente; confirmação e comparação de configuração continuam futuras. |
| `/last` | Um contrato dizia que o áudio também era reenviado. | O comando reenvia somente o Markdown salvo. |
| Retenção | A documentação prometia apagar todos os artefatos de um job juntos. | A política FIFO remove mídia original/conversão/log associado dos jobs antigos e preserva Markdown e snapshot de segmentos para histórico e renomeação. |
| Recovery | A fila em memória era confundida com ausência de recuperação. | A fila é em memória; `jobs` no SQLite guarda o payload mínimo. Pendentes são re-enfileirados; estados interrompidos são reconciliados, sem retomar ASR no meio. |
| Segurança | Os limites de mensagens de erro e dados privados estavam dispersos. | Somente um usuário Telegram configurado é atendido; mensagens, auditoria e diagnóstico usam sanitização e artefatos permanecem locais. |
| Configuração | A seleção do `.env` e os limites de mídia não estavam centralizados. | Variáveis de ambiente prevalecem; `YT_TRANSCRIBER_ENV_FILE` pode apontar o arquivo; `.env.example` nunca é carregado como configuração real. |

## Critério de leitura

Quando houver conflito entre um guia e o código, o código e seus testes são a
fonte de verdade. Alterações de comportamento devem atualizar, no mínimo,
README, contrato funcional, arquitetura, manual de uso e instalação quando
afetados.
