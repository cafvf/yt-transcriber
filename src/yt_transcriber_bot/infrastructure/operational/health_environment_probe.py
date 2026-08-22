from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Protocol

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.health_probe import (
    HealthEnvironmentProbe,
    HealthEnvironmentSnapshot,
)
from yt_transcriber_bot.configuration.runtime_settings import (
    find_development_checkout_root,
    resolve_runtime_settings_source,
)
from yt_transcriber_bot.infrastructure.operational.health_probes import probe_executable_version
from yt_transcriber_bot.infrastructure.persistence.filesystem.operational_error_store import (
    JsonlOperationalErrorStore,
)


class DiskUsageResult(Protocol):
    free: int


class LocalHealthEnvironmentProbe(HealthEnvironmentProbe):
    def __init__(
        self,
        *,
        settings: AppSettings,
        models_probe: Callable[[str, Mapping[str, str], float], Mapping[str, Any]],
        executable_finder: Callable[[str], str | None],
        module_checker: Callable[[str], bool],
        disk_usage: Callable[[Path], DiskUsageResult],
        sqlite_probe: Callable[[Path], None],
        operational_errors: JsonlOperationalErrorStore,
    ) -> None:
        self._settings = settings
        self._models_probe = models_probe
        self._find = executable_finder
        self._module = module_checker
        self._disk = disk_usage
        self._sqlite = sqlite_probe
        self._errors = operational_errors

    def snapshot(self) -> HealthEnvironmentSnapshot:
        import platform

        executables = {
            name: self._find(name) is not None
            for name in ("ffmpeg", "ffprobe", "yt-dlp", "deno", "node")
        }
        executable_versions = {
            name: probe_executable_version(name)
            for name in ("yt-dlp", "deno", "node")
            if executables.get(name, False)
        }
        modules = {
            name: self._module(name)
            for name in (
                "yt_dlp",
                "yt_dlp_ejs",
                "telegram",
                "sqlalchemy",
                "whisperx",
                "pyannote.audio",
                "transformers",
            )
        }
        directories = {
            "base_dir": self._settings.base_dir,
            "downloads": self._settings.downloads_dir(),
            "processed": self._settings.processed_dir(),
            "transcripts": self._settings.transcripts_dir(),
            "logs": self._settings.logs_dir(),
            "summaries": self._settings.summaries_dir(),
            "video_exports": self._settings.video_exports_dir(),
            "models": self._settings.models_dir,
        }
        writable = {name: _writable(path) for name, path in directories.items()}
        try:
            self._sqlite(self._settings.db_path)
            sqlite_error = None
        except Exception as exc:
            sqlite_error = str(exc)
        try:
            free_mb = self._disk(self._settings.base_dir).free / (1024 * 1024)
        except Exception:
            free_mb = None
        cookie = self._settings.youtube_cookies_file.strip()
        cookie_exists = Path(cookie).expanduser().is_file() if cookie else None

        model_ids: tuple[str, ...] | None = None
        model_error: str | None = None
        if self._settings.summary_backend != "disabled":
            headers = {"Content-Type": "application/json"}
            if self._settings.summary_api_key:
                headers["Authorization"] = f"Bearer {self._settings.summary_api_key}"
            try:
                data = self._models_probe(
                    f"{self._settings.summary_base_url.rstrip('/')}/models",
                    headers,
                    self._settings.healthcheck_lmstudio_timeout_s,
                )
                raw = data.get("data", [])
                model_ids = tuple(
                    str(item.get("id", ""))
                    for item in raw
                    if isinstance(item, Mapping) and item.get("id")
                )
            except Exception as exc:
                model_error = str(exc)
        try:
            source = resolve_runtime_settings_source()
            env = source.env_file
            if env is None:
                env_state = "nenhum dotenv implícito; usando ambiente/defaults."
            else:
                env_state = (
                    "arquivo runtime encontrado."
                    if env.exists()
                    else "arquivo runtime não existe; usando ambiente/defaults."
                )
        except ValueError as exc:
            env_state = str(exc)

        return HealthEnvironmentSnapshot(
            python_detail=f"{platform.python_implementation()} {platform.python_version()} em {platform.system()} {platform.machine()}.",
            project_root_found=find_development_checkout_root() is not None,
            env_file_state=env_state,
            executable_available=executables,
            module_available=modules,
            directory_writable=writable,
            sqlite_error=sqlite_error,
            operational_error_log_writable=writable.get("logs", False),
            operational_error_records=self._errors.recent_count(),
            free_disk_mb=free_mb,
            cookies_file_exists=cookie_exists,
            model_ids=model_ids,
            model_probe_error=model_error,
            executable_versions=executable_versions,
        )


def _writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        marker = path / ".health-write-test"
        marker.write_text("ok", encoding="utf-8")
        marker.unlink(missing_ok=True)
        return path.is_dir()
    except OSError:
        return False
