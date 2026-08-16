"""Provider credential configuration loaded at the operator/edge boundary."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass(frozen=True, slots=True)
class CredentialStatus:
    telegram_token_configured: bool
    telegram_token_shape_ok: bool
    hf_token_configured: bool
    hf_token_shape_ok: bool
    summary_api_key_configured: bool
    youtube_cookie_source_configured: bool


class ProviderCredentials(BaseSettings):
    """Single owner for provider authentication configuration."""

    model_config = SettingsConfigDict(
        env_file=None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    telegram_bot_token: str = Field(default="", description="Token do Telegram BotFather")
    hf_token: str = Field(default="", description="Token Hugging Face para diarização")
    summary_api_key: str = Field(
        default="", description="API key opcional do endpoint OpenAI-compatible"
    )
    youtube_cookies_file: str = Field(default="", description="Arquivo de cookies do YouTube")
    youtube_cookies_browser: str = Field(
        default="", description="Browser usado para extrair cookies do YouTube"
    )

    def status(self) -> CredentialStatus:
        telegram = self.telegram_bot_token.strip()
        hf = self.hf_token.strip()
        return CredentialStatus(
            telegram_token_configured=bool(telegram),
            telegram_token_shape_ok=bool(
                telegram and ":" in telegram and telegram.split(":", 1)[0].isdigit()
            ),
            hf_token_configured=bool(hf),
            hf_token_shape_ok=hf.startswith("hf_"),
            summary_api_key_configured=bool(self.summary_api_key.strip()),
            youtube_cookie_source_configured=bool(
                self.youtube_cookies_file.strip() or self.youtube_cookies_browser.strip()
            ),
        )

    def validation_problems(self, *, allowed_user_id: int) -> list[str]:
        problems: list[str] = []
        if not self.telegram_bot_token:
            problems.append(
                "TELEGRAM_BOT_TOKEN ausente. Exporte com: "
                "export TELEGRAM_BOT_TOKEN='123456:ABC...' (consulte o README)"
            )
        if allowed_user_id <= 0:
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

    def redaction_values(self) -> tuple[str, ...]:
        return (self.telegram_bot_token, self.hf_token, self.summary_api_key)
