from __future__ import annotations

from typing import Any, Mapping

import pytest

from yt_transcriber_bot.infrastructure.summarization.openai_compatible_client import (
    ChatCompletionError,
    ChatCompletionRequest,
    ChatCompletionTimeoutError,
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
        validate_model=False,
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
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}
    assert payload["reasoning_effort"] == "none"
    assert payload["messages"] == [
        {"role": "system", "content": "sistema"},
        {"role": "user", "content": "/no_think\n\nusuário"},
    ]
    assert headers["Authorization"] == "Bearer local-key"
    assert timeout_s == 77


def test_openai_compatible_client_allows_per_request_max_tokens_override() -> None:
    calls: list[tuple[str, Mapping[str, Any], Mapping[str, str], float]] = []

    def transport(
        url: str, payload: Mapping[str, Any], headers: Mapping[str, str], timeout_s: float
    ) -> Mapping[str, Any]:
        calls.append((url, payload, headers, timeout_s))
        return {"choices": [{"message": {"content": "ok"}}]}

    client = OpenAICompatibleChatClient(
        base_url="http://localhost:1234/v1",
        model="qwen3.5-9b",
        max_tokens=2048,
        validate_model=False,
        transport=transport,
    )

    assert client.complete(ChatCompletionRequest("s", "u", max_tokens=321)) == "ok"

    assert calls[0][1]["max_tokens"] == 321


def test_openai_compatible_client_reports_timeout_as_specific_error() -> None:
    def transport(
        url: str, payload: Mapping[str, Any], headers: Mapping[str, str], timeout_s: float
    ) -> Mapping[str, Any]:
        raise TimeoutError("timed out")

    client = OpenAICompatibleChatClient(
        base_url="http://localhost:1234/v1",
        model="qwen3.5-9b",
        validate_model=False,
        transport=transport,
    )

    with pytest.raises(ChatCompletionTimeoutError) as exc_info:
        client.complete(ChatCompletionRequest("s", "u"))

    message = str(exc_info.value)
    assert "SUMMARY_TIMEOUT_S" in message
    assert "SUMMARY_MAX_INPUT_TOKENS" in message


def test_openai_compatible_client_rejects_invalid_response() -> None:
    def transport(
        url: str, payload: Mapping[str, Any], headers: Mapping[str, str], timeout_s: float
    ) -> Mapping[str, Any]:
        return {"not_choices": []}

    client = OpenAICompatibleChatClient(
        base_url="http://localhost:1234/v1",
        model="qwen3.5-9b",
        validate_model=False,
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
        validate_model=False,
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
        validate_model=False,
        transport=transport,
    )

    assert client.complete(ChatCompletionRequest("s", "u")) == "Resposta direta"
    assert "enable_thinking" not in calls[0][1]
    assert "chat_template_kwargs" not in calls[0][1]
    assert "reasoning_effort" not in calls[0][1]


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
        validate_model=False,
        transport=transport,
    )

    result = client.complete(ChatCompletionRequest("s", "u"))

    assert "<think>" not in result
    assert "raciocínio interno" not in result
    assert result.startswith("## Resumo executivo")

def test_openai_compatible_client_rejects_reasoning_only_response() -> None:
    def transport(
        url: str, payload: Mapping[str, Any], headers: Mapping[str, str], timeout_s: float
    ) -> Mapping[str, Any]:
        return {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "reasoning_content": "Thinking Process: raciocínio que não deve virar resumo",
                    }
                }
            ]
        }

    client = OpenAICompatibleChatClient(
        base_url="http://localhost:1234/v1",
        model="qwen3.5-9b",
        disable_thinking=True,
        validate_model=False,
        transport=transport,
    )

    with pytest.raises(ChatCompletionError) as exc_info:
        client.complete(ChatCompletionRequest("s", "u"))

    message = str(exc_info.value)
    assert "reasoning_content" in message
    assert "Enable Thinking" in message
    assert "SUMMARY_DISABLE_THINKING" in message


