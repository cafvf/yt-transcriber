# Patch — summary reasoning_content guard

## Contexto

O LM Studio/Qwen3.5 pode retornar `content` vazio e preencher apenas `reasoning_content` quando o modelo continua em modo thinking. Isso fazia o bot responder que a LLM retornou conteúdo vazio.

## Alterações

- O payload OpenAI-compatible agora envia também `chat_template_kwargs={"enable_thinking": false}` quando `SUMMARY_DISABLE_THINKING=true`.
- O cliente detecta respostas com `content` vazio e `reasoning_content` preenchido.
- O erro agora orienta desativar **Enable Thinking** no LM Studio ou usar preset non-thinking.
- O bot continua sem usar `reasoning_content` como resumo, para evitar exposição de raciocínio interno.

## Validação

- Testes unitários cobrem o payload non-thinking.
- Testes unitários cobrem resposta apenas com `reasoning_content`.
