from __future__ import annotations

from typing import Any, Mapping

import pytest

from yt_transcriber_bot.infrastructure.summarization.openai_compatible_client import (
    ChatCompletionError,
    ChatCompletionRequest,
    OpenAICompatibleChatClient,
)


def test_openai_compatible_client_posts_chat_completion_payload() -> None:
    calls: list[tuple[str, Mapping[str, Any], Mapping[str, str], float]] = []

    def transport(
        url: str, payload: Mapping[str, Any], headers: Mapping[str, str], timeout_s: float
    ) -> Mapping[str, Any]:
        calls.append((url, payload, headers, timeout_s))
        return {"choices": [{"message": {"content": "Resumo gerado"}}]}

    client = OpenAICompatibleChatClient(
        base_url="http://localhost:1234/v1/",
        model="qwen3.5-9b",
        temperature=0.1,
        max_tokens=1234,
        timeout_s=77,
        api_key="local-key",
        transport=transport,
    )

    result = client.complete(ChatCompletionRequest("sistema", "usuário"))

    assert result == "Resumo gerado"
    url, payload, headers, timeout_s = calls[0]
    assert url == "http://localhost:1234/v1/chat/completions"
    assert payload["model"] == "qwen3.5-9b"
    assert payload["temperature"] == 0.1
    assert payload["max_tokens"] == 1234
    assert payload["stream"] is False
    assert payload["enable_thinking"] is False
    assert payload["messages"] == [
        {"role": "system", "content": "sistema"},
        {"role": "user", "content": "usuário"},
    ]
    assert headers["Authorization"] == "Bearer local-key"
    assert timeout_s == 77


def test_openai_compatible_client_rejects_invalid_response() -> None:
    def transport(
        url: str, payload: Mapping[str, Any], headers: Mapping[str, str], timeout_s: float
    ) -> Mapping[str, Any]:
        return {"not_choices": []}

    client = OpenAICompatibleChatClient(
        base_url="http://localhost:1234/v1",
        model="qwen3.5-9b",
        transport=transport,
    )

    with pytest.raises(ChatCompletionError, match="formato"):
        client.complete(ChatCompletionRequest("s", "u"))


def test_openai_compatible_client_reports_context_overflow_hint() -> None:
    import io
    import urllib.error

    def transport(
        url: str, payload: Mapping[str, Any], headers: Mapping[str, str], timeout_s: float
    ) -> Mapping[str, Any]:
        body = b'{"error": {"message": "request (5944 tokens) exceeds the available context size (4096 tokens)"}}'
        raise urllib.error.HTTPError(url, 400, "Bad Request", {}, io.BytesIO(body))

    client = OpenAICompatibleChatClient(
        base_url="http://localhost:1234/v1",
        model="qwen3.5-9b",
        transport=transport,
    )

    with pytest.raises(ChatCompletionError) as exc_info:
        client.complete(ChatCompletionRequest("s", "u"))

    message = str(exc_info.value)
    assert "exceeds the available context size" in message
    assert "SUMMARY_MAX_INPUT_TOKENS" in message


def test_openai_compatible_client_can_leave_thinking_untouched() -> None:
    calls: list[tuple[str, Mapping[str, Any], Mapping[str, str], float]] = []

    def transport(
        url: str, payload: Mapping[str, Any], headers: Mapping[str, str], timeout_s: float
    ) -> Mapping[str, Any]:
        calls.append((url, payload, headers, timeout_s))
        return {"choices": [{"message": {"content": "Resposta direta"}}]}

    client = OpenAICompatibleChatClient(
        base_url="http://localhost:1234/v1",
        model="qwen3.5-9b",
        disable_thinking=False,
        transport=transport,
    )

    assert client.complete(ChatCompletionRequest("s", "u")) == "Resposta direta"
    assert "enable_thinking" not in calls[0][1]


def test_openai_compatible_client_strips_qwen_think_blocks() -> None:
    def transport(
        url: str, payload: Mapping[str, Any], headers: Mapping[str, str], timeout_s: float
    ) -> Mapping[str, Any]:
        return {
            "choices": [
                {
                    "message": {
                        "content": "<think>raciocínio interno que não deve aparecer</think>\n\n## Resumo executivo\nConteúdo."
                    }
                }
            ]
        }

    client = OpenAICompatibleChatClient(
        base_url="http://localhost:1234/v1",
        model="qwen3.5-9b",
        disable_thinking=True,
        transport=transport,
    )

    result = client.complete(ChatCompletionRequest("s", "u"))

    assert "<think>" not in result
    assert "raciocínio interno" not in result
    assert result.startswith("## Resumo executivo")
