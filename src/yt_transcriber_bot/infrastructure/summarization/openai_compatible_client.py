"""Cliente mínimo para APIs OpenAI-compatible, incluindo LM Studio.

O LM Studio expõe um servidor local compatível com OpenAI. Para esta feature,
usamos ``GET /v1/models`` para validar o modelo selecionado e
``POST /v1/chat/completions`` para gerar o resumo.
"""

from __future__ import annotations

import json
import re
import socket
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any

from yt_transcriber_bot.application.ports.text_generation import (
    TextGenerationError as ChatCompletionError,
)
from yt_transcriber_bot.application.ports.text_generation import (
    TextGenerationRequest as ChatCompletionRequest,
)
from yt_transcriber_bot.application.ports.text_generation import (
    TextGenerationTimeoutError as ChatCompletionTimeoutError,
)
from yt_transcriber_bot.application.services.sanitization import sanitize_text

Transport = Callable[[str, Mapping[str, Any], Mapping[str, str], float], Mapping[str, Any]]
ModelsTransport = Callable[[str, Mapping[str, str], float], Mapping[str, Any]]
ErrorSanitizer = Callable[[str], str]


class OpenAICompatibleChatClient:
    """Cliente síncrono para ``/v1/chat/completions``.

    Parâmetros são compatíveis com LM Studio, Ollama/OpenAI-compatible e outros
    servidores locais que aceitam o formato de Chat Completions.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        timeout_s: float = 120.0,
        api_key: str = "",
        disable_thinking: bool = True,
        validate_model: bool = True,
        strict_model_match: bool = True,
        error_sanitizer: ErrorSanitizer | None = None,
        transport: Transport | None = None,
        models_transport: ModelsTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model.strip()
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout_s = timeout_s
        self._api_key = api_key.strip()
        self._disable_thinking = disable_thinking
        self._validate_model = validate_model
        self._strict_model_match = strict_model_match
        self._error_sanitizer = error_sanitizer or sanitize_text
        self._transport = transport or _urllib_transport
        self._models_transport = models_transport or _urllib_get_transport
        self._model_checked = False

    @property
    def model(self) -> str:
        return self._model

    def complete(self, request: ChatCompletionRequest) -> str:
        if self._validate_model:
            self._ensure_model_available()
        max_tokens = request.max_tokens if request.max_tokens is not None else self._max_tokens
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {
                    "role": "user",
                    "content": _maybe_add_no_think_prefix(
                        request.user_prompt, self._disable_thinking
                    ),
                },
            ],
            "temperature": self._temperature,
            "max_tokens": max(1, max_tokens),
            "stream": False,
        }
        # Qwen3.5/llama.cpp/LM Studio podem aceitar parâmetros não padrão
        # no corpo da requisição OpenAI-compatible para desabilitar thinking.
        # ``reasoning_effort="none"`` é enviado junto com ``enable_thinking=false``
        # para cobrir servidores/presets que expõem o controle como esforço de raciocínio.
        # A instrução textual, o prefixo /no_think e o pós-processamento abaixo
        # continuam como proteção caso o servidor ignore algum desses parâmetros.
        if self._disable_thinking:
            payload["enable_thinking"] = False
            payload["chat_template_kwargs"] = {"enable_thinking": False}
            payload["reasoning_effort"] = "none"
        headers = self._headers()
        try:
            data = self._transport(
                f"{self._base_url}/chat/completions",
                payload,
                headers,
                self._timeout_s,
            )
        except urllib.error.HTTPError as exc:
            detail = _read_http_error_body(exc)
            lowered = detail.lower()
            is_context_overflow = "exceeds" in lowered and "context" in lowered
            safe_detail = (
                "request exceeds the available context size"
                if is_context_overflow
                else "[OMITTED]"
                if detail
                else self._error_sanitizer(str(exc.reason))
            )
            hint = ""
            if is_context_overflow:
                hint = (
                    " Sugestão: reduza SUMMARY_MAX_INPUT_TOKENS, "
                    "SUMMARY_MAX_CHARS_PER_CHUNK ou SUMMARY_MAX_TOKENS; "
                    "ou aumente o contexto do modelo no LM Studio."
                )
            raise ChatCompletionError(
                "Falha HTTP ao chamar a API OpenAI-compatible. "
                f"Status: {exc.code}. Detalhe: {safe_detail}.{hint}"
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if _is_timeout_error(exc):
                raise ChatCompletionTimeoutError(
                    "Timeout ao chamar a API OpenAI-compatible. "
                    "A chamada demorou mais que SUMMARY_TIMEOUT_S. "
                    "O bot pode reduzir automaticamente o chunk atual, mas considere também diminuir "
                    "SUMMARY_MAX_INPUT_TOKENS/SUMMARY_MAX_CHARS_PER_CHUNK ou aumentar SUMMARY_TIMEOUT_S. "
                    f"Detalhe: {self._error_sanitizer(str(exc))}"
                ) from exc
            raise ChatCompletionError(
                "Falha ao chamar a API OpenAI-compatible. "
                "Verifique se o servidor do LM Studio está ativo e se SUMMARY_BASE_URL está correto. "
                f"Detalhe: {self._error_sanitizer(str(exc))}"
            ) from exc
        try:
            choices = data["choices"]
            message = choices[0]["message"]
            content = str(message.get("content", "")).strip()
            reasoning_content = str(message.get("reasoning_content", "")).strip()
            response_model = str(data.get("model", "")).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ChatCompletionError(
                "Resposta da LLM não tem formato Chat Completions válido."
            ) from exc
        if self._strict_model_match and response_model and response_model != self._model:
            raise ChatCompletionError(
                "O servidor OpenAI-compatible respondeu com um modelo diferente do configurado. "
                f"SUMMARY_MODEL='{self._model}', modelo usado pelo servidor='"
                f"{self._error_sanitizer(response_model)}'. "
                "Use exatamente o id listado por /v1/models em SUMMARY_MODEL ou desative "
                "SUMMARY_STRICT_MODEL_MATCH=false se aceitar aliases do servidor."
            )
        if self._disable_thinking:
            content = _strip_thinking_blocks(content).strip()
        if not content and reasoning_content:
            raise ChatCompletionError(
                "A LLM retornou apenas reasoning_content e deixou content vazio. "
                "Isso indica que o modelo ainda está em modo thinking. "
                "O reasoning_content não contém um resumo final confiável; em Qwen ele pode ser apenas o prompt/roteiro interno. "
                "No LM Studio, desative Enable Thinking no preset/modelo ou use um preset non-thinking; "
                "mantenha SUMMARY_DISABLE_THINKING=true. O bot não usa reasoning_content como resumo para "
                "evitar expor raciocínio interno e gerar artefatos incorretos."
            )
        if not content:
            raise ChatCompletionError("A LLM retornou conteúdo vazio.")
        return content

    def _ensure_model_available(self) -> None:
        if self._model_checked:
            return
        try:
            data = self._models_transport(
                f"{self._base_url}/models", self._headers(), self._timeout_s
            )
        except urllib.error.HTTPError as exc:
            detail = _read_http_error_body(exc)
            safe_detail = "[OMITTED]" if detail else self._error_sanitizer(str(exc.reason))
            raise ChatCompletionError(
                "Não consegui validar SUMMARY_MODEL em /v1/models. "
                f"Status: {exc.code}. Detalhe: {safe_detail}. "
                "Verifique SUMMARY_BASE_URL ou defina SUMMARY_VALIDATE_MODEL=false para pular a validação."
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ChatCompletionError(
                "Não consegui consultar /v1/models para validar SUMMARY_MODEL. "
                "Verifique se o LM Studio Server está ativo e acessível pelo WSL2/host. "
                f"Detalhe: {self._error_sanitizer(str(exc))}"
            ) from exc
        model_ids = _extract_model_ids(data)
        if self._model not in model_ids:
            shown_raw = ", ".join(model_ids[:20]) if model_ids else "<nenhum modelo retornado>"
            shown = self._error_sanitizer(shown_raw)
            raise ChatCompletionError(
                f"SUMMARY_MODEL='{self._model}' não está disponível em {self._base_url}/models. "
                f"Modelos disponíveis: {shown}. "
                "Use em SUMMARY_MODEL exatamente o id retornado por `curl $SUMMARY_BASE_URL/models`."
            )
        self._model_checked = True

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers


def _urllib_transport(
    url: str,
    payload: Mapping[str, Any],
    headers: Mapping[str, str],
    timeout_s: float,
) -> Mapping[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=dict(headers), method="POST")
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        raw = response.read().decode("utf-8")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ChatCompletionError("Resposta da LLM não é um objeto JSON.")
    return parsed


def _urllib_get_transport(
    url: str,
    headers: Mapping[str, str],
    timeout_s: float,
) -> Mapping[str, Any]:
    request = urllib.request.Request(url, headers=dict(headers), method="GET")
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        raw = response.read().decode("utf-8")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ChatCompletionError("Resposta de /v1/models não é um objeto JSON.")
    return parsed


def _is_timeout_error(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    reason = getattr(exc, "reason", None)
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return True
    message = str(exc).lower()
    return "timed out" in message or "timeout" in message


def _maybe_add_no_think_prefix(user_prompt: str, disable_thinking: bool) -> str:
    if not disable_thinking:
        return user_prompt
    # Qwen costuma aceitar /no_think como controle textual em vários templates.
    # Quando o template não honrar esse prefixo, os parâmetros estruturados e a
    # checagem de reasoning_content continuam protegendo o artefato final.
    return f"/no_think\n\n{user_prompt}"


def _strip_thinking_blocks(content: str) -> str:
    """Remove blocos explícitos de raciocínio de modelos Qwen/compatíveis.

    Alguns servidores ainda retornam ``<think>...</think>`` mesmo quando o
    parâmetro ``enable_thinking=false`` é enviado. Para resumos, esses blocos
    não são parte do artefato desejado e também aumentam ruído no Markdown.
    """

    cleaned = re.sub(r"(?is)<think>.*?</think>", "", content)
    cleaned = re.sub(r"(?is)^\s*thinking:\s*.*?(?=\n#{1,6}\s|\n\*\*|\nResumo|\Z)", "", cleaned)
    return cleaned.strip()


def _extract_model_ids(data: Mapping[str, Any]) -> list[str]:
    raw_models = data.get("data", [])
    ids: list[str] = []
    if isinstance(raw_models, list):
        for item in raw_models:
            if isinstance(item, Mapping):
                model_id = str(item.get("id", "")).strip()
                if model_id:
                    ids.append(model_id)
    return ids


def _read_http_error_body(exc: urllib.error.HTTPError) -> str:
    try:
        raw = exc.read().decode("utf-8", errors="replace")
    except Exception:  # pragma: no cover - defensivo
        return ""
    if not raw:
        return ""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return raw[:1000]
    if isinstance(parsed, dict):
        error = parsed.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if message:
                return str(message)[:1000]
        if error:
            return str(error)[:1000]
        message = parsed.get("message")
        if message:
            return str(message)[:1000]
    return raw[:1000]


__all__ = [
    "ChatCompletionError",
    "ChatCompletionRequest",
    "ChatCompletionTimeoutError",
    "OpenAICompatibleChatClient",
]
