from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class HealthEnvironmentSnapshot:
    python_detail: str
    project_root_found: bool
    env_file_state: str
    executable_available: dict[str, bool]
    module_available: dict[str, bool]
    directory_writable: dict[str, bool]
    sqlite_error: str | None
    operational_error_log_writable: bool
    operational_error_records: int | None
    free_disk_mb: float | None
    cookies_file_exists: bool | None
    model_ids: tuple[str, ...] | None
    model_probe_error: str | None
    executable_versions: dict[str, str | None] = field(default_factory=dict)


class HealthEnvironmentProbe(ABC):
    @abstractmethod
    def snapshot(self) -> HealthEnvironmentSnapshot: ...
