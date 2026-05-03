"""Seleção do dispositivo e parâmetros efetivos para a transcrição.

Implementa o algoritmo de auto-detect descrito na documentação:
1. Se ``device != auto`` -> respeita.
2. Se nao ha CUDA disponivel -> CPU.
3. Se CUDA tem CC < (6,0) -> CPU.
4. Se VRAM < requisito do modelo -> tenta um modelo menor; se ainda nao
   couber, cai para CPU.
5. Caso contrario -> CUDA.
"""

from __future__ import annotations

from dataclasses import dataclass

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.gpu_detector import HardwareProfile
from yt_transcriber_bot.domain.value_objects.compute_type import (
    ComputeKind,
    ComputeType,
)
from yt_transcriber_bot.domain.value_objects.device import Device
from yt_transcriber_bot.domain.value_objects.model_name import ModelName


@dataclass(frozen=True)
class RuntimePlan:
    """Decisao final dos parametros de execucao."""

    device: Device
    compute_type: ComputeType
    model: ModelName
    reason: str


def select_runtime(
    settings: AppSettings,
    hardware: HardwareProfile,
    language_code: str | None = None,
) -> RuntimePlan:
    """Decide os parametros efetivos a partir de config + hardware.

    Quando ``WHISPER_MODEL=auto``, escolhe o modelo por idioma antes de
    aplicar a política CPU/GPU/VRAM. Isso permite usar uma configuração mais
    leve para inglês e uma mais robusta para português, sem impedir override
    explícito pelo usuário.
    """
    requested_device = Device.from_string(settings.device)
    requested_model, model_reason = _resolve_model_for_language(settings, language_code)
    requested_compute = ComputeType.from_string(settings.compute_type)

    if requested_device.is_cpu():
        return RuntimePlan(
            device=Device.cpu(),
            compute_type=_resolve_cpu_compute(requested_compute),
            model=requested_model,
            reason=f"device=cpu (configurado pelo usuario); {model_reason}",
        )

    if requested_device.is_cuda():
        return RuntimePlan(
            device=Device.cuda(),
            compute_type=_resolve_cuda_compute(requested_compute),
            model=requested_model,
            reason=f"device=cuda (forcado pelo usuario); {model_reason}",
        )

    # device=auto → política completa
    if not hardware.has_cuda:
        return RuntimePlan(
            device=Device.cpu(),
            compute_type=_resolve_cpu_compute(requested_compute),
            model=requested_model,
            reason=f"auto: CUDA nao disponivel, usando CPU; {model_reason}",
        )
    if not hardware.is_cuda_compatible():
        cc = hardware.cuda_compute_capability
        return RuntimePlan(
            device=Device.cpu(),
            compute_type=_resolve_cpu_compute(requested_compute),
            model=requested_model,
            reason=f"auto: GPU com CC {cc} obsoleta, usando CPU; {model_reason}",
        )
    if not hardware.can_fit_model(requested_model.vram_requirement_gb()):
        # Iteramos para baixo ate achar um modelo que caiba na VRAM disponivel.
        candidate: ModelName | None = ModelName.smaller_alternative(requested_model)
        while candidate is not None and not hardware.can_fit_model(candidate.vram_requirement_gb()):
            candidate = ModelName.smaller_alternative(candidate)
        if candidate is not None:
            return RuntimePlan(
                device=Device.cuda(),
                compute_type=_resolve_cuda_compute(requested_compute),
                model=candidate,
                reason=(
                    f"auto: VRAM {hardware.vram_total_gb:.1f}GB insuficiente "
                    f"para {requested_model.name}, usando {candidate.name}; {model_reason}"
                ),
            )
        return RuntimePlan(
            device=Device.cpu(),
            compute_type=_resolve_cpu_compute(requested_compute),
            model=requested_model,
            reason=(
                f"auto: VRAM {hardware.vram_total_gb:.1f}GB insuficiente "
                f"para {requested_model.name}, usando CPU; {model_reason}"
            ),
        )

    return RuntimePlan(
        device=Device.cuda(),
        compute_type=_resolve_cuda_compute(requested_compute),
        model=requested_model,
        reason=f"auto: usando CUDA ({hardware.gpu_name}); {model_reason}",
    )


def _resolve_model_for_language(
    settings: AppSettings,
    language_code: str | None,
) -> tuple[ModelName, str]:
    """Escolhe o modelo Whisper solicitado ou o padrão por idioma."""
    if settings.whisper_model != "auto":
        return (
            ModelName(name=settings.whisper_model),
            f"modelo fixo configurado: {settings.whisper_model}",
        )

    lang = (language_code or "").strip().lower().split("-")[0]
    if lang == "pt":
        model = settings.whisper_model_pt
        reason = f"modelo auto por idioma pt: {model}"
    elif lang == "en":
        model = settings.whisper_model_en
        reason = f"modelo auto por idioma en: {model}"
    else:
        model = settings.whisper_model_default
        reason = f"modelo auto por idioma indefinido/outro: {model}"
    return ModelName(name=model), reason


def _resolve_cpu_compute(requested: ComputeType) -> ComputeType:
    """Em CPU, ``int8`` e o mais eficiente; ``float16`` nao e suportado."""
    if requested.kind in (ComputeKind.AUTO, ComputeKind.FLOAT16):
        return ComputeType(kind=ComputeKind.INT8)
    return requested


def _resolve_cuda_compute(requested: ComputeType) -> ComputeType:
    """Em CUDA, ``float16`` e o padrao; ``int8`` puro nao e ideal."""
    if requested.kind in (ComputeKind.AUTO, ComputeKind.INT8):
        return ComputeType(kind=ComputeKind.FLOAT16)
    return requested
