"""Specification base — padrão Specification para validações compostáveis."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class Specification(ABC, Generic[T]):
    """Especificação genérica que pode ser combinada com ``&``, ``|`` e ``~``."""

    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool: ...

    def __and__(self, other: Specification[T]) -> Specification[T]:
        return _AndSpecification(self, other)

    def __or__(self, other: Specification[T]) -> Specification[T]:
        return _OrSpecification(self, other)

    def __invert__(self) -> Specification[T]:
        return _NotSpecification(self)


class _AndSpecification(Specification[T]):
    def __init__(self, left: Specification[T], right: Specification[T]) -> None:
        self._left = left
        self._right = right

    def is_satisfied_by(self, candidate: T) -> bool:
        return self._left.is_satisfied_by(candidate) and self._right.is_satisfied_by(candidate)


class _OrSpecification(Specification[T]):
    def __init__(self, left: Specification[T], right: Specification[T]) -> None:
        self._left = left
        self._right = right

    def is_satisfied_by(self, candidate: T) -> bool:
        return self._left.is_satisfied_by(candidate) or self._right.is_satisfied_by(candidate)


class _NotSpecification(Specification[T]):
    def __init__(self, spec: Specification[T]) -> None:
        self._spec = spec

    def is_satisfied_by(self, candidate: T) -> bool:
        return not self._spec.is_satisfied_by(candidate)
