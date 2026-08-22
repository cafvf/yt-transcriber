"""Show effective runtime settings while masking credential values."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.configuration.runtime_settings import (
    SETTINGS_ENV_FILE_ENV_VAR,
    RuntimeSettingsSource,
    load_runtime_settings,
    resolve_runtime_settings_source,
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


def _lookup_case_insensitive(mapping: dict[str, object], key: str) -> tuple[str, object] | None:
    key_upper = key.upper()
    for actual_key, value in mapping.items():
        if actual_key.upper() == key_upper:
            return actual_key, value
    return None


def _dotenv_data(source: RuntimeSettingsSource) -> dict[str, object]:
    path = source.env_file
    if path is None or not path.exists():
        return {}
    return dict(dotenv_values(path))


def _source_for_field(
    field: str,
    source: RuntimeSettingsSource,
    dotenv_data: dict[str, object],
) -> str:
    env_names = (
        ("MAX_MEDIA_DURATION_MIN", "MAX_VIDEO_DURATION_MIN")
        if field == "max_media_duration_min"
        else (field.upper(),)
    )
    real_environment = dict(os.environ)
    for env_name in env_names:
        real_env = _lookup_case_insensitive(real_environment, env_name)
        if real_env is not None:
            actual_key, value = real_env
            if source.env_file is not None:
                dotenv_hit = _lookup_case_insensitive(dotenv_data, env_name)
                if dotenv_hit is not None and str(dotenv_hit[1]) == str(value):
                    return f"ambiente real {actual_key} (valor igual ao arquivo de ambiente)"
                return f"ambiente real {actual_key} (sobrescreve arquivo de ambiente)"
            return f"ambiente real {actual_key}"

    if source.env_file is not None:
        for env_name in env_names:
            dotenv_hit = _lookup_case_insensitive(dotenv_data, env_name)
            if dotenv_hit is not None:
                actual_key, _ = dotenv_hit
                return f"arquivo {source.env_file} ({actual_key})"
    return "valor padrão ou argumento explícito"


def build_report_lines(
    settings: AppSettings | None = None,
    source: RuntimeSettingsSource | None = None,
) -> list[str]:
    resolved = source or resolve_runtime_settings_source()
    settings = settings or load_runtime_settings(resolved)
    dotenv_data = _dotenv_data(resolved)
    forced_env_file = os.environ.get(SETTINGS_ENV_FILE_ENV_VAR, "").strip()

    source_detail = resolved.kind.value
    if resolved.env_file is not None:
        source_detail += f": {resolved.env_file}"

    lines = [
        "Configuração efetiva do yt-transcriber-bot",
        f"Diretório atual: {Path.cwd()}",
        f"Fonte runtime: {source_detail}",
        f"{SETTINGS_ENV_FILE_ENV_VAR}: {forced_env_file or '<não definido>'}",
        (
            "Arquivo dotenv efetivo: "
            + (str(resolved.env_file) if resolved.env_file is not None else "<nenhum>")
        ),
        ".env.example: nunca é usado como configuração runtime.",
        (
            "Produção via systemd: /etc/yt-transcriber-bot/env é injetado no "
            "process environment pelo EnvironmentFile."
        ),
        (
            "Instalação fora do checkout não procura .env no CWD; "
            "use ambiente real ou YT_TRANSCRIBER_ENV_FILE explícito."
        ),
        "Prioridade: variáveis do ambiente real sobrescrevem valores do arquivo dotenv.",
        "",
    ]
    for field in _FIELDS:
        value = getattr(settings, field)
        origin = _source_for_field(field, resolved, dotenv_data)
        lines.append(f"{field}={value}  # origem: {origin}")

    lines.append("")
    for field in sorted(_SECRET_FIELDS):
        value = getattr(settings, field)
        origin = _source_for_field(field, resolved, dotenv_data)
        lines.append(f"{field}={_mask(value)}  # origem: {origin}")
    return lines


def main() -> int:
    source = resolve_runtime_settings_source()
    settings = load_runtime_settings(source)
    for line in build_report_lines(settings, source):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
