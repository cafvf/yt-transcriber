# Patch 2026-05-03 — Mesclagem manual de falantes no Markdown

## Contexto

A diarização pode superestimar a quantidade de pessoas, dividindo a mesma voz em `SPEAKER_00`, `SPEAKER_02` etc. O `/rename` já aceitava atribuir o mesmo nome a múltiplos labels, mas o Markdown ainda era renderizado como se fossem falantes distintos.

## Alterações

- O renderer agora usa o **nome exibido** para agrupar blocos consecutivos, não apenas o label cru da diarização.
- O resumo de diarização agora agrega duração por nome exibido.
- O cabeçalho mantém o número original de falantes detectados e, quando houver mesclagem, adiciona o número após renomeação/mesclagem.
- Documentação atualizada com exemplo de uso: `SPEAKER_00=Christiano, SPEAKER_02=Christiano`.

## Exemplo

Entrada no diálogo `/rename`:

```text
SPEAKER_00=Christiano, SPEAKER_02=Christiano, SPEAKER_01=Entrevistador
```

Resultado: `SPEAKER_00` e `SPEAKER_02` aparecem como uma única pessoa no resumo e em blocos consecutivos do Markdown.
