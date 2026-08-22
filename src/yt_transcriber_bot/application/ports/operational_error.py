from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from yt_transcriber_bot.application.operational_errors import (
    OperationalErrorCategory,
    OperationalErrorCode,
)


@dataclass(frozen=True, slots=True)
class OperationalErrorRecord:
    user_id: int
    operation: str
    code: OperationalErrorCode = OperationalErrorCode.INTERNAL_INVARIANT_VIOLATION
    category: OperationalErrorCategory = OperationalErrorCategory.INTERNAL
    retryable: bool = False
    safe_message: str = ""
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    technical_context: dict[str, str] = field(default_factory=dict)
    stage: str = ""
    severity: str = "error"
    traceback_tail: str = ""


class OperationalErrorStore(ABC):
    @abstractmethod
    def append(self, record: OperationalErrorRecord) -> None: ...

    @abstractmethod
    def latest_for_user(self, user_id: int, *, limit: int) -> OperationalErrorRecord | None: ...


class JobLogReader(ABC):
    @abstractmethod
    def tail(self, path: Path, *, max_lines: int, max_chars: int) -> str: ...
