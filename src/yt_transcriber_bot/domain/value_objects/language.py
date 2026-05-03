"""Value object ``Language`` — código ISO-639-1 de duas letras minúsculas."""

from __future__ import annotations

import re
from dataclasses import dataclass

_LANGUAGE_PATTERN = re.compile(r"^[a-z]{2}$")


@dataclass(frozen=True, slots=True)
class Language:
    """Código ISO-639-1 (ex.: ``pt``, ``en``, ``es``)."""

    code: str

    def __post_init__(self) -> None:
        if not _LANGUAGE_PATTERN.match(self.code):
            raise ValueError(
                f"Código de idioma inválido: '{self.code}' (esperado 2 letras minúsculas)"
            )

    @classmethod
    def pt(cls) -> Language:
        return cls(code="pt")

    @classmethod
    def en(cls) -> Language:
        return cls(code="en")

    def __str__(self) -> str:
        return self.code
