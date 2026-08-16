"""Serviço de healthcheck operacional do bot."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import platform
import shutil
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from yt_transcriber_bot.application.config import (
    AppSettings,
    find_project_root,
    resolve_settings_env_file,
)
from yt_transcriber_bot.application.services.sanitization import sanitize_text

ModelsProbe = Callable[[str, Mapping[str, str], float], Mapping[str, Any]]
ExecutableFinder = Callable[[str], str | None]
ModuleChecker = Callable[[str], bool]


class DiskUsageResult(Protocol):
    free: int


DiskUsage = Callable[[Path], DiskUsageResult]
SQLiteProbe = Callable[[Path], None]


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
        statuses = {item.status for item in self.items}
        if "fail" in statuses:
            return "fail"
        if "warn" in statuses:
            return "warn"
        return "ok"

    def render(self, settings: AppSettings) -> str:
        title = {
            "ok": "✅ Healthcheck: OK",
            "warn": "⚠️ Healthcheck: OK com avisos",
            "fail": "❌ Healthcheck: problemas encontrados",
        }[self.overall_status]
        lines = [title, ""]
        lines.extend(f"{item.icon} {item.name}: {item.detail}" for item in self.items)
        return _sanitize_healthcheck_text("\n".join(lines), settings)


class HealthCheckService:
    """Executa checagens leves, rápidas e sanitizadas para uso via Telegram."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        models_probe: ModelsProbe | None = None,
        executable_finder: ExecutableFinder | None = None,
        module_checker: ModuleChecker | None = None,
        disk_usage: DiskUsage | None = None,
        sqlite_probe: SQLiteProbe | None = None,
    ) -> None:
        self._settings = settings
        self._models_probe = models_probe or _urllib_get_json
        self._executable_finder = executable_finder or shutil.which
        self._module_checker = module_checker or _module_exists
        self._disk_usage = disk_usage or shutil.disk_usage
        self._sqlite_probe = sqlite_probe

    def run(self) -> HealthCheckReport:
        items: list[HealthCheckItem] = []
        items.extend(self._check_runtime())
        items.extend(self._check_configuration())
        items.extend(self._check_dependencies())
        items.extend(self._check_directories())
        items.append(self._check_sqlite())
        items.append(self._check_operational_error_log())
        items.append(self._check_disk_space())
        items.append(self._check_youtube_cookies())
        items.extend(self._check_summary_configuration())
        items.append(self._check_lm_studio())
        return HealthCheckReport(tuple(items))

    def _check_runtime(self) -> list[HealthCheckItem]:
        root = find_project_root(Path.cwd())
        return [
            HealthCheckItem(
                "Python",
                "ok",
                f"{platform.python_implementation()} {platform.python_version()} "
                f"em {platform.system()} {platform.machine()}.",
            ),
            HealthCheckItem("Diretório atual", "ok", "resolvido sem expor caminho absoluto."),
            HealthCheckItem(
                "Raiz do projeto",
                "ok" if root is not None else "warn",
                "encontrada." if root is not None else "não encontrada a partir do diretório atual",
            ),
        ]

    def _check_configuration(self) -> list[HealthCheckItem]:
        items: list[HealthCheckItem] = []
        problems = self._settings.validate_runtime_secrets()
        items.append(
            HealthCheckItem(
                "Configuração obrigatória",
                "fail" if problems else "ok",
                "; ".join(sanitize_text(p, self._settings) for p in problems)
                if problems
                else "segredos mínimos definidos.",
            )
        )
        credential_status = self._settings.credentials.status()
        items.append(
            HealthCheckItem(
                "Formato TELEGRAM_BOT_TOKEN",
                "ok" if credential_status.telegram_token_shape_ok else "warn",
                "aparenta ter formato do BotFather."
                if credential_status.telegram_token_shape_ok
                else "não aparenta ter formato '<bot_id>:<secret>'.",
            )
        )
        items.append(
            HealthCheckItem(
                "Formato HF_TOKEN",
                "ok" if credential_status.hf_token_shape_ok else "warn",
                "prefixo hf_ detectado."
                if credential_status.hf_token_shape_ok
                else "não começa com hf_; confirme se é um token Hugging Face válido.",
            )
        )
        items.append(
            HealthCheckItem(
                "Usuário autorizado",
                "ok" if self._settings.telegram_allowed_user_id > 0 else "fail",
                f"user_id={self._settings.telegram_allowed_user_id}"
                if self._settings.telegram_allowed_user_id > 0
                else "TELEGRAM_ALLOWED_USER_ID inválido.",
            )
        )
        try:
            env_file = resolve_settings_env_file()
        except ValueError as exc:
            items.append(
                HealthCheckItem("Arquivo .env", "fail", _sanitize_exception(exc, self._settings))
            )
        else:
            if env_file.name == ".env.example":
                items.append(
                    HealthCheckItem("Arquivo .env", "fail", ".env.example não pode ser runtime.")
                )
            elif env_file.exists():
                items.append(HealthCheckItem("Arquivo .env", "ok", "arquivo runtime encontrado."))
            else:
                items.append(
                    HealthCheckItem(
                        "Arquivo .env",
                        "warn",
                        "arquivo runtime não existe; usando variáveis de ambiente/defaults.",
                    )
                )
        return items

    def _check_dependencies(self) -> list[HealthCheckItem]:
        items: list[HealthCheckItem] = []
        for executable in ("ffmpeg", "ffprobe", "yt-dlp"):
            found = self._executable_finder(executable)
            items.append(
                HealthCheckItem(
                    executable,
                    "ok" if found else ("warn" if executable == "yt-dlp" else "fail"),
                    "encontrado no PATH." if found else "não encontrado no PATH.",
                )
            )
        modules = {
            "yt-dlp": "yt_dlp",
            "python-telegram-bot": "telegram",
            "SQLAlchemy": "sqlalchemy",
            "WhisperX": "whisperx",
            "pyannote.audio": "pyannote.audio",
            "transformers": "transformers",
        }
        for label, module_name in modules.items():
            present = self._module_checker(module_name)
            status = "ok" if present else ("warn" if module_name == "transformers" else "fail")
            detail = (
                _module_detail(module_name)
                if present
                else f"módulo {module_name!r} não encontrado."
            )
            items.append(HealthCheckItem(label, status, detail))
        return items

    def _check_directories(self) -> list[HealthCheckItem]:
        dirs = {
            "base_dir": self._settings.base_dir,
            "downloads": self._settings.downloads_dir(),
            "processed": self._settings.processed_dir(),
            "transcripts": self._settings.transcripts_dir(),
            "logs": self._settings.logs_dir(),
            "summaries": self._settings.summaries_dir(),
            "video_exports": self._settings.video_exports_dir(),
            "models": self._settings.models_dir,
        }
        items: list[HealthCheckItem] = []
        for label, path in dirs.items():
            ok, detail = _ensure_directory_writable(path)
            items.append(HealthCheckItem(f"Diretório {label}", "ok" if ok else "fail", detail))
        return items

    def _check_sqlite(self) -> HealthCheckItem:
        if self._sqlite_probe is None:
            return HealthCheckItem("SQLite", "warn", "probe SQLite não configurado.")
        try:
            self._sqlite_probe(self._settings.db_path)
        except Exception as exc:
            return HealthCheckItem(
                "SQLite",
                "fail",
                f"falha ao acessar o banco SQLite: {_sanitize_exception(exc, self._settings)}",
            )
        return HealthCheckItem("SQLite", "ok", "acessível.")

    def _check_operational_error_log(self) -> HealthCheckItem:
        path = self._settings.logs_dir() / "operational_errors.jsonl"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            marker = path.parent / ".operational-errors-write-test"
            marker.write_text("ok", encoding="utf-8")
            marker.unlink(missing_ok=True)
            if path.exists() and not path.is_file():
                return HealthCheckItem(
                    "Registro de erros operacionais",
                    "fail",
                    "o caminho esperado existe, mas não é arquivo.",
                )
        except Exception as exc:
            return HealthCheckItem(
                "Registro de erros operacionais",
                "fail",
                f"não gravável no diretório de logs: {_sanitize_exception(exc, self._settings)}",
            )
        detail = "gravável."
        if path.is_file():
            try:
                lines = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
                detail = f"gravável; {lines} registro(s) existentes."
            except OSError as exc:
                return HealthCheckItem(
                    "Registro de erros operacionais",
                    "warn",
                    "arquivo existe, mas não consegui contar registros: "
                    f"{_sanitize_exception(exc, self._settings)}",
                )
        return HealthCheckItem("Registro de erros operacionais", "ok", detail)

    def _check_disk_space(self) -> HealthCheckItem:
        path = self._settings.base_dir
        try:
            path.mkdir(parents=True, exist_ok=True)
            usage = self._disk_usage(path)
        except Exception as exc:
            return HealthCheckItem(
                "Espaço em disco",
                "warn",
                f"não consegui medir: {_sanitize_exception(exc, self._settings)}",
            )
        free_mb = usage.free / (1024 * 1024)
        threshold = self._settings.healthcheck_min_free_disk_mb
        status = "ok" if free_mb >= threshold else "warn"
        return HealthCheckItem(
            "Espaço em disco",
            status,
            f"{free_mb:.0f} MB livres no diretório base; mínimo recomendado {threshold} MB.",
        )

    def _check_youtube_cookies(self) -> HealthCheckItem:
        cookies_file = self._settings.credentials.youtube_cookies_file.strip()
        cookies_browser = self._settings.credentials.youtube_cookies_browser.strip()
        if cookies_file:
            path = Path(cookies_file).expanduser()
            if path.is_file():
                return HealthCheckItem("Cookies YouTube", "ok", "arquivo configurado existe.")
            return HealthCheckItem("Cookies YouTube", "warn", "arquivo configurado não existe.")
        if cookies_browser:
            return HealthCheckItem(
                "Cookies YouTube", "ok", f"browser configurado: {cookies_browser}."
            )
        return HealthCheckItem(
            "Cookies YouTube", "warn", "não configurados; vídeos restritos podem falhar."
        )

    def _check_summary_configuration(self) -> list[HealthCheckItem]:
        if self._settings.summary_backend == "disabled":
            return [
                HealthCheckItem("Configuração de sumarização", "warn", "SUMMARY_BACKEND=disabled.")
            ]
        items: list[HealthCheckItem] = []
        input_tokens = self._settings.summary_max_input_tokens
        final_tokens = self._settings.summary_final_max_tokens
        partial_tokens = self._settings.summary_partial_max_tokens
        timeout = self._settings.summary_timeout_s
        status = "ok"
        problems: list[str] = []
        if partial_tokens > final_tokens:
            status = "warn"
            problems.append("SUMMARY_PARTIAL_MAX_TOKENS maior que SUMMARY_FINAL_MAX_TOKENS")
        if input_tokens < 3000:
            status = "warn"
            problems.append("SUMMARY_MAX_INPUT_TOKENS baixo; pode gerar muitos chunks")
        if timeout < 120:
            status = "warn"
            problems.append("SUMMARY_TIMEOUT_S baixo para LLM local")
        detail = (
            f"entrada={input_tokens}, parcial={partial_tokens}, final={final_tokens}, "
            f"timeout={timeout:.0f}s, split_retries={self._settings.summary_timeout_split_retries}."
        )
        if problems:
            detail += " Atenção: " + "; ".join(problems) + "."
        items.append(HealthCheckItem("Orçamento de sumarização", status, detail))
        backend = self._settings.summary_tokenizer_backend
        tokenizer_model = self._settings.summary_tokenizer_model or self._settings.summary_model
        transformers_present = self._module_checker("transformers")
        if backend == "estimate":
            items.append(
                HealthCheckItem(
                    "Tokenizer de sumarização",
                    "warn",
                    f"usando estimativa por caracteres/token ({self._settings.summary_chars_per_token:.2f}).",
                )
            )
        elif backend == "hf" and not transformers_present:
            items.append(
                HealthCheckItem(
                    "Tokenizer de sumarização",
                    "fail",
                    "SUMMARY_TOKENIZER_BACKEND=hf exige transformers importável.",
                )
            )
        elif backend == "auto" and not transformers_present:
            items.append(
                HealthCheckItem(
                    "Tokenizer de sumarização",
                    "warn",
                    "backend auto, mas transformers não está importável; cairá para estimativa.",
                )
            )
        else:
            items.append(
                HealthCheckItem(
                    "Tokenizer de sumarização",
                    "ok",
                    f"backend={backend}; modelo/tokenizer alvo={tokenizer_model}.",
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
        return items

    def _check_lm_studio(self) -> HealthCheckItem:
        if self._settings.summary_backend == "disabled":
            return HealthCheckItem("LM Studio", "warn", "sumarização desabilitada.")
        url = f"{self._settings.summary_base_url.rstrip('/')}/models"
        headers = _auth_headers(self._settings)
        try:
            data = self._models_probe(url, headers, self._settings.healthcheck_lmstudio_timeout_s)
        except Exception as exc:
            return HealthCheckItem(
                "LM Studio",
                "fail",
                "não consegui consultar /models do backend OpenAI-compatible: "
                f"{_sanitize_exception(exc, self._settings)}",
            )
        model_ids = _extract_model_ids(data)
        if self._settings.summary_model not in model_ids:
            shown = ", ".join(model_ids[:10]) if model_ids else "<nenhum modelo retornado>"
            return HealthCheckItem(
                "LM Studio",
                "fail",
                f"SUMMARY_MODEL='{self._settings.summary_model}' não aparece em /models. Disponíveis: {shown}.",
            )
        return HealthCheckItem(
            "LM Studio",
            "ok",
            f"modelo '{self._settings.summary_model}' disponível em /models.",
        )


def _module_detail(module_name: str) -> str:
    aliases = {
        "yt_dlp": "yt-dlp",
        "telegram": "python-telegram-bot",
        "pyannote.audio": "pyannote.audio",
    }
    try:
        version = importlib.metadata.version(module_name)
    except importlib.metadata.PackageNotFoundError:
        try:
            version = importlib.metadata.version(aliases.get(module_name, module_name))
        except importlib.metadata.PackageNotFoundError:
            version = "versão não determinada"
    return f"importável ({version})."


def _module_exists(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _ensure_directory_writable(path: Path) -> tuple[bool, str]:
    try:
        path.mkdir(parents=True, exist_ok=True)
        marker = path / ".healthcheck-write-test"
        marker.write_text("ok", encoding="utf-8")
        marker.unlink(missing_ok=True)
    except Exception as exc:
        return False, f"não gravável/criável: {exc}"
    return True, "gravável."


def _sanitize_exception(exc: BaseException, settings: AppSettings) -> str:
    return sanitize_text(str(exc), settings)


def _auth_headers(settings: AppSettings) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.summary_api_key.strip():
        headers["Authorization"] = f"Bearer {settings.summary_api_key.strip()}"
    return headers


def _urllib_get_json(
    url: str,
    headers: Mapping[str, str],
    timeout_s: float,
) -> Mapping[str, Any]:
    request = urllib.request.Request(url, headers=dict(headers), method="GET")
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        raw = response.read().decode("utf-8")
    parsed = json.loads(raw)
    if not isinstance(parsed, Mapping):
        raise ValueError("resposta não é um objeto JSON")
    return parsed


def _extract_model_ids(data: Mapping[str, Any]) -> list[str]:
    raw_models = data.get("data", [])
    ids: list[str] = []
    if isinstance(raw_models, list):
        for item in raw_models:
            if isinstance(item, Mapping):
                model_id = str(item.get("id", "")).strip()
                if model_id:
                    ids.append(model_id)
    return ids


def _sanitize_healthcheck_text(text: str, settings: AppSettings) -> str:
    """Sanitiza segredos e caminhos locais em saída segura para Telegram."""

    cleaned = sanitize_text(text, settings)
    for path in sorted(
        _healthcheck_sensitive_paths(settings), key=lambda item: len(str(item)), reverse=True
    ):
        rendered = str(path)
        if rendered and rendered != "." and (path.is_absolute() or len(rendered) > 8):
            cleaned = cleaned.replace(rendered, "[PATH]")
    return cleaned


def _healthcheck_sensitive_paths(settings: AppSettings) -> set[Path]:
    paths = {
        settings.base_dir,
        settings.db_path,
        settings.models_dir,
        settings.downloads_dir(),
        settings.processed_dir(),
        settings.transcripts_dir(),
        settings.logs_dir(),
        settings.summaries_dir(),
        settings.video_exports_dir(),
    }
    cookie_file = settings.youtube_cookies_file.strip()
    if cookie_file:
        paths.add(Path(cookie_file).expanduser())
    return paths
