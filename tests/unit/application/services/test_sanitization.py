"""Regressões de sanitização para Telegram/logs operacionais."""

from __future__ import annotations

from pathlib import Path

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.services.sanitization import sanitize_text

_TELEGRAM_TOKEN = "123456789" + ":" + "ABCDEFGHIJKLMNOPQRSTUVWXyz012345"
_SUMMARY_API_KEY = "sk-" + "proj-" + "secretKey123456789"
_OPENAI_API_KEY = "sk-" + "live-" + "abc12345678901234567"
_NETSCAPE_COOKIE_LINE = "." + "youtube.com\tTRUE\t/\tFALSE\t1999999999\tSID\tcookie-file-secret"


def _settings(tmp_path: Path) -> AppSettings:
    return AppSettings(
        telegram_bot_token=_TELEGRAM_TOKEN,
        telegram_allowed_user_id=42,
        hf_token="hf_alphaBravo123456",
        summary_api_key=_SUMMARY_API_KEY,
        base_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
    )


def test_sanitize_text_redacts_known_secret_shapes_and_configured_values(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    raw = (
        f"bot={_TELEGRAM_TOKEN}\n"
        "hf=hf_alphaBravo123456\n"
        f"api={_SUMMARY_API_KEY}\n"
        "Authorization: Bearer bearer-token-123\n"
        "Authorization: Basic abcdefghijklmnop\n"
        "Cookie: SID=abc; HSID=def\n"
        f"{_NETSCAPE_COOKIE_LINE}\n"
        '{"headers":{"Authorization":"Bearer json-token","api_key":"json-api-key"}}\n'
        f"OPENAI_API_KEY={_OPENAI_API_KEY}\n"
        "url=https://example.com/callback?token=abc&api_key=def&access_token=ghi"
    )

    cleaned = sanitize_text(raw, settings)

    assert _TELEGRAM_TOKEN not in cleaned
    assert "hf_alphaBravo123456" not in cleaned
    assert _SUMMARY_API_KEY not in cleaned
    assert _OPENAI_API_KEY not in cleaned
    assert "bearer-token-123" not in cleaned
    assert "abcdefghijklmnop" not in cleaned
    assert "SID=abc" not in cleaned
    assert "cookie-file-secret" not in cleaned
    assert "json-token" not in cleaned
    assert "json-api-key" not in cleaned
    assert "api_key=def" not in cleaned
    assert cleaned.count("[REDACTED]") >= 6


def test_sanitize_text_omits_prompt_fragments_and_api_body_fields(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    raw = (
        'payload={"messages":[{"role":"system","content":"system instructions"}],'
        '"prompt":"summarize this transcript","user_prompt":"user provided prompt",'
        '"system_prompt":"hidden rubric","content":"full transcript body",'
        '"input":"raw input transcript","transcript":"private transcript text"}}\n'
        'response_body={"input":"echoed raw input","content":"echoed transcript"}\n'
        "body={'messages':[{'role':'user','content':'raw request body'}]}"
    )

    cleaned = sanitize_text(raw, settings)

    assert "system instructions" not in cleaned
    assert "summarize this transcript" not in cleaned
    assert "user provided prompt" not in cleaned
    assert "hidden rubric" not in cleaned
    assert "full transcript body" not in cleaned
    assert "raw input transcript" not in cleaned
    assert "private transcript text" not in cleaned
    assert "echoed raw input" not in cleaned
    assert "echoed transcript" not in cleaned
    assert "raw request body" not in cleaned
    assert '"messages":[OMITTED]' in cleaned or '"messages": [OMITTED]' in cleaned
    assert cleaned.count("[OMITTED]") >= 4
