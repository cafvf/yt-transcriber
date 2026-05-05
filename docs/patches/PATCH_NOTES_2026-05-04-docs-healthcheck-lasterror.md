# Patch notes — documentação de observabilidade operacional

Data: 2026-05-04

## Resumo

Atualiza a documentação principal para refletir que `/healthcheck` e `/lasterror` foram implementados e testados manualmente.

## Alterações

- README atualizado com status implementado de observabilidade operacional.
- Contrato funcional atualizado com os comandos `/healthcheck` e `/lasterror`.
- Manual de uso expandido com comportamento, escopo e limitações dos comandos.
- Manual de instalação atualizado com diagnóstico pós-instalação.
- Arquitetura documenta `data/logs/operational_errors.jsonl`.
- Roadmap remove observabilidade da lista de futuras e promove `/search <texto>` como próxima prioridade.
- Glossário/ADRs registra a decisão arquitetural de observabilidade operacional.

## Observações

`/healthcheck` é triagem operacional; não substitui logs completos. `/lasterror` depende de registros persistidos em jobs falhos ou no arquivo JSONL de erros operacionais.
