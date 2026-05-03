# Patch — Documentação WSL2 + LM Studio

Atualiza a documentação de uso e instalação para deixar explícito que, quando o bot roda no WSL2 e o LM Studio roda no Windows, recomenda-se habilitar o Mirrored Mode do WSL2.

## Alterações

- Adicionada seção no manual de uso sobre LM Studio no Windows acessado a partir do WSL2.
- Adicionada seção de instalação `9.2 WSL2 + LM Studio no Windows: habilitar Mirrored Mode`.
- Atualizado `.env.example` para usar `http://127.0.0.1:1234/v1` como base URL recomendada.
- Incluído teste com `curl http://127.0.0.1:1234/v1/models` dentro do WSL2.

## Motivação

Sem mirrored networking, o WSL2 em modo NAT pode não alcançar o servidor local do LM Studio exposto no Windows por `localhost`, resultando em `Connection refused` no comando `/summary`.
