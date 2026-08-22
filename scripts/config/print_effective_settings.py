"""Mostra configurações efetivas carregadas pelo bot, mascarando segredos.

Use na raiz do projeto:

    uv run python scripts/config/print_effective_settings.py

O objetivo é confirmar se o arquivo .env e as variáveis de ambiente estão sendo
lidos pela mesma configuração que o bot usa em produção.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

from yt_transcriber_bot.application.config import (
    SETTINGS_ENV_FILE_ENV_VAR,
    AppSettings,
    find_project_root,
    get_forced_settings_env_file,
    resolve_settings_env_file,
)

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
    "summary_partial_max_tokens",
    "summary_final_max_tokens",
    "summary_max_chars_per_chunk",
    "summary_max_input_tokens",
    "summary_chars_per_token",
    "summary_tokenizer_backend",
    "summary_tokenizer_model",
    "summary_deduplicate_transcript",
    "summary_merge_same_speaker_gap_s",
    "summary_min_overlap_words",
    "summary_timeout_s",
    "summary_timeout_split_retries",
    "summary_output_language",
    "summary_disable_thinking",
    "summary_validate_model",
    "summary_strict_model_match",
    "summaries_dir_name",
    "max_media_duration_min",
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


def _settings_env_file_path() -> Path:
    return resolve_settings_env_file()


def _lookup_case_insensitive(mapping: dict[str, object], key: str) -> tuple[str, object] | None:
    key_upper = key.upper()
    for actual_key, value in mapping.items():
        if actual_key.upper() == key_upper:
            return actual_key, value
    return None


def _source_for_field(field: str, env_path: Path, dotenv_data: dict[str, object]) -> str:
    env_names = (
        ("MAX_MEDIA_DURATION_MIN", "MAX_VIDEO_DURATION_MIN")
        if field == "max_media_duration_min"
        else (field.upper(),)
    )
    real_environment = dict(os.environ)
    for env_name in env_names:
        real_env = _lookup_case_insensitive(real_environment, env_name)
        if real_env is not None:
            actual_key, _ = real_env
            return f"ambiente real {actual_key} (sobrescreve .env)"
    for env_name in env_names:
        dotenv_hit = _lookup_case_insensitive(dotenv_data, env_name)
        if dotenv_hit is not None:
            actual_key, _ = dotenv_hit
            return f"arquivo {env_path} ({actual_key})"
    return "valor padrão ou argumento explícito"


def build_report_lines(settings: AppSettings | None = None) -> list[str]:
    settings = settings or AppSettings()
    env_path = _settings_env_file_path().expanduser().resolve()
    dotenv_data = dict(dotenv_values(env_path)) if env_path.exists() else {}

    forced_env_file = os.environ.get(SETTINGS_ENV_FILE_ENV_VAR, "").strip()
    project_root_from_cwd = find_project_root(Path.cwd())
    project_root_from_code = find_project_root(Path(__file__))
    forced_path = get_forced_settings_env_file()
    lines = [
        "Configuração efetiva do yt-transcriber-bot",
        f"Diretório atual: {Path.cwd()}",
        f"Raiz detectada pelo diretório atual: {project_root_from_cwd or '<não encontrada>'}",
        f"Raiz detectada pelo código: {project_root_from_code or '<não encontrada>'}",
        f"{SETTINGS_ENV_FILE_ENV_VAR}: {forced_env_file or '<não definido>'}",
        f"Arquivo forçado resolvido: {forced_path or '<não definido>'}",
        f".env usado para diagnóstico/runtime: {env_path}",
        f".env existe: {'sim' if env_path.exists() else 'não'}",
        ".env.example: nunca é usado como configuração runtime.",
        "Prioridade: variáveis do ambiente real sobrescrevem valores do .env.",
        "",
    ]
    for field in _FIELDS:
        value = getattr(settings, field)
        source = _source_for_field(field, env_path, dotenv_data)
        lines.append(f"{field}={value}  # origem: {source}")
    lines.append("")
    for field in sorted(_SECRET_FIELDS):
        value = getattr(settings, field)
        source = _source_for_field(field, env_path, dotenv_data)
        lines.append(f"{field}={_mask(value)}  # origem: {source}")
    return lines


def main() -> int:
    for line in build_report_lines():
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
