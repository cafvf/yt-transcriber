from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import Protocol


class TextGenerationError(RuntimeError):
    pass


class TextGenerationTimeoutError(TextGenerationError):
    pass


@dataclass(frozen=True, slots=True)
class TextGenerationRequest:
    system_prompt: str
    user_prompt: str
    max_tokens: int | None = None


class TextGenerationClient(Protocol):
    @property
    @abstractmethod
    def model(self) -> str: ...

    @abstractmethod
    def complete(self, request: TextGenerationRequest) -> str: ...


class TextTokenizer(Protocol):
    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def is_exact(self) -> bool: ...

    @abstractmethod
    def count(self, text: str) -> int: ...

    @abstractmethod
    def split(self, text: str, max_tokens: int) -> list[str]: ...
