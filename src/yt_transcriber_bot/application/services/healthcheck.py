from __future__ import annotations

from dataclasses import dataclass

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.health_probe import (
    HealthEnvironmentProbe,
    HealthEnvironmentSnapshot,
)
from yt_transcriber_bot.application.services.sanitization import sanitize_text


@dataclass(frozen=True)
class HealthCheckItem:
    name: str
    status: str
    detail: str

    @property
    def icon(self) -> str:
        return {"ok": "✅", "warn": "⚠️", "fail": "❌"}.get(self.status, "•")


@dataclass(frozen=True)
class HealthCheckReport:
    items: tuple[HealthCheckItem, ...]

    @property
    def overall_status(self) -> str:
        states = {item.status for item in self.items}
        return "fail" if "fail" in states else "warn" if "warn" in states else "ok"

    def render(self, settings: AppSettings) -> str:
        title = {
            "ok": "✅ Healthcheck: OK",
            "warn": "⚠️ Healthcheck: OK com avisos",
            "fail": "❌ Healthcheck: problemas encontrados",
        }[self.overall_status]
        return sanitize_text(
            "\n".join(
                [title, "", *(f"{item.icon} {item.name}: {item.detail}" for item in self.items)]
            ),
            settings,
        )


class HealthCheckService:
    def __init__(self, *, settings: AppSettings, environment_probe: HealthEnvironmentProbe) -> None:
        self._settings = settings
        self._probe = environment_probe

    def run(self) -> HealthCheckReport:
        facts = self._probe.snapshot()
        items = [
            HealthCheckItem("Python", "ok", facts.python_detail),
            HealthCheckItem(
                "Raiz do projeto",
                "ok" if facts.project_root_found else "warn",
                "encontrada." if facts.project_root_found else "não encontrada.",
            ),
        ]
        problems = self._settings.validate_runtime_secrets()
        items.append(
            HealthCheckItem(
                "Configuração obrigatória",
                "fail" if problems else "ok",
                "; ".join(sanitize_text(item, self._settings) for item in problems)
                if problems
                else "segredos mínimos definidos.",
            )
        )
        credential_status = self._settings.credentials.status()
        items.extend(
            [
                HealthCheckItem(
                    "Formato TELEGRAM_BOT_TOKEN",
                    "ok" if credential_status.telegram_token_shape_ok else "warn",
                    "aparenta ter formato do BotFather."
                    if credential_status.telegram_token_shape_ok
                    else "não aparenta ter formato '<bot_id>:<secret>'.",
                ),
                HealthCheckItem(
                    "Formato HF_TOKEN",
                    "ok" if credential_status.hf_token_shape_ok else "warn",
                    "prefixo hf_ detectado."
                    if credential_status.hf_token_shape_ok
                    else "não começa com hf_; confirme se é um token Hugging Face válido.",
                ),
                HealthCheckItem(
                    "Usuário autorizado",
                    "ok" if self._settings.telegram_allowed_user_id > 0 else "fail",
                    f"user_id={self._settings.telegram_allowed_user_id}"
                    if self._settings.telegram_allowed_user_id > 0
                    else "TELEGRAM_ALLOWED_USER_ID inválido.",
                ),
            ]
        )
        env_status = (
            "fail"
            if ".env.example" in facts.env_file_state
            else "warn"
            if "não existe" in facts.env_file_state
            else "ok"
        )
        items.append(HealthCheckItem("Arquivo .env", env_status, facts.env_file_state))
        for executable in ("ffmpeg", "ffprobe", "yt-dlp"):
            present = facts.executable_available.get(executable, False)
            items.append(
                HealthCheckItem(
                    executable,
                    "ok" if present else ("warn" if executable == "yt-dlp" else "fail"),
                    "encontrado no PATH." if present else "não encontrado no PATH.",
                )
            )
        if any(name in facts.executable_available for name in ("deno", "node")):
            js_runtimes = tuple(
                name for name in ("deno", "node") if facts.executable_available.get(name, False)
            )
            items.append(
                HealthCheckItem(
                    "Runtime JS do YouTube",
                    "ok" if js_runtimes else "fail",
                    f"disponível: {', '.join(js_runtimes)}."
                    if js_runtimes
                    else "nenhum runtime suportado encontrado (Deno ou Node).",
                )
            )
        labels = {
            "yt_dlp": "yt-dlp",
            "yt_dlp_ejs": "yt-dlp EJS",
            "telegram": "python-telegram-bot",
            "sqlalchemy": "SQLAlchemy",
            "whisperx": "WhisperX",
            "pyannote.audio": "pyannote.audio",
            "transformers": "transformers",
        }
        for module, label in labels.items():
            if module == "yt_dlp_ejs" and module not in facts.module_available:
                continue
            present = facts.module_available.get(module, False)
            items.append(
                HealthCheckItem(
                    label,
                    "ok" if present else ("warn" if module == "transformers" else "fail"),
                    f"módulo {module!r} disponível."
                    if present
                    else f"módulo {module!r} não encontrado.",
                )
            )
        for label, writable in facts.directory_writable.items():
            items.append(
                HealthCheckItem(
                    f"Diretório {label}",
                    "ok" if writable else "fail",
                    "gravável." if writable else "não gravável.",
                )
            )
        items.append(
            HealthCheckItem(
                "SQLite",
                "fail" if facts.sqlite_error else "ok",
                (
                    "falha ao acessar o banco SQLite: "
                    + sanitize_text(facts.sqlite_error or "", self._settings)
                )
                if facts.sqlite_error
                else "acessível.",
            )
        )
        items.append(
            HealthCheckItem(
                "Registro de erros operacionais",
                "ok" if facts.operational_error_log_writable else "fail",
                (
                    f"gravável; {facts.operational_error_records} registro(s) recentes."
                    if facts.operational_error_records is not None
                    else "gravável."
                )
                if facts.operational_error_log_writable
                else "não gravável.",
            )
        )
        if facts.free_disk_mb is None:
            items.append(HealthCheckItem("Espaço em disco", "warn", "não foi possível medir."))
        else:
            threshold = self._settings.healthcheck_min_free_disk_mb
            items.append(
                HealthCheckItem(
                    "Espaço em disco",
                    "ok" if facts.free_disk_mb >= threshold else "warn",
                    f"{facts.free_disk_mb:.0f} MB livres; mínimo recomendado {threshold} MB.",
                )
            )
        if self._settings.youtube_cookies_file.strip():
            items.append(
                HealthCheckItem(
                    "Cookies YouTube",
                    "ok" if facts.cookies_file_exists else "warn",
                    "arquivo configurado existe."
                    if facts.cookies_file_exists
                    else "arquivo configurado não existe.",
                )
            )
        elif self._settings.youtube_cookies_browser.strip():
            items.append(HealthCheckItem("Cookies YouTube", "ok", "browser configurado."))
        else:
            items.append(
                HealthCheckItem(
                    "Cookies YouTube",
                    "warn",
                    "não configurados; o YouTube pode exigir autenticação anti-bot ou restringir vídeos.",
                )
            )
        items.extend(self._summary_items(facts))
        return HealthCheckReport(tuple(items))

    def _summary_items(self, facts: HealthEnvironmentSnapshot) -> list[HealthCheckItem]:
        if self._settings.summary_backend == "disabled":
            return [
                HealthCheckItem("Configuração de sumarização", "warn", "SUMMARY_BACKEND=disabled."),
                HealthCheckItem("LM Studio", "warn", "sumarização desabilitada."),
            ]
        problems: list[str] = []
        if self._settings.summary_partial_max_tokens > self._settings.summary_final_max_tokens:
            problems.append("SUMMARY_PARTIAL_MAX_TOKENS maior que SUMMARY_FINAL_MAX_TOKENS")
        if self._settings.summary_max_input_tokens < 3000:
            problems.append("SUMMARY_MAX_INPUT_TOKENS baixo; pode gerar muitos chunks")
        if self._settings.summary_timeout_s < 120:
            problems.append("SUMMARY_TIMEOUT_S baixo para LLM local")
        detail = (
            f"entrada={self._settings.summary_max_input_tokens}, "
            f"parcial={self._settings.summary_partial_max_tokens}, "
            f"final={self._settings.summary_final_max_tokens}, "
            f"timeout={self._settings.summary_timeout_s:.0f}s, "
            f"split_retries={self._settings.summary_timeout_split_retries}."
        )
        if problems:
            detail += " Atenção: " + "; ".join(problems) + "."
        items = [HealthCheckItem("Orçamento de sumarização", "warn" if problems else "ok", detail)]
        backend = self._settings.summary_tokenizer_backend
        transformers = facts.module_available.get("transformers", False)
        if backend == "hf" and not transformers:
            items.append(
                HealthCheckItem(
                    "Tokenizer de sumarização",
                    "fail",
                    "SUMMARY_TOKENIZER_BACKEND=hf exige transformers importável.",
                )
            )
        elif backend == "estimate":
            items.append(
                HealthCheckItem(
                    "Tokenizer de sumarização",
                    "warn",
                    f"usando estimativa por caracteres/token ({self._settings.summary_chars_per_token:.2f}).",
                )
            )
        else:
            items.append(
                HealthCheckItem(
                    "Tokenizer de sumarização",
                    "ok" if transformers else "warn",
                    f"backend={backend}; modelo/tokenizer alvo={self._settings.summary_tokenizer_model or self._settings.summary_model}.",
                )
            )
        items.append(
            HealthCheckItem(
                "trust_remote_code do tokenizer",
                "warn" if self._settings.summary_tokenizer_trust_remote_code else "ok",
                "trust_remote_code=true; habilitado explicitamente, revise a origem do tokenizer."
                if self._settings.summary_tokenizer_trust_remote_code
                else "trust_remote_code=false; desabilitado por padrão.",
            )
        )
        items.append(
            HealthCheckItem(
                "Thinking da LLM",
                "ok" if self._settings.summary_disable_thinking else "warn",
                "SUMMARY_DISABLE_THINKING=true; enviará controles anti-reasoning."
                if self._settings.summary_disable_thinking
                else "SUMMARY_DISABLE_THINKING=false; a LLM pode gerar reasoning.",
            )
        )
        if facts.model_probe_error:
            items.append(
                HealthCheckItem(
                    "LM Studio",
                    "fail",
                    "falha ao consultar /models: "
                    + sanitize_text(facts.model_probe_error, self._settings),
                )
            )
        elif facts.model_ids is None:
            items.append(HealthCheckItem("LM Studio", "warn", "probe de modelos não configurado."))
        elif self._settings.summary_model not in facts.model_ids:
            items.append(
                HealthCheckItem(
                    "LM Studio", "fail", f"{self._settings.summary_model} não aparece em /models."
                )
            )
        else:
            items.append(
                HealthCheckItem(
                    "LM Studio",
                    "ok",
                    f"modelo {self._settings.summary_model} disponível em /models.",
                )
            )
        return items
