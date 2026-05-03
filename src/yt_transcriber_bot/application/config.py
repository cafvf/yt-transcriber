"""Configuração centralizada do bot.

Segredos (TOKEN, USER_ID, HF_TOKEN, COOKIES) **devem** vir do ambiente.
Parâmetros não-sensíveis podem vir de ``.env`` ou variáveis de ambiente.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Configuração efetiva carregada na inicialização do bot."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===== Segredos / autorização =====
    telegram_bot_token: str = Field(default="", description="Token do Telegram BotFather")
    telegram_allowed_user_id: int = Field(
        default=0, description="user_id numérico do único usuário autorizado"
    )
    hf_token: str = Field(default="", description="Token Hugging Face para pyannote")

    # ===== Cookies do YouTube (members-only) =====
    youtube_cookies_file: str = Field(
        default="",
        description="Caminho para arquivo de cookies (Netscape format)",
    )
    youtube_cookies_browser: str = Field(
        default="",
        description="Browser para extrair cookies (firefox|chrome|brave|...)",
    )

    # ===== Whisper / diarização =====
    whisper_model: str = Field(
        default="auto",
        description=(
            "auto|tiny|base|small|medium|large-v2|large-v3. "
            "Em auto, escolhe o modelo por idioma."
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
    summary_api_key: str = Field(
        default="",
        description="API key opcional para servidores OpenAI-compatible; LM Studio local normalmente não exige",
    )
    summary_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    summary_max_tokens: int = Field(default=1024, ge=256, le=32768)
    summary_max_chars_per_chunk: int = Field(default=4000, ge=500, le=100000)
    summary_max_input_tokens: int = Field(
        default=2500,
        ge=512,
        le=32768,
        description="Orçamento aproximado de tokens de entrada por chamada de resumo",
    )
    summary_chars_per_token: float = Field(
        default=2.0,
        ge=1.0,
        le=10.0,
        description="Estimativa conservadora de caracteres por token para chunking sem tokenizer local",
    )
    summary_timeout_s: float = Field(default=300.0, ge=5.0, le=1800.0)
    summary_output_language: str = Field(
        default="auto",
        description="Idioma do resumo: auto mantém o idioma predominante da transcrição; use pt/en para forçar",
    )
    summary_disable_thinking: bool = Field(
        default=True,
        description="Desabilita thinking/reasoning explícito em chamadas de resumo quando suportado",
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
        """Hash que muda quando parâmetros que afetam a transcrição mudam.

        Usado para detectar quando um vídeo cacheado foi processado com
        configurações diferentes das atuais.
        """
        content = "|".join(
            [
                f"model={self.whisper_model}",
                f"model_pt={self.whisper_model_pt}",
                f"model_en={self.whisper_model_en}",
                f"model_default={self.whisper_model_default}",
                f"device={self.device}",
                f"compute={self.compute_type}",
                f"bitrate={self.audio_bitrate_kbps}",
                f"sr={self.audio_sample_rate_hz}",
                f"langs={','.join(sorted(self.allowed_languages))}",
            ]
        )
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def validate_runtime_secrets(self) -> list[str]:
        """Devolve a lista de erros se segredos obrigatórios estiverem ausentes."""
        problems: list[str] = []
        if not self.telegram_bot_token:
            problems.append(
                "TELEGRAM_BOT_TOKEN ausente. Exporte com: "
                "export TELEGRAM_BOT_TOKEN='123456:ABC...' (consulte o README)"
            )
        if self.telegram_allowed_user_id <= 0:
            problems.append(
                "TELEGRAM_ALLOWED_USER_ID ausente ou <= 0. "
                "Exporte com: export TELEGRAM_ALLOWED_USER_ID=123456789"
            )
        if not self.hf_token:
            problems.append(
                "HF_TOKEN ausente. Exporte com: export HF_TOKEN='hf_xxxx' "
                "(necessário para diarização; veja README)"
            )
        return problems


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
    if value.startswith((".", "~", "/")) and not any(ch.isspace() for ch in value):
        return True
    return False
