"""Value object ``ModelName`` — modelos Whisper/ASR suportados."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Modelos padrão suportados diretamente por faster-whisper/WhisperX.
_STANDARD_MODELS = frozenset({"tiny", "base", "small", "medium", "large-v2", "large-v3"})

# Requisito de VRAM (GB) em float16 para cada modelo. Aproximações conservadoras.
_VRAM_REQUIREMENTS_GB: dict[str, float] = {
    "tiny": 1.0,
    "base": 1.0,
    "small": 2.0,
    "medium": 5.0,
    "large-v2": 10.0,
    "large-v3": 10.0,
}

# Fine-tuned models are usually large-class unless proven otherwise.
_DEFAULT_CUSTOM_MODEL_VRAM_GB = 10.0


@dataclass(frozen=True, slots=True)
class ModelName:
    """Identificador de modelo Whisper.

    Além dos nomes padrão, aceita repositórios Hugging Face (``org/model``)
    e caminhos locais. Isso permite usar modelos fine-tuned como
    ``inesc-id/WhisperLv3-X-PT-All`` sem bloquear a configuração.
    """

    name: str

    def __post_init__(self) -> None:
        cleaned = self.name.strip()
        object.__setattr__(self, "name", cleaned)
        if not _is_supported_model_reference(cleaned):
            raise ValueError(
                f"Modelo não suportado: '{self.name}'. Use um modelo padrão "
                f"({sorted(_STANDARD_MODELS)}), um repositório Hugging Face "
                "(ex.: org/modelo) ou um caminho local."
            )

    @property
    def is_standard(self) -> bool:
        return self.name in _STANDARD_MODELS

    @property
    def is_custom(self) -> bool:
        return not self.is_standard

    def vram_requirement_gb(self) -> float:
        return _VRAM_REQUIREMENTS_GB.get(self.name, _DEFAULT_CUSTOM_MODEL_VRAM_GB)

    def __str__(self) -> str:
        return self.name

    @classmethod
    def smaller_alternative(cls, current: ModelName) -> ModelName | None:
        """Devolve o próximo modelo menor; ``None`` se não houver.

        Para modelos customizados não há uma relação segura de tamanho. Nesses
        casos não inventamos fallback automático: a política de modelos deve ser
        definida explicitamente no ``.env`` ou em futura camada de roteamento ASR.
        """
        if current.name not in _STANDARD_MODELS:
            return None
        order = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]
        idx = order.index(current.name)
        if idx == 0:
            return None
        return cls(name=order[idx - 1])


def _is_supported_model_reference(value: str) -> bool:
    if not value or any(ch.isspace() for ch in value):
        return False
    if value in _STANDARD_MODELS:
        return True
    if "/" in value:
        return True
    if value.startswith((".", "~", "/")):
        return True
    # Também aceita um diretório local sem ./ se ele existir no filesystem.
    try:
        return Path(value).exists()
    except OSError:
        return False
