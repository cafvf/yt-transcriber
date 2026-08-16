from __future__ import annotations

from yt_transcriber_bot.application.ports.cache import CacheCleanupResult
from yt_transcriber_bot.application.services.retention_policy import RetentionResult
from yt_transcriber_bot.application.workflows.operations import OperationalWorkflow


class Health:
    def run(self) -> str:
        return "health"


class LastError:
    def __init__(self) -> None:
        self.recorded = False

    def latest_for_user(self, user_id: int) -> str:
        return f"error:{user_id}"

    def record_operation_error(self, **kwargs: object) -> None:
        self.recorded = True


class Cache:
    def clear(self) -> CacheCleanupResult:
        return CacheCleanupResult(removed_files=2, removed_directories=1, failures=0)


class Retention:
    def apply(self) -> RetentionResult:
        return RetentionResult(expired_jobs=("job",), removed_files=())


def test_operational_workflow_coordinates_policies_without_external_io() -> None:
    last_error = LastError()
    workflow = OperationalWorkflow(
        healthcheck=Health(),  # type: ignore[arg-type]
        last_error=last_error,  # type: ignore[arg-type]
        cache=Cache(),  # type: ignore[arg-type]
        retention=Retention(),  # type: ignore[arg-type]
    )
    assert workflow.healthcheck() == "health"
    assert workflow.last_error(7) == "error:7"
    assert workflow.clear_cache().removed_files == 2
    assert workflow.apply_retention().expired_jobs == ("job",)
    workflow.record_error(user_id=7, operation="summary", message="boom")
    assert last_error.recorded is True
