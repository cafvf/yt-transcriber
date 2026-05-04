# Patch notes — testes menos acoplados aos defaults de modelos

Data: 2026-05-04

## Contexto

Após corrigir a resolução do `.env`, a suíte passou a enxergar configurações locais
como `WHISPER_MODEL_PT` e `SUMMARY_MODEL`. Isso expôs um acoplamento indevido dos
testes a nomes específicos de modelos default.

## Alterações

- Os testes de configuração agora verificam que os campos de modelo Whisper e LLM
  estão definidos, em vez de exigir nomes específicos.
- Os testes de seleção automática por idioma verificam que o runtime usa o modelo
  configurado para `pt` ou `en`, em vez de depender do default histórico.
- A suíte continua isolada de `.env` local por padrão, para evitar que segredos ou
  preferências pessoais alterem resultados de testes unitários.
- `.env.example` continua proibido como configuração runtime.

## Intenção

Preservar o contrato funcional relevante sem transformar escolhas operacionais de
modelo em API pública imutável.
