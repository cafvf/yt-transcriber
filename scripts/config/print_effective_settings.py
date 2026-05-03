"""Mostra configurações efetivas carregadas pelo bot, mascarando segredos.

Use na raiz do projeto:

    uv run python scripts/config/print_effective_settings.py

O objetivo é confirmar se o arquivo .env e as variáveis de ambiente estão sendo
lidos pela mesma configuração que o bot usa em produção.
"""

from __future__ import annotations

from pathlib import Path

from yt_transcriber_bot.application.config import AppSettings


_SECRET_FIELDS = {
    "telegram_bot_token",
    "hf_token",
    "summary_api_key",
}

_FIELDS = (
    "telegram_allowed_user_id",
    "youtube_cookies_file",
    "youtube_cookies_browser",
    "whisper_model",
    "whisper_model_pt",
    "whisper_model_en",
    "whisper_model_default",
    "device",
    "compute_type",
    "prefer_youtube_subtitles",
    "summary_backend",
    "summary_base_url",
    "summary_model",
    "summary_temperature",
    "summary_max_tokens",
    "summary_max_chars_per_chunk",
    "summary_max_input_tokens",
    "summary_chars_per_token",
    "summary_timeout_s",
    "summary_output_language",
    "summary_disable_thinking",
    "summaries_dir_name",
    "telegram_max_queue_size",
    "max_video_subtitles_duration_min",
    "max_video_subtitles_size_mb",
)


def _mask(value: object) -> str:
    text = str(value)
    if not text:
        return "<vazio>"
    if len(text) <= 8:
        return "***"
    return f"{text[:4]}...{text[-4:]}"


def main() -> int:
    settings = AppSettings()
    env_path = Path(".env").resolve()
    print("Configuração efetiva do yt-transcriber-bot")
    print(f"Diretório atual: {Path.cwd()}")
    print(f".env esperado: {env_path}")
    print(f".env existe: {'sim' if env_path.exists() else 'não'}")
    print()
    for field in _FIELDS:
        value = getattr(settings, field)
        print(f"{field}={value}")
    print()
    for field in sorted(_SECRET_FIELDS):
        value = getattr(settings, field)
        print(f"{field}={_mask(value)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
