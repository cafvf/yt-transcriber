from __future__ import annotations

from yt_transcriber_bot.application.ports.cache import CacheCleanupResult
from yt_transcriber_bot.application.services.cache_maintenance import CacheMaintenanceService
from yt_transcriber_bot.application.services.healthcheck import (
    HealthCheckReport,
    HealthCheckService,
)
from yt_transcriber_bot.application.services.last_error import LastErrorReport, LastErrorService
from yt_transcriber_bot.application.services.retention_policy import (
    RetentionPolicy,
    RetentionResult,
)


class OperationalWorkflow:
    def __init__(
        self,
        *,
        healthcheck: HealthCheckService,
        last_error: LastErrorService,
        cache: CacheMaintenanceService,
        retention: RetentionPolicy,
    ) -> None:
        self._healthcheck = healthcheck
        self._last_error = last_error
        self._cache = cache
        self._retention = retention

    def healthcheck(self) -> HealthCheckReport:
        return self._healthcheck.run()

    def last_error(self, user_id: int) -> LastErrorReport:
        return self._last_error.latest_for_user(user_id)

    def record_error(
        self,
        *,
        user_id: int,
        operation: str,
        message: str,
        context: dict[str, object] | None = None,
        error: BaseException | None = None,
        stage: str = "",
        severity: str = "error",
    ) -> None:
        self._last_error.record_operation_error(
            user_id=user_id,
            operation=operation,
            message=message,
            context=context,
            error=error,
            stage=stage,
            severity=severity,
        )

    def clear_cache(self) -> CacheCleanupResult:
        return self._cache.clear()

    def apply_retention(self) -> RetentionResult:
        return self._retention.apply()
