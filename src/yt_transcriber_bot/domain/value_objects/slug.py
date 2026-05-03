"""Value object ``Slug`` — versão sanitizada de um título para uso em nome de arquivo."""

from __future__ import annotations

from dataclasses import dataclass

from slugify import slugify

# Limite seguro para nomes de arquivo (deixando margem para sufixos e extensões).
_MAX_SLUG_LENGTH = 80


@dataclass(frozen=True, slots=True)
class Slug:
    """Slug ASCII-safe, lowercase, com hifens em vez de espaços."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("Slug não pode ser vazio")
        if len(self.value) > _MAX_SLUG_LENGTH:
            raise ValueError(
                f"Slug excede o tamanho máximo de {_MAX_SLUG_LENGTH} ({len(self.value)})"
            )

    @classmethod
    def from_title(cls, title: str) -> Slug:
        """Cria um ``Slug`` a partir de um título arbitrário.

        Trata acentos, emojis, símbolos, espaços múltiplos e trunca em
        ``_MAX_SLUG_LENGTH`` caracteres preservando integridade de palavras.
        """
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Título vazio não pode gerar slug")

        raw = slugify(
            title,
            max_length=_MAX_SLUG_LENGTH,
            word_boundary=True,
            save_order=True,
            allow_unicode=False,
        )
        if not raw:
            # slugify pode devolver vazio se o título só tinha emojis/símbolos.
            raw = "untitled"
        return cls(value=raw)

    def with_suffix(self, suffix: int) -> Slug:
        """Devolve um novo slug com ``-N`` apensado, respeitando o limite."""
        if suffix <= 0:
            raise ValueError("Sufixo deve ser positivo")
        suffix_str = f"-{suffix}"
        max_base = _MAX_SLUG_LENGTH - len(suffix_str)
        truncated = self.value[:max_base].rstrip("-")
        return Slug(value=f"{truncated}{suffix_str}")

    def __str__(self) -> str:
        return self.value
