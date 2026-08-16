from __future__ import annotations

import pytest

from yt_transcriber_bot.configuration.external_services import (
    TextGenerationEndpointPolicy,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:1234/v1",
        "http://127.0.0.1:1234/v1",
        "http://127.10.20.30:1234/v1",
        "http://[::1]:1234/v1",
    ],
)
def test_loopback_endpoint_needs_no_remote_disclosure_opt_in(url: str) -> None:
    policy = TextGenerationEndpointPolicy(url, "model", explicitly_configured=False)
    assert policy.is_local
    policy.require_transcript_disclosure_allowed()


def test_nonlocal_endpoint_requires_explicit_operator_configuration() -> None:
    policy = TextGenerationEndpointPolicy(
        "https://llm.example.invalid/v1",
        "model",
        explicitly_configured=False,
    )
    with pytest.raises(ValueError, match="explicit"):
        policy.require_transcript_disclosure_allowed()


def test_explicit_nonlocal_endpoint_is_allowed() -> None:
    policy = TextGenerationEndpointPolicy(
        "https://llm.example.invalid/v1",
        "model",
        explicitly_configured=True,
    )
    assert not policy.is_local
    policy.require_transcript_disclosure_allowed()


@pytest.mark.parametrize("url", ["relative/path", "file:///tmp/socket", ""])
def test_invalid_endpoint_is_rejected(url: str) -> None:
    with pytest.raises(ValueError, match="absolute http"):
        TextGenerationEndpointPolicy(url, "model", explicitly_configured=True)
