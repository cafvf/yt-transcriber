"""Value object ``Duration`` em segundos, com helpers de formatação."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Duration:
    """Duração em segundos (não-negativa)."""

    seconds: int

    def __post_init__(self) -> None:
        if self.seconds < 0:
            raise ValueError(f"Duration deve ser não-negativa, recebeu {self.seconds}")

    @classmethod
    def from_seconds(cls, seconds: float | int) -> Duration:
        return cls(seconds=int(seconds))

    @classmethod
    def from_minutes(cls, minutes: int) -> Duration:
        if minutes < 0:
            raise ValueError(f"Minutos não-negativo, recebeu {minutes}")
        return cls(seconds=minutes * 60)

    @property
    def total_seconds(self) -> int:
        return self.seconds

    def to_hms(self) -> str:
        """Formato ``HH:MM:SS`` (ou ``H:MM:SS`` se >= 100h)."""
        hours, remainder = divmod(self.seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def to_human(self) -> str:
        """Formato humano: ``45min 12s`` / ``1h 02min 03s``."""
        hours, remainder = divmod(self.seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours}h {minutes:02d}min {secs:02d}s"
        if minutes:
            return f"{minutes}min {secs:02d}s"
        return f"{secs}s"

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, Duration):
            return NotImplemented
        return self.seconds >= other.seconds

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Duration):
            return NotImplemented
        return self.seconds > other.seconds

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Duration):
            return NotImplemented
        return self.seconds <= other.seconds

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Duration):
            return NotImplemented
        return self.seconds < other.seconds
