"""Configuração centralizada do bot.

Segredos (TOKEN, USER_ID, HF_TOKEN, COOKIES) **devem** vir do ambiente.
Parâmetros não-sensíveis podem vir de ``.env`` ou variáveis de ambiente.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import Field, PrivateAttr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from yt_transcriber_bot.configuration.credentials import ProviderCredentials

SETTINGS_ENV_FILE_ENV_VAR = "YT_TRANSCRIBER_ENV_FILE"
PROJECT_NAME = "yt-transcriber-bot"


def _is_runtime_env_file(path: Path) -> bool:
    """Impede que templates sejam usados como configuração efetiva.

    ``.env.example`` é documentação de onboarding e pode conter valores
    ilustrativos. Carregá-lo em runtime mascara erros de configuração, como
    usar o modelo de exemplo em vez do ``SUMMARY_MODEL`` real.
    """

    return path.name != ".env.example"


def _looks_like_project_root(path: Path) -> bool:
    pyproject = path / "pyproject.toml"
    if not pyproject.exists():
        return False
    try:
        content = pyproject.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return f'name = "{PROJECT_NAME}"' in content or f"name = '{PROJECT_NAME}'" in content


def find_project_root(start: Path | None = None) -> Path | None:
    """Encontra a raiz do projeto a partir de ``start`` ou do diretório atual."""

    current = (start or Path.cwd()).expanduser().resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if _looks_like_project_root(candidate):
            return candidate
    return None


def get_forced_settings_env_file() -> Path | None:
    """Retorna o ``.env`` explicitamente escolhido pelo operador, se houver."""

    value = os.environ.get(SETTINGS_ENV_FILE_ENV_VAR, "").strip()
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def resolve_settings_env_file() -> Path:
    """Resolve o arquivo ``.env`` efetivo sem recorrer a ``.env.example``.

    Ordem de descoberta do arquivo dotenv:

    1. ``YT_TRANSCRIBER_ENV_FILE``, se definido;
    2. ``.env`` da raiz do projeto encontrada a partir do diretório atual;
    3. ``.env`` da raiz do projeto encontrada a partir deste arquivo Python;
    4. ``.env`` do diretório atual como fallback para instalações fora do repo.

    As variáveis reais do ambiente continuam tendo precedência sobre valores do
    arquivo dotenv, conforme o comportamento do pydantic-settings.
    """

    forced = get_forced_settings_env_file()
    if forced is not None:
        if not _is_runtime_env_file(forced):
            raise ValueError(
                "YT_TRANSCRIBER_ENV_FILE aponta para .env.example. "
                "Esse arquivo é apenas template; copie-o para .env e edite os valores reais."
            )
        return forced

    for root in (find_project_root(Path.cwd()), find_project_root(Path(__file__))):
        if root is not None:
            return root / ".env"

    return Path.cwd() / ".env"


@dataclass(frozen=True, slots=True)
class MediaProcessingSettings:
    """Source-neutral settings used by generic media processing."""

    max_media_duration_min: int
    audio_bitrate_kbps: int
    audio_sample_rate_hz: int
    allowed_languages: tuple[str, ...]


class AppSettings(BaseSettings):
    """Operator-facing compatibility loader for effective configuration.

    Provider credentials have their own owner (``ProviderCredentials``).
    Legacy flat constructor arguments and environment names remain accepted.
    """

    model_config = SettingsConfigDict(
        env_file=None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    _credentials: ProviderCredentials = PrivateAttr()

    def __init__(self, **values: Any) -> None:
        if "_env_file" not in values:
            values["_env_file"] = resolve_settings_env_file()

        env_file = values["_env_file"]
        credential_values: dict[str, Any] = {}
        for field_name in ProviderCredentials.model_fields:
            if field_name in values:
                credential_values[field_name] = values.pop(field_name)

        super().__init__(**values)
        # Pydantic Settings accepts _env_file dynamically at runtime; mypy does not expose it in the generated constructor signature.
        credentials_factory: Any = ProviderCredentials
        self._credentials = credentials_factory(
            _env_file=env_file,
            **credential_values,
        )

    # ===== Autorização =====
    telegram_allowed_user_id: int = Field(
        default=0, description="user_id numérico do único usuário autorizado"
    )

    # ===== Whisper / diarização =====
    whisper_model: str = Field(
        default="auto",
        description=(
            "auto|tiny|base|small|medium|large-v2|large-v3. Em auto, escolhe o modelo por idioma."
        ),
    )
    whisper_model_pt: str = Field(
        default="large-v3",
        description="Modelo Whisper usado quando WHISPER_MODEL=auto e o idioma for pt.",
    )
    whisper_model_en: str = Field(
        default="medium",
        description="Modelo Whisper usado quando WHISPER_MODEL=auto e o idioma for en.",
    )
    whisper_model_default: str = Field(
        default="medium",
        description="Modelo Whisper usado quando WHISPER_MODEL=auto e o idioma for desconhecido/outro.",
    )
    device: str = Field(default="auto", description="auto|cpu|cuda")
    compute_type: str = Field(default="auto", description="auto|float16|int8|int8_float16|float32")

    # ===== Áudio =====
    audio_bitrate_kbps: int = Field(default=32, ge=16, le=128)
    audio_sample_rate_hz: int = Field(default=16000, ge=8000, le=48000)

    # ===== Limites e retenção =====
    max_video_duration_min: int = Field(default=180, ge=1, le=720)
    retention_count: int = Field(
        default=5, ge=1, le=100, description="N de jobs mantidos antes da política FIFO"
    )

    # ===== Idiomas aceitos =====
    allowed_languages: tuple[str, ...] = Field(default=("pt", "en"))

    # ===== Estratégia de transcrição =====
    prefer_youtube_subtitles: bool = Field(
        default=True,
        description="Tenta usar legendas existentes do YouTube antes de transcrever",
    )

    # ===== Diretórios =====
    base_dir: Path = Field(default=Path("data"))
    downloads_dir_name: str = Field(default="downloads")
    processed_dir_name: str = Field(default="processed")
    transcripts_dir_name: str = Field(default="transcripts")
    logs_dir_name: str = Field(default="logs")
    models_dir: Path = Field(default=Path("models"))
    db_path: Path = Field(default=Path("data/jobs.db"))

    # ===== Telegram =====
    telegram_message_edit_min_interval_s: float = Field(default=2.0, ge=0.5, le=10.0)
    telegram_max_queue_size: int = Field(
        default=5, ge=1, le=50, description="Limite total de jobs em execução + pendentes"
    )
    telegram_max_media_size_mb: int = Field(default=20, ge=1, le=50)

    # ===== Observabilidade operacional =====
    healthcheck_lmstudio_timeout_s: float = Field(
        default=5.0,
        ge=0.5,
        le=60.0,
        description="Timeout curto para /healthcheck consultar o endpoint /models do LM Studio",
    )
    healthcheck_min_free_disk_mb: int = Field(
        default=500,
        ge=1,
        le=102400,
        description="Espaço livre mínimo recomendado em MB para /healthcheck",
    )
    lasterror_recent_limit: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Número de jobs recentes examinados por /lasterror",
    )
    lasterror_log_tail_lines: int = Field(
        default=20,
        ge=1,
        le=200,
        description="Número máximo de linhas do log anexadas ao /lasterror",
    )
    lasterror_log_tail_chars: int = Field(
        default=4000,
        ge=200,
        le=20000,
        description="Número máximo de caracteres do trecho de log anexado ao /lasterror",
    )
    lasterror_traceback_tail_lines: int = Field(
        default=12,
        ge=1,
        le=100,
        description="Número máximo de linhas do traceback operacional anexadas ao /lasterror",
    )
    lasterror_traceback_tail_chars: int = Field(
        default=4000,
        ge=200,
        le=20000,
        description="Número máximo de caracteres do traceback operacional anexado ao /lasterror",
    )
    operational_log_max_bytes: int = Field(default=5_000_000, ge=65_536, le=100_000_000)
    operational_log_backup_count: int = Field(default=3, ge=1, le=20)
    audit_log_max_bytes: int = Field(default=2_000_000, ge=65_536, le=100_000_000)
    audit_log_backup_count: int = Field(default=2, ge=1, le=20)
    operational_error_max_records: int = Field(default=500, ge=10, le=10_000)

    # ===== Sumarização por LLM local/OpenAI-compatible =====
    summary_backend: str = Field(
        default="openai_compatible",
        description="Backend de resumo: openai_compatible|disabled",
    )
    summary_base_url: str = Field(
        default="http://localhost:1234/v1",
        description="Base URL OpenAI-compatible, por exemplo LM Studio: http://localhost:1234/v1",
    )
    summary_model: str = Field(
        default="qwen3.5-9b",
        description="Modelo carregado/visível no servidor do LM Studio para sumarização",
    )
    summary_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    summary_max_tokens: int = Field(
        default=1024,
        ge=256,
        le=32768,
        description=(
            "Limite legado de tokens de saída do cliente. "
            "SUMMARY_PARTIAL_MAX_TOKENS e SUMMARY_FINAL_MAX_TOKENS controlam cada etapa."
        ),
    )
    summary_partial_max_tokens: int = Field(
        default=512,
        ge=128,
        le=32768,
        description="Máximo de tokens de saída para cada resumo parcial",
    )
    summary_final_max_tokens: int = Field(
        default=1024,
        ge=256,
        le=32768,
        description="Máximo de tokens de saída para resumo em passagem única ou síntese final",
    )
    summary_max_chars_per_chunk: int = Field(default=18000, ge=500, le=100000)
    summary_max_input_tokens: int = Field(
        default=6000,
        ge=512,
        le=32768,
        description="Orçamento aproximado de tokens de entrada por chamada de resumo",
    )
    summary_chars_per_token: float = Field(
        default=2.5,
        ge=1.0,
        le=10.0,
        description="Estimativa conservadora de caracteres por token para chunking sem tokenizer local",
    )
    summary_tokenizer_backend: str = Field(
        default="auto",
        description="Backend de tokenização para chunking: auto|hf|estimate",
    )
    summary_tokenizer_model: str = Field(
        default="",
        description="Modelo Hugging Face local para tokenização; vazio usa SUMMARY_MODEL",
    )
    summary_tokenizer_trust_remote_code: bool = Field(
        default=False,
        description=(
            "Permite trust_remote_code no AutoTokenizer local. "
            "Padrão seguro: false; habilite apenas para tokenizers confiáveis."
        ),
    )
    summary_deduplicate_transcript: bool = Field(
        default=True,
        description="Remove redundâncias adjacentes da transcrição antes da sumarização",
    )
    summary_merge_same_speaker_gap_s: float = Field(
        default=2.0,
        ge=0.0,
        le=300.0,
        description="Gap máximo para unir segmentos consecutivos do mesmo falante no texto de resumo",
    )
    summary_min_overlap_words: int = Field(
        default=6,
        ge=2,
        le=50,
        description="N mínimo de palavras sobrepostas para remover prefixo repetido entre segmentos",
    )
    summary_timeout_s: float = Field(default=600.0, ge=5.0, le=3600.0)
    summary_timeout_split_retries: int = Field(
        default=2,
        ge=0,
        le=8,
        description="Número máximo de subdivisões adaptativas quando uma chamada de resumo excede o timeout",
    )
    summary_output_language: str = Field(
        default="auto",
        description="Idioma do resumo: auto mantém o idioma predominante da transcrição; use pt/en para forçar",
    )
    summary_disable_thinking: bool = Field(
        default=True,
        description="Desabilita thinking/reasoning explícito em chamadas de resumo quando suportado",
    )
    summary_validate_model: bool = Field(
        default=True,
        description="Valida SUMMARY_MODEL contra GET /v1/models antes de chamar a LLM",
    )
    summary_strict_model_match: bool = Field(
        default=True,
        description="Falha se a resposta declarar um modelo diferente de SUMMARY_MODEL",
    )
    summaries_dir_name: str = Field(default="summaries")

    # ===== Vídeo com legenda selecionável =====
    max_video_subtitles_duration_min: int = Field(
        default=30,
        ge=1,
        le=180,
        description="Duração máxima para gerar vídeo MP4 com legenda selecionável",
    )
    max_video_subtitles_size_mb: int = Field(
        default=200,
        ge=1,
        le=2000,
        description="Tamanho máximo do MP4 legendado a ser enviado pelo Telegram",
    )
    video_exports_dir_name: str = Field(default="video_exports")

    @field_validator("device")
    @classmethod
    def _validate_device(cls, v: str) -> str:
        if v not in {"auto", "cpu", "cuda"}:
            raise ValueError(f"device inválido: '{v}'")
        return v

    @field_validator("compute_type")
    @classmethod
    def _validate_compute_type(cls, v: str) -> str:
        valid = {"auto", "float16", "float32", "int8", "int8_float16"}
        if v not in valid:
            raise ValueError(f"compute_type inválido: '{v}' (use {sorted(valid)})")
        return v

    @field_validator("summary_backend")
    @classmethod
    def _validate_summary_backend(cls, v: str) -> str:
        value = v.strip().lower()
        if value not in {"openai_compatible", "disabled"}:
            raise ValueError("summary_backend inválido: use 'openai_compatible' ou 'disabled'")
        return value

    @field_validator("summary_tokenizer_backend")
    @classmethod
    def _validate_summary_tokenizer_backend(cls, v: str) -> str:
        value = v.strip().lower()
        if value not in {"auto", "hf", "huggingface", "estimate", "estimated"}:
            raise ValueError("SUMMARY_TOKENIZER_BACKEND inválido: use auto, hf ou estimate")
        if value == "huggingface":
            return "hf"
        if value == "estimated":
            return "estimate"
        return value

    @field_validator("summary_base_url")
    @classmethod
    def _validate_summary_base_url(cls, v: str) -> str:
        value = v.strip().rstrip("/")
        if not value:
            raise ValueError("summary_base_url não pode ser vazio")
        return value

    @field_validator("summary_model")
    @classmethod
    def _validate_summary_model(cls, v: str) -> str:
        value = v.strip()
        if not value:
            raise ValueError("summary_model não pode ser vazio")
        return value

    @field_validator("whisper_model")
    @classmethod
    def _validate_model(cls, v: str) -> str:
        v = v.strip()
        if v == "auto" or _is_model_reference(v):
            return v
        raise ValueError(
            f"whisper_model inválido: '{v}'. Use 'auto', um modelo Whisper padrão, "
            "um repositório Hugging Face (ex.: org/modelo) ou um caminho local."
        )

    @field_validator("whisper_model_pt", "whisper_model_en", "whisper_model_default")
    @classmethod
    def _validate_language_model(cls, v: str) -> str:
        v = v.strip()
        if _is_model_reference(v):
            return v
        raise ValueError(
            f"modelo Whisper por idioma inválido: '{v}'. Use um modelo Whisper padrão, "
            "um repositório Hugging Face (ex.: inesc-id/WhisperLv3-X-PT-All) "
            "ou um caminho local."
        )

    @property
    def credentials(self) -> ProviderCredentials:
        """Provider authentication/configuration outside behavior policy."""

        return self._credentials

    @property
    def telegram_bot_token(self) -> str:
        return self._credentials.telegram_bot_token

    @property
    def hf_token(self) -> str:
        return self._credentials.hf_token

    @property
    def summary_api_key(self) -> str:
        return self._credentials.summary_api_key

    @property
    def youtube_cookies_file(self) -> str:
        return self._credentials.youtube_cookies_file

    @property
    def youtube_cookies_browser(self) -> str:
        return self._credentials.youtube_cookies_browser

    @property
    def media_processing(self) -> MediaProcessingSettings:
        """Source-neutral internal view over generic media-processing policy."""

        return MediaProcessingSettings(
            max_media_duration_min=self.max_video_duration_min,
            audio_bitrate_kbps=self.audio_bitrate_kbps,
            audio_sample_rate_hz=self.audio_sample_rate_hz,
            allowed_languages=self.allowed_languages,
        )

    def downloads_dir(self) -> Path:
        return self.base_dir / self.downloads_dir_name

    def processed_dir(self) -> Path:
        return self.base_dir / self.processed_dir_name

    def transcripts_dir(self) -> Path:
        return self.base_dir / self.transcripts_dir_name

    def logs_dir(self) -> Path:
        return self.base_dir / self.logs_dir_name

    def video_exports_dir(self) -> Path:
        return self.base_dir / self.video_exports_dir_name

    def summaries_dir(self) -> Path:
        return self.base_dir / self.summaries_dir_name

    def transcription_signature(self) -> str:
        """Nome compatível para o fingerprint canônico de processamento."""

        from yt_transcriber_bot.application.services.config_signature import (
            compute_processing_fingerprint,
        )

        return compute_processing_fingerprint(self)

    def validate_runtime_secrets(self) -> list[str]:
        """Compatibility API delegating validation to the credential owner."""

        return self._credentials.validation_problems(allowed_user_id=self.telegram_allowed_user_id)


def _is_model_reference(value: str) -> bool:
    """Aceita modelos padrão, repos Hugging Face e caminhos locais.

    O WhisperX/faster-whisper aceita nomes padrão como ``medium`` e também
    pode receber um repositório HF/caminho local quando o backend suporta.
    A validação aqui deve impedir apenas strings vazias ou claramente inválidas,
    não bloquear modelos fine-tuned como ``inesc-id/WhisperLv3-X-PT-All``.
    """
    if not value:
        return False
    standard = {"tiny", "base", "small", "medium", "large-v2", "large-v3"}
    if value in standard:
        return True
    # Repositório Hugging Face simples: org/model, sem espaços.
    if "/" in value and not any(ch.isspace() for ch in value):
        return True
    # Caminho local absoluto ou relativo explícito.
    return value.startswith((".", "~", "/")) and not any(ch.isspace() for ch in value)
