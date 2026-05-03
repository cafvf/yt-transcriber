"""Cliente mínimo para APIs OpenAI-compatible, incluindo LM Studio.

O LM Studio expõe um servidor local compatível com OpenAI. Para esta feature,
usamos apenas ``POST /v1/chat/completions`` para evitar dependência adicional
no SDK oficial da OpenAI.
"""

from __future__ import annotations

import json
import re
import socket
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any


class ChatCompletionError(RuntimeError):
    """Falha ao solicitar ou interpretar uma resposta da LLM."""


Transport = Callable[[str, Mapping[str, Any], Mapping[str, str], float], Mapping[str, Any]]


@dataclass(frozen=True)
class ChatCompletionRequest:
    """Entrada normalizada para uma chamada de chat completion."""

    system_prompt: str
    user_prompt: str


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
        transport: Transport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout_s = timeout_s
        self._api_key = api_key.strip()
        self._disable_thinking = disable_thinking
        self._transport = transport or _urllib_transport

    @property
    def model(self) -> str:
        return self._model

    def complete(self, request: ChatCompletionRequest) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "stream": False,
        }
        # Qwen3.5/llama.cpp/LM Studio podem aceitar esse parâmetro não padrão
        # no corpo da requisição OpenAI-compatible para desabilitar thinking.
        # A instrução textual e o pós-processamento abaixo continuam como
        # proteção caso o servidor ignore o parâmetro.
        if self._disable_thinking:
            payload["enable_thinking"] = False
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        try:
            data = self._transport(
                f"{self._base_url}/chat/completions",
                payload,
                headers,
                self._timeout_s,
            )
        except urllib.error.HTTPError as exc:
            detail = _read_http_error_body(exc)
            hint = ""
            lowered = detail.lower()
            if "exceeds" in lowered and "context" in lowered:
                hint = (
                    " Sugestão: reduza SUMMARY_MAX_INPUT_TOKENS, "
                    "SUMMARY_MAX_CHARS_PER_CHUNK ou SUMMARY_MAX_TOKENS; "
                    "ou aumente o contexto do modelo no LM Studio."
                )
            raise ChatCompletionError(
                "Falha HTTP ao chamar a API OpenAI-compatible. "
                f"Status: {exc.code}. Detalhe: {detail or exc.reason}.{hint}"
            ) from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
            raise ChatCompletionError(
                "Falha ao chamar a API OpenAI-compatible. "
                "Verifique se o servidor do LM Studio está ativo e se SUMMARY_BASE_URL está correto. "
                f"Detalhe: {exc}"
            ) from exc
        try:
            choices = data["choices"]
            message = choices[0]["message"]
            content = str(message.get("content", "")).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ChatCompletionError("Resposta da LLM não tem formato Chat Completions válido.") from exc
        if self._disable_thinking:
            content = _strip_thinking_blocks(content).strip()
        if not content:
            raise ChatCompletionError("A LLM retornou conteúdo vazio.")
        return content


def _urllib_transport(
    url: str,
    payload: Mapping[str, Any],
    headers: Mapping[str, str],
    timeout_s: float,
) -> Mapping[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=dict(headers), method="POST")
    with urllib.request.urlopen(request, timeout=timeout_s) as response:  # noqa: S310 - URL local/configurada pelo usuário
        raw = response.read().decode("utf-8")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ChatCompletionError("Resposta da LLM não é um objeto JSON.")
    return parsed


def _strip_thinking_blocks(content: str) -> str:
    """Remove blocos explícitos de raciocínio de modelos Qwen/compatíveis.

    Alguns servidores ainda retornam ``<think>...</think>`` mesmo quando o
    parâmetro ``enable_thinking=false`` é enviado. Para resumos, esses blocos
    não são parte do artefato desejado e também aumentam ruído no Markdown.
    """

    cleaned = re.sub(r"(?is)<think>.*?</think>", "", content)
    cleaned = re.sub(r"(?is)^\s*thinking:\s*.*?(?=\n#{1,6}\s|\n\*\*|\nResumo|\Z)", "", cleaned)
    return cleaned.strip()


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
