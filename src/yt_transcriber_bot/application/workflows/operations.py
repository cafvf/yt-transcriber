from __future__ import annotations

from yt_transcriber_bot.application.operational_errors import (
    OperationalErrorCategory,
    OperationalErrorCode,
)
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
        code: OperationalErrorCode = OperationalErrorCode.INTERNAL_INVARIANT_VIOLATION,
        category: OperationalErrorCategory = OperationalErrorCategory.INTERNAL,
        retryable: bool = False,
        context: dict[str, object] | None = None,
        error: BaseException | None = None,
        stage: str = "",
        severity: str = "error",
    ) -> None:
        self._last_error.record_operation_error(
            user_id=user_id,
            operation=operation,
            message=message,
            code=code,
            category=category,
            retryable=retryable,
            context=context,
            error=error,
            stage=stage,
            severity=severity,
        )

    def clear_cache(self, *, user_id: int | None = None) -> CacheCleanupResult:
        result = self._cache.clear()
        if result.failures and user_id is not None:
            self._last_error.record_operation_error(
                user_id=user_id,
                operation="clearcache",
                message=(
                    "Limpeza de cache concluída parcialmente; "
                    "alguns itens não puderam ser removidos."
                ),
                context={"failures": result.failures},
                stage="cache_cleanup",
                severity="warn",
            )
        return result

    def apply_retention(self) -> RetentionResult:
        return self._retention.apply()
