"""Seleção de runtime tipada por idioma."""

from __future__ import annotations

from dataclasses import dataclass

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.gpu_detector import HardwareProfile
from yt_transcriber_bot.application.ports.transcription_engine import (
    ProcessingPrecision,
    ProcessingTarget,
    TranscriptionProcessingProfile,
)
from yt_transcriber_bot.domain.value_objects.compute_type import (
    ComputeKind,
    ComputeType,
)
from yt_transcriber_bot.domain.value_objects.device import Device
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.model_name import ModelName

_STANDARD_MODEL_VRAM_GB: dict[str, float] = {
    "tiny": 1.0,
    "base": 1.0,
    "small": 2.0,
    "medium": 5.0,
    "large-v2": 10.0,
    "large-v3": 10.0,
}
_DEFAULT_CUSTOM_MODEL_VRAM_GB = 10.0
_MODEL_SIZE_ORDER = ("tiny", "base", "small", "medium", "large-v2", "large-v3")


def model_vram_requirement_gb(model: ModelName) -> float:
    return _STANDARD_MODEL_VRAM_GB.get(
        model.name,
        _DEFAULT_CUSTOM_MODEL_VRAM_GB,
    )


def smaller_model_alternative(current: ModelName) -> ModelName | None:
    if current.name not in _MODEL_SIZE_ORDER:
        return None
    idx = _MODEL_SIZE_ORDER.index(current.name)
    if idx == 0:
        return None
    return ModelName(name=_MODEL_SIZE_ORDER[idx - 1])


@dataclass(frozen=True)
class RuntimePlan:
    device: Device
    compute_type: ComputeType
    model: ModelName
    reason: str

    def processing_target(self) -> ProcessingTarget:
        if self.device.is_cpu():
            return ProcessingTarget.CPU
        if self.device.is_cuda():
            return ProcessingTarget.GPU
        raise ValueError("RuntimePlan cannot expose unresolved device=auto")

    def to_transcription_profile(self) -> TranscriptionProcessingProfile:
        precision = {
            ComputeKind.AUTO: ProcessingPrecision.AUTOMATIC,
            ComputeKind.FLOAT32: ProcessingPrecision.FULL,
            ComputeKind.FLOAT16: ProcessingPrecision.HALF,
            ComputeKind.INT8: ProcessingPrecision.EIGHT_BIT,
            ComputeKind.INT8_FLOAT16: ProcessingPrecision.EIGHT_BIT_HALF,
        }[self.compute_type.kind]
        return TranscriptionProcessingProfile(
            target=self.processing_target(),
            precision=precision,
            model_id=self.model.name,
        )


def select_runtime(
    settings: AppSettings,
    hardware: HardwareProfile,
    language: Language | None = None,
) -> RuntimePlan:
    requested_device = Device.from_string(settings.device)
    requested_model, model_reason = _resolve_model_for_language(settings, language)
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

    if not hardware.can_fit_model(model_vram_requirement_gb(requested_model)):
        candidate: ModelName | None = smaller_model_alternative(requested_model)
        while candidate is not None and not hardware.can_fit_model(
            model_vram_requirement_gb(candidate)
        ):
            candidate = smaller_model_alternative(candidate)
        if candidate is not None:
            return RuntimePlan(
                device=Device.cuda(),
                compute_type=_resolve_cuda_compute(requested_compute),
                model=candidate,
                reason=(
                    f"auto: VRAM {hardware.vram_total_gb:.1f}GB insuficiente "
                    f"para {requested_model.name}, usando {candidate.name}; "
                    f"{model_reason}"
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
    language: Language | None,
) -> tuple[ModelName, str]:
    if settings.whisper_model != "auto":
        return (
            ModelName(name=settings.whisper_model),
            f"modelo fixo configurado: {settings.whisper_model}",
        )

    lang = language.code if language is not None else None
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
    if requested.kind in (ComputeKind.AUTO, ComputeKind.FLOAT16):
        return ComputeType(kind=ComputeKind.INT8)
    return requested


def _resolve_cuda_compute(requested: ComputeType) -> ComputeType:
    if requested.kind in (ComputeKind.AUTO, ComputeKind.INT8):
        return ComputeType(kind=ComputeKind.FLOAT16)
    return requested