def test_openai_compatible_client_accepts_content_even_when_reasoning_content_exists() -> None:
    def transport(
        url: str, payload: Mapping[str, Any], headers: Mapping[str, str], timeout_s: float
    ) -> Mapping[str, Any]:
        return {
            "choices": [
                {
                    "message": {
                        "content": "## Resumo executivo\nConteúdo final.",
                        "reasoning_content": "Thinking Process: deve ser ignorado",
                    }
                }
            ]
        }

    client = OpenAICompatibleChatClient(
        base_url="http://localhost:1234/v1",
        model="qwen3.5-9b",
        disable_thinking=True,
        validate_model=False,
        transport=transport,
    )

    result = client.complete(ChatCompletionRequest("s", "u"))

    assert result == "## Resumo executivo\nConteúdo final."
    assert "Thinking Process" not in result



def test_openai_compatible_client_validates_configured_model_before_completion() -> None:
    model_calls: list[str] = []
    completion_calls: list[str] = []

    def models_transport(url: str, headers: Mapping[str, str], timeout_s: float) -> Mapping[str, Any]:
        model_calls.append(url)
        return {"data": [{"id": "modelo-correto"}]}

    def transport(
        url: str, payload: Mapping[str, Any], headers: Mapping[str, str], timeout_s: float
    ) -> Mapping[str, Any]:
        completion_calls.append(url)
        return {"model": "modelo-correto", "choices": [{"message": {"content": "ok"}}]}

    client = OpenAICompatibleChatClient(
        base_url="http://localhost:1234/v1",
        model="modelo-correto",
        transport=transport,
        models_transport=models_transport,
    )

    assert client.complete(ChatCompletionRequest("s", "u")) == "ok"
    assert model_calls == ["http://localhost:1234/v1/models"]
    assert completion_calls == ["http://localhost:1234/v1/chat/completions"]


def test_openai_compatible_client_rejects_model_missing_from_lm_studio() -> None:
    def models_transport(url: str, headers: Mapping[str, str], timeout_s: float) -> Mapping[str, Any]:
        return {"data": [{"id": "qwen3.5-9b@q4_k_m"}]}

    def transport(
        url: str, payload: Mapping[str, Any], headers: Mapping[str, str], timeout_s: float
    ) -> Mapping[str, Any]:  # pragma: no cover - não deve ser chamado
        raise AssertionError("completion não deveria ser chamada")

    client = OpenAICompatibleChatClient(
        base_url="http://localhost:1234/v1",
        model="modelo-do-env",
        transport=transport,
        models_transport=models_transport,
    )

    with pytest.raises(ChatCompletionError) as exc_info:
        client.complete(ChatCompletionRequest("s", "u"))

    message = str(exc_info.value)
    assert "SUMMARY_MODEL='modelo-do-env'" in message
    assert "qwen3.5-9b@q4_k_m" in message
    assert "/v1/models" in message


def test_openai_compatible_client_rejects_response_model_mismatch() -> None:
    def transport(
        url: str, payload: Mapping[str, Any], headers: Mapping[str, str], timeout_s: float
    ) -> Mapping[str, Any]:
        return {
            "model": "qwen3.5-9b@q4_k_m",
            "choices": [{"message": {"content": "resumo"}}],
        }

    client = OpenAICompatibleChatClient(
        base_url="http://localhost:1234/v1",
        model="modelo-configurado",
        validate_model=False,
        strict_model_match=True,
        transport=transport,
    )

    with pytest.raises(ChatCompletionError) as exc_info:
        client.complete(ChatCompletionRequest("s", "u"))

    message = str(exc_info.value)
    assert "modelo diferente" in message
    assert "SUMMARY_MODEL='modelo-configurado'" in message
    assert "qwen3.5-9b@q4_k_m" in message


def test_openai_compatible_client_can_allow_response_model_alias() -> None:
    def transport(
        url: str, payload: Mapping[str, Any], headers: Mapping[str, str], timeout_s: float
    ) -> Mapping[str, Any]:
        return {
            "model": "alias-do-servidor",
            "choices": [{"message": {"content": "resumo"}}],
        }

    client = OpenAICompatibleChatClient(
        base_url="http://localhost:1234/v1",
        model="modelo-configurado",
        validate_model=False,
        strict_model_match=False,
        transport=transport,
    )

    assert client.complete(ChatCompletionRequest("s", "u")) == "resumo"
