# Patch notes — UI queue/list/rename fixes (2026-05-03)

Correções aplicadas a partir de regressões observadas no Telegram:

- movidos todos os `PATCH_NOTES*.md` da raiz para `docs/patches/`;
- `/help` atualizado com todos os comandos atuais;
- `/queue`, `/fila`, `/clearqueue`, `/cancelqueue`, `/cancelall` e aliases registrados no entrypoint real;
- fallback textual para comandos que cheguem fora dos `CommandHandler`;
- `/list` agora tenta mostrar título do vídeo a partir do snapshot/metadados e horário de execução;
- `/rename [n]` agora envia botões inline para renomear/mesclar falantes;
- callbacks de renomeação registrados com `CallbackQueryHandler`;
- `/cancel` agora envia confirmação final quando o job encerra cancelado;
- testes adicionados para cobrir os comportamentos acima.
